"""P0 outcome-blind W2C owner census and population manifest.

This module is a read-only consumer of the private W2C experience owner.  It
publishes one census manifest for one declared through-session.  The manifest
carries the complete frozen activation/XNYS expected-session denominator -
admitted, abstained, missed and unrecorded typed gaps - and never filters by
mature, scoreable or outcome-observed state.

Membership identity is deliberately narrow.  It is derived only from the
registration identity, the exact declared through-session/calendar expected
denominator and each outcome-blind opportunity disposition, reason, exact
context/source reference and decision cutoff.  Outcome revisions and labels,
maturity state, population audit observation clocks, writer audit time and the
original population receipt's full-content audit hash are excluded from
membership; that receipt audit hash is retained separately in the manifest's
audit section, so audit identity may change without membership drift.

The manifest is authority-display and context only.  It performs no numerical
comparison, establishes no feature transform registry and no fitted normalizer,
and its fit eligibility is permanently false for P0.  Existing W2C binding
facts - ``training_eligible=false``, ``promotion_eligible=false`` and the
trusted owner's ``component_source_receipts_authenticated=false`` - are carried
through unchanged and never upgraded.

Rights authorization is a distinct layer that precedes source authentication:
the caller-supplied policy is consulted before any owner path is opened, again
once the owner identities are authenticated, and once more before the manifest
is disclosed.  A missing, false, mistyped, unbound or failing grant fails
closed.  Source authentication then authenticates the registration,
installation, ledger rows and original receipt through the owner's public
outcome-blind read seam, and closes every included context/capture/source
reference against the exact declared owner generation through existing public
owner read APIs.  A declared generation that is not published by the active
ancestry, or a declared capture that is absent from an authenticated
generation, is a typed retained gap; a present-but-corrupt closure is an
integrity failure.  A refused owner pin is a typed source qualification
failure and is never retried with a raised cap or replaced by a fallback
generation.  The manifest embeds only bounded identities, typed statuses and
digests - never source packet bodies or arbitrary payloads.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Protocol, runtime_checkable

from engine.neuralweb import market_memory
from engine.neuralweb import market_memory_experience_accrual as accrual
from engine.neuralweb import market_memory_pit
from engine.neuralweb import market_memory_technical_store as technical_store
from engine.neuralweb import market_memory_trusted as trusted_store

POPULATION_MANIFEST_SCHEMA = "market_memory.population_manifest.v1"
POPULATION_MANIFEST_PROFILE = "market_memory.population_manifest.v1"
POPULATION_MEMBERSHIP_SCHEMA = "market_memory.population_membership.v1"
POPULATION_ACCESS_POLICY_VERSION = "market_memory.population_manifest_access.v1"
POPULATION_MANIFEST_ID_PREFIX = "mmpopman_"

CENSUS_BASIS = (
    "frozen_activation_plus_xnys_calendar_not_presence_or_timer_runs"
)
GAP_DISPOSITION = "unrecorded"
GAP_REASON = "expected_session_without_authenticated_opportunity_row"
NO_CAPTURE_REASON = "no_source_reference_declared_by_owner_row"
CAPTURE_AUTHENTICATED_REASON = (
    "exact_declared_generation_and_capture_authenticated"
)
COORDINATES_PRESENT_REASON = (
    "registered_feature_coordinates_declared_by_owner_row"
)
COMPARISON_ELIGIBLE = "eligible_for_registered_comparison_only"
COMPARISON_PENDING = "pending_registered_coordinates"
COMPARISON_BLOCKED = "blocked_by_source_qualification"
COMPARISON_NOT_APPLICABLE = "not_applicable"
COMPARISON_STATUS = "not_performed_pending_registered_coordinates"
COMPARISON_REASON = (
    "p0_establishes_no_feature_transform_registry_or_fitted_normalizer"
)
FIT_REASON = "p0_population_manifest_is_authority_display_context_only"
CAPTURE_AVAILABLE = "authenticated"
CAPTURE_AVAILABLE_ABSENT = "absent_from_authenticated_generation"
CAPTURE_AVAILABLE_UNQUALIFIED = "generation_not_authenticated"
CAPTURE_AVAILABLE_NOT_APPLICABLE = "not_applicable"
GENERATION_AUTHENTICATED_STATUS = "authenticated"
GENERATION_AUTHENTICATED_REASON = (
    "exact_declared_generation_authenticated_under_the_registered_cap"
)
GENERATION_ABSENT_STATUS = "generation_absent_from_active_ancestry"
GENERATION_ABSENT_REASON = "declared_generation_not_published_by_active_ancestry"
CAP_REFUSED_STATUS = "capture_cap_refused"
CAP_REFUSED_REASON = "owner_pin_refused_under_the_registered_capture_cap"
STORE_ABSENT_STATUS = "owner_store_absent"
STORE_ABSENT_REASON = "declared_owner_store_root_is_absent"
CAPTURE_ABSENT_STATUS = "capture_absent_from_authenticated_generation"
CAPTURE_ABSENT_REASON = "declared_capture_absent_from_authenticated_generation"
GENERATION_NOT_AUTHENTICATED_STATUS = "generation_not_authenticated"
GENERATION_NOT_AUTHENTICATED_REASON = (
    "declared_generation_was_not_authenticated_so_capture_closure_is_unqualified"
)

MEMBERSHIP_EXCLUDED_DIMENSIONS = (
    "outcome_revision_ids",
    "outcome_labels_and_statuses",
    "maturity_state",
    "population_audit_observed_at",
    "population_writer_audit_commit",
    "population_receipt_full_content_audit_sha256",
)

MAX_EXPECTED_SESSIONS = 4096
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
FROZEN_PILOT_SESSIONS: tuple[str, ...] = tuple(
    session.isoformat()
    for session in accrual.nyse_calendar.sessions_between(
        accrual.ACTIVATION_SESSION, accrual.SUNSET_SESSION
    )
)
FROZEN_PILOT_SESSION_SET = frozenset(FROZEN_PILOT_SESSIONS)
_SESSION = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_SCOPE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_HEX64 = re.compile(r"[a-f0-9]{64}\Z")
_CAPTURE_ROLES = (("trusted", "trusted_capture"), ("technical", "technical_capture"))
_GENERATION_FIELDS = (
    ("trusted", "trusted_generation"),
    ("technical", "technical_generation"),
)


class MarketMemoryPopulationError(RuntimeError):
    """Base P0 population manifest contract failure."""


class MarketMemoryPopulationAccessError(MarketMemoryPopulationError):
    """The rights layer denied or failed before any owner path was opened."""


class MarketMemoryPopulationIntegrityError(MarketMemoryPopulationError):
    """An authenticated owner closure exists but is present and corrupt."""


@dataclass(frozen=True)
class PopulationAccessGrant:
    """One typed entitlement returned by a trusted-caller policy.

    A bare boolean is never treated as an authenticated entitlement: the
    policy must return this exact reviewed object shape, bound to the reviewed
    manifest policy version and, once they are authenticated, to the exact
    registration and store identities it may disclose.
    """

    policy_version: str
    caller_scope: str
    granted: bool
    registration_id: str | None = None
    store_id: str | None = None
    limitations: tuple[str, ...] = ()


@runtime_checkable
class PopulationAccessPolicy(Protocol):
    """Explicit trusted-caller rights seam, distinct from source authentication."""

    def authorize_population_manifest(
        self,
        *,
        repository_root: str,
        experience_root: str,
        through_session: str,
        registration_id: str | None,
        store_id: str | None,
    ) -> PopulationAccessGrant:
        """Return one typed grant, or deny by returning a refusal."""
        ...  # pragma: no cover - protocol


def _canonical_bytes(value: object) -> bytes:
    """Serialize one bounded finite JSON value in the owner's canonical form."""

    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise MarketMemoryPopulationError(
            "population manifest value is not finite canonical JSON"
        ) from exc


