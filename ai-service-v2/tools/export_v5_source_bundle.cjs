'use strict';

const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const { createRequire } = require('node:module');
const path = require('node:path');

const READ_ONLY_BEGIN = 'BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY';
const SOURCE_QUERIES = Object.freeze({
  run: `SELECT benchmark_run_id,store_id,seed,status,catalog_sha256,
               benchmark_spec_sha256,expected_event_count,split_boundaries,published_at
        FROM ml_benchmark_run_v1
        WHERE store_id=$1 AND benchmark_run_id=$2`,
  partition: `SELECT product_id AS raw_item_id,partition,seed,catalog_sha256,
                     benchmark_spec_sha256
              FROM ml_benchmark_item_partition_v1
              WHERE store_id=$1 AND benchmark_run_id=$2
              ORDER BY product_id`,
  catalog: `SELECT p.id AS raw_item_id,p.category_id,p.name,c.name AS category,
                   COALESCE(p.vendor,'unknown') AS vendor,p.unit_price AS price
            FROM product p JOIN category c ON c.id=p.category_id
            WHERE p.id=ANY($1::bigint[])
            ORDER BY p.id`,
  events: `SELECT event_id AS raw_event_id,user_id AS raw_user_id,
                  product_id AS raw_item_id,event_type,event_ts,event_origin,
                  session_id,cohort_id,persona_cluster,interaction_weight
           FROM ml_interaction_event_v1
           WHERE store_id=$1 AND benchmark_run_id=$2
           ORDER BY event_ts,event_id`,
  baskets: `SELECT o.id::text AS raw_basket_id,o.customer_id AS raw_user_id,
                   o.order_date AS basket_ts,o.benchmark_kind AS basket_origin,
                   array_agg(DISTINCT d.product_id ORDER BY d.product_id) AS raw_item_ids
            FROM sale_order o JOIN sale_order_detail d ON d.order_id=o.id
            WHERE o.store_id=$1 AND o.benchmark_run_id=$2
              AND o.status='delivered' AND o.payment_status='paid'
              AND o.order_date >= $3 AND o.order_date <= $4
              AND d.product_id IS NOT NULL
            GROUP BY o.id,o.customer_id,o.order_date,o.benchmark_kind
            ORDER BY o.order_date,o.id`
});

const SHA256 = /^[0-9a-f]{64}$/;
const COMMIT = /^[0-9a-f]{40}$/;
const CATALOG_EXPORT_FIELDS = Object.freeze(['category', 'name', 'price', 'vendor']);
const REAL_LICENSE_STATUSES = new Set([
  'APPROVED_PRIVATE_RESEARCH',
  'APPROVED_RESEARCH_AND_REDISTRIBUTION',
  'OPEN_LICENSE_VERIFIED'
]);

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.keys(value).sort().map((key) => [key, canonicalize(value[key])])
    );
  }
  if (typeof value === 'number' && !Number.isFinite(value)) {
    throw new Error('non-finite number cannot be serialized');
  }
  return value;
}

function canonicalJson(value) {
  return JSON.stringify(canonicalize(value));
}

function sha256(payload) {
  return crypto.createHash('sha256').update(payload).digest('hex');
}

function sha256File(filePath) {
  return sha256(fs.readFileSync(filePath));
}

function integer(value, name, minimum = 0) {
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed < minimum) {
    throw new Error(`${name} must be an integer >= ${minimum}`);
  }
  return parsed;
}

function finiteNumber(value, name, minimum = 0) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < minimum) {
    throw new Error(`${name} must be a finite number >= ${minimum}`);
  }
  return parsed;
}

function nonempty(value, name) {
  if (typeof value !== 'string' || !value) throw new Error(`${name} must be non-empty`);
  return value;
}

function isoTimestamp(value, name) {
  const parsed = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(parsed.valueOf())) throw new Error(`${name} is not a timestamp`);
  return parsed.toISOString();
}

