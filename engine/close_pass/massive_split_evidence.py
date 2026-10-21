"""Opt-in CorpActions observations, persisted by the existing source kernel.

No default collector, price reconstruction, applicability or basis admission. The
private transport seam is patchable by synthetic tests; production clocks/IDs
are never supplied by callers. Response hashes describe observed bytes only.
"""
from __future__ import annotations

import copy
import fcntl
import http.client
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from engine.neuralweb import market_memory as _mm
from engine.neuralweb import market_memory_source_kernel as K

ENDPOINT = "https://api.massive.com/stocks/v1/splits"
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_PAGES = 8
PAGE_LIMIT = 1000
MAX_ROWS = 4096
SOURCE_ID = "massive_rest:stocks:split_history"
SCHEMA = "market_memory.source.massive_split_history.v1"
FAMILY = K.SourceFamily(
    SOURCE_ID, SCHEMA,
    "market_memory.source_artifact_receipt.massive_split_history.v1",
    "market_memory.source_generation.massive_split_history.v1",
    "market_memory.source_head.massive_split_history.v1",
    "market_memory.source_store.massive_split_history.v1",
    "market_memory.source_capture.massive_split_history.v1",
)
AUTHORITY = dict(_mm.AUTHORITY)
ROOT_LEAF = "sources-massive-split-history-v1"
_NAME = re.compile(r"[A-Za-z0-9_.:/-]{1,128}\Z")
_TICKER = re.compile(r"[A-Za-z0-9.^_/-]{1,32}\Z")
_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z")
_SHA = re.compile(r"[a-f0-9]{64}\Z")
_KINDS = {"transport", "http_framing", "http_status", "redirect", "response_capacity", "malformed_json",
          "response_status", "results_missing", "response_identity", "malformed_row",
          "duplicate_id", "row_capacity", "pagination", "repeated_cursor", "page_capacity"}
_CLASSIFICATIONS = {"forward_split", "reverse_split", "stock_dividend"}


class SplitEvidenceError(K.SourceIntakeError):
    """Fixed diagnostic only; no provider body/error string is exposed."""


class _Number(str):
    """An original JSON numeric token, before any float conversion."""


def _fail(reason):
    raise SplitEvidenceError(reason)


def _date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        _fail("invalid_date")
    try:
        date.fromisoformat(value)
    except ValueError:
        _fail("invalid_date")
    return value


def _request(ticker, earliest_bar_et_date, basis_date):
    if not isinstance(ticker, str) or not _TICKER.fullmatch(ticker):
        _fail("invalid_ticker")
    earliest = _date(earliest_bar_et_date)
    basis = _date(basis_date)
    if earliest > basis:
        _fail("invalid_date_range")
    return {"endpoint": ENDPOINT, "ticker": ticker, "execution_date.gte": earliest,
            "sort": "execution_date.asc", "limit": PAGE_LIMIT, "basis_date": basis}


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("malformed_json")
        result[key] = value
    return result


def _constant(_value):
    _fail("malformed_json")


