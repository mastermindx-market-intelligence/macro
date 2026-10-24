"""Historical filed issue terms from retained native SEC archive receipts.

This read-only projection never joins a pricing-date spread to a current quote,
estimates a rating or publishes source prose. The corporate-bond cache retains
the original archive bytes; numeric terms are parsed anew, not model output.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from engine.fundamental_forensics.models import canonical_json
from engine.fundamental_forensics.sec_document_spine import (
    archive_document_url, archive_receipt_from_json_bytes, sec_document_id,
)

MAX_BYTES = 1024 * 1024


def _instant(value: str) -> datetime:
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("source clock needs a timezone")
    return stamp.astimezone(timezone.utc)


def _archive(row: dict, prefix: str, role: str, document: str):
    content = row[prefix + "_content"]
    raw = row[prefix + "_receipt"]
    if not isinstance(content, bytes) or not 0 < len(content) <= MAX_BYTES:
        raise ValueError("source bytes missing or over bound")
    if not isinstance(raw, str) or len(raw) > 8192:
        raise ValueError("native receipt missing or over bound")
    receipt = archive_receipt_from_json_bytes(canonical_json(json.loads(raw)).encode())
    if (receipt.document_id != sec_document_id(row["cik"], row["accession"], role, document)
            or receipt.archive_url != archive_document_url(row["cik"], row["accession"], document)
            or receipt.content_sha256 != hashlib.sha256(content).hexdigest()
            or receipt.byte_length != len(content)):
        raise ValueError("source identity differs from retained receipt")
    return receipt


def qualified_issue(row: dict, *, as_of: str) -> list[dict]:
    """Bind source type, issuer, document, clock and every parsed tranche."""
    from bs4 import BeautifulSoup
    from lib.dataos.sec_filing_identity import _validate_cusip
    try:
        if row["form"] != "FWP":
            return []
        receipt = _archive(row, "archive", "primary", row["document"])
        index = _archive(row, "index", "archive", row["accession"] + "-index.html")
        soup = BeautifulSoup(row["index_content"], "html.parser")
        heading = soup.select_one("#formName strong")
        accession = soup.select_one("#secNum")
        if (heading is None or heading.get_text(strip=True) != "Form FWP"
                or accession is None or not accession.get_text(" ", strip=True).endswith(row["accession"])):
            return []
        clocks = {}
        for label in soup.select(".infoHead"):
            key = label.get_text(strip=True)
            if key not in ("Accepted", "Filing Date"):
                continue
            value = label.find_next_sibling("div", class_="info")
            if key in clocks or value is None:
                return []
            clocks[key] = value.get_text(strip=True)
        filed_date = date.fromisoformat(clocks["Filing Date"])
        accepted = datetime.strptime(clocks["Accepted"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("America/New_York")).astimezone(timezone.utc)
        retrieved = max(_instant(receipt.retrieved_at), _instant(index.retrieved_at))
        # SEC post-cutoff submissions can carry the following filing date.
        if (abs((filed_date - accepted.date()).days) > 1
                or accepted > min(_instant(receipt.retrieved_at), _instant(index.retrieved_at))
                or retrieved > _instant(as_of)):
            return []
        matches = []
        for tr in soup.select('table[summary="Document Format Files"] tr'):
            cells = tr.find_all("td", recursive=False)
            if len(cells) == 5 and cells[3].get_text(strip=True) == "FWP":
                link = cells[2].find("a")
                if link is not None:
                    matches.append(urljoin(index.archive_url, link.get("href", "")))
        if matches != [receipt.archive_url]:
            return []
        # Exact source-listed subject company; do not infer a ticker from CUSIP.
        companies = []
        for company in soup.select(".companyName"):
            text = company.get_text(" ", strip=True)
            if "(Subject)" not in text:
                continue
            cik = re.search(r"CIK\s*:\s*(\d+)", text)
            if cik and int(cik.group(1)) == int(row["cik"]):
                companies.append(text.split("(Subject)")[0].strip())
        if len(companies) != 1:
            return []
        # Parse only after the retained document and filing index qualify.
        from engine.bond_issue_parser import parse_issue_terms
        terms = parse_issue_terms(row["archive_content"])
        normal = lambda value: re.sub(r"[^a-z0-9]", "", value.lower())
        seen = set()
        for term in terms:
            if normal(term["issuer"]) != normal(companies[0]) or term["cusip"] in seen:
                return []
            _validate_cusip(term["cusip"])
            if date.fromisoformat(term["trade_date"]) > accepted.astimezone(ZoneInfo("America/New_York")).date():
                return []
            seen.add(term["cusip"])
            # The sheets print '$', not an ISO currency declaration. A US ISIN
            # establishes the security identifier, not the denomination.
            term.pop("currency", None)
            term.update(currency_symbol="$", currency_code=None, principal=term.pop("principal_usd"))
            term.update(source_url=receipt.archive_url, accession=row["accession"],
                        filed_date=filed_date.isoformat(), accepted_at=accepted.isoformat(),
                        retrieved_at=retrieved.isoformat(), content_sha256=receipt.content_sha256,
                        scope="historical_issue_terms")
        return terms
    except (KeyError, TypeError, ValueError, AttributeError, ArithmeticError, OSError):
        return []


def native_comparison(root: Path, *, as_of: str | None = None) -> dict:
    """A bounded same-tenor peer context, never a current spread ranking."""
    import pandas as pd
    unavailable = {"status": "unavailable", "pairs": [], "sources": []}
    try:
        cache = pd.read_parquet(root / "data/corp_bonds/filing_pricing_sources.parquet")
    except (OSError, ValueError):
        return unavailable
    if len(cache) != 2:
        return unavailable
    now = as_of or datetime.now(timezone.utc).isoformat()
    groups = [qualified_issue(row, as_of=now) for row in cache.to_dict("records")]
    if any(not rows for rows in groups) or len({rows[0]["issuer"] for rows in groups}) != 2:
        return unavailable
    if [rows[0]["issuer"] for rows in groups] != ["Apple Inc.", "HP Inc."]:
        return unavailable
    pairs = []
    for tenor in (5, 10):
        selected = [[term for term in rows if term["tenor_years"] == tenor] for rows in groups]
        if any(len(terms) != 1 for terms in selected):
            return unavailable
        pairs.append({"tenor_years": tenor, "issues": [terms[0] for terms in selected]})
    return {"status": "qualified", "pairs": pairs, "sources": [rows[0] for rows in groups],
            "coverage": "two_historical_issuers", "available_at": max(row["retrieved_at"] for row in (groups[0][0], groups[1][0]))}
