/**
 * Order Detail Repository
 */
class OrderDetailRepository {
  constructor(pool) {
    this.pool = pool;
  }

  async findByOrderId(orderId) {
    const query = 'SELECT * FROM sale_order_detail WHERE order_id = $1';
    const { rows } = await this.pool.query(query, [orderId]);
    return rows;
  }

  async findByOrderIds(orderIds) {
    if (!orderIds || orderIds.length === 0) return [];
    const query = 'SELECT * FROM sale_order_detail WHERE order_id = ANY($1) ORDER BY order_id, id';
    const { rows } = await this.pool.query(query, [orderIds]);
    return rows;
  }

  async addDetailWithClient(client, orderId, data) {
    const { product_id, product_name, batch_id, quantity, unit_price, total_price } = data;
    const query = `
        INSERT INTO sale_order_detail 
        (order_id, product_id, product_name, batch_id, quantity, unit_price, total_price)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING *
      `;
    const { rows } = await client.query(query, [
      orderId, product_id || null, product_name, batch_id, quantity, unit_price, total_price
    ]);
    return rows[0];
  }

  /**
   * Aggregate sales by product — SQL GROUP BY, returns compact data
   * Used by statistics-service to avoid loading all raw order details
   */
  async aggregateProductSales(storeId, { startDate, endDate }) {
    const query = `
        SELECT 
          d.product_id,
          d.product_name,
          SUM(d.quantity) AS total_quantity,
          SUM(d.total_price) AS total_revenue,
          COUNT(DISTINCT d.order_id) AS order_count
        FROM sale_order_detail d
        INNER JOIN sale_order o ON d.order_id = o.id
        WHERE o.store_id = $1
          AND o.status = 'delivered'
          AND o.payment_status = 'paid'
          AND o.order_date >= $2
          AND o.order_date <= $3
        GROUP BY d.product_id, d.product_name
        ORDER BY total_revenue DESC
      `;
    const { rows } = await this.pool.query(query, [storeId, startDate, endDate]);
    return rows;
  }

  /**
   * Delete all details for an order (used in draft item editing)
   * CASCADE would handle this on order delete, but we need explicit delete for item replacement
   */
  async deleteByOrderIdWithClient(client, orderId) {
    const query = 'DELETE FROM sale_order_detail WHERE order_id = $1 RETURNING *';
    const { rows } = await client.query(query, [orderId]);
    return rows.length;
  }
}

module.exports = OrderDetailRepository;
