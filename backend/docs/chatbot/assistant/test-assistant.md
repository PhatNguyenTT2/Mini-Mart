# 🤖 Kịch Bản Demo: Chatbot Action Assistant

> **Thời lượng demo:** ~10-12 phút
> **Cấu trúc:** Setup → 5 ACTs → Kết luận
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
```
{ "status": "ok", "service": "chatbot-service" }
```

### 1.2 Chuẩn bị 2 tài khoản demo

| Tài khoản | userType | Mục đích | Dùng cho ACT |
|-----------|----------|----------|--------------|
| Customer (web store login) | `customer` | Mua sắm, giỏ hàng, theo dõi đơn | ACT 1, 3 |
| Employee POS (ID: 5, PIN: 123456) | `employee` | POS, tạo đơn, kiểm tra thanh toán | ACT 2, 4 |

### 1.3 Bố trí màn hình

| Vị trí | Nội dung |
|--------|----------|
| **Trái** | Customer/Employee Chatbot UI |
| **Phải** | Terminal logs (xem intent + audit log) |

---

## 🎬 BƯỚC 2: TRÌNH DIỄN 5 LUỒNG CHÍNH

### ACT 1: Tìm kiếm & Giỏ hàng — Customer Nabati Flow

> **Mục đích:** Chứng minh luồng Customer hoàn chỉnh từ tìm kiếm → thêm giỏ → cập nhật → thanh toán.
> **Context:** Đăng nhập Customer (web store), mở chatbot widget.
> **Intent routing:** `userType = 'customer'` → `ADD_TO_CART` → `cart.handler.js`

**📝 Kịch bản:**

| Bước | Gõ vào chatbot | Intent | Kết quả mong đợi |
|:---:|----------------|--------|-------------------|
| 1 | **"Giá nabati bao nhiêu?"** | `CHECK_PRICE` | Product card: Bánh xốp phô mai Nabati hộp 150g — 28,000đ |
| 2 | **"Còn bao nhiêu trên kệ?"** | `CHECK_STOCK` | Pronoun resolve "nabati" → "Còn 298 trên kệ" |
| 3 | **"Thêm 3 cái đó vào giỏ"** | `ADD_TO_CART` | Pronoun resolve → "Đã thêm 3 Nabati vào giỏ hàng" |
| 4 | **"Đổi số lượng thành 5"** | `UPDATE_CART_ITEM` | "Đã cập nhật số lượng thành 5" |
| 5 | **"Xem giỏ hàng"** | `VIEW_CART` | Action `VIEW_CART` → FE mở giỏ hàng |
| 6 | **"Thanh toán"** | `CHECKOUT_GUIDE` | Action `NAVIGATE → /checkout` |

**🎤 Thuyết minh (nói ở bước 3):**

> *"Ở bước 3, người dùng nói 'cái đó' — hệ thống không biết 'cái đó' là gì. Nhưng nhờ Pronoun Resolution, chatbot nhớ sản phẩm vừa hỏi ở bước 1-2 (Nabati) thông qua `lastMentionedProducts` lưu trong session metadata, tự động resolve 'cái đó' = Nabati mà không cần hỏi lại."*

**✅ Checkpoint:** 6 bước xuyên suốt không lỗi, Pronoun Resolution hoạt động → Customer full cart flow chứng minh.

---

### ACT 2: POS Employee — Check Price, Stock Shelf Location & Clarified Add to Cart

> **Mục đích:** Chứng minh luồng POS Employee với:
> - Pronoun Resolution trong việc kiểm tra giá và tồn kho kèm **📍 Vị trí trên kệ hàng (Store Shelf Map)**.
> - Clarification State Machine khi gặp nhập nhằng nhiều sản phẩm.
> - FTS-Boosted Auto-Add khi khớp chính xác.
> - Tạo đơn hàng (CREATE_ORDER) kèm Confirmation Gate.
> **Context:** Đăng nhập POS Terminal (Employee ID: 5, PIN: 123456), mở chatbot bằng F3.
> **Intent routing:** `userType = 'employee'` → Rẽ nhánh các intent tương ứng.

**📝 Kịch bản:**

