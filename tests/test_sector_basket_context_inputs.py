"""Explicit basket/context inputs preserve full owner output and isolate effects."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json

import numpy as np
import pandas as pd
import pytest

from engine import baskets as bk
from engine import theme_context as tc

GOLDEN = Path(__file__).parent / "fixtures" / "sector_basket_context_parity.json"
BASKET_CASES = (
    "normal", "missing_coverage", "migration", "newer_extras",
    "missing_proxy", "removed_member", "missing_spy", "missing_membership",
)
CONTEXT_CASES = (
    "normal", "empty_history", "same_day", "absent_alignment",
    "empty_alignment", "malformed_alignment", "rotating", "missing_ranks",
)


def basket_inputs(case="normal"):
    idx = pd.bdate_range(end="2026-11-04", periods=320)
    rng = np.random.default_rng(73)
    panel = pd.DataFrame({
        ticker: 100 * np.cumprod(1 + rng.normal(0.0007 + n * 0.00005, 0.009, len(idx)))
        for n, ticker in enumerate("ABCDEF")
    }, index=idx)
    extras = pd.DataFrame({
        ticker: 60 * np.cumprod(1 + rng.normal(0.0009, 0.012, len(idx)))
        for ticker in "GHI"
    }, index=idx)
    spy = pd.DataFrame({"close": 400 * np.cumprod(
        1 + rng.normal(0.0005, 0.007, len(idx)))}, index=idx)
    proxies = {ticker: pd.DataFrame({"close": 50 * np.cumprod(
        1 + rng.normal(0.0006, 0.008, len(idx)))}, index=idx)
        for ticker in ("XLP", "XLU", "XLK")}
    start = idx[0].date().isoformat()
    members = {}
    for identity, symbols, proxy in (
        ("alpha", "ABC", ["XLP", "XLU"]),
        ("beta", "DEF", "XLK"), ("gamma", "GHI", None),
    ):
        members[identity] = {
            "name": identity + " (Equal-Weight)", "category": identity,
            "created": start, "etf_proxy": proxy, "thesis": "Synthetic parity fixture",
            "members": [{"ticker": symbol, "added": start, "rationale": symbol}
                        for symbol in symbols],
        }
    membership = {"baskets": members}
    if case == "missing_coverage":
        panel.loc[idx[-1], ["A", "B"]] = np.nan
    elif case == "migration":
        panel["G"] = extras["G"] * 2
        panel.loc[idx[-80:], "G"] = np.nan
    elif case == "newer_extras":
        extras.loc[pd.Timestamp("2026-11-05")] = extras.iloc[-1] * 1.02
    elif case == "missing_proxy":
        proxies = {}
    elif case == "removed_member":
        members["alpha"]["members"][-1]["removed"] = idx[-10].date().isoformat()
    elif case == "missing_spy":
        spy = None
    elif case == "missing_membership":
        membership = None
    return bk.BasketInputs(
        membership, panel, spy, extras,
        {s: (s + " company", "fixture") for s in "ABCDEFGHI"}, proxies,
    )


def context_inputs(case="normal"):
    ranks, themes = [], []
    for n, identity in enumerate(("alpha", "beta", "gamma", "delta"), start=1):
        ranks.append({
            "id": identity, "name": identity + " (Equal-Weight)", "name_zh": identity,
            "category": identity, "rank": n, "score": 5.0 - n * .4,
            "eligible": True, "r10": .07 - n * .004, "val_state": "confirming",
            "gate": {"above_200dma": True}, "durability": {"breadth": .8},
        })
        themes.append({"id": identity, "label": "dominant", "reco": "hold",
                       "score": 90 - n * 3})
    allocation = {"as_of": "2026-11-04", "region": "us", "ranks": ranks,
                  "rotation": {}, "allocation": {"weights": [], "cash": 0.0}}
    intel = {"as_of": "2026-11-04", "themes": themes}
    history = [{
        "asof": stamp, "leadership_state": "healthy",
        "trailing_leader_id": "alpha", "leader_health": "confirmed",
        "labels": {r["id"]: "dominant" for r in ranks},
        "scores": {r["id"]: 70 + n for r in ranks},
    } for n, stamp in enumerate(
        ("2026-10-27", "2026-10-28", "2026-10-29", "2026-10-30", "2026-11-02"))]
    events = {"active": [{"to_leg": {"key": "beta"}}]}
    if case == "empty_history":
        history = []
    elif case == "same_day":
        history[-1]["asof"] = "2026-11-04"
    elif case == "absent_alignment":
        events = None
    elif case == "empty_alignment":
        events = {}
    elif case == "malformed_alignment":
        events = {"active": [{"to_leg": ["bad"]}]}
    elif case == "rotating":
        ranks[0]["durability"]["breadth"] = .1
        ranks[0]["r10"] = -.12
        themes[0].update(label="deteriorating", reco="avoid", score=15)
    elif case == "missing_ranks":
        allocation["ranks"] = []
    return tc.ThemeContextInputs(allocation, intel, "us", history, events)


def normalized(value):
    return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))


@pytest.mark.parametrize("case", BASKET_CASES)
def test_full_basket_output_matches_actual_pinned_owner(case):
    expected = json.loads(GOLDEN.read_text())["baskets"][case]
    assert normalized(bk.compute_baskets_from_inputs(basket_inputs(case))) == expected


@pytest.mark.parametrize("case", CONTEXT_CASES)
def test_full_context_output_matches_actual_pinned_owner(case):
    expected = json.loads(GOLDEN.read_text())["context"][case]
    assert normalized(tc.compute_theme_context_from_inputs(context_inputs(case))) == expected


def forbidden(*args, **kwargs):
    raise AssertionError("Undeclared IO, lane, writer or renderer reached")


def test_basket_core_has_no_repo_reads_and_does_not_emit_diagnostics(monkeypatch, capsys):
    inputs = basket_inputs("missing_coverage")
    expected = bk.compute_baskets_from_inputs(inputs)
    for name in ("_membership", "_closes", "_basket_extras", "_names_sectors", "_proxy_returns"):
        monkeypatch.setattr(bk, name, forbidden)
    monkeypatch.setattr(bk.store, "read", forbidden)
    monkeypatch.setattr(bk.config, "load", forbidden)
    monkeypatch.setattr(bk.config, "data_dir", forbidden)
    monkeypatch.setattr(pd, "read_parquet", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    assert normalized(bk.compute_baskets_from_inputs(inputs)) == normalized(expected)
    assert expected and expected["observation_refusals"]
    assert capsys.readouterr().out == ""


def test_context_core_never_loads_seeds_or_advances_even_on_nightly(monkeypatch):
    inputs = context_inputs()
    expected = tc.compute_theme_context_from_inputs(inputs)
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    monkeypatch.setenv("CN_LANE", "asia")
    for name in ("_repo_root", "_load_history", "_seed_from_archive", "_write_history",
                 "_advance_enabled", "_alignment", "_load_alignment_events", "write_context"):
        monkeypatch.setattr(tc, name, forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr(pd, "read_parquet", forbidden)
    assert normalized(tc.compute_theme_context_from_inputs(inputs)) == normalized(expected)
    assert expected


def test_inputs_and_outputs_do_not_alias():
    inputs = basket_inputs()
    membership = deepcopy(inputs.membership)
    closes, extras = inputs.closes.copy(deep=True), inputs.extras.copy(deep=True)
    result = bk.compute_baskets_from_inputs(inputs)
    result["baskets"][0]["changelog"][0]["note"] = "mutated output"
    assert inputs.membership == membership
    pd.testing.assert_frame_equal(inputs.closes, closes)
    pd.testing.assert_frame_equal(inputs.extras, extras)
    again = bk.compute_baskets_from_inputs(inputs)
    assert normalized(again) == json.loads(GOLDEN.read_text())["baskets"]["normal"]

    context = context_inputs()
    before = deepcopy(context)
    out = tc.compute_theme_context_from_inputs(context)
    out["leadership"]["trailing_leader"]["name"] = "mutated"
    assert context == before
    assert normalized(tc.compute_theme_context_from_inputs(context)) == (
        json.loads(GOLDEN.read_text())["context"]["normal"]
    )


@pytest.mark.parametrize("succeed", [True, False])
def test_legacy_seed_is_adopted_only_after_successful_write(monkeypatch, tmp_path, succeed):
    inputs = context_inputs("empty_history")
    seed = context_inputs().history
    calls = []
    monkeypatch.setattr(tc, "_load_history", lambda *a: [])
    monkeypatch.setattr(tc, "_advance_enabled", lambda *a: True)
    monkeypatch.setattr(tc, "_seed_from_archive", lambda *a: seed)
    monkeypatch.setattr(tc, "_load_alignment_events", lambda *a: inputs.rotation_events)
    def write(rows, *args):
        calls.append(deepcopy(rows))
        if not succeed and len(calls) == 1:
            raise OSError("fixture seed write refused")
    monkeypatch.setattr(tc, "_write_history", write)
    result = tc.compute_theme_context(inputs.allocation, inputs.theme_intel, root=tmp_path)
    expected = tc.compute_theme_context_from_inputs(tc.ThemeContextInputs(
        inputs.allocation, inputs.theme_intel, "us", seed if succeed else [],
        inputs.rotation_events,
    ))
    assert normalized(result) == normalized(expected)
    assert len(calls) == 2
    assert calls[-1][-1]["asof"] == "2026-11-04"
    assert len(calls[-1]) == (len(seed) + 1 if succeed else 1)


def test_legacy_missing_membership_preserves_early_short_circuit(monkeypatch):
    monkeypatch.setattr(bk, "_membership", lambda: None)
    for name in ("_closes", "_basket_extras", "_names_sectors"):
        monkeypatch.setattr(bk, name, forbidden)
    monkeypatch.setattr(bk.store, "read", forbidden)
    assert bk.compute_baskets() is None


def test_source_calendar_and_declared_context_date_survive():
    result = bk.compute_baskets_from_inputs(basket_inputs("newer_extras"))
    assert result["as_of"] == result["chart"]["dates"][-1] == "2026-11-04"
    context = tc.compute_theme_context_from_inputs(context_inputs("same_day"))
    assert context["as_of"] == context["prev_asof"] == "2026-11-04"
