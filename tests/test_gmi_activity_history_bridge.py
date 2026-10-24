"""The curated activity proposal -> activity-history APPEND bridge (GMI M1 step 2).

The tmp_path cases exercise the bridge end to end on the C01 Micron proposal:
curation-receipt checking, graph-membership-use qualification (every USE_RULING_*
refusal), the honest HELD state with the fold's own verdict, the fixture-granted
APPEND the real fold accepts as current belief, the file-only flip, idempotency
and the CLI. Ratification and grants live ONLY on tmp_path here — the committed
ledger is read once, to pin the embedded constant to the real PROPOSED line, and
never written. A fixture grant is unusable without ``allow_fixture=True``, which
``scripts/bridge_activity_history.py`` never passes.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from engine.theme_graph import materialize, probation
from engine.theme_graph import activity_history_bridge as bridge
from scripts import bridge_activity_history as cli

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_RULING = "research/theme_graph/issuer_disclosures_20261011/C01_CHAIRMAN_SOURCE_PURPOSE_RULING.json"
C01_PROPOSAL_ID = "actprop:287edbf7e04b8aba873b7493"
C01_PROPOSAL_SHA256 = "5b08d12032d6371471b9ee43fc365bcb38601058d3e3484183a4a26615ee66a1"
CURATOR_SEAT = "seat:6f14c2da-02a9-467e-9f37-7c2ebaccfe09 (acting curator, Chairman delegation 2026-10-21)"
DECIDED_AT = "2026-10-21T07:00:00Z"
RULING_RECORDED_AT = "2026-10-21T20:00:00Z"
RECORDED_AT = "2026-10-21T23:00:00Z"

C01_LEDGER_LINE = '{"authority_caps":{"may_materialize":false,"may_publish":false,"may_ratify":false},"created":"2026-10-21T11:46:22Z","curation":null,"evidence":{"clocks":{"admitted":{"precision":null,"state":"NOT_APPLICABLE","value":null},"correction":{"precision":null,"state":"NOT_APPLICABLE","value":null},"effective":{"precision":null,"state":"UNDISCLOSED","value":null},"knowledge":{"precision":"instant","state":"KNOWN","value":"2026-10-11T17:09:10.298093+00:00"},"observation":{"precision":"instant","state":"KNOWN","value":"2026-10-09T01:38:55.651385+00:00"},"publication":{"precision":"date","state":"KNOWN","value":"2024-02-26"},"served_generation":{"precision":null,"state":"NOT_APPLICABLE","value":null}},"endpoints":{"direction":"SOURCE_TO_TARGET","source_node_id":"co:us:MU","target_node_id":"theme:hbm_packaging"},"issuer":{"identity_read_sha256":"7d9ecc326f359d2638a396524aa760948dcf489475e700b1fd8df87f7f420851","issuer_id":"ISS:US-XNAS-MU","join_method":"master_inception_exact","node_id":"co:us:MU","resolution_asof":"2026-10-21","resolution_state":"RESOLVED","security_id":"SEC:US-XNAS-MU"},"lifecycle":"planned","magnitudes":{"amount":{"state":"UNDISCLOSED","value":null},"economic_share":{"state":"UNDISCLOSED","value":null}},"role":"component_supplier","schema":"gmi.activity_membership_evidence/v1","scope":{"counterparty_issuer_id":"ISS:US-XNAS-NVDA","platform":"NVIDIA H200","product":"24GB 8H HBM3E","segment":{"state":"UNDISCLOSED","value":null}},"source_evidence":{"disclosure_id":"disclosure:357369cb386fb6d31924ce61176180f3b57f8daccb974b2688d12b095f181bdb","edition":{"byte_length":504119,"published_date":"2024-02-26","source_key":"manual:micron-ir:hbm3e-h200:2024-02-26","source_sha256":"a7efabf9cec581ba684688368118e3e13df6a3043aff56667927e24df97e8b2e"},"fact_id":"integration:a67d5c6168617d71c5b1eedb241fc8518d3a8473476fe2a0889b73a5e3ff718f","fact_revision":1,"owner":"engine.company_intelligence.issuer_disclosure_owner","owner_bindings":{"adoption":"f2938b91e6828de9462cef2b9d984fcdff1a95ae0bca2ee969490b90ee73e0a4","purpose":"5b3fc66029456f38d40358496ba308596751ef7ffae0d3711adb1ab5caa84117","spec":"39c0e86c4bcb649eac2534806a5a20d6c88c44d410d5db82038430d189d04ccc"},"review_revision":"cbad48fd2ba90088349fee9f2153f39fc14decd4bad096dcce66b99b3353eb5f","span":{"end_byte":371320,"start_byte":370936,"text_sha256":"f79bce81f656e826b3aa74380eb9a2b63bf74fc0e60376dc2b40c64600eb890a"}},"species":"planned_product_integration","target_definition":{"asserted_on":"2026-10-08","crosswalk_sha256":"cfaaecf3dc9942653d43af9736406362b081e991023c059c0dddd7873706ad1b","definition_sha256":"7b6bd278681b3ac55030fea6a3341e4bf9122b010c8fc947be17913cc128c1eb","rights_family":"mastermind_curated","theme_id":"theme:hbm_packaging","tier":"micro_theme"},"use_qualification":{"graph_membership_use":"NOT_GRANTED","purpose":{"permitted_audience":"company_intelligence_entitled","permitted_purpose":"private_company_intelligence_context","ruling_binding_sha256":"5b3fc66029456f38d40358496ba308596751ef7ffae0d3711adb1ab5caa84117"},"source_rights":{"family":null,"public_emission":"RIGHTS_FAMILY_UNRESOLVED","rights_class":null},"target_definition_rights":{"family":"mastermind_curated","public_emission":"GRANTED","rights_class":"direct_display_ok"}}},"proposal_id":"actprop:287edbf7e04b8aba873b7493","schema":"gmi.activity_membership_proposal/v1","status":"PROPOSED"}'


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


@pytest.fixture(scope="module")
def proposed():
    return json.loads(C01_LEDGER_LINE)


@pytest.fixture(scope="module")
def original_ruling():
    return json.loads((ROOT / ORIGINAL_RULING).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def original_ruling_sha():
    return hashlib.sha256((ROOT / ORIGINAL_RULING).read_bytes()).hexdigest()


def _receipt_dict(proposed_row, *, curator=CURATOR_SEAT, decision="RATIFIED",
                  reviewed_at=DECIDED_AT, reasons=None, **overrides):
    receipt = {
        "schema": "gmi.activity_curation_receipt/v1",
        "proposal_id": proposed_row["proposal_id"],
        "proposal_sha256": bridge.proposal_sha256(proposed_row),
        "curator": curator,
        "decision": decision,
        "reviewed_at": reviewed_at,
        "reasons": reasons if reasons is not None else [
            {"code": "CHAIRMAN_DELEGATED_CURATOR",
             "detail": "GMI COMPLETION seat acting curator, Chairman delegation 2026-10-21"}],
    }
    receipt.update(overrides)
    return receipt


def _ratified(tmp_path, proposed_row, *, receipt_bytes=None, decision="ACCEPT",
              decided_at=DECIDED_AT, curator=CURATOR_SEAT):
    """The seat's receipt at the convention path + the terminal row its bytes hash into."""
    bytes_ = receipt_bytes if receipt_bytes is not None else _canonical(
        _receipt_dict(proposed_row))
    receipts_dir = tmp_path / "curation_receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    (receipts_dir / (proposed_row["proposal_id"].replace(":", "_") + ".json")).write_bytes(
        bytes_)
    terminal = probation.curate_activity_proposal(
        proposed_row, curator=curator, decision=decision, decided_at=decided_at,
        receipt_bytes=bytes_)
    return receipts_dir, terminal


