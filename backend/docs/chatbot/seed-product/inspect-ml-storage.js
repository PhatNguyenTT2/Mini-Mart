'use strict';

const path = require('path');

const { connectDatabases } = require('./benchmark-lib');

function argumentValue(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : undefined;
}

async function main() {
  const clients = await connectDatabases();
  try {
    if (process.argv.includes('--semantic-readiness')) {
      const requestedSpec = argumentValue('--spec');
      const runId = argumentValue('--run-id');
      if (!requestedSpec || !runId) {
        throw new Error('--semantic-readiness requires --spec and --run-id');
      }
      const specPath = path.isAbsolute(requestedSpec)
        ? requestedSpec
        : path.resolve(process.cwd(), requestedSpec);
      const spec = require(specPath);
      const results = [];
      for (const trap of spec.semantic_traps) {
        const baskets = await clients.order.query(
          `SELECT count(DISTINCT o.id)::int AS baskets
           FROM sale_order o
           WHERE o.store_id=$1 AND o.benchmark_run_id=$2 AND o.order_date <= $3
             AND EXISTS (
               SELECT 1 FROM sale_order_detail d
               WHERE d.order_id=o.id AND d.product_id=$4
             )
             AND EXISTS (
               SELECT 1 FROM sale_order_detail d
               WHERE d.order_id=o.id AND d.product_id=ANY($5::bigint[])
             )`,
          [spec.store_id, runId, spec.cutoffs.train_end, trap.anchor, trap.targets]
        );
        const rules = await clients.chat.query(
          `SELECT max(co_purchase_count)::int AS co_purchase_count,max(lift)::float8 AS lift
           FROM co_purchase_stats
           WHERE store_id=$1
             AND ((product_id_a=$2 AND product_id_b=ANY($3::bigint[]))
               OR (product_id_b=$2 AND product_id_a=ANY($3::bigint[])))`,
          [spec.store_id, trap.anchor, trap.targets]
        );
        const evidence = {
          trapId: trap.trap_id,
          baskets: baskets.rows[0].baskets,
          coPurchaseCount: rules.rows[0].co_purchase_count,
          lift: rules.rows[0].lift
        };
        evidence.passed = evidence.coPurchaseCount >= spec.minimum_semantic_copurchase_count
          && evidence.lift >= spec.minimum_semantic_lift;
        results.push(evidence);
      }
      const passed = results.filter((result) => result.passed).length;
      console.log(JSON.stringify({ runId, passed, total: results.length, results }));
      if (passed !== results.length) process.exitCode = 1;
      return;
    }
    const terminateIndex = process.argv.indexOf('--terminate-pid');
    if (terminateIndex >= 0) {
      const pid = Number(process.argv[terminateIndex + 1]);
      if (!Number.isInteger(pid) || pid <= 0) throw new Error('invalid --terminate-pid');
      const target = await clients.chat.query(
        `SELECT pid FROM pg_stat_activity
         WHERE pid=$1 AND application_name='Supavisor'
           AND (
             query LIKE 'WITH purchases AS MATERIALIZED%'
             OR query LIKE 'WITH organic AS MATERIALIZED%'
           )`,
        [pid]
      );
      if (target.rowCount !== 1) throw new Error('refusing to terminate an unverified backend');
      const terminated = await clients.chat.query(
        'SELECT pg_terminate_backend($1) AS terminated', [pid]
      );
      console.log(JSON.stringify(terminated.rows[0]));
      return;
    }
    const state = await clients.chat.query(`
      SELECT current_database() AS database_name,
             current_setting('default_transaction_read_only') AS default_read_only,
             current_setting('transaction_read_only') AS transaction_read_only,
             pg_is_in_recovery() AS in_recovery,
             pg_database_size(current_database())::bigint AS database_bytes
    `);
    const relations = await clients.chat.query(`
      SELECT c.relname,
             pg_relation_size(c.oid)::bigint AS table_bytes,
             pg_indexes_size(c.oid)::bigint AS index_bytes,
             pg_total_relation_size(c.oid)::bigint AS total_bytes
      FROM pg_class c
      JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname=current_schema()
        AND c.relname IN (
          'ml_interaction_event_v1',
          'user_product_interaction',
          'ml_benchmark_run_v1',
          'ml_benchmark_item_partition_v1'
        )
      ORDER BY c.relname
    `);
    const indexes = await clients.chat.query(`
      SELECT indexrelid::regclass::text AS index_name,
             pg_relation_size(indexrelid)::bigint AS bytes
      FROM pg_stat_user_indexes
      WHERE relname IN ('ml_interaction_event_v1','user_product_interaction')
      ORDER BY index_name
    `);
    const activity = await clients.chat.query(`
      SELECT pid,application_name,query_start,state,wait_event_type,wait_event,
             left(query,160) AS query
      FROM pg_stat_activity
      WHERE datname=current_database() AND pid<>pg_backend_pid()
      ORDER BY query_start DESC
      LIMIT 10
    `);
    const runs = await clients.chat.query(`
      SELECT r.benchmark_run_id,r.status,r.catalog_sha256,r.benchmark_spec_sha256,
             (SELECT count(*)::int FROM ml_interaction_event_v1 e
             WHERE e.benchmark_run_id=r.benchmark_run_id) AS events,
             (SELECT count(*)::int FROM user_product_interaction i
              WHERE i.store_id=r.store_id) AS interactions,
             (SELECT count(*)::int FROM ml_benchmark_item_partition_v1 p
              WHERE p.benchmark_run_id=r.benchmark_run_id) AS products
      FROM ml_benchmark_run_v1 r
      ORDER BY r.created_at DESC
      LIMIT 5
    `);
    console.log(JSON.stringify({
      state: state.rows[0],
      relations: relations.rows,
      indexes: indexes.rows,
      runs: runs.rows,
      activity: activity.rows
    }));
  } finally {
    await Promise.all(Object.values(clients).map((client) => client.end()));
  }
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exitCode = 1;
});