function assertCatalogAudit(audit, fixture) {
  const fields = new Set([
    'schema_version',
    'catalog_provenance_status',
    'catalog_license_status',
    'catalog_language_status',
    'export_authorized',
    'redistribution_authorized',
    'approved_fields',
    'evidence_sha256'
  ]);
  if (!audit || typeof audit !== 'object' || Array.isArray(audit)) {
    throw new Error('catalog audit must be an object');
  }
  if (Object.keys(audit).length !== fields.size || Object.keys(audit).some((key) => !fields.has(key))) {
    throw new Error('catalog audit fields do not match contract');
  }
  if (audit.schema_version !== 'catalog-audit/1.1') {
    throw new Error('unsupported catalog audit schema');
  }
  if (audit.export_authorized !== true || typeof audit.redistribution_authorized !== 'boolean') {
    throw new Error('catalog export is not authorized');
  }
  if (
    !Array.isArray(audit.approved_fields)
    || canonicalJson(audit.approved_fields) !== canonicalJson(CATALOG_EXPORT_FIELDS)
  ) {
    throw new Error('catalog audit does not approve the exact exported fields');
  }
  if (fixture) {
    if (
      audit.catalog_provenance_status !== 'TEST_ONLY'
      || audit.catalog_license_status !== 'TEST_ONLY'
      || audit.catalog_language_status !== 'TEST_ONLY'
      || audit.redistribution_authorized !== false
    ) {
      throw new Error('fixture catalog audit is not admitted');
    }
  } else {
    if (audit.catalog_provenance_status !== 'VERIFIED') {
      throw new Error('catalog provenance is not verified');
    }
    if (!REAL_LICENSE_STATUSES.has(audit.catalog_license_status)) {
      throw new Error('catalog license or permission is not admitted');
    }
    if (!['PENDING_POST_EXPORT_AUDIT', 'AUDITED'].includes(audit.catalog_language_status)) {
      throw new Error('catalog language status is invalid');
    }
    const redistributable = audit.catalog_license_status !== 'APPROVED_PRIVATE_RESEARCH';
    if (audit.redistribution_authorized !== redistributable) {
      throw new Error('catalog redistribution status conflicts with the admitted license scope');
    }
  }
  if (
    !Array.isArray(audit.evidence_sha256)
    || audit.evidence_sha256.length === 0
    || audit.evidence_sha256.some((value) => typeof value !== 'string' || !SHA256.test(value))
  ) {
    throw new Error('catalog audit evidence hashes are invalid');
  }
}

function catalogAuditSha256(audit) {
  return sha256(Buffer.from(`${canonicalJson(audit)}\n`, 'utf8'));
}

function normalizedSpec(spec) {
  const splitCounts = spec.split_counts;
  const cutoffs = spec.cutoffs;
  if (!splitCounts || !cutoffs) throw new Error('benchmark spec lacks split contract');
  return {
    schema_version: nonempty(spec.schema_version, 'spec.schema_version'),
    generator_version: nonempty(spec.generator_version, 'spec.generator_version'),
    seed: integer(spec.seed, 'spec.seed'),
    store_id: integer(spec.store_id, 'spec.store_id', 1),
    num_users: integer(spec.num_users, 'spec.num_users', 1),
    num_products: integer(spec.num_products, 'spec.num_products', 1),
    num_cold_products: integer(spec.num_cold_products, 'spec.num_cold_products'),
    num_events: integer(spec.num_events, 'spec.num_events', 1),
    num_orders: integer(spec.num_orders, 'spec.num_orders', 1),
    split_counts: {
      train: integer(splitCounts.train, 'spec.split_counts.train', 1),
      val: integer(splitCounts.val, 'spec.split_counts.val', 1),
      test: integer(splitCounts.test, 'spec.split_counts.test', 1)
    },
    cutoffs: {
      train_start: nonempty(cutoffs.train_start, 'spec.cutoffs.train_start'),
      train_end: nonempty(cutoffs.train_end, 'spec.cutoffs.train_end'),
      val_start: nonempty(cutoffs.val_start, 'spec.cutoffs.val_start'),
      val_end: nonempty(cutoffs.val_end, 'spec.cutoffs.val_end'),
      test_start: nonempty(cutoffs.test_start, 'spec.cutoffs.test_start'),
      test_end: nonempty(cutoffs.test_end, 'spec.cutoffs.test_end')
    }
  };
}

