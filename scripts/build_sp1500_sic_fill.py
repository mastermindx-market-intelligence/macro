"""Free SIC label fill for unlabeled S&P 1500 ever-members (off the render path).

Extends the existing SIC-derived labels in ``data/breadth/sp1500_pit_sectors.parquet``
for rows it leaves ``unlabeled`` (almost all index leavers), using only free
sources and no hand labelling:

  1. Tiingo fundamentals metadata (the archive's ``fund-meta`` capture): the
     company name the vendor holds under the ticker.
  2. SEC EDGAR ``cik-lookup-data.txt`` (public): that name -> CIK.
  3. SEC EDGAR submissions (public, via ``collectors.edgar_delisting``): CIK ->
     SIC code and description -> sector, with the SAME mapping as the existing
     collector (``collectors.sp1500_pit_sectors._map_sic``: text map first,
     numeric range second).

A row is filled only when every link is unambiguous:
  * the ticker has exactly ONE company in the Tiingo metadata;
  * the ticker's Tiingo price series starts on or before the membership start
    (+10 days). This screens out a ticker whose vendor history begins only after
    the membership (a later holder) but does NOT prove identity: a vendor may
    attach a predecessor's history to today's ticker;
  * the ticker has no handover inside one index (two windows in the same index
    within 5 days of each other): a split window under one ticker can mark a
    change of company (GAS: Nicor until 2011-12-12, AGL Resources after);
  * the normalized name maps to exactly ONE CIK in the SEC lookup;
  * the SEC SIC maps to one of the 11 sectors.

Leaver rule (collectors/sp1500_pit_sectors.py, seat ruling 2026-10-04): leavers
are labelled by CIK only, never by matching today's ticker universe. This fill
reaches the CIK through the vendor's ticker -> company-name record, which covers
inactive companies; it is a ticker-keyed route to a CIK and is disclosed as such.
Hand review of all 228 first-run fills found 1 plainly wrong company and about 6
earlier or later filers of the same company family (research/breadth_history/
LABEL_COVERAGE.md).

Every label written here is ``basis = sic_derived_fill``, as of now (the
filer's CURRENT SIC), ``era_correct = False``. The output is a separate overlay
file; the existing substrate and its readers are unchanged. Tiingo names are
used only as a join key and are not written out.

Usage:
  python -m scripts.build_sp1500_sic_fill --breadth-dir data/breadth \
      --fund-meta <tiingo raw fund-meta .raw.gz> --closes <off-git closes.parquet> \
      --sec-lookup <cik-lookup-data.txt> --cache <json> --out data/breadth/sp1500_pit_sectors_sic_fill.parquet
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import pandas as pd  # noqa: E402

from collectors.sp1500_pit_sectors import VALID_SECTORS, _clean_sic, _get_submissions, _map_sic  # noqa: E402

BASIS = "sic_derived_fill"
COLUMNS = ["ticker", "cik", "sec_name", "sic", "sic_desc", "sector", "basis", "label_join",
           "label_asof", "era_correct"]
_SUFFIX = re.compile(r"\b(INC|CORP|CORPORATION|CO|COMPANY|LTD|PLC|LP|THE|HOLDINGS?|GROUP|"
                     r"CLASS A|CL A|NEW|DEL)\b")


def norm_name(name: str) -> str:
    n = re.sub(r"[^A-Z0-9 ]", " ", str(name).upper())
    return " ".join(_SUFFIX.sub(" ", n).split())


def load_fund_meta(path: Path) -> pd.DataFrame:
    md = pd.DataFrame(json.loads(gzip.open(path).read()))
    md["ticker"] = md["ticker"].str.upper()
    return md[["ticker", "name"]]


def load_sec_lookup(path: Path) -> dict[str, set[int]]:
    out: dict[str, set[int]] = {}
    for line in open(path, encoding="latin-1"):
        parts = line.rstrip("\n").rsplit(":", 2)
        if len(parts) == 3 and parts[0]:
            try:
                out.setdefault(norm_name(parts[0]), set()).add(int(parts[1]))
            except ValueError:
                continue
    return out


def series_covers(closes: pd.DataFrame, ticker: str, start) -> bool:
    if ticker not in closes.columns:
        return False
    x = closes[ticker].dropna()
    return len(x) > 0 and x.index.min() <= pd.Timestamp(start) + pd.Timedelta(days=10)


def handover_tickers(membership: pd.DataFrame | None, gap_days: int = 5) -> set[str]:
    """Tickers with two windows in the same index within ``gap_days``: a possible
    change of company under one ticker."""
    if membership is None or membership.empty:
        return set()
    m = membership.sort_values(["ticker", "src", "start_date"])
    prev_end = m.groupby(["ticker", "src"])["end_date"].shift()
    near = (m["start_date"] - prev_end).dt.days.abs() <= gap_days
    return set(m.loc[near.fillna(False), "ticker"])


def candidates(sectors: pd.DataFrame, meta: pd.DataFrame, closes: pd.DataFrame,
               lookup: dict[str, set[int]],
               membership: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    """Unlabeled rows whose ticker -> name -> CIK chain is unambiguous."""
    u = sectors[sectors["basis"] == "unlabeled"]
    n_meta = meta["ticker"].value_counts()
    one = u[u["ticker"].map(n_meta).eq(1)]
    cov = one[[series_covers(closes, r.ticker, r.membership_start) for r in one.itertuples()]]
    cov = cov[~cov["ticker"].isin(handover_tickers(membership))]
    j = cov.merge(meta, on="ticker")
    j["ciks"] = j["name"].map(lambda n: lookup.get(norm_name(n), set()))
    ok = j[j["ciks"].map(len) == 1].copy()
    ok["cik"] = ok["ciks"].map(lambda s: next(iter(s)))
    funnel = {"unlabeled": len(u), "one_tiingo_company": len(one), "series_covers_window_no_handover": len(cov),
              "one_sec_cik": len(ok)}
    return ok[["ticker", "cik"]], funnel


def resolve_sic(ciks, cache: dict, cik_sic: dict, sleep_s: float = 0.12) -> dict:
    """CIK -> {sic, sic_desc, name}; reads cik_sic.json and the cache before SEC."""
    for cik in ciks:
        key = f"{int(cik):010d}"
        if key in cache:
            continue
        hit = cik_sic.get(key)
        if isinstance(hit, dict) and hit.get("sic"):
            cache[key] = {"sic": hit.get("sic"), "sic_desc": hit.get("sic_desc"), "name": hit.get("name")}
            continue
        sub = _get_submissions(int(cik))
        time.sleep(sleep_s)
        cache[key] = ({"sic": sub.get("sic"), "sic_desc": sub.get("sicDescription"), "name": sub.get("name")}
                      if sub else {})
    return cache


def build(breadth_dir: Path, fund_meta: Path, closes_path: Path, sec_lookup: Path, cache_path: Path,
          out: Path, cik_sic_path: Path | None = None) -> dict:
    sectors = pd.read_parquet(breadth_dir / "sp1500_pit_sectors.parquet")
    closes = pd.read_parquet(closes_path)
    membership = pd.read_parquet(breadth_dir / "sp1500_pit_membership.parquet")
    cand, funnel = candidates(sectors, load_fund_meta(fund_meta), closes, load_sec_lookup(sec_lookup),
                              membership)
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    cik_sic = json.loads(cik_sic_path.read_text()) if cik_sic_path and cik_sic_path.exists() else {}
    cache = resolve_sic(cand["cik"], cache, cik_sic)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=1, sort_keys=True))
    asof = datetime.now(UTC).date().isoformat()
    rows = []
    for r in cand.itertuples():
        h = cache.get(f"{int(r.cik):010d}") or {}
        sic, desc = _clean_sic(h.get("sic")), h.get("sic_desc")
        sector = _map_sic(sic, desc)
        if sector in VALID_SECTORS:
            rows.append({"ticker": r.ticker, "cik": f"{int(r.cik):010d}", "sec_name": h.get("name"),
                         "sic": sic, "sic_desc": desc, "sector": sector, "basis": BASIS,
                         "label_join": "tiingo_name_sec_cik", "label_asof": asof, "era_correct": False})
    fill = pd.DataFrame(rows, columns=COLUMNS)
    out.parent.mkdir(parents=True, exist_ok=True)
    fill.to_parquet(out, index=False)
    funnel["filled"] = len(fill)
    return funnel


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--breadth-dir", type=Path, default=Path("data/breadth"))
    ap.add_argument("--fund-meta", type=Path, required=True)
    ap.add_argument("--closes", type=Path, required=True)
    ap.add_argument("--sec-lookup", type=Path, required=True)
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--cik-sic", type=Path, default=Path("data/edgar/cik_sic.json"))
    ap.add_argument("--out", type=Path, default=Path("data/breadth/sp1500_pit_sectors_sic_fill.parquet"))
    a = ap.parse_args()
    print(json.dumps(build(a.breadth_dir, a.fund_meta, a.closes, a.sec_lookup, a.cache, a.out, a.cik_sic),
                     indent=2))


if __name__ == "__main__":
    main()
