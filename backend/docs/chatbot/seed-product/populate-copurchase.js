/**
 * Populate Co-Purchase Stats — Tạo dữ liệu co-purchase trực tiếp cho Chatbot Apriori
 * 
 * ⚡ PERFORMANCE (v4 — SQL Push-down, Step-by-step progress):
 *   - Push-down computation: tính HOÀN TOÀN trong PostgreSQL
 *   - Tách thành nhiều step nhỏ → hiện tiến độ sau MỖI bước
 *   - SELF JOIN thay thế O(N²) Node.js loop
 *   - Single atomic TRANSACTION (safe to cancel — ROLLBACK on error)
 */
require('dotenv').config();
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

const NAME_TO_ID = {
  'Ba chỉ bò Mỹ thái lát mỏng khay 500g': 1,
  'Nấm kim châm Hàn Quốc gói 150g': 2,
  'Rau muống VietGAP bó 500g': 3,
  'Gia vị nêm sẵn lẩu Thái Barona 80g': 4,
  'Bún tươi Ba Khánh gói 500g': 5,
  'Cá viên chiên xâu tôm viên Vissan 500g': 6,
  'Bánh mì Sandwich lạt Kinh Đô 275g': 7,
  'Lốc 4 hộp Sữa tươi Vinamilk không đường 180ml': 8,
  'Thùng 48 hộp Sữa tươi Vinamilk không đường 180ml': 9,
  'Trứng gà sạch V.Food hộp 10 quả': 10,
  'Xúc xích heo tiệt trùng Vissan gói 4 cây': 11,
  'Mì Hảo Hảo hương vị tôm chua cay 75g': 12,
  'Thùng 30 gói mì Hảo Hảo tôm chua cay': 13,
  'Mì xào khô Indomie vị sườn đặc biệt 85g': 14,
  'Phở bò Vifon gói 80g': 15,
  'Miến dong Phú Hương sườn heo': 16,
  'Bia Heineken Silver lon 330ml': 17,
  'Thùng 24 lon bia Tiger Bạc 330ml': 18,
  'Nước ngọt Coca-Cola vị nguyên bản chai 390ml': 19,
  "Snack khoai tây Lay's vị Tự nhiên 52g": 20,
  'Khô gà lá chanh G kitchen hũ 200g': 21,
  'Cải thìa mỡ VietGAP 500g': 22,
  'Cà chua mận đỏ Đà Lạt 500g': 23,
  'Hành tây vàng loại 1 kg': 24,
  'Chuối già Nam Mỹ nải 1kg': 25,
  'Cherry đỏ Mỹ size 9.5 Hộp 500g': 26,
  'Thịt sườn non heo chuẩn C.P 500g': 27,
  'Thịt ba rọi heo rút sườn 500g': 28,
  'Thăn ngoại bò Úc Hokubee cắt bít tết 250g': 29,
  'Tôm sú sinh thái lột vỏ đông lạnh 250g': 30,
  'Mực ống làm sạch khay 300g': 31,
  'Chả lụa heo G Kitchen đòn 500g': 32,
  'Há cảo tôm thịt mini Cầu Tre 500g': 33,
  'Xúc xích xông khói phô mai vòng CP 500g': 34,
  'Lốc 4 hộp Sữa tươi TH True Milk có đường 180ml': 35,
  'Lốc 4 hộp Sữa chua nha đam Vinamilk 100g': 36,
  'Phô mai Bò Lúc Lắc hộp 8 miếng 120g': 37,
  'Nước khoáng thiên nhiên La Vie chai 500ml': 38,
  'Nước tinh khiết Aquafina chai 1.5L': 39,
  'Trà Ô Long Tea+ Plus chai 455ml': 40,
  'Nước tăng lực Red Bull lon 250ml': 41,
  'Gạo thơm ST25 lúa tôm Ông Cua túi 5kg': 42,
  'Bao Gạo đặc sản ST25 Sóc Trăng 25kg': 43,
  'Gạo thơm Lài Miên túi 5kg': 44,
  'Nấm hương khô Tây Bắc gói 100g': 45,
  'Đậu đen xanh lòng hạt nhỏ 500g': 46,
  'Dầu ăn thực vật Tường An chai 1L': 47,
  'Dầu đậu nành Simply chai 2L': 48,
  'Nước mắm Nam Ngư 11 độ đạm chai 750ml': 49,
  'Nước mắm cá cơm Hưng Thịnh 35 độ đạm chai 620ml': 50,
  'Nước tương Chinsu tỏi ớt chai 250ml': 51,
  'Hạt nêm Knorr từ thịt thăn xương ống gói 400g': 52,
  'Bột ngọt Ajinomoto gói 454g': 53,
  'Đường tinh luyện Biên Hòa bịch 1kg': 54,
  'Bánh quy bơ Danisa hộp thiếc 454g': 55,
  'Bánh xốp phô mai Nabati hộp 150g': 56,
  'Kẹo mút Chupa Chups hương trái cây gói 10 que': 57,
  'Bánh mì hoa cúc Harrys Brioche Tressée 500g': 58,
  'Hạt điều rang muối Bình Phước hũ 250g': 59,
  'Đậu phộng da cá Tân Tân hũ 275g': 60,
};

