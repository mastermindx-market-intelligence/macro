"""Source-bound, delayed EOD evidence for the existing International workspace.

Not a market-data permission or calendar authority: the Chairman's specific
user-facing redistribution decision is supplied through the existing intl config;
the collector's persisted status and per-series parquet bytes establish that
the ordinary owner has actually written the observations. We delay every
published endpoint by at least two *calendar* days to exclude developing
bars where a full foreign-market close calendar has not been admitted.

A collector run may additionally carry an optional, narrowly scoped component
receipt inside the ``intl_prices`` status block: ``collection_scope`` names the
markets one component run covered, and ``collection_components`` binds each of
those markets to its own collection clock, its own retained per-country result
receipt and its own stored-file digests. When either key is present the
aggregate ``checked_at`` never lends its freshness to any market: a scoped
series is published only on its own component clock, and an unscoped stored
market is never published even when its bars are current and match. The
aggregate batch clock remains required, but it is a batch end, not a source
observation, and it cannot freshen an expired component.

Qualify only through engine.intl_inputs.qualify_return_records. Never substitute
the old global performance/rotation displays for this gate.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, time, timedelta, timezone
from io import BytesIO
from pathlib import Path

import pandas as pd

from engine import intl_inputs
from engine.intl_performance_records import build_return_records
from lib.intl_macro_publication import _read_stable_once

_POLICY = "intl-observed-endpoints-completed-session-v1"
_BASIS = "yfinance:auto_adjust=true:observed-close"
_MAX_COLLECT_AGE = timedelta(hours=48)
_MIN_OBSERVATION_AGE = timedelta(hours=48)
_MAX_TIP_AGE = timedelta(days=6)
_LEGS = ("local", "usd", "fx_contribution")
# One retained per-country result receipt is bounded: the component receipt is
# a small provenance record, never a bulk data carrier.
_MAX_RECEIPT_BYTES = 1024 * 1024
_COMPONENT_KEYS = ("market", "result", "result_sha256", "checked_at", "store")
_STORE_KEYS = ("sha256", "rows", "last")
_HEX = "0123456789abcdef"


def _when(value: str) -> datetime:
    if type(value) is not str or not value.strip():
        raise ValueError("timestamp must be nonempty text")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("evaluation time needs a UTC offset")
    return result.astimezone(timezone.utc)



def _weekday_elapsed(start: datetime, end: datetime) -> timedelta:
    """Elapsed UTC time on weekdays only; never infer foreign holiday opens.

    A verified Friday collector remains eligible through the closed weekend,
    but an old receipt still expires after 48 actual weekday hours. Both
    timestamps have already been normalized to UTC by the source gate.
    """
    if end < start:
        raise ValueError("collector clock is later than evaluation")
    elapsed = timedelta()
    midnight = datetime.combine(start.date(), time.min, tzinfo=timezone.utc)
    while midnight < end:
        tomorrow = midnight + timedelta(days=1)
        if midnight.weekday() < 5:
            lo = max(midnight, start)
            hi = min(tomorrow, end)
            if lo < hi:
                elapsed += hi - lo
        midnight = tomorrow
    return elapsed

def _source_ids() -> list[str]:
    unique = []
    for market in intl_inputs.countries().values():
        for series_id in (market["index"], market["fx"]):
            if series_id not in unique:
                unique.append(series_id)
    return unique


def _path(root: Path, series_id: str) -> Path:
    # The existing store._path normalization, scoped ONLY to configured IDs.
    safe = (series_id.replace("^", "_").replace("=", "_")
            .replace("/", "_").replace(" ", "_"))
    return root / "intl" / (safe + ".parquet")


def _is_text(value) -> bool:
    return type(value) is str and bool(value.strip())


def _is_sha256(value) -> bool:
    """A lower-case 64 hex digest; upper case is a different byte string."""
    return (type(value) is str and len(value) == 64
            and all(character in _HEX for character in value))


def _no_duplicate_keys(pairs):
    """JSON object hook that refuses a repeated key instead of overwriting it."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _cutoff(snapshot_clock: datetime) -> pd.Timestamp:
    """The conservative expected snapshot day for one bound collection clock."""
    cutoff = pd.Timestamp((snapshot_clock - _MIN_OBSERVATION_AGE).date())
    while cutoff.weekday() >= 5:
        cutoff -= pd.Timedelta(days=1)
    return cutoff


