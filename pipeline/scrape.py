"""抓取特朗普 Truth Social 公开存档（trumpstruth.org）。

策略：用 per_page=50 + cursor 翻页，从最新一路往回，直到超过 since_days 设定的
回溯窗口。每条帖子解析出 id / 时间 / 正文 / 链接卡 / 图片，按 id 去重并增量
合并进 data/posts.json，这样以后每天只需补抓新内容。
"""
from __future__ import annotations

import base64
import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from . import DATA_DIR

BASE = "https://trumpstruth.org/"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
POSTS_FILE = DATA_DIR / "posts.json"


def _decode_cursor(cursor: str) -> dict | None:
    try:
        pad = cursor + "=" * (-len(cursor) % 4)
        return json.loads(base64.urlsafe_b64decode(pad))
    except Exception:
        return None


def _parse_dt(text: str) -> str | None:
    """'May 29, 2026, 11:41 PM' -> ISO 字符串（视为美东时间，naive）。"""
    text = text.strip()
    for fmt in ("%b %d, %Y, %I:%M %p", "%B %d, %Y, %I:%M %p"):
        try:
            return datetime.strptime(text, fmt).isoformat()
        except ValueError:
            continue
    return None


def _parse_page(html: str) -> tuple[list[dict], str | None]:
    """解析一页，返回 (帖子列表, 下一页 cursor)。"""
    soup = BeautifulSoup(html, "lxml")
    posts = []
    # 顶层帖子带 data-status-url；嵌套的转发块没有该属性，自动被排除
    for st in soup.select("div.status[data-status-url]"):
        url = st.get("data-status-url", "").strip()
        m = re.search(r"statuses/(\d+)", url)
        if not m:
            continue
        sid = m.group(1)

        # 作者：原创帖是 Donald J. Trump / @realDonaldTrump；
        # 转发(ReTruth)会显示原作者和原始日期，需区分开
        acct = st.find("a", class_="status-info__account-name")
        account_name = acct.get_text(" ", strip=True) if acct else ""
        handle = ""
        # 时间：href 指向本帖的那个 meta-item；handle：href="#" 的 meta-item
        dt_iso = None
        for a in st.select("a.status-info__meta-item"):
            href = a.get("href") or ""
            if sid in href:
                dt_iso = _parse_dt(a.get_text())
            elif href == "#" and a.get_text(strip=True).startswith("@"):
                handle = a.get_text(strip=True)
        is_trump = handle.lower() == "@realdonaldtrump"

        # 正文：本帖自己的 status__content（document 顺序第一个即顶层帖）
        content_el = st.find("div", class_="status__content")
        text = content_el.get_text(" ", strip=True) if content_el else ""

        # 链接预览卡（常是他转发/引用的新闻标题，对识别公司有用）
        card_title = card_desc = card_domain = ""
        card = st.find("div", class_="status-card__title")
        if card:
            card_title = card.get_text(" ", strip=True)
        d = st.find("div", class_="status-card__description")
        if d:
            card_desc = d.get_text(" ", strip=True)
        ov = st.find("div", class_="status-card__overline")
        if ov:
            card_domain = ov.get_text(" ", strip=True)

        has_image = bool(st.find("div", class_="status-attachment--image"))

        posts.append({
            "id": sid,
            "datetime": dt_iso,
            "account_name": account_name,
            "handle": handle,
            "is_trump": is_trump,
            "url": url.rstrip(),
            "text": text,
            "card_title": card_title,
            "card_description": card_desc,
            "card_domain": card_domain,
            "has_image": has_image,
        })

    # 下一页 cursor
    nxt = None
    next_link = soup.find("a", string=re.compile("Next Page"))
    if not next_link:
        for a in soup.select("a.button"):
            if "Next Page" in a.get_text():
                next_link = a
                break
    if next_link and next_link.get("href"):
        m = re.search(r"cursor=([A-Za-z0-9_\-]+=*)", next_link["href"])
        if m:
            nxt = m.group(1)
    return posts, nxt


def fetch(since_days: int = 45, max_pages: int = 40, per_page: int = 50,
          pause: float = 1.0, verbose: bool = True) -> list[dict]:
    """抓取最近 since_days 天的帖子并合并进本地缓存，返回全部缓存帖子。"""
    DATA_DIR.mkdir(exist_ok=True)
    cache: dict[str, dict] = {}
    if POSTS_FILE.exists():
        for p in json.loads(POSTS_FILE.read_text(encoding="utf-8")):
            cache[p["id"]] = p

    cutoff = datetime.now() - timedelta(days=since_days)
    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    cursor = None
    new_count = 0
    for page in range(max_pages):
        params = {"sort": "desc", "per_page": str(per_page), "removed": "include"}
        if cursor:
            params["cursor"] = cursor
        try:
            r = session.get(BASE, params=params, timeout=30)
            r.raise_for_status()
        except Exception as e:
            if verbose:
                print(f"  ! 第{page+1}页抓取失败：{e}")
            break

        posts, cursor = _parse_page(r.text)
        if not posts:
            break

        for p in posts:
            if p["id"] not in cache:
                new_count += 1
            cache[p["id"]] = p

        # 用 cursor 时间戳（存档插入顺序，即特朗普发/转的时间）作为回溯前沿，
        # 不受转发帖原始日期的干扰
        frontier = None
        cdata = _decode_cursor(cursor) if cursor else None
        if cdata and cdata.get("status_created_at"):
            try:
                frontier = datetime.fromisoformat(cdata["status_created_at"])
            except ValueError:
                frontier = None

        if verbose:
            tail = frontier.date() if frontier else "?"
            n_trump = sum(1 for p in posts if p.get("is_trump"))
            print(f"  第{page+1}页：本页{len(posts)}条(原创{n_trump})，已回溯到 {tail}")

        # 翻到比窗口更早 或 没有下一页 即停
        if frontier and frontier < cutoff:
            break
        if not cursor:
            break
        time.sleep(pause)

    posts_all = sorted(cache.values(),
                       key=lambda p: p["datetime"] or "", reverse=True)
    POSTS_FILE.write_text(json.dumps(posts_all, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    if verbose:
        print(f"  抓取完成：新增 {new_count} 条，缓存共 {len(posts_all)} 条 "
              f"-> {POSTS_FILE.relative_to(DATA_DIR.parent)}")
    return posts_all


if __name__ == "__main__":
    fetch()
