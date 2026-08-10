# KỊCH BẢN THUYẾT TRÌNH BẢO VỆ ĐỒ ÁN — V2

> **Dự kiến**: 20 phút  
> **Thông điệp xuyên suốt**: *"Hệ thống phòng thủ nhiều lớp cấp Production (Production-grade Multi-layer Defense System)"*

---

## I. Mở đầu & Đặt vấn đề (2 phút)

"Kính thưa Hội đồng,

Đề tài của em là **'Hệ Thống Gợi Ý Sản Phẩm AI — POSMART'**. Khác với các chatbot hỏi đáp thông thường, mục tiêu của em là biến chatbot thành một **nhân viên bán hàng chủ động**.

Hệ thống gợi ý trải qua **hai giai đoạn phát triển**:

- **Giai đoạn 1:** Kiến trúc **Hybrid Ensemble** (Hộp trắng) — kết hợp 4 thuật toán truyền thống (RAG, Apriori, CF, Personalization) với trọng số tĩnh α, β, γ, δ. Cho phép hệ thống hoạt động ngay từ ngày đầu nhờ RAG, và tự học trọng số qua vòng lặp phản hồi (Adaptive Weight Learning).

- **Giai đoạn 2:** Nâng cấp lên **Kiến trúc Hai Tầng (Two-Tier Architecture)**:
  - **Tầng 1 (AI Fast Path):** Mạng nơ-ron Wide & Deep Two-Tower (ONNX) — tự động trích xuất đặc trưng ẩn với độ trễ dưới 1 mili-giây.
  - **Tầng 2 (Graceful Fallback):** Bộ 4 thuật toán cũ được đóng gói trong module riêng biệt, tự động kích hoạt khi AI Service gặp sự cố — đảm bảo **Zero Downtime**."

---

## II. Phân tích: Tại sao chọn kiến trúc Hai Tầng? (2 phút)

"Trước khi đi sâu, em xin trình bày bài toán đánh đổi giải thích lý do hệ thống tiến hóa qua 2 giai đoạn:"

### Bảng so sánh 3 kiến trúc

| Tiêu chí | V1: Hybrid Ensemble (Static) | Deep Learning thuần túy | **V2: Two-Tier Architecture** |
|---|---|---|---|
| **Cold-start** | ✅ RAG giải quyết | ❌ Không hoạt động | ✅ RAG + SBERT frozen |
| **Explainability** | ✅ White-box | ❌ Black-box | ✅ White-box Fallback |
| **Fault Tolerance** | ❌ Single Point of Failure | ❌ Khi GPU/AI sập → ngắt | ✅ **Circuit Breaker** |
| **Latency** | ~150-300ms | Tùy implement | **< 1ms** (ONNX CPU) |
| **Tài nguyên** | CPU vừa phải | Cần GPU đắt tiền | ONNX tối ưu CPU |
| **Học đặc trưng ẩn** | ❌ Thủ công | ✅ Tự động | ✅ Tự động |

"Điểm khác biệt cốt lõi: V2 **không loại bỏ** V1 — mà **nâng cấp V1 thành lưới an toàn** cho V2. Khi AI gặp sự cố, hệ thống tự động chuyển về Hybrid Ensemble mà người dùng không bao giờ nhận ra."

---

## III. Đi sâu thuật toán — 4 trụ cột Fallback Layer (6 phút)

### 1. Content-Based Filtering với RAG và RRF (α)

- **Bản chất:** Tìm sản phẩm khớp với câu hỏi bằng 2 luồng song song:
  - **Semantic Search:** Vector 768 chiều qua index HNSW — $O(\log n)$
  - **Keyword Search:** Full-Text Search qua GIN index — $O(k)$
- **RRF Fusion (k=60):** Hợp nhất bằng thứ hạng, không cần normalize score
- **Top 5:** Từ rank 6, score giảm đột ngột 51% — noise thay vì giá trị

### 2. Luật Kết hợp Apriori (γ)

- **Bản chất:** Cross-sell dựa trên quy luật mua kèm
- **Thước đo:** Lift > 1 = tương quan thật sự
- **Ví dụ:** 60% khách mua Ba chỉ bò cũng mua Nấm kim châm → lift = 3.00
- **Runtime:** $O(1)$ nhờ cache index + nightly batch 2AM

