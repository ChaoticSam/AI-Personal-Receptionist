from fastapi import FastAPI
from app.api.calls import router as calls_router
from app.api.orders import router as orders_router
from app.api.business import router as business_router
from app.api.products import router as products_router
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.agent_tools import router as agent_tools_router
from app.api.voice import router as voice_router
from app.api.voice_pipeline import router as voice_pipeline_router
from app.api.webhooks import router as webhooks_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(calls_router)
app.include_router(orders_router)
app.include_router(business_router)
app.include_router(products_router)
app.include_router(agent_tools_router)
app.include_router(voice_router)
app.include_router(voice_pipeline_router)
app.include_router(webhooks_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}