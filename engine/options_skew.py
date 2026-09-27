"""Single-name implied-volatility SKEW — the Xing-Zhang-Zhao (2010) cross-sectional
return predictor: steep OTM-put-over-ATM-call IV (informed put buying / crash fear)
historically preceded LOWER forward returns.

This computes skew = IV(25-delta OTM put) − IV(50-delta ATM call) at the ~30-day
expiry, per underlying, from the ThetaData chain store (engine/thetadata_store.py
`chain()`/`make_chain_provider()`) — columns underlying, expiry, K, T, iv, delta,
is_call, spot, oi, volume, asof.

The legacy `data/polygon_gex/chains/<date>.parquet` glob is RETIRED: it is reachable
only behind the explicit, off-by-default `OPTIONS_SKEW_LEGACY_CHAIN=1` env flag, and
is never used as an automatic fallback. As of 2026-08-13 the legacy store had reached
372 underlyings / 185,072 rows on its newest date — the earlier "~10 mega-cap
underlyings" claim here was stale; both that framing and F00B's "ThetaData canonical"
claim for this leg were superseded by the measured migration in MO-PAID-013.

HONEST STATE — DISPLAY-ONLY / NOT SCORED. This builds the SIGNAL + a forward-accruing
snapshot ledger + a dormant validation gate (scripts/validate_options_skew.py); the
gate stays closed — and the leg stays context — until the panel is wide and long
enough to earn a verdict. PURE compute; disk IO is isolated in snapshot()/load_*/
load_chain().

`backfill_from_store` recomputes an explicit list of dates from the ThetaData
store and upserts them under the same canonical-wins rule as `snapshot`.
`emit_from_ledger` drops weekend-dated rows, then drops any newer ledger
session whose row count is below `_THIN_SESSION_MIN_FRACTION × widest(count
of the up-to-10 immediately older sessions)` — a partial newest session
that would otherwise collapse the live surface from 372 → 12 — and reports
the skip in `source_detail["partial_sessions_skipped"]` /
`source_detail["partial_rows_skipped"]` (always present, possibly
empty/zero). `complete_store_session(td)` resolves the accrual session as
the newest date whose distinct greeks root count is at least
`_COMPLETE_SESSION_MIN_FRACTION × widest` (the FULL S panel the T1 daily
maintainer writes for `session_n_back(D, 1)`), with `<td>/_manifest.json`'s
`daily_refresh.S` winning on tie.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from lib import config

log = logging.getLogger(__name__)

SCHEMA = "options_skew.v1"
# The nine ledger columns, in the order the pre-packet writer emitted them.
# `source` is additive (polygon_gex | thetadata). A ledger written before this
# column existed is read as polygon_gex — it is not rewritten just to backfill.
_LEDGER_COLUMNS = (
    "date", "underlying", "asof", "spot", "tenor_days",
    "otm_put_iv", "atm_call_iv", "skew", "n_strikes", "source",
)
_SOURCE_POLYGON = "polygon_gex"
_SOURCE_THETA = "thetadata"
_DISCLAIMER = (
    "Single-name IV skew (25Δ OTM put − 50Δ ATM call, ~30d). "
    "DISPLAY-ONLY context: the chain panel is too narrow/short to "
    "validate as a return predictor — accruing toward a verdict."
)
_TARGET_DAYS = 30.0            # ~1-month tenor (Xing-Zhang-Zhao)
_MIN_DAYS = 7.0
_PUT_DELTA = -0.25            # OTM put target
_CALL_DELTA = 0.50           # ATM call target

# Legacy polygon_gex chain glob — RETIRED. Only reachable when this env flag is
# explicitly set; never an automatic fallback from a ThetaData failure.
_LEGACY_CHAIN_ENV = "OPTIONS_SKEW_LEGACY_CHAIN"

# Strike-unit sanity bounds for K/spot moneyness — outside this band the strike
# column is not in the units this engine assumes (see load_chain step 7).
_MONEYNESS_MIN = 0.2
_MONEYNESS_MAX = 5.0

# A chain older than this many calendar days is published but flagged stale.
_STALE_DAYS = 5

# A store date is a complete panel when its distinct greeks root count is at
# least this fraction of the widest date's count. The store writes the FULL
# S panel (372-378 roots) for S = the session BEFORE the last completed one,
# then a 12-root priority set hours earlier for the newest D — so a partial
# D shows up with ~3% of the widest panel and falls below the threshold.
_COMPLETE_SESSION_MIN_FRACTION = 0.5

# A ledger session is thin when its row count is below this fraction of the
# widest count among the up-to-10 immediately older sessions. Emit must skip
# thin newest sessions so the live surface does not collapse from 372 → 12.
_THIN_SESSION_MIN_FRACTION = 0.5

# How far back `catch_up_sessions` walks from the complete store session to
# the most recent complete ledger session. Five is enough to cover a long
# weekend plus a holiday; anything older needs an explicit `--backfill`.
_CATCH_UP_MAX_SESSIONS = 5


def _nearest_expiry(rows, target_days: float = _TARGET_DAYS, min_days: float = _MIN_DAYS):
    """The single expiry whose tenor is closest to `target_days` (≥ min_days). Returns
    a filtered frame or None. `rows` is one underlying's chain (column T in YEARS)."""
    try:
        df = rows.copy()
        df["_days"] = df["T"].astype(float) * 365.0
        cand = df[df["_days"] >= min_days]
        if cand.empty:
            cand = df[df["_days"] > 0]        # all short-dated → take the longest LIVE expiry
        if cand.empty:                        # only expired/0DTE rows → no usable tenor
            return None
        target_exp = cand.loc[(cand["_days"] - target_days).abs().idxmin(), "expiry"]
        return df[df["expiry"] == target_exp]
    except Exception as e:  # noqa: BLE001
        log.debug("nearest expiry failed (%s)", e)
        return None


