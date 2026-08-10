# Kịch Bản Demo Bảo Vệ Đồ Án — Graceful Fallback Ensemble (Tầng 2)

## Trình Diễn Cỗ Máy Gợi Ý Hộp Trắng Tầng 2 (Graceful Fallback Mode)

> **Bối cảnh sử dụng**: Kịch bản này được thực thi khi **tắt container `ai-service`** (`docker compose stop ai-service`) để trình diễn cho Hội đồng thấy khả năng tự động lùi về cỗ máy Hộp Trắng Multi-Source Ensemble (Content + CF + Apriori + Session) với thời gian chuyển đổi **0ms**.

| Thuật toán Tầng 2 | Điều kiện kích hoạt | Ví dụ thực tế | Badge hiển thị |
|---|---|---|---|
| **Content-Based RAG (α)** | Khách tìm kiếm danh mục / từ khóa | *"Tôi muốn mua bánh quy"* → Gợi ý Danisa, Nabati | 🔵 `[content]` |
| **Apriori Cross-sell (γ)** | Xác định SP mỏ neo | *"Tôi muốn mua bia Heineken"* → Gợi ý Khô gà, Coca | 🟧 `[apriori]` |
| **Collaborative Filtering (β)** | Khách lướt xem tổng hợp | *"Gợi ý cho tôi vài món"* → Gợi ý Nước mắm, OMO | 🟩 `[cf]` |
| **Session Context (δ)** | Chat multi-turn | Lượt 1: *Lẩu Thái* → Lượt 2: *Rau* → Lượt 3: *"Gợi ý thêm"* | 🟨 `[session]` |

---

### ACT 1 · Content-Based RAG (α) & Intent Gating

> **Mục đích:** Chứng minh RAG hiểu ngữ nghĩa sản phẩm từ seed data 1,380 SKU (Bách Hóa Xanh). Truy vấn "bánh quy" trả về đúng sản phẩm thuộc danh mục bánh quy mà không cần gõ tên thương hiệu cụ thể.

**Thao tác:**

| # | Hành động | Màn hình |
|:-:|---|---|
| 1 | Gõ: **"Tôi muốn mua bánh quy"** | Chatbot |
| 2 | Đợi 1–2s → xuất hiện 3 product cards | Chatbot |
| 3 | Click vào **Bánh xốp phô mai Nabati** | Card highlight, feedback gửi đi |
| 4 | Nhìn sang Dashboard | Badge `[content]` (blue) nhảy lên Live Feed |

**Kết quả thực tế (đã kiểm chứng):**

| # | Sản phẩm | Giá | Source |
|:-:|---|:-:|:-:|
| 1 | Bánh xốp phô mai Nabati hộp 150g | 22.400đ | `content` |
| 2 | Bánh quy bơ Danisa hộp thiếc 454g | 135.000đ | `content` |
| 3 | Kẹo mút Chupa Chups hương trái cây gói 10 que | 15.000đ | `content` |

#### 🧮 Cơ chế tính điểm chi tiết (Ensemble Scoring details)
Hệ thống sử dụng trọng số mặc định: `α (Content) = 0.40`, `β (CF) = 0.25`, `γ (Apriori) = 0.25`, `δ (Personal) = 0.10`. Do không có thông tin người dùng và ngữ cảnh chat trước đó, nên điểm CF/Personal bằng 0.

| Sản phẩm | content | apriori effective | penalty (content=0) | final_score (chưa chuẩn hóa) |
|---|:-:|:-:|:-:|:-:|
| Bánh xốp phô mai Nabati | 0.8533 | 0.0000 | ×1.00 | 0.40 × 0.8533 = **0.3413** (normalized ~0.6144) |
| Bánh quy bơ Danisa | 0.8310 | 0.0000 | ×1.00 | 0.40 × 0.8310 = **0.3324** (normalized ~0.5983) |
| Kẹo mút Chupa Chups | 0.8004 | 0.0000 | ×1.00 | 0.40 × 0.8004 = **0.3202** (normalized ~0.5763) |

