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
    template: Optional[str] = "default"
    agent: Optional[str] = None
    output_format: Optional[str] = None
    save_to_file: Optional[bool] = None
    options: Optional[AgentRuntimeOptions] = None


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


class UIProfileConfig(BaseModel):
    id: str
    label: str
    agent: str
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    output_format: str = "markdown"
    save_to_file: bool = False
    description: Optional[str] = None


class UIConfigPayload(BaseModel):
    active_profile_id: str
    profiles: List[UIProfileConfig]
