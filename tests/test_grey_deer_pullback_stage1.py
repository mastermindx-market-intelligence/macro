"""Grey Deer W3: synthetic tests for the pullback stage-1 executing script.

Preregistration: ``research/grey_deer/PULLBACK_PREREGISTRATION_2026-10-11.md``
(blob ``49a68b5e9c6543d662044b0aa391c4b6e6e6052e``). §12 requires the dedicated
test file to prove, on synthetic data only: the purge, the fold calendar, the
comparison-set intersection, the reuse of one index draw across configurations
and the crossing-then-clip order. This file carries the part-1 subset (tests
1, 2, 5, 6, 7 of the lane packet plus the recommended logistic gradient check);
tests 3 and 4 land with GD-W3-BUILD part 2.

Synthetic only: fixed-seed geometric random walks and hand-built arrays. No
``data/`` read or write, no network, no Massive store, no trial-ledger write,
no git-state dependence. ``load_ticker`` / ``fetch_r2`` / ``register_trials`` /
``subprocess`` appear ONLY as monkeypatch targets.

Run:
    python -m pytest tests/test_grey_deer_pullback_stage1.py -v
"""
from __future__ import annotations

import hashlib
import json
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scripts.research.grey_deer_pullback_stage1 as stage1  # noqa: E402


# ── helpers ──────────────────────────────────────────────────────────────────


def _random_walk_closes(n: int = 400, seed: int = 5) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return 400.0 * np.exp(np.cumsum(rng.normal(0.0, 0.011, n)))


def _raise_assertion(*_a, **_k):
    raise AssertionError("must not be called on this path")


# ── test 1: purge ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("h", stage1.HORIZONS)
def test_purge_excludes_origins_whose_horizon_crosses_fold_start(h):
    s0 = stage1.FIRST_TEST_IDX
    for candidates in (np.arange(0, s0), np.arange(stage1.WARM_IDX, s0)):
        kept = stage1.purged_training_indices(s0, h, candidates)
        assert kept.size
        # Frozen rule (prereg §7): admit training origin t only when idx(t)+h <= idx(s0).
        assert (kept + h <= s0).all()
        # The origin whose window ends exactly at the fold start is KEPT...
        assert (s0 - h) in kept
        # ...and the very next origin (window crossing into the test block) is not.
        assert (s0 - h + 1) not in kept
        assert (kept < s0).all()


# ── test 2: fold calendar ────────────────────────────────────────────────────


def test_fold_calendar_matches_prereg():
    # Synthetic index of 1,321 sessions (the frozen sample size), test region
    # running to the last row: first test idx 315, 8 blocks of 126 with a
    # 124-origin final block (>= 63, so no merge) — prereg §7 geometry.
    cal = stage1.build_fold_calendar(stage1.FIRST_TEST_IDX, 1320)
    assert cal[0][0] == stage1.FIRST_TEST_IDX
    assert len(cal) == 8
    lengths = [e - s + 1 for s, e in cal]
    assert all(l == stage1.BLOCK_LEN for l in lengths[:-1])
    assert lengths[-1] == 124
    assert min(lengths) >= stage1.MIN_FINAL_BLOCK  # no test block shorter than 63
    assert cal[-1][1] == 1320
    # Blocks are consecutive and non-overlapping.
    for (s1, e1), (s2, e2) in zip(cal, cal[1:]):
        assert e1 + 1 == s2
    # Per-horizon mature ends from prereg §7: last block 119 / 114 / 103 origins.
    assert [e - s + 1 for s, e in stage1.build_fold_calendar(315, 1320 - 5)][-1] == 119
    assert [e - s + 1 for s, e in stage1.build_fold_calendar(315, 1320 - 10)][-1] == 114
    assert [e - s + 1 for s, e in stage1.build_fold_calendar(315, 1320 - 21)][-1] == 103
    # A final remainder shorter than 63 merges into its predecessor.
    merged = stage1.build_fold_calendar(315, 1197 + 40 - 1)  # 40-origin remainder
    assert len(merged) == 7
    assert merged[-1] == (1071, 1236)
    assert all(e - s + 1 >= stage1.MIN_FINAL_BLOCK for s, e in merged)


# ── test 5: crossing detected on unclipped predictions, then clip ────────────


def test_quantile_crossing_detected_before_clip():
    crossing = (
        np.array([0.03]),
        np.array([0.02]),
        np.array([0.05]),
    )  # q0.5 > q0.8 on the UNCLIPPED values -> that origin abstains
    issued, clipped, reasons = stage1.quantile_output_policy(*crossing)
    assert issued.tolist() == [False]
    assert reasons[0] == "QUANTILE_CROSSING"

    negative = (np.array([-0.01]), np.array([0.02]), np.array([0.05]))
    issued, clipped, reasons = stage1.quantile_output_policy(*negative)
    assert issued.tolist() == [True]
    assert reasons[0] is None
    q50, q80, q90 = clipped
    assert q50.tolist() == [0.0]  # clipped below at 0 only AFTER the crossing check
    assert q80.tolist() == [0.02]
    assert q90.tolist() == [0.05]


# ── test 6: in-memory identity recipe == the §3 reference recipe ─────────────


