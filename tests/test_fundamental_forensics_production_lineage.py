"""FIF S2-p: the production lineage mint (v1 pairs ∪ v2 chains) and its proof.

Authority: ``WS:FINANCIAL-INTELLIGENCE-FABRIC`` task S2-p (acceptance A45,
A05, A12, A53; seat rulings R-S2P-1 and F10).  R-S2P-1: ONE function, ONE
mint path — ``mint_production_lineage_evidence`` returns the union of the v1
pair rule and the v2 chain rule over one issuer's admitted ledger, and the
golden provider keeps minting v1 alone.  F10 is CLOSED "no defect": the
clock law already prevents lookahead, and its adversarial repro (census Q9)
is folded in below as a named regression test.

The unit tests mint from fabricated in-memory filing packages so the taxonomy
URI map is produced by the SAME parser primitive the golden helper uses.  The
e2e test ports the census Q8 scratch: the committed FIP1 fixture extended with
two synthetic comparative reprints (one logical key across three accessions)
is minted through the production function, published into an in-memory
strict-conditional store, loaded via ``load_latest_generation``, and served
through ``ProductionFinancialQueryProvider`` + ``execute_financial_query``.

Offline only: no network, no wall clock, no real store — everything is
synthetic facts, committed fixtures, and ``InMemoryStrictConditionalStore``.
"""
from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from engine.fundamental_forensics import production_datasets as PDS
from engine.fundamental_forensics.admitted_filing_package import AdmittedFilingPackage
from engine.fundamental_forensics.financial_intelligence_packet import (
    EntityInput,
    load_filing_package_fixture,
)
from engine.fundamental_forensics.ixbrl_raw_ledger import (
    GOLDEN_AAPL_QUERY_ACCESSIONS,
    original_concept_namespace_uris,
)
from engine.fundamental_forensics.lineage_evidence import (
    CONFIRMATION_CHAIN_RULE_AVAILABLE_AT,
    CONFIRMATION_RULE_AVAILABLE_AT,
    LineageEvidenceError,
    derive_confirmation_receipts,
)
from engine.fundamental_forensics.production_lineage import (
    ProductionLineageError,
    admitted_concept_namespace_uris,
    mint_production_lineage_evidence,
)
from engine.fundamental_forensics.production_provider import (
    ProductionFinancialQueryProvider,
)
from engine.fundamental_forensics.query_service import (
    CanonicalEntityBinding,
    FinancialQueryUnavailableError,
    execute_financial_query,
)
from engine.fundamental_forensics.raw_ledger import (
    FactEventType,
    RawFactLedger,
)
from engine.fundamental_forensics.statement_graph import (
    GoldenFilingPackage,
    load_golden_aapl_package,
)

ROOT = Path(__file__).resolve().parents[1]

# FIP1 is a synthetic industrial issuer with no shipped coverage record; the
# hermetic production-path tests inject its SIC (R1-SIC/R2).
_FIP1_CIK = "0000999999"
_INDUSTRIAL_SIC = "3571"


def _fip1_issuer_sic_resolver(cik: str) -> str | None:
    return _INDUSTRIAL_SIC if cik == _FIP1_CIK else None

# The policy-approved standard taxonomy namespace the fabricated primary
# documents declare (the same URI the golden fixture family carries).
_TAXONOMY_URI = "http://fasb.org/us-gaap/2025"

# Unit-mint clocks: above every floor (rule clocks and recorded clocks).
_MINT_CLOCK = datetime(2026, 10, 14, tzinfo=timezone.utc)
# A clock above the v1 rule clock but below the v2 chain rule clock.
_BELOW_CHAIN_CLOCK = datetime(2026, 10, 11, tzinfo=timezone.utc)
# A clock above the chain rule clock but below a later capture recording.
_BELOW_RECORDED_CLOCK = datetime(2026, 10, 12, tzinfo=timezone.utc)

_A_ACCEPTED = "2025-10-31T10:00:00Z"
_B_ACCEPTED = "2026-01-31T10:00:00Z"
_C_ACCEPTED = "2026-07-31T10:00:00Z"

_UNLINKED_REASON = "unlinked source vintages require an explicit typed revision lineage"


# ---------------------------------------------------------------------------
# Synthetic occurrences + fabricated filing packages
# ---------------------------------------------------------------------------


