"""tests/test_topup_thetadata_daily.py — AD-1T1 `--daily` mode §H hostile suite.

Covers spec `research/AD1T1_INCREMENTAL_CADENCE_SPEC_2026-08-22.md` families:
clock (F3/F4/F12), pair (F1/F6), writer (F9/F14/F15), universe (F5/F6),
deadline (F2), compatibility, and receipt (F1/F8/F16).

The clock is injected via a `now_fn` seam — no test sleeps. The vendor is a
FakeTd object passed directly into the low-level pool functions, or installed
onto the real `collectors.thetadata` module (via monkeypatch) for tests that
exercise the full `_daily_main` entry point.
"""
from __future__ import annotations

import json
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

import scripts.topup_thetadata_day as topup
from lib import nyse_calendar as nc

ET = nc.ET
REPO_ROOT = Path(__file__).resolve().parent.parent
SENTINEL_SH = REPO_ROOT / "scripts" / "launchd" / "theta_staleness_sentinel.sh"


@pytest.mark.parametrize("forced,hour,partial,expected", [
    (False, 16, False, True), (True, 16, False, False),
    (False, 9, False, False), (False, 16, True, False),
])
def test_baseline_refresh_only_follows_healthy_natural_source(store, monkeypatch,
                                                           forced, hour, partial, expected):
    _wire_daily(monkeypatch, store, t1=["SPY"], ad=["SPY"])
    plan = {("greeks", "SPY", S_MID): _empty_df()} if partial else {}
    _install_fake_td(monkeypatch, FakeTd(plan=plan))
    calls = []
    runtime = Path("/existing/liveflow")
    monkeypatch.setattr(topup, "_refresh_live_flow_baselines",
                        lambda *a: calls.append(a) or {"status": "complete"})
    topup._daily_main(workers=1, deadline_min=20, forced=forced,
                     now_fn=lambda: _et(2026, 8, 19, hour, 30), baseline_runtime=runtime)
    assert calls == ([(runtime, store, S_MID)] if expected else [])


def test_failed_baseline_does_not_relabel_healthy_source_or_hold_writer_lock(store, monkeypatch):
    _wire_daily(monkeypatch, store, t1=["SPY"], ad=["SPY"])
    _install_fake_td(monkeypatch, FakeTd())
    def failed(*args):
        with topup._writer_lock(store) as acquired:
            assert acquired is False  # stable source throughout the child read
        return {"status": "failed", "reason": "timeout"}
    monkeypatch.setattr(topup, "_refresh_live_flow_baselines", failed)
    rc = topup._daily_main(workers=1, deadline_min=20, forced=False,
                           now_fn=lambda: _et(2026, 8, 19, 16, 30),
                           baseline_runtime=Path("/existing/liveflow"))
    receipt = json.loads((store / "_manifest.json").read_text())["daily_refresh"]
    assert rc == 1
    assert receipt["status"] == "healthy"
    assert receipt["live_flow_baselines"]["status"] == "failed"
    with topup._writer_lock(store) as acquired:
        assert acquired is True


@pytest.mark.parametrize("outcome", ["success", "nonzero", "timeout", "launch"])
def test_refresh_uses_exact_consumer_environment_and_bounded_builder(tmp_path, monkeypatch, outcome):
    runtime = tmp_path / "liveflow"
    wrapper = runtime / "ops/launchd/run_with_env.sh"
    wrapper.parent.mkdir(parents=True)
    wrapper.touch()
    (runtime / ".env").touch()
    def launch(argv, **kw):
        assert argv[:4] == [str(wrapper), str(runtime / ".env"), topup.sys.executable, "-m"]
        assert argv[4:] == ["scripts.build_live_flow_baselines", "--poll-universe", "--chunk-size", "1",
                           "--require-source-session", "2026-08-18", "--expected-store", str(tmp_path.resolve())]
        assert kw == {"cwd": runtime, "timeout": 600, "check": False}
        if outcome == "timeout": raise subprocess.TimeoutExpired(argv, 600)
        if outcome == "launch": raise PermissionError("test")
        return subprocess.CompletedProcess(argv, 0 if outcome == "success" else 1)
    monkeypatch.setattr(topup.subprocess, "run", launch)
    result = topup._refresh_live_flow_baselines(runtime, tmp_path, S_MID)
    assert result["status"] == ("complete" if outcome == "success" else "failed")

# A known midweek session day with a resolvable prior session.
D_MID = date(2026, 8, 19)          # Wednesday
S_MID = date(2026, 8, 18)          # Tuesday
# Friday -> Monday
D_MON = date(2026, 8, 24)
S_FRI = date(2026, 8, 21)
# A weekday holiday (New Year's Day observed on a Thursday in 2026)
HOLIDAY_WEEKDAY = date(2026, 1, 1)
# DST regimes
D_EDT = date(2026, 7, 15)          # summer, EDT = UTC-4
D_EST = date(2026, 1, 14)          # winter, EST = UTC-5
# Dec -> Jan session boundary
D_JAN = date(2026, 1, 2)
S_DEC = date(2025, 12, 31)


def _et(y, m, d, hh, mm) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=ET)


def _utc(y, m, d, hh, mm) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=timezone.utc)


def _df(day: date, n: int = 2) -> pd.DataFrame:
    return pd.DataFrame({"date": [pd.Timestamp(day)] * n, "strike": list(range(n))})


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame({"date": pd.Series([], dtype="datetime64[ns]"),
                         "strike": pd.Series([], dtype="float64")})


def _wrong_date_df(day: date, other: date) -> pd.DataFrame:
    """Rows returned, but none carry `day` — the F6 date_unresolved shape."""
    return pd.DataFrame({"date": [pd.Timestamp(other)], "strike": [1]})


def _snapshot_vendor_df(root: str, day: date, n: int = 2) -> pd.DataFrame:
    """Raw `snapshot_open_interest` vendor shape (K2): root, expiration,
    strike, right, snapshot_ts, open_interest — snapshot_ts stamped inside
    `day` (~06:30 ET OPRA print), NOT yet normalized to a `date` column
    (that is `_snapshot_oi_frame`'s job)."""
    ts = pd.Timestamp(day) + pd.Timedelta(hours=6, minutes=30)
    return pd.DataFrame({
        "root": [root] * n,
        "expiration": [pd.Timestamp(day)] * n,
        "strike": list(range(n)),
        "right": ["C"] * n,
        "snapshot_ts": [ts] * n,
        "open_interest": [100] * n,
    })


class FakeTd:
    """Fake vendor surface for the daily 4-cell ensure (§A4/§A5).

    `default_D` (K2) is the day the DEFAULT (unconfigured) snapshot response
    is stamped with — `snapshot_open_interest(root)` takes no date argument
    (matching the real vendor endpoint), so a test whose run's `D` is not
    `D_MID` (the file's dominant fixture day) must pass its own `default_D`
    explicitly for `snapshot_open_interest`'s default `complete` behavior to
    land on the right day. `snapshot_plan` (keyed by root only, matching the
    endpoint's own no-date signature) overrides the default per-root."""

    def __init__(self, plan: dict[tuple[str, str, date], object] | None = None,
                reachable_sequence=None,
                snapshot_plan: dict[str, object] | None = None,
                default_D: date | None = None):
        self.plan = plan or {}
        self.snapshot_plan = snapshot_plan or {}
        self.default_D = default_D if default_D is not None else D_MID
        self._reachable_seq = list(reachable_sequence) if reachable_sequence else None
        self._reachable_default = True
        self.calls: list[tuple] = []
        # (K2) tracked SEPARATELY from `self.calls` — both `bulk_open_interest`
        # and `snapshot_open_interest` tag their `self.calls` entry the same
        # ("oi", root, day) shape (for call-count-assertion compatibility with
        # the pre-K2 tests), so a test that must discriminate WHICH vendor
        # method oi_D actually invoked needs its own list.
        self.snapshot_calls: list[str] = []
        self.on_call = None

    def reachable(self) -> bool:
        if self._reachable_seq is not None:
            if self._reachable_seq:
                return self._reachable_seq.pop(0)
            return self._reachable_default
        return self._reachable_default

    def _get(self, tier: str, root: str, day: date):
        self.calls.append((tier, root, day))
        if self.on_call:
            self.on_call(tier, root, day)
        key = (tier, root, day)
        if key in self.plan:
            v = self.plan[key]
            return v(day) if callable(v) else v
        return _df(day)

    def bulk_eod(self, root, exp, start, end):
        return self._get("eod", root, start)

    def bulk_open_interest(self, root, exp, start, end):
        return self._get("oi", root, start)

    def bulk_greeks(self, root, exp, start, end, order=3):
        return self._get("greeks", root, start)

    def snapshot_open_interest(self, root):
        # (K2) tagged "oi"/default_D so call-count assertions written
        # against the old bulk_open_interest(root, 0, D, D) shape keep
        # working unchanged.
        self.calls.append(("oi", root, self.default_D))
        self.snapshot_calls.append(root)
        if self.on_call:
            self.on_call("oi", root, self.default_D)
        if root in self.snapshot_plan:
            v = self.snapshot_plan[root]
            return v(self.default_D) if callable(v) else v
        return _snapshot_vendor_df(root, self.default_D)


def _install_fake_td(monkeypatch, fake):
    import collectors.thetadata as real_td
    monkeypatch.setattr(real_td, "reachable", fake.reachable)
    monkeypatch.setattr(real_td, "bulk_eod", fake.bulk_eod)
    monkeypatch.setattr(real_td, "bulk_open_interest", fake.bulk_open_interest)
    monkeypatch.setattr(real_td, "bulk_greeks", fake.bulk_greeks)
    monkeypatch.setattr(real_td, "snapshot_open_interest", fake.snapshot_open_interest)


def _wire_daily(monkeypatch, store, *, t1=None, ad=None):
    monkeypatch.setattr(topup, "resolve_thetadata_store", lambda **kw: str(store))
    monkeypatch.setattr(topup, "_daily_universe", lambda: list(t1 or ["SPY", "QQQ", "AAPL", "SPX"]))
    monkeypatch.setattr(topup, "_ad_universe", lambda: list(ad or ["SPY", "QQQ", "AAPL"]))


def _manifest(store) -> dict:
    return json.loads((store / "_manifest.json").read_text())


@pytest.fixture()
def store(tmp_path):
    return tmp_path / "thetadata_eod"


# ═════════════════════════ CLOCK (F3/F4/F12) ════════════════════════════════
def test_gate_closed_on_weekend_no_op():
    ctx = topup._resolve_daily_context(_et(2026, 8, 22, 18, 0), forced=False)  # Saturday
    assert ctx is None


def test_gate_closed_on_weekday_holiday_no_op():
    ctx = topup._resolve_daily_context(_et(2026, 1, 1, 18, 0), forced=False)
    assert ctx is None


def test_gate_open_midweek_after_1610_et():
    ctx = topup._resolve_daily_context(_et(2026, 8, 19, 16, 10), forced=False)
    assert ctx is not None
    assert ctx.D == D_MID
    assert ctx.S == S_MID


def test_gate_closed_one_minute_before_1610_et():
    ctx = topup._resolve_daily_context(_et(2026, 8, 19, 16, 9), forced=False)
    assert ctx is None


def test_friday_to_monday_targets_prior_friday():
    ctx = topup._resolve_daily_context(_et(2026, 8, 24, 16, 30), forced=False)
    assert ctx.D == D_MON
    assert ctx.S == S_FRI


def test_delayed_invocation_2200_et_same_day_identical_context():
    early = topup._resolve_daily_context(_et(2026, 8, 19, 16, 15), forced=False)
    late = topup._resolve_daily_context(_et(2026, 8, 19, 22, 0), forced=False)
    assert early.D == late.D == D_MID
    assert early.S == late.S == S_MID


def test_f4_trap_expected_last_session_forbidden():
    """At 16:15 ET on session D, expected_last_session() would (wrongly)
    return the PRIOR session because its 17:00 ET settle buffer has not
    passed — this test fails if anyone swaps expected_last_session() in for
    the D derivation."""
    now = _et(2026, 8, 19, 16, 15)
    ctx = topup._resolve_daily_context(now, forced=False)
    assert ctx.D == D_MID
    assert ctx.D != nc.expected_last_session(now)


def test_dst_boundary_summer_edt_utc_time_would_fool_fixed_offset():
    # 16:10 ET in EDT (UTC-4) = 20:10 UTC. A fixed UTC-5 assumption would read
    # this as 15:10 ET (gate closed) — zoneinfo must get it right.
    now_utc = _utc(2026, 7, 15, 20, 10)
    ctx = topup._resolve_daily_context(now_utc, forced=False)
    assert ctx is not None
    assert ctx.D == D_EDT


def test_dst_boundary_winter_est_utc_time_would_fool_fixed_offset():
    # 16:10 ET in EST (UTC-5) = 21:10 UTC. A fixed UTC-4 assumption would read
    # this as 17:10 ET — still open, but on the WRONG derivation path; assert
    # the exact UTC-5 arithmetic instead of a coincidentally-passing gate.
    now_utc = _utc(2026, 1, 14, 21, 10)
    ctx = topup._resolve_daily_context(now_utc, forced=False)
    assert ctx is not None
    assert ctx.D == D_EST
    just_before = _utc(2026, 1, 14, 21, 9)
    assert topup._resolve_daily_context(just_before, forced=False) is None


def test_run_context_freeze_now_fn_called_exactly_once(store, monkeypatch):
    _wire_daily(monkeypatch, store, t1=["SPY"], ad=["SPY"])
    fake = FakeTd()
    _install_fake_td(monkeypatch, fake)
    calls = {"n": 0}

    def now_fn():
        calls["n"] += 1
        return _et(2026, 8, 19, 16, 30)

    rc = topup._daily_main(workers=1, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False, now_fn=now_fn)
    assert rc == 0
    assert calls["n"] == 1


def test_same_session_rerun_is_zero_vendor_calls(store, monkeypatch):
    day_ctx = topup.RunContext(D=D_MID, S=S_MID, forced=False)
    for cell_tier, day in (("eod", S_MID), ("oi", S_MID), ("oi", D_MID), ("greeks", S_MID)):
        topup._merge_day(store, cell_tier, "SPY", day, _df(day))
    _wire_daily(monkeypatch, store, t1=["SPY"], ad=["SPY"])
    fake = FakeTd()
    _install_fake_td(monkeypatch, fake)
    rc = topup._daily_main(workers=1, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                           now_fn=lambda: _et(2026, 8, 19, 16, 30))
    assert rc == 0
    assert fake.calls == []
    receipt = _manifest(store)["daily_refresh"]
    assert receipt["status"] == "healthy"


def test_f12_s_suspect_non_session_flag(store, monkeypatch):
    # 5 roots, all attempted + all vendor-empty: clears the N1 min-attempt
    # floor (max(5, ceil(5% of 5))=5) with ratio 100% > 50%.
    roots = ["SPY", "QQQ", "AAPL", "MSFT", "AMZN"]
    plan = {("eod", r, S_MID): _empty_df() for r in roots}
    _wire_daily(monkeypatch, store, t1=roots, ad=roots)
    fake = FakeTd(plan=plan)
    _install_fake_td(monkeypatch, fake)
    rc = topup._daily_main(workers=2, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                           now_fn=lambda: _et(2026, 8, 19, 16, 30))
    receipt = _manifest(store)["daily_refresh"]
    assert receipt["s_suspect_non_session"] is True


def test_f12_not_suspect_when_under_half_vendor_empty(store, monkeypatch):
    roots = ["SPY", "QQQ", "AAPL", "MSFT", "AMZN"]
    plan = {("eod", "SPY", S_MID): _empty_df()}   # 1/5 = 20%, under the ratio bar
    _wire_daily(monkeypatch, store, t1=roots, ad=roots)
    fake = FakeTd(plan=plan)
    _install_fake_td(monkeypatch, fake)
    topup._daily_main(workers=2, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                      now_fn=lambda: _et(2026, 8, 19, 16, 30))
    receipt = _manifest(store)["daily_refresh"]
    assert receipt["s_suspect_non_session"] is False


