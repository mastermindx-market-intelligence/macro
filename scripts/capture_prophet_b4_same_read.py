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
not), the alias table comes from the ``resolve_alias_table`` seam (``None`` at
BASE — no in-repo Data OS provider exists), and the D01 signal-gate artifact
stays its owner's (``None`` at BASE).

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

Run (nightly / DAG):  python -m scripts.capture_prophet_b4_same_read --nightly
Run (safe preview):   python -m scripts.capture_prophet_b4_same_read
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import ledger_lane  # noqa: E402
from engine.prophet_b4_same_read import (  # noqa: E402
    evaluate_same_read_entry_availability,
)
from engine.prophet_entry_availability import (  # noqa: E402
    AVAILABILITY_STATES,
    EntryAvailabilityContractError,
)
from engine.prophet_entry_availability_sources import RuntimeOwnerFactError  # noqa: E402
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


def resolve_alias_table() -> object:
    """The Data OS alias provider seam.  ``None`` at BASE.

    No in-repo ``vendor_symbol_for``/``resolve`` provider exists yet, so the
    canonical-security-id -> store-symbol relation is unbound and the sources
    adapter's own ``RuntimeOwnerFactError`` becomes the captured typed reason
    (``IDENTITY_ALIAS_UNRESOLVED``).  Binding a real provider here is a separate
    owner decision; this seam exists so there is exactly one place to bind it.
    """
    return None


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


def _merge_and_write(target: Path, rows: list[dict[str, object]]) -> int:
    """Keep-first merge of the run's rows into the day file; append-only.

    The key is ``_row_key_of`` (stamp_date, candidate_source_event_id,
    candidate_generation_id, strategy_definition_id).  An existing key keeps its
    committed row verbatim (``captured_at`` included); only new keys are appended; the whole day file is rewritten canonical-JSON,
    sorted by key, via temp file + atomic rename.  A changed body under an
    existing key is a typed conflict and NOTHING is written.
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
    return written


def run(
    root: object = None,
    *,
    nightly: bool = False,
    dry_run: bool = False,
    live_root: object = None,
) -> dict[str, object]:
    """One capture run.  Returns the run document; raises TypedRefusal/CaptureConflictError."""
    if nightly and live_root is not None:
        raise TypedRefusal(
            "LIVE_ROOT_OVERRIDE_FORBIDDEN_IN_NIGHTLY_MODE",
            "--live-root is a report-mode inspection flag; the nightly lane reads "
            "the publishers' fixed native live root only",
        )
    # --dry-run short-circuits the lane gate: it is the sanctioned no-write
    # preview of the nightly shape and writes nothing, so it needs no lane.
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
    live_root_path = Path(live_root) if live_root is not None else NATIVE_LIVE_ROOT
    if not live_root_path.is_absolute() or not live_root_path.is_dir():
        raise TypedRefusal(
            "NATIVE_LIVE_ROOT_MISSING",
            f"the native live owner root must be an existing absolute operator "
            f"directory: {live_root_path}",
        )

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

    alias_table = resolve_alias_table()
    captured_at = _now_iso(_now())
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

    mode = "nightly" if nightly and not dry_run else ("dry-run" if nightly else "report")
    target = capture_path(root_path, stamp_date) if nightly else None
    rows_written = 0
    if nightly and not dry_run:
        rows_written = _merge_and_write(target, rows)

    counts_by_state: dict[str, int] = {}
    counts_by_reason: dict[str, int] = {}
    for row in rows:
        counts_by_state[str(row["state"])] = counts_by_state.get(str(row["state"]), 0) + 1
        for reason in row["unavailable_reasons"]:
            counts_by_reason[str(reason)] = counts_by_reason.get(str(reason), 0) + 1
    return {
        "mode": mode,
        "dry_run": bool(nightly and dry_run),
        "root_override": root is not None,
        "data_root": str(root_path),
        "stamp_date": stamp_date,
        "snapshot_generation_id": str(snapshot.generation_id),
        "candidates": len(native_rows),
        "strategies": len(STRATEGY_DEFINITIONS),
        "rows": len(rows),
        "counts_by_state": dict(sorted(counts_by_state.items())),
        "counts_by_reason": dict(sorted(counts_by_reason.items())),
        "rows_written": rows_written,
        "target": str(target) if target is not None else None,
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
    args = parser.parse_args(argv)
    try:
        doc = run(
            args.root,
            nightly=bool(args.nightly),
            dry_run=bool(args.dry_run),
            live_root=args.live_root,
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
