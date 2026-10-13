"""A07 then-known exclusion — SNI-local guard property tests.

SNI-local DRAFT contract tests. They consume owner-supplied values and
synthetic fixtures; they do not mint, derive, or guess canonical issuer or
security identifiers. rank_authority, gate_authority, size_authority,
signal_authority, escalation_authority and trade_authority stay literal
false. Residuals and stress statistics are descriptive. These tests attack
the existing S1 vintage-leak predicate, the S2 info-leak scan, and the
US-stress then_known valid_from abstention. They do not build a then-known
compiler.
"""
from __future__ import annotations

import copy
import hashlib
import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research/single_name_intelligence/residual"))
sys.path.insert(0, str(ROOT / "research/single_name_intelligence/event_response"))
sys.path.insert(0, str(ROOT / "research/single_name_intelligence/us_stress"))

from s1_infoleak import STEP_TOLERANCE, detect, vintage_series  # noqa: E402
from stress_set import (  # noqa: E402
    _bench_then_known_violation,
    _ticker_then_known_violation,
    load_profiles,
    stress_table,
)

SEEDS = range(200)
PROFILES_DIR = ROOT / "research/single_name_intelligence/us_stress/profiles"
FALSE_AUTHORITY = {
    "rank_authority": False,
    "gate_authority": False,
    "size_authority": False,
    "signal_authority": False,
    "escalation_authority": False,
    "trade_authority": False,
}


def _msg(seed, case):
    return "seed=%s case=%s" % (seed, case)


def _business_days(n, start):
    out = []
    d = start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def _prices_with_q_steps(n, step_indices, rng):
    """Persistent q changes at each index in 1..n-1. close = q * close_price."""
    q = [1.0] * n
    for idx in sorted(set(step_indices)):
        if idx <= 0 or idx >= n:
            continue
        delta = rng.uniform(1e-4, 5e-2) * rng.choice((-1.0, 1.0))
        factor = 1.0 + delta
        for j in range(idx, n):
            q[j] *= factor
    close_price = [rng.uniform(20.0, 80.0) for _ in range(n)]
    close = [q[i] * close_price[i] for i in range(n)]
    return close, close_price


def _assert_detect_matches_steps(steps, state, anchor, last_bar, seed, case):
    msg = _msg(seed, case)
    if state != "OK":
        assert detect(steps, state, anchor, last_bar) is None, msg
        return
    in_window = [(d, s) for d, s in steps if anchor <= d <= last_bar]
    hit = detect(steps, state, anchor, last_bar)
    if not in_window:
        assert hit is None, msg
        return
    assert hit is not None, msg
    assert hit["first_offending_date"] == in_window[0][0].isoformat(), msg
    assert hit["count_of_steps_in_window"] == len(in_window), msg
    assert hit["contamination_class"] == "information_leak", msg


def _profile_fingerprints():
    out = {}
    for path in sorted(PROFILES_DIR.glob("*.yml")):
        data = path.read_bytes()
        out[path.name] = (len(data), hashlib.sha256(data).hexdigest())
    return out


PROFILE_FINGERPRINTS = _profile_fingerprints()


def _synth_profile(benches, sector, then_known):
    return {
        "authority": dict(FALSE_AUTHORITY),
        "canonical_issuer_id": None,
        "stress_set": {
            "benchmarks": list(benches),
            "sector_etf": sector,
            "descriptive_only": True,
        },
        "then_known": then_known,
        "cohort_selection": {
            "hindsight": True,
            "survivorship": True,
            "representative_sample": False,
            "transfer_evidence": False,
        },
    }


def _walk_closes(n, start, rng, level=100.0):
    dates = _business_days(n, start)
    price = level
    rows = []
    for d in dates:
        price *= math.exp(rng.uniform(-0.02, 0.02))
        price = max(price, 1.0)
        rows.append((d.isoformat(), float(price)))
    return rows


# ---------------------------------------------------------------------------
# S1 vintage leak predicate
# ---------------------------------------------------------------------------

