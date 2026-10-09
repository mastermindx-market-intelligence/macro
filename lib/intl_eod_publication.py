"""Source-bound, delayed EOD evidence for the existing International workspace.

Not a market-data permission or calendar authority: the Chairman's specific
user-facing redistribution decision is supplied through the existing intl config;
the collector's persisted status and per-series parquet bytes establish that
the ordinary owner has actually written the observations. We delay every
published endpoint by at least two *calendar* days to exclude developing
bars where a full foreign-market close calendar has not been admitted.

Qualify only through engine.intl_inputs.qualify_return_records. Never substitute
the old global performance/rotation displays for this gate.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

import pandas as pd

from engine import intl_inputs
from engine.intl_performance_records import build_return_records

_POLICY = "intl-observed-endpoints-completed-session-v1"
_BASIS = "yfinance:auto_adjust=true:observed-close"
_MAX_COLLECT_AGE = timedelta(hours=48)
_MIN_OBSERVATION_AGE = timedelta(hours=48)
_MAX_TIP_AGE = timedelta(days=6)
_LEGS = ("local", "usd", "fx_contribution")


def _when(value: str) -> datetime:
    if type(value) is not str or not value.strip():
        raise ValueError("timestamp must be nonempty text")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("evaluation time needs a UTC offset")
    return result.astimezone(timezone.utc)


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
                or collected > evaluated or evaluated - collected > _MAX_COLLECT_AGE
                or source_last > evaluated.date()
                or evaluated.date() - source_last > _MAX_TIP_AGE):
            return None
    except (OSError, KeyError, TypeError, ValueError, OverflowError):
        return None

    # This is an intentionally delayed source, not a live/current-session read.
    cutoff = pd.Timestamp((evaluated - _MIN_OBSERVATION_AGE).date())
    while cutoff.weekday() >= 5:
        cutoff -= pd.Timedelta(days=1)
    # This is a conservative weekday obligation, not an inferred foreign
    # holiday calendar. A missing expected day stays unavailable, even when
    # a venue may have been closed. No closure exemption is fabricated.
    selected = closes.loc[closes.index <= cutoff].copy()
    if selected.empty:
        return None

    ids = _source_ids()
    bases = {series_id: _BASIS for series_id in ids}
    pending = intl_inputs.source_snapshot(
        selected, source_reference="intl-supplied-close:pending",
        adjustment_bases=bases)
    source_reference = "intl-supplied-close:sha256:" + pending["content_sha256"]
    snapshot = intl_inputs.source_snapshot(
        selected, source_reference=source_reference, adjustment_bases=bases)
    records = build_return_records(
        selected, market_ids=list(intl_inputs.countries()),
        source_reference=source_reference)
    evidence = []
    observed = {}
    for series_id in ids:
        witness = _stored_witness(root, series_id, selected, cutoff, collected)
        if witness is None:
            continue
        tip, saved_digest = witness
        tip_date = datetime.fromisoformat(tip).date()
        if evaluated.date() - tip_date > _MAX_TIP_AGE:
            continue
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
            "decision_ref": "saved-parquet:sha256:" + saved_digest,
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
