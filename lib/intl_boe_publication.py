"""Post-store evidence for the Bank of England Official Bank Rate (IUDBEDR).

The reader proves response/cache agreement, not provider publication time or
permission. Only the normal publisher's separate byte-bound decision may expose
a value. No network or acquisition retry lives in this module.

``capture_boe_commit`` runs only after the canonical ``store.upsert`` has
succeeded. It binds the actual ``intl_macro/GB_bank_rate_official.parquet``
bytes and the original provider XML into one immutable, content-addressed
receipt, and publishes that receipt through an atomically replaced selector. A
failure here is an evidence failure: the canonical write already happened, it
must not be undone, and it must never be retried as an acquisition.

``read_boe_materialization`` re-proves that agreement from the bytes on disk.
The selector must still equal the original receipt sidecar exactly; the receipt
must still name the canonical BoE carrier and its exact query contract; the
original XML must still hash to the captured response; and every native
observed row must still match the actual stored artifact. A missing capture is
``missing``; a present but broken capture is ``failed``.

``admit_boe_policy_field`` is a pure projection of that evidence under an
independently supplied publisher decision. It returns the existing closed native
measure shape and binds the decision to the exact field and receipt digest.

Selection rules the field obeys:

* every native observation must lie inside the range the pinned carrier asked
  the provider for; a row outside it is not evidence from that carrier;
* with no ``observation_date`` the field is the LATEST supplied native row;
  a withheld tail stays unavailable and never falls back to an older value;
* with an explicit ``observation_date`` the field is that exact native row --
  no nearest match, no fill, no substitution;
* the current display applies the existing ``engine.cb_desk`` daily
  observation-age rule; an explicit historical endpoint bypasses that current
  age rule and remains latest-vintage evidence, not originally known evidence.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit, urlencode

import pandas as pd

from lib.intl_boe_source import parse_bank_rate_xml
from lib.intl_macro_publication import (
    _read_stable_once,
    _observe_native_path,
    _reject_duplicate_keys,
    _reject_nonstandard_constant,
)

COLUMN = "GB_bank_rate_official"
FIELD = "GB.policy_rate"
MARKET_ID = "GB"
PROVIDER = "boe"
SERIES_ID = "IUDBEDR"
INSTRUMENT_ID = "bank_rate"
UNIT = "percent"
FREQUENCY = "daily"
SCHEMA = "intl.gb_bank_rate_materialization.v1"
POLICY_REF = "docs/INTERNATIONAL_MACRO_DATA_CONTRACT.md#official-boe-bank-rate-admission"
OWNER_REF = "scripts/build_intl.py"

ARTIFACT_PATH = Path("intl_macro") / (COLUMN + ".parquet")
DIRECTORY = Path("intl_macro") / "publication" / COLUMN

#: Retained original carrier example. The validated native interval remains
#: part of each immutable receipt, bounded to one calendar year.
SOURCE_URL = (
    "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"
    "?CodeVer=new&xml.x=yes&Datefrom=01%2FJan%2F2026&Dateto=02%2FNov%2F2026"
    "&SeriesCodes=IUDBEDR&VPD=N&VFD=Y&VUD=A"
)
#: The exact recognised query contract of that carrier.
SOURCE_QUERY = {
    "CodeVer": "new",
    "Dateto": "02/Nov/2026",
    "Datefrom": "01/Jan/2026",
    "SeriesCodes": "IUDBEDR",
    "VFD": "Y",
    "VPD": "N",
    "VUD": "A",
    "xml.x": "yes",
}
SOURCE_PATH = "/boeapps/database/_iadb-fromshowcolumns.asp"
SOURCE_HOST = "www.bankofengland.co.uk"

ARTIFACT_LIMIT = 16 * 1024 * 1024
SOURCE_LIMIT = 8 * 1024 * 1024
RECEIPT_LIMIT = 8 * 1024 * 1024

_PERMISSIONS = {"allowed", "unknown", "denied"}
_STATUS_OBSERVED = "observed"
_STATUS_WITHHELD = "withheld"
_ROW_KEYS = {"date", "value", "status", "source_updated_raw"}
_RECEIPT_KEYS = {
    "schema", "column", "provider", "series_id", "market_id", "instrument_id",
    "unit", "frequency", "source_url", "source_query", "source_sha256",
    "artifact_sha256", "artifact_column", "requested_at", "response_received_at",
    "input_verified_at", "committed_at", "provider_published_at",
    "revision_vintage", "observation_label", "value", "value_status",
    "response_rows", "observed_rows", "withheld_rows", "notes", "rows",
}
_INSTRUMENT = {"kind": "official_policy", "id": INSTRUMENT_ID, "market_id": MARKET_ID}


# --------------------------------------------------------------------------
# Small helpers.
# --------------------------------------------------------------------------


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode()


def _utc(value):
    """Return the parsed instant of an ISO-8601 string carrying a UTC offset."""
    if type(value) is not str:
        raise ValueError("UTC instant required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("UTC instant required")
    return parsed


def _require_source_url(url) -> str:
    """Return the canonical carrier, or refuse an unrecognised source contract."""
    if type(url) is not str:
        raise ValueError("unrecognized original source contract")
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.netloc != SOURCE_HOST
            or parts.path != SOURCE_PATH or parts.fragment):
        raise ValueError("unrecognized original source contract")
    try:
        query = parse_qsl(parts.query, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise ValueError("unrecognized source query contract") from exc
    if len(query) != len(SOURCE_QUERY) or set(key for key, _ in query) != set(SOURCE_QUERY):
        raise ValueError("unrecognized source query contract")
    order = ("CodeVer", "xml.x", "Datefrom", "Dateto", "SeriesCodes", "VPD", "VFD", "VUD")
    if tuple(key for key, _ in query) != order:
        raise ValueError("noncanonical original source query order")
    if url != "https://" + SOURCE_HOST + SOURCE_PATH + "?" + urlencode(query):
        raise ValueError("noncanonical original source carrier encoding")
    supplied = dict(query)
    fixed = {k: v for k, v in SOURCE_QUERY.items() if k not in {"Datefrom", "Dateto"}}
    if any(supplied[k] != v for k, v in fixed.items()):
        raise ValueError("unrecognized source query contract")
    start, end = (_request_date(supplied[k]) for k in ("Datefrom", "Dateto"))
    if start.year != end.year or end < start:
        raise ValueError("source interval exceeds the native calendar-year bound")
    return url


def _request_date(text):
    months = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
              "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
    bits = text.split("/")
    if (len(bits) != 3 or len(bits[0]) != 2 or len(bits[2]) != 4
            or not bits[0].isdigit() or not bits[2].isdigit() or bits[1] not in months):
        raise ValueError("unrecognized source query contract")
    return date(int(bits[2]), months[bits[1]], int(bits[0]))


def _source_window(source_url=SOURCE_URL):
    query = dict(parse_qsl(urlsplit(_require_source_url(source_url)).query,
                           keep_blank_values=True, strict_parsing=True))
    return _request_date(query["Datefrom"]), _request_date(query["Dateto"])


def _require_window(rows, source_url=SOURCE_URL) -> None:
    """Require every native observation to lie inside the supplied range.

    The pinned carrier names the range it asked for. A row outside it is not
    evidence from that carrier, whatever the provider returned.
    """
    start, end = _source_window(source_url)
    for row in rows:
        observed = datetime.strptime(row["date"], "%Y-%m-%d").date()
        if observed < start or observed > end:
            raise ValueError("observation outside the supplied source range")


def _require_source_identity(parsed) -> None:
    """Require the response to be exactly the official IUDBEDR daily series."""
    if (type(parsed) is not dict
            or parsed.get("series_id") != SERIES_ID
            or parsed.get("market_id") != MARKET_ID
            or parsed.get("instrument_id") != INSTRUMENT_ID
            or parsed.get("unit") != UNIT
            or parsed.get("frequency") != "D"):
        raise ValueError("unrecognized original source contract")


def _source_rows(parsed) -> list:
    """Return the native observation rows of one parsed response.

    The provider's per-row ``LAST_UPDATED`` string is kept exactly as supplied.
    It carries no time zone in the response, so it is never read as UTC and
    never becomes a publication, vintage or calculation clock.
    """
    rows = []
    for observation in parsed["observations"]:
        status = observation["status"]
        value = observation["value"]
        if status == _STATUS_OBSERVED:
            if type(value) not in {int, float} or not math.isfinite(float(value)):
                raise ValueError("nonfinite source value")
        elif status == _STATUS_WITHHELD:
            if value is not None:
                raise ValueError("withheld source row carries a value")
        else:
            raise ValueError("unknown source row status")
        updated = observation["source_updated_raw"]
        if updated is not None and type(updated) is not str:
            raise ValueError("invalid source clock")
        rows.append({
            "date": observation["date"],
            "value": value,
            "status": status,
            "source_updated_raw": updated,
        })
    return rows


def _canonical_series(frame):
    """Return the canonical stored column of a supplied or stored frame."""
    if type(frame) is pd.DataFrame:
        if frame.columns.tolist() != [COLUMN]:
            raise ValueError("invalid source columns")
        series = frame[COLUMN]
    elif isinstance(frame, pd.Series):
        if frame.name != COLUMN:
            raise ValueError("invalid source columns")
        series = frame
    else:
        raise ValueError("invalid source frame")
    if not isinstance(series.index, pd.DatetimeIndex):
        raise ValueError("invalid source index")
    if series.index.tz is not None or not series.index.equals(series.index.normalize()):
        raise ValueError("invalid source index")
    if series.index.hasnans or series.index.has_duplicates or not series.index.is_monotonic_increasing:
        raise ValueError("invalid source index")
    if (series.empty or not pd.api.types.is_numeric_dtype(series.dtype)
            or pd.api.types.is_bool_dtype(series.dtype)):
        raise ValueError("invalid numeric source frame")
    if not all(math.isfinite(float(value)) for value in series.dropna()):
        raise ValueError("nonfinite source value")
    return series


def _require_coverage(rows, series, label) -> None:
    """Require every native observed row to match the actual current store.

    Extra incumbent history is allowed, and a withheld native row is never
    filled from an older cached store value.
    """
    values = {}
    for stamp, value in series.items():
        if value is None or pd.isna(value):
            continue
        values[stamp.date().isoformat()] = float(value)
    observed = [row for row in rows if row["status"] == _STATUS_OBSERVED]
    if not observed:
        raise ValueError("source response carries no observed observations")
    for row in observed:
        date = row["date"]
        if date not in values or values[date] != float(row["value"]):
            raise ValueError("%s coverage mismatch" % label)
    if series.index[-1].date().isoformat() < observed[-1]["date"]:
        raise ValueError("%s does not cover the response endpoint" % label)


def _existing(path: Path, limit: int) -> bytes:
    """Return the bytes of one already stored immutable object."""
    try:
        return _read_stable_once(path, limit)
    except OSError as exc:
        raise ValueError("immutable source is unreadable") from exc


def _put(path: Path, raw: bytes, limit: int) -> None:
    """Write one immutable content-addressed object exactly once."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if _existing(path, limit) != raw:
            raise ValueError("immutable source identity collision")
        return
    try:
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        # A concurrent writer won the exclusive create. The object is
        # content-addressed, so the same bytes are the same object.
        if _existing(path, limit) != raw:
            raise ValueError("immutable source identity collision")


