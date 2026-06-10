/**
 * Batch Repository
 * Quản lý lô hàng (Multi-Tenancy)
 */
class BatchRepository {
    constructor(pool) {
        this.pool = pool;
    }

    async findAll(storeId, filters = {}) {
        let query = 'SELECT * FROM product_batch WHERE store_id = $1';
        const params = [storeId];

        if (filters.productId) {
            params.push(filters.productId);
            query += ` AND product_id = $${params.length}`;
        }
        if (filters.status) {
            params.push(filters.status);
            query += ` AND status = $${params.length}`;
        }

        query += ' ORDER BY expiry_date ASC NULLS LAST';
        const { rows } = await this.pool.query(query, params);
        return rows;
    }

    async findById(storeId, batchId) {
        const query = 'SELECT * FROM product_batch WHERE id = $1 AND store_id = $2';
        const { rows } = await this.pool.query(query, [batchId, storeId]);
        return rows[0] || null;
    }

    async create(storeId, data) {
        const { product_id, cost_price, unit_price, quantity, mfg_date, expiry_date, notes } = data;
        const query = `
            INSERT INTO product_batch 
            (store_id, product_id, cost_price, unit_price, quantity, mfg_date, expiry_date, notes)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
        `;
        const { rows } = await this.pool.query(query, [
            storeId, product_id, cost_price, unit_price, quantity, mfg_date, expiry_date, notes
        ]);
        return rows[0];
    }

    // Tạo qua transaction context
    async createWithClient(client, storeId, data) {
        const { product_id, cost_price, unit_price, quantity, mfg_date, expiry_date, notes } = data;
        const query = `
             INSERT INTO product_batch 
             (store_id, product_id, cost_price, unit_price, quantity, mfg_date, expiry_date, notes)
             VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
             RETURNING *
         `;
        const { rows } = await client.query(query, [
            storeId, product_id, cost_price, unit_price, quantity, mfg_date, expiry_date, notes
        ]);
        return rows[0];
    }

    async updateStatusWithClient(client, storeId, batchId, status) {
        const query = `
            UPDATE product_batch 
            SET status = $1
            WHERE id = $2 AND store_id = $3
            RETURNING *
        `;
        const { rows } = await client.query(query, [status, batchId, storeId]);
        return rows[0];
    }

    // Saga compensation: delete orphaned batch (CASCADE deletes inventory_item + movement)
    async deleteById(storeId, batchId) {
        const query = 'DELETE FROM product_batch WHERE id = $1 AND store_id = $2 RETURNING *';
        const { rows } = await this.pool.query(query, [batchId, storeId]);
        return rows[0] || null;
    }

    async update(storeId, batchId, data) {
        const allowedFields = [
            'cost_price', 'unit_price', 'quantity', 'mfg_date', 'expiry_date',
            'status', 'notes', 'discount_percentage', 'promotion_applied'
        ];
        const sets = [];
        const params = [storeId, batchId];

        for (const field of allowedFields) {
            let dbField = field;
            let val = data[field];

            // support camelCase mappings
            if (field === 'cost_price' && data.costPrice !== undefined) val = data.costPrice;
            if (field === 'unit_price' && data.unitPrice !== undefined) val = data.unitPrice;
            if (field === 'mfg_date' && data.mfgDate !== undefined) val = data.mfgDate;
            if (field === 'expiry_date' && data.expiryDate !== undefined) val = data.expiryDate;
            if (field === 'discount_percentage' && data.discountPercentage !== undefined) val = data.discountPercentage;
            if (field === 'promotion_applied' && data.promotionApplied !== undefined) val = data.promotionApplied;

            if (val !== undefined) {
                params.push(val);
                sets.push(`${dbField} = $${params.length}`);
            }
        }
        if (sets.length === 0) return this.findById(storeId, batchId);

        const query = `UPDATE product_batch SET ${sets.join(', ')}, updated_at = NOW()
                       WHERE id = $2 AND store_id = $1 RETURNING *`;
        const { rows } = await this.pool.query(query, params);
        return rows[0] || null;
    }

    async bulkUpdateByProduct(storeId, productId, data) {
        let discount = data.discount_percentage;
        if (discount === undefined) discount = data.discountPercentage;
        let promotion = data.promotion_applied;
        if (promotion === undefined) promotion = data.promotionApplied;

        const query = `UPDATE product_batch
                       SET discount_percentage = $3, promotion_applied = $4, updated_at = NOW()
                       WHERE store_id = $1 AND product_id = $2 AND status = 'active'
                       RETURNING *`;
        const { rows } = await this.pool.query(query, [
            storeId, productId, discount, promotion || 'manual'
        ]);
        return { updatedCount: rows.length, batches: rows };
    }
}

module.exports = BatchRepository;
