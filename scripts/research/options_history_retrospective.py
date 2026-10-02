"""Frozen Theta retrospective association study; no PIT, alpha or execution claim."""

from __future__ import annotations

"""Proposal-only immutable input manifest; metadata/date scans never read feature values."""
import hashlib, importlib.util, json, platform
from datetime import date, datetime
from pathlib import Path
import numpy, pandas, scipy, yaml, pyarrow as pa, pyarrow.compute as pc, pyarrow.parquet as pq

PROTOCOL_SHA = "67011db3d3aed08827f027cafc5b5a2bf890289a1017b227cad15fc240826e68"
FAMILY = "options_theta_retrospective_association_v1"
DATE_NAMES = (
    "date",
    "session_date",
    "as_of_date",
    "asof_date",
    "quote_date",
    "trade_date",
)
AVAIL_WORDS = (
    "known",
    "available",
    "vintage",
    "revision",
    "received",
    "ingest",
    "publish",
    "asof",
    "as_of",
)


def canonical_bytes(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
        ).encode()
        + b"\n"
    )


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def stat(p):
    s = p.stat()
    return (s.st_size, s.st_mtime_ns, s.st_ino, s.st_dev)


def unique_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON key: " + key)
        out[key] = value
    return out


def load_protocol(p):
    raw = p.read_bytes()
    if sha_bytes(raw) != PROTOCOL_SHA:
        raise ValueError("frozen protocol SHA mismatch")
    d = json.loads(raw, object_pairs_hook=unique_object)
    if d.get("study_id") != "THETA-EOD-RETROSPECTIVE-ASSOCIATION-V1.1":
        raise ValueError("unexpected protocol study")
    return d


def expected_slots(proto):
    s = proto["source_snapshot"]["selection"]
    t = s["theta_source_slots"]
    slots = []
    for root in t["roots"]:
        for year in t["years"]:
            for kind in ("greeks", "oi"):
                slots.append(
                    {
                        "kind": kind,
                        "root": root,
                        "year": year,
                        "relative_path": f"theta/{kind}/{root}/{year}.parquet",
                    }
                )
    for root in s["price_source_slots"]["roots"]:
        slots.append(
            {
                "kind": "price",
                "root": root,
                "year": None,
                "relative_path": f"price/data/yahoo/{root}.parquet",
            }
        )
    if len(slots) != 435 or len({x["relative_path"] for x in slots}) != 435:
        raise ValueError("fixed selector is not 435 unique slots")
    return sorted(slots, key=lambda x: x["relative_path"])


def source_digest(root):
    engine, lib = root / "engine", root / "lib"
    if not engine.is_dir() or not lib.is_dir():
        raise IOError("engine/lib source directories required")
    ep, lp = list(engine.rglob("*.py")), list(lib.rglob("*.py"))
    if not ep or not lp:
        raise IOError("engine/lib source directories must be nonempty")
    paths = sorted(
        set(
            ep
            + lp
            + [
                root / "scripts/research/options_history_gauntlet.py",
                root / "scripts/research/options_history_retrospective.py",
                root / "config/ruling_graph.yml",
            ]
        ),
        key=lambda p: p.as_posix(),
    )
    if any(not p.is_file() for p in paths):
        raise IOError("required source digest path unavailable")
    return [
        {"relative_path": p.relative_to(root).as_posix(), "sha256": sha_file(p)}
        for p in paths
    ]


def family_registered(root):
    d = yaml.safe_load((root / "config/ruling_graph.yml").read_text()) or {}
    if FAMILY not in d.get("meta", {}).get("known_fdr_families", []):
        raise ValueError("registered FDR family token missing")