/** Helper: run a SQL step with progress logging */
async function step(client, label, sql, params = []) {
  const t = Date.now();
  process.stdout.write(`   ⏳ ${label}...`);
  const result = await client.query(sql, params);
  const ms = Date.now() - t;
  const count = result.rowCount ?? result.rows?.[0]?.cnt ?? '?';
  console.log(` ✓ ${count} rows (${ms}ms)`);
  return result;
}

async function populateCoPurchase() {
  const startTime = Date.now();
  console.log('\n🔄 Populate Co-Purchase Stats (v4 — SQL Push-down)\n');

  const client = await pool.connect();

  try {
    await client.query('BEGIN');
    console.log('🔒 BEGIN TRANSACTION\n');

    // ── Step 1: Temp mapping table ──
    console.log('📦 Step 1/6: Tạo bảng mapping name→id');
    await client.query(`
      CREATE TEMP TABLE _product_map (
        product_name TEXT PRIMARY KEY,
        product_id   INTEGER NOT NULL
      ) ON COMMIT DROP
    `);
    const names = Object.entries(NAME_TO_ID);
    const mv = [], mp = [];
    let pi = 1;
    for (const [name, id] of names) {
      mv.push(`($${pi}, $${pi + 1})`);
      mp.push(name, id);
      pi += 2;
    }
    await client.query(`INSERT INTO _product_map VALUES ${mv.join(', ')}`, mp);
    console.log(`   ✓ ${names.length} products mapped\n`);

    // ── Step 2: Materialize order_items into temp table ──
    console.log('📖 Step 2/6: Đọc order details + map product IDs');
    await step(client, 'Tạo _order_items', `
      CREATE TEMP TABLE _order_items AS
      SELECT DISTINCT o.id AS order_id, o.store_id::integer, pm.product_id
      FROM sale_order o
      JOIN sale_order_detail d ON d.order_id = o.id
      JOIN _product_map pm ON pm.product_name = d.product_name
      WHERE o.status = 'delivered' AND o.payment_status = 'paid'
    `);
    // Quick count for feedback
    const itemCount = await client.query('SELECT COUNT(*)::int AS cnt FROM _order_items');
    console.log(`   📊 ${itemCount.rows[0].cnt} order-item rows\n`);

    // ── Step 3: Qualified orders (>= 2 products) + frequencies ──
    console.log('📈 Step 3/6: Tính tần suất sản phẩm + đơn hàng đủ điều kiện');
    await step(client, 'Tạo _product_freq', `
      CREATE TEMP TABLE _product_freq AS
      SELECT store_id, product_id, COUNT(DISTINCT order_id)::int AS freq
      FROM _order_items
      GROUP BY store_id, product_id
    `);
    await step(client, 'Tạo _store_totals', `
      CREATE TEMP TABLE _store_totals AS
      SELECT store_id, COUNT(DISTINCT order_id)::int AS total_orders
      FROM (
        SELECT order_id, store_id FROM _order_items
        GROUP BY order_id, store_id
        HAVING COUNT(DISTINCT product_id) >= 2
      ) q
      GROUP BY store_id
    `);
    const storeTotal = await client.query('SELECT total_orders FROM _store_totals LIMIT 1');
    console.log(`   📊 ${storeTotal.rows[0]?.total_orders || 0} qualified orders\n`);

    // ── Step 4: SELF JOIN — tạo cặp co-purchase ──
    console.log('⚙️  Step 4/6: SELF JOIN tạo co-purchase pairs (bước nặng nhất)');
    await step(client, 'Tạo _pair_counts', `
      CREATE TEMP TABLE _pair_counts AS
      SELECT
        a.store_id,
        LEAST(a.product_id, b.product_id) AS pid_a,
        GREATEST(a.product_id, b.product_id) AS pid_b,
        COUNT(DISTINCT a.order_id)::int AS co_count
      FROM _order_items a
      JOIN _order_items b
        ON a.order_id = b.order_id
        AND a.store_id = b.store_id
        AND a.product_id < b.product_id
      GROUP BY a.store_id, LEAST(a.product_id, b.product_id), GREATEST(a.product_id, b.product_id)
    `);
    const pairCount = await client.query('SELECT COUNT(*)::int AS cnt FROM _pair_counts');
    console.log(`   📊 ${pairCount.rows[0].cnt} unique pairs\n`);

    // ── Step 5: Truncate + INSERT with Apriori metrics ──
    console.log('💾 Step 5/6: Ghi co_purchase_stats + Apriori metrics');
    await step(client, 'Truncate cũ', 'TRUNCATE TABLE co_purchase_stats CASCADE');
    await step(client, 'Insert pairs + metrics', `
      INSERT INTO co_purchase_stats (
        product_id_a, product_id_b, store_id, co_purchase_count,
        support, confidence_ab, confidence_ba, lift, total_orders, last_updated_at
      )
      SELECT
        pc.pid_a, pc.pid_b, pc.store_id, pc.co_count,
        ROUND(pc.co_count::numeric / st.total_orders, 4),
        ROUND(pc.co_count::numeric / fa.freq, 4),
        ROUND(pc.co_count::numeric / fb.freq, 4),
        ROUND((pc.co_count::numeric * st.total_orders) / (fa.freq * fb.freq), 2),
        st.total_orders, NOW()
      FROM _pair_counts pc
      JOIN _store_totals st ON st.store_id = pc.store_id
      JOIN _product_freq fa ON fa.store_id = pc.store_id AND fa.product_id = pc.pid_a
      JOIN _product_freq fb ON fb.store_id = pc.store_id AND fb.product_id = pc.pid_b
    `);
    console.log('');

    // ── Step 6: Update product_order_frequency ──
    console.log('📈 Step 6/6: Update product_order_frequency');
    await step(client, 'Upsert frequencies', `
      INSERT INTO product_order_frequency (product_id, store_id, order_count, last_computed_at)
      SELECT product_id, store_id, freq, NOW()
      FROM _product_freq
      ON CONFLICT (product_id, store_id)
      DO UPDATE SET order_count = EXCLUDED.order_count, last_computed_at = NOW()
    `);
    console.log('');

    // ── COMMIT ──
    await client.query('COMMIT');
    console.log('✅ COMMIT — all data written atomically.\n');

    // ── Statistics ──
    const stats = await client.query(`
      SELECT
        COUNT(*)::int AS total_pairs,
        MAX(co_purchase_count)::int AS max_count,
        MAX(lift::numeric)::numeric AS max_lift,
        COUNT(*) FILTER (WHERE lift::numeric >= 0.5)::int AS pairs_05,
        COUNT(*) FILTER (WHERE lift::numeric >= 1.0)::int AS pairs_10
      FROM co_purchase_stats
    `);
    const s = stats.rows[0];

    const topByLift = await client.query(`
      SELECT product_id_a, product_id_b, co_purchase_count, lift
      FROM co_purchase_stats ORDER BY lift::numeric DESC LIMIT 5
    `);

    const heineken = await client.query(`
      SELECT product_id_a, product_id_b, co_purchase_count, lift
      FROM co_purchase_stats
      WHERE product_id_a = 17 OR product_id_b = 17
      ORDER BY co_purchase_count DESC LIMIT 5
    `);

    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`⏱️  Tổng thời gian: ${elapsed}s`);
    console.log(`   📊 Total pairs: ${s.total_pairs}`);
    console.log(`   📊 Max lift: ${s.max_lift} | Pairs lift≥0.5: ${s.pairs_05} | lift≥1.0: ${s.pairs_10}`);

    console.log(`\n🏆 Top 5 by Lift:`);
    for (const r of topByLift.rows) {
      const nA = Object.entries(NAME_TO_ID).find(([, id]) => id === Number(r.product_id_a))?.[0]?.slice(0, 40) || `#${r.product_id_a}`;
      const nB = Object.entries(NAME_TO_ID).find(([, id]) => id === Number(r.product_id_b))?.[0]?.slice(0, 40) || `#${r.product_id_b}`;
      console.log(`   [lift=${r.lift}, count=${r.co_purchase_count}] ${nA} ↔ ${nB}`);
    }

    if (heineken.rows.length > 0) {
      console.log(`\n🍺 Heineken Pairs:`);
      for (const r of heineken.rows) {
        const oid = Number(r.product_id_a) === 17 ? r.product_id_b : r.product_id_a;
        const n = Object.entries(NAME_TO_ID).find(([, id]) => id === Number(oid))?.[0]?.slice(0, 50) || `#${oid}`;
        console.log(`   [count=${r.co_purchase_count}, lift=${r.lift}] ${n}`);
      }
    }

    console.log(`\n💡 Dữ liệu sẵn sàng cho Apriori. Chạy: docker compose restart chatbot\n`);

  } catch (err) {
    try { await client.query('ROLLBACK'); } catch (_) { }
    console.error('\n❌ ROLLBACK — no data changed.');
    console.error('   Lỗi:', err.message);
  } finally {
    client.release();
    await pool.end();
  }
}

populateCoPurchase();
