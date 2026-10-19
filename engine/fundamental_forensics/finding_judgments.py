"""FIF Q2 finding-judgment ledger: then-known beliefs, immutable originals (A48).

Acceptance case A48 preserves the original judgment/version of a finding:
delayed evidence never rewrites past apparent knowledge. A later build that
changes or drops a finding may not silently replace the earlier view, so this
module owns three things:

* an append-only ledger of judgment records over a strict-conditional object
  store. The ledger is a hash-chained sequence of numbered batch objects —
  one batch per recording run — plus a HEAD pointer that is the ledger's
  only commit point. A record is never edited or deleted. A correction is a
  NEW record that names the record it supersedes, and a withdrawal is a
  correction whose content is null;
* a then-known replay reader that reconstructs, for a caller-supplied cutoff,
  the last belief recorded at or before that cutoff (a visible withdrawal is
  returned as withdrawn);
* two adapters: the nightly workbench build state and kernel rows shaped like
  ``Finding.to_dict()``.

Clock law: every timestamp is supplied by the caller. The recording clock is
an explicit run argument (a workbench state's ``generated_at`` is recorded as
the run's source clock, never as the recording clock), and a replay cutoff is
mandatory — a missing cutoff is never treated as the present moment. No
function in this module consults the operating-system clock. The ledger-wide
clock is strict: a run's ``recorded_at`` may never precede the latest batch's
``recorded_at``; an equal clock is legal only for a run that appends nothing;
and batch clocks must strictly increase along the sequence.

Write law: batches live at deterministic keys
``{prefix}/batches/{sequence:08d}.json`` and are created only through
``put_bytes_strict_conditional(key, payload, expected_version=None)``. Each
batch names the exact-byte sha256 of its predecessor and is never rewritten.
HEAD is advanced by compare-and-swap on the version the writer loaded; an
absent HEAD is an empty ledger. A writer proves its batch bytes by a bounded
read-back before advancing HEAD: exact bytes already present prove idempotent
completion, different bytes at the next sequence are a conflict, and an
outcome read-back cannot settle is EFFECT_UNKNOWN — never retried or rerouted
here; a later run's roll-forward completes it on the same store. The reader
never lists a prefix: it reads HEAD, then batches ``1..HEAD.sequence`` by
their deterministic keys, verifying canonical bytes, the hash chain and
strictly increasing batch clocks. No unconditional put is ever issued.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from .models import parse_utc, stable_id, utc_text

JUDGMENT_SCHEMA = "fundamental_forensics.finding_judgment/v2"
JUDGMENT_BATCH_SCHEMA = "fundamental_forensics.finding_judgment_batch/v2"
JUDGMENT_HEAD_SCHEMA = "fundamental_forensics.finding_judgment_head/v1"
JUDGMENT_REPLAY_SCHEMA = "fundamental_forensics.finding_judgment_replay/v1"
JUDGMENT_PREFIX = "fundamental_forensics/finding-judgments/v1"
JUDGMENT_HEAD_KEY = f"{JUDGMENT_PREFIX}/HEAD.json"
HARD_MAX_BATCH_BYTES = 8 * 1024 * 1024
HARD_MAX_BATCHES = 5000
_HEAD_READ_BOUND = 64 * 1024
_HEX64 = re.compile(r"[0-9a-f]{64}")

_KINDS = ("workbench", "kernel")
_STATUSES = ("present", "withdrawn")
_RELATIONS = ("original", "correction")
_CHANGE_REASON_VALUES = ("content", "status", "detector_version")

_KERNEL_REQUIRED_KEYS = (
    "finding_id",
    "detector_id",
    "detector_version",
    "entity_cik",
    "state",
    "period_ends",
)

_RECORD_FIELDS = (
    "schema",
    "judgment_id",
    "kind",
    "subject_key",
    "entity_ref",
    "finding_ref",
    "content_sha256",
    "content",
    "status",
    "relation",
    "supersedes",
    "recorded_at",
    "source_ready_at",
    "source_generated_at",
    "change_reasons",
)

_BATCH_FIELDS = (
    "schema",
    "sequence",
    "predecessor_sha256",
    "recorded_at",
    "source_generated_at",
    "records",
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class FindingJudgmentError(RuntimeError):
    """An input or contract refusal. Carries a machine ``code``."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


class FindingJudgmentChainError(FindingJudgmentError):
    """A corrupt or forked judgment ledger."""


class FindingJudgmentEffectUnknownError(FindingJudgmentError):
    """A judgment write whose outcome could not be reconciled."""


# ---------------------------------------------------------------------------
# Canonical digests and clocks
# ---------------------------------------------------------------------------


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _content_digest(content: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(content)).hexdigest()