def test_a07_01_s1_boundary():
    """detect is non-None iff a step date sits in [anchor, last_bar] inclusive."""
    n_cases = 0
    for seed in SEEDS:
        rng = random.Random(seed)
        n = rng.randint(30, 300)
        start = date(2016, 1, 4) + timedelta(days=rng.randint(0, 1800))
        dates = _business_days(n, start)
        n_steps = rng.randint(0, 4)
        if n_steps:
            step_indices = rng.sample(range(1, n), n_steps)
        else:
            step_indices = []
        close, close_price = _prices_with_q_steps(n, step_indices, rng)
        steps, state = vintage_series(dates, close, close_price)
        assert state == "OK", _msg(seed, "random")
        assert {d for d, _ in steps} == {dates[i] for i in step_indices}, _msg(
            seed, "random"
        )
        for srel in steps:
            assert srel[1] > STEP_TOLERANCE, _msg(seed, "random")

        i_a = rng.randint(0, n - 1)
        i_b = rng.randint(0, n - 1)
        if rng.random() < 0.2:
            anchor, last_bar = dates[max(i_a, i_b)], dates[min(i_a, i_b)]
            if anchor == last_bar and n > 1:
                last_bar = dates[0]
                anchor = dates[-1]
        else:
            anchor, last_bar = dates[min(i_a, i_b)], dates[max(i_a, i_b)]
        _assert_detect_matches_steps(
            steps, state, anchor, last_bar, seed, "random"
        )
        n_cases += 1

        k = rng.randint(2, n - 3)
        close_one, cp_one = _prices_with_q_steps(n, [k], rng)
        steps_one, state_one = vintage_series(dates, close_one, cp_one)
        assert state_one == "OK", _msg(seed, "one_step")
        assert [d for d, _ in steps_one] == [dates[k]], _msg(seed, "one_step")

        _assert_detect_matches_steps(
            steps_one, state_one, dates[k], dates[-1], seed, "on_anchor"
        )
        hit_on = detect(steps_one, state_one, dates[k], dates[-1])
        assert hit_on is not None, _msg(seed, "on_anchor")
        assert hit_on["first_offending_date"] == dates[k].isoformat(), _msg(
            seed, "on_anchor"
        )
        assert hit_on["count_of_steps_in_window"] == 1, _msg(seed, "on_anchor")

        _assert_detect_matches_steps(
            steps_one, state_one, dates[k + 1], dates[-1], seed, "before_anchor"
        )
        assert detect(steps_one, state_one, dates[k + 1], dates[-1]) is None, _msg(
            seed, "before_anchor"
        )

        _assert_detect_matches_steps(
            steps_one, state_one, dates[0], dates[k], seed, "on_last_bar"
        )
        hit_last = detect(steps_one, state_one, dates[0], dates[k])
        assert hit_last is not None, _msg(seed, "on_last_bar")
        assert hit_last["first_offending_date"] == dates[k].isoformat(), _msg(
            seed, "on_last_bar"
        )

        _assert_detect_matches_steps(
            steps_one, state_one, dates[0], dates[k - 1], seed, "after_last_bar"
        )
        assert detect(steps_one, state_one, dates[0], dates[k - 1]) is None, _msg(
            seed, "after_last_bar"
        )

        _assert_detect_matches_steps(
            steps_one, state_one, dates[-1], dates[0], seed, "empty_window"
        )
        assert detect(steps_one, state_one, dates[-1], dates[0]) is None, _msg(
            seed, "empty_window"
        )
        n_cases += 5

    assert n_cases >= 200


def test_a07_02_s1_unverifiable_never_retires_but_is_disclosed():
    """Unusable raw column: VINTAGE_UNVERIFIABLE from vintage_series; detect is None."""
    n_cases = 0
    for seed in SEEDS:
        rng = random.Random(seed)
        n = rng.randint(0, 12)
        start = date(2020, 1, 6) + timedelta(days=rng.randint(0, 400))
        dates = _business_days(max(n, 1), start)[:n]
        kind = seed % 5
        if kind == 0:
            close = [rng.uniform(10.0, 40.0) for _ in dates]
            close_price = [None] * len(dates)
        elif kind == 1:
            close = [float("nan") for _ in dates]
            close_price = [rng.uniform(10.0, 40.0) for _ in dates]
        elif kind == 2:
            close = [rng.uniform(10.0, 40.0) for _ in dates]
            close_price = [0.0 if rng.random() < 0.5 else -abs(rng.uniform(0.1, 5.0))
                           for _ in dates]
        elif kind == 3:
            close = [rng.uniform(10.0, 40.0) for _ in dates]
            close_price = [float("nan") for _ in dates]
        else:
            # fewer than 2 usable rows: at most one valid pair
            close = [rng.uniform(10.0, 40.0) for _ in dates]
            close_price = [None] * len(dates)
            if dates:
                close_price[0] = rng.uniform(10.0, 40.0)
        steps, state = vintage_series(dates, close, close_price)
        msg = _msg(seed, "unverifiable_%s" % kind)
        assert state == "VINTAGE_UNVERIFIABLE", msg
        assert steps == [], msg
        if dates:
            hit = detect(
                steps, state, dates[0], dates[-1] if dates else date(2020, 1, 6)
            )
        else:
            hit = detect(steps, state, date(2020, 1, 6), date(2020, 12, 31))
        assert hit is None, msg
        # Public disclosure of the unverifiable state is the vintage_series
        # return value (the state string). detect() itself returns None and
        # does not carry series_state. Pipeline LANE_MANIFEST vintage_states
        # is pinned by tests/test_sni_s1_info_leak.py, not re-run here.
        assert state == "VINTAGE_UNVERIFIABLE", msg
        n_cases += 1
    assert "VINTAGE_UNVERIFIABLE" in (vintage_series.__doc__ or "")
    assert "unverifiable" in (detect.__doc__ or "").lower()
    assert n_cases >= 200