def _digest(body: bytes) -> str:
    return sha256(body).hexdigest()


def _content_id(value: dict[str, Any], *, field: str) -> str:
    core = dict(value)
    core[field] = ""
    return POPULATION_MANIFEST_ID_PREFIX + _digest(_canonical_bytes(core))


def _require_session(value: object, *, field: str) -> date:
    if type(value) is not str or not _SESSION.fullmatch(value):
        raise MarketMemoryPopulationError(
            f"population manifest {field} is not one ISO calendar session"
        )
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise MarketMemoryPopulationError(
            f"population manifest {field} is not one real calendar date"
        ) from exc


def _require_root(value: object, *, field: str) -> str:
    if isinstance(value, Path):
        value = str(value.expanduser())
    if type(value) is not str or not value:
        raise MarketMemoryPopulationError(
            f"population manifest {field} must be one concrete path string"
        )
    return value


def _require_grant(
    policy: object,
    *,
    repository_root: str,
    experience_root: str,
    through_session: str,
    registration_id: str | None,
    store_id: str | None,
) -> PopulationAccessGrant:
    """Run the rights layer once and fail closed on any refusal."""

    if type(policy) in (bool, int, float, str, bytes, list, dict, tuple, set):
        raise MarketMemoryPopulationAccessError(
            "population access policy is not one trusted-caller policy object"
        )
    authorize = getattr(policy, "authorize_population_manifest", None)
    if not callable(authorize):
        raise MarketMemoryPopulationAccessError(
            "population access policy is missing its authorize seam"
        )
    try:
        grant = authorize(
            repository_root=repository_root,
            experience_root=experience_root,
            through_session=through_session,
            registration_id=registration_id,
            store_id=store_id,
        )
    except MarketMemoryPopulationAccessError:
        raise
    except Exception as exc:
        raise MarketMemoryPopulationAccessError(
            "population access policy raised before any owner path was opened"
        ) from exc
    if type(grant) is not PopulationAccessGrant:
        raise MarketMemoryPopulationAccessError(
            "population access policy returned no typed reviewed grant"
        )
    if grant.granted is not True:
        raise MarketMemoryPopulationAccessError(
            "population access policy denied this manifest disclosure"
        )
    if grant.policy_version != POPULATION_ACCESS_POLICY_VERSION:
        raise MarketMemoryPopulationAccessError(
            "population access policy version is not the reviewed P0 policy"
        )
    if type(grant.caller_scope) is not str or not _SCOPE.fullmatch(
        grant.caller_scope
    ):
        raise MarketMemoryPopulationAccessError(
            "population access grant carries no bounded caller scope"
        )
    if registration_id is not None and grant.registration_id != registration_id:
        raise MarketMemoryPopulationAccessError(
            "population access grant is not bound to the authenticated registration"
        )
    if store_id is not None and grant.store_id != store_id:
        raise MarketMemoryPopulationAccessError(
            "population access grant is not bound to the authenticated store"
        )
    return grant


