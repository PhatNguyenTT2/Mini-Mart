# BÁO CÁO CHI TIẾT THẢO LUẬN BUỔI HỌP ĐẦU TIÊN VỚI GIẢNG VIÊN HƯỚNG DẪN
## ĐỀ TÀI: PHÁT TRIỂN HỆ THỐNG QUẢN LÝ BÁN LẺ ĐA CHI NHÁNH POSMART DỰA TRÊN KIẾN TRÚC MICROSERVICES VÀ HỆ GỢI Ý THÔNG MINH LAI

## NỘI DUNG 1: ĐỘNG LỰC NGHIÊN CỨU VÀ LÝ DO CHỌN ĐỀ TÀI

### 1.1. Bối cảnh và Tính cấp thiết của đề tài
* **Chuyển dịch Omnichannel:** Sự kết hợp giữa mua sắm tại cửa hàng tiện lợi và mua sắm trực tuyến (BOPIS - Buy Online, Pick Up In Store) đòi hỏi hệ thống quản lý bán lẻ phải vận hành tức thời theo thời gian thực (Real-time).
* **Nút thắt của kiến trúc nguyên khối (Monolith):** Các hệ thống POS bán lẻ truyền thống khi tích hợp luồng trực tuyến thường gặp xung đột gay gắt: luồng tra cứu danh mục hàng hóa đọc rất nhiều (*Read-heavy*), trong khi luồng ghi biến động tồn kho và thanh toán hóa đơn ghi liên tục (*Write-heavy*). Việc dùng chung một CSDL duy nhất gây khóa bảng, nghẽn cổ chai I/O và có nguy cơ sập toàn bộ các máy bán hàng tại quầy (Single Point of Failure - SPOF).
* **Bài toán chi phí Multi-tenancy:** Cấp phát mỗi chi nhánh một cơ sở dữ liệu vật lý riêng gây lãng phí tài nguyên máy chủ đối với chuỗi vừa và nhỏ (< 100 cửa hàng). Yêu cầu đặt ra là phải chia sẻ cơ sở dữ liệu nhưng cô lập dữ liệu tuyệt đối ở mức dòng (**Row-Level Security** qua `store_id`).

### 1.2. Động lực nâng cấp thuyết phục: Kế thừa từ Đồ án 2 lên Khóa luận tốt nghiệp
* **Nền tảng đã đạt được ở Đồ án 2:** Nhóm đã hoàn thành và vận hành ổn định hệ thống Backend phân tán gồm **9 Microservices** (Auth, Catalog, Order, Settings, Supplier, Inventory, Payment, Chatbot, Statistics), xây dựng luồng SAGA thanh toán và trừ kho an toàn qua RabbitMQ, tích hợp cổng VNPay Sandbox và cơ chế Multi-tenancy RLS.
* **Bài toán mới mang hàm lượng khoa học cao trong Khóa luận tốt nghiệp:**
  1. **Nâng cấp Trợ lý tác vụ hai chiều (Action Assistant v2.0):** Vượt qua mô hình Chatbot hỏi đáp chỉ đọc (Read-only RAG) thông thường, hệ thống trang bị giao thức **Action Response Protocol** và chốt chặn xác nhận **Confirmation Gate** 7 lớp, cho phép AI thực thi các hành động cụ thể trên giao diện (thêm hàng vào giỏ, tra cứu kho chi nhánh, lưu đơn chờ tại quầy) mà vẫn bảo đảm Backend Stateless và an toàn tuyệt đối.
  2. **Mũi nhọn nghiên cứu Hệ gợi ý thông minh lai (`ai-service-v2`):** Khắc phục các hạn chế của mô hình heuristic cũ, nhóm đã phát triển một Recommender Research Runner độc lập kết hợp giữa **Wide Tower** (Khai phá luật kết hợp Apriori trên giỏ hàng mua sắm tự nhiên) và **Deep Two-Tower** (Mạng nơ-ron tháp đôi tích hợp chiếu đặc trưng văn bản, danh mục, giá bán và tối ưu qua hàm mất mát **Bayesian Personalized Ranking - BPR Loss**).
  3. **Định hướng xuất bản bài báo khoa học (Tham khảo Paper Draft):** Nhóm đã chuẩn bị sẵn bản thảo bài báo hoàn chỉnh `master_draft_stage2.tex` (*"Reproducible Hybrid Recommendation for Vietnamese Retail"*), cam kết một quy trình benchmark minh bạch, có khả năng tái lập (Reproducible Protocol), đánh giá xếp hạng trên toàn bộ danh mục hàng hóa (*Full-catalog ranking* $C_u = I \setminus H_u^{\text{seen}}$).