def _require_aware_utc(value: Any, *, code: str, label: str) -> datetime:
    """Normalize a caller-supplied clock; refuse absent or naive values."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise FindingJudgmentError(f"{label} must be an aware UTC datetime", code=code)
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        try:
            parsed = parse_utc(value, field=label)
        except ValueError as exc:
            raise FindingJudgmentError(str(exc), code=code) from exc
        if parsed is None:
            raise FindingJudgmentError(f"{label} is required", code=code)
        return parsed
    raise FindingJudgmentError(f"{label} must be an aware UTC datetime", code=code)


def _judgment_id(subject_key: str, content_sha256: str | None, supersedes: str | None) -> str:
    return stable_id("fjudgment", subject_key, content_sha256 or "withdrawn", supersedes or "")


def _detector_version_of(record: Mapping[str, Any] | None) -> Any:
    if not isinstance(record, Mapping):
        return None
    content = record.get("content")
    if not isinstance(content, Mapping):
        return None
    return content.get("detector_version")


def _batch_key(sequence: int) -> str:
    return f"{JUDGMENT_PREFIX}/batches/{sequence:08d}.json"


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------


def kernel_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize one kernel row shaped like ``Finding.to_dict()``.

    Required keys are never synthesized: a row missing one is refused.
    ``computed_at`` is excluded from the recorded content so a recomputation
    at a different time alone never mints a correction.
    """
    if not isinstance(row, Mapping):
        raise FindingJudgmentError("kernel finding row must be an object", code="kernel_row_required")
    missing = [key for key in _KERNEL_REQUIRED_KEYS if row.get(key) is None]
    if missing:
        raise FindingJudgmentError(
            "kernel finding row is missing required keys: " + ", ".join(sorted(missing)),
            code="kernel_row_required",
        )
    period_ends = row["period_ends"]
    if isinstance(period_ends, (str, bytes)) or not isinstance(period_ends, (list, tuple)):
        raise FindingJudgmentError("kernel finding row period_ends must be a list", code="kernel_row_required")
    content = {key: value for key, value in row.items() if key != "computed_at"}
    entity_cik = str(row["entity_cik"])
    source_ready_at = row.get("source_ready_at")
    if source_ready_at is not None:
        source_ready_at = str(source_ready_at)
    return {
        "subject_key": stable_id("fjsubject", "kernel", str(row["detector_id"]), entity_cik, *sorted(period_ends)),
        "entity_ref": entity_cik,
        "finding_ref": str(row["finding_id"]),
        "content": content,
        "content_sha256": _content_digest(content),
        "source_ready_at": source_ready_at,
    }


def _normalize_row(kind: str, row: Any) -> dict[str, Any]:
    if kind == "kernel":
        return kernel_row(row)
    # Workbench rows arrive already normalized by workbench_rows_from_state.
    if not isinstance(row, Mapping):
        raise FindingJudgmentError("workbench finding row must be an object", code="row_shape")
    missing = [key for key in ("subject_key", "entity_ref", "finding_ref", "content") if row.get(key) is None]
    if missing:
        raise FindingJudgmentError(
            "workbench finding row is missing required keys: " + ", ".join(sorted(missing)),
            code="row_shape",
        )
    content = row["content"]
    if not isinstance(content, Mapping):
        raise FindingJudgmentError("workbench finding row content must be an object", code="row_shape")
    source_ready_at = row.get("source_ready_at")
    return {
        "subject_key": str(row["subject_key"]),
        "entity_ref": str(row["entity_ref"]),
        "finding_ref": str(row["finding_ref"]),
        "content": dict(content),
        "content_sha256": _content_digest(content),
        "source_ready_at": None if source_ready_at is None else str(source_ready_at),
    }


