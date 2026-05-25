# 🎓 Kịch Bản Bảo Vệ Đồ Án: Hybrid RAG Recommendation

> **Thời lượng demo:** ~8-10 phút
> **Cấu trúc:** Setup → 4 ACTs → Kết luận Weight Learning

---

## ⚙️ BƯỚC 1: CHUẨN BỊ (5 PHÚT TRƯỚC KHI LÊN BỤC)

### 1.1 Dọn dẹp dữ liệu + Kiểm tra sẵn sàng

Mở terminal tại `backend/` và chạy cleanup script:

```bash
cd backend; node docs/script/pre-demo-cleanup.js
```

**Script sẽ tự động:**
- Xóa toàn bộ `recommendation_feedback` → Dashboard trống sạch
- Kiểm tra `co_purchase_stats` (Apriori) → phải có pairs
- Kiểm tra `item_similarity` (CF) → phải có similarities
- Kiểm tra `product_knowledge_base` (RAG) → phải có products
- In ra top 5 Apriori pairs và CF similarities để bạn biết trước kết quả

**Kết quả mong đợi:**
```
🎯 READINESS CHECKLIST
   ✅ Apriori data ready
   ✅ CF similarities ready
   ✅ User interactions seeded
   ✅ Knowledge base populated
   ✅ Feedback table cleared

   🎉 ALL SYSTEMS GO!
```

> Nếu có mục ❌, chạy seed scripts theo hướng dẫn trên terminal trước khi demo.

### 1.2 Đăng nhập tài khoản Demo

Đăng nhập Customer UI bằng tài khoản có **Customer ID 1–150**.

> Đây là nhóm "Nội trợ Nấu lẩu" — có lịch sử tương tác mạnh với Bò, Nấm, Rau, Gia vị từ `mock-interactions.js`. CF engine sẽ gợi ý sản phẩm liên quan đến nấu ăn cho nhóm này.

### 1.3 Bố trí màn hình

| Vị trí | Nội dung | Ghi chú |
|--------|----------|---------|
| **Trái** | Customer Chatbot UI | Cửa sổ chính demo |
| **Phải** | Admin Dashboard → AI Insights | Hiện Live Feedback Stream |

Đảm bảo Dashboard đang mở trang **AI Insights** hoặc tab có hiển thị **Live Feedback Stream** real-time.

---

## 🎬 BƯỚC 2: TRÌNH DIỄN 4 THUẬT TOÁN

### ACT 1: Semantic Search — Content-Based (α)

> **Mục đích:** Chứng minh RAG hiểu ngữ nghĩa, không chỉ khớp từ khóa.

**📝 Kịch bản:**

| Bước | Hành động | Trên màn hình |
|:---:|----------|---------------|
| 1 | Gõ vào chatbot: **"Tôi muốn mua đồ ăn vặt"** | Chatbot (trái) |
| 2 | Đợi 2-3 giây, chatbot trả contekết quả | Xuất hiện product cards: Snack Lays, Mì gói, Coca-Cola... |
| 3 | **Click** vào thẻ sản phẩm **Snack Lays** | Card highlight + feedback gửi đi |
| 4 | Nhìn sang Dashboard (phải) | Badge `[content]` nhảy lên Live Feed |

**🎤 Thuyết minh (nói khi đang thao tác bước 2-3):**

> *"Thưa hội đồng, khi người dùng nhập 'đồ ăn vặt', hệ thống thực hiện 2 luồng tìm kiếm song song:*
> - *Semantic Search: Mã hóa câu hỏi thành Vector Embedding 768 chiều bằng HuggingFace, sau đó tính Cosine Similarity với toàn bộ Knowledge Base trên pgvector.*
> - *Keyword Search: Full-text search bằng PostgreSQL tsvector để bắt chính xác từ khóa.*
> 
> *Hai kết quả được hợp nhất bằng thuật toán Reciprocal Rank Fusion (RRF), đảm bảo kết quả vừa đúng ngữ nghĩa vừa chính xác về từ khóa."*

**✅ Checkpoint:** Dashboard hiện badge màu xanh dương `[content]` → Thuật toán 1/4 đã chứng minh.

---

### ACT 2: Association Rules — Apriori Cross-sell (γ)

> **Mục đích:** Chứng minh hệ thống phát hiện quy luật "mua kèm" từ 500 đơn hàng lịch sử.

**📝 Kịch bản:**

| Bước | Hành động | Trên màn hình |
|:---:|----------|---------------|
| 1 | Gõ tiếp (cùng session): **"Tôi muốn mua bia Heineken"** | Chatbot (trái) |
| 2 | Đợi kết quả | Bia Heineken(17) + **Khô gà lá chanh(21)** hoặc **Snack Lays(20)** |
| 3 | Chỉ tay vào sản phẩm Khô gà/Snack | "Sản phẩm này không phải do tìm kiếm" |
| 4 | **Click** vào **Khô gà lá chanh** | Feedback gửi đi |
| 5 | Nhìn sang Dashboard (phải) | Badge `[apriori]` nhảy lên |

