'use strict';

async function populateCopurchase({ chatClient, orderClient, spec, runId }) {
  const source = await orderClient.query(
    `SELECT o.id AS order_id,d.product_id
     FROM sale_order o JOIN sale_order_detail d ON d.order_id=o.id
     WHERE o.store_id=$1 AND o.status='delivered' AND o.payment_status='paid'
       AND o.order_date <= $2 AND o.benchmark_run_id=$3
     ORDER BY o.id,d.product_id`,
    [spec.store_id, spec.cutoffs.train_end, runId]
  );
  const baskets = new Map();
  for (const row of source.rows) {
    const orderId = Number(row.order_id);
    if (!baskets.has(orderId)) baskets.set(orderId, new Set());
    baskets.get(orderId).add(Number(row.product_id));
  }
  const itemCounts = new Map();
  const pairCounts = new Map();
  for (const basket of baskets.values()) {
    const items = [...basket].sort((left, right) => left - right);
    for (const item of items) itemCounts.set(item, (itemCounts.get(item) || 0) + 1);
    for (let left = 0; left < items.length; left += 1) {
      for (let right = left + 1; right < items.length; right += 1) {
        const key = `${items[left]}:${items[right]}`;
        pairCounts.set(key, (pairCounts.get(key) || 0) + 1);
      }
    }
  }
  const totalOrders = baskets.size;
  const rules = [];
  for (const [key, count] of pairCounts) {
    if (count < 3) continue;
    const [left, right] = key.split(':').map(Number);
    const leftCount = itemCounts.get(left);
    const rightCount = itemCounts.get(right);
    rules.push({
      left,
      right,
      count,
      support: count / totalOrders,
      confidenceAB: count / leftCount,
      confidenceBA: count / rightCount,
      lift: count * totalOrders / (leftCount * rightCount)
    });
  }
  await chatClient.query('BEGIN');
  try {
    await chatClient.query('SET TRANSACTION READ WRITE');
    await chatClient.query("SET LOCAL statement_timeout='5min'");
    await chatClient.query('DELETE FROM co_purchase_stats WHERE store_id=$1', [spec.store_id]);
    await chatClient.query('DELETE FROM product_order_frequency WHERE store_id=$1', [spec.store_id]);
    const frequencies = [...itemCounts.entries()];
    for (let offset = 0; offset < frequencies.length; offset += 5000) {
      const batch = frequencies.slice(offset, offset + 5000);
      await chatClient.query(
        `INSERT INTO product_order_frequency(product_id,store_id,order_count,last_computed_at)
         SELECT product_id,$1,order_count,NOW()
         FROM unnest($2::bigint[],$3::int[]) AS input(product_id,order_count)`,
        [spec.store_id, batch.map(([id]) => id), batch.map(([, count]) => count)]
      );
    }
    for (let offset = 0; offset < rules.length; offset += 3000) {
      const batch = rules.slice(offset, offset + 3000);
      await chatClient.query(
        `INSERT INTO co_purchase_stats
          (product_id_a,product_id_b,store_id,co_purchase_count,last_updated_at,
           support,confidence_ab,confidence_ba,lift,total_orders)
         SELECT product_a,product_b,$1,pair_count,NOW(),support,confidence_ab,confidence_ba,lift,$2
         FROM unnest($3::bigint[],$4::bigint[],$5::int[],$6::numeric[],$7::numeric[],
                     $8::numeric[],$9::numeric[])
           AS input(product_a,product_b,pair_count,support,confidence_ab,confidence_ba,lift)`,
        [
          spec.store_id, totalOrders, batch.map((rule) => rule.left), batch.map((rule) => rule.right),
          batch.map((rule) => rule.count), batch.map((rule) => rule.support),
          batch.map((rule) => rule.confidenceAB), batch.map((rule) => rule.confidenceBA),
          batch.map((rule) => rule.lift)
        ]
      );
    }
    await chatClient.query('COMMIT');
  } catch (error) {
    await chatClient.query('ROLLBACK');
    throw error;
  }
  return { totalOrders, directedRuleCount: rules.length * 2, storedPairCount: rules.length };
}

module.exports = { populateCopurchase };