def _iv_at_delta(leg, target_delta: float, want_call: bool):
    """IV of the option whose delta is closest to target (delta-first), falling back to
    moneyness if delta is unusable. Returns (iv, used_delta, K) or None."""
    import pandas as pd
    sub = leg[(leg["is_call"] == want_call) & (leg["iv"] > 0.0)]
    if sub.empty:
        return None
    d = pd.to_numeric(sub["delta"], errors="coerce")
    if d.notna().sum() >= 1 and d.abs().between(0.02, 0.98).any():
        sub = sub.assign(_dd=(d - target_delta).abs())
        r = sub.loc[sub["_dd"].idxmin()]
        return float(r["iv"]), float(r["delta"]), float(r["K"])
    # moneyness fallback: 25-delta put ≈ K/S 0.95, ATM call ≈ K/S 1.0
    spot = float(sub["spot"].iloc[0])
    if spot <= 0:
        return None
    target_mny = 1.0 if want_call else 0.95
    sub = sub.assign(_mm=(sub["K"].astype(float) / spot - target_mny).abs())
    r = sub.loc[sub["_mm"].idxmin()]
    return float(r["iv"]), float("nan"), float(r["K"])


def compute_skew(rows, drops: dict | None = None) -> dict | None:
    """Implied skew for one underlying's chain frame. PURE.
    Returns {underlying, asof, spot, tenor_days, otm_put_iv, atm_call_iv, skew, ...}.

    `drops` is an optional out-parameter dict the caller may pass so a rejected
    name can be classified by WHICH leg was unusable (never inferred after the
    fact) — compute_skew's own signature/return are otherwise unchanged."""
    try:
        if rows is None or getattr(rows, "empty", True):
            return None
        underlying = str(rows["underlying"].iloc[0]).upper() if "underlying" in rows.columns else None
        leg = _nearest_expiry(rows)
        if leg is None or leg.empty:
            if drops is not None and underlying:
                drops.setdefault("no_25d_put", []).append(underlying)
                drops.setdefault("no_atm_call", []).append(underlying)
            return None
        # No four-strike floor. The polygon builder published a name as soon as
        # the chosen expiry had a put and a call, including a two-row expiry.
        # A floor here drops those names from the live surface.
        put = _iv_at_delta(leg, _PUT_DELTA, want_call=False)
        call = _iv_at_delta(leg, _CALL_DELTA, want_call=True)
        if put is None or call is None:
            if drops is not None and underlying:
                if put is None:
                    drops.setdefault("no_25d_put", []).append(underlying)
                if call is None:
                    drops.setdefault("no_atm_call", []).append(underlying)
            return None
        otm_put_iv, _, _ = put
        atm_call_iv, _, _ = call
        skew = otm_put_iv - atm_call_iv
        spot = float(leg["spot"].iloc[0])
        tenor = float(leg["T"].astype(float).iloc[0] * 365.0)
        asof = leg["asof"].iloc[0]
        asof = str(asof.date()) if hasattr(asof, "date") else str(asof)[:10]
        return {
            "underlying": str(leg["underlying"].iloc[0]).upper(),
            "asof": asof, "spot": round(spot, 4),
            "tenor_days": round(tenor, 1),
            "otm_put_iv": round(otm_put_iv, 4),
            "atm_call_iv": round(atm_call_iv, 4),
            "skew": round(skew, 4),
            "n_strikes": int(len(leg)),
        }
    except Exception as e:  # noqa: BLE001
        log.debug("compute_skew failed (%s)", e)
        return None


def skew_map(chain, drops: dict | None = None) -> dict[str, dict]:
    """{underlying: skew metrics} over a full chain snapshot (many underlyings). PURE.

    `drops` (optional) collects per-underlying rejection reasons — see compute_skew."""
    out: dict[str, dict] = {}
    try:
        if chain is None or getattr(chain, "empty", True) or "underlying" not in chain.columns:
            return out
        for u, g in chain.groupby("underlying"):
            m = compute_skew(g, drops=drops)
            if m is not None:
                out[str(u).upper()] = m
    except Exception as e:  # noqa: BLE001
        log.debug("skew_map failed (%s)", e)
    return out


# --------------------------------------------------------------------------- #
# Disk: forward-accruing snapshot ledger (the apparatus that earns a verdict over time)
# --------------------------------------------------------------------------- #
def _snap_path():
    p = config.data_dir() / "options_skew"
    p.mkdir(parents=True, exist_ok=True)
    return p / "snapshots.parquet"


def _legacy_enabled() -> bool:
    import os
    return os.environ.get(_LEGACY_CHAIN_ENV, "").strip() in ("1", "true", "TRUE", "yes")


def _legacy_chain():
    """RETIRED polygon_gex path. Only reachable when OPTIONS_SKEW_LEGACY_CHAIN=1."""
    import glob
    import pandas as pd
    files = sorted(glob.glob(str(config.data_dir() / "polygon_gex" / "chains" / "*.parquet")))
    return pd.read_parquet(files[-1]) if files else None


def _greeks_roots_by_date(td) -> dict[str, int]:
    """Distinct greeks-root counts per YYYY-MM-DD — same walk as
    `_latest_store_date`, but returns the FULL histogram so the complete-session
    resolver can compare breadth across dates instead of trusting the
    single newest stamp (which is the 12-root priority set on the store host)."""
    import pandas as pd
    counts: dict[str, set[str]] = {}
    base = td / "greeks"
    if not base.exists():
        return {}
    for root_dir in sorted(base.iterdir()):
        if not root_dir.is_dir():
            continue
        root = root_dir.name
        for f in sorted(root_dir.glob("*.parquet")):
            try:
                df = pd.read_parquet(f, columns=["date"])
            except Exception as e:  # noqa: BLE001
                log.debug("_greeks_roots_by_date read failed for %s (%s)", f, e)
                continue
            for stamp in pd.to_datetime(df["date"]).dt.date.astype(str).unique().tolist():
                counts.setdefault(stamp, set()).add(root)
    return {stamp: len(roots) for stamp, roots in counts.items()}


