"""Authenticated read API for the Capital Structure observed-filing-state desk.

This router is deliberately a transport boundary, not another capital-structure
engine.  It reads only the compiler-verified ``projection.json`` artifact and the
published ``state_bundle.json`` generation, and returns their observed
filing-state records without integrating a family or deriving terms, capacity,
runway, dilution, severity, or financing probability at request time.  A
then-known view is re-derived by the producer's own functions over the verified
generation, so there is still exactly one calculation path.

All routes require the paid ``site_full`` entitlement even while the global
paywall switch is in observe mode.  The artifact is public-safe, but issuer
research remains a private product surface: every response is private,
uncacheable, and noindex.
"""
from __future__ import annotations

import json
import os
import re
import threading
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, NamedTuple
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse

from engine.capital_structure.capacity import CapacityInputError
from engine.capital_structure.funding import FundingInputError
from engine.capital_structure.issuer_state_contracts import (
    AUTHORITY,
    PROJECTION_COMPATIBILITY,
    VIEW_MODES,
    ActionSelection,
    ContractViolation,
    EvidenceRef,
    FinancingScenario,
    PriceAssumption,
    Provenance,
    Quantity,
    UnknownResolution,
)
from engine.capital_structure.projection import (
    PROJECTION_BUNDLE_SCHEMA,
    PROJECTION_SCHEMA,
    validate_projection_bundle,
)
from engine.capital_structure.registration_integration import REGISTRATION_FAMILY
from engine.capital_structure.rule_applicability import (
    RuleApplicabilityError,
    load_rule_applicability_pack,
    rule_status_as_of,
)
from engine.capital_structure.scenario_composition import (
    ScenarioCompositionError,
    compose_scenario,
)
from engine.capital_structure.scenario_inputs import (
    BUNDLE_FAMILIES,
    CAPACITY_INPUTS_FILENAME,
    CAPACITY_INPUTS_SCHEMA,
    ISSUER_FAMILIES,
    RULES_FAMILY,
    ScenarioInputsError,
    ScenarioInputsUnavailable,
    assemble_scenario_inputs,
    validate_capacity_inputs_bundle,
)
from engine.capital_structure.saved_scenarios import (
    RESTORE_NOTES,
    RestoreOutcome,
    SavedScenario,
    classify_restore,
    restore_anchor,
    result_digest_of,
    result_substance_digest_of,
)
from engine.capital_structure.saved_scenario_store import (
    READ_OK,
    READ_OK_ZERO,
    READ_UNAVAILABLE,
)
from engine.capital_structure import saved_scenario_store as store
from engine.capital_structure.scenario_export import (
    ScenarioExportError,
    export_filename,
    export_scenario_envelope,
)
from engine.capital_structure.state_changes import (
    CHANGE_KINDS,
    STATE_CHANGES_SCHEMA,
    StateChange,
    StateChangeSet,
    changes_for_issuer,
)
from engine.capital_structure.state_bundle import (
    STATE_BUNDLE_SCHEMA,
    coverage_for,
    issuer_inputs,
    not_yet_observed,
    state_from_record,
    then_known_state,
    validate_state_bundle,
)
from engine.capital_structure.verified_projection_generation import (
    read_verified_projection_generation,
)
from engine.fundamental_forensics.query_exports import EXPORT_FORMATS


router = APIRouter()

REPO = Path(os.environ.get("MACRO_REPO") or Path(__file__).resolve().parents[1])
PROJECTION_PATH = REPO / "data" / "capital_structure" / "projection.json"
STATE_PATH = REPO / "data" / "capital_structure" / "state_bundle.json"
#: U2-2: the derived change ledger the nightly publishes next to the bundle it
#: diffs into (SPEC_U2 §1.1); the change desk serves it, never recomputes it.
STATE_CHANGES_PATH = REPO / "data" / "capital_structure" / "state_changes.json"

_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")
_BARE_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_NEW_YORK = ZoneInfo("America/New_York")
_LOCK = threading.Lock()
_CACHE: dict[str, Any] = {
    "path": None,
    "mtime_ns": None,
    "size": None,
    "payload": None,
}
_STATE_CACHE: dict[str, Any] = {
    "path": None,
    "mtime_ns": None,
    "size": None,
    "payload": None,
}
_INPUTS_CACHE: dict[str, Any] = {
    "path": None,
    "mtime_ns": None,
    "size": None,
    "payload": None,
}
#: U2-2: the published change ledger, cached stat-exact like the other artifacts.
#: It is a published artifact, never user data, and a failed read is never cached.
_CHANGES_CACHE: dict[str, Any] = {
    "path": None,
    "mtime_ns": None,
    "size": None,
    "payload": None,
}
#: The verified generation is read only on the then-known path, and is cached on
#: the three artifacts that decide its contents.
_GENERATION_ARTIFACTS = ("telemetry.json", "event_versions.parquet", "event_edges.parquet")
_GENERATION_CACHE: dict[str, Any] = {"key": None, "payload": None}
_RULE_PACK_CACHE: dict[str, Any] = {"payload": None}

_PRIVATE_HEADERS = {
    "Cache-Control": "private, no-store",
    "Vary": "Authorization",
    "X-Content-Type-Options": "nosniff",
    "X-Robots-Tag": "noindex, noarchive",
}

#: U1a serves facts and historical knowledge only; ``scenario`` is U1b.
_VIEW_MODES = ("current", "then_known")
_CLOCKS = ("system", "public")
_PUBLIC_CLOCK_NOTE = "public clock not separately modelled in this generation"
_STATE_UNAVAILABLE = "capital structure state unavailable"
_STATE_NOT_BOUND = "state generation does not bind served projection"
_ABSENT_RULE_CONDITION = "rule text not in the applicability pack"
#: U1b: the published capacity inputs bundle sits next to the state bundle it
#: binds, and every refusal below is verbatim from SPEC_U1B §4.
_INPUTS_UNAVAILABLE = "capacity inputs unavailable"
_INPUTS_NOT_BOUND = "capacity inputs do not bind served state"
_SCENARIO_AS_OF_MISMATCH = "scenario.as_of must equal the state cutoff"
_MAX_SCENARIO_BODY_BYTES = 32 * 1024
_MAX_SCENARIO_ACTIONS = 16
_MAX_SCENARIO_LABEL_CHARS = 120
_RECOMMENDATION_WORDS = ("recommend", "should buy", "should sell", "should raise", "target price", "score")
#: U2-2 (SPEC_U2 §1 "U2-2"): every refusal below is verbatim from the frozen
#: spec, or the house-style typed 503 for a published artifact that is absent
#: or unreadable (the ledger has no other named message, so absence refuses
#: closed like the state bundle does).
_CHANGE_LEDGER_UNAVAILABLE = "change ledger unavailable"
_CHANGE_LEDGER_NOT_BOUND = "change ledger does not bind served state"
_CHANGE_LEDGER_DOES_NOT_COVER_SINCE = "change_ledger_does_not_cover_since"
_SAVED_SCENARIO_NOT_FOUND = "saved scenario not found"
_STORE_UNAVAILABLE = "saved_scenarios_store_unavailable"
_NOTHING_TO_EXPORT = "nothing to export: {outcome}"
_METHOD_NOT_ALLOWED = "method not allowed"
#: The exact top-level body a save accepts: the scenario, the view anchor the
#: row stores, and the display label.  Anything else is an unknown field.
_SAVE_BODY_FIELDS = frozenset({"scenario", "view", "label"})
_SAVED_VIEW_KEYS = frozenset({"mode", "cutoff"})
#: The exact top-level body a ``FinancingScenario`` is built from.  Anything
#: else — including a client-supplied ``scenario_id`` — is an unknown field.
_SCENARIO_BODY_FIELDS = frozenset(
    {
        "view",
        "as_of",
        "horizon_start",
        "horizon_end",
        "price",
        "actions",
        "fee_rate",
        "discount_rate",
        "other_assumptions",
        "unknown_resolutions",
        "label",
    }
)

#: Source grades whose retained text a viewer grant may expose.  U1a retains no
#: source text locally, so ``_retained_excerpt`` is the single hook a later grant
#: would implement.
_EXCERPT_GRADES = frozenset({"excerpt_permitted"})


def require_site_full_user(authorization: str | None = Header(default=None)) -> dict:
    """Authenticate, then apply the same always-on site_full gate as Forensics."""
    from app.main import require_user as _require_user  # noqa: PLC0415
    from app.paywall import enforce_site_full  # noqa: PLC0415

    try:
        return enforce_site_full(_require_user(authorization), always=True)
    except HTTPException as exc:
        # This dependency also runs in isolated router tests, before app.main's
        # API middleware has a chance to attach the cache/noindex policy.
        raise _private_error(exc.status_code, exc.detail, exc.headers) from None


def _private(response: Response) -> None:
    """Set the standalone-router response policy (main's API middleware reinforces it)."""
    response.headers.update(_PRIVATE_HEADERS)


def _private_error(
    status_code: int,
    detail: Any,
    extra_headers: dict[str, str] | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=detail,
        headers={**_PRIVATE_HEADERS, **(extra_headers or {})},
    )


def _unavailable(detail: str = "capital structure observed filing state unavailable") -> HTTPException:
    return _private_error(503, detail)


def _reset_cache() -> None:
    """Test seam; a failed reload is intentionally never cached."""
    with _LOCK:
        _CACHE.update(path=None, mtime_ns=None, size=None, payload=None)


def _reset_state_cache() -> None:
    """Test seam for the published generation and the verified inputs behind it."""
    with _LOCK:
        _STATE_CACHE.update(path=None, mtime_ns=None, size=None, payload=None)
        _GENERATION_CACHE.update(key=None, payload=None)


def _reset_inputs_cache() -> None:
    """Test seam for the published capacity inputs bundle."""
    with _LOCK:
        _INPUTS_CACHE.update(path=None, mtime_ns=None, size=None, payload=None)


def _reset_changes_cache() -> None:
    """Test seam for the published change ledger."""
    with _LOCK:
        _CHANGES_CACHE.update(path=None, mtime_ns=None, size=None, payload=None)


def _records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate the API's identity assumptions on top of the serialized contract."""
    records = payload.get("records")
    if not isinstance(records, list):
        raise _unavailable("capital structure observed filing state invalid")

    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict) or record.get("schema") != PROJECTION_SCHEMA:
            raise _unavailable("capital structure observed filing state invalid")
        issuer_id = record.get("issuer_id")
        if not isinstance(issuer_id, str) or not issuer_id or issuer_id in seen:
            # A ticker may legitimately map to more than one stable issuer, but
            # canonical issuer IDs may never collide.  Do not pick a winner.
            raise _unavailable("capital structure observed filing state invalid")
        seen.add(issuer_id)
        normalized.append(record)
    return sorted(normalized, key=lambda item: str(item["issuer_id"]))


