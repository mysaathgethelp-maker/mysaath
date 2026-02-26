# MySaath
MySaath — अपनों की यादें, हमेशा साथ

A single-user, memory-driven AI companion. Preserve the memory of a loved one and have meaningful conversations that reflect who they were.
A single-user, memory-driven AI companion system. The AI reflects memories explicitly provided by the user about a meaningful person.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Vercel)                     │
│   Vue 3 + Vite + Pinia + Vue Router                     │
│   Views: Register, Login, Persona, Chat, Memories, Plan │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS / Axios
┌────────────────────────▼────────────────────────────────┐
│                   Backend (Render)                       │
│   FastAPI + SQLAlchemy + JWT Auth                       │
│   Routes: /auth /persona /memories /chat /subscription  │
│   Services: groq_service, billing_service, prompt_service│
└──────────────┬──────────────────────┬───────────────────┘
               │                      │
┌──────────────▼──────┐   ┌───────────▼──────────────────┐
│  Supabase Postgres  │   │   Groq API (LLM inference)   │
│  (Free tier)        │   │   llama3-8b-8192             │
└─────────────────────┘   └──────────────────────────────┘
```

### Key Design Decisions

- **Cold-start tolerant**: No background workers, pure request-response
- **Token-efficient prompts**: Priority-sorted memories, 10-message history window
- **Subscription middleware**: Server-side enforcement — no client trust
- **Separation of concerns**: Route → Service → Model (never direct DB in routes except via dependency)

---

## Backend Folder Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI app, CORS, router mounting
│   ├── core/
│   │   ├── config.py              # Pydantic settings (env vars)
│   │   └── security.py            # JWT, password hashing, auth dependency
│   ├── db/
│   │   ├── base_class.py          # SQLAlchemy DeclarativeBase
│   │   ├── base.py                # Aggregates all models for Alembic
│   │   └── session.py             # Engine, SessionLocal, get_db()
│   ├── models/
│   │   ├── user.py
│   │   ├── persona.py
│   │   ├── memory.py
│   │   ├── chat.py
│   │   └── subscription.py
│   ├── schemas/
│   │   └── schemas.py             # All Pydantic request/response schemas
│   ├── api/routes/
│   │   ├── auth.py
│   │   ├── persona.py
│   │   ├── memory.py
│   │   ├── chat.py
│   │   └── subscription.py
│   └── services/
│       ├── groq_service.py        # Async Groq API wrapper
│       ├── prompt_service.py      # Layered prompt assembly
│       └── billing_service.py     # Plan enforcement + mock upgrade
├── requirements.txt
├── render.yaml
└── .env.example
```

---

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- A Supabase project (or local Postgres)
- A Groq API key (free at console.groq.com)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL, SECRET_KEY, GROQ_API_KEY

# Run migrations (Supabase — see below) or use auto-create for local dev
# Then start server:
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
# Edit VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

Visit `http://localhost:5173`

---

## Supabase Setup

1. Go to https://supabase.com and create a free project
2. Navigate to **SQL Editor**
3. Paste the contents of `supabase_schema.sql` and click **Run**
4. Go to **Settings → Database**
5. Copy the **Connection string** (URI format):
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```
6. Add this as `DATABASE_URL` in your `.env`

**Important**: Supabase free tier pauses after 7 days of inactivity. The backend uses `pool_pre_ping=True` to handle reconnections gracefully.

---

## Render Deployment (Backend)

1. Push your code to a GitHub repo
2. Go to https://render.com → **New Web Service**
3. Connect your repo, set **Root Directory** to `backend/`
4. Settings:
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables in Render dashboard:
   ```
   DATABASE_URL=postgresql://...
   SECRET_KEY=your-secret-key
   GROQ_API_KEY=gsk_...
   ALLOWED_ORIGINS=["https://your-app.vercel.app"]
   ```
6. Deploy. Note your Render URL (e.g. `https://mysaath-api.onrender.com`)

**Note**: Render free tier spins down after 15 minutes of inactivity. First request may take ~30s. This is normal.

---

## Vercel Deployment (Frontend)

1. Push your code to GitHub
2. Go to https://vercel.com → **New Project**
3. Import your repo, set **Root Directory** to `frontend/`
4. Add environment variable:
   ```
   VITE_API_BASE_URL=https://your-render-app.onrender.com
   ```
5. Deploy. Vercel auto-detects Vite.

The `vercel.json` file handles SPA routing (all paths → `index.html`).

---

## API Reference

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login, get JWT |
| GET | `/api/auth/me` | Get current user |

### Persona
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/persona` | Create persona |
| GET | `/api/persona` | Get persona |
| PUT | `/api/persona` | Update persona |
| DELETE | `/api/persona` | Delete persona |

### Memories
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/memories` | List all memories |
| POST | `/api/memories` | Create memory |
| PUT | `/api/memories/{id}` | Update memory |
| DELETE | `/api/memories/{id}` | Delete memory |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send message, get AI reply |
| GET | `/api/chat/history` | Get chat history |
| DELETE | `/api/chat/history` | Clear history |

### Subscription
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/subscription` | Get current plan |
| POST | `/api/subscription/upgrade` | Upgrade to premium (mock) |
| POST | `/api/subscription/cancel` | Cancel subscription |
| POST | `/api/subscription/webhook` | Stripe webhook (webhook-ready) |

---

## Prompt Architecture

The chat prompt is assembled in layers:

```
[System Layer]
  Identity rules: AI must never claim to be real
  
[Persona Layer]
  display_name, speaking_style, core_traits, core_values

[Memory Layer]
  Grouped by type (trait/value/phrase/episodic)
  Sorted by priority (high → medium → low)

[History Layer]
  Last 10 message turns (token budget)

[User Message]
  Current user input
```

---

## Plan Limits

| Feature | Free | Premium |
|---------|------|---------|
| Memories | 10 | Unlimited |
| Daily chat messages | 20 | 200 |
| Priority sorting | ✓ | ✓ |
| Price | $0 | $9.99/mo |

Limits are enforced **server-side only** — never trust the client.

---

## Security Notes

- JWT tokens are signed with `SECRET_KEY` (RS256 algorithm)
- Passwords hashed with bcrypt via passlib
- No secrets in code — all via environment variables
- Subscription plan verified on every chat/memory request
- CORS restricted to known frontend origins
- Groq API key never exposed to frontend
