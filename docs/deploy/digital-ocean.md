# 🚦 Hướng Dẫn Triển Khai Hạ Tầng Mini-Mart (DigitalOcean)

> **Tài liệu vận hành** — Cẩm nang từng bước để cấu hình server và verify trạng thái hệ thống.
> Tất cả thao tác sử dụng **DigitalOcean Web Console** (không cần Terminal/SSH client bên ngoài).

---

## Cách Truy Cập Web Console

1. Đăng nhập [DigitalOcean Dashboard](https://cloud.digitalocean.com)
2. Vào **Droplets** → Chọn Droplet Mini-Mart
3. Nhấn nút **Console** (góc phải) → Cửa sổ Web Console mở ra trong trình duyệt
4. Đăng nhập bằng tài khoản `root` + mật khẩu

> [!TIP]
> Web Console hoạt động trực tiếp trên trình duyệt, không cần cài đặt PuTTY hay Terminal. Hữu ích khi cần truy cập khẩn cấp hoặc khi mất kết nối SSH.

---

## Giai Đoạn 1: Chuẩn Bị Server ✅ ĐÃ HOÀN TẤT

> Trạng thái: **Tất cả bước đã được thực hiện thành công.**

### Bước 1.1 — Tạo Swap 4GB ✅

> Bắt buộc để gánh Model AI Chatbot RAG trên máy 2GB RAM.

**Paste vào Web Console:**

```bash
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

**✅ Verify:** Gõ `free -h` trong Web Console

| Kết quả | Ý nghĩa |
|---------|---------|
| Dòng Swap: hiện **4.0G** | ✅ Swap đã hoạt động |
| Dòng Swap: hiện **0B** | ❌ Sai — chạy lại lệnh trên |

---

### Bước 1.2 — Cấu hình Firewall (UFW) ✅

**Paste vào Web Console:**

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
```

**✅ Verify:** Gõ `ufw status` trong Web Console

| Kết quả | Ý nghĩa |
|---------|---------|
| `Status: active` + chỉ port 22, 80, 443 | ✅ Firewall đúng |
| Xuất hiện port 300x hoặc 2375/2376 | ❌ **Nguy hiểm** — Microservices/Docker bị lộ |

> [!CAUTION]
> Nếu thấy port 2375/2376 (Docker daemon), gõ ngay:
> ```bash
> ufw delete allow 2375/tcp
> ufw delete allow 2376/tcp
> ```

---

### Bước 1.3 — Cài đặt Nginx & Cấu hình Reverse Proxy ✅

**Paste vào Web Console (từng khối lệnh):**

**Khối 1 — Cài đặt:**
```bash
apt update && apt install -y nginx certbot python3-certbot-nginx
```

**Khối 2 — Tạo file cấu hình:**
```bash
cat > /etc/nginx/sites-available/api.mini-mart.dev << 'EOF'
server {
    listen 80;
    server_name api.mini-mart.dev;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (Quan trọng cho Chatbot Socket.IO)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}
EOF
```

**Khối 3 — Kích hoạt:**
```bash
ln -sf /etc/nginx/sites-available/api.mini-mart.dev /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

**✅ Verify:** `nginx -t` phải trả về `syntax is ok`

---

### Bước 1.4 — Cài đặt Certbot SSL (Let's Encrypt) ✅

**Paste vào Web Console:**

```bash
certbot --nginx -d api.mini-mart.dev --non-interactive --agree-tos -m <email_của_bạn>
```

**✅ Verify:**
- Mở trình duyệt → Truy cập `https://api.mini-mart.dev`
- Thấy ổ khóa xanh 🔒 + lỗi **502 Bad Gateway** (đúng — Docker chưa bật)
- Chứng chỉ hết hạn: **10/08/2026** (Certbot tự động gia hạn)

---

### Bước 1.5 — Tạo thư mục dự án ✅

**Paste vào Web Console:**

```bash
mkdir -p /opt/minimart
```

**✅ Verify:** `ls /opt/minimart` — thư mục tồn tại và trống.

---

## Giai Đoạn 2: Chuẩn Bị External Services

### 2.1 — GitHub Secrets & Packages

**Trên GitHub (trình duyệt):**

1. Vào Repo `Mini-Mart` → **Settings** → **Secrets and variables** → **Actions**
2. Thêm các secrets:

| Secret | Giá trị |
|--------|---------|
| `DO_HOST` | IP của Droplet |
| `DO_SSH_KEY` | SSH private key |
| `DO_SSH_USER` | `root` |

3. Vào trang **Packages** → Chuyển Visibility của **toàn bộ image** sang **Public**

### 2.2 — Tạo 2 Project Vercel riêng biệt

**Trên Vercel Dashboard (trình duyệt):**

> [!IMPORTANT]
> Bắt buộc tạo **2 Project riêng biệt** vì Monorepo có 2 frontend. Nếu chỉ tạo 1, Vercel không biết build giao diện nào.

**Project 1 — Admin/POS Dashboard:**

| Cấu hình | Giá trị |
|----------|---------|
| Import Repository | `PhatNguyenTT2/Mini-Mart` |
| Root Directory | Nhấn **Edit** → trỏ vào `frontend/` |
| Framework Preset | **Vite** |
| Environment Variable | `VITE_API_URL` = `https://api.mini-mart.dev` |
| Custom Domain | `admin.mini-mart.dev` |

**Project 2 — Customer Web:**

| Cấu hình | Giá trị |
|----------|---------|
| Import Repository | `PhatNguyenTT2/Mini-Mart` (import lại lần nữa) |
| Root Directory | Nhấn **Edit** → trỏ vào `customer/` |
| Framework Preset | **Vite** |
| Environment Variable | `VITE_API_URL` = `https://api.mini-mart.dev` |
| Custom Domain | `shop.mini-mart.dev` |

> [!WARNING]
> Bắt buộc **Redeploy** trên Vercel sau khi set biến môi trường.

### 2.3 — Tạo file .env.prod trên Droplet

**Mở Web Console → Paste:**

```bash
nano /opt/minimart/.env
```

Paste nội dung từ file `backend/.env.prod.example` và điền **secret thật** cho production. Nhấn `Ctrl+X` → `Y` → `Enter` để lưu.

> [!CAUTION]
> File `.env` chứa credential thật. **KHÔNG** commit vào Git hay truyền qua pipeline. Chỉ tạo trực tiếp trên Droplet.

---

## Giai Đoạn 3: First Deploy & Verify

### 3.1 — Upload Docker Compose lên Droplet

**Cách 1 — Qua Web Console (copy-paste nội dung file):**

```bash
nano /opt/minimart/docker-compose.prod.yml
```

Paste toàn bộ nội dung `backend/docker-compose.prod.yml` vào editor → Lưu.

**Cách 2 — Qua SCP (nếu có Terminal local):**

```bash
scp backend/docker-compose.prod.yml root@<IP_DROPLET>:/opt/minimart/
```

### 3.2 — Chạy GitHub Actions Deploy

1. Push code lên `main` branch
2. GitHub Actions tự động trigger `deploy-backend.yml`
3. Pipeline: Build images → Push ghcr.io → SSH pull + `docker compose up -d`

### 3.3 — Verify Containers

**Mở Web Console → Gõ:**

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

> [!WARNING]
> Nếu container ở trạng thái `Restarting`, xem log ngay:
> ```bash
> docker logs minimart-chatbot --tail=50
> ```

---

## Giai Đoạn 4: Monitoring & Giám Sát Sức Khỏe

> ⚠️ Do chạy ép trên 2GB RAM, bước này quyết định việc có cần Scale server hay không.

### 4.1 — Resource Monitoring

**Mở Web Console → Gõ:**

```bash
free -h
```

| Metric | Ngưỡng an toàn | Ngưỡng nguy hiểm | Hành động |
|--------|----------------|-------------------|-----------| 
| RAM Used | ~1.8GB - 1.9GB | > 1.95GB | Bình thường trên 2GB |
| Swap Used | < 2.5GB | > 3.5GB | **Scale up ngay** |

**Kiểm tra chi tiết từng container:**

```bash
docker stats --no-stream
```

| Dấu hiệu | Ý nghĩa |
|-----------|---------|
| Phản hồi < 2s | ✅ Bình thường |
| Phản hồi > 5s hoặc đơ | ❌ Hệ thống đang **Thrashing** |

> [!CAUTION]
> ### Khi nào PHẢI Scale up?
> Nếu `docker stats` phản hồi cực chậm (đơ mất vài giây) và Swap Used > 3.5GB → hệ thống đang **Thrashing** (CPU tốn toàn bộ thời gian chép dữ liệu giữa RAM và ổ cứng).
>
> **Dấu hiệu:**
> - Chatbot AI mất kết nối
> - Lỗi `504 Gateway Timeout`
> - Server mất phản hồi trong Web Console
>
> **Xử lý:** Vào DigitalOcean Dashboard → **Tắt Droplet** → **Resize lên 4GB RAM** ($24/tháng)

### 4.2 — Kiểm tra Log Chatbot AI

**Mở Web Console → Gõ:**

```bash
docker logs minimart-chatbot 2>&1 | grep -i "Loading embedding model"
```

Xác minh model Embedding đã nạp thành công vào Swap.

### 4.3 — Kiểm tra Thủ Công (Trên trình duyệt)

| # | Kiểm tra | Kết quả mong đợi |
|---|----------|-----------------|
| 1 | Truy cập `https://api.mini-mart.dev/health` | 200 OK + ổ khóa xanh |
| 2 | Truy cập `https://admin.mini-mart.dev` | Trang đăng nhập POS |
| 3 | Truy cập `https://shop.mini-mart.dev` | Trang mua sắm |
| 4 | Mở DevTools → Console → Chatbot widget | WebSocket kết nối thành công |
| 5 | Mở DevTools → Network → Gọi API từ domain lạ | CORS bị chặn |

---

## Tóm Tắt Trạng Thái Hiện Tại

| Giai đoạn | Trạng thái | Ghi chú |
|-----------|-----------|---------|
| **1. Chuẩn bị Server** | ✅ **HOÀN TẤT** | Swap, UFW, Nginx, SSL, /opt/minimart |
| **2. External Services** | ✅ **HOÀN TẤT** | GitHub Secrets, Vercel (2 projects), .env.prod |
| **3. First Deploy** | ✅ **HOÀN TẤT** | CI/CD pipeline hoạt động, 10 containers running |
| **4. Monitoring** | ✅ **HOÀN TẤT** | Health checks, resource monitoring |

> [!TIP]
> Xem báo cáo tổng quan tại [README.md](./README.md) để nắm toàn bộ kiến trúc và luồng deploy.