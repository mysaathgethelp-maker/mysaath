<template>
  <div class="page-wrap">
    <div class="card">
      <h2>{{ isEditing ? 'Update Persona' : 'Create Your Persona' }}</h2>
      <p class="sub">
        Describe the person whose memory you want to preserve. The AI will reflect these traits.
      </p>

      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label>Display Name *</label>
          <input v-model="form.display_name" class="input" placeholder="e.g. Grandma Rose" required maxlength="100" />
        </div>

        <div class="form-group">
          <label>Speaking Style</label>
          <textarea v-model="form.speaking_style" class="input" placeholder="e.g. Warm and direct. Often used Southern expressions. Never rushed." />
        </div>

        <div class="form-group">
          <label>Core Traits</label>
          <textarea v-model="form.core_traits" class="input" placeholder="e.g. Fiercely independent, deeply empathetic, sharp sense of humor." />
        </div>

        <div class="form-group">
          <label>Core Values</label>
          <textarea v-model="form.core_values" class="input" placeholder="e.g. Family above all. Hard work. Never ask for help you could give yourself." />
        </div>

        <div class="form-group">
          <label>Avatar Image URL (optional)</label>
          <input v-model="form.avatar_image_url" class="input" placeholder="https://..." type="url" />
        </div>

        <div v-if="error" class="error-msg">{{ error }}</div>
        <div v-if="success" class="success-msg">{{ success }}</div>

        <div class="actions">
          <button type="submit" class="btn btn-primary" :disabled="loading">
            <span v-if="loading" class="spinner"></span>
            <span v-else>{{ isEditing ? 'Save Changes' : 'Create Persona' }}</span>
          </button>
          <RouterLink to="/chat" class="btn btn-ghost" v-if="isEditing">Back to Chat</RouterLink>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { personaApi } from '../services/api'

const router = useRouter()
const isEditing = ref(false)
const loading = ref(false)
const error = ref('')
const success = ref('')

const form = reactive({
  display_name: '',
  speaking_style: '',
  core_traits: '',
  core_values: '',
  avatar_image_url: '',
})

onMounted(async () => {
  try {
    const res = await personaApi.get()
    Object.assign(form, res.data)
    isEditing.value = true
  } catch {
    // No persona yet — creation mode
  }
})

async function handleSubmit() {
  error.value = ''
  success.value = ''
  loading.value = true
  try {
    if (isEditing.value) {
      await personaApi.update(form)
      success.value = 'Persona updated successfully.'
    } else {
      await personaApi.create(form)
      router.push('/memories')
    }
    isEditing.value = true
  } catch (e) {
    error.value = e.response?.data?.detail || 'Something went wrong.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
h2 { font-size: 1.35rem; margin-bottom: 0.3rem; }
.sub { color: var(--text-muted); font-size: 13px; margin-bottom: 1.5rem; }
.actions { display: flex; gap: 0.75rem; margin-top: 0.5rem; }
.success-msg { color: var(--success); font-size: 13px; margin-top: 0.5rem; }
</style>
