"""tests/test_topup_thetadata_legacy.py — AD-1T1 §G/§H characterization suite.

(F17) The legacy `scripts/topup_thetadata_day.py --roots [--date]` contract was
UNTESTED before AD-1T1 (zero repo tests referenced the topup writer). This
suite pins the exit-code triple, `_merge_day` date-replacement semantics, and
`_last_weekday_before` BEFORE trusting any of the new `--daily`/`@universe`/
writer-exclusion code added alongside it (spec
`research/AD1T1_INCREMENTAL_CADENCE_SPEC_2026-08-22.md` §G/§H).

Also covers: the additive flock (refusal -> existing exit-1 shape, §B/§G),
the F9 tmp-file rename, and `--roots @universe` (F10) compatibility.
"""
from __future__ import annotations

import json
from datetime import date

import pandas as pd
import pytest

import scripts.topup_thetadata_day as topup


# ── fixtures ─────────────────────────────────────────────────────────────────
def _df(day: date, n: int = 2, **extra_cols) -> pd.DataFrame:
    data = {"date": [pd.Timestamp(day)] * n, "strike": list(range(n))}
    data.update({k: [v] * n for k, v in extra_cols.items()})
    return pd.DataFrame(data)


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame({"date": pd.Series([], dtype="datetime64[ns]"),
                         "strike": pd.Series([], dtype="float64")})


class FakeTd:
    """Fake `collectors.thetadata` surface for the legacy 3-tier pull."""

    def __init__(self, plan: dict[tuple[str, str], object] | None = None,
                reachable: bool = True):
        self.plan = plan or {}
        self._reachable = reachable
        self.calls: list[tuple] = []

    def reachable(self) -> bool:
        return self._reachable

    def _get(self, tier: str, root: str, day: date):
        self.calls.append((tier, root, day))
        key = (tier, root)
        if key in self.plan:
            v = self.plan[key]
            if callable(v):
                return v(day)
            return v
        return _df(day)

    def bulk_eod(self, root, exp, start, end):
        return self._get("eod", root, start)

    def bulk_open_interest(self, root, exp, start, end):
        return self._get("oi", root, start)

    def bulk_greeks(self, root, exp, start, end, order=3):
        return self._get("greeks", root, start)


@pytest.fixture()
def store(tmp_path):
    return tmp_path / "thetadata_eod"


def _install_fake_td(monkeypatch, fake):
    import collectors.thetadata as real_td
    monkeypatch.setattr(real_td, "reachable", fake.reachable)
    monkeypatch.setattr(real_td, "bulk_eod", fake.bulk_eod)
    monkeypatch.setattr(real_td, "bulk_open_interest", fake.bulk_open_interest)
    monkeypatch.setattr(real_td, "bulk_greeks", fake.bulk_greeks)


# ── _last_weekday_before ─────────────────────────────────────────────────────
def test_last_weekday_before_monday_returns_friday():
    assert topup._last_weekday_before(date(2026, 8, 24)) == date(2026, 8, 21)


def test_last_weekday_before_tuesday_returns_monday():
    assert topup._last_weekday_before(date(2026, 8, 19)) == date(2026, 8, 18)


def test_last_weekday_before_sunday_returns_friday():
    assert topup._last_weekday_before(date(2026, 8, 23)) == date(2026, 8, 21)


# ── _merge_day date-replacement semantics ────────────────────────────────────
def test_merge_day_appends_to_empty_store(tmp_path):
    store = tmp_path / "s"
    day = date(2026, 7, 30)
    n = topup._merge_day(store, "eod", "SPY", day, _df(day, n=3))
    assert n == 3
    out = pd.read_parquet(store / "eod" / "SPY" / "2026.parquet")
    assert len(out) == 3


