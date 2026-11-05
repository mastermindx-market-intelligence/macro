"""s1_data.py — read-only, pinned-blob data access for the SNI S1 residual lane.

The lane never checks anything out under data/. Every input is read as a git
blob of a pinned commit (`--input-ref`), verified against the sha recorded in
the seal (SEAL_AND_BUDGET.json -> INPUT_MANIFEST.json) before use.

Two access levels, so the outcome-free seal builder can prove it never touched
a price/volume column:

  * `schema(path)`      column names only.
  * `index_dates(path)` the index (Date) column alone, as `datetime.date`.
  * `frame(path, cols)` named columns + the index — used ONLY by the evidence
                        runner, never by build_seal or the manifest builder.

An `access_log` records every call so tests can spy on the loader (D5: the
manifest builder must request no non-index column).
"""
from __future__ import annotations

import subprocess
import tempfile
from datetime import date, datetime
from pathlib import Path

import pyarrow.parquet as pq

INDEX_COLUMN = "Date"


def _to_date(v) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    raise TypeError(f"cannot read {v!r} as a calendar date")


class GitBlobStore:
    """Reads pinned blobs out of a git ref without materialising data/ in the tree."""

    def __init__(self, repo_root: str | Path, input_ref: str, pins: dict[str, str],
                 workdir: str | Path | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.input_ref = input_ref
        self.pins = dict(pins)
        self.access_log: list[tuple] = []
        self._tmp = Path(workdir) if workdir is not None else None
        self._materialised: dict[str, Path] = {}

    # -- git plumbing ------------------------------------------------------ #
    def _git_bytes(self, args: list[str]) -> bytes:
        r = subprocess.run(["git", "-C", str(self.repo_root), *args],
                           capture_output=True)
        if r.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.decode(errors='replace')}")
        return r.stdout

    def _git_text(self, args: list[str]) -> str:
        return self._git_bytes(args).decode()

    def list_dir(self, prefix: str) -> list[str]:
        """Paths directly under `prefix` at the pinned ref (metadata only)."""
        self.access_log.append(("list_dir", prefix))
        out = self._git_text(["ls-tree", "--name-only", self.input_ref, prefix]).splitlines()
        return sorted(line.strip() for line in out if line.strip())

    def rev_parse_ref_path(self, path: str) -> str:
        return self._git_text(["rev-parse", f"{self.input_ref}:{path}"]).strip()

    def commit_date_iso(self, ref: str | None = None) -> str:
        """Committer date (ISO-8601) of a ref — used for deterministic stamps."""
        return self._git_text(["show", "-s", "--format=%cI",
                               ref or self.input_ref]).strip()

    # -- pin verification -------------------------------------------------- #
    def verify_pin(self, path: str) -> str:
        got = self.rev_parse_ref_path(path)
        want = self.pins.get(path)
        if want is None:
            raise RuntimeError(f"no sealed pin for {path}")
        if got != want:
            raise RuntimeError(
                f"PIN MISMATCH for {path}: seal pins {want}, {self.input_ref} has {got}")
        return got

    def verify_all(self) -> None:
        for p in sorted(self.pins):
            self.verify_pin(p)

    # -- blob materialisation ---------------------------------------------- #
    def _blob_file(self, path: str) -> Path:
        if path in self._materialised:
            return self._materialised[path]
        blob = self._git_bytes(["cat-file", "blob", f"{self.input_ref}:{path}"])
        if self._tmp is None:
            self._tmp = Path(tempfile.mkdtemp(prefix="sni_s1_blobs_"))
        out = self._tmp / path.replace("/", "__")
        out.write_bytes(blob)
        self._materialised[path] = out
        return out

    # -- the three access levels ------------------------------------------- #
    def schema(self, path: str) -> list[str]:
        self.access_log.append(("schema", path))
        return list(pq.read_schema(self._blob_file(path)).names)

    def index_dates(self, path: str) -> list[date]:
        """The index column ALONE — never a price/volume value."""
        self.access_log.append(("index_dates", path))
        tbl = pq.read_table(self._blob_file(path), columns=[INDEX_COLUMN])
        return sorted({_to_date(v) for v in tbl.column(INDEX_COLUMN).to_pylist()})

    def frame(self, path: str, columns: list[str]) -> tuple[list[date], dict[str, list[float]]]:
        """Index + the named columns. Evidence phase only."""
        self.access_log.append(("frame", path, tuple(columns)))
        tbl = pq.read_table(self._blob_file(path), columns=[INDEX_COLUMN, *columns])
        dates = [_to_date(v) for v in tbl.column(INDEX_COLUMN).to_pylist()]
        cols = {c: [float(v) for v in tbl.column(c).to_pylist()] for c in columns}
        return dates, cols

    def read_columns(self, path: str, columns: list[str]) -> dict[str, list]:
        """Named columns of a NON-price reference table (no index required).
        Used only for identity metadata (security_master), never prices."""
        self.access_log.append(("read_columns", path, tuple(columns)))
        tbl = pq.read_table(self._blob_file(path), columns=sorted(columns))
        return {c: tbl.column(c).to_pylist() for c in sorted(columns)}


