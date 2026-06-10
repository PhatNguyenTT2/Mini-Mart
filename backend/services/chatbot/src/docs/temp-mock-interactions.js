const { createPool } = require('../../../../shared/db');
const pool = createPool();

const STORE_ID = 1;

const PRODUCTS = {
  1: 'Ba chỉ bò Mỹ', 2: 'Nấm kim châm', 3: 'Rau muống VietGAP',
  4: 'Gia vị lẩu Thái', 5: 'Bún tươi', 6: 'Cá viên chiên Vissan',
  7: 'Bánh mì Sandwich', 8: 'Sữa Vinamilk', 9: 'Thùng sữa Vinamilk',
  10: 'Trứng gà sạch', 11: 'Xúc xích Vissan', 12: 'Mì Hảo Hảo',
  13: 'Dầu ăn Tường An', 14: 'Gạo ST25', 15: 'Đường trắng',
  16: 'Muối iốt', 17: 'Bia Heineken', 18: 'Bia Tiger',
  19: 'Coca-Cola', 20: 'Snack Lays', 21: 'Khô gà lá chanh',
  22: 'Đậu phộng rang', 23: 'Nước tương Maggi', 24: 'Cà chua',
  25: 'Hành tây', 26: 'Tỏi', 27: 'Ớt hiểm', 28: 'Chanh',
  29: 'Rau xà lách', 30: 'Dưa leo', 49: 'Nước mắm Nam Ngư',
  52: 'Hạt nêm Knorr', 53: 'Bột ngọt Ajinomoto',
};

const CLUSTERS = {
  // Nhóm 1: Nội trợ Nấu lẩu (25 users)
  NOI_TRO: {
    userRange: [1, 25],
    primary: [1, 2, 3, 4, 5, 24, 25, 26, 27, 28],
    secondary: [6, 13, 49, 52, 53, 23, 16],
    avoid: [17, 18, 12, 19, 20, 21],
    primaryFreq: [5, 10],
    secondaryFreq: [1, 3],
  },
  // Nhóm 2: Sinh viên Ăn vặt & Thức khuya (20 users)
  SINH_VIEN: {
    userRange: [26, 45],
    primary: [12, 11, 19, 20, 7, 8],
    secondary: [10, 15, 9, 22],
    avoid: [1, 2, 3, 4, 24, 25, 26, 49, 52, 53],
    primaryFreq: [10, 20],
    secondaryFreq: [2, 5],
  },
  // Nhóm 3: Dân nhậu Cuối tuần (14 users)
  DAN_NHAU: {
    userRange: [46, 54],
    primary: [17, 18, 21, 22, 6],
    secondary: [20, 19, 28, 27],
    avoid: [1, 2, 3, 14, 15, 52, 53],
    primaryFreq: [2, 4],
    secondaryFreq: [1, 2],
  }
};

function randInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randSubset(arr, minCount, maxCount) {
  const count = randInt(minCount, Math.min(maxCount, arr.length));
  const shuffled = [...arr].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, count);
}

function generateRecencyWeight() {
  const days = randInt(1, 90);
  return Math.round(Math.exp(-0.01 * days) * 10000) / 10000;
}

