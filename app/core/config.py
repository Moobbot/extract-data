import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DEFAULT_PROVIDER: str = os.getenv("AI_PROVIDER", "gemini")
    DEFAULT_OUTPUT_FORMAT: str = "markdown"


settings = Settings()
