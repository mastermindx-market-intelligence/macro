"""The saved-scenario monitor producer (SPEC_U2 §1 "U2-3").

A saved scenario a user never hears about again is a bookmark, not a monitor.
This producer is the enqueue-only projection that closes that gap — no new
analysis lifecycle, no scoring, no send (A7: notifications relay typed
outcomes only):

  - the subscription surface is the user's OWN saved row:
    ``engine.capital_structure.saved_scenario_store.read_all_service_side()``
    (the monitor is the one caller the store names for the unpartitioned
    read; every row is classified under that row's own user, and the only
    user id that ever leaves this module is the row's own);
  - the trigger inputs are the nightly's LOCAL published artifacts under
    ``root`` (``state_bundle.json``, ``capacity_inputs.json``,
    ``state_changes.json``), each independently absent-or-loaded — a missing
    state bundle is the outage SIGNAL (A39), never an error;
  - the queue is the existing ``alert_outbox`` (Terminal 0013); delivery
    belongs to the incumbent drain (``scripts/drain_alert_outbox.py``),
    never this module.

Per row the producer re-runs the restore offline — the SAME composition the
evaluate route owes, reached through ``assemble_scenario_inputs`` + the S0
composer alone (no HTTP, no API import) — and classifies it with
``engine.capital_structure.saved_scenarios.classify_restore``.  The offline
mirror keeps the restore route's own error table (``app.capital_structure``
``_restore_outcome_from_refusal``): a U1a 503 condition (no bindable state
generation, an absent inputs bundle, an unbindable rule pack) is
``source_outage``; the inputs-family refusal is ``inputs_unavailable``; an
issuer that left coverage or a body the served generation refuses is
``scenario_rejected``.  No second composition path is created and no outcome
outside the closed ``RESTORE_OUTCOMES`` vocabulary is ever minted.

Firing law: a row is planned only when the outcome is in ``FIRING_OUTCOMES``
AND ``(outcome, generation)`` differs from the row's stored
``last_outcome``/``last_outcome_generation_id`` — a repeated verdict on the
same generation is silence, and the alert_outbox UNIQUE(fire_event_id) plus a
pre-insert SELECT of the ids this run would mint is the FIF producer's
belt-and-braces dedupe.  ``fire_event_id`` is the FROZEN literal
concatenation (no hashing), and ``write_outcome`` lands only after that row's
enqueue actually succeeded — an outage night re-fires once per generation
gap and then stays quiet until the generation changes.

Payload: exactly the SPEC_U2 §1 "U2-3" fields — category, kind, saved and
issuer identity, the plain-guarded label, the two generation ids, the change
kinds and the restore link.  NO number is ever carried (a number without its
receipt is a recommendation surface); every glance-tier string obeys the
same banned-token discipline as the FIF producer, and a label that fails it
falls back to one fixed plain sentence.

Fail-soft: missing credentials/tables/inputs produce a typed unavailable
state with ZERO rows; this module never raises for a deployment reason and
never writes a local file.
"""
from __future__ import annotations

import json
import os
import uuid as _uuid_mod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from engine.alert_delivery_drain import (
    READ_OK,
    READ_OK_ZERO,
    READ_UNAVAILABLE,
    TypedRead,
)
from engine.capital_structure.issuer_state_contracts import ContractViolation
from engine.capital_structure.rule_applicability import load_rule_applicability_pack
from engine.capital_structure.scenario_composition import (
    ScenarioCompositionError,
    compose_scenario,
)
from engine.capital_structure.scenario_inputs import (
    BUNDLE_FAMILIES,
    CAPACITY_INPUTS_FILENAME,
    ScenarioInputsError,
    ScenarioInputsUnavailable,
    assemble_scenario_inputs,
)
from engine.capital_structure.capacity import CapacityInputError
from engine.capital_structure.funding import FundingInputError
from engine.capital_structure.saved_scenarios import (
    RESTORE_NOTES,
    RESTORE_OUTCOMES,
    RestoreOutcome,
    SavedScenario,
    classify_restore,
    restore_anchor,
)
from engine.capital_structure.saved_scenario_store import (
    read_all_service_side,
    write_outcome,
)
from engine.capital_structure.state_bundle import state_from_record
from engine.capital_structure.state_changes import (
    STATE_CHANGES_FILENAME,
    STATE_CHANGES_SCHEMA,
    StateChange,
    StateChangeSet,
    changes_for_issuer,
)

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://fsldfzlxyavsuwqbceod.supabase.co"
).rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
EVIDENCE_BASE = "https://www.mastermind-x.com"
SOURCE = "macro.capital_structure_saved_scenario_monitor"
CATEGORY = "cs_saved_scenario"
CHANNEL = "email"

