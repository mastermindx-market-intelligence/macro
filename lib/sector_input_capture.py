"""Sector capture and assembly through the existing source and calculation owners.

Explicit readers bind private generations and bounded local observations. The
pure assembler maps those values and qualified holdings to all five document
owners. No provider refresh, holdings acquisition or publication occurs here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from lib.yahoo_generation_contract import (
    VerifiedYahooGeneration, _instant, read_verified_yahoo_cohort,
)
from lib.breadth_member_generation_contract import (
    VerifiedBreadthMemberGeneration, read_verified_breadth_member_inputs,
)


@dataclass(frozen=True)
class SectorPriceCaptures:
    yahoo: VerifiedYahooGeneration
    breadth: VerifiedBreadthMemberGeneration
    captured_at: datetime

    def input_lineage(self) -> dict:
        """Describe these captured bytes; never resolve a pointer a second time."""
        return {
            "yahoo": self.yahoo.prior_identity(captured_at=self.captured_at),
            "breadth_members": self.breadth.prior_identity(captured_at=self.captured_at),
        }


def read_sector_price_captures(*, generations_root: Path, now: datetime) -> SectorPriceCaptures:
    """Capture both current selections once and require their exact dependency.

    If Yahoo advanced before breadth, the existing breadth validator refuses the
    pair. It does not fall back to a retained dependency or reread either pointer.
    Existing direct readers retain their explicit historical-recovery semantics.
    """
    captured_at = _instant(now)
    yahoo = read_verified_yahoo_cohort(generations_root=generations_root,
        now=captured_at, require_current=True)
    breadth = read_verified_breadth_member_inputs(generations_root=generations_root,
        now=captured_at, yahoo=yahoo, require_current=True)
    return SectorPriceCaptures(yahoo, breadth, captured_at)


def read_sector_member_ohlcv_capture(*, prices: SectorPriceCaptures, generations_root: Path, now: datetime):
    """Bind genuine member candles to this price pair without resolving it again."""
    from lib.member_ohlcv_generation_contract import read_verified_member_ohlcv_inputs
    if not isinstance(prices, SectorPriceCaptures) or _instant(now) < _instant(prices.captured_at):
        raise ValueError("captured_sector_price_pair_required")
    return read_verified_member_ohlcv_inputs(generations_root=generations_root, now=_instant(now),
        breadth=prices.breadth, yahoo=prices.yahoo, require_current=True)


class SectorInputCaptureError(ValueError):
    """A required captured source is unavailable or incoherent; no fallback."""


@dataclass(frozen=True)
class PreviousSectorCapture:
    """One verified previous Central, or an explicitly admitted absence.

    The captured selection fence survives calculation unchanged. The caller must
    use it with the incumbent publisher rather than resolve latest a second time.
    """

    snapshot: object | None
    central_bytes: bytes | None
    captured_at: datetime
    absence_reason: str | None
    _central_document: dict | None

    @property
    def expected_current_content_id(self) -> str | None:
        return None if self.snapshot is None else self.snapshot.content_id

    @property
    def prior_sector_text(self) -> str | None:
        return None if self.central_bytes is None else self.central_bytes.decode("utf-8")

    def central_document(self) -> dict | None:
        from copy import deepcopy
        return deepcopy(self._central_document)

    def input_lineage(self) -> dict:
        import hashlib
        selected = self.snapshot
        return {
            "schema": "sector_previous_capture.v1",
            "outcome": "observed_absent" if selected is None else "selected",
            "captured_at": self.captured_at.isoformat(),
            "absence_reason": self.absence_reason,
            "domain": "sector",
            "generation_id": None if selected is None else selected.generation_id,
            "content_id": self.expected_current_content_id,
            "published_at": None if selected is None else selected.published_at,
            "member": "sectordata/sector_central.json",
            "byte_length": None if self.central_bytes is None else len(self.central_bytes),
            "sha256": None if self.central_bytes is None else hashlib.sha256(self.central_bytes).hexdigest(),
        }


def read_previous_sector_capture(*, generations_root: Path,
                                 allow_bootstrap: bool, clock) -> PreviousSectorCapture:
    """Capture the existing selected-generation facade once, then sample clock.

    Only that facade's typed positive absence permits an explicit bootstrap
    capture. An unprovisioned root, unreadable/corrupt selection, or bad Central
    aborts acquisition. This function never initializes storage or reads legacy
    Sector output. The injected clock is sampled after the observed read.
    """
    from lib.sector_generation_contract import (
        SECTOR_GENERATION_DOMAIN, _decode_member, SectorGenerationContractError,
    )
    from scripts import vps_live_orchestrator as publisher
    if type(allow_bootstrap) is not bool or not callable(clock):
        raise SectorInputCaptureError("explicit_bootstrap_and_clock_required")
    try:
        selected = publisher.read_selected_generation(
            generations_root=generations_root, domain=SECTOR_GENERATION_DOMAIN,
            members=("sectordata/sector_central.json",))
    except publisher.SelectedGenerationAbsent as error:
        if not allow_bootstrap:
            raise SectorInputCaptureError("previous_selection_absent_bootstrap_not_enabled") from None
        captured_at = _instant(clock())
        return PreviousSectorCapture(None, None, captured_at, error.reason, None)
    except publisher.SelectedGenerationUnavailable:
        raise SectorInputCaptureError("previous_selection_unavailable") from None
    captured_at = _instant(clock())
    try:
        published = datetime.fromisoformat(selected.published_at.replace("Z", "+00:00"))
        if _instant(published) > captured_at:
            raise SectorInputCaptureError("previous_publication_after_capture")
        raw = selected.members["sectordata/sector_central.json"]
        document = _decode_member(raw)
    except SectorInputCaptureError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError, SectorGenerationContractError):
        raise SectorInputCaptureError("previous_central_invalid") from None
    return PreviousSectorCapture(selected, raw, captured_at, None, document)


@dataclass(frozen=True)
class SectorAssembledInputs:
    """Existing composer arguments and publication facts from one supplied capture.

    This value performs no calculation publication, selection, acquisition or
    scheduling. The incumbent publisher owns the generation, release revision,
    publication clock and final admission. Contained values are detached for this
    call; callers must not mutate them concurrently with composition.
    """
    basket_inputs: object
    theme_inputs: object
    allocation_inputs: object
    cycle_inputs: object
    timing_inputs: object
    context: object
    evaluation_date: object
    built_at: datetime
    input_identity: dict
    expected_current_content_id: str | None

    def composition_arguments(self) -> dict:
        return {name: getattr(self, name) for name in (
            "basket_inputs", "theme_inputs", "allocation_inputs", "cycle_inputs",
            "timing_inputs", "context", "evaluation_date", "built_at")}


def _source_date(value, label):
    from datetime import date
    try:
        if type(value) is not str or date.fromisoformat(value).isoformat() != value:
            raise ValueError
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise SectorInputCaptureError(label + "_source_date_invalid") from None


def _qualified_owner_context(auxiliary, *, evaluation_date):
    """Resolve the decoder's two owner-shape requirements from captured values."""
    from copy import deepcopy
    import math
    import re
    from engine import market_state
    from lib.market_session import market_local_date

    def dated(key, field):
        document = auxiliary.document(key)
        evidence = auxiliary.observation(key)
        if (evidence.observation != "present" or evidence.decode_outcome != "present"
                or type(document) is not dict or not document):
            raise SectorInputCaptureError(key + "_owner_result_unavailable")
        day = _source_date(document.get(field), key)
        if day > min(evaluation_date, market_local_date("US", now=evidence.captured_at)):
            raise SectorInputCaptureError(key + "_owner_result_future")
        return document

    state = dated("market_state", "asof")
    verdict, score = state.get("verdict"), state.get("score")
    radar = state.get("radar")
    if (state.get("schema") != "market_state.v1" or state.get("market") != "us"
            or state.get("is_display_only") is not True
            or verdict not in market_state._LABEL
            or type(score) not in (int, float) or not math.isfinite(score)
            or not 0 <= score <= 100
            or market_state._verdict_from_score(score) != verdict
            or (state.get("label_en"), state.get("label_zh")) != market_state._LABEL[verdict]
            or state.get("color") != market_state._COLOR[verdict]
            or type(radar) is not dict
            or (radar.get("state") is not None and
                (type(radar["state"]) is not str or not 0 < len(radar["state"]) <= 128))):
        raise SectorInputCaptureError("market_state_owner_result_invalid")
    state_projection = {key: deepcopy(state[key]) for key in (
        "schema", "asof", "market", "is_display_only", "verdict", "score",
        "label_en", "label_zh", "color")}
    state_projection["radar"] = {"state": radar.get("state")}

    alpha = dated("alpha", "as_of")
    rows = alpha.get("per_ticker")
    if (type(rows) is not dict or not 0 < len(rows) <= 10000
            or type(alpha.get("n")) is not int or alpha["n"] != len(rows)):
        raise SectorInputCaptureError("alpha_owner_result_invalid")
    projected = {}
    for ticker, row in rows.items():
        if (type(ticker) is not str or re.fullmatch(r"[A-Z0-9][A-Z0-9.\-]{0,31}", ticker) is None
                or type(row) is not dict):
            raise SectorInputCaptureError("alpha_owner_row_invalid")
        value, rank, count, entry = (row.get(key) for key in
                                    ("alpha", "sector_rank", "sector_n", "entry"))
        if (value is not None and
                (type(value) not in (int, float) or not math.isfinite(value))):
            raise SectorInputCaptureError("alpha_owner_value_invalid")
        if any(value is not None and (type(value) is not int or not 1 <= value <= 10000)
               for value in (rank, count)):
            raise SectorInputCaptureError("alpha_owner_rank_invalid")
        if rank is not None and count is not None and rank > count:
            raise SectorInputCaptureError("alpha_owner_rank_invalid")
        if entry not in (None, "extended", "pullback", "intact", "laggard", "neutral"):
            raise SectorInputCaptureError("alpha_owner_entry_invalid")
        projected[ticker] = {key: deepcopy(row[key]) for key in
                            ("alpha", "sector_rank", "sector_n", "entry") if key in row}
    qualification = {
        "market_state": {"outcome": "qualified_captured_owner_result", "asof": state["asof"],
                         "schema": state["schema"], "market": "us", "is_display_only": True,
                         "freshness": deepcopy(state.get("freshness")),
                         "freshness_basis": "source_declared", "availability": None},
        "alpha": {"outcome": "qualified_captured_owner_result", "as_of": alpha["as_of"],
                  "n": alpha["n"], "windows": deepcopy(alpha.get("windows")),
                  "availability": None},
    }
    return state_projection, projected, qualification