# ── RF8 (R3): denominator = roots with an ACTUAL EOD[S] vendor attempt ─────
def test_rf8_aggregate_denominator_excludes_already_present():
    """Direct flip test: the OLD denominator (all processed roots) would
    have read 5/10=50% here — NOT over the >50% bar, so a real closure
    signal would have been invisible. The FIXED denominator (only the 5
    ROOTS actually asked this run) reads 5/5=100%. 5 attempted also clears
    the N1 min-attempt floor for a 10-root universe (max(5, ceil(0.05*10))=5)."""
    results = {}
    for i in range(5):
        root = f"AP{i}"
        results[root] = topup.RootResult(root=root, state="already_present", cells={
            "eod_S": "already_present", "oi_S": "already_present",
            "oi_D": "already_present", "greeks_S": "already_present"})
    for i in range(5):
        root = f"VE{i}"
        results[root] = topup.RootResult(root=root, state="vendor_empty", cells={
            "eod_S": "vendor_empty", "oi_S": "vendor_empty",
            "oi_D": "vendor_empty", "greeks_S": "vendor_empty"})
    agg = topup._aggregate_daily(results, list(results), list(results))
    old_denominator_ratio = 5 / len(results)   # what the pre-RF8 code computed
    assert not (old_denominator_ratio > topup._S_SUSPECT_VENDOR_EMPTY_FRACTION)
    assert agg["s_suspect_non_session"] is True


def test_rf8_ladder_refire_fixture_end_to_end(store, monkeypatch):
    """Same shape as above but through the real `_daily_main` pipeline: 5
    roots already fully present (a prior ladder rung already fetched them
    today) + 5 freshly-attempted roots that come back EOD[S] vendor-empty
    (an unlisted market closure) — 5 attempted clears the N1 floor."""
    already_present_roots = [f"AP{i}" for i in range(5)]
    attempted_roots = [f"VE{i}" for i in range(5)]
    for root in already_present_roots:
        for tier, day in (("eod", S_MID), ("oi", S_MID), ("oi", D_MID), ("greeks", S_MID)):
            topup._merge_day(store, tier, root, day, _df(day))
    plan = {("eod", r, S_MID): _empty_df() for r in attempted_roots}
    all_roots = already_present_roots + attempted_roots
    _wire_daily(monkeypatch, store, t1=all_roots, ad=all_roots)
    fake = FakeTd(plan=plan)
    _install_fake_td(monkeypatch, fake)
    topup._daily_main(workers=4, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                      now_fn=lambda: _et(2026, 8, 19, 16, 30))
    receipt = _manifest(store)["daily_refresh"]
    assert receipt["s_suspect_non_session"] is True


# ── N1 (R3 verify-pass): minimum-attempt floor on the s_suspect ratio ──────
def test_n1_reviewer_exact_19_plus_1_fixture_is_false():
    """The exact reviewer-falsifying fixture: 19 roots already_present (a
    ladder re-fire steady state) + 1 genuinely option-less root attempted
    (vendor_empty). Pre-N1 this read eod_s_attempted=1, ratio=1/1=100% ->
    a spurious True from a single root. The floor
    (max(5, ceil(5% of t1_universe_count))) keeps a 1-root sample from
    ever meaning anything."""
    results = {}
    for i in range(19):
        root = f"AP{i}"
        results[root] = topup.RootResult(root=root, state="already_present", cells={
            "eod_S": "already_present", "oi_S": "already_present",
            "oi_D": "already_present", "greeks_S": "already_present"})
    results["ZZZZ"] = topup.RootResult(root="ZZZZ", state="vendor_empty", cells={
        "eod_S": "vendor_empty", "oi_S": "vendor_empty",
        "oi_D": "vendor_empty", "greeks_S": "vendor_empty"})
    agg = topup._aggregate_daily(results, list(results), list(results))
    assert agg["s_suspect_non_session"] is False


def test_n1_genuine_closure_above_the_floor_is_true():
    """A REAL closure with enough attempted roots to clear the floor still
    flags correctly — N1's floor guards against noise, not against
    detection. 15 already_present + 6 attempted (all vendor_empty): 6 >=
    max(5, ceil(0.05*21))=5, ratio 100% > 50%."""
    results = {}
    for i in range(15):
        root = f"AP{i}"
        results[root] = topup.RootResult(root=root, state="already_present", cells={
            "eod_S": "already_present", "oi_S": "already_present",
            "oi_D": "already_present", "greeks_S": "already_present"})
    for i in range(6):
        root = f"VE{i}"
        results[root] = topup.RootResult(root=root, state="vendor_empty", cells={
            "eod_S": "vendor_empty", "oi_S": "vendor_empty",
            "oi_D": "vendor_empty", "greeks_S": "vendor_empty"})
    agg = topup._aggregate_daily(results, list(results), list(results))
    assert agg["s_suspect_non_session"] is True


def test_n1_floor_scales_with_universe_size():
    """For a large universe, the 5% term can exceed the flat floor of 5 —
    e.g. a 200-root universe needs >=10 attempted roots, not just 5."""
    results = {}
    for i in range(190):
        root = f"AP{i}"
        results[root] = topup.RootResult(root=root, state="already_present", cells={
            "eod_S": "already_present", "oi_S": "already_present",
            "oi_D": "already_present", "greeks_S": "already_present"})
    for i in range(8):   # 8 attempted, all vendor_empty — 8 < ceil(0.05*198)=10
        root = f"VE{i}"
        results[root] = topup.RootResult(root=root, state="vendor_empty", cells={
            "eod_S": "vendor_empty", "oi_S": "vendor_empty",
            "oi_D": "vendor_empty", "greeks_S": "vendor_empty"})
    agg = topup._aggregate_daily(results, list(results), list(results))
    assert agg["s_suspect_non_session"] is False   # under the scaled floor


def test_rf8_zero_attempts_is_false_never_divides_by_zero(store):
    results = {"SPY": topup.RootResult(root="SPY", state="already_present", cells={
        "eod_S": "already_present", "oi_S": "already_present",
        "oi_D": "already_present", "greeks_S": "already_present"})}
    agg = topup._aggregate_daily(results, list(results), list(results))
    assert agg["s_suspect_non_session"] is False


# ═════════════════════════ PAIR (§A4/F1/F6) ═════════════════════════════════
def test_ensure_one_cell_already_present(store):
    topup._merge_day(store, "oi", "SPY", S_MID, _df(S_MID))
    state = topup._ensure_one_cell(store, "oi", "SPY", S_MID, lambda: (_ for _ in ()).throw(AssertionError("should not fetch")))
    assert state == "already_present"


def test_ensure_one_cell_bootstrap_fetches_and_merges(store):
    state = topup._ensure_one_cell(store, "oi", "SPY", S_MID, lambda: _df(S_MID))
    assert state == "complete"
    assert topup._has_day(store, "oi", "SPY", S_MID)


@pytest.mark.parametrize("tier,attr,day", [
    ("eod", "eod_S", S_MID), ("greeks", "greeks_S", S_MID), ("oi", "oi_D", D_MID),
])
def test_each_cell_independently_absent_is_fetched_singly(store, tier, attr, day):
    # NOTE: "oi" is the tier for BOTH oi_S and oi_D, so the call count must be
    # scoped to (tier, day), not tier alone — oi_S also fires unconditionally
    # per §A4/§A5, and would otherwise double-count as a second "oi" call.
    fake = FakeTd()
    result = topup._ensure_daily_root(store, "SPY", S_MID, D_MID, fake)
    assert result.cells[attr] == "complete"
    assert sum(1 for c, r, d in fake.calls if c == tier and d == day) == 1


def test_oi_d_absent_leaves_root_s_panel_complete_but_not_chain_next(store, monkeypatch):
    fake = FakeTd(snapshot_plan={"SPY": _empty_df()})
    result = topup._ensure_daily_root(store, "SPY", S_MID, D_MID, fake)
    assert topup._s_panel_ok(result) is True
    assert result.cells["oi_D"] == "vendor_empty"
    assert not topup._panel_present(result.cells, "oi_D")


# ── K1 (Sol B1a) INVERTED: this test used to assert `healthy` here — the
# frozen amendment (research/AD1T1_INCREMENTAL_CADENCE_SPEC_2026-08-22.md
# §K1) makes this exact fixture the hostile family: OI[D] absent EVERYWHERE
# must NEVER be healthy, no matter how complete the observational S-panel
# is. `chain_next_ad_roots == 0` (the OI[D]-within-AD-universe count) stays
# unaffected — it was already 0 in this fixture before the ruling.
def test_oi_d_absent_everywhere_is_partial_never_healthy(store, monkeypatch):
    snapshot_plan = {"SPY": _empty_df(), "QQQ": _empty_df()}
    _wire_daily(monkeypatch, store, t1=["SPY", "QQQ"], ad=["SPY", "QQQ"])
    fake = FakeTd(snapshot_plan=snapshot_plan)
    _install_fake_td(monkeypatch, fake)
    rc = topup._daily_main(workers=2, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                           now_fn=lambda: _et(2026, 8, 19, 16, 30))
    receipt = _manifest(store)["daily_refresh"]
    assert receipt["s_panel_coverage_pct"] == 1.0   # S-panel is perfect …
    assert receipt["ad_ready_coverage_pct"] == 0.0   # … but AD-ready is zero
    assert receipt["status"] == "partial"
    assert receipt["status"] != "healthy"
    assert receipt["chain_next_ad_roots"] == 0
    assert rc == 1


def test_no_eod_d_or_greeks_d_request_ever(store):
    fake = FakeTd()
    topup._ensure_daily_root(store, "SPY", S_MID, D_MID, fake)
    for tier, root, day in fake.calls:
        if day == D_MID:
            assert tier == "oi", f"unexpected D-day request for tier={tier}"


def test_dec_jan_year_boundary_cells_land_in_their_own_year(store):
    fake = FakeTd(default_D=D_JAN)
    topup._ensure_daily_root(store, "SPY", S_DEC, D_JAN, fake)
    assert topup._has_day(store, "eod", "SPY", S_DEC)
    assert topup._has_day(store, "greeks", "SPY", S_DEC)
    assert topup._has_day(store, "oi", "SPY", S_DEC)
    assert topup._has_day(store, "oi", "SPY", D_JAN)
    assert (store / "eod" / "SPY" / "2025.parquet").exists()
    assert (store / "oi" / "SPY" / "2026.parquet").exists()


def test_stale_july_fresh_august_store_no_writes_outside_s_d_cells(store):
    stale_day = date(2026, 7, 1)
    topup._merge_day(store, "eod", "SPY", stale_day, _df(stale_day))
    fake = FakeTd()
    topup._ensure_daily_root(store, "SPY", S_MID, D_MID, fake)
    out = pd.read_parquet(store / "eod" / "SPY" / "2026.parquet")
    dates_touched = set(pd.to_datetime(out["date"]).dt.date)
    assert dates_touched == {stale_day, S_MID}


# ═══════════════ K2 (Sol B1b) OI[D] SNAPSHOT FRONTIER WRAPPER ══════════════
class _StubSnapshotTd:
    """Frozen-frame vendor stub for `_snapshot_oi_frame` unit tests — NO live
    vendor calls, NO FakeTd machinery (this exercises the wrapper directly)."""

    def __init__(self, frame):
        self._frame = frame

    def snapshot_open_interest(self, root):
        return self._frame(root) if callable(self._frame) else self._frame


def test_k2_snapshot_wrapper_none_is_fetch_failed(store):
    state = topup._ensure_one_cell(
        store, "oi", "SPY", D_MID,
        lambda: topup._snapshot_oi_frame(_StubSnapshotTd(None), "SPY"))
    assert state == "fetch_failed"


def test_k2_snapshot_wrapper_empty_is_vendor_empty(store):
    state = topup._ensure_one_cell(
        store, "oi", "SPY", D_MID,
        lambda: topup._snapshot_oi_frame(_StubSnapshotTd(_empty_df()), "SPY"))
    assert state == "vendor_empty"


def test_k2_snapshot_wrapper_d_stamped_rows_pass_through_and_complete(store):
    raw = _snapshot_vendor_df("SPY", D_MID)
    state = topup._ensure_one_cell(
        store, "oi", "SPY", D_MID,
        lambda: topup._snapshot_oi_frame(_StubSnapshotTd(raw), "SPY"))
    assert state == "complete"
    assert topup._has_day(store, "oi", "SPY", D_MID)
    stored = pd.read_parquet(store / "oi" / "SPY" / f"{D_MID.year}.parquet")
    assert set(stored.columns) == {"root", "expiration", "strike", "right", "date",
                                   "open_interest"}


def test_k2_snapshot_wrapper_stale_stamped_only_is_date_unresolved(store):
    stale_day = date(2026, 8, 17)
    raw = _snapshot_vendor_df("SPY", stale_day)
    state = topup._ensure_one_cell(
        store, "oi", "SPY", D_MID,
        lambda: topup._snapshot_oi_frame(_StubSnapshotTd(raw), "SPY"))
    assert state == "date_unresolved"
    assert not topup._has_day(store, "oi", "SPY", D_MID)


def test_k2_snapshot_wrapper_mixed_dates_keeps_only_d_rows_and_merges(store):
    d_rows = _snapshot_vendor_df("SPY", D_MID, n=2)
    stale_rows = _snapshot_vendor_df("SPY", date(2026, 8, 17), n=3)
    mixed = pd.concat([d_rows, stale_rows], ignore_index=True)
    state = topup._ensure_one_cell(
        store, "oi", "SPY", D_MID,
        lambda: topup._snapshot_oi_frame(_StubSnapshotTd(mixed), "SPY"))
    assert state == "complete"
    stored = pd.read_parquet(store / "oi" / "SPY" / f"{D_MID.year}.parquet")
    assert len(stored) == 2   # only the D-stamped rows landed — stale rows dropped
    assert set(pd.to_datetime(stored["date"]).dt.date) == {D_MID}


def test_k2_snapshot_wrapper_drops_snapshot_ts_and_selects_exact_schema(store):
    raw = _snapshot_vendor_df("SPY", D_MID)
    raw["junk_extra_column"] = "should not survive"
    out = topup._snapshot_oi_frame(_StubSnapshotTd(raw), "SPY")
    assert list(out.columns) == ["root", "expiration", "strike", "right", "date",
                                 "open_interest"]
    assert "snapshot_ts" not in out.columns


# ── K6 MAJOR-2: dedup runs AFTER snapshot_ts is dropped ─────────────────────
def test_k6_major2_snapshot_wrapper_dedups_rows_differing_only_in_snapshot_ts(store):
    """Two vendor rows identical on every OTHER column (same contract, same
    OI) but stamped with different per-contract `snapshot_ts` values must
    collapse to exactly ONE stored row — upstream `_normalize_snapshot_df`
    dedupes while `snapshot_ts` still differs per-contract, so duplicate v3
    rows survive that pass unless this wrapper re-dedupes AFTER dropping
    `snapshot_ts` (same ordering law as `_normalize_oi_df`)."""
    ts_a = pd.Timestamp(D_MID) + pd.Timedelta(hours=6, minutes=30, seconds=0)
    ts_b = pd.Timestamp(D_MID) + pd.Timedelta(hours=6, minutes=30, seconds=1)
    raw = pd.DataFrame({
        "root": ["SPY", "SPY"],
        "expiration": [pd.Timestamp(D_MID), pd.Timestamp(D_MID)],
        "strike": [100, 100],
        "right": ["C", "C"],
        "snapshot_ts": [ts_a, ts_b],
        "open_interest": [500, 500],
    })
    state = topup._ensure_one_cell(
        store, "oi", "SPY", D_MID,
        lambda: topup._snapshot_oi_frame(_StubSnapshotTd(raw), "SPY"))
    assert state == "complete"
    stored = pd.read_parquet(store / "oi" / "SPY" / f"{D_MID.year}.parquet")
    assert len(stored) == 1   # duplicate rows (differing only pre-drop by snapshot_ts) collapse


