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
