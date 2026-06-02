/**
 * Script to safely delete order records created by Employee 11 acting as customer (customer_id = 11)
 * run with: node backend/scripts/clear-employee-11-orders.js
 */
const { Pool } = require('pg');
require('dotenv').config({ path: 'e:/UIT/cv/backend/backend/.env' });

async function clearEmployee11Orders() {
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) {
    console.error("❌ Error: DATABASE_URL environment variable is not defined.");
    process.exit(1);
  }

  const useSSL = process.env.DB_SSL === 'true';
  const pool = new Pool({
    connectionString: databaseUrl,
    ssl: useSSL ? { rejectUnauthorized: false } : false,
    max: 2,
    idleTimeoutMillis: 10000,
    connectionTimeoutMillis: 10000
  });

  const client = await pool.connect();

  try {
    console.log('🔗 Connected to Database via DATABASE_URL');
    console.log('🔄 Starting transaction to clear Employee 11 data...');

    await client.query('BEGIN');

    // 1. Fetch matching orders
    const { rows: orders } = await client.query(
      'SELECT id, store_id, customer_id, created_by, order_date, status, total_amount FROM sale_order WHERE customer_id = 11'
    );
    console.log(`🔍 Found ${orders.length} orders matching customer_id = 11:`);
    orders.forEach(o => {
      console.log(`   - Order ID: ${o.id}, Status: ${o.status}, Amount: ${o.total_amount}`);
    });

    if (orders.length === 0) {
      console.log('ℹ️ No orders matching customer_id = 11 found. Nothing to delete.');
      await client.query('COMMIT');
      return;
    }

    const orderIds = orders.map(o => o.id);

    // 2. Clear payments associated with these orders
    console.log('🧹 Clearing linked payment records...');
    const deletePaymentsRes = await client.query(
      "DELETE FROM payment WHERE reference_type = 'SaleOrder' AND reference_id = ANY($1) RETURNING id",
      [orderIds]
    );
    console.log(`   ✅ Cleaned up ${deletePaymentsRes.rows.length} linked payments.`);

    // 3. Clear VNPay transactions associated with payments (if any exist)
    if (deletePaymentsRes.rows.length > 0) {
      const paymentIds = deletePaymentsRes.rows.map(r => r.id);
      const deleteVnPayRes = await client.query(
        "DELETE FROM vnpay_transaction WHERE payment_id = ANY($1) RETURNING id",
        [paymentIds]
      );
      console.log(`   ✅ Cleaned up ${deleteVnPayRes.rows.length} linked VNPay transactions.`);
    }

    // 4. Delete the sales orders (Will automatically cascade delete sale_order_detail due to ON DELETE CASCADE)
    console.log('🧹 Deleting orders from sale_order (foreign details will cascade)...');
    const deleteOrdersRes = await client.query(
      'DELETE FROM sale_order WHERE customer_id = 11 RETURNING id'
    );
    console.log(`   ✅ Successfully deleted ${deleteOrdersRes.rows.length} orders.`);

    await client.query('COMMIT');
    console.log('🎉 Transaction committed successfully. Employee 11 orders cleared!');

  } catch (err) {
    await client.query('ROLLBACK');
    console.error('❌ Error during transaction processing. rolled back:', err);
  } finally {
    client.release();
    await pool.end();
    console.log('🔌 Database pool closed.');
  }
}

clearEmployee11Orders();
