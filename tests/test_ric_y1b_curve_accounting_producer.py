"""RIC Y1b: curve accounting reaches the transmission snapshot and the command board.

Additive producer (engine/rate_inflation_transmission.py -> snapshot curve_accounting key)
and passthrough board (engine/rates_inflation_command.py). Display-only, fail-open.
PIT term_premium_10y note correction (Kim-Wright, not ACM)."""
from __future__ import annotations

import datetime
import json
import math
import sys
import tempfile
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd
import pytest

import engine.rate_inflation_transmission as rit
import engine.rates_inflation_command as ric
from engine import yield_momentum as ym
from engine.pit import DEFAULT_RELEASE_LAGS


# --- base board key order (captured STEP 0; engine UNEDITED) --------------------
# C0 lane addition (2026-10-14): `board_generation` (generation integrity
# stamp) and `inflation_lenses` (verbatim I0 carry) were appended beside
# curve_accounting by RIC-W7 §2.11e. The base order was preserved up to
# `qualified_comparisons`; the two new keys land AFTER `curve_accounting`
# and `curve_accounting_export` so the suffix carries them in the order
# pinned by C0 (board_generation before inflation_lenses).
_BASE_BOARD_KEYS = [
    'schema', 'asof', 'built', 'display_only', 'authority', 'board',
    'expectations_pressure', 'divergence', 'conditions', 'market_check',
    'yield_momentum', 'caveats', 'stance', 'changes', 'prev_state',
    'basis_contract_version', 'qualified_comparisons',
]


# --- helpers --------------------------------------------------------------------

def _golden_frame(n: int = 400, start: str = "2019-01-01") -> pd.DataFrame:
    """Body of _synthetic_frame verbatim (same columns, same rng), plus
    term_premium_10y drawn from the SAME rng AFTER all existing draws."""
    idx = pd.bdate_range(start, periods=n)
    rng = np.random.default_rng(7)
    walk = lambda base, vol: base + np.cumsum(rng.normal(0, vol, n))  # noqa: E731
    f = pd.DataFrame(index=idx)
    f["us10y"] = walk(3.5, 0.03)
    f["us10y_real"] = walk(1.5, 0.03)
    f["breakeven_10y"] = f["us10y"] - f["us10y_real"]
    f["breakeven_5y5y"] = walk(2.3, 0.02)
    f["spread_2s10s"] = walk(0.2, 0.02)
    f["curve_tp_adj"] = f["spread_2s10s"] + walk(0.1, 0.01)
    f["rate_expectations_proxy"] = walk(-0.3, 0.02)
    f["core_pce_yoy"] = walk(3.0, 0.01)
    f["core_pce_3m_ann"] = f["core_pce_yoy"] + walk(0.0, 0.02)
    f["core_cpi_yoy"] = walk(3.2, 0.01)
    f["headline_cpi_yoy"] = walk(3.4, 0.02)
    f["ppi_core_yoy"] = walk(2.8, 0.02)
    f["eci_comp_yoy"] = walk(3.3, 0.005)
    f["infl_exp_5y"] = walk(2.4, 0.005)
    f["umich_infl_exp"] = walk(3.0, 0.01)
    f["cpi_core_services_yoy"] = walk(4.0, 0.01)
    f["cpi_shelter_yoy"] = walk(4.2, 0.01)
    f["term_premium_10y"] = 0.40 + np.cumsum(rng.normal(0, 0.01, n))
    return f


