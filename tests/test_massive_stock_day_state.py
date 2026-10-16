"""Gap-aware resume state (v2) for collectors/massive_stock_day.

Regression suite for the 2026-07-03 coverage-gap incident: the v1 scalar
`last_captured_date` state was advanced past a 110-day hole by a smoke test, so a
resumed backfill skipped 2026-03-13→2026-06-30 forever while the manifest claimed
freshness.  These tests pin the v2 semantics: `processed_days` is a per-day set,
target selection is a set difference (interior holes are fetched like the leading
edge), confirmed-empty days are recorded, errored days are retried, and a legacy v1
state file is migrated from the actual parquets — never trusted.

All S3 access is stubbed (fetch_aggs/latest_available/enabled monkeypatched); the
store goes to a tmp dir via a patched config.data_dir.
"""
from __future__ import annotations

import json
from datetime import date

import pandas as pd
import pytest

import collectors.massive_stock_day as msd

# Ten consecutive weekdays: Mon 2026-06-01 … Fri 2026-06-12.
DAYS = [date.fromisoformat(s) for s in
        ["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04", "2026-06-05",
         "2026-06-08", "2026-06-09", "2026-06-10", "2026-06-11", "2026-06-12"]]


def _day_frame(d: date) -> pd.DataFrame:
    """A two-ticker whole-market day frame in the raw fetch_aggs schema."""
    return pd.DataFrame({
        "ticker": ["SPY", "AAPL"],
        "open": [500.0, 200.0], "high": [505.0, 202.0],
        "low": [495.0, 198.0], "close": [502.0, 201.0],
        "volume": [1_000_000, 2_000_000], "transactions": [10_000, 20_000],
    })


@pytest.fixture()
def store(tmp_path, monkeypatch):
    """Tmp store + stubbed S3 layer.  Returns a dict the tests mutate to steer the
    fake fetch: holidays (empty frames) and failures (raise)."""
    monkeypatch.setattr(msd.config, "data_dir", lambda: tmp_path)
    # These tests are about resume-state semantics, not the store-absent fence: their
    # synthetic store is two tickers, and the real floor (~100 parquets, sized to tell a
    # restored store from a checkout holding only the committed sidecars) would read a
    # legitimate 2-file store as a throwaway checkout and short-circuit every case.
    # tests/test_massive_stock_day_fence.py owns the fence itself.
    monkeypatch.setattr(msd, "_MIN_STORE_FILES", 1)
    monkeypatch.setattr(msd, "enabled", lambda: True)
    monkeypatch.setattr(msd, "latest_available", lambda *a, **k: DAYS[-1])
    monkeypatch.setattr(msd, "probe_available", lambda *a, **k: type("P", (), {
        "available_date": DAYS[-1], "reason": "available", "detail": "",
    })())
    ctl = {"holidays": set(), "fail": set(), "calls": []}

    def fake_fetch(d, product="stock_day", underlyings=None, use_cache=True):
        ctl["calls"].append(d)
        if d in ctl["fail"]:
            raise OSError("S3 403")
        if d in ctl["holidays"]:
            return pd.DataFrame()
        return _day_frame(d)

    monkeypatch.setattr(msd, "fetch_aggs", fake_fetch)
    return ctl


def _spy_days() -> list[date]:
    df = msd.load_ticker("SPY")
    return sorted(t.date() for t in pd.to_datetime(df.index))


def test_smoke_then_full_backfill_fills_the_middle(store):
    """THE incident regression: a smoke capture at the tip must not make a later
    full backfill skip everything before it."""
    smoke = msd.backfill(start=DAYS[7], end=DAYS[9])
    assert smoke["days_fetched"] == 3
    # v1 would now resume at DAYS[9]+1 and fetch NOTHING; v2 targets the missing 7.
    full = msd.backfill(start=DAYS[0], end=DAYS[9])
    assert full["days_fetched"] == 7
    assert _spy_days() == DAYS


def test_confirmed_empty_day_recorded_and_not_reprobed(store):
    store["holidays"] = {DAYS[2]}
    r = msd.backfill(start=DAYS[0], end=DAYS[4])
    assert r["days_fetched"] == 4 and r["days_skipped"] == 1
    store["calls"].clear()
    r2 = msd.backfill(start=DAYS[0], end=DAYS[4])
    assert store["calls"] == []            # nothing re-probed, holiday included
    assert r2["days_fetched"] == 0


