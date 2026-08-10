'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../../../.env') });
const { Client } = require('pg');

function mulberry32(seed) {
  let state = seed >>> 0;
  return () => {
    state += 0x6D2B79F5;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function shuffle(values, random) {
  const result = [...values];
  for (let index = result.length - 1; index > 0; index -= 1) {
    const selected = Math.floor(random() * (index + 1));
    [result[index], result[selected]] = [result[selected], result[index]];
  }
  return result;
}

function dbConfig(connectionString) {
  if (!connectionString) throw new Error('required database URL is missing');
  const local = /localhost|127\.0\.0\.1/.test(connectionString);
  if (process.env.DB_SSL === 'false' || local) return { connectionString, ssl: false };
  const caPath = process.env.SUPABASE_DB_CA_PATH || process.env.DB_SSL_CA_PATH;
  if (!caPath) {
    throw new Error('SUPABASE_DB_CA_PATH is required for verified remote PostgreSQL TLS');
  }
  return {
    connectionString,
    ssl: {
      ca: fs.readFileSync(path.resolve(caPath), 'utf8'),
      rejectUnauthorized: true
    }
  };
}

function catalogChecksum(products) {
  const payload = products
    .map((product) => `${Number(product.product_id)}\t${Number(product.category_id)}\t${product.name}`)
    .join('\n');
  return crypto.createHash('sha256').update(payload).digest('hex');
}

function selectColdProducts(products, spec) {
  const excluded = new Set(spec.semantic_traps.flatMap((trap) => [trap.anchor, ...trap.targets]));
  const groups = new Map();
  for (const product of products) {
    const id = Number(product.product_id);
    if (excluded.has(id)) continue;
    const category = Number(product.category_id);
    if (!groups.has(category)) groups.set(category, []);
    groups.get(category).push(id);
  }
  const random = mulberry32(spec.seed);
  const categories = [...groups.keys()].sort((left, right) => left - right);
  const shuffled = new Map(categories.map((category) => [category, shuffle(groups.get(category), random)]));
  const cold = [];
  let cursor = 0;
  while (cold.length < spec.num_cold_products) {
    const category = categories[cursor % categories.length];
    const values = shuffled.get(category);
    if (values.length) cold.push(values.pop());
    cursor += 1;
    if (cursor > spec.num_products * 10) throw new Error('cannot allocate cold partition');
  }
  return cold.sort((left, right) => left - right);
}

async function connectDatabases() {
  const clients = {
    auth: new Client(dbConfig(process.env.AUTH_DATABASE_URL || process.env.DATABASE_URL)),
    chat: new Client(dbConfig(process.env.CHATBOT_DATABASE_URL)),
    catalog: new Client(dbConfig(process.env.CATALOG_DATABASE_URL)),
    order: new Client(dbConfig(process.env.ORDER_DATABASE_URL))
  };
  await Promise.all(Object.values(clients).map((client) => client.connect()));
  return clients;
}

async function ensureBenchmarkSchema(chat) {
  await chat.query('BEGIN');
  try {
    await chat.query('SET TRANSACTION READ WRITE');
    await chat.query(`
    CREATE TABLE IF NOT EXISTS ml_interaction_event_v1 (
      event_id TEXT PRIMARY KEY,
      store_id BIGINT NOT NULL,
      user_id BIGINT NOT NULL,
      product_id BIGINT NOT NULL,
      persona_cluster SMALLINT NOT NULL CHECK (persona_cluster BETWEEN 0 AND 7),
      event_type TEXT NOT NULL CHECK (event_type IN ('view','purchase')),
      event_ts TIMESTAMPTZ NOT NULL,
      interaction_weight REAL NOT NULL CHECK (interaction_weight > 0),
      session_id TEXT NOT NULL,
      event_origin TEXT NOT NULL CHECK (event_origin IN ('organic','semantic_trap','cold_start')),
      cohort_id TEXT,
      benchmark_run_id TEXT
    );
    CREATE TABLE IF NOT EXISTS ml_benchmark_run_v1 (
      benchmark_run_id TEXT PRIMARY KEY,
      store_id BIGINT NOT NULL,
      seed INTEGER NOT NULL,
      status TEXT NOT NULL CHECK (status IN ('staging','ready','failed')),
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
      partition TEXT NOT NULL CHECK (partition IN ('warm','cold')),
      seed INTEGER NOT NULL,
      catalog_sha256 TEXT NOT NULL CHECK (catalog_sha256 ~ '^[0-9a-f]{64}$'),
      benchmark_spec_sha256 TEXT NOT NULL CHECK (benchmark_spec_sha256 ~ '^[0-9a-f]{64}$'),
      PRIMARY KEY (benchmark_run_id, store_id, product_id)
    );
    ALTER TABLE ml_interaction_event_v1 ADD COLUMN IF NOT EXISTS benchmark_run_id TEXT;
    ALTER TABLE ml_interaction_event_v1 ADD COLUMN IF NOT EXISTS session_id TEXT;
    ALTER TABLE ml_interaction_event_v1 ADD COLUMN IF NOT EXISTS event_origin TEXT;
    ALTER TABLE ml_interaction_event_v1 ADD COLUMN IF NOT EXISTS cohort_id TEXT;
    ALTER TABLE ml_benchmark_run_v1 ADD COLUMN IF NOT EXISTS benchmark_spec_sha256 TEXT;
    ALTER TABLE ml_benchmark_item_partition_v1 ADD COLUMN IF NOT EXISTS benchmark_spec_sha256 TEXT;
    DO $$ BEGIN
      ALTER TABLE ml_interaction_event_v1
        ADD CONSTRAINT ml_interaction_event_type_v1_check
        CHECK (event_type IN ('view','purchase')) NOT VALID;
    EXCEPTION WHEN duplicate_object THEN NULL;
    END $$;
    DO $$ BEGIN
      ALTER TABLE ml_interaction_event_v1
        ADD CONSTRAINT ml_interaction_event_origin_v1_check
        CHECK (event_origin IN ('organic','semantic_trap','cold_start')) NOT VALID;
    EXCEPTION WHEN duplicate_object THEN NULL;
    END $$;
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
    -- Snapshot extraction is the only steady-state consumer.  Session/origin
    -- gates use grouped scans during rebuild; four extra indexes exceeded the
    -- managed benchmark database storage quota without serving request traffic.
    CREATE INDEX IF NOT EXISTS idx_ml_event_run_ts
      ON ml_interaction_event_v1(benchmark_run_id, store_id, event_ts, event_id);
    CREATE INDEX IF NOT EXISTS idx_ml_partition_lookup
      ON ml_benchmark_item_partition_v1(benchmark_run_id,store_id,partition,product_id);
    `);
    await chat.query('COMMIT');
  } catch (error) {
    await chat.query('ROLLBACK');
    throw error;
  }
}

module.exports = {
  catalogChecksum,
  connectDatabases,
  ensureBenchmarkSchema,
  mulberry32,
  selectColdProducts,
  shuffle
};
