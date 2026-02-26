<template>
  <div class="page-wrap">
    <h2>Your Plan</h2>

    <div v-if="loading" class="loading-center"><span class="spinner"></span></div>

    <template v-else-if="sub">

      <!-- ── Status banner for non-active states ────────────────────────── -->
      <div v-if="statusBanner" :class="['banner', `banner-${statusBanner.type}`]">
        <span class="banner-icon">{{ statusBanner.icon }}</span>
        <div>
          <strong>{{ statusBanner.title }}</strong>
          <p>{{ statusBanner.message }}</p>
        </div>
      </div>

      <!-- ── Current plan card ──────────────────────────────────────────── -->
      <div class="card plan-card">
        <div class="plan-header">
          <div>
            <div class="plan-name">
              {{ sub.plan_type === 'premium' ? '✦ MySaath Premium' : 'Free Plan' }}
            </div>
            <span :class="['badge', statusBadgeClass]">{{ sub.status }}</span>
          </div>
          <div v-if="sub.plan_type === 'premium' && sub.current_period_end" class="period-info">
            <div class="period-label">
              {{ sub.status === 'canceled' ? 'Access until' : 'Renews' }}
            </div>
            <div class="period-date">{{ formatDate(sub.current_period_end) }}</div>
          </div>
        </div>

        <div class="features">
          <div class="feature-row">
            <span>Memories</span>
            <span class="feature-val">{{ isPremiumActive ? 'Unlimited' : 'Up to 10' }}</span>
          </div>
          <div class="feature-row">
            <span>Daily chat messages</span>
            <span class="feature-val">{{ isPremiumActive ? '200' : '20' }}</span>
          </div>
          <div class="feature-row">
            <span>Priority memory in prompts</span>
            <span class="feature-val">✓</span>
          </div>
          <div class="feature-row">
            <span>Payment methods</span>
            <span class="feature-val payment-methods">
              <span class="pm-tag">UPI</span>
              <span class="pm-tag">Cards</span>
              <span class="pm-tag">Netbanking</span>
            </span>
          </div>
        </div>
      </div>

      <!-- ── Upgrade section ────────────────────────────────────────────── -->
      <div
        class="card upgrade-card"
        v-if="sub.plan_type === 'free' || ['canceled','halted','expired'].includes(sub.status)"
      >
        <div class="upgrade-top">
          <div>
            <h3>Upgrade to MySaath Premium</h3>
            <p class="upgrade-desc">
              Unlimited memories, 200 chat messages/day, and priority memory recall.
            </p>
          </div>
          <div class="price-block">
            <div class="price">₹999</div>
            <div class="price-period">/ month</div>
          </div>
        </div>

        <div v-if="checkoutError" class="error-msg">{{ checkoutError }}</div>

        <button class="btn btn-primary upgrade-btn" @click="startCheckout" :disabled="initiating">
          <span v-if="initiating" class="spinner"></span>
          <span v-else>🔒 Pay with Razorpay</span>
        </button>

        <div class="payment-note">
          Secure payment via Razorpay. Supports UPI, Debit/Credit Cards, Netbanking.
          Your subscription activates automatically after payment confirmation.
        </div>
      </div>

      <!-- ── Pending state guidance ─────────────────────────────────────── -->
      <div class="card pending-card" v-if="sub.status === 'pending'">
        <h3>⏳ Payment Pending</h3>
        <p>
          A payment session was created. Complete payment to activate your premium plan.
          If you've already paid, your subscription will activate within a few seconds.
        </p>
        <div class="pending-actions">
          <button class="btn btn-primary" @click="resumeCheckout" :disabled="initiating">
            <span v-if="initiating" class="spinner"></span>
            <span v-else>Complete Payment</span>
          </button>
          <button class="btn btn-ghost" @click="pollStatus" :disabled="polling">
            {{ polling ? 'Checking...' : 'I already paid — check status' }}
          </button>
        </div>
      </div>

      <!-- ── Cancel section ─────────────────────────────────────────────── -->
      <div class="cancel-section" v-if="isPremiumActive && sub.status === 'active'">
        <button class="btn btn-ghost" @click="cancelSub" :disabled="canceling">
          {{ canceling ? 'Canceling...' : 'Cancel Subscription' }}
        </button>
        <p class="cancel-note">You'll retain access until {{ formatDate(sub.current_period_end) }}</p>
      </div>

    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { subscriptionApi } from '../services/api'

