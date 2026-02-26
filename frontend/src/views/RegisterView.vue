<template>
  <div class="auth-page">
    <div class="card auth-card">
      <h1>Create Account</h1>
      <p class="sub">MySaath से अपनों की यादें सँजोना शुरू करें।</p>

      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label>Email</label>
          <input v-model="form.email" type="email" class="input" placeholder="you@example.com" required />
        </div>
        <div class="form-group">
          <label>Password</label>
          <input v-model="form.password" type="password" class="input" placeholder="Min. 8 characters" required />
        </div>

        <div v-if="error" class="error-msg">{{ error }}</div>

        <button type="submit" class="btn btn-primary full" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          <span v-else>Create Account</span>
        </button>
      </form>

      <p class="switch-link">Already have an account? <RouterLink to="/login">Sign in</RouterLink></p>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const form = reactive({ email: '', password: '' })
const loading = ref(false)
const error = ref('')

async function handleSubmit() {
  error.value = ''
  loading.value = true
  try {
    await auth.register(form.email, form.password)
    router.push('/setup')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Registration failed. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
}
.auth-card { width: 100%; max-width: 400px; }
h1 { font-size: 1.5rem; margin-bottom: 0.25rem; }
.sub { color: var(--text-muted); font-size: 14px; margin-bottom: 1.5rem; }
.full { width: 100%; margin-top: 0.5rem; }
.switch-link { text-align: center; margin-top: 1.25rem; font-size: 13px; color: var(--text-muted); }
</style>
