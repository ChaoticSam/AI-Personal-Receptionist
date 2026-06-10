"""ElevenLabs listing APIs for tenant dashboard (voices + LLM models)."""

from fastapi import APIRouter, Depends

from app.db.dependencies import get_current_user
from app.services.elevenlabs_platform import list_llm_models_sync, list_voices_sync

router = APIRouter(tags=["elevenlabs"])


@router.get("/voice/voices")
def list_voices(current_user=Depends(get_current_user)):
    """All ElevenLabs voices available to the workspace (any language)."""
    return list_voices_sync()


@router.get("/voice/llm-models")
def list_llm_models(current_user=Depends(get_current_user)):
    """LLM models available for ConvAI agents in this workspace."""
    return list_llm_models_sync()
