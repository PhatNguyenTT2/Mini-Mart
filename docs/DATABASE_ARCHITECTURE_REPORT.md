# BÁO CÁO TỔNG THỂ KIẾN TRÚC CƠ SỞ DỮ LIỆU MICROSERVICES (MINI-MART BACKEND)

---

## 1. TỔNG QUAN KIẾN TRÚC & NGUYÊN TẮC THIẾT KẾ

Hệ thống backend của **Mini-Mart** được xây dựng theo mô hình **Microservices Architecture** chuẩn mực với pattern **Database-per-Service**. Mỗi dịch vụ sở hữu cơ sở dữ liệu riêng biệt để đảm bảo tính độc lập, khả năng mở rộng độc lập (independent scaling) và phân tách trách nhiệm (separation of concerns).

### Các đặc điểm kiến trúc cốt lõi:
1. **Multi-Tenancy (Đa cửa hàng)**: 
   - `auth_db.store` đóng vai trò **Tenancy Root**. 
   - Hầu hết các dịch vụ xử lý dữ liệu giao dịch (`inventory`, `order`, `payment`, `supplier`, `chatbot`) đều chứa cột `store_id` để phân tách dữ liệu giữa các chi nhánh cửa hàng.

2. **Đảm bảo tính nhất quán dữ liệu (Data Consistency)**:
   - Các dịch vụ xử lý giao dịch cốt lõi (`order`, `inventory`, `payment`, `supplier`, `chatbot`) áp dụng mẫu **Transactional Outbox Pattern** (`outbox_events`) kết hợp bảng **Idempotency** (`processed_events`) để giao tiếp bất đồng bộ qua Event-Driven Messaging (SAGA Pattern / RabbitMQ / Kafka) an toàn, chống lặp sự kiện.

3. **Liên kết Liên Dịch Vụ (Cross-Service Logical References)**:
   - Các dịch vụ không dùng Foreign Key vật lý qua lại giữa các database khác nhau (để tránh thắt nút cứng giữa các DB). Thay vào đó, dữ liệu được tham chiếu logic (VD: `order_db.sale_order_detail.product_id` -> `catalog_db.product.id`).
   - Các dịch vụ lưu trữ dữ liệu **Snapshot** (VD: tên sản phẩm, giá niêm yết tại thời điểm tạo đơn) để đảm bảo lịch sử giao dịch không bị biến động khi danh mục sản phẩm thay đổi.

4. **Tích hợp AI & Tìm kiếm thông minh**:
   - `chatbot_db` tích hợp tiện ích mở rộng **pgvector** (`embedding VECTOR(768)`) cho tìm kiếm ngữ nghĩa RAG (Retrieval-Augmented Generation) kết hợp Full-Text Search (`fts_content TSVECTOR`).
   - Hỗ trợ các thuật toán gợi ý sản phẩm nâng cao: Apriori Co-Purchase, Item-based Collaborative Filtering, và Hybrid Ensemble Weights.

---

## 2. CHI TIẾT CƠ SỞ DỮ LIỆU CỦA TỪNG MICROSERVICE

### 2.1. Auth & Identity Service (`auth_db`)
- **Vai trò**: Quản trị người dùng, tài khoản, chuỗi cửa hàng và phân quyền RBAC.
- **Danh sách bảng**:
  - `store`: Quản lý danh sách cửa hàng/chi nhánh trong hệ thống.
  - `role`: Danh mục vai trò (Admin, Manager, Staff, Customer,...).
  - `permission`: Danh mục quyền hạn chi tiết trong hệ thống.
  - `role_permission`: Bảng trung gian gán quyền cho vai trò.
  - `user_account`: Tài khoản đăng nhập (chứa email, password hash, role).
  - `employee`: Hồ sơ nhân viên, liên kết với `user_account` và `store`.
  - `customer`: Hồ sơ khách hàng, hỗ trợ cả khách đăng ký tài khoản lẫn khách vãng lai (`user_id IS NULL`).
  - `auth_tokens`: Lưu trữ Refresh Token & Token khôi phục mật khẩu.
  - `pos_auth`: Lưu mã PIN và trạng thái khóa đăng nhập nhanh tại máy POS.

