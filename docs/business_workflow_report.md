# Báo cáo Nghiệp vụ: Luồng Order → Payment → Inventory

> **Hệ thống**: POSMART Microservices  
> **Ngày rà soát**: 2026-04-24  
> **Phạm vi**: 3 Core Services (Order, Payment, Inventory) + Admin Frontend + POS Frontend

---

## 1. Tổng quan Kiến trúc

Hệ thống sử dụng **Saga Choreography** — không có orchestrator trung tâm. Các service giao tiếp qua **RabbitMQ** events với đảm bảo **at-least-once delivery** thông qua **Transactional Outbox Pattern**.

| Service | Port | Vai trò | Vai trò Saga |
|---------|------|---------|-------------|
| **Order Service** | 3003 | CRUD đơn hàng, status machine | Consumer + Producer |
| **Payment Service** | 3007 | Thanh toán, VNPay, hoàn tiền | **Saga Trigger** (Producer chính) |
| **Inventory Service** | 3006 | Tồn kho, reserve, deduct, release | Consumer + Compensation Producer |

```mermaid
graph TB
    subgraph "Frontend"
        ADMIN["Admin Panel<br/>:5173"]
        POS["POS Terminal<br/>:5173/pos"]
        CUST["Customer Web<br/>:5174"]
    end

    subgraph "API Gateway"
        GW["Nginx :8080"]
    end

    subgraph "Core Services"
        ORD["Order :3003"]
        PAY["Payment :3007"]
        INV["Inventory :3006"]
    end

    subgraph "Infrastructure"
        RMQ["RabbitMQ<br/>(CloudAMQP)"]
        DB["Supabase PostgreSQL<br/>(Shared DB)"]
    end

    ADMIN & POS & CUST --> GW
    GW --> ORD & PAY & INV
    ORD <--> RMQ
    PAY <--> RMQ
    INV <--> RMQ
    ORD & PAY & INV --> DB

    style RMQ fill:#ff6b35,color:#fff
    style DB fill:#3ecf8e,color:#fff
    style PAY fill:#6366f1,color:#fff
```

> [!IMPORTANT]
> **Payment Service** là **Saga Trigger** — mọi luồng nghiệp vụ đều bắt đầu từ event `payment.completed`.

---

## 2. Hai Luồng Bán Hàng Chính

### 2.1. POS / Pickup Flow (Bán tại quầy)

**Đặc điểm**: Đồng bộ, khách nhận hàng ngay, thanh toán tại quầy.

```mermaid
sequenceDiagram
    actor Cashier as Thu ngân
    participant FE as POS Frontend
    participant ORD as Order Service
    participant PAY as Payment Service
    participant MQ as RabbitMQ
    participant INV as Inventory Service
    participant AUTH as Auth Service

    Note over Cashier,AUTH: Phase 1 — Tạo đơn hàng
    Cashier->>FE: Chọn SP, số lượng, KH
    FE->>ORD: POST /api/orders<br/>{delivery_type: "pickup", items}
    Note over ORD: FEFO Allocation:<br/>Auto-select batch (earliest expiry)
    ORD->>INV: GET /api/inventory/batches/:productId<br/>(inter-service HTTP call)
    INV-->>ORD: Available batches (sorted FEFO)
    ORD-->>FE: 201 {status: "draft", payment_status: "pending"}

    Note over Cashier,AUTH: Phase 2 — Pay & Complete
    Cashier->>FE: Nhấn "Pay & Complete"
    FE->>PAY: POST /api/payments/direct<br/>{method: "cash", items[], deliveryType: "pickup"}
    PAY->>PAY: INSERT payment (status=completed)<br/>+ INSERT outbox_events

    Note over PAY,MQ: Outbox Poller (~3s)
    PAY->>MQ: publish payment.completed

    par Order nhận event
        MQ->>ORD: payment.completed
        ORD->>ORD: draft → delivered, paid
        ORD->>ORD: INSERT outbox (order.completed)
    and Inventory nhận event
        MQ->>INV: payment.completed (pickup)
        INV->>INV: deductStock(on_shelf -= qty)
        INV->>INV: record movement(type=out)
    end

    Note over ORD,MQ: Outbox Poller
    ORD->>MQ: publish order.completed

    MQ->>AUTH: order.completed
    AUTH->>AUTH: customer.total_spent += orderTotal
```

**Kết quả cuối cùng (POS)**:

| Entity | Trạng thái |
|--------|-----------|
| Order | `status=delivered`, `payment_status=paid` |
| Payment | `status=completed` |
| Inventory | `on_shelf -= qty`, movement type `out` |
| Customer | `total_spent += orderTotal` (via Auth Service) |

