"""
VoiceSessionManager — in-memory registry of active voice call sessions.

Keyed by Twilio call_sid (not our internal call UUID) because the
WebSocket start event delivers call_sid before we create the DB record.
"""

from voice.call_session import VoiceCallSession


class VoiceSessionManager:
    def __init__(self):
        self._sessions: dict[str, VoiceCallSession] = {}

    def add(self, call_sid: str, session: VoiceCallSession) -> None:
        self._sessions[call_sid] = session
        print(f"[VoiceSessionManager] Added session: {call_sid} | total={len(self._sessions)}")

    def get(self, call_sid: str) -> VoiceCallSession | None:
        return self._sessions.get(call_sid)

    def remove(self, call_sid: str) -> None:
        if call_sid in self._sessions:
            del self._sessions[call_sid]
            print(f"[VoiceSessionManager] Removed session: {call_sid} | total={len(self._sessions)}")

    def active_count(self) -> int:
        return len(self._sessions)


# Module-level singleton
voice_session_manager = VoiceSessionManager()
