"""Captured values -> all five owners -> the incumbent private API.

Fixtures use real capture encoders/semantic verifiers and private publisher.
Only upstream acquisitions and identity lookups are controlled. The mounted-API
case includes real sponsor workbook parsing; it does not qualify a live provider
response, a worker execution, or production.
"""
from copy import deepcopy
from pathlib import Path
from dataclasses import replace
from datetime import date, timedelta
import hashlib
import json
import sys
from types import MappingProxyType

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from lib import sector_input_capture as capture, sector_auxiliary_capture as auxiliary
from lib import member_ohlcv_generation_contract as member_contract, config, store
from engine import session_anchor
from lib.yahoo_runtime_profile import SECTOR_CLOSE_TICKERS
from engine import sector_basket_documents as documents, sector_cycles, sector_action_board
from engine import theme_context, market_state, residual_alpha, group_flow, narrative_rotation
from scripts import vps_live_orchestrator as publisher
from app import main as macro_main
from app.sector_generation_reader import SectorGenerationReader
from tests.test_breadth_member_generation_contract import sources as _source_values, original, NOW, SOURCE, REVISION, _dates, _owner
from tests.test_member_ohlcv_generation_contract import dependency, acquire, encode, EVALUATION, PUBLISHED
from tests.test_sector_generation_api import _incumbent_gates

BUILT = NOW + timedelta(seconds=20)
CAPTURED = NOW + timedelta(seconds=18)
DATED = (date.fromisoformat(SOURCE) - timedelta(days=1)).isoformat()


def _aux(*, _capture_at=CAPTURED, **changes):
    values = {
        "config": {"engine": {"group_flow": {}, "macro_overlay": {},
            "confluence": {"sector_macro_beta": {"XLK": 0.2, "XLE": -0.1}}},
            "sponsors": {"sector_funds": list(SECTOR_CLOSE_TICKERS[:11])}},
        "market_state": {"schema": "market_state.v1", "asof": DATED, "market": "us",
            "is_display_only": True, "score": 57, "verdict": "MIXED",
            "label_en": "Mixed", "label_zh": "混合", "color": "yellow",
            "radar": {"state": "caution"}, "freshness": {"stale": False}},
        "alpha": {"as_of": DATED, "n": 2, "windows": {"beta_win": 252, "form": 252, "skip": 21, "shrink": .66},
            "per_ticker": {"T0000": {"alpha": .7, "sector_rank": 1, "sector_n": 2, "entry": "intact"},
                           "T0001": {"alpha": None, "sector_rank": None, "sector_n": None, "entry": None}}},
        "regime_latest": {"date": DATED, "liquidity_overlay": "neutral", "macro_risk": {"score": 0.0}},
        "factors": {"table": [{"ticker": "T0000", "composite_rank": .8, "sue": .2, "sector": "Industrials"}]},
    }
    values.update(changes)
    observations = {key: auxiliary.CapturedAuxiliarySource("fixture:/" + key, REVISION, _capture_at,
        "absent", "not_found", None, None, None) for key in auxiliary.SOURCE_KEYS}
    for key, value in values.items():
        if value is None:
            continue
        if isinstance(value, pd.DataFrame):
            from tests.test_sector_auxiliary_capture import parquet
            raw = parquet(value)
        elif auxiliary.SOURCE_SPECS[key][0] == "jsonl":
            raw = ("\n".join(json.dumps(row, ensure_ascii=False, allow_nan=False) for row in value) + "\n").encode()
        else:
            raw = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
        observations[key] = auxiliary.CapturedAuxiliarySource("fixture:/" + key, REVISION, _capture_at,
            "present", "observed", raw, len(raw), hashlib.sha256(raw).hexdigest())
    return auxiliary.decode_sector_auxiliary_capture(observations, captured_at=_capture_at)


@pytest.fixture(scope="module")
def sources(tmp_path_factory):
    # Narrative's incumbent four-basket minimum must be satisfied by the captured
    # membership itself. Keep the real encoder/verification path and every price.
    values = _source_values.__wrapped__(tmp_path_factory)
    values["membership"] = deepcopy(values["membership"])
    for number in range(1, 4):
        values["membership"]["baskets"]["theme_" + str(number)] = {
            "name": "Fixture theme " + str(number), "name_zh": "测试主题" + str(number),
            "category": "Other", "etf_proxy": ["QQQ"],
            "members": [{"ticker": f"T{i:04d}", "added": "2025-01-01"}
                        for i in range(number * 3, number * 3 + 3)]}
    # Extras binds the complete membership, including primary-price members.
    # Reacquire through the same controlled owner after changing that source.
    from lib import breadth_member_generation_contract as broad
    from scripts import fetch_basket_extras
    from tests.test_breadth_member_generation_contract import BROAD_GROUPS, YCFG
    groups, yahoo = values["groups"], values["yahoo"]
    _, primary, meta, _ = broad.derive_primary({g: item.panels for g, item in groups.items()},
        yahoo.cohort.frames["SPY"], source_session=SOURCE)
    qualified = frozenset(t for t, group in meta["source"].items() if t in groups[group].current)
    with pytest.MonkeyPatch.context() as scoped:
        scoped.setattr(fetch_basket_extras, "_download_closes", lambda names, **kwargs:
            pd.DataFrame({"NEW": [10., 11.]}, index=_dates(2)))
        values["extras"] = fetch_basket_extras.acquire_extras_from_inputs(
            membership=values["membership"], primary_panel=primary, prior_extras=None,
            qualified_primary_members=qualified, primary_history_threshold=252,
            evaluation_instant=NOW + timedelta(seconds=2), yahoo_config=YCFG, aliases={},
            history_start="2023-01-01", primary_basis="provider_auto_adjusted")
    assert values["extras"].status == "complete"
    return values


