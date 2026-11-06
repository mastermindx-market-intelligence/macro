"""Tests for ``engine/news_impact/transfer.py`` (A4 one-hop transfer layer).

Acceptance fixtures are the design packet's worked cases (A4_transfer_obs
section 5): 5.1, 5.3, 5.4 reproduce their emitted ``transfer_edge.v1``,
5.2 its ``transfer_absence.v1`` (gate ``gmi_member_of_only``), 5.8 its
``macro_shock_fanout.v1``.  Worked case 5.5 is an ``observation_window.v1``
fixture: section 4.7 belongs to a separate lane by commission, so this
suite pins its contract shape (schema-valid against the shipped
observation schema) without minting it.  Every design 4.4 abstention
reason is asserted by exact code with its absence schema-validated, every
error code in ``transfer.CODES`` is asserted by exact string, and module
output is permutation-invariant and deterministic (W3-R6).
"""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from engine.news_impact import transfer
from engine.news_impact.transfer import (
    CODES,
    PriorTransfer,
    TransferAbsence,
    TransferEdge,
    TransferError,
    build_macro_shock_fanout,
    build_peer_set,
    build_transfers,
    candidate_from_dict,
    evaluate_candidate,
    peer_set_absence,
    source_fact_from_dict,
)

HERE = Path(__file__).resolve()
CONTRACTS = HERE.parents[1] / "contracts" / "news_impact"
CASES = HERE.parents[1] / "research" / "prophet_v4" / "news_to_business_impact_20261006" / "phase1_designs" / "A4_transfer_obs" / "cases"

ALIASES = {
    "Apple": "cik:0000320193", "APPLE": "cik:0000320193",
    "TSMC": "cik:0001046179",
    "AMD": "cik:0000002488",
    "NVIDIA": "cik:0001045810",
    "ASML": "cik:0000937966",
    "GOOGL": "cik:0001652044", "GOOG": "cik:0001652044",
}

OBSERVED = "2026-09-28T13:35:00Z"
AVAILABLE = "2026-09-28T13:32:14Z"


def _load_case(name: str) -> dict:
    path = CASES / name
    assert path.is_file(), f"repo-owned design fixture missing (fail closed, never skip): {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _validator(schema_name: str) -> Draft202012Validator:
    path = CONTRACTS / schema_name
    assert path.is_file(), f"frozen contract missing (fail closed, never skip): {path}"
    return Draft202012Validator(json.loads(path.read_text(encoding="utf-8")))


def _edge_validator() -> Draft202012Validator:
    return _validator("transfer_edge.v1.schema.json")


# --------------------------------------------------------------- case 5.1

def _capex_candidate(fx: dict) -> dict:
    """The case-5.1 candidate dict (the perfect, all-gates-pass shape)."""
    return {
        "source_company_id": fx["source_company_id"],
        "target_company_id": fx["target_company_id"],
        "target_role": fx["target_role"],
        "edge_direction": fx["edge_direction"],
        "operating_effect_on_target": fx["operating_effect_on_target"],
        "mechanism_channel": fx["mechanism_channel"],
        "exposure_absence": fx["exposure"]["absence"],
        "timing": fx["timing"],
        "alternatives": fx["alternatives"],
        "claimed_quote": fx["two_party_span"]["claimed_quote"],
        "span": fx["two_party_span"]["span"],
        "display_summary": fx["display_summary"],
    }


def test_case_5_1_customer_capex_supplier_edge_emitted() -> None:
    fx = _load_case("W_customer_capex_supplier.json")
    fact = source_fact_from_dict(
        {"fact_id": fx["source_fact_id"], "company_id": fx["source_company_id"]})
    candidate = candidate_from_dict(_capex_candidate(fx))
    out = evaluate_candidate(candidate, fact, aliases=ALIASES,
                             observed_at=fx["observed_at"],
                             source_available_at=fx["source_available_at"])
    assert isinstance(out, TransferEdge)
    got = out.to_dict()
    assert got.keys() == fx.keys()
    for key in fx:
        if key != "transfer_id":
            assert got[key] == fx[key], key
    assert transfer._TRANSFER_ID_RE.match(got["transfer_id"])
    # deterministic id: identical rerun mints the identical record
    again = evaluate_candidate(candidate, fact, aliases=ALIASES,
                               observed_at=fx["observed_at"],
                               source_available_at=fx["source_available_at"])
    assert transfer.canonical_json(again.to_dict()) == transfer.canonical_json(got)
    _edge_validator().validate(got)


# --------------------------------------------------------------- case 5.2

