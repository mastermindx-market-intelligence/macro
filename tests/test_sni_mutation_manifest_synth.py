"""Killing tests for MUT4B survivors in s1_manifest.py and s1_synth.py.

SNI-local DRAFT contract tests. This module CONSUMES owner-supplied
opaque identity strings (Stock Identity / Data OS) and never mints
issuer or security identifiers. HISTORICAL-DESCRIPTIVE only:
rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority and trade_authority stay false. Fixtures are
synthetic. This file does not feed a rank, gate, size, signal,
escalation, or trade path.
"""
from __future__ import annotations

import ast
import inspect
import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RESIDUAL = REPO_ROOT / "research" / "single_name_intelligence" / "residual"
if str(RESIDUAL) not in sys.path:
    sys.path.insert(0, str(RESIDUAL))

from lib import nyse_calendar  # noqa: E402
from s1_manifest import (  # noqa: E402
    _MAX_WALK_DAYS,
    canonical_line,
    first_anchor,
    first_session_strictly_after,
    is_session_fn,
    last_session_before,
    rolling_grid,
    session_n_forward,
    session_n_forward_on_non_session,
)
from s1_synth import (  # noqa: E402
    PATHS,
    REPO,
    _spec,
    sessions_hk,
    sessions_us,
    walk,
)
import s1_synth  # noqa: E402

_AUTHORITY = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)


def _is_us(d: date) -> bool:
    return nyse_calendar.is_session(d)


def _count_sessions_after(d: date, n: int) -> date:
    c, seen = d, 0
    while seen < n:
        c += timedelta(days=1)
        if _is_us(c):
            seen += 1
    return c


# ---------------------------------------------------------------------------
# s1_manifest.py survivors
# ---------------------------------------------------------------------------


def test_mut4b_s1_manifest_module_1():
    """s1_manifest.py:35, 400 -> 401 (_MAX_WALK_DAYS = 3 * 400 + 60)."""
    assert _MAX_WALK_DAYS == 3 * 400 + 60
    assert _MAX_WALK_DAYS == 1260


def test_mut4b_s1_manifest_canonical_line_1():
    """s1_manifest.py:199, ensure_ascii=False -> True."""
    row = {
        "protocol_id": "P01",
        "version": "v1",
        "horizon": 5,
        "episode_key": "synthetic-episode",
        "issuer_key": "synthetic-issuer",
        "counter": "α-counter",
        "security_id": "synthetic-sec",
        "unit": "rolling_anchor",
        "anchor_session_date": "2020-01-02",
        "coverage_date": None,
        "split": "TRAIN",
    }
    line = canonical_line(row)
    assert "α-counter" in line
    assert "\\u03b1" not in line
    parsed = json.loads(line)
    assert parsed["counter"] == "α-counter"


def test_mut4b_s1_manifest_first_session_strictly_after_1():
    """s1_manifest.py:93, return session_n_forward_on_non_session(...) -> None."""
    got = first_session_strictly_after(_is_us, date(2019, 1, 2))
    assert got == date(2019, 1, 3)
    assert got is not None


def test_mut4b_s1_manifest_first_session_strictly_after_2():
    """s1_manifest.py:93, n=1 -> n=2 (first session after d, not the second)."""
    assert first_session_strictly_after(_is_us, date(2019, 1, 2)) == date(2019, 1, 3)
    assert first_session_strictly_after(_is_us, date(2019, 1, 6)) == date(2019, 1, 7)


def test_mut4b_s1_manifest_is_session_fn_1():
    """s1_manifest.py:47, delete if market not in (MARKET_US, MARKET_HK): raise."""
    assert callable(is_session_fn("US"))
    with pytest.raises(ValueError, match="MARKET_US/MARKET_HK"):
        is_session_fn("CN")


def test_mut4b_s1_manifest_last_session_before_1():
    """s1_manifest.py:54, c = d - timedelta(days=1) -> d + timedelta(days=1)."""
    monday = date(2019, 1, 7)
    got = last_session_before(_is_us, monday)
    assert got < monday
    assert got == date(2019, 1, 4)


