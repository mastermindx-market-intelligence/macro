"""Actual native acquisition/publisher join with controlled provider responses.

This proves local source behavior, not live-provider coverage, VPS resource fit,
global legacy-profile transfer, production deployment or product acceptance.
"""
from copy import deepcopy
from datetime import timedelta
from io import BytesIO
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from types import SimpleNamespace

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml

from collectors.breadth import BreadthAdapter, capture_adjusted_policy
from collectors.yahoo import YahooAdapter
from lib import adjusted_price_capture as values, ticker_aliases
from scripts import prepare_sector_native_inputs as prepare, vps_live_orchestrator as owner
from scripts import fetch_basket_extras, fetch_basket_ohlcv
from tests.test_breadth_member_generation_contract import sources, NOW, SOURCE, REVISION, CFG, YCFG
from tests.test_member_ohlcv_generation_contract import frame

CLOCK = NOW + timedelta(seconds=10)


def _orch(root, **kwargs):
    return owner.Orchestrator(live_dir=root / "public/live", state_dir=root / "private/state",
        data_dir=root / "legacy", now=CLOCK, source_revision=REVISION,
        work_budget_seconds=owner.BARS_WORK_SECONDS, **kwargs)


def _inputs(root, sources):
    root.mkdir(parents=True, exist_ok=True)
    (root / "config").mkdir(exist_ok=True)
    cfg = {"storage": {"data_dir": "data"}, "yahoo": deepcopy(YCFG),
           **{group: deepcopy(CFG) for group in prepare.broad.BROAD_GROUPS}}
    (root / "config.yml").write_text(yaml.safe_dump(cfg))
    (root / "config/delisted_symbols.yml").write_text("symbols: {}\n")
    for family in ("baskets", "baskets_nasdaq", "baskets_russell", *prepare.broad.BROAD_GROUPS):
        (root / "data" / family).mkdir(parents=True, exist_ok=True)
    (root / "data/baskets/membership.json").write_text(json.dumps(sources["membership"]))
    for family in ("nasdaq", "russell"):
        (root / "data" / ("baskets_" + family) / "membership.json").write_text(json.dumps(
            {"amalgamations": {"fixture": {"members": [{"ticker": "T0000"}, {"ticker": "INDEXONLY"}]}}}))
    for group, acquired in sources["groups"].items():
        acquired.members.to_parquet(root / "data" / group / "constituents.parquet", index=False)
    return cfg


def _providers(mp, sources, *, generations_root=None, events=None):
    events = [] if events is None else events
    mp.setattr(ticker_aliases, "YAHOO_FETCH_ALIASES", {})
    def yahoo_download(self, tickers, period, **kwargs):
        events.append(("download", "yahoo", period))
        return pd.concat({ticker: sources["yahoo"].cohort.frames[ticker].rename(
            columns={"close": "Adj Close", "close_price": "Close", "volume": "Volume"})
            for ticker in tickers}, axis=1)
    def breadth_download(self, tickers, period, **kwargs):
        events.append(("download", self.group, period))
        if generations_root is not None:
            assert (generations_root / prepare.yahoo.YAHOO_GENERATION_DOMAIN / "current.json").exists(), "breadth started before Yahoo publication"
        panels = sources["groups"][self.group].panels
        return values.AdjustedPriceCapture(
            {field: panel.loc[:, list(tickers)] for field, panel in panels.items()},
            {ticker: (panels["close"].index[0], panels["close"].index[-1]) for ticker in tickers}, tuple(tickers))
    def closes(tickers, **kwargs):
        index = sources["groups"]["breadth"].panels["close"].index
        return pd.DataFrame({ticker: 30. + pd.Series(range(len(index)), index=index) / 10 for ticker in tickers})
    def ohlcv(tickers, **kwargs):
        events.append(("download", "member", kwargs["history_start"]))
        if generations_root is not None:
            assert (generations_root / prepare.broad.DOMAIN / "current.json").exists(), "member started before breadth publication"
        return {ticker: frame(count=320, offset=i) for i, ticker in enumerate(tickers)}
    mp.setattr(YahooAdapter, "_download", yahoo_download)
    mp.setattr(BreadthAdapter, "_download_adjusted_capture", breadth_download)
    mp.setattr(fetch_basket_extras, "_download_closes", closes)
    mp.setattr(fetch_basket_ohlcv, "_download_ohlcv", ohlcv)


