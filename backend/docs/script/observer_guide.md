# 📋 Demo Hybrid RAG Recommendation

> **Trọng số mặc định:** `α (Content) = 0.40`, `β (CF) = 0.25`, `γ (Apriori) = 0.25`, `δ (Personal) = 0.10`

---

## ACT 1 · Content-Based RAG (α) — Sức Mạnh Ngữ Nghĩa

> **Mục đích:** Chứng minh RAG hiểu ngữ nghĩa (không chỉ khớp từ khóa). Pipeline song song Semantic + Keyword, hợp nhất bằng RRF.

| Bước | Hành động trên màn hình | Kỳ vọng quan sát |
|:-:|---|---|
| 1 | Gõ: **"Tôi muốn mua đồ ăn vặt"** | Chatbot hiển thị 3 product cards |
| 2 | Quan sát cards | Bánh xốp Nabati, Bánh quy Danisa, Kẹo Chupa Chups |
| 3 | Click **Bánh xốp Nabati** | Card highlight |
| 4 | **Nhìn Dashboard** | Badge `[content]` nhảy lên, AI Score ~0.6144 |

**Bảng kết quả kỳ vọng:**

| # | Sản phẩm | Source | AI Score |
|:-:|---|:-:|:-:|
| 1 | Bánh xốp phô mai Nabati hộp 150g | `content` | ~0.6144 |
| 2 | Bánh quy bơ Danisa hộp thiếc 454g | `content` | ~0.5983 |
| 3 | Kẹo mút Chupa Chups hương trái cây gói 10 que | `content` | ~0.5763 |

#### 🧮 Cơ chế tính điểm chi tiết

Không có thông tin CF/Personal → điểm CF/Personal bằng 0. Trọng số β được dồn sang Content (α thực tế = 0.65).

| Sản phẩm | content | apriori | penalty | final_score → AI Score |
|---|:-:|:-:|:-:|---|
| Bánh xốp Nabati | 0.8533 | 0.0000 | ×1.00 | 0.40 × 0.8533 = **0.3413** → ~**0.6144** |
| Bánh quy Danisa | 0.8310 | 0.0000 | ×1.00 | 0.40 × 0.8310 = **0.3324** → ~**0.5983** |
| Kẹo mút Chupa Chups | 0.8004 | 0.0000 | ×1.00 | 0.40 × 0.8004 = **0.3202** → ~**0.5763** |

> 💡 **Ánh xạ động:** $\text{AI Score} = \alpha_{\text{thực tế}} \times \text{content} + \delta \times personal = 0.65 \times 0.8991 + 0.03 = \mathbf{0.6144}$

> **✅ Checkpoint:** 3 badge `[content]` trên Dashboard → Xác nhận thuật toán **1/4**.

---

## ACT 2 · Apriori Cross-sell (γ) — Khai Phá Quy Luật

> **Mục đích:** Chứng minh hệ thống phát hiện quy luật "mua kèm" từ 500 đơn hàng lịch sử. Hiện tượng "Bia và Bỉm" kinh điển.

| Bước | Hành động trên màn hình | Kỳ vọng quan sát |
|:-:|---|---|
| 1 | Gõ: **"Tôi muốn mua bia Heineken"** | Chatbot trả kết quả |
| 2 | Quan sát cards | Bia Heineken (`content`) + Coca-Cola, Khô gà (`apriori`) |
| 3 | Click **Khô gà lá chanh** | Card highlight |
| 4 | **Nhìn Dashboard** | Badge `[apriori]` nhảy lên, AI Score ~0.1554 |

**Bảng kết quả kỳ vọng:**

| # | Sản phẩm | Source | AI Score |
|:-:|---|:-:|:-:|
| 1 | Bia Heineken Silver lon 330ml | `content` | ~0.7426 |
| 2 | Nước ngọt Coca-Cola chai 390ml | `apriori` | ~0.1727 |
| 3 | Khô gà lá chanh G kitchen hũ 200g | `apriori` | ~0.1554 |
| 4 | Thùng 24 lon bia Tiger Bạc 330ml | `content` | ~0.5502 |

**Dữ liệu Apriori (từ 500 đơn hàng):**

| Sản phẩm mua kèm | Co-purchase | Confidence | Lift |
|---|:-:|:-:|:-:|
| Coca-Cola | 165 | 0.801 | 1.90 |
| Khô gà | 146 | 0.709 | 1.74 |
| Snack Lay's | 140 | 0.680 | 1.66 |

