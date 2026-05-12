# Phase 1: PREPARE — Kế Hoạch Chi Tiết

> Cập nhật: 13/05/2026 — Dựa trên báo cáo tiến độ và phân tích codebase thực tế.

---

## Tiến Độ Tổng Quan

| Bước | Tên | Trạng thái | Ưu tiên |
|------|-----|-----------|---------|
| **1.1** | Chuẩn bị Server DigitalOcean | ✅ **HOÀN TẤT** | — |
| **1.2** | Docker Compose Production + .env template | ⏳ **ĐANG LÀM** | ⭐ Số 1 |
| **1.3** | Cấu hình Nginx Gateway (CORS, gzip) | 🔲 Chưa | Số 2 |
| **1.4** | Bảo mật CORS trên 6 services | 🔲 Chưa | Số 3 |
| **1.5** | CI/CD Pipeline (GitHub Actions) | 🔲 Chưa | Số 4 |
| **1.6** | Script hỗ trợ + Healthcheck fix | 🔲 Chưa | Số 5 |

---

## 1.1 — Chuẩn bị Server DigitalOcean ✅ HOÀN TẤT

| Hạng mục | Trạng thái | Ghi chú |
|----------|-----------|---------|
| Swap 4GB | ✅ | Gánh AI Chatbot RAG trên máy 2GB |
| Firewall UFW | ✅ | Chỉ port 22, 80, 443. Đã bít 2375/2376 |
| Nginx Reverse Proxy | ✅ | `127.0.0.1:8080` + WebSocket |
| SSL Certificate | ✅ | `api.mini-mart.dev` — hết hạn 10/08/2026 |
| Thư mục `/opt/minimart` | ✅ | Sẵn sàng nhận file cấu hình |

---

## 1.2 — Docker Compose Production ⏳ ĐANG LÀM

### Phân tích

Database (Supabase), Redis, RabbitMQ đều trên Cloud → Droplet 2GB chỉ gánh Node.js containers + Nginx Gateway. `mem_limit` bắt buộc để ngăn tràn RAM → Swap quá nhanh.

### File cần tạo

#### [NEW] `backend/docker-compose.prod.yml`

Nội dung đã được xác nhận trong review:

```yaml
version: '3.8'

x-common-config: &common-config
  restart: always
  networks:
    - minimart-net
  env_file:
    - .env

services:
  gateway:
    <<: *common-config
    image: ghcr.io/phatnguyentt2/mini-mart/gateway:latest
    container_name: minimart-gateway
    ports:
      - "8080:80"
    mem_limit: 150m
    depends_on:
      - auth
      - catalog

  auth:
    <<: *common-config
    image: ghcr.io/phatnguyentt2/mini-mart/auth:latest
    container_name: minimart-auth
    mem_limit: 250m

  catalog:
    <<: *common-config
    image: ghcr.io/phatnguyentt2/mini-mart/catalog:latest
    container_name: minimart-catalog
    mem_limit: 250m

  order:
    <<: *common-config
    image: ghcr.io/phatnguyentt2/mini-mart/order:latest
    container_name: minimart-order
    mem_limit: 250m

  settings:
    <<: *common-config
    image: ghcr.io/phatnguyentt2/mini-mart/settings:latest
    container_name: minimart-settings
    mem_limit: 200m

  supplier:
    <<: *common-config
    image: ghcr.io/phatnguyentt2/mini-mart/supplier:latest
    container_name: minimart-supplier
    mem_limit: 200m

  inventory:
    <<: *common-config
    image: ghcr.io/phatnguyentt2/mini-mart/inventory:latest
    container_name: minimart-inventory
    mem_limit: 250m

  payment:
    <<: *common-config
    image: ghcr.io/phatnguyentt2/mini-mart/payment:latest
    container_name: minimart-payment
    mem_limit: 250m

  statistics:
    <<: *common-config
    image: ghcr.io/phatnguyentt2/mini-mart/statistics:latest
    container_name: minimart-statistics
    mem_limit: 200m

  chatbot:
    <<: *common-config
    image: ghcr.io/phatnguyentt2/mini-mart/chatbot:latest
    container_name: minimart-chatbot
    mem_limit: 1.2g

networks:
  minimart-net:
    driver: bridge
```

**Tổng RAM cấp phát: ~2.4GB** (vừa đủ cho 2GB RAM + Swap đệm)

