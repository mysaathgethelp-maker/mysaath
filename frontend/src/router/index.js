import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/', redirect: '/chat' },
  { path: '/login', component: () => import('../views/LoginView.vue'), meta: { guest: true } },
  { path: '/register', component: () => import('../views/RegisterView.vue'), meta: { guest: true } },
  { path: '/setup', component: () => import('../views/PersonaSetupView.vue'), meta: { auth: true } },
  { path: '/chat', component: () => import('../views/ChatView.vue'), meta: { auth: true } },
  { path: '/memories', component: () => import('../views/MemoryManagerView.vue'), meta: { auth: true } },
  { path: '/subscription', component: () => import('../views/SubscriptionView.vue'), meta: { auth: true } },
  // Razorpay returns here after hosted checkout
  { path: '/payment/callback', component: () => import('../views/PaymentCallbackView.vue'), meta: { auth: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _, next) => {
  const auth = useAuthStore()
  if (to.meta.auth && !auth.isLoggedIn) return next('/login')
  if (to.meta.guest && auth.isLoggedIn) return next('/chat')
  next()
})

export default router
