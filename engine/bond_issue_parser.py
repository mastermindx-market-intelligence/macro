"""Bounded, deterministic table extraction for two retained SEC FWP formats.

This parser supplies literal issue terms only. Source identity and clocks belong
in bond_issue_terms; it never obtains prices, ratings or security mappings.
"""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal

from bs4 import BeautifulSoup

_LABELS = {
    "issuer": "issuer", "principal amount": "principal_usd",
    "maturity": "maturity_date", "maturity date": "maturity_date",
    "coupon": "coupon_pct", "interest rate": "coupon_pct",
    "price to public": "price_pct", "price to public (issue price)": "price_pct",
    "benchmark treasury": "benchmark", "benchmark": "benchmark",
    "benchmark treasury yield": "benchmark_yield_pct", "benchmark yield": "benchmark_yield_pct",
    "spread to benchmark treasury": "spread_bps", "spread to benchmark": "spread_bps",
    "yield": "yield_pct", "reoffer yield": "yield_pct",
    "trade date": "trade_date", "settlement date": "settlement_date",
    "cusip/isin": "identifiers", "cusip/isin nos.": "identifiers",
    "title of securities": "title",
}
_REQUIRED = frozenset(_LABELS.values()) - {"title"}
_DATE = r"(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}"


def _number(value: str, suffix: str, low: Decimal, high: Decimal) -> str:
    match = re.fullmatch(r"(\d{1,3}(?:\.\d{1,6})?)" + suffix, value)
    if match is None:
        raise ValueError("not an explicit numeric field")
    number = Decimal(match.group(1))
    if not number.is_finite() or not low < number < high:
        raise ValueError("numeric field outside supported bounds")
    return str(number)


def _date(value: str, *, settlement: bool = False) -> str:
    match = re.fullmatch(r"(" + _DATE + r")" + (r"(?: \(T\+\d+\))?" if settlement else ""), value)
    if match is None:
        raise ValueError("not an explicit date")
    return datetime.strptime(match.group(1), "%B %d, %Y").date().isoformat()


def _isin_valid(value: str) -> bool:
    digits = "".join(str(ord(c) - 55) if c.isalpha() else c for c in value)
    total = 0
    for index, digit in enumerate(reversed(digits)):
        n = int(digit) * (2 if index % 2 else 1)
        total += n // 10 + n % 10
    return total % 10 == 0


def _normalize(raw: dict[str, str]) -> dict:
    if set(raw) != _REQUIRED:
        raise ValueError("missing or unexpected tranche fields")
    issuer = raw["issuer"]
    if issuer not in ("Apple Inc.", "HP Inc."):
        raise ValueError("unsupported issuer")
    ids = re.fullmatch(r"([0-9A-Z ]+) / (US[0-9A-Z]{10})", raw["identifiers"])
    if ids is None:
        raise ValueError("malformed security identifiers")
    cusip, isin = ids.group(1).replace(" ", ""), ids.group(2)
    if not re.fullmatch(r"[0-9A-Z]{9}", cusip) or isin[2:11] != cusip or not _isin_valid(isin):
        raise ValueError("security identifiers disagree")
    principal = re.fullmatch(r"\$([1-9]\d{0,2}(?:,\d{3})+)", raw["principal_usd"])
    spread = re.fullmatch(r"\+?(\d{1,4}) [Bb]asis [Pp]oints", raw["spread_bps"])
    if principal is None or spread is None or int(spread.group(1)) > 3000:
        raise ValueError("unsupported principal or spread")
    trade = _date(raw["trade_date"])
    settlement = _date(raw["settlement_date"], settlement=True)
    maturity = _date(raw["maturity_date"])
    tenor = int(maturity[:4]) - int(settlement[:4])
    if not trade <= settlement < maturity or settlement[4:] != maturity[4:] or not 0 < tenor <= 50:
        raise ValueError("not an exact original year tenor")
    benchmark = raw["benchmark"]
    match = re.fullmatch(r"(?:UST )?(\d{1,2}\.\d{1,6})% due (" + _DATE + r")", benchmark)
    if match is None or not 0 < Decimal(match.group(1)) < 30:
        raise ValueError("unsupported benchmark")
    _date(match.group(2))
    result = {
        "issuer": issuer, "cusip": cusip, "isin": isin,
        "coupon_pct": _number(raw["coupon_pct"], r"%(?: per annum)?", Decimal(0), Decimal(30)),
        "yield_pct": _number(raw["yield_pct"], "%", Decimal(0), Decimal(30)),
        "benchmark_yield_pct": _number(raw["benchmark_yield_pct"], "%", Decimal(0), Decimal(30)),
        "price_pct": _number(raw["price_pct"], "%", Decimal(0), Decimal(200)),
        "spread_bps": int(spread.group(1)), "principal_usd": int(principal.group(1).replace(",", "")),
        "trade_date": trade, "settlement_date": settlement, "maturity_date": maturity,
        "tenor_years": tenor, "benchmark": benchmark,
    }
    # principal_usd is the internal input slot inherited by the consumer; the
    # source prints '$', not an ISO code. No currency assertion is returned.
    delta = Decimal(result["yield_pct"]) - Decimal(result["benchmark_yield_pct"])
    if abs(delta - Decimal(result["spread_bps"]) / 100) > Decimal("0.002"):
        raise ValueError("issue spread and yields disagree")
    return result