# ── K6 NOTE-3: an OI[D] cell must never classify complete without OI ────────
def test_k6_note3_snapshot_frame_missing_open_interest_column_is_fetch_failed(store):
    raw = pd.DataFrame({
        "root": ["SPY"],
        "expiration": [pd.Timestamp(D_MID)],
        "strike": [100],
        "right": ["C"],
        "snapshot_ts": [pd.Timestamp(D_MID) + pd.Timedelta(hours=6, minutes=30)],
        # no "open_interest" column — malformed vendor response
    })
    state = topup._ensure_one_cell(
        store, "oi", "SPY", D_MID,
        lambda: topup._snapshot_oi_frame(_StubSnapshotTd(raw), "SPY"))
    assert state == "fetch_failed"
    assert not topup._has_day(store, "oi", "SPY", D_MID)


def test_k2_ensure_daily_root_oi_d_uses_snapshot_not_bulk_open_interest(store):
    """Direct pin of the K2 call-site swap: `_ensure_daily_root`'s oi_D cell
    must call `td.snapshot_open_interest`, never `td.bulk_open_interest`.
    `snapshot_calls` is tracked separately from the legacy `calls` log
    precisely so this test can tell the two vendor methods apart (both tag
    `calls` identically for call-count-assertion compatibility)."""
    fake = FakeTd()
    topup._ensure_daily_root(store, "SPY", S_MID, D_MID, fake)
    assert fake.snapshot_calls == ["SPY"]
    oi_calls_for_d = [c for c in fake.calls if c == ("oi", "SPY", D_MID)]
    assert len(oi_calls_for_d) == 1


# ═════════════════════════ WRITER (§B/F9/F14) ═══════════════════════════════
def _hash_tree(store) -> dict:
    """(RF6, R3) CONTENT hashes keyed by relpath — a path-list compare (the
    original shape of this test) passes on an in-place overwrite that keeps
    the same set of filenames but changes their bytes; a content hash does
    not."""
    import hashlib
    out = {}
    if not store.exists():
        return out
    for p in sorted(store.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(store))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def test_two_concurrent_daily_invocations_second_refused(store, monkeypatch, capsys):
    _wire_daily(monkeypatch, store, t1=["SPY"], ad=["SPY"])
    fake = FakeTd()
    _install_fake_td(monkeypatch, fake)
    store.mkdir(parents=True)
    with topup._writer_lock(store) as acquired:
        assert acquired is True
        # Snapshot AFTER the outer (simulated first-writer) lock file itself
        # exists — that file's creation is the first writer's own legitimate
        # side effect, not something the REFUSED second writer may cause.
        before = _hash_tree(store)
        rc = topup._daily_main(workers=1, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                               now_fn=lambda: _et(2026, 8, 19, 16, 30))
        after = _hash_tree(store)
    assert rc == 0   # F14 — daily refusal exits 0
    assert fake.calls == []
    assert before == after   # CONTENT hash compare: zero mutations, not just zero new paths
    out = capsys.readouterr().out
    assert json.loads(out.strip().splitlines()[-1]) == {"event": "writer_locked", "mode": "daily"}


def test_daily_then_historical_backfill_either_order_both_locked(store, monkeypatch):
    """(RF4, R3) A REAL cross-writer lock test exercising `backfill.main()`'s
    own lock site (not a fake double `_writer_lock()` nesting) in BOTH
    orders against a topup lock holder. Pull internals are monkeypatched to
    no-ops so no real vendor/network access is needed."""
    import sys as _sys
    import threading

    import scripts.backfill_thetadata_eod as bf
    import collectors.thetadata as real_td

    store.mkdir(parents=True)
    monkeypatch.setattr(bf, "_store_dir", lambda: store)
    monkeypatch.setattr(bf, "resolve_thetadata_store", lambda **kw: str(store))  # RF3 agreement
    monkeypatch.setattr(bf, "_resolve_universe", lambda extra_roots=None: ["SPY"])
    monkeypatch.setattr(bf, "_pull_root_year", lambda *a, **kw: True)
    monkeypatch.setattr(bf.time, "sleep", lambda s: None)
    monkeypatch.setattr(real_td, "reachable", lambda: True)
    monkeypatch.setattr(_sys, "argv", ["backfill_thetadata_eod.py"])

    # Order 1: topup holds first -> bf.main() refuses at ITS OWN lock site.
    with topup._writer_lock(store) as acquired:
        assert acquired is True
        rc = bf.main()
    assert rc == 1
    assert not (store / "_backfill_state.json").exists()   # refusal mutates nothing

    # Order 2: backfill holds (via a REAL, blocking bf.main() run) -> topup refuses.
    hold_gate = threading.Event()
    release_gate = threading.Event()

    def _blocking_pull(*a, **kw):
        hold_gate.set()
        release_gate.wait(timeout=10)
        return True

    monkeypatch.setattr(bf, "_pull_root_year", _blocking_pull)
    outcome: dict = {}

    def _run_backfill():
        outcome["rc"] = bf.main()

    t = threading.Thread(target=_run_backfill)
    t.start()
    assert hold_gate.wait(timeout=10), "backfill never reached its lock-holding pull"
    with topup._writer_lock(store) as acquired2:
        assert acquired2 is False   # topup refused while backfill's REAL lock site holds
    release_gate.set()
    t.join(timeout=10)
    assert outcome["rc"] == 0


def test_sigkill_then_next_invocation_acquires_cleanly(store):
    """A held flock dies with the process (fd close) — simulate by simply
    releasing without an explicit unlock (process death behaves the same:
    the OS reclaims the fd on process exit)."""
    store.mkdir(parents=True)
    fh = open(store / topup.WRITER_LOCK_NAME, "a+")
    import fcntl
    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    fh.close()   # simulates process death — fd closes, lock releases
    with topup._writer_lock(store) as acquired:
        assert acquired is True


# ── RF5 (R3): pgrep breadcrumb is ADVISORY ONLY in --daily (F7) ────────────
def test_rf5_backfill_running_advisory_warns_but_never_refuses(store, monkeypatch, caplog):
    _wire_daily(monkeypatch, store, t1=["SPY"], ad=["SPY"])
    fake = FakeTd()
    _install_fake_td(monkeypatch, fake)
    monkeypatch.setattr(topup, "_backfill_running", lambda: True)
    with caplog.at_level("WARNING"):
        rc = topup._daily_main(workers=1, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                               now_fn=lambda: _et(2026, 8, 19, 16, 30))
    assert rc == 0   # never refuses on pgrep alone
    receipt = _manifest(store)["daily_refresh"]
    assert receipt["status"] == "healthy"   # the run actually completed
    assert any("advisory" in rec.message for rec in caplog.records)


def test_rf5_backfill_not_running_no_advisory_warning(store, monkeypatch, caplog):
    _wire_daily(monkeypatch, store, t1=["SPY"], ad=["SPY"])
    fake = FakeTd()
    _install_fake_td(monkeypatch, fake)
    monkeypatch.setattr(topup, "_backfill_running", lambda: False)
    with caplog.at_level("WARNING"):
        topup._daily_main(workers=1, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                          now_fn=lambda: _et(2026, 8, 19, 16, 30))
    assert not any("advisory" in rec.message for rec in caplog.records)


def test_f9_stale_tmp_sweep_counts_and_removes(store):
    (store / "eod" / "SPY").mkdir(parents=True)
    (store / "eod" / "SPY" / "2026.tmp.parquet").write_bytes(b"stale-old-shape")
    (store / "oi" / "AAPL").mkdir(parents=True)
    (store / "oi" / "AAPL" / "2026.parquet.tmp").write_bytes(b"stale-new-shape")
    n = topup._sweep_stale_tmp(store)
    assert n == 2
    assert not (store / "eod" / "SPY" / "2026.tmp.parquet").exists()
    assert not (store / "oi" / "AAPL" / "2026.parquet.tmp").exists()


def test_rf9_sweep_also_covers_store_root_tmp_receipt_files(store):
    """(RF9, R3) A SIGKILL mid `_manifest.json.tmp` write leaves a tmp file
    at the STORE ROOT, not under a tier dir — the sweep must reach it too."""
    store.mkdir(parents=True)
    (store / "_manifest.json.tmp").write_bytes(b"partial receipt write")
    (store / "_manifest.json").write_text('{"daily_refresh": {}}')
    n = topup._sweep_stale_tmp(store)
    assert n == 1
    assert not (store / "_manifest.json.tmp").exists()
    assert (store / "_manifest.json").exists()   # the real manifest is untouched


def test_rf9_publish_r2_excludes_any_tmp_suffixed_file(tmp_path):
    from scripts.publish_r2 import _uploadable
    base = tmp_path
    (base / "_manifest.json").write_text("{}")
    (base / "_manifest.json.tmp").write_text("partial")
    (base / "eod").mkdir()
    (base / "eod" / "keep.parquet").write_text("x")
    (base / "eod" / "2026.parquet.tmp").write_text("partial-parquet")
    files = [base / "_manifest.json", base / "_manifest.json.tmp",
            base / "eod" / "keep.parquet", base / "eod" / "2026.parquet.tmp"]
    kept = _uploadable("thetadata_eod", base, files)
    assert base / "eod" / "keep.parquet" in kept
    assert base / "_manifest.json.tmp" not in kept
    assert base / "eod" / "2026.parquet.tmp" not in kept
    assert base / "_manifest.json" not in kept   # pre-existing exclusion, unaffected


def test_f9_sweep_glob_test_no_reader_glob_matches_tmp_shape(tmp_path):
    dest = tmp_path / "2026.parquet"
    tmp = topup._tmp_path(dest)
    # engine/thetadata_store.py's reader glob is literally "*.parquet"
    import fnmatch
    assert not fnmatch.fnmatch(tmp.name, "*.parquet")


def test_one_root_vendor_failure_isolates_corrupt_parquet(store):
    d = store / "eod" / "SPY"
    d.mkdir(parents=True)
    (d / f"{S_MID.year}.parquet").write_bytes(b"not a parquet file (corrupt)")
    fake = FakeTd()
    result_bad = topup._ensure_daily_root(store, "SPY", S_MID, D_MID, fake)
    assert result_bad.state == "failed"
    assert result_bad.failure_reason is not None
    result_ok = topup._ensure_daily_root(store, "QQQ", S_MID, D_MID, fake)
    assert result_ok.state == "complete"


def test_one_tier_failure_makes_root_partial(store):
    plan = {("greeks", "SPY", S_MID): _empty_df()}
    fake = FakeTd(plan=plan)
    result = topup._ensure_daily_root(store, "SPY", S_MID, D_MID, fake)
    assert result.state == "partial"


# ── Fable ruling 2026-08-22: aggregate ladder binding constraints ──────────
# 1. complete ONLY if all four cells present post-run.
# 2. already_present ONLY if all four cells were present pre-run (zero calls).
# 3. ANY cell-level failure means NOT complete — ever.
def test_ladder_three_complete_one_fetch_failed_never_complete():
    cells = {"eod_S": "complete", "oi_S": "complete",
            "oi_D": "complete", "greeks_S": "fetch_failed"}
    state = topup._classify_root_state(cells)
    assert state != "complete"
    assert state == "fetch_failed"


def test_ladder_three_complete_one_date_unresolved_never_complete():
    cells = {"eod_S": "complete", "oi_S": "complete",
            "oi_D": "complete", "greeks_S": "date_unresolved"}
    state = topup._classify_root_state(cells)
    assert state != "complete"
    assert state == "date_unresolved"


def test_ladder_three_complete_one_vendor_empty_is_partial_never_complete():
    cells = {"eod_S": "complete", "oi_S": "complete",
            "oi_D": "complete", "greeks_S": "vendor_empty"}
    state = topup._classify_root_state(cells)
    assert state != "complete"
    assert state == "partial"


def test_ladder_all_four_vendor_empty_is_vendor_empty():
    cells = {k: "vendor_empty" for k in ("eod_S", "oi_S", "oi_D", "greeks_S")}
    assert topup._classify_root_state(cells) == "vendor_empty"


def test_ladder_all_four_complete_post_run_is_complete():
    cells = {k: "complete" for k in ("eod_S", "oi_S", "oi_D", "greeks_S")}
    assert topup._classify_root_state(cells) == "complete"


def test_ladder_mixed_present_states_is_complete_not_already_present():
    """3 already_present + 1 freshly-fetched complete: all four ARE present,
    but NOT all pre-run — so already_present's zero-vendor-calls guarantee
    must not apply. This is `complete`, not `already_present`."""
    cells = {"eod_S": "already_present", "oi_S": "already_present",
            "oi_D": "already_present", "greeks_S": "complete"}
    assert topup._classify_root_state(cells) == "complete"


def test_ladder_all_four_already_present_pre_run_is_already_present():
    cells = {k: "already_present" for k in ("eod_S", "oi_S", "oi_D", "greeks_S")}
    assert topup._classify_root_state(cells) == "already_present"


def test_ladder_fetch_failed_outranks_date_unresolved():
    cells = {"eod_S": "fetch_failed", "oi_S": "date_unresolved",
            "oi_D": "complete", "greeks_S": "complete"}
    assert topup._classify_root_state(cells) == "fetch_failed"


def test_unrelated_dates_byte_preserved_after_daily_merge(store):
    other_day = date(2026, 8, 3)
    topup._merge_day(store, "eod", "SPY", other_day, _df(other_day, n=4))
    before = pd.read_parquet(store / "eod" / "SPY" / "2026.parquet")
    fake = FakeTd()
    topup._ensure_daily_root(store, "SPY", S_MID, D_MID, fake)
    after = pd.read_parquet(store / "eod" / "SPY" / "2026.parquet")
    before_other = before[pd.to_datetime(before["date"]).dt.date == other_day]
    after_other = after[pd.to_datetime(after["date"]).dt.date == other_day]
    pd.testing.assert_frame_equal(
        before_other.reset_index(drop=True), after_other.reset_index(drop=True))


def test_f15_writer_lock_excluded_from_uploadable(tmp_path):
    from scripts.publish_r2 import _uploadable
    base = tmp_path
    (base / "_manifest.json").write_text("{}")
    (base / "_writer.lock").write_text("")
    (base / "eod").mkdir()
    (base / "eod" / "keep.parquet").write_text("x")
    files = [base / "_manifest.json", base / "_writer.lock", base / "eod" / "keep.parquet"]
    kept = _uploadable("thetadata_eod", base, files)
    assert base / "_writer.lock" not in kept
    assert base / "_manifest.json" not in kept
    assert base / "eod" / "keep.parquet" in kept


def test_f15_writer_lock_gitignored():
    text = (REPO_ROOT / ".gitignore").read_text()
    assert "data/thetadata_eod/_writer.lock" in text


# ═════════════════════════ UNIVERSE (F5/F6) ═════════════════════════════════
def test_symbol_added_to_resolver_changes_denominator(store, monkeypatch):
    _wire_daily(monkeypatch, store, t1=["SPY"], ad=["SPY"])
    fake = FakeTd()
    _install_fake_td(monkeypatch, fake)
    topup._daily_main(workers=1, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                      now_fn=lambda: _et(2026, 8, 19, 16, 30))
    r1 = _manifest(store)["daily_refresh"]
    assert r1["t1_universe_count"] == 1
    assert r1["ad_universe_count"] == 1

    _wire_daily(monkeypatch, store, t1=["SPY", "QQQ"], ad=["SPY", "QQQ"])
    topup._daily_main(workers=1, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                      now_fn=lambda: _et(2026, 8, 19, 16, 30))
    r2 = _manifest(store)["daily_refresh"]
    assert r2["t1_universe_count"] == 2
    assert r2["ad_universe_count"] == 2


def test_root_with_no_options_vendor_empty_run_continues(store, monkeypatch):
    """ZZZZ has no options at all (every tier vendor-empty) — the run must
    continue and finish SPY normally rather than aborting. ZZZZ is deliberately
    OUTSIDE the AD universe here (a T1-only root, like the index roots) so the
    assertion isolates "does the run survive a hopeless root" from the
    separate 90%-gate math (covered by the receipt-family tests)."""
    plan = {(t, "ZZZZ", d): _empty_df()
           for t in ("eod", "oi", "greeks") for d in (S_MID, D_MID)}
    _wire_daily(monkeypatch, store, t1=["ZZZZ", "SPY"], ad=["SPY"])
    fake = FakeTd(plan=plan, snapshot_plan={"ZZZZ": _empty_df()})
    _install_fake_td(monkeypatch, fake)
    rc = topup._daily_main(workers=2, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                           now_fn=lambda: _et(2026, 8, 19, 16, 30))
    receipt = _manifest(store)["daily_refresh"]
    assert receipt["status"] == "healthy"   # SPY alone clears the AD gate
    assert receipt["t1_universe_count"] == 2
    assert receipt["complete_t1_roots"] == 1   # ZZZZ never completes
    assert receipt["s_panel_ad_roots"] == 1
    assert receipt["ad_ready_roots"] == 1