@pytest.fixture(scope="module")
def native_chain(sources, tmp_path_factory):
    root = tmp_path_factory.mktemp("native-runtime-chain")
    repository = root / "inputs"
    _inputs(repository, sources)
    orchestrator = _orch(root)
    generations = orchestrator.state_dir / "generations"
    retained, events = root / "prepared", []
    retained.mkdir(mode=0o700)
    in_child = [False]
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(owner, "ROOT", repository)
        _providers(mp, sources, generations_root=generations, events=events)
        for kind, name in (("yahoo", "publish_yahoo_inputs"), ("breadth", "publish_breadth_member_inputs"),
                           ("member", "publish_member_ohlcv_inputs")):
            original = getattr(orchestrator, name)
            def publish(*args, _original=original, _kind=kind, **kwargs):
                assert not in_child[0], "acquisition child attempted publication"
                assert kwargs["expected_current_content_id"] is None
                status = json.loads((orchestrator.state_dir / "status-sector-inputs.json").read_text())
                task = next(t for t in status["tasks"] if t["name"] == "sector_inputs")
                assert status["finished_at"] is None
                assert task["native_input_attempt"]["phases"][_kind]["publication_state"] == "invocation_pending"
                events.append(("publish", _kind))
                return _original(*args, **kwargs)
            mp.setattr(orchestrator, name, publish)
        def runner(args, **kwargs):
            assert args[1:3] == ["-m", "scripts.prepare_sector_native_inputs"]
            assert orchestrator._native_lock_fd in kwargs["pass_fds"]
            phase = args[args.index("--phase") + 1]
            events.append(("prepare", phase))
            in_child[0] = True
            try:
                result = prepare.main(args[3:])
            finally:
                in_child[0] = False
            shutil.copytree(Path(args[args.index("--stage") + 1]), retained / phase)
            return subprocess.CompletedProcess(args, result, "prepared", "")
        orchestrator.runner = runner
        result = orchestrator.sector_inputs(allow_bootstrap=True)
    assert result.status == "ok", result.detail
    request_meta = json.loads((retained / "capture" / prepare.METADATA).read_text())
    raw, request = prepare.read_request(retained / "capture", attempt_id=request_meta["attempt_id"], source_revision=REVISION)
    return SimpleNamespace(root=root, repository=repository, orchestrator=orchestrator, generations=generations,
        stages=retained, request=request, raw=raw, result=result, events=events)


def test_actual_native_chain_has_parent_publication_order_and_index_only_observations(native_chain):
    chain = native_chain
    events = chain.events
    assert [row[1] for row in events if row[0] == "publish"] == ["yahoo", "breadth", "member"]
    assert events.index(("publish", "yahoo")) < events.index(("download", "breadth", "4y"))
    assert events.index(("publish", "breadth")) < events.index(("download", "member", "2014-01-01"))
    assert all(prior["content_id"] is None for prior in chain.request["priors"].values())
    yahoo = prepare.yahoo.read_verified_yahoo_cohort(generations_root=chain.generations, now=CLOCK, require_current=True)
    breadth = prepare.broad.read_verified_breadth_member_inputs(generations_root=chain.generations,
        yahoo=yahoo, now=CLOCK, require_current=True)
    member = prepare.candles.read_verified_member_ohlcv_inputs(generations_root=chain.generations,
        yahoo=yahoo, breadth=breadth, now=CLOCK, require_current=True)
    close, volume, facts = breadth.inputs.member_index_inputs([{"ticker": "INDEXONLY"}])
    assert close["INDEXONLY"].dropna().index[-1].date().isoformat() == SOURCE
    assert volume is None and facts["volume_unavailable"] == ["INDEXONLY"]
    assert "INDEXONLY" not in member.inputs.receipt["acquisition"]["requested"]
    assert all(phase.get("publication", {}).get("status") == "published"
        for kind, phase in chain.result.native_input_attempt["phases"].items() if kind != "capture")
    assert not list(chain.orchestrator.state_dir.glob(".sector-inputs-*"))
    public = (chain.orchestrator.live_dir / "orchestrator_status.json").read_text()
    assert "native_input_attempt" not in public and "generation_id" not in public and "fingerprint" not in public


