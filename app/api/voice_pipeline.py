"""
Voice Pipeline WebSocket endpoint.

Implements the same 3-stage async-generator pipeline as voice-sandwich-demo:
  Audio → STT (AssemblyAI) → Agent (Claude) → TTS (OpenAI or ElevenLabs)

Connect via:  ws://localhost:8000/voice-pipeline/ws?tts=openai
              ws://localhost:8000/voice-pipeline/ws?tts=elevenlabs
"""

import asyncio
import contextlib
import os
from typing import AsyncIterator

import anthropic
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.services.voice.assemblyai_stt import AssemblyAISTT
from app.services.voice.elevenlabs_tts import ElevenLabsTTS
from app.services.voice.events import (
    AgentChunkEvent,
    AgentEndEvent,
    STTOutputEvent,
    VoiceAgentEvent,
    event_to_dict,
)
from app.services.voice.openai_tts import OpenAITTS

router = APIRouter(prefix="/voice-pipeline")

SYSTEM_PROMPT = """
You are Clara, a friendly and professional AI receptionist.
Help the caller with their questions. Be concise and clear — your responses will be read aloud.
Use natural spoken language. Avoid markdown, bullet points, or special characters.
""".strip()

_anthropic = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# ── Stage 1: STT ────────────────────────────────────────────────────────────

async def _stt_stream(
    audio_stream: AsyncIterator[bytes],
) -> AsyncIterator[VoiceAgentEvent]:
    stt = AssemblyAISTT(sample_rate=16000)

    async def send_audio():
        try:
            async for chunk in audio_stream:
                await stt.send_audio(chunk)
        finally:
            await stt.close()

    send_task = asyncio.create_task(send_audio())
    try:
        async for event in stt.receive_events():
            yield event
    finally:
        with contextlib.suppress(asyncio.CancelledError):
            send_task.cancel()
            await send_task
        await stt.close()


# ── Stage 2: Agent ──────────────────────────────────────────────────────────

async def _agent_stream(
    event_stream: AsyncIterator[VoiceAgentEvent],
) -> AsyncIterator[VoiceAgentEvent]:
    history: list[dict] = []

    async for event in event_stream:
        yield event

        if not isinstance(event, STTOutputEvent):
            continue

        history.append({"role": "user", "content": event.transcript})
        full_response = ""

        async with _anthropic.messages.stream(
            model="claude-haiku-4-5-20251001",
            system=SYSTEM_PROMPT,
            messages=history,
            max_tokens=512,
        ) as stream:
            async for text in stream.text_stream:
                full_response += text
                yield AgentChunkEvent.create(text)

        history.append({"role": "assistant", "content": full_response})
        yield AgentEndEvent.create()


# ── Stage 3: TTS ────────────────────────────────────────────────────────────

async def _tts_stream(
    event_stream: AsyncIterator[VoiceAgentEvent],
    provider: str = "openai",
) -> AsyncIterator[VoiceAgentEvent]:
    tts: OpenAITTS | ElevenLabsTTS = (
        ElevenLabsTTS(voice_id="21m00Tcm4TlvDq8ikWAM")
        if provider == "elevenlabs"
        else OpenAITTS(voice="alloy", model="tts-1")
    )

    buffer: list[str] = []
    async for event in event_stream:
        yield event

        if isinstance(event, AgentChunkEvent):
            buffer.append(event.text)

        elif isinstance(event, AgentEndEvent):
            text = "".join(buffer)
            buffer = []
            if text.strip():
                async for audio_event in tts.synthesize(text):
                    yield audio_event


# ── WebSocket handler ────────────────────────────────────────────────────────

@router.websocket("/ws")
async def voice_pipeline_ws(
    websocket: WebSocket,
    tts: str = Query(default="openai"),
):
    await websocket.accept()
    print(f"[VoicePipeline] Client connected — TTS provider: {tts}")

    audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()

    async def audio_stream() -> AsyncIterator[bytes]:
        while True:
            chunk = await audio_queue.get()
            if chunk is None:
                break
            yield chunk

    async def receive_audio():
        try:
            while True:
                data = await websocket.receive_bytes()
                await audio_queue.put(data)
        except (WebSocketDisconnect, Exception):
            pass
        finally:
            await audio_queue.put(None)

    async def run_pipeline():
        pipeline = _tts_stream(
            _agent_stream(
                _stt_stream(audio_stream())
            ),
            provider=tts,
        )
        async for event in pipeline:
            try:
                await websocket.send_json(event_to_dict(event))
            except Exception:
                break

    receive_task = asyncio.create_task(receive_audio())
    pipeline_task = asyncio.create_task(run_pipeline())

    try:
        await asyncio.gather(receive_task, pipeline_task)
    except Exception as e:
        print(f"[VoicePipeline] Error: {e}")
    finally:
        receive_task.cancel()
        pipeline_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.gather(receive_task, pipeline_task)
        print("[VoicePipeline] Client disconnected")
