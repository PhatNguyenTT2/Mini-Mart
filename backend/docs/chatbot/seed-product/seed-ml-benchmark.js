'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
let spec;
const {
  catalogChecksum,
  connectDatabases,
  ensureBenchmarkSchema,
  selectColdProducts
} = require('./benchmark-lib');
const { mulberry32 } = require('./benchmark-lib');
const {
  buildPersonaAssignments,
  buildUserAffinities,
  buildOrganicBundleTemplates
} = require('./benchmark-affinity');
const { seedMlEvents } = require('./seed-ml-events');
const { rebuildInteractions } = require('./mock-interactions');
const { seedOrders } = require('./mock-orders');
const { populateCopurchase } = require('./populate-copurchase');

async function reclaimLegacyMlStorage(chat, storeId) {
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
    const events = await chat.query(
      `SELECT count(*)::int AS total
       FROM ml_interaction_event_v1
       WHERE store_id=$1 AND benchmark_run_id IS NULL`,
      [storeId]
    );
    await chat.query(
      `DELETE FROM ml_interaction_event_v1
       WHERE store_id=$1 AND benchmark_run_id IS NULL`,
      [storeId]
    );
    await chat.query('COMMIT');
    return { removedLegacyEvents: events.rows[0].total };
  } catch (error) {
    await chat.query('ROLLBACK');
    throw error;
  }
}

function argumentValue(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : undefined;
}

function loadBenchmarkSpec(specPath) {
  let parsed;
  try {
    parsed = JSON.parse(fs.readFileSync(specPath, 'utf8'));
  } catch (error) {
    throw new Error(`cannot load benchmark spec ${specPath}: ${error.message}`);
  }
  if (parsed.schema_version !== '2.1.0' || parsed.generator_version !== '4.0.0') {
    throw new Error('only benchmark generator v4/schema 2.1 specs are supported');
  }
  if (!Number.isInteger(parsed.store_id) || !Number.isInteger(parsed.seed)) {
    throw new Error('benchmark spec store_id and seed must be integers');
  }
  return parsed;
}

