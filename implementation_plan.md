# Plan: Discount + Coupon + Shipping System -- 5 Phases (v4 Final)

Dua tren [review.md](file:///e:/UIT/cv/backend/review.md) va [discount_scan_report.md](file:///C:/Users/ACER/.gemini/antigravity/brain/97f72080-6456-4f4e-947c-f4306bea9fbe/discount_scan_report.md).

---

## Hien Trang Tien Do

| Component | Membership Discount | Coupon System | Shipping Fee |
|---|---|---|---|
| **Auth Service** | Missing `customerType` | N/A | N/A |
| **Settings Service** | Done [getCustomerDiscounts()](file:///e:/UIT/cv/backend/backend/services/settings/src/services/settings.service.js#20-32) | No tables/API | N/A |
| **Order Service** | Done `resolveCustomerDiscount()` | No server-side validation | Trusts client value |
| **Customer Frontend** | No settingsService | Mock hardcoded in CartContext | Hardcoded "Free" |
| **Admin Frontend** | N/A | No management UI | N/A |
| **Nginx Gateway** | Done | No `/api/coupons` route | N/A |

---

## Quy Tac Tinh Toan (Sequential Discounting + Freeship)

```
1. Subtotal         = sum(item.price * item.quantity)
2. MemberDiscount   = Subtotal * memberRate%
3. AfterMember      = Subtotal - MemberDiscount
4. CouponDiscount   = percent -> AfterMember * rate%
                    | fixed   -> min(value, AfterMember)
                    | freeship -> 0 (tru vao ship, khong tru vao hang)
5. ShippingFee      = delivery ? 30000 : 0
6. ShippingDiscount = coupon.type === 'freeship' ? min(coupon.value, ShippingFee) : 0
7. FinalTotal       = AfterMember - CouponDiscount + ShippingFee - ShippingDiscount
```

---

## Phase 1: Auth Service -- Bo Sung `customerType`

### [MODIFY] [auth.service.js](file:///e:/UIT/cv/backend/backend/services/auth/src/services/auth.service.js)

Bo sung `customerType` vao `_formatUserResponse` (dong 338-340):

```diff
     if (isCustomer && profile) {
       response.customerId = profile.id;
+      response.customerType = profile.customer_type || profile.customerType || 'retail';
     }
```

---

## Phase 2: Coupon Backend -- Settings Service

### [MODIFY] [init.sql](file:///e:/UIT/cv/backend/backend/services/settings/src/db/init.sql)

Them bang `coupons` (ho tro `freeship` type + `is_public` flag) va `coupon_usages`:

```sql
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
```

---

### [NEW] [coupon.repository.js](file:///e:/UIT/cv/backend/backend/services/settings/src/repositories/coupon.repository.js)

| Method | Mo ta |
|---|---|
| [findByCode(code)](file:///e:/UIT/cv/backend/backend/services/settings/src/repositories/coupon.repository.js#6-13) | Tim coupon theo ma |
| [findAll(filters)](file:///e:/UIT/cv/backend/backend/services/settings/src/repositories/coupon.repository.js#26-59) | Paginated list (search, active filter) cho Admin |
| [findAvailable()](file:///e:/UIT/cv/backend/backend/services/settings/src/repositories/coupon.repository.js#14-25) | `is_active = true AND is_public = true AND (expires_at IS NULL OR expires_at > NOW())` cho Customer |
| [create(data)](file:///e:/UIT/cv/backend/backend/services/settings/src/repositories/coupon.repository.js#60-74) | Insert coupon moi |
| [update(id, data)](file:///e:/UIT/cv/backend/backend/services/settings/src/repositories/coupon.repository.js#75-113) | Update coupon fields |
| [softDelete(id)](file:///e:/UIT/cv/backend/backend/services/settings/src/repositories/coupon.repository.js#114-121) | Set `is_active = false` |
| [incrementUsedCount(client, id)](file:///e:/UIT/cv/backend/backend/services/settings/src/repositories/coupon.repository.js#122-130) | Atomic `+1` used_count |
| [logUsage(client, {couponId, customerId, orderId})](file:///e:/UIT/cv/backend/backend/services/settings/src/repositories/coupon.repository.js#131-141) | Insert vao coupon_usages |
| [getCustomerUsageCount(couponId, customerId)](file:///e:/UIT/cv/backend/backend/services/settings/src/repositories/coupon.repository.js#142-149) | Dem so lan customer da dung ma |
| [getUsageHistory(couponId, filters)](file:///e:/UIT/cv/backend/backend/services/settings/src/repositories/coupon.repository.js#150-174) | Paginated usage log cho Admin |

---

### [MODIFY] [settings.service.js](file:///e:/UIT/cv/backend/backend/services/settings/src/services/settings.service.js)

Them coupon methods:

```javascript
// --- Coupon Management (Admin) ---
async getCoupons(query) { /* paginated list */ }
async createCoupon(data) { /* validate unique code + insert */ }
async updateCoupon(id, data) { /* update fields */ }
async deleteCoupon(id) { /* soft delete */ }
async getCouponUsages(couponId, query) { /* paginated usage log */ }

// --- Coupon Public (Customer) ---
async getAvailableCoupons() {
  // Return is_active + is_public + not expired coupons
  return this.couponRepo.findAvailable();
}

// --- Coupon Validation ---
async validateCoupon(code, { customerId, subtotal }) {
  // 1. findByCode -> check is_active, dates, max_uses, min_order
  // 2. Check per-customer limit (1 lan/ma/khach)
  // Return: { valid, coupon: { discount_type, discount_value, description }, error? }
}

// --- Coupon Redemption (atomic) ---
async redeemCoupon(code, customerId, orderId) {
  // Transaction: incrementUsedCount + logUsage
}
```

---

### [MODIFY] [settings.routes.js](file:///e:/UIT/cv/backend/backend/services/settings/src/routes/settings.routes.js)

Admin CRUD routes (require `manage_settings`):

```
GET    /api/settings/coupons              -> getCoupons
POST   /api/settings/coupons              -> createCoupon
PUT    /api/settings/coupons/:id          -> updateCoupon
DELETE /api/settings/coupons/:id          -> deleteCoupon
GET    /api/settings/coupons/:id/usages   -> getCouponUsages
```

### [MODIFY] [app.js](file:///e:/UIT/cv/backend/backend/services/settings/src/app.js)

Public endpoints (customer-facing, require [verifyToken](file:///e:/UIT/cv/backend/backend/services/settings/tests/__mocks__/auth-middleware.js#2-10) only):

```javascript
// List available coupons for customer Drawer UI
app.get('/api/coupons/available', verifyToken, async (req, res, next) => {
  const result = await settingsService.getAvailableCoupons();
  res.json({ success: true, data: result });
});

// Validate coupon before apply
app.post('/api/coupons/validate', verifyToken, async (req, res, next) => {
  const { code, subtotal } = req.body;
  const customerId = req.user.customerId || req.user.id;
  const result = await settingsService.validateCoupon(code, { customerId, subtotal });
  res.json({ success: true, data: result });
});
```

### [MODIFY] [index.js](file:///e:/UIT/cv/backend/backend/services/settings/src/index.js)

Inject [CouponRepository](file:///e:/UIT/cv/backend/backend/services/settings/src/repositories/coupon.repository.js#1-175) vao DI.

### [MODIFY] [nginx.conf](file:///e:/UIT/cv/backend/backend/gateway/nginx.conf)

```diff
+        location /api/coupons {
+            proxy_pass http://settings_service;
+            proxy_set_header Host $host;
+            proxy_set_header X-Real-IP $remote_addr;
+            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
+        }
```

---

## Phase 3: Order Service -- Zero-Trust Coupon + Shipping Fee

### [MODIFY] [order.service.js](file:///e:/UIT/cv/backend/backend/services/order/src/services/order.service.js)

Cap nhat `createDraftOrder`:

```javascript
async createDraftOrder(storeId, data, userId, jwtToken) {
  const { customer_id, delivery_type, address, items: rawItems, coupon_code } = data;

  // Zero-Trust shipping fee (ignore client value)
  const base_shipping_fee = delivery_type === 'delivery' ? 30000 : 0;

  // Membership discount
  let discount_percentage = 0;
  if (customer_id) {
    discount_percentage = await this.resolveCustomerDiscount(customer_id, jwtToken);
  }
  const afterMember = subtotal * (1 - discount_percentage / 100);

  // Coupon resolution (supports percent, fixed, freeship)
  let coupon_discount = 0;
  let final_shipping_fee = base_shipping_fee;
  if (coupon_code) {
    const couponRes = await this.resolveCouponDiscount(coupon_code, customer_id, afterMember);
    if (couponRes.type === 'freeship') {
      final_shipping_fee = Math.max(0, base_shipping_fee - couponRes.value);
    } else {
      coupon_discount = couponRes.discount_amount;
    }
  }

  const total_amount = afterMember - coupon_discount + final_shipping_fee;
  // ...save with coupon_code, coupon_discount, shipping_fee: final_shipping_fee...
}
```

Them `resolveCouponDiscount` method -- goi Settings Service internal API.

### [MODIFY] [init.sql (Order DB)](file:///e:/UIT/cv/backend/backend/services/order/src/db/init.sql)

```sql
DO $$ BEGIN ALTER TABLE sale_order ADD COLUMN coupon_code TEXT;
EXCEPTION WHEN duplicate_column THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE sale_order ADD COLUMN coupon_discount NUMERIC NOT NULL DEFAULT 0;
EXCEPTION WHEN duplicate_column THEN NULL; END $$;
```

---

## Phase 4: Customer Frontend -- settingsService + CartContext Rewrite

### [NEW] [settingsService.js](file:///e:/UIT/cv/backend/customer/src/services/settingsService.js)

```javascript
import api from './api'
const FALLBACK_DISCOUNTS = { guest: 0, retail: 0, wholesale: 5, vip: 10 };

const settingsService = {
  getActiveDiscounts: async () => {
    try {
      const res = await api.get('/customer-discount-settings/active');
      return res.data?.data || FALLBACK_DISCOUNTS;
    } catch { return FALLBACK_DISCOUNTS; }
  },
  getAvailableCoupons: async () => {
    try {
      const res = await api.get('/coupons/available');
      return res.data?.data || [];
    } catch { return []; }
  },
  validateCoupon: async (code, subtotal) => {
    const res = await api.post('/coupons/validate', { code, subtotal });
    return res.data?.data;
  }
};
export default settingsService;
```

### [MODIFY] [CartContext.jsx](file:///e:/UIT/cv/backend/customer/src/contexts/CartContext.jsx)

Key changes:

1. Import `useAuth` + `settingsService`
2. State: `discountRates`, `availableCoupons`
3. Fetch on mount: `getActiveDiscounts()` + [getAvailableCoupons()](file:///e:/UIT/cv/backend/backend/services/settings/src/services/settings.service.js#237-240)
4. `getShippingFee()` -> returns `30000` for delivery
5. `getMembershipDiscount()` -> `getCartTotal() * (rate / 100)` (Membership truoc)
6. `applyCoupon(code)` -> async, goi `settingsService.validateCoupon()`
7. `getCartDiscount()` -> tinh tren `afterMember` (Coupon sau)
8. `getShippingDiscount()` -> returns shipping reduction if freeship coupon
9. Export: `getMembershipDiscount`, `getShippingFee`, `getShippingDiscount`, `availableCoupons`

### [MODIFY] [orderService.js](file:///e:/UIT/cv/backend/customer/src/services/orderService.js)

Them `coupon_code` vao payload `POST /orders`.

### [MODIFY] [CheckoutPage.jsx](file:///e:/UIT/cv/backend/customer/src/pages/CheckoutPage.jsx)

Truyen `couponCode: appliedCoupon?.code` vao `orderService.createOrder()`.

---

## Phase 5: Customer UI + Admin Coupon Management

### [MODIFY] [OrderSummary.jsx](file:///e:/UIT/cv/backend/customer/src/components/Checkout/OrderSummary.jsx)

Thay the text input bang **Coupon Drawer/Modal** (Pick-and-Apply):

1. Nut kich hoat: "Chon ma giam gia" button
2. Click -> Drawer/Modal truot len hien thi danh sach `availableCoupons` tu CartContext
3. Moi coupon card hien thi: code, description, discount_type badge, min_order_amount
4. Nut "Ap dung" tren moi card -> goi [validateCoupon(code, subtotal)](file:///e:/UIT/cv/backend/frontend/src/services/settingsService.js#339-351) ngam -> cap nhat `appliedCoupon`
5. Coupon da chon hien thi nho gon voi nut "Xoa"
6. Them dong Member Discount (sau Subtotal)
7. Shipping Fee: freeship -> line-through 30.000d + "0d"
8. Total = `getCartTotal() - getMembershipDiscount() - getCartDiscount() + getShippingFee() - getShippingDiscount()`

### [MODIFY] [Cart.jsx](file:///e:/UIT/cv/backend/customer/src/components/Cart/Cart.jsx)

Tuong tu OrderSummary: them Member + Shipping + Coupon Drawer.

---

### [NEW] [CouponManager.jsx](file:///e:/UIT/cv/backend/frontend/src/components/Settings/CouponManager.jsx)

Admin Coupon Management UI -- tab moi trong Settings page:

| Feature | Mo ta |
|---|---|
| **Coupon Table** | List: code, type badge, value, used/max, is_public, status, dates |
| **Create Modal** | Form: code, description, type (percent/fixed/freeship), value, min_order, max_uses, is_public, dates |
| **Edit Modal** | Update existing coupon |
| **Toggle Active** | Quick on/off toggle |
| **Toggle Public** | Control visibility in customer Drawer |
| **Usage History** | Expandable row: customer name, order ID, used_at |
| **Status Badge** | Active (green), Expired (red), Depleted (orange), Inactive (gray) |

### [MODIFY] [Settings.jsx](file:///e:/UIT/cv/backend/frontend/src/pages/Settings.jsx)

Them tab "Coupons" (icon: `Ticket`):

```diff
+import { CouponManager } from '../components/Settings';
+import { Ticket } from 'lucide-react';
 ...
+    {
+      id: 'coupons',
+      label: 'Coupons',
+      icon: Ticket,
+      description: 'Manage discount coupons and freeship codes',
+      component: CouponManager
+    },
```

### [MODIFY] [customerDiscountSettingsService.js](file:///e:/UIT/cv/backend/frontend/src/services/customerDiscountSettingsService.js)

Them coupon CRUD methods cho Admin panel:

```javascript
getCoupons: async (params) => { /* GET /settings/coupons */ },
createCoupon: async (data) => { /* POST /settings/coupons */ },
updateCoupon: async (id, data) => { /* PUT /settings/coupons/:id */ },
deleteCoupon: async (id) => { /* DELETE /settings/coupons/:id */ },
getCouponUsages: async (id, params) => { /* GET /settings/coupons/:id/usages */ }
```

---

## Phase 6: Sync UI Style Pattern & Fix Seed Permissions Override

### 6.1 UI Style Sync
Modify [CouponSettings.jsx](file:///e:/UIT/cv/backend/frontend/src/components/Settings/CouponSettings.jsx):
- Adjust main wrapper to use `max-w-6xl mx-auto space-y-8`.
- Build a dual-column layout for Admin settings pages.
- Standardize on `font-['Poppins',sans-serif]` for text and labels.
- Standardize on table styling with uppercase tracking-wider headers and smooth row hover transitions (`hover:bg-emerald-50/50`).
- Implement consistent clean borders.

### 6.2 SQL Seed Safeness
Modify [seed.sql](file:///e:/UIT/cv/backend/backend/services/auth/src/db/seed.sql):
- Prevent overwriting custom permissions of standard roles during service reboot.
- Add `AND NOT EXISTS (SELECT 1 FROM role_permission rp WHERE rp.role_id = r.id)` logic for Super Admin, Store Manager, Cashier, Store Admin, and Customer roles.

---

## Phase 7: Bugfix for Coupon Creation (type fallback) & Edit Validation

### [MODIFY] [settings.service.js](file:///e:/UIT/cv/backend/backend/services/settings/src/services/settings.service.js)

Normalize coupon properties inside [createCoupon](file:///e:/UIT/cv/backend/frontend/src/services/settingsService.js#365-377) and [updateCoupon](file:///e:/UIT/cv/backend/frontend/src/services/settingsService.js#378-390) to support mapping both camelCase/snake_case frontend forms:
- `discountType`: from `discount_type` / `discountType`
- `discountValue`: from `discount_value` / `discountValue`
- `minOrderAmount`: from `min_order_amount` / `minOrderAmount`
- `maxUses`: from `usage_limit` / `max_uses` / `maxUses`
- `isActive`: from `is_active` / `isActive`
- `startsAt`: from `start_date` / `starts_at` / `startsAt`
- `expiresAt`: from `end_date` / `expires_at` / `expiresAt`

Change comparison logic in [updateCoupon](file:///e:/UIT/cv/backend/frontend/src/services/settingsService.js#378-390) duplicate code check to use string comparison:
```javascript
if (existing && String(existing.id) !== String(id)) {
  throw new ValidationError('Coupon code already exists');
}
```

### [MODIFY] [CouponSettings.jsx](file:///e:/UIT/cv/backend/frontend/src/components/Settings/CouponSettings.jsx)

- In [handleOpenEdit](file:///e:/UIT/cv/backend/frontend/src/components/Settings/CouponSettings.jsx#91-111), retrieve starts_at, expires_at, and max_uses from the PG returned properties:
  - `startDate`: `coupon.starts_at || coupon.start_date`
  - `endDate`: `coupon.expires_at || coupon.end_date`
  - `usageLimit`: `coupon.max_uses !== undefined ? coupon.max_uses : coupon.usage_limit`
- Implement a helper [formatDateTimeLocal(dateString)](file:///e:/UIT/cv/backend/frontend/src/components/Settings/CouponSettings.jsx#60-73) to correctly shift standard UTC TIMESTAMPTZ formatting for `datetime-local` elements in the active browser timezone.
- In the coupons table render row, map `used_count` / `max_uses` to display properly instead of returning blank due to property checking mismatches.
  - `usageLimit`: `coupon.max_uses !== undefined && coupon.max_uses !== null ? coupon.max_uses : coupon.usage_limit`
  - `usageCount`: `coupon.used_count !== undefined && coupon.used_count !== null ? coupon.used_count : (coupon.usage_count ?? 0)`

---

## Phase 8: Settings Service Permission & UI Refactor

### 8.1 Database Seeds and Routings

#### [MODIFY] [seed.sql](file:///e:/UIT/cv/backend/backend/services/auth/src/db/seed.sql)
- Remove `manage_settings` permission.
- Insert `manager_setting` and `admin_setting` permissions.
- In Role-Permission mappings:
  - Assign `manager_setting` to `Store Manager`.
  - Assign `manager_setting` and `admin_setting` to `Store Admin`.
  - Clean up any legacy assignments.

#### [MODIFY] [settings.routes.js](file:///e:/UIT/cv/backend/backend/services/settings/src/routes/settings.routes.js)
- Update routes for `/security`, `/sales`, `/history`, and `/fresh-promotion/...` to require `admin_setting`.
- Update routes for `/coupons/...` to require `manager_setting`.

### 8.2 Frontend RBAC Integration

#### [MODIFY] [permissions.js](file:///e:/UIT/cv/backend/frontend/src/utils/permissions.js)
- Replace `MANAGE_SETTINGS: 'manage_settings'` with `MANAGER_SETTING: 'manager_setting'` and `ADMIN_SETTING: 'admin_setting'`.

#### [MODIFY] [ProtectedRoute.jsx](file:///e:/UIT/cv/backend/frontend/src/components/ProtectedRoute.jsx)
- Update `requiredPermission` checker to support checking arrays of allowable permissions (i.e. check if the user has at least one of the permissions).

#### [MODIFY] [NavigationMenuSection.jsx](file:///e:/UIT/cv/backend/frontend/src/components/Sidebar/sections/NavigationMenuSection/NavigationMenuSection.jsx)
- Enforce settings menu to allow array `permission: [PERMISSIONS.MANAGER_SETTING, PERMISSIONS.ADMIN_SETTING]`.
- Update standard permission loops to support array items via [hasAnyPermission](file:///e:/UIT/cv/backend/frontend/src/utils/permissions.js#54-66).

#### [MODIFY] [Settings.jsx](file:///e:/UIT/cv/backend/frontend/src/pages/Settings.jsx)
- Assign `permission` property to each settings tab:
  - Coupons and Product Price -> `manager_setting`.
  - Customer Discount, POS Security, and Fresh Product Promotion -> `admin_setting`.
- Rename Fresh Product Promotion tab ID to `perishable`, label to `Perishable Promotion`, and description to indicate perishable products.
- Dynamically filter settings tabs depending on permissions, and set fallback tab to the first allowed tab.

### 8.3 Product Price Settings UI Refactor

#### [MODIFY] [ProductPriceSettings.jsx](file:///e:/UIT/cv/backend/frontend/src/components/Settings/ProductPriceSettings.jsx)
- Implement frontend pagination table header & footer footer (Items per page selection, previous page, page number buttons, next page) matching [CustomerList](file:///e:/UIT/cv/backend/frontend/src/components/CustomerList/CustomerList.jsx#6-447).
- Integrate API page limits and page offsets, querying `productService.getAllProducts(params)` dynamically on state updates.
- Support live search text filtering from table header triggering API requests.
- Optimize rendering variables (proper keys, formatted IDs).

---

## Verification Plan

### Automated Tests
- Run settings service integration tests: `cd backend/services/settings && npm run test`
- Run auth service tests: `cd backend/services/auth && npm run test`

### Manual Verification
1. **Admin / Manager Page Filtering**: Login as `Store Manager`, navigate to Settings, verify only `Coupons Manager` and `Product Price` tabs are accessible.
2. **Tab Access Redirect**: Verify that the first selected tab defaults to `Coupons Manager` when logged in as Store Manager, rather than failing on `Customer Discounts`.
3. **Product Price settings pagination & filter**: Search a product, change pages, verify that query param [search](file:///e:/UIT/cv/backend/frontend/src/components/Settings/ProductPriceSettings.jsx#41-58), `page`, and `limit` are passed to Catalog API correctly.
