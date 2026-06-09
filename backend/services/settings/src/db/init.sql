-- ============================================================
-- Service 4: Settings Service
-- Database initialization script
-- ============================================================

-- 1. SECURITY SETTINGS (Singleton)
CREATE TABLE IF NOT EXISTS security_settings (
    id INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    max_failed_attempts INT NOT NULL DEFAULT 5,
    lock_duration_minutes INT NOT NULL DEFAULT 30,
    updated_by BIGINT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed Default Security Settings
INSERT INTO security_settings (id, max_failed_attempts, lock_duration_minutes)
VALUES (1, 5, 30)
ON CONFLICT (id) DO NOTHING;

-- 2. SALES SETTINGS (Singleton)
CREATE TABLE IF NOT EXISTS sales_settings (
    id INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    auto_promotion_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    promotion_start_time TIME,
    promotion_discount_percentage NUMERIC NOT NULL DEFAULT 0,
    discount_retail NUMERIC NOT NULL DEFAULT 0,
    discount_wholesale NUMERIC NOT NULL DEFAULT 5,
    discount_vip NUMERIC NOT NULL DEFAULT 10,
    updated_by BIGINT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed Default Sales Settings
INSERT INTO sales_settings (id, auto_promotion_enabled, promotion_start_time, promotion_discount_percentage, discount_retail, discount_wholesale, discount_vip)
VALUES (1, false, '18:00:00', 20, 0, 5, 10)
ON CONFLICT (id) DO NOTHING;

-- 3. SETTINGS HISTORY (Audit Log)
CREATE TABLE IF NOT EXISTS settings_history (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    setting_type TEXT NOT NULL CHECK (setting_type IN ('security', 'sales')),
    old_value JSONB NOT NULL,
    new_value JSONB NOT NULL,
    changed_by BIGINT,
    change_reason TEXT,
    changed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_settings_history_type ON settings_history(setting_type);
CREATE INDEX IF NOT EXISTS idx_settings_history_date ON settings_history(changed_at);

-- ==========================================
-- MIGRATION: Add expiry targeting columns to sales_settings
-- ==========================================
DO $$ BEGIN
    ALTER TABLE sales_settings ADD COLUMN apply_to_expiring_today BOOLEAN NOT NULL DEFAULT TRUE;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE sales_settings ADD COLUMN apply_to_expiring_tomorrow BOOLEAN NOT NULL DEFAULT FALSE;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

-- 4. OMNICHANNEL COUPONS AND USAGES
CREATE TABLE IF NOT EXISTS coupons (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    code TEXT NOT NULL UNIQUE,
    description TEXT,
    discount_type TEXT NOT NULL DEFAULT 'percent'
        CHECK (discount_type IN ('percent', 'fixed', 'freeship')),
    discount_value NUMERIC NOT NULL DEFAULT 0,
    min_order_amount NUMERIC NOT NULL DEFAULT 0,
    max_uses INT,
    used_count INT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_public BOOLEAN NOT NULL DEFAULT TRUE,
    starts_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_by BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS coupon_usages (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    coupon_id BIGINT NOT NULL REFERENCES coupons(id),
    customer_id BIGINT NOT NULL,
    order_id BIGINT,
    used_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed WELCOME100 freeship coupon
INSERT INTO coupons (code, description, discount_type, discount_value, is_public)
VALUES ('WELCOME100', 'Free shipping for new customers', 'freeship', 30000, true)
ON CONFLICT (code) DO NOTHING;

