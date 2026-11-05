"""S2 input loading: pinned-blob readers with an injectable seam for tests.

HISTORICAL-DESCRIPTIVE lane. The real loader reads bytes ONLY through
`git cat-file blob <input_ref>:<path>` after verifying the pinned blob id from
INPUT_MANIFEST (exit non-zero on any mismatch). Tests inject an in-memory
loader; nothing here ever writes under data/.

A ColumnRequestSpy wraps any loader and records every requested (path, columns)
pair so a test can prove the seal phase never requests a price or volume
column.
"""
from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pandas as pd
import yaml

from s2_seal import INPUT_MANIFEST


class InputVerificationError(RuntimeError):
    """A pinned input blob id did not match the input ref."""


def verify_pinned_blobs(repo_root: Path, input_ref: str,
                        manifest: dict | None = None) -> None:
    """git rev-parse <input_ref>:<path> must equal the pinned blob, else raise."""
    manifest = INPUT_MANIFEST if manifest is None else manifest
    for path, want in manifest.items():
        got = _git(repo_root, "rev-parse", f"{input_ref}:{path}")
        if got != want:
            raise InputVerificationError(
                f"pinned input mismatch for {path}: ref {input_ref} has blob "
                f"{got}, seal pins {want}")


def _git(repo_root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise InputVerificationError(
            f"git {' '.join(args)} failed: {proc.stderr.strip()[:400]}")
    return proc.stdout.strip()


class GitBlobLoader:
    """Reads every input through `git cat-file blob <input_ref>:<path>`."""

    def __init__(self, repo_root: Path, input_ref: str,
                 manifest: dict | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.input_ref = input_ref
        self.manifest = INPUT_MANIFEST if manifest is None else manifest

    # -- raw bytes -------------------------------------------------------- #
    def read_bytes(self, path: str) -> bytes:
        proc = subprocess.run(
            ["git", "-C", str(self.repo_root), "cat-file", "blob",
             f"{self.input_ref}:{path}"],
            capture_output=True,
        )
        if proc.returncode != 0:
            raise InputVerificationError(
                f"cat-file {self.input_ref}:{path} failed: "
                f"{proc.stderr.decode(errors='replace')[:400]}")
        return proc.stdout

    # -- typed readers ---------------------------------------------------- #
    def read_parquet(self, path: str, columns: tuple[str, ...] | None = None) -> pd.DataFrame:
        buf = io.BytesIO(self.read_bytes(path))
        return pd.read_parquet(buf, columns=list(columns) if columns else None)

    def read_yaml(self, path: str) -> dict:
        return yaml.safe_load(self.read_bytes(path).decode("utf-8"))

    def read_json(self, path: str) -> dict:
        return json.loads(self.read_bytes(path).decode("utf-8"))

    def read_text(self, path: str) -> str:
        return self.read_bytes(path).decode("utf-8")


class ColumnRequestSpy:
    """Wraps a loader and records every (path, columns) parquet request."""

    def __init__(self, inner) -> None:
        self.inner = inner
        self.requests: list[tuple[str, tuple[str, ...] | None]] = []

    def read_parquet(self, path: str, columns=None):
        self.requests.append((path, tuple(columns) if columns else None))
        return self.inner.read_parquet(path, columns=columns)

    def read_yaml(self, path: str):
        return self.inner.read_yaml(path)

    def read_json(self, path: str):
        return self.inner.read_json(path)

    def read_text(self, path: str):
        return self.inner.read_text(path)

    def read_bytes(self, path: str) -> bytes:
        return self.inner.read_bytes(path)

    @property
    def requested_columns(self) -> list[str]:
        out: list[str] = []
        for _path, cols in self.requests:
            if cols:
                out.extend(cols)
        return out
