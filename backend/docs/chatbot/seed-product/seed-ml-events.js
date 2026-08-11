'use strict';

const crypto = require('crypto');
const { mulberry32 } = require('./benchmark-lib');

function stableHashInt(...parts) {
  const digest = crypto.createHash('sha256').update(parts.join(':')).digest();
  return digest.readUInt32BE(0);
}

function deterministicTransitionUsers(spec, users) {
  const expected = Math.floor(users.length * spec.organic_rule_transition_fraction);
  if (expected !== spec.transition_user_count) {
    throw new Error('transition user count does not match the v5 fraction');
  }
  return new Set(
    [...users]
      .map((userId) => ({ userId, key: stableHashInt(spec.seed, userId) }))
      .sort((left, right) => left.key - right.key || left.userId - right.userId)
      .slice(0, expected)
      .map(({ userId }) => userId)
  );
}

function timestampAt(index, count, startValue, endValue) {
  const start = Date.parse(startValue);
  const end = Date.parse(endValue);
  const ratio = count <= 1 ? 0 : index / (count - 1);
  return new Date(Math.floor(start + (end - start) * ratio)).toISOString();
}

function zipfProduct(products, random, drift = 0) {
  if (!products.length) throw new Error('cannot sample from an empty product pool');
  const rank = Math.min(products.length - 1, Math.floor(products.length * Math.pow(random(), 2.2)));
  return products[(rank + drift) % products.length];
}

function buildHeldoutCohort(spec, usersPerTrap, userStart) {
  return spec.semantic_traps.flatMap((trap, trapIndex) =>
    Array.from({ length: usersPerTrap }, (_, repeat) => ({
      userId: userStart + trapIndex * usersPerTrap + repeat,
      anchor: trap.anchor,
      target: trap.targets[repeat % trap.targets.length],
      trapId: trap.trap_id,
      reservedTargets: new Set(trap.targets)
    }))
  );
}

function chooseAvailable(pool, blocked, seen, random, drift) {
  for (let attempt = 0; attempt < 128; attempt += 1) {
    const candidate = zipfProduct(pool, random, drift);
    if (!blocked.has(candidate) && !seen.has(candidate)) return candidate;
  }
  const candidate = pool.find((value) => !blocked.has(value) && !seen.has(value));
  if (candidate === undefined) {
    const fallback = pool.find((value) => !blocked.has(value));
    if (fallback === undefined) throw new Error('no product remains outside the reserved target set');
    return fallback;
  }
  return candidate;
}

function conversionProbability(product, affinity, priorViews, spec, split) {
  const affinityMatch = [
    product.categoryPersona === affinity.categoryPersona,
    product.vendor === affinity.vendor,
    product.priceBand === affinity.priceBand
  ].filter(Boolean).length / 3;
  const driftPenalty = split === 'train' ? 0 : split === 'val' ? 0.03 : 0.06;
  const viewFactor = Math.min(1, priorViews / 2);
  const probability = spec.session_purchase_probability
    + spec.conversion_affinity_weight * affinityMatch
    + spec.conversion_popularity_weight * product.popularity
    + spec.conversion_price_weight * (product.priceBand === affinity.priceBand ? 1 : -1)
    + 0.05 * viewFactor
    - driftPenalty;
  return Math.max(0.05, Math.min(0.98, probability));
}