#### 🧮 Cơ chế tính điểm chi tiết

Sản phẩm Apriori-only (không trùng khớp ngữ nghĩa) bị hình phạt `penalty = 0.75`:

| Sản phẩm | content | apriori effective | penalty | final_score → AI Score |
|---|:-:|:-:|:-:|---|
| Heineken (**anchor**) | 1.0000 | 0.0000 | ×1.00 | 0.40 × 1.00 = **0.4000** → ~**0.7426** |
| Coca (apriori-only) | 0.0000 | 0.8010 | ×0.75 | 0.25 × 0.8010 × 0.75 = **0.1502** → ~**0.1727** |
| Khô gà (apriori-only) | 0.0000 | 0.7090 | ×0.75 | 0.25 × 0.7090 × 0.75 = **0.1329** → ~**0.1554** |
| Bia Tiger Bạc (secondary) | 0.7500 | 0.0000 | ×1.00 | 0.40 × 0.75 = **0.3000** → ~**0.5502** |

> 💡 **Apriori-only:** $\text{AI Score} = (\gamma \times \text{apriori} + \text{Personal}) \times \text{penalty} = (0.25 \times 0.8010 + 0.03) \times 0.75 \approx \mathbf{0.1727}$

> **✅ Checkpoint:** Badge `[apriori]` + sản phẩm mua kèm xuất hiện → Xác nhận thuật toán **2/4**.

---

## ACT 3 · Collaborative Filtering (β) — Cá Nhân Hóa

> **Mục đích:** Chứng minh cá nhân hóa mù — AI nhận diện thói quen riêng khi người dùng hỏi chung chung.
> **Tài khoản demo:** User #51 thuộc nhóm **Nội trợ Nấu lẩu** (ID 1–150).

| Bước | Hành động trên màn hình | Kỳ vọng quan sát |
|:-:|---|---|
| 1 | Gõ: **"Gợi ý cho tôi vài món"** | Chatbot trả kết quả |
| 2 | Quan sát cards | 4/5 sản phẩm badge `[cf]`, liên quan nấu ăn gia đình |
| 3 | Click **Nước mắm Nam Ngư** | Card highlight |
| 4 | **Nhìn Dashboard** | Badge `[cf]` nhảy lên, AI Score ~0.7695 |

