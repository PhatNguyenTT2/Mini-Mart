# Plan: Discount + Coupon + Shipping System -- 5 Phases (v4 Final)

Dua tren [review.md](file:///e:/UIT/cv/backend/review.md) va [discount_scan_report.md](file:///C:/Users/ACER/.gemini/antigravity/brain/97f72080-6456-4f4e-947c-f4306bea9fbe/discount_scan_report.md).

---

## Hien Trang Tien Do

| Component | Membership Discount | Coupon System | Shipping Fee |
|---|---|---|---|
| **Auth Service** | Missing `customerType` | N/A | N/A |
| **Settings Service** | Done [getCustomerDiscounts()](file:///e:/UIT/cv/backend/backend/services/settings/src/services/settings.service.js#19-31) | No tables/API | N/A |
| **Order Service** | Done [resolveCustomerDiscount()](file:///e:/UIT/cv/backend/backend/services/order/src/services/order.service.js#282-358) | No server-side validation | Trusts client value |
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

Bo sung `customerType` vao [_formatUserResponse](file:///e:/UIT/cv/backend/backend/services/auth/src/services/auth.service.js#323-343) (dong 338-340):

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
| `findByCode(code)` | Tim coupon theo ma |
| [findAll(filters)](file:///e:/UIT/cv/backend/backend/services/catalog/src/repositories/product.repository.js#10-50) | Paginated list (search, active filter) cho Admin |
| `findAvailable()` | `is_active = true AND is_public = true AND (expires_at IS NULL OR expires_at > NOW())` cho Customer |
| [create(data)](file:///e:/UIT/cv/backend/backend/services/catalog/src/repositories/product.repository.js#143-155) | Insert coupon moi |
| [update(id, data)](file:///e:/UIT/cv/backend/backend/services/catalog/src/repositories/product.repository.js#156-175) | Update coupon fields |
| `softDelete(id)` | Set `is_active = false` |
| `incrementUsedCount(client, id)` | Atomic `+1` used_count |
| `logUsage(client, {couponId, customerId, orderId})` | Insert vao coupon_usages |
| `getCustomerUsageCount(couponId, customerId)` | Dem so lan customer da dung ma |
| `getUsageHistory(couponId, filters)` | Paginated usage log cho Admin |

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

Public endpoints (customer-facing, require `verifyToken` only):

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

Inject `CouponRepository` vao DI.

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

Cap nhat [createDraftOrder](file:///e:/UIT/cv/backend/backend/services/order/src/services/order.service.js#359-416):

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

1. Import [useAuth](file:///e:/UIT/cv/backend/customer/src/contexts/AuthContext.jsx#62-70) + `settingsService`
2. State: `discountRates`, `availableCoupons`
3. Fetch on mount: [getActiveDiscounts()](file:///e:/UIT/cv/backend/frontend/src/services/customerDiscountSettingsService.js#9-22) + `getAvailableCoupons()`
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
4. Nut "Ap dung" tren moi card -> goi `validateCoupon(code, subtotal)` ngam -> cap nhat `appliedCoupon`
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

## Verification Plan

### Automated Tests
- `cd backend/services/auth && npm run test:unit` -- customerType in response
- `cd backend/services/settings && npm run test:unit` -- coupon CRUD + validation + freeship
- `cd backend/services/order && npm run test:unit` -- coupon + shipping in createDraftOrder

### Manual Verification
1. **Phase 1**: Login Customer -> localStorage chua `customerType`
2. **Phase 2**: Admin -> Settings -> Coupons tab -> tao `SUMMER20` (percent, 20%, min 100k) + verify WELCOME100 seed
3. **Phase 3**: Customer VIP -> cart 500k -> checkout:
   - Subtotal: 500.000
   - Member VIP (-10%): -50.000
   - Coupon SUMMER20 (20% of 450k): -90.000
   - Shipping: 30.000
   - **Total: 390.000**
4. **Freeship**: Chon WELCOME100 tu Drawer -> Shipping hien thi ~~30.000~~ **0** -> Total: 450.000
5. **Usage**: Admin -> Coupons -> WELCOME100 -> usage history hien thi customer + order ID