@pytest.fixture(scope="module")
def captured_inputs(dependency, tmp_path_factory):
    breadth, yahoo = dependency
    fresh = {}
    for ticker, close in breadth.inputs.resolved_panel.items():
        observed = close.dropna()
        fresh[ticker] = pd.DataFrame({"open": observed - .25, "high": observed + 2,
            "low": observed - 2, "close": observed, "volume": observed * 0 + 1000})
    encoded = encode(dependency, acquisition=acquire(dependency, fresh=fresh))
    root = tmp_path_factory.mktemp("assembled-input-capture")
    owner = _owner(root, PUBLISHED)
    result = owner.publish_member_ohlcv_inputs(encoded, generation_id="assembly-candles",
        source_revision=REVISION, expected_current_content_id=None)
    assert result.status == "published", result.detail
    member_at = PUBLISHED + timedelta(seconds=1)
    member = member_contract.read_verified_member_ohlcv_inputs(
        generations_root=owner.state_dir / "generations", now=member_at,
        breadth=breadth, yahoo=yahoo, require_current=True)
    previous = capture.read_previous_sector_capture(generations_root=owner.state_dir / "generations",
        allow_bootstrap=True, clock=lambda: CAPTURED)
    assert previous.absence_reason == "domain_absent"
    tops, evidence = {}, {}
    for fund in SECTOR_CLOSE_TICKERS[:11]:
        tops[fund] = pd.DataFrame({"ticker": ["T0000", "T0001", "T0002"],
            "name": ["Fixture 0", "Fixture 1", "Fixture 2"],
            "weight_pct": [10.0, 9.0, 8.0], "rank": [1, 2, 3]},
            index=pd.DatetimeIndex([DATED] * 3, name="date"))
        # A controlled already-resolved collector result, not a workbook-parser test.
        raw = ("controlled-resolved-holdings:" + fund).encode()
        evidence[fund] = {"outcome": "present", "origin": "fixture:holdings/" + fund,
            "captured_at": CAPTURED.isoformat(), "document_date": DATED,
            "sha256": hashlib.sha256(raw).hexdigest(), "byte_length": len(raw)}
    spec = {"name": "Captured complex", "name_zh": "捕获组合",
        "members": [{"ticker": "T0000"}, {"ticker": "T0001"}, {"ticker": "T0002"}]}
    candle, facts = sector_cycles.member_candle_from_captured_inputs(spec["members"], captured=breadth.inputs)
    assert candle is not None
    amalgams = {family: sector_cycles.AmalgamSource(specs={"complex": deepcopy(spec)},
        candles={"complex": deepcopy(candle)}, bench_close=yahoo.cohort.frames[ticker]["close"].copy())
        for family, ticker in (("nasdaq", "QQQ"), ("russell", "IWM"))}
    args = dict(prices=capture.SectorPriceCaptures(yahoo, breadth, EVALUATION),
        member_ohlcv=member, member_captured_at=member_at, auxiliary=_aux(), previous=previous,
        holdings=tops, holdings_evidence=evidence, amalgams=amalgams,
        amalgam_input_lineage={family: {"source": "controlled_resolved_membership",
            "captured_at": CAPTURED.isoformat(), "member_capture": facts} for family in amalgams},
        reference_sessions={"US": _dates(1100)}, evaluation_date=date.fromisoformat(SOURCE),
        built_at=BUILT, input_version="captured-assembly-fixture", source_qualification="accepted",
        live_hazard_parity=None)
    return args, root


def _forbidden(*args, **kwargs):
    raise AssertionError("assembly reached ambient acquisition, clock or publication")


def test_assembly_uses_supplied_snapshots_and_preserves_owner_populations(captured_inputs, monkeypatch):
    args, _ = captured_inputs
    with monkeypatch.context() as scoped:
        for owner, name in ((config, "load"), (config, "data_dir"), (config, "site_dir"),
                            (store, "read"), (pd, "read_parquet"),
                            (session_anchor, "capture_reference_sessions"),
                            (publisher, "read_selected_generation"),
                            (market_state, "market_state_snapshot"), (market_state, "load_persisted"),
                            (residual_alpha, "compute_residual_alpha"),
                            (group_flow, "_acquire_setup"), (narrative_rotation, "_acquire_setup"),
                            (publisher.Orchestrator, "publish_sector_documents")):
            scoped.setattr(owner, name, _forbidden)
        scoped.setitem(sys.modules, "scripts.build_stock_library", None)
        actual = capture.assemble_sector_inputs(**args)
    assert actual.context.core_source_session == actual.context.baseline_session == SOURCE
    assert actual.input_identity["sector_view"]["source_qualification"] == "accepted"
    assert actual.expected_current_content_id is None
    assert actual.theme_inputs.prior_sector_text is None
    assert actual.cycle_inputs.calculation_inputs is actual.timing_inputs.calculation_inputs
    pd.testing.assert_frame_equal(actual.basket_inputs.closes, args["prices"].breadth.inputs.broad_panel)
    pd.testing.assert_frame_equal(actual.allocation_inputs.panel["closes"], args["prices"].breadth.inputs.broad_panel)
    pd.testing.assert_frame_equal(actual.theme_inputs.panel["closes"], args["prices"].breadth.inputs.resolved_panel)
    assert set(actual.cycle_inputs.amalgams) == {"nasdaq", "russell"}
    assert set(actual.timing_inputs.funds) == set(SECTOR_CLOSE_TICKERS[:11])
    lineage = actual.input_identity["sector_capture"]
    assert lineage["owner_qualifications"]["market_state"]["asof"] == DATED
    assert lineage["owner_qualifications"]["alpha"]["as_of"] == DATED
    assert lineage["owner_qualifications"]["alpha"]["availability"] is None
    assert lineage["member_ohlcv"]["content_id"] == args["member_ohlcv"].snapshot.content_id
    assert actual.context.sector_window_capture.source_binding["clocks"]["availability"] is None
    assert actual.timing_inputs.alpha_per_ticker["T0001"]["alpha"] is None
    assert actual.timing_inputs.factor_z["T0000"] == .8
    assert actual.timing_inputs.sue_z["T0000"] == .2
    assert actual.timing_inputs.macro_beta["XLK"] == .2
    assert actual.timing_inputs.macro_drag == 0.0
    actual.timing_inputs.top_holdings["XLB"].iloc[0, 2] = 88
    assert args["holdings"]["XLB"].iloc[0, 2] == 10
    actual.context.auxiliary_evidence["owner_qualifications"]["alpha"]["n"] = 99
    assert actual.input_identity["sector_capture"]["owner_qualifications"]["alpha"]["n"] == 2