### 2.2. Catalog Service (`catalog_db`)
- **Vai trò**: Quản lý danh mục hàng hóa niêm yết chung toàn chuỗi.
- **Danh sách bảng**:
  - `category`: Cây danh mục sản phẩm (hỗ trợ phân cấp cha-con `parent_id`, cờ `is_perishable` đánh dấu hàng tươi sống/hạn ngắn).
  - `product`: Sản phẩm niêm yết (tên, barcode EAN-13, giá niêm yết `unit_price`, nhà cung cấp gốc).
  - `product_price_history`: Nhật ký biến động giá niêm yết sản phẩm.

### 2.3. Inventory Service (`inventory_db`)
- **Vai trò**: Quản lý lô hàng, kho bãi, tồn kho chi tiết và xuất kho.
- **Danh sách bảng**:
  - `product_batch`: Quản lý lô hàng (hạn sử dụng `expiry_date`, giá vốn `cost_price`, giá bán lô, chương trình khuyến mãi tự động `promotion_applied`).
  - `warehouse_block`: Khối/kệ kho (`type`: kho tổng hoặc kệ bán hàng).
  - `location`: Vị trí ô/vị trí chi tiết trên kệ.
  - `inventory_item`: Số lượng tồn kho thực tế (`quantity_on_hand`, `quantity_on_shelf`, `quantity_reserved`).
  - `inventory_movement`: Lịch sử biến động tồn kho (nhập, xuất, điều chỉnh, giữ hàng, giải phóng).
  - `stock_out_order` & `stock_out_detail`: Đơn xuất kho và chi tiết xuất kho (hủy hàng, trả NCC, xuất bán).
  - `processed_events` & `outbox_events`: Đảm bảo SAGA & Idempotency.

### 2.4. Order Service (`order_db`)
- **Vai trò**: Quản lý vòng đời đơn hàng bán lẻ và đơn giao hàng.
- **Danh sách bảng**:
  - `sale_order`: Đơn hàng bán (hỗ trợ giao hàng/nhận tại cửa hàng, trạng thái thanh toán, mã coupon, tổng tiền).
  - `sale_order_detail`: Chi tiết mặt hàng trong đơn (snapshot tên sản phẩm, `batch_id`, `product_id`, số lượng, đơn giá).
  - `processed_events` & `outbox_events`: Hạ tầng sự kiện SAGA.

### 2.5. Supplier Service (`supplier_db`)
- **Vai trò**: Quản lý nhà cung cấp và quy trình nhập hàng (Purchase Order).
- **Danh sách bảng**:
  - `supplier`: Thông tin nhà cung cấp, hạn mức tín dụng (`credit_limit`), công nợ hiện tại (`current_debt`), điều khoản thanh toán (`payment_terms`).
  - `purchase_order`: Đơn đặt hàng nhập kho từ nhà cung cấp.
  - `purchase_order_detail`: Chi tiết từng sản phẩm và lô hàng trong đơn nhập.
  - `processed_events` & `outbox_events`: Hạ tầng sự kiện SAGA.

### 2.6. Payment Service (`payment_db`)
- **Vai trò**: Xử lý giao dịch thanh toán và cổng thanh toán VNPay.
- **Danh sách bảng**:
  - `payment`: Giao dịch thanh toán (hỗ trợ liên kết đa hình `reference_type`: 'SaleOrder' hoặc 'PurchaseOrder').
  - `vnpay_transaction`: Nhật ký giao dịch cổng thanh toán VNPay (mã giao dịch, mã phản hồi, IPN check, trạng thái).
  - `processed_events` & `outbox_events`: Hạ tầng sự kiện SAGA.