def _cik_identity(value: Any) -> str | None:
    """Normalize a company CIK to its zero-padded 10-digit text."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise FindingJudgmentError("workbench company cik must be an int or a digit string", code="state_shape")
    if isinstance(value, int):
        if value < 0 or value >= 10**10:
            raise FindingJudgmentError(f"workbench company cik is out of range: {value!r}", code="state_shape")
        return str(value).zfill(10)
    if isinstance(value, str):
        if len(value) < 1 or len(value) > 10 or any(char not in "0123456789" for char in value):
            raise FindingJudgmentError(f"workbench company cik is not a digit string: {value!r}", code="state_shape")
        return value.zfill(10)
    raise FindingJudgmentError(f"workbench company cik must be an int or a digit string: {value!r}", code="state_shape")


def _symbol_identity(symbol: Any) -> str:
    text = str(symbol).strip().upper()
    if not text:
        raise FindingJudgmentError("workbench company symbol must be non-empty", code="state_shape")
    return f"symbol:{text}"


def workbench_rows_from_state(state: Mapping[str, Any]) -> tuple[list[dict[str, Any]], set[str], datetime]:
    """Derive workbench rows, the run's entity scope, and the state's clock.

    The returned clock is ``state["generated_at"]`` (missing or naive values
    are refused); the caller records it as the run's ``source_generated_at``,
    never as the recording clock. The subject identity is the normalized
    10-digit company CIK, or the stripped upper-cased symbol when the CIK is
    null. ``entity_ref`` uses the same basis, and the scope holds BOTH the
    CIK identity and the symbol identity for every company, so a subject
    recorded under the symbol one night and under the CIK the next is
    withdrawn instead of staying present forever.
    """
    if not isinstance(state, Mapping):
        raise FindingJudgmentError("workbench state must be an object", code="state_shape")
    clock = _require_aware_utc(state.get("generated_at"), code="recorded_at_required", label="generated_at")
    companies = state.get("companies")
    if not isinstance(companies, Mapping):
        raise FindingJudgmentError("workbench state companies must be an object", code="state_shape")
    rows: list[dict[str, Any]] = []
    scope_entities: set[str] = set()
    for symbol, company in companies.items():
        if not isinstance(company, Mapping):
            raise FindingJudgmentError(f"workbench company {symbol!r} must be an object", code="state_shape")
        symbol_ref = _symbol_identity(symbol)
        cik_ref = _cik_identity(company.get("cik"))
        identity = cik_ref if cik_ref is not None else symbol_ref
        scope_entities.add(identity)
        scope_entities.add(symbol_ref)
        findings = company.get("findings")
        if findings is None:
            findings = []
        if not isinstance(findings, list):
            raise FindingJudgmentError(f"workbench company {symbol!r} findings must be a list", code="state_shape")
        for finding in findings:
            if not isinstance(finding, Mapping) or finding.get("id") is None:
                raise FindingJudgmentError(
                    f"workbench company {symbol!r} has a finding without an id", code="state_shape"
                )
            finding_id = str(finding["id"])
            rows.append({
                "subject_key": stable_id("fjsubject", "workbench", identity, finding_id),
                "entity_ref": identity,
                "finding_ref": finding_id,
                "content": dict(finding),
                "content_sha256": _content_digest(finding),
                "source_ready_at": None,
            })
    return rows, scope_entities, clock


# ---------------------------------------------------------------------------
# Ledger view
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LedgerView:
    """Every subject chain of a loadable ledger, in chain order."""

    chains: dict[str, tuple[dict[str, Any], ...]]
    batch_keys: tuple[str, ...] = ()
    head_sequence: int = 0
    tip_sha256: str = ""
    head_version: str | None = None
    latest_recorded_at: str | None = None

    def tip(self, subject_key: str) -> dict[str, Any] | None:
        chain = self.chains.get(subject_key)
        if not chain:
            return None
        return chain[-1]


def _chain_error(message: str, *, code: str) -> FindingJudgmentChainError:
    return FindingJudgmentChainError(message, code=code)


def _validate_record(
    record: Any,
    *,
    batch_recorded_at: str,
    batch_source_generated_at: str | None,
    batch_key: str,
) -> None:
    if not isinstance(record, dict):
        raise _chain_error(f"judgment batch {batch_key} holds a non-object record", code="record_shape")
    for name in _RECORD_FIELDS:
        if name not in record:
            raise _chain_error(f"judgment record is missing the {name} field", code="record_shape")
    for name in ("judgment_id", "subject_key", "entity_ref", "finding_ref", "recorded_at"):
        if not isinstance(record[name], str) or not record[name]:
            raise _chain_error(f"judgment record field {name} must be a non-empty string", code="record_shape")
    if record["schema"] != JUDGMENT_SCHEMA:
        raise _chain_error(f"judgment record carries an unexpected schema: {record['schema']!r}", code="record_schema")
    if record["kind"] not in _KINDS:
        raise _chain_error(f"judgment record carries an unknown kind: {record['kind']!r}", code="record_shape")
    if record["status"] not in _STATUSES:
        raise _chain_error(f"judgment record carries an unknown status: {record['status']!r}", code="record_shape")
    if record["relation"] not in _RELATIONS:
        raise _chain_error(f"judgment record carries an unknown relation: {record['relation']!r}", code="record_shape")
    if record["relation"] == "original" and record["supersedes"] is not None:
        raise _chain_error("an original judgment may not name a superseded record", code="record_shape")
    if record["relation"] == "correction" and not isinstance(record["supersedes"], str):
        raise _chain_error("a correction must name the record it supersedes", code="record_shape")
    reasons = record["change_reasons"]
    if not isinstance(reasons, list) or any(item not in _CHANGE_REASON_VALUES for item in reasons):
        raise _chain_error("judgment change_reasons must be a list of known values", code="record_shape")
    if record["status"] == "withdrawn":
        if record["content"] is not None or record["content_sha256"] is not None:
            raise _chain_error("a withdrawn judgment must carry null content and digest", code="record_content")
    else:
        if not isinstance(record["content"], Mapping) or not isinstance(record["content_sha256"], str):
            raise _chain_error("a present judgment must carry content and its digest", code="record_content")
        if _content_digest(record["content"]) != record["content_sha256"]:
            raise _chain_error("judgment content digest does not recompute", code="content_digest_mismatch")
    expected_id = _judgment_id(record["subject_key"], record["content_sha256"], record["supersedes"])
    if record["judgment_id"] != expected_id:
        raise _chain_error("judgment id does not recompute from its own fields", code="judgment_id_mismatch")
    try:
        parse_utc(record["recorded_at"], field="recorded_at")
    except ValueError as exc:
        raise _chain_error(f"judgment recorded_at is not an aware timestamp: {exc}", code="record_clock") from exc
    if record["recorded_at"] != batch_recorded_at:
        raise _chain_error(
            "judgment recorded_at disagrees with its batch recorded_at", code="record_clock_mismatch"
        )
    if record["source_generated_at"] != batch_source_generated_at:
        raise _chain_error(
            "judgment source_generated_at disagrees with its batch source_generated_at",
            code="record_source_mismatch",
        )


def _assemble_chain(subject_key: str, records: list[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    originals = [record for record in records if record["relation"] == "original"]
    if not originals:
        raise _chain_error(f"subject {subject_key} has no original judgment", code="missing_original")
    if len(originals) > 1:
        raise _chain_error(f"subject {subject_key} has more than one original judgment", code="duplicate_original")
    chain = [originals[0]]
    remaining = [record for record in records if record is not originals[0]]
    while remaining:
        tip_id = chain[-1]["judgment_id"]
        successors = [record for record in remaining if record["supersedes"] == tip_id]
        if not successors:
            raise _chain_error(
                f"subject {subject_key} holds a record whose superseded target is absent", code="dangling_supersedes"
            )
        if len(successors) > 1:
            raise _chain_error(f"subject {subject_key} forks: a record is superseded twice", code="fork")
        chain.append(successors[0])
        remaining.remove(successors[0])
    clocks = [parse_utc(record["recorded_at"], field="recorded_at") for record in chain]
    for earlier, later in zip(clocks, clocks[1:]):
        if later < earlier:
            raise _chain_error(f"subject {subject_key} regresses its recorded clock", code="clock_regression")
    return tuple(chain)


def _load_head(store: Any) -> tuple[int | None, str | None, str | None]:
    """Read HEAD strictly; ``None`` sequence means an authoritatively empty ledger."""
    try:
        observed = store.get_bytes_strict_bounded_versioned(JUDGMENT_HEAD_KEY, _HEAD_READ_BOUND)
    except Exception as exc:  # noqa: BLE001 - a failed HEAD read is a ledger failure
        raise _chain_error(f"judgment HEAD read failed: {exc}", code="head_read_failed") from exc
    if observed.data is None:
        return None, None, None
    payload = observed.data
    try:
        body = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _chain_error("judgment HEAD is not decodable JSON", code="head_schema") from exc
    if not isinstance(body, dict) or body.get("schema") != JUDGMENT_HEAD_SCHEMA:
        raise _chain_error("judgment HEAD carries an unexpected schema", code="head_schema")
    if set(body) != {"schema", "sequence", "tip_sha256"}:
        raise _chain_error("judgment HEAD body is malformed", code="head_schema")
    sequence = body["sequence"]
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise _chain_error(f"judgment HEAD sequence is out of range: {sequence!r}", code="head_schema")
    if sequence > HARD_MAX_BATCHES:
        raise _chain_error(
            f"judgment ledger exceeds the hard batch limit ({sequence} > {HARD_MAX_BATCHES})", code="batch_limit"
        )
    tip_sha256 = body["tip_sha256"]
    if not isinstance(tip_sha256, str) or not _HEX64.fullmatch(tip_sha256):
        raise _chain_error("judgment HEAD tip_sha256 is not a sha256 hex digest", code="head_schema")
    if _canonical_json_bytes(body) != payload:
        raise _chain_error("judgment HEAD bytes are not canonical", code="head_schema")
    return sequence, tip_sha256, observed.version


def _read_batch_bytes(store: Any, sequence: int) -> bytes | None:
    key = _batch_key(sequence)
    try:
        return store.get_bytes_strict_bounded(key, HARD_MAX_BATCH_BYTES)
    except Exception as exc:  # noqa: BLE001 - a failed batch read is a ledger failure
        raise _chain_error(f"judgment batch {key} read failed: {exc}", code="batch_read_failed") from exc


def _verify_batch(
    payload: bytes,
    *,
    sequence: int,
    predecessor_sha256: str,
) -> tuple[str, datetime, Any, list[dict[str, Any]]]:
    """Verify one batch's bytes against its key, shape and predecessor."""
    key = _batch_key(sequence)
    try:
        body = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _chain_error(f"judgment batch {key} is not decodable JSON", code="batch_undecodable") from exc
    if not isinstance(body, dict) or body.get("schema") != JUDGMENT_BATCH_SCHEMA:
        raise _chain_error(f"judgment batch {key} carries an unexpected schema", code="batch_schema")
    if set(body) != set(_BATCH_FIELDS):
        raise _chain_error(f"judgment batch {key} body is malformed", code="batch_schema")
    body_sequence = body["sequence"]
    if isinstance(body_sequence, bool) or not isinstance(body_sequence, int) or body_sequence < 1:
        raise _chain_error(f"judgment batch {key} sequence is malformed", code="batch_schema")
    predecessor = body["predecessor_sha256"]
    if not isinstance(predecessor, str) or not (predecessor == "" or _HEX64.fullmatch(predecessor)):
        raise _chain_error(f"judgment batch {key} predecessor_sha256 is malformed", code="batch_schema")
    recorded_at = body["recorded_at"]
    if not isinstance(recorded_at, str) or not recorded_at:
        raise _chain_error(f"judgment batch {key} recorded_at is malformed", code="batch_schema")
    try:
        recorded_dt = parse_utc(recorded_at, field="recorded_at")
    except ValueError as exc:
        raise _chain_error(f"judgment batch {key} recorded_at is not an aware timestamp", code="batch_schema") from exc
    if not isinstance(body["records"], list):
        raise _chain_error(f"judgment batch {key} records are malformed", code="batch_schema")
    if _canonical_json_bytes(body) != payload:
        raise _chain_error(f"judgment batch {key} bytes are not canonical", code="batch_noncanonical")
    if body_sequence != sequence:
        raise _chain_error(
            f"judgment batch {key} disagrees with its body sequence {body_sequence}", code="batch_key_mismatch"
        )
    if predecessor != predecessor_sha256:
        raise _chain_error(f"judgment batch {key} breaks the hash chain", code="chain_hash_mismatch")
    return recorded_at, recorded_dt, body["source_generated_at"], body["records"]


