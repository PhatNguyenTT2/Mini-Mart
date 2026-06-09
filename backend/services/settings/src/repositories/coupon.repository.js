class CouponRepository {
  constructor(pool) {
    this.pool = pool;
  }

  async findByCode(code) {
    const { rows } = await this.pool.query(
      'SELECT * FROM coupons WHERE code = $1',
      [code]
    );
    return rows[0] || null;
  }

  async findAvailable() {
    const { rows } = await this.pool.query(
      `SELECT * FROM coupons 
       WHERE is_active = TRUE 
         AND is_public = TRUE 
         AND (starts_at IS NULL OR starts_at <= NOW())
         AND (expires_at IS NULL OR expires_at > NOW())
       ORDER BY created_at DESC`
    );
    return rows;
  }

  async findAll({ page = 1, limit = 20, search, isActive } = {}) {
    const offset = (page - 1) * limit;
    const conditions = [];
    const params = [];

    if (isActive !== undefined && isActive !== '') {
      params.push(isActive === 'true' || isActive === true);
      conditions.push(`is_active = $${params.length}`);
    }

    if (search) {
      params.push(`%${search}%`);
      conditions.push(`(code ILIKE $${params.length} OR description ILIKE $${params.length})`);
    }

    const where = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
    const countQuery = `SELECT COUNT(*)::int FROM coupons ${where}`;
    const dataQuery = `
      SELECT * FROM coupons 
      ${where} 
      ORDER BY id DESC 
      LIMIT $${params.length + 1} OFFSET $${params.length + 2}`;

    const [countResult, dataResult] = await Promise.all([
      this.pool.query(countQuery, params),
      this.pool.query(dataQuery, [...params, limit, offset])
    ]);

    return {
      items: dataResult.rows,
      total: countResult.rows[0].count
    };
  }

  async create({ code, description, discountType, discountValue, minOrderAmount, maxUses, isPublic, startsAt, expiresAt, createdBy }) {
    const { rows } = await this.pool.query(
      `INSERT INTO coupons (
        code, description, discount_type, discount_value, min_order_amount, 
        max_uses, is_public, starts_at, expires_at, created_by
       ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
       RETURNING *`,
      [
        code, description, discountType || 'percent', discountValue || 0, minOrderAmount || 0,
        maxUses || null, isPublic !== false, startsAt || null, expiresAt || null, createdBy || null
      ]
    );
    return rows[0];
  }

  async update(id, data) {
    const updates = [];
    const params = [];
    let idx = 1;

    const allowedFields = {
      code: 'code',
      description: 'description',
      discountType: 'discount_type',
      discountValue: 'discount_value',
      minOrderAmount: 'min_order_amount',
      maxUses: 'max_uses',
      isPublic: 'is_public',
      isActive: 'is_active',
      startsAt: 'starts_at',
      expiresAt: 'expires_at'
    };

    params.push(id);
    const idIdx = idx++;

    for (const [key, value] of Object.entries(data)) {
      const dbCol = allowedFields[key];
      if (dbCol) {
        updates.push(`${dbCol} = $${idx++}`);
        params.push(value);
      }
    }

    if (!updates.length) {
      const { rows } = await this.pool.query('SELECT * FROM coupons WHERE id = $1', [id]);
      return rows[0] || null;
    }

    const query = `UPDATE coupons SET ${updates.join(', ')} WHERE id = $${idIdx} RETURNING *`;
    const { rows } = await this.pool.query(query, params);
    return rows[0] || null;
  }

  async softDelete(id) {
    const { rows } = await this.pool.query(
      'UPDATE coupons SET is_active = FALSE WHERE id = $1 RETURNING *',
      [id]
    );
    return rows[0] || null;
  }

  async incrementUsedCount(client, id) {
    const executor = client || this.pool;
    const { rows } = await executor.query(
      'UPDATE coupons SET used_count = used_count + 1 WHERE id = $1 RETURNING *',
      [id]
    );
    return rows[0] || null;
  }

  async logUsage(client, { couponId, customerId, orderId }) {
    const executor = client || this.pool;
    const { rows } = await executor.query(
      `INSERT INTO coupon_usages (coupon_id, customer_id, order_id) 
       VALUES ($1, $2, $3) 
       RETURNING *`,
      [couponId, customerId, orderId || null]
    );
    return rows[0];
  }

  async getCustomerUsageCount(couponId, customerId) {
    const { rows } = await this.pool.query(
      'SELECT COUNT(*)::int FROM coupon_usages WHERE coupon_id = $1 AND customer_id = $2',
      [couponId, customerId]
    );
    return rows[0].count;
  }

  async getUsageHistory(couponId, { page = 1, limit = 20 } = {}) {
    const offset = (page - 1) * limit;
    const countQuery = 'SELECT COUNT(*)::int FROM coupon_usages WHERE coupon_id = $1';

    // In our system, customer information might live in auth DB.
    // The settings service coupon_usages keeps customerID. We will query usage first, 
    // the caller service (or UI) can resolve customer names or we can join if we sync.
    // For now we just return standard usage info.
    const dataQuery = `
      SELECT * FROM coupon_usages 
      WHERE coupon_id = $1 
      ORDER BY used_at DESC 
      LIMIT $2 OFFSET $3`;

    const [countRes, dataRes] = await Promise.all([
      this.pool.query(countQuery, [couponId]),
      this.pool.query(dataQuery, [couponId, limit, offset])
    ]);

    return {
      items: dataRes.rows,
      total: countRes.rows[0].count
    };
  }
}

module.exports = CouponRepository;
