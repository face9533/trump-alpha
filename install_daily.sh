#!/usr/bin/env bash
# 可选：把"每天自动刷新数据"装成 macOS 定时任务（launchd）。
# 默认每天早上 8:00 跑一次 update。装好后电脑开机就会自动更新数据。
#   安装： ./install_daily.sh
#   卸载： ./install_daily.sh uninstall
set -e
cd "$(dirname "$0")"
PROJ="$(pwd)"
LABEL="com.trumpalpha.dailyupdate"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ "$1" = "uninstall" ]; then
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "已卸载每日自动更新。"
  exit 0
fi

mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PROJ/.venv/bin/python</string>
    <string>-m</string><string>pipeline.update</string>
    <string>--days</string><string>60</string>
  </array>
  <key>WorkingDirectory</key><string>$PROJ</string>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>8</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>$PROJ/data/cron.log</string>
  <key>StandardErrorPath</key><string>$PROJ/data/cron.log</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "✅ 已设置每天 08:00 自动刷新数据（日志：data/cron.log）。"
echo "   想改时间就编辑 $PLIST 后重新运行本脚本。"
echo "   取消： ./install_daily.sh uninstall"
