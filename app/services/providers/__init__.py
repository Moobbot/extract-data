"""
app/services/providers/__init__.py

Public API của package providers.
Import từ đây để dùng toàn bộ providers + factory:

    from app.services.providers import AIProviderFactory, GeminiProvider
"""

from .base import AIProvider
from .factory import AIProviderFactory
from .gemini import GeminiProvider
from .lightonocr import LightOnOCRProvider
from .local_http import LocalHTTPProvider
from .openai_provider import OpenAIProvider

__all__ = [
    "AIProvider",
    "AIProviderFactory",
    "GeminiProvider",
    "LightOnOCRProvider",
    "LocalHTTPProvider",
    "OpenAIProvider",
]