def _publish(directory: Path, raw: bytes) -> None:
    """Replace the mutable selector with exactly the receipt bytes."""
    fd, temporary = tempfile.mkstemp(prefix=".current-", dir=directory)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, directory / "current.json")
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _missing_result() -> dict:
    """Return the closed shape of a capture that was never written."""
    return {"status": "missing", "series": None, "receipt": None,
            "receipt_sha256": None}


def _failed_result(receipt_sha) -> dict:
    """Return the closed shape of a capture that is present but broken."""
    return {"status": "failed", "series": None, "receipt": None,
            "receipt_sha256": receipt_sha}


def _require_receipt(receipt) -> None:
    """Require one exact, self-consistent capture receipt."""
    if type(receipt) is not dict or set(receipt) != _RECEIPT_KEYS:
        raise ValueError("invalid receipt")
    if (receipt["schema"] != SCHEMA or receipt["column"] != COLUMN
            or receipt["provider"] != PROVIDER or receipt["series_id"] != SERIES_ID
            or receipt["market_id"] != MARKET_ID or receipt["instrument_id"] != INSTRUMENT_ID
            or receipt["unit"] != UNIT or receipt["frequency"] != FREQUENCY
            or receipt["artifact_column"] != COLUMN):
        raise ValueError("invalid receipt identity")
    if receipt["provider_published_at"] is not None or receipt["revision_vintage"] is not None:
        raise ValueError("invalid source semantics")
    _require_source_url(receipt["source_url"])
    if (type(receipt["source_query"]) is not dict
            or dict(receipt["source_query"]) != dict(parse_qsl(urlsplit(receipt["source_url"]).query,
                keep_blank_values=True, strict_parsing=True))):
        raise ValueError("invalid source query contract")
    for key in ("source_sha256", "artifact_sha256"):
        digest = receipt[key]
        if (type(digest) is not str or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)):
            raise ValueError("invalid digest")
    requested = _utc(receipt["requested_at"])
    received = _utc(receipt["response_received_at"])
    verified = _utc(receipt["input_verified_at"])
    committed = _utc(receipt["committed_at"])
    if not (requested <= received <= verified <= committed):
        raise ValueError("invalid source chronology")
    rows = receipt["rows"]
    if type(rows) is not list or not rows:
        raise ValueError("invalid source rows")
    dates = []
    observed = 0
    withheld = 0
    for row in rows:
        if type(row) is not dict or set(row) != _ROW_KEYS:
            raise ValueError("invalid source rows")
        if (type(row["date"]) is not str or type(row["status"]) is not str
                or row["status"] not in {_STATUS_OBSERVED, _STATUS_WITHHELD}):
            raise ValueError("invalid source rows")
        value = row["value"]
        if row["status"] == _STATUS_OBSERVED:
            if type(value) not in {int, float} or not math.isfinite(float(value)):
                raise ValueError("invalid source rows")
            observed += 1
        else:
            if value is not None:
                raise ValueError("invalid source rows")
            withheld += 1
        updated = row["source_updated_raw"]
        if updated is not None and type(updated) is not str:
            raise ValueError("invalid source rows")
        dates.append(row["date"])
    if dates != sorted(dates) or len(set(dates)) != len(dates):
        raise ValueError("invalid source rows")
    if (type(receipt["response_rows"]) is not int or receipt["response_rows"] != len(rows)
            or type(receipt["observed_rows"]) is not int or receipt["observed_rows"] != observed
            or type(receipt["withheld_rows"]) is not int or receipt["withheld_rows"] != withheld):
        raise ValueError("invalid source counts")
    if type(receipt["notes"]) is not list or any(type(note) is not str for note in receipt["notes"]):
        raise ValueError("invalid source notes")
    if (receipt["observation_label"] != rows[-1]["date"]
            or receipt["value_status"] != rows[-1]["status"]):
        raise ValueError("invalid receipt endpoint")
    value = receipt["value"]
    if rows[-1]["status"] == _STATUS_OBSERVED:
        if type(value) not in {int, float} or not math.isfinite(float(value)):
            raise ValueError("invalid receipt endpoint")
        if float(value) != float(rows[-1]["value"]):
            raise ValueError("invalid receipt endpoint")
    elif value is not None:
        raise ValueError("invalid receipt endpoint")


