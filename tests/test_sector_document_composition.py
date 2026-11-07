"""All real calculation owners produce one five-member native-admissible Sector bundle."""
from copy import deepcopy
from pathlib import Path
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


@lru_cache(maxsize=2)
def _captured(n_sessions=320):
    closes, _, _, spy, _, _, _, populations = _make_universe(n_sessions=n_sessions, seed=11)
    candidates = pd.bdate_range(end=SOURCE, periods=max(450, n_sessions * 2) if n_sessions != 320 else 450)
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


@pytest.mark.parametrize("cutoff", [None, "2026-10-01T20:00:00Z"])
def test_dated_context_is_an_additive_five_member_join_with_unchanged_measurements(cutoff):
    from engine.sector_dated_context import project_dated_context
    args = captured()
    before = documents.compose_sector_documents(**args)
    raw = json.loads((Path(__file__).parent / "fixtures" / "leadership_rotation" /
                      "dated_context_inputs_v1.json").read_text(encoding="utf-8"))
    raw["decision_cutoff"] = cutoff
    args["context"] = replace(args["context"], dated_context_inputs=documents.SectorDatedContextInputs(**raw))
    after = documents.compose_sector_documents(**args)
    assert set(after.member_bytes) == set(before.member_bytes) == set(SECTOR_GENERATION_MEMBERS)
    key = "sectordata/sector_central.json"
    for member in set(SECTOR_GENERATION_MEMBERS) - {key}:
        assert after.member_bytes[member] == before.member_bytes[member]
    old, new = json.loads(before.member_bytes[key]), json.loads(after.member_bytes[key])
    packet = new.pop("dated_context")
    assert new == old
    assert packet == project_dated_context(**raw)
    if cutoff:
        assert packet["observations"]["status"] == "withheld"
        assert "revision_state" not in packet["observations"]
        assert packet["market_risk"]["status"] == "withheld"
    else:
        assert packet["observations"]["bottleneck"]["asof"] == "2026-09-01"
    assert all(value is False for value in packet["authority"].values())


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