def _validate_ledger(ledger: object) -> dict[str, Any]:
    """Require the exact supported W2C outcome-blind owner profile."""

    if type(ledger) is not dict or ledger.get("schema") != (
        accrual.OUTCOME_BLIND_LEDGER_SCHEMA
    ):
        raise MarketMemoryPopulationError(
            "owner outcome-blind ledger schema is not the supported W2C profile"
        )
    if ledger.get("census_basis") != CENSUS_BASIS:
        raise MarketMemoryPopulationError(
            "owner outcome-blind census basis is not the frozen calendar census"
        )
    calendar = ledger.get("calendar")
    expected = calendar.get("expected_sessions") if type(calendar) is dict else None
    if (
        type(expected) is not list
        or not expected
        or len(expected) > MAX_EXPECTED_SESSIONS
        or any(type(item) is not str for item in expected)
        or len(set(expected)) != len(expected)
        or expected != sorted(expected)
    ):
        raise MarketMemoryPopulationError(
            "owner expected-session denominator is not one bounded ordered set"
        )
    for item in expected:
        _require_session(item, field="owner expected session")
    registration = ledger.get("registration")
    store = ledger.get("store")
    if type(registration) is not dict or type(store) is not dict:
        raise MarketMemoryPopulationError(
            "owner outcome-blind ledger lacks its authenticated identities"
        )
    if not _HEX64.fullmatch(str(registration.get("registration_sha256", ""))):
        raise MarketMemoryPopulationError(
            "owner registration identity is not content-addressed"
        )
    rows = ledger.get("rows")
    if type(rows) is not list or len(rows) > len(expected):
        raise MarketMemoryPopulationError(
            "owner ledger rows exceed their expected-session denominator"
        )
    known = set(expected)
    seen: set[str] = set()
    for row in rows:
        if type(row) is not dict:
            raise MarketMemoryPopulationError("owner ledger row is not an object")
        session = row.get("session")
        _require_session(session, field="owner ledger row session")
        if session in seen or session not in known:
            raise MarketMemoryPopulationError(
                "owner ledger row is duplicated or outside the denominator"
            )
        seen.add(session)
    return ledger


def _declared_sessions(expected: list[str], through_session: str) -> list[str]:
    if through_session not in FROZEN_PILOT_SESSION_SET:
        raise MarketMemoryPopulationError(
            "declared through-session is not one frozen XNYS pilot session"
        )
    if through_session not in expected:
        raise MarketMemoryPopulationError(
            "declared through-session is not one expected denominator session"
        )
    return list(expected[: expected.index(through_session) + 1])


def _registered_window(session: date) -> tuple[str, str]:
    """Recompute the frozen 04:30-04:45Z following-day admission window."""

    opened = datetime.combine(
        session + timedelta(days=1), time(4, 30), tzinfo=timezone.utc
    )
    deadline = opened + timedelta(seconds=900)
    return (
        opened.isoformat().replace("+00:00", "Z"),
        deadline.isoformat().replace("+00:00", "Z"),
    )


def _census_row(session: str, row: dict[str, Any] | None) -> dict[str, Any]:
    """Project one expected session as an outcome-blind census row."""

    if row is None:
        opened, deadline = _registered_window(
            _require_session(session, field="gap session")
        )
        return {
            "session": session,
            "opportunity_id": None,
            "disposition": GAP_DISPOSITION,
            "reason": GAP_REASON,
            "cutoff": {
                "window_opens_at": opened,
                "deadline_at": deadline,
                "clock_model": (
                    "session_ordinal_only_no_fabricated_market_close_timestamp"
                ),
            },
            "source_pins": None,
            "decision_state_projection": None,
            "decision_state_projection_reason": None,
        }
    return {
        "session": row["session"],
        "opportunity_id": row["opportunity_id"],
        "disposition": row["disposition"],
        "reason": row["reason"],
        "cutoff": row["cutoff"],
        "source_pins": row["source_pins"],
        "decision_state_projection": row["decision_state_projection"],
        "decision_state_projection_reason": row[
            "decision_state_projection_reason"
        ],
    }


def _generation_key(role: str, reference: dict[str, Any]) -> tuple[str, str, str]:
    return (
        role,
        str(reference.get("store_id")),
        str(reference.get("generation_id")),
    )


def _generation_refs(
    rows: list[dict[str, Any]],
) -> list[tuple[str, dict[str, Any]]]:
    """Collect distinct declared generation references in deterministic order."""

    declared: dict[tuple[str, str, str, str, str, int], tuple[str, dict[str, Any]]] = {}
    for row in rows:
        pins = row.get("source_pins")
        if not type(pins) is dict:
            continue
        for role, field in _GENERATION_FIELDS:
            reference = pins.get(field)
            if not type(reference) is dict:
                continue
            key = (
                role,
                str(reference.get("profile")),
                str(reference.get("store_id")),
                str(reference.get("generation_id")),
                str(reference.get("generation_sha256")),
                int(reference.get("capture_count", -1)),
            )
            declared.setdefault(key, (role, reference))
    return [
        declared[key]
        for key in sorted(declared, key=lambda item: (item[0], item[3]))
    ]


