import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../services/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || null)
  const user = ref(null)

  const isLoggedIn = computed(() => !!token.value)

  async function login(email, password) {
    const res = await authApi.login(email, password)
    token.value = res.data.access_token
    localStorage.setItem('token', token.value)
    await fetchMe()
  }

  async function register(email, password) {
    const res = await authApi.register(email, password)
    token.value = res.data.access_token
    localStorage.setItem('token', token.value)
    await fetchMe()
  }

  async function fetchMe() {
    try {
      const res = await authApi.me()
      user.value = res.data
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  return { token, user, isLoggedIn, login, register, fetchMe, logout }
})
