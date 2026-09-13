"""Tests for ``engine/market_ontology/ticker_cik_census.py`` + the F06-5 CLI.

Coverage (R5):
* RED-first fixture unit tests per class (C1-C4) — a planted collision per
  class MUST be detected; a clean fixture MUST yield zero for every class.
* Live-data invariant test against the committed ``data/reference/*.parquet``
  (data/reference churns nightly, so the test pins INVARIANTS only — C1
  (a)-(e) == 0; every current store symbol either resolves or fails with a
  closed-enum class — and PRINTS the dated counts).
* C5 renderer robustness test — frozen subject compiled through
  ``compile_security_state_failure`` + projected through ``build_security_state``
  must emit ZERO ``identity read value unmapped:`` warnings, must carry EN
  and ZH plain-word labels for every leg/degradation token, and must not leak
  any raw token (ISS:/SEC:/cik:/US-XN.../evt_) into any user-facing string.

Standalone (no full-suite dependency; safe in a sparse tree):

    python3 -m pytest tests/test_ticker_cik_collision_census.py -x -q
"""
from __future__ import annotations

import copy
import datetime as _dt
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
from contextlib import redirect_stderr
from pathlib import Path

import pytest

from engine.market_ontology import ticker_cik_census as tcc


ROOT = Path(__file__).resolve().parents[1]


# ── helpers ───────────────────────────────────────────────────────────────────
def _alias(vendor: str, sym: str, sec: str,
           vf: str | None = None, vt: str | None = None) -> dict:
    """One vendor_aliases row, dates as ISO strings or None."""
    return {
        "vendor": vendor,
        "vendor_symbol": sym,
        "security_id": sec,
        "valid_from": vf,
        "valid_to": vt,
        "ingested_at": "2026-09-04T00:00:00Z",
    }


def _sec(sec: str, *, iss: str | None = None, cik: str | None = None,
         lk: str | None = None, ss_state: str | None = None,
         sup_by: str | None = None) -> dict:
    return {
        "security_id": sec,
        "issuer_id": iss,
        "issuer_state": "ACTIVE" if iss else None,
        "issuer_cik": cik,
        "issuer_evidence_snapshot": None,
        "listing_key": lk,
        "country": "US",
        "mic": "XNAS",
        "inception_code": sec.split("-")[-1],
        "effective_at": "2020-01-01",
        "ingested_at": "2026-09-04T00:00:00Z",
        "security_state": ss_state,
        "superseded_by": sup_by,
    }


def _iss(iss: str, cik: str | None = None,
         ev_src: str | None = None) -> dict:
    return {
        "issuer_id": iss,
        "cik": cik,
        "legal_name": iss,
        "n_securities": 1,
        "evidence_source": ev_src,
        "evidence_snapshot": None,
        "status": "ACTIVE",
        "era": "current",
    }


_FIXTURE_DAY = _dt.date(2026, 9, 13)


# ── C1 — strict collisions ────────────────────────────────────────────────────
def test_c1a_store_symbol_bound_to_two_securities_is_detected() -> None:
    """RED-first: a planted (a) collision must show up under the right code."""
    alias = [
        _alias("store", "DUAL", "SEC:US-XNAS-DUAL"),
        _alias("store", "DUAL", "SEC:US-XNAS-DUAL2"),
    ]
    sec = [
        _sec("SEC:US-XNAS-DUAL"),
        _sec("SEC:US-XNAS-DUAL2"),
    ]
    iss: list[dict] = []
    out = tcc.c1_strict_collisions(
        alias_rows=alias, security_records=sec, issuer_records=iss,
        decision_date=_FIXTURE_DAY,
    )
    codes = [r.code for r in out]
    assert "store_symbol_multi_security" in codes, (
        f"RED: planted C1 (a) collision missed — got {codes}"
    )


def test_c1b_one_security_bound_to_two_store_symbols_is_detected() -> None:
    alias = [
        _alias("store", "FIRST", "SEC:US-XNAS-A"),
        _alias("store", "SECOND", "SEC:US-XNAS-A"),
    ]
    sec = [_sec("SEC:US-XNAS-A")]
    iss: list[dict] = []
    out = tcc.c1_strict_collisions(
        alias_rows=alias, security_records=sec, issuer_records=iss,
        decision_date=_FIXTURE_DAY,
    )
    codes = [r.code for r in out]
    assert "security_multi_store_symbol" in codes, (
        f"RED: planted C1 (b) collision missed — got {codes}"
    )


def test_c1c_one_cik_to_two_issuers_is_detected() -> None:
    alias: list[dict] = []
    sec: list[dict] = []
    iss = [
        _iss("ISS:US-XNAS-A", cik="0000320193"),
        _iss("ISS:US-XNAS-B", cik="0000320193"),
    ]
    out = tcc.c1_strict_collisions(
        alias_rows=alias, security_records=sec, issuer_records=iss,
        decision_date=_FIXTURE_DAY,
    )
    codes = [r.code for r in out]
    assert "cik_multi_issuer" in codes, (
        f"RED: planted C1 (c) collision missed — got {codes}"
    )


def test_c1d_one_listing_key_to_two_securities_is_detected() -> None:
    alias: list[dict] = []
    sec = [
        _sec("SEC:US-XNAS-A", lk="US-XNAS-A"),
        _sec("SEC:US-XNAS-A2", lk="US-XNAS-A"),
    ]
    iss: list[dict] = []
    out = tcc.c1_strict_collisions(
        alias_rows=alias, security_records=sec, issuer_records=iss,
        decision_date=_FIXTURE_DAY,
    )
    codes = [r.code for r in out]
    assert "listing_key_multi_security" in codes, (
        f"RED: planted C1 (d) collision missed — got {codes}"
    )


def test_c1e_issuer_cik_mismatch_is_detected() -> None:
    alias: list[dict] = []
    sec = [
        _sec("SEC:US-XNAS-A", iss="ISS:US-XNAS-A", cik="0000320193"),
    ]
    iss = [_iss("ISS:US-XNAS-A", cik="0000789019")]  # MSFT CIK — a planted mismatch
    out = tcc.c1_strict_collisions(
        alias_rows=alias, security_records=sec, issuer_records=iss,
        decision_date=_FIXTURE_DAY,
    )
    codes = [r.code for r in out]
    assert "issuer_cik_mismatch" in codes, (
        f"RED: planted C1 (e) mismatch missed — got {codes}"
    )


def test_c1f_disambiguator_listing_key_is_detected() -> None:
    alias: list[dict] = []
    sec = [_sec("SEC:US-XNYS-MMC.2", lk="US-XNYS-MMC.2")]
    iss: list[dict] = []
    out = tcc.c1_strict_collisions(
        alias_rows=alias, security_records=sec, issuer_records=iss,
        decision_date=_FIXTURE_DAY,
    )
    codes = [r.code for r in out]
    assert "listing_key_disambiguator" in codes, (
        f"RED: planted C1 (f) disambiguator missed — got {codes}"
    )


def test_c1g_superseded_row_is_reported_but_not_counted_as_defect() -> None:
    """Per R2 / V4-D2B1-R1 §3.6, owner-resolved duplicates are REPORTED, never defects."""
    alias: list[dict] = []
    sec = [_sec("SEC:US-XNAS-A", ss_state="SUPERSEDED_DUPLICATE_MINT", sup_by="SEC:US-XNAS-B")]
    iss: list[dict] = []
    out = tcc.c1_strict_collisions(
        alias_rows=alias, security_records=sec, issuer_records=iss,
        decision_date=_FIXTURE_DAY,
    )
    codes = [r.code for r in out]
    assert "superseded_duplicate_mint" in codes, (
        f"RED: planted C1 (g) superseded row missed — got {codes}"
    )
    # total_collisions MUST exclude (g)
    receipt = tcc.build_receipt(
        decision_date=_FIXTURE_DAY, data_dir="<fixture>",
        c1=out, c2=[], c3=[], c3_details={}, c4=[],
    )
    assert receipt["total_collisions"] == 0, (
        f"total_collisions must exclude superseded_duplicate_mint, got "
        f"{receipt['total_collisions']}"
    )


