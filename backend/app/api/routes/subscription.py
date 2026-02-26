"""
Subscription routes with Razorpay checkout and webhook handling.
"""

import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.schemas import SubscriptionOut, InitiateSubscriptionResponse
from app.services import billing_service as svc
from app.services.razorpay_client import verify_webhook_signature, RazorpayError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=SubscriptionOut)
def get_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.get_user_subscription(db, current_user)


@router.post("/initiate", response_model=InitiateSubscriptionResponse)
async def initiate_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Step 1 of checkout flow.
    Creates Razorpay subscription and returns hosted checkout URL.
    Premium is NOT activated here — only the webhook can activate it.
    """
    try:
        rzp_sub = await svc.initiate_premium_subscription(db, current_user)
    except RazorpayError as e:
        logger.error("Razorpay initiation error: %s", e)
        raise HTTPException(status_code=502, detail=f"Payment provider error: {e.message}")

    return InitiateSubscriptionResponse(
        razorpay_subscription_id=rzp_sub["id"],
        checkout_url=rzp_sub.get("short_url", ""),
        status=rzp_sub.get("status", "created"),
    )


@router.post("/cancel", response_model=SubscriptionOut)
async def cancel_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel at end of current billing cycle (access continues until then)."""
    try:
        sub = await svc.cancel_user_subscription(db, current_user)
    except RazorpayError as e:
        logger.error("Razorpay cancel error: %s", e)
        raise HTTPException(status_code=502, detail=f"Payment provider error: {e.message}")
    return sub


@router.post("/webhook", status_code=200)
async def razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_razorpay_signature: Optional[str] = Header(None),
):
    """
    Razorpay webhook endpoint. No JWT auth — verified via HMAC-SHA256 signature.

    Register in Razorpay Dashboard → Settings → Webhooks:
      URL: https://your-api.onrender.com/api/subscription/webhook

    Enable events:
      subscription.activated, subscription.charged, subscription.cancelled,
      subscription.paused, subscription.halted, subscription.resumed,
      subscription.pending, payment.captured
    """
    raw_body = await request.body()

    if not x_razorpay_signature:
        logger.warning("Webhook missing X-Razorpay-Signature header")
        raise HTTPException(status_code=400, detail="Missing webhook signature")

    try:
        valid = verify_webhook_signature(
            raw_body=raw_body,
            razorpay_signature=x_razorpay_signature,
            webhook_secret=settings.RAZORPAY_WEBHOOK_SECRET,
        )
    except ValueError as e:
        logger.error("Webhook secret config error: %s", e)
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    if not valid:
        logger.warning("Webhook signature FAILED — possible forgery attempt")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = payload.get("event", "")
    logger.info("Webhook event received: %s", event)

    # Always return 200 after signature validation to prevent Razorpay retries
    try:
        _dispatch_event(db, event, payload)
    except Exception as exc:
        logger.exception("Webhook handler error for event %s: %s", event, exc)

    return {"received": True, "event": event}


_HANDLERS = {
    "subscription.activated":  svc.handle_subscription_activated,
    "subscription.charged":    svc.handle_subscription_charged,
    "subscription.cancelled":  svc.handle_subscription_cancelled,
    "subscription.paused":     svc.handle_subscription_paused,
    "subscription.halted":     svc.handle_subscription_halted,
    "subscription.resumed":    svc.handle_subscription_resumed,
    "subscription.pending":    svc.handle_subscription_pending,
    "payment.captured":        svc.handle_payment_captured,
}


def _dispatch_event(db: Session, event: str, payload: dict):
    handler = _HANDLERS.get(event)
    if handler:
        handler(db, payload)
    else:
        logger.debug("Unhandled Razorpay event: %s", event)