def calendar(root):
    p = root / "lib/nyse_calendar.py"
    spec = importlib.util.spec_from_file_location("_frozen_nyse", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    dates = [
        d.isoformat()
        for d in mod.sessions_between(date(2016, 1, 1), date(2025, 12, 31))
    ]
    return {
        "start": "2016-01-01",
        "end": "2025-12-31",
        "count": len(dates),
        "sha256": sha_bytes(canonical_bytes(dates)),
    }, mod


def normalize(v):
    if isinstance(v, datetime):
        return v.date(), v.time().isoformat() != "00:00:00", False
    if isinstance(v, date):
        return v, False, False
    try:
        s = str(v).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt.date(), dt.time().isoformat() != "00:00:00", False
    except ValueError:
        try:
            return date.fromisoformat(str(v)[:10]), False, False
        except ValueError:
            return None, False, True


def metadata(path, cal):
    pf = pq.ParquetFile(path)
    names = pf.schema_arrow.names
    low = {x.lower(): x for x in names}
    col = next((low[x] for x in DATE_NAMES if x in low), None)
    out = {
        "size": path.stat().st_size,
        "sha256": sha_file(path),
        "row_count": pf.metadata.num_rows,
        "schema": str(pf.schema_arrow),
        "columns": names,
        "date_column": col,
        "availability_or_vintage_columns": [
            x for x in names if any(w in x.lower() for w in AVAIL_WORDS)
        ],
    }
    if col is None:
        out["date_scan"] = {"status": "NO_RECOGNIZED_DATE_COLUMN"}
        return out
    nulls = seen = invalid = nonmidnight = 0
    dates = set()
    for b in pf.iter_batches(columns=[col], batch_size=65536):
        a = b.column(0)
        nulls += a.null_count
        seen += len(a) - a.null_count
        pc.min_max(a)
        pc.count_distinct(a)
        for v in pc.unique(a).to_pylist():
            if v is not None:
                d, mid, bad = normalize(v)
                invalid += bad
                nonmidnight += mid
                if d is not None:
                    dates.add(d)
    out["date_scan"] = {
        "non_null": seen,
        "null_count": nulls,
        "min": min(dates).isoformat() if dates else None,
        "max": max(dates).isoformat() if dates else None,
        "unique_dates": len(dates),
        "non_session_dates": sum(not cal.is_session(d) for d in dates),
        "non_midnight_timestamp_count": nonmidnight,
        "invalid_date_metadata_count": invalid,
        "out_of_study_unique_dates": sum(
            d < date(2017, 1, 1) or d > date(2025, 12, 31) for d in dates
        ),
    }
    return out


def resolve(slot, store, prices):
    x = slot["relative_path"].split("/")
    return store / x[1] / x[2] / x[3] if slot["kind"] != "price" else prices / x[-1]


def prepare_manifest(
    store: Path, price_store: Path, protocol_path: Path, source_root: Path
) -> dict:
    store, price_store, source_root = map(Path, (store, price_store, source_root))
    proto = load_protocol(Path(protocol_path))
    slots = expected_slots(proto)
    code_before = source_digest(source_root)
    family_registered(source_root)
    calinfo, cal = calendar(source_root)
    baseline = {
        x["relative_path"]: (
            stat(resolve(x, store, price_store))
            if resolve(x, store, price_store).is_file()
            else None
        )
        for x in slots
    }
    entries = []
    for slot in slots:
        p = resolve(slot, store, price_store)
        entry = dict(slot)
        if not p.is_file():
            entry["state"] = "missing"
        else:
            entry.update(state="present", **metadata(p, cal))
        if (stat(p) if p.is_file() else None) != baseline[slot["relative_path"]]:
            raise IOError("input changed during prepare: " + slot["relative_path"])
        entries.append(entry)
    changed = [
        x["relative_path"]
        for x in slots
        if (
            stat(resolve(x, store, price_store))
            if resolve(x, store, price_store).is_file()
            else None
        )
        != baseline[x["relative_path"]]
    ]
    if changed:
        raise IOError(
            "input changed before manifest finalization: " + ",".join(changed)
        )
    code_after = source_digest(source_root)
    family_registered(source_root)
    if code_after != code_before:
        raise IOError("source changed during prepare")
    return {
        "schema": "options.science.theta_eod_retrospective_association.manifest/v1",
        "study_id": proto["study_id"],
        "protocol_sha256": PROTOCOL_SHA,
        "expected_slot_count": 435,
        "entries": entries,
        "source_code_digest": code_before,
        "calendar": calinfo,
        "runtime": {
            "python": platform.python_version(),
            "numpy": numpy.__version__,
            "pandas": pandas.__version__,
            "scipy": scipy.__version__,
            "pyarrow": pa.__version__,
        },
    }


def verify_manifest(
    manifest, expected_sha, store, price_store, protocol_path, source_root
) -> None:
    if (
        not isinstance(manifest, dict)
        or sha_bytes(canonical_bytes(manifest)) != expected_sha
    ):
        raise ValueError("manifest hash mismatch")
    if manifest.get("protocol_sha256") != PROTOCOL_SHA:
        raise ValueError("manifest protocol mismatch")
    rebuilt = prepare_manifest(
        Path(store), Path(price_store), Path(protocol_path), Path(source_root)
    )
    if canonical_bytes(rebuilt) != canonical_bytes(manifest):
        raise ValueError("manifest/input/source/runtime mismatch; refresh refused")


"""Pure pre-outcome feature adapter proposal for Theta retrospective v1.1.
No IO, d5, labels, returns, or outcome access occur here.
"""
from collections import Counter
from typing import Any
import numpy as np
import pandas as pd
from engine import exposure_math, options_dislocation, options_ivspread, options_skew
from lib import nyse_calendar

_ID = ["date", "expiration", "strike", "right"]
_NUM = [
    "net_gamma_norm",
    "net_vanna_norm",
    "net_charm_norm",
    "cw_ivspread",
    "skew",
    "atm_iv",
    "term_slope",
    "oi_total",
]
_COUNTER_KEYS = (
    "greeks_raw_input_rows",
    "oi_raw_input_rows",
    "greeks_root_mismatch_rows",
    "oi_root_mismatch_rows",
    "greeks_invalid_date_rows",
    "oi_invalid_date_rows",
    "greeks_non_session_rows",
    "oi_non_session_rows",
    "greeks_invalid_identity_rows",
    "oi_invalid_identity_rows",
    "greeks_duplicate_rows_removed",
    "oi_duplicate_rows_removed",
    "greeks_valid_rows",
    "oi_valid_rows",
    "greeks_empty_input",
    "oi_empty_input",
    "oi_total_dates",
    "greeks_unmatched_rows",
    "oi_unmatched_rows",
    "joined_rows",
    "joined_quote_excluded_rows",
)


def _require(df: pd.DataFrame, cols: list[str], name: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{name} missing required columns: {missing}")


def _root_col(df: pd.DataFrame, name: str) -> str:
    for col in ("underlying", "root"):
        if col in df.columns:
            return col
    raise ValueError(f"{name} missing required underlying/root column")


def _as_dates(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce").dt.date


def _empty(kind: str) -> pd.DataFrame:
    cols = _ID + (
        ["oi"]
        if kind == "oi"
        else ["bid", "ask", "iv", "spot", "delta", "gamma", "vanna", "charm"]
    )
    return pd.DataFrame(columns=cols)


def _raw_dates(
    df: pd.DataFrame | None, root: str, year: int, kind: str, q: Counter
) -> set:
    if df is None or df.empty:
        return set()
    _require(df, ["date"], kind)
    rcol = _root_col(df, kind)  # root identity is required for both input planes.
    dates = _as_dates(df["date"])
    root_ok = df[rcol].astype(str).str.upper().eq(root.upper())
    q[f"{kind}_raw_input_rows"] += len(df)
    q[f"{kind}_root_mismatch_rows"] += int((~root_ok).sum())
    invalid_date = dates.isna()
    q[f"{kind}_invalid_date_rows"] += int(invalid_date.sum())
    non_session = pd.Series(False, index=df.index)
    for i, d in dates.items():
        if pd.notna(d) and not nyse_calendar.is_session(d):
            non_session.loc[i] = True
    q[f"{kind}_non_session_rows"] += int(non_session.sum())
    return {
        d
        for d, ok in zip(dates, root_ok)
        if pd.notna(d) and d.year == year and nyse_calendar.is_session(d) and ok
    }


def _normalise_greeks(
    greeks: pd.DataFrame | None, root: str, year: int, q: Counter
) -> pd.DataFrame:
    if greeks is None or greeks.empty:
        q["greeks_empty_input"] += 1
        return _empty("greeks")
    _require(greeks, _ID + ["bid", "ask"], "greeks")
    rcol = _root_col(greeks, "greeks")
    ivcol = "iv" if "iv" in greeks else "implied_vol"
    spotcol = "spot" if "spot" in greeks else "underlying_price"
    _require(greeks, [ivcol, spotcol, "delta"], "greeks")
    g = greeks.copy()
    g["date"] = _as_dates(g["date"])
    g["expiration"] = _as_dates(g["expiration"])
    for c in (
        "strike",
        "bid",
        "ask",
        ivcol,
        spotcol,
        "delta",
        "gamma",
        "vanna",
        "charm",
    ):
        if c in g:
            g[c] = pd.to_numeric(g[c], errors="coerce")
    g = g.rename(columns={ivcol: "iv", spotcol: "spot"})
    g["right"] = g["right"].astype(str).str.upper()
    valid = (
        g["date"].notna()
        & g["expiration"].notna()
        & g["date"].map(lambda d: d.year == year and nyse_calendar.is_session(d))
        & g[rcol].astype(str).str.upper().eq(root.upper())
        & g["right"].isin(["C", "P"])
        & np.isfinite(g["strike"])
        & g["strike"].gt(0)
        & g["expiration"].gt(g["date"])
    )
    q["greeks_invalid_identity_rows"] += int((~valid).sum())
    g = g.loc[valid].copy()
    dup = g.duplicated(_ID, keep=False)
    q["greeks_duplicate_rows_removed"] += int(dup.sum())
    return g.loc[~dup].copy()


def _normalise_oi(
    oi: pd.DataFrame | None, root: str, year: int, q: Counter
) -> pd.DataFrame:
    if oi is None or oi.empty:
        q["oi_empty_input"] += 1
        return _empty("oi")
    _require(oi, _ID + ["open_interest"], "oi")
    rcol = _root_col(oi, "oi")
    o = oi.copy()
    o["date"] = _as_dates(o["date"])
    o["expiration"] = _as_dates(o["expiration"])
    o["strike"] = pd.to_numeric(o["strike"], errors="coerce")
    o["open_interest"] = pd.to_numeric(o["open_interest"], errors="coerce")
    o["right"] = o["right"].astype(str).str.upper()
    valid = (
        o["date"].notna()
        & o["expiration"].notna()
        & o["date"].map(lambda d: d.year == year and nyse_calendar.is_session(d))
        & o[rcol].astype(str).str.upper().eq(root.upper())
        & o["right"].isin(["C", "P"])
        & np.isfinite(o["strike"])
        & o["strike"].gt(0)
        & o["expiration"].gt(o["date"])
    )
    q["oi_invalid_identity_rows"] += int((~valid).sum())
    o = o.loc[valid].copy()
    dup = o.duplicated(_ID, keep=False)
    q["oi_duplicate_rows_removed"] += int(dup.sum())
    return o.loc[~dup].copy()


def _nearest(frame: pd.DataFrame, target: float, lo: float, hi: float | None):
    dte = (frame["expiration"] - frame["date"]).map(lambda x: x.days).astype(float)
    m = dte.ge(lo) if hi is None else dte.ge(lo) & dte.lt(hi)
    c = pd.DataFrame(
        {"expiry": frame.loc[m, "expiration"], "dte": dte.loc[m]}
    ).drop_duplicates()
    if c.empty:
        return None
    c["dist"] = (c["dte"] - target).abs()
    return c.sort_values(["dist", "expiry"], kind="stable").iloc[0]["expiry"]


def _atm(frame: pd.DataFrame, target: float, lo: float, hi: float) -> float | None:
    expiry = _nearest(frame, target, lo, hi)
    if expiry is None:
        return None
    sub = frame[frame["expiration"].eq(expiry)].copy()
    finite_delta = np.isfinite(pd.to_numeric(sub["delta"], errors="coerce"))
    sub = sub.loc[finite_delta].copy()
    if not (sub["right"].eq("C").any() and sub["right"].eq("P").any()):
        return None
    a = sub.rename(columns={"right": "_right"}).copy()
    a["is_call"] = a["_right"].eq("C")
    a["expiry"] = a["expiration"]
    a["_days"] = (a["expiration"] - a["date"]).map(lambda x: x.days).astype(float)
    v = options_dislocation._atm_iv(a, lo, hi)
    return round(float(v), 6) if np.isfinite(v) else None


def _cw(frame: pd.DataFrame) -> tuple[float | None, str]:
    expiry = _nearest(frame, 30.0, 7.0, None)
    if expiry is None:
        return None, "CW_NO_TENOR"
    a = (
        frame[frame["expiration"].eq(expiry)]
        .rename(columns={"right": "_right", "strike": "K"})
        .copy()
    )
    a["is_call"] = a["_right"].eq("C")
    a["expiry"] = a["expiration"]
    a["T"] = (a["expiration"] - a["date"]).map(lambda x: x.days / 365.0)
    a["underlying"] = a["root"]
    a["asof"] = a["date"]
    out = options_ivspread.compute_ivspread(a)
    if not out or out.get("n_pairs", 0) < 3 or out.get("weight_kind") != "oi":
        return None, "CW_INSUFFICIENT_STRICT_PAIRS"
    return float(out["ivspread"]), "OK"


def _skew(frame: pd.DataFrame) -> tuple[float | None, str]:
    expiry = _nearest(frame, 30.0, 7.0, None)
    if expiry is None:
        return None, "SKEW_NO_TENOR"
    sub = frame[frame["expiration"].eq(expiry)].copy()
    d = pd.to_numeric(sub["delta"], errors="coerce")
    call = sub["right"].eq("C") & np.isfinite(d) & d.between(0.02, 0.98)
    put = sub["right"].eq("P") & np.isfinite(d) & d.between(-0.98, -0.02)
    if not call.any() or not put.any():
        return None, "SKEW_STRICT_DELTA_LEG_MISSING"
    a = sub.loc[call | put].rename(columns={"right": "_right", "strike": "K"}).copy()
    a["is_call"] = a["_right"].eq("C")
    a["expiry"] = a["expiration"]
    a["T"] = (a["expiration"] - a["date"]).map(lambda x: x.days / 365.0)
    a["underlying"] = a["root"]
    a["asof"] = a["date"]
    out = options_skew.compute_skew(a)
    return (float(out["skew"]), "OK") if out else (None, "SKEW_CANONICAL_REFUSAL")


def _exposure(frame: pd.DataFrame, greek: str) -> tuple[float | None, str]:
    if greek not in frame:
        return None, f"{greek.upper()}_COLUMN_UNAVAILABLE"
    usable = exposure_math.usable_quote(frame["iv"], frame["oi"])
    book = frame.loc[usable]
    if book.empty:
        return None, f"{greek.upper()}_NO_USABLE_QUOTES"
    values = pd.to_numeric(book[greek], errors="coerce").to_numpy(float)
    if float(np.isfinite(values).mean()) < 0.90:
        return None, f"{greek.upper()}_COVERAGE_LT_90"
    x = exposure_math.dealer_exposures(
        is_call=book["right"].eq("C").to_numpy(),
        oi=book["oi"].to_numpy(float),
        spot=book["spot"].to_numpy(float),
        **{greek: values},
    )[greek]
    finite = np.isfinite(x)
    denom = float(np.abs(x[finite]).sum())
    return (
        (float(x[finite].sum() / denom), "OK")
        if finite.any() and denom > 0
        else (None, f"{greek.upper()}_ZERO_DENOM")
    )


def features_for_year(
    greeks: pd.DataFrame | None, oi: pd.DataFrame | None, root: str, year: int
) -> tuple[pd.DataFrame, dict]:
    """One row per canonical raw date; all feature values nullable with reason codes."""
    q: Counter = Counter({key: 0 for key in _COUNTER_KEYS})
    raw_dates = _raw_dates(greeks, root, year, "greeks", q) | _raw_dates(
        oi, root, year, "oi", q
    )
    g = _normalise_greeks(greeks, root, year, q)
    o = _normalise_oi(oi, root, year, q)
    q["greeks_valid_rows"] = len(g)
    q["oi_valid_rows"] = len(o)
    if not o.empty:
        o = o.rename(columns={"open_interest": "oi"})
    totals = (
        o[np.isfinite(o["oi"]) & o["oi"].gt(0)].groupby("date")["oi"].sum()
        if not o.empty
        else pd.Series(dtype=float)
    )
    q["oi_total_dates"] = len(totals)
    if g.empty and o.empty:
        merged = pd.DataFrame(columns=[*_ID, "oi", "_merge"])
    elif o.empty:
        merged = g.copy()
        merged["oi"] = np.nan
        merged["_merge"] = "left_only"
    elif g.empty:
        merged = o.copy()
        merged["_merge"] = "right_only"
    else:
        merged = g.merge(
            o[_ID + ["oi"]], on=_ID, how="outer", indicator=True, validate="one_to_one"
        )
    q["greeks_unmatched_rows"] = int(merged["_merge"].eq("left_only").sum())
    q["oi_unmatched_rows"] = int(merged["_merge"].eq("right_only").sum())
    q["joined_rows"] = int(merged["_merge"].eq("both").sum())
    joined = merged[merged["_merge"].eq("both")].copy()
    groups = {d: x for d, x in joined.groupby("date", sort=False)}
    rows: list[dict[str, Any]] = []
    for d in sorted(raw_dates):
        row = {"date": pd.Timestamp(d), "root": root.upper(), **{c: None for c in _NUM}}
        row["oi_total"] = float(totals[d]) if d in totals.index else None
        row["oi_total_reason"] = (
            "OK" if row["oi_total"] is not None else "OI_TOTAL_UNAVAILABLE"
        )
        gd = groups.get(d)
        if gd is None or gd.empty:
            for f in _NUM[:-1]:
                row[f"{f}_reason"] = "NO_ONE_TO_ONE_JOINED_CONTRACTS"
        else:
            quote = (
                np.isfinite(gd["bid"])
                & gd["bid"].gt(0)
                & np.isfinite(gd["ask"])
                & gd["ask"].gt(0)
                & gd["bid"].le(gd["ask"])
                & np.isfinite(gd["spot"])
                & gd["spot"].gt(0)
                & np.isfinite(gd["iv"])
                & gd["iv"].ge(0.005)
                & np.isfinite(gd["oi"])
                & gd["oi"].gt(0)
            )
            q["joined_quote_excluded_rows"] += int((~quote).sum())
            good = gd.loc[quote].copy()
            if good.empty:
                for f in _NUM[:-1]:
                    row[f"{f}_reason"] = "NO_VALID_UNCROSSED_QUOTE"
            else:
                good["spot"] = float(good["spot"].median())
                good["root"] = root.upper()
                for greek, col in (
                    ("gamma", "net_gamma_norm"),
                    ("vanna", "net_vanna_norm"),
                    ("charm", "net_charm_norm"),
                ):
                    row[col], row[f"{col}_reason"] = _exposure(good, greek)
                row["cw_ivspread"], row["cw_ivspread_reason"] = _cw(good)
                row["skew"], row["skew_reason"] = _skew(good)
                row["atm_iv"] = _atm(good, 30.0, 15.0, 45.0)
                row["atm_iv_reason"] = (
                    "OK" if row["atm_iv"] is not None else "ATM_NEAR_STRICT_REFUSAL"
                )
                back = _atm(good, 90.0, 60.0, 120.0)
                row["term_slope"] = (
                    round(row["atm_iv"] - back, 6)
                    if row["atm_iv"] is not None and back is not None
                    else None
                )
                row["term_slope_reason"] = (
                    "OK" if row["term_slope"] is not None else "TERM_STRICT_REFUSAL"
                )
        for f in _NUM[:-1]:
            q[f"{f}_reason:{row.get(f'{f}_reason', 'UNSET')}"] += 1
        rows.append(row)
    cols = ["root", *_NUM, "oi_total_reason"] + [f"{f}_reason" for f in _NUM[:-1]]
    daily = (
        pd.DataFrame(rows).set_index("date").sort_index()
        if rows
        else pd.DataFrame(columns=cols, index=pd.DatetimeIndex([], name="date"))
    )
    daily.index = pd.DatetimeIndex(daily.index, name="date")
    quality = {
        "root": root.upper(),
        "year": year,
        "counts": dict(q),
        "per_date": {
            str(d.date()): {k: r[k] for k in daily.columns if k.endswith("_reason")}
            for d, r in daily.iterrows()
        },
    }
    return daily, quality


"""Research-only execution over the exact inputs bound by the frozen manifest."""
import argparse
from collections import Counter
from datetime import date
import json
import os
from pathlib import Path
import sys
import tempfile

import numpy as np
import pandas as pd
from scipy import stats

from engine.grading import fill_index, forward_metrics
from engine.flow_signals_grade import _has_split_seam, _spy_window_matches
from engine.options_dislocation import _d5_by_session
from lib import nyse_calendar
from scripts.research.options_history_gauntlet import _bh_fdr

FEATURES = {
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
GREEK_COLUMNS = [
    "root",
    "date",
    "expiration",
    "strike",
    "right",
    "bid",
    "ask",
    "underlying_price",
    "implied_vol",
    "delta",
    "gamma",
    "vanna",
    "charm",
]
OI_COLUMNS = ["root", "date", "expiration", "strike", "right", "open_interest"]


def study_sessions():
    return pd.DatetimeIndex(
        nyse_calendar.sessions_between(date(2017, 1, 1), date(2025, 12, 31))
    )


def read_prices(path):
    """Keep the native index and missing bars; never repair or substitute prices."""
    if not path.exists():
        return None, "PRICE_FILE_MISSING"
    table = pd.read_parquet(path, columns=["close"])
    index = pd.DatetimeIndex(table.index)
    if index.hasnans or index.has_duplicates or index.tz is not None:
        return None, "PRICE_INDEX_INVALID"
    if not index.equals(index.normalize()):
        return None, "PRICE_INDEX_NOT_DAILY"
    series = pd.Series(
        pd.to_numeric(table["close"], errors="coerce").to_numpy(), index=index
    )
    return series.sort_index(), None


def native_window(prices, t, h, expected):
    if prices is None:
        return None, None, "PRICE_UNAVAILABLE"
    fill = fill_index(prices, t)
    if fill is None:
        return None, None, "FILL_UNAVAILABLE"
    window = prices.iloc[fill : fill + h + 1]
    if not window.index.equals(expected):
        return None, None, "NATIVE_SESSION_WINDOW_MISMATCH"
    if not np.isfinite(window.to_numpy()).all() or (window <= 0).any():
        return None, None, "INVALID_WINDOW_PRICE"
    if _has_split_seam(prices, fill, h):
        return None, None, "SPLIT_SEAM"
    return fill, window, None


def label_at(prices, spy, t, h, era_end, expected):
    """Both targets use the same complete, native calendar window and seam gates."""
    empty = {"excess": np.nan, "rv": np.nan, "reason": None}
    if len(expected) != h + 1 or expected[-1] > era_end:
        return {**empty, "reason": "ERA_BOUNDARY_PURGE"}
    fill, window, reason = native_window(prices, t, h, expected)
    if reason:
        return {**empty, "reason": "ROOT_" + reason}
    spy_fill, _, reason = native_window(spy, t, h, expected)
    if reason:
        return {**empty, "reason": "SPY_" + reason}
    if not _spy_window_matches(prices, fill, spy, h, t.date().isoformat()):
        return {**empty, "reason": "SPY_WINDOW_MISMATCH"}
    root_return = forward_metrics(prices, t, horizons=(h,))[f"fwd_ret_{h}"]
    spy_return = forward_metrics(spy, t, horizons=(h,))[f"fwd_ret_{h}"]
    if root_return is None or spy_return is None:
        return {**empty, "reason": "CANONICAL_RETURN_UNAVAILABLE"}
    return {
        "excess": float(root_return - spy_return),
        "rv": float(np.std(np.diff(np.log(window.to_numpy())), ddof=1) * np.sqrt(252)),
        "reason": None,
    }


def add_calendar_changes(daily, root, prices, calendar):
    """Feature grids preserve missing dates. Native price series are never reindexed."""
    if daily.index.has_duplicates:
        raise ValueError("duplicate root/date aggregate")
    out = daily.reindex(calendar).copy()
    out["date"] = calendar
    out["underlying"] = root
    for name in ["atm_iv", "cw_ivspread", "skew", "oi_total"]:
        if name not in out:
            out[name] = np.nan
    for name in ["atm_iv", "cw_ivspread", "skew", "oi_total", *FEATURES.values()]:
        out[name] = pd.to_numeric(
            out.get(name, pd.Series(np.nan, index=calendar)), errors="coerce"
        ).astype(float)
    out["d5_atm_iv"] = _d5_by_session(out, "atm_iv")
    out["d5_cw_ivspread"] = _d5_by_session(out, "cw_ivspread")
    out["d5_skew"] = _d5_by_session(out, "skew")
    out["skew_accel"] = _d5_by_session(out, "d5_skew")
    oi_change = _d5_by_session(out, "oi_total")
    prior_oi = out["oi_total"] - oi_change
    out["doi5"] = oi_change / prior_oi.where(prior_oi > 0)
    out["vanna_relief"] = out.get("net_vanna_norm", np.nan) * -out["d5_atm_iv"]
    price_map = {} if prices is None else prices.to_dict()
    momentum = []
    for t in calendar:
        before = nyse_calendar.session_n_back(t.date(), 5)
        a, b = price_map.get(t, np.nan), price_map.get(pd.Timestamp(before), np.nan)
        momentum.append(
            float(a / b - 1)
            if np.isfinite(a) and np.isfinite(b) and a > 0 and b > 0
            else np.nan
        )
    out["mom5"] = momentum
    for feature in FEATURES.values():
        if feature not in out:
            out[feature] = np.nan
    return out


def rank_ic(x, y, min_roots=5):
    mask = np.isfinite(x) & np.isfinite(y)
    n = int(mask.sum())
    if n < min_roots:
        return None, n, "INSUFFICIENT_ROOTS"
    x, y = x[mask], y[mask]
    if np.ptp(x) == 0:
        return None, n, "CONSTANT_FEATURE"
    if np.ptp(y) == 0:
        return None, n, "CONSTANT_TARGET"
    value = float(stats.spearmanr(x, y).statistic)
    if not np.isfinite(value):
        return None, n, "INVALID_IC"
    return value, n, None


def effective_blocks(dates, h):
    end = None
    count = 0
    for t in sorted(dates):
        start = nyse_calendar.session_n_forward(pd.Timestamp(t).date(), 1)
        finish = nyse_calendar.session_n_forward(start, h)
        if end is None or start > end:
            count += 1
            end = finish
    return count


def calendar_hac(values, h):
    """Exact v1.1 estimator: canonical positions, zero absent residuals, no pair renormalization."""
    values = np.asarray(values, dtype=float)
    observed = np.isfinite(values)
    n = int(observed.sum())
    if n < 3:
        return {"reason": "INSUFFICIENT_HAC_OBSERVATIONS"}
    mean = float(values[observed].mean())
    u = np.where(observed, values - mean, 0.0)
    lag = min(max(int(np.floor(4 * (n / 100) ** (2 / 9))), 2 * h), n - 2)
    numerator = float(u @ u)
    for shift in range(1, lag + 1):
        numerator += 2 * (1 - shift / (lag + 1)) * float(u[shift:] @ u[:-shift])
    variance = numerator / (n * n)
    if not np.isfinite(variance) or variance <= 0:
        return {"reason": "DEGENERATE_HAC_VARIANCE", "lag": lag, "variance": variance}
    se = float(np.sqrt(variance))
    statistic = mean / se
    critical = float(stats.t.ppf(0.975, n - 1))
    return {
        "reason": None,
        "lag": lag,
        "variance": variance,
        "standard_error": se,
        "t_stat": statistic,
        "raw_p": float(2 * stats.t.sf(abs(statistic), n - 1)),
        "ci95": [mean - critical * se, mean + critical * se],
        "df": n - 1,
    }


def evaluate_cell(panels, roots, calendar, era, h, contrast):
    dates = calendar[(calendar >= era["start"]) & (calendar <= era["end"])]
    feature = FEATURES[contrast]
    target = ("rv" if contrast == "GEX_NORM_TO_FWD_RV" else "excess") + f"_{h}"
    series, baseline, ablation = [], [], []
    reasons, root_coverage = Counter(), Counter()
    values = []
    target_reasons = Counter()
    for t in dates:
        x = np.array([panels[r].at[t, feature] for r in roots], dtype=float)
        y = np.array([panels[r].at[t, target] for r in roots], dtype=float)
        m = np.array([panels[r].at[t, "mom5"] for r in roots], dtype=float)
        eligible = np.isfinite(x) & np.isfinite(y)
        for i, r in enumerate(roots):
            if eligible[i]:
                root_coverage[r] += 1
            reason = panels[r].at[t, f"label_reason_{h}"]
            if pd.notna(reason) and reason:
                target_reasons[str(reason)] += 1
        ic, n, reason = rank_ic(x, y)
        values.append(np.nan if ic is None else ic)
        if reason:
            reasons[reason] += 1
        else:
            series.append({"date": t.date().isoformat(), "ic": ic, "n_roots": n})
        if contrast != "MOM5_BASELINE_TO_SPY_EXCESS":
            paired = eligible & np.isfinite(m)
            a, _, _ = rank_ic(x[paired], y[paired])
            b, _, _ = rank_ic(m[paired], y[paired])
            if a is not None and b is not None:
                baseline.append(
                    {
                        "date": t.date().isoformat(),
                        "ic_difference": a - b,
                        "n_roots": int(paired.sum()),
                    }
                )
        if contrast == "VANNA_RELIEF_TO_SPY_EXCESS":
            v = np.array(
                [panels[r].at[t, "net_vanna_norm"] for r in roots], dtype=float
            )
            paired = eligible & np.isfinite(v)
            a, _, _ = rank_ic(x[paired], y[paired])
            b, _, _ = rank_ic(v[paired], y[paired])
            if a is not None and b is not None:
                ablation.append(
                    {
                        "date": t.date().isoformat(),
                        "ic_difference": a - b,
                        "n_roots": int(paired.sum()),
                    }
                )
    observed = [row["ic"] for row in series]
    blocks = effective_blocks([row["date"] for row in series], h)
    result = {
        "id": f"{contrast}.{era['id']}.{h}",
        "contrast": contrast,
        "era": era["id"],
        "horizon": h,
        "feature": feature,
        "target": target,
        "n_dates": len(series),
        "n_root_date_pairs": sum(row["n_roots"] for row in series),
        "canonical_dates": len(dates),
        "nominal_root_date_slots": len(dates) * len(roots),
        "effective_blocks": blocks,
        "mean_ic": float(np.mean(observed)) if observed else None,
        "median_ic": float(np.median(observed)) if observed else None,
        "date_exclusions": dict(reasons),
        "target_exclusions": dict(target_reasons),
        "root_eligible_pairs": {r: root_coverage[r] for r in roots},
        "ic_series": series,
        "state": "NON_EVALUABLE",
        "reason": None,
        "raw_p": None,
        "ci95": None,
        "bh_adj_p": None,
        "bh_rank": None,
        "bh_reject": False,
    }
    if len(series) < 126:
        result["reason"] = "INSUFFICIENT_IC_DATES"
    elif blocks < 30:
        result["reason"] = "INSUFFICIENT_NONOVERLAPPING_BLOCKS"
    else:
        inference = calendar_hac(values, h)
        if inference["reason"]:
            result["reason"] = inference["reason"]
        else:
            result.update(inference)
            result["state"] = "EVALUABLE"
    for name, rows in [
        ("versus_momentum_descriptive", baseline),
        ("vanna_ablation_descriptive", ablation),
    ]:
        result[name] = {
            "n_dates": len(rows),
            "mean_paired_ic_difference": (
                float(np.mean([r["ic_difference"] for r in rows])) if rows else None
            ),
            "series": rows,
            "inferential_test": False,
        }
    return result


def run_analysis(
    manifest, manifest_sha, store, price_store, protocol_path, source_root
):
    """All reads use the same roots passed to manifest verification; there is no fixture data ingress."""
    verify_manifest(
        manifest, manifest_sha, store, price_store, protocol_path, source_root
    )
    protocol = load_protocol(protocol_path)
    roots = protocol["population"]["scored_roots"]
    calendar = study_sessions()
    spy, spy_reason = read_prices(price_store / "SPY.parquet")
    panels, quality = {}, {
        "spy_price_reason": spy_reason,
        "root_years": [],
        "root_coverage": {},
    }
    for root in roots:
        frames = []
        print(f"aggregate {root}", file=sys.stderr, flush=True)
        for year in range(2017, 2026):
            gp, op = (
                store / "greeks" / root / f"{year}.parquet",
                store / "oi" / root / f"{year}.parquet",
            )
            g = pd.read_parquet(gp, columns=GREEK_COLUMNS) if gp.exists() else None
            o = pd.read_parquet(op, columns=OI_COLUMNS) if op.exists() else None
            daily, receipt = features_for_year(g, o, root, year)
            quality["root_years"].append(receipt)
            frames.append(daily)
            del g, o
        combined = pd.concat(frames).sort_index()
        prices, price_reason = read_prices(price_store / f"{root}.parquet")
        panel = add_calendar_changes(combined, root, prices, calendar)
        counts = {
            "price_reason": price_reason,
            "canonical_dates": len(calendar),
            "features": {
                f: int(np.isfinite(panel[f]).sum()) for f in FEATURES.values()
            },
        }
        for h in protocol["horizons_nyse_sessions"]:
            labels = []
            for i, t in enumerate(calendar):
                era_end = next(
                    pd.Timestamp(e["end"])
                    for e in protocol["eras"]
                    if e["start"] <= t.date().isoformat() <= e["end"]
                )
                labels.append(
                    label_at(prices, spy, t, h, era_end, calendar[i + 1 : i + h + 2])
                )
            panel[f"excess_{h}"] = [v["excess"] for v in labels]
            panel[f"rv_{h}"] = [v["rv"] for v in labels]
            panel[f"label_reason_{h}"] = [v["reason"] for v in labels]
            counts[f"label_reasons_{h}"] = dict(
                Counter(v["reason"] or "EVALUABLE" for v in labels)
            )
        quality["root_coverage"][root] = counts
        panels[root] = panel
    cells = [
        evaluate_cell(panels, roots, calendar, era, h, contrast)
        for era in protocol["eras"]
        for h in protocol["horizons_nyse_sessions"]
        for contrast in FEATURES
    ]
    pvalues = {
        c["id"]: c["raw_p"]
        for c in cells
        if c["state"] == "EVALUABLE" and c["raw_p"] is not None
    }
    adjusted = _bh_fdr(pvalues, k_family=60, alpha=0.1)
    for cell in cells:
        if cell["id"] in adjusted:
            b = adjusted[cell["id"]]
            cell.update(
                bh_adj_p=float(b["bh_adj_p"]),
                bh_rank=int(b["rank"]),
                bh_reject=bool(b["reject_h0"]),
            )
    result = {
        "study_id": protocol["study_id"],
        "protocol_sha256": sha_file(protocol_path),
        "manifest_sha256": manifest_sha,
        "pit_status": "PIT_UNPROVEN",
        "research_only": True,
        "historical_alpha_validated": False,
        "n_cells": len(cells),
        "family_size": 60,
        "bh_alpha": 0.1,
        "cells": cells,
        "quality": quality,
        "unsupported": protocol["costs_and_unsupported"],
        "interpretation": "Retrospective associations; BH correction covers this 60-cell run, not historical program-wide trial selection. No OOS, option PnL, calibration or production promotion.",
    }
    # Validate JSON and rerun the full input binding before returning any final result.
    canonical_bytes(result)
    verify_manifest(
        manifest, manifest_sha, store, price_store, protocol_path, source_root
    )
    return result


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def load_manifest_file(path, expected_sha):
    raw = path.read_bytes()
    if sha_bytes(raw) != expected_sha:
        raise ValueError("manifest file hash mismatch")
    value = json.loads(raw, object_pairs_hook=_unique_object)
    if canonical_bytes(value) != raw:
        raise ValueError("manifest must use the frozen canonical encoding")
    return value


def write_artifact(path, content, input_roots):
    """Create a new immutable artifact atomically; never overwrite source or inputs."""
    target = path.resolve()
    if any(target.is_relative_to(root.resolve()) for root in input_roots):
        raise ValueError("output must be outside source and input directories")
    if target.exists():
        raise FileExistsError(f"artifact already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=target.parent, prefix=target.name + ".", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, target)  # Atomic creation fails if another writer won.
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Frozen Theta retrospective study; research only"
    )
    parser.add_argument("mode", choices=["prepare-manifest", "analyze"])
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--price-store", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--manifest-sha")
    args = parser.parse_args(argv)
    source_root = Path(__file__).resolve().parents[2]
    if args.mode == "prepare-manifest":
        value = prepare_manifest(
            args.store, args.price_store, args.protocol, source_root
        )
    else:
        if args.manifest is None or not args.manifest_sha:
            parser.error("analyze requires --manifest and --manifest-sha")
        manifest = load_manifest_file(args.manifest, args.manifest_sha)
        value = run_analysis(
            manifest,
            args.manifest_sha,
            args.store,
            args.price_store,
            args.protocol,
            source_root,
        )
    content = canonical_bytes(value)
    write_artifact(args.out, content, [args.store, args.price_store, source_root])
    print(
        json.dumps(
            {"artifact": str(args.out), "sha256": sha_bytes(content), "mode": args.mode}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