**Bảng kết quả kỳ vọng (User #51 — Nhóm Nội trợ):**

| # | Sản phẩm | Source | AI Score |
|:-:|---|:-:|:-:|
| 1 | Nước mắm Nam Ngư 11 độ đạm chai 750ml | `cf` | ~0.7695 |
| 2 | Rau muống VietGAP bó 500g | `apriori` | ~0.1768 |
| 3 | Cherry đỏ Mỹ size 9.5 | `cf` | ~0.3509 |
| 4 | Gia vị nêm sẵn lẩu Thái Barona 80g | `cf` | ~0.3422 |
| 5 | Cá viên chiên xâu tôm viên Vissan 500g | `cf` | ~0.3453 |

#### 🧮 Cơ chế tính điểm chi tiết

General query không chứa từ khóa neo → RAG content = 0. Hệ số phạt tìm kiếm rộng: CF ×0.50, Apriori ×0.75.

| Sản phẩm | content | cf (cohort) | apriori | penalty | final_score → AI Score |
|---|:-:|:-:|:-:|:-:|---|
| Nước mắm Nam Ngư | 0.00 | 1.0000 (max) | 0.00 | ×0.50 | 0.25 × 1.00 × 0.50 = **0.1250** → ~**0.7695** |
| Cá viên chiên Vissan | 0.00 | 0.4632 | 0.00 | ×0.50 | 0.25 × 0.4632 × 0.50 = **0.0579** → ~**0.3453** |
| Gia vị lẩu Thái | 0.00 | 0.4578 | 0.00 | ×0.50 | 0.25 × 0.4578 × 0.50 = **0.0572** → ~**0.3422** |
| Cherry đỏ Mỹ | 0.00 | 0.4560 | 0.00 | ×0.50 | 0.25 × 0.4560 × 0.50 = **0.0570** → ~**0.3509** |
| Rau muống (Apriori) | 0.00 | 0.0000 | 0.5000 | ×0.75 | 0.25 × 0.50 × 0.75 = **0.0938** → ~**0.1768** |

> 💡 **Local Scale Normalization:** Điểm CF Nước mắm được lấy làm thang chuẩn Max = 1.0000.

> **Lưu ý:** Nếu đổi sang tài khoản Sinh viên (User 151–300), kết quả sẽ khác hoàn toàn (Mì tôm, Xúc xích, Coca).

> **✅ Checkpoint:** 4 badge `[cf]` + sản phẩm nấu ăn gia đình → Xác nhận thuật toán **3/4**.

---

## ACT 4 · Session Context (δ) — Ngữ Cảnh Xuyên Phiên

> **Mục đích:** Chứng minh AI duy trì ngữ cảnh xuyên suốt phiên chat — giải bài toán Đại từ thế vị.

| Bước | Hành động trên màn hình | Kỳ vọng quan sát |
|:-:|---|---|
| 1 | **Lượt 1:** Gõ **"Tôi muốn nấu lẩu Thái cuối tuần"** | Gia vị lẩu, Ba chỉ bò... badge `[content]` |
| 2 | **Lượt 2:** Gõ **"Gợi ý rau ăn kèm lẩu đi"** | Rau muống, Nấm kim châm... badge `[content]` |
| 3 | **Lượt 3:** Gõ **"Gợi ý thêm đi"** | Hành tây, Rau muống, Nấm... badge **`[session]`** |
| 4 | Click **Hành tây vàng** | Card highlight |
| 5 | **Nhìn Dashboard** | Badge `[session]` nhảy lên, AI Score ~**0.9480** 🎉 |

**Bảng kết quả kỳ vọng — Lượt 2:**

| # | Sản phẩm | Source | AI Score |
|:-:|---|:-:|:-:|
| 1 | Rau muống VietGAP bó 500g | `content` | ~0.7787 |
| 2 | Nấm kim châm Hàn Quốc gói 150g | `content` | ~0.7746 |
| 3 | Nước tương Chinsu tỏi ớt chai 250ml | `content` | ~0.3814 |
| 4 | Ba chỉ bò Mỹ thái lát mỏng khay 500g | `cf`/`none` | ~0.1813 |
| 5 | Bún tươi Ba Khánh gói 500g | `apriori` | ~0.1781 |

**Bảng kết quả kỳ vọng — Lượt 3:**

| # | Sản phẩm | Source | AI Score |
|:-:|---|:-:|:-:|
| 1 | Hành tây vàng loại 1 kg | `session` | ~0.9480 |
| 2 | Rau muống VietGAP bó 500g | `session` | ~0.7787 |
| 3 | Nấm kim châm Hàn Quốc gói 150g | `session` | ~0.7746 |

#### 🧮 Cơ chế tính điểm và Xử lý ngữ cảnh

1. **Deterministic Reformulator** phát hiện ý định tiếp tục → kết hợp lịch sử chat → duy trì ngữ cảnh "lẩu/rau"
2. **Session Context Service** so khớp nhóm sản phẩm thuộc cụm vegetables/hotpot cluster
3. **Session Boost (+0.19)** cộng trực tiếp vào điểm số:

| Sản phẩm | base_score | Session Boost | AI Score |
|---|:-:|:-:|:-:|
| Hành tây vàng | ~0.7580 | +0.19 | **0.9480** |
| Rau muống VietGAP | ~0.5887 | +0.19 | **0.7787** |
| Nấm kim châm | ~0.5846 | +0.19 | **0.7746** |

> 💡 **Category-Driven mapping** thay vì hardcode Product ID — khi admin thêm sản phẩm mới vào danh mục rau/bún/thịt, hệ thống tự nhận diện. WarmUp in-memory, O(1).

> **Điểm mấu chốt:** Ở Lượt 3, câu hỏi *"Gợi ý thêm đi"* **không chứa từ khóa** liên quan lẩu hay rau. Hệ thống tự nhớ ngữ cảnh từ 2 lượt trước.

> **✅ Checkpoint:** Badge `[session]` hiển thị ở Lượt 3 → Xác nhận thuật toán **4/4 hoàn tất**.

---

## Kết Luận — Vòng Lặp Học Hỏi Tự Động (Weight Learner)

### Luồng dữ liệu Feedback

Mỗi thao tác của khách hàng trong demo đều được ghi nhận vào bảng `recommendation_feedback` kèm **nhãn nguồn gốc thuật toán** (`content`, `apriori`, `cf`, `session`):

| Thao tác trong demo | Action ghi nhận | Trọng số Weighted Conversion |
|---|---|:-:|
| Chatbot trả kết quả | `recommended` | — (mẫu số) |
| Rê chuột qua sản phẩm (hover) | `hovered` | ×0.1 |
| Click vào product card | `clicked` | ×0.2 |
| Bấm "Thêm vào giỏ" | `added_to_cart` | ×0.5 |
| Thanh toán thành công | `purchased` | ×1.0 |

> **Ví dụ thực tế từ demo:** Khi click vào Bánh xốp Nabati (ACT 1), hệ thống ghi nhận 1 record `action='clicked'`, `source='content'` → Đóng góp **0.2 điểm** vào Weighted Conversion của thuật toán Content-Based.

### Thuật toán Weight Learner (Nightly Batch)

| Bước | Mô tả | Công thức / Chi tiết |
|:-:|---|---|
| 1 | **Lấy trọng số hiện tại** | Query bảng `ensemble_weights` (mặc định: α = 0.40, β = 0.25, γ = 0.25, δ = 0.10) |
| 2 | **Tính Weighted Conversion Rate** | `Rate(s) = (purchased * 1.0 + added_to_cart * 0.5 + clicked * 0.2 + hovered * 0.1) / recommended` cho từng source `s` |
| 3 | **Chuẩn hóa** | `raw_weight(s) = (Rate(s) / sum(Rates)) * (1 - delta)` |
| 4 | **Smoothing (EWMA)** | `w_new = 0.80 * w_old + 0.20 * w_raw` |
| 5 | **Clamp** | Giới hạn mỗi trọng số trong khoảng `[0.05, 0.60]` |
| 6 | **Lưu kết quả** | Cập nhật `ensemble_weights` + ghi lịch sử vào `ensemble_weights_history` |

### Guardrails (An toàn)

| Điều kiện | Hành vi |
|---|---|
| Tổng feedback < 20 mẫu | **Bỏ qua** — giữ nguyên trọng số |
| Không có interaction mới trong 24h | **Bỏ qua** — tránh học lại dữ liệu cũ |
| Weighted Conversion tổng < 1.0 | **Bỏ qua** — chưa đủ tín hiệu chuyển đổi |
| Organic feedback > 80% | **Cảnh báo** (không chặn) — cần tăng engagement chatbot |
| δ (Session/Personal) | **Cố định** — không tham gia vào vòng lặp tự học |

### Ánh xạ Demo → Trọng số

| ACT | Click sản phẩm | Source ghi nhận | Ảnh hưởng trọng số |
|:-:|---|:-:|---|
| 1 | Bánh xốp Nabati | `content` | ↑ **α** (Content-Based) |
| 2 | Khô gà lá chanh | `apriori` | ↑ **γ** (Apriori) |
| 3 | Nước mắm Nam Ngư | `cf` | ↑ **β** (Collaborative Filtering) |
| 4 | Hành tây vàng | `session` | Ghi nhận nhưng **δ cố định** |

> 💡 **Weight Evolution Chart** trên Dashboard hiển thị lịch sử trọng số α,β,γ,δ theo thời gian — cho phép giảng viên quan sát xu hướng thích ứng của hệ thống.

> **✅ Final:** Vòng lặp khép kín: **Gợi ý → Tương tác → Tự học → Gợi ý tốt hơn**. 4/4 thuật toán đã kiểm chứng.

---

## Phụ Lục — Câu Hỏi Phản Biện

| Câu hỏi | Trả lời |
|---|---|
| User mới, chưa có lịch sử? | CF trả về rỗng → fallback Content + Apriori (cold-start graceful degradation) |
| Session Context nhớ qua phiên khác? | Không — Short-term Memory trong cùng 1 phiên. Long-term do CF qua `user_product_interaction` |
| Apriori có gợi ý sai danh mục? | Chỉ gợi ý khi Lift > 1 (mua kèm cao hơn ngẫu nhiên) và sản phẩm còn hàng |
| Latency có tăng khi thêm thuật toán? | Pipeline ~200–400ms. Local KB ~1ms, Catalog fallback timeout 500ms. WarmUp in-memory, O(1) |
| Category-Driven có hạn chế? | Category names phải khớp với data-ingestion. Đổi tên category → cần restart chatbot để warmUp |
| Tại sao δ không tự học? | Personalization weight giữ cố định để tránh overfitting trên dữ liệu session ngắn hạn |
| Smoothing 80/20 nghĩa là gì? | Trọng số mới = 80% giá trị cũ + 20% giá trị học được → tránh dao động mạnh, ổn định hội tụ |
