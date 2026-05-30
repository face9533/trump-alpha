#!/usr/bin/env bash
# 把「特朗普喊单追踪」菜单栏插件装成开机自启（macOS LaunchAgent）。
# 装好后：每次登录自动在菜单栏出现 📈，后台常驻托管 http://localhost:8000，
# 并每天自动刷新数据。崩溃会自动重启。
#   安装： ./install_app.sh
#   卸载： ./install_app.sh uninstall
set -e
cd "$(dirname "$0")"
PROJ="$(pwd)"
PY="$PROJ/.venv/bin/python"
LABEL="com.trumpalpha.menubar"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ "$1" = "uninstall" ]; then
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "已卸载菜单栏插件（下次登录不再自启）。当前若在运行，请点菜单栏 📈 → 退出。"
  exit 0
fi

if [ ! -x "$PY" ]; then echo "请先运行 ./setup.sh 安装依赖"; exit 1; fi

mkdir -p "$HOME/Library/LaunchAgents" "$PROJ/data"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PY</string>
    <string>$PROJ/menubar_app.py</string>
  </array>
  <key>WorkingDirectory</key><string>$PROJ</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key>
  <dict><key>SuccessfulExit</key><false/></dict>
  <key>StandardOutPath</key><string>$PROJ/data/app.log</string>
  <key>StandardErrorPath</key><string>$PROJ/data/app.log</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "✅ 已安装并启动。看一眼屏幕右上角菜单栏，应出现 📈 图标。"
echo "   点它 →「打开仪表盘」即可随时查看；数据每天自动刷新。"
echo "   日志：data/app.log   ·   取消自启： ./install_app.sh uninstall"
