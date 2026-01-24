from app.core.celery_app import celery_app
from app.services.ai_providers import AIProviderFactory
from app.services.prompt_manager import PromptManager
import os


@celery_app.task(bind=True)
def process_image_task(self, image_path: str, provider: str, output_format: str):
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

        return {
            "status": "success",
            "provider": provider,
            "format": output_format,
            "filename": os.path.basename(image_path),
            "content": content,
        }

    except Exception as e:
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise e
    finally:
        # Cleanup uploaded file if needed?
        # For now, let's keep it or manage cleanup policy separately
        # os.remove(image_path)
        pass
