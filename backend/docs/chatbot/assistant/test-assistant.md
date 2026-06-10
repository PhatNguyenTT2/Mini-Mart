# 🤖 Kịch Bản Demo: Chatbot Action Assistant (Restructured 8 Acts)

> **Thời lượng demo:** ~12-15 phút
> **Cấu trúc:** Setup → 8 ACTs → Kết luận
> **Yêu cầu:** Chatbot service running, Catalog + Inventory + Order services online

---

## ⚙️ BƯỚC 1: CHUẨN BỊ

### 1.1 Khởi động hệ thống

```bash
# Terminal 1: Chatbot service
cd backend/services/chatbot && npm start    # Port 3008

# Verify health
curl http://localhost:3008/health
```

**Kết quả mong đợi:**
```json
{ "status": "ok", "service": "chatbot-service" }
```

### 1.2 Chuẩn bị tài khoản demo

| Tài khoản | userType | Mục đích | Dùng cho ACT |
|-----------|----------|----------|--------------|
| Customer (web store login) | `customer` | Mua sắm, giỏ hàng, theo dõi đơn | ACT 1, 2 |
| Employee POS (ID: 5, PIN: 123456) | `employee` | POS, tạo đơn, xem lịch sử đơn | ACT 3, 4, 5 |
| Manager (admin store login) | `manager` | Xem báo cáo, thống kê, CRUD thực thể | ACT 6, 7 |

---

## 🎬 BƯỚC 2: TRÌNH DIỄN KỊCH BẢN (8 ACTS)

### ACT 1: Customer/POS Employee — Search, Cart & Smart Add

> **Mục đích:** Chứng minh luồng Customer/POS Employee tiện ích gồm Check Price, Stock, Pronoun Resolution, Clarification, và Smart Add.
> **Context:** Đăng nhập Customer, mở widget Chatbot.
> **Intent routing:** `userType = 'customer'` → `ADD_TO_CART` → `cart.handler.js`

**📝 Kịch bản:**

| Bước | Gõ vào chatbot | Intent | Kết quả mong đợi |
|:---:|----------------|--------|-------------------|
| 1 | **"Giá nabati bao nhiêu?"** | `CHECK_PRICE` | Product card: Bánh xốp phô mai Nabati hộp 150g — 28,000đ |
| 2 | **"Còn bao nhiêu?"** | `CHECK_STOCK` | Pronoun resolve "nabati" → "Còn 298 sản phẩm đang bán" (on_hand DB check) |
| 3 | **"Thêm 3 cái đó vào giỏ"** | `ADD_TO_CART` | Pronoun resolve → "Đã thêm 3 Nabati vào giỏ hàng" |
| 4 | **"Giá red bull và coca"** | `CHECK_PRICE` | 2 product cards: Red Bull 12,000đ + Coca 9,000đ |
| 5 | **"Thêm cái đó vào giỏ"** | `ADD_TO_CART` | ⚠️ Chatbot hỏi lại: "Bạn muốn thêm SP nào? [1] Red Bull [2] Coca-Cola" (Clarification State) |
| 6 | **"2"** | (CLARIFYING) | Chọn Coca-Cola → "Đã thêm Coca-Cola vào giỏ hàng" |
| 7 | **"Thêm 2 red bull"** | `ADD_TO_CART` | FTS exact match → Auto-add Red Bull x2 vào giỏ hàng |
| 8 | **"Đổi số lượng nabati thành 5"** | `UPDATE_CART_ITEM` | "Đã cập nhật số lượng thành 5" |
| 9 | **"Xem giỏ hàng"** | `VIEW_CART` | Action `VIEW_CART` → Frontend tự động mở Drawer Giỏ hàng |(Chỉ áp dụng cho Customer)
| 10 | **"Thanh toán"** | `CHECKOUT_GUIDE` | Action `NAVIGATE → /checkout` |
| 11 | **"Lưu hóa đơn"** | (Chỉ áp dụng cho POS Employee)->Cần cập nhật cho Customer