def parse_issue_terms(content: bytes) -> list[dict]:
    """Return all supported tranches, or no terms on ambiguity or corruption."""
    if not isinstance(content, bytes) or not 0 < len(content) <= 1024 * 1024:
        return []
    try:
        soup = BeautifulSoup(content.decode("utf-8", errors="strict"), "html.parser")
        for node in list(soup.find_all(True)):
            if node.attrs is None:
                continue
            style = re.sub(r"\s+", "", str(node.get("style", "")).lower())
            if (node.name in ("script", "style", "noscript", "template") or node.has_attr("hidden")
                    or str(node.get("aria-hidden", "")).lower() == "true"
                    or "display:none" in style or "visibility:hidden" in style):
                node.decompose()
        fields = []
        for tr in soup.find_all("tr"):
            cells = tr.find_all(["td", "th"], recursive=False)
            if any(cell.find("table") is not None for cell in cells):
                continue
            texts = [" ".join(cell.get_text(" ", strip=True).split()) for cell in cells]
            texts = [text for text in texts if text]
            if len(texts) < 2:
                continue
            label = re.sub(r":?(?:\s*\(\d+\))?\s*$", "", texts[0]).strip().lower()
            key = _LABELS.get(label)
            if key:
                if len(texts) != 2:
                    raise ValueError("ambiguous table columns")
                fields.append((key, texts[1]))
        if not fields or fields[0][0] != "issuer":
            return []
        issuer = fields[0][1]
        raw_groups = []
        current = {}
        common = {}
        for key, value in fields:
            if issuer == "Apple Inc." and key == "issuer":
                if current:
                    raw_groups.append(current)
                current = {}
            elif issuer == "HP Inc." and key == "title":
                if current:
                    raw_groups.append(current)
                current = dict(common)
                continue
            if key == "title":
                raise ValueError("unexpected tranche title")
            target = common if issuer == "HP Inc." and not current else current
            if key in target:
                raise ValueError("duplicate tranche field")
            target[key] = value
        if current:
            raw_groups.append(current)
        expected = {"Apple Inc.": 4, "HP Inc.": 2}.get(issuer)
        if expected is None or len(raw_groups) != expected:
            return []
        result = [_normalize(row) for row in raw_groups]
        if len({row["cusip"] for row in result}) != len(result):
            return []
        return result
    except (UnicodeError, ValueError, TypeError, KeyError, ArithmeticError):
        return []
