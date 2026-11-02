#!/usr/bin/env python3
"""V91 §9.1 vertical proof V3: capital allocation or major contract.

MASTERPLAN research/news_intelligence_estate_20261021/MASTERPLAN.md, section 9.1,
row "Capital allocation or major contract": "Authorised versus executed amount,
contract ceiling versus recognised economics, timing and conditions preserved",
consumer outcome "Deterministic scenario with assumptions; no automatic
EPS/price target".

Offline and deterministic. Every input is a synthetic news_impact event whose
quoted source text is written below (SYNTH issuer, synthetic CIK and filing id);
the expected roles come from those sentences, never from producer output. The
proof calls the repository producers (validate_event, producer_facts.run,
mechanisms.map_event, prophet_adapter.adapt_batch, the HKEX collector parse
functions) and prints what it observed. Standard library plus repository
modules only; no network (the HKEX request is captured by an in-process stub
transport, never sent), no model call, no wall clock, and every file it writes
lives under --scratch. Run from anywhere:

    python3 research/news_intelligence_estate_20261021/v91_proofs/v3_capital_contract.py \
        --scratch /tmp/any-dir

Output is exactly one line per property P1..P7 then one SUMMARY line; the
sibling .expected file pins the verdicts. Evidence cites producer and test
locations computed from the current source, so they track line drift.
"""
from __future__ import annotations

import argparse
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

from engine.news_impact import mechanisms as M  # noqa: E402
from engine.news_impact import producer_facts as pf  # noqa: E402
from engine.news_impact import prophet_adapter as PA  # noqa: E402
from engine.news_impact.validate import validate_event  # noqa: E402

# No committed data artifact is needed: every input is synthetic and inline.
REQUIRED_ARTIFACTS = ()

# ------------------------------------------------------------ source texts ----
# Capital allocation: a new authorisation and, separately, buybacks executed
# to date under existing programs. 500 million is authorised, 120 million is
# executed; nothing in the text says the 500 million was bought.
AUTH = ("The board authorized an additional USD 500 million share repurchase "
        "program through fiscal 2027.")
EXEC = ("Under its existing programs the company has repurchased USD 120 "
        "million of shares to date.")
COND = ("The repurchase is conditional on shareholder approval at the 2027 "
        "annual meeting.")
UNGROUNDED = "Subject to regulatory approval in three jurisdictions."
# Major contract: a firm order plus an option ceiling that is not revenue.
FIRM = ("The customer placed a firm order worth USD 400 million for delivery "
        "in fiscal 2027.")
OPT = ("Options in the agreement could raise the total contract value to USD 2 "
       "billion.")
# Plain-language recommendation wording that must never reach a reader.
RECO_PHRASES = ("price target of 250", "we rate it a buy",
                "fair value of USD 300 per share", "upgraded to buy")
RECO_QUOTE = "Analysts set a price target of 250 and we rate it a buy."
RATED_QUOTE = "The shares are rated a buy by the bank."

DOC = "sec:0000000000-26-000301:synth_v3.htm"
CIK = "cik:0000999301"
FLAGS = {"may_rank": False, "may_size": False, "may_gate": False,
         "prophet_authority": False}
FY27 = {"year": 2027, "quarter": None, "calendar_end": None,
        "period_kind": "fiscal_year"}
SRC = sha256(b"synth-v3-source").hexdigest()
AT = "2026-10-05T12:00:00Z"
CEILINGS = ("2000000000", "2400000000")
HK_LANG_NEEDLE = '"lang": "E"'


# --------------------------------------------------------------- citations ----
def _rel(path) -> str:
    return Path(path).resolve().relative_to(ROOT).as_posix()


def at_def(obj) -> str:
    """path:line of a producer definition, read from the current source."""
    _, line = inspect.getsourcelines(obj)
    return f"{_rel(inspect.getsourcefile(obj))}:{line}"


