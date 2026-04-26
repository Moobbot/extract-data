from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import FileResponse
from typing import List, Dict, Any, Optional
import shutil
import os
import uuid
import base64
from pathlib import Path
from celery.result import AsyncResult
from app.core.config import settings
from app.core.ui_config import load_ui_config, save_ui_config
from app.services.tasks import process_image_task
from app.services.ai_providers import AIProviderFactory
from app.api.models import (
    AgentsListResponse,
    ExtractionJsonRequest,
    UIConfigPayload,
)

router = APIRouter()


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
    file: UploadFile = File(...),
    agent: str = Form(settings.DEFAULT_PROVIDER),
    output_format: str = Form("markdown"),
    save_to_file: bool = Form(False),
    model: Optional[str] = Form(None),
    base_url: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None),
):
    """
    Submits an image for background processing via Celery.
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

    # Dispatch Task
    agent_config = _build_agent_config(model=model, base_url=base_url, api_key=api_key)
    task = process_image_task.delay(
        file_path,
        agent,
        output_format,
        save_to_file,
        agent_config,
    )

    return {
        "task_id": task.id,
        "message": "Task submitted successfully",
        "status": "pending",
    }


@router.post("/extract/batch", response_model=List[Dict[str, Any]])
async def extract_batch_task(
    files: List[UploadFile] = File(...),
    agent: str = Form(settings.DEFAULT_PROVIDER),
    output_format: str = Form("markdown"),
    save_to_file: bool = Form(False),
    model: Optional[str] = Form(None),
    base_url: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None),
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

            # Dispatch Task
            task = process_image_task.delay(
                file_path,
                agent,
                output_format,
                save_to_file,
                agent_config,
            )
            tasks.append(
                {"filename": file.filename, "task_id": task.id, "status": "pending"}
            )
        except Exception as e:
            tasks.append(
                {"filename": file.filename, "error": str(e), "status": "failed"}
            )

    return tasks


@router.post("/extract/folder", response_model=List[Dict[str, Any]])
async def extract_folder_task(
    folder_path: str = Form(...),
    agent: str = Form(settings.DEFAULT_PROVIDER),
    output_format: str = Form("markdown"),
    save_to_file: bool = Form(False),
    model: Optional[str] = Form(None),
    base_url: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None),
):
    """
    Scans a local directory for images and submits them for processing.
    """
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        raise HTTPException(status_code=400, detail="Invalid folder path")

    tasks = []
    agent_config = _build_agent_config(model=model, base_url=base_url, api_key=api_key)
    valid_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    # Walk through directory
    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext in valid_extensions:
                file_path = os.path.join(root, filename)

                # Note: We use the existing file path directly since it's local
                try:
                    task = process_image_task.delay(
                        file_path,
                        agent,
                        output_format,
                        save_to_file,
                        agent_config,
                    )
                    tasks.append(
                        {
                            "filename": filename,
                            "task_id": task.id,
                            "status": "pending",
                            "path": file_path,
                        }
                    )
                except Exception as e:
                    tasks.append(
                        {"filename": filename, "error": str(e), "status": "failed"}
                    )

    if not tasks:
        return [{"message": "No valid images found in folder"}]

    return tasks


@router.post("/extract/json", response_model=Dict[str, Any])
async def extract_table_task_json(payload: ExtractionJsonRequest = Body(...)):
    """
    Submits an extraction task using a JSON payload.
    Supports either a local image_path or image_base64.
    """
    from app.core.ui_config import load_ui_config, get_active_profile
    active_profile = get_active_profile(load_ui_config())

    agent = payload.agent if payload.agent else active_profile.get("agent", settings.DEFAULT_PROVIDER)
    output_format = payload.output_format if payload.output_format else active_profile.get("output_format", "markdown")
    save_to_file = payload.save_to_file if payload.save_to_file is not None else active_profile.get("save_to_file", False)

    options = payload.options or None
    model = options.model if options and options.model else active_profile.get("model")
    base_url = options.base_url if options and options.base_url else active_profile.get("base_url")
    api_key = options.api_key if options and options.api_key else active_profile.get("api_key")

    # If folder path is provided, redirect to folder task handler
    if payload.image_path and os.path.isdir(payload.image_path):
        tasks = await extract_folder_task(
            folder_path=payload.image_path,
            agent=agent,
            output_format=output_format,
            save_to_file=save_to_file,
            model=model,
            base_url=base_url,
            api_key=api_key
        )
        return {
            "task_id": "folder_batch",
            "message": f"Submitted {len(tasks)} tasks for folder",
            "status": "pending",
            "tasks": tasks
        }

    file_path = _persist_image_from_json_payload(payload)

    agent_config = _build_agent_config(model=model, base_url=base_url, api_key=api_key)
    task = process_image_task.delay(
        file_path,
        agent,
        output_format,
        save_to_file,
        agent_config,
    )

    return {
        "task_id": task.id,
        "message": "Task submitted successfully",
        "status": "pending",
    }


@router.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    """
    Get the status and result of a background task.
    """
    task = AsyncResult(task_id)

    response = {
        "task_id": task_id,
        "status": task.state,
    }

    if task.state == "SUCCESS":
        response["result"] = task.result
    elif task.state == "FAILURE":
        response["error"] = str(task.result)  # Use str() for safety or task.info

    return response


@router.get("/task-artifact/{task_id}/{artifact_kind}")
async def download_task_artifact(task_id: str, artifact_kind: str):
    """
    Download a saved task artifact from the outputs directory.
    artifact_kind can be 'json' or 'excel'.
    """
    if artifact_kind not in {"json", "excel"}:
        raise HTTPException(status_code=400, detail="Invalid artifact kind")

    task = AsyncResult(task_id)
    if task.state != "SUCCESS" or not isinstance(task.result, dict):
        raise HTTPException(status_code=404, detail="Task result not available")

    result_key = "saved_excel" if artifact_kind == "excel" else "saved_to"
    artifact_path = task.result.get(result_key)
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
