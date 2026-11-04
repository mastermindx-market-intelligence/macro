"""Post-store evidence for the existing Japan monthly ten-year yield producer.

The reader proves response/cache agreement, not provider publication time or
permission. Only the normal publisher's separate byte-bound decision may expose
a value. No network or acquisition retry lives in this module.
"""
from __future__ import annotations

import calendar
import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import pandas as pd

from lib.intl_macro_publication import _read_stable_once, _reject_duplicate_keys

COLUMN = "JP_yield_10y"
SOURCE_ID = "IRLTLT01JPM156N"
DIRECTORY = Path("intl_macro") / "publication" / COLUMN
SCHEMA = "intl.jp_yield_materialization.v1"
LIMIT = 8 * 1024 * 1024
SOURCE_CONTRACT = {"provider": "fred_fallback", "source_id": SOURCE_ID,
                   "source_url": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + SOURCE_ID,
                   "unit": "percent", "frequency": "monthly", "adjustment": "NSA",
                   "instrument_id": SOURCE_ID, "instrument_kind": "sovereign_10y"}


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _utc(value):
    if type(value) is not str:
        raise ValueError("UTC instant required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("UTC instant required")
    return parsed


def _series(frame):
    if type(frame) is not pd.DataFrame or frame.columns.tolist() != [COLUMN]:
        raise ValueError("invalid yield columns")
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is not None:
        raise ValueError("invalid monthly index")
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("ambiguous monthly index")
    series = frame[COLUMN].dropna()
    if series.empty or not all(math.isfinite(float(v)) for v in series):
        raise ValueError("no finite monthly observations")
    if any(d.day != 1 or d != d.normalize() for d in series.index):
        raise ValueError("monthly source labels must be original month starts")
    return series


def _put(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if _read_stable_once(path, LIMIT) != raw:
            raise ValueError("immutable source identity collision")
        return
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def capture_jp_yield_commit(*, data_root, returned, response_bytes, source,
                            received_at, committed_at):
    """Called once after normal store.upsert succeeds; never before the write.

    A failure may leave immutable source objects. It does not undo the canonical
    write and must not cause an acquisition retry. The last receipt is accepted
    only while it still hashes to the actual current canonical artifact.
    """
    if source != SOURCE_CONTRACT or type(response_bytes) is not bytes or not response_bytes or len(response_bytes) > LIMIT:
        raise ValueError("unrecognized original source contract")
    if _utc(committed_at) < _utc(received_at):
        raise ValueError("store precedes response")
    supplied = _series(returned)
    # Independently parse the original response, preserving dates and raw values.
    wire = pd.read_csv(BytesIO(response_bytes))
    if wire.columns.tolist() not in [["DATE", SOURCE_ID], ["observation_date", SOURCE_ID]]:
        raise ValueError("response source identity mismatch")
    wire[SOURCE_ID] = pd.to_numeric(wire[SOURCE_ID], errors="coerce")
    original = wire.set_index(pd.to_datetime(wire.iloc[:, 0]))[[SOURCE_ID]].rename(columns={SOURCE_ID: COLUMN})
    original = _series(original.sort_index())
    if not original.equals(supplied):
        # pandas dtypes may differ after canonical validation; values may not.
        if original.index.tolist() != supplied.index.tolist() or list(map(float, original)) != list(map(float, supplied)):
            raise ValueError("response and returned coverage differ")
    root = Path(data_root)
    artifact = _read_stable_once(root / "intl_macro" / (COLUMN + ".parquet"), LIMIT)
    stored = _series(pd.read_parquet(BytesIO(artifact)))
    # Old-only cache dates cannot become the current response's endpoint.
    if stored.index[-1] != supplied.index[-1]:
        raise ValueError("latest stored date not covered by response")
    if any(date not in stored or float(stored.loc[date]) != float(value) for date, value in supplied.items()):
        raise ValueError("committed response coverage mismatch")
    source_hash = _sha(response_bytes)
    receipt = {"schema": SCHEMA, "column": COLUMN, "source": source,
               "source_sha256": source_hash, "artifact_sha256": _sha(artifact),
               "received_at": received_at, "committed_at": committed_at,
               "provider_published_at": None, "revision_vintage": None,
               "observation_label": supplied.index[-1].date().isoformat(),
               "value": float(supplied.iloc[-1]), "response_rows": len(supplied)}
    directory = root / DIRECTORY
    _put(directory / (source_hash + ".csv"), response_bytes)
    raw = _json(receipt)
    _put(directory / (_sha(raw) + ".json"), raw)
    fd, temporary = tempfile.mkstemp(prefix=".current-", dir=directory)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, directory / "current.json")
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return receipt


def read_jp_yield_materialization(*, data_root):
    root = Path(data_root)
    pointer = root / DIRECTORY / "current.json"
    verified_receipt_sha = None
    try:
        pointer.lstat()
    except FileNotFoundError:
        return {"status": "missing"}
    except Exception:
        return {"status": "failed"}
    try:
        raw = _read_stable_once(pointer, LIMIT)
        # The mutable selector must retain the original capture's exact bytes.
        # This is integrity within the incumbent store trust, not authentication
        # of arbitrary filesystem writers.
        if _read_stable_once(root / DIRECTORY / (_sha(raw) + ".json"), LIMIT) != raw:
            raise ValueError("capture receipt identity changed")
        receipt = json.loads(raw, object_pairs_hook=_reject_duplicate_keys,
                             parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
        expected_keys = {"schema", "column", "source", "source_sha256", "artifact_sha256", "received_at",
                         "committed_at", "provider_published_at", "revision_vintage", "observation_label", "value", "response_rows"}
        if type(receipt) is not dict or set(receipt) != expected_keys or receipt["schema"] != SCHEMA or receipt["column"] != COLUMN:
            raise ValueError("invalid receipt")
        if (receipt["source"] != SOURCE_CONTRACT or receipt["provider_published_at"] is not None
                or receipt["revision_vintage"] is not None or type(receipt["response_rows"]) is not int):
            raise ValueError("invalid source semantics")
        verified_receipt_sha = _sha(raw)
        for key in ("source_sha256", "artifact_sha256"):
            if type(receipt[key]) is not str or len(receipt[key]) != 64 or any(c not in "0123456789abcdef" for c in receipt[key]):
                raise ValueError("invalid digest")
        source_raw = _read_stable_once(root / DIRECTORY / (receipt["source_sha256"] + ".csv"), LIMIT)
        artifact = _read_stable_once(root / "intl_macro" / (COLUMN + ".parquet"), LIMIT)
        if _sha(source_raw) != receipt["source_sha256"] or _sha(artifact) != receipt["artifact_sha256"]:
            raise ValueError("materialization identity changed")
        # Validate the actual response, committed bytes and original endpoint
        # independently; the receipt is not an input-data permission grant.
        stored = _series(pd.read_parquet(BytesIO(artifact)))
        wire = pd.read_csv(BytesIO(source_raw))
        if wire.columns.tolist() not in [["DATE", SOURCE_ID], ["observation_date", SOURCE_ID]]:
            raise ValueError("wrong source series")
        wire[SOURCE_ID] = pd.to_numeric(wire[SOURCE_ID], errors="coerce")
        original = _series(wire.set_index(pd.to_datetime(wire.iloc[:, 0]))[[SOURCE_ID]].rename(columns={SOURCE_ID: COLUMN}).sort_index())
        if (original.index[-1] != stored.index[-1] or len(original) != receipt["response_rows"]
                or original.index[-1].date().isoformat() != receipt["observation_label"]
                or any(d not in stored or float(stored.loc[d]) != float(v) for d, v in original.items())
                or type(receipt["value"]) not in {int, float} or float(original.iloc[-1]) != receipt["value"]
                or _utc(receipt["committed_at"]) < _utc(receipt["received_at"])):
            raise ValueError("invalid committed coverage")
        return {"status": "ready", "receipt": receipt, "receipt_sha256": _sha(raw)}
    except Exception:
        return ({"status": "failed", "receipt_sha256": verified_receipt_sha}
                if verified_receipt_sha is not None else {"status": "failed"})


def admit_jp_yield_field(materialized, *, evaluated_at, publication_decision):
    """A pure field projection under an independently supplied publisher decision."""
    blank = {"quality": "unknown", "reason": "disclosure_unknown", "metadata": "unknown",
             "value_permission": "unknown", "value": None, "unit": None, "instrument": None,
             "period": None, "observation_at": None, "calculation_at": None,
             "source_reference": None, "evidence_key": None}
    if materialized.get("status") != "ready" and not materialized.get("receipt_sha256"):
        return {**blank, "quality": materialized.get("status", "failed"),
                "reason": "not_supplied" if materialized.get("status") == "missing" else "source_failed"}
    metadata, permission = "unknown", "unknown"
    try:
        decision = publication_decision
        if type(decision) is not dict or set(decision) != {"owner_ref", "policy_ref", "decision_ref", "metadata", "value_permission", "binding"}:
            return blank
        if (decision["owner_ref"] != "scripts/build_intl.py" or not decision["policy_ref"] or not decision["decision_ref"]
                or decision["binding"] != {"field": "JP.yield_10y", "receipt_sha256": materialized["receipt_sha256"]}):
            return blank
        candidate_metadata, candidate_permission = decision["metadata"], decision["value_permission"]
        if (type(candidate_metadata) is not str or type(candidate_permission) is not str
                or candidate_metadata not in {"allowed", "unknown", "denied"} or candidate_permission not in {"allowed", "unknown", "denied"}):
            return blank
        metadata, permission = candidate_metadata, candidate_permission
        if metadata != "allowed":
            return {**blank, "quality": "denied" if metadata == "denied" else "unknown",
                    "reason": "metadata_denied" if metadata == "denied" else "disclosure_unknown",
                    "metadata": metadata, "value_permission": permission}
        if materialized.get("status") != "ready":
            raise ValueError("source failure after verified capture")
        row = materialized["receipt"]
        source = row["source"]
        if (source.get("source_id") != SOURCE_ID or source.get("unit") != "percent" or source.get("frequency") != "monthly"
                or source.get("adjustment") != "NSA" or source.get("instrument_kind") != "sovereign_10y"):
            raise ValueError("source semantics mismatch")
        evaluated = _utc(evaluated_at)
        observation = datetime.fromisoformat(row["observation_label"]).date()
        end = observation.replace(day=calendar.monthrange(observation.year, observation.month)[1])
        if end >= evaluated.date() or _utc(row["committed_at"]) > evaluated:
            raise ValueError("future or incomplete monthly observation")
        period_end = (end + pd.Timedelta(days=1)).isoformat()
        quality = "qualified" if (evaluated.date() - observation).days <= 45 else "stale"
        out = {**blank, "quality": quality, "reason": None if quality == "qualified" else "source_stale",
               "metadata": metadata, "value_permission": permission,
               "unit": "percent", "instrument": {"kind": "sovereign_10y", "id": SOURCE_ID, "market_id": "JP"},
               "period": {"start": observation.isoformat(), "end": period_end, "count": 1, "count_basis": "release_periods"},
               "observation_at": observation.isoformat(), "calculation_at": None,
               "source_reference": source["source_url"], "evidence_key": materialized["receipt_sha256"]}
        if permission == "allowed":
            out["value"] = row["value"]
        else:
            out.update(quality="denied" if permission == "denied" else "unknown",
                       reason="value_denied" if permission == "denied" else "disclosure_unknown")
        return out
    except (KeyError, TypeError, ValueError, OverflowError):
        if metadata == "allowed":
            return {**blank, "quality": "failed", "reason": "source_failed",
                    "metadata": metadata, "value_permission": permission,
                    "unit": "percent", "instrument": {"kind": "sovereign_10y", "id": SOURCE_ID, "market_id": "JP"}}
        return {**blank, "quality": "failed", "reason": "source_failed"}
