"""Section 11 report assembler: synthetic inputs only, the committed registration, eval_grade's
own fixtures. No filing text, figures or names appear here; quantities are synthetic ints."""
from __future__ import annotations

import json
import types
from pathlib import Path

import pytest

from engine.news_impact import eval_receipt as er
from engine.news_impact import section11_registration as s11
from engine.news_impact import section11_report as rep

ROOT = Path(__file__).resolve().parents[1]
REG_PATH = ROOT / s11.DEFAULT_OUT
T1 = "capital_allocation_event.v1"


# ---------------------------------------------------------------- fixtures (copied from eval_grade tests)

def field_absence(reason: str, subject: str = "slot") -> dict:
    return {
        "schema": "field_absence.v1",
        "authority": "context_only",
        "reason": reason,
        "subject": subject,
        "detail": "test fixture",
        "missing_fields": [subject],
    }


def span_evidence(quote: str) -> dict:
    return {"claimed_quote": quote, "span": {"schema": "source_span.v1", "span_id": "span_" + "0" * 20}}


def point_qty(value, *, quote="a stated amount", unit="USD", currency="USD", basis="incremental",
              period=None, negated=False, bound="exact", evidence=True):
    if period is None:
        period = {"year": 2026, "quarter": 3, "calendar_end": None, "period_kind": "quarter"}
    q = {
        "form": "point",
        "value": value,
        "bound": bound,
        "unit": unit,
        "currency": currency,
        "basis": basis,
        "period": period,
        "negated": negated,
    }
    if evidence:
        q["evidence"] = span_evidence(quote)
    return q


def absent_qty(reason="not_stated"):
    return {"form": "absent", "absence": field_absence(reason)}


