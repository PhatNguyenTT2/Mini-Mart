# KẾ HOẠCH NỘI DUNG NÂNG CẤP LUẬN VĂN (`main.tex`)
## TỪ BÁO CÁO ĐỒ ÁN 2 (SE122) LÊN KHÓA LUẬN TỐT NGHIỆP (SE505)
**Đề tài:** Phát triển Hệ thống Quản lý Bán lẻ Đa chi nhánh POSMART dựa trên Kiến trúc Microservices và Hệ Gợi ý Thông minh Lai (Hybrid Recommender)  
**Chuyên ngành:** Kỹ thuật Phần mềm — Trường Đại học Công nghệ Thông tin, ĐHQG-HCM  
**Giảng viên hướng dẫn:** TS. Nguyễn Thị Xuân Hương  
**Sinh viên thực hiện:** Nguyễn Trương Tiến Phát (23521148) & Đỗ Minh Đức (23520303)  
**Tài liệu tham chiếu:** 
- Paper Draft: `research/hybrid-recsys-v5/05_manuscript/stage2_write/03_draft/master_draft_stage2.tex`
- Template Khóa luận SE505: `thesis/22520664_SE505.Q21_Nguyen Thi Xuan Huong.pdf`
- Yêu cầu buổi họp đầu tiên: `thesis/target.md`

---

## I. TỔNG QUAN CHIẾN LƯỢC NÂNG CẤP NỘI DUNG

Báo cáo Đồ án 2 hiện tại (`main.tex` / `main.pdf` - 107 trang) đã có khung sườn kỹ thuật backend rất tốt (9 Microservices, Saga RabbitMQ, Row-Level Multi-tenancy, VNPay). Để nâng cấp lên **Khóa luận tốt nghiệp (SE505)** theo đúng định hướng của TS. Nguyễn Thị Xuân Hương và giải quyết triệt để 3 câu hỏi lớn trong buổi họp đầu tiên:

1. **Về Bài toán nghiên cứu & Đóng góp học thuật (Tham chiếu Paper Draft):** Tích hợp toàn bộ nền tảng toán học, mô hình đề xuất **Wide (Apriori Rules) + Deep Two-Tower (BPR Loss)** và **Quy trình Benchmark khoa học độc lập (Reproducible Protocol)** từ bản thảo nghiên cứu `master_draft_stage2.tex` vào Chương 2 và Chương 4. Khẳng định đề tài có định hướng công bố bài báo khoa học chuẩn hội nghị.
2. **Về Phạm vi Giao diện Frontend (Đầy đủ cả 3 phân hệ):** Khóa luận không chỉ có backend mà bao quát đầy đủ giải pháp thương mại toàn diện gồm:
   - **Giao diện Bán hàng tại quầy POS (POS Terminal):** Tối ưu cảm ứng, quét mã vạch, chọn lô, giữ đơn chờ (Hold order), thanh toán tiền mặt & VNPay QR động.
   - **Giao diện Quản trị chuỗi & cửa hàng (Admin & Manager Dashboard):** Quản trị 9 service, phân quyền RBAC, sơ đồ kho bãi, quản lý hạn dùng lô hàng, công nợ NCC và thống kê doanh thu thời gian thực (Redis Cache).
   - **Giao diện Khách hàng trực tuyến (Customer Storefront):** Mua sắm trực tuyến, theo dõi đơn hàng, tích hợp Trợ lý tác vụ hai chiều (**Action Assistant v2.0** với Confirmation Gate an toàn).
3. **Về Cấu trúc học thuật chuẩn mực:** Bổ sung Chương 1 theo đúng mẫu của TS. Nguyễn Thị Xuân Hương, đặc biệt là **Bảng 1.1: Ma trận phân tích 3 chiều** (Khoảng cách năng lực, Điểm nghẽn hệ thống, Nợ kỹ thuật & đánh đổi kiến trúc), Mục Yêu cầu dữ liệu, và định lượng hóa các chỉ số phi chức năng.

---

## II. CHI TIẾT NỘI DUNG CẦN CẬP NHẬT TRONG `main.tex` THEO TỪNG CHƯƠNG

### 1. PHẦN MỞ ĐẦU VÀ CÁC TRANG THỦ TỤC

