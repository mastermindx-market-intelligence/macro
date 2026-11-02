"""Private current-night delivery: real archive lineage plus finite failure paths."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

import pytest

import collectors.tiingo_archive as archive_module
from scripts import boats_history_bridge as bridge_module
from scripts import refresh_boats_live_history as live

NOW = datetime(2026, 10, 20, 2, 1, tzinfo=timezone.utc)


def interest(symbol="AMD", at=NOW, session="2026-10-20"):
    return {"schema": bridge_module.INTEREST_SCHEMA, "symbol": symbol,
            "session_date": session, "requested_at_utc": at.isoformat()}


@pytest.fixture
def lake(tmp_path, monkeypatch):
    monkeypatch.setattr(archive_module, "EXTERNAL_MOUNT", tmp_path)
    monkeypatch.setattr(archive_module, "utc_now", lambda: NOW.isoformat())
    return archive_module.Archive(tmp_path / "lake", check_mount=False, free_floor=0)


def snapshot(lake, *, rows=None, symbol="AMD"):
    if rows is None:
        rows = [{"date": "2026-10-20T02:00:00Z", "open": 10, "high": 12,
                 "low": 9, "close": 11, "volume": 13}]
    return live.capture_snapshot(symbol, "2026-10-20", lake, "fixture-key",
                fetch=lambda *_a, **_kw: (json.dumps(rows).encode(), "application/json"),
                check_mount=False)[0]


@pytest.fixture
def private_root(tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    (root / "requests").mkdir(mode=0o700)
    (root / "bars").mkdir(mode=0o700)
    return root


def test_real_pipeline_and_empty_response_keep_original_receipts(lake):
    full = snapshot(lake)
    assert full["history"]["bars"] == [[1792461600, 10., 12., 9., 11., 13.]]
    assert full["captured_at_utc"] == full["history"]["receipts"][0]["observed_at_utc"]
    assert len(full["history"]["receipts"]) == 1
    empty = snapshot(lake, rows=[])
    assert empty["history"]["bars"] == []
    assert empty["history"]["bar_receipt_ids"] == []
    assert empty["history"]["receipts"][0]["receipt_id"] != full["history"]["receipts"][0]["receipt_id"]
    assert len(list((lake.root / "receipts" / "boats-bars").rglob("*.json"))) == 2


def test_live_capture_requests_latest_session_without_calendar_date_filter(lake):
    from urllib.parse import parse_qs, urlsplit
    calls = []
    def fetch(route, key, **kwargs):
        calls.append((route, kwargs))
        return (json.dumps([{"date": "2026-10-20T00:01:00Z", "open": 10,
            "high": 12, "low": 9, "close": 11, "volume": 13}]).encode(), "application/json")
    result, _ = live.capture_snapshot("AMD", "2026-10-20", lake, "fixture-key",
                                     fetch=fetch, check_mount=False)
    assert len(calls) == 1
    url = urlsplit(calls[0][0])
    assert url.path == "/boats/AMD/prices"
    assert parse_qs(url.query) == {"resampleFreq": ["1min"],
        "columns": ["open,high,low,close,volume"], "forceFill": ["false"]}
    assert calls[0][1]["max_bytes"] == live.MAX_RESPONSE
    assert result["session_date"] == "2026-10-20"
    assert len(result["history"]["bars"]) == 1


@pytest.mark.parametrize("date", ["2026-10-19T02:00:00Z", "2026-10-20T02:02:00Z", "2026-10-20T08:00:00Z"])
def test_wrong_session_future_and_closed_bars_refuse(lake, date):
    with pytest.raises((archive_module.TiingoArchiveError, live.SymbolDataInvalid, ValueError)):
        snapshot(lake, rows=[{"date": date, "open": 10, "high": 12, "low": 9, "close": 11, "volume": 13}])


@pytest.mark.parametrize("query", [
    "resampleFreq=1min",
    "resampleFreq=1min&startDate=2026-10-20&endDate=2026-10-20",
])
def test_bridge_accepts_latest_and_retained_dated_receipts(lake, private_root, query):
    for rows in [None, []]:
        doc = snapshot(lake, rows=rows)
        doc["history"]["receipts"][0]["request_path"] = f"/boats/AMD/prices?{query}"
        assert bridge_module.validate_snapshot(doc)[0] == "AMD"


@pytest.mark.parametrize("query", [
    "startDate=2026-10-20", "endDate=2026-10-20", "startDate=&endDate=",
    "startDate=2026-10-19&endDate=2026-10-20",
    "startDate=2026-10-20&startDate=2026-10-20&endDate=2026-10-20",
])
def test_bridge_refuses_partial_blank_wrong_or_duplicate_dates(lake, private_root, query):
    doc = snapshot(lake, rows=[])
    doc["history"]["receipts"][0]["request_path"] = f"/boats/AMD/prices?resampleFreq=1min&{query}"
    with pytest.raises(ValueError, match="receipt does not bind"):
        bridge_module.exchange(private_root, {"operation": "publish", "snapshot": doc})
    assert list((private_root / "bars").iterdir()) == []


def test_private_bridge_reads_only_bounded_regular_interest(private_root, tmp_path):
    target = private_root / "requests" / "AMD.json"
    target.write_text(json.dumps(interest()))
    assert bridge_module.exchange(private_root, {"operation": "read"})["interests"] == [interest()]
    target.unlink()
    other = tmp_path / "other.json"
    other.write_text(json.dumps(interest()))
    target.symlink_to(other)
    result = bridge_module.exchange(private_root, {"operation": "read"})
    assert result["interests"] == [] and result["rejected"] == 1


def test_bridge_atomic_replace_refuses_older_and_conflicting_vintage(lake, private_root):
    first = snapshot(lake)
    receipt = bridge_module.exchange(private_root, {"operation": "publish", "snapshot": first})
    target = private_root / "bars" / "AMD.json"
    assert receipt["sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert target.stat().st_mode & 0o777 == 0o600
    assert bridge_module.exchange(private_root, {"operation": "publish", "snapshot": first})["status"] == "unchanged"
    conflict = json.loads(json.dumps(first))
    conflict["history"]["bars"][0][4] = 10
    with pytest.raises(ValueError, match="same-vintage"):
        bridge_module.exchange(private_root, {"operation": "publish", "snapshot": conflict})
    older = json.loads(json.dumps(first))
    older["captured_at_utc"] = older["history"]["receipts"][0]["observed_at_utc"] = "2026-10-20T02:00:30Z"
    assert bridge_module.exchange(private_root, {"operation": "publish", "snapshot": older})["status"] == "newer_retained"
    assert json.loads(target.read_text()) == first


class Clock:
    def __init__(self, now=NOW):
        self.start, self.elapsed = now, 0.
    def now(self):
        return self.start + timedelta(seconds=self.elapsed)
    def monotonic(self):
        return self.elapsed
    def sleep(self, seconds):
        self.elapsed += seconds


def setup_run(tmp_path, lake, symbols="AMD\nNVDA\nHELD\n", **kw):
    coverage, held = tmp_path / "coverage.txt", tmp_path / "held.txt"
    coverage.write_text(symbols)
    held.write_text("HELD\n")
    return live.Config(lake.root, coverage, held, capture=True, max_seconds=120, **kw)


def run_test(cfg, lake, bridge, *, clock=None, capture=None):
    clock = clock or Clock()
    return live.run(cfg, bridge, now=clock.now, monotonic=clock.monotonic,
                    sleep=clock.sleep, archive_factory=lambda _root: lake,
                    key_reader=lambda: "fixture-key", capture=capture or (lambda sym, *_a: (snapshot(lake, symbol=sym), 100)))


def test_run_coalesces_filters_and_respects_per_symbol_interval(tmp_path, lake, private_root):
    cfg = setup_run(tmp_path, lake)
    rows = [interest(), interest(), interest("HELD"), interest("UNKNOWN"),
            interest("NVDA", at=NOW - timedelta(minutes=3))]
    def bridge(req):
        if req["operation"] == "read": return {"interests": rows}
        return bridge_module.exchange(private_root, req)
    result = run_test(cfg, lake, bridge)
    assert result["requests"] == result["delivered"] == 2
    assert result["reason"] == "seconds_budget"
    assert len(list((lake.root / "run-receipts").glob("*start*"))) == 1
    with pytest.raises(FileExistsError):
        run_test(cfg, lake, bridge)


def test_404_holds_symbol_and_other_symbol_continues(tmp_path, lake, private_root):
    cfg = setup_run(tmp_path, lake)
    called = []
    def capture(sym, *_a):
        called.append(sym)
        if sym == "AMD": raise archive_module.TiingoArchiveError("Tiingo HTTP 404; source not admitted")
        return snapshot(lake, symbol=sym), 100
    def bridge(req):
        return {"interests": [interest("AMD"), interest("NVDA")]} if req["operation"] == "read" else bridge_module.exchange(private_root, req)
    result = run_test(cfg, lake, bridge, capture=capture)
    assert called == ["AMD", "NVDA", "NVDA"]
    assert result["held"] == ["AMD"]
    assert (lake.root / "run-receipts/boats-live-history-held/AMD.json").exists()


@pytest.mark.parametrize("failure", [archive_module.TiingoArchiveError("Tiingo HTTP 403; source not admitted"), OSError("disk full")])
def test_capture_failure_stops_without_publish_or_retry(tmp_path, lake, failure):
    cfg = setup_run(tmp_path, lake)
    calls = []
    def capture(*_a):
        raise failure
    def bridge(req):
        calls.append(req["operation"])
        return {"interests": [interest(), interest("NVDA")]}
    with pytest.raises(type(failure)):
        run_test(cfg, lake, bridge, capture=capture)
    assert calls == ["read"]
    result = json.loads((lake.root / "run-receipts/boats-live-history-final-2026-10-20.json").read_text())
    assert result["reason"] == "stopped" and result["requests"] == 1


def test_unknown_delivery_retains_snapshot_and_blocks_replay(tmp_path, lake):
    cfg = setup_run(tmp_path, lake)
    def bridge(req):
        if req["operation"] == "read": return {"interests": [interest()]}
        raise live.DeliveryUnknown("timed out")
    with pytest.raises(live.DeliveryUnknown):
        run_test(cfg, lake, bridge)
    assert list((lake.root / "run-receipts/boats-live-history-2026-10-20").glob("*-snapshot.json"))
    result = json.loads((lake.root / "run-receipts/boats-live-history-final-2026-10-20.json").read_text())
    assert result["reason"] == "effect_unknown"
    with pytest.raises(FileExistsError):
        run_test(cfg, lake, bridge)


def test_closed_venue_never_opens_archive_or_bridge(tmp_path, lake):
    cfg = setup_run(tmp_path, lake)
    with pytest.raises(live.RefreshStopped, match="outside"):
        run_test(cfg, lake, lambda *_a: pytest.fail("bridge called"), clock=Clock(NOW.replace(hour=9)))
    assert not (lake.root / "run-receipts").exists()


def test_request_budget_stops_exactly(tmp_path, lake, private_root):
    cfg = setup_run(tmp_path, lake, max_requests=1)
    def bridge(req):
        return {"interests": [interest(), interest("NVDA")]} if req["operation"] == "read" else bridge_module.exchange(private_root, req)
    result = run_test(cfg, lake, bridge)
    assert result["requests"] == 1 and result["reason"] == "capture_budget"


def test_wrong_delivery_hash_is_an_unknown_effect(tmp_path, lake):
    cfg = setup_run(tmp_path, lake)
    def bridge(req):
        return {"interests": [interest()]} if req["operation"] == "read" else {"status": "published", "symbol": "AMD", "sha256": "a" * 64}
    with pytest.raises(live.DeliveryUnknown):
        run_test(cfg, lake, bridge)
    result = json.loads((lake.root / "run-receipts/boats-live-history-final-2026-10-20.json").read_text())
    assert result["reason"] == "effect_unknown" and result["delivered"] == 0


def test_04_boundary_stops_without_a_following_request(tmp_path, lake, private_root):
    cfg = setup_run(tmp_path, lake)
    clock = Clock(NOW.replace(hour=7, minute=59, second=40))
    def bridge(req):
        return {"interests": [interest(at=clock.now())]} if req["operation"] == "read" else bridge_module.exchange(private_root, req)
    result = run_test(cfg, lake, bridge, clock=clock)
    assert result["requests"] == 1 and result["reason"] == "window_closed"


def test_clock_jump_stops_and_retains_final_receipt(tmp_path, lake):
    cfg = setup_run(tmp_path, lake)
    clock = Clock()
    def bridge(_req):
        clock.start += timedelta(seconds=10)
        return {"interests": [interest()]}
    with pytest.raises(live.RefreshStopped, match="clock"):
        run_test(cfg, lake, bridge, clock=clock)
    result = json.loads((lake.root / "run-receipts/boats-live-history-final-2026-10-20.json").read_text())
    assert result["reason"] == "stopped" and result["requests"] == 0


def test_byte_reservation_refuses_before_provider_attempt(tmp_path, lake):
    cfg = setup_run(tmp_path, lake, max_bytes=live.MAX_RESPONSE - 1)
    result = run_test(cfg, lake, lambda _req: pytest.fail("bridge called"))
    assert result["reason"] == "capture_budget" and result["requests"] == 0


def test_cycle_cap_keeps_the_rest_of_the_demand_for_next_cycle(tmp_path, lake, private_root):
    symbols = [f"Z{i:03d}" for i in range(30)]
    cfg = setup_run(tmp_path, lake, symbols="\n".join(symbols))
    called = []
    def capture(sym, *_a):
        called.append(sym)
        return snapshot(lake, symbol=sym), 100
    def bridge(req):
        return {"interests": [interest(s) for s in symbols]} if req["operation"] == "read" else bridge_module.exchange(private_root, req)
    result = run_test(cfg, lake, bridge, capture=capture)
    assert result["requests"] == 48
    assert called[:24] == symbols[:24]
    assert called[24:30] == symbols[24:]


def test_key_failure_before_any_effect_does_not_claim_session(tmp_path, lake):
    cfg = setup_run(tmp_path, lake)
    def no_key(): raise OSError("fixture key unavailable")
    with pytest.raises(OSError):
        live.run(cfg, lambda _req: pytest.fail("bridge called"), now=lambda: NOW,
                 archive_factory=lambda _root: lake, key_reader=no_key)
    assert not (lake.root / "run-receipts/boats-live-history-start-2026-10-20.json").exists()
    assert not (lake.root / "run-receipts/boats-live-history-final-2026-10-20.json").exists()


def test_bridge_capacity_and_snapshot_bound(private_root):
    for i in range(257):
        sym = f"Z{i:03d}"
        (private_root / "requests" / f"{sym}.json").write_text(json.dumps(interest(sym)))
    result = bridge_module.exchange(private_root, {"operation": "read"})
    assert len(result["interests"]) == 256 and result["truncated"] is True


def test_empty_held_file_and_persistent_hold_count(tmp_path, lake, private_root):
    cfg = setup_run(tmp_path, lake)
    cfg.held.write_text('')
    area = lake.root/'run-receipts'
    area.mkdir(mode=0o700)
    holds = area/'boats-live-history-held'
    holds.mkdir(mode=0o700)
    live.write_once(holds/'AMD.json', {'symbol':'AMD', 'http_status':404})
    result = run_test(cfg, lake, lambda req: {'interests':[]})
    assert result['eligible_symbols'] == 2 and result['requests'] == 0


@pytest.mark.parametrize("orphan", [".receipt-interrupted", ".receipt-linked"])
def test_interrupted_hold_temporary_does_not_block_later_session(tmp_path, lake, orphan):
    cfg = setup_run(tmp_path, lake)
    area = lake.root / "run-receipts"
    area.mkdir(mode=0o700)
    holds = area / "boats-live-history-held"
    holds.mkdir(mode=0o700)
    temporary = holds / orphan
    temporary.write_bytes(b'{"symbol":"AMD","http_status":404}\n')
    if orphan == ".receipt-linked":
        live.os.link(temporary, holds / "AMD.json")
    result = run_test(cfg, lake, lambda request: {"interests": []})
    assert result["requests"] == 0
    assert result["eligible_symbols"] == (1 if orphan == ".receipt-linked" else 2)
    assert temporary.read_bytes() == b'{"symbol":"AMD","http_status":404}\n'


def test_non_temporary_invalid_hold_still_refuses_before_start(tmp_path, lake):
    cfg = setup_run(tmp_path, lake)
    holds = lake.root / "run-receipts" / "boats-live-history-held"
    holds.parent.mkdir(mode=0o700)
    holds.mkdir(mode=0o700)
    (holds / "invalid-name").write_text("{}")
    with pytest.raises(live.RefreshStopped, match="invalid persistent hold identity"):
        run_test(cfg, lake, lambda request: {"interests": []})
    assert not (holds.parent / "boats-live-history-start-2026-10-20.json").exists()


def test_invalid_interest_does_not_hide_valid_demand(private_root):
    (private_root/'requests'/'BAD.json').write_text('{')
    (private_root/'requests'/'AMD.json').write_text(json.dumps(interest()))
    result = bridge_module.exchange(private_root, {'operation':'read'})
    assert result['interests'] == [interest()] and result['rejected'] == 1


def test_semantically_unchanged_snapshot_ack_binds_input(lake, private_root):
    doc = snapshot(lake)
    target = private_root/'bars'/'AMD.json'
    target.write_text(json.dumps(doc, sort_keys=True, indent=2))
    old = target.read_bytes()
    ack = bridge_module.exchange(private_root, {'operation':'publish','snapshot':doc})
    expected = (json.dumps(doc, separators=(',',':'))+'\n').encode()
    assert ack['status'] == 'unchanged' and ack['sha256'] == hashlib.sha256(expected).hexdigest()
    assert ack['stored_sha256'] == hashlib.sha256(old).hexdigest()
    assert target.read_bytes() == old


def test_newer_retained_is_not_counted_as_delivery(tmp_path, lake):
    cfg = setup_run(tmp_path, lake)
    def bridge(req):
        return {'interests':[interest()]} if req['operation']=='read' else {
            'symbol':'AMD','status':'newer_retained','sha256':'a'*64}
    result = run_test(cfg,lake,bridge)
    assert result['newer_retained'] == 1 and result['requests'] == 1 and result['delivered'] == 0


def test_invalid_symbol_data_is_metered_and_held_after_raw_storage(tmp_path, lake, private_root):
    cfg = setup_run(tmp_path,lake)
    bad = [{'date':'2026-10-20T02:00:00Z','open':10,'high':9,'low':8,'close':11,'volume':13}]
    raw = json.dumps(bad).encode()
    calls=[]
    def capture(symbol,*args):
        calls.append(symbol)
        if symbol=='AMD':
            return live.capture_snapshot(symbol,'2026-10-20',lake,'fixture',
                fetch=lambda *a,**k:(raw,'application/json'),check_mount=False)
        return snapshot(lake,symbol=symbol),100
    def bridge(req):
        return {'interests':[interest(),interest('NVDA')]} if req['operation']=='read' else bridge_module.exchange(private_root,req)
    result=run_test(cfg,lake,bridge,capture=capture)
    assert calls == ['AMD','NVDA','NVDA'] and result['raw_bytes'] == len(raw)+200
    assert result['held']==['AMD'] and result['delivered']==2
    invalid=list((lake.root/'run-receipts'/'boats-live-history-2026-10-20').glob('*-invalid.json'))
    assert len(invalid)==1 and json.loads(invalid[0].read_text())['retry_authorized'] is False
    assert len(list((lake.root/'receipts'/'boats-bars').rglob('*.json')))==2


def test_immutable_receipt_never_replaces_and_failed_publish_leaves_no_final(tmp_path,monkeypatch):
    path=tmp_path/'receipt.json'
    live.write_once(path,{'first':1})
    with pytest.raises(FileExistsError):live.write_once(path,{'second':2})
    assert json.loads(path.read_text())=={'first':1}
    monkeypatch.setattr(live.os,'link',lambda *a,**k:(_ for _ in ()).throw(OSError('fixture link failure')))
    with pytest.raises(OSError):live.write_once(tmp_path/'new.json',{'x':1})
    assert not (tmp_path/'new.json').exists()


@pytest.mark.parametrize('failure',['timeout','nonzero','oversized','malformed','unversioned','signal','nan','infinity'])
def test_ssh_bridge_publication_failure_is_unknown_without_retry(tmp_path,monkeypatch,failure):
    calls=[]
    def execute(*a,**k):
        calls.append(a)
        if failure=='timeout':raise live.subprocess.TimeoutExpired(a[0],45)
        if failure=='signal':raise live.RefreshStopped('signal 15')
        from types import SimpleNamespace
        raw={'oversized':b'x'*(256*1024+1),'malformed':b'{','unversioned':b'{}',
             'nan':json.dumps({'protocol':bridge_module.PROTOCOL,'value':float('nan')}).encode(),
             'infinity':json.dumps({'protocol':bridge_module.PROTOCOL,'value':float('inf')}).encode()}.get(failure,b'{}')
        return SimpleNamespace(returncode=1 if failure=='nonzero' else 0,stdout=raw)
    monkeypatch.setattr(live.subprocess,'run',execute)
    bridge=live.SSHBridge('root@example.test',tmp_path/'key','/private/bridge.py','/private/live')
    with pytest.raises(live.DeliveryUnknown):bridge({'operation':'publish','snapshot':{}})
    assert len(calls)==1
    with pytest.raises(live.RefreshStopped):bridge({'operation':'read'})
    assert len(calls)==2


def test_bad_ack_is_saved_before_unknown_result(tmp_path,lake):
    cfg=setup_run(tmp_path,lake)
    def bridge(req):return {'interests':[interest()]} if req['operation']=='read' else {'status':'bad'}
    with pytest.raises(live.DeliveryUnknown):run_test(cfg,lake,bridge)
    files=list((lake.root/'run-receipts'/'boats-live-history-2026-10-20').glob('*-delivery.json'))
    assert len(files)==1 and json.loads(files[0].read_text())=={'status':'bad'}


@pytest.mark.parametrize("change", [
    lambda d: d["history"]["bars"][0].__setitem__(2, 1),
    lambda d: d["history"]["bars"][0].__setitem__(5, -1),
    lambda d: d["history"]["bars"][0].__setitem__(0, 1792461601),
    lambda d: d["history"]["bar_receipt_ids"][0].__setitem__(0, "a"*64),
    lambda d: d["history"].__setitem__("complete", True),
    lambda d: d["history"]["receipts"][0].__setitem__("request_path", "/boats/AMD/prices?resampleFreq=1min&startDate=2026-10-20"),
])
def test_bridge_validates_full_snapshot_before_mutation(lake, private_root, change):
    doc = snapshot(lake)
    change(doc)
    with pytest.raises(ValueError):
        bridge_module.exchange(private_root, {"operation":"publish", "snapshot":doc})
    assert not (private_root/"bars"/"AMD.json").exists()


@pytest.mark.parametrize("day,offset,due_hour", [("2026-10-18",-7,17),("2026-11-01",-7,18),("2026-11-01",-8,17)])
def test_live_history_schedule_uses_market_open_without_provider_or_archive_on_unused_candidate(tmp_path, lake, day, offset, due_hour):
    import dataclasses, plistlib
    job = plistlib.loads((Path(__file__).resolve().parents[1]/"ops/launchd/com.macro.boats-live-history.plist").read_bytes())
    assert job["StartCalendarInterval"] == [{"Weekday":d,"Hour":h,"Minute":0} for d in range(5) for h in (17,18)]
    assert job["RunAtLoad"] is False and job["KeepAlive"] is False and "StartInterval" not in job
    assert "--scheduled" in job["ProgramArguments"]
    cfg = dataclasses.replace(setup_run(tmp_path,lake), scheduled=True)
    unused = 18 if due_hour == 17 else 17
    now = datetime.fromisoformat(day).replace(hour=unused,tzinfo=timezone(timedelta(hours=offset)))
    result=live.run(cfg,lambda r:pytest.fail("unused candidate reached SSH"),now=lambda:now,
        archive_factory=lambda root:pytest.fail("unused candidate reached archive"))
    assert result["reason"] == "scheduled_candidate_not_due" and result["requests"] == 0