# --------------------------------------------------------------------------
# Public API.
# --------------------------------------------------------------------------


def capture_boe_commit(data_root, returned, response_bytes, source_url, requested_at,
                       response_received_at, input_verified_at, committed_at):
    """Bind one committed BoE response to the actual stored artifact.

    Call this only after the canonical ``store.upsert`` has succeeded. The
    write has already happened: a failure here is an evidence failure for the
    composition owner, never a reason to acquire the response again.

    ``returned`` is the frame the canonical store returned, ``response_bytes``
    the original provider response, and the four clocks the actual UTC instants
    of the request, the response, the verified input and the committed write.

    Every evidence failure raises :class:`ValueError`; none of them is a
    request to acquire the response again.
    """
    url = _require_source_url(source_url)
    requested = _utc(requested_at)
    received = _utc(response_received_at)
    verified = _utc(input_verified_at)
    committed = _utc(committed_at)
    if not (requested <= received <= verified <= committed):
        raise ValueError("invalid source chronology")
    if (type(response_bytes) is not bytes or not response_bytes
            or len(response_bytes) > SOURCE_LIMIT):
        raise ValueError("unrecognized original source contract")

    parsed = parse_bank_rate_xml(response_bytes)
    _require_source_identity(parsed)
    rows = _source_rows(parsed)
    if not rows:
        raise ValueError("source response carries no observations")
    _require_window(rows, url)

    supplied = _canonical_series(returned)
    _require_coverage(rows, supplied, "returned")

    root = Path(data_root)
    try:
        artifact = _read_stable_once(root / ARTIFACT_PATH, ARTIFACT_LIMIT)
    except OSError as exc:
        raise ValueError("committed artifact is unavailable") from exc
    stored = _canonical_series(pd.read_parquet(BytesIO(artifact)))
    _require_coverage(rows, stored, "stored")

    observed = [row for row in rows if row["status"] == _STATUS_OBSERVED]
    receipt = {
        "schema": SCHEMA,
        "column": COLUMN,
        "provider": PROVIDER,
        "series_id": SERIES_ID,
        "market_id": MARKET_ID,
        "instrument_id": INSTRUMENT_ID,
        "unit": UNIT,
        "frequency": FREQUENCY,
        "source_url": url,
        "source_query": dict(parse_qsl(urlsplit(url).query, keep_blank_values=True,
                                       strict_parsing=True)),
        "source_sha256": _sha(response_bytes),
        "artifact_sha256": _sha(artifact),
        "artifact_column": COLUMN,
        "requested_at": requested_at,
        "response_received_at": response_received_at,
        "input_verified_at": input_verified_at,
        "committed_at": committed_at,
        "provider_published_at": None,
        "revision_vintage": None,
        "observation_label": rows[-1]["date"],
        "value": rows[-1]["value"],
        "value_status": rows[-1]["status"],
        "response_rows": len(rows),
        "observed_rows": len(observed),
        "withheld_rows": len(rows) - len(observed),
        "notes": list(parsed["notes"]),
        "rows": rows,
    }
    directory = root / DIRECTORY
    raw = _json(receipt)
    try:
        _put(directory / (receipt["source_sha256"] + ".xml"), response_bytes, SOURCE_LIMIT)
        _put(directory / (_sha(raw) + ".json"), raw, RECEIPT_LIMIT)
        _publish(directory, raw)
    except OSError as exc:
        raise ValueError("capture evidence could not be written") from exc
    return receipt


