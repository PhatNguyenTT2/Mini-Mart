# Master Plan & Framework chuẩn hóa cho Research Paper (IEEE Format)

> **Dự án:** Hệ thống Gợi ý Sản phẩm Thương mại Điện tử Lai (Hybrid Cascade Ranking Recommender System)  
> **Kiến trúc:** Wide (Apriori) + Deep (Two-Tower with SBERT) & Microservices (Node.js + Python FastAPI + ONNX Runtime)  
> **Chuẩn định dạng:** IEEE Conference / Journal Paper Framework  

---

## MỤC 1: Danh mục Tài liệu Tham khảo Chuẩn (18 Nguồn IEEE)

*Hướng dẫn: Sử dụng tên bài báo bên dưới để tra cứu PDF trên Google Scholar hoặc arXiv. Các nguồn đã được phân nhóm theo vai trò lý thuyết và kỹ thuật trong luận văn.*

### Nhóm A: Thuật toán Cơ sở & Khai phá Dữ liệu (Baseline & Memory)
*Phục vụ giải thích nhánh Wide và các mô hình Baseline truyền thống.*

| STT | Mã Ref | Tác giả & Năm | Tên bài báo / Nguồn | Vai trò trong bài báo |
|---|---|---|---|---|
| 1 | **[1]** | Agrawal, R., & Srikant, R. (1994) | *Fast algorithms for mining association rules* | Thuật toán Apriori (Khai phá luật kết hợp) |
| 2 | **[2]** | Koren, Y., Bell, R., & Volinsky, C. (2009) | *Matrix factorization techniques for recommender systems* | Baseline Matrix Factorization (MF) |
| 3 | **[3]** | Sarwar, B., Karypis, G., Konstan, J., & Riedl, J. (2001) | *Item-based collaborative filtering recommendation algorithms* | Baseline Item-based Collaborative Filtering (CF) |

---

### Nhóm B: Nền tảng Deep Learning & Hệ thống Gợi ý Lai (Hybrid RS)
*Phục vụ biện luận sức mạnh của Mạng nơ-ron và Kiến trúc Hybrid.*

| STT | Mã Ref | Tác giả & Năm | Tên bài báo / Nguồn | Vai trò trong bài báo |
|---|---|---|---|---|
| 4 | **[4]** | He, X., et al. (2017) | *Neural collaborative filtering (NCF)* | Nền tảng Neural CF |
| 5 | **[5]** | Cheng, H. T., et al. (2016) | *Wide & deep learning for recommender systems* | Mô hình Wide & Deep gốc (Core Concept) |
| 6 | **[6]** | Guo, H., et al. (2017) | *DeepFM: a factorization-machine based neural network for CTR prediction* | Mô hình DeepFM (Tích hợp FM và Deep) |
| 7 | **[7]** | Wang, R., et al. (2017) | *Deep & cross network for ad click predictions (DCN)* | Kiến trúc Deep & Cross Network |
| 8 | **[8]** | Covington, P., Adams, J., & Sargin, E. (2016) | *Deep neural networks for YouTube recommendations* | Kiến trúc Phễu 2 giai đoạn (Candidate Generation & Ranking) |

---

### Nhóm C: Kiến trúc Hai Tháp (Two-Tower Architecture) & Scale-up
*Phục vụ trực tiếp cho việc thiết kế Tháp User và Tháp Item (Deep Branch).*

| STT | Mã Ref | Tác giả & Năm | Tên bài báo / Nguồn | Vai trò trong bài báo |
|---|---|---|---|---|
| 9 | **[9]** | Yi, X., et al. (2019) | *Sampling-bias-corrected neural modeling for large corpus item recommendations* | Mạng Two-Tower gốc & Sửa lỗi lấy mẫu (Core) |
| 10 | **[10]** | Yang, J., et al. (2020) | *Mixed negative sampling for learning two-tower neural networks in recommendations* | Chiến lược Mixed/Hard Negative Sampling |
| 11 | **[11]** | Wang, J., et al. (2018) | *Billion-scale commodity embedding for e-commerce recommendation in Alibaba* | Embedding sản phẩm quy mô lớn trong E-commerce |

