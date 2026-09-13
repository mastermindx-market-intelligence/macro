"""Ticker<->CIK collision census — pure classifiers over the identity plane.

WHY THIS FILE EXISTS (``[MO-B F06-5]``, MO-PAID-020).
The Market Ontology F00C ledger row MO-PAID-020 rules:

    next_bounded_child = "RULED: a single bounded renderer/CIK-access repair may
    be admitted only after a fresh collision census; it remains
    CAPACITY_SELECTABLE / WAITING_CAPACITY (not this session's to self-assign);
    any owner-path mutation returns OWNER_BOUNDARY_REQUIRED"

This module is the CENSUS half. It enumerates five classes of collision / access
issue (C1 strict, C2 vendor-namespace divergence, C3 CIK-leg access failure,
C4 renderer coverage, C5 renderer robustness) over a frozen ``data/reference/``
identity plane snapshot, and reports them through a closed-enum receipt schema
that lives at ``engine.market_ontology.ticker_cik_census.RECEIPT_SCHEMA``. A
census reports; it never fails a build. The seat's admissibility ruling for the
ONE bounded repair (``R3``) lives in the F06-5 spec, never in this file.

PURE CLASSIFIERS — NO PANDAS AT MODULE TOP.  Per ``R5`` every classifier is a
pure function over ``list[dict]`` records (the canonical post-``to_dict`` form
the owner APIs already accept), so the test layer can build synthetic fixtures
without a pandas import. The parquet I/O lives in the CLI script
(``scripts/ticker_cik_collision_census.py``) and in the live-data test, never
here. The decision_date is INJECTED, never read from the wall clock.

CLOSED CLASSIFIER ENUMS.  C1 / C2 / C4 sub-codes are listed in
``C1_COLLISION_CODES`` / ``C2_NAMESPACE_CODES`` / ``C4_COVERAGE_CODES``; the
closed C3 message-class enum (the typed classes that map onto the producer's
exception flow) lives in :class:`CikFailureClass`. New codes require a DEC, not
a code-level widening.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from enum import Enum
import re

__all__ = [
    "C1_COLLISION_CODES",
    "C2_NAMESPACE_CODES",
    "C4_COVERAGE_CODES",
    "CikFailureClass",
    "RECEIPT_SCHEMA",
    "CensusCounts",
    "CensusRecord",
    "classify_failure_message",
    "c1_strict_collisions",
    "c2_namespace_divergence",
    "c3_cik_leg_access_failures",
    "c4_renderer_coverage",
    "build_receipt",
]


# ── Closed enum: C3 message class (R5) ────────────────────────────────────────
class CikFailureClass(str, Enum):
    """Closed enum of the typed C3 failure classes the producer emits.

    Maps 1:1 onto the ``SecurityStateCompilationError`` raised by
    ``scripts/security_state_producer.py::_read_security_state_identity_rows``,
    plus the unconditional pre-alias unbound path. The classifier is a pure
    function over the rendered failure message string; a fresh message class
    requires an explicit DEC, never a code-level widening here.
    """

    ALIAS_UNBOUND = "alias_unbound"
    ROUND_TRIP_MISMATCH = "round_trip_mismatch"
    NO_MASTER_ROW = "no_master_row"
    OWNER_IDENTITY_INCOMPLETE = "owner_identity_incomplete"
    LISTING_KEY_UNPARSEABLE = "listing_key_unparseable"
    SECURITY_ID_RENDER_MISMATCH = "security_id_render_mismatch"
    SECURITY_STATE_COMPILATION = "security_state_compilation"


# ── Closed enum: C1 / C2 / C4 sub-codes (R2) ──────────────────────────────────
C1_COLLISION_CODES: tuple[str, ...] = (
    "store_symbol_multi_security",     # (a)
    "security_multi_store_symbol",     # (b)
    "cik_multi_issuer",                # (c)
    "listing_key_multi_security",      # (d)
    "issuer_cik_mismatch",             # (e)
    "listing_key_disambiguator",       # (f)
    "superseded_duplicate_mint",       # (g)
)

C2_NAMESPACE_CODES: tuple[str, ...] = (
    "active_vendor_divergence",  # store vs yahoo/yahoo_fetch/membership/theme_graph_native disagree TODAY
    "expired_store_alias",       # a previous store symbol with valid_to <= today (the rename case)
)

C4_COVERAGE_CODES: tuple[str, ...] = (
    "no_identity_row",                # universe ticker with NO store alias today
    "resolvable_outside_allowlist",   # resolvable identity but NOT in SECURITY_STATE_TICKERS
)


# ── C3 message classifier (R5) — pure function over the failure string ─────────
def classify_failure_message(message: str) -> CikFailureClass:
    """Map a producer-side failure string to its closed C3 enum.

    PURE — no I/O, no state, no clock. The producer's failure strings are the
    canonical surface for this classifier (every error path in
    ``_read_security_state_identity_rows`` raises
    ``SecurityStateCompilationError`` with a stable substring the producer
    itself chose). Order of pattern tests matters only for disambiguation;
    patterns below are mutually exclusive in the current producer.
    """
    if not isinstance(message, str) or not message:
        return CikFailureClass.SECURITY_STATE_COMPILATION
    if "no current store binding" in message:
        return CikFailureClass.ALIAS_UNBOUND
    if "round-trip mismatch" in message:
        return CikFailureClass.ROUND_TRIP_MISMATCH
    if "no row for owner-resolved" in message:
        return CikFailureClass.NO_MASTER_ROW
    if "owner identity is incomplete" in message:
        return CikFailureClass.OWNER_IDENTITY_INCOMPLETE
    if "not a parseable ListingKey" in message:
        return CikFailureClass.LISTING_KEY_UNPARSEABLE
    if "does not render the alias-resolved security" in message:
        return CikFailureClass.SECURITY_ID_RENDER_MISMATCH
    return CikFailureClass.SECURITY_STATE_COMPILATION


# ── Output shapes (R5 — receipt schema) ──────────────────────────────────────
@dataclass(frozen=True, slots=True)
class CensusRecord:
    """One typed collision / access row.

    ``code`` is the closed-enum sub-code (R2); ``ids`` is a tuple of the exact
    raw identifiers observed, in the order produced by the classifier — never a
    deduplicated summary, so a receipt reader can reproduce the observation.
    """

    code: str
    ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CensusCounts:
    """Per-class counts (R5 live-data test prints these as receipt lines)."""

    c1: dict[str, int]
    c2: dict[str, int]
    c3: dict[str, int]
    c4: dict[str, int]

    def to_receipt_lines(self, decision_date: date, data_dir: str) -> list[str]:
        """Dated summary lines the CLI prints — one per code, never aggregated."""
        out = [
            f"decision_date={decision_date.isoformat()}",
            f"data_dir={data_dir}",
        ]
        for cls_name, counts in (("C1", self.c1), ("C2", self.c2), ("C3", self.c3), ("C4", self.c4)):
            for code in sorted(counts):
                out.append(f"{cls_name}.{code}={counts[code]}")
        return out


# ── C1: strict collisions (R2) ────────────────────────────────────────────────
def c1_strict_collisions(
    *,
    alias_rows: list[dict],
    security_records: list[dict],
    issuer_records: list[dict],
    decision_date: date,
) -> list[CensusRecord]:
    """Enumerate the seven C1 sub-codes over CURRENT alias + master rows.

    A store alias whose ``valid_to`` has passed is NOT a failure here — it is a
    RENAME/EXPIRY row (R2).  A ``SUPERSEDED_DUPLICATE_MINT`` row is REPORTED
    under (g) but never counted as a defect — owner-resolved duplicates are
    spec-allowed by V4-D2B1-R1 §3.6.
    """
    records: list[CensusRecord] = []

    # (a) one store symbol bound to >1 active security_id
    sym_to_secs: dict[str, set[str]] = {}
    for row in alias_rows:
        if row.get("vendor") != "store":
            continue
        if not _covers(row, decision_date):
            continue
        sym = _s(row.get("vendor_symbol"))
        sec = _s(row.get("security_id"))
        if sym and sec:
            sym_to_secs.setdefault(sym, set()).add(sec)
    for sym in sorted(syms for syms, secs in sym_to_secs.items() if len(secs) > 1):
        records.append(CensusRecord("store_symbol_multi_security", (sym,)))

    # (b) one active security_id bound to >1 store symbol
    sec_to_syms: dict[str, set[str]] = {}
    for row in alias_rows:
        if row.get("vendor") != "store":
            continue
        if not _covers(row, decision_date):
            continue
        sym = _s(row.get("vendor_symbol"))
        sec = _s(row.get("security_id"))
        if sym and sec:
            sec_to_syms.setdefault(sec, set()).add(sym)
    for sec in sorted(s for s, syms in sec_to_syms.items() if len(syms) > 1):
        records.append(CensusRecord("security_multi_store_symbol", (sec,)))

    # (c) one CIK <-> >1 issuer_id in issuer_master
    cik_to_issuers: dict[str, set[str]] = {}
    for row in issuer_records:
        cik = _s(row.get("cik"))
        iss = _s(row.get("issuer_id"))
        if cik and iss:
            cik_to_issuers.setdefault(cik, set()).add(iss)
    for cik in sorted(c for c, iss in cik_to_issuers.items() if len(iss) > 1):
        records.append(CensusRecord("cik_multi_issuer", (cik,)))

    # (d) one listing_key <-> >1 security_id in security_master
    lk_to_secs: dict[str, set[str]] = {}
    for row in security_records:
        lk = _s(row.get("listing_key"))
        sec = _s(row.get("security_id"))
        if lk and sec:
            lk_to_secs.setdefault(lk, set()).add(sec)
    for lk in sorted(l for l, secs in lk_to_secs.items() if len(secs) > 1):
        records.append(CensusRecord("listing_key_multi_security", (lk,)))

    # (e) security_master.issuer_cik != issuer_master.cik for the same issuer_id
    iss_to_issuer_cik: dict[str, str] = {}
    for row in security_records:
        iss = _s(row.get("issuer_id"))
        if iss and iss not in iss_to_issuer_cik:
            cik = _s(row.get("issuer_cik"))
            if cik:
                iss_to_issuer_cik[iss] = cik
    iss_to_master_cik: dict[str, str] = {}
    for row in issuer_records:
        iss = _s(row.get("issuer_id"))
        cik = _s(row.get("cik"))
        if iss and cik and iss not in iss_to_master_cik:
            iss_to_master_cik[iss] = cik
    for iss in sorted(set(iss_to_issuer_cik) & set(iss_to_master_cik)):
        if iss_to_issuer_cik[iss] != iss_to_master_cik[iss]:
            records.append(
                CensusRecord(
                    "issuer_cik_mismatch",
                    (iss, iss_to_issuer_cik[iss], iss_to_master_cik[iss]),
                )
            )

    # (f) `.N` disambiguator listing keys
    disamb_re = re.compile(r"\.\d+$")
    for row in security_records:
        lk = _s(row.get("listing_key"))
        if lk and disamb_re.search(lk):
            records.append(
                CensusRecord(
                    "listing_key_disambiguator",
                    (_s(row.get("security_id")), lk),
                )
            )

    # (g) security_state SUPERSEDED_DUPLICATE_MINT or superseded_by
    for row in security_records:
        sec = _s(row.get("security_id"))
        if not sec:
            continue
        ss_state = row.get("security_state")
        sup_by_raw = row.get("superseded_by")
        sup_by_norm = _s_or_none(sup_by_raw)
        if ss_state == "SUPERSEDED_DUPLICATE_MINT" or sup_by_norm is not None:
            records.append(
                CensusRecord(
                    "superseded_duplicate_mint",
                    (sec, sup_by_norm or ""),
                )
            )

    return records


# ── C2: vendor-namespace divergence (R2) ──────────────────────────────────────
_TRACKED_VENDORS: tuple[str, ...] = (
    "store", "yahoo", "yahoo_fetch", "membership", "theme_graph_native",
)


def c2_namespace_divergence(
    *,
    alias_rows: list[dict],
    decision_date: date,
) -> list[CensusRecord]:
    """Enumerate C2 pairs (active divergence + expired store aliases)."""
    records: list[CensusRecord] = []

    # Active divergence: per security_id, the set of vendor_symbols it carries
    # TODAY. A divergence = >1 distinct symbol across vendors.
    sec_to_vendor_syms: dict[str, dict[str, set[str]]] = {}
    for row in alias_rows:
        vendor = _s(row.get("vendor"))
        if vendor not in _TRACKED_VENDORS:
            continue
        if not _covers(row, decision_date):
            continue
        sec = _s(row.get("security_id"))
        sym = _s(row.get("vendor_symbol"))
        if not (sec and sym):
            continue
        sec_to_vendor_syms.setdefault(sec, {}).setdefault(vendor, set()).add(sym)

    for sec in sorted(sec_to_vendor_syms):
        per_vendor = sec_to_vendor_syms[sec]
        if len(per_vendor) < 2:
            continue
        all_syms = set()
        for syms in per_vendor.values():
            all_syms |= syms
        if len(all_syms) <= 1:
            continue
        ids = [sec]
        for vendor in _TRACKED_VENDORS:
            syms = sorted(per_vendor.get(vendor, ()))
            if syms:
                ids.append(f"{vendor}={'/'.join(syms)}")
        records.append(CensusRecord("active_vendor_divergence", tuple(ids)))

    # Expired store aliases: the rename case
    for row in alias_rows:
        if row.get("vendor") != "store":
            continue
        vt = _to_date(row.get("valid_to"))
        if vt is None or vt > decision_date:
            continue
        sec = _s(row.get("security_id"))
        sym = _s(row.get("vendor_symbol"))
        if not (sec and sym):
            continue
        records.append(
            CensusRecord(
                "expired_store_alias",
                (sec, sym, vt.isoformat()),
            )
        )

    return records


# ── C3: CIK-leg access failures (R2) ──────────────────────────────────────────
def c3_cik_leg_access_failures(
    *,
    alias_rows: list[dict],
    security_records: list[dict],
    issuer_records: list[dict],
    decision_date: date,
) -> tuple[list[CensusRecord], dict[str, dict[str, str | None]]]:
    """Enumerate C3 typed access failures over CURRENT bindings.

    Returns a tuple of (records, per-ticker detail). The per-ticker detail
    carries ``issuer_state`` + ``evidence_source`` straight from the master /
    issuer tables so the receipt can render the seat's probe verbatim (CTRA,
    FI, GOLD, TPH on 2026-09-13 are expected to land here with NO_ISSUER_EVIDENCE
    / DEFERRED_IDENTITY_EXCEPTION + legacy_mint).
    """
    # We cannot import the producer here without dragging pandas into the
    # module (R5: no pandas at module top). The classifier REPRODUCES the
    # producer's typed refusal path by re-running the same owner steps
    # through the same public APIs (``VendorAliasTable.from_records``,
    # ``IssuerMaster.from_records``). This is a deliberate separation — the
    # test layer exercises both the classifier and the producer on the same
    # fixture and asserts they agree.
    from lib.dataos.identity import (
        IdentityError,
        IssuerMaster,
        VendorAliasTable,
        parse_listing_key,
        security_id as render_security_id,
    )

    alias_owner = VendorAliasTable.from_records(alias_rows or ())
    issuer_owner = IssuerMaster.from_records(security_records or ())

    # Index security master rows by security_id for the receipt detail.
    sec_rows: dict[str, dict] = {}
    for row in security_records or ():
        sid = _s(row.get("security_id"))
        if sid:
            sec_rows[sid] = row

    # Index issuer_master rows by issuer_id for the receipt detail.
    iss_rows: dict[str, dict] = {}
    for row in issuer_records or ():
        iid = _s(row.get("issuer_id"))
        if iid:
            iss_rows[iid] = row

    # Walk every CURRENT store symbol (a `store` alias whose valid_to has
    # passed is a RENAME/EXPIRY row, never a C3 failure — per R2).
    seen_tickers: set[str] = set()
    for row in alias_rows or ():
        if row.get("vendor") != "store":
            continue
        if not _covers(row, decision_date):
            continue
        sym = _s(row.get("vendor_symbol"))
        if sym:
            seen_tickers.add(sym)

    records: list[CensusRecord] = []
    details: dict[str, dict[str, str | None]] = {}

    # Each loop iteration captures the ``resolved_sec`` for the receipt detail
    # by re-running the alias resolution outside the try block (the C3 path
    # never aliases the local). Keeping the re-resolution here means a C3
    # failure can still surface the matching master row's issuer_state and
    # evidence_source — that is the receipt row the spec's research note
    # cites verbatim (CTRA, FI, GOLD, TPH).
    def _resolve(t: str) -> str | None:
        try:
            return alias_owner.resolve("store", t, decision_date)
        except Exception:
            return None

    def _issuer_detail(sid: str | None) -> tuple[str | None, str | None]:
        if sid is None:
            return None, None
        sm_row = sec_rows.get(sid) or {}
        iss_state = sm_row.get("issuer_state")
        iss_id = sm_row.get("issuer_id")
        ev_src: object = None
        if isinstance(iss_id, str) and iss_id:
            im_row = iss_rows.get(iss_id) or {}
            ev_src = im_row.get("evidence_source")
        return _s_or_none(iss_state), _s_or_none(ev_src)

    for ticker in sorted(seen_tickers):
        try:
            if not ticker or ticker != ticker.upper():
                raise SecurityStateCompilationErrorSimulated(
                    f"security_state ticker must be a non-empty uppercase string, got {ticker!r}"
                )
            sec = alias_owner.resolve("store", ticker, decision_date)
            if sec is None:
                raise SecurityStateCompilationErrorSimulated(
                    f"VendorAliasTable has no current store binding for {ticker} on {decision_date}"
                )
            rev = alias_owner.vendor_symbol_for("store", sec, decision_date)
            if rev != ticker:
                raise SecurityStateCompilationErrorSimulated(
                    f"VendorAliasTable round-trip mismatch for {ticker}: {rev!r}"
                )
            row = sec_rows.get(sec)
            if row is None:
                raise SecurityStateCompilationErrorSimulated(
                    f"security master has no row for owner-resolved {sec}"
                )
            iss = issuer_owner.issuer_of_security(sec)
            cik = issuer_owner.cik_of_issuer(iss) if iss else None
            lk = issuer_owner.listing_key_of_security(sec)
            if not iss or not cik or not isinstance(lk, str) or not lk:
                raise SecurityStateCompilationErrorSimulated(
                    f"owner identity is incomplete for {ticker}: "
                    f"issuer_id={iss!r}, issuer_cik={cik!r}, listing_key={lk!r}"
                )
            try:
                plk = parse_listing_key(lk)
            except IdentityError:
                raise SecurityStateCompilationErrorSimulated(
                    f"owner listing key for {ticker} is not a parseable ListingKey: {lk!r}"
                ) from None
            if render_security_id(plk) != sec:
                raise SecurityStateCompilationErrorSimulated(
                    f"owner listing key {lk!r} does not render the alias-resolved "
                    f"security {sec!r} for {ticker}"
                )
        except SecurityStateCompilationErrorSimulated as exc:
            cls = classify_failure_message(str(exc))
            sid = _resolve(ticker)
            iss_state, ev_src = _issuer_detail(sid)
            details[ticker] = {"issuer_state": iss_state, "evidence_source": ev_src}
            records.append(CensusRecord(cls.value, (ticker, str(exc))))

    return records, details


# ── C4: renderer coverage (R2) ────────────────────────────────────────────────
def c4_renderer_coverage(
    *,
    alias_rows: list[dict],
    decision_date: date,
    universe_tickers: list[str],
    allowlist_tickers: tuple[str, ...],
) -> list[CensusRecord]:
    """Enumerate C4 coverage facts.

    ``universe_tickers`` is the F06 universe (data/stocks + data/sector_holdings;
    site/stockdata is gitignored — caller asserts this, never counts it).
    """
    active_store_syms: set[str] = set()
    for row in alias_rows or ():
        if row.get("vendor") != "store":
            continue
        if not _covers(row, decision_date):
            continue
        sym = _s(row.get("vendor_symbol"))
        if sym:
            active_store_syms.add(sym)

    universe = sorted(set(universe_tickers or ()))
    allowlist = set(allowlist_tickers or ())

    records: list[CensusRecord] = []
    no_id = [t for t in universe if t not in active_store_syms]
    if no_id:
        records.append(CensusRecord("no_identity_row", tuple(no_id)))

    resolvable = [t for t in universe if t in active_store_syms and t not in allowlist]
    if resolvable:
        records.append(CensusRecord("resolvable_outside_allowlist", tuple(resolvable)))

    return records


# ── Aggregate receipt (R5) ────────────────────────────────────────────────────
def build_receipt(
    *,
    decision_date: date,
    data_dir: str,
    c1: list[CensusRecord],
    c2: list[CensusRecord],
    c3: list[CensusRecord],
    c3_details: dict[str, dict[str, str | None]],
    c4: list[CensusRecord],
) -> dict:
    """Aggregate the four classifiers into a single JSON-serialisable receipt.

    The receipt is the canonical artefact the CLI emits to ``--out`` and the
    test layer asserts against. Counts are deterministic (Counter-shaped);
    the raw records are kept by class so a future tool can re-derive new
    counts without re-reading the parquet.

    ``total_collisions`` sums the C1 strict-collision sub-codes (a)-(f) only;
    the (g) superseded_duplicate_mint row is REPORTED (per R2 / V4-D2B1-R1
    §3.6) but never counted as a defect.
    """
    c1_counts: dict[str, int] = {code: 0 for code in C1_COLLISION_CODES}
    for r in c1:
        c1_counts[r.code] = c1_counts.get(r.code, 0) + 1
    c2_counts: dict[str, int] = {code: 0 for code in C2_NAMESPACE_CODES}
    for r in c2:
        c2_counts[r.code] = c2_counts.get(r.code, 0) + 1
    c3_counts: dict[str, int] = {cls.value: 0 for cls in CikFailureClass}
    for r in c3:
        c3_counts[r.code] = c3_counts.get(r.code, 0) + 1
    c4_counts: dict[str, int] = {code: 0 for code in C4_COVERAGE_CODES}
    for r in c4:
        c4_counts[r.code] = c4_counts.get(r.code, 0) + 1

    strict_total = sum(
        c1_counts[code]
        for code in C1_COLLISION_CODES
        if code != "superseded_duplicate_mint" and c1_counts[code] > 0
    )

    return {
        "schema": RECEIPT_SCHEMA["schema"],
        "schema_version": RECEIPT_SCHEMA["version"],
        "decision_date": decision_date.isoformat(),
        "data_dir": data_dir,
        "counts": {
            "C1": c1_counts,
            "C2": c2_counts,
            "C3": c3_counts,
            "C4": c4_counts,
        },
        "total_collisions": strict_total,
        "c1_records": [r.code for r in c1],
        "c2_records": [
            {"code": r.code, "ids": list(r.ids)} for r in c2
        ],
        "c3_records": [
            {"code": r.code, "ticker": r.ids[0], "message": r.ids[1]}
            for r in c3
        ],
        "c3_ticker_details": c3_details,
        "c4_records": [r.code for r in c4],
        "lines": CensusCounts(c1_counts, c2_counts, c3_counts, c4_counts)
        .to_receipt_lines(decision_date, data_dir),
    }


# ── Internal helpers ──────────────────────────────────────────────────────────
class SecurityStateCompilationErrorSimulated(Exception):
    """Private sentinel — the classifier re-raises a producer-shaped exception
    string without importing the producer (which would drag pandas in).
    """


def _covers(row: dict, decision_date: date) -> bool:
    """Mirror VendorAliasTable.AliasRow.covers() over a parquet dict row."""
    vf = _to_date(row.get("valid_from"))
    vt = _to_date(row.get("valid_to"))
    if vf is not None and decision_date < vf:
        return False
    if vt is not None and decision_date >= vt:
        return False
    return True


def _to_date(value: object) -> date | None:
    """Coerce a parquet date cell to ``datetime.date`` (or ``None``).

    Accepts the three shapes the identity plane emits:
      * a real ``datetime.date`` (the parquet writer's canonical form),
      * a pandas ``Timestamp`` / ``datetime.datetime`` (its ``.date()`` method
        unwraps it),
      * an ISO 8601 string (test fixtures; ``datetime.date.fromisoformat``
        handles ``YYYY-MM-DD`` directly).

    ``pandas.to_dict('records')`` preserves ``datetime.date`` for date columns
    but may also hand back ``None`` for nullable dates. NaN cells in
    non-nullable ``object`` columns are not expected here.
    """
    from datetime import datetime as _datetime
    if value is None:
        return None
    if isinstance(value, float) and value != value:  # noqa: PLR0124 — NaN test
        return None
    if isinstance(value, _datetime) and not isinstance(value, date):
        try:
            return value.date()
        except Exception:
            return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return _dt_date_fromisoformat(value)
        except Exception:
            return None
    if hasattr(value, "date") and callable(value.date):
        try:
            return value.date()
        except Exception:
            return None
    return None


# Local import for the ISO-string branch — kept private so the module top
# never widens beyond ``datetime.date`` / stdlib.
_dt_date_fromisoformat = date.fromisoformat


def _s(value: object) -> str:
    """Coerce a scalar cell to a trimmed string ('' for None / NaN)."""
    if value is None:
        return ""
    if isinstance(value, float) and value != value:  # noqa: PLR0124 — NaN test
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _s_or_none(value: object) -> str | None:
    out = _s(value)
    return out if out else None


# ── Receipt schema (R5) ───────────────────────────────────────────────────────
RECEIPT_SCHEMA: dict = {
    "schema": "ticker_cik_collision_census.v1",
    "version": "1.0.0",
    "fields": {
        "schema": "literal ticker_cik_collision_census.v1",
        "schema_version": "literal 1.0.0",
        "decision_date": "ISO 8601 date the census was computed at",
        "data_dir": "string identifying the reference/ root the census read",
        "counts.C1": "per-C1-code count (closed enum in C1_COLLISION_CODES)",
        "counts.C2": "per-C2-code count (closed enum in C2_NAMESPACE_CODES)",
        "counts.C3": "per-CikFailureClass count",
        "counts.C4": "per-C4-code count (closed enum in C4_COVERAGE_CODES)",
        "total_collisions": "sum of C1 codes with count > 0 (strict collisions only)",
        "c1_records": "list of C1 sub-codes observed (ids recoverable via the source parquet)",
        "c2_records": "list of {code, ids} for C2 (ids = sec_id + per-vendor symbol pairs OR expired-alias triple)",
        "c3_records": "list of {code, ticker, message} for C3 (closed-enum class + exact ticker + producer message)",
        "c3_ticker_details": "ticker -> {issuer_state, evidence_source} for every C3 row (master values, not inferred)",
        "c4_records": "list of C4 sub-codes observed (ids recoverable via c1_records-style detail; no per-ticker id list to keep the receipt bounded)",
        "lines": "dated summary lines the CLI prints (one per code, never aggregated)",
    },
}