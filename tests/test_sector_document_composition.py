"""All real calculation owners produce one five-member native-admissible Sector bundle."""
from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime, timezone, timedelta
from functools import lru_cache
import hashlib
import json
import datetime as datetime_module
from types import SimpleNamespace
import dateutil.relativedelta as relativedelta_module

import numpy as np
import pandas as pd
import pytest

from engine import baskets, cycles, group_flow, narrative_rotation as nr, sector_action_board as board
from engine import sector_basket_documents as documents, sector_central as central, sector_central_grader
from engine import sector_cycles as sc, theme_scoring as ts
from lib import config, store, market_session
from lib.closes_panel import align_latest_common_observation
from lib.sector_generation_contract import SECTOR_GENERATION_MEMBERS, preflight_sector_bundle
from tests.test_theme_allocation_explicit_inputs import _make_universe, _make_membership, NAMES, CALIBRATION, EMPTY_MACRO, _Trap
from tests.test_basket_enrichments_explicit_inputs import cycle_inputs, WEIGHTS
from tests.test_sector_cycles_explicit_inputs import _panel
from tests.test_sector_central import _mkt

SOURCE = "2026-11-05"
BUILT = datetime(2026, 11, 5, 23, tzinfo=timezone.utc)


@lru_cache(maxsize=1)
def _captured():
    closes, _, _, spy, _, _, _, populations = _make_universe(n_sessions=320, seed=11)
    candidates = pd.bdate_range(end=SOURCE, periods=450)
    idx = candidates[[market_session.is_session_date("US", stamp.date()) for stamp in candidates]][-len(closes):].as_unit("ns")
    closes.index = idx; spy.index = idx
    closes, spy, observation = align_latest_common_observation(closes, spy)
    membership = _make_membership(idx, populations)
    narrative = nr._build_setup({"cfg": {}, "mem": membership, "closes": closes, "bench_close": spy})
    theme_panel = {"mem": membership, "closes": closes, "rets": narrative["rets"], "idx": idx,
        "bench": narrative["bench"], "region": "us", "observation": observation,
        "price_resolution": {"effective_as_of": SOURCE}}
    cfg = deepcopy(group_flow._DEFAULTS)
    rows = ts.prepare_theme_basket_rows(theme_panel, region="us", group_flow_cfg=cfg, names_sectors=NAMES)
    frames = {ticker: pd.DataFrame({"open": close * .998, "high": close * 1.01, "low": close * .99,
        "close": close, "volume": pd.Series(10000.0 + np.arange(len(idx)), index=idx).where(close.notna())})
        for ticker, close in closes.items()}
    calculation = cycle_inputs(idx)
    enrichments = ts.basket_enrichments_from_inputs(rows, region="us", member_frames=frames,
        reference_close=closes, source_session=SOURCE, calculation_inputs=calculation,
        rollover_weights=WEIGHTS, breadth_divergence_fit={})
    basket_input = baskets.BasketInputs(membership=membership, closes=closes,
        spy=spy.rename("close").to_frame(), extras=None, names_sectors=NAMES, proxy_frames={})
    theme_input = ts.ThemeScoreInputs(region="us", panel=theme_panel, basket_rows=rows, group_flow_cfg=cfg,
        names_sectors=NAMES, macro_context=deepcopy(EMPTY_MACRO), signal_calibration=deepcopy(CALIBRATION),
        regime_snapshot={}, regime_sizing={}, regime_caution_scored=False, prior_sector_text=None,
        evaluation_date=date.fromisoformat(SOURCE), earnings_calendar={}, market_concentration={"hhi": .11, "n": 21},
        basket_enrichments=enrichments, bench_label="S&P 500", bench_label_zh="标普500")
    allocation_input = nr.NarrativeAllocationInputs(region="us", panel=narrative,
        region_meta={"id": "us", "market_en": "US", "market_zh": "美国", "bench_label": "S&P 500",
            "bench_label_zh": "标普500", "phase0_file": "thematic_rotation_phase0.json", "phase0_fallback": None},
        radar={}, short_interest=None, sizing_calibration={}, phase0_meta={}, phase0_fallback_meta=None)
    etfs = _panel(n=len(idx)); etfs.index = idx; etfs["SPY"] = spy
    volumes = pd.DataFrame({ticker: frame["volume"] for ticker, frame in frames.items()})
    candles = {}
    for bid, spec in membership["baskets"].items():
        tickers = [member["ticker"] for member in spec["members"]]
        candles[bid] = sc.member_candle_from_inputs(spec["members"], idx,
            close=closes[tickers], volume=volumes[tickers])
    cycle_input = sc.SectorCyclesInputs(closes_tr=etfs, closes_px=etfs.copy(deep=True), benchmark="SPY",
        basket_specs=membership["baskets"], basket_candles=candles, amalgams={}, phase_history=None,
        phase_history_status="absent", asof=SOURCE, hazard_calibration=None, calculation_inputs=calculation,
        live_hazard_parity=None)
    funds = ("XLK", "XLF", "XLE")
    tops = {}
    for fund, bid in zip(funds, ("mag7", "regional_banks", "energy_complex")):
        tickers = populations[bid][:3]
        tops[fund] = pd.DataFrame({"ticker": tickers, "name": [f"Holding {ticker}" for ticker in tickers],
                                  "weight_pct": [10.0, 9.0, 8.0]})
    timing_input = board.SectorTimingInputs(source_session=SOURCE, funds=funds,
        etf_frames={fund: etfs[fund].rename("close").to_frame() for fund in funds}, top_holdings=tops,
        stock_frames=frames, liquidity="neutral", macro_drag=0.0, macro_beta={fund: 1.0 for fund in funds},
        alpha_per_ticker={}, insider_map={}, factor_z={}, sue_z={}, calculation_inputs=calculation,
        auxiliary_evidence={"source": "synthetic_test_fixture", "holdings_observed_at": "2026-11-04"})
    calibrations = {}
    descriptors = [{"kind": "sector", "ticker": ticker} for ticker in funds]
    descriptors += [{"kind": "basket", "ticker": spec.get("etf_proxy"), "name": spec["name"]}
                    for spec in membership["baskets"].values()]
    for descriptor in descriptors:
        for state in ("", *cycles.LADDER):
            calibrations[central.fusion_calibration_key({**descriptor, "now": {"timing_state": state}})] = (1.0, 1.0)
    context = documents.SectorDocumentContext(core_source_session=SOURCE, baseline_session=SOURCE,
        market_context=_mkt(risk_on=0.0, gate_factor=1.0), membership_unavailable=False,
        rotation_artifact={}, rotation_events=None, fragmentation=None, fusion_calibrations=calibrations,
        setup_latest={"date": SOURCE}, setup_closes=etfs, setup_sectors=funds, context_history=[],
        bottoming_cycle_rows=None, bottoming_ledger_session=None, sector_names_zh={},
        factor_seasonality=None, flow={"as_of": "2026-11-04", "cluster": {"regime": "broadening"}},
        pulse_archive=[], pulse_heat_calibration={}, grader_calls=None, grader_frozen=None,
        auxiliary_evidence={"source": "synthetic_test_fixture", "flow_as_of": "2026-11-04"})
    return dict(basket_inputs=basket_input, theme_inputs=theme_input, allocation_inputs=allocation_input,
        cycle_inputs=cycle_input, timing_inputs=timing_input, context=context,
        evaluation_date=date.fromisoformat(SOURCE), built_at=BUILT)