def test_captured_chain_publishes_once_and_reaches_actual_mounted_api(captured_inputs, monkeypatch, tmp_path):
    args, root = captured_inputs
    from engine.sector_dated_context import project_dated_context
    raw = json.loads((Path(__file__).parent / "fixtures" / "leadership_rotation" /
                      "dated_context_inputs_v1.json").read_text(encoding="utf-8"))
    regime, risk = raw["regime_document"], raw["public_risk_document"]
    # Test owner clocks precede this actual capture; the bottleneck deliberately
    # remains older. None is restamped to the sector price session by production.
    regime["asof"] = regime["freshness"]["asof"] = SOURCE
    regime["freshness"]["built_at"] = NOW.isoformat()
    regime["theme_revisions"]["asof"] = SOURCE
    regime["date"] = DATED
    risk["source_session"] = risk["as_of"] = SOURCE
    risk["observed_at"] = risk["produced_at"] = NOW.isoformat()
    risk["measured_state"]["as_of"] = SOURCE
    risk["freshness"]["source_session"] = SOURCE
    for entry in risk["freshness"]["per_source"].values():
        entry["as_of"] = SOURCE if entry["matches_session"] else DATED
    settings = args["auxiliary"].document("config")
    settings.update(raw["config_document"])
    # A controlled theme roster whose members occur in the actual encoded
    # breadth fixture. This is not a real company-to-sector evidence claim.
    roster_map = {"MU": "T0000", "WDC": "T0001", "SNDK": "T9999", "STX": "T0002", "NTAP": "T8888"}
    settings["themes"]["memory_storage"]["tickers"] = list(roster_map.values())
    for member in regime["theme_revisions"]["themes"]["memory_storage"]["members"]:
        member["ticker"] = roster_map[member["ticker"]]
    args = dict(args, auxiliary=_aux(config=settings, regime_latest=regime,
                                    public_risk_envelope=risk))
    roots = _write_local_capture_sources(args, tmp_path)
    from tests.test_sector_classification_context import write_classification_reference
    write_classification_reference(roots["R"])
    local = _read_local(args, roots)
    args = dict(args, **local.assembly_arguments())
    from types import SimpleNamespace
    from collectors.sector_holdings import SectorHoldingsAdapter, SSGA_XLSX
    from tests.test_sector_holdings_explicit_inputs import workbook
    raw_holdings = workbook([
        ["Fixture 0", "T0000", 10.0], ["Fixture 1", "T0001", 9.0],
        ["Fixture 2", "T0002", 8.0]], document_date=DATED)
    acquired_urls = []
    def holdings_http(self, url, **kwargs):
        acquired_urls.append(url)
        assert kwargs == {"retries": 3, "timeout": 60,
                          "headers": {"User-Agent": "Mozilla/5.0 (research)"}}
        return SimpleNamespace(content=raw_holdings)
    monkeypatch.setattr(SectorHoldingsAdapter, "http_get", holdings_http)
    sponsors = local.auxiliary.document("config")["sponsors"]
    holdings = SectorHoldingsAdapter.capture_from_inputs(
        sponsors=sponsors, evaluated_at=EVALUATION, clock=lambda: CAPTURED)
    assert acquired_urls == [SSGA_XLSX.format(fund=fund.lower())
                             for fund in sponsors["sector_funds"]]
    assert len(acquired_urls) == 11
    for fund, frame in holdings.snapshots.items():
        assert list(frame["ticker"]) == ["T0000", "T0001", "T0002"]
        assert list(frame["weight_pct"]) == [10, 9, 8]
        assert all(value.date().isoformat() == DATED for value in frame.index)
        assert holdings.evidence[fund]["sha256"] == hashlib.sha256(raw_holdings).hexdigest()
        assert holdings.evidence[fund]["byte_length"] == len(raw_holdings)
        assert holdings.workbooks[fund] == raw_holdings
    args = dict(args, **holdings.assembly_arguments())
    actual = capture.assemble_sector_inputs(**args)
    assert actual.input_identity["sector_capture"]["holdings"] == holdings.evidence
    composition = documents.compose_sector_documents(**actual.composition_arguments())
    assert len(composition.member_bytes) == 5
    central = json.loads(composition.member_bytes["sectordata/sector_central.json"])
    dated_inputs = actual.context.dated_context_inputs
    expected_dated = project_dated_context(
        theme_key=dated_inputs.theme_key, regime_document=dated_inputs.regime_document,
        config_document=dated_inputs.config_document, public_risk_document=dated_inputs.public_risk_document,
        source_attribution=dated_inputs.source_attribution)
    assert central["dated_context"] == expected_dated
    assert central["captured_classification"] == local.classification_context
    assert central["captured_classification"]["association"]["coverage"]["associated_n"] == 3
    assert central["captured_classification"]["status"] == "partial"
    assert expected_dated["status"] == "dated_context"
    assert expected_dated["observations"]["bottleneck"]["asof"] == "2026-09-01"
    assert expected_dated["observations"]["revision_state"]["n_covered"] == 3
    assert expected_dated["theme"]["roster_size"] == 5
    assert expected_dated["limitations"]["current_sector_usable"] is False
    assert expected_dated["market_risk"]["scope"] == "market_global"
    for key, source in (("regime_document", "regime_latest"), ("config_document", "config"),
                        ("public_risk_document", "public_risk_envelope")):
        assert expected_dated["provenance"]["source_attribution"][key]["raw_sha256"] == local.auxiliary.observation(source).sha256
    measurements = central["measured_read"]["sector_window_measurements"]
    assert measurements["windows_sessions"] == [5, 20, 63]
    assert len(measurements["groups"]) == 11
    assert measurements["clocks"]["publication"] == args["prices"].yahoo.snapshot.published_at
    assert all(value is False for value in measurements["authority"].values())
    owner = _owner(root, BUILT + timedelta(seconds=1))
    published = owner.publish_sector_documents(composition, input_identity=actual.input_identity,
        generation_id="captured-sector-1", source_revision=REVISION,
        expected_current_content_id=actual.expected_current_content_id)
    assert published.status == "published", published.detail
    generations = owner.state_dir / "generations"
    reader = SectorGenerationReader(generations_root=generations, clock=lambda: BUILT + timedelta(seconds=2))
    monkeypatch.setattr(macro_main.app.state, "sector_generation_reader", reader, raising=False)
    client = TestClient(macro_main.app)
    client.cookies.set("sb-fixture-auth-token", "fixture")
    pointer_before = (generations / "sector/current.json").read_bytes()
    for audience in ("preview", "entitled"):
        response = client.get("/api/sector-generation?audience=" + audience)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["source_session"] == SOURCE
        assert body["published_at"] == published.published_at
        assert body["projection"]["receipt"]["generation_id"] == "captured-sector-1"
        projected = body["projection"]["data"]["core"]["measured_read"]["sector_window_measurements"]
        assert projected == measurements
        assert body["projection"]["data"]["core"]["dated_context"] == expected_dated
        assert body["projection"]["data"]["core"]["captured_classification"] == local.classification_context
        assert len(projected["groups"]) == 11
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["vary"] == "Cookie"
        assert "controlled_resolved_membership" not in response.text
        assert "fixture:holdings" not in response.text
        # Keep the exact mounted-API bytes for the isolated browser transport
        # probe. This remains inside pytest's temporary fixture directory.
        (tmp_path / f"sector-generation-{audience}.json").write_bytes(response.content)
    assert (generations / "sector/current.json").read_bytes() == pointer_before
    previous = capture.read_previous_sector_capture(generations_root=generations,
        allow_bootstrap=False, clock=lambda: BUILT + timedelta(seconds=2))
    next_args = {**args, "previous": previous, "built_at": BUILT + timedelta(seconds=3)}
    next_capture = capture.assemble_sector_inputs(**next_args)
    assert next_capture.expected_current_content_id == published.content_id
    assert next_capture.theme_inputs.prior_sector_text.encode() == composition.member_bytes["sectordata/sector_central.json"]


