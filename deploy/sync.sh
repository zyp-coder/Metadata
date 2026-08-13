#!/usr/bin/env bash
# sync.sh - MetaData002 服务器一键同步
# Usage: bash /opt/MetaData002/deploy/sync.sh

cd /opt/MetaData002
git pull origin master
cd frontend && npm run build
cd ../deploy
docker compose up -d --build backend
docker compose exec nginx nginx -s reload