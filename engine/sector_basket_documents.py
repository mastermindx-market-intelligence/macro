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


@dataclass(frozen=True)
class SectorWindowCapture:
    """Detached metadata plus an internal observation-consistency witness.

    The digest is not a generation, receipt, freshness or historical-admission
    claim. The published receipt remains the existing Yahoo owner's receipt.
    """
    source_binding: dict
    panel_sha256: str


def _sector_window_rows(panel):
    """Preserve a bounded TR panel as flat primitive rows; never repair it."""
    import hashlib
    import math
    from numbers import Real
    import pandas as pd

    if (not isinstance(panel, pd.DataFrame) or len(panel) > 20000
            or len(panel.columns) > 64 or panel.columns.has_duplicates
            or not isinstance(panel.index, pd.DatetimeIndex)
            or panel.index.hasnans or panel.index.has_duplicates
            or panel.index.tz is not None
            or not panel.index.is_monotonic_increasing
            or not panel.index.equals(panel.index.normalize())
            or any(type(column) is not str or not column or len(column) > 256
                   for column in panel.columns)):
        raise SectorDocumentCompositionError("invalid_sector_window_panel")
    columns = sorted(panel.columns)
    rows = []
    for stamp, values in zip(panel.index, panel[columns].itertuples(index=False, name=None)):
        row = {"session": stamp.date().isoformat()}
        for column, value in zip(columns, values):
            if value is None or value is pd.NA:
                row[column] = None
            elif isinstance(value, Real) and not isinstance(value, bool):
                try:
                    number = float(value)
                except (ValueError, OverflowError) as exc:
                    raise SectorDocumentCompositionError("nonfinite_sector_window_observation") from exc
                if math.isnan(number):
                    row[column] = None  # the captured pandas missing observation
                elif math.isfinite(number):
                    row[column] = number
                else:
                    raise SectorDocumentCompositionError("nonfinite_sector_window_observation")
            else:
                raise SectorDocumentCompositionError("invalid_sector_window_observation")
        rows.append(row)
    encoded = json.dumps(rows, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return rows, hashlib.sha256(encoded).hexdigest()


def sector_window_capture_from_prices(prices) -> SectorWindowCapture:
    """Project supplied captured bytes only; no selection, acquisition or clock.

    Reuse the incumbent semantic decoder over this snapshot's supplied member
    bytes, so mutable DataFrame state cannot detach the witness from its receipt.
    A later read time does not become vendor availability or historical evidence.
    """
    import pandas as pd
    from engine.leadership_rotation_context import US_SECTOR_COHORT_ID, _window_binding
    from lib.sector_input_capture import SectorPriceCaptures
    from lib.yahoo_generation_contract import VerifiedYahooGeneration, verify_yahoo_snapshot
    from lib.yahoo_runtime_profile import SECTOR_CLOSE_TICKERS, YahooRuntimeBindingError

    if not isinstance(prices, SectorPriceCaptures) or not isinstance(prices.yahoo, VerifiedYahooGeneration):
        raise SectorDocumentCompositionError("captured_yahoo_prices_required")
    try:
        verified = verify_yahoo_snapshot(prices.yahoo.snapshot, now=prices.captured_at,
                                         require_current=False)
        if (verified.cohort.generation_id != prices.yahoo.cohort.generation_id
                or verified.cohort.source_session != prices.yahoo.cohort.source_session):
            raise ValueError("different captured Yahoo identity")
        # Every individual index has already been admitted by the existing owner.
        # The outer union retains missing observations; it never fills a price.
        panel = pd.concat({ticker: verified.cohort.frames[ticker]["close"]
                           for ticker in SECTOR_CLOSE_TICKERS}, axis=1, sort=True)
        _, digest = _sector_window_rows(panel)
        supplied = {
            "source_roots": ["yahoo-sector-close-14"],
            "cohort_id": US_SECTOR_COHORT_ID,
            "benchmark": "SPY",
            "source_session": verified.cohort.source_session,
            "price_basis": "total_return",
            "clocks": {"publication": verified.snapshot.published_at,
                       "availability": None, "correction": None, "history": None},
            "receipt": verified.prior_identity(captured_at=prices.captured_at),
        }
        binding, diagnostics = _window_binding(supplied)
        if diagnostics["receipt_withheld"] or binding != supplied:
            raise ValueError("captured receipt could not be preserved")
        return SectorWindowCapture(binding, digest)
    except SectorDocumentCompositionError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError, YahooRuntimeBindingError) as exc:
        raise SectorDocumentCompositionError("invalid_sector_window_capture") from exc


