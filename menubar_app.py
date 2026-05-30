#!/usr/bin/env python3
"""特朗普喊单追踪 —— Mac 菜单栏插件。

常驻 macOS 菜单栏（顶栏 📈 图标），后台自动：
  · 在 http://localhost:8000 托管仪表盘，随时点开即看；
  · 每天自动刷新一次数据（抓取+复盘），也可手动「立即刷新」。

菜单项：打开仪表盘 / 立即刷新数据 / 数据状态 / 退出。

直接运行：  python menubar_app.py
开机自启：  ./install_app.sh
"""
from __future__ import annotations

import functools
import json
import os
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import rumps

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
DATA = WEB / "data.json"
PORT = int(os.environ.get("PORT", "8000"))
URL = f"http://localhost:{PORT}"
# 公网版（GitHub Pages）。部署后由 install_app/deploy 写入；缺省按约定仓库名。
SITE_URL_FILE = ROOT / "data" / "site_url.txt"


def public_url() -> str | None:
    if SITE_URL_FILE.exists():
        u = SITE_URL_FILE.read_text(encoding="utf-8").strip()
        return u or None
    return None


def _serve():
    """后台线程：托管 web/ 目录。"""
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(WEB))
    # allow_reuse_address 让重启不被 TIME_WAIT 卡住
    ThreadingHTTPServer.allow_reuse_address = True
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    httpd.serve_forever()


class TrumpAlphaApp(rumps.App):
    def __init__(self):
        super().__init__("TrumpAlpha", title="📈", quit_button=None)
        self.refreshing = False
        self.item_open = rumps.MenuItem("打开仪表盘（本机）", callback=self.open_dashboard)
        self.item_site = rumps.MenuItem("打开公网版（分享给朋友）", callback=self.open_site)
        self.item_refresh = rumps.MenuItem("立即刷新数据", callback=self.refresh_clicked)
        self.item_publish = rumps.MenuItem("立即发布到网上", callback=self.publish_clicked)
        self.item_status = rumps.MenuItem("数据：加载中…", callback=None)
        self.item_auto = rumps.MenuItem("每天自动：刷新 + 发布", callback=None)
        self.menu = [
            self.item_open,
            self.item_site,
            None,
            self.item_refresh,
            self.item_publish,
            None,
            self.item_status,
            self.item_auto,
            None,
            rumps.MenuItem("退出", callback=self.quit_clicked),
        ]

        # 启动本地服务器
        threading.Thread(target=_serve, daemon=True).start()
        self._update_status_label()

        # 启动时若数据缺失/过期，先刷一次；之后每 30 分钟检查是否该刷新
        threading.Thread(target=self._refresh_if_stale, daemon=True).start()
        self._timer = rumps.Timer(self._tick, 1800)
        self._timer.start()

    # ---------- 数据状态 ----------
    def _data_info(self):
        try:
            d = json.loads(DATA.read_text(encoding="utf-8"))
            gen = d.get("generated_at", "")
            gen_dt = datetime.fromisoformat(gen) if gen else None
            return {
                "gen": gen[:16].replace("T", " "),
                "gen_date": gen_dt.date() if gen_dt else None,
                "asof": d.get("as_of_date", "?"),
                "count": d.get("summary", {}).get("count", "?"),
            }
        except Exception:
            return None

    def _update_status_label(self):
        info = self._data_info()
        if not info:
            self.item_status.title = "数据：尚未生成，请点「立即刷新」"
        elif self.refreshing:
            self.item_status.title = "数据：正在刷新…"
        else:
            self.item_status.title = f"更新于 {info['gen']} · {info['count']} 条喊单（基准 {info['asof']}）"

    # ---------- 刷新 ----------
    def _run_update(self):
        if self.refreshing:
            return
        self.refreshing = True
        self.title = "📈…"
        self._update_status_label()
        try:
            subprocess.run(
                [sys.executable, "-m", "pipeline.update", "--days", "60"],
                cwd=str(ROOT), timeout=900,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass
        finally:
            self.refreshing = False
            self.title = "📈"
            self._update_status_label()
        # 刷新成功后自动发布到 GitHub Pages（若已部署）
        self._publish()

    def _publish(self):
        """把最新 web/ 推到 GitHub，触发 Pages 重新部署。未配置远程则跳过。"""
        try:
            remote = subprocess.run(["git", "remote"], cwd=str(ROOT),
                                    capture_output=True, text=True, timeout=15).stdout.strip()
            if not remote:
                return
            subprocess.run(["git", "add", "web/data.json", "web/index.html",
                            "web/app.js", "web/styles.css"], cwd=str(ROOT), timeout=30)
            if subprocess.run(["git", "diff", "--cached", "--quiet"],
                              cwd=str(ROOT)).returncode == 0:
                return  # 无变化
            subprocess.run(["git", "commit", "-q", "-m",
                            f"data update {datetime.now():%Y-%m-%d %H:%M}"],
                           cwd=str(ROOT), timeout=30,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "push", "-q"], cwd=str(ROOT), timeout=120,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def _refresh_if_stale(self):
        info = self._data_info()
        today = datetime.now().date()
        if info is None or info["gen_date"] != today:
            self._run_update()

    def _tick(self, _timer):
        """每 30 分钟：若今天还没刷新过且已过早上 7 点，刷新一次。"""
        info = self._data_info()
        now = datetime.now()
        if not self.refreshing and now.hour >= 7 and (info is None or info["gen_date"] != now.date()):
            threading.Thread(target=self._run_update, daemon=True).start()

    # ---------- 菜单回调 ----------
    def open_dashboard(self, _):
        webbrowser.open(URL)

    def open_site(self, _):
        u = public_url()
        if u:
            webbrowser.open(u)
        else:
            rumps.notification("特朗普喊单追踪", "公网版还没部署",
                               "在项目里运行一次性部署，之后这里就能直接打开分享链接。")

    def refresh_clicked(self, _):
        threading.Thread(target=self._run_update, daemon=True).start()
        rumps.notification("特朗普喊单追踪", "开始刷新数据",
                           "抓取+复盘约 1-2 分钟，完成后会自动发布到网上。")

    def publish_clicked(self, _):
        threading.Thread(target=self._publish, daemon=True).start()
        rumps.notification("特朗普喊单追踪", "正在发布到网上",
                           "推送到 GitHub，约 1 分钟后公网链接更新。")

    def quit_clicked(self, _):
        rumps.quit_application()


if __name__ == "__main__":
    TrumpAlphaApp().run()
