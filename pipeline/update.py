"""主流程：抓取 → 识别喊单 → 拉行情 → 分析复盘 → 写 web/data.json。

用法：
    python -m pipeline.update                # 默认回溯 60 天
    python -m pipeline.update --days 90      # 自定义回溯天数
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime

from . import WEB_DIR, DATA_DIR, scrape, extract, prices as P, analyze


def run(since_days: int = 60, verbose: bool = True, scrape_live: bool = True) -> dict:
    log = print if verbose else (lambda *a, **k: None)

    if scrape_live:
        log("① 抓取特朗普 Truth Social 发言…")
        posts = scrape.fetch(since_days=since_days, verbose=verbose)
    else:
        log("① 复用本地缓存（跳过抓取）…")
        posts = json.loads((scrape.POSTS_FILE).read_text(encoding="utf-8"))

    log("② 识别喊单的股票…")
    own = [p for p in posts if p.get("is_trump")]
    log(f"   共 {len(posts)} 条，其中特朗普原创 {len(own)} 条（转发帖日期不可靠，不计入股价基准）")
    annotated = extract.annotate_posts(own)
    tickers = sorted({m["ticker"] for p in annotated for m in p["mentions"]})
    log(f"   命中 {len(annotated)} 条发言，涉及 {len(tickers)} 只标的：{', '.join(tickers) or '（无）'}")

    history: dict[str, list[dict]] = {}
    records: list[dict] = []
    bench: list[dict] = []
    if tickers:
        earliest = min(datetime.fromisoformat(p["datetime"]).date()
                       for p in annotated if p["datetime"])
        log(f"③ 拉行情（含标普基准，自 {earliest} 起）…")
        history = P.fetch_history(tickers, start=earliest, verbose=verbose)
        bench = P.fetch_history(["SPY"], start=earliest, verbose=verbose).get("SPY", [])
        log("④ 计算自喊单以来的表现 + 大盘超额…")
        records = analyze.build_mentions(annotated, history, bench=bench)

    summary = analyze.summarize(records)
    stats = analyze.analytics(records, history, max_days=10)

    # 复盘基准日 = 最新美股交易日（"前一天"）。优先看股票（加密货币周末也有行情，
    # 会把基准日带到周末，导致复盘只剩币），股票缺失时再退回全体最新日。
    stock_tks = {r["ticker"] for r in records if r["type"] == "stock"}
    as_of = None
    for tk in stock_tks:
        s = history.get(tk) or []
        if s:
            d = date.fromisoformat(s[-1]["date"])
            as_of = d if as_of is None else max(as_of, d)
    if as_of is None:  # 没有股票（只有币）时退回全体最新
        for s in history.values():
            if s:
                d = date.fromisoformat(s[-1]["date"])
                as_of = d if as_of is None else max(as_of, d)
    if as_of is None:
        as_of = date.today()
    review = analyze.daily_review(records, history, as_of, bench=bench)

    # 复盘历史：对最近若干交易日各算一份复盘，累积存档（每天一条，长期保留）
    bench_days = [d["date"] for d in bench][-20:] if bench else [as_of.isoformat()]
    fresh_reviews = [analyze.daily_review(records, history, date.fromisoformat(ds), bench=bench)
                     for ds in bench_days]
    store: dict[str, dict] = {}
    reviews_file = DATA_DIR / "reviews.json"
    if reviews_file.exists():
        try:
            for rv in json.loads(reviews_file.read_text(encoding="utf-8")):
                store[rv["date"]] = rv
        except Exception:
            store = {}
    for rv in fresh_reviews:
        store[rv["date"]] = rv  # 重算则覆盖
    review_history = sorted(store.values(), key=lambda r: r["date"], reverse=True)
    DATA_DIR.mkdir(exist_ok=True)
    reviews_file.write_text(json.dumps(review_history, ensure_ascii=False, indent=2),
                            encoding="utf-8")
    log(f"   复盘历史已存档 {len(review_history)} 天 -> data/reviews.json")

    # 给前端准备每只标的的走势 + 喊单标记
    charts = {}
    for tk, series in history.items():
        marks = sorted({r["entry_date"] for r in records if r["ticker"] == tk})
        charts[tk] = {
            # 完整 OHLC，供前端画 K 线（蜡烛图）
            "series": [{"date": r["date"], "o": r["open"], "h": r["high"],
                        "l": r["low"], "c": r["close"]} for r in series],
            "marks": marks,
        }

    data = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "as_of_date": as_of.isoformat(),
        "window_days": since_days,
        "summary": summary,
        "analytics": stats,
        "daily_review": review,
        "review_history": review_history[:60],
        "mentions": records,
        "charts": charts,
        "config_tickers": tickers,
    }

    WEB_DIR.mkdir(exist_ok=True)
    out = WEB_DIR / "data.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"⑤ 已写入 {out}")
    log(f"\n复盘({as_of})：{review['headline']}")
    if summary.get("count"):
        log(f"近{since_days}天共 {summary['count']} 次喊单，自喊单以来平均 "
            f"{summary['avg_return_since']:+.2f}%，整体胜率 {summary['win_rate']}%")
    return data


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=60, help="回溯天数（默认60）")
    ap.add_argument("--no-scrape", action="store_true", help="跳过抓取，复用本地缓存重算")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    run(since_days=args.days, verbose=not args.quiet, scrape_live=not args.no_scrape)