function validateArguments({ mutating, benchmarkSpec }) {
  if (process.env.NODE_ENV === 'production') {
    throw new Error('benchmark rebuild is forbidden when NODE_ENV=production');
  }
  if (mutating && !process.argv.includes('--confirm-rebuild')) {
    throw new Error('destructive store-scoped rebuild requires --confirm-rebuild');
  }
  const requestedStore = argumentValue('--store-id');
  const requestedSeed = argumentValue('--seed');
  if (requestedStore !== undefined && Number(requestedStore) !== benchmarkSpec.store_id) {
    throw new Error(`--store-id must match the loaded benchmark spec (${benchmarkSpec.store_id})`);
  }
  if (requestedSeed !== undefined && Number(requestedSeed) !== benchmarkSpec.seed) {
    throw new Error(`--seed must match the loaded benchmark spec (${benchmarkSpec.seed})`);
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
         AND co_purchase_count >= $4 AND lift >= $5
       LIMIT 1`,
      [
        spec.store_id,
        trap.anchor,
        trap.targets,
        spec.minimum_semantic_copurchase_count,
        spec.minimum_semantic_lift
      ]
    );
    if (result.rowCount) passed += 1;
  }
  if (passed !== spec.semantic_traps.length) throw new Error(`semantic traps ${passed}/10 passed`);
  if (ruleSummary.totalOrders !== spec.num_orders) throw new Error('Apriori basket denominator mismatch');
  const fixtureIds = spec.semantic_traps.flatMap((trap) => [trap.anchor, ...trap.targets]);
  const context = await clients.chat.query(
    `WITH history AS (
       SELECT DISTINCT user_id,product_id
       FROM ml_interaction_event_v1
       WHERE store_id=$1 AND benchmark_run_id=$2 AND event_origin='organic'
         AND event_type='purchase' AND event_ts <= $3
     ),
     eligible AS (
       SELECT DISTINCT target.user_id
       FROM ml_interaction_event_v1 target
       WHERE target.store_id=$1 AND target.benchmark_run_id=$2
         AND target.event_origin='organic' AND target.event_type='purchase'
         AND target.event_ts > $3 AND target.event_ts <= $5
         AND NOT EXISTS (
           SELECT 1 FROM history
           WHERE history.user_id=target.user_id AND history.product_id=target.product_id
         )
     ),
     latest AS (
       SELECT DISTINCT ON (user_id) user_id,product_id
       FROM ml_interaction_event_v1
       WHERE store_id=$1 AND benchmark_run_id=$2 AND event_origin='organic'
         AND event_type='purchase' AND event_ts <= $3
       ORDER BY user_id,event_ts DESC,event_id DESC
     )
     SELECT count(*)::int AS eligible,
            count(*) FILTER (WHERE EXISTS (
              SELECT 1 FROM co_purchase_stats c
              WHERE c.store_id=$1
                AND latest.product_id <> ALL($4::bigint[])
                AND ((c.product_id_a=latest.product_id AND c.product_id_b <> ALL($4::bigint[]))
                  OR (c.product_id_b=latest.product_id AND c.product_id_a <> ALL($4::bigint[])))
            ))::int AS covered
     FROM latest JOIN eligible USING (user_id)`,
    [spec.store_id, runId, spec.cutoffs.train_end, fixtureIds, spec.cutoffs.val_end]
  );
  const eligibleContextUsers = Number(context.rows[0].eligible);
  const coveredContextUsers = Number(context.rows[0].covered);
  const valContextRuleCoverage = coveredContextUsers / Math.max(1, eligibleContextUsers);
  const targetAlignment = await clients.chat.query(
    `WITH history AS (
       SELECT DISTINCT user_id,product_id
       FROM ml_interaction_event_v1
       WHERE store_id=$1 AND benchmark_run_id=$2 AND event_origin='organic'
         AND event_type='purchase' AND event_ts <= $3
     ), targets AS (
       SELECT DISTINCT target.user_id,target.product_id
       FROM ml_interaction_event_v1 target
       WHERE target.store_id=$1 AND target.benchmark_run_id=$2
         AND target.event_origin='organic' AND target.event_type='purchase'
         AND target.event_ts > $3 AND target.event_ts <= $5
         AND NOT EXISTS (
           SELECT 1 FROM history
           WHERE history.user_id=target.user_id AND history.product_id=target.product_id
         )
     ), latest AS (
       SELECT DISTINCT ON (user_id) user_id,product_id
       FROM ml_interaction_event_v1
       WHERE store_id=$1 AND benchmark_run_id=$2 AND event_origin='organic'
         AND event_type='purchase' AND event_ts <= $3
       ORDER BY user_id,event_ts DESC,event_id DESC
     )
     SELECT count(DISTINCT targets.user_id)::int AS eligible,
            count(DISTINCT targets.user_id) FILTER (
              WHERE latest.product_id <> ALL($4::bigint[])
                AND targets.product_id <> ALL($4::bigint[])
                AND EXISTS (
                  SELECT 1 FROM co_purchase_stats c
                  WHERE c.store_id=$1
                    AND ((c.product_id_a=latest.product_id AND c.product_id_b=targets.product_id)
                      OR (c.product_id_b=latest.product_id AND c.product_id_a=targets.product_id))
                )
            )::int AS aligned
     FROM targets JOIN latest USING (user_id)`,
    [spec.store_id, runId, spec.cutoffs.train_end, fixtureIds, spec.cutoffs.val_end]
  );
  const eligibleValRuleTargetUsers = Number(targetAlignment.rows[0].eligible);
  const alignedValRuleTargetUsers = Number(targetAlignment.rows[0].aligned);
  const valRuleTargetRate = alignedValRuleTargetUsers
    / Math.max(1, eligibleValRuleTargetUsers);
  if (eligibleValRuleTargetUsers !== eligibleContextUsers) {
    throw new Error('VAL rule-target eligibility differs from context eligibility');
  }
  if (ruleSummary.nonTrapDirectedRules < spec.minimum_non_trap_directed_rules) {
    throw new Error(`non-trap directed rules ${ruleSummary.nonTrapDirectedRules} below threshold`);
  }
  if (ruleSummary.distinctOrganicRuleItems < spec.minimum_distinct_organic_rule_items) {
    throw new Error(`organic rule items ${ruleSummary.distinctOrganicRuleItems} below threshold`);
  }
  if (ruleSummary.trapAnchoredRuleFraction > spec.maximum_trap_anchored_rule_fraction) {
    throw new Error(`trap-anchored rule fraction ${ruleSummary.trapAnchoredRuleFraction} above threshold`);
  }
  if (valContextRuleCoverage < spec.minimum_val_context_rule_coverage) {
    throw new Error(`VAL context rule coverage ${valContextRuleCoverage} below threshold`);
  }
  if (valRuleTargetRate < spec.minimum_val_rule_target_rate) {
    throw new Error(`VAL rule-target rate ${valRuleTargetRate} below threshold`);
  }
  return {
    ...ruleSummary,
    eligibleValContextUsers: eligibleContextUsers,
    valContextUsersWithRule: coveredContextUsers,
    valContextRuleCoverage,
    eligibleValRuleTargetUsers,
    alignedValRuleTargetUsers,
    valRuleTargetRate
  };
}

async function requireUnusedBenchmarkRun(chat, storeId, runId) {
  const existing = await chat.query(
    `SELECT status FROM ml_benchmark_run_v1
     WHERE store_id=$1 AND benchmark_run_id=$2`,
    [storeId, runId]
  );
  if (existing.rowCount !== 0) {
    throw new Error(
      `benchmark run ${runId} already exists with status ${existing.rows[0].status}; `
      + 'benchmark lineages are immutable'
    );
  }
}

function buildAffinityModel({ spec, products, coldProducts, users }) {
  if (spec.generator_version !== '4.0.0') return undefined;
  const affinityRandom = mulberry32(spec.seed);
  const personaByUser = buildPersonaAssignments(users, spec.persona_distribution, affinityRandom);
  const warmProducts = products
    .map((product) => Number(product.product_id))
    .filter((id) => !coldProducts.includes(id));
  const affinity = buildUserAffinities(
    products, warmProducts, users, personaByUser, spec.persona_distribution.length
  );
  const fixtureProducts = spec.semantic_traps.flatMap((trap) => [trap.anchor, ...trap.targets]);
  const bundleTemplates = buildOrganicBundleTemplates({
    products,
    warmProducts,
    fixtureProducts,
    personaByUser,
    affinityByUser: affinity.affinityByUser,
    categoryPersona: affinity.categoryPersona,
    preferredProducts: affinity.preferredProducts,
    spec
  });
  return { personaByUser, ...affinity, bundleTemplates };
}

async function main() {
  const requestedSpec = argumentValue('--spec');
  if (!requestedSpec) {
    throw new Error('--spec is required; choose an explicit benchmark lineage');
  }
  const specPath = path.isAbsolute(requestedSpec)
    ? requestedSpec
    : path.resolve(process.cwd(), requestedSpec);
  spec = loadBenchmarkSpec(specPath);
  const preflightOnly = process.argv.includes('--preflight-only');
  const resumeRunId = argumentValue('--resume-run');
  validateArguments({ mutating: !preflightOnly, benchmarkSpec: spec });
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
    const users = Array.from({ length: spec.num_users }, (_, index) => index + 1);
    const affinityModel = buildAffinityModel({ spec, products, coldProducts, users });
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
        staged.rowCount !== 1 || state.status !== 'staging'
        || state.catalog_sha256 !== catalogHash
        || state.benchmark_spec_sha256 !== specHash
        || state.events !== spec.num_events || state.products !== spec.num_products
        || state.cold_products !== spec.num_cold_products
      ) throw new Error(`resume lineage is invalid: ${JSON.stringify(state || null)}`);
      console.log(JSON.stringify({ status: 'resuming-staged-events', runId }));
    } else {
      await ensureBenchmarkSchema(clients.chat);
      runId = `benchmark-v${String(spec.generator_version).split('.')[0]}-s${spec.seed}-${catalogHash.slice(0, 10)}-${specHash.slice(0, 10)}`;
      await requireUnusedBenchmarkRun(clients.chat, spec.store_id, runId);
      const reclaimed = await reclaimLegacyMlStorage(clients.chat, spec.store_id);
      console.log(JSON.stringify({ status: 'legacy-ml-storage-reclaimed', ...reclaimed }));
      await seedMlEvents({
        client: clients.chat,
        spec,
        runId,
        catalogHash,
        specHash,
        products,
        coldProducts,
        affinityModel
      });
    }
    await rebuildInteractions({ client: clients.chat, storeId: spec.store_id, runId });
    await seedOrders({
      client: clients.order,
      spec,
      runId,
      products,
      coldProducts,
      users,
      affinityModel
    });
    const ruleSummary = await populateCopurchase({
      chatClient: clients.chat,
      orderClient: clients.order,
      spec,
      runId
    });
    const coverage = await validateRun({ clients, runId, specHash, coldProducts, ruleSummary });
    await clients.chat.query(
      'UPDATE ml_benchmark_run_v1 SET rule_coverage=$2::jsonb WHERE benchmark_run_id=$1',
      [runId, JSON.stringify(coverage)]
    );
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
    const digest = crypto.createHash('sha256').update(JSON.stringify({ runId, coverage })).digest('hex');
    console.log(JSON.stringify({ status: 'ready', runId, coldProducts: coldProducts.length, ruleSummary: coverage, digest }));
  } catch (error) {
    if (runId) {
      await clients.chat.query('BEGIN').then(async () => {
        await clients.chat.query('SET TRANSACTION READ WRITE');
        await clients.chat.query(
          `UPDATE ml_benchmark_run_v1 SET status='failed'
           WHERE benchmark_run_id=$1 AND status='staging'`,
          [runId]
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

module.exports = {
  loadBenchmarkSpec,
  main,
  reclaimLegacyMlStorage,
  requireUnusedBenchmarkRun
};