**🎤 Thuyết minh (nói khi chỉ vào Khô gà, bước 3):**

> *"Điểm đặc biệt ở đây: Khô gà lá chanh xuất hiện trong kết quả dù người dùng KHÔNG hỏi về đồ nhắm. Đây là thuật toán Apriori — khai phá luật kết hợp (Association Rules) từ 500 đơn hàng lịch sử.*
>
> *Hệ thống đã phát hiện: những khách hàng mua Bia Heineken có xu hướng mua kèm Khô gà và Snack với chỉ số Lift > 1. Đây chính là hiện tượng 'Bia và Bỉm' (Diapers and Beer) kinh điển trong Data Mining, được áp dụng thực tế vào hệ thống gợi ý."*

**✅ Checkpoint:** Dashboard hiện badge `[apriori]` → Thuật toán 2/4 đã chứng minh.

---

### ACT 3: Cá nhân hóa — Collaborative Filtering (β)

> **Mục đích:** Chứng minh AI nhận diện thói quen riêng của từng người dùng.

**📝 Kịch bản:**

| Bước | Hành động | Trên màn hình |
|:---:|----------|---------------|
| 1 | **Clear chat** (xóa tin nhắn cũ, bắt đầu hội thoại mới) | Chatbot trống |
| 2 | Gõ: **"Gợi ý cho tôi vài món"** | Chatbot (trái) |
| 3 | Đợi kết quả | Ngoài Content, sẽ có **Hành tây(25)** hoặc **Cà chua(24)** lọt top |
| 4 | Chỉ tay vào sản phẩm Hành tây/Cà chua | "Sản phẩm này được cá nhân hóa" |
| 5 | **Click** vào **Hành tây** | Feedback gửi đi |
| 6 | Nhìn sang Dashboard (phải) | Badge `[cf]` nhảy lên |

**🎤 Thuyết minh (nói khi chỉ vào Hành tây, bước 4):**

> *"Câu hỏi 'Gợi ý cho tôi vài món' hoàn toàn không chứa từ khóa cụ thể. Vậy tại sao Hành tây lại xuất hiện trên Top?*
>
> *Đó là nhờ thuật toán Collaborative Filtering — Item-Item. Hệ thống phân tích dữ liệu tương tác của 500 người dùng, phát hiện 150 user thuộc nhóm 'Nội trợ' thường mua kèm Bò, Nấm, Rau. Tài khoản demo của em cũng thuộc nhóm này, nên CF engine tính toán Adjusted Cosine Similarity và dự đoán em sẽ thích Hành tây — một sản phẩm mà nhiều user tương tự đã mua.*
>
> *Lưu ý: Sản phẩm Hành tây ban đầu chỉ tồn tại trong kết quả CF, không có metadata hiển thị. Hệ thống giải quyết vấn đề này bằng Two-Tier Hydration — tra cứu Local Knowledge Base trước, nếu thiếu thì gọi Catalog API với timeout 500ms để bảo vệ domino."*

**✅ Checkpoint:** Dashboard hiện badge `[cf]` → Thuật toán 3/4 đã chứng minh.

---

### ACT 4: Trí nhớ ngắn hạn — Session Context (δ) — CÚ CHỐT 🎯

> **Mục đích:** Chứng minh AI duy trì ngữ cảnh xuyên suốt phiên chat (Multi-turn Context).

**📝 Kịch bản 3 lượt:**

#### Lượt 1 — Thiết lập ngữ cảnh

| Bước | Hành động | Trên màn hình |
|:---:|----------|---------------|
| 1 | **Clear chat** | Chatbot trống |
| 2 | Gõ: **"Tôi muốn nấu lẩu Thái cuối tuần"** | Chatbot (trái) |
| 3 | Đợi kết quả | Gia vị lẩu Thái(4), Ba chỉ bò(1), Nấm kim châm(2)... |

> *Không click, không giải thích — chỉ nói: "Em bắt đầu bằng một câu hỏi về nấu lẩu."*

#### Lượt 2 — Xây dựng context

| Bước | Hành động | Trên màn hình |
|:---:|----------|---------------|
| 4 | Gõ tiếp (cùng session): **"Gợi ý rau ăn kèm lẩu đi"** | Chatbot (trái) |
| 5 | Đợi kết quả | Rau muống(3), Cải thìa(22)... |

> *Nói ngắn gọn: "Em tiếp tục hỏi về rau ăn kèm. Lúc này Session Engine đã ngầm nhận diện ý định nấu lẩu."*

#### Lượt 3 — Cú chốt (không dùng từ khóa)

