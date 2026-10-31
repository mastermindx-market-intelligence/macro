"""Read-only, source-bound IPO terms and a retrospective per-deal price path.

The existing IPO cache holds retained SEC bytes/receipts. This consumer does not
fetch, discover a replacement prospectus, infer float, or calculate lockup expiry.
Unsupported prose is unavailable rather than a standard 180-day assumption.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from decimal import Decimal

from bs4 import BeautifulSoup

from engine.fundamental_forensics.models import canonical_json
from engine.fundamental_forensics.sec_document_spine import (
    archive_document_url, archive_receipt_from_json_bytes, sec_document_id,
)

MAX_BYTES = 8 * 1024 * 1024


def _single(pattern: str, text: str):
    matches = set(re.findall(pattern, text, re.I))
    return next(iter(matches)) if len(matches) == 1 else None


def parse_terms(content: bytes) -> dict:
    """Qualify one supported final Class A IPO form; preserve its conditions."""
    unavailable = {"status": "unavailable", "reason": "unsupported_or_conflicting_terms"}
    if not isinstance(content, bytes) or not content or len(content) > MAX_BYTES:
        return unavailable
    soup = BeautifulSoup(content, "html.parser")
    for node in soup.select("script,style,noscript,template,[hidden],[aria-hidden='true']"):
        node.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()
    # Require an actual priced IPO statement, not a marketed range or follow-on.
    if "This is an initial public offering of shares of Class A common stock" not in text:
        return unavailable
    issuer = _single(r"This is an initial public offering of shares of Class A common stock by (.{1,160}?) We are offering", text)
    shares = _single(r"We are offering ([\d,]+) shares of Class A common stock and the selling stockholders identified in this prospectus are offering ([\d,]+) shares of Class A common stock", text)
    price = _single(r"The initial public offering price is \$([\d,]+\.\d{2}) per share\.", text)
    option = _single(r"We have granted the underwriters an option for a period of (\d+) days to purchase up to ([\d,]+) additional shares of Class A common stock to cover over-allotments\.", text)
    listing = _single(r"approved for listing on the New York Stock Exchange.{0,40}?under the symbol [“\"]([A-Z.]{1,10})[”\"]", text)
    lockup = _single(r"period ending on the earlier of \(i\) the date that is the second trading day after we publicly announce our earnings for the quarter ending ([A-Za-z]+ \d{1,2}, \d{4}) and \(ii\) the date that is (\d+) days after the date of this prospectus", text)
    employee = _single(r"if the stockholder is an employee of ours and is not a selling stockholder in this offering or an officer as defined under Section 16 of the Exchange Act, then on the date that is the second trading day after we publicly announce our earnings for the quarter ending ([A-Za-z]+ \d{1,2}, \d{4}), (\d+)% of the aggregate number", text)
    waiver = "J.P. Morgan Securities LLC may waive the requirements of the lock-up agreements at any time in its sole discretion" in text
    if not all((issuer, shares, price, option, listing, lockup, employee, waiver)):
        return unavailable
    numbers = [*shares, option[1], price.split(".")[0]]
    if any(not re.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+)", n) for n in numbers):
        return unavailable
    try:
        primary, secondary = (int(v.replace(",", "")) for v in shares)
        amount = Decimal(price.replace(",", ""))
        quarter = datetime.strptime(lockup[0], "%B %d, %Y").date().isoformat()
        employee_quarter = datetime.strptime(employee[0], "%B %d, %Y").date().isoformat()
    except (ValueError, ArithmeticError):
        return unavailable
    if not (primary > 0 and secondary > 0 and amount > 0 and 0 < int(employee[1]) < 100):
        return unavailable
    return {
        "status": "qualified", "ticker": listing, "issuer": issuer, "security_class": "Class A common stock",
        "offer_price": str(amount), "primary_shares": primary, "secondary_shares": secondary,
        "base_shares": primary + secondary,
        "option_days": int(option[0]), "option_max_shares": int(option[1].replace(",", "")),
        "option_exercised": None, "lockup_expiry": None, "actual_float": None,
        "lockup_earnings_quarter": quarter,
        "lockup_max_days": int(lockup[1]), "lockup_trading_days_after_earnings": 2,
        "employee_earnings_quarter": employee_quarter,
        "employee_release_percent": int(employee[1]), "waiver_authority": "J.P. Morgan Securities LLC",
        "scope": "filed_terms_only",
    }


def _instant(value) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)


def qualified_deal(row: dict, calendar: dict, *, as_of: str) -> dict | None:
    """Bind exact filing, bytes, observed clock and native calendar identity."""
    try:
        content = row["prospectus_archive_content"]
        if not isinstance(content, bytes) or len(content) > MAX_BYTES or row["form"] != "424B4":
            return None
        raw = row["prospectus_archive_receipt"]
        if not isinstance(raw, str) or len(raw) > 8192:
            return None
        receipt = archive_receipt_from_json_bytes(canonical_json(json.loads(raw)).encode())
        cik, accession, document = row["cik"], row["accession"], row["primary_document"]
        if receipt.document_id != sec_document_id(cik, accession, "primary", document):
            return None
        if receipt.archive_url != archive_document_url(cik, accession, document):
            return None
        if receipt.byte_length != len(content) or receipt.content_sha256 != hashlib.sha256(content).hexdigest():
            return None
        if not (_instant(row["filed_at"]) <= _instant(receipt.retrieved_at) <= _instant(as_of)):
            return None
        terms = parse_terms(content)
        ticker = calendar["ticker"]
        if terms["status"] != "qualified" or terms["ticker"] != ticker or row["ticker"] != ticker:
            return None
        normalized = lambda name: re.sub(r"[^a-z0-9]", "", str(name).lower())
        if normalized(terms["issuer"]) != normalized(calendar["company"]):
            return None
        if calendar["status"] != "priced" or bool(calendar["is_spac"]):
            return None
        if Decimal(str(calendar["offer_price"])) != Decimal(terms["offer_price"]):
            return None
        if Decimal(str(calendar["shares"])) != Decimal(terms["base_shares"]):
            return None
        # The explicitly qualified cover date must occur in retained source bytes.
        cover = datetime.strptime(row["prospectus_date"], "%Y-%m-%d").date()
        cover_text = f"{cover:%B} {cover.day}, {cover.year}"
        front = re.sub(r"\s+", " ", BeautifulSoup(content, "html.parser").get_text(" ")[:18000])
        if cover_text not in front or cover.isoformat() > str(calendar["priced_date"]):
            return None
        return {**terms, "company": calendar["company"], "prospectus_date": cover.isoformat(),
                "first_trade_date": str(calendar["priced_date"]), "filed_at": row["filed_at"],
                "retrieved_at": receipt.retrieved_at, "source_url": receipt.archive_url,
                "content_sha256": receipt.content_sha256, "accession": accession}
    except (KeyError, TypeError, ValueError, ArithmeticError, AttributeError):
        return None


def price_path(prices, *, first_trade_date: str, as_of: str) -> list[dict]:
    """Unadjusted close/volume observations; no pre-IPO or future bars."""
    if prices is None or prices.empty or "close_price" not in prices:
        return []
    cutoff = _instant(as_of).date().isoformat()
    out = []
    for day, row in prices.sort_index().iterrows():
        stamp = str(day)[:10]
        if not first_trade_date <= stamp <= cutoff:
            continue
        try:
            close = float(row["close_price"])
            volume = float(row["volume"])
            if not math.isfinite(close) or close <= 0 or not math.isfinite(volume) or volume < 0:
                continue
        except (KeyError, TypeError, ValueError):
            continue
        out.append({"date": stamp, "close": close, "volume": int(volume)})
    return out


def native_deals(*, as_of: str | None = None) -> list[dict]:
    """Existing IPO cache/calendar and Yahoo price files only; never network."""
    import pandas as pd
    from lib import config
    root = config.data_dir()
    try:
        cached = pd.read_parquet(root / "ipo/lockups.parquet").reset_index()
        calendar = pd.read_parquet(root / "ipo/calendar.parquet")
    except (OSError, ValueError):
        return []
    now = as_of or datetime.now(timezone.utc).isoformat()
    out = []
    for row in cached.to_dict("records"):
        rows = calendar[calendar["ticker"] == row.get("ticker")]
        if len(rows) != 1:
            continue
        deal = qualified_deal(row, rows.iloc[0].to_dict(), as_of=now)
        if deal is None:
            continue
        try:
            prices = pd.read_parquet(root / "yahoo" / f"{deal['ticker']}.parquet")
            deal["prices"] = price_path(prices, first_trade_date=deal["first_trade_date"], as_of=now)
        except (OSError, ValueError):
            deal["prices"] = []
        out.append(deal)
    return out