def test_merge_day_replaces_only_the_target_date_exact(tmp_path):
    """The merge REPLACES rows for the target date and byte-preserves every
    other date in the same year parquet (§H writer: unrelated dates
    byte-preserved after a merge)."""
    store = tmp_path / "s"
    d1, d2 = date(2026, 7, 29), date(2026, 7, 30)
    topup._merge_day(store, "eod", "SPY", d1, _df(d1, n=2, tag="first"))
    topup._merge_day(store, "eod", "SPY", d2, _df(d2, n=2, tag="first"))
    # Re-merge d2 with DIFFERENT rows — d1 must be untouched.
    topup._merge_day(store, "eod", "SPY", d2, _df(d2, n=5, tag="second"))
    out = pd.read_parquet(store / "eod" / "SPY" / "2026.parquet")
    d1_rows = out[pd.to_datetime(out["date"]) == pd.Timestamp(d1)]
    d2_rows = out[pd.to_datetime(out["date"]) == pd.Timestamp(d2)]
    assert len(d1_rows) == 2
    assert (d1_rows["tag"] == "first").all()
    assert len(d2_rows) == 5
    assert (d2_rows["tag"] == "second").all()


def test_merge_day_empty_fresh_frame_is_a_noop(tmp_path):
    store = tmp_path / "s"
    day = date(2026, 7, 30)
    n = topup._merge_day(store, "eod", "SPY", day, _empty_df())
    assert n == 0
    assert not (store / "eod" / "SPY" / "2026.parquet").exists()


def test_merge_day_writes_to_the_fresh_row_year_not_the_call_year(tmp_path):
    """A Dec-session row lands in the SESSION's year parquet even if merged
    from a caller that thinks of `day` differently — §A4 year-boundary rule."""
    store = tmp_path / "s"
    day = date(2025, 12, 31)
    topup._merge_day(store, "eod", "SPY", day, _df(day))
    assert (store / "eod" / "SPY" / "2025.parquet").exists()
    assert not (store / "eod" / "SPY" / "2026.parquet").exists()


# ── F9: tmp file naming ──────────────────────────────────────────────────────
def test_write_atomic_tmp_suffix_does_not_match_the_parquet_glob(tmp_path):
    """(F9) `{YYYY}.parquet.tmp` must NOT match `*.parquet` — the shape the
    store readers glob on (`engine/thetadata_store.py`, `Path.glob`)."""
    dest = tmp_path / "eod" / "SPY" / "2026.parquet"
    tmp = topup._tmp_path(dest)
    assert tmp.name == "2026.parquet.tmp"
    assert not tmp.match("*.parquet")


def test_merge_day_leaves_no_tmp_file_behind(tmp_path):
    store = tmp_path / "s"
    day = date(2026, 7, 30)
    topup._merge_day(store, "eod", "SPY", day, _df(day))
    leftovers = list((store / "eod" / "SPY").glob("*.tmp"))
    assert leftovers == []


# ── _has_day ─────────────────────────────────────────────────────────────────
def test_has_day_false_when_file_absent(tmp_path):
    assert topup._has_day(tmp_path / "s", "eod", "SPY", date(2026, 7, 30)) is False


def test_has_day_true_after_merge(tmp_path):
    store = tmp_path / "s"
    day = date(2026, 7, 30)
    topup._merge_day(store, "eod", "SPY", day, _df(day))
    assert topup._has_day(store, "eod", "SPY", day) is True


def test_has_day_false_on_corrupt_parquet(tmp_path):
    store = tmp_path / "s"
    d = store / "eod" / "SPY"
    d.mkdir(parents=True)
    (d / "2026.parquet").write_bytes(b"not a parquet file")
    assert topup._has_day(store, "eod", "SPY", date(2026, 7, 30)) is False


# ── legacy exit-code triple (characterization, F17) ─────────────────────────
def test_legacy_exit_0_when_all_roots_complete(store, monkeypatch):
    monkeypatch.setattr(topup, "resolve_thetadata_store", lambda **kw: str(store))
    monkeypatch.setattr(topup, "_backfill_running", lambda: False)
    fake = FakeTd()
    _install_fake_td(monkeypatch, fake)
    rc = topup.main(["--roots", "SPY,QQQ", "--date", "2026-07-30"])
    assert rc == 0
    assert topup._has_day(store, "eod", "SPY", date(2026, 7, 30))
    assert topup._has_day(store, "greeks", "QQQ", date(2026, 7, 30))


def test_legacy_exit_2_when_all_roots_vendor_empty(store, monkeypatch):
    monkeypatch.setattr(topup, "resolve_thetadata_store", lambda **kw: str(store))
    monkeypatch.setattr(topup, "_backfill_running", lambda: False)
    fake = FakeTd(plan={
        ("eod", "SPY"): _empty_df(), ("oi", "SPY"): _empty_df(), ("greeks", "SPY"): _empty_df(),
    })
    _install_fake_td(monkeypatch, fake)
    rc = topup.main(["--roots", "SPY", "--date", "2026-07-30"])
    assert rc == 2


