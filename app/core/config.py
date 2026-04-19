import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DEFAULT_PROVIDER: str = os.getenv("AI_PROVIDER", "gemini")
    DEFAULT_OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    DEFAULT_GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    DEFAULT_OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")
    DEFAULT_LOCAL_HTTP_TIMEOUT: int = int(os.getenv("LOCAL_HTTP_TIMEOUT", "60"))
    DEFAULT_OUTPUT_FORMAT: str = "markdown"
    CORS_ALLOW_ORIGINS: str = os.getenv("CORS_ALLOW_ORIGINS", "")

    # Celery / Redis
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv(
        "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
    )

    # Uploads
    UPLOAD_DIR: str = "uploaded_images"
    OUTPUT_DIR: str = "outputs"


settings = Settings()

# Ensure dirs exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