def test_failed_day_not_recorded_and_retried(store):
    store["fail"] = {DAYS[2]}
    r = msd.backfill(start=DAYS[0], end=DAYS[4])
    assert r["days_failed"] == 1 and r["days_remaining"] == 1
    assert DAYS[2] not in msd._processed_days()
    store["fail"].clear()
    r2 = msd.backfill(start=DAYS[0], end=DAYS[4])
    assert r2["days_fetched"] == 1 and r2["days_remaining"] == 0
    assert _spy_days() == DAYS[:5]


def test_max_days_cap_reports_remaining(store):
    r = msd.backfill(start=DAYS[0], end=DAYS[9], max_days=3)
    assert r["days_fetched"] == 3
    assert r["days_remaining"] == 7


def test_incremental_self_heals_interior_hole(store):
    # Seed a store with an interior two-day hole + a missing leading edge.
    for d in [DAYS[0], DAYS[3], DAYS[4]]:
        msd.backfill(start=d, end=d)
    store["calls"].clear()
    r = msd.run_incremental()
    # Window = [min(processed) … latest_available] = DAYS[0]..DAYS[9]:
    # the hole (d1, d2) AND the edge (d5..d9) are both fetched.
    assert r["days_fetched"] == 7
    assert _spy_days() == DAYS


def test_incremental_already_current_short_circuits(store):
    msd.backfill(start=DAYS[0], end=DAYS[9])
    store["calls"].clear()
    r = msd.run_incremental()
    assert r.get("already_current") is True
    assert store["calls"] == []


def test_already_current_refreshes_stale_manifest(store):
    """An already-current run must reconcile the committed manifest with the store on
    disk: an R2 restore can hold days a cancelled run fetched but never committed, and
    publish_r2 would ship the stale anchor beside a larger store (10-11 incident)."""
    msd.backfill(start=DAYS[0], end=DAYS[9])
    n_true = sum(1 for _ in msd.iter_artifact_paths(msd._store_dir()))
    msd._manifest_path().write_text(json.dumps({
        "store": "massive_stock_day",
        "n_tickers": n_true - 6,
        "latest_date": DAYS[4].isoformat(),
        "updated_at": "2026-10-07T00:00:00+00:00",
    }))
    store["calls"].clear()
    r = msd.run_incremental()
    assert r.get("already_current") is True
    assert store["calls"] == []
    mf = json.loads(msd._manifest_path().read_text())
    assert mf["n_tickers"] == sum(1 for _ in msd.iter_artifact_paths(msd._store_dir()))
    assert mf["latest_date"] == max(msd._processed_days()).isoformat()


def test_already_current_leaves_coherent_manifest_bytes_untouched(store):
    """Idempotence: a coherent manifest is NOT rewritten on the already-current path —
    an updated_at-only git diff every quiet nightly would be churn."""
    msd.backfill(start=DAYS[0], end=DAYS[9])
    before = msd._manifest_path().read_bytes()
    store["calls"].clear()
    r = msd.run_incremental()
    assert r.get("already_current") is True
    assert msd._manifest_path().read_bytes() == before


def test_already_current_rewrites_missing_manifest(store):
    """A missing manifest must be rebuilt too — its absence is the worst incoherence:
    publish_r2 has no anchor at all to embed beside the store count."""
    msd.backfill(start=DAYS[0], end=DAYS[9])
    msd._manifest_path().unlink()
    store["calls"].clear()
    r = msd.run_incremental()
    assert r.get("already_current") is True
    mf = json.loads(msd._manifest_path().read_text())
    assert mf["n_tickers"] == sum(1 for _ in msd.iter_artifact_paths(msd._store_dir()))
    assert mf["latest_date"] == max(msd._processed_days()).isoformat()


def test_legacy_v1_state_migrated_from_parquets_not_trusted(store):
    """A v1 state whose scalar claims the tip must be rebuilt from actual content."""
    msd.backfill(start=DAYS[0], end=DAYS[2])
    # Forge the incident: v1-style state claiming the whole window is done.
    msd._backfill_state_path().write_text(
        json.dumps({"last_captured_date": DAYS[9].isoformat()}))
    processed = msd._processed_days()
    assert processed == set(DAYS[:3])       # from parquets, not the scalar's claim
    upgraded = json.loads(msd._backfill_state_path().read_text())
    assert upgraded["version"] == msd.STATE_VERSION
    # And a follow-up backfill fetches the 7 days the v1 scalar would have hidden.
    r = msd.backfill(start=DAYS[0], end=DAYS[9])
    assert r["days_fetched"] == 7


