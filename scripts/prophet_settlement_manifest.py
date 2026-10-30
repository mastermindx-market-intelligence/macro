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
    ``checkpoint``).

Anything less is ``PENDING`` (judged, not settled) or ``UNAVAILABLE_DATA``
(blind).  Blindness is reserved for what the sentinel calls INDETERMINATE
(a read that could not be made: no bytes, unparseable bytes, no receipt) or a
malformed ``owed_session`` (nothing can be owed).  A definitive read of a wrong
artifact (schema mismatch, digest mismatch, stale source) is a JUDGED failure —
``PENDING`` — never blindness.  Missing reader clock and missing receipt hash
fail closed: neither can ever be inferred.

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


def project_settlement_manifest(
    *,
    owed_session: str,
    accepted_health: Mapping | None,
    served_index_bytes: bytes | None,
    reader_observed_at: str | None,
    artifact_hashes: Mapping[str, str] | None = None,
    computed_at: str | None = None,
) -> dict:
    """Project the ``prophet.settlement_manifest/v1`` settlement envelope.

    Every input is EVIDENCE the caller already lawfully holds: the exact bytes
    production serves for ``prophet/index.json``, the caller's own read clock,
    and the accepted publisher receipt.  See the module docstring for the
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

    # ── accepted build-bundle artifact hashes: qualified entries only ───────
    manifest_hashes: dict[str, str] | None = None
    if artifact_hashes is not None:
        manifest_hashes = {}
        if isinstance(artifact_hashes, Mapping):
            for name, value in artifact_hashes.items():
                if isinstance(name, str) and name \
                        and isinstance(value, str) \
                        and _SHA256_RE.fullmatch(value):
                    manifest_hashes[name] = value
                else:
                    failures.add(FAILURE_ARTIFACT_HASHES_UNQUALIFIED)
        else:
            failures.add(FAILURE_ARTIFACT_HASHES_UNQUALIFIED)
        manifest_hashes = dict(sorted(manifest_hashes.items()))

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
