"""
VoiceCallSession — per-call state for the voice gateway layer.

Separate from the AI-layer CallSession (app/core/session_manager.py).
This holds voice-specific state: audio state machine, stream IDs, config.
"""

from enum import Enum
from datetime import datetime


class VoiceState(str, Enum):
    LISTENING  = "LISTENING"   # waiting for user speech → forwarding audio to STT
    PROCESSING = "PROCESSING"  # AI engine running
    SPEAKING   = "SPEAKING"    # TTS streaming to Twilio
    ENDED      = "ENDED"       # call finished


class VoiceCallSession:
    def __init__(
        self,
        call_sid: str,
        stream_sid: str,
        business_id: str,
        caller_phone: str,
        voice_config: dict | None = None,
    ):
        self.call_sid      = call_sid
        self.stream_sid    = stream_sid
        self.business_id   = business_id
        self.caller_phone  = caller_phone
        self.voice_config  = voice_config or {}

        # Set by orchestrator after DB records are created
        self.db_call_id     : str | None = None
        self.db_customer_id : str | None = None

        self.state      = VoiceState.LISTENING
        self.created_at = datetime.utcnow()

    def __repr__(self) -> str:
        return (
            f"VoiceCallSession(call_sid={self.call_sid!r}, "
            f"state={self.state}, business={self.business_id})"
        )
