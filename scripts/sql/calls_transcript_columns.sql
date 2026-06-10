-- Adds ElevenLabs ConvAI linkage + captured transcript to calls.
-- conversation_id : ElevenLabs conversation id (links a call to its ConvAI session)
-- transcript      : full turn-by-turn transcript [{role, message, time_in_call_secs}, ...]
-- summary         : ElevenLabs post-call transcript summary
ALTER TABLE calls
  ADD COLUMN IF NOT EXISTS conversation_id VARCHAR(128),
  ADD COLUMN IF NOT EXISTS transcript JSONB,
  ADD COLUMN IF NOT EXISTS summary TEXT;

CREATE INDEX IF NOT EXISTS ix_calls_conversation_id ON calls (conversation_id);
