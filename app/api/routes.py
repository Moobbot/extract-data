from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
    Body,
    BackgroundTasks,
)
from fastapi.responses import FileResponse
from typing import List, Dict, Any, Optional
import shutil
import os
import uuid
import base64
from pathlib import Path
from app.core.config import settings
from app.core.ui_config import load_ui_config, save_ui_config
from app.services.ai_providers import AIProviderFactory
from app.services.tasks import process_image_task
from app.api.models import (
    AgentsListResponse,
    ExtractionJsonRequest,
    UIConfigPayload,
)

router = APIRouter()

# In-memory task store for small deployments without Redis
_TASK_RESULTS: Dict[str, Any] = {}


def _start_background_processing(
    background_tasks: BackgroundTasks,
    image_path: str,
    agent: str,
    output_format: str,
    save_to_file: bool,
    agent_config: Dict[str, Any],
    template_id: str = "default",
    source_filename: Optional[str] = None,
    source_folder: Optional[str] = None,
) -> str:
    task_id = str(uuid.uuid4())
    _TASK_RESULTS[task_id] = {"status": "PENDING"}

    def run_and_store_result(
        tid: str,
        path: str,
        ag: str,
        fmt: str,
        save: bool,
        config: Dict[str, Any],
        template: str,
        filename: Optional[str],
        folder: Optional[str],
    ) -> None:
        try:
            _TASK_RESULTS[tid]["status"] = "STARTED"
            result = process_image_task(
                path,
                ag,
                fmt,
                save,
                config,
                template_id=template,
                source_filename=filename,
                source_folder=folder,
                task_id=tid,
            )
            _TASK_RESULTS[tid] = {"status": "SUCCESS", "result": result}
        except Exception as exc:
            _TASK_RESULTS[tid] = {"status": "FAILURE", "result": str(exc)}

    background_tasks.add_task(
        run_and_store_result,
        task_id,
        image_path,
        agent,
        output_format,
        save_to_file,
        agent_config,
        template_id,
        source_filename,
        source_folder,
    )
    return task_id


def _build_agent_config(
    model: Optional[str], base_url: Optional[str], api_key: Optional[str]
) -> Dict[str, Any]:
    config: Dict[str, Any] = {}
    if model:
        config["model"] = model
    if base_url:
        config["base_url"] = base_url
    if api_key:
        config["api_key"] = api_key
    return config


def _persist_image_from_json_payload(payload: ExtractionJsonRequest) -> str:
    if payload.image_path:
        if not os.path.exists(payload.image_path) or not os.path.isfile(
            payload.image_path
        ):
            raise HTTPException(status_code=400, detail="Invalid image_path")
        return payload.image_path

    if not payload.image_base64:
        raise HTTPException(
            status_code=400,
            detail="Either image_path or image_base64 must be provided",
        )

    try:
        raw_bytes = base64.b64decode(payload.image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image_base64: {e}")

    extension = ".jpg"
    if payload.filename:
        ext = os.path.splitext(payload.filename)[1].lower()
        if ext:
            extension = ext

    safe_filename = f"{uuid.uuid4()}{extension}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)
    with open(file_path, "wb") as f:
        f.write(raw_bytes)
    return file_path


@router.get("/agents", response_model=AgentsListResponse)
async def list_agents():
    return {
        "default_agent": settings.DEFAULT_PROVIDER,
        "agents": AIProviderFactory.list_available_agents(),
    }


@router.get("/ui-config", response_model=UIConfigPayload)
async def get_ui_config():
    return load_ui_config()


@router.put("/ui-config", response_model=UIConfigPayload)
async def update_ui_config(payload: UIConfigPayload):
    return save_ui_config(payload.model_dump())


@router.post("/extract", response_model=Dict[str, Any])
async def extract_table_task(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    agent: str = Form(settings.DEFAULT_PROVIDER),
    output_format: str = Form("markdown"),
    save_to_file: bool = Form(False),
    model: Optional[str] = Form(None),
    base_url: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None),
):
    """
    Submits an image for background processing via FastAPI BackgroundTasks.
    Returns a task_id to poll for results.
    """
    # Save file to a persistent upload directory for the worker to access
    # Note: In production with multiple workers, use shared storage (S3/NFS)
    file_ext = os.path.splitext(file.filename)[1]

    safe_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    agent_config = _build_agent_config(model=model, base_url=base_url, api_key=api_key)
    task_id = _start_background_processing(
        background_tasks,
        file_path,
        agent,
        output_format,
        save_to_file,
        agent_config,
        source_filename=file.filename,
    )

    from app.core.db import insert_task

    insert_task(task_id, file.filename, "default")

    return {
        "task_id": task_id,
        "message": "Task submitted successfully",
        "status": "pending",
    }


