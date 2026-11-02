"""S&P 1500 point-in-time sector substrate (Trend Persistence Wave C-0).

One row per ticker that has EVER appeared in
``data/breadth/sp1500_pit_membership.parquet`` (current members + LEAVERS),
carrying the best available 11-sector label plus an honest ``basis``.

AS-OF-NOW CAVEAT (load-bearing): no channel in this repo supplies the
membership-ERA GICS sector.  Every label this collector emits is as-of-now:
either the CURRENT GICS map (``ticker_sectors.parquet``) or the filer's
CURRENT SEC SIC mapped to GICS-style sectors.  ``era_correct`` is therefore a
constant ``False`` column and the receipt records ``era_correct_count == 0`` so
a downstream join cannot mistake these labels for membership-era sectors.

Channel priority per ticker (first hit wins):
  1. ``ticker_sectors.parquet``   gics_*      -> basis ``gics_current``
                                  sic_mapped  -> basis ``sic_current``
  2. CIK bridge (``dead_name_cik.json``) -> SIC from ``cik_sic.json`` (read
     only), else this collector's own cache, else a bounded SEC submissions
     lookup -> basis ``sic_derived``.  The SIC is mapped TEXT FIRST
     (``sic_desc`` via the build_sector_map text table), numeric SIC range as
     the fallback -- the same order as ``scripts/build_sector_map.py``
     (``_load_sic_numeric``: "text map is more precise").
  3. ``profiles.parquet`` ``sic_description`` -> text map -> ``sic_derived``
  4. otherwise ``unlabeled`` with a NULL sector.

LEAVERS ARE CIK-ONLY (load-bearing, seat ruling 2026-10-04): channels 1 and 3
match by TICKER STRING only.  A leaver has no open membership row, so its ticker
string appearing in the CURRENT constituents / profile universe means the ticker
is held today by a DIFFERENT listing (ECHO = Echo Global Logistics as an sp600
leaver vs EchoStar now).  For the same reason a leaver's CIK is trusted ONLY when
``dead_name_cik.json`` resolved it by ``edgar_fts`` or ``seed`` (historical filer
lookups); ``company_tickers`` / ``polygon`` look the ticker up in the CURRENT map and
return today's holder, so such a leaver stays unlabeled (the raw cik is kept on the row,
``cik_method`` NULL, and counted in the receipt as ``leavers_cik_untrusted_method``).
Therefore channels 1 and 3 are NEVER consulted for a
leaver: a leaver is labeled ONLY through the CIK bridge (channel 2,
``label_join='cik'``) and otherwise stays ``unlabeled``.  Current members keep
channels 1 -> 2 -> 3.  The nullable ``label_join`` column records HOW each label
was joined: ``ticker`` (channels 1/3, current members only), ``cik`` (channel 2),
NULL for unlabeled rows.  The receipt key ``leavers_labeled_by_ticker_string`` is
kept as an invariant and is 0 by construction.

When the CIK bridge finds a SIC/description that neither map can turn into a
sector, ``sic`` / ``sic_desc`` are still populated on the (unlabeled) row so a
downstream reader can see why.

Artifacts (under data_dir/breadth/):
  sp1500_pit_sectors.parquet            the per-ticker frame
  _sp1500_pit_sectors_coverage.json     the coverage receipt
  _sp1500_pit_sic_cache.json            own SIC cache (only writer: this module)

``data/edgar/cik_sic.json`` is owned by ``collectors/edgar_emergence.py`` and is
NEVER written here.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd

from collectors import edgar_delisting as _edgar_delisting
from collectors._first_seen_store import atomic_write
from scripts.build_sector_map import _SIC_TEXT_MAP, _sic_range_to_sector

VALID_SECTORS = frozenset({
    "Communication Services",
    "Consumer Discretionary",
    "Consumer Staples",
    "Energy",
    "Financials",
    "Health Care",
    "Industrials",
    "Information Technology",
    "Materials",
    "Real Estate",
    "Utilities",
})
BASES = ("gics_current", "sic_current", "sic_derived", "unlabeled")
COLUMNS = [
    "ticker", "is_leaver", "membership_start", "membership_end", "sector", "basis",
    "sic", "sic_desc", "cik", "cik_method", "label_join", "label_asof", "era_correct",
]
LABEL_JOINS = ("ticker", "cik")
NOTE = ("All labels are as-of-now (current GICS map or the filer's CURRENT SEC SIC "
        "mapped to GICS-style sectors). None is the membership-era GICS sector; "
        "era_correct is False for every row. Leavers are labeled through the filer "
        "CIK bridge only (label_join='cik'); ticker-string channels are never "
        "consulted for a leaver because the ticker may now belong to a different "
        "listing (ticker reuse), and a leaver CIK is bridged only when resolved by "
        "edgar_fts or seed (never a current-map lookup). label_join='ticker' appears only "
        "on current members and is matched by ticker string alone.")
# dead_name_cik methods that resolve the CIK of the company that WAS the leaver.  Any other
# method (company_tickers / polygon: a lookup of the ticker in the CURRENT map) returns the
# CURRENT holder of the ticker string, i.e. the ticker-reuse failure mode.
LEAVER_TRUSTED_CIK_METHODS = ("edgar_fts", "seed")
_SLEEP_S = 0.12


class MissingInputError(FileNotFoundError):
    """A REQUIRED input is absent."""


def _get_submissions(cik: int) -> dict | None:
    """Thin indirection over collectors.edgar_delisting._get_submissions."""
    return _edgar_delisting._get_submissions(cik)


# --------------------------------------------------------------------------- #
# input loaders (every optional input -> empty on absence/corruption)
# --------------------------------------------------------------------------- #
def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text())
    except Exception:  # noqa: BLE001 — optional input, treat as empty
        return {}
    return obj if isinstance(obj, dict) else {}


def _load_ticker_sectors(path: Path) -> dict[str, tuple[str, str]]:
    if not path.exists():
        return {}
    try:
        df = pd.read_parquet(path)
        if "ticker" not in df.columns:
            df = df.reset_index().rename(columns={df.index.name or "index": "ticker"})
    except Exception:  # noqa: BLE001
        return {}
    out: dict[str, tuple[str, str]] = {}
    for t, sec, src in zip(df["ticker"], df.get("sector"), df.get("source"), strict=False):
        if pd.notna(sec) and str(sec).strip() and pd.notna(src):
            out.setdefault(str(t), (str(sec), str(src)))
    return out


def _load_profile_desc(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        df = pd.read_parquet(path, columns=["sic_description"])
    except Exception:  # noqa: BLE001
        return {}
    out: dict[str, str] = {}
    for t, desc in zip(df.index, df["sic_description"], strict=False):
        if pd.notna(desc) and str(desc).strip():
            out[str(t)] = str(desc)
    return out


def _norm_cik(cik) -> str | None:
    try:
        return f"{int(cik):010d}"
    except (TypeError, ValueError):
        return None


def _clean_sic(sic) -> int | None:
    try:
        s = str(sic).strip()
        return int(float(s)) if s and s.lower() not in ("none", "nan") else None
    except (TypeError, ValueError, OverflowError):
        return None


def _map_sic(sic: int | None, desc: str | None) -> str | None:
    """Text map FIRST, numeric SIC range as the fallback.

    Mirrors scripts/build_sector_map.py:_load_sic_numeric ("text map is more
    precise than numeric range").
    """
    sector = _SIC_TEXT_MAP.get(desc) if desc else None
    if sector is None and sic is not None:
        sector = _sic_range_to_sector(sic)
    return sector


def _atomic_json(obj: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(json.dumps(obj, indent=2, sort_keys=True))
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


# --------------------------------------------------------------------------- #
# build
# --------------------------------------------------------------------------- #
def build(data_dir: Path | None = None, *, network: bool = True, max_lookups: int = 400,
          today: date | None = None) -> tuple[pd.DataFrame, dict]:
    """Build and write the sector substrate. Returns (frame, receipt)."""
    if data_dir is None:
        from lib import config
        data_dir = config.data_dir()
    data_dir = Path(data_dir)
    today = today or datetime.now(UTC).date()

    mem_path = data_dir / "breadth" / "sp1500_pit_membership.parquet"
    if not mem_path.exists():
        raise MissingInputError(f"required input missing: {mem_path}")
    mem = pd.read_parquet(mem_path)
    if len(mem) == 0:
        raise MissingInputError(f"required input has zero rows: {mem_path}")
    # pandas 3 keeps NaN through astype(str) and groupby drops NaN keys, so a null
    # ticker would vanish silently; drop it explicitly and count it in the receipt.
    null_ticker_rows = int(mem["ticker"].isna().sum())
    mem = mem[mem["ticker"].notna()].copy()
    mem["ticker"] = mem["ticker"].astype(str)
    if mem.empty:
        raise MissingInputError(f"required input has no usable ticker rows: {mem_path}")
    grp = mem.groupby("ticker").agg(
        membership_start=("start_date", "min"),
        membership_end=("end_date", "max"),
        _open=("end_date", lambda s: bool(s.isna().any())),
    )
    grp["is_leaver"] = ~grp["_open"].astype(bool)
    # a CURRENT ticker has no end: membership_end is NaT regardless of older closed rows
    grp.loc[grp["_open"], "membership_end"] = pd.NaT
    if grp.empty:
        raise MissingInputError(f"required input has no usable ticker rows: {mem_path}")

    gics = _load_ticker_sectors(data_dir / "breadth" / "ticker_sectors.parquet")
    dead = _read_json(data_dir / "edgar" / "dead_name_cik.json")
    cik_sic = _read_json(data_dir / "edgar" / "cik_sic.json")
    prof = _load_profile_desc(data_dir / "profile" / "profiles.parquet")
    cache_path = data_dir / "breadth" / "_sp1500_pit_sic_cache.json"
    cache = _read_json(cache_path)

    lookups = skipped = blank_fetch = failed = 0
    cache_dirty = False
    leavers_sic_on_disk = 0
    untrusted_cik = 0
    rows: list[dict] = []
    for ticker in sorted(grp.index):
        g = grp.loc[ticker]
        row = {
            "ticker": ticker, "is_leaver": bool(g["is_leaver"]),
            "membership_start": g["membership_start"], "membership_end": g["membership_end"],
            "sector": None, "basis": "unlabeled", "sic": None, "sic_desc": None,
            "cik": None, "cik_method": None, "label_join": None,
        }
        d = dead.get(ticker)
        cik = None
        if isinstance(d, dict):
            cik = _norm_cik(d.get("cik"))
            if cik is not None and d.get("method") in LEAVER_TRUSTED_CIK_METHODS:
                row["cik"], row["cik_method"] = cik, d["method"]
            elif cik is not None:
                row["cik"] = cik
                if row["is_leaver"]:
                    # current-map lookup (company_tickers/polygon): today's holder of the
                    # ticker string, NOT the leaver -- never bridge it
                    untrusted_cik += 1
                    cik = None

        disk = cik_sic.get(cik) if cik else None
        disk_has_sic = isinstance(disk, dict) and _clean_sic(disk.get("sic")) is not None
        if row["is_leaver"] and disk_has_sic:
            leavers_sic_on_disk += 1

        # 1. current GICS / SIC-mapped ticker map (ticker-string join: current members only --
        #    a leaver's ticker string may now belong to a different listing)
        hit = None if row["is_leaver"] else gics.get(ticker)
        if hit is not None and hit[1].startswith("gics_"):
            row["sector"], row["basis"] = hit[0], "gics_current"
            row["label_join"] = "ticker"
        elif hit is not None and hit[1] == "sic_mapped":
            row["sector"], row["basis"] = hit[0], "sic_current"
            row["label_join"] = "ticker"
        else:
            # 2. CIK bridge
            if cik is not None:
                src = None
                if isinstance(disk, dict) and (_clean_sic(disk.get("sic")) is not None
                                               or disk.get("sic_desc")):
                    src = disk
                elif cik in cache:
                    src = cache[cik]
                elif network and lookups < max_lookups:
                    lookups += 1
                    sub = _get_submissions(int(cik))
                    time.sleep(_SLEEP_S)
                    if isinstance(sub, dict):
                        sic_s = str(sub.get("sic") or "").strip()
                        src = {"sic": sic_s or None,
                               "sic_desc": sub.get("sicDescription") or None,
                               "name": sub.get("name") or None,
                               "fetched_at": datetime.now(UTC).isoformat()}
                        cache[cik] = src          # a BLANK sic is cached too
                        cache_dirty = True
                        if not sic_s:
                            blank_fetch += 1
                    else:
                        failed += 1               # not cached: retried next run
                elif network:
                    skipped += 1
                if src is not None:
                    sic = _clean_sic(src.get("sic"))
                    desc = src.get("sic_desc") or None
                    # known SIC/desc is recorded even when unmappable, so Wave C can see why
                    row.update(sic=sic, sic_desc=desc)
                    sector = _map_sic(sic, desc)
                    if sector is not None:
                        row.update(sector=sector, basis="sic_derived", label_join="cik")
            # 3. profiles sic_description (ticker-string join: current members only)
            if row["sector"] is None and not row["is_leaver"] and ticker in prof:
                sector = _SIC_TEXT_MAP.get(prof[ticker])
                if sector is not None:
                    row.update(sector=sector, basis="sic_derived", sic=None,
                               sic_desc=prof[ticker], label_join="ticker")
        rows.append(row)

    if cache_dirty:
        _atomic_json(cache, cache_path)   # raw fetched data is worth keeping regardless

    frame = pd.DataFrame(rows, columns=[c for c in COLUMNS if c not in ("label_asof", "era_correct")])
    bad = sorted({s for s in frame["sector"].dropna() if s not in VALID_SECTORS})
    if bad:
        raise ValueError(f"sector label(s) outside the 11-sector vocabulary: {bad}")
    frame["membership_start"] = pd.to_datetime(frame["membership_start"])
    frame["membership_end"] = pd.to_datetime(frame["membership_end"])
    frame["sic"] = pd.array(frame["sic"], dtype="Int64")
    frame["label_asof"] = pd.Timestamp(today)
    frame["era_correct"] = False
    frame = frame[COLUMNS].reset_index(drop=True)

    out_dir = data_dir / "breadth"
    atomic_write(frame, out_dir / "sp1500_pit_sectors.parquet")

    lv = frame[frame["is_leaver"].astype(bool)]
    counts_all = {b: int((frame["basis"] == b).sum()) for b in BASES}
    counts_lv = {b: int((lv["basis"] == b).sum()) for b in BASES}
    joins_all = {j: int((frame["label_join"] == j).sum()) for j in LABEL_JOINS}
    joins_lv = {j: int((lv["label_join"] == j).sum()) for j in LABEL_JOINS}
    receipt = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "label_asof": today.isoformat(),
        "denominator_all": len(frame),
        "denominator_leavers": len(lv),
        "membership_rows_null_ticker_dropped": null_ticker_rows,
        "basis_counts_all": counts_all,
        "basis_counts_leavers": counts_lv,
        "leavers_with_cik": int(lv["cik"].notna().sum()),
        "leavers_cik_untrusted_method": untrusted_cik,
        "leavers_labeled_by_ticker_string": joins_lv["ticker"],
        "leavers_labeled_by_cik": joins_lv["cik"],
        "labeled_by_ticker_string_all": joins_all["ticker"],
        "labeled_by_cik_all": joins_all["cik"],
        "leavers_sic_on_disk_before_run": int(leavers_sic_on_disk),
        "network_lookups_performed": lookups,
        "network_lookups_failed": failed,
        "network_lookups_skipped_cap": skipped,
        "network_disabled": not network,
        "sic_blank_after_fetch": blank_fetch,
        "unlabeled_leavers": counts_lv["unlabeled"],
        "era_correct_count": int(frame["era_correct"].sum()),
        "note": NOTE,
    }
    _atomic_json(receipt, out_dir / "_sp1500_pit_sectors_coverage.json")

    n = len(lv) - counts_lv["unlabeled"]
    print(f"::notice title=sp1500-pit-sectors::leavers labeled {n}/{len(lv)} "
          f"(gics_current {counts_lv['gics_current']}, sic_current {counts_lv['sic_current']}, "
          f"sic_derived {counts_lv['sic_derived']}, unlabeled {counts_lv['unlabeled']}); "
          f"era_correct=0", flush=True)
    return frame, receipt


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--no-network", action="store_true", help="skip SEC submissions lookups")
    ap.add_argument("--max-lookups", type=int, default=400)
    ap.add_argument("--data-dir", type=Path, default=None)
    args = ap.parse_args(argv)
    try:
        build(args.data_dir, network=not args.no_network, max_lookups=args.max_lookups)
    except MissingInputError as e:
        print(f"sp1500_pit_sectors: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