def captured():
    return deepcopy(_captured())


def test_real_owner_chain_is_atomic_finite_and_admitted_for_both_audiences(monkeypatch):
    args = captured()
    before_baskets = args["basket_inputs"].closes.copy(deep=True)
    before_etfs = args["cycle_inputs"].closes_tr.copy(deep=True)
    def forbidden(*a, **k): raise AssertionError("ambient acquisition or ledger effect reached")
    original_datetime_module = SimpleNamespace(**vars(datetime_module))
    with monkeypatch.context() as scoped:
        # pandas DateOffset uses dateutil type checks against real datetime values.
        # Preserve that library dependency while the observer traps engine clocks.
        scoped.setattr(relativedelta_module, "datetime", original_datetime_module)
        for owner, name in ((config, "load"), (config, "data_dir"), (config, "site_dir"), (store, "read"),
                            (sector_central_grader, "grade"), (sector_central_grader, "append_central_log")):
            scoped.setattr(owner, name, forbidden)
        with _Trap() as trap:
            # The observer replaces date classes throughout engine modules; use
            # its factories for explicit values so type checks remain meaningful.
            observed_args = {**args,
                "evaluation_date": documents.date.fromisoformat(args["evaluation_date"].isoformat()),
                "built_at": datetime_module.datetime.fromisoformat(args["built_at"].isoformat())}
            result = documents.compose_sector_documents(**observed_args)
    assert trap.reads == trap.writes == trap.clocks == trap.providers == []
    assert set(result.member_bytes) == set(SECTOR_GENERATION_MEMBERS)
    data = {name: json.loads(raw) for name, raw in result.member_bytes.items()}
    central_doc, cycle_doc, baskets_doc, handoff, action = (data[name] for name in SECTOR_GENERATION_MEMBERS)
    assert central_doc["as_of"] == cycle_doc["meta"]["asOf"] == baskets_doc["as_of"] == SOURCE
    assert action["baskets_sha256"] == hashlib.sha256(result.member_bytes[SECTOR_GENERATION_MEMBERS[2]]).hexdigest()
    assert len(central_doc["sectors"]) == len(cycle_doc["sectors"]) == 3
    assert len(baskets_doc["theme_intel"]["themes"]) >= 3
    assert all(theme["mtf"]["source"] == "member_ohlcv" for theme in baskets_doc["theme_intel"]["themes"])
    assert central_doc["publication"]["premium_payload"]["written"] is False
    assert central_doc["publication"]["research_handoff"]["status"] == "unbound"
    assert result.evidence["basket_documents"]["flow_source_as_of"] == "2026-11-04"
    assert result.evidence["grader"]["calls_appended"] is False
    for name, raw in result.member_bytes.items():
        assert result.evidence["member_sha256"][name] == hashlib.sha256(raw).hexdigest()
    pd.testing.assert_frame_equal(args["basket_inputs"].closes, before_baskets)
    pd.testing.assert_frame_equal(args["cycle_inputs"].closes_tr, before_etfs)
    identity = {"sector_view": {"schema": "sector.view_inputs.v1", "source_session": SOURCE,
        "input_version": "all-owner-fixture-v1", "baseline_session": None, "source_qualification": "accepted"}}
    views = preflight_sector_bundle(member_bytes=result.member_bytes, input_identity=identity,
        generation_id="all-owner-fixture-v1", published_at=BUILT.isoformat(), now=BUILT)
    assert set(views) == {"preview", "entitled"}
    assert all(view["receipt"]["qualification"] == "accepted" for view in views.values())


