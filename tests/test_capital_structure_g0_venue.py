"""SPEC_G0 Rev 2.2 §2 + §5 row G0-E — the listing fact, venue binding in
capacity, rule-pack selection and the Nasdaq 5615(a)(3) FPI rule.

Every fixture is built in code from explicit records: no ticker, no company
name and no real CIK anywhere (the issuer id is the synthetic ``cik:0001234567``
the component suites already use).  Arithmetic is exact; there is no score,
rank, sizing, probability or recommendation, and no network.  The case files of
lane G0-S are never opened: everything here is derived from the rules and the
qualified packs on this branch.
"""
from __future__ import annotations

import ast
import json
import re
from dataclasses import replace as dataclasses_replace
from pathlib import Path
from typing import Any

import pytest

import tests.test_capital_structure_capacity as C1
import tests.test_capital_structure_capacity_c2 as C2
import tests.test_capital_structure_funding as F
import tests.test_capital_structure_scenario_composition as S0
import tests.test_capital_structure_scenario_inputs as U1B
import tests.test_capital_structure_supply_scenarios as SS
import tests.test_capital_structure_transactions as X0
from engine.capital_structure import capacity as capacity_module
from engine.capital_structure import issuer_state_contracts as ic
from engine.capital_structure import reference_qualification as rq
from engine.capital_structure import rule_applicability as ra
from engine.capital_structure import scenario_composition as sc
from engine.capital_structure import scenario_inputs as si
from engine.capital_structure.issuer_state_contracts import EvidenceRef
from engine.capital_structure.listing_facts import (
    ListingFact,
    build_listing_fact,
    listing_fact_from_record,
)

REPO = Path(__file__).resolve().parents[1]
PACK_PATH = REPO / "config" / "capital_structure_rule_applicability_pack.v1.json"
E0_PATH = REPO / "config" / "capital_structure_reference_pack.v1.json"

SALE = C1.SALE
AS_OF = C1.AS_OF
NASDAQ_POOL = C1.NASDAQ_POOL
ISSUER = C1.ISSUER
PATH_A = C1.PATH_A
#: The 5615(a)(3) window the seat qualified: verified on and between these days.
WINDOW_START = "2025-11-24"
WINDOW_END = "2026-10-19"

MANIFEST = C1.MANIFEST
ITEM_16G_REF = EvidenceRef(MANIFEST, "span:item-16g", "3" * 64)
SUBMISSIONS_REF = EvidenceRef(MANIFEST, "span:submissions-exchanges", "4" * 64)
ANNUAL_FORM_REF = EvidenceRef(MANIFEST, "span:annual-report-form", "5" * 64)

#: The two shelves one standard world carries.
TWO_SHELVES = dict(
    registration=(
        C1.standard_registration()[0]
        + C1.standard_registration(path_id=C1.PATH_B, accession=C1.ACC_B, float_value=None, outstanding=None)[0]
    ),
    share_basis=C1.standard_registration()[1],
    resolutions=[
        C1.usd(f"shelf_usage:{C1.PATH_A}", "0"),
        C1.usd(f"continuing_offering:{C1.PATH_A}", "0"),
        C1.usd(f"shelf_usage:{C1.PATH_B}", "0"),
        C1.usd(f"continuing_offering:{C1.PATH_B}", "0"),
        C1.usd(f"baby_shelf_sold_trailing:{SALE}", "0"),
    ],
)


# ---------------------------------------------------------------------------
# Listing-fact fixtures (explicit records; no served producer exists: GAP
# served_listing_producer_owed)
# ---------------------------------------------------------------------------


def build(**kwargs: Any) -> ListingFact:
    base: dict[str, Any] = dict(
        exchanges=None,
        filings=(),
        item_16g=None,
        as_of=SALE,
        available_at=AS_OF,
        evidence=(),
    )
    base.update(kwargs)
    return build_listing_fact(**base)


def observed_nasdaq(**kwargs: Any) -> ListingFact:
    """FPI True, 5635 home-country practice elected, listed on nasdaq."""
    merged: dict[str, Any] = dict(
        exchanges=["Nasdaq"],
        filings=({"form": "20-F", "filed": C1.shift(SALE, 120)}, {"form": "F-3", "filed": C1.shift(SALE, 100)}),
        item_16g={
            "text": "Item 16G. The Company follows home country practice in lieu of "
            "Rule 5635 of the Nasdaq Listing Rules.",
            "complete": True,
            "filed": C1.shift(SALE, 100),
        },
        evidence=(ITEM_16G_REF, SUBMISSIONS_REF, ANNUAL_FORM_REF),
    )
    merged.update(kwargs)
    return build(**merged)


def observed_nasdaq_at(day: str) -> ListingFact:
    """``observed_nasdaq`` evaluated on ``day``, with its filings dated before ``day``.

    The builder ignores filings after its ``as_of`` (no look-ahead), so a fixture
    for another sale date must carry filings that were public by then.
    """
    return observed_nasdaq(
        as_of=day,
        available_at=f"{day}T00:00:00Z",
        filings=({"form": "20-F", "filed": C1.shift(day, 120)}, {"form": "F-3", "filed": C1.shift(day, 100)}),
        item_16g={
            "text": "Item 16G. The Company follows home country practice in lieu of "
            "Rule 5635 of the Nasdaq Listing Rules.",
            "complete": True,
            "filed": C1.shift(day, 100),
        },
    )


def domestic_nasdaq(**kwargs: Any) -> ListingFact:
    """A domestic issuer on nasdaq: the venue binds, the 5615 branch never fires."""
    merged: dict[str, Any] = dict(
        exchanges=["Nasdaq"],
        filings=({"form": "10-K", "filed": C1.shift(SALE, 120)},),
    )
    merged.update(kwargs)
    return build(**merged)


