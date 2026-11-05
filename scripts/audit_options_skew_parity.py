"""Methodology-parity audit: why legacy polygon_gex skew disagrees with ThetaData.

The two paths use the same formula (engine.options_skew.compute_skew). This
script does not change that formula. It reads a ledger parquet and a local
ThetaData store, classifies every legacy polygon_gex key the store cannot
price, and recomputes the keys both sides can price.

Classification (first match wins), from the store directory and parquet
files only — never the network:

  weekend_date
      The ledger date falls on Saturday or Sunday.
  root_not_in_store
      There is no eod/<ROOT> directory in the store.
  date_not_in_store_for_root
      The root directory exists, but that calendar day is not in the
      eod/<ROOT>/<YEAR>.parquet file (or the year file is absent).
  no_usable_tenor
      The store has the day, but every contract is expired or same-day,
      so compute_skew has no live expiry.
  other
      The store has the day, but the recompute still cannot price it
      (no IV, no put, no call, a mismatched as-of, or an unreadable file).
  compared
      Both sides priced the key.

For compared keys the skew gap is
    legacy skew − new skew
  = (legacy put IV − new put IV) − (legacy call IV − new call IV).

The receipt assigns each key's absolute gap to one explanation, in order:
a tenor mismatch (the tenors differ by more than 5 days), otherwise a spot
mismatch (the spots differ by more than 2 percent), otherwise whichever IV
leg moved more. Those four shares add up to the whole absolute gap.

Run:
  python -m scripts.audit_options_skew_parity [--ledger PATH] [--store PATH]
                                               [--limit N] [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path

# Repo-root pin. This must be the first sys.path mutation in the file.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_READ = 3
EXIT_UNRECONCILED = 4

LEGACY_SOURCE = "polygon_gex"
INDEX_ETFS = frozenset({"SPY", "QQQ", "IWM", "DIA"})
SAMPLE_SEED = 20260923
TENOR_MISMATCH_DAYS = 5.0
SPOT_MISMATCH_RATIO = 0.02
DEFAULT_LEDGER = "data/options_skew/snapshots.parquet"
DEFAULT_STORE = "/Users/chriswong/theta-ops-wt/data/thetadata_eod"

CLASS_ORDER = (
    "weekend_date",
    "root_not_in_store",
    "date_not_in_store_for_root",
    "no_usable_tenor",
    "other",
    "compared",
)
SIGN_BUCKETS = ("match", "flip", "zero")
EXPLAIN_ORDER = ("put", "call", "tenor", "spot")
CHOSEN_K_KEYS = (
    "otm_put_k",
    "atm_call_k",
    "put_k",
    "call_k",
    "otm_put_strike",
    "atm_call_strike",
)


def is_weekend_date(date_iso: str) -> bool:
    """True when the calendar day is Saturday or Sunday. A bad date is not a weekend."""
    try:
        year, month, day = (int(part) for part in str(date_iso)[:10].split("-"))
        return date(year, month, day).weekday() >= 5
    except (TypeError, ValueError):
        return False


def underlying_class(symbol: str) -> str:
    """Index ETF (SPY, QQQ, IWM, DIA) or a single name. Everything else is a single name."""
    if str(symbol).strip().upper() in INDEX_ETFS:
        return "index_etf"
    return "single_name"


def is_legacy_source(value) -> bool:
    """A blank or missing source is the legacy polygon ledger. thetadata is not."""
    if value is None:
        return True
    try:
        import pandas as pd
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if text in ("", "None", "nan", "NaN", "<NA>"):
        return True
    return text == LEGACY_SOURCE


def classify_key(
    date_iso: str,
    underlying: str,
    *,
    root_in_store: bool,
    date_in_store: bool,
    price_status: str | None,
) -> str:
    """Classify one legacy key. Weekend wins, then a missing root, then a missing date.

    Once the store has the root and the date, price_status must be compared,
    no_usable_tenor, or other. underlying is accepted so callers can pass the
    ledger symbol through one function; the store checks are the caller's.
    """
    del underlying  # the class does not depend on the symbol; the caller resolved the root
    if is_weekend_date(date_iso):
        return "weekend_date"
    if not root_in_store:
        return "root_not_in_store"
    if not date_in_store:
        return "date_not_in_store_for_root"
    if price_status not in ("compared", "no_usable_tenor", "other"):
        raise ValueError(
            "price_status must be compared, no_usable_tenor, or other "
            "when the store has this key"
        )
    return price_status


def tenor_is_unusable(chain) -> bool:
    """True when the chain has rows but none of them expire after today.

    This matches the branch in engine.options_skew._nearest_expiry that gives
    up when every year-fraction is zero. An empty chain is not this case.
    """
    if chain is None or getattr(chain, "empty", True) or "T" not in getattr(chain, "columns", []):
        return False
    import pandas as pd
    days = pd.to_numeric(chain["T"], errors="coerce") * 365.0
    return not bool((days > 0).fillna(False).any())


def tenor_mismatch(legacy_tenor: float, new_tenor: float, *, threshold: float = TENOR_MISMATCH_DAYS) -> bool:
    """True when the two tenors differ by more than 5 days. Exactly 5 is not a mismatch."""
    return abs(float(legacy_tenor) - float(new_tenor)) > threshold + 1e-9


def spot_mismatch(legacy_spot: float, new_spot: float, *, threshold: float = SPOT_MISMATCH_RATIO) -> bool:
    """True when the two spots differ by more than 2 percent of the legacy spot.

    A legacy spot of zero is a mismatch whenever the new spot is not zero.
    A difference of exactly 2 percent is not a mismatch. The small cushion
    keeps a binary-float 2 percent from counting as more than 2 percent.
    """
    legacy = float(legacy_spot)
    new = float(new_spot)
    if legacy == 0.0:
        return new != 0.0
    return abs(legacy - new) > threshold * abs(legacy) + 1e-9


def sign_bucket(legacy_skew: float, new_skew: float) -> str:
    """match, flip, or zero. The three buckets cover every finite pair.

    match: both non-zero and the same sign.
    flip: both non-zero and opposite signs.
    zero: at least one side is exactly zero (includes both zero).
    """
    product = float(legacy_skew) * float(new_skew)
    if product > 0.0:
        return "match"
    if product < 0.0:
        return "flip"
    return "zero"


def _finite(value) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def _nearest_rank(sorted_values: list[float], fraction: float) -> float | None:
    """Same nearest-rank percentile the overlap audit uses. Empty input is None."""
    if not sorted_values:
        return None
    index = int(round(fraction * (len(sorted_values) - 1)))
    index = max(0, min(len(sorted_values) - 1, index))
    return sorted_values[index]


def _abs_delta_stats(values: list[float]) -> dict[str, float | None]:
    ordered = sorted(abs(value) for value in values)
    return {
        "n": len(ordered),
        "p50": _nearest_rank(ordered, 0.50),
        "p90": _nearest_rank(ordered, 0.90),
        "max": ordered[-1] if ordered else None,
    }


def _round_shares(shares: dict[str, float]) -> dict[str, float | None]:
    """Round shares that add to 1. Put any 1e-6 rounding leftover on the largest share."""
    if not shares:
        return {}
    rounded = {key: round(value, 6) for key, value in shares.items()}
    drift = round(1.0 - sum(rounded.values()), 6)
    if drift != 0.0:
        key = max(rounded, key=lambda name: (rounded[name], name))
        rounded[key] = round(rounded[key] + drift, 6)
    return rounded


def _primary_explanation(record: dict) -> str:
    """tenor, else spot, else the IV leg with the larger absolute move. Ties go to the put."""
    if tenor_mismatch(record["legacy_tenor"], record["new_tenor"]):
        return "tenor"
    if spot_mismatch(record["legacy_spot"], record["new_spot"]):
        return "spot"
    put_move = abs(record["legacy_put"] - record["new_put"])
    call_move = abs(record["legacy_call"] - record["new_call"])
    if put_move >= call_move:
        return "put"
    return "call"


def decompose_compared(records: list[dict]) -> dict:
    """Split the compared skew gap into put, call, tenor, and spot.

    Each record needs legacy_skew, new_skew, legacy_put, new_put, legacy_call,
    new_call, legacy_tenor, new_tenor, legacy_spot, new_spot. The put and call
    fields are the 25-delta put IV and the 50-delta call IV.

    explained_share_* is the share of the total absolute skew gap assigned to
    that one explanation. The four shares add to 1 when any gap is non-zero,
    and are None when every gap is zero or there are no records.

    abs_put_movement_share and abs_call_movement_share are a second split:
    they divide the absolute IV movement, and they ignore tenor and spot.
    They also add to 1 when either leg moved.
    """
    empty_shares = {name: None for name in EXPLAIN_ORDER}
    if not records:
        return {
            "n": 0,
            "abs_delta_sum": 0.0,
            "explained_share_put_leg": None,
            "explained_share_call_leg": None,
            "explained_share_tenor": None,
            "explained_share_spot": None,
            "n_assigned_put": 0,
            "n_assigned_call": 0,
            "n_assigned_tenor": 0,
            "n_assigned_spot": 0,
            "n_tenor_mismatch": 0,
            "n_spot_mismatch": 0,
            "n_both_mismatch": 0,
            "abs_put_movement_share": None,
            "abs_call_movement_share": None,
            "sum_put_contribution": 0.0,
            "sum_call_contribution": 0.0,
            "sum_delta": 0.0,
            "max_identity_residual": None,
            **_abs_delta_stats([]),
        }

    mass = {name: 0.0 for name in EXPLAIN_ORDER}
    counts = {name: 0 for name in EXPLAIN_ORDER}
    n_tenor = 0
    n_spot = 0
    n_both = 0
    put_movement = 0.0
    call_movement = 0.0
    sum_put = 0.0
    sum_call = 0.0
    sum_delta = 0.0
    max_residual = 0.0
    deltas: list[float] = []

    for record in records:
        delta = float(record["legacy_skew"]) - float(record["new_skew"])
        put_leg = float(record["legacy_put"]) - float(record["new_put"])
        call_leg = float(record["legacy_call"]) - float(record["new_call"])
        # delta from the two IVs: the call leg enters with a minus, because
        # skew = put IV − call IV.
        identity = put_leg - call_leg
        residual = abs(delta - identity)
        if residual > max_residual:
            max_residual = residual
        explanation = _primary_explanation(record)
        mass[explanation] += abs(delta)
        counts[explanation] += 1
        tenor_flag = tenor_mismatch(record["legacy_tenor"], record["new_tenor"])
        spot_flag = spot_mismatch(record["legacy_spot"], record["new_spot"])
        n_tenor += int(tenor_flag)
        n_spot += int(spot_flag)
        n_both += int(tenor_flag and spot_flag)
        put_movement += abs(put_leg)
        call_movement += abs(call_leg)
        sum_put += put_leg
        sum_call += -call_leg
        sum_delta += delta
        deltas.append(delta)

    total = sum(mass.values())
    if total > 0.0:
        raw = {name: mass[name] / total for name in EXPLAIN_ORDER}
        rounded = _round_shares(raw)
        explained = {
            "explained_share_put_leg": rounded["put"],
            "explained_share_call_leg": rounded["call"],
            "explained_share_tenor": rounded["tenor"],
            "explained_share_spot": rounded["spot"],
        }
    else:
        explained = {
            "explained_share_put_leg": None,
            "explained_share_call_leg": None,
            "explained_share_tenor": None,
            "explained_share_spot": None,
        }

    movement = put_movement + call_movement
    if movement > 0.0:
        movement_shares = _round_shares({
            "put": put_movement / movement,
            "call": call_movement / movement,
        })
        put_share = movement_shares["put"]
        call_share = movement_shares["call"]
    else:
        put_share = None
        call_share = None

    stats = _abs_delta_stats(deltas)
    return {
        "n": len(records),
        "abs_delta_sum": total,
        **explained,
        "n_assigned_put": counts["put"],
        "n_assigned_call": counts["call"],
        "n_assigned_tenor": counts["tenor"],
        "n_assigned_spot": counts["spot"],
        "n_tenor_mismatch": n_tenor,
        "n_spot_mismatch": n_spot,
        "n_both_mismatch": n_both,
        "abs_put_movement_share": put_share,
        "abs_call_movement_share": call_share,
        "sum_put_contribution": sum_put,
        "sum_call_contribution": sum_call,
        "sum_delta": sum_delta,
        "max_identity_residual": max_residual,
        "p50": stats["p50"],
        "p90": stats["p90"],
        "max": stats["max"],
    }


def _stratum_row(name: str, records: list[dict]) -> dict:
    buckets = {bucket: 0 for bucket in SIGN_BUCKETS}
    deltas: list[float] = []
    for record in records:
        delta = float(record["legacy_skew"]) - float(record["new_skew"])
        buckets[sign_bucket(record["legacy_skew"], record["new_skew"])] += 1
        deltas.append(delta)
    stats = _abs_delta_stats(deltas)
    count = len(records)
    agreement = None if count == 0 else round(buckets["match"] / count, 6)
    return {
        "stratum": name,
        "n": count,
        "n_sign_match": buckets["match"],
        "n_sign_flip": buckets["flip"],
        "n_zero": buckets["zero"],
        "sign_agreement_rate": agreement,
        "abs_delta_p50": None if stats["p50"] is None else round(stats["p50"], 6),
        "abs_delta_p90": None if stats["p90"] is None else round(stats["p90"], 6),
        "abs_delta_max": None if stats["max"] is None else round(stats["max"], 6),
    }


def _quartile_labels(values: list[float]) -> list[str]:
    """Q1..Qk labels. Fewer than four distinct values, or fewer than four rows, stay one bin."""
    if len(values) < 4:
        return ["all"] * len(values)
    import pandas as pd
    series = pd.Series(values, dtype="float64")
    if int(series.nunique(dropna=True)) < 2:
        return ["all"] * len(values)
    try:
        bins = pd.qcut(series, 4, duplicates="drop")
    except ValueError:
        return ["all"] * len(values)
    codes = list(bins.cat.codes)
    intervals = [str(bin_) for bin_ in bins]
    return [f"Q{code + 1} {interval}" for code, interval in zip(codes, intervals)]


def _grouped_rows(records: list[dict], labels: list[str]) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    order: list[str] = []
    for record, label in zip(records, labels):
        if label not in groups:
            groups[label] = []
            order.append(label)
        groups[label].append(record)
    rows = [_stratum_row(label, groups[label]) for label in order]
    rows.sort(key=lambda row: row["stratum"])
    return rows


def stratify_compared(records: list[dict]) -> dict:
    """Sign agreement and |delta| by class, by legacy strike-count quartile, and by store size.

    N on every row is the number of compared keys in that row. Quartiles are
    computed on the compared keys only. A key with no store open interest, or
    no store volume, is reported in its own row instead of being dropped.
    Index ETFs are SPY, QQQ, IWM, and DIA. Every other underlying is a single name.
    Both classes are always present, even when N is 0.
    """
    by_class = [
        _stratum_row(name, [record for record in records if underlying_class(record["underlying"]) == name])
        for name in ("index_etf", "single_name")
    ]

    strike_values = [float(record["legacy_n_strikes"]) for record in records]
    by_strikes = _grouped_rows(records, _quartile_labels(strike_values)) if records else []

    def _liquidity_rows(field: str, missing_name: str) -> list[dict]:
        present = [record for record in records if _finite(record.get(field))]
        missing = [record for record in records if not _finite(record.get(field))]
        labels = _quartile_labels([float(record[field]) for record in present]) if present else []
        rows = _grouped_rows(present, labels) if present else []
        if missing:
            rows.append(_stratum_row(missing_name, missing))
        return rows

    return {
        "by_class": by_class,
        "by_n_strikes_quartile": by_strikes,
        "by_store_oi_quartile": _liquidity_rows("store_oi", "oi_unavailable"),
        "by_store_volume_quartile": _liquidity_rows("store_volume", "volume_unavailable"),
    }


def stratified_sample(keys: list[dict], limit: int, seed: int = SAMPLE_SEED) -> list[dict]:
    """Take `limit` keys, spread across class and weekend, with a fixed seed.

    Strata are index ETF vs single name, and weekend vs weekday. Each stratum
    keeps a share of the sample proportional to its size (largest remainder).
    The same seed returns the same keys. A limit at least as large as the
    population returns every key, in the input order.
    """
    if limit >= len(keys):
        return list(keys)
    import random
    groups: dict[tuple[str, str], list[dict]] = {}
    for key in keys:
        stratum = (
            underlying_class(key["underlying"]),
            "weekend" if is_weekend_date(key["date"]) else "weekday",
        )
        groups.setdefault(stratum, []).append(key)
    names = sorted(groups)
    total = len(keys)
    raw = {name: limit * len(groups[name]) / total for name in names}
    alloc = {name: int(math.floor(raw[name])) for name in names}
    leftover = limit - sum(alloc.values())
    for name in sorted(names, key=lambda item: (-(raw[item] - alloc[item]), item)):
        if leftover <= 0:
            break
        if alloc[name] < len(groups[name]):
            alloc[name] += 1
            leftover -= 1
    rng = random.Random(seed)
    chosen: list[dict] = []
    for name in names:
        pool = list(groups[name])
        rng.shuffle(pool)
        chosen.extend(pool[: alloc[name]])
    if len(chosen) < limit:
        chosen_ids = {(item["date"], item["underlying"]) for item in chosen}
        rest = [item for item in keys if (item["date"], item["underlying"]) not in chosen_ids]
        rng.shuffle(rest)
        chosen.extend(rest[: limit - len(chosen)])
    chosen.sort(key=lambda item: (item["date"], item["underlying"]))
    return chosen


def _iso_date(value) -> str:
    if value is None:
        return ""
    try:
        import pandas as pd
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    if hasattr(value, "isoformat") and not isinstance(value, str):
        return str(value.isoformat())[:10]
    return str(value).strip()[:10]


def _read_eod_dates(path: Path) -> set[str]:
    """The calendar days present in one eod year file. Reads the date column only."""
    import pandas as pd
    import pyarrow.parquet as pq
    frame = pq.read_table(path, columns=["date"]).to_pandas()
    parsed = pd.to_datetime(frame["date"], errors="coerce").dropna()
    return set(parsed.dt.strftime("%Y-%m-%d").tolist())


def _eod_dir(store: Path, root: str) -> Path:
    return store / "eod" / root


def _year_file(store: Path, root: str, year: int) -> Path:
    return _eod_dir(store, root) / f"{year}.parquet"


def _chain_liquidity(chain) -> tuple[float | None, float | None]:
    """Total open interest and total volume on the stored chain. None when the column is empty."""
    import pandas as pd
    totals: list[float | None] = []
    for column in ("oi", "volume"):
        if chain is None or column not in chain.columns:
            totals.append(None)
            continue
        numeric = pd.to_numeric(chain[column], errors="coerce")
        if not bool(numeric.notna().any()):
            totals.append(None)
        else:
            totals.append(float(numeric.sum(skipna=True)))
    return totals[0], totals[1]


def _chosen_strikes(recomputed: dict) -> dict[str, float]:
    found = {}
    for key in CHOSEN_K_KEYS:
        if key in recomputed and _finite(recomputed.get(key)):
            found[key] = float(recomputed[key])
    return found


def _price_status(chain, recomputed, date_iso: str, root: str) -> str:
    if chain is None or getattr(chain, "empty", True):
        return "other"
    if recomputed is None:
        return "no_usable_tenor" if tenor_is_unusable(chain) else "other"
    if str(recomputed.get("underlying", "")).upper() != root.upper():
        return "other"
    if str(recomputed.get("asof", ""))[:10] != date_iso[:10]:
        return "other"
    for field in ("skew", "otm_put_iv", "atm_call_iv", "tenor_days", "spot", "n_strikes"):
        if not _finite(recomputed.get(field)):
            return "other"
    return "compared"


def _load_ledger(path: Path):
    import pandas as pd
    if not path.is_file():
        raise FileNotFoundError(f"ledger not found: {path}")
    return pd.read_parquet(path)


def _legacy_keys(ledger) -> list[dict]:
    records = ledger.to_dict(orient="records")
    if "source" in ledger.columns:
        records = [row for row in records if is_legacy_source(row.get("source"))]
    keys = []
    for row in records:
        date_iso = _iso_date(row.get("date"))
        underlying = str(row.get("underlying", "")).strip().upper()
        if not date_iso or not underlying:
            continue
        keys.append({
            "date": date_iso,
            "underlying": underlying,
            "legacy_skew": row.get("skew"),
            "legacy_put": row.get("otm_put_iv"),
            "legacy_call": row.get("atm_call_iv"),
            "legacy_tenor": row.get("tenor_days"),
            "legacy_spot": row.get("spot"),
            "legacy_n_strikes": row.get("n_strikes"),
        })
    keys.sort(key=lambda item: (item["date"], item["underlying"]))
    return keys


def _legacy_comparable(key: dict) -> bool:
    return all(_finite(key.get(field)) for field in (
        "legacy_skew", "legacy_put", "legacy_call", "legacy_tenor",
        "legacy_spot", "legacy_n_strikes",
    ))


def _load_engine():
    from engine.options_skew import compute_skew
    from engine.thetadata_store import clear_parquet_cache, make_chain_provider
    return make_chain_provider, compute_skew, clear_parquet_cache


def _recompute(store: Path, keys: list[dict]) -> tuple[list[dict], list[dict], int]:
    """Price the keys whose class is not already an absence class.

    Returns (compared records, classified absence-or-failure rows, error count).
    """
    make_chain_provider, compute_skew, clear_parquet_cache = _load_engine()
    provider = make_chain_provider(store=store, require_iv=True)
    dir_cache: dict[str, bool] = {}
    date_cache: dict[tuple[str, int], tuple[str, set[str]]] = {}
    classified: list[dict] = []
    priceable: list[dict] = []

    def root_in_store(root: str) -> bool:
        if root not in dir_cache:
            dir_cache[root] = _eod_dir(store, root).is_dir()
        return dir_cache[root]

    def dates_for(root: str, year: int) -> tuple[str, set[str]]:
        cache_key = (root, year)
        if cache_key in date_cache:
            return date_cache[cache_key]
        path = _year_file(store, root, year)
        if not path.is_file():
            date_cache[cache_key] = ("missing", set())
            return date_cache[cache_key]
        try:
            found = _read_eod_dates(path)
        except Exception as exc:  # noqa: BLE001 — one bad file must not abort the audit
            sys.stderr.write(f"unreadable eod file {path}: {exc}\n")
            date_cache[cache_key] = ("unreadable", set())
            return date_cache[cache_key]
        date_cache[cache_key] = ("ok", found)
        return date_cache[cache_key]

    for key in keys:
        root = key["underlying"]
        try:
            year = int(str(key["date"])[:4])
            date(year, int(str(key["date"])[5:7]), int(str(key["date"])[8:10]))
        except (TypeError, ValueError, IndexError):
            classified.append({**key, "class": "other"})
            continue
        in_store = root_in_store(root)
        status = "missing"
        present = False
        if in_store and not is_weekend_date(key["date"]):
            status, found = dates_for(root, year)
            present = key["date"] in found
        if status == "unreadable":
            # The year file is there but cannot be read. Do not call that a missing date.
            classified.append({**key, "class": classify_key(
                key["date"], root, root_in_store=True, date_in_store=True, price_status="other",
            )})
            continue
        if is_weekend_date(key["date"]) or not in_store or not present:
            classified.append({**key, "class": classify_key(
                key["date"], root,
                root_in_store=in_store,
                date_in_store=present,
                price_status=None,
            )})
            continue
        priceable.append(key)

    by_root: dict[str, list[dict]] = {}
    for key in priceable:
        by_root.setdefault(key["underlying"], []).append(key)

    compared: list[dict] = []
    errors = 0
    roots = sorted(by_root)
    sys.stderr.write(
        f"recomputing {len(priceable)} keys across {len(roots)} roots\n"
    )
    for index, root in enumerate(roots, start=1):
        try:
            for key in by_root[root]:
                try:
                    chain = provider(key["date"], root)
                except Exception as exc:  # noqa: BLE001
                    errors += 1
                    sys.stderr.write(f"recompute failed {key['date']} {root}: {exc}\n")
                    chain = None
                    recomputed = None
                else:
                    try:
                        recomputed = compute_skew(chain) if chain is not None else None
                    except Exception as exc:  # noqa: BLE001
                        errors += 1
                        sys.stderr.write(f"compute_skew failed {key['date']} {root}: {exc}\n")
                        recomputed = None
                status = _price_status(chain, recomputed, key["date"], root)
                if status != "compared" or not _legacy_comparable(key):
                    classified.append({**key, "class": "other" if status == "compared" else status})
                    continue
                store_oi, store_volume = _chain_liquidity(chain)
                strikes = _chosen_strikes(recomputed)
                compared.append({
                    "date": key["date"],
                    "underlying": root,
                    "legacy_skew": float(key["legacy_skew"]),
                    "new_skew": float(recomputed["skew"]),
                    "legacy_put": float(key["legacy_put"]),
                    "new_put": float(recomputed["otm_put_iv"]),
                    "legacy_call": float(key["legacy_call"]),
                    "new_call": float(recomputed["atm_call_iv"]),
                    "legacy_tenor": float(key["legacy_tenor"]),
                    "new_tenor": float(recomputed["tenor_days"]),
                    "legacy_spot": float(key["legacy_spot"]),
                    "new_spot": float(recomputed["spot"]),
                    "legacy_n_strikes": float(key["legacy_n_strikes"]),
                    "new_n_strikes": float(recomputed["n_strikes"]),
                    "store_oi": store_oi,
                    "store_volume": store_volume,
                    "chosen_k": strikes,
                    "class": "compared",
                })
        finally:
            clear_parquet_cache()
        if index % 25 == 0 or index == len(roots):
            sys.stderr.write(f"priced {index} of {len(roots)} roots\n")
    return compared, classified, errors


def _sign_counts(records: list[dict]) -> dict[str, int]:
    counts = {bucket: 0 for bucket in SIGN_BUCKETS}
    for record in records:
        counts[sign_bucket(record["legacy_skew"], record["new_skew"])] += 1
    return counts


def _class_counts(classified: list[dict], compared: list[dict]) -> dict[str, int]:
    counts = {name: 0 for name in CLASS_ORDER}
    for row in classified:
        counts[row["class"]] += 1
    counts["compared"] = len(compared)
    return counts


def _worst(records: list[dict], limit: int = 20) -> list[dict]:
    def sort_key(record: dict) -> tuple:
        delta = float(record["legacy_skew"]) - float(record["new_skew"])
        return (-abs(delta), record["date"], record["underlying"])
    return sorted(records, key=sort_key)[:limit]


def _fmt(value, digits: int = 6) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        if not math.isfinite(value):
            return "—"
        return f"{value:.{digits}f}"
    return str(value)


def _percent(share) -> str:
    if share is None:
        return "not defined"
    return f"{share * 100:.1f} percent"


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def _stratum_table(rows: list[dict]) -> list[str]:
    body = []
    for row in rows:
        body.append([
            row["stratum"],
            str(row["n"]),
            str(row["n_sign_match"]),
            str(row["n_sign_flip"]),
            str(row["n_zero"]),
            _fmt(row["sign_agreement_rate"]),
            _fmt(row["abs_delta_p50"]),
            _fmt(row["abs_delta_p90"]),
            _fmt(row["abs_delta_max"]),
        ])
    return _table(
        ["stratum", "N", "match", "flip", "zero", "sign agreement", "|delta| p50", "|delta| p90", "|delta| max"],
        body,
    )


def _summary_payload(
    *,
    class_counts: dict[str, int],
    sign_counts: dict[str, int],
    decomposition: dict,
    strata: dict,
    limit: int | None,
    legacy_n: int,
    errors: int,
    chosen_k_exposed: bool,
    population_n: int,
) -> dict:
    compared = class_counts["compared"]
    agreement = None if compared == 0 else round(sign_counts["match"] / compared, 6)
    payload = {
        "schema": "options_skew_parity.v1",
        "legacy_keys": legacy_n,
        "population_keys": population_n,
        "weekend_date": class_counts["weekend_date"],
        "root_not_in_store": class_counts["root_not_in_store"],
        "date_not_in_store_for_root": class_counts["date_not_in_store_for_root"],
        "no_usable_tenor": class_counts["no_usable_tenor"],
        "other": class_counts["other"],
        "compared": compared,
        "n_sign_match": sign_counts["match"],
        "n_sign_flip": sign_counts["flip"],
        "n_zero": sign_counts["zero"],
        "sign_agreement_rate": agreement,
        "abs_delta_p50": None if decomposition["p50"] is None else round(decomposition["p50"], 6),
        "abs_delta_p90": None if decomposition["p90"] is None else round(decomposition["p90"], 6),
        "abs_delta_max": None if decomposition["max"] is None else round(decomposition["max"], 6),
        "explained_share_put_leg": decomposition["explained_share_put_leg"],
        "explained_share_call_leg": decomposition["explained_share_call_leg"],
        "explained_share_tenor": decomposition["explained_share_tenor"],
        "explained_share_spot": decomposition["explained_share_spot"],
        "abs_put_movement_share": decomposition["abs_put_movement_share"],
        "abs_call_movement_share": decomposition["abs_call_movement_share"],
        "n_tenor_mismatch": decomposition["n_tenor_mismatch"],
        "n_spot_mismatch": decomposition["n_spot_mismatch"],
        "n_both_mismatch": decomposition["n_both_mismatch"],
        "n_assigned_put": decomposition["n_assigned_put"],
        "n_assigned_call": decomposition["n_assigned_call"],
        "n_assigned_tenor": decomposition["n_assigned_tenor"],
        "n_assigned_spot": decomposition["n_assigned_spot"],
        "max_identity_residual": (
            None if decomposition["max_identity_residual"] is None
            else round(decomposition["max_identity_residual"], 6)
        ),
        "recompute_errors": errors,
        "limit": limit,
        "sample_seed": None if limit is None else SAMPLE_SEED,
        "chosen_k_exposed": chosen_k_exposed,
        "by_class": strata["by_class"],
        "by_n_strikes_quartile": strata["by_n_strikes_quartile"],
        "by_store_oi_quartile": strata["by_store_oi_quartile"],
        "by_store_volume_quartile": strata["by_store_volume_quartile"],
        "reconciles": (
            sum(class_counts.values()) == legacy_n
            and sign_counts["match"] + sign_counts["flip"] + sign_counts["zero"] == compared
            and sum(row["n"] for row in strata["by_class"]) == compared
            and sum(row["n"] for row in strata["by_n_strikes_quartile"]) == compared
            and sum(row["n"] for row in strata["by_store_oi_quartile"]) == compared
            and sum(row["n"] for row in strata["by_store_volume_quartile"]) == compared
        ),
    }
    return payload


def _render(
    *,
    ledger: str,
    store: str,
    payload: dict,
    decomposition: dict,
    strata: dict,
    worst: list[dict],
    run_utc: str,
) -> str:
    legacy_n = payload["legacy_keys"]
    lines: list[str] = []
    lines.append("# Options skew methodology-parity receipt")
    lines.append("")
    lines.append(
        "This receipt compares each legacy polygon_gex row with a fresh "
        "ThetaData recompute of the same date and underlying. Both sides use "
        "the same skew formula. This run does not change the formula, and it "
        "does not edit the engine."
    )
    lines.append("")
    lines.append(f"- Run (UTC): {run_utc}")
    lines.append(f"- Ledger: `{ledger}`")
    lines.append(f"- ThetaData store: `{store}`")
    if payload["limit"] is None:
        lines.append(f"- Legacy keys in this run: **{legacy_n}** (the full legacy population).")
    else:
        lines.append(
            f"- Legacy keys in this run: **{legacy_n}** of {payload['population_keys']} "
            f"(a stratified random sample, seed {payload['sample_seed']}). "
            "This is not the full ledger."
        )
    lines.append(
        "- A weekend date is Saturday or Sunday. A root is in the store when "
        "eod/<ROOT> exists. A date is in the store when that day appears in "
        "eod/<ROOT>/<YEAR>.parquet. Nothing here calls the network."
    )
    lines.append("")
    lines.append("## Classification")
    lines.append("")
    lines.append(
        "Every legacy key lands in exactly one class. The six classes add up "
        "to the legacy key count for this run."
    )
    lines.append("")
    class_rows = []
    for name in CLASS_ORDER:
        count = payload[name]
        share = "—" if legacy_n == 0 else f"{count / legacy_n * 100:.1f} percent"
        class_rows.append([name, str(count), share])
    class_rows.append(["total", str(sum(payload[name] for name in CLASS_ORDER)), "100.0 percent" if legacy_n else "—"])
    lines.extend(_table(["class", "N", "share of legacy keys"], class_rows))
    lines.append("")
    lines.append(
        f"Recompute errors while pricing a stored chain: {payload['recompute_errors']}. "
        "An error is counted in other, not dropped."
    )
    lines.append("")
    lines.append("## Compared keys")
    lines.append("")
    compared = payload["compared"]
    lines.append(
        f"Both paths priced **{compared}** keys. "
        f"Sign agreement (same non-zero sign, divided by compared keys) is "
        f"**{_fmt(payload['sign_agreement_rate'])}**. "
        f"The absolute skew gap has p50 {_fmt(payload['abs_delta_p50'])}, "
        f"p90 {_fmt(payload['abs_delta_p90'])}, and max {_fmt(payload['abs_delta_max'])}. "
        "The percentile is the nearest rank, the same rule as the overlap audit."
    )
    lines.append("")
    lines.append(
        "Match means both skews are non-zero and share a sign. Flip means both "
        "are non-zero and the signs disagree. Zero means at least one skew is "
        "exactly zero. Match, flip, and zero add up to the compared count."
    )
    lines.append("")
    lines.extend(_table(
        ["bucket", "N"],
        [
            ["match", str(payload["n_sign_match"])],
            ["flip", str(payload["n_sign_flip"])],
            ["zero", str(payload["n_zero"])],
            ["total", str(compared)],
        ],
    ))
    lines.append("")
    lines.append("## Decomposition")
    lines.append("")
    lines.append(
        "The skew gap equals the put-IV gap minus the call-IV gap. "
        f"Across compared keys, the put IV contributions sum to "
        f"{_fmt(decomposition['sum_put_contribution'])} and the call IV "
        f"contributions sum to {_fmt(decomposition['sum_call_contribution'])}. "
        f"Those two sums add to {_fmt(decomposition['sum_put_contribution'] + decomposition['sum_call_contribution'])}, "
        "which is the gap implied by the two IVs. The stored skews sum to a gap of "
        f"{_fmt(decomposition['sum_delta'])}. The largest absolute leftover on one "
        f"key, between that identity and the stored skew, is "
        f"{_fmt(payload['max_identity_residual'])}."
    )
    lines.append("")
    lines.append(
        "Each compared key's absolute gap is assigned to one explanation. "
        "A tenor mismatch (more than 5 days) comes first. Otherwise a spot "
        "mismatch (more than 2 percent) comes next. Otherwise the gap is "
        "assigned to the put leg when the put IV moved at least as much as "
        "the call IV, and to the call leg otherwise. "
        f"On that rule the put leg explains {_percent(payload['explained_share_put_leg'])} "
        f"of the absolute gap, the call leg {_percent(payload['explained_share_call_leg'])}, "
        f"a tenor mismatch {_percent(payload['explained_share_tenor'])}, and a spot "
        f"mismatch {_percent(payload['explained_share_spot'])}."
    )
    lines.append("")
    lines.append(
        f"The tenor flag is on {payload['n_tenor_mismatch']} compared keys and the "
        f"spot flag is on {payload['n_spot_mismatch']} compared keys. "
        f"{payload['n_both_mismatch']} "
        f"{'key has' if payload['n_both_mismatch'] == 1 else 'keys have'} both flags. "
        "A key with both flags "
        "is counted in the tenor share, not in both shares. "
        f"Assignment counts: put {payload['n_assigned_put']}, "
        f"call {payload['n_assigned_call']}, tenor {payload['n_assigned_tenor']}, "
        f"spot {payload['n_assigned_spot']}."
    )
    lines.append("")
    lines.append(
        "A second split ignores tenor and spot and only compares the size of "
        "the two IV moves. "
        f"The put IV accounts for {_percent(payload['abs_put_movement_share'])} of "
        f"the absolute IV movement, and the call IV accounts for "
        f"{_percent(payload['abs_call_movement_share'])}. Those two shares add to "
        "100 percent when either leg moved. They answer a different question "
        "from the four shares above."
    )
    lines.append("")
    if payload["chosen_k_exposed"]:
        lines.append(
            "compute_skew returned the strike it picked. Those strikes are in "
            "the worst-key table."
        )
    else:
        lines.append(
            "compute_skew does not return the strike it picked. This receipt "
            "does not invent a second strike picker, and the engine file was "
            "not edited to add one."
        )
    lines.append("")
    lines.append("## Stratification")
    lines.append("")
    lines.append(
        "N is the number of compared keys in the row. Match, flip, and zero "
        "add up to N. Sign agreement is match divided by N. A row with N of 0 "
        "has no agreement rate and no gap percentile. Quartiles use the "
        "compared keys only. Fewer than four distinct values stay in one bin."
    )
    lines.append("")
    lines.append("### By underlying class")
    lines.append("")
    lines.append(
        "Index ETFs are SPY, QQQ, IWM, and DIA. Every other underlying is a single name."
    )
    lines.append("")
    lines.extend(_stratum_table(strata["by_class"]))
    lines.append("")
    lines.append("### By legacy strike count")
    lines.append("")
    lines.append(
        "The quartile is the legacy ledger's n_strikes on the compared keys. "
        "Q1 is the lowest strike count."
    )
    lines.append("")
    lines.extend(_stratum_table(strata["by_n_strikes_quartile"]))
    lines.append("")
    lines.append("### By stored open interest")
    lines.append("")
    lines.append(
        "Open interest is the total on the stored chain for that day, across "
        "every expiry the file holds, not only the expiry the formula picked. "
        "A key whose chain has no open interest is in oi_unavailable."
    )
    lines.append("")
    lines.extend(_stratum_table(strata["by_store_oi_quartile"]))
    lines.append("")
    lines.append("### By stored volume")
    lines.append("")
    lines.append(
        "Volume is the total on that same stored chain. A key whose chain has "
        "no volume is in volume_unavailable."
    )
    lines.append("")
    lines.extend(_stratum_table(strata["by_store_volume_quartile"]))
    lines.append("")
    lines.append("## Twenty largest absolute gaps")
    lines.append("")
    lines.append(
        "Both IV legs are shown. Tenor mismatch means the tenors differ by "
        "more than 5 days. Spot mismatch means the spots differ by more than 2 percent."
    )
    lines.append("")
    headers = [
        "date", "underlying", "class", "legacy skew", "new skew", "delta",
        "legacy put IV", "new put IV", "legacy call IV", "new call IV",
        "legacy tenor", "new tenor", "legacy spot", "new spot",
        "tenor mismatch", "spot mismatch", "legacy strikes", "new strikes",
    ]
    if payload["chosen_k_exposed"]:
        headers.extend(["chosen put K", "chosen call K"])
    body = []
    for record in worst:
        delta = float(record["legacy_skew"]) - float(record["new_skew"])
        row = [
            record["date"],
            record["underlying"],
            underlying_class(record["underlying"]),
            _fmt(record["legacy_skew"]),
            _fmt(record["new_skew"]),
            _fmt(delta),
            _fmt(record["legacy_put"]),
            _fmt(record["new_put"]),
            _fmt(record["legacy_call"]),
            _fmt(record["new_call"]),
            _fmt(record["legacy_tenor"], 1),
            _fmt(record["new_tenor"], 1),
            _fmt(record["legacy_spot"], 4),
            _fmt(record["new_spot"], 4),
            "yes" if tenor_mismatch(record["legacy_tenor"], record["new_tenor"]) else "no",
            "yes" if spot_mismatch(record["legacy_spot"], record["new_spot"]) else "no",
            str(int(record["legacy_n_strikes"])),
            str(int(record["new_n_strikes"])),
        ]
        if payload["chosen_k_exposed"]:
            chosen = record.get("chosen_k") or {}
            put_k = chosen.get("otm_put_k", chosen.get("put_k", chosen.get("otm_put_strike")))
            call_k = chosen.get("atm_call_k", chosen.get("call_k", chosen.get("atm_call_strike")))
            row.extend([_fmt(put_k, 4), _fmt(call_k, 4)])
        body.append(row)
    if not body:
        lines.append("No compared keys, so there is no gap table.")
    else:
        lines.extend(_table(headers, body))
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("The next line is the summary of the counts above.")
    lines.append(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    lines.append("")
    return "\n".join(lines)


def _default_out(today: date | None = None) -> Path:
    day = today or datetime.now(timezone.utc).date()
    return Path("research") / f"MARKET_ONTOLOGY_F03_SKEW_PARITY_RECEIPT_{day.isoformat()}.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="audit_options_skew_parity",
        description="Decompose the legacy polygon_gex skew gap against a ThetaData recompute.",
    )
    parser.add_argument("--ledger", default=DEFAULT_LEDGER,
                        help="ledger parquet (default: data/options_skew/snapshots.parquet)")
    parser.add_argument("--store", default=None,
                        help="ThetaData EOD store root (default: $THETADATA_STORE)")
    parser.add_argument("--limit", type=int, default=None,
                        help="stratified-random cap on legacy keys (a quick smoke)")
    parser.add_argument("--out", default=None,
                        help="markdown receipt path (default: "
                             "research/MARKET_ONTOLOGY_F03_SKEW_PARITY_RECEIPT_<UTC date>.md)")
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        sys.stderr.write("limit must be a positive integer\n")
        return EXIT_USAGE

    import os
    store_text = args.store or os.environ.get("THETADATA_STORE", DEFAULT_STORE)
    store = Path(store_text)
    ledger_path = Path(args.ledger)
    out_path = Path(args.out) if args.out else _default_out()

    try:
        ledger = _load_ledger(ledger_path)
    except FileNotFoundError as exc:
        sys.stderr.write(f"READ_ERROR: {exc}\n")
        return EXIT_READ
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"READ_ERROR: {exc}\n")
        return EXIT_READ

    population = _legacy_keys(ledger)
    if not population:
        sys.stderr.write(
            "NO_LEGACY_ROWS: the ledger has no polygon_gex rows to audit.\n"
        )
        return EXIT_USAGE

    if args.limit is None or args.limit >= len(population):
        keys = population
        limit = None
    else:
        keys = stratified_sample(population, args.limit, SAMPLE_SEED)
        limit = args.limit

    compared, classified, errors = _recompute(store, keys)
    class_counts = _class_counts(classified, compared)
    sign_counts = _sign_counts(compared)
    decomposition = decompose_compared(compared)
    strata = stratify_compared(compared)
    worst = _worst(compared, 20)
    chosen = any(record.get("chosen_k") for record in compared)
    payload = _summary_payload(
        class_counts=class_counts,
        sign_counts=sign_counts,
        decomposition=decomposition,
        strata=strata,
        limit=limit,
        legacy_n=len(keys),
        errors=errors,
        chosen_k_exposed=chosen,
        population_n=len(population),
    )
    run_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    text = _render(
        ledger=str(ledger_path),
        store=str(store),
        payload=payload,
        decomposition=decomposition,
        strata=strata,
        worst=worst,
        run_utc=run_utc,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    sys.stdout.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    sys.stderr.write(f"receipt: {out_path}\n")
    if not payload["reconciles"]:
        sys.stderr.write(
            "UNRECONCILED: class counts or sign buckets do not add up.\n"
        )
        return EXIT_UNRECONCILED
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
