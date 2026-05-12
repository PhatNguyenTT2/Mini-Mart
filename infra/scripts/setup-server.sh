#!/bin/bash
set -e

echo "======================================"
echo " POSMART - Khởi tạo Server Droplet "
echo "======================================"

# 1. Cập nhật hệ thống
apt update && apt upgrade -y

# 2. Cài đặt Docker & Docker Compose
if ! command -v docker &> /dev/null; then
    echo "Cài đặt Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    apt install docker-compose-plugin -y
fi

# 3. Cấu hình UFW Firewall
echo "Cấu hình Firewall (UFW)..."
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# 4. Tạo Swap 4GB
if [ ! -f /swapfile ]; then
    echo "Tạo Swap 4GB..."
    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# 5. Cài Nginx + Certbot
if ! command -v nginx &> /dev/null; then
    echo "Cài đặt Nginx & Certbot..."
    apt install -y nginx certbot python3-certbot-nginx
fi

# 6. Tạo thư mục cấu hình
mkdir -p /opt/minimart

echo "✅ Khởi tạo Server thành công!"
