'use strict';

const crypto = require('crypto');
const fs = require('fs');

const SUPPORTED_SCHEMA = '3.0.0';
const SUPPORTED_GENERATOR = '5.0.0';

function canonicalSpecJson(spec) {
  const canonicalize = (value) => {
    if (Array.isArray(value)) return value.map(canonicalize);
    if (value && typeof value === 'object') {
      return Object.fromEntries(
        Object.keys(value).sort().map((key) => [key, canonicalize(value[key])])
      );
    }
    return value;
  };
  return JSON.stringify(canonicalize(spec));
}

function canonicalSpecSha256(spec) {
  return crypto.createHash('sha256').update(canonicalSpecJson(spec)).digest('hex');
}

function loadBenchmarkSpec(specPath) {
  let parsed;
  try {
    parsed = JSON.parse(fs.readFileSync(specPath, 'utf8'));
  } catch (error) {
    throw new Error(`cannot load benchmark spec ${specPath}: ${error.message}`);
  }
  if (!parsed || parsed.schema_version !== SUPPORTED_SCHEMA
      || parsed.generator_version !== SUPPORTED_GENERATOR) {
    throw new Error('only benchmark schema 3.0.0 / generator 5.0.0 is supported');
  }
  for (const field of ['store_id', 'seed', 'num_users', 'num_products', 'num_events']) {
    if (!Number.isInteger(parsed[field]) || parsed[field] <= 0) {
      throw new Error(`benchmark spec ${field} must be a positive integer`);
    }
  }
  if (!Array.isArray(parsed.semantic_traps) || parsed.semantic_traps.length !== 10) {
    throw new Error('benchmark spec must contain exactly ten semantic traps');
  }
  if (parsed.reset_confirmation !== `RESET_STORE_${parsed.store_id}_BENCHMARK_V5`) {
    throw new Error('v5 benchmark spec has an invalid reset confirmation token');
  }
  if (parsed.organic_rule_transition_fraction !== 0.5
      || parsed.transition_algorithm !== 'organic-rule-transition-v1'
      || parsed.transition_user_count !== Math.floor(parsed.num_users / 2)) {
    throw new Error('v5 benchmark spec has an invalid deterministic transition contract');
  }
  if (parsed.minimum_training_target_rule_rate < 0.4
      || parsed.minimum_val_rule_target_rate < 0.4) {
    throw new Error('v5 benchmark spec target-rule floors must be at least 0.40');
  }
  return Object.freeze(parsed);
}

function benchmarkCapabilities(spec) {
  if (spec.generator_version !== SUPPORTED_GENERATOR || spec.schema_version !== SUPPORTED_SCHEMA) {
    throw new Error('benchmark capabilities require v5');
  }
  return Object.freeze({
    generatorVersion: SUPPORTED_GENERATOR,
    schemaVersion: SUPPORTED_SCHEMA,
    supportsDeterministicTransitions: true,
    requiresOrderMetadata: true,
    requiresExactTrapDirections: true,
  });
}

module.exports = { benchmarkCapabilities, canonicalSpecJson, canonicalSpecSha256, loadBenchmarkSpec };