📌 **Tham chiếu vị trí trong `main.tex`:**
* Hiện tại `main.tex` (dòng 137–154) chỉ viết vắn tắt 4 gạch đầu dòng về lý do kỹ thuật đồ án 2.
* *Kế hoạch cập nhật ở phase sau:* Mở rộng thành mục `1.1 Động lực nghiên cứu và lý do chọn đề tài` theo chuẩn Khóa luận, làm nổi bật 2 mũi nhọn nghiên cứu mới (Action Assistant v2.0 & Hệ gợi ý lai Two-Tower).

---

## NỘI DUNG 2: KHẢO SÁT HIỆN TRẠNG VÀ HỆ THỐNG ĐỀ XUẤT

### 2.1. Khảo sát các nền tảng tương đương hiện có
1. **Nền tảng đóng gói SaaS nội địa (KiotViet, Sapo, Haravan):** Phù hợp hộ kinh doanh nhỏ, nhưng kiến trúc đóng kín, không có API mở phân tán, thiếu vắng mô hình AI học máy sâu và trợ lý tương tác hành động.
2. **Nền tảng mã nguồn mở (WooCommerce, Magento, Odoo POS):** Chi phí hạ tầng cao, dễ nghẽn cổ chai database quan hệ MySQL khi dữ liệu tăng lớn; Odoo viết bằng Python đồng bộ khó phân rã co giãn vi dịch vụ.
3. **Nền tảng Cloud quốc tế (Shopify Plus):** Chịu tải tốt nhưng chi phí cực kỳ đắt đỏ, không thể tùy biến sâu các nghiệp vụ sơ đồ kho chi tiết theo vị trí kệ (Location/Block) và luồng điều chuyển nội bộ giữa các chi nhánh.

### 2.2. BẢNG 1.1: MA TRẬN PHÂN TÍCH KHOẢNG CÁCH NĂNG LỰC, ĐIỂM NGHẼN KIẾN TRÚC VÀ NỢ KỸ THUẬT
*(Được thiết kế tuân thủ cấu trúc 3 chiều đặc trưng của TS. Nguyễn Thị Xuân Hương)*

| Tiêu chí phân tích (Ma trận tư duy) | Biểu hiện thực tế & Nguyên nhân kỹ thuật | Hệ quả & Điểm nghẽn hệ thống |
|:---|:---|:---|
| **1. Khoảng cách năng lực và Ràng buộc hệ thống (Capability Gap)** | • Các giải pháp POS SaaS đóng gói sẵn chỉ cung cấp các thao tác CRUD truyền thống, không có cơ chế xử lý ngôn ngữ tự nhiên.\newline • Hoàn toàn thiếu hụt mô hình học máy gợi ý sản phẩm cá nhân hóa sâu theo hành vi thời gian thực.\newline • Tìm kiếm sản phẩm phụ thuộc vào chuỗi từ khóa chính xác (Exact match), không xử lý được lỗi chính tả hay ngữ nghĩa tương đương. | • Bỏ lỡ cơ hội bán chéo sản phẩm (Cross-selling) để gia tăng giá trị giỏ hàng.\newline • Nhân viên thu ngân mất nhiều thời gian tìm kiếm mặt hàng thay thế khi một mã hàng bị hết.\newline • Trải nghiệm mua sắm của khách hàng trực tuyến bị gián đoạn, tỷ lệ chuyển đổi đơn hàng suy giảm. |
| **2. Điểm nghẽn hệ thống và Nguồn gốc vấn đề (Architectural Bottlenecks)** | • Bắt nguồn từ bản chất thiết kế nguyên khối (Monolithic Architecture) chia sẻ chung một cơ sở dữ liệu quan hệ vật lý.\newline • Khi lưu lượng truy cập online tăng đột biến, tài nguyên CPU/RAM của database bị quá tải do các truy vấn JOIN phức tạp.\newline • Chiến lược Multi-tenancy nếu triển khai theo dạng Database-per-tenant gây lãng phí tài nguyên và cạn kiệt Connection Pooling. | • Sự cố nghẽn cổ chai tại phân hệ báo cáo làm tê liệt toàn bộ luồng bán hàng tại máy POS của các chi nhánh (Single Point of Failure).\newline • Chi phí thuê máy chủ tăng cao đột biến nhưng hiệu suất phục vụ không tăng tương xứng. |
| **3. Nợ kỹ thuật và Sự đánh đổi kiến trúc (Technical Debt)** | • Trong nỗ lực tích hợp AI, các hệ thống thường phụ thuộc hoàn toàn vào việc gọi API đám mây thương mại (OpenAI, Anthropic).\newline • Bỏ qua tính tự chủ hạ tầng, độ trễ đường truyền mạng và sự kiểm soát mã nguồn.\newline • Thiếu vắng hệ thống kiểm thử tự động phân tầng (Unit/Integration Test) và cơ chế đền bù giao dịch phân tán (Saga Compensation). | • Rủi ro chi phí vận hành biến đổi tăng mất kiểm soát theo số lượt request.\newline • Độ trễ Chatbot lớn (> 2s), gây gián đoạn luồng tư vấn tại quầy.\newline • Nguy cơ rò rỉ dữ liệu mật về giá vốn, nhà cung cấp và lịch sử mua sắm của khách hàng ra bên ngoài. |