class InjectableStore:
    """Test double with the same three access levels, backed by in-memory frames."""

    input_ref = "SYNTHETIC"          # matches the seal's input_ref in tests

    def __init__(self, frames: dict[str, dict[str, list]], input_ref: str | None = None) -> None:
        # frames[path] = {"Date": [...], "close": [...], ...}
        self.frames = frames
        if input_ref is not None:
            self.input_ref = input_ref
        self.access_log: list[tuple] = []

    def schema(self, path: str) -> list[str]:
        self.access_log.append(("schema", path))
        return list(self.frames[path].keys())

    def list_dir(self, prefix: str) -> list[str]:
        self.access_log.append(("list_dir", prefix))
        return sorted(p for p in self.frames if p.startswith(prefix))

    def index_dates(self, path: str) -> list[date]:
        self.access_log.append(("index_dates", path))
        return sorted({_to_date(v) for v in self.frames[path][INDEX_COLUMN]})

    def frame(self, path: str, columns: list[str]) -> tuple[list[date], dict[str, list[float]]]:
        self.access_log.append(("frame", path, tuple(columns)))
        f = self.frames[path]
        return ([_to_date(v) for v in f[INDEX_COLUMN]],
                {c: [float(v) for v in f[c]] for c in columns})

    def read_columns(self, path: str, columns: list[str]) -> dict[str, list]:
        self.access_log.append(("read_columns", path, tuple(columns)))
        f = self.frames[path]
        return {c: list(f[c]) for c in columns}

    def commit_date_iso(self, ref: str | None = None) -> str:
        """Deterministic stand-in for the BASE commit date."""
        return "1970-01-01T00:00:00+00:00"


class IndexOnlySpy:
    """Wraps a store and exposes ONLY the index/schema surface.

    The manifest builder receives this; a test asserts the builder asked for
    nothing else (D5: membership is built before any outcome, from calendars
    and index dates alone).
    """

    def __init__(self, store) -> None:
        self._store = store
        self.calls: list[str] = []

    def schema(self, path: str) -> list[str]:
        self.calls.append("schema")
        return self._store.schema(path)

    def index_dates(self, path: str) -> list[date]:
        self.calls.append("index_dates")
        return self._store.index_dates(path)

    def list_dir(self, prefix: str) -> list[str]:
        self.calls.append("list_dir")
        return self._store.list_dir(prefix)


def closes_from_frame(dates: list[date], values: list[float]) -> tuple[list[date], dict[date, float]]:
    """Align a column to its index as a date -> float map (drop nulls)."""
    out: dict[date, float] = {}
    for d, v in zip(dates, values):
        if v is None:
            continue
        fv = float(v)
        if fv != fv:  # NaN
            continue
        out[d] = fv
    return dates, out