def _verify_batch_source_generated_at(
    source_generated_at: Any,
    *,
    recorded_dt: datetime,
    sequence: int,
) -> None:
    key = _batch_key(sequence)
    if source_generated_at is None:
        return
    if not isinstance(source_generated_at, str):
        raise _chain_error(f"judgment batch {key} source_generated_at is malformed", code="batch_schema")
    try:
        source_dt = parse_utc(source_generated_at, field="source_generated_at")
    except ValueError as exc:
        raise _chain_error(
            f"judgment batch {key} source_generated_at is not an aware timestamp", code="batch_schema"
        ) from exc
    if source_dt > recorded_dt:
        raise _chain_error(f"judgment batch {key} source_generated_at follows its recorded_at", code="batch_schema")


def load_ledger(store: Any) -> LedgerView:
    """Read HEAD, then verify every referenced batch and assemble the chains.

    Batches are fetched strictly by their deterministic keys — never through
    a prefix listing — so a batch beyond HEAD.sequence stays invisible until
    a roll-forward advances HEAD to name it.
    """
    if store is None:
        raise FindingJudgmentError("a judgment store is required", code="store_required")
    sequence, tip_sha256, head_version = _load_head(store)
    empty = LedgerView(chains={}, batch_keys=(), head_sequence=0, tip_sha256="", head_version=None)
    if sequence is None:
        return empty
    batches: list[tuple[str, str, str | None, list[dict[str, Any]]]] = []
    predecessor = ""
    previous_recorded_dt: datetime | None = None
    for index in range(1, sequence + 1):
        key = _batch_key(index)
        payload = _read_batch_bytes(store, index)
        if payload is None:
            raise _chain_error(f"judgment batch {key} is absent on read-back", code="batch_missing")
        recorded_at, recorded_dt, source_generated_at, records = _verify_batch(
            payload, sequence=index, predecessor_sha256=predecessor
        )
        if previous_recorded_dt is not None and recorded_dt <= previous_recorded_dt:
            raise _chain_error(
                f"judgment batch {key} does not advance the ledger clock", code="batch_clock_regression"
            )
        previous_recorded_dt = recorded_dt
        _verify_batch_source_generated_at(source_generated_at, recorded_dt=recorded_dt, sequence=index)
        predecessor = hashlib.sha256(payload).hexdigest()
        batches.append((key, recorded_at, source_generated_at, records))
    if predecessor != tip_sha256:
        raise _chain_error("judgment HEAD tip does not match the final batch bytes", code="chain_hash_mismatch")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for key, recorded_at, source_generated_at, records in batches:
        for record in records:
            _validate_record(
                record,
                batch_recorded_at=recorded_at,
                batch_source_generated_at=source_generated_at,
                batch_key=key,
            )
            grouped.setdefault(record["subject_key"], []).append(record)
    chains = {
        subject_key: _assemble_chain(subject_key, records)
        for subject_key, records in grouped.items()
    }
    return LedgerView(
        chains=chains,
        batch_keys=tuple(key for key, _, _, _ in batches),
        head_sequence=sequence,
        tip_sha256=tip_sha256,
        head_version=head_version,
        latest_recorded_at=batches[-1][1],
    )


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------