### 2.3. Hệ thống đề xuất: Nền tảng POSMART Enterprise
Đề tài đề xuất giải pháp **POSMART**:
* **Kiến trúc 9 Microservices độc lập:** Auth (:3001), Catalog (:3002), Order (:3003), Settings (:3004), Supplier (:3005), Inventory (:3006), Payment (:3007), Chatbot (:3008), và Statistics (:3009).
* **Nginx API Gateway (:8080):** Kiểm soát định tuyến, CORS, GZIP, Request tracing ($X\text{-Request-ID}$) và Rate Limiting 3 vùng (`strict`, `standard`, `ws_conn`).
* **Saga Choreography + RabbitMQ (`posmart.events`):** Đảm bảo tính toàn vẹn giao dịch tài chính và kho qua Transactional Outbox và Idempotency Guard.
* **Hệ gợi ý thông minh lai (`ai-service-v2`):** Kết hợp Wide Apriori và Deep Two-Tower (BPR Loss) với chuẩn hóa Z-score theo từng người dùng.

📌 **Tham chiếu vị trí trong `main.tex`:**
* Trong `main.tex` hiện tại, mục 2.1 (dòng 218–219) mang tiêu đề *"Những ứng dụng có liên quan đến đề tài"* nhưng **hoàn toàn để trống**.
* *Kế hoạch cập nhật ở phase sau:* Bổ sung toàn bộ mục 1.2 vào Chương 1 với **Bảng 1.1** hoàn chỉnh; đồng thời điền nội dung học thuật cho mục 2.1 ở Chương 2 (các công trình kinh điển: Two-Tower Covington 2016, Wide & Deep Cheng 2016, BPR Rendle 2009, Apriori Agrawal 1994, BERT4Rec Petrov 2022).

---

## NỘI DUNG 3: ĐỐI TƯỢNG VÀ PHẠM VI NGHIÊN CỨU

### 3.1. Đối tượng nghiên cứu
1. **Kiến trúc phân tán:** Microservices, API Gateway Pattern, Event-Driven Architecture (RabbitMQ AMQP 0-9-1), Saga Choreography, Transactional Outbox, Idempotent Consumer.
2. **Quản trị dữ liệu đa người thuê:** Row-Level Security trên PostgreSQL 16; Polyglot Persistence (PostgreSQL ACID, Redis In-memory Caching, pgvector HNSW).
3. **Trợ lý tác vụ đàm thoại:** RAG Pipeline (Vietnamese SBERT 768 chiều, chỉ mục HNSW) kết hợp GIN Full-Text Search qua RRF ($k=60$); Action Response Protocol và Confirmation Gate 7 lớp.
4. **Hệ gợi ý thông minh lai:** Thuật toán Apriori; Mạng nơ-ron Deep Two-Tower tối ưu hóa bằng Bayesian Personalized Ranking (BPR Loss); Additive Fusion với chuẩn hóa Z-score per-user.