def _latest_store_date(td) -> str | None:
    """Max `date` across every {td}/greeks/*/*.parquet — same enumeration
    scripts/validate_options_skew.py uses to walk the store. Behaviour
    unchanged; backed by the same `_greeks_roots_by_date` walk."""
    counts = _greeks_roots_by_date(td)
    return max(counts) if counts else None


def complete_store_session(td) -> dict:
    """Pick the COMPLETE panel the lane should accrue, never a partial newest.

    The store writes the FULL S panel (372-378 roots) for S = the session
    BEFORE the last completed one, then a 12-root priority set hours earlier
    for the newest D. `_latest_store_date` returns D (12 roots), so an
    accrual keyed off it would collapse the live surface from 372 → 12.

    Two sources are consulted and the newer wins; ISO date strings compare
    lexicographically:
      - `breadth`: the newest date in `_greeks_roots_by_date(td)` whose
        distinct root count is at least `_COMPLETE_SESSION_MIN_FRACTION`
        of the widest panel.
      - `manifest`: `<td>/_manifest.json`'s `daily_refresh.S` when it is a
        10-char ISO date string AND `daily_refresh.greeks_S_roots` is at
        least `_COMPLETE_SESSION_MIN_FRACTION * widest` (falling back to
        `>= 1` when the store is empty — so a brand-new manifest still
        picks itself on day one).

    Returns exactly `{session, newest_raw, method, partial_skipped,
    roots_on_session, widest_roots}`. `method` is "manifest" when the
    manifest value tied or won, "breadth" when breadth won, "none" when
    neither resolved. Never raises; missing/unparseable manifest keys
    are ignored."""
    import json
    counts = _greeks_roots_by_date(td)
    widest = max(counts.values()) if counts else 0
    threshold = _COMPLETE_SESSION_MIN_FRACTION * widest
    if widest == 0:
        threshold = 1.0  # brand-new manifest on an empty store still wins

    breadth_session: str | None = None
    for stamp in sorted(counts.keys()):
        if counts[stamp] >= threshold:
            breadth_session = stamp  # last assignment = newest

    manifest_session: str | None = None
    try:
        manifest_path = td / "_manifest.json"
        if manifest_path.exists():
            payload = json.loads(manifest_path.read_text())
            daily = (payload or {}).get("daily_refresh") or {}
            candidate = daily.get("S")
            greeks_roots = daily.get("greeks_S_roots")
            if (
                isinstance(candidate, str)
                and len(candidate) == 10
                and candidate[4] == "-"
                and candidate[7] == "-"
                and isinstance(greeks_roots, (int, float))
                and not isinstance(greeks_roots, bool)
                and float(greeks_roots) >= threshold
            ):
                manifest_session = candidate
    except Exception as e:  # noqa: BLE001
        log.debug("complete_store_session manifest read failed (%s)", e)

    candidates = [s for s in (breadth_session, manifest_session) if s]
    if not candidates:
        session: str | None = None
        method = "none"
    elif manifest_session is not None and (
        breadth_session is None or manifest_session >= breadth_session
    ):
        session = manifest_session
        method = "manifest"
    else:
        session = breadth_session
        method = "breadth"

    newest_raw = max(counts) if counts else None
    partial_skipped: list[str] = sorted(
        stamp for stamp in counts if session and stamp > session
    )
    return {
        "session": session,
        "newest_raw": newest_raw,
        "method": method,
        "partial_skipped": partial_skipped,
        "roots_on_session": counts.get(session) if session else None,
        "widest_roots": widest,
    }


def load_chain(asof: str | None = None, store=None, roots: list[str] | None = None):
    """Load one dated cross-sectional chain frame from the ThetaData store.

    Returns (frame_or_None, state) where state is one of the typed §5 states
    (see build_snapshot). frame columns are exactly the schema
    make_chain_provider emits: underlying, expiry, K, T, iv, delta, is_call,
    spot, oi, volume, asof. PURE except for the store read; never raises.
    """
    import pandas as pd
    from engine.thetadata_store import resolve_thetadata_store, universe, make_chain_provider

    td = store if store is not None else resolve_thetadata_store(
        required=False, purpose="options_skew chain")
    if td is None:
        print("::warning title=options-skew-source::ThetaData store unresolved — "
              "skew emits null (set THETADATA_STORE)", flush=True)
        return None, "thetadata_store_unresolved"

    if asof is None:
        info = complete_store_session(td)
        resolved_asof = info["session"]
        if info["partial_skipped"]:
            skipped = ", ".join(info["partial_skipped"])
            roots_on_session = info["roots_on_session"]
            print(
                f"::notice title=options-skew-session::accruing complete store "
                f"session {resolved_asof} ({roots_on_session} roots, "
                f"{info['method']}); newer partial session(s) skipped: {skipped}",
                flush=True,
            )
    else:
        resolved_asof = asof
    if not resolved_asof:
        return None, "no_iv_tier"

    use_roots = roots if roots is not None else universe(resolved_asof, store=td)
    if not use_roots:
        return None, "no_roots_for_date"

    provider = make_chain_provider(store=td, require_iv=True)
    frames = []
    for root in use_roots:
        f = provider(resolved_asof, root)
        if f is None or f.empty:
            continue
        frames.append(f)

    if not frames:
        return None, "no_chain_for_date"

    frame = pd.concat(frames, ignore_index=True)

    # Strike-unit sanity check — never rescale K ourselves; an unproven unit is
    # a null, not a guess (moneyness fallback in _iv_at_delta divides K/spot).
    try:
        mny = float(frame["K"].astype(float).median()) / float(frame["spot"].astype(float).median())
    except Exception:  # noqa: BLE001
        mny = float("nan")
    import math
    if math.isnan(mny) or not (_MONEYNESS_MIN <= mny <= _MONEYNESS_MAX):
        print("::warning title=options-skew-source::strike/spot moneyness "
              f"{mny!r} outside [{_MONEYNESS_MIN},{_MONEYNESS_MAX}] — unit unresolved",
              flush=True)
        return None, "strike_unit_unresolved"

    return frame, "ok"


