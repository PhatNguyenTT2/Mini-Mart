/**
 * test-e2e-demo.js
 * E2E WebSocket Test Suite for POSMART Chatbot Demo Pipeline.
 * Simulates browser interactions for the 4 ACTs defined in the demo script.
 */

const { io } = require('socket.io-client');
const jwt = require('jsonwebtoken');

const JWT_SECRET = process.env.JWT_SECRET || 'e3ff5f077839c1331b1d893a728246685cb7dba9e3a77bffe7d52eaccf660988';
const CHATBOT_URL = process.env.CHATBOT_URL || 'http://localhost:3008';

const createToken = (userId, role = 'Customer') => {
  return jwt.sign({
    id: userId,
    role: role,
    roleName: role,
    storeId: 1
  }, JWT_SECRET);
};

const colors = {
  reset: "\x1b[0m",
  green: "\x1b[32m",
  red: "\x1b[31m",
  yellow: "\x1b[33m",
  cyan: "\x1b[36m",
  magenta: "\x1b[35m",
  bright: "\x1b[1m"
};

// Helper: wrap socket connection and interaction in promises
function connectSocket(token) {
  return new Promise((resolve, reject) => {
    const socket = io(CHATBOT_URL, {
      path: '/ws/chat',
      auth: { token },
      transports: ['websocket']
    });

    socket.on('connect', () => {
      resolve(socket);
    });

    socket.on('connect_error', (err) => {
      reject(err);
    });
  });
}

function sendAndAwaitResponse(socket, sessionId, message) {
  return new Promise((resolve, reject) => {
    let streamCompleteReceived = false;

    // Set safety timeout of 10s
    const timeout = setTimeout(() => {
      if (!streamCompleteReceived) {
        socket.off('chat:stream_complete');
        reject(new Error(`Timeout waiting for stream response to: "${message}"`));
      }
    }, 10000);

    socket.on('chat:stream_complete', (data) => {
      if (data.session_id === sessionId) {
        streamCompleteReceived = true;
        clearTimeout(timeout);
        socket.off('chat:stream_complete');
        resolve(data);
      }
    });

    socket.emit('chat:send_message', { session_id: sessionId, message });
  });
}

function joinSession(socket) {
  return new Promise((resolve, reject) => {
    socket.emit('chat:join_session', {}, (response) => {
      if (response && response.success) {
        resolve(response.data.sessionId);
      } else {
        const errMsg = response?.error?.message || JSON.stringify(response) || 'Unknown error';
        reject(new Error(`Failed to join chat session: ${errMsg}`));
      }
    });
  });
}