function generatorTreeHash(generatorPaths, repoRoot) {
  const rows = generatorPaths.map((filePath) => {
    const absolute = path.resolve(filePath);
    const relative = path.relative(repoRoot, absolute).replaceAll('\\', '/');
    if (!relative || relative.startsWith('../') || path.isAbsolute(relative)) {
      throw new Error('generator source must be inside the repository');
    }
    return `${sha256File(absolute)}  ${relative}`;
  }).sort();
  if (new Set(rows.map((row) => row.slice(66))).size !== rows.length) {
    throw new Error('generator source paths must be unique');
  }
  return sha256(`${rows.join('\n')}\n`);
}

function assertGeneratorCommitBinding({
  generatorPaths,
  repoRoot,
  sourceCommit,
  readCommittedFile = (commit, relative) => execFileSync(
    'git', ['show', `${commit}:${relative}`], { cwd: repoRoot, encoding: null, maxBuffer: 16 * 1024 * 1024 }
  )
}) {
  if (!COMMIT.test(sourceCommit)) throw new Error('sourceCommit must be a full lowercase commit SHA');
  for (const filePath of generatorPaths) {
    const absolute = path.resolve(filePath);
    const relative = path.relative(repoRoot, absolute).replaceAll('\\', '/');
    if (!relative || relative.startsWith('../') || path.isAbsolute(relative)) {
      throw new Error('generator source must be inside the repository');
    }
    const committed = readCommittedFile(sourceCommit, relative);
    if (sha256(committed) !== sha256File(absolute)) {
      throw new Error(`generator source differs from ${sourceCommit}:${relative}`);
    }
  }
}

function catalogChecksum(rows) {
  const payload = rows.map((row) => (
    `${integer(row.raw_item_id, 'catalog.raw_item_id', 1)}\t`
    + `${integer(row.category_id, 'catalog.category_id', 1)}\t`
    + nonempty(row.name, 'catalog.name')
  )).join('\n');
  return sha256(payload);
}

function checkRows({ spec, specHash, runId, runRows, partitionRows, catalogRows, eventRows, basketRows }) {
  if (runRows.length !== 1) throw new Error('exactly one benchmark run row is required');
  const run = runRows[0];
  if (
    run.benchmark_run_id !== runId
    || integer(run.store_id, 'run.store_id', 1) !== spec.store_id
    || integer(run.seed, 'run.seed') !== spec.seed
    || run.status !== 'ready'
    || run.benchmark_spec_sha256 !== specHash
    || integer(run.expected_event_count, 'run.expected_event_count', 1) !== spec.num_events
    || canonicalJson(run.split_boundaries) !== canonicalJson(spec.cutoffs)
    || !run.published_at
  ) {
    throw new Error('benchmark run lineage is not ready or does not match the spec');
  }
  if (!SHA256.test(run.catalog_sha256) || catalogChecksum(catalogRows) !== run.catalog_sha256) {
    throw new Error('catalog checksum does not match benchmark run');
  }
  const expectedRunId = `benchmark-v${String(spec.generator_version).split('.')[0]}`
    + `-s${spec.seed}-${run.catalog_sha256.slice(0, 10)}-${specHash.slice(0, 10)}`;
  if (runId !== expectedRunId) throw new Error('benchmark run ID does not match frozen lineage');
  if (
    partitionRows.length !== spec.num_products
    || catalogRows.length !== spec.num_products
    || eventRows.length !== spec.num_events
    || basketRows.length !== spec.num_orders
  ) {
    throw new Error('source row counts do not match benchmark spec');
  }
  const coldCount = partitionRows.filter((row) => row.partition === 'cold').length;
  if (coldCount !== spec.num_cold_products) throw new Error('cold partition count mismatch');
  const partitionIds = partitionRows.map(
    (row) => integer(row.raw_item_id, 'partition.raw_item_id', 1)
  );
  const catalogIds = catalogRows.map((row) => integer(row.raw_item_id, 'catalog.raw_item_id', 1));
  if (
    new Set(partitionIds).size !== partitionIds.length
    || new Set(catalogIds).size !== catalogIds.length
    || canonicalJson([...partitionIds].sort((left, right) => left - right))
      !== canonicalJson([...catalogIds].sort((left, right) => left - right))
  ) {
    throw new Error('catalog and item-partition ID sets do not match exactly');
  }
  for (const row of partitionRows) {
    if (
      !['warm', 'cold'].includes(row.partition)
      || integer(row.seed, 'partition.seed') !== spec.seed
      || row.catalog_sha256 !== run.catalog_sha256
      || row.benchmark_spec_sha256 !== specHash
    ) {
      throw new Error('item partition lineage mismatch');
    }
  }
  return run;
}