def _iso_date(value) -> str:
    """Calendar day as YYYY-MM-DD. Timestamps and date objects collapse to that day."""
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


def _source_of(value) -> str:
    """A missing source column (or a blank cell) is the legacy polygon ledger."""
    if value is None:
        return _SOURCE_POLYGON
    try:
        import pandas as pd
        if pd.isna(value):
            return _SOURCE_POLYGON
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if text in ("", "None", "nan", "NaN", "<NA>"):
        return _SOURCE_POLYGON
    return text


def _atomic_write_parquet(df, path) -> None:
    """Write `path` via temp file + os.replace in the same directory.

    A crash mid-write leaves the previous ledger in place. os.replace on the
    same directory is atomic on POSIX, which is what the render hosts are.
    """
    import os
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.{os.getpid()}.tmp"
    try:
        df.to_parquet(tmp)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _ledger_frame(rows: list[dict]):
    import pandas as pd
    return pd.DataFrame([{col: rec.get(col) for col in _LEDGER_COLUMNS} for rec in rows],
                        columns=list(_LEDGER_COLUMNS))


def _ledger_unchanged(prev, proposed) -> bool:
    """True when the proposed upsert would not change a single stored value.

    The source column is compared after the missing-column → polygon_gex read,
    so a legacy file is left untouched until a row actually changes.
    """
    import numpy as np
    if len(prev) != len(proposed):
        return False
    left = _normalize_ledger(prev).sort_values(["date", "underlying"]).reset_index(drop=True)
    right = _normalize_ledger(proposed).sort_values(["date", "underlying"]).reset_index(drop=True)
    if len(left) != len(right):
        return False
    for col in ("spot", "tenor_days", "otm_put_iv", "atm_call_iv", "skew"):
        if not np.allclose(left[col].astype(float), right[col].astype(float),
                           rtol=0, atol=1e-9, equal_nan=True):
            return False
    if list(left["n_strikes"].astype(int)) != list(right["n_strikes"].astype(int)):
        return False
    for col in ("date", "underlying", "asof", "source"):
        if list(left[col].astype(str)) != list(right[col].astype(str)):
            return False
    return True


def _normalize_ledger(df):
    """Project a ledger frame onto the contract columns. Missing source → polygon_gex."""
    import pandas as pd
    rows = []
    for rec in df.to_dict(orient="records"):
        rows.append({
            "date": _iso_date(rec.get("date")),
            "underlying": str(rec.get("underlying", "")).upper(),
            "asof": _iso_date(rec.get("asof")),
            "spot": float(rec.get("spot")),
            "tenor_days": float(rec.get("tenor_days")),
            "otm_put_iv": float(rec.get("otm_put_iv")),
            "atm_call_iv": float(rec.get("atm_call_iv")),
            "skew": float(rec.get("skew")),
            "n_strikes": int(rec.get("n_strikes")),
            "source": _source_of(rec.get("source")),
        })
    return pd.DataFrame(rows, columns=list(_LEDGER_COLUMNS))


def snapshot(today: date | None = None, chain=None, source: str | None = None) -> int:
    """UPSERT today's per-underlying skew, keyed by (date, underlying).

    `source` is `polygon_gex` or `thetadata`. A thetadata row replaces a
    polygon_gex row for the same key. A polygon_gex row never replaces a
    thetadata row. Returns the number of rows inserted or replaced. The file
    is replaced atomically and is not rewritten when nothing changed.

    The date key is the chain's own as-of, not wall-clock `today` — a stale
    chain must not be recorded under today's date.
    """
    today = today or date.today()
    if chain is None and source is None:
        if _legacy_enabled():
            chain = _legacy_chain()
            source = _SOURCE_POLYGON
        else:
            chain, state = load_chain()
            if state == "thetadata_store_unresolved" or chain is None:
                return 0
            source = _SOURCE_THETA
    if source is None:
        source = _SOURCE_POLYGON if _legacy_enabled() else _SOURCE_THETA
    if source not in (_SOURCE_POLYGON, _SOURCE_THETA):
        raise ValueError(f"ledger source must be polygon_gex or thetadata, got {source!r}")
    if chain is None or getattr(chain, "empty", True):
        return 0
    rows = [{"date": (m.get("asof") or today.isoformat()), **m, "source": source}
            for m in skew_map(chain).values()]
    if not rows:
        return 0
    fresh = _normalize_ledger(_ledger_frame(rows))
    p = _snap_path()
    if p.exists():
        import pandas as pd
        prev = _normalize_ledger(pd.read_parquet(p))
        by_key: dict[tuple[str, str], dict] = {}
        order: list[tuple[str, str]] = []
        for rec in prev.to_dict(orient="records"):
            key = (rec["date"], rec["underlying"])
            if key not in by_key:
                order.append(key)
            by_key[key] = rec
        changed = 0
        for rec in fresh.to_dict(orient="records"):
            key = (rec["date"], rec["underlying"])
            old = by_key.get(key)
            if old is None:
                by_key[key] = rec
                order.append(key)
                changed += 1
                continue
            if source == _SOURCE_POLYGON and old["source"] == _SOURCE_THETA:
                continue
            if rec == old:
                continue
            by_key[key] = rec
            changed += 1
        if changed == 0:
            return 0
        proposed = _ledger_frame([by_key[key] for key in order])
        if _ledger_unchanged(prev, proposed):
            return 0
        _atomic_write_parquet(proposed, p)
        return changed
    _atomic_write_parquet(fresh, p)
    return int(len(fresh))


