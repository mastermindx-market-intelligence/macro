#!/usr/bin/env python3
"""V91 vertical proof V4 — masterplan §9.1 row "Policy or supply-chain event".

Fabric lane news-w4-v91-v4-build-r1 (News Intelligence Estate seat, V91 proof
wave). Offline, deterministic, synthetic: fixed 2026 ISO dates, no network, no
wall clock, no model call, and no write anywhere (not even under --scratch);
the producers under test receive explicit inputs only.

Rung COMMITTED_ARTIFACT (V91_VERTICAL_PROOF_READINESS.md §V4): P2, P3 and P5
read the tracked artifacts site/basketdata/foresight_cascade.json and
site/foresight.html from the repository path resolved from __file__, never
regenerate or write them. REQUIRED_ARTIFACTS below is what the shared harness
checks to skip this proof in a sparse tree.

Properties (readiness map §V4, quoting MASTERPLAN.md:474):
  P1 report/proposal/final/effective states distinct — collectors stage
     taxonomy + engine/policy_calendar.py effective-date proxy
  P2 sourced, dated product/company exposure — committed cascade chip +
     producer chip from a SYNTH row naming company/product/source
  P3 alternatives and falsifiers — cascade + producers (ceiling PARTIAL)
  P4 conditional mechanism in the contract — news_impact schema + channel lib
  P5 Theme + MarketOntology consumer — committed foresight page

Each property prints exactly one line ``V4 P<k> <VERDICT> <evidence>``. Every
verdict is derived from what THIS run observed: each probe computes a
discriminating count, refusal or mapped assignment, and the verdict follows
from those booleans (a mechanism that appears promotes its line; one that
vanishes demotes it). Run from the repo root with PYTHONPATH=.:

    PYTHONPATH=. python3 research/news_intelligence_estate_20261021/v91_proofs/ \
        v4_policy_supply_chain.py --scratch /tmp/any-dir
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED_ARTIFACTS = ("site/basketdata/foresight_cascade.json", "site/foresight.html")

TODAY = date(2026, 11, 2)  # fixed "today" for the calendar path; never the wall clock

# Member-name stems an alternative-explanation / falsifier surface would carry.
FALSIFIER_STEMS = re.compile(
    r"alternative|falsif|counter[_-]?evidence|disconfirm|refut|invalidat|null[_-]?hyp",
    re.IGNORECASE,
)


def _cascade() -> dict:
    """The committed foresight cascade JSON, read-only from the repository tree."""
    return json.loads((ROOT / REQUIRED_ARTIFACTS[0]).read_text(encoding="utf-8"))


def _walk_keys(node) -> list[str]:
    """Every object key in a nested JSON structure, in deterministic walk order."""
    if isinstance(node, dict):
        out = [str(k) for k in node]
        for v in node.values():
            out.extend(_walk_keys(v))
        return out
    if isinstance(node, list):
        out: list[str] = []
        for v in node:
            out.extend(_walk_keys(v))
        return out
    return []


# Member-name stems for the exposure families the §9.1 row asks for: a company
# or product identity, a source, and a date. PROVEN needs all three, non-empty.
EXPOSURE_COMPANY = re.compile(r"compan|product|ticker|cik|issuer", re.IGNORECASE)
EXPOSURE_SOURCE = re.compile(r"source|document|url|citation", re.IGNORECASE)
POLICY_LANE_MODULES = (
    "engine.policy_calendar",
    "engine.foresight_cascade",
    "collectors.federal_register",
)


def _synth_row(num: str, dtype: str, action: str, stage: str, weight: float,
               close_on: str, publication: str = "2026-09-15", **extra) -> dict:
    """One SYNTH Federal Register store row in the collector's _FIELDS shape."""
    row = {
        "document_number": num,
        "basket_id": "synth_policy_theme",
        "publication_date": publication,
        "type": dtype,
        "reg_stage": stage,
        "weight": weight,
        "significant": True,
        "title": f"SYNTH policy document {num}",
        "abstract": "SYNTH abstract",
        "action": action,
        "rin": "",
        "comments_close_on": close_on,
        "agency_slug": "synth-agency",
        "cfr_ref": "",
        "_first_seen": "2026-09-16T00:00:00+00:00",
    }
    row.update(extra)
    return row


