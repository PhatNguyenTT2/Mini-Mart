'use strict';

const crypto = require('crypto');
const fs = require('fs');

const SUPPORTED = new Map([
  ['2.1.0', '4.0.0'],
  ['3.0.0', '5.0.0']
]);

function canonicalSpecSha256(spec) {
  const canonicalize = (value) => {
    if (Array.isArray(value)) return value.map(canonicalize);
    if (value && typeof value === 'object') {
      return Object.fromEntries(
        Object.keys(value).sort().map((key) => [key, canonicalize(value[key])])
      );
    }
    return value;
  };
  const canonical = JSON.stringify(canonicalize(spec));
  return crypto.createHash('sha256').update(canonical).digest('hex');
}

function loadBenchmarkSpec(specPath) {
  let parsed;
  try {
    parsed = JSON.parse(fs.readFileSync(specPath, 'utf8'));
  } catch (error) {
    throw new Error(`cannot load benchmark spec ${specPath}: ${error.message}`);
  }
  if (!parsed || !SUPPORTED.has(parsed.schema_version)
      || SUPPORTED.get(parsed.schema_version) !== parsed.generator_version) {
    throw new Error('unsupported benchmark schema/generator pair');
  }
  for (const field of ['store_id', 'seed', 'num_users', 'num_products', 'num_events']) {
    if (!Number.isInteger(parsed[field]) || parsed[field] <= 0) {
      throw new Error(`benchmark spec ${field} must be a positive integer`);
    }
  }
  if (!Array.isArray(parsed.semantic_traps) || parsed.semantic_traps.length !== 10) {
    throw new Error('benchmark spec must contain exactly ten semantic traps');
  }
  if (parsed.generator_version === '5.0.0' && parsed.reset_confirmation !== `RESET_BENCHMARK_V5_STORE_${parsed.store_id}`) {
    throw new Error('v5 benchmark spec has an invalid reset confirmation token');
  }
  return Object.freeze(parsed);
}

module.exports = { canonicalSpecSha256, loadBenchmarkSpec };