def _fixture_ruling(proposed_row, original, original_sha):
    """The FIXTURE graph-membership-use revision of the original C01 ruling."""
    evidence = proposed_row["evidence"]
    return {
        "schema": "company_intelligence.source_purpose_ruling/v1",
        "ruling_id": "FIXTURE-GMI-C01-GRAPH-MEMBERSHIP-USE",
        "revises_ruling_sha256": original_sha,
        "revises_ruling_path": ORIGINAL_RULING,
        "recorded_at": RULING_RECORDED_AT,
        "decision": "covered",
        "decision_owner": "Chairman Chris",
        "evidence_kind": "direct_chairman_source_rights_confirmation",
        "source": {
            "sha256": evidence["source_evidence"]["edition"]["source_sha256"],
            "byte_length": evidence["source_evidence"]["edition"]["byte_length"],
        },
        "permitted_use": copy.deepcopy(original["permitted_use"]),
        "graph_membership_use_grant": {
            "purpose": "graph_membership_use",
            "graph_membership_use": "GRANTED",
            "internal": True,
            "display": False,
            "redistribution": False,
            "subject_node_id": evidence["endpoints"]["source_node_id"],
            "target_node_id": evidence["endpoints"]["target_node_id"],
            "species": evidence["species"],
            "membership_scope": {
                "counterparty_issuer_id": evidence["scope"]["counterparty_issuer_id"],
                "platform": evidence["scope"]["platform"],
                "product": evidence["scope"]["product"],
            },
            "proposal_ids": [proposed_row["proposal_id"]],
        },
    }


def _write_ruling(tmp_path, proposed_row, original, original_sha, *,
                  name="GRAPH_MEMBERSHIP_USE_RULING_C01.json", **overrides) -> Path:
    ruling = _fixture_ruling(proposed_row, original, original_sha)
    ruling.update(overrides)
    path = tmp_path / name
    path.write_text(json.dumps(ruling, sort_keys=True), encoding="utf-8")
    return path


class Rig:
    """One tmp scene: proposal, terminal row, receipt file, fixture ruling."""

    def __init__(self, tmp_path, proposed_row, original, original_sha):
        self.tmp_path = tmp_path
        self.proposed = proposed_row
        self.receipts_dir, self.terminal = _ratified(tmp_path, proposed_row)
        self.ruling = _write_ruling(tmp_path, proposed_row, original, original_sha)
        self.events_path = tmp_path / "activity_history_events.jsonl"
        self.receipts_path = tmp_path / "activity_history_bridge_receipts.jsonl"

    def plan(self, *, ruling=True, allow_fixture=True, existing=None,
             recorded_at=RECORDED_AT, rows=None):
        return bridge.plan_bridge(
            rows if rows is not None else [self.proposed, self.terminal],
            receipts_dir=self.receipts_dir,
            ruling_paths=[str(self.ruling)] if ruling else [],
            recorded_at=recorded_at, existing_events=existing or [],
            allow_fixture=allow_fixture)

    def apply(self, plan, *, recorded_at=RECORDED_AT):
        return bridge.apply_plan(plan, events_path=self.events_path,
                                 receipts_path=self.receipts_path,
                                 recorded_at=recorded_at)


@pytest.fixture
def rig(tmp_path, proposed, original_ruling, original_ruling_sha):
    return Rig(tmp_path, proposed, original_ruling, original_ruling_sha)


# ---------------------------------------------------------------------------
# The embedded constant and the committed ledger
# ---------------------------------------------------------------------------