def _exposure_families(obj: dict) -> dict[str, bool]:
    """Which exposure families a chip/row carries as NON-EMPTY members."""
    def has(rx: re.Pattern) -> bool:
        return any(rx.search(k) and obj.get(k) not in (None, "", [], {}) for k in obj)
    dated = any(("date" in k or k.endswith("_on")) and obj.get(k) for k in obj)
    return {
        "company_product": has(EXPOSURE_COMPANY),
        "source": has(EXPOSURE_SOURCE),
        "date": dated,
    }


# ----------------------------------------------------------------------- P1 ----
def p1_stage_states() -> tuple[str, str]:
    """Report/proposal/final/effective states: taxonomy distinct, effective proxied.

    Positive: four SYNTH documents whose action text states its own stage
    ("Request for Information" -> rfi, "Interim final rule" -> interim_final_rule,
    ...) must map to four distinct reg_stage values through the collector's own
    _reg_stage. Negative: a SYNTH final rule whose effective date differs from
    its comment-close date goes through the calendar path as the EARLIEST-closing
    final rule (the other final rule closes later, so no tie confounds the
    read); a mechanism that carried effective dates would report the effective
    date, the store proxy reports the comment-close date. The proxy is also what
    users see: format_policy_reg_chip renders it as "rule effective in Nd".
    """
    import pandas as pd
    from collectors.federal_register import _FIELDS, _reg_stage
    from engine.policy_calendar import compute_policy_calendar, format_policy_reg_chip

    # (document_number, type, action, expected reg_stage, comments_close_on) —
    # expected is stated by the action text itself per the _STAGE_WEIGHTS
    # taxonomy, before any call. The plain final rule closes AFTER the
    # discriminating rule below so the proxy cannot pick it by tie; the other
    # documents close BEFORE it so the chip's comment-close and rule-effective
    # days differ and the user-facing "rule effective in Nd" text is rendered.
    docs = [
        ("SYNTH-FR-001", "NOTICE", "Request for Information; synthetic advisory panel", "rfi", "2026-11-10"),
        ("SYNTH-FR-002", "PRORULE", "Proposed rule; synthetic energy standards", "proposed_rule", "2026-11-10"),
        ("SYNTH-FR-003", "RULE", "Final rule; synthetic energy standards", "final_rule", "2026-12-20"),
        ("SYNTH-FR-004", "RULE", "Interim final rule; synthetic import adjustment", "interim_final_rule", "2026-11-10"),
    ]
    derived = [(num, _reg_stage(dtype, action)) for num, dtype, action, _, _ in docs]
    positive_ok = all(
        stage == want for (_, _, _, want, _), (_, (stage, _w)) in zip(docs, derived)
    ) and len({stage for _, (stage, _w) in derived}) == len(docs)

    rows = [
        _synth_row(num, dtype, action, stage, weight, close_on)
        for (num, dtype, action, _want, close_on), (_n, (stage, weight)) in zip(docs, derived)
    ]
    # Discriminating doc: effective date (FR API field effective_on) != close date,
    # and it is the earliest-closing final rule in the frame.
    effective_on = "2026-12-15"
    close_on = "2026-11-20"
    rows.append(_synth_row(
        "SYNTH-FR-005", "RULE", "Final rule; effective December 15 2026", "final_rule", 1.5,
        close_on, publication="2026-10-01", effective_on=effective_on,
        title="SYNTH final rule with a distinct effective date",
        _first_seen="2026-10-02T00:00:00+00:00",
    ))
    result = compute_policy_calendar(df=pd.DataFrame(rows), today=TODAY)
    theme_row = result["themes"]["synth_policy_theme"]
    reported_effective = theme_row["next_rule_effective_date"]
    effective_carried = reported_effective == effective_on
    proxy_is_close = reported_effective == close_on
    field_requested = "effective_on" in _FIELDS
    chip = format_policy_reg_chip(theme_row, "synth_policy_theme") or {}
    shown_match = re.search(r"rule effective in (\d+)d", chip.get("summary") or "")
    shown_as_effective = bool(shown_match)

    if positive_ok and effective_carried and field_requested:
        verdict = "PROVEN"
    elif positive_ok:
        verdict = "PARTIAL"
    else:
        verdict = "ABSENT"
    stages_txt = "/".join(want for _, _, _, want, _ in docs)
    evidence = (
        f"SYNTH docs -> {stages_txt} distinct={len({s for _, (s, _w) in derived}) == len(docs)}; "
        f"earliest-closing SYNTH final rule effective_on={effective_on} vs comments_close_on="
        f"{close_on} -> next_rule_effective_date={reported_effective} (proxy={proxy_is_close}; "
        f"effective_on in _FIELDS={field_requested}); chip shows it to users as "
        f"'rule effective in {shown_match.group(1) if shown_match else '-'}d'={shown_as_effective}; "
        f"collectors/federal_register.py:107 engine/policy_calendar.py:146 "
        f"engine/policy_calendar.py:233 tests/test_federal_register.py:319"
    )
    return verdict, evidence