def test_case_5_2_semi_label_abstains_gmi_member_of_only() -> None:
    fx = _load_case("W_semi_label_abstain.json")
    fact = source_fact_from_dict(
        {"fact_id": fx["source_fact_id"], "company_id": fx["source_company_id"]})
    candidate = candidate_from_dict({
        "source_company_id": fx["source_company_id"],
        "target_company_id": fx["candidate_target_company_id"],
        "generator_kind": "gmi_member_of",
        "generator_id": "theme_graph:MEMBER_OF:ai_semiconductors",
        "graph": "fundamental_comparability",
        "span_absence_detail": fx["two_party_span"]["detail"],
        "absence_display_summary": fx["display_summary"],
    })
    out = evaluate_candidate(candidate, fact, aliases=ALIASES,
                             observed_at=fx["observed_at"],
                             source_available_at=fx["source_available_at"])
    assert isinstance(out, TransferAbsence)
    got = out.to_dict()
    assert got.keys() == fx.keys()
    for key in fx:
        if key != "absence_id":
            assert got[key] == fx[key], key
    assert transfer._TRANSFER_ID_RE.match(got["absence_id"])
    _edge_validator().validate(got)


# --------------------------------------------------------------- case 5.3

def test_case_5_3_supplier_shortage_buyer_negative_edge() -> None:
    fx = _load_case("W_supplier_shortage_buyer.json")
    fact = source_fact_from_dict(
        {"fact_id": fx["source_fact_id"], "company_id": fx["source_company_id"]})
    candidate = candidate_from_dict(_capex_candidate(fx))
    out = evaluate_candidate(candidate, fact, aliases=ALIASES,
                             observed_at=fx["observed_at"],
                             source_available_at=fx["source_available_at"])
    assert isinstance(out, TransferEdge)
    got = out.to_dict()
    for key in fx:
        if key != "transfer_id":
            assert got[key] == fx[key], key
    assert got["operating_effect_on_target"] == "negative"
    assert got["target_role"] == "customer"
    _edge_validator().validate(got)


# --------------------------------------------------------------- case 5.4

def test_case_5_4_correction_supersedes_prior_edge() -> None:
    fx = _load_case("W_correction_supersedes.json")
    prior_fact = "fact_678e8bf5a1906cc701210c40"
    fact = source_fact_from_dict({
        "fact_id": fx["source_fact_id"],
        "company_id": fx["source_company_id"],
        "novelty": "corrected_fact",
        "lineage_fact_ids": [prior_fact],
    })
    prior = PriorTransfer(
        transfer_id=fx["supersedes_transfer_id"],
        source_fact_id=prior_fact,
        source_company_id=fx["source_company_id"],
        target_company_id=fx["target_company_id"],
        observed_at="2026-09-28T13:35:00Z")
    candidate = candidate_from_dict(
        {**_capex_candidate(fx),
         "supersedes_transfer_id": fx["supersedes_transfer_id"]})
    out = evaluate_candidate(candidate, fact, aliases=ALIASES,
                             prior_transfers=[prior],
                             observed_at=fx["observed_at"],
                             source_available_at=fx["source_available_at"])
    assert isinstance(out, TransferEdge)
    got = out.to_dict()
    for key in fx:
        if key != "transfer_id":
            assert got[key] == fx[key], key
    assert got["supersedes_transfer_id"] == fx["supersedes_transfer_id"]
    _edge_validator().validate(got)

    # the same correction WITHOUT the supersedes pointer is a stale cite
    stale = evaluate_candidate(candidate_from_dict(_capex_candidate(fx)), fact,
                               aliases=ALIASES, prior_transfers=[prior],
                               observed_at=fx["observed_at"],
                               source_available_at=fx["source_available_at"])
    assert isinstance(stale, TransferAbsence)
    assert stale.abstention_reason == "source_fact_superseded_stale_cite"


# --------------------------------------------------------------- case 5.5

def test_case_5_5_observation_fixture_is_contract_shaped() -> None:
    """Case 5.5 is an observation_window.v1 fixture.  Section 4.7 is a
    separate lane by commission; this test pins the fixture's shape against
    the shipped observation schema and asserts nothing here mints it."""
    fx = _load_case("W_obs_coincident_ambiguous.json")
    _validator("observation_window.v1.schema.json").validate(fx)
    assert not hasattr(transfer, "build_observation_window")


# --------------------------------------------------------------- case 5.8

def test_case_5_8_macro_shock_fanout_analysed_once() -> None:
    fx = _load_case("W_macro_shock_fanout.json")
    fact = source_fact_from_dict(
        {"fact_id": fx["source_fact_id"], "company_id": "cik:0001046179"})
    roster = [
        {"company_id": "cik:0001046179", "display_name": "TSMC"},
        {"company_id": "cik:0000937966", "display_name": "ASML"},
    ]
    fanout = build_macro_shock_fanout(
        fact, fx["shock_span"], roster, observed_at=fx["observed_at"],
        source_available_at=fx["source_available_at"],
        display_summary=fx["display_summary"])
    got = fanout.to_dict()
    assert got.keys() == fx.keys()
    for key in fx:
        if key != "shock_id":
            assert got[key] == fx[key], key
    assert transfer._SHOCK_ID_RE.match(got["shock_id"])
    _edge_validator().validate(got)