def test_a07_03_s1_nan_rows_cannot_hide_a_step():
    """None/NaN/non-positive raw rows between two vintages do not erase the step.

    vintage_series skips unusable rows and attributes the step to the first
    usable date after the gap (dOK[i] of the first q that differs).
    """
    n_cases = 0
    for seed in SEEDS:
        rng = random.Random(seed)
        n = rng.randint(8, 40)
        start = date(2021, 3, 1) + timedelta(days=rng.randint(0, 500))
        dates = _business_days(n, start)
        gap_len = rng.randint(1, min(5, n - 3))
        gap_start = rng.randint(1, n - gap_len - 1)
        gap = set(range(gap_start, gap_start + gap_len))
        first_after = gap_start + gap_len
        assert first_after not in gap
        q0 = rng.uniform(0.8, 1.3)
        q1 = q0 * (1.0 + rng.choice((-1.0, 1.0)) * rng.uniform(1e-3, 4e-2))
        close_price = [rng.uniform(20.0, 70.0) for _ in range(n)]
        close = []
        for i in range(n):
            q = q0 if i < gap_start else q1
            close.append(q * close_price[i])
        kind = rng.choice(("none_cp", "nan_c", "nan_cp", "nonpos_cp", "none_c"))
        cp = list(close_price)
        cl = list(close)
        for i in gap:
            if kind == "none_cp":
                cp[i] = None
            elif kind == "nan_c":
                cl[i] = float("nan")
            elif kind == "nan_cp":
                cp[i] = float("nan")
            elif kind == "nonpos_cp":
                cp[i] = 0.0 if rng.random() < 0.5 else -1.0
            else:
                cl[i] = None
        steps, state = vintage_series(dates, cl, cp)
        msg = _msg(seed, "gap_%s_%s" % (kind, gap_len))
        assert state == "OK", msg
        assert len(steps) == 1, msg
        assert steps[0][0] == dates[first_after], msg
        assert steps[0][1] > STEP_TOLERANCE, msg
        n_cases += 1
    assert n_cases >= 200


# ---------------------------------------------------------------------------
# S2 info-leak scan
# ---------------------------------------------------------------------------

def _s2_engine(dates, baba_jump_idx, persistent=True):
    pd = pytest.importorskip("pandas")
    from s2_outcomes import OutcomeEngine

    def _frame(rows):
        return pd.DataFrame(rows, columns=["Date", "close", "close_price"])

    class _SyntheticLoader:
        """Serves the two price stores from synthetic frames (never data/)."""

        def __init__(self, baba, spy):
            self._frames = {
                "data/yahoo/BABA.parquet": baba,
                "data/yahoo/SPY.parquet": spy,
            }

        def read_parquet(self, path, columns=None):
            df = self._frames[path]
            return df if columns is None else df[[c for c in columns if c in df.columns]]

        def read_yaml(self, path):  # pragma: no cover - unused here
            raise AssertionError("no yaml reads in the price phase")

        def read_json(self, path):  # pragma: no cover
            raise AssertionError("no json reads in the price phase")

    n = len(dates)
    close = [100.0 + 0.1 * i for i in range(n)]
    raw = list(close)
    if baba_jump_idx is not None:
        if persistent:
            for j in range(baba_jump_idx, n):
                raw[j] = close[j] / 1.01
        else:
            raw[baba_jump_idx] = close[baba_jump_idx] / 1.01
    baba = _frame(
        [(d.isoformat(), c, r) for d, c, r in zip(dates, close, raw)]
    )
    spy = _frame([(d.isoformat(), 500.0, 500.0) for d in dates])
    return OutcomeEngine(_SyntheticLoader(baba, spy))