# ----------------------------------------------------------------------- P2 ----
def p2_dated_exposure() -> tuple[str, str]:
    """Sourced, dated product/company exposure: committed chip + producer row.

    Artifact half: every committed policy_reg_chip must carry a non-empty
    company/product member, a source member and a date member. Producer half,
    right by construction: a SYNTH final rule whose store row names a company
    (cik), a product and a source URL goes through compute_policy_calendar and
    format_policy_reg_chip; the chip the producer emits must carry those three
    families back. PROVEN needs both halves; dated-at-theme-level only is
    PARTIAL; no chip at all is ABSENT.
    """
    import pandas as pd
    from engine.policy_calendar import compute_policy_calendar, format_policy_reg_chip

    cascade = _cascade()
    themes = cascade.get("themes") or []
    chips = [t.get("policy_reg_chip") for t in themes if t.get("policy_reg_chip")]
    union = sorted(set().union(*(sorted(c) for c in chips))) if chips else []
    chip_fams = [_exposure_families(c) for c in chips]
    chips_complete = sum(1 for f in chip_fams if all(f.values()))
    dated = sum(1 for f in chip_fams if f["date"])

    row = _synth_row(
        "SYNTH-FR-010", "RULE", "Final rule; synthetic widget tariff", "final_rule", 1.5,
        "2026-11-20", publication="2026-10-01",
        company_id="cik:0000000001", product="SYNTH widget",
        source_url="https://synth.invalid/SYNTH-FR-010",
    )
    result = compute_policy_calendar(df=pd.DataFrame([row]), today=TODAY)
    producer_chip = format_policy_reg_chip(result["themes"]["synth_policy_theme"], "synth_policy_theme") or {}
    producer_fam = _exposure_families(producer_chip)
    producer_complete = all(producer_fam.values())
    producer_missing = sorted(k for k, v in producer_fam.items() if not v)

    if chips and chips_complete == len(chips) and producer_complete:
        verdict = "PROVEN"
    elif chips and dated:
        verdict = "PARTIAL"
    else:
        verdict = "ABSENT"
    evidence = (
        f"committed cascade: {len(chips)}/{len(themes)} theme rows carry policy_reg_chip "
        f"({len(union)} keys), {chips_complete}/{len(chips)} carry company/product+source+date, "
        f"{dated}/{len(chips)} dated; producer: SYNTH row naming cik+product+source_url -> chip "
        f"drops {','.join(producer_missing) or 'nothing'} (exposure unit is the theme); "
        f"engine/policy_calendar.py:223 engine/foresight_cascade.py:669 "
        f"scripts/build_foresight.py:332 no-test"
    )
    return verdict, evidence


