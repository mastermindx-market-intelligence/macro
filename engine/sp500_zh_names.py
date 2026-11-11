"""engine/sp500_zh_names.py — the S&P desk's owned-Chinese-name lookup (light loader).

Split out of scripts/build_subsector_confluence.py (review r1, B1) so tests can pin
the loader and its merge without importing the heavy builder — importing the builder
dragged 23 extra files into the curated-exclusive CI job that owns the subsector
suites and reddened the `contract-delta` check.

Closure contract: this module imports stdlib plus `SECTOR_ZH` from
engine.sp500_heatmap only (whose own imports are typing/numpy/pandas — no further
repo files), so anything importing it stays inside the subsector family's
registered CI paths.

Names are carried ONLY from tables the repo already owns (never an authored
translation):
  * sub-industry names → config/sp500_subindustry_zh.json, a character-for-character
    copy of templates/heatmap.js INDUSTRY_ZH (parity-pinned by
    tests/test_subsector_confluence_zh.py so the two can never drift);
  * sector words       → engine.sp500_heatmap.SECTOR_ZH — the SAME table the S&P
    heatmap renders from, imported directly so no second copy exists.

Merge order is the builder's historical one: the sub-industry table first, with
SECTOR_ZH winning on a shared key (the only shared key, 'Industrials', agrees —
pinned by test).

All-or-nothing validation (review r1, S2): anything other than a non-empty JSON
object whose every key and value is a non-empty string — a missing, empty or
invalid file, `null`, a list, a scalar, a list of pairs, or any non-string/empty
key or value — logs a warning and returns None for the WHOLE mapping, so every zh
field stays null and the nightly never dies. Matching downstream is exact string;
unknown keys stay null.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from engine.sp500_heatmap import SECTOR_ZH

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TABLE_PATH = REPO_ROOT / "config" / "sp500_subindustry_zh.json"


def load_sp500_zh_names(table_path: str | Path | None = None) -> dict[str, str] | None:
    """The S&P desk's {English name: owned Chinese name} lookup.

    Additive-never-fatal: a table that is missing, unreadable, or not a non-empty
    flat str→str object logs a warning and returns None (rows stay English/null),
    never raising into the nightly.
    """
    path = Path(table_path) if table_path is not None else DEFAULT_TABLE_PATH
    try:
        table = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 — display-only bilingual labels
        log.warning("sp500_zh_names: table unreadable (%s) — S&P rows stay English", e)
        return None
    if not isinstance(table, dict) or not table:
        log.warning("sp500_zh_names: table is not a non-empty object — S&P rows stay English")
        return None
    for key, value in table.items():
        if not isinstance(key, str) or not key or not isinstance(value, str) or not value:
            log.warning(
                "sp500_zh_names: key %r is not a non-empty string key/value — S&P rows stay English",
                key,
            )
            return None
    out = dict(table)
    out.update(SECTOR_ZH)  # sector words win on a shared key (they agree — pinned by test)
    return out
