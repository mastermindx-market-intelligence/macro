"""scripts/build_options_entry_state.py — options entry state + display projection builder.

Writes the canonical display-state table at data/options_entry/state.parquet and a
small browser projection at site/options_entry/current.json.  The JSON is a projection
of the parquet, not a second owner: it exposes only the already-computed raw/context
fields needed by the Options workspace's expiration-pressure panel.

See engine/options_entry_state.py for column spec and source details.

Runtime target: <60 seconds (light I/O; no network; reads committed parquet + JSON files).

Usage:
    .venv/bin/python -m scripts.build_options_entry_state
"""
from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd

# Allow running as a standalone script from the repo root.
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent
sys.path.insert(0, str(_REPO_ROOT))

from engine.options_entry_state import build_state   # noqa: E402
from lib import config                               # noqa: E402

log = logging.getLogger(__name__)

OUTPUT_DIR = config.data_dir() / "options_entry"
OUTPUT_PATH = OUTPUT_DIR / "state.parquet"
SITE_OUTPUT_PATH = config.site_dir() / "options_entry" / "current.json"

_PROJECTION_FIELDS = (
    "ticker",
    "as_of",
    "front7_charm_share",
    "front7_gex_share",
    "opex_days",
    "root_class",
    "evidence_quality",
    "src_gex_asof",
)


def _json_scalar(value):
    """Return one JSON-safe scalar; missing pandas/numpy values become null."""
    if value is None or pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if hasattr(value, "isoformat") and not isinstance(value, str):
        try:
            return value.isoformat()
        except (TypeError, ValueError):
            pass
    if isinstance(value, (str, bool, int, float)):
        return value
    return str(value)


def build_site_projection(df: pd.DataFrame) -> dict:
    """Project the current per-name expiration context without deriving a new score."""
    rows: dict[str, dict] = {}
    for raw in df.to_dict(orient="records"):
        ticker_value = _json_scalar(raw.get("ticker"))
        ticker = str(ticker_value or "").strip().upper()
        if not ticker:
            continue
        row = {key: _json_scalar(raw.get(key)) for key in _PROJECTION_FIELDS}
        row["ticker"] = ticker
        rows[ticker] = row

    as_of_values = [
        str(row["as_of"])
        for row in rows.values()
        if row.get("as_of") not in (None, "")
    ]
    return {
        "schema": "options_entry.current.v1",
        "as_of": max(as_of_values) if as_of_values else None,
        "is_context_only": True,
        "rows": dict(sorted(rows.items())),
    }


def _atomic_write_json(path: Path, payload: dict) -> None:
    """Write the display projection atomically and reject NaN/Infinity."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(
                payload,
                fh,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    t0 = time.perf_counter()
    root = _REPO_ROOT

    df = build_state(root)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_PATH, index=False)
    projection = build_site_projection(df)
    _atomic_write_json(SITE_OUTPUT_PATH, projection)

    elapsed = time.perf_counter() - t0
    n = len(df)
    eq_counts = df["evidence_quality"].value_counts().to_dict() if n else {}
    print(
        f"[build_options_entry_state] wrote {OUTPUT_PATH.relative_to(_REPO_ROOT)} + "
        f"{SITE_OUTPUT_PATH.relative_to(_REPO_ROOT)} — {n} tickers, "
        f"evidence_quality={eq_counts}, "
        f"elapsed={elapsed:.2f}s"
    )
    if elapsed > 60:
        log.warning(
            "build_options_entry_state exceeded 60s runtime budget (%.1fs) — "
            "investigate source I/O", elapsed
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