def test_embedded_c01_row_carries_the_documented_subject():
    row = json.loads(C01_LEDGER_LINE)
    assert C01_LEDGER_LINE == probation._activity_canonical(row)
    assert row["proposal_id"] == C01_PROPOSAL_ID
    assert row["status"] == "PROPOSED" and row["curation"] is None
    assert bridge.proposal_sha256(row) == C01_PROPOSAL_SHA256
    evidence = row["evidence"]
    assert evidence["endpoints"] == {"source_node_id": "co:us:MU",
                                     "target_node_id": "theme:hbm_packaging",
                                     "direction": "SOURCE_TO_TARGET"}
    assert evidence["scope"]["counterparty_issuer_id"] == "ISS:US-XNAS-NVDA"
    assert evidence["species"] == "planned_product_integration"
    assert evidence["role"] == "component_supplier" and evidence["lifecycle"] == "planned"
    assert (evidence["use_qualification"]["graph_membership_use"] == "NOT_GRANTED")


@pytest.mark.needs_full_checkout("data")
def test_embedded_constant_is_the_committed_ledger_line():
    lines = probation.ACTIVITY_PROPOSALS_PATH.read_text(encoding="utf-8").rstrip("\n").splitlines()
    # Line 1 is the embedded PROPOSED row; line 2 is its RATIFIED row (acting
    # curator, 2026-10-22, PR #10026) bound to the committed receipt by sha256.
    assert lines[0] == C01_LEDGER_LINE
    assert len(lines) == 2
    ratified = json.loads(lines[1])
    assert ratified["proposal_id"] == C01_PROPOSAL_ID and ratified["status"] == "RATIFIED"
    receipt = bridge.curation_receipt_path(bridge.DEFAULT_RECEIPTS_DIR, C01_PROPOSAL_ID)
    assert Path(receipt).exists()
    assert ratified["curation"]["receipt_sha256"] == hashlib.sha256(
        Path(receipt).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Plan outcomes: SKIPPED and the structural REFUSED codes
# ---------------------------------------------------------------------------

def test_awaiting_curation_skips_and_writes_nothing(tmp_path, proposed):
    [decision] = bridge.plan_bridge(
        [proposed], receipts_dir=tmp_path, ruling_paths=[], recorded_at=RECORDED_AT,
        existing_events=[])
    assert decision["outcome"] == "SKIPPED"
    assert decision["reason_code"] == "AWAITING_CURATION"
    assert decision["event"] is None and decision["graph_membership_use"] is None
    counts = bridge.apply_plan([decision], events_path=tmp_path / "events.jsonl",
                               receipts_path=tmp_path / "receipts.jsonl",
                               recorded_at=RECORDED_AT)
    assert counts == {"appended_events": 0, "receipt_rows": 0, "skipped": 1}
    assert not (tmp_path / "events.jsonl").exists()
    assert not (tmp_path / "receipts.jsonl").exists()


def test_rejected_terminal_skips(tmp_path, proposed):
    rejected = probation.curate_activity_proposal(
        proposed, curator="curator:gmi-desk", decision="REJECT",
        decided_at="2026-10-21T09:00:00Z", receipt_bytes=b"reject receipt")
    [decision] = bridge.plan_bridge(
        [proposed, rejected], receipts_dir=tmp_path, ruling_paths=[],
        recorded_at=RECORDED_AT, existing_events=[])
    assert decision["outcome"] == "SKIPPED"
    assert decision["reason_code"] == "PROPOSAL_REJECTED"


def test_ledger_proposal_missing_refused(tmp_path, proposed):
    terminal = probation.curate_activity_proposal(
        proposed, curator=CURATOR_SEAT, decision="ACCEPT", decided_at=DECIDED_AT,
        receipt_bytes=b"receipt")
    [decision] = bridge.plan_bridge(
        [terminal], receipts_dir=tmp_path, ruling_paths=[], recorded_at=RECORDED_AT,
        existing_events=[])
    assert decision["outcome"] == "REFUSED"
    assert decision["reason_code"] == "LEDGER_PROPOSAL_MISSING"


def test_curation_ambiguous_refused(tmp_path, proposed, original_ruling,
                                    original_ruling_sha):
    first = probation.curate_activity_proposal(
        proposed, curator=CURATOR_SEAT, decision="ACCEPT", decided_at=DECIDED_AT,
        receipt_bytes=b"first")
    second = probation.curate_activity_proposal(
        proposed, curator=CURATOR_SEAT, decision="ACCEPT",
        decided_at="2026-10-21T08:00:00Z", receipt_bytes=b"second")
    [decision] = bridge.plan_bridge(
        [proposed, first, second], receipts_dir=tmp_path, ruling_paths=[],
        recorded_at=RECORDED_AT, existing_events=[])
    assert decision["outcome"] == "REFUSED"
    assert decision["reason_code"] == "CURATION_AMBIGUOUS"


# ---------------------------------------------------------------------------
# Curation receipt codes
# ---------------------------------------------------------------------------

def _receipt_variant(tmp_path, proposed_row, variant):
    """(receipts_dir, terminal) for one RECEIPT_* variant; bytes are shared so the
    sha check passes and the named check is the one that fires."""
    if variant == "RECEIPT_MISSING":
        receipts_dir, terminal = _ratified(tmp_path, proposed_row)
        (receipts_dir / (proposed_row["proposal_id"].replace(":", "_") + ".json")).unlink()
        return receipts_dir, terminal
    if variant == "RECEIPT_SHA_MISMATCH":
        bytes_ = _canonical(_receipt_dict(proposed_row))
        receipts_dir, terminal = _ratified(tmp_path, proposed_row, receipt_bytes=bytes_)
        (receipts_dir / (proposed_row["proposal_id"].replace(":", "_") + ".json")
         ).write_bytes(b"different bytes entirely")
        return receipts_dir, terminal
    if variant == "RECEIPT_INVALID_JSON":
        bytes_ = b"not json at all"
        return _ratified(tmp_path, proposed_row, receipt_bytes=bytes_)
    if variant == "RECEIPT_INVALID_CONTRACT":
        receipt = _receipt_dict(proposed_row)
        del receipt["reasons"]
        return _ratified(tmp_path, proposed_row, receipt_bytes=_canonical(receipt))
    if variant == "RECEIPT_PROPOSAL_MISMATCH_ID":
        receipt = _receipt_dict(proposed_row, proposal_id="actprop:" + "0" * 24)
        return _ratified(tmp_path, proposed_row, receipt_bytes=_canonical(receipt))
    if variant == "RECEIPT_PROPOSAL_MISMATCH_SHA":
        receipt = _receipt_dict(proposed_row, proposal_sha256="0" * 64)
        return _ratified(tmp_path, proposed_row, receipt_bytes=_canonical(receipt))
    if variant == "RECEIPT_FIELD_MISMATCH_CURATOR":
        receipt = _receipt_dict(proposed_row, curator="someone else entirely")
        return _ratified(tmp_path, proposed_row, receipt_bytes=_canonical(receipt))
    if variant == "RECEIPT_FIELD_MISMATCH_REVIEWED_AT":
        receipt = _receipt_dict(proposed_row, reviewed_at="2026-10-21T08:00:00Z")
        return _ratified(tmp_path, proposed_row, receipt_bytes=_canonical(receipt))
    if variant == "RECEIPT_FIELD_MISMATCH_DECISION":
        receipt = _receipt_dict(proposed_row, decision="REJECTED")
        return _ratified(tmp_path, proposed_row, receipt_bytes=_canonical(receipt))
    raise AssertionError(variant)


@pytest.mark.parametrize("variant,expected", [
    ("RECEIPT_MISSING", "RECEIPT_MISSING"),
    ("RECEIPT_SHA_MISMATCH", "RECEIPT_SHA_MISMATCH"),
    ("RECEIPT_INVALID_JSON", "RECEIPT_INVALID"),
    ("RECEIPT_INVALID_CONTRACT", "RECEIPT_INVALID"),
    ("RECEIPT_PROPOSAL_MISMATCH_ID", "RECEIPT_PROPOSAL_MISMATCH"),
    ("RECEIPT_PROPOSAL_MISMATCH_SHA", "RECEIPT_PROPOSAL_MISMATCH"),
    ("RECEIPT_FIELD_MISMATCH_CURATOR", "RECEIPT_FIELD_MISMATCH"),
    ("RECEIPT_FIELD_MISMATCH_REVIEWED_AT", "RECEIPT_FIELD_MISMATCH"),
    ("RECEIPT_FIELD_MISMATCH_DECISION", "RECEIPT_FIELD_MISMATCH"),
])
def test_receipt_codes_refuse(tmp_path, proposed, original_ruling, original_ruling_sha,
                              variant, expected):
    receipts_dir, terminal = _receipt_variant(tmp_path, proposed, variant)
    [decision] = bridge.plan_bridge(
        [proposed, terminal], receipts_dir=receipts_dir,
        ruling_paths=[str(_write_ruling(tmp_path, proposed, original_ruling,
                                        original_ruling_sha, name="r.json"))],
        recorded_at=RECORDED_AT, existing_events=[])
    assert decision["outcome"] == "REFUSED"
    assert decision["reason_code"] == expected


# ---------------------------------------------------------------------------
# The honest NOT_GRANTED state and the use-ruling refusals
# ---------------------------------------------------------------------------

def test_not_granted_holds_with_the_folds_own_verdict(tmp_path, proposed):
    receipts_dir, terminal = _ratified(tmp_path, proposed)
    events_path = tmp_path / "events.jsonl"
    receipts_path = tmp_path / "receipts.jsonl"
    [decision] = bridge.plan_bridge(
        [proposed, terminal], receipts_dir=receipts_dir, ruling_paths=[],
        recorded_at=RECORDED_AT, existing_events=[])
    assert decision["outcome"] == "HELD"
    assert decision["reason_code"] == "GRAPH_MEMBERSHIP_USE_NOT_GRANTED"
    assert decision["graph_membership_use"] == "NOT_GRANTED"
    assert decision["fold_verdict"] == "GRAPH_MEMBERSHIP_USE_NOT_GRANTED"
    assert "USE_RULING_ABSENT" in [r["code"] for r in decision["ruling_refusals"]]
    counts = bridge.apply_plan([decision], events_path=events_path,
                               receipts_path=receipts_path, recorded_at=RECORDED_AT)
    assert counts == {"appended_events": 0, "receipt_rows": 1, "skipped": 0}
    assert not events_path.exists()
    [row] = bridge.read_bridge_receipts(receipts_path)
    assert row["outcome"] == "HELD" and row["event_id"] is None
    assert row["event_sha256"] is None
    assert row["graph_membership_use"] == "NOT_GRANTED"
    assert row["curation_receipt_sha256"] == terminal["curation"]["receipt_sha256"]
    # A second identical run is idempotent: nothing new is written.
    [again] = bridge.plan_bridge(
        [proposed, terminal], receipts_dir=receipts_dir, ruling_paths=[],
        recorded_at=RECORDED_AT, existing_events=bridge.read_events(events_path))
    assert again["outcome"] == "HELD"
    counts2 = bridge.apply_plan([again], events_path=events_path,
                                receipts_path=receipts_path, recorded_at=RECORDED_AT)
    assert counts2 == {"appended_events": 0, "receipt_rows": 0, "skipped": 1}
    assert len(bridge.read_bridge_receipts(receipts_path)) == 1


_RULING_MUTATIONS = {
    "USE_RULING_SCHEMA": lambda r: r.update(schema="wrong.ruling/v1"),
    "USE_RULING_REVISION_BINDING": lambda r: r.update(revises_ruling_sha256="0" * 64),
    "USE_RULING_REVISION_DRIFT": lambda r: r["permitted_use"].update(subject="SomeoneElse"),
    "USE_RULING_AUTHORITY": lambda r: r.update(decision_owner="Sol CEO"),
    "USE_RULING_SOURCE_MISMATCH": lambda r: r["source"].update(sha256="a" * 64),
    "USE_RULING_PERMITTED_USE": lambda r: r["graph_membership_use_grant"].update(
        internal=False),
    "USE_RULING_PERMITTED_USE_MISSING": lambda r: r.pop("graph_membership_use_grant"),
    "USE_RULING_GRANT_MISMATCH": lambda r: r["graph_membership_use_grant"].update(
        subject_node_id="co:us:INTC"),
    "USE_RULING_GRANT_MISMATCH_SCOPE": lambda r: r["graph_membership_use_grant"][
        "membership_scope"].update(product="NVIDIA B200"),
    "USE_RULING_GRANT_MISMATCH_PROPOSALS": lambda r: r["graph_membership_use_grant"].update(
        proposal_ids=["actprop:" + "0" * 24]),
    "USE_RULING_CLOCK": lambda r: r.update(recorded_at="2026-10-01T00:00:00Z"),
}


@pytest.mark.parametrize("code,mutate", sorted(_RULING_MUTATIONS.items()))
def test_use_ruling_refusal_codes(tmp_path, proposed, original_ruling,
                                  original_ruling_sha, code, mutate):
    receipts_dir, terminal = _ratified(tmp_path, proposed)
    ruling = _fixture_ruling(proposed, original_ruling, original_ruling_sha)
    mutate(ruling)
    path = tmp_path / f"ruling_{code}.json"
    path.write_text(json.dumps(ruling, sort_keys=True), encoding="utf-8")
    [decision] = bridge.plan_bridge(
        [proposed, terminal], receipts_dir=receipts_dir, ruling_paths=[str(path)],
        recorded_at=RECORDED_AT, existing_events=[], allow_fixture=True)
    assert decision["outcome"] == "HELD"
    assert decision["reason_code"] == "GRAPH_MEMBERSHIP_USE_NOT_GRANTED"
    assert decision["graph_membership_use"] == "NOT_GRANTED"
    assert decision["fold_verdict"] == "GRAPH_MEMBERSHIP_USE_NOT_GRANTED"
    # A mutation key may sharpen a code (…_SCOPE, …_MISSING); the code itself must fire.
    assert any(c == code or code.startswith(c + "_")
               for c in (r["code"] for r in decision["ruling_refusals"]))


def test_use_ruling_unreadable_refused(tmp_path, proposed):
    receipts_dir, terminal = _ratified(tmp_path, proposed)
    unreadable = tmp_path / "not_json.json"
    unreadable.write_bytes(b"<html>not a ruling</html>")
    [decision] = bridge.plan_bridge(
        [proposed, terminal], receipts_dir=receipts_dir,
        ruling_paths=[str(tmp_path / "missing.json"), str(unreadable)],
        recorded_at=RECORDED_AT, existing_events=[])
    codes = [r["code"] for r in decision["ruling_refusals"]]
    assert codes.count("USE_RULING_UNREADABLE") == 2
    assert decision["outcome"] == "HELD"


def test_fixture_grant_needs_allow_fixture(tmp_path, proposed, original_ruling,
                                           original_ruling_sha):
    receipts_dir, terminal = _ratified(tmp_path, proposed)
    ruling = _write_ruling(tmp_path, proposed, original_ruling, original_ruling_sha)
    [decision] = bridge.plan_bridge(
        [proposed, terminal], receipts_dir=receipts_dir, ruling_paths=[str(ruling)],
        recorded_at=RECORDED_AT, existing_events=[])
    assert decision["outcome"] == "HELD"
    assert decision["graph_membership_use"] == "NOT_GRANTED"
    assert "USE_RULING_FIXTURE" in [r["code"] for r in decision["ruling_refusals"]]
    assert decision["fold_verdict"] == "GRAPH_MEMBERSHIP_USE_NOT_GRANTED"


def test_two_qualifying_rulings_are_ambiguous(tmp_path, proposed, original_ruling,
                                              original_ruling_sha):
    receipts_dir, terminal = _ratified(tmp_path, proposed)
    one = _write_ruling(tmp_path, proposed, original_ruling, original_ruling_sha,
                        name="one.json")
    two = _write_ruling(tmp_path, proposed, original_ruling, original_ruling_sha,
                        name="two.json")
    [decision] = bridge.plan_bridge(
        [proposed, terminal], receipts_dir=receipts_dir, ruling_paths=[str(one), str(two)],
        recorded_at=RECORDED_AT, existing_events=[], allow_fixture=True)
    assert decision["outcome"] == "HELD"
    assert decision["graph_membership_use"] == "NOT_GRANTED"
    assert "USE_RULING_AMBIGUOUS" in [r["code"] for r in decision["ruling_refusals"]]


# ---------------------------------------------------------------------------
# The fixture-granted APPEND and idempotency
# ---------------------------------------------------------------------------

def test_fixture_grant_appends_and_the_fold_accepts_current_belief(rig):
    [decision] = rig.plan()
    assert decision["outcome"] == "APPEND"
    assert decision["reason_code"] == "GRAPH_MEMBERSHIP_USE_GRANTED"
    assert decision["graph_membership_use"] == "GRANTED"
    assert decision["use_ruling_path"] == str(rig.ruling)
    event = decision["event"]
    materialize.validate_activity_history_event(event)
    assert event["use_qualification"] == {"graph_membership_use": "GRANTED"}
    fold = materialize.apply_activity_membership_events(
        [event], knowledge_cutoff=event["clocks"]["knowledge_at"])
    assert [b["membership_id"] for b in fold["current"]] == [event["membership_id"]]
    assert fold["refused"] == [] and fold["history"] == []
    counts = rig.apply([decision])
    assert counts == {"appended_events": 1, "receipt_rows": 1, "skipped": 0}
    [stored] = bridge.read_events(rig.events_path)
    assert stored["event_sha256"] == event["event_sha256"]
    [row] = bridge.read_bridge_receipts(rig.receipts_path)
    assert row["outcome"] == "APPEND" and row["event_id"] == event["event_id"]
    # A rerun against the written events file bridges nothing new.
    [rerun] = rig.plan(existing=bridge.read_events(rig.events_path))
    assert rerun["outcome"] == "SKIPPED"
    assert rerun["reason_code"] == "ALREADY_BRIDGED"
    counts2 = rig.apply([rerun])
    assert counts2 == {"appended_events": 0, "receipt_rows": 0, "skipped": 1}
    assert len(bridge.read_events(rig.events_path)) == 1
    assert len(bridge.read_bridge_receipts(rig.receipts_path)) == 1


def test_tampered_existing_event_for_the_same_key_conflicts(rig):
    [first] = rig.plan()
    rig.apply([first])
    [stored] = bridge.read_events(rig.events_path)
    tampered = copy.deepcopy(stored)
    tampered["role"] = "platform_owner"  # same key, different content -> different sha
    tampered["event_sha256"] = materialize.activity_history_event_digest(tampered)
    tampered["event_id"] = "actevt:" + tampered["event_sha256"][:24]
    materialize.validate_activity_history_event(tampered)
    [decision] = rig.plan(existing=[tampered])
    assert decision["outcome"] == "REFUSED"
    assert decision["reason_code"] == "EVENT_KEY_CONFLICT"


def test_flip_from_held_to_append_needs_only_files(tmp_path, proposed, original_ruling,
                                                   original_ruling_sha):
    receipts_dir, terminal = _ratified(tmp_path, proposed)
    events_path = tmp_path / "events.jsonl"
    receipts_path = tmp_path / "receipts.jsonl"
    plan_args = dict(ledger_rows=[proposed, terminal], receipts_dir=receipts_dir,
                     recorded_at=RECORDED_AT, existing_events=[], allow_fixture=True)
    [held] = bridge.plan_bridge(ruling_paths=[], **plan_args)
    assert held["outcome"] == "HELD"
    assert bridge.apply_plan([held], events_path=events_path,
                             receipts_path=receipts_path,
                             recorded_at=RECORDED_AT) == {
        "appended_events": 0, "receipt_rows": 1, "skipped": 0}
    # Only files change: the ruling revision arrives, the receipt was already there.
    ruling = _write_ruling(tmp_path, proposed, original_ruling, original_ruling_sha)
    plan_args["existing_events"] = bridge.read_events(events_path)
    [appended] = bridge.plan_bridge(ruling_paths=[str(ruling)], **plan_args)
    assert appended["outcome"] == "APPEND"
    counts = bridge.apply_plan([appended], events_path=events_path,
                               receipts_path=receipts_path, recorded_at=RECORDED_AT)
    assert counts == {"appended_events": 1, "receipt_rows": 1, "skipped": 0}
    [row_held, row_append] = bridge.read_bridge_receipts(receipts_path)
    assert (row_held["outcome"], row_held["graph_membership_use"]) == ("HELD", "NOT_GRANTED")
    assert (row_append["outcome"], row_append["graph_membership_use"]) == ("APPEND", "GRANTED")
    [stored] = bridge.read_events(events_path)
    assert stored["use_qualification"] == {"graph_membership_use": "GRANTED"}
    assert stored["curation"]["receipt_sha256"] == terminal["curation"]["receipt_sha256"]


def test_granted_but_fold_refuses_duplicate_append(rig, proposed):
    [granted] = rig.plan()
    # A valid, already-bridged GRANTED APPEND for the SAME membership from another
    # proposal, known EARLIER so the fold admits it first: this event must then be
    # refused as DUPLICATE_APPEND.
    sibling = copy.deepcopy(granted["event"])
    sibling["evidence_lineage"]["proposal_id"] = "actprop:" + "f" * 24
    sibling["clocks"]["knowledge_at"] = "2026-10-21T19:00:00Z"
    sibling["event_sha256"] = materialize.activity_history_event_digest(sibling)
    sibling["event_id"] = "actevt:" + sibling["event_sha256"][:24]
    materialize.validate_activity_history_event(sibling)
    [decision] = rig.plan(existing=[sibling])
    assert decision["outcome"] == "REFUSED"
    assert decision["reason_code"] == "FOLD_REFUSED"
    assert decision["fold_verdict"] == "DUPLICATE_APPEND"


def test_unexpected_fold_verdict_refused(rig, monkeypatch):
    def fake_fold(events, *, knowledge_cutoff):
        fold = materialize.apply_activity_membership_events(
            events, knowledge_cutoff=knowledge_cutoff)
        for row in fold["refused"]:
            row["reason"] = "SOMETHING_ELSE"
        return fold

    monkeypatch.setattr(bridge, "_fold", fake_fold)
    [decision] = rig.plan(ruling=False, allow_fixture=False)
    assert decision["outcome"] == "REFUSED"
    assert decision["reason_code"] == "FOLD_VERDICT_UNEXPECTED"
    assert decision["fold_verdict"] == "SOMETHING_ELSE"


# ---------------------------------------------------------------------------
# Clocks and event validation
# ---------------------------------------------------------------------------

def test_effective_at_mapping():
    assert bridge.effective_at_from_evidence(
        {"state": "KNOWN", "precision": "date", "value": "2024-02-26"}
    ) == {"value": "2024-02-26", "state": "KNOWN"}
    assert bridge.effective_at_from_evidence(
        {"state": "KNOWN", "precision": "instant",
         "value": "2026-10-11T17:09:10.298093+00:00"}
    ) == {"value": "2026-10-11", "state": "KNOWN"}
    # A non-UTC instant maps to its UTC calendar date.
    assert bridge.effective_at_from_evidence(
        {"state": "KNOWN", "precision": "instant", "value": "2026-10-11T23:30:00-05:00"}
    ) == {"value": "2026-10-12", "state": "KNOWN"}
    assert bridge.effective_at_from_evidence(
        {"state": "UNDISCLOSED", "precision": None, "value": None}
    ) == {"value": None, "state": "UNDISCLOSED"}
    assert bridge.effective_at_from_evidence(
        {"state": "NOT_APPLICABLE", "precision": None, "value": None}
    ) == {"value": None, "state": "NOT_APPLICABLE"}
    for bad in ({"state": "STALE", "precision": "date", "value": "2024-02-26"},
                {"state": "KNOWN", "precision": "unknown", "value": "2024-02-26"}):
        with pytest.raises(bridge.BridgeRefusal) as caught:
            bridge.effective_at_from_evidence(bad)
        assert caught.value.code == "EFFECTIVE_CLOCK_UNMAPPABLE"


def test_recorded_before_knowledge_refused(rig):
    with pytest.raises(bridge.BridgeRefusal) as caught:
        bridge.build_append_event(rig.proposed, rig.terminal,
                                  bridge.qualify_graph_membership_use(
                                      rig.proposed, [str(rig.ruling)],
                                      allow_fixture=True),
                                  recorded_at="2026-10-21T12:00:00Z")
    assert caught.value.code == "RECORDED_BEFORE_KNOWLEDGE"
    [decision] = rig.plan(recorded_at="2026-10-21T12:00:00Z")
    assert decision["outcome"] == "REFUSED"
    assert decision["reason_code"] == "RECORDED_BEFORE_KNOWLEDGE"


def test_broken_scope_is_event_invalid(proposed, rig):
    broken = copy.deepcopy(proposed)
    broken["evidence"]["scope"]["segment"]["extra"] = "smuggled"
    use = {"graph_membership_use": "GRANTED", "ruling_recorded_at": RULING_RECORDED_AT}
    with pytest.raises(bridge.BridgeRefusal) as caught:
        bridge.build_append_event(broken, rig.terminal, use, recorded_at=RECORDED_AT)
    assert caught.value.code == "EVENT_INVALID"


def test_bridge_receipt_row_is_closed_and_validated(rig):
    [held] = rig.plan(ruling=False, allow_fixture=False)
    row = bridge._bridge_receipt_row(held, recorded_at=RECORDED_AT)
    assert bridge._bridge_receipt_row_problems(row) == []
    assert row["event_id"] is None and row["event_sha256"] is None
    assert set(row) == {
        "schema", "proposal_id", "proposal_sha256", "outcome", "reason_code",
        "graph_membership_use", "event_id", "event_sha256",
        "curation_receipt_sha256", "use_ruling_path", "use_ruling_sha256",
        "ruling_refusals", "recorded_at"}
    assert bridge._bridge_receipt_row_problems(dict(row, smuggled=True))
    assert bridge._bridge_receipt_row_problems(dict(row, recorded_at="not zoned"))
    assert bridge._bridge_receipt_row_problems(dict(row, outcome="MAYBE"))


# ---------------------------------------------------------------------------
# The CLI
# ---------------------------------------------------------------------------

def _write_ledger(tmp_path, rows) -> Path:
    path = tmp_path / "activity_proposals.jsonl"
    path.write_text(
        "".join(probation._activity_canonical(row) + "\n" for row in rows),
        encoding="utf-8")
    return path


def test_cli_dry_run_output(tmp_path, proposed, capsys):
    ledger = _write_ledger(tmp_path, [proposed])
    rc = cli.main(["--recorded-at", RECORDED_AT, "--ledger", str(ledger),
                   "--events-out", str(tmp_path / "events.jsonl"),
                   "--bridge-receipts-out", str(tmp_path / "receipts.jsonl"),
                   "--dry-run"])
    assert rc == 0
    printed = json.loads(capsys.readouterr().out.strip())
    assert [d["outcome"] for d in printed["decisions"]] == ["SKIPPED"]
    assert printed["decisions"][0]["reason_code"] == "AWAITING_CURATION"
    assert printed["counts"] == {"appended_events": 0, "receipt_rows": 0, "skipped": 1}
    assert not (tmp_path / "events.jsonl").exists()
    assert not (tmp_path / "receipts.jsonl").exists()


def test_cli_refused_outcome_prints_plan_exits_3_and_writes_nothing(
        tmp_path, proposed, original_ruling, original_ruling_sha, capsys):
    bytes_ = _canonical(_receipt_dict(proposed))
    terminal = probation.curate_activity_proposal(
        proposed, curator=CURATOR_SEAT, decision="ACCEPT", decided_at=DECIDED_AT,
        receipt_bytes=bytes_)
    ledger = _write_ledger(tmp_path, [proposed, terminal])
    # An EMPTY receipts dir under tmp_path: the fixture shares its proposal_id with
    # the real C01 row, so the repo default dir may hold the seat's real receipt and
    # this refusal must never depend on what the repository currently contains.
    empty_receipts = tmp_path / "no_receipts"
    empty_receipts.mkdir()
    rc = cli.main(["--recorded-at", RECORDED_AT, "--ledger", str(ledger),
                   "--receipts-dir", str(empty_receipts),
                   "--use-ruling",
                   str(_write_ruling(tmp_path, proposed, original_ruling,
                                     original_ruling_sha)),
                   "--events-out", str(tmp_path / "events.jsonl"),
                   "--bridge-receipts-out", str(tmp_path / "receipts.jsonl")])
    assert rc == 3
    printed = json.loads(capsys.readouterr().out.strip())
    assert [d["reason_code"] for d in printed["decisions"]] == ["RECEIPT_MISSING"]
    assert not (tmp_path / "events.jsonl").exists()
    assert not (tmp_path / "receipts.jsonl").exists()


def test_cli_flip_end_to_end_at_the_default_glob(tmp_path, proposed, monkeypatch,
                                                 original_ruling, original_ruling_sha,
                                                 capsys):
    receipts_dir, terminal = _ratified(tmp_path, proposed)
    ledger = _write_ledger(tmp_path, [proposed, terminal])
    # A REAL-shaped ruling revision (a fixture id could never move the CLI) arrives
    # at the DEFAULT glob under a patched root, so the CLI's own discovery — not a
    # --use-ruling flag — is what finds it. Only files change; no code, no flags.
    revision = _fixture_ruling(proposed, original_ruling, original_ruling_sha)
    revision["ruling_id"] = "GMI-C01-GRAPH-MEMBERSHIP-USE-20261021"
    glob_root = tmp_path / "glob_root"
    ruling_dir = glob_root / "research/theme_graph/issuer_disclosures_20261011"
    ruling_dir.mkdir(parents=True)
    (ruling_dir / "C01_GRAPH_MEMBERSHIP_USE_RULING.json").write_text(
        json.dumps(revision, sort_keys=True), encoding="utf-8")
    monkeypatch.setattr(cli, "ROOT", glob_root)
    rc = cli.main(["--recorded-at", RECORDED_AT, "--ledger", str(ledger),
                   "--receipts-dir", str(receipts_dir),
                   "--events-out", str(tmp_path / "events.jsonl"),
                   "--bridge-receipts-out", str(tmp_path / "receipts.jsonl")])
    assert rc == 0
    printed = json.loads(capsys.readouterr().out.strip())
    assert [d["outcome"] for d in printed["decisions"]] == ["APPEND"]
    assert printed["counts"] == {"appended_events": 1, "receipt_rows": 1, "skipped": 0}
    [stored] = bridge.read_events(tmp_path / "events.jsonl")
    assert stored["use_qualification"] == {"graph_membership_use": "GRANTED"}


def test_cli_top_level_refusal_exits_2_via_subprocess(tmp_path):
    malformed = tmp_path / "activity_proposals.jsonl"
    malformed.write_text("not json\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/bridge_activity_history.py"),
         "--recorded-at", RECORDED_AT, "--ledger", str(malformed),
         "--events-out", str(tmp_path / "events.jsonl"),
         "--bridge-receipts-out", str(tmp_path / "receipts.jsonl")],
        capture_output=True, text=True)
    assert proc.returncode == 2
    assert proc.stderr.startswith("REFUSED: ")
    assert not (tmp_path / "events.jsonl").exists()