| Service | Mem Limit | Lý do |
|---------|-----------|-------|
| gateway | 150m | Static proxy, không xử lý logic |
| auth, catalog, order, inventory, payment | 250m | CRUD + DB queries |
| settings, supplier, statistics | 200m | Ít tải hơn |
| chatbot | **1.2g** | Load model RAG + Embedding vào bộ nhớ |

#### [NEW] `backend/.env.prod.example`

```env
# ==========================================
# POSMART MINI-MART - PRODUCTION ENVIRONMENT
# File này chỉ là template. KHÔNG điền secret thật.
# File .env thật đặt tại /opt/minimart/.env trên Droplet
# ==========================================

# 1. CORE & SECURITY
NODE_ENV=production
CORS_ORIGINS=https://admin.mini-mart.dev,https://shop.mini-mart.dev
JWT_SECRET=

# 2. DATABASES (Supabase)
DATABASE_URL=postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres
CATALOG_DB_URL=postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres

# 3. CACHE & MESSAGE BROKER
REDIS_URL=redis://default:PASSWORD@ENDPOINT.cloud.redislabs.com:12869
RABBITMQ_URL=amqps://USER:PASSWORD@HOST.rmq.cloudamqp.com/VHOST

# 4. EXTERNAL SERVICES
VNP_TMN_CODE=
VNP_HASH_SECRET=
VNP_URL=https://sandbox.vnpayment.vn/paymentv2/vpcpay.html
VNP_API=https://sandbox.vnpayment.vn/merchant_webapi/api/transaction
VNP_RETURN_URL=https://shop.mini-mart.dev/checkout/payment-result
VNP_TEST_MODE=true

# 5. AI / Chatbot
AI_MODEL_API_KEY=
```

### Hành động

1. Tạo `backend/docker-compose.prod.yml` với nội dung trên
2. Tạo `backend/.env.prod.example` với nội dung trên
3. Commit + push

---

## 1.3 — Cấu hình Nginx Gateway

### Phân tích hiện trạng

