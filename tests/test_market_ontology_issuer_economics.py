"""``sector_intelligence.issuer_economics.v1`` — the lane-5 v1.1 falsifier
suite (SP04 / SP05 / SP12) plus the block's own contract tests.

EVIDENCE LABELS. Every test in this file except
:func:`test_real_security_master_alias_enumeration` runs on SYNTHETIC
bundles/scopes built below — FIXTURE evidence, never a claim about any real
issuer. The one exception is presence-gated on the committed
``data/reference/security_master.parquet`` and is REAL exactly where that
file is materialized (a sparse session worktree may legitimately not have
it); whether it ran is reported in the lane return.

What the three falsifier rows prove here (source definitions: Prophet
production masterplan §18 SP04/SP05/SP12, 2026-11-09):

* SP04 — with benchmark, membership, model parameters and non-issuer inputs
  held fixed, perturbing the candidate issuer and its aliases leaves the raw
  leave-one-out value unchanged; the whole-cohort benchmark effect that still
  contains the candidate is labelled ``mediated_benchmark``, never presented
  as independent issuer confirmation.
* SP05 — one price root repeated under several views (here: the same filing
  event re-served under several alias listings, and N facts from one filing)
  does not raise the independent evidence count: lineage families, not
  facts, are the count, and the wording says lineage-uniqueness, never
  independence.
* SP12 — a group population containing unreported issuer results keeps the
  eligible / reported / comparable / unknown denominators truthful: an
  unreported issuer is unknown, never zero, never a deterioration.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from engine.market_ontology.issuer_economics import (
    ISSUER_ECONOMICS_SCHEMA,
    build_issuer_economics,
)
from engine.market_ontology.semiconductor_witness_scope import (
    WitnessIdentity,
    WitnessScope,
)

ROOT = Path(__file__).resolve().parents[1]
REAL_MASTER_PATH = ROOT / "data" / "reference" / "security_master.parquet"

# The six all-false authority flags, restated as the expected literal so a
# drift in the module's AUTHORITY map is a red test, not a silent widening.
ALL_FALSE_AUTHORITY = {
    "rank": False, "gate": False, "size": False,
    "veto": False, "originate": False, "open_entry": False,
}


# ---------------------------------------------------------------------------
# Synthetic cohort builders (FIXTURE evidence only)
# ---------------------------------------------------------------------------


def _identity(ticker: str, issuer_id: str, cik: str) -> WitnessIdentity:
    return WitnessIdentity(
        ticker=ticker,
        company_node_id=f"co:synth_{ticker.lower()}",
        issuer_id=issuer_id,
        cik=cik,
    )


def _scope(*identities: WitnessIdentity) -> WitnessScope:
    return WitnessScope(
        slice_key="hbm_packaging",
        identities=tuple(identities),
        omissions=("slice_scope_unowned",),
    )


def _fact(metric: str, value: Any, unit: str, label: str) -> dict[str, Any]:
    return {
        "metric": metric, "value": value, "unit": unit, "fiscal_period": label,
        "basis": "reported_gaap", "currency": "USD", "perimeter": "as_reported",
    }


def _row(event_id: str, cik: str, year: int, quarter: int, facts: list[dict[str, Any]]) -> dict[str, Any]:
    """One event-workspace row shaped exactly like the owner fixtures: the
    structured ``fiscal_period`` is the ROW's; the facts carry only LABEL
    periods. Deliberately NO row-level ``metric``/``value`` keys exist, so any
    row-level read in the block under test yields nothing and the test fails."""
    return {
        "event_id": event_id,
        "cik": cik,
        "company_node_id": f"co:cik_{cik}",
        "fiscal_period": {"year": year, "quarter": quarter},
        "guidance": [],
        "reported": facts,
        "lifecycle": {
            "source_available_at": f"{year}-04-20T12:00:00Z",
            "observed_at": f"{year}-04-20T12:00:00Z",
            "recorded_at": f"{year}-04-20T12:00:00Z",
        },
    }


def _bundle(rows: list[dict[str, Any]]) -> SimpleNamespace:
    return SimpleNamespace(event_workspaces=tuple(rows))


def _query() -> SimpleNamespace:
    return SimpleNamespace(slice_key="hbm_packaging")


def _resolver(aliases_by_issuer: dict[str, tuple[str, ...]]):
    def resolve(issuer_id: str) -> tuple[str, ...]:
        return aliases_by_issuer.get(issuer_id, ())
    return resolve


def _build(
    rows: list[dict[str, Any]],
    identities: tuple[WitnessIdentity, ...],
    *,
    eligible_count: int,
    aliases: dict[str, tuple[str, ...]] | None = None,
    dropped: bool = False,
) -> dict[str, Any]:
    return dict(build_issuer_economics(
        _query(), _bundle(rows),
        scope=_scope(*identities),
        eligible_count=eligible_count,
        alias_resolver=_resolver(aliases or {}),
        dropped=dropped,
    ))


A = _identity("AAA", "ISS:SYN-A", "0000000010")
B = _identity("BBB", "ISS:SYN-B", "0000000020")
C = _identity("CCC", "ISS:SYN-C", "0000000030")
D = _identity("DDD", "ISS:SYN-D", "0000000040")
ALIASES = {
    "ISS:SYN-A": ("SEC:US-XNAS-AAA", "SEC:US-XNYS-AAAB"),
    "ISS:SYN-B": ("SEC:US-XNAS-BBB",),
    "ISS:SYN-C": ("SEC:US-XNAS-CCC",),
    "ISS:SYN-D": ("SEC:US-XNAS-DDD",),
}


# ---------------------------------------------------------------------------
# SP04 — leave-issuer-out invariance under candidate + alias perturbation
# ---------------------------------------------------------------------------


def test_sp04_leave_issuer_out_is_invariant_to_candidate_and_alias_perturbation():
    """Frozen benchmark/membership/model/non-issuer inputs: the declared
    cohort (3), the roster identities, B's and C's rows and the alias master
    are IDENTICAL across every call below. Only the candidate A's own rows
    move — its fact VALUES first, then an ENTIRE EXTRA alias listing under
    the same CIK — and A's raw leave-issuer-out block must not move at all,
    because it is computed over non-candidate rows only."""
    peers_rows = [
        _row("evt-b-2026q1", B.cik, 2026, 1, [_fact("revenue_usd_bn", 2.0, "USD_bn", "2026Q1")]),
        _row("evt-b-2026q2", B.cik, 2026, 2, [_fact("revenue_usd_bn", 2.4, "USD_bn", "2026Q2")]),
        _row("evt-c-2026q1", C.cik, 2026, 1, [_fact("revenue_usd_bn", 7.0, "USD_bn", "2026Q1")]),
        _row("evt-c-2026q2", C.cik, 2026, 2, [_fact("revenue_usd_bn", 7.7, "USD_bn", "2026Q2")]),
    ]
    candidate_rows = [
        # TWO alias listings of the SAME issuer (same CIK), each re-serving
        # the same filing's economics under its own event id.
        _row("evt-a-x-2026q1", A.cik, 2026, 1, [_fact("revenue_usd_bn", 10.0, "USD_bn", "2026Q1")]),
        _row("evt-a-y-2026q1", A.cik, 2026, 1, [_fact("revenue_usd_bn", 10.0, "USD_bn", "2026Q1")]),
        _row("evt-a-x-2026q2", A.cik, 2026, 2, [_fact("revenue_usd_bn", 11.0, "USD_bn", "2026Q2")]),
    ]
    fixed = dict(
        identities=(A, B, C),
        eligible_count=3,
        aliases=ALIASES,
    )

    baseline = _build(peers_rows + candidate_rows, **fixed)

    # (1) Perturb the candidate's VALUES across every alias row.
    perturbed_values = _build(peers_rows + [
        _row("evt-a-x-2026q1", A.cik, 2026, 1, [_fact("revenue_usd_bn", 99.0, "USD_bn", "2026Q1")]),
        _row("evt-a-y-2026q1", A.cik, 2026, 1, [_fact("revenue_usd_bn", 99.0, "USD_bn", "2026Q1")]),
        _row("evt-a-x-2026q2", A.cik, 2026, 2, [_fact("revenue_usd_bn", -5.0, "USD_bn", "2026Q2")]),
    ], **fixed)

    # (2) Perturb the candidate's ALIAS SET: a whole extra listing appears.
    perturbed_alias = _build(peers_rows + candidate_rows + [
        _row("evt-a-z-2026q2", A.cik, 2026, 2, [_fact("revenue_usd_bn", 123.0, "USD_bn", "2026Q2")]),
    ], **fixed)

    key = A.issuer_id
    assert key in baseline["leave_issuer_out"]
    assert baseline["leave_issuer_out"][key] == perturbed_values["leave_issuer_out"][key]
    assert baseline["leave_issuer_out"][key] == perturbed_alias["leave_issuer_out"][key]

    # The exclusion is BY CIK across every alias, and the removed aliases are
    # shown, not inferred.
    assert baseline["leave_issuer_out"][key]["removed_aliases"] == list(ALIASES[key])
    assert perturbed_alias["leave_issuer_out"][key]["removed_aliases"] == list(ALIASES[key])
    # Peer measures really are non-candidate-only: three A rows in the
    # baseline bundle, none of them counted.
    assert baseline["leave_issuer_out"][key]["peer_evidence_rows"] == len(peers_rows)
    assert perturbed_alias["leave_issuer_out"][key]["peer_evidence_rows"] == len(peers_rows)

    # Value-only perturbation moves nothing anywhere but the candidate's own
    # issuer block (B's and C's leave-out blocks read only non-B / non-C
    # rows, whose contents did not change shape).
    for other in (B.issuer_id, C.issuer_id):
        assert baseline["leave_issuer_out"][other] \
            == perturbed_values["leave_issuer_out"][other]

    # Non-vacuity: the candidate's own reported facts DID move.
    baseline_facts = [f["value"] for f in baseline["issuers"][0]["reported"]]
    perturbed_facts = [f["value"] for f in perturbed_values["issuers"][0]["reported"]]
    assert baseline_facts != perturbed_facts

    # The separately recomputed whole-cohort aggregate still contains the
    # candidate: labelled mediated, never independent confirmation.
    assert baseline["leave_issuer_out"][key]["mediated_benchmark"] is True
    assert baseline["leave_issuer_out"][key]["renormalization"] == \
        "equal_weight_over_declared_cohort"


# ---------------------------------------------------------------------------
# SP05 — one shared root under several views does not raise the count
# ---------------------------------------------------------------------------


def test_sp05_one_shared_root_does_not_raise_independent_evidence_count():
    """One filing's price root, re-served: (a) as N facts inside ONE event
    workspace, and (b) as the SAME event id under a second alias listing.
    Neither raises the lineage family count — N facts from one filing are ONE
    lineage family, and the count that matters is families, not facts, not
    rows. The block says lineage-uniqueness, never independence."""
    five_facts = [
        _fact("revenue_usd_bn", 16.5, "USD_bn", "2026Q2"),
        _fact("gross_margin_pct", 53.0, "PCT", "2026Q2"),
        _fact("capex_usd_bn", 4.1, "USD_bn", "2026Q2"),
        _fact("eps_usd", 1.27, "USD", "2026Q2"),
        _fact("wafer_asp_usd", 3150.0, "USD", "2026Q2"),
    ]
    one_row = _build(
        [_row("evt-shared-filing", A.cik, 2026, 2, five_facts)],
        (A,), eligible_count=1, aliases=ALIASES,
    )
    assert len(one_row["issuers"][0]["reported"]) == 5  # N facts served...
    assert one_row["lineage"]["family_count"] == 1      # ...ONE family.
    assert one_row["lineage"]["item_count"] == 1
    assert one_row["lineage"]["families"] == [["evt-shared-filing"]]

    # The same filing again under a second alias listing (same event id, same
    # CIK): still one family — the repeated root adds no evidence.
    re_served = _build(
        [
            _row("evt-shared-filing", A.cik, 2026, 2, five_facts),
            _row("evt-shared-filing", A.cik, 2026, 2, five_facts),
        ],
        (A,), eligible_count=1, aliases=ALIASES,
    )
    assert re_served["issuers"][0]["row_count"] == 2
    assert re_served["lineage"]["family_count"] == 1
    assert re_served["lineage"]["independent_count_rule"] == \
        "one family = one vote; aliases add no evidence"

    # And the same law on the leave-out side: the peer lineage also counts
    # families, not rows — B's two rows are ONE filing re-served (same event
    # id), so excluding A leaves exactly one peer lineage family. (Two
    # DIFFERENT workspaces would be two families — lineage uniqueness, still
    # never "independent confirmations" per the wording law.)
    peers = _build(
        [
            _row("evt-shared-filing", A.cik, 2026, 2, five_facts),
            _row("evt-peer-filing", B.cik, 2026, 2, five_facts),
            _row("evt-peer-filing", B.cik, 2026, 2, five_facts),
        ],
        (A, B), eligible_count=2, aliases=ALIASES,
    )
    loo = peers["leave_issuer_out"][A.issuer_id]
    assert loo["peer_evidence_rows"] == 2
    assert loo["peer_lineage"]["family_count"] == 1

    # The wording law is carried in the block itself.
    assert one_row["wording"]["lineage"] == (
        "Deduplicated source roots establish lineage uniqueness, "
        "not statistical independence."
    )


# ---------------------------------------------------------------------------
# SP12 — truthful denominators with unreported issuers in the population
# ---------------------------------------------------------------------------


def test_sp12_unreported_issuers_keep_truthful_denominators():
    """A declared cohort of four, one per state: A reported a metric in two
    adjacent periods (comparable); B served a row with NO reported facts;
    C is identified but served no row at all; D reported a single period
    only. Eligible is the DECLARED roster (4); unknown counts everyone who
    did not report (B and C) — never zero, never a deterioration; D is
    reported-but-noncomparable, which is not a negative result."""
    rows = [
        _row("evt-a-2026q1", A.cik, 2026, 1, [_fact("revenue_usd_bn", 10.0, "USD_bn", "2026Q1")]),
        _row("evt-a-2026q2", A.cik, 2026, 2, [_fact("revenue_usd_bn", 11.0, "USD_bn", "2026Q2")]),
        # B: a row exists, but it reported nothing.
        _row("evt-b-2026q1", B.cik, 2026, 1, []),
        # C: no row at all.
        # D: reported, but only one period.
        _row("evt-d-2026q2", D.cik, 2026, 2, [_fact("revenue_usd_bn", 5.0, "USD_bn", "2026Q2")]),
    ]
    block = _build(rows, (A, B, C, D), eligible_count=4, aliases=ALIASES)

    assert block["schema"] == ISSUER_ECONOMICS_SCHEMA
    assert block["cohort"] == {
        "eligible": 4,
        "identified": 4,
        "reported": 2,
        "comparable": 1,
        "unknown": 2,
        "noncomparable": 1,
        "denominator_rule": block["cohort"]["denominator_rule"],
    }
    rule = block["cohort"]["denominator_rule"]
    assert "unreported is unknown" in rule
    assert "not a negative result" in rule

    states = {i["issuer_id"]: i["cohort_state"] for i in block["issuers"]}
    assert states == {
        "ISS:SYN-A": "comparable",
        "ISS:SYN-B": "eligible_unreported",  # a row with no facts is UNREPORTED
        "ISS:SYN-C": "eligible_unreported",  # identified, no row: UNREPORTED
        "ISS:SYN-D": "reported_noncomparable",
    }
    # No selected-winner feed: every cohort issuer is listed with its own
    # state — all four, in one flat list, no ranking key anywhere.
    assert len(block["issuers"]) == 4
    for issuer in block["issuers"]:
        assert set(issuer) >= {
            "issuer_id", "cik", "ticker", "aliases", "cohort_state",
            "reported", "signed_changes", "unknowns",
        }
    # The unknown class is stated in the wording law, not just counted.
    assert block["wording"]["unreported"] == \
        "An unreported issuer is unknown, not a deterioration or zero."
    assert block["wording"]["noncomparable"] == \
        "A noncomparable report is not a negative result."


# ---------------------------------------------------------------------------
# The block's own contract (FIXTURE)
# ---------------------------------------------------------------------------


def test_signed_changes_read_the_nested_reported_facts():
    """The lane-5 defect this carrier fixed, pinned so it cannot return: the
    rows carry NO row-level metric/value fields at all — only nested
    ``reported`` facts — and the signed bridge still computes, over the
    owning row's structured period."""
    rows = [
        _row("evt-a-2026q1", A.cik, 2026, 1, [_fact("revenue_usd_bn", 10.0, "USD_bn", "2026Q1")]),
        _row("evt-a-2026q2", A.cik, 2026, 2, [_fact("revenue_usd_bn", 8.5, "USD_bn", "2026Q2")]),
    ]
    block = _build(rows, (A,), eligible_count=1)
    changes = block["issuers"][0]["signed_changes"]
    assert changes == [{
        "metric": "revenue_usd_bn",
        "unit": "USD_bn",
        "from_fiscal_period": {"year": 2026, "quarter": 1},
        "to_fiscal_period": {"year": 2026, "quarter": 2},
        "from_value": 10.0,
        "to_value": 8.5,
        "signed_change": -1.5,  # negative: displayed, never dropped
    }]

    # A disagreement between alias re-serves of one (period, metric, unit) is
    # ambiguous and is not differenced — never averaged, never picked.
    disagree = _build([
        _row("evt-a-2026q1", A.cik, 2026, 1, [_fact("revenue_usd_bn", 10.0, "USD_bn", "2026Q1")]),
        _row("evt-a-x-2026q1", A.cik, 2026, 1, [_fact("revenue_usd_bn", 10.0, "USD_bn", "2026Q1")]),
        _row("evt-a-2026q2", A.cik, 2026, 2, [_fact("revenue_usd_bn", 8.5, "USD_bn", "2026Q2")]),
        _row("evt-a-y-2026q2", A.cik, 2026, 2, [_fact("revenue_usd_bn", 9.9, "USD_bn", "2026Q2")]),
    ], (A,), eligible_count=1)
    assert disagree["issuers"][0]["signed_changes"] == []
    # ...while every conflicting original is still served VERBATIM.
    assert sorted(f["value"] for f in disagree["issuers"][0]["reported"]) == \
        [8.5, 9.9, 10.0, 10.0]