### 2.7. Settings Service (`settings_db`)
- **Vai trò**: Cấu hình hệ thống, chính sách bán hàng & quản lý Mã giảm giá (Coupons).
- **Danh sách bảng**:
  - `security_settings`: Cấu hình bảo mật hệ thống (Singleton table `id=1`).
  - `sales_settings`: Cấu hình khuyến mãi tự động hàng hết hạn & chiết khấu theo loại khách hàng (Singleton table `id=1`).
  - `settings_history`: Audit log ghi lại mọi sự thay đổi cấu hình.
  - `coupons`: Quản lý mã giảm giá toàn hệ thống (phần trăm, tiền cố định, freeship).
  - `coupon_usages`: Nhật ký sử dụng coupon của từng khách hàng.

### 2.8. AI Chatbot & Recommendation Service (`chatbot_db`)
- **Vai trò**: Trợ lý AI, truy vấn RAG sản phẩm và Động cơ gợi ý sản phẩm (Recommendation Engine).
- **Danh sách bảng**:
  - `chat_session` & `chat_message`: Lưu trữ phiên thoại và nội dung tin nhắn trợ lý AI.
  - `product_knowledge_base`: Kho tri thức RAG tích hợp Vector 768 chiều (`embedding`) & Full-Text Search.
  - `co_purchase_stats` & `product_order_frequency`: Dữ liệu phân tích luật kết hợp Apriori (Support, Confidence, Lift).
  - `user_product_interaction` & `item_similarity`: Ma trận tương tác người dùng - sản phẩm và độ tương đồng mặt hàng (Collaborative Filtering).
  - `recommendation_feedback`: Ghi nhận phản hồi click/mua từ gợi ý để tối ưu hóa trọng số.
  - `ensemble_weights` & `ensemble_weights_history`: Quản lý và theo dõi lịch sử trọng số Hybrid Recommendation.
  - `chatbot_audit_log`: Nhật ký ghi lại các hành động ghi/tác động hệ thống do Chatbot thực hiện.

### 2.9. Statistics Service (`statistics`)
- **Vai trò**: Tổng hợp báo cáo doanh thu, tồn kho, công nợ.
- **Đặc điểm**: Dịch vụ Stateless, không lưu trữ cơ sở dữ liệu ghi riêng mà truy vấn trực tiếp qua API REST internal của các service tương ứng kết hợp bộ đệm Redis.

---

## 3. MÃ DBDIAGRAM (DBML CODE) HOÀN CHỈNH