**✅ Checkpoint:** Khách hàng thêm giỏ hàng thành công, chatbot nhận diện đại từ chính xác và tự động resolve các tương tác nhập nhằng.

---

### ACT 2: Customer — Multi-turn Order & Tracking

> **Mục đích:** Chứng minh luồng Khách hàng tự chốt đơn, xử lý xen ngang câu hỏi và quản lý đơn hàng của mình.
> **Context:** Customer ở giao diện Chatbot Storefront.

**📝 Kịch bản:**

| Bước | Gõ vào chatbot | Intent | Kết quả mong đợi |
|:---:|----------------|--------|-------------------|
| 1 | **"Tạo đơn 2 Coca, 1 Nabati"** | `CREATE_ORDER` | Recap: "Bạn muốn tạo đơn: Coca x2, Nabati x1? Tổng: 46,000đ. Nhập 'Đồng ý' để tạo." |
| 2 | **"Giá pepsi bao nhiêu?"** | `CHECK_PRICE` | 💡 Luồng xen ngang: Trả lời giá Pepsi, nhưng vẫn giữ nguyên trạng thái chờ tạo đơn ở bước 1. |
| 3 | **"Đồng ý"** | (CONFIRMING) | Nhận diện confirm → Đơn hàng được tạo thành công, trả về mã đơn (Ví dụ: #2538) |
| 4 | **"Xem đơn hàng gần đây"** | `ORDER_STATUS` | Danh sách 5 đơn hàng gần nhất của chính Customer đó |
| 5 | **"Theo dõi đơn #2538"** | `TRACK_ORDER` | Đi qua ActionExecutor → Action `NAVIGATE → /orders/2538` |
| 6 | **"Hủy đơn #2538"** | `CANCEL_ORDER` | ⚠️ Hỏi xác nhận: "Bạn có chắc chắn muốn hủy đơn hàng #2538?" |
| 7 | **"Đồng ý"** | (CONFIRMING) | Ownership check thành công → Trả về: "Đơn hàng #2538 đã được hủy thành công." |

**✅ Checkpoint:** State Interruption được khôi phục chuẩn xác. Khách hàng không thể hủy đơn của người khác (Ownership check security layer).

---

### ACT 3: POS Employee — Order History & Tracking

> **Mục đích:** Employee điều khiển mở History Modal và quản lý đơn hàng ngay tại quầy POS.

**📝 Kịch bản:**

| Bước | Gõ vào chatbot | Intent | Kết quả mong đợi |
|:---:|----------------|--------|-------------------|
| 1 | **"Xem đơn hàng gần đây"** | `ORDER_STATUS` | Danh sách 5 đơn hàng do nhân viên này tạo hoặc xử lý tại POS |
| 2 | **"Mở lịch sử đơn hàng"** | `VIEW_ORDER_HISTORY` | Action `OPEN_MODAL` với payload `POSEmployeeOrdersModal` → Mở modal ngay trên màn hình POS |
| 3 | **"Theo dõi đơn #2538"** | `TRACK_ORDER` | Hiển thị chi tiết trạng thái, list mặt hàng, và khách hàng của đơn #2538 |
| 4 | **"Hủy đơn #2538"** | `CANCEL_ORDER` | Yêu cầu xác nhận → Nhân viên đồng ý → Hủy đơn trên hệ thống |

**✅ Checkpoint:** Action Executor phát ra hành động thay đổi UI trực tiếp ở POS (mở Modal Lịch sử Đơn Hàng).

---

### ACT 4: POS Employee — Multi-turn Order Creation

> **Mục đích:** Nhân viên POS hỗ trợ khách mua nhanh bằng hội thoại đa lượt tại quầy.

**📝 Kịch bản:**

| Bước | Gõ vào chatbot | Intent | Kết quả mong đợi |
|:---:|----------------|--------|-------------------|
| 1 | **"Thêm 3 coca vào POS"** | `POS_ADD_ITEM` | "Đã thêm 3 Coca-Cola vào POS thành công" |
| 2 | **"Tạo đơn 2 Coca, 1 Chupachup"** | `CREATE_ORDER` | Recap và yêu cầu confirmation tạo đơn POS |
| 3 | **"Đồng ý"** | (CONFIRMING) | Chốt tạo đơn tại POS |
| 4 | **"Kiểm tra thanh toán đơn #1"** | `PAYMENT_CHECK` | Kiểm hàng thanh toán trên đơn để đóng hóa đơn |

---

### ACT 5: Manager — Dashboard & Report Queries (Kịch bản sơ bộ)

> **Mục đích:** Manager truy vấn nhanh báo cáo tài chính và tình trạng vận hành chuỗi.
> **Context:** Đăng nhập Manager, mở Chatbot Admin Dashboard.

**📝 Kịch bản:**

| Bước | Gõ vào chatbot | Intent | Kết quả mong đợi |
|:---:|----------------|--------|-------------------|
| 1 | **"Doanh thu hôm nay bao nhiêu?"** | `REPORT_SALES` | Lấy dữ liệu bán hàng real-time từ Order Service → Thông báo tổng doanh thu hôm nay |
| 2 | **"Sản phẩm nào bán chạy nhất tuần này?"** | `REPORT_TOP_PRODUCTS` | Danh sách top 5 mặt hàng bán chạy và số lượng đã xuất kho |
| 3 | **"Kiểm tra hàng sắp hết"** | `REPORT_LOW_STOCK` | Cảnh báo các mặt hàng đang dưới định mức tồn kho tối thiểu |
| 4 | **"Xem báo cáo lợi nhuận tháng này"** | `REPORT_PROFIT` | Action `NAVIGATE → /statistics/profit` để dẫn Manager thẳng tới biểu đồ phân tích lợi nhuận |

---

### ACT 6: Manager — Entity Management (Kịch bản sơ bộ)

> **Mục đích:** CRUD nhanh các thực thể hệ thống phục vụ back-office qua Chatbot.

**📝 Kịch bản Minh Họa:**

*   **Quản lý Khách hàng (Customer):**
    *   *Manager*: "Tìm khách hàng Ngo Xuan Phuc"
    *   *Chatbot*: (Intent: `MANAGE_CUSTOMER_SEARCH`) → "Tìm thấy: Khách hàng Ngo Xuan Phuc, số ĐT: 090xxxx999, Hạng: Retail. Đơn hàng gần nhất: ORD-1002."
    *   *Manager*: "Nâng hạng khách này lên VIP"
    *   *Chatbot*: (Intent: `MANAGE_CUSTOMER_UPDATE`) → "Xác nhận nâng hạng Khách hàng Ngo Xuan Phuc lên VIP?" → "Đồng ý" → "Đã cập nhật hạng VIP thành công."
    *   *Manager*: "Danh sách khách hàng VIP"
    *   *Chatbot*: (Intent: `MANAGE_CUSTOMER_LIST`) → Action `NAVIGATE → /customers?type=vip`

*   **Quản lý Nhà Cung Cấp (Supplier):**
    *   *Manager*: "Danh sách nhà cung cấp"
    *   *Chatbot*: (Intent: `MANAGE_SUPPLIER_LIST`) → Action `NAVIGATE → /suppliers`
    *   *Manager*: "Thông tin nhà cung cấp Vinamilk"
    *   *Chatbot*: (Intent: `MANAGE_SUPPLIER_SEARCH`) → "NCC: Công ty Cổ phần Sữa Việt Nam. Địa chỉ: Q7 TPHCM. Liên hệ: vinamilk@posmart.vn. Danh mục cung cấp: Sữa & chế phẩm sữa."

*   **Quản lý Tồn Kho (Inventory):**
    *   *Manager*: "Kiểm tra tồn kho kho chính"
    *   *Chatbot*: (Intent: `MANAGE_INVENTORY_CHECK`) → "Tổng tồn kho chính: 12,050 sản phẩm. Giá trị ước tính: 450,000,000 VND. Có 3 sản phẩm đã hết hàng."
    *   *Manager*: "Sản phẩm nào hết hàng trong kho/trên kệ?"
    *   *Chatbot*: (Intent: `MANAGE_INVENTORY_STOCKOUT`) → "Hiện có: Bánh Custas hộp 6, Sữa chua TH ít đường đang hết hàng (stock = 0)."

---

### ACT 7: Security & Rate Limiting

> **Mục đích:** Chứng minh hệ thống kiên cố trước các hành vi bất hợp lệ hoặc spam.

**📝 Kịch bản:**

1.  **Sai phân quyền (RBAC Check):**
    *   Đăng nhập tài khoản `Customer`.
    *   Gõ: `"Doanh thu hôm nay bao nhiêu?"`
    *   *Kết quả*: Trả về lỗi: *"Rất tiếc, bạn không có quyền truy cập báo cáo doanh thu."* (Config `managerOnly` chặn truy cập).
2.  **Rate limiting:**
    *   Gõ liên tục 6 câu lệnh tác động ghi (giỏ hàng/tạo đơn) trong vòng ngắn.
    *   *Kết quả*: Câu lệnh thứ 6 bị chặn: *"Hệ thống chatbot đang bận. Vui lòng thử lại sau ít phút."* (Rate-limiter kích hoạt).
3.  **Sản phẩm không tồn tại:**
    *   Gõ: `"Thêm bánh xốp abcxyz vào giỏ"`
    *   *Kết quả*: *"Không tìm thấy bất kỳ sản phẩm nào tương tự."*

---

### ACT 8: Manager — Batch Discount & Conflict Resolution

> **Mục đích:** Hướng dẫn Manager thiết lập giảm giá hàng loạt lô hàng sản phẩm, giải quyết xung đột giảm giá hoặc phân luồng tự động cho mặt hàng perishable.
> **Context:** Đăng nhập Manager, mở Chatbot Admin Dashboard.

**📝 Kịch bản:**

| Bước | Gõ vào chatbot | Intent | Kết quả mong đợi |
|:---:|----------------|--------|-------------------|
| 1 | **"giảm giá 15% bánh nabati"** | `MANAGE_BATCH_DISCOUNT` | Recap & Xác nhận: "Xác nhận thiết lập giảm giá 15% cho tất cả lô hàng của sản phẩm \"Nabati Phô Mai\"? (Đồng ý/Hủy bỏ)" |
| 2 | **"Đồng ý"** | (CONFIRMING) | "Đã áp dụng giảm giá 15% cho các lô hàng của sản phẩm \"Nabati Phô Mai\" thành công." |
| 3 | **"giảm 20% mì hảo hảo"** | `MANAGE_BATCH_DISCOUNT` | Phát hiện xung đột -> "⚠️ Sản phẩm \"Mì Hảo Hảo\" hiện đang có lô hàng giảm giá 10%. Bạn có muốn ghi đè thành 20% cho tất cả lô hàng không? (Đồng ý/Hủy bỏ)" |
| 4 | **"Đồng ý"** | (CONFIRMING) | "Đã áp dụng giảm giá 20% cho các lô hàng của sản phẩm \"Mì Hảo Hảo\" thành công." |
| 5 | **"giảm giá 30% sữa vinamilk"** | `MANAGE_BATCH_DISCOUNT` | Phân luồng perishable -> "Sản phẩm \"Sữa Vinamilk\" thuộc nhóm hàng tươi sống/perishable. Yêu cầu chuyển đến màn hình Cấu hình Khuyến mãi để tránh sai lệch định giá tự động." + Action NAVIGATE tới `/inventory/batches?productId=...` |

---

## 📊 BƯỚC 3: TỔNG KẾT

Chatbot Action Assistant hỗ trợ kiểm soát chặt chẽ thông qua kiến trúc phân quyền và bảo vệ 4 lớp (Rate Limiting, Role Checking, Ownership Checking, và Confirmation Gates). Mọi hành động tác động ghi đều được ghi chép lịch sử chi tiết phục vụ giám sát vận hành.

