-- Per-tenant ElevenLabs ConvAI agent mapping (run once on existing DBs)
ALTER TABLE businesses
  ADD COLUMN IF NOT EXISTS elevenlabs_agent_id VARCHAR(128),
  ADD COLUMN IF NOT EXISTS convai_llm_model VARCHAR(128),
  ADD COLUMN IF NOT EXISTS convai_voice_id VARCHAR(128);
