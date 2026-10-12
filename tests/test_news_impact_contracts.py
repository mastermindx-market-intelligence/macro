"""Phase 0 freeze contract tests for contracts/news_impact/news_impact_event.v1.schema.json.

Hermetic: stdlib + pytest + jsonschema only, plus the owner modules
engine.company_intelligence.documents / events (provided on PYTHONPATH).
No data/ reads, no network, no subprocess. Runs under jsonschema 4.10 and 4.26.
"""
import copy
import json
import re
import sys
from hashlib import sha256
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from engine.company_intelligence import documents, events

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "contracts" / "news_impact" / "news_impact_event.v1.schema.json"
CASES_DIR = ROOT / "contracts" / "news_impact" / "cases"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
DEFS = SCHEMA["$defs"]
TEMPLATES = ("capital_allocation_event.v1", "demand_guidance_contract_event.v1",
             "strategic_product_partnership_event.v1")


def resolve_ref(ptr):
    node = SCHEMA
    for part in ptr.lstrip("#/").split("/"):
        node = node[part.replace("~1", "/").replace("~0", "~")]
    return node


def template_validator(template):
    """The harness idiom: the whole schema minus oneOf, pointed at one template."""
    doc = copy.deepcopy(SCHEMA)
    doc.pop("oneOf", None)
    doc["$ref"] = f"#/$defs/{template}"
    return Draft202012Validator(doc)


def sub_validator(ref):
    return Draft202012Validator({"$ref": f"#/$defs/{ref}", "$defs": DEFS})


TOP = Draft202012Validator(SCHEMA)
TV = {t: template_validator(t) for t in TEMPLATES}


def validate(row):
    """Return (verdict, first_error) for one fixture row."""
    tmpl, inst = row["template"], row["instance"]
    v = TOP if tmpl == "$" else (TV[tmpl[6:]] if tmpl.startswith("$defs.") else TV[inst["schema"]])
    errs = sorted(v.iter_errors(inst), key=lambda e: list(map(str, e.absolute_path)))
    return ("ACCEPT" if not errs else "REJECT"), (errs[0] if errs else None)


