"""Build the listed-member coverage companion (COO ruling 46).

Counts only. For each dated basis src (sp500 / sp400 / sp600) and each sector
group, this writes ``n_listed`` — the number of index members LISTED on a
session, whether or not a stored close exists for them — over the same session
calendar the dated sp500 breadth uses. It is the denominator companion to the
counted column (``n_members``) of each breadth file: ``n_members`` counts listed
AND priced members, ``n_listed`` counts listed members, so ``n_members <=
n_listed`` on every group-date when the same map and windows are used.

The group map and the membership windows are NOT re-implemented here: this
module imports ``membership_dated`` from ``scripts.build_group_breadth_history``
and ``assign_groups`` from ``engine.group_breadth_history`` (the same half-open
``start_date <= d < end_date`` windows, open ends, last-row-wins). A listed
member with no sector label is counted in a ``group_key == "unmapped"`` row for
that date — never dropped, never guessed into a group.

No price store is read. The only breadth file touched is the dated sp500
parquet's ``date`` column, used as the session calendar (group-level counts, no
prices). The house registries (#11107 baskets, #11146 families) are read for the
sidecar's static ``house_registry_sizes`` only.

No threshold, no "usable"/"thin" flag, no floor.

The parquet and the sidecar are each replaced atomically, but not as one atomic pair: a concurrent reader may see a new parquet beside the old sidecar for a moment.

Usage:
  python -m scripts.build_coverage_companion \
      --breadth-dir data/breadth \
      --dated-breadth data/breadth/history/group_breadth_daily_dated_sp500.parquet \
      --registry-json data/baskets/membership.json \
      --registry-dir data/breadth/history/registry \
      --out data/breadth/history \
      --map-commit <sha> --baskets-commit <sha> --families-commit <sha> \
      --calendar-commit <sha>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import pandas as pd  # noqa: E402

from engine import group_breadth_history as gbh  # noqa: E402
from scripts.build_group_breadth_history import membership_dated  # noqa: E402

UNMAPPED = "unmapped"
SRCS = ("sp500", "sp400", "sp600")

MEMBERSHIP_REL = "data/breadth/sp1500_pit_membership.parquet"
SECTORS_REL = "data/breadth/sp1500_pit_sectors.parquet"
BUILDER_REL = "scripts/build_group_breadth_history.py"
CALENDAR_REL = "data/breadth/history/group_breadth_daily_dated_sp500.parquet"
BASKETS_REL = "data/baskets/membership.json"
REGISTRY_REL = "data/breadth/history/registry/"

COUNTS_ONLY = ("Counts only. No threshold, flag or floor. n_listed joins the counted "
               "column of each breadth file on group and date.")
HOUSE_NOTE = ("Today's members applied to the past: n_listed is the registry size on "
              "every date.")


def _blob_sha(path: Path) -> str:
    """Git blob SHA-1 of a file's bytes (matches ``git rev-parse <commit>:<path>``)."""
    b = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()


def coverage_frame(mem: pd.DataFrame, calendar, groups, src: str) -> pd.DataFrame:
    """Listed-member counts per group per session, using the engine's windows.

    ``mem`` is the output of ``membership_dated`` (ticker, group, start_date,
    end_date). ``groups`` is the ordered list of mapped sector keys. Returns a
    long frame [src, group_key, session_date, n_listed] with one row per
    group (mapped groups plus ``unmapped``) per session. Pure: reads no files.
    """
    calendar = pd.DatetimeIndex(calendar)
    groups = list(groups)
    tickers = sorted(mem["ticker"].astype(str).unique())

    # Mapped groups: exactly the engine's assignment (it drops NaN-group rows).
    codes, _ = gbh.assign_groups(calendar, tickers, mem, groups=groups)
    # Unmapped: the SAME window function applied to the NaN-group rows only.
    un = mem[mem["group"].isna()].copy()
    un["group"] = UNMAPPED
    codes_u, _ = gbh.assign_groups(calendar, tickers, un, groups=[UNMAPPED])

    counts = {g: (codes == j).sum(axis=1) for j, g in enumerate(groups)}
    counts[UNMAPPED] = (codes_u == 0).sum(axis=1)

    blocks = []
    for g in groups + [UNMAPPED]:
        blocks.append(pd.DataFrame({
            "src": src,
            "group_key": g,
            "session_date": calendar,
            "n_listed": counts[g].astype("int64"),
        }))
    return pd.concat(blocks, ignore_index=True)


def _basket_sizes(baskets: dict) -> dict:
    """Today's active members per basket (a member with a 'removed' date is out)."""
    return {k: int(sum(1 for m in b.get("members", []) if not m.get("removed")))
            for k, b in baskets.items()}


def _family_sizes(registry_dir: Path) -> tuple[dict, list]:
    sizes, blobs = {}, []
    for f in sorted(Path(registry_dir).glob("*.csv")):
        df = pd.read_csv(f)
        sizes[f.name] = {str(g): int(n) for g, n in df.groupby("group").size().items()}
        blobs.append({"path": REGISTRY_REL + f.name, "blob_sha": _blob_sha(f)})
    return sizes, blobs


