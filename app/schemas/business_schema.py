from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class VoiceConfig(BaseModel):
    silence_threshold_ms: Optional[int] = 1000    # ms of silence before AI responds (200–3000)
    endpointing_ms: Optional[int] = 300            # Deepgram endpointing delay (100–800)
    vad_sensitivity: Optional[str] = "medium"      # low | medium | high
    tts_voice_id: Optional[str] = None             # ElevenLabs voice ID
    tts_voice_name: Optional[str] = None           # ElevenLabs voice display name
    language: Optional[str] = "en-IN"              # STT language hint
    greeting_message: Optional[str] = None         # What AI says when call connects

    class Config:
        extra = "allow"


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
    voice_config: Optional[VoiceConfig] = None


class BusinessResponse(BaseModel):
    id: UUID
    name: str
    business_type: Optional[str] = None
    phone_number: str
    whatsapp_number: Optional[str] = None
    timezone: Optional[str] = None
    address: Optional[str] = None
    voice_config: Optional[VoiceConfig] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
