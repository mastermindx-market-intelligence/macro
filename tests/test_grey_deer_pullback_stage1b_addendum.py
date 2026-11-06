"""Synthetic tests for the stage-1b results addendum renderer.

The fixture is a hand-built results object. It contains no prices.
"""

from __future__ import annotations

import hashlib
import json
import re

import pytest

from scripts.research.grey_deer_pullback_stage1b import IDENTITY_PINS, PANEL_TICKERS
from scripts.research.grey_deer_pullback_stage1b_addendum import main, render_addendum

FORBIDDEN = (
    "validated",
    "signal",
    "predicts",
    "forecast",
    "edge",
    "odds",
    "severity",
    "qualified",
    "promotion",
)

_DELTA_V_NAME = "delta_v@alpha=b (V(M3) - max(V(B1-20,B1-63,B2-21,B2-63)))"
_HEADLINE_POINT = 1.5
_HEADLINE_LB = -0.4
_DELTA_POINT = -0.25
_DELTA_LB = -0.8
_DECOY_POINT = 7.75
_HIDDEN_EVENT_DATE = 424242


def _episode(windows: list, dates: list) -> dict:
    return {
        "origins": 8,
        "ticker_events": 2,
        "events": 2,
        "clusters": 1,
        "episodes": 2,
        "event_months": 1,
        "event_dates": dates,
        "event_month_list": ["2024-01"],
        "episode_windows": windows,
        "power_floor": {"met": True, "min_episodes": 10, "min_months": 10},
        "per_ticker_episodes": {"QQQ": 1},
    }


def _boot_cell() -> dict:
    headline = {"lb": -0.2, "interval_90": [-0.3, 0.1]}
    variant = {"n_draws": 4, "L": 21, "N_dates": 3, "headline": headline, "seed": [1, 5]}
    return {"primary": variant, "sensitivity_L_h": dict(variant)}


def synthetic() -> dict:
    """One P-all binary claim. The delta-V condition is last, not at index 1."""
    binary = _episode([[10, 20], [30, 40]], [1, _HIDDEN_EVENT_DATE, 3])
    quantile = _episode([[10, 20]], [4, 5])
    hashes = {
        ticker: ("0" * 64 if ticker == "DIA" else IDENTITY_PINS[ticker]["subframe_sha256"])
        for ticker in PANEL_TICKERS
    }
    claim = {
        "id": "synthetic-h5",
        "h": 5,
        "pop": "P-all",
        "claim": "binary",
        "statistic": "delta_v@alpha=b_h",
        "point": _HEADLINE_POINT,
        "lb": _HEADLINE_LB,
        "threshold": 0.0,
        "flags": ["FRAGILE"],
        "verdict": "rejected candidate",
        "conditions": [
            {
                "condition": 0,
                "statistic": "not_delta_v@alpha=b",
                "point": _DECOY_POINT,
                "lb": _DECOY_POINT,
                "threshold": 0.0,
                "pass": False,
            },
            {
                "condition": 1,
                "statistic": "v_m3@alpha=b",
                "point": _HEADLINE_POINT,
                "lb": _HEADLINE_LB,
                "threshold": 0.0,
                "pass": False,
            },
            {
                "condition": 9,
                "statistic": _DELTA_V_NAME,
                "point": _DELTA_POINT,
                "lb": _DELTA_LB,
                "threshold": 0.0,
                "pass": False,
            },
            {
                "condition": 5,
                "statistic": "abstention (rate <= 5% of evaluation origins; event-vs-non-event gap <= 5pp)",
                "point": {
                    "rate": 0.0,
                    "gap_pp": 0.0,
                    "issued": 8,
                    "abstained": 0,
                    "by_type": {},
                },
                "lb": None,
                "threshold": {"rate": 0.05, "gap_pp": 5.0},
                "pass": True,
            },
        ],
        "honest_n": binary,
        "loeo": {
            "fragile": True,
            "min": {"bss": 0.0, "delta_v": -0.01},
            "n_episodes": 2,
        },
    }
    return {
        "schema": "grey_deer_pullback_stage1b/v1",
        "status": "OK",
        "claims": [claim],
        "negative_control": {
            "h5": {
                "expectation": "at or below 0; neither a claim nor a gate",
                "shift": "rolled",
                "m3-ALL-shifted": {"bss_vs_b0": 0.1, "v_at_b_h": -0.2, "n_scored": 3},
                "q3-ALL-shifted": {"n_scored": 3, "pinball_skill": -0.01},
            }
        },
        "bootstrap_cells": {"h5": {"binary": _boot_cell(), "quantile": _boot_cell()}},
        "bootstrap": {"axis": "date", "n_draws": 4, "seed_root": 1},
        "fold_block_table": [
            {
                "h": 5,
                "fold": 8,
                "start_index": 1,
                "end_index": 4,
                "start_date": "2026-04-13",
                "end_date": "2026-09-30",
                "after_excluded_session": False,
            }
        ],
        "episodes": {"h5": {"binary": binary, "quantile": quantile}},
        "comparison": {
            "h5": {
                "binary": {
                    "N_common": 8,
                    "sensitivity": {
                        "config": "M3-ALL-C0.1",
                        "n": 8,
                        "note": "sensitivity row only, never a gate",
                    },
                },
                "quantile": {"N_common": 8},
            }
        },
        "panel": {
            "tickers": list(PANEL_TICKERS),
            "n_dates": 4,
            "first_date": "2021-07-06",
            "last_date": "2026-10-07",
            "spy_excluded": True,
        },
        "subframe_sha256": hashes,
        "inc": {
            "id": "INC",
            "status": "NOT_APPLICABLE",
            "gate": False,
            "evidence_class": "NOT_APPLICABLE",
            "reason": "synthetic incumbent row",
        },
        "blocked": [],
        "commit_sha": "abc",
        "run_commit": "abc",
        "script_blob_sha": "def",
        "test_blob_sha": "def",
        "adjust_module_blob_sha": "def",
        "manifest_path": "research/grey_deer/manifest.md",
        "manifest_version": "1.1.0",
        "manifest_blob_sha": "aaa",
        "prereg_path": "research/grey_deer/prereg.md",
        "prereg_blob_sha": "bbb",
        "dividend_basis": "unadjusted",
        "dividend_disclosure": "Dividends are unadjusted.",
        "trial_family": "grey_deer_pullback_v11",
        "trial_budget": 66,
        "trial_counting": {"per_horizon": 22, "total": 66},
        "seed_root": 1,
        "n_draws": 4,
    }


