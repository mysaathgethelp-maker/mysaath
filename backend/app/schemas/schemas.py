from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime
from app.models.memory import MemoryType, MemoryPriority
from app.models.subscription import PlanType, SubscriptionStatus


# ── Auth ──────────────────────────────────────────────────────────────────────
class UserRegister(BaseModel):
    email: EmailStr
    password: str

    @validator("password")
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    created_at: datetime

    class Config:
        orm_mode = True


# ── Persona ───────────────────────────────────────────────────────────────────
class PersonaCreate(BaseModel):
    display_name: str
    speaking_style: Optional[str] = None
    core_traits: Optional[str] = None
    core_values: Optional[str] = None
    avatar_image_url: Optional[str] = None


class PersonaUpdate(BaseModel):
    display_name: Optional[str] = None
    speaking_style: Optional[str] = None
    core_traits: Optional[str] = None
    core_values: Optional[str] = None
    avatar_image_url: Optional[str] = None


class PersonaOut(BaseModel):
    id: int
    display_name: str
    speaking_style: Optional[str]
    core_traits: Optional[str]
    core_values: Optional[str]
    avatar_image_url: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True


# ── Memory ────────────────────────────────────────────────────────────────────
class MemoryCreate(BaseModel):
    memory_type: MemoryType
    content: str
    priority: MemoryPriority = MemoryPriority.medium

    @validator("content")
    def content_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Memory content cannot be empty")
        if len(v) > 2000:
            raise ValueError("Memory content must be under 2000 characters")
        return v.strip()


class MemoryUpdate(BaseModel):
    memory_type: Optional[MemoryType] = None
    content: Optional[str] = None
    priority: Optional[MemoryPriority] = None


class MemoryOut(BaseModel):
    id: int
    persona_id: int
    memory_type: MemoryType
    content: str
    priority: MemoryPriority
    created_at: datetime

    class Config:
        orm_mode = True


# ── Chat ──────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str

    @validator("message")
    def message_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Message cannot be empty")
        if len(v) > 1000:
            raise ValueError("Message must be under 1000 characters")
        return v.strip()


class ChatResponse(BaseModel):
    reply: str
    persona_name: str


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        orm_mode = True


# ── Subscription ──────────────────────────────────────────────────────────────
class SubscriptionOut(BaseModel):
    id: int
    plan_type: PlanType
    status: SubscriptionStatus
    razorpay_subscription_id: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    created_at: datetime

    class Config:
        orm_mode = True


class InitiateSubscriptionResponse(BaseModel):
    razorpay_subscription_id: str
    checkout_url: str
    status: str