def _resolved_holdings(*, funds, snapshots, evidence, built_at, evaluation_date):
    """Bind already-resolved collector values without parsing or fetching a workbook.

    The existing collector owns workbook parsing and top-20 selection. This seam
    consumes its detached snapshots and observation facts, including named failed
    funds. An unresolved result is not an empty observation or authorization to
    consume a protected worker result.
    """
    from collections.abc import Mapping
    from copy import deepcopy
    import math
    import re
    import pandas as pd
    from lib.market_session import market_local_date

    if (not isinstance(snapshots, Mapping) or not isinstance(evidence, Mapping)
            or set(snapshots) != set(funds) or set(evidence) != set(funds)):
        raise SectorInputCaptureError("holdings_capture_unresolved")
    captured, facts, present = {}, {}, 0
    for fund in funds:
        frame, fact = snapshots[fund], evidence[fund]
        if type(fact) is not dict or fact.get("outcome") not in {
                "present", "absent", "unreadable", "malformed"}:
            raise SectorInputCaptureError("holdings_observation_unresolved")
        stamp = fact.get("captured_at")
        try:
            stamp = _instant(datetime.fromisoformat(stamp.replace("Z", "+00:00")))
        except (AttributeError, TypeError, ValueError):
            raise SectorInputCaptureError("holdings_capture_clock_invalid") from None
        if stamp > built_at:
            raise SectorInputCaptureError("holdings_capture_after_build")
        if (type(fact.get("origin")) is not str or not 0 < len(fact["origin"]) <= 2048):
            raise SectorInputCaptureError("holdings_origin_unresolved")
        if fact["outcome"] != "present":
            if frame is not None or not isinstance(fact.get("reason"), str) or not fact["reason"]:
                raise SectorInputCaptureError("failed_holdings_observation_incoherent")
            captured[fund], facts[fund] = None, deepcopy(fact)
            continue
        day = _source_date(fact.get("document_date"), "holdings")
        if day > min(evaluation_date, market_local_date("US", now=stamp)):
            raise SectorInputCaptureError("holdings_document_future")
        if (type(fact.get("sha256")) is not str
                or re.fullmatch(r"[0-9a-f]{64}", fact["sha256"]) is None
                or type(fact.get("byte_length")) is not int or fact["byte_length"] <= 0):
            raise SectorInputCaptureError("holdings_workbook_identity_missing")
        if (not isinstance(frame, pd.DataFrame) or not 0 < len(frame) <= 20
                or frame.columns.has_duplicates or len(frame.columns) > 32
                or not {"ticker", "weight_pct"}.issubset(frame.columns)
                or not isinstance(frame.index, pd.DatetimeIndex)
                or frame.index.hasnans or frame.index.tz is not None
                or not frame.index.equals(frame.index.normalize())
                or any(stamp.date() != day for stamp in frame.index)):
            raise SectorInputCaptureError("holdings_snapshot_invalid")
        names = list(frame["ticker"])
        if (any(type(t) is not str or not 0 < len(t) <= 32 or t != t.strip() for t in names)
                or len(set(names)) != len(names)):
            raise SectorInputCaptureError("holdings_population_invalid")
        try:
            if any(isinstance(v, bool) or not math.isfinite(float(v)) or not 0 <= float(v) <= 100
                   for v in frame["weight_pct"]):
                raise ValueError
        except (TypeError, ValueError, OverflowError):
            raise SectorInputCaptureError("holdings_weight_invalid") from None
        captured[fund], facts[fund] = frame.copy(deep=True), deepcopy(fact)
        present += 1
    if not present:
        raise SectorInputCaptureError("holdings_capture_unavailable")
    return captured, facts


