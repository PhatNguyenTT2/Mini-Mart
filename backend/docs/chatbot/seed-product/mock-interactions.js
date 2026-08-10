'use strict';

async function rebuildInteractions({ client, storeId, runId }) {
  await client.query('BEGIN');
  try {
    await client.query('SET TRANSACTION READ WRITE');
    await client.query("SET LOCAL statement_timeout='20min'");
    await client.query("SET LOCAL work_mem='256MB'");
    await client.query('DELETE FROM user_product_interaction WHERE store_id=$1', [storeId]);
    await client.query('DROP INDEX IF EXISTS idx_interaction_user');
    await client.query('DROP INDEX IF EXISTS idx_interaction_product');
    await client.query(`
      INSERT INTO user_product_interaction
        (user_id,product_id,store_id,purchase_count,total_quantity,last_purchased_at,interaction_score)
      SELECT e.user_id,e.product_id,e.store_id,
             count(*) FILTER (WHERE e.event_type='purchase')::int,
             count(*) FILTER (WHERE e.event_type='purchase')::int,
             max(e.event_ts) FILTER (WHERE e.event_type='purchase'),
             0.5 * count(*) FILTER (WHERE e.event_type='view') +
             3.0 * count(*) FILTER (WHERE e.event_type='purchase')
      FROM ml_interaction_event_v1 e
      WHERE e.store_id=$1 AND e.benchmark_run_id=$2
        AND e.event_origin<>'cold_start'
      GROUP BY e.user_id,e.product_id,e.store_id
    `, [storeId, runId]);
    await client.query(`
      CREATE INDEX idx_interaction_user
        ON user_product_interaction(user_id,store_id);
      CREATE INDEX idx_interaction_product
        ON user_product_interaction(product_id,store_id);
    `);
    await client.query('COMMIT');
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  }
}

module.exports = { rebuildInteractions };