def _fact(
    *,
    accession,
    body,
    accepted_at,
    sok,
    value="359241000000",
    decimals="-6",
    recorded_at="2026-08-23T00:00:00Z",
    instant="2025-09-27",
    concept="us-gaap:Assets",
    event_type=FactEventType.FILED,
    revision_of=None,
    source_span=(10, 20),
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
        concept_qname=concept,
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
        source_occurrence_key=sok,
    )


def _primary_document(fact_ids) -> bytes:
    """A minimal Inline XBRL primary document parsed by the SAME strict parser.

    Every fact id becomes a ``(accession, fact_id) -> Clark URI`` entry through
    the production twin, exactly as a real admitted package would.
    """
    facts = "".join(
        '<ix:nonFraction id="{fact_id}" name="us-gaap:Assets" '
        'contextRef="c" unitRef="u" decimals="-6">359241000000</ix:nonFraction>'.format(
            fact_id=fact_id
        )
        for fact_id in fact_ids
    )
    return (
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" '
        'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
        'xmlns:iso4217="http://www.xbrl.org/2003/iso4217" '
        'xmlns:us-gaap="{uri}"><head></head><body><ix:header><ix:resources>'
        '<xbrli:context id="c"><xbrli:entity>'
        '<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier>'
        "</xbrli:entity><xbrli:period><xbrli:instant>2025-09-27</xbrli:instant>"
        "</xbrli:period></xbrli:context>"
        '<xbrli:unit id="u"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>'
        "</ix:resources></ix:header>"
        "{facts}</body></html>"
    ).format(uri=_TAXONOMY_URI, facts=facts).encode("utf-8")


def _package(accession, fact_ids):
    manifest = {
        "accession": accession,
        "primary_document": f"doc-{accession}.htm",
        "members": [
            {"name": f"doc-{accession}.htm", "state": "stored", "role": "primary"}
        ],
    }
    members = {f"doc-{accession}.htm": _primary_document(fact_ids)}
    return GoldenFilingPackage(manifest=manifest, members=members)


def _packages(events):
    """One fabricated package per accession, carrying that accession's fact ids."""
    by_accession: dict[str, list[str]] = {}
    for event in events:
        by_accession.setdefault(event.source.accession, []).append(
            event.source_occurrence_key
        )
    return tuple(
        _package(accession, sorted(soks))
        for accession, soks in sorted(by_accession.items())
    )


def _pair_events():
    """One logical key reprinted across exactly two accessions (v1's scope)."""
    return [
        _fact(accession="0001", body="a" * 64, accepted_at=_A_ACCEPTED, sok="pair-a"),
        _fact(accession="0002", body="b" * 64, accepted_at=_B_ACCEPTED, sok="pair-b"),
    ]


def _chain_events(
    *,
    instant="2024-09-27",
    a_decimals="-6",
    c_value="359241000000",
    c_decimals="-6",
    c_event_type=FactEventType.FILED,
    c_revision_of_index=None,
    c_accepted=_C_ACCEPTED,
    accepted=None,
    recorded_at="2026-08-23T00:00:00Z",
):
    """One logical key reprinted across three accessions (v2's scope).

    ``c_revision_of_index`` makes the tail a typed revision of an earlier
    filing's occurrence (the ledger requires the parent appended first).
    """
    if accepted is None:
        accepted = [_A_ACCEPTED, _B_ACCEPTED, c_accepted]
    parent_a = _fact(
        accession="0001",
        body="a" * 64,
        accepted_at=accepted[0],
        sok="chain-a",
        instant=instant,
        decimals=a_decimals,
        recorded_at=recorded_at,
    )
    parent_b = _fact(
        accession="0002",
        body="b" * 64,
        accepted_at=accepted[1],
        sok="chain-b",
        instant=instant,
        recorded_at=recorded_at,
    )
    earlier = (parent_a, parent_b)
    tail = _fact(
        accession="0003",
        body="c" * 64,
        accepted_at=accepted[2],
        sok="chain-c",
        instant=instant,
        value=c_value,
        decimals=c_decimals,
        event_type=c_event_type,
        revision_of=(
            earlier[c_revision_of_index].occurrence_id
            if c_revision_of_index is not None
            else None
        ),
        recorded_at=recorded_at,
    )
    return [parent_a, parent_b, tail]