#: Never fire on these: a family that was never available is not news, and
#: "nothing moved" is the monitor's most common honest answer.  A family that
#: WAS available and became unavailable arrives as a ``correction`` through
#: ``input_support_changed`` — never as a fourth channel here.
FIRING_OUTCOMES = ("correction", "new_events", "source_outage")

CS_PAGE = "capital_structure.html"
STATE_BUNDLE_FILENAME = "state_bundle.json"

#: The fixed plain sentence a label falls back to when it fails the glance
#: guard.  No digit, no banned token, no advisory vocabulary.
_LABEL_FALLBACK = "A saved scenario has a new status"

# Glance-tier banned tokens — the FIF producer's discipline
# (engine/fif_saved_research_notifications.py).  The mailer applies its own
# wider list at render time; this guards what we PERSIST.
_BANNED_TERMS = ("falsif", "refut", "证伪")

# A fixed, arbitrary namespace UUID for synthesizing alert_outbox.alert_id
# values (uuid5) from the conceptual "cs_saved_scenario:<user_id>" identity —
# the FIF producer's pattern with its OWN namespace: one stable synthetic
# alert_id per user across every saved-scenario event they receive.  Never
# change this constant — doing so would re-mint every user's id, and it is
# deliberately distinct from the FIF and thesis-monitor namespaces.
_ALERT_ID_NAMESPACE = _uuid_mod.UUID("5c2e8a41-6b39-4d07-92f4-1a83c6e05b47")


@dataclass(frozen=True)
class TypedTriggerInputs:
    """Local published artifacts, each independently absent-or-loaded."""

    state_doc: dict | None = None
    inputs_doc: dict | None = None
    changes_doc: dict | None = None
    state_state: str = READ_UNAVAILABLE
    inputs_state: str = READ_UNAVAILABLE
    changes_state: str = READ_UNAVAILABLE


@dataclass(frozen=True)
class ProducerPlan:
    """The rows this run WOULD enqueue, with the run's honest counts.

    Each entry pairs the alert_outbox row with the row identity, the outcome
    that minted it and the generation the row's outcome write will name, so
    the enqueue loop can order ``write_outcome`` after its own success only.
    """

    entries: list[tuple[dict, str, str, str]]
    rows_n: int
    candidates_n: int
    duplicate_n: int
    unreadable_n: int


@dataclass(frozen=True)
class ProducerResult:
    """The FIF producer's result shape over this lane's own counters."""

    outcome: str
    read_state: str
    error_class: str | None
    rows_n: int
    classified_n: int
    planned_n: int
    enqueued_n: int
    duplicate_n: int
    unreadable_n: int
    state_state: str
    inputs_state: str
    changes_state: str
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pure functions — no IO
# ---------------------------------------------------------------------------

def fire_event_id(
    *, saved_id: str, outcome: str, to_generation_id: str, user_id: str
) -> str:
    """The FROZEN dedupe key (SPEC_U2 §1 "U2-3"): literal concatenation, no
    hashing.  UNIQUE(fire_event_id) makes replays no-ops."""
    return f"cs_saved_scenario|{saved_id}|{outcome}|{to_generation_id}|{user_id}"


def synthetic_alert_id(user_id: str) -> str:
    """Deterministic per-user synthetic ``alert_outbox.alert_id`` (uuid5 of the
    conceptual "cs_saved_scenario:<user_id>" identity under this lane's own
    namespace).  Stable across every event produced for the same user."""
    return str(_uuid_mod.uuid5(_ALERT_ID_NAMESPACE, f"cs_saved_scenario:{user_id}"))


def _plain(text: Any, fallback: str) -> str:
    """Banned-token guard for every glance-tier string this module persists —
    mirrors app/mailer.py's fallback semantics via the FIF producer's shape."""
    value = str(text or "")
    if not value or any(term in value for term in _BANNED_TERMS):
        return fallback
    return value


def _label_plain(text: Any) -> str:
    """The saved label as the email may carry it: the banned-token guard, AND
    the no-number law — a label carrying any digit is exactly the "number
    without its receipt" surface, so it falls back to the fixed plain
    sentence rather than being sent verbatim."""
    value = _plain(text, _LABEL_FALLBACK)
    if any(character.isdigit() for character in value):
        return _LABEL_FALLBACK
    return value


