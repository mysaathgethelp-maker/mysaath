from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.db.session import engine
from app.db import base  # noqa: F401 - imports all models
from app.api.routes import auth, persona, memory, chat, subscription

@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup: tables are managed via Supabase migrations, not auto-create
    yield

app = FastAPI(
    title="MySaath",
    version="1.0.0",
    description="MySaath — अपनों की यादें, हमेशा साथ",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(persona.router, prefix="/api/persona", tags=["persona"])
app.include_router(memory.router, prefix="/api/memories", tags=["memories"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(subscription.router, prefix="/api/subscription", tags=["subscription"])

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "MySaath"}
