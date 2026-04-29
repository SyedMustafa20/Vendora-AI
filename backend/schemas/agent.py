from pydantic import BaseModel, Field
from typing import Optional


class AgentConfigResponse(BaseModel):
    id: int
    admin_id: int
    agent_type: str
    agent_behavior_type: str
    intent_prompt: str
    generative_prompt: str
    model_name: str
    model_version: str
    temperature: float
    created_at: Optional[str]
    updated_at: Optional[str]

    model_config = {"from_attributes": True}


class AgentConfigUpdate(BaseModel):
    agent_type: Optional[str] = Field(None, max_length=50)
    agent_behavior_type: Optional[str] = Field(None, pattern="^(deterministic|generative|creative)$")
    intent_prompt: Optional[str] = None
    generative_prompt: Optional[str] = None
    model_name: Optional[str] = Field(None, max_length=100)
    model_version: Optional[str] = Field(None, max_length=50)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