| Bước | Hành động | Trên màn hình |
|:---:|----------|---------------|
| 6 | Gõ: **"Gợi ý thêm đi"** | Chatbot (trái) |
| 7 | Đợi kết quả | **Bún tươi(5)**, **Hành tây(25)**, **Chanh(28)**... |
| 8 | **Click** vào **Bún tươi** | Feedback gửi đi |
| 9 | Nhìn sang Dashboard (phải) | Badge **`[session]`** nhảy lên 🎉 |

**🎤 Thuyết minh (nói sau bước 7, khi kết quả hiện ra):**

> *"Thưa thầy cô, ở câu cuối cùng, em hoàn toàn KHÔNG dùng bất kỳ từ khóa nào liên quan đến lẩu — không có 'bò', 'nấm', hay 'gia vị'. Câu hỏi cực ngắn chỉ là 'Gợi ý thêm đi'.*
>
> *Nhưng AI vẫn trả về Bún tươi, Hành tây, Chanh — toàn bộ đều là nguyên liệu ăn kèm lẩu. Đó là nhờ thuật toán Session Context Detection:*
> 1. *Hệ thống trích xuất chuỗi sản phẩm đã gợi ý ở các câu trước.*
> 2. *Deterministic Reformulator phát hiện câu continuation 'Gợi ý thêm đi', tự động tái sử dụng chủ đề chính là 'nấu lẩu' từ lịch sử để thực hiện Keyword Search ổn định.*
> 3. *Áp dụng Session Boost +0.15 cho các sản phẩm trong Cluster Lẩu Bò.*
> 4. *Kết quả: Bún tươi được đẩy lên Top phục vụ hoàn hảo chủ đề bữa ăn.*

**🎤 Bảo vệ thiết kế (nói sau khi Dashboard hiện badge `[session]`):**

> *"Một điểm đặc biệt em muốn chia sẻ: ban đầu Session Context sử dụng hardcode Product IDs, gắn chết vào dữ liệu mẫu. Em đã refactor sang kiến trúc Category-Driven — map cluster theo danh mục sản phẩm thay vì ID cứng. Nhờ đó, khi admin thêm sản phẩm mới vào bất kỳ danh mục nào, hệ thống tự động nhận diện mà không cần sửa code.*
>
> *Về hiệu năng: quá trình map Category chỉ chạy 1 lần lúc khởi động server (warmUp), toàn bộ dữ liệu lưu In-memory, nên thời gian xử lý runtime là O(1) — hoàn toàn không ảnh hưởng trải nghiệm người dùng."*

**✅ Checkpoint:** Dashboard hiện badge `[session]` → Thuật toán 4/4 đã chứng minh hoàn tất.

---

## 📊 BƯỚC 3: KẾT LUẬN — VÒNG LẶP HỌC HỎI TỰ ĐỘNG

**🎤 Thuyết minh tổng kết (30 giây):**

> *"Tất cả 4 tương tác vừa rồi — click Snack, Khô gà, Hành tây và Bún tươi — đều đã được ghi nhận vào bảng `recommendation_feedback` với nguồn gốc thuật toán rõ ràng: `content`, `apriori`, `cf`, `session`.*
>
> *Hàng đêm, một Batch Job tên Weight Learner sẽ tự động chạy:*
> - *Tính Conversion Rate (tỉ lệ click → mua) của từng thuật toán*
> - *Sử dụng EWMA (Exponential Weighted Moving Average) để điều chỉnh trọng số α, β, γ, δ*
> - *Lưu lịch sử vào `ensemble_weights_history` để theo dõi xu hướng theo thời gian*
>
> *Đây là một vòng lặp khép kín: Thu thập dữ liệu → Gợi ý → Tương tác → Tự học → Gợi ý tốt hơn. Hệ thống hoàn toàn có khả năng tự hoàn thiện mà không cần con người can thiệp."*

---

## 📋 PHỤ LỤC: CÂU HỎI GVHD CÓ THỂ HỎI

| Câu hỏi | Gợi ý trả lời |
|---------|---------------|
| "Nếu user mới, chưa có lịch sử?" | CF trả về rỗng, hệ thống fallback sang Content + Apriori (cold-start graceful degradation) |
| "Session Context có nhớ qua phiên khác không?" | Không — đây là Short-term Memory trong cùng 1 phiên chat. Long-term memory do CF đảm nhận qua bảng `user_product_interaction` |
| "Sao Apriori không gợi ý sai danh mục?" | Chỉ gợi ý khi Lift > 1 (tần suất mua kèm cao hơn ngẫu nhiên) và sản phẩm phải còn hàng (`is_in_stock = true`) |
| "Latency có tăng khi thêm nhiều thuật toán?" | Tổng pipeline ~200-400ms. Hydration local KB ~1ms, Catalog API fallback timeout 500ms. WarmUp in-memory nên runtime O(1) |
| "Category-Driven có hạn chế gì?" | Category names phải khớp chính xác với data-ingestion sync. Nếu đổi tên category ở Catalog, cần restart chatbot để warmUp lại |