def assemble_sector_inputs(*, prices, member_ohlcv, member_captured_at,
                           auxiliary, previous, holdings, holdings_evidence,
                           amalgams, amalgam_input_lineage, reference_sessions,
                           evaluation_date, built_at, input_version,
                           source_qualification, live_hazard_parity,
                           classification_context=None):
    """Map supplied captures to all five incumbent document builders.

    All reads, admission decisions and observation clocks arrive as values.
    Missing required holdings/index/calendar inputs refuse before calculation.
    Resolved optional absences retain their actual per-source evidence and use
    the existing owners' degradation semantics. The caller supplies the existing
    input version and qualification floor; no identity or availability is invented.
    """
    from collections.abc import Mapping
    from copy import deepcopy
    from datetime import date
    import hashlib
    import json
    import re
    import pandas as pd
    from engine import basket_breadth_divergence, basket_score, conditions, cycle_phase_age
    from engine import cycles, group_flow, hazard_score, narrative_rotation, sector_action_board
    from engine import sector_basket_documents, sector_central, sector_cycles, sector_pulse
    from engine import theme_context, theme_scoring, us_act_now, vol_regime
    from lib.breadth_member_generation_contract import verify_breadth_snapshot
    from lib.member_ohlcv_generation_contract import (
        VerifiedMemberOHLCVGeneration, _snapshot_bytes, validate_member_ohlcv_bundle)
    from lib.sector_auxiliary_capture import SectorAuxiliaryCapture, SOURCE_KEYS
    from lib.sector_generation_contract import _decode_member, SECTOR_INPUT_SCHEMA
    from lib.yahoo_generation_contract import verify_yahoo_snapshot
    from lib.yahoo_runtime_profile import SECTOR_CLOSE_TICKERS

    if (type(evaluation_date) is not date or type(built_at) is not datetime):
        raise SectorInputCaptureError("explicit_evaluation_and_build_clocks_required")
    built = _instant(built_at)
    if built.date() < evaluation_date:
        raise SectorInputCaptureError("evaluation_after_build")
    if classification_context is not None:
        from engine.sector_native_view import _classification_context
        classification_context = _classification_context(classification_context)
        if _instant(datetime.fromisoformat(
                classification_context["capture"]["captured_at"].replace("Z", "+00:00"))) > built:
            raise SectorInputCaptureError("classification_capture_after_build")
    if (type(input_version) is not str
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", input_version) is None
            or source_qualification not in {"accepted", "degraded", "stale"}):
        raise SectorInputCaptureError("explicit_sector_identity_required")
    if (not isinstance(prices, SectorPriceCaptures)
            or not isinstance(member_ohlcv, VerifiedMemberOHLCVGeneration)
            or not isinstance(auxiliary, SectorAuxiliaryCapture)
            or not isinstance(previous, PreviousSectorCapture)):
        raise SectorInputCaptureError("resolved_sector_captures_required")
    member_at = _instant(member_captured_at)
    if (any(_instant(stamp) > built for stamp in
            (prices.captured_at, member_at, auxiliary.captured_at, previous.captured_at))
            or member_at < _instant(prices.captured_at)):
        raise SectorInputCaptureError("incompatible_capture_clocks")
    if (len(auxiliary.evidence) != len(SOURCE_KEYS)
            or {fact.key for fact in auxiliary.evidence} != SOURCE_KEYS
            or any(_instant(fact.captured_at) > _instant(auxiliary.captured_at)
                   for fact in auxiliary.evidence)):
        raise SectorInputCaptureError("incomplete_auxiliary_capture")
    unresolved = set(auxiliary.unresolved) - {
        "market_state_owner_qualification_required", "alpha_owner_qualification_required"}
    if unresolved:
        raise SectorInputCaptureError("unresolved_auxiliary_inputs:" + ",".join(sorted(unresolved)))

    # Reuse the semantic owners over supplied immutable member bytes. These calls
    # never resolve a selected pointer; mutable cached projections are not authority.
    yahoo = verify_yahoo_snapshot(prices.yahoo.snapshot, now=prices.captured_at, require_current=False)
    breadth = verify_breadth_snapshot(prices.breadth.snapshot, yahoo=yahoo,
                                     now=prices.captured_at, require_current=False)
    raw, manifest = _snapshot_bytes(member_ohlcv.snapshot)
    members = validate_member_ohlcv_bundle(member_bytes=raw,
        input_identity=manifest.get("input_identity"), breadth=breadth, yahoo=yahoo,
        published_at=member_ohlcv.snapshot.published_at, now=member_at,
        source_revision=manifest.get("source_revision"), computed_at=manifest.get("computed_at"),
        require_current=False)
    prices = SectorPriceCaptures(yahoo, breadth, _instant(prices.captured_at))
    if classification_context is not None:
        configured = _configured_classification_roster(auxiliary.document("config"))
        population_rows, present, unclassified = _classification_population_rows(breadth, configured)
        expected_members = [symbol for symbol in configured if symbol in present]
        if (classification_context["configured_roster"] != configured
                or classification_context["membership_roster"] != expected_members
                or classification_context["unclassified_rows_n"] != unclassified
                or datetime.fromisoformat(classification_context["capture"]["captured_at"]
                    .replace("Z", "+00:00")) < prices.captured_at):
            raise SectorInputCaptureError("classification_capture_parent_mismatch")
        association = classification_context["association"]
        if association is not None:
            if association["lookup_on"] != evaluation_date.isoformat():
                raise SectorInputCaptureError("classification_lookup_date_mismatch")
            for fact in association["source_attribution"]:
                if fact["kind"] != "constituents":
                    continue
                member = "groups/" + fact["population"] + "/constituents.json"
                if (fact["generation_id"] != breadth.snapshot.generation_id
                        or fact["raw_sha256"] != hashlib.sha256(breadth.snapshot.members[member]).hexdigest()
                        or datetime.fromisoformat(fact["captured_at"].replace("Z", "+00:00")) < prices.captured_at):
                    raise SectorInputCaptureError("classification_capture_parent_mismatch")
            for row in association["associations"]:
                symbol = row["subject"]["vendor_symbol"]
                actual_rows = {item["population"]: (item["native_symbol"], item["native_name"], item["native_sector"])
                               for item in row["source_observations"]}
                expected_rows = {group: (item["symbol"], item["name"], item["sector"])
                                 for group, values in population_rows.items()
                                 for item in values if item["symbol"] == symbol}
                if actual_rows != expected_rows:
                    raise SectorInputCaptureError("classification_capture_parent_mismatch")
    source = yahoo.cohort.source_session
    if (breadth.inputs.source_session != source or members.source_session != source
            or _source_date(source, "price") > evaluation_date):
        raise SectorInputCaptureError("different_captured_source_sessions")
    if not isinstance(reference_sessions, Mapping) or "US" not in reference_sessions:
        raise SectorInputCaptureError("canonical_reference_sessions_required")
    reference = reference_sessions["US"]
    if (not isinstance(reference, pd.DatetimeIndex) or not 0 < len(reference) <= 20000
            or reference.hasnans or reference.has_duplicates or reference.tz is not None
            or not reference.is_monotonic_increasing
            or not reference.equals(reference.normalize()) or pd.Timestamp(source) not in reference):
        raise SectorInputCaptureError("invalid_canonical_reference_sessions")
    tr = pd.concat({ticker: yahoo.cohort.frames[ticker]["close"]
                    for ticker in SECTOR_CLOSE_TICKERS}, axis=1, sort=True)
    px = pd.concat({ticker: yahoo.cohort.frames[ticker]["close_price"]
                    for ticker in SECTOR_CLOSE_TICKERS}, axis=1, sort=True)
    if not tr.index.isin(reference).all():
        raise SectorInputCaptureError("captured_prices_outside_reference")
    basket = breadth.inputs.basket_inputs()
    observation = deepcopy(breadth.inputs.primary_metadata["observation"])
    baseline = observation.get("effective_as_of")
    if baseline != source:
        raise SectorInputCaptureError("captured_breadth_baseline_mismatch")

    cfg = auxiliary.document("config")
    if type(cfg) is not dict or type(cfg.get("engine")) is not dict:
        raise SectorInputCaptureError("configuration_resolution_required")
    settings = cfg["engine"]
    funds = (cfg.get("sponsors") or {}).get("sector_funds")
    if (not isinstance(funds, (list, tuple)) or len(funds) != 11
            or set(funds) != set(SECTOR_CLOSE_TICKERS[:11]) or len(set(funds)) != len(funds)):
        raise SectorInputCaptureError("captured_sector_fund_scope_invalid")
    funds = tuple(funds)
    tops, holding_facts = _resolved_holdings(funds=funds, snapshots=holdings,
        evidence=holdings_evidence, built_at=built, evaluation_date=evaluation_date)
    if (not isinstance(amalgams, Mapping) or set(amalgams) != {"nasdaq", "russell"}
            or not isinstance(amalgam_input_lineage, Mapping)
            or set(amalgam_input_lineage) != set(amalgams)
            or any(type(amalgam_input_lineage[key]) is not dict or not amalgam_input_lineage[key]
                   for key in amalgams)):
        raise SectorInputCaptureError("captured_index_amalgam_inputs_required")
    resolved_amalgams = {}
    for family, value in amalgams.items():
        if not isinstance(value, sector_cycles.AmalgamSource):
            raise SectorInputCaptureError("invalid_captured_amalgam_values")
        if (not isinstance(value.specs, Mapping) or not isinstance(value.candles, Mapping)
                or len(value.specs) > 512 or not set(value.candles).issubset(value.specs)
                or any(c is not None and not isinstance(c, sector_cycles.MemberIndexCandle)
                       for c in value.candles.values())):
            raise SectorInputCaptureError("invalid_captured_amalgam_population")
        benchmark = sector_cycles._AMALGAM_FAMILIES[family]["benchmark"]
        close = value.bench_close
        if close is not None and (not isinstance(close, pd.Series)
                or not close.astype("float64").dropna().equals(tr[benchmark].astype("float64").dropna())):
            raise SectorInputCaptureError("different_captured_amalgam_benchmark")
        resolved_amalgams[family] = sector_cycles.AmalgamSource(
            specs=deepcopy(dict(value.specs)), candles=deepcopy(dict(value.candles)),
            bench_close=None if close is None else close.copy(deep=True))

    state, alpha, owner_facts = _qualified_owner_context(auxiliary, evaluation_date=evaluation_date)
    def document(key):
        value = auxiliary.document(key)
        return {} if value is None else value
    calibration = document("baskets_calibration")
    gate = vol_regime.overlay_gate_from_document(auxiliary.document("overlay_gate"))
    calculation = cycles.CycleCalculationInputs(evaluation_date=evaluation_date.isoformat(),
        fitted_bands=document("cycle_bands"),
        risk_calibration=cycles.risk_calibration_from_document(auxiliary.document("risk_calibration")),
        macro_overlay=deepcopy(settings.get("macro_overlay") or {}),
        vol_regime_overlay=deepcopy(settings.get("vol_regime_overlay") or {}),
        vol_overlay_gate=gate,
        entry_gate=cycles.effective_entry_settings_from_inputs(settings.get("entry_gate")),
        reference_sessions={key: value.copy(deep=True) for key, value in reference_sessions.items()})

    shared = group_flow._build_setup({"region": "us", "mem": basket.membership,
        "closes": breadth.inputs.broad_panel.copy(deep=True),
        "bench_close": breadth.inputs.spy["close"].copy(deep=True),
        "theme_closes": breadth.inputs.resolved_panel.copy(deep=True),
        "theme_price_resolution": deepcopy(dict(breadth.inputs.resolution)), "observation": observation})
    if shared is None or len(shared["idx"]) < 60:
        raise SectorInputCaptureError("captured_theme_panel_unavailable")
    panel = {"closes": shared["theme_closes"], "rets": shared["theme_rets"],
        "idx": shared["idx"], "bench": shared["bench"], "mem": shared["mem"],
        "observation": shared["observation"], "price_resolution": shared["theme_price_resolution"]}
    flow_cfg = group_flow._cfg(deepcopy(settings.get("group_flow") or {}))
    names = deepcopy(basket.names_sectors)
    rows = theme_scoring.prepare_theme_basket_rows(panel, region="us",
        group_flow_cfg=flow_cfg, names_sectors=names)
    member_frames = members.frames()
    enrichments = theme_scoring.basket_enrichments_from_inputs(rows, region="us",
        member_frames=member_frames, reference_close=panel["closes"], source_session=source,
        calculation_inputs=calculation,
        rollover_weights=basket_score.rollover_weights_from_document(calibration),
        breadth_divergence_fit=basket_breadth_divergence.calibration_from_document(calibration))
    regime = document("regime_latest")
    snapshot = vol_regime.published_snapshot_from_documents(
        site_document=auxiliary.document("vol_regime"), regime_document=regime)

    if previous.snapshot is None:
        if (previous.central_bytes is not None or previous._central_document is not None
                or type(previous.absence_reason) is not str or not previous.absence_reason):
            raise SectorInputCaptureError("previous_absence_unqualified")
        prior_text = None
    else:
        if (previous.absence_reason is not None or type(previous.central_bytes) is not bytes
                or previous.snapshot.members.get("sectordata/sector_central.json") != previous.central_bytes
                or _instant(previous.snapshot.published_at) > _instant(previous.captured_at)):
            raise SectorInputCaptureError("previous_selection_incoherent")
        _decode_member(previous.central_bytes)
        prior_text = previous.central_bytes.decode("utf-8")

    # Static labels are the incumbent region's values; loader callbacks are not
    # carried into either calculation bundle.
    region = narrative_rotation._region_cfg("us")
    region_meta = {key: region[key] for key in ("id", "market_en", "market_zh",
        "bench_label", "bench_label_zh", "phase0_file", "phase0_fallback")}
    theme = theme_scoring.ThemeScoreInputs(region="us", panel=panel, basket_rows=rows,
        group_flow_cfg=flow_cfg, names_sectors=names,
        macro_context=theme_scoring.macro_context_from_inputs(regime=regime,
            bonds=document("bonds_latest"), forex=document("forex_latest"), region="us"),
        signal_calibration=theme_scoring.signal_calibration_from_document(calibration),
        regime_snapshot=snapshot,
        regime_sizing=vol_regime.sizing_overlay(snapshot,
            vol_regime.overlay_config_from_inputs(settings.get("vol_regime_overlay")), overlay_gate=gate),
        regime_caution_scored=vol_regime.regime_caution_scored(gate=gate),
        prior_sector_text=prior_text, evaluation_date=evaluation_date,
        earnings_calendar=theme_scoring.earnings_calendar_from_inputs(auxiliary.table("earnings"),
            panel_session=_source_date(source, "price")),
        market_concentration=basket_score.market_concentration_from_inputs(auxiliary.table("breadth_tape")),
        basket_enrichments=enrichments, bench_label=region_meta["bench_label"],
        bench_label_zh=region_meta["bench_label_zh"])
    narrative_panel = narrative_rotation._build_setup({"cfg": {},
        "mem": deepcopy(basket.membership), "closes": breadth.inputs.broad_panel.copy(deep=True),
        "bench_close": breadth.inputs.spy["close"].copy(deep=True)})
    allocation = narrative_rotation.NarrativeAllocationInputs(region="us",
        panel={key: value for key, value in narrative_panel.items() if key != "cfg"},
        region_meta=region_meta, radar=auxiliary.document("radar"),
        short_interest=auxiliary.table("short_interest"),
        sizing_calibration=narrative_rotation.sizing_calibration_from_document(calibration),
        phase0_meta=document("rotation_phase0"), phase0_fallback_meta=None)

    candle_facts, candles = {}, {}
    specs = deepcopy(basket.membership["baskets"])
    for key, spec in specs.items():
        population = spec.get("members") or []
        if len(population) < 3:
            candles[key], candle_facts[key] = None, {"reason": "fewer_than_three_members"}
        else:
            candles[key], candle_facts[key] = sector_cycles.member_candle_from_captured_inputs(
                population, captured=breadth.inputs)
    phase_frame = auxiliary.table("cycle_forward_log")
    phase_history, phase_status = cycle_phase_age.phase_history_from_inputs(phase_frame,
        observation=auxiliary.observation("cycle_forward_log").decode_outcome)
    model, km = auxiliary.document("hazard_model"), auxiliary.document("hazard_km")
    hazard = (hazard_score.HazardCalibration(model=model, km=km)
              if isinstance(model, dict) and isinstance(km, dict) else None)
    cycle = sector_cycles.SectorCyclesInputs(closes_tr=tr, closes_px=px, benchmark="SPY",
        basket_specs=specs, basket_candles=candles, amalgams=resolved_amalgams,
        phase_history=phase_history, phase_history_status=phase_status, asof=source,
        hazard_calibration=hazard, calculation_inputs=calculation,
        live_hazard_parity=deepcopy(live_hazard_parity))
    beta_table = deepcopy((settings.get("confluence") or {}).get("sector_macro_beta") or {})
    factors = sector_action_board.factor_context_from_document(auxiliary.document("factors"))
    lineage = {
        "prices": prices.input_lineage(),
        "member_ohlcv": {"generation_id": member_ohlcv.snapshot.generation_id,
            "content_id": member_ohlcv.snapshot.content_id, "published_at": member_ohlcv.snapshot.published_at,
            "captured_at": member_at.isoformat(), "source_session": source,
            "source_revision": manifest["source_revision"],
            "members": {name: {"sha256": hashlib.sha256(value).hexdigest(), "bytes": len(value)}
                        for name, value in raw.items()}},
        "auxiliary": auxiliary.input_lineage(), "owner_qualifications": owner_facts,
        "holdings": holding_facts, "amalgams": deepcopy(dict(amalgam_input_lineage)),
        "basket_candles": candle_facts, "previous": previous.input_lineage(),
        "holding_price_coverage": {"source": "sector_member_ohlcv",
            "captured_members": sorted(member_frames),
            "missing": sorted({str(ticker).replace(".", "-") for frame in tops.values()
                              if frame is not None for ticker in frame["ticker"]}
                             - set(member_frames))},
    }
    # Persist only finite ordinary metadata; raw member/workbook bytes stay with
    # their capture owners. This is evidence, not a new publication receipt.
    try:
        encoded_lineage = json.dumps(lineage, allow_nan=False, ensure_ascii=False)
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise SectorInputCaptureError("invalid_capture_lineage") from exc
    if len(encoded_lineage.encode("utf-8")) > 2 * 1024 * 1024:
        raise SectorInputCaptureError("capture_lineage_bound")
    lineage = json.loads(encoded_lineage)
    timing = sector_action_board.SectorTimingInputs(source_session=source, funds=funds,
        etf_frames={fund: yahoo.cohort.frames[fund].copy(deep=True) for fund in funds},
        top_holdings=tops, stock_frames=member_frames,
        liquidity=sector_action_board.liquidity_from_document(regime),
        macro_drag=sector_action_board.macro_drag_from_document(regime),
        macro_beta={fund: conditions.sector_macro_beta_from_inputs(fund, table=beta_table) for fund in funds},
        alpha_per_ticker=alpha, insider_map=document("insider_signals"),
        factor_z=factors["factor_z"], sue_z=factors["sue_z"],
        calculation_inputs=calculation, auxiliary_evidence=deepcopy(lineage))
    history = auxiliary.document("theme_context_history")
    if history is None or history == []:
        history = theme_context.seed_history_from_inputs(auxiliary.table("theme_seed_archive"))
    if type(history) is not list:
        raise SectorInputCaptureError("invalid_captured_context_history")
    previous_history_day = None
    baseline_day = _source_date(baseline, "context_history_baseline")
    for row in history:
        if type(row) is not dict:
            raise SectorInputCaptureError("invalid_captured_context_history")
        history_day = _source_date(row.get("asof"), "context_history")
        if (history_day > baseline_day or
                (previous_history_day is not None and history_day < previous_history_day)):
            raise SectorInputCaptureError("invalid_captured_context_history_order_or_baseline")
        previous_history_day = history_day
    bottoming = us_act_now.cycle_rows_from_inputs(phase_frame)
    ledger_session = None
    if bottoming:
        try:
            ledger_session = pd.Timestamp(bottoming[0]["date"]).date().isoformat()
        except (KeyError, TypeError, ValueError):
            raise SectorInputCaptureError("invalid_bottoming_ledger_date") from None
    # This is a configured-theme example, not an inferred ETF/sector identity.
    # The projector preserves separate owner clocks and withholds historical
    # claims. Logical labels are public; private acquisition paths stay in lineage.
    dated_sources = {
        "regime_document": ("regime_latest", "D/regime/latest.json"),
        "config_document": ("config", "R/config.yml"),
        "public_risk_document": ("public_risk_envelope", "S/riskdata/risk_envelope.json"),
    }
    dated_context = sector_basket_documents.SectorDatedContextInputs(
        theme_key="memory_storage",
        regime_document=auxiliary.document("regime_latest"),
        config_document=auxiliary.document("config"),
        public_risk_document=auxiliary.document("public_risk_envelope"),
        source_attribution={name: {"source_ref": label,
            "raw_sha256": auxiliary.observation(key).sha256}
            for name, (key, label) in dated_sources.items()})
    context = sector_basket_documents.SectorDocumentContext(
        core_source_session=source, baseline_session=baseline,
        market_context=sector_central.market_context_from_inputs(latest=regime,
            macro_overlay=deepcopy(settings.get("macro_overlay") or {}), market_state=state,
            heatmap=auxiliary.document("heatmap"), closes=breadth.inputs.broad_panel.copy(deep=True),
            short_interest=auxiliary.table("short_interest"), benchmark=breadth.inputs.spy["close"]),
        membership_unavailable=False, rotation_artifact=document("rotation_artifact"),
        rotation_events=auxiliary.document("rotation_events"),
        fragmentation=auxiliary.document("sector_fragmentation"),
        fusion_calibrations={}, setup_latest=deepcopy(regime), setup_closes=tr.copy(deep=True),
        setup_sectors=funds, context_history=deepcopy(history), bottoming_cycle_rows=bottoming,
        bottoming_ledger_session=ledger_session,
        sector_names_zh={key: value["name_zh"] for key, value in sector_cycles.SECTORS.items()},
        factor_seasonality=sector_basket_documents.factor_season_from_inputs(auxiliary.document("factor_seasonality")),
        flow=auxiliary.document("flow"),
        pulse_archive=sector_pulse.archive_snapshots_from_inputs(auxiliary.table("basket_archive")),
        pulse_heat_calibration=sector_pulse.heat_calibration_from_document(auxiliary.document("pulse_heat")),
        grader_calls=auxiliary.table("central_calls"), grader_frozen=auxiliary.table("basket_frozen"),
        auxiliary_evidence=deepcopy(lineage), fusion_macro_beta_table=beta_table,
        sector_window_capture=sector_basket_documents.sector_window_capture_from_prices(prices),
        dated_context_inputs=dated_context,
        classification_context=deepcopy(classification_context))
    identity = {"sector_view": {"schema": SECTOR_INPUT_SCHEMA, "source_session": source,
        "baseline_session": baseline, "input_version": input_version,
        "source_qualification": source_qualification}, "sector_capture": deepcopy(lineage)}
    return SectorAssembledInputs(basket, theme, allocation, cycle, timing, context,
        evaluation_date, built, identity, previous.expected_current_content_id)



