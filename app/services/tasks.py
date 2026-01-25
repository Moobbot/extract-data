from app.core.celery_app import celery_app
from app.services.ai_providers import AIProviderFactory
from app.services.prompt_manager import PromptManager
import os


@celery_app.task(bind=True)
def process_image_task(
    self, image_path: str, provider: str, output_format: str, save_to_file: bool = False
):
    """
    Background task to process an image.
    """
    try:
        self.update_state(state="PROGRESS", meta={"message": "Processing started"})

        # 1. Get Provider
        try:
            ai_provider = AIProviderFactory.get_provider(provider)
        except ValueError as e:
            return {"error": str(e), "status": "failed"}

        # 2. Get Prompt
        prompt = PromptManager.get_prompt(output_format)

        self.update_state(
            state="PROGRESS", meta={"message": "Generating content with AI"}
        )

        # 3. Generate
        try:
            content = ai_provider.generate_content(image_path, prompt)
        except Exception as e:
            return {"error": f"AI generation failed: {str(e)}", "status": "failed"}

        # 4. Save to file if requested
        saved_path = None
        if save_to_file:
            from app.core.config import settings

            base_name = os.path.splitext(os.path.basename(image_path))[0]
            ext = "md" if output_format == "markdown" else "json"
            output_filename = f"{base_name}.{ext}"
            saved_path = os.path.join(settings.OUTPUT_DIR, output_filename)

            with open(saved_path, "w", encoding="utf-8") as f:
                f.write(content)

        return {
            "status": "success",
            "provider": provider,
            "format": output_format,
            "filename": os.path.basename(image_path),
            "content": content,
            "saved_to": saved_path,
        }

    except Exception as e:
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise e
    finally:
        # Cleanup uploaded file if needed?
        # For now, let's keep it or manage cleanup policy separately
        # os.remove(image_path)
        pass
