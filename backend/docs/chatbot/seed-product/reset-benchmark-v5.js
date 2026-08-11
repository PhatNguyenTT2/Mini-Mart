'use strict';

const path = require('path');
const { connectDatabases } = require('./benchmark-lib');
const { loadBenchmarkSpec } = require('./benchmark-spec');

const RESET_TOKEN = (spec) => `RESET_STORE_${spec.store_id}_BENCHMARK_V5`;

async function count(client, sql, params) {
  const result = await client.query(sql, params);
  return Number(result.rows?.[0]?.count || 0);
}

async function identity(client) {
  const result = await client.query(
    'SELECT current_database() AS database, COALESCE(inet_server_addr()::text, \'local\') AS host, inet_server_port() AS port'
  );
  return result.rows?.[0] || {};
}

async function assertDatabaseIdentities(clients) {
  const names = ['auth', 'catalog', 'chat', 'order'];
  if (!names.every((name) => clients?.[name])) {
    throw new Error('auth, catalog, chat and order clients are required');
  }
  const identities = await Promise.all(names.map((name) => identity(clients[name])));
  const keys = identities.map((value) => `${value.host}:${value.port}/${value.database}`);
  if (new Set(keys).size !== keys.length) throw new Error('database identities must be distinct');
  return Object.fromEntries(names.map((name, index) => [name, identities[index]]));
}

async function planBenchmarkReset({ clients, spec }) {
  if (!clients?.chat || !clients?.order) throw new Error('chat and order clients are required');
  const storeId = Number(spec.store_id);
  if (storeId !== 1) throw new Error('benchmark reset is locked to store 1');
  const tables = [
    'item_similarity',
    'user_product_interaction',
    'co_purchase_stats',
    'product_order_frequency',
    'ml_interaction_event_v1',
    'ml_benchmark_item_partition_v1',
    'ml_benchmark_run_v1'
  ];
  const counts = {};
  for (const table of tables) {
    counts[table] = await count(
      clients.chat,
      `SELECT count(*)::int AS count FROM ${table} WHERE store_id=$1`,
      [storeId]
    );
  }
  counts.sale_order = await count(
    clients.order,
    'SELECT count(*)::int AS count FROM sale_order WHERE store_id=$1 AND benchmark_run_id IS NOT NULL',
    [storeId]
  );
  return {
    storeId,
    tables: counts,
    totalRows: Object.values(counts).reduce((sum, value) => sum + value, 0),
    confirmation: RESET_TOKEN(spec)
  };
}

async function deleteInTransaction(client, statements, storeId) {
  await client.query('BEGIN');
  try {
    await client.query('SET TRANSACTION READ WRITE');
    for (const [table, sql] of statements) await client.query(sql, [storeId]);
    await client.query('COMMIT');
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  }
}

async function executeBenchmarkReset({ clients, spec, confirmation }) {
  const expected = RESET_TOKEN(spec);
  if (confirmation !== expected) throw new Error('exact reset confirmation token is required');
  if (clients.auth && clients.catalog) await assertDatabaseIdentities(clients);
  const plan = await planBenchmarkReset({ clients, spec });
  await deleteInTransaction(clients.chat, [
    ['item_similarity', 'DELETE FROM item_similarity WHERE store_id=$1'],
    ['user_product_interaction', 'DELETE FROM user_product_interaction WHERE store_id=$1'],
    ['co_purchase_stats', 'DELETE FROM co_purchase_stats WHERE store_id=$1'],
    ['product_order_frequency', 'DELETE FROM product_order_frequency WHERE store_id=$1'],
    ['ml_interaction_event_v1', 'DELETE FROM ml_interaction_event_v1 WHERE store_id=$1'],
    ['ml_benchmark_item_partition_v1', 'DELETE FROM ml_benchmark_item_partition_v1 WHERE store_id=$1'],
    ['ml_benchmark_run_v1', 'DELETE FROM ml_benchmark_run_v1 WHERE store_id=$1']
  ], plan.storeId);
  await deleteInTransaction(clients.order, [
    ['sale_order', 'DELETE FROM sale_order WHERE store_id=$1 AND benchmark_run_id IS NOT NULL']
  ], plan.storeId);
  const post = await planBenchmarkReset({ clients, spec });
  if (post.totalRows !== 0) throw new Error(`benchmark reset postcondition failed: ${post.totalRows}`);
  return { status: 'reset', storeId: plan.storeId, planned: plan.tables, deleted: plan.tables };
}

async function main() {
  const specPath = process.argv[process.argv.indexOf('--spec') + 1];
  if (!specPath) throw new Error('usage: reset-benchmark-v5.js --spec <path> --preflight|--execute --confirm <token>');
  const spec = loadBenchmarkSpec(path.resolve(specPath));
  const preflight = process.argv.includes('--preflight');
  const execute = process.argv.includes('--execute');
  if (preflight === execute) throw new Error('choose exactly one of --preflight or --execute');
  if (preflight) {
    const clients = await connectDatabases();
    try {
      await assertDatabaseIdentities(clients);
      console.log(JSON.stringify({ status: 'preflight', ...(await planBenchmarkReset({ clients, spec })) }));
    } finally {
      await Promise.all(Object.values(clients).map((client) => client.end()));
    }
    return;
  }
  const confirmation = process.argv[process.argv.indexOf('--confirm') + 1];
  if (!confirmation) throw new Error('exact reset confirmation token is required');
  const clients = await connectDatabases();
  try {
    console.log(JSON.stringify(await executeBenchmarkReset({ clients, spec, confirmation })));
  } finally {
    await Promise.all(Object.values(clients).map((client) => client.end()));
  }
}

if (require.main === module) main().catch((error) => { console.error(error.message); process.exitCode = 1; });

module.exports = { assertDatabaseIdentities, executeBenchmarkReset, planBenchmarkReset };
