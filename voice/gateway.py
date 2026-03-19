"""
Voice Gateway — the real-time runtime engine for AI voice calls.

Two endpoints:

1. POST /calls/voice-webhook
   ─────────────────────────
   Twilio calls this when someone dials your registered phone number.
   We look up the business, then return TwiML instructing Twilio to open
   a Media Stream WebSocket to /voice/stream.

2. WebSocket /voice/stream
   ────────────────────────
   Twilio connects here and streams raw µ-law 8kHz audio in real-time.

   Message loop:
     'start'  → parse call_sid / business_id / caller_phone
                 → initialize DB records (customer + call)
                 → connect Deepgram STT
                 → send greeting TTS
     'media'  → forward raw audio to Deepgram (only while LISTENING)
     'stop'   → finish Deepgram, persist transcript, clean up session

   Transcript flow (via asyncio.Queue):
     Deepgram fires on_final_transcript callback
       → queued → transcript_processor task picks it up
       → orchestrator.handle_turn(transcript) → AI engine → TTS → Twilio
"""

import asyncio
import base64
import json
from typing import List

import httpx
from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.config import SERVER_BASE_URL, ELEVENLABS_API_KEY
from app.db.dependencies import get_db, get_current_user
from app.services.business_service import get_business_by_phone

from voice.call_session import VoiceCallSession, VoiceState
from voice.session_manager import voice_session_manager
from voice.stt.deepgram_stream import DeepgramStream
from voice.orchestrator import orchestrator

router = APIRouter(tags=["voice-gateway"])


# ── 1. TwiML Webhook ────────────────────────────────────────────────────────

@router.post("/calls/voice-webhook")
async def voice_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Twilio calls this endpoint when someone dials your Twilio number.
    Returns TwiML that connects the call to the Media Stream WebSocket.

    Twilio form fields used:
      From     – caller's E.164 phone number
      To       – your Twilio number (used to look up the business)
      CallSid  – unique call identifier
    """
    form       = await request.form()
    caller     = form.get("From", "")
    twilio_to  = form.get("To", "")
    call_sid   = form.get("CallSid", "")

    business = get_business_by_phone(db, twilio_to)
    if not business:
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            "<Say>Sorry, this number is not registered with our system. Goodbye.</Say>"
            "<Hangup/>"
            "</Response>"
        )
        return Response(content=twiml, media_type="application/xml")

    # Build wss:// URL from SERVER_BASE_URL
    base   = (SERVER_BASE_URL or "http://localhost:8000").rstrip("/")
    ws_url = base.replace("https://", "wss://").replace("http://", "ws://") + "/voice/stream"

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{ws_url}">
      <Parameter name="business_id"  value="{business.id}"/>
      <Parameter name="caller_phone" value="{caller}"/>
      <Parameter name="call_sid"     value="{call_sid}"/>
    </Stream>
  </Connect>
</Response>"""

    print(f"[Gateway] Webhook: caller={caller} → business={business.name} ws={ws_url}")
    return Response(content=twiml, media_type="application/xml")


# ── 2. ElevenLabs Voice List ─────────────────────────────────────────────────

@router.get("/voice/voices")
async def list_voices(current_user=Depends(get_current_user)):
    """
    Fetch ElevenLabs voices filtered to Hindi and English only.
    Returned order: Hindi voices first (alphabetical), then English voices (alphabetical).
    """
    if not ELEVENLABS_API_KEY:
        return []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.elevenlabs.io/v1/voices",
                headers={"xi-api-key": ELEVENLABS_API_KEY},
            )
            if response.status_code != 200:
                print(f"[Voice] ElevenLabs returned {response.status_code}: {response.text[:200]}")
                return []

            data = response.json()
            hindi   = []

            for v in data.get("voices", []):
                labels   = v.get("labels") or {}
                language = labels.get("language", "en").lower()

                if language not in ("hi"):
                    continue

                entry = {
                    "voice_id":    v.get("voice_id", ""),
                    "name":        v.get("name", ""),
                    "category":    v.get("category", ""),
                    "preview_url": v.get("preview_url", ""),
                    "labels":      labels,
                }

                if language == "hi":
                    hindi.append(entry)

            # Sort each group alphabetically by name
            hindi.sort(key=lambda x: x["name"].lower())

            return hindi

    except Exception as exc:
        print(f"[Voice] Failed to fetch ElevenLabs voices: {exc}")
        return []


# ── 3. Media Stream WebSocket ─────────────────────────────────────────────────

