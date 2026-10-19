"""Explicitly registered central-bank releases for the International collector."""
from __future__ import annotations
from datetime import date
from hashlib import sha256
from html.parser import HTMLParser
import re

from lib.intl_policy_evidence import normalize_policy_decision
from lib.intl_forecast_vintages import normalize_publication

BOE_URL = "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2026/september-2026"
CBC_URL = "https://www.cbc.gov.tw/en/cp-448-192883-c5fa1-2.html"
RELEASES = (
    {"cc": "GB", "provider": "Bank of England", "instrument": "bank_rate",
     "source_url": BOE_URL, "published": "2026-09-17", "decision_date": "2026-09-16",
     "effective_date": "2026-09-16", "value": 3.75, "previous_value": 3.75,
     "votes": {"hold": 6, "increase": 3, "decrease": 0},
     "rationale_en": "Energy-price persistence raises inflation risks. Soft labour conditions and higher borrowing costs pull the other way; three members favoured an increase.",
     "rationale_zh": "能源价格持续偏高加大通胀风险；劳动力市场偏软与借贷成本上升形成反向影响。三名委员主张加息。"},
    {"cc": "TW", "provider": "Central Bank of the Republic of China (Taiwan)", "instrument": "discount_rate",
     "source_url": CBC_URL, "published": "2026-09-17", "decision_date": "2026-09-17",
     "effective_date": "2026-09-17", "value": 2.0, "previous_value": 2.0, "votes": None,
     "rationale_en": "The CBC balanced contained inflation and strong activity against global uncertainty. A discount-rate hold can coexist with rising market borrowing costs.",
     "rationale_zh": "台湾央行权衡可控通胀、强劲经济活动与全球不确定性。贴现率维持不变，并不代表市场借贷成本不会上升。"},
)


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.hidden = [], 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)
    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def _unique(pattern, text):
    matches = re.findall(pattern, text, flags=re.I)
    if len(set(matches)) != 1:
        raise ValueError("policy_release_statement_missing_or_ambiguous")
    return matches[0]


def parse_registered_policy_release(blob, release, *, retrieved_at):
    if type(blob) is not bytes or len(blob) > 4_000_000 or release not in RELEASES:
        raise ValueError("unregistered_policy_release")
    parser = _Text()
    parser.feed(blob.decode("utf-8-sig"))
    text = " ".join(" ".join(parser.parts).split())
    stamp = sha256(blob).hexdigest()
    forecasts = []
    if release["cc"] == "GB":
        if ("Published on 17 September 2026" not in text
                or "soft labour market conditions" not in text
                or "second-round effects" not in text):
            raise ValueError("boe_release_identity_or_rationale_changed")
        found = _unique(r"meeting ending on 16 September 2026,.*?majority of (\d+)[–-](\d+) to maintain Bank Rate at ([\d.]+)%", text)
        if (int(found[0]), int(found[1]), float(found[2])) != (6, 3, 3.75):
            raise ValueError("boe_reviewed_decision_changed")
        minority = _unique(r"Three members voted to increase Bank Rate by ([\d.]+) percentage points, to ([\d.]+)%", text)
        if tuple(map(float, minority)) != (0.25, 4.0):
            raise ValueError("boe_minority_vote_changed")
    else:
        if ("Release Date: September 17, 2026" not in text or "Monetary Policy Decision of the Board Meeting (2026 Q3)" not in text
                or "higher base effect" not in text or "discount rate" not in text):
            raise ValueError("cbc_release_identity_changed")
        rates = _unique(r"discount rate, the rate on refinancing of secured loans, and the rate on temporary accommodations unchanged at ([\d.]+)%, ([\d.]+)%, and ([\d.]+)%", text)
        if tuple(map(float, rates)) != (2.0, 2.375, 4.25):
            raise ValueError("cbc_reviewed_decision_changed")
        current = float(_unique(r"([\d.]+)% for the year as a whole", text))
        following = float(_unique(r"higher base effect would lead the economic growth rate to register ([\d.]+)% next year", text))
        cpi = _unique(r"forecasts for Taiwan's CPI and core CPI inflation rates to ([\d.]+)% and ([\d.]+)%", text)
        next_cpi = _unique(r"next year the CPI and core CPI inflation rates will slow to ([\d.]+)% and ([\d.]+)%", text)
        if (current, following, float(cpi[0]), float(next_cpi[0])) != (11.48, 5.82, 2.03, 1.83):
            raise ValueError("cbc_reviewed_forecast_changed")
        for series, values in (("real_gdp_growth", {"2026": current, "2027": following}),
                               ("inflation_average", {"2026": float(cpi[0]), "2027": float(next_cpi[0])})):
            record = normalize_publication({
                "cc": "TW", "provider": "CBC", "family": "Monetary policy outlook", "edition": "2026-09-17",
                "kind": "sourced_forecast", "series_id": series, "published": release["published"],
                "source_url": CBC_URL, "unit": "percent", "period_basis": "calendar_year",
                "values": values, "precision": 2, "source_sha256": stamp,
                "retrieved_at": retrieved_at, "parser_version": "cbc_reviewed_release_v1",
            }, observed_at=retrieved_at)
            if record is None:
                raise ValueError("cbc_forecast_admission_failed")
            forecasts.append(record)
    decision = normalize_policy_decision({**release, "schema": "intl_policy_decision.v1", "unit": "percent",
        "action": "hold", "first_observed_at": retrieved_at, "source_sha256": stamp}, observed_at=retrieved_at)
    if decision is None:
        raise ValueError("policy_decision_admission_failed")
    return {"policy_decisions": [decision], "forecast_archive": forecasts}


def collect_registered_policy(fetch_bytes, *, retrieved_at):
    decisions, forecasts, sources, errors = [], [], [], []
    for release in RELEASES:
        if date.fromisoformat(release["published"]) > date.fromisoformat(retrieved_at[:10]):
            continue
        try:
            blob = fetch_bytes(release["source_url"], max_bytes=4_000_000)
            parsed = parse_registered_policy_release(blob, release, retrieved_at=retrieved_at)
            decisions.extend(parsed["policy_decisions"])
            forecasts.extend(parsed["forecast_archive"])
            sources.append({"provider": release["provider"], "url": release["source_url"],
                            "published": release["published"], "sha256": sha256(blob).hexdigest(),
                            "status": "verified", "retrieved_at": retrieved_at})
        except Exception as exc:
            errors.append({"source": release["provider"], "source_url": release["source_url"],
                           "error": type(exc).__name__, "detail": str(exc)[:160],
                           "attempted_at": retrieved_at, "status": "release_not_verified"})
    return {"policy_decisions": decisions, "forecast_archive": forecasts, "sources": sources, "errors": errors}