### 3. Item-based Collaborative Filtering (β)

- **Bản chất:** Gợi ý dựa trên hành vi mua tương tự của đám đông
- **Plain Cosine** (không Adjusted): Phù hợp Implicit Feedback
- **Pruning:** Loại cặp có < 2 common users → giảm 70-80% tính toán

### 4. Hybrid Ensemble & Adaptive Weight Learning

- **Công thức:** $\text{Score} = \alpha \cdot \text{Content} + \beta \cdot \text{CF} + \gamma \cdot \text{Apriori} + \delta \cdot \text{Personal}$
- **Vòng lặp tự học:** Feedback 5 bước (Recommended → Hovered → Clicked → Cart → Purchased) → Exponential Smoothing (80% cũ + 20% mới) → Trọng số tối ưu

"Tất cả 4 thuật toán này giờ đây được đóng gói trong `LegacyFallbackService` — module riêng biệt tuân thủ nguyên tắc **Single Responsibility Principle** trong SOLID."

---

## IV. Nâng cấp: Wide & Deep Two-Tower Neural Network (3 phút)

"Kính thưa Hội đồng, em xin trình bày kiến trúc mạng nơ-ron Học Sâu đã huấn luyện."

### 4.1 Kiến trúc — Tại sao Wide & Deep?

- **User Tower:** Embedding User_ID + Persona → MLP → Vector 64 chiều (đại diện CF & Session)
- **Item Tower:** SBERT Embedding 768d (frozen) → Linear → Vector 64 chiều (đại diện Content-RAG)
- **Wide Layer:** Apriori Co-purchase Lift score → Linear (đại diện Apriori)

"Tại sao cần Wide Layer? Vì nó là công cụ **bảo tồn tri thức luật kết hợp**. Khi kết hợp vào Deep Learning, các quy luật mua kèm truyền thống như Bia↔Khô gà (lift=1.74) được truyền trực tiếp vào mạng nơ-ron, thay vì chờ model tự khám phá lại từ đầu. **Memorization** (Wide) + **Generalization** (Deep)."

### 4.2 Data Pipeline — Chống Popularity Bias

"Kỹ thuật Negative Sampling quan trọng bậc nhất: 50% **Hard Popular Negatives** (các SP bán chạy nhất mà user KHÔNG mua) + 50% **Uniform Random**. Điều này buộc model phân biệt 'phổ biến' với 'phù hợp' — chống lại Thiên kiến tính phổ biến, vấn đề kinh điển trong recommendation systems."

### 4.3 Kết quả huấn luyện

| Metric | Giá trị |
|---|---|
| NDCG@10 | **1.0000** |
| AUC-ROC | **0.9984** |
| Hit Rate@10 | **100%** |
| ONNX Latency | **0.125 ms / sample** |

"Cần lưu ý rằng kết quả này đạt được trên tập dữ liệu giả lập có chủ đích (Synthetic Data) — nhằm minh chứng **tính hội tụ** của kiến trúc Two-Tower. Trên dữ liệu thực tế với nhiều nhiễu, các giá trị sẽ thấp hơn — đây là đặc điểm chung khi chuyển từ lab sang production."

---

## V. AI Serving & Circuit Breaker — Hệ Thống Phòng Thủ (2 phút)

"Đây là phần **kiến trúc phần mềm** quan trọng nhất."

### 5.1 Kiến trúc Serving

- **FastAPI (Python, Port 8000):** Load ONNX model + 1,380 product features vào RAM (4.2 MB). Latency < 1ms.
- **AIClient (Node.js):** HTTP client với **Circuit Breaker** bảo vệ hệ thống.
- **LegacyFallbackService:** Module fallback chứa 5 bước scoring cũ.

### 5.2 Circuit Breaker — 3 Trạng thái

"Em đã thiết kế mẫu Circuit Breaker (Cầu dao) với 3 trạng thái:"

| Trạng thái | Hành vi | Điều kiện chuyển |
|---|---|---|
| **CLOSED** | Gửi request bình thường đến FastAPI | 3 lần thất bại liên tiếp → OPEN |
| **OPEN** | Trả `null` ngay lập tức → Fallback | Hết 30 giây → HALF_OPEN |
| **HALF_OPEN** | Gửi 1 request thăm dò (probe) | Thành công → CLOSED; Thất bại → OPEN |

### 5.3 Demo Insight