def _parse(body):
    try:
        value = json.loads(body.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_int=_Number, parse_float=_Number, parse_constant=_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        _fail("malformed_json")
    if not isinstance(value, dict):
        _fail("malformed_json")
    return value


def _decimal(value, *, wire=False):
    if (type(value) is not (_Number if wire else str) or len(value) > 128
            or not _DECIMAL.fullmatch(value)):
        _fail("malformed_row")
    try:
        number = Decimal(value)
    except InvalidOperation:
        _fail("malformed_row")
    if not number.is_finite() or number <= 0:
        _fail("malformed_row")
    return str(value)


def _row(value, request, page_index, row_index, *, wire=True):
    if not isinstance(value, dict):
        _fail("malformed_row")
    event_id = value.get("id")
    if type(event_id) is not str or not _NAME.fullmatch(event_id):
        _fail("malformed_row")
    if type(value.get("ticker")) is not str or value["ticker"] != request["ticker"]:
        _fail("response_identity")
    try:
        execution = _date(value.get("execution_date"))
    except SplitEvidenceError:
        _fail("malformed_row")
    if execution < request["execution_date.gte"]:
        _fail("response_identity")
    if type(value.get("adjustment_type")) is not str or value["adjustment_type"] not in _CLASSIFICATIONS:
        _fail("malformed_row")
    result = {"id": event_id, "ticker": request["ticker"], "execution_date": execution,
              "split_from": _decimal(value.get("split_from"), wire=wire),
              "split_to": _decimal(value.get("split_to"), wire=wire),
              "adjustment_type": value["adjustment_type"],
              "page_index": page_index, "row_index": row_index}
    if "historical_adjustment_factor" in value:
        result["historical_adjustment_factor"] = _decimal(value["historical_adjustment_factor"], wire=wire)
    return result


def _next_url(value, request):
    if not isinstance(value, str) or len(value) > 8192:
        _fail("pagination")
    try:
        url = urllib.parse.urlsplit(value)
        pairs = urllib.parse.parse_qsl(url.query, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        _fail("pagination")
    if (url.scheme != "https" or url.netloc != "api.massive.com"
            or url.path != "/stocks/v1/splits" or url.fragment):
        _fail("pagination")
    query = dict(pairs)
    if len(query) != len(pairs) or set(query) - {"ticker", "execution_date.gte", "sort", "limit", "cursor", "apiKey"}:
        _fail("pagination")
    for key in ("ticker", "execution_date.gte", "sort", "limit"):
        if key in query and query[key] != str(request[key]):
            _fail("pagination")
    cursor = query.get("cursor")
    if not isinstance(cursor, str) or not re.fullmatch(r"[A-Za-z0-9_=-]{1,4096}", cursor):
        _fail("pagination")
    # Never use a credential received in pagination. Only the owner's header is used.
    return ENDPOINT + "?" + urllib.parse.urlencode({"cursor": cursor}), sha256(cursor.encode("ascii")).hexdigest()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open_split_request(request):
    """Only production transport seam; tests patch this without provider access."""
    return urllib.request.build_opener(_NoRedirect()).open(request, timeout=30)


def _seal(value):
    value["acquisition_sha256"] = sha256(K._canonical_bytes({k: v for k, v in value.items() if k != "acquisition_sha256"})).hexdigest()
    return value


def acquire_split_history(ticker: str, earliest_bar_et_date: str, basis_date: str) -> dict:
    """Acquire one bounded observation. Explicit opt-in; never called by close-pass.

    Missing credentials refuse before transport. No retries silently collapse HTTP
    attempts. Return complete/partial/failed evidence; capacity of the kernel object
    is checked again at intake, and is never solved by dropping evidence.
    """
    request = _request(ticker, earliest_bar_et_date, basis_date)
    from engine.close_pass.massive_close import api_key
    key = api_key()
    if not key:
        _fail("missing_credentials")
    started = time.time_ns()
    result = {"schema": SCHEMA, "source_id": SOURCE_ID, "acquisition_id": uuid4().hex,
              "request": request, "started_utc_ns": started, "completed_utc_ns": None,
              "status": "failed", "failure_kind": None, "pages": [], "rows": [],
              "basis_eligible": False, "authority": dict(AUTHORITY)}
    query = {k: request[k] for k in ("ticker", "execution_date.gte", "sort", "limit")}
    url = ENDPOINT + "?" + urllib.parse.urlencode(query)
    cursor_hash = None
    seen_cursors, seen_ids = set(), set()
    for page_index in range(MAX_PAGES):
        page = {"page_index": page_index, "cursor_sha256": cursor_hash,
                "request_started_utc_ns": time.time_ns(), "response_completed_utc_ns": None,
                "http_status": None, "observed_body_sha256": None, "body_bytes_observed": 0,
                "body_complete": False, "rows_received": None, "rows_retained": 0,
                "outcome": "transport"}
        result["pages"].append(page)
        response = None
        body = bytearray()
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json", "Authorization": "Bearer " + key})
            try:
                response = _open_split_request(req)
            except urllib.error.HTTPError as exc:
                response = exc
            page["http_status"] = response.code
            while len(body) <= MAX_RESPONSE_BYTES:
                chunk = response.read(min(65536, MAX_RESPONSE_BYTES + 1 - len(body)))
                if not chunk:
                    # HTTPResponse.read(amt) permits premature Content-Length EOF
                    # without raising. A valid JSON prefix is not a complete body.
                    if getattr(response, "length", None) not in (None, 0):
                        page["outcome"] = "http_framing"
                    else:
                        page["body_complete"] = True
                    break
                body.extend(chunk)
        except http.client.IncompleteRead as exc:
            # Only decoded body bytes exposed by the response parser are observed.
            # It may have consumed further framing/bytes which it did not return.
            if response is not None:
                body.extend(exc.partial[:MAX_RESPONSE_BYTES + 1 - len(body)])
            page["outcome"] = "http_framing"
        except http.client.HTTPException:
            page["outcome"] = "http_framing"
        except (urllib.error.URLError, TimeoutError, OSError):
            page["outcome"] = "transport"
        else:
            if page["outcome"] == "http_framing":
                pass
            elif len(body) > MAX_RESPONSE_BYTES:
                page["outcome"] = "response_capacity"
            elif 300 <= page["http_status"] < 400:
                page["outcome"] = "redirect"
            elif page["http_status"] != 200:
                page["outcome"] = "http_status"
            else:
                page["outcome"] = "ok"
        finally:
            if response is not None:
                try:
                    response.close()
                except http.client.HTTPException:
                    page["outcome"] = "http_framing"
                    page["body_complete"] = False
                except OSError:
                    page["outcome"] = "transport"
                    page["body_complete"] = False
            page["response_completed_utc_ns"] = time.time_ns()
            if response is not None:
                page["observed_body_sha256"] = sha256(body).hexdigest()
                page["body_bytes_observed"] = len(body)
        if page["outcome"] != "ok":
            result["failure_kind"] = page["outcome"]
            break
        try:
            payload = _parse(body)
            if payload.get("status") != "OK":
                _fail("response_status")
            if "ticker" in payload and (type(payload["ticker"]) is not str or payload["ticker"] != ticker):
                _fail("response_identity")
            values = payload.get("results")
            if not isinstance(values, list):
                _fail("results_missing")
            page["rows_received"] = len(values)
            for row_index, value in enumerate(values):
                if len(result["rows"]) >= MAX_ROWS:
                    _fail("row_capacity")
                row = _row(value, request, page_index, row_index)
                if row["id"] in seen_ids:
                    _fail("duplicate_id")
                if result["rows"] and row["execution_date"] < result["rows"][-1]["execution_date"]:
                    _fail("malformed_row")
                seen_ids.add(row["id"])
                result["rows"].append(row)
                page["rows_retained"] += 1
            if "next_url" not in payload:
                result["status"] = "complete"
                break
            url, cursor_hash = _next_url(payload["next_url"], request)
            if cursor_hash in seen_cursors:
                _fail("repeated_cursor")
            seen_cursors.add(cursor_hash)
            if page_index == MAX_PAGES - 1:
                _fail("page_capacity")
        except SplitEvidenceError as exc:
            page["outcome"] = str(exc)
            result["failure_kind"] = str(exc)
            break
    result["completed_utc_ns"] = time.time_ns()
    if result["status"] != "complete":
        result["status"] = "partial" if result["rows"] else "failed"
    return _seal(result)


def _ns(value):
    if type(value) is not int or value <= 0:
        _fail("invalid_clock")
    return value


def _validate_acquisition(value):
    fields = {"schema", "source_id", "acquisition_id", "request", "started_utc_ns", "completed_utc_ns", "status", "failure_kind", "pages", "rows", "basis_eligible", "authority", "acquisition_sha256"}
    if not isinstance(value, dict) or set(value) != fields:
        _fail("invalid_acquisition")
    clean = copy.deepcopy(value)
    if clean["schema"] != SCHEMA or clean["source_id"] != SOURCE_ID or clean["basis_eligible"] is not False or clean["authority"] != AUTHORITY:
        _fail("invalid_acquisition")
    if type(clean["acquisition_id"]) is not str or not re.fullmatch(r"[a-f0-9]{32}", clean["acquisition_id"]):
        _fail("invalid_acquisition")
    req = clean["request"]
    if not isinstance(req, dict) or req != _request(req.get("ticker"), req.get("execution_date.gte"), req.get("basis_date")):
        _fail("invalid_request")
    start, end = _ns(clean["started_utc_ns"]), _ns(clean["completed_utc_ns"])
    pages, rows = clean["pages"], clean["rows"]
    if start > end or not isinstance(pages, list) or not 1 <= len(pages) <= MAX_PAGES or not isinstance(rows, list) or len(rows) > MAX_ROWS:
        _fail("invalid_acquisition")
    last, cursor_hashes = start, set()
    for i, page in enumerate(pages):
        expected = {"page_index", "cursor_sha256", "request_started_utc_ns", "response_completed_utc_ns", "http_status", "observed_body_sha256", "body_bytes_observed", "body_complete", "rows_received", "rows_retained", "outcome"}
        if not isinstance(page, dict) or set(page) != expected or type(page["page_index"]) is not int or page["page_index"] != i:
            _fail("invalid_page")
        begin, done = _ns(page["request_started_utc_ns"]), _ns(page["response_completed_utc_ns"])
        if not last <= begin <= done <= end:
            _fail("invalid_clock")
        last = done
        cursor = page["cursor_sha256"]
        if (i == 0 and cursor is not None) or (i > 0 and (not isinstance(cursor, str) or not _SHA.fullmatch(cursor) or cursor in cursor_hashes)):
            _fail("invalid_page")
        cursor_hashes.add(cursor)
        status, digest, count = page["http_status"], page["observed_body_sha256"], page["body_bytes_observed"]
        if type(count) is not int or not 0 <= count <= MAX_RESPONSE_BYTES + 1 or type(page["body_complete"]) is not bool:
            _fail("invalid_page")
        if status is None:
            if digest is not None or count or page["body_complete"] or page["outcome"] not in ("transport", "http_framing"):
                _fail("invalid_page")
        elif type(status) is not int or not 100 <= status <= 599 or not isinstance(digest, str) or not _SHA.fullmatch(digest):
            _fail("invalid_page")
        if type(page["outcome"]) is not str or page["outcome"] not in _KINDS | {"ok"} or (i < len(pages)-1 and page["outcome"] != "ok"):
            _fail("invalid_page")
        received, retained = page["rows_received"], page["rows_retained"]
        if type(retained) is not int or retained < 0 or (received is not None and (type(received) is not int or received < retained)):
            _fail("invalid_page")
        if received is None and retained:
            _fail("invalid_page")
        if page["outcome"] == "ok" and (status != 200 or not page["body_complete"] or count > MAX_RESPONSE_BYTES or received is None or received != retained):
            _fail("invalid_page")
    ids, previous, previous_date, per_page = set(), None, None, [0] * len(pages)
    for row in rows:
        if not isinstance(row, dict) or type(row.get("page_index")) is not int or type(row.get("row_index")) is not int:
            _fail("malformed_row")
        pi, ri = row["page_index"], row["row_index"]
        if not 0 <= pi < len(pages) or ri != per_page[pi] or (previous is not None and (pi, ri) <= previous):
            _fail("malformed_row")
        if row != _row(row, req, pi, ri, wire=False) or row["id"] in ids or (previous_date is not None and row["execution_date"] < previous_date):
            _fail("malformed_row")
        ids.add(row["id"])
        per_page[pi] += 1
        previous = (pi, ri)
        previous_date = row["execution_date"]
    if per_page != [p["rows_retained"] for p in pages]:
        _fail("invalid_page")
    failure = clean["failure_kind"]
    if failure is None:
        if clean["status"] != "complete" or pages[-1]["outcome"] != "ok":
            _fail("invalid_acquisition")
    elif type(failure) is not str or failure not in _KINDS or pages[-1]["outcome"] != failure or clean["status"] != ("partial" if rows else "failed"):
        _fail("invalid_acquisition")
    if clean["acquisition_sha256"] != _seal(copy.deepcopy(clean))["acquisition_sha256"]:
        _fail("acquisition_seal_mismatch")
    if len(K._canonical_bytes(clean)) > K._MAX_OBJECT_BYTES:
        _fail("object_capacity")
    return clean


def _root(value):
    root = K.validate_source_store_root(value)
    if root.name != ROOT_LEAF:
        raise K.SourceStoreError("split evidence requires its dedicated private family leaf")
    return root


def _capture_id(artifact):
    return "mmscapture_" + sha256(K._canonical_bytes({"source_id": SOURCE_ID, "acquisition_id": artifact["acquisition_id"]})).hexdigest()


def _validate_receipt(value, store_id):
    clean = K._validate_receipt_minimal(value, store_id=store_id, family=FAMILY)
    fields = {"schema", "store_id", "receipt_id", "capture_id", "source_id", "source_schema", "vintage_id", "revision_id", "artifact_sha256", "object_key", "owner_intake_started_utc_ns", "owner_receipt_assembled_utc_ns", "basis_eligible", "authority"}
    if set(clean) != fields or clean["source_id"] != SOURCE_ID or clean["source_schema"] != SCHEMA or clean["basis_eligible"] is not False or clean["authority"] != AUTHORITY:
        raise K.SourceStoreError("split evidence receipt contract mismatch")
    if _ns(clean["owner_intake_started_utc_ns"]) > _ns(clean["owner_receipt_assembled_utc_ns"]):
        raise K.SourceStoreError("split evidence intake clock mismatch")
    if clean["object_key"] != f'source_objects/{clean["artifact_sha256"][:2]}/{clean["artifact_sha256"]}.json':
        raise K.SourceStoreError("split evidence object key mismatch")
    return clean


def _read_artifact(root, receipt):
    value, body = K._read_store_object(K._object_path(root, receipt["artifact_sha256"]), limit=K._MAX_OBJECT_BYTES, label="split evidence object")
    if sha256(body).hexdigest() != receipt["artifact_sha256"]:
        raise K.SourceStoreError("split evidence object hash mismatch")
    artifact = _validate_acquisition(value)
    vintage = "mmsvintage_" + sha256(K._canonical_bytes(artifact["request"])).hexdigest()
    revision = "mmsrevision_" + sha256(K._canonical_bytes({"vintage_id": vintage, "artifact_sha256": receipt["artifact_sha256"]})).hexdigest()
    if (receipt["capture_id"] != _capture_id(artifact) or receipt["vintage_id"] != vintage or receipt["revision_id"] != revision or artifact["completed_utc_ns"] > receipt["owner_intake_started_utc_ns"]):
        raise K.SourceStoreError("split evidence receipt does not bind acquisition")
    return artifact, body


def intake_split_acquisition(acquisition: dict, *, store_root: str | Path) -> K.StoredSourceArtifact:
    """Persist an exact acquired attempt; same identity/payload replay is idempotent.

    Receipt assembly is before durable HEAD publication, never a publication clock.
    An unpublished orphan receipt is reusable after a failed HEAD write, but remains
    unreadable through pinned generations until successful publication.
    """
    intake_started = time.time_ns()
    artifact = _validate_acquisition(acquisition)
    if artifact["completed_utc_ns"] > intake_started:
        _fail("future_acquisition")
    body = K._canonical_bytes(artifact)
    digest = sha256(body).hexdigest()
    capture = _capture_id(artifact)
    root = _root(store_root)
    K._mkdir_durable(root)
    fd = os.open(K._safe_path(root, ".writer.lock"), os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        state = K._ensure_store(root, FAMILY, AUTHORITY)
        existing = K._find_entry(state.generation, capture_id=capture)
        receipt = None
        capture_path = K._capture_path(root, capture)
        if existing is not None:
            receipt, _ = K._read_receipt_copies_by_validate(root, existing, store_id=state.manifest["store_id"], validate_fn=_validate_receipt)
        elif capture_path.exists():
            orphan, _ = K._read_store_object(capture_path, limit=K._MAX_RECEIPT_BYTES, label="unpublished split receipt")
            receipt = _validate_receipt(orphan, state.manifest["store_id"])
        if receipt is not None:
            old, old_body = _read_artifact(root, receipt)
            if old_body != body:
                _fail("acquisition_id_conflict")
            if existing is not None:
                return K.StoredSourceArtifact(old, receipt, state.generation["generation_id"], False)
        if len(state.generation["receipts"]) >= K._MAX_GENERATION_RECEIPTS:
            _fail("generation_capacity")
        if receipt is None:
            vintage = "mmsvintage_" + sha256(K._canonical_bytes(artifact["request"])).hexdigest()
            receipt = {"schema": FAMILY.receipt_schema, "store_id": state.manifest["store_id"], "receipt_id": "", "capture_id": capture, "source_id": SOURCE_ID, "source_schema": SCHEMA,
                       "vintage_id": vintage, "revision_id": "mmsrevision_" + sha256(K._canonical_bytes({"vintage_id": vintage, "artifact_sha256": digest})).hexdigest(),
                       "artifact_sha256": digest, "object_key": f"source_objects/{digest[:2]}/{digest}.json",
                       "owner_intake_started_utc_ns": intake_started, "owner_receipt_assembled_utc_ns": time.time_ns(),
                       "basis_eligible": False, "authority": dict(AUTHORITY)}
            receipt["receipt_id"] = K._content_id("mmsrc_", receipt, field="receipt_id")
        _validate_receipt(receipt, state.manifest["store_id"])
        receipt_body = K._canonical_bytes(receipt)
        if len(receipt_body) > K._MAX_RECEIPT_BYTES:
            _fail("receipt_capacity")
        generation = K._new_generation(store_id=state.manifest["store_id"], previous_generation_id=state.generation["generation_id"], receipts=state.generation["receipts"] + [K._entry(receipt)], family=FAMILY)
        generation_body = K._canonical_bytes(generation)
        if len(generation_body) > K._MAX_GENERATION_BYTES:
            _fail("generation_capacity")
        # All prospective capacity checks precede immutable data writes and HEAD.
        K._write_create_once(root, K._object_path(root, digest), body, label="split evidence object")
        K._write_create_once(root, capture_path, receipt_body, label="split evidence capture")
        K._write_create_once(root, K._receipt_path(root, receipt["receipt_id"]), receipt_body, label="split evidence receipt")
        K._write_create_once(root, K._generation_path(root, generation["generation_id"]), generation_body, label="split evidence generation")
        K._replace_head(root, K._new_head(generation, generation_body, FAMILY))
        return K.StoredSourceArtifact(artifact, receipt, generation["generation_id"], True)
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def retain_split_history(ticker: str, earliest_bar_et_date: str, basis_date: str, *, store_root: str | Path) -> K.StoredSourceArtifact:
    """Explicit CorpActions acquisition → kernel persistence entry point."""
    _root(store_root)  # Refuse an unsafe destination before requesting any data.
    return intake_split_acquisition(acquire_split_history(ticker, earliest_bar_et_date, basis_date), store_root=store_root)


@dataclass(frozen=True)
class SplitEvidenceSnapshot:
    artifact: dict
    owner_receipt: dict
    read_receipt: dict


class SplitEvidenceReader(K.GenericSourceArtifactReader):
    """Pins kernel generation; each actual read adds its own precise custody."""
    def __init__(self, store_root, *, generation_id=None):
        super().__init__(_root(store_root), FAMILY, AUTHORITY, generation_id=generation_id, validate_receipt_fn=_validate_receipt)

    def read(self, receipt_id: str) -> SplitEvidenceSnapshot:
        started = time.time_ns()
        receipt = self.read_receipt(receipt_id)
        artifact, body = _read_artifact(self._root, receipt)
        completed = time.time_ns()
        if started > completed or receipt["owner_receipt_assembled_utc_ns"] > completed:
            raise K.SourceStoreError("split evidence read clock regression")
        read = {"schema": "market_memory.source_read.massive_split_history.v1", "reader_id": "CorpActions.SplitEvidenceReader", "store_id": receipt["store_id"], "generation_id": self.pinned_generation_id,
                "receipt_id": receipt_id, "receipt_sha256": sha256(K._canonical_bytes(receipt)).hexdigest(),
                "artifact_sha256": sha256(body).hexdigest(), "artifact_bytes": len(body),
                "read_started_utc_ns": started, "read_completed_utc_ns": completed, "basis_eligible": False}
        read["read_receipt_sha256"] = sha256(K._canonical_bytes(read)).hexdigest()
        return SplitEvidenceSnapshot(artifact, receipt, read)