# --------------------------------------------------- every 4.4 gate, exact code

def _base_fact(fx_5_1: dict) -> object:
    return source_fact_from_dict(
        {"fact_id": fx_5_1["source_fact_id"], "company_id": fx_5_1["source_company_id"]})


GATE_CASES = {
    "instruction_detected":
        lambda c, f: (c, source_fact_from_dict(
            {"fact_id": f.fact_id, "company_id": f.company_id,
             "instruction_detected": True}), {}),
    "source_fact_not_validated":
        lambda c, f: (c, source_fact_from_dict(
            {"fact_id": f.fact_id, "company_id": f.company_id, "accepted": False}), {}),
    "source_fact_negated":
        lambda c, f: (c, source_fact_from_dict(
            {"fact_id": f.fact_id, "company_id": f.company_id, "negated": True}), {}),
    "source_fact_superseded_stale_cite":
        lambda c, f: (c, source_fact_from_dict(
            {"fact_id": f.fact_id, "company_id": f.company_id,
             "superseded_by_fact_id": "fact_" + "f" * 24}), {}),
    "participation_only_refused":
        lambda c, f: (candidate_from_dict({**c.to_inject(), "refusal_flags": ["participation_only"]}), f, {}),
    "body_unavailable":
        lambda c, f: (candidate_from_dict({**c.to_inject(), "refusal_flags": ["body_unavailable"]}), f, {}),
    "rights_redacted":
        lambda c, f: (candidate_from_dict({**c.to_inject(), "refusal_flags": ["rights_redacted"]}), f, {}),
    "parse_failed":
        lambda c, f: (candidate_from_dict({**c.to_inject(), "refusal_flags": ["parse_failed"]}), f, {}),
    "llm_relatedness_tag_refused":
        lambda c, f: (candidate_from_dict({**c.to_inject(), "generator_kind": "tagged_ticker_list"}), f, {}),
    "structure_learner_refused":
        lambda c, f: (candidate_from_dict({**c.to_inject(), "refusal_flags": ["structure_learner"]}), f, {}),
    "causal_dag_refused":
        lambda c, f: (candidate_from_dict({**c.to_inject(), "refusal_flags": ["causal_dag"]}), f, {}),
    "peer_selected_by_rally":
        lambda c, f: (candidate_from_dict({**c.to_inject(), "refusal_flags": ["selected_by_rally"]}), f, {}),
    "k3d_participation_only_hold":
        lambda c, f: (candidate_from_dict({**c.to_inject(), "refusal_flags": ["k3d_participation_only"]}), f, {}),
    "target_identity_unresolved":
        lambda c, f: (candidate_from_dict({**c.to_inject(), "target_company_id": None}), f, {}),
    "name_resolution_ambiguous":
        lambda c, f: (candidate_from_dict({
            **c.to_inject(), "target_company_id": None,
            "target_mention": {"ticker": "WAVE", "text": "WAVE", "asof": "2026-09-28"}}),
            f, {"ledger": {"WAVE": (("cik:0000899051", None, None),
                                    ("cik:0001054288", None, None))}}),
    "source_equals_target":
        lambda c, f: (candidate_from_dict({**c.to_inject(), "target_company_id": f.company_id}), f, {}),
    "second_hop_refused":
        lambda c, f: (candidate_from_dict({**c.to_inject(), "hop_count": 2}), f, {}),
    "hop_exceeds_one":
        lambda c, f: (c, f, {"prior_transfers": [PriorTransfer(
            transfer_id="xfer_" + "a" * 24, source_fact_id=f.fact_id,
            source_company_id=c.target_company_id or "",
            target_company_id="cik:0000937966", observed_at=OBSERVED)]}),
    "cycle_on_source_fact":
        lambda c, f: (c, f, {"prior_transfers": [PriorTransfer(
            transfer_id="xfer_" + "b" * 24, source_fact_id=f.fact_id,
            source_company_id=f.company_id,
            target_company_id=c.target_company_id or "", observed_at=OBSERVED)]}),
    "gmi_member_of_only":
        lambda c, f: (candidate_from_dict({**c.to_inject(), "generator_kind": "gmi_member_of"}), f, {}),
    "graph2_membership_only":
        lambda c, f: (candidate_from_dict({**c.to_inject(), "generator_kind": "gics_peer"}), f, {}),
    "graph3_residual_only":
        lambda c, f: (candidate_from_dict({**c.to_inject(), "generator_kind": "residual_comovement"}), f, {}),
    "demand_chain_list_only":
        lambda c, f: (candidate_from_dict({**c.to_inject(), "generator_kind": "demand_chain_hardcoded"}), f, {}),
    "linked_outsider_role_unlabeled":
        lambda c, f: (candidate_from_dict({**c.to_inject(), "generator_kind": "group_linked_outsiders"}), f, {}),
    "role_incidental_or_unknown":
        lambda c, f: (candidate_from_dict({**c.to_inject(), "target_role": None}), f, {}),
    "no_two_party_span":
        lambda c, f: (candidate_from_dict({**c.to_inject(), "claimed_quote": None}), f, {}),
    "span_names_one_party_only":
        lambda c, f: (c, f, {"aliases": {"Apple": "cik:0000320193"}}),
    "channel_market_only_no_graph1":
        lambda c, f: (candidate_from_dict({**c.to_inject(), "mechanism_channel": "market_only"}), f, {}),
    "competitor_without_competitive_claim":
        lambda c, f: (candidate_from_dict({**c.to_inject(), "target_role": "competitor"}), f, {}),
    "no_documented_exposure_for_shock":
        lambda c, f: (candidate_from_dict({
            **c.to_inject(), "generator_kind": "shock_exposure_roster",
            "claimed_quote": None}), f, {}),
}


