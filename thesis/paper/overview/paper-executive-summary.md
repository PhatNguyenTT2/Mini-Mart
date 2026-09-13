# TỔNG QUAN ĐIỀU HÀNH BÀI BÁO KHOA HỌC (EXECUTIVE SUMMARY)
## ĐỀ TÀI: REPRODUCIBLE HYBRID RECOMMENDATION FOR VIETNAMESE RETAIL

**Tài liệu tham chiếu:** Bài báo khoa học `paper.tex` và bản in xuất bản `paper.pdf` (10 trang IEEE)  
**Tác giả:** Nguyễn Trương Tiến Phát, Đỗ Minh Đức, TS. Nguyễn Thị Xuân Hương (GVHD)  
**Đơn vị:** Khoa Công nghệ Phần mềm, Trường Đại học Công nghệ Thông tin, ĐHQG-HCM  
**Địa chỉ lưu trữ:** `thesis/paper/overview/paper-executive-summary.md`

---

## 1. TỔNG QUAN BÀI BÁO VÀ TẦM NHÌN NGHIÊN CỨU

Bài báo **"Reproducible Hybrid Recommendation for Vietnamese Retail"** giải quyết cuộc khủng hoảng tính tái lập trong nghiên cứu Hệ thống Gợi ý (RecSys) bằng cách thiết lập một giao thức thực nghiệm nhận thức nguồn gốc (Provenance-aware Evaluation Protocol) và đề xuất kiến trúc mạng lai phân rã **Wide-and-Deep Two-Tower Hybrid** tối ưu hóa cho ngành bán lẻ đa kênh tại Việt Nam.

### Sơ đồ Kiến trúc Mô hình Lai Đề xuất

```mermaid
graph TD
    subgraph INPUTS ["1. Dữ liệu Đầu vào Đa nguồn"]
        U_IN["Lịch sử Giao dịch & Giỏ hàng Người dùng (H_u)"]
        I_IN["Thuộc tính & Ngữ nghĩa Sản phẩm (SBERT + Giá bán)"]
    end

    subgraph DEEP_TOWER ["2. Nhánh Sâu: Deep Two-Tower Network (S_deep)"]
        UT["User Tower: Embedding Người dùng + Lịch sử + Chuẩn hóa L2"]
        IT["Item Tower: ID + SBERT Tiếng Việt + Giá + Chuẩn hóa L2"]
        DOT["Tích vô hướng Cosine: S_deep(u, i) = e_u · e_i"]
        U_IN --> UT
        I_IN --> IT
        UT --> DOT
        IT --> DOT
    end

    subgraph WIDE_RULE ["3. Nhánh Rộng: Wide Apriori Rule Scorer (S_wide)"]
        AR["Khai phá Luật Apriori từ Giao dịch Train (s_min=0.001, c_min=0.05)"]
        MC["Điểm số Luật: Max Confidence của các luật kích hoạt từ H_u"]
        U_IN --> AR
        AR --> MC
    end

    subgraph FUSION ["4. Cơ chế Hợp nhất Điểm Chuẩn hóa (Z-Score Fusion)"]
        NORM_DEEP["Chuẩn hóa Z-Score Điểm Sâu: Norm(S_deep)"]
        NORM_WIDE["Chuẩn hóa Z-Score Điểm Luật: Norm(S_wide)"]
        HYBRID["Điểm Hợp nhất: S_hybrid = Norm(S_deep) + w_wide * Norm(S_wide)"]
        DOT --> NORM_DEEP
        MC --> NORM_WIDE
        NORM_DEEP --> HYBRID
        NORM_WIDE --> HYBRID
    end

    subgraph OUTPUT ["5. Xếp hạng Toàn danh mục & Đánh giá"]
        RANK["Xếp hạng Top-10 trên Không gian Ứng viên C_u = I \\ H_u^seen"]
        HYBRID --> RANK
    end

    classDef default fill:#1e293b,stroke:#64748b,stroke-width:1.5px,color:#ffffff;
    classDef inputNode fill:#0c4a6e,stroke:#38bdf8,stroke-width:2px,color:#ffffff;
    classDef deepNode fill:#3b0764,stroke:#c084fc,stroke-width:2px,color:#ffffff;
    classDef wideNode fill:#78350f,stroke:#fbbf24,stroke-width:2px,color:#ffffff;
    classDef fusionNode fill:#064e3b,stroke:#4ade80,stroke-width:2px,color:#ffffff;
    classDef rankNode fill:#7f1d1d,stroke:#f87171,stroke-width:2px,color:#ffffff;

    class U_IN,I_IN inputNode;
    class UT,IT,DOT deepNode;
    class AR,MC wideNode;
    class NORM_DEEP,NORM_WIDE,HYBRID fusionNode;
    class RANK rankNode;
```

---

## 2. BA ĐÓNG GÓP KHOA HỌC CHÍNH

Về mặt đóng góp, bài báo giải quyết cuộc khủng hoảng tính tái lập trong Hệ gợi ý thông qua **3 trụ cột**:

1. **Trụ cột 1 — Thiết lập giao thức đánh giá nhận thức nguồn gốc khóa bằng mã băm SHA-256:**
   - Thiết lập giao thức đánh giá nhận thức nguồn gốc khóa bằng mã băm **SHA-256**.
   - Ràng buộc toàn bộ dữ liệu phân tách thời gian (Temporal Split), tập ứng viên toàn danh mục ($C_u = I \setminus H_u^{\mathrm{seen}}$), quy tắc che mặt nạ sản phẩm đã xem (Seen-item Masking), bộ giải quyết điểm hòa tất định (Deterministic Tie-breaking) và chuỗi seed ngẫu nhiên bằng chữ ký mật mã học.
   - Thiết kế **Bộ đánh giá độc lập dùng chung (Decoupled Shared Evaluator)** hoàn toàn tách rời khỏi mã nguồn huấn luyện mô hình nhằm triệt tiêu rò rỉ thông tin và thiên lệch triển khai.

2. **Trụ cột 2 — Phân tách rạch ròi không gian minh chứng công khai và bán lẻ:**
   - Phân tách rạch ròi không gian minh chứng công khai (**`PUBLIC_VALIDATION`** trên MovieLens 100K) và không gian bán lẻ (**`RETAIL_BENCHMARK`**).
   - **`PUBLIC_VALIDATION`**: Xác thực tính tất định và khả năng tái lập của đường ống trên MovieLens 100K thông qua thư viện đối chuẩn quốc tế RecBole 1.2.1 (ACM CIKM 2021).
   - **`RETAIL_BENCHMARK`**: Đánh giá đối chuẩn thực nghiệm chuyên sâu trên tập dữ liệu bán lẻ kiểm soát **VietRetail-Synth** (5.000 khách hàng, 5.200 SKU, 823.371 tương tác).

3. **Trụ cột 3 — Đề xuất kiến trúc mạng lai phân rã Wide-and-Deep Two-Tower Hybrid:**
   - Đề xuất kiến trúc mạng lai phân rã **Wide-and-Deep Two-Tower Hybrid** kết hợp giữa luật kết hợp Apriori (nhánh Wide ghi nhớ các cặp sản phẩm đồng giao dịch tần suất cao) và mạng tháp đôi tối ưu hóa qua BPR loss (nhánh Deep khái quát hóa quan hệ ngữ nghĩa tiềm ẩn với SBERT tiếng Việt và chiếu đặc trưng giá bán).
   - Trên tập bán lẻ VietRetail-Synth, mô hình của nhóm đạt **NDCG@10 = 0.1385** (**tăng vượt bậc +21.28%** so với đường cơ sở Two-Tower BPR đơn lẻ), **HR@10 = 0.2190** (**tăng +17.11%**), và **Macro GAUC = 0.7812** (**tăng +6.29%**), với mức ý nghĩa thống kê $p < 0.001$ qua kiểm định **Hierarchical Bootstrap** (2.000 lượt lấy mẫu lại).

---

## 3. BẢNG TỔNG HỢP KẾT QUẢ THỰC NGHIỆM ĐỐI CHUẨN

| Phương pháp / Mô hình | NDCG@10 | Hit Rate (HR@10) | Recall@10 | Macro GAUC | Bản chất cơ chế |
|:---|:---:|:---:|:---:|:---:|:---|
| **Popularity (MostPop)** | 0.0421 | 0.0812 | 0.0385 | 0.5412 | Thất bại do bị che giấu các món quen thuộc mua lặp lại |
| **Apriori (Rule Alone)** | 0.0784 | 0.1245 | 0.0692 | 0.6120 | Chính xác cao trên giỏ hàng thường gặp nhưng độ phủ hẹp (< 15%) |
| **Deep Two-Tower (BPR Alone)**| 0.1142 | 0.1870 | 0.1034 | 0.7350 | Khái quát hóa mạnh nhờ SBERT văn bản và chiếu đặc trưng |
| **Proposed Hybrid (Wide + Deep)**| **0.1385** | **0.2190** | **0.1256** | **0.7812** | **Cộng hưởng tối ưu giữa Memorization và Generalization** |
| *Mức tăng trưởng tương đối* | ***+21.28%*** | ***+17.11%*** | ***+21.47%*** | ***+6.29%*** | *Kiểm định Bootstrap 2.000 lần: p < 0.001* |

---

## 4. TÀI NGUYÊN VÀ CẤU TRÚC ĐIỀU HƯỚNG

Toàn bộ các tài liệu nghiên cứu chi tiết đã được tổ chức theo cấu trúc chuyên nghiệp:
* 📁 `overview/`: Báo cáo chi tiết cho Giảng viên hướng dẫn (`advisor-paper-report.md`) và Tóm tắt điều hành (`paper-executive-summary.md`).
* 📁 `intro-related-work/`: Báo cáo giải nghĩa chi tiết Section 1 & 2 với bản dịch sát nghĩa tiếng Việt song hành và 36 tài liệu tham khảo quốc tế (`deep-analysis-intro-related-work.md`).
* 📁 `methodology-results-conclusion/`: Báo cáo giải nghĩa chi tiết Section 3 đến 7 bao gồm công thức toán học, thiết kế phân vùng, kết quả thực nghiệm và thảo luận giới hạn (`deep-analysis-methodology-results-conclusion.md`).
* 📄 `paper.pdf`: Bản in 10 trang bài báo chuẩn IEEE.
* 📝 `paper.tex` & `refs.bib`: Mã nguồn LaTeX và tệp trích dẫn hoàn chỉnh.
