"""Mastermind Data OS — the convergence spine, not a new stack.

THE THESIS (§D0).  This repo does not lack point-in-time or contract discipline.  It
contains **at least six independent, locally-correct implementations of it** —
Calcbench 5-clock bitemporal fundamentals, FRED/ALFRED vintage as-of reads, the CN
TuShare generation-atomic PIT universe, ``basket_membership_pit`` append-only
snapshots, ``collectors/base.py::ColumnContract`` per-column freshness, and
``engine/canon.py``'s golden-vector concept canon — which share **no vocabulary, no
registry and no enforcement**.  Correctness is therefore per-module and globally
unverifiable, and every new session re-invents the same wheel a seventh time.

**The Data OS is a convergence and enforcement spine over patterns the house already
proved.**  Corollary that governs every addition here: *the boring answer already
exists in this repo.*  Anything that is not an extension of an in-repo pattern must
name the specific requirement the in-repo pattern fails.

What each module owns:

``identity``   §D2 — a symbol is never an identity.  Listing keys, issuer/security
               ids, instrument-class ids, CN/HK symbol normalization, and a
               TIME-SCOPED vendor alias table.  Motivated by the MMC->MRSH rename that
               left ``data/baskets/ohlcv/MMC.parquet`` nonexistent for seven months.
``temporal``   §D3 — the seven named times, six temporal profiles, and the fail-closed
               PIT law: a profile that cannot answer ``known_at`` RAISES rather than
               silently returning the latest vintage.
``price``      §D4 — the naming law.  No stored price column may be named ``close``,
               ``price`` or ``value`` without a basis suffix; ``KNOWN_STORE_BASES``
               records the measured truth of the stores that exist today.
``nulls``      §D6 — the closed missing-reason vocabulary.  ``0`` may never be written
               to mean absence.
``registry``   §D5/§D9 — ``DatasetContract``, the registry file, and the static
               lineage DAG.  No new store.
``quality``    §D8 — nine check families x four severities, as PURE validators.

WHAT THIS IS NOT (§D11).  Not Kafka, Snowflake, Databricks, a data mesh, a lineage
SaaS, event sourcing, a feature store (§D10 verdict: NO), a rewrite of any store, or a
second control plane / authority map — the last is explicitly prohibited cross-repo
(``duplicate_control_planes``, Mastermind AGENTS.md).

STDLIB ONLY at import time.  ``yaml`` is imported lazily inside
``registry.load_registry`` and pandas appears nowhere, so every module here is
importable in the thin CI lanes and inside a collector that must not pay a dataframe
import to translate a ticker.
"""
from __future__ import annotations

from lib.dataos.identity import (
    AliasResolution,
    AliasRow,
    CNBoard,
    IdentityError,
    KNOWN_MICS,
    ListingKey,
    ReferenceReadReceipt,
    ReferenceSnapshot,
    VendorAliasTable,
    VENUE_TZ,
    VENUE_CURRENCY,
    cn_board,
    fx_id,
    future_id,
    index_id,
    is_legacy_bse_code,
    issuer_id,
    listing_id,
    normalize_cn_symbol,
    normalize_hk_symbol,
    option_contract_id,
    parse_fx_id,
    parse_future_id,
    parse_id,
    parse_index_id,
    parse_listing_key,
    parse_option_contract_id,
    security_id,
    validate_reference_snapshot,
    venue_timezone,
    venue_currency,
)
from lib.dataos.nulls import MissingReason, NullPolicy, validate_value
from lib.dataos.price import (
    AMBIGUOUS_NAMES,
    AdjustmentBasis,
    KNOWN_STORE_BASES,
    PriceError,
    PriceField,
    Session,
    VenueScope,
    canonical_column,
    is_ambiguous,
    parse_column,
)
from lib.dataos.price_views import (
    ActionFamily,
    RefusalReason,
    ViewRefusal,
    CONFIRMED,
    SUPPORTED_FAMILIES,
    UNSUPPORTED_FAMILIES,
    CASH_BASES,
    ActionEvent,
    ActionRevisionSet,
    AdjustmentReference,
    PriceView,
    split_factor,
    adjust_quantity,
    return_vector,
    qualified_return,
    raw_view,
    sadj_view,
    ReinvestPolicy,
    TotalReturnPolicy,
    TotalReturnView,
    total_return_view,
    ViewVintage,
    RetainedView,
    ReopenedView,
    ComposedView,
    admit_action_input,
    admit_revision_set,
    retain_view,
    reopen_view,
    reconstruct_price_view,
    simple_returns,
    view_label,
    view_receipt_sha256,
)
from lib.dataos.quality import (
    CheckFamily,
    Finding,
    Severity,
    check_completeness,
    check_freshness,
    check_referential,
    check_temporal_integrity,
    check_uniqueness,
    check_validity_ohlc,
    emit_annotations,
)
from lib.dataos.read_contract import (
    READ_CONTRACT_VERSION,
    CurrentEvidence,
    Dependency,
    GenerationRef,
    ReadContractError,
    ReadMode,
    ReadRefusal,
    ReadRequest,
    ReadResult,
    RefusalCode,
    RetainedOutput,
    ViewContract,
    current,
    eligible_rows,
    reconstruct,
    replay,
    resolve_revisions,
    select_generation,
    selected_input_sha256s,
)
from lib.dataos.registry import (
    ACTION_FIELD_CONVENTIONS,
    ACTION_INPUT_FIELDS,
    ACTION_INPUT_OPTIONAL_FIELDS,
    ACTION_INPUT_ORIGINS,
    ACTION_INPUT_RESPONSES,
    ActionInputStatus,
    ActionInputVerdict,
    ConflictPolicy,
    DatasetContract,
    DatasetStatus,
    Layer,
    REGISTRY_PATH,
    Registry,
    RegistryError,
    load_registry,
    qualify_action_input,
    validate_registry,
)
from lib.dataos.temporal import (
    Clock,
    KNOWN_AT_CLOCKS,
    PointInTimeError,
    TemporalError,
    TemporalProfile,
    as_of_filter,
    assert_pit_readable,
    known_at,
    utc,
)