> **⚡ Ghi chú V2:** Trong chế độ AI Fast Path, Content RAG Score được thay thế bằng Dot Product giữa User Embedding (User Tower) và Item Embedding (Item Tower 64d), tự động nội suy điểm tương đồng ngữ nghĩa mà không cần qua bảng trọng số tĩnh.

**Live Feedback (Dashboard):**

| Badge | Sản phẩm | AI Score |
|:-:|---|:-:|
| `content` | Bánh xốp phô mai Nabati hộp 150g | 0.6144 |
| `content` | Bánh quy bơ Danisa hộp thiếc 454g | 0.5983 |
| `content` | Kẹo mút Chupa Chups hương trái cây gói 10 que | 0.5763 |

**Thuyết minh:**

> *"Khi người dùng nhập 'đồ ăn vặt' hoặc 'bánh kẹo', hệ thống chạy song song 2 luồng: (1) Semantic Search — mã hóa câu hỏi thành Vector 768 chiều bằng mô hình multilingual-e5-base, tính Cosine Similarity trên pgvector; (2) Keyword Search — full-text search bằng PostgreSQL tsvector tiếng Việt. Hai kết quả được hợp nhất bằng Reciprocal Rank Fusion (RRF), đảm bảo vừa đúng ngữ nghĩa và chính xác từ khóa.*
>
> *3 sản phẩm đầu tiên đều là kết quả Content-Based — 'bánh xốp', 'bánh quy', 'kẹo mút' đều tự động được tìm thấy mặc dù khách hàng không cần truy vấn đúng nhãn tên. Tín hiệu Content-RAG đóng vai trò chủ đạo cho truy vấn tìm kiếm rộng này."*

**✅ Checkpoint:** 3 badge `[content]` → Thuật toán 1/5.

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
| 4 | Click sản phẩm Apriori → nhìn Dashboard | Badge `[apriori]` (amber) nhảy lên |

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

> **⚡ Ghi chú V2:** Trong mô hình Wide & Deep Two-Tower, điểm Lift của Apriori được nuôi thẳng vào **Wide Layer**, giúp mô hình học sâu không bị "quên" quy luật mua kèm kinh điển này khi chuyển sang kiến trúc Neural Network.

**Thuyết minh:**

> *"Sản phẩm Coca-Cola và Khô gà xuất hiện dù người dùng KHÔNG hỏi về chúng. Đây là thuật toán Apriori — khai phá luật kết hợp từ 500 đơn hàng. Hệ thống phát hiện khách mua Bia Heineken thường mua kèm Coca-Cola (Lift=1.90, 165 đơn mua kèm) và Khô gà (Lift=1.74, 146 đơn mua kèm). Đây chính là hiện tượng 'Bia và Bỉm' kinh điển trong Data Mining."*

**✅ Checkpoint:** Badge `[apriori]` + Coca-Cola/Khô gà → Thuật toán 2/5.

---

### ACT 3 · Collaborative Filtering (β)

> **Mục đích:** Chứng minh cá nhân hóa mù (Blind Personalization) — AI nhận diện thói quen riêng khi người dùng hỏi chung chung, không có từ khóa mỏ neo.
>
> **Điểm mạnh:** Ma trận tương đồng Item-Item phân loại user theo hành vi cộng đồng. Cùng một câu hỏi, nhưng kết quả khác nhau hoàn toàn giữa các nhóm người dùng (Nội trợ → Nước mắm, Rau muống, Gia vị lẩu; Sinh viên → Mì tôm, Xúc xích, Coca).

**Thao tác:**

| # | Hành động | Màn hình |
|:-:|---|---|
| 1 | Bấm 🔄 Phiên chat mới | Chat trống |
| 2 | Gõ: **"Gợi ý cho tôi vài món"** | Chatbot |
| 3 | Đợi kết quả → xuất hiện sản phẩm có badge `[cf]` chiếm đa số (3–4/5 slot) | Chatbot |
| 4 | Click sản phẩm CF → nhìn Dashboard | Badge `[cf]` (emerald) nhảy lên |

