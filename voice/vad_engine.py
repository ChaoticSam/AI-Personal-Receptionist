"""
VAD Engine — Voice Activity Detection.

MVP: We rely entirely on Deepgram's built-in endpointing / speech_final signal.
     Deepgram's VAD is production-grade and configurable via the endpointing_ms
     parameter passed at stream creation time.

     This class tracks consecutive silent chunks (for future local VAD) and
     exposes the business-configured silence threshold so that turn_detector.py
     can apply a secondary silence-based fallback if needed.

Production upgrade path:
  - Integrate webrtcvad (pip install webrtcvad) for frame-level local VAD.
  - Use as a pre-filter before sending audio to Deepgram.
  - Fire is_silent() signal to interrupt_handler.py during SPEAKING state.
"""

import time


class VADEngine:
    def __init__(self, silence_threshold_ms: int = 1000, vad_sensitivity: str = "medium"):
        self.silence_threshold_ms = silence_threshold_ms
        self.vad_sensitivity = vad_sensitivity

        self._last_speech_ts: float = time.monotonic()
        self._is_speaking: bool = False

    def on_speech_detected(self) -> None:
        """Call when audio energy indicates speech."""
        self._last_speech_ts = time.monotonic()
        self._is_speaking = True

    def on_silence_detected(self) -> None:
        """Call when audio energy falls below threshold."""
        self._is_speaking = False

    def silence_duration_ms(self) -> int:
        """Milliseconds since last speech detected."""
        return int((time.monotonic() - self._last_speech_ts) * 1000)

    def threshold_exceeded(self) -> bool:
        """True when silence has lasted longer than the configured threshold."""
        return not self._is_speaking and self.silence_duration_ms() >= self.silence_threshold_ms

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking
