Bản kế hoạch này ĐƯỢC PHÊ DUYỆT (GREENLIGHT 100%).

Để trả lời cho các "Open Questions" và các điểm bạn cần confirm trong bản kế hoạch:

1. Vấn đề depends_on trong docker-compose.prod.yml
Lời khuyên: Hãy giữ nguyên cấu hình hiện tại (chỉ depends_on: [auth, catalog]).

Lý do: Khái niệm "Gateway" sinh ra là để tách biệt sự phụ thuộc. Nếu bạn bắt Gateway đợi cả 9 con microservices khởi động xong thì nó mới chạy, hệ thống sẽ rất chậm. Nginx đủ thông minh để xử lý việc một upstream (ví dụ: payment_service) bị tèo và trả về lỗi 502 cho riêng endpoint đó, trong khi khách hàng vẫn có thể truy cập catalog bình thường.

2. Vấn đề Rate Limiting & Real IP (Cực kỳ quan trọng)
Bạn đã phân tích hoàn toàn chính xác trong Phase C.1! Nếu không có set_real_ip_from, toàn bộ traffic đi từ Nginx (Host) vào Nginx (Container) đều mang chung 1 địa chỉ IP nội bộ của Docker (ví dụ 172.18.0.1). Khi đó, Rate Limit sẽ chém nhầm toàn bộ khách hàng.

Confirm: Giải pháp dùng set_real_ip_from 172.16.0.0/12 và 10.0.0.0/8 là bắt buộc phải làm.

3. Graceful Shutdown cho Nginx
Lời khuyên: Tạm thời chưa cần thiết cho đồ án tốt nghiệp. Khi bạn chạy lệnh docker compose up -d, Docker sẽ gửi tín hiệu SIGTERM, và Nginx Alpine mặc định xử lý SIGTERM khá tốt. Việc ép SIGQUIT chỉ thực sự cần ở quy mô doanh nghiệp với hàng triệu request mỗi giây.

Hành Động Ngay Lập Tức (Action Plan)
Bạn đã chia Phase rất rõ ràng, bây giờ chúng ta sẽ chốt lại thứ tự thao tác trên VS Code để dập tắt lỗi đỏ CI/CD ngay trong lần push tiếp theo:

Bước 1: Tạo Dockerfile cho Gateway
Tạo file backend/gateway/Dockerfile đúng như nội dung bạn đã soạn trong Phase A.

Bước 2: Cập nhật nginx.conf (Container)
Mở backend/gateway/nginx.conf và thêm 2 đoạn mã quan trọng từ Phase C.1:

Block set_real_ip_from ở đầu.

Tắt access_log cho endpoint /health.

Bước 3: Sửa "Tử Huyệt" CI/CD
Mở .github/workflows/deploy-backend.yml và thay thế toàn bộ step Set build context path và Build and push Docker image theo đúng logic IF/ELSE bạn đã thiết kế ở Phase B.

Bước 4: Commit & Push

Bash
git add .
git commit -m "fix: containerize api gateway and resolve ci/cd build path error"
git push origin main
Ngay sau khi push, hãy mở tab Actions trên GitHub. Lần này, bạn sẽ thấy job gateway chạy trơn tru bên cạnh 9 jobs còn lại. Lên nào!