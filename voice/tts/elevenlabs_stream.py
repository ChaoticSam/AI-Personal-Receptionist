"""
ElevenLabsStream — streaming Text-to-Speech via ElevenLabs API.

Output format: ulaw_8000 (µ-law 8kHz mono) — exactly what Twilio expects.
No audio conversion required; chunks are base64-encoded and sent as
Twilio Media Stream "media" events.

Model: eleven_turbo_v2_5 (lowest latency, ~200ms TTFB)
"""

import base64
from typing import TYPE_CHECKING

import httpx

from app.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL_ID

if TYPE_CHECKING:
    from fastapi import WebSocket

_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"

# Bytes per chunk sent to Twilio. Twilio handles variable chunk sizes fine.
_CHUNK_SIZE = 4096


async def stream_tts_to_twilio(
    text: str,
    ws: "WebSocket",
    stream_sid: str,
    voice_id: str | None = None,
    model_id: str | None = None,
) -> bool:
    """
    Convert text to µ-law audio via ElevenLabs and stream it to Twilio.

    Args:
        text       : The AI response text to speak.
        ws         : Active Twilio Media Stream WebSocket.
        stream_sid : Twilio stream SID (required for outbound media events).
        voice_id   : ElevenLabs voice ID (falls back to ELEVENLABS_VOICE_ID env var).
        model_id   : ElevenLabs model  (falls back to ELEVENLABS_MODEL_ID env var).

    Returns:
        True if audio was streamed successfully, False on any error.
    """
    vid = voice_id or ELEVENLABS_VOICE_ID
    mid = model_id or ELEVENLABS_MODEL_ID

    if not ELEVENLABS_API_KEY:
        print("[TTS] ELEVENLABS_API_KEY not configured — TTS disabled.")
        return False

    if not vid:
        print("[TTS] ELEVENLABS_VOICE_ID not configured — TTS disabled.")
        return False

    url = _TTS_URL.format(voice_id=vid)
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": mid,
        "output_format": "ulaw_8000",   # µ-law 8kHz — native Twilio format
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        },
    }

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0)
        ) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    print(f"[TTS] ElevenLabs error {response.status_code}: {body[:200]}")
                    return False

                async for chunk in response.aiter_bytes(chunk_size=_CHUNK_SIZE):
                    if not chunk:
                        continue
                    encoded = base64.b64encode(chunk).decode("utf-8")
                    await ws.send_json({
                        "event": "media",
                        "streamSid": stream_sid,
                        "media": {"payload": encoded},
                    })

        return True

    except httpx.TimeoutException as exc:
        print(f"[TTS] ElevenLabs timeout: {exc}")
        return False
    except Exception as exc:
        print(f"[TTS] Unexpected error: {exc}")
        return False