@pytest.mark.parametrize("failure", [
    "holdings_none", "holdings_missing_fund", "holdings_empty_observed", "holdings_future_date",
    "holdings_bad_hash", "holdings_all_failed", "holdings_undated_rows",
    "amalgams_none", "amalgam_lineage_absent", "amalgam_benchmark_changed",
    "reference_absent", "reference_missing_observation", "reference_intraday",
    "naive_build", "evaluation_after_build", "capture_after_build", "member_before_prices",
    "unresolved_config", "unresolved_market_state", "unresolved_alpha",
    "previous_fake_absence", "source_qualification_absent",
])
def test_required_input_shortfalls_refuse_before_any_owner_calculation(captured_inputs, monkeypatch, failure):
    original_args, _ = captured_inputs
    args = dict(original_args)
    if failure.startswith("holdings_"):
        args["holdings"] = deepcopy(original_args["holdings"])
        args["holdings_evidence"] = deepcopy(original_args["holdings_evidence"])
    if failure == "holdings_none": args["holdings"] = None
    elif failure == "holdings_missing_fund": del args["holdings"]["XLB"]
    elif failure == "holdings_empty_observed": args["holdings"]["XLB"] = args["holdings"]["XLB"].iloc[:0]
    elif failure == "holdings_future_date": args["holdings_evidence"]["XLB"]["document_date"] = "2026-11-09"
    elif failure == "holdings_bad_hash": args["holdings_evidence"]["XLB"]["sha256"] = "unbound"
    elif failure == "holdings_undated_rows": args["holdings"]["XLB"] = args["holdings"]["XLB"].reset_index(drop=True)
    elif failure == "holdings_all_failed":
        args["holdings"] = {fund: None for fund in args["holdings"]}
        for fact in args["holdings_evidence"].values(): fact.update(outcome="unreadable", reason="controlled_read_failure")
    elif failure == "amalgams_none": args["amalgams"] = None
    elif failure == "amalgam_lineage_absent": args["amalgam_input_lineage"] = {}
    elif failure == "amalgam_benchmark_changed":
        args["amalgams"] = deepcopy(args["amalgams"])
        args["amalgams"]["nasdaq"].bench_close.iloc[-1] += 1
    elif failure == "reference_absent": args["reference_sessions"] = {}
    elif failure == "reference_missing_observation": args["reference_sessions"] = {"US": args["reference_sessions"]["US"][1:]}
    elif failure == "reference_intraday": args["reference_sessions"] = {"US": args["reference_sessions"]["US"] + pd.Timedelta(hours=1)}
    elif failure == "naive_build": args["built_at"] = BUILT.replace(tzinfo=None)
    elif failure == "evaluation_after_build": args["evaluation_date"] = date(2026, 11, 9)
    elif failure == "capture_after_build": args["member_captured_at"] = BUILT + timedelta(seconds=1)
    elif failure == "member_before_prices": args["member_captured_at"] = NOW
    elif failure == "unresolved_config": args["auxiliary"] = _aux(config=None)
    elif failure == "unresolved_market_state": args["auxiliary"] = _aux(market_state=None)
    elif failure == "unresolved_alpha": args["auxiliary"] = _aux(alpha=None)
    elif failure == "previous_fake_absence": args["previous"] = replace(args["previous"], absence_reason=None)
    elif failure == "source_qualification_absent": args["source_qualification"] = None
    monkeypatch.setattr(documents, "compose_sector_documents", _forbidden)
    monkeypatch.setattr(publisher.Orchestrator, "publish_sector_documents", _forbidden)
    with pytest.raises((capture.SectorInputCaptureError, ValueError)):
        capture.assemble_sector_inputs(**args)


@pytest.mark.parametrize("key,field,value", [
    ("market_state", "score", True), ("market_state", "score", 101),
    ("market_state", "market", "hk"), ("market_state", "is_display_only", False),
    ("market_state", "label_en", "Risk-on"), ("market_state", "asof", "2026-11-09"),
    ("alpha", "n", 3), ("alpha", "as_of", "2026-02-30"),
])
def test_owner_qualification_is_more_than_json_decoding(key, field, value):
    source = _aux().document(key)
    source[field] = value
    packet = _aux(**{key: source})
    with pytest.raises(capture.SectorInputCaptureError):
        capture._qualified_owner_context(packet, evaluation_date=date.fromisoformat(SOURCE))


@pytest.mark.parametrize("field,value", [("alpha", True), ("sector_rank", 0),
    ("sector_rank", 3), ("sector_n", True), ("entry", "BUY_NOW")])
def test_alpha_consumed_row_refuses_incoherent_values(field, value):
    alpha = _aux().document("alpha")
    alpha["per_ticker"]["T0000"][field] = value
    with pytest.raises(capture.SectorInputCaptureError):
        capture._qualified_owner_context(_aux(alpha=alpha), evaluation_date=date.fromisoformat(SOURCE))


def test_partial_holdings_and_missing_stock_coverage_are_named(captured_inputs):
    original_args, _ = captured_inputs
    args = {**original_args, "holdings": deepcopy(original_args["holdings"]),
        "holdings_evidence": deepcopy(original_args["holdings_evidence"])}
    args["holdings"]["XLB"] = None
    args["holdings_evidence"]["XLB"].update(outcome="unreadable", reason="controlled_read_failure")
    args["holdings"]["XLK"].iloc[0, 0] = "OUTSIDE"
    actual = capture.assemble_sector_inputs(**args)
    assert actual.timing_inputs.top_holdings["XLB"] is None
    assert actual.input_identity["sector_capture"]["holdings"]["XLB"]["outcome"] == "unreadable"
    assert actual.input_identity["sector_capture"]["holding_price_coverage"]["missing"] == ["OUTSIDE"]
    assert "OUTSIDE" not in actual.timing_inputs.stock_frames


def test_member_snapshot_bytes_cannot_be_detached_from_manifest(captured_inputs):
    args, _ = captured_inputs
    old = args["member_ohlcv"]
    raw = dict(old.snapshot.members)
    name = next(iter(raw))
    raw[name] = raw[name] + b"changed"
    damaged = replace(old, snapshot=replace(old.snapshot, members=MappingProxyType(raw)))
    with pytest.raises(ValueError):
        capture.assemble_sector_inputs(**{**args, "member_ohlcv": damaged})


