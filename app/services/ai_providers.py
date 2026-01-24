from app.core.interfaces import AIProvider
from app.core.config import settings
from app.services.image_processor import ImageProcessor
from google import genai
from PIL import Image

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Google API Key is missing")
        self.client = genai.Client(api_key=api_key)

    def generate_content(self, image_path: str, prompt: str) -> str:
        img = Image.open(image_path)
        candidate_models = [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-flash-latest",
            "gemini-2.5-pro",
            "gemini-pro-latest",
            "gemini-1.5-flash",
        ]

        last_err = None
        for m in candidate_models:
            try:
                resp = self.client.models.generate_content(
                    model=m,
                    contents=[prompt, img],
                )
                return resp.text
            except Exception as e:
                last_err = e

        raise RuntimeError(f"All Gemini models failed. Last error: {last_err}")


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str):
        if not OpenAI:
            raise ImportError("OpenAI module not installed")
        if not api_key:
            raise ValueError("OpenAI API Key is missing")
        self.client = OpenAI(api_key=api_key)

    def generate_content(self, image_path: str, prompt: str) -> str:
        base64_image = ImageProcessor.encode_image_base64(image_path)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=4096,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI call failed: {e}")


class AIProviderFactory:
    @staticmethod
    def get_provider(provider_name: str) -> AIProvider:
        if provider_name == "gemini":
            return GeminiProvider(settings.GOOGLE_API_KEY)
        elif provider_name == "openai":
            return OpenAIProvider(settings.OPENAI_API_KEY)
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
