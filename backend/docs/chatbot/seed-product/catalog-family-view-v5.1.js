'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const SOURCE_ITEM_FIELDS = Object.freeze([
  'raw_item_id',
  'name',
  'category',
  'vendor',
  'price',
  'partition'
]);

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.keys(value).sort().map((key) => [key, canonicalize(value[key])])
    );
  }
  if (typeof value === 'number' && !Number.isFinite(value)) {
    throw new Error('non-finite values cannot be canonicalized');
  }
  return value;
}

function canonicalJson(value) {
  return JSON.stringify(canonicalize(value));
}

function sha256(payload) {
  return crypto.createHash('sha256').update(payload).digest('hex');
}

function sha256File(filePath) {
  return sha256(fs.readFileSync(filePath));
}

function exactKeys(value, keys, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`${label} must be an object`);
  }
  const actual = Object.keys(value).sort();
  const expected = [...keys].sort();
  if (canonicalJson(actual) !== canonicalJson(expected)) {
    throw new Error(`${label} fields do not match the v5.1 contract`);
  }
}

function positiveInteger(value, label) {
  if (!Number.isSafeInteger(value) || value <= 0) {
    throw new Error(`${label} must be a positive integer`);
  }
  return value;
}

function nonempty(value, label) {
  if (typeof value !== 'string' || !value.trim()) {
    throw new Error(`${label} must be a non-empty string`);
  }
  return value;
}