def evidence_url(
    issuer_id: str, saved_id: str, evidence_base: str = EVIDENCE_BASE
) -> str:
    return (
        f"{evidence_base.rstrip('/')}/{CS_PAGE}"
        f"?issuer={issuer_id}&saved={saved_id}"
    )


def compose_payload(
    outcome: RestoreOutcome,
    saved: SavedScenario,
    *,
    evidence_base: str = EVIDENCE_BASE,
) -> dict:
    """Exactly the SPEC_U2 §1 "U2-3" payload fields — and nothing else.

    ``kind`` is the closed restore outcome; ``label`` passes the glance guard
    with one fixed fallback; ``change_kinds`` is the closed change vocabulary.
    No number, no score, no recommendation surface anywhere in the email —
    the email says what changed and links to the restore.
    """
    return {
        "category": CATEGORY,
        "kind": outcome.outcome,
        "saved_id": saved.saved_id,
        "issuer_id": saved.issuer_id,
        "label": _label_plain(saved.label),
        "from_generation_id": outcome.from_generation_id,
        "to_generation_id": outcome.to_generation_id,
        "change_kinds": list(outcome.change_kinds),
        "evidence_url": evidence_url(saved.issuer_id, saved.saved_id, evidence_base),
    }


# ---------------------------------------------------------------------------
# Local published artifacts — the trigger reads
# ---------------------------------------------------------------------------

def _read_json(path: Path) -> dict | None:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return doc if isinstance(doc, dict) else None


def load_trigger_inputs(root: str | Path) -> TypedTriggerInputs:
    """Local-only reads of the nightly's published generation.  Each artifact
    is independently absent-or-loaded; absence is a typed state, not an error.
    A missing state bundle is the outage signal itself (A39)."""
    root_path = Path(root)
    state_doc = _read_json(root_path / STATE_BUNDLE_FILENAME)
    inputs_doc = _read_json(root_path / CAPACITY_INPUTS_FILENAME)
    changes_doc = _read_json(root_path / STATE_CHANGES_FILENAME)
    return TypedTriggerInputs(
        state_doc=state_doc,
        inputs_doc=inputs_doc,
        changes_doc=changes_doc,
        state_state=READ_OK if state_doc is not None else READ_UNAVAILABLE,
        inputs_state=READ_OK if inputs_doc is not None else READ_UNAVAILABLE,
        changes_state=READ_OK if changes_doc is not None else READ_UNAVAILABLE,
    )


def _changeset_of(doc: Any) -> StateChangeSet | None:
    """Rebuild the published ledger through the contract constructors, or
    ``None`` when it does not reconstruct — an unreadable ledger classifies
    nothing honestly and is never guessed into a change."""
    if not isinstance(doc, Mapping) or doc.get("schema") != STATE_CHANGES_SCHEMA:
        return None
    try:
        changes = tuple(
            StateChange(**{str(key): value for key, value in row.items() if key != "change_id"})
            for row in doc.get("changes") or ()
            if isinstance(row, Mapping)
        )
        return StateChangeSet(
            from_generation_id=doc.get("from_generation_id"),
            to_generation_id=str(doc.get("to_generation_id")),
            from_as_of=doc.get("from_as_of"),
            to_as_of=str(doc.get("to_as_of")),
            baseline=bool(doc.get("baseline")),
            changes=changes,
            generated_at=str(doc.get("generated_at")),
        )
    except (ContractViolation, ValueError, TypeError, KeyError, AttributeError):
        return None


def _usable_changeset(
    changes_doc: Any, saved_generation_id: Any, served_generation_id: str | None
) -> StateChangeSet | None:
    """The retained ledger, but ONLY when it spans exactly saved→served — the
    restore route's own ``_usable_ledger`` law.  A ledger between other
    generations classifies nothing honestly; an absent or unreadable one is
    context the classification answers without."""
    if not saved_generation_id or served_generation_id is None:
        return None
    changeset = _changeset_of(changes_doc)
    if changeset is None:
        return None
    if changeset.from_generation_id != saved_generation_id:
        return None
    if changeset.to_generation_id != served_generation_id:
        return None
    return changeset


# ---------------------------------------------------------------------------
# The offline restore — the evaluate route's composition, no API import
# ---------------------------------------------------------------------------

