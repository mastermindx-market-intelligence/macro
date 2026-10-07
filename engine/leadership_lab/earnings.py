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

from engine.leadership_lab.measurement import finite_number


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
) -> tuple[dict | None, str | None]:
    if not isinstance(payload, Mapping) or payload.get("schema") != "prophet.episode_earnings_detail/v1":
        return None, "OWNER_SCHEMA_MISMATCH"
    if not _all_false(payload.get("authority")):
        return None, "OWNER_AUTHORITY_DRIFT"
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

    cut = payload.get("decision_cut")
    if not isinstance(cut, Mapping):
        return None, "EPISODE_CLOCK_MISMATCH"
    if (
        cut.get("opened_at") != episode.get("opened_at")
        or cut.get("opened_session") != episode.get("opened_session")
    ):
        return None, "EPISODE_CLOCK_MISMATCH"

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
        changes = dossier.get("reported_changes")
        if (
            not isinstance(changes, Sequence) or isinstance(changes, (str, bytes))
            or len(changes) > _MAX_EVIDENCE_ROWS
        ):
            return None, "OWNER_PAYLOAD_INVALID"
        for raw in changes:
            projected = _reported_change(raw)
            if projected is None:
                return None, "OWNER_PAYLOAD_INVALID"
            available = datetime.fromisoformat(projected["current_available_at"].replace("Z", "+00:00"))
            if available > decision_time:
                return None, "EPISODE_CLOCK_MISMATCH"
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
        "source_projection_id": _text(payload.get("source_projection_id")),
        "decision_cut": {key: deepcopy(cut[key]) for key in
                         ("opened_at", "opened_session", "anchor_time", "known_at") if key in cut},
        "source_authentication": "CALLER_SUPPLIED_OWNER_OUTPUT_NOT_INDEPENDENTLY_ATTESTED",
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
    view: Mapping, details_by_episode: Mapping[str, Mapping],
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

    result = deepcopy(dict(view))
    episode_book = result["current_context"].get("episode_book")
    generation_id = (
        _text(episode_book.get("generation_id"))
        if isinstance(episode_book, Mapping) and episode_book.get("status") == "AVAILABLE"
        else None
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
        projected, refusal = _project_detail(
            payload, episode=episode, generation_id=generation_id)
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
        "authority": dict(_AUTHORITY),
    }
    return result