@dataclass(frozen=True)
class SectorLocalCaptures:
    """Observed local auxiliary/index inputs and the canonical US calendar.

    These are individual file observations, not an atomic multi-file generation.
    Holdings and native generation acquisition remain their existing owners' work.
    """
    auxiliary: object
    amalgams: dict
    amalgam_input_lineage: dict
    reference_sessions: dict
    captured_at: datetime
    classification_context: dict | None = None

    def assembly_arguments(self) -> dict:
        return {name: getattr(self, name) for name in (
            "auxiliary", "amalgams", "amalgam_input_lineage", "reference_sessions",
            "classification_context")}


def _configured_classification_roster(config_document):
    """The bounded, exact configured example; never infer vendor namespaces."""
    themes = config_document.get("themes") if type(config_document) is dict else None
    theme = themes.get("memory_storage") if type(themes) is dict else None
    roster = theme.get("tickers") if type(theme) is dict else None
    valid = (type(roster) in (list, tuple) and 0 < len(roster) <= 5
             and all(type(t) is str and 0 < len(t) <= 16 and t == t.strip()
                     and not any(ord(c) < 32 for c in t) for t in roster)
             and len(set(roster)) == len(roster))
    return list(roster) if valid else []


def _classification_population_rows(breadth, roster):
    """Exact captured labels, with incomplete classification rows counted."""
    populations, present, unclassified = {}, set(), 0
    for group in ("breadth", "smallcap_breadth", "midcap_breadth"):
        frame = breadth.inputs.constituents[group]
        selected = frame[frame["symbol"].isin(roster)].to_dict("records")
        present.update(row["symbol"] for row in selected)
        populations[group] = []
        for row in selected:
            if (type(row["name"]) is str and 0 < len(row["name"]) <= 512
                    and row["name"] == row["name"].strip()
                    and type(row["sector"]) is str and 0 < len(row["sector"]) <= 128
                    and row["sector"] == row["sector"].strip()
                    and not any(ord(c) < 32 for c in row["name"] + row["sector"])):
                populations[group].append(row)
            else:
                unclassified += 1
    return populations, present, unclassified


