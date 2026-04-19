from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
from typing import List, Dict, Any, Optional
import shutil
import os
import uuid
import base64
from celery.result import AsyncResult
from app.core.config import settings
from app.services.tasks import process_image_task
from app.services.ai_providers import AIProviderFactory
from app.api.models import ExtractionJsonRequest, AgentsListResponse

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
    file_path = _persist_image_from_json_payload(payload)

    agent_config = _build_agent_config(
        model=payload.options.model,
        base_url=payload.options.base_url,
        api_key=payload.options.api_key,
    )
    task = process_image_task.delay(
        file_path,
        payload.agent,
        payload.output_format,
        payload.save_to_file,
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