def _mixed_events():
    """A v1 pair and a v2 chain on disjoint logical keys in one ledger."""
    return _pair_events() + _chain_events()


def _mint(events, *, clock=_MINT_CLOCK, packages=None):
    ledger = RawFactLedger(tuple(events))
    return mint_production_lineage_evidence(
        ledger,
        _packages(events) if packages is None else packages,
        system_available_at=clock,
    )


# ---------------------------------------------------------------------------
# Unit — clocks, refusals, determinism, scope
# ---------------------------------------------------------------------------


def test_naive_clock_refuses():
    with pytest.raises(LineageEvidenceError, match="timezone-aware"):
        _mint(_mixed_events(), clock=datetime(2026, 10, 14))


def test_clock_below_the_v1_floor_refuses_for_a_two_accession_key():
    # Floor: max(CONFIRMATION_RULE_AVAILABLE_AT 2026-08-25, recorded 2026-08-23).
    with pytest.raises(LineageEvidenceError, match="precedes the accepted lineage clock floor"):
        _mint(_pair_events(), clock=datetime(2026, 8, 24, tzinfo=timezone.utc))


def test_clock_below_the_chain_rule_clock_refuses_for_a_repeated_chain():
    with pytest.raises(LineageEvidenceError, match="precedes the accepted lineage clock floor"):
        _mint(_chain_events(), clock=_BELOW_CHAIN_CLOCK)


def test_clock_below_the_recorded_clock_floor_refuses_for_a_repeated_chain():
    # Capture recordings at 2026-10-13 lift the chain floor above the rule
    # clock: 2026-10-12 is above the rule clock yet still backdated.
    events = _chain_events(recorded_at="2026-10-13T00:00:00Z")
    with pytest.raises(LineageEvidenceError, match="precedes the accepted lineage clock floor"):
        _mint(events, clock=_BELOW_RECORDED_CLOCK)


def test_mint_is_deterministic_down_to_receipt_ids():
    first = _mint(_mixed_events())
    second = _mint(_mixed_events())
    assert first == second
    assert [r.receipt_id for r in first] == [r.receipt_id for r in second]
    assert [r.evidence_digest for r in first] == [r.evidence_digest for r in second]
    assert first  # the determinism claim is over a non-empty bundle


def test_co_mint_on_a_mixed_ledger():
    events = _mixed_events()
    receipts = _mint(events)
    pair_key = _pair_events()[0].logical_key
    chain_key = _chain_events()[0].logical_key
    assert pair_key != chain_key
    by_key: dict[str, list[int]] = {}
    for receipt in receipts:
        by_key.setdefault(receipt.logical_key, []).append(
            receipt.evidence_rule_version
        )
    # One v1 receipt for the pair, two adjacent v2 edges for the chain.
    assert by_key == {pair_key: [1], chain_key: [2, 2]}
    edges = sorted(
        (r.positive_evidence["parent_accession"], r.positive_evidence["child_accession"])
        for r in receipts
        if r.evidence_rule_version == 2
    )
    assert edges == [("0001", "0002"), ("0002", "0003")]


def test_a_two_accession_key_never_yields_a_v2_receipt():
    receipts = _mint(_pair_events())
    assert len(receipts) == 1
    assert receipts[0].evidence_rule_version == 1


@pytest.mark.parametrize(
    "label",
    ["revised", "contradictory", "rounded", "ambiguous"],
)
def test_non_repeated_chains_mint_nothing(label):
    if label == "revised":
        # A typed restatement of the middle filing: never a plain reprint.
        events = _chain_events(
            c_event_type=FactEventType.RESTATEMENT,
            c_revision_of_index=1,
        )
    elif label == "contradictory":
        events = _chain_events(c_value="400000000000")
    elif label == "rounded":
        # Equal values at different accuracy tokens: precision-consistent,
        # not exact — the A/B link refuses and the chain state degrades.
        events = _chain_events(a_decimals="-8")
    else:  # ambiguous: no strict acceptance order exists
        events = _chain_events(accepted=[_A_ACCEPTED, _A_ACCEPTED, _C_ACCEPTED])
    assert _mint(events) == ()