# These fixtures exercise the real supplied-byte decoder, without acquisition,
# selection or publication. Their IDs, clocks, observations and no-dividend
# close/close_price equality are synthetic. Default 320-session tests above stay
# unchanged; genuine Yahoo admission requires at least 1,000 actual US sessions.
def _window_capture_fixture(*, missing=None):
    from pathlib import Path
    from collectors.yahoo import CycleBenchmarkAcquisition
    from lib.sector_input_capture import SectorPriceCaptures
    from lib import yahoo_generation_contract as yahoo
    from lib.yahoo_runtime_profile import SECTOR_CLOSE_TICKERS
    from scripts.vps_live_orchestrator import SelectedGenerationSnapshot

    args = deepcopy(_captured(1100))
    panel = args["cycle_inputs"].closes_tr.copy(deep=True)
    for index, ticker in enumerate(SECTOR_CLOSE_TICKERS):
        if ticker not in panel:
            panel[ticker] = 100.0 + index + np.arange(len(panel)) / 100
    panel = panel[list(SECTOR_CLOSE_TICKERS)]
    frames = {ticker: pd.DataFrame({"close": panel[ticker],
                                   "close_price": panel[ticker]})
              for ticker in SECTOR_CLOSE_TICKERS}
    if missing is not None:
        ticker, position = missing
        frames[ticker] = frames[ticker].drop(index=panel.index[position])
    revision = "334b26b540ea82fc2593ab3a723ceda65be32b3b"
    evaluated = BUILT - timedelta(seconds=3)
    prepared = BUILT - timedelta(seconds=2)
    published = BUILT - timedelta(seconds=1)
    clocks = {
        "known": {"evaluation_instant": evaluated.isoformat(), "expected_session": SOURCE,
            "session_calendar": "US", "target_calendar_verified": True,
            "completed_sessions_only": True, "minimum_history_sessions": 1000,
            "basis_tolerance": .001, "fetch_period": "max", "batch_size": 14,
            "retries": 1, "backoff_base_s": 0.0},
        "unknown": {
            "vendor_publication_clock": "Not supplied per bar by yfinance",
            "provider_available_at": "First retrievable time is not observed",
            "vendor_session_metadata": "No per-bar session-completion proof supplied",
            "upstream_correction_clock": "Corrections are observed only on a later request"},
    }
    lineage = {ticker: {
        "provider": "yahoo", "ticker": ticker, "vendor_symbol": ticker,
        "alias_applied": False, "field": "Adj Close", "basis": "total_return",
        "close_price_basis": "split_adjusted_dividend_unadjusted",
        "attempt_periods": ["max"], "basis_comparison": {}, "prior": "absent",
        "completed_sessions_only": True, "expected_session": SOURCE,
        "rows": len(frame), "first_session": frame.index[0].date().isoformat(),
        "last_session": SOURCE, "status": "accepted",
    } for ticker, frame in frames.items()}
    prior = {"kind": "bootstrap", "source_ref": "fixture-absent-yahoo", "content_id": None,
        "captured_at": (BUILT - timedelta(seconds=4)).isoformat(),
        "domain": yahoo.YAHOO_GENERATION_DOMAIN, "source_revision": revision,
        "member_sha256": {ticker: None for ticker in SECTOR_CLOSE_TICKERS},
        "member_bytes": {ticker: None for ticker in SECTOR_CLOSE_TICKERS}}
    acquisition = CycleBenchmarkAcquisition(
        accepted=True, reason="accepted", requested=SECTOR_CLOSE_TICKERS,
        returned=SECTOR_CLOSE_TICKERS, failed=(), primary_failed=(),
        failure_reasons={}, frames=frames, lineage=lineage, clocks=clocks, notes=())
    encoded = yahoo.encode_yahoo_acquisition(acquisition, prior_identity=prior,
        prepared_at=prepared, source_revision=revision)
    snapshot = SelectedGenerationSnapshot(
        domain=yahoo.YAHOO_GENERATION_DOMAIN, generation_id="fixture-sector-yahoo-1100",
        content_id="a" * 64, generation_dir=Path("/inert-fixture-not-read"),
        published_at=published.isoformat(),
        manifest={"input_identity": encoded.input_identity, "source_revision": revision,
                  "computed_at": prepared.isoformat()},
        members=encoded.members)
    verified = yahoo.verify_yahoo_snapshot(snapshot, now=BUILT, require_current=True)
    # Only the Yahoo leg is consumed by this adapter. The other five-owner inputs
    # remain the existing explicit calculation fixture; no breadth-capture
    # acquisition or admission is claimed by this new Yahoo receipt test.
    prices = SectorPriceCaptures(yahoo=verified, breadth=None, captured_at=BUILT)
    decoded_panel = pd.concat({ticker: verified.cohort.frames[ticker]["close"]
                               for ticker in SECTOR_CLOSE_TICKERS}, axis=1, sort=True)
    args["cycle_inputs"] = replace(args["cycle_inputs"], closes_tr=decoded_panel,
                                   closes_px=decoded_panel.copy(deep=True))
    args["timing_inputs"] = replace(args["timing_inputs"],
        etf_frames={fund: decoded_panel[fund].rename("close").to_frame()
                    for fund in args["timing_inputs"].funds})
    calibrations = dict(args["context"].fusion_calibrations)
    for ticker in SECTOR_CLOSE_TICKERS[:11]:
        for state in ("", *cycles.LADDER):
            calibrations[central.fusion_calibration_key({
                "kind": "sector", "ticker": ticker,
                "now": {"timing_state": state}})] = (1.0, 1.0)
    args["context"] = replace(args["context"], setup_closes=decoded_panel.copy(deep=True),
        fusion_calibrations=calibrations,
        sector_window_capture=documents.sector_window_capture_from_prices(prices))
    return args, prices


