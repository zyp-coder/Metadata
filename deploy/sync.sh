#!/usr/bin/env bash
# sync.sh - MetaData002 服务器一键同步（放在 deploy/ 目录）
# Usage: bash /opt/metadata/deploy/sync.sh
#   1) git pull 拉最新代码
#   2) 构建前端 dist（服务器需 Node/npm；首次自动 npm install）
#   3) 重建并重启后端（镜像内含代码必须 --build；容器启动自带 migrate，模型变更自动生效）
#   4) 重载 Nginx（前端静态文件挂载 dist，reload 即生效）
# 任一步失败即中止（set -e），不会留下半同步状态

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "========================================"
echo "  MetaData002 Server Sync"
echo "  仓库: $REPO_ROOT"
echo "========================================"

# 1. 拉取最新代码（服务器有本地未提交改动会失败，先处理）
echo "[1/4] git pull origin master"
git pull origin master

# 2. 构建前端
echo "[2/4] build frontend (npm run build)"
cd "$REPO_ROOT/frontend"
if [ ! -d node_modules ]; then
    echo "  node_modules 不存在，先 npm install ..."
    npm install
fi
npm run build

# 3. 重建并重启后端（启动命令自带 migrate --noinput）
echo "[3/4] rebuild & restart backend"
cd "$REPO_ROOT/deploy"
if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi
$COMPOSE_CMD up -d --build backend

# 4. 重载 Nginx
echo "[4/4] reload nginx"
$COMPOSE_CMD exec nginx nginx -s reload || $COMPOSE_CMD restart nginx

echo "========================================"
echo "  Sync done."
echo "  验证: $COMPOSE_CMD ps"
echo "========================================"