def test_f6_date_unresolved_distinct_from_vendor_empty(store):
    plan = {("eod", "SPY", S_MID): _wrong_date_df(S_MID, date(2026, 8, 17))}
    fake = FakeTd(plan=plan)
    result = topup._ensure_daily_root(store, "SPY", S_MID, D_MID, fake)
    assert result.cells["eod_S"] == "date_unresolved"
    assert result.state == "date_unresolved"


def test_f5_fetch_failed_over_25pct_triggers_reprobe_and_aborts(store, monkeypatch):
    plan = {("eod", r, S_MID): None for r in ["A", "B", "C"]}
    fake = FakeTd(plan=plan, reachable_sequence=[True, False])
    _wire_daily(monkeypatch, store, t1=["A", "B", "C", "D"], ad=["A", "B", "C", "D"])
    _install_fake_td(monkeypatch, fake)
    rc = topup._daily_main(workers=1, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                           now_fn=lambda: _et(2026, 8, 19, 16, 30))
    assert rc == 1
    receipt = _manifest(store)["daily_refresh"]
    assert receipt["status"] == "failed"
    assert receipt["terminal_health"] == "lost_mid_run"


def test_rf12_terminal_lost_gathers_already_completed_futures_unit():
    """(RF12, R3) Unit-level pin of the finally-branch shape: a future that
    is ALREADY done() at the moment terminal_lost_mid_run fires must have
    its result recorded, never silently discarded by a blind cancel()."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as ex:
        fut_done = ex.submit(lambda: topup.RootResult(root="DONE", state="complete"))
        fut_done.result()   # block until actually finished: fut_done.done() is True
        fut_pending = ex.submit(lambda: __import__("time").sleep(5))
        in_flight = {fut_done: "DONE", fut_pending: "PENDING"}
        results: dict = {}

        def _record(fut, root):
            results[root] = fut.result()

        # Mirrors _run_daily_pool's terminal_lost_mid_run finally-branch.
        for f in list(in_flight):
            if f.done():
                _record(f, in_flight[f])
            else:
                f.cancel()
        assert "DONE" in results
        assert results["DONE"].state == "complete"
        assert "PENDING" not in results
        fut_pending.cancel()


def test_rf12_terminal_lost_mid_run_gathers_already_completed_work(store, monkeypatch):
    """(RF12, R3) Integration-level pin: SLOW completes DURING the gap
    between the reprobe decision and the cancel sweep (the re-probe is
    deliberately slower than SLOW) — its result must survive into the
    receipt's counts, not vanish because the run aborted."""
    import time as _time

    def _slow_ok(_day):
        _time.sleep(0.05)
        return _df(S_MID)

    plan = {
        ("eod", "A", S_MID): None, ("eod", "B", S_MID): None, ("eod", "C", S_MID): None,
        ("eod", "SLOW", S_MID): _slow_ok,
    }
    fake = FakeTd(plan=plan, reachable_sequence=[True])
    _orig_reachable = fake.reachable

    def _reachable_delayed_false():
        if fake._reachable_seq:
            return _orig_reachable()
        _time.sleep(0.3)   # >> SLOW's 0.05s — guarantees SLOW finishes first
        return False

    fake.reachable = _reachable_delayed_false
    _wire_daily(monkeypatch, store, t1=["A", "B", "C", "SLOW"], ad=["SLOW"])
    _install_fake_td(monkeypatch, fake)
    rc = topup._daily_main(workers=4, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                           now_fn=lambda: _et(2026, 8, 19, 16, 30))
    assert rc == 1
    receipt = _manifest(store)["daily_refresh"]
    assert receipt["status"] == "failed"
    assert receipt["terminal_health"] == "lost_mid_run"
    # SLOW's completed EOD[S] cell must be counted, not vanished.
    assert receipt["eod_S_roots"] >= 1


def test_f5_fetch_failed_over_25pct_but_reachable_continues(store, monkeypatch):
    plan = {("eod", r, S_MID): None for r in ["A"]}
    fake = FakeTd(plan=plan, reachable_sequence=[True, True])
    _wire_daily(monkeypatch, store, t1=["A", "B"], ad=["A", "B"])
    _install_fake_td(monkeypatch, fake)
    rc = topup._daily_main(workers=1, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                           now_fn=lambda: _et(2026, 8, 19, 16, 30))
    receipt = _manifest(store)["daily_refresh"]
    assert receipt["status"] != "failed"


def test_denominator_has_no_hardcoded_universe_size():
    import inspect
    src = inspect.getsource(topup)
    for lit in ("375", "378"):
        assert lit not in src, f"found hard-coded universe literal {lit!r} in topup module"


# ── Live-flow anchor retention (native resolver regression) ─────────────────
def test_daily_universe_keeps_live_flow_anchor_etfs_exactly_once(monkeypatch):
    """Live-flow commodity/rate anchors survive the native daily resolver,
    including case-normalized duplicates from the independently owned basket.
    Existing index and basket members retain their first-seen ordering.
    """
    monkeypatch.setattr("engine.options_universe.gex_symbols",
                        lambda: ["gld", "AAPL", "MSFT", "SPY"])
    roots = topup._daily_universe()
    for root in ("GLD", "SLV", "TLT", "HYG", "SPY", "SPX", "SPXW", "AAPL", "MSFT"):
        assert roots.count(root) == 1
    assert roots.index("HYG") < roots.index("SPX") < roots.index("SPXW")
    assert roots.index("SPXW") < roots.index("AAPL") < roots.index("MSFT")


# ═════════════════════════ DEADLINE (F2) ════════════════════════════════════
def test_deadline_exceeded_stops_new_dispatch_and_drains(store, monkeypatch):
    import time as _time

    def slow_call(kind_root_day):
        _time.sleep(0.3)

    plan = {}
    slow_roots = ["R1", "R2", "R3", "R4", "R5"]

    def _mk(day):
        def _v(_day):
            _time.sleep(0.3)
            return _df(day)
        return _v

    for r in slow_roots:
        for tier in ("eod", "oi", "greeks"):
            plan[(tier, r, S_MID)] = _mk(S_MID)
            plan[(tier, r, D_MID)] = _mk(D_MID)

    fake = FakeTd(plan=plan)
    ctx = topup.RunContext(D=D_MID, S=S_MID, forced=False)
    results, deadline_exceeded, terminal_lost = topup._run_daily_pool(
        store, slow_roots, fake, workers=1, deadline_min=0.005, ctx=ctx)
    assert deadline_exceeded is True
    assert terminal_lost is False
    assert len(results) < len(slow_roots)


def test_deadline_writes_partial_receipt_with_flag(store, monkeypatch):
    import time as _time

    def _mk(day):
        def _v(_day):
            _time.sleep(0.2)
            return _df(day)
        return _v

    roots = ["R1", "R2", "R3"]
    plan = {}
    for r in roots:
        for tier in ("eod", "oi", "greeks"):
            plan[(tier, r, S_MID)] = _mk(S_MID)
            plan[(tier, r, D_MID)] = _mk(D_MID)
    _wire_daily(monkeypatch, store, t1=roots, ad=roots)
    fake = FakeTd(plan=plan)
    _install_fake_td(monkeypatch, fake)
    rc = topup._daily_main(workers=1, deadline_min=0.004, forced=False,
                           now_fn=lambda: _et(2026, 8, 19, 16, 30))
    receipt = _manifest(store)["daily_refresh"]
    assert receipt["deadline_exceeded"] is True
    assert receipt["status"] in ("partial", "failed")
    assert rc == 1


# ── RF7 (R3): default deadline fits inside the plist's fire spacing ────────
def test_rf7_default_deadline_is_65_minutes():
    assert topup._DEFAULT_DEADLINE_MIN == 65


def test_rf7_default_deadline_fits_under_minimum_fire_spacing():
    """The plist's four fire points are >=70 min apart (§E: 13:20/14:30/16:00/
    18:00 PT — the tightest gap is 70 min). A held lock must release before
    the NEXT fire or that rung of the retry ladder is silently swallowed."""
    fire_points_minutes = [13 * 60 + 20, 14 * 60 + 30, 16 * 60 + 0, 18 * 60 + 0]
    gaps = [b - a for a, b in zip(fire_points_minutes, fire_points_minutes[1:])]
    assert min(gaps) == 70
    assert topup._DEFAULT_DEADLINE_MIN < min(gaps)


# ── RF2 (R3): deadline_exceeded FORCES partial, even at high coverage ──────
def test_rf2_deadline_exceeded_forces_partial_even_at_full_coverage(store, monkeypatch):
    """Falsified by the reviewer: 95%+ coverage + a tripped deadline used to
    stamp `healthy`/rc=0. Construct a fixture where ALL roots complete (100%
    AD coverage) inside the SAME pool call that also trips deadline_exceeded
    (workers == root count, so every root is primed before the deadline is
    even checked; deadline_min is already-expired so the very first
    completion check trips it) — status must be exactly "partial", never
    "healthy", and rc must be 1."""
    roots = ["SPY", "QQQ"]
    _wire_daily(monkeypatch, store, t1=roots, ad=roots)
    fake = FakeTd()   # instant, all-complete responses
    _install_fake_td(monkeypatch, fake)
    rc = topup._daily_main(workers=len(roots), deadline_min=0.00001, forced=False,
                           now_fn=lambda: _et(2026, 8, 19, 16, 30))
    receipt = _manifest(store)["daily_refresh"]
    assert receipt["ad_ready_coverage_pct"] == 1.0
    assert receipt["deadline_exceeded"] is True
    assert receipt["status"] == "partial"
    assert receipt["status"] != "healthy"
    assert rc == 1


# ═════════════════════════ COMPATIBILITY ════════════════════════════════════
def test_legacy_characterization_suite_is_unmodified_by_daily_mode(store, monkeypatch):
    """--daily and legacy --roots don't share mutable module state."""
    monkeypatch.setattr(topup, "resolve_thetadata_store", lambda **kw: str(store))
    monkeypatch.setattr(topup, "_backfill_running", lambda: False)
    fake = FakeTd(plan={})
    import collectors.thetadata as real_td
    monkeypatch.setattr(real_td, "reachable", lambda: True)
    monkeypatch.setattr(real_td, "bulk_eod", lambda root, exp, s, e: _df(s))
    monkeypatch.setattr(real_td, "bulk_open_interest", lambda root, exp, s, e: _df(s))
    monkeypatch.setattr(real_td, "bulk_greeks", lambda root, exp, s, e, order=3: _df(s))
    rc = topup.main(["--roots", "SPY", "--date", "2026-08-18"])
    assert rc == 0


def test_at_universe_resolves_via_resolve_universe_and_applies_3tier(store, monkeypatch):
    monkeypatch.setattr(topup, "resolve_thetadata_store", lambda **kw: str(store))
    monkeypatch.setattr(topup, "_backfill_running", lambda: False)
    monkeypatch.setattr("scripts.backfill_thetadata_eod._resolve_universe",
                        lambda: ["SPY", "QQQ"])
    import collectors.thetadata as real_td
    monkeypatch.setattr(real_td, "reachable", lambda: True)
    monkeypatch.setattr(real_td, "bulk_eod", lambda root, exp, s, e: _df(s))
    monkeypatch.setattr(real_td, "bulk_open_interest", lambda root, exp, s, e: _df(s))
    monkeypatch.setattr(real_td, "bulk_greeks", lambda root, exp, s, e, order=3: _df(s))
    rc = topup.main(["--roots", "@universe", "--date", "2026-08-18"])
    assert rc == 0
    assert topup._has_day(store, "eod", "SPY", date(2026, 8, 18))
    assert topup._has_day(store, "eod", "QQQ", date(2026, 8, 18))


# ═════════════════════════ RECEIPT (F1/F8/F16) ══════════════════════════════
def test_receipt_healthy_when_coverage_meets_gate(store, monkeypatch):
    _wire_daily(monkeypatch, store, t1=["SPY", "QQQ"], ad=["SPY", "QQQ"])
    fake = FakeTd()
    _install_fake_td(monkeypatch, fake)
    rc = topup._daily_main(workers=2, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                           now_fn=lambda: _et(2026, 8, 19, 16, 30))
    receipt = _manifest(store)["daily_refresh"]
    assert receipt["status"] == "healthy"
    assert rc == 0


def test_receipt_partial_when_s_panel_short(store, monkeypatch):
    plan = {("eod", "QQQ", S_MID): None}
    _wire_daily(monkeypatch, store, t1=["SPY", "QQQ"], ad=["SPY", "QQQ"])
    fake = FakeTd(plan=plan)
    _install_fake_td(monkeypatch, fake)
    rc = topup._daily_main(workers=2, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                           now_fn=lambda: _et(2026, 8, 19, 16, 30))
    receipt = _manifest(store)["daily_refresh"]
    assert receipt["status"] == "partial"
    assert rc == 1


def test_receipt_threshold_imported_from_engine_flip(store, monkeypatch):
    _wire_daily(monkeypatch, store, t1=["SPY", "QQQ"], ad=["SPY", "QQQ"])
    plan = {("eod", "QQQ", S_MID): None}   # only 1/2 = 50% AD coverage
    fake = FakeTd(plan=plan)
    _install_fake_td(monkeypatch, fake)

    from engine.options_intel_brief import CONFIG
    monkeypatch.setitem(CONFIG, "SOURCE_COVERAGE_GATE", 0.40)
    rc = topup._daily_main(workers=2, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                           now_fn=lambda: _et(2026, 8, 19, 16, 30))
    receipt = _manifest(store)["daily_refresh"]
    assert receipt["status"] == "healthy"   # 0.50 >= lowered 0.40 gate


def test_forced_stamps_forced_true(store, monkeypatch):
    # Saturday 2026-08-22 forced -> D = last_session_on_or_before == the
    # prior Friday (see test_forced_on_non_session_day_derives_last_session
    # _on_or_before) — the fake's default_D must match, or its snapshot
    # (D_MID by default) misclassifies oi_D as date_unresolved and this
    # run would never reach `healthy`.
    forced_d = nc.last_session_on_or_before(date(2026, 8, 22))
    _wire_daily(monkeypatch, store, t1=["SPY"], ad=["SPY"])
    fake = FakeTd(default_D=forced_d)
    _install_fake_td(monkeypatch, fake)
    rc = topup._daily_main(workers=1, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=True,
                           now_fn=lambda: _et(2026, 8, 22, 12, 0))   # Saturday
    receipt = _manifest(store)["daily_refresh"]
    assert receipt["forced"] is True
    assert receipt["status"] == "healthy"
    assert rc == 0


# ── Fable ruling 2026-08-22: forced-mode non-session fallback (ACCEPTED) ───
def test_forced_on_non_session_day_derives_last_session_on_or_before():
    """--force-run on a non-session day (Saturday 2026-08-22) derives
    D = last_session_on_or_before(today_et) = the prior Friday, and S = the
    session before THAT — never today_et itself (which is not a session)."""
    saturday = _et(2026, 8, 22, 12, 0)
    ctx = topup._resolve_daily_context(saturday, forced=True)
    assert ctx is not None
    assert ctx.forced is True
    assert ctx.D == nc.last_session_on_or_before(date(2026, 8, 22))
    assert ctx.D == date(2026, 8, 21)   # the Friday before
    assert ctx.S == nc.session_n_back(ctx.D, 1)


def test_forced_on_a_session_day_still_uses_today_as_d():
    """forced on an ALREADY-open session day changes nothing about D — only
    the gate/time check is bypassed."""
    ctx = topup._resolve_daily_context(_et(2026, 8, 19, 10, 0), forced=True)
    assert ctx.D == D_MID
    assert ctx.S == S_MID