def test_empty_bundle_is_lawful():
    # A ledger whose facts have no taxonomy URI entries (no packages supplied)
    # mints nothing: guard 11 refuses the edges and the floors never bind.
    events = _mixed_events()
    ledger = RawFactLedger(tuple(events))
    assert mint_production_lineage_evidence(ledger, (), system_available_at=_MINT_CLOCK) == ()


def test_v1_subset_is_byte_identical_to_v1_called_alone():
    """Seat ruling (b): V1 IDENTITY — receipt ids included."""
    events = _mixed_events()
    ledger = RawFactLedger(tuple(events))
    packages = _packages(events)
    minted = mint_production_lineage_evidence(
        ledger, packages, system_available_at=_MINT_CLOCK
    )
    v1_alone = derive_confirmation_receipts(
        ledger.events,
        system_available_at=_MINT_CLOCK,
        original_taxonomy_uris=admitted_concept_namespace_uris(packages),
    )
    assert v1_alone  # the identity claim is over a non-empty v1 subset
    v1_subset = tuple(r for r in minted if r.evidence_rule_version == 1)
    assert v1_subset == v1_alone
    assert [r.receipt_id for r in v1_subset] == [r.receipt_id for r in v1_alone]


def test_rule_scopes_are_disjoint_and_each_key_carries_one_version():
    """Seat ruling (a): DISJOINTNESS on one mixed ledger."""
    events = _mixed_events()
    receipts = _mint(events)
    assert receipts
    v1_keys = {
        r.logical_key for r in receipts if r.evidence_rule_version == 1
    }
    v2_keys = {
        r.logical_key for r in receipts if r.evidence_rule_version == 2
    }
    assert v1_keys and v2_keys
    assert v1_keys.isdisjoint(v2_keys)
    versions_by_key: dict[str, set[int]] = {}
    for receipt in receipts:
        versions_by_key.setdefault(receipt.logical_key, set()).add(
            receipt.evidence_rule_version
        )
    assert all(len(versions) == 1 for versions in versions_by_key.values())


# ---------------------------------------------------------------------------
# Unit — the issuer-neutral taxonomy URI twin
# ---------------------------------------------------------------------------


def test_uri_twin_returns_the_golden_helpers_map_on_golden_packages():
    packages = [
        load_golden_aapl_package(ROOT, accession=accession)
        for accession in GOLDEN_AAPL_QUERY_ACCESSIONS
    ]
    golden = original_concept_namespace_uris(packages)
    assert golden  # 1991 entries on the committed two-filing golden set
    assert admitted_concept_namespace_uris(packages) == golden


def test_uri_twin_accepts_admitted_packages_and_stays_issuer_neutral():
    events = _chain_events()
    packages = _packages(events)
    golden_shape = admitted_concept_namespace_uris(packages)
    admitted = tuple(
        AdmittedFilingPackage(
            manifest=dict(package.manifest),
            members=dict(package.members),
            parse_evidence={},
        )
        for package in packages
    )
    # Duck-compatible admitted packages produce the identical map.
    assert admitted_concept_namespace_uris(admitted) == golden_shape
    assert golden_shape == {
        (event.source.accession, event.source_occurrence_key): _TAXONOMY_URI
        for event in events
    }


def test_uri_twin_refuses_an_unparseable_primary_with_neutral_wording():
    package = _package("0001", ["chain-a"])
    package.members[f"doc-0001.htm"] = b"<html><body>not a filing"  # unterminated XML
    with pytest.raises(ProductionLineageError) as excinfo:
        admitted_concept_namespace_uris([package])
    message = str(excinfo.value)
    assert "0001" in message
    assert "golden" not in message.lower()
    assert "aapl" not in message.lower()


def test_uri_twin_refuses_a_malformed_package():
    with pytest.raises(ProductionLineageError):
        admitted_concept_namespace_uris(
            [GoldenFilingPackage(manifest={"accession": "0001"}, members={})]
        )
    with pytest.raises(ProductionLineageError):
        admitted_concept_namespace_uris(
            [GoldenFilingPackage(manifest={}, members={})]
        )


def test_mint_refuses_an_unparseable_primary_through_the_twin():
    events = _chain_events()
    packages = list(_packages(events))
    packages[0].members["doc-0001.htm"] = b"garbage"
    with pytest.raises(ProductionLineageError):
        mint_production_lineage_evidence(
            RawFactLedger(tuple(events)),
            tuple(packages),
            system_available_at=_MINT_CLOCK,
        )


