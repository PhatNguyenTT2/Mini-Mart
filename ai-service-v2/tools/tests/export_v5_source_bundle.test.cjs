'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const {
  SOURCE_QUERIES,
  assertGeneratorCommitBinding,
  canonicalJson,
  catalogAuditSha256,
  exportSourceBundle
} = require('../export_v5_source_bundle.cjs');

class FakeClient {
  constructor(rows) {
    this.rows = rows;
    this.calls = [];
  }

  async query(sql) {
    this.calls.push(sql);
    if (sql.startsWith('BEGIN') || sql === 'COMMIT' || sql === 'ROLLBACK') {
      return { rows: [], rowCount: 0 };
    }
    const marker = Object.entries(SOURCE_QUERIES).find(([, query]) => query === sql)?.[0];
    if (!marker) throw new Error(`unexpected query: ${sql}`);
    const rows = this.rows[marker] || [];
    return { rows, rowCount: rows.length };
  }
}

function fixture(root) {
  const spec = {
    schema_version: '3.0.0',
    generator_version: '5.0.0',
    seed: 42,
    store_id: 1,
    num_users: 2,
    num_products: 2,
    num_cold_products: 1,
    num_events: 3,
    split_counts: { train: 1, val: 1, test: 1 },
    cutoffs: {
      train_start: '2026-01-01T00:00:00.000Z',
      train_end: '2026-01-31T23:59:59.000Z',
      val_start: '2026-02-01T00:00:00.000Z',
      val_end: '2026-02-28T23:59:59.000Z',
      test_start: '2026-03-01T00:00:00.000Z',
      test_end: '2026-03-31T23:59:59.000Z'
    },
    num_orders: 1
  };
  const specPath = path.join(root, 'benchmark-spec-v5.json');
  const generatorPath = path.join(root, 'generator.js');
  fs.writeFileSync(specPath, `${JSON.stringify(spec)}\n`);
  fs.writeFileSync(generatorPath, "'use strict';\n");
  const audit = {
    schema_version: 'catalog-audit/1.1',
    catalog_provenance_status: 'TEST_ONLY',
    catalog_license_status: 'TEST_ONLY',
    catalog_language_status: 'TEST_ONLY',
    export_authorized: true,
    redistribution_authorized: false,
    approved_fields: ['category', 'name', 'price', 'vendor'],
    evidence_sha256: ['a'.repeat(64)]
  };
  const catalogRows = [
    { raw_item_id: '10', category_id: '1', name: 'item a', category: 'cat', vendor: 'v', price: '1.0' },
    { raw_item_id: '20', category_id: '1', name: 'item b', category: 'cat', vendor: 'v', price: '2.0' }
  ];
  const crypto = require('node:crypto');
  const catalogPayload = catalogRows
    .map((row) => `${Number(row.raw_item_id)}\t${Number(row.category_id)}\t${row.name}`)
    .join('\n');
  const catalogHash = crypto.createHash('sha256').update(catalogPayload).digest('hex');
  const canonicalize = (value) => {
    if (Array.isArray(value)) return value.map(canonicalize);
    if (value && typeof value === 'object') {
      return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonicalize(value[key])]));
    }
    return value;
  };
  const specHash = crypto.createHash('sha256')
    .update(JSON.stringify(canonicalize(spec))).digest('hex');
  const runId = `benchmark-v5-s42-${catalogHash.slice(0, 10)}-${specHash.slice(0, 10)}`;
  const clients = {
    chat: new FakeClient({
      run: [{
        benchmark_run_id: runId, store_id: '1', seed: 42,
        status: 'ready', catalog_sha256: catalogHash,
        benchmark_spec_sha256: specHash, expected_event_count: 3,
        split_boundaries: spec.cutoffs,
        published_at: new Date('2026-04-01T00:00:00.000Z')
      }],
      partition: [
        { raw_item_id: '10', partition: 'warm', seed: 42, catalog_sha256: catalogHash, benchmark_spec_sha256: specHash },
        { raw_item_id: '20', partition: 'cold', seed: 42, catalog_sha256: catalogHash, benchmark_spec_sha256: specHash }
      ],
      events: [
        { raw_event_id: 'e-1', raw_user_id: '1', raw_item_id: '10', event_type: 'purchase', event_ts: new Date('2026-01-02T00:00:00Z'), event_origin: 'organic', session_id: 's-1', cohort_id: null, persona_cluster: 0, interaction_weight: 1 },
        { raw_event_id: 'e-2', raw_user_id: '1', raw_item_id: '20', event_type: 'purchase', event_ts: new Date('2026-02-02T00:00:00Z'), event_origin: 'organic', session_id: 's-2', cohort_id: null, persona_cluster: 0, interaction_weight: 1 },
        { raw_event_id: 'e-3', raw_user_id: '2', raw_item_id: '20', event_type: 'purchase', event_ts: new Date('2026-03-02T00:00:00Z'), event_origin: 'cold_start', session_id: 's-3', cohort_id: 'cold-20', persona_cluster: 1, interaction_weight: 1 }
      ]
    }),
    catalog: new FakeClient({ catalog: catalogRows }),
    order: new FakeClient({
      baskets: [{ raw_basket_id: '100', raw_user_id: '1', basket_ts: new Date('2026-01-03T00:00:00Z'), basket_origin: 'organic', raw_item_ids: ['10', '20'] }]
    })
  };
  return {
    audit,
    clients,
    generatorPaths: [specPath, generatorPath],
    repoRoot: root,
    runId,
    spec,
    specPath
  };
}

