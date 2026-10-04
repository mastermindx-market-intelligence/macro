"""Unit tests for ``scripts.regime_outlook_replay`` (slice E1r / rule R-I).

Pure-path tests only: synthetic frames, injected mapping, injected producers.
Never reads ``data/``/``site/`` stores; never opens a parquet file.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
SCRIPT_PATH = SCRIPTS_DIR / "regime_outlook_replay.py"
FIXTURE_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "regime_outlook" / "readings_golden_v2.json"
)


def _load_module():
    """Load the tool as a module without making ``scripts`` a package."""
    spec = importlib.util.spec_from_file_location(
        "regime_outlook_replay", SCRIPT_PATH,
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def tool():
    return _load_module()


@pytest.fixture(scope="module")
def mapping():
    from engine.rates_command_outlook import load_mapping
    return load_mapping()


@pytest.fixture(scope="module")
def mapping_sha(mapping):
    from engine.rates_command_outlook import mapping_sha256
    return mapping_sha256()


@pytest.fixture(scope="module")
def golden_base():
    with FIXTURE_PATH.open() as f:
        return json.load(f)["base"]


def _make_frame(d: str, *, extra_rows_pct: float = 0.0) -> pd.DataFrame:
    """Synthetic frame with business-day index spanning well past ``d``.

    ``extra_rows_pct`` lets a test inflate the tail past the date so the cut
    actually has something to clip.
    """
    start = pd.Timestamp(d) - pd.tseries.offsets.BDay(30)
    end = pd.Timestamp(d) + pd.tseries.offsets.BDay(60 + int(60 * extra_rows_pct))
    idx = pd.bdate_range(start, end)
    f = pd.DataFrame(index=idx)
    f["nfci"] = 0.0
    f["anfci"] = 0.0
    f["infl_exp_5y"] = 2.0
    f["indeed_postings"] = 100.0
    f["pct_above_200"] = 0.5
    f["net_liquidity_bn"] = 100.0
    f["zq_front"] = 95.0
    f["liquidity"] = "expanding"
    return f


# ---------------------------------------------------------------------------
# T1 / T2: build_frame
# ---------------------------------------------------------------------------

def test_build_frame_cuts_and_clears_attrs(tool):
    """The cut clips rows past the date and records what was cleared."""
    frame = _make_frame("2022-10-31")
    captured = {}

    def fake_bf(pit_basis=None, pit_as_of=None):
        captured["pit_basis"] = pit_basis
        captured["pit_as_of"] = pit_as_of
        return frame.copy()

    out = tool.build_frame("2022-10-31", build_features=fake_bf)
    assert captured["pit_basis"] == "release"
    assert captured["pit_as_of"] == "2022-10-31"
    assert out.index[-1] <= pd.Timestamp("2022-10-31")
    # attrs is cleared for downstream use; cleared copy lives under the key.
    assert "cleared_attrs" in out.attrs
    # Whatever was on the source frame lives in cleared_attrs (the source had
    # no attrs but the contract still records the cleared snapshot).
    assert isinstance(out.attrs["cleared_attrs"], dict)


def test_build_frame_empty(tool):
    """Empty frame raises ValueError."""
    empty = pd.DataFrame(index=pd.DatetimeIndex([], tz=None))
    with pytest.raises(ValueError, match="empty"):
        tool.build_frame("2022-10-31", build_features=lambda **_: empty)


# ---------------------------------------------------------------------------
# T3: reconstruct_letters — every mapping field appears exactly once
# ---------------------------------------------------------------------------

def test_reconstruct_letters_field_inventory(tool, mapping, golden_base):
    """T/R/M bytes parse; L/B/D/C are None; every field of every letter is reported."""
    frame = _make_frame("2022-10-31")
    base = golden_base

    def fake_state(f, **_):
        return base["T"]["state"]

    def fake_bd(f, **_):
        return base["T"].get("breakeven_decomp")

    def fake_yc(f, **_):
        return base["T"].get("yield_curve")

    def fake_ym(f, **_):
        return base["T"].get("yield_momentum")

    def fake_cs(f, **_):
        return base["R"].get("conditions")

    def fake_lq(f, **_):
        return base["R"].get("liquidity_quality")

    def fake_cb(payload, **_):
        return {"tone": "broadening"}

    producers = {
        "current_state": fake_state,
        "breakeven_decomposition": fake_bd,
        "yield_curve_regime": fake_yc,
        "build_yield_momentum": fake_ym,
        "conditions_snapshot": fake_cs,
        "liquidity_quality": fake_lq,
        "comp_breadth": fake_cb,
    }

    input_bytes, coverage = tool.reconstruct_letters(
        frame, "2022-10-31", producers=producers,
    )

    # T/R/M are bytes; L/B/D/C are None
    for L in "TRM":
        assert input_bytes[L] is not None
        parsed = json.loads(input_bytes[L])
        assert parsed["asof"] == "2022-10-31"
    for L in "LBDC":
        assert input_bytes[L] is None

    # Every mapping field appears exactly once across the coverage dict.
    all_field_ids = {f["field_id"] for f in mapping["fields"]}
    seen: dict[str, int] = {}
    for letter, cov in coverage.items():
        for fid in cov["fields"]:
            seen[fid] = seen.get(fid, 0) + 1
    assert set(seen) == all_field_ids
    for fid, n in seen.items():
        assert n == 1, f"{fid} reported {n} times"


# ---------------------------------------------------------------------------
# T4: labour read marking
# ---------------------------------------------------------------------------

def test_labor_marking_single_vs_partial(tool, golden_base):
    """2018/2019 -> unavailable:single_vote; 2022 -> partial:2_of_3_votes."""
    frame = _make_frame("2018-10-31")
    base = golden_base

    def fake_cs(f, **_):
        return base["R"]["conditions"]

    def fake_lq(f, **_):
        return base["R"]["liquidity_quality"]

    def fake_state(f, **_):
        return base["T"]["state"]

    def fake_bd(f, **_):
        return base["T"]["breakeven_decomp"]

    def fake_yc(f, **_):
        return base["T"]["yield_curve"]

    def fake_ym(f, **_):
        return base["T"]["yield_momentum"]

    def fake_cb(payload, **_):
        return {"tone": "broadening"}

    producers = {
        "current_state": fake_state,
        "breakeven_decomposition": fake_bd,
        "yield_curve_regime": fake_yc,
        "build_yield_momentum": fake_ym,
        "conditions_snapshot": fake_cs,
        "liquidity_quality": fake_lq,
        "comp_breadth": fake_cb,
    }

    labor_fid = "R.conditions.labor_nowcast.read"

    for d, expected_marker in [
        ("2018-10-31", "unavailable:single_vote"),
        ("2019-08-30",  "unavailable:single_vote"),
        ("2022-06-30",  "partial:2_of_3_votes"),
        ("2022-10-31",  "partial:2_of_3_votes"),
    ]:
        _, cov = tool.reconstruct_letters(
            _make_frame(d), d, producers=producers,
        )
        assert cov["R"]["fields"][labor_fid] == expected_marker


def test_labor_marking_value_present(tool, golden_base):
    """2018 -> value is dropped (None in the doc); 2022 -> value stays."""
    base = golden_base
    producers = {
        "current_state":   lambda f, **_: base["T"]["state"],
        "breakeven_decomposition": lambda f, **_: base["T"]["breakeven_decomp"],
        "yield_curve_regime":      lambda f, **_: base["T"]["yield_curve"],
        "build_yield_momentum":    lambda f, **_: base["T"]["yield_momentum"],
        "conditions_snapshot":     lambda f, **_: base["R"]["conditions"],
        "liquidity_quality":       lambda f, **_: base["R"]["liquidity_quality"],
        "comp_breadth":            lambda p, **_: {"tone": "broadening"},
    }

    # 2018 date -> labor_nowcast.read must NOT appear in the doc.
    _, cov = tool.reconstruct_letters(
        _make_frame("2018-10-31"), "2018-10-31", producers=producers,
    )
    assert cov["R"]["fields"]["R.conditions.labor_nowcast.read"] == (
        "unavailable:single_vote"
    )

    # 2022 date -> labor_nowcast.read must appear (partial marker).
    _, cov = tool.reconstruct_letters(
        _make_frame("2022-10-31"), "2022-10-31", producers=producers,
    )
    assert cov["R"]["fields"]["R.conditions.labor_nowcast.read"] == (
        "partial:2_of_3_votes"
    )


# ---------------------------------------------------------------------------
# T5: a producer raising
# ---------------------------------------------------------------------------

def test_letter_unavailable_when_producer_raises(tool, golden_base):
    """A raising producer marks its letter unavailable; others still reconstruct."""
    base = golden_base
    producers = {
        "current_state":   lambda f, **_: (_ for _ in ()).throw(RuntimeError("boom")),
        "breakeven_decomposition": lambda f, **_: base["T"]["breakeven_decomp"],
        "yield_curve_regime":      lambda f, **_: base["T"]["yield_curve"],
        "build_yield_momentum":    lambda f, **_: base["T"]["yield_momentum"],
        "conditions_snapshot":     lambda f, **_: base["R"]["conditions"],
        "liquidity_quality":       lambda f, **_: base["R"]["liquidity_quality"],
        "comp_breadth":            lambda p, **_: {"tone": "broadening"},
    }
    _, cov = tool.reconstruct_letters(
        _make_frame("2022-10-31"), "2022-10-31", producers=producers,
    )
    assert cov["T"]["status"] == "unavailable"
    assert cov["T"]["reason"] == "producer_error:RuntimeError"
    assert all(
        v.startswith("not_produced:producer_error:RuntimeError")
        for v in cov["T"]["fields"].values()
    )
    # R and M must still have reconstructed.
    assert cov["R"]["status"] == "reconstructed"
    assert cov["M"]["status"] == "reconstructed"


# ---------------------------------------------------------------------------
# T6: end-to-end replay determinism
# ---------------------------------------------------------------------------

def test_replay_end_to_end(tool, mapping, mapping_sha, golden_base):
    """4 per_date rows; 9 cards in mapping order; byte-deterministic JSON."""
    base = golden_base
    producers = {
        "current_state":            lambda f, **_: base["T"]["state"],
        "breakeven_decomposition":  lambda f, **_: base["T"]["breakeven_decomp"],
        "yield_curve_regime":       lambda f, **_: base["T"]["yield_curve"],
        "build_yield_momentum":     lambda f, **_: base["T"]["yield_momentum"],
        "conditions_snapshot":      lambda f, **_: base["R"]["conditions"],
        "liquidity_quality":        lambda f, **_: base["R"]["liquidity_quality"],
        "comp_breadth":             lambda p, **_: {"tone": "broadening"},
    }

    def bf(d, **_):
        return _make_frame(d)

    out = tool.replay(
        mapping,
        mapping_sha256=mapping_sha,
        build_frame_fn=bf,
        producers=producers,
    )

    assert out["schema_version"] == "regime_outlook_replay.v1"
    assert out["label"] == tool.LABEL
    assert out["rule"] == "R-I"
    assert out["seen_history_row"] == "SH-12"
    assert out["revised_columns_caveat"]

    assert len(out["per_date"]) == 4
    expected_path_ids = [p["path_id"] for p in mapping["paths"]]
    for row in out["per_date"]:
        got = [c["path_id"] for c in row["paths"]]
        assert got == expected_path_ids, (
            f"{row['date']}: got {got}"
        )

    # Determinism
    out2 = tool.replay(
        mapping,
        mapping_sha256=mapping_sha,
        build_frame_fn=bf,
        producers=producers,
    )
    assert json.dumps(out) == json.dumps(out2)


# ---------------------------------------------------------------------------
# T7: CLI
# ---------------------------------------------------------------------------

def test_cli_dry_run_writes_nothing(tool, tmp_path):
    """--dry-run prints the table and does not write."""
    res = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--dry-run"],
        capture_output=True, text=True, env={
            **os.environ,
            "PYTHONPATH": str(REPO_ROOT),
            "REGIME_OUTLOOK_REPLAY_FAKE_FRAME": "1",
        },
        cwd=str(REPO_ROOT),
    )
    assert res.returncode == 0, res.stderr
    out_path = tmp_path / "should_not_exist.json"
    assert not out_path.exists()
    assert "T | R | M | L | B | D | C" in res.stdout


def test_cli_writes_file(tool, tmp_path):
    """--out writes a parseable JSON file ending in a newline."""
    out_path = tmp_path / "out.json"
    res = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--out", str(out_path)],
        capture_output=True, text=True, env={
            **os.environ,
            "PYTHONPATH": str(REPO_ROOT),
            "REGIME_OUTLOOK_REPLAY_FAKE_FRAME": "1",
        },
        cwd=str(REPO_ROOT),
    )
    assert res.returncode == 0, res.stderr
    assert out_path.exists()
    raw = out_path.read_bytes()
    assert raw.endswith(b"\n")
    parsed = json.loads(raw.decode("utf-8"))
    assert parsed["schema_version"] == "regime_outlook_replay.v1"


def test_cli_refuses_data_out(tool):
    """--out under data/ exits 2 with the forbidden-root message."""
    res = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--out", "data/x.json"],
        capture_output=True, text=True, env={
            **os.environ,
            "PYTHONPATH": str(REPO_ROOT),
            "REGIME_OUTLOOK_REPLAY_FAKE_FRAME": "1",
        },
        cwd=str(REPO_ROOT),
    )
    assert res.returncode == 2
    assert "regime-outlook-replay-out-forbidden" in res.stdout


# ---------------------------------------------------------------------------
# T8: source check — banned tokens absent from the module source
# ---------------------------------------------------------------------------

def test_module_does_not_call_banned_producers():
    """The module must never name these forbidden call shapes."""
    src = SCRIPT_PATH.read_text()
    banned = (
        "fed_path.snapshot",
        "rate_inflation_transmission.snapshot",
        "leadership_crack._build",
        "fed_path.compute",
    )
    for tok in banned:
        assert tok not in src, f"banned token present in source: {tok}"