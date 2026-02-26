import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Handle 401 globally
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (email, password) => api.post('/api/auth/register', { email, password }),
  login: (email, password) => api.post('/api/auth/login', { email, password }),
  me: () => api.get('/api/auth/me'),
}

// ── Persona ───────────────────────────────────────────────────────────────────
export const personaApi = {
  get: () => api.get('/api/persona'),
  create: (data) => api.post('/api/persona', data),
  update: (data) => api.put('/api/persona', data),
  delete: () => api.delete('/api/persona'),
}

// ── Memory ────────────────────────────────────────────────────────────────────
export const memoryApi = {
  list: () => api.get('/api/memories'),
  create: (data) => api.post('/api/memories', data),
  update: (id, data) => api.put(`/api/memories/${id}`, data),
  delete: (id) => api.delete(`/api/memories/${id}`),
}

// ── Chat ──────────────────────────────────────────────────────────────────────
export const chatApi = {
  send: (message) => api.post('/api/chat', { message }),
  history: (limit = 50) => api.get(`/api/chat/history?limit=${limit}`),
  clearHistory: () => api.delete('/api/chat/history'),
}

// ── Subscription (Razorpay) ───────────────────────────────────────────────────
export const subscriptionApi = {
  get: () => api.get('/api/subscription'),
  // Initiates a Razorpay subscription → returns { razorpay_subscription_id, checkout_url }
  initiate: () => api.post('/api/subscription/initiate'),
  cancel: () => api.post('/api/subscription/cancel'),
}

export default api