def test_negative_values_are_served_verbatim_and_signed():
    rows = [
        _row("evt-neg-2026q1", A.cik, 2026, 1, [
            _fact("net_income_usd_bn", -1.25, "USD_bn", "2026Q1"),
            _fact("revenue_usd_bn", 3.0, "USD_bn", "2026Q1"),
        ]),
        _row("evt-neg-2026q2", A.cik, 2026, 2, [
            _fact("net_income_usd_bn", -2.0, "USD_bn", "2026Q2"),
            _fact("revenue_usd_bn", 3.1, "USD_bn", "2026Q2"),
        ]),
    ]
    block = _build(rows, (A,), eligible_count=1)
    # Every original is served VERBATIM — signs included, none dropped.
    assert sorted(
        (f["metric"], f["value"]) for f in block["issuers"][0]["reported"]
    ) == [
        ("net_income_usd_bn", -2.0),
        ("net_income_usd_bn", -1.25),
        ("revenue_usd_bn", 3.0),
        ("revenue_usd_bn", 3.1),
    ]
    changes = {c["metric"]: c["signed_change"] for c in block["issuers"][0]["signed_changes"]}
    assert changes["net_income_usd_bn"] == pytest.approx(-0.75)


def test_authority_is_all_false_and_wording_law_is_carried():
    block = _build([], (A,), eligible_count=1)
    assert block["authority"] == ALL_FALSE_AUTHORITY
    assert block["wording"]["relative_strength"] == \
        "Raw relative strength is not estimated alpha."
    assert block["wording"]["selection_contribution"] == \
        "Positive selection contribution is not evidence of portfolio skill."
    assert "slice_scope_unowned" in block["limitations"]


