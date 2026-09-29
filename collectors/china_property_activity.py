"""NBS origin-published property activity; the existing ChinaPropertyAdapter owns it.

YTD growth is not monthly growth; inventory is an end-month stock. Store the
observed publication time and response hash, never an invented release vintage.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import pandas as pd

INDEX = "https://www.stats.gov.cn/sj/zxfb/"
TITLE = re.compile(r"(20\d{2})年1[—－–-](\d{1,2})月份全国房地产(?:市场基本情况|开发投资和销售情况)")
FIELDS = {
    "房地产开发投资（亿元）": ("investment", "cny100m"),
    "房屋施工面积（万平方米）": ("construction", "sqm10k"),
    "房屋新开工面积（万平方米）": ("starts", "sqm10k"),
    "房屋竣工面积（万平方米）": ("completions", "sqm10k"),
    "新建商品房销售面积（万平方米）": ("sales_area", "sqm10k"),
    "商品房销售面积（万平方米）": ("sales_area", "sqm10k"),
    "二手房交易网签面积（万平方米）": ("resale_area", "sqm10k"),
    "新建商品房销售额（亿元）": ("sales_value", "cny100m"),
    "商品房销售额（亿元）": ("sales_value", "cny100m"),
    "商品房待售面积（万平方米）": ("inventory", "sqm10k"),
    "房地产开发企业本年到位资金（亿元）": ("funds", "cny100m"),
    "其中：国内贷款": ("domestic_loans", "cny100m"),
    "个人按揭贷款": ("mortgages", "cny100m"),
    "定金及预收款": ("deposits", "cny100m"),
    "自筹资金": ("self_funding", "cny100m"),
}
REQUIRED = {"investment_ytd_yoy", "sales_area_ytd_yoy", "starts_ytd_yoy", "funds_ytd_yoy"}


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text).replace("(", "（").replace(")", "）")


def origin_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "www.stats.gov.cn" or not parsed.path.startswith("/sj/") or parsed.username or parsed.password:
        raise ValueError("NBS property source must remain on approved origin/path")
    return url


def release_links(html: str) -> list[tuple[str, tuple[int, int]]]:
    links = {}
    for a in BeautifulSoup(html, "html.parser").select("a[href]"):
        m = TITLE.search(compact(a.get("title", "") + a.get_text("", strip=True)))
        if not m:
            continue
        year, month = int(m[1]), int(m[2])
        if 2 <= month <= 12:
            links[origin_url(urljoin(INDEX, a["href"]))] = (year, month)
    return sorted(links.items(), key=lambda x:x[1], reverse=True)


def number(text: str):
    text = compact(text).replace(",", "").replace("，", "").replace("−", "-")
    if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", text):
        return None
    value = float(text)
    return value if abs(value) < 1e15 else None


def parse_release(html: str, url: str, *, observed_at: datetime | None = None) -> pd.DataFrame:
    origin_url(url)
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("meta", attrs={"name":"ArticleTitle"})
    heading = title.get("content", "") if title else soup.title.get_text() if soup.title else ""
    match = TITLE.search(compact(heading))
    if not match:
        raise ValueError("NBS property title/reference-month contract changed")
    year, month = int(match[1]), int(match[2])
    if not 2 <= month <= 12:
        raise ValueError("NBS YTD property release must be February through December")
    reference = pd.Timestamp(year, month, 1)
    pub = soup.find("meta", attrs={"name":"PubDate"})
    if not pub or not pub.get("content"):
        raise ValueError("NBS publication timestamp missing")
    published = pd.Timestamp(pub["content"])
    if published.tzinfo is None:
        published = published.tz_localize("Asia/Shanghai")
    else:
        published = published.tz_convert("Asia/Shanghai")
    now = pd.Timestamp(observed_at or datetime.now(timezone.utc))
    if now.tzinfo is None:
        now = now.tz_localize("UTC")
    if published > now+pd.Timedelta(minutes=5) or published.tz_localize(None) < reference+pd.offsets.MonthEnd(0):
        raise ValueError("NBS publication/reference chronology invalid")
    values = {}
    for table in soup.select("table"):
        text = compact(table.get_text("", strip=True))
        if "房地产开发投资（亿元）" not in text or "房屋新开工面积（万平方米）" not in text:
            continue
        for tr in table.select("tr"):
            cells = tr.find_all(["td", "th"], recursive=False)
            if len(cells) != 3:
                continue
            label = compact(cells[0].get_text("", strip=True))
            if label not in FIELDS:
                continue
            stem, unit = FIELDS[label]
            period = "stock" if stem == "inventory" else "ytd"
            key = f"{stem}_{period}_yoy"
            if key in values:
                raise ValueError("duplicate national property metric: "+key)
            absolute, growth = number(cells[1].get_text()), number(cells[2].get_text())
            values[key] = growth
            values[f"{stem}_{period}_{unit}"] = absolute
        break
    if not REQUIRED <= values.keys() or any(values[k] is None for k in REQUIRED):
        raise ValueError("NBS national table missing core metrics")
    for key, value in values.items():
        if value is not None and ((key.endswith("_yoy") and value < -100) or (not key.endswith("_yoy") and value < 0)):
            raise ValueError("NBS property impossible value: "+key)
    values.update(source_url=url, publication_time=published.isoformat(), observed_at=now.isoformat(),
        source_sha256=hashlib.sha256(html.encode()).hexdigest(), period_start=f"{year}-01-01",
        period_end=(reference+pd.offsets.MonthEnd(0)).date().isoformat(),
        vintage_status="current_published_revision_not_original_vintage")
    return pd.DataFrame([values], index=pd.DatetimeIndex([reference], name="date"))


def fetch_activity(http_get, *, full_history: bool = False) -> pd.DataFrame:
    """Bounded latest-release ingestion; no silent fallback to an older release."""
    headers = {"User-Agent":"Mozilla/5.0", "Referer":INDEX}
    response = http_get(INDEX, timeout=20, retries=2, headers=headers)
    response.raise_for_status()
    if getattr(response, "url", None):
        origin_url(response.url)
    response.encoding = "utf-8"
    links = release_links(response.text)
    if not links:
        raise ValueError("NBS index has no matching property releases")
    frames = []
    for url, period in links[:6 if full_history else 1]:
        response = http_get(url, timeout=20, retries=2, headers=headers)
        response.raise_for_status()
        if getattr(response, "url", None):
            origin_url(response.url)
        response.encoding = "utf-8"
        frame = parse_release(response.text, url)
        actual = (frame.index[0].year, frame.index[0].month)
        if actual != period:
            raise ValueError("NBS index and article reference periods disagree")
        frames.append(frame)
    result = pd.concat(frames).sort_index()
    if result.index.has_duplicates:
        raise ValueError("Multiple NBS revisions for one month require reconciliation")
    return result
