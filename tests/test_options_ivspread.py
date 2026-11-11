"""Pure-function tests for engine/options_ivspread.py — Cremers-Weinbaum call−put IV spread
(directional options confirmer, display-only until the forward-IC gate validates)."""
import json
import math
import sys
from datetime import date

import numpy as np
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from engine import options_ivspread as S  # noqa: E402


def _chain(underlying="XYZ", spot=100.0, call_iv=0.32, put_iv=0.30, days=30, strikes=(0.95, 1.0, 1.05)):
    """A minimal matched-strike chain: at each strike a CALL (call_iv) and a PUT (put_iv), so
    every matched pair's spread = call_iv − put_iv. Two expiries exercise expiry selection."""
    T = days / 365.0
    rows = []
    for exp, t in [("2026-07-21", T), ("2027-01-21", T * 6)]:
        for k_mult in strikes:
            K = spot * k_mult
            rows.append(dict(underlying=underlying, expiry=exp, K=K, T=t, is_call=True,
                             iv=call_iv, delta=0.5, oi=100, gamma=0.01, volume=10,
                             spot=spot, asof="2026-06-21"))
            rows.append(dict(underlying=underlying, expiry=exp, K=K, T=t, is_call=False,
                             iv=put_iv, delta=-0.5, oi=100, gamma=0.01, volume=10,
                             spot=spot, asof="2026-06-21"))
    return pd.DataFrame(rows)


def test_compute_ivspread_calls_richer():
    m = S.compute_ivspread(_chain(call_iv=0.34, put_iv=0.30))
    assert m is not None
    assert abs(m["ivspread"] - 0.04) < 1e-6            # +4 vol pts call-over-put
    assert m["n_pairs"] == 3 and m["weight_kind"] == "oi"
    assert 25 <= m["tenor_days"] <= 35                 # picked the ~30d expiry, not the far one


def test_compute_ivspread_puts_richer():
    m = S.compute_ivspread(_chain(call_iv=0.30, put_iv=0.34))
    assert m["ivspread"] < 0                            # puts richer → negative spread


def test_ivspread_map_multi_underlying():
    chain = pd.concat([_chain("AAA", call_iv=0.36, put_iv=0.30),
                       _chain("BBB", call_iv=0.30, put_iv=0.35)], ignore_index=True)
    mp = S.ivspread_map(chain)
    assert set(mp) == {"AAA", "BBB"}
    assert mp["AAA"]["ivspread"] > 0 and mp["BBB"]["ivspread"] < 0


def test_compute_degrades_empty():
    assert S.compute_ivspread(pd.DataFrame()) is None
    assert S.compute_ivspread(None) is None
    assert S.ivspread_map(None) == {}


# ---- the confirmer -------------------------------------------------------- #
def test_assess_confirm_when_calls_strongly_richer():
    m = S.compute_ivspread(_chain(call_iv=0.35, put_iv=0.30))     # +5 vol pts
    a = S.assess(m)
    assert a["verdict"] == "confirm" and a["score"] >= 1.0
    assert any(r["tone"] == "confirm" for r in a["reasons"])


def test_assess_caution_when_puts_strongly_richer():
    m = S.compute_ivspread(_chain(call_iv=0.30, put_iv=0.35))     # −5 vol pts
    a = S.assess(m)
    assert a["verdict"] == "caution" and a["score"] <= -1.0


def test_assess_neutral_near_parity():
    m = S.compute_ivspread(_chain(call_iv=0.302, put_iv=0.30))    # +0.2 vol pts, inside band
    a = S.assess(m)
    assert a["verdict"] == "neutral" and a["score"] == 0.0


def test_assess_direction_guard_caps_long_on_falling_name():
    m = S.compute_ivspread(_chain(call_iv=0.35, put_iv=0.30))     # would confirm a long
    a = S.assess(m, direction="down")
    assert a["score"] == 0.0 and a["verdict"] == "neutral"


