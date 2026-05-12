#!/bin/bash
set -e

cd /opt/minimart

echo "1. Pulling latest images from GHCR..."
docker compose -f docker-compose.prod.yml pull

echo "2. Starting containers..."
docker compose -f docker-compose.prod.yml up -d

echo "3. Waiting for services to initialize..."
sleep 30

echo "4. Running health checks..."
# Using the healthcheck script from the order container (or any container that has it)
# Or run it via node locally if node is installed on Droplet
if docker exec minimart-auth node scripts/healthcheck.js; then
    echo "✅ Deployment successful."
else
    echo "⚠️ Một số service không qua health check"
fi

echo "5. Cleaning up old images..."
docker system prune -f