def test_legacy_exit_1_when_partial(store, monkeypatch):
    monkeypatch.setattr(topup, "resolve_thetadata_store", lambda **kw: str(store))
    monkeypatch.setattr(topup, "_backfill_running", lambda: False)
    fake = FakeTd(plan={("eod", "SPY"): _empty_df()})
    _install_fake_td(monkeypatch, fake)
    rc = topup.main(["--roots", "SPY", "--date", "2026-07-30"])
    assert rc == 1
    # oi/greeks did merge even though eod was empty for this root.
    assert topup._has_day(store, "oi", "SPY", date(2026, 7, 30))
    assert not topup._has_day(store, "eod", "SPY", date(2026, 7, 30))


def test_legacy_default_date_is_last_weekday_before_today(store, monkeypatch):
    monkeypatch.setattr(topup, "resolve_thetadata_store", lambda **kw: str(store))
    monkeypatch.setattr(topup, "_backfill_running", lambda: False)
    fake = FakeTd()
    _install_fake_td(monkeypatch, fake)
    topup.main(["--roots", "SPY"])
    expected = topup._last_weekday_before(date.today())
    assert any(day == expected for _, _, day in fake.calls)


def test_legacy_backfill_running_refuses_exit_1(store, monkeypatch):
    monkeypatch.setattr(topup, "resolve_thetadata_store", lambda **kw: str(store))
    monkeypatch.setattr(topup, "_backfill_running", lambda: True)
    fake = FakeTd()
    _install_fake_td(monkeypatch, fake)
    rc = topup.main(["--roots", "SPY", "--date", "2026-07-30"])
    assert rc == 1
    assert fake.calls == []


def test_legacy_terminal_unreachable_exit_2(store, monkeypatch):
    monkeypatch.setattr(topup, "resolve_thetadata_store", lambda **kw: str(store))
    monkeypatch.setattr(topup, "_backfill_running", lambda: False)
    fake = FakeTd(reachable=False)
    _install_fake_td(monkeypatch, fake)
    rc = topup.main(["--roots", "SPY", "--date", "2026-07-30"])
    assert rc == 2


def test_legacy_store_resolution_failure_exit_1(monkeypatch):
    def _boom(**kw):
        raise RuntimeError("no store")
    monkeypatch.setattr(topup, "resolve_thetadata_store", _boom)
    monkeypatch.setattr(topup, "_backfill_running", lambda: False)
    rc = topup.main(["--roots", "SPY", "--date", "2026-07-30"])
    assert rc == 1


def test_legacy_already_present_makes_zero_vendor_calls(store, monkeypatch):
    monkeypatch.setattr(topup, "resolve_thetadata_store", lambda **kw: str(store))
    monkeypatch.setattr(topup, "_backfill_running", lambda: False)
    day = date(2026, 7, 30)
    for tier in topup.TIERS:
        topup._merge_day(store, tier, "SPY", day, _df(day))
    fake = FakeTd()
    _install_fake_td(monkeypatch, fake)
    rc = topup.main(["--roots", "SPY", "--date", "2026-07-30"])
    assert rc == 0
    assert fake.calls == []


# ── writer-lock refusal keeps the legacy exit-1 shape (§B/§G additive) ──────
def test_legacy_lock_refusal_exits_1_and_mutates_nothing(store, monkeypatch, capsys):
    monkeypatch.setattr(topup, "resolve_thetadata_store", lambda **kw: str(store))
    monkeypatch.setattr(topup, "_backfill_running", lambda: False)
    fake = FakeTd()
    _install_fake_td(monkeypatch, fake)
    store.mkdir(parents=True)
    with topup._writer_lock(store) as acquired:
        assert acquired is True
        rc = topup.main(["--roots", "SPY", "--date", "2026-07-30"])
    assert rc == 1
    assert fake.calls == []
    assert not (store / "eod" / "SPY").exists()
    out = capsys.readouterr().out
    assert json.loads(out.strip().splitlines()[-1]) == {"event": "writer_locked", "mode": "legacy"}


