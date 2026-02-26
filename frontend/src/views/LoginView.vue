<template>
  <div class="auth-page">
    <div class="card auth-card">
      <h1>Welcome Back</h1>
      <p class="sub">Continue your MySaath journey.</p>

      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label>Email</label>
          <input v-model="form.email" type="email" class="input" placeholder="you@example.com" required />
        </div>
        <div class="form-group">
          <label>Password</label>
          <input v-model="form.password" type="password" class="input" placeholder="Your password" required />
        </div>

        <div v-if="error" class="error-msg">{{ error }}</div>

        <button type="submit" class="btn btn-primary full" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          <span v-else>Sign In</span>
        </button>
      </form>

      <p class="switch-link">New here? <RouterLink to="/register">Create account</RouterLink></p>
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
    await auth.login(form.email, form.password)
    router.push('/chat')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Invalid credentials.'
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
