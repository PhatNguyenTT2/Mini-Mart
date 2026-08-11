'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const { executeBenchmarkReset, planBenchmarkReset } = require('../reset-benchmark-v5');

function client(counts) {
  return {
    queries: [],
    async query(sql, params) {
      this.queries.push({ sql, params });
      if (sql.startsWith('SELECT count')) {
        const table = sql.match(/FROM (\w+)/)?.[1];
        return { rows: [{ count: counts[table] || 0 }] };
      }
      return { rows: [], rowCount: 0 };
    }
  };
}

const spec = { store_id: 1 };

test('reset plan is read-only and scoped to store', async () => {
  const clients = { chat: client({}), order: client({}) };
  const plan = await planBenchmarkReset({ clients, spec });
  assert.equal(plan.storeId, 1);
  assert.equal(clients.chat.queries.every((query) => query.sql.startsWith('SELECT')), true);
  assert.equal(clients.order.queries.every((query) => query.sql.startsWith('SELECT')), true);
});

test('reset requires the exact confirmation token', async () => {
  const clients = { chat: client({}), order: client({}) };
  await assert.rejects(
    executeBenchmarkReset({ clients, spec, confirmation: 'yes' }),
    /exact reset confirmation/
  );
});

test('reset deletes order rows before chat derived and lineage rows', async () => {
  const clients = { chat: client({}), order: client({}) };
  const result = await executeBenchmarkReset({
    clients,
    spec,
    confirmation: 'RESET_STORE_1_BENCHMARK_V5'
  });
  assert.equal(result.status, 'reset');
  assert.match(clients.order.queries.find((query) => query.sql.startsWith('DELETE')).sql, /sale_order/);
  assert.equal(clients.chat.queries.some((query) => query.sql.includes('ml_interaction_event_v1')), true);
});
