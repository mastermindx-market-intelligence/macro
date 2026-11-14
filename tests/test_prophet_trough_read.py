"""Synthetic causal-feed acceptance. Real-source parity is an explicit raw run."""
import copy
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from jsonschema import ValidationError

from engine import canon
from engine.stock_identity.replay import grey_dot as gd
from engine.stock_identity.replay.grid import macro_grid
from engine.trough_read import causal_fires, completed_bars, own_history, stock_read, washed_out
from scripts.build_prophet_trough_read import build, publish, validate


def tape(n=1500):
    rng = np.random.default_rng(42)
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(0, .025, n))),
                     index=pd.bdate_range("2018-01-01", periods=n))


def reference_fires(c):
    # Independent literal reference of the accepted causal_fires definition.
    mask, _, grid = gd._terminal_dot_mask(c)
    known = pd.DatetimeIndex(grid.known)
    two = gd._period_last_session(c, "2B")
    if len(two) < canon.BASE_LEN + canon.SIG_LEN:
        return pd.DatetimeIndex([])
    m, s = canon.rsi_macd(pd.Series(two.close.to_numpy()))
    h = m - s
    rise = (h > h.shift()).fillna(False).to_numpy()
    first = c.resample("2B").apply(lambda z: z.index[0] if len(z) else pd.NaT).dropna()
    avail = pd.DatetimeIndex(first.iloc[1:len(two) + 1])
    ix = avail.searchsorted(known, side="right") - 1
    good = ix >= 0
    out = np.zeros(len(mask), bool)
    out[good] = rise[ix[good]]
    out &= ix + 1 >= canon.BASE_LEN + canon.SIG_LEN
    return known[mask & out]


def test_washout_boundary_window():
    assert not washed_out(pd.Series([20.] * 10)).any()
    d = pd.Series([19.] + [30.] * 9)
    assert not washed_out(d).iloc[:7].any()
    assert washed_out(d).iloc[7]
    assert not washed_out(d).iloc[8:].any()


def test_causal_filtered_mask_and_latest_turn():
    c = tape()
    expected = reference_fires(c)
    assert len(expected) > 0
    pd.testing.assert_index_equal(causal_fires(c), expected)
    row = stock_read(c, group_id="Technology", group_name="Technology")
    tf = row["timeframes"][1]
    assert tf["turned_up"] == (pd.Timestamp(tf["bar_end"]) in expected)
    assert row["known_ts"] == expected[-1].tz_localize("UTC").isoformat()


@pytest.mark.parametrize("tf", ["3D", "1W", "2W"])
def test_partial_bar_guard(tf):
    c = tape()
    # Every prefix must retain only the replay's completed bars, not a future tail.
    for offset in range(8):
        prefix = c.iloc[:len(c) - offset]
        bars, known = completed_bars(prefix, tf)
        if tf == "3D":
            grid = macro_grid(prefix, 3)
            pd.testing.assert_index_equal(known, pd.DatetimeIndex(grid.known[grid.completed_mask()]))
            np.testing.assert_array_equal(bars, grid.close.to_numpy()[grid.completed_mask()])
        else:
            rule = "W-FRI" if tf == "1W" else "2W-FRI"
            expected = gd._period_last_session(prefix, rule)
            pd.testing.assert_index_equal(known, pd.DatetimeIndex(expected.known))
            assert known[-1] < prefix.index[-1]
        assert known[-1] <= prefix.index[-1]


def test_own_history_strict_prior_minimum_and_percentile():
    c = tape()
    assert own_history(c, pd.DatetimeIndex(c.index[-2:])) is None
    fires = pd.DatetimeIndex(c.index[-4:])
    result = own_history(c, fires)
    assert result["n_prior"] == 3
    assert all(pd.Timestamp(p["date"]) < c.index[-1] for p in result["past"])
    assert result["own_history_pct"] == np.mean([p["depth_atrc"] <= result["depth_atrc"] for p in result["past"]])


def payload():
    c = tape()
    return build(population=[("TEST", c, None, "Test", "Technology")],
                 sources={"complete": True}, now=datetime(2023, 10, 2, 23, tzinfo=timezone.utc))


def test_json_schema_and_shape(tmp_path):
    p = payload()
    validate(p)
    row = p["tickers"]["TEST"]
    assert [t["tf"] for t in row["timeframes"]] == ["1D", "3D", "1W", "2W"]
    assert all(t["turned_up"] is None for t in row["timeframes"] if t["tf"] != "3D")
    target = tmp_path / "trough_read.json"
    publish(p, target)
    assert target.is_file()
    for mutate in (lambda p: p.update(schema="other"),
                   lambda p: p["tickers"]["TEST"]["timeframes"].reverse(),
                   lambda p: p["tickers"]["TEST"].update(kind={"position": .2})):
        invalid = copy.deepcopy(p)
        mutate(invalid)
        with pytest.raises(ValidationError):
            validate(invalid)


def test_cutoff_missing_and_stale_sources():
    c = tape()
    now = datetime(2023, 10, 2, 23, tzinfo=timezone.utc)
    p = build(population=[("TEST", c, None, "Test", "Technology")], now=now)
    assert p["tickers"]["TEST"]["as_of"] <= p["as_of"]
    assert p["status"] == "stale"
    row = p["tickers"]["TEST"]
    assert row["own_history"] is None
    assert all(not tf["available"] and tf["washed_out"] is None
               and tf["turned_up"] is None and tf["d"] is None
               and all(value is None for value in tf["components"].values())
               for tf in row["timeframes"])
    assert build(population=[], now=now)["status"] == "unavailable"
    assert build(population=[("TEST", c, None, "Test", "Technology")],
                 sources={"complete": False}, now=now)["status"] == "unavailable"


def test_publish_rejects_invalid_payload_without_replacing_output(tmp_path):
    target = tmp_path / "trough_read.json"
    target.write_text("accepted previous output")
    invalid = payload()
    invalid["schema"] = "other"
    with pytest.raises(ValidationError):
        publish(invalid, target)
    assert target.read_text() == "accepted previous output"


@pytest.mark.parametrize("temporary", [False, True])
def test_publish_rejects_symlinks(tmp_path, temporary):
    target = tmp_path / "trough_read.json"
    victim = tmp_path / "previous.json"
    victim.write_text("untouched")
    link = target.with_suffix(".json.tmp") if temporary else target
    link.symlink_to(victim)
    with pytest.raises(ValueError, match="symlinked"):
        publish(payload(), target)
    assert victim.read_text() == "untouched"


def test_nightly_publication_closure():
    root = Path(__file__).resolve().parents[1]
    nightly = (root / "scripts/ci/daily_engine_prophet_nightly.sh").read_text()
    checkpoint = (root / "scripts/ci/daily_engine_prophet_checkpoint.sh").read_text()
    assert nightly.count('"site/prophet/trough_read.json"') == 2
    assert "site/prophet/trough_read.json|" in checkpoint
    # Description-only feed: it runs after build_prophet succeeds, and its own
    # failure is a warning that can never change rc (plan binding/ledger).
    assert "if ! python -m scripts.build_prophet_trough_read 2>&1; then" in nightly
    assert "scripts.build_prophet_trough_read 2>&1; rc=$?" not in nightly
    assert "build_prophet_trough_read failed; site/prophet/trough_read.json not refreshed" in nightly