def test_sector_window_real_capture_chain_keeps_exact_values_receipt_and_clocks(monkeypatch):
    from lib import yahoo_generation_contract as yahoo
    from lib.yahoo_runtime_profile import SECTOR_CLOSE_TICKERS

    args, prices = _window_capture_fixture()
    before = args["cycle_inputs"].closes_tr.copy(deep=True)
    binding = deepcopy(args["context"].sector_window_capture.source_binding)
    rotation_seen = []
    from engine import leadership_rotation_context as lrc
    original_projection = lrc.measured_group_read
    def project(*a, **k):
        rotation_seen.append(deepcopy(k["rotation_payload"]))
        return original_projection(*a, **k)
    def forbidden(*a, **k):
        raise AssertionError("ambient input, selection, calendar acquisition or effect reached")
    original_datetime_module = SimpleNamespace(**vars(datetime_module))
    with monkeypatch.context() as scoped:
        scoped.setattr(relativedelta_module, "datetime", original_datetime_module)
        for owner, name in ((config, "load"), (config, "data_dir"), (config, "site_dir"),
                            (store, "read"), (central, "_load_rotation_events"),
                            (yahoo, "read_verified_yahoo_cohort"),
                            (sector_central_grader, "grade"),
                            (sector_central_grader, "append_central_log")):
            scoped.setattr(owner, name, forbidden)
        scoped.setattr(lrc, "measured_group_read", project)
        with _Trap() as trap:
            observed = {**args,
                "evaluation_date": documents.date.fromisoformat(SOURCE),
                "built_at": datetime_module.datetime.fromisoformat(BUILT.isoformat())}
            result = documents.compose_sector_documents(**observed)
    assert trap.reads == trap.writes == trap.clocks == trap.providers == []
    assert rotation_seen == [None]
    # The longer, admitted capture reaches a real rollover-watch branch that
    # the 320-session fixture never reached. Its owner must sort each actual
    # candidate, not capture an unrelated outer ticker variable.
    watch = json.loads(result.member_bytes["basketdata/baskets.json"])["theme_intel"]["rollover"]
    assert watch and [row["risk"] for row in watch] == sorted(
        (row["risk"] for row in watch), reverse=True)
    read = json.loads(result.member_bytes[SECTOR_GENERATION_MEMBERS[0]])["measured_read"]
    exact = read["sector_window_measurements"]
    assert exact["windows_sessions"] == [5, 20, 63]
    assert [row["group_id"] for row in exact["groups"]] == list(SECTOR_CLOSE_TICKERS[:11])
    assert exact["source_session"] == exact["end_session"] == SOURCE
    assert exact["windows"]["63"]["start_session"] == "2026-08-07"
    assert "2026-09-07" not in [x.date().isoformat()
        for x in args["cycle_inputs"].calculation_inputs.reference_sessions["US"]]
    cell = next(x for x in exact["groups"] if x["group_id"] == "XLB")["windows"]["5"]
    # XLB is the explicit 1100-row linear synthetic series: 110.99 / 110.94.
    assert cell["absolute_return_pct"] == pytest.approx((110.99 / 110.94 - 1) * 100, abs=1e-6)
    benchmark_ratio = before["SPY"].iloc[-1] / before["SPY"].iloc[-6]
    assert cell["relative_wealth_pct"] == pytest.approx(
        ((110.99 / 110.94) / benchmark_ratio - 1) * 100, abs=1e-6)
    assert exact["clocks"]["publication"] == (BUILT - timedelta(seconds=1)).isoformat()
    assert exact["clocks"]["availability"] is None
    assert exact["clocks"]["history"] is None and exact["clocks"]["correction"] is None
    assert exact["receipt"] == prices.yahoo.prior_identity(captured_at=BUILT)
    assert exact["source_roots"] == ["yahoo-sector-close-14"]
    assert exact["limitations"]["freshness"]["status"] == "unverified"
    assert exact["limitations"]["point_in_time"]["status"] == "not_qualified"
    assert all(flag is False for flag in exact["authority"].values())
    assert read["sector_dossiers"]["windows_sessions"] == [21, 63]
    json.dumps(exact, allow_nan=False)
    pd.testing.assert_frame_equal(args["cycle_inputs"].closes_tr, before)
    assert args["context"].sector_window_capture.source_binding == binding


def test_sector_window_absence_preserves_frozen_joined_preimage_bytes():
    result = documents.compose_sector_documents(**captured())
    # Parent executed the frozen 720995... composition owner with the joined
    # 36cfcb... Central and accepted 43b1cf... producer, before the optional join.
    expected = {
        "sectordata/sector_central.json": "88582a9f101a761ade15accbbc8c94014880a5d9a731cb46665d6edbbf3de6b1",
        "sectordata/sector_cycles.json": "6310bdc78ab7ddd56e34c4a5bfb8e846e21a56db2767fdf92daae3c983df63bf",
        "basketdata/baskets.json": "3e22034d17fce3190e910531e5155941f46c2a52c9afea9968b2bff80698b59f",
        "basketdata/si_handoff.json": "b0277b794719bb71ba335bbfee168f272d2f88ac95244aeb27433d7db4d45de0",
        "basketdata/action_board.json": "d68476a46519f92c0e6e683ca2f2dd39336f6b64101be070c330f698df89214f",
    }
    assert {name: hashlib.sha256(raw).hexdigest()
            for name, raw in result.member_bytes.items()} == expected
    assert "sector_window_measurements" not in json.loads(
        result.member_bytes[SECTOR_GENERATION_MEMBERS[0]])["measured_read"]


@pytest.mark.parametrize("change", ["panel", "source_session", "benchmark", "basis", "cohort",
                                   "receipt", "capture_type", "duplicate", "boolean", "future"])