async function generateMockInteractions() {
  const startTime = Date.now();
  console.log('\n🧑‍🤝‍🧑 Mock Interactions Generator — Phase 2 CF Data Seeding in Docker\n');

  try {
    // Clear existing data
    console.log('🧹 Clearing existing interaction data...');
    await pool.query('DELETE FROM item_similarity WHERE store_id = $1', [STORE_ID]);
    await pool.query('DELETE FROM user_product_interaction WHERE store_id = $1', [STORE_ID]);

    const allInteractions = [];
    const stats = { noiTro: 0, sinhVien: 0, danNhau: 0, totalRows: 0 };
    const allProductIds = Object.keys(PRODUCTS).map(Number);

    for (const [clusterName, cluster] of Object.entries(CLUSTERS)) {
      const [startUser, endUser] = cluster.userRange;
      const userCount = endUser - startUser + 1;
      let clusterRows = 0;

      console.log(`\n📋 Cluster: ${clusterName} (User ${startUser}-${endUser}, ${userCount} users)`);

      for (let userId = startUser; userId <= endUser; userId++) {
        const userInteractions = new Map();

        const primaryPicks = randSubset(cluster.primary,
          Math.ceil(cluster.primary.length * 0.6),
          cluster.primary.length);

        for (const pid of primaryPicks) {
          const count = randInt(cluster.primaryFreq[0], cluster.primaryFreq[1]);
          userInteractions.set(pid, {
            count,
            qty: count * randInt(1, 4),
            recency: generateRecencyWeight()
          });
        }

        if (cluster.secondary) {
          const secondaryPicks = randSubset(cluster.secondary, 1,
            Math.ceil(cluster.secondary.length * 0.5));
          for (const pid of secondaryPicks) {
            const count = randInt(cluster.secondaryFreq[0], cluster.secondaryFreq[1]);
            userInteractions.set(pid, {
              count,
              qty: count * randInt(1, 2),
              recency: generateRecencyWeight()
            });
          }
        }

        if (Math.random() < 0.10 && cluster.avoid.length > 0) {
          const noisePid = cluster.avoid[randInt(0, cluster.avoid.length - 1)];
          if (!userInteractions.has(noisePid)) {
            userInteractions.set(noisePid, { count: 1, qty: 1, recency: 0.5 });
          }
        }

        for (const [pid, data] of userInteractions) {
          const interactionScore = Math.round(data.count * data.recency * 1000) / 1000;
          allInteractions.push([
            userId, pid, STORE_ID,
            data.count, data.qty,
            interactionScore
          ]);
        }

        clusterRows += userInteractions.size;
      }

      stats[clusterName === 'NOI_TRO' ? 'noiTro' :
        clusterName === 'SINH_VIEN' ? 'sinhVien' : 'danNhau'] = clusterRows;
      stats.totalRows += clusterRows;
      console.log(`   → ${clusterRows} interaction rows generated.`);
    }

    console.log(`\n💾 Inserting ${allInteractions.length} interactions...`);
    const INSERT_CHUNK = 300;
    for (let c = 0; c < allInteractions.length; c += INSERT_CHUNK) {
      const chunk = allInteractions.slice(c, c + INSERT_CHUNK);
      const values = [];
      const params = [];
      let pi = 1;

      for (const row of chunk) {
        values.push(`($${pi}, $${pi + 1}, $${pi + 2}, $${pi + 3}, $${pi + 4}, NOW(), $${pi + 5})`);
        params.push(...row);
        pi += 6;
      }

      await pool.query(`
        INSERT INTO user_product_interaction 
          (user_id, product_id, store_id, purchase_count, total_quantity, last_purchased_at, interaction_score)
        VALUES ${values.join(', ')}
        ON CONFLICT (user_id, product_id, store_id)
        DO UPDATE SET 
          purchase_count = EXCLUDED.purchase_count,
          total_quantity = EXCLUDED.total_quantity,
          last_purchased_at = EXCLUDED.last_purchased_at,
          interaction_score = EXCLUDED.interaction_score
      `, params);
    }

    console.log(`   ✓ ${allInteractions.length} rows inserted.`);

    console.log('\n🧮 Computing Adjusted Cosine Similarities...');
    const CollaborativeFilteringService = require('../services/cf.service');
    const cfService = new CollaborativeFilteringService(pool);
    const result = await cfService.computeItemSimilarities(STORE_ID, 2);

    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`\n✅ HOÀN THÀNH trong ${elapsed}s!`);
    console.log(`   📊 Interactions: ${allInteractions.length} rows`);
    console.log(`   👥 Users: 54`);
    console.log(`   🔗 Item similarities: ${result.pairsComputed} pairs`);

  } catch (err) {
    console.error('\n❌ Lỗi:', err.message);
    console.error(err.stack);
  } finally {
    await pool.end();
  }
}

generateMockInteractions();