* **Trang bìa 1 & Trang bìa phụ (Titlepage):**
  * Đổi tiêu đề lớn: `BÁO CÁO ĐỒ ÁN 2` $\rightarrow$ `KHÓA LUẬN TỐT NGHIỆP`.
  * Đổi mã môn học: `SE122.P21 - Đồ án 2` $\rightarrow$ `KỸ SƯ / CỬ NHÂN NGÀNH KỸ THUẬT PHẦN MỀM` (Mã học phần: `SE505.Q21`).
  * Tên đề tài hoàn chỉnh: **"PHÁT TRIỂN HỆ THỐNG QUẢN LÝ BÁN LẺ ĐA CHI NHÁNH DỰA TRÊN KIẾN TRÚC MICROSERVICES VÀ HỆ GỢI Ý THÔNG MINH LAI"** *(Tiếng Anh: Development of a Multi-branch Retail Management System based on Microservices Architecture and Hybrid Recommender)*.
  * Giữ nguyên thông tin GVHD: TS. Nguyễn Thị Xuân Hương; Nhóm SV: Nguyễn Trương Tiến Phát (23521148) & Đỗ Minh Đức (23520303).
* **Trang Thông tin Hội đồng chấm Khóa luận tốt nghiệp:** Bổ sung trang xác nhận của Hội đồng chấm theo đúng chuẩn mẫu UIT.
* **Trang Lời cảm ơn:** Giữ nguyên và cập nhật cảm ơn sâu sắc đến GVHD TS. Nguyễn Thị Xuân Hương và bộ môn Kỹ thuật Phần mềm.
* **Trang Tóm tắt Khóa luận (Tiếng Việt & English Abstract):**
  * *Tiếng Việt:* Cập nhật từ 8 Microservices lên **9 Microservices**, bổ sung hệ gợi ý lai **Wide & Deep Two-Tower (`ai-service-v2`)** và trợ lý tác vụ **Action Assistant v2.0**.
  * *Tiếng Anh (Abstract):* Tích hợp đoạn Abstract từ `master_draft_stage2.tex` làm nổi bật tính có thể tái lập (Reproducibility), đánh giá danh mục đầy đủ (Full-catalog evaluation) và cơ chế bù trừ SAGA.
* **Danh mục Từ viết tắt (Acronyms):** Bổ sung đầy đủ các thuật ngữ:
  * *BPR:* Bayesian Personalized Ranking.
  * *NDCG@K:* Normalized Discounted Cumulative Gain at rank K.
  * *HR@K:* Hit Ratio at rank K.
  * *GAUC:* Group Area Under Curve.
  * *HNSW:* Hierarchical Navigable Small World (Chỉ mục vector).
  * *RRF:* Reciprocal Rank Fusion.
  * *RLS:* Row-Level Security.
  * *SAGA:* Mô hình điều phối giao dịch phân tán.
  * *IPN:* Instant Payment Notification (VNPay Webhook).
  * *TOTP:* Time-Based One-Time Password (Bảo mật 2FA).

---

### 2. CHƯƠNG 1: TỔNG QUAN ĐỀ TÀI (TÁI CẤU TRÚC HOÀN TOÀN)

Thay thế Chương 1 cũ (8 mục rời rạc) bằng 4 mục lớn chuẩn mực theo template KLTN UIT:

#### 1.1. Động lực nghiên cứu và lý do chọn đề tài
* **Bối cảnh vĩ mô:** Sự chuyển dịch từ bán lẻ đơn kênh sang bán lẻ đa kênh tích hợp (Omnichannel). Nhu cầu xử lý đồng bộ giữa quầy thanh toán trực tiếp (POS) và kênh trực tuyến (Storefront).
* **Thách thức hệ thống phân tán:** Bài toán tải đọc (Read-heavy Catalog) đối lập tải ghi (Write-heavy Inventory/Order); rủi ro nghẽn cổ chai và sập hệ thống (SPOF) của kiến trúc nguyên khối Monolith.
* **Động lực kế thừa và nâng cấp từ Đồ án 2:** Đồ án 2 đã làm chủ hạ tầng Backend 9 Microservices và SAGA RabbitMQ. Khóa luận tốt nghiệp mở rộng giải quyết 2 bài toán lớn:
  1. Xây dựng Trợ lý ảo tác vụ hai chiều (**Action Assistant v2.0**) cho phép can thiệp trực tiếp trạng thái ứng dụng một cách an toàn.
  2. Nghiên cứu và hiện thực hóa mô hình gợi ý thông minh lai (**`ai-service-v2`**) kết hợp Wide (Apriori) và Deep Two-Tower (BPR loss) với quy trình benchmark khoa học, khách quan, không rò rỉ dữ liệu.

