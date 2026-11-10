"""The activity proposal ledger — writer, curation and CLI contract (PIPE-PROPOSE).

The tmp_path cases exercise the appended probation ledger writer end to end on the
C01 Micron evidence fixture: append/read round trip and idempotence, the ledger
key, curation without a PROPOSED row, evidence drift, the single-terminal cap,
the ratification reader, the knowledge clock, the legacy-ledger refusal and the
CLI's write and refusal paths. The committed-tree case reads the real ledger and
must keep seeing exactly the native C01 PROPOSED row. Curator ratification is
exercised ONLY on tmp_path ledgers here — never on the committed ledger.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from engine.theme_graph import probation
from engine.theme_graph.membership_evidence import build_activity_membership_evidence
from scripts import propose_activity_membership as cli

ROOT = Path(__file__).resolve().parents[1]
CODE_VERSION = "0" * 40
CREATED = "2026-10-21T05:00:00Z"
AFTER_ALL_KNOWLEDGE = "2026-10-19T00:00:00Z"
MU_NODE = "co:us:MU"
TARGET = "theme:hbm_packaging"
C01_PROPOSAL_ID = "actprop:287edbf7e04b8aba873b7493"
CURATOR = "curator:gmi-desk"


def _identity_row(node_id, symbol, issuer_id, *, state="RESOLVED"):
    """The identity owner's row shape (data/theme_graph/identity_resolution.parquet)."""
    listing = issuer_id.removeprefix("ISS:") if issuer_id else None
    return {
        "schema": "gmi.identity_resolution/v1",
        "node_id": node_id,
        "graph_kind": "company",
        "market_scope": "us",
        "graph_identity_epoch": 1,
        "source_native_symbol": symbol,
        "resolution_asof": "2026-10-18",
        "resolution_state": state,
        "issuer_id": issuer_id,
        "security_id": ("SEC:" + listing) if (listing and state == "RESOLVED") else None,
        "listing_key": listing if state == "RESOLVED" else None,
        "join_method": "master_inception_exact" if state == "RESOLVED" else None,
        "refusal_reason": None if state == "RESOLVED" else "multiple_candidates",
        "computed_at": "2026-10-18T11:03:21Z",
        "engine_version": "theme_graph.v1",
    }


MU_ROW = _identity_row(MU_NODE, "MU", "ISS:US-XNAS-MU")


def _mu_reader(node_id):
    assert node_id == MU_NODE
    return dict(MU_ROW)


def _curate(proposal, *, decision="ACCEPT", decided_at="2026-10-21T07:00:00Z",
            receipt=b"curation receipt"):
    return probation.curate_activity_proposal(
        proposal, curator=CURATOR, decision=decision, decided_at=decided_at,
        receipt_bytes=receipt)


@pytest.fixture(scope="module")
def evidence():
    return build_activity_membership_evidence(
        issuer_node_id=MU_NODE, target_theme_id=TARGET, role="component_supplier",
        knowledge_cutoff=AFTER_ALL_KNOWLEDGE, code_version=CODE_VERSION,
        identity_reader=_mu_reader)


@pytest.fixture
def proposal(evidence):
    return probation.make_activity_membership_proposal(
        copy.deepcopy(evidence), created=CREATED)


def test_propose_append_read_roundtrip_and_idempotent(tmp_path, proposal):
    ledger = tmp_path / "activity_proposals.jsonl"
    first = probation.append_activity_proposals([proposal], ledger)
    assert first == {"appended": 1, "unchanged": 0, "path": str(ledger)}
    assert probation.read_activity_proposals(ledger) == [proposal]
    second = probation.append_activity_proposals([copy.deepcopy(proposal)], ledger)
    assert second["appended"] == 0 and second["unchanged"] == 1
    assert len(probation.read_activity_proposals(ledger)) == 1


