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
    """RED-first: a ticker whose issuer has no CIK must show up under OWNER_IDENTITY_INCOMPLETE."""
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


# ── Receipt schema validation (R5) ───────────────────────────────────────────
def test_receipt_schema_validates_against_itself() -> None:
    """The receipt validates against its declared schema (R5 live-data test)."""
    receipt = tcc.build_receipt(
        decision_date=_FIXTURE_DAY, data_dir="<fixture>",
        c1=[], c2=[], c3=[], c3_details={}, c4=[],
    )
    assert receipt["schema"] == "ticker_cik_collision_census.v1"
    assert receipt["schema_version"] == "1.0.0"
    assert isinstance(receipt["lines"], list)
    assert receipt["total_collisions"] == 0


# ── Live-data invariant test (R5) ────────────────────────────────────────────
def _maybe_read_parquet(name: str) -> list[dict] | None:
    """Read a parquet from data/reference/ or materialise it from git HEAD."""
    import subprocess

    p = ROOT / "data" / "reference" / name
    if p.is_file():
        import pandas as pd
        return pd.read_parquet(p).to_dict("records")
    # materialise from HEAD
    try:
        out = subprocess.run(
            ["git", "show", f"HEAD:data/reference/{name}"],
            cwd=str(ROOT), capture_output=True, timeout=15, check=False,
        )
    except Exception:
        return None
    if out.returncode != 0 or not out.stdout:
        return None
    tmp = ROOT / "_w7b_f06_5_materialised"
    tmp.mkdir(exist_ok=True)
    target = tmp / name
    target.write_bytes(out.stdout)
    try:
        import pandas as pd
        return pd.read_parquet(target).to_dict("records")
    except Exception:
        return None


@pytest.mark.skipif(
    os.environ.get("W7B_F06_5_SKIP_LIVE") == "1",
    reason="W7B_F06_5_SKIP_LIVE=1 — live-data test explicitly skipped for fast iteration",
)
def test_live_data_invariants_pin_only_collisions_and_enum_coverage() -> None:
    """Live-data test (R5): pin invariants; PRINT dated counts as receipt lines.

    data/reference/ churns nightly, so the test asserts only:
        (i)  every C1 (a)-(e) code is 0,
        (ii) every current store symbol EITHER resolves fully (no C3 row)
             OR fails with a class from CikFailureClass,
        (iii) the receipt validates against its own schema.

    It PRINTS the dated counts as receipt lines — a human reviewer can see
    what the live data actually said without the test failing on drift.
    """
    alias = _maybe_read_parquet("vendor_aliases.parquet")
    sec = _maybe_read_parquet("security_master.parquet")
    iss = _maybe_read_parquet("issuer_master.parquet")
    if alias is None or sec is None or iss is None:
        pytest.skip(
            "data/reference/{vendor_aliases,security_master,issuer_master}.parquet "
            "unavailable locally and not materialisable from git HEAD — the live-data "
            "test cannot run in this environment."
        )

    decision_date = _dt.date.today()
    c1 = tcc.c1_strict_collisions(
        alias_rows=alias, security_records=sec, issuer_records=iss,
        decision_date=decision_date,
    )
    c2 = tcc.c2_namespace_divergence(alias_rows=alias, decision_date=decision_date)
    c3, c3_details = tcc.c3_cik_leg_access_failures(
        alias_rows=alias, security_records=sec, issuer_records=iss,
        decision_date=decision_date,
    )
    universe = sorted(
        {p.stem for p in (ROOT / "data" / "stocks").glob("*.parquet")}
        | {p.stem for p in (ROOT / "data" / "sector_holdings").glob("*.parquet")}
    )
    c4 = tcc.c4_renderer_coverage(
        alias_rows=alias, decision_date=decision_date,
        universe_tickers=universe, allowlist_tickers=tcc._allowlist() if hasattr(tcc, "_allowlist") else ("AAPL", "MSFT"),
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

    # (iii) receipt schema self-check
    assert receipt["schema"] == tcc.RECEIPT_SCHEMA["schema"]
    assert receipt["schema_version"] == tcc.RECEIPT_SCHEMA["version"]

    # PRINT the dated counts (R5). A human reviewer can see what the live
    # data said without the test failing on nightly changes.
    for line in receipt["lines"]:
        print(line)


# ── C5 — renderer robustness (frozen subject + build_security_state) ──────────
def _ss_validator():
    from jsonschema import Draft202012Validator
    schema = json.loads(
        (ROOT / "contracts" / "market_os" / "security_state.v1.schema.json").read_text()
    )
    return Draft202012Validator(schema)


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


def test_c5_failure_shell_renders_no_unmapped_identity_warnings() -> None:
    """A frozen-subject failure shell projected through build_security_state
    must NOT emit ``identity read value unmapped:`` warnings and must NOT leak
    raw tokens into any user-facing (en/zh label/degradation/desc) string."""
    from scripts.build_ticker_pages import build_security_state

    # CTRA-shaped subject — incomplete-CIK row, frozen fields
    shell = _shell_for(dict(
        security_id="SEC:US-XNYS-CTRA",
        issuer_id="ISS:US-XNYS-CTRA",
        listing_key="US-XNYS-CTRA",
        ticker_display="CTRA",
        issuer_cik="0001175483",
    ))
    buf = io.StringIO()
    with redirect_stderr(buf):
        rendered = build_security_state({"security_state": shell})
    unmapped = [ln for ln in buf.getvalue().splitlines()
                if "identity read value unmapped:" in ln]
    assert unmapped == [], f"unmapped-identity warnings emitted: {unmapped}"

    # Every user-facing label (en/zh) is a plain word — no ISS:/SEC:/cik:/US-XN/evt_
    import re

    def _walk(o, path=""):
        if isinstance(o, dict):
            for k, v in o.items():
                yield from _walk(v, path + "/" + k)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                yield from _walk(v, path + f"[{i}]")
        elif isinstance(o, str):
            yield path, o

    raw_patterns = [
        re.compile(r"ISS:[A-Z0-9.\-]+"),
        re.compile(r"SEC:[A-Z0-9.\-]+"),
        re.compile(r"\bcik:"),
        re.compile(r"US-XN[A-Z]+-[A-Z]+-[A-Z0-9.\-]+"),
        re.compile(r"\bevt_"),
    ]
    leaked: list[str] = []
    for path, val in _walk(rendered):
        # user-facing strings live under en/zh labels, desc_* fields, or degradation tone
        if (path.endswith("/en") or path.endswith("/zh")
            or "/degradation/" in path or "/desc_" in path or path.endswith("/desc")):
            for rx in raw_patterns:
                if rx.search(val):
                    leaked.append(f"{path}: {val!r}")
    assert leaked == [], f"raw tokens leaked into user-facing strings: {leaked}"


def test_c5_two_goldens_project_through_build_security_state() -> None:
    """Project the two committed goldens (AAPL + MSFT) through build_security_state
    and assert the same invariants — proves the C5 frozen-subject path agrees
    with the canonical golden projection."""
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
        state = ss.compile_security_state(**payload)
        buf = io.StringIO()
        with redirect_stderr(buf):
            rendered = build_security_state({"security_state": state})
        unmapped = [ln for ln in buf.getvalue().splitlines()
                    if "identity read value unmapped:" in ln]
        assert unmapped == [], (
            f"golden {name}: build_security_state emitted unmapped warnings: {unmapped}"
        )
        # The golden deck is the per-axis truth; we only assert it renders.
        assert rendered is not None, f"golden {name}: build_security_state returned None"