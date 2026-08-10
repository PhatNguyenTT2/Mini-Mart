# Kịch Bản Demo Bảo Vệ Khóa Luận: Mạng Nơ-ron Hai Tháp (Two-Tower Deep Learning Recommender)

> **Mục tiêu**: Trình diễn cỗ máy gợi ý AI Tầng 1 (AI Fast Path - Wide & Deep Two-Tower ONNX) hoạt động siêu tốc (< 1ms), khả năng cá nhân hóa dựa trên vector ẩn 64 chiều, và cơ chế chuyển đổi mềm dẻo (Graceful Fallback) khi gặp sự cố.
> 
> 📖 **Hồ sơ Kỹ thuật Thuật toán Chi tiết**:
> - [01-content-based.md](file:///e:/UIT/cv/backend/backend/docs/neural/01-content-based.md) — Semantic RAG (SBERT 768d + RRF)
> - [02-collaborative-filtering.md](file:///e:/UIT/cv/backend/backend/docs/neural/02-collaborative-filtering.md) — Item-Item CF & Persona Clusters
> - [03-apriori.md](file:///e:/UIT/cv/backend/backend/docs/neural/03-apriori.md) — Association Rule Mining & Data Tuning Analysis
> - [04-two-tower.md](file:///e:/UIT/cv/backend/backend/docs/neural/04-two-tower.md) — Wide & Deep Two-Tower ONNX Architecture & Fallback Circuit Breaker
> - [05-training-results.md](file:///e:/UIT/cv/backend/backend/docs/neural/05-training-results.md) — Kết Quả Huấn Luyện & Giải Thích Metrics

---

## 🎬 5 Hồi Kịch Bản Trình Diễn (Showstopper Demo)

### ACT 1: Gợi Ý Đa Kênh Tốc Độ Siêu Tốc (Semantic RAG Search)
- **Thao tác**: Trên giao diện Chatbot, nhập truy vấn:
  > *"Tôi muốn mua bánh quy"*
- **Kết quả hiển thị**: Chatbot trả về danh sách các sản phẩm Bánh quy (Danisa, Gouté, Nabati, Chocopie) từ seed data Bách Hóa Xanh.
- **Minh chứng AI**:
  - Mã nguồn thực thi qua FastAPI AI Microservice (`localhost:8000/recommend`).
  - Vector truy vấn được đối chiếu trong không gian ẩn 768 chiều với dữ liệu `product_features.parquet`.
  - Thời gian phản hồi mạng nơ-ron: **< 1ms**.

---

### ACT 2: Khám Phá Quy Luật Mua Kèm Tự Nhiên (Wide Layer Co-Purchase)
- **Thao tác**: Nhập truy vấn:
  > *"Tôi muốn mua bia Heineken"*
- **Kết quả hiển thị**: Mạng Two-Tower trả về Bia Heineken kèm theo các món nhậu tự nhiên (Khô gà, Coca-Cola, Đậu phộng sấy).
- **Minh chứng AI**:
  - Không cần khai báo luật thủ công như Apriori truyền thống.
  - Lớp Wide Layer của mạng nơ-ron tự động kết nối các sản phẩm có chỉ số co-purchase cao từ dữ liệu huấn luyện.

---

### ACT 3: Cá Nhân Hóa Theo Cụm Người Dùng (User Tower Persona Clustering)
- **Thao tác**: Đăng nhập tài khoản thuộc Persona Cluster 1 (Khách hàng gia đình) và hỏi:
  > *"Gợi ý cho tôi vài món tiêu dùng"*
- **Kết quả hiển thị**: Mạng nơ-ron kích hoạt User Tower với `user_id` và `persona_cluster`, ưu tiên đẩy các sản phẩm Nước giặt OMO, Dầu ăn Tường An, Sữa tươi Vinamilk lên đầu danh sách.

---

### ACT 4: Ngữ Cảnh Phiên Ngắn Hạn (Short-Term Session Context)
- **Thao tác**: 
  1. Người dùng bấm xem sản phẩm "Gia vị lẩu Thái".
  2. Tiếp tục bấm xem "Rau muống" và "Nấm kim châm".
  3. Nhập truy vấn: *"Gợi ý thêm đồ ăn cho tôi"*.
- **Kết quả hiển thị**: AI tự bổ sung "Ba chỉ bò slide", "Đậu hũ non" vào danh sách gợi ý. Context embedding được cập nhật thời gian thực vào candidate scoring engine.

---

### ACT 5: "Show, Don't Tell" — Minh Chứng Đáng Giá Nhất Trên Dashboard & Graceful Fallback Toggle

- **Phương Án 1 (Nút Toggle Tạm Thời Trên AI Dashboard - Nhanh & Trực Quan)**:
  - Mở Tab **AI Insights** trên Dashboard.
  - Bấm vào nút trạng thái: **🟢 AI Fast Path (ONNX) Active** $\rightarrow$ Nút chuyển thành **🟡 Fallback Ensemble Mode Active**.
  - Thực hiện lại các truy vấn trên Chatbot:
    - Hỏi *"Tôi muốn mua bia Heineken"* $\rightarrow$ Badge hiển thị **`[apriori]`** kèm Khô gà/Coca-Cola.
    - Hỏi *"Gợi ý cho tôi vài món"* $\rightarrow$ Badge hiển thị **`[cf]`** dựa trên lịch sử mua.
  - Bấm toggle lần nữa $\rightarrow$ Nút chuyển lại **🟢 AI Fast Path (ONNX) Active** $\rightarrow$ Mạng Two-Tower tiếp tục chấm điểm Deep Learning với badge tím **`[two_tower_onnx]`**.

- **Phương Án 2 (Giả lập sự cố Hạ tầng - Stop Container AI)**:
  - Gõ lệnh tại Terminal:
    ```bash
    docker compose stop ai-service
    ```
  - Thực hiện lại truy vấn trên Chatbot $\rightarrow$ Circuit Breaker tự động chuyển hướng sang Tầng 2 Fallback Ensemble trong **0ms**.
  - Gõ `docker compose start ai-service` $\rightarrow$ Hệ thống tự động khôi phục về AI Fast Path!

---

## 📊 Bảng So Sánh Hai Tầng Hệ Thống

| Tiêu chí | Tầng 1: AI Fast Path (Two-Tower) | Tầng 2: Graceful Fallback (Ensemble) |
|:---|:---|:---|
| **Kiến trúc** | Neural Network (User Tower + Item Tower) | Multi-Source Ensemble (Content + CF + Apriori) |
| **Mô hình** | Deep Learning (Black-box, ONNX runtime) | Rule-based & Static Weights ($\alpha, \beta, \gamma, \delta$) |
| **Badge hiển thị** | 🟣 **`[two_tower_onnx]` (Tím)** | 🔵 `[content]`, 🟧 `[apriori]`, 🟩 `[cf]`, 🟨 `[session]` |
| **Latency** | **< 1ms** | 10ms - 25ms |
| **Biểu đồ Weight Evolution** | **Đứng yên (flat line)** — Không dùng trọng số tĩnh | **Cập nhật** sau Nightly Batch |

---

## ❓ 5 Câu Hỏi Phản Bỏ Thường Gặp Của Hội Đồng (Q&A Appendix)

### Q1: "Tại sao biểu đồ Weight Evolution lại đứng yên khi AI Tầng 1 hoạt động?"
> **Trả lời**: Tầng 1 là mạng nơ-ron sâu (Two-Tower) đã nén toàn bộ tri thức vào vector ẩn 64 chiều. Điểm số sinh ra từ hàm Sigmoid/Cosine Similarity chứ không dùng tổ hợp tuyến tính $\alpha \cdot S_{content} + \beta \cdot S_{cf}$. Việc biểu đồ đứng yên chứng minh hệ thống đang phục vụ hoàn toàn bằng AI Fast Path.

### Q2: "Làm thế nào chứng minh được Two-Tower tốt hơn các thuật toán truyền thống?"
> **Trả lời**: Trên widget **Source Performance**, ta so sánh trực tiếp CVR (Tỷ lệ chuyển đổi mua hàng) của thanh màu Tím `two_tower_onnx` so với các thanh màu cũ. Kết quả thực nghiệm cho thấy Two-Tower đạt CVR vượt trội nhờ khả năng capture phi tuyến tính giữa người dùng và sản phẩm.

### Q3: "Nếu container AI bị sập thì hệ thống xử lý ra sao?"
> **Trả lời**: Bộ ngắt mạch Circuit Breaker trong Node.js backend sẽ bắt lỗi connection ECONNREFUSED trong vòng < 1ms, lập tức chuyển hướng lưu lượng sang Tầng 2 Fallback Ensemble. Người dùng hoàn toàn không thấy thông báo lỗi.

### Q4: "Tập dữ liệu 1,380 sản phẩm lấy từ đâu và có thực tế không?"
> **Trả lời**: Tập dữ liệu được thu thập (scrape) trực tiếp từ hệ thống Bách Hóa Xanh thực tế, bao gồm đầy đủ 160+ danh mục từ Thực phẩm tươi sống, Đồ khô, Nước giải khát cho đến Chăm sóc cá nhân.

### Q5: "Mô hình được tối ưu hóa như thế nào để đạt latency < 1ms?"
> **Trả lời**: Mô hình PyTorch được export sang định dạng **ONNX (Open Neural Network Exchange)** và chạy trên ONNX Runtime C++ backend. Dữ liệu embedding của 1,380 sản phẩm được nạp sẵn vào RAM (In-Memory Cache) khi server khởi động.
