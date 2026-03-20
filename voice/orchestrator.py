"""
Orchestrator — bridges the voice layer to the AI conversation engine.

Responsibilities per customer turn:
  1. Guard: drop turns if session is not LISTENING.
  2. Set state → PROCESSING.
  3. Call conversation_engine.process() (existing AI pipeline — unchanged).
  4. Set state → SPEAKING.
  5. Stream TTS response to Twilio WebSocket.
  6. Set state → LISTENING (always, even on error).

Also handles:
  - initialize_call(): create DB call/customer records + AI session.
  - send_greeting(): stream opening message when call connects.
  - end_call(): persist transcript and clean up AI session.
"""

from typing import TYPE_CHECKING

from app.db.session import SessionLocal
from app.core.session_manager import session_manager
from app.ai.conversation_engine import conversation_engine
from app.services.customer_service import find_or_create_customer
from app.services.call_service import create_call, end_call as db_end_call

from voice.call_session import VoiceCallSession, VoiceState
from voice.tts.elevenlabs_stream import stream_tts_to_twilio

if TYPE_CHECKING:
    from fastapi import WebSocket

_DEFAULT_GREETING = "Hi, I am Sarah. Thank you for calling {business_name}. How can I help you?"


class Orchestrator:

    # ── Call lifecycle ──────────────────────────────────────────────────────

    async def initialize_call(self, voice_session: VoiceCallSession) -> None:
        """
        Create DB customer + call records, then register an AI session.
        Called once when the Twilio 'start' event is received.
        """
        db = SessionLocal()
        try:
            customer = find_or_create_customer(
                db,
                business_id=voice_session.business_id,
                phone=voice_session.caller_phone,
                name=None,
                email=None,
                notes=None,
            )

            call = create_call(
                db,
                business_id=voice_session.business_id,
                customer_id=customer.id,
                caller_phone=voice_session.caller_phone,
                call_sid=voice_session.call_sid,
            )

            voice_session.db_call_id     = str(call.id)
            voice_session.db_customer_id = str(customer.id)

            session_manager.create_session(
                call_id=str(call.id),
                business_id=str(voice_session.business_id),
                customer_id=str(customer.id),
            )

            print(
                f"[Orchestrator] Call initialized: "
                f"call_id={call.id} customer_id={customer.id}"
            )
        except Exception as exc:
            print(f"[Orchestrator] initialize_call error: {exc}")
        finally:
            db.close()

    async def send_greeting(
        self,
        voice_session: VoiceCallSession,
        ws: "WebSocket",
    ) -> None:
        """Stream the opening greeting to the caller immediately after connect."""
        voice_cfg = voice_session.voice_config or {}
        greeting  = voice_cfg.get("greeting_message") or _DEFAULT_GREETING

        # Resolve {business_name} placeholder — works in both default and custom greetings
        business_name = "our store"
        try:
            from app.db.session import SessionLocal as _SL
            from app.services.business_service import get_business_by_id as _get_biz
            _db = _SL()
            try:
                biz = _get_biz(_db, voice_session.business_id)
                if biz and biz.name:
                    business_name = biz.name
            finally:
                _db.close()
        except Exception:
            pass

        greeting = greeting.replace("{business_name}", business_name)

        voice_session.state = VoiceState.SPEAKING
        print(f"[Orchestrator] Sending greeting: {greeting!r}")
        try:
            await stream_tts_to_twilio(
                text       = greeting,
                ws         = ws,
                stream_sid = voice_session.stream_sid,
                voice_id   = voice_cfg.get("tts_voice_id") or None,
            )
        except Exception as exc:
            print(f"[Orchestrator] Greeting TTS error: {exc}")
        finally:
            voice_session.state = VoiceState.LISTENING
            print(f"[Orchestrator] Greeting done — state set to LISTENING")

    async def end_call(self, voice_session: VoiceCallSession) -> None:
        """Persist transcript to DB and remove the AI session."""
        call_id = voice_session.db_call_id
        if not call_id:
            return

        db = SessionLocal()
        try:
            ai_session = session_manager.get_session(call_id)
            transcript: str | None = None

            if ai_session:
                msgs       = ai_session.conversation_history
                transcript = "\n".join(
                    f"{m['role'].upper()}: {m['message']}" for m in msgs
                )

            db_end_call(db, call_id=call_id, transcript=transcript)
            session_manager.end_session(call_id)
            print(f"[Orchestrator] Call ended: call_id={call_id}")
        except Exception as exc:
            print(f"[Orchestrator] end_call error: {exc}")
        finally:
            db.close()

    # ── Per-turn processing ─────────────────────────────────────────────────

    async def handle_turn(
        self,
        transcript: str,
        voice_session: VoiceCallSession,
        ws: "WebSocket",
    ) -> None:
        """
        Process a complete customer turn:
          transcript → AI engine → TTS → Twilio.

        Drops the turn silently if the session is not in LISTENING state
        (e.g. AI is still speaking from the previous turn).
        """
        if voice_session.state != VoiceState.LISTENING:
            print(
                f"[Orchestrator] Turn dropped (state={voice_session.state}): "
                f"{transcript!r}"
            )
            return

        print(f"[Orchestrator] Turn received: {transcript!r}")
        voice_session.state = VoiceState.PROCESSING

        db = SessionLocal()
        try:
            ai_session = session_manager.get_session(voice_session.db_call_id or "")
            if not ai_session:
                print(f"[Orchestrator] No AI session for call_id={voice_session.db_call_id}")
                voice_session.state = VoiceState.LISTENING
                return

            # Run the full AI pipeline (intent → slots → product match → response)
            result = conversation_engine.process(
                customer_message = transcript,
                session          = ai_session,
                db               = db,
                business_context = "",
            )

            print(f"[Orchestrator] AI response: {result.response!r}")

        except Exception as exc:
            print(f"[Orchestrator] AI engine error: {exc}")
            result = None

        finally:
            db.close()

        # ── TTS ──────────────────────────────────────────────────────────
        voice_session.state = VoiceState.SPEAKING
        try:
            response_text = result.response if result else (
                "I'm sorry, I had some trouble understanding that. Could you repeat?"
            )
            voice_cfg = voice_session.voice_config or {}
            await stream_tts_to_twilio(
                text       = response_text,
                ws         = ws,
                stream_sid = voice_session.stream_sid,
                voice_id   = voice_cfg.get("tts_voice_id") or None,
            )
        except Exception as exc:
            print(f"[Orchestrator] TTS error: {exc}")
        finally:
            voice_session.state = VoiceState.LISTENING


# Module-level singleton
orchestrator = Orchestrator()