def _atomic_write(target: Path, writer) -> None:
    """Replace ``target`` atomically: write a temp file in the same directory,
    then ``os.replace`` it onto the target. ``writer`` receives the temp Path and
    writes the full content. On any failure the temp file is removed and any
    existing target is left byte-for-byte untouched.
    """
    fd, tmp = tempfile.mkstemp(dir=str(target.parent), prefix="." + target.name + ".", suffix=".tmp")
    os.close(fd)
    try:
        writer(Path(tmp))
        os.chmod(tmp, 0o644)
        os.replace(tmp, target)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def build(breadth_dir, dated_breadth, registry_json, registry_dir, out,
          map_commit: str, baskets_commit: str, families_commit: str,
          calendar_commit: str) -> dict:
    breadth_dir, out = Path(breadth_dir), Path(out)
    dated_breadth, registry_json, registry_dir = (Path(dated_breadth),
                                                 Path(registry_json), Path(registry_dir))

    sec = pd.read_parquet(breadth_dir / "sp1500_pit_sectors.parquet")
    groups = sorted(sec["sector"].dropna().astype(str).unique().tolist())

    cal = pd.read_parquet(dated_breadth, columns=["date"])["date"]
    calendar = pd.DatetimeIndex(sorted(pd.unique(cal)))

    frames, srcs, excluded = [], [], {}
    for src in SRCS:
        mem = membership_dated(breadth_dir, src)
        if mem.empty:
            excluded[src] = "no dated membership rows"
            continue
        # A source whose members are ALL unlabelled is still counted, entirely
        # under 'unmapped' (ruling 60 gap a): never excluded, never guessed into
        # a group. srcs_excluded is reserved for a source with NO dated rows.
        frames.append(coverage_frame(mem, calendar, groups, src))
        srcs.append(src)
    cov = pd.concat(frames, ignore_index=True)

    # Validate and build EVERYTHING in memory before touching published files
    # (ruling 60 gap b): a malformed basket JSON or a family CSV without a
    # 'group' column fails here, leaving any existing parquet and sidecar
    # byte-for-byte untouched.
    baskets = json.loads(registry_json.read_text())["baskets"]
    basket_sizes = _basket_sizes(baskets)
    family_sizes, family_blobs = _family_sizes(registry_dir)

    builder_path = _ROOT / BUILDER_REL
    meta = {
        "basis": "listed_member_coverage",
        "counts_only": COUNTS_ONLY,
        "group_map": {"path": SECTORS_REL, "blob_sha": _blob_sha(breadth_dir / "sp1500_pit_sectors.parquet"),
                      "commit": map_commit},
        "membership_dated": {"path": BUILDER_REL,
                             "blob_sha": _blob_sha(builder_path) if builder_path.exists() else None,
                             "commit": map_commit, "function": "membership_dated",
                             "windows": "engine.group_breadth_history.assign_groups (start_date <= d < end_date)"},
        "inputs": [
            {"path": MEMBERSHIP_REL, "blob_sha": _blob_sha(breadth_dir / "sp1500_pit_membership.parquet"),
             "commit": map_commit},
            {"path": SECTORS_REL, "blob_sha": _blob_sha(breadth_dir / "sp1500_pit_sectors.parquet"),
             "commit": map_commit},
        ],
        "calendar": {"path": CALENDAR_REL, "blob_sha": _blob_sha(dated_breadth),
                     "commit": calendar_commit, "n_sessions": int(len(calendar)),
                     "first": str(calendar.min().date()), "last": str(calendar.max().date()),
                     "source": "session_date values of the dated sp500 breadth parquet (no prices read)"},
        "srcs_included": srcs,
        "srcs_excluded": excluded,
        "sp400_sp600_note": ("sp400 and sp600 are included when the same sp1500 sector map labels "
                             "their members; unlabeled members are counted under 'unmapped'."),
        "groups": groups + [UNMAPPED],
        "rows": int(len(cov)),
        "span": {"first": str(calendar.min().date()), "last": str(calendar.max().date())},
        "house_registry_sizes": {
            "note": HOUSE_NOTE,
            "baskets": {"source": BASKETS_REL, "commit": baskets_commit,
                        "rule": "active members (a member with a 'removed' date is excluded)",
                        "blob_sha": _blob_sha(registry_json), "sizes": basket_sizes},
            "families": {"source": REGISTRY_REL, "commit": families_commit,
                         "sizes": family_sizes, "blobs": family_blobs},
        },
        "build_time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "not_an_outcome_claim": "Data only. No forward return, hit rate or backtest is attached.",
    }
    # Publish only after the whole build passes: the parquet first, then the
    # sidecar, each through a temp file in the same directory + os.replace.
    out.mkdir(parents=True, exist_ok=True)
    _atomic_write(out / "coverage_listed_dated.parquet",
                  lambda p: cov.to_parquet(p, index=False, compression="zstd"))
    _atomic_write(out / "coverage_listed.meta.json",
                  lambda p: p.write_text(json.dumps(meta, indent=2) + "\n"))
    return meta


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--breadth-dir", type=Path, default=Path("data/breadth"))
    ap.add_argument("--dated-breadth", type=Path,
                    default=Path("data/breadth/history/group_breadth_daily_dated_sp500.parquet"))
    ap.add_argument("--registry-json", type=Path, default=Path("data/baskets/membership.json"))
    ap.add_argument("--registry-dir", type=Path, default=Path("data/breadth/history/registry"))
    ap.add_argument("--out", type=Path, default=Path("data/breadth/history"))
    ap.add_argument("--map-commit", required=True)
    ap.add_argument("--baskets-commit", required=True)
    ap.add_argument("--families-commit", required=True)
    ap.add_argument("--calendar-commit", required=True)
    a = ap.parse_args()
    meta = build(a.breadth_dir, a.dated_breadth, a.registry_json, a.registry_dir, a.out,
                 a.map_commit, a.baskets_commit, a.families_commit, a.calendar_commit)
    print(json.dumps({k: meta[k] for k in ("rows", "span", "srcs_included", "srcs_excluded",
                                           "groups", "counts_only")}, indent=2))


if __name__ == "__main__":
    main()