def test_later_evaluation_day_retains_default_cycle_source_clock():
    args = captured(); later = date(2026, 11, 6)
    args["theme_inputs"] = replace(args["theme_inputs"], evaluation_date=later)
    args["cycle_inputs"] = replace(args["cycle_inputs"], asof=None)
    args.update(evaluation_date=later, built_at=BUILT + timedelta(days=1))
    result = documents.compose_sector_documents(**args)
    assert result.evidence["evaluation_date"] == "2026-11-06"
    assert result.evidence["cycle_evaluation_date"] == SOURCE
    assert result.evidence["cycle_asof"] is None
    assert result.evidence["core_source_session"] == SOURCE
    assert json.loads(result.member_bytes[SECTOR_GENERATION_MEMBERS[0]])["as_of"] == SOURCE


@pytest.mark.parametrize("change", ["future_core", "future_baseline", "future_cycle", "different_cycle_settings", "theme_clock", "timing_clock", "naive_build", "missing_spy", "future_setup", "different_setup", "different_timing", "different_membership", "frozen_nat", "frozen_intraday", "frozen_future"])
def test_incompatible_inputs_refuse_before_any_calculation(change, monkeypatch):
    args = captured()
    if change == "future_core": args["context"] = replace(args["context"], core_source_session="2026-11-06")
    elif change == "future_baseline": args["context"] = replace(args["context"], baseline_session="2026-11-06")
    elif change == "future_cycle":
        future = replace(args["cycle_inputs"].calculation_inputs, evaluation_date="2026-11-06")
        args["cycle_inputs"] = replace(args["cycle_inputs"], calculation_inputs=future)
        args["timing_inputs"] = replace(args["timing_inputs"], calculation_inputs=future)
    elif change == "different_cycle_settings":
        changed = replace(args["timing_inputs"].calculation_inputs, macro_overlay={"changed": True})
        args["timing_inputs"] = replace(args["timing_inputs"], calculation_inputs=changed)
    elif change == "theme_clock": args["theme_inputs"] = replace(args["theme_inputs"], evaluation_date=date(2026, 11, 6))
    elif change == "timing_clock": args["timing_inputs"] = replace(args["timing_inputs"], source_session="2026-11-04")
    elif change == "naive_build": args["built_at"] = BUILT.replace(tzinfo=None)
    elif change == "missing_spy": args["context"] = replace(args["context"], setup_closes=args["context"].setup_closes.drop(columns="SPY"))
    elif change == "future_setup":
        panel = args["context"].setup_closes.copy(deep=True)
        panel.loc[pd.Timestamp("2026-11-06")] = panel.iloc[-1]
        args["context"] = replace(args["context"], setup_closes=panel)
    elif change == "different_setup":
        panel = args["context"].setup_closes.copy(deep=True); panel.iloc[-1, panel.columns.get_loc("XLK")] *= 1.01
        args["context"] = replace(args["context"], setup_closes=panel)
    elif change == "different_timing":
        frames = deepcopy(args["timing_inputs"].etf_frames); frames["XLK"].iloc[-1, 0] *= 1.01
        args["timing_inputs"] = replace(args["timing_inputs"], etf_frames=frames)
    elif change == "different_membership":
        specs = deepcopy(args["cycle_inputs"].basket_specs); specs["mag7"]["members"][0]["ticker"] = "OTHER"
        args["cycle_inputs"] = replace(args["cycle_inputs"], basket_specs=specs)
    elif change in ("frozen_nat", "frozen_intraday", "frozen_future"):
        stamps = {"frozen_nat": [pd.NaT], "frozen_intraday": ["2026-11-05T12:00:00"], "frozen_future": ["2026-11-06"]}[change]
        frozen = pd.DataFrame({"a__level_tr": [100.0]}, index=pd.DatetimeIndex(stamps))
        args["context"] = replace(args["context"], grader_frozen=frozen)
    def forbidden(*a, **k): raise AssertionError("calculation must not start")
    monkeypatch.setattr(baskets, "compute_baskets_from_inputs", forbidden)
    with pytest.raises(documents.SectorDocumentCompositionError):
        documents.compose_sector_documents(**args)