def test_captured_archive_seed_preserves_incumbent_values_without_reads(monkeypatch):
    frame = pd.DataFrame({"asof": ["2026-11-02", "2026-10-30"], "snapshot_json": [
        '{"themes":[{"id":"theme","label":"rising","score":4}]}',
        '{"themes":[{"id":"theme","label":"neutral","score":2}]}']})
    monkeypatch.setattr(pd, "read_parquet", _forbidden)
    result = theme_context.seed_history_from_inputs(frame)
    assert [row["asof"] for row in result] == ["2026-10-30", "2026-11-02"]
    assert result[1] == {"asof": "2026-11-02", "leadership_state": None,
        "trailing_leader_id": None, "leader_health": None,
        "labels": {"theme": "rising"}, "scores": {"theme": 4}}
    assert list(frame["asof"]) == ["2026-11-02", "2026-10-30"]


@pytest.mark.parametrize("case", ["future_history", "unordered_history", "invalid_history_date", "future_seed"])
def test_prior_context_must_be_dated_before_or_on_document_baseline(captured_inputs, case):
    base, _ = captured_inputs
    later = BUILT + timedelta(days=3)
    values = [{"asof": "2026-11-04", "labels": {"test_theme": "rising"}, "scores": {"test_theme": 4}}]
    if case == "unordered_history":
        values = [{"asof": "2026-11-02", "labels": {}, "scores": {}},
                  {"asof": "2026-10-30", "labels": {}, "scores": {}}]
    elif case == "invalid_history_date":
        values[0]["asof"] = "2026-02-30"
    if case == "future_seed":
        data = pd.DataFrame({"asof": ["2026-11-04"],
            "snapshot_json": ['{"themes":[{"id":"test_theme","label":"rising","score":4}]}']})
        aux = _aux(_capture_at=later, theme_seed_archive=data)
    else:
        aux = _aux(_capture_at=later, theme_context_history=values)
    with pytest.raises(capture.SectorInputCaptureError, match="context_history"):
        capture.assemble_sector_inputs(**{**base, "auxiliary": aux,
            "built_at": later + timedelta(seconds=1), "evaluation_date": later.date(),
            "source_qualification": "stale"})


def test_impossible_score_verdict_is_not_a_qualified_market_state():
    state = _aux().document("market_state")
    state.update(score=100, verdict="RISK_OFF", label_en="Risk-off", label_zh="避险", color="red")
    with pytest.raises(capture.SectorInputCaptureError, match="market_state"):
        capture._qualified_owner_context(_aux(market_state=state), evaluation_date=date.fromisoformat(SOURCE))


def test_chronological_history_preserves_same_day_owner_entries(captured_inputs):
    base, _ = captured_inputs
    values = [
        {"asof": "2026-10-30", "labels": {}, "scores": {}},
        {"asof": "2026-11-03", "labels": {"test_theme": "rising"}, "scores": {"test_theme": 4}},
        {"asof": "2026-11-03", "labels": {"test_theme": "strong"}, "scores": {"test_theme": 5}},
    ]
    result = capture.assemble_sector_inputs(**dict(base, auxiliary=_aux(theme_context_history=values)))
    assert result.context.context_history == values



def _write_local_capture_sources(base, tmp_path, *, alias_theme=False):
    """Actual bounded files; holdings remain the separately resolved fixture."""
    from pathlib import Path
    from tests.test_sector_auxiliary_capture import parquet
    repo = (tmp_path / "source-repo").resolve()
    theme_root = repo if alias_theme else (tmp_path / "theme-context").resolve()
    roots = {"R": repo, "D": repo / ("data" if alias_theme else "configured-data"),
             "S": repo / "published-site", "T": theme_root}
    for path in roots.values():
        path.mkdir(parents=True, exist_ok=True)
    documents_by_key = {key: base["auxiliary"].document(key)
                       for key, (kind, _) in auxiliary.SOURCE_SPECS.items() if kind != "parquet"}
    documents_by_key["config"]["storage"] = {
        "data_dir": str(roots["D"].relative_to(repo)),
        "site_dir": str(roots["S"].relative_to(repo))}
    archive = pd.DataFrame({"asof": [DATED], "snapshot_json": ['{"themes":[]}']})
    for key, (kind, declaration) in auxiliary.SOURCE_SPECS.items():
        prefix, relative = declaration.split("/", 1)
        path = roots[prefix] / relative
        if kind == "parquet":
            value = archive if key in {"basket_archive", "theme_seed_archive"} else base["auxiliary"].table(key)
        else:
            value = documents_by_key[key]
        if value is None:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        if kind == "parquet":
            raw = parquet(value)
        elif kind == "jsonl":
            raw = ("\n".join(json.dumps(row, ensure_ascii=False, allow_nan=False) for row in value) + "\n").encode()
        else:
            raw = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
        path.write_bytes(raw)
    for family, source in base["amalgams"].items():
        path = roots["D"] / ("baskets_" + family) / "membership.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"amalgamations": source.specs}, ensure_ascii=False), encoding="utf-8")
    return roots


def _read_local(base, roots, *, clock=lambda: CAPTURED):
    return capture.read_sector_local_captures(repository_root=roots["R"], theme_root=roots["T"],
        prices=base["prices"], evaluation_date=base["evaluation_date"], clock=clock)


