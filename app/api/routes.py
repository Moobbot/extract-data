from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional, List, Dict, Any
import shutil
import os
import tempfile
from celery.result import AsyncResult
from app.core.config import settings
from app.services.tasks import process_image_task
from app.api.models import ExtractionResponse, ErrorResponse

router = APIRouter()


@router.post("/extract", response_model=Dict[str, Any])
async def extract_table_task(
    file: UploadFile = File(...),
    provider: str = Form("gemini"),
    output_format: str = Form("markdown"),
    save_to_file: bool = Form(False),
):
    """
    Submits an image for background processing via Celery.
    Returns a task_id to poll for results.
    """
    # Save file to a persistent upload directory for the worker to access
    # Note: In production with multiple workers, use shared storage (S3/NFS)
    file_ext = os.path.splitext(file.filename)[1]
    import uuid

    safe_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Dispatch Task
    task = process_image_task.delay(file_path, provider, output_format, save_to_file)

    return {
        "task_id": task.id,
        "message": "Task submitted successfully",
        "status": "pending",
    }


@router.post("/extract/batch", response_model=List[Dict[str, Any]])
async def extract_batch_task(
    files: List[UploadFile] = File(...),
    provider: str = Form("gemini"),
    output_format: str = Form("markdown"),
    save_to_file: bool = Form(False),
):
    """
    Submits multiple images for background processing.
    Returns a list of task_ids.
    """
    import uuid

    tasks = []

    for file in files:
        file_ext = os.path.splitext(file.filename)[1]
        safe_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Dispatch Task
            task = process_image_task.delay(
                file_path, provider, output_format, save_to_file
            )
            tasks.append(
                {"filename": file.filename, "task_id": task.id, "status": "pending"}
            )
        except Exception as e:
            tasks.append(
                {"filename": file.filename, "error": str(e), "status": "failed"}
            )


@router.post("/extract/folder", response_model=List[Dict[str, Any]])
async def extract_folder_task(
    folder_path: str = Form(...),
    provider: str = Form("gemini"),
    output_format: str = Form("markdown"),
    save_to_file: bool = Form(False),
):
    """
    Scans a local directory for images and submits them for processing.
    """
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        raise HTTPException(status_code=400, detail="Invalid folder path")

    import uuid

    tasks = []
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
                        file_path, provider, output_format, save_to_file
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
