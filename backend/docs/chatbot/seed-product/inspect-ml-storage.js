'use strict';

const { connectDatabases } = require('./benchmark-lib');

async function main() {
  const clients = await connectDatabases();
  try {
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
    console.log(JSON.stringify({
      state: state.rows[0],
      relations: relations.rows,
      indexes: indexes.rows,
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