# ---------------------------------------------------------------------------
# Unit — the C0-b producer hook clock (CLOCK RULE)
# ---------------------------------------------------------------------------


def test_hook_clock_rule_pins_the_c0b_producer_clock():
    """C0-b §5 CLOCK RULE: the producer's clock is derived from CAPTURE
    recordings plus the rule clocks — never from the filings' acceptance
    times, which sit years below the rule floors."""
    events = _chain_events(
        accepted=["2024-02-15T16:00:00Z", "2024-11-15T16:00:00Z", "2025-02-15T16:00:00Z"],
        recorded_at="2026-10-13T00:00:00Z",  # captured after the chain rule clock
    )
    ledger = RawFactLedger(tuple(events))
    packages = _packages(events)

    hook_clock = max(
        [event.clocks.recorded_at for event in events]
        + [CONFIRMATION_RULE_AVAILABLE_AT, CONFIRMATION_CHAIN_RULE_AVAILABLE_AT]
    )
    assert hook_clock == datetime(2026, 10, 13, tzinfo=timezone.utc)

    receipts = mint_production_lineage_evidence(
        ledger, packages, system_available_at=hook_clock
    )
    assert len(receipts) == 2
    assert all(r.evidence_rule_version == 2 for r in receipts)
    assert all(r.system_available_at == hook_clock for r in receipts)

    # The trap: deriving the clock from the filings' ACCEPTANCE times instead
    # of their capture recordings is below the chain floor and refuses.
    acceptance_clock = max(event.clocks.accepted_at for event in events)
    assert acceptance_clock < CONFIRMATION_CHAIN_RULE_AVAILABLE_AT
    with pytest.raises(LineageEvidenceError, match="precedes the accepted lineage clock floor"):
        mint_production_lineage_evidence(
            ledger, packages, system_available_at=acceptance_clock
        )


# ---------------------------------------------------------------------------
# E2E — the production write side serves minted v2 receipts (census Q8)
# ---------------------------------------------------------------------------

_FIP1_ENTITY_ID = "mmx.issuer.fip1"
_ACC_23 = "0000999999-23-000010"
_ACC_24 = "0000999999-24-000010"
_ACC_25 = "0000999999-25-000010"

_E2E_MINT_CLOCK = datetime(2026, 10, 14, tzinfo=timezone.utc)
_E2E_EARLY_ADMITTED = datetime(2026, 10, 13, tzinfo=timezone.utc)
_E2E_RECORDED_AFTER = "2026-10-20T00:00:00Z"
_E2E_SOURCE_ALL = "2025-06-30T00:00:00Z"