def _issuer_state_record(bundle: Mapping[str, Any], issuer_id: str) -> Mapping[str, Any] | None:
    for row in bundle.get("issuers") or ():
        if (
            isinstance(row, Mapping)
            and str((row.get("request") or {}).get("issuer_id") or "") == issuer_id
        ):
            return row
    return None


def _rule_pack() -> Any | None:
    """The pack every served rule status is read from, or ``None`` when this
    checkout cannot load it — the API answers 503 for that state, so the
    offline mirror classifies it as an outage rather than composing with a
    pack the served generation was not built under."""
    try:
        return load_rule_applicability_pack()
    except Exception:  # noqa: BLE001 — a typed outage, never a crash
        return None


def _pack_binds(bundle: Mapping[str, Any], pack: Any) -> bool:
    identity = bundle.get("rule_pack") or {}
    return (
        isinstance(identity, Mapping)
        and identity.get("rule_pack_id") == pack.rule_pack_id
        and identity.get("rule_pack_digest") == pack.file_sha256
    )


class _ScenarioRefused(Exception):
    """The served engine refuses the restore anchor (the route's 409/422)."""


def _recompose(
    saved: SavedScenario,
    *,
    bundle: Mapping[str, Any],
    inputs_doc: Mapping[str, Any],
    pack: Any,
) -> tuple[Any, Any, Any]:
    """``(state, scenario, result)`` for one saved row against the served
    generation — the SAME anchor (:func:`restore_anchor`, which rebases a
    ``current``/``scenario`` save to the served as_of and keeps a
    ``then_known`` save verbatim), ``assemble_scenario_inputs`` and S0
    composer the restore route runs, offline.

    Raises :class:`ContractViolation` when the saved body no longer
    reconstructs (the route's rejected restore), :class:`ScenarioInputsError`
    for a bundle conflict (the route's inputs 409) and
    :class:`_ScenarioRefused` for every other refusal of the anchor (the
    route's composition 409 or as_of/capacity/funding 422)."""
    state = state_from_record(_issuer_state_record(bundle, saved.issuer_id))
    served_as_of = str(state.request.as_of)
    scenario = restore_anchor(saved, served_as_of)
    then_known = str(saved.view.get("mode") or "") == "then_known"
    if not then_known and scenario.as_of != served_as_of:
        raise _ScenarioRefused("scenario_as_of_mismatch")
    # A then_known anchor keeps its own cutoff as_of.  The route re-derives the
    # then-known state at that cutoff (its as_of IS the cutoff), so its as_of
    # check passes and the inputs bundle decides: after a nightly the bundle
    # as_of has moved and assembly raises ScenarioInputsError (inputs
    # unavailable), exactly as below.  Offline the monitor holds no verified
    # projection generation to re-derive the then-known state, so when the
    # bundle as_of still equals the cutoff it composes against the served
    # state at that same as_of: the one documented approximation.
    assembled = assemble_scenario_inputs(
        inputs_doc,
        saved.issuer_id,
        scenario.as_of,
        served_state_generation_id=str(bundle["generation_id"]),
    )
    if isinstance(assembled, ScenarioInputsUnavailable):
        return state, scenario, assembled
    try:
        result = compose_scenario(
            state,
            assembled.instruments,
            assembled.basis,
            assembled.financials,
            assembled.commitments,
            scenario,
            assembled.rules,
            pack=pack,
        )
    except (ScenarioCompositionError, CapacityInputError, FundingInputError) as exc:
        raise _ScenarioRefused(str(exc)) from exc
    return state, scenario, result


