🛠️ Cách khắc phục (Dứt điểm nhãn unhealthy)
Bạn chỉ cần chỉnh lại địa chỉ IP trong file docker-compose.prod.yml (trên máy local) để ép Docker kiểm tra bằng chuẩn IPv4 (127.0.0.1).

Tìm khối cấu hình gateway và sửa lại phần healthcheck như sau:

YAML
  gateway:
    <<: *common-config
    image: ghcr.io/phatnguyentt2/mini-mart/gateway:latest
    container_name: minimart-gateway
    ports:
      - "8080:80"
    mem_limit: 150m
    healthcheck:
      # Sử dụng CMD-SHELL và 127.0.0.1 để đảm bảo tương thích 100% với Alpine
      test: ["CMD-SHELL", "wget -qO- http://127.0.0.1/health || exit 1"]
      interval: 30s
      timeout: 5s
      start_period: 10s
      retries: 3
    depends_on:
      - auth
      - catalog
Sau khi sửa xong, hãy commit và push lên GitHub để CI/CD tự động cập nhật:

Bash
git add backend/docker-compose.prod.yml
git commit -m "fix: update gateway healthcheck to use IPv4 127.0.0.1 and CMD-SHELL"
git push origin main