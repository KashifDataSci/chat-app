from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine, base

# Import all models so SQLAlchemy registers them before create_all
from app.models import user, otp, chat, participant  # noqa: F401

from app.routers import chat as chat_router
from app.routers import user as user_router
from app.routers import auth as auth_router

app = FastAPI(
    title="Chat Backend API",
    version="1.0.0",
    root_path="/api",
)

# ── CORS ────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Create DB tables ─────────────────────────────────────────
base.metadata.create_all(bind=engine)

# ── Routers ──────────────────────────────────────────────────
app.include_router(chat_router.router)
app.include_router(user_router.router)
app.include_router(auth_router.router)


# ── Health check ─────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {
        "message": "Chat Backend API v2.0 is running",
        "docs": "/api/docs",
    }