const sub = ref(null)
const loading = ref(true)
const initiating = ref(false)
const canceling = ref(false)
const polling = ref(false)
const checkoutError = ref('')

onMounted(async () => {
  await loadSub()
})

async function loadSub() {
  try {
    const res = await subscriptionApi.get()
    sub.value = res.data
  } finally {
    loading.value = false
  }
}

const isPremiumActive = computed(() =>
  sub.value?.plan_type === 'premium' && sub.value?.status === 'active'
)

const statusBadgeClass = computed(() => {
  const map = {
    active: 'badge-active',
    pending: 'badge-pending',
    canceled: 'badge-canceled',
    paused: 'badge-warning',
    halted: 'badge-danger',
    expired: 'badge-danger',
    free: 'badge-free',
  }
  return map[sub.value?.status] || 'badge-free'
})

const statusBanner = computed(() => {
  const s = sub.value?.status
  if (s === 'paused') return {
    type: 'warning',
    icon: '⚠️',
    title: 'Payment Failed — Retrying',
    message: 'Razorpay is retrying your payment. Premium features are temporarily limited. Update your payment method to restore access.',
  }
  if (s === 'halted') return {
    type: 'danger',
    icon: '🚫',
    title: 'Subscription Halted',
    message: 'Multiple payment attempts failed. Your plan has been downgraded to Free. Subscribe again to restore premium access.',
  }
  if (s === 'canceled') return {
    type: 'info',
    icon: 'ℹ️',
    title: 'Subscription Canceled',
    message: sub.value?.current_period_end
      ? `Your premium access continues until ${formatDate(sub.value.current_period_end)}.`
      : 'Your subscription has been canceled.',
  }
  return null
})

async function startCheckout() {
  checkoutError.value = ''
  initiating.value = true
  try {
    const res = await subscriptionApi.initiate()
    const { razorpay_subscription_id, checkout_url } = res.data

    // Reload sub to get pending state
    await loadSub()

    // Open Razorpay Checkout.js
    openRazorpayCheckout(razorpay_subscription_id, checkout_url)
  } catch (e) {
    checkoutError.value = e.response?.data?.detail || 'Could not start payment. Please try again.'
  } finally {
    initiating.value = false
  }
}

async function resumeCheckout() {
  checkoutError.value = ''
  initiating.value = true
  try {
    const res = await subscriptionApi.initiate()
    openRazorpayCheckout(res.data.razorpay_subscription_id, res.data.checkout_url)
  } catch (e) {
    checkoutError.value = e.response?.data?.detail || 'Could not resume payment.'
  } finally {
    initiating.value = false
  }
}

function openRazorpayCheckout(subscriptionId, shortUrl) {
  /**
   * Razorpay Checkout.js integration.
   *
   * TWO options:
   * A) Redirect to hosted page (short_url) — simplest, no JS SDK needed
   * B) Inline modal via Razorpay Checkout.js
   *
   * We use Option A (redirect) here as it requires zero SDK setup.
   * To use the modal instead, load https://checkout.razorpay.com/v1/checkout.js
   * and call new Razorpay({ subscription_id, ... }).open()
   *
   * IMPORTANT: Never trust the frontend success callback alone.
   * The backend only activates the plan via webhook.
   */
  if (shortUrl) {
    // Redirect to Razorpay hosted checkout page
    window.location.href = shortUrl
  } else {
    // Fallback: direct Razorpay subscription URL
    window.location.href = `https://api.razorpay.com/v1/checkout/embedded`
  }
}

async function pollStatus() {
  polling.value = true
  // Poll up to 10 times with 2s interval
  for (let i = 0; i < 10; i++) {
    await new Promise(r => setTimeout(r, 2000))
    const res = await subscriptionApi.get()
    sub.value = res.data
    if (res.data.status === 'active') break
  }
  polling.value = false
}

