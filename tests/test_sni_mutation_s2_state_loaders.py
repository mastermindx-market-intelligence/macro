"""MUT4A killing tests for s2_state.py and s2_loaders.py survivors.

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings (Stock Identity / Data OS) and never mint issuer or security ids.
HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority, size_authority,
signal_authority, escalation_authority and trade_authority stay false.
Fixtures are synthetic. Residuals and event-study numbers are descriptive,
never causal, never a news-impact claim.

Each test_mut4a_<module>_<function>_<n> docstring names the surviving mutant
from the 2026-10-13 sweep (seed 20261013).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research/single_name_intelligence/event_response"))

from s2_loaders import (  # noqa: E402
    ColumnRequestSpy,
    GitBlobLoader,
    InputVerificationError,
    _git,
    verify_pinned_blobs,
)
from s2_seal import (  # noqa: E402
    EARNINGS_METADATA_COLUMNS,
    EVENTS_METADATA_COLUMNS,
    SECURITY_MASTER_ID_COLUMNS,
)
from s2_state import compute_state  # noqa: E402


def _empty_frame(columns: tuple[str, ...]) -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in columns})


class _SyntheticStateLoader:
    """In-memory loader: synthetic empty tables, no git, no credentials."""

    def read_json(self, path: str) -> dict:
        return {"synthetic": True, "path": path}

    def read_parquet(self, path: str, columns=None) -> pd.DataFrame:
        if path.endswith("events.parquet"):
            df = _empty_frame(EVENTS_METADATA_COLUMNS)
        elif path.endswith("earnings.parquet"):
            df = _empty_frame(EARNINGS_METADATA_COLUMNS)
        else:
            df = _empty_frame(SECURITY_MASTER_ID_COLUMNS)
        if columns is None:
            return df
        return df[[c for c in columns if c in df.columns]]


class _Inner:
    def read_parquet(self, path, columns=None):
        return pd.DataFrame({"col_a": [1], "col_b": [2]})

    def read_yaml(self, path):
        return {"k": "v"}

    def read_json(self, path):
        return {"k": "v"}

    def read_text(self, path):
        return "hello"

    def read_bytes(self, path):
        return b"hello"


def _loader() -> GitBlobLoader:
    return GitBlobLoader(Path("/tmp/sni-mut4a-synthetic"), "synthetic-ref", manifest={})


# ---------------------------------------------------------------------------
# s2_state survivors
# ---------------------------------------------------------------------------


def test_mut4a_s2_state_compute_state_1() -> None:
    """s2_state.py:55, delete if got != want: raise SystemExit (identity pin)."""
    with pytest.raises(SystemExit, match="seal pins"):
        compute_state(_SyntheticStateLoader())


# ---------------------------------------------------------------------------
# s2_loaders survivors
# ---------------------------------------------------------------------------


def test_mut4a_s2_loaders__git_1(monkeypatch) -> None:
    """s2_loaders.py:48, 400 -> 401 (_git stderr slice)."""

    def fake_run(*_a, **_k):
        return SimpleNamespace(returncode=1, stdout="", stderr="Z" * 500)

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(InputVerificationError) as ei:
        _git(Path("/tmp/sni-mut4a-synthetic"), "rev-parse", "synthetic:path")
    assert str(ei.value).count("Z") == 400


def test_mut4a_s2_loaders__git_2(monkeypatch) -> None:
    """s2_loaders.py:46, delete if proc.returncode != 0: raise (_git)."""

    def fake_run(*_a, **_k):
        return SimpleNamespace(returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(InputVerificationError, match="git rev-parse synthetic:path failed"):
        _git(Path("/tmp/sni-mut4a-synthetic"), "rev-parse", "synthetic:path")


def test_mut4a_s2_loaders_read_bytes_1(monkeypatch) -> None:
    """s2_loaders.py:68, delete if proc.returncode != 0: raise (GitBlobLoader.read_bytes)."""

    def fake_run(*_a, **_k):
        return SimpleNamespace(returncode=1, stdout=b"", stderr=b"missing")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(InputVerificationError, match="cat-file"):
        _loader().read_bytes("synthetic.parquet")


def test_mut4a_s2_loaders_read_bytes_2(monkeypatch) -> None:
    """s2_loaders.py:71, 400 -> 401 (GitBlobLoader.read_bytes stderr slice)."""

    def fake_run(*_a, **_k):
        return SimpleNamespace(returncode=1, stdout=b"", stderr=b"Z" * 500)

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(InputVerificationError) as ei:
        _loader().read_bytes("synthetic.parquet")
    assert str(ei.value).count("Z") == 400


def test_mut4a_s2_loaders_read_bytes_3() -> None:
    """s2_loaders.py:110, return self.inner.read_bytes(path) -> return None (ColumnRequestSpy)."""
    spy = ColumnRequestSpy(_Inner())
    assert spy.read_bytes("synthetic.bin") == b"hello"


def test_mut4a_s2_loaders_read_json_1(monkeypatch) -> None:
    """s2_loaders.py:83, return json.loads(...) -> return None (GitBlobLoader.read_json)."""
    loader = _loader()
    monkeypatch.setattr(loader, "read_bytes", lambda _path: b'{"k": "v"}')
    assert loader.read_json("synthetic.json") == {"k": "v"}


def test_mut4a_s2_loaders_read_json_2() -> None:
    """s2_loaders.py:104, return self.inner.read_json(path) -> return None (ColumnRequestSpy)."""
    spy = ColumnRequestSpy(_Inner())
    assert spy.read_json("synthetic.json") == {"k": "v"}


def test_mut4a_s2_loaders_read_parquet_1() -> None:
    """s2_loaders.py:98, return self.inner.read_parquet(...) -> return None (ColumnRequestSpy)."""
    spy = ColumnRequestSpy(_Inner())
    frame = spy.read_parquet("synthetic.parquet", columns=["col_a"])
    assert list(frame.columns) == ["col_a", "col_b"]
    assert frame["col_a"].tolist() == [1]


def test_mut4a_s2_loaders_read_text_1(monkeypatch) -> None:
    """s2_loaders.py:86, return self.read_bytes(path).decode(...) -> return None (GitBlobLoader)."""
    loader = _loader()
    monkeypatch.setattr(loader, "read_bytes", lambda _path: b"hello")
    assert loader.read_text("synthetic.txt") == "hello"


def test_mut4a_s2_loaders_read_text_2() -> None:
    """s2_loaders.py:107, return self.inner.read_text(path) -> return None (ColumnRequestSpy)."""
    spy = ColumnRequestSpy(_Inner())
    assert spy.read_text("synthetic.txt") == "hello"


def test_mut4a_s2_loaders_read_yaml_1(monkeypatch) -> None:
    """s2_loaders.py:80, return yaml.safe_load(...) -> return None (GitBlobLoader.read_yaml)."""
    loader = _loader()
    monkeypatch.setattr(loader, "read_bytes", lambda _path: b"k: v\n")
    assert loader.read_yaml("synthetic.yml") == {"k": "v"}


def test_mut4a_s2_loaders_read_yaml_2() -> None:
    """s2_loaders.py:101, return self.inner.read_yaml(path) -> return None (ColumnRequestSpy)."""
    spy = ColumnRequestSpy(_Inner())
    assert spy.read_yaml("synthetic.yml") == {"k": "v"}


def test_mut4a_s2_loaders_requested_columns_1() -> None:
    """s2_loaders.py:118, return out -> return None (ColumnRequestSpy.requested_columns)."""
    spy = ColumnRequestSpy(_Inner())
    spy.read_parquet("synthetic.parquet", columns=["col_a", "col_b"])
    assert spy.requested_columns == ["col_a", "col_b"]


def test_mut4a_s2_loaders_verify_pinned_blobs_1(monkeypatch) -> None:
    """s2_loaders.py:35, delete if got != want: raise InputVerificationError."""
    import s2_loaders as loaders

    monkeypatch.setattr(loaders, "_git", lambda *_a, **_k: "zzz-not-the-pin")
    with pytest.raises(InputVerificationError, match="pinned input mismatch"):
        verify_pinned_blobs(
            Path("/tmp/sni-mut4a-synthetic"),
            "synthetic-ref",
            manifest={"synthetic.parquet": "aaa-the-pin"},
        )
