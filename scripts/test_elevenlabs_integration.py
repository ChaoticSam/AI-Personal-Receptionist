"""
Smoke test for the ElevenLabs integration.

Verifies, against the live ElevenLabs API using the workspace key in .env:
  1. ELEVENLABS_API_KEY is configured
  2. Voices can be listed (GET /v1/voices)
  3. ConvAI LLM models can be listed (GET /v1/convai/llm/list)
  4. The configured agent can be fetched (GET /v1/convai/agents/{id})
  5. Recent conversations can be listed and one transcript fetched
     (GET /v1/convai/conversations[/{id}])

Run:  .venv/bin/python scripts/test_elevenlabs_integration.py

Exit code is non-zero if any *required* check fails (1-4). Conversation
checks (5) are informational — a brand-new agent may have zero calls.
"""

from __future__ import annotations

import sys

from app.config import ELEVENLABS_API_KEY
import os

from app.services.elevenlabs_platform import (
    get_agent_sync,
    get_conversation_sync,
    list_conversations_sync,
    list_llm_models_sync,
    list_voices_sync,
    normalize_transcript,
)

AGENT_ID = os.getenv("ELEVENLABS_CONVAI_AGENT_ID", "").strip()

GREEN, RED, YELLOW, DIM, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[2m", "\033[0m"


def ok(msg: str) -> None:
    print(f"{GREEN}  PASS{RESET}  {msg}")


def fail(msg: str) -> None:
    print(f"{RED}  FAIL{RESET}  {msg}")


def warn(msg: str) -> None:
    print(f"{YELLOW}  WARN{RESET}  {msg}")


def main() -> int:
    failures = 0
    print("\n=== ElevenLabs integration smoke test ===\n")

    # 1. API key
    print("[1] API key")
    if ELEVENLABS_API_KEY:
        ok(f"ELEVENLABS_API_KEY present ({ELEVENLABS_API_KEY[:6]}…, len={len(ELEVENLABS_API_KEY)})")
    else:
        fail("ELEVENLABS_API_KEY is empty — set it in .env")
        return 1  # nothing else can pass

    # 2. Voices
    print("\n[2] List voices  GET /v1/voices")
    voices = list_voices_sync()
    if voices:
        ok(f"{len(voices)} voices available. e.g. {voices[0]['name']} ({voices[0]['voice_id']})")
    else:
        fail("No voices returned — key invalid or no workspace access")
        failures += 1

    # 3. LLM models
    print("\n[3] List ConvAI LLM models  GET /v1/convai/llm/list")
    models = list_llm_models_sync()
    if models:
        ok(f"{len(models)} models: {', '.join(m['id'] for m in models[:6])}{' …' if len(models) > 6 else ''}")
    else:
        warn("No LLM models returned (may be plan-dependent)")

    # 4. Agent
    print(f"\n[4] Get agent  GET /v1/convai/agents/{{id}}")
    if not AGENT_ID:
        warn("ELEVENLABS_CONVAI_AGENT_ID not set — skipping agent fetch")
    else:
        agent = get_agent_sync(AGENT_ID)
        if agent:
            cc = agent.get("conversation_config") or {}
            ag = (cc.get("agent") or {})
            llm = ((ag.get("prompt") or {}).get("llm"))
            ok(f"Agent '{agent.get('name', AGENT_ID)}' — llm={llm}, voice={(cc.get('tts') or {}).get('voice_id')}")
        else:
            fail(f"Could not fetch agent {AGENT_ID}")
            failures += 1

    # 5. Conversations + transcript (informational)
    print("\n[5] Conversations + transcript  GET /v1/convai/conversations")
    convos = list_conversations_sync(agent_id=AGENT_ID or None, page_size=5)
    if not convos:
        warn("No conversations found yet (agent may not have taken any calls).")
    else:
        ok(f"{len(convos)} recent conversation(s) listed.")
        cid = convos[0].get("conversation_id") or convos[0].get("id")
        if cid:
            detail = get_conversation_sync(cid)
            if detail:
                turns = normalize_transcript(detail)
                summary = ((detail.get("analysis") or {}).get("transcript_summary")) or "(none)"
                ok(f"Fetched transcript for {cid}: {len(turns)} turns, status={detail.get('status')}")
                print(f"{DIM}        summary: {summary[:120]}{RESET}")
                for t in turns[:4]:
                    print(f"{DIM}        {t['role']:>5}: {t['message'][:80]}{RESET}")
            else:
                warn(f"Could not fetch transcript detail for {cid}")

    print()
    if failures:
        print(f"{RED}=== {failures} required check(s) FAILED ==={RESET}\n")
        return 1
    print(f"{GREEN}=== All required checks passed ==={RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
