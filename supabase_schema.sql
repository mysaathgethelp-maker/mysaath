-- MySaath — Supabase Schema (Razorpay Edition)
-- Run this in Supabase SQL Editor (Project → SQL Editor → New Query)

-- Users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Personas (one per user)
CREATE TABLE IF NOT EXISTS personas (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    display_name VARCHAR(100) NOT NULL,
    speaking_style TEXT,
    core_traits TEXT,
    core_values TEXT,
    avatar_image_url VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- Memories
CREATE TABLE IF NOT EXISTS memories (
    id SERIAL PRIMARY KEY,
    persona_id INTEGER NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
    memory_type VARCHAR(20) NOT NULL CHECK (memory_type IN ('trait', 'value', 'phrase', 'episodic')),
    content TEXT NOT NULL,
    priority VARCHAR(10) NOT NULL DEFAULT 'medium' CHECK (priority IN ('high', 'medium', 'low')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Subscriptions (Razorpay-integrated, one per user)
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_type VARCHAR(20) NOT NULL DEFAULT 'free'
        CHECK (plan_type IN ('free', 'premium')),
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'canceled', 'expired', 'pending', 'paused', 'halted')),

    -- Razorpay identifiers
    razorpay_subscription_id VARCHAR(100) UNIQUE,
    razorpay_customer_id VARCHAR(100),

    -- Billing period (set by webhook on payment.captured)
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,

    -- Audit: last raw webhook event for debugging
    last_webhook_event TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- Chat messages
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    persona_id INTEGER NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_memories_persona       ON memories(persona_id);
CREATE INDEX IF NOT EXISTS idx_memories_priority      ON memories(priority);
CREATE INDEX IF NOT EXISTS idx_chat_messages_persona  ON chat_messages(persona_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_user_date ON chat_messages(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_sub_status             ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_sub_razorpay_id        ON subscriptions(razorpay_subscription_id);

-- Migration: if upgrading from previous schema without Razorpay columns, run:
-- ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS razorpay_subscription_id VARCHAR(100) UNIQUE;
-- ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS razorpay_customer_id VARCHAR(100);
-- ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS current_period_start TIMESTAMPTZ;
-- ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS last_webhook_event TEXT;
-- ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;
-- ALTER TABLE subscriptions DROP COLUMN IF EXISTS stripe_subscription_id;
-- ALTER TABLE subscriptions ADD CONSTRAINT sub_status_check
--   CHECK (status IN ('active', 'canceled', 'expired', 'pending', 'paused', 'halted'));