def read_sector_classification_context(*, repository_root, config_document,
                                       breadth, lookup_on, clock):
    """Optional descriptive association through the incumbent LEGACY reader.

    This fixed producer path has no mode discovery or native-refusal fallback.
    Only exact configured labels present in already captured native populations
    become membership subjects. Complete reference bytes are acquired with
    tighter owner-enforced bounds, projected here, then released before the
    large auxiliary decode/build. No new deadline, source or publication owner.
    """
    import hashlib
    import json
    from datetime import date
    from engine.entry_radar.replay.identity_observation_snapshot import (
        ReferenceReadBounds, read_reference_generation)
    from engine.neuralweb.sector_map import project_captured_sector_associations
    from lib.dataos.identity import IdentityError, VendorAliasTable
    from lib.breadth_member_generation_contract import VerifiedBreadthMemberGeneration

    if (not isinstance(breadth, VerifiedBreadthMemberGeneration)
            or type(lookup_on) is not date or not callable(clock)
            or not isinstance(repository_root, Path) or not repository_root.is_absolute()):
        raise SectorInputCaptureError("explicit_classification_capture_required")
    stamp = _instant(clock())
    if lookup_on > stamp.date():
        raise SectorInputCaptureError("classification_lookup_after_capture")
    roster = _configured_classification_roster(config_document)
    out = {"schema": "sector_classification_context/v1", "status": "unavailable",
        "theme_key": "memory_storage", "configured_roster": roster,
        "membership_roster": [], "missing_roster": list(roster),
        "unclassified_rows_n": 0,
        "capture": {"mode": "LEGACY", "status": "not_attempted",
            "reason": "configured_roster_unavailable", "captured_at": stamp.isoformat(),
            "producer_receipt_sha256": None, "artifact_sha256": None},
        "association": None}
    if not roster:
        return out
    sources = []
    population_rows, present, out["unclassified_rows_n"] = _classification_population_rows(breadth, roster)
    for group, rows in population_rows.items():
        member = "groups/" + group + "/constituents.json"
        # These are the already captured immutable normalized JSON bytes.
        # Their observation clock is this observation of the held value, not
        # the earlier acquisition time of the upstream Parquet artifact.
        captured = stamp
        sources.append({"population": group, "vendor": "membership", "rows": rows,
            "source_ref": "breadth_member_generation/" + member,
            "generation_id": breadth.snapshot.generation_id,
            "raw_sha256": hashlib.sha256(breadth.snapshot.members[member]).hexdigest(),
            "captured_at": captured})
    out["membership_roster"] = [t for t in roster if t in present]
    out["missing_roster"] = [t for t in roster if t not in present]
    if out["unclassified_rows_n"]:
        # A missing name must not erase a conflicting sector label. Withhold
        # this whole optional addendum rather than let its filtered rows create
        # a positive association. Never fabricate a name to satisfy the helper.
        out["capture"]["reason"] = "captured_classification_rows_incomplete"
        return out
    if not out["membership_roster"]:
        out["capture"]["reason"] = "no_captured_membership_label"
        return out
    bounds = ReferenceReadBounds(artifact_bytes=4 * 1024**2, receipt_bytes=1024**2,
        total_bytes=16 * 1024**2, rows=16_384, columns=64,
        decoded_bytes=8 * 1024**2, string_bytes=4096, record_bytes=65_536)
    try:
        # Matches scripts.build_security_master.DEFAULT_OUT. Do not substitute
        # a private company-context root or infer an HTTP-configurable mode.
        reference = read_reference_generation(repository_root / "data" / "reference", bounds=bounds)
        aliases = VendorAliasTable.from_records(reference.records("vendor_aliases.parquet"))
        master = reference.records("security_master.parquet")
        completed = _instant(clock())
        if completed < stamp:
            raise SectorInputCaptureError("classification_capture_clock_regressed")
        hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in reference.artifact_bytes}
        identity = {kind: {"source_ref": "R/data/reference/" + name,
            "raw_sha256": hashes[name], "captured_at": completed}
            for kind, name in (("vendor_aliases", "vendor_aliases.parquet"),
                               ("issuer_master", "security_master.parquet"))}
        association = project_captured_sector_associations(
            subjects=[{"vendor": "membership", "vendor_symbol": t}
                      for t in out["membership_roster"]],
            constituent_sources=sources, alias_table=aliases, issuer_records=master,
            identity_source=identity, lookup_on=lookup_on, observed_at=completed)
        out["capture"] = {"mode": "LEGACY", "status": "captured", "reason": None,
            "captured_at": completed.isoformat(),
            "producer_receipt_sha256": hashlib.sha256(reference.receipt_bytes).hexdigest(),
            "artifact_sha256": hashes}
        out["association"] = association
        out["status"] = association["status"]
        if out["status"] == "available" and (out["missing_roster"] or out["unclassified_rows_n"]):
            out["status"] = "partial"
        if len(json.dumps(out, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()) > 32 * 1024:
            raise IdentityError("classification context result byte bound")
    except (IdentityError, ValueError) as exc:
        if isinstance(exc, SectorInputCaptureError):
            raise
        # Preserve measurements on a known optional input refusal. No second
        # reader, synthetic identity inputs, previous positive or raw error leaks.
        detail = str(exc)
        reason = ("native_reference_requires_native_reader" if "native" in detail
                  else "reference_resource_bound" if "bound" in detail
                  else "reference_writer_busy" if "writer busy" in detail
                  else "reference_capture_unavailable")
        completed = _instant(clock())
        if completed < stamp:
            raise SectorInputCaptureError("classification_capture_clock_regressed")
        out.update(status="unavailable", association=None)
        out["capture"] = {"mode": "LEGACY", "status": "unavailable", "reason": reason,
            "captured_at": completed.isoformat(), "producer_receipt_sha256": None,
            "artifact_sha256": None}
    return out


def _observe_sector_source(path: Path, *, limit: int, clock):
    """Observe one declared path through retained, non-symlink descriptors."""
    import errno
    import hashlib
    import os
    from lib.sector_auxiliary_capture import CapturedAuxiliarySource
    from scripts.vps_live_orchestrator import _read_source_bytes, SourceReadRejected

    if (not isinstance(path, Path) or not path.is_absolute()
            or ".." in path.parts or len(path.parts) < 2):
        raise SectorInputCaptureError("absolute_capture_source_required")
    if not getattr(os, "O_NOFOLLOW", 0) or not getattr(os, "O_DIRECTORY", 0):
        raise SectorInputCaptureError("safe_capture_directory_open_unsupported")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0)
    descriptor = None
    raw = None
    outcome, reason = "present", "observed"
    try:
        descriptor = os.open(path.anchor, flags)
        for component in path.parts[1:-1]:
            following = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = following
        raw = _read_source_bytes(Path(path.name), limit=limit,
            directory_fd=descriptor, require_stable=True)
    except SourceReadRejected as exc:
        if exc.reason not in {"not_found", "read_denied", "io_error", "unstable_read"}:
            raise SectorInputCaptureError("unsafe_capture_source:" + exc.reason) from exc
        outcome = "absent" if exc.reason == "not_found" else "unreadable"
        reason = exc.reason
    except OSError as exc:
        if exc.errno == errno.ENOENT:
            outcome, reason = "absent", "not_found"
        elif exc.errno in {errno.EACCES, errno.EPERM}:
            outcome, reason = "unreadable", "read_denied"
        elif exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise SectorInputCaptureError("unsafe_capture_directory") from exc
        else:
            outcome, reason = "unreadable", "io_error"
    finally:
        if descriptor is not None:
            os.close(descriptor)
    captured_at = _instant(clock())
    return CapturedAuxiliarySource(str(path), None, captured_at, outcome, reason, raw,
        None if raw is None else len(raw), None if raw is None else hashlib.sha256(raw).hexdigest())


