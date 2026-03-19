"""
InterruptHandler — stops TTS when user speaks mid-response.

MVP: Stub. Interruption detection is disabled.
     The AI will always finish speaking before listening again.

Production upgrade path:
  - While VoiceState=SPEAKING, still forward audio to Deepgram (or local VAD).
  - When speech energy detected:
      1. Set a stop_speaking flag on the TTS stream.
      2. Send Twilio "clear" event to flush buffered audio.
      3. Switch session state to LISTENING.
  - Requires async signalling between the media loop and TTS streaming task.
"""

import asyncio


class InterruptHandler:
    def __init__(self):
        self._stop_event: asyncio.Event = asyncio.Event()

    def arm(self) -> None:
        """Reset interrupt state — call before each TTS stream starts."""
        self._stop_event.clear()

    def trigger(self) -> None:
        """Signal that the user started speaking — stop TTS."""
        self._stop_event.set()

    def is_triggered(self) -> bool:
        return self._stop_event.is_set()

    async def wait(self) -> None:
        """Await interrupt signal."""
        await self._stop_event.wait()

    async def send_clear_to_twilio(self, ws, stream_sid: str) -> None:
        """Send Twilio clear event to flush audio buffer on caller's phone."""
        try:
            await ws.send_json({"event": "clear", "streamSid": stream_sid})
        except Exception as e:
            print(f"[InterruptHandler] Failed to send clear: {e}")