def test_mut4b_s1_manifest_rolling_grid_1():
    """s1_manifest.py:154, `s is None or s > last_bar` -> `and`."""
    dates = sessions_us(400)
    s0 = first_anchor(_is_us, dates, date(2012, 10, 31))
    assert s0 is not None
    got = rolling_grid(_is_us, dates, 5, date(2012, 10, 31), s0 - timedelta(days=1))
    assert got == []


def test_mut4b_s1_manifest_rolling_grid_2():
    """s1_manifest.py:155, return [] -> return None (empty grid)."""
    dates = sessions_us(10)
    got = rolling_grid(_is_us, dates, 5, date(2012, 10, 31), dates[-1])
    assert got == []
    assert got is not None


def test_mut4b_s1_manifest_session_n_forward_1():
    """s1_manifest.py:87, `if seen == n` -> `if seen != n`."""
    start = date(2019, 1, 2)
    got = session_n_forward(_is_us, start, 3)
    assert got == _count_sessions_after(start, 3)
    assert got == date(2019, 1, 7)


def test_mut4b_s1_manifest_session_n_forward_on_non_session_1():
    """s1_manifest.py:104, `if seen == n` -> `if seen != n`."""
    sunday = date(2019, 1, 6)
    assert session_n_forward_on_non_session(_is_us, sunday, 1) == date(2019, 1, 7)
    assert session_n_forward_on_non_session(_is_us, sunday, 2) == date(2019, 1, 8)


def test_mut4b_s1_manifest_session_n_forward_on_non_session_2():
    """s1_manifest.py:105, return c -> return None."""
    got = session_n_forward_on_non_session(_is_us, date(2019, 1, 6), 1)
    assert got == date(2019, 1, 7)
    assert got is not None


# ---------------------------------------------------------------------------
# s1_synth.py survivors
# ---------------------------------------------------------------------------


def test_mut4b_s1_synth_module_1():
    """s1_synth.py:15, Path.parents[3] -> Path.parents[4] (REPO root)."""
    here = Path(s1_synth.__file__).resolve()
    assert REPO == here.parents[3]
    assert (REPO / "research/single_name_intelligence/residual/s1_synth.py").resolve() == here


def test_mut4b_s1_synth_module_2(tmp_path: Path) -> None:
    """s1_synth.py:18, sys.path.insert(0, p) -> insert(1, p).

    Behavioural (X7-06, schk_09 pattern): import s1_synth in a subprocess
    whose sys.path is poisoned ahead of everything else by a decoy module
    named like a residual module s1_synth imports (s1_prereg). The loader's
    insert(0, residual/) must make the residual copy win the import; no
    .py source text is read.
    """
    poison = tmp_path
    (poison / "s1_prereg.py").write_text(
        'def __getattr__(name):\n    return "decoy:" + name\n', encoding="utf-8")
    s1_synth_py = RESIDUAL / "s1_synth.py"
    code = "\n".join([
        "import importlib.util, sys",
        "spec = importlib.util.spec_from_file_location('s1_synth', %r)" % str(s1_synth_py),
        "mod = importlib.util.module_from_spec(spec)",
        "sys.modules['s1_synth'] = mod",
        "err = ''",
        "try:",
        "    spec.loader.exec_module(mod)",
        "except BaseException as exc:",
        "    err = '%s: %s' % (type(exc).__name__, exc)",
        "m = sys.modules.get('s1_prereg')",
        "print('MISSING' if m is None else m.__file__)",
        "if err:",
        "    print('IMPORT_ERROR', err)",
    ])
    env = dict(os.environ)
    env["PYTHONPATH"] = str(poison)  # the decoy dir is first on the path
    proc = subprocess.run(
        [sys.executable, "-c", code], cwd=str(poison), env=env,
        capture_output=True, text=True, timeout=300,
    )
    assert proc.returncode == 0, proc.stderr
    assert "IMPORT_ERROR" not in proc.stdout, proc.stdout + proc.stderr
    out_lines = [ln for ln in proc.stdout.splitlines() if ln]
    assert out_lines, proc.stdout + proc.stderr
    won = Path(out_lines[-1]).resolve()
    assert won == (RESIDUAL / "s1_prereg.py").resolve(), (
        "the decoy won the import: %s" % won)


