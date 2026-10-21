"""Bounded access-history semantics used by the installed E0 owner.

This validates supplied metadata, not its origin or current selection. Only the
installed owner may load the current private selected chain and supply its own
clock. A hash-linked list from a caller cannot grant access, reset reservations,
prove reviewer independence, or establish that no later revocation exists.
ReservationStore remains the authority for actual consumed/reserved looks;
these records describe policy history, not a second reservation ledger.
"""
from __future__ import annotations

import hashlib

from . import market_memory_contextual_registration as control
from .market_memory_e0_reservations import MAX_LOOKS

MAX_ACCESS_RECORDS = 1025
MAX_ACCESS_HISTORY_BYTES = 8 * 1024 * 1024
_BOUND_FIELDS = (
    "study_id", "installation_id", "installation_epoch", "access_state_id",
    "registration_ref", "publication_ref", "owner_principal_ref", "scope_ref",
)


class E0AccessHistoryError(ValueError):
    """Stable reason only; no caller values or private record bodies."""


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise E0AccessHistoryError(reason)


def validate_access_history(*, installation: object, history: object, as_of: str) -> dict:
    """Validate one complete chronological chain against its installation.

    Exact canonical bytes preserve every predecessor reference. Time is an
    explicit diagnostic input here; production must use current owner time.
    Revocation, exhaustion and contamination cannot be undone within an epoch.
    Incomplete/malformed history refuses instead of treating its newest row as
    evidence of current permission. The returned summary grants no actions.
    """
    bound = control.validate_e0_control_record(installation, kind="installed_binding")
    now = control._clock(as_of)
    _require(control._clock(bound["installed_at"]) <= now < control._clock(bound["expires_at"]),
             "installation_clock_or_expiry")
    _require(type(history) is list and 1 <= len(history) <= MAX_ACCESS_RECORDS,
             "bounded_access_history_required")
    _require(all(type(body) is bytes and 0 < len(body) <= control.MAX_CONTROL_BYTES
                 for body in history), "bounded_access_record_bytes_required")
    _require(sum(map(len, history)) <= MAX_ACCESS_HISTORY_BYTES, "access_history_byte_limit")
    previous = None
    previous_ref = None
    initial = None
    latest_ref = None
    for index, body in enumerate(history):
        state = control.parse_e0_control_record(body, kind="access_state")
        _require(state["sequence"] == index, "access_sequence_gap")
        _require(state["previous_state_ref"] == previous_ref, "access_predecessor_mismatch")
        _require(all(state[key] == bound[key] for key in _BOUND_FIELDS if key != "scope_ref"),
                 "access_installation_binding_mismatch")
        recorded = control._clock(state["recorded_at"])
        _require(control._clock(bound["installed_at"]) <= recorded <= now,
                 "access_clock_order")
        budget = state["budget"]
        used = budget["consumed_looks"] + budget["reserved_looks"]
        _require(budget["maximum_looks"] <= MAX_LOOKS, "unsupported_owner_look_budget")
        if previous is None:
            _require(used == 0, "initial_access_budget_not_empty")
            initial = state
        else:
            _require(all(state[key] == initial[key] for key in _BOUND_FIELDS),
                     "access_epoch_binding_changed")
            _require(recorded >= control._clock(previous["recorded_at"]), "access_clock_order")
            old_budget = previous["budget"]
            _require(budget["maximum_looks"] == old_budget["maximum_looks"],
                     "access_budget_limit_changed")
            _require(budget["consumed_looks"] >= old_budget["consumed_looks"]
                     and used >= old_budget["consumed_looks"] + old_budget["reserved_looks"],
                     "access_look_refund")
            # Revoking an already exhausted epoch tightens its policy. Neither
            # terminal state can return to active, and revocation is final.
            rank = {"active": 0, "exhausted": 1, "revoked": 2}
            _require(rank[state["status"]] >= rank[previous["status"]],
                     "terminal_access_state_changed")
            _require(previous["contamination_state"] != "contaminated"
                     or state["contamination_state"] == "contaminated",
                     "contamination_state_reversed")
        latest_ref = {"schema": control.SCHEMAS["access_state"],
                      "object_id": state["access_state_id"],
                      "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
        previous, previous_ref = state, latest_ref
    return {"schema": "research_factory.market_memory_e0_access_history_consistency.v1",
            "authority": "display_only", "study_id": bound["study_id"],
            "installation_id": bound["installation_id"],
            "installation_epoch": bound["installation_epoch"],
            "records": len(history), "selected_state_ref": latest_ref,
            "status": previous["status"], "contamination_state": previous["contamination_state"],
            "declared_budget": dict(previous["budget"]),
            "metadata_consistent": True, "current_selection_authenticated": False,
            "actual_reservation_accounting_verified": False, "operational_admission": False}