### 3.2. Phạm vi nghiên cứu
* **Quy mô:** Chuỗi bán lẻ, siêu thị mini dưới 100 cửa hàng chi nhánh.
* **Phân hệ trong phạm vi:** 
  * 9 Microservices Backend hoàn chỉnh (bao gồm Statistics Service cổng 3009).
  * Phân hệ nghiên cứu thực nghiệm học máy `ai-service-v2` độc lập trên Python.
  * Đầy đủ cả 3 phân hệ giao diện: POS Terminal tại quầy, Admin & Manager Dashboard, và Customer Storefront.
* **Ranh giới loại trừ:** Không giải quyết bài toán logistics đội xe tải vận chuyển hàng ngoài thực địa; phân hệ `ai-service` cũ chỉ giữ lưu trữ đối soát (quarantined audit).
* **Tích hợp bên thứ ba:** Cổng thanh toán điện tử VNPay Sandbox; Hugging Face Inference API cho LLM.

📌 **Tham chiếu vị trí trong `main.tex`:**
* Trong `main.tex` dòng 165–183: Mục 1.4 "Phạm vi thực hiện" và mục 1.5 "Đối tượng sử dụng" bị nhầm lẫn giữa Tác nhân sử dụng (Actors) và Đối tượng nghiên cứu (Research Objects).
* *Kế hoạch cập nhật ở phase sau:* Tách bạch chuẩn hóa thành mục `1.3.1 Đối tượng nghiên cứu` và `1.3.2 Phạm vi nghiên cứu`.

---

## NỘI DUNG 4: MỤC TIÊU ĐỀ TÀI VÀ CÁC YÊU CẦU HỆ THỐNG

### 4.1. Yêu cầu chức năng hệ thống (Functional Requirements)
Hệ thống phân rã đầy đủ theo 4 nhóm tác nhân:
1. **Khách hàng (Customer - Online Storefront):** Đăng ký/đăng nhập JWT, khám phá ngành hàng, tìm kiếm realtime debounce, giỏ hàng, thanh toán trực tuyến VNPay / COD, theo dõi đơn hàng, tương tác với AI Chatbot (nhận gợi ý mua kèm và tự động thêm hàng vào giỏ).
2. **Thu ngân (Cashier - POS Terminal):** Đăng nhập nhanh bằng mã PIN 4-6 số (mã hóa Bcrypt, khóa sau 5 lần sai), quét mã vạch bán lẻ, chọn lô hàng theo hạn sử dụng, **lưu và phục hồi đơn hàng chờ (Hold orders)**, thanh toán tiền mặt (tự tính tiền thừa), hiển thị mã QR VNPay động, in hóa đơn nhiệt.
3. **Quản lý cửa hàng (Store Manager):** Quản lý đơn nhập hàng nhà cung cấp (Purchase Order), nghiệm thu nhập kho và gán vị trí ô/kệ (Location/Block), quản lý hạn dùng lô hàng (Batch), điều chuyển hàng lên kệ (Move to Shelf), xuất hủy hàng hỏng (Stock Out), theo dõi công nợ NCC chi nhánh.
4. **Quản trị viên cấp cao (Super Admin / Chain Owner):** Khởi tạo và quản lý chi nhánh (`store_id`), quản trị danh mục tập trung (SKU, giá niêm yết, lịch sử đổi giá), phân quyền vai trò RBAC, cấu hình hệ thống (bảo mật PIN, chiết khấu VIP, tự động khuyến mãi ban đêm cho hàng cận date lúc 18h), xem Dashboard toàn chuỗi.

### 4.2. Yêu cầu dữ liệu (Data Requirements)
1. **ACID & Eventual Consistency:** Giao dịch cục bộ tuân thủ ACID; giao dịch phân tán giữa Payment, Order và Inventory tuân thủ Saga Choreography, có cơ chế đền bù tự động (Compensation).
2. **Cách ly dữ liệu đa người thuê:** Mọi bảng nghiệp vụ chi nhánh bắt buộc có khóa ngoại `store_id`. Middleware tự động trích xuất `storeId` từ JWT Token đã được ký số để áp vào câu truy vấn.
3. **Bán cấu trúc và Kiểm toán:** Sử dụng `JSONB` cho snapshot giỏ hàng, cấu hình động và audit log (`settings_history`, `inventory_movement`). Bảng `processed_events` đảm bảo xử lý Idempotent. Bảng `outbox` đảm bảo Transactional Outbox.
4. **Lưu trữ Vector nhúng:** Tích hợp `pgvector` HNSW 768 chiều (Vietnamese SBERT) kết hợp Full-Text Search GIN trên bảng `product_knowledge_base`.
5. **Tính bất biến của dữ liệu Benchmark:** Hỗ trợ trường `benchmark_run_id` trong `sale_order`. Module `ai-service-v2` quản lý Dataset Snapshot v5.1 bất biến kiểm chứng bằng SHA-256, phân tách thời gian nghiêm ngặt Train / Val / Test.