def at_text(rel: str, needle: str) -> str:
    """path:line of the first source line containing needle."""
    text = (ROOT / rel).read_text(encoding="utf-8")
    for n, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return f"{rel}:{n}"
    raise LookupError(f"{needle!r} not found in {rel}")


def at_test(rel: str, name: str) -> str:
    return at_text(rel, f"def {name}(")


# ---------------------------------------------------------------- builders ----
def span(text: str) -> dict:
    n = len(text.encode())
    digest = sha256(text.encode()).hexdigest()
    return {
        "schema": "source_span.v1", "authority": "context_only",
        "span_id": "span_" + sha256((DOC + text).encode()).hexdigest()[:20],
        "document_id": DOC, "document_version": 1,
        "locator": {"kind": "text_span", "sub_kind": "transcript_segment",
                    "segment_index": 0, "span_start_byte": 0, "span_end_byte": n},
        "text_sha256": digest, "display_excerpt": text,
        "rights_profile": "rp_unknown_v1", "receipt_state": "byte_replayed",
        "receipt": {"source_sha256": SRC, "segment_index": 0,
                    "segment_sha256": SRC, "segment_bytes": 400,
                    "span_start_byte": 0, "span_end_byte": n, "text_sha256": digest},
        "unreplayable_reason": None,
    }


def ev(text: str) -> dict:
    return {"claimed_quote": text, "span": span(text)}


def absent(subject: str) -> dict:
    return {"schema": "field_absence.v1", "authority": "context_only",
            "reason": "not_stated", "subject": subject, "detail": "",
            "missing_fields": [subject]}


def q_point(value: int, basis: str, text: str) -> dict:
    return {"form": "point", "value": value, "bound": "exact", "unit": "USD",
            "currency": "USD", "basis": basis, "period": dict(FY27),
            "negated": False, "evidence": ev(text)}


def q_absent(subject: str) -> dict:
    return {"form": "absent", "absence": absent(subject)}


def envelope(schema: str, seed: str) -> dict:
    return {
        "schema": schema, "authority": "context_only",
        "prophet_flags": dict(FLAGS), "unsolicited_instruction_detected": False,
        "fact_id": "fact_" + sha256(seed.encode()).hexdigest()[:24],
        "document_id": DOC, "observed_at": AT, "source_available_at": AT,
        "supersedes_fact_id": None, "company_id": CIK, "issuer_role": "subject",
        "novelty": "new_magnitude_timing_commitment_counterparty", "negated": False,
    }


def t1(seed: str, **overrides) -> dict:
    """T1 capital action: 500M authorised (AUTH), 120M executed (EXEC)."""
    event = envelope(pf.T1, seed)
    event.update({
        "action_type": "share_repurchase", "commitment_status": "authorized",
        "primary_amount_role": "incremental_authorization",
        "incremental_amount": q_point(500_000_000, "incremental", AUTH),
        "remaining_authorization": q_absent("remaining_authorization"),
        "executed_amount": q_point(120_000_000, "total", EXEC),
        "horizon_period": dict(FY27), "action_span": ev(AUTH),
        "cluster_grain": "fact_revision",
    })
    event.update(overrides)
    return event


def t2(seed: str, **overrides) -> dict:
    """T2 demand event: 400M firm order (FIRM) plus a 2B option ceiling (OPT)."""
    event = envelope(pf.T2, seed)
    event.update({
        "demand_stage": "bookings", "metric": "bookings",
        "commitment_status": "announced",
        "stated_amount": q_point(400_000_000, "incremental", FIRM),
        "option_ceiling": q_point(2_000_000_000, "total", OPT),
        "cluster_grain": "fact_revision", "fiscal_period": dict(FY27),
        "revision_direction": "awarded",
        "counterparty_company_id": absent("counterparty_company_id"),
        "baseline": {
            "type": "UNKNOWN", "timestamp": absent("baseline_timestamp"),
            "contributors": absent("baseline_contributors"),
            "coverage": absent("baseline_coverage"),
            "period": absent("baseline_period"), "basis": absent("baseline_basis"),
            "age_days": absent("baseline_age_days"),
        },
    })
    event.update(overrides)
    return event


