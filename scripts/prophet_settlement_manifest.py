#!/usr/bin/env python3
"""Prophet US settlement manifest — the machine-verifiable reader-side
``prophet.settlement_manifest/v1`` projection (masterplan §18.1-§18.2, §21 V4-A2).

WHAT BROKE (2026-10-30, audit prophet-v4-a2-adoption-audit-20261030-01).  The
public R2 health receipt (``prophet.public_health/v1``) republished fresh while
the board's ``source_asof`` lagged the owed session.  Every green instrument
that reads publication metadata said HEALTHY; none of them proves a reader ever
saw the owed session.  Publication freshness is not settlement — the receipt is
emitted by the publisher about itself, so it can never be the thing it attests.

THE CHAIN (masterplan §18.1).  For every owed NYSE session::

    owed_session → source_asof → computed_asof → artifact_asof
                → published_asof → reader_visible_asof

``SETTLED`` only when the reader-visible projection carries the owed session
AND the exact bytes a reader receives are the accepted bundle.  Concretely,
this module returns ``SETTLED`` if and only if ALL of:

  * ``owed_session`` is a qualified session date and the accepted receipt's
    ``source_asof`` is qualified and >= it (a gate-skip or any other no-advance
    night fails here even when ``published_at`` is minutes old — the 10-30
    shape);
  * SHA-256 of the caller-supplied production-served ``index.json`` BYTES
    equals the receipt's ``index_sha256`` — RAW bytes, never reserialized.
    A semantically identical re-dump is a DIFFERENT bundle and must stay
    PENDING (the served tree is authoritative, not its meaning);
  * the served JSON's own ``source_asof`` equals the accepted receipt's
    (the served/health split-brain is loud, §18.3);
  * the caller's own read clock is supplied and explicitly UTC;
  * a genuine caller-recorded compute clock is supplied and explicitly UTC;
  * the served index proves the negative on vintage: ``source_delayed``,
    ``source_unknown`` and ``source_mixed_vintage`` are each exactly
    ``false`` — an absent or null flag is NOT proven clean and fails closed;
  * the receipt itself is the accepted shape (schema, qualified 64-hex
    lowercase ``index_sha256``, qualified UTC ``published_at``, non-empty
    ``checkpoint``);
  * the §18.2 accepted build bundle is proven as a WHOLE and BOUND: the
    caller supplies the full four-asset raw hash map (``candidate_store``,
    ``board``, ``index``, ``theme_state``) whose ``index`` entry hashes the
    exact served bytes, a SOURCE-ISSUED accepted bundle reference
    (``accepted_bundle``: ``bundle_id``, ``board_definition``,
    ``candidate_count``, and the issuer's own four-asset hash map), and the
    reader-served bundle identity (``reader_proof.served_bundle_id``) — and
    all three agree: reader map == issuer map, issuer index hash ==
    receipt ``index_sha256``, issuer ``bundle_id`` == reader
    ``served_bundle_id``.

BUNDLE BINDING LAW (§18.2, fail closed).  The multi-asset binding is never
inferred.  A single index hash — however exactly it matches the accepted
receipt — proves one asset, not the accepted bundle; the projection will not
reconstruct the remaining assets, and a map carrying entries outside the
frozen four is not the bundle either.  The bundle identity is injected
issuer/reader evidence: the projection never mints one (an id it computed
itself — from the served bytes, the receipt, anything — would manufacture
the very attestation it is supposed to judge), and it never borrows the
receipt's ``checkpoint``, which is the source git archive commit, a
different identity from the published bundle.  An injected ``bundle_id``
equal to the receipt checkpoint is the conflation defect itself and stays
PENDING.

ACCEPTANCE-SIDE HANDOFF.  Until the publisher/readers actually issue the
accepted bundle reference and the served-identity proof, callers that bind
no bundle evidence — the incumbent sentinel read model
``project_prophet_settlement_from_reads`` among them — get ``PENDING`` with
typed missing-evidence codes even when every other gate is green.  That is
deliberate: it closes the reproduced false green in which a settled verdict
was reachable with ``artifact_hashes`` null.

Anything less is ``PENDING`` (judged, not settled) or ``UNAVAILABLE_DATA``
(blind).  Blindness is reserved for what the sentinel calls INDETERMINATE
(a read that could not be made: no bytes, unparseable bytes, no receipt) or a
malformed ``owed_session`` (nothing can be owed).  A definitive read of a wrong
artifact (schema mismatch, digest mismatch, stale source, incomplete or
mismatched bundle binding) is a JUDGED failure — ``PENDING`` — never
blindness.  Missing reader clock, missing receipt hash and missing bundle
evidence fail closed: none of them can ever be inferred.

OWNER BINDING — why the interface takes evidence, not endpoints.  This module
performs NO I/O: the caller supplies (a) the exact production-served bytes,
(b) its own read clock, (c) the accepted publisher receipt.  That keeps the
settlement AUTHORITY in this pure projection while the reader-side OWNERSHIP —
who may read the served tree behind the registration wall, and whose clock
counts — stays with the availability lane's existing instruments
(``scripts/freshness_sentinel.py`` reads the served bytes it already watches;
``scripts/prophet_rescue.py`` already fetches the R2 receipt).  It is the same
injection boundary rescue froze for its own pure core ("``decide`` reads no
clock and opens no socket — ``state.now`` is injected"): a manifest function
that opened sockets or read the wall clock itself would manufacture its own
evidence, and a manifest is exactly the thing that must not do that.

SAFETY LAWS.  No disk or network writes, no global clock, no persisted state,
no random.  ``computed_at`` is echoed back ONLY when the caller supplies a
genuine recorded clock; it is never synthesized from run time, and the index's
own re-stampable ``asof``/``recorded_at`` run-clock fields are deliberately not
consulted (the ``build_prophet`` field comment already tells sentinels to use
``source_asof`` for exactly this reason).  The envelope is CLOSED: exactly the
fields listed in ``MANIFEST_FIELDS`` — no plans, no tickers, no index dump, no
paths, no secrets; failures are codes from ``FAILURE_CODES`` and nothing else.

This is the V4-A2 delta (wave-graph §4 ruling 11: A2 is adopt-first, sibling
owner).  The accepted A1/availability machinery — publisher, checkpoint, R2
receipt, sentinel, rescue — is used as-is and is not modified or re-derived
here; this module only binds their accepted outputs into one verdict.

Run: python3 -m pytest tests/test_prophet_settlement_manifest.py -q
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from datetime import date, datetime, timedelta

__all__ = [
    "SETTLEMENT_SCHEMA",
    "INDEX_SCHEMA",
    "HEALTH_SCHEMA",
    "STATUS_SETTLED",
    "STATUS_PENDING",
    "STATUS_UNAVAILABLE_DATA",
    "FAILURE_CODES",
    "MANIFEST_FIELDS",
    "VINTAGE_FLAGS",
    "REQUIRED_BUNDLE_ARTIFACT_KEYS",
    "project_settlement_manifest",
]

SETTLEMENT_SCHEMA = "prophet.settlement_manifest/v1"
INDEX_SCHEMA = "prophet.index/v1"
HEALTH_SCHEMA = "prophet.public_health/v1"

STATUS_SETTLED = "SETTLED"
STATUS_PENDING = "PENDING"
STATUS_UNAVAILABLE_DATA = "UNAVAILABLE_DATA"

#: Served-index fields that must each be exactly ``false`` for the projection
#: to prove a single-vintage, non-delayed, known-source read.  The failure code
#: IS the field name — the manifest accuses the field, not a paraphrase.
VINTAGE_FLAGS = ("source_delayed", "source_unknown", "source_mixed_vintage")

#: §18.2 frozen accepted build bundle: exactly these four raw asset hashes.
#: No fewer (a subset is not the bundle) and no others (an unrelated entry is
#: not part of the accepted bundle either).
REQUIRED_BUNDLE_ARTIFACT_KEYS = (
    "board",
    "candidate_store",
    "index",
    "theme_state",
)
_REQUIRED_BUNDLE_KEYS = frozenset(REQUIRED_BUNDLE_ARTIFACT_KEYS)

#: A source-issued opaque bundle identity is a bounded single token.  The
#: bound is a sanity envelope, not a format claim: the projection judges
#: injected identity strings, it never mints or parses them.
_MAX_BUNDLE_ID_LEN = 128

# ── typed failure vocabulary (closed; no paths, no secrets, no hosts) ────────

FAILURE_OWED_SESSION_MALFORMED = "owed_session_malformed"
FAILURE_SERVED_INDEX_UNAVAILABLE = "served_index_unavailable"
FAILURE_SERVED_INDEX_MALFORMED = "served_index_malformed"
FAILURE_SERVED_INDEX_SCHEMA_MISMATCH = "served_index_schema_mismatch"
FAILURE_HEALTH_RECEIPT_UNAVAILABLE = "health_receipt_unavailable"
FAILURE_HEALTH_RECEIPT_SCHEMA_MISMATCH = "health_receipt_schema_mismatch"
FAILURE_HEALTH_HASH_MISSING = "health_hash_missing"
FAILURE_SERVED_DIGEST_MISMATCH = "served_digest_mismatch"
FAILURE_SOURCE_ASO_MISSING = "source_asof_missing"
FAILURE_SOURCE_ASO_STALE = "source_asof_stale"
FAILURE_SERVED_SOURCE_ASO_MISSING = "served_source_asof_missing"
FAILURE_SERVED_SOURCE_ASO_MISMATCH = "served_source_asof_mismatch"
FAILURE_READER_CLOCK_MISSING = "reader_clock_missing"
FAILURE_READER_CLOCK_UNQUALIFIED = "reader_clock_unqualified"
FAILURE_READER_CLOCK_NOT_UTC = "reader_clock_not_utc"
FAILURE_COMPUTED_AT_MISSING = "computed_at_missing"
FAILURE_COMPUTED_AT_UNQUALIFIED = "computed_at_unqualified"
FAILURE_PUBLISHED_AT_MISSING = "published_at_missing"
FAILURE_PUBLISHED_AT_UNQUALIFIED = "published_at_unqualified"
FAILURE_CHECKPOINT_MISSING = "checkpoint_missing"
FAILURE_ARTIFACT_HASHES_UNQUALIFIED = "artifact_hashes_unqualified"
FAILURE_ARTIFACT_HASHES_MISSING = "artifact_hashes_missing"
FAILURE_ARTIFACT_BUNDLE_INCOMPLETE = "artifact_bundle_incomplete"
FAILURE_ARTIFACT_BUNDLE_UNRECOGNIZED_ENTRY = "artifact_bundle_unrecognized_entry"
FAILURE_ARTIFACT_INDEX_DIGEST_MISMATCH = "artifact_index_digest_mismatch"
FAILURE_ARTIFACT_BUNDLE_MISMATCH = "artifact_bundle_mismatch"
FAILURE_ACCEPTED_BUNDLE_MISSING = "accepted_bundle_missing"
FAILURE_ACCEPTED_BUNDLE_MALFORMED = "accepted_bundle_malformed"
FAILURE_READER_PROOF_MISSING = "reader_proof_missing"
FAILURE_READER_PROOF_MALFORMED = "reader_proof_malformed"
FAILURE_BUNDLE_ID_MISMATCH = "bundle_id_mismatch"
FAILURE_BUNDLE_INDEX_DIGEST_MISMATCH = "bundle_index_digest_mismatch"
FAILURE_BUNDLE_ID_CHECKPOINT_CONFLATED = "bundle_id_checkpoint_conflated"

FAILURE_CODES = frozenset(
    {
        FAILURE_OWED_SESSION_MALFORMED,
        FAILURE_SERVED_INDEX_UNAVAILABLE,
        FAILURE_SERVED_INDEX_MALFORMED,
        FAILURE_SERVED_INDEX_SCHEMA_MISMATCH,
        FAILURE_HEALTH_RECEIPT_UNAVAILABLE,
        FAILURE_HEALTH_RECEIPT_SCHEMA_MISMATCH,
        FAILURE_HEALTH_HASH_MISSING,
        FAILURE_SERVED_DIGEST_MISMATCH,
        FAILURE_SOURCE_ASO_MISSING,
        FAILURE_SOURCE_ASO_STALE,
        FAILURE_SERVED_SOURCE_ASO_MISSING,
        FAILURE_SERVED_SOURCE_ASO_MISMATCH,
        FAILURE_READER_CLOCK_MISSING,
        FAILURE_READER_CLOCK_UNQUALIFIED,
        FAILURE_READER_CLOCK_NOT_UTC,
        FAILURE_COMPUTED_AT_MISSING,
        FAILURE_COMPUTED_AT_UNQUALIFIED,
        FAILURE_PUBLISHED_AT_MISSING,
        FAILURE_PUBLISHED_AT_UNQUALIFIED,
        FAILURE_CHECKPOINT_MISSING,
        *VINTAGE_FLAGS,
        FAILURE_ARTIFACT_HASHES_UNQUALIFIED,
        FAILURE_ARTIFACT_HASHES_MISSING,
        FAILURE_ARTIFACT_BUNDLE_INCOMPLETE,
        FAILURE_ARTIFACT_BUNDLE_UNRECOGNIZED_ENTRY,
        FAILURE_ARTIFACT_INDEX_DIGEST_MISMATCH,
        FAILURE_ARTIFACT_BUNDLE_MISMATCH,
        FAILURE_ACCEPTED_BUNDLE_MISSING,
        FAILURE_ACCEPTED_BUNDLE_MALFORMED,
        FAILURE_READER_PROOF_MISSING,
        FAILURE_READER_PROOF_MALFORMED,
        FAILURE_BUNDLE_ID_MISMATCH,
        FAILURE_BUNDLE_INDEX_DIGEST_MISMATCH,
        FAILURE_BUNDLE_ID_CHECKPOINT_CONFLATED,
    }
)

#: The closed envelope.  Exactly these keys, in this order; nothing additive.
MANIFEST_FIELDS = (
    "schema",
    "owed_session",
    "source_asof",
    "computed_at",
    "published_at",
    "reader_visible_asof",
    "checked_at",
    "artifact_hashes",
    "checkpoint",
    "status",
    "failures",
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SESSION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_UTC_OFFSET = timedelta(0)


def _parse_session(value: object) -> date | None:
    """A strict ``YYYY-MM-DD`` session literal, or None.  Zero-padding is part
    of the contract: ``strptime`` alone would accept ``2026-1-3``."""
    if not isinstance(value, str) or not _SESSION_RE.fullmatch(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _utc_stamp_failure(value: object) -> str | None:
    """Why this stamp is not a genuine explicit-UTC recording, or None if it is.

    Explicit UTC means tz-aware with a zero offset — ``...Z`` or ``+00:00``.
    A naive stamp is not "probably UTC": accepting it would let a caller's
    unconverted local clock stand as a UTC proof, and the clocks in a
    settlement chain are evidence, not decoration.  The publisher's own
    receipt stamp (``...Z``) and the reader's host clock both already emit
    qualified forms.
    """
    if not isinstance(value, str) or not value:
        return FAILURE_READER_CLOCK_UNQUALIFIED
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return FAILURE_READER_CLOCK_UNQUALIFIED
    if parsed.tzinfo is None or parsed.utcoffset() != _UTC_OFFSET:
        return FAILURE_READER_CLOCK_NOT_UTC
    return None


def _load_served_index(raw: bytes) -> dict | None:
    """Parsed served ``index.json`` object, or None when unreadable."""
    if not raw:
        return None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _qualified_bundle_identity(value: object) -> bool:
    """True for a non-empty, whitespace-free, bounded identity token.

    The projection only JUDGES injected identities; it never builds one.  A
    bundle id computed here — from the served bytes, the receipt, or anything
    else — would be a self-minted attestation, which is exactly what a
    settlement manifest must not manufacture (§18.2 bundle identity is
    source-issued evidence).
    """
    return (
        isinstance(value, str)
        and bool(value)
        and len(value) <= _MAX_BUNDLE_ID_LEN
        and value.split() == [value]
    )


def project_settlement_manifest(
    *,
    owed_session: str,
    accepted_health: Mapping | None,
    served_index_bytes: bytes | None,
    reader_observed_at: str | None,
    artifact_hashes: Mapping[str, str] | None = None,
    computed_at: str | None = None,
    accepted_bundle: Mapping | None = None,
    reader_proof: Mapping | None = None,
) -> dict:
    """Project the ``prophet.settlement_manifest/v1`` settlement envelope.

    Every input is EVIDENCE the caller already lawfully holds: the exact bytes
    production serves for ``prophet/index.json``, the caller's own read clock,
    the accepted publisher receipt, and — required for SETTLED since the §18.2
    binding law — the full four-asset raw hash map (``artifact_hashes``), the
    SOURCE-ISSUED accepted bundle reference (``accepted_bundle``: bundle_id,
    board_definition, candidate_count, artifact_hashes) and the reader-served
    bundle identity (``reader_proof``: served_bundle_id).  None of that is
    ever inferred or minted here; absent binding evidence is a typed PENDING,
    even with every other gate green.  See the module docstring for the
    SETTLED contract, the blindness boundary and the owner binding.  Pure:
    no I/O, no clock, no state; identical inputs give an identical envelope.
    """
    failures: set[str] = set()

    # ── demand side: the owed session ────────────────────────────────────────
    owed_date = _parse_session(owed_session)
    if owed_date is None:
        failures.add(FAILURE_OWED_SESSION_MALFORMED)

    # ── reader plane: the bytes production actually serves ──────────────────
    served_digest: str | None = None
    served: dict | None = None
    if not isinstance(served_index_bytes, (bytes, bytearray)):
        failures.add(FAILURE_SERVED_INDEX_UNAVAILABLE)
    else:
        raw = bytes(served_index_bytes)
        served_digest = hashlib.sha256(raw).hexdigest()
        served = _load_served_index(raw)
        if served is None:
            failures.add(FAILURE_SERVED_INDEX_MALFORMED)

    # ── accepted publication receipt (publisher-emitted, NOT new authority) ─
    health = accepted_health if isinstance(accepted_health, Mapping) else None
    health_digest: str | None = None
    health_source_text: str | None = None
    health_source_date: date | None = None
    published_text: str | None = None
    checkpoint_text: str | None = None
    if health is None:
        failures.add(FAILURE_HEALTH_RECEIPT_UNAVAILABLE)
    else:
        if health.get("schema") != HEALTH_SCHEMA:
            failures.add(FAILURE_HEALTH_RECEIPT_SCHEMA_MISMATCH)

        digest_text = health.get("index_sha256")
        if isinstance(digest_text, str) and _SHA256_RE.fullmatch(digest_text):
            health_digest = digest_text
        else:
            failures.add(FAILURE_HEALTH_HASH_MISSING)

        candidate = health.get("published_at")
        if candidate is None:
            failures.add(FAILURE_PUBLISHED_AT_MISSING)
        elif _utc_stamp_failure(candidate) is not None:
            failures.add(FAILURE_PUBLISHED_AT_UNQUALIFIED)
        else:
            published_text = candidate

        candidate = health.get("checkpoint")
        if isinstance(candidate, str) and candidate:
            checkpoint_text = candidate
        else:
            failures.add(FAILURE_CHECKPOINT_MISSING)

        candidate = health.get("source_asof")
        health_source_date = _parse_session(candidate)
        if health_source_date is None:
            failures.add(FAILURE_SOURCE_ASO_MISSING)
        else:
            health_source_text = candidate

    # ── served projection fields (only when the bytes were readable) ────────
    served_source_text: str | None = None
    served_source_date: date | None = None
    if served is not None:
        if served.get("schema") != INDEX_SCHEMA:
            failures.add(FAILURE_SERVED_INDEX_SCHEMA_MISMATCH)

        candidate = served.get("source_asof")
        served_source_date = _parse_session(candidate)
        if served_source_date is None:
            failures.add(FAILURE_SERVED_SOURCE_ASO_MISSING)
        else:
            served_source_text = candidate

        for flag in VINTAGE_FLAGS:
            if served.get(flag) is not False:
                failures.add(flag)

    # ── cross-binding gates: reader bytes vs accepted bundle vs owed session ─
    if health_digest is not None and served_digest is not None \
            and health_digest != served_digest:
        failures.add(FAILURE_SERVED_DIGEST_MISMATCH)

    if health_source_date is not None and served_source_date is not None \
            and health_source_date != served_source_date:
        failures.add(FAILURE_SERVED_SOURCE_ASO_MISMATCH)

    if owed_date is not None and health_source_date is not None \
            and health_source_date < owed_date:
        failures.add(FAILURE_SOURCE_ASO_STALE)

    # ── reader clock: the caller's own observation stamp ────────────────────
    checked_at: str | None = None
    if reader_observed_at is None or reader_observed_at == "":
        failures.add(FAILURE_READER_CLOCK_MISSING)
    else:
        verdict = _utc_stamp_failure(reader_observed_at)
        if verdict is None:
            checked_at = reader_observed_at
        else:
            failures.add(verdict)

    # ── compute clock: echoed ONLY when genuinely recorded by the caller ────
    manifest_computed_at: str | None = None
    if computed_at is None:
        failures.add(FAILURE_COMPUTED_AT_MISSING)
    elif _utc_stamp_failure(computed_at) is None:
        manifest_computed_at = computed_at
    else:
        failures.add(FAILURE_COMPUTED_AT_UNQUALIFIED)

    # ── §18.2 accepted build bundle: the full raw-asset map, bound ──────────
    # The bundle is proven as a WHOLE or not at all: the reader-side map must
    # be complete and well-formed, its index entry must hash the exact served
    # bytes, and it must equal the issuer's accepted map entry-for-entry.  A
    # matching index hash alone proves one asset — never the bundle — and is
    # never promoted into one.
    manifest_hashes: dict[str, str] | None = None
    caller_map_qualified = False
    if artifact_hashes is None:
        failures.add(FAILURE_ARTIFACT_HASHES_MISSING)
    elif not isinstance(artifact_hashes, Mapping):
        failures.add(FAILURE_ARTIFACT_HASHES_UNQUALIFIED)
    else:
        manifest_hashes = {}
        entries_qualified = True
        for name, value in artifact_hashes.items():
            if isinstance(name, str) and name \
                    and isinstance(value, str) \
                    and _SHA256_RE.fullmatch(value):
                manifest_hashes[name] = value
            else:
                entries_qualified = False
                failures.add(FAILURE_ARTIFACT_HASHES_UNQUALIFIED)
        manifest_hashes = dict(sorted(manifest_hashes.items()))
        raw_keys = {name for name in artifact_hashes
                    if isinstance(name, str) and name}
        missing = _REQUIRED_BUNDLE_KEYS - raw_keys
        unknown = raw_keys - _REQUIRED_BUNDLE_KEYS
        if missing:
            failures.add(FAILURE_ARTIFACT_BUNDLE_INCOMPLETE)
        if unknown:
            failures.add(FAILURE_ARTIFACT_BUNDLE_UNRECOGNIZED_ENTRY)
        caller_map_qualified = entries_qualified and not missing and not unknown
        index_entry = manifest_hashes.get("index")
        if index_entry is not None and served_digest is not None \
                and index_entry != served_digest:
            failures.add(FAILURE_ARTIFACT_INDEX_DIGEST_MISMATCH)

    # ── source-issued accepted bundle reference (§18.2 publish identity) ────
    # Injected evidence, never derived: the reference comes from the issuer of
    # the accepted bundle.  Building one here — from the receipt, the served
    # bytes or anything else — would manufacture authority the projection does
    # not have, so absence is a typed PENDING and defects accuse the
    # REFERENCE, not the reader's own map.
    accepted_map: dict[str, str] | None = None
    accepted_map_qualified = False
    bundle_id: str | None = None
    if accepted_bundle is None:
        failures.add(FAILURE_ACCEPTED_BUNDLE_MISSING)
    elif not isinstance(accepted_bundle, Mapping):
        failures.add(FAILURE_ACCEPTED_BUNDLE_MALFORMED)
    else:
        candidate = accepted_bundle.get("bundle_id")
        if _qualified_bundle_identity(candidate):
            bundle_id = candidate
        else:
            failures.add(FAILURE_ACCEPTED_BUNDLE_MALFORMED)

        candidate = accepted_bundle.get("board_definition")
        if not (isinstance(candidate, str) and candidate):
            failures.add(FAILURE_ACCEPTED_BUNDLE_MALFORMED)

        candidate = accepted_bundle.get("candidate_count")
        if not (isinstance(candidate, int)
                and not isinstance(candidate, bool)
                and candidate >= 0):
            failures.add(FAILURE_ACCEPTED_BUNDLE_MALFORMED)

        issuer_hashes = accepted_bundle.get("artifact_hashes")
        if not isinstance(issuer_hashes, Mapping):
            failures.add(FAILURE_ACCEPTED_BUNDLE_MALFORMED)
        else:
            accepted_map = {}
            entries_qualified = True
            for name, value in issuer_hashes.items():
                if isinstance(name, str) and name \
                        and isinstance(value, str) \
                        and _SHA256_RE.fullmatch(value):
                    accepted_map[name] = value
                else:
                    entries_qualified = False
            if entries_qualified and set(accepted_map) == _REQUIRED_BUNDLE_KEYS:
                accepted_map_qualified = True
            else:
                failures.add(FAILURE_ACCEPTED_BUNDLE_MALFORMED)

    # ── reader-served bundle identity (§18.2 reader_proof.served_bundle_id) ─
    served_bundle_id: str | None = None
    if reader_proof is None:
        failures.add(FAILURE_READER_PROOF_MISSING)
    elif not isinstance(reader_proof, Mapping):
        failures.add(FAILURE_READER_PROOF_MALFORMED)
    else:
        candidate = reader_proof.get("served_bundle_id")
        if _qualified_bundle_identity(candidate):
            served_bundle_id = candidate
        else:
            failures.add(FAILURE_READER_PROOF_MALFORMED)

    # ── accepted-bundle binding gates: reader read vs issuer vs receipt ─────
    if bundle_id is not None and served_bundle_id is not None \
            and bundle_id != served_bundle_id:
        failures.add(FAILURE_BUNDLE_ID_MISMATCH)

    if bundle_id is not None and checkpoint_text is not None \
            and bundle_id == checkpoint_text:
        # The receipt checkpoint is the source git archive commit — a
        # different identity from the published bundle.  An identity equal to
        # it is the checkpoint/bundle conflation defect itself, never a
        # legitimate settled identity, and the projection never borrows it.
        failures.add(FAILURE_BUNDLE_ID_CHECKPOINT_CONFLATED)

    if caller_map_qualified and accepted_map_qualified \
            and manifest_hashes != accepted_map:
        failures.add(FAILURE_ARTIFACT_BUNDLE_MISMATCH)

    if accepted_map_qualified and health_digest is not None \
            and accepted_map.get("index") != health_digest:
        failures.add(FAILURE_BUNDLE_INDEX_DIGEST_MISMATCH)

    # ── fold one status from the collected failures ─────────────────────────
    if failures & {
        FAILURE_OWED_SESSION_MALFORMED,
        FAILURE_SERVED_INDEX_UNAVAILABLE,
        FAILURE_SERVED_INDEX_MALFORMED,
        FAILURE_HEALTH_RECEIPT_UNAVAILABLE,
    }:
        status = STATUS_UNAVAILABLE_DATA
    elif failures:
        status = STATUS_PENDING
    else:
        status = STATUS_SETTLED

    return {
        "schema": SETTLEMENT_SCHEMA,
        "owed_session": owed_session if owed_date is not None else None,
        "source_asof": health_source_text,
        "computed_at": manifest_computed_at,
        "published_at": published_text,
        "reader_visible_asof": served_source_text,
        "checked_at": checked_at,
        "artifact_hashes": manifest_hashes,
        "checkpoint": checkpoint_text,
        "status": status,
        "failures": sorted(failures),
    }
