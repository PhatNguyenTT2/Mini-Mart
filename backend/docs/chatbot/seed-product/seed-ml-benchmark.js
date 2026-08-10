'use strict';

const crypto = require('crypto');
const spec = require('./benchmark-spec.json');
const {
  catalogChecksum,
  connectDatabases,
  ensureBenchmarkSchema,
  selectColdProducts
} = require('./benchmark-lib');
const { seedMlEvents } = require('./seed-ml-events');
const { rebuildInteractions } = require('./mock-interactions');
const { seedOrders } = require('./mock-orders');
const { populateCopurchase } = require('./populate-copurchase');

async function reclaimLegacyMlStorage(chat) {
  const disposableIndexes = [
    'idx_ml_event_session',
    'idx_ml_event_origin',
    'idx_ml_event_store_ts',
    'idx_ml_event_user_ts'
  ];
  for (const indexName of disposableIndexes) {
    await chat.query('BEGIN');
    try {
      await chat.query('SET TRANSACTION READ WRITE');
      await chat.query(`DROP INDEX IF EXISTS ${indexName}`);
      await chat.query('COMMIT');
    } catch (error) {
      await chat.query('ROLLBACK');
      throw error;
    }
  }
  await chat.query('BEGIN');
  try {
    await chat.query('SET TRANSACTION READ WRITE');
    await chat.query('LOCK TABLE ml_interaction_event_v1 IN ACCESS EXCLUSIVE MODE');
    await chat.query('LOCK TABLE user_product_interaction IN ACCESS EXCLUSIVE MODE');
    const events = await chat.query(
      `SELECT count(*)::int AS total,
              count(*) FILTER (WHERE store_id<>$1)::int AS other_store
       FROM ml_interaction_event_v1`,
      [spec.store_id]
    );
    const interactions = await chat.query(
      `SELECT count(*)::int AS total,
              count(*) FILTER (WHERE store_id<>$1)::int AS other_store
       FROM user_product_interaction`,
      [spec.store_id]
    );
    if (events.rows[0].other_store !== 0 || interactions.rows[0].other_store !== 0) {
      throw new Error('refusing TRUNCATE because an ML legacy table contains another store');
    }
    await chat.query('TRUNCATE TABLE ml_interaction_event_v1, user_product_interaction');
    await chat.query(
      'TRUNCATE TABLE ml_benchmark_item_partition_v1, ml_benchmark_run_v1'
    );
    await chat.query('COMMIT');
    return {
      removedEvents: events.rows[0].total,
      removedInteractions: interactions.rows[0].total
    };
  } catch (error) {
    await chat.query('ROLLBACK');
    throw error;
  }
}

function argumentValue(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : undefined;
}

function validateArguments({ mutating }) {
  if (process.env.NODE_ENV === 'production') {
    throw new Error('benchmark rebuild is forbidden when NODE_ENV=production');
  }
  if (mutating && !process.argv.includes('--confirm-rebuild')) {
    throw new Error('destructive store-scoped rebuild requires --confirm-rebuild');
  }
  const requestedStore = argumentValue('--store-id');
  const requestedSeed = argumentValue('--seed');
  if (requestedStore !== undefined && Number(requestedStore) !== spec.store_id) {
    throw new Error(`--store-id must match benchmark-spec.json (${spec.store_id})`);
  }
  if (requestedSeed !== undefined && Number(requestedSeed) !== spec.seed) {
    throw new Error(`--seed must match benchmark-spec.json (${spec.seed})`);
  }
}

