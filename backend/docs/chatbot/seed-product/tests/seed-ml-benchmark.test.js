'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const {
  loadBenchmarkSpec,
  requireUnusedBenchmarkRun
} = require('../seed-ml-benchmark');

test('benchmark loader accepts only the canonical v5 spec', () => {
  const spec = loadBenchmarkSpec(path.resolve(__dirname, '..', 'benchmark-spec-v5.json'));
  assert.equal(spec.schema_version, '3.0.0');
  assert.equal(spec.generator_version, '5.0.0');
});

test('benchmark loader rejects archived spec generations', () => {
  const temporary = path.join(os.tmpdir(), `benchmark-spec-legacy-${process.pid}.json`);
  fs.writeFileSync(temporary, JSON.stringify({ schema_version: '1.0.0', generator_version: '3.0.0' }));
  assert.throws(
    () => loadBenchmarkSpec(temporary),
    /only benchmark schema 3.0.0 \/ generator 5.0.0 is supported/
  );
  fs.rmSync(temporary, { force: true });
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
    requireUnusedBenchmarkRun(chat, 1, 'benchmark-v5-existing'),
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

  await requireUnusedBenchmarkRun(chat, 1, 'benchmark-v5-new');
});
