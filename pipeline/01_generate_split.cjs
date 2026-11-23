'use strict';
// Stage 1: regenerate the synthetic retail dataset offline from the Mini-Mart data generator.
// `pg` is replaced by a stub that cannot connect, so no database is touched. Events are captured at
// the insert call and orders come from the pure order plan.
// --test-reseed <n> redraws only the TEST split; TRAIN and VAL stay byte-identical.
// Usage: node 01_generate_split.cjs --generator-root <Mini-Mart>/backend/docs/chatbot //          --seed <n> [--test-reseed <n>] --out <dir>

const crypto = require('crypto');
const fs = require('fs');
const Module = require('module');
const path = require('path');

const generatorIndex = process.argv.indexOf('--generator-root');
if (generatorIndex < 0) throw new Error('--generator-root <Mini-Mart>/backend/docs/chatbot is required');
const REPO = path.resolve(process.argv[generatorIndex + 1]);
const SEED_DIR = path.join(REPO, 'seed-product');
const CATALOG_SQL = path.join(REPO, 'catalog-bootstrap/seed-5000.sql');
const FIRST_ORDER_ID = 323643;

const originalLoad = Module._load;
Module._load = function load(request, parent, isMain) {
  if (request === 'pg') {
    return { Client: class { constructor() { throw new Error('database access is disabled'); } } };
  }
  if (request === 'dotenv') return { config() { return {}; } };
  return originalLoad.call(this, request, parent, isMain);
};

const { catalogChecksum, mulberry32, selectColdProducts } = require(path.join(SEED_DIR, 'benchmark-lib'));
const {
  buildPersonaAssignments,
  buildUserAffinities,
  buildOrganicBundleTemplates
} = require(path.join(SEED_DIR, 'benchmark-affinity'));
// Applies one in-memory change to the unmodified generator: the organic random stream is replaced
// just before the test split, so TRAIN and VAL stay byte-identical. Without --test-reseed the file
// runs unchanged. The source file on disk is never edited.
function loadEventGenerator() {
  const file = path.join(SEED_DIR, 'seed-ml-events.js');
  const index = process.argv.indexOf('--test-reseed');
  if (index < 0) return require(file);
  const reseed = Number(process.argv[index + 1]);
  if (!Number.isInteger(reseed)) throw new Error('--test-reseed needs an integer');
  let source = fs.readFileSync(file, 'utf8');
  const stream = 'const random = mulberry32(affinityModel ? spec.seed + 17 : spec.seed);';
  const loop = 'for (const definition of definitions) {';
  if (source.split(stream).length !== 2 || source.split(loop).length !== 2) {
    throw new Error('generator source no longer matches the expected lines');
  }
  source = source.replace(stream, stream.replace('const random', 'let random'));
  source = source.replace(loop, `${loop}\n      if (definition.split === 'test') random = mulberry32(${reseed});`);
  const patched = new Module(file, module);
  patched.filename = file;
  patched.paths = Module._nodeModulePaths(path.dirname(file));
  patched._compile(source, file);
  return patched.exports;
}

const { seedMlEvents } = loadEventGenerator();
const { generateOrderPlan } = require(path.join(SEED_DIR, 'mock-orders'));
const { canonicalSpecSha256, loadBenchmarkSpec } = require(path.join(SEED_DIR, 'benchmark-spec'));

class CaptureComplete extends Error {}

function argument(name) {
  const index = process.argv.indexOf(name);
  if (index < 0) throw new Error(`${name} is required`);
  return process.argv[index + 1];
}

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonicalize(value[key])]));
  }
  return value;
}

function canonicalLine(value) {
  return `${JSON.stringify(canonicalize(value))}\n`;
}

function unescapeSql(value) {
  return value.replaceAll("''", "'");
}