def read_boe_materialization(data_root):
    """Read one exact BoE capture and prove it against the actual bytes.

    The mutable selector must retain the original capture's exact bytes before
    the receipt, its clocks and its URL are trusted at all. This is integrity
    within the incumbent store trust, not authentication of arbitrary
    filesystem writers.
    """
    root = Path(data_root)
    directory = root / DIRECTORY
    pointer = directory / "current.json"
    try:
        _observe_native_path(pointer)
        pointer.lstat()
    except FileNotFoundError:
        return _missing_result()
    except Exception:
        return _failed_result(None)
    verified_receipt_sha = None
    try:
        raw = _read_stable_once(pointer, RECEIPT_LIMIT)
        if _read_stable_once(directory / (_sha(raw) + ".json"), RECEIPT_LIMIT) != raw:
            raise ValueError("capture receipt identity changed")
        receipt = json.loads(raw, object_pairs_hook=_reject_duplicate_keys,
                             parse_constant=_reject_nonstandard_constant)
        _require_receipt(receipt)
        verified_receipt_sha = _sha(raw)
        source_raw = _read_stable_once(directory / (receipt["source_sha256"] + ".xml"),
                                       SOURCE_LIMIT)
        if _sha(source_raw) != receipt["source_sha256"]:
            raise ValueError("original response identity changed")
        artifact = _read_stable_once(root / ARTIFACT_PATH, ARTIFACT_LIMIT)
        if _sha(artifact) != receipt["artifact_sha256"]:
            raise ValueError("materialization identity changed")
        # Validate the actual response, committed bytes and supplied rows
        # independently; the receipt is not an input-data permission grant.
        parsed = parse_bank_rate_xml(source_raw)
        _require_source_identity(parsed)
        rows = _source_rows(parsed)
        _require_window(rows, receipt["source_url"])
        if rows != receipt["rows"] or list(parsed["notes"]) != list(receipt["notes"]):
            raise ValueError("original response does not match the receipt")
        stored = _canonical_series(pd.read_parquet(BytesIO(artifact)))
        _require_coverage(rows, stored, "stored")
        return {"status": "ready", "series": stored, "receipt": receipt,
                "receipt_sha256": verified_receipt_sha}
    except Exception:
        return _failed_result(verified_receipt_sha)


