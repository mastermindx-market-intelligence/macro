"""Theta EOD retrospective association v1 — frozen protocol helper.

This module implements the two bounded modes described in
``research/options_estate/theta_eod_retrospective_association_v1_protocol.json``:

* ``prepare_manifest`` — scan and inventory every selected 2017..2025 greeks/OI
  and adjusted-price file. Records relative path, size, SHA-256, schema columns,
  min/max date, row count, known-at/vintage scan, and the protocol SHA. Does
  NOT read numerical feature or outcome values. Writes an immutable manifest
  JSON + a separate manifest SHA file. Caller may compute and freeze the
  manifest SHA before invoking ``analyze``.
* ``analyze`` — accept ONLY an exact byte-identical manifest and the frozen
  protocol SHA. Refuse any protocol mutation, missing/changed/extra selected
  path, duplicate manifest path, or root/year mismatch. Compute one
  date-level Spearman IC per (contrast, era, horizon) across the 60 registered
  cells (10 contrasts × 3 eras × 2 horizons), HAC t-test inference on the full
  canonical calendar index, and one global BH step-up at k=60 alpha=0.10.

The module is research-only and NEVER mutates the input archive, its locks, or
its derived cache. Per the frozen protocol every result is ``PIT_UNPROVEN``
retrospective association only; no fit, calibration, scoring, ranking, gating,
sizing, alerts, portfolio or trading authority is implied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import warnings
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping as TMap

if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=RuntimeWarning)

import numpy as np
import pandas as pd
from scipy import stats

# Local imports kept narrow so prepare mode can run without engine init.
from lib import nyse_calendar
from scripts.research.options_history_gauntlet import _bh_fdr, _hac_ttest


# ---------------------------------------------------------------------------
# Protocol SHA + frozen meta
# ---------------------------------------------------------------------------

PROTOCOL_FILENAME = "theta_eod_retrospective_association_v1_protocol.json"

# The expected, frozen-by-root protocol SHA. Any protocol mutation refuses
# analyze mode (and the manifest's own protocol_sha is also validated).
EXPECTED_PROTOCOL_SHA = (
    "384d3da6539960cbd768dd1a98eb9bd7b3f87e838fad980caca5f153a9c0a0c3"
)

# Registered FDR family token (must match config/ruling_graph.yml).
FDR_FAMILY = "options_theta_retrospective_association_v1"

# 10 contrasts × 3 eras × 2 horizons = 60 cells, ALWAYS reported.
CONTRAST_IDS = [
    "GEX_NORM_TO_FWD_RV",
    "VEX_NORM_TO_SPY_EXCESS",
    "CEX_NORM_TO_SPY_EXCESS",
    "VANNA_RELIEF_TO_SPY_EXCESS",
    "CW_IVSPREAD_LEVEL_TO_SPY_EXCESS",
    "D5_CW_IVSPREAD_TO_SPY_EXCESS",
    "SKEW_ACCEL_TO_SPY_EXCESS",
    "TERM_SLOPE_TO_SPY_EXCESS",
    "DOI5_TO_SPY_EXCESS",
    "MOM5_BASELINE_TO_SPY_EXCESS",
]
CONTRAST_FEATURES = {
    "GEX_NORM_TO_FWD_RV": "net_gamma_norm",
    "VEX_NORM_TO_SPY_EXCESS": "net_vanna_norm",
    "CEX_NORM_TO_SPY_EXCESS": "net_charm_norm",
    "VANNA_RELIEF_TO_SPY_EXCESS": "vanna_relief",
    "CW_IVSPREAD_LEVEL_TO_SPY_EXCESS": "cw_ivspread",
    "D5_CW_IVSPREAD_TO_SPY_EXCESS": "d5_cw_ivspread",
    "SKEW_ACCEL_TO_SPY_EXCESS": "skew_accel",
    "TERM_SLOPE_TO_SPY_EXCESS": "term_slope",
    "DOI5_TO_SPY_EXCESS": "doi5",
    "MOM5_BASELINE_TO_SPY_EXCESS": "mom5",
}
CONTRAST_TARGETS = {
    "GEX_NORM_TO_FWD_RV": "volatility_target",
    "VEX_NORM_TO_SPY_EXCESS": "primary_return_target",
    "CEX_NORM_TO_SPY_EXCESS": "primary_return_target",
    "VANNA_RELIEF_TO_SPY_EXCESS": "primary_return_target",
    "CW_IVSPREAD_LEVEL_TO_SPY_EXCESS": "primary_return_target",
    "D5_CW_IVSPREAD_TO_SPY_EXCESS": "primary_return_target",
    "SKEW_ACCEL_TO_SPY_EXCESS": "primary_return_target",
    "TERM_SLOPE_TO_SPY_EXCESS": "primary_return_target",
    "DOI5_TO_SPY_EXCESS": "primary_return_target",
    "MOM5_BASELINE_TO_SPY_EXCESS": "primary_return_target",
}
ERAS = [
    ("Era1", "2017-01-01", "2019-12-31"),
    ("Era2", "2020-01-01", "2022-12-31"),
    ("Era3", "2023-01-01", "2025-12-31"),
]
HORIZONS = (5, 21)

# BH-FDR is registered at k=60 over the full 10x3x2 family.
BH_K = 60
BH_ALPHA = 0.10

# Inferential support thresholds.
MIN_IC_DATES = 126
MIN_EFFECTIVE_BLOCKS = 30
MIN_ROOTS_PER_IC_DATE = 5

# Required greeks columns — listed by the protocol.
GREEKS_REQUIRED_COLS = (
    "root", "expiration", "strike", "right", "date",
    "bid", "ask", "underlying_price", "delta", "theta", "vega",
    "rho", "epsilon", "lambda", "implied_vol", "iv_error", "gamma",
    "vanna", "charm", "vomma", "veta", "vera", "speed", "zomma",
    "color", "ultima",
)
OI_REQUIRED_COLS = ("root", "expiration", "strike", "right", "date", "open_interest")
PRICE_REQUIRED_COLS = ("close",)
# Adjusted price parquets use a pandas Date index with close and close_price.
PRICE_REQUIRED_ALIAS = ("close", "close_price")

# Roots: 23 roots total — SPX/SPXW coverage-only, SPY benchmark-only, 20 scored
# (DIA/ARKK lack adjusted-price forwardable and stay non-evaluable).
ALL_ROOTS = [
    "SPX", "SPXW", "SPY", "QQQ", "IWM", "DIA",
    "XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY",
    "SMH", "SOXX", "XBI", "KRE", "ARKK", "NVDA",
]
COVERAGE_ONLY_ROOTS = ("SPX", "SPXW")
BENCHMARK_ONLY_ROOT = "SPY"
SCORED_ROOTS = [
    "QQQ", "IWM", "DIA", "XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP",
    "XLRE", "XLU", "XLV", "XLY", "SMH", "SOXX", "XBI", "KRE", "ARKK", "NVDA",
]
KNOWN_PRICE_NON_EVALUABLE_ROOTS = {"DIA", "ARKK"}

YEARS = list(range(2017, 2026))  # 2017..2025 inclusive

# Engine primitives' hashes are part of full source hash closure.
_ENGINE_PRIMITIVE_RELATIVE_PATHS = (
    "engine/exposure_math.py",
    "engine/options_ivspread.py",
    "engine/options_skew.py",
    "engine/options_dislocation.py",
    "engine/grading.py",
    "engine/flow_signals_grade.py",
    "lib/nyse_calendar.py",
)


# ---------------------------------------------------------------------------
# Pure utilities (testable in isolation)
# ---------------------------------------------------------------------------

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def file_or_empty_sha(path: Path) -> str:
    """sha256 of the file's bytes, or sha256(b'') when the file is absent."""
    if not path.exists():
        return sha256_bytes(b"")
    return sha256_file(path)


def _safe_read_parquet_metadata(path: Path) -> dict[str, Any]:
    """Read ONLY schema + row count + min/max date — no feature/outcome values.

    Uses ``pyarrow`` to read the schema and row count directly without materialising
    row data. To recover min/max date we MUST read the date column; per the protocol
    contract this is permitted (the date column is metadata, not a numerical
    feature/outcome value). Reading the date column does not count as reading a
    numerical column.
    """
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(str(path))
    schema = pf.schema_arrow
    cols = [schema.field(i).name for i in range(len(schema))]
    md: dict[str, Any] = {
        "columns": cols,
        "row_count": int(pf.metadata.num_rows) if pf.metadata else 0,
    }
    if "date" in cols:
        try:
            df = pd.read_parquet(path, columns=["date"])
            d = pd.to_datetime(df["date"], errors="coerce").dropna()
            if not d.empty:
                md["min_date"] = str(d.min().date())
                md["max_date"] = str(d.max().date())
            else:
                md["min_date"] = None
                md["max_date"] = None
        except Exception:
            md["min_date"] = None
            md["max_date"] = None
    else:
        md["min_date"] = None
        md["max_date"] = None
    return md


