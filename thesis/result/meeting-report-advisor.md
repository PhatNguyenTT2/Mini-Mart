# BÁO CÁO CHI TIẾT LÀM VIỆC VỚI GIẢNG VIÊN HƯỚNG DẪN
## ĐỀ TÀI: PHÁT TRIỂN HỆ THỐNG QUẢN LÝ BÁN LẺ ĐA CHI NHÁNH DỰA TRÊN KIẾN TRÚC MICROSERVICES VÀ HỆ GỢI Ý THÔNG MINH LAI

**Giảng viên hướng dẫn:** TS. Nguyễn Thị Xuân Hương  
**Sinh viên thực hiện:** 
- Nguyễn Trương Tiến Phát (MSSV: 23521148)
- Đỗ Minh Đức (MSSV: 23520303)  
**Chuyên ngành:** Kỹ thuật Phần mềm – Khoa Công nghệ Phần mềm  
**Đơn vị:** Trường Đại học Công nghệ Thông tin, ĐHQG-HCM  

---

## MỤC LỤC BÁO CÁO
1. [Nội dung 1: Động lực nghiên cứu và Lý do chọn đề tài](#nội-dung-1-động-lực-nghiên-cứu-và-lý-do-chọn-đề-tài)
2. [Nội dung 2: Khảo sát hiện trạng và Hệ thống đề xuất](#nội-dung-2-khảo-sát-hiện-trạng-và-hệ-thống-đề-xuất)
3. [Nội dung 3: Đối tượng và Phạm vi nghiên cứu](#nội-dung-3-đối-tượng-và-phạm-vi-nghiên-cứu)
4. [Nội dung 4: Mục tiêu đề tài và Các yêu cầu hệ thống](#nội-dung-4-mục-tiêu-đề-tài-và-các-yêu-cầu-hệ-thống)
5. [Bảng đối chiếu và Tham chiếu chi tiết các thay đổi trong Báo cáo Luận văn (`main.tex`)](#bảng-đối-chiếu-và-tham-chiếu-chi-tiết-các-thay-đổi-trong-báo-cáo-luận-văn-maintex)

---

## NỘI DUNG 1: ĐỘNG LỰC NGHIÊN CỨU VÀ LÝ DO CHỌN ĐỀ TÀI

### 1.1. Bối cảnh và Tính cấp thiết
* **Xu hướng thương mại bán lẻ đa kênh (Omnichannel Retailing):** Sự bùng nổ của mô hình kết hợp giữa trải nghiệm tại quầy siêu thị tiện lợi và kênh mua sắm trực tuyến (BOPIS – Buy Online, Pick Up In Store) đặt ra áp lực vận hành theo thời gian thực (Real-time). Khách hàng đòi hỏi khả năng tra cứu tồn kho tức thời tại từng chi nhánh cụ thể, trong khi hệ thống bán lẻ phải đảm bảo tốc độ phản hồi tính bằng mili-giây cho nhân viên thu ngân tại điểm bán.
* **Điểm nghẽn nghiêm trọng của kiến trúc nguyên khối (Monolith):** Các phần mềm bán lẻ truyền thống khi tích hợp cổng thương mại điện tử thường đối mặt với xung đột tài nguyên sâu sắc:
  * Phân hệ tra cứu danh mục và giỏ hàng trực tuyến đòi hỏi năng lực đọc dữ liệu cực lớn (*Read-heavy*).
  * Phân hệ thu ngân POS tại quầy và biến động kho hàng lại liên tục ghi dữ liệu (*Write-heavy*).
  * Việc sử dụng chung một cơ sở dữ liệu quan hệ nguyên khối dẫn đến hiện tượng khóa bảng (Table locking), nghẽn cổ chai I/O, và nguy cơ sự cố lan truyền (Cascading Failure) làm tê liệt toàn bộ các máy bán hàng tại các chi nhánh (Single Point of Failure – SPOF).
* **Bài toán kinh tế hạ tầng trong quản trị đa chi nhánh (Multi-tenancy):**
  * Mô hình cấp phát riêng biệt từng máy chủ và CSDL vật lý cho từng chi nhánh (Database-per-tenant) gây lãng phí chi phí hạ tầng nghiêm trọng đối với quy mô chuỗi bán lẻ vừa và nhỏ (< 100 cửa hàng).
  * Do đó, hệ thống bắt buộc phải giải quyết triệt để bài toán chia sẻ hạ tầng (Shared Database, Shared Schema) nhưng vẫn đảm bảo tính cô lập và toàn vẹn dữ liệu tuyệt đối ở mức dòng (**Row-Level Security – RLS**) thông qua định danh chi nhánh (`store_id`).

### 1.2. Động lực nâng cấp và Tính thuyết phục: Kế thừa từ Đồ án 2 lên Khóa luận tốt nghiệp
* **Nền tảng kỹ thuật đã hoàn thành trong Đồ án 2:**
  * Nhóm nghiên cứu đã phân rã thành công hệ sinh thái bán lẻ thành các Microservices độc lập, triển khai hạ tầng điều phối tin nhắn RabbitMQ và định tuyến Nginx API Gateway.
  * Hiện thực hóa thành công chu trình giao dịch phân tán Saga Choreography giữa luồng thanh toán (Payment Service) và luồng trừ kho (Inventory Service) kết hợp xác thực chữ ký số Webhook VNPay IPN.
* **Các bài toán khoa học chuyên sâu được mở rộng trong Khóa luận tốt nghiệp:**
  1. **Nâng cấp Trợ lý tác vụ hai chiều (Action Assistant):** Chuyển dịch toàn diện từ mô hình Chatbot chỉ đọc (Read-only RAG) sang mô hình trợ lý thực thi tác vụ hai chiều. Bằng việc xây dựng giao thức thông điệp hành động có cấu trúc (*Action Response Protocol*) kết hợp chốt chặn an toàn (*Confirmation Gate*) bảo vệ 7 lớp, Chatbot có khả năng trực tiếp hỗ trợ khách hàng và thu ngân tra cứu tồn kho theo chi nhánh, tạo đơn giữ chỗ tại quầy và tự động hóa giỏ hàng mà máy chủ Backend vẫn duy trì tính chất phi trạng thái (*Stateless*).
  2. **Nghiên cứu Hệ gợi ý thông minh lai (Hybrid Recommender System):** Thay thế các thuật toán lọc đơn giản bằng mô hình gợi ý hai nhánh kết hợp:
     * *Nhánh Wide:* Khai phá tập phổ biến và luật kết hợp Apriori trên tập các giỏ hàng mua sắm tự nhiên (Organic Transactions), nắm bắt các quy luật mua kèm tức thời tại quầy.
     * *Nhánh Deep Two-Tower:* Xây dựng mạng nơ-ron hai tháp độc lập (User Tower và Item Tower) tích hợp tầng chiếu đặc trưng văn bản, ngành hàng và giá bán; được huấn luyện chuyên sâu bằng hàm mất mát thứ hạng Bayesian Personalized Ranking (**BPR Loss**) trên không gian dữ liệu phản hồi ngầm.
     * *Cơ chế kết hợp Z-score per-user:* Chuẩn hóa phân phối điểm số của từng người dùng trước khi tính điểm lai tổng hợp, giúp cân bằng hoàn hảo giữa khả năng gợi ý chính xác quy luật sẵn có và khả năng gợi ý khám phá sản phẩm tiềm năng.
  3. **Cam kết tính nghiêm ngặt và khả năng tái lập thực nghiệm (Reproducibility):** Khóa luận xây dựng quy trình thực nghiệm độc lập với bộ dữ liệu kiểm thử đóng băng mã băm SHA-256 (Benchmark Dataset Snapshot), phân tách thời gian nghiêm ngặt (*Temporal Split*) và áp dụng giao thức đánh giá toàn danh mục hàng hóa (*Full-catalog ranking* $C_u = I \setminus H_u^{\text{seen}}$), đáp ứng đầy đủ chuẩn mực xuất bản công trình khoa học chuyên ngành.

📌 **Chi tiết tham chiếu các thay đổi so với báo cáo Đồ án 2 cũ trong `main.tex`:**
* *Báo cáo Đồ án 2 cũ (Dòng 137–154):* Chỉ nêu vắn tắt lý do chọn đề tài theo 4 gạch đầu dòng kỹ thuật cơ bản, chưa làm rõ tính cấp thiết của bài toán bán lẻ đa kênh, chưa phân tích mâu thuẫn đọc/ghi của Monolith và hoàn toàn thiếu vắng cơ sở khoa học cho việc nâng cấp lên Khóa luận tốt nghiệp.
* *Báo cáo Luận văn hiện tại (`main.tex` Mục 1.1):* Đã được viết mới toàn diện, phân tích sâu sắc động lực chuyển dịch Omnichannel, chứng minh tính cấp thiết của kiến trúc Microservices phân tán và khẳng định rõ 3 mũi nhọn nâng cấp khoa học (Action Assistant, Mô hình lai Deep Two-Tower với BPR Loss, và Thực nghiệm Full-catalog tái lập).

---

## NỘI DUNG 2: KHẢO SÁT HIỆN TRẠNG VÀ HỆ THỐNG ĐỀ XUẤT

### 2.1. Khảo sát các nền tảng tương đương hiện có
1. **Nền tảng đóng gói SaaS nội địa (KiotViet, Sapo, Haravan):**
   * *Ưu điểm:* Triển khai nhanh, giao diện thân thiện với hộ kinh doanh nhỏ lẻ tại Việt Nam.
   * *Hạn chế kỹ thuật:* Kiến trúc hộp đen đóng kín, không cung cấp API mở phân tán để mở rộng; năng lực gợi ý sản phẩm chỉ dừng lại ở thống kê doanh số bán chạy nhất (Best-seller) thô sơ; hoàn toàn thiếu vắng trợ lý ảo tương tác tác vụ thông minh.
2. **Nền tảng mã nguồn mở (WooCommerce, Magento, Odoo POS):**
   * *Ưu điểm:* Mã nguồn mở, cho phép can thiệp chỉnh sửa logic nghiệp vụ.
   * *Hạn chế kỹ thuật:* Kiến trúc nguyên khối truyền thống dựa trên CSDL MySQL/PostgreSQL dùng chung gây suy giảm hiệu năng nghiêm trọng khi dữ liệu giao dịch tăng trưởng; chi phí duy trì phần cứng đắt đỏ; Odoo sử dụng mô hình xử lý đơn luồng đồng bộ trong Python, gây nghẽn cổ chai khi nhiều máy POS đồng thời kết nối.
3. **Nền tảng Cloud quốc tế (Shopify Plus):**
   * *Ưu điểm:* Hạ tầng chịu tải toàn cầu ổn định, hệ sinh thái ứng dụng phong phú.
   * *Hạn chế kỹ thuật:* Chi phí bản quyền và hoa hồng giao dịch rất cao, không phù hợp cho chuỗi bán lẻ nội địa; không thể can thiệp tùy biến sâu vào mô hình định tuyến kho chi tiết theo ô/kệ (Location/Block) và nghiệp vụ điều chuyển hàng hóa liên chi nhánh.

### 2.2. BẢNG 1.1: MA TRẬN PHÂN TÍCH KHOẢNG CÁCH NĂNG LỰC, ĐIỂM NGHẼN KIẾN TRÚC VÀ NỢ KỸ THUẬT
*(Bảng ma trận phân tích 3 chiều được xây dựng hoàn chỉnh theo phương pháp luận đánh giá khoa học)*

| Tiêu chí phân tích (Ma trận tư duy) | Biểu hiện thực tế & Nguyên nhân kỹ thuật | Hệ quả & Điểm nghẽn hệ thống |
|:---|:---|:---|
| **1. Khoảng cách năng lực và Ràng buộc hệ thống (Capability Gap)** | • Các giải pháp POS SaaS thương mại chỉ cung cấp các thao tác CRUD truyền thống, không có cơ chế hiểu ngữ cảnh tự nhiên của khách hàng.<br>• Hoàn toàn thiếu hụt mô hình học máy gợi ý cá nhân hóa sâu theo lịch sử tiêu dùng và tương quan giỏ hàng thời gian thực.<br>• Bộ máy tìm kiếm sản phẩm phụ thuộc vào chuỗi từ khóa chính xác (Exact match), không xử lý được từ đồng nghĩa hoặc lỗi chính tả tiếng Việt. | • Bỏ lỡ cơ hội bán chéo sản phẩm (Cross-selling) nhằm gia tăng quy mô giá trị giỏ hàng.<br>• Nhân viên thu ngân mất nhiều thời gian tra cứu thủ công khi một mặt hàng cụ thể tại quầy bị hết.<br>• Trải nghiệm mua sắm trực tuyến rời rạc, tỷ lệ rời bỏ giỏ hàng (Cart Abandonment) ở mức cao. |
| **2. Điểm nghẽn hệ thống và Nguồn gốc vấn đề (Architectural Bottlenecks)** | • Xuất phát từ bản chất thiết kế nguyên khối (Monolithic Architecture) dùng chung một cơ sở dữ liệu quan hệ vật lý duy nhất.<br>• Khi phát sinh đột biến lưu lượng truy cập trực tuyến, tài nguyên CPU và bộ nhớ của CSDL bị chiếm dụng bởi các truy vấn thống kê phức tạp.<br>• Chiến lược đa người thuê nếu triển khai theo hướng Database-per-tenant gây cạn kiệt tài nguyên kết nối (Connection Pooling exhaustion). | • Hiện tượng nghẽn cổ chai tại phân hệ báo cáo hoặc kênh online có thể làm tê liệt toàn bộ luồng xuất hóa đơn tại quầy POS (Single Point of Failure).<br>• Chi phí thuê máy chủ đám mây tăng vọt nhưng không giải quyết được bài toán mở rộng quy mô độc lập. |
| **3. Nợ kỹ thuật và Sự đánh đổi kiến trúc (Technical Debt)** | • Khi tích hợp AI, các hệ thống có xu hướng gọi phụ thuộc hoàn toàn vào API đám mây thương mại của bên thứ ba.<br>• Bỏ qua tính tự chủ hạ tầng, độ trễ mạng Internet công cộng và sự kiểm soát mã nguồn giải thuật.<br>• Thiếu vắng cơ chế bù trừ giao dịch phân tán tự động (Saga Compensation) và kiểm soát trùng lặp sự kiện (Idempotency Guard). | • Chi phí vận hành biên tăng mất kiểm soát theo số lượt truy vấn.<br>• Độ trễ phản hồi của trợ lý ảo vượt ngưỡng 2 giây, không thể ứng dụng trong giao dịch thời gian thực tại quầy.<br>• Nguy cơ thất thoát dữ liệu bí mật kinh doanh về giá vốn, chính sách nhà cung cấp và thông tin khách hàng ra hạ tầng ngoài. |

### 2.3. Hệ thống đề xuất: Nền tảng Quản trị Bán lẻ Phân tán POSMART
Để giải quyết triệt để các hạn chế trên, đề tài đề xuất kiến trúc hệ thống POSMART:
* **Hạ tầng 9 Microservices độc lập:** Auth & Identity (:3001), Catalog (:3002), Order (:3003), Settings (:3004), Supplier (:3005), Inventory (:3006), Payment (:3007), AI Chatbot (:3008), và Statistics & Analytics (:3009).
* **Cổng điều phối Nginx API Gateway (:8080):** Thiết lập cơ chế kiểm soát truy cập tập trung, phân vùng Rate Limiting (`strict` cho định danh, `standard` cho nghiệp vụ, `ws_conn` cho WebSocket), gắn mã định danh phân tán `$X\text{-Request-ID}$` phục vụ Distributed Tracing.
* **Mạng lưới hướng sự kiện RabbitMQ (`posmart.events`):** Đảm bảo giao dịch phân tán thông qua Saga Choreography kết hợp mẫu thiết kế Transactional Outbox và bảng chốt chặn Idempotency Guard (`processed_events`).
* **Hệ gợi ý thông minh lai kết hợp Deep Two-Tower (BPR Loss) và Wide Apriori:** Vận hành độc lập, cung cấp điểm số dự đoán cá nhân hóa chính xác với độ trễ thấp.

📌 **Chi tiết tham chiếu các thay đổi so với báo cáo Đồ án 2 cũ trong `main.tex`:**
* *Báo cáo Đồ án 2 cũ (Mục 2.1 dòng 218–219):* Tiêu đề *"Những ứng dụng có liên quan đến đề tài"* bị để trống hoàn toàn (0 nội dung), không có khảo sát so sánh công nghệ và thiếu vắng Ma trận nợ kỹ thuật 3 chiều.
* *Báo cáo Luận văn hiện tại (`main.tex` Mục 1.2 và Mục 2.1):* Bổ sung trọn vẹn Mục 1.2 với **Bảng 1.1: Ma trận nợ kỹ thuật 3 chiều** đạt chuẩn học thuật; đồng thời cập nhật Mục 2.1 với tổng quan các công trình nghiên cứu kinh điển quốc tế làm nền tảng lý thuyết vững chắc cho hệ thống.

---

## NỘI DUNG 3: ĐỐI TƯỢNG VÀ PHẠM VI NGHIÊN CỨU

### 3.1. Đối tượng nghiên cứu
1. **Kiến trúc hệ thống phần mềm phân tán:** Mô hình Microservices, API Gateway Pattern, Kiến trúc hướng sự kiện (Event-Driven Architecture) với RabbitMQ AMQP 0-9-1, Saga Pattern trong điều phối giao dịch phân tán không dùng khóa (Non-blocking), Mẫu thiết kế Transactional Outbox và Idempotent Consumer.
2. **Quản trị cơ sở dữ liệu đa người thuê:** Kỹ thuật Row-Level Multi-tenancy trên hệ quản trị CSDL quan hệ PostgreSQL 16; Mô hình lưu trữ đa dạng (Polyglot Persistence) kết hợp PostgreSQL (ACID), Redis (In-memory Caching) và chỉ mục vector `pgvector` HNSW.
3. **Mô hình Trợ lý tác vụ đàm thoại (Action Assistant):** Kỹ thuật truy xuất tăng cường RAG kết hợp giữa tìm kiếm ngữ nghĩa Vector nhúng (Vietnamese SBERT 768 chiều) và tìm kiếm toàn văn Full-Text Search GIN thông qua thuật toán hợp nhất thứ hạng tương hỗ Reciprocal Rank Fusion (RRF); Giao thức thông điệp tác vụ Action Response Protocol và chốt chặn an toàn Confirmation Gate 7 lớp.
4. **Hệ gợi ý thông minh lai hai nhánh (Hybrid Recommender System):** Thuật toán khai phá luật kết hợp Apriori; Mạng nơ-ron sâu hai tháp Deep Two-Tower; Kỹ thuật tối ưu hóa thứ hạng Bayesian Personalized Ranking (BPR Loss); Cơ chế chuẩn hóa Z-score per-user và giao thức đánh giá toàn danh mục Full-catalog ranking.

### 3.2. Phạm vi nghiên cứu
* **Quy mô triển khai ứng dụng:** Hệ thống tập trung giải quyết bài toán quản trị cho các chuỗi bán lẻ, siêu thị mini, cửa hàng tiện lợi có quy mô mạng lưới dưới 100 điểm bán chi nhánh.
* **Phân hệ thuộc phạm vi đề tài:**
  * Toàn bộ **9 Microservices Backend** độc lập vận hành trong môi trường container hóa.
  * Phân hệ nghiên cứu, huấn luyện và thực nghiệm đo lường học máy độc lập.
  * Đầy đủ cả **3 phân hệ giao diện người dùng (UI Surfaces)**:
    1. *POS Terminal:* Giao diện ứng dụng máy bán hàng chuyên dụng tại quầy cho thu ngân.
    2. *Admin & Manager Dashboard:* Cổng thông tin điều hành và quản trị chuỗi cho Chủ chuỗi và Quản lý chi nhánh.
    3. *Customer Storefront:* Cổng thương mại điện tử mua sắm trực tuyến tích hợp Trợ lý ảo cho khách hàng.
* **Ranh giới loại trừ (Out of scope):**
  * Không nghiên cứu bài toán tối ưu hóa lộ trình xe tải vận chuyển hàng hóa vật lý ngoài thực địa.
  * Không phát triển trình điều khiển phần cứng nhúng máy in hóa đơn ở cấp độ kernel hệ điều hành (hệ thống xuất hóa đơn thông qua giao thức chuẩn trình duyệt Web Print API).
* **Tích hợp dịch vụ bên thứ ba:**
  * Cổng thanh toán điện tử VNPay Sandbox phục vụ thanh toán qua mã phản hồi nhanh VNPay-QR động và thẻ ngân hàng.
  * Cổng suy luận ngôn ngữ tự nhiên Hugging Face Inference API phục vụ mô hình ngôn ngữ lớn nguồn mở.

📌 **Chi tiết tham chiếu các thay đổi so với báo cáo Đồ án 2 cũ trong `main.tex`:**
* *Báo cáo Đồ án 2 cũ (Dòng 165–183):* Nhầm lẫn nghiêm trọng giữa "Đối tượng sử dụng hệ thống" (Actors) và "Đối tượng nghiên cứu khoa học" (Research Objects); phạm vi nghiên cứu chỉ mô tả sơ sài các tính năng chung chung.
* *Báo cáo Luận văn hiện tại (`main.tex` Mục 1.3):* Đã được phân định rành mạch thành Mục `1.3.1 Đối tượng nghiên cứu` (gồm 4 trọng tâm kỹ thuật khoa học) và Mục `1.3.2 Phạm vi nghiên cứu` (bao quát đầy đủ 9 Microservices, AI Runner và cả 3 phân hệ giao diện POS, Dashboard, Storefront).

---

## NỘI DUNG 4: MỤC TIÊU ĐỀ TÀI VÀ CÁC YÊU CẦU HỆ THỐNG

### 4.1. Yêu cầu chức năng hệ thống (Functional Requirements)
Hệ thống được thiết kế đáp ứng toàn diện 4 nhóm tác nhân vận hành:
1. **Khách hàng trực tuyến (Customer – Storefront):**
   * Đăng ký, đăng nhập bảo mật bằng JSON Web Token (JWT).
   * Khám phá danh mục hàng hóa, tìm kiếm sản phẩm với cơ chế Realtime Debounce.
   * Quản lý giỏ hàng trực tuyến, đặt hàng và thanh toán trực tuyến qua cổng VNPay-QR hoặc nhận hàng thanh toán tiền mặt (COD).
   * Theo dõi trạng thái đơn hàng theo thời gian thực.
   * Tương tác đàm thoại với Trợ lý ảo AI: nhận gợi ý các mặt hàng mua kèm phù hợp và ra lệnh cho trợ lý tự động bổ sung sản phẩm vào giỏ hàng thông qua giao thức Action Response.
2. **Nhân viên thu ngân tại điểm bán (Cashier – POS Terminal):**
   * Đăng nhập phiên làm việc bằng mã PIN 4–6 số (mã hóa băm Bcrypt an toàn, tự động khóa tài khoản tạm thời sau 5 lần nhập sai).
   * Quét mã vạch sản phẩm (EAN-13), tự động chọn lô hàng có hạn sử dụng gần nhất theo nguyên tắc FEFO (First Expired, First Out).
   * Hỗ trợ lưu trữ và phục hồi danh sách đơn hàng chờ tại quầy (**Hold Orders**) khi khách hàng chưa hoàn tất việc chọn đồ.
   * Xử lý thanh toán đa phương thức: tiền mặt (hệ thống tự tính tiền thừa chính xác) hoặc hiển thị mã QR thanh toán động qua VNPay.
   * Xuất và in hóa đơn bán lẻ tức thời.
3. **Quản lý chi nhánh (Store Manager – Dashboard):**
   * Lập đơn đặt hàng nhập kho từ nhà cung cấp (Purchase Order – PO).
   * Thực hiện quy trình nghiệm thu hàng nhập kho, phân bổ vị trí lưu trữ hàng hóa chi tiết theo sơ đồ ô/kệ (Location / Block).
   * Quản lý vòng đời hạn sử dụng của từng lô hàng (Batch Management), nhận cảnh báo hàng cận hạn sử dụng.
   * Điều chuyển hàng hóa từ kho phụ lên kệ hàng trưng bày ngoài cửa hàng (Move to Shelf).
   * Lập phiếu xuất hủy hàng hỏng/hết hạn và theo dõi hạn mức công nợ nhà cung cấp của chi nhánh.
4. **Quản trị viên toàn chuỗi (Super Admin / Chain Owner – Dashboard):**
   * Khởi tạo chi nhánh mới và cấp phát mã định danh `store_id`.
   * Quản lý cây danh mục hàng hóa dùng chung toàn chuỗi (Centralized Catalog) và thiết lập chính sách giá bán.
   * Quản lý lịch sử biến động giá vốn và giá niêm yết (`product_price_history`).
   * Phân quyền truy cập dựa trên vai trò (Role-Based Access Control – RBAC).
   * Cấu hình thiết lập hệ thống tập trung (độ dài mã PIN, chiết khấu khách hàng thân thiết, tự động kích hoạt chương trình khuyến mãi giảm giá ban đêm cho hàng cận date lúc 18h hàng ngày).
   * Giám sát bảng điều khiển thông tin điều hành (Dashboard) toàn chuỗi với các chỉ số doanh thu, chi phí và lợi nhuận gộp được tăng tốc độ truy xuất bằng bộ nhớ đệm phân tán Redis.

### 4.2. Yêu cầu dữ liệu (Data Requirements)
Hệ thống được chuẩn hóa trên 5 trụ cột dữ liệu cốt lõi:
1. **Dữ liệu Master Data hàng hóa toàn chuỗi:** Quản lý tập trung tại Catalog Service, đảm bảo tính nhất quán về mã vạch, tên gọi, hình ảnh và danh mục sản phẩm trên toàn bộ các cửa hàng.
2. **Dữ liệu Tồn kho phân tán theo lô và vị trí:** Quản lý chi tiết tới cấp độ số lô (`batch_number`), hạn sử dụng (`expiry_date`), số lượng khả dụng (`quantity`), số lượng đã đặt chỗ (`reserved_quantity`), và tọa độ lưu kho trên giá kệ (`shelf_location`).
3. **Dữ liệu Giao dịch và Trạng thái phân tán:** Quản lý toàn bộ vòng đời đơn hàng và thanh toán. Bắt buộc áp dụng mẫu thiết kế **Transactional Outbox** để phát tán sự kiện đáng tin cậy và bảng kiểm soát trùng lặp **Idempotency Guard** (`processed_events`) để loại trừ nguy cơ xử lý trùng lặp giao dịch tài chính.
4. **Dữ liệu Vector nhúng và Tri thức nghiệp vụ:** Lưu trữ các vector biểu diễn ngữ nghĩa 768 chiều trên PostgreSQL với tiện ích mở rộng `pgvector`, tối ưu hóa truy vấn bằng chỉ mục đồ thị HNSW kết hợp chỉ mục đảo GIN phục vụ bộ máy tìm kiếm lai RRF.
5. **Dữ liệu Thực nghiệm Benchmark bất biến:** Cơ sở dữ liệu hỗ trợ trường định danh `benchmark_run_id` trong các bản ghi đơn hàng; phân hệ nghiên cứu quản lý bộ dữ liệu bộ dữ liệu thực nghiệm chuẩn hóa (Benchmark Dataset Snapshot) được cố định bằng mã băm SHA-256 với phân tách thời gian Train/Validation/Test nghiêm ngặt nhằm triệt tiêu hiện tượng rò rỉ thông tin tương lai (Data Leakage).

### 4.3. Yêu cầu giao diện người dùng (UI Surfaces)
Hệ thống hoàn thiện đầy đủ cả 3 phân hệ giao diện chuyên biệt:
* **Phân hệ POS Terminal (6 màn hình chuyên dụng):**
  1. Màn hình khóa và xác thực nhanh bằng mã PIN bảo mật.
  2. Màn hình bán hàng chính tích hợp quét mã vạch và giỏ hàng thời gian thực.
  3. Hộp thoại quản lý đơn hàng tạm hoãn (Hold Order Modal).
  4. Màn hình thanh toán tiền mặt với công cụ tính tiền thối tự động.
  5. Màn hình thanh toán điện tử VNPay hiển thị mã QR động.
  6. Mẫu in phiếu thanh toán hóa đơn nhiệt tiêu chuẩn.
* **Phân hệ Admin & Manager Dashboard (16 màn hình quản trị):**
  1. Bảng điều khiển tổng quan chỉ số kinh doanh toàn chuỗi.
  2. Màn hình quản trị chi nhánh và cấu hình cửa hàng.
  3. Màn hình quản lý người dùng và phân quyền vai trò RBAC.
  4. Màn hình cấu hình thiết lập bảo mật và tự động hóa hệ thống.
  5. Màn hình quản lý nhà cung cấp và theo dõi công nợ chi tiết.
  6. Màn hình lập và quản lý đơn đặt hàng nhập kho (PO).
  7. Màn hình nghiệm thu hàng nhập kho và định vị kệ hàng.
  8. Màn hình quản lý danh sách lô hàng và cảnh báo hạn dùng.
  9. Màn hình sơ đồ trực quan vị trí kho hàng và quầy kệ.
  10. Báo cáo doanh thu, lợi nhuận và phân tích tồn kho tăng tốc qua Redis Cache.
* **Phân hệ Customer Storefront (8 màn hình trực tuyến):**
  1. Trang chủ giới thiệu sản phẩm nổi bật và ngành hàng.
  2. Trang danh mục sản phẩm kết hợp bộ lọc động đa tiêu chí.
  3. Trang chi tiết sản phẩm tích hợp khối gợi ý mua kèm Apriori.
  4. Trang giỏ hàng trực tuyến và áp dụng mã giảm giá.
  5. Trang thanh toán đơn hàng tích hợp cổng VNPay Sandbox.
  6. Trang theo dõi lịch sử đơn hàng và trạng thái giao hàng.
  7. Floating Widget Trợ lý ảo AI tương tác đàm thoại và nhận lệnh hành động.

### 4.4. Yêu cầu phi chức năng (Quality Attributes)
* **Hiệu năng và Độ trễ:**
  * Độ trễ thời gian phản hồi cho 95% các yêu cầu nghiệp vụ CRUD (P95 Latency) đạt dưới **200ms**.
  * Độ trễ toàn chu trình xử lý của Trợ lý ảo AI (gồm trích xuất intent, truy xuất RAG vector và sinh phản hồi) đạt mức P95 dưới **500ms**.
  * Tốc độ suy diễn luật gợi ý bán chéo Apriori đạt mức tức thời $O(1)$ với độ trễ dưới **5ms**.
  * Tỷ lệ trúng bộ nhớ đệm (Cache Hit Ratio) trên phân hệ thống kê Statistics đạt trên **85%**.
* **Bảo mật và Phân quyền:**
  * Kiểm soát lưu lượng 3 tầng tại API Gateway (Strict 10 req/phút cho luồng nhạy cảm; Standard 100 req/phút cho luồng nghiệp vụ; Giới hạn kết nối đồng thời cho WebSocket).
  * Mã PIN thu ngân được mã hóa bằng thuật toán Bcrypt với hệ số Salt Rounds = 10; ngăn chặn tấn công dò quét Brute-force bằng cơ chế khóa tài khoản tự động.
  * Xác thực tính toàn vẹn thông điệp Webhook VNPay bằng thuật toán chữ ký số HMAC-SHA512.
* **Độ tin cậy và Tính toàn vẹn phân tán:**
  * Cơ chế bù trừ tự động của Saga Pattern đảm bảo không bao giờ xảy ra hiện tượng thất thoát tồn kho khi giao dịch thanh toán thất bại.
  * Mô hình Transactional Outbox kết hợp Idempotency Guard đảm bảo tin nhắn sự kiện được truyền phát chính xác và không bị xử lý lặp lại.

📌 **Chi tiết tham chiếu các thay đổi so với báo cáo Đồ án 2 cũ trong `main.tex`:**
* *Báo cáo Đồ án 2 cũ (Dòng 534–604 rải rác ở Chương 3):* Các yêu cầu chức năng và phi chức năng bị đặt sai vị trí ở Chương 3, viết chung chung, thiếu vắng hoàn toàn mục "Yêu cầu dữ liệu" và không liệt kê đầy đủ 3 phân hệ giao diện.
* *Báo cáo Luận văn hiện tại (`main.tex` Mục 1.4):* Đã được chuẩn hóa lại toàn bộ vào Chương 1 với 4 tiểu mục hoàn chỉnh (`1.4.1 Yêu cầu chức năng cho 4 nhóm tác nhân`, `1.4.2 Yêu cầu dữ liệu trên 5 trụ cột`, `1.4.3 Yêu cầu giao diện 3 phân hệ`, `1.4.4 Yêu cầu phi chức năng`).

---

## BẢNG ĐỐI CHIẾU VÀ THAM CHIẾU CHI TIẾT CÁC THAY ĐỔI TRONG BÁO CÁO LUẬN VĂN (`main.tex`)

Bảng dưới đây tổng hợp chi tiết toàn bộ các vị trí đã được rà soát, nâng cấp và cập nhật trực tiếp trong tài liệu báo cáo `main.tex` so với bản báo cáo Đồ án 2 cũ:

| Vị trí / Mục trong `main.tex` | Tình trạng trong Báo cáo Đồ án 2 cũ | Nội dung đã được Nâng cấp & Hoàn thiện trong Báo cáo Luận văn hiện tại |
|:---|:---|:---|
| **Trang bìa chính & Trang thông tin thủ tục**<br>*(Dòng 1 – 144)* | • Tiêu đề: "BÁO CÁO ĐỒ ÁN 2".<br>• Thiếu trang phê duyệt của Hội đồng chấm Khóa luận.<br>• Thiếu phần Tóm tắt luận văn bằng tiếng Anh (Abstract).<br>• Thiếu Bảng danh mục các từ viết tắt chuyên ngành. | • Cập nhật chuẩn hóa: **"KHÓA LUẬN TỐT NGHIỆP - SE505.Q21"**.<br>• Bổ sung đầy đủ trang Quyết định và Chữ ký của Hội đồng chấm Khóa luận tốt nghiệp.<br>• Bổ sung Lời cảm ơn trang trọng gửi đến GVHD TS. Nguyễn Thị Xuân Hương.<br>• Bổ sung phần Tóm tắt luận văn tiếng Việt và Abstract học thuật tiếng Anh.<br>• Bổ sung Danh mục từ viết tắt chuẩn mực (25 thuật ngữ quốc tế). |
| **Chương 1: Động lực nghiên cứu & Lý do chọn đề tài**<br>*(Mục 1.1, Dòng 252 – 287)* | • Chỉ có 4 gạch đầu dòng ngắn gọn về lý do làm ứng dụng.<br>• Hoàn toàn không phân tích bài toán kinh doanh bán lẻ đa kênh.<br>• Không chỉ ra được mâu thuẫn đọc/ghi của kiến trúc Monolith. | • Viết mới toàn diện Mục 1.1 theo văn phong học thuật chuyên sâu.<br>• Phân tích sâu sắc bài toán Omnichannel, mô hình BOPIS và xung đột I/O đọc/ghi.<br>• Chứng minh tính thuyết phục của việc nâng cấp từ Đồ án 2 lên Khóa luận tốt nghiệp dựa trên 3 mũi nhọn: Trợ lý tác vụ hai chiều Action Assistant, Mô hình lai Deep Two-Tower với BPR Loss, và Thực nghiệm Full-catalog có tính tái lập. |
| **Chương 1: Khảo sát hiện trạng & Bảng Ma trận nợ kỹ thuật 3 chiều**<br>*(Mục 1.2, Dòng 288 – 352)* | • Hoàn toàn không có nội dung khảo sát hiện trạng ở Chương 1.<br>• Thiếu vắng hoàn toàn Bảng ma trận nợ kỹ thuật 1.1 theo định hướng của GVHD. | • Bổ sung phân tích hiện trạng các giải pháp SaaS nội địa (KiotViet, Sapo), Open-source (Odoo, WooCommerce), và Cloud quốc tế (Shopify Plus).<br>• Xây dựng trọn vẹn **Bảng 1.1: Ma trận phân tích khoảng cách năng lực, điểm nghẽn kiến trúc và nợ kỹ thuật** tuân thủ cấu trúc ma trận 3 chiều đặc trưng của GVHD.<br>• Trình bày giải pháp đề xuất nền tảng phân tán POSMART. |
| **Chương 1: Đối tượng và Phạm vi nghiên cứu**<br>*(Mục 1.3, Dòng 353 – 388)* | • Bị nhầm lẫn giữa Tác nhân sử dụng (Actors) và Đối tượng nghiên cứu khoa học.<br>• Phạm vi mô tả chung chung, thiếu ranh giới kỹ thuật rõ ràng. | • Tách bạch chuẩn hóa thành `1.3.1 Đối tượng nghiên cứu` (Kiến trúc phân tán, Quản trị CSDL đa người thuê RLS, Trợ lý tác vụ đàm thoại, Hệ gợi ý thông minh lai) và `1.3.2 Phạm vi nghiên cứu` (Chuỗi < 100 cửa hàng, 9 Microservices, AI Runner, và cả 3 phân hệ giao diện POS, Dashboard, Storefront). |
| **Chương 1: Mục tiêu đề tài và Các yêu cầu hệ thống**<br>*(Mục 1.4, Dòng 389 – 486)* | • Thiếu vắng hoàn toàn mục Yêu cầu dữ liệu.<br>• Yêu cầu chức năng và phi chức năng bị đặt sai vị trí ở Chương 3. | • Tái cấu trúc chuẩn xác vào Chương 1 gồm đủ 4 tiểu mục:<br>  + Yêu cầu chức năng phân bổ theo 4 nhóm tác nhân.<br>  + Yêu cầu dữ liệu dựa trên 5 trụ cột (Master Data, Lô hàng/Vị trí, Giao dịch phân tán Saga/Outbox, Vector nhúng, Dữ liệu thực nghiệm bất biến).<br>  + Yêu cầu giao diện bao quát cả 3 phân hệ (POS, Dashboard, Storefront).<br>  + Yêu cầu phi chức năng về hiệu năng, bảo mật và độ tin cậy. |
| **Chương 2: Khảo sát các công trình liên quan**<br>*(Mục 2.1, Dòng 488 – 540)* | • Mục 2.1 mang tiêu đề *"Những ứng dụng có liên quan"* bị **để trống hoàn toàn (0 nội dung)**. | • Bổ sung tổng quan học thuật chuyên sâu về các công trình nghiên cứu kinh điển thế giới làm nền tảng cho đề tài: Deep Two-Tower (Covington et al., 2016), Wide & Deep (Cheng et al., 2016), Bayesian Personalized Ranking (Rendle et al., 2009), Thuật toán khai phá luật Apriori, và Giao thức phân tách thời gian Temporal Split (Gusak et al., 2025). |
| **Chương 2: Mô hình thuật toán Gợi ý thông minh lai**<br>*(Mục 2.2.9, Dòng 740 – 810)* | • Chỉ trình bày lý thuyết thuật toán heuristic bán chéo sơ bộ của Đồ án 2. | • Nâng cấp toàn diện cơ sở toán học của Mô hình Gợi ý lai:<br>  + Nguyên tắc xếp hạng toàn danh mục: $C_u = I \setminus H_u^{\text{seen}}$.<br>  + Kiến trúc mạng nơ-ron Deep Two-Tower (User Tower và Item Tower tích hợp Content Projection).<br>  + Hàm mất mát Bayesian Personalized Ranking ($\mathcal{L}_{\text{BPR}}$).<br>  + Cơ chế kết hợp lai cộng tính với chuẩn hóa Z-score độc lập cho từng người dùng.<br>  + Giao thức Trợ lý tác vụ hai chiều Action Assistant (Action Payload và Confirmation Gate). |
| **Chương 3: Kiến trúc Microservices**<br>*(Mục 3.2.2, Dòng 890 – 950)* | • Báo cáo cũ ghi nhận hệ thống gồm "8 Microservices", hoàn toàn bỏ sót Statistics Service. | • Cập nhật chính xác thành **9 Microservices** độc lập.<br>• Bổ sung chi tiết kiến trúc của **Statistics & Analytics Service (Port 3009)** sử dụng Redis Cache.<br>• Làm rõ cơ chế phân tán của Saga Orchestrator, Transactional Outbox và Idempotency Guard. |
| **Chương 4: Kết quả Thực nghiệm và Đo lường Benchmark**<br>*(Mục 4.3, Dòng 3650 – 3720)* | • Hoàn toàn không có thực nghiệm đo lường thuật toán học máy (chỉ có kiểm thử phần mềm thông thường). | • Bổ sung trọn vẹn phần **Thực nghiệm và Đo lường Mô hình Gợi ý Thông minh Lai**:<br>  + Thiết lập thực nghiệm trên bộ dữ liệu bộ dữ liệu thực nghiệm chuẩn hóa (Benchmark Dataset Snapshot) (5.000 người dùng, 5.200 sản phẩm, 823.371 tương tác) có mã băm SHA-256.<br>  + Giao thức phân tách thời gian Train / Validation / Test nghiêm ngặt.<br>  + **Bảng kết quả so sánh đối chuẩn (Benchmark Table)** giữa 4 mô hình: MostPop, Apriori, Deep Two-Tower BPR, và Proposed Hybrid trên các thang đo NDCG@10, HR@10, Recall@10, và Macro GAUC.<br>  + Phân tích khoa học chứng minh hiệu quả vượt trội của mô hình lai (+21.3% NDCG@10). |
| **Tài liệu tham khảo**<br>*(Phần BIBLIOGRAPHY, Cuối tài liệu)* | • Chỉ có 12 tài liệu tham khảo chung chung về lập trình web. | • Bổ sung đầy đủ các trích dẫn công trình khoa học quốc tế uy tín (ACM RecSys, UAI, DLRS, O'Reilly) chuẩn IEEE/ACM, tạo nền tảng vững chắc cho bài báo khoa học. |

---

## KẾT LUẬN VÀ BƯỚC ĐI TIẾP THEO

Bản báo cáo này đã hoàn thiện 100% các nội dung trọng tâm theo định hướng của Giảng viên hướng dẫn:
1. **Luận cứ thuyết phục:** Đã làm rõ lý do kế thừa và phát triển từ Đồ án 2 lên Khóa luận tốt nghiệp với hai trụ cột khoa học rõ rệt: Trợ lý tác vụ Action Assistant và Mô hình gợi ý lai Deep Two-Tower tối ưu bằng BPR Loss.
2. **Phương pháp luận chặt chẽ:** Đã hoàn thiện Bảng 1.1 Ma trận nợ kỹ thuật 3 chiều và tổng quan các công trình nghiên cứu nền tảng.
3. **Bao quát toàn diện hệ thống:** Phân định rõ 9 Microservices Backend, hạ tầng nghiên cứu thực nghiệm độc lập và đầy đủ cả 3 phân hệ giao diện (POS Terminal, Admin Dashboard, Customer Storefront).
4. **Đồng bộ hóa tài liệu mã nguồn:** Toàn bộ các định hướng trên đã được cập nhật trực tiếp vào tài liệu báo cáo luận văn `main.tex`, sẵn sàng cho công tác biên tập chuyên sâu và thực hiện các giai đoạn tiếp theo của Khóa luận tốt nghiệp.