**Kết quả thực tế (User #51, nhóm Nội trợ):**

| # | Sản phẩm | Source | AI Score |
|:-:|---|:-:|:-:|
| 1 | Nước mắm Nam Ngư 11 độ đạm chai 750ml | `cf` | 0.7695 |
| 2 | Rau muống VietGAP bó 500g | `apriori` | 0.1768 |
| 3 | Cherry đỏ Mỹ size 9.5 (Hộp 500g - Hàng VIP) | `cf` | 0.3509 |
| 4 | Gia vị nêm sẵn lẩu Thái Barona 80g | `cf` | 0.3422 |
| 5 | Cá viên chiên xâu tôm viên Vissan 500g | `cf` | 0.3453 |

> **⚡ Ghi chú V2:** Trong Two-Tower, các đặc trưng ẩn (latent features) của Collaborative Filtering được tự động trích xuất từ User Tower MLP (User_ID + Persona Cluster → 64d vector) thay vì phải tính toán ma trận Cosine thủ công.

**Thuyết minh:**

> *"Câu hỏi 'Gợi ý cho tôi vài món' hoàn toàn không chứa từ khóa cụ thể. Đó là nhờ Collaborative Filtering — hệ thống phân tích dữ liệu tương tác của 500 người dùng, phát hiện tài khoản #51 thuộc nhóm 'Nội trợ Nấu lẩu', nên gợi ý sản phẩm mà nhóm user tương tự thường xuyên mua."*

**✅ Checkpoint:** 4 badge `[cf]` + 1 badge `[apriori]` → Thuật toán 3/5.

---

### ACT 4 · Session Context (δ) — Real-time Multi-turn Boost

> **Mục đích:** Chứng minh AI duy trì ngữ cảnh xuyên suốt phiên chat (Multi-turn Context) — giải bài toán Đại từ thế vị.
>
> **Điểm mạnh:** Khi khách hỏi "Gợi ý thêm đi", Category-Driven Session mapping tự động nhận diện chủ đề từ lịch sử, khóa chặt danh mục liên đới mà không cần truy xuất lại DB.

**Thao tác (3 lượt cùng session):**

| # | Hành động | Màn hình |
|:-:|---|---|
| 1 | Bấm 🔄 Phiên chat mới | Chat trống |
| 2 | **Lượt 1:** Gõ: **"Tôi muốn nấu lẩu Thái cuối tuần"** | Gia vị lẩu, Ba chỉ bò... badge `[content]` |
| 3 | **Lượt 2:** Gõ: **"Gợi ý rau ăn kèm lẩu đi"** | Rau muống, Nấm kim châm... badge `[content]` |
| 4 | **Lượt 3:** Gõ: **"Gợi ý thêm đi"** | Hành tây vàng, Rau muống, Nấm kim châm... badge `[session]` |
| 5 | Click **Hành tây vàng** → nhìn Dashboard | Badge `[session]` (rose) nhảy trên Live Feed 🎉 |

**Kết quả thực tế Lượt 3:**

| # | Sản phẩm | Giá | Source | AI Score |
|:-:|---|:-:|:-:|:-:|
| 1 | Hành tây vàng loại 1 kg | 30.000đ | `session` | 0.9480 |
| 2 | Rau muống VietGAP bó 500g | 10.500đ | `session` | 0.7787 |
| 3 | Nấm kim châm Hàn Quốc gói 150g | 18.000đ | `session` | 0.7746 |

**Thuyết minh:**

> *"Ở lượt 3, người dùng chỉ gõ 'Gợi ý thêm đi'. Tuy nhiên hệ thống vẫn trả về Hành tây vàng, Rau muống, Nấm kim châm với nhãn nguồn gốc là `[session]` nhờ cơ chế Deterministic Reformulator duy trì ngữ cảnh lẩu và áp dụng Session Boost (+0.19).*

**✅ Checkpoint:** Badge `[session]` hiển thị ở Lượt 3 → Thuật toán 4/5.

---

### ACT 5 · Two-Tower AI trên Dashboard (Nút Thắt Cao Trào — Showstopper) 🚀

> **Mục đích:** Chứng minh mạng nơ-ron Học Sâu Wide & Deep Two-Tower (ONNX) đang trực tiếp phục vụ gợi ý trong môi trường Production — biến "Hộp Đen" (Black-box) thành trực quan trên Dashboard.
>
> **Điểm nhấn:** Huy hiệu màu Tím (**`[two_tower_onnx]`**) nổi bật trên Dashboard minh chứng luồng dữ liệu đang chạy qua động cơ AI Fast Path với latency < 1ms.

**Thao tác:**

| # | Hành động | Màn hình |
|:-:|---|---|
| 0 | Đảm bảo FastAPI AI Service đang chạy (port 8000) | Terminal |
| 1 | Bấm 🔄 Phiên chat mới | Chat trống |
| 2 | Gõ: **"Tôi muốn mua bia Heineken"** (như ACT 2) | Chatbot |
| 3 | Nhận kết quả gợi ý sản phẩm | Chatbot |
| 4 | **Mở Dashboard → tab "AI Insights"** | Dashboard |
| 5 | Chỉ vào **Live Feedback Stream**: xuất hiện badge màu tím **`[two_tower_onnx]`** | Dashboard |
| 6 | Chỉ vào **Source Performance Chart**: cột **Two-Tower AI** màu tím xuất hiện | Dashboard |

**Hình ảnh hiển thị thực tế trên Dashboard:**

```
┌────────────────────────────────────────────────────────────────────────┐
│ LIVE FEEDBACK STREAM                                        ● Live     │
├────────────────────────────────────────────────────────────────────────┤
│ User #51  •  Just now                        [two_tower_onnx] (Purple) │
│ 👁️ Recommended: Bia Heineken Silver lon 330ml                          │
│ AI Score: 0.8912                                                       │
├────────────────────────────────────────────────────────────────────────┤
│ User #51  •  Just now                        [two_tower_onnx] (Purple) │
│ 👁️ Recommended: Khô gà lá chanh G kitchen                             │
│ AI Score: 0.7645                                                       │
└────────────────────────────────────────────────────────────────────────┘
```

**Thuyết minh (Thủ pháp "Tự đặt câu hỏi"):**

> *"Kính thưa Hội đồng, hãy quan sát kết quả gợi ý ở Chatbot: các sản phẩm Bia Heineken và Khô gà trông có vẻ giống như ACT 2. Vậy câu hỏi đặt ra là: **Hệ thống có đang lừa chúng ta bằng cách gọi lại code cũ hay không?**
>
> Hãy nhìn sang Dashboard tab **AI Insights**.
>
> Badge nguồn gốc ở đây KHÔNG CÒN là `[content]` (màu xanh) hay `[apriori]` (màu cam) nữa, mà là **`[two_tower_onnx]`** màu Tím độc bản!
>
> Điều này chứng tỏ toàn bộ ứng viên đã được xếp hạng trực tiếp bởi **Mạng nơ-ron Hai Tháp (Two-Tower ONNX)** qua Fast Path với thời gian suy luận dưới 1 mili-giây.
>
> **Tại sao kết quả gợi ý lại tương đồng?**
> Bởi vì mạng nơ-ron Two-Tower đã **học thành công** đúng những mẫu hành vi (patterns) mà 4 thuật toán truyền thống phát hiện bằng thủ công — nhưng với tốc độ nhanh hơn 300 lần, và quan trọng nhất: mô hình AI có khả năng **tự tổng quát hóa (Generalization)** cho các hành vi mua sắm mới mà rule-based không thể bao quát hết."*

**✅ Checkpoint:** Badge `[two_tower_onnx]` (purple) hiển thị trên Dashboard → Chứng minh AI Fast Path hoạt động thành công! (5/5 hoàn tất).

---

## Kết Luận — Kiến Trúc Nâng Cấp & Vòng Lặp Học Hỏi (1 phút)

> *"Kính thưa Hội đồng,
>
> Qua 5 phần trình diễn vừa rồi, POSMART đã chứng minh được sự tiến hóa từ một bộ thuật toán Hộp Trắng thủ công thành một **Kiến Trúc Hai Tầng (Two-Tier Architecture)** hoàn chỉnh:
>
> 1. **Tầng 1 (AI Fast Path):** Mạng nơ-ron Wide & Deep Two-Tower (ONNX) dự đoán cực nhanh (< 1ms), bảo tồn tri thức Apriori qua Wide Layer và tự động hóa trích xuất đặc trưng.
> 2. **Tầng 2 (Graceful Fallback):** Bộ 4 thuật toán cũ (RAG, Apriori, CF, Session) đóng vai trò lưới an toàn Hộp Trắng, sẵn sàng tiếp quản tự động khi AI Service gặp sự cố mà người dùng không nhận ra.
> 3. **Vòng lặp tự học (Adaptive Weight Learning):** Mọi tương tác `[two_tower_onnx]`, `[content]`, `[cf]`, `[apriori]`, `[session]` đều được ghi nhận vào `recommendation_feedback` để hàng đêm tự động cập nhật trọng số.
>
> Đây không đơn thuần là một chatbot gợi ý, mà là một **Hệ Thống Phòng Thủ Nhiều Lớp Cấp Production (Production-grade Multi-layer Defense System)**."*

---

## Phụ Lục — Câu Hỏi Phản Biện Chuyên Sâu

| # | Câu hỏi từ Hội đồng | Trả lời thuyết phục |
|---|---|---|
| 1 | **Tại sao NDCG@10 = 1.0000 tuyệt đối? Liệu có Overfitting?** | NDCG = 1.0 là kết quả trên tập dati Synthetic Data có nhãn persona rõ ràng nhằm **minh chứng tính hội tụ** của thuật toán Hai Tháp. Trên dữ liệu thực tế có nhiễu, NDCG kỳ vọng sẽ đạt ~0.75-0.85 — đây là đặc tính chung khi chuyển từ Lab sang Production. |
| 2 | **Two-Tower là Black-box — làm sao Admin kiểm tra được tại sao AI gợi ý SP đó?** | Thứ nhất, Dashboard track nguồn `[two_tower_onnx]` giúp nhận diện chính xác luồng chạy. Thứ hai, Wide Layer trong mô hình chính là cầu nối Hộp Trắng (Apriori Lift) được đưa trực tiếp vào mạng nơ-ron. Thứ ba, nếu cần giải thích 100%, Admin có thể ngắt AI để hệ thống lùi về White-box Fallback với 4 điểm score α/β/γ/δ rõ ràng. |
| 3 | **Tại sao không dùng GPU để phục vụ ONNX model?** | Với 1,380 SKU, toàn bộ feature cache chỉ chiếm 4.2 MB RAM. ONNX CPU Runtime đạt tốc độ **0.125ms / sample** — nhanh hơn cả RTT mạng HTTP. Dùng GPU cho quy mô này là không cần thiết và lãng phí chi phí hạ tầng (Overkill). |
| 4 | **User mới chưa có lịch sử (Cold-start) thì Two-Tower xử lý thế nào?** | Item Tower sử dụng SBERT Embedding (frozen 768d) mã hóa thông tin ngữ nghĩa sản phẩm, kết hợp RAG Semantic Search. Nhờ đó, cold-start product vẫn được gợi ý chính xác dựa trên điểm tương đồng vector mà không cần lịch sử mua hàng. |
| 5 | **Session Context có nhớ thông tin sang phiên chat khác không?** | Không. Session Context là Short-term Memory lưu in-memory trong thời gian sống của phiên chat. Thói quen dài hạn (Long-term preference) được đảm nhiệm bởi User Tower qua lịch sử mua hàng `user_product_interaction`. |
| 6 | **Apriori có nguy cơ gợi ý sai danh mục không?** | Không. Hệ thống chỉ chấp nhận luật kết hợp khi Lift > 1.0 (xác suất mua kèm cao hơn ngẫu nhiên) và sản phẩm gợi ý phải còn tồn kho (Stock > 0). |
| 7 | **Latency toàn hệ thống là bao nhiêu?** | Với AI Fast Path: ~20-30ms (bao gồm 0.125ms ONNX + network RTT). Khi Fallback: ~150-250ms (RAG vector search + PostgreSQL query). |
| 8 | **Khi đổi tên Danh mục (Category), Session Context có bị ảnh hưởng?** | Dữ liệu Session WarmUp được nạp in-memory khi khởi động backend. Nếu Admin đổi tên danh mục trong DB, chỉ cần gọi endpoint `/chatbot/admin/force-learn` hoặc restart service để làm mới warmUp cache trong $O(1)$. |
