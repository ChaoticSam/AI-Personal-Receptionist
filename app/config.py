import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
APP_ENV = os.getenv("APP_ENV", "development")

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EMBEDDING_MODEL = "text-embedding-3-small"
CHEAP_MODEL = "gpt-4o-mini"
SMART_MODEL = "gpt-4.1"
EMBEDDING_DIMENSIONS = 1536

# LLM Provider — "openai" (default) or "groq"
LLM_PROVIDER     = os.getenv("LLM_PROVIDER", "openai")
GROQ_API_KEY     = os.getenv("GROQ_API_KEY", "")
GROQ_CHEAP_MODEL = os.getenv("GROQ_CHEAP_MODEL", "llama-3.1-8b-instant")
GROQ_SMART_MODEL = os.getenv("GROQ_SMART_MODEL", "llama-3.3-70b-versatile")

# Twilio (WhatsApp notifications)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
NOTIFICATION_MAX_RETRIES = int(os.getenv("NOTIFICATION_MAX_RETRIES", "3"))

# Voice Gateway
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5")
SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "http://localhost:8000")
