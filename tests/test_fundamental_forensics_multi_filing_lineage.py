"""FIF S2: versioned multi-filing (3+ accession) confirmation lineage chains.

Authority: ``WS:FINANCIAL-INTELLIGENCE-FABRIC`` task S2 (acceptance A03, A04,
A05, A12, A53).  v1 — ``derive_confirmation_receipts`` and the
``spans more than two filings`` admission guard — stays byte-identical and is
re-pinned here as the control; this suite pins the SECOND, versioned rule
(v2) for one logical key reprinted across three or more filings:

* only a ``repeated`` chain (every ADJACENT pair exact) mints v2 evidence,
  one receipt per adjacent pair — never a transitive A~C shortcut (A03);
* a comparative reprint is still not a revision, so ``latest_restated``
  stays missing without explicit revision evidence (A04);
* the v1 refusal is preserved, not disabled — v1 bundles over 3+ filings
  still raise, and v2 is a separately versioned law (A05);
* a filing or rule not yet available under a source/system clock is excluded,
  and a recorded_at before the chain rule clock sees no v2 evidence (A12/A53).

All facts are offline synthetic occurrences; no golden fixture is mutated and
``GOLDEN_AAPL_QUERY_ACCESSIONS`` is never widened.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from engine.fundamental_forensics.ixbrl_raw_ledger import (
    GoldenAaplFinancialQueryProvider,
)
from engine.fundamental_forensics.lineage_evidence import (
    ADMITTED_CONFIRMATION_RULE_VERSIONS,
    CHAIN_STATE_AMBIGUOUS,
    CHAIN_STATE_CONTRADICTORY,
    CHAIN_STATE_REPEATED,
    CHAIN_STATE_REVISED,
    CHAIN_STATE_ROUNDED_CONSISTENT,
    CHAIN_STATES,
    CONFIRMATION_CHAIN_RULE_AVAILABLE_AT,
    CONFIRMATION_CHAIN_RULE_VERSION,
    LineageEvidenceError,
    LineageEvidenceReceipt,
    _positive_evidence_payload,
    classify_filing_chain,
    derive_chain_confirmation_receipts,
    derive_confirmation_receipts,
    evaluate_confirmation,
    receipt_envelope_refusal,
)
from engine.fundamental_forensics.query import (
    BitemporalMetricQueryEngine,
    QueryPolicy,
)
from engine.fundamental_forensics.raw_ledger import (
    FactEventType,
    RawFactLedger,
)

ROOT = Path(__file__).resolve().parents[1]

_GOLDEN_ENTITY = "ISS:US-XNAS-AAPL"
_URI = "http://fasb.org/us-gaap/2025"

# v1 mint availability (the accepted FIF-3A4 rule clock plus its recording).
_A4_AVAILABLE = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
# FIF S2 clocks: the chain rule clock, and post-everything query cutoffs.
_S2_AVAILABLE = datetime(2026, 10, 12, tzinfo=timezone.utc)
_S2_SOURCE = "2026-10-20T00:00:00Z"
_S2_RECORDED = "2026-10-20T00:00:00Z"

_A_ACCEPTED = "2025-10-31T10:00:00Z"
_B_ACCEPTED = "2026-01-31T10:00:00Z"
_C_ACCEPTED = "2026-07-31T10:00:00Z"
_D_ACCEPTED = "2026-08-10T10:00:00Z"

_UNLINKED_REASON = "unlinked source vintages require an explicit typed revision lineage"
_CHAIN_PATH_MESSAGE = "chain lineage evidence must form one strictly ordered path"


def _synthetic_fact(
    *,
    accession,
    body,
    value="359241000000",
    accepted_at,
    decimals="-6",
    recorded_at="2026-08-23T00:00:00Z",
    event_type=FactEventType.FILED,
    revision_of=None,
    source_occurrence_key=None,
    source_span=(10, 20),
    instant="2025-09-27",
):
    from engine.fundamental_forensics.raw_ledger import (
        FactContext,
        FactUnit,
        SourceIdentity,
        make_raw_fact,
    )

    return make_raw_fact(
        source=SourceIdentity(
            source="sec-edgar",
            entity_id="0000320193",
            accession=accession,
            document_id=f"doc-{accession}.htm",
            body_sha256=body,
            source_url="https://www.sec.gov/Archives/example",
        ),
        concept_qname="us-gaap:Assets",
        context=FactContext(
            context_id="ctx",
            entity_scheme="http://www.sec.gov/CIK",
            entity_identifier="0000320193",
            instant=instant,
        ),
        unit=FactUnit("usd", ["iso4217:USD"]),
        raw_token=value,
        parsed_value=value,
        decimals=decimals,
        source_span=source_span,
        accepted_at=accepted_at,
        recorded_at=recorded_at,
        event_type=event_type,
        revision_of=revision_of,
        source_occurrence_key=source_occurrence_key,
    )


def _chain_facts(*, c_value="359241000000", c_decimals="-6"):
    """An ordinary comparative reprint: 10-K, then 10-Q, then 10-Q."""
    return [
        _synthetic_fact(accession="0001", body="a" * 64, accepted_at=_A_ACCEPTED),
        _synthetic_fact(accession="0002", body="b" * 64, accepted_at=_B_ACCEPTED),
        _synthetic_fact(
            accession="0003",
            body="c" * 64,
            accepted_at=_C_ACCEPTED,
            value=c_value,
            decimals=c_decimals,
        ),
    ]


def _uris(facts):
    return {
        (fact.source.accession, fact.source_occurrence_key or ""): _URI
        for fact in facts
    }


def _v2_chain_receipts(facts):
    return derive_chain_confirmation_receipts(
        facts,
        system_available_at=_S2_AVAILABLE,
        original_taxonomy_uris=_uris(facts),
    )


def _engine(facts, receipts, registry):
    return BitemporalMetricQueryEngine(
        RawFactLedger(tuple(facts)),
        registry,
        entities={"AAPL": "0000320193"},
        lineage_evidence=receipts,
    )


def _policy(
    *,
    source=_S2_SOURCE,
    recorded=_S2_RECORDED,
    selection="latest_known_as_of",
):
    return QueryPolicy(
        source_snapshot_at=source,
        recorded_at=recorded,
        selection=selection,
    )


def _as_v2(receipt, **overrides):
    """A hand-built v2 twin of a genuine receipt, envelope fields overridden.

    The constructor recomputes the digest, so the twin is internally
    self-consistent — the only forgery shape that matters.
    """
    return LineageEvidenceReceipt(
        parent_occurrence_id=overrides.pop(
            "parent_occurrence_id", receipt.parent_occurrence_id
        ),
        child_occurrence_id=overrides.pop(
            "child_occurrence_id", receipt.child_occurrence_id
        ),
        logical_key=receipt.logical_key,
        source_known_at=overrides.pop("source_known_at", receipt.source_known_at),
        system_available_at=overrides.pop(
            "system_available_at", receipt.system_available_at
        ),
        positive_evidence=dict(receipt.positive_evidence),
        evidence_rule_version=overrides.pop(
            "evidence_rule_version", CONFIRMATION_CHAIN_RULE_VERSION
        ),
        **overrides,
    )


@pytest.fixture(scope="module")
def registry():
    provider = GoldenAaplFinancialQueryProvider(ROOT)
    return provider.resolve(_GOLDEN_ENTITY).registry


def _by_parent_accession(receipts):
    return {receipt.positive_evidence["parent_accession"]: receipt for receipt in receipts}


# ---------------------------------------------------------------------------
# t1 — a repeated 10-K / 10-Q / 10-Q chain
# ---------------------------------------------------------------------------


def test_a_repeated_chain_classifies_repeated_with_exact_edges():
    facts = _chain_facts()
    classification = classify_filing_chain(facts, original_taxonomy_uris=_uris(facts))
    assert classification.state == CHAIN_STATE_REPEATED
    assert classification.accessions == ("0001", "0002", "0003")
    assert classification.edge_refusals == (None, None)
    assert classification.logical_key == facts[0].logical_key


def test_a_repeated_chain_mints_exactly_two_adjacent_v2_receipts():
    facts = _chain_facts()
    receipts = _v2_chain_receipts(facts)
    assert len(receipts) == 2
    assert all(receipt.evidence_rule_version == CONFIRMATION_CHAIN_RULE_VERSION for receipt in receipts)
    assert all(receipt.is_positive_confirmation for receipt in receipts)
    by_parent = _by_parent_accession(receipts)
    assert set(by_parent) == {"0001", "0002"}
    assert by_parent["0001"].positive_evidence["child_accession"] == "0002"
    assert by_parent["0002"].positive_evidence["child_accession"] == "0003"
    # Adjacent pairs only: neither receipt links A to C.
    edges = {
        (receipt.parent_occurrence_id, receipt.child_occurrence_id)
        for receipt in receipts
    }
    assert (facts[0].occurrence_id, facts[2].occurrence_id) not in edges
    # v1 is unchanged on the same facts: three filings still mint nothing.
    assert (
        derive_confirmation_receipts(
            facts, system_available_at=_A4_AVAILABLE, original_taxonomy_uris=_uris(facts)
        )
        == ()
    )


def test_a_repeated_chain_resolves_through_the_query_engine(registry):
    """A03/A04 end to end: latest_known reads C, as_reported reads A, and a
    confirmation chain is still not a reported revision vintage."""
    facts = _chain_facts()
    receipts = _v2_chain_receipts(facts)
    engine = _engine(facts, receipts, registry)

    latest = engine._select_source_group(tuple(facts), _policy(selection="latest_known_as_of"))
    assert latest.state.value == "value"
    assert latest.occurrence.occurrence_id == facts[2].occurrence_id
    assert latest.occurrence.source.accession == "0003"

    as_reported = engine._select_source_group(tuple(facts), _policy(selection="as_reported"))
    assert as_reported.state.value == "value"
    assert as_reported.occurrence.occurrence_id == facts[0].occurrence_id
    assert as_reported.occurrence.source.accession == "0001"

    restated = engine._select_source_group(tuple(facts), _policy(selection="latest_restated"))
    assert restated.state.value == "missing"
    assert restated.reason == "no eligible explicitly typed reported revision vintage"


# ---------------------------------------------------------------------------
# t2 — no evidence keeps the honest unlinked refusal
# ---------------------------------------------------------------------------


def test_three_filings_without_evidence_stay_not_evaluable(registry):
    facts = _chain_facts()
    engine = _engine(facts, (), registry)
    selection = engine._select_source_group(tuple(facts), _policy())
    assert selection.state.value == "not_evaluable"
    assert selection.reason == _UNLINKED_REASON


# ---------------------------------------------------------------------------
# t3 — the v1 guard is preserved (A05)
# ---------------------------------------------------------------------------


def test_a_v1_chained_bundle_still_raises_the_two_filing_guard(registry):
    facts = _chain_facts()
    uris = _uris(facts)
    chained = derive_confirmation_receipts(
        facts[:2], system_available_at=_A4_AVAILABLE, original_taxonomy_uris=uris
    ) + derive_confirmation_receipts(
        facts[1:], system_available_at=_A4_AVAILABLE, original_taxonomy_uris=uris
    )
    assert len(chained) == 2
    assert all(receipt.evidence_rule_version == 1 for receipt in chained)
    with pytest.raises(LineageEvidenceError, match="spans more than two filings"):
        _engine(facts, chained, registry)


# ---------------------------------------------------------------------------
# t4 — mixed rule versions on one key
# ---------------------------------------------------------------------------


def test_mixed_rule_versions_on_one_key_are_refused(registry):
    facts = _chain_facts()
    uris = _uris(facts)
    v1_edge = derive_confirmation_receipts(
        facts[:2], system_available_at=_A4_AVAILABLE, original_taxonomy_uris=uris
    )
    assert len(v1_edge) == 1
    v2_edge = next(
        receipt
        for receipt in _v2_chain_receipts(facts)
        if receipt.positive_evidence["parent_accession"] == "0002"
    )
    with pytest.raises(LineageEvidenceError, match="mixes confirmation rule versions"):
        _engine(facts, (v1_edge[0], v2_edge), registry)


# ---------------------------------------------------------------------------
# t5 — a changed tail is contradictory and never unifies A with C
# ---------------------------------------------------------------------------


def test_a_changed_tail_is_contradictory_and_never_mints(registry):
    facts = _chain_facts(c_value="400000000000")
    classification = classify_filing_chain(facts, original_taxonomy_uris=_uris(facts))
    assert classification.state == CHAIN_STATE_CONTRADICTORY
    assert classification.edge_refusals == (None, "changed_value")
    assert _v2_chain_receipts(facts) == ()


def test_a_partial_v2_path_missing_a_filing_is_refused_at_admission(registry):
    """A hand-built v2 A->B receipt alone (missing C) cannot chain; A and C
    therefore stay unlinked — the whole-ledger path is the only lawful shape."""
    contradictory = _chain_facts(c_value="400000000000")
    repeated = _chain_facts()
    a_to_b = next(
        receipt
        for receipt in _v2_chain_receipts(repeated)
        if receipt.positive_evidence["parent_accession"] == "0001"
    )
    with pytest.raises(LineageEvidenceError, match=_CHAIN_PATH_MESSAGE):
        _engine(contradictory, (a_to_b,), registry)


# ---------------------------------------------------------------------------
# t6 — a rounded link breaks the chain; no greedy transitive equality (A03)
# ---------------------------------------------------------------------------


def _rounded_chain_facts():
    return [
        _synthetic_fact(
            accession="0001", body="a" * 64, accepted_at=_A_ACCEPTED,
            value="90678000000", decimals="-6",
        ),
        _synthetic_fact(
            accession="0002", body="b" * 64, accepted_at=_B_ACCEPTED,
            value="90700000000", decimals="-8",
        ),
        _synthetic_fact(
            accession="0003", body="c" * 64, accepted_at=_C_ACCEPTED,
            value="90700000000", decimals="-8",
        ),
    ]


def test_a_rounded_link_classifies_rounded_consistent_and_mints_nothing(registry):
    facts = _rounded_chain_facts()
    # Control: the A/B pair is precision-consistent under the exact v1 rule
    # (interval overlap, unequal values/tokens), and B/C is exact.
    assert (
        evaluate_confirmation(
            (facts[0],), (facts[1],),
            parent_taxonomy_uri=_URI, child_taxonomy_uri=_URI, require_taxonomy_uri=True,
        )
        == "precision_consistent_unconfirmed"
    )
    classification = classify_filing_chain(facts, original_taxonomy_uris=_uris(facts))
    assert classification.state == CHAIN_STATE_ROUNDED_CONSISTENT
    assert classification.edge_refusals == ("precision_consistent_unconfirmed", None)
    assert _v2_chain_receipts(facts) == ()
    # No transitivity: B~C exact never rescues the rounded A~B link, so A and
    # C stay unlinked roots.
    engine = _engine(facts, (), registry)
    selection = engine._select_source_group(tuple(facts), _policy())
    assert selection.state.value == "not_evaluable"
    assert selection.reason == _UNLINKED_REASON


# ---------------------------------------------------------------------------
# t7 — ambiguous chains, and the admitted v2 path shape
# ---------------------------------------------------------------------------


def test_equal_acceptance_times_classify_ambiguous_and_mint_nothing():
    facts = [
        _synthetic_fact(accession="0001", body="a" * 64, accepted_at="2026-05-01T00:00:00Z"),
        _synthetic_fact(accession="0002", body="b" * 64, accepted_at="2026-05-01T00:00:00Z"),
        _synthetic_fact(accession="0003", body="c" * 64, accepted_at=_C_ACCEPTED),
    ]
    classification = classify_filing_chain(facts, original_taxonomy_uris=_uris(facts))
    assert classification.state == CHAIN_STATE_AMBIGUOUS
    # No strict order exists, so the accessions fall back to lexicographic
    # order and no edge is evaluable.
    assert classification.accessions == ("0001", "0002", "0003")
    assert classification.edge_refusals == ()
    assert _v2_chain_receipts(facts) == ()


def test_admission_refuses_forks_skips_and_missing_accessions(registry):
    facts = _chain_facts()
    uris = _uris(facts)
    honest = _v2_chain_receipts(facts)
    a_to_b = next(r for r in honest if r.positive_evidence["parent_accession"] == "0001")
    v1_skip = derive_confirmation_receipts(
        [facts[0], facts[2]], system_available_at=_A4_AVAILABLE, original_taxonomy_uris=uris
    )
    assert len(v1_skip) == 1
    skip = _as_v2(v1_skip[0], system_available_at=_S2_AVAILABLE)

    # A skip edge A->C alone is not the adjacent path.
    with pytest.raises(LineageEvidenceError, match=_CHAIN_PATH_MESSAGE):
        _engine(facts, (skip,), registry)
    # A fork: two v2 receipts sharing one parent (A->B and A->C).
    with pytest.raises(LineageEvidenceError, match=_CHAIN_PATH_MESSAGE):
        _engine(facts, (a_to_b, skip), registry)
    # A closed triangle over the path — the guard-4-legal cycle shape — has
    # an extra edge and is not the adjacent path either.
    with pytest.raises(LineageEvidenceError, match=_CHAIN_PATH_MESSAGE):
        _engine(facts, (*honest, skip), registry)
    # A path missing one ledger accession: a complete 3-filing path over a
    # ledger that holds a fourth filing of the same logical key.
    four = facts + [_synthetic_fact(accession="0004", body="d" * 64, accepted_at=_D_ACCEPTED)]
    with pytest.raises(LineageEvidenceError, match=_CHAIN_PATH_MESSAGE):
        _engine(four, honest, registry)


def test_admission_refuses_a_back_edge_at_the_per_edge_guard(registry):
    """A literal back edge C->A is refused before the shape gate: guard 4
    (parent accepted strictly before child, on group representatives) makes
    every admitted edge forward in the total representative-time order, so no
    admitted edge set can contain a cycle — the chain-path guard's no-cycle
    clause is reached only through forward non-path shapes (previous test)."""
    facts = _chain_facts()
    honest = _v2_chain_receipts(facts)
    backwards = LineageEvidenceReceipt(
        parent_occurrence_id=facts[2].occurrence_id,
        child_occurrence_id=facts[0].occurrence_id,
        logical_key=facts[0].logical_key,
        source_known_at=max(facts[2].accepted_at, facts[0].accepted_at),
        system_available_at=_S2_AVAILABLE,
        positive_evidence=_positive_evidence_payload(
            (facts[2],), (facts[0],),
            parent_taxonomy_uri=_URI, child_taxonomy_uri=_URI,
        ),
        evidence_rule_version=CONFIRMATION_CHAIN_RULE_VERSION,
    )
    with pytest.raises(LineageEvidenceError, match="not a v1 positive"):
        _engine(facts, (*honest, backwards), registry)


# ---------------------------------------------------------------------------
# t8 — same-report duplicates are kept and break the chain (A03)
# ---------------------------------------------------------------------------


def test_disagreeing_same_report_duplicates_are_kept_and_break_the_chain(registry):
    dup_a = _synthetic_fact(
        accession="0001", body="a" * 64, accepted_at=_A_ACCEPTED,
        value="359241000000", decimals="-6",
        source_occurrence_key="span-a", source_span=(10, 20),
    )
    dup_b = _synthetic_fact(
        accession="0001", body="a" * 64, accepted_at=_A_ACCEPTED,
        value="360000000000", decimals="-8",
        source_occurrence_key="span-b", source_span=(30, 40),
    )
    facts = [
        dup_a,
        dup_b,
        _synthetic_fact(accession="0002", body="b" * 64, accepted_at=_B_ACCEPTED),
        _synthetic_fact(accession="0003", body="c" * 64, accepted_at=_C_ACCEPTED),
    ]
    # Both same-report occurrences survive as distinct source facts.
    assert len({fact.occurrence_id for fact in facts}) == 4
    # Their rounding intervals are disjoint (359,241M±0.5M vs 360,000M±50M),
    # so guard 7 (``_duplicates_agree`` on the group) refuses every edge out
    # of filing 0001; precedence (ii) classifies the chain ambiguous.
    classification = classify_filing_chain(facts, original_taxonomy_uris=_uris(facts))
    assert classification.state == CHAIN_STATE_AMBIGUOUS
    assert classification.edge_refusals == ("ambiguous_duplicate_group", None)
    assert _v2_chain_receipts(facts) == ()
    engine = _engine(facts, (), registry)
    selection = engine._select_source_group(tuple(facts), _policy())
    assert selection.state.value == "not_evaluable"


# ---------------------------------------------------------------------------
# t9 — a typed revision occurrence makes the chain revised
# ---------------------------------------------------------------------------


def test_a_typed_revision_occurrence_classifies_revised_and_mints_nothing():
    filed = _chain_facts()
    restated = _synthetic_fact(
        accession="0003",
        body="c" * 64,
        accepted_at=_C_ACCEPTED,
        event_type=FactEventType.RESTATEMENT,
        revision_of=filed[1].occurrence_id,
    )
    chain = [filed[0], filed[1], restated]
    classification = classify_filing_chain(chain, original_taxonomy_uris=_uris(chain))
    assert classification.state == CHAIN_STATE_REVISED
    assert _v2_chain_receipts(chain) == ()


# ---------------------------------------------------------------------------
# t10 — the four clocks (A12/A53)
# ---------------------------------------------------------------------------


def test_a_source_cutoff_between_filings_hides_the_unaccepted_tail(registry):
    """A12: with source_snapshot_at between B and C, C is not source-visible,
    so latest_known resolves through B and the B->C receipt is inert."""
    facts = _chain_facts()
    receipts = _v2_chain_receipts(facts)
    engine = _engine(facts, receipts, registry)
    selection = engine._select_source_group(
        tuple(facts), _policy(source="2026-04-01T00:00:00Z")
    )
    assert selection.state.value == "value"
    assert selection.occurrence.occurrence_id == facts[1].occurrence_id
    assert selection.occurrence.source.accession == "0002"


def test_a_recorded_cutoff_before_the_chain_rule_sees_no_v2_evidence(registry):
    """A53: no newest-rule hindsight — before 2026-10-12 the v2 receipts are
    not system-visible and the cell keeps the unlinked refusal."""
    facts = _chain_facts()
    receipts = _v2_chain_receipts(facts)
    assert all(receipt.system_available_at >= CONFIRMATION_CHAIN_RULE_AVAILABLE_AT for receipt in receipts)
    engine = _engine(facts, receipts, registry)
    selection = engine._select_source_group(
        tuple(facts), _policy(recorded="2026-10-01T00:00:00Z")
    )
    assert selection.state.value == "not_evaluable"
    assert selection.reason == _UNLINKED_REASON


def test_minting_below_the_chain_clock_floor_raises():
    facts = _chain_facts()
    with pytest.raises(LineageEvidenceError, match="precedes the accepted lineage clock floor"):
        derive_chain_confirmation_receipts(
            facts,
            system_available_at=datetime(2026, 10, 11, tzinfo=timezone.utc),
            original_taxonomy_uris=_uris(facts),
        )
    # A recorded clock above the rule clock dominates the floor too.
    late = [
        _synthetic_fact(accession="0001", body="a" * 64, accepted_at=_A_ACCEPTED, recorded_at="2026-10-15T00:00:00Z"),
        _synthetic_fact(accession="0002", body="b" * 64, accepted_at=_B_ACCEPTED, recorded_at="2026-10-15T00:00:00Z"),
        _synthetic_fact(accession="0003", body="c" * 64, accepted_at=_C_ACCEPTED, recorded_at="2026-10-15T00:00:00Z"),
    ]
    with pytest.raises(LineageEvidenceError, match="precedes the accepted lineage clock floor"):
        derive_chain_confirmation_receipts(
            late,
            system_available_at=datetime(2026, 10, 13, tzinfo=timezone.utc),
            original_taxonomy_uris=_uris(late),
        )


def test_a_backdated_v2_envelope_is_refused_at_admission(registry):
    facts = _chain_facts()
    honest = _v2_chain_receipts(facts)
    backdated = _as_v2(
        honest[0], system_available_at=datetime(2026, 10, 10, tzinfo=timezone.utc)
    )
    assert backdated.receipt_id != honest[0].receipt_id
    with pytest.raises(LineageEvidenceError, match="receipt_system_availability_backdated"):
        _engine(facts, (backdated, *honest[1:]), registry)


def test_a_version_three_receipt_is_refused_as_a_rule_mismatch(registry):
    facts = _chain_facts()
    honest = _v2_chain_receipts(facts)
    v3 = _as_v2(honest[0], evidence_rule_version=3)
    assert v3.receipt_id != honest[0].receipt_id
    with pytest.raises(LineageEvidenceError, match="receipt_rule_mismatch"):
        _engine(facts, (v3, *honest[1:]), registry)


def test_the_v2_envelope_accepts_honest_chain_receipts():
    facts = _chain_facts()
    for receipt in _v2_chain_receipts(facts):
        parent = next(f for f in facts if f.occurrence_id == receipt.parent_occurrence_id)
        child = next(f for f in facts if f.occurrence_id == receipt.child_occurrence_id)
        assert receipt_envelope_refusal(receipt, (parent,), (child,)) is None


# ---------------------------------------------------------------------------
# t11 — classifier input contracts
# ---------------------------------------------------------------------------


def test_the_classifier_rejects_underspecified_inputs():
    facts = _chain_facts()
    with pytest.raises(LineageEvidenceError):
        classify_filing_chain(facts[:1], original_taxonomy_uris=_uris(facts))
    other_key = _synthetic_fact(
        accession="0009", body="e" * 64, accepted_at="2026-02-01T00:00:00Z",
        instant="2024-09-28",
    )
    assert other_key.logical_key != facts[0].logical_key
    with pytest.raises(LineageEvidenceError):
        classify_filing_chain([*facts[:2], other_key], original_taxonomy_uris=_uris(facts))


def test_classification_inputs_are_not_mutated():
    facts = _chain_facts()
    before = [(fact.occurrence_id, fact.raw_token, fact.decimals) for fact in facts]
    classify_filing_chain(facts, original_taxonomy_uris=_uris(facts))
    derive_chain_confirmation_receipts(
        facts, system_available_at=_S2_AVAILABLE, original_taxonomy_uris=_uris(facts)
    )
    after = [(fact.occurrence_id, fact.raw_token, fact.decimals) for fact in facts]
    assert before == after
    assert len(facts) == 3


# ---------------------------------------------------------------------------
# t12 — the v1 control in this suite
# ---------------------------------------------------------------------------


def test_a_two_filing_key_stays_v1_exclusive():
    facts = _chain_facts()[:2]
    v1 = derive_confirmation_receipts(
        facts, system_available_at=_A4_AVAILABLE, original_taxonomy_uris=_uris(facts)
    )
    assert len(v1) == 1
    assert v1[0].evidence_rule_version == 1
    assert v1[0].evidence_rule_version in ADMITTED_CONFIRMATION_RULE_VERSIONS
    assert derive_chain_confirmation_receipts(
        facts, system_available_at=_S2_AVAILABLE, original_taxonomy_uris=_uris(facts)
    ) == ()


def test_the_chain_state_vocabulary_is_the_frozen_tuple():
    assert CHAIN_STATES == (
        "repeated",
        "revised",
        "rounded_consistent",
        "contradictory",
        "ambiguous",
        "unproven",
    )
    assert CONFIRMATION_CHAIN_RULE_VERSION == 2
    assert ADMITTED_CONFIRMATION_RULE_VERSIONS == (1, 2)
    assert CONFIRMATION_CHAIN_RULE_AVAILABLE_AT == datetime(
        2026, 10, 12, tzinfo=timezone.utc
    )


# ---------------------------------------------------------------------------
# t13 — A04: reprint vs amendment vs changed reported fact
# ---------------------------------------------------------------------------

_SELECTIONS = ("latest_known_as_of", "as_reported", "latest_restated")


def _selected(facts, receipts, registry):
    engine = _engine(facts, receipts, registry)
    out = {}
    for selection in _SELECTIONS:
        group = engine._select_source_group(tuple(facts), _policy(selection=selection))
        accession = group.occurrence.source.accession if group.occurrence else None
        out[selection] = (group.state.value, accession, group.reason)
    return out


def test_a04_a_confirmed_reprint_is_not_a_restatement(registry):
    """Confirmation links the vintages but never makes the reprint a revision."""
    facts = _chain_facts()[:2]
    receipts = derive_confirmation_receipts(
        facts, system_available_at=_A4_AVAILABLE, original_taxonomy_uris=_uris(facts)
    )
    assert len(receipts) == 1
    out = _selected(facts, receipts, registry)
    assert out["latest_known_as_of"] == ("value", "0002", None)
    assert out["as_reported"] == ("value", "0001", None)
    assert out["latest_restated"] == (
        "missing",
        None,
        "no eligible explicitly typed reported revision vintage",
    )


@pytest.mark.parametrize("value", ["359241000000", "400000000000"])
def test_a04_an_untyped_later_vintage_is_never_silently_picked(registry, value):
    """A same-value reprint or a changed value without lineage stays not evaluable."""
    facts = [
        _synthetic_fact(accession="0001", body="a" * 64, accepted_at=_A_ACCEPTED),
        _synthetic_fact(accession="0002", body="b" * 64, accepted_at=_B_ACCEPTED, value=value),
    ]
    out = _selected(facts, (), registry)
    assert out == {
        selection: ("not_evaluable", None, _UNLINKED_REASON) for selection in _SELECTIONS
    }


@pytest.mark.parametrize("value", ["359241000000", "400000000000"])
def test_a04_only_a_typed_amendment_satisfies_latest_restated(registry, value):
    """An explicit AMENDMENT revision is restated evidence; as-reported keeps the original."""
    original = _synthetic_fact(accession="0001", body="a" * 64, accepted_at=_A_ACCEPTED)
    amendment = _synthetic_fact(
        accession="0002",
        body="b" * 64,
        accepted_at=_B_ACCEPTED,
        value=value,
        event_type=FactEventType.AMENDMENT,
        revision_of=original.occurrence_id,
    )
    out = _selected([original, amendment], (), registry)
    assert out == {
        "latest_known_as_of": ("value", "0002", None),
        "as_reported": ("value", "0001", None),
        "latest_restated": ("value", "0002", None),
    }


def test_a12_a_correction_recorded_after_the_cutoff_stays_out_of_the_then_known_view(registry):
    """A12 source-layer clock: replay before the amendment was recorded sees only the original."""
    original = _synthetic_fact(accession="0001", body="a" * 64, accepted_at=_A_ACCEPTED)
    amendment = _synthetic_fact(
        accession="0002",
        body="b" * 64,
        accepted_at=_B_ACCEPTED,
        value="400000000000",
        recorded_at="2026-10-15T00:00:00Z",
        event_type=FactEventType.AMENDMENT,
        revision_of=original.occurrence_id,
    )
    facts = (original, amendment)
    engine = _engine(facts, (), registry)

    def at(recorded):
        out = {}
        for selection in _SELECTIONS:
            group = engine._select_source_group(
                facts, _policy(recorded=recorded, selection=selection)
            )
            accession = group.occurrence.source.accession if group.occurrence else None
            out[selection] = (group.state.value, accession, group.reason)
        return out

    assert at("2026-10-01T00:00:00Z") == {
        "latest_known_as_of": ("value", "0001", None),
        "as_reported": ("value", "0001", None),
        "latest_restated": (
            "missing",
            None,
            "no eligible explicitly typed reported revision vintage",
        ),
    }
    assert at(_S2_RECORDED) == {
        "latest_known_as_of": ("value", "0002", None),
        "as_reported": ("value", "0001", None),
        "latest_restated": ("value", "0002", None),
    }