async function validateRun({ clients, runId, specHash, coldProducts, ruleSummary }) {
  const lineage = await clients.chat.query(
    `SELECT count(*)::int AS count FROM ml_benchmark_run_v1
     WHERE benchmark_run_id=$1 AND benchmark_spec_sha256=$2 AND status='staging'`,
    [runId, specHash]
  );
  if (lineage.rows[0].count !== 1) throw new Error('benchmark spec lineage mismatch');
  const events = await clients.chat.query(
    `SELECT count(*)::int AS events,count(DISTINCT user_id)::int AS users,
            count(DISTINCT product_id)::int AS products,
            count(*) FILTER (WHERE event_ts <= $3)::int AS train,
            count(*) FILTER (WHERE event_ts >= $4 AND event_ts <= $5)::int AS val,
            count(*) FILTER (WHERE event_ts >= $6)::int AS test
     FROM ml_interaction_event_v1 WHERE store_id=$1 AND benchmark_run_id=$2`,
    [
      spec.store_id, runId, spec.cutoffs.train_end, spec.cutoffs.val_start,
      spec.cutoffs.val_end, spec.cutoffs.test_start
    ]
  );
  const actual = events.rows[0];
  for (const [name, expected] of Object.entries({
    events: spec.num_events,
    users: spec.num_users,
    products: spec.num_products,
    ...spec.split_counts
  })) {
    if (actual[name] !== expected) throw new Error(`${name}=${actual[name]} expected=${expected}`);
  }
  const coldEvents = await clients.chat.query(
    `SELECT count(DISTINCT product_id)::int AS products,
            count(*) FILTER (WHERE event_ts < $2 OR event_type <> 'purchase')::int AS invalid
     FROM ml_interaction_event_v1
     WHERE store_id=$1 AND product_id=ANY($3::bigint[]) AND benchmark_run_id=$4`,
    [spec.store_id, spec.cutoffs.test_start, coldProducts, runId]
  );
  if (coldEvents.rows[0].products !== spec.num_cold_products || coldEvents.rows[0].invalid !== 0) {
    throw new Error(`cold isolation failed: ${JSON.stringify(coldEvents.rows[0])}`);
  }
  const coldOrders = await clients.order.query(
    `SELECT count(*)::int AS count FROM sale_order o JOIN sale_order_detail d ON d.order_id=o.id
     WHERE o.store_id=$1 AND d.product_id=ANY($2::bigint[]) AND o.order_date <= $3
       AND o.benchmark_run_id=$4`,
    [spec.store_id, coldProducts, spec.cutoffs.train_end, runId]
  );
  if (coldOrders.rows[0].count !== 0) throw new Error('cold products leaked into train orders');
  let passed = 0;
  for (const trap of spec.semantic_traps) {
    const result = await clients.chat.query(
      `SELECT co_purchase_count,lift FROM co_purchase_stats
       WHERE store_id=$1
         AND ((product_id_a=$2 AND product_id_b=ANY($3::bigint[]))
           OR (product_id_b=$2 AND product_id_a=ANY($3::bigint[])))
         AND co_purchase_count>=100 AND lift>=10
       LIMIT 1`,
      [spec.store_id, trap.anchor, trap.targets]
    );
    if (result.rowCount) passed += 1;
  }
  if (passed !== spec.semantic_traps.length) throw new Error(`semantic traps ${passed}/10 passed`);
  if (ruleSummary.totalOrders !== spec.num_orders) throw new Error('Apriori basket denominator mismatch');
}

