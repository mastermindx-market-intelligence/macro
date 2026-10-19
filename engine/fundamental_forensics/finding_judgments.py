"""FIF Q2 finding-judgment ledger: then-known beliefs, immutable originals (A48).

Acceptance case A48 preserves the original judgment/version of a finding:
delayed evidence never rewrites past apparent knowledge. A later build that
changes or drops a finding may not silently replace the earlier view, so this
module owns three things:

* an append-only ledger of judgment records over a strict-conditional object
  store. One batch object is written per recording run; a record is never
  edited or deleted. A correction is a NEW record that names the record it
  supersedes, and a withdrawal is a correction whose content is null;
* a then-known replay reader that reconstructs, for a caller-supplied cutoff,
  the last belief recorded at or before that cutoff (a visible withdrawal is
  returned as withdrawn);
* two adapters: the nightly workbench build state and kernel rows shaped like
  ``Finding.to_dict()``.

Clock law: every timestamp is supplied by the caller. The recording clock is
the workbench state's ``generated_at`` or an explicit kernel-run argument,
and a replay cutoff is mandatory — a missing cutoff is never treated as the
present moment. No function in this module consults the operating-system
clock.

Write law: batches are created only through
``put_bytes_strict_conditional(key, payload, expected_version=None)`` followed
by a bounded read-back. Exact bytes already present prove idempotent
completion; different bytes at the same key are a collision; an outcome that
read-back cannot settle is EFFECT_UNKNOWN and is never retried or rerouted
here.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from .models import parse_utc, stable_id, utc_text

JUDGMENT_SCHEMA = "fundamental_forensics.finding_judgment/v1"
JUDGMENT_BATCH_SCHEMA = "fundamental_forensics.finding_judgment_batch/v1"
JUDGMENT_REPLAY_SCHEMA = "fundamental_forensics.finding_judgment_replay/v1"
JUDGMENT_PREFIX = "fundamental_forensics/finding-judgments/v1"
HARD_MAX_BATCH_BYTES = 8 * 1024 * 1024
HARD_MAX_BATCHES = 5000

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
    "change_reasons",
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
    """A judgment batch write whose outcome could not be reconciled."""


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


def _compact_stamp(clock: datetime) -> str:
    return clock.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _judgment_id(subject_key: str, content_sha256: str | None, supersedes: str | None) -> str:
    return stable_id("fjudgment", subject_key, content_sha256 or "withdrawn", supersedes or "")


def _detector_version_of(record: Mapping[str, Any]) -> Any:
    content = record.get("content")
    if not isinstance(content, Mapping):
        return None
    return content.get("detector_version")


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


def workbench_rows_from_state(state: Mapping[str, Any]) -> tuple[list[dict[str, Any]], set[str], datetime]:
    """Derive workbench rows, the run's entity scope, and its clock from a build state.

    The clock is ``state["generated_at"]`` (missing or naive values are
    refused). The subject identity is the company CIK as text, or the symbol
    when the CIK is null; ``entity_ref`` uses the same basis so the withdrawal
    scope stays joinable. Every company present in the state is in scope.
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
        cik = company.get("cik")
        identity = str(cik) if cik is not None else str(symbol)
        scope_entities.add(identity)
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

    def tip(self, subject_key: str) -> dict[str, Any] | None:
        chain = self.chains.get(subject_key)
        if not chain:
            return None
        return chain[-1]


def _chain_error(message: str, *, code: str) -> FindingJudgmentChainError:
    return FindingJudgmentChainError(message, code=code)