def load_cases(name):
    return json.loads((CASES_DIR / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 1. schema valid
def test_check_schema():
    Draft202012Validator.check_schema(SCHEMA)
    assert SCHEMA["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert SCHEMA["$id"] == ("https://mastermind-x.com/contracts/news_impact/"
                             "news_impact_event.v1.schema.json")


# ---------------------------------------------------------------- 2. closedness
FRAGMENTS = ("if", "then", "else", "allOf", "anyOf", "oneOf", "not")


def _walk_closed(node, path, open_nodes, unbounded):
    """Descend through properties only; if/then/allOf/... are fragments of closed parents."""
    if not isinstance(node, dict):
        return
    if "$ref" in node:
        return
    for name, prop in node.get("properties", {}).items():
        merged = dict(prop)
        if "$ref" in prop:  # 2020-12: siblings merge additively with the target
            target = dict(resolve_ref(prop["$ref"]))
            target.update({k: v for k, v in prop.items() if k != "$ref"})
            merged = target
        types = merged.get("type")
        types = types if isinstance(types, list) else ([types] if types else [])
        if "string" in types and not any(k in merged for k in ("maxLength", "enum", "const")):
            pat = merged.get("pattern", "")
            # Bounded means no unbounded free text: maxLength/enum/const, or an
            # anchored pattern with only fixed repetition (pins length). The
            # literal "pattern+maxLength" reading fails 5 frozen base nodes
            # (supersedes_fact_id x4, calendar_end) whose anchored patterns
            # already pin the length; the freeze base is not editable here.
            anchored = (pat.startswith("^") and pat.endswith("$")
                        and not re.search(r"[*+]|\{\d+,\}", pat))
            if not anchored:
                unbounded.append(f"{path}.{name}")
        if "properties" in merged or merged.get("type") == "object":
            if merged.get("additionalProperties") is not False:
                open_nodes.append(f"{path}.{name}")
        _walk_closed(prop, f"{path}.{name}", open_nodes, unbounded)
    if "properties" in node or node.get("type") == "object":
        if node.get("additionalProperties") is not False:
            open_nodes.append(path)


def test_closedness_and_string_bounds():
    open_nodes, unbounded = [], []
    for name, d in DEFS.items():
        _walk_closed(d, f"$defs.{name}", open_nodes, unbounded)
    _walk_closed({k: v for k, v in SCHEMA.items() if k != "$defs"}, "$", open_nodes, unbounded)
    assert open_nodes == [], f"open object nodes: {open_nodes}"
    assert unbounded == [], f"unbounded string nodes: {unbounded}"


# ---------------------------------------------------------------- 3. forbidden names
FORBIDDEN = ("confidence", "probability", "score", "target", "fair_value", "rating", "price_target")


def _forbidden_hits():
    # Word-boundary match: "rating_change" is one snake_case token, not the
    # standalone token "rating"; a substring scan would flag ordinary English.
    hits = []
    pats = [(w, re.compile(rf"\b{re.escape(w)}\b", re.IGNORECASE)) for w in FORBIDDEN]

    def rec(node, path):
        if isinstance(node, dict):
            for key in list(node.get("properties", {})):
                for w, p in pats:
                    if p.search(key):
                        hits.append(f"property {path}.{key}: {w}")
            for key in list(node.get("$defs", {})):
                for w, p in pats:
                    if p.search(key):
                        hits.append(f"def {key}: {w}")
            for kw in ("enum", "const"):
                val = node.get(kw)
                vals = val if isinstance(val, list) else [val]
                for v in vals:
                    if isinstance(v, str):
                        for w, p in pats:
                            if p.search(v):
                                hits.append(f"{kw} {path}={v!r}: {w}")
            for k, v in node.items():
                if k not in ("properties", "$defs"):
                    rec(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                rec(v, f"{path}[{i}]")
    rec(SCHEMA, "$")
    return hits


def test_forbidden_names_absent():
    hits = _forbidden_hits()
    assert hits == [], f"forbidden names: {hits}"
    raw = SCHEMA_PATH.read_text(encoding="utf-8")
    for w in FORBIDDEN:
        assert not re.search(rf"\b{re.escape(w)}\b", raw, re.IGNORECASE), w
    # the frozen assumptions also ban these in the header description
    for w in ("contagion", "validated", "fair value", "price target"):
        assert w.lower() not in SCHEMA.get("description", "").lower(), w


# ---------------------------------------------------------------- 4. critical fields
CRITICAL = {
    "capital_allocation_event.v1": [
        "company_id", "issuer_role", "novelty", "action_type", "commitment_status",
        "primary_amount_role", "incremental_amount", "remaining_authorization",
        "executed_amount", "horizon_period", "negated", "action_span"],
    "demand_guidance_contract_event.v1": [
        "company_id", "issuer_role", "demand_stage", "metric", "commitment_status",
        "stated_amount", "fiscal_period", "revision_direction", "negated", "novelty",
        "counterparty_company_id", "baseline"],
    "strategic_product_partnership_event.v1": [
        "company_id", "issuer_role", "event_kind", "object_name", "commitment_status",
        "novelty", "counterparty_company_id", "counterparty_role", "stated_quantity",
        "economic_claim_class", "negated", "action_span"],
}
QUANTITY_SLOTS = {
    "capital_allocation_event.v1": ["incremental_amount", "remaining_authorization", "executed_amount"],
    "demand_guidance_contract_event.v1": ["stated_amount"],
    "strategic_product_partnership_event.v1": ["stated_quantity"],
}


def test_critical_fields():
    for template, names in CRITICAL.items():
        assert len(names) <= 12, (template, len(names))
        props = DEFS[template]["properties"]
        for name in names:
            assert name in props, (template, name)
        for slot in QUANTITY_SLOTS[template]:
            assert props[slot] == {"$ref": "#/$defs/quantity"}, (template, slot)


# ---------------------------------------------------------------- 5. shared defs
SHARED = ("quantity", "source_span_v1", "evidence_span", "field_absence.v1", "absence_union",
          "baseline", "novelty", "issuer_role", "commitment_status", "fiscal_period", "envelope")


def _ref_closure(def_name):
    seen, stack = set(), [DEFS[def_name]]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if "$ref" in node and node["$ref"].startswith("#/$defs/"):
                top = node["$ref"].split("/")[2]
                seen.add(top)
                stack.append(resolve_ref(node["$ref"]))
                stack.extend(v for k, v in node.items() if k != "$ref")
            else:
                stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return seen


def test_shared_defs_reachable_from_all_templates():
    present = [n for n in SHARED if n in DEFS]
    assert present == list(SHARED), f"missing from $defs: {set(SHARED) - set(present)}"
    for template in TEMPLATES:
        closure = _ref_closure(template)
        for name in present:
            assert name in closure, (template, name)


# ---------------------------------------------------------------- 6/7/8. fixtures
@pytest.mark.parametrize("row", load_cases("worked_cases.json"), ids=lambda r: r["id"])
def test_worked_cases_accept(row):
    verdict, err = validate(row)
    assert verdict == "ACCEPT", err


@pytest.mark.parametrize("row", load_cases("counterexamples.json"), ids=lambda r: r["id"])
def test_counterexamples_reject(row):
    assert row["expected"] == "REJECT" and row["rejection_label"], row["id"]
    verdict, err = validate(row)
    assert verdict == "REJECT", f"{row['id']} admitted"


@pytest.mark.parametrize("row", load_cases("projected_cases.json")
                         + [load_cases("owner_int_table_case.json")], ids=lambda r: r["id"])
def test_projected_and_owner_int_table_accept(row):
    verdict, err = validate(row)
    assert verdict == "ACCEPT", err


# ---------------------------------------------------------------- 9. attack battery
BATTERY = load_cases("attack_battery.json")
ADVERSARIAL, BENIGN = BATTERY["adversarial"], BATTERY["benign"]
QN = {"schema": "quarantine_note.v1", "authority": "context_only",
      "fact_id": "fact_000000000000000000000001", "quarantine_reason": "held for operator review"}
QV = sub_validator("quarantine_note.v1")


def _worked_map():
    w1 = copy.deepcopy(load_cases("worked_cases.json")[0]["instance"])
    assert w1["schema"] == "capital_allocation_event.v1"
    old_span = w1["action_span"]["span"]
    w1t = copy.deepcopy(w1)
    w1t["action_span"] = {
        "claimed_quote": "consolidated statement of cash flows, fiscal 2026 Q3",
        "span": {"schema": "source_span.v1", "authority": "context_only",
                 "span_id": old_span["span_id"], "document_id": old_span["document_id"],
                 "document_version": 1,
                 "locator": {"kind": "table_cell", "page": 7, "table": "CONSOLIDATED CASH FLOWS",
                             "row": 14, "column": 2, "cell_ref": "C15"},
                 "text_sha256": None, "display_excerpt": "share repurchases of common stock",
                 "rights_profile": "rp_public_primary_v1", "receipt_state": "address_only",
                 "receipt": None, "unreplayable_reason": "document_bytes_not_held"}}
    by_id = {r["id"]: r["instance"] for r in load_cases("worked_cases.json")}
    return {"W1": w1, "W1t": w1t, "W5": by_id["W5"], "R1": by_id["R1"], "QN": QN}


def _setleaf(doc, path, value):
    keys = path.replace("]", "").replace("[", ".[").split(".")
    node = doc
    for i, k in enumerate(keys):
        k = int(k[1:]) if k.startswith("[") else k
        if i == len(keys) - 1:
            node[k] = value
        else:
            nxt = keys[i + 1]
            nxt = int(nxt[1:]) if nxt.startswith("[") else nxt
            if isinstance(nxt, int):
                while len(node[k]) <= nxt:
                    node[k].append(None)
            node = node[k]


def _rejects(v, inst):
    return bool(list(v.iter_errors(inst)))


def test_attack_battery_replay():
    assert len(ADVERSARIAL) == 443 and len(BENIGN) == 154
    worked = _worked_map()
    vmap = {"capital_allocation_event.v1": TV["capital_allocation_event.v1"],
            "demand_guidance_contract_event.v1": TV["demand_guidance_contract_event.v1"],
            "strategic_product_partnership_event.v1": TV["strategic_product_partnership_event.v1"],
            "quarantine_note.v1": QV}
    admitted = []
    for row in ADVERSARIAL:  # rebuild each instance exactly as the harness injected it
        inst = copy.deepcopy(worked[row["case"]])
        leaf, payload = row["leaf"], row["payload"]
        if row["id"] == "V27":  # split instruction across two quote fields
            first, second = payload.split(" || ", 1)
            _setleaf(inst, "conditions_quote", first)
            _setleaf(inst, "consideration_quote", second)
        else:
            _setleaf(inst, leaf, payload)
        rejected = _rejects(vmap[_template_of(row, worked)], inst)
        if row["id"] == "V26":  # benign control: replay must match the recorded verdict
            if rejected != (row["copy"] == "REJECT"):
                admitted.append((row["id"], row["case"], leaf))
        elif not rejected:
            admitted.append((row["id"], row["case"], leaf))
    assert admitted == [], admitted

    false_rejects = []
    for row in BENIGN:
        case = "QN" if row["slot"] == "quarantine_reason" else row_leaf_case(row)
        tmpl = "quarantine_note.v1" if case == "QN" else worked[case]["schema"]
        inst = copy.deepcopy(worked[case])
        _setleaf(inst, row["leaf"], row["sentence"])
        if _rejects(vmap[tmpl], inst):
            false_rejects.append((row["slot"], row["id"]))
    assert false_rejects == [], false_rejects


def _template_of(row, worked):
    cid = row.get("case")
    if cid is None or cid == "QN":
        return "quarantine_note.v1"
    inst = worked.get(cid)
    return "quarantine_note.v1" if inst is None else inst["schema"]


def row_leaf_case(row):
    return {"claimed_quote_span": "W1", "claimed_quote_qty": "W1", "conditions_quote": "W1",
            "consideration_quote": "W1", "license_quote": "W5", "adoption_proxy_quote": "W5",
            "contrary_mechanism_quote": "W5", "display_excerpt": "W1", "unreplayable_reason": "W1t",
            "absence_detail": "W1"}[row["slot"]]


# ---------------------------------------------------------------- 10. live owner payloads
BODY = "NVIDIA Announces a $150 Billion Share Repurchase Authorization Increase."
URL_TEXT = "The exhibit is available at https://www.sec.gov/Archives/edgar/data/320193."
LONG_TEXT = (
    "Fiscal 2026 capital return: the company intends to repurchase shares from time to time in "
    "the open market or in privately negotiated transactions, subject to market conditions, and "
    "it expects the program to remain in place through the end of fiscal 2028 unless interrupted "
    "by the board of directors. The program may be executed through Rule 10b5-1 plans, open "
    "market purchases, privately negotiated transactions or any combination thereof, in each "
    "case in compliance with applicable securities laws, and the company has no obligation to "
    "repurchase the full amount, and the program may be suspended or discontinued at any time "
    "without prior notice.")


def _mint_text(doc_id, text, excerpt=None, version=1):
    return documents.text_span(
        document_id=doc_id, document_version=version,
        body_sha256=sha256(text.encode()).hexdigest(), segment_index=0,
        segment_text=text, start_byte=0, end_byte=len(text.encode()), text=text,
        display_excerpt=excerpt if excerpt is not None else text).to_payload()


EV = sub_validator("evidence_span")


def _span_wraps(span):
    return {"claimed_quote": BODY, "span": span}


def test_live_owner_payloads():
    # byte-replayed text span
    assert not list(EV.iter_errors(_span_wraps(_mint_text("doc_t1", BODY))))
    # address_only slide region + page
    slide = documents.address_only_span(
        document_id="doc_slides", document_version=1, kind="slide_region",
        address={"page": 12, "region": "upper_right"},
        unreplayable_reason="document_bytes_not_held").to_payload()
    assert not list(EV.iter_errors(_span_wraps(slide)))
    # INTEGER-table cell locator (owner spine test :414 shape) — G-OC1
    int_tbl = documents.address_only_span(
        document_id="doc_10q_cf", document_version=1, kind="table_cell",
        address={"page": 4, "table": 1, "row": 3, "column": 2},
        unreplayable_reason="document_bytes_not_held").to_payload()
    assert int_tbl["locator"]["table"] == 1
    assert not list(EV.iter_errors(_span_wraps(int_tbl)))
    # owner TypedAbsence-backed absence
    ta = documents.TypedAbsence(reason="missing_period", subject="stated_amount.period").to_payload()
    assert not list(sub_validator("absence_union").iter_errors(ta))
    # fiscal period payloads
    for payload in ({**events.FiscalPeriod(year=2026, quarter=3).to_payload(), "period_kind": "quarter"},
                    {**events.FiscalPeriod(year=2027, quarter=None).to_payload(), "period_kind": "fiscal_year"}):
        assert not list(sub_validator("fiscal_period").iter_errors(payload)), payload
    # URL-bearing excerpt: projected ACCEPT, unprojected REJECT (ruling R1)
    url_unproj = _mint_text("doc_url", URL_TEXT)
    assert list(EV.iter_errors(_span_wraps(url_unproj)))
    url_proj = dict(url_unproj, display_excerpt=None)
    assert not list(EV.iter_errors(_span_wraps(url_proj)))
    # over-500 excerpt: projected ACCEPT, unprojected REJECT (ruling R2)
    long_unproj = _mint_text("doc_long", LONG_TEXT, excerpt=LONG_TEXT)
    assert len(long_unproj["display_excerpt"]) > 500
    assert list(EV.iter_errors(_span_wraps(long_unproj)))
    long_proj = dict(long_unproj, display_excerpt=None)
    assert not list(EV.iter_errors(_span_wraps(long_proj)))
    # document_version 0 REJECT — text_span() does not gate the version (only
    # SourceDocument.revision does), so it is minted directly at 0.
    v0 = _mint_text("doc_v0", BODY, version=0)
    assert v0["document_version"] == 0
    assert list(EV.iter_errors(_span_wraps(v0)))
    # extra owner address key REJECT (ruling R4: keys are never stripped)
    sheet = documents.address_only_span(
        document_id="doc_tbl2", document_version=1, kind="table_cell",
        address={"page": 4, "table": 1, "row": 3, "column": 2, "sheet": "balance_sheet"},
        unreplayable_reason="document_bytes_not_held").to_payload()
    assert list(EV.iter_errors(_span_wraps(sheet)))


# ---------------------------------------------------------------- 11. absence enums
def test_absence_reason_envs_match_owner():
    owner = set(documents.ABSENCE_REASONS)
    fa = DEFS["field_absence.v1"]["properties"]["owner_reason"]["enum"]
    assert set(fa) == owner
    ota = DEFS.get("owner_typed_absence_v1", {}).get("properties", {}).get("reason", {}).get("enum")
    assert ota is not None, "owner_typed_absence_v1 carries a reason enum"
    assert set(ota) == owner


# ---------------------------------------------------------------- 12. F3 matrix
F3 = {"revenue": "total", "eps": "per_share", "bookings": "incremental",
      "backlog": "total", "units": "total"}
BASES = ("total", "incremental", "run_rate", "per_share", "percent")
BY_ID = {r["id"]: r["instance"] for r in load_cases("worked_cases.json")}


def _t2_from(base_id, metric, basis):
    inst = copy.deepcopy(BY_ID[base_id])
    inst["metric"] = metric
    inst["stated_amount"]["basis"] = basis
    return inst


def test_f3_metric_keyed_basis_consts():
    t2 = TV["demand_guidance_contract_event.v1"]
    assert BY_ID["W3"]["metric"] == "revenue" and BY_ID["W4"]["metric"] == "bookings"
    for metric, bound in F3.items():
        base_id = "W4" if metric == "bookings" else "W3"
        for basis in BASES:
            errs = list(t2.iter_errors(_t2_from(base_id, metric, basis)))
            if basis == bound:
                assert not errs, (metric, basis, errs[:1])
            else:
                assert errs, (metric, basis)
    for basis in BASES:  # metric 'other' gets no const
        assert not list(t2.iter_errors(_t2_from("W3", "other", basis))), basis
