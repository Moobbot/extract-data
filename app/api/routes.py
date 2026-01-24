from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional, List
import shutil
import os
import tempfile
from app.services.ai_providers import AIProviderFactory
from app.services.prompt_manager import PromptManager
from app.api.models import ExtractionResponse

router = APIRouter()


@router.post("/extract", response_model=ExtractionResponse)
async def extract_table(
    file: UploadFile = File(...),
    provider: str = Form("gemini"),
    output_format: str = Form("markdown"),
):
    """
    Extracts table data from an uploaded image.
    """
    tmp_path = None
    try:
        # Save temp file
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=os.path.splitext(file.filename)[1]
        ) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        # Get Provider
        try:
            ai_provider = AIProviderFactory.get_provider(provider)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Get Prompt
        prompt = PromptManager.get_prompt(output_format)

        # Generate
        try:
            content = ai_provider.generate_content(tmp_path, prompt)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"AI generation failed: {str(e)}"
            )

        return ExtractionResponse(
            filename=file.filename,
            content=content,
            provider=provider,
            format=output_format,
        )

    finally:
        # Cleanup
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/extract/batch", response_model=List[ExtractionResponse])
async def extract_batch(
    files: List[UploadFile] = File(...),
    provider: str = Form("gemini"),
    output_format: str = Form("markdown"),
):
    """
    Extracts table data from multiple uploaded images.
    """
    results = []
    # Note: In a real app, you might want to process these in parallel using asyncio.gather
    # For now, sequential for simplicity.

    for file in files:
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=os.path.splitext(file.filename)[1]
            ) as tmp:
                shutil.copyfileobj(file.file, tmp)
                tmp_path = tmp.name

            ai_provider = AIProviderFactory.get_provider(provider)
            prompt = PromptManager.get_prompt(output_format)

            content = ai_provider.generate_content(tmp_path, prompt)

            results.append(
                ExtractionResponse(
                    filename=file.filename,
                    content=content,
                    provider=provider,
                    format=output_format,
                )
            )

        except Exception as e:
            results.append(
                ExtractionResponse(
                    filename=file.filename,
                    content=f"Error: {str(e)}",
                    provider=provider,
                    format=output_format,
                )
            )
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

    return results