def read_sector_local_captures(*, repository_root: Path, theme_root: Path,
                               prices: SectorPriceCaptures, evaluation_date, clock):
    """Read real local prerequisites once; never refresh providers or holdings.

    Configured data/site roots come from the captured config bytes. ThemeContext's
    root is independent. Repeated declarations of the same absolute path reuse
    one observation with the strictest applicable encoded bound. The actual
    source revision of mutable files is unknown; their byte hashes are retained.
    """
    from copy import deepcopy
    from datetime import date
    from lib import sector_auxiliary_capture as aux
    from lib.breadth_member_generation_contract import verify_breadth_snapshot
    from lib.yahoo_generation_contract import verify_yahoo_snapshot
    from engine import sector_cycles, session_anchor

    if (not callable(clock) or type(evaluation_date) is not date
            or not isinstance(prices, SectorPriceCaptures)):
        raise SectorInputCaptureError("explicit_local_capture_inputs_required")

    def root(value):
        if not isinstance(value, (str, Path)):
            raise SectorInputCaptureError("absolute_capture_root_required")
        value = Path(value)
        if (not value.is_absolute() or ".." in value.parts
                or any(ord(char) < 32 or ord(char) == 127 for char in str(value))):
            raise SectorInputCaptureError("absolute_capture_root_required")
        return value

    roots = {"R": root(repository_root), "T": root(theme_root)}
    last_clock = _instant(prices.captured_at)

    def observed_clock():
        nonlocal last_clock
        value = _instant(clock())
        if value < last_clock or evaluation_date > value.date():
            raise SectorInputCaptureError("nonmonotonic_or_future_capture_clock")
        last_clock = value
        return value

    observed_clock()
    # Reconstruct projections from captured generation bytes, never mutable caches.
    yahoo = verify_yahoo_snapshot(prices.yahoo.snapshot, now=prices.captured_at,
                                  require_current=False)
    breadth = verify_breadth_snapshot(prices.breadth.snapshot, yahoo=yahoo,
                                     now=prices.captured_at, require_current=False)
    limits = {"yaml": aux.MIB, "json": 8 * aux.MIB,
              "jsonl": 16 * aux.MIB, "parquet": aux.MAX_PARQUET_BYTES}
    cache = {}
    total = 0

    def observe(path, limit):
        nonlocal total
        if path in cache:
            item = cache[path]
            if item.raw_bytes is not None and len(item.raw_bytes) > limit:
                raise SectorInputCaptureError("local_capture_encoded_bound")
            return item
        item = _observe_sector_source(path, limit=limit, clock=observed_clock)
        total += len(item.raw_bytes) if item.raw_bytes is not None else 0
        if total > aux.MAX_CAPTURE_BYTES:
            raise SectorInputCaptureError("local_capture_aggregate_bound")
        cache[path] = item
        return item

    config_path = roots["R"] / "config.yml"
    configuration = observe(config_path, limits["yaml"])
    if configuration.outcome != "present":
        raise SectorInputCaptureError("configuration_root_source_" + configuration.outcome)
    try:
        cfg, _ = aux._yaml(configuration.raw_bytes)
    except aux._Malformed as exc:
        raise SectorInputCaptureError("configuration_root_source_malformed") from exc
    storage = cfg.get("storage") if type(cfg) is dict else None
    if type(storage) is not dict:
        raise SectorInputCaptureError("captured_storage_roots_required")
    for label, key in (("D", "data_dir"), ("S", "site_dir")):
        setting = storage.get(key)
        if type(setting) is not str or not setting or len(setting.encode("utf-8")) > 2048:
            raise SectorInputCaptureError("captured_storage_roots_required")
        roots[label] = root(roots["R"] / setting)

    classification = read_sector_classification_context(repository_root=roots["R"],
        config_document=cfg, breadth=breadth, lookup_on=evaluation_date, clock=observed_clock)

    declarations = {}
    path_limits = {}
    for key, (kind, label) in aux.SOURCE_SPECS.items():
        prefix, relative = label.split("/", 1)
        path = roots[prefix] / relative
        declarations[key] = path
        path_limits[path] = min(path_limits.get(path, limits[kind]), limits[kind])
    index_paths = {family: roots["D"] / ("baskets_" + family) / "membership.json"
                   for family in sector_cycles._AMALGAM_FAMILIES}
    for path in index_paths.values():
        path_limits[path] = min(path_limits.get(path, limits["json"]), limits["json"])
    sources = {key: observe(path, path_limits[path]) for key, path in declarations.items()}
    index_sources = {family: observe(path, path_limits[path]) for family, path in index_paths.items()}
    completed = observed_clock()
    auxiliary = aux.decode_sector_auxiliary_capture(sources, captured_at=completed)
    bound_index_bytes = None
    if "index_membership" in breadth.inputs.receipt:
        from lib.sector_index_membership_capture import decode_index_membership
        _, bound_index_bytes = decode_index_membership(
            breadth.inputs.receipt["index_membership"], before=prices.captured_at)
    amalgams, lineage = {}, {}
    for family, observation in index_sources.items():
        if observation.outcome != "present":
            raise SectorInputCaptureError(f"index_membership_{family}_" + observation.outcome)
        if bound_index_bytes is not None and observation.raw_bytes != bound_index_bytes[family]:
            raise SectorInputCaptureError(f"index_membership_{family}_generation_mismatch")
        try:
            document, _ = aux._json(observation.raw_bytes)
        except aux._Malformed as exc:
            raise SectorInputCaptureError(f"index_membership_{family}_malformed") from exc
        specs = document.get("amalgamations") if type(document) is dict else None
        if (type(specs) is not dict or len(specs) > 512
                or any(type(key) is not str or not 0 < len(key) <= 128
                       or type(spec) is not dict or type(spec.get("members")) is not list
                       for key, spec in specs.items())):
            raise SectorInputCaptureError(f"index_membership_{family}_invalid")
        candles, member_facts = {}, {}
        for key, spec in specs.items():
            # An uncaptured required member is a prerequisite refusal. Never
            # truncate membership or replace this failure with an empty candle.
            candle, evidence = sector_cycles.member_candle_from_captured_inputs(
                spec["members"], captured=breadth.inputs)
            candles[key], member_facts[key] = candle, evidence
        ticker = sector_cycles._AMALGAM_FAMILIES[family]["benchmark"]
        benchmark = yahoo.cohort.frames[ticker]["close"].copy(deep=True)
        amalgams[family] = sector_cycles.AmalgamSource(
            specs=deepcopy(specs), candles=candles, bench_close=benchmark)
        lineage[family] = {
            "membership": {"origin": observation.origin, "source_revision": None,
                "captured_at": observation.captured_at.isoformat(),
                "observation": observation.outcome, "observation_reason": observation.reason,
                "byte_length": observation.byte_length, "sha256": observation.sha256},
            "member_capture": member_facts,
            "breadth_members": breadth.prior_identity(captured_at=prices.captured_at),
            "benchmark": {"ticker": ticker, "field": "close",
                "yahoo": yahoo.prior_identity(captured_at=prices.captured_at)},
        }
    reference = session_anchor.capture_reference_sessions("US", asof=evaluation_date)
    return SectorLocalCaptures(auxiliary, amalgams, lineage, {"US": reference}, completed,
                               classification)
