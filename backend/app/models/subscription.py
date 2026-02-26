import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class PlanType(str, enum.Enum):
    free = "free"
    premium = "premium"


class SubscriptionStatus(str, enum.Enum):
    active = "active"
    canceled = "canceled"
    expired = "expired"
    pending = "pending"      # Razorpay order created, awaiting first payment
    paused = "paused"        # Razorpay paused billing (e.g. card soft-decline retry)
    halted = "halted"        # Razorpay halted after max retries exhausted


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    plan_type = Column(Enum(PlanType), default=PlanType.free, nullable=False)
    status = Column(
        Enum(SubscriptionStatus),
        default=SubscriptionStatus.active,
        nullable=False,
        index=True,
    )

    # Razorpay identifiers
    razorpay_subscription_id = Column(String(100), nullable=True, unique=True, index=True)
    razorpay_customer_id = Column(String(100), nullable=True)

    # Billing period (populated by webhook on payment.captured)
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)

    # Audit – last raw webhook payload stored for debugging/replay
    last_webhook_event = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="subscription")