---

### 2.2. Online / Delivery Flow (Giao hàng)

**Đặc điểm**: Bất đồng bộ, 2-phase inventory (reserve → confirm).

```mermaid
sequenceDiagram
    actor Customer as Khách hàng
    participant FE as Customer Web / Admin
    participant ORD as Order Service
    participant PAY as Payment Service
    participant MQ as RabbitMQ
    participant INV as Inventory Service

    Note over Customer,INV: Phase 1 — Đặt hàng
    Customer->>FE: Đặt hàng online
    FE->>ORD: POST /api/orders<br/>{delivery_type: "delivery", items}
    ORD-->>FE: 201 {status: "draft"}

    Note over Customer,INV: Phase 2 — Thanh toán
    FE->>PAY: POST /api/payments/direct<br/>{deliveryType: "delivery", items}
    PAY->>PAY: INSERT payment (completed)

    PAY->>MQ: publish payment.completed

    par Order cập nhật
        MQ->>ORD: payment.completed (delivery)
        ORD->>ORD: draft → shipping, paid
        ORD->>ORD: INSERT outbox (order.shipping)
    and Inventory SKIP
        MQ->>INV: payment.completed (delivery)
        INV->>INV: SKIP — đợi order.shipping
    end

    Note over ORD,INV: Phase 3 — Reserve stock
    ORD->>MQ: publish order.shipping
    MQ->>INV: order.shipping
    INV->>INV: reserveStock<br/>(on_shelf -= qty, reserved += qty)

    Note over Customer,INV: Phase 4 — Xác nhận giao hàng
    FE->>ORD: PUT /api/orders/:id {status: "delivered"}
    ORD->>ORD: shipping → delivered
    ORD->>MQ: publish order.delivered

    MQ->>INV: order.delivered
    INV->>INV: confirmDeduct<br/>(reserved -= qty)
```

**Inventory thay đổi theo 2 pha (Delivery)**:

| Pha | Event | `on_shelf` | `reserved` | Ý nghĩa |
|-----|-------|-----------|-----------|---------|
| Phase 1 | `order.shipping` | −qty | +qty | Hàng rời kệ, đánh dấu tạm giữ |
| Phase 2 | `order.delivered` | — | −qty | Xác nhận đã bán, giải phóng reserved |

---

## 3. Luồng Bổ trợ

### 3.1. VNPay Payment Gateway

```mermaid
sequenceDiagram
    actor Customer as Khách
    participant FE as Frontend
    participant PAY as Payment Service
    participant VNPAY as VNPay Sandbox
    participant MQ as RabbitMQ

    Customer->>FE: Chọn thanh toán VNPay
    FE->>PAY: POST /api/payments<br/>{method: "vnpay", amount}
    PAY->>PAY: INSERT payment(pending) + vnpay_transaction
    PAY-->>FE: {paymentUrl: "https://sandbox.vnpay..."}

    FE->>Customer: Redirect → VNPay

    alt Thành công
        VNPAY->>PAY: IPN Callback (vnp_ResponseCode=00)
        PAY->>PAY: payment → completed
        PAY->>MQ: publish payment.completed
    else Thất bại
        VNPAY->>PAY: IPN (vnp_ResponseCode≠00)
        PAY->>MQ: publish payment.failed → Order cancelled
    else Timeout (15 phút)
        PAY->>PAY: Timeout Scanner (5 phút/lần)
        PAY->>MQ: publish payment.timeout → Order cancelled
    end
```

### 3.2. Hủy đơn (Delivery đang giao)

```mermaid
sequenceDiagram
    participant FE as Admin Panel
    participant ORD as Order Service
    participant MQ as RabbitMQ
    participant INV as Inventory Service

    FE->>ORD: PUT /api/orders/:id {status: "cancelled"}
    ORD->>ORD: shipping → cancelled
    ORD->>MQ: publish order.cancelled

    MQ->>INV: order.cancelled
    INV->>INV: releaseStock<br/>(reserved -= qty, on_hand += qty)
    Note over INV: Hàng quay về kho, không lên kệ
```

### 3.3. Hoàn tiền (Refund)

