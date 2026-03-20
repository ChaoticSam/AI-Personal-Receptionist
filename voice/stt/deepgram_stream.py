"""
DeepgramStream — async live transcription via Deepgram WebSocket (SDK v6).

SDK v6 uses a context-manager + event-emitter pattern.

  connect() opens the WebSocket and runs `start_listening()` as a background
  task so it stays alive for the entire call.  Audio chunks are forwarded with
  send(), and the connection is closed with finish().

Configuration:
  model        : nova-2  (best for conversational speech)
  encoding     : mulaw   (matches Twilio's audio format — no conversion)
  sample_rate  : 8000
  endpointing  : from voice_config (default 300ms)
  language     : from voice_config (default en-IN)
"""

import asyncio
import logging
from typing import Callable, Awaitable

from app.config import DEEPGRAM_API_KEY

stt_pipeline_log = logging.getLogger("voice.stt.pipeline")


class DeepgramStream:
    def __init__(
        self,
        on_final_transcript: Callable[[str], Awaitable[None]],
        language: str = "en-IN",
        endpointing_ms: int = 300,
    ):
        self._on_final       = on_final_transcript
        self._language       = language
        self._endpointing    = endpointing_ms
        self._connection     = None   # AsyncV1SocketClient
        self._listen_task    = None   # asyncio.Task running start_listening()
        self._ctx_manager    = None   # async context manager
        self._connected      = False

    async def connect(self) -> bool:
        """Open Deepgram live transcription WebSocket. Returns True on success."""
        if not DEEPGRAM_API_KEY:
            stt_pipeline_log.warning("DEEPGRAM_API_KEY not configured — transcription disabled.")
            return False

        try:
            from deepgram import AsyncDeepgramClient
            from deepgram.listen.v1.types import ListenV1Results
            from deepgram.core.events import EventType

            client = AsyncDeepgramClient(api_key=DEEPGRAM_API_KEY)

            self._ctx_manager = client.listen.v1.connect(
                model          = "nova-2",
                language       = self._language,
                encoding       = "mulaw",
                sample_rate    = "8000",
                channels       = "1",
                endpointing    = str(self._endpointing),
                interim_results= "true",
                smart_format   = "true",
                punctuate      = "true",
            )

            self._connection = await self._ctx_manager.__aenter__()

            _on_final = self._on_final

            async def _on_message(event_type, result, **kwargs):  # noqa: ANN001
                try:
                    if not isinstance(result, ListenV1Results):
                        return
                    alts = result.channel.alternatives if result.channel else []
                    if not alts:
                        return
                    text = alts[0].transcript.strip() if alts[0].transcript else ""
                    if not text:
                        return

                    if result.speech_final:
                        stt_pipeline_log.info("Deepgram→app speech_final: %s", text)
                        await _on_final(text)
                    elif result.is_final:
                        stt_pipeline_log.info("Deepgram→app is_final: %s", text)
                except Exception as exc:
                    stt_pipeline_log.warning("Deepgram message handler error: %s", exc)

            async def _on_error(event_type, error, **kwargs):  # noqa: ANN001
                stt_pipeline_log.warning("Deepgram error: %s", error)

            self._connection.on(EventType.MESSAGE, _on_message)
            self._connection.on(EventType.ERROR,   _on_error)

            # start_listening() blocks until connection closes — run in background
            self._listen_task = asyncio.create_task(
                self._connection.start_listening(),
                name="deepgram_listen",
            )

            self._connected = True
            return True

        except Exception as exc:
            stt_pipeline_log.warning("Deepgram connect error: %s", exc)
            return False

    async def send(self, audio: bytes) -> None:
        """Forward a raw µ-law audio chunk to Deepgram."""
        if not self._connected or self._connection is None:
            return
        try:
            await self._connection.send_media(audio)
        except Exception as exc:
            stt_pipeline_log.warning("Deepgram send error: %s", exc)

    async def finish(self) -> None:
        """Signal end of audio stream and close Deepgram connection."""
        self._connected = False
        if self._connection is not None:
            try:
                await self._connection.send_close_stream()
            except Exception as exc:
                stt_pipeline_log.warning("Deepgram close stream error: %s", exc)

        if self._listen_task is not None:
            try:
                await asyncio.wait_for(self._listen_task, timeout=3.0)
            except (asyncio.TimeoutError, Exception):
                self._listen_task.cancel()

        if self._ctx_manager is not None:
            try:
                await self._ctx_manager.__aexit__(None, None, None)
            except Exception:
                pass