def _load() -> dict[str, Any]:
    """Read one validated canonical artifact; absent, stale-invalid, and unavailable fail closed."""
    try:
        stat = PROJECTION_PATH.stat()
    except OSError as exc:
        raise _unavailable() from exc

    with _LOCK:
        if (
            _CACHE["payload"] is not None
            and _CACHE["path"] == str(PROJECTION_PATH)
            and _CACHE["mtime_ns"] == stat.st_mtime_ns
            and _CACHE["size"] == stat.st_size
        ):
            return _CACHE["payload"]

        try:
            value = json.loads(PROJECTION_PATH.read_text(encoding="utf-8"))
            if not isinstance(value, dict) or value.get("schema") != PROJECTION_BUNDLE_SCHEMA:
                raise ValueError("schema mismatch")
            validate_projection_bundle(value)
            _records(value)
            coverage = value.get("coverage")
            if not isinstance(coverage, dict) or coverage.get("state") == "unavailable":
                raise ValueError("unavailable artifact")
        except Exception as exc:  # noqa: BLE001 — source artifact is an all-or-nothing boundary
            raise _unavailable() from exc

        _CACHE.update(
            path=str(PROJECTION_PATH),
            mtime_ns=stat.st_mtime_ns,
            size=stat.st_size,
            payload=value,
        )
        return value


def _load_state() -> dict[str, Any]:
    """Read one validated published state generation; anything else fails closed."""
    try:
        stat = STATE_PATH.stat()
    except OSError as exc:
        raise _unavailable(_STATE_UNAVAILABLE) from exc

    with _LOCK:
        if (
            _STATE_CACHE["payload"] is not None
            and _STATE_CACHE["path"] == str(STATE_PATH)
            and _STATE_CACHE["mtime_ns"] == stat.st_mtime_ns
            and _STATE_CACHE["size"] == stat.st_size
        ):
            return _STATE_CACHE["payload"]

        try:
            value = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            if not isinstance(value, dict) or value.get("schema") != STATE_BUNDLE_SCHEMA:
                raise ValueError("schema mismatch")
            validate_state_bundle(value)
        except Exception as exc:  # noqa: BLE001 — a published generation is all-or-nothing
            raise _unavailable(_STATE_UNAVAILABLE) from exc

        _STATE_CACHE.update(
            path=str(STATE_PATH),
            mtime_ns=stat.st_mtime_ns,
            size=stat.st_size,
            payload=value,
        )
        return value


def _load_inputs() -> dict[str, Any]:
    """Read one validated published capacity inputs bundle, or fail closed.

    The bundle is published next to the state bundle it binds, so the path is
    derived from the served ``STATE_PATH`` on every call.  A missing, unreadable
    or contract-invalid file is :data:`_INPUTS_UNAVAILABLE`; a valid bundle that
    binds another state generation is :data:`_INPUTS_NOT_BOUND`.  A failed check
    is never cached.
    """
    path = STATE_PATH.parent / CAPACITY_INPUTS_FILENAME
    try:
        stat = path.stat()
    except OSError as exc:
        raise _unavailable(_INPUTS_UNAVAILABLE) from exc

    with _LOCK:
        if (
            _INPUTS_CACHE["payload"] is not None
            and _INPUTS_CACHE["path"] == str(path)
            and _INPUTS_CACHE["mtime_ns"] == stat.st_mtime_ns
            and _INPUTS_CACHE["size"] == stat.st_size
        ):
            return _INPUTS_CACHE["payload"]

        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict) or value.get("schema") != CAPACITY_INPUTS_SCHEMA:
                raise ValueError("schema mismatch")
            validate_capacity_inputs_bundle(value)
        except Exception as exc:  # noqa: BLE001 — a published bundle is all-or-nothing
            raise _unavailable(_INPUTS_UNAVAILABLE) from exc

    # The binding check reads the state bundle through its own loader (which
    # takes the same lock), so it runs outside the block above.
    state = _load_state()
    if value.get("state_generation_id") != state.get("generation_id"):
        raise _unavailable(_INPUTS_NOT_BOUND)

    with _LOCK:
        _INPUTS_CACHE.update(
            path=str(path),
            mtime_ns=stat.st_mtime_ns,
            size=stat.st_size,
            payload=value,
        )
        return value


def _changeset_from_record(value: Any) -> StateChangeSet:
    """Rebuild the published ledger through the contract constructors only.

    The producer writes ``StateChangeSet.as_record()``; every record is
    reconstructed as a :class:`StateChange` and the set re-validates itself, so
    a tampered or foreign artifact is a :class:`ContractViolation` — never a
    partially trusted desk.
    """
    if not isinstance(value, Mapping) or value.get("schema") != STATE_CHANGES_SCHEMA:
        raise ContractViolation("state_changes: schema mismatch")
    changes = tuple(
        StateChange(
            kind=row["kind"],
            reason=row["reason"],
            issuer_id=row["issuer_id"],
            subject=row["subject"],
            before=row["before"],
            after=row["after"],
            evidence=row["evidence"],
            from_generation_id=row["from_generation_id"],
            to_generation_id=row["to_generation_id"],
        )
        for row in value.get("changes") or ()
    )
    return StateChangeSet(
        from_generation_id=value.get("from_generation_id"),
        to_generation_id=value["to_generation_id"],
        from_as_of=value.get("from_as_of"),
        to_as_of=value["to_as_of"],
        baseline=bool(value.get("baseline")),
        changes=changes,
        generated_at=value["generated_at"],
    )


def _load_changes() -> StateChangeSet:
    """Read one validated published change ledger; anything else fails closed."""
    try:
        stat = STATE_CHANGES_PATH.stat()
    except OSError as exc:
        raise _unavailable(_CHANGE_LEDGER_UNAVAILABLE) from exc

    with _LOCK:
        if (
            _CHANGES_CACHE["payload"] is not None
            and _CHANGES_CACHE["path"] == str(STATE_CHANGES_PATH)
            and _CHANGES_CACHE["mtime_ns"] == stat.st_mtime_ns
            and _CHANGES_CACHE["size"] == stat.st_size
        ):
            return _CHANGES_CACHE["payload"]

        try:
            value = json.loads(STATE_CHANGES_PATH.read_text(encoding="utf-8"))
            changeset = _changeset_from_record(value)
        except Exception as exc:  # noqa: BLE001 — a published ledger is all-or-nothing
            raise _unavailable(_CHANGE_LEDGER_UNAVAILABLE) from exc

        _CHANGES_CACHE.update(
            path=str(STATE_CHANGES_PATH),
            mtime_ns=stat.st_mtime_ns,
            size=stat.st_size,
            payload=changeset,
        )
        return changeset


def _generation_key() -> tuple[tuple[str, int, int], ...]:
    """The identity of the verified generation on disk: three artifacts, stat-exact."""
    key: list[tuple[str, int, int]] = []
    for name in _GENERATION_ARTIFACTS:
        artifact = STATE_PATH.parent / name
        try:
            stat = artifact.stat()
        except OSError as exc:
            raise _unavailable(_STATE_UNAVAILABLE) from exc
        key.append((str(artifact), stat.st_mtime_ns, stat.st_size))
    return tuple(key)


def _load_generation() -> Any:
    """The verified generation; read only on the then-known path, never for current."""
    key = _generation_key()
    with _LOCK:
        if _GENERATION_CACHE["payload"] is not None and _GENERATION_CACHE["key"] == key:
            return _GENERATION_CACHE["payload"]

        try:
            generation = read_verified_projection_generation(STATE_PATH.parent)
        except Exception as exc:  # noqa: BLE001 — an unverifiable generation is never served
            raise _unavailable(_STATE_UNAVAILABLE) from exc

        _GENERATION_CACHE.update(key=key, payload=generation)
        return generation


def _rule_pack() -> Any:
    """The one applicability pack every rule status in a response is read from."""
    with _LOCK:
        if _RULE_PACK_CACHE["payload"] is not None:
            return _RULE_PACK_CACHE["payload"]

        try:
            pack = load_rule_applicability_pack()
        except Exception as exc:  # noqa: BLE001 — without the pack no rule text is known
            raise _unavailable(_STATE_UNAVAILABLE) from exc

        _RULE_PACK_CACHE["payload"] = pack
        return pack


def _rule_pack_identity(pack: Any) -> dict[str, Any]:
    """The rule-pack binding the producer writes, read from the pack the same way."""
    return {
        "rule_pack_id": pack.rule_pack_id,
        "rule_pack_version": pack.version,
        "rule_pack_digest": pack.file_sha256,
    }


def _bound_state(projection: dict[str, Any]) -> dict[str, Any]:
    """The published generation, only while it binds the projection being served."""
    bundle = _load_state()
    if bundle.get("projection_generation_id") != projection.get("generation_id"):
        raise _unavailable(_STATE_NOT_BOUND)
    if dict(bundle.get("rule_pack") or {}) != _rule_pack_identity(_rule_pack()):
        raise _unavailable(_STATE_UNAVAILABLE)
    return bundle


def _envelope(bundle: dict[str, Any]) -> dict[str, Any]:
    """Shared observed-state receipt carried by every API response."""
    return {
        "schema": bundle["schema"],
        "projection_version": bundle["projection_version"],
        "generation_id": bundle["generation_id"],
        "as_of": bundle["as_of"],
        "generated_at": bundle["generated_at"],
        "authority": bundle["authority"],
        "coverage": bundle["coverage"],
        "unavailable": bundle["unavailable"],
    }


def _overview_record(record: dict[str, Any]) -> dict[str, Any]:
    """A compact issuer card, directly selected from the projection—not computed."""
    return {
        "issuer_id": record["issuer_id"],
        "identity": record["identity"],
        "latest_observed_event": record["latest_observed_event"],
        "what_changed": record["what_changed"],
        "coverage": record["coverage"],
        "authority": record["authority"],
        "unavailable": record["unavailable"],
    }


def _issuer(bundle: dict[str, Any], issuer_id: str) -> dict[str, Any]:
    record = next(
        (row for row in _records(bundle) if row["issuer_id"] == issuer_id),
        None,
    )
    if record is None:
        raise _private_error(404, "issuer not covered")
    return record


def _page_after_id(rows: list[dict[str, Any]], cursor: str | None, key: str) -> tuple[list[dict[str, Any]], str | None]:
    """Stable keyset pagination; unknown cursors never silently restart a listing."""
    if cursor is None:
        return rows, None
    index = next((idx for idx, row in enumerate(rows) if row.get(key) == cursor), None)
    if index is None:
        raise _private_error(400, "invalid cursor")
    return rows[index + 1 :], cursor