def test_cli_never_opens_the_fixture_door():
    source = (ROOT / "scripts/bridge_activity_history.py").read_text(encoding="utf-8")
    assert "allow_fixture=True" not in source


def test_default_ruling_glob_discovers_one_directory_level(tmp_path):
    """The default glob reaches research/theme_graph/<dir>/<file> only — the shape a
    real Chairman revision would land at, never deeper, never a bare research file."""
    hit_dir = tmp_path / "research/theme_graph/issuer_disclosures_20261011"
    hit_dir.mkdir(parents=True)
    (hit_dir / "C01_GRAPH_MEMBERSHIP_USE_RULING.json").write_text("{}", encoding="utf-8")
    deep = tmp_path / "research/theme_graph/a/b/C01_GRAPH_MEMBERSHIP_USE_RULING.json"
    deep.parent.mkdir(parents=True)
    deep.write_text("{}", encoding="utf-8")
    shallow = tmp_path / "research/theme_graph/C01_GRAPH_MEMBERSHIP_USE_RULING.json"
    shallow.write_text("{}", encoding="utf-8")
    other = tmp_path / "research/theme_graph/issuer_disclosures_20261011/OTHER_FILE.json"
    other.write_text("{}", encoding="utf-8")
    found = sorted(p.name for p in tmp_path.glob(bridge.DEFAULT_USE_RULING_GLOB))
    assert found == ["C01_GRAPH_MEMBERSHIP_USE_RULING.json"]


