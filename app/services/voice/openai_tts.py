import os
from typing import AsyncIterator, Optional

import openai

from app.services.voice.events import TTSChunkEvent


class OpenAITTS:
    def __init__(
        self,
        api_key: Optional[str] = None,
        voice: str = "alloy",
        model: str = "tts-1",
    ):
        self.client = openai.AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.voice = voice
        self.model = model

    async def synthesize(self, text: str) -> AsyncIterator[TTSChunkEvent]:
        """Stream PCM audio chunks for the given text via OpenAI TTS REST API."""
        if not text or not text.strip():
            return

        async with self.client.audio.speech.with_streaming_response.create(
            model=self.model,
            voice=self.voice,  # type: ignore[arg-type]
            input=text,
            response_format="pcm",  # raw PCM s16le at 24 kHz mono
        ) as response:
            async for chunk in response.iter_bytes(chunk_size=4096):
                if chunk:
                    yield TTSChunkEvent.create(chunk)