def _prereg_reference_sha(path: str) -> str:
    """The prereg §3 identity recipe, copied verbatim.

    Only the ``p = sys.argv[1]`` line becomes the ``path`` parameter and the
    final ``print`` becomes a return; every other line is byte-for-byte the
    frozen recipe from PULLBACK_PREREGISTRATION_2026-10-11.md §3.
    """
    import hashlib
    import pandas as pd  # noqa: F811  (verbatim recipe body)

    p = path
    raw = open(p, "rb").read()  # noqa: F841  (part of the frozen recipe)
    df = pd.read_parquet(p)
    df = df.reset_index(drop=("date" in df.columns))
    if "date" not in df.columns:
        df = df.rename(columns={df.columns[0]: "date"})
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    cols = ["date", "open", "high", "low", "close", "volume", "transactions"]
    sub = df[df["date"] <= "2026-10-07"][cols].sort_values("date")

    def enc(v):
        if isinstance(v, str):
            return v
        if pd.isna(v):
            return "NA"
        return float(v).hex()

    h = hashlib.sha256()
    h.update(("|".join(cols) + "\n").encode())
    for row in sub.itertuples(index=False):
        h.update(("|".join(enc(v) for v in row) + "\n").encode())
    return h.hexdigest()


def test_identity_recipe_matches_reference_on_synthetic_frame(tmp_path):
    rng = np.random.default_rng(11)
    n = 30
    idx = pd.bdate_range("2026-09-01", periods=n)
    assert (idx > "2026-10-07").any()  # fixture really has rows after AS_OF
    close = _random_walk_closes(n, seed=11)
    frame = pd.DataFrame(
        {
            "open": close * (1 + rng.normal(0, 0.002, n)),
            "high": close * (1 + np.abs(rng.normal(0, 0.004, n))),
            "low": close * (1 - np.abs(rng.normal(0, 0.004, n))),
            "close": close,
            "volume": rng.integers(4_000_000, 9_000_000, n).astype(float),
            "transactions": rng.integers(80_000, 200_000, n).astype(float),
        },
        index=idx.rename("date"),
    )
    frame.loc[frame.index[3], "volume"] = np.nan  # the NA encoding path
    frame.loc[frame.index[7], "volume"] = np.nan
    p = tmp_path / "SPY.parquet"
    frame.to_parquet(p)

    # The in-memory recipe applied to the frame load_ticker would return (never
    # a second read of the file) must equal the §3 reference run on the path.
    loaded = pd.read_parquet(p)
    sub = stage1.normalize_subframe(loaded)
    got = stage1.subframe_sha256(sub)
    want = _prereg_reference_sha(str(p))
    assert got == want
    # Sanity: the hashed subframe drops the post-AS_OF rows and encodes NA.
    n_expected = int((sub["date"] <= stage1.AS_OF).sum())
    assert len(sub) == n_expected < n
    assert "NA" in {stage1._enc(v) for v in frame["volume"].tolist()}


# ── test 7: --dry-run touches no data; empty store blocks without a ledger ───


def test_dry_run_reads_no_data(tmp_path, monkeypatch, capsys):
    canned = {
        "schema": stage1.SCHEMA,
        "prereg": {
            "path": stage1.PREREG_PATH,
            "blob_sha": stage1.PREREG_BLOB,
            "sha256": stage1.PREREG_SHA256,
        },
        "manifest": {
            "path": stage1.MANIFEST_PATH,
            "blob_sha": stage1.MANIFEST_BLOB,
            "version": stage1.MANIFEST_VERSION,
        },
        "run": {
            "utc": "canned",
            "commit_sha": "canned",
            "script_blob_sha": "canned",
            "test_blob_sha": "canned",
        },
    }
    monkeypatch.setattr(stage1, "verify_identities", lambda **kwargs: dict(canned))

    # load_ticker is patched at its home module as the script imports it; a
    # stub module keeps the real collectors chain (requests/yaml) unimported.
    stub = types.ModuleType("collectors.massive_stock_day")
    stub.load_ticker = _raise_assertion
    monkeypatch.setitem(sys.modules, "collectors.massive_stock_day", stub)
    monkeypatch.setattr(stage1.subprocess, "run", _raise_assertion)
    monkeypatch.setattr(stage1.trial_ledger, "register_trials", _raise_assertion)

    assert stage1.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "PULLBACK_PREREGISTRATION_2026-10-11.md" in out
    assert stage1.PREREG_BLOB in out
    assert any(cfg_id in out for cfg_id in ("M3-ALL", "B0"))  # configuration table

    # An empty store frame blocks as SOURCE_UNREADABLE before any ledger entry.
    stub.load_ticker = lambda *_a, **_k: pd.DataFrame()
    assert stage1.main(["--skip-hydrate", "--out-dir", str(tmp_path)]) == 2
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "BLOCKED / SOURCE_UNREADABLE"
    blocked = json.loads((tmp_path / "PULLBACK_STAGE1_RESULTS_2026-10-11.json").read_text())
    assert blocked["blocked"][0]["type"] == "SOURCE_UNREADABLE"
    assert blocked["run"]["commit_sha"] == "canned"


# ── recommended: logistic objective/gradient consistency ─────────────────────


def test_logistic_objective_gradient_matches_finite_differences():
    rng = np.random.default_rng(3)
    n, p = 60, 4
    X = np.column_stack([np.ones(n), rng.normal(size=(n, p - 1))])
    y = (rng.random(n) < 0.3).astype(float)
    for C in (stage1.C_MAIN, stage1.C_SENS):
        beta = rng.normal(size=p)
        val, grad = stage1.logistic_objective_and_gradient(beta, X, y, C)
        assert np.isfinite(val)
        eps = 1e-6
        num = np.empty(p)
        for j in range(p):
            up, dn = beta.copy(), beta.copy()
            up[j] += eps
            dn[j] -= eps
            num[j] = (
                stage1.logistic_objective_and_gradient(up, X, y, C)[0]
                - stage1.logistic_objective_and_gradient(dn, X, y, C)[0]
            ) / (2 * eps)
        np.testing.assert_allclose(grad, num, rtol=1e-5, atol=1e-6)