#### 1.2. Khảo sát hiện trạng và Hệ thống đề xuất
* **1.2.1. Hiện trạng các nền tảng thương mại điện tử & bán lẻ:** Khảo sát đối chiếu 3 nhóm: SaaS nội địa (KiotViet, Sapo), Mã nguồn mở (WooCommerce, Odoo POS), Nền tảng Cloud quốc tế (Shopify Plus).
* **1.2.2. Phân tích các hạn chế kỹ thuật phổ biến:** Nêu rõ các nút thắt: Bottleneck cơ sở dữ liệu khi chạy báo cáo thống kê; xung đột tồn kho (Overselling); và nợ kỹ thuật khi phụ thuộc vào API AI thương mại của bên thứ ba.
* **1.2.3. Ma trận phân tích khoảng cách năng lực, điểm nghẽn kiến trúc và nợ kỹ thuật (BẢNG 1.1):**
  * Đưa trọn vẹn **Bảng 1.1** (đã xây dựng trong `preliminary-survey-report.md`) vào `main.tex`. Đây là bảng phân tích 3 chiều (Capability Gap, Bottlenecks, Technical Debt) được đánh giá rất cao trong các hội đồng bảo vệ của TS. Nguyễn Thị Xuân Hương.
* **1.2.4. Hệ thống kiến trúc đề xuất (POSMART):** Trình bày giải pháp tổng thể: 9 Microservices + Nginx Gateway + RabbitMQ SAGA + Row-Level Multi-tenancy + Hệ gợi ý lai độc lập nội bộ `ai-service-v2`.

#### 1.3. Đối tượng và Phạm vi nghiên cứu
* **1.3.1. Đối tượng nghiên cứu:** Kiến trúc phân tán (Microservices, Saga Choreography/Orchestration, Transactional Outbox, Idempotency Guard), Quản trị dữ liệu đa người thuê (Row-Level Security qua `store_id`), Trợ lý tác vụ (RAG Pipeline, Action Response Protocol, Confirmation Gate), và Mô hình toán học Hệ gợi ý lai (Apriori, Deep Two-Tower với BPR Loss, Additive Z-score Fusion).
* **1.3.2. Phạm vi nghiên cứu:** Chuỗi siêu thị mini quy mô dưới 100 cửa hàng; 9 dịch vụ Backend và Recommender Runner `ai-service-v2`; môi trường Docker Compose và Cloud (Supabase PostgreSQL, CloudAMQP, Redis Cloud); Sandbox VNPay. (Loại trừ bài toán logistics xe tải vận chuyển hàng ngoài thực địa).

#### 1.4. Mục tiêu đề tài và Các yêu cầu hệ thống
* **1.4.1. Yêu cầu chức năng hệ thống:** Phân rã chi tiết theo 4 nhóm tác nhân:
  * *Khách hàng (Customer):* Khám phá sản phẩm, giỏ hàng, thanh toán VNPay/COD, theo dõi đơn hàng, tương tác AI Chatbot gợi ý & thêm giỏ hàng.
  * *Thu ngân (Cashier):* Đăng nhập nhanh mã PIN (Bcrypt), quét mã vạch bán hàng POS, lưu/phục hồi đơn hàng chờ (Hold orders), thanh toán đa phương thức.
  * *Quản lý cửa hàng (Store Manager):* Quản lý nhập hàng (PO), nghiệm thu nhập kho theo vị trí kệ, quản lý lô hàng & hạn dùng, điều chuyển hàng lên kệ, hủy hàng hỏng, theo dõi công nợ nhà cung cấp.
  * *Quản trị viên cấp cao (Super Admin):* Quản lý chi nhánh (`store_id`), danh mục sản phẩm tập trung, phân quyền RBAC, cấu hình khuyến mãi tự động ban đêm.
