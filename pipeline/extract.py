"""从发言文本里识别提及的股票 / 加密货币，并粗判情绪倾向。

- 显式 cashtag：$AAPL、$TRUMP 这类直接命中。
- 公司名/别名：按 config/companies.json 的 aliases 做词边界匹配。
- 情绪：在命中词附近的窗口里数正/负面词，给出 positive / negative / neutral。
  （特朗普"夸"的多半看涨，"骂/加关税"的多半看跌——情绪只是辅助标签，不替你做决策。）
"""
from __future__ import annotations

import json
import re

from . import CONFIG_DIR

_CFG = None

# 链接/域名：公司名常出现在 URL 里（stocks.apple.com、amazon.com 买书链接等），
# 这类不是真喊单。匹配前把 URL 替换成等长空格，既不误命中、又不影响摘录定位。
_URL_RE = re.compile(
    r"https?://\S*"
    r"|www\.\S*"
    r"|\b[\w-]+\.(?:com|org|net|gov|io|co|us|edu|info|tv|app|ai|xyz|news|gg)\b(?:/[^\s]*)?",
    re.I,
)


def _strip_urls(text: str) -> str:
    return _URL_RE.sub(lambda m: " " * len(m.group(0)), text)


_SLUG_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/_.-")


def _in_url_slug(text: str, span: tuple[int, int]) -> bool:
    """命中词是否落在 URL 路径/长 slug 里（存档常把链接用空格拆断，
    残留的路径片段如 'cadillac-and-boeing-join-forces' 会被这里拦下）。"""
    i, j = span
    while i > 0 and text[i - 1] in _SLUG_CHARS:
        i -= 1
    while j < len(text) and text[j] in _SLUG_CHARS:
        j += 1
    run = text[i:j]
    return ("/" in run) or (len(run) > 30)


_MODEL_RE = re.compile(r"\s+\d{2,4}\b")


def _is_product_model(text: str, span: tuple[int, int]) -> bool:
    """公司名后紧跟 2-4 位数字 → 多半是机型/产品号引用（如 'Boeing 757'），非投资信号。"""
    return bool(_MODEL_RE.match(text[span[1]:span[1] + 6]))


def _load_config():
    global _CFG
    if _CFG is None:
        cfg = json.loads((CONFIG_DIR / "companies.json").read_text(encoding="utf-8"))
        compiled = []
        for c in cfg["companies"]:
            patterns = []
            for alias in c["aliases"]:
                if alias.startswith("$"):
                    # cashtag：$TRUMP 这种
                    patterns.append(re.compile(r"\$" + re.escape(alias[1:]) + r"\b", re.I))
                else:
                    patterns.append(re.compile(r"\b" + re.escape(alias) + r"\b", re.I))
            compiled.append({
                **c,
                "patterns": patterns,
                "require_context": [w.lower() for w in c.get("require_context", [])],
            })
        cfg["compiled"] = compiled
        cfg["pos"] = set(w.lower() for w in cfg["positive_words"])
        cfg["neg"] = set(w.lower() for w in cfg["negative_words"])
        _CFG = cfg
    return _CFG


def _context(text: str, span: tuple[int, int], width: int = 170) -> str:
    """截取命中词附近的一段上下文，让摘录与该公司相关。"""
    lo = max(0, span[0] - width // 2)
    hi = min(len(text), span[1] + width // 2)
    snippet = text[lo:hi].strip()
    if lo > 0:
        snippet = "…" + snippet
    if hi < len(text):
        snippet = snippet + "…"
    return snippet


def _sentiment(text: str, span: tuple[int, int], cfg) -> str:
    lo = max(0, span[0] - 120)
    hi = min(len(text), span[1] + 120)
    window = text[lo:hi].lower()
    words = re.findall(r"[a-z'&\-]+", window)
    pos = sum(1 for w in words if w in cfg["pos"])
    neg = sum(1 for w in words if w in cfg["neg"])
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def detect(text: str, card_title: str = "", card_description: str = "") -> list[dict]:
    """返回该条发言命中的股票列表（已按 ticker 去重）。"""
    cfg = _load_config()
    # 检测文本：正文权重最高，链接卡标题/摘要作为补充信号
    display_text = " \n ".join(filter(None, [text, card_title, card_description]))
    if not display_text.strip():
        return []
    # 用于匹配的文本：剥掉 URL（等长替换，偏移量不变，摘录仍按 display_text 取）
    search_text = _strip_urls(display_text)

    hits: dict[str, dict] = {}
    for c in cfg["compiled"]:
        first_match = None
        matched_alias = None
        for pat in c["patterns"]:
            for m in pat.finditer(search_text):
                # 命中词落在 URL 路径/长 slug 里、或后跟机型号的，跳过
                if _in_url_slug(search_text, m.span()) or _is_product_model(search_text, m.span()):
                    continue
                # 歧义别名（如 Intel=情报/英特尔）：命中词附近须出现行业语境词
                if c["require_context"]:
                    lo = max(0, m.start() - 90)
                    hi = min(len(search_text), m.end() + 90)
                    win = search_text[lo:hi].lower()
                    if not any(w in win for w in c["require_context"]):
                        continue
                if first_match is None or m.start() < first_match.start():
                    first_match = m
                    matched_alias = m.group(0)
                break  # 该别名取最早一个通过语境校验的命中即可
        if first_match is None:
            continue
        # 情绪以正文为准：命中点在正文范围内才算，否则中性
        in_body = first_match.start() < len(text)
        sentiment = _sentiment(text, first_match.span(), cfg) if in_body else "neutral"
        hits[c["ticker"]] = {
            "ticker": c["ticker"],
            "company": c["name"],
            "type": c["type"],
            "matched": matched_alias,
            "in_body": in_body,
            "sentiment": sentiment,
            "context": _context(display_text, first_match.span()),
        }
    return list(hits.values())


def annotate_posts(posts: list[dict]) -> list[dict]:
    """给每条帖子加上 mentions 字段，只保留有命中的。"""
    out = []
    for p in posts:
        mentions = detect(p.get("text", ""), p.get("card_title", ""),
                          p.get("card_description", ""))
        if mentions:
            out.append({**p, "mentions": mentions})
    return out


if __name__ == "__main__":
    samples = [
        "Tesla is doing GREAT under Elon, tremendous company, best cars!",
        "Boeing is a DISASTER, failing badly. Sad!",
        "Just had a wonderful meeting. MAGA!",
        "I love Truth Social and DJT, incredible platform!",
    ]
    for s in samples:
        print(s[:50], "=>", detect(s))