def _fip1_chain_material(*, lineage=True, admitted_at=_E2E_MINT_CLOCK):
    """The committed FIP1 fixture plus two FILED comparative reprints of the
    FY2022 us-gaap:GrossProfit fact — one logical key across three accessions,
    exactly the production shape C0-b will admit."""
    fixture = load_filing_package_fixture(
        ROOT / "tests" / "fixtures" / "fundamental_forensics" / "filing_package_raw_ledger_v1.json"
    )
    events = list(fixture.ledger.events)
    # The engine keys filing metadata by OCCURRENCE id (query.py _filing_metadata),
    # so each synthetic reprint needs its own entry mirroring its accession's.
    filing_metadata = {
        key: dict(value) for key, value in fixture.filing_metadata.items()
    }
    meta_24 = next(v for v in filing_metadata.values() if v.get("accession") == _ACC_24)
    meta_25 = next(v for v in filing_metadata.values() if v.get("accession") == _ACC_25)

    orig = next(
        event
        for event in events
        if event.concept_qname == "us-gaap:GrossProfit"
        and event.source.accession == _ACC_23
        and str(event.context.start) == "2022-01-01"
    )
    reprint_24 = replace(
        orig,
        source=replace(
            orig.source,
            accession=_ACC_24,
            document_id="fip1-20231231.htm",
            body_sha256="e2179bd6330a94c3ebbe1a74e87f839d4c3c0d7646bc68650a26c1b05a438953",
            source_url=f"https://www.sec.gov/Archives/edgar/data/999999/{_ACC_24.replace('-', '')}/fip1-20231231.htm",
        ),
        clocks=replace(
            orig.clocks,
            accepted_at=datetime(2024, 2, 15, 16, 0, tzinfo=timezone.utc),
            recorded_at=datetime(2026, 10, 13, tzinfo=timezone.utc),
        ),
        source_occurrence_key="fy2022-gross-profit-comparative-2024",
        source_span=(20, 23),
        occurrence_id=None,
    )
    reprint_25 = replace(
        orig,
        source=replace(
            orig.source,
            accession=_ACC_25,
            document_id="fip1-20241231.htm",
            body_sha256="cc778004019a56e3168d07118c1087efe4cb38dceb4244c3c86941325e4f897d",
            source_url=f"https://www.sec.gov/Archives/edgar/data/999999/{_ACC_25.replace('-', '')}/fip1-20241231.htm",
        ),
        clocks=replace(
            orig.clocks,
            accepted_at=datetime(2025, 2, 15, 16, 0, tzinfo=timezone.utc),
            recorded_at=datetime(2026, 10, 13, tzinfo=timezone.utc),
        ),
        source_occurrence_key="fy2022-gross-profit-comparative-2025",
        source_span=(21, 24),
        occurrence_id=None,
    )
    extended = tuple(events) + (reprint_24, reprint_25)
    assert reprint_24.logical_key == orig.logical_key == reprint_25.logical_key
    assert len({event.occurrence_id for event in extended}) == len(extended)
    filing_metadata[reprint_24.occurrence_id] = dict(meta_24)
    filing_metadata[reprint_25.occurrence_id] = dict(meta_25)

    # One fabricated package per accession carrying the chain facts' source
    # occurrence keys; the mint derives its taxonomy URI map from these bytes.
    packages = (
        _package(_ACC_23, [orig.source_occurrence_key]),
        _package(_ACC_24, [reprint_24.source_occurrence_key]),
        _package(_ACC_25, [reprint_25.source_occurrence_key]),
    )
    ledger = RawFactLedger(extended)
    minted = mint_production_lineage_evidence(
        ledger, packages, system_available_at=_E2E_MINT_CLOCK
    )
    binding = CanonicalEntityBinding(
        entity_id=_FIP1_ENTITY_ID,
        cik="0000999999",
        ticker="FIP1",
        source_entity_id="0000999999",
    )
    material = PDS.ProductionDatasetMaterial(
        binding=binding,
        entity=EntityInput(
            entity_id=_FIP1_ENTITY_ID,
            cik="0000999999",
            ticker="FIP1",
            name="FIP1 Fixture",
            identity_basis="sec-cik",
            source_entity_id="0000999999",
        ),
        ledger=ledger,
        filing_metadata=filing_metadata,
        registry_payload=PDS.snapshot_core_registry_payload(ROOT),
        admitted_at=admitted_at,
        source_recorded_at_floor=datetime(2026, 8, 1, tzinfo=timezone.utc),
        lineage_evidence=minted if lineage else (),
    )
    return SimpleNamespace(
        material=material,
        minted=minted if lineage else (),
        packages=packages,
    )


def _publish(material):
    store = PDS.InMemoryStrictConditionalStore()
    publication = PDS.publish_production_dataset(store, material)
    return store, publication