def _canon(obj):
    """Recursive canonicaliser for byte-equal JSON comparison.

    dict -> dict with str(k) keys in the SAME order;
    list/tuple -> list; numpy scalar -> .item(); numpy array -> .tolist();
    pd.Timestamp, datetime.date, datetime.datetime -> .isoformat();
    bool/int/float/str/None unchanged (NaN kept); else -> str(obj)."""
    if isinstance(obj, dict):
        return {str(k): _canon(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_canon(v) for v in obj]
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return _canon(obj.tolist())
    if isinstance(obj, (pd.Timestamp, datetime.date, datetime.datetime)):
        return obj.isoformat()
    if isinstance(obj, (bool, int, float, str)) or obj is None:
        return obj
    return str(obj)


def _snapshot_isolated(f: pd.DataFrame) -> dict:
    """Run rit.snapshot(f) with the calibration/config patched out so the
    output is deterministic across machines (the unit under test is the
    snapshot dict shape, not the calibration server)."""
    with mock.patch.object(rit, "load_calibration", return_value=None), \
         mock.patch.object(rit.config, "load", return_value={}):
        return rit.snapshot(f)


def _golden_snapshot_bytes() -> bytes:
    """Snapshot of the golden frame, canonicalised, packed as bytes.

    Used by the fixture generator; the body of snapshot() at the time this
    runs is the UNEDITED engine (no curve_accounting key)."""
    return json.dumps(
        _canon(_snapshot_isolated(_golden_frame())),
        allow_nan=True, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")


_FIXTURE = Path(__file__).parent / "fixtures" / "ric_y1b_snapshot_base.json"


def _same(a, b, path: str = "$") -> None:
    """Recursive equality with strict key order + numeric tolerance. Raise the
    first differing path."""
    if isinstance(a, dict):
        assert isinstance(b, dict), f"{path}: type {type(b).__name__}"
        assert list(a) == list(b), f"{path}: dict key order or set differs: {list(a)} vs {list(b)}"
        for k in a:
            _same(a[k], b[k], f"{path}.{k}")
        return
    if isinstance(a, list):
        assert isinstance(b, list), f"{path}: type {type(b).__name__}"
        assert len(a) == len(b), f"{path}: list length {len(a)} vs {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            _same(x, y, f"{path}[{i}]")
        return
    if isinstance(a, float) or isinstance(b, float):
        a_is_nan = isinstance(a, float) and math.isnan(a)
        b_is_nan = isinstance(b, float) and math.isnan(b)
        if a_is_nan and b_is_nan:
            return
        assert type(a) is type(b), f"{path}: float vs {type(b).__name__}"
        assert math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12), \
            f"{path}: {a!r} vs {b!r}"
        return
    assert type(a) == type(b), f"{path}: {type(a).__name__} vs {type(b).__name__}"
    assert a == b, f"{path}: {a!r} vs {b!r}"


# --- T1 -------------------------------------------------------------------------

def test_y1b_snapshot_carries_curve_accounting_as_last_key():
    snap = _snapshot_isolated(_golden_frame())
    assert list(snap)[-1] == "curve_accounting"
    ca = snap["curve_accounting"]
    assert isinstance(ca, dict)
    assert ca["schema"] == ym.CURVE_ACCOUNTING_SCHEMA
    assert ca["calculation_version"] == ym.CURVE_ACCOUNTING_VERSION
    assert ca["status"] == "available"


# --- T2 -------------------------------------------------------------------------

def test_y1b_existing_snapshot_keys_are_invariant():
    post = _canon(_snapshot_isolated(_golden_frame()))
    post.pop("curve_accounting")
    base = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    _same(post, base)


# --- T3 -------------------------------------------------------------------------

def test_y1b_snapshot_uses_the_same_frame():
    f = _golden_frame()
    ca = _snapshot_isolated(f)["curve_accounting"]
    assert ca == ym.build_curve_accounting(f)


# --- T4 -------------------------------------------------------------------------

def test_y1b_fail_open_on_runtime_error(monkeypatch):
    monkeypatch.setattr(
        ym, "build_curve_accounting",
        lambda frame, *, cutoff=None: (_ for _ in ()).throw(RuntimeError("boom\n  line2")),
    )
    snap = _snapshot_isolated(_golden_frame())
    assert isinstance(snap, dict)
    ca = snap["curve_accounting"]
    assert ca["status"] == "unavailable"
    assert ca["reason"] == "RuntimeError: boom line2"
    assert ca["observations"] == {}
    assert ca["comparisons"] == {}
    assert ca["accounting_views"] == []
    assert ca["display_only"] is True
    assert ca["authority"] is False
    assert ca["can_score"] is False
    assert ca["can_size"] is False
    assert ca["can_trade"] is False
    assert ca["basis_schema"] is None
    # Every other snapshot key equals the unpatched snapshot (canonicalised).
    unpatched = _canon(_snapshot_isolated(_golden_frame()))
    unpatched.pop("curve_accounting")
    other = _canon(snap)
    other.pop("curve_accounting")
    _same(other, unpatched)


# --- T5 -------------------------------------------------------------------------

def test_y1b_fail_open_on_import_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "engine.yield_momentum", None)
    snap = _snapshot_isolated(_golden_frame())
    assert isinstance(snap, dict)
    ca = snap["curve_accounting"]
    assert ca["status"] == "unavailable"
    assert ca["reason"].split(":")[0] in ("ImportError", "ModuleNotFoundError")


