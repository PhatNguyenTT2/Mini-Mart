'use strict';

function productItems(productIds, productMap, orderIndex) {
  return productIds.map((productId, itemIndex) => {
    const product = productMap.get(productId);
    if (!product) throw new Error(`organic bundle references unknown product ${productId}`);
    const quantity = 1 + ((orderIndex + itemIndex) % 2);
    const unitPrice = Number(product.unit_price);
    return {
      productId,
      productName: product.name,
      quantity,
      unitPrice,
      totalPrice: Number((quantity * unitPrice).toFixed(2))
    };
  });
}

function orderDate(spec, orderIndex) {
  const start = Date.parse(spec.cutoffs.train_start);
  const end = Date.parse(spec.cutoffs.train_end);
  const ratio = spec.num_orders <= 1 ? 0 : orderIndex / (spec.num_orders - 1);
  return new Date(Math.floor(start + (end - start) * ratio)).toISOString();
}

function generateOrderPlan({ spec, users, products, coldProducts, affinityModel }) {
  if (spec.generator_version !== '5.0.0' || spec.schema_version !== '3.0.0') {
    throw new Error('order generator requires benchmark v5');
  }
  const organicCount = Number(spec.organic_order_count);
  const semanticCount = Number(spec.semantic_order_count);
  if (organicCount + semanticCount !== spec.num_orders) {
    throw new Error('organic and semantic order counts must equal num_orders');
  }
  if (
    !Number.isInteger(spec.minimum_semantic_copurchase_count)
    || spec.minimum_semantic_copurchase_count < 3
    || semanticCount < spec.semantic_traps.length * spec.minimum_semantic_copurchase_count
  ) {
    throw new Error('semantic order budget cannot satisfy the per-trap co-purchase threshold');
  }
  if (!affinityModel || !affinityModel.bundleTemplates) {
    throw new Error('v5 order generation requires the shared affinity model and templates');
  }
  const cold = new Set(coldProducts);
  const productMap = new Map(products.map((product) => [Number(product.product_id), product]));
  const fixtureProducts = new Set(spec.semantic_traps.flatMap((trap) => [trap.anchor, ...trap.targets]));
  for (const trapProduct of fixtureProducts) {
    if (!productMap.has(trapProduct) || cold.has(trapProduct)) {
      throw new Error(`invalid semantic trap product ${trapProduct}`);
    }
  }
  const templates = affinityModel.bundleTemplates.templates;
  const expectedTemplates = Number(spec.organic_bundle_template_count);
  const repeatCount = Number(spec.organic_bundle_repeats);
  if (templates.length !== expectedTemplates || templates.some((template) => template.repeatCount !== repeatCount)) {
    throw new Error('organic template count/repeat contract is invalid');
  }
  if (templates.length * repeatCount !== organicCount) {
    throw new Error('organic template repetitions do not cover organic_order_count');
  }
  const personaUsers = new Map();
  users.forEach((userId) => {
    const persona = affinityModel.personaByUser.get(userId);
    if (persona === undefined) throw new Error(`missing persona assignment for user ${userId}`);
    if (!personaUsers.has(persona)) personaUsers.set(persona, []);
    personaUsers.get(persona).push(userId);
  });
  const slotsByPersona = new Map();
  for (const template of templates) {
    slotsByPersona.set(
      template.persona,
      (slotsByPersona.get(template.persona) || 0) + template.repeatCount
    );
  }
  const remainingByUser = new Map();
  for (const [persona, candidates] of personaUsers) {
    const slots = slotsByPersona.get(persona) || 0;
    if (slots < candidates.length * 2 || slots > candidates.length * 3) {
      throw new Error(`organic order quota cannot give persona ${persona} 2-3 orders per user`);
    }
    const extras = slots - candidates.length * 2;
    candidates.forEach((userId, index) => remainingByUser.set(userId, 2 + (index < extras ? 1 : 0)));
  }
  const personaCursors = new Map();
  const orders = [];
  let orderIndex = 0;
  for (const template of templates) {
    const candidates = personaUsers.get(template.persona) || users;
    if (!candidates.length) throw new Error(`no users assigned to persona ${template.persona}`);
    let cursor = personaCursors.get(template.persona) || 0;
    for (let repeat = 0; repeat < template.repeatCount; repeat += 1) {
      let scanned = 0;
      while (remainingByUser.get(candidates[cursor]) === 0 && scanned < candidates.length) {
        cursor = (cursor + 1) % candidates.length;
        scanned += 1;
      }
      if (remainingByUser.get(candidates[cursor]) === 0) {
        throw new Error(`organic order quota exhausted for persona ${template.persona}`);
      }
      const userId = candidates[cursor];
      remainingByUser.set(userId, remainingByUser.get(userId) - 1);
      const items = productItems(template.productIds, productMap, orderIndex);
      if (items.some((item) => cold.has(item.productId) || fixtureProducts.has(item.productId))) {
        throw new Error(`organic template ${template.templateId} contains a cold/trap product`);
      }
      orders.push({
        storeId: spec.store_id,
        runId: null,
        userId,
        orderDate: orderDate(spec, orderIndex),
        totalAmount: items.reduce((sum, item) => sum + item.totalPrice, 0).toFixed(2),
        items,
        templateId: template.templateId,
        kind: 'organic'
      });
      orderIndex += 1;
      cursor = (cursor + 1) % candidates.length;
    }
    personaCursors.set(template.persona, cursor);
  }
  if ([...remainingByUser.values()].some((remaining) => remaining !== 0)) {
    throw new Error('organic order quota did not cover every user exactly');
  }
  const trapOccurrences = new Map();
  for (let index = 0; index < semanticCount; index += 1) {
    const trap = spec.semantic_traps[index % spec.semantic_traps.length];
    const occurrence = trapOccurrences.get(trap.trap_id) || 0;
    trapOccurrences.set(trap.trap_id, occurrence + 1);
    const target = trap.targets[occurrence % trap.targets.length];
    const items = productItems([trap.anchor, target], productMap, orderIndex);
    orders.push({
      storeId: spec.store_id,
      runId: null,
      userId: users[index % users.length],
      orderDate: orderDate(spec, orderIndex),
      totalAmount: items.reduce((sum, item) => sum + item.totalPrice, 0).toFixed(2),
      items,
      templateId: `semantic-${trap.trap_id}`,
      trapId: trap.trap_id,
      kind: 'semantic_trap'
    });
    orderIndex += 1;
  }
  for (const trap of spec.semantic_traps) {
    const trapOrders = orders.filter((order) => order.trapId === trap.trap_id).length;
    if (trapOrders < spec.minimum_semantic_copurchase_count) {
      throw new Error(`semantic trap ${trap.trap_id} has only ${trapOrders} orders`);
    }
  }
  if (orders.length !== spec.num_orders) throw new Error(`generated ${orders.length} orders`);
  return orders;
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
      (id,store_id,customer_id,created_by,order_date,delivery_type,total_amount,payment_status,status,payment_method,benchmark_run_id,benchmark_kind,benchmark_template_id,benchmark_trap_id)
     OVERRIDING SYSTEM VALUE
     SELECT id,store_id,customer_id,NULL,order_date,'pickup',total_amount,'paid','delivered','cash',benchmark_run_id,benchmark_kind,benchmark_template_id,benchmark_trap_id
     FROM unnest($1::bigint[],$2::bigint[],$3::bigint[],$4::timestamptz[],$5::numeric[],$6::text[],$7::text[],$8::text[],$9::int[])
       AS input(id,store_id,customer_id,order_date,total_amount,benchmark_run_id,benchmark_kind,benchmark_template_id,benchmark_trap_id)`,
    [
      orders.map((order) => order.id), orders.map((order) => order.storeId),
      orders.map((order) => order.userId), orders.map((order) => order.orderDate),
      orders.map((order) => order.totalAmount), orders.map((order) => order.runId),
      orders.map((order) => order.kind), orders.map((order) => order.templateId),
      orders.map((order) => order.trapId || null)
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

async function seedOrders({ client, spec, runId, products, coldProducts, users, affinityModel }) {
  const resolvedUsers = users || Array.from({ length: spec.num_users }, (_, index) => index + 1);
  const generated = generateOrderPlan({
    spec,
    users: resolvedUsers,
    products,
    coldProducts,
    affinityModel
  }).map((order) => ({ ...order, runId }));
  await client.query('BEGIN');
  try {
    await client.query('SET TRANSACTION READ WRITE');
    await client.query("SET LOCAL statement_timeout='5min'");
    await client.query('ALTER TABLE sale_order ADD COLUMN IF NOT EXISTS benchmark_run_id TEXT');
    await client.query('ALTER TABLE sale_order ADD COLUMN IF NOT EXISTS benchmark_kind TEXT');
    await client.query('ALTER TABLE sale_order ADD COLUMN IF NOT EXISTS benchmark_template_id TEXT');
    await client.query('ALTER TABLE sale_order ADD COLUMN IF NOT EXISTS benchmark_trap_id INTEGER');
    await client.query('ALTER TABLE sale_order DROP COLUMN IF EXISTS benchmark_trap_target_id');
    await client.query(`CREATE INDEX IF NOT EXISTS idx_sale_order_benchmark_run
      ON sale_order(store_id,benchmark_run_id,order_date)
      WHERE benchmark_run_id IS NOT NULL`);
    const existing = await client.query(
      `SELECT count(*)::int AS count FROM sale_order
       WHERE store_id=$1 AND benchmark_run_id=$2`,
      [spec.store_id, runId]
    );
    if (existing.rows[0].count !== 0) {
      throw new Error(`immutable benchmark orders already exist for ${runId}`);
    }
    const ids = await reserveIds(client, generated.length);
    for (let offset = 0; offset < spec.num_orders; offset += 500) {
      const batch = generated.slice(offset, offset + 500).map((order, index) => ({
        ...order,
        id: ids[offset + index],
        storeId: spec.store_id
      }));
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

module.exports = { generateOrderPlan, seedOrders };