function normalizeText(value) {
  return String(value)
    .normalize('NFKC')
    .toLocaleLowerCase('vi')
    .replace(/[’']/gu, '')
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .trim()
    .replace(/\s+/gu, ' ');
}

function groupKey(category, vendor) {
  return `${normalizeText(category)}\u001f${normalizeText(vendor)}`;
}

function expandAnchorIds(ranges) {
  const ids = [];
  for (const range of ranges) {
    exactKeys(range, ['start', 'end'], 'family_anchor_range');
    const start = positiveInteger(range.start, 'family_anchor_range.start');
    const end = positiveInteger(range.end, 'family_anchor_range.end');
    if (end < start) throw new Error('family anchor range is reversed');
    for (let id = start; id <= end; id += 1) ids.push(id);
  }
  if (new Set(ids).size !== ids.length) throw new Error('family anchor ranges overlap');
  return ids;
}

function validateSpec(spec) {
  exactKeys(spec, [
    'schema_version',
    'dataset_version',
    'generator_version',
    'parent_generator_version',
    'seed',
    'num_users',
    'num_products',
    'num_product_families',
    'num_cold_products',
    'num_events',
    'num_orders',
    'split_counts',
    'catalog_seed_path',
    'catalog_seed_sha256',
    'parent_source_items_sha256',
    'parent_dataset_sha256',
    'parent_dataset_manifest_sha256',
    'behavior_artifact_policy',
    'family_anchor_ranges',
    'ambiguous_family_groups',
    'model_feature_policy',
    'scientific_scope'
  ], 'v5.1 spec');
  if (
    spec.schema_version !== 'benchmark-dataset-amendment/1.0'
    || spec.dataset_version !== 'v5.1'
    || spec.generator_version !== '5.1.0'
    || spec.parent_generator_version !== '5.0.0'
  ) throw new Error('unsupported v5.1 dataset amendment version');
  for (const field of [
    'seed', 'num_users', 'num_products', 'num_product_families', 'num_cold_products',
    'num_events', 'num_orders'
  ]) positiveInteger(spec[field], `v5.1 spec.${field}`);
  if (spec.num_products !== 5200) throw new Error('v5.1 must preserve all 5,200 SKUs');
  if (spec.behavior_artifact_policy !== 'REUSE_PARENT_V5_EXACT_BYTES_BY_HASH') {
    throw new Error('v5.1 may not silently regenerate parent behavior');
  }
  for (const field of [
    'catalog_seed_sha256', 'parent_source_items_sha256', 'parent_dataset_sha256',
    'parent_dataset_manifest_sha256'
  ]) {
    if (!/^[0-9a-f]{64}$/u.test(spec[field])) throw new Error(`${field} must be a SHA-256`);
  }
  const anchorIds = expandAnchorIds(spec.family_anchor_ranges);
  if (anchorIds.length !== spec.num_product_families) {
    throw new Error('family anchor count does not match num_product_families');
  }
  if (!Array.isArray(spec.ambiguous_family_groups)) {
    throw new Error('ambiguous_family_groups must be an array');
  }
  for (const [index, group] of spec.ambiguous_family_groups.entries()) {
    exactKeys(group, ['category', 'vendor', 'rules'], `ambiguous_family_groups[${index}]`);
    nonempty(group.category, `ambiguous_family_groups[${index}].category`);
    nonempty(group.vendor, `ambiguous_family_groups[${index}].vendor`);
    if (!Array.isArray(group.rules) || group.rules.length < 2) {
      throw new Error(`ambiguous_family_groups[${index}].rules must contain at least two rules`);
    }
    for (const [ruleIndex, rule] of group.rules.entries()) {
      exactKeys(rule, ['family_id', 'required_phrase'], `ambiguous rule ${index}:${ruleIndex}`);
      if (!anchorIds.includes(positiveInteger(rule.family_id, 'ambiguous family_id'))) {
        throw new Error('ambiguous rule references a non-anchor family');
      }
      nonempty(rule.required_phrase, 'ambiguous required_phrase');
    }
  }
  if (spec.scientific_scope.test_set_opened !== false) {
    throw new Error('v5.1 design freeze cannot open TEST');
  }
  return spec;
}

function loadFamilyViewSpec(specPath) {
  const payload = fs.readFileSync(specPath);
  if (payload.subarray(0, 3).equals(Buffer.from([0xef, 0xbb, 0xbf]))) {
    throw new Error('UTF-8 BOM is forbidden in the v5.1 spec');
  }
  return Object.freeze(validateSpec(JSON.parse(payload.toString('utf8'))));
}

function parseSourceItemsJsonl(itemsPath) {
  const payload = fs.readFileSync(itemsPath);
  if (payload.subarray(0, 3).equals(Buffer.from([0xef, 0xbb, 0xbf]))) {
    throw new Error('UTF-8 BOM is forbidden in source items');
  }
  return payload.toString('utf8').split('\n').filter((line, index, lines) => {
    if (!line && index === lines.length - 1) return false;
    if (!line.trim()) throw new Error(`blank JSONL row at line ${index + 1}`);
    return true;
  }).map((line, index) => {
    let row;
    try {
      row = JSON.parse(line);
    } catch (error) {
      throw new Error(`invalid source item JSON at line ${index + 1}: ${error.message}`);
    }
    exactKeys(row, SOURCE_ITEM_FIELDS, `source item line ${index + 1}`);
    return row;
  });
}

function unescapeSqlText(value) {
  return value.replaceAll("''", "'");
}

function parseCatalogSeedSql(sql) {
  const categoryStart = sql.indexOf('INSERT INTO category');
  const productStart = sql.indexOf('INSERT INTO product');
  if (categoryStart < 0 || productStart < 0 || productStart <= categoryStart) {
    throw new Error('catalog seed lacks ordered category/product INSERT sections');
  }
  const categorySection = sql.slice(categoryStart, productStart);
  const productSection = sql.slice(productStart);
  const categoryPattern = /^\s*\((\d+),\s*(?:NULL|\d+),\s*'((?:''|[^'])*)',\s*(?:NULL|'(?:''|[^'])*'),\s*\d+\)[,;]\s*$/u;
  const productPattern = /^\s*\((\d+),\s*(\d+),\s*'((?:''|[^'])*)',\s*(\d+(?:\.\d+)?),\s*'((?:''|[^'])*)',\s*(?:NULL|'(?:''|[^'])*')\)[,;]\s*$/u;
  const categories = new Map();
  for (const line of categorySection.split(/\r?\n/u)) {
    const match = categoryPattern.exec(line);
    if (match) categories.set(Number(match[1]), unescapeSqlText(match[2]));
  }
  const products = [];
  for (const line of productSection.split(/\r?\n/u)) {
    const match = productPattern.exec(line);
    if (!match) continue;
    const category = categories.get(Number(match[2]));
    if (!category) throw new Error(`product ${match[1]} references an unknown category`);
    products.push({
      raw_item_id: Number(match[1]),
      name: unescapeSqlText(match[3]),
      category,
      vendor: unescapeSqlText(match[5]),
      price: Number(match[4]),
      partition: 'warm'
    });
  }
  if (!categories.size || !products.length) throw new Error('catalog seed parser found no rows');
  return { categories, products };
}

function quartileBoundaries(anchors) {
  const prices = anchors.map((row) => row.price).sort((left, right) => left - right);
  return [0.25, 0.5, 0.75].map(
    (quantile) => prices[Math.min(prices.length - 1, Math.floor(prices.length * quantile))]
  );
}

function buildFamilyView(sourceRows, rawSpec) {
  const spec = validateSpec(rawSpec);
  if (!Array.isArray(sourceRows) || sourceRows.length !== spec.num_products) {
    throw new Error(`source catalog must contain exactly ${spec.num_products} products`);
  }
  const byId = new Map();
  for (const [index, row] of sourceRows.entries()) {
    exactKeys(row, SOURCE_ITEM_FIELDS, `source item ${index}`);
    const id = positiveInteger(row.raw_item_id, `source item ${index}.raw_item_id`);
    if (byId.has(id)) throw new Error(`duplicate source item ID ${id}`);
    for (const field of ['name', 'category', 'vendor']) nonempty(row[field], `item ${id}.${field}`);
    if (!Number.isFinite(row.price) || row.price < 0) throw new Error(`item ${id}.price is invalid`);
    if (!['warm', 'cold'].includes(row.partition)) throw new Error(`item ${id}.partition is invalid`);
    byId.set(id, row);
  }

  const anchorIds = expandAnchorIds(spec.family_anchor_ranges);
  const anchors = anchorIds.map((id) => {
    const row = byId.get(id);
    if (!row) throw new Error(`missing family anchor ${id}`);
    return row;
  });
  const anchorsByGroup = new Map();
  for (const anchor of anchors) {
    const key = groupKey(anchor.category, anchor.vendor);
    if (!anchorsByGroup.has(key)) anchorsByGroup.set(key, []);
    anchorsByGroup.get(key).push(anchor);
  }
  const ambiguityByGroup = new Map(
    spec.ambiguous_family_groups.map((group) => [groupKey(group.category, group.vendor), group])
  );
  for (const [key, groupAnchors] of anchorsByGroup) {
    if (groupAnchors.length > 1 && !ambiguityByGroup.has(key)) {
      throw new Error(`missing ambiguity rules for ${key}`);
    }
  }

  const boundaries = quartileBoundaries(anchors);
  const output = [...sourceRows].sort((left, right) => left.raw_item_id - right.raw_item_id).map((row) => {
    let anchor = byId.get(row.raw_item_id);
    if (!anchorIds.includes(row.raw_item_id)) {
      const key = groupKey(row.category, row.vendor);
      const candidates = anchorsByGroup.get(key) || [];
      if (candidates.length === 1) {
        [anchor] = candidates;
      } else if (candidates.length > 1) {
        const ambiguity = ambiguityByGroup.get(key);
        const normalizedName = normalizeText(row.name);
        const matches = ambiguity.rules.filter(
          (rule) => normalizedName.includes(normalizeText(rule.required_phrase))
        );
        if (matches.length !== 1) {
          throw new Error(`item ${row.raw_item_id} does not resolve to one ambiguous family`);
        }
        anchor = byId.get(matches[0].family_id);
        if (!candidates.some((candidate) => candidate.raw_item_id === anchor.raw_item_id)) {
          throw new Error(`item ${row.raw_item_id} ambiguity rule crosses its source group`);
        }
      } else {
        throw new Error(`item ${row.raw_item_id} has no family anchor for category/vendor`);
      }
    }
    const priceBucket = boundaries.filter((boundary) => anchor.price > boundary).length;
    return {
      raw_item_id: row.raw_item_id,
      family_id: anchor.raw_item_id,
      model_text: `${anchor.name}. Danh mục: ${anchor.category}.`,
      category: row.category,
      model_price: anchor.price,
      price_bucket: priceBucket,
      partition: row.partition,
      raw_item_sha256: sha256(`${canonicalJson(row)}\n`)
    };
  });
  const representedFamilies = new Set(output.map((row) => row.family_id));
  if (representedFamilies.size !== spec.num_product_families) {
    throw new Error('not every frozen family anchor is represented');
  }
  return output;
}

function buildFamilyViewArtifact(sourceRows, spec, sourceItemsSha256) {
  if (sourceItemsSha256 !== spec.parent_source_items_sha256) {
    throw new Error('source items hash does not match the frozen parent v5 artifact');
  }
  const rows = buildFamilyView(sourceRows, spec);
  const coldCount = rows.filter((row) => row.partition === 'cold').length;
  if (coldCount !== spec.num_cold_products) {
    throw new Error('cold partition count does not match the parent v5 contract');
  }
  const bytes = Buffer.from(rows.map((row) => canonicalJson(row)).join('\n') + '\n', 'utf8');
  const familyCounts = new Map();
  for (const row of rows) familyCounts.set(row.family_id, (familyCounts.get(row.family_id) || 0) + 1);
  const counts = [...familyCounts.values()];
  const manifest = {
    schema_version: 'catalog-family-view/1.0',
    dataset_version: spec.dataset_version,
    parent_dataset_sha256: spec.parent_dataset_sha256,
    parent_dataset_manifest_sha256: spec.parent_dataset_manifest_sha256,
    parent_source_items_sha256: sourceItemsSha256,
    policy_sha256: sha256(`${canonicalJson(spec)}\n`),
    catalog_family_view_sha256: sha256(bytes),
    num_products: rows.length,
    num_product_families: familyCounts.size,
    num_cold_products: coldCount,
    minimum_family_size: Math.min(...counts),
    maximum_family_size: Math.max(...counts),
    model_feature_policy: spec.model_feature_policy,
    scientific_scope: spec.scientific_scope,
    behavior_artifact_policy: spec.behavior_artifact_policy,
    test_set_opened: false,
    accepted_result_rows: 0
  };
  return { rows, bytes, manifest };
}

function writeFamilyView({ specPath, itemsPath, outputRoot }) {
  const spec = loadFamilyViewSpec(specPath);
  const sourceHash = sha256File(itemsPath);
  const sourceRows = parseSourceItemsJsonl(itemsPath);
  const artifact = buildFamilyViewArtifact(sourceRows, spec, sourceHash);
  const target = path.resolve(outputRoot);
  const staging = path.join(path.dirname(target), `.${path.basename(target)}.staging`);
  if (fs.existsSync(target) || fs.existsSync(staging)) {
    throw new Error('v5.1 output or staging root already exists');
  }
  fs.mkdirSync(staging, { recursive: false });
  try {
    fs.writeFileSync(path.join(staging, 'catalog_family_view.jsonl'), artifact.bytes, { flag: 'wx' });
    fs.writeFileSync(
      path.join(staging, 'catalog_family_view_manifest.json'),
      `${canonicalJson(artifact.manifest)}\n`,
      { flag: 'wx' }
    );
    fs.renameSync(staging, target);
  } catch (error) {
    fs.rmSync(staging, { recursive: true, force: true });
    throw error;
  }
  return artifact.manifest;
}

function parseArguments(argv) {
  const values = new Map();
  let verifyOnly = false;
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === '--verify-only') {
      verifyOnly = true;
      continue;
    }
    if (!['--spec', '--items', '--output'].includes(argv[index]) || !argv[index + 1]) {
      throw new Error(`unsupported or incomplete argument: ${argv[index]}`);
    }
    values.set(argv[index], argv[index + 1]);
    index += 1;
  }
  if (!values.has('--spec') || !values.has('--items')) {
    throw new Error('--spec and --items are required');
  }
  if (!verifyOnly && !values.has('--output')) throw new Error('--output is required for materialization');
  return { verifyOnly, values };
}