# ── Fable ruling 2026-08-22: exit-code quadruple (ACCEPTED, pinned) ─────────
def test_daily_exit_code_quadruple_pinned(store, monkeypatch):
    """--daily exits 0 for {healthy, gate no-op, lock refusal}, 1 for
    {partial, failed} — pinned as one quadruple so it cannot silently drift."""
    # healthy -> 0
    _wire_daily(monkeypatch, store, t1=["SPY"], ad=["SPY"])
    fake = FakeTd()
    _install_fake_td(monkeypatch, fake)
    rc_healthy = topup._daily_main(workers=1, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                                   now_fn=lambda: _et(2026, 8, 19, 16, 30))
    assert rc_healthy == 0
    assert _manifest(store)["daily_refresh"]["status"] == "healthy"

    # gate no-op -> 0 (Saturday, not forced)
    rc_noop = topup._daily_main(workers=1, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                                now_fn=lambda: _et(2026, 8, 22, 12, 0))
    assert rc_noop == 0

    # lock refusal -> 0
    store.mkdir(parents=True, exist_ok=True)
    with topup._writer_lock(store):
        rc_locked = topup._daily_main(workers=1, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                                      now_fn=lambda: _et(2026, 8, 20, 16, 30))
    assert rc_locked == 0

    # partial -> 1
    plan_partial = {("eod", "QQQ", date(2026, 8, 21)): None}
    _wire_daily(monkeypatch, store, t1=["SPY", "QQQ"], ad=["SPY", "QQQ"])
    fake_partial = FakeTd(plan=plan_partial, default_D=D_MON)
    _install_fake_td(monkeypatch, fake_partial)
    rc_partial = topup._daily_main(workers=2, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                                   now_fn=lambda: _et(2026, 8, 24, 16, 30))  # Mon
    assert rc_partial == 1
    assert _manifest(store)["daily_refresh"]["status"] == "partial"

    # failed -> 1 (terminal unreachable)
    fake_failed = FakeTd()
    fake_failed._reachable_default = False
    _install_fake_td(monkeypatch, fake_failed)
    rc_failed = topup._daily_main(workers=1, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                                  now_fn=lambda: _et(2026, 8, 25, 16, 30))  # Tue
    assert rc_failed == 1
    assert _manifest(store)["daily_refresh"]["status"] == "failed"


def test_manifest_write_is_atomic_no_tmp_left_behind(store, monkeypatch):
    _wire_daily(monkeypatch, store, t1=["SPY"], ad=["SPY"])
    fake = FakeTd()
    _install_fake_td(monkeypatch, fake)
    topup._daily_main(workers=1, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                      now_fn=lambda: _et(2026, 8, 19, 16, 30))
    assert not (store / "_manifest.json.tmp").exists()
    assert (store / "_manifest.json").exists()


def test_backfill_manifest_rewrite_preserves_daily_refresh(store, monkeypatch):
    import scripts.backfill_thetadata_eod as bf
    monkeypatch.setattr(bf, "_manifest_path", lambda: store / "_manifest.json")
    store.mkdir(parents=True)
    (store / "_manifest.json").write_text(json.dumps({
        "daily_refresh": {"S": "2026-08-18", "D": "2026-08-19", "status": "healthy"},
    }))
    bf._write_manifest({"completed": {"SPY": ["2026"]}})
    doc = _manifest(store)
    assert doc["daily_refresh"]["D"] == "2026-08-19"
    assert doc["n_roots"] == 1


def test_backfill_manifest_rewrite_preservation_flip_would_fail():
    """Flip test: an implementation that full-REPLACES (the old behavior)
    would drop daily_refresh — pin the read-modify-write directly."""
    import inspect
    import scripts.backfill_thetadata_eod as bf
    src = inspect.getsource(bf._write_manifest)
    assert "preserved" in src or "read" in src.lower()


def test_f16_corrupt_manifest_fail_open_daily(store, monkeypatch, caplog):
    store.mkdir(parents=True)
    (store / "_manifest.json").write_text("{not valid json")
    _wire_daily(monkeypatch, store, t1=["SPY"], ad=["SPY"])
    fake = FakeTd()
    _install_fake_td(monkeypatch, fake)
    rc = topup._daily_main(workers=1, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                           now_fn=lambda: _et(2026, 8, 19, 16, 30))
    assert rc == 0
    doc = _manifest(store)
    assert doc["daily_refresh"]["status"] == "healthy"


def test_f16_corrupt_manifest_fail_open_backfill(store):
    import scripts.backfill_thetadata_eod as bf
    store.mkdir(parents=True)
    (store / "_manifest.json").write_text("{not valid json")
    import unittest.mock as mock
    with mock.patch.object(bf, "_manifest_path", return_value=store / "_manifest.json"):
        bf._write_manifest({"completed": {}})
    doc = _manifest(store)
    assert doc["n_roots"] == 0


def test_sentinel_script_mentions_daily_refresh_and_session_date():
    text = SENTINEL_SH.read_text()
    assert "daily_refresh" in text
    assert "session_date" in text


def _run_sentinel(*, now_utc_iso: str, manifest_d: str, tmp_path,
                  repo_root: str | None = None, cwd: str | None = None,
                  status: str = "healthy", forced: bool = False):
    """Invoke the REAL sentinel script (RF1, R3 — computed, not grep-only)
    with its test seams: SENTINEL_NOW_UTC overrides the wall clock, STORE
    points at a crafted tmp store, HEALTH_URL points at a closed port so the
    terminal-health curl fails fast instead of a 6s timeout. `repo_root`
    (N3) lets a test inject a broken REPO_ROOT to force the
    `from lib import nyse_calendar` import to fail; `cwd` closes the loophole
    where python's stdin-script sys.path[0] (the process cwd) would
    otherwise still resolve `lib` regardless of REPO_ROOT. `status`/`forced`
    (K4, Sol B3) default to the normal production-healthy shape — a test
    exercising the health/forced anchor conditions overrides one."""
    store = tmp_path / "store"
    (store / "greeks" / "SPY").mkdir(parents=True)
    (store / "_manifest.json").write_text(json.dumps(
        {"daily_refresh": {"D": manifest_d, "S": "2026-08-18",
                           "status": status, "forced": forced}}))
    pd.DataFrame({"date": [pd.Timestamp("2026-08-19")], "x": [1]}).to_parquet(
        store / "greeks" / "SPY" / "2026.parquet")
    env = {
        "STORE": str(store),
        "HEALTH_URL": "http://127.0.0.1:1/unreachable",
        "SENTINEL_NOW_UTC": now_utc_iso,
        "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
        "HOME": str(tmp_path),
    }
    if repo_root is not None:
        env["REPO_ROOT"] = repo_root
    # OUT_JSON/LOG are not env-overridable in the script (production paths
    # are the fixed /tmp files below) — read the script's real /tmp output;
    # safe here because the assertion is on daily_refresh_anchor_due, a pure
    # function of NOW/D that doesn't depend on any other concurrent writer.
    result = subprocess.run(
        ["bash", str(SENTINEL_SH), "--due-today"],
        env=env, cwd=cwd, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    return json.loads(Path("/tmp/theta_staleness.json").read_text())


def test_rf1_anchor_not_due_at_morning_fire_0615_pt(tmp_path):
    # 06:15 PT (PDT, UTC-7) on session Wed 2026-08-19 = 13:15 UTC = 09:15 ET.
    verdict = _run_sentinel(now_utc_iso="2026-08-19T13:15:00+00:00",
                            manifest_d="2026-08-19", tmp_path=tmp_path)
    assert verdict["daily_refresh_anchor_due"] is False


def test_rf1_anchor_due_at_evening_fire_1830_pt_session_day(tmp_path):
    # 18:30 PT (PDT, UTC-7) on session Wed 2026-08-19 = 01:30 UTC next day
    # = 21:30 ET — still the 08-19 ET calendar day, after the new 20:00 gate.
    verdict = _run_sentinel(now_utc_iso="2026-08-20T01:30:00+00:00",
                            manifest_d="2026-08-19", tmp_path=tmp_path)
    assert verdict["daily_refresh_anchor_due"] is True
    assert verdict["daily_refresh_expected"] == "2026-08-19"


def test_rf1_anchor_due_and_stale_alerts(tmp_path):
    """The evening fire with a STALE daily_refresh.D (a real miss) must
    ALERT — the anchor check has teeth, not just a flag."""
    verdict = _run_sentinel(now_utc_iso="2026-08-20T01:30:00+00:00",
                            manifest_d="2026-08-18", tmp_path=tmp_path)
    assert verdict["daily_refresh_anchor_due"] is True
    assert verdict["level"] == "ALERT"
    assert any("daily_refresh.D stale" in r for r in verdict["reasons"])


# ── K4 (Sol B3): the anchor validates HEALTH, not only freshness of D ──────
def test_k4_current_d_partial_alerts(tmp_path):
    verdict = _run_sentinel(now_utc_iso="2026-08-20T01:30:00+00:00",
                            manifest_d="2026-08-19", status="partial", forced=False,
                            tmp_path=tmp_path)
    assert verdict["daily_refresh_anchor_due"] is True
    assert verdict["level"] == "ALERT"
    assert verdict["daily_refresh_status"] == "partial"
    assert any("not healthy" in r for r in verdict["reasons"])


def test_k4_current_d_failed_alerts(tmp_path):
    verdict = _run_sentinel(now_utc_iso="2026-08-20T01:30:00+00:00",
                            manifest_d="2026-08-19", status="failed", forced=False,
                            tmp_path=tmp_path)
    assert verdict["daily_refresh_anchor_due"] is True
    assert verdict["level"] == "ALERT"
    assert verdict["daily_refresh_status"] == "failed"
    assert any("not healthy" in r for r in verdict["reasons"])


def test_k4_current_d_healthy_forced_true_alerts(tmp_path):
    """A `forced=true` diagnostic run is not a normal production-healthy
    result — even with status=="healthy" and D current, it must still
    ALERT."""
    verdict = _run_sentinel(now_utc_iso="2026-08-20T01:30:00+00:00",
                            manifest_d="2026-08-19", status="healthy", forced=True,
                            tmp_path=tmp_path)
    assert verdict["daily_refresh_anchor_due"] is True
    assert verdict["level"] == "ALERT"
    assert verdict["daily_refresh_forced"] is True
    assert any("forced=True" in r for r in verdict["reasons"])


def test_k4_current_d_healthy_unforced_no_anchor_alert(tmp_path):
    """The one shape that satisfies the anchor: D current, status healthy,
    forced exactly False — the anchor itself raises no reason (the fixture's
    HEALTH_URL is deliberately unreachable per `_run_sentinel`'s docstring,
    so the OVERALL level still ALERTs on the unrelated terminal-health
    check — this test isolates the anchor's own contribution, not the
    terminal check)."""
    verdict = _run_sentinel(now_utc_iso="2026-08-20T01:30:00+00:00",
                            manifest_d="2026-08-19", status="healthy", forced=False,
                            tmp_path=tmp_path)
    assert verdict["daily_refresh_anchor_due"] is True
    assert verdict["daily_refresh_status"] == "healthy"
    assert verdict["daily_refresh_forced"] is False
    assert not any("K4 anchor" in r for r in verdict["reasons"])
    assert not any("AD-1T1 F8 anchor" in r for r in verdict["reasons"])


def test_n3_broken_calendar_import_alerts_regardless_of_anchor_due(tmp_path):
    """(N3, R3 verify-pass) The pre-N3 shape left `anchor_due` at its False
    default when the calendar import/eval itself raised, so the
    `if anchor_due:` gate was never entered and the failure was invisible —
    the same silent-dead-instrument class RF1 fixed for the threshold.
    Inject a broken REPO_ROOT (and a cwd with no `lib/` package to close the
    stdin-script sys.path[0]-is-cwd loophole) at a time that is NOT anchor-due
    (morning fire) — this must STILL ALERT, proving the fix does not merely
    ride along with the evening-fire case."""
    isolated_cwd = tmp_path / "no_lib_here"
    isolated_cwd.mkdir()
    verdict = _run_sentinel(
        now_utc_iso="2026-08-19T13:15:00+00:00",   # 09:15 ET — NOT due under a working calendar
        manifest_d="2026-08-19", tmp_path=tmp_path,
        repo_root=str(tmp_path / "nonexistent_repo_root"),
        cwd=str(isolated_cwd))
    assert verdict["daily_refresh_anchor_eval_failed"] is True
    assert verdict["level"] == "ALERT"
    assert any("staleness anchor cannot evaluate" in r for r in verdict["reasons"])


def test_n3_working_calendar_import_does_not_report_eval_failed(tmp_path):
    """Sanity converse: a WORKING import never sets the eval-failed flag."""
    verdict = _run_sentinel(now_utc_iso="2026-08-19T13:15:00+00:00",
                            manifest_d="2026-08-19", tmp_path=tmp_path)
    assert verdict["daily_refresh_anchor_eval_failed"] is False


def test_lock_refusal_writes_no_receipt(store, monkeypatch):
    _wire_daily(monkeypatch, store, t1=["SPY"], ad=["SPY"])
    fake = FakeTd()
    _install_fake_td(monkeypatch, fake)
    store.mkdir(parents=True)
    with topup._writer_lock(store):
        topup._daily_main(workers=1, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                          now_fn=lambda: _et(2026, 8, 19, 16, 30))
    assert not (store / "_manifest.json").exists()


def test_gate_no_op_writes_no_receipt(store, monkeypatch):
    _wire_daily(monkeypatch, store, t1=["SPY"], ad=["SPY"])
    fake = FakeTd()
    _install_fake_td(monkeypatch, fake)
    rc = topup._daily_main(workers=1, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                           now_fn=lambda: _et(2026, 8, 22, 12, 0))   # Saturday
    assert rc == 0
    assert not (store / "_manifest.json").exists()


def test_session_resolution_failure_aborts_as_failed(store, monkeypatch):
    _wire_daily(monkeypatch, store, t1=["SPY"], ad=["SPY"])
    fake = FakeTd()
    _install_fake_td(monkeypatch, fake)
    monkeypatch.setattr(nc, "session_n_back", lambda *a, **kw: None)
    rc = topup._daily_main(workers=1, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                           now_fn=lambda: _et(2026, 8, 19, 16, 30))
    assert rc == 1
    receipt = _manifest(store)["daily_refresh"]
    assert receipt["status"] == "failed"


def test_terminal_unreachable_at_startup_aborts_failed(store, monkeypatch):
    _wire_daily(monkeypatch, store, t1=["SPY"], ad=["SPY"])
    fake = FakeTd()
    fake._reachable_default = False
    _install_fake_td(monkeypatch, fake)
    rc = topup._daily_main(workers=1, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                           now_fn=lambda: _et(2026, 8, 19, 16, 30))
    assert rc == 1
    receipt = _manifest(store)["daily_refresh"]
    assert receipt["status"] == "failed"
    assert receipt["terminal_health"] == "unreachable"


# ═══════════════════ K1 (Sol B1a) AD-READY RECEIPT FIELDS ══════════════════
def test_k1_receipt_new_fields_present_and_correct(store, monkeypatch):
    roots = ["SPY", "QQQ", "AAPL"]
    _wire_daily(monkeypatch, store, t1=roots, ad=roots)
    fake = FakeTd()
    _install_fake_td(monkeypatch, fake)
    rc = topup._daily_main(workers=3, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                           now_fn=lambda: _et(2026, 8, 19, 16, 30))
    receipt = _manifest(store)["daily_refresh"]
    assert receipt["s_panel_ad_roots"] == 3
    assert receipt["s_panel_coverage_pct"] == 1.0
    assert receipt["ad_ready_roots"] == 3
    assert receipt["ad_ready_coverage_pct"] == 1.0
    assert receipt["oi_D_source"] == "snapshot_open_interest"
    assert receipt["status"] == "healthy"
    assert rc == 0
    # K1 renamed these fields — the old names must not linger.
    assert "complete_ad_roots" not in receipt
    assert "ad_coverage_pct" not in receipt


def test_k1_s_panel_high_ad_ready_low_is_partial_not_healthy(store, monkeypatch):
    """The exact K1 discriminating fixture: 10 AD roots all clear the
    S-panel (>=90%), but only 8/10 land OI[D] (80% < the 90% gate) — must be
    `partial`, exit 1, even though the OLD (pre-K1) healthy law — keyed on
    the S-panel alone — would have called this `healthy`."""
    roots = [f"R{i}" for i in range(10)]
    short_roots = roots[:2]
    snapshot_plan = {r: _empty_df() for r in short_roots}
    _wire_daily(monkeypatch, store, t1=roots, ad=roots)
    fake = FakeTd(snapshot_plan=snapshot_plan)
    _install_fake_td(monkeypatch, fake)
    rc = topup._daily_main(workers=4, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                           now_fn=lambda: _et(2026, 8, 19, 16, 30))
    receipt = _manifest(store)["daily_refresh"]
    assert receipt["s_panel_coverage_pct"] == 1.0        # old law would be healthy here
    assert receipt["ad_ready_coverage_pct"] == 0.8        # new gate: 8/10 < 0.90
    assert receipt["status"] == "partial"
    assert receipt["status"] != "healthy"
    assert rc == 1


# ── K6 NOTE-1: auditable oi_D_source stamps only on an actual vendor attempt ─
def test_k6_note1_oi_d_source_null_when_all_oi_d_already_present(store, monkeypatch):
    """A same-day rerun where every cell (including oi_D) is already
    satisfied makes ZERO vendor calls at all — `oi_D_source` must not be
    falsely attributed to the snapshot endpoint it never touched this run."""
    for cell_tier, day in (("eod", S_MID), ("oi", S_MID), ("oi", D_MID), ("greeks", S_MID)):
        topup._merge_day(store, cell_tier, "SPY", day, _df(day))
    _wire_daily(monkeypatch, store, t1=["SPY"], ad=["SPY"])
    fake = FakeTd()
    _install_fake_td(monkeypatch, fake)
    rc = topup._daily_main(workers=1, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                           now_fn=lambda: _et(2026, 8, 19, 16, 30))
    assert rc == 0
    assert fake.snapshot_calls == []
    receipt = _manifest(store)["daily_refresh"]
    assert receipt["oi_D_source"] is None


def test_k6_note1_oi_d_source_stamped_when_any_oi_d_vendor_attempt(store, monkeypatch):
    """SPY's oi_D is already satisfied (no vendor attempt); QQQ's oi_D is
    genuinely fetched and comes back vendor_empty — still counted as an
    ATTEMPT per the spec's `{complete, vendor_empty, date_unresolved,
    fetch_failed}` attempt set, so ONE root attempting is enough to stamp
    the path even though the other root made zero vendor calls."""
    topup._merge_day(store, "oi", "SPY", D_MID, _df(D_MID))
    _wire_daily(monkeypatch, store, t1=["SPY", "QQQ"], ad=["SPY", "QQQ"])
    fake = FakeTd(snapshot_plan={"QQQ": _empty_df()})
    _install_fake_td(monkeypatch, fake)
    topup._daily_main(workers=2, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                      now_fn=lambda: _et(2026, 8, 19, 16, 30))
    assert fake.snapshot_calls == ["QQQ"]   # SPY's oi_D never called the vendor
    receipt = _manifest(store)["daily_refresh"]
    assert receipt["oi_D_source"] == "snapshot_open_interest"


# ═════════════════════════ RF3 (R3): backfill/daily store agreement ═══════
def test_rf3_backfill_refuses_when_resolved_store_disagrees(tmp_path, monkeypatch):
    import scripts.backfill_thetadata_eod as bf

    own_store = tmp_path / "own_store"
    other_store = tmp_path / "a_completely_different_store"
    monkeypatch.setattr(bf, "_store_dir", lambda: own_store)
    monkeypatch.setattr(bf, "resolve_thetadata_store", lambda **kw: str(other_store))
    import sys as _sys
    monkeypatch.setattr(_sys, "argv", ["backfill_thetadata_eod.py"])
    import collectors.thetadata as real_td
    monkeypatch.setattr(real_td, "reachable", lambda: True)

    rc = bf.main()
    assert rc == 1
    assert not own_store.exists()   # refused before touching its own store at all
    assert not other_store.exists()


def test_rf3_backfill_permits_fresh_install_when_nothing_resolves(tmp_path, monkeypatch):
    import scripts.backfill_thetadata_eod as bf

    own_store = tmp_path / "own_store"
    monkeypatch.setattr(bf, "_store_dir", lambda: own_store)
    monkeypatch.setattr(bf, "resolve_thetadata_store", lambda **kw: None)   # nothing resolves anywhere
    import sys as _sys
    monkeypatch.setattr(_sys, "argv", ["backfill_thetadata_eod.py", "--dry-run"])
    import collectors.thetadata as real_td
    monkeypatch.setattr(real_td, "reachable", lambda: True)
    monkeypatch.setattr(bf, "_resolve_universe", lambda extra_roots=None: ["SPY"])

    rc = bf.main()
    assert rc == 0   # dry-run proceeds normally past the agreement check


# ── K3 (Sol B2): the store-agreement check fails CLOSED on resolver raise ──
def test_k3_backfill_resolver_raises_fails_closed_zero_mutations(tmp_path, monkeypatch):
    """A resolver RAISE (not a clean fresh-install `None`) is the case this
    check exists to catch — canonical resolution is UNCERTAIN, not
    confirmed absent. Must exit 1 with ZERO mutations, never warn-and-
    proceed with `own_store`.

    (K6 MAJOR-1 repair.) This uses the REAL `_store_dir()` — not a stubbed
    non-mkdir lambda, which would pin a property production code doesn't
    have — seamed only at the path SOURCE `_store_dir()` actually reads
    (`lib.config.data_dir()`). Because `_store_dir()` itself `mkdir`s, the
    only way to prove zero mutations is to diff a full recursive listing of
    the tmp root before and after, not to check a single path's existence.
    """
    import scripts.backfill_thetadata_eod as bf
    from lib import config

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)

    def _boom(**kw):
        raise RuntimeError("resolver blew up")

    monkeypatch.setattr(bf, "resolve_thetadata_store", _boom)
    import sys as _sys
    monkeypatch.setattr(_sys, "argv", ["backfill_thetadata_eod.py"])
    import collectors.thetadata as real_td
    monkeypatch.setattr(real_td, "reachable", lambda: True)

    before = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*"))
    assert before == []   # tmp_path starts empty

    rc = bf.main()

    after = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*"))
    assert rc == 1
    assert after == []   # NOTHING created anywhere under the tmp root — not
                          # even the `thetadata_eod` dir `_store_dir()` mkdirs