@router.websocket("/voice/stream")
async def voice_stream(websocket: WebSocket):
    """
    Twilio Media Stream WebSocket.

    State machine per connection:
      LISTENING  → audio forwarded to Deepgram
      PROCESSING → AI engine running; audio dropped
      SPEAKING   → TTS streaming; audio dropped
    """
    await websocket.accept()

    voice_session : VoiceCallSession | None = None
    dg_stream     : DeepgramStream    | None = None
    transcript_q  : asyncio.Queue[str | None] = asyncio.Queue()
    processor_task: asyncio.Task | None = None

    # ── Transcript processor (background task) ──────────────────────────
    async def transcript_processor() -> None:
        """Drain transcript queue and handle turns sequentially."""
        while True:
            item = await transcript_q.get()
            if item is None:          # sentinel — time to stop
                break
            if voice_session:
                await orchestrator.handle_turn(item, voice_session, websocket)

    # ── Deepgram callback (called from Deepgram's async event loop) ─────
    async def on_final_transcript(text: str) -> None:
        await transcript_q.put(text)

    # ── Main WebSocket loop ─────────────────────────────────────────────
    try:
        processor_task = asyncio.create_task(transcript_processor())

        while True:
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                print("[Gateway] WebSocket disconnected by Twilio")
                break

            try:
                msg   = json.loads(raw)
            except json.JSONDecodeError:
                continue

            event = msg.get("event")

            # ── start ────────────────────────────────────────────────
            if event == "start":
                start_data  = msg.get("start", {})
                params      = start_data.get("customParameters", {})
                stream_sid  = start_data.get("streamSid", "")
                business_id = params.get("business_id", "")
                caller_phone= params.get("caller_phone", "")
                call_sid    = params.get("call_sid", "")

                print(
                    f"[Gateway] Stream started: sid={stream_sid} "
                    f"caller={caller_phone} business={business_id}"
                )

                # Load business voice config
                from app.db.session import SessionLocal
                from app.services.business_service import get_business_by_id
                _db = SessionLocal()
                try:
                    biz        = get_business_by_id(_db, business_id)
                    voice_cfg  = (biz.voice_config if biz else None) or {}
                finally:
                    _db.close()

                voice_session = VoiceCallSession(
                    call_sid     = call_sid,
                    stream_sid   = stream_sid,
                    business_id  = business_id,
                    caller_phone = caller_phone,
                    voice_config = voice_cfg,
                )
                voice_session_manager.add(call_sid, voice_session)

                # Create DB records and AI session
                await orchestrator.initialize_call(voice_session)

                # Connect to Deepgram STT
                vc         = voice_session.voice_config
                dg_stream  = DeepgramStream(
                    on_final_transcript = on_final_transcript,
                    language            = vc.get("language", "en-IN"),
                    endpointing_ms      = vc.get("endpointing_ms", 300),
                )
                connected = await dg_stream.connect()
                if not connected:
                    print("[Gateway] Warning: Deepgram not connected — STT will not work")

                # Send greeting (non-blocking so media loop continues)
                asyncio.create_task(
                    orchestrator.send_greeting(voice_session, websocket)
                )

            # ── media ────────────────────────────────────────────────
            elif event == "media":
                if (
                    dg_stream
                    and voice_session
                    and voice_session.state == VoiceState.LISTENING
                ):
                    try:
                        audio = base64.b64decode(msg["media"]["payload"])
                        await dg_stream.send(audio)
                    except Exception as exc:
                        print(f"[Gateway] Audio forward error: {exc}")

            # ── stop ─────────────────────────────────────────────────
            elif event == "stop":
                sid = voice_session.call_sid if voice_session else "unknown"
                print(f"[Gateway] Stream stopped: call_sid={sid}")
                break

    except Exception as exc:
        print(f"[Gateway] Unexpected WebSocket error: {exc}")

    finally:
        # ── Teardown ────────────────────────────────────────────────
        # Signal transcript processor to exit
        await transcript_q.put(None)
        if processor_task:
            try:
                await asyncio.wait_for(processor_task, timeout=5.0)
            except (asyncio.TimeoutError, Exception):
                processor_task.cancel()

        # Close Deepgram
        if dg_stream:
            await dg_stream.finish()

        # Persist call transcript + end AI session
        if voice_session:
            voice_session.state = VoiceState.ENDED
            await orchestrator.end_call(voice_session)
            voice_session_manager.remove(voice_session.call_sid)

        print("[Gateway] Connection fully cleaned up")