def _canonical(evaluation: Any) -> str:
    return json.dumps(
        {
            "envelope": evaluation.envelope.as_record(),
            "inputs": ic._record(evaluation.inputs),
            "kernel": evaluation.kernel,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _run(**kwargs: Any):
    """C1's build + explain, with the additive listing keyword and validation."""
    listing = kwargs.pop("listing", None)
    transactions = kwargs.pop("transactions", None)
    state, scenario, rules = C1.build(**kwargs)
    evaluation = capacity_module.explain_capacity(
        state, scenario, rules, pack=C1.PACK, transactions=transactions, listing=listing
    )
    record = evaluation.envelope.as_record()
    ic.validate_state_record("capacity_envelope", record)
    return evaluation


def _routes(evaluation: Any) -> dict[str, Any]:
    return {route.route_id: route for route in evaluation.envelope.routes}


def _pools(evaluation: Any) -> dict[str, Any]:
    return {pool.constraint_id: pool for pool in evaluation.envelope.shared_pools}


def _unknown_ids(evaluation: Any) -> set[str]:
    return {item.unknown_id for item in evaluation.envelope.unknowns}


def _consulted_rules(evaluation: Any) -> set[str]:
    rules: set[str] = set()
    for path in evaluation.inputs["registration_paths"]:
        rules.update(path["consulted_rules"])
    return rules


def _assumptions_only_world(**kwargs: Any):
    return _two_shelf_run(**kwargs)


def _two_shelf_run(**kwargs: Any):
    """The two-shelf world with the A14 assumptions unless the test overrides them."""
    kwargs.setdefault("other", C1.NASDAQ_ASSUMPTIONS)
    return _run(**TWO_SHELVES, **kwargs)


# ---------------------------------------------------------------------------
# §2.1 the record and the builder
# ---------------------------------------------------------------------------


def test_g0e_listing_fact_record_round_trip() -> None:
    fact = observed_nasdaq()
    record = fact.as_record()
    assert listing_fact_from_record(record) == fact
    assert json.dumps(record, sort_keys=True) == json.dumps(
        listing_fact_from_record(record).as_record(), sort_keys=True
    )
    with pytest.raises(Exception):
        listing_fact_from_record(dict(record, issuer_note="x"))
    with pytest.raises(Exception):
        listing_fact_from_record({key: value for key, value in record.items() if key != "reasons"})
    with pytest.raises(Exception):
        listing_fact_from_record(dict(record, venue="lse"))
    with pytest.raises(Exception):
        listing_fact_from_record(dict(record, foreign_private_issuer="maybe"))
    # An unknown axis without its reason is refused.
    with pytest.raises(Exception):
        ListingFact(
            venue="unknown",
            foreign_private_issuer=True,
            home_country_practice_5635="elected",
            reasons=(),
            evidence=(),
            available_at=AS_OF,
            as_of=SALE,
        )
    with pytest.raises(Exception):
        ListingFact(
            venue="nasdaq",
            foreign_private_issuer="unknown",
            home_country_practice_5635="elected",
            reasons=(),
            evidence=(),
            available_at=AS_OF,
            as_of=SALE,
        )


def test_g0e_builder_venue_rules() -> None:
    assert build(exchanges=["Nasdaq"]).venue == "nasdaq"
    assert build(exchanges=[" nasdaq "]).venue == "nasdaq"
    assert build(exchanges=["NYSE"]).venue == "nyse"
    assert build(exchanges=["NYSE American"]).venue == "nyse_american"
    assert build(exchanges=["NYSE MKT"]).venue == "nyse_american"
    assert build(exchanges=["OTC"]).venue == "otc"
    missing = build(exchanges=None)
    assert missing.venue == "unknown"
    assert "listing_exchanges_missing" in missing.reasons
    assert build(exchanges=[]).reasons == missing.reasons
    unmapped = build(exchanges=["LSE"])
    assert unmapped.venue == "unknown" and "listing_exchange_unmapped" in unmapped.reasons
    disagree = build(exchanges=["Nasdaq", "NYSE"])
    assert disagree.venue == "unknown" and "listing_exchanges_disagree" in disagree.reasons
    # Repeated names of one venue are one distinct venue, and the builder never
    # emits the reserved `none`.
    assert build(exchanges=["NYSE", "NYSE", "NYSE"]).venue == "nyse"
    for exchanges in ([], None, ["Nasdaq"], ["Nasdaq", "NYSE"], ["LSE"]):
        assert build(exchanges=exchanges).venue != "none"


def test_g0e_builder_fpi_rules() -> None:
    def fpi_of(*forms: str) -> bool | str:
        filings = tuple({"form": form, "filed": C1.shift(SALE, 30)} for form in forms)
        return build(filings=filings).foreign_private_issuer

    assert fpi_of("20-F") is True
    assert fpi_of("40-F") is True
    assert fpi_of("10-K") is False
    mixed_fpi = build(filings=({"form": "20-F", "filed": C1.shift(SALE, 30)}, {"form": "S-3", "filed": C1.shift(SALE, 40)}))
    assert "fpi_forms_disagree" in mixed_fpi.reasons
    mixed_domestic = build(filings=({"form": "10-K", "filed": C1.shift(SALE, 30)}, {"form": "F-3", "filed": C1.shift(SALE, 40)}))
    assert "fpi_forms_disagree" in mixed_domestic.reasons
    absent = build(filings=({"form": "S-8", "filed": C1.shift(SALE, 30)},))
    assert absent.foreign_private_issuer == "unknown" and "fpi_forms_absent" in absent.reasons
    assert "fpi_forms_absent" in build(filings=()).reasons
    # A trailing /A counts as its base form; S-8 is ignored beside a 20-F.
    assert fpi_of("20-F/A") is True
    assert fpi_of("20-F", "S-8") is True
    # A filing after `as_of` and a filing older than 24 months are ignored.
    assert build(filings=({"form": "20-F", "filed": C1.shift(SALE, -1)},)).foreign_private_issuer == "unknown"
    assert build(filings=({"form": "10-K", "filed": "2020-01-01"},)).foreign_private_issuer == "unknown"


def test_g0e_builder_home_country_practice_rules() -> None:
    def practice(filings: Any, disclosure: Any) -> str:
        return build(filings=filings, item_16g=disclosure).home_country_practice_5635

    domestic = ({"form": "10-K", "filed": C1.shift(SALE, 30)},)
    assert practice(domestic, None) == "not_elected"
    fpi_unknown = ({"form": "S-8", "filed": C1.shift(SALE, 30)},)
    got = build(filings=fpi_unknown, item_16g={"text": "names 5635", "complete": True, "filed": C1.shift(SALE, 30)})
    assert got.home_country_practice_5635 == "unknown"
    assert "home_country_practice_fpi_unknown" in got.reasons
    fpi_world = ({"form": "20-F", "filed": C1.shift(SALE, 30)},)
    assert practice(fpi_world, None) == "unknown"
    late = build(filings=fpi_world, item_16g={
        "text": "names Rule 5635 and home country practice", "complete": True, "filed": C1.shift(SALE, -1),
    })
    assert "item_16g_missing" in late.reasons
    elected = build(filings=fpi_world, item_16g={
        "text": "Item 16G. The Company follows home-country practice in lieu of Rule 5635.",
        "complete": True,
        "filed": C1.shift(SALE, 10),
    })
    assert elected.home_country_practice_5635 == "elected"
    nbsp = build(filings=fpi_world, item_16g={
        "text": "Item 16G. The Company follows home country practice in lieu of Rule 5635.",
        "complete": True,
        "filed": C1.shift(SALE, 10),
    })
    assert nbsp.home_country_practice_5635 == "elected"
    complete_without_rule = build(filings=fpi_world, item_16g={
        "text": "Item 16G. There is no difference between the Company's home country practice and the requirements.",
        "complete": True,
        "filed": C1.shift(SALE, 10),
    })
    assert complete_without_rule.home_country_practice_5635 == "not_elected"
    incomplete = build(filings=fpi_world, item_16g={
        "text": "Item 16G. The disclosure continues in the next exhibit.",
        "complete": False,
        "filed": C1.shift(SALE, 10),
    })
    assert incomplete.home_country_practice_5635 == "unknown"
    assert "item_16g_inconclusive" in incomplete.reasons


def test_g0e_item_16g_reads_each_clause() -> None:
    fpi_world = ({"form": "20-F", "filed": C1.shift(SALE, 30)},)

    def read(text: str, complete: bool = True) -> ListingFact:
        return build(filings=fpi_world, item_16g={"text": text, "complete": complete, "filed": C1.shift(SALE, 10)})

    # Home country practice for another sub-paragraph is no 5635(d) election.
    other = read("Item 16G. We follow home country practice in lieu of Rule 5635(c); we comply with Rule 5635(d).")
    assert other.home_country_practice_5635 == "not_elected"
    # A negated practice clause beside a compliance statement elects nothing.
    complying = "We do not follow home country practice; we comply with Nasdaq Rule 5635 in full."
    assert read(complying).home_country_practice_5635 == "not_elected"
    partial = read(complying, complete=False)
    assert partial.home_country_practice_5635 == "unknown"
    assert "item_16g_inconclusive" in partial.reasons
    # 5635(d) by sub-paragraph elects like the whole rule.
    by_letter = read("We follow home country practice in lieu of Nasdaq Rule 5635(d).")
    assert by_letter.home_country_practice_5635 == "elected"
    # A negated clause that names 5635(d) is inconclusive, never an election.
    negated = read("We do not follow home country practice in lieu of Rule 5635(d).")
    assert negated.home_country_practice_5635 == "unknown"
    assert "item_16g_inconclusive" in negated.reasons
    # Practice in one sentence and the rule in another are not joined.
    split = read("We follow home country practice for shareholder approvals. See Nasdaq Rule 5635.")
    assert split.home_country_practice_5635 == "unknown"
    assert "item_16g_inconclusive" in split.reasons
    # An election in an incomplete disclosure is inconclusive.
    cut = read("We follow home country practice in lieu of Rule 5635.", complete=False)
    assert cut.home_country_practice_5635 == "unknown"
    assert "item_16g_inconclusive" in cut.reasons
    # A non-breaking hyphen normalizes like a hyphen.
    assert read("We follow home\u2011country practice in lieu of Rule 5635.").home_country_practice_5635 == "elected"


def test_g0e_item_16g_older_than_the_fpi_window_is_missing() -> None:
    fpi_world = ({"form": "20-F", "filed": C1.shift(SALE, 30)},)
    text = "Item 16G. The Company follows home country practice in lieu of Rule 5635."
    # The window is the FPI determination's: 24 calendar months ending on as_of.
    stale = build(filings=fpi_world, item_16g={"text": text, "complete": True, "filed": "2024-10-13"})
    assert stale.home_country_practice_5635 == "unknown"
    assert "item_16g_missing" in stale.reasons
    first_day = build(filings=fpi_world, item_16g={"text": text, "complete": True, "filed": "2024-10-14"})
    assert first_day.home_country_practice_5635 == "elected"


def test_g0e_listing_fact_refuses_a_day_after_its_availability() -> None:
    with pytest.raises(ic.ContractViolation, match="precedes the day it describes"):
        build(as_of=C1.shift(SALE, -1), available_at=f"{C1.shift(SALE, 1)}T00:00:00Z")
    # Available on the day it describes, or later, is admissible.
    assert build(as_of=SALE, available_at=f"{SALE}T00:00:00Z").as_of == SALE
    assert build(as_of=C1.shift(SALE, 1), available_at=AS_OF).as_of == C1.shift(SALE, 1)


def test_g0e_builder_validates_available_at() -> None:
    with pytest.raises(Exception):
        build(available_at="2026-10-14 00:00:00")
    with pytest.raises(Exception):
        build(available_at="2026-10-14T05:00:00+05:00")
    with pytest.raises(Exception):
        build(available_at=None)
    with pytest.raises(Exception):
        ListingFact(
            venue="nasdaq",
            foreign_private_issuer=True,
            home_country_practice_5635="elected",
            reasons=(),
            evidence=(),
            available_at=AS_OF,
            as_of="not-a-date",
        )
    assert build(available_at="2026-10-14T00:00:00Z").available_at == "2026-10-14T00:00:00Z"


# ---------------------------------------------------------------------------
# §2.2 venue binding in capacity
# ---------------------------------------------------------------------------


def test_g0e_listing_none_is_byte_identical() -> None:
    s3 = C1.standard_registration()
    f3 = C1.standard_registration(form="F-3", family="registration_f3")
    reg, shares = C1.standard_registration()
    ledger = X0.reconcile(
        issuer_id=ISSUER,
        as_of=AS_OF,
        observations=(X0.observation(
            kind="registered_takedown", basis="individual", event_date=C1.shift(SALE, 5),
            gross="1000000", form="424B5", accepted=C1.shift(SALE, 5), issuer_id=ISSUER,
        ),),
        bindings=(),
        filing_coverage=(),
        registration_paths=(X0.shelf_path_record(PATH_A, "000-00000", C1.shift(SALE, 30), ISSUER),),
    )
    worlds = {
        "s3_baby_shelf": dict(registration=s3[0], share_basis=s3[1], other=C1.NASDAQ_ASSUMPTIONS),
        "f3_shelf": dict(registration=f3[0], share_basis=f3[1], other=C1.NASDAQ_ASSUMPTIONS),
        "with_transactions": dict(
            registration=reg, share_basis=shares, other=C1.NASDAQ_ASSUMPTIONS, transactions=ledger
        ),
    }
    plain = {name: _run(**kwargs) for name, kwargs in worlds.items()}
    explicit = {name: _run(**kwargs, listing=None) for name, kwargs in worlds.items()}
    for name in worlds:
        assert _canonical(plain[name]) == _canonical(explicit[name]), name
        assert not any(key.startswith("listing") for key in plain[name].inputs), name
        nasdaq = plain[name].inputs["nasdaq"]
        if isinstance(nasdaq, dict):
            assert not any(key.startswith("listing") for key in nasdaq), name
    # The third fixture really carries the C2x ledger, so its byte identity is
    # proven on the additive-keyword shape too.
    assert "transaction_ledger" in plain["with_transactions"].inputs
    assert plain["with_transactions"].inputs["transaction_ledger"]["input_digest"] == ledger.receipt.input_digest


def test_g0e_observed_venue_with_assumption_absent() -> None:
    evaluation = _run(
        registration=C1.standard_registration()[0],
        share_basis=C1.standard_registration()[1],
        other=tuple(key_value for key_value in C1.NASDAQ_ASSUMPTIONS if key_value[0] != "listing_venue"),
        listing=domestic_nasdaq(),
    )
    assert NASDAQ_POOL in _pools(evaluation)
    assert evaluation.inputs["nasdaq"]["listing_venue_basis"] == "observed"
    assert evaluation.inputs["listing"] == domestic_nasdaq().as_record()


def test_g0e_observed_venue_equal_to_assumption() -> None:
    assumed = _two_shelf_run()
    observed = _two_shelf_run(listing=domestic_nasdaq())
    assert _pools(assumed)[NASDAQ_POOL].bound.as_record() == _pools(observed)[NASDAQ_POOL].bound.as_record()
    assert assumed.inputs["nasdaq"]["largest_issuance_below_threshold"] == (
        observed.inputs["nasdaq"]["largest_issuance_below_threshold"]
    )
    assert observed.inputs["nasdaq"]["listing_venue_basis"] == "observed"


def test_g0e_venue_conflict() -> None:
    evaluation = _run(
        registration=C1.standard_registration()[0],
        share_basis=C1.standard_registration()[1],
        other=C1.NASDAQ_ASSUMPTIONS,
        listing=observed_nasdaq(exchanges=["NYSE"]),
    )
    conflicts = {uid for uid in _unknown_ids(evaluation) if uid.startswith("listing_venue_conflict:")}
    assert conflicts
    for route_id, route in _routes(evaluation).items():
        if route.status in capacity_module.ACTIVE_ROUTE_STATUSES:
            assert f"listing_venue_conflict:{route_id}" in conflicts
            assert "listing_venue_conflict" in route.conditions
            assert route.status != "eligible"
    assert NASDAQ_POOL not in _pools(evaluation)
    assert evaluation.inputs["nasdaq"]["reason"] == "listing_venue_conflict"
    # Conflict wins over unqualified: the same facts never produce the
    # unqualified unknown instead.
    assert not any(uid.startswith("venue_rule_pack_unqualified") for uid in _unknown_ids(evaluation))


def test_g0e_venue_unqualified() -> None:
    two = dict(registration=C1.standard_registration()[0], share_basis=C1.standard_registration()[1])
    for exchange, venue in (("NYSE", "nyse"), ("NYSE American", "nyse_american"), ("OTC", "otc")):
        evaluation = _run(
            **two,
            other=tuple(key_value for key_value in C1.NASDAQ_ASSUMPTIONS if key_value[0] != "listing_venue"),
            listing=observed_nasdaq(exchanges=[exchange]),
        )
        assert any(uid.startswith(f"venue_rule_pack_unqualified:{venue}:") for uid in _unknown_ids(evaluation)), venue
        for route in _routes(evaluation).values():
            assert route.status != "eligible"
            if route.status in capacity_module.ACTIVE_ROUTE_STATUSES:
                assert f"venue_rule_pack_unqualified:{venue}" in route.conditions
        assert "no_active_route" not in evaluation.envelope.blockers
        assert NASDAQ_POOL not in _pools(evaluation)
    # A `none` venue is unqualified exactly like the named exchanges.  The
    # builder never emits `none`, so the reserved value is constructed directly.
    reserved = ListingFact(
        venue="none",
        foreign_private_issuer=True,
        home_country_practice_5635="elected",
        reasons=(),
        evidence=(ITEM_16G_REF,),
        available_at=AS_OF,
        as_of=SALE,
    )
    evaluation = _run(
        **two,
        other=tuple(key_value for key_value in C1.NASDAQ_ASSUMPTIONS if key_value[0] != "listing_venue"),
        listing=reserved,
    )
    assert any(uid.startswith("venue_rule_pack_unqualified:none:") for uid in _unknown_ids(evaluation))
    assert NASDAQ_POOL not in _pools(evaluation)


def test_g0e_venue_unknown_keeps_the_assumption_branch() -> None:
    assumed = _two_shelf_run()
    unknown_venue = _two_shelf_run(listing=build())
    assert _pools(unknown_venue)[NASDAQ_POOL].bound.as_record() == _pools(assumed)[NASDAQ_POOL].bound.as_record()
    assert unknown_venue.inputs["nasdaq"]["listing_venue_basis"] == "assumption"


def test_g0e_listing_after_as_of_is_ignored() -> None:
    kwargs = dict(
        registration=C1.standard_registration()[0],
        share_basis=C1.standard_registration()[1],
        other=C1.NASDAQ_ASSUMPTIONS,
    )
    plain = _run(**kwargs)
    late = _run(**kwargs, listing=observed_nasdaq(available_at=f"{C1.shift(SALE, -1)}T00:00:00Z"))
    got = json.loads(_canonical(late))
    expected = json.loads(_canonical(plain))
    assert got["inputs"]["listing_excluded_after_as_of"] is True
    got["inputs"].pop("listing_excluded_after_as_of")
    # The receipt digests the inputs, which record the exclusion (SPEC_G0 §2.2),
    # so only its input digest and the id derived from it may move.
    got_receipt = got["envelope"].pop("receipt")
    expected_receipt = expected["envelope"].pop("receipt")
    for key in ("input_digest", "receipt_id"):
        assert got_receipt.pop(key) != expected_receipt.pop(key)
    assert got_receipt == expected_receipt
    assert got == expected


def test_g0e_other_assumption_keys_still_required() -> None:
    evaluation = _run(
        registration=C1.standard_registration()[0],
        share_basis=C1.standard_registration()[1],
        other=(("price_relative_to_minimum_price", "below"),),
        listing=observed_nasdaq(),
    )
    assert f"nasdaq_offering_treatment:shelf_takedown:{PATH_A}" in _unknown_ids(evaluation)
    assert NASDAQ_POOL not in _pools(evaluation)


def test_g0e_existing_conditions_are_never_removed() -> None:
    kwargs = dict(
        registration=C1.standard_registration()[0],
        share_basis=C1.standard_registration()[1],
        other=C1.NASDAQ_ASSUMPTIONS,
    )
    plain = _run(**kwargs)
    observed = _run(**kwargs, listing=observed_nasdaq())
    for route_id, route in _routes(plain).items():
        observed_conditions = set(_routes(observed)[route_id].conditions)
        assert set(route.conditions) <= observed_conditions
        assert "issuer_facts_not_verified:exchange_listed_common_equity" in observed_conditions


# ---------------------------------------------------------------------------
# §2.3 the 5615(a)(3) exemption and its window
# ---------------------------------------------------------------------------


def test_g0e_fpi_elected_with_5615_verified_exempts_the_pool() -> None:
    assert WINDOW_START <= SALE <= WINDOW_END
    evaluation = _two_shelf_run(listing=observed_nasdaq())
    assert NASDAQ_POOL not in _pools(evaluation)
    nasdaq = evaluation.inputs["nasdaq"]
    assert nasdaq["pool"] is None
    assert nasdaq["reason"] == "home_country_practice_elected"
    assert nasdaq["rule_id"] == "nasdaq.5615.a.3"
    assert nasdaq["rule_state"] == "verified"
    assert nasdaq["evidence"] == [
        ITEM_16G_REF.as_record(), SUBMISSIONS_REF.as_record(), ANNUAL_FORM_REF.as_record(),
    ]
    assert "nasdaq.5615.a.3" in _consulted_rules(evaluation)


def test_g0e_fpi_election_unknown_is_conditional() -> None:
    unelected = build(
        exchanges=["Nasdaq"],
        filings=({"form": "20-F", "filed": C1.shift(SALE, 120)},),
        item_16g=None,
    )
    evaluation = _two_shelf_run(listing=unelected)
    pools = _pools(evaluation)
    assert NASDAQ_POOL in pools
    for route_id in pools[NASDAQ_POOL].shared_by:
        route = _routes(evaluation)[route_id]
        assert "nasdaq_5635_applies_unless_home_country_practice_elected" in route.conditions
        assert route.status != "eligible"
    assert evaluation.inputs["nasdaq"]["home_country_practice_5635"] == "unknown"


def test_g0e_listing_describing_a_later_day_is_ignored() -> None:
    kwargs = dict(
        registration=C1.standard_registration()[0],
        share_basis=C1.standard_registration()[1],
        other=C1.NASDAQ_ASSUMPTIONS,
    )
    plain = _run(**kwargs)
    later = observed_nasdaq()
    # A record that bypassed the constructor can still describe a day after the
    # cutoff while claiming an availability on or before it; capacity excludes
    # it on its own.
    object.__setattr__(later, "as_of", C1.shift(SALE, -1))
    evaluation = _run(**kwargs, listing=later)
    assert evaluation.inputs["listing_excluded_after_as_of"] is True
    assert _pools(evaluation).keys() == _pools(plain).keys()
    assert {rid: r.status for rid, r in _routes(evaluation).items()} == {
        rid: r.status for rid, r in _routes(plain).items()
    }


def test_g0e_election_without_evidence_keeps_the_pool() -> None:
    evaluation = _two_shelf_run(listing=observed_nasdaq(evidence=()))
    pools = _pools(evaluation)
    assert NASDAQ_POOL in pools
    for route_id in pools[NASDAQ_POOL].shared_by:
        route = _routes(evaluation)[route_id]
        assert "nasdaq_5635_applies_unless_home_country_practice_evidenced" in route.conditions
        assert route.status != "eligible"
    assert evaluation.inputs["nasdaq"].get("reason") != "home_country_practice_elected"
    assert "nasdaq.5615.a.3" not in _consulted_rules(evaluation)


def _run_at(sale: str, listing: ListingFact, pack: Any = C1.PACK):
    reg, shares = C1.standard_registration(sale=sale)
    rules = ra.build_rule_pack(pack, sale)[0]
    assert rules is not None, f"no qualified rule text on {sale}"
    state, scenario, built = C1.build(
        sale=sale, registration=reg, share_basis=shares, other=C1.NASDAQ_ASSUMPTIONS, rules=rules
    )
    return capacity_module.explain_capacity(state, scenario, built, pack=pack, listing=listing)


def test_g0e_5615_outside_its_window_gives_no_exemption() -> None:
    # The 20% pool id is keyed to the sale date it is evaluated on.
    beyond = _run_at("2026-10-20", observed_nasdaq_at("2026-10-20"))
    assert beyond.inputs["nasdaq"]["fpi"] is True
    assert "nasdaq_20pct:2026-10-20" in _pools(beyond)
    for route in _routes(beyond).values():
        if route.status in capacity_module.ACTIVE_ROUTE_STATUSES:
            assert "nasdaq_5615_a_3_beyond_window_at_sale_date" in route.conditions
    withheld = _run_at("2025-11-23", observed_nasdaq_at("2025-11-23"))
    assert withheld.inputs["nasdaq"]["fpi"] is True
    assert "nasdaq_20pct:2025-11-23" in _pools(withheld)
    for route in _routes(withheld).values():
        if route.status in capacity_module.ACTIVE_ROUTE_STATUSES:
            assert "nasdaq_5615_a_3_withheld_at_sale_date" in route.conditions
    raw = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    raw["rules"] = [rule for rule in raw["rules"] if rule["rule_id"] != "nasdaq.5615.a.3"]
    pack_without = ra.parse_rule_applicability_pack(raw)
    absent = _run_at(SALE, observed_nasdaq(), pack=pack_without)
    assert NASDAQ_POOL in _pools(absent)
    for route in _routes(absent).values():
        if route.status in capacity_module.ACTIVE_ROUTE_STATUSES:
            assert "nasdaq_5615_a_3_absent_at_sale_date" in route.conditions


def test_g0e_fpi_false_is_unchanged() -> None:
    domestic = build(
        exchanges=["Nasdaq"],
        filings=({"form": "10-K", "filed": C1.shift(SALE, 100)},),
        item_16g=None,
    )
    assumed = _two_shelf_run()
    domestic_run = _two_shelf_run(listing=domestic)
    # A supplied listing adds exactly these digest keys (SPEC_G0 §2.2); the answer itself is unchanged.
    listing_keys = {"listing_venue_basis", "listing_venue", "fpi", "home_country_practice_5635"}
    assert listing_keys <= set(domestic_run.inputs["nasdaq"])
    assert not listing_keys & set(assumed.inputs["nasdaq"])
    plain_nasdaq = {key: value for key, value in assumed.inputs["nasdaq"].items() if key not in listing_keys}
    domestic_nasdaq = {key: value for key, value in domestic_run.inputs["nasdaq"].items() if key not in listing_keys}
    assert plain_nasdaq == domestic_nasdaq
    assert _pools(assumed)[NASDAQ_POOL].bound.as_record() == _pools(domestic_run)[NASDAQ_POOL].bound.as_record()
    assert domestic_run.inputs["nasdaq"]["fpi"] is False


# ---------------------------------------------------------------------------
# §2.3 pack selection and the qualified packs
# ---------------------------------------------------------------------------


def test_g0e_f3_never_cites_s3_and_back() -> None:
    f3_world = C1.standard_registration(form="F-3", family="registration_f3")
    f3 = _run(registration=f3_world[0], share_basis=f3_world[1], other=C1.NASDAQ_ASSUMPTIONS)
    consulted = _consulted_rules(f3)
    assert "form_f3.I.B.5" in consulted
    assert "form_s3.I.B.6" not in consulted
    s3 = _two_shelf_run()
    consulted_s3 = _consulted_rules(s3)
    assert "form_s3.I.B.6" in consulted_s3
    assert "form_f3.I.B.5" not in consulted_s3
    assert "form_f3.I.B.1" not in consulted_s3


def test_g0e_select_rule_pack() -> None:
    pack_s3 = ra.select_rule_pack("US-federal", "nasdaq", "S-3")
    assert isinstance(pack_s3, ra.RuleApplicabilityPack)
    pack_f3 = ra.select_rule_pack("US-federal", "nasdaq", "F-3")
    assert isinstance(pack_f3, ra.RuleApplicabilityPack)
    unqualified = ra.select_rule_pack("US-federal", "nyse", "S-3")
    assert isinstance(unqualified, ic.Unknown)
    assert unqualified.unknown_id == "rule_pack_unqualified:US-federal:nyse:S-3"
    unknown_form = ra.select_rule_pack("US-federal", "nasdaq", "S-1")
    assert isinstance(unknown_form, ic.Unknown)
    assert unknown_form.unknown_id == "rule_pack_unqualified:US-federal:nasdaq:S-1"
    other_jurisdiction = ra.select_rule_pack("Japan", "nasdaq", "S-3")
    assert isinstance(other_jurisdiction, ic.Unknown)
    assert other_jurisdiction.unknown_id == "rule_pack_unqualified:Japan:nasdaq:S-3"


def test_g0e_l0_pack_is_1_2_0_with_the_5615_rule() -> None:
    pack = ra.load_rule_applicability_pack()
    assert pack.version == "capital-structure-rule-applicability/1.2.0"
    assert ra.RULE_APPLICABILITY_PACK_VERSION == "capital-structure-rule-applicability/1.2.0"
    for day, expected in (
        (WINDOW_START, "verified"),
        (WINDOW_END, "verified"),
        ("2025-11-23", "withheld"),
        ("2026-10-20", "beyond_window"),
    ):
        assert ra.rule_status_as_of(pack, "nasdaq.5615.a.3", day).state == expected, day


def test_g0e_e0_nasdaq_spans() -> None:
    reference = rq.load_reference_pack(E0_PATH)
    nasdaq = next(source for source in reference.sources if source.source_id == "nasdaq_rule_5600_series")
    spans = {span.label: span for span in nasdaq.spans}
    text_a = "(A) A Foreign Private Issuer may follow its home country practice in lieu of the requirements of the Rule 5600 Series"
    text_b = "(i) A Foreign Private Issuer that follows a home country practice in lieu of one or more of the Listing Rules shall disclose in its annual reports filed with the Commission each requirement that it does not follow and describe the home country practice followed by the Company in lieu of such requirements."
    for label, text, digest in (
        ("nasdaq_5615_a_3_A_fpi_home_country_practice", text_a, "c037f7c516a11ff8b263226c1dfe823f632d7ebce47e3bf286a2c4d4de150be6"),
        ("nasdaq_5615_a_3_B_i_annual_report_disclosure", text_b, "87f96f8b7b3ecd7051bcfa2604049db4d2d6fd9cdab4bc2c95f1b6e8c3862240"),
    ):
        span = spans[label]
        assert span.text == text
        assert span.chars == len(text) <= rq.EXCERPT_CAP_CHARS
        assert span.sha256 == digest == rq.span_digest(text)
        assert span.interpretation_date == "2025-11-24"
    pinned = json.loads(PACK_PATH.read_text(encoding="utf-8"))["reference_pack"]["pinned_spans"]
    for label, span in spans.items():
        if label.startswith("nasdaq_5615_a_3_"):
            assert pinned[label] == span.sha256


def test_g0e_no_issuer_literal_in_engine() -> None:
    banned = {"AIR", "CLNN", "QNCX", "WHK", "LPTH", "EDBL"}
    for name in (
        "engine/capital_structure/listing_facts.py",
        "engine/capital_structure/capacity.py",
        "engine/capital_structure/rule_applicability.py",
    ):
        tree = ast.parse((REPO / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant):
                value = node.value
                if isinstance(value, str):
                    assert not re.search(r"[0-9]{10}", value), (name, value[:60])
                    assert value not in banned, (name, value)
                elif isinstance(value, int) and not isinstance(value, bool):
                    assert len(str(abs(value))) < 10, (name, value)


# ---------------------------------------------------------------------------
# §2.4 the capacity inputs bundle and the composition pass-through
# ---------------------------------------------------------------------------


def _gate_bundle(listings: Any = None) -> dict[str, Any]:
    kwargs: dict[str, Any] = dict(
        as_of=U1B.GATE_AS_OF,
        generated_at=f"{U1B.GATE_AS_OF[:10]}T12:00:00Z",
        state_generation_id=ic.stable_id("state_bundle", {"fixture": "g0e"}),
        source_generation_id=ic.stable_id("projection:cs:", {"fixture": "g0e"}),
        rules=U1B._fixture_rules(),
        issuers={U1B.GATE_ISSUER: U1B._fixture_family_entries()},
    )
    if listings is not None:
        kwargs["listings"] = listings
    return si.CapacityInputsBundle(**kwargs).as_record()


def test_g0e_capacity_inputs_listing_is_optional() -> None:
    plain_bundle = _gate_bundle()
    explicit_bundle = _gate_bundle(listings={})
    assert plain_bundle == explicit_bundle
    parsed = json.loads(json.dumps(plain_bundle, sort_keys=True))
    si.validate_capacity_inputs_bundle(parsed)
    fact = observed_nasdaq()
    with_listing = _gate_bundle(listings={U1B.GATE_ISSUER: fact})
    parsed_with = json.loads(json.dumps(with_listing, sort_keys=True))
    si.validate_capacity_inputs_bundle(parsed_with)
    assert "listings" not in parsed
    assert parsed_with["listings"][U1B.GATE_ISSUER] == fact.as_record()
    assert parsed_with["generation_id"] != parsed["generation_id"]
    assert parsed_with["coverage"] == parsed["coverage"]
    # The published form reconstructs through the contract reader.
    assert listing_fact_from_record(parsed_with["listings"][U1B.GATE_ISSUER]) == fact
    # A malformed listing is refused by the loader and by the schema.
    malformed_venue = dict(fact.as_record(), venue="lse")
    with pytest.raises(Exception):
        listing_fact_from_record(malformed_venue)
    bad = json.loads(json.dumps(with_listing, sort_keys=True))
    bad["listings"][U1B.GATE_ISSUER] = malformed_venue
    with pytest.raises(Exception):
        si.validate_capacity_inputs_bundle(bad)
    malformed_extra = dict(fact.as_record(), unexpected="x")
    with pytest.raises(Exception):
        listing_fact_from_record(malformed_extra)
    bad2 = json.loads(json.dumps(with_listing, sort_keys=True))
    bad2["listings"][U1B.GATE_ISSUER] = malformed_extra
    with pytest.raises(Exception):
        si.validate_capacity_inputs_bundle(bad2)


def _assembled_listing(fact: ListingFact) -> ListingFact:
    bundle = _gate_bundle(listings={U1B.GATE_ISSUER: fact})
    inputs = si.assemble_scenario_inputs(
        json.loads(json.dumps(bundle, sort_keys=True)), U1B.GATE_ISSUER, U1B.GATE_AS_OF
    )
    assert isinstance(inputs, si.ScenarioInputs)
    assert inputs.listing == fact
    return inputs.listing


def _composed(listing: Any = None) -> sc.ScenarioComposition:
    """S0's own A21 world, composed with the additive listing keyword."""
    kwargs = dict(C2.a21_kwargs())
    other = tuple(kwargs.pop("other", ()))
    state, scenario, built_rules = C1.build(other=other + tuple(S0.FUNDING_ASSUMPTIONS), **kwargs)
    scenario = dataclasses_replace(scenario, fee_rate=S0.FEE_RATE)
    financials = F.financials(F.cash(str(S0.OPENING_CASH), measured="2026-06-30"))
    commitments = F.covenants(
        F.covenant("cov-min-1", str(S0.LIQUIDITY_FLOOR), available_at=S0.COVENANT_AVAILABLE)
    )
    return sc.explain_scenario(
        state,
        SS.instrument_set(),
        SS.basis(),
        financials,
        commitments,
        scenario,
        built_rules,
        pack=C1.PACK,
        listing=listing,
    )


def _canonical_composition(composition: sc.ScenarioComposition) -> str:
    return json.dumps(
        {
            "result": composition.result.as_record(),
            "capacity_inputs": ic._record(composition.capacity.inputs),
            "capacity_envelope": composition.capacity.envelope.as_record(),
            "supply_trace": composition.supply_trace,
            "funding": composition.funding.as_record(),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def test_g0e_compose_scenario_passes_the_listing() -> None:
    plain = _composed()
    explicit = _composed(listing=None)
    assert _canonical_composition(plain) == _canonical_composition(explicit)
    # The composed scenario assumes nasdaq, so an observed NYSE listing is a
    # conflict, which SPEC_G0 §2.2 checks before the unqualified-venue branch.
    conflicted = _composed(listing=observed_nasdaq(exchanges=["NYSE"]))
    unknowns = [item.unknown_id for item in conflicted.result.capacity_envelope.unknowns]
    assert any(uid.startswith("listing_venue_conflict:") for uid in unknowns)
    assert conflicted.capacity.inputs["nasdaq"]["pool"] is None
    assert conflicted.capacity.inputs["nasdaq"]["listing_venue"] == "nyse"
    for route in conflicted.result.capacity_envelope.routes:
        assert route.status != "eligible"
    # The exact ListingFact that `assemble_scenario_inputs` binds from a bundle
    # carrying a listing record is the fact explain_capacity digests.
    fact = observed_nasdaq(evidence=(ITEM_16G_REF,))
    listing = _assembled_listing(fact)
    composed = _composed(listing=listing)
    capacity_inputs = composed.capacity.inputs
    assert capacity_inputs["listing"] == fact.as_record()
    assert capacity_inputs["nasdaq"]["reason"] == "home_country_practice_elected"


def test_g0e_compose_scenario_forwards_the_listing() -> None:
    kwargs = dict(C2.a21_kwargs())
    other = tuple(kwargs.pop("other", ()))
    state, scenario, built_rules = C1.build(other=other + tuple(S0.FUNDING_ASSUMPTIONS), **kwargs)
    scenario = dataclasses_replace(scenario, fee_rate=S0.FEE_RATE)
    financials = F.financials(F.cash(str(S0.OPENING_CASH), measured="2026-06-30"))
    commitments = F.covenants(
        F.covenant("cov-min-1", str(S0.LIQUIDITY_FLOOR), available_at=S0.COVENANT_AVAILABLE)
    )
    args = (state, SS.instrument_set(), SS.basis(), financials, commitments, scenario, built_rules)
    listing = observed_nasdaq(exchanges=["NYSE"])
    composed = sc.compose_scenario(*args, pack=C1.PACK, listing=listing)
    explained = sc.explain_scenario(*args, pack=C1.PACK, listing=listing)
    assert composed.as_record() == explained.result.as_record()
    unknowns = [item.unknown_id for item in composed.capacity_envelope.unknowns]
    assert any(uid.startswith("listing_venue_conflict:") for uid in unknowns)
    plain = sc.explain_scenario(*args, pack=C1.PACK).result.as_record()
    assert sc.compose_scenario(*args, pack=C1.PACK).as_record() == plain


# ---------------------------------------------------------------------------
# Hygiene
# ---------------------------------------------------------------------------


def test_g0e_exact_arithmetic_only() -> None:
    needle = "float" + "("
    for name in (
        REPO / "tests" / Path(__file__).name,
        REPO / "engine" / "capital_structure" / "listing_facts.py",
    ):
        assert needle not in name.read_text(encoding="utf-8"), name.name