# ── @universe catch-up mode (F10) ───────────────────────────────────────────
def test_roots_at_universe_resolves_via_resolve_universe(store, monkeypatch):
    calls = {"n": 0}

    def _fake_resolve_universe():
        calls["n"] += 1
        return ["SPY", "QQQ", "AAPL"]

    monkeypatch.setattr(topup, "resolve_thetadata_store", lambda **kw: str(store))
    monkeypatch.setattr(topup, "_backfill_running", lambda: False)
    monkeypatch.setattr("scripts.backfill_thetadata_eod._resolve_universe",
                        _fake_resolve_universe)
    fake = FakeTd()
    _install_fake_td(monkeypatch, fake)
    rc = topup.main(["--roots", "@universe", "--date", "2026-07-30"])
    assert rc == 0
    assert calls["n"] == 1
    pulled_roots = {root for _, root, _ in fake.calls}
    assert pulled_roots == {"SPY", "QQQ", "AAPL"}


def test_roots_at_universe_same_exit_code_triple_as_legacy(store, monkeypatch):
    monkeypatch.setattr(topup, "resolve_thetadata_store", lambda **kw: str(store))
    monkeypatch.setattr(topup, "_backfill_running", lambda: False)
    monkeypatch.setattr("scripts.backfill_thetadata_eod._resolve_universe",
                        lambda: ["SPY"])
    fake = FakeTd(reachable=False)
    _install_fake_td(monkeypatch, fake)
    rc = topup.main(["--roots", "@universe", "--date", "2026-07-30"])
    assert rc == 2


# ── CLI validation ───────────────────────────────────────────────────────────
def test_daily_and_roots_are_mutually_exclusive():
    with pytest.raises(SystemExit):
        topup.main(["--daily", "--roots", "SPY"])


def test_roots_required_unless_daily():
    with pytest.raises(SystemExit):
        topup.main([])


def test_workers_above_hard_cap_rejected():
    with pytest.raises(SystemExit):
        topup.main(["--daily", "--workers", "7"])


@pytest.fixture
def bounded_eod_case(tmp_path, monkeypatch):
    """Real incumbent CSV/parser/normalizer with only requests transport replaced."""
    import io
    from types import SimpleNamespace
    from collectors import thetadata as td
    root_store = tmp_path / 'store'
    root_store.mkdir()
    parent = tmp_path / 'captures'
    parent.mkdir()
    scope = dict(start=date(2020, 10, 19), end=date(2020, 10, 22),
        original_root='01a156f1-f450-7793-8951-bddadd4784c2',
        assigning_parent='01a15700-1ae2-7a73-9756-f1546da7ace8',
        max_response_bytes=16384, max_total_bytes=65536,
        max_response_rows=100, max_total_rows=400)
    calls, statuses, bodies = [], {}, {}
    for root in topup._EOD_CATCHUP_ROOTS:
        bodies[root] = ('symbol,expiration,strike,right,last_trade,close,volume\n' + ''.join(
            f'{root},2020-11-20,100,CALL,2020-10-{day}T16:00:00,2,3\n'
            for day in range(19, 23))).encode()
        topup._merge_day(root_store, 'eod', root, date(2020, 10, 16), _df(date(2020, 10, 16)))
    class Session:
        def get_adapter(self, url):
            return SimpleNamespace(max_retries=SimpleNamespace(total=0))
        def get(self, url, **kwargs):
            root = kwargs['params']['symbol']
            # Exact original operation reservation must precede actual GET.
            receipt = json.loads((parent/'operation'/'receipt.json').read_text())
            assert receipt['requests'][-1]['state'] == 'REQUEST_STARTED'
            assert receipt['attempts'] == len(calls)+1
            calls.append((url, kwargs))
            response = SimpleNamespace(status_code=statuses.get(root, 200), close=lambda: None)
            response.iter_content = lambda **kw: iter([bodies[root]])
            return response
    monkeypatch.setattr(td, '_session', Session)
    monkeypatch.setattr(td, 'reachable', lambda: pytest.fail('Hidden health probe'))
    monkeypatch.setattr(td, '_concurrent_windows', lambda *a, **kw: pytest.fail('Hidden retry/windows'))
    original_read = pd.read_csv
    def read_csv(stream, *args, **kwargs):
        if isinstance(stream, io.BytesIO):
            data = stream.getvalue()
            assert any((parent/'operation'/f'{r}.csv').exists() and
                (parent/'operation'/f'{r}.csv').read_bytes()==data for r in bodies)
        return original_read(stream, *args, **kwargs)
    monkeypatch.setattr(pd, 'read_csv', read_csv)
    return SimpleNamespace(store=root_store, directory=parent/'operation', scope=scope,
        calls=calls, statuses=statuses, bodies=bodies, td=td)


