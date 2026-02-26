#!/usr/bin/env python3
"""
test_webhook.py
---------------
Simulate Razorpay webhook events for local development and testing.

Usage:
  python test_webhook.py --event subscription.activated --sub-id sub_xxxx
  python test_webhook.py --event payment.captured --sub-id sub_xxxx --payment-id pay_xxxx
  python test_webhook.py --event subscription.halted --sub-id sub_xxxx

Requirements:
  pip install httpx python-dotenv

The script reads RAZORPAY_WEBHOOK_SECRET from .env to sign payloads correctly,
so your local server will accept them exactly as it would accept real Razorpay webhooks.
"""

import argparse
import hashlib
import hmac
import json
import time
import os
import sys
import httpx
from dotenv import load_dotenv

load_dotenv()

WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
WEBHOOK_URL = os.getenv("WEBHOOK_TEST_URL", "http://localhost:8000/api/subscription/webhook")


def build_payload(event: str, sub_id: str, payment_id: str | None = None) -> dict:
    now = int(time.time())

    rzp_sub = {
        "id": sub_id,
        "status": _sub_status_for_event(event),
        "current_start": now - 86400 * 30,
        "current_end": now + 86400 * 30,
        "charge_at": now + 86400 * 30,
    }

    payload: dict = {
        "entity": "event",
        "account_id": "acc_test123",
        "event": event,
        "contains": ["subscription"],
        "payload": {
            "subscription": {"entity": rzp_sub}
        },
        "created_at": now,
    }

    if event == "payment.captured" and payment_id:
        payload["contains"].append("payment")
        payload["payload"]["payment"] = {
            "entity": {
                "id": payment_id or "pay_test123",
                "amount": 99900,
                "currency": "INR",
                "status": "captured",
                "subscription_id": sub_id,
            }
        }

    return payload


def _sub_status_for_event(event: str) -> str:
    mapping = {
        "subscription.activated": "active",
        "subscription.charged": "active",
        "subscription.cancelled": "cancelled",
        "subscription.paused": "paused",
        "subscription.halted": "halted",
        "subscription.resumed": "active",
        "subscription.pending": "pending",
        "payment.captured": "active",
    }
    return mapping.get(event, "active")


def sign_payload(raw_body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()


def send_webhook(event: str, sub_id: str, payment_id: str | None = None):
    if not WEBHOOK_SECRET:
        print("ERROR: RAZORPAY_WEBHOOK_SECRET not set in .env")
        sys.exit(1)

    payload = build_payload(event, sub_id, payment_id)
    raw_body = json.dumps(payload, separators=(",", ":")).encode()
    signature = sign_payload(raw_body, WEBHOOK_SECRET)

    print(f"\n→ Sending webhook: {event}")
    print(f"  URL:       {WEBHOOK_URL}")
    print(f"  Sub ID:    {sub_id}")
    print(f"  Signature: {signature[:20]}...")

    resp = httpx.post(
        WEBHOOK_URL,
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": signature,
        },
        timeout=10,
    )

    print(f"\n← Response: {resp.status_code}")
    print(f"  Body: {resp.text}")

    if resp.status_code == 200:
        print("\n✓ Webhook accepted successfully")
    else:
        print("\n✗ Webhook rejected")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Razorpay webhooks locally")
    parser.add_argument("--event", required=True, choices=[
        "subscription.activated", "subscription.charged", "subscription.cancelled",
        "subscription.paused", "subscription.halted", "subscription.resumed",
        "subscription.pending", "payment.captured",
    ])
    parser.add_argument("--sub-id", required=True, help="Razorpay subscription ID")
    parser.add_argument("--payment-id", default=None, help="Razorpay payment ID (for payment events)")
    parser.add_argument("--url", default=None, help="Override webhook URL")

    args = parser.parse_args()
    if args.url:
        WEBHOOK_URL = args.url

    send_webhook(args.event, args.sub_id, args.payment_id)
