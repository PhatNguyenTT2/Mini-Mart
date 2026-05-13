# 📋 Báo Cáo Tổng Quan — Luồng Deploy POSMART Mini-Mart

> **Trạng thái:** ✅ Toàn bộ luồng deploy đã hoàn tất và hoạt động.
> **Cập nhật lần cuối:** 13/05/2026

---

## Kiến Trúc Triển Khai

```
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub (PhatNguyenTT2/Mini-Mart)             │
│                         Nhánh: main                             │
│                                                                 │
│  backend/**  ──► deploy-backend.yml ──► DigitalOcean Droplet    │
│  frontend/** ──► deploy-frontend.yml ──► Vercel (Admin/POS)     │
│  customer/** ──► deploy-customer.yml ──► Vercel (Customer Web)  │
└─────────────────────────────────────────────────────────────────┘

                        ┌────────────┐
                        │  Name.com  │
                        │ mini-mart  │
                        │   .dev     │
                        └─────┬──────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
  api.mini-mart.dev    admin.mini-mart.dev   shop.mini-mart.dev
    (A Record)            (CNAME)              (CNAME)
         │                    │                    │
         ▼                    ▼                    ▼
  DigitalOcean Droplet     Vercel               Vercel
  2GB RAM + 4GB Swap     frontend/             customer/
         │
         ▼
  Nginx (Host :443)
  SSL + Reverse Proxy
         │
         ▼
  Docker Gateway (:8080)
  CORS + Rate Limit + GZIP
         │
    ┌────┼────┬─────┬─────┬──────┬─────┬──────┬─────┬──────┐
    ▼    ▼    ▼     ▼     ▼      ▼     ▼      ▼     ▼      ▼
  Auth Catalog Order Settings Supplier Inv  Payment Stats Chatbot
  :3001 :3002 :3003  :3004   :3005  :3006  :3007  :3009  :3008
    │     │     │      │       │      │      │      │      │
    ▼     ▼     ▼      ▼       ▼      ▼      ▼      ▼      ▼
  ┌─────────────────┐ ┌──────────────┐ ┌──────────────────────┐
  │ Supabase (Shared)│ │ Supabase     │ │ Redis Cloud + AMQP   │
  │ ap-northeast-2   │ │ (Catalog)    │ │ ap-east-1            │
  └─────────────────┘ │ ap-southeast-2│ └──────────────────────┘
                       └──────────────┘
```

---

## Thành Phần Hệ Thống

### Backend — DigitalOcean Droplet

| Service | Image (GHCR) | Port | RAM Limit | Vai trò |
|---------|-------------|------|-----------|---------|
| **Gateway** | `ghcr.io/.../gateway` | 8080→80 | 150m | Nginx reverse proxy, CORS, rate limit |
| **Auth** | `ghcr.io/.../auth` | 3001 | 250m | Đăng nhập, JWT, phân quyền |
| **Catalog** | `ghcr.io/.../catalog` | 3002 | 250m | Sản phẩm, danh mục (DB riêng) |
| **Order** | `ghcr.io/.../order` | 3003 | 250m | Đơn hàng, POS, Online |
| **Settings** | `ghcr.io/.../settings` | 3004 | 200m | Cấu hình hệ thống |
| **Supplier** | `ghcr.io/.../supplier` | 3005 | 200m | Nhà cung cấp, đơn nhập |
| **Inventory** | `ghcr.io/.../inventory` | 3006 | 250m | Kho hàng, lô hàng |
| **Payment** | `ghcr.io/.../payment` | 3007 | 250m | Thanh toán VNPay |
| **Statistics** | `ghcr.io/.../statistics` | 3009 | 200m | Thống kê, báo cáo |
| **Chatbot** | `ghcr.io/.../chatbot` | 3008 | **1.2g** | AI RAG, Socket.IO, đề xuất |

**Tổng RAM cấp phát:** ~2.4GB (2GB thật + đệm Swap)

### Frontend — Vercel

| Project | Thư mục | Domain | Framework |
|---------|---------|--------|-----------|
| Admin/POS Dashboard | `frontend/` | `admin.mini-mart.dev` | Vite + React 19 + TW4 |
| Customer Web | `customer/` | `shop.mini-mart.dev` | Vite + React 19 + TW3 |

### Dịch Vụ Cloud (Managed)

| Dịch vụ | Nhà cung cấp | Khu vực |
|---------|-------------|---------|
| PostgreSQL (Shared) | Supabase | ap-northeast-2 (Seoul) |
| PostgreSQL (Catalog) | Supabase | ap-southeast-2 (Sydney) |
| Redis | Redis Cloud | ap-east-1 (Hong Kong) |
| RabbitMQ | CloudAMQP | Managed |
| Domain | Name.com | `mini-mart.dev` |