def test_bounded_eod_retains_before_parse_and_merges_only_separately(bounded_eod_case):
    c = bounded_eod_case
    record = topup.capture_bounded_eod_catchup(c.store, c.directory, **c.scope)
    assert record['state']=='CAPTURED' and record['attempts']==4 and record['raw_rows']==16
    assert record['store_writes']==0
    assert len(c.calls)==4 and all(call[1]['allow_redirects'] is False for call in c.calls)
    for root in topup._EOD_CATCHUP_ROOTS:
        assert not topup._has_day(c.store, 'eod', root, c.scope['start'])
    merged = topup.merge_bounded_eod_capture(c.store, c.directory)
    assert merged['state']=='MERGED' and merged['store_writes']==16 and len(c.calls)==4
    for root in topup._EOD_CATCHUP_ROOTS:
        assert topup._has_day(c.store, 'eod', root, date(2020, 10, 16))
        for day in range(19,23):
            assert topup._has_day(c.store, 'eod', root, date(2020, 10, day))
    with pytest.raises(ValueError):
        topup.merge_bounded_eod_capture(c.store, c.directory)
    with pytest.raises(ValueError):
        topup.capture_bounded_eod_catchup(c.store, c.directory, **c.scope)
    assert len(c.calls)==4


@pytest.mark.parametrize('kind', ['refusal', 'wrong_root', 'wrong_date', 'malformed'])
def test_bounded_eod_stops_first_bad_source_and_never_writes(bounded_eod_case, kind):
    c = bounded_eod_case
    if kind=='refusal':c.statuses['GLD']=472
    elif kind=='wrong_root':c.bodies['GLD']=c.bodies['GLD'].replace(b'GLD,',b'SPY,')
    elif kind=='wrong_date':c.bodies['GLD']=c.bodies['GLD'].replace(b'2020-10-19',b'2020-10-16')
    else:c.bodies['GLD']=b'not a contract CSV\n'
    with pytest.raises(ValueError):
        topup.capture_bounded_eod_catchup(c.store,c.directory,**c.scope)
    record=json.loads((c.directory/'receipt.json').read_text())
    assert len(c.calls)==1 and record['state']=='STOPPED' and record['store_writes']==0
    assert record['requests'][0]['state']==('REFUSED' if kind=='refusal' else 'RAW_CAPTURED')
    assert not topup._has_day(c.store,'eod','GLD',c.scope['start'])


@pytest.mark.parametrize('field,value', [('max_total_bytes',300),('max_total_rows',5),
    ('max_response_bytes',10),('max_response_rows',1)])
def test_bounded_eod_individual_and_aggregate_caps_stop_chain(bounded_eod_case,field,value):
    c=bounded_eod_case;c.scope[field]=value
    with pytest.raises(ValueError):topup.capture_bounded_eod_catchup(c.store,c.directory,**c.scope)
    record=json.loads((c.directory/'receipt.json').read_text())
    assert record['state'] in ('STOPPED','EFFECT_UNKNOWN') and len(c.calls)<=2
    assert record['store_writes']==0


def test_bounded_eod_abrupt_attempt_stays_unknown_no_replay(bounded_eod_case,monkeypatch):
    c=bounded_eod_case
    class Abrupt:
        def get_adapter(self,url):
            from types import SimpleNamespace
            return SimpleNamespace(max_retries=SimpleNamespace(total=0))
        def get(self,*args,**kwargs):
            record=json.loads((c.directory/'receipt.json').read_text())
            assert record['attempts']==1 and record['requests'][0]['state']=='REQUEST_STARTED'
            raise KeyboardInterrupt('simulated missing return')
    monkeypatch.setattr(c.td,'_session',Abrupt)
    with pytest.raises(KeyboardInterrupt):topup.capture_bounded_eod_catchup(c.store,c.directory,**c.scope)
    record=json.loads((c.directory/'receipt.json').read_text())
    assert record['state']==record['requests'][0]['state']=='EFFECT_UNKNOWN'
    with pytest.raises(FileExistsError):topup.capture_bounded_eod_catchup(c.store,c.directory,**c.scope)