| Bước | Gõ vào chatbot | Intent | Kết quả mong đợi |
|:---:|----------------|--------|-------------------|
| 1 | **"Giá nabati bao nhiêu?"** | `CHECK_PRICE` | Product card: Bánh xốp phô mai Nabati hộp 150g — 28,000đ |
| 2 | **"Còn bao nhiêu trên kệ?"** | `CHECK_STOCK` | Pronoun resolve "nabati" từ bước 1 → Trả về chi tiết: `On-hand: 300, On-shelf: 298, ... 📍 Vị trí trên kệ: Kệ Bánh Kẹo → BK-03` |
| 3 | **"Thêm 3 cái đó vào giỏ"** | `POS_ADD_ITEM` | Pronoun resolve "nabati" → Thêm trực tiếp 3 Nabati vào giỏ hàng POS |
| 4 | **"Giá red bull và coca"** | `CHECK_PRICE` | 2 product cards: Red Bull lon 250ml — 12,000đ + Coca-Cola chai 390ml — 9,000đ |
| 5 | **"Thêm cái đó vào giỏ"** | `POS_ADD_ITEM` | ⚠️ Chatbot HỎI LẠI: "Bạn muốn thêm SP nào? [1] Red Bull [2] Coca-Cola" |
| 6 | **"1"** | (CLARIFYING) | Chọn Red Bull → "Đã thêm Red Bull vào POS" |
| 7 | **"Thêm 2 coca"** | `POS_ADD_ITEM` | FTS exact match → Auto-add Coca x2 vào giỏ POS |
| 8 | **"Tạo đơn"** | `CREATE_ORDER` | Recap: "Bạn có chắc chắn muốn lập hóa đơn cho các sản phẩm: [Nabati x3, Red Bull x1, Coca x2]?" |
| 9 | **"Đồng ý"** | (CONFIRMING) | Đơn hàng tạo thành công → trả về ID hóa đơn mới |

**🎤 Thuyết minh (nói ở bước 2):**

> *"Ở bước 2, khi nhân viên hỏi 'Còn bao nhiêu trên kệ?', chatbot sử dụng Pronoun Resolution để nhận diện sản phẩm Nabati vừa hỏi ở bước 1. Đồng thời, hệ thống truy vấn dữ liệu từ Location Store Shelf Map của microservice Inventory để phản hồi chính xác tọa độ vị trí: `Kệ Bánh Kẹo → BK-03`."*

**🎤 Thuyết minh (nói ở bước 5-6):**

> *"Khi có từ 2 sản phẩm trở lên được nhắc đến ở bước 4, câu lệnh mơ hồ 'Thêm cái đó vào giỏ' ở bước 5 kích hoạt Clarification State Machine. Trạng thái CLARIFYING được set để khóa luồng và bắt buộc nhân viên phải chọn 1 hoặc 2."*

**🎤 Thuyết minh (nói ở bước 7):**

> *"Nhưng ở bước 7, câu lệnh 'Thêm 2 coca' lại khớp chính xác từ khóa qua Full-Text Search. Điểm số tìm kiếm được cộng thêm 0.15 boost, vượt ngưỡng auto-add trực tiếp mà không cần hỏi lại."*

**✅ Checkpoint:** Location Shelf Mapping + Pronoun Stock Check + Clarification Machine + CREATE_ORDER hoạt động → POS Employee full flow chứng minh.

---

### ACT 3: Đơn hàng — Theo dõi & Hủy

> **Mục đích:** Chứng minh luồng TRACK + CANCEL với Confirmation Gate và Ownership Check.

**📝 Kịch bản:**

| Bước | Gõ vào chatbot | Kết quả mong đợi |
|:---:|----------------|-------------------|
| 1 | **"Xem đơn hàng gần đây"** | Intent: `ORDER_STATUS` → Danh sách 5 đơn gần nhất |
| 2 | **"Theo dõi đơn hàng #1"** | Intent: `TRACK_ORDER` → Action `NAVIGATE → /orders/1` |
| 3 | **"Hủy đơn hàng #1"** | Intent: `CANCEL_ORDER` → ⚠️ Hỏi xác nhận: "Bạn có chắc chắn?" |
| 4 | **"Đồng ý"** | Execute cancel (nếu đơn draft) → "Hủy thành công" |

**🎤 Thuyết minh (nói ở bước 3-4):**

> *"Hệ thống bắt buộc xác nhận trước khi hủy đơn — đây là Confirmation Gate trong ActionExecutor. Ngoài ra, Ownership Check đảm bảo customer chỉ hủy được đơn của chính mình — nếu cố hủy đơn của customer khác, hệ thống sẽ từ chối."*

**✅ Checkpoint:** Confirmation Gate hoạt động → Security layer chứng minh.

---

### ACT 4: Employee POS — Tạo đơn Multi-turn

> **Mục đích:** Chứng minh luồng Employee với State Machine phức tạp.

⚠️ **Chuyển sang tài khoản Employee** (userType = `employee`)

**📝 Kịch bản:**