def test_k3_backfill_resolver_none_still_proceeds_fresh_install(tmp_path, monkeypatch):
    """Converse pin: a clean `None` return (the resolver genuinely found
    NOTHING anywhere) remains the explicit fresh-install exception — only a
    RAISE fails closed, never a clean None."""
    import scripts.backfill_thetadata_eod as bf

    own_store = tmp_path / "own_store"
    monkeypatch.setattr(bf, "_store_dir", lambda: own_store)
    monkeypatch.setattr(bf, "resolve_thetadata_store", lambda **kw: None)
    import sys as _sys
    monkeypatch.setattr(_sys, "argv", ["backfill_thetadata_eod.py", "--dry-run"])
    import collectors.thetadata as real_td
    monkeypatch.setattr(real_td, "reachable", lambda: True)
    monkeypatch.setattr(bf, "_resolve_universe", lambda extra_roots=None: ["SPY"])

    rc = bf.main()
    assert rc == 0


# ═════════════════════════ HARDENING (R3): lock-open OSError ══════════════
def test_hardening_daily_oserror_opening_lock_is_failed_not_traceback(store, monkeypatch):
    _wire_daily(monkeypatch, store, t1=["SPY"], ad=["SPY"])
    fake = FakeTd()
    _install_fake_td(monkeypatch, fake)

    def _boom(*a, **kw):
        raise OSError(28, "No space left on device")   # ENOSPC

    monkeypatch.setattr(topup, "open", _boom, raising=False)
    rc = topup._daily_main(workers=1, deadline_min=topup._DEFAULT_DEADLINE_MIN, forced=False,
                           now_fn=lambda: _et(2026, 8, 19, 16, 30))
    assert rc == 1
    assert fake.calls == []


def test_hardening_legacy_oserror_opening_lock_is_failed_not_traceback(store, monkeypatch):
    monkeypatch.setattr(topup, "resolve_thetadata_store", lambda **kw: str(store))
    monkeypatch.setattr(topup, "_backfill_running", lambda: False)

    def _boom(*a, **kw):
        raise OSError(30, "Read-only file system")

    monkeypatch.setattr(topup, "open", _boom, raising=False)
    rc = topup.main(["--roots", "SPY", "--date", "2026-08-18"])
    assert rc == 1


def test_hardening_backfill_oserror_opening_lock_is_failed_not_traceback(tmp_path, monkeypatch):
    import scripts.backfill_thetadata_eod as bf

    own_store = tmp_path / "own_store"
    monkeypatch.setattr(bf, "_store_dir", lambda: own_store)
    monkeypatch.setattr(bf, "resolve_thetadata_store", lambda **kw: str(own_store))
    import sys as _sys
    monkeypatch.setattr(_sys, "argv", ["backfill_thetadata_eod.py"])
    import collectors.thetadata as real_td
    monkeypatch.setattr(real_td, "reachable", lambda: True)
    monkeypatch.setattr(bf, "_resolve_universe", lambda extra_roots=None: ["SPY"])

    def _boom(*a, **kw):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(topup, "open", _boom, raising=False)
    rc = bf.main()
    assert rc == 1


@pytest.mark.parametrize('setting,root,expected',[
 ('','SPY',{}),('SPY','SPY',{'version':'1'}),('SPY','QQQ',{}),
 ('SPY, QQQ','QQQ',{'version':'1'}),('SPY,QQQ','AAPL',{})])
def test_dated_version_opt_in_keeps_other_roots_and_default_unchanged(monkeypatch,setting,root,expected):
 monkeypatch.setenv('THETADATA_DATED_GREEKS_V1_ROOTS',setting)
 assert topup._dated_greek_request_options(root)==expected


def test_invalid_dated_version_root_config_stops_before_source_work(monkeypatch):
 monkeypatch.setenv('THETADATA_DATED_GREEKS_V1_ROOTS','SPY,AAPL')
 monkeypatch.setattr(topup,'_daily_main',lambda **kw:pytest.fail('Invalid config reached acquisition'))
 with pytest.raises(SystemExit):topup.main(['--daily'])


@pytest.mark.parametrize('root,expected',[('SPY',{'version':'1'}),('QQQ',{'version':'1'}),('AAPL',{})])
def test_daily_owner_forwards_version_only_for_explicit_opt_in(store,monkeypatch,root,expected):
 monkeypatch.setenv('THETADATA_DATED_GREEKS_V1_ROOTS','SPY,QQQ')
 fake=FakeTd();calls=[]
 def greeks(r,exp,start,end,order=3,**kwargs):
  calls.append(kwargs);return fake._get('greeks',r,start)
 fake.bulk_greeks=greeks
 result=topup._ensure_daily_root(store,root,S_MID,D_MID,fake)
 assert result.state=='complete' and calls==[expected]


# D-session preparation: all acquisitions below are SYNTHETIC STRUCTURAL mocks.
# No current incumbent transport is admitted or enabled by these tests.
def _observation_frame(day, *, oi=False):
    out = pd.DataFrame({'root':['SPY','SPY'], 'expiration':[pd.Timestamp('2027-02-19')]*2,
        'strike':[745.,760.], 'right':['P','P'], 'date':[pd.Timestamp(day)]*2})
    if oi:out['open_interest']=[0,10]
    else:
        out['close']=[2.,3.];out['volume']=[10,20]
        out['gamma']=[-0.01,0.02];out['underlying_price']=[770.,770.]
    return out


@pytest.fixture
def observation_case(tmp_path, monkeypatch):
    from types import SimpleNamespace
    store = tmp_path/'store';store.mkdir();private=tmp_path/'private';private.mkdir()
    for tier,day,frame in [('oi',D_MID,_observation_frame(D_MID,oi=True)),
        ('oi',S_MID,_observation_frame(S_MID,oi=True)),
        ('eod',S_MID,_observation_frame(S_MID)),('greeks',S_MID,_observation_frame(S_MID))]:
        topup._merge_day(store,tier,'SPY',day,frame)
    calls=[];mode={'kind':None};clock={'value':10.}
    monkeypatch.setattr(topup._time,'monotonic',lambda:clock['value'])
    class Transport:
        origin='http://127.0.0.1:25503'
        def __call__(self,kind,**kw):
            from types import SimpleNamespace
            url=self.origin+('/v3/option/history/eod' if kind=='eod' else '/v3/option/history/greeks/eod')
            session=SimpleNamespace(get_adapter=lambda u:SimpleNamespace(max_retries=SimpleNamespace(total=0)))
            kw['request_budget'].begin(session,url)
            # Actual mock transport attempt happens only AFTER durable reservation.
            p=private/f'spy-{D_MID.isoformat()}-1730-observation-v1/receipt.json'
            receipt=json.loads(p.read_text())
            assert receipt['attempts']==len(calls)+1
            assert receipt['requests'][-1]['state']=='REQUEST_STARTED'
            calls.append((kind,kw))
            if mode['kind']=='abrupt':raise KeyboardInterrupt('unreturned request')
            kw['response_handler'](472 if mode['kind']=='refusal' else 200)
            body=b'' if mode['kind']=='raw_empty' else b'synthetic licensed-body substitute, not provider data\n'
            kw['raw_response_handler'](body)
            if mode['kind']=='retry':kw['request_budget'].begin(session,url)
            frame=_observation_frame(D_MID)
            frame.attrs['_bounded_raw_rows']=len(frame)
            import hashlib
            actual=json.loads(p.read_text())['requests'][-1]
            frame.attrs['_d_session_binding']=dict(origin=self.origin,endpoint=actual['endpoint'],
                parameters=actual['parameters'],raw_rows=len(frame),
                payload_sha256=hashlib.sha256(body).hexdigest(),payload_bytes=len(body))
            if mode['kind']=='missing_raw_count':frame.attrs.pop('_bounded_raw_rows')
            if mode['kind']=='raw_row_cap':frame.attrs['_bounded_raw_rows']=100001
            if mode['kind']=='date':frame['date']=pd.Timestamp(S_MID)
            if mode['kind']=='partial' and kind=='greeks':frame=frame.iloc[:1].copy()
            if mode['kind']=='model' and kind=='greeks':frame.attrs['requested_version']='2'
            if mode['kind']=='empty':frame=frame.iloc[:0].copy()
            if mode['kind']=='late':clock['value']=100.
            return frame
    config=topup._DSessionObservation(private,'01a156f1-f450-7793-8951-bddadd4784c2',
        '01a15700-1ae2-7a73-9756-f1546da7ace8',Transport(),session_day=D_MID)
    return SimpleNamespace(store=store,private=private,config=config,calls=calls,mode=mode,clock=clock,
        ctx=topup.RunContext(D_MID,S_MID,False),now=_et(2026,8,19,17,30),
        receipt=private/f'spy-{D_MID.isoformat()}-1730-observation-v1/receipt.json')


def _run_observation(c,**changes):
    return topup._observe_spy_d_session(c.store,changes.get('ctx',c.ctx),changes.get('now',c.now),
        50.,changes.get('config',c.config),request_options=changes.get('options',{'version':'1'}))


