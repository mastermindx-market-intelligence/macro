"""Device-native FDA decision facts. No forecast, issuer guess, or commercial inference.

The transport dataset is part of identity. PMA supplements retain their own
identity and parent; a 30-day notice never becomes a new-device approval.
All source dates are day precision. Knowledge begins at our actual retrieval,
not at the retrospective FDA decision date.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import re
from typing import Any, Mapping

SCHEMA = "medtech.event/v1"
DATASETS = {"510k": "https://api.fda.gov/device/510k.json",
            "pma": "https://api.fda.gov/device/pma.json"}
SUBMISSION_PATTERNS = {
    "510k": r"(?:[A-Z][0-9]{6}|DEN[0-9]{6})",
    "pma": r"(?:[A-Z][0-9]{6}|N[0-9]{5})",
}
EVENT_ID_RE = re.compile(
    rf"(?:fda-510k-{SUBMISSION_PATTERNS['510k']}|"
    rf"fda-pma-{SUBMISSION_PATTERNS['pma']}(?:-S[0-9]{{1,6}})?)\Z"
)
PATHWAYS = {
    "510k": "510(k)",
    "de_novo": "De Novo",
    "pma_original": "PMA original",
    "pma_panel_track_supplement": "PMA panel-track supplement",
    "pma_supplement": "PMA supplement",
    "hde": "Humanitarian device exemption",
    "other_device_submission": "Other FDA device submission",
}
# Exact documented codes only. Unmapped live codes stay visible and unclassified.
PMA_DECISIONS = {
    "APPR": ("approved", "Approved"),
    "WTDR": ("withdrawn", "Withdrawn"),
    "DENY": ("denied", "Denied"),
    "LE30": ("notice_accepted", "30-day notice accepted"),
    "APRL": ("reclassified", "Reclassified after approval"),
    "APWD": ("approval_withdrawn", "Approval withdrawn"),
    "GT30": ("notice_pending", "No decision within 30 days"),
    "APCV": ("converted", "Converted after approval"),
}
K_DECISIONS = {
    "SESE": ("cleared", "Cleared"),
}
DE_NOVO_DECISIONS = {
    "DENG": ("granted", "Granted"),
}
MEANINGFUL_FIELDS = (
    "decision", "received_on", "device", "applicant", "supplement", "pathway",
)


class MedTechError(ValueError):
    """Stable bounded error code; never include upstream bodies or host paths."""


def instant(value: str) -> datetime:
    if not isinstance(value, str):
        raise MedTechError("INVALID_OBSERVATION_TIME")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise MedTechError("INVALID_OBSERVATION_TIME") from None
    if result.tzinfo is None or result.utcoffset() is None:
        raise MedTechError("INVALID_OBSERVATION_TIME")
    return result.astimezone(timezone.utc)


def utc(value: str) -> str:
    return instant(value).isoformat(timespec="microseconds").replace("+00:00", "Z")


def text_field(value: Any, *, limit: int = 4000) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str) or len(value) > limit:
        raise MedTechError("INVALID_SOURCE_FIELD")
    # Preserve the source's case; normalize display whitespace only.
    return " ".join(value.split()) or None


def source_date(value: Any, *, observed_at: str) -> str | None:
    raw = text_field(value, limit=10)
    if raw is None:
        return None
    try:
        if re.fullmatch(r"[0-9]{8}", raw):
            parsed = datetime.strptime(raw, "%Y%m%d").date()
        else:
            parsed = date.fromisoformat(raw)
    except ValueError:
        raise MedTechError("INVALID_SOURCE_DATE") from None
    if parsed.year < 1900 or parsed > instant(observed_at).date():
        raise MedTechError("INVALID_SOURCE_DATE")
    return parsed.isoformat()


@dataclass(frozen=True)
class Observation:
    event: dict[str, Any]
    observed_at: str
    dataset_updated_at: str
    raw: dict[str, Any]

    @property
    def event_id(self) -> str:
        return self.event["event_id"]

    @property
    def state_hash(self) -> str:
        # Only allowlisted product state: contact/address and harmonized metadata
        # changes remain in retained source receipts, never masquerade as catalysts.
        from engine.sector_intelligence import canonical_json_sha256
        return canonical_json_sha256(self.event)


def source_record_url(dataset: str, number: str, supplement: str | None = None) -> str:
    if dataset not in SUBMISSION_PATTERNS or not re.fullmatch(SUBMISSION_PATTERNS[dataset], number):
        raise MedTechError("INVALID_SUBMISSION_ID")
    if supplement and (dataset != "pma" or not re.fullmatch(r"S[0-9]{1,6}", supplement)):
        raise MedTechError("INVALID_SUPPLEMENT_ID")
    if dataset == "pma":
        return f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpma/pma.cfm?id={number}{supplement or ''}"
    if number.startswith("DEN"):
        return f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/denovo.cfm?id={number}"
    return f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID={number}"


def normalize_record(dataset: str, record: Mapping[str, Any], *,
                     observed_at: str, dataset_updated_at: str) -> Observation:
    if dataset not in DATASETS or not isinstance(record, Mapping):
        raise MedTechError("INVALID_DATASET")
    observed_at = utc(observed_at)
    updated = source_date(dataset_updated_at, observed_at=observed_at)
    if updated is None:
        raise MedTechError("DATASET_CLOCK_MISSING")
    number = text_field(record.get("k_number" if dataset == "510k" else "pma_number"),
                        limit=9 if dataset == "510k" else 7)
    if not number or not re.fullmatch(SUBMISSION_PATTERNS[dataset], number):
        raise MedTechError("INVALID_SUBMISSION_ID")
    supplement = text_field(record.get("supplement_number"), limit=7) if dataset == "pma" else None
    if supplement and not re.fullmatch(r"S[0-9]{1,6}", supplement):
        raise MedTechError("INVALID_SUPPLEMENT_ID")
    supplement_type = text_field(record.get("supplement_type")) if dataset == "pma" else None
    if dataset == "510k" and number.startswith("DEN"):
        pathway = "de_novo"
    elif dataset == "510k" and number.startswith("K"):
        pathway = "510k"
    elif dataset == "pma" and number.startswith("H"):
        pathway = "hde"
    elif dataset == "pma" and number.startswith("P"):
        if not supplement:
            pathway = "pma_original"
        elif supplement_type and supplement_type.casefold().replace("-", " ") == "panel track":
            pathway = "pma_panel_track_supplement"
        else:
            pathway = "pma_supplement"
    else:
        pathway = "other_device_submission"
    code = text_field(record.get("decision_code"), limit=16)
    decision_map = (DE_NOVO_DECISIONS if pathway == "de_novo" else
                    K_DECISIONS if dataset == "510k" else PMA_DECISIONS)
    status, label = decision_map.get(code, ("unmapped", "Decision recorded"))
    decision_on = source_date(record.get("decision_date"), observed_at=observed_at)
    received_on = source_date(record.get("date_received"), observed_at=observed_at)
    if decision_on and received_on and received_on > decision_on:
        raise MedTechError("SOURCE_DATE_ORDER_INVALID")
    suffix = "-" + supplement if supplement else ""
    event_id = f"fda-{dataset}-{number}{suffix}"
    source_id = number + (supplement or "")
    source_url = source_record_url(dataset, number, supplement)
    event = {
        "schema": SCHEMA,
        "event_id": event_id,
        "submission_id": number,
        "parent_submission_id": number if supplement else None,
        "pathway": pathway,
        "pathway_label": PATHWAYS[pathway],
        "device": {
            "name": text_field(record.get("device_name" if dataset == "510k" else "trade_name")),
            "generic_name": text_field(record.get("generic_name")),
            "product_code": text_field(record.get("product_code"), limit=16),
        },
        "applicant": {"name": text_field(record.get("applicant"))},
        "decision": {
            "code": code, "status": status, "label": label,
            "date": decision_on, "date_precision": "day" if decision_on else None,
            "source_description": text_field(record.get("decision_description")),
        },
        "received_on": received_on,
        "supplement": {
            "number": supplement, "type": supplement_type,
            "reason": text_field(record.get("supplement_reason")) if dataset == "pma" else None,
        },
        "source": {
            "publisher": "FDA", "dataset": dataset, "record_id": source_id,
            "url": source_url, "source_published_at": None,
        },
        # Applicant != listed issuer != territorial commercial-rights holder.
        "company_link": {"status": "not_joined"},
        "commercial_evidence": {"status": "not_assessed"},
        "next_milestone": None,
    }
    return Observation(event, observed_at, updated, dict(record))


def changes_between(before: Mapping[str, Any], after: Mapping[str, Any]) -> list[dict]:
    """Concise, exact Previous -> Now values for the R14 change-review surface."""
    from engine.sector_intelligence import exact_json_diff

    prior = {key: before[key] for key in MEANINGFUL_FIELDS}
    current = {key: after[key] for key in MEANINGFUL_FIELDS}
    changes = exact_json_diff(prior, current)
    for change in changes:
        change["change_family"] = change["json_path"].split("/")[1]
    return changes
