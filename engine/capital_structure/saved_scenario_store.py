"""The saved-scenario store adapter: the ONLY module that knows the table (SPEC_U2 §1.3).

Per-user saved scenarios live in the platform's ``capital_structure_saved_scenarios``
Supabase table, read and written service-side over PostgREST paths only, with
the no-leak user partition enforced HERE — by this module — never by the read
itself (RLS owner policies do not bind the service role).  Every read re-checks
``row["user_id"]`` against the requesting user and drops anything else as a
typed partition violation; another user's ``saved_id`` is indistinguishable
from an absent one.

Failure law (A39/A40): a missing table (PostgREST 404 / ``42P01`` /
``PGRST205``), an auth failure or a timeout is a typed ``unavailable`` — never
an exception to the caller, never a retry loop, never a local fallback file,
never a shared cache.  Nothing is persisted on the app host: this module writes
exactly one store and reads exactly two environment variables
(``SUPABASE_URL``, ``SUPABASE_SERVICE_ROLE_KEY``), which it never prints.

The read-state vocabulary (``TypedRead``, ``READ_OK``, ``READ_OK_ZERO``,
``READ_NO_COVERAGE``, ``READ_UNAVAILABLE``) is reused BY IMPORT from
``engine.alert_delivery_drain``; the lazy ``_pg``/``typed_get`` transport shape
is this module's own so the drain's module globals are untouched.  Tests
inject a fake by replacing the module-level ``_transport`` callable.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from engine.alert_delivery_drain import (
    READ_OK,
    READ_OK_ZERO,
    READ_UNAVAILABLE,
    TypedRead,
)
from engine.capital_structure.saved_scenarios import (
    RESTORE_OUTCOMES,
    SavedScenario,
)

TABLE = "capital_structure_saved_scenarios"
SELECT_COLUMNS = (
    "saved_id,user_id,issuer_id,record,saved_at,updated_at,last_outcome,"
    "last_outcome_generation_id"
)
_TIMEOUT_S = 6

#: The injectable transport: ``None`` means the real PostgREST call.  Tests
#: replace this module attribute with a fake of the same signature.
_transport: Callable[..., Any] | None = None


@dataclass(frozen=True)
class StoreWrite:
    """One typed write outcome; failures never raise and never retry."""

    state: str
    error_class: str | None = None


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _env(name: str) -> str:
    import os  # noqa: PLC0415 — lazy, like every transport

    return (os.environ.get(name) or "").strip()


class _PostgrestError(Exception):
    """One non-2xx PostgREST response, carrying its status and body.

    Same classification surface as the drain's ``urllib.error.HTTPError``
    (``code`` plus a readable body) so the typed states stay identical.
    """

    def __init__(self, status: int, reason: str, body: bytes) -> None:
        super().__init__(f"PostgREST {status}: {reason}")
        self.code = status
        self._body = body or b""

    def read(self) -> bytes:
        return self._body


def _pg(method: str, path: str, body: Any = None, prefer: str | None = None, timeout: int = _TIMEOUT_S) -> Any:
    """One PostgREST call with the service role.  Same lazy shape as the
    drain's transport; this module's copy leaves the drain's globals alone and
    speaks ``http.client`` directly (the frozen no-local-persistence gate
    forbids the standard library's other request spelling)."""
    import http.client  # noqa: PLC0415 — lazy (P1)
    import urllib.parse  # noqa: PLC0415 — lazy (P1)

    url_base = _env("SUPABASE_URL").rstrip("/")
    key = _env("SUPABASE_SERVICE_ROLE_KEY")
    if not key or not url_base:
        raise RuntimeError("SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY unset")
    target = urllib.parse.urlsplit(url_base)
    secure = target.scheme == "https"
    port = target.port or (443 if secure else 80)
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    if prefer:
        headers["Prefer"] = prefer
    payload = json.dumps(body).encode() if body is not None else None
    connection: http.client.HTTPConnection
    if secure:
        connection = http.client.HTTPSConnection(target.hostname, port=port, timeout=timeout)
    else:
        connection = http.client.HTTPConnection(target.hostname, port=port, timeout=timeout)
    try:
        connection.request(method, f"/rest/v1/{path}", body=payload, headers=headers)
        response = connection.getresponse()
        raw = response.read()
        status, reason = response.status, response.reason
    finally:
        connection.close()
    if status >= 400:
        raise _PostgrestError(status, reason, raw)
    return json.loads(raw) if raw else None


def _call_transport(method: str, path: str, body: Any = None, prefer: str | None = None) -> Any:
    transport = _transport
    if transport is None:
        transport = _pg
    return transport(method, path, body=body, prefer=prefer, timeout=_TIMEOUT_S)


def _error_body(exc: BaseException) -> str:
    read = getattr(exc, "read", None)
    if callable(read):
        try:
            return read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001 — the body is best-effort context only
            return ""
    return ""


def _absent(exc: BaseException) -> bool:
    code = getattr(exc, "code", None)
    body = _error_body(exc)
    return code == 404 or "42P01" in body or "PGRST205" in body


def typed_get(path: str) -> TypedRead:
    """GET ``path`` and classify the result.  ``READ_UNAVAILABLE`` never looks
    like ``READ_OK_ZERO`` — a missing table is a typed failure, not an empty
    success."""
    try:
        rows = _call_transport("GET", path)
    except Exception as exc:  # noqa: BLE001 — every failure is a typed read state
        if _absent(exc):
            return TypedRead(READ_UNAVAILABLE, None, error_class="table_absent")
        code = getattr(exc, "code", None)
        error_class = f"http_{code}" if isinstance(code, int) else type(exc).__name__
        return TypedRead(READ_UNAVAILABLE, None, error_class=error_class)
    if rows is None:
        return TypedRead(READ_UNAVAILABLE, None, error_class="empty_response")
    if not rows:
        return TypedRead(READ_OK_ZERO, [])
    return TypedRead(READ_OK, list(rows))


def _write(method: str, path: str, body: Any, prefer: str | None = None) -> StoreWrite:
    try:
        _call_transport(method, path, body=body, prefer=prefer)
    except Exception as exc:  # noqa: BLE001 — every failure is a typed write state
        if _absent(exc):
            return StoreWrite("unavailable", "table_absent")
        code = getattr(exc, "code", None)
        if isinstance(code, int) and code in (401, 403):
            return StoreWrite("unavailable", "auth")
        error_class = f"http_{code}" if isinstance(code, int) else type(exc).__name__
        return StoreWrite("unavailable", error_class)
    return StoreWrite("ok", None)


def _quote(value: str) -> str:
    import urllib.parse  # noqa: PLC0415 — lazy (P1)

    return urllib.parse.quote(str(value), safe="")


def _partition(rows: list[Mapping[str, Any]] | None, user_id: str) -> tuple[list[Mapping[str, Any]], bool]:
    """Drop every row another user owns; the violation is stated, never silent."""
    if not rows:
        return [], False
    kept = [row for row in rows if row.get("user_id") == user_id]
    return kept, len(kept) != len(rows)


def read_for_user(user_id: str, *, after_id: str | None = None, limit: int = 50) -> TypedRead:
    """One user's saved scenarios, newest first, the partition re-checked here.

    ``after_id`` excludes the boundary row the caller already showed; page
    slicing beyond that stays the route's ``_page_after_id`` concern.
    """
    _require(bool(user_id) and isinstance(user_id, str), "read_for_user: user_id required")
    _require(isinstance(limit, int) and 1 <= limit <= 500, "read_for_user: limit out of range")
    path = (
        f"{TABLE}?select={SELECT_COLUMNS}&user_id=eq.{_quote(user_id)}"
        f"&order=saved_at.desc,saved_id.desc&limit={int(limit)}"
    )
    if after_id is not None:
        path += f"&saved_id=neq.{_quote(after_id)}"
    result = typed_get(path)
    if result.state != READ_OK:
        return result
    kept, violated = _partition(result.rows, user_id)
    if not kept:
        return TypedRead(READ_OK_ZERO, [], error_class="partition_violation" if violated else None)
    return TypedRead(READ_OK, kept, error_class="partition_violation" if violated else None)


def read_one(user_id: str, saved_id: str) -> TypedRead:
    """One saved scenario by id, scoped to its owner.  Another user's id is
    indistinguishable from an absent one (``READ_OK_ZERO``, never 403)."""
    _require(bool(user_id) and isinstance(user_id, str), "read_one: user_id required")
    _require(bool(saved_id) and isinstance(saved_id, str), "read_one: saved_id required")
    path = (
        f"{TABLE}?select={SELECT_COLUMNS}&user_id=eq.{_quote(user_id)}"
        f"&saved_id=eq.{_quote(saved_id)}"
    )
    result = typed_get(path)
    if result.state != READ_OK:
        return result
    kept, violated = _partition(result.rows, user_id)
    if not kept:
        return TypedRead(READ_OK_ZERO, [], error_class="partition_violation" if violated else None)
    return TypedRead(READ_OK, kept, error_class="partition_violation" if violated else None)


def read_all_service_side() -> TypedRead:
    """Every saved row, for the monitor only.  No user partition here BY
    DESIGN — the monitor classifies every row it reads under that row's own
    user, and per-user reads keep their partition at the call site."""
    path = f"{TABLE}?select={SELECT_COLUMNS}&order=saved_at.desc,saved_id.desc"
    return typed_get(path)


def _row_of(saved: SavedScenario) -> dict[str, Any]:
    record = saved.as_record()
    return {
        "saved_id": saved.saved_id,
        "user_id": saved.user_id,
        "issuer_id": saved.issuer_id,
        "record": json.dumps(record, sort_keys=True, separators=(",", ":")),
        "saved_at": saved.saved_at,
        "updated_at": saved.saved_at,
        "last_outcome": saved.last_outcome,
        "last_outcome_generation_id": saved.last_outcome_generation_id,
    }


def upsert(saved: SavedScenario) -> StoreWrite:
    """Insert-or-merge one saved scenario; the same answer saved twice is the
    same row (``saved_id`` is the primary key, ``merge-duplicates``)."""
    _require(isinstance(saved, SavedScenario), "upsert: a SavedScenario is required")
    return _write(
        "POST",
        TABLE,
        body=_row_of(saved),
        prefer="resolution=merge-duplicates,return=minimal",
    )


def delete(user_id: str, saved_id: str) -> StoreWrite:
    """Remove one row scoped to BOTH keys — never a user-wide delete."""
    _require(bool(user_id) and isinstance(user_id, str), "delete: user_id required")
    _require(bool(saved_id) and isinstance(saved_id, str), "delete: saved_id required")
    return _write(
        "DELETE",
        f"{TABLE}?user_id=eq.{_quote(user_id)}&saved_id=eq.{_quote(saved_id)}",
        body=None,
        prefer="return=minimal",
    )


def write_outcome(saved_id: str, outcome: str, generation_id: str) -> StoreWrite:
    """Record the monitor's last classified outcome on the row (monitor only)."""
    _require(bool(saved_id) and isinstance(saved_id, str), "write_outcome: saved_id required")
    _require(outcome in RESTORE_OUTCOMES, f"write_outcome: {outcome!r} is not a restore outcome")
    _require(bool(generation_id) and isinstance(generation_id, str), "write_outcome: generation_id required")
    return _write(
        "PATCH",
        f"{TABLE}?saved_id=eq.{_quote(saved_id)}",
        body={
            "last_outcome": outcome,
            "last_outcome_generation_id": generation_id,
        },
        prefer="return=minimal",
    )
