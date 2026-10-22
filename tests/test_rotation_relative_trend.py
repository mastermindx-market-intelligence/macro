"""Contract suite for the W2A weekly sector relative-trend feed (Options R1 freeze §T).

The engine (engine/rotation_relative_trend.py) emits ``sector_rotation.relative_trend.v1``,
the second, named method on Sector Central's rotation map: weekly EMA relative trend
centred on 100, measured on completed calendar-week NYSE endpoints. The Terminal reader
rejects the WHOLE file on any §C violation, so test 11 replays every reader rule against
a mixed feed. Everything here is synthetic: sessions come from lib.nyse_calendar and
prices from a deterministic ratio panel — the committed parquet store is never read.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import nyse_calendar  # noqa: E402

from engine.rotation_relative_trend import (  # noqa: E402
    ANCHOR,
    BENCHMARK,
    BOUNDARY_TOLERANCE,
    EMIT_WEEKS,
    METHOD,
    SCHEMA,
    WARMUP_WEEKS,
    InvalidVintage,
    build_relative_trend_feed,
    completed_week_endpoints,
    ema,
    emit_relative_trend_additive,
    latest_asof,
    relative_trend,
    write_relative_trend_feed,
)

ASOF = date(2026, 10, 16)
#: Session spine shared by every panel: covers the anchor with room to spare.
SESSIONS = nyse_calendar.sessions_between(date(2015, 10, 1), ASOF)


def _panel(ratio: float = 3.0, growth: float | None = None, end: date | None = None,
           benchmark_ratio: float = 1.0):
    """A deterministic (asset, bench) pair indexed by the session spine.

    bench = 100 * 1.0005**n; asset = ratio * bench, or bench * growth**n when a
    growth rate is given. ``end`` truncates the panel at that session."""
    sessions = [d for d in SESSIONS if end is None or d <= end]
    idx = pd.Index([pd.Timestamp(d) for d in sessions], name="session")
    n = np.arange(len(idx), dtype=float)
    bench_vals = benchmark_ratio * 100.0 * 1.0005 ** n
    asset_vals = (bench_vals * growth ** n) if growth is not None else (ratio * bench_vals)
    return pd.Series(asset_vals, index=idx), pd.Series(bench_vals, index=idx)


def _obs(record: list[dict]) -> dict[str, dict]:
    """week_end -> (x, y, status) view of an observation list."""
    return {o["week_end"]: (o["x"], o["y"], o["status"]) for o in record}


# ---------------------------------------------------------------------------
# 1. constant ratio — every measured week sits exactly on the centre (RED-FIRST)
# ---------------------------------------------------------------------------
def test_constant_ratio_places_every_measured_week_on_the_boundary():
    asset, bench = _panel(ratio=3.0)
    obs = relative_trend(asset, bench, asof=ASOF)
    assert obs, "no observations produced"
    n_warm = sum(1 for o in obs if o["status"] == "warming_up")
    n_bound = sum(1 for o in obs if o["status"] == "boundary")
    assert n_warm == WARMUP_WEEKS, f"expected exactly {WARMUP_WEEKS} warming_up weeks, got {n_warm}"
    assert n_warm + n_bound == len(obs), "unexpected third status on a constant panel"
    for i, o in enumerate(obs):
        if i < WARMUP_WEEKS:
            assert o["status"] == "warming_up" and o["x"] is None and o["y"] is None
        else:
            assert o["x"] == 100.0, f"week {o['week_end']} x={o['x']!r}"
            assert o["y"] == 100.0, f"week {o['week_end']} y={o['y']!r}"
            assert o["status"] == "boundary"


# ---------------------------------------------------------------------------
# 2. scale invariance
# ---------------------------------------------------------------------------
def test_scale_invariance_of_x_and_y():
    asset, bench = _panel(ratio=3.0)
    scaled = (asset * 7.0, bench * 0.3)
    base = [(o["week_end"], o["x"], o["y"], o["status"])
            for o in relative_trend(asset, bench, asof=ASOF)]
    rescaled = [(o["week_end"], o["x"], o["y"], o["status"])
                for o in relative_trend(*scaled, asof=ASOF)]
    assert base and base == rescaled


# ---------------------------------------------------------------------------
# 3. compounding out/under-performance reads off-centre
# ---------------------------------------------------------------------------
def test_compounding_outperformance_reads_above_centre():
    # A pure exponential q drives X to a constant asymptote (~120 for +0.3%/session),
    # so y = 100*EMA3(X/X[-3]) rings at ~100.0x forever and the OR-based boundary rule
    # flags many weeks "boundary" even at x=120. The durable claims are the SIDES:
    # outperformance reads x above centre on every measured week (and off the ring
    # often enough to be a live read), the mirror reads below.
    asset, bench = _panel(growth=1.003)
    up = relative_trend(asset, bench, asof=ASOF)
    measured = [o for o in up if o["status"] != "warming_up"]
    assert measured, "no measured weeks"
    for o in measured:
        assert o["status"] in ("observed", "boundary"), \
            f"{o['week_end']}: {o['status']} x={o['x']}"
        assert o["x"] > 100.0, f"{o['week_end']} x={o['x']}"
    n_observed = sum(1 for o in measured if o["status"] == "observed")
    assert n_observed >= 100, f"only {n_observed} observed weeks off the ring"
    dn = relative_trend(bench * 0.997 ** np.arange(len(asset), dtype=float), bench, asof=ASOF)
    measured_dn = [o for o in dn if o["status"] != "warming_up"]
    assert measured_dn
    for o in measured_dn:
        assert o["x"] < 100.0, f"{o['week_end']} x={o['x']}"


# ---------------------------------------------------------------------------
# 4. Good Friday 2024 — the week's endpoint is its Thursday
# ---------------------------------------------------------------------------
def test_week_end_is_thursday_when_good_friday_closes_the_market():
    asset, bench = _panel()
    obs = relative_trend(asset, bench, asof=ASOF)
    week_ends = [o["week_end"] for o in obs]
    assert "2024-03-28" in week_ends, "Good Friday week must end on Thu 2024-03-28"
    assert "2024-03-22" in week_ends, "the holiday-free week before must end on its Friday"
    i = week_ends.index("2024-03-28")
    assert week_ends[i - 1] == "2024-03-22", "endpoints must stay strictly consecutive weeks"


# ---------------------------------------------------------------------------
# 5. missing endpoint — reported, never backshifted (RED-FIRST)
# ---------------------------------------------------------------------------
def test_missing_endpoint_is_reported_and_never_backshifted():
    asset, bench = _panel(ratio=3.0)
    unbroken = relative_trend(asset, bench, asof=ASOF)
    dropped = pd.Timestamp(date(2025, 6, 13))
    assert dropped in asset.index, "2025-06-13 must be a session on the panel"
    asset2 = asset.drop(dropped)
    broken = relative_trend(asset2, bench, asof=ASOF)
    view = _obs(broken)
    assert view["2025-06-13"] == (None, None, "missing_endpoint")
    assert "2025-06-12" not in view, "a Thursday substitute is a backshift — forbidden"
    base = _obs(unbroken)
    assert set(view) == set(base), "the calendar of weeks must not move"
    for wk, triple in view.items():
        if wk != "2025-06-13":
            assert triple == base[wk], f"week {wk} drifted: {triple} != {base[wk]}"


# ---------------------------------------------------------------------------
# 6. non-positive / non-finite closes are invalid input, not fed, not fatal
# ---------------------------------------------------------------------------
def test_nonpositive_or_nonfinite_close_is_invalid_input():
    asset, bench = _panel(ratio=3.0)
    eps = completed_week_endpoints(ASOF)
    poisoned = {eps[200]: 0.0, eps[240]: -5.0, eps[280]: np.nan}
    asset2 = asset.copy()
    for e, v in poisoned.items():
        asset2.loc[pd.Timestamp(e)] = v
    obs = relative_trend(asset2, bench, asof=ASOF)
    view = _obs(obs)
    for e in poisoned:
        assert view[e.isoformat()] == (None, None, "invalid_input"), f"week {e}"
    tail = [o for o in obs if o["week_end"] > max(poisoned).isoformat()
            and o["status"] != "warming_up"]
    assert tail
    for o in tail:
        assert o["x"] is not None and math.isfinite(o["x"]), f"{o['week_end']} x={o['x']!r}"
        assert o["y"] is not None and math.isfinite(o["y"]), f"{o['week_end']} y={o['y']!r}"


# ---------------------------------------------------------------------------
# 7. duplicated session rows -> InvalidVintage, isolated per series in the feed
# ---------------------------------------------------------------------------
def test_duplicate_session_rows_reject_the_series_as_invalid_vintage():
    asset, bench = _panel(ratio=3.0)
    dup = pd.concat([asset, asset.iloc[[-1]]])
    assert dup.index.duplicated().any()
    with pytest.raises(InvalidVintage):
        relative_trend(dup, bench, asof=ASOF)
    # A frame's index is shared by every column, so the duplicated row rides in a
    # series-level mapping — the only fixture that can poison ONE sector and leave
    # its neighbours measured.
    closes = {"SPY": bench, "CLEAN": asset, "DUPX": dup}
    sectors = [("clean", "CLEAN"), ("absent", "ABSENT"), ("dupx", "DUPX")]
    feed = build_relative_trend_feed(closes, sectors)
    by_id = {s["id"]: s for s in feed["sectors"]}
    assert by_id["dupx"]["observations"] == []
    assert by_id["dupx"]["reason"] == "invalid_vintage"
    assert by_id["absent"]["reason"] == "no_series"
    assert len(by_id["clean"]["observations"]) > 0 and "reason" not in by_id["clean"]


# ---------------------------------------------------------------------------
# 8. vintage stability and forward-only correction (RED-FIRST)
# ---------------------------------------------------------------------------
def test_vintage_is_stable_and_moves_only_from_the_corrected_week_forward():
    asset, bench = _panel(ratio=3.0)
    run1 = relative_trend(asset, bench, asof=ASOF)
    run2 = relative_trend(asset, bench, asof=ASOF)
    assert [(o["week_end"], o["x"], o["y"], o["status"], o["vintage"]) for o in run1] == \
           [(o["week_end"], o["x"], o["y"], o["status"], o["vintage"]) for o in run2]

    fixed_week = "2024-02-09"
    asset2 = asset.copy()
    asset2.loc[pd.Timestamp(date(2024, 2, 9))] = float(asset.loc[pd.Timestamp(date(2024, 2, 9))]) * 1.07
    run3 = relative_trend(asset2, bench, asof=ASOF)
    v1 = {o["week_end"]: o["vintage"] for o in run1}
    v3 = {o["week_end"]: o["vintage"] for o in run3}
    assert set(v1) == set(v3)
    moved = [wk for wk in v1 if v1[wk] != v3[wk]]
    assert fixed_week in moved, "the corrected week's own vintage must move"
    assert moved == [wk for wk in v1 if wk >= fixed_week], \
        "a correction may only move vintages from its own week forward"
    c1 = _obs(run1)
    c3 = _obs(run3)
    for wk in [w for w in v1 if w < fixed_week]:
        assert c1[wk] == c3[wk], f"earlier week {wk} changed after a later correction"


# ---------------------------------------------------------------------------
# 9. prefix expansion leaves shared history untouched
# ---------------------------------------------------------------------------
def test_prefix_expansion_leaves_shared_history_unchanged():
    short_end = date(2026, 8, 14)
    asset_s, bench_s = _panel(ratio=3.0, end=short_end)
    asset_f, bench_f = _panel(ratio=3.0)
    short = relative_trend(asset_s, bench_s, asof=short_end)
    full = relative_trend(asset_f, bench_f, asof=ASOF)
    vs = _obs(short)
    vf = {o["week_end"]: o for o in full}
    assert short and len(short) < len(full)
    short_vint = {o["week_end"]: o["vintage"] for o in short}
    full_vint = {o["week_end"]: o["vintage"] for o in full}
    for wk, triple in vs.items():
        o = vf[wk]
        assert (o["x"], o["y"], o["status"]) == triple, f"week {wk} changed when the prefix grew"
        assert full_vint[wk] == short_vint[wk], f"week {wk} vintage changed when the prefix grew"


# ---------------------------------------------------------------------------
# 10. the SMA seed rule, and its (vanishing) sensitivity
# ---------------------------------------------------------------------------
def test_ema_seed_rule_and_seed_sensitivity_report():
    assert ema([1, 2, 3, 4, 5], 3) == [None, None, 2.0, 3.0, 4.0]
    assert ema([1.0, 2.0], 3) == [None, None], "input shorter than span must be all None"

    def sma_seeded(values: list[float], span: int) -> list[float | None]:
        return ema(values, span)

    def first_seeded(values: list[float], span: int) -> list[float | None]:
        alpha = 2.0 / (span + 1)
        out: list[float | None] = [None] * (span - 1)
        out.append(float(values[span - 1]))  # alternative rule: seed on the first span-1... first value
        for i in range(span, len(values)):
            out.append(alpha * values[i] + (1 - alpha) * out[i - 1])
        return out

    rng = np.random.default_rng(7)
    n = 400
    noisy = (100.0 * (1 + 0.01 * np.sin(np.arange(n) / 3.7)
                      + rng.normal(0.0, 0.02, n))).tolist()
    worst = 0.0
    for span in (10, 20):
        a = sma_seeded(noisy, span)
        b = first_seeded(noisy, span)
        for i in range(119, n):
            rel = abs(a[i] - b[i]) / max(abs(a[i]), 1e-12)
            worst = max(worst, rel)
    print(f"seed-sensitivity: max relative SMA-vs-first-value seed difference at position >=120: {worst:.3e}")
    assert worst < 0.01, f"seed choice still matters at position 120: {worst:.3e}"


# ---------------------------------------------------------------------------
# 11. the whole-file Terminal contract (§C)
# ---------------------------------------------------------------------------
def _hexok(s) -> bool:
    return isinstance(s, str) and len(s) == 64 and all(c in "0123456789abcdef" for c in s)


def test_feed_contract_matches_the_terminal_reader():
    asset, bench = _panel(ratio=3.0)
    dup = pd.concat([asset, asset.iloc[[-1]]])
    closes = pd.DataFrame({"SPY": bench, "CLEAN": asset, "DUPX": dup})
    sectors = [("clean", "CLEAN"), ("absent", "ABSENT"), ("dupx", "DUPX")]
    feed = build_relative_trend_feed(closes, sectors)

    assert list(feed.keys()) == ["meta", "sectors"], "top-level keys exactly meta and sectors"
    meta = feed["meta"]
    assert list(meta.keys()) == ["schema", "asOf", "vintage", "method"]
    assert meta["schema"] == SCHEMA == "sector_rotation.relative_trend.v1"
    assert meta["asOf"] == ASOF.isoformat()
    assert _hexok(meta["vintage"])
    assert list(meta["method"].keys()) == list(METHOD.keys()), "method key order is frozen"
    assert meta["method"] == METHOD
    assert meta["method"]["center"] == 100 and isinstance(meta["method"]["center"], int)
    assert isinstance(meta["method"]["warmup_weeks"], int) and isinstance(meta["method"]["trail_weeks"], int)
    assert isinstance(meta["method"]["boundary_tolerance"], float)

    dump = json.dumps(feed["sectors"], separators=(",", ":"), sort_keys=True)
    assert meta["vintage"] == hashlib.sha256(dump.encode()).hexdigest()

    assert len(feed["sectors"]) <= 100
    seen_ids = set()
    for s in feed["sectors"]:
        assert list(s.keys())[:4] == ["id", "ticker", "kind", "observations"]
        assert set(s.keys()) in ({"id", "ticker", "kind", "observations"},
                                 {"id", "ticker", "kind", "observations", "reason"})
        assert 1 <= len(s["id"]) <= 32 and s["id"][0].islower() and s["id"] == s["ticker"].lower()
        assert s["ticker"][0].isupper() and len(s["ticker"]) <= 12
        assert s["kind"] == "sector"
        assert s["id"] not in seen_ids
        seen_ids.add(s["id"])
        obs = s["observations"]
        if not obs:
            assert isinstance(s.get("reason"), str) and 0 < len(s["reason"]) <= 120
            continue
        assert "reason" not in s, "a series with observations must not carry reason"
        assert len(obs) <= EMIT_WEEKS <= 600
        prev = None
        for o in obs:
            assert list(o.keys()) == ["week_end", "x", "y", "status", "vintage"]
            assert o["status"] in ("observed", "boundary", "warming_up",
                                   "missing_endpoint", "invalid_input")
            if prev is not None:
                assert o["week_end"] > prev, "week_end must strictly increase"
            prev = o["week_end"]
            assert o["week_end"] <= meta["asOf"]
            assert _hexok(o["vintage"])
            if o["status"] in ("observed", "boundary"):
                assert isinstance(o["x"], float) and math.isfinite(o["x"])
                assert 1.0 <= o["x"] <= 10000.0
                assert isinstance(o["y"], float) and math.isfinite(o["y"])
                assert 1.0 <= o["y"] <= 10000.0
            else:
                assert o["x"] is None and o["y"] is None

    round_trip = json.loads(json.dumps(feed))
    assert round_trip == feed, "the feed must round-trip through JSON unchanged"
    text = json.dumps(feed, separators=(",", ":"), ensure_ascii=False)
    assert json.loads(text) == feed


# ---------------------------------------------------------------------------
# 12. the emitter is additive and never fatal
# ---------------------------------------------------------------------------
def test_emitter_is_additive_and_never_fatal(tmp_path):
    def raising_loader():
        raise RuntimeError("no store in this lane")

    res = emit_relative_trend_additive(tmp_path, closes_loader=raising_loader)
    assert res is None, "a failing loader must return None, never raise"
    assert list(tmp_path.iterdir()) == [], "a failed emit must write nothing"

    asset, bench = _panel(ratio=3.0)
    closes = pd.DataFrame({"SPY": bench, "CLEAN": asset})
    res2 = emit_relative_trend_additive(tmp_path, closes_loader=lambda: closes,
                                        sectors=[("clean", "CLEAN")])
    assert res2 == tmp_path / "sector_rotation_relative_trend.json"
    assert res2.exists()
    feed = json.loads(res2.read_text(encoding="utf-8"))
    assert list(feed.keys()) == ["meta", "sectors"]
    assert feed["meta"]["schema"] == SCHEMA
    assert feed["sectors"][0]["observations"]

    write_relative_trend_feed(tmp_path / "nested" / "out.json", feed)
    assert (tmp_path / "nested" / "out.json").exists()

    src = (ROOT / "scripts" / "build_sector_central.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    in_try = any(isinstance(node, ast.Try) and "emit_relative_trend_additive" in ast.dump(node)
                 for node in ast.walk(tree))
    assert in_try, "the hook call must sit inside a try block in scripts/build_sector_central.py"
    try:  # import the module only where its own module-scope imports can resolve
        import jinja2  # noqa: F401
        from scripts.build_sector_central import main  # noqa: F401
    except ImportError as e:  # pragma: no cover — jinja2 missing in a slim venv
        raise AssertionError(f"scripts.build_sector_central not importable here: {e}")


# ---------------------------------------------------------------------------
# 13. the CI manifest declares the job
# ---------------------------------------------------------------------------
def test_ci_manifest_declares_the_job():
    import yaml
    doc = yaml.safe_load((ROOT / ".github" / "ci" / "legacy-jobs.yml").read_text(encoding="utf-8"))
    jobs = doc["jobs"] if isinstance(doc, dict) and "jobs" in doc else doc
    job = jobs.get("options-r1-rotation-relative-trend")
    assert job is not None, "the job must be declared"
    assert job.get("gate") == "code"
    paths = job.get("paths") or []
    for need in ("engine/rotation_relative_trend.py",
                 "tests/test_rotation_relative_trend.py",
                 "scripts/build_sector_central.py"):
        assert need in paths, f"paths must cover {need}"
    runs = [st.get("run", "") for st in job.get("steps", []) if isinstance(st, dict)]
    assert any("tests/test_rotation_relative_trend.py" in r for r in runs), \
        "a step must run the new suite"
