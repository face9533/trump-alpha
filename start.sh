#!/usr/bin/env bash
# 启动本地网站。若还没有数据，会先自动刷新一次。
#   ./start.sh          用现有数据直接开（最快）
#   ./start.sh --fresh  先刷新数据再开
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then echo "请先运行 ./setup.sh 安装依赖"; exit 1; fi
source .venv/bin/activate

if [ "$1" = "--fresh" ] || [ ! -f web/data.json ]; then
  echo "==> 刷新数据中（约 1-2 分钟）…"
  python -m pipeline.update --days 60
fi

PORT="${PORT:-8000}"
echo ""
echo "==> 本地网站已启动： http://localhost:$PORT"
echo "   关闭：按 Ctrl+C"
( sleep 1; open "http://localhost:$PORT" >/dev/null 2>&1 || true ) &
cd web && exec python -m http.server "$PORT"