def _retained_excerpt(entry: dict[str, Any]) -> str | None:
    """Retained source text for one evidence span; U1a retains none locally."""
    return None


def _parameter_error(message: str, parameter: str, reason: str) -> HTTPException:
    """A private 400 that names the refused parameter and why it was refused."""
    return _private_error(400, {"error": message, "parameter": parameter, "reason": reason})


def _instant(value: Any) -> datetime:
    """Parse a published ISO-8601 instant; an unreadable one fails closed."""
    text = str(value)
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise _unavailable(_STATE_UNAVAILABLE) from exc


def _utc_stamp(moment: datetime) -> str:
    """Whole-second UTC ``YYYY-MM-DDTHH:MM:SSZ`` — the generation's own clock form."""
    return moment.astimezone(timezone.utc).replace(microsecond=0, tzinfo=None).isoformat() + "Z"


def _normalize_instant(value: str, parameter: str) -> str:
    """Normalize a query date or instant to UTC ``YYYY-MM-DDTHH:MM:SSZ``.

    A bare date means the END of that calendar day in New York, DST-correct.  An
    instant must carry an explicit offset or ``Z``, and a non-zero sub-second
    fraction is refused: every clock in the generation is whole seconds.
    """
    text = str(value)
    if _BARE_DATE_RE.fullmatch(text):
        try:
            day = date.fromisoformat(text)
        except ValueError as exc:
            raise _parameter_error(f"invalid {parameter}", parameter, "not_iso8601") from exc
        end_of_day = datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=_NEW_YORK)
        return _utc_stamp(end_of_day)

    candidate = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        moment = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise _parameter_error(f"invalid {parameter}", parameter, "not_iso8601") from exc
    if moment.tzinfo is None or moment.microsecond:
        raise _parameter_error(f"invalid {parameter}", parameter, "not_iso8601")
    return _utc_stamp(moment)


def _view_query(
    mode: str | None, cutoff: str | None, clock: str | None
) -> tuple[str, str | None, str]:
    """Validate the view parameters before any artifact is read."""
    view_mode = _VIEW_MODES[0] if mode is None else mode
    if view_mode not in _VIEW_MODES:
        raise _parameter_error("invalid mode", "mode", "unsupported_mode")
    view_clock = _CLOCKS[0] if clock is None else clock
    if view_clock not in _CLOCKS:
        raise _parameter_error("invalid clock", "clock", "unsupported_clock")
    if cutoff is not None and view_mode == "current":
        raise _parameter_error("invalid cutoff", "cutoff", "only_with_then_known")
    if cutoff is None and view_mode == "then_known":
        raise _parameter_error("cutoff required for then_known", "cutoff", "missing")
    normalized = None if cutoff is None else _normalize_instant(cutoff, "cutoff")
    return view_mode, normalized, view_clock


def _view(
    mode: str, as_of: str, clock: str, state_id: str | None, generation_id: str
) -> dict[str, Any]:
    """The echoed request identity; a derivation never mints a generation."""
    view: dict[str, Any] = {
        "mode": mode,
        "as_of": as_of,
        "clock": clock,
        "state_id": state_id,
        "generation_id": generation_id,
        "scenario_id": None,
    }
    if clock == "public":
        view["clock_note"] = _PUBLIC_CLOCK_NOTE
    return view


def _state_record(bundle: dict[str, Any], issuer_id: str) -> dict[str, Any]:
    """The published state of one covered issuer; an uncovered one is a 404."""
    index = bundle.get("issuer_index")
    if not isinstance(index, dict) or issuer_id not in index:
        raise _private_error(404, "issuer not covered")
    record = next(
        (
            row
            for row in bundle.get("issuers") or ()
            if isinstance(row, dict)
            and str((row.get("request") or {}).get("issuer_id") or "") == issuer_id
        ),
        None,
    )
    if record is None:
        raise _private_error(404, "issuer not covered")
    return record


def _registration_family(record: dict[str, Any]) -> dict[str, Any] | None:
    return next(
        (
            row
            for row in record.get("families") or ()
            if isinstance(row, dict) and str(row.get("family") or "") == REGISTRATION_FAMILY
        ),
        None,
    )


def _path_rows(family_record: dict[str, Any]) -> list[dict[str, Any]]:
    """The family's registration paths in the API's stable listing order."""
    return sorted(
        (row for row in family_record.get("records") or () if isinstance(row, dict)),
        key=lambda row: str(row["path_id"]),
    )


def _published_coverage(bundle: dict[str, Any], issuer_id: str) -> dict[str, Any]:
    coverage = bundle["issuer_index"][issuer_id]["coverage"].get(REGISTRATION_FAMILY)
    if not isinstance(coverage, dict):
        raise _unavailable(_STATE_UNAVAILABLE)
    return dict(coverage)


def _cited_event_ids(path: dict[str, Any]) -> set[str]:
    """Every event a path's predicates cite — the producer's evidence-join rule."""
    predicates = path.get("predicates")
    if not isinstance(predicates, dict):
        return set()
    cited: set[str] = set()
    for predicate in predicates.values():
        if isinstance(predicate, dict):
            cited.update(str(event_id) for event_id in predicate.get("evidence_event_ids") or () if event_id)
    return cited


def _cited_rule_ids(path: dict[str, Any]) -> list[str]:
    """Every rule a path's predicates cite, sorted and de-duplicated."""
    predicates = path.get("predicates")
    if not isinstance(predicates, dict):
        return []
    cited: set[str] = set()
    for predicate in predicates.values():
        if isinstance(predicate, dict):
            cited.update(str(rule_id) for rule_id in predicate.get("rule_ids") or () if rule_id)
    return sorted(cited)


def _evidence_refs(
    bundle: dict[str, Any], issuer_id: str, path: dict[str, Any], *, then_known: bool
) -> list[dict[str, Any]]:
    """The EvidenceRefs one path cites; a key the index lacks fails closed.

    A derived path id embeds its own cutoff, so the then-known view cannot use
    the published per-path index and re-joins on the cited events instead.
    """
    index = bundle["evidence_index"]
    if then_known:
        cited = _cited_event_ids(path)
        keys = sorted(
            key
            for key, entry in index.items()
            if entry.get("issuer_id") == issuer_id
            and cited.intersection(str(event_id) for event_id in entry["event_ids"])
        )
    else:
        keys = list(bundle["issuer_index"][issuer_id]["path_evidence"].get(str(path["path_id"]), ()))
    refs = []
    for key in keys:
        entry = index.get(key)
        if not isinstance(entry, dict):
            raise _unavailable(_STATE_UNAVAILABLE)
        refs.append(
            {
                "manifest_id": entry["manifest_id"],
                "span_id": entry["span_id"],
                "text_sha256": entry["text_sha256"],
            }
        )
    return sorted(refs, key=lambda ref: (str(ref["manifest_id"]), str(ref["span_id"])))


def _rule_status_for(pack: Any, rule_id: str, as_of_day: str) -> dict[str, Any]:
    """One rule's status on one day; a rule the pack lacks is named, never fatal."""
    try:
        return rule_status_as_of(pack, rule_id, as_of_day).as_record()
    except RuleApplicabilityError:
        return {
            "rule_id": rule_id,
            "as_of": as_of_day,
            "state": None,
            "window": None,
            "condition": _ABSENT_RULE_CONDITION,
        }


def _earliest_available_at(inputs: Any) -> datetime | None:
    """The first house-knowledge clock among one issuer's bound input events."""
    moments = [
        _instant(available_at)
        for available_at in (
            (event.get("point_in_time") or {}).get("available_at")
            for event in inputs.events
            if isinstance(event, dict)
        )
        if available_at
    ]
    return min(moments) if moments else None


class _StateView(NamedTuple):
    """Everything both state routes answer from, resolved in ruling A5's order."""

    issuer_id: str
    mode: str
    bundle: dict[str, Any]
    projection_record: dict[str, Any]
    state_record: dict[str, Any]
    family_record: dict[str, Any]
    coverage: dict[str, Any]
    view: dict[str, Any]
    not_yet_observed: list[dict[str, Any]]


def _state_view(
    issuer_id: str, mode: str | None, cutoff: str | None, clock: str | None
) -> _StateView:
    """Resolve one issuer's registration state, current or then known at a cutoff.

    The order is the law: parameter format, projection, binding, coverage,
    cutoff bounds, and only then the verified generation a derivation needs.
    """
    view_mode, cutoff_instant, view_clock = _view_query(mode, cutoff, clock)
    projection = _load()
    projection_record = _issuer(projection, issuer_id)
    bundle = _bound_state(projection)
    published = _state_record(bundle, issuer_id)
    pack = _rule_pack()
    if cutoff_instant is not None and _instant(cutoff_instant) > _instant(bundle["as_of"]):
        raise _parameter_error("invalid cutoff", "cutoff", "after_generation_as_of")

    if view_mode == "current":
        family_record = _registration_family(published)
        if family_record is None:
            raise _unavailable(_STATE_UNAVAILABLE)
        state_record = published
        coverage = _published_coverage(bundle, issuer_id)
        view_as_of = str(bundle["as_of"])
        pending: list[dict[str, Any]] = []
    else:
        generation = _load_generation()
        try:
            inputs = issuer_inputs(bundle, generation, issuer_id)
        except (ContractViolation, ValueError) as exc:
            raise _unavailable(str(exc)) from exc
        earliest = _earliest_available_at(inputs)
        if earliest is not None and _instant(cutoff_instant) < earliest:
            raise _parameter_error("invalid cutoff", "cutoff", "before_first_bound_event")
        try:
            derived = then_known_state(published, inputs, cutoff=cutoff_instant, rule_pack=pack)
        except (ContractViolation, ValueError) as exc:
            raise _unavailable(str(exc)) from exc
        family = derived.family(REGISTRATION_FAMILY)
        if family is None:
            raise _unavailable(_STATE_UNAVAILABLE)
        state_record = derived.as_record()
        family_record = family.as_record()
        coverage = coverage_for(family, rule_pack=pack)
        view_as_of = cutoff_instant or str(bundle["as_of"])
        pending = not_yet_observed(published, derived, inputs)

    view = _view(
        view_mode,
        view_as_of,
        view_clock,
        str(state_record["state_id"]),
        str(bundle["generation_id"]),
    )
    return _StateView(
        issuer_id=issuer_id,
        mode=view_mode,
        bundle=bundle,
        projection_record=projection_record,
        state_record=state_record,
        family_record=family_record,
        coverage=coverage,
        view=view,
        not_yet_observed=pending,
    )


# ---------------------------------------------------------------------------
# U1b — the scenario evaluate route and its body boundary
# ---------------------------------------------------------------------------


