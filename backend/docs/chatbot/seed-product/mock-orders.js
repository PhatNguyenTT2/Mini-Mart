'use strict';

const { mulberry32 } = require('./benchmark-lib');

function pick(values, random) {
  return values[Math.floor(random() * values.length)];
}

async function reserveIds(client, count) {
  const result = await client.query(
    `SELECT nextval(pg_get_serial_sequence('sale_order','id'))::bigint AS id
     FROM generate_series(1,$1)`,
    [count]
  );
  return result.rows.map((row) => Number(row.id));
}

async function insertOrders(client, orders) {
  await client.query(
    `INSERT INTO sale_order
      (id,store_id,customer_id,created_by,order_date,delivery_type,total_amount,payment_status,status,payment_method,benchmark_run_id)
     OVERRIDING SYSTEM VALUE
     SELECT id,store_id,customer_id,NULL,order_date,'pickup',total_amount,'paid','delivered','cash',benchmark_run_id
     FROM unnest($1::bigint[],$2::bigint[],$3::bigint[],$4::timestamptz[],$5::numeric[],$6::text[])
       AS input(id,store_id,customer_id,order_date,total_amount,benchmark_run_id)`,
    [
      orders.map((order) => order.id), orders.map((order) => order.storeId),
      orders.map((order) => order.userId), orders.map((order) => order.orderDate),
      orders.map((order) => order.totalAmount), orders.map((order) => order.runId)
    ]
  );
  const details = orders.flatMap((order) => order.items.map((item) => ({ orderId: order.id, ...item })));
  await client.query(
    `INSERT INTO sale_order_detail
      (order_id,product_id,product_name,batch_id,quantity,unit_price,total_price)
     SELECT order_id,product_id,product_name,batch_id,quantity,unit_price,total_price
     FROM unnest($1::bigint[],$2::bigint[],$3::text[],$4::bigint[],$5::int[],$6::numeric[],$7::numeric[])
       AS input(order_id,product_id,product_name,batch_id,quantity,unit_price,total_price)`,
    [
      details.map((detail) => detail.orderId), details.map((detail) => detail.productId),
      details.map((detail) => detail.productName), details.map((detail) => detail.productId),
      details.map((detail) => detail.quantity), details.map((detail) => detail.unitPrice),
      details.map((detail) => detail.totalPrice)
    ]
  );
}

async function seedOrders({ client, spec, runId, products, coldProducts }) {
  const random = mulberry32(spec.seed + 1000);
  const cold = new Set(coldProducts);
  const productMap = new Map(products.map((product) => [Number(product.product_id), product]));
  const warm = products.map((product) => Number(product.product_id)).filter((id) => !cold.has(id));
  for (const trap of spec.semantic_traps) {
    for (const id of [trap.anchor, ...trap.targets]) {
      if (!productMap.has(id) || cold.has(id)) throw new Error(`invalid semantic trap product ${id}`);
    }
  }
  await client.query('BEGIN');
  try {
    await client.query('SET TRANSACTION READ WRITE');
    await client.query("SET LOCAL statement_timeout='5min'");
    await client.query('ALTER TABLE sale_order ADD COLUMN IF NOT EXISTS benchmark_run_id TEXT');
    await client.query(`CREATE INDEX IF NOT EXISTS idx_sale_order_benchmark_run
      ON sale_order(store_id,benchmark_run_id,order_date)
      WHERE benchmark_run_id IS NOT NULL`);
    // One-time migration from the pre-lineage fixture.  Never use created_by as
    // provenance for new rows; only remove the old block when its entire
    // store-scoped signature is exactly the known 15,000-row benchmark.
    const legacy = await client.query(
      `SELECT count(*)::int AS total,
              count(*) FILTER (
                WHERE status='delivered' AND payment_status='paid'
              )::int AS eligible
       FROM sale_order
       WHERE store_id=$1 AND benchmark_run_id IS NULL AND created_by=1`,
      [spec.store_id]
    );
    const legacyCount = legacy.rows[0].total;
    if (legacyCount !== 0) {
      if (legacyCount !== spec.num_orders || legacy.rows[0].eligible !== legacyCount) {
        throw new Error(
          `refusing ambiguous legacy order cleanup: ${JSON.stringify(legacy.rows[0])}`
        );
      }
      await client.query(
        `DELETE FROM sale_order
         WHERE store_id=$1 AND benchmark_run_id IS NULL AND created_by=1`,
        [spec.store_id]
      );
    }
    await client.query(
      'DELETE FROM sale_order WHERE store_id=$1 AND benchmark_run_id IS NOT NULL',
      [spec.store_id]
    );
    const ids = await reserveIds(client, spec.num_orders);
    for (let offset = 0; offset < spec.num_orders; offset += 500) {
      const batch = [];
      for (let index = offset; index < Math.min(offset + 500, spec.num_orders); index += 1) {
        const selected = new Set();
        if (random() < 0.45) {
          const trap = pick(spec.semantic_traps, random);
          selected.add(trap.anchor);
          selected.add(pick(trap.targets, random));
        }
        const size = 2 + Math.floor(random() * 4);
        while (selected.size < size) selected.add(pick(warm, random));
        const items = [...selected].map((productId) => {
          const product = productMap.get(productId);
          const quantity = 1 + Math.floor(random() * 3);
          const unitPrice = Number(product.unit_price);
          return {
            productId,
            productName: product.name,
            quantity,
            unitPrice,
            totalPrice: Number((quantity * unitPrice).toFixed(2))
          };
        });
        const start = Date.parse(spec.cutoffs.train_start);
        const end = Date.parse(spec.cutoffs.train_end);
        batch.push({
          id: ids[index],
          storeId: spec.store_id,
          runId,
          userId: 1 + Math.floor(random() * spec.num_users),
          orderDate: new Date(Math.floor(start + random() * (end - start))).toISOString(),
          totalAmount: items.reduce((sum, item) => sum + item.totalPrice, 0).toFixed(2),
          items
        });
      }
      await insertOrders(client, batch);
    }
    const check = await client.query(
      `SELECT count(*)::int AS count FROM sale_order
       WHERE store_id=$1 AND benchmark_run_id=$2
         AND status='delivered' AND payment_status='paid'`,
      [spec.store_id, runId]
    );
    if (check.rows[0].count !== spec.num_orders) {
      throw new Error(`order count mismatch: ${check.rows[0].count}`);
    }
    await client.query('COMMIT');
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  }
}

module.exports = { seedOrders };