def _generation_state(
    closures: list[dict[str, Any]],
) -> dict[tuple[str, str, str], dict[str, Any]]:
    return {
        _generation_key(str(item["role"]), item): item for item in closures
    }


def _cap_refused_or_corrupt(
    observe: Callable[[], Any], *, cap: int, exc: Exception, label: str,
) -> bool:
    """An untyped exception cannot prove a bound was the sole failure.

    Conservatively refuse integrity qualification; an unrelated current HEAD
    over cap never authenticates historical bytes. Do not reread or retry.
    """
    raise MarketMemoryPopulationIntegrityError(label) from exc


def _require_pin_identity(
    pin: Any, reference: dict[str, Any], *, role: str
) -> None:
    observed = {
        "profile": getattr(pin, "profile", None),
        "store_id": getattr(pin, "store_id", None),
        "generation_id": getattr(pin, "generation_id", None),
        "generation_sha256": getattr(pin, "generation_sha256", None),
    }
    expected = {
        "profile": reference["profile"],
        "store_id": reference["store_id"],
        "generation_id": reference["generation_id"],
        "generation_sha256": reference["generation_sha256"],
    }
    if observed != expected or len(getattr(pin, "captures", ())) != int(
        reference["capture_count"]
    ):
        raise MarketMemoryPopulationIntegrityError(
            f"declared {role} generation identity differs from its owner store"
        )


def _close_trusted_capture(
    reader: trusted_store.TrustedFileAsKnownAtReader,
    pin_by_generation: dict[tuple[str, str, str], Any],
    *,
    row: dict[str, Any],
    states: dict[tuple[str, str, str], dict[str, Any]],
) -> dict[str, Any]:
    declared = row["source_pins"]["trusted_capture"]
    reference = row["source_pins"]["trusted_generation"]
    key = _generation_key("trusted", reference)
    closure = {
        "session": row["session"],
        "opportunity_id": row["opportunity_id"],
        "role": "trusted",
        "capture_id": str(declared.get("capture_id")),
        "context_id": declared.get("context_id"),
        "status": CAPTURE_ABSENT_STATUS,
        "reason": CAPTURE_ABSENT_REASON,
    }
    if states[key]["status"] != GENERATION_AUTHENTICATED_STATUS:
        closure["status"] = GENERATION_NOT_AUTHENTICATED_STATUS
        closure["reason"] = GENERATION_NOT_AUTHENTICATED_REASON
        return closure
    try:
        receipt = reader.read_pinned_capture_receipt(
            pin_by_generation[key], query_id=str(declared["query_id"])
        )
    except market_memory_pit.MarketMemoryContextNotFound:
        return closure
    except Exception as exc:
        raise MarketMemoryPopulationIntegrityError(
            "declared trusted capture is present and corrupt"
        ) from exc
    expected = {
        "capture_id": declared["capture_id"],
        "context_id": declared["context_id"],
        "packet_sha256": declared["packet_sha256"],
    }
    observed = {
        "capture_id": receipt.get("capture_id"),
        "context_id": receipt.get("context_id"),
        "packet_sha256": receipt.get("packet_sha256"),
    }
    snapshot = receipt.get("feature_snapshot")
    if type(snapshot) is dict:
        observed["feature_snapshot_id"] = snapshot.get("snapshot_id")
        observed["feature_content_sha256"] = snapshot.get("content_sha256")
        expected["feature_snapshot_id"] = declared["feature_snapshot_id"]
        expected["feature_content_sha256"] = declared["feature_content_sha256"]
    if observed != expected:
        raise MarketMemoryPopulationIntegrityError(
            "authenticated trusted capture differs from its declared reference"
        )
    closure["status"] = GENERATION_AUTHENTICATED_STATUS
    closure["reason"] = CAPTURE_AUTHENTICATED_REASON
    return closure


def _close_technical_capture(
    pin_by_generation: dict[tuple[str, str, str], Any],
    *,
    row: dict[str, Any],
    states: dict[tuple[str, str, str], dict[str, Any]],
) -> dict[str, Any]:
    declared = row["source_pins"]["technical_capture"]
    reference = row["source_pins"]["technical_generation"]
    key = _generation_key("technical", reference)
    closure = {
        "session": row["session"],
        "opportunity_id": row["opportunity_id"],
        "role": "technical",
        "capture_id": str(declared.get("capture_id")),
        "context_id": None,
        "status": CAPTURE_ABSENT_STATUS,
        "reason": CAPTURE_ABSENT_REASON,
    }
    if states[key]["status"] != GENERATION_AUTHENTICATED_STATUS:
        closure["status"] = GENERATION_NOT_AUTHENTICATED_STATUS
        closure["reason"] = GENERATION_NOT_AUTHENTICATED_REASON
        return closure
    pin = pin_by_generation[key]
    entry = next(
        (
            item
            for item in pin.captures
            if item.capture_id == declared["capture_id"]
        ),
        None,
    )
    if entry is None:
        return closure
    expected = {
        "session": declared["source_session"],
        "revision_id": declared["revision_id"],
        "source_observation_id": declared["source_observation_id"],
        "snapshot_id": declared["snapshot_id"],
        "first_observed_at": declared["first_observed_at"],
    }
    observed = {
        "session": entry.session,
        "revision_id": entry.revision_id,
        "source_observation_id": entry.source_observation_id,
        "snapshot_id": entry.snapshot_id,
        "first_observed_at": entry.first_observed_at,
    }
    if observed != expected:
        raise MarketMemoryPopulationIntegrityError(
            "authenticated technical capture differs from its declared reference"
        )
    closure["status"] = GENERATION_AUTHENTICATED_STATUS
    closure["reason"] = CAPTURE_AUTHENTICATED_REASON
    return closure