def test_manifest_carries_coverage_and_anchor_truth(store):
    store["holidays"] = {DAYS[1]}
    msd.backfill(start=DAYS[0], end=DAYS[4])
    mf = json.loads(msd._manifest_path().read_text())
    cov = mf["coverage"]
    assert cov["first_day"] == DAYS[0].isoformat()
    assert cov["last_day"] == DAYS[4].isoformat()
    assert cov["n_processed_days"] == 5
    assert cov["max_missing_run_weekdays"] == 0     # holiday was processed, not missing
    anchor = mf["anchor"]
    assert anchor["ticker"] == "SPY"
    assert anchor["n_rows"] == 4                     # 5 days minus the holiday
    assert anchor["last"] == DAYS[4].isoformat()


def test_manifest_reports_interior_missing_run(store):
    # Process the edges only; the middle 6 weekdays were never attempted.
    msd.backfill(start=DAYS[0], end=DAYS[1])
    msd.backfill(start=DAYS[8], end=DAYS[9])
    mf = json.loads(msd._manifest_path().read_text())
    assert mf["coverage"]["max_missing_run_weekdays"] == 6
    assert mf["coverage"]["missing_sample"][0] == DAYS[2].isoformat()



# Operator-only processed-day member repair must NEVER clear the global resume
# state or refetch 20k unaffected members through the normal nightly path.
# These fixtures use a tiny disposable store and a fake Massive S3 response.
def _remove_bar(symbol, day):
    path = msd._ticker_path(symbol)
    rows = pd.read_parquet(path)
    rows.drop(pd.Timestamp(day)).to_parquet(path)


def test_operator_only_missing_processed_member_day_repair(store):
    msd.backfill(start=DAYS[0], end=DAYS[4])
    _remove_bar("AAPL", DAYS[2])
    store["calls"].clear()
    assert DAYS[2] in msd._processed_days()
    # The existing ordinary incremental advances other days but misses this
    # already-processed member hole. Compare source bytes AFTER that ordinary
    # work, so the recovery-only effect check is not contaminated by nightly.
    msd.run_incremental(max_days=None, pace_s=0)
    assert DAYS[2] not in set(msd.load_ticker("AAPL").index.date)
    assert DAYS[2] not in store["calls"]
    original_state = msd._backfill_state_path().read_bytes()
    original_spy = msd._ticker_path("SPY").read_bytes()
    store["calls"].clear()
    output = msd.repair_processed_day_missing_members(DAYS[2], ("AAPL",))
    assert output["status"] == "REPAIRED"
    assert output["repaired"] == ["AAPL"]
    assert DAYS[2] in set(msd.load_ticker("AAPL").index.date)
    assert store["calls"] == [DAYS[2]]
    assert msd._ticker_path("SPY").read_bytes() == original_spy
    assert msd._backfill_state_path().read_bytes() == original_state
    assert msd._manifest_path().exists()


def test_operator_member_repair_does_not_redownload_when_already_present(store):
    msd.backfill(start=DAYS[0], end=DAYS[2])
    store["calls"].clear()
    state_before=msd._backfill_state_path().read_bytes()
    manifest_before=msd._manifest_path().read_bytes()
    output = msd.repair_processed_day_missing_members(DAYS[2], ("AAPL",))
    assert output["status"] == "ALREADY_PRESENT"
    assert store["calls"] == []
    assert msd._backfill_state_path().read_bytes() == state_before
    assert msd._manifest_path().read_bytes() == manifest_before


def test_operator_member_repair_withholds_if_original_vendor_lacks_name(store, monkeypatch):
    msd.backfill(start=DAYS[0], end=DAYS[3])
    _remove_bar("AAPL", DAYS[2])
    before={str(p):p.read_bytes() for p in msd._store_dir().rglob("*") if p.is_file()}
    monkeypatch.setattr(msd, "fetch_aggs",
                        lambda *a, **k: _day_frame(DAYS[2]).query("ticker == 'SPY'"))
    output = msd.repair_processed_day_missing_members(DAYS[2], ("AAPL",))
    assert output["status"] == "REFUSED"
    assert output["reason"] == "SOURCE_MEMBER_MISSING"
    assert before == {str(p):p.read_bytes() for p in msd._store_dir().rglob("*") if p.is_file()}