def _restore_outcome_for(
    saved: SavedScenario,
    *,
    bundle: Mapping[str, Any] | None,
    inputs_doc: Mapping[str, Any] | None,
    pack: Any,
    changeset: StateChangeSet | None,
) -> RestoreOutcome:
    """Classify one saved row exactly the way the restore route would.

    The order is the route's own: a U1a 503 condition first (no bindable
    state generation, an unbindable rule pack, an absent inputs bundle), the
    inputs-family 409 second, then the composed answer.  An issuer whose
    record the served bundle no longer carries is the route's 404 — the
    saved scenario failing to produce its answer under the served
    generation: ``scenario_rejected``.  Identity drift is never caught into
    an outcome: it is a bug, raised.
    """
    state_generation_id = str(bundle["generation_id"]) if bundle is not None else None
    inputs_generation_id = (
        str(inputs_doc["generation_id"]) if inputs_doc is not None else None
    )

    def _rejected() -> RestoreOutcome:
        return classify_restore(
            saved,
            state_generation_id=state_generation_id,
            inputs_generation_id=inputs_generation_id,
            current_result=None,
            unavailable=None,
            state_unavailable=False,
            scenario_rejected=True,
            changes=changeset,
        )

    if bundle is None:
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
    if _issuer_state_record(bundle, saved.issuer_id) is None:
        return _rejected()
    if pack is None or not _pack_binds(bundle, pack):
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
    if inputs_doc is None:
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
    try:
        state, scenario, outcome = _recompose(
            saved, bundle=bundle, inputs_doc=inputs_doc, pack=pack
        )
    except ScenarioInputsError as exc:
        # a bundle conflict (another as_of after a nightly, an unknown issuer):
        # every family unavailable with the engine's own message, as the route.
        return classify_restore(
            saved,
            state_generation_id=state_generation_id,
            inputs_generation_id=inputs_generation_id,
            current_result=None,
            unavailable=ScenarioInputsUnavailable(
                {
                    family: {"support": "unavailable", "reason_codes": [str(exc)]}
                    for family in BUNDLE_FAMILIES
                },
                (),
            ),
            state_unavailable=False,
            scenario_rejected=False,
            changes=changeset,
        )
    except _ScenarioRefused:
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
    except (ContractViolation, ValueError, TypeError):
        # ScenarioInputsError subclasses ContractViolation, so this clause
        # comes after it: the saved body no longer reconstructs under the
        # served contract — the rejected restore.
        return _rejected()
    if isinstance(outcome, ScenarioInputsUnavailable):
        return classify_restore(
            saved,
            state_generation_id=state_generation_id,
            inputs_generation_id=inputs_generation_id,
            current_result=None,
            unavailable=outcome,
            state_unavailable=False,
            scenario_rejected=False,
            changes=changeset,
        )
    return classify_restore(
        saved,
        state_generation_id=state_generation_id,
        inputs_generation_id=inputs_generation_id,
        current_result=outcome.as_record(),
        unavailable=None,
        state_unavailable=False,
        scenario_rejected=False,
        changes=changeset,
        current_scenario_id=scenario.scenario_id,
        current_as_of=str(state.request.as_of),
    )


# ---------------------------------------------------------------------------
# Planning — one candidate row per (saved row, firing transition)
# ---------------------------------------------------------------------------

def _saved_of_row(row: Mapping[str, Any]) -> SavedScenario:
    """Rebuild the stored row's contract record.  ``last_outcome`` is read
    from the row's own columns first — the monitor's ``write_outcome`` is
    what maintains them — falling back to the record the row was saved with."""
    raw = row.get("record")
    record = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(record, Mapping):
        raise ContractViolation("saved_scenario.record: a stored record object is required")
    user_id = str(record.get("user_id") or "")
    if str(row.get("user_id") or "") != user_id:
        raise ContractViolation("saved_scenario.record: user_id does not bind its row")
    last_outcome = row.get("last_outcome")
    if last_outcome is None:
        last_outcome = record.get("last_outcome")
    last_generation = row.get("last_outcome_generation_id")
    if last_generation is None:
        last_generation = record.get("last_outcome_generation_id")
    return SavedScenario(
        **{
            str(key): value
            for key, value in record.items()
            if str(key) not in ("schema", "saved_id", "last_outcome", "last_outcome_generation_id")
        },
        last_outcome=last_outcome,
        last_outcome_generation_id=last_generation,
    )