@pytest.mark.parametrize("mode", ["explicit_ceiling", "benchmark_tail"])
def test_cycle_central_and_grader_share_the_same_effective_yahoo_panel(mode, monkeypatch):
    args = captured(); baseline = documents.compose_sector_documents(**args)
    raw = args["cycle_inputs"].closes_tr.copy(deep=True)
    raw.loc[pd.Timestamp("2026-11-06")] = raw.iloc[-1] * 2
    if mode == "benchmark_tail": raw.loc[pd.Timestamp("2026-11-06"), "SPY"] = np.nan
    args["cycle_inputs"] = replace(args["cycle_inputs"], closes_tr=raw, closes_px=raw.copy(deep=True),
        asof=SOURCE if mode == "explicit_ceiling" else None)
    observed = []
    original_grade = sector_central_grader.grade_from_inputs
    def grade(*a, **k):
        observed.append(k["yahoo_panel"].copy(deep=True)); return original_grade(*a, **k)
    monkeypatch.setattr(sector_central_grader, "grade_from_inputs", grade)
    result = documents.compose_sector_documents(**args)
    assert result.member_bytes == baseline.member_bytes
    assert len(observed) == 1 and str(observed[0].index[-1].date()) == SOURCE
    assert pd.Timestamp("2026-11-06") not in observed[0].index
    central_doc = json.loads(result.member_bytes[SECTOR_GENERATION_MEMBERS[0]])
    assert central_doc["publication"]["secondary_sources"]["si_handoff"]["as_of"] == SOURCE


