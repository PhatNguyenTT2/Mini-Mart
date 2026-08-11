'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const path = require('node:path');
const { canonicalSpecSha256, loadBenchmarkSpec } = require('../benchmark-spec');

test('v5 spec is explicit, frozen, and canonically hashed', () => {
  const spec = loadBenchmarkSpec(path.resolve(__dirname, '..', 'benchmark-spec-v5.json'));
  assert.equal(spec.schema_version, '3.0.0');
  assert.equal(spec.generator_version, '5.0.0');
  assert.equal(spec.reset_confirmation, 'RESET_STORE_1_BENCHMARK_V5');
  assert.equal(spec.organic_rule_transition_fraction, 0.5);
  assert.equal(spec.transition_user_count, 2500);
  assert.equal(canonicalSpecSha256(spec).length, 64);
  assert.throws(() => { spec.store_id = 9; }, TypeError);
});

test('v4 spec is rejected after the v5 cutover', () => {
  assert.throws(
    () => loadBenchmarkSpec(path.resolve(__dirname, '..', 'benchmark-spec-v4.json')),
    /only benchmark schema 3.0.0 \/ generator 5.0.0 is supported/
  );
});