def _render(results: dict | None = None, sha: str = "abc", ref: str = "ref") -> str:
    return render_addendum(synthetic() if results is None else results, results_sha256=sha, results_ref=ref)


def _f1_row(text: str) -> list[str]:
    rows = [
        line
        for line in text.splitlines()
        if line.startswith("| synthetic-h5 |") and "V(M3)@alpha=b_h" in line
    ]
    assert len(rows) == 1
    return [cell.strip() for cell in rows[0].strip().strip("|").split("|")]


def test_delta_v_taken_by_statistic_name_not_position():
    text = _render()
    cells = _f1_row(text)
    assert cells[2] == "V(M3)@alpha=b_h"
    assert cells[3] == repr(_HEADLINE_POINT)
    assert cells[4] == repr(_HEADLINE_LB)
    assert cells[5] == _DELTA_V_NAME
    assert cells[6] == repr(_DELTA_POINT)
    assert cells[7] == repr(_DELTA_LB)
    assert str(_DECOY_POINT) not in text
    assert str(_HIDDEN_EVENT_DATE) not in text

    f3 = text.split("## F3.", 1)[1].split("## F4.", 1)[0]
    data = [line for line in f3.splitlines() if line.startswith("| ") and not line.startswith("| ticker |")]
    assert len(data) == len(PANEL_TICKERS)
    dia = next(line for line in data if line.startswith("| DIA |"))
    dia_cells = [cell.strip() for cell in dia.strip().strip("|").split("|")]
    assert dia_cells[1] == "0" * 64
    assert dia_cells[2] == str(IDENTITY_PINS["DIA"]["rows"])
    assert dia_cells[3] == IDENTITY_PINS["DIA"]["first_date"]
    assert dia_cells[4] == IDENTITY_PINS["DIA"]["last_date"]
    assert dia_cells[5] == "false"
    qqq = next(line for line in data if line.startswith("| QQQ |"))
    qqq_cells = [cell.strip() for cell in qqq.strip().strip("|").split("|")]
    assert qqq_cells[1] == IDENTITY_PINS["QQQ"]["subframe_sha256"]
    assert qqq_cells[5] == "true"


def test_render_is_byte_identical():
    results = synthetic()
    first = render_addendum(results, results_sha256="abc", results_ref="ref")
    second = render_addendum(results, results_sha256="abc", results_ref="ref")
    assert first == second
    assert first.encode("utf-8") == second.encode("utf-8")


def test_schema_mismatch_and_missing_key_raise():
    bad_schema = synthetic()
    bad_schema["schema"] = "grey_deer_pullback_stage1/v0"
    with pytest.raises(ValueError, match="schema"):
        render_addendum(bad_schema, results_sha256="abc", results_ref="ref")

    missing = synthetic()
    del missing["fold_block_table"]
    with pytest.raises(ValueError, match="fold_block_table"):
        render_addendum(missing, results_sha256="abc", results_ref="ref")


@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
def test_main_refuses_nonfinite(tmp_path, literal: str):
    src = tmp_path / "bad.json"
    src.write_text(
        '{"schema": "grey_deer_pullback_stage1b/v1", "x": ' + literal + "}\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.md"
    with pytest.raises(ValueError):
        main(["--results", str(src), "--out", str(out), "--ref", ""])
    assert not out.exists()


def test_forbidden_words_absent():
    text = _render()
    for word in FORBIDDEN:
        match = re.search(rf"\b{word}\b", text, flags=re.IGNORECASE)
        assert match is None, word
    cleaned = text
    for token in (
        "delta_v@alpha=b_h",
        "V(M3)@alpha=b_h",
        "v_m3@alpha=0.5b",
        "v_m3@alpha=2b",
        "v_m3@alpha=b",
        "delta_v@alpha=b",
        "not_delta_v@alpha=b",
    ):
        cleaned = cleaned.replace(token, "")
    assert re.findall(r"alpha", cleaned, flags=re.IGNORECASE) == []


def test_provenance_block_has_sha256_and_no_rerun_sentence():
    sha = "0123456789abcdef"
    text = _render(sha=sha, ref="ref-1")
    head = text.split("## F1", 1)[0]
    assert sha in head
    assert (
        "Derived only from the stored results JSON. No claim was re-run and no verdict changed."
        in head
    )
    assert head.startswith("# Pullback stage-1b results addendum\n")


def test_main_writes_sha_of_raw_bytes(tmp_path, capsys):
    raw = json.dumps(synthetic(), sort_keys=True).encode("utf-8")
    src = tmp_path / "in.json"
    src.write_bytes(raw)
    out = tmp_path / "nested" / "out.md"
    rc = main(["--results", str(src), "--out", str(out), "--ref", "abc"])
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert hashlib.sha256(raw).hexdigest() in text
    assert capsys.readouterr().out.strip() == str(out)
    assert text.endswith("\n")
    assert "\r" not in text
