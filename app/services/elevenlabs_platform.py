"""
ElevenLabs platform API — list voices/LLMs and sync per-tenant ConvAI agent settings.

No custom STT/LLM/TTS stack: configuration is pushed to ElevenLabs agents only.
"""

from __future__ import annotations

import copy
import logging
from typing import Any

import httpx

from app.config import ELEVENLABS_API_KEY
from app.models.business import Business

logger = logging.getLogger(__name__)

BASE = "https://api.elevenlabs.io/v1"


def _headers() -> dict[str, str]:
    return {"xi-api-key": ELEVENLABS_API_KEY or ""}


def list_voices_sync() -> list[dict[str, Any]]:
    """All voices available to the workspace (any language)."""
    if not ELEVENLABS_API_KEY:
        return []
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.get(f"{BASE}/voices", headers=_headers())
            if r.status_code != 200:
                logger.warning("ElevenLabs voices: %s %s", r.status_code, r.text[:300])
                return []
            data = r.json()
    except Exception as exc:
        logger.warning("ElevenLabs voices request failed: %s", exc)
        return []

    out = []
    for v in data.get("voices", []):
        out.append(
            {
                "voice_id": v.get("voice_id", ""),
                "name": v.get("name", ""),
                "category": v.get("category", ""),
                "preview_url": v.get("preview_url", ""),
                "labels": v.get("labels") or {},
            }
        )
    out.sort(key=lambda x: (x.get("name") or "").lower())
    return out


def list_llm_models_sync() -> list[dict[str, Any]]:
    """Models available for ConvAI agents in this workspace."""
    if not ELEVENLABS_API_KEY:
        return []
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.get(f"{BASE}/convai/llm/list", headers=_headers())
            if r.status_code != 200:
                logger.warning("ElevenLabs LLM list: %s %s", r.status_code, r.text[:300])
                return []
            data = r.json()
    except Exception as exc:
        logger.warning("ElevenLabs LLM list failed: %s", exc)
        return []

    # API shape may be { "models": [...] } or a raw list — normalize
    if isinstance(data, list):
        raw = data
    else:
        raw = data.get("models") or data.get("llms") or []

    normalized = []
    for m in raw:
        if isinstance(m, str):
            normalized.append({"id": m, "name": m})
        elif isinstance(m, dict):
            mid = m.get("model_id") or m.get("id") or m.get("name")
            if mid:
                normalized.append(
                    {
                        "id": str(mid),
                        "name": m.get("name") or m.get("display_name") or str(mid),
                    }
                )
    return normalized


def get_conversation_sync(conversation_id: str) -> dict[str, Any] | None:
    """Full conversation detail incl. transcript/metadata/analysis for one conversation."""
    if not ELEVENLABS_API_KEY or not conversation_id:
        return None
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.get(
                f"{BASE}/convai/conversations/{conversation_id}",
                headers=_headers(),
            )
            if r.status_code != 200:
                logger.warning(
                    "ElevenLabs get conversation: %s %s", r.status_code, r.text[:300]
                )
                return None
            return r.json()
    except Exception as exc:
        logger.warning("ElevenLabs get conversation failed: %s", exc)
        return None


def list_conversations_sync(
    agent_id: str | None = None, page_size: int = 30
) -> list[dict[str, Any]]:
    """Recent conversations for the workspace (optionally filtered by agent)."""
    if not ELEVENLABS_API_KEY:
        return []
    params: dict[str, Any] = {"page_size": max(1, min(page_size, 100))}
    if agent_id:
        params["agent_id"] = agent_id
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.get(
                f"{BASE}/convai/conversations", headers=_headers(), params=params
            )
            if r.status_code != 200:
                logger.warning(
                    "ElevenLabs list conversations: %s %s", r.status_code, r.text[:300]
                )
                return []
            data = r.json()
    except Exception as exc:
        logger.warning("ElevenLabs list conversations failed: %s", exc)
        return []
    if isinstance(data, list):
        return data
    return data.get("conversations") or []


def normalize_transcript(convo: dict[str, Any]) -> list[dict[str, Any]]:
    """Reduce an ElevenLabs conversation payload's transcript to {role, message, time_in_call_secs}."""
    turns = []
    for t in convo.get("transcript") or []:
        msg = t.get("message")
        if msg is None:
            continue  # skip tool-only / empty turns
        role = t.get("role") or "agent"
        turns.append(
            {
                "role": "user" if role == "user" else "agent",
                "message": str(msg),
                "time_in_call_secs": t.get("time_in_call_secs"),
            }
        )
    return turns


def get_agent_sync(agent_id: str) -> dict[str, Any] | None:
    if not ELEVENLABS_API_KEY or not agent_id:
        return None
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.get(f"{BASE}/convai/agents/{agent_id}", headers=_headers())
            if r.status_code != 200:
                logger.warning("ElevenLabs get agent: %s %s", r.status_code, r.text[:300])
                return None
            return r.json()
    except Exception as exc:
        logger.warning("ElevenLabs get agent failed: %s", exc)
        return None


def patch_agent_sync(agent_id: str, body: dict[str, Any]) -> tuple[bool, str | None]:
    if not ELEVENLABS_API_KEY or not agent_id:
        return False, "missing_api_key_or_agent_id"
    try:
        with httpx.Client(timeout=60.0) as client:
            r = client.patch(
                f"{BASE}/convai/agents/{agent_id}",
                headers={**_headers(), "Content-Type": "application/json"},
                json=body,
            )
            if r.status_code not in (200, 201):
                return False, r.text[:500]
            return True, None
    except Exception as exc:
        logger.warning("ElevenLabs patch agent failed: %s", exc)
        return False, str(exc)


def merge_and_sync_agent_from_business(business: Business) -> tuple[bool, str | None]:
    """
    Push tenant fields to the ElevenLabs agent: LLM, TTS voice, first message, language.
    Preserves existing conversation_config (including system prompt) via GET-merge-PATCH.
    """
    aid = (business.elevenlabs_agent_id or "").strip()
    if not aid:
        return True, None

    existing = get_agent_sync(aid)
    if not existing:
        return False, "elevenlabs_get_agent_failed"

    cc = copy.deepcopy(existing.get("conversation_config") or {})
    if "agent" not in cc:
        cc["agent"] = {}
    if "prompt" not in cc["agent"]:
        cc["agent"]["prompt"] = {}

    ui = business.voice_config or {}
    if business.convai_llm_model:
        cc["agent"]["prompt"]["llm"] = business.convai_llm_model.strip()

    fm = ui.get("first_message")
    if fm is not None:
        cc["agent"]["first_message"] = str(fm).strip()
    lang = ui.get("language")
    if lang:
        cc["agent"]["language"] = str(lang).strip()[:12]

    if "tts" not in cc:
        cc["tts"] = {}
    if business.convai_voice_id:
        cc["tts"]["voice_id"] = business.convai_voice_id.strip()

    ok, err = patch_agent_sync(aid, {"conversation_config": cc})
    return ok, err