@router.post("/extract/batch", response_model=List[Dict[str, Any]])
async def extract_batch_task(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    agent: str = Form(settings.DEFAULT_PROVIDER),
    output_format: str = Form("markdown"),
    save_to_file: bool = Form(False),
    model: Optional[str] = Form(None),
    base_url: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None),
    template: str = Form("default"),
):
    """
    Submits multiple images for background processing.
    Returns a list of task_ids.
    """
    tasks = []
    agent_config = _build_agent_config(model=model, base_url=base_url, api_key=api_key)

    for file in files:
        file_ext = os.path.splitext(file.filename)[1]
        safe_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            task_id = _start_background_processing(
                background_tasks,
                file_path,
                agent,
                output_format,
                save_to_file,
                agent_config,
                template_id=template,
                source_filename=file.filename,
            )
            from app.core.db import insert_task

            insert_task(task_id, file.filename, template)
            tasks.append(
                {"filename": file.filename, "task_id": task_id, "status": "pending"}
            )
        except Exception as e:
            tasks.append(
                {"filename": file.filename, "error": str(e), "status": "failed"}
            )

    return tasks


@router.post("/extract/folder", response_model=List[Dict[str, Any]])
async def extract_folder_task(
    background_tasks: BackgroundTasks,
    folder_path: str = Form(...),
    agent: str = Form(settings.DEFAULT_PROVIDER),
    output_format: str = Form("markdown"),
    save_to_file: bool = Form(False),
    model: Optional[str] = Form(None),
    base_url: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None),
    template: str = Form("default"),
):
    """
    Scans a local directory for images and submits them for processing.
    """
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        raise HTTPException(status_code=400, detail="Invalid folder path")

    agent_config = _build_agent_config(model=model, base_url=base_url, api_key=api_key)

    task_id = _start_background_processing(
        background_tasks,
        folder_path,
        agent,
        output_format,
        save_to_file,
        agent_config,
        template_id=template,
        source_filename=os.path.basename(os.path.normpath(folder_path)),
        source_folder=folder_path,
    )

    from app.core.db import insert_task

    insert_task(
        task_id,
        os.path.basename(os.path.normpath(folder_path)),
        template,
        folder_path=folder_path,
    )

    return [
        {
            "filename": os.path.basename(os.path.normpath(folder_path)),
            "task_id": task_id,
            "status": "pending",
            "path": folder_path,
        }
    ]


@router.post("/extract/json", response_model=Dict[str, Any])
async def extract_table_task_json(
    background_tasks: BackgroundTasks, payload: ExtractionJsonRequest = Body(...)
):
    """
    Submits an extraction task using a JSON payload.
    Supports either a local image_path or image_base64.
    """
    from app.core.ui_config import load_ui_config, get_active_profile

    active_profile = get_active_profile(load_ui_config())

    agent = (
        payload.agent
        if payload.agent
        else active_profile.get("agent", settings.DEFAULT_PROVIDER)
    )
    output_format = (
        payload.output_format
        if payload.output_format
        else active_profile.get("output_format", "markdown")
    )
    save_to_file = (
        payload.save_to_file
        if payload.save_to_file is not None
        else active_profile.get("save_to_file", False)
    )

    options = payload.options or None
    model = options.model if options and options.model else active_profile.get("model")
    base_url = (
        options.base_url
        if options and options.base_url
        else active_profile.get("base_url")
    )
    api_key = (
        options.api_key
        if options and options.api_key
        else active_profile.get("api_key")
    )

    # If folder path is provided, redirect to folder task handler
    if payload.image_path and os.path.isdir(payload.image_path):
        tasks = await extract_folder_task(
            background_tasks=background_tasks,
            folder_path=payload.image_path,
            agent=agent,
            output_format=output_format,
            save_to_file=save_to_file,
            model=model,
            base_url=base_url,
            api_key=api_key,
            template=payload.template or "default",
        )
        return {
            "task_id": "folder_batch",
            "message": f"Submitted {len(tasks)} tasks for folder",
            "status": "pending",
            "tasks": tasks,
        }

    file_path = _persist_image_from_json_payload(payload)
    source_filename = payload.filename or os.path.basename(file_path)
    source_folder = (
        os.path.dirname(payload.image_path)
        if payload.image_path and os.path.isfile(payload.image_path)
        else None
    )

    agent_config = _build_agent_config(model=model, base_url=base_url, api_key=api_key)
    task_id = _start_background_processing(
        background_tasks,
        file_path,
        agent,
        output_format,
        save_to_file,
        agent_config,
        template_id=payload.template or "default",
        source_filename=source_filename,
        source_folder=source_folder,
    )

    from app.core.db import insert_task

    insert_task(
        task_id,
        source_filename,
        payload.template or "default",
        folder_path=source_folder,
    )

    return {
        "task_id": task_id,
        "message": "Task submitted successfully",
        "status": "pending",
    }