def load_history():
    import pandas as pd
    p = _snap_path()
    return pd.read_parquet(p) if p.exists() else None


def _is_weekend_iso(value: str) -> bool:
    """True for a Saturday or Sunday calendar day. Anything else is not a weekend."""
    try:
        return date.fromisoformat(str(value)[:10]).weekday() >= 5
    except ValueError:
        return False


def _per_source_coverage(df) -> list[dict]:
    """Per-SOURCE coverage spans over session (weekday) dates.

    Returns one dict per source present on the ledger, sorted by
    (first_date, source):
      {"source": str, "first_date": "YYYY-MM-DD",
       "last_date": "YYYY-MM-DD", "n_dates": int}
    where `n_dates` is the count of distinct weekday dates on which that
    source has at least one row.

    Session-only dates: weekend as-of rows are excluded before the per-date
    group, mirroring `emit_from_ledger`'s session-only pick — a Saturday-only
    ledger therefore returns [] (no session to count, not a Saturday window).
    A missing `source` column reads as polygon_gex (the legacy default).

    PURE (no I/O, no clock); empty/invalid input returns [].
    """
    if df is None or getattr(df, "empty", True):
        return []
    try:
        import pandas as pd
    except Exception:  # noqa: BLE001
        return []
    if "date" not in df.columns:
        return []
    work = df.copy()
    if "source" not in work.columns:
        work["source"] = _SOURCE_POLYGON
    else:
        work["source"] = work["source"].map(_source_of)
    work["date"] = work["date"].map(_iso_date)
    work = work[work["date"].astype(str).str.len() > 0]
    if work.empty:
        return []
    weekend = work["date"].map(_is_weekend_iso)
    if bool((~weekend).any()):
        work = work.loc[~weekend]
    else:
        return []
    out: list[dict] = []
    for source_name, group in work.groupby("source"):
        dates = sorted({str(d) for d in group["date"].tolist() if d})
        if not dates:
            continue
        out.append({
            "source": str(source_name),
            "first_date": dates[0],
            "last_date": dates[-1],
            "n_dates": len(dates),
        })
    out.sort(key=lambda row: (row["first_date"], row["source"]))
    return out


def source_windows(df) -> list[dict]:
    """Coverage spans per source across the session dates of a ledger.

    A-F03-W2-4c (round-5 measured-truth shape, after the 2026-08-14..2026-09-18
    backfill; per-source coverage on session dates — the 2026-06-21 Sunday
    as-of row is excluded): thetadata 2026-06-22..2026-09-21 on 64 session
    dates, polygon_gex 2026-06-22..2026-08-13 on 33 session dates, first
    ThetaData-only session = 2026-08-14.  The earlier per-date majority-run
    rule returned fifteen alternating windows — 8 ThetaData ranges + 7 Polygon
    ranges — that the Directional-read sentence could not print, and did not
    answer the reader's question ("can I compare today's skew with a month
    ago?").  The producer now publishes one coverage span per source present
    on the ledger, sorted by (first_date, source), and the consumer renders
    the sentence from those spans plus `source_break_date`.

    Session-only dates: weekend as-of rows are excluded before grouping
    (`_is_weekend_iso`), the same way `emit_from_ledger` already excludes
    them when it picks the latest session — a Saturday-only ledger returns
    [] (no session to count, not a fabricated Saturday window).

    PURE (no I/O, no clock); empty/invalid input returns [].
    """
    return _per_source_coverage(df)


def source_break_date(df) -> str | None:
    """The first session date strictly after the OLDER source's last_date.

    Using the same normalised weekday frame as `source_windows`, when at
    least two sources are present: `older_last` = the smallest `last_date`
    across sources; return the earliest weekday date strictly greater than
    `older_last` on which any OTHER source has rows.  Returns None when:
      · fewer than two sources are present (no boundary to name);
      · no such date is present (the older source is still the only one with
        rows, or both sources end on the same day);
      · input is empty/invalid.

    The "newer source has rows" check walks the ledger's ACTUAL rows for
    each newer source — not the span bounds — so a backfill gap (a newer
    source whose rows skip some dates inside its own coverage span) cannot
    fabricate a break date that the ledger itself never has a row for.
    On the live ledger (2026-09-23, after the 2026-08-14..2026-09-18
    backfill): polygon_gex.last_date = 2026-08-13, thetadata.last_date =
    2026-09-21, older_last = 2026-08-13, the earliest thetadata-only
    weekday strictly greater than 2026-08-13 that actually has a row is
    2026-08-14 → returns "2026-08-14".

    PURE (no I/O, no clock).
    """
    spans = _per_source_coverage(df)
    if len(spans) < 2:
        return None
    try:
        from datetime import date as _date, timedelta as _td
        older_last_text = min(str(span["last_date"]) for span in spans)
        older_last = _date.fromisoformat(older_last_text)
    except (ValueError, TypeError):
        return None
    # The "newer" sources are those whose last_date is strictly greater than
    # older_last — i.e. the sources still accruing past the older one's end.
    newer_source_names = {
        str(span["source"]) for span in spans
        if str(span["last_date"]) > older_last_text
    }
    if not newer_source_names:
        return None
    # Walk the ledger's ACTUAL rows for newer sources, not the span bounds.
    # A newer source's coverage span may interpolate over a backfill gap;
    # only dates that appear in the ledger as a row count as "the newer
    # source has rows".
    if df is None or getattr(df, "empty", True):
        return None
    work = df.copy()
    if "source" not in work.columns:
        work["source"] = _SOURCE_POLYGON
    else:
        work["source"] = work["source"].map(_source_of)
    work["date"] = work["date"].map(_iso_date)
    work = work[work["date"].astype(str).str.len() > 0]
    if "date" not in work.columns:
        return None
    weekend = work["date"].map(_is_weekend_iso)
    work = work.loc[~weekend]
    actual_newer_dates = {
        str(d) for d in work.loc[work["source"].isin(newer_source_names),
                                  "date"].astype(str).tolist()
    }
    if not actual_newer_dates:
        return None
    cursor = older_last + _td(days=1)
    # Walk at most 5 years past older_last as a safety bound (no real
    # backfill spans longer than this, and a non-terminating walk on a
    # bad ledger would otherwise hang the call site).
    max_walk = older_last + _td(days=5 * 366)
    while cursor <= max_walk:
        cursor_text = cursor.isoformat()
        if cursor_text in actual_newer_dates:
            return cursor_text
        cursor += _td(days=1)
    return None