def codes(report) -> list[tuple[str, str]]:
    return sorted({(issue.code, issue.path) for issue in report.issues})


def run_producer(scratch: Path, name: str, event: dict) -> dict[str, str]:
    """producer_facts.run on one event; returns every output file's text."""
    work = scratch / name
    work.mkdir(parents=True, exist_ok=True)
    rows = work / "events.jsonl"
    rows.write_text(json.dumps({"case_id": name, "shadow": False,
                                "novelty_source": "label_provisional",
                                "event": event}, sort_keys=True) + "\n",
                    encoding="utf-8")
    pf.run([rows], work / "out", None)
    return {f.name: f.read_text(encoding="utf-8")
            for f in sorted((work / "out").iterdir()) if f.is_file()}


def prophet_rows(outputs: dict[str, str]) -> list[dict]:
    return [json.loads(line)["evidence"]
            for line in outputs["prophet_evidence.jsonl"].splitlines() if line]


def amounts(record: dict) -> dict[str, object]:
    return {q.get("slot"): q.get("value") for q in record.get("quantities") or []}


def nq_values(mapping: dict) -> dict[str, tuple]:
    return {k: (v.get("value"), v.get("basis"), v.get("source_contract_path"))
            for k, v in sorted((mapping.get("named_quantities") or {}).items())}


# -------------------------------------------------------------- properties ----
def p1_authorised_versus_executed(scratch: Path) -> str:
    pos = t1("v3-p1-pos")
    pos_report = validate_event(pos)
    mapped = nq_values(M.map_event(pos).to_dict())
    produced = prophet_rows(run_producer(scratch, "p1_pos", pos))
    got = amounts(produced[0]) if produced else {}
    positive = (
        pos_report.ok
        and mapped.get("authorization_capacity") == (500_000_000, "incremental", "/incremental_amount")
        and mapped.get("executed_retired_or_issued") == (120_000_000, "total", "/executed_amount")
        and got.get("incremental_amount") == 500_000_000
        and got.get("executed_amount") == 120_000_000
    )
    # Structural negatives: executed role with no executed amount; executed
    # amount carried on an incremental basis.
    n1 = validate_event(t1("v3-p1-n1", primary_amount_role="executed",
                           executed_amount=q_absent("executed_amount")))
    n2 = validate_event(t1("v3-p1-n2",
                           executed_amount=q_point(120_000_000, "incremental", EXEC)))
    structural = (not n1.ok) and (not n2.ok)
    # Semantic mislabel: the authorised 500M, quoted from the authorisation
    # sentence, labelled as executed.
    mis = t1("v3-p1-mislabel", primary_amount_role="executed",
             commitment_status="executed",
             incremental_amount=q_absent("incremental_amount"),
             executed_amount=q_point(500_000_000, "total", AUTH))
    mis_report = validate_event(mis)
    mis_mapped = nq_values(M.map_event(mis).to_dict()) if mis_report.ok else {}
    mis_copy = ""
    if mis_report.ok:
        rec = PA.adapt_batch([mis])[0]
        mis_copy = PA.render_glance_copy(rec)["en"]["subtitle"]
    mislabel_held = (not mis_report.ok) or (
        mis_mapped.get("executed_retired_or_issued", (None,))[0] != 500_000_000)

    if positive and structural and mislabel_held:
        verdict = "PROVEN"
    elif positive:
        verdict = "PARTIAL"
    else:
        verdict = "ABSENT"
    print(
        f"V3 P1 {verdict} positive validate ok={pos_report.ok}; map_event keeps "
        f"authorization_capacity={mapped.get('authorization_capacity', (None,))[0]} "
        f"from /incremental_amount and executed_retired_or_issued="
        f"{mapped.get('executed_retired_or_issued', (None,))[0]} from /executed_amount; "
        f"producer_facts prophet_evidence slots incremental_amount="
        f"{got.get('incremental_amount')} executed_amount={got.get('executed_amount')}; "
        f"structural negatives refused n1={codes(n1)} n2={codes(n2)}; "
        f"semantic mislabel (500M quoted from the authorisation sentence, role executed) "
        f"validate ok={mis_report.ok}, map executed_retired_or_issued="
        f"{mis_mapped.get('executed_retired_or_issued', (None,))[0]}, reader copy "
        f"{mis_copy!r}: no check ties the role to its own quote; "
        f"{at_def(validate_event)} {at_def(M.map_event)} {at_def(pf.run)} "
        f"{at_test('tests/test_news_impact_producer_facts.py', 'test_t1_executed_role_keys_as_execution_under_program')} "
        f"{at_test('tests/test_news_impact_mechanisms.py', 'test_case_a_nvidia_authorization')}"
    )
    return verdict


