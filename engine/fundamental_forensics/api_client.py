"""Thin stdlib client for the governed financial query HTTP surface.

The default transport is :mod:`urllib.request`. Tests inject a FastAPI
``TestClient`` adapter and never open sockets. Every emitted number is a
:class:`~decimal.Decimal` of source decimal text; this module does not
originate a signal, score, rank, or finding.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from .query_service import MAX_METRIC_IDS, MAX_PERIODS, MAX_REQUEST_BYTES

Transport = Callable[
    [str, str, Mapping[str, str], bytes, float],
    tuple[int, Mapping[str, str], bytes],
]

_JSON_PATH = "/api/forensics/v1/financial/query"
_EXPORT_PATHS = {
    "csv": "/api/forensics/v1/financial/query.csv",
    "parquet": "/api/forensics/v1/financial/query.parquet",
    "xlsx": "/api/forensics/v1/financial/query.xlsx",
}


class FinancialQueryClientError(Exception):
    """Admission or transport refusal. ``status_code`` is 0 for client-side checks."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(status_code={self.status_code!r}, "
            f"detail={self.detail!r})"
        )


class FinancialQueryIntegrityError(FinancialQueryClientError):
    """Response digest missing or not equal to sha256 of the raw body."""

    def __init__(self, detail: str = "response digest mismatch") -> None:
        super().__init__(0, detail)


@dataclass(frozen=True)
class QueryResponse:
    body: bytes
    sha256: str
    envelope: dict

    def cell_values(self) -> list[tuple[dict, Decimal | None]]:
        receipt = self.envelope.get("receipt") if isinstance(self.envelope, dict) else None
        nodes = receipt.get("nodes") if isinstance(receipt, dict) else None
        if not isinstance(nodes, list):
            return []
        values: list[tuple[dict, Decimal | None]] = []
        for cell in nodes:
            if not isinstance(cell, dict):
                continue
            raw = cell.get("value")
            parsed: Decimal | None
            if isinstance(raw, str):
                try:
                    parsed = Decimal(raw)
                except InvalidOperation:
                    raise FinancialQueryClientError(0, "malformed response") from None
            else:
                parsed = None
            values.append((cell, parsed))
        return values


@dataclass(frozen=True)
class ExportResponse:
    fmt: str
    media_type: str
    payload: bytes
    sha256: str
    receipt_sha256: str
    filename: str


def _refuse_binary_floats(value: Any) -> None:
    if isinstance(value, float):
        raise FinancialQueryClientError(0, "malformed request")
    if isinstance(value, Mapping) and not isinstance(value, (str, bytes, bytearray)):
        for item in value.values():
            _refuse_binary_floats(item)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _refuse_binary_floats(item)


def _sequence_len(value: Any) -> int | None:
    if isinstance(value, (str, bytes, bytearray, Mapping)):
        return None
    if isinstance(value, Sequence):
        return len(value)
    return None