function buildOrganicRows({
  split, count, runId, users, warmProducts, preferredProducts, personaByUser,
  affinityByUser, productMetadata, categoryPersona, blockedByUser, seenByUser,
  lastPurchaseByUser, bundleNeighbors, random, spec
}) {
  const rows = [];
  const transitionUsers = deterministicTransitionUsers(spec, users);
  let sessionIndex = 0;
  const drift = split === 'train' ? 0 : split === 'val' ? 37 : 83;
  while (rows.length < count) {
    const remaining = count - rows.length;
    let length = Math.min(
      remaining,
      spec.session_min_events
        + Math.floor(random() * (spec.session_max_events - spec.session_min_events + 1))
    );
    if (remaining - length === 1 && length > spec.session_min_events) length -= 1;
    const guaranteedUser = sessionIndex < users.length;
    const userId = guaranteedUser ? users[sessionIndex] : users[Math.floor(random() * users.length)];
    const persona = personaByUser.get(userId);
    const blocked = blockedByUser.get(userId) || new Set();
    const seen = seenByUser.get(userId) || new Set();
    const preferred = preferredProducts.get(userId);
    const preferenceProbability = spec.split_preference_probability[split];
    const sourcePool = random() < preferenceProbability && preferred.length
      ? preferred
      : warmProducts;
    const requireNovelPurchase = split !== 'train' && guaranteedUser;
    const priorPurchase = lastPurchaseByUser.get(userId);
    const availableRuleNeighbors = (bundleNeighbors.get(priorPurchase) || []).filter(
      (productId) => !blocked.has(productId) && !seen.has(productId)
    );
    let transitionProduct;
    if (transitionUsers.has(userId) && priorPurchase !== undefined && availableRuleNeighbors.length) {
      const offset = stableHashInt(spec.seed, userId, split, sessionIndex);
      transitionProduct = availableRuleNeighbors[offset % availableRuleNeighbors.length];
    }
    let mainProduct;
    if (split === 'train' && sessionIndex < warmProducts.length) {
      mainProduct = warmProducts[sessionIndex];
    } else if (transitionProduct !== undefined) {
      mainProduct = transitionProduct;
    } else if (requireNovelPurchase) {
      mainProduct = chooseAvailable(sourcePool, blocked, seen, random, drift);
    } else {
      mainProduct = chooseAvailable(sourcePool, blocked, new Set(), random, drift);
    }
    const sessionId = `${runId}:${split}:organic:${String(sessionIndex).padStart(7, '0')}`;
    const metadata = productMetadata.get(mainProduct);
    // Every deterministic transition user needs a real train context before
    // the VAL transition is emitted.  Without this explicit purchase, the
    // user can complete a view-only first session and silently lose the
    // context->target rule contract even though the cohort membership is
    // correct.
    const forceTransitionContext = split === 'train' && transitionUsers.has(userId) && guaranteedUser;
    const willPurchase = forceTransitionContext || (length >= 2 && (
      requireNovelPurchase
      || random() < conversionProbability(
        { ...metadata, categoryPersona: categoryPersona.get(metadata.category) },
        affinityByUser.get(userId),
        length - 1,
        spec,
        split
      )
    ));
    for (let offset = 0; offset < length; offset += 1) {
      const isLast = offset === length - 1;
      const eventType = isLast && willPurchase ? 'purchase' : 'view';
      const productId = eventType === 'purchase' || offset === 0
        ? mainProduct
        : (random() < 0.6
          ? mainProduct
          : chooseAvailable(sourcePool, blocked, new Set(), random, drift + offset));
      rows.push({
        userId,
        productId,
        persona,
        eventType,
        sessionId,
        eventOrigin: 'organic',
        cohortId: null
      });
      seen.add(productId);
      if (eventType === 'purchase') lastPurchaseByUser.set(userId, productId);
    }
    seenByUser.set(userId, seen);
    sessionIndex += 1;
  }
  if (rows.length !== count) throw new Error(`${split} organic event quota mismatch`);
  return rows;
}

function semanticTrainingRows(spec, runId, personaByUser) {
  return spec.semantic_traps.flatMap((trap, trapIndex) =>
    Array.from({ length: spec.semantic_event_pairs_per_trap }, (_, repeat) => {
      const userId = 1 + trapIndex * spec.semantic_event_pairs_per_trap + repeat;
      const sessionId = `${runId}:train:semantic:${trap.trap_id}:${repeat}`;
      const target = trap.targets[repeat % trap.targets.length];
      return [trap.anchor, target].map((productId) => ({
        userId,
        productId,
        persona: personaByUser.get(userId),
        eventType: 'purchase',
        sessionId,
        eventOrigin: 'semantic_trap',
        cohortId: `semantic-train-${trap.trap_id}`
      }));
    }).flat()
  );
}

function cohortRows(cohort, runId, split, phase, personaByUser, origin) {
  return cohort.map((row, index) => ({
    userId: row.userId,
    productId: phase === 'anchor' ? row.anchor : row.target,
    persona: personaByUser.get(row.userId),
    eventType: 'purchase',
    sessionId: `${runId}:${split}:${origin}:${phase}:${index}`,
    eventOrigin: origin,
    cohortId: origin === 'cold_start' ? `cold-${row.target}` : `semantic-${row.trapId}`
  }));
}