def p2_ceiling_versus_recognised(scratch: Path) -> str:
    full = t2("v3-p2-full")
    full_report = validate_event(full)
    full_map = M.map_event(full).to_dict()
    full_out = run_producer(scratch, "p2_full", full)
    full_rec = prophet_rows(full_out)
    full_amounts = amounts(full_rec[0]) if full_rec else {}
    full_blob = json.dumps(full_map, sort_keys=True) + "".join(full_out.values())
    full_ok = (
        full_report.ok
        and nq_values(full_map) == {"stated_bookings": (400_000_000, "incremental", "/stated_amount")}
        and not any(c in full_blob for c in CEILINGS)
        and full_amounts == {"stated_amount": 400_000_000}
    )
    # Negative: the only amount is the ceiling.
    ceil = t2("v3-p2-ceiling-only", stated_amount=q_absent("stated_amount"))
    ceil_report = validate_event(ceil)
    ceil_map = M.map_event(ceil).to_dict()
    ceil_out = run_producer(scratch, "p2_ceiling", ceil)
    ceil_rec = prophet_rows(ceil_out)
    ceil_amounts = amounts(ceil_rec[0]) if ceil_rec else {}
    ceil_blob = json.dumps(ceil_map, sort_keys=True) + "".join(ceil_out.values())
    ceil_ok = (
        ceil_report.ok
        and not nq_values(ceil_map)
        and not any(c in ceil_blob for c in CEILINGS)
        and all(v is None for v in ceil_amounts.values())
    )
    stripped = PA.adapt_batch([full])[0].stripped_fields
    # Semantic mislabel, the same standard P1 applies: the 2B quoted from the
    # option sentence filed as the firm stated_amount.  Held only if the engine
    # refuses it or keeps it out of the firm bookings quantity.
    mis = t2("v3-p2-mislabel", stated_amount=q_point(2_000_000_000, "incremental", OPT))
    mis_report = validate_event(mis)
    mis_mapped = nq_values(M.map_event(mis).to_dict()) if mis_report.ok else {}
    mislabel_held = (not mis_report.ok) or (
        mis_mapped.get("stated_bookings", (None,))[0] != 2_000_000_000)
    # Pre-summed firm order plus ceiling filed as one incremental amount.
    summed = t2("v3-p2-summed",
                stated_amount=q_point(2_400_000_000, "incremental", FIRM + " " + OPT))
    summed_report = validate_event(summed)
    summed_held = not summed_report.ok
    # Reader copy for the ceiling-only event: a template placeholder in the
    # subtitle is a reader defect the ceiling-only path exposes.
    ceil_copy = ""
    if ceil_report.ok:
        ceil_copy = PA.render_glance_copy(PA.adapt_batch([ceil])[0])["en"]["subtitle"]
    copy_clean = "{" not in ceil_copy and "}" not in ceil_copy
    if full_ok and ceil_ok and mislabel_held and summed_held and copy_clean:
        verdict = "PROVEN"
    elif full_ok or ceil_ok:
        verdict = "PARTIAL"
    else:
        verdict = "ABSENT"
    print(
        f"V3 P2 {verdict} firm order + 2B option ceiling: validate ok={full_report.ok}, "
        f"map_event named_quantities={nq_values(full_map)} rules={full_map.get('rule_ids')}, "
        f"producer_facts prophet_evidence amounts={full_amounts}, the ceiling value appears "
        f"in no map or producer output (adapter stripped {sorted(stripped)}); ceiling-only "
        f"negative: validate ok={ceil_report.ok}, named_quantities={nq_values(ceil_map)}, "
        f"not_yet_quantifiable present={bool(ceil_map.get('not_yet_quantifiable'))}, prophet "
        f"amounts={ceil_amounts}, reader copy {ceil_copy!r}; semantic mislabel (2B quoted "
        f"from the option sentence filed as stated_amount) validate ok={mis_report.ok}, map "
        f"stated_bookings={mis_mapped.get('stated_bookings', (None,))[0]}; pre-summed 2.4B "
        f"validate ok={summed_report.ok} codes={codes(summed_report)}: the engine keeps "
        f"ceiling and firm order apart only when the extractor already filed them in "
        f"separate fields, and the ceiling itself is dropped, never shown as a labelled "
        f"ceiling, so the row's ceiling-versus-recognised-economics is not preserved; "
        f"{at_def(M.map_event)} {at_text('engine/news_impact/prophet_adapter.py', 'ALWAYS_DROP = frozenset(')} "
        f"{at_text('engine/news_impact/producer_facts.py', 'EVIDENCE_LADDER')} "
        f"{at_test('tests/test_news_impact_mechanisms.py', 'test_t2_option_ceiling_not_summed')} "
        f"(that test's final assertion cannot fail because map_event never writes option_ceiling)"
    )
    return verdict