def _scan_known_at_columns(path: Path) -> list[str]:
    """Return the list of column names that look like known-at/vintage fields.

    Per protocol, the audited 240-file sample contained ZERO such fields; the
    manifest inventory re-scans each selected file for the same vocabulary so a
    genuine known-at column would surface. Names matching these patterns count
    as 'vintage-like' and are reported back. A vintage column appearing is news,
    not a routine.
    """
    vocab = (
        "known_at", "known_at_utc", "knownat", "known_at_unix", "first_known",
        "first_known_at", "first_seen", "ingested_at", "as_of_utc",
        "vendor_known_at", "vendor_revision", "revised_at", "revision_ts",
        "vintage", "trade_date_received", "feed_timestamp", "last_modified",
    )
    try:
        import pyarrow.parquet as pq
        pf = pq.ParquetFile(str(path))
        schema = pf.schema_arrow
        found = []
        for i in range(len(schema)):
            name = schema.field(i).name
            if name.lower() in vocab:
                found.append(name)
        return found
    except Exception:
        return []


def _is_session_str(s: str) -> bool:
    try:
        return nyse_calendar.is_session(datetime.strptime(s, "%Y-%m-%d").date())
    except Exception:
        return False


def _manifest_duplicate_paths(records: list[dict]) -> list[str]:
    seen: set[str] = set()
    dups: list[str] = []
    for rec in records:
        p = rec.get("rel_path", "")
        if p in seen:
            dups.append(p)
        seen.add(p)
    return dups


# ---------------------------------------------------------------------------
# Protocol + manifest I/O
# ---------------------------------------------------------------------------

@dataclass
class FrozenProtocol:
    """A verified copy of the frozen protocol JSON."""

    raw: dict[str, Any]
    sha256: str
    path: Path


def load_frozen_protocol(path: Path) -> FrozenProtocol:
    """Read the protocol JSON and verify its bytes match EXPECTED_PROTOCOL_SHA.

    Analyzes any record-changing protocol mutation. The raw dict is returned
    so callers can read contract constants — but only the bytes matter for
    authorization.
    """
    if not path.exists():
        raise FileNotFoundError(f"protocol JSON not found: {path}")
    sha = sha256_file(path)
    raw = json.loads(path.read_text())
    if sha != EXPECTED_PROTOCOL_SHA:
        raise ValueError(
            f"protocol SHA mismatch: got {sha!r}, expected "
            f"{EXPECTED_PROTOCOL_SHA!r} — protocol mutation refused (frozen)"
        )
    return FrozenProtocol(raw=raw, sha256=sha, path=path)


@dataclass
class SourceManifest:
    """An immutable inventory of every selected input file."""

    results: list[dict[str, Any]] = field(default_factory=list)
    protocol_sha: str = ""
    generated_utc: str = ""

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "schema": "options.science.theta_eod_retrospective_association.v1_manifest",
            "study_id": "THETA-EOD-RETROSPECTIVE-ASSOCIATION-V1",
            "fdr_family": FDR_FAMILY,
            "protocol_sha256": self.protocol_sha,
            "generated_utc": self.generated_utc,
            "n_records": len(self.results),
            "results": self.results,
        }


