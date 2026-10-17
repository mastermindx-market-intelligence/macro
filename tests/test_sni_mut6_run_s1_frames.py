"""M6I killing tests for run_s1.py second-half helpers.

SNI-local DRAFT contract tests. They consume caller-supplied opaque identity
strings and synthetic fixtures; they do not mint issuer or security identifiers
and they do not feed a rank, gate, size, signal, escalation, or trade path.
Authority flags stay false. Each test_m6i_* docstring names one non-equivalent
mutant that survived the S1 importer suite (file:line, original -> mutated).
"""
from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "research/single_name_intelligence/residual"))
sys.path.insert(0, str(REPO))

import run_s1  # noqa: E402
from s1_synth import sessions_us, walk  # noqa: E402


# ---------------------------------------------------------------------------
# run_s1 survivors (M6I second pass)
# ---------------------------------------------------------------------------


def test_m6i_run_s1__byte_compare_1(tmp_path, capsys):
    """run_s1.py:1115, const_bool `return False` -> `return True` in _byte_compare."""
    a = tmp_path / "committed"
    b = tmp_path / "produced"
    for root in (a, b):
        (root / "results").mkdir(parents=True)
        (root / "observations").mkdir()
        # REPORT.md differs between committed and produced -> _tree_equal returns False.
        (root / "REPORT.md").write_text("ok\n", encoding="utf-8")
        (root / "LANE_MANIFEST.json").write_text("{}\n", encoding="utf-8")
        (root / "trial_ledger.jsonl").write_text("", encoding="utf-8")
    (b / "REPORT.md").write_text("DIFFER\n", encoding="utf-8")
    # Original: REPORT.md differs -> _tree_equal returns False -> _byte_compare returns False.
    # Mutated: return False -> return True so _byte_compare returns True even on a tree diff.
    assert run_s1._byte_compare(a, b) is False
    captured = capsys.readouterr()
    assert "differs under REPORT.md" in captured.err


def test_m6i_run_s1__comparison_block_quarantine_count_1():
    """run_s1.py:742, cmp_flip `r["split"] == "QUARANTINE"` -> `!=` in exclusions."""
    rows = [
        {"r__oc_key": "q1", "split": "QUARANTINE", "abstention": "OK", "r__oc": 0.1,
         "common__oc": 0.05, "anchor_session_date": "2024-01-02"},
        {"r__oc_key": "q2", "split": "QUARANTINE", "abstention": "OK", "r__oc": 0.1,
         "common__oc": 0.05, "anchor_session_date": "2024-01-04"},
        {"r__oc_key": "t1", "split": "TRAIN", "abstention": "OK", "r__oc": 0.2,
         "common__oc": 0.1, "anchor_session_date": "2024-01-03"},
        {"r__oc_key": "t2", "split": "TRAIN", "abstention": "OK", "r__oc": 0.2,
         "common__oc": 0.1, "anchor_session_date": "2024-02-03"},
        {"r__oc_key": "t3", "split": "TRAIN", "abstention": "OK", "r__oc": 0.2,
         "common__oc": 0.1, "anchor_session_date": "2024-03-03"},
    ]
    prev = {r["r__oc_key"]: r for r in rows}
    nxt = {r["r__oc_key"]: r for r in rows}
    out = run_s1._comparison_block(
        prev, nxt, "M0", "M1", "TRAIN",
        label="", receipt_base={}, membership={"TRAIN": ""},
        trial_accounting={}, rows_total=len(rows),
    )
    # Original counts rows with split == "QUARANTINE": q1 + q2 = 2.
    # Mutated counts rows with split != "QUARANTINE": t1 + t2 + t3 = 3.
    assert out["exclusions"]["quarantine"] == 2, (
        f"expected 2 QUARANTINE rows, got {out['exclusions']['quarantine']}"
    )