def _advisory_match(value: Any) -> str | None:
    """The first advisory-vocabulary match in one JSON string, or None.

    Applied to every key and every string value of a request body: the joint
    model answers what the contracted actions and inputs imply, and no field of
    the request may ask it for advisory language instead.
    """
    text = str(value).strip().lower()
    for word in _RECOMMENDATION_WORDS:
        if word in text:
            return word
    return None


def _body_advisory(body: Any) -> str | None:
    """Scan a parsed body's keys and string values for advisory vocabulary."""
    if isinstance(body, dict):
        for key, value in body.items():
            match = _advisory_match(key) or _body_advisory(value)
            if match is not None:
                return match
        return None
    if isinstance(body, list):
        for item in body:
            match = _body_advisory(item)
            if match is not None:
                return match
        return None
    if isinstance(body, str):
        return _advisory_match(body)
    return None


def _quantity_from_body(row: Any) -> Quantity | None:
    """Build a request ``Quantity`` through the contract constructor only."""
    if row is None:
        return None
    if not isinstance(row, dict):
        raise ContractViolation("quantity: an object is required")
    provenance_row = row.get("provenance")
    provenance = None
    if provenance_row is not None:
        if not isinstance(provenance_row, dict):
            raise ContractViolation("quantity.provenance: an object is required")
        evidence = provenance_row.get("evidence")
        if evidence is None:
            evidence = []
        if not isinstance(evidence, list):
            raise ContractViolation("quantity.provenance.evidence: a list is required")
        refs = []
        for item in evidence:
            if not isinstance(item, dict):
                raise ContractViolation("quantity.provenance.evidence: an object is required")
            refs.append(
                EvidenceRef(item.get("manifest_id"), item.get("span_id"), item.get("text_sha256"))
            )
        provenance = Provenance(
            input_family=provenance_row.get("input_family"),
            generation_id=provenance_row.get("generation_id"),
            evidence=tuple(refs),
            available_at=provenance_row.get("available_at"),
        )
    return Quantity(
        unit=row.get("unit"),
        status=row.get("status") or "unknown",
        value=row.get("value"),
        share_basis=row.get("share_basis"),
        security_class_id=row.get("security_class_id"),
        applicability=row.get("applicability"),
        provenance=provenance,
        note=row.get("note"),
    )


def _scenario_from_body(body: dict[str, Any]) -> FinancingScenario:
    """The request body as a ``FinancingScenario``, constructor by constructor.

    Every nested object is built through its own frozen contract class, so a
    body that cannot be a scenario is a ``ContractViolation`` carrying the
    contract's own message — never a partial guess.
    """
    price_row = body.get("price")
    if not isinstance(price_row, dict):
        raise ContractViolation("scenario.price: PriceAssumption required")
    path = price_row.get("path")
    if path is None:
        path = []
    if not isinstance(path, list):
        raise ContractViolation("price.path: a list of (date, price) pairs is required")
    price = PriceAssumption(
        kind=price_row.get("kind"),
        currency=price_row.get("currency") or "USD",
        fixed_price=price_row.get("fixed_price"),
        path=tuple(tuple(point) for point in path),
    )

    action_rows = body.get("actions")
    if action_rows is None:
        action_rows = []
    if not isinstance(action_rows, list):
        raise ContractViolation("scenario.actions: a list of ActionSelection is required")
    actions = []
    for row in action_rows:
        if not isinstance(row, dict):
            raise ContractViolation("scenario.actions: ActionSelection required")
        conditions = row.get("conditions_assumed_met") or ()
        if not isinstance(conditions, list):
            raise ContractViolation("action.conditions_assumed_met: a list is required")
        actions.append(
            ActionSelection(
                route_id=row.get("route_id"),
                action=row.get("action"),
                settlement=row.get("settlement"),
                quantity=_quantity_from_body(row.get("quantity")),
                conditions_assumed_met=tuple(conditions),
            )
        )

    resolution_rows = body.get("unknown_resolutions")
    if resolution_rows is None:
        resolution_rows = []
    if not isinstance(resolution_rows, list):
        raise ContractViolation("scenario.unknown_resolutions: a list is required")
    resolutions = []
    for row in resolution_rows:
        if not isinstance(row, dict):
            raise ContractViolation("scenario.unknown_resolutions: UnknownResolution required")
        resolutions.append(
            UnknownResolution(
                unknown_id=row.get("unknown_id"),
                assumed=_quantity_from_body(row.get("assumed")),
                rationale=row.get("rationale"),
            )
        )

    other = body.get("other_assumptions")
    if other is None:
        other = []
    if not isinstance(other, list):
        raise ContractViolation("scenario.other_assumptions: a list of pairs is required")
    label = body.get("label")
    if label is not None and not isinstance(label, str):
        raise ContractViolation("scenario.label: a string or null is required")
    return FinancingScenario(
        view=body.get("view"),
        as_of=body.get("as_of"),
        horizon_start=body.get("horizon_start"),
        horizon_end=body.get("horizon_end"),
        price=price,
        actions=tuple(actions),
        fee_rate=body.get("fee_rate"),
        discount_rate=body.get("discount_rate"),
        other_assumptions=tuple(tuple(item) for item in other),
        unknown_resolutions=tuple(resolutions),
        label=label,
    )


def _inputs_view(inputs_record: dict[str, Any], issuer_id: str) -> dict[str, Any]:
    """The per-family support echo: support, reason codes and binding, no records.

    The served bundle is the provenance of what was composed; echoing its whole
    records would duplicate the result's own inputs.  ``rules`` is bundle-level
    and names no binding of its own.
    """
    entries = inputs_record["issuers"][issuer_id]
    echo: dict[str, Any] = {
        family: {
            "support": entries[family]["support"],
            "reason_codes": list(entries[family]["reason_codes"]),
            "binding": entries[family]["binding"],
        }
        for family in ISSUER_FAMILIES
    }
    rules = inputs_record["rules"]
    echo[RULES_FAMILY] = {
        "support": rules["support"],
        "reason_codes": list(rules["reason_codes"]),
        "binding": None,
    }
    return echo


@router.get("/api/capital-structure/v1/coverage")
def coverage(response: Response, _user: dict = Depends(require_site_full_user)) -> dict[str, Any]:
    """Coverage/freshness receipt for observed filing state; no inferred risk fields.

    The projection half is unchanged.  The added ``state`` block reports the
    published generation's own denominators, and an unavailable generation is
    named inside that block rather than allowed to take the projection receipt
    down with it.
    """
    _private(response)
    projection = _load()
    try:
        bundle = _bound_state(projection)
        family = bundle["coverage"]["families"][REGISTRATION_FAMILY]
        state_block: dict[str, Any] = {
            "status": "available",
            "generation_id": bundle["generation_id"],
            "as_of": bundle["as_of"],
            "families": {
                REGISTRATION_FAMILY: {
                    "support": family["support"],
                    "examined": family["examined"],
                    "total": family["total"],
                    "unexamined_reason_codes": family["unexamined_reason_codes"],
                }
            },
        }
    except HTTPException as exc:
        state_block = {"status": "unavailable", "reason": exc.detail}
    except (KeyError, TypeError):
        state_block = {"status": "unavailable", "reason": _STATE_UNAVAILABLE}
    return _envelope(projection) | {"state": state_block}


@router.get("/api/capital-structure/v1/overview")
def overview(
    response: Response,
    cursor: str | None = Query(default=None, min_length=1, max_length=128),
    limit: int = Query(default=25, ge=1, le=100),
    _user: dict = Depends(require_site_full_user),
) -> dict[str, Any]:
    """Stable-issuer paginated overview for the observed filing-state desk."""
    _private(response)
    bundle = _load()
    candidates, requested_cursor = _page_after_id(_records(bundle), cursor, "issuer_id")
    page_records = candidates[:limit]
    has_more = len(candidates) > len(page_records)
    return _envelope(bundle) | {
        "page": {
            "cursor": requested_cursor,
            "next_cursor": page_records[-1]["issuer_id"] if has_more and page_records else None,
            "limit": limit,
            "returned": len(page_records),
            "total": len(_records(bundle)),
        },
        "records": [_overview_record(record) for record in page_records],
    }


@router.get("/api/capital-structure/v1/issuers/resolve")
def resolve_issuer(
    response: Response,
    ticker: str = Query(min_length=1, max_length=16),
    as_of: str | None = Query(default=None),
    _user: dict = Depends(require_site_full_user),
) -> dict[str, Any]:
    """Resolve an observed ticker without treating a ticker as a stable issuer identity.

    With ``as_of`` the answer is the then-known one — the issuer that held the
    ticker at that instant, plus every holder change observed up to it.  Without
    ``as_of`` the response is byte-identical to the projection-only resolver and
    the state bundle is never read.
    """
    _private(response)
    normalized = ticker.strip().upper()
    if not _TICKER_RE.fullmatch(normalized):
        raise _private_error(400, "invalid ticker")
    moment = None if as_of is None else _normalize_instant(as_of, "as_of")

    bundle = _load()
    if moment is not None:
        return _resolve_at(bundle, normalized, moment)

    matches = []
    for record in _records(bundle):
        identity = record["identity"]
        tickers = {
            str(identity.get("ticker") or "").upper(),
            *(str(value).upper() for value in identity.get("observed_tickers") or []),
        }
        if normalized in tickers:
            matches.append(record)

    if not matches:
        raise _private_error(404, "ticker not covered")
    if len(matches) > 1:
        raise _private_error(
            status_code=409,
            detail={
                "code": "ambiguous_ticker",
                "ticker": normalized,
                "matches": [
                    {"issuer_id": record["issuer_id"], "identity": record["identity"]}
                    for record in matches
                ],
            },
        )

    return _envelope(bundle) | {
        "query": {"ticker": normalized},
        "issuer": _overview_record(matches[0]),
    }