def test_operator_member_repair_refuses_corrupt_existing_name_before_fetch(store):
    msd.backfill(start=DAYS[0], end=DAYS[3])
    path=msd._ticker_path("AAPL")
    path.write_bytes(b"corrupt-recovered-parquet")
    state=msd._backfill_state_path().read_bytes()
    store["calls"].clear()
    output=msd.repair_processed_day_missing_members(DAYS[2], ("AAPL",))
    assert output["status"] == "REFUSED"
    assert output["reason"] == "SOURCE_MEMBER_UNREADABLE"
    assert path.read_bytes()==b"corrupt-recovered-parquet"
    assert state==msd._backfill_state_path().read_bytes()
    assert store["calls"]==[]


@pytest.mark.parametrize("day,symbols", [
    (DAYS[2], ("../AAPL",)),
    (DAYS[2], ("AAPL", "AAPL")),
    (date(2026, 6, 7), ("AAPL",)),
    (DAYS[2], ()),
])
def test_operator_member_repair_rejects_invalid_request_without_io(store, day, symbols):
    store["calls"].clear()
    with pytest.raises(ValueError):
        msd.repair_processed_day_missing_members(day, symbols)
    assert store["calls"]==[]


def test_operator_member_repair_refuses_unprocessed_day_without_mutation(store):
    msd.backfill(start=DAYS[0], end=DAYS[1])
    state=msd._backfill_state_path().read_bytes()
    store["calls"].clear()
    output=msd.repair_processed_day_missing_members(DAYS[2], ("AAPL",))
    assert output["status"] == "REFUSED"
    assert output["reason"] == "ORIGINAL_DAY_NOT_PROCESSED"
    assert state==msd._backfill_state_path().read_bytes()
    assert store["calls"]==[]



def test_operator_repair_partial_atomic_effect_remains_recoverable(store, monkeypatch):
    """Second file fails: no fake all-or-nothing claim or reset of processed days."""
    import os
    from pathlib import Path
    msd.backfill(start=DAYS[0], end=DAYS[3])
    _remove_bar("AAPL", DAYS[2]); _remove_bar("SPY", DAYS[2])
    previous_state=msd._backfill_state_path().read_bytes()
    previous_manifest=msd._manifest_path().read_bytes()
    original_replace=os.replace
    def fail_second(src, dst):
        if Path(dst).name == "SPY.parquet":
            raise OSError("synthetic second atomic replacement interrupted")
        return original_replace(src, dst)
    with monkeypatch.context() as m:
        m.setattr(os, "replace", fail_second)
        result=msd.repair_processed_day_missing_members(DAYS[2], ("AAPL", "SPY"))
    assert result["status"]=="PARTIAL"
    assert result["reason"]=="REPAIR_LOCAL_EFFECT_UNSETTLED"
    assert result["repaired"]==["AAPL"]
    assert DAYS[2] in set(msd.load_ticker("AAPL").index.date)
    assert DAYS[2] not in set(msd.load_ticker("SPY").index.date)
    assert msd._backfill_state_path().read_bytes()==previous_state
    assert msd._manifest_path().read_bytes()==previous_manifest
    # Same exact original day/target recovery; already-durable AAPL is not replaced.
    already=msd._ticker_path("AAPL").read_bytes()
    recovered=msd.repair_processed_day_missing_members(DAYS[2], ("AAPL", "SPY"))
    assert recovered["status"]=="REPAIRED"
    assert recovered["repaired"]==["SPY"]
    assert msd._ticker_path("AAPL").read_bytes()==already
    assert DAYS[2] in set(msd.load_ticker("SPY").index.date)
    assert msd._backfill_state_path().read_bytes()==previous_state