---

## Luồng CI/CD

### 1. Backend Deploy (`deploy-backend.yml`)

```
Push vào main (backend/**)
        │
        ▼
┌─────────────────────────────────────────┐
│  GitHub Actions (ubuntu-latest)         │
│                                         │
│  1. Checkout code                       │
│  2. Lowercase repo name (GHCR yêu cầu) │
│  3. Xác định build context             │
│     ├── gateway → ./backend/gateway     │
│     └── services → ./backend            │
│  4. Login GHCR (GITHUB_TOKEN)           │
│  5. Build 9 images (parallel matrix)    │
│  6. Push → ghcr.io/phatnguyentt2/...    │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  Deploy Job (SSH → Droplet)             │
│                                         │
│  cd /opt/minimart                       │
│  docker compose pull                    │
│  docker compose up -d --remove-orphans  │
│  docker system prune -f                 │
└─────────────────────────────────────────┘
```

**GitHub Secrets:**

| Secret | Mục đích |
|--------|----------|
| `DO_HOST` | IP Droplet |
| `DO_USER` | SSH username (`root`) |
| `DO_SSH_KEY` | SSH private key |

### 2. Frontend Deploy (`deploy-frontend.yml` / `deploy-customer.yml`)

```
Push vào main (frontend/** hoặc customer/**)
        │
        ▼
┌──────────────────────────┐
│  GitHub Actions          │
│  1. npm ci               │
│  2. npm run lint         │
│  3. npm run build        │
│  (Quality gate trước khi │
│   Vercel tự động deploy) │
└──────────────────────────┘
        │
        ▼
  Vercel auto-deploys via GitHub Integration
```

### 3. CI Checks (`ci.yml`)

```
Pull Request vào main
        │
        ▼
  Lint + Build verification (frontend + customer)
  → Block merge nếu thất bại
```

---

## Cấu Hình Server (DigitalOcean Droplet)

### Hạ tầng

| Hạng mục | Cấu hình | Trạng thái |
|----------|---------|-----------|
| **Droplet** | 2GB RAM, 1 vCPU | ✅ Active |
| **Swap** | 4GB (`/swapfile`) | ✅ Persistent (fstab) |
| **Firewall** | UFW: 22, 80, 443 only | ✅ Đã bảo mật |
| **SSL** | Let's Encrypt via Certbot | ✅ Tự gia hạn (hết hạn 10/08/2026) |
| **Reverse Proxy** | Nginx (host) → Docker :8080 | ✅ Hoạt động |
| **Thư mục** | `/opt/minimart` | ✅ Chứa compose + .env |

### Luồng Request

```
Client (HTTPS :443)
  → Nginx Host (SSL termination + WebSocket upgrade)
    → Docker Gateway :8080 (CORS + Rate Limit + GZIP + X-Request-ID)
      → proxy_hide_header (loại bỏ CORS trùng từ Node.js)
        → Service :300x (xử lý business logic)
          → Supabase / Redis / RabbitMQ (Cloud)
```

### Chiến lược CORS (Defense in Depth)

> Bài học thực tế: Header CORS bị nhân đôi (Gateway + Node.js) gây lỗi browser block.

**Giải pháp hiện tại (đã áp dụng):**

| Tầng | Hành động | File |
|------|-----------|------|
| **Gateway (Nginx)** | `proxy_hide_header` loại bỏ CORS từ upstream, rồi tự gắn header chuẩn | `gateway/nginx.conf` |
| **Services (Node.js)** | Vẫn giữ `cors({ origin: allowedOrigins })` làm lớp phòng thủ thứ 2 | `services/*/src/app.js` |
| **Socket.IO** | CORS whitelist thay vì `'*'` | `services/chatbot/src/index.js` |

**Origins được phép:**
- `https://admin.mini-mart.dev`
- `https://shop.mini-mart.dev`
- `http://localhost:5173` (dev)
- `http://localhost:5174` (dev)

---

## Cấu Trúc File Triển Khai