def _resolve_at(projection: dict[str, Any], normalized: str, moment: str) -> dict[str, Any]:
    """The then-known holder of a ticker, and every holder change up to that instant."""
    bundle = _bound_state(projection)
    cutoff = _instant(moment)
    if cutoff > _instant(bundle["as_of"]):
        raise _parameter_error("invalid as_of", "as_of", "after_generation_as_of")

    index = bundle["issuer_index"]
    holders: list[tuple[dict[str, Any], str]] = []
    observed: list[tuple[str, str, str, dict[str, Any]]] = []
    for issuer_id in sorted(index):
        rows = sorted(
            index[issuer_id]["ticker_observations"],
            key=lambda row: (str(row["first_observed_at"]), str(row["event_id"])),
        )
        known = [row for row in rows if _instant(row["first_observed_at"]) <= cutoff]
        if known and str(known[-1]["ticker"]).upper() == normalized:
            holders.append((known[-1], issuer_id))
        observed.extend(
            (str(row["first_observed_at"]), str(row["event_id"]), issuer_id, row)
            for row in known
            if str(row["ticker"]).upper() == normalized
        )

    if not holders:
        raise _private_error(404, "ticker not covered")

    observed.sort(key=lambda row: (row[0], row[1]))
    transitions: list[dict[str, Any]] = []
    previous: str | None = None
    for first_observed_at, event_id, issuer_id, row in observed:
        if issuer_id == previous:
            continue
        transitions.append(
            {
                "from": previous,
                "to": issuer_id,
                "effective": first_observed_at,
                "evidence": {"event_id": event_id, "accession": row["accession"]},
            }
        )
        previous = issuer_id

    latest = max(row["first_observed_at"] for row, _ in holders)
    winners = sorted(
        issuer_id for row, issuer_id in holders if row["first_observed_at"] == latest
    )
    if len(winners) > 1:
        raise _private_error(
            status_code=409,
            detail={
                "code": "ambiguous_ticker",
                "ticker": normalized,
                "as_of": moment,
                "matches": [
                    {"issuer_id": issuer_id, "identity": _issuer(projection, issuer_id)["identity"]}
                    for issuer_id in winners
                ],
            },
        )

    holder = winners[0]
    return _envelope(projection) | {
        "query": {"ticker": normalized, "as_of": moment},
        "issuer": _overview_record(_issuer(projection, holder)),
        "identity_transitions": transitions,
        "view": _view("then_known", moment, "system", None, str(bundle["generation_id"])),
    }


@router.get("/api/capital-structure/v1/issuers/{issuer_id}")
def issuer_dossier(
    issuer_id: str,
    response: Response,
    _user: dict = Depends(require_site_full_user),
) -> dict[str, Any]:
    """Return one issuer's observed-state dossier (timeline remains paginated separately)."""
    _private(response)
    bundle = _load()
    record = _issuer(bundle, issuer_id)
    return _envelope(bundle) | {"issuer": _overview_record(record)}


@router.get("/api/capital-structure/v1/issuers/{issuer_id}/events")
def issuer_events(
    issuer_id: str,
    response: Response,
    cursor: str | None = Query(default=None, min_length=1, max_length=128),
    limit: int = Query(default=25, ge=1, le=100),
    _user: dict = Depends(require_site_full_user),
) -> dict[str, Any]:
    """Paginate the artifact's issuer timeline, including its bounded SEC evidence refs."""
    _private(response)
    bundle = _load()
    record = _issuer(bundle, issuer_id)
    timeline = list(record["timeline"])
    candidates, requested_cursor = _page_after_id(timeline, cursor, "event_id")
    events = candidates[:limit]
    has_more = len(candidates) > len(events)
    return _envelope(bundle) | {
        "issuer": {
            "issuer_id": record["issuer_id"],
            "identity": record["identity"],
            "coverage": record["coverage"],
            "authority": record["authority"],
            "unavailable": record["unavailable"],
        },
        "page": {
            "cursor": requested_cursor,
            "next_cursor": events[-1]["event_id"] if has_more and events else None,
            "limit": limit,
            "returned": len(events),
            "total": len(timeline),
        },
        "events": events,
    }


@router.get("/api/capital-structure/v1/issuers/{issuer_id}/state")
def issuer_state_view(
    issuer_id: str,
    response: Response,
    mode: str | None = Query(default=None),
    cutoff: str | None = Query(default=None),
    clock: str | None = Query(default=None),
    _user: dict = Depends(require_site_full_user),
) -> dict[str, Any]:
    """One issuer's registration state, as published or as then known at a cutoff."""
    _private(response)
    resolved = _state_view(issuer_id, mode, cutoff, clock)
    return {
        "view": resolved.view,
        "compatibility": dict(PROJECTION_COMPATIBILITY),
        "authority": dict(AUTHORITY),
        "issuer_id": issuer_id,
        "identity": resolved.projection_record["identity"],
        "families": {
            REGISTRATION_FAMILY: {**resolved.family_record, "coverage": resolved.coverage}
        },
        "horizons": resolved.bundle["horizons"],
        "unavailable": resolved.state_record["unavailable"],
        "capabilities_proven": resolved.state_record["capabilities_proven"],
        "receipt": resolved.state_record["receipt"],
        "input_generations": resolved.state_record["request"]["input_generations"],
        "not_yet_observed": resolved.not_yet_observed,
    }


def _admit_scenario_body(raw: bytes) -> dict[str, Any]:
    """The evaluate body boundary, shared by every scenario-consuming route.

    Size limit, JSON object, advisory scan, unknown fields and per-field
    limits — the U1B-2 table verbatim, so save, restore and export refuse a
    body exactly as the evaluate route does.
    """
    if len(raw) > _MAX_SCENARIO_BODY_BYTES:
        raise _private_error(413, "request body too large")
    try:
        body = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise _private_error(422, "request body is not valid JSON") from exc
    if not isinstance(body, dict):
        raise _private_error(422, "request body must be a JSON object")

    advisory = _body_advisory(body)
    if advisory is not None:
        raise _private_error(422, f"request carries advisory vocabulary: {advisory!r}")
    unknown = next((str(key) for key in sorted(body) if str(key) not in _SCENARIO_BODY_FIELDS), None)
    if unknown is not None:
        raise _private_error(422, f"unknown field: {unknown}")
    label = body.get("label")
    if isinstance(label, str) and len(label) > _MAX_SCENARIO_LABEL_CHARS:
        raise _private_error(422, "label too long")
    action_rows = body.get("actions")
    if isinstance(action_rows, list) and len(action_rows) > _MAX_SCENARIO_ACTIONS:
        raise _private_error(422, "too many actions")
    return body


class _Evaluated(NamedTuple):
    """One evaluate run: the response envelope plus what it actually bound.

    The restore classifies against the state and inputs generations THIS run
    bound — never a second independent read — and carries the evaluated
    scenario (the rebased anchor on a restore) for the typed outcome and the
    export envelope.
    """

    envelope: dict[str, Any]
    scenario: FinancingScenario
    state_generation_id: str
    inputs_generation_id: str


def _evaluate_internals(
    issuer_id: str,
    mode: str | None,
    cutoff: str | None,
    clock: str | None,
    raw: bytes,
    *,
    rebase_as_of: bool = False,
    anchor: SavedScenario | None = None,
) -> _Evaluated:

    """The evaluate route's whole body — U1B-2 §4, unchanged, now shared.

    SPEC_U2 §1 "U2-2": save, restore and export run THIS function, so an
    unavailable result is never saved, restored or exported.  The order is the
    route's original law: the served state generation, the published inputs
    bundle, then the body, then composition.  Every refusal is the route's own
    typed error, propagated unchanged.

    The restore path alone sets ``rebase_as_of`` (with the saved row as
    ``anchor``): the scenario evaluated is :func:`restore_anchor`'s — the saved
    assumptions re-anchored at the served generation's as_of — so the as_of
    equality below holds by construction and a nightly move is a re-run, not a
    refusal.  Every public caller keeps the defaults and byte-identical
    behaviour.
    """
    resolved = _state_view(issuer_id, mode, cutoff, clock)
    state_bundle = resolved.bundle
    inputs_record = _load_inputs()
    state = state_from_record(resolved.state_record)

    body = _admit_scenario_body(raw)
    try:
        scenario = _scenario_from_body(body)
    except ContractViolation as exc:
        raise _private_error(422, {"contract_error": str(exc)}) from exc
    if rebase_as_of:
        if anchor is None:
            raise _private_error(422, {"contract_error": "restore rebase requires the saved anchor"})
        scenario = restore_anchor(anchor, str(state.request.as_of))
    if scenario.as_of != state.request.as_of:
        raise _private_error(422, _SCENARIO_AS_OF_MISMATCH)

    try:
        assembled = assemble_scenario_inputs(
            inputs_record,
            issuer_id,
            scenario.as_of,
            served_state_generation_id=str(state_bundle["generation_id"]),
        )
    except ScenarioInputsError as exc:
        # A stale binding, another as_of or an unknown issuer is a conflict with
        # the published bundle — refused, never composed around.
        raise _private_error(409, str(exc)) from exc
    if isinstance(assembled, ScenarioInputsUnavailable):
        raise _private_error(
            409,
            {
                "code": "scenario_inputs_unavailable",
                "components": assembled.components,
                "available": list(assembled.available),
            },
        )
    inputs_view = _inputs_view(inputs_record, issuer_id)

    view = _view(
        "scenario",
        scenario.as_of,
        resolved.view["clock"],
        str(state.state_id),
        str(state_bundle["generation_id"]),
    )
    view["scenario_id"] = scenario.scenario_id
    try:
        result = compose_scenario(
            state,
            assembled.instruments,
            assembled.basis,
            assembled.financials,
            assembled.commitments,
            scenario,
            assembled.rules,
            pack=_rule_pack(),
        )
    except ScenarioCompositionError as exc:
        raise _private_error(409, str(exc)) from exc
    except (CapacityInputError, FundingInputError) as exc:
        raise _private_error(422, str(exc)) from exc

    return _Evaluated(
        envelope={
            "view": view,
            "inputs": inputs_view,
            "result": result.as_record(),
            "facts_unchanged": True,
            "compatibility": dict(PROJECTION_COMPATIBILITY),
            "authority": dict(AUTHORITY),
        },
        scenario=scenario,
        state_generation_id=str(state_bundle["generation_id"]),
        inputs_generation_id=str(inputs_record["generation_id"]),
    )


def _scenario_record_of(raw: bytes) -> dict[str, Any]:
    """The constructed scenario's published record for an admitted body.

    Deterministic re-derivation through the same constructors the internals
    used: after a successful evaluate this cannot refuse, and the record —
    with its server-minted schema and scenario_id — is what a saved row and
    every export carry.
    """
    return _scenario_from_body(_admit_scenario_body(raw)).as_record()


@router.post("/api/capital-structure/v1/issuers/{issuer_id}/scenarios/evaluate")
async def issuer_scenario_evaluate(
    issuer_id: str,
    request: Request,
    response: Response,
    mode: str | None = Query(default=None),
    cutoff: str | None = Query(default=None),
    clock: str | None = Query(default=None),
    _user: dict = Depends(require_site_full_user),
) -> dict[str, Any]:
    """Compose one financing scenario over the served state and inputs, or refuse.

    SPEC_U1B §4.  The route is the only place the product reaches the joint
    model, and it never persists or caches a scenario: entitlement first, then
    the served state generation and the published capacity inputs bundle, then
    the body — built into a ``FinancingScenario`` through the contract
    constructors only, under strict size and field limits.  A family the
    bundle cannot bind is a typed 409 that names every unavailable family; the
    composition itself is S0's, returned unchanged with the request's view
    identity and the context-only authority receipt.
    """
    _private(response)
    raw = await request.body()
    return _evaluate_internals(issuer_id, mode, cutoff, clock, raw).envelope


