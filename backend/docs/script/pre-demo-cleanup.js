/**
 * Pre-Demo Cleanup Script — Reset Recommendation Feedback
 * 
 * Run BEFORE thesis defense demo to clear old feedback data.
 * This ensures Dashboard Live Feed starts empty for maximum visual impact.
 * 
 * Usage:
 *   cd microservices && node docs/script/pre-demo-cleanup.js
 * 
 * What it does:
 *   1. Clears recommendation_feedback (all sources)
 *   2. Verifies seed data integrity (co_purchase_stats, item_similarity, product_knowledge_base)
 *   3. Prints a readiness checklist
 */
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

async function cleanup() {
  const startTime = Date.now();
  console.log('\n🧹 Pre-Demo Cleanup — Thesis Defense Preparation\n');
  console.log('─'.repeat(55));

  try {
    // Step 1: Clear recommendation feedback
    console.log('\n📋 Step 1: Clearing recommendation_feedback...');
    const { rowCount: feedbackCleared } = await pool.query(
      'DELETE FROM recommendation_feedback WHERE store_id = 1'
    );
    console.log(`   ✓ Deleted ${feedbackCleared} feedback rows`);

    // Step 2: Verify seed data integrity
    console.log('\n📋 Step 2: Verifying seed data integrity...\n');

    // Check co_purchase_stats (Apriori)
    const { rows: [aprioriStats] } = await pool.query(`
      SELECT COUNT(*)::int AS pair_count, 
             COALESCE(MAX(co_purchase_count), 0)::int AS max_freq
      FROM co_purchase_stats WHERE store_id = 1
    `);
    const aprioriOk = aprioriStats.pair_count > 0;
    console.log(`   ${aprioriOk ? '✅' : '❌'} Apriori (co_purchase_stats): ${aprioriStats.pair_count} pairs, max freq = ${aprioriStats.max_freq}`);
    if (!aprioriOk) {
      console.log('      ⚠ Run: node docs/chatbot/seed-product/mock-orders.js && node docs/chatbot/seed-product/populate-copurchase.js');
    }

    // Check item_similarity (CF)
    const { rows: [cfStats] } = await pool.query(`
      SELECT COUNT(*)::int AS pair_count,
             ROUND(COALESCE(MAX(similarity), 0)::numeric, 4) AS max_sim
      FROM item_similarity WHERE store_id = 1
    `);
    const cfOk = cfStats.pair_count > 0;
    console.log(`   ${cfOk ? '✅' : '❌'} CF (item_similarity): ${cfStats.pair_count} pairs, max sim = ${cfStats.max_sim}`);
    if (!cfOk) {
      console.log('      ⚠ Run: node docs/chatbot/seed-product/mock-interactions.js');
    }

    // Check user_product_interaction (CF user data)
    const { rows: [interactionStats] } = await pool.query(`
      SELECT COUNT(DISTINCT user_id)::int AS user_count,
             COUNT(*)::int AS total_rows
      FROM user_product_interaction WHERE store_id = 1
    `);
    const interOk = interactionStats.user_count > 0;
    console.log(`   ${interOk ? '✅' : '❌'} CF Interactions: ${interactionStats.user_count} users, ${interactionStats.total_rows} rows`);

    // Check product_knowledge_base (RAG)
    const { rows: [kbStats] } = await pool.query(`
      SELECT COUNT(*)::int AS total,
             COUNT(*) FILTER (WHERE is_in_stock = true)::int AS in_stock
      FROM product_knowledge_base WHERE store_id = 1
    `);
    const kbOk = kbStats.total > 0;
    console.log(`   ${kbOk ? '✅' : '❌'} Knowledge Base: ${kbStats.total} products (${kbStats.in_stock} in stock)`);
    if (!kbOk) {
      console.log('      ⚠ Restart chatbot service to trigger data sync');
    }

    // Top 5 co-purchase pairs (preview for demo)
    if (aprioriOk) {
      console.log('\n   🏆 Top 5 Apriori Pairs (for ACT 2 reference):');
      const { rows: topPairs } = await pool.query(`
        SELECT product_id_a, product_id_b, co_purchase_count
        FROM co_purchase_stats
        WHERE store_id = 1
        ORDER BY co_purchase_count DESC
        LIMIT 5
      `);
      for (const p of topPairs) {
        console.log(`      [${p.co_purchase_count}x] Product #${p.product_id_a} ↔ #${p.product_id_b}`);
      }
    }

    // Top 5 CF similarities (preview for demo)
    if (cfOk) {
      console.log('\n   🏆 Top 5 CF Similarities (for ACT 3 reference):');
      const { rows: topSims } = await pool.query(`
        SELECT item_a, item_b, ROUND(similarity::numeric, 4) AS sim, common_users
        FROM item_similarity
        WHERE store_id = 1
        ORDER BY similarity DESC
        LIMIT 5
      `);
      for (const s of topSims) {
        console.log(`      [sim=${s.sim}] Product #${s.item_a} ↔ #${s.item_b} (${s.common_users} users)`);
      }
    }

    // Step 3: Readiness checklist
    const allOk = aprioriOk && cfOk && interOk && kbOk;
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

    console.log('\n' + '─'.repeat(55));
    console.log(`\n${allOk ? '🎯' : '⚠️'} READINESS CHECKLIST (${elapsed}s)\n`);
    console.log(`   ${aprioriOk ? '✅' : '❌'} Apriori data ready`);
    console.log(`   ${cfOk ? '✅' : '❌'} CF similarities ready`);
    console.log(`   ${interOk ? '✅' : '❌'} User interactions seeded`);
    console.log(`   ${kbOk ? '✅' : '❌'} Knowledge base populated`);
    console.log(`   ✅ Feedback table cleared (${feedbackCleared} rows removed)`);

    if (allOk) {
      console.log('\n   🎉 ALL SYSTEMS GO! Dashboard is clean, data is ready.');
      console.log('   → Login as Customer ID 1-150 (Persona: Noi Tro Nau Lau)');
      console.log('   → Open Dashboard Live Feed in a separate tab');
      console.log('   → Follow the 4-ACT demo script\n');
    } else {
      console.log('\n   ⚠️ Some data is missing. Run the seed scripts listed above first.\n');
    }

  } catch (err) {
    console.error('\n❌ Error:', err.message);
    console.error(err.stack);
  } finally {
    await pool.end();
  }
}

cleanup();