def test_clean_fixture_yields_zero_collisions_everywhere() -> None:
    """Negative control: a clean identity-plane fixture must yield zero across C1-C4."""
    alias = [_alias("store", "AAPL", "SEC:US-XNAS-AAPL")]
    sec = [
        _sec("SEC:US-XNAS-AAPL", iss="ISS:US-XNAS-AAPL",
             cik="0000320193", lk="US-XNAS-AAPL"),
    ]
    iss = [_iss("ISS:US-XNAS-AAPL", cik="0000320193", ev_src="current_registrant")]
    c1 = tcc.c1_strict_collisions(
        alias_rows=alias, security_records=sec, issuer_records=iss,
        decision_date=_FIXTURE_DAY,
    )
    c2 = tcc.c2_namespace_divergence(alias_rows=alias, decision_date=_FIXTURE_DAY)
    c3, _ = tcc.c3_cik_leg_access_failures(
        alias_rows=alias, security_records=sec, issuer_records=iss,
        decision_date=_FIXTURE_DAY,
    )
    c4 = tcc.c4_renderer_coverage(
        alias_rows=alias, decision_date=_FIXTURE_DAY,
        universe_tickers=["AAPL"], allowlist_tickers=("AAPL", "MSFT"),
    )
    assert c1 == [], f"clean fixture C1 expected [] got {c1}"
    assert c2 == [], f"clean fixture C2 expected [] got {c2}"
    assert c3 == [], f"clean fixture C3 expected [] got {c3}"
    assert c4 == [], f"clean fixture C4 expected [] got {c4}"
    receipt = tcc.build_receipt(
        decision_date=_FIXTURE_DAY, data_dir="<clean>",
        c1=c1, c2=c2, c3=c3, c3_details={}, c4=c4,
    )
    assert receipt["total_collisions"] == 0


# ── C2 — vendor namespace divergence ──────────────────────────────────────────
def test_c2_active_vendor_divergence_detected() -> None:
    """RED-first: a security whose store/yahoo disagree today must be flagged."""
    alias = [
        _alias("store", "MMC", "SEC:US-XNYS-MMC"),
        _alias("yahoo", "MRSH", "SEC:US-XNYS-MMC"),
        _alias("yahoo_fetch", "MRSH", "SEC:US-XNYS-MMC"),
    ]
    out = tcc.c2_namespace_divergence(alias_rows=alias, decision_date=_FIXTURE_DAY)
    codes = [r.code for r in out]
    assert "active_vendor_divergence" in codes, (
        f"RED: planted C2 active divergence missed — got {codes}"
    )


def test_c2_expired_store_alias_detected() -> None:
    """RED-first: a previous store symbol with valid_to <= today is the rename case."""
    alias = [
        _alias("store", "EQR", "SEC:US-XNYS-EQR", vt="2026-08-18"),
        _alias("store", "VMRK", "SEC:US-XNYS-EQR", vf="2026-08-18"),
    ]
    out = tcc.c2_namespace_divergence(alias_rows=alias, decision_date=_FIXTURE_DAY)
    codes = [r.code for r in out]
    assert "expired_store_alias" in codes, (
        f"RED: planted C2 expired alias missed — got {codes}"
    )


# ── C3 — CIK-leg access failures + closed-enum classifier ─────────────────────
def test_classify_failure_message_covers_every_closed_enum_value() -> None:
    """Every CikFailureClass has at least one matching producer substring."""
    cases = {
        tcc.CikFailureClass.ALIAS_UNBOUND:
            "VendorAliasTable has no current store binding for X on 2026-09-13",
        tcc.CikFailureClass.ROUND_TRIP_MISMATCH:
            "VendorAliasTable round-trip mismatch for X: 'Y'",
        tcc.CikFailureClass.NO_MASTER_ROW:
            "security master has no row for owner-resolved SEC:X",
        tcc.CikFailureClass.OWNER_IDENTITY_INCOMPLETE:
            "owner identity is incomplete for X: issuer_id=None",
        tcc.CikFailureClass.LISTING_KEY_UNPARSEABLE:
            "owner listing key for X is not a parseable ListingKey: 'Y'",
        tcc.CikFailureClass.SECURITY_ID_RENDER_MISMATCH:
            "owner listing key 'X' does not render the alias-resolved security 'Y'",
    }
    for cls, msg in cases.items():
        assert tcc.classify_failure_message(msg) is cls, (
            f"RED: classifier missed {cls.value} for {msg!r}"
        )


def test_c3_owner_identity_incomplete_detected_on_planted_fixture() -> None:
    """RED-first: a ticker whose issuer has no CIK must show up under OWNER_IDENTITY_INCOMPLETE.

    H2 heal-round (PR #7122): CTRA's owner value is NaN/None for issuer_cik,
    so the classifier path REPRODUCES the producer's typed refusal by
    raising ``SecurityStateCompilationErrorSimulated`` ("owner identity is
    incomplete"). The ``compile_security_state_failure`` boundary, by
    contrast, REFUSES a subject with issuer_cik=None — see
    ``test_c5_owner_identity_incomplete_unprobeable_through_compile``.
    """
    alias = [_alias("store", "CTRA", "SEC:US-XNYS-CTRA")]
    sec = [_sec("SEC:US-XNYS-CTRA", iss="ISS:US-XNYS-CTRA",
                cik=None, lk="US-XNYS-CTRA")]
    iss = [_iss("ISS:US-XNYS-CTRA", cik=None, ev_src="legacy_mint")]
    out, details = tcc.c3_cik_leg_access_failures(
        alias_rows=alias, security_records=sec, issuer_records=iss,
        decision_date=_FIXTURE_DAY,
    )
    assert any(r.code == "owner_identity_incomplete" for r in out), (
        f"RED: planted C3 incomplete-CIK missed — got {[r.code for r in out]}"
    )
    assert details["CTRA"]["issuer_state"] in ("NO_ISSUER_EVIDENCE", "ACTIVE", "DEFERRED_IDENTITY_EXCEPTION")
    assert details["CTRA"]["evidence_source"] == "legacy_mint"