# ----------------------------------------------------------------------- P3 ----
def p3_alternatives_falsifiers() -> tuple[str, str]:
    """Alternatives and falsifiers for the policy chain: cascade + producer scan.

    Ceiling PARTIAL by construction: no producer exposes an alternative or
    falsifier surface that a SYNTH input could exercise with a known answer, so
    this probe can only observe whether such a member exists (artifact keys and
    non-comment producer source). Comment lines are excluded from the source
    scan so a remark cannot promote the line.
    """
    cascade = _cascade()
    themes = cascade.get("themes") or []
    key_hits = sorted({k for k in _walk_keys(cascade) if FALSIFIER_STEMS.search(k)})
    producers = (
        "engine/policy_calendar.py",
        "engine/foresight_cascade.py",
        "scripts/build_foresight.py",
    )
    source_hits = {}
    for rel in producers:
        code_lines = [
            ln for ln in (ROOT / rel).read_text(encoding="utf-8").splitlines()
            if not ln.lstrip().startswith("#")
        ]
        source_hits[rel] = len(FALSIFIER_STEMS.findall("\n".join(code_lines)))
    folded = sum(1 for t in themes if "policy pipeline:" in (t.get("rationale") or ""))
    total = len(key_hits) + sum(source_hits.values())
    verdict = "PARTIAL" if total else "ABSENT"
    evidence = (
        f"recursive key scan of committed cascade ({len(themes)} themes + top level): "
        f"{len(key_hits)} alternative/falsifier members; non-comment producer source hits "
        f"{sum(source_hits.values())} stem matches across {len(producers)} files; policy "
        f"text folds into rationale as an assertion in {folded}/{len(themes)} themes "
        f"(engine/foresight_cascade.py:602) no-test"
    )
    return verdict, evidence


