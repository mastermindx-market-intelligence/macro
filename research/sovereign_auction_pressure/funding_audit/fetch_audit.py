"""Bounded, read-only official funding-source feasibility capture; no outcomes fit."""
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
SOURCES = {
    "dts_tga_earliest.json": "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance?sort=record_date&page[size]=1",
    "dts_tga_latest.json": "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance?sort=-record_date&page[size]=1",
    "dts_oct6_cash.json": "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance?filter=record_date:eq:2026-10-06&page[size]=100",
    "dts_oct6_marketable.json": "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/public_debt_transactions?filter=record_date:eq:2026-10-06,security_market:eq:Marketable&page[size]=100",
    "nyfed_latest_rates.json": "https://markets.newyorkfed.org/api/rates/all/latest.json",
    "tgcr_first_week.json": "https://markets.newyorkfed.org/api/rates/secured/tgcr/search.json?startDate=2018-04-02&endDate=2018-04-06",
    "borrowing_aug3_2026.html": "https://home.treasury.gov/news/press-releases/sb0584",
    "refunding_aug5_2026.html": "https://home.treasury.gov/news/press-releases/sb0590",
    "dealer_publication.html": "https://www.newyorkfed.org/markets/counterparties/primary-dealers-statistics",
    "reference_rates_policy.html": "https://www.newyorkfed.org/markets/reference-rates/additional-information-about-reference-rates",
    "soma_holdings.html": "https://www.newyorkfed.org/markets/soma-holdings",
    "dts_oct6.pdf": "https://fiscaldata.treasury.gov/static-data/published-reports/dts/DailyTreasuryStatement_20261006.pdf",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def fetch(item):
    name, url = item
    receipt = {"file": "raw/" + name, "url": url, "request_started_at": now()}
    try:
        request = Request(url, headers={"User-Agent": "Mastermind-Source-Feasibility/1.0"})
        with urlopen(request, timeout=25) as response:
            body = response.read(2 * 1024 * 1024 + 1)
            received = now()
            if len(body) > 2 * 1024 * 1024:
                raise ValueError("bounded response limit exceeded")
            receipt.update(status=response.status, final_url=response.url,
                           body_received_at=received,
                           content_type=response.headers.get("Content-Type"),
                           http_date=response.headers.get("Date"),
                           http_last_modified=response.headers.get("Last-Modified"),
                           sha256=hashlib.sha256(body).hexdigest(), bytes=len(body),
                           published_at=None)
        (ROOT / receipt["file"]).write_bytes(body)
        receipt["verified_present_at"] = now()
    except Exception as exc:
        receipt.update(error=type(exc).__name__ + ": " + str(exc), attempt_completed_at=now())
    return receipt


if __name__ == "__main__":
    (ROOT / "raw").mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        receipts = list(pool.map(fetch, SOURCES.items()))
    (ROOT / "SOURCE_RECEIPTS.json").write_text(json.dumps(receipts, indent=2) + "\n")
    for row in receipts:
        print(json.dumps({key: row.get(key) for key in ("file", "status", "bytes", "body_received_at", "error")}))
