-- ============================================================
-- Service 8: AI Chatbot — chatbot_db
-- Port: 3008
-- ============================================================

CREATE TABLE IF NOT EXISTS chat_session (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id BIGINT NOT NULL,
    user_type TEXT NOT NULL DEFAULT 'customer'
        CHECK (user_type IN ('customer', 'employee')),
    store_id BIGINT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS chat_message (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    session_id BIGINT NOT NULL REFERENCES chat_session(id),
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    intent TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_session_user ON chat_session(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_session_active ON chat_session(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_chat_message_session ON chat_message(session_id);

-- ============================================================
-- RAG: pgvector + Full-text Search
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS product_knowledge_base (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,

    -- Cross-service references (no FK — different DB)
    product_id BIGINT NOT NULL,
    store_id BIGINT NOT NULL,

    -- Content & Embedding
    content TEXT NOT NULL,
    embedding VECTOR(768),
    fts_content TSVECTOR,

    -- Cached metadata (avoid cross-service queries)
    category_name TEXT,
    unit_price NUMERIC DEFAULT 0,
    is_in_stock BOOLEAN DEFAULT TRUE,
    quantity_on_shelf INT DEFAULT 0,

    last_synced_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (product_id, store_id)
);

-- HNSW index for vector similarity search (cosine)
CREATE INDEX IF NOT EXISTS idx_pkb_embedding
    ON product_knowledge_base USING hnsw (embedding vector_cosine_ops);

-- GIN index for full-text keyword search
CREATE INDEX IF NOT EXISTS idx_pkb_fts
    ON product_knowledge_base USING gin (fts_content);

-- B-Tree for metadata filtering
CREATE INDEX IF NOT EXISTS idx_pkb_store_stock
    ON product_knowledge_base(store_id, is_in_stock)
    WHERE is_in_stock = TRUE;

CREATE INDEX IF NOT EXISTS idx_pkb_product_store
    ON product_knowledge_base(product_id, store_id);

-- ============================================================
-- Co-purchase Statistics (from order.completed events)
-- ============================================================

CREATE TABLE IF NOT EXISTS co_purchase_stats (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    product_id_a BIGINT NOT NULL,
    product_id_b BIGINT NOT NULL,
    store_id BIGINT NOT NULL,
    co_purchase_count INT DEFAULT 1,
    last_updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (product_id_a, product_id_b, store_id)
);

CREATE INDEX IF NOT EXISTS idx_copurchase_lookup
    ON co_purchase_stats(product_id_a, store_id)
    WHERE co_purchase_count >= 3;

-- ============================================================
-- Event Idempotency (same pattern as inventory/order services)
-- ============================================================

CREATE TABLE IF NOT EXISTS processed_events (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    service_name TEXT NOT NULL DEFAULT 'chatbot-service',
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(event_id, service_name)
);

CREATE INDEX IF NOT EXISTS idx_processed_events_id ON processed_events(event_id);

-- ============================================================
-- MIGRATION: Apriori Metrics (Phase 1B)
-- Adds support, confidence, lift to co_purchase_stats
-- ============================================================

DO $$ BEGIN
    ALTER TABLE co_purchase_stats ADD COLUMN support NUMERIC DEFAULT 0;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE co_purchase_stats ADD COLUMN confidence_ab NUMERIC DEFAULT 0;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE co_purchase_stats ADD COLUMN confidence_ba NUMERIC DEFAULT 0;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE co_purchase_stats ADD COLUMN lift NUMERIC DEFAULT 0;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE co_purchase_stats ADD COLUMN total_orders INT DEFAULT 0;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

-- Partial index: only rows with meaningful lift
CREATE INDEX IF NOT EXISTS idx_copurchase_lift
    ON co_purchase_stats(product_id_a, store_id)
    WHERE lift > 1;

-- Single-item order frequency (denominator for confidence)
CREATE TABLE IF NOT EXISTS product_order_frequency (
    product_id BIGINT NOT NULL,
    store_id BIGINT NOT NULL,
    order_count INT DEFAULT 0,
    last_computed_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (product_id, store_id)
);

-- ============================================================
-- Phase 2: Item-based Collaborative Filtering
-- ============================================================

-- User-item interaction matrix (implicit feedback from orders)
CREATE TABLE IF NOT EXISTS user_product_interaction (
    user_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    store_id BIGINT NOT NULL,
    purchase_count INT DEFAULT 0,
    total_quantity INT DEFAULT 0,
    last_purchased_at TIMESTAMPTZ,
    interaction_score NUMERIC DEFAULT 0,
    PRIMARY KEY (user_id, product_id, store_id)
);

CREATE INDEX IF NOT EXISTS idx_interaction_user
    ON user_product_interaction(user_id, store_id);

CREATE INDEX IF NOT EXISTS idx_interaction_product
    ON user_product_interaction(product_id, store_id);

-- Pre-computed item similarity (nightly batch — Adjusted Cosine)
CREATE TABLE IF NOT EXISTS item_similarity (
    item_a BIGINT NOT NULL,
    item_b BIGINT NOT NULL,
    store_id BIGINT NOT NULL,
    similarity NUMERIC NOT NULL,
    common_users INT DEFAULT 0,
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (item_a, item_b, store_id)
);

CREATE INDEX IF NOT EXISTS idx_item_sim_lookup
    ON item_similarity(item_a, store_id)
    WHERE similarity >= 0.3;

-- ============================================================
-- Phase 3: Hybrid Ensemble + Feedback Loop
-- ============================================================

-- Recommendation feedback (for adaptive weight learning)
CREATE TABLE IF NOT EXISTS recommendation_feedback (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    product_id BIGINT,
    store_id BIGINT NOT NULL,
    source TEXT NOT NULL,
    action TEXT NOT NULL,
    session_id TEXT,
    sequence_order INT DEFAULT 1,
    recommendation_score NUMERIC,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Migration: Add metadata column if table already exists
DO $$ BEGIN
    ALTER TABLE recommendation_feedback ADD COLUMN metadata JSONB;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

-- Migration: Add sequence_order column if table already exists (Phase 5 Sequential RecSys)
DO $$ BEGIN
    ALTER TABLE recommendation_feedback ADD COLUMN sequence_order INT DEFAULT 1;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_feedback_user
    ON recommendation_feedback(user_id, store_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_feedback_session_seq
    ON recommendation_feedback(session_id, sequence_order ASC);

CREATE INDEX IF NOT EXISTS idx_feedback_source_action
    ON recommendation_feedback(source, action, store_id);

-- Composite index for time-window deduplication query
CREATE INDEX IF NOT EXISTS idx_feedback_dedup
    ON recommendation_feedback(user_id, product_id, store_id, action, source, created_at DESC);

-- Ensemble weight configuration (per store, tunable)
CREATE TABLE IF NOT EXISTS ensemble_weights (
    store_id BIGINT PRIMARY KEY,
    alpha NUMERIC DEFAULT 0.40,
    beta NUMERIC DEFAULT 0.25,
    gamma NUMERIC DEFAULT 0.25,
    delta NUMERIC DEFAULT 0.10,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Phase 5: Weight history log (for trend visualization in AI Dashboard)
CREATE TABLE IF NOT EXISTS ensemble_weights_history (
    id BIGSERIAL PRIMARY KEY,
    store_id BIGINT NOT NULL,
    alpha NUMERIC NOT NULL,
    beta NUMERIC NOT NULL,
    gamma NUMERIC NOT NULL,
    delta NUMERIC NOT NULL,
    feedback_count INT DEFAULT 0,
    trigger_type TEXT DEFAULT 'nightly',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_weight_history_store_date
    ON ensemble_weights_history(store_id, created_at DESC);

-- ============================================================
-- Phase 6: Chatbot Action Assistant
-- ============================================================

-- Add metadata column to chat_session for multi-turn state and pronoun/action storage
DO $$ BEGIN
    ALTER TABLE chat_session ADD COLUMN metadata JSONB DEFAULT '{}';
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

-- Create audit log table to track write operations by the assistant
CREATE TABLE IF NOT EXISTS chatbot_audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    session_id BIGINT REFERENCES chat_session(id),
    action_type TEXT NOT NULL,
    payload JSONB,
    result JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chatbot_audit_session ON chatbot_audit_log(session_id);
CREATE INDEX IF NOT EXISTS idx_chatbot_audit_user ON chatbot_audit_log(user_id);

-- ============================================================
-- MIGRATION: Support 'manager' user_type (RBAC Phase)
-- ============================================================
DO $$ BEGIN
    ALTER TABLE chat_session DROP CONSTRAINT IF EXISTS chat_session_user_type_check;
    ALTER TABLE chat_session ADD CONSTRAINT chat_session_user_type_check
        CHECK (user_type IN ('customer', 'employee', 'manager'));
END $$;

-- ============================================================
-- AI Service: Scaled ML Interaction Event Table (v1)
-- ============================================================

CREATE TABLE IF NOT EXISTS ml_interaction_event_v1 (
    event_id TEXT PRIMARY KEY,
    store_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    persona_cluster SMALLINT NOT NULL CHECK (persona_cluster BETWEEN 0 AND 7),
    event_type TEXT NOT NULL,
    event_ts TIMESTAMPTZ NOT NULL,
    interaction_weight REAL NOT NULL CHECK (interaction_weight > 0),
    session_id TEXT NOT NULL,
    event_origin TEXT NOT NULL CHECK (event_origin IN ('organic', 'semantic_trap', 'cold_start')),
    cohort_id TEXT,
    benchmark_run_id TEXT
);

ALTER TABLE ml_interaction_event_v1
    ADD COLUMN IF NOT EXISTS benchmark_run_id TEXT;
ALTER TABLE ml_interaction_event_v1
    ADD COLUMN IF NOT EXISTS session_id TEXT;
ALTER TABLE ml_interaction_event_v1
    ADD COLUMN IF NOT EXISTS event_origin TEXT;
ALTER TABLE ml_interaction_event_v1
    ADD COLUMN IF NOT EXISTS cohort_id TEXT;

DO $$ BEGIN
    ALTER TABLE ml_interaction_event_v1
        ADD CONSTRAINT ml_interaction_event_type_v1_check
        CHECK (event_type IN ('view', 'purchase')) NOT VALID;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE ml_interaction_event_v1
        ADD CONSTRAINT ml_interaction_event_origin_v1_check
        CHECK (event_origin IN ('organic', 'semantic_trap', 'cold_start')) NOT VALID;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS ml_benchmark_run_v1 (
    benchmark_run_id TEXT PRIMARY KEY,
    store_id BIGINT NOT NULL,
    seed INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('staging', 'ready', 'failed')),
    catalog_sha256 TEXT NOT NULL CHECK (catalog_sha256 ~ '^[0-9a-f]{64}$'),
    benchmark_spec_sha256 TEXT NOT NULL CHECK (benchmark_spec_sha256 ~ '^[0-9a-f]{64}$'),
    expected_event_count INTEGER NOT NULL CHECK (expected_event_count > 0),
    split_boundaries JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS ml_benchmark_item_partition_v1 (
    benchmark_run_id TEXT NOT NULL REFERENCES ml_benchmark_run_v1(benchmark_run_id) ON DELETE CASCADE,
    store_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    partition TEXT NOT NULL CHECK (partition IN ('warm', 'cold')),
    seed INTEGER NOT NULL,
    catalog_sha256 TEXT NOT NULL CHECK (catalog_sha256 ~ '^[0-9a-f]{64}$'),
    benchmark_spec_sha256 TEXT NOT NULL CHECK (benchmark_spec_sha256 ~ '^[0-9a-f]{64}$'),
    PRIMARY KEY (benchmark_run_id, store_id, product_id)
);

ALTER TABLE ml_benchmark_run_v1
    ADD COLUMN IF NOT EXISTS benchmark_spec_sha256 TEXT;
ALTER TABLE ml_benchmark_item_partition_v1
    ADD COLUMN IF NOT EXISTS benchmark_spec_sha256 TEXT;

DO $$ BEGIN
    ALTER TABLE ml_benchmark_run_v1
        ADD CONSTRAINT ml_benchmark_run_spec_sha256_check
        CHECK (benchmark_spec_sha256 ~ '^[0-9a-f]{64}$') NOT VALID;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE ml_benchmark_item_partition_v1
        ADD CONSTRAINT ml_benchmark_partition_spec_sha256_check
        CHECK (benchmark_spec_sha256 ~ '^[0-9a-f]{64}$') NOT VALID;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_ml_event_run_ts
  ON ml_interaction_event_v1(benchmark_run_id, store_id, event_ts, event_id);
CREATE INDEX IF NOT EXISTS idx_ml_partition_lookup
    ON ml_benchmark_item_partition_v1(benchmark_run_id, store_id, partition, product_id);
