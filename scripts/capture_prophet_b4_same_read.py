"""Capture-only nightly decision-time stamps for Prophet B4 same-read entry.

ZERO AUTHORITY. This script is the first production-shaped caller of the merged
B4 runtime library (#7581 sources adapter, #7738 entry policy, #9945 same-read
composition).  For every current US candidate it calls the accepted same-read
entry point — ``engine.prophet_b4_same_read.evaluate_same_read_entry_availability``
— through the ONE registered strategy definition, and appends the decision-time
facts it returns to an append-only JSONL stream under the incumbent prospective
evaluation root.  It runs off the render path.  It changes no page, plan, grade
or rank, invents no geometry/metric/NBBO/alias fact, reads no outcome, and
NOTHING downstream may read the stream it appends to (the consumer fence is
pinned by ``tests/test_capture_prophet_b4_same_read.py``).  The preregistration
owns the law (``research/prophet_v4/B4_ENTRY_POLICY_CALIBRATION_PREREG_2026-09-23.md``):
extend the existing prospective evaluation path with append-only decision-time
stamps, never create a new outcome authority — and the first run is
capture-only.  At BASE every row is honestly ``UNAVAILABLE_DATA`` with the
owners' typed reasons; that census IS the deliverable.

NIGHTLY IS THE SOLE ADVANCER (W3 + B01 discipline).  Durable appends happen
only with ``--nightly`` AND ``engine.ledger_lane.nightly_advance_enabled()``
(``COLLECT_LANE=nightly``); any other invocation is report mode — rows are
built and printed, nothing is written, no directory is created.  Outside the
lane the script refuses with a typed message and exit code 3 BEFORE any store
read.  ``--nightly --dry-run`` is the no-write preview of the nightly shape: it
is not lane-gated, builds every row, prints the run document and writes nothing
(no file, no directory).  ``stamp_date`` is the committed board as_of
(``engine.us_prophet_w3.resolve_board_as_of``) — never wall-clock, run id or
Pages — and ``captured_at`` is the writer's own UTC clock, stamped once per
run.  Owner inputs are never guessed: the native live root is the publishers'
fixed constant (report mode may override it for inspection; ``--nightly`` may
not), the alias table is the Data OS reader ``lib.dataos.identity.VendorAliasTable``
over the committed ``data/reference/vendor_aliases.parquet`` (the estate's ONLY
identity reader, loaded through the same intake snapshot the B1 generation uses;
absent reference -> unbound -> the adapter's typed ``IDENTITY_ALIAS_UNRESOLVED``
row reason, never a guessed alias; an unlawful table -> typed whole-run refusal),
and the D01 signal-gate artifact stays its owner's (``None`` at BASE).

NO AVAILABILITY VERDICT IS EVER PERSISTED (seat ruling R6-D11-01 rule 3:
``ENTRY_OPEN`` is never persisted and it is forbidden to create it).  The row
stores the evaluator's INPUT facts and the same-read envelope's typed reasons
verbatim; every verdict field — ``state``, ``entry_open``, ``chase_state``,
``availability_id`` and the verdict trace ``blockers`` / ``reasons`` — is
stripped from ``facts``.  The verdict is NOT re-derivable from a capture row
alone: the gates, quote freshness, chase_above and lifecycle inputs that decide
it are not stored, so deriving it again means a fresh evaluation of the owners'
live reads through the pinned strategy definition, never a read of this stream.
A write-time guard refuses to persist any availability state token, and any
``blockers`` / ``reasons`` field, anywhere in a row.  The row-level ``state`` is
the SAME-READ envelope's own vocabulary (``EVALUATED`` / ``UNAVAILABLE_DATA``),
not an availability verdict.

TWO HOSTS, ONE STREAM (durable home; seat ruling 2026-10-31).  The facts this
script reads live on two machines: the committed repo tree (candidates store,
board as_of, B1 episode HEAD, alias reference) on every checkout, and the native
live plane ``/var/lib/macro-live`` (``state/quotes_full.json`` +
``public/live/prophet_live.json``) on the VPS only.  The VPS writes NOTHING under
``data/`` (ledger law G0.2) and the nightly Mac runner has no live plane, so the
same-read is SPLIT exactly like the incumbent Prophet Live lane (evaluator ->
R2 event spool -> nightly reconciler), never duplicated:
  ``--spool``                the VPS timer pass (app/deploy/macro-live-b4capture.timer,
                             once per US session after the open).  SESSION GUARD
                             first: the pass's Eastern date must be an NYSE session
                             (``NOT_A_SESSION`` otherwise -- a holiday never produces
                             a row) and the committed board stamp must be EXACTLY the
                             session immediately before it (``STALE_BOARD_STAMP``
                             otherwise -- a nightly that has not landed on this host,
                             or a board rendered mid-session, never yields a row).  Then it builds every row against the live
                             plane, writes nothing under data/, and publishes ONE
                             object per pass at
                             ``live_flow/prophet_b4_capture/<stamp_date>/<captured_at>.json``
                             (object-per-pass, never read-modify-write).  An
                             unpublished pass is a typed refusal (exit 3), never a
                             silent no-op: the spool IS this pass's only output.
  ``--nightly --from-spool`` the Mac nightly (daily.yml ``us_prophet_ledgers``): a STRICT
                             listing (a failed LIST is ``SPOOL_LIST_FAILED``, never an
                             empty spool), calendar-stamp prefixes only, every object
                             and row validated (schema, producer, stamp, pass date,
                             session rule, closed key set, write fence) BEFORE any
                             write; per stamp the EARLIEST pass is the observation and
                             later passes are recorded as superseded, not merged; all
                             day-file merges are planned (conflicts raised) before the
                             first byte is written; then keep-first merge -- the SOLE
                             durable advancer, still lane-gated, and the commit step
                             lands the stream.  Selected stamps = the last N prefixes
                             plus every older prefix that has no committed day file
                             yet (a backlog is never aged out unread).  An EMPTY spool
                             is a valid state (the VPS lane not enrolled yet), never a
                             refusal.
  ``--nightly`` alone        unchanged: a host that has BOTH the tree and the live
                             plane (none exists today) captures and writes directly.
No row is built twice and no verdict is persisted on either host; the row key,
body digest, conflict law and ``captured_at`` (the VPS pass clock) are the same.

Run (VPS pass):       python -m scripts.capture_prophet_b4_same_read --spool
Run (nightly ingest): python -m scripts.capture_prophet_b4_same_read --nightly --from-spool
Run (nightly / DAG):  python -m scripts.capture_prophet_b4_same_read --nightly
Run (safe preview):   python -m scripts.capture_prophet_b4_same_read
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import ledger_lane  # noqa: E402
from engine.prophet_live import live_states, r2io  # noqa: E402
from lib.nyse_calendar import is_session, last_session_on_or_before  # noqa: E402
from engine.prophet_b4_same_read import (  # noqa: E402
    evaluate_same_read_entry_availability,
)
from engine.prophet_entry_availability import (  # noqa: E402
    AVAILABILITY_STATES,
    EntryAvailabilityContractError,
)
from engine.prophet_entry_availability_sources import RuntimeOwnerFactError  # noqa: E402
from engine.us_candidate_episode_intake import _records_snapshot  # noqa: E402
from lib.dataos.identity import IdentityError, VendorAliasTable  # noqa: E402
from engine.prophet_candidate_state import CandidateStateContractError  # noqa: E402
from engine.us_candidate_episode import (  # noqa: E402
    EpisodeContractError,
    canonical_json,
    load_candidate_episode_store_snapshot,
)
from engine.us_context_vector import read_today_candidate_source_rows  # noqa: E402
from engine.us_prophet_w3 import _repo_root, _store_dir, resolve_board_as_of  # noqa: E402
from engine.prophet_strategy_definition import (  # noqa: E402
    build_early_leadership_sector_rotation_definition,
)

#: The closed schema of one capture row.
ROW_SCHEMA = "prophet.b4.capture/v1"

#: The closed capture-row key set (seat ruling F22, frozen).  Tested verbatim.
ROW_KEYS = (
    "schema",
    "stamp_date",
    "captured_at",
    "ticker",
    "security_id",
    "episode_id",
    "candidate_generation_id",
    "market_session",
    "candidate_source_event_id",
    "candidate_source_receipt",
    "strategy_definition_id",
    "strategy_definition_receipt",
    "same_read_schema",
    "state",
    "nbbo_quality",
    "b3_projection_id",
    "owner_read_schema",
    "binding",
    "unavailable_reasons",
    "receipts",
    "facts",
)

#: The same-read envelope's own state vocabulary (persisted at row level; it is
#: the join's outcome, never an availability verdict).
SAME_READ_STATES = frozenset({"EVALUATED", "UNAVAILABLE_DATA"})

#: The availability row's verdict fields — REMOVED from ``facts`` and never
#: persisted anywhere in a capture row (D11 rule 3).  ``state`` is the
#: ENTRY_OPEN-class availability token, ``entry_open`` its boolean shadow,
#: ``chase_state`` the evaluator's derived chase classification, and
#: ``availability_id`` a digest over the verdict-bearing material, and
#: ``blockers`` / ``reasons`` the state-decision branch's verdict TRACE — an
#: encoded form of the verdict.  What remains is the evaluator's INPUT facts;
#: the verdict is NOT re-derivable from them alone.
VERDICT_FIELDS = (
    "state", "entry_open", "chase_state", "availability_id", "blockers", "reasons",
)

#: The verdict-trace keys the write-time fence refuses wherever they appear —
#: at the top level of a row or anywhere inside ``facts``.
VERDICT_TRACE_KEYS = ("blockers", "reasons")

#: Every registered strategy definition on main.  At BASE exactly the one
#: immutable, authority-false proving definition.
STRATEGY_DEFINITIONS: list[Mapping[str, object]] = [
    build_early_leadership_sector_rotation_definition(),
]

#: The publishers' native live root — the owner of ``state/quotes_full.json``
#: and ``public/live/prophet_live.json`` (``scripts/prophet_live_evaluator.py``).
#: Report mode may override it with ``--live-root`` for inspection; the nightly
#: lane never may.
NATIVE_LIVE_ROOT = Path("/var/lib/macro-live")

#: The capture stream's directory under the incumbent prospective-evaluation
#: root, as a sibling of the W3 grain store.  W3's own files and grains are
#: never written or edited here.
CAPTURE_SUBDIR = "b4_capture"

#: The R2 spool the VPS pass publishes to and the nightly ingests from (sibling of
#: the Prophet Live event spool ``live_flow/prophet_live_events``).
SPOOL_PREFIX = "live_flow/prophet_b4_capture"
SPOOL_SCHEMA = "prophet.b4.capture_spool/v1"
SPOOL_PRODUCER = "scripts/capture_prophet_b4_same_read.py"
#: How many most-recent stamp_date prefixes one nightly ingest reads (keep-first
#: makes a re-read a no-op, so this bounds GETs, not correctness).
SPOOL_SESSIONS_DEFAULT = 5
#: A spool prefix is a calendar stamp or it is ignored (never a path component).
_STAMP_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

#: The three identity columns every durable candidates-store row must carry for
#: the builder-identical source-key derivation to be lawful.
_REQUIRED_CANDIDATE_FIELDS = ("stamp_date", "ticker", "board_definition")

#: The episode store root parts under the repo root (the native reader's own
#: fixed root; kept in one place so the snapshot and the evaluator cannot drift).
_EPISODE_STORE_PARTS = ("data", "us_prophet_rank", "episodes")

#: The only per-candidate exceptions the evaluation chain may lawfully raise for
#: an absent or contradictory mandatory owner fact; each is captured verbatim as
#: ``"<ExceptionClass>: <message>"`` in ``unavailable_reasons``.  EXACTLY the
#: list ``engine.prophet_b4_same_read._CONTRACT_ERRORS`` itself declares — an
#: ``EpisodeContractError`` escaping the same-read module is a defect, not a
#: typed reason, and propagates.
_CONTRACT_ERRORS = (
    RuntimeOwnerFactError,
    EntryAvailabilityContractError,
    CandidateStateContractError,
)


class TypedRefusal(Exception):
    """A typed, non-traceback refusal.  Exit code 3; nothing written."""

    def __init__(self, token: str, message: str) -> None:
        super().__init__(message)
        self.token = token
        self.message = message


class CaptureConflictError(ValueError):
    """A frozen capture key was presented with a different row body.

    The W3ConflictError analogue: exit code 2, NOTHING written — the committed
    day file is left byte-identical and the refusal names the key and the
    sha256 digests of the two canonical row bodies (never the bodies).
    """

    def __init__(self, key: tuple, existing_digest: str, incoming_digest: str) -> None:
        self.key = key
        self.existing_digest = existing_digest
        self.incoming_digest = incoming_digest
        super().__init__(
            f"b4 capture conflict on {key}: committed={existing_digest} "
            f"incoming={incoming_digest}"
        )


class CaptureDayFileError(ValueError):
    """The committed day file is not a lawful capture stream."""


ALIAS_REFERENCE_PARTS = ("data", "reference", "vendor_aliases.parquet")


class BoundAliasTable:
    """The Data OS alias reader plus the receipt of the bytes it was built from.

    Delegates the two calls the sources adapter requires (``vendor_symbol_for`` /
    ``resolve``) to ``lib.dataos.identity.VendorAliasTable`` unchanged.  The
    receipt (path + sha256 of the parquet payload) is reported in the run
    document only (stdout): captured rows keep their closed key set and carry
    no alias field, and this script persists nothing about the receipt.
    """

    __slots__ = ("_table", "receipt")

    def __init__(self, table: object, receipt: Mapping[str, object]) -> None:
        self._table = table
        self.receipt = dict(receipt)

    def vendor_symbol_for(self, vendor: str, security_id: str, on: object) -> object:
        return self._table.vendor_symbol_for(vendor, security_id, on)

    def resolve(self, vendor: str, vendor_symbol: str, on: object) -> object:
        return self._table.resolve(vendor, vendor_symbol, on)


def resolve_alias_table(root: object = None, *, required: bool = False) -> object:
    """The Data OS alias provider: the ONE in-repo identity reader, or ``None``.

    Reads ``data/reference/vendor_aliases.parquet`` under ``root`` through the
    intake's ``_records_snapshot`` (the same rows + sha256 receipt the B1
    candidate-episode generation binds its identity spine from) and builds
    ``VendorAliasTable.from_records`` over them.

    Absent (or not a regular file) reference: in report / dry-run mode this
    returns ``None`` — the canonical-security-id -> store-symbol relation
    stays unbound and the sources adapter's own ``RuntimeOwnerFactError``
    remains the typed row reason (``IDENTITY_ALIAS_UNRESOLVED``), never a
    guessed alias.  With ``required=True`` (the durable nightly write) it is a
    typed refusal of the whole run instead: the reference is a tracked file,
    so its absence means an incomplete checkout, and a durable row written
    against an unbound seam could never be told apart from a security that
    truly has no store alias — nor corrected later, because the day file keeps
    the first row written under each key.  A reference that is present but
    unlawful (ambiguous overlapping rows, a missing column) is a typed refusal
    in every mode, not a silent unbind.
    """
    base = Path(root).resolve() if root is not None else _repo_root()
    path = base.joinpath(*ALIAS_REFERENCE_PARTS)
    if not path.is_file():
        if required:
            raise TypedRefusal(
                "ALIAS_REFERENCE_MISSING",
                f"the Data OS alias reference {path} is absent from this checkout "
                "(it is a tracked file); a durable nightly capture may not persist "
                "rows against an unbound identity seam",
            )
        return None
    try:
        rows, receipt = _records_snapshot(path)
        table = VendorAliasTable.from_records(rows)
    except (IdentityError, OSError, ValueError, KeyError) as exc:
        raise TypedRefusal(
            "ALIAS_TABLE_MALFORMED",
            f"the Data OS alias reference {path} is present but not a lawful "
            f"alias table: {type(exc).__name__}: {exc}",
        ) from exc
    return BoundAliasTable(table, receipt)


def _now() -> datetime:
    """The writer's OWN UTC clock.  Called exactly ONCE per run."""
    return datetime.now(timezone.utc)


