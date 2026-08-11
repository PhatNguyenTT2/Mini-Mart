'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const spec = require('../benchmark-spec-v5.json');
const { generateOrderPlan, seedOrders } = require('../mock-orders');
const { buildPersonaAssignments, buildUserAffinities, buildOrganicBundleTemplates } = require('../benchmark-affinity');
const { mulberry32 } = require('../benchmark-lib');

function model() {
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
    categoryPersona: affinity.categoryPersona,
    preferredProducts: affinity.preferredProducts,
    spec
  });
  return { products, users, coldProducts, affinityModel: { personaByUser, ...affinity, bundleTemplates } };
}

test('v5 order plan has exact organic/trap split and no organic fixture leakage', () => {
  const fixture = model();
  const plan = generateOrderPlan({ spec, ...fixture });
  assert.equal(plan.length, spec.num_orders);
  assert.equal(plan.filter((order) => order.kind === 'organic').length, spec.organic_order_count);
  assert.equal(plan.filter((order) => order.kind === 'semantic_trap').length, spec.semantic_order_count);
  for (const trap of spec.semantic_traps) {
    const count = plan.filter(
      (order) => order.kind === 'semantic_trap' && order.trapId === trap.trap_id
    ).length;
    assert.ok(count >= spec.minimum_semantic_copurchase_count);
  }
  const cold = new Set(fixture.coldProducts);
  const traps = new Set(spec.semantic_traps.flatMap((trap) => [trap.anchor, ...trap.targets]));
  for (const order of plan.filter((candidate) => candidate.kind === 'organic')) {
    assert.equal(order.items.some((item) => cold.has(item.productId) || traps.has(item.productId)), false);
  }
  const repeated = new Map();
  const userCounts = new Map();
  const productById = new Map(fixture.products.map((product) => [product.product_id, product]));
  for (const order of plan.filter((candidate) => candidate.kind === 'organic')) {
    repeated.set(order.templateId, (repeated.get(order.templateId) || 0) + 1);
    userCounts.set(order.userId, (userCounts.get(order.userId) || 0) + 1);
    const persona = fixture.affinityModel.personaByUser.get(order.userId);
    for (const item of order.items) {
      assert.equal(
        fixture.affinityModel.categoryPersona.get(productById.get(item.productId).category_id),
        persona
      );
    }
  }
  assert.ok([...repeated.values()].every((count) => count === spec.organic_bundle_repeats));
  assert.equal(userCounts.size, spec.num_users);
  assert.ok([...userCounts.values()].every((count) => count >= 2 && count <= 3));
});

test('order seeding rejects an existing run without deleting any lineage', async () => {
  const fixture = model();
  const statements = [];
  const client = {
    async query(sql) {
      statements.push(sql);
      if (sql.includes('SELECT count(*)::int AS count FROM sale_order')) {
        return { rows: [{ count: 1 }] };
      }
      return { rows: [] };
    }
  };

  await assert.rejects(
    seedOrders({ client, spec, runId: 'immutable-run', ...fixture }),
    /immutable benchmark orders already exist/
  );
  assert.equal(statements.some((statement) => /^\s*DELETE\s/i.test(statement)), false);
});