def test_operator_repair_all_missing_members_preflight_before_any_file_change(
    store, monkeypatch,
):
    msd.backfill(start=DAYS[0], end=DAYS[3])
    _remove_bar("AAPL", DAYS[2]); _remove_bar("SPY", DAYS[2])
    before={str(p):p.read_bytes() for p in msd._store_dir().rglob("*") if p.is_file()}
    monkeypatch.setattr(msd, "fetch_aggs",
                        lambda *a, **k: _day_frame(DAYS[2]).query("ticker == 'AAPL'"))
    outcome=msd.repair_processed_day_missing_members(DAYS[2], ("AAPL", "SPY"))
    assert outcome["status"]=="REFUSED"
    assert outcome["reason"]=="SOURCE_MEMBER_MISSING"
    assert before=={str(p):p.read_bytes() for p in msd._store_dir().rglob("*") if p.is_file()}


def test_operator_repair_invalid_provider_price_refuses_with_no_effect(store, monkeypatch):
    msd.backfill(start=DAYS[0], end=DAYS[3])
    _remove_bar("AAPL", DAYS[2])
    before={str(p):p.read_bytes() for p in msd._store_dir().rglob("*") if p.is_file()}
    def bogus(*args, **kwargs):
        data=_day_frame(DAYS[2])
        data.loc[data["ticker"]=="AAPL","close"]=-10.0
        return data
    monkeypatch.setattr(msd, "fetch_aggs", bogus)
    outcome=msd.repair_processed_day_missing_members(DAYS[2], ("AAPL",))
    assert outcome["status"]=="REFUSED"
    assert outcome["reason"]=="SOURCE_PRICE_INVALID"
    assert before=={str(p):p.read_bytes() for p in msd._store_dir().rglob("*") if p.is_file()}


def test_operator_repair_refuses_without_restored_full_store_before_fetch(store, monkeypatch):
    msd.backfill(start=DAYS[0], end=DAYS[3])
    _remove_bar("AAPL", DAYS[2])
    state=msd._backfill_state_path().read_bytes()
    store["calls"].clear()
    monkeypatch.setattr(msd,"_MIN_STORE_FILES",100)
    outcome=msd.repair_processed_day_missing_members(DAYS[2], ("AAPL",))
    assert outcome["status"]=="REFUSED"
    assert outcome["reason"]=="ORIGINAL_STORE_NOT_RESTORED"
    assert store["calls"]==[]
    assert msd._backfill_state_path().read_bytes()==state


def test_operator_repair_refuses_absent_provider_credentials_before_fetch(store, monkeypatch):
    msd.backfill(start=DAYS[0], end=DAYS[3])
    _remove_bar("AAPL", DAYS[2])
    store["calls"].clear()
    monkeypatch.setattr(msd, "enabled", lambda: False)
    outcome=msd.repair_processed_day_missing_members(DAYS[2], ("AAPL",))
    assert outcome["status"]=="REFUSED"
    assert outcome["reason"]=="ORIGINAL_SOURCE_CREDENTIALS_UNAVAILABLE"
    assert store["calls"]==[]



def test_operator_repair_existing_cli_routes_to_original_repair_api(
    store, monkeypatch, capsys,
):
    import sys
    from scripts import backfill_massive_stock_day as cli
    seen=[]
    def original_repair(day, tickers):
        seen.append((day,tickers))
        return {"status":"REPAIRED","repaired":list(tickers)}
    monkeypatch.setattr(msd,"repair_processed_day_missing_members",original_repair)
    monkeypatch.setattr(sys,"argv",
                        ["script","--repair-day","2026-06-03",
                         "--repair-tickers","AAPL,MSFT"])
    assert cli.main()==0
    assert seen==[(DAYS[2],("AAPL","MSFT"))]
    assert '"REPAIRED"' in capsys.readouterr().out


@pytest.mark.parametrize("bad_args", [
    ["--repair-day","2026-06-03","--repair-tickers","AAPL","--force"],
    ["--repair-day","2026-06-03"],
    ["--repair-tickers","AAPL"],
    ["--repair-day","2026-06-03","--repair-tickers","AAPL","--smoke"],
])
def test_operator_repair_cli_rejects_unsafe_mode_combinations(
    store, monkeypatch, bad_args,
):
    import sys
    from scripts import backfill_massive_stock_day as cli
    seen=[]
    monkeypatch.setattr(msd,"repair_processed_day_missing_members",
                        lambda *a: seen.append(a))
    monkeypatch.setattr(sys,"argv",["script"]+bad_args)
    with pytest.raises(SystemExit):
        cli.main()
    assert seen==[]


