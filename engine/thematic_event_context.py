"""Rights-bounded event context for the thematic desk.

This module is an ADAPTER over existing owners, not a collector, ranker, thesis store, or
trade authority. V1 intentionally uses only:
  * SEC EDGAR material 8-K metadata already collected at
    data/edgar/material_8k_events.parquet; and
  * first-party curated theme membership at data/baskets/membership.json.

General press/narrative/search remains explicitly blocked from model use under the current
Prophet US source-rights register. The adapter preserves that absence as a typed state rather
than silently treating "not examined" as "no catalyst".

Membership is CURRENT-ONLY in this slice. It is suitable for prospective context now; it is
not evidence that current membership was historically true. Every emitted authority flag is
false. No field here directly changes a theme score, gate, size, entry, or trade.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable

import pandas as pd

from engine.theme_graph import rights as _theme_rights
from lib import config


SCHEMA = "thematic_event_context.v1"
SOURCE_PATH = "data/edgar/material_8k_events.parquet"
MEMBERSHIP_PATH = "data/baskets/membership.json"
RIGHTS_FAMILY = "sec_edgar"
RIGHTS_REF = "config/theme_sources.yml#families.sec_edgar"
MODEL_USE_RIGHTS_PATH = "research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md"
MODEL_USE_RIGHTS_REF = MODEL_USE_RIGHTS_PATH + "#SEC-EDGAR"
PRESS_RIGHTS_REF = (
    "research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md"
    "#press-narrative-search"
)
DEFAULT_WINDOW_DAYS = 14
DEFAULT_MAX_EVENTS = 256
_MAX_EVENTS = 512
_ACCESSION_RE = re.compile(r"^\d{10}-\d{2}-\d{6}$")

_REQUIRED_EVENT_COLUMNS = frozenset({
    "ticker", "cik", "form", "filing_date", "items", "accession", "_first_seen",
})


def _iso(stamp: pd.Timestamp) -> str:
    return stamp.tz_convert("UTC").isoformat().replace("+00:00", "Z")


def _aware(value: Any) -> pd.Timestamp | None:
    if value is None or value is pd.NaT:
        return None
    try:
        stamp = pd.Timestamp(value)
    except Exception:  # noqa: BLE001
        return None
    if stamp is pd.NaT or stamp.tzinfo is None:
        return None
    return stamp.tz_convert("UTC")


def _date_text(value: Any) -> str | None:
    if value is None or value is pd.NaT:
        return None
    try:
        stamp = pd.Timestamp(value)
    except Exception:  # noqa: BLE001
        return None
    if stamp is pd.NaT:
        return None
    return stamp.date().isoformat()


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_ref(path: str, digest: str) -> str:
    return f"{path}#sha256:{digest}"


def _model_use_admitted(repo_root: Path) -> bool:
    """Read the existing D03 rights register; never invent model-use permission.

    The register is Markdown today, so this narrow adapter reads only the SEC EDGAR
    section and its Model use row. Missing/changed/unreadable text fails closed.
    """
    path = repo_root / MODEL_USE_RIGHTS_PATH
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return False
    start = text.find("## SEC EDGAR")
    if start < 0:
        return False
    end = text.find("\n## ", start + len("## SEC EDGAR"))
    section = text[start:] if end < 0 else text[start:end]
    for line in section.splitlines():
        if line.startswith("| Model use |"):
            return "Posture: **user-facing**" in line
    return False


def _sec_rights_posture(repo_root: Path) -> dict:
    """Consume existing source-rights owners at call time; missing admission fails closed."""
    registry_path = repo_root / _theme_rights.REGISTRY_FILE
    try:
        cls = _theme_rights.rights_class(RIGHTS_FAMILY, path=registry_path)
    except _theme_rights.RightsRefusal:
        cls = None
    internal_ok, display_ok, redistribution_ok = _theme_rights.licensing_for_family(
        RIGHTS_FAMILY, path=registry_path)
    model_use_ok = _model_use_admitted(repo_root)
    admitted = bool(display_ok and model_use_ok)
    return {
        "family": RIGHTS_FAMILY,
        "status": "admitted" if admitted else "not_admitted",
        "rights_class": cls,
        "internal_ok": bool(internal_ok),
        "display_ok": bool(display_ok),
        "model_use_ok": bool(model_use_ok),
        "redistribution_ok": bool(redistribution_ok),
        "rights_ref": RIGHTS_REF,
        "model_use_rights_ref": MODEL_USE_RIGHTS_REF,
        "representation_scope": (
            "SEC filing metadata and incumbent extracted factual fields only; no filing/exhibit "
            "body, whole expressive document, third-party attachment, logo/branding, or dataset "
            "redistribution"
        ),
    }


def _blocked_sources() -> dict[str, dict]:
    return {
        "press_narrative_search": {
            "status": "blocked_rights",
            "reason": (
                "current rights register does not clear this family for model-facing "
                "processing/storage/inference and user redistribution"
            ),
            "rights_ref": PRESS_RIGHTS_REF,
        }
    }


def _base(
    *,
    cutoff: pd.Timestamp,
    window_days: int,
    source_snapshot_ref: str | None,
    membership_snapshot_ref: str | None,
    rights_posture: dict | None = None,
) -> dict:
    return {
        "schema": SCHEMA,
        "authority": "descriptive_research_only",
        "is_context_only": True,
        "may_rank": False,
        "may_gate": False,
        "may_size": False,
        "may_trade": False,
        "region": "us",
        "knowledge_cutoff": _iso(cutoff),
        "window_days": window_days,
        "source_family": "sec_edgar_material_8k",
        "source_path": SOURCE_PATH,
        "source_snapshot_ref": source_snapshot_ref,
        "rights_ref": RIGHTS_REF,
        "model_use_rights_ref": MODEL_USE_RIGHTS_REF,
        "rights_posture": rights_posture or {
            "family": RIGHTS_FAMILY,
            "status": "not_admitted",
            "rights_class": None,
            "internal_ok": True,
            "display_ok": False,
            "model_use_ok": False,
            "redistribution_ok": False,
            "rights_ref": RIGHTS_REF,
            "model_use_rights_ref": MODEL_USE_RIGHTS_REF,
            "representation_scope": "projection only; no activation rights were supplied",
        },
        "membership_path": MEMBERSHIP_PATH,
        "membership_snapshot_ref": membership_snapshot_ref,
        "membership_basis": "current_only",
        "historical_vintage_proven": False,
        "entity_semantics": (
            "ticker is the SEC registrant symbol in the filing metadata; theme_ids are "
            "current house membership joins, not SEC claims and not economic-exposure proof"
        ),
        "selection_policy": (
            "newest known SEC events with one-event-per-affected-theme coverage first; "
            "no return, score, rank, sentiment, ticker-preference, or entry preference"
        ),
        "blocked_sources": _blocked_sources(),
        "status": "unavailable",
        "reason": None,
        "coverage": {},
        "events": [],
    }


def _membership_map(
    membership: dict,
    theme_ids: Iterable[str] | None,
) -> tuple[dict[str, tuple[str, ...]], dict[str, Any]]:
    baskets = membership.get("baskets") if isinstance(membership, dict) else None
    if not isinstance(baskets, dict):
        return {}, {
            "requested_themes": 0,
            "resolved_themes": 0,
            "missing_theme_definitions": [],
            "expected_members": 0,
        }

    requested = (
        {str(x) for x in theme_ids if isinstance(x, str) and x}
        if theme_ids is not None else set(baskets)
    )
    ticker_themes: dict[str, set[str]] = defaultdict(set)
    missing: list[str] = []
    resolved = 0
    for theme_id in sorted(requested):
        basket = baskets.get(theme_id)
        if not isinstance(basket, dict):
            missing.append(theme_id)
            continue
        resolved += 1
        members = basket.get("members") if isinstance(basket.get("members"), list) else []
        for member in members:
            if not isinstance(member, dict) or member.get("removed"):
                continue
            ticker = str(member.get("ticker") or "").strip().upper()
            if ticker:
                ticker_themes[ticker].add(theme_id)

    return (
        {ticker: tuple(sorted(themes)) for ticker, themes in ticker_themes.items()},
        {
            "requested_themes": len(requested),
            "resolved_themes": resolved,
            "missing_theme_definitions": missing,
            "expected_members": len(ticker_themes),
        },
    )


def _cik_text(value: Any) -> str | None:
    try:
        if pd.isna(value):
            return None
        return str(int(value)).zfill(10)
    except Exception:  # noqa: BLE001
        text = str(value or "").strip()
        return text.zfill(10) if text.isdigit() and len(text) <= 10 else None


def _sec_index_url(cik: str, accession: str) -> str:
    return (
        "https://www.sec.gov/Archives/edgar/data/"
        f"{int(cik)}/{accession.replace('-', '')}/{accession}-index.htm"
    )


def _normalized_event(
    row: dict[str, Any],
    *,
    ticker_themes: dict[str, tuple[str, ...]],
    cutoff: pd.Timestamp,
    start: pd.Timestamp,
    excluded: Counter,
) -> dict | None:
    first_seen = _aware(row.get("_first_seen"))
    if first_seen is None:
        excluded["invalid_first_seen"] += 1
        return None
    if first_seen > cutoff:
        excluded["not_yet_seen"] += 1
        return None
    if first_seen < start:
        excluded["outside_context_window"] += 1
        return None

    ticker = str(row.get("ticker") or "").strip().upper()
    themes = ticker_themes.get(ticker)
    if not themes:
        excluded["outside_theme_membership"] += 1
        return None

    accession = str(row.get("accession") or "").strip()
    cik = _cik_text(row.get("cik"))
    form = str(row.get("form") or "").strip()
    filing_date = _date_text(row.get("filing_date"))
    if not accession or not _ACCESSION_RE.fullmatch(accession) or not cik or not form:
        excluded["missing_event_identity"] += 1
        return None
    if filing_date is None:
        excluded["invalid_source_date"] += 1
        return None
    if filing_date > first_seen.date().isoformat():
        excluded["source_date_after_first_seen"] += 1
        return None

    items = str(row.get("items") or "").strip()
    event_key = f"sec_edgar:{cik}:{accession}"
    source_url = _sec_index_url(cik, accession)
    report = {
        "item_id": event_key,
        "source": "SEC EDGAR",
        "source_url": source_url,
        "url": source_url,
        "title": f"{ticker} {form}" + (f" items {items}" if items else ""),
        "body_sha256": None,
        "source_date_value": filing_date,
        "publisher_stated_at": None,
        "context_available_at": _iso(first_seen),
        "first_seen_at": _iso(first_seen),
        "timestamp_quality": "CRAWL_BOUNDED",
        "evidence_level": "sec_filing_metadata",
        "ticker": ticker,
        "cik": cik,
        "accession": accession,
        "form": form,
        "items": items,
        "extraction_ok": bool(row.get("extraction_ok") is True),
    }

    if report["extraction_ok"]:
        amount = row.get("amount_usd")
        if amount is not None and not pd.isna(amount):
            try:
                amount = float(amount)
                if amount > 0:
                    report["amount_usd"] = amount
            except Exception:  # noqa: BLE001
                pass
        counterparty = str(row.get("counterparty") or "").strip()
        if counterparty:
            report["counterparty"] = counterparty
        for key in ("amount_src", "counterparty_src"):
            value = str(row.get(key) or "").strip()
            if value:
                report[key] = value

    return {
        "event_key": event_key,
        "unclustered_item_id": None,
        "first_context_available_at": _iso(first_seen),
        "last_report_available_at": _iso(first_seen),
        "first_seen_in_window": True,
        "n_reports": 1,
        "n_reports_shown": 1,
        "reports_omitted": 0,
        "mentioned_entities": [ticker],
        "theme_ids": list(themes),
        "membership_basis": "current_only",
        "n_source_labels": 1,
        "reports": [report],
        "_sort_ts": first_seen,
    }


def _coverage_first(events: list[dict], max_events: int) -> list[dict]:
    """Guarantee each affected theme a newest representative before filling by recency."""
    if len(events) <= max_events:
        return events

    chosen: set[str] = set()
    affected = sorted({theme for event in events for theme in event["theme_ids"]})
    for theme in affected:
        for event in events:
            if theme in event["theme_ids"]:
                chosen.add(event["event_key"])
                break

    selected = [event for event in events if event["event_key"] in chosen]
    if len(selected) < max_events:
        for event in events:
            if event["event_key"] in chosen:
                continue
            selected.append(event)
            chosen.add(event["event_key"])
            if len(selected) >= max_events:
                break

    selected.sort(key=lambda event: (event["_sort_ts"], event["event_key"]), reverse=True)
    return selected[:max_events]


def project_sec_event_context(
    events: pd.DataFrame,
    membership: dict,
    *,
    theme_ids: Iterable[str] | None,
    knowledge_cutoff: str | datetime | pd.Timestamp,
    window_days: int = DEFAULT_WINDOW_DAYS,
    max_events: int = DEFAULT_MAX_EVENTS,
    source_snapshot_ref: str | None = None,
    membership_snapshot_ref: str | None = None,
    rights_posture: dict | None = None,
) -> dict:
    """Project SEC event metadata into a bounded, clock-honest thematic context.

    This low-level projector also fails closed unless the caller supplies an admitted posture
    from the existing rights owners. Product code obtains that posture via build_sec_event_context.
    """
    cutoff = _aware(knowledge_cutoff)
    if cutoff is None:
        fallback = pd.Timestamp(datetime.now(timezone.utc))
        out = _base(
            cutoff=fallback, window_days=DEFAULT_WINDOW_DAYS,
            source_snapshot_ref=source_snapshot_ref,
            membership_snapshot_ref=membership_snapshot_ref,
        )
        out["reason"] = "invalid_knowledge_cutoff"
        return out

    if type(window_days) is not int or not 1 <= window_days <= 90:
        out = _base(
            cutoff=cutoff, window_days=DEFAULT_WINDOW_DAYS,
            source_snapshot_ref=source_snapshot_ref,
            membership_snapshot_ref=membership_snapshot_ref,
        )
        out["reason"] = "invalid_window_days"
        return out
    if type(max_events) is not int or not 1 <= max_events <= _MAX_EVENTS:
        out = _base(
            cutoff=cutoff, window_days=window_days,
            source_snapshot_ref=source_snapshot_ref,
            membership_snapshot_ref=membership_snapshot_ref,
        )
        out["reason"] = "invalid_max_events"
        return out

    out = _base(
        cutoff=cutoff, window_days=window_days,
        source_snapshot_ref=source_snapshot_ref,
        membership_snapshot_ref=membership_snapshot_ref,
        rights_posture=rights_posture,
    )
    if not isinstance(rights_posture, dict) or rights_posture.get("status") != "admitted":
        out["reason"] = "source_rights_not_admitted"
        return out
    ticker_themes, membership_cov = _membership_map(membership, theme_ids)
    coverage = {
        **membership_cov,
        "input_rows": 0,
        "eligible_events": 0,
        "shown_events": 0,
        "omitted_events": 0,
        "themes_with_events": 0,
        "themes_represented": 0,
        "excluded": {
            "invalid_first_seen": 0,
            "not_yet_seen": 0,
            "outside_context_window": 0,
            "outside_theme_membership": 0,
            "missing_event_identity": 0,
            "invalid_source_date": 0,
            "source_date_after_first_seen": 0,
            "duplicate_identical_accession": 0,
            "conflicting_accession": 0,
        },
    }
    out["coverage"] = coverage

    if not isinstance(events, pd.DataFrame):
        out["reason"] = "invalid_source_frame"
        return out
    coverage["input_rows"] = len(events)
    missing_columns = sorted(_REQUIRED_EVENT_COLUMNS - set(events.columns))
    if missing_columns:
        out["reason"] = "missing_required_columns"
        coverage["missing_required_columns"] = missing_columns
        return out
    if not ticker_themes:
        out["status"] = "empty"
        out["reason"] = "no_resolved_theme_membership"
        return out

    start = cutoff - pd.Timedelta(days=window_days)
    excluded = Counter()
    by_accession: dict[str, dict] = {}
    conflicted: set[str] = set()

    for raw in events.to_dict("records"):
        event = _normalized_event(
            raw, ticker_themes=ticker_themes, cutoff=cutoff, start=start, excluded=excluded)
        if event is None:
            continue
        accession = event["reports"][0]["accession"]
        if accession in conflicted:
            excluded["conflicting_accession"] += 1
            continue
        prior = by_accession.get(accession)
        if prior is None:
            by_accession[accession] = event
            continue

        def comparable(value: dict) -> dict:
            return {k: v for k, v in value.items() if k != "_sort_ts"}

        if comparable(prior) == comparable(event):
            excluded["duplicate_identical_accession"] += 1
        else:
            excluded["conflicting_accession"] += 2
            conflicted.add(accession)
            by_accession.pop(accession, None)

    normalized = list(by_accession.values())
    normalized.sort(key=lambda event: (event["_sort_ts"], event["event_key"]), reverse=True)
    coverage["eligible_events"] = len(normalized)
    coverage["themes_with_events"] = len(
        {theme for event in normalized for theme in event["theme_ids"]})

    selected = _coverage_first(normalized, max_events)
    coverage["shown_events"] = len(selected)
    coverage["omitted_events"] = max(0, len(normalized) - len(selected))
    coverage["themes_represented"] = len(
        {theme for event in selected for theme in event["theme_ids"]})
    for key in coverage["excluded"]:
        coverage["excluded"][key] = int(excluded.get(key, 0))

    for event in selected:
        event.pop("_sort_ts", None)
    out["events"] = selected
    if not normalized:
        out["status"] = "empty"
        out["reason"] = "no_known_in_window_member_events"
    elif coverage["omitted_events"] or coverage["themes_represented"] < coverage["themes_with_events"]:
        out["status"] = "partial"
        out["reason"] = "event_budget_partial"
    else:
        out["status"] = "ready"
        out["reason"] = None
    return out


def build_sec_event_context(
    *,
    root: str | Path | None = None,
    theme_ids: Iterable[str] | None = None,
    knowledge_cutoff: str | datetime | pd.Timestamp | None = None,
    window_days: int = DEFAULT_WINDOW_DAYS,
    max_events: int = DEFAULT_MAX_EVENTS,
) -> dict:
    """Load existing SEC/membership owners and project a prospective thematic context.

    Never fetches the network. Missing/corrupt source files return typed unavailable;
    absence is not converted into an empty/no-catalyst conclusion.
    """
    cutoff = _aware(knowledge_cutoff)
    if knowledge_cutoff is None:
        cutoff = pd.Timestamp(datetime.now(timezone.utc))
    if cutoff is None:
        fallback = pd.Timestamp(datetime.now(timezone.utc))
        out = _base(
            cutoff=fallback,
            window_days=window_days if isinstance(window_days, int) else DEFAULT_WINDOW_DAYS,
            source_snapshot_ref=None, membership_snapshot_ref=None)
        out["reason"] = "invalid_knowledge_cutoff"
        return out

    repo_root = Path(root) if root is not None else Path(config.ROOT)
    data_root = repo_root / "data"
    source = data_root / "edgar" / "material_8k_events.parquet"
    membership_path = data_root / "baskets" / "membership.json"
    if not source.exists() or not membership_path.exists():
        out = _base(
            cutoff=cutoff,
            window_days=window_days if isinstance(window_days, int) else DEFAULT_WINDOW_DAYS,
            source_snapshot_ref=None, membership_snapshot_ref=None)
        out["reason"] = "source_files_unavailable"
        return out

    rights_posture = _sec_rights_posture(repo_root)
    if rights_posture.get("status") != "admitted":
        out = _base(
            cutoff=cutoff,
            window_days=window_days if isinstance(window_days, int) else DEFAULT_WINDOW_DAYS,
            source_snapshot_ref=None, membership_snapshot_ref=None,
            rights_posture=rights_posture)
        out["reason"] = "source_rights_not_admitted"
        return out

    try:
        source_digest = _sha256_file(source)
        membership_bytes = membership_path.read_bytes()
        membership_digest = sha256(membership_bytes).hexdigest()
        membership = json.loads(membership_bytes)
        events = pd.read_parquet(source)
    except Exception:  # noqa: BLE001
        out = _base(
            cutoff=cutoff,
            window_days=window_days if isinstance(window_days, int) else DEFAULT_WINDOW_DAYS,
            source_snapshot_ref=None, membership_snapshot_ref=None)
        out["reason"] = "source_read_failed"
        return out

    return project_sec_event_context(
        events, membership, theme_ids=theme_ids, knowledge_cutoff=cutoff,
        window_days=window_days, max_events=max_events,
        source_snapshot_ref=_source_ref(SOURCE_PATH, source_digest),
        membership_snapshot_ref=_source_ref(MEMBERSHIP_PATH, membership_digest),
        rights_posture=rights_posture,
    )