# --- T6 -------------------------------------------------------------------------

def test_y1b_fail_open_on_non_dict_return(monkeypatch):
    monkeypatch.setattr(ym, "build_curve_accounting", lambda frame, *, cutoff=None: None)
    snap = _snapshot_isolated(_golden_frame())
    ca = snap["curve_accounting"]
    assert ca["status"] == "unavailable"
    assert ca["reason"].startswith("TypeError: ")


# --- T7 -------------------------------------------------------------------------

def test_y1b_both_shells_match_the_producer_contract():
    keys = list(ym.build_curve_accounting(pd.DataFrame()))
    # Producer shell (forced via a RuntimeError monkeypatch):
    with mock.patch.object(
        ym, "build_curve_accounting",
        lambda frame, *, cutoff=None: (_ for _ in ()).throw(RuntimeError("shell-probe")),
    ):
        prod_shell = _snapshot_isolated(_golden_frame())["curve_accounting"]
    board_shell = ric._curve_accounting_board_shell("x")
    for shell in (prod_shell, board_shell):
        assert list(shell) == keys
        assert shell["schema"] == ym.CURVE_ACCOUNTING_SCHEMA
        assert shell["calculation_version"] == ym.CURVE_ACCOUNTING_VERSION
        assert shell["status"] == "unavailable"


# --- T8 -------------------------------------------------------------------------

def test_y1b_board_passes_curve_accounting_through_verbatim(tmp_path):
    ca = json.loads(json.dumps(ym.build_curve_accounting(_golden_frame())))
    ca["reason"] = "y1b-sentinel-7f3a"
    tx_dir = tmp_path / "transmission"
    tx_dir.mkdir(parents=True)
    (tx_dir / "latest.json").write_text(
        json.dumps({"asof": ca["asof"], "curve_accounting": ca}),
        encoding="utf-8",
    )
    out = ric.build_board(root=tmp_path)["curve_accounting"]
    assert json.dumps(out) == json.dumps(ca)
    assert out["reason"] == "y1b-sentinel-7f3a"
    assert out["basis_schema"] == ca["basis_schema"]
    assert out["calculation_version"] == ca["calculation_version"]
    assert out["cutoff"] == ca["cutoff"]
    assert out["asof"] == ca["asof"]
    for k in ca["observations"]:
        assert out["observations"][k] == ca["observations"][k]


# --- T9 -------------------------------------------------------------------------

def test_y1b_board_key_order_and_stance_input_unchanged(tmp_path):
    result = ric.build_board(root=tmp_path)
    # C0 lane addition (2026-10-14): `board_generation` + `inflation_lenses`
    # land beside curve_accounting per RIC-W7 §2.11e — see DEVIATIONS entry
    # in /tmp/ric-c0/RETURN.md for the FROZEN-key-order update rationale.
    assert list(result) == _BASE_BOARD_KEYS + [
        "curve_accounting", "curve_accounting_export",
        "board_generation", "inflation_lenses",
    ]

    # Wrap compose_stance so we can read what compose_stance actually saw.
    original = ric.compose_stance
    seen = {}

    def spy(board):
        seen["input"] = board
        return original(board)

    compose_name = "compose_stance"
    if not hasattr(ric, compose_name):
        # The packet allows reporting the actual name under DEVIATIONS; record it.
        seen["actual_name"] = None
        for cand in dir(ric):
            obj = getattr(ric, cand)
            if callable(obj) and getattr(obj, "__name__", "") == "compose_stance":
                compose_name = cand
                break
    monkey = pytest.MonkeyPatch()
    monkey.setattr(ric, compose_name, spy)
    try:
        ric.build_board(root=tmp_path)
    finally:
        monkey.undo()
    assert "input" in seen, f"compose_stance spy did not run (name={compose_name!r})"
    spy_input = seen["input"]
    assert "curve_accounting" not in spy_input
    assert "curve_accounting_export" not in spy_input


# --- T10 ------------------------------------------------------------------------

