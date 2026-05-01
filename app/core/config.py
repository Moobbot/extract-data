import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ── AI Providers ─────────────────────────────────────────────────────────
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DEFAULT_PROVIDER: str = os.getenv("AI_PROVIDER", "gemini")
    DEFAULT_OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    DEFAULT_GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    DEFAULT_OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")

    # ── LightOnOCR / Local HTTP ───────────────────────────────────────────────
    LOCAL_HTTP_BASE_URL: str = os.getenv(
        "LOCAL_HTTP_BASE_URL", "http://localhost:7861/extract"
    )
    DEFAULT_LOCAL_HTTP_TIMEOUT: int = int(os.getenv("LOCAL_HTTP_TIMEOUT", "300"))

    # ── Output ────────────────────────────────────────────────────────────────
    DEFAULT_OUTPUT_FORMAT: str = "markdown"

    # ── API ───────────────────────────────────────────────────────────────────
    CORS_ALLOW_ORIGINS: str = os.getenv("CORS_ALLOW_ORIGINS", "")

    # ── Storage ───────────────────────────────────────────────────────────────
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploaded_images")
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "outputs")


    # ── Paths ─────────────────────────────────────────────────────────────────
    # Thư mục gốc project (chứa app/, config/, templates/)
    # Trong Docker: /app | Local: thư mục chứa app/
    BASE_DIR: str = os.getenv(
        "BASE_DIR",
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    TEMPLATES_DIR: str = os.getenv("TEMPLATES_DIR", "")  # override nếu cần


settings = Settings()
# Resolve TEMPLATES_DIR sau khi BASE_DIR được set
if not settings.TEMPLATES_DIR:
    settings.TEMPLATES_DIR = os.path.join(settings.BASE_DIR, "templates")

# Ensure required directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