test('exporter uses read-only SQL and writes one strict source bundle', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ais-r2-export-test-'));
  try {
    const input = fixture(root);
    const outputRoot = path.join(root, 'source-bundle');
    const result = await exportSourceBundle({
      ...input,
      outputRoot,
      runId: input.runId,
      sourceCommit: '0'.repeat(40),
      catalogAuditSha256: catalogAuditSha256(input.audit)
    });

    assert.equal(result.status, 'PASS_SOURCE_BUNDLE_EXPORTED');
    assert.deepEqual(fs.readdirSync(outputRoot).sort(), [
      'baskets.jsonl', 'benchmark_spec.json', 'events.jsonl',
      'items.jsonl', 'source_manifest.json', 'users.jsonl'
    ]);
    const manifest = JSON.parse(fs.readFileSync(path.join(outputRoot, 'source_manifest.json')));
    assert.equal(manifest.expected_counts.events, 3);
    assert.equal(manifest.expected_counts.baskets, 1);
    assert.equal(manifest.observed_behavior, false);
    assert.equal(manifest.catalog_audit_sha256, catalogAuditSha256(input.audit));
    for (const client of Object.values(input.clients)) {
      assert.equal(client.calls[0], 'BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY');
      assert.equal(client.calls.at(-1), 'COMMIT');
    }
    for (const query of Object.values(SOURCE_QUERIES)) {
      assert.doesNotMatch(query, /\b(?:INSERT|UPDATE|DELETE|ALTER|CREATE|DROP|TRUNCATE)\b/i);
    }
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('exporter rejects pending catalog rights before opening a transaction', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ais-r2-export-audit-test-'));
  try {
    const input = fixture(root);
    input.audit.catalog_license_status = 'PENDING';
    await assert.rejects(
      exportSourceBundle({
        ...input,
        outputRoot: path.join(root, 'blocked'),
        runId: input.runId,
        sourceCommit: '0'.repeat(40),
        catalogAuditSha256: catalogAuditSha256(input.audit)
      }),
      /catalog audit is not admitted/
    );
    assert.equal(Object.values(input.clients).every((client) => client.calls.length === 0), true);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('exporter permits post-export language audit only after access rights pass', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ais-r2-export-language-test-'));
  try {
    const input = fixture(root);
    input.audit = {
      ...input.audit,
      catalog_provenance_status: 'VERIFIED',
      catalog_license_status: 'APPROVED_PRIVATE_RESEARCH',
      catalog_language_status: 'PENDING_POST_EXPORT_AUDIT'
    };
    const result = await exportSourceBundle({
      ...input,
      outputRoot: path.join(root, 'source-bundle'),
      runId: input.runId,
      sourceCommit: '1'.repeat(40),
      catalogAuditSha256: catalogAuditSha256(input.audit)
    });
    assert.equal(result.status, 'PASS_SOURCE_BUNDLE_EXPORTED');
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('catalog audit hash and misleading status prefixes fail closed', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ais-r2-export-hash-test-'));
  try {
    const input = fixture(root);
    await assert.rejects(
      exportSourceBundle({
        ...input,
        outputRoot: path.join(root, 'bad-hash'),
        runId: input.runId,
        sourceCommit: '0'.repeat(40),
        catalogAuditSha256: 'b'.repeat(64)
      }),
      /does not match canonical catalog audit bytes/
    );
    input.audit.catalog_provenance_status = 'VERIFIED_BUT_PENDING';
    await assert.rejects(
      exportSourceBundle({
        ...input,
        outputRoot: path.join(root, 'bad-status'),
        runId: input.runId,
        sourceCommit: '1'.repeat(40),
        catalogAuditSha256: catalogAuditSha256(input.audit)
      }),
      /catalog provenance is not verified/
    );
    assert.equal(Object.values(input.clients).every((client) => client.calls.length === 0), true);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('generator files must match the declared Git commit bytes', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ais-r2-generator-binding-test-'));
  try {
    const generator = path.join(root, 'generator.js');
    fs.writeFileSync(generator, "'use strict';\n");
    const bytes = fs.readFileSync(generator);
    assert.doesNotThrow(() => assertGeneratorCommitBinding({
      generatorPaths: [generator],
      repoRoot: root,
      sourceCommit: '1'.repeat(40),
      readCommittedFile: () => bytes
    }));
    assert.throws(() => assertGeneratorCommitBinding({
      generatorPaths: [generator],
      repoRoot: root,
      sourceCommit: '1'.repeat(40),
      readCommittedFile: () => Buffer.from('different')
    }), /generator source differs/);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});