def _perfect_candidate() -> transfer.TransferCandidate:
    fx = _load_case("W_customer_capex_supplier.json")
    return candidate_from_dict(_capex_candidate(fx))


def _to_inject(self: transfer.TransferCandidate) -> dict:
    """Round-trip a candidate back to its ingest dict (test helper)."""
    data = {
        "source_company_id": self.source_company_id,
        "target_company_id": self.target_company_id,
        "target_role": self.target_role,
        "generator_kind": self.generator_kind,
        "generator_id": self.generator_id,
        "graph": self.graph,
        "hop_count": self.hop_count,
        "mechanism_channel": self.mechanism_channel,
        "operating_effect_on_target": self.operating_effect_on_target,
        "edge_direction": self.edge_direction,
        "claimed_quote": self.claimed_quote,
        "span": self.span,
        "exposure_absence": self.exposure_absence,
        "timing": self.timing,
        "alternatives": self.alternatives,
        "refusal_flags": sorted(self.refusal_flags),
        "display_summary": self.display_summary,
        "supersedes_transfer_id": self.supersedes_transfer_id,
        "span_absence_detail": self.span_absence_detail,
    }
    return {k: v for k, v in data.items() if v is not None}


transfer.TransferCandidate.to_inject = _to_inject  # type: ignore[attr-defined]


@pytest.mark.parametrize("reason", transfer.ABSTENTION_REASONS)
def test_every_abstention_reason_is_reachable_and_schema_valid(reason: str) -> None:
    fx = _load_case("W_customer_capex_supplier.json")
    fact = _base_fact(fx)
    base = _perfect_candidate()
    candidate, fact_mutated, extra = GATE_CASES[reason](base, fact)
    out = evaluate_candidate(
        candidate, fact_mutated,
        aliases=extra.get("aliases", ALIASES),
        ledger=extra.get("ledger"),
        prior_transfers=extra.get("prior_transfers", ()),
        observed_at=OBSERVED, source_available_at=AVAILABLE)
    assert isinstance(out, TransferAbsence), reason
    assert out.abstention_reason == reason
    assert out.unsolicited_instruction_detected == (reason == "instruction_detected")
    _edge_validator().validate(out.to_dict())


def test_body_receipt_address_only_is_body_unavailable() -> None:
    """F19: an address_only receipt can never authorize an edge (span-level
    trigger, distinct from the declarative refusal flag)."""
    fx = _load_case("W_customer_capex_supplier.json")
    data = _capex_candidate(fx)
    span = dict(data["span"])
    span["receipt_state"] = "address_only"
    data["span"] = span
    out = evaluate_candidate(candidate_from_dict(data), _base_fact(fx),
                             aliases=ALIASES, observed_at=OBSERVED,
                             source_available_at=AVAILABLE)
    assert isinstance(out, TransferAbsence)
    assert out.abstention_reason == "body_unavailable"