def test_bounded_eod_claim_durability_failure_precedes_get(bounded_eod_case,monkeypatch):
    c=bounded_eod_case
    def fail(path):raise OSError('directory fsync failure')
    monkeypatch.setattr(topup,'_eod_sync_directory',fail)
    with pytest.raises(OSError):topup.capture_bounded_eod_catchup(c.store,c.directory,**c.scope)
    assert not c.calls and c.directory.exists()


@pytest.mark.parametrize('failure',['lock','existing_day'])
def test_bounded_eod_refuses_before_claim_on_store_conflict(bounded_eod_case,failure):
    c=bounded_eod_case
    if failure=='existing_day':
        topup._merge_day(c.store,'eod','GLD',c.scope['start'],_df(c.scope['start']))
        with pytest.raises(ValueError):topup.capture_bounded_eod_catchup(c.store,c.directory,**c.scope)
    else:
        with topup._writer_lock(c.store) as held:
            assert held
            with pytest.raises(RuntimeError):topup.capture_bounded_eod_catchup(c.store,c.directory,**c.scope)
    assert not c.calls and not c.directory.exists()


def test_bounded_eod_interrupted_merge_preserves_nonretryable_state(bounded_eod_case,monkeypatch):
    c=bounded_eod_case;topup.capture_bounded_eod_catchup(c.store,c.directory,**c.scope)
    original=topup._merge_day;n=[]
    def fail_after_one(*args):
        n.append(1)
        if len(n)>1:raise OSError('simulated store failure')
        return original(*args)
    monkeypatch.setattr(topup,'_merge_day',fail_after_one)
    with pytest.raises(OSError):topup.merge_bounded_eod_capture(c.store,c.directory)
    assert json.loads((c.directory/'receipt.json').read_text())['state']=='MERGE_STARTED'
    with pytest.raises(ValueError):topup.merge_bounded_eod_capture(c.store,c.directory)
    assert len(n)==2 and len(c.calls)==4


@pytest.mark.parametrize('mutation',['digest','future','root','scope','bytes'])
def test_bounded_eod_merge_refuses_tampered_receipt(bounded_eod_case,mutation):
    c=bounded_eod_case;topup.capture_bounded_eod_catchup(c.store,c.directory,**c.scope)
    p=c.directory/'receipt.json';record=json.loads(p.read_text());first=record['requests'][0]
    if mutation=='digest':first['response_sha256']='0'*64
    elif mutation=='future':first['received_at']='2099-01-01T00:00:00Z'
    elif mutation=='root':first['parameters']['symbol']='SPY'
    elif mutation=='scope':record['end']='2020-10-23'
    else:record['response_bytes']+=1
    p.write_text(json.dumps(record))
    with pytest.raises(ValueError):topup.merge_bounded_eod_capture(c.store,c.directory)
    assert not topup._has_day(c.store,'eod','GLD',c.scope['start'])


@pytest.mark.parametrize('stage',['capture','merge'])
def test_bounded_eod_preserves_unreconciled_canonical_temporary_file(bounded_eod_case,stage):
    c=bounded_eod_case
    if stage=='merge':topup.capture_bounded_eod_catchup(c.store,c.directory,**c.scope)
    temporary=topup._tmp_path(c.store/'eod'/'GLD'/'2020.parquet')
    temporary.write_bytes(b'original unknown store effect')
    with pytest.raises(ValueError,match='Unreconciled'):
        if stage=='merge':topup.merge_bounded_eod_capture(c.store,c.directory)
        else:topup.capture_bounded_eod_catchup(c.store,c.directory,**c.scope)
    assert temporary.read_bytes()==b'original unknown store effect'
    assert len(c.calls)==(4 if stage=='merge' else 0)


@pytest.mark.parametrize('field,value',[('collector_sha256','0'*64),('store_ref','/some/other/store')])
def test_bounded_eod_refuses_different_collector_or_store(bounded_eod_case,field,value):
    c=bounded_eod_case;topup.capture_bounded_eod_catchup(c.store,c.directory,**c.scope)
    path=c.directory/'receipt.json';record=json.loads(path.read_text());record[field]=value
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError):topup.merge_bounded_eod_capture(c.store,c.directory)
    assert not topup._has_day(c.store,'eod','GLD',c.scope['start'])


