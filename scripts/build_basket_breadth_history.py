"""Build the reconstructed within-basket breadth history for US themes/baskets.

Off the render path. Runs the SAME functions as the sector history
(``engine.group_breadth_history``) over a stored closes matrix and the US
basket roster (``data/baskets/membership.json``, suite ``baskets``), and writes:

  <out>/basket_breadth_daily_current.parquet    (date, group) levels/changes/ranks/states
  <out>/basket_breadth_weekly_current.parquet   weekly fixed-set 13w/26w change
  <out>/basket_breadth_current.meta.json        protocol §4.4 sidecar

Basis: ``reconstructed_current_membership`` only. The US basket history
(``membership_history.parquet``) starts 2026-08-13, so today's active roster is
applied to every past session; a name that left a basket, or a company that no
longer trades, is absent throughout.

A ticker in several baskets counts in each (the engine assigns one group per
column, so each (ticker, basket) pair gets its own column here). Ranks are
across baskets; overlapping baskets are not independent.

No forward returns, no outcome relation, no threshold.

Usage:
  python -m scripts.build_basket_breadth_history --closes <off-git closes.parquet> \
      --membership data/baskets/membership.json --out data/breadth/history
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import pandas as pd  # noqa: E402

from engine import group_breadth_history as gbh  # noqa: E402
from scripts.build_group_breadth_history import (_code_version, _sha,  # noqa: E402
                                                 count_duplicates_once, drop_partial_rows,
                                                 duplicate_series_pairs)

BASIS = "reconstructed_current_membership"
_SEP = "@"


def membership_baskets(path: Path) -> pd.DataFrame:
    """Today's active US basket roster as (ticker, group=basket id)."""
    doc = json.loads(Path(path).read_text())
    rows = [{"ticker": m["ticker"], "group": bid}
            for bid, b in doc["baskets"].items() for m in b["members"] if not m.get("removed")]
    return pd.DataFrame(rows, columns=["ticker", "group"]).drop_duplicates()


def expand_multi(closes: pd.DataFrame, mem: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One column per (ticker, basket) so a name counts in every basket it belongs to."""
    m = mem[mem["ticker"].isin(closes.columns)]
    keys = (m["ticker"] + _SEP + m["group"]).tolist()
    wide = pd.concat({k: closes[t] for k, t in zip(keys, m["ticker"])}, axis=1) if keys \
        else pd.DataFrame(index=closes.index)
    return wide, pd.DataFrame({"ticker": keys, "group": m["group"].tolist()})


def build(closes_path: Path, membership_path: Path, out: Path, closes_label: str | None = None) -> dict:
    closes, dropped_rows = drop_partial_rows(pd.read_parquet(closes_path).sort_index())
    mem = membership_baskets(membership_path)
    names = mem.drop_duplicates("ticker").assign(group="all")
    dup_pairs = duplicate_series_pairs(closes, names)
    closes = count_duplicates_once(closes, dup_pairs)
    wide, emem = expand_multi(closes, mem)
    daily = gbh.daily_group_breadth(wide, emem, groups=sorted(mem["group"].unique()))
    weekly = gbh.weekly_fixed_set(wide, emem, groups=sorted(mem["group"].unique()),
                                  include_last_partial_week=False)
    out.mkdir(parents=True, exist_ok=True)
    daily.to_parquet(out / "basket_breadth_daily_current.parquet", index=False, compression="zstd")
    weekly.to_parquet(out / "basket_breadth_weekly_current.parquet", index=False, compression="zstd")

    unpriced = sorted(set(mem["ticker"]) - set(closes.columns))
    multi = int((mem.loc[mem["ticker"].isin(closes.columns), "ticker"].value_counts() > 1).sum())
    valid = daily.dropna(subset=["pct_above_200"])
    first_valid = valid.groupby("group")["date"].min()
    last = daily[daily["date"] == daily["date"].max()]
    never = sorted(set(mem["group"]) - set(first_valid.index))
    sentence = (f"Only today's active basket members are present; {len(unpriced)} of "
                f"{mem['ticker'].nunique()} names have no stored close and are absent "
                f"({', '.join(unpriced)}). {multi} priced names sit in more than one basket and count in each. "
                f"{len(never)} of {mem['group'].nunique()} baskets never reach {gbh.MIN_MEMBERS} members "
                f"with a 200-session history and are missing throughout ({', '.join(never)}).")
    if len(dup_pairs):
        sentence += (f" {len(dup_pairs)} ticker pair(s) carry the same price series and are counted once: "
                     + "; ".join(f"{p.ticker_a}={p.ticker_b} {p.identical_from}..{p.identical_to}"
                                 for p in dup_pairs.itertuples(index=False)) + ".")
    else:
        sentence += " Duplicate-series scan: no two basket tickers carry the same price series."
    meta = {
        "basis": BASIS,
        "price_note": ("Adjusted closes are today's restated values (split and dividend adjustment "
                       "as of the store's capture), not the prices printed at the time."),
        "redistribution_note": ("Basket-level shares and counts only; no member prices. Member-level "
                                "closes stay off git."),
        "span": {"closes_start": str(closes.index.min().date()),
                 "closes_end": str(closes.index.max().date()),
                 "first_valid_pct_above_200": str(valid["date"].min().date()) if len(valid) else None},
        "first_valid_by_basket": {g: str(d.date()) for g, d in first_valid.sort_values().items()},
        "valid_on_last_session": int(last["pct_above_200"].notna().sum()),
        "build_time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "code_version": _code_version(),
        "engine": "engine/group_breadth_history.py",
        "inputs": [{"path": str(p), "sha256_16": _sha(p)} for p in (closes_path, membership_path)],
        "closes_store": closes_label or str(closes_path),
        "missing": sentence,
        "coverage": {"baskets": int(mem["group"].nunique()), "member_rows": len(mem),
                     "names": int(mem["ticker"].nunique()), "names_unpriced": unpriced,
                     "names_in_several_baskets": multi, "baskets_never_valid": never},
        "dropped_partial_rows": dropped_rows,
        "duplicate_series_pairs": dup_pairs.to_dict("records"),
        "overlap_note": "Baskets share members; ranks across baskets are not across independent groups.",
        "rules": {"windows": list(gbh.WINDOWS), "horizons_sessions": list(gbh.HORIZONS),
                  "horizons_weeks": list(gbh.WEEKLY_HORIZONS), "min_members": gbh.MIN_MEMBERS,
                  "headline": gbh.HEADLINE},
        "rows": {"daily": len(daily), "weekly": len(weekly)},
        "not_an_outcome_claim": "Data only. No forward return, hit rate or backtest is attached.",
    }
    (out / "basket_breadth_current.meta.json").write_text(json.dumps(meta, indent=2, default=str) + "\n")
    return meta


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--closes", type=Path, required=True)
    ap.add_argument("--membership", type=Path, default=Path("data/baskets/membership.json"))
    ap.add_argument("--out", type=Path, default=Path("data/breadth/history"))
    ap.add_argument("--closes-label", default=None)
    a = ap.parse_args()
    meta = build(a.closes, a.membership, a.out, a.closes_label)
    print(json.dumps({k: meta[k] for k in ("basis", "span", "rows", "valid_on_last_session")}, indent=2))


if __name__ == "__main__":
    main()
