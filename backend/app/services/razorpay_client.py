"""
razorpay_client.py
------------------
Thin async wrapper around Razorpay's REST API.
All Razorpay I/O is isolated here — no provider logic leaks into routes or services.

Razorpay uses HTTP Basic Auth: key_id as username, key_secret as password.
All amounts are in smallest currency unit (paise for INR).
"""

import hashlib
import hmac
import json
import httpx
from typing import Optional

from app.core.config import settings

RAZORPAY_BASE = "https://api.razorpay.com/v1"

# INR paise: ₹999 = 99900 paise
PREMIUM_AMOUNT_PAISE = 99900  # ₹999/month


def _auth() -> tuple[str, str]:
    return (settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)


def _headers() -> dict:
    return {"Content-Type": "application/json"}


# ── Customer ─────────────────────────────────────────────────────────────────

async def create_customer(email: str, name: str = "") -> dict:
    """Create or retrieve Razorpay customer."""
    async with httpx.AsyncClient(auth=_auth(), timeout=15) as client:
        resp = await client.post(
            f"{RAZORPAY_BASE}/customers",
            json={"email": email, "name": name or email.split("@")[0]},
            headers=_headers(),
        )
        _raise_for_status(resp)
        return resp.json()


# ── Plans ─────────────────────────────────────────────────────────────────────

async def get_or_create_plan() -> str:
    """
    Return the Razorpay plan ID for the monthly premium plan.
    Uses RAZORPAY_PLAN_ID from env if pre-created in dashboard.
    Falls back to creating it dynamically (idempotent via interval).
    """
    if settings.RAZORPAY_PLAN_ID:
        return settings.RAZORPAY_PLAN_ID

    async with httpx.AsyncClient(auth=_auth(), timeout=15) as client:
        resp = await client.post(
            f"{RAZORPAY_BASE}/plans",
            json={
                "period": "monthly",
                "interval": 1,
                "item": {
                    "name": "MySaath Premium",
                    "amount": PREMIUM_AMOUNT_PAISE,
                    "currency": "INR",
                    "description": "Unlimited memories and extended chat with MySaath",
                },
            },
            headers=_headers(),
        )
        _raise_for_status(resp)
        return resp.json()["id"]


# ── Subscriptions ─────────────────────────────────────────────────────────────

async def create_subscription(
    plan_id: str,
    customer_id: str,
    total_count: int = 120,  # 10 years max; Razorpay requires a total_count
    notes: Optional[dict] = None,
) -> dict:
    """
    Create a Razorpay subscription object.
    Returns the subscription dict including `id` and `short_url` (payment link).
    """
    payload = {
        "plan_id": plan_id,
        "customer_id": customer_id,
        "total_count": total_count,
        "quantity": 1,
        "notes": notes or {},
    }
    async with httpx.AsyncClient(auth=_auth(), timeout=15) as client:
        resp = await client.post(
            f"{RAZORPAY_BASE}/subscriptions",
            json=payload,
            headers=_headers(),
        )
        _raise_for_status(resp)
        return resp.json()


async def fetch_subscription(razorpay_sub_id: str) -> dict:
    """Fetch current state of a Razorpay subscription."""
    async with httpx.AsyncClient(auth=_auth(), timeout=15) as client:
        resp = await client.get(
            f"{RAZORPAY_BASE}/subscriptions/{razorpay_sub_id}",
        )
        _raise_for_status(resp)
        return resp.json()


async def cancel_subscription(razorpay_sub_id: str, cancel_at_end: bool = True) -> dict:
    """
    Cancel a Razorpay subscription.
    cancel_at_end=True → cancels after current billing cycle (recommended UX).
    cancel_at_end=False → cancels immediately.
    """
    async with httpx.AsyncClient(auth=_auth(), timeout=15) as client:
        resp = await client.post(
            f"{RAZORPAY_BASE}/subscriptions/{razorpay_sub_id}/cancel",
            json={"cancel_at_cycle_end": 1 if cancel_at_end else 0},
            headers=_headers(),
        )
        _raise_for_status(resp)
        return resp.json()


# ── Webhook Signature Verification ───────────────────────────────────────────

def verify_webhook_signature(
    raw_body: bytes,
    razorpay_signature: str,
    webhook_secret: str,
) -> bool:
    """
    HMAC-SHA256 verification of Razorpay webhook payload.
    Must be called BEFORE processing any webhook event.

    Raises ValueError if secret is not configured.
    Returns True if valid, False if signature mismatch.
    """
    if not webhook_secret:
        raise ValueError("RAZORPAY_WEBHOOK_SECRET is not set. Cannot verify webhooks.")

    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, razorpay_signature)


# ── Payment Fetch ──────────────────────────────────────────────────────────────

async def fetch_payment(payment_id: str) -> dict:
    """Fetch a payment object by ID to verify amount / status server-side."""
    async with httpx.AsyncClient(auth=_auth(), timeout=15) as client:
        resp = await client.get(f"{RAZORPAY_BASE}/payments/{payment_id}")
        _raise_for_status(resp)
        return resp.json()


# ── Helpers ───────────────────────────────────────────────────────────────────

class RazorpayError(Exception):
    """Raised when Razorpay returns a non-2xx response."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Razorpay {status_code}: {message}")


def _raise_for_status(resp: httpx.Response):
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("error", {}).get("description", resp.text)
        except Exception:
            detail = resp.text
        raise RazorpayError(resp.status_code, detail)
