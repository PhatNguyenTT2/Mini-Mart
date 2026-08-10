const { Pool } = require('pg');
require('dotenv').config({ path: '../../../.env' });

const CATALOG_DB_URL = process.env.CATALOG_DATABASE_URL || 'postgresql://postgres.edilvszptbqhksmmennf:601235016138C39@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres';
const INVENTORY_DB_URL = process.env.INVENTORY_DATABASE_URL || 'postgresql://postgres.pulizqbqrgygdowrywst:601235016138C39@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres';

const catalogPool = new Pool({
  connectionString: CATALOG_DB_URL,
  ssl: { rejectUnauthorized: false }
});

const inventoryPool = new Pool({
  connectionString: INVENTORY_DB_URL,
  ssl: { rejectUnauthorized: false }
});

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

async function seedInventory() {
  console.log('🚀 Starting Bulk Inventory Seed Script (1:1 Batch-to-Item Structure)...');
  const storeId = 1;
  const startTime = Date.now();

  try {
    // 1. Fetch all products from Catalog DB
    console.log('📦 Fetching products from Catalog Database...');
    const catalogRes = await catalogPool.query(`
      SELECT id, name, unit_price 
      FROM product 
      ORDER BY id ASC
    `);

    const products = catalogRes.rows;
    console.log(`✅ Found ${products.length} products in Catalog DB.`);

    if (products.length === 0) {
      throw new Error('No products found in Catalog DB!');
    }

    const invClient = await inventoryPool.connect();

    try {
      await invClient.query('BEGIN');

      console.log('🧹 Cleaning up old inventory data...');
      await invClient.query('TRUNCATE inventory_movement CASCADE');
      await invClient.query('TRUNCATE inventory_item CASCADE');
      await invClient.query('TRUNCATE product_batch CASCADE');
      await invClient.query('TRUNCATE location CASCADE');
      await invClient.query('TRUNCATE warehouse_block CASCADE');

      // 2. Insert Warehouse Blocks
      console.log('🏗️ Inserting 6 Warehouse Blocks (3 Warehouse + 3 Store Shelves)...');
      const blocksData = [
        { id: 1, name: 'Kho chính A', type: 'warehouse', rows: 10, cols: 10, prefix: 'W-A' },
        { id: 2, name: 'Kho chính B', type: 'warehouse', rows: 10, cols: 10, prefix: 'W-B' },
        { id: 3, name: 'Kho chính C', type: 'warehouse', rows: 10, cols: 10, prefix: 'W-C' },
        { id: 4, name: 'Kệ trưng bày A', type: 'store_shelf', rows: 10, cols: 10, prefix: 'S-A' },
        { id: 5, name: 'Kệ trưng bày B', type: 'store_shelf', rows: 10, cols: 10, prefix: 'S-B' },
        { id: 6, name: 'Kệ trưng bày C', type: 'store_shelf', rows: 10, cols: 10, prefix: 'S-C' },
      ];

      for (const b of blocksData) {
        await invClient.query(`
          INSERT INTO warehouse_block (id, store_id, name, type, rows, cols)
          OVERRIDING SYSTEM VALUE
          VALUES ($1, $2, $3, $4, $5, $6)
        `, [b.id, storeId, b.name, b.type, b.rows, b.cols]);
      }
      await invClient.query(`SELECT setval(pg_get_serial_sequence('warehouse_block', 'id'), 6)`);

      // 3. Prepare Location Bulk Inserts
      console.log('📍 Generating 600 Locations...');
      let locationId = 1;
      const shelfLocationIds = []; // 301..600 (Store shelves)

      const locIds = [], locBlockIds = [], locNames = [], locPositions = [];

      for (const b of blocksData) {
        for (let pos = 1; pos <= 100; pos++) {
          const locName = `${b.prefix}${pos.toString().padStart(2, '0')}`;
          locIds.push(locationId);
          locBlockIds.push(b.id);
          locNames.push(locName);
          locPositions.push(pos);

          if (b.type === 'store_shelf') {
            shelfLocationIds.push(locationId);
          }
          locationId++;
        }
      }

      await invClient.query(`
        INSERT INTO location (id, block_id, name, position, max_capacity, is_active)
        OVERRIDING SYSTEM VALUE
        SELECT id, block_id, name, position, 5000, TRUE
        FROM unnest($1::bigint[], $2::bigint[], $3::text[], $4::int[])
        AS t(id, block_id, name, position)
      `, [locIds, locBlockIds, locNames, locPositions]);

      await invClient.query(`SELECT setval(pg_get_serial_sequence('location', 'id'), ${locationId - 1})`);
      console.log(`✅ Bulk inserted 600 locations.`);

      // 4. Prepare Batches, Items, Movements Bulk Arrays (1:1 Relationship!)
      console.log(`📦 Bulk preparing 1:1 Batches & Inventory Items for ${products.length} products...`);

      const discountOptions = [5, 10, 15, 20, 25, 30];

      // Batches arrays
      const batchIds = [], batchStoreIds = [], batchProductIds = [], batchCostPrices = [], batchUnitPrices = [];
      const batchDiscounts = [], batchPromotions = [], batchQuantities = [];

      // Items arrays (1 item per batch)
      const itemIds = [], itemBatchIds = [], itemLocIds = [], itemOnHand = [], itemOnShelf = [];

      // Movements arrays (1 movement per item)
      const movIds = [], movItemIds = [], movTypes = [], movQuantities = [], movReasons = [];

      let batchIdCounter = 1;
      let itemIdCounter = 1;
      let movementIdCounter = 1;

      for (let i = 0; i < products.length; i++) {
        const prod = products[i];
        const unitPrice = parseFloat(prod.unit_price) || 20000;
        const costPrice = Math.round(unitPrice * 0.7); // 30% gross margin

        const totalQty = 1000;
        const onShelf = randomInt(200, 800);
        const onHand = totalQty - onShelf;

        // Round-robin assign primary display location on shelf
        const primaryLocationId = shelfLocationIds[i % shelfLocationIds.length];

        // Random Discount: ~35% chance to have discount
        const hasDiscount = Math.random() < 0.35;
        const discount = hasDiscount ? discountOptions[randomInt(0, discountOptions.length - 1)] : 0;
        const promotionApplied = hasDiscount ? 'manual' : 'none';

        // Batch (1 per product)
        const batchId = batchIdCounter++;
        batchIds.push(batchId);
        batchStoreIds.push(storeId);
        batchProductIds.push(prod.id);
        batchCostPrices.push(costPrice);
        batchUnitPrices.push(unitPrice);
        batchDiscounts.push(discount);
        batchPromotions.push(promotionApplied);
        batchQuantities.push(totalQty);

        // Inventory Item (Single 1:1 item containing BOTH onHand and onShelf)
        const itemId = itemIdCounter++;
        itemIds.push(itemId);
        itemBatchIds.push(batchId);
        itemLocIds.push(primaryLocationId);
        itemOnHand.push(onHand);
        itemOnShelf.push(onShelf);

        // Inventory Movement (Initial 1000 stock in)
        const movId = movementIdCounter++;
        movIds.push(movId);
        movItemIds.push(itemId);
        movTypes.push('in');
        movQuantities.push(totalQty);
        movReasons.push('initial_stock | Kho & Kệ trưng bày');
      }

      // Execute Bulk INSERT product_batch
      console.log('⚡ Bulk inserting 1380 product_batch records (1 per product)...');
      await invClient.query(`
        INSERT INTO product_batch (id, store_id, product_id, cost_price, unit_price, discount_percentage, promotion_applied, quantity, mfg_date, expiry_date, status, notes)
        OVERRIDING SYSTEM VALUE
        SELECT id, store_id, product_id, cost_price, unit_price, discount_percentage, promotion_applied, quantity, '2026-01-01'::date, '2029-01-01'::date, 'active', 'Initial seed stock'
        FROM unnest($1::bigint[], $2::bigint[], $3::bigint[], $4::numeric[], $5::numeric[], $6::numeric[], $7::text[], $8::int[])
        AS t(id, store_id, product_id, cost_price, unit_price, discount_percentage, promotion_applied, quantity)
      `, [batchIds, batchStoreIds, batchProductIds, batchCostPrices, batchUnitPrices, batchDiscounts, batchPromotions, batchQuantities]);

      // Execute Bulk INSERT inventory_item (1:1 with batch)
      console.log('⚡ Bulk inserting 1380 inventory_item records (1:1 with batch)...');
      await invClient.query(`
        INSERT INTO inventory_item (id, product_batch_id, location_id, quantity_on_hand, quantity_on_shelf, quantity_reserved, reorder_point)
        OVERRIDING SYSTEM VALUE
        SELECT id, product_batch_id, location_id, quantity_on_hand, quantity_on_shelf, 0, 10
        FROM unnest($1::bigint[], $2::bigint[], $3::bigint[], $4::int[], $5::int[])
        AS t(id, product_batch_id, location_id, quantity_on_hand, quantity_on_shelf)
      `, [itemIds, itemBatchIds, itemLocIds, itemOnHand, itemOnShelf]);

      // Execute Bulk INSERT inventory_movement
      console.log('⚡ Bulk inserting 1380 inventory_movement records...');
      await invClient.query(`
        INSERT INTO inventory_movement (id, inventory_item_id, movement_type, quantity, reason, moved_at, performed_by)
        OVERRIDING SYSTEM VALUE
        SELECT id, inventory_item_id, movement_type, quantity, reason, NOW(), 1
        FROM unnest($1::bigint[], $2::bigint[], $3::text[], $4::int[], $5::text[])
        AS t(id, inventory_item_id, movement_type, quantity, reason)
      `, [movIds, movItemIds, movTypes, movQuantities, movReasons]);

      // Set Sequence Values
      await invClient.query(`SELECT setval(pg_get_serial_sequence('product_batch', 'id'), ${batchIdCounter - 1})`);
      await invClient.query(`SELECT setval(pg_get_serial_sequence('inventory_item', 'id'), ${itemIdCounter - 1})`);
      await invClient.query(`SELECT setval(pg_get_serial_sequence('inventory_movement', 'id'), ${movementIdCounter - 1})`);

      await invClient.query('COMMIT');
      const duration = ((Date.now() - startTime) / 1000).toFixed(2);
      console.log(`🎉 Database transaction committed successfully in ${duration}s!`);

      // 5. Verification Summary
      console.log('\n📊 VERIFICATION SUMMARY:');
      const counts = await invClient.query(`
        SELECT 'warehouse_block' AS table_name, COUNT(*)::int AS count FROM warehouse_block WHERE store_id = $1
        UNION ALL SELECT 'location', COUNT(*)::int FROM location
        UNION ALL SELECT 'product_batch', COUNT(*)::int FROM product_batch WHERE store_id = $1
        UNION ALL SELECT 'inventory_item', COUNT(*)::int FROM inventory_item
        UNION ALL SELECT 'inventory_movement', COUNT(*)::int FROM inventory_movement
      `, [storeId]);

      console.table(counts.rows);

      const discountSummary = await invClient.query(`
        SELECT 
          COUNT(*)::int AS total_batches,
          COUNT(*) FILTER (WHERE discount_percentage > 0)::int AS discounted_batches,
          COUNT(*) FILTER (WHERE promotion_applied = 'manual')::int AS manual_promotions,
          ROUND(AVG(discount_percentage) FILTER (WHERE discount_percentage > 0), 2) AS avg_discount_pct
        FROM product_batch WHERE store_id = $1
      `, [storeId]);

      console.log('🏷️ Promotion & Discount Summary:');
      console.table(discountSummary.rows);

      const viewSummary = await invClient.query(`
        SELECT 
          COUNT(*)::int AS total_products, 
          SUM(total_on_hand)::bigint AS total_on_hand, 
          SUM(total_on_shelf)::bigint AS total_on_shelf,
          SUM(total_available)::bigint AS grand_total
        FROM v_product_inventory WHERE store_id = $1
      `, [storeId]);

      console.log('📈 Inventory View Summary:');
      console.table(viewSummary.rows);

    } catch (err) {
      await invClient.query('ROLLBACK');
      throw err;
    } finally {
      invClient.release();
    }

  } catch (error) {
    console.error('❌ SEED ERROR:', error);
    process.exit(1);
  } finally {
    await catalogPool.end();
    await inventoryPool.end();
  }
}

seedInventory();
