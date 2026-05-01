"""
app/core/interfaces.py

Backward-compatibility shim.
AIProvider đã được chuyển sang app/services/providers/base.py.
"""

from app.services.providers.base import AIProvider  # noqa: F401

__all__ = ["AIProvider"]