@pytest.fixture(scope="module")
def registration() -> dict:
    return json.loads(REG_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def registry():
    return er.load_registry()


@pytest.fixture
def eligible(monkeypatch):
    """The committed v1 registration is historical; make the loaded code match it."""
    monkeypatch.setattr(s11, "current_code_versions", lambda: dict(s11.HISTORICAL_V1_CODE_VERSIONS))


def _cases(registration):
    fields = registration["populations"]["v2_match"]["row_fields"]
    return {r[0]: dict(zip(fields, r)) for r in registration["populations"]["v2_match"]["rows"]}


def _pick(registration, template, n, *, audit=False):
    cases = _cases(registration)
    audit_ids = set(registration["draws"]["frontier_only_audit"]["v2_match_case_ids"])
    out = [c for c in sorted(cases.values(), key=lambda c: c["case_id"])
           if c["template"] == template and ((c["case_id"] in audit_ids) == audit or not audit)]
    assert len(out) >= n, (template, n)
    return out[:n]


def _fields(template):
    return rep._template_fields(template)


def _fill(inp, registration, construction, disposition="deferred"):
    """Give every remaining manifest case of `construction` one disposition so accounting
    can be complete (the frontier audit manifest is the 13-case draw)."""
    cases = _cases(registration)
    manifest = set(cases)
    if construction == "frontier_only_audit":
        manifest = set(registration["draws"]["frontier_only_audit"]["v2_match_case_ids"])
    have = {r["case_id"] for r in inp["sut_rows"] if r["construction"] == construction}
    for cid in sorted(manifest - have):
        inp["sut_rows"].append({"case_id": cid, "construction": construction, "disposition": disposition,
                                "novelty": None, "quantities": {}})
        inp["case_groups"].setdefault(cid, f"g_{cid}")
        inp["case_issuers"].setdefault(cid, f"i_{cid}")
    return inp


def _inputs(registration, *, rows=None, gold=None, routing=None, transfer=None, costs=None,
            calibration=None, w2=None, groups=None, issuers=None, full=True):
    if full:
        picked = sorted(_cases(registration).values(), key=lambda c: c["case_id"])
    else:
        picked = _pick(registration, "T1", 3) + _pick(registration, "T2", 2) + _pick(registration, "T3", 1)
    if gold is None:
        gold = []
        for c in picked:
            for f in _fields(c["template"]):
                gold.append({"case_id": c["case_id"], "field": f, "status": "agreed", "quantity": point_qty(7)})
    if rows is None:
        rows = []
        for c in picked:
            rows.append({
                "case_id": c["case_id"],
                "construction": "proposed_cascade",
                "disposition": "auto_published",
                "novelty": "restatement",
                "quantities": {f: point_qty(7) for f in _fields(c["template"])},
            })
    cids = sorted({r["case_id"] for r in rows} | {g["case_id"] for g in gold} | {c["case_id"] for c in picked})
    if groups is None:
        groups = {cid: f"g_{cid}" for cid in cids}
    if issuers is None:
        issuers = {cid: f"i_{cid}" for cid in cids}
    if routing is None:
        routing = [
            {"case_id": c["case_id"], "construction": "proposed_cascade", "metric": "material_routing",
             "outcome": "hit", "fold": c["fold"], "source": "routing_verdicts", "template": c["template"]}
            for c in picked
        ]
    if transfer is None:
        transfer = [
            {"case_id": c["case_id"], "construction": "proposed_cascade", "outcome": "no",
             "fold": c["fold"], "template": c["template"]}
            for c in picked
        ]
    if costs is None:
        costs = [{"construction": "proposed_cascade", "tokens_in": 1000, "tokens_out": 200, "calls": 6, "frontier_calls": 0}]
    return {
        "sut_rows": rows,
        "gold_slots": gold,
        "case_groups": groups,
        "case_issuers": issuers,
        "routing_items": routing,
        "transfer_items": transfer,
        "costs": costs,
        "gold_calibration": calibration if calibration is not None else {},
        "w2_extraction": w2 if w2 is not None else {},
    }


def _view_row(report, metric, construction, stratum="all"):
    rows = report["view"]["all"] if stratum == "all" else report["view"]["strata"][stratum]
    hits = [r for r in rows if r["metric_id"] == metric and r["construction"] == construction]
    assert len(hits) == 1, (metric, construction, stratum, len(hits))
    return hits[0]


# ---------------------------------------------------------------- registration gate

def test_committed_registration_is_refused_without_matching_code(registration):
    if s11.current_code_versions() == dict(s11.HISTORICAL_V1_CODE_VERSIONS):
        pytest.skip("loaded code matches the historical v1 registration")
    with pytest.raises(s11.RegistrationError) as ei:
        rep.assemble(_inputs(registration), registration)
    assert ei.value.code == "REGISTERED_IMPLEMENTATION_MISMATCH"


def test_drifted_code_is_refused_even_when_otherwise_eligible(registration, monkeypatch):
    drifted = dict(s11.HISTORICAL_V1_CODE_VERSIONS)
    drifted["producer_facts"] = drifted["producer_facts"] + "-x"
    monkeypatch.setattr(s11, "current_code_versions", lambda: drifted)
    with pytest.raises(s11.RegistrationError) as ei:
        rep.assemble(_inputs(registration), registration)
    assert ei.value.code == "REGISTERED_IMPLEMENTATION_MISMATCH"


@pytest.mark.parametrize("mutate,code", [
    (lambda r: r.update(schema="other"), "BAD_REGISTRATION"),
    (lambda r: r.update(registration_version="ni-section11-registration-9"), "BAD_REGISTRATION"),
    (lambda r: r.pop("draws"), "BAD_REGISTRATION"),
])
def test_bad_registration_codes(registration, eligible, mutate, code):
    reg = json.loads(json.dumps(registration))
    mutate(reg)
    with pytest.raises(rep.ReportError) as ei:
        rep.assemble(_inputs(registration), reg)
    assert ei.value.code == code


def test_mutated_registration_is_refused_by_the_historical_hash(registration, eligible):
    reg = json.loads(json.dumps(registration))
    reg["a3_registration"]["endpoints_sha256"] = "0" * 64
    with pytest.raises(s11.RegistrationError) as ei:
        rep.assemble(_inputs(registration), reg)
    assert ei.value.code == "HISTORICAL_REGISTRATION_CHANGED"


def test_endpoints_sha_mismatch(registration, registry, eligible):
    stand_in = types.SimpleNamespace(**{k: getattr(registry, k) for k in vars(registry)})
    stand_in.sha256 = "0" * 64
    with pytest.raises(rep.ReportError) as ei:
        rep.assemble(_inputs(registration), registration, registry=stand_in)
    assert ei.value.code == "ENDPOINTS_SHA_MISMATCH"
    assert registry.sha256[:12] in str(ei.value) and registry.sha256[:13] not in str(ei.value)


# ---------------------------------------------------------------- happy path

def test_assembles_and_self_checks(registration, registry, eligible):
    report = rep.assemble(_inputs(registration), registration)
    assert report["schema"] == rep.SCHEMA
    assert report["authority"] == "context_only"
    assert report["may_rank"] is False and report["may_size"] is False and report["may_gate"] is False
    assert report["registration"]["endpoints_sha256"] == registry.sha256
    assert report["populations"]["v2_match"]["n"] == 74
    pt = report["populations"]["v2_match"]["per_template"]
    assert pt["T1"] == {"n": 34, "shortfall_vs_200": 166}
    assert pt["T3"] == {"n": 4, "shortfall_vs_200": 196}
    assert report["populations"]["frontier_only_audit"]["n"] == 13
    assert report["gold"]["slots"]["registered"] == 142
    assert report["gold"]["slots"]["provided"] == 142
    assert report["gold"]["slots"]["gold_missing"] == 0
    assert report["correction_replay"] == {"status": "null_printed", "null_reason": "no_gold_correction_case"}
    assert report["cost"]["gold_labeling"]["null_reason"] == "no_usage_receipts"
    assert report["cost"]["system"]["proposed_cascade"]["total_tokens"] == 1200
    assert report["routing"]["label"] == "seat_only"
    assert report["routing"]["coverage_by_source"] == {"proposed_cascade": {"routing_verdicts": 74}}
    assert report["transfer"]["metric_id"] == "unsupported_ticker_to_supplier_count"
    assert report["receipts"]["all"]["schema"] == "eval_receipt.v1"
    assert set(report["receipts"]["strata"]) == {"T1", "T2", "T3"}
    # every graded slot correct -> 1.0 on the two populated critical populations for the cascade
    row = _view_row(report, "critical_numeric_correctness_auto_published", "proposed_cascade")
    assert row["value"] == 1.0 and row["n"] == 142 and row["n_clusters"] == 74
    assert row["status"] == "measured" and row["interval"] is not None and row["crossing"] == "meets"
    row = _view_row(report, "critical_numeric_correctness_all_dispositions", "proposed_cascade")
    assert row["value"] == 1.0 and row["n"] == 142 and row["status"] == "measured"
    # absence correctness has no gold-absent slot here
    row = _view_row(report, "absence_correctness", "proposed_cascade")
    assert row["status"] == "null_printed" and row["interval"] is None and row["value"] is None
    # routing recall 74/74
    row = _view_row(report, "material_event_routing_recall", "proposed_cascade")
    assert row["value"] == 1.0 and row["n"] == 74 and row["crossing"] == "meets"
    # unsupported transfer count 0, interval floored (too_small_at_600)
    row = _view_row(report, "unsupported_ticker_to_supplier_count", "proposed_cascade")
    assert row["value"] == 0 and row["interval"] is None
    assert row["interval_null_reason"] == rep.REPORTING_FLOOR_REASON
    # accounting complete, six-way sum printed
    row = _view_row(report, "disposition_accounting_complete", "proposed_cascade")
    assert row["value"] == 1.0 and row["six_way_sum"] == 74 and row["interval_null_reason"] == "not_a_rate"
    acct = report["system"]["constructions"]["proposed_cascade"]["accounting"]
    assert acct["manifest_n"] == 74 and acct["discovered"] == 74 and acct["auto_published"] == 74
    assert acct["unique_groups"] == 74 and acct["issuer_impacts"] == 74 and acct["evaluated"] == 74
    assert acct["complete"] is True
    # the cheap extractor ran nothing: null rows, accounting empty but complete
    row = _view_row(report, "critical_numeric_correctness_auto_published", "cheap_extractor_no_frontier")
    assert row["status"] != "measured" and row["value"] is None
    assert report["system"]["constructions"]["cheap_extractor_no_frontier"]["accounting"]["discovered"] == 0
    assert report["system"]["accounting_construction"] == "proposed_cascade"
    assert report["span_verification"] == "not_injected"
    rep.self_check(report)
    text = rep.render(report)
    assert "\n" in text and json.loads(text)["report_version"] == rep.SECTION11_REPORT_VERSION


def test_population_split_auto_published_vs_all_dispositions_vs_gold_absent(registration, eligible):
    t1 = _pick(registration, "T1", 3)
    f = _fields("T1")
    gold = []
    for c in t1:
        gold.append({"case_id": c["case_id"], "field": f[0], "status": "agreed", "quantity": point_qty(5)})
        gold.append({"case_id": c["case_id"], "field": f[1], "status": "adjudicated", "quantity": absent_qty()})
        gold.append({"case_id": c["case_id"], "field": f[2], "status": "null_printed", "null_reason": "no_third_value"})
    rows = [
        # auto-published, all correct (incl. absent agreed)
        {"case_id": t1[0]["case_id"], "construction": "proposed_cascade", "disposition": "auto_published",
         "novelty": "restatement", "quantities": {f[0]: point_qty(5), f[1]: absent_qty()}},
        # reviewed: value wrong, absence wrong (present where gold absent)
        {"case_id": t1[1]["case_id"], "construction": "proposed_cascade", "disposition": "reviewed_published",
         "novelty": "restatement", "quantities": {f[0]: point_qty(6), f[1]: point_qty(1)}},
        # deferred: value correct, absence correct
        {"case_id": t1[2]["case_id"], "construction": "proposed_cascade", "disposition": "deferred",
         "novelty": "restatement", "quantities": {f[0]: point_qty(5), f[1]: absent_qty()}},
    ]
    picked_ids = [c["case_id"] for c in t1]
    inp = _inputs(registration, rows=rows, gold=gold, routing=[], transfer=[], costs=[],
                  groups={cid: f"g_{cid}" for cid in picked_ids}, issuers={cid: f"i_{cid}" for cid in picked_ids})
    _fill(inp, registration, "proposed_cascade")
    report = rep.assemble(inp, registration)
    auto = _view_row(report, "critical_numeric_correctness_auto_published", "proposed_cascade")
    assert auto["n"] == 2 and auto["value"] == 1.0
    alld = _view_row(report, "critical_numeric_correctness_all_dispositions", "proposed_cascade")
    assert alld["n"] == 6 and alld["value"] == pytest.approx(4 / 6)
    absn = _view_row(report, "absence_correctness", "proposed_cascade")
    assert absn["n"] == 3 and absn["value"] == pytest.approx(2 / 3)
    slots = report["gold"]["slots"]
    assert slots["by_status"] == {"agreed": 3, "adjudicated": 3, "null_printed": 3}
    assert slots["null_by_reason"] == {"no_third_value": 3, "economic_refusal": 0}
    notes = report["system"]["constructions"]["proposed_cascade"]["note_prefix_counts"]
    assert sum(notes.values()) >= 1 and all(":" not in k for k in notes)
    acct = report["system"]["constructions"]["proposed_cascade"]["accounting"]
    assert (acct["auto_published"], acct["reviewed_published"], acct["deferred"]) == (1, 1, 72)
    assert acct["extracted_packets"] == 2 and acct["issuer_impacts"] == 2 and acct["evaluated"] == 3
    assert acct["discovered"] == 74 and acct["complete"] is True


def test_group_independence_hold_and_violation(registration, eligible):
    t1 = _pick(registration, "T1", 3)
    ids = [c["case_id"] for c in t1]
    groups = {ids[0]: "g_shared", ids[1]: "g_shared", ids[2]: "g_solo"}
    rows = [
        {"case_id": cid, "construction": "proposed_cascade", "disposition": "auto_published",
         "novelty": rep.NOVELTY_INDEPENDENCE, "quantities": {}}
        for cid in ids
    ]
    inp = _inputs(registration, rows=rows, gold=[], routing=[], transfer=[], costs=[], groups=groups,
                  issuers={cid: f"i_{cid}" for cid in ids})
    report = rep.assemble(inp, registration)
    row = _view_row(report, "root_source_independence_hold", "proposed_cascade")
    assert row["n"] == 2 and row["value"] == pytest.approx(0.5)
    assert report["system"]["constructions"]["proposed_cascade"]["n_multi_case_groups"] == 1
    assert report["system"]["constructions"]["proposed_cascade"]["accounting"]["unique_groups"] == 2
    # the same pair without the independence novelty on one member holds
    rows[1]["novelty"] = "restatement"
    report = rep.assemble(inp, registration)
    row = _view_row(report, "root_source_independence_hold", "proposed_cascade")
    assert row["value"] == 1.0


def test_t3_stratum_and_no_packet_baselines_are_null_by_name(registration, eligible):
    report = rep.assemble(_inputs(registration), registration)
    t3 = _view_row(report, "critical_numeric_correctness_auto_published", "proposed_cascade", "T3")
    assert t3["n"] == 4 and t3["value"] == 1.0 and t3["status"] == "not_estimable"
    assert t3["interval"] is None and t3["interval_null_reason"] == rep.REPORTING_FLOOR_REASON
    t1 = _view_row(report, "critical_numeric_correctness_auto_published", "proposed_cascade", "T1")
    assert t1["n"] == 102 and t1["n_clusters"] == 34 and t1["status"] == "measured"
    cns = _view_row(report, "critical_numeric_correctness_auto_published", "current_news_stack")
    assert cns["status"] == "null_printed" and cns["null_reason"] == "baseline_emits_no_packet"
    cns_r = _view_row(report, "material_event_routing_recall", "current_news_stack")
    assert cns_r["null_reason"] != "baseline_emits_no_packet"
    det = _view_row(report, "material_event_routing_recall", "deterministic_materiality_price_factor")
    assert det["status"] == "null_printed" and det["null_reason"] == "no_licensed_pit_price_factor_source"
    assert report["strata_accounting"]["T3"]["proposed_cascade"]["manifest_n"] == 4


def test_frontier_audit_manifest_and_off_subset(registration, eligible):
    audit = _pick(registration, "T1", 1, audit=True)[0]
    rows = [{"case_id": audit["case_id"], "construction": "frontier_only_audit", "disposition": "abstained",
             "novelty": None, "quantities": {}}]
    inp = _inputs(registration, rows=rows, gold=[], routing=[], transfer=[], costs=[],
                  groups={audit["case_id"]: "g"}, issuers={audit["case_id"]: "i"})
    _fill(inp, registration, "frontier_only_audit", "abstained")
    report = rep.assemble(inp, registration)
    acct = report["system"]["constructions"]["frontier_only_audit"]["accounting"]
    assert acct["manifest_n"] == 13 and acct["abstained"] == 13 and acct["complete"] is True
    assert report["system"]["constructions"]["proposed_cascade"]["accounting"]["complete"] is False
    assert report["system"]["accounting_construction"] == "frontier_only_audit"
    off = next(c for c in _cases(registration).values()
               if c["case_id"] not in registration["draws"]["frontier_only_audit"]["v2_match_case_ids"])
    rows[0]["case_id"] = off["case_id"]
    inp["case_groups"][off["case_id"]] = "g"
    inp["case_issuers"][off["case_id"]] = "i"
    with pytest.raises(rep.ReportError) as ei:
        rep.assemble(inp, registration)
    assert ei.value.code == "OFF_AUDIT_SUBSET"


def test_gold_calibration_and_w2_table(registration, eligible):
    inp = _inputs(registration, calibration={"w2_seat_audit": {"n": 20, "gold_wrong": 1}},
                  w2={"T1": {"correct": 10, "wrong_value": 2}})
    report = rep.assemble(inp, registration)
    cal = report["gold"]["calibration"]
    assert cal["w2_seat_audit"]["gold_wrong_rate"] == pytest.approx(0.05)
    assert cal["w2_seat_audit"]["interval"]["method"]
    assert cal["gold_agreed_audit"] == {"status": "null_printed", "null_reason": "audit_not_run"}
    assert report["w2_extraction"] == {"T1": {"correct": 10, "wrong_value": 2}}
    bad = _inputs(registration, calibration={"w2_seat_audit": {"n": 2, "gold_wrong": 3}})
    with pytest.raises(rep.ReportError) as ei:
        rep.assemble(bad, registration)
    assert ei.value.code == "BAD_COUNT"


def test_span_verifier_failure_counts_as_unevidenced(registration, eligible):
    report = rep.assemble(_inputs(registration), registration, span_verifier=lambda ev: False)
    assert report["span_verification"] == "injected"
    row = _view_row(report, "critical_numeric_correctness_auto_published", "proposed_cascade")
    assert row["value"] == 0.0 and row["n"] == 142 and row["crossing"] == "below"


# ---------------------------------------------------------------- refusal codes

def _mut(inp, path, value):
    cur = inp
    for p in path[:-1]:
        cur = cur[p]
    cur[path[-1]] = value
    return inp


@pytest.mark.parametrize("path,value,code", [
    (("sut_rows", 0, "case_id"), "ffffffffffffffff", "UNKNOWN_CASE"),
    (("sut_rows", 0, "construction"), "current_news_stack", "UNKNOWN_CONSTRUCTION"),
    (("sut_rows", 0, "disposition"), "published", "UNKNOWN_DISPOSITION"),
    (("sut_rows", 0, "quantities"), {"unregistered_amount": None}, "UNKNOWN_FIELD"),
    (("sut_rows", 0, "quantities"), 3, "BAD_ROW"),
    (("gold_slots", 0, "case_id"), "ffffffffffffffff", "UNKNOWN_CASE"),
    (("gold_slots", 0, "field"), "stated_quantity", "UNKNOWN_FIELD"),
    (("gold_slots", 0, "status"), "guessed", "BAD_GOLD_STATUS"),
    (("gold_slots", 0, "status"), "null_printed", "BAD_GOLD_STATUS"),
    (("gold_slots", 0, "quantity"), {"form": "point"}, "GOLD_SLOT_MALFORMED"),
    (("routing_items", 0, "construction"), "deterministic_materiality_price_factor", "UNKNOWN_CONSTRUCTION"),
    (("routing_items", 0, "outcome"), "maybe", "BAD_OUTCOME"),
    (("routing_items", 0, "metric"), "unsupported_transfer", "BAD_OUTCOME"),
    (("routing_items", 0, "fold"), "f9", "BAD_FOLD"),
    (("routing_items", 0, "template"), "T4", "UNKNOWN_TEMPLATE"),
    (("routing_items", 0, "source"), "seat_memory", "UNKNOWN_ROUTING_SOURCE"),
    (("transfer_items", 0, "outcome"), "unsure", "BAD_OUTCOME"),
    (("transfer_items", 0, "construction"), "current_news_stack", "UNKNOWN_CONSTRUCTION"),
    (("costs", 0, "tokens_in"), -1, "BAD_COUNT"),
    (("costs", 0, "construction"), "current_news_stack", "UNKNOWN_CONSTRUCTION"),
    (("w2_extraction",), {"T9": {}}, "UNKNOWN_TEMPLATE"),
])
def test_refusal_codes(registration, eligible, path, value, code):
    inp = _mut(_inputs(registration), path, value)
    with pytest.raises(rep.ReportError) as ei:
        rep.assemble(inp, registration)
    assert ei.value.code == code


@pytest.mark.parametrize("key,code", [
    ("sut_rows", "DUPLICATE_ROW"),
    ("gold_slots", "DUPLICATE_SLOT"),
    ("routing_items", "DUPLICATE_ROUTING"),
    ("transfer_items", "DUPLICATE_TRANSFER"),
    ("costs", "DUPLICATE_COST"),
])
def test_duplicate_codes(registration, eligible, key, code):
    inp = _inputs(registration)
    inp[key] = inp[key] + [json.loads(json.dumps(inp[key][0]))]
    with pytest.raises(rep.ReportError) as ei:
        rep.assemble(inp, registration)
    assert ei.value.code == code


def test_cluster_missing_and_no_rows(registration, eligible):
    inp = _inputs(registration)
    cid = inp["sut_rows"][0]["case_id"]
    del inp["case_groups"][cid]
    with pytest.raises(rep.ReportError) as ei:
        rep.assemble(inp, registration)
    assert ei.value.code == "CLUSTER_MISSING" and cid in str(ei.value)
    empty = _inputs(registration)
    empty["sut_rows"] = []
    with pytest.raises(rep.ReportError) as ei:
        rep.assemble(empty, registration)
    assert ei.value.code == "NO_SYSTEM_ROWS"


def test_refusal_messages_carry_no_values(registration, eligible):
    inp = _inputs(registration)
    inp["gold_slots"][0]["quantity"] = {"form": "point", "value": 123456789}
    with pytest.raises(rep.ReportError) as ei:
        rep.assemble(inp, registration)
    assert "123456789" not in str(ei.value)


def test_self_check_rejects_forbidden_keys_and_words(registration, eligible):
    report = rep.assemble(_inputs(registration), registration)
    bad = json.loads(json.dumps(report))
    bad["confidence_note"] = "x"
    with pytest.raises(rep.ReportError) as ei:
        rep.self_check(bad)
    assert ei.value.code == "FORBIDDEN_KEY"
    bad = json.loads(json.dumps(report))
    bad["disclosures"].append("this proves the thesis")
    with pytest.raises(er.EvalReceiptError):
        rep.self_check(bad)


# ---------------------------------------------------------------- CLI

def test_cli_writes_once_and_refuses_overwrite(registration, eligible, tmp_path, capsys):
    inputs = tmp_path / "inputs.json"
    inputs.write_text(json.dumps(_inputs(registration)), encoding="utf-8")
    out = tmp_path / "report.json"
    assert rep.main(["--inputs", str(inputs), "--out", str(out)]) == 0
    assert "report ok" in capsys.readouterr().out
    body = json.loads(out.read_text(encoding="utf-8"))
    assert body["schema"] == rep.SCHEMA and len(body["inputs_sha256"]) == 64
    assert rep.main(["--inputs", str(inputs), "--out", str(out)]) == 1
    assert "OUT_EXISTS" in capsys.readouterr().err


def test_cli_reports_registration_refusal(tmp_path, capsys, registration, monkeypatch):
    if s11.current_code_versions() == dict(s11.HISTORICAL_V1_CODE_VERSIONS):
        drifted = dict(s11.HISTORICAL_V1_CODE_VERSIONS)
        drifted["sampler"] += "-x"
        monkeypatch.setattr(s11, "current_code_versions", lambda: drifted)
    inputs = tmp_path / "inputs.json"
    inputs.write_text(json.dumps(_inputs(registration)), encoding="utf-8")
    out = tmp_path / "report.json"
    assert rep.main(["--inputs", str(inputs), "--out", str(out)]) == 1
    assert "REGISTERED_IMPLEMENTATION_MISMATCH" in capsys.readouterr().err
    assert not out.exists()