* **1.4.2. Yêu cầu dữ liệu:** 5 trụ cột: (1) Tính nhất quán giao dịch (ACID cục bộ, Eventual Consistency qua SAGA); (2) Cô lập dữ liệu đa người thuê (Row-Level Security); (3) Linh hoạt bán cấu trúc (JSONB settings & audit); (4) Lưu trữ vector & ngữ nghĩa (`pgvector` HNSW 768d + GIN); (5) Bất biến dữ liệu nghiên cứu (Dataset Snapshot v5.1 hash SHA-256).
* **1.4.3. Yêu cầu giao diện, phần cứng, phần mềm:**
  * Giao diện: Responsive Web, chuẩn Core Web Vitals, tối ưu cảm ứng và phím tắt cho POS, widget AI nổi.
  * Phần mềm: Node.js 20 LTS, Python 3.11, PostgreSQL 16, Redis 7, RabbitMQ 3.13, Nginx Alpine, Docker Compose.
  * Phần cứng: Workstation RAM $\ge$ 16GB, CPU 6 cores; Staging Cloud VPS 4 vCPU, 8-16GB RAM.
* **1.4.4. Yêu cầu phi chức năng:** P95 API < 200ms; P95 RAG AI < 500ms; tra cứu Apriori $O(1)$ (< 5ms); Redis cache hit rate > 85%; bảo mật 3 tầng Rate Limit, POS PIN bcrypt, VNPay HMAC-SHA512; cô lập lỗi (Fault Isolation).

---

### 3. CHƯƠNG 2: CƠ SỞ LÝ THUYẾT (TÍCH HỢP NỀN TẢNG TỪ PAPER DRAFT)

Cập nhật và bổ sung sâu các cơ sở khoa học máy tính:
* **2.1. Công nghệ nền tảng Backend:** Giữ nguyên và chuẩn hóa các mục: Node.js, Express.js, PostgreSQL 16 & pgvector, RabbitMQ (AMQP 0-9-1), Redis In-memory Caching, Nginx API Gateway, Docker & Docker Compose. Bổ sung giải thích thư viện `pino` (Structured logging) và SAGA Pattern.
* **2.2. Cơ sở lý thuyết Hệ gợi ý thông minh (Nâng cấp đột phá từ Paper Draft):**
  * *Bài toán xếp hạng danh mục đầy đủ (Full-catalog Ranking Problem):* Thiết lập không gian ứng viên $C_u = I \setminus H_u^{\text{seen}}$, loại bỏ bias của phương pháp lấy mẫu (Sampled metrics).
  * *Thuật toán Khai phá luật kết hợp Apriori (Wide Component):* Định nghĩa toán học về Support, Confidence, và Lift trên các giỏ hàng mua sắm tự nhiên (organic training baskets). Phân tích vì sao Lift là tiêu chí quyết định.
  * *Mạng nơ-ron Deep Two-Tower Recommender (Deep Component):* 
    * User Tower: Biểu diễn người dùng qua User Embedding kết hợp History Embedding tích lũy.
    * Item Tower: Chiếu đặc trưng văn bản, danh mục và giá sản phẩm thông qua tầng Content Projection.
    * Hàm mất mát xếp hạng Bayesian Personalized Ranking (BPR Loss): Tối ưu hóa xác suất ưu tiên sản phẩm tích cực so với sản phẩm âm tính:
      $$\mathcal{L}_{\text{BPR}} = - \sum_{(u, i, j) \in \mathcal{D}} \ln \sigma(\hat{x}_{ui} - \hat{x}_{uj}) + \frac{\lambda_{\Theta}}{2} \|\Theta\|^2$$
  * *Mô hình kết hợp lai (Additive Hybrid Fusion):* 
    * Chuẩn hóa điểm số theo từng người dùng (Per-user Z-score Normalization):
      $$\text{Norm}(S) = \frac{S - \mu_u}{\sigma_u}$$
    * Công thức kết hợp tổng quát:
      $$S_{\text{hybrid}}(u, i) = \text{Norm}(S_{\text{deep}}(u, i)) + w_{\text{wide}} \cdot \text{Norm}(S_{\text{wide}}(u, i))$$
  * *Kỹ thuật RAG & Hợp nhất thứ hạng RRF (Content-Based):* Vietnamese SBERT 768 chiều, Cosine Similarity HNSW kết hợp GIN Full-Text Search qua Reciprocal Rank Fusion ($k=60$).
