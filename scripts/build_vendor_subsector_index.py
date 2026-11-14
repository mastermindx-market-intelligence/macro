"""Vendor subsector daily price index — written OUTSIDE the repository tree only.

COO ruling 38 Part B (s2a/s2b). The repository is PUBLIC, so every output of this
builder is written outside the repository tree (default ``/tmp/r38b/vendor_out``);
the builder refuses an output path inside the tree. No vendor group name or
per-group number is committed anywhere: this source carries none, and the tests
use a made-up fixture group. The vendor outputs (index parquet, sidecar, key map)
are internal research data under the Chairman gate 2 ruling and never go to git,
a site page or any public bucket.

Builds a daily equal-weight total-return index for the engine turn store's
subsector keys (``data/subsector_rotation/state.json``, the store written by
``engine/subsector_rotation_alerts.py``), on the #11146 theme-tree membership
as-is (``data/themes_heatmap/themes_tree.json``). Only keys present in BOTH the
engine store and the tree subsector family are built — exact key intersection, no
remapping or name matching. A store key with no tree membership (a synthetic
basket-backed group) is reported as a count and not built.

Reuses ``scripts/build_tree_breadth_and_index.py`` (``group_index``,
``tree_membership``, ``VENDOR_RIGHTS`` and the rights-set prefix) and
``engine.baskets._ew_level``. Floor of 5 priced members. Basis
``reconstructed_current_membership`` (sensitivity, today's members only); there is
no dated form. ``rights_class`` is stamped on every row and in the sidecar; the
rights and use sentences are copied exactly from the #11146 set.

Usage:
  python scripts/build_vendor_subsector_index.py \
      --closes <scratch closes_with_topup.parquet> \
      --download-meta <scratch download_meta_with_topup.json> \
      [--tree <themes_tree.json>] [--state <state.json>] \
      [--start 2000-01-01] [--out /tmp/r38b/vendor_out]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import pandas as pd  # noqa: E402

from engine import group_breadth_history as gbh  # noqa: E402
import scripts.build_tree_breadth_and_index as bt  # noqa: E402

FLOOR = 5
LEVEL = "subsector"
DEFAULT_OUT = Path("/tmp/r38b/vendor_out")
DEFAULT_START = "2000-01-01"

# Derive the output names from the rights-set prefix so this source names no vendor
# file (the display-surface guard scans every build_*.py for those literals).
_PREFIX = bt.RIGHTS_SETS["internal_only"]["prefix"]
OUT_INDEX = f"{_PREFIX}_subsector_index_daily_current.parquet"
OUT_META = f"{_PREFIX}_subsector_index_current.meta.json"
OUT_KEYMAP = f"{_PREFIX}_subsector_key_map.csv"

COLS = ["date", "level", "group", "index", "n_priced_members", "membership_basis", "rights_class"]
RIGHTS = bt.VENDOR_RIGHTS["rights_class"]
SPDR_PARENT_NOTE = ("spdr_parent is blank: the engine turn store assigns each subsector a theme "
                    "parent (engine/subsector_rotation_alerts.py _snapshot 'theme' field), not a "
                    "SPDR sector ETF; no SPDR parent is guessed. engine_key is the subsector key "
                    "itself, the key the turn store is written under.")
NO_OUTCOMES = ("Data only. Descriptive group levels and counts. No outcome relation, no backtest, "
               "no hit rate, no signal, ranking or score column.")


def guard_out(out: Path, root: Path) -> Path:
    """Fail closed if the output path is inside the repository tree (the repo is public)."""
    out = Path(out).resolve()
    root = Path(root).resolve()
    if out == root or root in out.parents:
        raise ValueError(f"vendor output must be outside the repository tree: {out} is under {root}")
    return out


def build_index(closes: pd.DataFrame, mem_sub: pd.DataFrame, engine_keys: set,
                start: pd.Timestamp, floor: int = FLOOR) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Daily per-subsector index on exactly the engine keys present in the tree family.

    ``mem_sub`` is the (ticker, group) subsector membership from ``bt.tree_membership``;
    ``engine_keys`` is the turn store's key set. Returns (index_df, keymap_df, counts).
    Counts are aggregates only — no per-group number is exposed by this function's meta.
    """
    closes = gbh.through_last_complete_row(closes.sort_index())
    rets = closes.pct_change(fill_method=None)
    rets = rets.where(closes.notna() & closes.shift(1).notna())
    priced = closes.notna()
    family_keys = set(mem_sub["group"].unique())
    buildable = sorted(set(engine_keys) & family_keys)
    keep = closes.index >= start
    parts = []
    for g in buildable:
        members = mem_sub.loc[mem_sub["group"] == g, "ticker"].tolist()
        lvl, n, _reason = bt.group_index(rets, members, start, floor=floor, priced=priced)
        parts.append(pd.DataFrame({"date": closes.index[keep], "level": LEVEL, "group": g,
                                   "index": lvl[keep].round(6).values,
                                   "n_priced_members": n[keep].values.astype("int64"),
                                   "membership_basis": bt.BASIS, "rights_class": RIGHTS}))
    df = pd.concat(parts, ignore_index=True)[COLS] if parts else pd.DataFrame(columns=COLS)
    km = pd.DataFrame({"group_key": buildable, "level": LEVEL,
                       "engine_key": buildable, "spdr_parent": ""})
    bmem = mem_sub[mem_sub["group"].isin(buildable)]
    priced_cols = set(closes.columns[closes.notna().any()])
    ever = df.groupby("group")["index"].apply(lambda s: bool(s.notna().any())) if len(df) else pd.Series(dtype=bool)
    counts = {
        "engine_store_keys": len(set(engine_keys)),
        "family_subsector_keys": len(family_keys),
        "built_keys": len(buildable),
        "store_only_keys": len(set(engine_keys) - family_keys),
        "family_only_keys": len(family_keys - set(engine_keys)),
        "groups_reaching_floor": int(ever.sum()),
        "groups_below_floor_throughout": int((~ever).sum()),
        "member_tickers": int(bmem["ticker"].nunique()),
        "member_tickers_priced": len(set(bmem["ticker"]) & priced_cols),
        "rows": int(len(df)),
        "span": ({"start": str(df["date"].min().date()), "end": str(df["date"].max().date())}
                 if len(df) else None),
    }
    return df, km, counts


