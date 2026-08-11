'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const spec = require('../benchmark-spec-v5.json');
const { mulberry32 } = require('../benchmark-lib');
const {
  buildPersonaAssignments,
  buildUserAffinities,
  buildOrganicBundleTemplates
} = require('../benchmark-affinity');

function fixture() {
  const products = Array.from({ length: 5200 }, (_, index) => ({
    product_id: index + 1,
    category_id: index % 40,
    name: `product-${index + 1}`,
    unit_price: 10 + (index % 100),
    vendor: `vendor-${index % 20}`
  }));
  const users = Array.from({ length: spec.num_users }, (_, index) => index + 1);
  const coldProducts = products.slice(-spec.num_cold_products).map((product) => product.product_id);
  const warmProducts = products.slice(0, -spec.num_cold_products).map((product) => product.product_id);
  const personaByUser = buildPersonaAssignments(users, spec.persona_distribution, mulberry32(spec.seed));
  const affinity = buildUserAffinities(products, warmProducts, users, personaByUser, 8);
  const bundleTemplates = buildOrganicBundleTemplates({
    products,
    warmProducts,
    fixtureProducts: spec.semantic_traps.flatMap((trap) => [trap.anchor, ...trap.targets]),
    personaByUser,
    affinityByUser: affinity.affinityByUser,
    preferredProducts: affinity.preferredProducts,
    spec
  });
  return { products, users, coldProducts, personaByUser, ...affinity, bundleTemplates };
}

test('v5 affinity model is deterministic and covers all users', () => {
  const left = fixture();
  const right = fixture();
  assert.deepEqual([...left.personaByUser], [...right.personaByUser]);
  assert.equal(left.preferredProducts.size, spec.num_users);
  assert.equal(left.bundleTemplates.templates.length, spec.organic_bundle_template_count);
  assert.ok(left.bundleTemplates.distinctOrganicProducts >= spec.minimum_distinct_organic_rule_items);
  assert.deepEqual(left.bundleTemplates.templates, right.bundleTemplates.templates);
  assert.throws(() => left.personaByUser.set(1, 7), TypeError);
  assert.throws(() => left.affinityByUser.set(1, {}), TypeError);
  assert.throws(() => left.preferredProducts.set(1, []), TypeError);
  assert.throws(() => left.bundleTemplates.neighborsByProduct.set(1, []), TypeError);
  assert.equal(Object.isFrozen(left.affinityByUser.get(1)), true);
  assert.equal(Object.isFrozen(left.preferredProducts.get(1)), true);
  for (const template of left.bundleTemplates.templates) {
    const aligned = new Set();
    for (const [userId, persona] of left.personaByUser) {
      if (persona !== template.persona) continue;
      left.preferredProducts.get(userId).forEach((productId) => aligned.add(productId));
    }
    assert.ok(template.productIds.every((productId) => aligned.has(productId)));
    for (const productId of template.productIds) {
      const neighbors = left.bundleTemplates.neighborsByProduct.get(productId);
      assert.ok(neighbors.length >= template.productIds.length - 1);
      assert.ok(template.productIds.every(
        (candidate) => candidate === productId || neighbors.includes(candidate)
      ));
    }
  }
});