function prepareRows({ spec, partitionRows, catalogRows, eventRows, basketRows }) {
  const partition = new Map(
    partitionRows.map((row) => [integer(row.raw_item_id, 'partition.raw_item_id', 1), row.partition])
  );
  const items = catalogRows.map((row) => {
    const rawItemId = integer(row.raw_item_id, 'catalog.raw_item_id', 1);
    if (!partition.has(rawItemId)) throw new Error('catalog item is absent from partition');
    return {
      raw_item_id: rawItemId,
      name: nonempty(row.name, 'catalog.name'),
      category: nonempty(row.category, 'catalog.category'),
      vendor: nonempty(row.vendor, 'catalog.vendor'),
      price: finiteNumber(row.price, 'catalog.price'),
      partition: partition.get(rawItemId)
    };
  });
  const itemIds = new Set(items.map((row) => row.raw_item_id));
  const eventIds = new Set();
  const splitCounts = { train: 0, val: 0, test: 0 };
  let previousEventKey = null;
  const events = eventRows.map((row) => {
    const event = {
      raw_event_id: nonempty(row.raw_event_id, 'event.raw_event_id'),
      raw_user_id: integer(row.raw_user_id, 'event.raw_user_id', 1),
      raw_item_id: integer(row.raw_item_id, 'event.raw_item_id', 1),
      event_type: nonempty(row.event_type, 'event.event_type'),
      event_ts: isoTimestamp(row.event_ts, 'event.event_ts'),
      event_origin: nonempty(row.event_origin, 'event.event_origin'),
      session_id: nonempty(row.session_id, 'event.session_id'),
      cohort_id: row.cohort_id === null ? null : nonempty(row.cohort_id, 'event.cohort_id'),
      persona_cluster: integer(row.persona_cluster, 'event.persona_cluster'),
      interaction_weight: finiteNumber(
        row.interaction_weight, 'event.interaction_weight', Number.EPSILON
      )
    };
    if (eventIds.has(event.raw_event_id)) throw new Error('event IDs must be unique');
    eventIds.add(event.raw_event_id);
    if (!itemIds.has(event.raw_item_id)) throw new Error('event references an unknown catalog item');
    if (!['view', 'purchase'].includes(event.event_type)) throw new Error('event type is invalid');
    if (!['organic', 'semantic_trap', 'cold_start'].includes(event.event_origin)) {
      throw new Error('event origin is invalid');
    }
    if (event.persona_cluster > 7) throw new Error('event persona cluster is invalid');
    const eventKey = `${event.event_ts}\t${event.raw_event_id}`;
    if (previousEventKey !== null && eventKey < previousEventKey) {
      throw new Error('events are not in canonical source order');
    }
    previousEventKey = eventKey;
    const instant = Date.parse(event.event_ts);
    const split = ['train', 'val', 'test'].find((candidate) => (
      instant >= Date.parse(spec.cutoffs[`${candidate}_start`])
      && instant <= Date.parse(spec.cutoffs[`${candidate}_end`])
    ));
    if (!split) throw new Error('event timestamp is outside the frozen split boundaries');
    splitCounts[split] += 1;
    return event;
  });
  if (canonicalJson(splitCounts) !== canonicalJson(spec.split_counts)) {
    throw new Error('event split counts do not match benchmark spec');
  }
  const users = [...new Set(events.map((row) => row.raw_user_id))]
    .sort((left, right) => left - right)
    .map((rawUserId) => ({ raw_user_id: rawUserId }));
  if (users.length !== spec.num_users) throw new Error('event user coverage does not match spec');
  const userIds = new Set(users.map((row) => row.raw_user_id));
  const basketIds = new Set();
  let previousBasketKey = null;
  const baskets = basketRows.map((row) => {
    const rawItems = row.raw_item_ids;
    if (!Array.isArray(rawItems)) throw new Error('basket.raw_item_ids must be an array');
    const basket = {
      raw_basket_id: nonempty(String(row.raw_basket_id), 'basket.raw_basket_id'),
      raw_user_id: integer(row.raw_user_id, 'basket.raw_user_id', 1),
      basket_ts: isoTimestamp(row.basket_ts, 'basket.basket_ts'),
      basket_origin: nonempty(row.basket_origin, 'basket.basket_origin'),
      raw_item_ids: rawItems.map((value) => integer(value, 'basket.raw_item_id', 1))
    };
    if (basketIds.has(basket.raw_basket_id)) throw new Error('basket IDs must be unique');
    basketIds.add(basket.raw_basket_id);
    if (!userIds.has(basket.raw_user_id)) throw new Error('basket references an unknown user');
    if (
      basket.raw_item_ids.length < 2
      || new Set(basket.raw_item_ids).size !== basket.raw_item_ids.length
      || basket.raw_item_ids.some((itemId) => !itemIds.has(itemId))
    ) {
      throw new Error('basket items must be unique known catalog items');
    }
    if (!['organic', 'semantic_trap'].includes(basket.basket_origin)) {
      throw new Error('basket origin is invalid');
    }
    const instant = Date.parse(basket.basket_ts);
    if (
      instant < Date.parse(spec.cutoffs.train_start)
      || instant > Date.parse(spec.cutoffs.train_end)
    ) {
      throw new Error('basket timestamp is outside TRAIN');
    }
    const basketKey = `${basket.basket_ts}\t${basket.raw_basket_id.padStart(32, '0')}`;
    if (previousBasketKey !== null && basketKey < previousBasketKey) {
      throw new Error('baskets are not in canonical source order');
    }
    previousBasketKey = basketKey;
    return basket;
  });
  return { users, items, events, baskets };
}