* **2.3. Cơ sở lý thuyết về Trợ lý ảo tác vụ (Action Assistant v2.0):**
  * Cơ chế Intent Classification phân tầng (Regex -> Implicit Keyword -> Smart Fallback).
  * Giao thức Action Response Protocol (Định dạng phản hồi hành động có cấu trúc: Action Payload, Parameters, Confirmation Requirement).
  * Mô hình bảo mật 7 lớp và chốt chặn xác nhận (Confirmation Gate) đảm bảo an toàn khi AI can thiệp vào nghiệp vụ bán hàng.

---

### 4. CHƯƠNG 3: PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG (BAO QUÁT ĐẦY ĐỦ 3 GIAO DIỆN)

* **3.1. Kiến trúc phân rã 9 Microservices:**
  * Bổ sung dịch vụ thứ 9: **Statistics Service (Port 3009)** vào sơ đồ tổng thể và bảng danh mục cổng service.
  * Làm rõ luồng giao tiếp Event-Driven SAGA Choreography giữa Payment (:3007), Order (:3003), Inventory (:3006), Supplier (:3005) qua RabbitMQ Topic Exchange `posmart.events`.
  * Trình bày chi tiết mẫu thiết kế **Transactional Outbox** và bảng **`processed_events`** (Idempotency Guard).
* **3.2. Thiết kế Cơ sở dữ liệu phân tán (Database Design):**
  * Chuẩn hóa 8 Logical Databases trên PostgreSQL (Auth, Catalog, Order, Settings, Supplier, Inventory, Payment, Chatbot) và Redis Cache.
  * Bổ sung các trường chuyên dụng cho nghiên cứu học máy trong bảng `sale_order`: `benchmark_run_id`, `benchmark_kind`, `benchmark_template_id`.
  * Đặc tả chi tiết bảng `product_knowledge_base` lưu trữ vector 768 chiều (`VECTOR(768)`) với chỉ mục HNSW và cột FTS với chỉ mục GIN.
* **3.3. Đặc tả Use Case chi tiết:**
  * Gom nhóm và đánh số use case theo 4 tác nhân: UC-CUST-* (Khách hàng), UC-POS-* (Thu ngân), UC-MGR-* (Quản lý kho), UC-ADM-* (Quản trị hệ thống).
  * Bổ sung đầy đủ use case: Bán hàng quét mã vạch, Giữ đơn chờ tại POS (Hold orders), Nhập kho theo vị trí kệ, Quản lý công nợ NCC, Tự động kích hoạt khuyến mãi ban đêm, và AI Action Execution.
