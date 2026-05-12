# Kế Hoạch Triển Khai CI/CD — POSMART Mini-Mart

## Tổng Quan Kiến Trúc

```
┌──────────────────────────────────────────────────────┐
│  GitHub Repository: PhatNguyenTT2/Mini-Mart (main)   │
│  Monorepo:                                           │
│   /backend   ← 9 microservices + Nginx Gateway       │
│   /frontend  ← Admin/POS Dashboard (Vite + React 19) │
│   /customer  ← Customer Web (Vite + React 19)        │
└──────────────────────────────────────────────────────┘
```

### Bảng Thành Phần

| Thành phần | Tech Stack | Port | Nơi triển khai |
|------------|-----------|------|----------------|
| **Gateway** | Nginx Alpine | 8080→80 | DigitalOcean (Docker) |
| **Auth** | Node 20, Express, pg | 3001 | DigitalOcean (Docker) |
| **Catalog** | Node 20, Express, pg | 3002 | DigitalOcean (Docker) |
| **Order** | Node 20, Express, pg | 3003 | DigitalOcean (Docker) |
| **Settings** | Node 20, Express, pg | 3004 | DigitalOcean (Docker) |
| **Supplier** | Node 20, Express, pg | 3005 | DigitalOcean (Docker) |
| **Inventory** | Node 20, Express, pg | 3006 | DigitalOcean (Docker) |
| **Payment** | Node 20, Express, pg, VNPay | 3007 | DigitalOcean (Docker) |
| **Chatbot** | Node 20-slim, Socket.IO, AI/RAG | 3008 | DigitalOcean (Docker) |
| **Statistics** | Node 20, Express, Redis | 3009 | DigitalOcean (Docker) |
| **Frontend (Admin/POS)** | React 19, Vite, TW4 | 5173 | **Vercel** |
| **Customer Web** | React 19, Vite 8, TW3 | 5174 | **Vercel** |

### Dịch Vụ Ngoài (Cloud-managed)

| Dịch vụ | Nhà cung cấp | Trạng thái |
|---------|-------------|------------|
| PostgreSQL (Shared) | Supabase (ap-northeast-2) | ✅ Đã cấu hình |
| PostgreSQL (Catalog) | Supabase (ap-southeast-2) | ✅ Đã cấu hình |
| Redis | Redis Cloud (ap-east-1) | ✅ Đã cấu hình |
| RabbitMQ | CloudAMQP | ✅ Đã cấu hình |
| Domain | Name.com (`mini-mart.dev`) | ✅ Khả dụng |

### Hạ Tầng Hiện Có

| Hạng mục | Trạng thái | Vị trí |
|----------|-----------|--------|
| Dockerfiles (9 services) | ✅ Có | `services/*/Dockerfile` |
| docker-compose.yml (dev) | ✅ Có | `backend/docker-compose.yml` |
| docker-compose.prod.yml | ❌ **Thiếu** | Chưa tạo |
| .env.prod | ❌ **Thiếu** | Chưa tạo trên Droplet |
| Nginx Gateway config | ✅ Hoàn chỉnh | `backend/gateway/nginx.conf` |
| Health check endpoints | ✅ Tất cả 9 services | `/health/*` + `/ready/*` |
| Healthcheck script | ✅ Có | `backend/scripts/healthcheck.js` |
| GitHub Actions | ❌ **Thiếu** | Chưa có `.github/` |
| `.dockerignore` | ✅ Có | Loại trừ node_modules, .env |

### Hạ Tầng Server (DigitalOcean Droplet)

