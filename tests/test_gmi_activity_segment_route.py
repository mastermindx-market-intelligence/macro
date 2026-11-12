"""The SEC annual-report segment route into the EXISTING activity admission lane.

Synthetic owner fixtures only; no production admission, real-company ruling or
data/theme_graph write. Covers the route-extension commission's five checks:

1. Every existing committed row regenerates byte-identical with the change in
   place (the writer is the only thing that could change a row: the base-commit
   writer module is loaded and proven equal to the current writer for the C01
   planned_product_integration evidence with identical injected readers), the
   committed proposal rows still validate, and the bridge re-loads/validates the
   committed event + receipt files.
2. Form refusals (8-K / 10-Q / S-1 / press release) and span refusals
   (missing / zero-length).
3. The closed ``exposure`` block: an unknown key fails the contract; exposure on
   planned_product_integration evidence fails.
4. One fixture segment member through writer + bridge with a FIXTURE ruling
   (``allow_fixture``), pointed at a micro-theme; the #11150 tier guard still
   refuses a non-micro target for the segment species.
5. House rule v1 (0.07 share + product_line -> EXPOSURE_BELOW_HOUSE_RULE) and the
   curator exposure restatement (CURATION_EXPOSURE_MISMATCH).
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import types
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from engine.company_intelligence import issuer_disclosures as n
from engine.company_intelligence import issuer_disclosure_owner as o
from engine.company_intelligence import sec_segment_adoption as segment
from engine.earnings_release.receipts import receipt_for_char_span
from engine.theme_graph import activity_history_bridge as bridge
from engine.theme_graph import materialize, probation
from engine.theme_graph import membership_evidence as me
from tests.test_company_pinned_relationship_candidates import (
    fixture as pinned_fixture, inspect as pinned_inspect,
)

ROOT = Path(__file__).resolve().parents[1]
BASE_COMMIT = "7387e1f829b54c51de316a7ea74c066abdfcd24c"
CODE_VERSION = "0" * 40
C01_PROPOSAL_ID = "actprop:287edbf7e04b8aba873b7493"
TARGET = "theme:hbm_packaging"
SEG_NODE = "co:us:ALPHA"
SEG_ISSUER = "ISS:US-XNAS-ALPHA"
SEG_LINE = "Data Center Storage"
SEG_BODY = ("SYNTHETIC annual report. Aurora operates the Data Center Storage segment. "
            "Aurora buys Widget wafers from Boreal. Data Center Storage revenue and profit "
            "are disclosed.").encode("utf-8")
SEG_ACCESSION = "0000000001-24-000001"
KNOWLEDGE_CUTOFF = "2024-03-06T00:00:00Z"
CREATED = "2024-03-06T01:00:00Z"
DECIDED_AT = "2024-03-06T02:00:00Z"
RULING_RECORDED_AT = "2024-03-06T03:00:00Z"
RECORDED_AT = "2024-03-06T04:00:00Z"
CURATOR = "curator:gmi-desk"


def canon(value) -> bytes:
    return n._canonical(value)


def _git_show(path: str) -> bytes:
    return subprocess.run(["git", "show", f"origin/main:{path}"], cwd=ROOT,
                          capture_output=True, check=True).stdout


# ---------------------------------------------------------------------------
# Synthetic single-party segment owner fixture (mirrors sec_supplier_adoption)
# ---------------------------------------------------------------------------

def _segment_case(tmp_path, *, share_scope="segment", revenue=30.0, revenue_denominator=100.0,
                  profit=10.0, profit_denominator=100.0, profit_measure="operating_income",
                  fiscal_year=2023, form="10-K"):
    f = pinned_fixture(tmp_path / "native", body=SEG_BODY, form=form)
    receipt = receipt_for_char_span(source=SEG_BODY.decode("utf-8"),
                                    source_sha256=o.digest(SEG_BODY),
                                    char_start=0, char_end=len(SEG_BODY)).to_dict()
    # The pinned candidate's built-in span receipt is bound to the helper's default
    # body; rebind it to this segment body so native replay is INSPECTABLE. The
    # candidate assertion's labels (Aurora/Widget/Boreal) all occur in SEG_BODY.
    f.candidate["receipt"] = receipt
    inspection = pinned_inspect(f)
    assert inspection["inspection_status"] == "INSPECTABLE"
    identities = {"subject": {
        "schema": o.context.RECEIPT_SCHEMA, "identity_mode": "current",
        "issuer_id": SEG_ISSUER, "evidenced_cik": "0000000001", "source_commit": "a" * 40,
        "sources": {name: {"sha256": "b" * 64, "byte_length": 100} for name in o.IDENTITY_SOURCES},
        "evidence_source": "sec_company_tickers", "evidence_snapshot": "2024-02-01"}}
    assertion = {"subject_label": "Aurora", "disclosed_line": SEG_LINE, "share_scope": share_scope,
                 "revenue": revenue, "revenue_denominator": revenue_denominator,
                 "profit": profit, "profit_denominator": profit_denominator,
                 "profit_measure": profit_measure, "fiscal_year": fiscal_year}
    role_review = {"decision": "supported_segment_activity_in_selected_filing",
                   "source_sha256": receipt["source_sha256"], "span_sha256": receipt["span_sha256"],
                   "snapshot_id": inspection["native_source_binding"]["snapshot_id"],
                   "disclosed_line": SEG_LINE}
    prepared = segment.prepare_segment_input(
        inspection, assertion=assertion, receipt=receipt, identities=identities,
        identity_queries={"subject": "ALPHA"}, identity_observed_at="2024-03-03T10:00:00Z",
        reviewed_at="2024-03-03T11:00:00Z", role_review=role_review)
    e, fact = prepared["edition"], prepared["proposed_fact"]
    s = e["sec_source"]
    policy = {"schema": segment.POLICY_SCHEMA, "basis_id": "SYNTHETIC-SEGMENT-POLICY",
              "recorded_at": "2024-03-04T10:00:00Z", "reviewer": "synthetic fixture",
              "evidence_kind": "published_source_reuse_policy", "decision": "covered_for_described_use",
              "rights_family": "sec_public_filing_facts",
              "source_policy_evidence": [{"url": url, "section": "synthetic", "finding": "synthetic",
                                          "verification": "synthetic"} for url in segment.POLICY_URLS],
              "source": {"accession": s["accession"], "reporting_cik": s["issuer_cik"],
                         "archive_url": s["archive_url"], "raw_sha256": e["source_sha256"],
                         "byte_start": fact["span"]["start_byte"], "byte_end": fact["span"]["end_byte"],
                         "span_sha256": fact["span"]["text_sha256"]},
              "permitted_use": {"purpose": n.SEC_SUPPLIER_PURPOSE, "audience": n.SEC_SUPPLIER_AUDIENCE,
                                "paid_product_display": True, "fact_retention": True,
                                "source_attribution_required": True, "kind": "segment_activity",
                                "lifecycle": "reported", "subject": SEG_ISSUER,
                                "disclosed_line": SEG_LINE, "share_scope": share_scope,
                                "source_quotation": False, "source_body_export": False,
                                "reviewer_text": False},
              "scope_limits": ["SYNTHETIC fixture; no actual policy or production acceptance"]}
    theme = yaml.safe_dump({"families": {"sec_public_filing_facts":
                            {"rights_class": "derived_display_ok", "auth_class": "keyless_public"}}}).encode()
    spec = segment.adopt_segment_input(prepared, adopted_at="2024-03-05T10:00:00Z",
                                       ruling_raw=canon(policy), theme_sources_raw=theme,
                                       identity_observed_at="2024-03-03T10:00:00Z")
    registry = Path(o.REGISTRY_PATH).read_bytes()
    snapshot = o.qualify_records("a" * 40, canon(spec), canon(policy), registry, identities,
                                 theme_sources_raw=theme)
    return SimpleNamespace(pinned=f, inspection=inspection, receipt=receipt, identities=identities,
                           prepared=prepared, policy=policy, theme=theme, spec=spec,
                           snapshot=snapshot, registry=registry)


def _segment_identity_reader(node_id):
    assert node_id == SEG_NODE
    return {"schema": "gmi.identity_resolution/v1", "node_id": SEG_NODE, "graph_kind": "company",
            "market_scope": "us", "graph_identity_epoch": 1, "source_native_symbol": "ALPHA",
            "resolution_asof": "2024-03-03", "resolution_state": "RESOLVED", "issuer_id": SEG_ISSUER,
            "security_id": "SEC:US-XNAS-ALPHA", "listing_key": "US-XNAS-ALPHA",
            "join_method": "master_inception_exact", "refusal_reason": None,
            "computed_at": "2024-03-03T10:00:00Z", "engine_version": "theme_graph.v1"}


def _segment_evidence(case, *, role="operator", exposure_role="primary", profit_driver=True,
                      target=TARGET):
    return me.build_activity_membership_evidence(
        issuer_node_id=SEG_NODE, target_theme_id=target, role=role,
        knowledge_cutoff=KNOWLEDGE_CUTOFF, code_version=CODE_VERSION,
        identity_reader=_segment_identity_reader,
        disclosure_reader=lambda root, cv: case.snapshot,
        exposure_role=exposure_role, profit_driver=profit_driver)


def _segment_receipt(proposed_row, *, exposure=None, decision="RATIFIED"):
    receipt = {"schema": "gmi.activity_curation_receipt/v1",
               "proposal_id": proposed_row["proposal_id"],
               "proposal_sha256": bridge.proposal_sha256(proposed_row),
               "curator": CURATOR, "decision": decision, "reviewed_at": DECIDED_AT,
               "reasons": [{"code": "CHAIRMAN_DELEGATED_CURATOR",
                            "detail": "synthetic fixture curator act"}]}
    if exposure is not None:
        receipt["exposure"] = exposure
    return canon(receipt)


def _segment_fixture_ruling(tmp_path, case, proposed_row):
    """A FIXTURE graph-membership-use revision of the segment source-purpose policy.

    The segment scope is segment-only, so the grant's membership_scope is {} — the
    bridge compares counterparty/platform/product, all absent (None) on both sides.
    """
    evidence = proposed_row["evidence"]
    policy_path = tmp_path / "segment_source_purpose_policy.json"
    policy_path.write_bytes(canon(case.policy))
    ruling = {"schema": "company_intelligence.source_purpose_ruling/v1",
              "ruling_id": "FIXTURE-GMI-SEGMENT-GRAPH-MEMBERSHIP-USE",
              "revises_ruling_sha256": hashlib.sha256(canon(case.policy)).hexdigest(),
              "revises_ruling_path": str(policy_path),
              "recorded_at": RULING_RECORDED_AT, "decision": "covered",
              "decision_owner": "Chairman Chris",
              "evidence_kind": "direct_chairman_source_rights_confirmation",
              "source": {"sha256": evidence["source_evidence"]["edition"]["source_sha256"],
                         "byte_length": evidence["source_evidence"]["edition"]["byte_length"]},
              "permitted_use": copy.deepcopy(case.policy["permitted_use"]),
              "graph_membership_use_grant": {
                  "purpose": "graph_membership_use", "graph_membership_use": "GRANTED",
                  "internal": True, "display": False, "redistribution": False,
                  "subject_node_id": evidence["endpoints"]["source_node_id"],
                  "target_node_id": evidence["endpoints"]["target_node_id"],
                  "species": evidence["species"], "membership_scope": {},
                  "proposal_ids": [proposed_row["proposal_id"]]}}
    path = tmp_path / "SEGMENT_GRAPH_MEMBERSHIP_USE_RULING.json"
    path.write_text(json.dumps(ruling, sort_keys=True), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Test 1 — existing rows regenerate byte-identical; committed files still load
# ---------------------------------------------------------------------------

def _base_writer_module():
    raw = subprocess.run(
        ["git", "show", f"{BASE_COMMIT}:engine/theme_graph/membership_evidence.py"],
        cwd=ROOT, capture_output=True, check=True).stdout
    path = ROOT / "engine/theme_graph/membership_evidence.py"
    mod = types.ModuleType("base_membership_evidence")
    mod.__file__ = str(path)
    exec(compile(raw, str(path), "exec"), mod.__dict__)
    return mod


def _mu_identity_reader(node_id):
    assert node_id == "co:us:MU"
    return {"schema": "gmi.identity_resolution/v1", "node_id": "co:us:MU", "graph_kind": "company",
            "market_scope": "us", "graph_identity_epoch": 1, "source_native_symbol": "MU",
            "resolution_asof": "2026-10-18", "resolution_state": "RESOLVED",
            "issuer_id": "ISS:US-XNAS-MU", "security_id": "SEC:US-XNAS-MU",
            "listing_key": "US-XNAS-MU", "join_method": "master_inception_exact",
            "refusal_reason": None, "computed_at": "2026-10-18T11:03:21Z",
            "engine_version": "theme_graph.v1"}


def test_ppi_evidence_and_proposal_byte_identical_to_base_commit_writer():
    # The writer is the only thing that could change an existing row. Prove the
    # current writer equals the base-commit writer for the C01 PPI evidence under
    # identical injected readers (one shared disclosure snapshot, one identity row).
    base = _base_writer_module()
    snapshot = me._default_activity_disclosure(ROOT, CODE_VERSION)
    reader = lambda root, cv: snapshot  # noqa: E731 — one shared snapshot for both writers
    kwargs = dict(issuer_node_id="co:us:MU", target_theme_id=TARGET, role="component_supplier",
                  knowledge_cutoff="2026-10-19T00:00:00Z", code_version=CODE_VERSION,
                  identity_reader=_mu_identity_reader, disclosure_reader=reader)
    base_evidence = base.build_activity_membership_evidence(**kwargs)
    current_evidence = me.build_activity_membership_evidence(**kwargs)
    assert canon(base_evidence) == canon(current_evidence)
    assert "exposure" not in current_evidence
    assert current_evidence["species"] == "planned_product_integration"
    base_row = probation.make_activity_membership_proposal(base_evidence, created=CREATED)
    current_row = probation.make_activity_membership_proposal(current_evidence, created=CREATED)
    assert probation._activity_canonical(base_row) == probation._activity_canonical(current_row)


def test_committed_activity_rows_validate_and_bridge_reloads_them(tmp_path):
    rows = [json.loads(line) for line in
            _git_show("data/theme_graph/probation/activity_proposals.jsonl").decode().splitlines()
            if line.strip()]
    assert [r["status"] for r in rows if r["proposal_id"] == C01_PROPOSAL_ID] == ["PROPOSED", "RATIFIED"]
    for row in rows:
        assert probation.validate_activity_membership_proposal(row) == []
        assert "exposure" not in row["evidence"]
    # Re-run the bridge's load/validate over the committed event + receipt files.
    events_path = tmp_path / "activity_history_events.jsonl"
    receipts_path = tmp_path / "activity_history_bridge_receipts.jsonl"
    events_path.write_bytes(_git_show("data/theme_graph/probation/activity_history_events.jsonl"))
    receipts_path.write_bytes(_git_show("data/theme_graph/probation/activity_history_bridge_receipts.jsonl"))
    tiers = bridge.activity_target_tiers_from_crosswalk_path(ROOT / bridge.DEFAULT_CROSSWALK_PATH)
    loaded = bridge.load_bound_activity_events(
        events_path=events_path, bridge_receipts_path=receipts_path,
        receipts_dir=ROOT / bridge.DEFAULT_RECEIPTS_DIR, ruling_root=ROOT, target_tiers=tiers)
    assert loaded is not None and len(loaded["events"]) == 1
    event = loaded["events"][0]
    assert event["evidence_lineage"]["proposal_id"] == C01_PROPOSAL_ID
    assert event["species"] == "planned_product_integration"
    materialize.validate_activity_history_event(event)


# ---------------------------------------------------------------------------
# Test 2 — form refusals and span refusals
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("form", ["8-K", "10-Q", "S-1", "PRESS RELEASE"])
def test_non_annual_report_form_refused_at_preparation(tmp_path, form):
    with pytest.raises(n.DisclosureError, match="SEGMENT_FORM_NOT_ADMITTED"):
        _segment_case(tmp_path, form=form)


@pytest.mark.parametrize("form", ["8-K", "10-Q", "S-1", "PRESS RELEASE"])
def test_non_annual_report_form_refused_by_fact_validation(tmp_path, form):
    case = _segment_case(tmp_path)
    fact = copy.deepcopy(case.spec["fact"])
    fact["form_type"] = form
    with pytest.raises(n.DisclosureError, match="SEGMENT_FORM_NOT_ADMITTED"):
        n.validate_fact(fact)


def test_missing_span_refused(tmp_path):
    case = _segment_case(tmp_path)
    fact = copy.deepcopy(case.spec["fact"])
    del fact["span"]
    with pytest.raises(n.DisclosureError, match="SPAN_REQUIRED"):
        n.validate_fact(fact)


def test_zero_length_span_refused(tmp_path):
    case = _segment_case(tmp_path)
    fact = copy.deepcopy(case.spec["fact"])
    fact["span"]["end_byte"] = fact["span"]["start_byte"]
    with pytest.raises(n.DisclosureError, match="SPAN_REQUIRED"):
        n.validate_fact(fact)


def test_segment_fact_validates_and_carries_the_annual_report_form(tmp_path):
    case = _segment_case(tmp_path)
    fact = case.spec["fact"]
    assert n.validate_fact(fact).schema == n.SEGMENT_FACT_SCHEMA
    assert fact["kind"] == "segment_activity" and fact["lifecycle"] == "reported"
    assert fact["form_type"] == "10-K" and fact["accession"] == SEG_ACCESSION
    assert fact["fact_id"].startswith("activity:")


# ---------------------------------------------------------------------------
# Test 3 — the closed exposure block
# ---------------------------------------------------------------------------

def test_segment_proposal_validates_with_closed_exposure(tmp_path):
    case = _segment_case(tmp_path)
    evidence = _segment_evidence(case)
    row = probation.make_activity_membership_proposal(evidence, created=CREATED)
    assert probation.validate_activity_membership_proposal(row) == []
    exposure = row["evidence"]["exposure"]
    assert exposure["basis"] == "house_rule_v1"
    assert exposure["role"] == "primary" and exposure["profit_driver"] is True
    assert exposure["disclosed_line"] == SEG_LINE and exposure["share_scope"] == "segment"
    assert exposure["revenue_share"] == pytest.approx(0.30)
    assert exposure["revenue_denominator"] == 100.0
    assert exposure["accession"] == SEG_ACCESSION and exposure["fiscal_year"] == 2023
    assert row["evidence"]["scope"] == {"segment": {"value": SEG_LINE, "state": "KNOWN"}}
    assert row["evidence"]["role"] == "operator" and row["evidence"]["lifecycle"] == "current"


def test_unknown_exposure_key_fails_the_contract(tmp_path):
    case = _segment_case(tmp_path)
    evidence = _segment_evidence(case)
    evidence["exposure"]["smuggled"] = True
    with pytest.raises(probation.ActivityProposalRefusal, match="PROPOSAL_INVALID"):
        probation.make_activity_membership_proposal(evidence, created=CREATED)


def test_exposure_on_planned_product_integration_fails_the_contract():
    rows = [json.loads(line) for line in
            _git_show("data/theme_graph/probation/activity_proposals.jsonl").decode().splitlines()
            if line.strip()]
    ppi = next(r for r in rows if r["status"] == "PROPOSED")
    assert ppi["evidence"]["species"] == "planned_product_integration"
    drifted = copy.deepcopy(ppi)
    drifted["evidence"]["exposure"] = {
        "basis": "house_rule_v1", "role": "primary", "profit_driver": True,
        "disclosed_line": SEG_LINE, "share_scope": "segment", "revenue_share": 0.3,
        "revenue_denominator": 100.0, "fiscal_year": 2023, "accession": SEG_ACCESSION}
    assert probation.validate_activity_membership_proposal(drifted)


# ---------------------------------------------------------------------------
# Test 4 — one fixture segment member through writer + bridge; tier guard holds
# ---------------------------------------------------------------------------

def test_fixture_segment_member_bridges_to_a_micro_theme_and_fold_accepts(tmp_path):
    case = _segment_case(tmp_path)
    evidence = _segment_evidence(case)
    proposed = probation.make_activity_membership_proposal(evidence, created=CREATED)
    receipt_bytes = _segment_receipt(proposed, exposure={"role": "primary", "profit_driver": True})
    receipts_dir = tmp_path / "curation_receipts"
    receipts_dir.mkdir()
    (receipts_dir / (proposed["proposal_id"].replace(":", "_") + ".json")).write_bytes(receipt_bytes)
    terminal = probation.curate_activity_proposal(
        proposed, curator=CURATOR, decision="ACCEPT", decided_at=DECIDED_AT,
        receipt_bytes=receipt_bytes)
    ruling = _segment_fixture_ruling(tmp_path, case, proposed)
    tiers = {TARGET: "micro_theme"}
    [decision] = bridge.plan_bridge(
        [proposed, terminal], receipts_dir=receipts_dir, ruling_paths=[str(ruling)],
        recorded_at=RECORDED_AT, existing_events=[], allow_fixture=True, target_tiers=tiers)
    assert decision["outcome"] == "APPEND"
    assert decision["reason_code"] == "GRAPH_MEMBERSHIP_USE_GRANTED"
    assert decision["graph_membership_use"] == "GRANTED"
    event = decision["event"]
    materialize.validate_activity_history_event(event)
    assert event["species"] == "principal_business_activity"
    assert event["role"] == "operator" and event["lifecycle"] == "current"
    assert event["scope"] == {"segment": {"value": SEG_LINE, "state": "KNOWN"}}
    assert event["use_qualification"] == {"graph_membership_use": "GRANTED"}
    fold = materialize.apply_activity_membership_events(
        [event], knowledge_cutoff=event["clocks"]["knowledge_at"])
    assert [b["membership_id"] for b in fold["current"]] == [event["membership_id"]]
    assert fold["refused"] == [] and fold["history"] == []
    events_path = tmp_path / "activity_history_events.jsonl"
    bridge_receipts_path = tmp_path / "activity_history_bridge_receipts.jsonl"
    counts = bridge.apply_plan([decision], events_path=events_path,
                               receipts_path=bridge_receipts_path, recorded_at=RECORDED_AT)
    assert counts == {"appended_events": 1, "receipt_rows": 1, "skipped": 0}
    [stored] = bridge.read_events(events_path)
    assert stored["event_sha256"] == event["event_sha256"]
    # A rerun bridges nothing new.
    [rerun] = bridge.plan_bridge(
        [proposed, terminal], receipts_dir=receipts_dir, ruling_paths=[str(ruling)],
        recorded_at=RECORDED_AT, existing_events=bridge.read_events(events_path),
        allow_fixture=True, target_tiers=tiers)
    assert (rerun["outcome"], rerun["reason_code"]) == ("SKIPPED", "ALREADY_BRIDGED")


@pytest.mark.parametrize("tier", ["theme", "macro_category", "sub_theme"])
def test_segment_member_tier_guard_matches_the_c01_guard(tmp_path, tier):
    # The #11150 producer-side tier gate holds for the segment species exactly as
    # for C01: micro_theme/sub_theme append, theme/macro_category/unknown refuse.
    case = _segment_case(tmp_path)
    proposed = probation.make_activity_membership_proposal(_segment_evidence(case), created=CREATED)
    receipt_bytes = _segment_receipt(proposed, exposure={"role": "primary", "profit_driver": True})
    receipts_dir = tmp_path / "curation_receipts"
    receipts_dir.mkdir()
    (receipts_dir / (proposed["proposal_id"].replace(":", "_") + ".json")).write_bytes(receipt_bytes)
    terminal = probation.curate_activity_proposal(
        proposed, curator=CURATOR, decision="ACCEPT", decided_at=DECIDED_AT,
        receipt_bytes=receipt_bytes)
    ruling = _segment_fixture_ruling(tmp_path, case, proposed)
    [decision] = bridge.plan_bridge(
        [proposed, terminal], receipts_dir=receipts_dir, ruling_paths=[str(ruling)],
        recorded_at=RECORDED_AT, existing_events=[], allow_fixture=True,
        target_tiers={TARGET: tier})
    if tier == "sub_theme":
        assert decision["outcome"] == "APPEND"
    else:
        assert (decision["outcome"], decision["reason_code"]) == (
            "REFUSED", "ACTIVITY_TARGET_TIER_NOT_ADMITTED")


def test_segment_fixture_grant_needs_allow_fixture(tmp_path):
    case = _segment_case(tmp_path)
    proposed = probation.make_activity_membership_proposal(_segment_evidence(case), created=CREATED)
    receipt_bytes = _segment_receipt(proposed, exposure={"role": "primary", "profit_driver": True})
    receipts_dir = tmp_path / "curation_receipts"
    receipts_dir.mkdir()
    (receipts_dir / (proposed["proposal_id"].replace(":", "_") + ".json")).write_bytes(receipt_bytes)
    terminal = probation.curate_activity_proposal(
        proposed, curator=CURATOR, decision="ACCEPT", decided_at=DECIDED_AT,
        receipt_bytes=receipt_bytes)
    ruling = _segment_fixture_ruling(tmp_path, case, proposed)
    [decision] = bridge.plan_bridge(
        [proposed, terminal], receipts_dir=receipts_dir, ruling_paths=[str(ruling)],
        recorded_at=RECORDED_AT, existing_events=[], target_tiers={TARGET: "micro_theme"})
    assert decision["outcome"] == "HELD"
    assert "USE_RULING_FIXTURE" in [r["code"] for r in decision["ruling_refusals"]]


# ---------------------------------------------------------------------------
# Test 5 — house rule v1 and the curator exposure restatement
# ---------------------------------------------------------------------------

def test_minor_product_line_share_below_house_rule_refused(tmp_path):
    case = _segment_case(tmp_path, share_scope="product_line", revenue=7.0, revenue_denominator=100.0)
    with pytest.raises(me.ActivityAdmissionRefusal) as caught:
        _segment_evidence(case)
    assert caught.value.code == "EXPOSURE_BELOW_HOUSE_RULE"


def test_product_line_at_or_above_house_rule_admits(tmp_path):
    case = _segment_case(tmp_path, share_scope="product_line", revenue=10.0, revenue_denominator=100.0)
    evidence = _segment_evidence(case)
    assert evidence["exposure"]["revenue_share"] == pytest.approx(0.10)
    assert evidence["exposure"]["share_scope"] == "product_line"


def test_reportable_segment_admits_regardless_of_share(tmp_path):
    case = _segment_case(tmp_path, share_scope="segment", revenue=1.0, revenue_denominator=100.0)
    evidence = _segment_evidence(case)
    assert evidence["exposure"]["share_scope"] == "segment"
    assert evidence["exposure"]["revenue_share"] == pytest.approx(0.01)


def test_undisclosed_revenue_product_line_below_house_rule_refused(tmp_path):
    case = _segment_case(tmp_path, share_scope="product_line", revenue=None, revenue_denominator=None)
    with pytest.raises(me.ActivityAdmissionRefusal) as caught:
        _segment_evidence(case)
    assert caught.value.code == "EXPOSURE_BELOW_HOUSE_RULE"


def _segment_proposed(tmp_path):
    case = _segment_case(tmp_path)
    return probation.make_activity_membership_proposal(_segment_evidence(case), created=CREATED)


def test_curator_accept_must_restate_exposure_role(tmp_path):
    proposed = _segment_proposed(tmp_path)
    with pytest.raises(probation.ActivityProposalRefusal) as caught:
        probation.curate_activity_proposal(
            proposed, curator=CURATOR, decision="ACCEPT", decided_at=DECIDED_AT,
            receipt_bytes=_segment_receipt(proposed, exposure={"role": "secondary", "profit_driver": True}))
    assert caught.value.code == "CURATION_EXPOSURE_MISMATCH"


def test_curator_accept_must_restate_exposure_profit_driver(tmp_path):
    proposed = _segment_proposed(tmp_path)
    with pytest.raises(probation.ActivityProposalRefusal) as caught:
        probation.curate_activity_proposal(
            proposed, curator=CURATOR, decision="ACCEPT", decided_at=DECIDED_AT,
            receipt_bytes=_segment_receipt(proposed, exposure={"role": "primary", "profit_driver": False}))
    assert caught.value.code == "CURATION_EXPOSURE_MISMATCH"


def test_curator_accept_without_exposure_restatement_refused(tmp_path):
    proposed = _segment_proposed(tmp_path)
    with pytest.raises(probation.ActivityProposalRefusal) as caught:
        probation.curate_activity_proposal(
            proposed, curator=CURATOR, decision="ACCEPT", decided_at=DECIDED_AT,
            receipt_bytes=_segment_receipt(proposed))
    assert caught.value.code == "CURATION_EXPOSURE_MISMATCH"


def test_matching_exposure_restatement_accepts(tmp_path):
    proposed = _segment_proposed(tmp_path)
    terminal = probation.curate_activity_proposal(
        proposed, curator=CURATOR, decision="ACCEPT", decided_at=DECIDED_AT,
        receipt_bytes=_segment_receipt(proposed, exposure={"role": "primary", "profit_driver": True}))
    assert terminal["status"] == "RATIFIED"
    assert probation.validate_activity_membership_proposal(terminal) == []


def test_receipt_exposure_on_a_proposal_without_one_refused():
    rows = [json.loads(line) for line in
            _git_show("data/theme_graph/probation/activity_proposals.jsonl").decode().splitlines()
            if line.strip()]
    ppi = next(r for r in rows if r["status"] == "PROPOSED")
    receipt = canon({"schema": "gmi.activity_curation_receipt/v1", "proposal_id": ppi["proposal_id"],
                     "exposure": {"role": "primary", "profit_driver": True}})
    with pytest.raises(probation.ActivityProposalRefusal) as caught:
        probation.curate_activity_proposal(
            ppi, curator=CURATOR, decision="ACCEPT", decided_at="2026-10-22T04:50:12Z",
            receipt_bytes=receipt)
    assert caught.value.code == "CURATION_EXPOSURE_MISMATCH"


def test_exposure_judgments_refused_for_planned_product_integration():
    snapshot = me._default_activity_disclosure(ROOT, CODE_VERSION)
    with pytest.raises(me.ActivityAdmissionRefusal) as caught:
        me.build_activity_membership_evidence(
            issuer_node_id="co:us:MU", target_theme_id=TARGET, role="component_supplier",
            knowledge_cutoff="2026-10-19T00:00:00Z", code_version=CODE_VERSION,
            identity_reader=_mu_identity_reader, disclosure_reader=lambda root, cv: snapshot,
            exposure_role="primary", profit_driver=True)
    assert caught.value.code == "EXPOSURE_SPECIES_MISMATCH"


def test_operator_role_refused_for_planned_product_integration():
    snapshot = me._default_activity_disclosure(ROOT, CODE_VERSION)
    with pytest.raises(me.ActivityAdmissionRefusal) as caught:
        me.build_activity_membership_evidence(
            issuer_node_id="co:us:MU", target_theme_id=TARGET, role="operator",
            knowledge_cutoff="2026-10-19T00:00:00Z", code_version=CODE_VERSION,
            identity_reader=_mu_identity_reader, disclosure_reader=lambda root, cv: snapshot)
    assert caught.value.code == "ROLE_NOT_ADMITTED"