def test_mut4b_s1_synth__spec_1():
    """s1_synth.py:134, return build_spec() -> return None."""
    spec = _spec()
    assert isinstance(spec, dict)
    assert spec is not None
    flags = spec.get("authority_flags") or {}
    for key in _AUTHORITY:
        assert flags.get(key, False) is False


def test_mut4b_s1_synth_sessions_hk_1():
    """s1_synth.py:46, default start year 2019 -> 2020."""
    default = inspect.signature(sessions_hk).parameters["start"].default
    assert default == date(2019, 1, 2)
    assert sessions_hk(1)[0] == date(2019, 1, 2)


def test_mut4b_s1_synth_sessions_hk_2():
    """s1_synth.py:46, default start month 1 -> 2."""
    default = inspect.signature(sessions_hk).parameters["start"].default
    assert default == date(2019, 1, 2)
    assert default.month == 1


def test_mut4b_s1_synth_sessions_hk_3():
    """s1_synth.py:46, default start day 2 -> 3."""
    default = inspect.signature(sessions_hk).parameters["start"].default
    assert default == date(2019, 1, 2)
    assert default.day == 2


def test_mut4b_s1_synth_sessions_us_1():
    """s1_synth.py:37, default start month 1 -> 2."""
    default = inspect.signature(sessions_us).parameters["start"].default
    assert default == date(2019, 1, 2)
    assert sessions_us(1)[0] == date(2019, 1, 2)


def test_mut4b_s1_synth_sessions_us_2():
    """s1_synth.py:37, default start day 2 -> 3."""
    default = inspect.signature(sessions_us).parameters["start"].default
    assert default.day == 2
    assert sessions_us(1)[0] == date(2019, 1, 2)


def test_mut4b_s1_synth_synth_frames_1():
    """s1_synth.py:73, walk seed 7 -> 8 for 3033.HK."""
    src = Path(s1_synth.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    found = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Tuple) and len(node.elts) == 3:
            key_n, _dates_n, seed_n = node.elts
            if isinstance(key_n, ast.Constant) and key_n.value == "3033.HK":
                assert isinstance(seed_n, ast.Constant)
                found = seed_n.value
    assert found == 7
    us = sessions_us(12)
    hk = sessions_hk(12)
    # leak_start needs a 2024-04-01 bar; pin the pairing without that walk
    assert PATHS["3033.HK"].endswith("3033.HK.parquet")
    assert walk(hk, 7) != walk(hk, 8)
    assert walk(us, 7) != walk(us, 8)


def test_mut4b_s1_synth_walk_1():
    """s1_synth.py:55, default vol 0.01 -> 0.01001."""
    default = inspect.signature(walk).parameters["vol"].default
    assert default == 0.01
    dates = sessions_us(8)
    assert walk(dates, 3) == walk(dates, 3, vol=0.01)
    assert walk(dates, 3, vol=0.01) != walk(dates, 3, vol=0.01001)


def test_mut4b_s1_synth_walk_2():
    """s1_synth.py:59, start * prod(exp(r)) -> start / prod(exp(r))."""
    dates = sessions_us(8)
    got = walk(dates, 1, start=100.0, vol=0.01)
    rng = np.random.default_rng(1)
    r = rng.normal(0.0, 0.01, size=len(dates))
    expect = [float(100.0 * float(np.prod(np.exp(r[: i + 1])))) for i in range(len(dates))]
    assert got == expect
    divided = [float(100.0 / float(np.prod(np.exp(r[: i + 1])))) for i in range(len(dates))]
    assert got != divided