function writeJson(filePath, value) {
  fs.writeFileSync(filePath, `${canonicalJson(value)}\n`, { flag: 'wx' });
}

function writeJsonl(filePath, rows) {
  fs.writeFileSync(filePath, `${rows.map(canonicalJson).join('\n')}\n`, { flag: 'wx' });
}

async function rollbackAll(clients) {
  await Promise.allSettled(Object.values(clients).map((client) => client.query('ROLLBACK')));
}

async function exportSourceBundle(options) {
  const {
    clients,
    runId,
    spec,
    specPath,
    audit,
    catalogAuditSha256: declaredCatalogAuditSha256,
    sourceCommit,
    generatorPaths,
    outputRoot
  } = options;
  if (!COMMIT.test(sourceCommit)) throw new Error('sourceCommit must be a full lowercase commit SHA');
  if (
    !SHA256.test(declaredCatalogAuditSha256)
    || declaredCatalogAuditSha256 !== catalogAuditSha256(audit)
  ) {
    throw new Error('catalogAuditSha256 does not match canonical catalog audit bytes');
  }
  const fixture = sourceCommit === '0'.repeat(40);
  assertCatalogAudit(audit, fixture);
  const normalized = normalizedSpec(spec);
  const specHash = sha256(canonicalJson(spec));
  const target = path.resolve(outputRoot);
  const staging = path.join(path.dirname(target), `.${path.basename(target)}.staging`);
  if (fs.existsSync(target) || fs.existsSync(staging)) throw new Error('output or staging root already exists');

  const names = ['chat', 'catalog', 'order'];
  if (names.some((name) => !clients[name] || typeof clients[name].query !== 'function')) {
    throw new Error('chat, catalog, and order clients are required');
  }
  try {
    for (const name of names) await clients[name].query(READ_ONLY_BEGIN);
    const runRows = (await clients.chat.query(SOURCE_QUERIES.run, [spec.store_id, runId])).rows;
    const partitionRows = (
      await clients.chat.query(SOURCE_QUERIES.partition, [spec.store_id, runId])
    ).rows;
    const itemIds = partitionRows.map((row) => integer(row.raw_item_id, 'partition.raw_item_id', 1));
    const catalogRows = (await clients.catalog.query(SOURCE_QUERIES.catalog, [itemIds])).rows;
    const eventRows = (
      await clients.chat.query(SOURCE_QUERIES.events, [spec.store_id, runId])
    ).rows;
    const basketRows = (
      await clients.order.query(SOURCE_QUERIES.baskets, [
        spec.store_id,
        runId,
        spec.cutoffs.train_start,
        spec.cutoffs.train_end
      ])
    ).rows;
    checkRows({
      spec,
      specHash,
      runId,
      runRows,
      partitionRows,
      catalogRows,
      eventRows,
      basketRows
    });
    const rows = prepareRows({ spec, partitionRows, catalogRows, eventRows, basketRows });
    fs.mkdirSync(staging, { recursive: false });
    writeJson(path.join(staging, 'benchmark_spec.json'), normalized);
    writeJsonl(path.join(staging, 'users.jsonl'), rows.users);
    writeJsonl(path.join(staging, 'items.jsonl'), rows.items);
    writeJsonl(path.join(staging, 'events.jsonl'), rows.events);
    writeJsonl(path.join(staging, 'baskets.jsonl'), rows.baskets);
    const dataFiles = [
      'benchmark_spec.json', 'users.jsonl', 'items.jsonl', 'events.jsonl', 'baskets.jsonl'
    ];
    const fileSha256 = Object.fromEntries(
      dataFiles.map((name) => [name, sha256File(path.join(staging, name))])
    );
    const bundleBinding = sha256(canonicalJson(fileSha256));
    const sourceManifest = {
      schema_version: 'v5-source-bundle/1.1',
      source_bundle_id: `${runId}-source-${bundleBinding.slice(0, 12)}`,
      source_kind: 'seed-product-postgres-export',
      source_commit: sourceCommit,
      benchmark_run_id: runId,
      generator_source_tree_sha256: generatorTreeHash(
        generatorPaths,
        options.repoRoot ? path.resolve(options.repoRoot) : process.cwd()
      ),
      generator_spec_source_sha256: sha256File(path.resolve(specPath)),
      export_query_contract_sha256: sha256(canonicalJson(SOURCE_QUERIES)),
      catalog_audit_sha256: declaredCatalogAuditSha256,
      catalog_audit_evidence_sha256: audit.evidence_sha256,
      file_sha256: fileSha256,
      expected_counts: {
        users: spec.num_users,
        items: spec.num_products,
        events: spec.num_events,
        baskets: spec.num_orders,
        cold_items: spec.num_cold_products,
        train_events: spec.split_counts.train,
        val_events: spec.split_counts.val,
        test_events: spec.split_counts.test
      },
      catalog_provenance_status: audit.catalog_provenance_status,
      catalog_license_status: audit.catalog_license_status,
      catalog_language_status: audit.catalog_language_status,
      behavior_nature: 'CONTROLLED_GENERATED_BEHAVIOR',
      observed_behavior: false
    };
    writeJson(path.join(staging, 'source_manifest.json'), sourceManifest);
    for (const name of names) await clients[name].query('COMMIT');
    fs.renameSync(staging, target);
    return {
      status: 'PASS_SOURCE_BUNDLE_EXPORTED',
      source_bundle_id: sourceManifest.source_bundle_id,
      source_bundle_manifest_sha256: sha256(canonicalJson(sourceManifest)),
      output_root: target
    };
  } catch (error) {
    await rollbackAll(clients);
    if (fs.existsSync(staging)) fs.rmSync(staging, { recursive: true, force: true });
    throw error;
  }
}