def _read_back(store: Any, key: str, payload: bytes) -> bool | None:
    """True = exact bytes; False = different bytes; None = unreadable or absent."""
    try:
        observed = store.get_bytes_strict_bounded(key, HARD_MAX_BATCH_BYTES)
    except Exception:  # noqa: BLE001 - an unreadable outcome cannot settle anything
        return None
    if observed is None:
        return None
    return observed == payload


def _write_batch(store: Any, key: str, payload: bytes) -> None:
    """Create one immutable batch create-only, then prove its bytes.

    Exact bytes already present prove idempotent completion (our own
    committed write or a byte-identical concurrent run); different bytes at
    the sequence mean a concurrent writer won it; an outcome read-back
    cannot settle is EFFECT_UNKNOWN. This never falls back to an
    unconditional put, another key, or a retry loop.
    """
    written: bool | None
    try:
        written = store.put_bytes_strict_conditional(
            key,
            payload,
            expected_version=None,
            content_type="application/json",
        )
        raised: Exception | None = None
    except Exception as exc:  # noqa: BLE001 - the write may have committed
        written = None
        raised = exc
    reconcile = _read_back(store, key, payload)
    if reconcile is True:
        return
    if reconcile is None:
        raise FindingJudgmentEffectUnknownError(
            "judgment batch write outcome could not be reconciled", code="effect_unknown"
        )
    if written is True:
        raise FindingJudgmentError(
            f"judgment batch read-back mismatch at {key}", code="readback_mismatch"
        )
    if raised is not None:
        raise FindingJudgmentError(
            f"judgment batch bytes at {key} are not this run's bytes", code="head_conflict"
        ) from raised
    raise FindingJudgmentError(
        f"a concurrent writer won judgment batch sequence at {key}", code="head_conflict"
    )


