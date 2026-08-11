'use strict';

const { loadBenchmarkSpec } = require('./benchmark-spec');

const RESET_TOKEN = (spec) => `RESET_BENCHMARK_V5_STORE_${spec.store_id}`;

async function count(client, sql, params) {
  const result = await client.query(sql, params);
  return Number(result.rows?.[0]?.count || 0);
}

async function planBenchmarkReset({ clients, spec }) {
  if (!clients?.chat || !clients?.order) throw new Error('chat and order clients are required');
  const storeId = Number(spec.store_id);
  const events = await count(clients.chat, 'SELECT count(*)::int AS count FROM ml_interaction_event_v1 WHERE store_id=$1', [storeId]);
  const partitions = await count(clients.chat, 'SELECT count(*)::int AS count FROM ml_benchmark_item_partition_v1 WHERE store_id=$1', [storeId]);
  const runs = await count(clients.chat, 'SELECT count(*)::int AS count FROM ml_benchmark_run_v1 WHERE store_id=$1', [storeId]);
  const copurchase = await count(clients.chat, 'SELECT count(*)::int AS count FROM co_purchase_stats WHERE store_id=$1', [storeId]);
  const frequency = await count(clients.chat, 'SELECT count(*)::int AS count FROM product_order_frequency WHERE store_id=$1', [storeId]);
  const interactions = await count(clients.chat, 'SELECT count(*)::int AS count FROM user_product_interaction WHERE store_id=$1', [storeId]);
  const orders = await count(clients.order, 'SELECT count(*)::int AS count FROM sale_order WHERE store_id=$1 AND benchmark_run_id IS NOT NULL', [storeId]);
  return {
    storeId,
    tables: { ml_interaction_event_v1: events, ml_benchmark_item_partition_v1: partitions,
      ml_benchmark_run_v1: runs, co_purchase_stats: copurchase,
      product_order_frequency: frequency, user_product_interaction: interactions, sale_order: orders },
    totalRows: events + partitions + runs + copurchase + frequency + interactions + orders,
    confirmation: RESET_TOKEN(spec)
  };
}

async function executeBenchmarkReset({ clients, spec, confirmation }) {
  const expected = RESET_TOKEN(spec);
  if (confirmation !== expected) throw new Error('exact reset confirmation token is required');
  const plan = await planBenchmarkReset({ clients, spec });
  const deleted = {};
  await clients.order.query('BEGIN');
  try {
    await clients.order.query('SET TRANSACTION READ WRITE');
    deleted.sale_order = await count(clients.order,
      'SELECT count(*)::int AS count FROM sale_order WHERE store_id=$1 AND benchmark_run_id IS NOT NULL',
      [plan.storeId]);
    await clients.order.query(
      'DELETE FROM sale_order WHERE store_id=$1 AND benchmark_run_id IS NOT NULL', [plan.storeId]
    );
    await clients.order.query('COMMIT');
  } catch (error) {
    await clients.order.query('ROLLBACK');
    throw error;
  }
  await clients.chat.query('BEGIN');
  try {
    await clients.chat.query('SET TRANSACTION READ WRITE');
    for (const [name, sql] of [
      ['co_purchase_stats', 'DELETE FROM co_purchase_stats WHERE store_id=$1'],
      ['product_order_frequency', 'DELETE FROM product_order_frequency WHERE store_id=$1'],
      ['user_product_interaction', 'DELETE FROM user_product_interaction WHERE store_id=$1'],
      ['ml_interaction_event_v1', 'DELETE FROM ml_interaction_event_v1 WHERE store_id=$1'],
      ['ml_benchmark_item_partition_v1', 'DELETE FROM ml_benchmark_item_partition_v1 WHERE store_id=$1'],
      ['ml_benchmark_run_v1', 'DELETE FROM ml_benchmark_run_v1 WHERE store_id=$1']
    ]) {
      deleted[name] = await count(clients.chat,
        `SELECT count(*)::int AS count FROM ${name} WHERE store_id=$1`, [plan.storeId]);
      await clients.chat.query(sql, [plan.storeId]);
    }
    await clients.chat.query('COMMIT');
  } catch (error) {
    await clients.chat.query('ROLLBACK');
    throw error;
  }
  return { status: 'reset', storeId: plan.storeId, planned: plan.tables, deleted };
}

async function main() {
  const specPath = process.argv[2];
  if (!specPath) throw new Error('usage: node reset-benchmark-v5.js <benchmark-spec-v5.json> --plan');
  const spec = loadBenchmarkSpec(specPath);
  if (spec.generator_version !== '5.0.0') throw new Error('reset requires benchmark generator v5');
  if (!process.argv.includes('--plan')) throw new Error('live reset requires an explicit --plan preflight');
  console.log(JSON.stringify({ status: 'ready', storeId: spec.store_id, confirmation: RESET_TOKEN(spec) }));
}

if (require.main === module) main().catch((error) => { console.error(error.message); process.exitCode = 1; });

module.exports = { executeBenchmarkReset, planBenchmarkReset };