```mermaid
sequenceDiagram
    participant FE as Admin Panel
    participant PAY as Payment Service
    participant MQ as RabbitMQ
    participant ORD as Order Service

    Note over FE,ORD: Step 1 — Refund Payment (Payments page)
    FE->>PAY: POST /api/payments/:id/refund
    PAY->>PAY: completed → refunded
    PAY->>PAY: Check allRefunded?
    PAY->>MQ: publish payment.refunded<br/>{allRefunded: true/false}

    MQ->>ORD: payment.refunded
    ORD->>ORD: payment_status → refunded / partial_refund

    Note over FE,ORD: Step 2 — Refund Order (Orders page)
    FE->>ORD: POST /api/orders/:id/refund
    ORD->>ORD: delivered → refunded
    ORD->>MQ: publish order.refunded

    Note over FE,ORD: Step 3 — Return Items (Manual, Orders page)
    FE->>FE: Admin click "Return Items"
    FE->>FE: POST /inventory/return-stock
    Note over FE: items quay lại on_hand (warehouse)
```

> [!NOTE]
> **Refund tách 3 bước**: Hoàn tiền (Payment) → Đổi status order (Order) → Hoàn hàng (Inventory). Đây là thiết kế chủ đích để tách biệt nghiệp vụ tài chính và logistics.

### 3.4. Saga Compensation (Xử lý lỗi)

```mermaid
sequenceDiagram
    participant PAY as Payment
    participant MQ as RabbitMQ
    participant ORD as Order
    participant INV as Inventory

    PAY->>MQ: payment.completed
    MQ->>INV: deductStock

    INV--xINV: ❌ Hết hàng (on_shelf < qty)
    INV->>MQ: publish inventory.deduct_failed

    MQ->>ORD: inventory.deduct_failed
    ORD->>ORD: → cancelled, payment_status=failed
```

---

## 4. Event Catalog

### 4.1. Payment Service → Publish

| Event | Trigger | Key Payload | Consumers |
|-------|---------|------------|-----------|
| `payment.completed` | Payment thành công | `orderId, storeId, items[], deliveryType, totalPaidSoFar` | Order, Inventory |
| `payment.failed` | VNPay thất bại | `orderId, storeId, reason` | Order, Inventory |
| `payment.timeout` | VNPay hết hạn (15m) | `orderId, storeId` | Order, Inventory |
| `payment.refunded` | Admin hoàn tiền | `orderId, allRefunded` | Order |

### 4.2. Order Service → Publish

| Event | Trigger | Key Payload | Consumers |
|-------|---------|------------|-----------|
| `order.shipping` | draft → shipping | `orderId, storeId, items[], deliveryType` | Inventory |
| `order.delivered` | shipping → delivered | `orderId, storeId, items[]` | Inventory |
| `order.cancelled` | shipping → cancelled | `orderId, storeId, items[]` | Inventory |
| `order.completed` | → delivered (any type) | `orderId, customerId, items[]` | Auth (total_spent) |
| `order.refunded` | → refunded | `orderId, items[]` | Inventory |

### 4.3. Inventory Service → Publish

| Event | Trigger | Key Payload | Consumers |
|-------|---------|------------|-----------|
| `inventory.deduct_failed` | Stock operation lỗi | `orderId, reason` | Order |
| `inventory.updated` | Bất kỳ stock change | `storeId` | Statistics |

---

## 5. Frontend Integration

### 5.1. Admin Panel — Orders Page

| Component | File | Chức năng |
|-----------|------|----------|
| `Orders.jsx` | Page wrapper | Fetch orders + Client-Side Join (resolve customer/employee names) |
| `OrderList.jsx` | Table | Hiển thị danh sách đơn hàng |
| `OrderListHeader.jsx` | Toolbar | Filter: status, payment, delivery type |
| `AddOrderModal.jsx` | Modal | Tạo đơn draft (FEFO allocation) |
| `EditOrderModal.jsx` | Modal | Sửa đơn + cập nhật status |
| `ViewOrderPaymentsModal.jsx` | Modal | Xem payment history + Add Payment / Pay & Complete |
| `InvoiceOrderModal.jsx` | Modal | Xuất hóa đơn |

**Client-Side Join Pattern**:
```
Orders.jsx → GET /api/orders (headers only)
           → Promise.allSettled(customerService.getCustomerById(id))
           → Promise.allSettled(employeeService.getEmployeeById(id))
           → Enrich orders with _customerName, _customerPhone, _createdByName
```

### 5.2. Admin Panel — Payments Page

| Component | File | Chức năng |
|-----------|------|----------|
| `Payments.jsx` | Page wrapper | Fetch all payments + client-side filter/sort |
| `PaymentList.jsx` | Table | Hiển thị giao dịch |
| `PaymentListHeader.jsx` | Toolbar | Filter: method, reference, status |
| `AddPaymentModal.jsx` | Modal | Tạo payment mới |
| `EditPaymentModal.jsx` | Modal | Sửa payment pending |