def test_bounded_eod_merge_rechecks_claim_under_writer_lock(bounded_eod_case, monkeypatch):
    from contextlib import contextmanager
    c = bounded_eod_case
    topup.capture_bounded_eod_catchup(c.store, c.directory, **c.scope)
    receipt = c.directory / 'receipt.json'
    original_lock = topup._writer_lock
    @contextmanager
    def competing_merge(store):
        # Another admitted caller started and failed before writing any day.
        record = json.loads(receipt.read_text())
        record['state'] = 'MERGE_STARTED'
        receipt.write_text(json.dumps(record))
        with original_lock(store) as acquired:
            yield acquired
    monkeypatch.setattr(topup, '_writer_lock', competing_merge)
    with pytest.raises(ValueError, match='receipt changed'):
        topup.merge_bounded_eod_capture(c.store, c.directory)
    assert json.loads(receipt.read_text())['state'] == 'MERGE_STARTED'
    assert not topup._has_day(c.store, 'eod', 'GLD', c.scope['start'])
    assert len(c.calls) == 4


@pytest.mark.parametrize('clock', ['created_only', 'missing_last_trade', 'conflicting_date'])
def test_bounded_eod_requires_raw_source_session_clock(bounded_eod_case, clock):
    c = bounded_eod_case
    if clock == 'created_only':
        c.bodies['GLD'] = c.bodies['GLD'].replace(b'last_trade', b'created')
    elif clock == 'missing_last_trade':
        lines = c.bodies['GLD'].decode().splitlines()
        c.bodies['GLD'] = ('\n'.join(','.join(line.split(',')[:4] + line.split(',')[5:])
            for line in lines) + '\n').encode()
    else:
        # _date formerly hid source observations outside the requested window.
        c.bodies['GLD'] = c.bodies['GLD'].replace(b'last_trade,', b'last_trade,_date,')
        for day in range(19, 23):
            c.bodies['GLD'] = c.bodies['GLD'].replace(
                f'2020-10-{day}T16:00:00,'.encode(),
                f'2020-10-16T16:00:00,2020-10-{day},'.encode())
    with pytest.raises(ValueError, match='source'):
        topup.capture_bounded_eod_catchup(c.store, c.directory, **c.scope)
    record = json.loads((c.directory / 'receipt.json').read_text())
    assert record['state'] == 'STOPPED' and record['requests'][0]['state'] == 'RAW_CAPTURED'
    assert (c.directory / 'GLD.csv').read_bytes() == c.bodies['GLD']
    assert record['store_writes'] == 0 and len(c.calls) == 1


@pytest.mark.parametrize('failure', ['file', 'directory'])
def test_bounded_eod_durability_failure_keeps_merge_started(bounded_eod_case, monkeypatch, failure):
    import os
    c = bounded_eod_case
    topup.capture_bounded_eod_catchup(c.store, c.directory, **c.scope)
    dest = c.store / 'eod' / 'GLD' / '2020.parquet'
    real_fsync = os.fsync
    real_directory_sync = topup._eod_sync_directory
    def fail_file(fd):
        if failure == 'file' and os.fstat(fd).st_ino == dest.stat().st_ino:
            raise OSError('canonical file fsync failed')
        return real_fsync(fd)
    def fail_directory(path):
        if failure == 'directory' and path == dest.parent:
            raise OSError('canonical directory fsync failed')
        return real_directory_sync(path)
    monkeypatch.setattr(os, 'fsync', fail_file)
    monkeypatch.setattr(topup, '_eod_sync_directory', fail_directory)
    with pytest.raises(OSError, match='canonical'):
        topup.merge_bounded_eod_capture(c.store, c.directory)
    record = json.loads((c.directory / 'receipt.json').read_text())
    assert record['state'] == 'MERGE_STARTED' and record['store_writes'] == 0
    # Bytes may already exist; no receipt is allowed to claim durable completion.
    assert topup._has_day(c.store, 'eod', 'GLD', c.scope['start'])
    with pytest.raises(ValueError):
        topup.merge_bounded_eod_capture(c.store, c.directory)
    assert len(c.calls) == 4
