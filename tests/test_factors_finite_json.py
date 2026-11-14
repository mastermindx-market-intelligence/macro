"""The ordinary factors producer emits strict finite JSON (no post-hoc repair).

REAL   ``site/factordata/factors.json`` is the committed nightly output. It may
       already contain only finite JSON values. The test feeds the parsed table
       through the producer's own ``write_factors_json`` and requires: zero
       non-finite tokens on a STRICT parse, every finite value identical, every
       previously non-finite position null. The fixed fixture below supplies
       non-finite regression coverage independently of the nightly output.
FIXTURE a tiny synthetic table with numpy/pandas missing values and a finite
       ``0.0`` (must stay 0.0, never become null) - labelled as such.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from lib.numeric import finite_json_value
from scripts import build_site

REPO = Path(__file__).resolve().parents[1]


def _strict(raw: str):
    def refuse(token):
        raise AssertionError("non-finite literal in output: " + token)
    return json.loads(raw, parse_constant=refuse)


def _walk(before, after, path="$"):
    if isinstance(before, dict):
        assert isinstance(after, dict) and set(before) == set(after), path
        for key in before:
            _walk(before[key], after[key], path + "." + key)
    elif isinstance(before, list):
        assert isinstance(after, list) and len(before) == len(after), path
        for i, (x, y) in enumerate(zip(before, after)):
            _walk(x, y, f"{path}[{i}]")
    elif isinstance(before, float) and not math.isfinite(before):
        assert after is None, path
    else:
        assert before == after, path


def test_real_factors_table_round_trips_to_strict_finite_json(tmp_path):
    real = json.loads((REPO / "site/factordata/factors.json").read_text(),
                      parse_constant=lambda token: float("nan") if token == "NaN" else float(token))
    out = tmp_path / "factors.json"
    build_site.write_factors_json(real, out)
    produced = _strict(out.read_text())  # strict parse: any NaN/Infinity raises
    _walk(real, produced)
    assert out.read_text() == json.dumps(finite_json_value(real), separators=(",", ":"),
                                         default=str, allow_nan=False)


def test_fixture_missing_values_become_null_and_zero_stays_zero(tmp_path):
    """FIXTURE."""
    table = {"table": [{"ticker": "A", "value": np.float64("nan"), "quality": 0.0,
                        "profitability": float("inf"), "sue": pd.NA, "n": np.int64(3)}],
             "as_of": "2026-11-06"}
    out = tmp_path / "f.json"
    build_site.write_factors_json(table, out)
    row = _strict(out.read_text())["table"][0]
    assert row == {"ticker": "A", "value": None, "quality": 0.0,
                   "profitability": None, "sue": None, "n": 3}


def test_factors_page_uses_the_strict_writer():
    source = (REPO / "scripts/build_site.py").read_text()
    assert 'write_factors_json(fac, fdir / "factors.json")' in source
    assert '(fdir / "factors.json").write_text(json.dumps(fac' not in source
