"""核心分析：把"发言提及"和"行情"对齐，算出每次喊单以来的表现，
并生成面向前一交易日的每日复盘。"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from . import prices as P


def _pct(a: float, b: float) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return round((a / b - 1) * 100, 2)


def build_mentions(annotated_posts: list[dict],
                   history: dict[str, list[dict]],
                   bench: list[dict] | None = None) -> list[dict]:
    """每条（发言 × 命中股票）生成一条追踪记录。bench 为大盘(标普)日线，用于算超额收益。"""
    records = []
    for post in annotated_posts:
        if not post.get("datetime"):
            continue
        post_dt = datetime.fromisoformat(post["datetime"])
        for mt in post["mentions"]:
            series = history.get(mt["ticker"], [])
            if not series:
                continue
            ei = P.entry_index(series, post_dt)
            if ei is None:
                continue  # 喊单太新，还没有基准交易日（比如今天盘后刚发）
            entry = series[ei]
            latest = series[-1]
            entry_price = entry["close"]

            nxt = series[ei + 1]["close"] if ei + 1 < len(series) else None
            d3 = series[ei + 3]["close"] if ei + 3 < len(series) else None
            wk = series[ei + 5]["close"] if ei + 5 < len(series) else None

            window = series[ei:]
            # 用日内高低算最高浮盈/最大回撤（更贴近真实 K 线）
            max_high = max(r["high"] for r in window)
            min_low = min(r["low"] for r in window)

            return_since = _pct(latest["close"], entry_price)
            # 同期大盘(标普)涨跌 与 超额收益
            bench_since = excess_since = None
            if bench:
                _, b_entry = P.close_on_or_after(bench, date.fromisoformat(entry["date"]))
                if b_entry:
                    bench_since = _pct(bench[-1]["close"], b_entry["close"])
                    if return_since is not None and bench_since is not None:
                        excess_since = round(return_since - bench_since, 2)

            rec = {
                "post_id": post["id"],
                "post_url": post["url"],
                "post_datetime": post["datetime"],
                "post_date": post_dt.date().isoformat(),
                "excerpt": mt.get("context") or (post.get("text") or post.get("card_title") or "")[:280],
                "card_title": post.get("card_title", ""),
                "ticker": mt["ticker"],
                "company": mt["company"],
                "type": mt["type"],
                "sentiment": mt["sentiment"],
                "matched": mt["matched"],
                "entry_date": entry["date"],
                "entry_price": entry_price,
                "latest_date": latest["date"],
                "latest_price": latest["close"],
                "return_since": return_since,
                "return_next_day": _pct(nxt, entry_price),
                "return_3d": _pct(d3, entry_price),
                "return_1w": _pct(wk, entry_price),
                "max_gain": _pct(max_high, entry_price),
                "max_drawdown": _pct(min_low, entry_price),
                "bench_since": bench_since,
                "excess_since": excess_since,
                "days_tracked": (date.fromisoformat(latest["date"])
                                 - date.fromisoformat(entry["date"])).days,
            }
            rec["kline_read"] = _kline_read(rec)
            records.append(rec)
    # 最新喊单排在前
    records.sort(key=lambda r: r["post_datetime"], reverse=True)
    return records


def _kline_read(r: dict) -> str:
    """根据喊单后的价格走势生成一句中文解读。"""
    def f(v):
        return f"{v:+.1f}%" if v is not None else "—"

    since = r["return_since"]
    seq = [("次日", r["return_next_day"]), ("3日", r["return_3d"]),
           ("一周", r["return_1w"]), ("至今", since)]
    metrics = "、".join(f"{name} {f(v)}" for name, v in seq if v is not None)

    tail = []
    if r["max_gain"] is not None:
        tail.append(f"期间最高浮盈 {f(r['max_gain'])}")
    if r["max_drawdown"] is not None and r["max_drawdown"] < 0:
        tail.append(f"最大回撤 {f(r['max_drawdown'])}")
    line = "；".join(x for x in [metrics, "，".join(tail)] if x)

    # 定性
    if since is None:
        verdict = "喊单太新，尚无足够交易日数据。"
    elif since >= 10:
        verdict = "喊单后明显上涨。"
    elif since >= 2:
        verdict = "喊单后小幅走高。"
    elif since > -2:
        verdict = "喊单后基本走平。"
    else:
        verdict = "喊单后不升反跌。"

    exc = r.get("excess_since")
    if exc is not None:
        verdict += f"（同期标普 {f(r.get('bench_since'))}，超额 {f(exc)}）"
    return (line + "。 " + verdict) if line else verdict


def _daily_move(series: list[dict], d: date) -> float | None:
    """某交易日相对前一交易日的涨跌幅(%)。"""
    idx = None
    for i, row in enumerate(series):
        if row["date"] == d.isoformat():
            idx = i
            break
    if idx is None or idx == 0:
        return None
    return _pct(series[idx]["close"], series[idx - 1]["close"])


def summarize(records: list[dict]) -> dict:
    valid = [r for r in records if r["return_since"] is not None]
    if not valid:
        return {"count": 0}
    ups = [r for r in valid if r["return_since"] > 0]
    avg = round(sum(r["return_since"] for r in valid) / len(valid), 2)
    best = max(valid, key=lambda r: r["return_since"])
    worst = min(valid, key=lambda r: r["return_since"])
    # 只看正面情绪喊单的胜率（更贴近"他看好的"）
    bull = [r for r in valid if r["sentiment"] == "positive"]
    bull_ups = [r for r in bull if r["return_since"] > 0]
    # 相对大盘(标普)的超额收益
    ex = [r for r in valid if r["excess_since"] is not None]
    beat = [r for r in ex if r["excess_since"] > 0]
    avg_excess = round(sum(r["excess_since"] for r in ex) / len(ex), 2) if ex else None
    beat_rate = round(len(beat) / len(ex) * 100, 1) if ex else None
    return {
        "count": len(valid),
        "unique_tickers": len(set(r["ticker"] for r in valid)),
        "win_rate": round(len(ups) / len(valid) * 100, 1),
        "avg_return_since": avg,
        "avg_excess_since": avg_excess,
        "beat_market_rate": beat_rate,
        "bull_count": len(bull),
        "bull_win_rate": round(len(bull_ups) / len(bull) * 100, 1) if bull else None,
        "best": {"ticker": best["ticker"], "company": best["company"],
                 "return": best["return_since"]},
        "worst": {"ticker": worst["ticker"], "company": worst["company"],
                  "return": worst["return_since"]},
    }


def daily_review(records: list[dict], history: dict[str, list[dict]],
                 as_of: date, bench: list[dict] | None = None) -> dict:
    """对"前一交易日"(as_of)做复盘。"""
    market_move = _daily_move(bench, as_of) if bench else None
    # 当日新增的喊单
    new_today = [r for r in records if r["post_date"] == as_of.isoformat()]

    # 所有在追踪的股票，当天涨跌
    tracked = {}
    for r in records:
        tracked.setdefault(r["ticker"], r)  # 取最近一次喊单作代表
    movers = []
    for tk, rep in tracked.items():
        mv = _daily_move(history.get(tk, []), as_of)
        if mv is not None:
            movers.append({"ticker": tk, "company": rep["company"],
                           "day_move": mv, "sentiment": rep["sentiment"],
                           "return_since": rep["return_since"]})
    movers.sort(key=lambda x: (x["day_move"] is not None, x["day_move"]), reverse=True)

    up = [m for m in movers if m["day_move"] and m["day_move"] > 0]
    headline = _headline(as_of, new_today, movers, up)
    if market_move is not None:
        headline += f"（当天标普 {market_move:+.2f}%）"
    return {
        "date": as_of.isoformat(),
        "headline": headline,
        "market_move": market_move,
        "new_mentions": [
            {"ticker": r["ticker"], "company": r["company"],
             "sentiment": r["sentiment"], "excerpt": r["excerpt"],
             "post_url": r["post_url"]} for r in new_today
        ],
        "movers": movers,
        "n_up": len(up),
        "n_tracked": len(movers),
    }


def _headline(as_of: date, new_today: list, movers: list, up: list) -> str:
    d = as_of.strftime("%-m月%-d日")
    parts = []
    if new_today:
        names = "、".join(sorted(set(r["company"] for r in new_today)))
        parts.append(f"{d}特朗普新喊到 {len(new_today)} 次（{names}）")
    else:
        parts.append(f"{d}特朗普当天没有新的股票相关发言")
    if movers:
        ratio = f"{len(up)}/{len(movers)}"
        parts.append(f"在追踪的 {len(movers)} 只里 {ratio} 当天上涨")
        if movers[0]["day_move"] is not None:
            top = movers[0]
            parts.append(f"涨幅最大 {top['company']}({top['ticker']}) {top['day_move']:+.2f}%")
    return "；".join(parts) + "。"
