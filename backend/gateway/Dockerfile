# ============================================================
# POSMART API GATEWAY — Nginx Alpine Container
# Chỉ ~25MB, chứa sẵn rules rate-limiting + CORS + routing
# ============================================================
FROM nginx:alpine

# Xóa config mặc định
RUN rm /etc/nginx/nginx.conf

# Copy cấu hình chuẩn của dự án
COPY nginx.conf /etc/nginx/nginx.conf

# Container lắng nghe port 80
EXPOSE 80

# Health check cho Docker
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost/health || exit 1

# Chạy Nginx foreground
CMD ["nginx", "-g", "daemon off;"]