def test_d_observation_mock_two_attempts_private_only_and_no_replay(observation_case,monkeypatch):
    import hashlib
    c=observation_case
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in c.store.rglob('*.parquet')}
    monkeypatch.setattr(topup,'_ensure_one_cell',lambda *a,**k:pytest.fail('Pilot canonical ensure'))
    monkeypatch.setattr(topup,'_merge_day',lambda *a,**k:pytest.fail('Pilot canonical merge'))
    out=_run_observation(c)
    assert out['state']=='OBSERVED_COMPLETE' and out['attempts']==2
    assert [k for k,_ in c.calls]==['eod','greeks']
    assert c.calls[1][1]['order']==3 and c.calls[1][1]['request_options']=={'version':'1'}
    receipt=json.loads(c.receipt.read_text())
    assert receipt['first_availability'] is None and receipt['market_universe_complete'] is None
    assert receipt['canonical_writes']==0 and receipt['hub_promotion'] is False
    assert receipt['coverage']['observed_contracts']==2
    assert all(r['sha256'] and r['bytes']>0 and r['parsed_at'] for r in receipt['requests'])
    assert before=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in c.store.rglob('*.parquet')}
    assert _run_observation(c)['reason']=='existing_observation_claim' and len(c.calls)==2


@pytest.mark.parametrize('kind,expected,max_attempts',[('refusal','STOPPED',1),('abrupt','EFFECT_UNKNOWN',1),
    ('retry','STOPPED',1),('date','WITHHELD',2),('partial','WITHHELD',2),
    ('model','STOPPED',2),('empty','STOPPED',1),('raw_empty','STOPPED',1),
    ('missing_raw_count','STOPPED',1),('raw_row_cap','STOPPED',1),('late','STOPPED',1)])
def test_d_observation_mock_negative_outcomes_never_promote(observation_case,kind,expected,max_attempts):
    c=observation_case;c.mode['kind']=kind
    if kind=='abrupt':
        with pytest.raises(KeyboardInterrupt):_run_observation(c)
        out=json.loads(c.receipt.read_text())
    else:out=_run_observation(c)
    assert out['state']==expected and out['attempts']<=max_attempts
    assert len(c.calls)<=max_attempts
    assert not topup._has_day(c.store,'greeks','SPY',D_MID)
    if kind=='refusal':assert json.loads(c.receipt.read_text())['requests'][0]['state']=='REFUSED'
    c.clock['value']=10.  # replay guard is distinct from an exhausted caller deadline
    assert _run_observation(c)['reason']=='existing_observation_claim'


@pytest.mark.parametrize('kind',['missing_oi','missing_baseline','stale_oi','forced','wrong_rung','first_rung',
    'weekend','policy','deadline','unimplemented'])
def test_d_observation_zero_request_preconditions(observation_case,kind):
    from dataclasses import replace
    c=observation_case;changes={}
    if kind in ['missing_oi','missing_baseline','stale_oi']:
        path=c.store/'oi/SPY/2026.parquet';frame=pd.read_parquet(path)
        remove=D_MID if kind!='missing_baseline' else S_MID
        frame=frame[frame.date!=pd.Timestamp(remove)]
        if kind=='stale_oi':frame=pd.concat([frame,_observation_frame(date(2026,8,17),oi=True)])
        frame.to_parquet(path,index=False)
    elif kind=='forced':changes['ctx']=replace(c.ctx,forced=True)
    elif kind=='wrong_rung':changes['now']=_et(2026,8,19,19,0)
    elif kind=='first_rung':changes['now']=_et(2026,8,19,16,20)
    elif kind=='weekend':
        changes.update(ctx=topup.RunContext(date(2026,8,22),date(2026,8,21),False),now=_et(2026,8,22,17,30))
    elif kind=='policy':changes['options']={}
    elif kind=='deadline':c.clock['value']=100.
    else:changes['config']=replace(c.config,transport=None)
    out=_run_observation(c,**changes)
    assert out['state']=='WITHHELD' and out['attempts']==0
    assert not c.calls and not c.receipt.exists()


def test_d_observation_durability_failure_before_mock_get(observation_case,monkeypatch):
    c=observation_case
    monkeypatch.setattr(topup,'_eod_sync_directory',lambda p:(_ for _ in ()).throw(OSError('fsync')))
    with pytest.raises(OSError):_run_observation(c)
    assert not c.calls and not c.receipt.exists()


@pytest.mark.parametrize('mutation',['missing','wrong_root','bad_right','nan','duplicate','zero_price','version'])
def test_d_observation_coverage_falsifiers(mutation):
    a=_observation_frame(D_MID);g=a.copy();d=_observation_frame(D_MID,oi=True);s=_observation_frame(S_MID,oi=True)
    version='1'
    if mutation=='missing':d=None
    elif mutation=='wrong_root':g.loc[0,'root']='QQQ'
    elif mutation=='bad_right':g.loc[0,'right']='X'
    elif mutation=='nan':g.loc[0,'gamma']=float('nan')
    elif mutation=='duplicate':g=pd.concat([g,g.iloc[:1]])
    elif mutation=='zero_price':g.loc[0,'underlying_price']=0
    else:version='2'
    assert not topup._d_session_coverage(a,g,d,s,D=D_MID,S=S_MID,requested_version=version)['ready']


@pytest.mark.parametrize('hour,minute',[(16,20),(17,30)])
def test_daily_observation_none_keeps_four_cell_health_and_calls(store,monkeypatch,hour,minute):
    _wire_daily(monkeypatch,store,t1=['SPY'],ad=['SPY']);fake=FakeTd();_install_fake_td(monkeypatch,fake)
    monkeypatch.setattr(topup,'_observe_spy_d_session',lambda *a,**k:pytest.fail('Default must stay off'))
    assert topup._daily_main(workers=1,deadline_min=65,forced=False,now_fn=lambda:_et(2026,8,19,hour,minute))==0
    assert fake.calls==[('eod','SPY',S_MID),('oi','SPY',S_MID),('oi','SPY',D_MID),('greeks','SPY',S_MID)]
    receipt=json.loads((store/'_manifest.json').read_text())['daily_refresh']
    assert receipt['status']=='healthy' and 'd_session_observation' not in receipt


@pytest.mark.parametrize('case',['pre_gate','holiday','weekend','forced','lock_refused'])
def test_daily_admitted_observation_still_respects_existing_entry_fences(observation_case,monkeypatch,case):
    c=observation_case;_wire_daily(monkeypatch,c.store,t1=['SPY'],ad=['SPY']);_install_fake_td(monkeypatch,FakeTd())
    monkeypatch.setattr(topup,'_dated_greek_request_options',lambda r:{'version':'1'})
    # Existing default maintainer would pass that option only to ordinary Greek calls.
    now=c.now;forced=False
    if case=='pre_gate':now=_et(2026,8,19,15,30)
    if case=='holiday':now=_et(2026,1,1,17,30)
    if case=='weekend':now=_et(2026,8,22,17,30)
    if case=='forced':forced=True
    if case=='lock_refused':
        with topup._writer_lock(c.store) as held:
            assert held
            assert topup._daily_main(workers=1,deadline_min=65,forced=False,now_fn=lambda:now,
                d_session_observation=c.config)==0
    else:
        topup._daily_main(workers=1,deadline_min=65,forced=forced,now_fn=lambda:now,
            d_session_observation=c.config)
    assert not c.calls and not c.receipt.exists()


def test_daily_mock_observation_keeps_health_and_debits_same_deadline(observation_case,monkeypatch):
    c=observation_case;_wire_daily(monkeypatch,c.store,t1=['SPY'],ad=['SPY']);fake=FakeTd();_install_fake_td(monkeypatch,fake)
    monkeypatch.setattr(topup,'_dated_greek_request_options',lambda r:{'version':'1'})
    real_transport=c.config.transport
    class Timed:
        origin=real_transport.origin
        def __call__(self,*args,**kw):
            result=real_transport(*args,**kw);c.clock['value']+=2.;return result
    from dataclasses import replace
    config=replace(c.config,transport=Timed())
    real_pool=topup._run_daily_pool;limits=[]
    def pool(*args,**kw):
        limits.append(kw['deadline_min']);return real_pool(*args,**kw)
    monkeypatch.setattr(topup,'_run_daily_pool',pool)
    assert topup._daily_main(workers=1,deadline_min=65,forced=False,now_fn=lambda:c.now,
        d_session_observation=config)==0
    receipt=json.loads((c.store/'_manifest.json').read_text())['daily_refresh']
    assert receipt['status']=='healthy' and receipt['ad_ready_coverage_pct']==1
    assert receipt['d_session_observation']['state']=='OBSERVED_COMPLETE'
    assert limits==[pytest.approx(65-4/60)]
    assert not fake.calls  # all four existing cells already present
    assert not topup._has_day(c.store,'greeks','SPY',D_MID)


@pytest.mark.parametrize('day,prior,hour_utc',[(date(2026,7,15),date(2026,7,14),21),
    (date(2026,1,14),date(2026,1,13),22),(date(2026,1,2),date(2025,12,31),22),
    (date(2026,8,24),date(2026,8,21),21)])
def test_d_observation_calendar_rung_roles_no_offset_guess(day,prior,hour_utc):
    entered=datetime(day.year,day.month,day.day,hour_utc,30,tzinfo=timezone.utc)
    ctx=topup._resolve_daily_context(entered,forced=False)
    assert ctx.D==day and ctx.S==prior
    assert entered.astimezone(ET).hour==17


def test_d_observation_bad_adapter_without_reservation_is_unknown(observation_case):
    from dataclasses import replace
    c=observation_case
    class Unreserved:
        origin='http://127.0.0.1:25503'
        def __call__(self,*a,**kw):raise RuntimeError('adapter failed without a verified request outcome')
    out=_run_observation(c,config=replace(c.config,transport=Unreserved()))
    assert out['state']=='EFFECT_UNKNOWN' and not c.calls
    assert json.loads(c.receipt.read_text())['requests'][0]['state']=='EFFECT_UNKNOWN'


def test_daily_optional_observation_return_failure_preserves_four_cells(store,monkeypatch,tmp_path):
    _wire_daily(monkeypatch,store,t1=['SPY'],ad=['SPY']);fake=FakeTd();_install_fake_td(monkeypatch,fake)
    def failed(*args,**kwargs):raise OSError('private journal durability unavailable')
    monkeypatch.setattr(topup,'_observe_spy_d_session',failed)
    config=topup._DSessionObservation(tmp_path,'01a156f1-f450-7793-8951-bddadd4784c2',
        '01a15700-1ae2-7a73-9756-f1546da7ace8')
    assert topup._daily_main(workers=1,deadline_min=65,forced=False,now_fn=lambda:_et(2026,8,19,17,30),
        d_session_observation=config)==0
    receipt=json.loads((store/'_manifest.json').read_text())['daily_refresh']
    assert receipt['status']=='healthy'
    assert receipt['d_session_observation']['state']=='EFFECT_UNKNOWN'
    assert receipt['d_session_observation']['attempts'] is None
    assert fake.calls==[('eod','SPY',S_MID),('oi','SPY',S_MID),('oi','SPY',D_MID),('greeks','SPY',S_MID)]


def test_d_observation_retry_enabled_adapter_refused_before_actual_attempt(observation_case):
    from dataclasses import replace
    from types import SimpleNamespace
    c=observation_case
    class Retrying:
        origin='http://127.0.0.1:25503'
        def __call__(self,*args,**kw):
            session=SimpleNamespace(get_adapter=lambda u:SimpleNamespace(max_retries=SimpleNamespace(total=2)))
            kw['request_budget'].begin(session,self.origin+'/v3/option/history/eod')
            pytest.fail('No actual transport may follow rejected carrier')
    out=_run_observation(c,config=replace(c.config,transport=Retrying()))
    assert out['state']=='STOPPED' and out['attempts']==0 and not c.calls
    assert json.loads(c.receipt.read_text())['requests'][0]['state']=='NOT_ATTEMPTED'


def test_d_observation_local_reports_cross_year_without_date_substitution(observation_case):
    c=observation_case
    for day in [S_DEC,D_JAN]:topup._merge_day(c.store,'oi','SPY',day,_observation_frame(day,oi=True))
    d,s,refs=topup._d_session_local_oi(c.store,D_JAN,S_DEC)
    assert set(d.date)=={pd.Timestamp(D_JAN)} and set(s.date)=={pd.Timestamp(S_DEC)}
    assert len(refs)==2 and all(r['sha256'] and r['bytes']>0 and r['first_availability'] is None for r in refs)
    assert not c.calls


def test_d_observation_probe_scope_refused_before_actual_attempt(observation_case):
    from dataclasses import replace
    from types import SimpleNamespace
    c=observation_case
    class Probe:
        origin='http://127.0.0.1:25503'
        def __call__(self,*args,**kw):
            session=SimpleNamespace(get_adapter=lambda u:SimpleNamespace(max_retries=SimpleNamespace(total=0)))
            kw['request_budget'].begin(session,self.origin+'/v3/health')
            pytest.fail('Hidden probe must not reach physical transport')
    out=_run_observation(c,config=replace(c.config,transport=Probe()))
    assert out['state']=='STOPPED' and out['attempts']==0 and not c.calls
    assert json.loads(c.receipt.read_text())['requests'][0]['state']=='NOT_ATTEMPTED'


def test_d_observation_wrong_return_dates_never_stamped_as_target(observation_case):
    c=observation_case;c.mode['kind']='date'
    assert _run_observation(c)['state']=='WITHHELD'
    record=json.loads(c.receipt.read_text())
    for request in record['requests']:
        assert request['parameters']['start_date']==20260819
        assert request['returned_frame_dates']==['2026-08-18T00:00:00']
        assert 'source_date' not in request
    assert record['requested_greek_version']=='1' and record['model_scope'] is None
    assert record['requests'][1]['response_model_metadata'] is None
    assert record['requests'][1]['frame_request_version_provenance'] is None


@pytest.mark.parametrize('kind',['missing_expiry','timezone_expiry','intraday_expiry','expired_report',
    'intraday_report_date','live_baseline_mismatch'])
def test_d_observation_known_invalid_local_baseline_precedes_claim(observation_case,kind):
    c=observation_case;p=c.store/'oi/SPY/2026.parquet';frame=pd.read_parquet(p)
    d=frame.date.eq(pd.Timestamp(D_MID));s=frame.date.eq(pd.Timestamp(S_MID))
    if kind=='missing_expiry':frame.loc[d,'expiration']=pd.NaT
    elif kind=='timezone_expiry':frame['expiration']=frame.expiration.dt.tz_localize('America/New_York')
    elif kind=='intraday_expiry':frame.loc[d,'expiration']=pd.Timestamp('2027-02-19T12:00:00')
    elif kind=='expired_report':frame.loc[d,'expiration']=pd.Timestamp(S_MID)
    elif kind=='intraday_report_date':frame.loc[d,'date']=pd.Timestamp(D_MID)+pd.Timedelta(hours=12)
    else:frame.loc[s & frame.strike.eq(745.),'strike']=746.
    frame.to_parquet(p,index=False)
    out=_run_observation(c)
    assert out['state']=='WITHHELD' and out['attempts']==0
    assert not c.calls and not c.receipt.exists()


def test_d_observation_expired_baseline_retained_and_explicitly_excluded(observation_case):
    c=observation_case;p=c.store/'oi/SPY/2026.parquet';frame=pd.read_parquet(p)
    old=_observation_frame(S_MID,oi=True).iloc[:1].copy()
    old['expiration']=pd.Timestamp(S_MID);old['strike']=700.
    pd.concat([frame,old]).to_parquet(p,index=False)
    out=_run_observation(c)
    assert out['state']=='OBSERVED_COMPLETE'
    coverage=out['coverage']
    assert coverage['counts']['oi_S']==3
    assert coverage['excluded_before_D']=={'eod_D':0,'greeks_D':0,'oi_D':0,'oi_S':1}
    assert coverage['observed_contracts']==2 and all(v==0 for v in coverage['missing_by_input'].values())
    retained=pd.read_csv(c.receipt.parent/'oi_S.csv')
    assert len(retained)==3 and '2026-08-18' in set(retained.expiration)
    record=json.loads(c.receipt.read_text())
    assert record['local_report_copies'][1]['rows']==3
    assert record['local_report_copies'][1]['excluded_expiry_before_D']==1
    # A live extra/missing member is never converted into the expiry exclusion.
    a=_observation_frame(D_MID);g=a.iloc[:1].copy()
    d=_observation_frame(D_MID,oi=True);s=pd.concat([_observation_frame(S_MID,oi=True),old])
    value=topup._d_session_coverage(a,g,d,s,D=D_MID,S=S_MID,requested_version='1')
    assert not value['ready'] and value['missing_by_input']['greeks_D']==1
    assert value['excluded_before_D']['oi_S']==1 and value['observed_contracts']==2