def _write_head(store: Any, view: LedgerView, new_head_bytes: bytes) -> None:
    """Advance HEAD by one compare-and-swap on the version the writer loaded.

    A ``False`` or a raise is settled by one strict re-read: HEAD already
    holding the new bytes proves completion (a concurrent roll-forward or
    our own committed write); HEAD unchanged after a ``False`` is a conflict;
    HEAD unchanged after a raise, or an unreadable HEAD, is EFFECT_UNKNOWN —
    the batch exists and the next run's roll-forward completes it on the
    same store. Nothing is retried here.
    """
    raised: Exception | None = None
    try:
        written = store.put_bytes_strict_conditional(
            JUDGMENT_HEAD_KEY,
            new_head_bytes,
            expected_version=view.head_version,
            content_type="application/json",
        )
    except Exception as exc:  # noqa: BLE001 - the write may have committed
        written = None
        raised = exc
    if written is True:
        return
    try:
        observed = store.get_bytes_strict_bounded_versioned(JUDGMENT_HEAD_KEY, _HEAD_READ_BOUND)
    except Exception as exc:  # noqa: BLE001 - an unreadable HEAD cannot settle anything
        raise FindingJudgmentEffectUnknownError(
            "judgment HEAD write outcome could not be reconciled", code="effect_unknown"
        ) from exc
    if observed.data == new_head_bytes:
        return
    if view.head_version is None:
        unchanged = observed.data is None
    else:
        unchanged = observed.version == view.head_version
    if unchanged:
        if raised is not None:
            raise FindingJudgmentEffectUnknownError(
                f"judgment HEAD write failed without a settled outcome: {raised}", code="effect_unknown"
            ) from raised
        raise FindingJudgmentError(
            "a concurrent writer advanced the judgment HEAD", code="head_conflict"
        )
    raise FindingJudgmentError(
        "judgment HEAD holds unexpected bytes after a failed compare-and-swap", code="head_conflict"
    )


def _roll_forward(store: Any, view: LedgerView) -> LedgerView:
    """Complete an earlier run's committed batch by advancing HEAD to it.

    A batch at the next sequence with a matching predecessor is the residue
    of an interrupted HEAD write. At most one roll-forward happens per call;
    a further orphan beyond it is a refused orphan chain.
    """
    next_sequence = view.head_sequence + 1
    key = _batch_key(next_sequence)
    payload = _read_batch_bytes(store, next_sequence)
    if payload is None:
        return view
    try:
        recorded_at, recorded_dt, source_generated_at, records = _verify_batch(
            payload, sequence=next_sequence, predecessor_sha256=view.tip_sha256
        )
        if view.latest_recorded_at is not None:
            latest_dt = parse_utc(view.latest_recorded_at, field="recorded_at")
            if recorded_dt <= latest_dt:
                raise _chain_error(
                    f"orphan judgment batch {key} does not advance the ledger clock", code="orphan_batch_invalid"
                )
        _verify_batch_source_generated_at(
            source_generated_at, recorded_dt=recorded_dt, sequence=next_sequence
        )
        grouped: dict[str, list[dict[str, Any]]] = {
            subject_key: list(chain) for subject_key, chain in view.chains.items()
        }
        for record in records:
            _validate_record(
                record,
                batch_recorded_at=recorded_at,
                batch_source_generated_at=source_generated_at,
                batch_key=key,
            )
            grouped.setdefault(record["subject_key"], []).append(record)
        for subject_key, subject_records in grouped.items():
            _assemble_chain(subject_key, subject_records)
    except FindingJudgmentError as exc:
        raise _chain_error(f"orphan judgment batch {key} is invalid: {exc}", code="orphan_batch_invalid") from exc
    new_head = _canonical_json_bytes({
        "schema": JUDGMENT_HEAD_SCHEMA,
        "sequence": next_sequence,
        "tip_sha256": hashlib.sha256(payload).hexdigest(),
    })
    _write_head(store, view, new_head)
    reloaded = load_ledger(store)
    if _read_batch_bytes(store, reloaded.head_sequence + 1) is not None:
        raise _chain_error(
            f"judgment ledger holds an orphan chain beyond sequence {reloaded.head_sequence}", code="orphan_chain"
        )
    return reloaded


def _last_present_record(chain: tuple[dict[str, Any], ...]) -> dict[str, Any] | None:
    for record in reversed(chain):
        if record["status"] == "present":
            return record
    return None