def _request(
    *,
    selection="latest_known_as_of",
    recorded_at=_E2E_RECORDED_AFTER,
    source_snapshot_at=_E2E_SOURCE_ALL,
    period=("2022-01-01", "2022-12-31"),
):
    return json.dumps(
        {
            "schema": "fundamental_forensics.financial_query_request/v1",
            "entity_id": _FIP1_ENTITY_ID,
            "policy": {
                "selection": selection,
                "source_snapshot_at": source_snapshot_at,
                "recorded_at": recorded_at,
            },
            "metric_ids": ["gross_profit"],
            "periods": [
                {"kind": "duration", "start": period[0], "end": period[1], "label": "FY"}
            ],
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _confirmations(result):
    lineage = result.envelope.get("lineage")
    return lineage["confirmations"] if lineage else []


def _no_lookahead(result, recorded_at):
    recorded = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
    for confirmation in _confirmations(result):
        system_clock = datetime.fromisoformat(
            confirmation["system_available_at"].replace("Z", "+00:00")
        )
        assert system_clock <= recorded


@pytest.fixture(scope="module")
def e2e():
    built = _fip1_chain_material()
    store, publication = _publish(built.material)
    generation = PDS.load_latest_generation(store, _FIP1_ENTITY_ID)
    provider = ProductionFinancialQueryProvider(store)
    return SimpleNamespace(
        material=built.material,
        minted=built.minted,
        publication=publication,
        generation=generation,
        provider=provider,
    )


def test_e2e_mint_returns_exactly_the_two_adjacent_v2_edges(e2e):
    assert len(e2e.minted) == 2
    assert all(r.evidence_rule_version == 2 for r in e2e.minted)
    # The mint block is sorted by (logical_key, receipt_id), not chain order,
    # so compare the adjacent-edge set.
    edges = sorted(
        (r.positive_evidence["parent_accession"], r.positive_evidence["child_accession"])
        for r in e2e.minted
    )
    assert edges == sorted([(_ACC_23, _ACC_24), (_ACC_24, _ACC_25)])


def test_e2e_published_generation_round_trips_the_lineage_role(e2e):
    assert e2e.generation is not None
    assert e2e.generation.generation_id == e2e.publication.generation_id
    assert "lineage_evidence_json" in e2e.generation.role_payloads
    loaded = PDS.lineage_from_role_payload(
        e2e.generation.role_payloads["lineage_evidence_json"]
    )
    assert tuple(e2e.minted) == tuple(loaded)


def test_e2e_latest_known_serves_the_newest_edge_of_the_v2_chain(e2e):
    result = execute_financial_query(
        body=_request(selection="latest_known_as_of"),
        provider=e2e.provider,
        issuer_sic_resolver=_fip1_issuer_sic_resolver,
    )
    cell = result.envelope["receipt"]["nodes"][0]
    assert cell["state"] == "value"
    assert cell["value"] == "480"
    confirmations = _confirmations(result)
    assert confirmations
    assert all(c["evidence_rule_version"] == 2 for c in confirmations)
    # The selected root is the newest filing, so the disclosed edge ends there.
    for confirmation in confirmations:
        evidence = confirmation["positive_evidence"]
        assert evidence["child_accession"] == _ACC_25
        assert evidence["parent_accession"] == _ACC_24
    _no_lookahead(result, _E2E_RECORDED_AFTER)


def test_e2e_as_reported_serves_the_oldest_edge_of_the_v2_chain(e2e):
    result = execute_financial_query(
        body=_request(selection="as_reported"),
        provider=e2e.provider,
        issuer_sic_resolver=_fip1_issuer_sic_resolver,
    )
    cell = result.envelope["receipt"]["nodes"][0]
    assert cell["state"] == "value"
    assert cell["value"] == "480"
    confirmations = _confirmations(result)
    assert confirmations
    assert all(c["evidence_rule_version"] == 2 for c in confirmations)
    # The selected root is the earliest filed root, so the disclosed edge
    # starts there — the OTHER adjacent edge, not both rows at once.
    for confirmation in confirmations:
        evidence = confirmation["positive_evidence"]
        assert evidence["parent_accession"] == _ACC_23
        assert evidence["child_accession"] == _ACC_24
    _no_lookahead(result, _E2E_RECORDED_AFTER)


def test_e2e_query_hash_is_identical_with_and_without_lineage():
    """Lineage disclosure never enters the receipt, so a cell whose selection
    does not depend on the chain hashes identically whether the generation
    carries the minted bundle or not (query.py: never perturbs query_hash)."""
    with_lineage = _fip1_chain_material(lineage=True)
    without_lineage = _fip1_chain_material(lineage=False)
    assert with_lineage.minted and not without_lineage.minted
    store_with, _ = _publish(with_lineage.material)
    store_without, _ = _publish(without_lineage.material)
    # FY2024 GrossProfit lives in a single accession: its cell cannot depend
    # on cross-filing lineage, so any hash delta is lineage leaking into it.
    period = ("2024-01-01", "2024-12-31")
    result_with = execute_financial_query(
        body=_request(period=period),
        provider=ProductionFinancialQueryProvider(store_with),
        issuer_sic_resolver=_fip1_issuer_sic_resolver,
    )
    result_without = execute_financial_query(
        body=_request(period=period),
        provider=ProductionFinancialQueryProvider(store_without),
        issuer_sic_resolver=_fip1_issuer_sic_resolver,
    )
    cell_with = result_with.envelope["receipt"]["nodes"][0]
    cell_without = result_without.envelope["receipt"]["nodes"][0]
    assert cell_with["state"] == cell_without["state"] == "value"
    assert cell_with["value"] == cell_without["value"]
    assert (
        result_with.envelope["receipt"]["query_hash"]
        == result_without.envelope["receipt"]["query_hash"]
    )
    # Contrast: the FY2022 chain cell DOES change (lineage unifies vintages),
    # which is the evidence working — never the hash of an unchanged cell.
    chained = execute_financial_query(
        body=_request(),
        provider=ProductionFinancialQueryProvider(store_with),
        issuer_sic_resolver=_fip1_issuer_sic_resolver,
    )
    assert chained.envelope["receipt"]["nodes"][0]["state"] == "value"
    unchained = execute_financial_query(
        body=_request(),
        provider=ProductionFinancialQueryProvider(store_without),
        issuer_sic_resolver=_fip1_issuer_sic_resolver,
    )
    assert unchained.envelope["receipt"]["nodes"][0]["state"] == "not_evaluable"


def test_f10_regression_receipt_clock_after_generation_admission_yields_zero_lineage_rows():
    """F10 CLOSED "no defect" — the adversarial Q9(b) repro, pinned by name.

    A mis-published generation admitted BEFORE the receipts' own
    system_available_at clock can still be queried: the per-query receipt
    clock gate must refuse the receipts, leave ZERO lineage rows, and return
    the honest unlinked-vintage refusal instead of leaking lookahead."""
    built = _fip1_chain_material()
    early_material = replace(built.material, admitted_at=_E2E_EARLY_ADMITTED)
    assert all(
        receipt.system_available_at > _E2E_EARLY_ADMITTED for receipt in built.minted
    )
    store, _ = _publish(early_material)
    provider = ProductionFinancialQueryProvider(store)

    for selection in ("as_reported", "latest_known_as_of"):
        result = execute_financial_query(
            body=_request(
                selection=selection,
                recorded_at="2026-10-13T00:00:00Z",
                source_snapshot_at="2025-06-30T00:00:00Z",
            ),
            provider=provider,
            issuer_sic_resolver=_fip1_issuer_sic_resolver,
        )
        cell = result.envelope["receipt"]["nodes"][0]
        assert cell["state"] != "value"
        assert "unlinked source vintages" in (cell.get("reason") or "")
        assert _confirmations(result) == []
        _no_lookahead(result, "2026-10-13T00:00:00Z")


def test_q9_probes_keep_the_clock_law_on_the_production_path(e2e):
    """The remaining census Q9 arms: lawful visibility above the receipt
    clock, a source-side cutoff narrowing the visible chain, and the dataset
    admission floor refusing a pre-admission recorded_at outright."""
    # (a) Lawful visibility: recorded_at above the receipt clock serves rows.
    lawful = execute_financial_query(
        body=_request(
            selection="as_reported",
            recorded_at=_E2E_RECORDED_AFTER,
            source_snapshot_at=_E2E_SOURCE_ALL,
        ),
        provider=e2e.provider,
        issuer_sic_resolver=_fip1_issuer_sic_resolver,
    )
    assert lawful.envelope["receipt"]["nodes"][0]["state"] == "value"
    assert _confirmations(lawful)
    _no_lookahead(lawful, _E2E_RECORDED_AFTER)

    # (c) Source-side as-of: a snapshot before the child filing's acceptance
    # narrows the visible chain; whatever still serves stays clock-lawful.
    narrowed = execute_financial_query(
        body=_request(
            selection="as_reported",
            recorded_at=_E2E_RECORDED_AFTER,
            source_snapshot_at="2024-06-30T00:00:00Z",
        ),
        provider=e2e.provider,
    )
    for confirmation in _confirmations(narrowed):
        assert confirmation["positive_evidence"]["child_accession"] != _ACC_25
    _no_lookahead(narrowed, _E2E_RECORDED_AFTER)

    # (c2) recorded_at below the generation's admission clock: refused BEFORE
    # the query — no response, no lineage.
    with pytest.raises(FinancialQueryUnavailableError):
        execute_financial_query(
            body=_request(recorded_at="2026-09-01T00:00:00Z"),
            provider=e2e.provider,
        )