---

### Nhóm D: Xử lý Ngôn ngữ Tự nhiên & Semantic Embedding
*Phục vụ giải thích biểu diễn ngữ nghĩa sản phẩm trong Tháp Item.*

| STT | Mã Ref | Tác giả & Năm | Tên bài báo / Nguồn | Vai trò trong bài báo |
|---|---|---|---|---|
| 12 | **[12]** | Reimers, N., & Gurevych, I. (2019) | *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks* | Trích xuất Vector nhúng SBERT (Core) |
| 13 | **[13]** | Devlin, J., et al. (2018) | *BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding* | Mô hình nền tảng BERT |
| 14 | **[14]** | Mikolov, T., et al. (2013) | *Distributed representations of words and phrases and their compositionality* | Baseline Word2Vec Embeddings |

---

### Nhóm E: Kỹ thuật Hệ thống, Tối ưu hóa & Cold-Start (System & Serving)
*Phục vụ phần Triển khai (Implementation), Tối ưu độ trễ ONNX và xử lý Cold-Start.*

| STT | Mã Ref | Tác giả & Năm | Tên bài báo / Nguồn | Vai trò trong bài báo |
|---|---|---|---|---|
| 15 | **[15]** | Bai, J., et al. (2019) | *ONNX: Open Neural Network Exchange* | Tối ưu hóa mô hình & Inference Engine (ONNX Runtime) |
| 16 | **[16]** | Volkovs, M., Yu, G., & Poutanen, T. (2017) | *DropoutNet: Addressing cold start in recommender systems* | Giải quyết bài toán Người dùng / Sản phẩm mới (Cold-Start) |
| 17 | **[17]** | Dragoni, N., et al. (2017) | *Microservices: yesterday, today, and tomorrow* | Kiến trúc Microservices trong AI Systems |
| 18 | **[18]** | Järvelin, K., & Kekäläinen, J. (2002) | *Cumulated gain-based evaluation of IR techniques* | Chỉ số đánh giá NDCG và Hit Rate |
| 19 | **[19]** | Krichene, W., & Rendle, S. (2022) | *On the Inconsistency of Evaluation Metrics in Recommender Systems* (RecSys / SIGIR) | Biện luận Full-Catalog Ranking vs Sampled Metrics; chống "Illusion of Accuracy" |

---

## MỤC 2: Khung Sườn Chi Tiết Bài Báo (Chuẩn IEEE) & Ánh Xạ Trích Dẫn

### 1. Introduction (Mở Đầu)

* **1.1. Bối cảnh & Thách thức**
  * Thương mại điện tử bùng nổ dẫn đến quá tải thông tin; hệ thống gợi ý đóng vai trò sống còn để cải thiện trải nghiệm người dùng và tăng tỷ lệ chuyển đổi **[11]**.
  * Các hệ thống thực tế đối mặt với bài toán dữ liệu thưa thớt (sparsity) và cold-start khi xuất hiện sản phẩm/người dùng mới **[16]**.
* **1.2. Đánh đổi giữa Ghi nhớ (Memorization) và Tổng quát hóa (Generalization)**
  * Mô hình truyền thống (như Apriori) giỏi *Memorization* các quy luật mua kèm cố định nhưng thiếu linh hoạt **[1]**, **[5]**.
  * Mạng Deep Learning (như NCF) giỏi *Generalization* ngữ nghĩa ẩn nhưng dễ bỏ sót các tương quan kết hợp trực tiếp **[4]**, **[5]**.
* **1.3. Khuyết điểm Kiến trúc & Nghẽn cổ chai Tốc độ**
  * Mô hình Wide & Deep nối tầng gộp truyền thống gây quá tải tính toán thời gian thực khi scoring hàng ngàn ứng viên **[6]**, **[8]**.
