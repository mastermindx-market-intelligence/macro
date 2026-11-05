"""Exact IMF native-edition current-account materialization and Risk projection.

DataMapper's numeric cache is not a vintage/type witness. This path retains the
original workbook and field metadata, and only exposes values under a separate
trusted publisher decision. It performs no acquisition.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import pandas as pd

from lib.intl_macro_publication import _read_stable_once, _reject_duplicate_keys

SERIES = "JPN.BCA_NGDPD.A"
CACHE = Path("imf_weo") / "BCA_NGDPD_JPN.parquet"
DIRECTORY = Path("imf_weo") / "publication" / "JPN_BCA_NGDPD"
COLUMN = "current_account_pct_gdp"
SCHEMA = "intl.weo_current_account_materialization.v1"
LIMIT = 16 * 1024 * 1024
ANNUAL_METHOD = "https://data.imf.org/-/media/iData/External-Storage/Documents/C4182C5C54794FC48892DE8F6C74FF82/en/October-2026-WEO-Database-Appendix.pdf#page=3"


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _utc(value):
    if type(value) is not str:
        raise ValueError("UTC timestamp required")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None or stamp.utcoffset() != timezone.utc.utcoffset(stamp):
        raise ValueError("UTC timestamp required")
    return stamp


def parse_native_current_account(workbook_bytes):
    """Read the actual Countries row; preserve missing reporting-year metadata.

    LATEST_ACTUAL_ANNUAL_DATA distinguishes actuals from later staff estimates.
    It does not provide a threshold for a distinct projection classification.
    """
    from openpyxl import load_workbook

    if type(workbook_bytes) is not bytes or not workbook_bytes or len(workbook_bytes) > LIMIT:
        raise ValueError("invalid source byte image")
    with zipfile.ZipFile(BytesIO(workbook_bytes)) as archive:
        if sum(row.file_size for row in archive.infolist()) > 256 * 1024 * 1024:
            raise ValueError("expanded workbook exceeds bound")
    book = load_workbook(BytesIO(workbook_bytes), read_only=True, data_only=True, keep_links=False)
    try:
        sheet = book["Countries"]
        if sheet.max_row > 100_000 or sheet.max_column > 200:
            raise ValueError("source sheet exceeds bound")
        rows = sheet.iter_rows(values_only=True)
        header = next(rows)
        if len(header) != len(set(header)):
            raise ValueError("ambiguous workbook header")
        selected = []
        for position, values in enumerate(rows, 2):
            row = dict(zip(header, values))
            if row.get("SERIES_CODE") == SERIES:
                selected.append((position, row))
        if len(selected) != 1:
            raise ValueError("missing or duplicate exact source row")
        position, row = selected[0]
        if (row.get("COUNTRY.ID") != "JPN" or row.get("INDICATOR.ID") != "BCA_NGDPD"
                or row.get("FREQUENCY") != "Annual" or row.get("UNIT") != "Percent" or row.get("SCALE") != "Units"
                or not str(row.get("DATASET", "")).startswith("IMF.RES:WEO(")):
            raise ValueError("source instrument or unit mismatch")
        latest_actual = row.get("LATEST_ACTUAL_ANNUAL_DATA")
        if type(latest_actual) is not int or not 1900 <= latest_actual <= 2200:
            raise ValueError("missing field-specific actual boundary")
        publication = row.get("PUBLICATION_DATE")
        update = row.get("UPDATE_DATE")
        _utc(publication); _utc(update)
        country_update = row.get("COUNTRY_UPDATE_DATE")
        if isinstance(country_update, datetime):
            country_update = country_update.date().isoformat()
        elif country_update is not None:
            raise ValueError("ambiguous country update date")
        values = {}
        for key, value in row.items():
            year_text = str(key)
            if len(year_text) == 4 and year_text.isdigit() and value is not None:
                if type(value) not in {int, float} or not math.isfinite(value):
                    raise ValueError("invalid annual observation")
                year = int(year_text)
                values[year] = {"value": value, "observation_type": "actual" if year <= latest_actual else "estimate"}
        if latest_actual not in values:
            raise ValueError("actual endpoint absent from source")
        return {"series_code": SERIES, "dataset": row["DATASET"], "country_id": "JPN",
                "indicator_id": "BCA_NGDPD", "unit": "percent_gdp", "scale": "Units", "frequency": "Annual",
                "publication_at": publication, "source_updated_at": update,
                "country_updated_on": country_update, "latest_actual_year": latest_actual,
                "reporting_year_months": row.get("START_END_MONTHS_OF_REPORTING_YEAR"),
                "methodology": row.get("METHODOLOGY.ID"), "methodology_notes": row.get("METHODOLOGY_NOTES"),
                "worksheet": "Countries", "row": position, "values": values}
    finally:
        book.close()


def _put(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if _read_stable_once(path, LIMIT) != raw:
            raise ValueError("immutable source collision")
        return
    with path.open("xb") as output:
        output.write(raw); output.flush(); os.fsync(output.fileno())


def capture_current_account_commit(*, data_root, workbook_bytes, source_receipt,
                                   returned, committed_at):
    """Bind native response and actual cache after the incumbent upsert succeeds."""
    row = parse_native_current_account(workbook_bytes)
    if (type(source_receipt) is not dict or source_receipt.get("sha256") != _sha(workbook_bytes)
            or source_receipt.get("status") != 200
            or not str(source_receipt.get("url", "")).startswith("https://data.imf.org/")
            or _utc(committed_at) < _utc(source_receipt["received_at"])):
        raise ValueError("unbound source acquisition")
    root = Path(data_root)
    raw = _read_stable_once(root / CACHE, LIMIT)
    stored = pd.read_parquet(BytesIO(raw))
    if stored.columns.tolist() != [COLUMN] or stored.index.has_duplicates or returned.columns.tolist() != [COLUMN]:
        raise ValueError("invalid annual materialization")
    for year, observation in row["values"].items():
        label = pd.Timestamp(f"{year}-12-31")
        if (label not in returned.index or label not in stored.index
                or float(returned.loc[label, COLUMN]) != observation["value"]
                or float(stored.loc[label, COLUMN]) != observation["value"]):
            raise ValueError("response and committed coverage differ")
    receipt = {"schema": SCHEMA, "source_sha256": _sha(workbook_bytes), "artifact_sha256": _sha(raw),
               "source_url": source_receipt["url"], "received_at": source_receipt["received_at"],
               "committed_at": committed_at, "source": row}
    # JSON keys normalize the native annual labels; no dates or values change.
    directory = root / DIRECTORY
    _put(directory / (receipt["source_sha256"] + ".xlsx"), workbook_bytes)
    receipt_raw = _json(receipt)
    _put(directory / (_sha(receipt_raw) + ".json"), receipt_raw)
    fd, temporary = tempfile.mkstemp(prefix=".current-", dir=directory)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(receipt_raw); output.flush(); os.fsync(output.fileno())
        os.replace(temporary, directory / "current.json")
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
    return receipt


def read_current_account_materialization(*, data_root):
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
        receipt_raw = _read_stable_once(pointer, LIMIT)
        # Preserve the exact original capture, including receipt/store clocks
        # and source URL. Equality is not filesystem-writer authentication.
        if _read_stable_once(root / DIRECTORY / (_sha(receipt_raw) + ".json"), LIMIT) != receipt_raw:
            raise ValueError("capture receipt identity changed")
        receipt = json.loads(receipt_raw, object_pairs_hook=_reject_duplicate_keys)
        if type(receipt) is not dict or set(receipt) != {"schema", "source_sha256", "artifact_sha256", "source_url", "received_at", "committed_at", "source"} or receipt["schema"] != SCHEMA:
            raise ValueError("invalid receipt")
        verified_receipt_sha = _sha(receipt_raw)
        for key in ("source_sha256", "artifact_sha256"):
            if type(receipt[key]) is not str or len(receipt[key]) != 64 or any(c not in "0123456789abcdef" for c in receipt[key]):
                raise ValueError("invalid digest")
        workbook = _read_stable_once(root / DIRECTORY / (receipt["source_sha256"] + ".xlsx"), LIMIT)
        artifact = _read_stable_once(root / CACHE, LIMIT)
        if _sha(workbook) != receipt["source_sha256"] or _sha(artifact) != receipt["artifact_sha256"]:
            raise ValueError("changed source or store")
        source = parse_native_current_account(workbook)
        if _json(source) != _json(receipt["source"]) or _utc(receipt["committed_at"]) < _utc(receipt["received_at"]):
            raise ValueError("source provenance mismatch")
        frame = pd.read_parquet(BytesIO(artifact))
        if frame.columns.tolist() != [COLUMN] or frame.index.has_duplicates:
            raise ValueError("invalid stored source")
        for year, value in source["values"].items():
            label = pd.Timestamp(f"{year}-12-31")
            if label not in frame.index or float(frame.loc[label, COLUMN]) != value["value"]:
                raise ValueError("committed response mismatch")
        return {"status": "ready", "receipt": receipt, "receipt_sha256": _sha(receipt_raw)}
    except Exception:
        return ({"status": "failed", "receipt_sha256": verified_receipt_sha}
                if verified_receipt_sha is not None else {"status": "failed"})


def admit_current_account_field(materialized, *, evaluated_at, publication_decision):
    """Project latest source-labelled actual; estimates stay separate in evidence."""
    blank = {"quality": "unknown", "reason": "disclosure_unknown", "metadata": "unknown", "value_permission": "unknown",
             "value": None, "unit": None, "instrument": None, "period": None,
             "observation_at": None, "calculation_at": None, "source_reference": None, "evidence_key": None}
    metadata, permission = "unknown", "unknown"
    try:
        if materialized["status"] != "ready" and not materialized.get("receipt_sha256"):
            return {"measure": {**blank, "quality": materialized["status"], "reason": "not_supplied" if materialized["status"] == "missing" else "source_failed"}, "support": None}
        decision = publication_decision
        if (type(decision) is not dict or set(decision) != {"owner_ref", "policy_ref", "decision_ref", "metadata", "value_permission", "binding"}
                or decision["owner_ref"] != "scripts/build_intl.py" or not decision["policy_ref"] or not decision["decision_ref"]
                or decision["binding"] != {"field": "JP.annual_current_account", "receipt_sha256": materialized["receipt_sha256"]}):
            return {"measure": blank, "support": None}
        candidate_metadata, candidate_permission = decision["metadata"], decision["value_permission"]
        if (type(candidate_metadata) is not str or type(candidate_permission) is not str
                or candidate_metadata not in {"allowed", "denied", "unknown"} or candidate_permission not in {"allowed", "denied", "unknown"}):
            return {"measure": blank, "support": None}
        metadata, permission = candidate_metadata, candidate_permission
        if metadata != "allowed":
            return {"measure": {**blank, "quality": "denied" if metadata == "denied" else "unknown", "reason": "metadata_denied" if metadata == "denied" else "disclosure_unknown", "metadata": metadata, "value_permission": permission}, "support": None}
        if materialized["status"] != "ready":
            raise ValueError("source failure after verified capture")
        receipt = materialized["receipt"]; source = receipt["source"]
        year = source["latest_actual_year"]
        actual = source["values"].get(str(year), source["values"].get(year))
        evaluated = _utc(evaluated_at)
        publication = _utc(source["publication_at"])
        update = source["country_updated_on"]
        if update is None:
            raise ValueError("missing source country update clock")
        source_day = datetime.fromisoformat(update).date()
        if (source_day.isoformat() != update or actual["observation_type"] != "actual"
                or source_day < datetime(year + 1, 1, 1).date()
                or source_day > publication.date() or publication > _utc(receipt["received_at"])
                or _utc(receipt["received_at"]) > _utc(receipt["committed_at"])
                or _utc(receipt["committed_at"]) > evaluated):
            raise ValueError("invalid actual publication chronology")
        # Native country-series update date, not edition publication or local
        # evaluation. The incumbent annual source owner uses a200-day tolerance.
        quality = "stale" if (evaluated.date() - source_day).days > 200 else "qualified"
        measure = {**blank, "quality": quality, "reason": "source_stale" if quality == "stale" else None,
                   "metadata": metadata, "value_permission": permission, "unit": "percent_gdp",
                   "instrument": {"kind": "current_account", "id": SERIES, "market_id": "JP"},
                   "period": {"start": f"{year}-01-01", "end": f"{year+1}-01-01", "count": 1, "count_basis": "release_periods"},
                   "observation_at": update, "calculation_at": None,
                   "source_reference": receipt["source_url"], "evidence_key": materialized["receipt_sha256"]}
        support = {"method_ref": ANNUAL_METHOD, "market_id": "JP",
                   "field_year": year, "vintage": source["publication_at"], "observation_type": "actual"}
        if permission == "allowed": measure["value"] = actual["value"]
        else:
            measure.update(quality="denied" if permission == "denied" else "unknown", reason="value_denied" if permission == "denied" else "disclosure_unknown")
        return {"measure": measure, "support": support}
    except (KeyError, TypeError, ValueError, OverflowError):
        if metadata == "allowed":
            # Only a previously validated, bound publisher decision survives.
            # Retain static typed field descriptors so the existing Risk mount
            # can report source_failed, with no value/dynamic clock/source.
            return {"measure": {**blank, "quality": "failed", "reason": "source_failed",
                    "metadata": metadata, "value_permission": permission, "unit": "percent_gdp",
                    "instrument": {"kind": "current_account", "id": SERIES, "market_id": "JP"}}, "support": None}
        return {"measure": {**blank, "quality": "failed", "reason": "source_failed"}, "support": None}