async function main() {
  const preflightOnly = process.argv.includes('--preflight-only');
  const resumeRunId = argumentValue('--resume-run');
  validateArguments({ mutating: !preflightOnly });
  const clients = await connectDatabases();
  let runId;
  try {
    const catalogResult = await clients.catalog.query(
      `SELECT id AS product_id,category_id,name,unit_price,vendor
       FROM product WHERE is_active=true ORDER BY id`
    );
    const products = catalogResult.rows.map((row) => ({
      ...row,
      product_id: Number(row.product_id),
      category_id: Number(row.category_id),
      unit_price: Number(row.unit_price),
      vendor: String(row.vendor || 'unknown')
    }));
    if (products.length !== spec.num_products) throw new Error(`catalog has ${products.length} products`);
    const customerResult = await clients.auth.query(
      `SELECT count(*)::int AS total,count(*) FILTER (WHERE is_active)::int AS active,
              count(DISTINCT id)::int AS distinct_ids,min(id)::bigint AS min_id,
              max(id)::bigint AS max_id,
              count(*) FILTER (WHERE user_id IS NULL)::int AS unlinked
       FROM customer`
    );
    const customers = customerResult.rows[0];
    const customerContractValid = customers.total === spec.num_users
      && customers.active === spec.num_users
      && customers.distinct_ids === spec.num_users
      && Number(customers.min_id) === 1
      && Number(customers.max_id) === spec.num_users
      && customers.unlinked === 0;
    if (!customerContractValid) {
      throw new Error(`customer contract invalid: ${JSON.stringify(customers)}`);
    }
    const trapIds = new Set(spec.semantic_traps.flatMap((trap) => [trap.anchor, ...trap.targets]));
    const productIds = new Set(products.map((product) => product.product_id));
    const missingTraps = [...trapIds].filter((productId) => !productIds.has(productId));
    if (missingTraps.length) throw new Error(`semantic trap products missing: ${missingTraps.join(',')}`);
    const catalogHash = catalogChecksum(products);
    const specHash = crypto.createHash('sha256').update(JSON.stringify(spec)).digest('hex');
    if (preflightOnly) {
      const chatState = await clients.chat.query(
        `SELECT to_regclass('public.ml_interaction_event_v1') IS NOT NULL AS event_table,
                to_regclass('public.user_product_interaction') IS NOT NULL AS interaction_table`
      );
      const orderState = await clients.order.query(
        `SELECT count(*)::int AS existing_orders,
                count(*) FILTER (
                  WHERE benchmark_run_id IS NULL AND created_by=1
                )::int AS legacy_orders,
                count(*) FILTER (
                  WHERE benchmark_run_id IS NOT NULL
                )::int AS benchmark_orders,
                count(*) FILTER (
                  WHERE benchmark_run_id IS NULL AND created_by IS DISTINCT FROM 1
                )::int AS business_orders
         FROM sale_order WHERE store_id=$1`,
        [spec.store_id]
      );
      console.log(JSON.stringify({
        status: 'preflight-ok',
        storeId: spec.store_id,
        customers: customers.total,
        catalogProducts: products.length,
        semanticTrapProducts: trapIds.size,
        catalogHash,
        specHash,
        ...chatState.rows[0],
        ...orderState.rows[0]
      }));
      return;
    }
    const coldProducts = selectColdProducts(products, spec);
    if (resumeRunId) {
      await ensureBenchmarkSchema(clients.chat);
      runId = resumeRunId;
      const staged = await clients.chat.query(
        `SELECT r.status,r.catalog_sha256,r.benchmark_spec_sha256,
                (SELECT count(*)::int FROM ml_interaction_event_v1 e
                 WHERE e.store_id=r.store_id AND e.benchmark_run_id=r.benchmark_run_id) AS events,
                (SELECT count(*)::int FROM ml_benchmark_item_partition_v1 p
                 WHERE p.store_id=r.store_id AND p.benchmark_run_id=r.benchmark_run_id) AS products,
                (SELECT count(*)::int FROM ml_benchmark_item_partition_v1 p
                 WHERE p.store_id=r.store_id AND p.benchmark_run_id=r.benchmark_run_id
                   AND p.partition='cold') AS cold_products
         FROM ml_benchmark_run_v1 r
         WHERE r.store_id=$1 AND r.benchmark_run_id=$2`,
        [spec.store_id, runId]
      );
      const state = staged.rows[0];
      if (
        staged.rowCount !== 1 || !['staging', 'failed'].includes(state.status)
        || state.catalog_sha256 !== catalogHash
        || state.benchmark_spec_sha256 !== specHash
        || state.events !== spec.num_events || state.products !== spec.num_products
        || state.cold_products !== spec.num_cold_products
      ) throw new Error(`resume lineage is invalid: ${JSON.stringify(state || null)}`);
      if (state.status === 'failed') {
        await clients.chat.query('BEGIN');
        try {
          await clients.chat.query('SET TRANSACTION READ WRITE');
          await clients.chat.query(
            `UPDATE ml_benchmark_run_v1 SET status='staging',published_at=NULL
             WHERE store_id=$1 AND benchmark_run_id=$2`,
            [spec.store_id, runId]
          );
          await clients.chat.query('COMMIT');
        } catch (error) {
          await clients.chat.query('ROLLBACK');
          throw error;
        }
      }
      console.log(JSON.stringify({ status: 'resuming-staged-events', runId }));
    } else {
      const reclaimed = await reclaimLegacyMlStorage(clients.chat);
      console.log(JSON.stringify({ status: 'legacy-ml-storage-reclaimed', ...reclaimed }));
      await ensureBenchmarkSchema(clients.chat);
      runId = `benchmark-v3-s${spec.seed}-${catalogHash.slice(0, 10)}-${specHash.slice(0, 10)}`;
      await seedMlEvents({
        client: clients.chat,
        spec,
        runId,
        catalogHash,
        specHash,
        products,
        coldProducts
      });
    }
    await rebuildInteractions({ client: clients.chat, storeId: spec.store_id, runId });
    await seedOrders({ client: clients.order, spec, runId, products, coldProducts });
    const ruleSummary = await populateCopurchase({
      chatClient: clients.chat,
      orderClient: clients.order,
      spec,
      runId
    });
    await validateRun({ clients, runId, specHash, coldProducts, ruleSummary });
    await clients.chat.query('BEGIN');
    try {
      await clients.chat.query('SET TRANSACTION READ WRITE');
      await clients.chat.query(
        `UPDATE ml_benchmark_run_v1 SET status='ready',published_at=NOW()
         WHERE benchmark_run_id=$1`,
        [runId]
      );
      await clients.chat.query('COMMIT');
    } catch (error) {
      await clients.chat.query('ROLLBACK');
      throw error;
    }
    const digest = crypto.createHash('sha256').update(JSON.stringify({ runId, ruleSummary })).digest('hex');
    console.log(JSON.stringify({ status: 'ready', runId, coldProducts: coldProducts.length, ruleSummary, digest }));
  } catch (error) {
    if (runId) {
      await clients.chat.query('BEGIN').then(async () => {
        await clients.chat.query('SET TRANSACTION READ WRITE');
        await clients.chat.query(
          `UPDATE ml_benchmark_run_v1 SET status='failed' WHERE benchmark_run_id=$1`, [runId]
        );
        await clients.chat.query('COMMIT');
      }).catch(async () => {
        await clients.chat.query('ROLLBACK').catch(() => undefined);
      });
    }
    throw error;
  } finally {
    await Promise.all(Object.values(clients).map((client) => client.end()));
  }
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error.stack || error.message);
    process.exitCode = 1;
  });
}

module.exports = { main };