async function runTests() {
  console.log(`\n${colors.bright}${colors.magenta}====================================================`);
  console.log(`🚀 POSMART CHATBOT E2E DEMO TEST SUITE`);
  console.log(`====================================================${colors.reset}\n`);

  let passedCount = 0;
  let failedCount = 0;

  const assert = (condition, message) => {
    if (condition) {
      console.log(`   ${colors.green}✓ PASS: ${message}${colors.reset}`);
      passedCount++;
    } else {
      console.log(`   ${colors.red}✗ FAIL: ${message}${colors.reset}`);
      failedCount++;
    }
  };

  try {
    // ==========================================
    // ACT 1: Semantic Search — Content-Based (α)
    // ==========================================
    console.log(`${colors.cyan}--- ACT 1: Content-Based ("Tôi muốn mua đồ ăn vặt") ---${colors.reset}`);
    const token11 = createToken(11);
    const socket11 = await connectSocket(token11);
    const session11 = await joinSession(socket11);

    console.log(`Connected customer 11. Joined session: ${session11}`);

    const act1Res = await sendAndAwaitResponse(socket11, session11, "Tôi muốn mua đồ ăn vặt");

    assert(act1Res.intent === "RECOMMENDATION", "Intent should be resolve to RECOMMENDATION");
    assert(act1Res.products && act1Res.products.length >= 3, `Should return at least 3 products (got ${act1Res.products?.length || 0})`);

    // Assert the categories/names of the top slots match snacking items
    const topProductNames = act1Res.products?.slice(0, 3).map(p => p.name) || [];
    console.log(`   Top 3 products: ${JSON.stringify(topProductNames)}`);

    const hasSnackMatch = act1Res.products?.slice(0, 3).some(p =>
      p.name.toLowerCase().includes('đậu phộng') ||
      p.name.toLowerCase().includes('hạt điều') ||
      p.name.toLowerCase().includes('khô gà') ||
      p.name.toLowerCase().includes('snack') ||
      p.name.toLowerCase().includes('bánh')
    );
    assert(hasSnackMatch, "Top 3 products should contain snack/nut/dry food items");

    // ==========================================
    // ACT 2: Association Rules — Apriori (γ)
    // ==========================================
    console.log(`\n${colors.cyan}--- ACT 2: Apriori Cross-sell ("Tôi muốn mua bia Heineken") ---${colors.reset}`);
    const act2Res = await sendAndAwaitResponse(socket11, session11, "Tôi muốn mua bia Heineken");
    assert(act2Res.products && act2Res.products.length > 0, "Should return recommended products");

    // Check for cross-sell (e.g. snack or dry food combined via apriori rules)
    console.log(`   Products: ${JSON.stringify(act2Res.products?.map(p => `${p.name} (${p.ensemble_sources || 'none'})`))}`);

    const hasBia = act2Res.products?.some(p => p.name.includes('Bia Heineken'));
    assert(hasBia, "Should contain Bia Heineken");

    const hasAprioriSource = act2Res.products?.some(p => p.ensemble_sources?.includes('apriori'));
    assert(hasAprioriSource, "Should feature products sourced or enriched by 'apriori'");

    // ==========================================
    // ACT 3: Collaborative Filtering (β)
    // ==========================================
    console.log(`\n${colors.cyan}--- ACT 3: Collaborative Filtering ("Gợi ý cho tôi vài món") ---${colors.reset}`);
    // User 30 is student (buys snacks, mì gói, coca). Let's connect as User 30
    const token30 = createToken(30);
    const socket30 = await connectSocket(token30);
    const session30 = await joinSession(socket30);

    const act3Res = await sendAndAwaitResponse(socket30, session30, "Gợi ý cho tôi vài món");
    console.log(`   Products: ${JSON.stringify(act3Res.products?.map(p => `${p.name} (${p.ensemble_sources || 'none'})`))}`);

    assert(act3Res.intent === "RECOMMENDATION", "Intent should be RECOMMENDATION");
    const hasCFSource = act3Res.products?.some(p => p.ensemble_sources?.includes('cf'));
    assert(hasCFSource, "Should return personalized items via Collaborative Filtering (cf)");

    // ==========================================
    // ACT 4: Short-term Context — Session (δ)
    // ==========================================
    console.log(`\n${colors.cyan}--- ACT 4: Session Context (3-turn Lẩu Thái flow) ---${colors.reset}`);
    const token12 = createToken(12);
    const socket12 = await connectSocket(token12);
    const session12 = await joinSession(socket12);

    console.log("   Turn 1: 'Tôi muốn nấu lẩu Thái cuối tuần'");
    const turn1Res = await sendAndAwaitResponse(socket12, session12, "Tôi muốn nấu lẩu Thái cuối tuần");
    assert(turn1Res.products && turn1Res.products.length > 0, "Should return lẩu starters");

    console.log("   Turn 2: 'Gợi ý rau ăn kèm lẩu đi'");
    const turn2Res = await sendAndAwaitResponse(socket12, session12, "Gợi ý rau ăn kèm lẩu đi");
    const topRau = turn2Res.products?.map(p => p.name) || [];
    console.log(`   Rau results: ${JSON.stringify(topRau)}`);
    assert(topRau.some(r => r.toLowerCase().includes('rau') || r.toLowerCase().includes('cải') || r.toLowerCase().includes('nấm')), "Should offer vegetables like raw muống, cải or nấm");

    console.log("   Turn 3: 'Gợi ý thêm đi'");
    const turn3Res = await sendAndAwaitResponse(socket12, session12, "Gợi ý thêm đi");
    console.log(`   Turn 3 results: ${JSON.stringify(turn3Res.products?.map(p => `${p.name} (${p.ensemble_sources || 'none'})`))}`);

    assert(turn3Res.products && turn3Res.products.length > 0, "Should return continuation products");
    const hasSessionSource = turn3Res.products?.some(p => p.ensemble_sources?.includes('session'));
    assert(hasSessionSource, "Should boost session context category (lẩu) products with 'session' badge");

    // Clean up connections
    socket11.disconnect();
    socket30.disconnect();
    socket12.disconnect();

    console.log(`\n${colors.bright}${colors.magenta}====================================================`);
    console.log(`🏁 TEST RESULTS SUMMARY`);
    console.log(`   🟢 PASSED: ${passedCount}`);
    console.log(`   🔴 FAILED: ${failedCount}`);
    console.log(`====================================================${colors.reset}\n`);

    if (failedCount > 0) {
      process.exit(1);
    }
  } catch (e) {
    console.error(`${colors.red}Test run aborted with exception: ${e.message}`, e);
    process.exit(1);
  }
}

runTests();