def test_y1b_board_missing_and_malformed_contract(tmp_path):
    cases = [
        ("missing", None),
        ("explicit_null", None),  # placeholder, set below
        ("malformed", [1, 2]),
    ]
    # no latest.json
    out0 = ric.build_board(root=tmp_path)["curve_accounting"]
    assert out0["reason"] == "transmission_contract_missing_curve_accounting"
    assert out0["status"] == "unavailable"
    assert out0["display_only"] is True
    assert out0["authority"] is False
    assert out0["observations"] == {}

    # latest.json with curve_accounting: null
    (tmp_path / "transmission").mkdir(parents=True)
    (tmp_path / "transmission" / "latest.json").write_text(
        json.dumps({"curve_accounting": None}), encoding="utf-8"
    )
    out1 = ric.build_board(root=tmp_path)["curve_accounting"]
    assert out1["reason"] == "transmission_contract_missing_curve_accounting"
    assert out1["status"] == "unavailable"

    # latest.json with curve_accounting: [1, 2]
    (tmp_path / "transmission" / "latest.json").write_text(
        json.dumps({"curve_accounting": [1, 2]}), encoding="utf-8"
    )
    out2 = ric.build_board(root=tmp_path)["curve_accounting"]
    assert out2["reason"] == "transmission_contract_malformed_curve_accounting"
    assert out2["status"] == "unavailable"


# --- T11 ------------------------------------------------------------------------

def test_y1b_export_stays_closed_until_e1(tmp_path):
    # Empty dir.
    empty = ric.build_board(root=tmp_path)["curve_accounting_export"]
    assert empty == {
        "export_allowed": False,
        "reason": "awaiting_e1_ruling",
        "display_only": True,
    }
    # T8 setup.
    ca = json.loads(json.dumps(ym.build_curve_accounting(_golden_frame())))
    tx_dir = tmp_path / "transmission"
    tx_dir.mkdir(parents=True)
    (tx_dir / "latest.json").write_text(
        json.dumps({"asof": ca["asof"], "curve_accounting": ca}),
        encoding="utf-8",
    )
    full = ric.build_board(root=tmp_path)["curve_accounting_export"]
    assert full == {
        "export_allowed": False,
        "reason": "awaiting_e1_ruling",
        "display_only": True,
    }


# --- T12 ------------------------------------------------------------------------

def test_y1b_basis_is_carried_never_mixed():
    ca = _snapshot_isolated(_golden_frame())["curve_accounting"]
    seen_conventions = set()
    for k, obs in ca["observations"].items():
        cc = obs["curve_convention"]
        assert cc in {"par", "real_par", "zero"}, f"{k}: {cc}"
        seen_conventions.add(cc)
    assert "par" in seen_conventions
    assert "zero" in seen_conventions
    cmp_ = ca["comparisons"]["nominal_par_vs_kw_zero"]
    assert cmp_["status"] == "not_comparable"
    assert cmp_["reason"] == "basis_mismatch:curve_convention"
    assert ca["views_are_alternatives_never_summed"] is True


# --- T13 ------------------------------------------------------------------------

def test_y1b_pit_term_premium_note_names_kim_wright():
    note = DEFAULT_RELEASE_LAGS["term_premium_10y"]["note"]
    assert "Kim-Wright" in note
    assert "THREEFYTP10" in note
    assert "ACM" not in note
    assert DEFAULT_RELEASE_LAGS["term_premium_10y"]["lag_bd"] == 3
    assert DEFAULT_RELEASE_LAGS["term_premium_10y"]["cadence"] == "D"


# --- T14 ------------------------------------------------------------------------

def test_y1b_payload_is_strict_json_and_display_only():
    snap_ca = _snapshot_isolated(_golden_frame())["curve_accounting"]
    # strict JSON (no NaN) — both payloads pass
    json.dumps(snap_ca, allow_nan=False)

    # T8 board passthrough setup
    tmp = Path(tempfile.mkdtemp())
    ca = json.loads(json.dumps(ym.build_curve_accounting(_golden_frame())))
    (tmp / "transmission").mkdir(parents=True)
    (tmp / "transmission" / "latest.json").write_text(
        json.dumps({"asof": ca["asof"], "curve_accounting": ca}),
        encoding="utf-8",
    )
    board_ca = ric.build_board(root=tmp)["curve_accounting"]
    json.dumps(board_ca, allow_nan=False)

    banned_exact = {"rank", "score", "recommendation", "allowed_actions"}
    banned_prefix = "may_"

    def walk(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                assert k not in banned_exact, f"{path}.{k} banned"
                assert not k.startswith(banned_prefix), f"{path}.{k} starts with may_"
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(snap_ca)
    walk(board_ca)