def test_local_capture_uses_actual_config_roots_and_single_observation_aliases(captured_inputs, tmp_path, monkeypatch):
    base, _ = captured_inputs
    roots = _write_local_capture_sources(base, tmp_path, alias_theme=True)
    observed = []
    original_read = publisher._read_source_bytes
    def counting(source, **kwargs):
        observed.append(str(source))
        return original_read(source, **kwargs)
    monkeypatch.setattr(publisher, "_read_source_bytes", counting)
    monkeypatch.setattr(config, "load", _forbidden)
    monkeypatch.setattr(config, "data_dir", _forbidden)
    monkeypatch.setattr(config, "site_dir", _forbidden)
    actual = _read_local(base, roots)
    assert observed.count("config.yml") == 1
    assert observed.count("baskets.parquet") == 1
    archive = actual.auxiliary.observation("basket_archive")
    seed = actual.auxiliary.observation("theme_seed_archive")
    assert (archive.origin, archive.captured_at, archive.sha256) == (seed.origin, seed.captured_at, seed.sha256)
    assert actual.auxiliary.observation("alpha").origin == str(roots["S"] / "factordata/alpha.json")
    assert all(e.source_revision is None for e in actual.auxiliary.evidence)
    assert actual.auxiliary.observation("cycle_bands").observation == "absent"
    assert actual.auxiliary.observation("cycle_bands").observation_reason == "not_found"
    assert actual.reference_sessions["US"].equals(
        session_anchor.capture_reference_sessions("US", asof=base["evaluation_date"]))
    for family, ticker in (("nasdaq", "QQQ"), ("russell", "IWM")):
        pd.testing.assert_series_equal(actual.amalgams[family].bench_close,
            base["prices"].yahoo.cohort.frames[ticker]["close"])
        facts = actual.amalgam_input_lineage[family]
        assert facts["membership"]["sha256"] == hashlib.sha256(
            (roots["D"] / ("baskets_" + family) / "membership.json").read_bytes()).hexdigest()
        assert facts["member_capture"]["complex"]["bundle_source_session"] == SOURCE
    with pytest.raises(capture.SectorInputCaptureError, match="holdings_capture_unresolved"):
        capture.assemble_sector_inputs(**dict(base, **actual.assembly_arguments(),
                                              holdings=None, holdings_evidence=None))


def test_local_index_membership_must_match_native_capture_bytes(captured_inputs, sources, tmp_path, monkeypatch):
    from lib import breadth_member_generation_contract as broad
    from lib.sector_index_membership_capture import capture_index_membership
    from scripts import fetch_basket_extras
    from tests.test_breadth_member_generation_contract import YCFG, PREPARED, PUBLISHED as BROAD_PUBLISHED

    base, _ = captured_inputs
    roots = _write_local_capture_sources(base, tmp_path)
    captured_at = NOW + timedelta(seconds=1)
    adjunct = capture_index_membership({family: capture._observe_sector_source(
        roots["D"] / ("baskets_" + family) / "membership.json", limit=1024 * 1024,
        clock=lambda: captured_at) for family in ("nasdaq", "russell")}, before=captured_at)
    _, primary, meta, _ = broad.derive_primary({g: item.panels for g, item in sources["groups"].items()},
        sources["yahoo"].cohort.frames["SPY"], source_session=SOURCE)
    monkeypatch.setattr(fetch_basket_extras, "_download_closes", lambda names, **kwargs:
        pd.DataFrame({"NEW": [10., 11.]}, index=_dates(2)))
    extras = fetch_basket_extras.acquire_extras_from_inputs(membership=sources["membership"],
        primary_panel=primary, prior_extras=None,
        qualified_primary_members=frozenset(t for t, g in meta["source"].items()
                                             if t in sources["groups"][g].current),
        primary_history_threshold=252, evaluation_instant=NOW + timedelta(seconds=2),
        yahoo_config=YCFG, aliases={}, history_start="2023-01-01",
        primary_basis="provider_auto_adjusted", index_membership=adjunct)
    encoded_broad = broad.encode_breadth_member_acquisitions(
        **{**sources, "extras": extras, "index_membership": adjunct})
    owner = _owner(tmp_path / "native-index", BROAD_PUBLISHED)
    publication = owner.publish_breadth_member_inputs(encoded_broad, generation_id="local-index-bound",
        source_revision=REVISION, expected_current_content_id=None)
    assert publication.status == "published", publication.detail
    captured = broad.read_verified_breadth_member_inputs(generations_root=owner.state_dir / "generations",
        yahoo=encoded_broad.yahoo, now=EVALUATION, require_current=True)
    bound = dict(base, prices=capture.SectorPriceCaptures(encoded_broad.yahoo, captured, EVALUATION))
    assert _read_local(bound, roots).amalgams["nasdaq"].candles["complex"] is not None
    path = roots["D"] / "baskets_nasdaq" / "membership.json"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(capture.SectorInputCaptureError, match="index_membership_nasdaq_generation_mismatch"):
        _read_local(bound, roots)


@pytest.mark.parametrize("case", ["absent", "malformed", "shape", "uncaptured_member",
                                  "bad_config", "escaping_root"])
def test_local_capture_refuses_unresolved_real_prerequisites(captured_inputs, tmp_path, case):
    base, _ = captured_inputs
    roots = _write_local_capture_sources(base, tmp_path)
    path = roots["D"] / "baskets_nasdaq/membership.json"
    expected = "index_membership_nasdaq"
    if case == "absent":
        path.unlink()
    elif case == "malformed":
        path.write_bytes(b'{"amalgamations":')
    elif case == "shape":
        path.write_bytes(b"{}")
    elif case == "uncaptured_member":
        value = json.loads(path.read_bytes())
        value["amalgamations"]["complex"]["members"][0]["ticker"] = "UNCAPTURED"
        path.write_text(json.dumps(value))
        expected = "uncaptured_member_index_population"
    elif case == "bad_config":
        (roots["R"] / "config.yml").write_text("storage: {}\nstorage: {}\n")
        expected = "configuration_root_source_malformed"
    else:
        p = roots["R"] / "config.yml"
        value = json.loads(p.read_bytes())
        value["storage"]["data_dir"] = "../outside"
        p.write_text(json.dumps(value))
        expected = "absolute_capture_root_required"
    with pytest.raises(ValueError, match=expected):
        _read_local(base, roots)


