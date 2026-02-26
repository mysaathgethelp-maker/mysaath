<template>
  <div class="callback-page">
    <div class="card callback-card">
      <template v-if="state === 'checking'">
        <span class="spinner large-spinner"></span>
        <h2>Verifying Payment</h2>
        <p>Please wait while we confirm your payment with Razorpay...</p>
      </template>

      <template v-else-if="state === 'success'">
        <div class="status-icon success-icon">✓</div>
        <h2>You're Premium!</h2>
        <p>Your subscription is now active. Welcome to MySaath Premium.</p>
        <RouterLink to="/chat" class="btn btn-primary">Start Chatting</RouterLink>
      </template>

      <template v-else-if="state === 'pending'">
        <div class="status-icon pending-icon">⏳</div>
        <h2>Payment Processing</h2>
        <p>
          Your payment is being processed. This usually takes a few seconds.
          You'll be redirected automatically.
        </p>
        <p class="sub-note">If this takes longer than expected, check your email for confirmation from Razorpay.</p>
      </template>

      <template v-else-if="state === 'failed'">
        <div class="status-icon fail-icon">✕</div>
        <h2>Payment Not Confirmed</h2>
        <p>We couldn't verify your payment yet. Your account has not been charged.</p>
        <div class="failed-actions">
          <RouterLink to="/subscription" class="btn btn-primary">Try Again</RouterLink>
          <RouterLink to="/chat" class="btn btn-ghost">Go to Chat</RouterLink>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
/**
 * PaymentCallbackView
 *
 * Razorpay hosted checkout redirects back here after payment attempt.
 * We NEVER trust URL parameters to confirm payment.
 * Instead we poll our backend (which is updated via webhook) to verify status.
 *
 * URL Razorpay returns to (set as callback_url on subscription):
 *   https://your-app.vercel.app/payment/callback
 */
import { ref, onMounted } from 'vue'
import { subscriptionApi } from '../services/api'

const state = ref('checking') // 'checking' | 'success' | 'pending' | 'failed'
const MAX_POLLS = 15
const POLL_INTERVAL_MS = 2000

onMounted(async () => {
  await pollForActivation()
})

async function pollForActivation() {
  for (let i = 0; i < MAX_POLLS; i++) {
    try {
      const res = await subscriptionApi.get()
      const { status, plan_type } = res.data

      if (plan_type === 'premium' && status === 'active') {
        state.value = 'success'
        return
      }

      if (status === 'pending') {
        // Still waiting on webhook — keep polling
        await sleep(POLL_INTERVAL_MS)
        continue
      }

      // Any other status (halted, canceled, etc.) = not successful
      state.value = 'failed'
      return
    } catch {
      await sleep(POLL_INTERVAL_MS)
    }
  }

  // Timeout: payment may still be processing
  state.value = 'pending'
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}
</script>

<style scoped>
.callback-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
}
.callback-card {
  width: 100%;
  max-width: 420px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 2.5rem 2rem;
}
h2 { font-size: 1.35rem; }
p { color: var(--text-muted); font-size: 14px; line-height: 1.6; max-width: 300px; }
.sub-note { font-size: 12px; }

.large-spinner {
  width: 40px;
  height: 40px;
  border-width: 3px;
  margin-bottom: 0.5rem;
}

.status-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.6rem;
  font-weight: 700;
  margin-bottom: 0.25rem;
}
.success-icon { background: #0d2e1e; color: var(--success); }
.pending-icon { background: #1e1e0d; color: #c8b84a; }
.fail-icon { background: #250f12; color: var(--danger); }

.failed-actions { display: flex; gap: 0.75rem; margin-top: 0.25rem; }
</style>
