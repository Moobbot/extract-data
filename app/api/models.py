from pydantic import BaseModel
from typing import Optional


class ExtractionResponse(BaseModel):
    filename: str
    content: str
    provider: str
    format: str


class ErrorResponse(BaseModel):
    detail: str
