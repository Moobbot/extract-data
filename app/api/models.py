from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class ExtractionResponse(BaseModel):
    filename: str
    content: str
    agent: str
    provider: str
    format: str


class ErrorResponse(BaseModel):
    detail: str


class AgentRuntimeOptions(BaseModel):
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None


class ExtractionJsonRequest(BaseModel):
    image_path: Optional[str] = None
    image_base64: Optional[str] = None
    filename: Optional[str] = None
    agent: str = "gemini"
    output_format: str = "markdown"
    save_to_file: bool = False
    options: AgentRuntimeOptions = Field(default_factory=AgentRuntimeOptions)


class AgentDescriptor(BaseModel):
    name: str
    type: str
    source: str
    requires: Optional[List[str]] = None
    has_api_key: Optional[bool] = None
    has_base_url: Optional[bool] = None
    has_model: Optional[bool] = None


class AgentsListResponse(BaseModel):
    default_agent: str
    agents: List[AgentDescriptor]