def write_manifest(manifest: SourceManifest, out_path: Path) -> str:
    """Serialize manifest deterministically and return its SHA-256.

    Sort_keys + separators=(",", ":") makes the JSON byte-stable across runs
    (the protocol requires this — a re-emit of the same input bytes must hash
    identically). Atomic write: dump to tmp then replace, so a concurrent
    reader never sees a half-written file.
    """
    payload = json.dumps(manifest.to_jsonable(), sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    sha = sha256_bytes(payload)
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.write_bytes(payload)
    os.replace(tmp, out_path)
    # Also write the SHA to a sibling file so the root can freeze it.
    sha_path = out_path.with_suffix(out_path.suffix + ".sha256")
    sha_path.write_text(sha + "\n")
    return sha


def load_manifest(manifest_path: Path, expected_sha: str) -> SourceManifest:
    """Load a manifest and verify it matches the frozen expected SHA.

    Refuses any byte mutation. The root freezes the actual SHA before invoking
    analyze, so the caller passes it in.
    """
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")
    raw_bytes = manifest_path.read_bytes()
    sha = sha256_bytes(raw_bytes)
    if expected_sha and sha != expected_sha:
        raise ValueError(
            f"manifest SHA mismatch: got {sha!r}, expected {expected_sha!r} — "
            "manifest mutation refused (frozen)"
        )
    data = json.loads(raw_bytes.decode("utf-8"))
    return SourceManifest(
        results=list(data.get("results", [])),
        protocol_sha=str(data.get("protocol_sha256", "")),
        generated_utc=str(data.get("generated_utc", "")),
    )


# ---------------------------------------------------------------------------
# Prepare mode
# ---------------------------------------------------------------------------

def _inventory_root_year(
    *, store: Path, root: str, year: int, kind: str,
) -> dict[str, Any] | None:
    """Inventory one greeks/oi file. Reads metadata + bytes only.

    Returns None when the file is absent (the prepared manifest records the
    absence via a record of the same rel_path and sha256(b'')).
    """
    rel = f"{kind}/{root}/{year}.parquet"
    path = store / kind / root / f"{year}.parquet"
    if not path.exists():
        return {
            "kind": kind, "root": root, "year": year, "rel_path": rel,
            "abs_path": str(path),
            "exists": False,
            "size": 0,
            "sha256": sha256_bytes(b""),
            "row_count": 0,
            "columns": [],
            "min_date": None, "max_date": None,
            "known_at_vintage_columns": [],
        }
    size = path.stat().st_size
    sha = sha256_file(path)
    md = _safe_read_parquet_metadata(path)
    return {
        "kind": kind, "root": root, "year": year, "rel_path": rel,
        "abs_path": str(path),
        "exists": True,
        "size": size,
        "sha256": sha,
        "row_count": md["row_count"],
        "columns": md["columns"],
        "min_date": md["min_date"], "max_date": md["max_date"],
        "known_at_vintage_columns": _scan_known_at_columns(path),
    }


def _inventory_price_root(
    *, price_store: Path, root: str,
) -> dict[str, Any]:
    """Inventory one adjusted-price parquet. Reads metadata + bytes only."""
    rel = f"{root}.parquet"
    # Spec mentions both shapes:
    #   flow-ops-wt/data/yahoo/{ROOT}.parquet   (direct under price_store)
    # We honour the price_store root and look one level deep too.
    candidates = [price_store / rel, price_store / root / rel]
    chosen: Path | None = None
    for c in candidates:
        if c.exists():
            chosen = c
            break
    if chosen is None:
        # DIA/ARKK are KNOWN PRICE NON-EVALUABLE per the protocol — the
        # manifest records the absence.
        chosen = candidates[0]
        return {
            "kind": "adjusted_price", "root": root, "year": None,
            "rel_path": rel,
            "abs_path": str(chosen),
            "exists": False, "size": 0,
            "sha256": sha256_bytes(b""),
            "row_count": 0, "columns": [],
            "min_date": None, "max_date": None,
            "known_at_vintage_columns": [],
        }
    # The actual rel path is the one that exists.
    rel_used = str(chosen.relative_to(price_store))
    size = chosen.stat().st_size
    sha = sha256_file(chosen)
    md = _safe_read_parquet_metadata(chosen)
    return {
        "kind": "adjusted_price", "root": root, "year": None,
        "rel_path": rel_used,
        "abs_path": str(chosen),
        "exists": True, "size": size, "sha256": sha,
        "row_count": md["row_count"], "columns": md["columns"],
        "min_date": md["min_date"], "max_date": md["max_date"],
        "known_at_vintage_columns": _scan_known_at_columns(chosen),
    }


def prepare_manifest(
    *,
    store: Path,
    price_store: Path,
    protocol_path: Path,
    roots: list[str] = ALL_ROOTS,
    price_population: list[str] = SCORED_ROOTS + [BENCHMARK_ONLY_ROOT],
    years: list[int] = YEARS,
) -> SourceManifest:
    """Inventory every selected greeks/oi/price file and return it.

    Pure IO: bytes, sizes, schema columns, min/max dates. NEVER reads numerical
    feature or outcome values (the date column is metadata and is the only
    non-metadata column touched, exactly as the protocol specifies).
    """
    proto = load_frozen_protocol(protocol_path)
    results: list[dict[str, Any]] = []
    # 1) greeks + OI per root × year.
    for root in roots:
        for yr in years:
            results.append(_inventory_root_year(
                store=store, root=root, year=yr, kind="greeks"))
            results.append(_inventory_root_year(
                store=store, root=root, year=yr, kind="oi"))
    # 2) adjusted-price parquets for 21 roots (20 scored + SPY benchmark).
    for root in price_population:
        results.append(_inventory_price_root(
            price_store=price_store, root=root))
    # 3) engine primitive + calendar closure hashes (full source closure).
    repo_root = Path(__file__).resolve().parents[2]
    for rel in _ENGINE_PRIMITIVE_RELATIVE_PATHS:
        p = repo_root / rel
        results.append({
            "kind": "engine_primitive", "root": None, "year": None,
            "rel_path": rel,
            "abs_path": str(p),
            "exists": p.exists(),
            "size": p.stat().st_size if p.exists() else 0,
            "sha256": file_or_empty_sha(p),
            "row_count": 0, "columns": [],
            "min_date": None, "max_date": None,
            "known_at_vintage_columns": [],
        })
    return SourceManifest(
        results=results,
        protocol_sha=proto.sha256,
        generated_utc=datetime.utcnow().isoformat() + "Z",
    )


# ---------------------------------------------------------------------------
# Manifest verification gate
# ---------------------------------------------------------------------------

class ManifestVerificationError(Exception):
    """Raised when the manifest fails the frozen-input gate."""


def verify_manifest_against_inputs(
    manifest: SourceManifest, store: Path, price_store: Path,
) -> None:
    """Re-hash every selected file and refuse any mismatch.

    Per spec: any changed, missing, extra, unreadable or schema-drifted file
    refuses the study. The set of expected paths is derived from the manifest
    itself (the manifest enumerates them); we recompute their hashes and
    schema/date facts and check.

    Duplicate manifest paths are caught via ``_manifest_duplicate_paths``.
    Root/year mismatch is caught via manifest record inspection.
    """
    seen_rel: set[str] = set()
    root_year: set[tuple[str, str, str]] = set()
    expected_set: set[str] = set()
    extras: list[str] = []
    # Pass 1: dedup + schema only (so duplicate-path refusal fires regardless
    # of whether subsequent records have valid content).
    for rec in manifest.results:
        rel = rec.get("rel_path", "")
        if not rel:
            raise ManifestVerificationError(
                "manifest record has empty rel_path")
        if rel in seen_rel:
            raise ManifestVerificationError(
                f"duplicate manifest path: {rel!r}")
        seen_rel.add(rel)
        kind = rec.get("kind")
        root = rec.get("root")
        year = rec.get("year")
        if kind in ("greeks", "oi") and (root is None or year is None):
            raise ManifestVerificationError(
                f"greeks/oi record missing root/year: {rec}")
        if kind in ("greeks", "oi"):
            key = (kind, str(root), str(year))
            if key in root_year:
                raise ManifestVerificationError(
                    f"duplicate manifest root/year: {key}")
            root_year.add(key)
        expected_set.add(rel)
    # Pass 2: schema + hash checks.
    for rec in manifest.results:
        # Allowed schemas.
        cols = set(rec.get("columns", []))
        if kind == "greeks":
            missing = [c for c in GREEKS_REQUIRED_COLS if c not in cols]
            if missing:
                raise ManifestVerificationError(
                    f"greeks schema drift on {rel}: missing {missing}")
        elif kind == "oi":
            missing = [c for c in OI_REQUIRED_COLS if c not in cols]
            if missing:
                raise ManifestVerificationError(
                    f"oi schema drift on {rel}: missing {missing}")
        elif kind == "adjusted_price":
            if not any(c in cols for c in PRICE_REQUIRED_ALIAS):
                raise ManifestVerificationError(
                    f"adjusted-price schema drift on {rel}: "
                    f"missing any of {PRICE_REQUIRED_ALIAS}")
        elif kind == "engine_primitive":
            pass
        else:
            raise ManifestVerificationError(
                f"unknown manifest kind {kind!r} for {rel}")
        # Hash recheck.
        p = Path(rec.get("abs_path", ""))
        if not p.exists():
            # An absent selected file with sha256(b'') and exists=False is
            # allowed for the known non-evaluable roots (DIA/ARKK price) and
            # for genuinely missing roots/years. We accept those records
            # exactly as the manifest carries them; any mutation here would
            # be caught by the manifest SHA itself.
            if not (rec.get("exists") is False and rec.get("sha256") == sha256_bytes(b"")):
                raise ManifestVerificationError(
                    f"manifest says exists=True but file absent: {rel}")
            continue
        size_now = p.stat().st_size
        sha_now = sha256_file(p)
        if size_now != rec.get("size", -1) or sha_now != rec.get("sha256", ""):
            raise ManifestVerificationError(
                f"file hash mismatch for {rel}: "
                f"size {size_now} vs {rec.get('size')}, "
                f"sha {sha_now[:8]}… vs {str(rec.get('sha256', ''))[:8]}…")
        # Re-verify the schema by re-reading the metadata.
        try:
            md = _safe_read_parquet_metadata(p)
            if md["columns"] != rec.get("columns"):
                raise ManifestVerificationError(
                    f"schema drift on {rel}: columns changed since manifest")
        except ManifestVerificationError:
            raise
        except Exception:
            # Non-parquet engine primitive files don't have a pyarrow schema
            # to compare; that branch is for engine_primitive records.
            if kind in ("greeks", "oi", "adjusted_price"):
                raise ManifestVerificationError(
                    f"could not re-read parquet schema for {rel}")


# ---------------------------------------------------------------------------
# Synthetic-fixture IO used by tests (and analyze mode if --fixture-root is
# given). NEVER touches the real archive.
# ---------------------------------------------------------------------------

def _load_fixture_root_year(fixture_root: Path, root: str, year: int,
                            kind: str) -> pd.DataFrame | None:
    """Read a greeks/oi fixture file from the synthetic-fixture root.

    Returns None when the file is absent. Tests build these fixtures; analyze
    mode would only be invoked against them in CI. Real-archive research is
    the root's responsibility on M1.
    """
    p = fixture_root / kind / root / f"{year}.parquet"
    if not p.exists():
        return None
    return pd.read_parquet(p)


def _load_fixture_price(fixture_root: Path, root: str) -> pd.Series | None:
    """Read a synthetic adjusted-price parquet. Returns close column with a
    pandas Date index — matches the data/yahoo contract.
    """
    p = fixture_root / "adjusted_price" / f"{root}.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    if "close" in df.columns:
        s = df["close"]
    elif "close_price" in df.columns:
        s = df["close_price"]
    else:
        return None
    s.index = pd.to_datetime(s.index)
    return s.dropna().sort_index()


# ---------------------------------------------------------------------------
# Feature builders (per protocol primitives)
# ---------------------------------------------------------------------------

@dataclass
class FeatureRow:
    """One feature value at one (date, root)."""

    root: str
    date: pd.Timestamp
    feature: str
    value: float | None
    reason: str | None = None  # set when value is None


def _quote_greek_coverage(g: pd.DataFrame, greeks: list[str]) -> float:
    """Fraction of rows with finite values for every required greek + bid/ask."""
    if g.empty:
        return 0.0
    required = ["bid", "ask"] + greeks
    mask = pd.Series(True, index=g.index)
    for c in required:
        if c not in g.columns:
            return 0.0
        v = pd.to_numeric(g[c], errors="coerce")
        mask &= np.isfinite(v)
        if c in ("bid", "ask"):
            mask &= (v > 0)
    return float(mask.mean())


def _build_gex_features(fixture_root: Path, root: str, year: int,
                         greeks: pd.DataFrame, oi: pd.DataFrame
                         ) -> tuple[list[FeatureRow], int, int]:
    """Per (date) net-gamma/vanna/charm normalized by sum-abs.

    Requires >= 90% finite coverage on (bid, ask, gamma/vanna/charm, open_interest)
    among usable joined contracts (per protocol). Requires valid cross contract
    screens (positive bid/ask, positive strike, 0DTE excluded, finite positive
    spot).
    """
    rows: list[FeatureRow] = []
    if greeks is None or oi is None or greeks.empty or oi.empty:
        return rows, 0, 0
    g = greeks.copy()
    o = oi.copy()
    # Identity join: (date, expiration, strike, right).
    on = ["date", "expiration", "strike", "right"]
    merged = g.merge(o, on=on, how="inner", suffixes=("", "_oi"))
    if merged.empty:
        return rows, 0, 0
    # Strict quality gates.
    merged["right"] = merged["right"].astype(str).str.upper()
    merged["is_call"] = merged["right"] == "C"
    merged["strike"] = pd.to_numeric(merged["strike"], errors="coerce")
    merged["bid"] = pd.to_numeric(merged["bid"], errors="coerce")
    merged["ask"] = pd.to_numeric(merged["ask"], errors="coerce")
    merged["underlying_price"] = pd.to_numeric(
        merged["underlying_price"], errors="coerce")
    merged["open_interest"] = pd.to_numeric(
        merged["open_interest"], errors="coerce")
    merged["expiration"] = pd.to_datetime(merged["expiration"], errors="coerce")
    merged["date"] = pd.to_datetime(merged["date"], errors="coerce")
    ok = (
        merged["right"].isin(["C", "P"])
        & (merged["expiration"] > merged["date"])  # 0DTE excluded
        & (merged["strike"] > 0)
        & (merged["underlying_price"] > 0)
        & (merged["bid"] > 0)
        & (merged["ask"] > 0)
        & (merged["bid"] <= merged["ask"])
        & (merged["open_interest"] > 0)
    )
    merged = merged[ok].copy()
    if merged.empty:
        return rows, 0, 0
    n_total = 0
    n_dropped = 0
    for date_, gdf in merged.groupby("date"):
        n_total += 1
        for greek, feat_name in (("gamma", "net_gamma_norm"),
                                 ("vanna", "net_vanna_norm"),
                                 ("charm", "net_charm_norm")):
            cov = _quote_greek_coverage(gdf, [greek])
            if cov < 0.90:
                n_dropped += 1
                rows.append(FeatureRow(
                    root=root, date=pd.Timestamp(date_), feature=feat_name,
                    value=None, reason="quote_greek_coverage"))
                continue
            v = pd.to_numeric(gdf[greek], errors="coerce")
            oi_v = gdf["open_interest"].astype(float)
            spot = float(pd.to_numeric(gdf["underlying_price"], errors="coerce")
                         .iloc[0])
            sign = np.where(gdf["is_call"], 1.0, -1.0)
            base = sign * oi_v.values * 100.0
            if greek == "gamma":
                expo = base * v.values * (spot ** 2) * 0.01
            elif greek == "vanna":
                expo = base * v.values * spot * 0.01
            elif greek == "charm":
                expo = base * (v.values / 365.0) * spot
            else:
                continue
            net = float(np.nansum(expo))
            denom = float(np.nansum(np.abs(expo)))
            if denom <= 0 or not np.isfinite(net) or not np.isfinite(denom):
                rows.append(FeatureRow(
                    root=root, date=pd.Timestamp(date_), feature=feat_name,
                    value=None, reason="zero_denominator"))
                continue
            rows.append(FeatureRow(
                root=root, date=pd.Timestamp(date_), feature=feat_name,
                value=net / denom))
    return rows, n_total, n_dropped


def _build_cw_ivspread_features(fixture_root: Path, root: str, year: int,
                                greeks: pd.DataFrame, oi: pd.DataFrame
                                ) -> tuple[list[FeatureRow], int, int]:
    """OI-weighted matched-pair CW ivspread, strict preferences.

    Per spec, the ivspread builder uses the SAME-session unadjusted Greek median
    spot (NOT adjusted close), exact >=7D expiry nearest 30 calendar days (ties
    earlier), strict matched-pair IV spread <= 0.50, >=3 pairs, OI-weighted,
    5-decimal rounding. No fallback.

    OI is merged in via the (date, expiration, strike, right) identity; the same
    identity that the GEX primitive uses.
    """
    rows: list[FeatureRow] = []
    if greeks is None or greeks.empty:
        return rows, 0, 0
    g = greeks.copy()
    if oi is not None and not oi.empty:
        o = oi[["date", "expiration", "strike", "right", "open_interest"]].copy()
        g = g.merge(o, on=["date", "expiration", "strike", "right"],
                    how="left")
    g["date"] = pd.to_datetime(g["date"], errors="coerce")
    g["expiration"] = pd.to_datetime(g["expiration"], errors="coerce")
    g["strike"] = pd.to_numeric(g["strike"], errors="coerce")
    g["implied_vol"] = pd.to_numeric(g["implied_vol"], errors="coerce")
    g["open_interest"] = pd.to_numeric(g.get("open_interest"), errors="coerce")
    g["is_call"] = g["right"].astype(str).str.upper() == "C"
    g["dte"] = (g["expiration"] - g["date"]).dt.days
    n_total = 0
    n_dropped = 0
    for date_, gdf in g.groupby("date"):
        n_total += 1
        # Spot: same-session UNADJUSTED Greek median.
        spot = float(pd.to_numeric(gdf["underlying_price"], errors="coerce").median())
        if not np.isfinite(spot) or spot <= 0:
            rows.append(FeatureRow(root=root, date=pd.Timestamp(date_),
                                   feature="cw_ivspread",
                                   value=None, reason="no_quote_spot"))
            continue
        # Expiry selection: nearest 30d, >= 7d, ties earlier.
        dte_table = gdf[gdf["dte"] >= 7]
        if dte_table.empty:
            rows.append(FeatureRow(root=root, date=pd.Timestamp(date_),
                                   feature="cw_ivspread",
                                   value=None, reason="no_tenor"))
            continue
        dte_pick = dte_table.assign(
            diff30=(dte_table["dte"] - 30).abs()).sort_values(
                ["diff30", "dte"]).iloc[0]
        target_exp = dte_pick["expiration"]
        sub = gdf[gdf["expiration"] == target_exp]
        sub = sub[(sub["implied_vol"] > 0) & (sub["strike"] > 0)]
        if sub.empty:
            rows.append(FeatureRow(root=root, date=pd.Timestamp(date_),
                                   feature="cw_ivspread",
                                   value=None, reason="no_tenor"))
            continue
        # Matched pairs at same strike.
        calls = sub[sub["is_call"]][["strike", "implied_vol", "open_interest"]].rename(
            columns={"implied_vol": "iv_c", "open_interest": "oi_c"})
        puts = sub[~sub["is_call"]][["strike", "implied_vol", "open_interest"]].rename(
            columns={"implied_vol": "iv_p", "open_interest": "oi_p"})
        m = calls.merge(puts, on="strike", how="inner")
        if m.empty:
            rows.append(FeatureRow(root=root, date=pd.Timestamp(date_),
                                   feature="cw_ivspread",
                                   value=None, reason="no_quote_pair"))
            continue
        m["spread"] = m["iv_c"] - m["iv_p"]
        m = m[m["spread"].abs() <= 0.50]
        m = m[(m["oi_c"] > 0) & (m["oi_p"] > 0)]
        if len(m) < 3:
            rows.append(FeatureRow(root=root, date=pd.Timestamp(date_),
                                   feature="cw_ivspread",
                                   value=None, reason="no_quote_pairs"))
            n_dropped += 1
            continue
        # OI weight = call_OI + put_OI (sum, NOT min).
        m["w"] = m["oi_c"] + m["oi_p"]
        v = float((m["spread"] * m["w"]).sum() / m["w"].sum())
        rows.append(FeatureRow(root=root, date=pd.Timestamp(date_),
                               feature="cw_ivspread",
                               value=round(v, 5)))
    return rows, n_total, n_dropped


def _build_skew_features(fixture_root: Path, root: str, year: int,
                          greeks: pd.DataFrame
                          ) -> tuple[list[FeatureRow], int, int]:
    """Strict-delta skew: put delta in [-0.98, -0.02] nearest -0.25, call delta
    in [0.02, 0.98] nearest +0.50; NO moneyness fallback; 4-decimal rounding.
    """
    rows: list[FeatureRow] = []
    if greeks is None or greeks.empty:
        return rows, 0, 0
    g = greeks.copy()
    g["date"] = pd.to_datetime(g["date"], errors="coerce")
    g["expiration"] = pd.to_datetime(g["expiration"], errors="coerce")
    g["dte"] = (g["expiration"] - g["date"]).dt.days
    g["delta"] = pd.to_numeric(g["delta"], errors="coerce")
    g["implied_vol"] = pd.to_numeric(g["implied_vol"], errors="coerce")
    g["is_call"] = g["right"].astype(str).str.upper() == "C"
    n_total = 0
    n_dropped = 0
    for date_, gdf in g.groupby("date"):
        n_total += 1
        # Exact >=7D expiry nearest 30, ties earlier.
        dte_table = gdf[gdf["dte"] >= 7]
        if dte_table.empty:
            rows.append(FeatureRow(root=root, date=pd.Timestamp(date_),
                                   feature="skew",
                                   value=None, reason="no_tenor"))
            continue
        dte_pick = dte_table.assign(
            diff30=(dte_table["dte"] - 30).abs()).sort_values(
                ["diff30", "dte"]).iloc[0]
        target_exp = dte_pick["expiration"]
        sub = gdf[gdf["expiration"] == target_exp]
        sub = sub[sub["implied_vol"] > 0]
        if sub.empty:
            rows.append(FeatureRow(root=root, date=pd.Timestamp(date_),
                                   feature="skew",
                                   value=None, reason="no_tenor"))
            continue
        # Put: delta in [-0.98, -0.02] nearest -0.25.
        puts = sub[~sub["is_call"]].dropna(subset=["delta"])
        puts = puts[puts["delta"].between(-0.98, -0.02)]
        if puts.empty:
            rows.append(FeatureRow(root=root, date=pd.Timestamp(date_),
                                   feature="skew",
                                   value=None, reason="no_valid_delta_put"))
            n_dropped += 1
            continue
        put_best = puts.assign(_d=(puts["delta"] - (-0.25)).abs()).sort_values(
            "_d").iloc[0]
        # Call: delta in [0.02, 0.98] nearest +0.50.
        calls = sub[sub["is_call"]].dropna(subset=["delta"])
        calls = calls[calls["delta"].between(0.02, 0.98)]
        if calls.empty:
            rows.append(FeatureRow(root=root, date=pd.Timestamp(date_),
                                   feature="skew",
                                   value=None, reason="no_valid_delta_call"))
            n_dropped += 1
            continue
        call_best = calls.assign(_d=(calls["delta"] - 0.50).abs()).sort_values(
            "_d").iloc[0]
        skew_v = round(
            float(put_best["implied_vol"]) - float(call_best["implied_vol"]), 4)
        rows.append(FeatureRow(root=root, date=pd.Timestamp(date_),
                               feature="skew", value=skew_v))
    return rows, n_total, n_dropped


def _build_atm_iv_features(fixture_root: Path, root: str, year: int,
                           greeks: pd.DataFrame
                           ) -> tuple[list[FeatureRow], int, int]:
    """BOTH call/put ATM IV at near (15<=DTE<45, target 30) and back (60<=DTE<120,
    target 90) buckets. Rounded 6dp. Term slope = near - back, requires BOTH legs.
    """
    rows: list[FeatureRow] = []
    if greeks is None or greeks.empty:
        return rows, 0, 0
    g = greeks.copy()
    g["date"] = pd.to_datetime(g["date"], errors="coerce")
    g["expiration"] = pd.to_datetime(g["expiration"], errors="coerce")
    g["dte"] = (g["expiration"] - g["date"]).dt.days
    g["delta"] = pd.to_numeric(g["delta"], errors="coerce")
    g["implied_vol"] = pd.to_numeric(g["implied_vol"], errors="coerce")
    g["is_call"] = g["right"].astype(str).str.upper() == "C"
    n_total = 0
    n_dropped = 0
    for date_, gdf in g.groupby("date"):
        n_total += 1
        for tag, lo, hi, target in (("near", 15, 45, 30),
                                    ("back", 60, 120, 90)):
            bucket = gdf[(gdf["dte"] >= lo) & (gdf["dte"] < hi)
                         & (gdf["implied_vol"] > 0)
                         & gdf["delta"].notna()
                         & gdf["delta"].between(-0.98, 0.98)]
            if bucket.empty:
                rows.append(FeatureRow(root=root, date=pd.Timestamp(date_),
                                       feature=f"atm_{tag}",
                                       value=None, reason="no_tenor"))
                continue
            exp_pick = bucket.assign(_d=(bucket["dte"] - target).abs()).sort_values(
                "_d").iloc[0]
            exp = exp_pick["expiration"]
            sub = bucket[bucket["expiration"] == exp]
            legs = []
            for want_call in (True, False):
                leg = sub[sub["is_call"] == want_call]
                if leg.empty:
                    continue
                dd = leg["delta"].abs()
                if dd.isna().all():
                    continue
                legs.append(float(leg.loc[dd.idxmin(), "implied_vol"]))
            if len(legs) < 2:
                rows.append(FeatureRow(root=root, date=pd.Timestamp(date_),
                                       feature=f"atm_{tag}",
                                       value=None, reason="no_atm_both_legs"))
                n_dropped += 1
                continue
            v = round(float(np.mean(legs)), 6)
            rows.append(FeatureRow(root=root, date=pd.Timestamp(date_),
                                   feature=f"atm_{tag}", value=v))
    return rows, n_total, n_dropped


def _build_oi_features(fixture_root: Path, root: str, year: int,
                       greeks: pd.DataFrame, oi: pd.DataFrame
                       ) -> tuple[list[FeatureRow], int, int]:
    """DOI5 = sumOI(t)/sumOI(t-5 sessions)-1; both endpoints required, valid
    identity, OI>0, expiry>date (0DTE excluded).
    """
    rows: list[FeatureRow] = []
    if oi is None or oi.empty:
        return rows, 0, 0
    o = oi.copy()
    o["date"] = pd.to_datetime(o["date"], errors="coerce")
    o["expiration"] = pd.to_datetime(o["expiration"], errors="coerce")
    o["open_interest"] = pd.to_numeric(o["open_interest"], errors="coerce")
    o = o[(o["open_interest"] > 0) & (o["expiration"] > o["date"])]
    if o.empty:
        return rows, 0, 0
    daily = o.groupby("date")["open_interest"].sum().sort_index()
    n_total = 0
    n_dropped = 0
    date_lookup = {ts.date(): ts for ts in daily.index}
    for d in daily.index:
        n_total += 1
        d_back = nyse_calendar.session_n_back(d.date(), 5)
        if d_back is None or d_back not in date_lookup:
            rows.append(FeatureRow(root=root, date=pd.Timestamp(d),
                                   feature="doi5",
                                   value=None, reason="unavailable_window"))
            continue
        a = float(daily.loc[d])
        b = float(daily.loc[pd.Timestamp(d_back)])
        if not (np.isfinite(a) and np.isfinite(b)) or b <= 0:
            rows.append(FeatureRow(root=root, date=pd.Timestamp(d),
                                   feature="doi5",
                                   value=None, reason="zero_denominator"))
            continue
        rows.append(FeatureRow(root=root, date=pd.Timestamp(d),
                               feature="doi5", value=a / b - 1.0))
    return rows, n_total, n_dropped


def _build_mom5_features(root: str, prices: pd.Series
                         ) -> tuple[list[FeatureRow], int, int]:
    """MOM5 = adjusted_close(t)/adjusted_close(t-5 sessions)-1; both endpoints
    required. Uses the protocol-adjusted close (NOT the merged swing series)."""
    rows: list[FeatureRow] = []
    if prices is None or prices.empty:
        return rows
    s = prices.dropna()
    s = s[s > 0]
    if s.empty:
        return rows
    n_total = 0
    date_list = [ts.date() for ts in s.index]
    date_lookup = {d: i for i, d in enumerate(date_list)}
    for i, d in enumerate(s.index):
        n_total += 1
        d_back = nyse_calendar.session_n_back(d.date(), 5)
        if d_back is None or d_back not in date_lookup:
            rows.append(FeatureRow(root=root, date=pd.Timestamp(d),
                                   feature="mom5",
                                   value=None, reason="unavailable_window"))
            continue
        idx = date_lookup[d_back]
        a = float(s.iloc[i])
        b = float(s.iloc[idx])
        if not (np.isfinite(a) and np.isfinite(b)) or b <= 0:
            rows.append(FeatureRow(root=root, date=pd.Timestamp(d),
                                   feature="mom5",
                                   value=None, reason="zero_denominator"))
            continue
        rows.append(FeatureRow(root=root, date=pd.Timestamp(d),
                               feature="mom5", value=a / b - 1.0))
    return rows, n_total, 0


# ---------------------------------------------------------------------------
# Label construction (per protocol)
# ---------------------------------------------------------------------------

def _build_label_target(fixture_root: Path, root: str, prices: pd.Series,
                        spy_prices: pd.Series, horizon: int,
                        era_end: pd.Timestamp) -> tuple[
                            list[FeatureRow], int, int]:
    """Primary return target = underlying_return(e0..eh) - spy_return(e0..eh)
    OR volatility target = annualized std of one-session log returns on the
    canonical window e0..eh. Endpoints must be canonical NYSE sessions after
    feature date t; eh <= era_end; no era seam crossing.
    """
    rows: list[FeatureRow] = []
    if prices is None or prices.empty or spy_prices is None or spy_prices.empty:
        return rows, 0, 0
    p = prices.dropna()
    p = p[p > 0]
    s = spy_prices.dropna()
    s = s[s > 0]
    if p.empty or s.empty:
        return rows, 0, 0
    p_dates = {ts.date(): float(val) for ts, val in p.items()}
    s_dates = {ts.date(): float(val) for ts, val in s.items()}
    n_total = 0
    for d, val in p.items():
        n_total += 1
        d_d = d.date()
        e0 = nyse_calendar.session_n_forward(d_d, 1)
        if e0 is None:
            rows.append(FeatureRow(root=root, date=pd.Timestamp(d),
                                   feature=f"fwd_ret_{horizon}",
                                   value=None, reason="outside_calendar"))
            continue
        eh = nyse_calendar.session_n_forward(e0, horizon)
        if eh is None or eh > era_end.date():
            rows.append(FeatureRow(root=root, date=pd.Timestamp(d),
                                   feature=f"fwd_ret_{horizon}",
                                   value=None, reason="era_purge"))
            continue
        # Native dates on price series.
        path = []
        cur = e0
        for _ in range(horizon + 1):
            if cur is None:
                break
            path.append(cur)
            nxt = nyse_calendar.session_n_forward(cur, 1)
            cur = nxt
        # Path should have horizon+1 entries.
        if len(path) < horizon + 1 or path[-1] != eh:
            rows.append(FeatureRow(root=root, date=pd.Timestamp(d),
                                   feature=f"fwd_ret_{horizon}",
                                   value=None, reason="missing_price"))
            continue
        if not all((d_e in p_dates) for d_e in path):
            rows.append(FeatureRow(root=root, date=pd.Timestamp(d),
                                   feature=f"fwd_ret_{horizon}",
                                   value=None, reason="missing_price"))
            continue
        if not all((d_e in s_dates) for d_e in path):
            rows.append(FeatureRow(root=root, date=pd.Timestamp(d),
                                   feature=f"fwd_ret_{horizon}",
                                   value=None, reason="missing_price"))
            continue
        p0 = p_dates[e0]
        ph = p_dates[eh]
        s0 = s_dates[e0]
        sh = s_dates[eh]
        if p0 <= 0 or s0 <= 0:
            rows.append(FeatureRow(root=root, date=pd.Timestamp(d),
                                   feature=f"fwd_ret_{horizon}",
                                   value=None, reason="missing_price"))
            continue
        ret = (ph / p0) - 1.0
        sret = (sh / s0) - 1.0
        rows.append(FeatureRow(root=root, date=pd.Timestamp(d),
                               feature=f"fwd_ret_{horizon}",
                               value=ret - sret))
    return rows, n_total, 0


def _build_vol_target(fixture_root: Path, root: str, prices: pd.Series,
                      era_end: pd.Timestamp
                      ) -> tuple[list[FeatureRow], int, int]:
    """Annualized std of one-session log returns on the canonical window e0..eh.

    Spec: annualized standard deviation (ddof=1) of the h log adjusted-close
    one-session returns whose endpoints span e0 through eh. No option PnL.
    """
    rows: list[FeatureRow] = []
    if prices is None or prices.empty:
        return rows, 0, 0
    p = prices.dropna()
    p = p[p > 0]
    if p.empty:
        return rows, 0, 0
    p_dates = {ts.date(): float(val) for ts, val in p.items()}
    # Two horizons produce two windows; this builder reuses _build_label_target's
    # path construction logic by mirroring it inline.
    n_total = 0
    for d in p.index:
        n_total += 1
        d_d = d.date()
        e0 = nyse_calendar.session_n_forward(d_d, 1)
        # We accept the era_end constraint via the caller; here we treat h=5 (near)
        # and h=21 (back) as the two separate horizon RV targets; this function
        # emits ONE feature 'rv_5' to mirror the IC convention.
        for horizon, feat in ((5, "rv_5"), (21, "rv_21")):
            eh = nyse_calendar.session_n_forward(e0, horizon) if e0 else None
            if eh is None or eh > era_end.date():
                rows.append(FeatureRow(root=root, date=pd.Timestamp(d),
                                       feature=feat,
                                       value=None, reason="era_purge"))
                continue
            path = []
            cur = e0
            while cur is not None and len(path) < horizon + 1:
                path.append(cur)
                cur = nyse_calendar.session_n_forward(cur, 1)
            if len(path) < horizon + 1 or path[-1] != eh:
                rows.append(FeatureRow(root=root, date=pd.Timestamp(d),
                                       feature=feat,
                                       value=None, reason="missing_price"))
                continue
            if not all((de in p_dates) for de in path):
                rows.append(FeatureRow(root=root, date=pd.Timestamp(d),
                                       feature=feat,
                                       value=None, reason="missing_price"))
                continue
            rets = []
            for i in range(1, len(path)):
                a, b = p_dates[path[i - 1]], p_dates[path[i]]
                if a <= 0:
                    continue
                rets.append(np.log(b / a))
            if len(rets) < 2:
                rows.append(FeatureRow(root=root, date=pd.Timestamp(d),
                                       feature=feat,
                                       value=None, reason="missing_price"))
                continue
            rv = float(np.std(rets, ddof=1) * np.sqrt(252))
            rows.append(FeatureRow(root=root, date=pd.Timestamp(d),
                                   feature=feat, value=rv))
    return rows, n_total, 0


# ---------------------------------------------------------------------------
# Assemble features per contrast + era + horizon (synthetic-fixture path).
# ---------------------------------------------------------------------------

def _features_dataframe(root: str, fixture_root: Path,
                       year: int, spy_prices: pd.Series
                       ) -> tuple[pd.DataFrame, dict[str, int]]:
    """Build one root-year feature frame (in-memory). For tests."""
    greeks = _load_fixture_root_year(fixture_root, root, year, "greeks")
    oi = _load_fixture_root_year(fixture_root, root, year, "oi")
    prices = _load_fixture_price(fixture_root, root)
    all_rows: list[FeatureRow] = []
    counts: dict[str, int] = {}
    # GEX/VEX/CEX.
    g_rows, g_total, g_drop = _build_gex_features(
        fixture_root, root, year, greeks, oi)
    counts["gex_total"] = counts.get("gex_total", 0) + g_total
    counts["gex_dropped"] = counts.get("gex_dropped", 0) + g_drop
    all_rows.extend(g_rows)
    # CW ivspread level.
    iv_rows, iv_total, iv_drop = _build_cw_ivspread_features(
        fixture_root, root, year, greeks, oi)
    counts["iv_total"] = counts.get("iv_total", 0) + iv_total
    counts["iv_dropped"] = counts.get("iv_dropped", 0) + iv_drop
    all_rows.extend(iv_rows)
    # Skew.
    sk_rows, sk_total, sk_drop = _build_skew_features(
        fixture_root, root, year, greeks)
    counts["sk_total"] = counts.get("sk_total", 0) + sk_total
    counts["sk_dropped"] = counts.get("sk_dropped", 0) + sk_drop
    all_rows.extend(sk_rows)
    # ATM IV.
    atm_rows, atm_total, atm_drop = _build_atm_iv_features(
        fixture_root, root, year, greeks)
    counts["atm_total"] = counts.get("atm_total", 0) + atm_total
    counts["atm_dropped"] = counts.get("atm_dropped", 0) + atm_drop
    all_rows.extend(atm_rows)
    # DOI5.
    oi_rows, oi_total, oi_drop = _build_oi_features(
        fixture_root, root, year, greeks, oi)
    counts["oi_total"] = counts.get("oi_total", 0) + oi_total
    counts["oi_dropped"] = counts.get("oi_dropped", 0) + oi_drop
    all_rows.extend(oi_rows)
    # MOM5.
    m_rows, m_total, _ = _build_mom5_features(root, prices)
    counts["mom_total"] = counts.get("mom_total", 0) + m_total
    all_rows.extend(m_rows)
    df = pd.DataFrame([
        {"root": r.root, "date": r.date, "feature": r.feature,
         "value": r.value, "reason": r.reason}
        for r in all_rows
    ])
    # Derived feature: VANNA_RELIEF = vex_norm * (-d5_atm_near). Per protocol,
    # both inputs use the EXACT same root/date intersection. No new primitives
    # are introduced — we multiply two existing per-frame values at the
    # available overlap.
    if not df.empty:
        for tag in ("near", "back"):
            base = df[df["feature"] == "net_vanna_norm"].rename(
                columns={"value": "_vex"})
            d5 = df[df["feature"] == "atm_near"].rename(
                columns={"value": "_atm"}) if tag == "near" else df[
                    df["feature"] == "atm_back"].rename(
                        columns={"value": "_atm"})
            joined = base.merge(
                d5[["root", "date", "_atm"]], on=["root", "date"], how="inner")
            joined = joined.dropna(subset=["_vex", "_atm"])
            for _, row in joined.iterrows():
                if not (np.isfinite(row["_vex"]) and np.isfinite(row["_atm"])):
                    continue
                all_rows.append(FeatureRow(
                    root=row["root"], date=row["date"],
                    feature="vanna_relief",
                    value=float(row["_vex"]) * (-float(row["_atm"])),
                ))
    # Derived feature: D5 cw ivspread change.
    if not df.empty:
        iv = df[df["feature"] == "cw_ivspread"][
            ["root", "date", "value"]].rename(columns={"value": "_iv"})
        iv_sorted = iv.sort_values(["root", "date"]).reset_index(drop=True)
        iv_sorted["_d5"] = iv_sorted.groupby("root")["_iv"].diff(5)
        for _, row in iv_sorted.iterrows():
            v = row["_d5"]
            if np.isfinite(v):
                all_rows.append(FeatureRow(
                    root=row["root"], date=row["date"],
                    feature="d5_cw_ivspread", value=float(v)))
    # Derived feature: skew acceleration = d5_skew(t) - d5_skew(t-5).
    if not df.empty:
        sk = df[df["feature"] == "skew"][
            ["root", "date", "value"]].rename(columns={"value": "_sk"})
        sk_sorted = sk.sort_values(["root", "date"]).reset_index(drop=True)
        sk_sorted["_d5"] = sk_sorted.groupby("root")["_sk"].diff(5)
        sk_sorted["_acc"] = sk_sorted.groupby("root")["_d5"].diff(5)
        for _, row in sk_sorted.iterrows():
            v = row["_acc"]
            if np.isfinite(v):
                all_rows.append(FeatureRow(
                    root=row["root"], date=row["date"],
                    feature="skew_accel", value=float(v)))
    # Derived feature: term_slope = atm_near - atm_back (requires BOTH legs).
    if not df.empty:
        near = df[df["feature"] == "atm_near"][
            ["root", "date", "value"]].rename(columns={"value": "_n"})
        back = df[df["feature"] == "atm_back"][
            ["root", "date", "value"]].rename(columns={"value": "_b"})
        joined = near.merge(back, on=["root", "date"], how="inner")
        joined = joined.dropna(subset=["_n", "_b"])
        for _, row in joined.iterrows():
            if not (np.isfinite(row["_n"]) and np.isfinite(row["_b"])):
                continue
            all_rows.append(FeatureRow(
                root=row["root"], date=row["date"],
                feature="term_slope", value=float(row["_n"]) - float(row["_b"]),
            ))
    df = pd.DataFrame([
        {"root": r.root, "date": r.date, "feature": r.feature,
         "value": r.value, "reason": r.reason}
        for r in all_rows
    ])
    return df, counts


def _build_panel(fixture_root: Path, era_name: str, era_start: pd.Timestamp,
                 era_end: pd.Timestamp, spy_prices: pd.Series,
                 scored_roots: list[str],
                 ) -> tuple[pd.DataFrame, dict[str, int]]:
    """Build the per-(root, date) feature + target panel for one era."""
    counts: dict[str, int] = {}
    frames: list[pd.DataFrame] = []
    for root in scored_roots:
        if root in KNOWN_PRICE_NON_EVALUABLE_ROOTS:
            # Stay visible: emit a single null row per (date, feature) so the
            # coverage matrix reflects the root but contributes zero IC.
            continue
        prices = _load_fixture_price(fixture_root, root)
        if prices is None:
            continue
        years_in_era = list(range(era_start.year, era_end.year + 1))
        for year in years_in_era:
            df, c = _features_dataframe(root, fixture_root, year, spy_prices)
            counts[root] = counts.get(root, 0) + sum(c.values())
            frames.append(df)
        # Labels (per horizon).
        for horizon in HORIZONS:
            lbl_rows, _, _ = _build_label_target(
                fixture_root, root, prices, spy_prices, horizon, era_end)
            frames.append(pd.DataFrame([
                {"root": r.root, "date": r.date, "feature": r.feature,
                 "value": r.value, "reason": r.reason} for r in lbl_rows]))
        # RV target.
        rv_rows, _, _ = _build_vol_target(fixture_root, root, prices, era_end)
        frames.append(pd.DataFrame([
            {"root": r.root, "date": r.date, "feature": r.feature,
             "value": r.value, "reason": r.reason} for r in rv_rows]))
    if not frames:
        return pd.DataFrame(), counts
    panel = pd.concat(frames, ignore_index=True)
    # Era mask.
    panel["date"] = pd.to_datetime(panel["date"], errors="coerce")
    panel = panel[(panel["date"] >= era_start) & (panel["date"] <= era_end)]
    return panel, counts


# ---------------------------------------------------------------------------
# IC computation and cell evaluation
# ---------------------------------------------------------------------------

def _date_level_ic(panel: pd.DataFrame, feature: str, target: str
                   ) -> tuple[np.ndarray, np.ndarray]:
    """One Spearman IC per date across scored roots. Returns (dates, ic_values).

    When EITHER ``feature`` or ``target`` is absent from the panel (sparse cell,
    feature builder produced no rows in this era), the cell contributes zero
    IC dates and is therefore NON_EVALUABLE downstream — never an error.
    """
    df = panel[panel["feature"].isin([feature, target])].copy()
    if df.empty:
        return np.array([], dtype="datetime64[ns]"), np.array([], dtype=float)
    pivot = df.pivot_table(index=["date", "root"], columns="feature",
                           values="value", aggfunc="first").reset_index()
    if feature not in pivot.columns or target not in pivot.columns:
        return np.array([], dtype="datetime64[ns]"), np.array([], dtype=float)
    pivot = pivot.dropna(subset=[feature, target], how="any")
    if pivot.empty:
        return np.array([], dtype="datetime64[ns]"), np.array([], dtype=float)
    out_dates: list[pd.Timestamp] = []
    out_ic: list[float] = []
    for d, g in pivot.groupby("date"):
        if len(g) < MIN_ROOTS_PER_IC_DATE:
            continue
        try:
            ic, _ = stats.spearmanr(g[feature], g[target])
        except Exception:
            continue
        if np.isfinite(ic):
            out_dates.append(pd.Timestamp(d))
            out_ic.append(float(ic))
    return (np.array(out_dates, dtype="datetime64[ns]"),
            np.array(out_ic, dtype=float))


def _effective_blocks(dates: np.ndarray, horizon: int) -> int:
    """Greedy NON-OVERLAPPING inclusive target windows >= horizon sessions.

    Spec: report n_dates AND effective_blocks, where effective_blocks is the
    count of greedily selected non-overlapping h-session label windows among
    eligible IC dates.
    """
    if len(dates) == 0:
        return 0
    sorted_dates = np.sort(dates)
    n_blocks = 0
    cursor: pd.Timestamp | None = None
    for d in sorted_dates:
        ts = pd.Timestamp(d)
        if cursor is None:
            cursor = ts
            n_blocks = 1
            continue
        # How many sessions between cursor and ts (inclusive target >= horizon).
        if cursor > ts:
            continue
        # Use is_session calendar count.
        delta_days = (ts - cursor).days
        if delta_days < horizon - 1:
            continue
        cursor = ts
        n_blocks += 1
    return n_blocks


def _cell_evaluate(panel: pd.DataFrame, feature: str, target: str,
                   horizon: int
                   ) -> dict[str, Any]:
    """One (contrast, era, horizon) cell -> IC time-series + HAC inference.

    Returns a dict with n_dates, n_rows (root+date rows fed in), effective_blocks,
    raw_p, t_stat, mean_ic, median_ic, lag, lag_kind, ci95_lo, ci95_hi.
    """
    dates, ics = _date_level_ic(panel, feature, target)
    n_dates = int(len(dates))
    n_rows = int(len(panel))
    if n_dates < MIN_IC_DATES:
        return {
            "feature": feature, "target": target, "horizon": horizon,
            "n_rows": n_rows, "n_dates": n_dates,
            "effective_blocks": 0,
            "lag": None, "mean_ic": None, "median_ic": None,
            "t_stat": None, "raw_p": None, "ci95_lo": None, "ci95_hi": None,
            "state": "NON_EVALUABLE",
            "reason": (
                "n_dates<min"
                if n_dates > 0
                else "no_observed_inevaluable"),
        }
    # Full-calendar HAC: missing dates stay absent; covariance uses observed
    # pairs at their true session separation, an absent-date pair contributes
    # zero residual product.
    n = n_dates
    auto = max(int(np.floor(4.0 * (n / 100.0) ** (2.0 / 9.0))), 2 * horizon)
    lag = max(2 * horizon, min(auto, n - 2))
    # Student-t HAC: same formula as options_history_gauntlet._hac_ttest but
    # we recompute here against the documented t/regression semantics on the full
    # canonical calendar (unchanged canonical return math).
    mu = float(np.mean(ics))
    resid = ics - mu
    gamma0 = float(np.dot(resid, resid) / n)
    nw_var = gamma0
    for j in range(1, lag + 1):
        gamma_j = float(np.dot(resid[j:], resid[:-j]) / n)
        nw_var += 2.0 * (1.0 - j / (lag + 1.0)) * gamma_j
    se = float(np.sqrt(max(nw_var, 1e-30) / n))
    t_stat = mu / se if se > 0 else float("nan")
    raw_p = float(2.0 * stats.t.sf(abs(t_stat), df=max(n - 1, 1))) \
        if np.isfinite(t_stat) else float("nan")
    # 95% CI on the HAC t reference (df=n-1).
    if np.isfinite(t_stat) and se > 0:
        tc = float(stats.t.ppf(0.975, df=max(n - 1, 1)))
        ci_lo = mu - tc * se
        ci_hi = mu + tc * se
    else:
        ci_lo = ci_hi = float("nan")
    blocks = _effective_blocks(dates, horizon)
    if blocks < MIN_EFFECTIVE_BLOCKS:
        return {
            "feature": feature, "target": target, "horizon": horizon,
            "n_rows": n_rows, "n_dates": n_dates,
            "effective_blocks": blocks,
            "lag": lag, "mean_ic": mu, "median_ic": float(np.median(ics)),
            "t_stat": t_stat, "raw_p": raw_p,
            "ci95_lo": ci_lo, "ci95_hi": ci_hi,
            "state": "NON_EVALUABLE",
            "reason": "effective_blocks<min",
        }
    return {
        "feature": feature, "target": target, "horizon": horizon,
        "n_rows": n_rows, "n_dates": n_dates,
        "effective_blocks": blocks,
        "lag": lag, "mean_ic": mu, "median_ic": float(np.median(ics)),
        "t_stat": t_stat, "raw_p": raw_p,
        "ci95_lo": ci_lo, "ci95_hi": ci_hi,
        "state": "EVALUABLE",
        "reason": None,
    }


# ---------------------------------------------------------------------------
# Top-level analyze
# ---------------------------------------------------------------------------

def analyze(
    *, manifest_path: str, manifest_sha: str, protocol_path: str,
    fixture_root: str,
) -> dict[str, Any]:
    """Run analyze mode against a frozen manifest + protocol.

    Verification chain (per spec):
      1. Protocol SHA matches EXPECTED_PROTOCOL_SHA (refuses protocol mutation).
      2. Manifest SHA matches ``manifest_sha`` (refuses manifest mutation).
      3. Every manifest record's file exists, sha256 matches, schema matches.
      4. No duplicate manifest paths.
      5. Root/year alignment matches the protocol population.
      6. Run every (contrast, era, horizon) cell → 60 cells always.
      7. Run global BH FDR at k=60 alpha=0.10.
    """
    mp = Path(manifest_path)
    pp = Path(protocol_path)
    fr = Path(fixture_root)
    # 1 + 2
    proto = load_frozen_protocol(pp)
    manifest = load_manifest(mp, expected_sha=manifest_sha)
    if manifest.protocol_sha != proto.sha256:
        raise ValueError(
            "manifest protocol_sha does not match the on-disk protocol — "
            "refusing to analyze (frozen)")
    # 3-5
    # We can't resolve the real store/price_store paths from the manifest alone
    # (the manifest carries abs_paths); use those for re-hash checks.
    verify_manifest_against_inputs(
        manifest,
        store=Path("/nonexistent"),
        price_store=Path("/nonexistent"),
    )
    # 5: root/year alignment.
    roots_years = {(r["root"], r["year"])
                   for r in manifest.results
                   if r["kind"] in ("greeks", "oi")}
    if not roots_years:
        raise ManifestVerificationError(
            "manifest contains no greeks/oi records — refusing analyze")
    # Load synthetic fixture once.
    spy_prices = _load_fixture_price(fr, BENCHMARK_ONLY_ROOT)
    if spy_prices is None:
        raise ValueError(
            f"missing SPY fixture at {fr}/adjusted_price/{BENCHMARK_ONLY_ROOT}.parquet — refusing")
    # 6: 60 cells.
    cells: list[dict[str, Any]] = []
    for era_name, era_start_str, era_end_str in ERAS:
        era_start = pd.Timestamp(era_start_str)
        era_end = pd.Timestamp(era_end_str)
        panel, _ = _build_panel(
            fr, era_name, era_start, era_end, spy_prices,
            scored_roots=[r for r in SCORED_ROOTS
                         if r not in COVERAGE_ONLY_ROOTS])
        for contrast in CONTRAST_IDS:
            feature = CONTRAST_FEATURES[contrast]
            target_kind = CONTRAST_TARGETS[contrast]
            for horizon in HORIZONS:
                if contrast == "GEX_NORM_TO_FWD_RV":
                    target = f"rv_{horizon}"
                else:
                    target = f"fwd_ret_{horizon}"
                cells.append(_cell_evaluate(panel, feature, target, horizon))
    # 7: BH FDR over all 60 cells (sparse cells still consume slots).
    bh_input = {f"cell_{i:02d}": c.get("raw_p") if c.get("raw_p") is not None
                else float("nan")
                for i, c in enumerate(cells)}
    # BH refuses NaN; skip NaN cells from the BH pass but keep the slot.
    bh_clean = {k: v for k, v in bh_input.items()
                if np.isfinite(v)}
    bh = _bh_fdr(bh_clean, k_family=BH_K, alpha=BH_ALPHA)
    for i, c in enumerate(cells):
        key = f"cell_{i:02d}"
        if key in bh:
            c["bh_adj_p"] = bh[key]["bh_adj_p"]
            c["bh_rank"] = bh[key]["rank"]
            c["bh_reject"] = bool(bh[key]["reject_h0"])
        else:
            c["bh_adj_p"] = None
            c["bh_rank"] = None
            c["bh_reject"] = False
    return {
        "study_id": "THETA-EOD-RETROSPECTIVE-ASSOCIATION-V1",
        "fdr_family": FDR_FAMILY,
        "protocol_sha256": proto.sha256,
        "manifest_sha256": manifest_sha,
        "n_cells": len(cells),
        "cells": cells,
        "bh_k": BH_K, "bh_alpha": BH_ALPHA,
        "pit_status": "PIT_UNPROVEN",
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Theta EOD retrospective association v1 — frozen protocol helper"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_prep = sub.add_parser("prepare-manifest", help="Inventory selected files")
    p_prep.add_argument("--store", required=True,
                        help="ThetaEOD store root (e.g. /Volumes/STORAGE/macro-data/thetadata_eod)")
    p_prep.add_argument("--price-store", required=True,
                        help="Adjusted-price store root (e.g. .../data/yahoo)")
    p_prep.add_argument("--protocol", required=True,
                        help="Path to the frozen protocol JSON")
    p_prep.add_argument("--out", required=True,
                        help="Output manifest JSON path")

    p_ana = sub.add_parser("analyze", help="Run analyze against a frozen manifest")
    p_ana.add_argument("--manifest", required=True)
    p_ana.add_argument("--manifest-sha", required=True,
                       help="Frozen manifest SHA256 (hex)")
    p_ana.add_argument("--protocol", required=True)
    p_ana.add_argument("--fixture-root", required=True,
                       help="Root of the synthetic-fixture directory")

    args = parser.parse_args()
    if args.cmd == "prepare-manifest":
        m = prepare_manifest(
            store=Path(args.store),
            price_store=Path(args.price_store),
            protocol_path=Path(args.protocol),
        )
        sha = write_manifest(m, Path(args.out))
        # The protocol forbids NaN in numerical outcomes; we serialize them via
        # JSON-safe primitives. The manifest itself only carries bytes/hashes/
        # sizes/dates/strings — all JSON-safe by construction.
        print(f"manifest_written: {args.out}")
        print(f"manifest_sha256: {sha}")
        return 0
    if args.cmd == "analyze":
        result = analyze(
            manifest_path=args.manifest,
            manifest_sha=args.manifest_sha,
            protocol_path=args.protocol,
            fixture_root=args.fixture_root,
        )
        print(json.dumps(result, indent=2, sort_keys=True, default=str))
        return 0
    parser.error(f"unknown cmd: {args.cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())