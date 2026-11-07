"""The analyst-revision drip runs in collect_tail, not on the engine job's render path.

macro #7646 root cause (2026-11-07): ``collectors.equity_revisions.fetch_revisions``
was called from inside ``scripts/build_stock_library.py`` on the nightly engine job —
102 of build_site's 143 minutes on 2026-11-06 — the one step that carried the engine
job past the runner kill six nights running. daily.yml's collect_tail now runs the
collector's CLI bare and the engine job sets ``MACRO_REVISIONS_DRIP=collect_tail`` so
the stock library reads the committed parquet instead of dripping.

Three contracts pinned here, hermetically (no network, no live stores):

1. ``drip_if_owner`` — the guard the stock library consults — drips only for the
   owner named by the environment, and keeps the historical in-build-site default
   when the variable is unset (ad-hoc local builds must not silently stop accruing).
2. The CLI's bare default is the nightly config cap (``equity_profile.per_build``),
   not the pre-move 50-name smoke default, and an argv overrides it.
3. Progress is checkpointed every ``PERSIST_EVERY`` names, so a step-timeout-
   truncated night keeps what it fetched and the next night drips only the rest.

Run: .venv/bin/python -m pytest --noconftest tests/test_revisions_drip_offrender.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collectors import equity_revisions as revisions  # noqa: E402


class _Recorder:
    def __init__(self, result: int = 3) -> None:
        self.calls: list[dict] = []
        self.result = result

    def __call__(self, max_new: int = 200, **kwargs):
        self.calls.append({"max_new": max_new, **kwargs})
        return self.result


# ── 1. ownership guard ────────────────────────────────────────────────────────

def test_default_owner_is_build_site_when_unset_or_blank():
    assert revisions.nightly_drip_owner({}) == "build_site"
    assert revisions.nightly_drip_owner({"MACRO_REVISIONS_DRIP": ""}) == "build_site"
    assert revisions.nightly_drip_owner({"MACRO_REVISIONS_DRIP": "  "}) == "build_site"
    assert revisions.nightly_drip_owner({"MACRO_REVISIONS_DRIP": "collect_tail"}) == "collect_tail"


def test_build_site_skips_the_drip_when_collect_tail_owns_it(monkeypatch, caplog):
    rec = _Recorder()
    monkeypatch.setattr(revisions, "fetch_revisions", rec)
    caplog.set_level("INFO", logger="equity_revisions")
    out = revisions.drip_if_owner("build_site", max_new=5, environ={"MACRO_REVISIONS_DRIP": "collect_tail"})
    assert out is None
    assert rec.calls == [], "build_site dripped although collect_tail owns the nightly drip"
    assert "reading the committed parquet" in caplog.text


def test_build_site_still_drips_when_the_variable_is_unset(monkeypatch):
    rec = _Recorder(result=7)
    monkeypatch.setattr(revisions, "fetch_revisions", rec)
    assert revisions.drip_if_owner("build_site", max_new=5, environ={}) == 7
    assert rec.calls == [{"max_new": 5}]


def test_named_owner_drips_and_a_bare_call_uses_the_config_cap(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(revisions, "fetch_revisions", rec)
    monkeypatch.setattr(revisions, "per_build_cap", lambda: 123)
    env = {"MACRO_REVISIONS_DRIP": "collect_tail"}
    assert revisions.drip_if_owner("collect_tail", environ=env) == 3
    assert rec.calls == [{"max_new": 123}]


def test_the_guard_reads_the_process_environment_by_default(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(revisions, "fetch_revisions", rec)
    monkeypatch.setenv("MACRO_REVISIONS_DRIP", "collect_tail")
    assert revisions.drip_if_owner("build_site", max_new=1) is None
    monkeypatch.delenv("MACRO_REVISIONS_DRIP")
    assert revisions.drip_if_owner("build_site", max_new=1) == 3
    assert rec.calls == [{"max_new": 1}]


# ── 2. CLI cap ────────────────────────────────────────────────────────────────

def test_per_build_cap_reads_the_stock_library_key_with_the_same_default(monkeypatch):
    monkeypatch.setattr(revisions.config, "load", lambda: {"equity_profile": {"per_build": 7}})
    assert revisions.per_build_cap() == 7
    monkeypatch.setattr(revisions.config, "load", lambda: {})
    assert revisions.per_build_cap() == 200


def test_bare_cli_drips_the_config_cap_and_argv_overrides_it(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(revisions, "fetch_revisions", rec)
    monkeypatch.setattr(revisions, "per_build_cap", lambda: 200)
    assert revisions.main([]) == 0
    assert revisions.main(["12"]) == 0
    assert [c["max_new"] for c in rec.calls] == [200, 12], (
        "a bare CLI run must drip the nightly cap — the pre-move default was a "
        "50-name smoke cap that would silently starve the store"
    )


# ── 3. checkpointed persistence ───────────────────────────────────────────────

def _hermetic(monkeypatch, tmp_path: Path, universe: list[str]) -> None:
    monkeypatch.setattr(revisions.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(revisions, "_universe", lambda: list(universe))
    monkeypatch.setattr(
        revisions, "accrue_expectation_observations",
        lambda *a, **k: {"attempts": 0, "observations": 0},
    )


def test_a_truncated_drip_keeps_its_checkpointed_names_and_resumes(monkeypatch, tmp_path):
    """A step timeout kills the process mid-loop (modelled as a BaseException the
    per-name guard does not swallow). Everything fetched up to the last checkpoint
    must already be on disk, and the next run must drip only the remaining names."""
    names = [f"T{i:03d}" for i in range(60)]
    _hermetic(monkeypatch, tmp_path, names)
    seen: list[str] = []

    def _one_then_killed(t):
        if len(seen) == 55:
            raise KeyboardInterrupt("step timeout")
        seen.append(t)
        return {"breadth": 0.1, "n_analysts": 3}

    monkeypatch.setattr(revisions, "_one", _one_then_killed)
    with pytest.raises(KeyboardInterrupt):
        revisions.fetch_revisions(max_new=200)
    latest = pd.read_parquet(tmp_path / "revisions" / "latest.parquet")
    history = pd.read_parquet(tmp_path / "revisions" / "history.parquet")
    assert len(latest) == 50 and len(history) == 50, (
        f"expected two 25-name checkpoints on disk, got latest={len(latest)} history={len(history)}"
    )
    assert list(latest.columns) == ["breadth", "n_analysts", "asof"]
    assert list(history.columns) == ["ticker", "breadth", "n_analysts", "asof", "date"]

    monkeypatch.setattr(revisions, "_one", lambda t: {"breadth": 0.2, "n_analysts": 4})
    assert revisions.fetch_revisions(max_new=200) == 10, "the resumed night must drip only the 10 unfetched names"
    latest = pd.read_parquet(tmp_path / "revisions" / "latest.parquet")
    history = pd.read_parquet(tmp_path / "revisions" / "history.parquet")
    assert len(latest) == 60 and sorted(latest.index) == names
    assert len(history) == 60 and history["ticker"].is_unique


def test_checkpoints_are_idempotent_per_date_and_ticker(tmp_path):
    out = tmp_path / "revisions"
    out.mkdir()
    today = pd.Timestamp("2026-11-07")
    rows = {"ACME": {"breadth": 0.5, "n_analysts": 4}}
    latest, n = revisions._persist_snapshot(out, pd.DataFrame(), dict(rows), today)
    assert n == 1 and len(latest) == 1
    latest, n = revisions._persist_snapshot(out, latest, dict(rows), today)
    assert n == 1 and len(latest) == 1, "re-persisting the same (date, ticker) must not duplicate history"
    history = pd.read_parquet(out / "history.parquet")
    assert history["ticker"].tolist() == ["ACME"]


def test_a_single_chunk_run_matches_the_legacy_single_write(monkeypatch, tmp_path):
    """The legacy latest/history shape (pinned by the SRC-A1 acceptance suite) is
    unchanged when the drip finishes inside one checkpoint."""
    _hermetic(monkeypatch, tmp_path, ["ACME", "BETA"])
    monkeypatch.setattr(revisions, "_one", lambda t: {"breadth": 0.5, "n_analysts": 4})
    assert revisions.fetch_revisions(max_new=2) == 2
    latest = pd.read_parquet(tmp_path / "revisions" / "latest.parquet")
    history = pd.read_parquet(tmp_path / "revisions" / "history.parquet")
    assert sorted(latest.index) == ["ACME", "BETA"]
    assert list(history.columns) == ["ticker", "breadth", "n_analysts", "asof", "date"]
    assert sorted(history["ticker"]) == ["ACME", "BETA"]