def p3_timing_and_conditions(scratch: Path) -> str:
    missing = t1("v3-p3-missing")
    del missing["commitment_status"]
    missing_report = validate_event(missing)
    # Grounded: the condition sentence is inside the action span the event cites.
    grounded = t1("v3-p3-grounded", commitment_status="conditional",
                  action_span=ev(AUTH + " " + COND), conditions_quote=COND)
    grounded_report = validate_event(grounded)
    # Ungrounded: the condition text appears in no evidence span of the event.
    loose = t1("v3-p3-ungrounded", commitment_status="conditional",
               conditions_quote=UNGROUNDED)
    loose_report = validate_event(loose)
    rec = PA.adapt_batch([grounded])[0]
    hover_quotes = [row.get("quote") for row in rec.hover]
    glance = PA.render_glance_copy(rec)["en"]
    leaf = pf.leaf_payload(grounded, pf.fact_slot(grounded), Counter())
    out = run_producer(scratch, "p3_grounded", grounded)
    produced = prophet_rows(out)
    status_out = produced[0].get("commitment_status") if produced else None
    window_out = (produced[0].get("glance") or {}).get("slots", {}).get("window_plain") if produced else None
    cond_files = sorted(name for name, text in out.items() if COND in text)
    quote_key_kept = any("conditions_quote" in text for text in out.values())
    survives = (grounded_report.ok and status_out == "conditional"
                and window_out == "through fiscal 2027" and COND in hover_quotes)
    critical = not missing_report.ok
    ungrounded_refused = not loose_report.ok
    if critical and survives and ungrounded_refused:
        verdict = "PROVEN"
    elif critical and survives:
        verdict = "PARTIAL"
    else:
        verdict = "ABSENT"
    print(
        f"V3 P3 {verdict} missing commitment_status refused {codes(missing_report)}; "
        f"grounded condition: validate ok={grounded_report.ok}, producer_facts "
        f"prophet_evidence commitment_status={status_out!r} window={window_out!r}, leaf "
        f"commitment_status={leaf.get('commitment_status')!r}, reader copy {glance['title']!r}, "
        f"adapter hover carries the condition quote={COND in hover_quotes}, condition sentence "
        f"found in producer_facts files {cond_files} (inside the cited action span excerpt; "
        f"conditions_quote key kept={quote_key_kept}); ungrounded conditions_quote "
        f"(in no evidence span) validate ok={loose_report.ok}: no grounding check exists; "
        f"{at_def(validate_event)} {at_def(PA._hover_from)} {at_def(pf.leaf_payload)} "
        f"{at_test('tests/test_news_impact_contracts.py', 'test_critical_fields')} "
        f"{at_test('tests/test_news_impact_validate.py', 'test_s8_split_role_marker_rejected')}"
    )
    return verdict