### 4.3. Yêu cầu giao diện, phần cứng, phần mềm
* **Giao diện (UI/UX - ĐẦY ĐỦ CẢ 3 PHÂN HỆ):**
  1. *POS Terminal (6 màn hình):* Đăng nhập PIN, Bán hàng quét mã vạch, Modal đơn chờ Hold order, Thanh toán tiền mặt, Thanh toán VNPay QR động, Mẫu in hóa đơn.
  2. *Admin & Manager Dashboard (16 màn hình):* Overview toàn chuỗi, Quản lý chi nhánh, RBAC, Cấu hình, Nhà cung cấp & công nợ, Đơn nhập PO, Nghiệm thu nhập kho theo kệ, Quản lý lô hàng, Sơ đồ kho bãi trực quan, Báo cáo doanh thu Redis cache.
  3. *Customer Storefront (8 màn hình):* Trang chủ, Danh mục & lọc sản phẩm, Chi tiết sản phẩm & gợi ý Apriori, Giỏ hàng, Thanh toán VNPay Sandbox, Lịch sử đơn hàng, Floating widget Trợ lý ảo AI Action Assistant.
* **Phần mềm:** Node.js v20 LTS, Python 3.11+, PostgreSQL 16 (pgvector), Redis 7, RabbitMQ 3.13, Nginx Alpine, Docker Compose v2, Jest, Supertest, Pytest, Ruff, Mypy.
* **Phần cứng máy chủ:** Workstation phát triển RAM $\ge$ 16GB, CPU 6 cores; Staging Cloud VPS 4 vCPU, 8GB - 16GB RAM kết hợp Managed Cloud DB (Supabase, CloudAMQP, Redis Cloud).

### 4.4. Yêu cầu phi chức năng (Quality Attributes)
* **Hiệu năng:** API CRUD P95 < 200ms; AI pipeline P95 < 500ms; tra cứu luật Apriori $O(1)$ (< 5ms); Redis cache hit rate > 85%.
* **Bảo mật:** Rate Limiting 3 vùng tại Nginx, POS PIN băm Bcrypt, xác thực chữ ký VNPay HMAC-SHA512, tiêu đề bảo vệ Helmet.
* **Độ tin cậy:** Cô lập lỗi (Fault Isolation), bù trừ tự động qua Saga, không bao giờ mất mát sự kiện nhờ Transactional Outbox.

📌 **Tham chiếu vị trí trong `main.tex`:**
* Trong `main.tex`, yêu cầu chức năng và phi chức năng nằm rải rác ở Chương 3 (dòng 534–604), thiếu mục Yêu cầu dữ liệu ở Chương 1.
* *Kế hoạch cập nhật ở phase sau:* Cấu trúc lại Chương 1 thành mục `1.4 Mục tiêu đề tài và Các yêu cầu hệ thống` gồm đủ 4 tiểu mục chuẩn mực.

---

## NỘI DUNG 5: TỔNG HỢP VỊ TRÍ DỰ KIẾN CẬP NHẬT TRONG `main.tex`

