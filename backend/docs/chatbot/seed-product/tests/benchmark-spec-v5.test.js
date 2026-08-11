'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const path = require('node:path');
const { canonicalSpecSha256, loadBenchmarkSpec } = require('../benchmark-spec');

test('v5 spec is explicit, frozen, and canonically hashed', () => {
  const spec = loadBenchmarkSpec(path.resolve(__dirname, '..', 'benchmark-spec-v5.json'));
  assert.equal(spec.schema_version, '3.0.0');
  assert.equal(spec.generator_version, '5.0.0');
  assert.equal(spec.reset_confirmation, 'RESET_BENCHMARK_V5_STORE_1');
  assert.equal(canonicalSpecSha256(spec).length, 64);
  assert.throws(() => { spec.store_id = 9; }, TypeError);
});

test('v4 spec remains loadable for read-only R0 replay', () => {
  const spec = loadBenchmarkSpec(path.resolve(__dirname, '..', 'benchmark-spec-v4.json'));
  assert.equal(spec.generator_version, '4.0.0');
});