function argumentValue(argv, name) {
  const index = argv.indexOf(name);
  return index >= 0 ? argv[index + 1] : undefined;
}

function databaseConfig(connectionString, caPath) {
  if (!connectionString) throw new Error('required database URL is missing');
  const parsed = new URL(connectionString);
  const local = ['localhost', '127.0.0.1', '::1'].includes(parsed.hostname);
  if (local) return { connectionString, ssl: false };
  if (!caPath) throw new Error('a CA path is required for remote PostgreSQL TLS');
  return {
    connectionString,
    ssl: { ca: fs.readFileSync(path.resolve(caPath), 'utf8'), rejectUnauthorized: true }
  };
}

async function main(argv = process.argv.slice(2)) {
  const repoRoot = path.resolve(__dirname, '..', '..');
  const backendRoot = path.join(repoRoot, 'backend');
  const workspaceRequire = createRequire(path.join(backendRoot, 'package.json'));
  workspaceRequire('dotenv').config({ path: path.join(backendRoot, '.env') });
  const { Client } = workspaceRequire('pg');
  const specPath = path.resolve(nonempty(argumentValue(argv, '--spec'), '--spec'));
  const auditPath = path.resolve(nonempty(argumentValue(argv, '--catalog-audit'), '--catalog-audit'));
  const outputRoot = path.resolve(nonempty(argumentValue(argv, '--output-root'), '--output-root'));
  const runId = nonempty(argumentValue(argv, '--run-id'), '--run-id');
  const sourceCommit = nonempty(argumentValue(argv, '--source-commit'), '--source-commit');
  const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));
  const auditPayload = fs.readFileSync(auditPath, 'utf8');
  const audit = JSON.parse(auditPayload);
  if (auditPayload !== `${canonicalJson(audit)}\n`) {
    throw new Error('catalog audit must be canonical JSON with one trailing LF');
  }
  const declaredCatalogAuditSha256 = sha256(Buffer.from(auditPayload));
  assertCatalogAudit(audit, false);
  const caPath = process.env.SUPABASE_DB_CA_PATH || process.env.DB_SSL_CA_PATH;
  const clients = {
    chat: new Client(databaseConfig(process.env.CHATBOT_DATABASE_URL, caPath)),
    catalog: new Client(databaseConfig(process.env.CATALOG_DATABASE_URL, caPath)),
    order: new Client(databaseConfig(process.env.ORDER_DATABASE_URL, caPath))
  };
  const generatorRoot = path.join(backendRoot, 'docs', 'chatbot', 'seed-product');
  const expectedSpecPath = path.join(generatorRoot, 'benchmark-spec-v5.json');
  if (specPath.toLowerCase() !== expectedSpecPath.toLowerCase()) {
    throw new Error('spec path must be the repository benchmark-spec-v5.json');
  }
  const generatorPaths = [
    specPath,
    path.join(generatorRoot, 'benchmark-spec.js'),
    path.join(generatorRoot, 'benchmark-lib.js'),
    path.join(generatorRoot, 'benchmark-affinity.js'),
    path.join(generatorRoot, 'seed-ml-events.js'),
    path.join(generatorRoot, 'seed-ml-benchmark.js'),
    path.join(generatorRoot, 'mock-interactions.js'),
    path.join(generatorRoot, 'mock-orders.js'),
    path.join(generatorRoot, 'populate-copurchase.js')
  ];
  assertGeneratorCommitBinding({ generatorPaths, repoRoot, sourceCommit });
  const connected = [];
  try {
    for (const client of Object.values(clients)) {
      await client.connect();
      connected.push(client);
    }
    const result = await exportSourceBundle({
      clients,
      runId,
      spec,
      specPath,
      audit,
      catalogAuditSha256: declaredCatalogAuditSha256,
      sourceCommit,
      generatorPaths,
      outputRoot,
      repoRoot
    });
    process.stdout.write(`${canonicalJson(result)}\n`);
  } finally {
    await Promise.allSettled(connected.map((client) => client.end()));
  }
}

if (require.main === module) {
  main().catch((error) => {
    process.stderr.write(`${error.stack || error.message}\n`);
    process.exitCode = 1;
  });
}

module.exports = {
  READ_ONLY_BEGIN,
  SOURCE_QUERIES,
  assertCatalogAudit,
  assertGeneratorCommitBinding,
  catalogAuditSha256,
  canonicalJson,
  exportSourceBundle,
  generatorTreeHash,
  main,
  normalizedSpec
};