def capture_dir(root: Path | None = None) -> Path:
    """The capture stream root: a sibling of the W3 grain store, never inside it."""
    return _store_dir(root).parent / CAPTURE_SUBDIR


def capture_path(root: Path | None, stamp_date: str) -> Path:
    """The append-only day file for one stamp: ``b4_capture/<YYYY-MM>/<day>.jsonl``."""
    day = str(stamp_date)[:10]
    return capture_dir(root) / day[:7] / f"{day}.jsonl"


def _now_iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds").replace("+00:00", "Z")


def _typed_reason(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


def _strategy_receipt(definition: Mapping[str, object]) -> str:
    """The policy pin: sha256 of the definition's canonical JSON bytes."""
    return "sha256:" + sha256(canonical_json(definition).encode("utf-8")).hexdigest()


def _candidate_source_identity(native_row: Mapping[str, object]) -> tuple[str, str, str]:
    """Derive the candidate source key + receipt exactly as the builder does.

    Byte-identical to the incumbent derivation at
    ``scripts/build_stock_library.py`` (``"candidate:{stamp_date}:{ticker}:{board_definition}".format(**native_row)``
    and ``"sha256:" + sha256(canonical_json(native_row))``) over the SAME native
    rows ``engine.us_context_vector.read_today_candidate_source_rows`` returns.
    The builder is read for parity, never imported (render path, #9495/#9369).
    """
    for field in _REQUIRED_CANDIDATE_FIELDS:
        value = native_row.get(field)
        if not isinstance(value, str) or not value:
            raise TypedRefusal(
                "CANDIDATE_ROW_MALFORMED",
                f"candidates store row is missing a usable {field!r} identity column",
            )
    source_event_id = "candidate:{stamp_date}:{ticker}:{board_definition}".format(
        **native_row
    )
    source_receipt = (
        "sha256:" + sha256(canonical_json(native_row).encode("utf-8")).hexdigest()
    )
    return native_row["ticker"], source_event_id, source_receipt


def _stamp_native_rows(root: Path, stamp_date: str) -> list[dict[str, object]]:
    """The durable ``us_prophet_rank.candidates/v1`` store rows for one stamp."""
    try:
        rows, _receipts = read_today_candidate_source_rows(root)
    except (OSError, ValueError) as exc:
        raise TypedRefusal(
            "CANDIDATES_STORE_UNREADABLE", f"candidates store unreadable: {exc}"
        ) from exc
    return [row for row in rows if str(row.get("stamp_date")) == stamp_date]


def _load_snapshot(root: Path):
    """The ONE HEAD-backed candidate-episode snapshot for the whole run."""
    store_root = root.joinpath(*_EPISODE_STORE_PARTS)
    try:
        return load_candidate_episode_store_snapshot(store_root)
    except (EpisodeContractError, OSError) as exc:
        raise TypedRefusal(
            "EPISODE_STORE_UNREADABLE", f"candidate episode store unreadable: {exc}"
        ) from exc


def _episode_security_id(snapshot, episode_id: object) -> str | None:
    """Echo the canonical B1 security_id of one bound episode, or None.

    Identity echo only: the same-read module alone types every relation,
    retraction and suppression outcome.  When the envelope's owner read already
    published its binding that is the stronger source and is used instead.
    """
    if not isinstance(episode_id, str) or not episode_id:
        return None
    for row in snapshot.generation.episodes:
        if row.get("episode_id") == episode_id:
            security_id = row.get("security_id")
            if isinstance(security_id, str) and security_id:
                return security_id
            return None
    return None


def _row_security_id(envelope: Mapping[str, object], snapshot) -> str | None:
    binding = envelope.get("binding")
    if isinstance(binding, Mapping):
        security_id = binding.get("security_id")
        if isinstance(security_id, str) and security_id:
            return security_id
    return _episode_security_id(snapshot, envelope.get("episode_id"))


def _row_generation_id(envelope: Mapping[str, object], snapshot) -> str:
    binding = envelope.get("binding")
    if isinstance(binding, Mapping):
        generation_id = binding.get("candidate_generation_id")
        if isinstance(generation_id, str) and generation_id:
            return generation_id
    return str(snapshot.generation_id)


def _facts_without_verdict(availability: object) -> dict[str, object] | None:
    """The availability row with every verdict field removed; None if absent."""
    if not isinstance(availability, Mapping):
        return None
    return {key: value for key, value in availability.items() if key not in VERDICT_FIELDS}


def _walk_scalars(value: object):
    if isinstance(value, Mapping):
        for item in value.values():
            yield from _walk_scalars(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_scalars(item)
    else:
        yield value


def _walk_mappings(value: object):
    """Every mapping node under ``value`` (``value`` itself included)."""
    if isinstance(value, Mapping):
        yield value
        for item in value.values():
            yield from _walk_mappings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_mappings(item)


def _assert_row_is_lawful(row: Mapping[str, object]) -> None:
    """The write-time D11 fence: no availability state token is ever persisted.

    The row-level ``state`` is the same-read envelope's own vocabulary and is
    checked against THAT closed set; every other scalar anywhere in the row —
    including ``facts``, ``binding`` and every receipt — must not equal an
    availability state token, and the verdict trace (``blockers`` /
    ``reasons``) may appear neither at the top level nor anywhere inside
    ``facts``.  A violation refuses the run rather than writing an unlawful row.
    """
    for trace_key in VERDICT_TRACE_KEYS:
        if trace_key in row:
            raise TypedRefusal(
                "CAPTURE_ROW_PERSISTS_A_VERDICT_TRACE",
                f"capture row would persist verdict trace field {trace_key!r}",
            )
    if set(row) != set(ROW_KEYS):
        raise TypedRefusal(
            "CAPTURE_ROW_KEYS_NOT_CLOSED", "capture row key set is not closed"
        )
    for mapping in _walk_mappings(row.get("facts")):
        for trace_key in VERDICT_TRACE_KEYS:
            if trace_key in mapping:
                raise TypedRefusal(
                    "CAPTURE_ROW_PERSISTS_A_VERDICT_TRACE",
                    f"capture row would persist verdict trace field {trace_key!r} "
                    "inside facts",
                )
    if row["state"] not in SAME_READ_STATES:
        raise TypedRefusal(
            "CAPTURE_ROW_STATE_INVALID",
            f"capture row state {row['state']!r} is not a same-read state",
        )
    for key, value in row.items():
        if key == "state":
            continue
        for scalar in _walk_scalars(value):
            if isinstance(scalar, str) and scalar in AVAILABILITY_STATES:
                raise TypedRefusal(
                    "CAPTURE_ROW_PERSISTS_A_STATE_TOKEN",
                    f"capture row field {key!r} would persist state token {scalar!r}",
                )


def _capture_row(
    *,
    stamp_date: str,
    captured_at: str,
    ticker: str,
    source_event_id: str,
    source_receipt: str,
    definition: Mapping[str, object],
    definition_receipt: str,
    envelope: Mapping[str, object],
    snapshot,
) -> dict[str, object]:
    state = envelope.get("state")
    availability = envelope.get("availability") if state == "EVALUATED" else None
    row: dict[str, object] = {
        "schema": ROW_SCHEMA,
        "stamp_date": stamp_date,
        "captured_at": captured_at,
        "ticker": ticker,
        "security_id": _row_security_id(envelope, snapshot),
        "episode_id": envelope.get("episode_id"),
        "candidate_generation_id": _row_generation_id(envelope, snapshot),
        "market_session": stamp_date,
        "candidate_source_event_id": source_event_id,
        "candidate_source_receipt": source_receipt,
        "strategy_definition_id": definition.get("strategy_definition_id"),
        "strategy_definition_receipt": definition_receipt,
        "same_read_schema": envelope.get("schema"),
        "state": state,
        "nbbo_quality": envelope.get("nbbo_quality"),
        "b3_projection_id": envelope.get("b3_projection_id"),
        "owner_read_schema": envelope.get("owner_read_schema"),
        "binding": envelope.get("binding"),
        "unavailable_reasons": list(envelope.get("unavailable_reasons") or []),
        "receipts": list(envelope.get("receipts") or []),
        "facts": _facts_without_verdict(availability),
    }
    _assert_row_is_lawful(row)
    return row


def _evaluate(
    root: Path,
    snapshot,
    *,
    source_event_id: str,
    source_receipt: str,
    live_root: Path,
    alias_table: object,
    definition: Mapping[str, object],
) -> Mapping[str, object]:
    """One same-read evaluation; a typed owner refusal stays a capture row.

    The per-candidate exceptions the chain lawfully raises for an absent or
    contradictory mandatory owner fact are captured verbatim as typed reasons on
    an ``UNAVAILABLE_DATA`` row — the same convention the same-read module uses
    internally.  Anything else is a defect and propagates loudly.
    """
    try:
        return evaluate_same_read_entry_availability(
            root,
            snapshot,
            candidate_source_event_id=source_event_id,
            candidate_source_receipt=source_receipt,
            native_live_root=live_root,
            alias_table=alias_table,
            strategy_definition=definition,
            signal_gate_artifact=None,
        )
    except _CONTRACT_ERRORS as exc:
        return {
            "schema": None,
            "state": "UNAVAILABLE_DATA",
            "availability": None,
            "b3_projection_id": None,
            "episode_id": None,
            "binding": None,
            "owner_read_schema": None,
            "nbbo_quality": "MISSING",
            "unavailable_reasons": [_typed_reason(exc)],
            "receipts": [],
        }


def _row_key_of(row: Mapping[str, object]) -> tuple:
    """The frozen capture key (spec point 6 as amended by seat ruling F27).

    ``candidate_source_event_id`` (``candidate:{stamp_date}:{ticker}:{board_definition}``)
    is unique per candidate per stamp whether or not the candidate's
    ``security_id`` is bound; ``security_id`` stays in the row BODY.  Keying on
    ``security_id`` collapsed every unbound candidate — and the script's own
    ``UNAVAILABLE_DATA`` fallback envelope — onto one ``None`` key, so two
    unbound candidates were a false conflict and the night's census was lost.
    """
    return (
        row.get("stamp_date"),
        row.get("candidate_source_event_id"),
        row.get("candidate_generation_id"),
        row.get("strategy_definition_id"),
    )


def _body_digest(body: str) -> str:
    """sha256 of one canonical row body — what a conflict reports, never the body."""
    return "sha256:" + sha256(body.encode("utf-8")).hexdigest()


def _sort_key(key: tuple) -> tuple:
    return tuple((value is None, "" if value is None else str(value)) for value in key)


def _row_body(row: Mapping[str, object]) -> str:
    """The row minus ``captured_at`` — the part keep-first may legitimately vary."""
    material = {key: value for key, value in row.items() if key != "captured_at"}
    return json.dumps(
        material, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def _read_day_file(target: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if not target.exists():
        return rows
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise CaptureDayFileError(f"committed capture day file unreadable: {exc}") from exc
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CaptureDayFileError(
                f"committed capture day file line {number} is not JSON: {exc}"
            ) from exc
        if not isinstance(row, dict) or row.get("schema") != ROW_SCHEMA \
                or set(row) != set(ROW_KEYS):
            raise CaptureDayFileError(
                f"committed capture day file line {number} is not a {ROW_SCHEMA} row"
            )
        rows.append(row)
    return rows


def _plan_merge(
    target: Path, rows: list[dict[str, object]]
) -> tuple[dict[tuple, dict[str, object]], int]:
    """Keep-first merge of ``rows`` into the day file's committed rows, WITHOUT writing.

    Returns ``(committed_by_key, written)``; raises CaptureConflictError on a changed
    body under an existing key.  Reading and merging are separated from writing so a
    caller holding several day files can plan every merge before the first write.
    """
    committed: dict[tuple, dict[str, object]] = {}
    for row in _read_day_file(target):
        key = _row_key_of(row)
        if key in committed:
            if _row_body(committed[key]) != _row_body(row):
                raise CaptureConflictError(
                    key,
                    _body_digest(_row_body(committed[key])),
                    _body_digest(_row_body(row)),
                )
            continue  # keep-first inside the committed file
        committed[key] = row
    written = 0
    for row in sorted(rows, key=lambda item: _sort_key(_row_key_of(item))):
        key = _row_key_of(row)
        existing = committed.get(key)
        if existing is not None:
            if _row_body(existing) != _row_body(row):
                raise CaptureConflictError(
                    key, _body_digest(_row_body(existing)), _body_digest(_row_body(row))
                )
            continue  # keep-first: the committed row (and its captured_at) stand
        committed[key] = row
        written += 1
    return committed, written


def _write_day_file(target: Path, committed: dict[tuple, dict[str, object]]) -> None:
    """Rewrite the whole day file canonical-JSON, sorted by key, temp file + atomic rename."""
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(
        json.dumps(
            committed[key], sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ) + "\n"
        for key in sorted(committed, key=_sort_key)
    )
    # A UNIQUE temp name in the day directory (two writers never share one),
    # fsync'd before the atomic rename so a crash leaves either the old file or
    # the complete new one — never a torn day file.
    handle, temp_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    temp = Path(temp_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, target)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def _merge_and_write(target: Path, rows: list[dict[str, object]]) -> int:
    """Keep-first merge of the run's rows into the day file; append-only.

    The key is ``_row_key_of`` (stamp_date, candidate_source_event_id,
    candidate_generation_id, strategy_definition_id).  An existing key keeps its
    committed row verbatim (``captured_at`` included); only new keys are appended;
    the whole day file is rewritten canonical-JSON, sorted by key, via temp file +
    atomic rename.  A changed body under an existing key is a typed conflict and
    NOTHING is written.
    """
    committed, written = _plan_merge(target, rows)
    _write_day_file(target, committed)
    return written


def spool_key(stamp_date: str, captured_at: str) -> str:
    """``<SPOOL_PREFIX>/<stamp_date>/<captured_at digits>.json`` — one object per pass."""
    stamp = "".join(ch for ch in str(captured_at) if ch.isalnum())
    return f"{SPOOL_PREFIX}/{str(stamp_date)[:10]}/{stamp}.json"


def _stamp_is_lawful_for_pass(stamp: date, pass_date: date) -> bool:
    """The one session rule both hosts enforce: the pass date is an NYSE session and
    the committed board stamp is EXACTLY the session immediately before it.

    A holiday pass (no session), a pass whose host has not yet pulled the prior
    session's nightly (stamp two or more sessions old) and a board stamped with the
    pass day itself (the nightly runs after the close, so a same-day stamp during the
    session can only be an anomalous mid-session render) all fail; none may become a
    row, because ``captured_at`` is the observation instant of the stamp's candidates
    at THE NEXT session's decision window, not of an arbitrary other day.
    """
    if not is_session(pass_date):
        return False
    return stamp == last_session_on_or_before(pass_date - timedelta(days=1))


def _pass_date(moment: datetime) -> date:
    """The Eastern calendar date of a pass (one ET definition: live_states.et_clock)."""
    return live_states.et_clock(moment).date()


def _spool_session_guard(root_path: Path, moment: datetime) -> dict[str, str]:
    """``--spool`` refuses before any live-plane read when the session rule fails."""
    pass_date = _pass_date(moment)
    if not is_session(pass_date):
        raise TypedRefusal(
            "NOT_A_SESSION",
            f"the pass date {pass_date.isoformat()} (US-Eastern) is not an NYSE session; "
            "a holiday pass observes nothing and publishes nothing",
        )
    stamp_date = resolve_board_as_of(root_path)
    if not stamp_date:
        raise TypedRefusal(
            "COMMITTED_BOARD_AS_OF_MISSING",
            "no committed board as_of: the stamp is the observation identity and "
            "is never wall-clock, run id or Pages",
        )
    try:
        stamp = date.fromisoformat(str(stamp_date)[:10])
    except ValueError as exc:
        raise TypedRefusal(
            "COMMITTED_BOARD_AS_OF_MISSING", f"board as_of is not a date: {stamp_date!r}"
        ) from exc
    prior = last_session_on_or_before(pass_date - timedelta(days=1))
    if not _stamp_is_lawful_for_pass(stamp, pass_date):
        raise TypedRefusal(
            "STALE_BOARD_STAMP",
            f"committed board as_of {stamp.isoformat()} is not the session before the "
            f"pass session {pass_date.isoformat()} (expected {prior.isoformat()}): the "
            "prior session's nightly has not landed on this host, or the board was "
            "rendered mid-session; no row is observed against that stamp",
        )
    return {
        "pass_date": pass_date.isoformat(),
        "stamp_date": str(stamp_date),
        "prior_session": prior.isoformat(),
    }


def _build_rows(
    root_path: Path, live_root_path: Path, *, alias_required: bool,
    moment: datetime | None = None, stamp_date: str | None = None,
) -> dict[str, object]:
    """Every capture row for the committed stamp against the given live plane.

    Shared by the direct nightly, the dry-run, report mode and the VPS spool pass:
    one HEAD-backed snapshot, one alias table, one ``captured_at`` per run, and ONE
    board read per run (the spool pass hands in the stamp its session guard read, so
    a board re-rendered by macro-update between two reads cannot split the pass).
    """
    if stamp_date is None:
        stamp_date = resolve_board_as_of(root_path)
    if not stamp_date:
        raise TypedRefusal(
            "COMMITTED_BOARD_AS_OF_MISSING",
            "no committed board as_of: the stamp is the observation identity and "
            "is never wall-clock, run id or Pages",
        )
    native_rows = _stamp_native_rows(root_path, stamp_date)
    if not native_rows:
        raise TypedRefusal(
            "CANDIDATES_STAMP_ABSENT",
            f"the durable candidates store has no rows for stamp {stamp_date}",
        )
    snapshot = _load_snapshot(root_path)

    alias_table = resolve_alias_table(root_path, required=alias_required)
    alias_receipt = getattr(alias_table, "receipt", None)
    captured_at = _now_iso(moment if moment is not None else _now())
    rows: list[dict[str, object]] = []
    for native_row in native_rows:
        ticker, source_event_id, source_receipt = _candidate_source_identity(native_row)
        for definition in STRATEGY_DEFINITIONS:
            definition_receipt = _strategy_receipt(definition)
            envelope = _evaluate(
                root_path,
                snapshot,
                source_event_id=source_event_id,
                source_receipt=source_receipt,
                live_root=live_root_path,
                alias_table=alias_table,
                definition=definition,
            )
            rows.append(
                _capture_row(
                    stamp_date=stamp_date,
                    captured_at=captured_at,
                    ticker=ticker,
                    source_event_id=source_event_id,
                    source_receipt=source_receipt,
                    definition=definition,
                    definition_receipt=definition_receipt,
                    envelope=envelope,
                    snapshot=snapshot,
                )
            )
    return {
        "stamp_date": stamp_date,
        "candidates": len(native_rows),
        "snapshot": snapshot,
        "alias_table": {
            "bound": alias_table is not None,
            "receipt": dict(alias_receipt) if isinstance(alias_receipt, Mapping) else None,
        },
        "captured_at": captured_at,
        "rows": rows,
    }


def _counts(rows: list[dict[str, object]]) -> tuple[dict[str, int], dict[str, int]]:
    counts_by_state: dict[str, int] = {}
    counts_by_reason: dict[str, int] = {}
    for row in rows:
        counts_by_state[str(row["state"])] = counts_by_state.get(str(row["state"]), 0) + 1
        for reason in row["unavailable_reasons"]:
            counts_by_reason[str(reason)] = counts_by_reason.get(str(reason), 0) + 1
    return dict(sorted(counts_by_state.items())), dict(sorted(counts_by_reason.items()))


def _validate_spool_object(key: str, stamp_date: str, obj: object) -> list[dict[str, object]]:
    """The ingest side's own check of one pass object: schema, producer, stamp,
    closed row key set and the write fence, re-applied here because a spool object
    is bytes from another host, not a row this process built."""
    def refuse(detail: str) -> TypedRefusal:
        # A malformed object under a stamp with no committed day file fails EVERY
        # nightly until it is gone (the backlog rule re-reads it each night).  That is
        # fail-closed on purpose; the remedy is an operator act on the spool, never a
        # day-file edit: move or delete the exact object in R2 and let the next
        # nightly ingest the rest.  No lawful producer writes such an object.
        return TypedRefusal(
            "SPOOL_OBJECT_MALFORMED",
            f"spool object {key} refused, nothing written: {detail}; operator remedy = move "
            "or delete that exact object in the R2 spool (never edit a day file), then let "
            "the next nightly ingest the rest",
        )
    if not isinstance(obj, Mapping):
        raise refuse("not a JSON object (or unreadable)")
    if obj.get("schema") != SPOOL_SCHEMA:
        raise refuse(f"schema is not {SPOOL_SCHEMA}")
    if obj.get("producer") != SPOOL_PRODUCER:
        raise refuse(f"producer is not {SPOOL_PRODUCER}")
    if str(obj.get("stamp_date")) != stamp_date:
        raise refuse("stamp_date does not match its prefix")
    try:
        stamp_d = date.fromisoformat(stamp_date)
        pass_d = date.fromisoformat(str(obj.get("pass_date")))
    except (TypeError, ValueError):
        raise refuse("stamp_date / pass_date are not calendar dates") from None
    if not _stamp_is_lawful_for_pass(stamp_d, pass_d):
        raise refuse(
            f"pass_date {pass_d.isoformat()} is not a session whose stamp may be {stamp_date}"
        )
    try:
        captured = datetime.fromisoformat(str(obj.get("captured_at")).replace("Z", "+00:00"))
    except ValueError:
        raise refuse("captured_at is not an instant") from None
    if captured.tzinfo is None or _pass_date(captured) != pass_d:
        # pass_date is the producer's declaration; captured_at is the observation.  The
        # ingest trusts neither alone: the Eastern date of the instant must BE pass_date.
        raise refuse(
            f"captured_at {obj.get('captured_at')} is not on the declared pass_date {pass_d.isoformat()}"
        )
    rows = obj.get("rows")
    if not isinstance(rows, list) or not rows:
        raise refuse("rows is not a non-empty list")
    out: list[dict[str, object]] = []
    for number, row in enumerate(rows, 1):
        if not isinstance(row, Mapping) or row.get("schema") != ROW_SCHEMA \
                or set(row) != set(ROW_KEYS):
            raise refuse(f"row {number} is not a {ROW_SCHEMA} row")
        if str(row.get("stamp_date")) != stamp_date:
            raise refuse(f"row {number} stamp_date does not match the object")
        if str(row.get("captured_at")) != str(obj.get("captured_at")):
            raise refuse(f"row {number} captured_at does not match the pass")
        try:
            _assert_row_is_lawful(row)
        except Exception as exc:  # noqa: BLE001 — any fence failure is the same refusal
            raise refuse(f"row {number} fails the write fence: {exc}") from exc
        out.append(dict(row))
    return out


def _strict_list_keys(s3, prefix: str) -> list[str]:
    """Every key under ``prefix`` or a typed refusal.

    ``r2io.list_keys`` returns an EMPTY or PARTIAL list on any failure, which here
    would be indistinguishable from "no VPS pass has published" — the exact silent
    dark that cost 27 days in 2026-07/08.  The ingest therefore lists itself and
    refuses on error.
    """
    out: list[str] = []
    kwargs: dict[str, object] = {"Bucket": r2io.bucket(), "Prefix": prefix}
    try:
        while True:
            page = s3.list_objects_v2(**kwargs)
            out.extend(str(o["Key"]) for o in (page.get("Contents") or []))
            token = page.get("NextContinuationToken")
            if not page.get("IsTruncated") or not token:
                break
            kwargs["ContinuationToken"] = token
    except Exception as exc:  # noqa: BLE001 — any transport/auth failure is the same refusal
        raise TypedRefusal(
            "SPOOL_LIST_FAILED",
            f"listing {prefix} failed ({type(exc).__name__}: {exc}); an unreadable spool "
            "is not an empty spool — nothing ingested, nothing written",
        ) from exc
    return out


def _ingest_spool(
    root_path: Path, *, dry_run: bool, sessions: int, root_override: bool
) -> dict[str, object]:
    """``--nightly --from-spool``: list strictly, validate everything, plan every
    merge, then write — the sole durable advancer of the capture stream."""
    s3 = r2io.client()
    if s3 is None:
        raise TypedRefusal(
            "SPOOL_CLIENT_UNAVAILABLE",
            "no R2 credentials: the capture spool cannot be listed, so nothing is "
            "ingested and nothing is written",
        )
    prefix = SPOOL_PREFIX + "/"
    by_stamp: dict[str, list[str]] = {}
    foreign: list[str] = []
    for key in _strict_list_keys(s3, prefix):
        parts = str(key)[len(prefix):].split("/")
        lawful = (
            len(parts) == 2 and bool(_STAMP_PREFIX_RE.match(parts[0]))
            and parts[1].endswith(".json") and len(parts[1]) > len(".json")
        )
        if lawful:
            try:
                date.fromisoformat(parts[0])
            except ValueError:
                lawful = False
        if not lawful:
            foreign.append(str(key))
            continue
        by_stamp.setdefault(parts[0], []).append(str(key))
    stamps_seen = sorted(by_stamp)
    window = set(stamps_seen[-sessions:]) if sessions > 0 else set(stamps_seen)
    # A stamp outside the window is still ingested while it has NO committed day file:
    # a backlog (runner outage, late enrollment) is never aged out unread.  A stamp
    # outside the window WITH a day file is already landed; a later pass for it is a
    # superseded re-observation and is not fetched.
    selected = [
        stamp for stamp in stamps_seen
        if stamp in window or not capture_path(root_path, stamp).exists()
    ]
    aged_out = [stamp for stamp in stamps_seen if stamp not in selected]

    # Phase 1 — read and validate EVERY object of every selected stamp; the earliest
    # pass (by captured_at) is the stamp's observation, later passes are superseded.
    # One malformed object refuses the whole run before any write.
    observations: list[tuple[str, str, list[dict[str, object]], list[str]]] = []
    objects_read = 0
    for stamp in selected:
        passes: list[tuple[str, str, list[dict[str, object]]]] = []
        for key in sorted(by_stamp[stamp]):
            obj = r2io.get_json(key, s3=s3, allow_public=False)
            rows = _validate_spool_object(key, stamp, obj)
            objects_read += 1
            passes.append((str(obj["captured_at"]), key, rows))
        passes.sort(key=lambda item: (item[0], item[1]))
        _, first_key, first_rows = passes[0]
        observations.append((stamp, first_key, first_rows, [k for _, k, _ in passes[1:]]))

    # Phase 2a — plan every day-file merge; a conflict or malformed committed file
    # anywhere raises BEFORE the first write (never a partial night).
    plans: list[tuple[str, Path, dict[tuple, dict[str, object]], int]] = []
    for stamp, _key, rows, _superseded in observations:
        target = capture_path(root_path, stamp)
        committed, written = _plan_merge(target, rows)
        plans.append((stamp, target, committed, written))
    # Phase 2b — write.
    if not dry_run:
        for _stamp, target, committed, written in plans:
            if written:
                _write_day_file(target, committed)

    sessions_doc: dict[str, dict[str, object]] = {}
    total_rows = 0
    total_written = 0
    for (stamp, key, rows, superseded), (_s, target, _c, written) in zip(observations, plans):
        total_rows += len(rows)
        total_written += written if not dry_run else 0
        sessions_doc[stamp] = {
            "objects": 1 + len(superseded),
            "observation": key,
            "superseded": superseded,
            "rows": len(rows),
            "rows_written": written if not dry_run else 0,
            "target": str(target),
        }
    if not stamps_seen:
        print(
            "::notice title=prophet-b4-capture::capture spool is empty — no VPS pass "
            f"has published under {prefix} (lane not enrolled, or no session); "
            "nothing to ingest, nothing written",
            file=sys.stderr, flush=True,
        )
    return {
        "mode": "dry-run" if dry_run else "nightly",
        "source": "spool",
        "dry_run": bool(dry_run),
        "root_override": root_override,
        "data_root": str(root_path),
        "spool": {
            "prefix": SPOOL_PREFIX,
            "sessions_requested": sessions,
            "stamps_seen": stamps_seen,
            "stamps_selected": selected,
            "stamps_aged_out": aged_out,
            "foreign_keys": len(foreign),
            "objects": objects_read,
            "sessions": sessions_doc,
        },
        "rows": total_rows,
        "rows_written": total_written,
        "authority": "none — capture only",
    }


def run(
    root: object = None,
    *,
    nightly: bool = False,
    dry_run: bool = False,
    live_root: object = None,
    spool: bool = False,
    from_spool: bool = False,
    spool_sessions: int = SPOOL_SESSIONS_DEFAULT,
) -> dict[str, object]:
    """One capture run.  Returns the run document; raises TypedRefusal/CaptureConflictError."""
    if spool and (nightly or from_spool or dry_run):
        raise TypedRefusal(
            "SPOOL_MODE_IS_NOT_NIGHTLY",
            "--spool is the VPS pass: it reads the native live plane and publishes one "
            "object; it never writes under data/ and never combines with --nightly, "
            "--dry-run or --from-spool",
        )
    if spool and live_root is not None:
        raise TypedRefusal(
            "LIVE_ROOT_OVERRIDE_FORBIDDEN_IN_SPOOL_MODE",
            "--live-root is a report-mode inspection flag; the spool pass reads the "
            "publishers' fixed native live root only",
        )
    if from_spool and not nightly:
        raise TypedRefusal(
            "FROM_SPOOL_REQUIRES_NIGHTLY",
            "--from-spool is the nightly ingest of the VPS spool; it has no report mode",
        )
    if nightly and live_root is not None:
        raise TypedRefusal(
            "LIVE_ROOT_OVERRIDE_FORBIDDEN_IN_NIGHTLY_MODE",
            "--live-root is a report-mode inspection flag; the nightly lane reads "
            "the publishers' fixed native live root only",
        )
    if nightly and not dry_run and not ledger_lane.nightly_advance_enabled():
        raise TypedRefusal(
            "NIGHTLY_LANE_NOT_ARMED",
            "nightly is the sole advancer: durable capture requires --nightly AND "
            "engine.ledger_lane.nightly_advance_enabled() (COLLECT_LANE=nightly); "
            "run report mode or --nightly --dry-run for a no-write preview",
        )

    root_path = Path(root).resolve() if root is not None else _repo_root()
    if not root_path.is_absolute() or not root_path.is_dir():
        raise TypedRefusal(
            "REPO_ROOT_MISSING", f"repo root is not an existing directory: {root_path}"
        )
    if from_spool:
        return _ingest_spool(
            root_path, dry_run=dry_run, sessions=int(spool_sessions),
            root_override=root is not None,
        )
    # ONE clock read per pass: the guard's pass date and every row's captured_at are
    # the same instant (the ingest re-derives pass_date from captured_at and refuses
    # a disagreement).
    moment = _now()
    session_guard: dict[str, str] | None = None
    if spool:
        session_guard = _spool_session_guard(root_path, moment)
    live_root_path = Path(live_root) if live_root is not None else NATIVE_LIVE_ROOT
    if not live_root_path.is_absolute() or not live_root_path.is_dir():
        raise TypedRefusal(
            "NATIVE_LIVE_ROOT_MISSING",
            f"the native live owner root must be an existing absolute operator "
            f"directory: {live_root_path}",
        )

    built = _build_rows(
        root_path, live_root_path,
        alias_required=bool((nightly and not dry_run) or spool),
        moment=moment,
        stamp_date=session_guard["stamp_date"] if session_guard else None,
    )
    stamp_date = str(built["stamp_date"])
    rows = list(built["rows"])  # type: ignore[arg-type]
    captured_at = str(built["captured_at"])
    counts_by_state, counts_by_reason = _counts(rows)

    spool_doc: dict[str, object] | None = None
    if spool:
        key = spool_key(stamp_date, captured_at)
        payload = {
            "schema": SPOOL_SCHEMA,
            "producer": SPOOL_PRODUCER,
            "stamp_date": stamp_date,
            "pass_date": session_guard["pass_date"] if session_guard else None,
            "captured_at": captured_at,
            "snapshot_generation_id": str(built["snapshot"].generation_id),
            "alias_table": built["alias_table"],
            "candidates": built["candidates"],
            "strategies": len(STRATEGY_DEFINITIONS),
            "counts_by_state": counts_by_state,
            "counts_by_reason": counts_by_reason,
            "rows": rows,
        }
        if not r2io.put_json(key, payload):
            raise TypedRefusal(
                "SPOOL_NOT_PUBLISHED",
                f"the pass built {len(rows)} rows but {key} was not published (no R2 "
                "credentials, PROPHET_LIVE_NO_PUBLISH, or a PUT failure); nothing is "
                "written anywhere else, so this decision instant is lost unless re-run",
            )
        spool_doc = {"key": key, "published": True, "session_guard": session_guard}

    if spool:
        mode = "spool"
    else:
        mode = "nightly" if nightly and not dry_run else ("dry-run" if nightly else "report")
    target = capture_path(root_path, stamp_date) if nightly else None
    rows_written = 0
    if nightly and not dry_run:
        rows_written = _merge_and_write(target, rows)

    return {
        "mode": mode,
        "source": "native_live_root",
        "dry_run": bool(nightly and dry_run),
        "root_override": root is not None,
        "data_root": str(root_path),
        "stamp_date": stamp_date,
        "snapshot_generation_id": str(built["snapshot"].generation_id),
        "alias_table": built["alias_table"],
        "candidates": built["candidates"],
        "strategies": len(STRATEGY_DEFINITIONS),
        "rows": len(rows),
        "counts_by_state": counts_by_state,
        "counts_by_reason": counts_by_reason,
        "rows_written": rows_written,
        "target": str(target) if target is not None else None,
        "spool": spool_doc,
        "captured_at": captured_at,
        "authority": "none — capture only",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--nightly", action="store_true",
        help="durable append (the SOLE advancer; requires COLLECT_LANE=nightly)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="with --nightly: build rows and write nothing",
    )
    parser.add_argument(
        "--live-root", default=None,
        help="report mode only: inspect against this native live owner root "
             "(refused with --nightly)",
    )
    parser.add_argument(
        "--root", default=None,
        help="repo root (default: this checkout; isolated/preview runs only)",
    )
    parser.add_argument(
        "--spool", action="store_true",
        help="VPS pass: read the native live plane, write nothing under data/, "
             "publish one object to the R2 capture spool (never with --nightly)",
    )
    parser.add_argument(
        "--from-spool", action="store_true",
        help="with --nightly: ingest the VPS capture spool from R2 instead of "
             "reading the native live plane (the Mac nightly's durable path)",
    )
    parser.add_argument(
        "--spool-sessions", type=int, default=SPOOL_SESSIONS_DEFAULT,
        help="with --from-spool: how many most-recent stamp_date prefixes to read",
    )
    args = parser.parse_args(argv)
    try:
        doc = run(
            args.root,
            nightly=bool(args.nightly),
            dry_run=bool(args.dry_run),
            live_root=args.live_root,
            spool=bool(args.spool),
            from_spool=bool(args.from_spool),
            spool_sessions=int(args.spool_sessions),
        )
    except TypedRefusal as exc:
        print(json.dumps({"refused": exc.token, "message": exc.message}, sort_keys=True))
        return 3
    except CaptureConflictError as exc:
        print(
            json.dumps(
                {
                    "conflict": [str(item) for item in exc.key],
                    "committed": exc.existing_digest,
                    "incoming": exc.incoming_digest,
                },
                sort_keys=True,
            )
        )
        return 2
    except CaptureDayFileError as exc:
        # A malformed committed day file: typed, exit 2, nothing written (the
        # read precedes every write) — never a traceback the nightly lane
        # cannot classify.
        print(
            json.dumps(
                {"error": {"type": "CaptureDayFileError", "detail": str(exc)}},
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(doc, sort_keys=True, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
