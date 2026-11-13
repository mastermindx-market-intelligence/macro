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
from scripts import propose_activity_membership as cli
from tests.test_company_pinned_relationship_candidates import (
    fixture as pinned_fixture, inspect as pinned_inspect,
)

ROOT = Path(__file__).resolve().parents[1]
# The base writer is read from git at this commit; a shallow/fresh clone without the
# object skips the byte-identity proof rather than carrying a fixture copy.
BASE_COMMIT = "7387e1f829b54c51de316a7ea74c066abdfcd24c"
CODE_VERSION = "0" * 40
C01_PROPOSAL_ID = "actprop:287edbf7e04b8aba873b7493"
TARGET = "theme:hbm_packaging"
SEG_NODE = "co:us:ALPHA"
SEG_ISSUER = "ISS:US-XNAS-ALPHA"
SEG_LINE = "Data Center Storage"
SEG_BODY_BASE = ("SYNTHETIC annual report. Aurora operates the Data Center Storage segment. "
                 "Aurora buys Widget wafers from Boreal.")
SEG_ACCESSION = "0000000001-24-000001"
KNOWLEDGE_CUTOFF = "2024-03-06T00:00:00Z"
CREATED = "2024-03-06T01:00:00Z"
DECIDED_AT = "2024-03-06T02:00:00Z"
RULING_RECORDED_AT = "2024-03-06T03:00:00Z"
RECORDED_AT = "2024-03-06T04:00:00Z"
CURATOR = "curator:gmi-desk"


def canon(value) -> bytes:
    return n._canonical(value)


def _committed_bytes(path: str) -> bytes:
    return (ROOT / path).read_bytes()


# ---------------------------------------------------------------------------
# Synthetic single-party segment owner fixture (mirrors sec_supplier_adoption)
# ---------------------------------------------------------------------------

def _figure_span_for(body: bytes, name: str, text: str) -> dict:
    """The pinned byte span of one figure's digits inside its unique labelled slot."""
    source = body.decode("utf-8")
    marker = f"{name}: "
    pos = source.index(marker) + len(marker)
    assert source[pos:pos + len(text)] == text
    start = len(source[:pos].encode("utf-8"))
    end = len(source[:pos + len(text)].encode("utf-8"))
    return {"start_byte": start, "end_byte": end,
            "text_sha256": hashlib.sha256(body[start:end]).hexdigest()}


