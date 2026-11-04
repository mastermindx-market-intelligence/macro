"""Exact EA21 Eurostat YoY fields, successful-store evidence and disclosure.

Economic period ends, dataset updates, acquisition requests and local verification
are different clocks. A retained response supplies no original HTTP receipt time.
"""
from __future__ import annotations

from datetime import datetime, timezone, date, timedelta
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import json
import math
import os
import tempfile
import re

import pandas as pd

from lib.intl_macro_publication import _read_stable_once, _reject_duplicate_keys
from lib.intl_yield_publication import _json, _sha, _utc, _put
from lib.intl_eurostat_source import parse_eurostat_series

FIELDS = {
    "EZ.gdp_yoy": {
        "column": "EZ_gdp_yoy_official", "dataset": "NAMQ_10_GDP",
        "selectors": {"freq": "Q", "unit": "CLV_PCH_SM", "s_adj": "SCA", "na_item": "B1GQ", "geo": "EA21"},
        "max_age_days": 120,
    },
    "EZ.cpi_yoy": {
        "column": "EZ_hicp_yoy_official", "dataset": "PRC_HICP_MINR",
        "selectors": {"freq": "M", "unit": "RCH_A", "coicop18": "TOTAL", "geo": "EA21"},
        "max_age_days": 75,
    },
}
POLICY = "docs/INTERNATIONAL_MACRO_DATA_CONTRACT.md#official-eurostat-ea21-gdp-and-hicp"
SCHEMA = "intl.eurostat_yoy_materialization.v1"
LIMIT = 8 * 1024 * 1024


def _spec(field):
    if type(field) is not str or field not in FIELDS:
        raise ValueError("unsupported Eurostat field")
    return FIELDS[field]


def instrument_id(field):
    spec = _spec(field)
    return spec["dataset"] + "/" + "/".join(spec["selectors"].values())


def _source_time(value):
    if type(value) is not str:
        raise ValueError("source update clock required")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("source update offset required")
    return stamp.astimezone(timezone.utc)