def test_current_same_request_reuses_chain_without_provider_or_publication(native_chain, monkeypatch):
    chain = native_chain
    monkeypatch.setattr(owner, "ROOT", chain.repository)
    monkeypatch.setattr(ticker_aliases, "YAHOO_FETCH_ALIASES", {})
    def forbidden(*args, **kwargs):
        pytest.fail("current native chain reacquired or republished")
    for obj, name in ((YahooAdapter, "_download"), (BreadthAdapter, "_download_adjusted_capture"),
                      (fetch_basket_extras, "_download_closes"), (fetch_basket_ohlcv, "_download_ohlcv")):
        monkeypatch.setattr(obj, name, forbidden)
    orchestrator = _orch(chain.root)
    for name in ("publish_yahoo_inputs", "publish_breadth_member_inputs", "publish_member_ohlcv_inputs"):
        monkeypatch.setattr(orchestrator, name, forbidden)
    orchestrator.runner = lambda args, **kwargs: subprocess.CompletedProcess(args, prepare.main(args[3:]), "", "")
    result = orchestrator.sector_inputs()
    assert result.status == "ok", result.detail
    assert result.native_input_attempt["current_chain"] == chain.result.native_input_attempt["current_chain"]
    assert all(result.native_input_attempt["phases"][kind]["publication_state"] == "reused" for kind in prepare.KINDS)


@pytest.mark.parametrize("damage", ["empty", "windows", "bool", "lookback", "fixups"])
def test_bad_breadth_policy_refuses_request_capture_before_provider(sources, tmp_path, monkeypatch, damage):
    cfg = _inputs(tmp_path / "inputs", sources)
    if damage == "empty": cfg["breadth"] = {}
    elif damage == "windows": cfg["breadth"]["ma_windows"] = [200]
    elif damage == "bool": cfg["breadth"]["nhnl_window"] = True
    elif damage == "lookback": cfg["breadth"]["lookback_days_live"] = 0
    else: cfg["breadth"]["ticker_fixups"] = {"OLD": 2}
    (tmp_path / "inputs/config.yml").write_text(yaml.safe_dump(cfg))
    stage = owner._private_dir(tmp_path / "request")
    generations = owner._private_dir(tmp_path / "generations")
    monkeypatch.setattr(YahooAdapter, "_download", lambda *a, **kw: pytest.fail("bad policy reached provider"))
    with pytest.raises(ValueError, match="invalid_breadth_policy"):
        prepare.capture_request(repository_root=tmp_path / "inputs", generations_root=generations,
            source_revision=REVISION, attempt_id="bad-policy", allow_bootstrap=True, stage=stage, clock=lambda: CLOCK)
    assert not list(stage.iterdir())


def test_optional_null_sector_dtype_preserves_incumbent_membership_contract(sources):
    members = sources["groups"]["breadth"].members.copy()
    members["sector"] = None
    buffer = BytesIO()
    table = pa.Table.from_pandas(members, preserve_index=False)
    assert pa.types.is_null(table.schema.field("sector").type)
    pq.write_table(table, buffer)
    actual = prepare._constituents(buffer.getvalue(), "breadth")
    assert actual["sector"].isna().all() and len(actual) == len(members)


def test_semantically_valid_second_request_cannot_be_wrapped_as_original(native_chain, sources, tmp_path, monkeypatch):
    chain = native_chain
    repository = tmp_path / "other-inputs"
    _inputs(repository, sources)
    path = repository / "data/baskets/membership.json"
    document = json.loads(path.read_text())
    document["baskets"]["test_theme"]["name"] = "A different actual request"
    path.write_text(json.dumps(document))
    stage = owner._private_dir(tmp_path / "other-request")
    empty = owner._private_dir(tmp_path / "empty-generations")
    _providers(monkeypatch, sources)
    request_b = prepare.capture_request(repository_root=repository, generations_root=empty,
        source_revision=REVISION, attempt_id="other-request", allow_bootstrap=True, stage=stage, clock=lambda: CLOCK)
    candidate = owner._private_dir(tmp_path / "other-breadth")
    deps = {"yahoo": chain.result.native_input_attempt["current_chain"]["yahoo"]}
    metadata = prepare.prepare_phase(kind="breadth", request_stage=stage, stage=candidate,
        generations_root=chain.generations, attempt_id=request_b["attempt_id"], source_revision=REVISION,
        dependencies=deps, clock=lambda: CLOCK)
    raw_b, request_b = prepare.read_request(stage, attempt_id="other-request", source_revision=REVISION)
    valid, _, _ = prepare.read_prepared(candidate, kind="breadth", request=request_b, request_members=raw_b,
        generations_root=chain.generations, dependencies=deps, clock=lambda: CLOCK)
    receipt = json.loads(valid.members["acquisition.json"])
    prepare.broad.validate_breadth_member_bundle(member_bytes=valid.members, input_identity=valid.input_identity,
        yahoo=valid.yahoo, published_at=CLOCK, now=CLOCK, source_revision=REVISION,
        computed_at=receipt["prepared_at"], require_current=True)
    metadata.update(generation_id=chain.request["attempt_id"] + "-breadth", request_fingerprint=chain.request["fingerprint"])
    (candidate / prepare.METADATA).write_bytes(owner._canonical_json(metadata))
    with pytest.raises(ValueError, match="native_candidate_request_binding_mismatch"):
        prepare.read_prepared(candidate, kind="breadth", request=chain.request, request_members=chain.raw,
            generations_root=chain.generations, dependencies=deps, clock=lambda: CLOCK)