def test_repo_hosts_no_fixture_use_ruling():
    """Fixture grants never live in the repo; only tmp_path tests may use one."""
    proc = subprocess.run(
        ["git", "ls-files", "-z", "--",
         "research/theme_graph/*/*GRAPH_MEMBERSHIP_USE_RULING*.json"],
        cwd=ROOT, capture_output=True)
    if proc.returncode == 0:
        paths = [p for p in proc.stdout.decode("utf-8").split("\0") if p]
    else:  # no git here: the checked-out tree is the next-best committed census
        paths = sorted(str(p.relative_to(ROOT)) for p in
                       (ROOT / "research/theme_graph").glob(
                           "*/*GRAPH_MEMBERSHIP_USE_RULING*.json"))
    for rel in paths:
        ruling = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        assert not str(ruling.get("ruling_id", "")).startswith("FIXTURE"), rel


# ---------------------------------------------------------------------------
# The curation receipt contract itself
# ---------------------------------------------------------------------------

def test_curation_receipt_contract_shape(proposed):
    validator = bridge._curation_receipt_validator()
    good = _receipt_dict(proposed)
    assert not list(validator.iter_errors(good))
    for key in ("schema", "proposal_id", "proposal_sha256", "curator", "decision",
                "reviewed_at", "reasons"):
        assert list(validator.iter_errors(
            {k: v for k, v in good.items() if k != key})), key
    assert list(validator.iter_errors(dict(good, smuggled=True)))
    assert list(validator.iter_errors(dict(good, decision="MAYBE")))
    assert list(validator.iter_errors(dict(good, reviewed_at="2026-10-21T07:00:00")))
    assert list(validator.iter_errors(dict(good, proposal_id="actprop:xyz")))
    assert list(validator.iter_errors(dict(good, reasons=[])))
    assert list(validator.iter_errors(
        dict(good, reasons=[{"code": "lower_case", "detail": "x"}])))
    assert list(validator.iter_errors(
        dict(good, reasons=[{"code": "CODE_ONLY"}])))
