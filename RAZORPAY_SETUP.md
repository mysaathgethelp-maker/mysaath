# Razorpay Subscription Integration Guide

Complete setup guide for MySaath's Razorpay premium subscription system.

---

## Architecture Overview

```
User clicks "Pay"
       │
       ▼
POST /api/subscription/initiate
  ├── Creates Razorpay Customer
  ├── Gets/creates Plan (₹999/month)
  ├── Creates Razorpay Subscription → { id, short_url }
  ├── Marks DB: status = pending
  └── Returns { checkout_url } to frontend
       │
       ▼
Frontend redirects to checkout_url (Razorpay hosted page)
  ├── User pays via UPI / Card / Netbanking
  └── Razorpay redirects to /payment/callback
       │
       ▼                       │
Frontend polls GET /api/subscription    │
  └── Waits for status = active         │
                                        ▼
                          Razorpay fires webhook POST /api/subscription/webhook
                            ├── Verify HMAC-SHA256 signature
                            ├── Dispatch to event handler
                            ├── Set status = active
                            ├── Set current_period_start / current_period_end
                            └── DB committed

CRITICAL: Premium is NEVER activated by frontend payment response.
          Only the webhook can activate it.
```

---

## Step 1: Razorpay Account Setup

1. Sign up at https://dashboard.razorpay.com
2. Go to **Settings → API Keys** → Generate Test Keys
3. Copy **Key ID** (starts with `rzp_test_`) and **Key Secret**
4. Add to your `.env`:
   ```
   RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
   RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxx
   ```

---

## Step 2: Create a Subscription Plan (Optional)

You can either:

**Option A — Auto-create (default):** Leave `RAZORPAY_PLAN_ID` blank. The app creates a plan on first use.

**Option B — Pre-create in Dashboard (recommended for production):**
1. Razorpay Dashboard → Products → Subscriptions → Plans → Create Plan
2. Settings:
   - Plan Name: `MySaath Premium`
   - Billing Cycle: Monthly
   - Amount: ₹999
   - Currency: INR
3. Copy the Plan ID (e.g. `plan_xxxxxxxxxxxx`)
4. Add to `.env`:
   ```
   RAZORPAY_PLAN_ID=plan_xxxxxxxxxxxx
   ```

---

## Step 3: Configure Webhook

1. Razorpay Dashboard → Settings → Webhooks → Add New Webhook
2. **Webhook URL:**
   ```
   https://your-api.onrender.com/api/subscription/webhook
   ```
3. **Secret:** Generate a random string (e.g. `openssl rand -hex 32`)
4. Add to `.env`:
   ```
   RAZORPAY_WEBHOOK_SECRET=your-generated-secret
   ```
5. **Enable these events:**
   - `subscription.activated`
   - `subscription.charged`
   - `subscription.cancelled`
   - `subscription.paused`
   - `subscription.halted`
   - `subscription.resumed`
   - `subscription.pending`
   - `payment.captured`
6. Save webhook

---

## Step 4: Set Callback URL (for hosted checkout)

When using Razorpay's hosted checkout (`short_url`), configure the return URL:

In `razorpay_client.py → create_subscription()`, add to the payload:
```python
"notify_info": {
    "notify_email": True,
    "notify_sms": True,
    "notify_whatsapp": True,
},
# callback_url is set at the plan level in dashboard, or via API
```

In Razorpay Dashboard → Your Plan → Edit:
- **Callback URL:** `https://your-app.vercel.app/payment/callback`

---

## Step 5: Test Locally with ngrok

Razorpay cannot reach `localhost`. Use ngrok to expose your local server:

```bash
# Install ngrok: https://ngrok.com
ngrok http 8000

# Copy the HTTPS URL, e.g.: https://a1b2c3d4.ngrok.io
# Update your Razorpay webhook to: https://a1b2c3d4.ngrok.io/api/subscription/webhook
```

### Test with the included test script:

```bash
cd backend

# First, create a subscription via the API to get a razorpay_subscription_id
# Then simulate webhooks:

# Test activation
python test_webhook.py --event subscription.activated --sub-id sub_test123

# Test payment captured
python test_webhook.py --event payment.captured --sub-id sub_test123 --payment-id pay_test456

# Test cancellation
python test_webhook.py --event subscription.cancelled --sub-id sub_test123

# Test payment failure
python test_webhook.py --event subscription.paused --sub-id sub_test123
python test_webhook.py --event subscription.halted --sub-id sub_test123

# Test recovery
python test_webhook.py --event subscription.resumed --sub-id sub_test123
```

---

## Step 6: Go Live

1. Switch to **Live mode** in Razorpay Dashboard
2. Generate **Live API Keys**
3. Update `.env`:
   ```
   RAZORPAY_KEY_ID=rzp_live_xxxxxxxxxxxx
   RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxx
   ```
4. Update webhook URL to your live Render URL
5. Re-generate webhook secret for live environment
6. Test with a real small payment to verify

---

## Webhook Event Reference

| Event | Meaning | Our Action |
|-------|---------|------------|
| `subscription.activated` | First payment done | Set active, update period |
| `subscription.charged` | Recurring payment done | Set active, update period |
| `subscription.cancelled` | Canceled (end of cycle) | Set canceled; keep premium until period end |
| `subscription.paused` | Payment failed, retrying | Set paused; restrict features |
| `subscription.halted` | All retries exhausted | Set halted; downgrade to free |
| `subscription.resumed` | Payment recovered | Set active, update period |
| `subscription.pending` | Payment failed, retry pending | Log; keep current status |
| `payment.captured` | Payment received | Set active, update period |

---

## Subscription Lifecycle State Machine

```
[New User]
    │
    ▼
  free/active  ──── initiate ────►  premium/pending
                                         │
                                   webhook: activated
                                         │
                                         ▼
                                   premium/active  ◄─── webhook: resumed
                                    │    │    │
                          cancel    │    │    │   payment fails
                                    │    │    │
                         ▼          │    │    ▼
                   premium/canceled │    │  premium/paused
                   (access until    │    │    │
                    period end)     │    │    │ max retries fail
                         │          │    │    ▼
                         ▼          │    │  free/halted
                    free/canceled   │    │
                                    │    │ manual resubscribe
                                    │    ▼
                                  free/active
```

---

## Security Checklist

- [x] Webhook signature verified via HMAC-SHA256 before any processing
- [x] Raw body read before JSON parsing (signature is over raw bytes)
- [x] `RAZORPAY_WEBHOOK_SECRET` stored in env var, never in code
- [x] Premium activated ONLY via webhook — never via frontend response
- [x] `is_premium_active()` checks plan + status + period expiry on every request
- [x] Webhook returns 200 after signature validation (prevents Razorpay retries)
- [x] Exceptions in event handlers are logged but not propagated to Razorpay
- [x] Razorpay Key Secret never exposed to frontend

---

## Payment Methods Supported

All methods are available via Razorpay's hosted checkout:

- **UPI** (Google Pay, PhonePe, Paytm, BHIM, etc.)
- **Cards** (Visa, Mastercard, RuPay — Debit and Credit)
- **Netbanking** (50+ Indian banks)
- **Wallets** (Paytm, Mobikwik, etc.)
- **EMI** (on eligible cards)