def _chain_asof_dates(chain) -> set[str]:
    """Distinct YYYY-MM-DD stamps on a chain frame. Empty when the column is absent."""
    if chain is None or "asof" not in getattr(chain, "columns", []):
        return set()
    found: set[str] = set()
    for value in chain["asof"].tolist():
        if value is None:
            continue
        if hasattr(value, "date") and not isinstance(value, str):
            text = str(value.date())
        else:
            text = str(value).strip()
        text = text[:10]
        if text:
            found.add(text)
    return found


def _backfill_row_counts(chain, requested: str) -> dict[str, int]:
    """How many ledger keys this chain would replace, add, or leave unchanged.

    Counts against the ledger as it sits now. A polygon_gex row at the same
    (date, underlying) is a replacement. A missing key is an add. An equal
    thetadata row is unchanged. Does not write.
    """
    rows = [
        {"date": (metric.get("asof") or requested), **metric, "source": _SOURCE_THETA}
        for metric in skew_map(chain).values()
    ]
    if not rows:
        return {"rows_replaced": 0, "rows_added": 0, "rows_unchanged": 0}
    fresh = _normalize_ledger(_ledger_frame(rows))
    existing: dict[tuple[str, str], dict] = {}
    path = _snap_path()
    if path.exists():
        import pandas as pd
        prev = _normalize_ledger(pd.read_parquet(path))
        for rec in prev.to_dict(orient="records"):
            existing[(rec["date"], rec["underlying"])] = rec
    replaced = added = unchanged = 0
    for rec in fresh.to_dict(orient="records"):
        old = existing.get((rec["date"], rec["underlying"]))
        if old is None:
            added += 1
        elif old == rec:
            unchanged += 1
        else:
            # polygon_gex -> thetadata, or a thetadata row whose values differ.
            replaced += 1
    return {"rows_replaced": replaced, "rows_added": added, "rows_unchanged": unchanged}


def catch_up_sessions(target: str, hist, max_sessions: int = _CATCH_UP_MAX_SESSIONS) -> list[str]:
    """Dates the daily lane should backfill to catch up to the COMPLETE store session.

    Pure helper. `target` is the complete-session resolver's choice — the
    NEWEST date that has a full root panel. `hist` is the ledger frame (or
    None) — the lane's own accrued history. The ledger's newest COMPLETE
    session (`have`) is the newest thetadata date whose row count is at
    least `_THIN_SESSION_MIN_FRACTION × widest(counts among the up-to-10
    dates immediately older than it)`; a lone thetadata date is complete.

    Returns dates in ASCENDING order. `target` itself is always included;
    the rest are NYSE sessions walked BACKWARD from the latest session at
    or before `target`, stopping at `have` exclusive or after `max_sessions`
    total dates — whichever first. When `have is None` (no thetadata
    history) or no NYSE session exists at-or-before `target`, returns
    `[target]` only — the store decides whether that date has a panel.
    """
    from lib import nyse_calendar

    target_iso = str(target)[:10]
    try:
        target_date = date.fromisoformat(target_iso)
    except ValueError:
        return [target_iso]

    if hist is None or getattr(hist, "empty", True):
        return [target_iso]
    norm = _normalize_ledger(hist)
    weekday_theta = norm[
        (norm["source"] == _SOURCE_THETA) & (~norm["date"].map(_is_weekend_iso))
    ]
    if weekday_theta.empty:
        return [target_iso]

    counts: dict[str, int] = {}
    for stamp in weekday_theta["date"].tolist():
        if stamp:
            counts[stamp] = counts.get(stamp, 0) + 1
    sorted_dates = sorted(counts.keys())

    have: str | None = None
    for index in range(len(sorted_dates) - 1, -1, -1):
        stamp = sorted_dates[index]
        older_window = sorted_dates[:index][-10:]
        widest_older = max((counts[w] for w in older_window), default=0)
        threshold = _THIN_SESSION_MIN_FRACTION * widest_older
        if widest_older == 0 or counts[stamp] >= threshold:
            have = stamp
            break

    if nyse_calendar.is_session(target_date):
        cursor = target_date
        n_start = 1  # skip n=0; target already in walked
    else:
        cursor = nyse_calendar.last_session_on_or_before(target_date)
        if cursor is None:
            return [target_iso]
        n_start = 0  # cursor is one session BEFORE target, so n=0 is fair game

    walked: list[str] = [target_iso]
    n = n_start
    while len(walked) < max_sessions:
        sess = nyse_calendar.session_n_back(cursor, n)
        if sess is None:
            break
        sess_iso = sess.isoformat()
        if have is not None and sess_iso <= have:
            break
        walked.append(sess_iso)
        n += 1
    walked.reverse()
    return walked