def _keys(node, found=None):
    found = set() if found is None else found
    if isinstance(node, dict):
        for key, value in node.items():
            found.add(str(key))
            _keys(value, found)
    elif isinstance(node, (list, tuple)):
        for value in node:
            _keys(value, found)
    return found


def p4_deterministic_scenario(scratch: Path) -> str:
    del scratch
    one = (M.ChannelAssignment("strategic_option", "earnings_countable"),)
    two = one + (M.ChannelAssignment("moat_duration", "watch_only"),)
    first = M.assemble_duration_scenarios(one)
    again = M.assemble_duration_scenarios(one)
    other = M.assemble_duration_scenarios(two)
    deterministic = first is not None and first == again and (
        json.dumps(first, sort_keys=True) == json.dumps(again, sort_keys=True))
    keys = _keys(first) if first else set()
    weighted = sorted(keys & set(M.FORBIDDEN_KEYS))
    assumption_keys = sorted(k for k in keys if "assumption" in k)
    params = list(inspect.signature(M.assemble_duration_scenarios).parameters)
    input_independent = (first or {}).get("scenarios") == (other or {}).get("scenarios")
    own = {
        "T1 buyback": M.map_event(t1("v3-p4-t1")).to_dict().get("duration_scenarios"),
        "T2 contract": M.map_event(t2("v3-p4-t2")).to_dict().get("duration_scenarios"),
    }
    if deterministic and not weighted and assumption_keys:
        verdict = "PROVEN"
    elif deterministic and not weighted:
        verdict = "PARTIAL"
    else:
        verdict = "ABSENT"
    print(
        f"V3 P4 {verdict} assemble_duration_scenarios returns identical output on two "
        f"calls={deterministic}, weights_status={(first or {}).get('weights_status')!r}, "
        f"forbidden weight keys present={weighted}, each scenario carries "
        f"evidence_needed_before_weight and who_would_rule; assumption fields={assumption_keys}; "
        f"its only parameter is {params} (channel assignments), so no stated assumption can be "
        f"changed and the four scenarios are identical for a different channel set="
        f"{input_independent}; this vertical's own events map to duration_scenarios="
        f"{own}; {at_def(M.assemble_duration_scenarios)} "
        f"{at_test('tests/test_news_impact_mechanisms.py', 'test_assemble_not_yet_quantifiable_and_duration')}"
    )
    return verdict


