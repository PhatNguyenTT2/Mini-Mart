/**
 * Customer Data Seeding Script (v2 Scaled)
 * Target Database: AUTH_DATABASE_URL (Supabase Auth Dedicated DB)
 * 
 * Generates 5,000 mock users across 8 distinct persona clusters:
 *  - 1,000 Nội trợ (Homemaker): Female 85%, 28-55y (IDs 1–1000)
 *  - 1,000 Sinh viên (Student): Mixed 50/50, 18-25y (IDs 1001–2000)
 *  -   750 Dân nhậu (Drinker): Male 90%, 25-45y (IDs 2001–2750)
 *  -   500 Khách vãng lai (Walk-in): Mixed 50/50, 18-65y (IDs 2751–3250)
 *  -   650 Dân văn phòng (Office Worker): Female 60%, 24-40y (IDs 3251–3900)
 *  -   400 Dân Gym/Thể thao (Gym Enthusiast): Male 70%, 20-35y (IDs 3901–4300)
 *  -   400 Người cao tuổi (Senior): Female 55%, 55-75y (IDs 4301–4700)
 *  -   300 Tech/Geek: Male 80%, 22-35y (IDs 4701–5000)
 * 
 * Usage: node backend/docs/chatbot/catalog-bootstrap/seed-customers-v2.js
 */

const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');

// 1. Load .env from backend root
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

const AUTH_DATABASE_URL = process.env.AUTH_DATABASE_URL || process.env.DATABASE_URL;
if (!AUTH_DATABASE_URL) {
  console.error('❌ AUTH_DATABASE_URL not found in .env');
  process.exit(1);
}