def _plan(
    *,
    saved_rows: list[Mapping[str, Any]],
    bundle: Mapping[str, Any] | None,
    inputs_doc: Mapping[str, Any] | None,
    pack: Any,
    changes_doc: Any,
    evidence_base: str,
) -> ProducerPlan:
    """One candidate entry per saved row whose classified outcome fires on a
    NEW (outcome, generation) transition.  Everything else — a non-firing
    outcome, a repeated verdict, a row that no longer reconstructs, an
    unreadable row — plans nothing and is counted instead."""
    served_generation_id = str(bundle["generation_id"]) if bundle is not None else None
    entries: list[tuple[dict, str, str, str]] = []
    rows_n = len(saved_rows)
    classified_n = 0
    unreadable_n = 0
    for row in saved_rows:
        if not isinstance(row, Mapping):
            unreadable_n += 1
            continue
        try:
            saved = _saved_of_row(row)
        except (ContractViolation, ValueError, TypeError, KeyError):
            # A row that no longer reconstructs is the typed
            # ``scenario_rejected`` outcome on the route — never a fire, and
            # never a crash for the rows behind it.
            classified_n += 1
            continue
        try:
            changeset = _usable_changeset(
                changes_doc, saved.state_generation_id, served_generation_id
            )
            outcome = _restore_outcome_for(
                saved,
                bundle=bundle,
                inputs_doc=inputs_doc,
                pack=pack,
                changeset=changeset,
            )
        except ContractViolation:
            # Identity drift on unchanged generations is a bug, never an
            # outcome: counted, noted, never planned, never fatal to the run.
            unreadable_n += 1
            continue
        classified_n += 1
        if outcome.outcome not in FIRING_OUTCOMES:
            continue
        anchor = outcome.to_generation_id or saved.state_generation_id
        if (outcome.outcome, anchor) == (saved.last_outcome, saved.last_outcome_generation_id):
            continue
        user_id = saved.user_id
        entries.append(
            (
                {
                    "user_id": user_id,
                    "alert_id": synthetic_alert_id(user_id),
                    "fire_event_id": fire_event_id(
                        saved_id=saved.saved_id,
                        outcome=outcome.outcome,
                        to_generation_id=anchor,
                        user_id=user_id,
                    ),
                    "channel": CHANNEL,
                    "status": "pending",
                    "attempts": 0,
                    "payload": compose_payload(outcome, saved, evidence_base=evidence_base),
                },
                saved.saved_id,
                outcome.outcome,
                anchor,
            )
        )
    return ProducerPlan(
        entries=entries,
        rows_n=rows_n,
        candidates_n=classified_n,
        duplicate_n=0,
        unreadable_n=unreadable_n,
    )


# ---------------------------------------------------------------------------
# IO functions — isolated, monkeypatched in tests. urllib is imported LAZILY
# so importing this module never loads an HTTP client (P1).
# ---------------------------------------------------------------------------

def _pg(method: str, path: str, body: Any = None, prefer: str | None = None, timeout: int = 6):
    import urllib.request  # noqa: PLC0415 — lazy by design (P1)

    url = f"{SUPABASE_URL}/rest/v1/{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def read_existing_fire_ids(ids: list[str]) -> TypedRead:
    """The pre-insert SELECT over alert_outbox for exactly the ids this run
    would mint (the FIF producer's dedupe belt)."""
    if not ids:
        return TypedRead(READ_OK_ZERO, [])
    import urllib.parse  # noqa: PLC0415 — lazy (P1)

    all_rows: list[dict] = []
    for chunk in _chunks([str(i) for i in ids], 100):
        in_list = ",".join(urllib.parse.quote(c, safe="") for c in chunk)
        path = f"alert_outbox?fire_event_id=in.({in_list})&select=fire_event_id"
        try:
            rows = _pg("GET", path)
        except Exception:  # noqa: BLE001 — the UNIQUE index is the backstop
            return TypedRead(READ_UNAVAILABLE, None, "unknown")
        all_rows.extend(rows or [])
    return TypedRead(READ_OK if all_rows else READ_OK_ZERO, all_rows)


def enqueue(
    entries: list[tuple[dict, str, str, str]], *, dry_run: bool
) -> tuple[list[str | None], str | None]:
    """Insert-or-ignore on fire_event_id: a 409/23505 replay is a no-op
    (UNIQUE backstop), never an error.

    Returns one status per entry — ``None`` when that row's POST succeeded,
    ``"duplicate"`` when the UNIQUE index absorbed a replay — plus the error
    class that stopped the loop (``None`` when it ran to completion).  A dry
    run performs no call at all and marks nothing.
    """
    import urllib.error  # noqa: PLC0415 — lazy by design (P1)

    statuses: list[str | None] = []
    if dry_run:
        return statuses, None
    for row, _saved_id, _outcome, _generation in entries:
        try:
            _pg("POST", "alert_outbox", body=row, prefer="return=minimal")
            statuses.append(None)
        except urllib.error.HTTPError as exc:
            code = getattr(exc, "code", None)
            body = ""
            try:
                body = exc.read().decode("utf-8", "ignore")
            except Exception:  # noqa: BLE001
                pass
            if code == 409 or "23505" in body:
                statuses.append("duplicate")
                continue
            if code == 400 or "23502" in body:
                statuses.append("schema_mismatch")
                return statuses, "schema_mismatch"
            statuses.append(f"http_{code}")
            return statuses, f"http_{code}"
        except Exception:  # noqa: BLE001 — typed, never raised to the caller
            statuses.append("unknown")
            return statuses, "unknown"
    return statuses, None