def admit_boe_policy_field(materialized, evaluated_at, publication_decision,
                            observation_date=None):
    """A pure field projection under an independently supplied publisher decision.

    The decision must be the one owner's own decision, bound to the exact field
    and to the exact receipt digest this materialization was read from. No
    permission, clock or value is minted here.

    With no ``observation_date`` the field is the latest supplied native row
    and the existing ``engine.cb_desk`` daily observation-age rule applies. An
    explicit ``observation_date`` selects that exact native row and bypasses
    the current-age rule; it remains latest-vintage evidence, not originally
    known evidence, and the returned ``source_reference`` says so in its
    ``vintage=latest_retrieval`` and ``endpoint=`` markers.
    """
    blank = {"quality": "unknown", "reason": "disclosure_unknown", "metadata": "unknown",
             "value_permission": "unknown", "value": None, "unit": None, "instrument": None,
             "period": None, "observation_at": None, "calculation_at": None,
             "source_reference": None, "evidence_key": None}
    if type(materialized) is not dict:
        return blank
    status = materialized.get("status")
    if status != "ready" and not materialized.get("receipt_sha256"):
        return {**blank, "quality": "missing" if status == "missing" else "failed",
                "reason": "not_supplied" if status == "missing" else "source_failed"}

    metadata, permission = "unknown", "unknown"
    try:
        decision = publication_decision
        if type(decision) is not dict or set(decision) != {"owner_ref", "policy_ref",
                                                            "decision_ref", "metadata",
                                                            "value_permission", "binding"}:
            return blank
        if (decision["owner_ref"] != OWNER_REF
                or decision["policy_ref"] != POLICY_REF
                or type(decision["decision_ref"]) is not str
                or not decision["decision_ref"].strip()
                or decision["binding"] != {"field": FIELD,
                                           "receipt_sha256": materialized["receipt_sha256"]}):
            return blank
        candidate_metadata, candidate_permission = decision["metadata"], decision["value_permission"]
        if (type(candidate_metadata) is not str or type(candidate_permission) is not str
                or candidate_metadata not in _PERMISSIONS
                or candidate_permission not in _PERMISSIONS):
            return blank
        metadata, permission = candidate_metadata, candidate_permission
        if metadata != "allowed":
            return {**blank, "quality": "denied" if metadata == "denied" else "unknown",
                    "reason": "metadata_denied" if metadata == "denied" else "disclosure_unknown",
                    "metadata": metadata, "value_permission": permission}
        if materialized.get("status") != "ready":
            raise ValueError("source failure after verified capture")
        receipt = materialized["receipt"]
        if type(receipt) is not dict:
            raise ValueError("invalid receipt")
        _require_receipt(receipt)
        if _sha(_json(receipt)) != materialized["receipt_sha256"]:
            raise ValueError("materialized receipt changed after read")
        rows = receipt["rows"]
        if type(rows) is not list or not rows:
            raise ValueError("invalid source rows")
        _require_window(rows, receipt["source_url"])
        evaluated = _utc(evaluated_at)
        if _utc(receipt["committed_at"]) > evaluated:
            raise ValueError("committed after the evaluation clock")
        # Select the exact native row. No nearest match, no fill, no
        # substitution and no older cached value may stand in for it.
        if observation_date is None:
            selected = max(rows, key=lambda row: row["date"])
            mode = "current_latest"
        else:
            if type(observation_date) is not str:
                raise ValueError("invalid observation date")
            matches = [row for row in rows if row["date"] == observation_date]
            if len(matches) != 1:
                raise ValueError("observation date not supplied by the source")
            selected = matches[0]
            mode = "historical_exact"
        row_status = selected["status"]
        value = selected["value"]
        if row_status == _STATUS_WITHHELD:
            if value is not None:
                raise ValueError("withheld source row carries a value")
            # The provider withheld this observation. It stays unavailable even
            # when the cache still holds an older value for that date.
            return {**blank, "quality": "denied" if permission == "denied" else "unknown",
                    "reason": "value_denied" if permission == "denied" else "disclosure_unknown",
                    "metadata": metadata, "value_permission": permission,
                    "unit": UNIT, "instrument": dict(_INSTRUMENT),
                    "observation_at": selected["date"], "source_reference":
                        _source_reference(materialized, mode),
                    "evidence_key": _evidence_key(materialized, selected, mode)}
        if row_status != _STATUS_OBSERVED or type(value) not in {int, float}:
            raise ValueError("invalid source row")
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError("nonfinite source value")
        observation = datetime.fromisoformat(selected["date"]).date()
        if observation > evaluated.date():
            raise ValueError("future observation")
        _require_stored_agreement(materialized, selected, numeric)
        stale = False
        if mode == "current_latest":
            from engine.cb_desk import _STALE_DAYS

            age = (evaluated.date() - observation).days
            stale = age > _STALE_DAYS["daily"]
        out = {**blank, "quality": "stale" if stale else "qualified",
               "reason": "source_stale" if stale else None,
               "metadata": metadata, "value_permission": permission,
               "unit": UNIT, "instrument": dict(_INSTRUMENT), "period": None,
               "observation_at": selected["date"], "calculation_at": None,
               "source_reference": _source_reference(materialized, mode),
               "evidence_key": _evidence_key(materialized, selected, mode)}
        if permission == "allowed":
            out["value"] = numeric
        else:
            out.update(quality="denied" if permission == "denied" else "unknown",
                       reason="value_denied" if permission == "denied" else "disclosure_unknown")
        return out
    except (KeyError, TypeError, ValueError, OverflowError):
        if metadata == "allowed" and permission != "allowed":
            return {**blank, "quality": "denied" if permission == "denied" else "unknown",
                    "reason": "value_denied" if permission == "denied" else "disclosure_unknown",
                    "metadata": metadata, "value_permission": permission}
        if metadata == "allowed":
            return {**blank, "quality": "failed", "reason": "source_failed",
                    "metadata": metadata, "value_permission": permission,
                    "unit": UNIT, "instrument": dict(_INSTRUMENT)}
        return {**blank, "quality": "failed", "reason": "source_failed"}


