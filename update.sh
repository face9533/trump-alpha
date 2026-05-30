#!/usr/bin/env bash
# 刷新数据：抓取特朗普最新发言 + 拉行情 + 重算复盘，写入 web/data.json。
# 每天跑一次即可（也可用 ./install_daily.sh 设成自动）。
#   ./update.sh         回溯 60 天
#   ./update.sh 90      回溯 90 天
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then echo "请先运行 ./setup.sh 安装依赖"; exit 1; fi
source .venv/bin/activate
python -m pipeline.update --days "${1:-60}"