def backfill_from_store(
    dates: Sequence[str],
    *,
    store=None,
    roots=None,
    dry_run: bool = False,
) -> dict:
    """Recompute each requested session from the ThetaData store into the ledger.

    Weekend dates are counted and skipped. A date the store does not cover is
    counted and skipped. Neither case is filled from a neighbouring session.
    A non-empty chain for that exact as-of calls `snapshot` with source
    thetadata (dry_run only counts). A second call reports no replacements
    and no additions. The store-unresolved warning is the one `load_chain`
    already prints; this function does not raise for that.
    """
    wanted = [str(item).strip()[:10] for item in dates]
    receipt: dict = {
        "dates_requested": len(wanted),
        "dates_weekend_skipped": 0,
        "dates_not_in_store": 0,
        "dates_backfilled": 0,
        "rows_replaced": 0,
        "rows_added": 0,
        "rows_unchanged": 0,
        "per_date": [],
    }
    for requested in wanted:
        if _is_weekend_iso(requested):
            receipt["dates_weekend_skipped"] += 1
            receipt["per_date"].append({"date": requested, "status": "weekend_skipped"})
            continue
        chain, state = load_chain(asof=requested, store=store, roots=roots)
        if state == "thetadata_store_unresolved":
            receipt["per_date"].append({
                "date": requested,
                "status": "thetadata_store_unresolved",
                "state": state,
            })
            continue
        asofs = _chain_asof_dates(chain)
        uncovered = chain is None or getattr(chain, "empty", True) or (
            bool(asofs) and asofs != {requested}
        )
        if uncovered:
            receipt["dates_not_in_store"] += 1
            receipt["per_date"].append({
                "date": requested,
                "status": "not_in_store",
                "state": state if not asofs or asofs == {requested} else "asof_not_requested_date",
            })
            continue
        counts = _backfill_row_counts(chain, requested)
        if not dry_run:
            snapshot(
                today=date.fromisoformat(requested),
                chain=chain,
                source=_SOURCE_THETA,
            )
        receipt["dates_backfilled"] += 1
        for key in ("rows_replaced", "rows_added", "rows_unchanged"):
            receipt[key] += counts[key]
        receipt["per_date"].append({
            "date": requested,
            "status": "backfilled",
            "state": state,
            **counts,
        })
    return receipt


def emit_from_ledger(today: date | None = None, accrual_state: str = "ledger_only") -> dict:
    """Display payload read from the committed ledger. Never opens a chain store.

    `accrual_state` is `accrued_today` when this process just wrote the ledger,
    otherwise `ledger_only`. Names are the rows on the ledger's newest COMPLETE
    session: weekend-dated rows are dropped first, then the thin-session
    guard skips any newer date whose row count is below
    `_THIN_SESSION_MIN_FRACTION × widest(count of the up-to-10 dates
    immediately older than it)` so the live surface does not collapse from
    372 → 12 on a partial newest session. Skipped dates are reported in
    `source_detail["partial_sessions_skipped"]` / `partial_rows_skipped`
    (always present, possibly empty/zero).
    """
    if accrual_state not in ("accrued_today", "ledger_only"):
        raise ValueError(f"accrual_state must be accrued_today or ledger_only, got {accrual_state!r}")
    today = today or date.today()
    hist = load_history()
    names: dict[str, dict] = {}
    ledger_asof = None
    source = None
    stale_days = None
    n_weekend_rows_excluded = 0
    history_sources: list[str] = []
    # A-F03-W2-4c defaults — overwritten below when the ledger has any session rows.
    windows: list[dict] = []
    history_dates = 0
    source_break = False
    break_date: str | None = None
    partial_sessions_skipped: list[str] = []
    partial_rows_skipped = 0
    if hist is not None and not getattr(hist, "empty", True) and "underlying" in hist.columns:
        norm = _normalize_ledger(hist)
        history_sources = sorted({
            str(item) for item in norm["source"].tolist() if str(item)
        })
        weekend = norm["date"].map(_is_weekend_iso)
        # A weekday row means weekend as-of rows are not a session. A ledger
        # with only weekend dates keeps those rows, so the count stays zero.
        if bool((~weekend).any()):
            n_weekend_rows_excluded = int(weekend.sum())
            norm = norm.loc[~weekend]
        dates = [d for d in norm["date"].tolist() if d]
        if dates:
            sorted_dates = sorted(set(dates))
            per_date_counts: dict[str, int] = {}
            for stamp in sorted_dates:
                per_date_counts[stamp] = int((norm["date"] == stamp).sum())

            # Newest date whose count meets the thin-session guard.
            chosen: str | None = None
            for index in range(len(sorted_dates) - 1, -1, -1):
                stamp = sorted_dates[index]
                older_window = sorted_dates[:index][-10:]
                widest_older = max(
                    (per_date_counts[w] for w in older_window), default=0
                )
                threshold = _THIN_SESSION_MIN_FRACTION * widest_older
                if widest_older == 0 or per_date_counts[stamp] >= threshold:
                    chosen = stamp
                    break
            # Cannot happen by construction (the oldest date is always
            # complete when there is at least one row on it), but defend
            # against an empty `norm` masking the loop's exit.
            if chosen is None:
                chosen = sorted_dates[-1]

            partial_dates = [s for s in sorted_dates if s > chosen]
            partial_sessions_skipped = partial_dates
            partial_rows_skipped = int(sum(per_date_counts[s] for s in partial_dates))
            ledger_asof = chosen
            latest = norm[norm["date"] == ledger_asof].sort_values("underlying")
            sources = []
            for rec in latest.to_dict(orient="records"):
                metric = {
                    "underlying": rec["underlying"],
                    "asof": rec["asof"] or ledger_asof,
                    "spot": float(rec["spot"]),
                    "tenor_days": float(rec["tenor_days"]),
                    "otm_put_iv": float(rec["otm_put_iv"]),
                    "atm_call_iv": float(rec["atm_call_iv"]),
                    "skew": float(rec["skew"]),
                    "n_strikes": int(rec["n_strikes"]),
                }
                names[metric["underlying"]] = metric
                sources.append(rec["source"])
            uniq = set(sources)
            source = sources[0] if len(uniq) == 1 else None
            try:
                stale_days = (today - date.fromisoformat(ledger_asof)).days
            except ValueError:
                stale_days = None
        # A-F03-W2-4c: report which source each session came from and whether the
        # history crosses a source boundary — the consumer renders this verbatim on
        # options.html as a one-sentence footnote.  Reuses the session-only `norm`
        # frame above (weekends already excluded) so the windows match the names
        # the panel prints.  `history_dates` is the count of DISTINCT session
        # dates across the normalised ledger frame (the union of dates any source
        # has rows on), so a mixed-source ledger where polygon's dates are a
        # subset of thetadata's dates reports the longer span's count, not the
        # overlap-aware sum.  An all-weekend ledger has zero of both
        # (windows == [] and history_dates == 0).  Session-only dates:
        # `history_dates` is computed against the session frame so an
        # all-weekend ledger reports 0, not 2.
        windows = source_windows(norm)
        # Seat round 6: the break date is a property of the same session frame,
        # so it is computed HERE — a ledger-less host (no snapshots.parquet, the
        # state of every sparse worktree) never binds `norm` and must emit None.
        break_date = source_break_date(norm)
        # Session-only dates: history_dates counts weekday dates so it
        # agrees with windows (an all-weekend ledger has zero of both,
        # not two of the first).  The names pick above keeps weekend rows
        # when there is no weekday row, but the additive source-break
        # keys must report 0 — not the all-weekend row count — when the
        # ledger has no session to count.
        history_dates = 0
        if "date" in norm.columns:
            weekend_mask = norm["date"].map(_is_weekend_iso)
            if bool((~weekend_mask).any()):
                history_dates = int(len({str(d) for d in norm.loc[~weekend_mask, "date"].tolist()}))
        source_break = bool(len(windows) > 1)
    if not names:
        source_state = "empty_ledger"
    elif stale_days is not None and stale_days > _STALE_DAYS:
        source_state = "stale_chain"
    elif source == _SOURCE_POLYGON:
        source_state = "legacy_polygon"
    else:
        source_state = "ok"
    gate = load_gate() or {}
    ranked = sorted(names.values(), key=lambda m: m["skew"], reverse=True)
    return {
        "schema": SCHEMA, "is_context_only": True,
        "scored": bool(gate.get("scored")),
        "as_of": today.isoformat(),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "names": names, "ranked": ranked, "n": len(names),
        "gate_status": gate.get("status", "measuring"),
        "disclaimer": _DISCLAIMER,
        "source": source,
        "source_state": source_state,
        "source_detail": {
            "asof": ledger_asof,
            "roots_seen": len(names),
            "roots_with_iv": len(names),
            "names_dropped_no_25d_put": [],
            "names_dropped_no_atm_call": [],
            "stale_days": stale_days,
            "partial_sessions_skipped": partial_sessions_skipped,
            "partial_rows_skipped": partial_rows_skipped,
        },
        "ledger_asof": ledger_asof,
        "accrual_state": accrual_state,
        "n_weekend_rows_excluded": n_weekend_rows_excluded,
        "history_sources": history_sources,
        # A-F03-W2-4c — additive keys the consumer reads to render one sentence
        # about the source break on the Directional read panel.  Schema string
        # unchanged; downstream consumers that pre-date the packet see None for
        # source_break (None is not the truthy check) and stay silent.
        "source_windows": windows,
        "source_break": source_break,
        "source_break_date": break_date,
        "history_dates": history_dates,
    }