@router.post("/task-artifact/{task_id}/json")
async def get_task_artifact_json(task_id: str):
    return await download_task_artifact(task_id, "json")


@router.post("/task-artifact/{task_id}/excel")
async def get_task_artifact_excel(task_id: str):
    return await download_task_artifact(task_id, "excel")


@router.post("/task-artifact/{task_id}/excel-lv1")
async def get_task_artifact_excel_lv1(task_id: str):
    return await download_task_artifact(task_id, "excel_lv1")


@router.post("/task-artifact/{task_id}/excel-template")
async def get_task_artifact_excel_template(task_id: str):
    return await download_task_artifact(task_id, "excel_template")


@router.get("/tasks")
async def get_tasks():
    from app.core.db import get_all_tasks

    return get_all_tasks()


@router.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    """
    Get the status and result of a background task.
    Kiểm tra in-memory store trước, sau đó fallback về SQLite DB.
    """
    if task_id in _TASK_RESULTS:
        return _TASK_RESULTS[task_id]

    # Fallback: đọc từ DB (task đã hoàn thành trước khi restart)
    from app.core.db import get_task_by_id

    task_row = get_task_by_id(task_id)
    if task_row:
        return {
            "status": task_row.get("status", "UNKNOWN").upper(),
            "task_id": task_id,
            "result": (
                {
                    "saved_to": task_row.get("json_path"),
                    "saved_excel": task_row.get("excel_path"),
                    "status": task_row.get("status"),
                    "filename": task_row.get("filename"),
                }
                if task_row.get("status") == "success"
                else None
            ),
            "error": task_row.get("error"),
        }

    return {"task_id": task_id, "status": "UNKNOWN", "message": "Task not found"}


@router.get("/task-artifact/{task_id}/{artifact_kind}")
@router.post("/task-artifact/{task_id}/{artifact_kind}")
async def download_task_artifact(task_id: str, artifact_kind: str):
    """
    Download a saved task artifact from the outputs directory.
    artifact_kind can be 'json', 'excel', 'excel_lv1', or 'excel_template'.
    """
    if artifact_kind not in {"json", "excel", "excel_lv1", "excel_template"}:
        raise HTTPException(status_code=400, detail="Invalid artifact kind")

    result_key_map = {
        "json": "saved_to",
        "excel": "saved_excel",
        "excel_lv1": "saved_excel_lv1",
        "excel_template": "saved_excel_template",
    }
    result_key = result_key_map[artifact_kind]
    artifact_path = None

    if task_id in _TASK_RESULTS:
        res_entry = _TASK_RESULTS[task_id]
        if res_entry.get("status") == "SUCCESS" and isinstance(
            res_entry.get("result"), dict
        ):
            artifact_path = res_entry["result"].get(result_key)

    # (AsyncResult fallback removed — no Redis in this deployment)

    # Fallback to persisted DB record in case result backend is gone.
    if not artifact_path:
        from app.core.db import get_task_by_id

        task_row = get_task_by_id(task_id)
        if task_row:
            if artifact_kind == "json":
                artifact_path = task_row.get("json_path")
            elif artifact_kind in {"excel", "excel_template"}:
                artifact_path = task_row.get("excel_path")
            elif artifact_kind == "excel_lv1":
                template_path = task_row.get("excel_path")
                if isinstance(template_path, str) and template_path.endswith(
                    "_template.xlsx"
                ):
                    candidate = template_path.replace("_template.xlsx", "_lv1.xlsx")
                    if os.path.exists(candidate):
                        artifact_path = candidate

    if not artifact_path:
        raise HTTPException(
            status_code=404, detail=f"No {artifact_kind} artifact found"
        )

    artifact_file = Path(artifact_path).resolve()
    outputs_dir = Path(settings.OUTPUT_DIR).resolve()

    if artifact_file.suffix.lower() not in {".json", ".xlsx"}:
        raise HTTPException(status_code=400, detail="Unsupported artifact type")

    try:
        artifact_file.relative_to(outputs_dir)
    except ValueError:
        raise HTTPException(status_code=403, detail="Artifact path is not allowed")

    if not artifact_file.exists():
        raise HTTPException(status_code=404, detail="Artifact file not found")

    media_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if artifact_file.suffix.lower() == ".xlsx"
        else "application/json"
    )
    return FileResponse(
        path=str(artifact_file),
        media_type=media_type,
        filename=artifact_file.name,
    )