def _close_sources(
    *,
    rows: list[dict[str, Any]],
    trusted_root: str,
    technical_root: str,
    capture_cap: int,
) -> dict[str, Any]:
    """Close every included reference against its exact declared generation."""

    reader: trusted_store.TrustedFileAsKnownAtReader | None = None
    if _directory_exists(trusted_root):
        reader = trusted_store.TrustedFileAsKnownAtReader(trusted_root)
    technical_ready = _directory_exists(technical_root)
    declared_count: dict[tuple[str, str, str], int] = {}
    for row in rows:
        pins = row.get("source_pins")
        if not type(pins) is dict:
            continue
        for role, field in _GENERATION_FIELDS:
            reference = pins.get(field)
            if type(reference) is dict:
                key = _generation_key(role, reference)
                declared_count[key] = declared_count.get(key, 0) + 1
    generation_closures: list[dict[str, Any]] = []
    pin_by_generation: dict[tuple[str, str, str], Any] = {}
    for role, reference in _generation_refs(rows):
        key = _generation_key(role, reference)
        closure = {
            "role": role,
            "profile": str(reference["profile"]),
            "store_id": str(reference["store_id"]),
            "generation_id": str(reference["generation_id"]),
            "generation_sha256": str(reference["generation_sha256"]),
            "capture_count": int(reference["capture_count"]),
            "declared_by_session_count": declared_count[key],
            "status": STORE_ABSENT_STATUS,
            "reason": STORE_ABSENT_REASON,
        }
        generation_closures.append(closure)
        if role == "trusted":
            if reader is None:
                continue
            try:
                pin = reader.read_pinned_generation(
                    generation_id=str(reference["generation_id"]),
                    maximum_capture_count=capture_cap,
                )
            except market_memory_pit.MarketMemoryContextNotFound:
                closure["status"] = GENERATION_ABSENT_STATUS
                closure["reason"] = GENERATION_ABSENT_REASON
                continue
            except Exception as exc:
                if _cap_refused_or_corrupt(
                    reader.observe_generation_head,
                    cap=capture_cap,
                    exc=exc,
                    label="declared trusted owner generation is present and corrupt",
                ):
                    closure["status"] = CAP_REFUSED_STATUS
                    closure["reason"] = CAP_REFUSED_REASON
                continue
            _require_pin_identity(pin, reference, role=role)
            pin_by_generation[key] = pin
            closure["status"] = GENERATION_AUTHENTICATED_STATUS
            closure["reason"] = GENERATION_AUTHENTICATED_REASON
            continue
        if not technical_ready:
            continue
        try:
            pin = technical_store.pin_technical_actual_output_generation(
                technical_root,
                generation_id=str(reference["generation_id"]),
                maximum_capture_count=capture_cap,
            )
        except market_memory_pit.MarketMemoryContextNotFound:
            closure["status"] = GENERATION_ABSENT_STATUS
            closure["reason"] = GENERATION_ABSENT_REASON
            continue
        except Exception as exc:
            if _cap_refused_or_corrupt(
                lambda: technical_store.observe_technical_actual_output_generation_head(
                    technical_root
                ),
                cap=capture_cap,
                exc=exc,
                label=(
                    "declared technical owner generation is present and corrupt"
                ),
            ):
                closure["status"] = CAP_REFUSED_STATUS
                closure["reason"] = CAP_REFUSED_REASON
            continue
        _require_pin_identity(pin, reference, role=role)
        pin_by_generation[key] = pin
        closure["status"] = GENERATION_AUTHENTICATED_STATUS
        closure["reason"] = GENERATION_AUTHENTICATED_REASON
    states = _generation_state(generation_closures)
    capture_closures: list[dict[str, Any]] = []
    for row in rows:
        pins = row.get("source_pins")
        if not type(pins) is dict:
            continue
        if type(pins.get("trusted_capture")) is dict:
            capture_closures.append(
                _close_trusted_capture(
                    reader, pin_by_generation, row=row, states=states
                )
            )
        if type(pins.get("technical_capture")) is dict:
            capture_closures.append(
                _close_technical_capture(
                    pin_by_generation, row=row, states=states
                )
            )
    published = generation_closures + capture_closures
    retained = sum(
        1 for item in published if item["status"] != GENERATION_AUTHENTICATED_STATUS
    )
    if not published:
        status = "no_source_refs_declared"
    elif retained == 0:
        status = "complete"
    else:
        status = "retained_gaps"
    return {
        "capture_cap": capture_cap,
        "status": status,
        "generation_closures": generation_closures,
        "capture_closures": capture_closures,
        "retained_gap_count": retained,
        "component_source_receipts_authenticated": False,
    }


def _directory_exists(root: str) -> bool:
    try:
        return Path(root).is_dir() and not Path(root).is_symlink()
    except OSError:
        return False