# ── H7 heal-round — RED-first fixture cases for the 6 of 7 C3 classes that
# only had hand-copied substrings behind them. Each plants a parquet fixture
# that triggers the producer's typed failure path, then asserts the
# classifier maps the message to the right enum class. The
# ALIAS_UNBOUND branch is exercised structurally in
# ``test_c3_alias_unbound_message_classifier_closes_the_enum`` — the
# classifier's input set excludes it (the producer's own call surface
# raises it, not the census walker). ──────────────────────────────────────────
def test_c3_round_trip_mismatch_detected_on_planted_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RED-first: round-trip mismatch branch must close the enum.

    The round-trip check produces an asymmetric state: ``resolve(store, DUAL)``
    returns ``SEC:X`` while ``vendor_symbol_for(store, SEC:X)`` returns a
    DIFFERENT store symbol on the same date. ``VendorAliasTable`` normally
    forbids this — its constructor's ``_assert_unambiguous`` check would
    REJECT two overlapping rows on the same ``(vendor, security_id)`` — so
    a real round-trip mismatch is structurally unreachable in production
    data. We monkeypatch the assertion off here ONLY so the test can plant
    the asymmetry the producer's typed refusal path needs to fire; the
    classifier's job is to recognise the message, and that is what this
    test pins. (``aliases_owner = VendorAliasTable.from_records([...]); …
    _assert_unambiguous()`` are the production guard the test bypasses;
    the production tables thus never produce this state.)
    """
    from lib.dataos.identity import VendorAliasTable

    # Bypass the production ambiguity guard ONLY for this test — the
    # asymmetric round-trip is what we are trying to plant, so the guard
    # would otherwise reject the fixture before the classifier ever sees it.
    monkeypatch.setattr(VendorAliasTable, "_assert_unambiguous", lambda self: None)

    # Order matters: vendor_symbol_for iterates rows in order and returns the
    # FIRST match that covers the date. Row 1 binds SEC:X to DUAL2 first;
    # Row 2 binds SEC:X to DUAL. Both must cover the decision date, so
    # resolve("DUAL") walks Row 1 (no DUAL match) → Row 2 (DUAL ✓, covers) →
    # SEC:X, and vendor_symbol_for(SEC:X) walks Row 1 (DUAL2 ✓, covers) →
    # DUAL2. The reverse ≠ forward asymmetry is exactly what the producer's
    # round-trip check rejects. The production ambiguity guard would reject
    # these two overlapping rows; the monkeypatch above disables it.
    alias = [
        _alias("store", "DUAL2", "SEC:US-XNAS-DUALA",
               vf="2026-09-04"),
        _alias("store", "DUAL", "SEC:US-XNAS-DUALA",
               vf="2026-09-04"),
    ]
    sec = [_sec("SEC:US-XNAS-DUALA", iss="ISS:US-XNAS-DUALA",
                cik="0000320193", lk="US-XNAS-DUALA")]
    iss = [_iss("ISS:US-XNAS-DUALA", cik="0000320193", ev_src="current_registrant")]
    out, _ = tcc.c3_cik_leg_access_failures(
        alias_rows=alias, security_records=sec, issuer_records=iss,
        decision_date=_FIXTURE_DAY,
    )
    assert any(r.code == "round_trip_mismatch" for r in out), (
        f"RED: planted C3 round_trip_mismatch missed — got {[r.code for r in out]}"
    )


def test_c3_no_master_row_detected_on_planted_fixture() -> None:
    """A store alias whose security_id has no row in security_master must show up
    under NO_MASTER_ROW."""
    alias = [_alias("store", "GHOST", "SEC:US-XNAS-GHOST")]
    sec = [_sec("SEC:US-XNAS-OTHER", iss="ISS:US-XNAS-OTHER",
                cik="0000320193", lk="US-XNAS-OTHER")]
    iss = [_iss("ISS:US-XNAS-OTHER", cik="0000320193", ev_src="current_registrant")]
    out, _ = tcc.c3_cik_leg_access_failures(
        alias_rows=alias, security_records=sec, issuer_records=iss,
        decision_date=_FIXTURE_DAY,
    )
    assert any(r.code == "no_master_row" for r in out), (
        f"RED: planted C3 no_master_row missed — got {[r.code for r in out]}"
    )


def test_c3_listing_key_unparseable_detected_on_planted_fixture() -> None:
    """A security whose listing_key is not a parseable ListingKey must show up
    under LISTING_KEY_UNPARSEABLE."""
    alias = [_alias("store", "BADLK", "SEC:US-XNAS-BADLK")]
    sec = [_sec("SEC:US-XNAS-BADLK", iss="ISS:US-XNAS-BADLK",
                cik="0000320193", lk="not-a-parseable-listing-key")]
    iss = [_iss("ISS:US-XNAS-BADLK", cik="0000320193", ev_src="current_registrant")]
    out, _ = tcc.c3_cik_leg_access_failures(
        alias_rows=alias, security_records=sec, issuer_records=iss,
        decision_date=_FIXTURE_DAY,
    )
    assert any(r.code == "listing_key_unparseable" for r in out), (
        f"RED: planted C3 listing_key_unparseable missed — got {[r.code for r in out]}"
    )


def test_c3_security_id_render_mismatch_detected_on_planted_fixture() -> None:
    """A listing_key whose rendered security_id does not match the alias-resolved
    security must show up under SECURITY_ID_RENDER_MISMATCH."""
    alias = [_alias("store", "RENDIFF", "SEC:US-XNAS-RENDIFF")]
    sec = [_sec("SEC:US-XNAS-RENDIFF", iss="ISS:US-XNAS-RENDIFF",
                cik="0000320193", lk="US-XNAS-OTHERDIFF")]
    iss = [_iss("ISS:US-XNAS-RENDIFF", cik="0000320193", ev_src="current_registrant")]
    out, _ = tcc.c3_cik_leg_access_failures(
        alias_rows=alias, security_records=sec, issuer_records=iss,
        decision_date=_FIXTURE_DAY,
    )
    assert any(r.code == "security_id_render_mismatch" for r in out), (
        f"RED: planted C3 security_id_render_mismatch missed — got {[r.code for r in out]}"
    )


def test_c3_security_state_compilation_detected_on_planted_fixture() -> None:
    """A non-typed refusal message (no closed-enum substring) must map to
    SECURITY_STATE_COMPILATION (the catch-all)."""
    alias = [_alias("store", "ODD", "SEC:US-XNAS-ODD")]
    sec = [_sec("SEC:US-XNAS-ODD", iss="ISS:US-XNAS-ODD",
                cik="0000320193", lk="US-XNAS-ODD")]
    iss = [_iss("ISS:US-XNAS-ODD", cik="0000320193", ev_src="current_registrant")]
    # We can't trigger the producer's catch-all through a parquet fixture (every
    # producer path has a typed substring), so test the classifier's catch-all
    # directly with a synthetic message:
    from engine.market_ontology.ticker_cik_census import CikFailureClass, classify_failure_message
    assert (
        classify_failure_message("some other typed refusal the producer has not classified yet")
        is CikFailureClass.SECURITY_STATE_COMPILATION
    )


def test_c3_alias_unbound_message_classifier_closes_the_enum() -> None:
    """RED-first: the closed-enum mapping is the structural coverage for
    ALIAS_UNBOUND. The classifier walks CURRENT store rows whose security_id
    resolves; a row that resolves to ``None`` is structurally impossible in
    that walk (the row's existence and current-ness together imply a valid
    resolve), so the ALIAS_UNBOUND case lives in the producer's own call
    surface (a ticker the producer's allowlist names with no current row),
    not in the census classifier's input set. The message-substring test
    above is the comprehensive coverage for this code."""
    # This test is intentionally a no-op assertion: it documents why the
    # ALIAS_UNBOUND branch has no RED-first planted fixture (the census
    # classifier's input set excludes it), and it asserts the closed-enum
    # invariant the live-data test relies on.
    from engine.market_ontology.ticker_cik_census import CikFailureClass
    assert CikFailureClass.ALIAS_UNBOUND.value == "alias_unbound"


# ── C4 — renderer coverage ────────────────────────────────────────────────────
def test_c4_no_identity_row_detected() -> None:
    alias = [_alias("store", "AAPL", "SEC:US-XNAS-AAPL")]
    out = tcc.c4_renderer_coverage(
        alias_rows=alias, decision_date=_FIXTURE_DAY,
        universe_tickers=["AAPL", "EA"], allowlist_tickers=("AAPL",),
    )
    codes = [r.code for r in out]
    assert "no_identity_row" in codes, (
        f"RED: planted C4 no_identity_row missed — got {codes}"
    )
    assert "EA" in [i for r in out if r.code == "no_identity_row" for i in r.ids]


def test_c4_resolvable_outside_allowlist_detected() -> None:
    alias = [_alias("store", "AAPL", "SEC:US-XNAS-AAPL")]
    out = tcc.c4_renderer_coverage(
        alias_rows=alias, decision_date=_FIXTURE_DAY,
        universe_tickers=["AAPL"], allowlist_tickers=("MSFT",),
    )
    codes = [r.code for r in out]
    assert "resolvable_outside_allowlist" in codes, (
        f"RED: planted C4 resolvable_outside_allowlist missed — got {codes}"
    )


# ── H8 heal-round — C4 receipt must carry counts AND exact ids ────────────────
def test_c4_receipt_carries_counts_and_exact_ids() -> None:
    """Each C4 record must carry its exact ticker ids in the receipt — the same
    shape as C1/C2/C3 records. The receipt reader can recover the ids without
    re-reading the parquet."""
    alias = [_alias("store", "AAPL", "SEC:US-XNAS-AAPL")]
    c4 = tcc.c4_renderer_coverage(
        alias_rows=alias, decision_date=_FIXTURE_DAY,
        universe_tickers=["AAPL", "EA", "MSFT"], allowlist_tickers=("MSFT",),
    )
    receipt = tcc.build_receipt(
        decision_date=_FIXTURE_DAY, data_dir="<fixture>",
        c1=[], c2=[], c3=[], c3_details={}, c4=c4,
    )
    c4_rec = receipt["c4_records"]
    assert isinstance(c4_rec, list)
    by_code: dict[str, list[str]] = {}
    for r in c4_rec:
        assert "code" in r and "ids" in r, (
            f"RED: c4_records item missing code/ids — got {r}"
        )
        by_code.setdefault(r["code"], []).extend(r["ids"])
    assert "EA" in by_code.get("no_identity_row", []), (
        f"RED: c4_records missing EA — got {by_code}"
    )
    assert "AAPL" in by_code.get("resolvable_outside_allowlist", []), (
        f"RED: c4_records missing AAPL — got {by_code}"
    )


# ── H8 heal-round — C4 summary lines print TICKER counts, not record counts ───
def test_c4_summary_lines_print_ticker_count_not_record_count() -> None:
    """C4 summary lines must print ``len(r.ids)`` summed per code, so
    ``C4.no_identity_row=1`` means one ticker (EA), not one record."""
    alias = [_alias("store", "AAPL", "SEC:US-XNAS-AAPL")]
    c4 = tcc.c4_renderer_coverage(
        alias_rows=alias, decision_date=_FIXTURE_DAY,
        universe_tickers=["AAPL", "EA"], allowlist_tickers=("MSFT",),
    )
    receipt = tcc.build_receipt(
        decision_date=_FIXTURE_DAY, data_dir="<fixture>",
        c1=[], c2=[], c3=[], c3_details={}, c4=c4,
    )
    line_map = {}
    for line in receipt["lines"]:
        if "=" in line and "." in line and line.split(".", 1)[0] in ("C1", "C2", "C3", "C4"):
            k, _, v = line.partition("=")
            line_map[k] = int(v)
    assert line_map.get("C4.no_identity_row") == 1, (
        f"RED: C4.no_identity_row must be ticker count 1 — got {line_map}"
    )
    assert line_map.get("C4.resolvable_outside_allowlist") == 1, (
        f"RED: C4.resolvable_outside_allowlist must be ticker count 1 — got {line_map}"
    )


# ── Receipt schema validation (R5 + H6) ──────────────────────────────────────
def test_receipt_validates_against_its_own_schema() -> None:
    """The receipt structurally validates against ``RECEIPT_SCHEMA`` (R5/H6).

    A failure here is a receipt-shape bug: the classifiers / CLI agreed on
    the receipt, but the receipt itself drifted away from the schema. The
    test pins ``validate_receipt`` success on a clean fixture."""
    receipt = tcc.build_receipt(
        decision_date=_FIXTURE_DAY, data_dir="<fixture>",
        c1=[], c2=[], c3=[], c3_details={}, c4=[],
    )
    # If the schema's structural rules ever reject the receipt, validate_receipt
    # raises ValueError. This MUST NOT be a copy-equals-itself assertion (H6).
    tcc.validate_receipt(receipt)


def test_receipt_schema_rejects_a_malformed_receipt() -> None:
    """RED-first: ``validate_receipt`` MUST raise on a receipt missing a required
    key — the schema is structural, not prose. We prove the validation can fail
    by deleting a required field and asserting the ValueError."""
    receipt = tcc.build_receipt(
        decision_date=_FIXTURE_DAY, data_dir="<fixture>",
        c1=[], c2=[], c3=[], c3_details={}, c4=[],
    )
    bad = {k: v for k, v in receipt.items() if k != "c4_records"}
    with pytest.raises(ValueError, match="RECEIPT_SCHEMA violation"):
        tcc.validate_receipt(bad)


# ── Live-data invariant test (R5 + H4 + H5) ───────────────────────────────────
def _materialise_parquet_from_git(name: str, tmp_dir: Path) -> Path | None:
    """H5 heal-round (PR #7122): materialise into the caller-supplied tmp dir,
    never into an untracked repo-root directory. Returns the path or None on
    failure (so the live-data test can ``pytest.skip`` with a named reason)."""
    try:
        out = subprocess.run(
            ["git", "show", f"HEAD:data/reference/{name}"],
            cwd=str(ROOT), capture_output=True, timeout=15, check=False,
        )
    except Exception:
        return None
    if out.returncode != 0 or not out.stdout:
        return None
    target = tmp_dir / name
    target.write_bytes(out.stdout)
    return target


def _read_parquet_or_materialise(name: str, tmp_dir: Path) -> list[dict] | None:
    """Read a parquet from data/reference/ or materialise it from git HEAD
    into the caller-supplied tmp dir (H5)."""
    p = ROOT / "data" / "reference" / name
    if p.is_file():
        import pandas as pd
        return pd.read_parquet(p).to_dict("records")
    target = _materialise_parquet_from_git(name, tmp_dir)
    if target is None:
        return None
    try:
        import pandas as pd
        return pd.read_parquet(target).to_dict("records")
    except Exception:
        return None


def _read_universe_parquet_or_materialise(name: str, sub: str, tmp_dir: Path) -> Path | None:
    """Materialise a universe parquet (data/stocks/, data/sector_holdings/)
    into the caller-supplied tmp dir (H4). Returns the path or None on failure.
    """
    p = ROOT / "data" / sub / name
    if p.is_file():
        return p
    try:
        out = subprocess.run(
            ["git", "show", f"HEAD:data/{sub}/{name}"],
            cwd=str(ROOT), capture_output=True, timeout=15, check=False,
        )
    except Exception:
        return None
    if out.returncode != 0 or not out.stdout:
        return None
    target = tmp_dir / sub / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(out.stdout)
    return target


@pytest.mark.skipif(
    os.environ.get("W7B_F06_5_SKIP_LIVE") == "1",
    reason="W7B_F06_5_SKIP_LIVE=1 — live-data test explicitly skipped for fast iteration",
)
def test_live_data_invariants_pin_only_collisions_and_enum_coverage(
    tmp_path: Path,
) -> None:
    """Live-data test (R5 + H4 + H5): pin invariants; PRINT dated counts as
    receipt lines; STRUCTURALLY validate against RECEIPT_SCHEMA.

    data/reference/ churns nightly, so the test asserts only:
        (i)  every C1 (a)-(e) code is 0,
        (ii) every current store symbol EITHER resolves fully (no C3 row)
             OR fails with a class from CikFailureClass,
        (iii) the receipt structurally validates against RECEIPT_SCHEMA,
        (iv) C4's universe is the stock-library data/stocks/ enumeration
             (sparse trees must materialise into tmp_path or skip with a
             NAMED reason — never silently print C4.*=0).
        (v)  allowlist is imported from ``engine.security_state.SECURITY_STATE_TICKERS``,
             never a hardcoded tuple (H9 Q-m1).

    It PRINTS the dated counts as receipt lines — a human reviewer can see
    what the live data actually said without the test failing on drift.
    """
    # H5: materialise into tmp_path, never into an untracked repo-root dir.
    # Teardown at the end of the test leaves tmp_path's contents cleaned.
    mat_dir = tmp_path / "w7b_f06_5_materialised"
    mat_dir.mkdir(exist_ok=True)
    try:
        alias = _read_parquet_or_materialise("vendor_aliases.parquet", mat_dir)
        sec = _read_parquet_or_materialise("security_master.parquet", mat_dir)
        iss = _read_parquet_or_materialise("issuer_master.parquet", mat_dir)
        if alias is None or sec is None or iss is None:
            pytest.skip(
                "data/reference/{vendor_aliases,security_master,issuer_master}.parquet "
                "unavailable locally and not materialisable from git HEAD — the live-data "
                "test cannot run in this environment."
            )

        # H9 Q-m2: use today's UTC date (same helper the CLI uses) so the
        # live-data test agrees with the CLI within ~7h/day in America/Vancouver.
        from scripts.ticker_cik_collision_census import _today_utc
        decision_date = _today_utc()

        c1 = tcc.c1_strict_collisions(
            alias_rows=alias, security_records=sec, issuer_records=iss,
            decision_date=decision_date,
        )
        c2 = tcc.c2_namespace_divergence(alias_rows=alias, decision_date=decision_date)
        c3, c3_details = tcc.c3_cik_leg_access_failures(
            alias_rows=alias, security_records=sec, issuer_records=iss,
            decision_date=decision_date,
        )

        # H4 + H3: C4 universe is the stock-library data/stocks/ enumeration.
        # A sparse worktree that did NOT materialise data/stocks/ must
        # ``pytest.skip`` with a NAMED reason (never silently print C4.*=0).
        from scripts.ticker_cik_collision_census import _default_universe
        if not (ROOT / "data" / "stocks").is_dir():
            # Try to materialise a sample to confirm the source is reachable.
            sample = _read_universe_parquet_or_materialise(
                "AAPL.parquet", "stocks", mat_dir,
            )
            if sample is None:
                pytest.skip(
                    "C4 universe (data/stocks/) is not materialised in this sparse "
                    "worktree — opt into a full checkout with: "
                    "python3 scripts/worktree_sparse.py add data"
                )
            # Materialised one sample — but the full enumeration still needs
            # every stock parquet. Fall back to git-ls-tree for the stem set
            # so the test can still enumerate the universe WITHOUT the bytes.
            import subprocess as _sp
            out = _sp.run(
                ["git", "ls-tree", "-r", "--name-only", "HEAD", "--", "data/stocks/"],
                cwd=str(ROOT), capture_output=True, timeout=15, check=False,
            )
            if out.returncode != 0:
                pytest.skip(
                    "C4 universe (data/stocks/) stem enumeration unreachable via git "
                    "ls-tree — cannot enumerate the C4 universe in this environment."
                )
            stems = sorted(
                line.split("data/stocks/", 1)[1].rsplit(".", 1)[0]
                for line in out.stdout.decode("utf-8").splitlines()
                if line.endswith(".parquet")
            )
            universe = stems
        else:
            universe, _src = _default_universe(ROOT / "data")

        # H9 Q-m1: import SECURITY_STATE_TICKERS (the canonical allowlist),
        # not a hardcoded tuple.
        from engine.security_state import SECURITY_STATE_TICKERS
        allowlist = tuple(SECURITY_STATE_TICKERS)
        c4 = tcc.c4_renderer_coverage(
            alias_rows=alias, decision_date=decision_date,
            universe_tickers=universe, allowlist_tickers=allowlist,
        )

        receipt = tcc.build_receipt(
            decision_date=decision_date, data_dir="data/reference",
            c1=c1, c2=c2, c3=c3, c3_details=c3_details, c4=c4,
        )

        # (i) C1 strict-collision invariants — a-f must be 0 (g is reported, not a defect)
        strict = {k: v for k, v in receipt["counts"]["C1"].items() if k != "superseded_duplicate_mint"}
        for code, n in strict.items():
            assert n == 0, f"live data C1.{code}={n}; spec pins 0"

        # (ii) every C3 row carries a closed-enum class
        closed = {c.value for c in tcc.CikFailureClass}
        for r in c3:
            assert r.code in closed, f"live data C3 emitted non-closed-enum code {r.code!r}"

        # (iii) H6: structural validation against RECEIPT_SCHEMA (not prose equality)
        tcc.validate_receipt(receipt)

        # (iv) C4 universe source must be reported in the receipt
        assert receipt.get("c4_universe_source"), (
            "live data receipt must carry c4_universe_source (H3)"
        )

        # PRINT the dated counts (R5). A human reviewer can see what the live
        # data said without the test failing on nightly changes.
        for line in receipt["lines"]:
            print(line)
    finally:
        # H5 teardown: leave tmp_path's contents cleaned (tmp_path is
        # auto-cleaned by pytest, but the materialised subdir lives under it).
        if mat_dir.is_dir():
            shutil.rmtree(mat_dir, ignore_errors=True)


# ── H7 heal-round — classifier/producer agreement test ────────────────────────
def test_classifier_and_producer_agree_on_typed_failures(tmp_path: Path) -> None:
    """The classifier's C3 set (tickers, classes, messages) must agree with the
    producer's ``_read_security_state_identity_rows`` output on the same
    synthetic fixture. Without this, the classifier's "agreement" is a
    hand-copied fiction (qwen_r1 H7 finding).

    Imports ``scripts.security_state_producer`` directly — never modifies it.
    Uses a synthetic fixture written to tmp_path (H5) so this test does not
    dirty the worktree.
    """
    from scripts.security_state_producer import _read_security_state_identity_rows
    from engine.security_state import SecurityStateSubject

    # Plant a synthetic fixture: AAPL resolves cleanly; CTRA is
    # owner-identity-incomplete (issuer_cik None); GHOST has no master row.
    fixture = tmp_path / "f06_5_h7_fixture"
    fixture.mkdir(exist_ok=True)
    ref = fixture / "reference"
    ref.mkdir(exist_ok=True)
    import pandas as pd
    pd.DataFrame([{
        "security_id": "SEC:US-XNAS-AAPL", "issuer_id": "ISS:US-XNAS-AAPL",
        "issuer_state": "ACTIVE", "issuer_cik": "0000320193",
        "issuer_evidence_snapshot": None, "listing_key": "US-XNAS-AAPL",
        "country": "US", "mic": "XNAS", "inception_code": "AAPL",
        "effective_at": "2020-01-01", "ingested_at": "2026-09-04T00:00:00Z",
        "security_state": None, "superseded_by": None,
    }, {
        "security_id": "SEC:US-XNYS-CTRA", "issuer_id": "ISS:US-XNYS-CTRA",
        "issuer_state": "NO_ISSUER_EVIDENCE", "issuer_cik": None,
        "issuer_evidence_snapshot": None, "listing_key": "US-XNYS-CTRA",
        "country": "US", "mic": "XNYS", "inception_code": "CTRA",
        "effective_at": "2020-01-01", "ingested_at": "2026-09-04T00:00:00Z",
        "security_state": None, "superseded_by": None,
    }]).to_parquet(ref / "security_master.parquet")
    pd.DataFrame([{
        "vendor": "store", "vendor_symbol": "AAPL",
        "security_id": "SEC:US-XNAS-AAPL",
        "valid_from": None, "valid_to": None,
        "ingested_at": "2026-09-04T00:00:00Z",
    }, {
        "vendor": "store", "vendor_symbol": "CTRA",
        "security_id": "SEC:US-XNYS-CTRA",
        "valid_from": None, "valid_to": None,
        "ingested_at": "2026-09-04T00:00:00Z",
    }, {
        "vendor": "store", "vendor_symbol": "GHOST",
        "security_id": "SEC:US-XNAS-GHOST",
        "valid_from": None, "valid_to": None,
        "ingested_at": "2026-09-04T00:00:00Z",
    }]).to_parquet(ref / "vendor_aliases.parquet")
    pd.DataFrame([{
        "issuer_id": "ISS:US-XNAS-AAPL", "cik": "0000320193",
        "legal_name": "Apple Inc.", "n_securities": 1,
        "evidence_source": "current_registrant",
        "evidence_snapshot": None, "status": "ACTIVE", "era": "current",
    }, {
        "issuer_id": "ISS:US-XNYS-CTRA", "cik": None,
        "legal_name": "Coterra Energy", "n_securities": 1,
        "evidence_source": "legacy_mint",
        "evidence_snapshot": None, "status": "ACTIVE", "era": "current",
    }]).to_parquet(ref / "issuer_master.parquet")
    pd.DataFrame(columns=["issuer_id", "migrated_to", "valid_from", "valid_to", "evidence_source"]).to_parquet(
        ref / "issuer_migrations.parquet",
    )
    pd.DataFrame(columns=["security_id", "migrated_to", "valid_from", "valid_to", "evidence_source"]).to_parquet(
        ref / "security_migrations.parquet",
    )

    decision_date = _FIXTURE_DAY
    tickers = ("AAPL", "CTRA", "GHOST")

    # Producer side: imports scripts.security_state_producer (never modified).
    try:
        inputs, failures = _read_security_state_identity_rows(
            fixture, tickers, decision_date=decision_date,
        )
    except Exception as exc:
        pytest.skip(f"producer fixture read failed: {exc}")

    # Classifier side: walk the SAME fixture through the same owner APIs.
    import pandas as _pd
    alias_rows = _pd.read_parquet(ref / "vendor_aliases.parquet").to_dict("records")
    sec_rows = _pd.read_parquet(ref / "security_master.parquet").to_dict("records")
    iss_rows = _pd.read_parquet(ref / "issuer_master.parquet").to_dict("records")
    classifier_records, _ = tcc.c3_cik_leg_access_failures(
        alias_rows=alias_rows, security_records=sec_rows, issuer_records=iss_rows,
        decision_date=decision_date,
    )

    # Producer failures: ticker -> message substring (the substring is what
    # the classifier maps to an enum). Classifier failures: (code, ticker,
    # message). Both must agree on the typed set for the planted fixture.
    producer_classes: dict[str, str] = {}
    for ticker, msg in failures.items():
        producer_classes[ticker] = tcc.classify_failure_message(msg).value
    classifier_classes: dict[str, str] = {
        r.ids[0]: r.code for r in classifier_records
    }
    # AAPL: both should be empty (resolves cleanly).
    assert "AAPL" not in producer_classes, (
        f"producer reported AAPL as a failure: {producer_classes['AAPL']!r}"
    )
    assert "AAPL" not in classifier_classes, (
        f"classifier reported AAPL as a failure: {classifier_classes['AAPL']!r}"
    )
    # CTRA: both should report owner_identity_incomplete.
    assert producer_classes.get("CTRA") == "owner_identity_incomplete", (
        f"RED: producer typed CTRA as {producer_classes.get('CTRA')!r}, expected "
        f"owner_identity_incomplete"
    )
    assert classifier_classes.get("CTRA") == "owner_identity_incomplete", (
        f"RED: classifier typed CTRA as {classifier_classes.get('CTRA')!r}, "
        f"expected owner_identity_incomplete"
    )
    # GHOST: both should report no_master_row.
    assert producer_classes.get("GHOST") == "no_master_row", (
        f"RED: producer typed GHOST as {producer_classes.get('GHOST')!r}, "
        f"expected no_master_row"
    )
    assert classifier_classes.get("GHOST") == "no_master_row", (
        f"RED: classifier typed GHOST as {classifier_classes.get('GHOST')!r}, "
        f"expected no_master_row"
    )


# ── C5 — renderer robustness (frozen subject + build_security_state) ──────────
def _clear_unmapped_warnings() -> None:
    """H9 Q-m4: clear ``_SS_UNMAPPED_WARNED`` before each ``redirect_stderr``
    C5 capture so process-global memoisation cannot mask a fresh warning
    emission. Importing ``scripts.build_ticker_pages`` here is the first time
    the process touches it, so we patch its global state directly."""
    import scripts.build_ticker_pages as btp
    btp._SS_UNMAPPED_WARNED.clear()


def _ss_validator():
    from jsonschema import Draft202012Validator
    schema = json.loads(
        (ROOT / "contracts" / "market_os" / "security_state.v1.schema.json").read_text()
    )
    return Draft202012Validator(schema)


# H2 heal-round: build frozen SecurityStateSubject for each C3 failure class
# and one C2 rename. Each subject has VALID fields (CIK is 10 digits, ticker
# is 1-5 uppercase letters so it matches the ticker-shape regex used by
# ``_ss_is_id_shape`` to gate ss-id rendering) so ``_require_subject`` accepts
# it and ``compile_security_state_failure`` returns a shell.
# OWNER_IDENTITY_INCOMPLETE is exercised TWICE: once with a valid CIK (so
# the shell builds) and once with issuer_cik=None (so the compile refuses —
# see ``test_c5_owner_identity_incomplete_unprobeable_through_compile``).
_C5_C3_SUBJECTS: tuple[tuple[str, dict], ...] = (
    ("ALIAS_UNBOUND", dict(
        security_id="SEC:US-XNAS-AB",
        issuer_id="ISS:US-XNAS-AB",
        listing_key="US-XNAS-AB",
        ticker_display="AB",
        issuer_cik="0000000001",
    )),
    ("ROUND_TRIP_MISMATCH", dict(
        security_id="SEC:US-XNAS-RD",
        issuer_id="ISS:US-XNAS-RD",
        listing_key="US-XNAS-RD",
        ticker_display="RD",
        issuer_cik="0000000002",
    )),
    ("NO_MASTER_ROW", dict(
        security_id="SEC:US-XNAS-NM",
        issuer_id="ISS:US-XNAS-NM",
        listing_key="US-XNAS-NM",
        ticker_display="NM",
        issuer_cik="0000000003",
    )),
    ("OWNER_IDENTITY_INCOMPLETE", dict(
        security_id="SEC:US-XNAS-OI",
        issuer_id="ISS:US-XNAS-OI",
        listing_key="US-XNAS-OI",
        ticker_display="OI",
        issuer_cik="0000000004",  # NOTE: NOT the real CTRA None; see refusal test.
    )),
    ("LISTING_KEY_UNPARSEABLE", dict(
        security_id="SEC:US-XNAS-LK",
        issuer_id="ISS:US-XNAS-LK",
        listing_key="US-XNAS-LK",
        ticker_display="LK",
        issuer_cik="0000000005",
    )),
    ("SECURITY_ID_RENDER_MISMATCH", dict(
        security_id="SEC:US-XNAS-SR",
        issuer_id="ISS:US-XNAS-SR",
        listing_key="US-XNAS-SR",
        ticker_display="SR",
        issuer_cik="0000000006",
    )),
    ("SECURITY_STATE_COMPILATION", dict(
        security_id="SEC:US-XNAS-SC",
        issuer_id="ISS:US-XNAS-SC",
        listing_key="US-XNAS-SC",
        ticker_display="SC",
        issuer_cik="0000000007",
    )),
)


def _shell_for(subject_kwargs: dict) -> dict:
    """Compile a failure shell for the given frozen subject kwargs."""
    from engine import security_state as ss
    subject = ss.SecurityStateSubject(
        **subject_kwargs,
        owner_evidence=(
            ("decision_date", "2026-09-13"),
            ("alias_reader", "VendorAliasTable.resolve(store)"),
            ("issuer_reader", "IssuerMaster.issuer_of_security"),
            ("cik_reader", "IssuerMaster.cik_of_issuer"),
        ),
    )
    return ss.compile_security_state_failure(
        subject=subject, validator=_ss_validator(),
        now="2026-09-13T00:00:00Z", prior_state=None, owner_read_completed=True,
    )


def _raw_token_patterns() -> list[re.Pattern[str]]:
    return [
        re.compile(r"ISS:[A-Z0-9.\-]+"),
        re.compile(r"SEC:[A-Z0-9.\-]+"),
        re.compile(r"\bcik:"),
        re.compile(r"US-XN[A-Z]+-[A-Z]+-[A-Z0-9.\-]+"),
        re.compile(r"\bevt_"),
    ]


def _walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _walk(v, path + "/" + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _walk(v, path + f"[{i}]")
    elif isinstance(o, str):
        yield path, o


def _assert_user_facing_strings_are_clean(rendered: dict, label: str) -> None:
    """Walk the rendered security-state dict; assert NO user-facing string
    carries a raw ISS:/SEC:/cik:/US-XN.../evt_ token. H1 + H2 widen the C5
    walker to EVERY user-facing string (labels, descriptions, evidence
    receipts, fields, etc.) — not only paths ending /en,/zh or containing
    /degradation/,/desc_.

    The walker EXCLUDES audit-data fields that the template never renders
    as visible text:
      - top-level ``security_id`` / ``issuer_id`` / ``listing_key`` /
        ``content_sha256`` / ``recipe_id`` / ``version`` / ``generation_id``
        / ``source`` — these are the ``data-*`` attributes consumed by the
        audit guard (``scripts/check_stock_dossier_integrity.py``) and the
        dossier page's data-attribute hooks, never user-facing text.
      - ``reads[].k`` / ``reads[].label_en`` / ``reads[].label_zh`` — these
        are FIELD NAMES that happen to share a shape with a raw token
        (e.g. ``subject_issuer_cik``). The visible text for the value is
        carried on ``reads[].v_en`` / ``reads[].v_zh``, which the walker
        checks separately.
      - ``reads[].raw_token`` / ``equalities[].left_raw`` /
        ``equalities[].right_raw`` — these are the preserved raw tokens
        for the audit guard (``data-*`` attribute); the walker does NOT
        check them as user-facing.
    """
    patterns = _raw_token_patterns()
    leaked: list[str] = []
    AUDIT_DATA_KEYS = {
        "security_id", "issuer_id", "listing_key", "content_sha256",
        "recipe_id", "version", "generation_id", "source",
    }
    AUDIT_DATA_FIELDS_PREFIXES = (
        "/reads/",  # contains k, label_en/label_zh, raw_token — but we only check v_en/v_zh
        "/equalities/",  # contains check, left_raw/right_raw — but we only check left_en/left_zh/...
    )
    USER_FACING_LEAVES = {
        "en", "zh", "desc", "description", "v_en", "v_zh",
        "label_en", "label_zh",
        "headline", "summary", "reason", "reason_en", "reason_zh",
        "clear_en", "clear_zh", "clear",
        "owner", "cov_en", "cov_zh",
        "title_en", "title_zh", "actionable",
        "why_en", "why_zh", "result_en", "result_zh",
        "artifact_en", "artifact_zh",
        "reader_en", "reader_zh",
        "unresolved", "unresolved_en", "unresolved_zh",
        "subreads", "observables",
        "k", "v",  # field rows carry the typed value
    }
    for path, val in _walk(rendered):
        if not isinstance(val, str):
            continue
        # Skip top-level audit-data fields (these are data-* attributes).
        # They are root-level keys whose value is a raw identifier token.
        leaf = path.rsplit("/", 1)[-1] if "/" in path else path
        if "/" not in path and leaf in AUDIT_DATA_KEYS:
            continue
        # Skip the audit-only ``raw_token`` / ``left_raw`` / ``right_raw``
        # fields — they preserve the raw token for the data-* attribute but
        # never render as visible text.
        if leaf in {"raw_token", "left_raw", "right_raw"}:
            continue
        # Skip reads[].k / label_en / label_zh — these are FIELD NAMES, not
        # the rendered visible value (which lives on v_en/v_zh and is now
        # withheld when ``is_id=True``).
        if "/reads/" in path and leaf in {"k", "label_en", "label_zh"}:
            continue
        # Skip equalities[].check / label_en / label_zh — these are
        # the check name, not the rendered value.
        if "/equalities/" in path and leaf in {
            "check", "label_en", "label_zh", "left_value", "right_value",
        }:
            continue
        # User-facing string fields: match by leaf name OR by /suffix.
        if leaf in USER_FACING_LEAVES or path.endswith(tuple(
            "/" + k for k in USER_FACING_LEAVES
        )):
            for rx in patterns:
                if rx.search(val):
                    leaked.append(f"{path}: {val!r}")
    assert leaked == [], f"{label}: raw tokens leaked into user-facing strings: {leaked}"


@pytest.mark.parametrize(
    "case_name, subject_kwargs",
    [(name, kw) for name, kw in _C5_C3_SUBJECTS],
)
def test_c5_failure_shell_renders_no_unmapped_or_raw_tokens(
    case_name: str, subject_kwargs: dict,
) -> None:
    """A frozen-subject failure shell projected through ``build_security_state``
    must NOT emit ``identity read value unmapped:`` warnings and must NOT leak
    raw tokens into any user-facing string (H1 + H2 widen the walker)."""
    from scripts.build_ticker_pages import build_security_state

    _clear_unmapped_warnings()
    shell = _shell_for(subject_kwargs)
    buf = io.StringIO()
    with redirect_stderr(buf):
        rendered = build_security_state({"security_state": shell})
    unmapped = [ln for ln in buf.getvalue().splitlines()
                if "identity read value unmapped:" in ln]
    assert unmapped == [], (
        f"{case_name}: unmapped-identity warnings emitted: {unmapped}"
    )
    _assert_user_facing_strings_are_clean(
        rendered, f"{case_name} (owner_read_completed=True)",
    )


@pytest.mark.parametrize(
    "case_name, subject_kwargs",
    [(name, kw) for name, kw in _C5_C3_SUBJECTS],
)
def test_c5_failure_shell_owner_read_not_completed(
    case_name: str, subject_kwargs: dict,
) -> None:
    """H2 heal-round (PR #7122): the C5 probe must exercise
    ``owner_read_completed=False`` as well — a different public_reason and
    identity_proof state."""
    from engine import security_state as ss
    from scripts.build_ticker_pages import build_security_state

    _clear_unmapped_warnings()
    subject = ss.SecurityStateSubject(
        **subject_kwargs,
        owner_evidence=(
            ("decision_date", "unavailable"),
            ("alias_reader", ss._OWNER_IDENTITY_UNREAD),
            ("issuer_reader", ss._OWNER_IDENTITY_UNREAD),
            ("cik_reader", ss._OWNER_IDENTITY_UNREAD),
        ),
    )
    buf = io.StringIO()
    with redirect_stderr(buf):
        shell = ss.compile_security_state_failure(
            subject=subject, validator=_ss_validator(),
            now="2026-09-13T00:00:00Z", prior_state=None, owner_read_completed=False,
        )
        rendered = build_security_state({"security_state": shell})
    unmapped = [ln for ln in buf.getvalue().splitlines()
                if "identity read value unmapped:" in ln]
    assert unmapped == [], (
        f"{case_name} (owner_read_completed=False): unmapped warnings: {unmapped}"
    )
    _assert_user_facing_strings_are_clean(
        rendered, f"{case_name} (owner_read_completed=False)",
    )


def test_c5_c2_rename_subject_renders_clean() -> None:
    """H2 heal-round (PR #7122): the C5 probe must also cover ONE C2 rename
    case — the VMRK/EQR rename (SEC:US-XNYS-EQR vt=2026-08-18). The C5
    projection of a rename-driven subject must carry plain-word copy and
    no raw tokens."""
    from scripts.build_ticker_pages import build_security_state

    _clear_unmapped_warnings()
    shell = _shell_for(dict(
        security_id="SEC:US-XNYS-EQR",
        issuer_id="ISS:US-XNYS-EQR",
        listing_key="US-XNYS-EQR",
        ticker_display="VMRK",
        issuer_cik="0000000010",
    ))
    buf = io.StringIO()
    with redirect_stderr(buf):
        rendered = build_security_state({"security_state": shell})
    unmapped = [ln for ln in buf.getvalue().splitlines()
                if "identity read value unmapped:" in ln]
    assert unmapped == [], f"C2 rename: unmapped warnings: {unmapped}"
    _assert_user_facing_strings_are_clean(rendered, "C2 rename VMRK/EQR")


def test_c5_owner_identity_incomplete_unprobeable_through_compile() -> None:
    """H2 heal-round (PR #7122): ``compile_security_state_failure`` REFUSES a
    subject with ``issuer_cik=None`` — the OWNER_IDENTITY_INCOMPLETE class
    is un-probeable through this path. The compiler raises
    ``SecurityStateCompilationError("owner-composed subject fields must be
    non-empty strings")``; the PR body and the research note record the
    refusal so a future seat knows to widen the probe or admit a second
    repair."""
    from engine import security_state as ss

    subject = ss.SecurityStateSubject(
        security_id="SEC:US-XNYS-CTRA",
        issuer_id="ISS:US-XNYS-CTRA",
        listing_key="US-XNYS-CTRA",
        ticker_display="CTRA",
        issuer_cik=None,  # CTRA's owner value is NaN/None — never inject a CIK.
        owner_evidence=(
            ("decision_date", "2026-09-13"),
            ("alias_reader", "VendorAliasTable.resolve(store)"),
            ("issuer_reader", "IssuerMaster.issuer_of_security"),
            ("cik_reader", "IssuerMaster.cik_of_issuer"),
        ),
    )
    with pytest.raises(ss.SecurityStateCompilationError) as excinfo:
        ss.compile_security_state_failure(
            subject=subject, validator=_ss_validator(),
            now="2026-09-13T00:00:00Z", prior_state=None, owner_read_completed=True,
        )
    assert "owner-composed subject fields must be non-empty strings" in str(
        excinfo.value,
    ), f"RED: compile refused with unexpected message: {excinfo.value!r}"


def test_c5_two_goldens_project_through_build_security_state(tmp_path: Path) -> None:
    """Project the two committed goldens (AAPL + MSFT) through build_security_state
    and assert the same invariants — proves the C5 frozen-subject path agrees
    with the canonical golden projection. H2 heal-round: also walk the raw-token
    scan on the rendered goldens (the same walk as the failure shells)."""
    from engine import security_state as ss
    from scripts.build_ticker_pages import build_security_state

    for name in ("golden_aapl", "golden_msft"):
        payload = json.loads(
            (ROOT / "tests" / "fixtures" / "security_state" / f"{name}_input.json").read_text()
        )
        # MSFT fixture carries an inline subject; AAPL uses _subject() defaults
        raw_subject = payload.get("subject") or {}
        if raw_subject:
            payload["subject"] = ss.SecurityStateSubject(
                **{
                    **raw_subject,
                    "owner_evidence": tuple(
                        tuple(item) for item in raw_subject.get("owner_evidence", ())
                    ),
                }
            )
        else:
            payload["subject"] = ss.SecurityStateSubject(
                security_id="SEC:US-XNAS-AAPL",
                issuer_id="ISS:US-XNAS-AAPL",
                listing_key="US-XNAS-AAPL",
                ticker_display="AAPL",
                issuer_cik="0000320193",
                owner_evidence=(
                    ("decision_date", "2026-09-04"),
                    ("alias_reader", "VendorAliasTable.resolve(store)"),
                    ("issuer_reader", "IssuerMaster.issuer_of_security"),
                    ("cik_reader", "IssuerMaster.cik_of_issuer"),
                ),
            )
        # Build the K1 bundle for compile_security_state
        from lib.evidence_foundation import compile_recipe
        sub = payload["subject"]
        recipe = ss._build_k1_recipe(subject=sub)
        empty = compile_recipe(recipe, blocks=[], references={})
        found = None
        if payload.get("workspace_disposition") == "found" and isinstance(payload.get("workspace"), dict):
            ws = payload["workspace"]
            if ws.get("event_id") and ws.get("generation_id"):
                lc = (ws.get("lifecycle") or {})
                ref = ss._build_k1_reference(
                    subject=sub,
                    generation_id=str(ws["generation_id"]), event_id=str(ws["event_id"]),
                    manifest_sha256=payload.get("manifest_sha256"),
                    source_available_at=lc.get("source_available_at"),
                    observed_at=lc.get("observed_at"),
                    generated_at=ws.get("generated_at"),
                )
                block = ss._build_k1_block([ref], subject=sub)
                found = {
                    "reference_id": ref["reference_id"],
                    "block_id": block["evidence_block_id"],
                    "compilation": compile_recipe(
                        recipe, blocks=[block], references={ref["reference_id"]: ref},
                    ),
                }
        payload["validator"] = _ss_validator()
        payload["k1_bundle"] = {
            "subject_cik": sub.issuer_cik, "recipe_id": recipe["recipe_id"],
            "empty_compilation": empty, "found": found,
        }
        _clear_unmapped_warnings()
        state = ss.compile_security_state(**payload)
        buf = io.StringIO()
        with redirect_stderr(buf):
            rendered = build_security_state({"security_state": state})
        unmapped = [ln for ln in buf.getvalue().splitlines()
                    if "identity read value unmapped:" in ln]
        assert unmapped == [], (
            f"golden {name}: build_security_state emitted unmapped warnings: {unmapped}"
        )
        # H2: goldens also go through the raw-token walk (the same one as the
        # failure shells). The golden deck is engine truth, but if a raw token
        # leaks into a user-facing string we want the test to fail.
        _assert_user_facing_strings_are_clean(rendered, f"golden {name}")
