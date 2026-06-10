import base64
import time
from dataclasses import dataclass
from typing import Literal, Union


def _now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class STTChunkEvent:
    type: Literal["stt_chunk"]
    transcript: str
    ts: int

    @classmethod
    def create(cls, transcript: str) -> "STTChunkEvent":
        return cls(type="stt_chunk", transcript=transcript, ts=_now_ms())


@dataclass
class STTOutputEvent:
    type: Literal["stt_output"]
    transcript: str
    ts: int

    @classmethod
    def create(cls, transcript: str) -> "STTOutputEvent":
        return cls(type="stt_output", transcript=transcript, ts=_now_ms())


STTEvent = Union[STTChunkEvent, STTOutputEvent]


@dataclass
class AgentChunkEvent:
    type: Literal["agent_chunk"]
    text: str
    ts: int

    @classmethod
    def create(cls, text: str) -> "AgentChunkEvent":
        return cls(type="agent_chunk", text=text, ts=_now_ms())


@dataclass
class AgentEndEvent:
    type: Literal["agent_end"]
    ts: int

    @classmethod
    def create(cls) -> "AgentEndEvent":
        return cls(type="agent_end", ts=_now_ms())


@dataclass
class TTSChunkEvent:
    type: Literal["tts_chunk"]
    audio: bytes
    ts: int

    @classmethod
    def create(cls, audio: bytes) -> "TTSChunkEvent":
        return cls(type="tts_chunk", audio=audio, ts=_now_ms())


VoiceAgentEvent = Union[STTEvent, AgentChunkEvent, AgentEndEvent, TTSChunkEvent]


def event_to_dict(event: VoiceAgentEvent) -> dict:
    if isinstance(event, (STTChunkEvent, STTOutputEvent)):
        return {"type": event.type, "transcript": event.transcript, "ts": event.ts}
    if isinstance(event, AgentChunkEvent):
        return {"type": event.type, "text": event.text, "ts": event.ts}
    if isinstance(event, AgentEndEvent):
        return {"type": event.type, "ts": event.ts}
    if isinstance(event, TTSChunkEvent):
        return {
            "type": event.type,
            "audio": base64.b64encode(event.audio).decode("ascii"),
            "ts": event.ts,
        }
    raise ValueError(f"Unknown event type: {type(event)}")