# ----------------------------------------------------------------------- P4 ----
def p4_contract_condition() -> tuple[str, str]:
    """Conditional mechanism in the contract: enum + closed templates + channel rule.

    Positive: the committed news_event_class enum admits the policy classes and
    the channel-library runtime fires T2-AWARD-POLICY as a when-conjunction on a
    SCHEMA-VALID SYNTH policy event (a committed worked case re-keyed to the
    policy class), assigning the rule's own channel/role. Discriminating
    negatives: the same event without the policy class does not fire the rule,
    and an incidental issuer role is ineligible. Lifecycle half: a SYNTH
    policy_stage member must be refused by the SELECTED template's own branch
    (not by the sibling templates it never matched).
    """
    from jsonschema import Draft202012Validator

    from engine.news_impact.mechanisms import load_library, map_event

    schema = json.loads(
        (ROOT / "contracts" / "news_impact" / "news_impact_event.v1.schema.json")
        .read_text(encoding="utf-8")
    )
    library = load_library(ROOT / "contracts" / "news_impact" / "channel_library.v1.json")
    full_validator = Draft202012Validator(schema)

    class_def = schema["$defs"]["news_event_class"]
    class_validator = Draft202012Validator(class_def)
    enum_ok = class_validator.is_valid("policy_trade_control") and class_validator.is_valid(
        "regulatory_probe"
    )

    template = "demand_guidance_contract_event.v1"
    template_names = (
        "capital_allocation_event.v1",
        template,
        "strategic_product_partnership_event.v1",
    )
    lifecycle_members = sorted(
        f"{name}:{prop}"
        for name in template_names
        for prop in schema["$defs"][name]["properties"]
        if re.search(r"policy|lifecycle", prop) or (prop.endswith("_stage") and "demand" not in prop)
    )

    # Schema-valid base: the committed worked case W3 (a demand/guidance event),
    # re-keyed to the policy class the rule names. Validity is asserted, not assumed.
    worked = json.loads(
        (ROOT / "contracts" / "news_impact" / "cases" / "worked_cases.json").read_text(encoding="utf-8")
    )
    base = next(r["instance"] for r in worked if r["id"] == "W3")
    synth = {
        **base,
        "fact_id": "fact_000000000000000000000f04",
        "issuer_role": "subject",
        "demand_stage": "bookings",
        "metric": "revenue",
        "commitment_status": "announced",
        "revision_direction": "awarded",
        "news_event_class": "policy_trade_control",
    }
    fixture_valid = base.get("schema") == template and full_validator.is_valid(synth)

    # Branch-scoped validator: the selected template only, so sibling templates
    # that never matched cannot inflate the refusal count.
    branch_schema = {k: v for k, v in schema.items() if k != "oneOf"}
    branch_schema["$ref"] = f"#/$defs/{template}"
    branch_validator = Draft202012Validator(branch_schema)

    def refusal_count(event: dict) -> int:
        return sum(
            1 for err in branch_validator.iter_errors(event)
            if err.validator == "additionalProperties" and "policy_stage" in err.message
        )

    with_stage = refusal_count({**synth, "policy_stage": "proposed_rule"})
    without_stage = refusal_count(dict(synth))
    stage_refused = with_stage > without_stage

    rule = next(
        r for r in library["mapping_rules"] if r.get("rule_id") == "T2-AWARD-POLICY"
    )
    assign = (rule.get("assign") or [{}])[0]
    chan_id, chan_role = assign.get("id"), assign.get("role")

    payload = map_event(dict(synth), library=library).to_dict()
    fired = "T2-AWARD-POLICY" in payload["rule_ids"]
    assigned_as_stated = {"id": chan_id, "role": chan_role} in payload["assigned_channels"]
    # Discriminating negatives: drop the policy class, or make the issuer role
    # incidental — the when-conjunction must stop firing the policy rule.
    variants = {
        "customer_win": {**synth, "news_event_class": "customer_win"},
        "incidental_role": {**synth, "issuer_role": "incidental"},
    }
    silent = sorted(
        name for name, variant in variants.items()
        if "T2-AWARD-POLICY" not in map_event(variant, library=library).to_dict()["rule_ids"]
    )
    negatives_kept_distinct = len(silent) == len(variants)

    condition_ok = (
        enum_ok and fixture_valid and fired and assigned_as_stated and negatives_kept_distinct
    )
    lifecycle_ok = bool(lifecycle_members) and not stage_refused
    if condition_ok and lifecycle_ok:
        verdict = "PROVEN"
    elif condition_ok or lifecycle_ok:
        verdict = "PARTIAL"
    else:
        verdict = "ABSENT"
    evidence = (
        f"policy classes in enum={enum_ok}; schema-valid policy fixture={fixture_valid}; "
        f"lifecycle members={len(lifecycle_members)} (policy_stage SYNTH refused by the "
        f"{template} branch {with_stage}x, {without_stage}x without); T2-AWARD-POLICY "
        f"fired={fired} -> {chan_id}/{chan_role} assigned={assigned_as_stated}; silent on "
        f"{','.join(silent) or 'none'} of {len(variants)} negatives; "
        f"contracts/news_impact/news_impact_event.v1.schema.json:1577 "
        f"contracts/news_impact/channel_library.v1.json:1099 "
        f"engine/news_impact/mechanisms.py:961 tests/test_news_impact_mechanisms.py:458"
    )
    return verdict, evidence


