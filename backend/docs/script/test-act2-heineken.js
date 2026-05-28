/**
 * Test Act 2: "Tôi muốn mua bia Heineken"
 * Verifies Apriori cross-sell products appear correctly.
 *
 * Expected: Coca-Cola (#19), Khô gà (#21), Snack Lay's (#20)
 * NOT expected: Nấm kim châm (#2), Gia vị nêm sẵn lẩu (#4)
 */
require('dotenv').config();
const { io } = require('socket.io-client');
const jwt = require('jsonwebtoken');

const JWT_SECRET = process.env.JWT_SECRET || 'e3ff5f077839c1331b1d893a728246685cb7dba9e3a77bffe7d52eaccf660988';
const CHATBOT_URL = process.env.CHATBOT_URL || 'http://localhost:3008';

const createToken = (userId, role = 'Customer') =>
  jwt.sign({ id: userId, role, roleName: role, storeId: 1 }, JWT_SECRET);

const EXPECTED_APRIORI_IDS = new Set([19, 21, 20]); // Coca, Kho ga, Snack
const UNEXPECTED_APRIORI_IDS = new Set([2, 4]);      // Nam kim cham, Gia vi

async function main() {
  console.log('\n=== TEST ACT 2: Bia Heineken Apriori Cross-sell ===\n');

  const token = createToken(11);
  const socket = io(CHATBOT_URL, {
    path: '/ws/chat', auth: { token }, transports: ['websocket']
  });

  await new Promise((res, rej) => { socket.on('connect', res); socket.on('connect_error', rej); });
  console.log('Connected');

  const sessionId = await new Promise((res, rej) => {
    socket.emit('chat:join_session', {}, r => r?.success ? res(r.data.sessionId) : rej(new Error(`Join failed`)));
  });
  console.log(`Session: ${sessionId}`);

  // Unicode escapes for Vietnamese diacritics (avoid encoding issues on Windows)
  const MESSAGE = 'T\u00f4i mu\u1ed1n mua bia Heineken';
  console.log(`Sending: "${MESSAGE}"\n`);

  const resp = await new Promise((res, rej) => {
    const t = setTimeout(() => rej(new Error('Timeout 30s')), 30000);
    socket.on('chat:stream_complete', d => { if (d.session_id === sessionId) { clearTimeout(t); res(d); } });
    socket.emit('chat:send_message', { session_id: sessionId, message: MESSAGE });
  });

  const products = resp.products || [];
  let pass = 0, fail = 0;

  const assert = (ok, msg) => { ok ? (console.log(`  PASS: ${msg}`), pass++) : (console.log(`  FAIL: ${msg}`), fail++); };

  // 1. Intent
  assert(resp.intent === 'RECOMMENDATION', `Intent = ${resp.intent} (expected RECOMMENDATION)`);

  // 2. Has products
  assert(products.length >= 3, `${products.length} products returned (expected >= 3)`);

  // Show products
  console.log('\n  Products:');
  products.forEach(p => {
    const src = (p.ensemble_sources || []).join(',');
    console.log(`    #${p.id} [${src}] ${(p.name || '').slice(0, 45)}`);
  });
  console.log('');

  const allIds = new Set(products.map(p => p.id));
  const aprioriProducts = products.filter(p => (p.ensemble_sources || []).includes('apriori'));
  const aprioriIds = new Set(aprioriProducts.map(p => p.id));

  // 3. At least 1 expected product present
  const expectedFound = [...EXPECTED_APRIORI_IDS].filter(id => allIds.has(id));
  assert(expectedFound.length >= 1, `Found ${expectedFound.length}/3 expected (Coca #19, Kho ga #21, Snack #20): [${expectedFound}]`);

  // 4. No unexpected in Apriori slots
  const unexpectedFound = [...UNEXPECTED_APRIORI_IDS].filter(id => aprioriIds.has(id));
  assert(unexpectedFound.length === 0, `No unexpected in Apriori slots (Nam #2, Gia vi #4). Found: [${unexpectedFound}]`);

  // 5. Heineken is top product
  assert(products[0]?.id === 17, `Top product = #${products[0]?.id} (expected #17 Heineken)`);

  console.log(`\n=== RESULT: ${pass} PASSED, ${fail} FAILED ===\n`);
  socket.disconnect();
  process.exit(fail === 0 ? 0 : 1);
}

main().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