function main(argv = process.argv.slice(2)) {
  const { verifyOnly, values } = parseArguments(argv);
  const spec = loadFamilyViewSpec(values.get('--spec'));
  const itemsPath = values.get('--items');
  const sourceHash = sha256File(itemsPath);
  const sourceRows = parseSourceItemsJsonl(itemsPath);
  const artifact = buildFamilyViewArtifact(sourceRows, spec, sourceHash);
  const manifest = verifyOnly
    ? artifact.manifest
    : writeFamilyView({ specPath: values.get('--spec'), itemsPath, outputRoot: values.get('--output') });
  process.stdout.write(`${canonicalJson({ status: 'PASS', mode: verifyOnly ? 'VERIFY_ONLY' : 'MATERIALIZED', ...manifest })}\n`);
  return 0;
}

if (require.main === module) {
  try {
    main();
  } catch (error) {
    process.stderr.write(`${error.stack || error.message}\n`);
    process.exitCode = 1;
  }
}

module.exports = {
  buildFamilyView,
  buildFamilyViewArtifact,
  canonicalJson,
  loadFamilyViewSpec,
  main,
  normalizeText,
  parseCatalogSeedSql,
  parseSourceItemsJsonl,
  sha256,
  sha256File,
  validateSpec,
  writeFamilyView
};