```
Mini-Mart/
├── .github/workflows/
│   ├── deploy-backend.yml      # CI/CD backend → DigitalOcean
│   ├── deploy-frontend.yml     # CI/CD admin → Vercel
│   ├── deploy-customer.yml     # CI/CD customer → Vercel
│   └── ci.yml                  # PR quality gate
│
├── backend/
│   ├── docker-compose.prod.yml # Production orchestration
│   ├── docker-compose.yml      # Dev orchestration
│   ├── .env                    # Dev secrets (gitignored)
│   ├── .env.prod               # Prod secrets (gitignored)
│   ├── .env.prod.example       # Template (committed)
│   ├── gateway/
│   │   ├── nginx.conf          # CORS, Rate Limit, GZIP, Routing
│   │   └── Dockerfile          # Nginx Alpine image
│   ├── services/
│   │   ├── auth/Dockerfile
│   │   ├── catalog/Dockerfile
│   │   ├── order/Dockerfile
│   │   ├── settings/Dockerfile
│   │   ├── supplier/Dockerfile
│   │   ├── inventory/Dockerfile
│   │   ├── payment/Dockerfile
│   │   ├── chatbot/Dockerfile
│   │   └── statistics/Dockerfile
│   └── scripts/
│       └── healthcheck.js      # 9 services + exit code
│
├── infra/scripts/
│   ├── setup-server.sh         # Khởi tạo Droplet lần đầu
│   └── deploy.sh               # Deploy nhanh trên Droplet
│
├── docs/deploy/
│   ├── README.md               # ← Bạn đang đọc file này
│   └── digital-ocean.md        # Hướng dẫn chi tiết từng bước
│
├── frontend/                   # Admin/POS → Vercel
└── customer/                   # Customer Web → Vercel
```

---

## Quản Lý Secrets

| File | Nơi lưu | Có trong Git? | Mục đích |
|------|---------|--------------|----------|
| `backend/.env` | Local dev | ❌ `.gitignored` | Secrets dev |
| `backend/.env.prod` | Local + Droplet | ❌ `.gitignored` | Secrets production |
| `backend/.env.prod.example` | Repo | ✅ Committed | Template tham khảo (không có secret) |
| `/opt/minimart/.env` | Droplet only | — | File thật, Docker Compose đọc |

> **Quy tắc:** Secrets KHÔNG BAO GIỜ đi qua GitHub Actions. File `.env` được tạo trực tiếp trên Droplet.

---

## Giám Sát & Xử Lý Sự Cố

### Lệnh kiểm tra nhanh (Web Console)

| Lệnh | Mục đích |
|-------|---------|
| `docker ps` | Xem trạng thái 10 containers |
| `docker stats --no-stream` | RAM/CPU từng container |
| `free -h` | RAM + Swap tổng thể |
| `docker logs minimart-chatbot --tail=50` | Log chatbot (service nặng nhất) |
| `docker compose -f docker-compose.prod.yml restart <service>` | Restart 1 service |

### Ngưỡng cảnh báo

| Metric | An toàn | Nguy hiểm | Hành động |
|--------|---------|-----------|-----------|
| RAM Used | ~1.8-1.9GB | > 1.95GB | Bình thường (2GB máy) |
| Swap Used | < 2.5GB | **> 3.5GB** | ⚠️ Scale up 4GB RAM |
| `docker stats` response | < 2s | > 5s / đơ | ⚠️ Thrashing — resize ngay |

### Rollback

```bash
# Trên Droplet (Web Console):
cd /opt/minimart
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml pull   # Pull image cũ nếu cần
docker compose -f docker-compose.prod.yml up -d
```

---

## Sự Cố Đã Xảy Ra & Cách Xử Lý

| # | Sự cố | Nguyên nhân | Fix |
|---|-------|------------|-----|
| 1 | GHCR push fail | `github.repository` trả về tên có chữ HOA (`PhatNguyenTT2/Mini-Mart`) | Thêm step `tr '[:upper:]' '[:lower:]'` |
| 2 | Frontend báo "Unable to connect" dù API trả 200 | Header CORS bị nhân đôi (Nginx + Node.js cùng gắn) | Thêm `proxy_hide_header` vào Nginx |
| 3 | Catalog service kết nối sai DB | `docker-compose.prod.yml` không override `DATABASE_URL` | Thêm `environment: DATABASE_URL=${CATALOG_DATABASE_URL}` |

---

## Tài Liệu Liên Quan

| Tài liệu | Đường dẫn | Nội dung |
|-----------|-----------|---------|
| Hướng dẫn chi tiết DigitalOcean | [digital-ocean.md](./digital-ocean.md) | Từng bước cấu hình server |
| Kế hoạch triển khai | [implementation_plan.md](../../implementation_plan.md) | Lộ trình 5 phase |
| Phase 1 chi tiết | [phase1_plan.md](../../phase1_plan.md) | Cấu hình hạ tầng |
