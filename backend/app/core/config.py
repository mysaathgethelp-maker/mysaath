from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Database
    DATABASE_URL: str = ""

    # Groq
    GROQ_API_KEY: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "llama3-8b-8192"

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── Razorpay ──────────────────────────────────────────────────────────────
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    RAZORPAY_PLAN_ID: str = ""   # Optional: pre-create in dashboard and set here

    # Plan limits
    FREE_MEMORY_LIMIT: int = 10
    FREE_CHAT_DAILY_LIMIT: int = 20
    PREMIUM_CHAT_DAILY_LIMIT: int = 200

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