* **3.4. Thiết kế Giao diện người dùng (BAO GỒM ĐẦY ĐỦ CẢ 3 PHÂN HỆ):**
  * **Phân hệ 1: Giao diện Bán hàng tại quầy POS (POS Cashier Terminal - 6 màn hình):**
    1. UI-POS-01: Màn hình Đăng nhập nhanh bằng mã PIN số lớn.
    2. UI-POS-02: Màn hình Bán hàng chính (Lưới sản phẩm + Quét mã vạch + Giỏ hàng quầy).
    3. UI-POS-03: Modal Quản lý và phục hồi đơn hàng chờ (Hold Orders).
    4. UI-POS-04: Màn hình Thanh toán đa phương thức (Tiền mặt, tính tiền thừa tự động).
    5. UI-POS-05: Màn hình Thanh toán VNPay QR Code động.
    6. UI-POS-06: Mẫu Hóa đơn bán lẻ in nhiệt (Thermal Receipt).
  * **Phân hệ 2: Giao diện Quản trị chuỗi & Cửa hàng (Admin & Manager Dashboard - 16 màn hình):**
    1. UI-ADM-01: Tổng quan Dashboard Super Admin (Chỉ số toàn chuỗi, biểu đồ doanh thu).
    2. UI-ADM-02: Quản lý Danh sách chi nhánh cửa hàng (`store_id`).
    3. UI-ADM-03: Quản lý Người dùng và Tài khoản nhân viên.
    4. UI-ADM-04: Quản lý Phân quyền và Vai trò (RBAC Permissions).
    5. UI-ADM-05: Cấu hình hệ thống (Bảo mật PIN, Chiết khấu VIP, Khuyến mãi ban đêm).
    6. UI-ADM-06: Dashboard Quản lý cửa hàng (Manager Overview).
    7. UI-ADM-07: Quản lý Danh mục hàng hóa tập trung (Catalog Categories).
    8. UI-ADM-08: Quản lý Danh sách sản phẩm và Biến động giá (Price History).
    9. UI-ADM-09: Quản lý Nhà cung cấp và Hạn mức công nợ (Supplier Debt).
    10. UI-ADM-10: Quản lý Đơn nhập hàng từ nhà cung cấp (Purchase Orders).
    11. UI-ADM-11: Giao diện Nghiệm thu nhập kho và Gán vị trí kệ (Receive Stock).
    12. UI-ADM-12: Tổng quan Quản lý tồn kho theo lô (Inventory & Batch Management).
    13. UI-ADM-13: Sơ đồ trực quan kho bãi và kệ hàng (Warehouse Map & Locations).
    14. UI-ADM-14: Quản lý Phiếu xuất kho hủy hàng / hao hụt (Stock Out).
    15. UI-ADM-15: Quản lý Hồ sơ khách hàng và Lịch sử chi tiêu.
    16. UI-ADM-16: Báo cáo Thống kê doanh thu, chi phí và lợi nhuận gộp (Redis Caching).
  * **Phân hệ 3: Giao diện Khách hàng trực tuyến (Customer Storefront - 8 màn hình):**
    1. UI-CUST-01: Trang chủ Storefront (Hero banner, danh mục ngành hàng, sản phẩm nổi bật).
    2. UI-CUST-02: Danh sách sản phẩm với bộ lọc đa tiêu chí (Debounce Search & Filters).
    3. UI-CUST-03: Chi tiết sản phẩm, bảng thông số và gợi ý mua kèm (Apriori).
    4. UI-CUST-04: Giỏ hàng trực tuyến và áp dụng mã giảm giá.
    5. UI-CUST-05: Quy trình Thanh toán trực tuyến (Địa chỉ, hình thức nhận hàng).
    6. UI-CUST-06: Thanh toán VNPay Sandbox trực tuyến.
    7. UI-CUST-07: Lịch sử đơn hàng và Tiến trình giao hàng cá nhân.
    8. UI-CUST-08: Giao diện Trợ lý ảo AI Chatbot (Floating Widget, thẻ sản phẩm, nút xác nhận hành động).

---

### 5. CHƯƠNG 4: XÂY DỰNG ỨNG DỤNG VÀ KIỂM THỬ CHƯƠNG TRÌNH

* **4.1. Tổ chức thư mục mã nguồn:** Trình bày cấu trúc Monorepo chuẩn hóa gồm: `backend/services/` (9 dịch vụ Node.js), `backend/gateway/` (Nginx), `backend/shared/`, và thư mục nghiên cứu độc lập `ai-service-v2/` (Python runner).
* **4.2. Kiểm thử Chức năng (Functional Testing):**
  * Kiểm thử luồng SAGA thanh toán và trừ kho (Testcase SAGA-01: Thanh toán thành công -> Trừ kho; Testcase SAGA-02: Trừ kho lỗi -> Kích hoạt đền bù Rollback đơn hàng).
  * Kiểm thử phân quyền RBAC và xác thực mã PIN POS (Testcase PIN-01: Đăng nhập thành công; Testcase PIN-02: Khóa tài khoản sau 5 lần sai).
  * Kiểm thử Webhook VNPay IPN (Xác thực chữ ký số hợp lệ và chặn đứng giả mạo).
  * Kiểm thử Action Assistant v2.0 (Kiểm thử phân tích intent và thực thi hành động qua Confirmation Gate).
* **4.3. Kiểm thử Phi chức năng & Hiệu năng hệ thống (Non-functional Testing):**
  * Đo lường thời gian phản hồi API qua Nginx: Xác nhận P95 < 200ms.
  * Đo lường hiệu suất truy vấn Vector HNSW: So sánh với Brute-force ($O(\log n)$ vs $O(n)$).
  * Kiểm thử sức chịu tải và Cache Hit Rate của Redis trên Statistics Service (Đạt > 85%).