def test_gmi_supplies_reserved_without_span_is_no_two_party_span() -> None:
    """Section 7 default 2: a Graph-1 reserved edge is candidate provenance
    only; without the news two-party span it abstains on the span gate."""
    fx = _load_case("W_customer_capex_supplier.json")
    data = {**_capex_candidate(fx), "generator_kind": "gmi_supplies_reserved",
            "claimed_quote": None}
    out = evaluate_candidate(candidate_from_dict(data), _base_fact(fx),
                             aliases=ALIASES, observed_at=OBSERVED,
                             source_available_at=AVAILABLE)
    assert isinstance(out, TransferAbsence)
    assert out.abstention_reason == "no_two_party_span"

    # with a news two-party span the edge is authorized by the SPAN, and the
    # emitted provenance is converted to source_span_two_party (4.2)
    data2 = {**_capex_candidate(fx), "generator_kind": "gmi_supplies_reserved"}
    out2 = evaluate_candidate(candidate_from_dict(data2), _base_fact(fx),
                              aliases=ALIASES, observed_at=OBSERVED,
                              source_available_at=AVAILABLE)
    assert isinstance(out2, TransferEdge)
    assert out2.to_dict()["graph_provenance"]["generator_kind"] == "source_span_two_party"


def test_competitor_with_competitive_claim_emits() -> None:
    fx = _load_case("W_customer_capex_supplier.json")
    fact = source_fact_from_dict(
        {"fact_id": fx["source_fact_id"], "company_id": "cik:0000002488"})
    data = {
        "source_company_id": "cik:0000002488",
        "target_company_id": "cik:0001045810",
        "target_role": "competitor",
        "claimed_quote": "AMD's new accelerator takes share from NVIDIA in the accelerator market.",
        "span": fx["two_party_span"]["span"],
        "display_summary": "AMD and NVIDIA are named in a share-taking sentence; the window is this quarter.",
    }
    out = evaluate_candidate(candidate_from_dict(data), fact,
                             aliases=ALIASES, observed_at=OBSERVED,
                             source_available_at=AVAILABLE)
    assert isinstance(out, TransferEdge)
    assert out.target_role == "competitor"
    _edge_validator().validate(out.to_dict())


def test_error_code_source_company_mismatch() -> None:
    fx = _load_case("W_customer_capex_supplier.json")
    data = {**_capex_candidate(fx), "source_company_id": "cik:0000002488"}
    _expect_code("SOURCE_COMPANY_MISMATCH", lambda: evaluate_candidate(
        candidate_from_dict(data), _base_fact(fx), aliases=ALIASES,
        observed_at=OBSERVED, source_available_at=AVAILABLE))


# ------------------------------------------------------- V_TWO_PARTY_SPAN law

def test_two_party_span_cannot_be_disabled() -> None:
    """Seat ruling: V_TWO_PARTY_SPAN is never skipped and never configurable
    off — the gate pipeline exposes no disabling parameter, and a one-party
    span rejects even a candidate that passes every other gate."""
    import inspect
    for func in (evaluate_candidate, build_transfers):
        params = set(inspect.signature(func).parameters)
        assert not any(re_word in p.lower()
                       for p in params
                       for re_word in ("skip", "disable", "ignore", "nocheck")), \
            f"{func.__name__} exposes a gate-disabling parameter"
    assert set(inspect.signature(evaluate_candidate).parameters) == {
        "candidate", "source_fact", "aliases", "ledger",
        "prior_transfers", "observed_at", "source_available_at"}
    # GOOGL/GOOG aliases resolve to one CIK and neither source nor target is
    # named: the whole replayed evidence names at most one party -> reject
    fx = _load_case("W_customer_capex_supplier.json")
    data = _capex_candidate(fx)
    data["claimed_quote"] = "GOOGL and GOOG are one issuer here."
    span = dict(data["span"])
    span["display_excerpt"] = "GOOGL and GOOG are one issuer here."
    data["span"] = span
    out = evaluate_candidate(candidate_from_dict(data), _base_fact(fx),
                             aliases=ALIASES, observed_at=OBSERVED,
                             source_available_at=AVAILABLE)
    assert isinstance(out, TransferAbsence)
    assert out.abstention_reason == "span_names_one_party_only"


# ----------------------------------------------------------- error codes

def _expect_code(code: str, thunk) -> None:
    with pytest.raises(TransferError) as excinfo:
        thunk()
    assert excinfo.value.code == code
    assert str(excinfo.value).startswith(f"{code}: ")


def test_error_code_unknown_candidate_key() -> None:
    _expect_code("UNKNOWN_CANDIDATE_KEY", lambda: candidate_from_dict(
        {"source_company_id": "cik:0000320193", "wat": 1}))


def test_error_code_missing_source_company() -> None:
    _expect_code("MISSING_SOURCE_COMPANY",
                 lambda: candidate_from_dict({"target_company_id": "cik:0001046179"}))


def test_error_code_unknown_refusal_flag() -> None:
    _expect_code("UNKNOWN_REFUSAL_FLAG", lambda: candidate_from_dict(
        {"source_company_id": "cik:0000320193", "refusal_flags": ["nope"]}))