| Khối nội dung trong `main.tex` | Dòng hiện tại trong `main.tex` | Tình trạng hiện tại | Dự kiến cập nhật ở Phase sau |
|:---|:---:|:---|:---|
| **Trang bìa & Khối thủ tục** | Dòng 1 – 134 | Tiêu đề "BÁO CÁO ĐỒ ÁN 2", thiếu Hội đồng chấm KLTN, thiếu English Abstract và Danh mục từ viết tắt. | Đổi thành "KHÓA LUẬN TỐT NGHIỆP - SE505.Q21", bổ sung trang Hội đồng, thêm Abstract từ paper draft, thêm Danh mục từ viết tắt. |
| **Chương 1: Tổng quan đề tài** | Dòng 137 – 210 | Gồm 8 mục rời rạc theo form đồ án 2, thiếu Bảng Ma trận nợ kỹ thuật 1.1, thiếu Yêu cầu dữ liệu. | Tái cấu trúc thành 4 mục lớn (1.1 đến 1.4), chèn **Bảng 1.1: Ma trận phân tích 3 chiều**, bổ sung Yêu cầu dữ liệu 5 trụ cột và 4 nhóm Actor. |
| **Chương 2: Cơ sở lý thuyết (Mục 2.1)** | Dòng 218 – 219 | Mục *"Những ứng dụng có liên quan"* **đang để trống**. | Bổ sung khảo sát 5 công trình kinh điển (Two-Tower Covington 2016, Wide & Deep Cheng 2016, BPR Rendle 2009, Apriori Agrawal 1994, Gusak 2025). |
| **Chương 2: Cơ sở lý thuyết (Mục 2.2.9)** | Dòng 410 – 528 | Chỉ có lý thuyết heuristic sơ bộ. | Bổ sung toán học từ `master_draft_stage2.tex`: Full-catalog ranking ($C_u$), Deep Two-Tower với BPR Loss, Additive Z-score Fusion, và Action Assistant Protocol. |
| **Chương 3: Kiến trúc hệ thống** | Dòng 606 – 642 | Ghi nhận "8 Microservices", thiếu Statistics Service :3009. | Cập nhật thành **9 Microservices**, bổ sung Statistics Service (Port 3009) dùng Redis Cache, làm rõ Transactional Outbox và Idempotency Guard. |
| **Chương 3: Thiết kế Giao diện** | Dòng 2960 – 3280 | Đã có danh sách 30 màn hình nhưng chưa làm nổi bật cấu trúc 3 phân hệ. | Gom nhóm và chuẩn hóa rõ rệt 3 phân hệ: (1) POS Terminal, (2) Admin Dashboard, (3) Customer Storefront. |
| **Chương 4: Kiểm thử chương trình** | Dòng 3285 – 3801 | Chỉ có kiểm thử chức năng và phi chức năng backend. | Bổ sung mục **Kết quả Thực nghiệm & Benchmark Hệ gợi ý lai từ paper draft**: Bảng kết quả so sánh MostPop, Apriori, Deep Two-Tower BPR, và Proposed Hybrid trên Snapshot v5.1. |
| **Kết luận & Hướng phát triển** | Dòng 3802 – 3825 | Kết luận ở mức Đồ án 2. | Bổ sung 3 đóng góp khoa học và định hướng hoàn thiện bài báo khoa học xuất bản hội nghị. |
| **Tài liệu tham khảo** | Dòng 3831 – 3870 | Có 12 tài liệu tham khảo cơ bản. | Bổ sung các bài báo khoa học chuẩn quốc tế từ `master_draft_stage2.tex` (Covington 2016, Cheng 2016, Rendle 2009, Gusak 2025, Petrov 2022, Kleppmann 2022). |

---

## KẾT LUẬN

Báo cáo này đã chuẩn bị đầy đủ 100% luận cứ, số liệu và cơ sở khoa học để 2 sinh viên tự tin báo cáo và thảo luận với **TS. Nguyễn Thị Xuân Hương** trong buổi họp đầu tiên hôm nay:
1. Đã làm rõ tính thuyết phục để tiếp tục từ Đồ án 2 lên Khóa luận tốt nghiệp.
2. Đã có Bảng Ma trận nợ kỹ thuật 3 chiều (Bảng 1.1) theo đúng phong cách yêu cầu của Cô.
3. Đã xác định rõ đối tượng, phạm vi nghiên cứu, và đầy đủ 4 nhóm yêu cầu hệ thống (bao quát cả 3 phân hệ giao diện: POS, Admin Dashboard, Customer Storefront).
4. Đã sẵn sàng các nội dung học thuật từ paper draft `master_draft_stage2.tex` để trả lời câu hỏi về mô hình gợi ý và định hướng công bố bài báo.
5. Đã định vị chính xác toàn bộ vị trí tham chiếu cần cập nhật trong `main.tex` để sẵn sàng tiến hành cập nhật mã nguồn luận văn ở phase tiếp theo sau khi Cô thông qua.