def test_key_conflict_refused_and_file_unchanged(tmp_path, evidence, proposal):
    ledger = tmp_path / "activity_proposals.jsonl"
    probation.append_activity_proposals([proposal], ledger)
    before = ledger.read_bytes()
    drifted_evidence = copy.deepcopy(evidence)
    drifted_evidence["scope"]["product"] = drifted_evidence["scope"]["product"] + " (annotated)"
    drifted = probation.make_activity_membership_proposal(drifted_evidence, created=CREATED)
    assert drifted["proposal_id"] == proposal["proposal_id"]
    assert not probation._activity_repropose_is_same(proposal, drifted)
    with pytest.raises(probation.ActivityProposalRefusal) as caught:
        probation.append_activity_proposals([drifted], ledger)
    assert caught.value.code == "LEDGER_KEY_CONFLICT"
    assert ledger.read_bytes() == before


def test_repropose_with_new_created_is_unchanged(tmp_path, proposal):
    """A re-run of the same subject differs only in ``created``: the same row."""
    ledger = tmp_path / "activity_proposals.jsonl"
    probation.append_activity_proposals([proposal], ledger)
    before = ledger.read_bytes()
    rerun = copy.deepcopy(proposal)
    rerun["created"] = "2026-10-21T23:59:59Z"
    assert probation._activity_repropose_is_same(proposal, rerun)
    result = probation.append_activity_proposals([rerun], ledger)
    assert result["appended"] == 0 and result["unchanged"] == 1
    assert ledger.read_bytes() == before


def test_curation_without_proposal_refused(tmp_path, proposal):
    ledger = tmp_path / "activity_proposals.jsonl"
    curated = _curate(proposal)
    with pytest.raises(probation.ActivityProposalRefusal) as caught:
        probation.append_activity_proposals([curated], ledger)
    assert caught.value.code == "CURATION_WITHOUT_PROPOSAL"
    assert not ledger.exists()


def test_curation_evidence_drift_refused(tmp_path, evidence, proposal):
    ledger = tmp_path / "activity_proposals.jsonl"
    probation.append_activity_proposals([proposal], ledger)
    before = ledger.read_bytes()
    drifted_evidence = copy.deepcopy(evidence)
    drifted_evidence["scope"]["product"] = drifted_evidence["scope"]["product"] + " (annotated)"
    sibling = probation.make_activity_membership_proposal(drifted_evidence, created=CREATED)
    assert sibling["proposal_id"] == proposal["proposal_id"]
    curated = _curate(sibling)
    with pytest.raises(probation.ActivityProposalRefusal) as caught:
        probation.append_activity_proposals([curated], ledger)
    assert caught.value.code == "CURATION_EVIDENCE_DRIFT"
    assert ledger.read_bytes() == before


def test_second_terminal_row_refused(tmp_path, proposal):
    ledger = tmp_path / "activity_proposals.jsonl"
    result = probation.append_activity_proposals(
        [proposal, _curate(proposal)], ledger)
    assert result["appended"] == 2
    before = ledger.read_bytes()
    rejected = _curate(proposal, decision="REJECT", decided_at="2026-10-21T08:00:00Z",
                       receipt=b"second receipt")
    with pytest.raises(probation.ActivityProposalRefusal) as caught:
        probation.append_activity_proposals([rejected], ledger)
    assert caught.value.code == "TERMINAL_CONFLICT"
    assert ledger.read_bytes() == before


def test_curate_ratified_row_is_seen_by_ratified_activity_memberships(tmp_path, proposal):
    ledger = tmp_path / "activity_proposals.jsonl"
    receipt = b"curation receipt"
    curated = _curate(proposal, receipt=receipt)
    probation.append_activity_proposals([proposal, curated], ledger)
    ratified = probation.ratified_activity_memberships(
        probation.read_activity_proposals(ledger))
    assert len(ratified) == 1
    assert ratified[0]["curation"]["receipt_sha256"] == hashlib.sha256(receipt).hexdigest()
    assert ratified[0]["curation"]["curator"] == CURATOR
    assert ratified[0]["evidence"] == proposal["evidence"]
    assert ratified[0]["authority_caps"] == proposal["authority_caps"]