def _row_qualification(
    rows: list[dict[str, Any]], closure: dict[str, Any]
) -> list[dict[str, Any]]:
    """Type capture availability, comparison eligibility and fit eligibility."""

    capture_status: dict[tuple[str, str], list[str]] = {}
    for item in closure["capture_closures"]:
        capture_status.setdefault(
            (item["session"], item["opportunity_id"]), []
        ).append(item["status"])
    generation_status = {
        _generation_key(str(item["role"]), item): item["status"]
        for item in closure["generation_closures"]
    }
    qualification: list[dict[str, Any]] = []
    for row in rows:
        pins = row.get("source_pins")
        if row["disposition"] == GAP_DISPOSITION or not type(pins) is dict:
            qualification.append(
                {
                    "session": row["session"],
                    "opportunity_id": row["opportunity_id"],
                    "capture_available": CAPTURE_AVAILABLE_NOT_APPLICABLE,
                    "capture_available_reason": NO_CAPTURE_REASON,
                    "comparison_eligibility": COMPARISON_NOT_APPLICABLE,
                    "comparison_eligibility_reason": NO_CAPTURE_REASON,
                    "fit_eligibility": False,
                    "fit_eligibility_reason": FIT_REASON,
                }
            )
            continue
        statuses = capture_status.get(
            (row["session"], row["opportunity_id"]), []
        )
        declared_captures = [
            pins[field] for _role, field in _CAPTURE_ROLES
            if type(pins.get(field)) is dict
        ]
        unqualified_generations = [
            status
            for role, field in _GENERATION_FIELDS
            if type(pins.get(field)) is dict
            for status in (
                generation_status.get(_generation_key(role, pins[field])),
            )
            if status != GENERATION_AUTHENTICATED_STATUS
        ]
        if unqualified_generations:
            available = CAPTURE_AVAILABLE_UNQUALIFIED
            available_reason = GENERATION_NOT_AUTHENTICATED_REASON
        elif any(
            item != GENERATION_AUTHENTICATED_STATUS for item in statuses
        ):
            available = CAPTURE_AVAILABLE_ABSENT
            available_reason = CAPTURE_ABSENT_REASON
        elif statuses:
            available = CAPTURE_AVAILABLE
            available_reason = CAPTURE_AUTHENTICATED_REASON
        else:
            available = CAPTURE_AVAILABLE_NOT_APPLICABLE
            available_reason = NO_CAPTURE_REASON
        if row["decision_state_projection"] is None:
            comparison = COMPARISON_PENDING
            comparison_reason = (
                "owner_row_declares_no_registered_feature_coordinates"
            )
        elif available != CAPTURE_AVAILABLE:
            comparison = COMPARISON_BLOCKED
            comparison_reason = (
                "exact_source_closure_is_not_authenticated_for_this_row"
            )
        elif declared_captures:
            comparison = COMPARISON_ELIGIBLE
            comparison_reason = COORDINATES_PRESENT_REASON
        else:
            comparison = COMPARISON_PENDING
            comparison_reason = (
                "owner_row_declares_no_qualified_capture_evidence"
            )
        qualification.append(
            {
                "session": row["session"],
                "opportunity_id": row["opportunity_id"],
                "capture_available": available,
                "capture_available_reason": available_reason,
                "comparison_eligibility": comparison,
                "comparison_eligibility_reason": comparison_reason,
                "fit_eligibility": False,
                "fit_eligibility_reason": FIT_REASON,
            }
        )
    return qualification


def _validate_manifest(value: dict[str, Any]) -> bytes:
    """Bind one canonical, bounded, content-addressed manifest body."""

    body = _canonical_bytes(value)
    if not body or len(body) > MAX_MANIFEST_BYTES:
        raise MarketMemoryPopulationError(
            "population manifest is empty or exceeds its canonical byte bound"
        )
    fields = {
        "schema", "manifest_id", "manifest_version", "owner", "census_basis",
        "through_session", "expected_sessions", "census", "membership",
        "source_closure", "audit", "eligibility", "claims", "authority",
    }
    if type(value) is not dict or set(value) != fields:
        raise MarketMemoryPopulationError(
            "population manifest fields are not canonical"
        )
    if value["schema"] != POPULATION_MANIFEST_SCHEMA:
        raise MarketMemoryPopulationError("population manifest schema mismatch")
    if value["manifest_id"] != _content_id(value, field="manifest_id"):
        raise MarketMemoryPopulationError(
            "population manifest ID does not bind its content"
        )
    return body