def test_error_code_unknown_generator_kind() -> None:
    _expect_code("UNKNOWN_GENERATOR_KIND", lambda: candidate_from_dict(
        {"source_company_id": "cik:0000320193", "generator_kind": "telepathy"}))


def test_error_code_unknown_graph() -> None:
    _expect_code("UNKNOWN_GRAPH", lambda: candidate_from_dict(
        {"source_company_id": "cik:0000320193", "graph": "social_network"}))


def test_error_code_unknown_channel() -> None:
    _expect_code("UNKNOWN_CHANNEL", lambda: candidate_from_dict(
        {"source_company_id": "cik:0000320193", "mechanism_channel": "vibes"}))


def test_error_code_unknown_target_role() -> None:
    _expect_code("UNKNOWN_TARGET_ROLE", lambda: candidate_from_dict(
        {"source_company_id": "cik:0000320193", "target_role": "distributor"}))


def test_error_code_unknown_operating_effect() -> None:
    _expect_code("UNKNOWN_OPERATING_EFFECT", lambda: candidate_from_dict(
        {"source_company_id": "cik:0000320193", "operating_effect_on_target": "bullish"}))


def test_error_code_unknown_edge_direction() -> None:
    _expect_code("UNKNOWN_EDGE_DIRECTION", lambda: candidate_from_dict(
        {"source_company_id": "cik:0000320193", "edge_direction": "sideways"}))


def test_error_code_malformed_company_id() -> None:
    _expect_code("MALFORMED_COMPANY_ID", lambda: candidate_from_dict(
        {"source_company_id": "AAPL"}))


def test_error_code_malformed_fact_id() -> None:
    _expect_code("MALFORMED_FACT_ID", lambda: source_fact_from_dict(
        {"fact_id": "fact_xyz", "company_id": "cik:0000320193"}))


def test_error_code_malformed_transfer_id() -> None:
    _expect_code("MALFORMED_TRANSFER_ID", lambda: candidate_from_dict(
        {"source_company_id": "cik:0000320193",
         "supersedes_transfer_id": "xfer_zzz"}))


def test_error_code_malformed_shock_id() -> None:
    _expect_code("MALFORMED_SHOCK_ID", lambda: candidate_from_dict(
        {"source_company_id": "cik:0000320193", "shock_id": "shock_1"}))


def test_error_code_malformed_timestamp() -> None:
    fx = _load_case("W_customer_capex_supplier.json")
    _expect_code("MALFORMED_TIMESTAMP", lambda: evaluate_candidate(
        _perfect_candidate(), _base_fact(fx), aliases=ALIASES,
        observed_at="2026-09-28 13:35:00", source_available_at=AVAILABLE))


def test_error_code_hop_count_invalid() -> None:
    _expect_code("HOP_COUNT_INVALID", lambda: candidate_from_dict(
        {"source_company_id": "cik:0000320193", "hop_count": 0}))


def test_error_code_display_summary_required() -> None:
    fx = _load_case("W_customer_capex_supplier.json")
    data = _capex_candidate(fx)
    del data["display_summary"]
    _expect_code("DISPLAY_SUMMARY_REQUIRED", lambda: evaluate_candidate(
        candidate_from_dict(data), _base_fact(fx), aliases=ALIASES,
        observed_at=OBSERVED, source_available_at=AVAILABLE))


def test_error_code_target_identity_conflict() -> None:
    fx = _load_case("W_customer_capex_supplier.json")
    data = _capex_candidate(fx)
    data["target_mention"] = {"ticker": "TSM", "text": "TSM", "asof": "2026-09-28"}
    _expect_code("TARGET_IDENTITY_CONFLICT", lambda: evaluate_candidate(
        candidate_from_dict(data), _base_fact(fx),
        aliases=ALIASES, ledger={"TSM": (("cik:0000937966", None, None),)},
        observed_at=OBSERVED, source_available_at=AVAILABLE))


def test_error_code_candidate_span_malformed() -> None:
    _expect_code("CANDIDATE_SPAN_MALFORMED", lambda: candidate_from_dict(
        {"source_company_id": "cik:0000320193", "claimed_quote": "x",
         "span": {"schema": "not_a_span"}}))


def test_error_code_absence_reason_unknown() -> None:
    _expect_code("ABSENCE_REASON_UNKNOWN",
                 lambda: transfer._field_absence("because", "subject"))


def _fanout_thunk(fx: dict, roster, **kwargs):
    fact = source_fact_from_dict(
        {"fact_id": fx["source_fact_id"], "company_id": "cik:0001046179"})
    return lambda: build_macro_shock_fanout(
        fact, fx["shock_span"], roster, observed_at=fx["observed_at"],
        source_available_at=fx["source_available_at"],
        display_summary=fx["display_summary"], **kwargs)