| Bước | Gõ vào chatbot | Kết quả mong đợi |
|:---:|----------------|-------------------|
| 1 | **"Thêm 3 coca vào POS"** | Intent: `POS_ADD_ITEM` → "Đã thêm 3 Coca vào POS thành công" |
| 2 | **"Tạo đơn 2 Coca, 1 Sting"** | Intent: `CREATE_ORDER` → Recap: "Bạn có chắc? [Coca x2, Sting x1]" |
| 3 | **"Giá pepsi bao nhiêu?"** | 💡 READ INTENT xen ngang → trả giá Pepsi, NHƯNG `pendingAction` vẫn được bảo lưu |
| 4 | **"Đồng ý"** | Quay lại confirm → Đơn hàng tạo thành công, ID trả về |
| 5 | **"Kiểm tra thanh toán đơn #1"** | Intent: `PAYMENT_CHECK` → "Đã thanh toán" / "Chưa thanh toán" |

**🎤 Thuyết minh (nói ở bước 3):**

> *"Điểm đặc biệt ở bước 3: giữa lúc đang tạo đơn, nhân viên hỏi một câu tìm kiếm giá. Hệ thống nhận diện đây là Read Intent — trả lời ngay mà KHÔNG mất trạng thái tạo đơn. Khi nhân viên quay lại xác nhận, đơn hàng tiếp tục từ đúng nơi dừng lại. Đây là State Interruption — một tính năng quan trọng trong thực tế khi nhân viên phải xử lý nhiều tác vụ đồng thời."*

**✅ Checkpoint:** Multi-turn + State Interruption hoạt động → Employee flow hoàn chỉnh.

---

### ACT 5: Security & Rate Limiting

> **Mục đích:** Chứng minh hệ thống từ chối hành vi trái phép.

**📝 Kịch bản:**

#### Test A — Permission Check

| Bước | Hành động | Kết quả mong đợi |
|:---:|----------|-------------------|
| 1 | Đăng nhập **Customer** | |
| 2 | Gõ: **"Tạo đơn 2 Coca"** | Intent: `CREATE_ORDER` → ❌ Permission denied (employee-only) |

#### Test B — Rate Limiting

| Bước | Hành động | Kết quả mong đợi |
|:---:|----------|-------------------|
| 1 | Gõ liên tục 6 lệnh write trong 5 phút | Các lệnh: "Thêm coca", "Xóa coca", "Thêm pepsi"... |
| 2 | Lệnh thứ 6 | ❌ "Rate limit exceeded. Please try again after 5 minutes." |

#### Test C — Edge Cases

| Bước | Gõ vào chatbot | Kết quả mong đợi |
|:---:|----------------|-------------------|
| 1 | **"Thêm xyzabc vào giỏ"** | "Không tìm thấy sản phẩm" |
| 2 | **"Thêm 999 coca vào giỏ"** | "chỉ còn X sản phẩm trên kệ, không đủ" |
| 3 | **"Hôm nay thời tiết thế nào?"** | Intent: `FREE_CHAT` → LLM trả lời tự nhiên |

**✅ Checkpoint:** Permission + Rate Limit + Error handling → Security layer hoàn chỉnh.

---

## 📊 BƯỚC 3: TỔNG KẾT

**🎤 Thuyết minh tổng kết (30 giây):**

> *"Chatbot Action Assistant hỗ trợ 16 intent — 6 read-only và 10 write actions. Mọi hành động write đều đi qua ActionExecutor với 4 layer bảo vệ:*
> 1. *Rate Limiting — max 5 writes mỗi 5 phút*
> 2. *Permission Check — phân biệt Customer vs Employee*
> 3. *Ownership Check — customer chỉ thao tác trên dữ liệu của mình*
> 4. *Confirmation Gate — hành động nguy hiểm (hủy đơn, tạo đơn) bắt buộc xác nhận*
>
> *Toàn bộ write actions được ghi vào Audit Log trong database, đảm bảo traceability. Kiến trúc modular với 5 handler modules cho phép mở rộng tính năng mà không ảnh hưởng đến stability."*

---

## 📋 PHỤ LỤC: CÂU HỎI CÓ THỂ GẶP

| Câu hỏi | Gợi ý trả lời |
|---------|---------------|
| "Nếu Inventory API chết?" | Stock check fail → `logger.warn` + proceed with caution. Nhờ `try/catch`, cart vẫn hoạt động |
| "Nếu downstream API chậm?" | `withTimeout(5s)` bọc tất cả downstream calls. Timeout → graceful error message, không treo UI |
| "Race condition khi 2 user cùng thêm?" | Pre-check stock trước execute + Post-execute re-check. Nếu stock giảm → warning message |
| "Pronoun Resolution sai thì sao?" | Nếu có 2+ sản phẩm → Clarification State Machine hỏi lại. Nếu 0 sản phẩm → hỏi tên SP |
| "Giỏ hàng mất khi F5?" | Cart action dispatch về FE → FE tự xử lý persist (localStorage/API). Chatbot trả action, FE quyết định lưu đâu |
| "Rate Limit reset khi nào?" | Sliding window 5 phút, in-memory. Reset khi service restart |