def test_concentration_hhi_raw_and_per_leave_out():
    rows = [
        _row("evt-a-2026q1", A.cik, 2026, 1, [_fact("revenue_usd_bn", 1.0, "USD_bn", "2026Q1")]),
        _row("evt-b-2026q1", B.cik, 2026, 1, [_fact("revenue_usd_bn", 2.0, "USD_bn", "2026Q1")]),
        _row("evt-c-2026q1", C.cik, 2026, 1, [_fact("revenue_usd_bn", 3.0, "USD_bn", "2026Q1")]),
    ]
    block = _build(rows, (A, B, C), eligible_count=3, aliases=ALIASES)
    # Equal weights over the declared cohort: HHI = 3 * (1/3)^2 = 1/3.
    assert block["concentration"]["method"] == "hhi_over_declared_cohort_equal_weights"
    assert block["concentration"]["hhi"] == pytest.approx(1 / 3)
    assert block["concentration"]["effective_issuer_count"] == 3.0
    # Leave-one-out: two equal remainders, HHI = 1/2 — and the raw figure is
    # not an estimated alpha (wording law above).
    for key in (A.issuer_id, B.issuer_id, C.issuer_id):
        loo = block["leave_issuer_out"][key]
        assert loo["concentration_hhi"] == pytest.approx(0.5)
        assert loo["remaining_count"] == 2
        assert loo["remaining_weight_each"] == pytest.approx(0.5)


