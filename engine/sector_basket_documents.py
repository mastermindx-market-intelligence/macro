"""Data-only basket and Sector Brief documents from captured owner outputs.

This module acquires and publishes nothing. Existing engines retain calculation,
calendar, history and ledger ownership. Legacy builders reuse its display helpers.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timezone
import json

from engine.sector_pulse import enrich_theme_intel_from_inputs
from engine.theme_context import ThemeContextInputs, compute_theme_context_from_inputs
from engine.us_act_now import assemble_bottoming_watch


def attach_bottoming_watch(ti: dict, *, cycle_rows: list[dict] | None,
                           sector_names_zh: Mapping[str, str]) -> dict | None:
    """Apply existing display fields to a caller-owned theme document, with no reads."""
    if not ti or not isinstance(ti.get("act_now"), dict):
        return None
    _an_ba = ti["act_now"]
    _zh_ba = {}
    for theme in ti.get("themes") or []:
        if theme.get("id") and theme.get("name_zh"):
            _zh_ba[theme["id"]] = theme["name_zh"]
    _zh_ba.update(sector_names_zh)
    _bw = assemble_bottoming_watch(cycle_rows,
        reduce_ids=[row.get("id") for row in (_an_ba.get("reduce") or []) if row.get("id")],
        names_zh=_zh_ba)
    _an_ba["bottoming_watch"] = _bw["bottoming_watch"]
    _an_ba["dual_read_ids"] = _bw["dual_read_ids"]
    _an_ba["recovering_ids"] = _bw["recovering_ids"]
    _an_ba["bottoming_authority"] = _bw["authority"]
    return _bw


def factor_season_from_inputs(document: dict | None) -> dict | None:
    """The existing optional factor-season chip; no new interpretation or clock."""
    factor_season = None
    try:
        _seas_raw = document
        _seas_now = _seas_raw.get("now") if isinstance(_seas_raw, dict) else None
        if (
            isinstance(_seas_raw, dict)
            and _seas_raw.get("schema") == "factor_seasonality.v2"
            and isinstance(_seas_now, dict)
            and _seas_now.get("chip_en")
        ):
            _factor_list = _seas_now.get("factors") or []
            _mom = next((f for f in _factor_list if f.get("key") == "momentum"), None)
            _any_non_neutral = (
                (_mom and _mom.get("verdict") != "neutral")
                or any(f.get("verdict") != "neutral" for f in _factor_list if f.get("key") != "momentum")
            )
            if _any_non_neutral:
                _mom_verdict = (_mom or {}).get("verdict", "neutral")
                _tone = _mom_verdict if _mom_verdict != "neutral" else next(
                    (f.get("verdict") for f in _factor_list if f.get("verdict") != "neutral"),
                    "neutral",
                )
                factor_season = {
                    "chip_en": _seas_now.get("chip_en"),
                    "chip_zh": _seas_now.get("chip_zh"),
                    "tip_en": (
                        (_seas_now.get("headline_en") or "")
                        + (" " + _seas_now.get("stance_en") if _seas_now.get("stance_en") else "")
                    ).strip(),
                    "tip_zh": (
                        (_seas_now.get("headline_zh") or "")
                        + (" " + _seas_now.get("stance_zh") if _seas_now.get("stance_zh") else "")
                    ).strip(),
                    "tone": _tone,
                }
    except Exception:  # noqa: BLE001 — existing optional display degradation
        return None
    return factor_season


def basket_member_symbols(data: dict) -> list[str]:
    """Project computed basket rows exactly as the incumbent quote-scrape handoff."""
    return sorted({
        str(m.get("symbol", "")).strip().upper()
        for b in data.get("baskets", [])
        for m in (b.get("members") or [])
        if m.get("symbol")
    })


def make_si_handoff(*, theme_context, factor_season, flow, member_symbols, generated_utc):
    """Existing five-field display handoff, separate from publication receipts."""
    _theme_context, _member_syms, built = theme_context, member_symbols, generated_utc
    return {
        "theme_context": _theme_context,
        "factor_season": factor_season,
        "flow": ({"cluster": {"regime": ((flow or {}).get("cluster") or {}).get("regime")}}
                 if (flow or {}).get("cluster") else None),
        "basket_member_syms": _member_syms,
        "generated_utc": built,
    }


@dataclass(frozen=True)
class SectorBasketDocumentInputs:
    source_session: str
    basket_payload: dict
    theme_intel: dict
    allocation: dict
    context_history: Sequence[dict]
    rotation_events: dict | None
    bottoming_cycle_rows: list[dict] | None
    bottoming_ledger_session: str | None
    sector_names_zh: Mapping[str, str]
    factor_seasonality: dict | None
    flow: dict | None
    pulse_archive: list[dict]
    pulse_heat_calibration: dict
    built_at: datetime


@dataclass(frozen=True)
class SectorBasketDocuments:
    baskets: dict
    si_handoff: dict
    pulse: dict | None
    evidence: dict


def _session(value, label):
    if not isinstance(value, str):
        raise ValueError(f"{label}: missing ISO session")
    try:
        valid = date.fromisoformat(value).isoformat() == value
    except ValueError:
        valid = False
    if not valid:
        raise ValueError(f"{label}: invalid ISO session")
    return value


def assemble_sector_basket_documents(inputs: SectorBasketDocumentInputs) -> SectorBasketDocuments:
    """Compose one coherent basket/Brief baseline without pages or deferred writes."""
    value = deepcopy(inputs)
    baseline = _session(value.source_session, "source_session")
    for label, document in (("baskets", value.basket_payload), ("theme_intel", value.theme_intel),
                            ("allocation", value.allocation)):
        if not isinstance(document, dict) or _session(document.get("as_of"), label) != baseline:
            raise ValueError(f"{label}: baseline session mismatch")
    if "chart" not in value.basket_payload:
        raise ValueError("baskets: missing chart")
    if (not isinstance(value.built_at, datetime) or value.built_at.tzinfo is None
            or value.built_at.utcoffset() is None):
        raise ValueError("built_at: explicit aware timestamp required")
    built = value.built_at.astimezone(timezone.utc)
    if built.date().isoformat() < baseline:
        raise ValueError("built_at: before source session")
    ledger_session = value.bottoming_ledger_session
    if ledger_session is not None:
        if _session(ledger_session, "bottoming ledger") > baseline:
            raise ValueError("bottoming ledger: future observation")
    if value.bottoming_cycle_rows is None:
        if ledger_session is not None:
            raise ValueError("bottoming ledger: absent rows have no observation")
    elif not isinstance(value.bottoming_cycle_rows, list):
        raise ValueError("bottoming ledger: invalid rows")
    elif value.bottoming_cycle_rows:
        if ledger_session is None:
            raise ValueError("bottoming ledger: observation required for rows")
        for row in value.bottoming_cycle_rows:
            if not isinstance(row, dict) or _session(row.get("date"), "bottoming row") != ledger_session:
                raise ValueError("bottoming ledger: row session mismatch")

    data = value.basket_payload
    data["theme_intel"] = value.theme_intel
    bottoming = attach_bottoming_watch(data["theme_intel"], cycle_rows=value.bottoming_cycle_rows,
                                       sector_names_zh=value.sector_names_zh)
    enriched, pulse = enrich_theme_intel_from_inputs(data["theme_intel"], "us",
        archive_snapshots=value.pulse_archive, heat_calibration=value.pulse_heat_calibration)
    data["theme_intel"] = enriched
    context = compute_theme_context_from_inputs(ThemeContextInputs(value.allocation, enriched, "us",
        value.context_history, value.rotation_events))
    if context is None or context.get("as_of") != baseline:
        raise ValueError("theme_context: unavailable coherent baseline")
    handoff = make_si_handoff(theme_context=context,
        factor_season=factor_season_from_inputs(value.factor_seasonality), flow=value.flow,
        member_symbols=basket_member_symbols(data), generated_utc=built.strftime("%Y-%m-%d %H:%M UTC"))
    evidence = {"source_session": baseline,
        "bottoming_ledger_session": ledger_session,
        "bottoming_source": ("absent" if value.bottoming_cycle_rows is None else
                             "present" if value.bottoming_cycle_rows else "present_empty"),
        "bottoming_notes": (bottoming or {}).get("notes", []),
        "factor_source_as_of": (value.factor_seasonality.get("as_of") if isinstance(value.factor_seasonality, dict) else None),
        "flow_source_as_of": (value.flow or {}).get("as_of"),
        "pulse_available": pulse is not None,
        "pulse_history": (pulse or {}).get("history"),
        "built_at": built.isoformat()}
    # Serialization is a semantic check only. The generation owner serializes and
    # hashes the final basket bytes once; this helper creates no publication identity.
    try:
        json.dumps([data, handoff, pulse, evidence], allow_nan=False, ensure_ascii=False)
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise ValueError("Sector basket documents are not finite JSON values") from exc
    return SectorBasketDocuments(data, handoff, pulse, evidence)
