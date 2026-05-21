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
| Customer (userId=1) | `customer` | Mua sắm, giỏ hàng, theo dõi đơn | ACT 1, 2, 3 |
| Employee (userId=100) | `employee` | POS, tạo đơn, kiểm tra thanh toán | ACT 4 |

### 1.3 Bố trí màn hình

| Vị trí | Nội dung |
|--------|----------|
| **Trái** | Customer/Employee Chatbot UI |
| **Phải** | Terminal logs (xem intent + audit log) |

---

## 🎬 BƯỚC 2: TRÌNH DIỄN 5 LUỒNG CHÍNH

### ACT 1: Tìm kiếm & Giỏ hàng — Customer Full Flow

> **Mục đích:** Chứng minh luồng hoàn chỉnh từ tìm kiếm → thêm giỏ → cập nhật → thanh toán.

**📝 Kịch bản:**

| Bước | Gõ vào chatbot | Kết quả mong đợi |
|:---:|----------------|-------------------|
| 1 | **"Giá coca bao nhiêu?"** | Intent: `CHECK_PRICE` → Hiện giá + product cards |
| 2 | **"Còn bao nhiêu trên kệ?"** | Intent: `CHECK_STOCK` → Số lượng tồn kho |
| 3 | **"Thêm 2 cái đó vào giỏ"** | Intent: `ADD_TO_CART` → Pronoun resolution → "Đã thêm 2 Coca vào giỏ hàng" |
| 4 | **"Đổi số lượng thành 5"** | Intent: `UPDATE_CART_ITEM` → "Đã cập nhật số lượng thành 5" |
| 5 | **"Xem giỏ hàng"** | Intent: `VIEW_CART` → Action `VIEW_CART` trả về FE |
| 6 | **"Thanh toán"** | Intent: `CHECKOUT_GUIDE` → Action `NAVIGATE → /checkout` |

**🎤 Thuyết minh (nói ở bước 3):**

> *"Ở bước 3, người dùng nói 'cái đó' — hệ thống không biết 'cái đó' là gì. Nhưng nhờ Pronoun Resolution, chatbot nhớ sản phẩm vừa hỏi ở bước 1-2 (Coca) thông qua `lastMentionedProducts` lưu trong session metadata, tự động resolve 'cái đó' = Coca mà không cần hỏi lại."*

**✅ Checkpoint:** 6 bước xuyên suốt không lỗi, Pronoun Resolution hoạt động → Full cart flow chứng minh.

---

### ACT 2: Pronoun Ambiguity — Clarification State Machine

> **Mục đích:** Chứng minh hệ thống xử lý mơ hồ khi có nhiều sản phẩm.

**📝 Kịch bản:**

| Bước | Gõ vào chatbot | Kết quả mong đợi |
|:---:|----------------|-------------------|
| 1 | **"Giá pepsi và coca"** | Trả về 2+ product cards |
| 2 | **"Thêm cái đó vào giỏ"** | ⚠️ Chatbot HỎI LẠI: "Bạn muốn thêm sản phẩm nào? [1] Coca, [2] Pepsi" |
| 3 | **"1"** | Chatbot chọn Coca → "Đã thêm Coca vào giỏ hàng thành công" |

**🎤 Thuyết minh (nói ở bước 2):**

> *"Khi có 2 sản phẩm trong `lastMentionedProducts`, hệ thống KHÔNG tự ý chọn sản phẩm đầu tiên. Thay vào đó, kích hoạt Clarification State Machine — lưu trạng thái CLARIFYING vào session metadata, hiển thị danh sách cho user chọn. Đây là giải pháp cho Gotcha B trong thiết kế."*

**✅ Checkpoint:** Chatbot hỏi lại thay vì đoán → Clarification hoạt động.

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