@pytest.mark.parametrize('wrong_date',[False,True])
def test_d_observation_actual_native_get_binding_keeps_canonical_unchanged(observation_case,monkeypatch,wrong_date):
    import hashlib,io
    from types import SimpleNamespace
    from dataclasses import replace
    from collectors import thetadata as td
    c=observation_case;calls=[]
    bodies={
      'eod':b'symbol,expiration,strike,right,last_trade,created,close,volume\nSPY,2027-02-19,745,PUT,2026-08-19T16:00:00,2026-08-19T17:15:00,2,10\nSPY,2027-02-19,760,PUT,2026-08-19T16:00:00,2026-08-19T17:15:00,3,20\n',
      'greeks':b'symbol,expiration,strike,right,timestamp,underlying_timestamp,underlying_price,gamma,speed\nSPY,2027-02-19,745,PUT,2026-08-19T16:00:00,2026-08-19T16:00:00,770,-0.01,0.001\nSPY,2027-02-19,760,PUT,2026-08-19T16:00:00,2026-08-19T16:00:00,770,0.02,0.002\n'}
    if wrong_date:bodies['eod']=bodies['eod'].replace(b'2026-08-19T16:00:00',b'2026-08-18T16:00:00')
    class Session:
        def get_adapter(self,url):return SimpleNamespace(max_retries=SimpleNamespace(total=0))
        def get(self,url,**kw):
            record=json.loads(c.receipt.read_text())
            assert record['attempts']==len(calls)+1 and record['requests'][-1]['state']=='REQUEST_STARTED'
            with topup._writer_lock(c.store) as held:assert held is False
            kind='greeks' if '/greeks/' in url else 'eod';calls.append((url,kw))
            assert kw['allow_redirects'] is False
            return SimpleNamespace(status_code=200,close=lambda:None,
                iter_content=lambda **k:iter([bodies[kind]]))
    monkeypatch.setattr(td,'_base_url',lambda:'http://127.0.0.1:25503')
    monkeypatch.setattr(td,'_session',Session)
    monkeypatch.setattr(td,'reachable',lambda:pytest.fail('Additional probe'))
    monkeypatch.setattr(td,'_concurrent_windows',lambda *a,**k:pytest.fail('Retries/window worker'))
    original=pd.read_csv
    def parse(stream,*args,**kwargs):
        if isinstance(stream,io.BytesIO):
            record=json.loads(c.receipt.read_text());request=record['requests'][-1]
            assert request['state']=='RAW_CAPTURED'
            assert request['sha256']==hashlib.sha256(stream.getvalue()).hexdigest()
        return original(stream,*args,**kwargs)
    monkeypatch.setattr(pd,'read_csv',parse)
    config=replace(c.config,transport=td.bounded_spy_d_session_transport(D_MID))
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in c.store.rglob('*.parquet')}
    with topup._writer_lock(c.store) as held:
        assert held;out=_run_observation(c,config=config)
    assert out['state']==('WITHHELD' if wrong_date else 'OBSERVED_COMPLETE')
    assert out['attempts']==2 and len(calls)==2
    record=json.loads(c.receipt.read_text())
    assert record['model_scope'] is None and record['model_details'] is None
    assert record['requests'][1]['frame_request_version_provenance']=='1'
    assert record['requests'][1]['response_model_metadata'] is None
    assert record['requests'][0]['returned_frame_dates']==[
        '2026-08-18T00:00:00' if wrong_date else '2026-08-19T00:00:00']
    assert record['requests'][1]['returned_frame_dates']==['2026-08-19T00:00:00']
    assert before=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in c.store.rglob('*.parquet')}
    assert not topup._has_day(c.store,'greeks','SPY',D_MID)


@pytest.mark.parametrize('phase',['headers','body'])
def test_d_observation_inflight_deadline_is_sticky_unknown_without_capture_thread(observation_case,monkeypatch,phase):
    import threading,time
    from dataclasses import replace
    from types import SimpleNamespace
    from collectors import thetadata as td
    c=observation_case;calls=[];closed=[]
    monkeypatch.setattr(time,'monotonic',time.perf_counter)
    class Session:
        def get_adapter(self,url):return SimpleNamespace(max_retries=SimpleNamespace(total=0))
        def get(self,url,**kw):
            calls.append(url)
            record=json.loads(c.receipt.read_text())
            assert record['requests'][-1]['state']=='REQUEST_STARTED'
            if phase=='headers':
                threading.Event().wait(1)
                pytest.fail('Absolute timer did not interrupt synchronous header read')
            def body(**kw):
                threading.Event().wait(1)
                pytest.fail('Absolute timer did not interrupt synchronous body read')
                yield b''
            return SimpleNamespace(status_code=200,iter_content=body,close=lambda:closed.append(True))
    monkeypatch.setattr(td,'_session',Session)
    monkeypatch.setattr(td,'_base_url',lambda:'http://127.0.0.1:25503')
    config=replace(c.config,transport=td.bounded_spy_d_session_transport(D_MID))
    start=time.monotonic()
    out=topup._observe_spy_d_session(c.store,c.ctx,c.now,start+.3,config,request_options={'version':'1'})
    assert time.monotonic()-start<.8
    assert out['state']=='EFFECT_UNKNOWN' and out['attempts']==1 and len(calls)==1
    record=json.loads(c.receipt.read_text())
    assert record['requests'][0]['state']=='EFFECT_UNKNOWN'
    assert len(record['requests'])==1 and not (c.receipt.parent/'eod.csv').exists()
    assert closed==([True] if phase=='body' else [])
    again=topup._observe_spy_d_session(c.store,c.ctx,c.now,time.monotonic()+2,config,request_options={'version':'1'})
    assert again['reason']=='existing_observation_claim' and len(calls)==1


@pytest.mark.parametrize('binding',[None,date(2026,8,18),date(2026,8,20),'2026-08-19'])
def test_d_observation_session_binding_refuses_before_local_read_and_claim(observation_case,monkeypatch,binding):
    from dataclasses import replace
    c=observation_case
    monkeypatch.setattr(topup,'_d_session_local_oi',lambda *a:pytest.fail('Unbound operation reached local-source preflight'))
    out=_run_observation(c,config=replace(c.config,session_day=binding))
    assert out['reason']=='observation_session_not_bound' and out['attempts']==0
    assert not c.calls and not c.receipt.parent.exists()


def test_d_observation_receipt_binds_exact_session_operation(observation_case):
    c=observation_case;out=_run_observation(c)
    assert out['state']=='OBSERVED_COMPLETE'
    record=json.loads(c.receipt.read_text())
    assert record['bound_session']==D_MID.isoformat()
    assert record['operation_ref']==f'spy-{D_MID.isoformat()}-1730-observation-v1'


@pytest.mark.parametrize('root,setting,expected', [
    ('SPY', '', {}), ('QQQ', '', {}), ('SPY', ' spy , qqq ', {'version': '1'}),
    ('QQQ', 'SPY,QQQ', {'version': '1'}), ('QQQ', 'SPY', {}),
    ('AAPL', 'SPY,QQQ', {}),
])
def test_backfill_owner_shares_explicit_dated_version_policy(monkeypatch, root, setting, expected):
    import collectors.thetadata as td
    import scripts.backfill_thetadata_eod as backfill

    monkeypatch.setenv('THETADATA_DATED_GREEKS_V1_ROOTS', setting)
    calls = []
    monkeypatch.setattr(td, 'bulk_eod', lambda *a, **kw: pd.DataFrame())
    monkeypatch.setattr(td, 'bulk_open_interest', lambda *a, **kw: pd.DataFrame())
    def greeks(*args, **kwargs):
        calls.append((args, kwargs))
        return pd.DataFrame()
    monkeypatch.setattr(td, 'bulk_greeks', greeks)
    day = date(2026, 10, 22)
    assert backfill._pull_root_year(root, 2026, day, day)
    assert calls == [((root, 0, day, day), {'order': 3, **expected})]
    assert topup._dated_greek_request_options(root) == expected


def test_invalid_dated_policy_stops_backfill_before_any_source_call(monkeypatch):
    import collectors.thetadata as td
    import scripts.backfill_thetadata_eod as backfill

    monkeypatch.setenv('THETADATA_DATED_GREEKS_V1_ROOTS', 'SPY,AAPL')
    for name in ('reachable', 'bulk_eod', 'bulk_open_interest', 'bulk_greeks'):
        monkeypatch.setattr(td, name, lambda *a, **kw: pytest.fail('Invalid policy reached source'))
    with pytest.raises(ValueError, match='SPY/QQQ'):
        backfill._pull_root_year('SPY', 2026, S_MID, S_MID)
    monkeypatch.setattr('sys.argv', ['backfill_thetadata_eod.py'])
    with pytest.raises(SystemExit):
        backfill.main()


def test_opt_in_does_not_refetch_an_already_present_unversioned_day(store, monkeypatch):
    monkeypatch.setenv('THETADATA_DATED_GREEKS_V1_ROOTS', 'SPY,QQQ')
    topup._merge_day(store, 'greeks', 'SPY', S_MID, _df(S_MID))
    assert topup._dated_greek_request_options('SPY') == {'version': '1'}
    assert topup._ensure_one_cell(store, 'greeks', 'SPY', S_MID,
        lambda: pytest.fail('Opt-in must not replay an existing day')) == 'already_present'


@pytest.fixture
def pilot_cli_case(request, monkeypatch):
    """Exact approved date through real main/daily entry, synthetic transport only."""
    import sys
    monkeypatch.setattr(sys.modules[__name__], 'D_MID', date(2026,10,26))
    monkeypatch.setattr(sys.modules[__name__], 'S_MID', date(2026,10,23))
    c=request.getfixturevalue('observation_case');c.now=_et(2026,10,26,17,30)
    _wire_daily(monkeypatch,c.store,t1=['SPY'],ad=['SPY'])
    c.fake=FakeTd(default_D=D_MID);_install_fake_td(monkeypatch,c.fake)
    import collectors.thetadata as td
    c.capacity={'ready':True}
    c.config.transport.preflight=lambda **kw:c.capacity['ready']
    monkeypatch.setattr(td,'bounded_spy_d_session_transport',lambda day:c.config.transport)
    monkeypatch.setattr(topup,'_SPY_20261026_RETENTION_PARENT',c.private,raising=False)
    monkeypatch.setenv('THETADATA_D_SESSION_OBSERVATION','spy-2026-10-26-1730-observation-v1')
    monkeypatch.setenv('THETADATA_DATED_GREEKS_V1_ROOTS','SPY')
    original=topup._daily_main
    monkeypatch.setattr(topup,'_daily_main',lambda **kw:original(now_fn=lambda:c.now,**kw))
    return c


def test_pilot_cli_exact_operation_reaches_existing_two_attempt_journal(pilot_cli_case):
    c=pilot_cli_case
    assert topup.main(['--daily','--workers','1'])==0
    assert [kind for kind,_ in c.calls]==['eod','greeks']
    r=json.loads(c.receipt.read_text())
    assert (r['operation_ref'],r['D'],r['S'],r['attempts'])==('spy-2026-10-26-1730-observation-v1','2026-10-26','2026-10-23',2)
    assert r['max_gets']==2 and r['requested_greek_version']=='1'
    assert not c.fake.calls and not topup._has_day(c.store,'greeks','SPY',D_MID)
    health=_manifest(c.store)['daily_refresh']
    assert health['status']=='healthy' and health['worker_count']==1
    assert health['d_session_observation']['state']=='OBSERVED_COMPLETE'


@pytest.mark.parametrize('case',['pre_gate','early_rung','wrong_rung','wrong_day','weekend','lock','no_oi','capacity','parent','existing_unknown'])
def test_pilot_cli_refusal_makes_no_pilot_attempt_or_new_claim(pilot_cli_case,monkeypatch,case):
    c=pilot_cli_case;before=None
    if case=='pre_gate':c.now=_et(2026,10,26,15,30)
    if case=='early_rung':c.now=_et(2026,10,26,17,15)
    if case=='wrong_rung':c.now=_et(2026,10,26,19,0)
    if case=='wrong_day':c.now=_et(2026,10,27,17,30)
    if case=='weekend':c.now=_et(2026,10,24,17,30)
    if case=='no_oi':(c.store/'oi/SPY/2026.parquet').unlink()
    if case=='capacity':c.capacity['ready']=False
    if case=='parent':monkeypatch.setattr(topup,'_SPY_20261026_RETENTION_PARENT',c.private/'absent')
    if case=='existing_unknown':
        c.receipt.parent.mkdir();before=b'{"state":"EFFECT_UNKNOWN","attempts":1}\n';c.receipt.write_bytes(before)
    if case=='lock':
        with topup._writer_lock(c.store) as held:
            assert held;assert topup.main(['--daily','--workers','1'])==0
    else:topup.main(['--daily','--workers','1'])
    assert not c.calls
    if before is None:assert not c.receipt.parent.exists()
    else:assert c.receipt.read_bytes()==before


@pytest.mark.parametrize('env,args',[
    ('spy-2026-10-27-1730-observation-v1',['--daily']),
    ('spy-2026-10-26-1730-observation-v1',['--daily','--force-run']),
    ('spy-2026-10-26-1730-observation-v1',['--roots','SPY']),
    ('spy-2026-10-26-1730-observation-v1',['--daily','--deadline-min','66']),
])
def test_pilot_cli_invalid_configuration_fails_before_source_work(pilot_cli_case,monkeypatch,env,args):
    c=pilot_cli_case;monkeypatch.setenv('THETADATA_D_SESSION_OBSERVATION',env)
    with pytest.raises(SystemExit) as ex:topup.main(args)
    assert ex.value.code==2 and not c.calls and not c.fake.calls and not c.receipt.parent.exists()


def test_pilot_cli_absent_configuration_preserves_default_none(pilot_cli_case,monkeypatch):
    c=pilot_cli_case;monkeypatch.delenv('THETADATA_D_SESSION_OBSERVATION')
    monkeypatch.setattr(topup,'_observe_spy_d_session',lambda *a,**k:pytest.fail('Absent config activated pilot'))
    assert topup.main(['--daily','--workers','1'])==0
    assert not c.calls and not c.receipt.parent.exists()
    assert 'd_session_observation' not in _manifest(c.store)['daily_refresh']


@pytest.mark.parametrize('outcome,state',[('abrupt','EFFECT_UNKNOWN'),('refusal','STOPPED')])
def test_pilot_cli_unreturned_attempt_is_sticky_and_never_reoffered(pilot_cli_case,outcome,state):
    c=pilot_cli_case;c.mode['kind']=outcome
    if outcome=='abrupt':
        with pytest.raises(KeyboardInterrupt):topup.main(['--daily','--workers','1'])
    else:assert topup.main(['--daily','--workers','1'])==0
    before=c.receipt.read_bytes();r=json.loads(before)
    assert r['state']==state and r['attempts']==1 and len(c.calls)==1
    assert topup.main(['--daily','--workers','1'])==0
    assert c.receipt.read_bytes()==before and len(c.calls)==1


def test_pilot_cli_missing_version_policy_cannot_mint_model_or_claim(pilot_cli_case,monkeypatch):
    c=pilot_cli_case;monkeypatch.delenv('THETADATA_DATED_GREEKS_V1_ROOTS')
    assert topup.main(['--daily','--workers','1'])==0
    assert not c.calls and not c.receipt.parent.exists()
    assert _manifest(c.store)['daily_refresh']['d_session_observation']['reason']=='greek_request_policy_unestablished'


@pytest.mark.parametrize('fault',['origin','preflight'])
def test_pilot_cli_bad_native_binding_refuses_before_daily_source(pilot_cli_case,fault):
    c=pilot_cli_case
    if fault=='origin':c.config.transport.origin='http://source-lookalike.invalid'
    else:del c.config.transport.preflight
    with pytest.raises(SystemExit) as ex:topup.main(['--daily','--workers','1'])
    assert ex.value.code==2 and not c.calls and not c.fake.calls and not c.receipt.parent.exists()