def test_local_capture_preserves_malformed_optional_bytes_as_decode_outcome(captured_inputs, tmp_path):
    base, _ = captured_inputs
    roots = _write_local_capture_sources(base, tmp_path)
    path = roots["S"] / "factordata/factors.json"
    path.write_bytes(b'{"table":')
    actual = _read_local(base, roots)
    evidence = actual.auxiliary.observation("factors")
    assert evidence.observation == "present"
    assert evidence.decode_outcome == "malformed"
    assert evidence.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual.auxiliary.document("factors") is None
    assert actual.auxiliary.observation("basket_archive").origin != actual.auxiliary.observation("theme_seed_archive").origin


def test_local_capture_rejects_clock_before_bound_generation(captured_inputs, tmp_path, monkeypatch):
    base, _ = captured_inputs
    roots = _write_local_capture_sources(base, tmp_path)
    monkeypatch.setattr(publisher, "_read_source_bytes", _forbidden)
    with pytest.raises(capture.SectorInputCaptureError, match="capture_clock"):
        _read_local(base, roots, clock=lambda: base["prices"].captured_at - timedelta(seconds=1))


@pytest.mark.parametrize("kind", ["leaf_symlink", "ancestor_symlink", "fifo", "bound"])
def test_local_observer_refuses_unsafe_sources(tmp_path, kind):
    import os
    path = (tmp_path / "source.json").resolve()
    if kind == "leaf_symlink":
        other = tmp_path / "other.json"
        other.write_bytes(b"{}")
        path.symlink_to(other)
    elif kind == "ancestor_symlink":
        actual = tmp_path / "actual"
        actual.mkdir()
        (actual / "source.json").write_bytes(b"{}")
        link = tmp_path / "linked"
        link.symlink_to(actual, target_is_directory=True)
        path = link / "source.json"  # Deliberately do not resolve a symlink.
    elif kind == "fifo":
        os.mkfifo(path)
    else:
        path.write_bytes(b"x" * 129)
    with pytest.raises(capture.SectorInputCaptureError, match="unsafe_capture"):
        capture._observe_sector_source(path, limit=128, clock=lambda: CAPTURED)


@pytest.mark.parametrize("code, outcome, reason", [(2, "absent", "not_found"),
    (13, "unreadable", "read_denied"), (5, "unreadable", "io_error")])
def test_local_observer_keeps_actual_os_failure_distinctions(tmp_path, monkeypatch, code, outcome, reason):
    import os
    path = (tmp_path / "source.json").resolve()
    path.write_bytes(b"{}")
    original_open = os.open
    def fail_leaf(name, flags, *args, **kwargs):
        if str(name) == path.name:
            raise OSError(code, "controlled read fault")
        return original_open(name, flags, *args, **kwargs)
    monkeypatch.setattr(os, "open", fail_leaf)
    actual = capture._observe_sector_source(path, limit=128, clock=lambda: CAPTURED)
    assert (actual.outcome, actual.reason) == (outcome, reason)
    assert actual.raw_bytes is actual.byte_length is actual.sha256 is None


def test_local_observer_records_observed_in_place_change(tmp_path, monkeypatch):
    import os
    path = (tmp_path / "source.json").resolve()
    path.write_bytes(b'{"before":1}')
    original_read = os.read
    changed = False
    def concurrent_change(fd, size):
        nonlocal changed
        raw = original_read(fd, size)
        if raw and not changed:
            changed = True
            path.write_bytes(b'{"changed":1000000}')
        return raw
    monkeypatch.setattr(os, "read", concurrent_change)
    actual = capture._observe_sector_source(path, limit=128, clock=lambda: CAPTURED)
    assert (actual.outcome, actual.reason) == ("unreadable", "unstable_read")
    assert actual.raw_bytes is actual.sha256 is None


@pytest.mark.parametrize("name", ["/absolute.json", "../outside.json", "sub/file.json", ".", ".."])
def test_retained_directory_reader_requires_one_relative_leaf(tmp_path, name):
    import os
    from pathlib import Path
    descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(publisher.SourceReadRejected, match="relative source leaf"):
            publisher._read_source_bytes(Path(name), limit=128, directory_fd=descriptor, require_stable=True)
    finally:
        os.close(descriptor)



def test_local_observer_growth_exceeding_bound_is_not_optional_unreadable(tmp_path, monkeypatch):
    import os
    path = (tmp_path / "source.json").resolve()
    path.write_bytes(b"x" * 32)
    original_read = os.read
    changed = False
    def grow(fd, size):
        nonlocal changed
        raw = original_read(fd, size)
        if raw and not changed:
            changed = True
            with path.open("ab") as stream:
                stream.write(b"x" * 256)
        return raw
    monkeypatch.setattr(os, "read", grow)
    with pytest.raises(capture.SectorInputCaptureError, match="unsafe_capture_source:encoded_bound"):
        capture._observe_sector_source(path, limit=128, clock=lambda: CAPTURED)