def _receipt_path(root: Path, relative: str) -> Path | None:
    """Resolve one data-relative receipt path without escaping the data root."""
    if not _is_text(relative):
        return None
    candidate = Path(relative)
    if candidate.is_absolute() or candidate.drive or candidate.root:
        return None
    if any(part == ".." for part in candidate.parts):
        return None
    try:
        base = root.resolve()
        current = base
        for part in candidate.parts:
            current = current / part
            if current.is_symlink():
                return None
        resolved = current.resolve()
    except (OSError, RuntimeError, ValueError):
        return None
    if resolved != base and base not in resolved.parents:
        return None
    return current


def _valid_store_entry(entry) -> bool:
    """One stored-file descriptor: digest, positive row count and last date."""
    if type(entry) is not dict or set(entry) != set(_STORE_KEYS):
        return False
    if not _is_sha256(entry["sha256"]):
        return False
    rows = entry["rows"]
    if type(rows) is not int or rows <= 0:
        return False
    return _is_text(entry["last"])


def _load_component(root: Path, component, market_row: dict) -> dict | None:
    """Bind one market's configured primary index and FX to its own receipt.

    None means the receipt contradicts itself, the run, or its stored bytes.
    That is an integrity failure of the scoped collection, not a stale series,
    so the caller fails the whole gate closed instead of publishing part of an
    unproven component run.
    """
    if type(component) is not dict or set(component) != set(_COMPONENT_KEYS):
        return None
    if not _is_text(component["market"]):
        return None
    store = component["store"]
    if type(store) is not dict:
        return None
    series_ids = (market_row["index"], market_row["fx"])
    if set(store) != set(series_ids):
        return None
    for entry in store.values():
        if not _valid_store_entry(entry):
            return None
    if not _is_sha256(component["result_sha256"]):
        return None
    try:
        clock = _when(component["checked_at"])
    except (TypeError, ValueError, OverflowError):
        return None
    path = _receipt_path(root, component["result"])
    if path is None:
        return None
    try:
        if path.is_symlink() or not path.is_file():
            return None
        payload = _read_stable_once(path, _MAX_RECEIPT_BYTES)
    except (OSError, ValueError):
        return None
    if hashlib.sha256(payload).hexdigest() != component["result_sha256"]:
        return None
    try:
        result = json.loads(payload.decode("utf-8"), object_pairs_hook=_no_duplicate_keys,
                            parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite receipt")))
    except (UnicodeDecodeError, ValueError):
        return None
    if type(result) is not dict:
        return None
    if any(key not in result for key in ("fetch_result", "checked_at", "post_store")):
        return None
    # The component clock IS the receipt clock. A component may not claim a
    # collection time its own retained receipt does not carry.
    if result["checked_at"] != component["checked_at"]:
        return None
    fetch = result["fetch_result"]
    if type(fetch) is not dict:
        return None
    if fetch.get("source") != "intl_prices" or fetch.get("status") != "ok":
        return None
    if not _is_text(fetch.get("last_date")):
        return None
    try:
        last_date = datetime.fromisoformat(fetch["last_date"]).date()
    except (TypeError, ValueError, OverflowError):
        return None
    post_store = result["post_store"]
    if type(post_store) is not dict:
        return None
    filenames = {_path(root, series_id).name: series_id for series_id in series_ids}
    if set(post_store) != set(filenames):
        return None
    for filename, series_id in filenames.items():
        entry = post_store[filename]
        if not _valid_store_entry(entry) or entry != store[series_id]:
            return None
    return {
        "market": component["market"],
        "clock": clock,
        "last_date": last_date,
        "receipt_sha256": component["result_sha256"],
        "store": store,
    }


def _scope_components(root: Path, source: dict, countries: dict) -> dict | None:
    """Validate the optional component scope against its own receipts."""
    scope = source.get("collection_scope")
    components = source.get("collection_components")
    if type(scope) is not list or not scope:
        return None
    if type(components) is not list:
        return None
    markets = []
    for market in scope:
        if not _is_text(market) or market not in countries:
            return None
        if market in markets:
            return None
        markets.append(market)
    bound = {}
    for component in components:
        if type(component) is not dict:
            return None
        market = component.get("market")
        if not _is_text(market) or market not in countries:
            return None
        if market in bound:
            return None
        info = _load_component(root, component, countries[market])
        if info is None:
            return None
        bound[market] = info
    if set(bound) != set(markets):
        return None
    return {market: bound[market] for market in markets}


def _component_admission(clock: datetime, last_date, collected: datetime,
                         evaluated: datetime) -> str | None:
    """Classify one component clock against the run and the evaluation clock.

    None admits the component. "stale" withholds that component's series
    only. "impossible" refuses a receipt that contradicts the run it claims
    to belong to, which fails the whole gate closed.
    """
    if clock > evaluated or clock > collected or last_date > evaluated.date():
        return "impossible"
    try:
        elapsed = _weekday_elapsed(clock, evaluated)
    except (TypeError, ValueError, OverflowError):
        return "impossible"
    if (evaluated - clock > _MAX_COLLECT_AGE + timedelta(days=2)
            or elapsed > _MAX_COLLECT_AGE
            or evaluated.date() - last_date > _MAX_TIP_AGE):
        return "stale"
    return None


def _stored_digest(root: Path, series_id: str) -> str | None:
    """The digest of the stored bytes themselves, or None when there are none."""
    path = _path(root, series_id)
    try:
        if not path.is_file() or path.is_symlink():
            return None
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except (OSError, ValueError):
        return None


def _stored_witness(root: Path, series_id: str, expected: pd.DataFrame,
                    cutoff: pd.Timestamp, collected: datetime) -> tuple[str, str] | None:
    """Re-read the stored file; prove its close series equals the selected frame.

    A directory walk, successful download, status=ok, or source timestamp alone
    is not proof that this exact saved series matches the price arithmetic.
    """
    path = _path(root, series_id)
    try:
        if not path.is_file() or path.is_symlink():
            return None
        data = path.read_bytes()
        frame = pd.read_parquet(BytesIO(data))  # Parse the exact bytes we hash.
        if "close" not in frame or not isinstance(frame.index, pd.DatetimeIndex):
            return None
        if frame.index.hasnans or frame.index.has_duplicates:
            return None
        bars = frame["close"].sort_index()
        if bars.index.tz is not None or cutoff.tz is not None:
            return None  # Normalized daily-store contract is timezone-naive.
        bars = bars.loc[bars.index <= cutoff].dropna()
        if series_id not in expected or bars.empty:
            return None
        selected = expected[series_id].dropna()
        if not bars.index.equals(selected.index) or not bars.equals(selected):
            return None
        latest = selected.index[-1]
        # A fresh run for another series cannot make this old tail current.
        # The expected snapshot date is chosen from the clock BEFORE looking
        # at this series, never by calling its last saved bar "completed".
        if latest != cutoff:
            return None
        # The collector must have finished after this observed daily bar and
        # outside a conservative two-day post-date window.
        observed = datetime.combine(latest.date(), datetime.min.time(), timezone.utc)
        if collected - observed < _MIN_OBSERVATION_AGE:
            return None
        return latest.isoformat(), hashlib.sha256(data).hexdigest()
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        return None


def build_eod_inputs(
    closes: pd.DataFrame | None, *, data_root: Path, evaluated_at: str,
    rights: dict,
) -> tuple[pd.DataFrame, dict] | None:
    """Return (closes, production_inputs) for the existing R10 projection.

    Missing/expired evidence fails closed, not to a source-free "allowed"
    qualification. Partial index/FX witnesses remain independent: an admitted
    local return may exist without an admitted USD return.

    An optional component scope replaces the aggregate receipt as the clock
    authority for the markets it names. Each scoped market then carries its
    own component clock, and an unscoped market is never published.
    """
    if (type(rights) is not dict
            or rights.get("status") != "confirmed"
            or rights.get("scope") != "intl-index-fx-eod-user-facing-v1"
            or type(rights.get("decision_ref")) is not str
            or not rights["decision_ref"].strip()):
        return None
    if closes is None or not isinstance(closes, pd.DataFrame):
        return None
    try:
        evaluated = _when(evaluated_at)
    except (TypeError, ValueError, OverflowError):
        return None
    if (not isinstance(closes.index, pd.DatetimeIndex)
            or closes.index.hasnans or closes.index.has_duplicates
            or not closes.index.is_monotonic_increasing
            or closes.index.tz is not None):
        return None
    root = Path(data_root)
    try:
        status = json.loads((root / "run_status.json").read_text(encoding="utf-8"))
        source = status["sources"]["intl_prices"]
        collected = _when(source["checked_at"])
        source_last = datetime.fromisoformat(source["last_date"]).date()
        if (source["source"] != "intl_prices" or source["status"] != "ok"
                or collected > evaluated
                or evaluated - collected > _MAX_COLLECT_AGE + timedelta(days=2)
                or _weekday_elapsed(collected, evaluated) > _MAX_COLLECT_AGE
                or source_last > evaluated.date()
                or evaluated.date() - source_last > _MAX_TIP_AGE):
            return None
    except (OSError, KeyError, TypeError, ValueError, OverflowError):
        return None
    if not isinstance(source, dict):
        return None

    countries = intl_inputs.countries()
    all_ids = _source_ids()
    scoped = "collection_scope" in source or "collection_components" in source
    clocks: dict[str, datetime] = {}
    receipts: dict[str, dict] = {}
    ids: list[str] = []
    if scoped:
        # A component scope is validated strictly and completely: an invalid
        # scope, a missing receipt or a changed receipt fails the whole gate
        # closed. There is no legacy fallback for a broken scope.
        components = _scope_components(root, source, countries)
        if components is None:
            return None
        admitted = {}
        for market, info in components.items():
            verdict = _component_admission(
                info["clock"], info["last_date"], collected, evaluated)
            if verdict == "impossible":
                return None
            if verdict == "stale":
                continue  # Withhold this component's series only.
            admitted[market] = info
        if not admitted:
            return None
        # The common cutoff is derived from the EARLIEST eligible component
        # clock, so no component can borrow the aggregate batch clock. The
        # aggregate cutoff is never earlier than that day; it is retained
        # only where every admitted component separately clears the same
        # 48-hour delay at it, which can only be that same day.
        snapshot_clock = min(evaluated, min(info["clock"] for info in admitted.values()))
        cutoff = _cutoff(snapshot_clock)
        aggregate_cutoff = _cutoff(min(evaluated, collected))
        if aggregate_cutoff > cutoff:
            midnight = datetime.combine(aggregate_cutoff.date(), time.min,
                                        tzinfo=timezone.utc)
            if all(info["clock"] - midnight >= _MIN_OBSERVATION_AGE
                   for info in admitted.values()):
                cutoff = aggregate_cutoff
        for market, info in admitted.items():
            row = countries[market]
            for series_id in (row["index"], row["fx"]):
                if series_id in clocks:
                    continue
                ids.append(series_id)
                clocks[series_id] = info["clock"]
                receipts[series_id] = info
        for series_id in ids:
            bound = receipts[series_id]["store"][series_id]["sha256"]
            stored = _stored_digest(root, series_id)
            if stored != bound:
                # The stored bytes are not the bytes this receipt bound.
                return None
    else:
        # This is an intentionally delayed source, not a live/current-session read.
        # Both clocks are independent of the stored series. A UTC midnight does
        # not advance a still-current collector receipt or certify another day.
        # Its age is bounded above; a new receipt advances the obligation.
        snapshot_clock = min(evaluated, collected)
        cutoff = _cutoff(snapshot_clock)
        ids = list(all_ids)
        for series_id in ids:
            clocks[series_id] = collected

    # This is a conservative weekday obligation, not an inferred foreign
    # holiday calendar. A missing expected day stays unavailable, even when
    # a venue may have been closed. No closure exemption is fabricated.
    selected = closes.loc[closes.index <= cutoff].copy()
    if selected.empty:
        return None

    bases = {series_id: _BASIS for series_id in all_ids}
    try:
        pending = intl_inputs.source_snapshot(
            selected, source_reference="intl-supplied-close:pending",
            adjustment_bases=bases)
        source_reference = "intl-supplied-close:sha256:" + pending["content_sha256"]
        snapshot = intl_inputs.source_snapshot(
            selected, source_reference=source_reference, adjustment_bases=bases)
        records = build_return_records(
            selected, market_ids=list(intl_inputs.countries()),
            source_reference=source_reference)
    except (ValueError, TypeError, OverflowError):
        # This publication adapter is optional; malformed source frames are
        # withheld. The strict numerical/snapshot APIs retain their errors.
        return None
    evidence = []
    observed = {}
    for series_id in ids:
        witness = _stored_witness(root, series_id, selected, cutoff, clocks[series_id])
        if witness is None:
            continue
        tip, saved_digest = witness
        tip_date = datetime.fromisoformat(tip).date()
        if evaluated.date() - tip_date > _MAX_TIP_AGE:
            continue
        receipt = receipts.get(series_id)
        if receipt is not None:
            if saved_digest != receipt["store"][series_id]["sha256"]:
                return None
            decision_ref = ("saved-parquet:sha256:" + saved_digest
                            + ";component-receipt:sha256:" + receipt["receipt_sha256"])
        else:
            decision_ref = "saved-parquet:sha256:" + saved_digest
        observed[series_id] = saved_digest
        # The exact persisted content and conservative elapsed-time contract
        # are the evidence, not a fictitious exchange holiday calendar.
        evidence.append({
            "source_reference": source_reference,
            "content_sha256": snapshot["content_sha256"],
            "series_id": series_id,
            "adjustment_basis": _BASIS,
            "basis_state": "accepted",
            "evaluated_at": evaluated.replace(tzinfo=None).isoformat(),
            "latest_completed_observation": tip,
            "calendar_ref": "intl-conservative-observed-eod-tplus2-v1",
            "owner_ref": "collectors.intl_prices:stored-close",
            "decision_ref": decision_ref,
        })
    if not evidence:
        return None

    decisions = []
    for record in records["records"]:
        for currency_basis in ("local", "usd_unhedged"):
            for leg in _LEGS:
                decisions.append({
                    "source_reference": source_reference,
                    "content_sha256": snapshot["content_sha256"],
                    "market_id": record["market_id"],
                    "index_id": record["index_id"],
                    "fx_id": record["fx_id"],
                    "horizon": record["horizon"],
                    "currency_basis": currency_basis,
                    "return_basis": record["return_basis"],
                    "leg": leg,
                    "owner_ref": "scripts.build_intl:publication",
                    "policy_ref": "intl-index-fx-eod-user-facing-v1",
                    "decision_ref": rights["decision_ref"],
                    "metadata": "allowed",
                    "value": "allowed",
                })
    return selected, {
        "adjustment_bases": bases,
        "source_evidence": evidence,
        "disclosure_decisions": decisions,
        "policy_id": _POLICY,
    }