def build_population_manifest(
    repository_root: str | Path,
    *,
    experience_root: str | Path,
    trusted_root: str | Path,
    technical_root: str | Path,
    through_session: str,
    policy: object,
) -> dict[str, Any]:
    """Build one P0 outcome-blind W2C population census manifest.

    Rights authorization runs before any owner path is opened, again once the
    owner identities are authenticated, and once more before the manifest is
    disclosed.  Every owner read goes through the owner's public outcome-blind
    read seam and public owner generation readers.
    """

    repository = _require_root(repository_root, field="repository_root")
    experience = _require_root(experience_root, field="experience_root")
    trusted = _require_root(trusted_root, field="trusted_root")
    technical = _require_root(technical_root, field="technical_root")
    _require_session(through_session, field="declared through_session")
    if through_session not in FROZEN_PILOT_SESSION_SET:
        # Ordinary malformed input fails before any rights check or owner read.
        raise MarketMemoryPopulationError(
            "declared through-session is outside the frozen 126-session pilot"
        )

    # Rights layer first: no owner root, receipt or object may be opened yet.
    _require_grant(
        policy,
        repository_root=repository,
        experience_root=experience,
        through_session=through_session,
        registration_id=None,
        store_id=None,
    )

    ledger = accrual.read_outcome_blind_population_ledger(
        repository, experience_root=experience
    )
    _validate_ledger(ledger)
    registration_id = str(ledger["registration"]["registration_id"])
    store_id = str(ledger["store"]["store_id"])

    # Rights layer again, now bound to authenticated identities, before any
    # manifest disclosure is built.
    _require_grant(
        policy,
        repository_root=repository,
        experience_root=experience,
        through_session=through_session,
        registration_id=registration_id,
        store_id=store_id,
    )

    expected_sessions = list(ledger["calendar"]["expected_sessions"])
    declared_sessions = _declared_sessions(expected_sessions, through_session)
    rows_by_session = {row["session"]: row for row in ledger["rows"]}
    rows = [
        _census_row(session, rows_by_session.get(session))
        for session in declared_sessions
    ]
    counts = {
        "expected": len(declared_sessions),
        "recorded": sum(
            row["disposition"] != GAP_DISPOSITION for row in rows
        ),
        "admitted": sum(row["disposition"] == "admitted" for row in rows),
        "abstained": sum(row["disposition"] == "abstained" for row in rows),
        "missed": sum(row["disposition"] == "missed" for row in rows),
        "unrecorded": sum(
            row["disposition"] == GAP_DISPOSITION for row in rows
        ),
    }
    membership_body = {
        "schema": POPULATION_MEMBERSHIP_SCHEMA,
        "membership_version": 1,
        "registration_id": registration_id,
        "registration_sha256": ledger["registration"]["registration_sha256"],
        "census_basis": CENSUS_BASIS,
        "through_session": through_session,
        "expected_sessions": declared_sessions,
        "rows": rows,
    }
    membership = {
        "schema": POPULATION_MEMBERSHIP_SCHEMA,
        "membership_version": 1,
        "algorithm": "sha256_canonical_json_v1",
        "membership_sha256": _digest(_canonical_bytes(membership_body)),
        "excluded_identity_dimensions": list(MEMBERSHIP_EXCLUDED_DIMENSIONS),
    }
    population = ledger.get("population")
    closure = _close_sources(
        rows=rows,
        trusted_root=trusted,
        technical_root=technical,
        capture_cap=int(accrual.MAX_OWNER_GENERATION_CAPTURES),
    )
    qualification = _row_qualification(rows, closure)
    comparison = {
        "performed": False,
        "status": COMPARISON_STATUS,
        "reason": COMPARISON_REASON,
        "rows_with_registered_coordinates": sum(
            item["comparison_eligibility"] == COMPARISON_ELIGIBLE
            for item in qualification
        ),
        "rows_pending_coordinates": sum(
            item["comparison_eligibility"] == COMPARISON_PENDING
            for item in qualification
        ),
        "rows_blocked_by_source_qualification": sum(
            item["comparison_eligibility"] == COMPARISON_BLOCKED
            for item in qualification
        ),
        "rows_not_applicable": sum(
            item["comparison_eligibility"] == COMPARISON_NOT_APPLICABLE
            for item in qualification
        ),
    }
    authority = dict(market_memory.AUTHORITY)
    manifest: dict[str, Any] = {
        "schema": POPULATION_MANIFEST_SCHEMA,
        "manifest_id": "",
        "manifest_version": 1,
        "owner": {
            "owner_id": "W2C",
            "registration_id": registration_id,
            "registration_sha256": ledger["registration"][
                "registration_sha256"
            ],
            "store_id": store_id,
            "store_schema": ledger["store"]["store_schema"],
            "store_profile": ledger["store"]["store_profile"],
            "installation_id": ledger["store"]["installation_id"],
            "installation_writer_commit": ledger["store"][
                "installation_writer_commit"
            ],
        },
        "census_basis": CENSUS_BASIS,
        "through_session": through_session,
        "expected_sessions": declared_sessions,
        "census": {
            "counts": counts,
            "rows": rows,
            "gaps": [
                {"session": row["session"], "reason": GAP_REASON}
                for row in rows
                if row["disposition"] == GAP_DISPOSITION
            ],
        },
        "membership": membership,
        "source_closure": closure,
        "audit": {
            "population_receipt_id": (
                None
                if population is None
                else population["population_receipt_id"]
            ),
            "population_receipt_sha256": (
                None
                if population is None
                else population["population_receipt_sha256"]
            ),
            "population_receipt_bytes": (
                None
                if population is None
                else population["population_receipt_bytes"]
            ),
            "population_receipt_through_session": (
                None if population is None else population["through_session"]
            ),
            "population_observed_at": (
                None if population is None else population["observed_at"]
            ),
            "population_writer_commit": (
                None if population is None else population["writer_commit"]
            ),
            "population_complete": (
                None if population is None else population["complete"]
            ),
            "population_owner_generation_refs": (
                None
                if population is None
                else population["owner_generation_refs"]
            ),
            "membership_independent_of_audit": True,
        },
        "eligibility": {
            "capture_availability": {
                "authenticated": sum(
                    item["capture_available"] == CAPTURE_AVAILABLE
                    for item in qualification
                ),
                "absent_from_authenticated_generation": sum(
                    item["capture_available"] == CAPTURE_AVAILABLE_ABSENT
                    for item in qualification
                ),
                "generation_not_authenticated": sum(
                    item["capture_available"] == CAPTURE_AVAILABLE_UNQUALIFIED
                    for item in qualification
                ),
                "not_applicable": sum(
                    item["capture_available"] == CAPTURE_AVAILABLE_NOT_APPLICABLE
                    for item in qualification
                ),
            },
            "comparison": comparison,
            "fit": {
                "eligible": False,
                "reason": FIT_REASON,
                "training_eligible": False,
                "promotion_eligible": False,
                "authority": dict(authority),
            },
            "row_qualification": qualification,
        },
        "claims": {
            "registration_authenticated": True,
            "installation_authenticated": True,
            "ledger_rows_authenticated": True,
            "population_receipt_authenticated": population is not None,
            "source_closure_complete": closure["status"] == "complete",
            "membership_outcome_blind": True,
            "external_clock_authenticated": False,
            "aba_resistance_authenticated": False,
            "calendar_session_derivation_authenticated": True,
            "component_source_receipts_authenticated": False,
            "training_eligible": False,
            "promotion_eligible": False,
        },
        "authority": dict(authority),
    }
    manifest["manifest_id"] = _content_id(manifest, field="manifest_id")
    _validate_manifest(manifest)

    # Rights layer once more: nothing is disclosed unless this exact
    # registration/store disclosure is granted.
    _require_grant(
        policy,
        repository_root=repository,
        experience_root=experience,
        through_session=through_session,
        registration_id=registration_id,
        store_id=store_id,
    )
    return manifest