def test_m6i_run_s1_build_challenger_context_non_estimable_1(monkeypatch):
    """run_s1.py:569, return_none `return ctx` -> `return None` on non-estimable path."""

    class _Store:
        input_ref = "fake-ref"

        def frame(self, path, columns):
            return [date(2020, 1, 2)], {c: [1.0] for c in columns}

        def read_columns(self, path, columns):
            return {c: [1.0] for c in columns}

    universe = {
        "admitted": [{"path": "p1"}, {"path": "p2"}],
        "files_examined": 2,
        "admitted_count": 2,
    }

    def _fake_estimability(*_a, **_k):
        return {"estimable": False, "admitted_names": 2,
                "characteristics": 0, "train_months_with_valid_cross_section": 0}

    monkeypatch.setattr(run_s1, "estimability", _fake_estimability)

    out = run_s1.build_challenger_context(_Store(), universe)
    # Original returns ctx (a dict). Mutated returns None on the non-estimable
    # early-return at line 569.
    assert isinstance(out, dict)
    assert out.get("gamma") is None
    assert out.get("estimability", {}).get("estimable") is False


def test_m6i_run_s1_challenger_apply_beta_value_1(monkeypatch):
    """run_s1.py:603, const_int g[0] -> g[1] in the linear beta form."""
    dates = sessions_us(300)
    aligned = walk(dates, seed=1)
    subj_close = {d: aligned[i] for i, d in enumerate(dates)}
    s = dates[280]
    fill = dates[270]
    coverage = dates[275]
    # Use 60 panel paths so cross-section >= 30 threshold is met.
    names = [f"data/yahoo/P{i:03d}.parquet" for i in range(60)]
    # Deterministic panel values.
    panel_aligned = {p: walk(dates, seed=i + 2) for i, p in enumerate(names)}
    panel_dates = {p: dates for p in names}

    def _stable_char(subj_dates, subj_aligned, t):
        # characteristics_at expects characteristics_at(dates, aligned, t) and
        # returns dict with mom_12_1/vol_63/rev_21 keys or None.
        try:
            from s1_challenger import characteristics_at as _real
            return _real(subj_dates, subj_aligned, t)
        except Exception:
            return None

    monkeypatch.setattr(run_s1, "characteristics_at", _stable_char)

    # Use gamma where g[0] != g[1] so the mutation is observable.
    ctx = {
        "gamma": [1.0, 5.0, 0.0, 0.0],
        "universe_paths": names,
        "panel_dates": panel_dates,
        "panel_aligned": panel_aligned,
        "spy_close": {d: 100.0 + 0.001 * i for i, d in enumerate(dates)},
    }
    out = run_s1.challenger_apply(ctx, dates, subj_close, s, fill, coverage)
    assert out["state"] == "OK"
    beta = out["beta_ipca__dc"]
    # The mutation replaces g[0] with g[1]. With gamma=[1, 5, 0, 0] the original
    # intercept contribution is 1.0 (g[0]=1), the mutated is 5.0 (g[1]=5).
    # The shift between original and mutated beta is exactly (g[1] - g[0]) = 4.0
    # (everything else equal), so if the original is X, the mutated is X + 4.0.
    # We don't know X here without re-running, so instead pin the range:
    # original beta = 1.0 + 5.0*zm["BABA"] + 0 + 0 = 1.0 + 5.0*zm.
    # Mutated beta = 5.0 + 5.0*zm["BABA"] + 0 + 0 = 5.0 + 5.0*zm.
    # Both share the same slope (5.0*zm) so the difference is a fixed offset of 4.0.
    # We can't easily know zm["BABA"] independently, so drive a setup where zm=0.
    # Instead, verify that beta is consistent with the gamma contribution: with
    # zm/zu/zr all equal to some value z, original beta = 1 + 5z, mutated = 5 + 5z.
    # The difference of 4 is exact and observable IF we can pin zm. We can pin it
    # by constructing a panel where BABA's standardised characteristics are
    # known. However, characteristics_at is complex, so we use the cross-section
    # structure: rank_standardise yields deterministic values. We instead rely
    # on the existing MUT5C test surface plus a stronger assertion.
    #
    # Stronger assertion: if mutated, beta_ipca__dc >= 4.0 (because zm["BABA"]
    # is bounded by the rank_standardise range, typically [-3, 3], so 5*zm in
    # [-15, 15], and adding g[1]=5 instead of g[0]=1 shifts beta by exactly 4).
    # If the mutation is applied, beta >= 5.0 - 15 = -10.0 (no useful bound).
    # Use a specific gamma where g[0]=0 and g[1]=10. Then original beta can be
    # near 0 (if zm is bounded), mutated beta can be near 10. Difference 10.
    ctx2 = {
        "gamma": [0.0, 10.0, 0.0, 0.0],
        "universe_paths": names,
        "panel_dates": panel_dates,
        "panel_aligned": panel_aligned,
        "spy_close": {d: 100.0 + 0.001 * i for i, d in enumerate(dates)},
    }
    out2 = run_s1.challenger_apply(ctx2, dates, subj_close, s, fill, coverage)
    # Use first gamma where g[0]=0: rank_standardise maps BABA's char to a z-score.
    # Since panel_aligned varies per name, zm["BABA"] is bounded roughly in
    # [-3, 3] (rank_standardise over 60 names places it in this range). The
    # original beta = 0 + 10*zm["BABA"] = 10*zm["BABA"], so abs(beta) <= ~30.
    # The mutated beta = 10 + 10*zm["BABA"], so abs(beta) >= 10 - 30 = bounded.
    # The difference is exactly 10.0. We use a sharper test:
    # If the mutation were applied, beta would equal original + 10. We need
    # to verify beta is consistent with original. We can compute zm["BABA"]
    # from the panel data independently.
    beta_orig_call = out2["beta_ipca__dc"]
    # Recompute zm["BABA"] using the public helpers.
    from s1_challenger import characteristics_at as _real_char
    from s1_challenger import rank_standardise as _real_rank

    ch_baba = _real_char(dates, aligned, s)
    if ch_baba is None:
        pytest.skip("BABA characteristics unavailable at anchor; non-estimable path")
    combined = {}
    for p in ctx2["universe_paths"]:
        c = _real_char(panel_dates[p], panel_aligned[p], s)
        if c is not None:
            combined[p] = c
    combined["BABA"] = ch_baba
    zm = _real_rank({k: v["mom_12_1"] for k, v in combined.items()})
    zv = _real_rank({k: v["vol_63"] for k, v in combined.items()})
    zr = _real_rank({k: v["rev_21"] for k, v in combined.items()})
    expected = (
        ctx2["gamma"][0]
        + ctx2["gamma"][1] * zm["BABA"]
        + ctx2["gamma"][2] * zv["BABA"]
        + ctx2["gamma"][3] * zr["BABA"]
    )
    assert beta_orig_call == pytest.approx(expected, abs=1e-9), (
        f"challenger_apply returned {beta_orig_call}; "
        f"expected {expected} with original gamma[0] contribution"
    )


