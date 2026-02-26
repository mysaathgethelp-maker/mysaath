"""
billing_service.py
------------------
Business logic layer for subscriptions.
Calls razorpay_client for provider I/O.
Enforces plan limits for feature access.
"""

import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.subscription import Subscription, PlanType, SubscriptionStatus
from app.models.user import User
from app.core.config import settings
from app.services import razorpay_client as rzp


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_user_subscription(db: Session, user: User) -> Subscription:
    """Return the user's subscription, creating a free one if missing."""
    sub = user.subscription
    if not sub:
        sub = Subscription(
            user_id=user.id,
            plan_type=PlanType.free,
            status=SubscriptionStatus.active,
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
    return sub


def is_premium_active(sub: Subscription) -> bool:
    """
    True only when:
    - plan is premium
    - status is active
    - current_period_end is in the future (or not yet set = first cycle pending)
    """
    if sub.plan_type != PlanType.premium:
        return False
    if sub.status != SubscriptionStatus.active:
        return False
    if sub.current_period_end and sub.current_period_end < _utcnow():
        return False
    return True


# ── Feature enforcement ───────────────────────────────────────────────────────

def enforce_memory_limit(db: Session, user: User):
    sub = get_user_subscription(db, user)
    if is_premium_active(sub):
        return

    persona = user.persona
    if not persona:
        return

    count = len(persona.memories)
    if count >= settings.FREE_MEMORY_LIMIT:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Free plan allows up to {settings.FREE_MEMORY_LIMIT} memories. "
                "Upgrade to Premium for unlimited memories."
            ),
        )


def enforce_chat_limit(db: Session, user: User):
    from app.models.chat import ChatMessage

    sub = get_user_subscription(db, user)
    limit = (
        settings.PREMIUM_CHAT_DAILY_LIMIT
        if is_premium_active(sub)
        else settings.FREE_CHAT_DAILY_LIMIT
    )

    today_start = _utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    count = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.user_id == user.id,
            ChatMessage.role == "user",
            ChatMessage.created_at >= today_start,
        )
        .count()
    )

    if count >= limit:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Daily chat limit of {limit} messages reached. "
                + (
                    "Upgrade to Premium for more."
                    if not is_premium_active(sub)
                    else "Try again tomorrow."
                )
            ),
        )


# ── Subscription initiation ───────────────────────────────────────────────────

async def initiate_premium_subscription(db: Session, user: User) -> dict:
    """
    Creates Razorpay customer + subscription, marks DB row as pending.
    Returns Razorpay subscription object with `short_url` for checkout.
    Subscription becomes ACTIVE only after webhook confirms payment.
    """
    sub = get_user_subscription(db, user)

    # Idempotency: reuse existing pending/active subscription
    if sub.razorpay_subscription_id and sub.status in (
        SubscriptionStatus.pending,
        SubscriptionStatus.active,
    ):
        rzp_sub = await rzp.fetch_subscription(sub.razorpay_subscription_id)
        return rzp_sub

    # 1. Create Razorpay customer
    customer = await rzp.create_customer(email=user.email)
    customer_id = customer["id"]

    # 2. Resolve plan ID
    plan_id = await rzp.get_or_create_plan()

    # 3. Create Razorpay subscription (returns short_url for checkout)
    rzp_sub = await rzp.create_subscription(
        plan_id=plan_id,
        customer_id=customer_id,
        notes={"user_id": str(user.id), "email": user.email},
    )

    # 4. Mark DB as pending — NOT active yet
    sub.plan_type = PlanType.premium
    sub.status = SubscriptionStatus.pending
    sub.razorpay_subscription_id = rzp_sub["id"]
    sub.razorpay_customer_id = customer_id
    db.commit()

    return rzp_sub


# ── Webhook event handlers ────────────────────────────────────────────────────

def handle_subscription_activated(db: Session, payload: dict):
    """subscription.activated — first payment done, subscription live."""
    rzp_sub = payload["payload"]["subscription"]["entity"]
    _activate_subscription(db, rzp_sub)


def handle_payment_captured(db: Session, payload: dict):
    """payment.captured — recurring charge succeeded."""
    payment_entity = payload["payload"]["payment"]["entity"]
    rzp_sub_id = payment_entity.get("subscription_id")
    if not rzp_sub_id:
        return

    sub = _find_sub_by_rzp_id(db, rzp_sub_id)
    if not sub:
        return

    sub.status = SubscriptionStatus.active
    sub.plan_type = PlanType.premium
    sub.last_webhook_event = json.dumps({
        "event": "payment.captured",
        "payment_id": payment_entity["id"],
    })

    rzp_sub_entity = payload["payload"].get("subscription", {}).get("entity")
    if rzp_sub_entity:
        _set_period(sub, rzp_sub_entity)

    db.commit()


