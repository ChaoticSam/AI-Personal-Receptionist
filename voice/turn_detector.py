"""
TurnDetector — decides when a customer has finished their turn.

MVP strategy: Trust Deepgram's speech_final signal exclusively.
  When Deepgram emits speech_final=True the transcript is complete and the
  AI turn begins. No additional silence timer is needed.

Production upgrade path:
  - Hybrid: speech_final OR vad_engine.threshold_exceeded() as backup.
  - Configurable via voice_config.silence_threshold_ms.
"""

import asyncio
from typing import Callable, Awaitable


class TurnDetector:
    def __init__(
        self,
        on_turn_end: Callable[[str], Awaitable[None]],
        silence_threshold_ms: int = 1000,
    ):
        self._on_turn_end = on_turn_end
        self.silence_threshold_ms = silence_threshold_ms
        self._pending_transcript: str = ""

    async def on_interim(self, text: str) -> None:
        """Accumulate interim (non-final) transcript words for context."""
        self._pending_transcript = text

    async def on_final(self, text: str) -> None:
        """
        Called when Deepgram signals speech_final=True.
        Fires the on_turn_end callback with the complete utterance.
        """
        if text.strip():
            self._pending_transcript = ""
            await self._on_turn_end(text.strip())