def test_m6i_run_s1_load_frames_first_series_1():
    """run_s1.py:468, const_int d[-1] -> d[-2] on the first-iteration branch only."""

    class _Store:
        def frame(self, path, columns):
            # BABA (index 0) has 3 dates; the LAST is the canonical last_bar.
            # The mutation changes d[-1] -> d[-2] on the None branch ONLY.
            # Original: last_bar starts at BABA's d[-1] = 2024-06-04.
            # Mutated: last_bar starts at BABA's d[-2] = 2024-05-30; subsequent
            # max() calls still use d[-1] (unmutated), so 3033.HK's d[-1] (the
            # canonical last bar) still drives last_bar to 2024-06-04 if its
            # d[-1] > the mutated starting value. To detect, we need ALL
            # subsequent series to have d[-1] <= BABA's d[-2].
            if "BABA" in path:
                ds = [date(2024, 5, 28), date(2024, 5, 30), date(2024, 6, 4)]
            else:
                # All other series end on or before BABA's d[-2] = 2024-05-30.
                ds = [date(2024, 5, 28), date(2024, 5, 30)]
            return ds, {c: [10.0 + i for i in range(len(ds))] for c in columns}

    frames, last_bar = run_s1.load_frames(_Store())
    # Original: last_bar = BABA's d[-1] = 2024-06-04.
    # Mutated: last_bar = BABA's d[-2] = 2024-05-30 (because subsequent max()
    # values are <= 2024-05-30).
    assert last_bar == date(2024, 6, 4)