def test_error_code_roster_too_small() -> None:
    fx = _load_case("W_macro_shock_fanout.json")
    _expect_code("ROSTER_TOO_SMALL", _fanout_thunk(
        fx, [{"company_id": "cik:0001046179", "display_name": "TSMC"}]))


def test_error_code_roster_too_large() -> None:
    fx = _load_case("W_macro_shock_fanout.json")
    roster = [{"company_id": f"cik:{i:010d}", "display_name": f"N{i}"}
              for i in range(1, 66)]
    _expect_code("ROSTER_TOO_LARGE", _fanout_thunk(fx, roster))


def test_error_code_roster_duplicate_company() -> None:
    fx = _load_case("W_macro_shock_fanout.json")
    roster = [{"company_id": "cik:0001046179", "display_name": "TSMC"}] * 2
    _expect_code("ROSTER_DUPLICATE_COMPANY", _fanout_thunk(fx, roster))


def test_error_code_roster_row_malformed() -> None:
    fx = _load_case("W_macro_shock_fanout.json")
    roster = [{"company_id": "cik:0001046179", "display_name": "TSMC", "wat": 1},
              {"company_id": "cik:0000937966", "display_name": "ASML"}]
    _expect_code("ROSTER_ROW_MALFORMED", _fanout_thunk(fx, roster))


def test_error_code_roster_name_required() -> None:
    fx = _load_case("W_macro_shock_fanout.json")
    roster = [{"company_id": "cik:0001046179"},
              {"company_id": "cik:0000937966", "display_name": "ASML"}]
    _expect_code("ROSTER_NAME_REQUIRED", _fanout_thunk(fx, roster))


def test_error_code_evidence_span_malformed() -> None:
    fx = _load_case("W_macro_shock_fanout.json")
    fact = source_fact_from_dict(
        {"fact_id": fx["source_fact_id"], "company_id": "cik:0001046179"})
    _expect_code("EVIDENCE_SPAN_MALFORMED", lambda: build_macro_shock_fanout(
        fact, {"claimed_quote": "no span here"},
        [{"company_id": "cik:0001046179", "display_name": "TSMC"},
         {"company_id": "cik:0000937966", "display_name": "ASML"}],
        observed_at=fx["observed_at"], source_available_at=fx["source_available_at"],
        display_summary=fx["display_summary"]))


def test_error_code_peer_set_empty() -> None:
    _expect_code("PEER_SET_EMPTY", lambda: build_peer_set([], "cik:0001046179"))


def test_error_code_peer_set_too_large() -> None:
    members = [f"cik:{i:010d}" for i in range(1, 66)]
    _expect_code("PEER_SET_TOO_LARGE",
                 lambda: build_peer_set(members, "cik:0001046179"))


def test_error_code_peer_set_contains_target() -> None:
    _expect_code("PEER_SET_CONTAINS_TARGET", lambda: build_peer_set(
        ["cik:0000320193", "cik:0001046179"], "cik:0001046179"))


def test_error_code_unknown_peer_selector() -> None:
    _expect_code("UNKNOWN_PEER_SELECTOR", lambda: peer_set_absence("documented_exposure"))


def test_codes_frozenset_covers_every_raised_code() -> None:
    import inspect
    source = inspect.getsource(transfer)
    raised = set(__import__("re").findall(r'TransferError\(\s*"([A-Z_]+)"', source))
    assert raised <= CODES
    assert all(code in source for code in CODES)  # no orphan codes


# ------------------------------------------------------------- peer set (4.6)

def test_build_peer_set_documented_exposure_excludes_target() -> None:
    got = build_peer_set(["cik:0000937966", "cik:0000723125",
                          "cik:0000937966"], "cik:0001046179")
    assert got == {
        "selection": "documented_exposure",
        "member_ids": ["cik:0000937966", "cik:0000723125"],
        "excluded_target_id": "cik:0001046179",
        "target_excluded": True,
    }


def test_peer_set_absence_names_forbidden_selector() -> None:
    got = peer_set_absence("rallied_most")
    assert got["schema"] == "field_absence.v1"
    assert got["reason"] == "not_stated"
    assert got["subject"] == "peer_set"


# ----------------------------------------------- determinism / invariance

def _mixed_candidates() -> list:
    fx_edge = _load_case("W_customer_capex_supplier.json")
    data = _capex_candidate(fx_edge)
    return [
        candidate_from_dict(data),
        candidate_from_dict({**data, "generator_kind": "gmi_member_of"}),
        candidate_from_dict({**data, "mechanism_channel": "market_only"}),
        candidate_from_dict({**data, "target_role": "competitor"}),
        candidate_from_dict({**data, "claimed_quote": None}),
        candidate_from_dict({**data, "target_company_id": fx_edge["source_company_id"]}),
    ]