def test_a07_04_s2_scan_boundary():
    """S2 info_leak_scan: pre-anchor silent, strictly post-anchor and last-bar fire.

    Construction copies tests/test_sni_s2_info_leak.py (_SyntheticLoader +
    OutcomeEngine). A step dated exactly ON first_tune_anchor is a separate
    xfail (F-A07-01): the scan filters q to index >= anchor before differencing.
    """
    n_cases = 0
    for seed in SEEDS:
        rng = random.Random(seed)
        n = rng.randint(30, 80)
        start = date(2024, 1, 2) + timedelta(days=rng.randint(0, 200))
        dates = _business_days(n, start)
        k = rng.randint(2, n - 3)
        engine = _s2_engine(dates, k)
        last_bar = engine.last_bar_date
        assert last_bar == dates[-1], _msg(seed, "last_bar_identity")

        # pre-anchor: window starts the session after the step
        scan_pre = engine.info_leak_scan(dates[k + 1])
        assert scan_pre["leak"] is False, _msg(seed, "before_anchor")
        assert scan_pre["series"]["BABA"]["steps_above_tolerance"] == 0, _msg(
            seed, "before_anchor"
        )
        assert scan_pre["series"]["BABA"]["first_offending_date"] is None, _msg(
            seed, "before_anchor"
        )

        # strictly post-anchor: window starts the session before the step
        scan_post = engine.info_leak_scan(dates[k - 1])
        assert scan_post["leak"] is True, _msg(seed, "after_anchor")
        assert scan_post["series"]["BABA"]["steps_above_tolerance"] >= 1, _msg(
            seed, "after_anchor"
        )
        assert scan_post["series"]["BABA"]["first_offending_date"] == dates[k].isoformat(), _msg(
            seed, "after_anchor"
        )

        # on last_bar: plant the step on the final session
        engine_last = _s2_engine(dates, n - 1)
        scan_last = engine_last.info_leak_scan(dates[0])
        assert scan_last["leak"] is True, _msg(seed, "on_last_bar")
        assert scan_last["series"]["BABA"]["first_offending_date"] == dates[-1].isoformat(), _msg(
            seed, "on_last_bar"
        )
        assert scan_last["last_bar"] == dates[-1].isoformat(), _msg(seed, "on_last_bar")

        # after last_bar is unconstructable in the scan (last_bar is max(series));
        # an anchor after the last session is an empty window.
        scan_empty = engine.info_leak_scan(dates[-1] + timedelta(days=1))
        assert scan_empty["leak"] is False, _msg(seed, "empty_window")
        assert scan_empty["series"]["BABA"]["steps_above_tolerance"] == 0, _msg(
            seed, "empty_window"
        )
        n_cases += 4
    assert n_cases >= 200


def test_a07_04_s2_scan_on_anchor_inclusive():
    """S1-equivalent: a step ON the earliest TUNE anchor must be reported.

    seed=0 case=on_anchor. Current S2 scan returns leak=False for this fixture.
    """
    seed = 0
    n = 40
    dates = _business_days(n, date(2026, 6, 1))
    k = 10
    engine = _s2_engine(dates, k)
    scan = engine.info_leak_scan(dates[k])
    assert scan["leak"] is True, _msg(seed, "on_anchor")
    assert scan["series"]["BABA"]["first_offending_date"] == dates[k].isoformat(), _msg(
        seed, "on_anchor"
    )


# ---------------------------------------------------------------------------
# US-stress then_known valid_from
# ---------------------------------------------------------------------------