@router.get("/api/capital-structure/v1/issuers/{issuer_id}/state/registration")
def issuer_registration_state(
    issuer_id: str,
    response: Response,
    mode: str | None = Query(default=None),
    cutoff: str | None = Query(default=None),
    clock: str | None = Query(default=None),
    cursor: str | None = Query(default=None, min_length=1, max_length=128),
    limit: int = Query(default=25, ge=1, le=100),
    _user: dict = Depends(require_site_full_user),
) -> dict[str, Any]:
    """The registration family alone: its paths, their evidence and their rule status."""
    _private(response)
    resolved = _state_view(issuer_id, mode, cutoff, clock)
    pack = _rule_pack()
    rows = _path_rows(resolved.family_record)
    candidates, requested_cursor = _page_after_id(rows, cursor, "path_id")
    paths = candidates[:limit]
    has_more = len(candidates) > len(paths)
    then_known = resolved.mode == "then_known"
    as_of_day = str(resolved.view["as_of"])[:10]
    return {
        "view": resolved.view,
        "compatibility": dict(PROJECTION_COMPATIBILITY),
        "authority": dict(AUTHORITY),
        "issuer_id": issuer_id,
        "family": {
            key: value for key, value in resolved.family_record.items() if key != "records"
        },
        "coverage": resolved.coverage,
        "paths": [
            {
                **path,
                "evidence": _evidence_refs(resolved.bundle, issuer_id, path, then_known=then_known),
                "rule_status": {
                    rule_id: _rule_status_for(pack, rule_id, as_of_day)
                    for rule_id in _cited_rule_ids(path)
                },
            }
            for path in paths
        ],
        "page": {
            "cursor": requested_cursor,
            "next_cursor": paths[-1]["path_id"] if has_more and paths else None,
            "limit": limit,
            "returned": len(paths),
            "total": len(rows),
        },
        "not_yet_observed": resolved.not_yet_observed,
    }


@router.get("/api/capital-structure/v1/issuers/{issuer_id}/evidence/{manifest_id}/{span_id}")
def issuer_evidence_span(
    issuer_id: str,
    manifest_id: str,
    span_id: str,
    response: Response,
    _user: dict = Depends(require_site_full_user),
) -> dict[str, Any]:
    """One exact retained-byte span: its locator, the operands it supports, its rule.

    The span is served only to the issuer that cites it, only while its retained
    digest still equals the source ledger's, and never with retained text unless
    the source grade permits and a retention hook actually returns it.
    """
    _private(response)
    projection = _load()
    _issuer(projection, issuer_id)
    bundle = _bound_state(projection)
    published = _state_record(bundle, issuer_id)

    entry = bundle["evidence_index"].get(f"{manifest_id}/{span_id}")
    if not isinstance(entry, dict) or entry.get("issuer_id") != issuer_id:
        raise _private_error(404, "evidence not found")
    if entry["ledger_text_sha256"] is not None and entry["ledger_text_sha256"] != entry["text_sha256"]:
        raise _private_error(409, "evidence hash mismatch")

    family_record = _registration_family(published) or {}
    by_path = {str(row["path_id"]): row for row in _path_rows(family_record)}
    cited_events = {str(event_id) for event_id in entry["event_ids"]}
    evidence_ref = {
        "manifest_id": entry["manifest_id"],
        "span_id": entry["span_id"],
        "text_sha256": entry["text_sha256"],
    }
    operands: list[dict[str, Any]] = []
    rule_ids: set[str] = set()
    for path_id in sorted(str(item) for item in entry["path_ids"]):
        path = by_path.get(path_id)
        predicates = path.get("predicates") if path is not None else None
        if not isinstance(predicates, dict):
            raise _unavailable(_STATE_UNAVAILABLE)
        for name in sorted(predicates):
            predicate = predicates[name]
            if not isinstance(predicate, dict):
                raise _unavailable(_STATE_UNAVAILABLE)
            cited = {str(item) for item in predicate.get("evidence_event_ids") or () if item}
            if not cited.intersection(cited_events):
                continue
            operands.append(
                {
                    "name": name,
                    "path_id": path_id,
                    "value": predicate.get("status"),
                    "unit": None,
                    "evidence": dict(evidence_ref),
                }
            )
            rule_ids.update(str(item) for item in predicate.get("rule_ids") or () if item)

    pack = _rule_pack()
    rule = None
    for rule_id in sorted(rule_ids):
        if rule_id in pack.rules:
            rule = {
                "rule_id": rule_id,
                "class": pack.rules[rule_id].binding_class,
                "pack_version": pack.version,
            }
            break

    body: dict[str, Any] = {
        "manifest_id": entry["manifest_id"],
        "span_id": entry["span_id"],
        "text_sha256": entry["text_sha256"],
        "filing": entry["filing"],
        "document": entry["document"],
        "anchor": entry["anchor"],
        "reason": entry["reason"],
        "grade": entry["grade"],
        "operands": operands,
        "rule": rule,
        "input_generations": bundle["input_generations"],
        "available_at": entry["available_at"],
        "view": _view(
            "current",
            str(bundle["as_of"]),
            "system",
            str(published["state_id"]),
            str(bundle["generation_id"]),
        ),
        "compatibility": dict(PROJECTION_COMPATIBILITY),
        "authority": dict(AUTHORITY),
    }
    if entry["grade"] not in _EXCERPT_GRADES:
        body["excerpt_status"] = "withheld"
        return body
    retained = _retained_excerpt(entry)
    if retained:
        body["excerpt_status"] = "present"
        body["excerpt"] = retained
    else:
        body["excerpt_status"] = "not_retained"
    return body


# ---------------------------------------------------------------------------
# U2-2 — the change desk, saved scenarios, restore and exact export (SPEC_U2)
# ---------------------------------------------------------------------------


def _caller_id(user: Mapping[str, Any]) -> str:
    """The entitled user's id — the only identity a saved row may carry.

    Read from the entitlement dependency alone; a ``user_id`` in a body is
    never looked at.
    """
    user_id = str(user.get("id") or "")
    if not user_id:
        raise _unavailable("authenticated user has no identity")
    return user_id


def _stored_record(row: Mapping[str, Any]) -> dict[str, Any]:
    """One store row's saved record.

    PostgREST delivers the ``record`` column as a jsonb object; the fake test
    transport delivers the same bytes as text.  Both forms are admitted, and a
    record that is neither — or text that does not parse — is the store being
    in doubt: the typed 503, never a partial answer.
    """
    raw = row.get("record")
    if isinstance(raw, str):
        try:
            value = json.loads(raw)
        except ValueError as exc:
            raise _unavailable(_STORE_UNAVAILABLE) from exc
    else:
        value = raw
    if not isinstance(value, dict):
        raise _unavailable(_STORE_UNAVAILABLE)
    return value


def _saved_from_record(record: Mapping[str, Any]) -> SavedScenario:
    """A stored record as a ``SavedScenario``, contract-checked on the way.

    ``schema`` and ``saved_id`` are the server's mint; every other field must
    reconstruct under the served contract version.  A row that no longer does
    — a missing or extra field, an invalid value, a record written before the
    substance digest existed — is the typed ``scenario_rejected`` restore
    outcome, never a partial answer and never a 500.
    """
    body = {
        str(key): value for key, value in record.items() if str(key) not in ("schema", "saved_id")
    }
    try:
        return SavedScenario(**body)
    except ContractViolation:
        raise
    except (TypeError, ValueError) as exc:
        raise ContractViolation(f"saved_scenario: stored record does not reconstruct ({exc})") from exc


def _public_of_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """A stored record minus its ``user_id`` — the most a response may carry."""
    return {str(key): value for key, value in record.items() if str(key) != "user_id"}


def _served_generations() -> tuple[str | None, str | None]:
    """The served state and inputs generation ids, ``None`` where the published
    artifact does not answer (each read is independently typed)."""
    try:
        state_generation_id = str(_load_state()["generation_id"])
    except HTTPException:
        state_generation_id = None
    try:
        inputs_generation_id = str(_load_inputs()["generation_id"])
    except HTTPException:
        inputs_generation_id = None
    return state_generation_id, inputs_generation_id


def _usable_ledger(
    saved_state_generation_id: Any, served_generation_id: str | None
) -> StateChangeSet | None:
    """The retained ledger, but ONLY when it spans exactly saved→served.

    A ledger between other generations classifies nothing honestly, and an
    absent or unreadable one is context the restore answers without — never a
    refusal of the caller's own row.
    """
    if not saved_state_generation_id or served_generation_id is None:
        return None
    try:
        changeset = _load_changes()
    except HTTPException:
        return None
    if changeset.from_generation_id != saved_state_generation_id:
        return None
    if changeset.to_generation_id != served_generation_id:
        return None
    return changeset


def _restore_view_params(view: Mapping[str, Any]) -> tuple[str | None, str | None]:
    """The evaluate parameters a stored view anchor re-runs under.

    A ``scenario`` or ``current`` anchor re-runs on the served current facts;
    a ``then_known`` anchor re-runs at its own cutoff (normalized at save
    time).  The evaluate internals' own error table still refuses an anchor
    the served generation cannot honour.
    """
    mode = str(view.get("mode") or "")
    cutoff = view.get("cutoff")
    if mode == "then_known":
        return "then_known", (None if cutoff is None else str(cutoff))
    return None, None