def test_dropped_and_unreadable_master_are_typed_never_raised():
    # Unreadable alias master (resolver None): aliases carry the typed unknown.
    block = dict(build_issuer_economics(
        _query(), _bundle([_row("evt-a-2026q1", A.cik, 2026, 1, [])]),
        scope=_scope(A), eligible_count=1, alias_resolver=None,
    ))
    assert block["issuers"][0]["aliases_unknown"] is True
    assert "issuer_aliases_unknown" in block["limitations"]
    # Rights-refused families: named as hidden, never disclosed.
    dropped = _build(
        [_row("evt-a-2026q1", A.cik, 2026, 1, [])], (A,), eligible_count=1, dropped=True,
    )
    assert "rights_refused_families_hidden" in dropped["limitations"]


def test_singleton_cohort_states_its_lack_of_independent_support():
    block = _build(
        [_row("evt-a-2026q1", A.cik, 2026, 1, [_fact("revenue_usd_bn", 1.0, "USD_bn", "2026Q1")])],
        (A,), eligible_count=1, aliases=ALIASES,
    )
    loo = block["leave_issuer_out"][A.issuer_id]
    assert loo["remaining_count"] == 0
    assert loo["remaining_weight_each"] is None
    assert loo["independent_peer_support"] == "none_singleton_cohort"