### 5.3. POS Frontend (posDataService)

POS sử dụng **isolated Axios instance** (`posApi.js`) với token riêng:

```
POS Flow:
  usePOSOrder → posDataService.createOrder()
  usePOSPayment → posDataService.createDirectPayment()
  
  All POS calls go through posApi (posToken)
  All Admin calls go through api (adminToken)
```

### 5.4. ViewOrderPaymentsModal — Điểm nối quan trọng

Modal này là **cầu nối Order ↔ Payment**, xử lý:

1. **Fetch order details** (GET `/api/orders/:id`) để lấy `items[]`
2. **Submit payment** với `items[]` đầy đủ cho inventory deduction
3. Hỗ trợ 2 mode:
   - **Save as Pending**: Tạo payment chờ duyệt
   - **Pay & Complete**: Tạo + hoàn thành ngay (trigger Saga)

> [!WARNING]
> Nếu `items[]` rỗng khi submit payment → Inventory handler sẽ **SKIP** silently (không trừ kho). Đây là guard có chủ đích, nhưng frontend phải đảm bảo luôn fetch order details trước khi tạo payment.

---

## 6. Bảng So sánh Tổng hợp: Pickup vs Delivery

| Bước | Pickup (POS) | Delivery (Online) |
|------|-------------|-------------------|
| **Tạo đơn** | `draft` | `draft` |
| **Thanh toán** | `payment.completed` → **delivered** | `payment.completed` → **shipping** |
| **Inventory @ payment** | `deductStock` (on_shelf -= qty) | **SKIP** |
| **Inventory @ shipping** | — | `reserveStock` (on_shelf → reserved) |
| **Giao hàng** | Ngay tại quầy | Admin xác nhận → `delivered` |
| **Inventory @ delivered** | **SKIP** (đã trừ) | `confirmDeduct` (reserved -= qty) |
| **Hủy đơn** | ❌ Không thể (đã delivered) | ✅ `releaseStock` (reserved → on_shelf) |
| **Hoàn tiền** | Payment → Order → Manual Inventory | Payment → Order → Manual Inventory |

---

## 7. Reliability & Safety Mechanisms

### 7.1. Transactional Outbox

```
Business Write + Event Insert = 1 Transaction (atomic)
Poller reads unpublished events every 3s → publish to RabbitMQ → mark published_at
```

### 7.2. Idempotency (processed_events)

```sql
-- Mỗi service track riêng, không xung đột
UNIQUE(event_id, service_name)
```

### 7.3. Shared-DB Isolation

```sql
-- Outbox: mỗi poller chỉ đọc events của service mình
WHERE published_at IS NULL AND service_name = $1
```

### 7.4. FEFO Batch Allocation

Order Service gọi HTTP tới Inventory Service để lấy batches, tự động chọn lô **hết hạn sớm nhất** (First Expired, First Out). Hỗ trợ **multi-batch split** nếu 1 lô không đủ số lượng.

### 7.5. VNPay Timeout Scanner

Payment Service chạy scanner mỗi **5 phút**, quét VNPay payments pending quá **15 phút** → publish `payment.timeout` → Order cancelled.

---

## 8. Sơ đồ Tổng hợp Event Flow

```mermaid
graph LR
    subgraph "Pickup Flow"
        P1["draft"] -->|"payment.completed"| P2["delivered ✅"]
        P2 -.->|"Inventory"| P3["on_shelf -= qty"]
    end

    subgraph "Delivery Flow"
        D1["draft"] -->|"payment.completed"| D2["shipping 🚚"]
        D2 -.->|"Phase 1: reserve"| D3["on_shelf -= qty<br/>reserved += qty"]
        D2 -->|"Admin: delivered"| D4["delivered ✅"]
        D4 -.->|"Phase 2: confirm"| D5["reserved -= qty"]
    end

    subgraph "Cancellation"
        D2 -->|"Admin: cancel"| C1["cancelled ❌"]
        C1 -.->|"release"| C2["reserved -= qty<br/>on_hand += qty"]
    end

    subgraph "Refund"
        P2 & D4 -->|"refund payments"| R1["refunded 💸"]
        R1 -.->|"manual return"| R2["on_hand += qty"]
    end

    style P2 fill:#10b981,color:#fff
    style D2 fill:#f59e0b,color:#fff
    style D4 fill:#10b981,color:#fff
    style C1 fill:#ef4444,color:#fff
    style R1 fill:#8b5cf6,color:#fff
```