async function validateHeldoutCohort(
  client,
  { runId, storeId, cohort, historyEnd, targetStart, targetEnd, label }
) {
  const result = await client.query(
    `WITH expected AS (
       SELECT * FROM unnest($1::bigint[],$2::bigint[],$3::bigint[])
         AS x(user_id,anchor_id,target_id)
     ), cohort_events AS MATERIALIZED (
       SELECT e.user_id,e.product_id,e.event_type,e.event_ts,e.event_id
       FROM ml_interaction_event_v1 e
       WHERE e.benchmark_run_id=$4 AND e.store_id=$5 AND e.user_id=ANY($1::bigint[])
     ), last_purchase AS (
       SELECT DISTINCT ON (e.user_id) e.user_id,e.product_id
       FROM cohort_events e
       WHERE e.event_type='purchase' AND e.event_ts<=$6
       ORDER BY e.user_id,e.event_ts DESC,e.event_id DESC
     )
     SELECT (SELECT count(*) FROM expected)::int AS users,
            (SELECT count(*) FROM expected x JOIN last_purchase p USING(user_id)
             WHERE p.product_id=x.anchor_id)::int AS context_matches,
            (SELECT count(DISTINCT x.user_id) FROM expected x JOIN cohort_events e
               ON e.user_id=x.user_id AND e.product_id=x.target_id
             WHERE e.event_type='purchase' AND e.event_ts>=$7 AND e.event_ts<=$8)::int AS target_matches,
            (SELECT count(DISTINCT x.user_id) FROM expected x JOIN cohort_events e
               ON e.user_id=x.user_id AND e.product_id=x.target_id
             WHERE e.event_ts<=$6)::int AS leaked_targets`,
    [
      cohort.map((row) => row.userId), cohort.map((row) => row.anchor),
      cohort.map((row) => row.target), runId, storeId, historyEnd, targetStart, targetEnd
    ]
  );
  const actual = result.rows[0];
  if (
    actual.users !== cohort.length
    || actual.context_matches !== cohort.length
    || actual.target_matches !== cohort.length
    || actual.leaked_targets !== 0
  ) throw new Error(`${label} held-out cohort invalid: ${JSON.stringify(actual)}`);
}

async function insertBatch(client, rows) {
  await client.query(
    `INSERT INTO ml_interaction_event_v1
      (event_id,store_id,user_id,product_id,persona_cluster,event_type,event_ts,
       interaction_weight,session_id,event_origin,cohort_id,benchmark_run_id)
     SELECT * FROM unnest(
       $1::text[],$2::bigint[],$3::bigint[],$4::bigint[],$5::smallint[],$6::text[],
       $7::timestamptz[],$8::real[],$9::text[],$10::text[],$11::text[],$12::text[]
     )`,
    [
      rows.map((row) => row.eventId), rows.map((row) => row.storeId),
      rows.map((row) => row.userId), rows.map((row) => row.productId),
      rows.map((row) => row.persona), rows.map((row) => row.eventType),
      rows.map((row) => row.eventTs), rows.map((row) => row.weight),
      rows.map((row) => row.sessionId), rows.map((row) => row.eventOrigin),
      rows.map((row) => row.cohortId), rows.map((row) => row.runId)
    ]
  );
}

