#!/usr/bin/env bash
# 把最新数据发布到 GitHub Pages（朋友看到的公网版本）。
# push 到 GitHub 后，Actions 会自动重新部署，约 1 分钟线上更新。
#   ./publish.sh           只发布现有数据
#   ./publish.sh --fresh   先刷新数据再发布
set -e
cd "$(dirname "$0")"

if [ "$1" = "--fresh" ]; then
  echo "==> 先刷新数据…"
  ./update.sh
fi

if ! git rev-parse --git-dir >/dev/null 2>&1 || ! git remote | grep -q .; then
  echo "❌ 还没连上 GitHub 仓库。请先完成一次性部署设置。"
  exit 1
fi

git add web/data.json web/index.html web/app.js web/styles.css
if git diff --cached --quiet; then
  echo "（线上已是最新，无需发布）"
  exit 0
fi
git commit -q -m "数据更新 $(date '+%Y-%m-%d %H:%M')"
git push -q
echo "✅ 已推送。约 1 分钟后线上自动更新。"
git remote get-url origin 2>/dev/null | sed -E 's#git@github.com:#https://github.com/#; s#\.git$##' | \
  awk -F/ '{print "   公网链接： https://"$4".github.io/"$5"/"}'