def _segment_case(tmp_path, *, share_scope="segment", revenue=30.0, revenue_denominator=100.0,
                  profit=10.0, profit_denominator=100.0, profit_measure="operating_income",
                  fiscal_year=2023, form="10-K", body=None, figure_specs=None,
                  figure_spans=None, mutate_assertion=None):
    figures = {"revenue": revenue, "revenue_denominator": revenue_denominator,
               "profit": profit, "profit_denominator": profit_denominator}
    if figure_specs is None:
        figure_specs = {
            name: (None if value is None else
                   {"text": str(int(abs(value))), "sign": "+" if value >= 0 else "-", "scale": "units"})
            for name, value in figures.items()}
    if body is None:
        parts = [SEG_BODY_BASE] + [f"{name}: {figure_specs[name]['text']}"
                                   for name in n.SEGMENT_FIGURE_NAMES if figure_specs[name] is not None]
        body = " ".join(parts).encode("utf-8")
    if figure_spans is None:
        figure_spans = {
            name: (None if figure_specs[name] is None else
                   _figure_span_for(body, name, figure_specs[name]["text"]))
            for name in n.SEGMENT_FIGURE_NAMES}
    f = pinned_fixture(tmp_path / "native", body=body, form=form)
    receipt = receipt_for_char_span(source=body.decode("utf-8"),
                                    source_sha256=o.digest(body),
                                    char_start=0, char_end=len(body.decode("utf-8"))).to_dict()
    # The pinned candidate's built-in span receipt is bound to the helper's default
    # body; rebind it to this segment body so native replay is INSPECTABLE. The
    # candidate assertion's labels (Aurora/Widget/Boreal) all occur in the body.
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
                 "profit_measure": profit_measure, "fiscal_year": fiscal_year,
                 "figure_spans": figure_spans}
    for name in n.SEGMENT_FIGURE_NAMES:
        spec = figure_specs[name]
        for suffix in ("text", "sign", "scale"):
            assertion[f"{name}_{suffix}"] = None if spec is None else spec[suffix]
    if mutate_assertion is not None:
        mutate_assertion(assertion)
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
                           snapshot=snapshot, registry=registry, assertion=assertion,
                           role_review=role_review, figure_specs=figure_specs)


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
    rel = "engine/theme_graph/membership_evidence.py"
    try:
        raw = subprocess.run(["git", "show", f"{BASE_COMMIT}:{rel}"], cwd=ROOT,
                             check=True, capture_output=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("base commit 7387e1f8 not in object store (shallow/fresh clone); byte-identity proof not run")
    path = ROOT / rel
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


@pytest.mark.needs_full_checkout("data")
def test_committed_activity_rows_validate_and_bridge_reloads_them(tmp_path):
    rows = [json.loads(line) for line in
            _committed_bytes("data/theme_graph/probation/activity_proposals.jsonl").decode().splitlines()
            if line.strip()]
    assert [r["status"] for r in rows if r["proposal_id"] == C01_PROPOSAL_ID] == ["PROPOSED", "RATIFIED"]
    for row in rows:
        assert probation.validate_activity_membership_proposal(row) == []
        # Only PPI rows are exposure-free; a real PBA member may carry exposure.
        if row["evidence"]["species"] == "planned_product_integration":
            assert "exposure" not in row["evidence"]
    # Re-run the bridge's load/validate over the committed event + receipt files.
    events_path = tmp_path / "activity_history_events.jsonl"
    receipts_path = tmp_path / "activity_history_bridge_receipts.jsonl"
    events_path.write_bytes(_committed_bytes("data/theme_graph/probation/activity_history_events.jsonl"))
    receipts_path.write_bytes(_committed_bytes("data/theme_graph/probation/activity_history_bridge_receipts.jsonl"))
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


def test_span_disagreeing_with_pinned_receipt_refused_at_replay(tmp_path):
    # A fact whose span offsets no longer match the pinned receipt (the edition's
    # sec_source) is refused at replay: the source policy is bound to the exact span.
    case = _segment_case(tmp_path)
    spec = copy.deepcopy(case.spec)
    spec["fact"]["span"]["start_byte"] += 1
    with pytest.raises(n.DisclosureError, match="POLICY_SOURCE_MISMATCH"):
        o.qualify_records("a" * 40, canon(spec), canon(case.policy), case.registry,
                          case.identities, theme_sources_raw=case.theme)


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
    assert exposure["revenue_share"] == 0.30
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


@pytest.mark.needs_full_checkout("data")
def test_exposure_on_planned_product_integration_fails_the_contract():
    rows = [json.loads(line) for line in
            _committed_bytes("data/theme_graph/probation/activity_proposals.jsonl").decode().splitlines()
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
    assert evidence["exposure"]["revenue_share"] == 0.10
    assert evidence["exposure"]["share_scope"] == "product_line"


def test_reportable_segment_admits_regardless_of_share(tmp_path):
    case = _segment_case(tmp_path, share_scope="segment", revenue=1.0, revenue_denominator=100.0)
    evidence = _segment_evidence(case)
    assert evidence["exposure"]["share_scope"] == "segment"
    assert evidence["exposure"]["revenue_share"] == 0.01


def test_undisclosed_revenue_product_line_below_house_rule_refused(tmp_path):
    case = _segment_case(tmp_path, share_scope="product_line", revenue=None, revenue_denominator=None)
    with pytest.raises(me.ActivityAdmissionRefusal) as caught:
        _segment_evidence(case)
    assert caught.value.code == "EXPOSURE_BELOW_HOUSE_RULE"


def test_zero_revenue_denominator_refused_with_typed_code(tmp_path):
    # The public builder must refuse a non-positive denominator with a typed code,
    # never a ZeroDivisionError. The owner lane only yields denominators > 0, so the
    # zero is injected straight into the fact the builder reads.
    case = _segment_case(tmp_path, share_scope="segment")
    spec = copy.deepcopy(case.snapshot.spec)
    spec["fact"]["revenue_denominator"] = 0.0
    snapshot = SimpleNamespace(spec=spec, bindings=dict(case.snapshot.bindings))
    with pytest.raises(me.ActivityAdmissionRefusal) as caught:
        me.build_activity_membership_evidence(
            issuer_node_id=SEG_NODE, target_theme_id=TARGET, role="operator",
            knowledge_cutoff=KNOWLEDGE_CUTOFF, code_version=CODE_VERSION,
            identity_reader=_segment_identity_reader,
            disclosure_reader=lambda root, cv: snapshot,
            exposure_role="primary", profit_driver=True)
    assert caught.value.code == "EXPOSURE_DENOMINATOR_INVALID"


# ---------------------------------------------------------------------------
# Test 6 — figure spans, literal text/sign/scale, and losses (amendments 2/3/3b)
# ---------------------------------------------------------------------------

def _segment_builder(snapshot):
    return me.build_activity_membership_evidence(
        issuer_node_id=SEG_NODE, target_theme_id=TARGET, role="operator",
        knowledge_cutoff=KNOWLEDGE_CUTOFF, code_version=CODE_VERSION,
        identity_reader=_segment_identity_reader,
        disclosure_reader=lambda root, cv: snapshot,
        exposure_role="primary", profit_driver=True)


def test_revenue_share_is_exact_quotient_of_filed_figures(tmp_path):
    case = _segment_case(tmp_path)
    fact = case.spec["fact"]
    exposure = _segment_evidence(case)["exposure"]
    assert exposure["revenue_share"] == fact["revenue"] / fact["revenue_denominator"]


def test_figure_without_span_refused(tmp_path):
    with pytest.raises(n.DisclosureError, match="FIGURE_SPAN_REQUIRED"):
        _segment_case(tmp_path, mutate_assertion=lambda a: a["figure_spans"].__setitem__("profit", None))


def test_figure_span_text_lacking_figure_refused(tmp_path):
    with pytest.raises(n.DisclosureError, match="FIGURE_SPAN_MISMATCH"):
        _segment_case(tmp_path, mutate_assertion=lambda a: a.__setitem__("profit_text", "999"))


def test_figure_numeric_not_equal_to_derived_text_refused(tmp_path):
    with pytest.raises(n.DisclosureError, match="FIGURE_TEXT_MISMATCH"):
        _segment_case(tmp_path, mutate_assertion=lambda a: a.__setitem__("profit", 999.0))


def test_tampered_figure_span_offset_fails_at_replay(tmp_path):
    case = _segment_case(tmp_path)
    spec = copy.deepcopy(case.snapshot.spec)
    spec["fact"]["figure_spans"]["revenue"]["start_byte"] += 1
    snapshot = SimpleNamespace(spec=spec, bindings=dict(case.snapshot.bindings))
    source = segment.PinnedSegmentSource(snapshot, case.pinned.authority)
    e = spec["edition"]
    with pytest.raises(n.DisclosureError, match="FIGURE_SPAN_MISMATCH"):
        source.read_source(disclosure_id=e["disclosure_id"], edition_reference=n.validate_edition(e),
                           source_sha256=e["source_sha256"], expected_byte_length=e["source_byte_length"],
                           max_byte_length=n.MAX_SEC_SOURCE_BYTES)


def test_exposure_scale_mismatch_refused(tmp_path):
    case = _segment_case(tmp_path)
    spec = copy.deepcopy(case.snapshot.spec)
    spec["fact"]["revenue_scale"] = "thousands"  # differs from revenue_denominator_scale="units"
    snapshot = SimpleNamespace(spec=spec, bindings=dict(case.snapshot.bindings))
    with pytest.raises(me.ActivityAdmissionRefusal) as caught:
        _segment_builder(snapshot)
    assert caught.value.code == "EXPOSURE_SCALE_MISMATCH"


def test_negative_revenue_denominator_refused(tmp_path):
    case = _segment_case(tmp_path)
    spec = copy.deepcopy(case.snapshot.spec)
    spec["fact"]["revenue_denominator"] = -100.0
    snapshot = SimpleNamespace(spec=spec, bindings=dict(case.snapshot.bindings))
    with pytest.raises(me.ActivityAdmissionRefusal) as caught:
        _segment_builder(snapshot)
    assert caught.value.code == "EXPOSURE_DENOMINATOR_INVALID"


def test_negative_revenue_numerator_refused(tmp_path):
    case = _segment_case(tmp_path)
    spec = copy.deepcopy(case.snapshot.spec)
    spec["fact"]["revenue"] = -30.0
    snapshot = SimpleNamespace(spec=spec, bindings=dict(case.snapshot.bindings))
    with pytest.raises(me.ActivityAdmissionRefusal) as caught:
        _segment_builder(snapshot)
    assert caught.value.code == "EXPOSURE_NUMERATOR_INVALID"


def test_loss_profit_ix_shape_carries_sign_and_omits_profit_share(tmp_path):
    # The inline-XBRL loss shape keeps its parentheses outside the tag, so "(54,602)"
    # is never contiguous; the digits are pinned literally and the sign is declared.
    ix_loss = '(<ix:nonFraction name="us-gaap:OperatingIncomeLoss" sign="-">54,602</ix:nonFraction>)'
    body = (SEG_BODY_BASE + " revenue: 30 revenue_denominator: 100 profit: "
            + ix_loss + " profit_denominator: 100").encode("utf-8")
    source = body.decode("utf-8")
    pos = source.index(ix_loss)
    start = len(source[:pos].encode("utf-8"))
    end = len(source[:pos + len(ix_loss)].encode("utf-8"))
    profit_span = {"start_byte": start, "end_byte": end,
                   "text_sha256": hashlib.sha256(body[start:end]).hexdigest()}
    figure_specs = {
        "revenue": {"text": "30", "sign": "+", "scale": "units"},
        "revenue_denominator": {"text": "100", "sign": "+", "scale": "units"},
        "profit": {"text": "54,602", "sign": "-", "scale": "units"},
        "profit_denominator": {"text": "100", "sign": "+", "scale": "units"}}
    figure_spans = {
        "revenue": _figure_span_for(body, "revenue", "30"),
        "revenue_denominator": _figure_span_for(body, "revenue_denominator", "100"),
        "profit": profit_span,
        "profit_denominator": _figure_span_for(body, "profit_denominator", "100")}
    case = _segment_case(tmp_path, profit=-54602.0, body=body,
                         figure_specs=figure_specs, figure_spans=figure_spans)
    fact = case.spec["fact"]
    assert fact["profit"] == -54602.0 and fact["profit_sign"] == "-"
    exposure = _segment_evidence(case)["exposure"]
    assert exposure["profit_share"] is None
    assert exposure["revenue_share"] == fact["revenue"] / fact["revenue_denominator"]


def test_figure_sign_declared_negative_without_marker_refused(tmp_path):
    with pytest.raises(n.DisclosureError, match="FIGURE_SIGN_UNSUPPORTED"):
        _segment_case(tmp_path, mutate_assertion=lambda a: a.__setitem__("profit_sign", "-"))


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


@pytest.mark.needs_full_checkout("data")
def test_receipt_exposure_on_a_proposal_without_one_refused():
    rows = [json.loads(line) for line in
            _committed_bytes("data/theme_graph/probation/activity_proposals.jsonl").decode().splitlines()
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


# ---------------------------------------------------------------------------
# Test 7 — fix round 2: whole-token match (B1), two-direction sign (B2),
# value==text at every read-back (B3), manifest form at replay (N2)
# ---------------------------------------------------------------------------

def _profit_expression_case(tmp_path, expression, *, profit, sign, text="54,602", scale="units"):
    """A case whose profit figure is pinned to a custom printed expression."""
    body = (SEG_BODY_BASE + " revenue: 30 revenue_denominator: 100 profit: "
            + expression + " profit_denominator: 100").encode("utf-8")
    source = body.decode("utf-8")
    pos = source.index(expression)
    start = len(source[:pos].encode("utf-8"))
    end = len(source[:pos + len(expression)].encode("utf-8"))
    profit_span = {"start_byte": start, "end_byte": end,
                   "text_sha256": hashlib.sha256(body[start:end]).hexdigest()}
    figure_specs = {
        "revenue": {"text": "30", "sign": "+", "scale": "units"},
        "revenue_denominator": {"text": "100", "sign": "+", "scale": "units"},
        "profit": {"text": text, "sign": sign, "scale": scale},
        "profit_denominator": {"text": "100", "sign": "+", "scale": "units"}}
    figure_spans = {
        "revenue": _figure_span_for(body, "revenue", "30"),
        "revenue_denominator": _figure_span_for(body, "revenue_denominator", "100"),
        "profit": profit_span,
        "profit_denominator": _figure_span_for(body, "profit_denominator", "100")}
    return _segment_case(tmp_path, profit=profit, body=body,
                         figure_specs=figure_specs, figure_spans=figure_spans)


def _read_source(source, edition):
    return source.read_source(disclosure_id=edition["disclosure_id"],
                              edition_reference=n.validate_edition(edition),
                              source_sha256=edition["source_sha256"],
                              expected_byte_length=edition["source_byte_length"],
                              max_byte_length=n.MAX_SEC_SOURCE_BYTES)


# --- B1: the printed number must match as a whole token ---------------------

def test_figure_leading_fragment_refused(tmp_path):
    # Reviewer probe 1: span prints "30", text "3" was admitted as 0.03; a leading
    # fragment is not a whole token and is now refused.
    def mutate(a):
        a["revenue"] = 3.0
        a["revenue_text"] = "3"
    with pytest.raises(n.DisclosureError, match="FIGURE_SPAN_MISMATCH"):
        _segment_case(tmp_path, revenue=30.0, mutate_assertion=mutate)


def test_figure_trailing_fragment_refused(tmp_path):
    # A trailing fragment ("0" in "30") is not a whole token.
    def mutate(a):
        a["revenue"] = 0.0
        a["revenue_text"] = "0"
    with pytest.raises(n.DisclosureError, match="FIGURE_SPAN_MISMATCH"):
        _segment_case(tmp_path, revenue=30.0, mutate_assertion=mutate)


def test_figure_comma_group_fragment_refused(tmp_path):
    # A fragment inside a comma group ("602" in "54,602") is not a whole token.
    body = (SEG_BODY_BASE + " revenue: 54,602 revenue_denominator: 100 "
            "profit: 10 profit_denominator: 100").encode("utf-8")
    figure_specs = {
        "revenue": {"text": "54,602", "sign": "+", "scale": "units"},
        "revenue_denominator": {"text": "100", "sign": "+", "scale": "units"},
        "profit": {"text": "10", "sign": "+", "scale": "units"},
        "profit_denominator": {"text": "100", "sign": "+", "scale": "units"}}
    figure_spans = {name: _figure_span_for(body, name, figure_specs[name]["text"])
                    for name in n.SEGMENT_FIGURE_NAMES}

    def mutate(a):
        a["revenue"] = 602.0
        a["revenue_text"] = "602"
    with pytest.raises(n.DisclosureError, match="FIGURE_SPAN_MISMATCH"):
        _segment_case(tmp_path, revenue=54602.0, body=body, figure_specs=figure_specs,
                      figure_spans=figure_spans, mutate_assertion=mutate)


def test_whole_token_inside_ix_tag_still_matches(tmp_path):
    # B1: the whole-token rule must still find a number sitting inside an ix tag
    # (">54,602<"). A "+" figure needs no loss marker, isolating the match itself.
    case = _profit_expression_case(
        tmp_path, '<ix:nonFraction>54,602</ix:nonFraction>',
        profit=54602.0, sign="+")
    assert case.spec["fact"]["profit"] == 54602.0


# --- B2: the sign is decided in BOTH directions -----------------------------

def test_loss_ix_full_attributes_admits_negative(tmp_path):
    ix = ('(<ix:nonFraction id="c1" contextRef="d" unitRef="USD" '
          'name="us-gaap:OperatingIncomeLoss" scale="3" decimals="-3" sign="-">'
          '54,602</ix:nonFraction>)')
    case = _profit_expression_case(tmp_path, ix, profit=-54602.0, sign="-")
    assert case.spec["fact"]["profit"] == -54602.0
    assert case.spec["fact"]["profit_sign"] == "-"


def test_loss_ix_td_cells_around_parentheses_admits_negative(tmp_path):
    # The definition skips whole tags, so </td><td> cell boundaries around the
    # parentheses do not hide the loss shape.
    td = '<td>(</td><td><ix:nonFraction sign="-">54,602</ix:nonFraction></td><td>)</td>'
    case = _profit_expression_case(tmp_path, td, profit=-54602.0, sign="-")
    assert case.spec["fact"]["profit"] == -54602.0


def test_loss_unicode_minus_admits_negative(tmp_path):
    case = _profit_expression_case(tmp_path, "−54,602", profit=-54602.0, sign="-")
    assert case.spec["fact"]["profit"] == -54602.0


def test_loss_currency_and_whitespace_skipped(tmp_path):
    case = _profit_expression_case(tmp_path, "( $ 54,602 )", profit=-54602.0, sign="-")
    assert case.spec["fact"]["profit"] == -54602.0


def test_loss_nbsp_entities_skipped(tmp_path):
    case = _profit_expression_case(tmp_path, "(&nbsp;$54,602&#160;)", profit=-54602.0, sign="-")
    assert case.spec["fact"]["profit"] == -54602.0


def test_parentheses_declared_plus_refused(tmp_path):
    # Reviewer probe 2: "(54,602)" with sign "+" was 546.02; now refused.
    with pytest.raises(n.DisclosureError, match="FIGURE_SIGN_UNSUPPORTED"):
        _profit_expression_case(tmp_path, "(54,602)", profit=54602.0, sign="+")


def test_note_parentheses_declared_minus_refused(tmp_path):
    # Reviewer probe 3: "(Note 5) 54,602 (a)" with sign "-" was -54602. Under the
    # closed rule the printed span is not one of the three figure shapes (extra
    # note text and footnote mark), so it is refused as FIGURE_SPAN_MISMATCH.
    with pytest.raises(n.DisclosureError, match="FIGURE_SPAN_MISMATCH"):
        _profit_expression_case(tmp_path, "(Note 5) 54,602 (a)", profit=-54602.0, sign="-")


def test_minus_declared_plus_refused(tmp_path):
    with pytest.raises(n.DisclosureError, match="FIGURE_SIGN_UNSUPPORTED"):
        _profit_expression_case(tmp_path, "-54,602", profit=54602.0, sign="+")


def test_trailing_paren_declared_plus_refused(tmp_path):
    # A trailing ")" is printed in the span but is not part of any closed shape,
    # so the span is refused as FIGURE_SPAN_MISMATCH (not a sign disagreement).
    with pytest.raises(n.DisclosureError, match="FIGURE_SPAN_MISMATCH"):
        _profit_expression_case(tmp_path, "54,602)", profit=54602.0, sign="+")


# --- B3: value == text at EVERY read-back (adopt, qualify, replay) ----------

def test_altered_value_refused_at_adopt_qualify_and_replay(tmp_path):
    # Reviewer probe 4: prepare a valid fact, then alter revenue to 90.0 while
    # revenue_text stays "30". It must be refused at each read-back, separately.
    case = _segment_case(tmp_path)

    prepared = copy.deepcopy(case.prepared)
    prepared["proposed_fact"]["revenue"] = 90.0
    with pytest.raises(n.DisclosureError, match="FIGURE_TEXT_MISMATCH"):
        segment.adopt_segment_input(prepared, adopted_at="2024-03-05T10:00:00Z",
                                    ruling_raw=canon(case.policy), theme_sources_raw=case.theme,
                                    identity_observed_at="2024-03-03T10:00:00Z")

    spec = copy.deepcopy(case.spec)
    spec["fact"]["revenue"] = 90.0
    with pytest.raises(n.DisclosureError, match="FIGURE_TEXT_MISMATCH"):
        o.qualify_records("a" * 40, canon(spec), canon(case.policy), case.registry,
                          case.identities, theme_sources_raw=case.theme)

    spec = copy.deepcopy(case.snapshot.spec)
    spec["fact"]["revenue"] = 90.0
    snapshot = SimpleNamespace(spec=spec, bindings=dict(case.snapshot.bindings))
    source = segment.PinnedSegmentSource(snapshot, case.pinned.authority)
    with pytest.raises(n.DisclosureError, match="FIGURE_TEXT_MISMATCH"):
        _read_source(source, spec["edition"])


def test_altered_value_refused_by_fact_validation(tmp_path):
    # The same invariant holds for any direct validate_fact read-back (publication
    # and the manifest both re-validate the adopted fact).
    case = _segment_case(tmp_path)
    fact = copy.deepcopy(case.spec["fact"])
    fact["revenue"] = 90.0
    with pytest.raises(n.DisclosureError, match="FIGURE_TEXT_MISMATCH"):
        n.validate_fact(fact)


# --- N2: the pinned manifest's form must equal the fact's form_type ---------

def test_manifest_form_not_equal_to_fact_form_refused_at_replay(tmp_path):
    case = _segment_case(tmp_path)  # manifest and fact both 10-K
    spec = copy.deepcopy(case.snapshot.spec)
    spec["fact"]["form_type"] = "20-F"  # admitted, but not the manifest's 10-K
    snapshot = SimpleNamespace(spec=spec, bindings=dict(case.snapshot.bindings))
    source = segment.PinnedSegmentSource(snapshot, case.pinned.authority)
    with pytest.raises(n.DisclosureError, match="SEGMENT_FORM_NOT_ADMITTED"):
        _read_source(source, spec["edition"])


# ---------------------------------------------------------------------------
# Test 8 — fix round 3: the span IS the figure (closed rule, tables A-D)
# ---------------------------------------------------------------------------

# Non-ASCII characters used in table A, written as explicit escapes so a dash or
# bracket look-alike can never slip in.
_EN_DASH = "–"
_EM_DASH = "—"
_MINUS = "−"
_FW_OPEN = "（"
_FW_CLOSE = "）"

# Addendum (ruling 42): invisible and non-Pd sign characters, written as explicit
# code points so no look-alike or zero-width byte can slip into the source.
_THIN_SPACE = chr(0x2009)
_ZWSP = chr(0x200B)
_BOM = chr(0xFEFF)
_SUP_MINUS = chr(0x207B)
_HEAVY_MINUS = chr(0x2796)
_MOD_MINUS = chr(0x02D7)
_PLUS_MINUS = chr(0x00B1)
_TILDE_OP = chr(0x223C)

# Table A: one parametrised test straight on _verify_figure_span. Each row is
# (id, raw, span, text, sign, whole_document, expected_code); expected_code None
# means ADMIT. The span is the whole raw string unless a cut is named (then the
# span is the named substring of raw).
_TABLE_A = [
    # --- must be ADMITTED ---
    ("A01_plain", "54,602", "54,602", "54,602", "+", True, None),
    ("A02_dollar_space", "$ 54,602", "$ 54,602", "54,602", "+", True, None),
    ("A03_ix_scale_decimals",
     '<ix:nonFraction scale="3" decimals="-3" contextRef="c30" id="f-30">54,602</ix:nonFraction>',
     '<ix:nonFraction scale="3" decimals="-3" contextRef="c30" id="f-30">54,602</ix:nonFraction>',
     "54,602", "+", True, None),
    ("A04_ix_loss_parens", '(<ix:nonFraction sign="-" scale="3">54,602</ix:nonFraction>)',
     '(<ix:nonFraction sign="-" scale="3">54,602</ix:nonFraction>)', "54,602", "-", True, None),
    ("A05_td_cells_dollar", "$</td><td>(54,602</td><td>)", "$</td><td>(54,602</td><td>)",
     "54,602", "-", True, None),
    ("A06_parens", "(54,602)", "(54,602)", "54,602", "-", True, None),
    ("A07_ascii_minus", "-54,602", "-54,602", "54,602", "-", True, None),
    ("A08_unicode_minus", _MINUS + "54,602", _MINUS + "54,602", "54,602", "-", True, None),
    ("A09_sentence_end", "was 54,602.", "54,602", "54,602", "+", True, None),
    ("A10_sentence_end_prepare", "was 54,602.", "54,602", "54,602", "+", False, None),
    ("A11_leading_digits_doc", "54,602 was revenue", "54,602", "54,602", "+", True, None),
    ("A12_ix_scale_cut", 'Revenue <ix:nonFraction scale="3">54,602</ix:nonFraction>',
     "54,602", "54,602", "+", True, None),
    ("A13_table_cells_cut", "<td>48,310</td><td>54,602</td><td>(1,200)</td>",
     "54,602", "54,602", "+", True, None),
    # --- must be REFUSED ---
    ("A14_leading_fragment", "30", "30", "3", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("A15_ix_scale_fragment", '<ix:nonFraction scale="3">30</ix:nonFraction>',
     '<ix:nonFraction scale="3">30</ix:nonFraction>', "3", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("A16_ix_scale_text3", '<ix:nonFraction scale="3">54,602</ix:nonFraction>',
     '<ix:nonFraction scale="3">54,602</ix:nonFraction>', "3", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("A17_ix_decimals_text3", '<ix:nonFraction decimals="-3">54,602</ix:nonFraction>',
     '<ix:nonFraction decimals="-3">54,602</ix:nonFraction>', "3", "-", True, "FIGURE_SPAN_MISMATCH"),
    ("A18_space_group", "54 602", "54 602", "602", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("A19_nbsp_group", "54&#160;602", "54&#160;602", "602", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("A20_dot_group", "54.602", "54.602", "602", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("A21_percent", "30%", "30%", "30", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("A22_footnote", "54,602(a)", "54,602(a)", "54,602", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("A23_second_number", "300 and 3", "300 and 3", "3", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("A24_parens_declared_plus", "(54,602)", "(54,602)", "54,602", "+", True, "FIGURE_SIGN_UNSUPPORTED"),
    ("A25_note_parens", "(Note 5) 54,602 (a)", "(Note 5) 54,602 (a)", "54,602", "-", True,
     "FIGURE_SPAN_MISMATCH"),
    ("A26_en_dash", _EN_DASH + "54,602", _EN_DASH + "54,602", "54,602", "+", True,
     "FIGURE_SPAN_MISMATCH"),
    ("A27_em_dash", _EM_DASH + "54,602", _EM_DASH + "54,602", "54,602", "+", True,
     "FIGURE_SPAN_MISMATCH"),
    ("A28_entity_minus", "&#x2212;54,602", "&#x2212;54,602", "54,602", "+", True,
     "FIGURE_SPAN_MISMATCH"),
    ("A29_fullwidth_parens", _FW_OPEN + "54,602" + _FW_CLOSE, _FW_OPEN + "54,602" + _FW_CLOSE,
     "54,602", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("A30_trailing_minus", "54,602-", "54,602-", "54,602", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("A31_cr", "54,602 CR", "54,602 CR", "54,602", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("A32_double_open_paren", "((54,602)", "((54,602)", "54,602", "-", True, "FIGURE_SPAN_MISMATCH"),
    ("A33_broken_tag", "(<b>x >54,602)", "(<b>x >54,602)", "54,602", "-", True, "FIGURE_SPAN_MISMATCH"),
    ("A34_double_dollar", "($$54,602)", "($$54,602)", "54,602", "-", True, "FIGURE_SPAN_MISMATCH"),
    ("A35_cut_parens", "(54,602)", "54,602", "54,602", "+", True, "FIGURE_SIGN_UNSUPPORTED"),
    ("A36_cut_en_dash", _EN_DASH + "54,602", "54,602", "54,602", "+", True, "FIGURE_SIGN_UNSUPPORTED"),
    ("A37_cut_entity_minus", "&#x2212;54,602", "54,602", "54,602", "+", True, "FIGURE_SIGN_UNSUPPORTED"),
    ("A38_cut_trailing_minus", "54,602-", "54,602", "54,602", "+", True, "FIGURE_SIGN_UNSUPPORTED"),
    ("A39_cut_ix_loss", '(<ix:nonFraction sign="-">54,602</ix:nonFraction>)', "54,602", "54,602",
     "+", True, "FIGURE_SIGN_UNSUPPORTED"),
    ("A40_ix_neg_declared_plus", '<ix:nonFraction sign="-" scale="3">54,602</ix:nonFraction>',
     '<ix:nonFraction sign="-" scale="3">54,602</ix:nonFraction>', "54,602", "+", True,
     "FIGURE_SIGN_UNSUPPORTED"),
    ("A41_ix_neg_declared_minus", '<ix:nonFraction sign="-" scale="3">54,602</ix:nonFraction>',
     '<ix:nonFraction sign="-" scale="3">54,602</ix:nonFraction>', "54,602", "-", True,
     "FIGURE_SIGN_UNSUPPORTED"),
    ("A42_cut_ix_neg_doc", 'Revenue <ix:nonFraction sign="-" scale="3">54,602</ix:nonFraction>',
     "54,602", "54,602", "+", True, "FIGURE_SIGN_UNSUPPORTED"),
    ("A43_leading_digits_prepare", "54,602 was revenue", "54,602", "54,602", "+", False,
     "FIGURE_SIGN_UNSUPPORTED"),
    ("A44_cut_comma_group", "54,602", "4,602", "4,602", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("A45_cut_decimal", "54,602.5", "54,602", "54,602", "+", True, "FIGURE_SPAN_MISMATCH"),
    # --- Addendum (ruling 42): every row of the COO's coo_split.py probe. Each
    # cut occurs once in its raw, so index == rfind == find and the span matches
    # the probe. Fragments / malformed text -> FIGURE_SPAN_MISMATCH; invisible
    # characters and non-allowlisted sign marks -> FIGURE_SIGN_UNSUPPORTED. ---
    ("S01_space_tail", "54 602", "602", "602", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("S02_space_head", "54 602", "54", "54", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("S03_nbsp_entity_tail", "54&#160;602", "602", "602", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("S04_nbsp_named_head", "54&nbsp;602", "54", "54", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("S05_thin_entity_tail", "54&#8239;602", "602", "602", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("S06_thin_char_tail", "54" + _THIN_SPACE + "602", "602", "602", "+", True,
     "FIGURE_SPAN_MISMATCH"),
    ("S07_inline_tag_comma_tail", "<b>54</b>,602", "602", "602", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("S08_comma_inline_tag_tail", "54,<span>602</span>", "602", "602", "+", True,
     "FIGURE_SPAN_MISMATCH"),
    ("S09_inline_tag_head", "<b>54</b>,602", "54", "54", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("S10_apostrophe_tail", "54'602", "602", "602", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("S11_decimal_after_tag", "54,602<span>.5</span>", "54,602", "54,602", "+", True,
     "FIGURE_SPAN_MISMATCH"),
    ("S12_year_in_prose", "in 2024 54,602 was", "54,602", "54,602", "+", True,
     "FIGURE_SPAN_MISMATCH"),
    ("S13_superscript_digit", "54,602<sup>1</sup>", "54,602", "54,602", "+", True,
     "FIGURE_SPAN_MISMATCH"),
    ("S14_cell_neighbour", "<td>48,310</td><td>54,602</td>", "54,602", "54,602", "+", True, None),
    ("S15_cell_neighbour_upper", "<TD>48,310</TD><TD>54,602</TD>", "54,602", "54,602", "+", True,
     None),
    ("S16_br_neighbour", "48,310<br/>54,602", "54,602", "54,602", "+", True, None),
    ("S17_paragraph_neighbour", "<p>48,310</p><p>54,602</p>", "54,602", "54,602", "+", True, None),
    ("S18_sentence_end_then_cell", "<td>of 54,602.</td><td>5</td>", "54,602", "54,602", "+", True,
     None),
    ("S19_word_neighbours", "Revenue 54,602 thousand", "54,602", "54,602", "+", True, None),
    ("S20_footnote_in_brackets", "<td>54,602 (1)</td>", "54,602", "54,602", "+", True, None),
    ("S21_zwsp_hides_paren", "(" + _ZWSP + "54,602" + _ZWSP + ")", "54,602", "54,602", "+", True,
     "FIGURE_SIGN_UNSUPPORTED"),
    ("S22_soft_hyphen_hides_paren", "(&shy;54,602)", "54,602", "54,602", "+", True,
     "FIGURE_SIGN_UNSUPPORTED"),
    ("S23_zwsp_entity_right", "x 54,602&#8203;)", "54,602", "54,602", "+", True,
     "FIGURE_SIGN_UNSUPPORTED"),
    ("S24_bom_hides_dash", "x -" + _BOM + "54,602", "54,602", "54,602", "+", True,
     "FIGURE_SIGN_UNSUPPORTED"),
    ("S25_superscript_minus", "x " + _SUP_MINUS + "54,602", "54,602", "54,602", "+", True,
     "FIGURE_SIGN_UNSUPPORTED"),
    ("S26_heavy_minus", "x " + _HEAVY_MINUS + "54,602", "54,602", "54,602", "+", True,
     "FIGURE_SIGN_UNSUPPORTED"),
    ("S27_modifier_minus", "x " + _MOD_MINUS + "54,602", "54,602", "54,602", "+", True,
     "FIGURE_SIGN_UNSUPPORTED"),
    ("S28_plus_minus", "x " + _PLUS_MINUS + "54,602", "54,602", "54,602", "+", True,
     "FIGURE_SIGN_UNSUPPORTED"),
    ("S29_tilde_operator", "x " + _TILDE_OP + "54,602", "54,602", "54,602", "+", True,
     "FIGURE_SIGN_UNSUPPORTED"),
    ("S30_trailing_comma_text", "x 54, y", "54,", "54,", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("S31_double_comma_text", "x 54,,602 y", "54,,602", "54,,602", "+", True,
     "FIGURE_SPAN_MISMATCH"),
    ("S32_bad_grouping_text", "x 5,46,02 y", "5,46,02", "5,46,02", "+", True,
     "FIGURE_SPAN_MISMATCH"),
    ("S33_leading_zero_text", "x 054,602 y", "054,602", "054,602", "+", True,
     "FIGURE_SPAN_MISMATCH"),
    ("S34_plain_digits_text", "x 54602 y", "54602", "54602", "+", True, None),
    ("S35_zero_text", "x 0 y", "0", "0", "+", True, None),
    # --- Addendum: figure-text grammar (Change 1) on whole spans. ---
    ("G01_grammar_zero", "0", "0", "0", "+", True, None),
    ("G02_grammar_double_zero", "00", "00", "00", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("G03_grammar_trailing_comma", "54,", "54,", "54,", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("G04_grammar_double_comma", "54,,602", "54,,602", "54,,602", "+", True,
     "FIGURE_SPAN_MISMATCH"),
    ("G05_grammar_bad_group", "5,46,02", "5,46,02", "5,46,02", "+", True, "FIGURE_SPAN_MISMATCH"),
    ("G06_grammar_four_digit_lead", "1234,602", "1234,602", "1234,602", "+", True,
     "FIGURE_SPAN_MISMATCH"),
    ("G07_grammar_plain", "54602", "54602", "54602", "+", True, None),
    ("G08_grammar_grouped", "1,254,602", "1,254,602", "1,254,602", "+", True, None),
]


def _table_a_span(raw: bytes, span: bytes) -> dict:
    start = raw.index(span)
    end = start + len(span)
    return {"start_byte": start, "end_byte": end,
            "text_sha256": hashlib.sha256(raw[start:end]).hexdigest()}


@pytest.mark.parametrize("row", _TABLE_A, ids=[r[0] for r in _TABLE_A])
def test_figure_span_closed_rule_table_a(row):
    _, raw, span_text, text, sign, whole_document, expected = row
    raw_bytes = raw.encode("utf-8")
    span = _table_a_span(raw_bytes, span_text.encode("utf-8"))
    if expected is None:
        n._verify_figure_span("profit", span, text, sign, raw_bytes, whole_document=whole_document)
    else:
        with pytest.raises(n.DisclosureError) as caught:
            n._verify_figure_span("profit", span, text, sign, raw_bytes, whole_document=whole_document)
        assert caught.value.code == expected


# --- Fourth review (ruling 52): every row of the COO's coo_fourth.py probe,
# copied in as literals (ids prefixed r4-). Each row asserts admit, or refusal
# with a code that is one of FIGURE_SPAN_MISMATCH / FIGURE_SIGN_UNSUPPORTED.
# Non-ASCII and invisible characters are written as escapes. The cut is None
# (whole raw), ("f", s) first occurrence, ("l", s) last occurrence, or a
# (start, end) byte pair, exactly as the probe's cut_span. ---
_TABLE_R4 = [
    ('r4-P01_style_font_size_10pt', '<p style="font-size:10pt">Revenue 54,602</p>', ('f', '10'), '10', '+', True, False),
    ('r4-P02_same_prepare', '<p style="font-size:10pt">Revenue 54,602</p>', ('f', '10'), '10', '+', False, False),
    ('r4-P03_style_margin_top_6pt', '<td style="margin-top:6pt;width:50%">Revenue</td>', ('f', '6'), '6', '+', True, False),
    ('r4-P04_style_padding_0_5pt_ctl', '<td style="padding:0 5pt">x</td>', ('f', '5'), '5', '+', True, False),
    ('r4-P05_img_alt_words', '<img alt="Segment revenue 1,234 million">', ('f', '1,234'), '1,234', '+', True, False),
    ('r4-P06_title_words', '<td title="x 1,234 y">5</td>', ('f', '1,234'), '1,234', '+', True, False),
    ('r4-P07_title_bare_ctl', '<td title="1,234">5</td>', ('f', '1,234'), '1,234', '+', True, False),
    ('r4-P08_html_comment', '<!-- revenue 1,234 total -->54,602', ('f', '1,234'), '1,234', '+', True, False),
    ('r4-P09_script_body', '<script>var r = "a 1,234 b";</script>54,602', ('f', '1,234'), '1,234', '+', True, False),
    ('r4-P10_style_body_12px', '<style>.a{font-size:12px}</style>54,602', ('f', '12'), '12', '+', True, False),
    ('r4-P11_CDATA', '<![CDATA[ value 1,234 here ]]>', ('f', '1,234'), '1,234', '+', True, False),
    ('r4-P12_hex_ref_emdash_2014', 'Revenue&#x2014;54,602', ('f', '2014'), '2014', '+', True, False),
    ('r4-P13_hex_ref_nbsp_0', 'Revenue&#xA0;54,602', ('f', '0'), '0', '+', True, False),
    ('r4-P14_named_ref_frac12', 'Total &frac12; share', ('f', '12'), '12', '+', True, False),
    ('r4-P15_x_eats_54_prints_T_602', 'Revenue &#x54,602', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-P16_x1F_eats_54', 'Revenue &#x1F54,602', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-P17_tag_name_h2', '<h2 class="x">Revenue</h2>', ('f', '2'), '2', '+', True, False),
    ('r4-P18_colspan_ctl', '<td colspan="3">Revenue</td>', ('f', '3'), '3', '+', True, False),
    ('r4-P19_ix_contextRef_words', '<ix:nonFraction contextRef="c 3 x" name="a">54,602</ix:nonFraction>', ('f', '3'), '3', '+', True, False),
    ('r4-P20_display_none_span', 'Revenue <span style="display:none">1,234</span> 54,602', ('f', '1,234'), '1,234', '+', True, False),
    ('r4-P21_ix_hidden', '<ix:hidden>Revenue 1,234 total</ix:hidden>', ('f', '1,234'), '1,234', '+', True, False),
    ('r4-P22_decimal_split_across_cells', '<td>54,602</td><td>.5</td>', ('f', '54,602'), '54,602', '+', True, False),
    ('r4-X01_attr_order', 'Revenue <ix:nonFraction name="a" contextRef="c" sign="-" scale="3">54,602</ix:nonFraction>', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-X02_newline_spaces', 'Revenue <ix:nonFraction\n   sign = "-"\n  name="a">54,602</ix:nonFraction>', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-X03_prefix_ix2', 'Revenue <ix2:nonFraction sign="-">54,602</ix2:nonFraction>', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-X04_default_namespace', 'Revenue <nonFraction sign="-">54,602</nonFraction>', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-X05_sign_45', 'Revenue <ix:nonFraction sign="&#45;">54,602</ix:nonFraction>', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-X06_self_closing_neg_before', 'Revenue <ix:nonFraction sign="-"/> 54,602', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-X07_neg_closed_pos_after', 'Loss <ix:nonFraction sign="-">5</ix:nonFraction> and gain <ix:nonFraction name="g">54,602</ix:nonFraction>', ('l', '54,602'), '54,602', '+', True, True),
    ('r4-X08_nested_outer_neg', 'Revenue <ix:nonFraction sign="-" name="a"><ix:nonFraction name="b">54,602</ix:nonFraction></ix:nonFraction>', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-X09_close_tag_in_comment', 'Revenue <ix:nonFraction sign="-"><!--</ix:nonFraction>-->54,602</ix:nonFraction>', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-X10_unclosed_neg', 'Revenue <ix:nonFraction sign="-">54,602', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-X11_space_before', 'Revenue <ix:nonFraction sign="-" >54,602</ix:nonFraction>', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-X12_mixed_case_prefix', 'Revenue <Ix:NonFraction sign="-">54,602</Ix:NonFraction>', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-X13_prefix_ix2_prepare', 'Revenue <ix2:nonFraction sign="-">54,602</ix2:nonFraction>', ('l', '54,602'), '54,602', '+', False, False),
    ('r4-X14_neg_open_2000B_left_letter_filler', 'Revenue <ix:nonFraction sign="-"><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em>54,602</ix:nonFraction>', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-X15_sign_single_quotes_spaces', "Revenue <ix:nonFraction sign = '-'>54,602</ix:nonFraction>", ('l', '54,602'), '54,602', '+', True, False),
    ('r4-X16_ix_continuation_not_nonFraction', 'Revenue <ix:nonFraction sign="-"></ix:nonFraction><ix:continuation>54,602</ix:continuation>', ('l', '54,602'), '54,602', '+', True, True),
    ('r4-X17_neg_on_enclosing_span_not_ix', 'Revenue <span><ix:nonFraction sign="-" name="a"><b>54,602</b></ix:nonFraction></span>', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-W01_dash_just_inside_window', '-                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               54,602', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-W02_dash_just_outside_window', '-                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                54,602', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-W03_blank_2000_then_figure_replay', '                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                54,602', ('l', '54,602'), '54,602', '+', True, True),
    ('r4-W04_blank_2000_then_figure_prepare', '                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                54,602', ('l', '54,602'), '54,602', '+', False, False),
    ('r4-W05_blank_2001_then_figure_replay', '                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 54,602', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-W06_U_2212_whole_inside', '\u2212                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             54,602', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-W07_U_2212_cut_by_window_edge', '\u2212                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              54,602', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-W08_digit_just_inside_right', '54,602                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               5', ('f', '54,602'), '54,602', '+', True, False),
    ('r4-W09_U_2212_cut_at_right_edge', '54,602                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              \u2212', ('f', '54,602'), '54,602', '+', True, False),
    ('r4-W10_dash_just_inside_right', '54,602                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               -', ('f', '54,602'), '54,602', '+', True, False),
    ('r4-W11_dash_just_outside_right', '54,602                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                -', ('f', '54,602'), '54,602', '+', True, False),
    ('r4-W12_td_split_at_right_edge', '54,602                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             <td>9', ('f', '54,602'), '54,602', '+', True, False),
    ('r4-W13_td_split_at_left_edge', '9</td>                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             54,602', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-W14_e_acute_left_of_figure', '\xe954,602', ('l', '54,602'), '54,602', '+', True, True),
    ('r4-W15_span_starts_mid_char', 'x\u221254,602', (2, 10), '54,602', '-', True, False),
    ('r4-W16_span_ends_mid_char', '54,602\u2212', (0, 7), '54,602', '+', True, False),
    ('r4-W17_paren_then_1999B_of_tags', '(<em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><i>54,602)', None, '54,602', '-', True, True),
    ('r4-W18_letter_1_byte_beyond_left_window_dash_inside', '-<em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em><em>54,602', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-G01_text_with_newline', 'x 54602 y', ('f', '54602'), '54602\n', '+', True, False),
    ('r4-G02_text_leading_space', 'x 54,602 y', ('f', ' 54,602'), ' 54,602', '+', True, False),
    ('r4-G03_arabic_indic_digits', 'x \u0665\u0664 y', ('f', '\u0665\u0664'), '\u0665\u0664', '+', True, False),
    ('r4-G04_grouped_millions', 'x 1,234,567 y', ('f', '1,234,567'), '1,234,567', '+', True, True),
    ('r4-G05_text_as_int', 'x 54602 y', ('f', '54602'), 54602, '+', True, False),
    ('r4-G06_fullwidth_comma', 'x 54\uff0c602 y', ('f', '54\uff0c602'), '54,602', '+', True, False),
    ('r4-G07_5000_digit_figure', 'x 44444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444 y', ('f', '44444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444'), '44444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444', '+', True, False),
    ('r4-G08_text_1_234_printed_1234', 'x 1234 y', ('f', '1234'), '1,234', '+', True, False),
    ('r4-C01_sign_as_list', 'x 54,602 y', ('f', '54,602'), '54,602', ['+'], True, False),
    ('r4-C02_text_None', 'x 54,602 y', ('f', '54,602'), None, '+', True, False),
    ('r4-C03_sign_empty', 'x 54,602 y', ('f', '54,602'), '54,602', '', True, False),
    ('r4-S01_U_30FC_prolonged_mark', 'x \u30fc54,602', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-S02_U_4E00_CJK_one', 'x \u4e0054,602', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-S03_U_02C9_modifier_macron', 'x \u02c954,602', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-S04_U_2010_hyphen', 'x \u201054,602', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-S05_U_FE63_small_hyphen_minus', 'x \ufe6354,602', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-S06_U_FF0D_fullwidth_hyphen_minus', 'x \uff0d54,602', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-S25_U_30FC_prepare', 'x \u30fc54,602', ('l', '54,602'), '54,602', '+', False, False),
    ('r4-S26_right_U_FE63', '54,602\ufe63 x', ('f', '54,602'), '54,602', '+', True, False),
    ('r4-S18_trailing_U_2212', 'x 54,602\u2212', ('f', '54,602'), '54,602', '+', True, False),
    ('r4-S13_trailing_Cr', '54,602 Cr', ('f', '54,602'), '54,602', '+', True, False),
    ('r4-S14_trailing_cr', '54,602 cr.', ('f', '54,602'), '54,602', '+', True, False),
    ('r4-S15_trailing_DR_ctl', '54,602 DR', ('f', '54,602'), '54,602', '+', True, False),
    ('r4-S16_COVID_19_as_minus_19', 'COVID-19 cases', ('f', '-19'), '19', '-', True, False),
    ('r4-S17_model_X_1234_as_minus', 'Model X-1234 units', ('f', '-1234'), '1234', '-', True, False),
    ('r4-H01_EDGAR_table_row', '<tr><td>Segment A</td><td>$</td><td>54,602</td><td>&#160;</td></tr>', ('l', '54,602'), '54,602', '+', True, True),
    ('r4-H02_iXBRL_revenue_cell', '<td>Revenues</td><td style="text-align:right"><span style="font-size:10pt">$</span></td><td><span style="font-size:10pt"><ix:nonFraction unitRef="usd" contextRef="c-1" decimals="-6" name="us-gaap:Revenues" format="ixt:num-dot-decimal" scale="6">54,602</ix:nonFraction></span></td>', ('l', '54,602'), '54,602', '+', True, True),
    ('r4-H04_prose_with_percent', 'revenue decreased 5% to $54,602 million in 2024', ('l', '54,602'), '54,602', '+', True, True),
    ('r4-H05_year_cell_before', '<td>2024</td><td>54,602</td>', ('l', '54,602'), '54,602', '+', True, True),
    ('r4-H07_prepare_excerpt_cell', '<td>Segment A</td><td>$</td><td>54,602</td>', ('l', '54,602'), '54,602', '+', False, True),
    ('r4-K01_quoted_in_attribute', '<td title="a > 1,234 b">5</td>', ('f', '1,234'), '1,234', '+', True, False),
    ('r4-K02_quoted_single_quotes', "<td title='a > 1,234 b'>5</td>", ('f', '1,234'), '1,234', '+', True, False),
    ('r4-K03_title_element', '<title>Report 1,234 pages</title><p>x</p>', ('f', '1,234'), '1,234', '+', True, False),
    ('r4-K04_textarea', '<textarea>a 1,234 b</textarea>', ('f', '1,234'), '1,234', '+', True, False),
    ('r4-K05_head_meta', '<head><meta content="x"></head><body>a 1,234 b</body>', ('f', '1,234'), '1,234', '+', True, True),
    ('r4-K06_inside_head', '<head><base>a 1,234 b</head><body>x</body>', ('f', '1,234'), '1,234', '+', True, False),
    ('r4-K07_ix_header_resources', '<ix:header><ix:resources>a 1,234 b</ix:resources></ix:header>', ('f', '1,234'), '1,234', '+', True, False),
    ('r4-K08_visibility_hidden', 'x <span style="visibility: hidden">1,234</span> y', ('f', '1,234'), '1,234', '+', True, False),
    ('r4-K09_display_none_entity', 'x <span style="display&#58;none">1,234</span> y', ('f', '1,234'), '1,234', '+', True, False),
    ('r4-K10_hidden_attribute', 'x <span hidden>1,234</span> y', ('f', '1,234'), '1,234', '+', True, False),
    ('r4-K11_nested_in_display_none', 'x <div style="DISPLAY : NONE"><div>a</div> 1,234 </div> y', ('f', '1,234'), '1,234', '+', True, False),
    ('r4-K12_after_hidden_block_closed', 'x <div style="display:none"><div>a</div></div> revenue 1,234 y', ('f', '1,234'), '1,234', '+', True, True),
    ('r4-K13_unreadable_tag_before', 'x <a b"c> revenue 1,234 y', ('f', '1,234'), '1,234', '+', True, False),
    ('r4-K14_open_tag_never_closed', 'revenue <td style="x 1,234 y', ('f', '1,234'), '1,234', '+', True, False),
    ('r4-K15_comment_never_closed', 'revenue <!-- x 1,234 y', ('f', '1,234'), '1,234', '+', True, False),
    # Fix 9 addendum (ruling 81): wanted False. An XML parser reads the whole string as one comment, so the
    # figure is not shown; the row was right for the HTML reading only.
    ('r4-K16_empty_comment_then_text', '<!-->revenue 1,234 total-->', ('f', '1,234'), '1,234', '+', True, False),
    ('r4-K17_literal_ampersand_word', 'AT&T revenue 1,234 total', ('f', '1,234'), '1,234', '+', True, True),
    ('r4-K18_span_holds_a_numeric_ref', 'x &#49;,234 y', ('f', '&#49;,234'), '1,234', '+', True, False),
    ('r4-K19_excerpt_starts_inside_a_tag', 'font-size:10pt">Revenue 54,602</p>', ('f', '10'), '10', '+', False, False),
    ('r4-K20_excerpt_starts_inside_a_tag_honest', 'class="x">Revenue 54,602</p>', ('l', '54,602'), '54,602', '+', False, False),
    ('r4-K21_svg_text', '<svg><text>a 1,234 b</text></svg>', ('f', '1,234'), '1,234', '+', True, False),
    ('r4-K22_select_option', '<select><option>a 1,234 b</option></select>', ('f', '1,234'), '1,234', '+', True, False),
    ('r4-K23_span_straddles_a_tag_edge', '<b>x 1,234</b> y', ('f', '1,234</b'), '1,234', '+', True, False),
    ('r4-K24_semicolon_less_ref_eats_digits', 'x &nbsp54,602 y', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-K25_script_holds_a_fake_close_tag', '<script>var a="</td> 1,234 ";</script>', ('f', '1,234'), '1,234', '+', True, False),
    ('r4-L01_CR_on_the_left', 'CR 54,602', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-L02_Dr_on_the_left', 'balance Dr. 54,602', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-L03_crores_on_the_right', 'x 54,602 crores', ('f', '54,602'), '54,602', '+', True, True),
    ('r4-L04_word_ending_dr_before', 'x Hundr 54,602 y', ('l', '54,602'), '54,602', '+', True, True),
    ('r4-L05_cr_in_next_cell', '<td>x 54,602</td><td>Cr</td>', ('f', '54,602'), '54,602', '+', True, False),
    ('r4-L06_bidi_override_far_left', 'x \u202e- abc 54,602 y', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-L07_bidi_override_by_ref', 'x &#x202E;- abc 54,602 y', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-L08_ogham_space_mark', 'x \u1680 54,602 y', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-L09_greek_letter_before', 'x \u03b1 54,602', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-L10_minus_after_tagged_letter', 'X<b>-1234</b> units', ('f', '-1234'), '1234', '-', True, False),
    ('r4-L11_minus_after_a_blank', 'was -54,602 in', ('f', '-54,602'), '54,602', '-', True, True),
    ('r4-L12_parens_after_a_blank', 'was (54,602) in', ('f', '(54,602)'), '54,602', '-', True, True),
    ('r4-L13_parens_glued_to_a_word', 'Note(54,602) in', ('f', '(54,602)'), '54,602', '-', True, False),
    ('r4-L14_cdata_hides_a_dash', 'x <![CDATA[>-]]>54,602 y', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-L15_em_space_inside_span', 'x $\u200354,602 y', ('f', '$\u200354,602'), '54,602', '+', True, True),
    ('r4-M01_unquoted_sign', 'Revenue <ix:nonFraction sign=->54,602</ix:nonFraction>', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-M02_unicode_minus_sign', 'Revenue <ix:nonFraction sign="\u2212">54,602</ix:nonFraction>', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-M03_hex_entity_sign', 'Revenue <ix:nonFraction sign="&#x2D;">54,602</ix:nonFraction>', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-M04_outer_neg_far_left', 'Revenue <ix:nonFraction sign="-"><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><em>x</em><ix:nonFraction name="a" contextRef="c" scale="3">54,602</ix:nonFraction></ix:nonFraction>', ('l', '54,602'), '54,602', '+', True, False),
    ('r4-M05_two_closed_negs_then_plus', 'Loss <ix:nonFraction sign="-">5</ix:nonFraction> Loss <ix:nonFraction sign="-">5</ix:nonFraction> gain <ix:nonFraction name="a" contextRef="c" scale="3">54,602</ix:nonFraction>', ('l', '54,602'), '54,602', '+', True, True),
    ('r4-M06_neg_with_parens_declared_minus', 'x (<ix:nonFraction sign="-">54,602</ix:nonFraction>) y', ('f', '(<ix:nonFraction sign="-">54,602</ix:nonFraction>)'), '54,602', '-', True, True),
    ('r4-M07_nonfraction_in_comment_is_not_open', 'Revenue <!-- <ix:nonFraction sign="-"> --><ix:nonFraction name="a" contextRef="c" scale="3">54,602</ix:nonFraction>', ('l', '54,602'), '54,602', '+', True, True),
    ('r4-N01_21_digits', 'x 444444444444444444444 y', ('f', '444444444444444444444'), '444444444444444444444', '+', True, True),
    ('r4-N02_22_digits', 'x 4444444444444444444444 y', ('f', '4444444444444444444444'), '4444444444444444444444', '+', True, False),
    ('r4-N03_seven_groups', 'x 1,234,567,890,123,456,789 y', ('f', '1,234,567,890,123,456,789'), '1,234,567,890,123,456,789', '+', True, True),
    ('r4-N04_eight_groups', 'x 1,234,567,890,123,456,789,012 y', ('f', '1,234,567,890,123,456,789,012'), '1,234,567,890,123,456,789,012', '+', True, False),
    ('r4-H10_full_iXBRL_row', '<tr><td style="padding:0 5pt"><p style="margin:0"><span style="font-size:10pt">Cloud</span></p></td><td><span>$</span></td><td style="text-align:right"><span style="font-size:10pt"><ix:nonFraction name="a" contextRef="c" scale="3">54,602</ix:nonFraction></span></td><td>&#160;</td><td><span>$</span></td><td><span>48,310</span></td></tr>', ('f', '54,602'), '54,602', '+', True, True),
    ('r4-H11_loss_in_parens_across_cells', '<tr><td>Other</td><td>$</td><td>(54,602</td><td>)</td></tr>', ('f', '(54,602</td><td>)'), '54,602', '-', True, True),
    ('r4-H12_prose_in_millions', '<p>Segment revenue was $54,602 million, compared with $48,310 million.</p>', ('f', '54,602'), '54,602', '+', True, True),
    ('r4-H13_doctype_and_xml_head', '<?xml version="1.0"?><!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0//EN" "http://x"><html><head><title>10-K</title><style>td{font-size:10pt}</style></head><body><table><tr><td>Total</td><td>54,602</td></tr></table></body></html>', ('l', '54,602'), '54,602', '+', True, True),
    ('r4-H14_legacy_font_tags', '<TR><TD><FONT SIZE=2 FACE="Times New Roman">Product</FONT></TD><TD ALIGN=right NOWRAP><FONT SIZE=2>54,602</FONT></TD></TR>', ('l', '54,602'), '54,602', '+', True, True),
    ('r4-H15_prepare_excerpt_row', '<td>Cloud</td><td>$</td><td>54,602</td>', ('l', '54,602'), '54,602', '+', False, True),
    ('r4-H16_sentence_end_then_cell', '<td>of 54,602.</td><td>5</td>', ('l', '54,602'), '54,602', '+', True, True),
    ('r4-H17_width_percent_attr', '<td width=50%>Total</td><td>54,602</td>', ('l', '54,602'), '54,602', '+', True, True),
]

def _r4_span(raw: bytes, cut) -> dict:
    if cut is None:
        start, end = 0, len(raw)
    elif isinstance(cut[0], int):
        start, end = cut
    else:
        sb = cut[1].encode("utf-8")
        start = raw.find(sb) if cut[0] == "f" else raw.rfind(sb)
        assert start >= 0, cut
        end = start + len(sb)
    return {"start_byte": start, "end_byte": end,
            "text_sha256": hashlib.sha256(raw[start:end]).hexdigest()}


@pytest.mark.parametrize("row", _TABLE_R4, ids=[r[0] for r in _TABLE_R4])
def test_figure_span_fourth_review_table(row):
    _, raw, cut, text, sign, whole_document, want_admit = row
    raw_bytes = raw.encode("utf-8")
    span = _r4_span(raw_bytes, cut)
    if want_admit:
        n._verify_figure_span("profit", span, text, sign, raw_bytes, whole_document=whole_document)
    else:
        with pytest.raises(n.DisclosureError) as caught:
            n._verify_figure_span("profit", span, text, sign, raw_bytes, whole_document=whole_document)
        assert caught.value.code in ("FIGURE_SPAN_MISMATCH", "FIGURE_SIGN_UNSUPPORTED")


# --- B: end to end through prepare/adopt/qualify, refused at prepare ---------

def test_b_scale_attribute_not_a_figure_refused_at_prepare(tmp_path):
    # The scale="3" attribute is not the figure: the span prints 54,602, text "3".
    with pytest.raises(n.DisclosureError, match="FIGURE_SPAN_MISMATCH"):
        _profit_expression_case(tmp_path, '<ix:nonFraction scale="3">54,602</ix:nonFraction>',
                                profit=3.0, sign="+", text="3")


def test_b_decimals_attribute_not_a_sign_refused_at_prepare(tmp_path):
    # decimals="-3" is not a minus sign: the span prints 54,602, text "3", sign "-".
    with pytest.raises(n.DisclosureError, match="FIGURE_SPAN_MISMATCH"):
        _profit_expression_case(tmp_path, '<ix:nonFraction decimals="-3">54,602</ix:nonFraction>',
                                profit=-3.0, sign="-", text="3")


def test_b_en_dash_not_a_minus_refused_at_prepare(tmp_path):
    # The en dash is not a minus sign. Pin it as the FIRST figure so no other
    # figure's neighbour window sees the dash; the span prints "–54,602" while
    # text is "54,602" and sign "+", which is not a closed shape.
    expression = _EN_DASH + "54,602"
    body = (SEG_BODY_BASE + " " + expression + " revenue_denominator: 100 "
            "profit: 10 profit_denominator: 100").encode("utf-8")
    source = body.decode("utf-8")
    pos = source.index(expression)
    start = len(source[:pos].encode("utf-8"))
    end = len(source[:pos + len(expression)].encode("utf-8"))
    figure_specs = {
        "revenue": {"text": "54,602", "sign": "+", "scale": "units"},
        "revenue_denominator": {"text": "100", "sign": "+", "scale": "units"},
        "profit": {"text": "10", "sign": "+", "scale": "units"},
        "profit_denominator": {"text": "100", "sign": "+", "scale": "units"}}
    figure_spans = {
        "revenue": {"start_byte": start, "end_byte": end,
                    "text_sha256": hashlib.sha256(body[start:end]).hexdigest()},
        "revenue_denominator": _figure_span_for(body, "revenue_denominator", "100"),
        "profit": _figure_span_for(body, "profit", "10"),
        "profit_denominator": _figure_span_for(body, "profit_denominator", "100")}
    with pytest.raises(n.DisclosureError, match="FIGURE_SPAN_MISMATCH"):
        _segment_case(tmp_path, revenue=54602.0, body=body,
                      figure_specs=figure_specs, figure_spans=figure_spans)


# --- C: a span cut to the digits inside printed parentheses, refused at replay ---

def test_c_cut_span_inside_parentheses_refused_at_replay(tmp_path):
    # Prepare a valid loss fact, then cut the profit span to the digits while the
    # document still prints parentheses around it and declare "+": refused at replay.
    case = _profit_expression_case(tmp_path, "(54,602)", profit=-54602.0, sign="-")
    body = case.receipt["span_text"].encode("utf-8")
    digits = b"54,602"
    pos = body.index(digits)
    spec = copy.deepcopy(case.snapshot.spec)
    spec["fact"]["figure_spans"]["profit"] = {
        "start_byte": pos, "end_byte": pos + len(digits),
        "text_sha256": hashlib.sha256(body[pos:pos + len(digits)]).hexdigest()}
    spec["fact"]["profit_sign"] = "+"
    spec["fact"]["profit"] = 54602.0
    snapshot = SimpleNamespace(spec=spec, bindings=dict(case.snapshot.bindings))
    source = segment.PinnedSegmentSource(snapshot, case.pinned.authority)
    with pytest.raises(n.DisclosureError, match="FIGURE_SIGN_UNSUPPORTED"):
        _read_source(source, spec["edition"])


# --- D: the four reviewer probes from round 2 must still be refused ----------

def test_d_round2_reviewer_probes_still_refused(tmp_path):
    # Each probe builds its own pinned fixture, so each needs its own directory.
    # Probe 1: span "30", text "3".
    def probe1(a):
        a["revenue"] = 3.0
        a["revenue_text"] = "3"
    with pytest.raises(n.DisclosureError, match="FIGURE_SPAN_MISMATCH"):
        _segment_case(tmp_path / "p1", revenue=30.0, mutate_assertion=probe1)
    # Probe 2: "(54,602)" declared "+".
    with pytest.raises(n.DisclosureError, match="FIGURE_SIGN_UNSUPPORTED"):
        _profit_expression_case(tmp_path / "p2", "(54,602)", profit=54602.0, sign="+")
    # Probe 3: "(Note 5) 54,602 (a)" declared "-".
    with pytest.raises(n.DisclosureError, match="FIGURE_SPAN_MISMATCH"):
        _profit_expression_case(tmp_path / "p3", "(Note 5) 54,602 (a)", profit=-54602.0, sign="-")
    # Probe 4: revenue altered to 90.0 at adopt, qualify and replay.
    case = _segment_case(tmp_path / "p4")
    prepared = copy.deepcopy(case.prepared)
    prepared["proposed_fact"]["revenue"] = 90.0
    with pytest.raises(n.DisclosureError, match="FIGURE_TEXT_MISMATCH"):
        segment.adopt_segment_input(prepared, adopted_at="2024-03-05T10:00:00Z",
                                    ruling_raw=canon(case.policy), theme_sources_raw=case.theme,
                                    identity_observed_at="2024-03-03T10:00:00Z")
    spec = copy.deepcopy(case.spec)
    spec["fact"]["revenue"] = 90.0
    with pytest.raises(n.DisclosureError, match="FIGURE_TEXT_MISMATCH"):
        o.qualify_records("a" * 40, canon(spec), canon(case.policy), case.registry,
                          case.identities, theme_sources_raw=case.theme)
    spec = copy.deepcopy(case.snapshot.spec)
    spec["fact"]["revenue"] = 90.0
    snapshot = SimpleNamespace(spec=spec, bindings=dict(case.snapshot.bindings))
    source = segment.PinnedSegmentSource(snapshot, case.pinned.authority)
    with pytest.raises(n.DisclosureError, match="FIGURE_TEXT_MISMATCH"):
        _read_source(source, spec["edition"])


# ---------------------------------------------------------------------------
# Fifth review round: the proposal path replays the pinned source before any
# ledger write (the disclosure store does not admit a segment fact).
# ---------------------------------------------------------------------------

_R5_ATTR_BODY = (SEG_BODY_BASE + ' <td colspan="30"> revenue: 30 revenue_denominator: 100'
                 ' profit: 10 profit_denominator: 100').encode("utf-8")


def _r5_tampered_snapshot(case):
    """The honest snapshot with the revenue span moved onto the digits of colspan="30"."""
    body = _R5_ATTR_BODY
    digits = b"30"
    pos = body.index(b'colspan="30"') + len(b'colspan="')
    spec = copy.deepcopy(case.snapshot.spec)
    spec["fact"]["figure_spans"]["revenue"] = {
        "start_byte": pos, "end_byte": pos + len(digits),
        "text_sha256": hashlib.sha256(body[pos:pos + len(digits)]).hexdigest()}
    return SimpleNamespace(spec=spec, bindings=dict(case.snapshot.bindings))


def _r5_attr_case(tmp_path):
    return _segment_case(tmp_path, body=_R5_ATTR_BODY)


def _r5_wire_cli(monkeypatch, snapshot, authority):
    """Point the proposal CLI at one snapshot and one authority; no real owner or store."""
    monkeypatch.setattr(o, "CommittedDisclosureSource",
                        lambda root, **kwargs: SimpleNamespace(snapshot=lambda: snapshot))
    monkeypatch.setattr(cli, "_segment_source_authority", lambda snap: authority)
    monkeypatch.setattr(me, "_default_activity_identity", _segment_identity_reader)


def _r5_propose_argv(ledger):
    return ["propose", "--issuer", SEG_NODE, "--theme", TARGET, "--role", "operator",
            "--knowledge-cutoff", KNOWLEDGE_CUTOFF, "--created", CREATED,
            "--code-version", CODE_VERSION, "--ledger", str(ledger),
            "--segment-packet", "a", "b", "c", "--exposure-role", "primary", "--profit-driver"]


def test_r5_replay_honest_segment_source_returns_none(tmp_path):
    case = _segment_case(tmp_path)
    assert segment.replay_segment_source(case.snapshot, case.pinned.authority) is None


def test_r5_replay_refuses_figure_span_moved_onto_tag_attribute_digits(tmp_path):
    case = _r5_attr_case(tmp_path)
    assert segment.replay_segment_source(case.snapshot, case.pinned.authority) is None
    tampered = _r5_tampered_snapshot(case)
    with pytest.raises(n.DisclosureError) as caught:
        segment.replay_segment_source(tampered, case.pinned.authority)
    assert caught.value.code == "FIGURE_SPAN_MISMATCH"


def test_r5_replay_refuses_fact_form_differing_from_pinned_manifest_form(tmp_path):
    case = _segment_case(tmp_path)  # manifest and fact both 10-K
    spec = copy.deepcopy(case.snapshot.spec)
    spec["fact"]["form_type"] = "20-F"
    snapshot = SimpleNamespace(spec=spec, bindings=dict(case.snapshot.bindings))
    with pytest.raises(n.DisclosureError) as caught:
        segment.replay_segment_source(snapshot, case.pinned.authority)
    assert caught.value.code == "SEGMENT_FORM_NOT_ADMITTED"


def test_r5_cli_honest_segment_packet_writes_one_proposed_row(tmp_path, monkeypatch, capsys):
    case = _segment_case(tmp_path)
    ledger = tmp_path / "ledger" / "activity_proposals.jsonl"
    _r5_wire_cli(monkeypatch, case.snapshot, case.pinned.authority)
    rc = cli.main(_r5_propose_argv(ledger))
    assert rc == 0, capsys.readouterr().err
    rows = probation.read_activity_proposals(ledger)
    assert len(rows) == 1 and rows[0]["status"] == "PROPOSED"


def test_r5_cli_tampered_figure_span_refused_before_any_ledger_write(tmp_path, monkeypatch, capsys):
    case = _r5_attr_case(tmp_path)
    ledger = tmp_path / "ledger" / "activity_proposals.jsonl"
    _r5_wire_cli(monkeypatch, _r5_tampered_snapshot(case), case.pinned.authority)
    rc = cli.main(_r5_propose_argv(ledger))
    assert rc == 2
    err = capsys.readouterr().err
    assert "SOURCE_OWNER_REFUSED" in err and "FIGURE_SPAN_MISMATCH" in err
    assert not ledger.exists()


def test_r5_cli_replay_is_mandatory_authority_failure_blocks_the_ledger(tmp_path, monkeypatch, capsys):
    case = _segment_case(tmp_path)
    ledger = tmp_path / "ledger" / "activity_proposals.jsonl"
    _r5_wire_cli(monkeypatch, case.snapshot, case.pinned.authority)

    def unavailable(snapshot):
        raise n.DisclosureError("SEC_NATIVE_SOURCE_STORE_UNAVAILABLE")
    monkeypatch.setattr(cli, "_segment_source_authority", unavailable)
    rc = cli.main(_r5_propose_argv(ledger))
    assert rc == 2
    err = capsys.readouterr().err
    assert "SOURCE_OWNER_REFUSED" in err and "SEC_NATIVE_SOURCE_STORE_UNAVAILABLE" in err
    assert not ledger.exists()


def test_r5_factory_refuses_local_source_override_before_any_store_construction(monkeypatch):
    from engine.research_vault import r2_store
    monkeypatch.setenv("RESEARCH_LOCAL_STORE", "/must-not-be-created")
    monkeypatch.setattr(r2_store, "build_store", lambda: pytest.fail("store constructed before refusal"))
    with pytest.raises(n.DisclosureError, match="SEC_LOCAL_SOURCE_OVERRIDE_REFUSED"):
        cli._segment_source_authority(None)


@pytest.mark.parametrize("store", [None, object()])
def test_r5_factory_refuses_unavailable_or_alternate_store(monkeypatch, store):
    from engine.research_vault import r2_store
    monkeypatch.delenv("RESEARCH_LOCAL_STORE", raising=False)
    monkeypatch.setattr(r2_store, "build_store", lambda: store)
    with pytest.raises(n.DisclosureError, match="SEC_NATIVE_SOURCE_STORE_UNAVAILABLE"):
        cli._segment_source_authority(None)


def test_r5_factory_builds_the_native_authority_from_the_native_store(monkeypatch):
    from engine.fundamental_forensics import filing_attestation
    from engine.research_vault import r2_store
    monkeypatch.delenv("RESEARCH_LOCAL_STORE", raising=False)

    class NativeStore:
        available = True
    store = NativeStore()
    monkeypatch.setattr(r2_store, "R2Store", NativeStore)
    monkeypatch.setattr(r2_store, "build_store", lambda: store)
    calls = []

    def authority(**kwargs):
        calls.append(kwargs)
        return "native-authority"
    monkeypatch.setattr(filing_attestation, "PinnedSourceAuthority", authority)
    snapshot = SimpleNamespace(spec={"edition": {"schema": n.SEC_EDITION_SCHEMA,
                                                 "sec_source": {"snapshot_id": "ffsecsrc_" + "b" * 64}}})
    assert cli._segment_source_authority(snapshot) == "native-authority"
    assert calls == [{"store": store, "snapshot_id": "ffsecsrc_" + "b" * 64}]


class _R5Store:
    def __init__(self):
        self.objects = {}
        self.reads = self.writes = self.capabilities = 0

    def validate_strict_conditional_write_capability(self):
        self.capabilities += 1

    def get_bytes_strict_bounded(self, key, *, expected_byte_length, max_byte_length):
        self.reads += 1
        return self.objects.get(key)

    def get_bytes_strict_bounded_versioned(self, key, maximum_bytes):
        self.reads += 1
        return n.VersionedBytes(None, None)

    def put_bytes_strict_conditional(self, key, raw, *, expected_version, content_type):
        self.writes += 1
        self.objects[key] = raw
        return True


class _R5Reader:
    def __init__(self):
        self.calls = []

    def read_source(self, **binding):
        self.calls.append(binding)
        return b""


class _R5Authority:
    def __init__(self, admission):
        self.admission = admission

    def resolve(self, request, candidate=None):
        return self.admission

    def authorize_publication(self, request, candidate):
        return self.admission


def test_r5_store_path_does_not_admit_a_segment_fact_so_it_never_reads_the_source(tmp_path):
    """Tripwire. The disclosure store does not admit a segment fact at this head: the
    segment edition carries SEC_EDITION_SCHEMA but Admission.validate demands
    EDITION_SCHEMA for every non-supplier fact, so publish_disclosure refuses before
    any source read. Whoever opens that admission must keep the whole-document figure
    check (the PinnedSegmentSource.read_source path) on the write.
    """
    case = _segment_case(tmp_path)
    edition, fact = case.snapshot.spec["edition"], case.snapshot.spec["fact"]
    request = n.Request(fact["fact_id"], n.SEC_SUPPLIER_PURPOSE, n.SEC_SUPPLIER_AUDIENCE)
    admission = n.Admission(
        request, n.validate_fact(fact), n.validate_edition(edition), "fixture-generation-1",
        "fixture:disclosures", "DERIVED", "4" * 64, "5" * 64, "6" * 64, "7" * 64, "8" * 64,
        fact["known_at"], "date", "current", frozenset({"fact_id", "kind", "lifecycle"}),
        operation="publish")
    store, reader = _R5Store(), _R5Reader()
    with pytest.raises(n.DisclosureError) as caught:
        n.publish_disclosure(store, _R5Authority(admission), request, edition=edition, fact=fact,
                             source_reader=reader)
    assert caught.value.code == "ADMISSION_REFERENCE_INVALID"
    assert reader.calls == []
    assert store.objects == {} and store.writes == 0


# ---------------------------------------------------------------------------
# Sixth review (ruling 61): the figure check admits only markup it knows. Every
# case below is the exact input of the fifth reviewer's probe (~ stands for a
# double quote; [[ ]] marks the figure span).
# ---------------------------------------------------------------------------

_R6_NX = "<p>Next line</p>"


def _r6_verify(doc: str, text="1,234", sign="+"):
    doc = doc.replace("~", chr(34))
    i, j = doc.index("[["), doc.index("]]")
    raw = (doc[:i] + doc[i + 2:j] + doc[j + 2:]).encode("utf-8")
    start = len(doc[:i].encode("utf-8"))
    end = start + len(doc[i + 2:j].encode("utf-8"))
    span = {"start_byte": start, "end_byte": end, "text_sha256": hashlib.sha256(raw[start:end]).hexdigest()}
    n._verify_figure_span("revenue", span, text, sign, raw)


def _r6_refused(doc: str, text="1,234", sign="+"):
    with pytest.raises(n.DisclosureError) as caught:
        _r6_verify(doc, text, sign)
    assert caught.value.code == "FIGURE_SPAN_MISMATCH"


@pytest.mark.parametrize("doc", [
    "<p>Intro</p><span style=~display:none~><p></span>Revenue [[1,234]]</p>" + _R6_NX,
    "<p>Intro</p><div hidden><table><tr><td></div>Revenue [[1,234]]</td></tr></table></div>" + _R6_NX,
], ids=["A1_span_close_ignored_by_p", "A2_div_close_ignored_in_td"])
def test_r6_1_hidden_region_with_broken_nesting_stays_hidden(doc):
    _r6_refused(doc)


def test_r6_1_a_self_closed_tag_inside_a_hidden_region_opens_an_element():
    # <b/> reads as an opening <b> in HTML: the </div> then no longer closes the region.
    _r6_refused("<p>Intro</p><div hidden><b/></div>Revenue [[1,234]] total</p>" + _R6_NX)


@pytest.mark.parametrize("doc", [
    "<p>Intro</p><dialog>Revenue [[1,234]] total</dialog>" + _R6_NX,
    "<p>Intro</p><ruby>x<rp>Revenue [[1,234]] total</rp></ruby>" + _R6_NX,
    "<p>Intro</p><plaintext></plaintext>Revenue [[1,234]] total",
    "<p>Intro</p><audio>Revenue [[1,234]] total</audio>" + _R6_NX,
    "<p>Intro</p><canvas>Revenue [[1,234]] total</canvas>" + _R6_NX,
    "<details><summary>Note</summary>Revenue [[1,234]] total</details>" + _R6_NX,
], ids=["A3_dialog", "A6_rp_in_ruby", "A16_plaintext_close", "A4_audio", "A5_canvas", "A10_details"])
def test_r6_2_unknown_element_names_are_refused(doc):
    _r6_refused(doc)


def test_r6_2_an_unknown_prefixed_name_is_refused():
    _r6_refused("<p>Revenue <foo:bar>[[1,234]]</foo:bar> total</p>" + _R6_NX)


@pytest.mark.parametrize("doc", [
    "<p>Intro</p><span style=~display:/**/none~>Revenue [[1,234]] total</span>" + _R6_NX,
    "<p>Intro</p><span style=~display:\\6e one~>Revenue [[1,234]] total</span>" + _R6_NX,
    "<p>Intro</p><span style=~display&#58;block~>Revenue [[1,234]] total</span>" + _R6_NX,
    "<p>Segment</p><p dir=~rtl~>[[1,234]] abc -</p>" + _R6_NX,
], ids=["A7_css_comment", "A8_css_escape", "ampersand_in_style", "A15_dir_attribute"])
def test_r6_3_style_that_cannot_be_read_plainly_and_dir_are_refused(doc):
    _r6_refused(doc)


@pytest.mark.parametrize("doc,text", [
    ("<p>Revenue 5<br style=~display:none~>[[1,234]] total</p>" + _R6_NX, "1,234"),
    ("<p>Revenue 5.<br style=~display:none~>[[234]] total</p>" + _R6_NX, "234"),
    ("<p>Revenue</p><p style=~display:inline~>5</p><p style=~display:inline~>[[1,234]]</p>" + _R6_NX, "1,234"),
], ids=["A13_hidden_br_joins_digits", "A14_hidden_br_joins_decimal", "A12_inline_p_digit_fragment"])
def test_r6_4_a_styled_block_tag_is_not_a_separator(doc, text):
    _r6_refused(doc, text)


def test_r6_honest_shapes_stay_admitted():
    ix = ("<tr><td><span>Cloud</span></td><td>$</td><td style=~text-align:right~><ix:nonFraction"
          " name=~us-gaap:Revenues~ contextRef=~c1~ unitRef=~usd~ decimals=~-6~ scale=~6~"
          " format=~ixt:num-dot-decimal~>[[54,602]]</ix:nonFraction></td><td>&#160;</td><td>$</td>"
          "<td>48,000</td></tr>")
    _r6_verify(ix + _R6_NX, "54,602")                                                   # H1
    _r6_verify("<tr><td>Operating loss</td><td>$</td><td>[[(</td><td><ix:nonFraction sign=~-~"
               " name=~x~>1,234</ix:nonFraction></td><td>)]]</td></tr>" + _R6_NX, "1,234", "-")  # H2


def test_r6_honest_shape_h3_xhtml_head_ixheader_stays_admitted():
    _r6_verify("<?xml version=~1.0~?><!DOCTYPE html><html><head><title>10-K</title></head><body>"
               "<div style=~display:none~><ix:header><ix:hidden/></ix:header></div>"
               "<p>Cloud revenue $[[54,602]] million</p>" + _R6_NX, "54,602")


def test_r6_1a_a_prefixed_self_closed_tag_in_a_hidden_region_is_an_empty_element():
    _r6_verify("<?xml version=~1.0~?><html><body><div hidden><link:schemaRef xlink:href=~x~/></div>"
               "<p>Cloud revenue $[[54,602]] million</p>" + _R6_NX, "54,602")


def test_r6_1a_a_prefixed_tag_not_self_closed_still_opens_an_element():
    _r6_refused("<p>Intro</p><div hidden><ix:hidden></div>Revenue [[1,234]] total</p>" + _R6_NX)


def test_r6_h10_sgml_text_table_is_refused():
    # accepted limit, ruling 61: pre-2001 SGML text filings are refused
    _r6_refused("<TABLE>\n<S> <C>\nCloud ........ $ [[54,602]] $ 48,000\n</TABLE>" + _R6_NX, "54,602")


def _r6_outside_span_snapshot(case):
    """The honest snapshot with the activity span cut to the first sentence, so the
    (still correct, whole-document) figure spans lie outside it."""
    spec = copy.deepcopy(case.snapshot.spec)
    first = SEG_BODY_BASE.encode("utf-8")[:24]
    assert spec["fact"]["figure_spans"]["revenue"]["start_byte"] >= len(first)
    spec["fact"]["span"] = {"start_byte": 0, "end_byte": len(first),
                            "text_sha256": hashlib.sha256(first).hexdigest()}
    return SimpleNamespace(spec=spec, bindings=dict(case.snapshot.bindings))


def test_r6_5_replay_refuses_a_figure_span_outside_the_activity_span(tmp_path):
    case = _segment_case(tmp_path)
    assert segment.replay_segment_source(case.snapshot, case.pinned.authority) is None
    with pytest.raises(n.DisclosureError) as caught:
        segment.replay_segment_source(_r6_outside_span_snapshot(case), case.pinned.authority)
    assert caught.value.code == "SOURCE_SPAN_MISMATCH"


def test_r6_5_replay_honest_source_still_returns_none(tmp_path):
    test_r5_replay_honest_segment_source_returns_none(tmp_path)


# ---------------------------------------------------------------------------
# Seventh review (ruling 67): the exact inputs of the sixth reviewer's probe
# (B1..B6, B9) plus the sc-tag and replay-bounds cases.
# ---------------------------------------------------------------------------

_R7_PAD = "<p>" + "pad " * 600 + "</p>"


@pytest.mark.parametrize("doc", [
    "<p>Intro</p><ix:nonNumeric style=~display:none~ name=~a~><ix:nonNumeric name=~b~/></ix:nonNumeric>"
    "Revenue [[1,234]] total</p>" + _R6_NX,
    "<p>Intro</p><x:span hidden><x:span/></x:span>Revenue [[1,234]] total" + _R6_NX,
], ids=["B1_ix_selfclose_same_name_hidden", "B1b_x_span_hidden_attr"])
def test_r7_1_flagged_self_closed_entry_named_like_the_closing_tag_is_permanent(doc):
    _r6_refused(doc)


@pytest.mark.parametrize("doc", [
    "<p>Intro</p><x:title><div hidden></x:title>" + _R7_PAD + "Revenue [[1,234]] total</div>" + _R6_NX,
    "<p>Intro</p><x:title><div hidden></x:title>Revenue [[1,234]] total</div>" + _R6_NX,
], ids=["B2_prefixed_rawtext_far", "B2b_prefixed_rawtext_near"])
def test_r7_2_a_prefixed_name_is_not_raw_text(doc):
    _r6_refused(doc)


def test_r7_3_a_misnested_inline_block_is_refused():
    _r6_refused("<p>Revenue</p><p style=~display:inline~>5<b></p><p style=~display:inline~>[[1,234]]</p>" + _R6_NX)


@pytest.mark.parametrize("early", ["<span/>", "<td/>"])
def test_r7_3_a12_after_an_earlier_sc_tag_is_still_refused(early):
    _r6_refused(early + "<p>Revenue</p><p style=~display:inline~>5</p>"
                "<p style=~display:inline~>[[1,234]]</p>" + _R6_NX)


@pytest.mark.parametrize("doc", [
    "<p>Revenue 5<td>[[1,234]]</td> total</p>" + _R6_NX,
    "<div>Revenue 5<tr>[[1,234]] total</div>" + _R6_NX,
    "<div>Revenue 5<caption>[[1,234]] total</div>" + _R6_NX,
    "<div>Revenue 5<table>[[1,234]]<tr><td>x</td></tr></table></div>" + _R6_NX,
    "<div>Revenue 5<table><tr><td>x</td></tr>[[1,234]]</table> total</div>" + _R6_NX,
], ids=["B3_td_outside_table", "B3b_tr_outside_table", "B3d_caption_outside",
        "B4_foster_before_tr", "B4b_foster_after_tr"])
def test_r7_4_the_table_content_model_is_enforced(doc):
    _r6_refused(doc)


def test_r7_5_style_direction_is_unreadable():
    _r6_refused("<p>Segment</p><p style=~direction:rtl~>[[1,234]] abc -</p>" + _R6_NX)


def test_r7_6_img_alt_holding_a_digit_is_refused():
    _r6_refused("<p>Revenue <img src=~x~ alt=~5~>[[1,234]] total</p>" + _R6_NX)


@pytest.mark.parametrize("start,end", [(-5, 99999), (0, 10 ** 9)], ids=["negative_start", "end_past_body"])
def test_r7_7_replay_refuses_an_activity_span_outside_the_body(tmp_path, start, end):
    case = _segment_case(tmp_path)
    spec = copy.deepcopy(case.snapshot.spec)
    body_len = spec["edition"]["source_byte_length"]
    spec["fact"]["span"] = {"start_byte": start, "end_byte": end if end < 10 ** 9 else body_len + 7,
                            "text_sha256": spec["fact"]["span"]["text_sha256"]}
    snapshot = SimpleNamespace(spec=spec, bindings=dict(case.snapshot.bindings))
    with pytest.raises(n.DisclosureError) as caught:
        segment.replay_segment_source(snapshot, case.pinned.authority)
    assert caught.value.code == "SOURCE_SPAN_MISMATCH"


# Ruling 70: R7-3a (stray closing tag with nothing open) and R7-8 (empty hidden cell).

def test_r7_3a_a_stray_closing_tag_with_something_open_is_still_refused():
    _r6_refused("<div>Revenue</td>5 <b>[[1,234]]</b> total</div>" + _R6_NX)


def test_r7_3a_a_stray_closing_tag_with_nothing_open_is_ignored():
    _r6_verify("$</td><td>[[1,234]]</td></tr>" + _R6_NX)


_R7_8_ROW = ("<table><tr><td>Revenue</td><td style=~display:none~/>{mid}"
             "{nxt}[[1,234]]</td></tr></table>" + _R6_NX)


def test_r7_8_a_empty_hidden_cell_before_a_cell_is_admitted():
    _r6_verify(_R7_8_ROW.format(mid="", nxt="<td>"))


def test_r7_8_b_text_after_the_hidden_cell_is_refused():
    _r6_refused(_R7_8_ROW.format(mid="5", nxt="<td>"))


def test_r7_8_c_an_inline_tag_after_the_hidden_cell_is_refused():
    _r6_refused(_R7_8_ROW.format(mid="", nxt="<span>"))


def test_r7_8_d_a_hidden_self_closed_div_before_a_cell_is_refused_as_today():
    _r6_refused("<table><tr><td>Revenue</td><div style=~display:none~/><td>[[1,234]]</td></tr></table>" + _R6_NX)


def test_r7_8_e_hidden_cell_then_row_end_then_new_row_is_admitted():
    _r6_verify("<table><tr><td>Revenue</td><td style=~display:none~/></tr>"
               "<tr><td>[[1,234]]</td></tr></table>" + _R6_NX)


def test_r7_8_f_hidden_cell_followed_by_a_closing_cell_is_refused():
    # refused as today: the region opens and its end is a not-printed neighbour
    with pytest.raises(n.DisclosureError) as caught:
        _r6_verify("<table><tr><td>Revenue</td><td style=~display:none~/></td>"
                   "<td>[[1,234]]</td></tr></table>" + _R6_NX)
    assert caught.value.code == "FIGURE_SIGN_UNSUPPORTED"


# ---------------------------------------------------------------------------
# Eighth review (ruling 73): the exact inputs of the seventh reviewer's probe.
# ---------------------------------------------------------------------------

_R8_VT = chr(11)
_R8_H = "<html><body>"
_R8_T = "</body></html>"


@pytest.mark.parametrize("doc", [
    _R8_H + "<table><tr><td>Revenue</td><td style=~display:none~/><td" + _R8_VT + ">[[1,234]]</td><td>x</td></tr></table>" + _R8_T,
    _R8_H + "<table><tr><td>Revenue</td><td style=~display:none~/><td" + _R8_VT + "class=~c~>[[1,234]]</td><td>x</td></tr></table>" + _R8_T,
    _R8_H + "<table><tr><td>Revenue</td><td style=~display:none~/></tr" + _R8_VT + "><tr><td>[[1,234]]</td></tr></table>" + _R8_T,
], ids=["VT_td", "VT_td_attr", "VT_tr"])
def test_r8_1_a_vertical_tab_is_refused(doc):
    _r6_refused(doc)


@pytest.mark.parametrize("doc", [
    _R8_H + "<div>Revenue 7<table/></div><b>[[1,234]]</b>" + _R8_T,
    _R8_H + "<div>7<table/></div><b>[[1,234]]</b><p>tail</p>" + _R8_T,
    _R8_H + "<div>Revenue 7<table/></div>[[1,234]]" + _R8_T,
    _R8_H + "<p>Revenue 7<table/></p><span>[[1,234]]</span>" + _R8_T,
    _R8_H + "<div>Revenue 7<TABLE/></div><b>[[1,234]]</b>" + _R8_T,
    _R8_H + "<div>Revenue 7<tbody/></div><b>[[1,234]]</b>" + _R8_T,
], ids=["sc_table_div", "sc_table_div2", "sc_table_plain", "sc_table_p", "sc_TABLE_up", "sc_tbody"])
def test_r8_2_a_self_closed_table_part_is_refused(doc):
    _r6_refused(doc)


def test_r8_2_a_properly_closed_empty_table_is_admitted():
    _r6_verify(_R8_H + "<div>Revenue 7<table></table></div><b>[[1,234]]</b>" + _R8_T)


@pytest.mark.parametrize("doc", [
    _R8_H + "<div><span>7<table></span><tr><td>" + "A" * 2100 + "</td></tr><b>[[1,234]]</b></div>" + _R8_T,
    _R8_H + "<div><span>7<table></span><tr><td>AAA</td></tr><b>[[1,234]]</b></div>" + _R8_T,
    "<html><body><div><span style=~direction:rtl~><p></span>" + "A" * 2100 + "<b>[[1,234]]</b></div></body></html>",
], ids=["desync_win", "desync_inwin", "misnest_far_before_window"])
def test_r8_3_a_nesting_fault_is_refused_wherever_it_lies(doc):
    _r6_refused(doc)


# Ruling 74: R8-4, the root attribute merge.

_R8_PAD = "<p>" + "A" * 2100 + "</p>"


@pytest.mark.parametrize("doc", [
    "</p><div><sub>[[1,234]]<h4>,<body hidden><br><h3/>",
    "<html><body><p>Revenue [[1,234]] total</p>" + _R8_PAD + "<body hidden></body></html>",
    "<html><body><p>Revenue [[1,234]] total</p>" + _R8_PAD + "<html style=~display:none~></body></html>",
    "<html><body><p>Revenue [[1,234]] total</p>" + _R8_PAD + "<body dir=~rtl~></body></html>",
    "<html><body style=~direction:rtl~></body>" + _R8_PAD + "<p>Revenue [[1,234]] total</p></html>",
], ids=["oracle_4989", "late_body_hidden", "late_html_display_none", "late_body_dir", "only_body_direction"])
def test_r8_4_a_root_tag_that_could_hide_or_merge_is_refused(doc):
    _r6_refused(doc)


def test_r8_4_a_plain_page_is_admitted():
    _r6_verify("<html><body><p>Revenue [[1,234]] total</p></body></html>" + _R6_NX)


def test_r8_4_a_fragment_with_neither_tag_is_admitted():
    _r6_verify("<p>Revenue [[1,234]] total</p>" + _R6_NX)


# ---------------------------------------------------------------------------
# Ninth review (ruling 80): R9-1 to R9-5. ~ stands for a double quote; [[ ]] marks the span.
# ---------------------------------------------------------------------------

_R9_NS = "http://www.w3.org/1999/xhtml"
_R9_HEAD = "<?xml version=~1.0~ encoding=~UTF-8~?><html xmlns=~" + _R9_NS + "~><body>"
_R9_TAIL = "</body></html>"


def _r9_doc(body: str, head: str = _R9_HEAD) -> str:
    return head + body + _R9_TAIL


def _r9_refused(body: str, head: str = _R9_HEAD):
    _r6_refused(_r9_doc(body, head))


def _r9_admitted(body: str, head: str = _R9_HEAD):
    _r6_verify(_r9_doc(body, head))


def test_r9_template_is_admitted():
    _r9_admitted("<p>Revenue [[1,234]] total</p>")


@pytest.mark.parametrize("body", [
    "<p>5&#x200F;:[[1,234]]</p>",
    "<p>Net -&#x200F;:[[1,234]]</p>",
    "<p>5‏:[[1,234]]</p>",
    "<p>Net -‏:[[1,234]]</p>",
    "<p>5&#x61C;:[[1,234]]</p>",
    "<p>5&#x200F;)[[1,234]]</p>",
    "<table><tr><td>5&#x200F;)[[1,234]]</td></tr></table>",
    "<p>5א:[[1,234]]</p>",
    "<p>-א:[[1,234]]</p>",
    "<p>-א)[[1,234]]</p>",
    "<p>-ا:[[1,234]]</p>",
    "<p>[[1,234]]:&#x200F;5</p>",
    "<p>[[1,234]] א</p>",
    "<p>[[1,234]] &#1488;</p>",
    "<p>Revenue ١ [[1,234]] total</p>",
    "<p>Revenue [[1,234]] total ١</p>",
    "<p title=~א~>Revenue [[1,234]] total</p>",
], ids=["rlm_ref", "rlm_ref_minus", "rlm_literal", "rlm_literal_minus", "alm_ref", "rlm_paren", "rlm_paren_td",
        "hebrew_left", "hebrew_minus", "hebrew_minus_paren", "arabic_minus", "rlm_right", "hebrew_right",
        "hebrew_ref_right", "arabic_indic_digit_left", "arabic_indic_digit_right", "hebrew_in_attribute"])
def test_r9_1_a_right_to_left_character_in_the_window_is_refused(body):
    _r9_refused(body)


def test_r9_1_a_named_reference_to_a_right_to_left_mark_is_refused():
    _r9_refused("<p>5&rlm;:[[1,234]]</p>")


def test_r9_1_a_right_to_left_character_far_before_the_window_is_refused():
    _r9_refused("<p>א</p><p>" + "A" * 2100 + "</p><p>Revenue [[1,234]] total</p>")


def test_r9_1_blanks_do_not_hide_a_right_to_left_mark_from_the_window():
    _r9_refused("<p>Net -&#x200F;:" + " " * 2100 + "[[1,234]] total</p>")


def test_r9_1_a_right_to_left_letter_fifty_thousand_bytes_before_is_refused():
    _r9_refused("<p>א</p><p>" + "A" * 50000 + "</p><p>Revenue [[1,234]] total</p>")


def test_r9_1_a_direction_override_followed_by_blanks_is_refused():
    _r9_refused("<p>Net -&#x202E;" + " " * 2100 + "[[1,234]] total</p>")


def test_r9_1_a_literal_isolate_fifty_thousand_bytes_before_is_refused():
    _r9_refused("<p>⁧</p><p>" + "A" * 50000 + "</p><p>Revenue [[1,234]] total</p>")


def test_r9_1_a_direction_override_on_the_right_before_the_scan_limit_is_refused():
    _r9_refused("<p>Revenue [[1,234]] total &#x202E;</p>")


def test_r9_1_a_direction_override_after_the_scan_limit_is_admitted():
    _r9_admitted("<p>Revenue [[1,234]] total</p><p>" + "A" * 2100 + "</p><p>&#x202E;⁧</p>")


def test_r9_1_a_right_to_left_letter_after_the_scan_limit_is_admitted():
    _r9_admitted("<p>Revenue [[1,234]] total</p><p>" + "A" * 2100 + "</p><p>א</p>")


def test_r9_1_a_right_to_left_reference_after_the_scan_limit_is_admitted():
    _r9_admitted("<p>Revenue [[1,234]] total</p><p>" + "A" * 2100 + "</p><p>&#x200F;&#1488;</p>")


@pytest.mark.parametrize("body", [
    '<h:script xmlns:h=~http://www.w3.org/1999/xhtml~>[[1,234]]</h:script>',
    '<p>Revenue</p><h:span xmlns:h=~http://www.w3.org/1999/xhtml~ hidden=~hidden~>[[1,234]]</h:span>',
    '<h:title xmlns:h=~http://www.w3.org/1999/xhtml~>[[1,234]]</h:title>',
    '<p xmlns:h=~http://www.w3.org/1999/xht&#109;l~>Revenue [[1,234]] total</p>',
    '<p XMLNS:h=~http://www.w3.org/1999/xhtml~>Revenue [[1,234]] total</p>',
], ids=["script", "span_hidden", "title", "reference", "upper_case"])
def test_r9_3b_the_xhtml_namespace_under_a_prefix_is_refused(body):
    _r9_refused(body)


@pytest.mark.parametrize("body,head", [
    ("<p>Revenue [[1,234]] total</p>", "<?xml version=~1.0~ encoding=~windows-1255~?><html><body>"),
    ("<p>Revenue [[1,234]] total</p>", "<?xml version=~1.0~ encoding=~ISO-8859-8~?><html><body>"),
    ("<head><meta charset=~shift_jis~/></head><p>Revenue [[1,234]] total</p>", _R9_HEAD),
    ("<head><meta http-equiv=~Content-Type~ content=~text/html; charset=windows-1255~/></head><p>Revenue [[1,234]] total</p>", _R9_HEAD),
    ("<head><META CHARSET=~Windows-1255~></head><p>Revenue [[1,234]] total</p>", _R9_HEAD),
    ("<p>Revenue [[1,234]] total</p>", _R9_HEAD),
    ("<p>Revenue [[1,234]] total</p>", _R9_HEAD),
], ids=["xml_windows_1255", "xml_iso_8859_8", "meta_shift_jis", "meta_http_equiv", "meta_upper_case", "esc_after",
        "esc_before"])
def test_r9_6_a_declared_encoding_other_than_utf8_or_ascii_or_an_esc_byte_is_refused(body, head):
    _r9_refused(body, head)


@pytest.mark.parametrize("body,head", [
    ("<p>Revenue [[1,234]] total</p>", "<?xml version=~1.0~ encoding=~UTF-8~?><html><body>"),
    ("<p>Revenue [[1,234]] total</p>", "<?xml version='1.0' encoding='ASCII'?><html><body>"),
    ("<p>Revenue [[1,234]] total</p>", "<?xml version=~1.0~ encoding=~us-ascii~?><html><body>"),
    ("<head><meta charset=~utf-8~/></head><p>Revenue [[1,234]] total</p>", _R9_HEAD),
    ("<head><meta http-equiv=~Content-Type~ content=~text/html; charset=UTF-8~/></head><p>Revenue [[1,234]] total</p>", _R9_HEAD),
    ("<head><meta name=~viewport~ content=~width=device-width~/></head><p>Revenue [[1,234]] total</p>", _R9_HEAD),
], ids=["xml_utf8_upper", "xml_ascii_single_quotes", "xml_us_ascii", "meta_utf8", "meta_http_equiv_utf8", "meta_other"])
def test_r9_6_utf8_and_ascii_declarations_are_admitted(body, head):
    _r9_admitted(body, head)


def test_r9_6_a_declaration_after_the_scan_limit_is_admitted():
    _r9_admitted("<p>Revenue [[1,234]] total</p><p>" + "A" * 2100 + "</p><meta charset=~shift_jis~/>")


def test_r9_1_plain_text_is_admitted():
    _r9_admitted("<p>Revenue [[1,234]] total</p>")


@pytest.mark.parametrize("body", [
    "<p>5<!-->x<!x-->[[1,234]]</p>",
    "<p>-<!-->x<!x-->[[1,234]]</p>",
    "<p>-<?p >q<!x?>[[1,234]]</p>",
    "<p>5<!--->x<!x-->[[1,234]]</p>",
    "<p>Revenue [[1,234]] total</p><?php echo 1; ?>",
    "<?php echo 1; ?><p>Revenue [[1,234]] total</p>",
    "<?xml version=~1.0~?><p>Revenue [[1,234]] total</p>",
    "<!DOCTYPE html><p>Revenue [[1,234]] total</p>",
    "<p>Revenue [[1,234]] total</p><!ENTITY x ~y~>",
], ids=["empty_comment", "empty_comment_minus", "pi", "dash_comment", "php_after", "php_before",
        "second_xml_declaration", "doctype_after_root", "entity_declaration"])
def test_r9_2_a_split_comment_or_instruction_form_is_refused(body):
    _r9_refused(body)


def test_r9_2_a_cdata_section_is_refused():
    # The marker helper cannot hold ]] before the span, so the raw bytes are cut by hand.
    raw = _r9_doc("<p>5<![CDATA[x]]>1,234</p>").replace("~", chr(34)).encode("utf-8")
    start = raw.rfind(b"1,234")
    span = {"start_byte": start, "end_byte": start + 5, "text_sha256": hashlib.sha256(raw[start:start + 5]).hexdigest()}
    with pytest.raises(n.DisclosureError) as caught:
        n._verify_figure_span("revenue", span, "1,234", "+", raw)
    assert caught.value.code == "FIGURE_SPAN_MISMATCH"


def test_r9_2_a_php_instruction_at_byte_zero_is_refused():
    _r6_refused("<?php echo 1; ?><html><body><p>Revenue [[1,234]] total</p></body></html>")


def test_r9_2_a_second_doctype_is_refused():
    _r6_refused("<!DOCTYPE html><!DOCTYPE html><html><body><p>Revenue [[1,234]] total</p></body></html>")


def test_r9_2_the_template_with_its_xml_declaration_is_admitted():
    _r9_admitted("<p>Revenue [[1,234]] total</p>")


def test_r9_2_an_ordinary_comment_before_the_figure_is_admitted():
    _r9_admitted("<!-- note --><p>Revenue [[1,234]] total</p>")


def test_r9_2_a_doctype_before_the_root_is_admitted():
    _r6_verify("<!DOCTYPE html><html><body><p>Revenue [[1,234]] total</p></body></html>")


def test_r9_2_an_empty_dash_comment_is_admitted():
    _r9_admitted("<p>Revenue<!----> [[1,234]] total</p>")


def test_r9_2_a_byte_order_mark_before_the_xml_declaration_is_admitted():
    _r6_verify("﻿" + _r9_doc("<p>Revenue [[1,234]] total</p>"))


@pytest.mark.parametrize("body", [
    "<p>Revenue <span xmlns=~http://www.w3.org/2000/svg~>[[1,234]]</span> total</p>",
    "<div xmlns=~http://www.w3.org/2000/svg~><p>Revenue [[1,234]] total</p></div>",
    "<div xmlns=~http://www.w3.org/2000/sv&#x67;~><p>Revenue [[1,234]] total</p></div>",
    "<div xmlns=~~><p>Revenue [[1,234]] total</p></div>",
    "<div xmlns=~urn:x~><p>Revenue [[1,234]] total</p></div>",
    "<div XMLNS=~urn:x~><p>Revenue [[1,234]] total</p></div>",
    "<p xmlns:s=~http://www.w3.org/2000/svg~>Revenue [[1,234]] total</p>",
    "<p xmlns:s=~http://www.w3.org/1998/Math/MathML~>Revenue [[1,234]] total</p>",
    "<p xmlns:s=~http://www.w3.org/2000/sv&#103;~>Revenue [[1,234]] total</p>",
    "<p XMLNS:m=~http://www.w3.org/1998/Math/MathML~>Revenue [[1,234]] total</p>",
], ids=["svg_on_span", "svg_on_div", "svg_with_reference", "empty_value", "urn_value", "upper_case_name",
        "svg_prefix", "mathml_prefix", "svg_prefix_reference", "mathml_prefix_upper_case"])
def test_r9_3_a_foreign_namespace_is_refused(body):
    _r9_refused(body)


def test_r9_3_a_foreign_prefix_with_an_element_of_that_prefix_is_refused():
    _r9_refused("<p xmlns:s=~http://www.w3.org/2000/svg~>Revenue <s:text>[[1,234]]</s:text></p>")


def test_r9_3_a_foreign_namespace_before_the_window_is_refused():
    _r9_refused("<div xmlns=~urn:x~></div><p>" + "A" * 2100 + "</p><p>Revenue [[1,234]] total</p>")


def test_r9_3_a_nested_xhtml_namespace_is_admitted():
    _r9_admitted("<div xmlns=~" + _R9_NS + "~><p>Revenue [[1,234]] total</p></div>")


def test_r9_3_another_prefixed_declaration_is_admitted():
    _r9_admitted("<p xmlns:s=~urn:other~>Revenue [[1,234]] total</p>")


def test_r9_3_inline_xbrl_declarations_are_admitted():
    head = ("<html xmlns=~" + _R9_NS + "~ xmlns:ix=~http://www.xbrl.org/2013/inlineXBRL~"
            " xmlns:xbrli=~http://www.xbrl.org/2003/instance~ xmlns:us-gaap=~http://fasb.org/us-gaap/2025~><body>")
    _r6_verify(head + "<p>Revenue <ix:nonFraction name=~us-gaap:Revenues~>[[1,234]]</ix:nonFraction> total</p>"
               + _R9_TAIL)


@pytest.mark.parametrize("body", [
    "<p>5&#138;[[1,234]]</p>",
    "<p>5&#x8A;[[1,234]]</p>",
    "<p>5&#x9F;[[1,234]]</p>",
    "<p>5&#128;[[1,234]]</p>",
    "<p>5&#X8a;[[1,234]]</p>",
    "<p>5&#0000138;[[1,234]]</p>",
    "<p>5&#138[[1,234]]</p>",
    "<p>[[1,234]]&#145;5</p>",
], ids=["decimal_138", "hex_8A", "hex_9F", "decimal_128", "upper_hex", "leading_zeros", "no_semicolon", "right_side"])
def test_r9_4_a_reference_to_a_c1_control_is_refused(body):
    _r9_refused(body)


def test_r9_4_a_reference_just_outside_the_range_is_admitted():
    _r9_admitted("<p>Revenue&#160;[[1,234]]&#xA0;total</p>")


def test_r9_4_an_em_dash_reference_is_handled_as_before():
    with pytest.raises(n.DisclosureError) as caught:
        _r6_verify(_r9_doc("<p>Revenue &#8212; [[1,234]] total</p>"))
    assert caught.value.code == "FIGURE_SIGN_UNSUPPORTED"


@pytest.mark.parametrize("body", [
    "<p>Revenue &#" + "9" * 6000 + "; [[1,234]] total</p>",
    "<p>Revenue &#x" + "F" * 6000 + "; [[1,234]] total</p>",
    "<p>Revenue [[1,234]] total</p>" + "<p>" + "A" * 2100 + "</p><body title=~&#" + "9" * 6000 + ";~>",
], ids=["decimal_6000", "hex_6000", "root_tag_after_the_window"])
def test_r9_4_a_reference_with_thousands_of_figures_is_a_disclosure_error_not_a_value_error(body):
    _r9_refused(body)


def _r9_replay_snapshot(case, edit):
    spec = copy.deepcopy(case.snapshot.spec)
    edit(spec["fact"])
    return SimpleNamespace(spec=spec, bindings=dict(case.snapshot.bindings))


_R9_BAD_TYPES = [(1.0, "float"), ("1", "str"), (None, "none"), (True, "bool")]


@pytest.mark.parametrize("field", ["start_byte", "end_byte"])
@pytest.mark.parametrize("bad", [b for b, _ in _R9_BAD_TYPES], ids=[i for _, i in _R9_BAD_TYPES])
def test_r9_5_a_stored_activity_span_offset_of_the_wrong_type_is_a_disclosure_error(tmp_path, field, bad):
    case = _segment_case(tmp_path)
    snapshot = _r9_replay_snapshot(case, lambda fact: fact["span"].__setitem__(field, bad))
    with pytest.raises(n.DisclosureError) as caught:
        segment.replay_segment_source(snapshot, case.pinned.authority)
    assert caught.value.code == "SOURCE_SPAN_MISMATCH"


@pytest.mark.parametrize("bad", [b for b, _ in _R9_BAD_TYPES], ids=[i for _, i in _R9_BAD_TYPES])
def test_r9_5_a_stored_figure_offset_of_the_wrong_type_is_a_disclosure_error(tmp_path, bad):
    case = _segment_case(tmp_path)
    snapshot = _r9_replay_snapshot(case, lambda fact: fact["figure_spans"]["revenue"].__setitem__("end_byte", bad))
    with pytest.raises(n.DisclosureError) as caught:
        segment.replay_segment_source(snapshot, case.pinned.authority)
    assert caught.value.code in ("SOURCE_SPAN_MISMATCH", "FIGURE_SPAN_MISMATCH")


def test_r9_5_a_stored_activity_span_that_is_not_a_mapping_is_a_disclosure_error(tmp_path):
    case = _segment_case(tmp_path)
    snapshot = _r9_replay_snapshot(case, lambda fact: fact.__setitem__("span", None))
    with pytest.raises(n.DisclosureError) as caught:
        segment.replay_segment_source(snapshot, case.pinned.authority)
    assert caught.value.code == "SOURCE_SPAN_MISMATCH"


# ---------------------------------------------------------------------------------------------
# Fix 9b (ruling 84): only DisclosureError for a malformed span or stored row; invalid UTF-8; comment forms.
# ---------------------------------------------------------------------------------------------
_R9B_VALUES = [("none", None), ("true", True), ("float", 1.5), ("str", "x"), ("list", []), ("dict", {}),
               ("negative", -1), ("huge", 2 ** 80), ("removed", "__REMOVED__")]
_R9B_PAGE = b"<html><body><p>Revenue 1,234 total</p></body></html>"
_R9B_START = _R9B_PAGE.index(b"1,234")
_R9B_SPAN = {"start_byte": _R9B_START, "end_byte": _R9B_START + 5,
             "text_sha256": hashlib.sha256(_R9B_PAGE[_R9B_START:_R9B_START + 5]).hexdigest()}
# Every argument and every span key _verify_figure_span reads (``name`` and ``whole_document`` are not
# read as data: ``name`` is only a label, ``whole_document`` only selects a branch by truthiness).
_R9B_FIGURE_KEYS = ["span", "span.start_byte", "span.end_byte", "span.text_sha256", "text", "sign", "raw"]


def _r9b_figure_call(path, value):
    args = {"span": dict(_R9B_SPAN), "text": "1,234", "sign": "+", "raw": _R9B_PAGE}
    head, _, key = path.partition(".")
    if key:
        if value == "__REMOVED__":
            del args[head][key]
        else:
            args[head][key] = value
    elif value == "__REMOVED__":
        args[head] = None
    else:
        args[head] = value
    n._verify_figure_span("revenue", args["span"], args["text"], args["sign"], args["raw"])


def test_r9b_the_valid_figure_input_is_admitted():
    _r9b_figure_call("text", "1,234")


@pytest.mark.parametrize("path", _R9B_FIGURE_KEYS)
@pytest.mark.parametrize("value", [v for _, v in _R9B_VALUES], ids=[i for i, _ in _R9B_VALUES])
def test_r9b_a_malformed_figure_span_or_argument_is_only_a_disclosure_error(path, value):
    with pytest.raises(n.DisclosureError):
        _r9b_figure_call(path, value)


def test_r9b_a_figure_span_with_an_extra_key_is_refused():
    with pytest.raises(n.DisclosureError) as caught:
        n._verify_figure_span("revenue", dict(_R9B_SPAN, extra=1), "1,234", "+", _R9B_PAGE)
    assert caught.value.code == "FIGURE_SPAN_MISMATCH"


def test_r9b_a_wrong_type_sign_has_the_sign_code_and_the_others_the_span_code():
    with pytest.raises(n.DisclosureError) as caught:
        n._verify_figure_span("revenue", dict(_R9B_SPAN), "1,234", None, _R9B_PAGE)
    assert caught.value.code == "FIGURE_SIGN_UNSUPPORTED"
    for span, text, raw in ((None, "1,234", _R9B_PAGE), (dict(_R9B_SPAN), 5, _R9B_PAGE),
                            (dict(_R9B_SPAN), "1,234", "text")):
        with pytest.raises(n.DisclosureError) as caught:
            n._verify_figure_span("revenue", span, text, "+", raw)
        assert caught.value.code == "FIGURE_SPAN_MISMATCH"


# Stored edition and fact keys read by read_source and replay_segment_source.
_R9B_EDITION_KEYS = ["schema", "disclosure_id", "source_sha256", "source_byte_length", "published_date",
                     "sec_source"] + ["sec_source." + k for k in (
                         "snapshot_id", "manifest_key", "document_id", "snapshot_at", "issuer_cik", "accession",
                         "accepted_at", "recorded_at", "archive_url", "retrieval_receipt_id", "retrieved_at")]
_R9B_FACT_KEYS = (["schema", "edition", "form_type", "span", "span.start_byte", "span.end_byte", "span.text_sha256",
                   "figure_spans"] + ["figure_spans." + name for name in n.SEGMENT_FIGURE_NAMES]
                  + [f"figure_spans.{name}.{key}" for name in n.SEGMENT_FIGURE_NAMES
                     for key in ("start_byte", "end_byte", "text_sha256")]
                  + [f"{name}{suffix}" for name in n.SEGMENT_FIGURE_NAMES
                     for suffix in ("", "_text", "_sign", "_scale")])
_R9B_NULLABLE = {"figure_spans." + name for name in n.SEGMENT_FIGURE_NAMES}
_R9B_REPLAY_KEYS = ([("edition", k) for k in _R9B_EDITION_KEYS] + [("fact", k) for k in _R9B_FACT_KEYS])


def _r9b_set(container, dotted, value):
    parts = dotted.split(".")
    for part in parts[:-1]:
        container = container[part]
    if value == "__REMOVED__":
        del container[parts[-1]]
    else:
        container[parts[-1]] = value


@pytest.mark.parametrize("value", [v for _, v in _R9B_VALUES], ids=[i for i, _ in _R9B_VALUES])
@pytest.mark.parametrize("where,key", _R9B_REPLAY_KEYS, ids=[f"{w}.{k}" for w, k in _R9B_REPLAY_KEYS])
def test_r9b_a_malformed_stored_row_is_only_a_disclosure_error_at_replay(tmp_path, where, key, value):
    case = _segment_case(tmp_path)
    spec = copy.deepcopy(case.snapshot.spec)
    _r9b_set(spec[where], key, value)
    snapshot = SimpleNamespace(spec=spec, bindings=dict(case.snapshot.bindings))
    if where == "fact" and key in _R9B_NULLABLE and value is None:
        # A figure span of None is the legal absent figure, not a malformed row.
        assert segment.replay_segment_source(snapshot, case.pinned.authority) is None
        return
    with pytest.raises(n.DisclosureError):
        segment.replay_segment_source(snapshot, case.pinned.authority)


@pytest.mark.parametrize("value", [v for _, v in _R9B_VALUES], ids=[i for i, _ in _R9B_VALUES])
@pytest.mark.parametrize("where", ["edition", "fact", "spec"])
def test_r9b_a_stored_container_of_any_type_is_only_a_disclosure_error_at_replay(tmp_path, where, value):
    case = _segment_case(tmp_path)
    spec = copy.deepcopy(case.snapshot.spec)
    if where == "spec":
        if value == "__REMOVED__":
            value = None
        snapshot = SimpleNamespace(spec=value, bindings=dict(case.snapshot.bindings))
    else:
        _r9b_set(spec, where, value)
        snapshot = SimpleNamespace(spec=spec, bindings=dict(case.snapshot.bindings))
    with pytest.raises(n.DisclosureError):
        segment.replay_segment_source(snapshot, case.pinned.authority)


def test_r9b_the_valid_stored_row_replays(tmp_path):
    case = _segment_case(tmp_path)
    assert segment.replay_segment_source(case.snapshot, case.pinned.authority) is None


@pytest.mark.parametrize("which,code", [
    ("span_sha_none", "SOURCE_SPAN_MISMATCH"),
    ("figures_list", "SOURCE_SPAN_MISMATCH"),
    ("figures_missing_name", "SOURCE_SPAN_MISMATCH"),
    ("figure_sha_int", "SOURCE_SPAN_MISMATCH"),
    ("length_bool", "SOURCE_BYTES_MISMATCH"),
    ("source_sha_int", "SOURCE_BYTES_MISMATCH"),
])
def test_r9b_stored_span_and_source_field_codes(tmp_path, which, code):
    edits = {
        "span_sha_none": lambda spec: spec["fact"]["span"].__setitem__("text_sha256", None),
        "figures_list": lambda spec: spec["fact"].__setitem__("figure_spans", []),
        "figures_missing_name": lambda spec: spec["fact"]["figure_spans"].pop("revenue"),
        "figure_sha_int": lambda spec: spec["fact"]["figure_spans"]["revenue"].__setitem__("text_sha256", 1),
        "length_bool": lambda spec: spec["edition"].__setitem__("source_byte_length", True),
        "source_sha_int": lambda spec: spec["edition"].__setitem__("source_sha256", 5),
    }
    case = _segment_case(tmp_path)
    spec = copy.deepcopy(case.snapshot.spec)
    edits[which](spec)
    with pytest.raises(n.DisclosureError) as caught:
        segment.replay_segment_source(SimpleNamespace(spec=spec, bindings=dict(case.snapshot.bindings)),
                                      case.pinned.authority)
    assert caught.value.code == code


def _r9b_bytes_verify(raw: bytes, marker=b"[[", close=b"]]"):
    i = raw.index(marker)
    j = raw.index(close)
    page = raw[:i] + raw[i + len(marker):j] + raw[j + len(close):]
    start, end = i, j - len(marker)
    span = {"start_byte": start, "end_byte": end, "text_sha256": hashlib.sha256(page[start:end]).hexdigest()}
    n._verify_figure_span("revenue", span, page[start:end].decode("ascii"), "+", page)


def _r9b_bytes_refused(raw: bytes):
    with pytest.raises(n.DisclosureError) as caught:
        _r9b_bytes_verify(raw)
    assert caught.value.code == "FIGURE_SPAN_MISMATCH"


_R9B_OPEN = _R9_HEAD.replace("~", '"').encode("utf-8")
_R9B_CLOSE = _R9_TAIL.encode("utf-8")


@pytest.mark.parametrize("before", [b"Revenue \xff\xfe ", b"\x80total ", b"Revenue \xc3 ", b"Revenue \xed\xa0\x80 ",
                                    b"Revenue \xc0\xaf "], ids=["ff_fe", "lone_continuation", "truncated_lead",
                                                                "surrogate", "overlong"])
def test_r9b_3_invalid_utf8_before_the_figure_is_refused(before):
    _r9b_bytes_refused(_R9B_OPEN + b"<p>" + before + b"[[1,234]] \x80total</p>" + _R9B_CLOSE)


def test_r9b_3_the_exact_spec_example_is_refused():
    _r9b_bytes_refused(_R9B_OPEN + b"<p>Revenue \xff\xfe [[1,234]] \x80total</p>" + _R9B_CLOSE)


def test_r9b_3_valid_two_and_three_byte_characters_before_the_figure_are_admitted():
    _r9b_bytes_verify(_R9B_OPEN + "<p>Café €</p><p>Revenue [[1,234]] total</p>".encode("utf-8") + _R9B_CLOSE)


def test_r9b_3_invalid_bytes_after_the_scan_limit_are_admitted():
    _r9b_bytes_verify(_R9B_OPEN + b"<p>Revenue [[1,234]] total</p>" + b"A" * 2100 + b"\xff\xfe\x80" + _R9B_CLOSE)


def test_r9b_3_a_character_cut_by_the_scan_limit_is_not_invalid():
    # The 2,000-byte right window ends inside the three-byte euro sign; the cut tail is not an error.
    filler = b"A" * 1996
    _r9b_bytes_verify(_R9B_OPEN + b"<p>Revenue [[1,234]]" + filler + "€".encode("utf-8") + b"</p>" + _R9B_CLOSE)


@pytest.mark.parametrize("body", [
    "<p>Revenue <!-- a --!> [[1,234]] <!-- --> total</p>",
    "<p>Revenue <!-- a --!> [[1,234]] total</p>",
    "<!-- a --!><p>Revenue [[1,234]] total</p>",
    "<p>Revenue --!> [[1,234]] total</p>",
    "<!-- a -- b --><p>Revenue [[1,234]] total</p>",
    "<p>Revenue <!-- a -- b --> [[1,234]] total</p>",
    "<!-- -- --><p>Revenue [[1,234]] total</p>",
], ids=["spec_example", "bang_close_only", "bang_close_before", "bang_close_in_text", "double_hyphen",
        "double_hyphen_inline", "double_hyphen_only"])
def test_r9b_4_a_comment_end_bang_or_a_double_hyphen_comment_body_is_refused(body):
    _r9_refused(body)


@pytest.mark.parametrize("body", [
    "<p>Revenue <!-- note --> [[1,234]] total</p>",
    "<p>Revenue <!----> [[1,234]] total</p>",
    "<!-- one --><!-- two --><p>Revenue [[1,234]] total</p>",
    "<p>Revenue <!-- a - b --> [[1,234]] total</p>",
], ids=["plain_comment", "empty_comment", "two_comments", "single_hyphen"])
def test_r9b_4_an_ordinary_comment_is_admitted(body):
    _r9_admitted(body)


def test_r9b_4_a_double_hyphen_after_the_scan_limit_is_admitted():
    _r9_admitted("<p>Revenue [[1,234]] total</p><p>" + "A" * 2100 + "</p><!-- a -- b --><!-- c --!>")


# ---------------------------------------------------------------------------------------------
# Fix 9c (ruling 86): an instant at the edge of the date range with an offset is a DisclosureError.
# ---------------------------------------------------------------------------------------------
_R9C_EDGES = ["0001-01-01T00:00:00+01:00", "9999-12-31T23:59:59-01:00"]
# (dotted path in the stored edition, extra edits applied first so the instant is actually read)
_R9C_INSTANT_FIELDS = [
    ("known_at", {}),
    ("published_at", {"publication_precision": "instant"}),
    ("sec_source.accepted_at", {}),
    ("sec_source.retrieved_at", {}),
    ("sec_source.recorded_at", {}),
    ("sec_source.snapshot_at", {}),
]


def _r9c_edition(case, path, extra, value):
    spec = copy.deepcopy(case.snapshot.spec)
    for key, val in extra.items():
        spec["edition"][key] = val
    _r9b_set(spec["edition"], path, value)
    return spec


@pytest.mark.parametrize("edge", _R9C_EDGES)
@pytest.mark.parametrize("path,extra", _R9C_INSTANT_FIELDS, ids=[p for p, _ in _R9C_INSTANT_FIELDS])
def test_r9c_an_edge_instant_is_a_disclosure_error_at_replay_and_in_validate_edition(tmp_path, path, extra, edge):
    case = _segment_case(tmp_path)
    spec = _r9c_edition(case, path, extra, edge)
    with pytest.raises(n.DisclosureError):
        n.validate_edition(spec["edition"])
    with pytest.raises(n.DisclosureError):
        segment.replay_segment_source(SimpleNamespace(spec=spec, bindings=dict(case.snapshot.bindings)),
                                      case.pinned.authority)


@pytest.mark.parametrize("edge", _R9C_EDGES)
def test_r9c_an_edge_instant_has_the_instant_invalid_code(edge):
    with pytest.raises(n.DisclosureError) as caught:
        n._instant(edge)
    assert caught.value.code == "INSTANT_INVALID"


def _r9c_paths(obj, prefix=""):
    out = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = prefix + ("." if prefix else "") + key
            out.append(path)
            out += _r9c_paths(value, path)
    return out


def test_r9c_every_key_path_of_the_real_stored_row_leaves_only_a_disclosure_error_or_a_clean_return(tmp_path):
    case = _segment_case(tmp_path)
    base = case.snapshot.spec
    walked = ([("edition", p) for p in _r9c_paths(base["edition"])]
              + [("fact", p) for p in _r9c_paths(base["fact"])])
    values = [v for _, v in _R9B_VALUES] + _R9C_EDGES
    failures, cases = [], 0
    for where, path in walked:
        for value in values:
            spec = copy.deepcopy(base)
            _r9b_set(spec[where], path, value)
            cases += 1
            try:
                segment.replay_segment_source(SimpleNamespace(spec=spec, bindings=dict(case.snapshot.bindings)),
                                              case.pinned.authority)
            except n.DisclosureError:
                pass
            except Exception as error:
                failures.append((where, path, repr(value)[:30], type(error).__name__, str(error)[:60]))
    print("\nr9c walk: paths", len(walked), "cases", cases, "crashes", len(failures))
    assert not failures, failures[:12]
