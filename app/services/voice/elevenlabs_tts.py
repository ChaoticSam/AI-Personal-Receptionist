import os
from typing import AsyncIterator, Optional

import httpx

from app.services.voice.events import TTSChunkEvent


class ElevenLabsTTS:
    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        model_id: str = "eleven_multilingual_v2",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
    ):
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError("ElevenLabs API key is required")
        self.voice_id = voice_id
        self.model_id = model_id
        self.stability = stability
        self.similarity_boost = similarity_boost

    async def synthesize(self, text: str) -> AsyncIterator[TTSChunkEvent]:
        """Stream raw PCM audio from ElevenLabs REST streaming endpoint."""
        if not text or not text.strip():
            return

        url = (
            f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream"
            f"?output_format=pcm_24000"
        )
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        body = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": self.stability,
                "similarity_boost": self.similarity_boost,
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, headers=headers, json=body) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size=4096):
                    if chunk:
                        yield TTSChunkEvent.create(chunk)