def _sector_window_inputs(capture, *, panel, reference, benchmark, source_session):
    """Bind these exact observations and supplied canonical sessions to Central."""
    import re
    import pandas as pd
    from engine.leadership_rotation_context import US_SECTOR_COHORT_ID, _window_binding

    if not isinstance(capture, SectorWindowCapture):
        raise SectorDocumentCompositionError("invalid_sector_window_capture")
    if (not isinstance(capture.panel_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", capture.panel_sha256) is None):
        raise SectorDocumentCompositionError("invalid_sector_window_witness")
    try:
        binding, diagnostics = _window_binding(capture.source_binding)
    except (TypeError, ValueError, OverflowError) as exc:
        raise SectorDocumentCompositionError("invalid_sector_window_binding") from exc
    if (diagnostics["receipt_withheld"]
            or set(binding) != {"source_roots", "cohort_id", "benchmark", "source_session",
                                "price_basis", "clocks", "receipt"}
            or binding["source_roots"] != ["yahoo-sector-close-14"]
            or binding["cohort_id"] != US_SECTOR_COHORT_ID
            or binding["benchmark"] != benchmark or benchmark != "SPY"
            or binding["source_session"] != source_session
            or binding["price_basis"] != "total_return"
            or binding != capture.source_binding):
        raise SectorDocumentCompositionError("incompatible_sector_window_binding")
    rows, digest = _sector_window_rows(panel)
    if digest != capture.panel_sha256:
        raise SectorDocumentCompositionError("different_captured_sector_window_prices")
    if (not isinstance(reference, pd.DatetimeIndex) or len(reference) > 20000
            or reference.hasnans or reference.has_duplicates or reference.tz is not None
            or not reference.is_monotonic_increasing
            or not reference.equals(reference.normalize())):
        raise SectorDocumentCompositionError("invalid_sector_window_reference_sessions")
    return {
        "closes": rows, "benchmark": benchmark, "end_session": source_session,
        "source_session": source_session,
        "reference_sessions": [stamp.date().isoformat() for stamp in reference],
        "windows": [5, 20, 63], "source_binding": binding,
    }


@dataclass(frozen=True)
class SectorDatedContextInputs:
    """Captured owner documents for one explicitly configured theme example.

    This selector is not a theme-to-sector mapping. Capture attribution identifies
    bytes, not original historical availability or a qualified causal relationship.
    """
    theme_key: str
    regime_document: object
    config_document: object
    public_risk_document: object
    source_attribution: dict
    decision_cutoff: str | None = None


@dataclass(frozen=True)
class SectorDocumentContext:
    """Captured adjuncts for the existing five-member Sector calculation.

    The capture adapter owns byte provenance and input-generation admission. This
    context contains no precomputed Central, cycles, board or publication receipt.
    Core and basket-baseline sessions remain distinct explicit source facts.
    """
    core_source_session: str
    baseline_session: str
    market_context: dict
    membership_unavailable: bool
    rotation_artifact: dict
    rotation_events: dict | None
    fragmentation: dict | None
    fusion_calibrations: Mapping
    setup_latest: dict
    setup_closes: object
    setup_sectors: tuple[str, ...]
    context_history: Sequence[dict]
    bottoming_cycle_rows: list[dict] | None
    bottoming_ledger_session: str | None
    sector_names_zh: Mapping[str, str]
    factor_seasonality: dict | None
    flow: dict | None
    pulse_archive: list[dict]
    pulse_heat_calibration: dict
    grader_calls: object
    grader_frozen: object
    auxiliary_evidence: dict
    fusion_macro_beta_table: Mapping | None = None
    sector_window_capture: SectorWindowCapture | None = None
    dated_context_inputs: SectorDatedContextInputs | None = None
    classification_context: dict | None = None


@dataclass(frozen=True)
class SectorDocumentComposition:
    member_bytes: Mapping[str, bytes]
    deferred_effects: tuple
    evidence: dict


class SectorDocumentCompositionError(ValueError):
    """A required captured calculation is unavailable or incoherent."""


def compose_sector_documents(*, basket_inputs, theme_inputs, allocation_inputs,
                             cycle_inputs, timing_inputs, context: SectorDocumentContext,
                             evaluation_date: date, built_at: datetime) -> SectorDocumentComposition:
    """Compute exactly the incumbent five Sector members, with no publication effects.

    The trusted capture adapter supplies existing explicit input types. Prepared
    theme features and their enrichment must be bound to that adapter's verified
    thematic capture; narrative retains its separately owned price projection.
    The previous selected Central is only ThemeScoreInputs.prior_sector_text.
    No caller-supplied result substitutes for a calculation in this composition.
    Staging, byte admission, selection, auth and ledger advancement stay upstream.
    """
    from dataclasses import fields, replace
    import hashlib
    import pandas as pd
    from engine import basket_index, baskets, cycles, narrative_rotation, sector_action_board
    from engine import sector_central, sector_central_grader, sector_cycles, theme_scoring
    from engine.sector_generation_guard import parse_session, rotation_context_from_inputs
    from lib.sector_generation_contract import SECTOR_GENERATION_MEMBERS

    expected_types = (
        (basket_inputs, baskets.BasketInputs), (theme_inputs, theme_scoring.ThemeScoreInputs),
        (allocation_inputs, narrative_rotation.NarrativeAllocationInputs),
        (cycle_inputs, sector_cycles.SectorCyclesInputs),
        (timing_inputs, sector_action_board.SectorTimingInputs),
        (context, SectorDocumentContext),
    )
    if any(not isinstance(value, expected) for value, expected in expected_types):
        raise TypeError("Existing captured Sector input types are required")
    if (type(evaluation_date) is not date or not isinstance(built_at, datetime)
            or built_at.tzinfo is None or built_at.utcoffset() is None):
        raise SectorDocumentCompositionError("explicit_evaluation_and_aware_build_clocks_required")
    if context.fusion_macro_beta_table is not None and (
            not isinstance(context.fusion_macro_beta_table, Mapping) or context.fusion_calibrations):
        raise SectorDocumentCompositionError("ambiguous_or_invalid_fusion_source")
    if (context.dated_context_inputs is not None
            and not isinstance(context.dated_context_inputs, SectorDatedContextInputs)):
        raise SectorDocumentCompositionError("captured_dated_context_inputs_required")
    built = built_at.astimezone(timezone.utc)
    core_session = _session(context.core_source_session, "core_source_session")
    baseline = _session(context.baseline_session, "baseline_session")
    if (max(date.fromisoformat(core_session), date.fromisoformat(baseline)) > evaluation_date
            or built.date() < evaluation_date or baseline > core_session):
        raise SectorDocumentCompositionError("incompatible_source_or_evaluation_clocks")
    if (theme_inputs.region != "us" or allocation_inputs.region != "us"
            or theme_inputs.evaluation_date != evaluation_date
            or timing_inputs.source_session != core_session):
        raise SectorDocumentCompositionError("incompatible_owner_scope_or_clock")
    left, right = cycle_inputs.calculation_inputs, timing_inputs.calculation_inputs
    if (not isinstance(left, cycles.CycleCalculationInputs)
            or not isinstance(right, cycles.CycleCalculationInputs)):
        raise SectorDocumentCompositionError("captured_cycle_context_required")
    cycle_day = date.fromisoformat(left.evaluation_date)
    if not date.fromisoformat(core_session) <= cycle_day <= evaluation_date:
        raise SectorDocumentCompositionError("incompatible_cycle_evaluation_clock")
    for field in fields(left):
        a, b = getattr(left, field.name), getattr(right, field.name)
        same = (set(a) == set(b) and all(a[key].equals(b[key]) for key in a)
                if field.name == "reference_sessions" else a == b)
        if not same:
            raise SectorDocumentCompositionError("inconsistent_shared_cycle_context")

    # Qualify a present capture before deepcopy or panel bounding can hide an
    # unsupported value, duplicate label or unrelated/future observation.
    if context.sector_window_capture is not None:
        _sector_window_inputs(context.sector_window_capture,
            panel=cycle_inputs.closes_tr, reference=left.reference_sessions.get("US"),
            benchmark=cycle_inputs.benchmark, source_session=core_session)

    # One detached value set for this call. Acquisition must not mutate admitted
    # inputs concurrently; this copy is not another capture/provenance authority.
    basket_inputs, theme_inputs, allocation_inputs, cycle_inputs, timing_inputs, value = deepcopy(
        (basket_inputs, theme_inputs, allocation_inputs, cycle_inputs, timing_inputs, context))
    bounded_yahoo, bounded_price, observed, raw_tip = sector_cycles._bound_panels(
        cycle_inputs.closes_tr, cycle_inputs.closes_px, cycle_inputs.benchmark,
        sector_cycles._clock_date(cycle_inputs.asof))
    if observed is None or observed.date().isoformat() != core_session:
        raise SectorDocumentCompositionError("yahoo_effective_session_mismatch")
    cycle_inputs = replace(cycle_inputs, closes_tr=bounded_yahoo, closes_px=bounded_price)
    sector_window_inputs = (None if value.sector_window_capture is None else
        _sector_window_inputs(value.sector_window_capture,
            panel=cycle_inputs.closes_tr,
            reference=cycle_inputs.calculation_inputs.reference_sessions.get("US"),
            benchmark=cycle_inputs.benchmark, source_session=core_session))
    membership = (basket_inputs.membership or {}).get("baskets") or {}
    if dict(cycle_inputs.basket_specs) != membership:
        raise SectorDocumentCompositionError("different_captured_basket_membership")
    try:
        setup_closes = basket_index._capture_index_panel(value.setup_closes)
    except (TypeError, ValueError) as exc:
        raise SectorDocumentCompositionError("invalid_setup_price_capture") from exc
    reference = cycle_inputs.calculation_inputs.reference_sessions.get("US")
    if (reference is None or "SPY" not in setup_closes
            or not set(value.setup_sectors).issubset(setup_closes.columns)
            or not setup_closes.index.isin(reference).all()
            or (len(setup_closes) and setup_closes.index[-1].date().isoformat() > core_session)):
        raise SectorDocumentCompositionError("setup_prices_outside_admitted_core")
    def same_observations(series, reference_series):
        return series.astype("float64").dropna().equals(reference_series.astype("float64").dropna())
    for ticker in setup_closes.columns.intersection(bounded_yahoo.columns):
        if not same_observations(setup_closes[ticker], bounded_yahoo[ticker]):
            raise SectorDocumentCompositionError("different_captured_setup_prices")
    for ticker, frame in timing_inputs.etf_frames.items():
        if ticker not in bounded_yahoo or frame is None:
            continue
        if (not isinstance(frame, pd.DataFrame) or "close" not in frame
                or not same_observations(frame["close"], bounded_yahoo[ticker])):
            raise SectorDocumentCompositionError("different_captured_timing_prices")
    setup_day = parse_session(value.setup_latest.get("date"))
    if value.setup_latest.get("date") is not None and (setup_day is None or setup_day > evaluation_date):
        raise SectorDocumentCompositionError("invalid_setup_context_clock")
    frozen = value.grader_frozen
    if frozen is not None:
        if (not isinstance(frozen, pd.DataFrame) or not isinstance(frozen.index, pd.DatetimeIndex)
                or frozen.index.has_duplicates or frozen.index.hasnans
                or not frozen.index.equals(frozen.index.normalize())
                or not frozen.index.is_monotonic_increasing
                or frozen.index.tz is not None):
            raise SectorDocumentCompositionError("invalid_captured_frozen_history")
        if len(frozen) and frozen.index[-1].date().isoformat() > core_session:
            raise SectorDocumentCompositionError("frozen_price_history_after_core_session")
    basket_data = baskets.compute_baskets_from_inputs(basket_inputs)
    theme_result = theme_scoring.compute_theme_intel_core(theme_inputs)
    allocation = narrative_rotation.compute_narrative_rotation_core(allocation_inputs)
    cycle_data = sector_cycles.compute_from_inputs(cycle_inputs)
    for label, data in (("baskets", basket_data), ("theme_intel", theme_result.payload),
                        ("allocation", allocation), ("cycles", cycle_data)):
        if not isinstance(data, dict) or not data:
            raise SectorDocumentCompositionError(label + "_calculation_unavailable")
    if (cycle_data.get("meta") or {}).get("asOf") != core_session:
        raise SectorDocumentCompositionError("cycle_source_session_mismatch")
    cycle_data.update(rotation_context_from_inputs(
        consumer_session=core_session, rotation_events=value.rotation_events,
        fragmentation=value.fragmentation, today=evaluation_date))

    documents = assemble_sector_basket_documents(SectorBasketDocumentInputs(
        source_session=baseline, basket_payload=basket_data, theme_intel=theme_result.payload,
        allocation=allocation, context_history=value.context_history,
        rotation_events=value.rotation_events, bottoming_cycle_rows=value.bottoming_cycle_rows,
        bottoming_ledger_session=value.bottoming_ledger_session, sector_names_zh=value.sector_names_zh,
        factor_seasonality=value.factor_seasonality, flow=value.flow, pulse_archive=value.pulse_archive,
        pulse_heat_calibration=value.pulse_heat_calibration, built_at=built))
    timing = sector_action_board.sector_timing_and_notable_from_inputs(timing_inputs)
    setups = sector_action_board.sector_setup_from_inputs(
        latest=value.setup_latest, closes=setup_closes,
        sectors=value.setup_sectors, timing=timing.timing)
    if setups is None:
        raise SectorDocumentCompositionError("sector_setup_unavailable")
    action = sector_action_board.assemble_action_board_from_inputs(
        sector_timing=timing.timing, notable=timing.notable, baskets=documents.baskets,
        allocation=allocation, sector_setups=setups)

    def encode(document):
        try:
            return json.dumps(document, ensure_ascii=False, separators=(",", ":"),
                              allow_nan=False).encode("utf-8")
        except (TypeError, ValueError, OverflowError, RecursionError) as exc:
            raise SectorDocumentCompositionError("nonfinite_or_unserializable_document") from exc

    # Final basket bytes are serialized ONCE and then shared with the board hash,
    # Central secondary-source facts and the eventual existing publisher request.
    basket_raw = encode(documents.baskets)
    handoff_raw = encode(documents.si_handoff)
    board_document = sector_action_board.action_board_envelope(
        basket_raw=basket_raw, action_board=action, generated_utc=built.isoformat())
    board_raw = encode(board_document)

    calibrations = value.fusion_calibrations
    if value.fusion_macro_beta_table is not None:
        if not isinstance(value.fusion_macro_beta_table, Mapping) or calibrations:
            raise SectorDocumentCompositionError("ambiguous_or_invalid_fusion_source")
        # The captured adapter selects this path. Reuse the exact normalized risk
        # calibration that produced the cycle spine; never accept an unrelated map.
        calibrations = sector_central.fusion_calibrations_from_inputs(cycle_data,
            macro_beta_table=dict(value.fusion_macro_beta_table),
            risk_calibration=cycle_inputs.calculation_inputs.risk_calibration)

    try:
        central_data = sector_central.compute_from_inputs(sector_central.SectorCentralInputs(
            cycle_spine=cycle_data, market_context=value.market_context,
            closes=cycle_inputs.closes_tr, narrative_rotation=allocation,
            membership_document=basket_inputs.membership,
            membership_unavailable=value.membership_unavailable,
            rotation_artifact=value.rotation_artifact, rotation_events=value.rotation_events,
            fusion_calibrations=calibrations,
            sector_window_inputs=sector_window_inputs), evaluation_date=evaluation_date)
    except sector_central.SectorWindowProjectionError as exc:
        raise SectorDocumentCompositionError("sector_window_projection_refused") from exc
    if not isinstance(central_data, dict) or not central_data.get("sectors"):
        raise SectorDocumentCompositionError("central_calculation_unavailable")
    if central_data.get("as_of") != core_session:
        raise SectorDocumentCompositionError("central_source_session_mismatch")

    if value.dated_context_inputs is not None:
        from engine.sector_dated_context import project_dated_context
        dated = value.dated_context_inputs
        central_data["dated_context"] = project_dated_context(
            theme_key=dated.theme_key, regime_document=dated.regime_document,
            config_document=dated.config_document,
            public_risk_document=dated.public_risk_document,
            source_attribution=dated.source_attribution,
            decision_cutoff=dated.decision_cutoff)

    if value.classification_context is not None:
        from engine.sector_native_view import _classification_context
        central_data["captured_classification"] = _classification_context(value.classification_context)

    # Grading observes the same admitted Yahoo panel and one captured frozen store.
    # It does not append today's calls, freeze basket levels or use computed charts.
    frozen_levels = sector_central_grader.frozen_basket_levels_from_inputs(frozen)
    freeze_start = str(frozen.index[0].date()) if frozen is not None and len(frozen) else None
    central_data["grader"] = sector_central_grader.grade_from_inputs(
        value.grader_calls, yahoo_panel=cycle_inputs.closes_tr,
        basket_levels=frozen_levels, frozen_df=frozen, freeze_start=freeze_start)

    def byte_status(name, raw, observed_at):
        return {"status": "ok", "path": name, "sha256": hashlib.sha256(raw).hexdigest(),
                "as_of": observed_at, "error": None, "transport": "sector_generation_member"}
    secondary = {
        "flows_html": {"status": "not_applicable", "path": None, "sha256": None,
                       "as_of": None, "error": None},
        "si_handoff": byte_status(SECTOR_GENERATION_MEMBERS[3], handoff_raw,
                                  baseline),
        "action_board": byte_status(SECTOR_GENERATION_MEMBERS[4], board_raw, baseline),
        "baskets": byte_status(SECTOR_GENERATION_MEMBERS[2], basket_raw, baseline),
        "grader": {"status": "ok", "path": None, "sha256": None, "as_of": None,
                   "error": None, "mode": "captured_pre_append_calculation"},
    }
    central_data = sector_central.complete_document_from_inputs(
        central_data, built_at=built, secondary_sources=secondary,
        premium_publication={"path": "premiumdata/sector_central.json", "written": False,
                             "withheld_rows": 0},
        transport={"kind": "sector_generation", "legacy_html_published": False,
                   "publication_receipt_owner": "existing_generation_publisher"},
        research_mode="unbound_native")
    members = {
        SECTOR_GENERATION_MEMBERS[0]: encode(central_data),
        SECTOR_GENERATION_MEMBERS[1]: encode(cycle_data),
        SECTOR_GENERATION_MEMBERS[2]: basket_raw,
        SECTOR_GENERATION_MEMBERS[3]: handoff_raw,
        SECTOR_GENERATION_MEMBERS[4]: board_raw,
    }
    evidence = {
        "core_source_session": core_session, "baseline_session": baseline,
        "evaluation_date": evaluation_date.isoformat(), "cycle_evaluation_date": cycle_day.isoformat(),
        "cycle_asof": cycle_inputs.asof, "built_at": built.isoformat(),
        "yahoo_evaluation_panel_tip": raw_tip.date().isoformat() if raw_tip is not None else None,
        "basket_documents": documents.evidence, "timing": timing.input_evidence,
        "auxiliary": deepcopy(value.auxiliary_evidence),
        "member_sha256": {name: hashlib.sha256(raw).hexdigest() for name, raw in members.items()},
        "member_bytes": {name: len(raw) for name, raw in members.items()},
        "grader": {"calls_appended": False, "frozen_history_advanced": False,
                   "freeze_start": freeze_start, "price_source_session": core_session},
        "deferred_effect_count": len(theme_result.deferred_effects),
        "native_research_receiver": "unbound",
        "publication": "not_performed; existing generation factory must admit actual bytes",
    }
    return SectorDocumentComposition(members, deepcopy(theme_result.deferred_effects), evidence)