_POPULATION_TOKEN = object()


@dataclass(frozen=True, init=False)
class PopulationManifestCapability:
    """Owner-loaded process capability; disclosed JSON is not authority.

    Protects accidental forgery/mutation in a trusted application, not hostile
    Python execution. This is not an external signature or usage grant.
    """
    _body: bytes
    _digest: str
    _resource: bytes
    _seal: object

    def __init__(self, body: bytes, resource: bytes, *, _key: object = None):
        if _key is not _POPULATION_TOKEN:
            raise MarketMemoryPopulationError("owner_verified_population_capability_required")
        object.__setattr__(self, "_body", body)
        object.__setattr__(self, "_digest", _digest(body))
        object.__setattr__(self, "_resource", resource)
        object.__setattr__(self, "_seal", _POPULATION_TOKEN)


def read_population_manifest_capability(
    repository_root: str | Path, *, experience_root: str | Path,
    trusted_root: str | Path, technical_root: str | Path,
    through_session: str, policy: object,
) -> PopulationManifestCapability:
    """Mint after complete owner authentication and current disclosure rights."""
    value = build_population_manifest(
        repository_root, experience_root=experience_root, trusted_root=trusted_root,
        technical_root=technical_root, through_session=through_session, policy=policy,
    )
    resource = {
        "repository_root": _require_root(repository_root, field="repository_root"),
        "experience_root": _require_root(experience_root, field="experience_root"),
        "through_session": through_session,
        "registration_id": value["owner"]["registration_id"],
        "store_id": value["owner"]["store_id"],
    }
    return PopulationManifestCapability(
        _canonical_bytes(value), _canonical_bytes(resource), _key=_POPULATION_TOKEN
    )


def disclose_population_manifest(
    capability: PopulationManifestCapability, *, policy: object,
) -> dict[str, Any]:
    """Disclose detached frozen membership after checking current rights."""
    if (type(capability) is not PopulationManifestCapability
            or capability._seal is not _POPULATION_TOKEN
            or type(capability._body) is not bytes
            or len(capability._body) > MAX_MANIFEST_BYTES
            or _digest(capability._body) != capability._digest
            or type(capability._resource) is not bytes):
        raise MarketMemoryPopulationError("owner_verified_population_capability_required")
    _require_grant(policy, **json.loads(capability._resource))
    return json.loads(capability._body)


__all__ = [
    "CAPTURE_AVAILABLE",
    "CAPTURE_AVAILABLE_ABSENT",
    "CAPTURE_AVAILABLE_NOT_APPLICABLE",
    "CAPTURE_AVAILABLE_UNQUALIFIED",
    "CENSUS_BASIS",
    "FIT_REASON",
    "GAP_DISPOSITION",
    "GAP_REASON",
    "MAX_EXPECTED_SESSIONS",
    "MAX_MANIFEST_BYTES",
    "MarketMemoryPopulationAccessError",
    "MarketMemoryPopulationError",
    "MarketMemoryPopulationIntegrityError",
    "POPULATION_ACCESS_POLICY_VERSION",
    "POPULATION_MANIFEST_ID_PREFIX",
    "POPULATION_MANIFEST_PROFILE",
    "POPULATION_MANIFEST_SCHEMA",
    "POPULATION_MEMBERSHIP_SCHEMA",
    "PopulationAccessGrant",
    "PopulationAccessPolicy",
    "build_population_manifest",
    "PopulationManifestCapability",
    "read_population_manifest_capability",
    "disclose_population_manifest",
]