def _restore_outcome_from_refusal(
    saved: SavedScenario,
    exc: HTTPException,
    state_generation_id: str | None,
    inputs_generation_id: str | None,
    changeset: StateChangeSet | None,
) -> RestoreOutcome:
    """Map an evaluate refusal to the typed restore outcome it names.

    The closed table (S8), decided on the typed cause — the internals raise
    with ``from exc``, so ``exc.__cause__`` carries the engine class:

    - 503 → ``source_outage``;
    - 404 (the issuer is absent from the served state) → ``source_outage``;
    - 409 whose detail names ``scenario_inputs_unavailable`` →
      ``inputs_unavailable`` with the detail's components;
    - 409 whose cause is a ``ScenarioInputsError`` (an inputs as_of mismatch —
      the normal case for a ``then_known`` save after a nightly — or an
      unknown issuer) → ``inputs_unavailable``, naming every family with the
      engine's own reason, never an invented code;
    - any other 409 or 422 (composition, capacity, funding, a body contract
      error, the then_known as_of mismatch, a contract refusal of the rebased
      anchor) → ``scenario_rejected`` as a refusal of the served engine
      (``scenario_refused``);
    - any other status propagates unchanged.

    A restore refusal is a typed outcome for the caller's own row — never a
    number and never a propagated error.
    """
    detail = exc.detail
    cause = exc.__cause__
    if exc.status_code == 409 and isinstance(detail, Mapping) and detail.get("code") == "scenario_inputs_unavailable":
        unavailable = ScenarioInputsUnavailable(
            dict(detail.get("components") or {}),
            tuple(detail.get("available") or ()),
        )
        return classify_restore(
            saved,
            state_generation_id=state_generation_id,
            inputs_generation_id=inputs_generation_id,
            current_result=None,
            unavailable=unavailable,
            state_unavailable=False,
            scenario_rejected=False,
            changes=changeset,
        )
    if exc.status_code == 409 and isinstance(cause, ScenarioInputsError):
        unavailable = ScenarioInputsUnavailable(
            {
                family: {"support": "unavailable", "reason_codes": [str(cause)]}
                for family in BUNDLE_FAMILIES
            },
            (),
        )
        return classify_restore(
            saved,
            state_generation_id=state_generation_id,
            inputs_generation_id=inputs_generation_id,
            current_result=None,
            unavailable=unavailable,
            state_unavailable=False,
            scenario_rejected=False,
            changes=changeset,
        )
    if exc.status_code in (503, 404):
        return classify_restore(
            saved,
            state_generation_id=None,
            inputs_generation_id=None,
            current_result=None,
            unavailable=None,
            state_unavailable=True,
            scenario_rejected=False,
            changes=None,
        )
    if exc.status_code in (409, 422):
        return classify_restore(
            saved,
            state_generation_id=state_generation_id,
            inputs_generation_id=inputs_generation_id,
            current_result=None,
            unavailable=None,
            state_unavailable=False,
            scenario_rejected=False,
            scenario_refused=True,
            changes=changeset,
        )
    raise exc


def _restore_body(
    saved_public: dict[str, Any],
    current: dict[str, Any] | None,
    outcome: RestoreOutcome,
    issuer_changes: tuple[StateChange, ...],
) -> dict[str, Any]:
    """The one restore response shape, on the happy path and on every outcome."""
    return {
        "saved": saved_public,
        "current": current,
        "unavailable": (
            {"components": list(outcome.unavailable_components)}
            if outcome.outcome == "inputs_unavailable"
            else None
        ),
        "restore": outcome.as_record(),
        "changes": [change.as_record() for change in issuer_changes],
    }


def _rejected_restore(record: Mapping[str, Any], issuer_id: str, served_generation_id: str | None) -> dict[str, Any]:
    """The typed answer for a row that no longer reconstructs.

    Mirrors the classifier's first precedence row for a body the served
    contract version refuses — the one case where no ``SavedScenario`` exists
    to classify with, so the outcome carries the row's own stored identity.
    The scenario's as_of and scenario_id name the answer that cannot be
    re-run; a row missing either is store corruption, not an outcome the
    closed vocabulary can name.
    """
    result_id_before = str(record.get("result_id") or "")
    scenario_record = record.get("scenario")
    scenario_as_of = str(scenario_record.get("as_of") or "") if isinstance(scenario_record, Mapping) else ""
    scenario_id = str(scenario_record.get("scenario_id") or "") if isinstance(scenario_record, Mapping) else ""
    if not result_id_before or not scenario_as_of or not scenario_id:
        raise _unavailable(_STORE_UNAVAILABLE)
    _state_generation_id, inputs_generation_id = _served_generations()
    changeset = _usable_ledger(record.get("state_generation_id"), served_generation_id)
    issuer_changes = changes_for_issuer(changeset, issuer_id)
    outcome = RestoreOutcome(
        outcome="scenario_rejected",
        from_generation_id=(
            None if record.get("state_generation_id") is None else str(record["state_generation_id"])
        ),
        to_generation_id=served_generation_id,
        from_inputs_generation_id=(
            None if record.get("inputs_generation_id") is None else str(record["inputs_generation_id"])
        ),
        to_inputs_generation_id=inputs_generation_id,
        from_as_of=scenario_as_of,
        to_as_of=None,
        result_id_before=result_id_before,
        result_id_after=None,
        scenario_id_before=scenario_id,
        scenario_id_after=None,
        result_identical=None,
        changes_n=len(issuer_changes),
        change_kinds=tuple(sorted({change.kind for change in issuer_changes})),
        unavailable_components=(),
        note=RESTORE_NOTES["scenario_rejected"],
    )
    return _restore_body(_public_of_record(record), None, outcome, issuer_changes)


class _Restored(NamedTuple):
    """The restore response plus the envelope an export route may flatten."""

    body: dict[str, Any]
    export_envelope: dict[str, Any] | None


def _restore_answer(user_id: str, issuer_id: str, saved_id: str) -> _Restored:
    """Restore one saved exact answer against the served generation.

    The row is read through the store adapter (which owns the partition), the
    route re-checks it, and the evaluate internals re-run the saved scenario
    and view against the served generation — the SAME function, so a restore
    never recomposes differently from the live route.  A ``current`` or
    ``scenario`` anchor re-runs the saved assumptions AT the served as_of
    (:func:`restore_anchor` builds S′, once); a ``then_known`` anchor re-runs
    at its own cutoff.  The classification binds the generations THIS re-run
    bound, and identity is substance: the saved block stays byte-verbatim.
    Every outcome of the re-run is typed and 200; another user's or an absent
    ``saved_id`` is 404, never 403; identity drift is the typed 503.
    """
    result = store.read_one(user_id, saved_id)
    if result.state == READ_UNAVAILABLE:
        raise _unavailable(_STORE_UNAVAILABLE)
    if result.state != READ_OK or not result.rows:
        raise _private_error(404, _SAVED_SCENARIO_NOT_FOUND)
    row = result.rows[0]
    if str(row.get("user_id") or "") != user_id:
        # Defense in depth on the adapter's partition: not the caller's row
        # is an absent one, with nothing to distinguish.
        raise _private_error(404, _SAVED_SCENARIO_NOT_FOUND)
    record = _stored_record(row)
    if str(record.get("issuer_id") or "") != issuer_id:
        # A row is restorable only under its own issuer's path.
        raise _private_error(404, _SAVED_SCENARIO_NOT_FOUND)

    state_generation_id, inputs_generation_id = _served_generations()
    try:
        saved = _saved_from_record(record)
    except ContractViolation:
        return _Restored(_rejected_restore(record, issuer_id, state_generation_id), None)

    changeset = _usable_ledger(saved.state_generation_id, state_generation_id)
    issuer_changes = changes_for_issuer(changeset, saved.issuer_id)
    scenario_body = json.dumps(
        {
            str(key): value
            for key, value in saved.scenario.items()
            if str(key) not in ("schema", "scenario_id")
        }
    ).encode("utf-8")
    mode, cutoff = _restore_view_params(saved.view)
    try:
        evaluated = _evaluate_internals(
            saved.issuer_id,
            mode,
            cutoff,
            "system",
            scenario_body,
            rebase_as_of=mode is None,
            anchor=saved,
        )
    except HTTPException as exc:
        outcome = _restore_outcome_from_refusal(
            saved, exc, state_generation_id, inputs_generation_id, changeset
        )
        return _Restored(
            _restore_body(saved.public_record(), None, outcome, issuer_changes),
            None,
        )
    rebased = evaluated.scenario
    try:
        outcome = classify_restore(
            saved,
            state_generation_id=evaluated.state_generation_id,
            inputs_generation_id=evaluated.inputs_generation_id,
            current_result=evaluated.envelope["result"],
            unavailable=None,
            state_unavailable=False,
            scenario_rejected=False,
            changes=changeset,
            current_scenario_id=rebased.scenario_id,
            current_as_of=str(evaluated.envelope["view"]["as_of"]),
        )
    except ContractViolation as exc:
        if "saved_scenario:identity_drift" not in str(exc):
            raise
        raise _private_error(503, {"code": "saved_scenario_identity_drift"}) from exc
    export_envelope = {
        "view": evaluated.envelope["view"],
        "inputs": evaluated.envelope["inputs"],
        "result": evaluated.envelope["result"],
        "scenario": rebased.as_record(),
        "issuer_id": saved.issuer_id,
        "inputs_generation_id": evaluated.inputs_generation_id,
    }
    current = {
        "view": evaluated.envelope["view"],
        "inputs": evaluated.envelope["inputs"],
        "result": evaluated.envelope["result"],
        "scenario": rebased.as_record(),
    }
    return _Restored(
        _restore_body(saved.public_record(), current, outcome, issuer_changes),
        export_envelope,
    )


@router.get("/api/capital-structure/v1/issuers/{issuer_id}/changes")
def issuer_changes(
    issuer_id: str,
    response: Response,
    since: str | None = Query(default=None, min_length=1, max_length=128),
    _user: dict = Depends(require_site_full_user),
) -> dict[str, Any]:
    """One issuer's typed change desk over the retained generation pair.

    SPEC_U2 §1 "U2-2".  The desk serves the published ledger the nightly
    derived — never a recomputation — bound to the served state generation,
    and states honestly that only one generation of changes is retained.
    """
    _private(response)
    bundle = _load_state()
    _state_record(bundle, issuer_id)
    changeset = _load_changes()
    if str(changeset.to_generation_id) != str(bundle["generation_id"]):
        raise _unavailable(_CHANGE_LEDGER_NOT_BOUND)
    if since is not None and since != changeset.from_generation_id:
        raise _private_error(409, _CHANGE_LEDGER_DOES_NOT_COVER_SINCE)
    issuer_changes = changes_for_issuer(changeset, issuer_id)
    counts = {kind: 0 for kind in CHANGE_KINDS}
    for change in issuer_changes:
        counts[change.kind] += 1
    return {
        "from_generation_id": changeset.from_generation_id,
        "to_generation_id": changeset.to_generation_id,
        "baseline": changeset.baseline,
        "changes": [change.as_record() for change in issuer_changes],
        "counts": counts,
    }


