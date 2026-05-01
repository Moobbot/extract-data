"""
app/services/ai_providers.py

Backward-compatibility shim.
Toàn bộ logic đã được chuyển sang app/services/providers/.

Import từ file này vẫn hoạt động bình thường:
    from app.services.ai_providers import AIProviderFactory
"""

from app.services.providers import (  # noqa: F401
    AIProvider,
    AIProviderFactory,
    GeminiProvider,
    LightOnOCRProvider,
    LocalHTTPProvider,
    OpenAIProvider,
)

__all__ = [
    "AIProvider",
    "AIProviderFactory",
    "GeminiProvider",
    "LightOnOCRProvider",
    "LocalHTTPProvider",
    "OpenAIProvider",
]