def record_judgments(
    store: Any,
    *,
    kind: str,
    rows: Any,
    recorded_at: Any,
    source_generated_at: Any = None,
    scope_entities: Any = None,
) -> dict[str, Any]:
    """Append one batch of judgments for a recording run.

    Per subject: no prior tip appends an original; a present tip with the
    same content digest appends nothing; anything else appends a correction
    superseding the tip. Subjects of in-scope entities with no row this run
    and a present tip are withdrawn. When nothing is appended, no batch is
    written. The clock is caller-supplied and ledger-wide: it may never
    precede the latest batch's clock, and an equal clock is legal only for
    a run that appends nothing.
    """
    if kind not in _KINDS:
        raise FindingJudgmentError(f"unknown judgment kind: {kind!r}", code="kind")
    clock = _require_aware_utc(recorded_at, code="recorded_at_required", label="recorded_at")
    source_text: str | None = None
    if source_generated_at is not None:
        source_clock = _require_aware_utc(
            source_generated_at, code="source_generated_at_required", label="source_generated_at"
        )
        if source_clock > clock:
            raise FindingJudgmentError(
                f"recorded_at {utc_text(clock)} precedes source_generated_at {utc_text(source_clock)}",
                code="recorded_before_source",
            )
        source_text = utc_text(source_clock)
    if rows is None:
        rows = []
    if not isinstance(rows, (list, tuple)):
        raise FindingJudgmentError("rows must be a list of finding rows", code="rows_shape")
    normalized = [_normalize_row(kind, row) for row in rows]
    seen: set[str] = set()
    for row in normalized:
        if row["subject_key"] in seen:
            raise FindingJudgmentError(
                f"subject {row['subject_key']} appears twice in one recording run", code="duplicate_subject"
            )
        seen.add(row["subject_key"])
    view = _roll_forward(store, load_ledger(store))
    latest = view.latest_recorded_at
    if latest is not None and clock < parse_utc(latest, field="recorded_at"):
        raise FindingJudgmentError(
            f"recorded_at {utc_text(clock)} precedes the ledger tip at {latest}", code="clock_regression"
        )
    recorded_text = utc_text(clock)
    appended: list[dict[str, Any]] = []
    unchanged = 0
    for row in normalized:
        subject_key = row["subject_key"]
        chain = view.chains.get(subject_key)
        tip = chain[-1] if chain else None
        sha = row["content_sha256"]
        if tip is None:
            appended.append({
                "schema": JUDGMENT_SCHEMA,
                "judgment_id": _judgment_id(subject_key, sha, None),
                "kind": kind,
                "subject_key": subject_key,
                "entity_ref": row["entity_ref"],
                "finding_ref": row["finding_ref"],
                "content_sha256": sha,
                "content": row["content"],
                "status": "present",
                "relation": "original",
                "supersedes": None,
                "recorded_at": recorded_text,
                "source_ready_at": row["source_ready_at"],
                "source_generated_at": source_text,
                "change_reasons": [],
            })
            continue
        if tip["status"] == "present" and tip["content_sha256"] == sha:
            unchanged += 1
            continue
        if tip["status"] == "present":
            reference = tip
            reasons: set[str] = set()
        else:
            reference = _last_present_record(chain)
            reasons = {"status"}
        if reference is None or reference["content_sha256"] != sha:
            reasons.add("content")
        if _detector_version_of(reference) != row["content"].get("detector_version"):
            reasons.add("detector_version")
        appended.append({
            "schema": JUDGMENT_SCHEMA,
            "judgment_id": _judgment_id(subject_key, sha, tip["judgment_id"]),
            "kind": kind,
            "subject_key": subject_key,
            "entity_ref": row["entity_ref"],
            "finding_ref": row["finding_ref"],
            "content_sha256": sha,
            "content": row["content"],
            "status": "present",
            "relation": "correction",
            "supersedes": tip["judgment_id"],
            "recorded_at": recorded_text,
            "source_ready_at": row["source_ready_at"],
            "source_generated_at": source_text,
            "change_reasons": sorted(reasons),
        })
    if scope_entities is not None:
        if isinstance(scope_entities, (str, bytes)) or not isinstance(scope_entities, (set, frozenset, list, tuple)):
            raise FindingJudgmentError("scope_entities must be a set of entity_ref values", code="scope_shape")
        scope = {str(value) for value in scope_entities}
        for subject_key, chain in view.chains.items():
            if subject_key in seen:
                continue
            tip = chain[-1]
            if tip["kind"] != kind or tip["entity_ref"] not in scope or tip["status"] != "present":
                continue
            appended.append({
                "schema": JUDGMENT_SCHEMA,
                "judgment_id": _judgment_id(subject_key, None, tip["judgment_id"]),
                "kind": kind,
                "subject_key": subject_key,
                "entity_ref": tip["entity_ref"],
                "finding_ref": tip["finding_ref"],
                "content_sha256": None,
                "content": None,
                "status": "withdrawn",
                "relation": "correction",
                "supersedes": tip["judgment_id"],
                "recorded_at": recorded_text,
                "source_ready_at": None,
                "source_generated_at": source_text,
                "change_reasons": ["status"],
            })
    originals = sum(1 for record in appended if record["relation"] == "original")
    withdrawals = sum(1 for record in appended if record["status"] == "withdrawn")
    corrections = len(appended) - originals - withdrawals
    report: dict[str, Any] = {
        "schema": JUDGMENT_BATCH_SCHEMA,
        "recorded_at": recorded_text,
        "source_generated_at": source_text,
        "sequence": None,
        "batch_key": None,
        "originals": originals,
        "corrections": corrections,
        "withdrawals": withdrawals,
        "unchanged": unchanged,
    }
    if not appended:
        return report
    if latest is not None and clock == parse_utc(latest, field="recorded_at"):
        raise FindingJudgmentError(
            f"recorded_at {recorded_text} ties the ledger tip at {latest} and would append records",
            code="clock_regression",
        )
    if view.head_sequence >= HARD_MAX_BATCHES:
        raise FindingJudgmentError(
            f"judgment ledger is at the hard batch limit ({view.head_sequence} >= {HARD_MAX_BATCHES})",
            code="batch_limit",
        )
    sequence = view.head_sequence + 1
    key = _batch_key(sequence)
    body = {
        "schema": JUDGMENT_BATCH_SCHEMA,
        "sequence": sequence,
        "predecessor_sha256": view.tip_sha256,
        "recorded_at": recorded_text,
        "source_generated_at": source_text,
        "records": sorted(appended, key=lambda record: record["subject_key"]),
    }
    payload = _canonical_json_bytes(body)
    if len(payload) > HARD_MAX_BATCH_BYTES:
        raise FindingJudgmentError(
            f"judgment batch exceeds the hard byte limit ({len(payload)} > {HARD_MAX_BATCH_BYTES})",
            code="batch_oversize",
        )
    _write_batch(store, key, payload)
    new_head = _canonical_json_bytes({
        "schema": JUDGMENT_HEAD_SCHEMA,
        "sequence": sequence,
        "tip_sha256": hashlib.sha256(payload).hexdigest(),
    })
    _write_head(store, view, new_head)
    report["sequence"] = sequence
    report["batch_key"] = key
    return report