def test_curation_before_knowledge_clock_refused(proposal):
    known = proposal["evidence"]["clocks"]["knowledge"]["value"]
    assert known is not None
    with pytest.raises(probation.ActivityProposalRefusal) as caught:
        _curate(proposal, decided_at="2020-01-01T00:00:00Z")
    assert caught.value.code == "PROPOSAL_INVALID"
    assert "predates" in caught.value.args[0]


def test_legacy_proposals_ledger_is_never_written(tmp_path, proposal):
    ledger = tmp_path / "proposals.jsonl"
    with pytest.raises(probation.ActivityProposalRefusal) as caught:
        probation.append_activity_proposals([proposal], ledger)
    assert caught.value.code == "LEGACY_LEDGER_REFUSED"
    assert not ledger.exists()


@pytest.mark.needs_full_checkout("data")
def test_cli_propose_writes_one_valid_row_to_tmp_ledger(tmp_path, capsys):
    ledger = tmp_path / "activity_proposals.jsonl"
    rc = cli.main(["propose", "--issuer", MU_NODE, "--theme", TARGET,
                   "--role", "component_supplier",
                   "--knowledge-cutoff", AFTER_ALL_KNOWLEDGE, "--created", CREATED,
                   "--code-version", CODE_VERSION, "--ledger", str(ledger)])
    assert rc == 0
    printed = json.loads(capsys.readouterr().out.strip())
    expected = probation.make_activity_membership_proposal(
        build_activity_membership_evidence(
            issuer_node_id=MU_NODE, target_theme_id=TARGET, role="component_supplier",
            knowledge_cutoff=AFTER_ALL_KNOWLEDGE, code_version=CODE_VERSION),
        created=CREATED)
    assert printed["proposal_id"] == expected["proposal_id"]
    assert printed["status"] == "PROPOSED"
    assert printed["appended"] == 1 and printed["unchanged"] == 0
    rows = probation.read_activity_proposals(ledger)
    assert len(rows) == 1
    assert {**rows[0], "created": CREATED} == expected


@pytest.mark.needs_full_checkout("data")
def test_committed_ledger_rows_validate_and_carry_the_c01_proposal():
    rows = probation.read_activity_proposals()
    assert rows, "the committed activity ledger must not be empty"
    c01 = [row for row in rows if row["proposal_id"] == C01_PROPOSAL_ID]
    # Append-only history of the first witness: the PROPOSED row, then the
    # RATIFIED row the acting curator appended on 2026-10-22 (PR #10026). The
    # RATIFIED row binds its receipt by sha256; nothing here grants graph
    # membership use, which the bridge still holds on the Chairman ruling.
    assert [row["status"] for row in c01] == ["PROPOSED", "RATIFIED"]
    assert c01[0]["curation"] is None
    receipt = Path("research/theme_graph/activity_curation_receipts/"
                   "actprop_287edbf7e04b8aba873b7493.json")
    assert receipt.exists()
    assert c01[1]["curation"]["receipt_sha256"] == hashlib.sha256(
        receipt.read_bytes()).hexdigest()
    ratified = [row for row in rows if row["status"] == "RATIFIED"]
    assert [row["proposal_id"] for row in ratified] == [C01_PROPOSAL_ID]
    assert len(probation.ratified_activity_memberships(rows)) == 1


def test_cli_refuses_vendor_family_target(tmp_path, capsys):
    rc = cli.main(["propose", "--issuer", MU_NODE, "--theme", "ltheme:x",
                   "--role", "component_supplier",
                   "--knowledge-cutoff", AFTER_ALL_KNOWLEDGE, "--created", CREATED,
                   "--code-version", CODE_VERSION,
                   "--ledger", str(tmp_path / "activity_proposals.jsonl")])
    assert rc == 2
    err = capsys.readouterr().err
    assert err.startswith("REFUSED: ENDPOINT_NOT_ADMITTED")