# ---------------------------------------------------------------------------
# Review follow-ups (2026-11-10, READY WITH FOLLOW-UP at 95aa439d0a8a):
# S1/S2, N1/N3/N4/N5/N6/N7 — each test pins the rule the review found
# untested or broken, and each was mutation-checked in a scratch copy.
# ---------------------------------------------------------------------------


def _raw_fact(metric: str, value: Any, **fields: Any) -> dict[str, Any]:
    """A fact with ONLY the fields the caller states — unlike ``_fact``, no
    default basis/currency/perimeter, so absent-versus-stated is testable."""
    out: dict[str, Any] = {"metric": metric, "value": value}
    out.update(fields)
    return out


def _changes(block: dict[str, Any], index: int = 0) -> list[dict[str, Any]]:
    return list(block["issuers"][index]["signed_changes"])


def test_no_bridge_across_a_missing_period():
    """A missing quarter is a GAP, never a span (review mutation M7: the gap
    rule had no test — allowing ``right - left > 2`` passed every test)."""
    block = _build([
        _row("evt-gap-q1", A.cik, 2026, 1, [_fact("revenue_usd_bn", 10.0, "USD_bn", "2026Q1")]),
        _row("evt-gap-q3", A.cik, 2026, 3, [_fact("revenue_usd_bn", 12.0, "USD_bn", "2026Q3")]),
    ], (A,), eligible_count=1)
    assert _changes(block) == []
    assert block["issuers"][0]["cohort_state"] == "reported_noncomparable"
    # Both original observations are still served verbatim.
    assert sorted(f["value"] for f in block["issuers"][0]["reported"]) == [10.0, 12.0]


def test_the_bridge_never_crosses_basis_currency_perimeter_or_definition():
    """S1: a series is one (metric, unit, basis, currency, perimeter,
    definition) key in the PROJECTOR'S OWN field names. GAAP is never
    subtracted from non-GAAP, a segment from the consolidated company, TWD
    from USD, one definition from another — and a field ABSENT on one fact
    never bridges against the same field STATED on the other."""
    def one_series(first: dict[str, Any], second: dict[str, Any]) -> list[dict[str, Any]]:
        block = _build([
            _row("evt-s1", A.cik, 2026, 1, [first]),
            _row("evt-s2", A.cik, 2026, 2, [second]),
        ], (A,), eligible_count=1)
        return _changes(block)

    assert one_series(
        _raw_fact("eps", 1.0, unit="USD", basis="gaap"),
        _raw_fact("eps", 1.5, unit="USD", basis="non_gaap"),
    ) == []
    assert one_series(
        _raw_fact("rev", 10.0, unit="millions", currency="TWD"),
        _raw_fact("rev", 50.0, unit="millions", currency="USD"),
    ) == []
    assert one_series(
        _raw_fact("rev", 10.0, unit="millions", perimeter="segment_x"),
        _raw_fact("rev", 50.0, unit="millions", perimeter="consolidated"),
    ) == []
    assert one_series(
        _raw_fact("rev", 10.0, unit="millions", definition="as_reported"),
        _raw_fact("rev", 50.0, unit="millions", definition="restated"),
    ) == []
    # Absent on one fact, stated on the other: NOT a match, no bridge.
    assert one_series(
        _raw_fact("rev", 10.0, unit="millions"),
        _raw_fact("rev", 12.0, unit="millions", basis="gaap"),
    ) == []

    # Positive control — the bridge is not dead: the SAME stated series
    # across adjacent periods still differences...
    assert one_series(
        _raw_fact("eps", 1.0, unit="USD", basis="gaap"),
        _raw_fact("eps", 1.5, unit="USD", basis="gaap"),
    ) == [{
        "metric": "eps", "unit": "USD",
        "from_fiscal_period": {"year": 2026, "quarter": 1},
        "to_fiscal_period": {"year": 2026, "quarter": 2},
        "from_value": 1.0, "to_value": 1.5, "signed_change": pytest.approx(0.5),
    }]

    # ...and two bases that EACH span both quarters give two SEPARATE
    # bridges inside their own series — never one cross-basis subtraction.
    both = _build([
        _row("evt-b1", A.cik, 2026, 1, [
            _raw_fact("eps", 1.0, unit="USD", basis="gaap"),
            _raw_fact("eps", 1.2, unit="USD", basis="non_gaap"),
        ]),
        _row("evt-b2", A.cik, 2026, 2, [
            _raw_fact("eps", 1.5, unit="USD", basis="gaap"),
            _raw_fact("eps", 1.6, unit="USD", basis="non_gaap"),
        ]),
    ], (A,), eligible_count=1)
    sorted_changes = sorted(_changes(both), key=lambda c: c["from_value"])
    got = [(c["from_value"], c["to_value"], c["signed_change"])
           for c in sorted_changes]
    assert got[0] == (1.0, 1.5, pytest.approx(0.5))
    assert got[1] == (1.2, 1.6, pytest.approx(0.4))