def test_a07_05_us_stress_ticker_then_known():
    """Ticker/listing valid_from after earliest close is a violation; equality is not."""
    n_cases = 0
    benches = ["SPY", "QQQ"]
    sector = "XLK"
    all_names = ["T0", "SPY", "QQQ", "XLK"]
    for seed in SEEDS:
        rng = random.Random(seed)
        n = rng.randint(8, 24)
        start = date(2019, 1, 2) + timedelta(days=rng.randint(0, 900))
        stock = _walk_closes(n, start, rng, 100.0)
        closes = {name: _walk_closes(n, start, rng, 50.0 + i) for i, name in enumerate(all_names)}
        closes["T0"] = stock
        earliest = stock[0][0]
        field = rng.choice(("ticker", "listing"))
        mode = seed % 5
        if mode == 0:
            vf = None
            expect_vf = None
        elif mode == 1:
            vf = ""
            expect_vf = None
        elif mode == 2:
            vf = earliest
            expect_vf = None
        elif mode == 3:
            earlier = (date.fromisoformat(earliest) - timedelta(days=rng.randint(1, 40))).isoformat()
            vf = earlier
            expect_vf = None
        else:
            later = (date.fromisoformat(earliest) + timedelta(days=rng.randint(1, 40))).isoformat()
            vf = later
            expect_vf = vf

        entries = [
            {"field": field, "value": "T0", "valid_from": vf, "verified": False},
            {
                "field": "share_class",
                "value": "common",
                "valid_from": (date.fromisoformat(earliest) + timedelta(days=365)).isoformat(),
                "verified": False,
            },
        ]
        if rng.random() < 0.4:
            other_field = "listing" if field == "ticker" else "ticker"
            extra_later = (date.fromisoformat(earliest) + timedelta(days=rng.randint(1, 80))).isoformat()
            entries.append(
                {"field": other_field, "value": "T0", "valid_from": extra_later, "verified": False}
            )
            if extra_later > earliest:
                if expect_vf is None:
                    expect_vf = extra_later
                else:
                    expect_vf = max(expect_vf, extra_later)

        profile = _synth_profile(benches, sector, entries)
        got = _ticker_then_known_violation(profile, stock)
        msg = _msg(seed, "mode_%s_vf_%s" % (mode, vf))
        assert got == expect_vf, msg

        table = stress_table({"T0": profile}, closes, window=5)
        per = table["summaries"]["T0"]
        if expect_vf is not None:
            for b in ("SPY", "QQQ", "XLK"):
                assert per[b]["reason"] == "TICKER_NOT_THEN_KNOWN", msg + " bench=" + b
                assert per[b]["then_known_valid_from"] == expect_vf, msg + " bench=" + b
                assert per[b]["n"] == 0, msg
        else:
            for b in ("SPY", "QQQ", "XLK"):
                assert per[b].get("reason") != "TICKER_NOT_THEN_KNOWN", msg + " bench=" + b

        # Equality pin: earliest close == valid_from is not a violation (`<`).
        eq_entries = [{"field": field, "value": "T0", "valid_from": earliest, "verified": False}]
        eq_profile = _synth_profile(benches, sector, eq_entries)
        assert _ticker_then_known_violation(eq_profile, stock) is None, _msg(
            seed, "equality"
        )
        eq_table = stress_table({"T0": eq_profile}, closes, window=5)
        for b in ("SPY", "QQQ", "XLK"):
            assert eq_table["summaries"]["T0"][b].get("reason") != "TICKER_NOT_THEN_KNOWN", _msg(
                seed, "equality"
            )
        n_cases += 2
    assert n_cases >= 200


