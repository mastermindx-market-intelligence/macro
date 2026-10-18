"""Read existing stores and publish the display-only Dark Flow projection.

No ingestion, credential access, network, risk scoring, or PSS-AF1 writes. The
existing nightly engine owns invocation after its raw-price restore. Other render
lanes consume the last publication; they do not replace it with an empty mirror.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile

import pandas as pd

from collectors.finra_short_volume import expected_available_session
from engine.darkflow_index import Policy, SCHEMA, build_index, canonical_symbol
from lib import nyse_calendar
from lib.massive_ticker import artifact_relative_path


class SourceUnavailable(RuntimeError):
    """A required source could not be read; retain the last publication unchanged."""


def _read_snapshot(path: Path, columns: list[str] | None = None) -> tuple[pd.DataFrame, str]:
    """Parse and attest the SAME immutable bytes, even if the source is replaced."""
    from io import BytesIO

    if not path.is_file():
        raise SourceUnavailable(f"missing source: {path.parent.name}/{path.name}")
    try:
        raw = path.read_bytes()
        frame = pd.read_parquet(BytesIO(raw), columns=columns)
        return frame, hashlib.sha256(raw).hexdigest()
    except Exception as exc:
        raise SourceUnavailable(f"unreadable source: {path.parent.name}/{path.name}") from exc


def load_membership(data: Path) -> tuple[pd.DataFrame, dict, dict[str, str]]:
    """Use existing historical + observed membership owners, not today's survivors.

    Historical intervals stop at the observed ledger's first date. Active ledger
    members retain their ongoing state after last_seen, with the observation date
    disclosed and a five-session freshness ceiling at publication. The known
    June/July accrual hole remains explicitly unsuitable for strategy evidence.
    """
    historic_path = data / "breadth/sp1500_pit_membership.parquet"
    ledger_path = data / "universe/membership.parquet"
    historic, historic_sha = _read_snapshot(historic_path)
    ledger, ledger_sha = _read_snapshot(ledger_path)
    if not {"ticker", "start_date", "end_date", "src"}.issubset(historic.columns):
        raise SourceUnavailable("historical membership schema mismatch")
    if not {"ticker", "group", "first_seen", "last_seen", "active", "sector"}.issubset(ledger.columns):
        raise SourceUnavailable("observed membership schema mismatch")
    ledger = ledger[ledger.group == "sp500"].copy()
    if ledger.empty:
        raise SourceUnavailable("no observed S&P 500 membership")
    for column in ["first_seen", "last_seen"]:
        ledger[column] = pd.to_datetime(ledger[column], utc=True).dt.tz_localize(None).dt.normalize()
    if ledger[["first_seen", "last_seen"]].isna().any().any():
        raise SourceUnavailable("membership dates malformed")
    cutoff = ledger.first_seen.min()
    historic = historic[historic.src == "sp500"].copy()
    historic["start_date"] = pd.to_datetime(historic.start_date)
    historic["end_date"] = pd.to_datetime(historic.end_date).fillna(cutoff - pd.Timedelta(days=1))
    historic["end_date"] = historic.end_date.clip(upper=cutoff - pd.Timedelta(days=1))
    historic = historic[historic.start_date <= historic.end_date]
    observed = ledger.rename(columns={"first_seen": "start_date", "last_seen": "end_date"})
    observed.loc[observed.active == True, "end_date"] = pd.NaT  # ongoing observed state, not a price fill
    observed["src"] = "sp500"
    columns = ["ticker", "start_date", "end_date", "src"]
    combined = pd.concat([historic[columns], observed[columns]], ignore_index=True)
    sectors = {canonical_symbol(row.ticker): str(row.sector) for row in ledger.itertuples()}
    # Fill only classifications, never membership, from the existing sector map.
    sector_path = data / "breadth/ticker_sectors.parquet"
    sector_sha = None
    if sector_path.is_file():
        extra, sector_sha = _read_snapshot(sector_path)
        if {"ticker", "sector"}.issubset(extra.columns):
            for row in extra.itertuples():
                sectors.setdefault(canonical_symbol(row.ticker), str(row.sector))
    receipt = {
        "historic_sha256": historic_sha, "ledger_sha256": ledger_sha, "sectors_sha256": sector_sha,
        "observed_from": str(cutoff.date()), "observed_through": str(ledger.last_seen.max().date()),
        "active_members": int((ledger.active == True).sum()),
        "known_history_gap": ["2026-06-14", "2026-07-10"],
        "basis": "historical intervals, then observed ledger; active state carried from observed_through",
        "sector_basis": "latest observed classification, not historical sector membership",
    }
    return combined, receipt, sectors


def load_panel(data: Path) -> tuple[pd.DataFrame, list[dict]]:
    frames, receipts = [], []
    # Identical precedence to the existing Dark Pool Desk. Neither store is written.
    for name in ["panel_deep.parquet", "panel.parquet"]:
        path = data / "finra_short_volume" / name
        if name == "panel_deep.parquet" and not path.is_file():
            continue
        frame, source_sha = _read_snapshot(path)
        if not {"date", "ticker"}.issubset(frame.columns):
            raise SourceUnavailable("FINRA panel schema mismatch")
        frames.append(frame)
        receipts.append({"path": f"finra_short_volume/{name}", "sha256": source_sha})
    if not frames:
        raise SourceUnavailable("FINRA panel unavailable")
    frame = pd.concat(frames, ignore_index=True)
    frame["date"] = pd.to_datetime(frame.date)
    return frame.drop_duplicates(["date", "ticker"], keep="last"), receipts


def load_raw_prices(data: Path, names: set[str], start: pd.Timestamp) -> tuple[pd.DataFrame, dict]:
    frames, missing, invalid, digest = [], [], [], hashlib.sha256()
    for name in sorted(names):
        vendor = {"BRK-B": "BRK.B", "BF-B": "BF.B"}.get(name, name)
        path = data / "massive_stock_day" / artifact_relative_path(vendor)
        if not path.is_file():
            missing.append(name)
            continue
        try:
            frame, source_sha = _read_snapshot(path, columns=["close"])
            if not isinstance(frame.index, pd.DatetimeIndex):
                raise ValueError("raw store must have a date index")
            frame = frame.copy()
            frame.index = pd.to_datetime(frame.index, utc=True).tz_localize(None).normalize()
            frame = frame[frame.index >= start]
            frame["date"] = frame.index
            frame["ticker"] = name
            frames.append(frame.reset_index(drop=True))
            digest.update(name.encode() + b"\0" + bytes.fromhex(source_sha))
        except Exception:
            invalid.append(name)
    if not frames:
        raise SourceUnavailable("raw-price mirror absent or unreadable; adjusted-price fallback prohibited")
    prices = pd.concat(frames, ignore_index=True)
    receipt = {
        "source": "massive_stock_day", "basis": "unadjusted", "inputs_sha256": digest.hexdigest(),
        "files_read": len(frames), "missing_files": len(missing), "unreadable_files": len(invalid),
        "latest_available": str(prices.date.max().date()) if not prices.empty else None,
    }
    return prices, receipt


def _price_context(prices: pd.DataFrame, sessions: list, asof: str) -> dict:
    """SPY comparison is a separately dated observation, never a combined score."""
    spy = prices[prices.ticker == "SPY"].set_index("date").close
    if spy.index.duplicated().any() or len(sessions) < 6:
        return {"asof": asof, "spy_change_5d_pct": None}
    a, b = pd.Timestamp(asof), pd.Timestamp(sessions[-6])
    if a not in spy.index or b not in spy.index or spy.loc[b] <= 0:
        return {"asof": asof, "spy_change_5d_pct": None}
    return {"asof": asof, "spy_change_5d_pct": round(100 * (float(spy.loc[a]) / float(spy.loc[b]) - 1), 3),
            "basis": "unadjusted SPY close; price return, not total return"}


def build_from_store(data: Path, *, now: datetime | None = None, policy: Policy = Policy()) -> dict:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must carry an explicit timezone")
    asof = expected_available_session(now)
    membership, membership_receipt, sectors = load_membership(data)
    member_date = pd.Timestamp(membership_receipt["observed_through"]).date()
    age = len(nyse_calendar.sessions_strictly_between(member_date, asof)) + (int(asof > member_date))
    if age > 5:
        raise SourceUnavailable("observed membership is more than five market sessions old")
    panel, finra_receipts = load_panel(data)
    start = asof - timedelta(days=policy.history_sessions * 2)
    sessions = nyse_calendar.sessions_between(start, asof)[-policy.history_sessions:]
    names = set(membership.loc[membership.end_date.isna() | (membership.end_date >= pd.Timestamp(sessions[0])), "ticker"])
    if len(names) > 1000:
        raise SourceUnavailable("unexpected index membership expansion")
    prices, price_receipt = load_raw_prices(data, names | {"SPY"}, pd.Timestamp(sessions[0]))
    result = build_index(panel, prices, membership, sectors, sessions, asof=str(asof),
                         known_at=now.astimezone(timezone.utc).isoformat(), price_basis="unadjusted", policy=policy)
    result["sources"] = {"finra": finra_receipts, "prices": price_receipt, "membership": membership_receipt}
    result["sources"]["finra_latest"] = str(pd.to_datetime(panel.date).max().date())
    result["sources"]["membership"]["age_sessions"] = age
    result["context"] = _price_context(prices, sessions, str(asof))
    if result["last_complete"] is not None:
        last_date = result["last_complete"]["date"]
        prior_sessions = [s for s in sessions if str(s) <= last_date]
        result["last_complete_context"] = _price_context(prices, prior_sessions, last_date)
    # Every visible number shares one observation date. A partial new session
    # never borrows yesterday's reading while displaying today's empty sectors.
    shown = result
    mode = "current" if result["current"]["value"] is not None else "unavailable"
    if mode == "unavailable" and result["last_complete"] is not None:
        last_date = result["last_complete"]["date"]
        prior_sessions = [s for s in sessions if str(s) <= last_date]
        shown = build_index(panel, prices, membership, sectors, prior_sessions,
                            asof=last_date, known_at=result["known_at"],
                            price_basis="unadjusted", policy=policy)
        mode = "last_complete"
    result["display"] = {
        "mode": mode, "asof": shown["asof"], "reading": shown["current"],
        "sectors": shown["sectors"], "attribution_5d": shown["attribution_5d"],
        "context": _price_context(prices, [s for s in sessions if str(s) <= shown["asof"]], shown["asof"]),
        "sparkline": [{"date": row["date"], "value": row["value"]} for row in shown["history"][-20:]],
    }
    result["names"] = shown["names"]
    result["names_asof"] = shown["asof"]
    # Freshness monitors must measure the last covered OBSERVATION, not the
    # expected session stamped on a newly built but incomplete publication.
    result["observed_asof"] = shown["asof"] if mode != "unavailable" else None
    next_session = nyse_calendar.session_n_forward(asof, 1)
    if next_session is None:
        raise SourceUnavailable("next exchange session unavailable")
    due = datetime.combine(next_session, time(18, 30), tzinfo=nyse_calendar.ET)
    result["next_due_at"] = due.astimezone(timezone.utc).isoformat()
    result["publication_owner"] = "daily-engine / scripts.build_darkflow_index"
    result.pop("generation", None)
    result["generation"] = hashlib.sha256(json.dumps(result, sort_keys=True, allow_nan=False).encode()).hexdigest()
    return result


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(payload)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def publish(result: dict, site: Path) -> dict:
    """Two atomic files, one content generation; consumer rejects mixed generations."""
    deferred = {"history", "sector_history", "names"}
    latest = {k: v for k, v in result.items() if k not in deferred}
    latest["history_url"] = "darkflow_history.json"
    history = {"schema": SCHEMA, "generation": result["generation"], "asof": result["asof"],
               "observed_asof": result["observed_asof"],
               "history_basis": result["history_basis"], "sector_basis": result["sector_basis"],
               "history": result["history"][-252:],
               "sector_history": {k: v[-252:] for k, v in result["sector_history"].items()},
               "names": result["names"], "names_asof": result["names_asof"]}
    _atomic_json(site / "darkflow_history.json", history)
    _atomic_json(site / "darkflow_latest.json", latest)
    return latest
