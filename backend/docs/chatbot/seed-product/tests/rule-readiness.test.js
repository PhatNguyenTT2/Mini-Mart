'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const spec = require('../benchmark-spec-v5.json');
const { generateOrderPlan } = require('../mock-orders');

test('v5 order readiness rejects an invalid organic/trap allocation', () => {
  assert.throws(
    () => generateOrderPlan({
      spec: { ...spec, organic_order_count: spec.organic_order_count - 1 },
      users: [1],
      products: [],
      coldProducts: [],
      affinityModel: { bundleTemplates: { templates: [] }, personaByUser: new Map() }
    }),
    /organic and semantic order counts/
  );
});
