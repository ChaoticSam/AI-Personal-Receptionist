"""
Tests for the call-transcript pipeline that do NOT require a database:

  1. normalize_transcript() reduces an ElevenLabs payload to clean turns
  2. _format_duration() formats seconds as M:SS
  3. Webhook HMAC signature verification accepts a correct signature and
     rejects a tampered one
  4. POST /webhooks/elevenlabs/post-call returns 401 on a bad signature and
     200 (ignored) for a non-transcription event — exercised via TestClient

Run:  .venv/bin/python scripts/test_transcript_pipeline.py
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sys

from fastapi.testclient import TestClient

import app.api.webhooks as webhooks
from app.services.call_service import _coerce_duration_secs
from app.services.elevenlabs_platform import normalize_transcript

GREEN, RED, RESET = "\033[92m", "\033[91m", "\033[0m"
_failures = 0


def check(name, cond):
    global _failures
    if cond:
        print(f"{GREEN}  PASS{RESET}  {name}")
    else:
        print(f"{RED}  FAIL{RESET}  {name}")
        _failures += 1


SAMPLE = {
    "type": "post_call_transcription",
    "event_timestamp": 1739537297,
    "data": {
        "conversation_id": "conv_test_123",
        "agent_id": "agent_1",
        "status": "done",
        "transcript": [
            {"role": "agent", "message": "Hello, how can I help?", "time_in_call_secs": 0},
            {"role": "user", "message": "What products do you have?", "time_in_call_secs": 4},
            {"role": "agent", "message": None, "time_in_call_secs": 6, "tool_calls": [{"x": 1}]},
            {"role": "agent", "message": "We have mugs and frames.", "time_in_call_secs": 8},
        ],
        "metadata": {"call_duration_secs": 125, "start_time_unix_secs": 1739537000},
        "analysis": {"transcript_summary": "Customer asked about products."},
    },
}


def sign(secret, body_bytes):
    ts = "1739537300"
    payload = f"{ts}.{body_bytes.decode()}"
    digest = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v0={digest}"


def main():
    print("\n=== Transcript pipeline tests (no DB) ===\n")

    print("[1] normalize_transcript")
    turns = normalize_transcript(SAMPLE["data"])
    check("drops tool-only/empty turns (4 -> 3)", len(turns) == 3)
    check("roles normalized", [t["role"] for t in turns] == ["agent", "user", "agent"])
    check("keeps time_in_call_secs", turns[1]["time_in_call_secs"] == 4)

    print("\n[2] _coerce_duration_secs")
    check("125 -> 125", _coerce_duration_secs(125) == 125)
    check("'9' -> 9", _coerce_duration_secs("9") == 9)
    check("None -> None", _coerce_duration_secs(None) is None)
    check("-1 -> None", _coerce_duration_secs(-1) is None)

    print("\n[3] HMAC signature verification")
    secret = "whsec_test_secret"
    webhooks.ELEVENLABS_WEBHOOK_SECRET = secret
    body = json.dumps(SAMPLE).encode()
    good_sig = sign(secret, body)
    check("accepts valid signature", webhooks._verify_signature(body, good_sig) is True)
    check("rejects tampered body", webhooks._verify_signature(body + b"x", good_sig) is False)
    check("rejects missing header", webhooks._verify_signature(body, None) is False)
    check("rejects malformed header", webhooks._verify_signature(body, "garbage") is False)

    print("\n[4] Webhook endpoint (TestClient)")
    # Build app fresh so the patched secret is in effect for the route too.
    import main
    client = TestClient(main.app)

    r = client.post(
        "/webhooks/elevenlabs/post-call",
        content=body,
        headers={"elevenlabs-signature": "t=1,v0=deadbeef", "content-type": "application/json"},
    )
    check("bad signature -> 401", r.status_code == 401)

    ignored = json.dumps({"type": "post_call_audio", "data": {}}).encode()
    r2 = client.post(
        "/webhooks/elevenlabs/post-call",
        content=ignored,
        headers={"elevenlabs-signature": sign(secret, ignored), "content-type": "application/json"},
    )
    check("non-transcription event -> 200 ignored", r2.status_code == 200 and r2.json().get("ignored") == "post_call_audio")

    print()
    if _failures:
        print(f"{RED}=== {_failures} test(s) FAILED ==={RESET}\n")
        return 1
    print(f"{GREEN}=== All transcript pipeline tests passed ==={RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