def test_comparable_requires_an_emitted_change():
    """S2: an issuer is ``comparable`` exactly when the signed bridge emits
    at least one change — never on a mere inspection of shapes. Reported
    facts with no emitted change are reported_noncomparable."""
    def state_and_changes(rows):
        block = _build(rows, (A,), eligible_count=1)
        issuer = block["issuers"][0]
        return block, issuer["cohort_state"], _changes(block)

    # Both bases in ONE period: facts exist, nothing comparable is shown.
    _, state, changes = state_and_changes([
        _row("evt-q1", A.cik, 2026, 1, [
            _raw_fact("eps", 1.0, unit="USD", basis="gaap"),
            _raw_fact("eps", 1.2, unit="USD", basis="non_gaap"),
        ]),
    ])
    assert state == "reported_noncomparable" and changes == []

    # Disagreeing duplicates for one (period, series): ambiguous, no bridge.
    _, state, changes = state_and_changes([
        _row("evt-d1", A.cik, 2026, 1, [_raw_fact("rev", 10.0, unit="USD")]),
        _row("evt-d2", A.cik, 2026, 1, [_raw_fact("rev", 11.0, unit="USD")]),
        _row("evt-d3", A.cik, 2026, 2, [_raw_fact("rev", 12.0, unit="USD")]),
    ])
    assert state == "reported_noncomparable" and changes == []

    # String numbers / None values: not reported numbers, no bridge.
    for bad in ("10", None):
        _, state, changes = state_and_changes([
            _row("evt-s1", A.cik, 2026, 1, [_raw_fact("rev", bad, unit="USD")]),
            _row("evt-s2", A.cik, 2026, 2, [_raw_fact("rev", 12.0, unit="USD")]),
        ])
        assert state == "reported_noncomparable" and changes == []

    # And the one rule's positive side: one emitted change → comparable.
    block, state, changes = state_and_changes([
        _row("evt-p1", A.cik, 2026, 1, [_fact("revenue_usd_bn", 10.0, "USD_bn", "2026Q1")]),
        _row("evt-p2", A.cik, 2026, 2, [_fact("revenue_usd_bn", 11.0, "USD_bn", "2026Q2")]),
    ])
    assert state == "comparable" and changes
    assert block["cohort"]["comparable"] == 1


def test_non_string_or_missing_identity_cik_is_a_typed_unknown():
    """N1: a non-string (int) or missing (None) identity CIK can match no
    row — a typed unknown stated in limitations, never a TypeError — and a
    row literally carrying the string "None" is NOT matched to a CIK-less
    identity either."""
    int_cik = SimpleNamespace(
        ticker="AAA", company_node_id="co:synth_a",
        issuer_id="ISS:SYN-A", cik=1,
    )
    none_cik = SimpleNamespace(
        ticker="AAA2", company_node_id="co:synth_a2",
        issuer_id="ISS:SYN-A2", cik=None,
    )
    rows = [
        _row("evt-a", A.cik, 2026, 1, [_fact("revenue_usd_bn", 1.0, "USD_bn", "2026Q1")]),
        {"event_id": "evt-none", "cik": "None",
         "fiscal_period": {"year": 2026, "quarter": 1},
         "reported": [_fact("revenue_usd_bn", 2.0, "USD_bn", "2026Q1")],
         "omissions": []},
    ]
    block = dict(build_issuer_economics(
        _query(), _bundle(rows),
        scope=WitnessScope(
            slice_key="hbm_packaging",
            identities=(int_cik, none_cik),
            omissions=("slice_scope_unowned",),
        ),
        eligible_count=2, alias_resolver=None,
    ))
    # Every issuer is honestly unreported; no row was attributed to either.
    assert all(i["row_count"] == 0 for i in block["issuers"])
    assert "identity_cik_not_string:2" in block["limitations"]
    assert "unattributed_workspace_rows:2" in block["limitations"]
    assert block["cohort"] == {
        "eligible": 2, "identified": 2, "reported": 0,
        "comparable": 0, "unknown": 2, "noncomparable": 0,
        "denominator_rule": block["cohort"]["denominator_rule"],
    }