def test_operator_repair_cli_reports_refusal_as_failed_exit(store, monkeypatch):
    import sys
    from scripts import backfill_massive_stock_day as cli
    monkeypatch.setattr(msd,"repair_processed_day_missing_members",
                        lambda *a: {"status":"REFUSED","reason":"SOURCE_MEMBER_MISSING"})
    monkeypatch.setattr(sys,"argv",["script","--repair-day","2026-06-03",
                                   "--repair-tickers","AAPL"])
    assert cli.main()==1



def test_operator_repair_refuses_source_mutation_while_fetching(store, monkeypatch):
    """A concurrent source writer invalidates the original CAS; no repair overwrite."""
    msd.backfill(start=DAYS[0], end=DAYS[3])
    _remove_bar("AAPL", DAYS[2])
    original_state=msd._backfill_state_path().read_bytes()
    original_manifest=msd._manifest_path().read_bytes()
    path=msd._ticker_path("AAPL")
    def concurrent(*args, **kwargs):
        altered=pd.read_parquet(path)
        altered.loc[pd.Timestamp(DAYS[0]),"close"]=199.5
        altered.to_parquet(path)
        return _day_frame(DAYS[2])
    monkeypatch.setattr(msd, "fetch_aggs", concurrent)
    output=msd.repair_processed_day_missing_members(DAYS[2], ("AAPL",))
    assert output["status"]=="REFUSED"
    assert output["reason"]=="ORIGINAL_SOURCE_CHANGED"
    assert DAYS[2] not in set(msd.load_ticker("AAPL").index.date)
    assert float(msd.load_ticker("AAPL").loc[pd.Timestamp(DAYS[0]),"close"])==199.5
    assert msd._manifest_path().read_bytes()==original_manifest
    assert msd._backfill_state_path().read_bytes()==original_state
    assert list(path.parent.glob(".AAPL.parquet.repair-*.tmp"))==[]



def test_operator_repair_refuses_changed_global_state_during_vendor_fetch(
    store, monkeypatch,
):
    """A concurrent night's updated resume state cannot be reverted by repair."""
    msd.backfill(start=DAYS[0], end=DAYS[3])
    _remove_bar("AAPL", DAYS[2])
    before=msd._ticker_path("AAPL").read_bytes()
    manifest=msd._manifest_path().read_bytes()
    state_path=msd._backfill_state_path()
    def concurrent(*args, **kwargs):
        body=json.loads(state_path.read_text())
        body["processed_days"].append(DAYS[4].isoformat())
        body["last_captured_date"]=DAYS[4].isoformat()
        state_path.write_text(json.dumps(body))
        return _day_frame(DAYS[2])
    monkeypatch.setattr(msd, "fetch_aggs", concurrent)
    outcome=msd.repair_processed_day_missing_members(DAYS[2], ("AAPL",))
    assert outcome["status"]=="REFUSED"
    assert outcome["reason"]=="ORIGINAL_STATE_CHANGED"
    assert msd._ticker_path("AAPL").read_bytes()==before
    assert msd._manifest_path().read_bytes()==manifest
    assert DAYS[4] in msd._processed_days()


def test_operator_repair_refuses_changed_original_manifest_during_vendor_fetch(
    store, monkeypatch,
):
    """A changed collector manifest is not overwritten by the repair's clock."""
    msd.backfill(start=DAYS[0], end=DAYS[3])
    _remove_bar("AAPL", DAYS[2])
    original=msd._ticker_path("AAPL").read_bytes()
    original_state=msd._backfill_state_path().read_bytes()
    manifest=msd._manifest_path()
    def concurrent(*args, **kwargs):
        body=json.loads(manifest.read_text())
        body["updated_at"]="2026-10-16T15:00:00+00:00"
        manifest.write_text(json.dumps(body))
        return _day_frame(DAYS[2])
    monkeypatch.setattr(msd, "fetch_aggs", concurrent)
    outcome=msd.repair_processed_day_missing_members(DAYS[2], ("AAPL",))
    assert outcome["status"]=="REFUSED"
    assert outcome["reason"]=="ORIGINAL_MANIFEST_CHANGED"
    assert msd._ticker_path("AAPL").read_bytes()==original
    assert msd._backfill_state_path().read_bytes()==original_state
    assert json.loads(manifest.read_text())["updated_at"]=="2026-10-16T15:00:00+00:00"
