"""用 yfinance 拉日线行情，并提供按交易日查价的辅助函数。"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import yfinance as yf


def fetch_history(tickers: list[str], start: date, end: date | None = None,
                  verbose: bool = True) -> dict[str, list[dict]]:
    """返回 {ticker: [{date, close, high, low}, ...]}，按日期升序。"""
    if end is None:
        end = date.today()
    # 多留几天缓冲，保证 start 当天/附近能取到交易日
    start_buf = start - timedelta(days=7)
    end_buf = end + timedelta(days=1)
    out: dict[str, list[dict]] = {}
    for t in tickers:
        try:
            df = yf.Ticker(t).history(start=start_buf.isoformat(),
                                      end=end_buf.isoformat(),
                                      auto_adjust=False)
        except Exception as e:
            if verbose:
                print(f"  ! {t} 行情抓取失败：{e}")
            out[t] = []
            continue
        rows = []
        for idx, row in df.iterrows():
            rows.append({
                "date": idx.date().isoformat(),
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
            })
        out[t] = rows
        if verbose:
            tail = rows[-1]["date"] if rows else "无数据"
            print(f"  {t}: {len(rows)} 根日线，截至 {tail}")
    return out


def close_on_or_after(series: list[dict], d: date) -> tuple[int, dict] | tuple[None, None]:
    """第一个日期 >= d 的交易日，返回 (下标, 行)。"""
    for i, row in enumerate(series):
        if date.fromisoformat(row["date"]) >= d:
            return i, row
    return None, None


def entry_index(series: list[dict], post_dt: datetime) -> int | None:
    """根据发言时间确定建仓基准交易日下标。

    盘后(美东 16:00 后)发的，基准用下一个交易日；否则用当天或之后第一个交易日。
    """
    eff = post_dt.date()
    if post_dt.hour >= 16:
        eff = eff + timedelta(days=1)
    i, _ = close_on_or_after(series, eff)
    return i