def test_assess_change_reinforces_modest_level():
    m = S.compute_ivspread(_chain(call_iv=0.31, put_iv=0.30))     # +1 vol pt = modest (+0.5)
    assert S.assess(m)["verdict"] == "neutral"                     # modest level alone → neutral
    a = S.assess(m, chg=0.006)                                     # demand building (+0.5) → 1.0
    assert a["verdict"] == "confirm"


def test_assess_thin_pairs_returns_none():
    assert S.assess({"ivspread": 0.04, "n_pairs": 2}) is None      # below min_pairs
    assert S.assess(None) is None


# ---- ledger / disk -------------------------------------------------------- #
def test_snapshot_idempotent_and_prior_map(monkeypatch, tmp_path):
    from lib import config
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    chain = _chain("AAA", call_iv=0.34, put_iv=0.30)
    assert S.snapshot(chain=chain) == 1                            # one underlying added
    assert S.snapshot(chain=chain) == 0                            # same (date,underlying) → idempotent
    led = S.load_history()
    assert led is not None and len(led) == 1
    pm = S.prior_spread_map()
    # GAP DISCIPLINE — COMPARE: the map now carries the row's DATE alongside the value.
    # Discarding it is what let a multi-session drift be narrated "vs the prior session";
    # the adjacency test lives in the caller, which is the only party that knows the
    # current reading's own session (see test_options_gap_discipline.py).
    assert abs(pm["AAA"]["ivspread"] - 0.04) < 1e-6
    assert pm["AAA"]["date"] is not None


def test_build_snapshot_is_context_only(monkeypatch, tmp_path):
    from lib import config
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    pay = S.build_snapshot()
    assert pay["is_context_only"] is True
    assert pay["scored"] is False
    assert pay["schema"] == S.SCHEMA


# --------------------------------------------------------------------------- #
# Regression: _fwd_ic must emit a finite, non-NaN HAC t-stat                  #
# --------------------------------------------------------------------------- #

