'use strict';

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const {
  buildFamilyView,
  loadFamilyViewSpec,
  parseCatalogSeedSql
} = require('../catalog-family-view-v5.1');

const seedRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(seedRoot, '..', '..', '..', '..');
const specPath = path.join(seedRoot, 'benchmark-spec-v5.1.json');
const catalogPath = path.join(repoRoot, 'backend', 'docs', 'chatbot', 'catalog-bootstrap', 'seed-5000.sql');

test('v5.1 freezes the current 5,200-SKU catalog instead of the historical seed', () => {
  const spec = loadFamilyViewSpec(specPath);
  assert.equal(spec.num_products, 5200);
  assert.equal(spec.num_product_families, 77);
  assert.equal(spec.behavior_artifact_policy, 'REUSE_PARENT_V5_EXACT_BYTES_BY_HASH');
  assert.equal(spec.scientific_scope.test_set_opened, false);
  assert.equal(spec.scientific_scope.cold_item_scope, 'DIAGNOSTIC_NOT_PRIMARY');

  const seedBytes = fs.readFileSync(catalogPath);
  assert.equal(
    crypto.createHash('sha256').update(seedBytes).digest('hex'),
    spec.catalog_seed_sha256
  );
});

test('all 5,200 committed SKU rows resolve deterministically to 77 clean family anchors', () => {
  const spec = loadFamilyViewSpec(specPath);
  const { products } = parseCatalogSeedSql(fs.readFileSync(catalogPath, 'utf8'));
  const view = buildFamilyView(products, spec);

  assert.equal(products.length, 5200);
  assert.equal(view.length, 5200);
  assert.equal(new Set(view.map((row) => row.family_id)).size, 77);
  assert.equal(view.find((row) => row.raw_item_id === 2055).family_id, 2015);
  assert.equal(view.find((row) => row.raw_item_id === 2062).family_id, 1013);
  assert.equal(view.find((row) => row.raw_item_id === 2081).family_id, 1001);
  assert.equal(
    view.find((row) => row.raw_item_id === 2055).model_text,
    'Khoai tây củ 1kg. Danh mục: Củ, quả.'
  );
  assert.equal('raw_name' in view[0], false);
  assert.equal('raw_price' in view[0], false);
  assert.ok(view.every((row) => row.price_bucket >= 0 && row.price_bucket <= 3));
});

test('family mapping fails closed for an unknown category/vendor surface', () => {
  const spec = loadFamilyViewSpec(specPath);
  const { products } = parseCatalogSeedSql(fs.readFileSync(catalogPath, 'utf8'));
  products.find((row) => row.raw_item_id === 2055).vendor = 'UNREGISTERED';

  assert.throws(() => buildFamilyView(products, spec), /has no family anchor/);
});

test('ambiguous family mapping rejects a product without one discriminator', () => {
  const spec = loadFamilyViewSpec(specPath);
  const { products } = parseCatalogSeedSql(fs.readFileSync(catalogPath, 'utf8'));
  const product = products.find((row) => row.raw_item_id === 2055);
  product.category = 'Cá, hải sản';
  product.vendor = 'BHX Fresh';
  product.name = 'Sản phẩm không xác định';

  assert.throws(() => buildFamilyView(products, spec), /does not resolve to one ambiguous family/);
});