const pool = new Pool({
  connectionString: AUTH_DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

// Vietnamese Name Components
const LAST_NAMES = ['Nguyễn', 'Trần', 'Lê', 'Phạm', 'Hoàng', 'Huỳnh', 'Phan', 'Vũ', 'Võ', 'Đặng', 'Bùi', 'Đỗ', 'Hồ', 'Ngô', 'Dương', 'Lý'];
const MIDDLE_MALE = ['Văn', 'Hữu', 'Đức', 'Thành', 'Minh', 'Quang', 'Đình', 'Hoàng', 'Thái', 'Trọng', 'Tuấn'];
const MIDDLE_FEMALE = ['Thị', 'Ngọc', 'Phương', 'Thảo', 'Thanh', 'Khánh', 'Minh', 'Thu', 'Anh', 'Tú'];

const FIRST_MALE = ['Anh', 'Bình', 'Cường', 'Dũng', 'Đạt', 'Đức', 'Hải', 'Hiếu', 'Hùng', 'Huy', 'Khoa', 'Lam', 'Long', 'Minh', 'Nam', 'Nghĩa', 'Phúc', 'Quân', 'Sơn', 'Tài', 'Tâm', 'Thắng', 'Thành', 'Cảnh', 'Tuấn', 'Việt'];
const FIRST_FEMALE = ['Anh', 'Bích', 'Châu', 'Dung', 'Hà', 'Hạnh', 'Hoa', 'Hương', 'Hằng', 'Lan', 'Linh', 'Mai', 'Ngân', 'Nhi', 'Nhung', 'Oanh', 'Phương', 'Quỳnh', 'Thảo', 'Trang', 'Trinh', 'Tuyết', 'Vân', 'Yến'];

const ADDRESS_HOUSEWIFE = [
  '12 Lê Văn Sỹ, Phường 13, Quận 3, TP.HCM',
  '45 Nguyễn Trãi, Phường Bến Thành, Quận 1, TP.HCM',
  '88 Phan Xích Long, Phường 2, Quận Phú Nhuận, TP.HCM',
  '102 Điện Biên Phủ, Phường 15, Quận Bình Thạnh, TP.HCM',
  '55 Võ Văn Ngân, Phường Bình Thọ, TP. Thủ Đức, TP.HCM',
  '23 Hoàng Hoa Thám, Phường 13, Quận Tân Bình, TP.HCM',
  '67 Trần Hưng Đạo, Phường 5, Quận 5, TP.HCM',
  '14 Nguyễn Thị Minh Khai, Phường Đa Kao, Quận 1, TP.HCM'
];

const ADDRESS_STUDENT = [
  'KTX Khu A ĐHQG, Phường Linh Trung, TP. Thủ Đức, TP.HCM',
  '268 Lý Thường Kiệt, Phường 14, Quận 10, TP.HCM',
  '120 Hoàng Diệu 2, Phường Linh Chiểu, TP. Thủ Đức, TP.HCM',
  '450 Lê Văn Việt, Phường Tăng Nhơn Phú A, TP. Thủ Đức, TP.HCM',
  '15 Nguyễn Kiệm, Phường 3, Quận Gò Vấp, TP.HCM',
  '89 Đinh Bộ Lĩnh, Phường 26, Quận Bình Thạnh, TP.HCM',
  '34 Đường D2, Phường 25, Quận Bình Thạnh, TP.HCM'
];

const ADDRESS_DRINKER = [
  '78 Bùi Viện, Phường Phạm Ngũ Lão, Quận 1, TP.HCM',
  '156 Phạm Văn Đồng, Phường 1, Quận Gò Vấp, TP.HCM',
  '234 Hoàng Sa, Phường 5, Quận Tân Bình, TP.HCM',
  '89 Trường Sa, Phường 14, Quận 3, TP.HCM',
  '45 Vĩnh Khánh, Phường 8, Quận 4, TP.HCM',
  '112 Tô Hiến Thành, Phường 15, Quận 10, TP.HCM'
];

const ADDRESS_WALKIN = [
  '15 Lê Đại Hành, Phường 15, Quận 11, TP.HCM',
  '78 Cách Mạng Tháng 8, Phường 6, Quận 3, TP.HCM',
  '23 Hậu Giang, Phường 4, Quận 6, TP.HCM',
  '56 Lạc Long Quân, Phường 3, Quận 11, TP.HCM',
  '89 Ba Tháng Hai, Phường 11, Quận 10, TP.HCM'
];

const ADDRESS_OFFICE = [
  '33 Lê Duẩn, Phường Bến Nghé, Quận 1, TP.HCM',
  '72 Lê Thánh Tôn, Phường Bến Nghé, Quận 1, TP.HCM',
  '81 Nguyễn Hữu Cảnh, Phường 22, Quận Bình Thạnh, TP.HCM',
  '180 Nguyễn Thị Minh Khai, Phường 6, Quận 3, TP.HCM',
  '18A Cộng Hòa, Phường 4, Quận Tân Bình, TP.HCM'
];

const ADDRESS_GYM = [
  '215 Võ Văn Ngân, Phường Bình Thọ, TP. Thủ Đức, TP.HCM',
  '145 Quang Trung, Phường 10, Quận Gò Vấp, TP.HCM',
  '350 Sư Vạn Hạnh, Phường 12, Quận 10, TP.HCM',
  '99 Nguyễn Xí, Phường 26, Quận Bình Thạnh, TP.HCM'
];

const ADDRESS_SENIOR = [
  '45 Lý Thường Kiệt, Phường 7, Quận Tân Bình, TP.HCM',
  '112 Âu Cơ, Phường 14, Quận 11, TP.HCM',
  '88 Hải Thượng Lãn Ông, Phường 10, Quận 5, TP.HCM',
  '234 Trần Hưng Đạo, Phường 11, Quận 5, TP.HCM'
];

const ADDRESS_TECH = [
  'Đường D1, Khu Công Nghệ Cao, TP. Thủ Đức, TP.HCM',
  '54 Nguyễn Thị Minh Khai, Phường Đa Kao, Quận 1, TP.HCM',
  '123 Nam Kỳ Khởi Nghĩa, Phường 7, Quận 3, TP.HCM'
];

function getRandomItem(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function getRandomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function generateVietnameseName(gender) {
  const last = getRandomItem(LAST_NAMES);
  if (gender === 'Male') {
    const middle = getRandomItem(MIDDLE_MALE);
    const first = getRandomItem(FIRST_MALE);
    return `${last} ${middle} ${first}`;
  } else {
    const middle = getRandomItem(MIDDLE_FEMALE);
    const first = getRandomItem(FIRST_FEMALE);
    return `${last} ${middle} ${first}`;
  }
}

function generatePhone(idx) {
  const prefixes = ['090', '091', '093', '097', '098', '032', '035', '038', '070', '077', '083', '085'];
  const pref = prefixes[idx % prefixes.length];
  const rest = String(idx).padStart(7, '0');
  return `${pref}${rest.substring(0, 7)}`;
}

function generateDob(minAge, maxAge) {
  const currentYear = 2026;
  const birthYear = currentYear - getRandomInt(minAge, maxAge);
  const month = String(getRandomInt(1, 12)).padStart(2, '0');
  const day = String(getRandomInt(1, 28)).padStart(2, '0');
  return `${birthYear}-${month}-${day}`;
}

async function seedCustomers() {
  console.log('🔌 Connecting to Auth DB on Supabase...');
  const client = await pool.connect();

  try {
    await client.query('BEGIN');

    // 1. Find Customer Role ID
    const roleRes = await client.query("SELECT id FROM role WHERE name = 'Customer'");
    let roleId;
    if (roleRes.rows.length === 0) {
      console.log("Creating 'Customer' role in Auth DB...");
      const newRole = await client.query("INSERT INTO role (name, description) VALUES ('Customer', 'Customer self-service') RETURNING id");
      roleId = newRole.rows[0].id;
    } else {
      roleId = roleRes.rows[0].id;
    }

    console.log(`📌 Customer Role ID: ${roleId}`);

    // 2. Clear existing customer profiles & customer user_accounts with RESTART IDENTITY
    console.log('🧹 Clearing old customer data (TRUNCATE customer & user_account RESTART IDENTITY CASCADE)...');
    await client.query('TRUNCATE TABLE customer RESTART IDENTITY CASCADE');
    await client.query("DELETE FROM user_account WHERE role_id = $1 OR username LIKE 'customer_%'", [roleId]);

    // Reset user_account sequence
    await client.query("SELECT setval(pg_get_serial_sequence('user_account', 'id'), (SELECT COALESCE(MAX(id), 1) FROM user_account))");

    // 3. Define 5,000 Personas across 8 Clusters
    const TOTAL_USERS = 5000;
    const customersToInsert = [];

    for (let i = 1; i <= TOTAL_USERS; i++) {
      let gender, minAge, maxAge, addressList, personaLabel;

      if (i <= 1000) {
        // 0. Homemaker (85% Female, 28-55y)
        gender = Math.random() < 0.85 ? 'Female' : 'Male';
        minAge = 28; maxAge = 55;
        addressList = ADDRESS_HOUSEWIFE;
        personaLabel = 'housewife';
      } else if (i <= 2000) {
        // 1. Student (50% Female, 18-25y)
        gender = Math.random() < 0.5 ? 'Female' : 'Male';
        minAge = 18; maxAge = 25;
        addressList = ADDRESS_STUDENT;
        personaLabel = 'student';
      } else if (i <= 2750) {
        // 2. Drinker (90% Male, 25-45y)
        gender = Math.random() < 0.9 ? 'Male' : 'Female';
        minAge = 25; maxAge = 45;
        addressList = ADDRESS_DRINKER;
        personaLabel = 'drinker';
      } else if (i <= 3250) {
        // 3. Walk-in (50% Female, 18-65y)
        gender = Math.random() < 0.5 ? 'Female' : 'Male';
        minAge = 18; maxAge = 65;
        addressList = ADDRESS_WALKIN;
        personaLabel = 'walkin';
      } else if (i <= 3900) {
        // 4. Office Worker (60% Female, 24-40y)
        gender = Math.random() < 0.6 ? 'Female' : 'Male';
        minAge = 24; maxAge = 40;
        addressList = ADDRESS_OFFICE;
        personaLabel = 'office';
      } else if (i <= 4300) {
        // 5. Gym Enthusiast (70% Male, 20-35y)
        gender = Math.random() < 0.7 ? 'Male' : 'Female';
        minAge = 20; maxAge = 35;
        addressList = ADDRESS_GYM;
        personaLabel = 'gym';
      } else if (i <= 4700) {
        // 6. Senior (55% Female, 55-75y)
        gender = Math.random() < 0.55 ? 'Female' : 'Male';
        minAge = 55; maxAge = 75;
        addressList = ADDRESS_SENIOR;
        personaLabel = 'senior';
      } else {
        // 7. Tech/Geek (80% Male, 22-35y)
        gender = Math.random() < 0.8 ? 'Male' : 'Female';
        minAge = 22; maxAge = 35;
        addressList = ADDRESS_TECH;
        personaLabel = 'tech';
      }

      const fullName = generateVietnameseName(gender);
      const phone = generatePhone(i);
      const dob = generateDob(minAge, maxAge);
      const address = getRandomItem(addressList);
      const username = `customer_${i}`;
      const email = `customer_${i}@minimart.vn`;
      const passwordHash = '$2b$10$6YtVsO.S8Li3CWQD7sjx1eYGDGnVRlVMqr9Yyz3sk.34LXOmgCRaq';

      customersToInsert.push({
        id: i,
        username,
        email,
        passwordHash,
        fullName,
        phone,
        address,
        gender,
        dob,
        customerType: 'retail',
        personaLabel
      });
    }

    console.log(`⚡ Seeding ${customersToInsert.length} mock customers across 8 persona clusters in multi-row SQL chunks...`);

    // 4. Optimized Multi-row Batch Insert (500 users per SQL chunk)
    const CHUNK_SIZE = 500;
    for (let c = 0; c < customersToInsert.length; c += CHUNK_SIZE) {
      const chunk = customersToInsert.slice(c, c + CHUNK_SIZE);

      // Batch insert user_account
      const userValues = [];
      const userParams = [];
      let upi = 1;
      for (const u of chunk) {
        userValues.push(`($${upi}, $${upi + 1}, $${upi + 2}, $${upi + 3}, TRUE)`);
        userParams.push(u.username, u.email, u.passwordHash, roleId);
        upi += 4;
      }

      const userRes = await client.query(
        `INSERT INTO user_account (username, email, password_hash, role_id, is_active)
         VALUES ${userValues.join(', ')} RETURNING id, username`,
        userParams
      );

      // Map username -> userId
      const userMap = {};
      userRes.rows.forEach(r => userMap[r.username] = r.id);

      // Batch insert customer
      const custValues = [];
      const custParams = [];
      let cpi = 1;
      for (const u of chunk) {
        const userId = userMap[u.username];
        custValues.push(`($${cpi}, $${cpi + 1}, $${cpi + 2}, $${cpi + 3}, $${cpi + 4}, $${cpi + 5}, $${cpi + 6}, 0, $${cpi + 7}, TRUE)`);
        custParams.push(u.id, userId, u.fullName, u.phone, u.address, u.gender, u.dob, u.customerType);
        cpi += 8;
      }

      await client.query(
        `INSERT INTO customer (id, user_id, full_name, phone, address, gender, dob, total_spent, customer_type, is_active)
         OVERRIDING SYSTEM VALUE
         VALUES ${custValues.join(', ')}`,
        custParams
      );
    }

    // Reset sequences
    await client.query("SELECT setval(pg_get_serial_sequence('customer', 'id'), (SELECT MAX(id) FROM customer))");
    await client.query("SELECT setval(pg_get_serial_sequence('user_account', 'id'), (SELECT MAX(id) FROM user_account))");

    await client.query('COMMIT');

    console.log(`✅ Successfully seeded 5,000 customers into AUTH_DATABASE_URL!`);

    // Verification queries
    const countRes = await client.query('SELECT COUNT(*) FROM customer');
    const userCountRes = await client.query('SELECT COUNT(*) FROM user_account WHERE role_id = $1', [roleId]);
    console.log(`📊 Auth DB Verification:`);
    console.log(`   - Customer Profiles in DB: ${countRes.rows[0].count}`);
    console.log(`   - Customer User Accounts in DB: ${userCountRes.rows[0].count}`);

  } catch (err) {
    await client.query('ROLLBACK');
    console.error('❌ Failed to seed customers:', err);
    process.exit(1);
  } finally {
    client.release();
    await pool.end();
  }
}

seedCustomers();