async function seedMlEvents({
  client, spec, runId, catalogHash, specHash, products, coldProducts, affinityModel
}) {
  const random = mulberry32(affinityModel ? spec.seed + 17 : spec.seed);
  const coldSet = new Set(coldProducts);
  const warmProducts = products
    .map((product) => Number(product.product_id))
    .filter((id) => !coldSet.has(id));
  const users = Array.from({ length: spec.num_users }, (_, index) => index + 1);
  if (
    spec.generator_version !== '5.0.0'
    || spec.schema_version !== '3.0.0'
    || spec.persona_distribution.length !== 8
    || Math.abs(spec.persona_distribution.reduce((sum, value) => sum + value, 0) - 1) > 1e-9
  ) throw new Error('benchmark v5 persona/generator contract is invalid');
  if (warmProducts.length !== spec.num_products - spec.num_cold_products) {
    throw new Error(`warm catalog count mismatch: ${warmProducts.length}`);
  }
  if (!affinityModel || !affinityModel.bundleTemplates) {
    throw new Error('v5 event generation requires one shared affinity model');
  }
  const model = affinityModel;
  const { personaByUser, affinityByUser, preferredProducts, productMetadata, categoryPersona } = model;

  const validationSize = spec.semantic_traps.length * spec.semantic_validation_users_per_trap;
  const testSize = spec.semantic_traps.length * spec.semantic_test_users_per_trap;
  const validationCohort = buildHeldoutCohort(
    spec, spec.semantic_validation_users_per_trap, spec.num_users - validationSize - testSize + 1
  );
  const testCohort = buildHeldoutCohort(
    spec, spec.semantic_test_users_per_trap, spec.num_users - testSize + 1
  );
  const warmByCategory = new Map();
  products.forEach((product) => {
    const id = Number(product.product_id);
    if (coldSet.has(id)) return;
    const category = Number(product.category_id);
    if (!warmByCategory.has(category)) warmByCategory.set(category, []);
    warmByCategory.get(category).push(id);
  });
  const productById = new Map(products.map((product) => [Number(product.product_id), product]));
  const coldCohort = coldProducts.map((target, index) => {
    const category = Number(productById.get(target).category_id);
    const anchors = warmByCategory.get(category);
    return {
      userId: 2001 + index,
      anchor: anchors[index % anchors.length],
      target,
      trapId: 0,
      reservedTargets: new Set([target])
    };
  });
  const blockedByUser = new Map();
  [...validationCohort, ...testCohort, ...coldCohort].forEach((row) => {
    if (!blockedByUser.has(row.userId)) blockedByUser.set(row.userId, new Set());
    row.reservedTargets.forEach((target) => blockedByUser.get(row.userId).add(target));
  });
  const seenByUser = new Map(users.map((userId) => [userId, new Set()]));
  const lastPurchaseByUser = new Map();
  const semanticTrain = semanticTrainingRows(spec, runId, personaByUser);
  const trainValidationAnchors = cohortRows(
    validationCohort, runId, 'train', 'anchor', personaByUser, 'semantic_trap'
  );
  const valValidationTargets = cohortRows(
    validationCohort, runId, 'val', 'target', personaByUser, 'semantic_trap'
  );
  const valColdAnchors = cohortRows(
    coldCohort, runId, 'val', 'anchor', personaByUser, 'cold_start'
  );
  const valTestAnchors = cohortRows(
    testCohort, runId, 'val', 'anchor', personaByUser, 'semantic_trap'
  );
  const testColdTargets = cohortRows(
    coldCohort, runId, 'test', 'target', personaByUser, 'cold_start'
  );
  const testSemanticTargets = cohortRows(
    testCohort, runId, 'test', 'target', personaByUser, 'semantic_trap'
  );
  const definitions = [
    {
      split: 'train', count: spec.split_counts.train,
      start: spec.cutoffs.train_start, end: spec.cutoffs.train_end,
      before: semanticTrain, after: trainValidationAnchors
    },
    {
      split: 'val', count: spec.split_counts.val,
      start: spec.cutoffs.val_start, end: spec.cutoffs.val_end,
      before: valValidationTargets, after: [...valColdAnchors, ...valTestAnchors]
    },
    {
      split: 'test', count: spec.split_counts.test,
      start: spec.cutoffs.test_start, end: spec.cutoffs.test_end,
      before: [...testColdTargets, ...testSemanticTargets], after: []
    }
  ];

  await client.query('BEGIN');
  try {
    await client.query('SET TRANSACTION READ WRITE');
    await client.query("SET LOCAL work_mem='256MB'");
    await client.query("SET LOCAL statement_timeout='20min'");
    await client.query("SET LOCAL statement_timeout='10min'");
    const existing = await client.query(
      `SELECT count(*)::int AS count FROM ml_interaction_event_v1
       WHERE store_id=$1 AND benchmark_run_id=$2`,
      [spec.store_id, runId]
    );
    if (existing.rows[0].count !== 0) {
      throw new Error(`immutable benchmark events already exist for ${runId}`);
    }
    await client.query(
      `INSERT INTO ml_benchmark_run_v1
        (benchmark_run_id,store_id,seed,status,catalog_sha256,benchmark_spec_sha256,
         expected_event_count,split_boundaries)
       VALUES ($1,$2,$3,'staging',$4,$5,$6,$7::jsonb)`,
      [runId, spec.store_id, spec.seed, catalogHash, specHash, spec.num_events, JSON.stringify(spec.cutoffs)]
    );
    for (const definition of definitions) {
      const organicCount = definition.count - definition.before.length - definition.after.length;
      if (organicCount <= spec.num_users * spec.session_min_events) {
        throw new Error(`${definition.split} organic quota is too small for user coverage`);
      }
      const organic = buildOrganicRows({
        split: definition.split,
        count: organicCount,
        runId,
        users,
        warmProducts,
        preferredProducts,
        personaByUser,
        affinityByUser,
        productMetadata,
        categoryPersona,
        blockedByUser,
        seenByUser,
        lastPurchaseByUser,
        bundleNeighbors: model.bundleTemplates.neighborsByProduct,
        random,
        spec
      });
      const rows = [...definition.before, ...organic, ...definition.after];
      if (rows.length !== definition.count) throw new Error(`${definition.split} count mismatch`);
      for (let offset = 0; offset < rows.length; offset += 5000) {
        const batch = rows.slice(offset, offset + 5000).map((row, batchOffset) => {
          const index = offset + batchOffset;
          return {
            ...row,
            eventId: `${runId}:${definition.split}:${String(index).padStart(9, '0')}`,
            storeId: spec.store_id,
            eventTs: timestampAt(index, definition.count, definition.start, definition.end),
            weight: row.eventType === 'purchase' ? 1 : 0.5,
            runId
          };
        });
        await insertBatch(client, batch);
      }
    }

    const validation = await client.query(
      `SELECT count(*)::int AS events,count(DISTINCT user_id)::int AS users,
              count(DISTINCT product_id)::int AS products,
              count(*) FILTER (WHERE session_id IS NULL OR event_origin IS NULL)::int AS invalid_contract
       FROM ml_interaction_event_v1 WHERE store_id=$1 AND benchmark_run_id=$2`,
      [spec.store_id, runId]
    );
    const counts = validation.rows[0];
    if (
      counts.events !== spec.num_events || counts.users !== spec.num_users
      || counts.products !== spec.num_products || counts.invalid_contract !== 0
    ) throw new Error(`event staging validation failed: ${JSON.stringify(counts)}`);
    const organicQuality = await client.query(
      `WITH session_products AS MATERIALIZED (
         SELECT user_id,product_id,session_id,
                count(*) FILTER (WHERE event_type='purchase') AS purchases,
                min(event_ts) FILTER (WHERE event_type='view') AS first_view_ts,
                min(event_ts) FILTER (WHERE event_type='purchase') AS first_purchase_ts
         FROM ml_interaction_event_v1
         WHERE store_id=$1 AND benchmark_run_id=$2 AND event_origin='organic'
         GROUP BY user_id,product_id,session_id
       )
       SELECT coalesce(sum(purchases),0)::int AS purchases,
              coalesce(sum(purchases) FILTER (
                WHERE first_view_ts<first_purchase_ts
              ),0)::int AS purchases_after_view
       FROM session_products`,
      [spec.store_id, runId]
    );
    const quality = organicQuality.rows[0];
    if (
      !quality.purchases
      || quality.purchases_after_view / quality.purchases < spec.minimum_purchase_prior_view_fraction
    ) throw new Error(`organic conversion quality failed: ${JSON.stringify(quality)}`);
    const funnelLift = await client.query(
      `WITH pairs AS (
         SELECT user_id,product_id,
                bool_or(event_type='view') AS viewed,
                bool_or(event_type='purchase') AS purchased
         FROM ml_interaction_event_v1
         WHERE store_id=$1 AND benchmark_run_id=$2 AND event_origin='organic'
         GROUP BY user_id,product_id
       )
       SELECT count(*) FILTER (WHERE viewed)::int AS viewed_pairs,
              count(*) FILTER (WHERE viewed AND purchased)::int AS converted_pairs,
              count(*) FILTER (WHERE purchased)::int AS purchase_pairs
       FROM pairs`,
      [spec.store_id, runId]
    );
    const funnel = funnelLift.rows[0];
    const conversionRate = funnel.converted_pairs / Math.max(1, funnel.viewed_pairs);
    const randomPurchaseRate = funnel.purchase_pairs
      / (spec.num_users * (spec.num_products - spec.num_cold_products));
    const viewPurchaseLift = conversionRate / Math.max(Number.EPSILON, randomPurchaseRate);
    if (viewPurchaseLift < 2) {
      throw new Error(`organic view-to-purchase lift ${viewPurchaseLift} is below 2`);
    }
    const novelCoverage = await client.query(
      `WITH pair_summary AS MATERIALIZED (
         SELECT user_id,product_id,min(event_ts) AS first_event_ts,
                bool_or(event_type='purchase' AND event_ts BETWEEN $3 AND $4)
                  AS has_val_purchase,
                bool_or(event_type='purchase' AND event_ts BETWEEN $6 AND $7)
                  AS has_test_purchase
         FROM ml_interaction_event_v1
         WHERE store_id=$1 AND benchmark_run_id=$2 AND event_origin='organic'
         GROUP BY user_id,product_id
       )
       SELECT count(DISTINCT user_id) FILTER (
                WHERE has_val_purchase AND first_event_ts>$5
              )::int AS val_users,
              count(DISTINCT user_id) FILTER (
                WHERE has_test_purchase AND first_event_ts>$4
              )::int AS test_users
       FROM pair_summary`,
      [
        spec.store_id, runId, spec.cutoffs.val_start, spec.cutoffs.val_end,
        spec.cutoffs.train_end, spec.cutoffs.test_start, spec.cutoffs.test_end
      ]
    );
    const novel = novelCoverage.rows[0];
    if (
      novel.val_users < spec.minimum_organic_novel_purchase_users
      || novel.test_users < spec.minimum_organic_novel_purchase_users
    ) throw new Error(`organic novel-purchase coverage failed: ${JSON.stringify(novel)}`);
    const coldValidation = await client.query(
      `SELECT count(DISTINCT product_id)::int AS cold_count,
              count(*) FILTER (WHERE event_type<>'purchase' OR event_origin<>'cold_start')::int AS invalid
       FROM ml_interaction_event_v1
       WHERE store_id=$1 AND benchmark_run_id=$2 AND product_id=ANY($3::bigint[])`,
      [spec.store_id, runId, coldProducts]
    );
    if (
      coldValidation.rows[0].cold_count !== spec.num_cold_products
      || coldValidation.rows[0].invalid !== 0
    ) throw new Error(`cold event validation failed: ${JSON.stringify(coldValidation.rows[0])}`);
    await validateHeldoutCohort(client, {
      runId, storeId: spec.store_id, cohort: validationCohort,
      historyEnd: spec.cutoffs.train_end, targetStart: spec.cutoffs.val_start,
      targetEnd: spec.cutoffs.val_end, label: 'validation'
    });
    await validateHeldoutCohort(client, {
      runId, storeId: spec.store_id, cohort: testCohort,
      historyEnd: spec.cutoffs.val_end, targetStart: spec.cutoffs.test_start,
      targetEnd: spec.cutoffs.test_end, label: 'test'
    });
    await validateHeldoutCohort(client, {
      runId, storeId: spec.store_id, cohort: coldCohort,
      historyEnd: spec.cutoffs.val_end, targetStart: spec.cutoffs.test_start,
      targetEnd: spec.cutoffs.test_end, label: 'cold-start'
    });
    await client.query(
      `INSERT INTO ml_benchmark_item_partition_v1
        (benchmark_run_id,store_id,product_id,partition,seed,catalog_sha256,benchmark_spec_sha256)
       SELECT $1,$2,value,CASE WHEN value=ANY($3::bigint[]) THEN 'cold' ELSE 'warm' END,$4,$5,$6
       FROM unnest($7::bigint[]) value`,
      [
        runId, spec.store_id, coldProducts, spec.seed, catalogHash, specHash,
        products.map((product) => Number(product.product_id))
      ]
    );
    await client.query(
      'ALTER TABLE ml_interaction_event_v1 VALIDATE CONSTRAINT ml_interaction_event_type_v1_check'
    );
    await client.query(
      'ALTER TABLE ml_interaction_event_v1 VALIDATE CONSTRAINT ml_interaction_event_origin_v1_check'
    );
    await client.query('ALTER TABLE ml_interaction_event_v1 ALTER COLUMN benchmark_run_id SET NOT NULL');
    await client.query('ALTER TABLE ml_interaction_event_v1 ALTER COLUMN session_id SET NOT NULL');
    await client.query('ALTER TABLE ml_interaction_event_v1 ALTER COLUMN event_origin SET NOT NULL');
    await client.query('COMMIT');
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  }
}

module.exports = {
  buildOrganicRows,
  conversionProbability,
  seedMlEvents,
  timestampAt
};
