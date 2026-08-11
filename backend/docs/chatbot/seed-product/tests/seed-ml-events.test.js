'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const spec = require('../benchmark-spec-v4.json');
const { buildOrganicRows, seedMlEvents } = require('../seed-ml-events');

test('organic validation purchase follows an unseen bundle neighbor when selected', () => {
  const lastPurchaseByUser = new Map([[1, 10]]);
  const rows = buildOrganicRows({
    split: 'val',
    count: 2,
    runId: 'fixture',
    users: [1],
    warmProducts: [10, 11, 12],
    preferredProducts: new Map([[1, [12]]]),
    personaByUser: new Map([[1, 0]]),
    affinityByUser: new Map([[1, { categoryPersona: 0, vendor: 'v', priceBand: 0 }]]),
    productMetadata: new Map([
      [10, { category: 1, vendor: 'v', priceBand: 0, popularity: 0.5 }],
      [11, { category: 1, vendor: 'v', priceBand: 0, popularity: 0.5 }],
      [12, { category: 1, vendor: 'v', priceBand: 0, popularity: 0.5 }]
    ]),
    categoryPersona: new Map([[1, 0]]),
    blockedByUser: new Map([[1, new Set()]]),
    seenByUser: new Map([[1, new Set([10])]]),
    lastPurchaseByUser,
    bundleNeighbors: new Map([[10, [11]]]),
    random: () => 0.5,
    spec: {
      session_min_events: 2,
      session_max_events: 2,
      split_preference_probability: { val: 1 },
      organic_rule_transition_probability: 1,
      session_purchase_probability: 1,
      conversion_affinity_weight: 0,
      conversion_popularity_weight: 0,
      conversion_price_weight: 0
    }
  });

  assert.deepEqual(rows.map((row) => row.productId), [11, 11]);
  assert.equal(rows.at(-1).eventType, 'purchase');
  assert.equal(lastPurchaseByUser.get(1), 11);
});

test('v4 event seeding rejects a missing shared affinity model', async () => {
  const products = Array.from({ length: spec.num_products }, (_, index) => ({
    product_id: index + 1
  }));
  const coldProducts = products
    .slice(-spec.num_cold_products)
    .map((product) => product.product_id);

  await assert.rejects(
    seedMlEvents({
      client: null,
      spec,
      runId: 'fixture',
      catalogHash: 'a'.repeat(64),
      specHash: 'b'.repeat(64),
      products,
      coldProducts,
      affinityModel: undefined
    }),
    /requires one shared affinity model/
  );
});