def test_fwd_ic_hac_t_is_finite_not_nan():
    """Regression guard for the t_hac key bug.

    Before the fix, _fwd_ic used summ.get("t", summ.get("hac_t", ...)) which
    always produces NaN because ic_summary() returns the key 't_hac', not 't'
    or 'hac_t'.  This test creates a synthetic panel large enough to pass the
    6-IC floor in ic_summary and asserts the returned 'hac_t' is a finite float.
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    import numpy as np
    import pandas as pd

    # Build a synthetic panel with a monotone signal.  Strong positive IC so the
    # HAC t-stat is robustly non-NaN across all reasonable random seeds.
    dates = [f"2020-01-{i+2:02d}" for i in range(25)]
    underlyings = [f"SYM{j:02d}" for j in range(15)]

    rows = []
    spot_base = 100.0
    for i, d in enumerate(dates):
        for j, u in enumerate(underlyings):
            rows.append({"date": d, "underlying": u,
                         "ivspread": float(j) / 14.0,  # cross-sectional rank matches j
                         "spot": spot_base + i * 0.5 + j * 0.1})
    panel = pd.DataFrame(rows)

    from scripts.validate_options_ivspread import _fwd_ic
    result = _fwd_ic(panel, h=5)

    assert result["n_dates"] > 0, "Expected non-zero IC dates from synthetic panel"
    hac_t = result.get("hac_t")
    assert hac_t is not None, "_fwd_ic did not return 'hac_t' key"
    assert np.isfinite(float(hac_t)), (
        f"hac_t is {hac_t!r} — expected a finite float. "
        "This indicates the t_hac key is still wrong (ic_summary returns 't_hac', "
        "not 't' or 'hac_t')."
    )


# ---- admitted count qualification and arithmetic -------------------------- #
def _spread_chain(underlying="XYZ"):
    """The sign-reversal witness: all three admitted spreads are positive."""
    frame = _chain(underlying)
    frame = frame[frame["T"] < 0.1].copy().reset_index(drop=True)
    frame["expiry"] = "2026-12-10"
    frame["asof"] = "2026-11-10"
    frame["oi"] = 1.0
    frame["volume"] = 1.0
    frame.loc[frame["is_call"], "iv"] = [0.36, 0.31, 0.31]
    return frame


@pytest.mark.parametrize("basis", ["oi", "volume"])
@pytest.mark.parametrize("bad", [-3.0, -1.0, float("inf"), -float("inf"), "bad", "NaN", ""])
def test_corrupt_active_operand_is_not_rescued_by_fallback(basis, bad):
    chain = _spread_chain()
    if basis == "volume":
        chain["oi"] = 0.0
    chain[basis] = chain[basis].astype(object)
    chain.loc[0, basis] = bad
    # -1 is masked by the positive put leg; -3 reverses the old weighted mean.
    assert S.compute_ivspread(chain) is None
    assert S.assess(S.compute_ivspread(chain)) is None


@pytest.mark.parametrize("basis", ["oi", "volume"])
def test_duplicate_positive_count_cannot_conceal_negative_operand(basis):
    chain = _spread_chain()
    if basis == "volume":
        chain["oi"] = 0.0
    duplicate = chain.iloc[[0]].copy()
    chain.loc[0, basis] = -1.0
    duplicate[basis] = 4.0
    assert S.compute_ivspread(pd.concat([chain, duplicate], ignore_index=True)) is None


@pytest.mark.parametrize("bad", [-1.0, float("inf"), "bad"])
def test_unused_bad_volume_does_not_change_valid_oi_observation(bad):
    chain = _spread_chain()
    expected = S.compute_ivspread(chain)
    chain["volume"] = chain["volume"].astype(object)
    chain.loc[0, "volume"] = bad
    assert S.compute_ivspread(chain) == expected


@pytest.mark.parametrize("missing", [None, pd.NA, float("nan")])
@pytest.mark.parametrize("volume_present", [False, True])
def test_true_nullable_weights_preserve_volume_and_equal_fallback(missing, volume_present):
    chain = _spread_chain()
    chain["oi"] = pd.Series([missing] * len(chain), dtype=object)
    chain["volume"] = 2.0 if volume_present else pd.Series([missing] * len(chain), dtype=object)
    metric = S.compute_ivspread(chain)
    assert metric is not None
    assert metric["weight_kind"] == ("volume" if volume_present else "equal")
    assert metric["ivspread"] == pytest.approx(0.02667, abs=1e-8)


@pytest.mark.parametrize("dtype", ["Float64", "Int64", "UInt64"])
def test_nullable_numeric_dtype_fallback(dtype):
    chain = _spread_chain()
    chain["oi"] = pd.Series([pd.NA] * len(chain), dtype=dtype)
    metric = S.compute_ivspread(chain)
    assert metric is not None and metric["weight_kind"] == "volume"
    assert metric["ivspread"] == pytest.approx(0.02667, abs=1e-8)


@pytest.mark.parametrize("columns,kind", [(("oi",), "volume"), (("oi", "volume"), "equal")])
def test_absent_count_columns_keep_existing_fallback(columns, kind):
    metric = S.compute_ivspread(_spread_chain().drop(columns=list(columns)))
    assert metric is not None and metric["weight_kind"] == kind
    assert metric["ivspread"] == pytest.approx(0.02667, abs=1e-8)


def test_measured_zero_counts_use_equal_weights():
    chain = _spread_chain()
    chain[["oi", "volume"]] = 0.0
    metric = S.compute_ivspread(chain)
    assert metric is not None and metric["weight_kind"] == "equal"
    assert metric["ivspread"] == pytest.approx(0.02667, abs=1e-8)


@pytest.mark.parametrize("exclusion", ["expiry", "orphan", "wing", "iv", "spread"])
@pytest.mark.parametrize("basis", ["oi", "volume"])
def test_corrupt_counts_outside_admitted_support_do_not_suppress_metric(exclusion, basis):
    chain = _spread_chain()
    if basis == "volume":
        chain["oi"] = 0.0
    extra = chain.iloc[[0]].copy()
    extra[basis] = -10.0
    expected_frame = chain
    if exclusion == "expiry":
        extra["expiry"], extra["T"] = "2027-05-09", 180 / 365.0
    elif exclusion == "orphan":
        extra["K"] = 96.0
    elif exclusion == "wing":
        extra["K"] = 150.0
    elif exclusion == "iv":
        extra["iv"] = float("nan")
    else:
        # Both the bad count and the extreme IV are on a pair the incumbent
        # spread rule excludes. The two remaining pairs still provide context.
        chain.loc[0, ["iv", basis]] = [1.0, -10.0]
        extra = chain.iloc[0:0]
        expected_frame = chain[chain["K"] != 95.0]
    expected = S.compute_ivspread(expected_frame)
    actual = S.compute_ivspread(pd.concat([chain, extra], ignore_index=True))
    assert actual == expected and actual is not None


@pytest.mark.parametrize("basis", ["oi", "volume"])
@pytest.mark.parametrize("dtype,scale", [
    ("float32", 1e38),
    ("float64", 5e307),
    ("int64", 2_000_000_000_000_000_000),
    ("uint64", 5_000_000_000_000_000_000),
    ("float64", 5e-323),
    ("float64", 1e-323),
    ("float32", float(np.nextafter(np.float32(0), np.float32(1)))),
])
def test_finite_extreme_operands_preserve_weighted_mean_and_basis(basis, dtype, scale):
    chain = _spread_chain()
    if basis == "volume":
        chain["oi"] = 0.0
    chain[basis] = pd.Series([3 * scale, 3 * scale, scale, scale, 2 * scale, 2 * scale], dtype=dtype)
    metric = S.compute_ivspread(chain)
    assert metric is not None and metric["weight_kind"] == basis
    # True weights 6:2:4 give (.06*6 + .01*2 + .01*4)/12 = .035.
    assert metric["ivspread"] == pytest.approx(0.035, abs=5e-6)
    assert 0.01 - 5e-6 <= metric["ivspread"] <= 0.06 + 5e-6
    assert all(math.isfinite(metric[k]) for k in ("ivspread", "atm_spread", "spot", "tenor_days"))


def test_overflowing_duplicate_leg_is_recomputed_from_original_operands():
    chain = _spread_chain()
    chain["oi"] = 1e308
    chain = pd.concat([chain, chain.iloc[[0]], chain.iloc[[0]]], ignore_index=True)
    metric = S.compute_ivspread(chain)
    assert metric is not None and metric["weight_kind"] == "oi"
    assert metric["ivspread"] == pytest.approx(0.035, abs=5e-6)


def test_excluded_enormous_operand_cannot_underflow_admitted_weights():
    chain = _spread_chain()
    chain["oi"] = 5e-323
    extra = chain.iloc[[0]].copy()
    extra["K"], extra["oi"] = 96.0, 1e308  # unmatched strike
    metric = S.compute_ivspread(pd.concat([chain, extra], ignore_index=True))
    assert metric is not None and metric["weight_kind"] == "oi"
    assert metric["ivspread"] == pytest.approx(0.02667, abs=5e-6)


@pytest.mark.parametrize("n", [1, 2, 3])
def test_thin_pair_context_and_assessment_floor_remain_distinct(n):
    metric = S.compute_ivspread(_spread_chain().iloc[:2 * n])
    assert metric is not None and metric["n_pairs"] == n
    assert (S.assess(metric) is not None) is (n >= 3)


@pytest.mark.parametrize("n", [4, 5])
def test_relative_panel_counts_only_qualified_names_and_keeps_five_name_boundary(n):
    frames = []
    for i in range(n):
        frame = _spread_chain(f"GOOD{i}")
        frame.loc[frame["is_call"], "iv"] = 0.30 + i * 0.01
        frames.append(frame)
    bad = _spread_chain("BAD")
    bad.loc[0, "oi"] = -3.0
    metrics = S.ivspread_map(pd.concat([*frames, bad], ignore_index=True))
    assert set(metrics) == {f"GOOD{i}" for i in range(n)}
    for i in range(n):
        assert metrics[f"GOOD{i}"]["ivspread"] == pytest.approx(i * 0.01)
        expected = i * 0.01 - (0.02 if n == 5 else 0.0)
        assert metrics[f"GOOD{i}"]["ivspread_rel"] == pytest.approx(expected)


@pytest.mark.parametrize("column,value", [
    ("spot", float("inf")), ("spot", -float("inf")), ("spot", float("nan")),
    ("T", float("inf")), ("T", float("nan")),
])
def test_nonfinite_ancillary_fields_are_refused_before_persistence(column, value):
    chain = _spread_chain()
    chain[column] = value
    assert S.compute_ivspread(chain) is None


# ---- real session chain -> ledger -> strict JSON -> complete ticker page -- #
@pytest.fixture
def isolated_storage(monkeypatch, tmp_path):
    from lib import config
    data, site = tmp_path / "data", tmp_path / "site"
    data.mkdir()
    site.mkdir()
    cfg = dict(config.load())
    cfg["storage"] = {
        **cfg["storage"], "data_dir": str(data), "site_dir": str(site),
        "run_status_file": str(data / "run_status.json"),
    }
    monkeypatch.setattr(config, "load", lambda: cfg)
    monkeypatch.setattr(config, "data_dir", lambda: data)
    return data, site


def _write_session_chain(data, chain, day="2026-11-10"):
    path = data / "polygon_gex" / "chains" / f"{day}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    chain.to_parquet(path, index=False)
    return path


def _strict_json(path):
    def reject_constant(value):
        raise AssertionError(f"Nonfinite JSON literal: {value}")
    return json.loads(path.read_text(), parse_constant=reject_constant)


@pytest.mark.parametrize("basis,bad_value", [
    ("oi", -3.0), ("oi", float("inf")),
    ("volume", -3.0), ("volume", float("inf")),
])
def test_complete_writer_withholds_bad_neighbor_before_append_and_preserves_history(
        isolated_storage, basis, bad_value):
    from scripts import build_options_ivspread as writer
    data, site = isolated_storage
    prior = _spread_chain("OLD")
    prior["asof"] = "2026-11-09"
    assert S.snapshot(chain=prior) == 1
    old_rows = S.load_history().copy()

    bad, good = _spread_chain("BAD"), _spread_chain("GOOD")
    if basis == "volume":
        bad["oi"] = 0.0
    bad.loc[0, basis] = bad_value
    _write_session_chain(data, pd.concat([bad, good], ignore_index=True))
    assert writer.main() == 0
    payload = _strict_json(site / "options_ivspread" / "latest.json")
    assert set(payload["names"]) == {"GOOD"}
    assert payload["is_context_only"] is True and payload["scored"] is False
    assert payload["names"]["GOOD"]["ivspread"] == pytest.approx(0.02667)
    history = S.load_history()
    assert set(history["underlying"]) == {"OLD", "GOOD"} and len(history) == 2
    pd.testing.assert_frame_equal(
        history[history["underlying"] == "OLD"].reset_index(drop=True),
        old_rows.reset_index(drop=True))
    assert np.isfinite(history.select_dtypes(include="number").to_numpy()).all()
    path = data / "options_ivspread" / "snapshots.parquet"
    before = path.read_bytes()
    assert writer.main() == 0
    assert path.read_bytes() == before  # actual writer retains append-only identity


def test_all_refused_new_chain_adds_nothing_to_existing_ledger(isolated_storage):
    from scripts import build_options_ivspread as writer
    data, site = isolated_storage
    assert S.snapshot(chain=_spread_chain("OLD")) == 1
    path = data / "options_ivspread" / "snapshots.parquet"
    before = path.read_bytes()
    bad = _spread_chain("BAD")
    bad.loc[0, "oi"] = -3.0
    _write_session_chain(data, bad)
    assert writer.main() == 0
    assert path.read_bytes() == before
    payload = _strict_json(site / "options_ivspread" / "latest.json")
    assert payload["names"] == {} and payload["ranked"] == [] and payload["n"] == 0


@pytest.mark.parametrize("bad", [float("inf"), -float("inf"), float("nan")])
def test_nonfinite_latest_prior_is_withheld_without_rewriting_or_backfilling(isolated_storage, bad):
    data, _ = isolated_storage
    metric = S.compute_ivspread(_spread_chain("AAA"))
    rows = [{"date": "2026-11-09", **metric},
            {"date": "2026-11-10", **metric, "ivspread": bad},
            {"date": "2026-11-10", **metric, "underlying": "BBB"}]
    path = data / "options_ivspread" / "snapshots.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)
    before = path.read_bytes()
    actual = S.prior_spread_map()
    assert set(actual) == {"BBB"}
    assert actual["BBB"]["date"] == date(2026, 11, 10)
    assert path.read_bytes() == before


def test_actual_calendar_selects_session_chain_over_later_weekend_file(isolated_storage):
    data, _ = isolated_storage
    session = _spread_chain("SESSION")
    weekend = _spread_chain("WEEKEND")
    _write_session_chain(data, session, "2026-11-06")
    _write_session_chain(data, weekend, "2026-11-08")
    chain, chosen = S._latest_chain_dated()
    assert chosen == date(2026, 11, 6)
    assert set(chain["underlying"]) == {"SESSION"}


@pytest.mark.parametrize("scored", [False, True])
def test_snapshot_retains_existing_gate_authority(isolated_storage, scored):
    data, _ = isolated_storage
    gate = data / "options_ivspread" / "validation_gate.json"
    gate.parent.mkdir(parents=True, exist_ok=True)
    gate.write_text(json.dumps({"scored": scored, "status": "fixture"}))
    payload = S.build_snapshot()
    assert payload["is_context_only"] is True and payload["scored"] is scored


class _OptionsDialogText:
    """Parse the shipped role=dialog element, including both language spans."""
    @staticmethod
    def read(page):
        from html.parser import HTMLParser
        class Reader(HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)
                self.depth, self.found, self.parts = 0, False, []
            def handle_starttag(self, tag, attrs):
                void = tag in {"area", "base", "br", "col", "embed", "hr", "img",
                               "input", "link", "meta", "param", "source", "track", "wbr"}
                if self.depth:
                    self.depth += int(not void)
                elif dict(attrs).get("id") == "dlg-options":
                    assert dict(attrs).get("role") == "dialog"
                    self.found, self.depth = True, 1
            def handle_startendtag(self, tag, attrs):
                pass
            def handle_endtag(self, tag):
                if self.depth:
                    self.depth -= 1
            def handle_data(self, value):
                if self.depth:
                    self.parts.append(value)
        parser = Reader()
        parser.feed(page)
        assert parser.found and parser.depth == 0
        return " ".join(parser.parts)


@pytest.mark.parametrize("raw,expected", [
    (0.04, "+4.0pp"), (-0.04, "-4.0pp"),
    (0.12, "+12.0pp"), (-0.12, "-12.0pp"),
    (0.005, "+0.5pp"), (0.0, "+0.0pp"), (None, None),
])
def test_actual_writer_to_complete_bilingual_ticker_page(
        isolated_storage, monkeypatch, tmp_path, raw, expected):
    import socket
    from scripts import build_options_ivspread as writer
    from scripts import build_ticker_pages as ticker

    data, site = isolated_storage
    chain = _spread_chain()
    if raw is None:
        chain.loc[0, "oi"] = -3.0
    else:
        chain.loc[chain["is_call"], "iv"] = 0.30 + raw
    _write_session_chain(data, chain)
    assert writer.main() == 0
    emitted = _strict_json(site / "options_ivspread" / "latest.json")
    metric = emitted["names"].get("XYZ")
    if raw is None:
        assert metric is None
    else:
        assert metric["ivspread"] == pytest.approx(raw)
    # Carry the real emitted decimal through the real confirmer to stockdata.
    ivs = S.assess(metric)
    blob = {
        "ticker": "XYZ", "asof": "2026-11-10", "price": {"last": 100.0},
        "profile": {"name": "Fixture XYZ", "sector": "Technology"},
        "valuation": {"pe_ttm": 20.0}, "financials": {"gross_margin": 0.4},
        "gex": {"iv30": 30.0}, "iv_spread": ivs,
    }
    stockdata = site / "stockdata" / "XYZ.json"
    stockdata.parent.mkdir(parents=True, exist_ok=True)
    stockdata.write_text(json.dumps(blob, allow_nan=False))
    membership = data / "universe" / "membership.parquet"
    membership.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"active": True, "ticker": "XYZ", "group": "sp500",
                   "name": "Fixture XYZ", "sector": "Technology"}]).to_parquet(membership)
    monkeypatch.setattr(ticker, "_ROOT", tmp_path)
    monkeypatch.setenv("RENDER_NO_DRIP", "1")  # incumbent offline logo seam
    attempts = []
    def blocked(*args, **kwargs):
        attempts.append("network")
        raise AssertionError("Native page proof must not acquire external inputs")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
    manifest = tmp_path / "render-manifest.json"
    contexts = tmp_path / "contexts"
    assert ticker.run(out=site / "stocks", site=site, context_only=False,
                      dump_context=contexts, only_tickers={"XYZ"},
                      manifest_out=manifest) == 0
    assert attempts == []
    receipt = _strict_json(manifest)
    assert receipt["rendered_count"] == 1 and receipt["failure_count"] == 0
    assert receipt["tickers"] == ["XYZ"]
    page = (site / "stocks" / "XYZ.html").read_text()
    assert len(page) > 10000 and "<html" in page.lower()
    assert 'name="mmx-shell-document"' in page  # actual write_page shell injection
    ctx = _strict_json(contexts / "XYZ.json")
    dialogs = [d for d in ctx["deep"]["dialogs"] if d["id"] == "options"]
    assert len(dialogs) == 1
    dialog = dialogs[0]
    rows = [row for panel in dialog["panels"] for row in panel.get("rows", [])]
    spreads = [row for row in rows if row.get("k_en") == "Call-put IV spread"]
    rendered = _OptionsDialogText.read(page)
    if expected is None:
        assert spreads == [] and "Call-put IV spread" not in rendered
        assert "看涨-看跌IV价差" not in rendered
    else:
        assert len(spreads) == 1 and spreads[0]["v"] == expected
        assert "Call-put IV spread" in rendered and "看涨-看跌IV价差" in rendered
        assert expected in rendered


@pytest.mark.parametrize("raw", [True, float("inf"), -float("inf"), float("nan"), 1e308, -1e308, "bad", None])
def test_consumer_withholds_nonfinite_or_unmeasured_spread(raw):
    from scripts import build_ticker_pages as ticker
    dialog = ticker._deep_options({"gex": {"iv30": 30.0}, "iv_spread": {"ivspread": raw}}, None)
    rows = [row for panel in dialog["panels"] for row in panel.get("rows", [])]
    assert not any(row.get("k_en") == "Call-put IV spread" for row in rows)