def _prepared_yahoo_runner(chain, orchestrator, *, fail_phase=None):
    def run(args, **kwargs):
        phase = args[args.index("--phase") + 1]
        if phase == fail_phase:
            raise subprocess.TimeoutExpired(args, kwargs["timeout"])
        if phase == "capture":
            return subprocess.CompletedProcess(args, prepare.main(args[3:]), "", "")
        assert phase == "yahoo"
        stage = Path(args[args.index("--stage") + 1])
        shutil.copytree(chain.stages / "yahoo", stage, dirs_exist_ok=True)
        metadata = json.loads((stage / prepare.METADATA).read_text())
        metadata["generation_id"] = args[args.index("--attempt-id") + 1] + "-yahoo"
        (stage / prepare.METADATA).write_bytes(owner._canonical_json(metadata))
        return subprocess.CompletedProcess(args, 0, "", "")
    return run


@pytest.mark.parametrize("outcome", ["uncertain", "durability", "raises", "rejected", "checkpoint"])
def test_native_publication_boundary_does_not_repeat_effect(native_chain, tmp_path, monkeypatch, outcome):
    chain = native_chain
    monkeypatch.setattr(owner, "ROOT", chain.repository)
    monkeypatch.setattr(ticker_aliases, "YAHOO_FETCH_ALIASES", {})
    orchestrator = _orch(tmp_path)
    orchestrator.runner = _prepared_yahoo_runner(chain, orchestrator)
    calls = []
    def publisher(*args, **kwargs):
        calls.append(kwargs)
        if outcome == "raises": raise OSError("after invocation")
        return owner.GenerationPublishResult(status="uncertain" if outcome == "uncertain" else
            "rejected" if outcome == "rejected" else "published", generation_id=kwargs["generation_id"],
            durability="unconfirmed" if outcome == "durability" else "not_applicable")
    monkeypatch.setattr(orchestrator, "publish_yahoo_inputs", publisher)
    if outcome == "checkpoint":
        original = owner.atomic_write_json
        def fail_intent(path, payload, **kwargs):
            attempt = next(task for task in payload["tasks"] if task["name"] == "sector_inputs")["native_input_attempt"]
            if attempt["phases"].get("yahoo", {}).get("publication_state") == "invocation_pending":
                raise OSError("receipt storage unavailable before invocation")
            return original(path, payload, **kwargs)
        monkeypatch.setattr(owner, "atomic_write_json", fail_intent)
    result = orchestrator.sector_inputs(allow_bootstrap=True)
    assert len(calls) == (0 if outcome == "checkpoint" else 1), result.detail
    assert result.status == ("failed" if outcome == "rejected" else
                            "receipt_unconfirmed" if outcome == "checkpoint" else "publication_unconfirmed"), result.detail
    if outcome in {"uncertain", "durability", "raises"}:
        before = (orchestrator.state_dir / "status-sector-inputs.json").read_bytes()
        resumed = _orch(tmp_path, runner=lambda *a, **kw: pytest.fail("uncertain publication reacquired"))
        assert resumed.sector_inputs(allow_bootstrap=True).status == "publication_unconfirmed"
        assert (orchestrator.state_dir / "status-sector-inputs.json").read_bytes() == before