# ---------------------------------------------------------------------------
# Then-known replay
# ---------------------------------------------------------------------------


def _as_view(store_or_view: Any) -> LedgerView:
    if isinstance(store_or_view, LedgerView):
        return store_or_view
    return load_ledger(store_or_view)


def replay_then_known(
    store_or_view: Any,
    *,
    recorded_cutoff: Any,
    kind: str | None = None,
    entity_ref: str | None = None,
) -> dict[str, Any]:
    """Reconstruct the then-known belief of every subject at a cutoff.

    The visible record is the last chain record recorded at or before the
    cutoff; subjects with no visible record are omitted, and a visible
    withdrawn tip is returned as withdrawn. The cutoff is mandatory: it is
    never assumed to be the present moment.
    """
    cutoff = _require_aware_utc(recorded_cutoff, code="cutoff_required", label="recorded_cutoff")
    if kind is not None and kind not in _KINDS:
        raise FindingJudgmentError(f"unknown judgment kind: {kind!r}", code="kind")
    if entity_ref is not None and (not isinstance(entity_ref, str) or not entity_ref):
        raise FindingJudgmentError("entity_ref must be a non-empty string", code="entity_ref")
    view = _as_view(store_or_view)
    subjects: list[dict[str, Any]] = []
    for subject_key in sorted(view.chains):
        chain = view.chains[subject_key]
        visible = None
        versions_visible = 0
        for record in chain:
            if parse_utc(record["recorded_at"], field="recorded_at") <= cutoff:
                visible = record
                versions_visible += 1
        if visible is None:
            continue
        if kind is not None and visible["kind"] != kind:
            continue
        if entity_ref is not None and visible["entity_ref"] != entity_ref:
            continue
        subjects.append({
            "subject_key": subject_key,
            "kind": visible["kind"],
            "entity_ref": visible["entity_ref"],
            "visible": visible,
            "original_judgment_id": chain[0]["judgment_id"],
            "versions_visible": versions_visible,
            "versions_total": len(chain),
        })
    return {
        "schema": JUDGMENT_REPLAY_SCHEMA,
        "recorded_cutoff": utc_text(cutoff),
        "subjects": subjects,
    }


def history(store_or_view: Any, subject_key: str) -> tuple[dict[str, Any], ...]:
    """Return one subject's full chain, original first."""
    view = _as_view(store_or_view)
    return view.chains.get(subject_key, ())


__all__ = [
    "HARD_MAX_BATCHES",
    "HARD_MAX_BATCH_BYTES",
    "JUDGMENT_BATCH_SCHEMA",
    "JUDGMENT_HEAD_KEY",
    "JUDGMENT_HEAD_SCHEMA",
    "JUDGMENT_PREFIX",
    "JUDGMENT_REPLAY_SCHEMA",
    "JUDGMENT_SCHEMA",
    "FindingJudgmentChainError",
    "FindingJudgmentEffectUnknownError",
    "FindingJudgmentError",
    "LedgerView",
    "history",
    "kernel_row",
    "load_ledger",
    "record_judgments",
    "replay_then_known",
    "workbench_rows_from_state",
]