Sao chép toàn bộ đoạn mã DBML dưới đây và dán vào trang web [dbdiagram.io](https://dbdiagram.io) để hiển thị sơ đồ ERD trực quan toàn hệ thống.

```dbml
// ============================================================
// MICROSERVICES DATABASE DIAGRAM (MINI-MART BACKEND)
// Compatible with dbdiagram.io (DBML v2.0)
// ============================================================

Project MiniMart_Backend {
  database_type: 'PostgreSQL'
  Note: 'Sơ đồ tổng thể Cơ sở dữ liệu 9 Microservices cho Hệ thống Quản lý Chuỗi Cửa hàng Bán lẻ Mini-Mart'
}

// ============================================================
// 1. SERVICE AUTH & IDENTITY (auth_db)
// ============================================================
Table auth_store {
  id bigint [pk, increment]
  name text [not null]
  address text
  phone text
  manager_id bigint
  is_active boolean [not null, default: true]
  created_at timestamptz [default: `now()`]
  Note: 'Bảng root đa cửa hàng (Multi-Tenancy Root)'
}

Table auth_permission {
  id bigint [pk, increment]
  code text [unique, not null]
  description text
}

Table auth_role {
  id bigint [pk, increment]
  name text [unique, not null]
  description text
}

Table auth_role_permission {
  role_id bigint [ref: > auth_role.id]
  permission_id bigint [ref: > auth_permission.id]
  indexes {
    (role_id, permission_id) [pk]
  }
}

Table auth_user_account {
  id bigint [pk, increment]
  username text [unique, not null]
  email text [unique, not null]
  password_hash text [not null]
  role_id bigint [not null, ref: > auth_role.id]
  is_active boolean [not null, default: true]
  last_login timestamptz
}

Table auth_employee {
  user_id bigint [pk, ref: - auth_user_account.id]
  store_id bigint [ref: > auth_store.id]
  full_name text [not null]
  address text
  phone text
  gender text
  dob date
}

Table auth_customer {
  id bigint [pk, increment]
  user_id bigint [ref: > auth_user_account.id]
  full_name text [not null]
  phone text
  address text
  gender text
  dob date
  total_spent numeric [default: 0]
  customer_type text [default: 'retail']
  is_active boolean [not null, default: true]
}

Table auth_tokens {
  id bigint [pk, increment]
  user_id bigint [not null, ref: > auth_user_account.id]
  token_hash text [not null]
  type text [not null]
  expires_at timestamptz [not null]
}

Table auth_pos_auth {
  user_id bigint [pk, ref: - auth_user_account.id]
  pin_hash text [not null]
  failed_attempts int [default: 0]
  locked_until timestamptz
  is_enabled boolean [default: true]
  last_login timestamptz
}

Ref: auth_store.manager_id > auth_user_account.id

// ============================================================
// 2. SERVICE CATALOG (catalog_db)
// ============================================================
Table catalog_category {
  id bigint [pk, increment]
  parent_id bigint [ref: > catalog_category.id]
  name text [not null]
  image_url text
  description text
  sort_order int [not null, default: 0]
  is_perishable boolean [not null, default: false]
}

Table catalog_product {
  id bigint [pk, increment]
  category_id bigint [not null, ref: > catalog_category.id]
  name text [not null]
  image_url text
  unit_price numeric [not null, default: 0]
  is_active boolean [not null, default: true]
  vendor text
  barcode text [unique]
}

Table catalog_product_price_history {
  id bigint [pk, increment]
  product_id bigint [not null, ref: > catalog_product.id]
  old_price numeric [not null]
  new_price numeric [not null]
  reason text
  changed_by bigint
  changed_at timestamptz [default: `now()`]
}

// ============================================================
// 3. SERVICE INVENTORY (inventory_db)
// ============================================================
Table inventory_product_batch {
  id bigint [pk, increment]
  store_id bigint [not null]
  product_id bigint [not null]
  cost_price numeric [not null]
  unit_price numeric [not null]
  discount_percentage numeric [default: 0]
  quantity int [not null]
  mfg_date date
  expiry_date date
  status text [not null, default: 'active']
  promotion_applied text [not null, default: 'none']
  updated_at timestamptz [default: `now()`]
  notes text
}

Table inventory_warehouse_block {
  id bigint [pk, increment]
  store_id bigint [not null]
  name text [not null]
  type text [not null, default: 'warehouse']
  rows int [not null]
  cols int [not null]
  column_gaps "int[]"
}

Table inventory_location {
  id bigint [pk, increment]
  block_id bigint [not null, ref: > inventory_warehouse_block.id]
  name text [not null]
  position int [not null]
  max_capacity int [not null, default: 100]
  is_active boolean [not null, default: true]
}

Table inventory_item {
  id bigint [pk, increment]
  product_batch_id bigint [not null, ref: > inventory_product_batch.id]
  location_id bigint [ref: > inventory_location.id]
  quantity_on_hand int [not null, default: 0]
  quantity_on_shelf int [not null, default: 0]
  quantity_reserved int [not null, default: 0]
  reorder_point int [not null, default: 10]
}

Table inventory_movement {
  id bigint [pk, increment]
  inventory_item_id bigint [not null, ref: > inventory_item.id]
  movement_type text [not null]
  quantity int [not null]
  reason text
  moved_at timestamptz [not null, default: `now()`]
  performed_by bigint
}

Table inventory_stock_out_order {
  id bigint [pk, increment]
  store_id bigint [not null]
  order_date timestamptz [not null, default: `now()`]
  completed_date timestamptz
  reason text [not null, default: 'sales']
  destination text
  status text [not null, default: 'draft']
  total_price numeric [not null, default: 0]
  created_by bigint [not null]
}

Table inventory_stock_out_detail {
  id bigint [pk, increment]
  so_id bigint [not null, ref: > inventory_stock_out_order.id]
  batch_id bigint [not null, ref: > inventory_product_batch.id]
  quantity int [not null]
  unit_price numeric [not null, default: 0]
  total_price numeric [not null, default: 0]
}

// ============================================================
// 4. SERVICE ORDER (order_db)
// ============================================================
Table order_sale_order {
  id bigint [pk, increment]
  store_id bigint [not null]
  customer_id bigint
  created_by bigint
  order_date timestamptz [not null, default: `now()`]
  delivery_type text [not null, default: 'pickup']
  address text
  shipping_fee numeric [not null, default: 0]
  discount_percentage numeric [not null, default: 0]
  total_amount numeric [not null, default: 0]
  payment_status text [not null, default: 'pending']
  status text [not null, default: 'draft']
  coupon_code text
  coupon_discount numeric [not null, default: 0]
  payment_method text
}

Table order_sale_order_detail {
  id bigint [pk, increment]
  order_id bigint [not null, ref: > order_sale_order.id]
  product_id bigint
  product_name text [not null]
  batch_id bigint [not null]
  quantity int [not null, default: 1]
  unit_price numeric [not null]
  total_price numeric [not null]
}

// ============================================================
// 5. SERVICE SUPPLIER (supplier_db)
// ============================================================
Table supplier_supplier {
  id bigint [pk, increment]
  company_name text [not null]
  phone text
  address text
  account_number text
  payment_terms text [not null, default: 'cod']
  credit_limit numeric [not null, default: 0]
  current_debt numeric [not null, default: 0]
  is_active boolean [not null, default: true]
}

Table supplier_purchase_order {
  id bigint [pk, increment]
  store_id bigint [not null]
  supplier_id bigint [not null, ref: > supplier_supplier.id]
  order_date timestamptz [not null, default: `now()`]
  received_date timestamptz
  shipping_fee numeric [not null, default: 0]
  discount_percentage numeric [not null, default: 0]
  total_price numeric [not null, default: 0]
  status text [not null, default: 'draft']
  payment_status text [not null, default: 'unpaid']
  created_by bigint
  notes text
}

Table supplier_purchase_order_detail {
  id bigint [pk, increment]
  po_id bigint [not null, ref: > supplier_purchase_order.id]
  product_id bigint [not null]
  product_name text [not null]
  batch_id bigint
  quantity int [not null, default: 1]
  cost_price numeric [not null]
  total_price numeric [not null]
}

// ============================================================
// 6. SERVICE PAYMENT (payment_db)
// ============================================================
Table payment_payment {
  id bigint [pk, increment]
  store_id bigint [not null]
  amount numeric [not null]
  method text [not null]
  status text [not null, default: 'pending']
  reference_type text [not null]
  reference_id bigint [not null]
  items jsonb [not null, default: '[]']
  delivery_type text [not null, default: 'pickup']
  payment_date timestamptz [not null, default: `now()`]
  created_by bigint
  notes text
}

Table payment_vnpay_transaction {
  id bigint [pk, increment]
  payment_id bigint [ref: > payment_payment.id]
  reference_id bigint [not null]
  vnp_txn_ref text [unique, not null]
  vnp_transaction_no text
  vnp_amount bigint [not null]
  vnp_response_code text
  vnp_transaction_status text
  vnp_bank_code text
  vnp_bank_tran_no text
  vnp_card_type text
  vnp_pay_date text
  vnp_order_info text
  vnp_ip_addr text
  vnp_locale text
  vnp_secure_hash text
  status text [not null, default: 'pending']
  payment_url text
  ipn_verified boolean [not null, default: false]
  return_url_accessed boolean [not null, default: false]
  origin text [not null, default: 'pos']
}

// ============================================================
// 7. SERVICE SETTINGS (settings_db)
// ============================================================
Table settings_security_settings {
  id int [pk, default: 1]
  max_failed_attempts int [not null, default: 5]
  lock_duration_minutes int [not null, default: 30]
  updated_by bigint
  updated_at timestamptz [default: `now()`]
}

Table settings_sales_settings {
  id int [pk, default: 1]
  auto_promotion_enabled boolean [not null, default: false]
  promotion_start_time time
  promotion_discount_percentage numeric [not null, default: 0]
  discount_retail numeric [not null, default: 0]
  discount_wholesale numeric [not null, default: 5]
  discount_vip numeric [not null, default: 10]
  apply_to_expiring_today boolean [not null, default: true]
  apply_to_expiring_tomorrow boolean [not null, default: false]
  updated_by bigint
  updated_at timestamptz [default: `now()`]
}

Table settings_settings_history {
  id bigint [pk, increment]
  setting_type text [not null]
  old_value jsonb [not null]
  new_value jsonb [not null]
  changed_by bigint
  change_reason text
  changed_at timestamptz [default: `now()`]
}

Table settings_coupons {
  id bigint [pk, increment]
  code text [unique, not null]
  description text
  discount_type text [not null, default: 'percent']
  discount_value numeric [not null, default: 0]
  min_order_amount numeric [not null, default: 0]
  max_uses int
  used_count int [not null, default: 0]
  is_active boolean [not null, default: true]
  is_public boolean [not null, default: true]
  starts_at timestamptz
  expires_at timestamptz
  created_by bigint
  created_at timestamptz [default: `now()`]
}

Table settings_coupon_usages {
  id bigint [pk, increment]
  coupon_id bigint [not null, ref: > settings_coupons.id]
  customer_id bigint [not null]
  order_id bigint
  used_at timestamptz [default: `now()`]
}

// ============================================================
// 8. SERVICE CHATBOT & AI RECOMMENDATIONS (chatbot_db)
// ============================================================
Table chatbot_chat_session {
  id bigint [pk, increment]
  user_id bigint [not null]
  user_type text [not null, default: 'customer']
  store_id bigint
  started_at timestamptz [not null, default: `now()`]
  ended_at timestamptz
  is_active boolean [not null, default: true]
  metadata jsonb
}

Table chatbot_chat_message {
  id bigint [pk, increment]
  session_id bigint [not null, ref: > chatbot_chat_session.id]
  role text [not null]
  content text [not null]
  intent text
  metadata jsonb
  created_at timestamptz [not null, default: `now()`]
}

Table chatbot_product_knowledge_base {
  id bigint [pk, increment]
  product_id bigint [not null]
  store_id bigint [not null]
  content text [not null]
  embedding "vector(768)"
  fts_content tsvector
  category_name text
  unit_price numeric [default: 0]
  is_in_stock boolean [default: true]
  quantity_on_shelf int [default: 0]
  last_synced_at timestamptz [default: `now()`]
}

Table chatbot_co_purchase_stats {
  id bigint [pk, increment]
  product_id_a bigint [not null]
  product_id_b bigint [not null]
  store_id bigint [not null]
  co_purchase_count int [default: 1]
  last_updated_at timestamptz [default: `now()`]
  support numeric [default: 0]
  confidence_ab numeric [default: 0]
  confidence_ba numeric [default: 0]
  lift numeric [default: 0]
  total_orders int [default: 0]
}

Table chatbot_product_order_frequency {
  product_id bigint [not null]
  store_id bigint [not null]
  order_count int [default: 0]
  last_computed_at timestamptz [default: `now()`]
  indexes {
    (product_id, store_id) [pk]
  }
}

Table chatbot_user_product_interaction {
  user_id bigint [not null]
  product_id bigint [not null]
  store_id bigint [not null]
  purchase_count int [default: 0]
  total_quantity int [default: 0]
  last_purchased_at timestamptz
  interaction_score numeric [default: 0]
  indexes {
    (user_id, product_id, store_id) [pk]
  }
}

Table chatbot_item_similarity {
  item_a bigint [not null]
  item_b bigint [not null]
  store_id bigint [not null]
  similarity numeric [not null]
  common_users int [default: 0]
  computed_at timestamptz [default: `now()`]
  indexes {
    (item_a, item_b, store_id) [pk]
  }
}

Table chatbot_recommendation_feedback {
  id bigserial [pk]
  user_id bigint
  product_id bigint
  store_id bigint [not null]
  source text [not null]
  action text [not null]
  session_id text
  recommendation_score numeric
  metadata jsonb
  created_at timestamptz [default: `now()`]
}

Table chatbot_ensemble_weights {
  store_id bigint [pk]
  alpha numeric [default: 0.40]
  beta numeric [default: 0.25]
  gamma numeric [default: 0.25]
  delta numeric [default: 0.10]
  updated_at timestamptz [default: `now()`]
}

Table chatbot_ensemble_weights_history {
  id bigserial [pk]
  store_id bigint [not null]
  alpha numeric [not null]
  beta numeric [not null]
  gamma numeric [not null]
  delta numeric [not null]
  feedback_count int [default: 0]
  trigger_type text [default: 'nightly']
  created_at timestamptz [default: `now()`]
}

Table chatbot_audit_log {
  id bigserial [pk]
  user_id bigint
  session_id bigint [ref: > chatbot_chat_session.id]
  action_type text [not null]
  payload jsonb
  result jsonb
  created_at timestamptz [default: `now()`]
}

// ============================================================
// 9. CROSS-SERVICE LOGICAL REFERENCES (MICROSERVICE BOUNDARIES)
// Note: Các liên kết này mang tính chất logic (Cross-Service boundary)
// không tạo Foreign Key vật lý ở cấp DB để đảm bảo tính độc lập Microservices.
// ============================================================

// Multi-Tenancy Store References
Ref: inventory_product_batch.store_id > auth_store.id
Ref: inventory_warehouse_block.store_id > auth_store.id
Ref: inventory_stock_out_order.store_id > auth_store.id
Ref: order_sale_order.store_id > auth_store.id
Ref: supplier_purchase_order.store_id > auth_store.id
Ref: payment_payment.store_id > auth_store.id
Ref: chatbot_chat_session.store_id > auth_store.id

// Catalog Product References
Ref: inventory_product_batch.product_id > catalog_product.id
Ref: order_sale_order_detail.product_id > catalog_product.id
Ref: supplier_purchase_order_detail.product_id > catalog_product.id
Ref: chatbot_product_knowledge_base.product_id > catalog_product.id

// Inventory Batch References
Ref: order_sale_order_detail.batch_id > inventory_product_batch.id
Ref: supplier_purchase_order_detail.batch_id > inventory_product_batch.id

// Customer & Account References
Ref: order_sale_order.customer_id > auth_customer.id
Ref: settings_coupon_usages.customer_id > auth_customer.id

// User/Employee Audit References
Ref: order_sale_order.created_by > auth_user_account.id
Ref: inventory_stock_out_order.created_by > auth_user_account.id
Ref: inventory_movement.performed_by > auth_user_account.id
Ref: payment_payment.created_by > auth_user_account.id
Ref: supplier_purchase_order.created_by > auth_user_account.id
```