* **1.4. Đóng góp Chính của Bài báo (Key Contributions)**
  1. Đề xuất kiến trúc lai 2 nhánh tách biệt: Wide (Apriori Rule Engine) + Deep (Mạng Hai Tháp độc lập).
  2. Tích hợp SBERT **[12]** đóng băng (Frozen SBERT) để giải quyết triệt để bài toán Cold-Start cho sản phẩm mới.
  3. Triển khai thực tế với ONNX Runtime **[15]** trên hạ tầng Microservices, đạt độ trễ dự đoán cực thấp (<1ms).

---

### 2. Related Work (Các Nghiên Cứu Liên Quan)

* **2.1. Traditional Recommendation Approaches**
  * Tổng quan Lọc cộng tác (CF) **[2]**, **[3]** và khai phá luật kết hợp Apriori **[1]**.
* **2.2. Deep Learning & Hybrid Recommender Systems**
  * Sự phát triển từ NCF **[4]** đến các kiến trúc kết hợp như Wide & Deep **[5]**, DeepFM **[6]**, và DCN **[7]**.
* **2.3. Dual-Tower Architecture (Mạng Hai Tháp)**
  * Sự ưu việt của việc tách rời Tháp User và Tháp Item cho luồng Candidate Generation và Scoring **[8]**, **[9]**.
  * Các kỹ thuật lấy mẫu mẫu âm (Negative Sampling) tối ưu hóa biểu diễn không gian vector **[10]**.
* **2.4. NLP Embeddings trong Hệ thống Gợi ý**
  * Ứng dụng mô hình ngôn ngữ lớn (BERT **[13]**, SBERT **[12]**) trong trích xuất ngữ nghĩa ngữ cảnh sản phẩm.

---

### 3. Proposed Methodology (Phương Pháp Luận Cốt Lõi)

* **3.1. Luồng Hệ thống Phễu Lọc 2 Giai đoạn (Cascade Ranking Pipeline)**
  * Mô hình phễu: Truy xuất ứng viên (Retrieval / Candidate Generation) $\rightarrow$ Xếp hạng chi tiết (Re-ranking / Scoring) **[8]**.
* **3.2. Tiền xử lý & Trích xuất Đặc trưng (Feature Extraction)**
  * **Tháp Item:** Sử dụng SBERT **[12]** đóng băng trọng số để sinh vector ngữ nghĩa 768 chiều từ tên và mô tả sản phẩm.
  * **Tháp User:** Mã hóa lịch sử tương tác, phân cụm hành vi (Persona clusters) và ngữ cảnh.
* **3.3. Nhánh Wide - Bộ nhớ của Hệ thống**
  * Tính toán điểm tương quan từ luật kết hợp (co-purchase lift matrix). Giải quyết các trường hợp mua kèm cứng mà Deep Learning bỏ sót **[5]**.
* **3.4. Nhánh Deep - Kiến trúc Hai Tháp (Two-Tower Network)**
  * Biểu diễn hàm nhúng User $u(x)$ và Item $v(y)$ **[9]**.
  * Sử dụng tích vô hướng (Dot Product) kết hợp L2 Normalization và Temperature Scaling ($\tau$) để tính độ tương đồng:
    $$\text{Score}_{\text{Deep}} = \frac{u(x) \cdot v(y)}{\|u(x)\| \|v(y)\| \cdot \tau}$$
* **3.5. Tích hợp & Huấn luyện Chung (Joint Training)**
  * Kết hợp đầu ra Wide và Deep thông qua hàm kích hoạt Sigmoid **[5]**.
  * Huấn luyện với chiến lược Hard Negative Sampling (tỷ lệ 1:4) và hàm mất mát Binary Cross-Entropy (BCE) **[10]**.

---

### 4. System Implementation (Triển Khai Hệ Thống)

* **4.1. Tiền tính toán Offline (Offline Pre-computation)**
  * Xuất trước toàn bộ vector embedding của Tháp Item vào CSDL (Vector DB / Cache) để truy vấn tức thì **[9]**.