def test_a07_06_us_stress_bench_then_known():
    """sector_etf then_known abstains only the matching benchmark value."""
    n_cases = 0
    benches = ["SPY", "QQQ"]
    sector = "XLK"
    all_names = ["T0", "SPY", "QQQ", "XLK"]
    for seed in SEEDS:
        rng = random.Random(seed)
        n = rng.randint(8, 24)
        start = date(2018, 6, 4) + timedelta(days=rng.randint(0, 900))
        closes = {name: _walk_closes(n, start, rng, 40.0 + i) for i, name in enumerate(all_names)}
        earliest = closes["XLK"][0][0]
        later = (date.fromisoformat(earliest) + timedelta(days=rng.randint(1, 30))).isoformat()
        earlier = (date.fromisoformat(earliest) - timedelta(days=rng.randint(1, 30))).isoformat()

        # Matching XLK valid_from after earliest: only XLK abstains.
        match_entries = [
            {"field": "ticker", "value": "T0", "valid_from": None, "verified": False},
            {"field": "sector_etf", "value": "XLK", "valid_from": later, "verified": False},
        ]
        profile = _synth_profile(benches, sector, match_entries)
        msg = _msg(seed, "match_xlk")
        assert _bench_then_known_violation(profile, "XLK", closes["XLK"]) == later, msg
        assert _bench_then_known_violation(profile, "SPY", closes["SPY"]) is None, msg
        assert _bench_then_known_violation(profile, "QQQ", closes["QQQ"]) is None, msg
        table = stress_table({"T0": profile}, closes, window=5)
        per = table["summaries"]["T0"]
        assert per["XLK"]["reason"] == "BENCH_NOT_THEN_KNOWN", msg
        assert per["XLK"]["then_known_valid_from"] == later, msg
        assert per["SPY"].get("reason") != "BENCH_NOT_THEN_KNOWN", msg
        assert per["QQQ"].get("reason") != "BENCH_NOT_THEN_KNOWN", msg

        # Different benchmark value must not abstain XLK / SPY / QQQ.
        other_entries = [
            {"field": "sector_etf", "value": "OTHER_ETF", "valid_from": later, "verified": False},
        ]
        other_profile = _synth_profile(benches, sector, other_entries)
        msg_o = _msg(seed, "other_etf")
        for b in ("XLK", "SPY", "QQQ"):
            assert _bench_then_known_violation(other_profile, b, closes[b]) is None, msg_o
        table_o = stress_table({"T0": other_profile}, closes, window=5)
        for b in ("XLK", "SPY", "QQQ"):
            assert table_o["summaries"]["T0"][b].get("reason") != "BENCH_NOT_THEN_KNOWN", msg_o

        # None / "" never trigger; equality is not a violation.
        for vf, case in ((None, "vf_none"), ("", "vf_empty"), (earliest, "vf_eq"), (earlier, "vf_before")):
            entries = [{"field": "sector_etf", "value": "XLK", "valid_from": vf, "verified": False}]
            p = _synth_profile(benches, sector, entries)
            assert _bench_then_known_violation(p, "XLK", closes["XLK"]) is None, _msg(seed, case)
        n_cases += 2
    assert n_cases >= 200


def test_a07_07_post_cutoff_fact_injection():
    """Injecting a post-cutoff then_known fact into a deepcopy abstains stress_table.

    Committed profile files stay byte-identical.
    """
    before = _profile_fingerprints()
    assert before == PROFILE_FINGERPRINTS
    profiles = load_profiles(PROFILES_DIR)
    tickers = sorted(profiles)
    n_cases = 0
    for seed in SEEDS:
        rng = random.Random(seed)
        ticker = tickers[seed % len(tickers)]
        clone = copy.deepcopy(profiles[ticker])
        n = rng.randint(10, 20)
        # Start after committed ticker/listing valid_from values (META 2022-06-09,
        # GOOGL 2014-04-03, TSLA listing 2010-06-29) so the injection is the
        # sole ticker/listing violation.
        start = date(2024, 1, 2) + timedelta(days=rng.randint(0, 200))
        stock = _walk_closes(n, start, rng, 120.0)
        earliest = date.fromisoformat(stock[0][0])
        vf = (earliest + timedelta(days=1)).isoformat()
        field = rng.choice(("ticker", "listing"))
        control = copy.deepcopy(profiles[ticker])
        assert _ticker_then_known_violation(control, stock) is None, _msg(
            seed, "control_%s" % ticker
        )
        clone.setdefault("then_known", []).append(
            {
                "field": field,
                "value": ticker if field == "ticker" else "NASDAQ",
                "valid_from": vf,
                "valid_to": None,
                "source": "synthetic A07 injection",
                "verified": False,
            }
        )
        benches = list((clone.get("stress_set") or {}).get("benchmarks") or [])
        sector = (clone.get("stress_set") or {}).get("sector_etf")
        names = [ticker] + benches + ([sector] if sector else [])
        closes = {ticker: stock}
        for i, name in enumerate(names):
            if name == ticker:
                continue
            closes[name] = _walk_closes(n, start, rng, 80.0 + i)
        msg = _msg(seed, "inject_%s_%s" % (ticker, field))
        table = stress_table({ticker: clone}, closes, window=5)
        per = table["summaries"][ticker]
        reasons = {b: per[b].get("reason") for b in per}
        assert reasons, msg
        assert all(r == "TICKER_NOT_THEN_KNOWN" for r in reasons.values()), msg + " " + str(reasons)
        for b in per:
            reason = per[b].get("reason") or ""
            assert "THEN_KNOWN" in reason, msg
            assert per[b].get("then_known_valid_from") == vf, msg
        after = _profile_fingerprints()
        assert after == PROFILE_FINGERPRINTS, msg
        n_cases += 1
    after_all = _profile_fingerprints()
    assert after_all == before
    assert n_cases >= 200