def encode_query_request(request: Mapping[str, Any]) -> bytes:
    """Canonical JSON request bytes. Refuses floats and oversize inputs."""
    if not isinstance(request, Mapping) or isinstance(request, (str, bytes, bytearray)):
        raise FinancialQueryClientError(0, "malformed request")
    _refuse_binary_floats(request)
    metric_count = _sequence_len(request.get("metric_ids"))
    if metric_count is not None and metric_count > MAX_METRIC_IDS:
        raise FinancialQueryClientError(0, "request exceeds transport bound")
    period_count = _sequence_len(request.get("periods"))
    if period_count is not None and period_count > MAX_PERIODS:
        raise FinancialQueryClientError(0, "request exceeds transport bound")
    try:
        encoded = json.dumps(
            request,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise FinancialQueryClientError(0, "malformed request") from exc
    if len(encoded) > MAX_REQUEST_BYTES:
        raise FinancialQueryClientError(0, "request body exceeds bound")
    return encoded


def _header(headers: Mapping[str, str], name: str) -> str | None:
    want = name.casefold()
    for key, value in headers.items():
        if str(key).casefold() == want:
            return str(value)
    return None


def _reject_json_constant(value: str) -> None:
    raise FinancialQueryClientError(0, "malformed request")


def _parse_json_object(payload: bytes) -> dict[str, Any] | None:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return None
    try:
        parsed = json.loads(text, parse_constant=_reject_json_constant)
    except FinancialQueryClientError:
        raise
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _error_detail(payload: bytes) -> str:
    parsed = _parse_json_object(payload)
    if parsed is None:
        return ""
    detail = parsed.get("detail")
    return detail if isinstance(detail, str) else ""


def _disposition_filename(headers: Mapping[str, str]) -> str:
    disposition = _header(headers, "Content-Disposition") or ""
    marker = "filename="
    idx = disposition.lower().find(marker)
    if idx < 0:
        return ""
    value = disposition[idx + len(marker) :].strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return value.split(";", 1)[0].strip()


def _media_type(headers: Mapping[str, str]) -> str:
    raw = _header(headers, "Content-Type") or ""
    return raw.split(";", 1)[0].strip()


def _default_transport(
    method: str,
    url: str,
    headers: Mapping[str, str],
    body: bytes,
    timeout: float,
) -> tuple[int, Mapping[str, str], bytes]:
    import urllib.error
    import urllib.request

    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={str(key): str(value) for key, value in headers.items()},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw_headers = {str(key): str(value) for key, value in response.headers.items()}
            return int(response.status), raw_headers, response.read()
    except urllib.error.HTTPError as exc:
        raw_headers = (
            {str(key): str(value) for key, value in exc.headers.items()}
            if exc.headers is not None
            else {}
        )
        return int(exc.code), raw_headers, exc.read()


class FinancialQueryClient:
    """POST the JSON/CSV/Parquet/XLSX query routes and check the response digest."""

    def __init__(
        self,
        base_url: str,
        *,
        bearer_token: str | None = None,
        transport: Transport | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = str(base_url).rstrip("/") + "/"
        self._bearer_token = bearer_token
        self._transport = transport or _default_transport
        self._timeout = float(timeout)

    def __repr__(self) -> str:
        return (
            f"FinancialQueryClient(base_url={self._base_url.rstrip('/')!r}, "
            f"timeout={self._timeout!r})"
        )

    def query(self, request: Mapping[str, Any]) -> QueryResponse:
        payload = encode_query_request(request)
        status, headers, body = self._send("POST", _JSON_PATH, payload)
        self._raise_http_error(status, body)
        digest = self._checked_digest(headers, body)
        envelope = _parse_json_object(body)
        if envelope is None:
            raise FinancialQueryClientError(0, "malformed request")
        return QueryResponse(body=body, sha256=digest, envelope=envelope)

    def export(self, request: Mapping[str, Any], fmt: str) -> ExportResponse:
        normalized = str(fmt).lower()
        path = _EXPORT_PATHS.get(normalized)
        if path is None:
            raise FinancialQueryClientError(0, "unsupported export format")
        encoded = encode_query_request(request)
        status, headers, body = self._send("POST", path, encoded)
        self._raise_http_error(status, body)
        digest = self._checked_digest(headers, body)
        receipt = _header(headers, "X-FIF-Receipt-SHA256") or ""
        return ExportResponse(
            fmt=normalized,
            media_type=_media_type(headers),
            payload=body,
            sha256=digest,
            receipt_sha256=receipt.strip(),
            filename=_disposition_filename(headers),
        )

    def sidecar(self, request: Mapping[str, Any], export: ExportResponse) -> QueryResponse:
        """Fetch the JSON lineage sidecar of an export and bind it to the export.

        The JSON route is the lineage sidecar of every export: binding means
        the export's ``X-FIF-Receipt-SHA256`` equals the JSON response's
        ``X-FIF-Response-SHA256`` for the same canonical request bytes. CSV
        additionally checks every data row's ``query_hash`` column against
        the sidecar receipt's ``query_hash``; Parquet and XLSX are bound by
        header only.
        """
        if not export.receipt_sha256:
            raise FinancialQueryIntegrityError("export carries no receipt digest")
        query_response = self.query(request)
        if query_response.sha256 != export.receipt_sha256:
            raise FinancialQueryIntegrityError("sidecar receipt digest mismatch")
        if export.fmt == "csv":
            expected = self._receipt_query_hash(query_response)
            rows = csv.DictReader(io.StringIO(export.payload.decode("utf-8")))
            for row in rows:
                if row.get("query_hash") != expected:
                    raise FinancialQueryIntegrityError("sidecar query_hash mismatch")
        return query_response

    def export_with_sidecar(
        self,
        request: Mapping[str, Any],
        fmt: str,
    ) -> tuple[ExportResponse, QueryResponse]:
        """Export, then bind it to its JSON lineage sidecar.

        The JSON route is the lineage sidecar of every export: binding means
        the export's ``X-FIF-Receipt-SHA256`` equals the JSON response's
        ``X-FIF-Response-SHA256`` for the same canonical request bytes.
        Returns ``(export, sidecar)`` on success; raises
        :class:`FinancialQueryIntegrityError` on any binding failure.
        """
        exported = self.export(request, fmt)
        return exported, self.sidecar(request, exported)

    def _receipt_query_hash(self, query_response: QueryResponse) -> Any:
        receipt = query_response.envelope.get("receipt")
        if not isinstance(receipt, dict):
            raise FinancialQueryIntegrityError("sidecar receipt digest mismatch")
        return receipt.get("query_hash")

    def _send(
        self,
        method: str,
        path: str,
        body: bytes,
    ) -> tuple[int, Mapping[str, str], bytes]:
        url = f"{self._base_url.rstrip('/')}{path}"
        headers = {"Content-Type": "application/json"}
        token = self._bearer_token
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            status, response_headers, payload = self._transport(
                method, url, headers, body, self._timeout
            )
        except FinancialQueryClientError:
            raise
        except Exception:
            raise FinancialQueryClientError(0, "transport failure") from None
        return int(status), response_headers, payload

    def _raise_http_error(self, status: int, payload: bytes) -> None:
        if 200 <= status < 300:
            return
        raise FinancialQueryClientError(status, _error_detail(payload))

    def _checked_digest(self, headers: Mapping[str, str], payload: bytes) -> str:
        computed = hashlib.sha256(payload).hexdigest()
        advertised = _header(headers, "X-FIF-Response-SHA256")
        if advertised is None or not str(advertised).strip():
            raise FinancialQueryIntegrityError("missing X-FIF-Response-SHA256")
        advertised_digest = str(advertised).strip().lower()
        if advertised_digest != computed:
            raise FinancialQueryIntegrityError("response digest mismatch")
        return advertised_digest
