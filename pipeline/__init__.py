"""特朗普喊单追踪 —— 数据流水线包。

模块：
  scrape   抓取 Truth Social 公开存档（trumpstruth.org）
  extract  从发言里识别提及的股票/加密货币
  prices   用 yfinance 拉行情
  analyze  计算自喊单以来的表现 + 生成每日复盘
  update   主流程，串起以上并输出 web/data.json
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
WEB_DIR = ROOT / "web"