* **4.2. Tối ưu hóa Inference với ONNX Runtime**
  * Chuyển đổi mô hình PyTorch sang định dạng ONNX. Áp dụng Constant Folding và Layer Fusing để tăng tốc độ tính toán **[15]**.
* **4.3. Kiến trúc Microservices Thực tế**
  * Thiết kế luồng giao tiếp bất đồng bộ giữa API Gateway (Node.js) và Inference Service (Python FastAPI) **[17]**.

---

### 5. Experiments & Results (Thực Nghiệm & Kết Quả)

* **5.1. Thiết lập Thực nghiệm (Experimental Setup)**
  * Mô tả tập dữ liệu Controlled Proprietary Vietnamese E-commerce Benchmark (500 users, 1,380 SKUs, ~7.2% density), siêu tham số (Hyper-parameters, Batch Size, Learning Rate, Optimizer).
  * Biện luận quy mô dữ liệu: Full-Catalog Ranking (690,000 predictions/test run) thay vì Sampled Metrics **[19]**.
* **5.2. Chỉ số Đánh giá (Evaluation Metrics)**
  * Định nghĩa công thức toán học của Hit Rate@10 (HR@10), Normalized Discounted Cumulative Gain@10 (NDCG@10) **[18]**, và GAUC.
  * Giải thích tại sao NDCG@10 tuyệt đối thấp (0.0644-0.0782) là hệ quả trực tiếp của Full-Catalog Ranking với mẫu số IDCG lớn, không phải do mô hình yếu **[18]**, **[19]**.
* **5.3. Kết quả So sánh Mô hình (Performance Comparison)**
  * Bảng so sánh hiệu năng giữa mô hình Đề xuất vs. Baselines (Rule-based, Standard MF **[2]**, NCF **[4]**, Wide & Deep gốc **[5]**).
  * Phân tích nguyên nhân mô hình Đề xuất đạt độ chính xác cao hơn nhờ sự kết hợp Apriori + SBERT.
* **5.4. Đánh giá Tốc độ & Độ trễ (Latency Analysis)**
  * So sánh thời gian xử lý khi scoring 100 sản phẩm ứng viên giữa PyTorch native (`.pt`) và ONNX Engine (`.onnx`).

---

### 6. Conclusion & Future Work (Kết Luận & Hướng Phát Triển)

* **6.1. Kết luận**
  * Khẳng định sự kết hợp giữa Wide (Apriori) và Deep (Two-Tower + SBERT) đạt được sự cân bằng tối ưu giữa Độ chính xác (Accuracy) và Tốc độ đáp ứng (Latency).
* **6.2. Hướng Phát triển Tương lai**
  * Tích hợp thuật toán Multi-Armed Bandit (LinUCB) để phản hồi hành vi người dùng theo thời gian thực (Real-time Dynamic Personalization).
  * Áp dụng Mạng hồi quy (GRU / Transformer) cho bài toán gợi ý theo phiên (Session-based Recommendation).

---

## MỤC 3: Hướng Dẫn Thực Hiện & Lời Khuyên (Best Practices)

> [!TIP]
> **Quy trình triển khai viết bài hiệu quả:**
> 1. **Khởi tạo Document:** Tạo file làm việc (Word/LaTeX template chuẩn IEEE). Dựng sẵn toàn bộ Khung Đề mục từ Mục 1 đến Mục 6.
> 2. **Ưu tiên Viết trước:** Tập trung viết **Mục 3 (Proposed Methodology)** và **Mục 4 (System Implementation)** trước vì đây là phần hệ thống bạn đã xây dựng và nắm rõ nhất.
> 3. **Chèn Trích dẫn (Citation Mapping):** Trong quá trình viết từng câu/ý tưởng, tra cứu danh mục 18 tài liệu tham khảo ở MỤC 1 và chèn ngay mã trích dẫn `[x]` tương ứng.