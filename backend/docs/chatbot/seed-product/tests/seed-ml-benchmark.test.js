'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const {
  reclaimLegacyMlStorage,
  requireUnusedBenchmarkRun
} = require('../seed-ml-benchmark');

test('legacy reclaim preserves every benchmark lineage', async () => {
  const statements = [];
  const chat = {
    async query(sql) {
      statements.push(sql);
      if (sql.includes('SELECT count(*)::int AS total')) {
        return { rows: [{ total: 0 }] };
      }
      return { rows: [] };
    }
  };

  const result = await reclaimLegacyMlStorage(chat, 1);

  assert.deepEqual(result, { removedLegacyEvents: 0 });
  assert.equal(statements.some((sql) => /TRUNCATE/i.test(sql)), false);
  assert.equal(
    statements.some((sql) => /DELETE FROM ml_benchmark_(run|item_partition)/i.test(sql)),
    false
  );
  assert.ok(statements.some(
    (sql) => /DELETE FROM ml_interaction_event_v1[\s\S]*benchmark_run_id IS NULL/i.test(sql)
  ));
  assert.equal(
    statements.some((sql) => /DELETE FROM user_product_interaction/i.test(sql)),
    false
  );
});

test('new seed rejects an existing immutable benchmark run before mutation', async () => {
  const statements = [];
  const chat = {
    async query(sql) {
      statements.push(sql);
      return { rowCount: 1, rows: [{ status: 'ready' }] };
    }
  };

  await assert.rejects(
    requireUnusedBenchmarkRun(chat, 1, 'benchmark-v4-existing'),
    /already exists with status ready; benchmark lineages are immutable/
  );
  assert.equal(statements.length, 1);
  assert.match(statements[0], /^SELECT status/);
});

test('new seed accepts only an unused benchmark run ID', async () => {
  const chat = {
    async query() {
      return { rowCount: 0, rows: [] };
    }
  };

  await requireUnusedBenchmarkRun(chat, 1, 'benchmark-v4-new');
});
