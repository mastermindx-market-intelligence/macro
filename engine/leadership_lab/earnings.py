"""Pure consumer of the incumbent Prophet Earnings detail contract.

Leadership Lab does not fetch Company Intelligence, discover earnings events, compute
expectations, or create trading authority. It accepts already-produced
prophet.episode_earnings_detail/v1 payloads and binds them only through the
native Prophet episode identity established by the current-context adapter.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import datetime
import re

from engine.leadership_lab.measurement import finite_number
from lib.dataos.identity import IdentityError, IssuerMaster


_AUTHORITY = {
    "rank": False,
    "entry": False,
    "size": False,
    "execution": False,
    "trade": False,
}
_METHOD_SCOPE = "RETROSPECTIVE_FACTUAL_RECONSTRUCTION_NO_AS_RUN_PROMOTION"
_TIME_INTERPRETATION = "ORIGINAL_SOURCE_VINTAGE_RECONSTRUCTION_NOT_ORIGINAL_RECOMMENDATION"
_MAX_EVIDENCE_ROWS = 128
_MAX_TEXT = 2048
_PROJECTION_RE = re.compile(r"piv:[0-9a-f]{64}")
_EARNINGS_ISSUER_RE = re.compile(r"cik:[0-9]{10}")
_DECISION_CUT_KEYS = frozenset({"opened_at", "opened_session", "anchor_time", "known_at", "tradable_at"})
_TRADABLE_AT = {
    "state": "NOT_ASSERTED", "value": None,
    "basis": "no_us_availability_owner_and_b4_not_built",
}


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if value and len(value) <= _MAX_TEXT else None


def _aware_time(value: object) -> str | None:
    text = _text(value)
    if text is None:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return text


def _all_false(value: object) -> bool:
    return (isinstance(value, Mapping) and set(value) == set(_AUTHORITY)
            and all(flag is False for flag in value.values()))


def _decision_cut(value: object, *, episode: Mapping) -> tuple[dict | None, str | None]:
    if not isinstance(value, Mapping) or frozenset(value) != _DECISION_CUT_KEYS:
        return None, "EPISODE_CLOCK_MISMATCH"
    if value.get("tradable_at") != _TRADABLE_AT:
        return None, "EPISODE_CLOCK_MISMATCH"
    opened_text = _aware_time(value.get("opened_at"))
    anchor_text = _aware_time(value.get("anchor_time"))
    known_text = _aware_time(value.get("known_at"))
    session = _text(value.get("opened_session"))
    if None in (opened_text, anchor_text, known_text, session):
        return None, "EPISODE_CLOCK_MISMATCH"
    opened = datetime.fromisoformat(opened_text.replace("Z", "+00:00"))
    anchor = datetime.fromisoformat(anchor_text.replace("Z", "+00:00"))
    known = datetime.fromisoformat(known_text.replace("Z", "+00:00"))
    if (
        opened != max(anchor, known)
        or session != opened.date().isoformat()
        or opened_text != episode.get("opened_at")
        or session != episode.get("opened_session")
    ):
        return None, "EPISODE_CLOCK_MISMATCH"
    return deepcopy(dict(value)), None


def _qualified_subject_binding(
    value: object, *, episode: Mapping, event_id: str, issuer_id: str,
) -> bool:
    if not isinstance(value, Mapping) or set(value) != {
        "state", "episode_company_id", "earnings_company_id", "owner_subject_id"
    }:
        return False
    earnings_issuer = _text(value.get("earnings_company_id"))
    return (
        value.get("state") == "RESOLVED"
        and value.get("episode_company_id") == episode.get("company_id")
        and earnings_issuer is not None
        and _EARNINGS_ISSUER_RE.fullmatch(earnings_issuer) is not None
        and earnings_issuer == issuer_id
        and value.get("owner_subject_id") == event_id
    )


def _current_native_issuer_cik(master: object, episode: Mapping) -> str | None:
    """Reuse the canonical Data OS *current* issuer reader; never infer historical lineage.

    A caller's RESOLVED subject tuple is only a claim. Both the security/issuer
    relation and CIK must agree with the existing IssuerMaster. Superseded or
    provisional records are ineligible. The source pin/loader is owned by the
    builder; this pure function does not open files or allocate identities.
    """
    if not isinstance(master, IssuerMaster):
        return None
    security = _text(episode.get("security_id"))
    company = _text(episode.get("company_id"))
    if security is None or company is None:
        return None
    try:
        if (
            master.issuer_of_security(security) != company
            or security not in master.securities_of_issuer(company)
        ):
            return None
        matching = [row for row in master.rows if row.security_id == security]
        if (
            len(matching) != 1
            or matching[0].issuer_state != "RESOLVED"
            or matching[0].security_state not in (None, "")
        ):
            return None
        cik = master.cik_of_issuer(company)
    except IdentityError:
        return None
    if not isinstance(cik, str) or re.fullmatch(r"[0-9]{10}", cik) is None:
        return None
    return "cik:" + cik


def _string_list(value: object, *, limit: int = _MAX_EVIDENCE_ROWS) -> list[str] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) > limit:
        return None
    out: list[str] = []
    for item in value:
        text = _text(item)
        if text is None:
            return None
        out.append(text)
    return out


def _safe_values(value: object) -> dict[str, object] | None:
    if not isinstance(value, Mapping) or len(value) > 24:
        return None
    out: dict[str, object] = {}
    for key, raw in value.items():
        name = _text(key)
        if name is None:
            return None
        if raw is None or isinstance(raw, (str, bool, int)):
            out[name] = raw
            continue
        number = finite_number(raw)
        if number is None:
            return None
        out[name] = number
    return out


def _brief_items(value: object) -> list[dict] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) > _MAX_EVIDENCE_ROWS:
        return None
    out = []
    for raw in value:
        if not isinstance(raw, Mapping):
            return None
        code = _text(raw.get("code"))
        text = _text(raw.get("text"))
        ref = _text(raw.get("evidence_ref"))
        values = _safe_values(raw.get("values", {}))
        if code is None or text is None or ref is None or values is None:
            return None
        out.append({"code": code, "text": text, "evidence_ref": ref, "values": values})
    return out


def _reported_change(raw: object) -> dict | None:
    if not isinstance(raw, Mapping):
        return None
    metric = _text(raw.get("metric"))
    current_period = _text(raw.get("current_fiscal_period"))
    prior_period = _text(raw.get("prior_fiscal_period"))
    units = _text(raw.get("units"))
    currency = _text(raw.get("currency"))
    basis = _text(raw.get("basis"))
    current_available_at = _aware_time(raw.get("current_available_at"))
    current = finite_number(raw.get("current_value"))
    prior = finite_number(raw.get("prior_value"))
    change_pct = finite_number(raw.get("change_pct"))
    if (
        metric is None or current_period is None or prior_period is None
        or units is None or currency is None or basis is None
        or current_available_at is None
        or current is None or prior is None or change_pct is None
    ):
        return None
    return {
        "metric": metric,
        "current_fiscal_period": current_period,
        "prior_fiscal_period": prior_period,
        "current_value": current,
        "prior_value": prior,
        "units": units,
        "currency": currency,
        "basis": basis,
        "change_pct": change_pct,
        "current_available_at": current_available_at,
        "source_contract_ref": _text(raw.get("source_contract_ref")),
    }


def _project_detail(
    payload: object, *, episode: Mapping, generation_id: str,
    subject_binding: Mapping | None, issuer_master: IssuerMaster | None,
    episode_generation_validated: bool,
) -> tuple[dict | None, str | None]:
    if not isinstance(payload, Mapping) or payload.get("schema") != "prophet.episode_earnings_detail/v1":
        return None, "OWNER_SCHEMA_MISMATCH"
    if not _all_false(payload.get("authority")):
        return None, "OWNER_AUTHORITY_DRIFT"
    projection_id = _text(payload.get("source_projection_id"))
    if projection_id is None or _PROJECTION_RE.fullmatch(projection_id) is None:
        return None, "OWNER_PROJECTION_REFERENCE_INVALID"
    if (
        payload.get("method_scope") != _METHOD_SCOPE
        or payload.get("time_interpretation") != _TIME_INTERPRETATION
        or payload.get("is_original_as_run_recommendation") is not False
    ):
        return None, "OWNER_METHOD_SCOPE_DRIFT"

    ref = payload.get("episode_ref")
    if not isinstance(ref, Mapping):
        return None, "EPISODE_IDENTITY_MISMATCH"
    if (
        ref.get("schema") != "prophet.candidate_episode/v1"
        or ref.get("episode_id") != episode.get("episode_id")
        or ref.get("generation_id") != generation_id
        or ref.get("identity_ref") != episode.get("company_id")
    ):
        return None, "EPISODE_IDENTITY_MISMATCH"

    if not episode_generation_validated:
        return None, "EARNINGS_EPISODE_GENERATION_UNVERIFIED"
    if issuer_master is None:
        return None, "EARNINGS_NATIVE_ISSUER_UNAVAILABLE"
    expected_cik = _current_native_issuer_cik(issuer_master, episode)
    if expected_cik is None:
        return None, "EARNINGS_NATIVE_ISSUER_MISMATCH"

    cut, cut_error = _decision_cut(payload.get("decision_cut"), episode=episode)
    if cut_error is not None or cut is None:
        return None, cut_error or "EPISODE_CLOCK_MISMATCH"

    headline = _text(payload.get("headline"))
    interpretation = _text(payload.get("interpretation"))
    comparison_state = _text(payload.get("comparison_state"))
    missing = _string_list(payload.get("missing"))
    if headline is None or interpretation is None or comparison_state is None or missing is None:
        return None, "OWNER_PAYLOAD_INVALID"

    coverage_out = None
    coverage = payload.get("coverage")
    if isinstance(coverage, Mapping):
        coverage_out = {
            "state": _text(coverage.get("state")),
            "basis": _text(coverage.get("basis")),
        }

    reported: list[dict] = []
    dossier = payload.get("dossier")
    brief_out = None
    not_established = set(missing)
    event_id = issuer_id = None
    if dossier is not None:
        if (
            not isinstance(dossier, Mapping)
            or dossier.get("schema") != "prophet.earnings_dossier/v1"
            or not _all_false(dossier.get("authority"))
        ):
            return None, "OWNER_AUTHORITY_DRIFT"
        decision_clock = _aware_time(cut.get("opened_at"))
        if decision_clock is None or dossier.get("decision_at") != decision_clock:
            return None, "EPISODE_CLOCK_MISMATCH"
        decision_time = datetime.fromisoformat(decision_clock.replace("Z", "+00:00"))
        event_id = _text(dossier.get("event_id"))
        issuer_id = _text(dossier.get("issuer_id"))
        if event_id is None or issuer_id is None:
            return None, "OWNER_PAYLOAD_INVALID"
        if issuer_id != expected_cik:
            return None, "EARNINGS_NATIVE_ISSUER_MISMATCH"
        if subject_binding is None:
            return None, "EARNINGS_SUBJECT_BINDING_UNAVAILABLE"
        if not _qualified_subject_binding(
            subject_binding, episode=episode, event_id=event_id, issuer_id=issuer_id
        ):
            return None, "EARNINGS_SUBJECT_BINDING_MISMATCH"
        changes = dossier.get("reported_changes")
        if (
            not isinstance(changes, Sequence) or isinstance(changes, (str, bytes))
            or len(changes) > _MAX_EVIDENCE_ROWS
        ):
            return None, "OWNER_PAYLOAD_INVALID"
        for raw in changes:
            if not isinstance(raw, Mapping):
                return None, "OWNER_PAYLOAD_INVALID"
            if (
                raw.get("issuer_id") != issuer_id
                or raw.get("current_event_id") != event_id
                or _text(raw.get("prior_event_id")) is None
                or raw.get("decision_at") != decision_clock
            ):
                return None, "EARNINGS_SUBJECT_BINDING_MISMATCH"
            current_available = _aware_time(raw.get("current_available_at"))
            prior_available = _aware_time(raw.get("prior_available_at"))
            if current_available is None or prior_available is None:
                return None, "OWNER_PAYLOAD_INVALID"
            if (
                datetime.fromisoformat(current_available.replace("Z", "+00:00")) > decision_time
                or datetime.fromisoformat(prior_available.replace("Z", "+00:00")) > decision_time
            ):
                return None, "EPISODE_CLOCK_MISMATCH"
            projected = _reported_change(raw)
            if projected is None:
                return None, "OWNER_PAYLOAD_INVALID"
            reported.append(projected)

        brief = payload.get("evidence_brief")
        if brief is not None:
            if (
                not isinstance(brief, Mapping)
                or brief.get("schema") != "prophet.earnings_evidence_brief/v1"
                or not _all_false(brief.get("authority"))
                or brief.get("event_id") != event_id
                or brief.get("issuer_id") != issuer_id
                or brief.get("decision_at") != cut.get("opened_at")
            ):
                return None, "OWNER_AUTHORITY_DRIFT"
            summary_state = _text(brief.get("summary_state"))
            supporting = _brief_items(brief.get("supporting_facts"))
            counters = _brief_items(brief.get("counterevidence"))
            context = _brief_items(brief.get("context_facts"))
            unresolved = _string_list(brief.get("not_established"))
            if (
                summary_state is None or supporting is None or counters is None
                or context is None or unresolved is None
            ):
                return None, "OWNER_PAYLOAD_INVALID"
            not_established.update(unresolved)
            brief_out = {
                "summary_state": summary_state,
                "supporting_facts": supporting,
                "counterevidence": counters,
                "context_facts": context,
                "not_established": sorted(set(unresolved)),
                "interpretation": _text(brief.get("interpretation")),
            }

    return {
        "status": "AVAILABLE",
        "source_projection_id": projection_id,
        "decision_cut": deepcopy(cut),
        "source_authentication": "CALLER_SUPPLIED_OWNER_OUTPUT_NOT_INDEPENDENTLY_ATTESTED",
        "identity_scope": "CURRENT_ISSUER_MASTER_ONLY_NOT_PIT",
        "historical_identity_qualified": False,
        "headline": headline,
        "interpretation": interpretation,
        "comparison_state": comparison_state,
        "coverage": coverage_out,
        "event_id": event_id,
        "issuer_id": issuer_id,
        "reported_changes": reported,
        "brief": brief_out,
        "not_established": sorted(not_established),
        "forecast_probability": None,
        "catalyst_probability": None,
        "rerating_probability": None,
        "authority": dict(_AUTHORITY),
    }, None


def attach_earnings_evidence(
    view: Mapping, details_by_episode: Mapping[str, Mapping], *,
    subject_bindings_by_episode: Mapping[str, Mapping] | None = None,
    issuer_master: IssuerMaster | None = None,
) -> dict:
    """Attach already-produced Earnings details through exact native episode ids."""
    if (
        not isinstance(view, Mapping)
        or view.get("schema") != "mastermind.leadership_lab.recovery.v1"
        or not isinstance(view.get("current_context"), Mapping)
    ):
        raise ValueError("Leadership Lab current-context view required")
    if not isinstance(details_by_episode, Mapping):
        raise ValueError("earnings detail mapping required")
    if subject_bindings_by_episode is not None and not isinstance(subject_bindings_by_episode, Mapping):
        raise ValueError("earnings subject-binding mapping required")
    if issuer_master is not None and not isinstance(issuer_master, IssuerMaster):
        raise ValueError("native Data OS IssuerMaster required")

    result = deepcopy(dict(view))
    episode_book = result["current_context"].get("episode_book")
    generation_id = (
        _text(episode_book.get("generation_id"))
        if isinstance(episode_book, Mapping) and episode_book.get("status") == "AVAILABLE"
        else None
    )
    proof = episode_book.get("source_validation") if isinstance(episode_book, Mapping) else None
    generation_validated = (
        isinstance(proof, Mapping)
        and proof.get("status") == "VALIDATED_CANONICAL_OWNER"
    )

    def enrich(raw: object) -> dict:
        if not isinstance(raw, Mapping):
            raise ValueError("Leadership Lab row must be a mapping")
        row = deepcopy(dict(raw))
        current = row.get("current_context")
        if not isinstance(current, Mapping):
            raise ValueError("Leadership Lab row current_context required")
        current = deepcopy(dict(current))
        episode = current.get("episode")
        if not isinstance(episode, Mapping) or episode.get("status") != "AVAILABLE":
            current["earnings"] = {
                "status": "UNAVAILABLE", "reason": "NO_NATIVE_EPISODE_ID"}
            row["current_context"] = current
            return row
        episode_id = _text(episode.get("episode_id"))
        if episode_id is None or generation_id is None:
            current["earnings"] = {
                "status": "UNAVAILABLE", "reason": "NO_NATIVE_EPISODE_ID"}
            row["current_context"] = current
            return row
        payload = details_by_episode.get(episode_id)
        if payload is None:
            current["earnings"] = {
                "status": "UNAVAILABLE", "reason": "NO_EARNINGS_DETAIL"}
            row["current_context"] = current
            return row
        binding = (
            subject_bindings_by_episode.get(episode_id)
            if isinstance(subject_bindings_by_episode, Mapping) else None
        )
        projected, refusal = _project_detail(
            payload, episode=episode, generation_id=generation_id,
            subject_binding=binding, issuer_master=issuer_master,
            episode_generation_validated=generation_validated)
        current["earnings"] = (
            projected if projected is not None
            else {"status": "REFUSED", "reason": refusal}
        )
        row["current_context"] = current
        return row

    rows = result.get("rows")
    shortlist = result.get("shortlist")
    if not isinstance(rows, list) or not isinstance(shortlist, list):
        raise ValueError("Leadership Lab rows and shortlist required")
    result["rows"] = [enrich(row) for row in rows]
    result["shortlist"] = [enrich(row) for row in shortlist]

    statuses = [
        row["current_context"]["earnings"]["status"]
        for row in result["rows"]
    ]
    result["current_context"]["earnings"] = {
        "schema": "mastermind.leadership_lab.earnings_context.v1",
        "mode": "EXISTING_OWNER_OUTPUT_ONLY",
        "available_rows": statuses.count("AVAILABLE"),
        "refused_rows": statuses.count("REFUSED"),
        "unavailable_rows": statuses.count("UNAVAILABLE"),
        "probability_calibration": "NOT_CONNECTED",
        "identity_scope": "CURRENT_ISSUER_MASTER_ONLY_NOT_PIT",
        "historical_identity_qualified": False,
        "authority": dict(_AUTHORITY),
    }
    return result