def handle_subscription_charged(db: Session, payload: dict):
    """subscription.charged — successful recurring charge (v2 event)."""
    rzp_sub = payload["payload"]["subscription"]["entity"]
    _activate_subscription(db, rzp_sub)


def handle_subscription_cancelled(db: Session, payload: dict):
    """subscription.cancelled — canceled; keep premium until period ends."""
    rzp_sub = payload["payload"]["subscription"]["entity"]
    sub = _find_sub_by_rzp_id(db, rzp_sub["id"])
    if not sub:
        return

    sub.status = SubscriptionStatus.canceled
    # Access continues until period end; plan_type downgrade on next enforce_ call
    if not sub.current_period_end or sub.current_period_end <= _utcnow():
        sub.plan_type = PlanType.free
    sub.last_webhook_event = json.dumps({"event": "subscription.cancelled"})
    db.commit()


def handle_subscription_paused(db: Session, payload: dict):
    """subscription.paused — Razorpay is retrying failed payment."""
    rzp_sub = payload["payload"]["subscription"]["entity"]
    sub = _find_sub_by_rzp_id(db, rzp_sub["id"])
    if not sub:
        return
    sub.status = SubscriptionStatus.paused
    sub.last_webhook_event = json.dumps({"event": "subscription.paused"})
    db.commit()


def handle_subscription_halted(db: Session, payload: dict):
    """subscription.halted — max retries exhausted; downgrade immediately."""
    rzp_sub = payload["payload"]["subscription"]["entity"]
    sub = _find_sub_by_rzp_id(db, rzp_sub["id"])
    if not sub:
        return
    sub.status = SubscriptionStatus.halted
    sub.plan_type = PlanType.free
    sub.last_webhook_event = json.dumps({"event": "subscription.halted"})
    db.commit()


def handle_subscription_resumed(db: Session, payload: dict):
    """subscription.resumed — payment recovered after pause."""
    rzp_sub = payload["payload"]["subscription"]["entity"]
    _activate_subscription(db, rzp_sub)


def handle_subscription_pending(db: Session, payload: dict):
    """subscription.pending — payment failed, retry in progress."""
    rzp_sub = payload["payload"]["subscription"]["entity"]
    sub = _find_sub_by_rzp_id(db, rzp_sub["id"])
    if not sub:
        return
    sub.last_webhook_event = json.dumps({"event": "subscription.pending"})
    db.commit()


# ── User-initiated cancel ─────────────────────────────────────────────────────

async def cancel_user_subscription(db: Session, user: User) -> Subscription:
    """Cancel at end of current billing cycle."""
    sub = get_user_subscription(db, user)

    if sub.plan_type == PlanType.free or not sub.razorpay_subscription_id:
        raise HTTPException(status_code=400, detail="No active premium subscription to cancel.")

    if sub.status == SubscriptionStatus.canceled:
        raise HTTPException(status_code=400, detail="Subscription is already canceled.")

    await rzp.cancel_subscription(sub.razorpay_subscription_id, cancel_at_end=True)

    # Optimistic local update; webhook will confirm
    sub.status = SubscriptionStatus.canceled
    sub.last_webhook_event = json.dumps({"event": "user_initiated_cancel"})
    db.commit()
    db.refresh(sub)
    return sub


# ── Private ───────────────────────────────────────────────────────────────────

def _find_sub_by_rzp_id(db: Session, rzp_sub_id: str) -> Subscription | None:
    return (
        db.query(Subscription)
        .filter(Subscription.razorpay_subscription_id == rzp_sub_id)
        .first()
    )


def _activate_subscription(db: Session, rzp_sub: dict):
    sub = _find_sub_by_rzp_id(db, rzp_sub["id"])
    if not sub:
        return
    sub.status = SubscriptionStatus.active
    sub.plan_type = PlanType.premium
    _set_period(sub, rzp_sub)
    sub.last_webhook_event = json.dumps({
        "event": "activated",
        "rzp_status": rzp_sub.get("status"),
    })
    db.commit()


def _set_period(sub: Subscription, rzp_sub: dict):
    """Populate billing period timestamps from Razorpay subscription entity."""
    current_start = rzp_sub.get("current_start")
    current_end = rzp_sub.get("current_end")
    charge_at = rzp_sub.get("charge_at")

    if current_start:
        sub.current_period_start = datetime.fromtimestamp(int(current_start), tz=timezone.utc)
    if current_end:
        sub.current_period_end = datetime.fromtimestamp(int(current_end), tz=timezone.utc)
    elif charge_at:
        sub.current_period_end = datetime.fromtimestamp(int(charge_at), tz=timezone.utc)
