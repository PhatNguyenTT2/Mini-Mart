-- ============================================================
-- SEED DATA: Permissions + Roles + Role-Permission assignments
-- Run after init.sql (idempotent — uses ON CONFLICT)
-- ============================================================

-- 1. Clean up legacy permission 'manage_settings'
DELETE FROM role_permission WHERE permission_id = (SELECT id FROM permission WHERE code = 'manage_settings');
DELETE FROM permission WHERE code = 'manage_settings';

-- 1. Insert all system permissions
INSERT INTO permission (code, description) VALUES
  ('view_dashboard', 'View Dashboard'),
  ('manage_products', 'Manage Products'),
  ('manage_categories', 'Manage Categories'),
  ('manage_orders', 'Manage Orders'),
  ('manage_customers', 'Manage Customers'),
  ('manage_suppliers', 'Manage Suppliers'),
  ('manage_employees', 'Manage Employees'),
  ('manage_POS', 'Manage POS'),
  ('manage_roles', 'Manage Roles'),
  ('manage_inventory', 'Manage Inventory'),
  ('view_reports', 'View Reports'),
  ('manage_payments', 'Manage Payments'),
  ('manager_setting', 'Manage Site Settings (Coupons, Product Prices)'),
  ('admin_setting', 'Manage Admin Settings (Discounts, POS Security, Perishables)'),
  ('view_notifications', 'View Notifications'),
  ('pos_access', 'POS Access - Can use POS terminal with PIN')
ON CONFLICT (code) DO NOTHING;

-- 2. Create 5 system roles
INSERT INTO role (name, description) VALUES
  ('Super Admin', 'Full system access - all permissions'),
  ('Store Manager', 'Store-level management - products, orders, inventory, customers, suppliers'),
  ('Cashier', 'POS operations - process sales and payments'),
  ('Store Admin', 'Store administration - manage employees, roles, and system settings'),
  ('Customer', 'Customer self-service - view only')
ON CONFLICT (name) DO NOTHING;

-- 3. Super Admin → ALL permissions
INSERT INTO role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM role r
CROSS JOIN permission p
WHERE r.name = 'Super Admin'
  AND NOT EXISTS (
    SELECT 1 FROM role_permission rp WHERE rp.role_id = r.id
  )
ON CONFLICT DO NOTHING;

-- 4. Store Manager → store management + POS access
INSERT INTO role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM role r
CROSS JOIN permission p
WHERE r.name = 'Store Manager'
  AND p.code IN (
    'view_dashboard', 'manage_products', 'manage_categories',
    'manage_orders', 'manage_customers', 'manage_suppliers',
    'manage_inventory', 'view_reports', 'manage_payments',
    'view_notifications', 'pos_access', 'manager_setting'
  )
  AND NOT EXISTS (
    SELECT 1 FROM role_permission rp WHERE rp.role_id = r.id
  )
ON CONFLICT DO NOTHING;

-- 5. Cashier → POS operations only
INSERT INTO role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM role r
CROSS JOIN permission p
WHERE r.name = 'Cashier'
  AND p.code IN (
    'view_dashboard', 'manage_orders', 'manage_payments',
    'view_notifications', 'pos_access'
  )
  AND NOT EXISTS (
    SELECT 1 FROM role_permission rp WHERE rp.role_id = r.id
  )
ON CONFLICT DO NOTHING;

-- 6. Store Admin → admin management (no POS access)
INSERT INTO role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM role r
CROSS JOIN permission p
WHERE r.name = 'Store Admin'
  AND p.code IN (
    'view_dashboard', 'manage_employees', 'manage_roles',
    'manager_setting', 'admin_setting', 'view_reports', 'view_notifications'
  )
  AND NOT EXISTS (
    SELECT 1 FROM role_permission rp WHERE rp.role_id = r.id
  )
ON CONFLICT DO NOTHING;

-- 7. Customer → view only
INSERT INTO role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM role r
CROSS JOIN permission p
WHERE r.name = 'Customer'
  AND p.code IN ('view_dashboard')
  AND NOT EXISTS (
    SELECT 1 FROM role_permission rp WHERE rp.role_id = r.id
  )
ON CONFLICT DO NOTHING;

-- 8. Explicit Migrations: Ensure roles always get their setting permissions
-- Ensure new setting permissions are assigned to Super Admin (who has everything)
INSERT INTO role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM role r, permission p
WHERE r.name = 'Super Admin' 
  AND p.code IN ('manager_setting', 'admin_setting')
ON CONFLICT DO NOTHING;

-- Ensure manager_setting is assigned to Store Manager
INSERT INTO role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM role r, permission p
WHERE r.name = 'Store Manager' 
  AND p.code = 'manager_setting'
ON CONFLICT DO NOTHING;

-- Ensure manager_setting and admin_setting are assigned to Store Admin
INSERT INTO role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM role r, permission p
WHERE r.name = 'Store Admin' 
  AND p.code IN ('manager_setting', 'admin_setting')
ON CONFLICT DO NOTHING;