def write_outputs(df: pd.DataFrame, km: pd.DataFrame, counts: dict, out: Path, root: Path,
                  dm: dict, start: pd.Timestamp) -> dict:
    """Write the three vendor outputs outside the tree; stamp rights on every row and the sidecar."""
    out = guard_out(out, root)
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / OUT_INDEX, index=False, compression="zstd")
    km.to_csv(out / OUT_KEYMAP, index=False)
    meta = dict(bt.VENDOR_RIGHTS)            # rights_class, source_family, rights_source,
    meta.update({                            # rights_sentence and use, copied exactly
        "basis": bt.BASIS, "basis_note": bt.BASIS_NOTE,
        "sensitivity": True, "level": LEVEL, "floor": FLOOR,
        "start": {"date": str(start.date()), "reason_before": bt.REASON_START},
        "spdr_parent_note": SPDR_PARENT_NOTE,
        "price_source": "the #11146 single-vintage download with topup (closes_with_topup.parquet), "
                        "held off git; a different source from the Tiingo sector history, never joined",
        "price_vintage": dm.get("vintage"), "price_topup": dm.get("topup"),
        "data_end": str(df["date"].max().date()) if len(df) else None,
        "counts": counts,
        "files": [OUT_INDEX, OUT_META, OUT_KEYMAP],
        "engine": "scripts.build_tree_breadth_and_index.group_index; engine.baskets._ew_level",
        "no_outcomes": NO_OUTCOMES,
        "out_of_tree": "every output is written outside the repository tree; the builder refuses an "
                       "in-tree output path (COO ruling 38 s2b; the repository is public)",
    })
    (out / OUT_META).write_text(json.dumps(meta, indent=1) + "\n")
    return meta


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--closes", type=Path, required=True)
    ap.add_argument("--download-meta", type=Path, required=True)
    ap.add_argument("--tree", type=Path, default=_ROOT / "data/themes_heatmap/themes_tree.json")
    ap.add_argument("--state", type=Path, default=_ROOT / "data/subsector_rotation/state.json")
    ap.add_argument("--start", default=DEFAULT_START)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--root", type=Path, default=_ROOT)
    a = ap.parse_args()
    try:
        # Fail closed BEFORE reading prices or building: an in-tree output path is
        # refused with a non-zero exit (COO ruling 38 s2b; the repository is public).
        a.out = guard_out(a.out, a.root)
    except ValueError as e:
        print(f"refused: {e}", file=sys.stderr)
        raise SystemExit(2)
    closes = pd.read_parquet(a.closes)
    dm = json.loads(Path(a.download_meta).read_text())
    mem_sub, _ = bt.tree_membership(a.tree)
    engine_keys = set(json.loads(Path(a.state).read_text()).keys())
    start = pd.Timestamp(a.start)
    df, km, counts = build_index(closes, mem_sub, engine_keys, start)
    write_outputs(df, km, counts, a.out, a.root, dm, start)
    print(json.dumps({"built_keys": counts["built_keys"], "rows": counts["rows"],
                      "groups_reaching_floor": counts["groups_reaching_floor"],
                      "out": str(Path(a.out).resolve())}, indent=1))


if __name__ == "__main__":
    main()