@router.post("/api/capital-structure/v1/issuers/{issuer_id}/scenarios/saved")
async def issuer_scenario_save(
    issuer_id: str,
    request: Request,
    response: Response,
    _user: dict = Depends(require_site_full_user),
) -> JSONResponse:
    """Evaluate, then save the exact answer for the entitled user.

    SPEC_U2 §1 "U2-2".  The evaluate internals run first and their refusals
    propagate unchanged, so an unavailable result is never saved.  The saved
    view is the anchor the row stores (exactly ``mode`` and ``cutoff``), the
    user's id comes from the dependency alone, and the only write on this
    host is the one adapter call.
    """
    _private(response)
    user_id = _caller_id(_user)
    raw = await request.body()
    if len(raw) > _MAX_SCENARIO_BODY_BYTES:
        raise _private_error(413, "request body too large")
    try:
        body = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise _private_error(422, "request body is not valid JSON") from exc
    if not isinstance(body, dict):
        raise _private_error(422, "request body must be a JSON object")
    advisory = _body_advisory(body)
    if advisory is not None:
        raise _private_error(422, f"request carries advisory vocabulary: {advisory!r}")
    unknown = next((str(key) for key in sorted(body) if str(key) not in _SAVE_BODY_FIELDS), None)
    if unknown is not None:
        raise _private_error(422, f"unknown field: {unknown}")
    scenario_row = body.get("scenario")
    if not isinstance(scenario_row, dict):
        raise _private_error(422, "scenario: an object is required")
    view_row = body.get("view")
    if not isinstance(view_row, dict):
        raise _private_error(422, "view: an object is required")
    unexpected_view = next(
        (str(key) for key in sorted(view_row) if str(key) not in _SAVED_VIEW_KEYS), None
    )
    if unexpected_view is not None:
        raise _private_error(422, f"unknown field: {unexpected_view}")
    mode = view_row.get("mode")
    if not isinstance(mode, str) or mode not in VIEW_MODES:
        raise _private_error(422, f"view.mode: {mode!r} is not a view mode")
    raw_cutoff = view_row.get("cutoff")
    if raw_cutoff is not None and not isinstance(raw_cutoff, str):
        raise _private_error(422, "view.cutoff: a string or null is required")
    normalized_cutoff = None if raw_cutoff is None else _normalize_instant(raw_cutoff, "cutoff")
    label = body.get("label")
    if label is None:
        label = ""
    if not isinstance(label, str):
        raise _private_error(422, "label: a string or null is required")
    if len(label) > _MAX_SCENARIO_LABEL_CHARS:
        raise _private_error(422, "label too long")

    scenario_raw = json.dumps(scenario_row).encode("utf-8")
    eval_mode, eval_cutoff = (
        ("then_known", normalized_cutoff) if mode == "then_known" else (None, normalized_cutoff)
    )
    envelope = _evaluate_internals(issuer_id, eval_mode, eval_cutoff, "system", scenario_raw).envelope
    scenario_record = _scenario_record_of(scenario_raw)
    served_state = _load_state()
    served_inputs = _load_inputs()
    result = envelope["result"]
    try:
        saved = SavedScenario(
            user_id=user_id,
            issuer_id=issuer_id,
            label=label,
            view={"mode": mode, "cutoff": normalized_cutoff},
            scenario=scenario_record,
            state_generation_id=str(served_state["generation_id"]),
            inputs_generation_id=str(served_inputs["generation_id"]),
            result_id=str(result["result_id"]),
            result_digest=result_digest_of(result),
            result_substance_digest=result_substance_digest_of(result),
            rule_pack_digest=str(result["capacity_envelope"]["rule_pack_digest"]),
            saved_at=_utc_stamp(datetime.now(timezone.utc)),
        )
    except ContractViolation as exc:
        raise _private_error(422, {"contract_error": str(exc)}) from exc
    write = store.upsert(saved)
    if write.state != "ok":
        raise _unavailable(_STORE_UNAVAILABLE)
    return JSONResponse(
        {"saved": saved.public_record(), "restore": None},
        status_code=201,
        headers=_PRIVATE_HEADERS,
    )


@router.get("/api/capital-structure/v1/issuers/{issuer_id}/scenarios/saved")
def issuer_scenario_saved_list(
    issuer_id: str,
    response: Response,
    after: str | None = Query(default=None, min_length=1, max_length=128),
    limit: int = Query(default=25, ge=1, le=100),
    _user: dict = Depends(require_site_full_user),
) -> dict[str, Any]:
    """The caller's saved scenarios, newest first, one keyset page.

    The adapter owns the partition and the ``after`` keyset exclusion; the
    route re-checks the user of every row it serves and slices the page.
    """
    _private(response)
    user_id = _caller_id(_user)
    result = store.read_for_user(user_id, after_id=after, limit=limit + 1)
    if result.state == READ_UNAVAILABLE:
        raise _unavailable(_STORE_UNAVAILABLE)
    if result.error_class == "partition_violation":
        # The adapter caught the store serving another user's row: the typed
        # unavailable response, never the rows.
        raise _unavailable(_STORE_UNAVAILABLE)
    rows = list(result.rows or [])
    page = rows[:limit]
    items = []
    for row in page:
        if str(row.get("user_id") or "") != user_id:
            continue  # defense in depth: never serve another user's row
        try:
            items.append(_saved_from_record(_stored_record(row)).public_record())
        except ContractViolation as exc:
            # A row the contract refuses is the store being in doubt; refuse
            # the whole page rather than serve a partial one.
            raise _unavailable(_STORE_UNAVAILABLE) from exc
    next_after = str(page[-1]["saved_id"]) if page and len(rows) > len(page) else None
    return {"items": items, "next_after": next_after}


@router.get("/api/capital-structure/v1/issuers/{issuer_id}/scenarios/saved/{saved_id}")
async def issuer_scenario_restore(
    issuer_id: str,
    saved_id: str,
    response: Response,
    _user: dict = Depends(require_site_full_user),
) -> dict[str, Any]:
    """Restore one saved exact answer against the served generation.

    SPEC_U2 §1 "U2-2".  Always 200 with a typed ``restore.outcome`` when the
    row is the caller's — a correction, new events, no change, a source
    outage, unavailable inputs and a body that no longer reconstructs are
    named, never averaged into a number or an error.
    """
    _private(response)
    return _restore_answer(_caller_id(_user), issuer_id, saved_id).body


@router.delete("/api/capital-structure/v1/issuers/{issuer_id}/scenarios/saved/{saved_id}")
def issuer_scenario_delete(
    issuer_id: str,
    saved_id: str,
    response: Response,
    _user: dict = Depends(require_site_full_user),
) -> Response:
    """Remove one of the caller's saved scenarios, scoped to both keys."""
    _private(response)
    user_id = _caller_id(_user)
    result = store.read_one(user_id, saved_id)
    if result.state == READ_UNAVAILABLE:
        raise _unavailable(_STORE_UNAVAILABLE)
    if result.state != READ_OK or not result.rows:
        raise _private_error(404, _SAVED_SCENARIO_NOT_FOUND)
    row = result.rows[0]
    if str(row.get("user_id") or "") != user_id:
        raise _private_error(404, _SAVED_SCENARIO_NOT_FOUND)
    if str(_stored_record(row).get("issuer_id") or "") != issuer_id:
        raise _private_error(404, _SAVED_SCENARIO_NOT_FOUND)
    write = store.delete(user_id, saved_id)
    if write.state != "ok":
        raise _unavailable(_STORE_UNAVAILABLE)
    return Response(status_code=204, headers=_PRIVATE_HEADERS)


def _attachment(envelope: Mapping[str, Any], fmt: str) -> Response:
    """The one export response: deterministic bytes, exact filename, exact hash."""
    try:
        export = export_scenario_envelope(envelope, fmt)
        filename = export_filename(envelope, fmt)
    except ScenarioExportError as exc:
        raise _private_error(503, str(exc)) from None
    return Response(
        content=export.payload,
        media_type=export.media_type,
        headers={
            **_PRIVATE_HEADERS,
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-SHA256": export.sha256,
        },
    )


@router.get(
    "/api/capital-structure/v1/issuers/{issuer_id}/scenarios/saved/{saved_id}/export.{fmt}"
)
async def issuer_scenario_saved_export(
    issuer_id: str,
    saved_id: str,
    fmt: str,
    response: Response,
    _user: dict = Depends(require_site_full_user),
) -> Response:
    """The restored answer's exact bytes as a private attachment (SPEC_U2 §1.4)."""
    _private(response)
    if fmt not in EXPORT_FORMATS:
        raise _private_error(404, f"unsupported export format: {fmt}")
    restored = _restore_answer(_caller_id(_user), issuer_id, saved_id)
    if restored.export_envelope is None:
        raise _private_error(
            409,
            _NOTHING_TO_EXPORT.format(outcome=restored.body["restore"]["outcome"]),
        )
    return _attachment(restored.export_envelope, fmt)


@router.post(
    "/api/capital-structure/v1/issuers/{issuer_id}/scenarios/evaluate/export.{fmt}"
)
async def issuer_scenario_evaluate_export(
    issuer_id: str,
    fmt: str,
    request: Request,
    response: Response,
    mode: str | None = Query(default=None),
    cutoff: str | None = Query(default=None),
    clock: str | None = Query(default=None),
    _user: dict = Depends(require_site_full_user),
) -> Response:
    """The fresh evaluate answer's exact bytes as a private attachment.

    SPEC_U2 §1 "U2-2".  Same admission and error table as the evaluate route;
    the envelope states ``issuer_id`` and ``inputs_generation_id`` explicitly
    and embeds the evaluated scenario record, exactly as the serializer reads
    them.
    """
    _private(response)
    if fmt not in EXPORT_FORMATS:
        raise _private_error(404, f"unsupported export format: {fmt}")
    raw = await request.body()
    envelope = _evaluate_internals(issuer_id, mode, cutoff, clock, raw).envelope
    export_envelope = {
        **envelope,
        "scenario": _scenario_record_of(raw),
        "issuer_id": issuer_id,
        "inputs_generation_id": str(_load_inputs()["generation_id"]),
    }
    return _attachment(export_envelope, fmt)


@router.api_route(
    "/api/capital-structure/v1/issuers/{issuer_id}/scenarios/saved/{saved_id}/export.{fmt}",
    methods=["POST", "PUT", "PATCH", "DELETE", "HEAD"],
)
def issuer_scenario_saved_export_method_not_allowed(
    response: Response,
    _user: dict = Depends(require_site_full_user),
) -> None:
    """Auth first, then a private 405. Starlette's default 405 has no no-store policy."""
    del response
    raise _private_error(405, _METHOD_NOT_ALLOWED)


@router.api_route(
    "/api/capital-structure/v1/issuers/{issuer_id}/scenarios/evaluate/export.{fmt}",
    methods=["GET", "PUT", "PATCH", "DELETE", "HEAD"],
)
def issuer_scenario_evaluate_export_method_not_allowed(
    response: Response,
    _user: dict = Depends(require_site_full_user),
) -> None:
    """Auth first, then a private 405. Starlette's default 405 has no no-store policy."""
    del response
    raise _private_error(405, _METHOD_NOT_ALLOWED)


__all__ = ["router", "require_site_full_user"]