def _decode(raw):
    if type(raw) is not bytes or not raw or len(raw) > LIMIT:
        raise ValueError("invalid native source bytes")
    return json.loads(raw, object_pairs_hook=_reject_duplicate_keys,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def _source_url(field, value):
    spec = _spec(field)
    if type(value) is not str:
        raise ValueError("source URL required")
    u = urlsplit(value)
    if (u.scheme != "https" or u.netloc != "ec.europa.eu" or u.fragment
            or u.path.lower() != "/eurostat/api/dissemination/statistics/1.0/data/" + spec["dataset"].lower()):
        raise ValueError("source origin or dataset mismatch")
    query = parse_qs(u.query, keep_blank_values=True, strict_parsing=True)
    allowed = set(spec["selectors"]) | {"lang", "sinceTimePeriod"}
    if not set(query) <= allowed or any(len(v) != 1 for v in query.values()):
        raise ValueError("ambiguous source query")
    for key, expected in spec["selectors"].items():
        # The actual retained HICP response contains all 555 categories. TOTAL
        # is selected against returned positions, even when not request-filtered.
        if key == "coicop18" and key not in query:
            continue
        if query.get(key) != [expected]:
            raise ValueError("requested source dimensions mismatch")
    return value


def parse_native_field(field, response_bytes):
    spec = _spec(field)
    parsed = parse_eurostat_series(_decode(response_bytes), dataset=spec["dataset"], selectors=spec["selectors"])
    _source_time(parsed["updated"])
    rows = [r for r in parsed["observations"] if r["value"] is not None]
    if not rows:
        raise ValueError("no selected native observations")
    frame = pd.DataFrame({spec["column"]: [r["value"] for r in rows]},
                         index=pd.DatetimeIndex([r["observation_at"] for r in rows], name="date"))
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("ambiguous selected economic periods")
    return parsed, frame


def _series(field, frame):
    column = _spec(field)["column"]
    if (type(frame) is not pd.DataFrame or frame.columns.tolist() != [column]
            or not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is not None
            or frame.index.has_duplicates or not frame.index.is_monotonic_increasing):
        raise ValueError("invalid canonical Eurostat series")
    s = frame[column].dropna()
    if (not pd.api.types.is_numeric_dtype(s.dtype) or pd.api.types.is_bool_dtype(s.dtype)
            or s.empty or any(d != d.normalize() for d in s.index) or not all(math.isfinite(float(v)) for v in s)):
        raise ValueError("invalid canonical Eurostat observations")
    return s


def capture_eurostat_commit(*, field, data_root, returned, response_bytes,
                            source_url, requested_at, input_verified_at,
                            committed_at, response_received_at=None):
    """Capture only after the incumbent canonical upsert succeeded."""
    spec = _spec(field)
    _source_url(field, source_url)
    parsed, original = parse_native_field(field, response_bytes)
    requested, verified, committed = map(_utc, (requested_at, input_verified_at, committed_at))
    if not _source_time(parsed["updated"]) <= requested <= verified <= committed:
        raise ValueError("source or commit chronology mismatch")
    if response_received_at is not None and not requested <= _utc(response_received_at) <= verified:
        raise ValueError("response chronology mismatch")
    supplied = _series(field, returned)
    native = _series(field, original)
    if supplied.index.tolist() != native.index.tolist() or list(map(float, supplied)) != list(map(float, native)):
        raise ValueError("returned source coverage mismatch")
    root = Path(data_root)
    artifact = _read_stable_once(root / "intl_macro" / (spec["column"] + ".parquet"), LIMIT)
    saved = _series(field, pd.read_parquet(BytesIO(artifact)))
    if saved.index[-1] != supplied.index[-1] or any(d not in saved or float(saved.loc[d]) != float(v) for d, v in supplied.items()):
        raise ValueError("successful store does not match source coverage")
    receipt = {"schema": SCHEMA, "field": field, "column": spec["column"],
               "dataset": spec["dataset"], "selectors": spec["selectors"],
               "source_url": source_url, "source_sha256": _sha(response_bytes),
               "artifact_sha256": _sha(artifact), "requested_at": requested_at,
               "input_verified_at": input_verified_at, "response_received_at": response_received_at,
               "committed_at": committed_at, "source_updated": parsed["updated"],
               "observations": parsed["observations"], "provider_published_at": None,
               "revision_vintage": None}
    directory = root / "intl_macro" / "publication" / spec["column"]
    _put(directory / (_sha(response_bytes) + ".source.json"), response_bytes)
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


def read_eurostat_materialization(*, field, data_root):
    spec = _spec(field)
    root = Path(data_root)
    directory = root / "intl_macro" / "publication" / spec["column"]
    pointer = directory / "current.json"
    verified_digest = None
    try:
        pointer.lstat()
    except FileNotFoundError:
        return {"status": "missing"}
    except Exception:
        return {"status": "failed"}
    try:
        raw = _read_stable_once(pointer, LIMIT)
        if _read_stable_once(directory / (_sha(raw) + ".json"), LIMIT) != raw:
            raise ValueError("original capture receipt mismatch")
        receipt = _decode(raw)
        expected = {"schema", "field", "column", "dataset", "selectors", "source_url", "source_sha256",
                    "artifact_sha256", "requested_at", "input_verified_at", "response_received_at", "committed_at",
                    "source_updated", "observations", "provider_published_at", "revision_vintage"}
        if (type(receipt) is not dict or set(receipt) != expected or receipt["schema"] != SCHEMA
                or receipt["field"] != field or receipt["column"] != spec["column"]
                or receipt["dataset"] != spec["dataset"] or receipt["selectors"] != spec["selectors"]
                or receipt["provider_published_at"] is not None or receipt["revision_vintage"] is not None):
            raise ValueError("capture source contract mismatch")
        verified_digest = _sha(raw)
        if any(type(receipt[k]) is not str or re.fullmatch(r"[0-9a-f]{64}", receipt[k]) is None
               for k in ("source_sha256", "artifact_sha256")):
            raise ValueError("invalid retained content identity")
        _source_url(field, receipt["source_url"])
        source = _read_stable_once(directory / (receipt["source_sha256"] + ".source.json"), LIMIT)
        artifact = _read_stable_once(root / "intl_macro" / (spec["column"] + ".parquet"), LIMIT)
        if _sha(source) != receipt["source_sha256"] or _sha(artifact) != receipt["artifact_sha256"]:
            raise ValueError("canonical source or store changed")
        parsed, frame = parse_native_field(field, source)
        if parsed["updated"] != receipt["source_updated"] or parsed["observations"] != receipt["observations"]:
            raise ValueError("selected source metadata changed")
        saved = _series(field, pd.read_parquet(BytesIO(artifact)))
        supplied = _series(field, frame)
        if saved.index[-1] != supplied.index[-1] or any(d not in saved or float(saved.loc[d]) != float(v) for d, v in supplied.items()):
            raise ValueError("canonical response coverage changed")
        return {"status": "ready", "receipt_sha256": verified_digest, "receipt": receipt}
    except Exception:
        return {"status": "failed", **({"receipt_sha256": verified_digest} if verified_digest else {})}


def admit_eurostat_field(materialized, *, field, evaluated_at, publication_decision):
    spec = _spec(field)
    blank = {"quality": "unknown", "reason": "disclosure_unknown", "metadata": "unknown",
             "value_permission": "unknown", "value": None, "unit": None, "instrument": None,
             "period": None, "observation_at": None, "calculation_at": None,
             "source_reference": None, "evidence_key": None}
    metadata = permission = "unknown"
    def result(measure, evidence=None):
        return {"measure": measure, "evidence": evidence}
    if materialized.get("status") != "ready" and not materialized.get("receipt_sha256"):
        missing = materialized.get("status") == "missing"
        return result({**blank, "quality": "missing" if missing else "failed", "reason": "not_supplied" if missing else "source_failed"})
    try:
        d = publication_decision
        if (type(d) is not dict or set(d) != {"owner_ref", "policy_ref", "decision_ref", "metadata", "value_permission", "binding"}
                or d["owner_ref"] != "scripts/build_intl.py" or d["policy_ref"] != POLICY
                or type(d["decision_ref"]) is not str or not d["decision_ref"]
                or d["binding"] != {"field": field, "receipt_sha256": materialized["receipt_sha256"]}):
            return result(blank)
        if any(type(d[k]) is not str or d[k] not in {"allowed", "unknown", "denied"} for k in ["metadata", "value_permission"]):
            return result(blank)
        metadata, permission = d["metadata"], d["value_permission"]
        if metadata != "allowed":
            return result({**blank, "metadata": metadata, "value_permission": permission,
                           "quality": "denied" if metadata == "denied" else "unknown",
                           "reason": "metadata_denied" if metadata == "denied" else "disclosure_unknown"})
        if materialized.get("status") != "ready":
            raise ValueError("source failure after verified capture")
        r = materialized["receipt"]
        e = _utc(evaluated_at)
        if not _source_time(r["source_updated"]) <= _utc(r["requested_at"]) <= _utc(r["input_verified_at"]) <= _utc(r["committed_at"]) <= e:
            raise ValueError("source chronology mismatch")
        if r["response_received_at"] is not None and not _utc(r["requested_at"]) <= _utc(r["response_received_at"]) <= _utc(r["input_verified_at"]):
            raise ValueError("response chronology mismatch")
        latest = next(row for row in reversed(r["observations"]) if row["value"] is not None)
        end = datetime.fromisoformat(latest["observation_at"]).date()
        if end > _source_time(r["source_updated"]).date() or end > e.date():
            raise ValueError("economic period not completed")
        stale = (e.date() - end).days > spec["max_age_days"]
        out = {**blank, "quality": "stale" if stale else "qualified", "reason": "source_stale" if stale else None,
               "metadata": metadata, "value_permission": permission, "unit": "percent",
               "instrument": {"kind": "macro_yoy", "id": instrument_id(field), "market_id": "EZ"},
               "period": {"start": latest["period_start"], "end": latest["period_end_exclusive"], "count": 1, "count_basis": "release_periods"},
               "observation_at": latest["observation_at"], "calculation_at": None,
               "source_reference": r["source_url"], "evidence_key": materialized["receipt_sha256"]}
        if permission == "allowed":
            out["value"] = latest["value"]
        else:
            out.update(quality="denied" if permission == "denied" else "unknown", reason="value_denied" if permission == "denied" else "disclosure_unknown")
        evidence = {"field": field, "instrument_id": instrument_id(field), "source_reference": out["source_reference"],
                    "evidence_key": out["evidence_key"], "period_label": latest["period"],
                    "dataset_updated_at": r["source_updated"], "observation_status": latest["status"],
                    "requested_at": r["requested_at"], "response_received_at": r["response_received_at"],
                    "input_verified_at": r["input_verified_at"], "committed_at": r["committed_at"]}
        return result(out, evidence)
    except (KeyError, TypeError, ValueError, OverflowError, StopIteration):
        quality, reason = "failed", "source_failed"
        if metadata == "allowed" and permission != "allowed":
            quality = "denied" if permission == "denied" else "unknown"
            reason = "value_denied" if permission == "denied" else "disclosure_unknown"
        return result({**blank, "quality": quality, "reason": reason, "metadata": metadata,
                       "value_permission": permission, **({"unit": "percent", "instrument": {"kind": "macro_yoy", "id": instrument_id(field), "market_id": "EZ"}} if metadata == "allowed" else {})})


def project_field_evidence(field_evidence, measures):
    """Narrow additive Macro metadata projection, bound to the typed measure.

    This validates the caller's projection; the actual capture reader establishes
    source/store integrity. Neither dictionaries nor a matching digest authenticate
    an arbitrary filesystem writer.
    """
    if field_evidence is None:
        return {}
    if type(field_evidence) is not dict or not set(field_evidence) <= set(FIELDS):
        raise ValueError("invalid Eurostat field evidence")
    keys = {"field", "instrument_id", "source_reference", "evidence_key", "period_label",
            "dataset_updated_at", "observation_status", "requested_at", "response_received_at",
            "input_verified_at", "committed_at"}
    projected = {}
    for field, evidence in field_evidence.items():
        measure = measures.get(field)
        if type(measure) is not dict or measure.get("metadata") != "allowed":
            continue
        if type(evidence) is not dict or set(evidence) != keys:
            raise ValueError("invalid Eurostat evidence shape")
        if (evidence["field"] != field or evidence["instrument_id"] != instrument_id(field)
                or measure.get("instrument") != {"kind": "macro_yoy", "id": instrument_id(field), "market_id": "EZ"}
                or evidence["source_reference"] != measure.get("source_reference")
                or evidence["evidence_key"] != measure.get("evidence_key")
                or type(evidence["evidence_key"]) is not str
                or re.fullmatch(r"[0-9a-f]{64}", evidence["evidence_key"]) is None):
            raise ValueError("Eurostat evidence binding mismatch")
        _source_url(field, evidence["source_reference"])
        label = evidence["period_label"]
        if field == "EZ.gdp_yoy":
            if type(label) is not str or re.fullmatch(r"[0-9]{4}-Q[1-4]", label) is None:
                raise ValueError("quarter label required")
            year, month = int(label[:4]), (int(label[-1]) - 1) * 3 + 1
            start = date(year, month, 1)
            end = date(year + 1, 1, 1) if month == 10 else date(year, month + 3, 1)
        else:
            if type(label) is not str or re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", label) is None:
                raise ValueError("month label required")
            year, month = int(label[:4]), int(label[5:])
            start = date(year, month, 1)
            end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        if (measure.get("observation_at") != (end - timedelta(days=1)).isoformat()
                or measure.get("period") != {"start": start.isoformat(), "end": end.isoformat(), "count": 1, "count_basis": "release_periods"}):
            raise ValueError("economic period projection mismatch")
        if not _source_time(evidence["dataset_updated_at"]) <= _utc(evidence["requested_at"]) <= _utc(evidence["input_verified_at"]) <= _utc(evidence["committed_at"]):
            raise ValueError("projected source chronology mismatch")
        if evidence["response_received_at"] is not None and not _utc(evidence["requested_at"]) <= _utc(evidence["response_received_at"]) <= _utc(evidence["input_verified_at"]):
            raise ValueError("projected response chronology mismatch")
        if evidence["observation_status"] is not None and type(evidence["observation_status"]) is not str:
            raise ValueError("source status flag must remain native text")
        projected[field] = deepcopy(evidence)
    return projected