def p5_no_automatic_eps_or_target(scratch: Path) -> str:
    del scratch
    structured = t2("v3-p5-structured")
    structured.update({"price_target": 250, "eps": 3.1, "rating": "buy"})
    _, stripped = M.strip_forbidden_fields(structured)
    structured_report = validate_event(structured)
    structured_refused = (not structured_report.ok) and any(
        path in ("/price_target", "/eps", "/rating") or code.startswith("forbidden")
        for code, path in codes(structured_report))
    detected = {text: PA.recommendation_phrase(text) for text in RECO_PHRASES}
    leaks = {}
    for name, quote in (("reco", RECO_QUOTE), ("rated", RATED_QUOTE)):
        event = t1(f"v3-p5-{name}", commitment_status="conditional",
                   conditions_quote=quote)
        report = validate_event(event)
        reached = False
        if report.ok:
            try:
                rec = PA.adapt_batch([event])[0]
                reached = any(row.get("quote") == quote for row in rec.hover)
            except PA.ProphetAdapterError:
                reached = False
        leaks[name] = {"validate_ok": report.ok, "reaches_hover": reached}
    plain_refused = (all(detected[t] for t in RECO_PHRASES)
                     and not any(v["reaches_hover"] for v in leaks.values()))
    if structured_refused and plain_refused:
        verdict = "PROVEN"
    elif structured_refused:
        verdict = "PARTIAL"
    else:
        verdict = "ABSENT"
    print(
        f"V3 P5 {verdict} structured price_target/eps/rating: strip_forbidden_fields "
        f"strips {sorted(stripped)}, validate refuses {codes(structured_report)}; "
        f"recommendation_phrase detects "
        f"{ {t: detected[t] for t in RECO_PHRASES} }; free-text conditions_quote "
        f"{RECO_QUOTE!r} -> {leaks['reco']}, {RATED_QUOTE!r} -> {leaks['rated']}: the "
        f"phrase gate covers glance copy only and misses 'price target of N' and 'rate it a "
        f"buy'; {at_def(M.strip_forbidden_fields)} {at_def(PA.recommendation_phrase)} "
        f"{at_def(PA._hover_from)} "
        f"{at_test('tests/test_news_impact_f2_text_safety.py', 'test_recommendation_phrase_detects')} "
        f"{at_test('tests/test_news_impact_contracts.py', 'test_forbidden_names_absent')}"
    )
    return verdict


CONSUMER_TOKENS = ("news_impact", "prophet_adapter", "assemble_duration_scenarios",
                   "duration_scenario_set", "primary_amount_role", "option_ceiling")
CONSUMER_DIRS = ("app", "templates", "scripts")
TEXT_SUFFIXES = {".py", ".html", ".j2", ".js", ".jsx", ".ts", ".tsx", ".json",
                 ".yml", ".yaml", ".sh"}


def p6_user_facing_consumer(scratch: Path) -> str:
    del scratch
    hits: dict[str, list[str]] = {t: [] for t in CONSUMER_TOKENS}
    scanned = 0
    for top in CONSUMER_DIRS:
        base = ROOT / top
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
                continue
            scanned += 1
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for token in CONSUMER_TOKENS:
                if token in text:
                    hits[token].append(_rel(path))
    found = sorted({p for paths in hits.values() for p in paths})
    verdict = "ABSENT" if not found else "PARTIAL"
    reader = at_text("scripts/build_ticker_pages.py", 'blob.get("capital_allocation")')
    print(
        f"V3 P6 {verdict} read-only scan of {scanned} source files under "
        f"{'/'.join(CONSUMER_DIRS)} for {list(CONSUMER_TOKENS)} found "
        f"{len(found)} files{(': ' + ', '.join(found[:5])) if found else ''}; no page, "
        f"template or builder renders a news_impact scenario; the nearest reader {reader} "
        f"shows the ticker capital_allocation blob, not news_impact output; no-test"
    )
    return verdict


# Synthetic HKEXnews servlet rows (stock code 99999 is not a listing).
HK_ROWS = [
    {"NEWS_ID": "99990001", "STOCK_CODE": "99999", "DATE_TIME": "05/10/2026 18:30",
     "TITLE": ("SYNTH HOLDINGS - ANNOUNCEMENT PURSUANT TO CODE ON SHARE BUY-BACKS: "
               "BOARD AUTHORISES REPURCHASE OF UP TO HK$500 MILLION; HK$120 MILLION "
               "REPURCHASED TO DATE"),
     "SHORT_TEXT": "Announcements and Notices - [Share Buyback]"},
    {"NEWS_ID": "99990002", "STOCK_CODE": "99999", "DATE_TIME": "05/10/2026 18:31",
     "TITLE": "合成控股 - 根據股份回購守則刊發的公告：董事會授權回購最多5億港元；迄今已回購1.2億港元",
     "SHORT_TEXT": "公告及通告 - [股份回購]"},
]