def load_gate() -> dict | None:
    """The validation verdict (scripts/validate_options_skew.py). None → 'measuring'."""
    try:
        import json
        p = config.data_dir() / "options_skew" / "validation_gate.json"
        return json.loads(p.read_text()) if p.exists() else None
    except Exception:  # noqa: BLE001
        return None


def build_snapshot(today: date | None = None) -> dict:
    """Display payload: latest skew per name + the (likely-dormant) gate. CONTEXT-ONLY."""
    today = today or date.today()
    if _legacy_enabled():
        chain, state = _legacy_chain(), "legacy_polygon"
    else:
        chain, state = load_chain()

    drops: dict[str, list] = {}
    names = skew_map(chain, drops=drops) if chain is not None else {}
    source = None if chain is None else ("legacy_polygon" if _legacy_enabled() else "thetadata")

    stale_days = None
    if state == "ok" and names:
        try:
            newest = max(m["asof"] for m in names.values())
            stale_days = (today - date.fromisoformat(newest)).days
            if stale_days > _STALE_DAYS:
                state = "stale_chain"
                print(f"::warning title=options-skew-stale::skew chain is {stale_days}d "
                      "old — publishing stale values", flush=True)
        except Exception as e:  # noqa: BLE001
            log.debug("staleness check failed (%s)", e)

    gate = load_gate() or {}
    ranked = sorted(names.values(), key=lambda m: m["skew"], reverse=True)

    disclaimer = _DISCLAIMER
    if state != "ok":
        disclaimer += " Source unavailable — no skew reading published for this date."

    return {
        "schema": SCHEMA, "is_context_only": True,
        "scored": bool(gate.get("scored")),
        "as_of": today.isoformat(),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "names": names, "ranked": ranked, "n": len(names),
        "gate_status": gate.get("status", "measuring"),
        "source": source,
        "source_state": state,
        "source_detail": {
            "asof": (max(m["asof"] for m in names.values()) if names else None),
            "roots_seen": len(names) + sum(len(v) for v in drops.values()),
            "roots_with_iv": len(names),
            "names_dropped_no_25d_put": drops.get("no_25d_put", []),
            "names_dropped_no_atm_call": drops.get("no_atm_call", []),
            "stale_days": stale_days,
        },
        "disclaimer": disclaimer,
    }
