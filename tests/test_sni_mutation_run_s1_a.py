"""MUT5B killing tests for run_s1.py (owned site range SealMismatch..load_frames).

SNI-local DRAFT contract tests. They consume caller-supplied synthetic rows,
close maps, and opaque identity strings owned by Stock Identity / Data OS;
they do not mint issuer or security identifiers and they do not feed a rank,
gate, size, signal, escalation, or trade path. Authority flags stay false.
Fixtures are synthetic.

Each test_mut5b_* docstring names one non-equivalent mutant that survived
the pre-existing importer suite (file:line, original -> mutated).
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/residual"),
)

import run_s1  # noqa: E402
from s1_manifest import is_session_fn  # noqa: E402
from s1_prereg import HORIZONS  # noqa: E402


def test_mut5b_run_s1_canon_1():
    """run_s1.py:99, sort_keys True -> False."""
    obj = {"z": 1, "a": 2}
    assert run_s1.canon(obj) == '{"a":2,"z":1}'


def test_mut5b_run_s1_code_tree_sha_1(monkeypatch):
    """run_s1.py:153, BoolOp `or` -> `and` in git_out fallback."""
    monkeypatch.setattr(run_s1, "git_out", lambda *a, **k: "deadbeefcafebabe")
    assert run_s1.code_tree_sha(Path(".")) == "deadbeefcafebabe"


def test_mut5b_run_s1_directional_blocks_1():
    """run_s1.py:342, TUNE abstain_resolver_none init 0 -> 1."""
    rebuilt = {}
    for h in HORIZONS:
        rebuilt[("P01", "adr_baba", h)] = {
            "rows": [],
            "digests": {
                "TRAIN": {"membership_sha256": "0" * 64, "count": 0},
                "TUNE": {"membership_sha256": "0" * 64, "count": 0},
            },
        }
    obs_tune = {
        "episode_key": "synthetic-ek-tune",
        "anchor_session_date": "2024-06-03",
        "coverage_date": "2024-06-10",
        "manifest_split": "TUNE",
        "split": "TUNE",
        "time_split": "TUNE",
        "abstention": "OK",
        "excess": 0.01,
        "tie": False,
        "always_long_direction": 1,
        "trail63_direction": 1,
    }
    evaluation = {
        "observations": {
            "P01_adr_baba_5": [obs_tune],
            "P01_adr_baba_21": [],
            "P01_adr_baba_63": [],
        }
    }
    blocks, _ = run_s1.directional_blocks(
        "P01",
        evaluation,
        rebuilt,
        set(),
        trial_accounting={"literal_n": 0, "effective_n": 0, "declared_budget": 6},
        receipt_base={},
    )
    tune = [blk for key, blk in blocks.items() if "|TUNE" in key and "|h=5|" in key]
    assert tune
    for blk in tune:
        detail = (blk.get("exclusions") or {}).get("detail") or {}
        assert detail.get("abstain_resolver_none") == 0


def test_mut5b_run_s1_doc_json_1():
    """run_s1.py:106, ensure_ascii False -> True."""
    text = run_s1.doc_json({"note": "café"})
    assert "é" in text
    assert "\\u00e9" not in text


def test_mut5b_run_s1_evaluate_directional_1():
    """run_s1.py:310, resolve_horizon_window as-of `s - timedelta` -> `s + timedelta`."""
    is_us = is_session_fn("US")
    sessions = []
    cur = date(2022, 1, 3)
    while cur < date(2023, 8, 1):
        if is_us(cur):
            sessions.append(cur)
        cur += timedelta(days=1)
    s = date(2023, 6, 15)
    assert s in sessions

    class _Store:
        def frame(self, path, columns):
            cols = {c: [100.0 + i * 0.1 for i, _ in enumerate(sessions)] for c in columns}
            return list(sessions), cols

    rebuilt = {}
    for h in HORIZONS:
        rebuilt[("P01", "adr_baba", h)] = {
            "rows": (
                [{
                    "episode_key": "synthetic-ek",
                    "anchor_session_date": s.isoformat(),
                    "coverage_date": "2023-06-23",
                    "split": "TRAIN",
                }]
                if h == 5
                else []
            ),
            "digests": {
                "TRAIN": {"membership_sha256": "0" * 64, "count": 1},
                "TUNE": {"membership_sha256": "0" * 64, "count": 0},
            },
        }
    ev = run_s1.evaluate_directional("P01", _Store(), rebuilt)
    obs = ev["observations"]["P01_adr_baba_5"]
    assert len(obs) == 1
    assert obs[0]["abstention"] == "OK"
    assert obs[0]["excess"] is not None


def test_mut5b_run_s1_git_out_1(monkeypatch):
    """run_s1.py:144, return stdout.strip() on rc==0 -> return None."""

    class _R:
        returncode = 0
        stdout = "synthetic-out\n"

    monkeypatch.setattr(run_s1.subprocess, "run", lambda *a, **k: _R())
    assert run_s1.git_out(Path("."), ["rev-parse", "--is-inside-work-tree"]) == "synthetic-out"


def test_mut5b_run_s1_leg_simple_ret_1():
    """run_s1.py:269, comparison `a <= 0` -> `a < 0` (zero-price guard)."""
    fill = date(2024, 1, 2)
    cov = date(2024, 1, 3)
    assert run_s1.leg_simple_ret({fill: 0.0, cov: 10.0}, fill, cov) is None
    assert run_s1.leg_simple_ret({fill: 10.0, cov: 11.0}, fill, cov) == round(11.0 / 10.0 - 1.0, 6)


def test_mut5b_run_s1_rebuild_manifests_1(monkeypatch):
    """run_s1.py:201, last_bar dates[-1] -> dates[-2]."""
    last = date(2019, 6, 5)
    dates = [date(2019, 6, 3), date(2019, 6, 4), last]
    seen: list[date] = []

    def _fake_build_rows(pid, issuer, counter, sec, market, h, subject_dates, last_bar):
        seen.append(last_bar)
        return []

    monkeypatch.setattr(run_s1, "build_rows", _fake_build_rows)
    monkeypatch.setattr(run_s1, "manifest_bytes", lambda rows: b"")
    monkeypatch.setattr(run_s1, "split_digests", lambda rows: {})

    class _Store:
        def index_dates(self, path):
            return list(dates)

    out = run_s1.rebuild_manifests(_Store())
    assert isinstance(out, dict) and out
    assert seen
    assert all(lb == last for lb in seen)


def test_mut5b_run_s1_seal_commit_sha_1(monkeypatch):
    """run_s1.py:158, BoolOp `or` -> `and` in git_out fallback."""
    monkeypatch.setattr(run_s1, "git_out", lambda *a, **k: "cafebabedeadbeef")
    assert run_s1.seal_commit_sha(Path(".")) == "cafebabedeadbeef"