class _StubResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self) -> None:
        return None


def p7_hong_kong_variant(scratch: Path) -> str:
    del scratch
    from collectors import hk_hkexnews as hk

    payload = {"result": json.dumps(HK_ROWS, ensure_ascii=False), "recordCnt": 2}
    sent: list[dict] = []
    real_get = hk.requests.get

    def stub_get(url, params=None, **_kw):
        sent.append(dict(params or {}))
        return _StubResponse(json.dumps(payload, ensure_ascii=False))

    hk.requests.get = stub_get
    try:
        got = hk._query("18100", "8", date(2026, 10, 1), date(2026, 10, 5), 1000, retries=1)
    finally:
        hk.requests.get = real_get
    rows = hk._result_rows(got)
    frame = hk._rows_to_frame(rows, "buyback")
    columns = list(frame.columns)
    amount_cols = [c for c in columns if any(w in c for w in ("amount", "authori", "execut", "value"))]
    titles = list(frame["title"])
    zh_verbatim = HK_ROWS[1]["TITLE"] in titles
    en_verbatim = HK_ROWS[0]["TITLE"] in titles
    langs = sorted({p.get("lang") for p in sent})
    hk_event = t1("v3-p7-hk", company_id="hkex:99999")
    hk_report = validate_event(hk_event)
    distinct = bool(amount_cols) and hk_report.ok
    verdict = "PROVEN" if distinct else "ABSENT"
    print(
        f"V3 P7 {verdict} HKEX buyback collector exercised offline (stub transport, no "
        f"send): request lang={langs}, parsed {len(frame)} rows with columns {columns}; amount "
        f"columns={amount_cols}, so authorised HK$500M and executed HK$120M survive only "
        f"inside the title text; EN title verbatim={en_verbatim}, ZH title passes _clean_text "
        f"verbatim={zh_verbatim}, but the collector only requests the English listing; a "
        f"news_impact event for this issuer is refused {codes(hk_report)} because company_id "
        f"must be a SEC CIK; languages declared: EN requested, ZH parsed only when supplied; "
        f"{at_def(hk._rows_to_frame)} {at_text('collectors/hk_hkexnews.py', HK_LANG_NEEDLE)} "
        f"{at_text('contracts/news_impact/news_impact_event.v1.schema.json', '^cik:')} "
        f"{at_text('tests/test_hk_filing_bus.py', 'from collectors.hk_hkexnews import _rows_to_frame, _EVENT_COLS')}"
    )
    return verdict


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scratch",
        default=None,
        help="directory for every file this proof writes (default: a new temp dir)",
    )
    args = parser.parse_args()
    scratch = Path(args.scratch or tempfile.mkdtemp(prefix="v91-v3-proof-"))
    scratch.mkdir(parents=True, exist_ok=True)

    tally = {"PROVEN": 0, "PARTIAL": 0, "ABSENT": 0, "HUMAN_GATE": 0}
    for check in (
        p1_authorised_versus_executed,
        p2_ceiling_versus_recognised,
        p3_timing_and_conditions,
        p4_deterministic_scenario,
        p5_no_automatic_eps_or_target,
        p6_user_facing_consumer,
        p7_hong_kong_variant,
    ):
        tally[check(scratch)] += 1
    print(
        "V3 SUMMARY "
        f"proven={tally['PROVEN']} partial={tally['PARTIAL']} "
        f"absent={tally['ABSENT']} human_gate={tally['HUMAN_GATE']} "
        f"rung=OFFLINE_FIXTURE"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
