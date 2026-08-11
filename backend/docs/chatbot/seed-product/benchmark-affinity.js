'use strict';

const { shuffle } = require('./benchmark-lib');

class ImmutableMap {
  #values;

  constructor(entries) {
    this.#values = new Map(entries);
    Object.freeze(this);
  }

  get size() { return this.#values.size; }
  get(key) { return this.#values.get(key); }
  has(key) { return this.#values.has(key); }
  entries() { return this.#values.entries(); }
  keys() { return this.#values.keys(); }
  values() { return this.#values.values(); }
  [Symbol.iterator]() { return this.#values[Symbol.iterator](); }
  forEach(callback, thisArg) {
    this.#values.forEach((value, key) => callback.call(thisArg, value, key, this));
  }
}

function buildPersonaAssignments(users, distribution, random) {
  if (!users.length || !distribution.length) throw new Error('persona inputs cannot be empty');
  const total = distribution.reduce((sum, value) => sum + value, 0);
  if (Math.abs(total - 1) > 1e-9) throw new Error('persona distribution must sum to one');
  const shuffledUsers = shuffle([...users], random);
  const assignments = new Map();
  let cursor = 0;
  distribution.forEach((probability, persona) => {
    const remaining = shuffledUsers.length - cursor;
    const count = persona === distribution.length - 1
      ? remaining
      : Math.min(remaining, Math.round(probability * users.length));
    shuffledUsers.slice(cursor, cursor + count).forEach((userId) => assignments.set(userId, persona));
    cursor += count;
  });
  if (assignments.size !== users.length) throw new Error('persona assignment did not cover all users');
  return new ImmutableMap(assignments);
}

function buildUserAffinities(products, warmProducts, users, personaByUser, personaCount = 8) {
  const warmSet = new Set(warmProducts);
  const warm = products.filter((product) => warmSet.has(Number(product.product_id)));
  if (!warm.length) throw new Error('cannot build affinity model without warm products');
  const vendors = [...new Set(warm.map((product) => String(product.vendor || 'unknown')))].sort();
  const prices = warm.map((product) => Number(product.unit_price)).sort((left, right) => left - right);
  const quartiles = [0.25, 0.5, 0.75].map(
    (quantile) => prices[Math.min(prices.length - 1, Math.floor(prices.length * quantile))]
  );
  const priceBand = (price) => quartiles.filter((boundary) => price > boundary).length;
  const categories = [...new Set(warm.map((product) => Number(product.category_id)))].sort(
    (left, right) => left - right
  );
  const categoryPersona = new Map(categories.map((category, index) => [category, index % personaCount]));
  const productMetadata = new Map();
  warm.forEach((product, popularityRank) => {
    productMetadata.set(Number(product.product_id), Object.freeze({
      category: Number(product.category_id),
      vendor: String(product.vendor || 'unknown'),
      priceBand: priceBand(Number(product.unit_price)),
      popularity: 1 - popularityRank / Math.max(1, warm.length - 1)
    }));
  });
  const affinityByUser = new Map();
  const preferredProducts = new Map();
  users.forEach((userId) => {
    const persona = personaByUser.get(userId);
    if (persona === undefined) throw new Error(`missing persona assignment for user ${userId}`);
    const affinity = Object.freeze({
      categoryPersona: persona,
      vendor: vendors[(userId * 2654435761) % vendors.length],
      priceBand: (userId * 17 + persona) % 4
    });
    affinityByUser.set(userId, affinity);
    const exact = warmProducts.filter((productId) => {
      const product = productMetadata.get(productId);
      return categoryPersona.get(product.category) === affinity.categoryPersona
        && product.vendor === affinity.vendor
        && product.priceBand === affinity.priceBand;
    });
    const categoryFallback = warmProducts.filter(
      (productId) => categoryPersona.get(productMetadata.get(productId).category)
        === affinity.categoryPersona
    );
    preferredProducts.set(userId, Object.freeze(exact.length ? exact : categoryFallback));
  });
  return Object.freeze({
    affinityByUser: new ImmutableMap(affinityByUser),
    preferredProducts: new ImmutableMap(preferredProducts),
    productMetadata: new ImmutableMap(productMetadata),
    categoryPersona: new ImmutableMap(categoryPersona)
  });
}

function buildOrganicBundleTemplates({
  products,
  warmProducts,
  fixtureProducts,
  personaByUser,
  affinityByUser,
  categoryPersona: sharedCategoryPersona,
  preferredProducts,
  spec
}) {
  const templateCount = Number(spec.organic_bundle_template_count || 0);
  const repeatCount = Number(spec.organic_bundle_repeats || 0);
  const minSize = Number(spec.organic_bundle_min_size || 3);
  const maxSize = Number(spec.organic_bundle_max_size || minSize);
  if (!templateCount || !repeatCount || minSize < 2 || maxSize < minSize) {
    throw new Error('organic bundle template contract is invalid');
  }
  const blocked = new Set(fixtureProducts);
  const warm = warmProducts.filter((productId) => !blocked.has(productId));
  const personaCount = Math.max(...personaByUser.values()) + 1;
  const productsByPersona = Array.from({ length: personaCount }, () => []);
  const metadata = new Map(products.map((product) => [Number(product.product_id), product]));
  const categoryPersona = sharedCategoryPersona || new ImmutableMap();
  for (const [productId, product] of metadata) {
    if (blocked.has(productId) || !warm.includes(productId)) continue;
    const resolvedPersona = categoryPersona.get(Number(product.category_id))
      ?? Number(product.category_id) % personaCount;
    productsByPersona[resolvedPersona].push(productId);
  }
  const usersByPersona = Array.from({ length: personaCount }, () => 0);
  const preferredByPersona = Array.from({ length: personaCount }, () => new Set());
  for (const [userId, persona] of personaByUser) {
    if (!affinityByUser.has(userId)) throw new Error(`missing affinity for user ${userId}`);
    const preferred = preferredProducts.get(userId);
    if (!preferred || !preferred.length) throw new Error(`missing preferred products for user ${userId}`);
    usersByPersona[persona] += 1;
    preferred.forEach((productId) => preferredByPersona[persona].add(productId));
  }
  const rawTemplateCounts = usersByPersona.map(
    (count) => (templateCount * count) / personaByUser.size
  );
  const templateCounts = rawTemplateCounts.map(Math.floor);
  let remainingTemplates = templateCount - templateCounts.reduce((sum, count) => sum + count, 0);
  const largestRemainders = rawTemplateCounts
    .map((value, persona) => ({ persona, remainder: value - Math.floor(value) }))
    .sort((left, right) => right.remainder - left.remainder || left.persona - right.persona);
  for (let index = 0; index < remainingTemplates; index += 1) {
    templateCounts[largestRemainders[index].persona] += 1;
  }
  const personaSequence = templateCounts.flatMap((count, persona) => Array(count).fill(persona));
  const personaTemplateOrdinals = Array(personaCount).fill(0);
  const templates = [];
  for (let index = 0; index < templateCount; index += 1) {
    const persona = personaSequence[index];
    const pool = productsByPersona[persona].filter(
      (productId) => preferredByPersona[persona].has(productId)
    );
    if (!pool.length) throw new Error(`persona ${persona} has no affinity-aligned bundle pool`);
    const size = minSize + (index % (maxSize - minSize + 1));
    const cycle = personaTemplateOrdinals[persona];
    personaTemplateOrdinals[persona] += 1;
    const selected = [];
    for (let offset = 0; selected.length < size && offset < pool.length * 2; offset += 1) {
      const productId = pool[(cycle * size + offset) % pool.length];
      if (!selected.includes(productId)) selected.push(productId);
    }
    if (selected.length < size) throw new Error(`cannot build organic template ${index}`);
    templates.push(Object.freeze({
      templateId: `organic-${String(index + 1).padStart(4, '0')}`,
      persona,
      productIds: Object.freeze(selected),
      repeatCount
    }));
  }
  const distinct = new Set(templates.flatMap((template) => template.productIds));
  const minimumDistinct = Number(spec.minimum_distinct_organic_rule_items || 0);
  if (distinct.size < minimumDistinct) {
    throw new Error(`organic templates cover ${distinct.size} products; expected ${minimumDistinct}`);
  }
  const neighborSets = new Map();
  for (const template of templates) {
    for (const source of template.productIds) {
      if (!neighborSets.has(source)) neighborSets.set(source, new Set());
      for (const target of template.productIds) {
        if (target !== source) neighborSets.get(source).add(target);
      }
    }
  }
  const neighborsByProduct = new ImmutableMap(
    [...neighborSets].map(([productId, neighbors]) => [
      productId,
      Object.freeze([...neighbors].sort((left, right) => left - right))
    ])
  );
  return Object.freeze({
    templates: Object.freeze(templates),
    distinctOrganicProducts: distinct.size,
    neighborsByProduct,
    categoryPersona,
    personaByUser,
    affinityByUser,
    preferredProducts
  });
}

module.exports = {
  ImmutableMap,
  buildPersonaAssignments,
  buildUserAffinities,
  buildOrganicBundleTemplates
};
