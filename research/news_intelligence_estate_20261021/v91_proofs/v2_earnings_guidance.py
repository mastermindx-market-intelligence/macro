#!/usr/bin/env python3
"""V91 §9.1 vertical proof V2: earnings and guidance.

MASTERPLAN research/news_intelligence_estate_20261021/MASTERPLAN.md, section 9.1,
row "Earnings/guidance": "Issuer/listing identity, fiscal period and basis match;
actual/expected/prior guide separated; source correction invalidates derivatives",
consumer outcome "Ticker and catalyst assessment explain the real change and what
remains unknown".

Offline and deterministic. Inputs are the committed earnings fixtures under
tests/fixtures (a synthetic CIK 1234567 release and its tampered amendment, the
P&G and Apple company-intelligence exhibits) plus synthetic news_impact events and
short synthetic release paragraphs written below. The expected roles come from
those sentences, never from producer output. The proof calls the repository
producers (news_impact.issuer.resolve_mention, earnings_release binding and
figures, event_workspace_build.build_event_workspace, news_impact validate_event,
producer_facts.run, thesis.quantity_fingerprint, prophet_adapter.format_amount,
app.company_intelligence._public_workspace_glance) and prints what it observed.
Standard library plus repository modules only; no network, no model call, no
wall clock, and every file it writes lives under --scratch. Run from anywhere:

    python3 research/news_intelligence_estate_20261021/v91_proofs/v2_earnings_guidance.py \
        --scratch /tmp/any-dir

Output is exactly one line per property P1..P6 then one SUMMARY line; the sibling
.expected file pins the verdicts. A verdict is PROVEN only when every named check
holds, ABSENT when none does, PARTIAL otherwise; each line names the checks that
did not hold. Evidence cites producer and test locations computed from the
current source, so they track line drift.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import inspect
import json
import sys
import tempfile
from collections import Counter
from datetime import date
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.company_intelligence import _public_workspace_glance  # noqa: E402
from engine.company_intelligence import event_workspace as EW  # noqa: E402
from engine.company_intelligence.event_workspace import WorkspaceError  # noqa: E402
from engine.company_intelligence.event_workspace_build import build_event_workspace  # noqa: E402
from engine.company_intelligence.identity import (  # noqa: E402
    IssuerIdentity,
    IssuerRegistry,
    ListingAlias,
)
from engine.company_intelligence.pg_profile import pg_private_registry, pg_profile  # noqa: E402
from engine.earnings_release import binding as B  # noqa: E402
from engine.earnings_release import figures as FIG  # noqa: E402
from engine.fundamental_forensics.disclosure_diff import normalize_filing  # noqa: E402
from engine.news_impact import cluster as CL  # noqa: E402
from engine.news_impact import issuer as ISS  # noqa: E402
from engine.news_impact import producer_facts as pf  # noqa: E402
from engine.news_impact import prophet_adapter as PA  # noqa: E402
from engine.news_impact import thesis as TH  # noqa: E402
from engine.news_impact.validate import validate_event  # noqa: E402
from tests import earnings_economic_fixtures as EF  # noqa: E402

# No committed data artifact is needed: every input is a tracked test fixture or inline.
REQUIRED_ARTIFACTS = ()

CONTRACT = "contracts/news_impact/news_impact_event.v1.schema.json"
RELEASE_FIXTURES = ROOT / "tests" / "fixtures" / "earnings_release"
CI_FIXTURES = ROOT / "tests" / "fixtures" / "company_intelligence"

# ------------------------------------------------------------ source texts ----
# Earnings release paragraphs. Only NEW is the company's own forward guide; the
# consensus sentence is analysts' expectation and the prior clause is the old guide.
NEW_GUIDE = "For the first quarter 2027, the company expects non-GAAP EPS of $1.94 to $2.11."
CONSENSUS = "Analysts expect non-GAAP EPS of $2.40 to $2.50 for the first quarter 2027."
PRIOR_CLAUSE = ("Up from its prior outlook of $1.80 to $1.95, the company now expects "
                "non-GAAP EPS of $1.94 to $2.11 for the first quarter 2027.")
# A results table header, and a quarter and a twelve-month table that end on the
# same date: 8,412 is the quarter, 31,020 is the year.
TABLE_HEADER = ("<div>CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS (Unaudited)</div>"
                "<div>(In millions, except per share amounts)</div>")
QUARTER, YEAR = "8,412", "31,020"
# news_impact guidance statements (synthetic issuer, synthetic filing id).
GUIDE = "The company raised its full-year revenue outlook to USD 900 million."
GUIDE_REWORDED = "The company lifted its full-year revenue outlook to USD 900 million."
PRIOR = "The prior full-year revenue outlook was USD 800 million."
CORRECTION = "The company corrected its full-year revenue outlook to USD 850 million."

ISSUER = "cik:0000999201"
DOC = "sec:0000000000-26-000201:synth_v2.htm"
FLAGS = {"may_rank": False, "may_size": False, "may_gate": False, "prophet_authority": False}
FY27 = {"year": 2027, "quarter": None, "calendar_end": None, "period_kind": "fiscal_year"}
Q1_27 = {"year": 2027, "quarter": 1, "calendar_end": None, "period_kind": "quarter"}
Q3_27 = {"year": 2027, "quarter": 3, "calendar_end": None, "period_kind": "quarter"}
SOURCE_SHA = sha256(b"v91-v2-synthetic-source").hexdigest()

# Release binding fixture identity (tests/test_earnings_release_binding.py).
REL_CIK = 1234567
REL_ACCESSION = "0001234567-26-000012"
REL_AMENDMENT = "0001234567-26-000031"
REL_REPORT_DATE = "2026-01-28"


# ------------------------------------------------------------- citations ----
def _rel(path) -> str:
    return Path(path).resolve().relative_to(ROOT).as_posix()


def at_def(obj) -> str:
    _, line = inspect.getsourcelines(obj)
    return f"{_rel(inspect.getsourcefile(obj))}:{line}"


def at_text(rel: str, needle: str) -> str:
    text = (ROOT / rel).read_text(encoding="utf-8")
    for n, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return f"{rel}:{n}"
    raise LookupError(f"{needle!r} not found in {rel}")


def at_test(rel: str, name: str) -> str:
    return at_text(rel, f"def {name}(")


T_ISSUER = "tests/test_news_impact_issuer.py"
T_BINDING = "tests/test_earnings_release_binding.py"
T_FACTS = "tests/test_news_impact_producer_facts.py"
T_WORKSPACE = "tests/test_company_intelligence_event_workspace.py"


# -------------------------------------------------------------- verdicts ----
def judge(checks: list[tuple[str, bool]]) -> tuple[str, str]:
    held = [name for name, ok in checks if ok]
    missing = [name for name, ok in checks if not ok]
    if not missing:
        verdict = "PROVEN"
    elif not held:
        verdict = "ABSENT"
    else:
        verdict = "PARTIAL"
    text = f"held={len(held)}/{len(checks)}"
    if missing:
        text += " missing=" + ",".join(missing)
    return verdict, text


def emit(k: int, checks: list[tuple[str, bool]], observed: str, cites: list[str]) -> str:
    verdict, tally = judge(checks)
    print(f"V2 P{k} {verdict} {tally}; observed {observed}; " + " ".join(cites))
    return verdict


# ------------------------------------------------- news_impact T2 events ----
def _span(text: str) -> dict:
    n = len(text.encode())
    digest = sha256(text.encode()).hexdigest()
    return {
        "schema": "source_span.v1",
        "authority": "context_only",
        "span_id": "span_" + sha256((DOC + text).encode()).hexdigest()[:20],
        "document_id": DOC,
        "document_version": 1,
        "locator": {"kind": "text_span", "sub_kind": "transcript_segment",
                    "segment_index": 0, "span_start_byte": 0, "span_end_byte": n},
        "text_sha256": digest,
        "display_excerpt": text,
        "rights_profile": "rp_unknown_v1",
        "receipt_state": "byte_replayed",
        "receipt": {"source_sha256": SOURCE_SHA, "segment_index": 0,
                    "segment_sha256": SOURCE_SHA, "segment_bytes": 200,
                    "span_start_byte": 0, "span_end_byte": n, "text_sha256": digest},
        "unreplayable_reason": None,
    }


def _evidence(text: str) -> dict:
    return {"claimed_quote": text, "span": _span(text)}


def _absence(subject: str) -> dict:
    return {"schema": "field_absence.v1", "authority": "context_only",
            "reason": "not_stated", "subject": subject, "detail": "",
            "missing_fields": [subject]}


def _qpoint(value, basis: str, text: str, period: dict = FY27, unit: str = "USD") -> dict:
    return {"form": "point", "value": value, "bound": "exact", "unit": unit,
            "currency": "USD", "basis": basis, "period": dict(period),
            "negated": False, "evidence": _evidence(text)}


def _t2(seed: str = "v2_guide", day: int = 1, **overrides) -> dict:
    stamp = f"2026-10-{day:02d}T12:00:00Z"
    event = {
        "schema": pf.T2,
        "authority": "context_only",
        "prophet_flags": dict(FLAGS),
        "unsolicited_instruction_detected": False,
        "fact_id": "fact_" + sha256(seed.encode()).hexdigest()[:24],
        "document_id": DOC,
        "observed_at": stamp,
        "source_available_at": stamp,
        "supersedes_fact_id": None,
        "company_id": ISSUER,
        "issuer_role": "subject",
        "novelty": "new_magnitude_timing_commitment_counterparty",
        "negated": False,
        "demand_stage": "guidance",
        "metric": "revenue",
        "commitment_status": "announced",
        "stated_amount": _qpoint(900_000_000, "total", GUIDE),
        "fiscal_period": dict(FY27),
        "revision_direction": "raised",
        "counterparty_company_id": _absence("counterparty_company_id"),
        "baseline": {
            "type": "UNKNOWN",
            "timestamp": _absence("baseline_timestamp"),
            "contributors": _absence("baseline_contributors"),
            "coverage": _absence("baseline_coverage"),
            "period": _absence("baseline_period"),
            "basis": _absence("baseline_basis"),
            "age_days": _absence("baseline_age_days"),
        },
    }
    event.update(overrides)
    return event


def _valid(event: dict) -> bool:
    return validate_event(event).ok


def _codes(event: dict) -> str:
    issues = validate_event(event).issues
    return "+".join(sorted({f"{i.code}@{i.path}" for i in issues})) or "none"


def _leaf(event: dict) -> dict:
    return pf.leaf_payload(event, pf.fact_slot(event), Counter())


def _fingerprint(event: dict) -> str:
    return TH.quantity_fingerprint(_leaf(event), pf.T2)["canonical_sha256"]


def _run_facts(scratch: Path, name: str, events: list[dict]):
    rows = [{"case_id": f"{name}_{i}", "shadow": False,
             "novelty_source": "label_provisional", "event": ev}
            for i, ev in enumerate(events, 1)]
    path = scratch / f"{name}_events.jsonl"
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows),
                    encoding="utf-8")
    out = scratch / name
    pf.run([path], out, None)
    log = json.loads((out / "fact_log.json").read_text(encoding="utf-8"))
    views = [json.loads(line) for line in
             (out / "thesis_views.jsonl").read_text(encoding="utf-8").splitlines() if line]
    return {rec["fact_id"]: rec for rec in log["records"]}, views


# ------------------------------------------------ release figure helpers ----
def _figures(body: str):
    doc = normalize_filing({"accession": "0000999201-26-000001", "entity_cik": "999201",
                            "form": "8-K", "content": body})
    return FIG.extract_release_figures(doc)


def _paragraphs(*paras: str):
    return _figures("<html><body>" + "".join(f"<p>{p}</p>" for p in paras) + "</body></html>")


def _guide_values(result) -> dict:
    return {(f.concept, f.basis): f.value for f in result.figures
            if f.concept.startswith("guidance_")}


def _table(prefix: str, value: str) -> str:
    return (f"<table><tr><td>{prefix}</td></tr>"
            "<tr><td></td><td>December 28, 2025</td></tr>"
            f"<tr><td>Total net sales</td><td>$</td><td>{value}</td></tr></table>")


def _bind(body: str, accession: str = REL_ACCESSION, form: str = "8-K",
          filing_date: str = "2026-01-29", acceptance: str = "2026-01-29T21:07:14Z"):
    return B.bind_release_document(cik=REL_CIK, accession=accession, form=form,
                                   filing_date=filing_date, acceptance_datetime=acceptance,
                                   report_date=REL_REPORT_DATE, body=body)


def _release_body(name: str) -> str:
    return (RELEASE_FIXTURES / name).read_text(encoding="utf-8")


# --------------------------------------------- company workspace helpers ----
def _pg_workspace(body: str | None = None, *, filing_cik: str | None = None,
                  prior_sha: str | None = None, prior_state: str | None = None) -> dict:
    filing = dict(EF._filing())
    if filing_cik is not None:
        filing["cik"] = filing_cik
    return build_event_workspace(
        registry=pg_private_registry(), ticker="PG", asof=date(2026, 7, 29),
        fiscal_period=EF.FISCAL_PERIOD,
        exhibit_body=body if body is not None else EF.pg_bound_case("annual_first").source,
        filing=filing, transcript=None, observed_at="2026-07-29T17:01:00Z",
        source_available_at=EF.ACCEPTANCE, prior_source_sha256=prior_sha,
        prior_lifecycle_state=prior_state, profile=pg_profile(fiscal_scope=EF.FISCAL_SCOPE))


def _aapl_workspace(body: str | None = None, prior_sha: str | None = None) -> dict:
    raw = gzip.decompress((CI_FIXTURES / "aapl_fy2026_q3.json.gz").read_bytes())
    exhibit = (CI_FIXTURES / "aapl_fy2026_q3_ex99_1.htm").read_text(encoding="utf-8")
    filing = json.loads((CI_FIXTURES / "aapl_fy2026_q3_filing.json").read_text(encoding="utf-8"))
    collector = json.loads(
        (CI_FIXTURES / "aapl_edgar_8k_collector_legacy.json").read_text(encoding="utf-8"))
    return build_event_workspace(
        registry=EW.apple_registry(), ticker="AAPL", asof=EW.AAPL_CALL_DATE,
        fiscal_period=EW.flagship_fiscal_period(),
        exhibit_body=body if body is not None else exhibit, filing=filing,
        transcript=json.loads(raw.decode("utf-8")), transcript_sha256=sha256(raw).hexdigest(),
        observed_at="2026-08-16T18:00:00Z", source_available_at="2026-07-30T16:30:00Z",
        collector_rows=[collector], wire_record_found=False, prior_source_sha256=prior_sha)


def _eps(ws: dict) -> list:
    return [f.get("value") for f in ws["facts"] if f.get("metric") == "pg_diluted_eps"]


def _signature(ws: dict) -> str:
    """What a reader is told about the build: event, issuer, state and warnings.

    The completeness block echoes the filing key back verbatim, so it is left out:
    recording the foreign CIK there is not a refusal or a warning.
    """
    return json.dumps([ws["event_id"], ws["issuer"].get("company_id"),
                       ws["lifecycle"]["state"], ws["warnings"]], sort_keys=True, default=str)


# ------------------------------------------------------------- properties ----
ASOF = date(2026, 10, 11)


def _alias(ticker: str) -> ListingAlias:
    return ListingAlias(ticker=ticker, mic="XNAS", share_class="A", trading_currency="USD",
                        is_primary=True, valid_from=date(2020, 1, 1), valid_to=None)


SYNW = IssuerIdentity(company_id="cik:0000000901", display_name="Synthwave Instruments Inc",
                      fiscal_year_end_month=12, reporting_currency="USD",
                      listings=(_alias("SYNW"),))
OTHM = IssuerIdentity(company_id="cik:0000000902", display_name="Othermark Holdings Inc",
                      fiscal_year_end_month=12, reporting_currency="USD",
                      listings=(_alias("OTHM"),))


def _mention(**fields) -> ISS.Mention:
    base = {"text": "", "ticker": None, "cik": None, "exchange_mic": None, "asof": ASOF}
    base.update(fields)
    return ISS.Mention(**base)


def _resolution(result) -> tuple:
    note = (result.receipt.get("rungs") or [{}])[-1].get("note")
    return (result.company_id, result.rung, result.absence_reason,
            tuple(result.candidates), note)


def p1_identity(scratch: Path) -> str:
    """Issuer/listing identity: resolve or refuse, and surface a listing conflict."""
    registry = IssuerRegistry([SYNW, OTHM])

    def resolve(**fields):
        return ISS.resolve_mention(_mention(**fields), registry=registry)

    by_cik = resolve(text="Synthwave reports results", cik="0000000901")
    by_ticker = resolve(text="$SYNW", ticker="SYNW")
    malformed = resolve(cik="12x")
    unknown = resolve(ticker="ZZZZ")
    name_only = resolve(text="Synthwave Instruments said")
    dual = ISS.resolve_mention(
        _mention(ticker="DUAL"), registry=registry,
        ledger={"DUAL": (("cik:0000000901", None, None), ("cik:0000000902", None, None))})
    matching = resolve(cik="0000000901", ticker="SYNW")
    conflict = resolve(cik="0000000901", ticker="OTHM")

    own = _pg_workspace(filing_cik=EF.CIK)
    try:
        foreign = _pg_workspace(filing_cik="0000000902")
        foreign_refused = False
        recorded = sorted({str((s.get("filing_key") or {}).get("cik"))
                           for s in foreign["sources"] if isinstance(s.get("filing_key"), dict)})
        foreign_text = (f"foreign filing cik recorded as {recorded} under issuer "
                        f"{foreign['issuer'].get('company_id')} state "
                        f"{foreign['lifecycle']['state']}")
        foreign_same = _signature(foreign) == _signature(own)
    except WorkspaceError as exc:  # the builder's typed refusal is the desired behaviour
        foreign_refused, foreign_same = True, False
        foreign_text = f"foreign filing cik refused {type(exc).__name__}"

    checks = [
        ("explicit_cik_resolves", by_cik.company_id == "cik:0000000901"),
        ("listed_ticker_resolves", by_ticker.company_id == "cik:0000000901"),
        ("malformed_cik_terminal",
         malformed.company_id is None and malformed.absence_reason == "malformed_identifier"),
        ("unknown_ticker_typed",
         unknown.company_id is None and unknown.absence_reason == "unknown_ticker"),
        ("name_only_typed",
         name_only.company_id is None and name_only.absence_reason == "name_only_mention"),
        ("ambiguous_ticker_lists_both",
         dual.company_id is None
         and sorted(dual.candidates) == ["cik:0000000901", "cik:0000000902"]),
        ("cik_listing_conflict_surfaced", _resolution(conflict) != _resolution(matching)),
        ("foreign_filing_cik_refused_or_warned", foreign_refused or not foreign_same),
    ]
    observed = (f"cik+OTHM resolves {conflict.company_id} via {conflict.rung} note "
                f"{_resolution(conflict)[4]!r} identical to cik+SYNW; PG workspace with "
                f"{foreign_text}, event/issuer/state/warnings identical to own-cik build")
    if foreign_refused or not foreign_same:
        observed = (f"cik+OTHM resolves {conflict.company_id} via {conflict.rung}; "
                    f"{foreign_text}")
    return emit(1, checks, observed, [
        at_def(ISS.resolve_mention),
        at_text("engine/company_intelligence/event_workspace_build.py",
                'cik = str(filing.get("cik")'),
        at_test(T_ISSUER, "test_explicit_cik_wins_over_conflicting_ticker"),
        at_test(T_ISSUER, "test_ambiguous_ticker_lists_every_candidate"),
    ])


def p2_period_basis(scratch: Path) -> str:
    """Fiscal period and basis bound deterministically on every figure."""
    fs = _bind(_release_body("ex99_1_release.htm")).figures
    actual = [f for f in fs.figures if not f.concept.startswith("guidance_")]
    guide = [f for f in fs.figures if f.concept.startswith("guidance_")]
    by_key = {(f.concept, f.basis): f.value for f in fs.figures}
    absent = {a.concept: a.reason for a in fs.absences}
    actual_labels = {f.period_label for f in actual}

    quarter_only = _figures("<html><body>" + TABLE_HEADER + _table("Three Months Ended", QUARTER)
                            + "</body></html>")
    both = _figures("<html><body>" + TABLE_HEADER + _table("Three Months Ended", QUARTER)
                    + TABLE_HEADER + _table("Twelve Months Ended", YEAR) + "</body></html>")
    q_values = sorted(f.value for f in quarter_only.figures if f.concept == "revenue")
    both_values = sorted(f.value for f in both.figures if f.concept == "revenue")
    both_reason = {a.concept: a.reason for a in both.absences}.get("revenue")

    fy_event = _t2()
    q_event = _t2(fiscal_period=dict(Q1_27),
                  stated_amount=_qpoint(225_000_000, "total", GUIDE, period=Q1_27))

    checks = [
        ("figures_carry_basis_units_period",
         bool(fs.figures) and all(f.basis and f.units and f.period_label for f in fs.figures)),
        ("gaap_and_non_gaap_eps_separate",
         by_key.get(("eps_diluted", "gaap")) is not None
         and by_key.get(("eps_diluted", "non_gaap")) is not None
         and by_key[("eps_diluted", "gaap")] != by_key[("eps_diluted", "non_gaap")]),
        ("actuals_share_one_period_end",
         len(actual) > 1 and len({f.period_end for f in actual}) == 1),
        ("guidance_period_distinct_from_actuals",
         bool(guide) and all(f.period_label and f.period_label not in actual_labels
                             for f in guide)),
        ("undeclared_guidance_basis_is_absent",
         absent.get("guidance_revenue_low") == "basis_undeclared"),
        ("fiscal_year_and_quarter_slots_differ",
         _valid(fy_event) and _valid(q_event) and pf.fact_slot(fy_event) != pf.fact_slot(q_event)),
        ("quarter_table_alone_binds", q_values == [8412.0]),
        ("quarter_and_year_same_end_both_bind", both_values == [8412.0, 31020.0]),
    ]
    observed = (f"eps_diluted gaap {by_key.get(('eps_diluted', 'gaap'))} non_gaap "
                f"{by_key.get(('eps_diluted', 'non_gaap'))} one period_end "
                f"{sorted({f.period_end for f in actual})}; guidance label "
                f"{sorted({f.period_label for f in guide})}; 3m+12m tables ending the same "
                f"day give revenue {both_values} reason {both_reason}")
    return emit(2, checks, observed, [
        at_def(FIG.extract_release_figures),
        at_def(FIG._resolve_restatements),
        at_def(pf.fact_slot),
        at_test(T_BINDING, "test_every_bound_figure_carries_basis_units_period_and_source"),
        at_test(T_BINDING, "test_two_rows_disagreeing_on_one_concept_drop_both"),
    ])


def p3_output_basis(scratch: Path) -> str:
    """Model-output basis: the contract refuses a basis or period that cannot be the claim."""
    base = _t2()
    revenue_bases = {}
    for basis in ("per_share", "run_rate", "incremental", "percent"):
        ev = copy.deepcopy(base)
        ev["stated_amount"]["basis"] = basis
        revenue_bases[basis] = _valid(ev)
    eps_total = _t2(metric="eps", stated_amount=_qpoint(2.18, "total", GUIDE))

    q_event = _t2(fiscal_period=dict(Q1_27),
                  stated_amount=_qpoint(900_000_000, "total", GUIDE, period=Q1_27))
    basis_leaf = copy.deepcopy(base)
    basis_leaf["stated_amount"]["basis"] = "per_share"
    reworded = copy.deepcopy(base)
    reworded["stated_amount"]["evidence"] = _evidence(GUIDE_REWORDED)
    mismatch = copy.deepcopy(base)
    mismatch["stated_amount"]["period"] = dict(Q3_27)

    eps = {"form": "point", "value": 2.18, "unit": "USD/share", "currency": "USD",
           "basis": "per_share", "bound": "exact"}
    en, zh = PA.format_amount(eps, "en"), PA.format_amount(eps, "zh")

    checks = [
        ("base_t2_valid", _valid(base)),
        ("revenue_non_total_basis_refused", not any(revenue_bases.values())),
        ("eps_total_basis_refused", not _valid(eps_total)),
        ("fingerprint_tracks_period",
         _valid(q_event) and _fingerprint(q_event) != _fingerprint(base)),
        ("fingerprint_tracks_basis", _fingerprint(basis_leaf) != _fingerprint(base)),
        ("fingerprint_ignores_wording", _fingerprint(reworded) == _fingerprint(base)),
        ("claim_period_mismatch_refused", not _valid(mismatch)),
        ("per_share_amount_keeps_cents", "2.18" in en and "2.18" in zh),
    ]
    observed = (f"FY27 claim with a Q3 2027 stated_amount validates={_valid(mismatch)} "
                f"({_codes(mismatch)}); EPS 2.18 per_share renders en={ascii(en)} "
                f"zh={ascii(zh)}")
    return emit(3, checks, observed, [
        at_def(validate_event),
        at_def(TH.quantity_fingerprint),
        at_def(PA.format_amount),
        at_def(PA._one_decimal),
        at_test(T_FACTS, "test_fingerprint_moves_when_a_meaning_term_changes"),
        at_test(T_FACTS, "test_fingerprint_ignores_evidence_and_basis_whitespace"),
    ])


def _resolve_ref(schema: dict, node: dict) -> dict:
    while isinstance(node, dict) and "$ref" in node:
        name = node["$ref"].split("/")[-1]
        node = schema["$defs"][name]
    return node


def p4_actual_expected_prior(scratch: Path) -> str:
    """Actual, expected (consensus) and prior guide are separate roles end to end."""
    fs = _bind(_release_body("ex99_1_release.htm")).figures
    actual_concepts = {f.concept for f in fs.figures if not f.concept.startswith("guidance_")}
    guide_concepts = {f.concept for f in fs.figures if f.concept.startswith("guidance_")}

    new_only = _guide_values(_paragraphs(NEW_GUIDE))
    with_consensus = _guide_values(_paragraphs(CONSENSUS, NEW_GUIDE))
    with_prior = _guide_values(_paragraphs(PRIOR_CLAUSE))
    low = ("guidance_eps_low", "non_gaap")
    high = ("guidance_eps_high", "non_gaap")

    schema = json.loads((ROOT / CONTRACT).read_text(encoding="utf-8"))
    t2_props = schema["$defs"][pf.T2]["properties"]
    baseline_props = _resolve_ref(schema, t2_props["baseline"]).get("properties", {})
    baseline_types = set(_resolve_ref(schema, baseline_props.get("type", {})).get("enum", []))

    with_prior_amount = _t2(prior_amount=_qpoint(800_000_000, "total", PRIOR))
    prior_typed = _t2()
    prior_typed["baseline"]["type"] = "prior_company_guidance_or_contract"
    leaf = _leaf(with_prior_amount)

    checks = [
        ("actuals_and_guidance_separate_concepts",
         bool(actual_concepts) and bool(guide_concepts)
         and not (actual_concepts & guide_concepts)),
        ("company_guide_binds", new_only.get(low) == 1.94 and new_only.get(high) == 2.11),
        ("consensus_not_bound_as_guide", with_consensus.get(low) == 1.94),
        ("prior_guide_not_bound_as_new", with_prior.get(low) == 1.94),
        ("t2_contract_carries_prior_amount",
         "prior_amount" in t2_props and _valid(with_prior_amount)),
        ("baseline_type_separates_consensus_and_prior_guide",
         {"licensed_consensus_period_basis_matched",
          "prior_company_guidance_or_contract"} <= baseline_types and _valid(prior_typed)),
        ("baseline_carries_value", "value" in baseline_props),
        ("leaf_keeps_prior_amount", "prior_amount" in json.dumps(leaf, sort_keys=True)),
        ("reader_template_names_prior",
         "prior_amount_plain" in PA.TEMPLATE_SLOT_KEYS.get("T2_guidance", ())),
    ]
    observed = (f"consensus sentence first binds guide low/high "
                f"{with_consensus.get(low)}/{with_consensus.get(high)}; prior-outlook clause "
                f"binds {with_prior.get(low)}/{with_prior.get(high)}; baseline properties "
                f"{sorted(baseline_props)} have no value; leaf keys {sorted(leaf)}; "
                f"T2_guidance slots {list(PA.TEMPLATE_SLOT_KEYS.get('T2_guidance', ()))}")
    return emit(4, checks, observed, [
        at_text("engine/earnings_release/figures.py", "_GUIDANCE_SENTENCE_RE ="),
        at_def(FIG._extract_guidance),
        at_def(pf.leaf_payload),
        at_text("engine/news_impact/prophet_adapter.py", '"T2_guidance": ('),
        at_text(CONTRACT, '"prior_amount": {'),
        at_test(T_BINDING, "test_a_guidance_range_with_no_declared_basis_is_absent_not_guessed"),
        at_test(T_BINDING, "test_a_guidance_range_that_declares_everything_does_bind"),
    ])


def p5_correction(scratch: Path) -> str:
    """A source correction supersedes the old value and invalidates what was derived."""
    original = _bind(_release_body("ex99_1_release.htm"))
    amended = _bind(_release_body("ex99_1_release_tampered.htm"), accession=REL_AMENDMENT,
                    form="8-K/A", filing_date="2026-02-02", acceptance="2026-02-02T14:31:00Z")
    collapsed = B.collapse_release_events([original, amended])
    event = collapsed.events[0] if len(collapsed.events) == 1 else None
    eps_before = original.figures.figure("eps_diluted", basis="gaap").value
    eps_after = amended.figures.figure("eps_diluted", basis="gaap").value

    source = EF.pg_bound_case("annual_first").source
    first = _pg_workspace()
    corrected = _pg_workspace(source.replace("3.07", "3.11"), prior_sha=first["_source_sha256"])
    sticky = _pg_workspace(source.replace("3.07", "3.11"), prior_sha=corrected["_source_sha256"],
                           prior_state="corrected")

    guide = _t2("v2_guide", 1)
    fix = _t2("v2_corr", 2, stated_amount=_qpoint(850_000_000, "total", CORRECTION))
    fix["novelty"] = "corrected_fact"
    fix["supersedes_fact_id"] = guide["fact_id"]
    records, _ = _run_facts(scratch, "p5_correction", [guide, fix])
    rec = records.get(fix["fact_id"]) or {}
    first_rec = records.get(guide["fact_id"]) or {}

    bridge = sorted(p.name for p in (ROOT / "engine" / "news_impact").glob("*.py")
                    if "earnings_release" in p.read_text(encoding="utf-8")
                    or "event_workspace" in p.read_text(encoding="utf-8"))

    checks = [
        ("amendment_is_second_revision_of_one_event",
         event is not None and len(event.revisions) == 2
         and event.current.filing_key.accession == REL_AMENDMENT and event.amended),
        ("amended_figure_replaces_original", eps_before != eps_after),
        ("workspace_correction_keeps_event_id",
         corrected["event_id"] == first["event_id"]
         and corrected["lifecycle"]["state"] == "corrected"
         and _eps(first) == [3.07] and _eps(corrected) == [3.11]),
        ("corrected_state_sticky", sticky["lifecycle"]["state"] == "corrected"),
        ("workspace_retains_superseded_value",
         "3.07" in json.dumps(corrected, sort_keys=True, default=str)),
        ("news_impact_correction_event_valid", _valid(fix)),
        ("later_fact_revises_the_same_slot",
         rec.get("record_kind") == "fact_revision"
         and rec.get("fact_key") == first_rec.get("fact_key")),
        ("producer_records_corrected_fact",
         rec.get("novelty") == "corrected_fact"
         and rec.get("supersedes_fact_id") == guide["fact_id"]),
        ("news_impact_reads_release_correction", bool(bridge)),
    ]
    observed = (f"8-K/A collapses to {len(collapsed.events)} event "
                f"{len(event.revisions) if event else 0} revisions eps_diluted gaap "
                f"{eps_before}->{eps_after}; PG workspace eps {_eps(first)}->{_eps(corrected)} "
                f"state {corrected['lifecycle']['state']} lifecycle keys "
                f"{sorted(corrected['lifecycle'])}; news_impact corrected_fact recorded as "
                f"{rec.get('record_kind')} novelty {rec.get('novelty')} supersedes "
                f"{'linked' if rec.get('supersedes_fact_id') else 'none'}; "
                f"news_impact modules naming earnings_release/event_workspace in source "
                f"{bridge} (source census, not a producer call)")
    return emit(5, checks, observed, [
        at_def(B.collapse_release_events),
        at_text("engine/news_impact/producer_facts.py", "FactObservation("),
        at_def(CL.assign_novelty),
        at_test(T_BINDING, "test_an_amended_release_body_is_a_second_revision_of_one_event"),
        at_test(T_WORKSPACE, "test_prior_lifecycle_state_corrected_is_sticky_when_sha_unchanged"),
    ])


def p6_explanation(scratch: Path) -> str:
    """The ticker and catalyst read explains the real change and what remains unknown."""
    aapl = _aapl_workspace()
    aapl_body = (CI_FIXTURES / "aapl_fy2026_q3_ex99_1.htm").read_text(encoding="utf-8")
    aapl_fixed = _aapl_workspace(aapl_body.replace("109,417", "110,417"),
                                 prior_sha=aapl["_source_sha256"])
    glance = _public_workspace_glance({"workspace": aapl, "ticker": "AAPL"})
    glance_fixed = _public_workspace_glance({"workspace": aapl_fixed, "ticker": "AAPL"})

    source = EF.pg_bound_case("annual_first").source
    pg_first = _pg_workspace()
    pg_fixed = _pg_workspace(source.replace("3.07", "3.11"), prior_sha=pg_first["_source_sha256"])
    pg_glance = _public_workspace_glance({"workspace": pg_fixed, "ticker": "PG"})

    _, views = _run_facts(scratch, "p6_thesis", [_t2()])
    proposition = (views[0].get("view") or {}).get("original_proposition") or {} if views else {}
    statement = proposition.get("plain_statement") or ""

    def revenue(g):
        return [r["value"] for r in g["reported"] if r.get("metric") == "revenue"]

    coverage = {c["id"]: c["state"] for c in glance["coverage_states"]}
    checks = [
        ("reported_value_from_replayed_receipt",
         any(r.get("metric") == "revenue" and r.get("receipt_state") == "byte_replayed"
             and r.get("value") for r in glance["reported"])),
        ("guidance_names_horizon",
         bool(glance["guidance"]) and all(g.get("horizon") for g in glance["guidance"])),
        ("unknowns_declared", {"consensus", "reaction"} <= set(coverage)),
        ("corrected_value_reaches_glance",
         glance_fixed["lifecycle_state"] == "corrected"
         and glance_fixed["event_id"] == glance["event_id"]
         and revenue(glance_fixed) != revenue(glance)),
        ("profile_metric_correction_reaches_glance",
         pg_glance["lifecycle_state"] == "corrected" and bool(pg_glance["reported"])),
        ("thesis_states_amount_and_direction",
         "900" in statement and "raise" in statement.lower()),
    ]
    observed = (f"AAPL revenue {ascii(revenue(glance))}->{ascii(revenue(glance_fixed))} state "
                f"{glance_fixed['lifecycle_state']}; coverage {sorted(coverage.items())}; PG "
                f"corrected glance state {pg_glance['lifecycle_state']} reported "
                f"{len(pg_glance['reported'])} items guidance {len(pg_glance['guidance'])}; "
                f"T2 thesis plain_statement {statement!r}; served page not exercised offline")
    return emit(6, checks, observed, [
        at_def(_public_workspace_glance),
        at_def(TH._plain_statement),
        at_test(T_WORKSPACE, "test_public_glance_same_event_correction_updates_value_not_id"),
    ])


CHECKS = (p1_identity, p2_period_basis, p3_output_basis, p4_actual_expected_prior,
          p5_correction, p6_explanation)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scratch", type=Path, default=None)
    args = parser.parse_args()
    scratch = args.scratch or Path(tempfile.mkdtemp(prefix="v91-v2-proof-"))
    scratch.mkdir(parents=True, exist_ok=True)
    tally = {"PROVEN": 0, "PARTIAL": 0, "ABSENT": 0, "HUMAN_GATE": 0}
    for check in CHECKS:
        tally[check(scratch)] += 1
    print(f"V2 SUMMARY proven={tally['PROVEN']} partial={tally['PARTIAL']} "
          f"absent={tally['ABSENT']} human_gate={tally['HUMAN_GATE']} rung=OFFLINE_FIXTURE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