@pytest.mark.parametrize("phase", ["capture", "yahoo", "breadth"])
def test_only_actual_cold_acquisition_timeout_is_sticky(native_chain, tmp_path, monkeypatch, phase):
    monkeypatch.setattr(owner, "ROOT", native_chain.repository)
    monkeypatch.setattr(ticker_aliases, "YAHOO_FETCH_ALIASES", {})
    orchestrator = _orch(tmp_path)
    orchestrator.runner = _prepared_yahoo_runner(native_chain, orchestrator, fail_phase=phase)
    result = orchestrator.sector_inputs(allow_bootstrap=True)
    assert result.status == "timeout", result.detail
    attempt = result.native_input_attempt
    assert (attempt["cold_timeout"] is not None) == (phase != "capture")
    if phase == "breadth":
        assert attempt["phases"]["yahoo"]["publication"]["status"] == "published"
        assert (orchestrator.state_dir / "generations" / prepare.yahoo.YAHOO_GENERATION_DOMAIN / "current.json").exists()
    if phase != "capture":
        resumed = _orch(tmp_path, runner=lambda *a, **kw: pytest.fail("cold timeout repeated"))
        assert resumed.sector_inputs(allow_bootstrap=True).status == "cold_timeout_held"


def test_remaining_budget_and_busy_native_lock_do_not_start_work(tmp_path, monkeypatch):
    orchestrator = _orch(tmp_path, deadline_monotonic=time.monotonic() + 20,
        runner=lambda *a, **kw: pytest.fail("unadmitted child launched"))
    assert orchestrator.sector_inputs().status == "budget_exhausted"
    orchestrator._command_deadline = time.monotonic() + 800
    held = owner._lock_lane(orchestrator.state_dir, "sector-inputs")
    try:
        assert orchestrator.sector_inputs(allow_bootstrap=True).status == "deferred"
    finally:
        held.close()


@pytest.mark.parametrize("bar_status", ["ok", "failed"])
def test_bars_obligations_precede_native_remainder_without_restart(tmp_path, monkeypatch, bar_status):
    tick, calls = [10.0], []
    monkeypatch.setattr(owner.time, "monotonic", lambda: tick[0])
    monkeypatch.setattr(owner, "intraday_flow_symbols", lambda path: ["SPY"])
    orchestrator = _orch(tmp_path, deadline_monotonic=850)
    def module(name, *args, **kwargs):
        calls.append((name, kwargs["timeout"]))
        tick[0] += 500 if name == "intraday_bars" else 90
        result = owner.TaskResult(name, bar_status if name == "intraday_bars" else "ok", 0)
        orchestrator.results.append(result)
        return result
    def native(**kwargs):
        calls.append(("native", orchestrator._command_deadline - time.monotonic()))
        assert kwargs == {"allow_bootstrap": False}
    monkeypatch.setattr(orchestrator, "module", module)
    monkeypatch.setattr(orchestrator, "sector_inputs", native)
    orchestrator.bars()
    assert calls == ([('intraday_bars', 720), ('intraday_flow', 180), ('native', 250)] if bar_status == "ok" else
                     [('intraday_bars', 720), ('native', 340)])
    assert orchestrator._command_deadline == 850


def test_native_lock_descriptor_reaches_actual_child(tmp_path):
    orchestrator = _orch(tmp_path, deadline_monotonic=time.monotonic() + 60)
    held = owner._lock_lane(orchestrator.state_dir, "sector-inputs")
    orchestrator._native_lock_fd = held.fileno()
    script = "import os,sys,fcntl\nfd=int(sys.argv[1]);os.fstat(fd)\nf=open(sys.argv[2],'a+')\ntry:\n fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)\nexcept BlockingIOError:\n sys.exit(0)\nsys.exit(3)\n"
    try:
        result = orchestrator.command("native-lock-proof", [str(orchestrator.python), "-c", script,
            str(held.fileno()), str(orchestrator.state_dir / "sector-inputs.lock")], timeout=10)
        assert result.status == "ok", result.detail
    finally:
        held.close()


