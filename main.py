from fastapi import FastAPI

# Import all models so SQLAlchemy registers them with Base before any DB operation
from app.models import business, customer, order, product, call, user  # noqa: F401
from app.models import ai_interaction, product_embedding, order_customization, notification  # noqa: F401

from app.api.calls import router as calls_router
from app.api.orders import router as orders_router
from app.api.business import router as business_router
from app.api.products import router as products_router
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.call_session import router as call_session_router
from voice.gateway import router as voice_gateway_router
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
app.include_router(call_session_router)
app.include_router(orders_router)
app.include_router(business_router)
app.include_router(products_router)
app.include_router(voice_gateway_router)

@app.get("/")
def root():
    return {"message": "Hello, World!"}

@app.get("/health")
def health_check():
    return {"status": "ok"}