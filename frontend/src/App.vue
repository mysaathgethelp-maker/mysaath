<template>
  <div>
    <nav class="nav" v-if="auth.isLoggedIn">
      <span class="nav-brand">✦ MySaath</span>
      <div class="nav-links">
        <RouterLink to="/chat" active-class="active">Chat</RouterLink>
        <RouterLink to="/memories" active-class="active">Memories</RouterLink>
        <RouterLink to="/setup" active-class="active">Persona</RouterLink>
        <RouterLink to="/subscription" active-class="active">Plan</RouterLink>
        <a href="#" @click.prevent="auth.logout(); router.push('/login')">Sign out</a>
      </div>
    </nav>
    <RouterView />
  </div>
</template>

<script setup>
import { useAuthStore } from './stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()
</script>
