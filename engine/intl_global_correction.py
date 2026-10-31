"""Superseding-revision correction receipts for global observations (E3).

Masterplan §12.4/§14 row 16, "Source correction / Correction propagation":
publish a superseding observation, invalidate dependent derived results and
preserve the original research record. This module is the engine half of that
rule: it mints a typed correction receipt (or abstains with a closed reason
vocabulary), names the derived results a correction invalidates — transitively,
without ever mutating or deleting them — and attests that a saved record's
digest survives the analysis unchanged.

Engine law: no invented signal, no causal verb, no score, no ranking and no
sizing live here. A correction receipt describes what superseded what, at
which revision, under which clocks; an abstaining receipt renders as withheld
with its closed reasons and never upgrades itself. Point-in-time only: the
later-version rule compares ingestion instants, and a session-dated
ingestion counts as the next day 00:00Z, never earlier.

Pure contract: no collector, no network, no UI, no pandas. It imports only
the frozen observation contract (:func:`engine.intl_global_observation.check_clocks`
and ``IDENTITY_FIELDS``' vocabulary) and the shared display vocabulary
(:func:`lib.intl_gs_display.format_clock`). The canonical-JSON sha256 digest
pattern is reused from ``engine/capital_structure/saved_scenarios.py`` by
pattern only — that module is never imported.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from engine.intl_global_observation import IDENTITY_FIELDS, check_clocks
from lib.intl_gs_display import format_clock

CONTRACT_VERSION = "intl-global-correction-v1"

#: The gate string of the only record type this contract corrects. A literal
#: here (not an import) keeps the correction contract's import surface at the
#: two admitted names; tests/test_intl_global_correction.py pins it to
#: engine.intl_global_observation.CONTRACT_VERSION so it cannot drift.
OBSERVATION_CONTRACT_VERSION = "intl-global-observation-v1"

#: Dislocation dependency shape (the one typed consumer contract).
DISLOCATION_CONTRACT_VERSION = "intl-global-dislocation-v1"

#: Every abstain reason, in the fixed emission order.
CORRECTION_ABSTAIN_REASONS = (
    "clock_missing",
    "clock_order_violation",
    "not_same_slot",
    "identical_content",
    "not_later_version",
)

#: The closed changed_fields path list, in the fixed order.
TRACKED_PATHS = (
    "state",
    "abstain_reasons",
    "value.pct",
    "decomposition.local_pct",
    "decomposition.fx_pct",
    "decomposition.usd_pct",
    "clocks.observation",
    "clocks.source_publication",
    "evidence_ref",
)

#: Numeric display paths, first match wins (NOT the changed_fields order).
DISPLAY_NUMERIC_PATHS = (
    "value.pct",
    "decomposition.usd_pct",
    "decomposition.local_pct",
    "decomposition.fx_pct",
)

#: (EN, ZH) leg labels for the display line.
FIELD_LABELS = {
    "value.pct": ("return", "收益"),
    "decomposition.usd_pct": ("USD return", "美元收益"),
    "decomposition.local_pct": ("local return", "本地收益"),
    "decomposition.fx_pct": ("FX return", "汇率收益"),
}

#: The slot is the identity WITHOUT the source content digest, so a new
#: vintage of the same observation is the same slot.
_SLOT_EXCLUDED_FIELD = "source_content_sha256"

assert _SLOT_EXCLUDED_FIELD in IDENTITY_FIELDS  # the vocabulary stays shared


class CorrectionError(ValueError):
    """Malformed correction request. The contract never guesses a revision."""


# ---------------------------------------------------------------------------
# Canonical encoding (the saved_scenarios digest pattern, reused by pattern)
# ---------------------------------------------------------------------------

def _canonical(payload) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _record_digest(record) -> str:
    return "sha256:" + _digest(_canonical(record))


# ---------------------------------------------------------------------------
# Clocks and instants
# ---------------------------------------------------------------------------

def _parse_instant(text) -> "datetime | None":
    """UTC instant of an ISO-8601 string; naive is UTC; None when unusable."""
    try:
        moment = datetime.fromisoformat(str(text).strip().replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _clock_of(record: dict, name: str) -> "dict | None":
    clocks = record.get("clocks")
    clock = clocks.get(name) if isinstance(clocks, dict) else None
    return clock if isinstance(clock, dict) else None


def _ingestion_instant(record: dict) -> "datetime | None":
    clock = _clock_of(record, "ingestion")
    return _parse_instant(clock.get("at")) if clock is not None else None


def _effective_ingestion_instant(record: dict) -> "datetime | None":
    """The comparable ingestion instant; a session_date is next day 00:00Z."""
    clock = _clock_of(record, "ingestion")
    moment = _ingestion_instant(record)
    if clock is None or moment is None:
        return None
    if clock.get("precision") == "session_date":
        day = moment.date() + timedelta(days=1)
        return datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    return moment


# ---------------------------------------------------------------------------
# Record accessors
# ---------------------------------------------------------------------------

def _is_observation(record) -> bool:
    return (isinstance(record, dict)
            and record.get("contract_version") == OBSERVATION_CONTRACT_VERSION)


def _identity_of(record: dict) -> dict:
    identity = record.get("identity")
    return identity if isinstance(identity, dict) else {}


def _slot_of(record: dict) -> str:
    """'slot:sha256:' + sha256 over the canonical identity minus the source.

    Byte-identical to the E1 replay contract's slot_key encoding; E1 is not
    imported (and is not merged yet), so this re-derives the same encoding
    from the frozen definition instead of reaching for an absent module.
    """
    identity = {key: value for key, value in _identity_of(record).items()
                if key != _SLOT_EXCLUDED_FIELD}
    return "slot:sha256:" + _digest(_canonical(identity))


def _read_path(record: dict, path: str):
    """Dotted-path read; any missing hop renders None."""
    value = record
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


# ---------------------------------------------------------------------------
# correction_receipt
# ---------------------------------------------------------------------------

def _abstain_reasons(original: dict, corrected: dict) -> list[str]:
    """Every applicable reason, in the fixed order."""
    reasons = []
    original_at = _effective_ingestion_instant(original)
    corrected_at = _effective_ingestion_instant(corrected)
    if original_at is None or corrected_at is None:
        reasons.append("clock_missing")
    if check_clocks(corrected.get("clocks")) is not None:
        reasons.append("clock_order_violation")
    if _slot_of(original) != _slot_of(corrected):
        reasons.append("not_same_slot")
    same_id = (original.get("observation_id") == corrected.get("observation_id"))
    same_content = (_identity_of(original).get(_SLOT_EXCLUDED_FIELD)
                    == _identity_of(corrected).get(_SLOT_EXCLUDED_FIELD))
    if same_id or same_content:
        reasons.append("identical_content")
    if (original_at is not None and corrected_at is not None
            and corrected_at <= original_at):
        reasons.append("not_later_version")
    assert reasons == [reason for reason in CORRECTION_ABSTAIN_REASONS
                       if reason in reasons]
    return reasons


def _changed_fields(original: dict, corrected: dict) -> list[dict]:
    entries = []
    for path in TRACKED_PATHS:
        old, new = _read_path(original, path), _read_path(corrected, path)
        if old != new:
            entries.append({"path": path, "old": old, "new": new})
    return entries


def _display(original: dict, corrected: dict) -> dict:
    identity = _identity_of(corrected)
    universe_id, horizon = identity.get("universe_id"), identity.get("horizon")
    clock = _clock_of(corrected, "source_publication")
    clock_at = clock.get("at") if clock is not None else None
    shown = None
    if clock_at:
        try:
            shown = format_clock(clock_at)
        except ValueError:  # never echo an unparseable clock into markup
            shown = None
    numeric = None
    for path in DISPLAY_NUMERIC_PATHS:
        old, new = _read_path(original, path), _read_path(corrected, path)
        if _is_number(old) and _is_number(new) and old != new:
            numeric = (path, old, new)
            break
    if numeric is None:
        if shown is None:  # unreachable through the abstain gate
            return {"en": f"Corrected · {universe_id} {horizon}",
                    "zh": f"已更正 · {universe_id} {horizon}"}
        return {"en": f"Corrected {shown['en']} · {universe_id} {horizon}",
                "zh": f"已更正 {shown['zh']} · {universe_id} {horizon}"}
    path, old, new = numeric
    label_en, label_zh = FIELD_LABELS[path]
    if shown is None:
        return {"en": f"Corrected {label_en} {old:.2f}% → {new:.2f}%",
                "zh": f"已更正 {label_zh} {old:.2f}% → {new:.2f}%"}
    return {
        "en": (f"Corrected {shown['en']} · {universe_id} {horizon} "
               f"{label_en} {old:.2f}% → {new:.2f}%"),
        "zh": (f"已更正 {shown['zh']} · {universe_id} {horizon} "
               f"{label_zh} {old:.2f}% → {new:.2f}%"),
    }


def correction_receipt(original: dict, corrected: dict, *, prior_revision=0) -> dict:
    """One superseding-revision receipt, or an abstaining receipt.

    Both inputs must be ``intl-global-observation-v1`` records. Inputs are
    deep-copied on entry and never mutated.
    """
    if not _is_observation(original) or not _is_observation(corrected):
        raise CorrectionError("not_an_observation")
    original, corrected = deepcopy(original), deepcopy(corrected)

    reasons = _abstain_reasons(original, corrected)
    is_corrected = not reasons
    slot = _slot_of(corrected)
    original_id = original.get("observation_id")
    corrected_id = corrected.get("observation_id")
    revision = ({"revision": prior_revision + 1, "supersedes": original_id}
                if is_corrected else None)
    correction_id = "corr:sha256:" + _digest(_canonical({
        "contract_version": CONTRACT_VERSION,
        "slot": slot,
        "original_id": original_id,
        "corrected_id": corrected_id,
        "revision": revision["revision"] if revision is not None else None,
    }))
    changed_fields = _changed_fields(original, corrected)
    caveats = []
    if is_corrected and not changed_fields:
        caveats.append("content_changed_no_tracked_field")
    return {
        "contract_version": CONTRACT_VERSION,
        "correction_id": correction_id,
        "slot": slot,
        "original_id": original_id,
        "corrected_id": corrected_id,
        "revision": revision,
        "clocks": {
            "original_ingestion": deepcopy(_clock_of(original, "ingestion")),
            "corrected_ingestion": deepcopy(_clock_of(corrected, "ingestion")),
            "corrected_source_publication":
                deepcopy(_clock_of(corrected, "source_publication")),
        },
        "changed_fields": changed_fields,
        "caveats": sorted(caveats),
        "state": "corrected" if is_corrected else "abstain",
        "abstain_reasons": reasons,
        "display": _display(original, corrected) if is_corrected else None,
    }


# ---------------------------------------------------------------------------
# correction_chain
# ---------------------------------------------------------------------------

def correction_chain(versions: list) -> dict:
    """Receipts over an ordered version history of one slot.

    Duplicates by observation_id collapse, versions order by ingestion instant
    then observation_id, and receipt i compares versions[i] -> versions[i+1]
    with prior_revision = i, so revisions number 1..n-1.
    """
    for version in versions:
        if not _is_observation(version):
            raise CorrectionError("not_an_observation")
    unique, seen = [], set()
    for version in versions:
        version_id = version.get("observation_id")
        if version_id not in seen:
            seen.add(version_id)
            unique.append(version)
    slots = {_slot_of(version) for version in unique}
    if len(slots) > 1:
        raise CorrectionError("not_same_slot")
    ordered = sorted(
        unique,
        key=lambda version: (
            _effective_ingestion_instant(version)
            or datetime.min.replace(tzinfo=timezone.utc),
            version.get("observation_id") or ""))
    ids = [version.get("observation_id") for version in ordered]
    receipts = [correction_receipt(ordered[i], ordered[i + 1], prior_revision=i)
                for i in range(len(ordered) - 1)]
    return {
        "contract_version": CONTRACT_VERSION,
        "slot": _slot_of(ordered[0]) if ordered else None,
        "versions": ids,
        "receipts": receipts,
        "head": ids[-1] if ids else None,
    }


# ---------------------------------------------------------------------------
# invalidated (dependent derived results)
# ---------------------------------------------------------------------------

def _dependency_axes(record) -> "tuple[str, set]":
    """(dependency_id, consumed ids) for one derived record."""
    if isinstance(record, dict) and record.get(
            "contract_version") == DISLOCATION_CONTRACT_VERSION:
        subject = record.get("subject")
        references = record.get("references")
        references = references if isinstance(references, dict) else {}
        dependency_id = record.get("dislocation_id")
        consumes = []
        if isinstance(subject, dict) and subject.get("observation_id") is not None:
            consumes.append(subject["observation_id"])
        consumes.extend(references.get("used_observation_ids") or [])
        consumes.extend(references.get("subject_block_ids") or [])
    else:
        dependency_id = record.get("dependency_id") if isinstance(record, dict) else None
        consumes = record.get("consumes") if isinstance(record, dict) else None
        if not isinstance(consumes, list):
            raise CorrectionError("derived_record_shape")
    if not isinstance(dependency_id, str) or not dependency_id:
        raise CorrectionError("derived_record_shape")
    return dependency_id, set(consumes)


def invalidated(receipt: dict, derived: list) -> dict:
    """Name every derived result the correction invalidates, transitively.

    Never mutates or deletes a derived record — it only names them. A record
    consuming an invalidated dependency_id is invalidated too; paths carry one
    shortest chain each (BFS, ties by ascending id).
    """
    correction_id = receipt.get("correction_id")
    if receipt.get("state") != "corrected":
        return {
            "correction_id": correction_id,
            "invalidated": [],
            "unaffected_count": len(derived),
            "paths": {},
            "withheld_reason": "receipt_not_corrected",
        }
    original_id = receipt.get("original_id")
    axes = [_dependency_axes(record) for record in derived]
    consumers = {}
    for dependency_id, consumed in axes:
        for token in consumed:
            consumers.setdefault(token, set()).add(dependency_id)
    # Breadth-first distances from the superseded observation.
    distance = {original_id: 0}
    frontier = [original_id]
    while frontier:
        next_frontier = []
        for node in frontier:
            for neighbour in sorted(consumers.get(node, ())):
                if neighbour not in distance:
                    distance[neighbour] = distance[node] + 1
                    next_frontier.append(neighbour)
        frontier = next_frontier
    invalidated_ids = sorted(
        dependency_id for dependency_id in distance if dependency_id != original_id)
    by_id = {}
    for dependency_id, consumed in axes:
        by_id.setdefault(dependency_id, set()).update(consumed)
    paths = {}
    for dependency_id in invalidated_ids:
        chain = [dependency_id]
        node = dependency_id
        while node != original_id:
            step = distance[node] - 1
            predecessors = [token for token in by_id[node]
                            if distance.get(token) == step]
            node = min(predecessors)  # ties resolve by ascending id
            chain.append(node)
        paths[dependency_id] = list(reversed(chain))
    invalidated_records = sum(1 for dependency_id, _ in axes
                              if dependency_id in invalidated_ids)
    return {
        "correction_id": correction_id,
        "invalidated": invalidated_ids,
        "unaffected_count": len(derived) - invalidated_records,
        "paths": paths,
        "withheld_reason": None,
    }


# ---------------------------------------------------------------------------
# saved_evidence (the original research record is preserved)
# ---------------------------------------------------------------------------

def _iter_string_values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_string_values(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _iter_string_values(item)


def saved_evidence(record, receipt: dict) -> dict:
    """Attest that the saved record's digest survives the analysis unchanged.

    digest = canonical-JSON sha256 before and after; preserved must be True.
    affected means the superseded original_id occurs in any string value
    anywhere in the record (deep walk).
    """
    digest_before = _record_digest(record)
    original_id = receipt.get("original_id")
    affected = any(original_id is not None and original_id in text
                   for text in _iter_string_values(record))
    digest_after = _record_digest(record)
    superseded_by = (receipt.get("corrected_id")
                     if affected and receipt.get("state") == "corrected" else None)
    return {
        "record_digest_before": digest_before,
        "record_digest_after": digest_after,
        "preserved": digest_before == digest_after,
        "affected": affected,
        "superseded_by": superseded_by,
    }
