#!/usr/bin/env bash
# 首次安装：创建 Python 虚拟环境并装依赖。只需运行一次。
set -e
cd "$(dirname "$0")"

echo "==> 创建虚拟环境 .venv"
python3 -m venv .venv
source .venv/bin/activate

echo "==> 安装依赖"
pip install --upgrade pip -q
pip install -q -r requirements.txt

echo ""
echo "✅ 安装完成。"
echo "   刷新数据： ./update.sh"
echo "   启动网站： ./start.sh   然后浏览器打开 http://localhost:8000"