def older_baseline(day):
    """Recalculate the original theme/narrative owners on an actual older panel."""
    args = captured()
    old = args["basket_inputs"]
    closes = old.closes.loc[:day].copy(deep=True)
    spy = old.spy["close"].loc[:day].copy(deep=True)
    closes, spy, observation = align_latest_common_observation(closes, spy)
    idx = closes.index
    narrative = nr._build_setup({"cfg": {}, "mem": old.membership, "closes": closes, "bench_close": spy})
    panel = {"mem": old.membership, "closes": closes, "rets": narrative["rets"], "idx": idx,
        "bench": narrative["bench"], "region": "us", "observation": observation,
        "price_resolution": {"effective_as_of": day}}
    theme = args["theme_inputs"]
    rows = ts.prepare_theme_basket_rows(panel, region="us", group_flow_cfg=theme.group_flow_cfg, names_sectors=NAMES)
    frames = {ticker: frame.loc[:day].copy(deep=True) for ticker, frame in args["timing_inputs"].stock_frames.items()}
    enrichment = ts.basket_enrichments_from_inputs(rows, region="us", member_frames=frames,
        reference_close=closes, source_session=day,
        calculation_inputs=args["cycle_inputs"].calculation_inputs, rollover_weights=WEIGHTS,
        breadth_divergence_fit={})
    candles = {}
    volumes = pd.DataFrame({ticker: frame["volume"] for ticker, frame in frames.items()})
    for bid, spec in old.membership["baskets"].items():
        tickers = [member["ticker"] for member in spec["members"]]
        candles[bid] = sc.member_candle_from_inputs(spec["members"], idx,
            close=closes[tickers], volume=volumes[tickers])
    args["basket_inputs"] = replace(old, closes=closes, spy=spy.rename("close").to_frame())
    args["theme_inputs"] = replace(theme, panel=panel, basket_rows=rows, basket_enrichments=enrichment)
    args["allocation_inputs"] = replace(args["allocation_inputs"], panel=narrative)
    args["cycle_inputs"] = replace(args["cycle_inputs"], basket_candles=candles)
    args["context"] = replace(args["context"], baseline_session=day)
    return args


def composition_identity(result, *, baseline=True):
    facts = result.evidence
    return {"sector_view": {"schema": "sector.view_inputs.v1", "source_session": facts["core_source_session"],
        "input_version": "all-owner-fixture-v1",
        "baseline_session": facts["baseline_session"] if baseline and facts["baseline_session"] != facts["core_source_session"] else None,
        "source_qualification": "accepted"}, "capture": {"source": "synthetic_test_fixture"}}


def private_owner(tmp_path, now=BUILT):
    from scripts.vps_live_orchestrator import Orchestrator
    return Orchestrator(live_dir=tmp_path / "public/live", state_dir=tmp_path / "state",
                        data_dir=tmp_path / "data", now=now)


def publish_composition(tmp_path, result, *, now=BUILT, identity=None, generation="g1", expected=None):
    return private_owner(tmp_path, now).publish_sector_documents(
        result, input_identity=composition_identity(result) if identity is None else identity,
        generation_id=generation, source_revision="fixture-composition-source", expected_current_content_id=expected)