__all__ = [
    # identity (§D2)
    "IdentityError", "KNOWN_MICS", "ListingKey", "parse_listing_key",
    "listing_id", "security_id", "issuer_id", "parse_id",
    "option_contract_id", "parse_option_contract_id",
    "future_id", "parse_future_id", "index_id", "parse_index_id",
    "fx_id", "parse_fx_id",
    "VENUE_TZ", "VENUE_CURRENCY", "venue_timezone", "venue_currency",
    "CNBoard", "cn_board", "is_legacy_bse_code",
    "normalize_cn_symbol", "normalize_hk_symbol",
    "AliasRow", "VendorAliasTable",
    "AliasResolution", "ReferenceReadReceipt", "ReferenceSnapshot",
    "validate_reference_snapshot",
    # temporal (§D3)
    "TemporalError", "PointInTimeError", "Clock", "TemporalProfile",
    "KNOWN_AT_CLOCKS", "utc", "known_at", "assert_pit_readable", "as_of_filter",
    # read contract (D00.D1: CURRENT / RECONSTRUCT / REPLAY above temporal)
    "READ_CONTRACT_VERSION", "ReadMode", "RefusalCode", "ReadContractError",
    "ReadRefusal", "ViewContract", "ReadRequest", "GenerationRef", "Dependency",
    "CurrentEvidence", "RetainedOutput", "ReadResult", "eligible_rows",
    "resolve_revisions", "select_generation", "reconstruct", "current", "replay",
    "selected_input_sha256s",
    # price (§D4)
    "PriceError", "AdjustmentBasis", "PriceField", "Session", "VenueScope",
    "canonical_column", "parse_column", "AMBIGUOUS_NAMES", "is_ambiguous",
    "KNOWN_STORE_BASES",
    # registry (§D5/§D9)
    "RegistryError", "Layer", "DatasetStatus", "ConflictPolicy",
    "DatasetContract", "Registry", "REGISTRY_PATH", "load_registry",
    "validate_registry",
    "ActionInputStatus", "ActionInputVerdict", "qualify_action_input",
    "ACTION_INPUT_FIELDS", "ACTION_INPUT_OPTIONAL_FIELDS", "ACTION_INPUT_ORIGINS",
    "ACTION_INPUT_RESPONSES", "ACTION_FIELD_CONVENTIONS",
    # price_views (D00.D3 action projection, split/distribution/total-return views)
    "ActionFamily",
    "RefusalReason",
    "ViewRefusal",
    "CONFIRMED",
    "SUPPORTED_FAMILIES",
    "UNSUPPORTED_FAMILIES",
    "CASH_BASES",
    "ActionEvent",
    "ActionRevisionSet",
    "AdjustmentReference",
    "PriceView",
    "split_factor",
    "adjust_quantity",
    "return_vector",
    "qualified_return",
    "raw_view",
    "sadj_view",
    "ReinvestPolicy",
    "TotalReturnPolicy",
    "TotalReturnView",
    "total_return_view",
    # price_views revision/vintage layer (P05) and venue-bound reconstruction (P06)
    "ViewVintage",
    "RetainedView",
    "ReopenedView",
    "ComposedView",
    "admit_action_input",
    "admit_revision_set",
    "retain_view",
    "reopen_view",
    "reconstruct_price_view",
    "simple_returns",
    "view_label",
    "view_receipt_sha256",
    # nulls (§D6)
    "MissingReason", "NullPolicy", "validate_value",
    # quality (§D8)
    "Severity", "CheckFamily", "Finding",
    "check_uniqueness", "check_validity_ohlc", "check_freshness",
    "check_completeness", "check_referential", "check_temporal_integrity",
    "emit_annotations",
]