def _enqueue_and_record(
    entries: list[tuple[dict, str, str, str]], *, dry_run: bool
) -> tuple[int, int, int, str | None]:
    """Enqueue, then ``write_outcome`` for each row whose OWN enqueue
    succeeded — never before, never for a duplicate, and nothing at all on a
    dry run.  Returns ``(enqueued, duplicates, written, error_class)``."""
    statuses, error_class = enqueue(entries, dry_run=dry_run)
    enqueued = sum(1 for status in statuses if status is None)
    duplicates = sum(1 for status in statuses if status == "duplicate")
    written = 0
    if dry_run:
        return (enqueued, duplicates, written, error_class)
    for (_row, saved_id, outcome, generation), status in zip(entries, statuses):
        if status is not None:
            continue
        write = write_outcome(saved_id, outcome, generation)
        if write.state == "ok":
            written += 1
    return (enqueued, duplicates, written, error_class)


def run(
    *,
    root: str | Path = ".",
    dry_run: bool = True,
    evidence_base: str = EVIDENCE_BASE,
) -> ProducerResult:
    saved_read = read_all_service_side()
    if saved_read.state == READ_UNAVAILABLE:
        return ProducerResult(
            outcome="unavailable", read_state=saved_read.state,
            error_class=saved_read.error_class, rows_n=0, classified_n=0,
            planned_n=0, enqueued_n=0, duplicate_n=0, unreadable_n=0,
            state_state=READ_UNAVAILABLE, inputs_state=READ_UNAVAILABLE,
            changes_state=READ_UNAVAILABLE,
        )
    saved_rows = [row for row in saved_read.rows or [] if isinstance(row, Mapping)]
    arts = load_trigger_inputs(root)
    notes: list[str] = []
    pack = _rule_pack()
    if pack is None:
        notes.append("rule applicability pack unloadable — classified as an outage")
    probe = _plan(
        saved_rows=saved_rows,
        bundle=arts.state_doc,
        inputs_doc=arts.inputs_doc,
        pack=pack,
        changes_doc=arts.changes_doc,
        evidence_base=evidence_base,
    )
    existing_read = read_existing_fire_ids(
        [entry[0]["fire_event_id"] for entry in probe.entries]
    )
    existing_ids = (
        {str(row.get("fire_event_id")) for row in existing_read.rows or []}
        if existing_read.state != READ_UNAVAILABLE
        else set()
    )
    if existing_read.state == READ_UNAVAILABLE:
        notes.append(
            f"existing_fire_ids unreadable ({existing_read.error_class}) — "
            "enqueue relies on UNIQUE alone"
        )
    entries = [
        (row, saved_id, outcome, generation)
        for row, saved_id, outcome, generation in probe.entries
        if row["fire_event_id"] not in existing_ids
    ]
    duplicate_n = len(probe.entries) - len(entries)
    enqueued_n, enqueue_duplicates, written_n, error_class = _enqueue_and_record(
        entries, dry_run=dry_run
    )
    if error_class is not None:
        notes.append(f"enqueue stopped early ({error_class})")
    return ProducerResult(
        outcome="ok" if error_class is None else "partial",
        read_state=READ_OK,
        error_class=error_class,
        rows_n=probe.rows_n,
        classified_n=probe.candidates_n,
        planned_n=len(entries),
        enqueued_n=enqueued_n,
        duplicate_n=duplicate_n + enqueue_duplicates,
        unreadable_n=probe.unreadable_n,
        state_state=arts.state_state,
        inputs_state=arts.inputs_state,
        changes_state=arts.changes_state,
        notes=notes,
    )


__all__ = [
    "CATEGORY",
    "CHANNEL",
    "FIRING_OUTCOMES",
    "SOURCE",
    "ProducerPlan",
    "ProducerResult",
    "compose_payload",
    "enqueue",
    "evidence_url",
    "fire_event_id",
    "load_trigger_inputs",
    "read_existing_fire_ids",
    "run",
    "synthetic_alert_id",
]
