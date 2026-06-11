# Kịch Bản Demo Bảo Vệ Đồ Án — Hybrid RAG Recommendation

> **Thời lượng:** 8–10 phút · **Cấu trúc:** Chuẩn bị → 4 ACTs → Kết luận

---

## Chuẩn Bị (5 phút trước demo)

### Bước 1 — Khởi tạo dữ liệu

```bash
cd backend && node docs/script/pre-demo-cleanup.js
```

Script tự động: xóa bảng `recommendation_feedback`, kiểm tra dữ liệu Apriori/CF/RAG, in top pairs để nắm trước kết quả. Kết quả mong đợi: `ALL SYSTEMS GO`.

### Bước 2 — Đăng nhập & Bố trí

- Đăng nhập Customer UI bằng tài khoản **Customer ID 51** (nhóm "Nội trợ Nấu lẩu").
- **Màn hình trái:** Customer Chatbot UI.
- **Màn hình phải:** Admin Dashboard → AI Insights (Live Feedback Stream).

**Bản đồ Persona (từ `mock-interactions.js`):**

| Nhóm | User ID | Sản phẩm đặc trưng | Tần suất |
|---|---|---|---|
| 🍲 **Nội trợ Nấu lẩu** | **1–150** *(demo: #51)* | Ba chỉ bò, Nấm, Rau muống, Bún tươi, Gia vị | 5–10x/tháng |
| 🍜 Sinh viên Ăn vặt | 151–300 | Mì Hảo Hảo, Xúc xích, Coca, Snack, Sữa | 10–20x/tháng |
| 🍺 Dân nhậu Cuối tuần | 301–450 | Bia Heineken, Tiger, Khô gà, Đậu phộng | 2–4x/tháng |
| 🎲 Khách vãng lai | 451–500 | Random (noise) | — |

---

## Trình Diễn 4 Thuật Toán

> **Nguyên lý điều hướng (Contextual Router):** Hệ thống không chạy cào bằng, mà tự động kích hoạt thuật toán tối ưu dựa trên ý định người dùng và điểm chạm hiển thị:

| Thuật toán | Khi nào kích hoạt | Điểm chạm lý tưởng |
|---|---|---|
| **Content-Based RAG (α)** | Khách tìm kiếm chủ động, hỏi rộng | Tìm kiếm, Chat tư vấn khởi đầu |
| **Apriori (γ)** | Đã xác định sản phẩm mỏ neo cụ thể | PDP, Giỏ hàng, Checkout |
| **Collaborative Filtering (β)** | Khách lướt xem chung, không đích danh | Trang chủ "Dành cho bạn", Chat welcome |
| **Session Context (δ)** | Chat nhiều lượt, ý định biến đổi liên tục | Chat trực tuyến, "Vừa xem" |

---

### ACT 1 · Content-Based RAG (α) & Intent Gating

> **Mục đích:** Chứng minh RAG hiểu ngữ nghĩa (không chỉ khớp từ khóa). Truy vấn rộng "đồ ăn vặt" trả về đúng sản phẩm thuộc danh mục snack/hạt mà không cần gõ tên cụ thể.
>
> **Điểm mạnh:** Giải quyết vấn đề của Keyword Search truyền thống (từ đồng nghĩa, từ lóng). Pipeline song song Semantic + Keyword, hợp nhất bằng RRF, kết hợp tín hiệu Apriori cross-sell tự nhiên.

**Thao tác:**

| # | Hành động | Màn hình |
|:-:|---|---|
| 1 | Gõ: **"Tôi muốn mua đồ ăn vặt"** | Chatbot |
| 2 | Đợi 2–3s → xuất hiện 5 product cards | Chatbot |
| 3 | Click vào **Khô gà lá chanh** hoặc **Snack Lay's** | Card highlight, feedback gửi đi |
| 4 | Nhìn sang Dashboard | Badge `[content]` nhảy lên Live Feed |

**Kết quả thực tế (đã kiểm chứng):**

| # | Sản phẩm | Giá | Source |
|:-:|---|:-:|:-:|
| 1 | Khô gà lá chanh G kitchen hũ 200g | 85.000đ | `content` |
| 2 | Snack khoai tây Lay's vị Tự nhiên 52g | 12.000đ | `content` |
| 3 | Đậu phộng da cá Tân Tân hũ 275g | 42.000đ | `content` |
| 4 | Hạt điều rang muối Bình Phước hũ 250g | 95.000đ | `content` |
| 5 | Bánh mì hoa cúc Harrys Brioche Tressée 500g | 145.000đ | `apriori` |

**Chatbot Reply (mẫu):**

> *"Đây là một số lựa chọn đồ ăn vặt ngon và phổ biến:*
> - *Khô gà lá chanh G kitchen hũ 200g — 85.000đ*
> - *Snack khoai tây Lay's vị Tự nhiên 52g — 12.000đ*
> - *Đậu phộng da cá Tân Tân hũ 275g — 42.000đ*
> - *Hạt điều rang muối Bình Phước hũ 250g — 95.000đ*
>
> *Nhiều khách hàng mua khô gà lá chanh cũng thường mua kèm snack khoai tây Lay's.*
>
> *Bạn có muốn thử các loại hạt rang muối hay bánh mì hoa cúc Harrys không?"*

**Live Feedback (Dashboard):**

| Badge | Sản phẩm | AI Score |
|:-:|---|:-:|
| `content` | Snack khoai tây Lay's vị Tự nhiên 52g | 0.6853 |
| `content` | Khô gà lá chanh G kitchen hũ 200g | 0.7204 |
| `content` | Đậu phộng da cá Tân Tân hũ 275g | 0.5959 |
| `content` | Hạt điều rang muối Bình Phước hũ 250g | 0.5798 |
| `apriori` | Bánh mì hoa cúc Harrys Brioche Tressée 500g | 0.3994 |

**Thuyết minh:**

> *"Khi người dùng nhập 'đồ ăn vặt', hệ thống chạy song song 2 luồng: (1) Semantic Search — mã hóa câu hỏi thành Vector 768 chiều bằng mô hình multilingual-e5-base, tính Cosine Similarity trên pgvector; (2) Keyword Search — full-text search bằng PostgreSQL tsvector tiếng Việt. Hai kết quả được hợp nhất bằng Reciprocal Rank Fusion (RRF), đảm bảo vừa đúng ngữ nghĩa vừa chính xác từ khóa.*
>
> *4 sản phẩm đầu tiên là kết quả thuần Content-Based — 'khô gà', 'snack', 'đậu phộng', 'hạt điều' đều thuộc danh mục đồ ăn vặt dù người dùng không gõ tên cụ thể. Sản phẩm thứ 5 — Bánh mì hoa cúc — có badge `apriori`, nghĩa là hệ thống phát hiện khách hàng mua khô gà thường mua kèm bánh mì hoa cúc. Đây là tín hiệu cross-sell tự nhiên, xuất hiện ngay cả ở truy vấn rộng."*

**✅ Checkpoint:** 4 badge `[content]` + 1 badge `[apriori]` → Thuật toán 1/4.

---

### ACT 2 · Apriori Cross-sell (γ)

> **Mục đích:** Chứng minh hệ thống phát hiện quy luật "mua kèm" từ 500 đơn hàng lịch sử.
>
> **Điểm mạnh:** Khai phá luật kết hợp xuyên danh mục (Cross-Category Discovery) — phát hiện mối quan hệ ẩn giữa các mặt hàng dường như không liên quan (Bia → Khô gà, Coca). Hiện tượng "Bia và Bỉm" kinh điển, tối ưu AOV (Average Order Value).

⚠️ **Bấm "Phiên chat mới" (🔄) trước khi bắt đầu.**

**Thao tác:**

| # | Hành động | Màn hình |
|:-:|---|---|
| 0 | Bấm 🔄 Phiên chat mới | Session reset |
| 1 | Gõ: **"Tôi muốn mua bia Heineken"** | Chatbot |
| 2 | Đợi kết quả → Bia Heineken + sản phẩm có badge `[apriori]` | Chatbot |
| 3 | Chỉ vào sản phẩm Apriori (Coca-Cola, Khô gà): *"Sản phẩm này không phải do tìm kiếm"* | — |
| 4 | Click sản phẩm Apriori → nhìn Dashboard | Badge `[apriori]` nhảy lên |

**Dữ liệu Apriori thực tế (Heineken):**

| Sản phẩm | Co-purchase | Confidence | Lift |
|---|:-:|:-:|:-:|
| Nước ngọt Coca-Cola chai 390ml (#19) | 165 | 0.801 | 1.90 |
| Khô gà lá chanh G kitchen hũ 200g (#21) | 146 | 0.709 | 1.74 |
| Snack khoai tây Lay's vị Tự nhiên 52g (#20) | 140 | 0.680 | 1.66 |

**Kết quả thực tế (đã kiểm chứng):**

| # | Sản phẩm | Giá | Source | AI Score |
|:-:|---|:-:|:-:|:-:|
| 1 | Bia Heineken Silver lon 330ml | 19.500đ | `content` | 0.7426 |
| 2 | Nước ngọt Coca-Cola vị nguyên bản chai 390ml | 9.000đ | `apriori` | 0.1727 |
| 3 | Khô gà lá chanh G kitchen hũ 200g | 85.000đ | `apriori` | 0.1554 |
| 4 | Thùng 24 lon bia Tiger Bạc (Tiger Crystal) 330ml | 395.000đ | `content` | 0.5502 |

**Chatbot Reply (mẫu):**

> *"Bia Heineken Silver lon 330ml đang có giá 19.500đ, còn 300 sản phẩm. Nhiều khách hàng mua bia Heineken Silver lon 330ml cũng thường mua kèm nước ngọt Coca-Cola vị nguyên bản chai 390ml. Bạn có muốn thêm vào giỏ hàng không?"*

> **Lưu ý:** LLM chỉ nhắc đến 2-3 sản phẩm trong văn bản (Heineken + Coca + Tiger), trong khi hiển thị đầy đủ 5 product cards. Đây là **thiết kế có chủ đích**: LLM prompt nhận `productContext` từ top content results, trong khi Product Cards hiển thị toàn bộ Ensemble results (content + apriori + cf). Điều này giúp văn bản trả lời tự nhiên, không liệt kê dài dòng.

**Thuyết minh:**

> *"Sản phẩm Coca-Cola và Khô gà xuất hiện dù người dùng KHÔNG hỏi về chúng. Đây là thuật toán Apriori — khai phá luật kết hợp từ 500 đơn hàng. Hệ thống phát hiện khách mua Bia Heineken thường mua kèm Coca-Cola (Lift=1.90, 165 đơn mua kèm) và Khô gà (Lift=1.74, 146 đơn mua kèm). Đây chính là hiện tượng 'Bia và Bỉm' kinh điển trong Data Mining."*
>
> *"Đặc biệt, hệ thống ưu tiên sản phẩm bán chéo từ sản phẩm 'mỏ neo' (Heineken) thay vì từ sản phẩm phụ (Tiger). Tín hiệu Apriori được nhân với độ liên quan nội dung (Content Relevance Weight), đảm bảo sản phẩm cross-sell đúng mục tiêu."*

**✅ Checkpoint:** Badge `[apriori]` + Coca-Cola/Khô gà → Thuật toán 2/4.

---

### ACT 3 · Collaborative Filtering (β)

> **Mục đích:** Chứng minh cá nhân hóa mù (Blind Personalization) — AI nhận diện thói quen riêng khi người dùng hỏi chung chung, không có từ khóa mỏ neo.
>
> **Điểm mạnh:** Ma trận tương đồng Item-Item phân loại user theo hành vi cộng đồng. Cùng một câu hỏi, nhưng kết quả khác nhau hoàn toàn giữa các nhóm người dùng (Nội trợ → Nước mắm, Rau muống, Gia vị lẩu; Sinh viên → Mì tôm, Xúc xích, Coca).
>
> **Tài khoản demo:** User #51 thuộc nhóm **Nội trợ Nấu lẩu** (ID 1–150). CF phân tích 500 user interactions, phát hiện User #51 có hành vi tương đồng với nhóm mua bò, nấm, rau, gia vị → gợi ý sản phẩm từ cùng cluster.

**Thao tác:**

| # | Hành động | Màn hình |
|:-:|---|---|
| 1 | Bấm 🔄 Phiên chat mới | Chat trống |
| 2 | Gõ: **"Gợi ý cho tôi vài món"** | Chatbot |
| 3 | Đợi kết quả → xuất hiện sản phẩm có badge `[cf]` chiếm đa số (3–4/5 slot) | Chatbot |
| 4 | Chỉ vào sản phẩm CF: *"Sản phẩm này được cá nhân hóa theo thói quen mua sắm"* | — |
| 5 | Click sản phẩm CF → nhìn Dashboard | Badge `[cf]` nhảy lên |

**Kết quả thực tế (đã kiểm chứng — User #51, nhóm Nội trợ):**

| # | Sản phẩm | Source | AI Score |
|:-:|---|:-:|:-:|
| 1 | Nước mắm Nam Ngư 11 độ đạm chai 750ml | `cf` | 0.7586 |
| 2 | Rau muống VietGAP bó 500g | `apriori` | 0.1768 |
| 3 | Cherry đỏ Mỹ size 9.5 (Hộp 500g - Hàng VIP) | `cf` | 0.3410 |
| 4 | Gia vị nêm sẵn lẩu Thái Barona 80g | `cf` | 0.3418 |
| 5 | Cá viên chiên xâu tôm viên Vissan 500g | `cf` | 0.3453 |

> **Nhận xét:** 4/5 sản phẩm mang badge `[cf]` — toàn bộ liên quan đến nấu ăn gia đình (nước mắm, gia vị lẩu, cá viên). Slot 2 có badge `[apriori]` vì Rau muống thường được mua kèm với gia vị lẩu. Kết quả này sẽ **hoàn toàn khác** nếu đăng nhập bằng User 200 (Sinh viên) — lúc đó CF sẽ gợi ý Mì gói, Snack, Coca.

**Thuyết minh:**

> *"Câu hỏi 'Gợi ý cho tôi vài món' hoàn toàn không chứa từ khóa cụ thể. Vậy tại sao Nước mắm Nam Ngư, Gia vị lẩu Thái, Cá viên chiên xuất hiện?*
>
> *Đó là nhờ Collaborative Filtering — hệ thống phân tích dữ liệu tương tác của 500 người dùng, phát hiện tài khoản #51 thuộc nhóm 'Nội trợ Nấu lẩu' (User 1–150), nên gợi ý sản phẩm mà 150 user tương tự thường xuyên mua. Nếu em đổi sang tài khoản sinh viên (User 151–300), kết quả sẽ hoàn toàn khác — Mì Hảo Hảo, Xúc xích, Coca-Cola.*
>
> *Slot Partitioning ưu tiên CF chiếm 3–4 slot đầu cho welcome query, đảm bảo cá nhân hóa nổi bật. Sản phẩm CF ban đầu không có metadata hiển thị — hệ thống giải quyết bằng Two-Tier Hydration: tra cứu Local KB trước, fallback Catalog API với timeout 500ms."*

**✅ Checkpoint:** 4 badge `[cf]` + 1 badge `[apriori]` → Thuật toán 3/4.

---

### ACT 4 · Session Context (δ) — Cú Chốt 🎯

> **Mục đích:** Chứng minh AI duy trì ngữ cảnh xuyên suốt phiên chat (Multi-turn Context) — giải bài toán Đại từ thế vị.
>
> **Điểm mạnh:** Khi khách hỏi "Gợi ý thêm đi" (không chứa bất kỳ từ khóa chính nào), kiến trúc Category-Driven Session mapping (warmUp in-memory O(1)) tự động nhận diện chủ đề từ lịch sử, khóa chặt danh mục liên đới mà không cần truy xuất lại DB.

**Thao tác (3 lượt cùng session):**

| # | Hành động | Màn hình |
|:-:|---|---|
| 1 | Bấm 🔄 Phiên chat mới | Chat trống |
| 2 | **Lượt 1:** Gõ: **"Tôi muốn nấu lẩu Thái cuối tuần"** | Gia vị lẩu, Ba chỉ bò, Nấm... có badge `[content]` |
| 3 | **Lượt 2:** Gõ: **"Gợi ý rau ăn kèm lẩu đi"** | Cà chua mận đỏ Đà Lạt, Rau muống VietGAP... có badge `[content]` |
| 4 | **Lượt 3:** Gõ: **"Gợi ý thêm đi"** | Bún tươi Ba Khánh, Ba chỉ bò Mỹ... có badge `[session]` (đã loại trừ Cà chua, Rau muống) |
| 5 | Click **Bún tươi** hoặc **Ba chỉ bò** → nhìn Dashboard | Badge `[session]` nhảy lên 🎉 |

**Thuyết minh (sau khi kết quả Lượt 3 hiện ra):**

> *"Ở câu cuối cùng, em hoàn toàn KHÔNG dùng từ khóa liên quan đến lẩu hay rau — chỉ gõ 'Gợi ý thêm đi'. Nhưng AI vẫn trả về Bún tươi, Ba chỉ bò Mỹ — toàn bộ đều là nguyên liệu lẩu.*
>
> *Đó là nhờ Session Context kết hợp Novelty Filter:*
> 1. *Trích xuất chuỗi sản phẩm đã hiển thị ở lượt trước (Cà chua, Rau muống).*
> 2. *Deterministic Reformulator phát hiện câu continuation, tái sử dụng chủ đề 'nấu lẩu' từ lịch sử.*
> 3. *Novelty Filter loại trừ hoàn toàn các sản phẩm đã hiện ở Lượt 2.*
> 4. *Áp dụng Session Boost +0.15 cho các sản phẩm khác trong cụm Lẩu Bò.*
> 5. *Cơ chế Attribution gán nhãn `[session]` thiết thực cho Bún tươi và Ba chỉ bò để bộ học Weight Learner ghi nhận chính xác.*
>
> *Điểm thiết kế quan trọng: Session Context sử dụng Category-Driven mapping thay vì hardcode Product ID — khi admin thêm sản phẩm mới vào danh mục rau/bún/thịt, hệ thống tự động nhận diện mà không cần sửa code. Toàn bộ dữ liệu warmUp in-memory, runtime cực nhanh với O(1)."*

**✅ Checkpoint:** Badge `[session]` hiển thị nổi bật ở Lượt 3 → Thuật toán 4/4 hoàn tất.

---

## Kết Luận — Vòng Lặp Học Hỏi Tự Động (30 giây)

> *"Tất cả 4 tương tác vừa rồi đều được ghi nhận vào bảng `recommendation_feedback` với nguồn gốc thuật toán rõ ràng: `content`, `apriori`, `cf`, `session`.*
>
> *Hàng đêm, Weight Learner tự động:*
> - *Tính Conversion Rate (click → mua) của từng thuật toán*
> - *Điều chỉnh trọng số α, β, γ, δ bằng EWMA (Exponential Weighted Moving Average)*
> - *Lưu lịch sử vào `ensemble_weights_history`*
>
> *Đây là vòng lặp khép kín: Gợi ý → Tương tác → Tự học → Gợi ý tốt hơn. Hệ thống hoàn toàn tự hoàn thiện mà không cần con người can thiệp."*

---

## Phụ Lục — Câu Hỏi Phản Biện

| Câu hỏi | Trả lời |
|---|---|
| User mới, chưa có lịch sử? | CF trả về rỗng → fallback Content + Apriori (cold-start graceful degradation) |
| Session Context nhớ qua phiên khác? | Không — Short-term Memory trong cùng 1 phiên. Long-term do CF qua `user_product_interaction` |
| Apriori có gợi ý sai danh mục? | Chỉ gợi ý khi Lift > 1 (mua kèm cao hơn ngẫu nhiên) và sản phẩm còn hàng |
| Latency có tăng khi thêm thuật toán? | Pipeline ~200–400ms. Local KB ~1ms, Catalog fallback timeout 500ms. WarmUp in-memory, O(1) |
| Category-Driven có hạn chế? | Category names phải khớp với data-ingestion. Đổi tên category → cần restart chatbot để warmUp |