function loadCatalog() {
  const sql = fs.readFileSync(CATALOG_SQL, 'utf8');
  const categoryStart = sql.indexOf('INSERT INTO category');
  const productStart = sql.indexOf('INSERT INTO product');
  const categoryPattern = /^\s*\((\d+),\s*(?:NULL|\d+),\s*'((?:''|[^'])*)',/u;
  const productPattern = /^\s*\((\d+),\s*(\d+),\s*'((?:''|[^'])*)',\s*(\d+(?:\.\d+)?),\s*'((?:''|[^'])*)',/u;
  const categories = new Map();
  for (const line of sql.slice(categoryStart, productStart).split(/\r?\n/u)) {
    const match = categoryPattern.exec(line);
    if (match) categories.set(Number(match[1]), unescapeSql(match[2]));
  }
  const products = [];
  for (const line of sql.slice(productStart).split(/\r?\n/u)) {
    const match = productPattern.exec(line);
    if (!match) continue;
    products.push({
      product_id: Number(match[1]),
      category_id: Number(match[2]),
      name: unescapeSql(match[3]),
      unit_price: Number(match[4]),
      vendor: unescapeSql(match[5]) || 'unknown'
    });
  }
  products.sort((left, right) => left.product_id - right.product_id);
  return { categories, products };
}

// Same body as buildAffinityModel in seed-ml-benchmark.js, which does not export it.
function buildAffinityModel({ spec, products, coldProducts, users }) {
  const affinityRandom = mulberry32(spec.seed);
  const personaByUser = buildPersonaAssignments(users, spec.persona_distribution, affinityRandom);
  const warmProducts = products
    .map((product) => Number(product.product_id))
    .filter((id) => !coldProducts.includes(id));
  const affinity = buildUserAffinities(
    products, warmProducts, users, personaByUser, spec.persona_distribution.length
  );
  const fixtureProducts = spec.semantic_traps.flatMap((trap) => [trap.anchor, ...trap.targets]);
  const bundleTemplates = buildOrganicBundleTemplates({
    products,
    warmProducts,
    fixtureProducts,
    personaByUser,
    affinityByUser: affinity.affinityByUser,
    categoryPersona: affinity.categoryPersona,
    preferredProducts: affinity.preferredProducts,
    spec
  });
  return { personaByUser, ...affinity, bundleTemplates };
}

function captureClient(events) {
  return {
    async query(sql, parameters) {
      if (sql.includes('INSERT INTO ml_interaction_event_v1')) {
        const [ids, , users, items, personas, types, times, weights, sessions, origins, cohorts] = parameters;
        ids.forEach((id, index) => events.push({
          id,
          user: users[index],
          item: items[index],
          persona: personas[index],
          type: types[index],
          time: new Date(times[index]),
          weight: weights[index],
          session: sessions[index],
          origin: origins[index],
          cohort: cohorts[index]
        }));
        return { rows: [] };
      }
      if (sql.includes('count(*)::int AS events')) throw new CaptureComplete();
      if (sql.includes('count(*)::int AS count')) return { rows: [{ count: 0 }] };
      return { rows: [] };
    }
  };
}

async function main() {
  const seed = Number(argument('--seed'));
  const out = argument('--out');
  fs.mkdirSync(out, { recursive: true });
  const spec = JSON.parse(JSON.stringify(loadBenchmarkSpec(path.join(SEED_DIR, 'benchmark-spec-v5.json'))));
  spec.seed = seed;
  const { categories, products } = loadCatalog();
  if (products.length !== spec.num_products) throw new Error(`catalog has ${products.length} products`);
  const catalogHash = catalogChecksum(products);
  const specHash = canonicalSpecSha256(spec);
  const major = String(spec.generator_version).split('.')[0];
  const runId = `benchmark-v${major}-s${spec.seed}-${catalogHash.slice(0, 10)}-${specHash.slice(0, 10)}`;
  const coldProducts = selectColdProducts(products, spec);
  const coldSet = new Set(coldProducts);
  const users = Array.from({ length: spec.num_users }, (_, index) => index + 1);
  const affinityModel = buildAffinityModel({ spec, products, coldProducts, users });

  const events = [];
  try {
    await seedMlEvents({
      client: captureClient(events), spec, runId, catalogHash, specHash, products, coldProducts, affinityModel
    });
    throw new Error('event generation ended without reaching the validation queries');
  } catch (error) {
    if (!(error instanceof CaptureComplete)) throw error;
  }
  if (events.length !== spec.num_events) throw new Error(`captured ${events.length} events`);
  const byIdentity = (left, right) => {
    const delta = left.time - right.time;
    if (delta) return delta;
    if (left.id === right.id) return 0;
    return left.id < right.id ? -1 : 1;
  };
  events.sort(byIdentity);
  fs.writeFileSync(path.join(out, 'events.jsonl'), events.map((row) => canonicalLine({
    cohort_id: row.cohort,
    event_origin: row.origin,
    event_ts: row.time.toISOString(),
    event_type: row.type,
    interaction_weight: row.weight,
    persona_cluster: row.persona,
    raw_event_id: row.id,
    raw_item_id: row.item,
    raw_user_id: row.user,
    session_id: row.session
  })).join(''));

  const orders = generateOrderPlan({ spec, users, products, coldProducts, affinityModel })
    .map((order, index) => ({ ...order, id: FIRST_ORDER_ID + index }))
    .sort((left, right) => new Date(left.orderDate) - new Date(right.orderDate) || left.id - right.id);
  fs.writeFileSync(path.join(out, 'baskets.jsonl'), orders.map((order) => canonicalLine({
    basket_origin: order.kind,
    basket_ts: new Date(order.orderDate).toISOString(),
    raw_basket_id: String(order.id),
    raw_item_ids: [...new Set(order.items.map((item) => Number(item.productId)))].sort((a, b) => a - b),
    raw_user_id: order.userId
  })).join(''));

  fs.writeFileSync(path.join(out, 'items.jsonl'), products.map((product) => canonicalLine({
    category: categories.get(product.category_id),
    name: product.name,
    partition: coldSet.has(product.product_id) ? 'cold' : 'warm',
    price: product.unit_price,
    raw_item_id: product.product_id,
    vendor: product.vendor
  })).join(''));
  fs.writeFileSync(path.join(out, 'users.jsonl'), users.map((id) => canonicalLine({ raw_user_id: id })).join(''));
  fs.writeFileSync(path.join(out, 'benchmark_spec.json'), `${JSON.stringify(canonicalize(spec), null, 2)}\n`);

  const hash = (name) => crypto.createHash('sha256').update(fs.readFileSync(path.join(out, name))).digest('hex');
  const report = {
    runId,
    catalogHash,
    specHash,
    seed,
    events: events.length,
    orders: orders.length,
    files: Object.fromEntries(['events.jsonl', 'baskets.jsonl', 'items.jsonl', 'users.jsonl'].map((n) => [n, hash(n)]))
  };
  fs.writeFileSync(path.join(out, 'generation_report.json'), `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify(report));
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exitCode = 1;
});