def _validate_record(record: Any, *, batch_recorded_at: str, batch_key: str) -> None:
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
        raise _chain_error(f"judgment recorded_at is not an aware timestamp: {exc}") from exc
    if record["recorded_at"] != batch_recorded_at:
        raise _chain_error(
            "judgment recorded_at disagrees with its batch recorded_at", code="record_clock_mismatch"
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


def load_ledger(store: Any) -> LedgerView:
    """Read and verify every judgment batch, then assemble the subject chains."""
    if store is None:
        raise FindingJudgmentError("a judgment store is required", code="store_required")
    prefix = JUDGMENT_PREFIX + "/batches/"
    try:
        keys = sorted(store.list_prefix(prefix))
    except FindingJudgmentError:
        raise
    except Exception as exc:  # noqa: BLE001 - listing failures are ledger failures
        raise _chain_error(f"judgment batch listing failed: {exc}") from exc
    if len(keys) > HARD_MAX_BATCHES:
        raise _chain_error(
            f"judgment ledger exceeds the hard batch limit ({len(keys)} > {HARD_MAX_BATCHES})", code="batch_limit"
        )
    batches: list[tuple[str, str, list[dict[str, Any]]]] = []
    for key in keys:
        try:
            payload = store.get_bytes_strict_bounded(key, HARD_MAX_BATCH_BYTES)
        except FindingJudgmentError:
            raise
        except Exception as exc:  # noqa: BLE001 - oversize/failed reads are ledger failures
            raise _chain_error(f"judgment batch {key} exceeded its read bound: {exc}", code="batch_oversize") from exc
        if payload is None:
            raise _chain_error(f"judgment batch {key} is absent on read-back", code="batch_missing")
        try:
            body = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _chain_error(f"judgment batch {key} is not decodable JSON", code="batch_undecodable") from exc
        if not isinstance(body, dict) or body.get("schema") != JUDGMENT_BATCH_SCHEMA:
            raise _chain_error(f"judgment batch {key} carries an unexpected schema", code="batch_schema")
        records = body.get("records")
        recorded_at = body.get("recorded_at")
        if not isinstance(records, list) or not isinstance(recorded_at, str) or not recorded_at:
            raise _chain_error(f"judgment batch {key} body is malformed", code="batch_schema")
        batches.append((recorded_at, key, records))
    batches.sort(key=lambda item: (item[0], item[1]))
    grouped: dict[str, list[dict[str, Any]]] = {}
    for recorded_at, key, records in batches:
        for record in records:
            _validate_record(record, batch_recorded_at=recorded_at, batch_key=key)
            grouped.setdefault(record["subject_key"], []).append(record)
    chains = {
        subject_key: _assemble_chain(subject_key, records)
        for subject_key, records in grouped.items()
    }
    return LedgerView(chains=chains, batch_keys=tuple(key for _, key, _ in batches))


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
    """Create one immutable batch, then prove its bytes (A18 write law).

    An exceptional or False outcome receives bounded read-back reconciliation
    only; this never falls back to an unconditional put. Exact bytes already
    present prove idempotent completion; different bytes are a collision;
    anything else preserves EFFECT_UNKNOWN as a hard error on the original
    target. Nothing else is written in this call.
    """
    try:
        written = store.put_bytes_strict_conditional(
            key,
            payload,
            expected_version=None,
            content_type="application/json",
        )
    except Exception as exc:  # noqa: BLE001 - the write may have committed
        reconcile = _read_back(store, key, payload)
        if reconcile is None:
            raise FindingJudgmentEffectUnknownError(
                "judgment batch write outcome could not be reconciled", code="effect_unknown"
            ) from exc
        if reconcile is False:
            raise FindingJudgmentError(
                f"judgment batch collision at existing key {key}", code="batch_collision"
            ) from exc
        return
    if written is True:
        if _read_back(store, key, payload) is not True:
            raise FindingJudgmentError(
                f"judgment batch read-back mismatch at {key}", code="batch_collision"
            )
        return
    if written is False:
        reconcile = _read_back(store, key, payload)
        if reconcile is True:
            return
        if reconcile is False:
            raise FindingJudgmentError(
                f"judgment batch collision at existing key {key}", code="batch_collision"
            )
        raise FindingJudgmentEffectUnknownError(
            "judgment batch write outcome could not be reconciled", code="effect_unknown"
        )
    raise FindingJudgmentError("judgment batch write was refused by the store", code="write_refused")


def _batch_key(clock: datetime, records: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256(_canonical_json_bytes(records)).hexdigest()[:16]
    return f"{JUDGMENT_PREFIX}/batches/{_compact_stamp(clock)}-{digest}.json"


def record_judgments(
    store: Any,
    *,
    kind: str,
    rows: Any,
    recorded_at: Any,
    scope_entities: Any = None,
) -> dict[str, Any]:
    """Append one batch of judgments for a recording run.

    Per subject: no prior tip appends an original; a present tip with the
    same content digest appends nothing; anything else appends a correction
    superseding the tip. Subjects of in-scope entities with no row this run
    and a present tip are withdrawn. When nothing is appended, no batch is
    written. The clock is caller-supplied and may never precede a tip.
    """
    if kind not in _KINDS:
        raise FindingJudgmentError(f"unknown judgment kind: {kind!r}", code="kind")
    clock = _require_aware_utc(recorded_at, code="recorded_at_required", label="recorded_at")
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
    view = load_ledger(store)
    recorded_text = utc_text(clock)
    appended: list[dict[str, Any]] = []
    unchanged = 0
    for row in normalized:
        subject_key = row["subject_key"]
        tip = view.tip(subject_key)
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
                "change_reasons": [],
            })
            continue
        if tip["status"] == "present" and tip["content_sha256"] == sha:
            unchanged += 1
            continue
        tip_clock = parse_utc(tip["recorded_at"], field="recorded_at")
        if clock < tip_clock:
            raise FindingJudgmentError(
                f"recorded_at {recorded_text} precedes the subject tip at {tip['recorded_at']}",
                code="clock_regression",
            )
        reasons = set()
        if tip["content_sha256"] != sha:
            reasons.add("content")
        if tip["status"] != "present":
            reasons.add("status")
        if _detector_version_of(tip) != row["content"].get("detector_version"):
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
                "change_reasons": ["status"],
            })
    originals = sum(1 for record in appended if record["relation"] == "original")
    withdrawals = sum(1 for record in appended if record["status"] == "withdrawn")
    corrections = len(appended) - originals - withdrawals
    report: dict[str, Any] = {
        "schema": JUDGMENT_BATCH_SCHEMA,
        "recorded_at": recorded_text,
        "batch_key": None,
        "originals": originals,
        "corrections": corrections,
        "withdrawals": withdrawals,
        "unchanged": unchanged,
    }
    if not appended:
        return report
    records = sorted(appended, key=lambda record: record["subject_key"])
    key = _batch_key(clock, records)
    body = {
        "schema": JUDGMENT_BATCH_SCHEMA,
        "recorded_at": recorded_text,
        "records": records,
    }
    payload = _canonical_json_bytes(body)
    if len(payload) > HARD_MAX_BATCH_BYTES:
        raise FindingJudgmentError(
            f"judgment batch exceeds the hard byte limit ({len(payload)} > {HARD_MAX_BATCH_BYTES})",
            code="batch_oversize",
        )
    _write_batch(store, key, payload)
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