# ----------------------------------------------------------------------- P5 ----
def p5_consumer_conditional() -> tuple[str, str]:
    """Theme + MarketOntology consumers: conditional mechanism vs asserted fact.

    Theme half: EVERY committed per-theme policy line must carry conditional
    form and none a causal verb. MarketOntology half: a real import edge (ast,
    not substring) from a module under engine/market_ontology to a policy-lane
    module. PROVEN needs all three; causal-free but unconditional lines with no
    consumer edge is PARTIAL.
    """
    import ast

    html = (ROOT / REQUIRED_ARTIFACTS[1]).read_text(encoding="utf-8")
    policy_lines = re.findall(r"policy pipeline: [^<\"]*", html)
    conditional = re.compile(r"\b(if|unless|conditional|contingent|would|could)\b", re.IGNORECASE)
    causal = re.compile(r"\b(will|boost|benefit|benefits|drive|drives|driven|because|causes)\b", re.IGNORECASE)
    n_conditional = sum(1 for line in policy_lines if conditional.search(line))
    n_causal = sum(1 for line in policy_lines if causal.search(line))
    all_conditional = bool(policy_lines) and n_conditional == len(policy_lines)
    asserted_blurb = html.count("money lands")

    ontology_dir = ROOT / "engine" / "market_ontology"
    ontology_files = sorted(ontology_dir.rglob("*.py"))
    edge_files: list[str] = []
    for path in ontology_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
        if any(m == lane or m.startswith(lane + ".") for m in modules for lane in POLICY_LANE_MODULES):
            edge_files.append(path.name)

    if policy_lines and n_causal == 0 and all_conditional and edge_files:
        verdict = "PROVEN"
    elif policy_lines and n_causal == 0:
        verdict = "PARTIAL"
    else:
        verdict = "ABSENT"
    missing = [
        label for label, ok in (
            ("conditional form on every line", all_conditional),
            ("MarketOntology import edge", bool(edge_files)),
        ) if not ok
    ]
    evidence = (
        f"committed page: {len(policy_lines)} 'policy pipeline:' theme lines, causal verbs="
        f"{n_causal}, conditional lines={n_conditional}/{len(policy_lines)}, panel asserts "
        f"lead-time {asserted_blurb}x ('before money lands'); MarketOntology import edges to "
        f"policy-lane modules={len(edge_files)} across {len(ontology_files)} files"
        f"{' (' + ','.join(edge_files) + ')' if edge_files else ''}; missing: "
        f"{'; '.join(missing) or 'nothing'}; scripts/build_foresight.py:340 "
        f"engine/market_ontology/exposure_map.py:19 tests/test_policy_calendar.py:246"
    )
    return verdict, evidence


# ---------------------------------------------------------------------- main ----
PROPERTIES = (
    p1_stage_states,
    p2_dated_exposure,
    p3_alternatives_falsifiers,
    p4_contract_condition,
    p5_consumer_conditional,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scratch",
        default=None,
        help="directory for all artifacts (this proof writes none)",
    )
    args = parser.parse_args()
    if args.scratch:
        Path(args.scratch).mkdir(parents=True, exist_ok=True)

    # The calendar's forward-ledger appender is lane-gated on COLLECT_LANE/US_LANE
    # (engine/policy_calendar.py:_append_ledger). The harness strips both before
    # running this proof; pop them here too so no ambient lane variable can make
    # the producer write data/ during P1.
    for lane_var in ("COLLECT_LANE", "US_LANE"):
        os.environ.pop(lane_var, None)

    tally = {"PROVEN": 0, "PARTIAL": 0, "ABSENT": 0, "HUMAN_GATE": 0}
    for number, proof in enumerate(PROPERTIES, start=1):
        verdict, evidence = proof()
        tally[verdict] += 1
        print(f"V4 P{number} {verdict} {evidence}")
    print(
        f"V4 SUMMARY proven={tally['PROVEN']} partial={tally['PARTIAL']} "
        f"absent={tally['ABSENT']} human_gate={tally['HUMAN_GATE']} "
        f"rung=COMMITTED_ARTIFACT"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