@pytest.mark.parametrize("baseline", [SOURCE, "2026-11-04", "2026-11-02"])
def test_actual_composition_private_publication_and_selected_reader(tmp_path, baseline):
    from app.sector_generation import SectorGenerationRequest
    from app.sector_generation_reader import SectorGenerationReader
    from scripts.vps_live_orchestrator import read_selected_generation
    args = captured() if baseline == SOURCE else older_baseline(baseline)
    result = documents.compose_sector_documents(**args)
    published = publish_composition(tmp_path, result)
    root = tmp_path / "state/generations"
    if baseline == "2026-11-02":
        assert published.status == "rejected", published.detail
        assert "sector_source_not_accepted" in published.detail
        assert not (root / "sector/current.json").exists()
        return
    assert published.status == "published", published.detail
    raw = read_selected_generation(generations_root=root, domain="sector", members=SECTOR_GENERATION_MEMBERS)
    assert dict(raw.members) == result.member_bytes
    assert raw.manifest["computed_at"] == BUILT.isoformat()
    reader = SectorGenerationReader(generations_root=root, clock=lambda: BUILT + timedelta(minutes=1))
    for audience in ("preview", "entitled"):
        selected = reader.read_selected_generation(SectorGenerationRequest(audience))
        assert selected.qualification == "accepted"
        assert selected.source_session == SOURCE
        assert selected.payload["data"]["brief"]["as_of"] == baseline
        assert selected.payload["data"]["action_board"]["as_of"] == baseline
        if baseline != SOURCE:
            assert selected.payload["data"]["brief"]["status"] == "declared_older_baseline"
            assert selected.payload["receipt"]["baseline_session"] == baseline
    assert not list((tmp_path / "state").glob(".private-input-*"))
    assert not (tmp_path / "public/live").exists()


def test_older_baseline_cannot_be_omitted_from_composition_publication(tmp_path):
    from lib.sector_generation_contract import SectorGenerationContractError
    result = documents.compose_sector_documents(**older_baseline("2026-11-04"))
    with pytest.raises(SectorGenerationContractError, match="composition_identity_mismatch"):
        publish_composition(tmp_path, result, identity=composition_identity(result, baseline=False))
    assert not (tmp_path / "state").exists()


def test_late_publication_cannot_reuse_preparation_acceptance(tmp_path):
    result = documents.compose_sector_documents(**captured())
    first = publish_composition(tmp_path, result)
    assert first.status == "published", first.detail
    pointer = tmp_path / "state/generations/sector/current.json"
    before = pointer.read_bytes()
    delayed = publish_composition(tmp_path, result, now=datetime(2026, 11, 10, 23, tzinfo=timezone.utc),
        generation="g2", expected=first.content_id)
    assert delayed.status == "rejected", delayed.detail
    assert "sector_source_not_accepted" in delayed.detail
    assert pointer.read_bytes() == before


def test_computation_after_actual_publication_is_rejected(tmp_path):
    args = captured()
    args["built_at"] = BUILT + timedelta(minutes=1)
    result = documents.compose_sector_documents(**args)
    attempt = publish_composition(tmp_path, result, now=BUILT)
    assert attempt.status == "rejected"
    assert "sector_computation_after_publication_or_changed" in attempt.detail
    assert not (tmp_path / "state/generations/sector/current.json").exists()


@pytest.mark.parametrize("change", ["bytes", "member_set", "identity", "build_clock"])
def test_changed_composition_refuses_before_private_staging(tmp_path, change):
    from lib.sector_generation_contract import SectorGenerationContractError
    result = documents.compose_sector_documents(**captured())
    identity = composition_identity(result)
    if change == "bytes":
        raw = dict(result.member_bytes); raw[SECTOR_GENERATION_MEMBERS[0]] += b" "
        result = replace(result, member_bytes=raw)
    elif change == "member_set":
        raw = dict(result.member_bytes); del raw[SECTOR_GENERATION_MEMBERS[4]]
        result = replace(result, member_bytes=raw)
    elif change == "identity": identity["sector_view"]["source_session"] = "2026-11-04"
    elif change == "build_clock":
        evidence = deepcopy(result.evidence); evidence["built_at"] = (BUILT + timedelta(seconds=1)).isoformat()
        result = replace(result, evidence=evidence)
    with pytest.raises(SectorGenerationContractError):
        publish_composition(tmp_path, result, identity=identity)
    assert not (tmp_path / "state").exists()