| Hạng mục | Trạng thái | Ghi chú |
|----------|-----------|--------|
| Swap 4GB | ✅ Hoạt động | Gánh AI Chatbot RAG trên máy 2GB |
| Firewall UFW | ✅ Đã bảo mật | Chỉ mở port 22, 80, 443. Đã bít Port 2375/2376 |
| Nginx Reverse Proxy | ✅ Chuẩn xác | Trỏ về `127.0.0.1:8080`, hỗ trợ WebSocket |
| SSL Certificate | ✅ Hợp lệ | `api.mini-mart.dev` — Hết hạn: 10/08/2026 (tự gia hạn) |
| Thư mục `/opt/minimart` | ✅ Đã tạo | Sẵn sàng nhận file cấu hình |
| Docker Containers | ⏳ Chưa deploy | Đang hiển thị 502 Bad Gateway (đúng tiến trình) |

---

## 📊 Walkthrough Tiến Độ

| Phase | Tên | Trạng thái | Chi tiết |
|-------|-----|-----------|----------|
| **1.1** | Chuẩn bị Server DigitalOcean | ✅ **HOÀN TẤT** | Swap, UFW, Nginx, SSL, /opt/minimart |
| **1.2** | Docker Compose Production | ⏳ Tiếp theo | Ưu tiên số 1 — file `docker-compose.prod.yml` |
| **1.3** | Cấu hình Nginx Gateway | 🔲 Chưa bắt đầu | CORS headers, gzip, X-Request-ID |
| **1.4** | Bảo mật CORS | 🔲 Chưa bắt đầu | Hardening 5 services + chatbot |
| **1.5** | CI/CD Pipeline | 🔲 Chưa bắt đầu | GitHub Actions workflows |
| **1.6** | Script Hỗ Trợ | 🔲 Chưa bắt đầu | setup-server.sh, deploy.sh |
| **2** | Backup & Rollback | 🔲 Chưa bắt đầu | Git tag, DB backup |
| **3** | Deploy Production | 🔲 Chưa bắt đầu | GitHub Secrets, Vercel, Backend deploy |
| **4** | Verify | 🔲 Chưa bắt đầu | Container, Health, Resources, Manual |
| **5** | Confirm / Rollback | 🔲 Chưa bắt đầu | Quyết định cuối cùng |

---

## 🔴 Vấn Đề Cần Xử Lý

> [!NOTE]
> ### 1. Secrets — ĐÃ AN TOÀN ✅
> File `.env` đã được thêm vào `.gitignore` ngay từ đầu, **chưa bao giờ bị commit** vào Git. Không cần rotate credentials. File `.env.prod` sẽ được tạo **trực tiếp trên Droplet** (không truyền qua GitHub Actions).

> [!WARNING]
> ### 2. CORS mở toàn bộ trên 5/9 service
> Auth, catalog, supplier, settings, statistics sử dụng `cors()` **không giới hạn origin**. Chỉ order, inventory, payment dùng `CORS_ORIGINS`. Chatbot dùng `CORS_ORIGIN || '*'`.

> [!WARNING]
> ### 3. Chưa có Docker Compose Production
> File `docker-compose.prod.yml` chưa tồn tại. File dev hiện tại dùng **volume mounts** và **expose toàn bộ port** — không an toàn cho production. **Đây là ưu tiên số 1 cần hoàn thành.**

> [!CAUTION]
> ### 4. Tài nguyên Server — GIỚI HẠN ĐỎ ⚠️
> Droplet 2GB RAM + 4GB Swap đã được cấu hình. Hệ thống 9 microservices + Chatbot AI/RAG đang chạy ở **mức giới hạn tối đa**. Ổ cứng đọc/ghi chậm hơn RAM rất nhiều — nếu Swap bị sử dụng quá mức (Thrashing), toàn bộ hệ thống sẽ bị treo cứng. Cần giám sát chặt chẽ trong Phase 4.

---

## Sơ Đồ Định Tuyến DNS

```
mini-mart.dev (Name.com)
│
├── api.mini-mart.dev ──→ A Record ──→ DigitalOcean Droplet IP
│                                      └── Nginx (host) :80/:443
│                                          └── proxy_pass → Docker :8080
│                                              └── Nginx (container) → microservices
│
├── admin.mini-mart.dev ──→ CNAME ──→ Vercel (frontend/)
│
└── shop.mini-mart.dev  ──→ CNAME ──→ Vercel (customer/)
```