"Nếu Hội đồng cho phép, em xin demo trực tiếp: khi em **tắt FastAPI** giữa chừng, hệ thống chatbot **vẫn hoạt động bình thường** — chatbot vẫn trả về câu trả lời và thẻ sản phẩm nhờ cầu dao tự động chuyển sang Legacy Fallback. Sau đó, khi em bật lại FastAPI và chờ 30 giây, cầu dao tự phục hồi trạng thái CLOSED, khôi phục hoàn toàn AI Fast Path. **Zero Downtime.**"

---

## VI. Đánh giá Tổng thể Hệ thống (2 phút)

### 6.1 Bảng đánh giá tổng hợp

| Thuật toán / Mô hình | Metric chính | Kết quả | Điểm mạnh |
|---|---|---|---|
| **RAG + RRF** | Precision@5 | ≥ 80% | Cold-start, không cần lịch sử |
| **Apriori** | Lift > 1 rate | ≥ 60% | Cross-sell, giải thích được |
| **CF** | Hit Rate@5 | ≥ 40% | Cá nhân hóa theo hành vi |
| **Two-Tower ONNX** | NDCG@10 | 1.0000 | Latency < 1ms, tự động học |
| **Circuit Breaker** | 4/4 scenarios | Passed | Zero Downtime |

### 6.2 So sánh trước và sau nâng cấp

| Chỉ số | V1 (Hybrid Ensemble) | V2 (Two-Tier Architecture) |
|---|---|---|
| Scoring Latency | ~150-300ms | **< 1ms** |
| Fault Tolerance | Không | **Circuit Breaker** |
| Feature Learning | Thủ công | **Tự động (Neural)** |
| Cold-start | RAG | RAG + SBERT frozen |

---

## VII. Phương án Cải tiến: Hover Dwell & Dual-Tracking (2 phút)

### 7.1 Tín hiệu Hover Dwell

"Hover giống như **quan sát ngôn ngữ cơ thể** trong bán lẻ: khách *cầm món hàng lên xem rồi đặt xuống* (≥ 1.5s) có giá trị cao hơn khách *đi thẳng qua*."

**Phễu mới 5 bước:** Recommended → Hovered → Clicked → Cart → Purchased

**Graceful Degradation:** Desktop 5 bước, Mobile 4 bước (không có hover) — Weight Learner vẫn hoạt động.

### 7.2 Dual-Tracking System

- **Luồng 1 (Chatbot):** Đánh giá hiệu quả AI → Weight Learning
- **Luồng 2 (Organic):** Thu thập implicit feedback → CF Interaction Matrix
- **Data Isolation:** Weight Learner **chỉ** dùng dữ liệu chatbot, tránh Data Poisoning

### 7.3 Phương hướng mở rộng tương lai

1. **GRU/Transformer** thay Session Personalization (δ) → học chuỗi hành vi real-time
2. **LinUCB** thay Exponential Smoothing → cá nhân hóa trọng số per-user
3. **Fine-tuning LLM (LoRA)** → chatbot hiểu domain bán lẻ Việt Nam

---

## VIII. Kết luận & Demo (1 phút)

"Kính thưa Hội đồng,

Qua quá trình phát triển hệ thống từ V1 đến V2, POSMART đã chứng minh khả năng:

1. **Gợi ý thông minh** — Mạng nơ-ron Wide & Deep Two-Tower tự động trích xuất đặc trưng ẩn
2. **Chống chịu lỗi** — Circuit Breaker đảm bảo Zero Downtime mọi lúc
3. **Tự học và cải tiến** — Vòng lặp phản hồi 5 bước + Adaptive Weight Learning
4. **Giải thích được** — Fallback Layer White-box cho phép admin gỡ lỗi từng thuật toán

Sự kết hợp giữa **Deep Learning** (tầng 1) và **Bộ thuật toán truyền thống** (tầng 2 — lưới an toàn) đã biến POSMART thành một **hệ thống phòng thủ nhiều lớp cấp Production** — không chỉ là một chatbot gợi ý, mà là một kiến trúc phần mềm hoàn chỉnh cho ứng dụng bán lẻ thực tế.

Em xin chân thành cảm ơn Hội đồng. Sau đây em sẵn sàng demo Circuit Breaker Failover trực tiếp và nhận câu hỏi phản biện."