def test_permutation_invariance_and_stripping() -> None:
    fx = _load_case("W_customer_capex_supplier.json")
    fact = _base_fact(fx)
    base = _mixed_candidates()
    spiked = [candidate_from_dict({**c.to_inject(), "confidence": 0.9,
                                   "sentiment": "positive"})
              for c in base]
    canonical = []
    for order in (spiked, spiked[::-1], spiked[3:] + spiked[:3]):
        result = build_transfers(fact, order, aliases=ALIASES,
                                 observed_at=OBSERVED, source_available_at=AVAILABLE)
        canonical.append(transfer.canonical_json(result.to_dicts()))
        assert result.stripped_fields == ("confidence", "sentiment")
        assert len(result.edges) == 1 and len(result.absences) == 5
    assert canonical[0] == canonical[1] == canonical[2]

    def walk_keys(node, acc):
        if isinstance(node, dict):
            acc.update(node.keys())
            for v in node.values():
                walk_keys(v, acc)
        elif isinstance(node, list):
            for v in node:
                walk_keys(v, acc)
    keys: set = set()
    for doc in json.loads(canonical[0]):
        walk_keys(doc, keys)
        _edge_validator().validate(doc)
    assert not (keys & transfer.FORBIDDEN_INBOUND_KEYS)


def test_ladder_resolved_target_emits_edge() -> None:
    """A candidate with no explicit id resolves its target through the owner
    D12 ladder (issuer.resolve_mention) and can still emit."""
    fx = _load_case("W_customer_capex_supplier.json")
    data = _capex_candidate(fx)
    data["target_company_id"] = None
    data["target_mention"] = {"ticker": "TSM", "text": "TSM", "asof": "2026-09-28"}
    out = evaluate_candidate(
        candidate_from_dict(data), _base_fact(fx), aliases=ALIASES,
        ledger={"TSM": (("cik:0001046179", None, None),)},
        observed_at=OBSERVED, source_available_at=AVAILABLE)
    assert isinstance(out, TransferEdge)
    assert out.target_company_id == "cik:0001046179"
    _edge_validator().validate(out.to_dict())


def test_constants_mirror_the_frozen_schema() -> None:
    schema = transfer.load_transfer_schema()
    defs = schema["$defs"]
    assert transfer.TARGET_ROLES == tuple(defs["target_role"]["enum"])
    assert transfer.EDGE_DIRECTIONS == tuple(defs["edge_direction"]["enum"])
    assert transfer.OPERATING_EFFECTS == tuple(
        defs["operating_effect_on_target"]["enum"])
    assert transfer.CHANNELS == tuple(defs["channel_hint"]["enum"])
    assert transfer.GENERATOR_KINDS == tuple(defs["generator_kind"]["enum"])
    assert transfer.GRAPH_NAMES == tuple(defs["graph_name"]["enum"])
    assert transfer.ABSTENTION_REASONS == tuple(defs["abstention_reason"]["enum"])
    assert set(transfer.GENERATOR_GATE_REASON) <= set(transfer.GENERATOR_KINDS)
    assert set(transfer.GENERATOR_GATE_REASON.values()) <= set(transfer.ABSTENTION_REASONS)
    assert set(transfer.REFUSAL_FLAG_REASONS)  # non-empty, ordered
    assert all(r in transfer.ABSTENTION_REASONS for _, r in transfer.REFUSAL_FLAG_REASONS)
    assert transfer.RESIDUAL_FACTOR_IDS == ("market", "documented_peer_residual")


def test_shock_roster_row_with_minted_transfer_ref_round_trips() -> None:
    fx = _load_case("W_macro_shock_fanout.json")
    fact = source_fact_from_dict(
        {"fact_id": fx["source_fact_id"], "company_id": "cik:0001046179"})
    roster = [
        {"company_id": "cik:0001046179",
         "transfer_ref": "xfer_" + "0" * 24},
        {"company_id": "cik:0000937966", "display_name": "ASML"},
    ]
    fanout = build_macro_shock_fanout(
        fact, fx["shock_span"], roster, observed_at=fx["observed_at"],
        source_available_at=fx["source_available_at"],
        display_summary=fx["display_summary"])
    doc = fanout.to_dict()
    assert doc["exposure_roster"][0]["transfer_ref"] == "xfer_" + "0" * 24
    assert doc["exposure_roster"][1]["transfer_ref"]["reason"] == "not_stated"
    _edge_validator().validate(doc)