def test_non_finite_values_are_refused_by_this_modules_own_check():
    """N3: NaN and infinity are not reported numbers — refused HERE, not by
    trusting the projector upstream — so the block is finite JSON by this
    module's own check and the refusal is displayed, never silent."""
    for bad in (float("nan"), float("inf"), float("-inf")):
        block = _build([
            _row("evt-f1", A.cik, 2026, 1, [_raw_fact("rev", bad, unit="USD")]),
            _row("evt-f2", A.cik, 2026, 2, [_raw_fact("rev", 1.0, unit="USD")]),
        ], (A,), eligible_count=1)
        json.dumps(block, allow_nan=False)  # finite JSON: raises ValueError if not
        issuer = block["issuers"][0]
        assert [f["value"] for f in issuer["reported"]] == [1.0]
        assert "reported_non_finite:rev" in issuer["unknowns"]
        assert _changes(block) == []
        assert issuer["cohort_state"] == "reported_noncomparable"


def test_lineage_strips_whitespace_counts_unrooted_and_states_its_rule():
    """N4: the family key is the event id with surrounding whitespace
    stripped (no case folding); a row with facts but no event id is counted
    in ``unrooted_rows``; the block states that families are distinct event
    ids."""
    stripped = _build([
        _row("ACC-0001", A.cik, 2026, 1, [_fact("revenue_usd_bn", 1.0, "USD_bn", "2026Q1")]),
        _row("ACC-0001 ", A.cik, 2026, 1, [_fact("revenue_usd_bn", 1.0, "USD_bn", "2026Q1")]),
    ], (A,), eligible_count=1)
    assert stripped["lineage"]["family_count"] == 1
    assert stripped["lineage"]["unrooted_rows"] == 0

    # No case folding: these two stay TWO families.
    cased = _build([
        _row("acc-0001", A.cik, 2026, 1, [_fact("revenue_usd_bn", 1.0, "USD_bn", "2026Q1")]),
        _row("ACC-0001", A.cik, 2026, 1, [_fact("revenue_usd_bn", 1.0, "USD_bn", "2026Q1")]),
    ], (A,), eligible_count=1)
    assert cased["lineage"]["family_count"] == 2

    unrooted = _build([
        {"cik": A.cik, "fiscal_period": {"year": 2026, "quarter": 1},
         "reported": [_fact("revenue_usd_bn", 1.0, "USD_bn", "2026Q1")], "omissions": []},
    ], (A,), eligible_count=1)
    lineage = unrooted["lineage"]
    assert lineage["family_count"] == 0
    assert lineage["item_count"] == 0
    assert lineage["unrooted_rows"] == 1
    assert lineage["family_rule"] == (
        "families are distinct event ids; two workspaces citing one filing "
        "under different ids are not detected"
    )
    # The facts the unrooted row carried are still served.
    assert unrooted["issuers"][0]["row_count"] == 1


def test_leave_out_peers_are_other_cohort_members_only():
    """N5: peers are the rows attributed to OTHER cohort members — not
    "every row whose CIK differs". CIKs compare as ten-digit zero-padded
    strings (an unpadded row belongs to its issuer), and a row belonging to
    no cohort member is not a peer: counted separately and stated."""
    rows = [
        _row("evt-a", A.cik, 2026, 1, [_fact("revenue_usd_bn", 10.0, "USD_bn", "2026Q1")]),
        # A's own row served with an UNPADDED CIK: still A's, never a peer.
        _row("evt-a-unpadded", "10", 2026, 1, [_fact("revenue_usd_bn", 10.0, "USD_bn", "2026Q1")]),
        _row("evt-b", B.cik, 2026, 1, [_fact("revenue_usd_bn", 7.0, "USD_bn", "2026Q1")]),
        # Belongs to NO cohort member: not a peer of anyone.
        _row("evt-x", "0000000009", 2026, 1, [_fact("revenue_usd_bn", 3.0, "USD_bn", "2026Q1")]),
    ]
    block = _build(rows, (A, B), eligible_count=2, aliases=ALIASES)
    states = {i["issuer_id"]: i for i in block["issuers"]}
    # The unpadded row was attributed to A through zero-padded comparison.
    assert states["ISS:SYN-A"]["row_count"] == 2
    loo_a = block["leave_issuer_out"]["ISS:SYN-A"]
    loo_b = block["leave_issuer_out"]["ISS:SYN-B"]
    # Peers of A: exactly B's one row. Peers of B: exactly A's two rows.
    assert loo_a["peer_evidence_rows"] == 1
    assert loo_b["peer_evidence_rows"] == 2
    assert loo_a["peer_lineage"]["families"] == [["evt-b"]]
    # The non-cohort row is stated, never folded into peer evidence.
    assert "unattributed_workspace_rows:1" in block["limitations"]


