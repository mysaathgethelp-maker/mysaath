<template>
  <div class="page-wrap">
    <div class="header-row">
      <h2>Memory Manager</h2>
      <div class="limit-badge" v-if="planInfo">
        <span :class="['badge', planInfo.is_premium ? 'badge-premium' : 'badge-free']">
          {{ planInfo.is_premium ? 'Premium' : `${memories.length}/${FREE_LIMIT} Free` }}
        </span>
      </div>
    </div>

    <!-- Add memory form -->
    <div class="card add-form">
      <h3>Add Memory</h3>
      <div class="form-row">
        <div class="form-group">
          <label>Type</label>
          <select v-model="newMemory.memory_type" class="input">
            <option value="trait">Trait</option>
            <option value="value">Value</option>
            <option value="phrase">Phrase</option>
            <option value="episodic">Episodic</option>
          </select>
        </div>
        <div class="form-group">
          <label>Priority</label>
          <select v-model="newMemory.priority" class="input">
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>
      <div class="form-group">
        <label>Memory Content</label>
        <textarea
          v-model="newMemory.content"
          class="input"
          placeholder="Describe a trait, value, phrase, or memory..."
          maxlength="2000"
        />
      </div>
      <div v-if="addError" class="error-msg">{{ addError }}</div>
      <button class="btn btn-primary" @click="addMemory" :disabled="adding || !newMemory.content.trim()">
        <span v-if="adding" class="spinner"></span>
        <span v-else>Add Memory</span>
      </button>
    </div>

    <!-- Memory list -->
    <div v-if="loading" class="loading-center"><span class="spinner"></span></div>

    <div v-else-if="memories.length === 0" class="empty-card card">
      No memories yet. Add your first one above.
    </div>

    <div v-else class="memories-grid">
      <div
        v-for="mem in memories"
        :key="mem.id"
        class="memory-item card"
        :class="`priority-${mem.priority}`"
      >
        <div class="mem-header">
          <span class="type-tag">{{ mem.memory_type }}</span>
          <span class="priority-tag">{{ mem.priority }}</span>
          <button class="delete-btn" @click="deleteMemory(mem.id)" title="Delete">✕</button>
        </div>
        <p class="mem-content">{{ mem.content }}</p>
        <div class="mem-date">{{ formatDate(mem.created_at) }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { memoryApi, subscriptionApi } from '../services/api'

const FREE_LIMIT = 10

const memories = ref([])
const loading = ref(true)
const adding = ref(false)
const addError = ref('')
const planInfo = ref(null)

const newMemory = reactive({
  memory_type: 'episodic',
  priority: 'medium',
  content: '',
})

onMounted(async () => {
  try {
    const [mRes, sRes] = await Promise.all([memoryApi.list(), subscriptionApi.get()])
    memories.value = mRes.data
    planInfo.value = {
      plan: sRes.data.plan_type,
      is_premium: sRes.data.plan_type === 'premium' && sRes.data.status === 'active',
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

async function addMemory() {
  addError.value = ''
  adding.value = true
  try {
    const res = await memoryApi.create({ ...newMemory })
    memories.value.unshift(res.data)
    newMemory.content = ''
  } catch (e) {
    addError.value = e.response?.data?.detail || 'Failed to add memory.'
  } finally {
    adding.value = false
  }
}

async function deleteMemory(id) {
  if (!confirm('Delete this memory?')) return
  try {
    await memoryApi.delete(id)
    memories.value = memories.value.filter(m => m.id !== id)
  } catch (e) {
    alert(e.response?.data?.detail || 'Failed to delete.')
  }
}

function formatDate(dt) {
  return new Date(dt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}
</script>

<style scoped>
.header-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.25rem; }
h2 { font-size: 1.3rem; }

.add-form { margin-bottom: 1.5rem; }
.add-form h3 { font-size: 1rem; margin-bottom: 1rem; }
.form-row { display: flex; gap: 1rem; }
.form-row .form-group { flex: 1; }

.loading-center { display: flex; justify-content: center; padding: 2rem; }
.empty-card { color: var(--text-muted); font-size: 14px; text-align: center; }

.memories-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 0.85rem;
}

.memory-item { position: relative; }
.priority-high { border-left: 3px solid var(--accent); }
.priority-medium { border-left: 3px solid var(--success); }
.priority-low { border-left: 3px solid var(--border); }

.mem-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.6rem; }
.type-tag {
  background: var(--surface2);
  color: var(--text-muted);
  font-size: 11px;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  text-transform: capitalize;
}
.priority-tag { font-size: 11px; color: var(--text-muted); text-transform: capitalize; }
.delete-btn {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 13px;
  padding: 0.15rem 0.35rem;
  border-radius: 4px;
}
.delete-btn:hover { background: var(--surface2); color: var(--danger); }

.mem-content { font-size: 13.5px; line-height: 1.55; color: var(--text); }
.mem-date { font-size: 11px; color: var(--text-muted); margin-top: 0.6rem; }
</style>