async function cancelSub() {
  if (!confirm('Cancel your subscription? You keep access until your billing period ends.')) return
  canceling.value = true
  try {
    const res = await subscriptionApi.cancel()
    sub.value = res.data
  } catch (e) {
    alert(e.response?.data?.detail || 'Cancellation failed.')
  } finally {
    canceling.value = false
  }
}

function formatDate(dt) {
  return new Date(dt).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'long', year: 'numeric',
  })
}
</script>

<style scoped>
h2 { font-size: 1.3rem; margin-bottom: 1.25rem; }
.loading-center { display: flex; justify-content: center; padding: 2rem; }

/* Banners */
.banner {
  display: flex;
  gap: 0.9rem;
  align-items: flex-start;
  padding: 1rem 1.25rem;
  border-radius: var(--radius);
  margin-bottom: 1.25rem;
  font-size: 14px;
}
.banner strong { display: block; margin-bottom: 0.2rem; }
.banner p { color: var(--text-muted); margin: 0; }
.banner-icon { font-size: 1.4rem; flex-shrink: 0; }
.banner-warning { background: #2a2010; border: 1px solid #6b4a10; }
.banner-danger { background: #250f12; border: 1px solid #7a1a22; }
.banner-info { background: #0e1e2e; border: 1px solid #1a4060; }

/* Plan card */
.plan-card { margin-bottom: 1.25rem; }
.plan-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.25rem;
}
.plan-name { font-size: 1.1rem; font-weight: 700; margin-bottom: 0.4rem; }
.period-info { text-align: right; }
.period-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
.period-date { font-size: 14px; font-weight: 600; margin-top: 0.15rem; }

.features { display: flex; flex-direction: column; gap: 0; }
.feature-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  padding: 0.6rem 0;
  border-bottom: 1px solid var(--border);
  color: var(--text-muted);
}
.feature-row:last-child { border-bottom: none; }
.feature-val { color: var(--text); font-weight: 500; }

.payment-methods { display: flex; gap: 0.4rem; }
.pm-tag {
  background: var(--surface2);
  border: 1px solid var(--border);
  color: var(--text-muted);
  font-size: 11px;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
}

/* Status badges */
.badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 20px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
.badge-active { background: #0d2e1e; color: var(--success); }
.badge-free { background: var(--surface2); color: var(--text-muted); border: 1px solid var(--border); }
.badge-pending { background: #1e1e0d; color: #c8b84a; }
.badge-canceled { background: #1a1a2e; color: #7070a0; }
.badge-warning { background: #2a1e0d; color: #d4863a; }
.badge-danger { background: #250f12; color: #e05060; }

/* Upgrade card */
.upgrade-card { margin-bottom: 1.25rem; }
.upgrade-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem; gap: 1rem; }
.upgrade-top h3 { font-size: 1rem; margin-bottom: 0.35rem; }
.upgrade-desc { color: var(--text-muted); font-size: 13px; line-height: 1.5; }
.price-block { text-align: right; flex-shrink: 0; }
.price { font-size: 1.75rem; font-weight: 800; color: var(--accent-light); }
.price-period { font-size: 12px; color: var(--text-muted); }
.upgrade-btn { width: 100%; padding: 0.75rem; font-size: 15px; }
.payment-note { font-size: 12px; color: var(--text-muted); text-align: center; margin-top: 0.75rem; line-height: 1.5; }

/* Pending card */
.pending-card h3 { font-size: 1rem; margin-bottom: 0.5rem; }
.pending-card p { color: var(--text-muted); font-size: 14px; margin-bottom: 1rem; line-height: 1.5; }
.pending-actions { display: flex; gap: 0.75rem; flex-wrap: wrap; }

/* Cancel */
.cancel-section { display: flex; flex-direction: column; align-items: flex-start; gap: 0.4rem; margin-top: 0.5rem; }
.cancel-note { font-size: 12px; color: var(--text-muted); }
</style>
