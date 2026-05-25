/**
 * Data-Driven Category Synonyms Migration
 * Run: node docs/chatbot/seed-product/migrate-synonyms.js
 */
const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');

// Load env
const envPath = path.resolve(__dirname, '..', '..', '..', '.env');
if (fs.existsSync(envPath)) {
  const envContent = fs.readFileSync(envPath, 'utf8');
  for (const line of envContent.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx === -1) continue;
    const key = trimmed.substring(0, eqIdx).trim();
    const val = trimmed.substring(eqIdx + 1).trim();
    if (!process.env[key]) process.env[key] = val;
  }
}

const dbUrl = process.env.DATABASE_URL;
if (!dbUrl) {
  console.error('❌ DATABASE_URL not set');
  process.exit(1);
}

const pool = new Pool({
  connectionString: dbUrl,
  ssl: { rejectUnauthorized: false }
});

async function run() {
  try {
    console.log('🔄 Running database schema migration for Category Synonyms...');

    // 1. Add column search_synonyms to category
    await pool.query(`
            ALTER TABLE category ADD COLUMN IF NOT EXISTS search_synonyms TEXT DEFAULT NULL
        `);
    console.log('✅ search_synonyms column created or already exists.');

    // 2. Seed initial search synonyms to categories
    await pool.query(`
            UPDATE category SET search_synonyms = 'đồ ăn vặt, snack, đồ nhắm, bánh kẹo, ăn vặt' WHERE name = 'Bánh, kẹo, snack';
            UPDATE category SET search_synonyms = 'đồ ăn vặt, snack, đồ nhắm ngon, ăn vặt' WHERE name = 'Snack & Đồ nhắm';
            UPDATE category SET search_synonyms = 'bánh kẹo, đồ ăn vặt, kẹo ngọt, bánh quy' WHERE name = 'Bánh quy & Kẹo';
            UPDATE category SET search_synonyms = 'bánh mì, bánh ngọt, ăn sáng' WHERE name = 'Bánh mì & Bánh ngọt';
            UPDATE category SET search_synonyms = 'đồ uống, thức uống, bia rượu, nước ngọt' WHERE name ILIKE '%bia%nước%';
            UPDATE category SET search_synonyms = 'đồ ăn nhanh, thức ăn nhanh, ăn liền' WHERE name ILIKE '%mì%miến%';
            UPDATE category SET search_synonyms = 'gia vị nấu ăn, đồ nêm, nước chấm' WHERE name ILIKE '%dầu ăn%gia vị%';
        `);
    console.log('✅ Initial Category Synonyms seeded successfully.');

    // 3. Confirm contents
    const { rows } = await pool.query(`
            SELECT id, name, search_synonyms FROM category WHERE search_synonyms IS NOT NULL
        `);
    console.log('\n📊 SEEDED CATEGORIES WITH SYNONYMS:');
    rows.forEach(r => {
      console.log(`   [ID: ${r.id}] ${r.name} ➔ "${r.search_synonyms}"`);
    });

    await pool.end();
  } catch (err) {
    console.error('❌ Migration failed:', err.message);
    await pool.end();
    process.exit(1);
  }
}

run();
