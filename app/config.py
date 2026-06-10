import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
APP_ENV = os.getenv("APP_ENV", "development")

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# Twilio (WhatsApp notifications)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
NOTIFICATION_MAX_RETRIES = int(os.getenv("NOTIFICATION_MAX_RETRIES", "3"))

# ElevenLabs — workspace API key (list voices/LLMs, PATCH agents per tenant)
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# Default/global ConvAI agent id (used for diagnostics and conversation lookups).
ELEVENLABS_CONVAI_AGENT_ID = os.getenv("ELEVENLABS_CONVAI_AGENT_ID", "")

# Shared secret for webhook tools (X-Agent-Key); all tenants use the same backend tools.
ELEVENLABS_AGENT_TOOL_SECRET = os.getenv("ELEVENLABS_AGENT_TOOL_SECRET", "")

# Shared secret for the ElevenLabs post-call webhook (HMAC validation of the
# `elevenlabs-signature` header). Leave empty to skip verification in dev.
ELEVENLABS_WEBHOOK_SECRET = os.getenv("ELEVENLABS_WEBHOOK_SECRET", "")