def test_denominators_add_up_or_say_they_cannot():
    """N6: ``unknown = eligible - reported`` is stated in the block and the
    published counts always satisfy ``reported + unknown = eligible``; each
    issuer is counted once; when the inputs make the sum impossible the
    block is the typed inconsistent form with raw inputs and NULL derived
    counts."""
    # The rule is stated.
    assert "unknown = eligible - reported" in _build([], (A,), eligible_count=1)\
        ["cohort"]["denominator_rule"]

    # Two identities sharing one issuer id are ONE issuer, counted once,
    # and the sums still hold.
    a2 = _identity("AAA2", "ISS:SYN-A", "0000000010")
    dup = _build(
        [_row("evt-a", A.cik, 2026, 1, [_fact("revenue_usd_bn", 1.0, "USD_bn", "2026Q1")])],
        (A, a2), eligible_count=2,
    )
    assert len(dup["issuers"]) == 1
    assert dup["cohort"]["identified"] == 1
    assert dup["cohort"]["reported"] + dup["cohort"]["unknown"] \
        == dup["cohort"]["eligible"] == 2

    # More reporting issuers than eligible: the sum is impossible — the
    # typed inconsistent form, never counts that fail the sum.
    inconsistent = _build([
        _row("evt-a", A.cik, 2026, 1, [_fact("revenue_usd_bn", 1.0, "USD_bn", "2026Q1")]),
        _row("evt-b", B.cik, 2026, 1, [_fact("revenue_usd_bn", 1.0, "USD_bn", "2026Q1")]),
        _row("evt-c", C.cik, 2026, 1, [_fact("revenue_usd_bn", 1.0, "USD_bn", "2026Q1")]),
    ], (A, B, C), eligible_count=2)
    assert inconsistent["state"] == "cohort_counts_inconsistent"
    cohort = inconsistent["cohort"]
    assert cohort["eligible"] == 2 and cohort["reported"] == 3
    assert cohort["unknown"] is None and cohort["comparable"] is None
    assert cohort["noncomparable"] is None
    assert cohort["inconsistency"] == "reported_exceeds_eligible"
    assert inconsistent["leave_issuer_out"] is None
    assert inconsistent["concentration"]["state"] \
        == "unavailable_cohort_counts_inconsistent"
    assert inconsistent["authority"] == ALL_FALSE_AUTHORITY
    json.dumps(inconsistent, allow_nan=False)

    # A negative eligible is impossible the other way: also typed, never -1.
    negative = _build([], (), eligible_count=-1)
    assert negative["state"] == "cohort_counts_inconsistent"
    assert negative["cohort"]["inconsistency"] == "eligible_is_negative"


def test_concentration_states_its_weighting_and_degrades_typed():
    """N7: the arithmetic and key names stay; the equal-over-declared-cohort
    weighting is STATED with one wording line, and a zero eligible gives the
    typed unavailable form — never a number."""
    block = _build([], (A,), eligible_count=3)
    conc = block["concentration"]
    assert conc["method"] == "hhi_over_declared_cohort_equal_weights"
    assert conc["weighting"] == "equal_over_declared_cohort"
    assert conc["weighting_note"] == (
        "The concentration figure is equal weights over the declared cohort, "
        "so it measures cohort size, not economic concentration."
    )
    assert conc["hhi"] == pytest.approx(1 / 3)
    assert conc["effective_issuer_count"] == 3.0

    zero = _build([], (), eligible_count=0)
    assert zero["concentration"]["state"] == "unavailable_eligible_not_positive"
    assert "hhi" not in zero["concentration"]
    assert "effective_issuer_count" not in zero["concentration"]
    # A singleton leave-out still says so, typed, never -1.
    singleton = _build([], (A,), eligible_count=0)
    loo = singleton["leave_issuer_out"]["ISS:SYN-A"]
    assert loo["remaining_count"] == 0
    assert loo["remaining_weight_each"] is None
    assert loo["independent_peer_support"] == "none_singleton_cohort"


# ---------------------------------------------------------------------------
# REAL alias enumeration — presence-gated on the committed security master
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not REAL_MASTER_PATH.is_file(),
    reason="real data/reference/security_master.parquet is not materialized "
           "in this checkout (sparse worktree profile excludes data/)",
)
def test_real_security_master_alias_enumeration():
    """REAL evidence, gated on file presence: the Data OS master's own
    ``securities_of_issuer`` enumeration — the §9.7 canonical alias query —
    flows through the block unchanged, as both the issuer's ``aliases`` and
    the leave-issuer-out ``removed_aliases``."""
    pd = pytest.importorskip("pandas")
    from lib.dataos.identity import IssuerMaster

    records = pd.read_parquet(REAL_MASTER_PATH).to_dict("records")
    master = IssuerMaster.from_records(records)

    # A probe issuer: active, with an UNAMBIGUOUS ten-digit current CIK and a
    # non-empty canonical security roster. Ambiguous-CIK issuers are refused
    # by the master itself; the walk skips them rather than guessing.
    def _probe() -> tuple[str, str]:
        for row in master.rows:
            if not row.issuer_id or row.security_state:
                continue
            try:
                cik = master.cik_of_issuer(row.issuer_id)
            except Exception:  # noqa: BLE001 — ambiguity is a typed refusal, skip it
                continue
            if isinstance(cik, str) and len(cik) == 10 \
                    and master.securities_of_issuer(row.issuer_id):
                return row.issuer_id, cik
        pytest.fail("no unambiguous ten-digit-CIK issuer in the real master")

    probe_issuer, probe_cik = _probe()
    aliases = master.securities_of_issuer(probe_issuer)
    assert aliases and list(aliases) == sorted(aliases)
    for security_id in aliases:
        assert master.issuer_of_security(security_id) == probe_issuer

    identity = WitnessIdentity(
        ticker="REAL-PROBE", company_node_id="co:real_probe",
        issuer_id=probe_issuer, cik=probe_cik,
    )
    block = dict(build_issuer_economics(
        _query(),
        _bundle([_row("evt-real-probe", identity.cik, 2026, 2,
                      [_fact("revenue_usd_bn", 1.0, "USD_bn", "2026Q2")])]),
        scope=_scope(identity),
        eligible_count=1,
        alias_resolver=master.securities_of_issuer,
    ))
    issuer = block["issuers"][0]
    assert tuple(issuer["aliases"]) == aliases
    assert issuer["aliases_unknown"] is False
    assert tuple(block["leave_issuer_out"][probe_issuer]["removed_aliases"]) == aliases
