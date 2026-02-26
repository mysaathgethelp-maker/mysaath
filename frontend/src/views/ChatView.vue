<template>
  <div class="chat-layout">
    <!-- Sidebar / persona info -->
    <aside class="sidebar">
      <div v-if="persona" class="persona-card">
        <div class="avatar">
          <img v-if="persona.avatar_image_url" :src="persona.avatar_image_url" alt="persona" />
          <span v-else class="avatar-initial">{{ persona.display_name[0] }}</span>
        </div>
        <div class="persona-name">{{ persona.display_name }}</div>
        <div class="persona-hint">MySaath AI reflection</div>
      </div>
      <div v-else class="no-persona">
        <p>No persona yet.</p>
        <RouterLink to="/setup" class="btn btn-primary">Create Persona</RouterLink>
      </div>
    </aside>

    <!-- Chat area -->
    <main class="chat-main">
      <div class="messages" ref="messagesEl">
        <div v-if="messages.length === 0 && persona" class="empty-state">
          <p>Begin a conversation with the memory of <strong>{{ persona.display_name }}</strong>.</p>
        </div>

        <div
          v-for="msg in messages"
          :key="msg.id || msg._key"
          class="message"
          :class="msg.role"
        >
          <div class="bubble">{{ msg.content }}</div>
        </div>

        <div v-if="thinking" class="message assistant">
          <div class="bubble thinking"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>
        </div>
      </div>

      <form class="input-row" @submit.prevent="sendMessage" v-if="persona">
        <input
          v-model="input"
          class="input"
          placeholder="Say something..."
          :disabled="thinking"
          maxlength="1000"
        />
        <button type="submit" class="btn btn-primary" :disabled="thinking || !input.trim()">Send</button>
      </form>

      <div v-if="error" class="chat-error">{{ error }}</div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { personaApi, chatApi } from '../services/api'

const persona = ref(null)
const messages = ref([])
const input = ref('')
const thinking = ref(false)
const error = ref('')
const messagesEl = ref(null)

let msgCounter = 0

onMounted(async () => {
  try {
    const [pRes, hRes] = await Promise.all([personaApi.get(), chatApi.history()])
    persona.value = pRes.data
    messages.value = hRes.data
  } catch {
    // persona may not exist yet
  }
  scrollBottom()
})

async function sendMessage() {
  if (!input.value.trim() || thinking.value) return
  error.value = ''

  const userMsg = { role: 'user', content: input.value, _key: ++msgCounter }
  messages.value.push(userMsg)
  const text = input.value
  input.value = ''
  thinking.value = true
  await scrollBottom()

  try {
    const res = await chatApi.send(text)
    messages.value.push({ role: 'assistant', content: res.data.reply, _key: ++msgCounter })
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to get a response. Please try again.'
    messages.value.pop()
    input.value = text
  } finally {
    thinking.value = false
    await scrollBottom()
  }
}

async function scrollBottom() {
  await nextTick()
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  }
}
</script>

<style scoped>
.chat-layout {
  display: flex;
  height: calc(100vh - 49px);
}

.sidebar {
  width: 220px;
  flex-shrink: 0;
  background: var(--surface);
  border-right: 1px solid var(--border);
  padding: 1.5rem 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.persona-card { text-align: center; }
.avatar {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: var(--surface2);
  border: 2px solid var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 0.75rem;
  overflow: hidden;
}
.avatar img { width: 100%; height: 100%; object-fit: cover; }
.avatar-initial { font-size: 28px; font-weight: 700; color: var(--accent-light); }
.persona-name { font-weight: 600; font-size: 15px; }
.persona-hint { font-size: 11px; color: var(--text-muted); margin-top: 0.2rem; }
.no-persona { text-align: center; font-size: 13px; color: var(--text-muted); display: flex; flex-direction: column; gap: 0.75rem; }

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.empty-state {
  text-align: center;
  color: var(--text-muted);
  margin: auto;
  font-size: 14px;
}

.message { display: flex; }
.message.user { justify-content: flex-end; }
.message.assistant { justify-content: flex-start; }

.bubble {
  max-width: 70%;
  padding: 0.65rem 1rem;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.55;
  white-space: pre-wrap;
}
.user .bubble { background: var(--accent); color: #fff; border-bottom-right-radius: 4px; }
.assistant .bubble { background: var(--surface2); color: var(--text); border-bottom-left-radius: 4px; }

.thinking {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 0.75rem 1rem;
}
.dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--text-muted);
  animation: bounce 1.2s infinite;
}
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%,60%,100% { transform: translateY(0); } 30% { transform: translateY(-6px); } }

.input-row {
  display: flex;
  gap: 0.6rem;
  padding: 0.9rem 1.25rem;
  border-top: 1px solid var(--border);
  background: var(--surface);
}
.input-row .input { flex: 1; }

.chat-error {
  color: var(--danger);
  font-size: 13px;
  padding: 0.5rem 1.25rem;
  background: var(--surface);
}
</style>
