from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class AgentUiConfig(BaseModel):
    """UI-only fields synced to ElevenLabs (first message, language). No STT/VAD — ConvAI handles that."""

    first_message: Optional[str] = None
    language: Optional[str] = Field(default="en", description="ISO language code for the agent")

    class Config:
        extra = "ignore"


class BusinessCreate(BaseModel):
    name: str
    business_type: Optional[str] = None
    phone_number: str
    timezone: Optional[str] = None
    address: Optional[str] = None


class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    business_type: Optional[str] = None
    phone_number: Optional[str] = None
    whatsapp_number: Optional[str] = None
    timezone: Optional[str] = None
    address: Optional[str] = None
    # ElevenLabs ConvAI — one agent ID per tenant
    elevenlabs_agent_id: Optional[str] = None
    convai_llm_model: Optional[str] = None
    convai_voice_id: Optional[str] = None
    agent_ui: Optional[AgentUiConfig] = None


class BusinessResponse(BaseModel):
    id: UUID
    name: str
    business_type: Optional[str] = None
    phone_number: str
    whatsapp_number: Optional[str] = None
    timezone: Optional[str] = None
    address: Optional[str] = None
    elevenlabs_agent_id: Optional[str] = None
    convai_llm_model: Optional[str] = None
    convai_voice_id: Optional[str] = None
    agent_ui: Optional[AgentUiConfig] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