def test_timeout_fact_survives_unconfirmed_process_cleanup(monkeypatch, tmp_path):
    class Child:
        pid = 987654
        def communicate(self, **kwargs):
            raise subprocess.TimeoutExpired(["fixture"], kwargs["timeout"])
    monkeypatch.setattr(owner.subprocess, "Popen", lambda *a, **kw: Child())
    def unresolved(process):
        raise owner.ProcessGroupCleanupUnconfirmed(process.pid)
    monkeypatch.setattr(owner, "_stop_command_group", unresolved)
    orchestrator = _orch(tmp_path, deadline_monotonic=time.monotonic() + 60)
    result = orchestrator.command("cold-provider", ["fixture"], timeout=10)
    assert result.status == "cleanup_unconfirmed" and result.timed_out is True
    assert result.cleanup_group_id == Child.pid


def test_cold_timeout_remains_held_after_original_group_disappears(native_chain, tmp_path, monkeypatch):
    monkeypatch.setattr(owner, "ROOT", native_chain.repository)
    monkeypatch.setattr(ticker_aliases, "YAHOO_FETCH_ALIASES", {})
    orchestrator = _orch(tmp_path)
    capture_runner = _prepared_yahoo_runner(native_chain, orchestrator)
    def runner(args, **kwargs):
        if args[args.index("--phase") + 1] == "yahoo":
            raise owner.ProcessGroupCleanupUnconfirmed(987654, timed_out=True)
        return capture_runner(args, **kwargs)
    orchestrator.runner = runner
    result = orchestrator.sector_inputs(allow_bootstrap=True)
    assert result.status == "cleanup_unconfirmed", result.detail
    assert result.native_input_attempt["cold_timeout"]["phase"] == "yahoo"
    assert Path(result.native_input_attempt["stage"]).is_dir()
    monkeypatch.setattr(owner, "_process_group_exists", lambda group: False)
    resumed = _orch(tmp_path, runner=lambda *a, **kw: pytest.fail("cold work repeated after group disappearance"))
    assert resumed.sector_inputs(allow_bootstrap=True).status == "cold_timeout_held"


def test_snapshot_cap_and_bars_cap_remain_distinct(tmp_path, monkeypatch):
    monkeypatch.setattr(owner.time, "monotonic", lambda: 100)
    assert _orch(tmp_path, deadline_monotonic=1100)._command_deadline == 980
    snapshot = owner.Orchestrator(live_dir=tmp_path / "live", state_dir=tmp_path / "state",
        data_dir=tmp_path / "data", deadline_monotonic=1100)
    assert snapshot._command_deadline == 500


@pytest.mark.parametrize("lane,budget", [("snapshot", 400), ("bars", 880), ("sector-inputs", 880)])
def test_source_owner_deadline_includes_lock_wait_without_new_service(lane, budget, monkeypatch):
    from tests.test_deploy_live_source_barrier import module
    source = module()
    tick, executed = [0.0], []
    monkeypatch.setattr(source.os, "geteuid", lambda: source.ROOT_UID)
    monkeypatch.setattr(source, "owner_identity", lambda *a, **kw: "fixture-owner")
    monkeypatch.setattr(source, "open_lock", lambda: 8)
    monkeypatch.setattr(source, "verify_lock", lambda fd: None)
    monkeypatch.setattr(source, "read_pending", lambda *a: None)
    monkeypatch.setattr(source, "git", lambda *a, **kw: REVISION)
    monkeypatch.setattr(source.os, "close", lambda *a: None)
    monkeypatch.setattr(source.os, "set_inheritable", lambda *a: None)
    monkeypatch.setattr(source.os, "chdir", lambda *a: None)
    def execute(*args):
        executed.append(args[1])
        raise RuntimeError("fixture-exec")
    monkeypatch.setattr(source.os, "execv", execute)
    def flock(*args):
        if tick[0] < 50:
            tick[0] = 50
            raise BlockingIOError
    monkeypatch.setattr(source.fcntl, "flock", flock)
    monkeypatch.setattr(source.time, "monotonic", lambda: tick[0])
    monkeypatch.setattr(source.time, "sleep", lambda *a: None)
    with pytest.raises(RuntimeError, match="fixture-exec"):
        source.main(["fixture-descriptor", "run", lane])
    command = executed[0]
    assert float(command[command.index("--deadline-monotonic") + 1]) == budget
    assert command[command.index("--source-lock-fd") + 1] == "8"
    assert source.LANES == ("fast", "snapshot", "bars") and len(source.UNITS) == 6
