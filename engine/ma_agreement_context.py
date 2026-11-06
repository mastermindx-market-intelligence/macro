"""Public, dated agreement facts for the existing featured merger.

The immutable SEC documents remain the source. This display adapter does not
decide whether a fee is payable, a condition is satisfied or a deal will close.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from engine.fundamental_forensics.models import canonical_json
from engine.fundamental_forensics.sec_document_spine import (
    archive_document_url, archive_receipt_from_json_bytes, sec_document_id,
)


def _one(pattern: str, text: str):
    matches = list(re.finditer(pattern, text))
    if len(matches) != 1:
        raise ValueError("source assertion missing or ambiguous")
    return matches[0]


def _instant(value: str) -> datetime:
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("source clock has no timezone")
    return stamp.astimezone(timezone.utc)


def _receipt(row: dict, key: str, role: str, name: str):
    content = row[key + "_content"]
    raw = row[key + "_receipt"]
    if not isinstance(content, bytes) or not 0 < len(content) <= 4 * 1024 * 1024:
        raise ValueError("retained source size or type")
    if not isinstance(raw, str) or len(raw) > 8192:
        raise ValueError("retained receipt size or type")
    receipt = archive_receipt_from_json_bytes(canonical_json(json.loads(raw)).encode())
    if (receipt.document_id != sec_document_id(row["cik"], row["accession"], role, name)
            or receipt.archive_url != archive_document_url(row["cik"], row["accession"], name)
            or receipt.content_sha256 != hashlib.sha256(content).hexdigest()
            or receipt.byte_length != len(content)):
        raise ValueError("retained source identity mismatch")
    return receipt


def parse_agreement(content: bytes) -> dict:
    """Literal extraction from the supported proxy; refuse incomplete context."""
    if not isinstance(content, bytes) or not 0 < len(content) <= 4 * 1024 * 1024:
        return {}
    try:
        soup = BeautifulSoup(content.decode("utf-8", errors="strict"), "html.parser")
        for node in list(soup.find_all(True)):
            if node.attrs is None:
                continue
            style = re.sub(r"\s+", "", str(node.get("style", "")).lower())
            if (node.name in ("script", "style", "noscript", "template") or node.has_attr("hidden")
                    or node.get("aria-hidden") == "true" or "display:none" in style):
                node.decompose()
        text = " ".join(soup.get_text(" ", strip=True).split())
        cover = _one(r"entered into by the Company on (August 10, 2026) \(the “ Merger Agreement ”\) with (Prive Parent, Inc\.), a Delaware corporation \(“ Parent ”\)", text)
        finance = _one(r"Financing of the Merger Equity Financing Concurrently.*?(?=Regulatory Clearances and Approvals Required for the Merger General Efforts)", text).group()
        company = _one(r"Company Termination Fee The Company is required.*?(?=Parent Termination Fee Subject to certain limitations)", text).group()
        parent = _one(r"Parent Termination Fee Subject to certain limitations.*?(?=Page \| 87 TABLE OF CONTENTS Limitations of Liability)", text).group()
        equity = int(_one(r"aggregate amount equal to \$([\d,]+), on the terms and subject to the conditions", finance).group(1).replace(",", ""))
        debt = _one(r"with a \$(\d+) million senior secured first-lien term loan facility, a \$(\d+) million senior secured first-lien revolving credit facility and a \$(\d+) million senior secured first-lien delayed draw term loan facility", finance)
        fee = int(_one(r"fee equal to \$([\d,]+) \(the “ Company Termination Fee ”\) to Parent", company).group(1).replace(",", ""))
        reduced = int(_one(r"Company Termination Fee will be an amount equal to \$([\d,]+)", company).group(1).replace(",", ""))
        parent_fee = int(_one(r"Parent is required to pay the Company a termination fee equal to \$([\d,]+)", parent).group(1).replace(",", ""))
        required = [
            ("not subject to any financing condition", finance),
            ("subject to the satisfaction or waiver of the conditions to the Closing", finance),
            ("subject to the satisfaction of certain customary conditions to funding", finance),
            ("on or prior to September 28, 2026", company),
            ("Superior Proposal received from an Excluded Party", company),
            ("Recommendation Change", company),
            ("prior to such termination an Acquisition Proposal", company),
            ("publicly announced or publicly disclosed and not publicly withdrawn", company),
            ("within 12 months following such termination", company),
            ("Subject to certain limitations and cure provisions", parent),
            ("failure to effect the Closing when required", parent),
            ("ready, willing and able", parent),
            ('references to “ $ ” or “ Dollars ” are references to U.S. dollars.', text),
        ]
        if any(literal not in source for literal, source in required):
            return {}
        amounts = [equity, fee, reduced, parent_fee] + [int(v) * 1000000 for v in debt.groups()]
        if any(not 0 < amount < 100000000000 for amount in amounts) or reduced >= fee:
            return {}
        return {
            "company": "Bowman Consulting Group Ltd.", "buyer": cover.group(2),
            "agreement_date": "2026-08-10", "currency": "USD",
            "equity_commitment": equity,
            "term_loan_commitment": int(debt.group(1)) * 1000000,
            "revolver_commitment": int(debt.group(2)) * 1000000,
            "delayed_draw_commitment": int(debt.group(3)) * 1000000,
            "company_to_parent_fee": fee, "parent_to_company_fee": parent_fee,
            "reduced_company_fee": reduced, "reduced_fee_deadline": "2026-09-28",
            "funded_amount": None, "fee_payable_now": None, "closing_probability": None,
            "financing_is_closing_condition": False, "other_closing_conditions_apply": True,
            "source_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        }
    except (UnicodeError, ValueError, TypeError, KeyError, AttributeError):
        return {}


def qualified_agreement(row: dict, premium: dict, *, as_of: str) -> dict:
    """Bind the displayed deal to the same issuer and filing, never ticker alone."""
    try:
        if (row["form"] != "DEFM14A" or row["cik"] != "1847590"
                or premium.get("status") != "computed"
                or premium.get("issuer_key") != "cik:" + row["cik"]
                or premium.get("offer_accession") != row["accession"]
                or premium.get("offer_form_type") != row["form"]):
            return {}
        primary = _receipt(row, "archive", "primary", row["document"])
        index = _receipt(row, "index", "archive", row["accession"] + "-index.htm")
        soup = BeautifulSoup(row["index_content"], "html.parser")
        heading, accession = soup.select_one("#formName strong"), soup.select_one("#secNum")
        if (heading is None or heading.get_text(strip=True) != "Form DEFM14A"
                or accession is None or not accession.get_text(" ", strip=True).endswith(row["accession"])):
            return {}
        companies = [e.get_text(" ", strip=True) for e in soup.select(".companyName")]
        if len(companies) != 1 or not re.fullmatch(r"Bowman Consulting Group Ltd\. \(Filer\) CIK\s*:\s*0001847590 \(see all company filings\)", companies[0]):
            return {}
        docs = []
        for tr in soup.select('table[summary="Document Format Files"] tr'):
            cells = tr.find_all("td", recursive=False)
            if len(cells) == 5 and cells[3].get_text(strip=True) == row["form"]:
                link = cells[2].find("a")
                if link is not None:
                    docs.append(urljoin(index.archive_url, link.get("href", "")))
        if docs != [primary.archive_url]:
            return {}
        clocks = {}
        for label in soup.select(".infoHead"):
            key = label.get_text(strip=True)
            if key in ("Accepted", "Filing Date"):
                if key in clocks:
                    return {}
                clocks[key] = label.find_next_sibling("div", class_="info").get_text(strip=True)
        accepted = datetime.strptime(clocks["Accepted"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("America/New_York")).astimezone(timezone.utc)
        retrieved = max(_instant(primary.retrieved_at), _instant(index.retrieved_at))
        if (clocks["Filing Date"] != premium.get("offer_filing_date")
                or accepted > min(_instant(primary.retrieved_at), _instant(index.retrieved_at))
                or retrieved > _instant(as_of)):
            return {}
        result = parse_agreement(row["archive_content"])
        if not result:
            return {}
        return result | {"status": "qualified", "source_url": primary.archive_url,
                         "accession": row["accession"], "filed_date": clocks["Filing Date"],
                         "accepted_at": accepted.isoformat(), "retrieved_at": retrieved.isoformat(),
                         "source_sha256": primary.content_sha256, "scope": "dated_public_agreement_facts"}
    except (KeyError, ValueError, TypeError, AttributeError, OSError):
        return {}


def featured_agreement(root: Path, premium: dict, *, as_of: str | None = None) -> dict:
    import pandas as pd
    try:
        rows = pd.read_parquet(root / "data/special_situations/agreement_sources.parquet")
        if len(rows) != 1:
            return {}
        return qualified_agreement(rows.to_dict("records")[0], premium,
                                   as_of=as_of or datetime.now(timezone.utc).isoformat())
    except (OSError, ValueError):
        return {}