* **4.4. ĐÓNG GÓP MỚI: Kết quả Thực nghiệm & Benchmark Hệ gợi ý lai (Từ `master_draft_stage2.tex`):**
  * Trình bày quy trình kiểm thử khoa học độc lập: Dataset Snapshot v5.1 bất biến, phân tách thời gian (Train: Jan-Jun 2026, Val: Jun-Jul 2026, Test: Jul-Aug 2026).
  * Báo cáo kết quả trên làn kiểm chứng công khai (Public Protocol Lane - MovieLens 100K qua RecBole 1.2.1 với Pop và BPR).
  * Đánh giá so sánh các biến thể kiến trúc: Popularity Baseline, Pure Rule-based (Apriori), Deep Two-Tower (BPR), và Proposed Hybrid Recommender trên bộ chỉ số toàn diện (NDCG@10, HR@10, Recall@10, GAUC, Item-Cold Coverage).

---

### 6. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN

* **Kết luận khoa học:** 
  1. Đã giải quyết triệt để bài toán kiến trúc phân tán cho chuỗi bán lẻ bằng 9 Microservices, đảm bảo toàn vẹn giao dịch qua Saga Choreography và tối ưu chi phí qua Row-Level Multi-tenancy.
  2. Hiện thực hóa thành công mô hình Trợ lý tác vụ hai chiều (Action Assistant v2.0) giúp AI tương tác trực tiếp với nghiệp vụ bán lẻ mà vẫn đảm bảo tính an toàn và trạng thái Stateless.
  3. Xây dựng và kiểm chứng độc lập mô hình gợi ý lai Wide & Deep Two-Tower với quy trình benchmark minh bạch, có thể tái lập.
* **Hướng phát triển:**
  1. Hoàn thiện thủ tục phản biện và gửi công bố bài báo khoa học về phương pháp Hybrid Recommender và Reproducible Benchmark tại Hội nghị chuyên ngành (như SoICT, KSE, hoặc IEEE/ACM RecSys workshop) dưới sự hướng dẫn của TS. Nguyễn Thị Xuân Hương.
  2. Nâng cấp mô hình từ Edge Two-Tower sang Graph Neural Networks (LightGCN) khi dữ liệu tương tác đồ thị người dùng - sản phẩm đủ lớn.
  3. Triển khai mở rộng ứng dụng di động đa nền tảng (Mobile App React Native) cho khách hàng và nhân viên quét mã vạch kiểm kho di động.

---

### 7. TÀI LIỆU THAM KHẢO (BIBLIOGRAPHY)

Đồng bộ toàn bộ danh mục tài liệu tham khảo theo chuẩn IEEE, kết hợp các tài liệu giáo trình UIT với các bài báo khoa học đỉnh cao trích xuất từ `master_draft_stage2.tex`:
1. *Covington, P., Adams, J., & Sargin, E. (2016).* Deep neural networks for YouTube recommendations. *ACM RecSys*.
2. *Cheng, H. T., et al. (2016).* Wide & deep learning for recommender systems. *ACM DLRS*.
3. *Rendle, S., et al. (2009).* BPR: Bayesian personalized ranking from implicit feedback. *UAI*.
4. *Agrawal, R., & Srikant, R. (1994).* Fast algorithms for mining association rules. *VLDB*.
5. *Sarwar, B., et al. (2001).* Item-based collaborative filtering recommendation algorithms. *WWW*.
6. *Cormack, G. V., et al. (2009).* Reciprocal rank fusion out-performs evaluation measures. *ACM SIGIR*.
7. *Gusak, J., et al. (2025).* Temporal evaluation protocols for sequential recommendation.
8. *Petrov, A., & Macdonald, C. (2022).* A systematic review and replicability study of BERT4Rec. *ACM RecSys*.
9. *Kleppmann, M. (2022).* Designing Data-Intensive Applications. *O'Reilly Media*.
10. *Giáo trình Phân tích Thiết kế Hệ thống Thông tin & Kiến trúc Phần mềm — ĐH Công nghệ Thông tin (UIT).*