def _source_reference(materialized, mode) -> str:
    """Return the read-only source reference of the admitted endpoint."""
    receipt = materialized["receipt"]
    return ("%s#receipt=%s&artifact=%s&endpoint=%s&vintage=latest_retrieval"
            % (receipt["source_url"], materialized["receipt_sha256"],
               receipt["artifact_sha256"], mode))


def _evidence_key(materialized, selected, mode) -> str:
    """Return the digest binding the decision, the receipt and the endpoint."""
    payload = {
        "field": FIELD,
        "receipt_sha256": materialized["receipt_sha256"],
        "observation_at": selected["date"],
        "mode": mode,
        "value": selected["value"],
    }
    return "boe-bank-rate:" + _sha(_json(payload))


def _require_stored_agreement(materialized, selected, numeric) -> None:
    """Require the actual stored artifact to still carry the native row."""
    series = materialized.get("series")
    if series is None:
        raise ValueError("committed source series missing")
    if not isinstance(series, pd.Series):
        raise ValueError("invalid stored series")
    for stamp, value in series.items():
        if stamp.date().isoformat() != selected["date"]:
            continue
        if value is None or pd.isna(value):
            raise ValueError("stored row does not carry the native observation")
        if float(value) != numeric:
            raise ValueError("stored row does not match the native observation")
        return
    raise ValueError("stored row does not carry the native observation")