---

## Các Phase Triển Khai

> Tuân theo quy trình 5 pha của DevOps: **PREPARE → BACKUP → DEPLOY → VERIFY → CONFIRM/ROLLBACK**

---

### Phase 1: PREPARE — Chuẩn Bị Hạ Tầng & Cấu Hình

> Mục tiêu: Chuẩn bị mọi thứ cần thiết trước khi triển khai — server, file cấu hình, pipeline CI/CD, và bảo mật.

#### 1.1 — Chuẩn bị Server DigitalOcean ✅ HOÀN TẤT

Tham chiếu: [deploy.md — Hướng dẫn chi tiết](file:///e:/UIT/backend/docs/deploy.md)

**Thực hiện qua DigitalOcean Web Console:**

| Bước | Hành động | Trạng thái |
|------|-----------|------------|
| Tạo Swap 4GB | Phân bổ 4GB RAM ảo cho AI Chatbot | ✅ Đã hoàn tất |
| Firewall UFW | Chỉ mở port 22, 80, 443. Đã bít 2375/2376 | ✅ Đã bảo mật |
| Nginx + Certbot | Reverse Proxy → `127.0.0.1:8080` + WebSocket | ✅ syntax ok |
| SSL Certificate | HTTPS cho `api.mini-mart.dev` (hết hạn 10/08/2026) | ✅ 🔒 Hợp lệ |
| Thư mục dự án | `/opt/minimart` sẵn sàng | ✅ Đã tạo |

#### 1.2 — Tạo file Production Docker Compose ⭐ ƯU TIÊN SỐ 1

##### [NEW] `backend/docker-compose.prod.yml`

- **Xóa** volume mounts (không hot-reload trong prod)
- **Xóa** ánh xạ port riêng lẻ (chỉ gateway:8080 được expose)
- Dùng image tag `ghcr.io/phatnguyentt2/mini-mart/<service>:latest`
- Thêm `restart: always`
- Thêm health checks cho từng container
- Thêm giới hạn bộ nhớ (chatbot: `mem_limit: 2g`)
- Thêm Docker network isolation
- Thiết lập network hợp lý để các service giao tiếp nội bộ

##### [NEW] `backend/.env.prod.example`

File template (không chứa secret thật), liệt kê tất cả biến môi trường production cần thiết.

> [!IMPORTANT]
> **Quản lý Secrets:** File `.env.prod` thật sẽ được tạo **trực tiếp trên Droplet** tại `/opt/minimart/.env`. KHÔNG truyền qua GitHub Actions hay bất kỳ pipeline nào. Docker Compose sẽ tự động đọc file này khi chạy `docker-compose up -d`.

#### 1.3 — Cấu hình Nginx Gateway

##### [MODIFY] `backend/gateway/nginx.conf`

- Thêm CORS headers tập trung tại gateway
- Thêm header `X-Request-ID` cho tracing
- Bật gzip compression

##### [NEW] `infra/nginx/api.mini-mart.dev.conf`

Cấu hình Nginx host-level trên Droplet:
- SSL termination (Let's Encrypt/Certbot)
- Reverse proxy tới Docker gateway `:8080`
- WebSocket upgrade cho `/ws/chat`
- Security headers (HSTS, X-Frame-Options, etc.)

#### 1.4 — Bảo mật CORS (Security Hardening)

##### [MODIFY] 5 file `services/*/src/app.js` (auth, catalog, supplier, settings, statistics)

Đổi `cors()` → `cors({ origin: allowedOrigins, credentials: true })` dùng biến `CORS_ORIGINS`, theo pattern đã có ở order/inventory/payment.

##### [MODIFY] `services/chatbot/src/index.js`

Đổi Socket.IO CORS từ `CORS_ORIGIN || '*'` → dùng `CORS_ORIGINS` (comma-separated).

##### [MODIFY] `backend/docker-compose.yml`

Thêm `CORS_ORIGINS` cho tất cả services (mặc định: `http://localhost:5173,http://localhost:5174`).

##### [MODIFY] `backend/docker-compose.prod.yml`

Set `CORS_ORIGINS=https://admin.mini-mart.dev,https://shop.mini-mart.dev`.

#### 1.5 — Thiết lập CI/CD Pipeline (GitHub Actions)

##### [NEW] `.github/workflows/deploy-backend.yml`

**Trigger:** Push vào `main` có thay đổi trong `backend/**`

```
Pipeline:
  1. Checkout code
  2. Build Docker images (parallel matrix: 9 services)
  3. Push lên GitHub Container Registry (ghcr.io)
  4. SSH vào DigitalOcean Droplet
  5. Pull images mới + docker-compose up -d
  6. Chạy health check xác minh
  7. Thông báo nếu thất bại (Discord/Slack webhook)
```

**GitHub Secrets cần thiết:**

| Secret | Mục đích |
|--------|----------|
| `DO_HOST` | IP của Droplet |
| `DO_SSH_KEY` | SSH private key để deploy |
| `DO_SSH_USER` | SSH user (mặc định: root) |

> [!NOTE]
> **Không cần** `PROD_ENV_FILE` trong GitHub Secrets. File `.env.prod` đã được tạo sẵn trực tiếp trên Droplet tại `/opt/minimart/.env`. Pipeline chỉ cần SSH vào và chạy `docker compose up -d`.

##### [NEW] `.github/workflows/deploy-frontend.yml`

**Trigger:** Push vào `main` có thay đổi trong `frontend/**`

1. Kiểm tra lint (`npm run lint`)
2. Xác minh build (`npm run build`)
3. Trigger deploy Vercel (hoặc dùng Vercel GitHub integration)

##### [NEW] `.github/workflows/deploy-customer.yml`

**Trigger:** Push vào `main` có thay đổi trong `customer/**` — cùng pattern với frontend.

##### [NEW] `.github/workflows/ci.yml`

**Trigger:** Tất cả PR vào `main`

```
Pipeline:
  1. Lint tất cả packages bị thay đổi
  2. Chạy unit tests (nếu có)
  3. Xác minh build (frontend + customer)
  4. Test build Docker (backend — chỉ build, không push)
```

#### 1.6 — Script Hỗ Trợ

##### [NEW] `infra/scripts/setup-server.sh`

Script khởi tạo server lần đầu:
- Cài Docker + Docker Compose
- Cấu hình UFW firewall (22, 80, 443)
- Tạo Swap 4GB cho Droplet 2GB
- Cài Nginx + Certbot
- Tạo thư mục `/opt/minimart`

##### [NEW] `infra/scripts/deploy.sh`

Script deploy trên Droplet:
```bash
#!/bin/bash
cd /opt/minimart
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
sleep 30
node scripts/healthcheck.js || echo "⚠️ Một số service không qua health check"
docker system prune -f
```

##### [MODIFY] `backend/scripts/healthcheck.js`

- Thêm `statistics` vào mảng SERVICES (hiện đang thiếu)
- Thêm exit code 1 khi có service DOWN (cho CI/CD)

---

### Phase 2: BACKUP — Sao Lưu & Chuẩn Bị Rollback

> Mục tiêu: Đảm bảo có phương án quay lại nếu deployment thất bại.

| Hạng mục | Hành động | Chi tiết |
|----------|-----------|---------|
| **Git tag** | Gắn tag trước deploy | `git tag v1.0.0-pre-deploy` |
| **Docker images** | Giữ image cũ | Không xóa image tagged `latest` cũ cho tới khi verify xong |
| **Database** | Backup Supabase | Export backup từ Supabase Dashboard trước khi deploy |
| **Env files** | Sao lưu trên server | `cp /opt/minimart/.env /opt/minimart/.env.bak` |
| **Rollback plan** | Chuẩn bị sẵn | Quay về image Docker cũ nếu service lỗi |

**Chiến lược Rollback:**

| Triệu chứng | Hành động |
|-------------|-----------|
| Service DOWN hoàn toàn | Rollback ngay lập tức về image cũ |
| Lỗi nghiêm trọng trong logs | Rollback |
| Hiệu năng giảm >50% | Cân nhắc rollback |
| Lỗi nhỏ | Fix forward nếu nhanh, nếu không thì rollback |

---

### Phase 3: DEPLOY — Triển Khai Lên Production

> Mục tiêu: Thực thi deployment với monitoring sẵn sàng.

Tham chiếu: [deploy.md — Giai đoạn 2 & 3](file:///e:/UIT/backend/docs/deploy.md)

#### 3.1 — Cấu hình GitHub Secrets & Packages

1. Vào Repo → Settings → Secrets and variables → Actions → Thêm:
   - `DO_HOST` — IP của Droplet
   - `DO_SSH_KEY` — SSH private key
   - `DO_SSH_USER` — User SSH (mặc định: `root`)
2. Vào trang **Packages** trên GitHub → chuyển Visibility của **toàn bộ image** (auth, catalog, inventory, chatbot...) sang **Public**

#### 3.2 — Thiết lập Vercel Monorepo (2 Project riêng biệt)

> [!IMPORTANT]
> **Bắt buộc tạo 2 Project Vercel riêng biệt.** Nếu chỉ tạo 1 Project trỏ vào thư mục gốc, Vercel sẽ không biết phải build giao diện Admin hay Customer.

**Project 1 — Admin/POS Dashboard:**

| Cấu hình | Giá trị |
|----------|---------|
| Import Repository | `PhatNguyenTT2/Mini-Mart` |
| Root Directory | Chọn **Edit** → trỏ vào `frontend/` |
| Framework Preset | **Vite** |
| Environment Variable | `VITE_API_URL` = `https://api.mini-mart.dev` |
| Custom Domain | `admin.mini-mart.dev` |

**Project 2 — Customer Web:**

| Cấu hình | Giá trị |
|----------|---------|
| Import Repository | `PhatNguyenTT2/Mini-Mart` (import lại lần nữa) |
| Root Directory | Chọn **Edit** → trỏ vào `customer/` |
| Framework Preset | **Vite** |
| Environment Variable | `VITE_API_URL` = `https://api.mini-mart.dev` |
| Custom Domain | `shop.mini-mart.dev` |

> [!WARNING]
> Bắt buộc **Redeploy** trên Vercel sau khi set biến môi trường. Khi cấu hình `paths` trong GitHub Actions, thay đổi ở thư mục nào thì Vercel chỉ build lại Project tương ứng.

#### 3.3 — Deploy Backend (GitHub Actions)

1. Tạo file `.env.prod` trực tiếp trên Droplet:
   ```bash
   ssh root@<IP_DROPLET>
   nano /opt/minimart/.env
   # Paste nội dung từ .env.prod.example và điền secret thật
   ```
2. Upload file compose lên server (chỉ lần đầu):
   ```bash
   scp backend/docker-compose.prod.yml root@<IP_DROPLET>:/opt/minimart/
   ```
3. Push code lên `main` branch
4. GitHub Actions tự động trigger `deploy-backend.yml`
5. Pipeline: build images → push ghcr.io → SSH pull + `docker compose up -d`

#### 3.4 — Deploy Frontend (Vercel Auto-deploy)

- Vercel auto-deploy khi push thay đổi vào `frontend/` hoặc `customer/` (mỗi project chỉ build thư mục tương ứng)
- GitHub Actions chạy lint + build verification trước khi merge

---

### Phase 4: VERIFY — Xác Minh Sau Triển Khai

> Mục tiêu: Kiểm tra toàn diện hệ thống sau deploy. Không bỏ qua bước nào.

Tham chiếu: [deploy.md — Giai đoạn 3 & 4](file:///e:/UIT/backend/docs/deploy.md)

#### 4.1 — Kiểm tra Container

```bash
docker ps
```

| Container | Trạng thái mong đợi |
|-----------|-------------------|
| minimart-gateway | Up (Port 8080) |
| minimart-auth | Up |
| minimart-catalog | Up |
| minimart-order | Up |
| minimart-settings | Up |
| minimart-supplier | Up |
| minimart-inventory | Up |
| minimart-payment | Up |
| minimart-chatbot | Up (Load model RAG lâu nhất) |
| minimart-statistics | Up |

> Nếu container ở trạng thái `Restarting`: `docker logs minimart-<service> --tail=50`

#### 4.2 — Kiểm tra Health Endpoints

```bash
node scripts/healthcheck.js
```

Tất cả 9 endpoint `/health/*` + `/ready/*` phải trả về **200 OK**.

#### 4.3 — Kiểm tra Tài Nguyên Server ⚠️ QUAN TRỌNG

```bash
free -h
docker stats --no-stream
```

| Metric | Ngưỡng an toàn | Ngưỡng nguy hiểm | Hành động |
|--------|----------------|-------------------|-----------|
| RAM Used | ~1.8GB - 1.9GB | > 1.95GB | Bình thường trên 2GB |
| Swap Used | < 2.5GB | > 3.5GB | **Scale up ngay** |
| `docker stats` response | < 2s | > 5s hoặc đơ | Hệ thống đang Thrashing |

> [!CAUTION]
> ### Khi nào PHẢI Scale up?
> Do ổ cứng đọc/ghi chậm hơn RAM rất nhiều, khi Swap bị sử dụng quá mức, hệ thống rơi vào trạng thái **"Thrashing"** — CPU tốn toàn bộ thời gian để chép dữ liệu giữa RAM và ổ cứng thay vì xử lý request.
>
> **Dấu hiệu nhận biết:**
> - Lệnh `docker stats` phản hồi cực kỳ chậm (đơ mất vài giây)
> - Swap Used vượt ngưỡng **3.5GB** hoặc liên tục tăng
> - Chatbot AI mất kết nối / lỗi `504 Gateway Timeout`
> - Server mất kết nối SSH
>
> **Xử lý:** Vào DigitalOcean Dashboard → **Tắt Droplet** → **Resize lên 4GB RAM** ($24/tháng)

> [!TIP]
> **Phương án phòng hờ:** Nếu trong quá trình deploy hoặc test luồng Chatbot gặp lỗi 504 hoặc mất SSH, hãy sẵn sàng resize ngay. Không cố khắc phục trên máy 2GB vì vấn đề là phần cứng, không phải phần mềm.

#### 4.4 — Kiểm tra Thủ Công

| # | Kiểm tra | Kết quả mong đợi |
|---|----------|-----------------|
| 1 | `nslookup api.mini-mart.dev` | Trả về IP Droplet |
| 2 | `curl -I https://api.mini-mart.dev/health` | 200 OK + cert hợp lệ |
| 3 | Truy cập `https://admin.mini-mart.dev` | Trang đăng nhập POS |
| 4 | Truy cập `https://shop.mini-mart.dev` | Trang mua sắm |
| 5 | Chatbot WebSocket `wss://api.mini-mart.dev/ws/chat` | Kết nối thành công |
| 6 | CORS test từ domain lạ | Bị chặn |

#### 4.5 — Kiểm tra Log Chatbot

```bash
docker logs minimart-chatbot 2>&1 | grep -i "Loading embedding model"
```

Xác minh model Embedding đã nạp thành công vào Swap.

---

### Phase 5: CONFIRM / ROLLBACK — Xác Nhận Hoặc Quay Lại

> Mục tiêu: Đưa ra quyết định cuối cùng — hệ thống ổn định hay cần rollback.

#### ✅ Nếu TẤT CẢ kiểm tra Phase 4 đều PASS:

1. Xóa backup image cũ: `docker system prune -f`
2. Gắn tag release: `git tag v1.0.0 && git push --tags`
3. Cập nhật tài liệu triển khai
4. Thông báo team deployment thành công

#### ❌ Nếu có vấn đề — Rollback:

```bash
# Trên Droplet (SSH):
cd /opt/minimart
cp .env.bak .env                                      # Khôi phục env cũ
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml pull <image_cũ>
docker compose -f docker-compose.prod.yml up -d
```

| Phương pháp rollback | Khi nào dùng |
|---------------------|-------------|
| **Git revert** | Lỗi code, cần fix nhanh |
| **Image tag cũ** | Pull lại image Docker phiên bản trước |
| **Env restore** | Lỗi do cấu hình môi trường |

---

## Quyết Định Đã Xác Nhận

| # | Câu hỏi | Kết luận | Ảnh hưởng tới Plan |
|---|---------|---------|--------------------|
| 1 | **Secrets `.env` bị lộ?** | ✅ **KHÔNG** — `.gitignore` đã có từ đầu, chưa bao giờ commit | Loại bỏ `PROD_ENV_FILE` khỏi GitHub Secrets. Tạo `.env.prod` trực tiếp trên Droplet. |
| 2 | **Cấu hình Droplet?** | ✅ Đã có Droplet **2GB RAM** + 4GB Swap | Giữ nguyên plan, tăng cường giám sát Swap trong Phase 4.3. Sẵn sàng resize lên 4GB nếu Thrashing. |
| 3 | **Docker Registry?** | ✅ Repo **public** → dùng **ghcr.io** miễn phí | Không cần cấu hình GHCR authentication trên Droplet. |
| 4 | **Vercel Projects?** | ⚠️ Cần tạo **2 project riêng biệt** | Đã bổ sung hướng dẫn chi tiết tại Phase 3.2 (Admin → `frontend/`, Customer → `customer/`). |
| 5 | **VNPay Production?** | ✅ Giữ **chế độ test** (`VNP_TEST_MODE=true`) | Không thay đổi. Chuyển sang production khi go-live chính thức. |

---

## Tóm Tắt File Thay Đổi

| Hành động | File | Mục đích | Phase |
|-----------|------|----------|-------|
| **NEW** | `backend/docker-compose.prod.yml` | Docker Compose production | 1.2 |
| **NEW** | `backend/.env.prod.example` | Template biến môi trường | 1.2 |
| **NEW** | `.github/workflows/deploy-backend.yml` | CI/CD backend | 1.5 |
| **NEW** | `.github/workflows/deploy-frontend.yml` | CI/CD admin/POS | 1.5 |
| **NEW** | `.github/workflows/deploy-customer.yml` | CI/CD customer web | 1.5 |
| **NEW** | `.github/workflows/ci.yml` | Pipeline kiểm tra PR | 1.5 |
| **NEW** | `infra/nginx/api.mini-mart.dev.conf` | Nginx host + SSL | 1.3 |
| **NEW** | `infra/scripts/setup-server.sh` | Script khởi tạo server | 1.6 |
| **NEW** | `infra/scripts/deploy.sh` | Script deploy | 1.6 |
| **MODIFY** | 5× `services/*/src/app.js` | Bảo mật CORS | 1.4 |
| **MODIFY** | `services/chatbot/src/index.js` | Fix Socket.IO CORS | 1.4 |
| **MODIFY** | `backend/gateway/nginx.conf` | Thêm CORS headers, gzip | 1.3 |
| **MODIFY** | `backend/scripts/healthcheck.js` | Thêm statistics, exit codes | 1.6 |