File [nginx.conf](file:///e:/UIT/backend/backend/gateway/nginx.conf) (328 dòng) hiện tại:
- ✅ Rate limiting đã có (strict/standard zones)
- ✅ WebSocket upgrade cho `/ws/chat`
- ✅ Health check endpoints (9 services + gateway)
- ❌ **Thiếu CORS headers** — browser sẽ bị chặn cross-origin
- ❌ **Thiếu gzip** — response chưa nén, tốn bandwidth
- ❌ **Thiếu X-Request-ID** — không trace được request qua services

### Thay đổi cần thực hiện

#### [MODIFY] `backend/gateway/nginx.conf`

**Thêm vào khối `http {}` (sau dòng 10):**

```nginx
    # === GZIP Compression ===
    gzip on;
    gzip_types text/plain application/json application/javascript text/css;
    gzip_min_length 256;
    gzip_vary on;
```

**Thêm vào khối `server {}` (sau dòng 68, trước các location):**

```nginx
        # === CORS Headers (Centralized) ===
        set $cors_origin '';
        if ($http_origin ~* '^https://(admin|shop)\.mini-mart\.dev$') {
            set $cors_origin $http_origin;
        }
        # Dev fallback
        if ($http_origin ~* '^http://localhost:(5173|5174)$') {
            set $cors_origin $http_origin;
        }

        add_header Access-Control-Allow-Origin $cors_origin always;
        add_header Access-Control-Allow-Methods 'GET, POST, PUT, PATCH, DELETE, OPTIONS' always;
        add_header Access-Control-Allow-Headers 'Authorization, Content-Type, X-Request-ID' always;
        add_header Access-Control-Allow-Credentials 'true' always;

        # Preflight
        if ($request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin $cors_origin;
            add_header Access-Control-Allow-Methods 'GET, POST, PUT, PATCH, DELETE, OPTIONS';
            add_header Access-Control-Allow-Headers 'Authorization, Content-Type, X-Request-ID';
            add_header Access-Control-Allow-Credentials 'true';
            add_header Content-Length 0;
            add_header Content-Type text/plain;
            return 204;
        }

        # === Request Tracing ===
        add_header X-Request-ID $request_id always;
        proxy_set_header X-Request-ID $request_id;
```

### Verify sau khi sửa

```bash
# Trong Docker dev
docker compose exec gateway nginx -t
docker compose restart gateway

# Test CORS
curl -I -H "Origin: https://admin.mini-mart.dev" http://localhost:8080/api/products
# Expect: Access-Control-Allow-Origin: https://admin.mini-mart.dev

curl -I -H "Origin: https://evil.com" http://localhost:8080/api/products
# Expect: KHÔNG có header Access-Control-Allow-Origin
```

---

## 1.4 — Bảo mật CORS trên 6 Services

### Phân tích hiện trạng

Kết quả grep codebase thực tế:

| Service | File | CORS hiện tại | Trạng thái |
|---------|------|--------------|-----------|
| auth | `services/auth/src/app.js:17` | `cors()` | ❌ Mở toàn bộ |
| catalog | `services/catalog/src/app.js:15` | `cors()` | ❌ Mở toàn bộ |
| supplier | `services/supplier/src/app.js:15` | `cors()` | ❌ Mở toàn bộ |
| settings | `services/settings/src/app.js:12` | `cors()` | ❌ Mở toàn bộ |
| statistics | `services/statistics/src/app.js:10` | `cors()` | ❌ Mở toàn bộ |
| chatbot | `services/chatbot/src/app.js:16` | `cors()` | ❌ Mở toàn bộ |
| chatbot | `services/chatbot/src/index.js:149` | `CORS_ORIGIN \|\| '*'` | ❌ Socket.IO fallback '*' |
| **order** | `services/order/src/app.js:11` | `CORS_ORIGINS` + allowedOrigins | ✅ Đúng chuẩn |
| **inventory** | `services/inventory/src/app.js:11` | `CORS_ORIGINS` + allowedOrigins | ✅ Đúng chuẩn |
| **payment** | `services/payment/src/app.js:11` | `CORS_ORIGINS` + allowedOrigins | ✅ Đúng chuẩn |

### Pattern chuẩn (copy từ order service)

```javascript
const allowedOrigins = (process.env.CORS_ORIGINS || 'http://localhost:5173').split(',').map(o => o.trim());
app.use(cors({ origin: allowedOrigins, credentials: true }));
```

### Thay đổi cần thực hiện

#### [MODIFY] 6 file — Thay `cors()` → pattern chuẩn

| File | Dòng | Thay đổi |
|------|------|---------|
| `services/auth/src/app.js` | L17 | `cors()` → pattern chuẩn |
| `services/catalog/src/app.js` | L15 | `cors()` → pattern chuẩn |
| `services/supplier/src/app.js` | L15 | `cors()` → pattern chuẩn |
| `services/settings/src/app.js` | L12 | `cors()` → pattern chuẩn |
| `services/statistics/src/app.js` | L10 | `cors()` → pattern chuẩn |
| `services/chatbot/src/app.js` | L16 | `cors()` → pattern chuẩn |

#### [MODIFY] `services/chatbot/src/index.js` — Socket.IO CORS

Dòng 149: Thay `CORS_ORIGIN || '*'` → dùng `CORS_ORIGINS` (comma-separated):

```javascript
const allowedOrigins = (process.env.CORS_ORIGINS || 'http://localhost:5174').split(',').map(o => o.trim());
// ...
cors: {
  origin: allowedOrigins,
  credentials: true
}
```

#### [MODIFY] `backend/docker-compose.yml` (dev)

Thêm `CORS_ORIGINS` cho tất cả services:

```yaml
environment:
  - CORS_ORIGINS=http://localhost:5173,http://localhost:5174
```

#### [MODIFY] `backend/docker-compose.prod.yml`

Đã có sẵn qua `env_file: .env` → biến `CORS_ORIGINS` trong `.env.prod` sẽ tự áp dụng.

### Verify

```bash
# Sau khi sửa, restart dev
docker compose down && docker compose up -d

# Test CORS blocked
curl -I -H "Origin: https://evil.com" http://localhost:8080/api/auth/login
# Expect: Không có Access-Control-Allow-Origin
```

---

## 1.5 — CI/CD Pipeline (GitHub Actions)

### File cần tạo

#### [NEW] `.github/workflows/deploy-backend.yml`

**Trigger:** Push vào `main` có thay đổi trong `backend/**`

```
Pipeline:
  1. Checkout code
  2. Login ghcr.io (GITHUB_TOKEN)
  3. Build Docker images (parallel matrix: 9 services + gateway)
  4. Push lên ghcr.io
  5. SSH vào Droplet
  6. cd /opt/minimart && docker compose pull && docker compose up -d
  7. Health check verification
```

**GitHub Secrets cần thiết:**

| Secret | Mục đích |
|--------|----------|
| `DO_HOST` | IP Droplet |
| `DO_SSH_KEY` | SSH private key |
| `DO_SSH_USER` | `root` |

> [!NOTE]
> Không cần `PROD_ENV_FILE` — file `.env` đã tạo trực tiếp trên Droplet.

#### [NEW] `.github/workflows/deploy-frontend.yml`

**Trigger:** Push vào `main` có thay đổi trong `frontend/**`

1. Lint (`npm run lint`)
2. Build (`npm run build`)
3. Vercel auto-deploy qua GitHub integration

#### [NEW] `.github/workflows/deploy-customer.yml`

**Trigger:** Push vào `main` có thay đổi trong `customer/**` — cùng pattern.

#### [NEW] `.github/workflows/ci.yml`

**Trigger:** Tất cả PR vào `main`

```
Pipeline:
  1. Lint packages bị thay đổi
  2. Unit tests (nếu có)
  3. Build verification (frontend + customer)
  4. Docker build test (chỉ build, không push)
```

---

## 1.6 — Script Hỗ Trợ + Healthcheck Fix

### Phân tích hiện trạng

File [healthcheck.js](file:///e:/UIT/backend/backend/scripts/healthcheck.js) (76 dòng):
- ❌ **Thiếu `statistics`** trong mảng SERVICES (chỉ có 8/9)
- ❌ **Không có exit code** — CI/CD không biết pass/fail

### Thay đổi cần thực hiện

#### [MODIFY] `backend/scripts/healthcheck.js`

**Dòng 3-12 — Thêm statistics:**

```javascript
const SERVICES = [
  'auth',
  'catalog',
  'order',
  'settings',
  'supplier',
  'inventory',
  'payment',
  'chatbot',
  'statistics'  // ← THÊM
];
```

**Dòng 67-75 — Thêm exit code:**

```javascript
async function run() {
  console.log('Fetching overall health status of POSMART microservices...\n');
  const results = await Promise.all(SERVICES.map(checkService));
  results.forEach(r => {
    console.log(`${r.Service.padEnd(10)} | HTTP: ${r.Status.padEnd(8)} | DB: ${r.Database.padEnd(8)} | MQ: ${r.RabbitMQ.padEnd(4)} | Time: ${r.Time_ms}ms`);
  });

  // Exit code cho CI/CD
  const hasFailure = results.some(r => r.Status !== 'UP');
  if (hasFailure) {
    console.log('\n❌ Một số service không hoạt động!');
    process.exit(1);
  }
  console.log('\n✅ Tất cả services hoạt động bình thường.');
}
```

#### [NEW] `infra/scripts/setup-server.sh`

Script khởi tạo server (đã thực hiện thủ công, lưu lại để tham khảo):
- Cài Docker + Docker Compose
- Cấu hình UFW (22, 80, 443)
- Tạo Swap 4GB
- Cài Nginx + Certbot
- Tạo `/opt/minimart`

#### [NEW] `infra/scripts/deploy.sh`

Script deploy trên Droplet:

```bash
#!/bin/bash
set -e
cd /opt/minimart
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
sleep 30
node scripts/healthcheck.js || echo "⚠️ Một số service không qua health check"
docker system prune -f
```

---

## Tóm Tắt File Thay Đổi Phase 1

| Hành động | File | Bước |
|-----------|------|------|
| **NEW** | `backend/docker-compose.prod.yml` | 1.2 |
| **NEW** | `backend/.env.prod.example` | 1.2 |
| **MODIFY** | `backend/gateway/nginx.conf` | 1.3 |
| **MODIFY** | `services/auth/src/app.js` (L17) | 1.4 |
| **MODIFY** | `services/catalog/src/app.js` (L15) | 1.4 |
| **MODIFY** | `services/supplier/src/app.js` (L15) | 1.4 |
| **MODIFY** | `services/settings/src/app.js` (L12) | 1.4 |
| **MODIFY** | `services/statistics/src/app.js` (L10) | 1.4 |
| **MODIFY** | `services/chatbot/src/app.js` (L16) | 1.4 |
| **MODIFY** | `services/chatbot/src/index.js` (L149) | 1.4 |
| **MODIFY** | `backend/docker-compose.yml` | 1.4 |
| **NEW** | `.github/workflows/deploy-backend.yml` | 1.5 |
| **NEW** | `.github/workflows/deploy-frontend.yml` | 1.5 |
| **NEW** | `.github/workflows/deploy-customer.yml` | 1.5 |
| **NEW** | `.github/workflows/ci.yml` | 1.5 |
| **MODIFY** | `backend/scripts/healthcheck.js` (L3, L67) | 1.6 |
| **NEW** | `infra/scripts/setup-server.sh` | 1.6 |
| **NEW** | `infra/scripts/deploy.sh` | 1.6 |