def test_sector_window_incompatible_capture_refuses_before_calculation(change, monkeypatch):
    args, _ = _window_capture_fixture()
    capture = args["context"].sector_window_capture
    if change in ("panel", "duplicate", "boolean", "future"):
        panel = args["cycle_inputs"].closes_tr.copy(deep=True)
        if change == "panel":
            panel.iloc[-1, panel.columns.get_loc("XLB")] += 1
        elif change == "duplicate":
            panel = pd.concat([panel, panel.iloc[-1:]])
        elif change == "boolean":
            panel = panel.astype(object); panel.iloc[-1, 0] = True
        else:
            panel.loc[pd.Timestamp("2026-11-06")] = panel.iloc[-1]
        args["cycle_inputs"] = replace(args["cycle_inputs"], closes_tr=panel)
    elif change == "benchmark":
        args["cycle_inputs"] = replace(args["cycle_inputs"], benchmark="QQQ")
    elif change == "capture_type":
        args["context"] = replace(args["context"], sector_window_capture={})
    else:
        binding = deepcopy(capture.source_binding)
        if change == "source_session": binding["source_session"] = "2026-11-04"
        elif change == "basis": binding["price_basis"] = "price"
        elif change == "cohort": binding["cohort_id"] = "other"
        elif change == "receipt": binding["receipt"] = {"pad": "x" * 17000}
        args["context"] = replace(args["context"],
            sector_window_capture=replace(capture, source_binding=binding))
    def forbidden(*a, **k): raise AssertionError("calculation must not start")
    monkeypatch.setattr(baskets, "compute_baskets_from_inputs", forbidden)
    with pytest.raises(documents.SectorDocumentCompositionError):
        documents.compose_sector_documents(**args)


@pytest.mark.parametrize("ticker", ["XLB", "SPY"])
def test_sector_window_missing_start_observation_is_not_filled_or_shifted(ticker):
    # The verified member legitimately omits one old session; every retained
    # value is finite/positive and >1000 actual sessions remain. The outer
    # captured panel carries that absence, rather than a NaN encoded as a bar.
    args, _ = _window_capture_fixture(missing=(ticker, -6))
    result = documents.compose_sector_documents(**args)
    exact = json.loads(result.member_bytes[SECTOR_GENERATION_MEMBERS[0]])[
        "measured_read"]["sector_window_measurements"]
    window = exact["windows"]["5"]
    assert window["start_session"] == "2026-10-29"
    assert window["end_session"] == SOURCE
    cell = next(x for x in exact["groups"] if x["group_id"] == "XLB")["windows"]["5"]
    if ticker == "XLB":
        assert cell["absolute_return_pct"] is None
        assert cell["relative_wealth_pct"] is None
        assert cell["coverage"]["observed_n"] == 5
    else:
        assert cell["absolute_return_pct"] is not None
        assert cell["relative_wealth_pct"] is None
        assert cell["coverage"]["observed_n"] == 6
        assert window["benchmark_return_pct"] is None
        assert window["benchmark_coverage"]["observed_n"] == 5
    assert cell["null_reasons"]["relative_wealth_pct"] is not None


def test_sector_window_adapter_uses_supplied_bytes_not_mutable_frame_state():
    args, prices = _window_capture_fixture()
    original = args["context"].sector_window_capture
    prices.yahoo.cohort.frames["XLB"].iloc[-1, 0] *= 2
    assert documents.sector_window_capture_from_prices(prices) == original
    panel = args["cycle_inputs"].closes_tr.copy(deep=True)
    panel.iloc[-1, panel.columns.get_loc("XLB")] *= 2
    args["cycle_inputs"] = replace(args["cycle_inputs"], closes_tr=panel)
    with pytest.raises(documents.SectorDocumentCompositionError,
                       match="different_captured_sector_window_prices"):
        documents.compose_sector_documents(**args)


def test_sector_window_short_history_cannot_masquerade_as_verified_capture():
    from lib.yahoo_generation_contract import encode_history
    from lib.yahoo_runtime_profile import YahooRuntimeBindingError
    frame = captured()["cycle_inputs"].closes_tr["SPY"]
    with pytest.raises(YahooRuntimeBindingError, match="YAHOO_RUNTIME_HISTORY_INSUFFICIENT"):
        encode_history(pd.DataFrame({"close": frame, "close_price": frame}), source_session=SOURCE)


def test_sector_window_explicit_failure_is_visible_but_legacy_stays_failsoft(monkeypatch):
    from engine import leadership_rotation_context as lrc
    def refused(*a, **k): raise ValueError("explicit invalid composition fixture")
    monkeypatch.setattr(lrc, "measured_group_read", refused)
    def forbidden(*a, **k): raise AssertionError("captured absence must not load rotation")
    monkeypatch.setattr(central, "_load_rotation_events", forbidden)
    legacy = central._measured_read({}, rotation_payload=None)
    assert legacy["reason"] == "projection_error"
    with pytest.raises(central.SectorWindowProjectionError,
                       match="sector_window_projection_refused"):
        central._measured_read({}, rotation_payload=None, sector_window_inputs={})
