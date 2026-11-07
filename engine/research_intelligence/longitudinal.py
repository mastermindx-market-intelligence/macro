"""Deterministic W5 longitudinal stream identity and predecessor selection.

This module is intentionally read-only.  It extends the existing Qualitative
Research Intelligence owner with exact longitudinal identity; it does not compare
beliefs, persist transitions, infer motives, or create a second identity plane.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
import re
from typing import Any

from engine.research_vault.sidecar import canon_institution, institution_is_desk
from lib.dataos.identity import VendorAliasTable


ELIGIBLE = "eligible"
SELECTED = "selected"
NO_PREDECESSOR = "no_predecessor"

ABSTAIN_MISSING_REPORT_ID = "abstain_missing_report_id"
ABSTAIN_MISSING_OR_INVALID_INSTITUTION = "abstain_missing_or_invalid_institution"
ABSTAIN_MISSING_DESK = "abstain_missing_desk"
ABSTAIN_TICKER_CARDINALITY = "abstain_ticker_cardinality"
ABSTAIN_NO_EXACT_SECURITY_SUBJECT = "abstain_no_exact_security_subject"
ABSTAIN_SUBJECT_CONFLICT = "abstain_subject_conflict"
ABSTAIN_INVALID_PUBLISHED_AT = "abstain_invalid_published_at"
ABSTAIN_UNRESOLVED_SECURITY = "abstain_unresolved_security"
ABSTAIN_AMBIGUOUS_PREDECESSOR = "abstain_ambiguous_predecessor"
ABSTAIN_CONFLICTING_REPORT_RECORD = "abstain_conflicting_report_record"


@dataclass(frozen=True, slots=True)
class StreamObservation:
    """One exact, identity-safe Research Vault observation."""

    report_id: str
    institution: str
    institution_at_observation: str
    desk: str
    desk_key: str
    security_id: str
    ticker_at_observation: str
    ticker_source: str
    ticker_evidence: str
    published_at: datetime
    published_at_source: str
    observation_date: date

    @property
    def stream_key(self) -> tuple[str, str, str]:
        return (self.institution, self.desk_key, self.security_id)


@dataclass(frozen=True, slots=True)
class StreamResolution:
    state: str
    observation: StreamObservation | None = None


@dataclass(frozen=True, slots=True)
class PredecessorSelection:
    state: str
    current: StreamObservation | None = None
    predecessor: StreamObservation | None = None


_TITLE_SECURITY_SUBJECT = re.compile(
    r"^(?P<label>[A-Z][A-Za-z0-9&.,'’+/\-–— ]{1,63})\s+"
    r"\((?P<ticker>[A-Z][A-Z0-9]{0,4}(?:\.[A-Z]{1,4})?)\)(?:\s|$)"
)
_COMPANY_DESIGNATORS = frozenset({
    "INC", "INC.", "CORP", "CORP.", "CORPORATION", "CO", "CO.", "COMPANY",
    "LTD", "LTD.", "LIMITED", "PLC", "GROUP", "HOLDING", "HOLDINGS", "SE",
    "S.E.", "AG", "NV", "N.V.", "SA", "S.A.", "LLC", "LP", "L.P.",
})


def _sidecar_ticker(value: object) -> tuple[str, str | None]:
    if value is None:
        return "empty", None
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return "invalid", None
    tickers = {
        item.strip().upper()
        for item in value
        if isinstance(item, str) and item.strip()
    }
    if not tickers:
        return "empty", None
    if len(tickers) != 1:
        return "multi", None
    return "single", next(iter(tickers))


def _strict_title_ticker(value: object) -> tuple[str, str] | None:
    """Extract only an explicit leading Company Name (TICKER) source form.

    This deliberately refuses generic parenthetical-token matching. The subject
    label must be near the start, contain lowercase letters so an all-caps macro
    acronym is not treated as a company, and cannot end in a short all-caps token
    after a long prose label. The Data OS alias table remains the identity owner;
    this function only recovers an observed symbol candidate from source syntax.
    """

    if not isinstance(value, str):
        return None
    match = _TITLE_SECURITY_SUBJECT.match(value.strip())
    if match is None:
        return None
    label = " ".join(match.group("label").split())
    words = label.split()
    if not words:
        return None

    # Two deliberately narrow admitted forms:
    #   1. a single mixed-case brand (CrowdStrike, AstraZeneca, Carrefour);
    #   2. a multi-word name ending in an explicit company/legal designator.
    # Generic research concepts such as "Brazilian Real (BRL)" and
    # "Transformational Innovation Opportunities (TRIO)" are therefore refused
    # even if their acronym happens to collide with a real listed symbol.
    single_brand = (
        len(words) == 1
        and len(label) >= 5
        and any(ch.islower() for ch in label)
    )
    designator = (
        len(words) >= 2
        and words[-1].upper() in _COMPANY_DESIGNATORS
        and any(ch.islower() for ch in label)
    )
    if not (single_brand or designator):
        return None
    return match.group("ticker").upper(), match.group(0).rstrip()


def _observed_ticker(item: Mapping[str, Any]) -> tuple[str | None, str, str]:
    state, sidecar = _sidecar_ticker(item.get("tickers"))
    if state in {"invalid", "multi"}:
        return None, ABSTAIN_TICKER_CARDINALITY, ""

    title_subject = _strict_title_ticker(item.get("title"))
    title_ticker = title_subject[0] if title_subject is not None else None
    if sidecar is not None:
        if title_ticker is not None and title_ticker != sidecar:
            return None, ABSTAIN_SUBJECT_CONFLICT, ""
        return sidecar, "sidecar_ticker", sidecar
    if title_subject is not None:
        return title_subject[0], "source_title_explicit_ticker", title_subject[1]
    return None, ABSTAIN_NO_EXACT_SECURITY_SUBJECT, ""


def _published_at(value: object) -> tuple[datetime, date, str] | None:
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    iso = raw[:-1] + "+00:00" if raw.endswith(("Z", "z")) else raw
    try:
        parsed = datetime.fromisoformat(iso)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    observation_date = parsed.date()
    return parsed.astimezone(timezone.utc), observation_date, raw


def _desk_key(value: str) -> str:
    return " ".join(value.split()).casefold()


def resolve_stream_observation(
    item: Mapping[str, Any],
    aliases: VendorAliasTable,
) -> StreamResolution:
    """Resolve one Research Vault row to an exact W5 stream identity.

    A report is eligible only when its institution, desk, single observed ticker,
    exact timestamp, and historical security identity are all provable without
    guessing.  The current issuer master is deliberately not consulted.
    """

    report_id = str(item.get("id") or item.get("report_id") or "").strip()
    if not report_id:
        return StreamResolution(ABSTAIN_MISSING_REPORT_ID)

    institution_raw = str(item.get("institution") or "").strip()
    institution = canon_institution(institution_raw)
    if not institution or not institution_is_desk(institution):
        return StreamResolution(ABSTAIN_MISSING_OR_INVALID_INSTITUTION)

    desk = str(item.get("desk") or "").strip()
    if not desk:
        return StreamResolution(ABSTAIN_MISSING_DESK)
    desk_key = _desk_key(desk)
    if not desk_key:
        return StreamResolution(ABSTAIN_MISSING_DESK)

    ticker, ticker_source, ticker_evidence = _observed_ticker(item)
    if ticker is None:
        return StreamResolution(ticker_source)

    published = _published_at(item.get("published_at"))
    if published is None:
        return StreamResolution(ABSTAIN_INVALID_PUBLISHED_AT)
    published_at, observation_date, published_at_source = published

    security_id = aliases.resolve("membership", ticker, on=observation_date)
    if not security_id:
        return StreamResolution(ABSTAIN_UNRESOLVED_SECURITY)

    return StreamResolution(
        ELIGIBLE,
        StreamObservation(
            report_id=report_id,
            institution=institution,
            institution_at_observation=institution_raw,
            desk=desk,
            desk_key=desk_key,
            security_id=security_id,
            ticker_at_observation=ticker,
            ticker_source=ticker_source,
            ticker_evidence=ticker_evidence,
            published_at=published_at,
            published_at_source=published_at_source,
            observation_date=observation_date,
        ),
    )


def select_predecessor(
    current_item: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    aliases: VendorAliasTable,
) -> PredecessorSelection:
    """Select the newest strictly-earlier eligible report in the exact W5 stream.

    Candidate rows that are not independently eligible never become synthetic
    evidence.  Duplicate identical rows collapse; the same report id resolving to
    conflicting observations fails closed.  A latest-timestamp tie across distinct
    reports is ambiguous and is never broken by input order or report-id ordering.
    """

    current_resolution = resolve_stream_observation(current_item, aliases)
    if current_resolution.state != ELIGIBLE or current_resolution.observation is None:
        return PredecessorSelection(current_resolution.state)

    current = current_resolution.observation
    eligible_by_id: dict[str, StreamObservation] = {}

    for candidate_item in candidates:
        candidate_resolution = resolve_stream_observation(candidate_item, aliases)
        if candidate_resolution.state != ELIGIBLE or candidate_resolution.observation is None:
            continue
        candidate = candidate_resolution.observation
        if candidate.report_id == current.report_id:
            continue
        if candidate.stream_key != current.stream_key:
            continue
        if candidate.published_at >= current.published_at:
            continue

        previous = eligible_by_id.get(candidate.report_id)
        if previous is not None and previous != candidate:
            return PredecessorSelection(
                ABSTAIN_CONFLICTING_REPORT_RECORD,
                current=current,
            )
        eligible_by_id[candidate.report_id] = candidate

    if not eligible_by_id:
        return PredecessorSelection(NO_PREDECESSOR, current=current)

    latest_time = max(row.published_at for row in eligible_by_id.values())
    latest = tuple(
        row for row in eligible_by_id.values()
        if row.published_at == latest_time
    )
    if len(latest) != 1:
        return PredecessorSelection(
            ABSTAIN_AMBIGUOUS_PREDECESSOR,
            current=current,
        )

    return PredecessorSelection(
        SELECTED,
        current=current,
        predecessor=latest[0],
    )
