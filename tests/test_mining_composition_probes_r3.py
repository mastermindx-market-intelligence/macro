"""Round-3 adversarial probes for the T04a Mining composition (frozen at 94e74dd8).

PROVENANCE. Rounds 1 and 2 were rejected by an independent Opus red-team, and their
probes are frozen in ``test_mining_composition_probes.py`` / ``_probes_r2.py``. Round 3
delivered a module that passes all of those. This file is the round-3 attack: it was
authored by the SEAT (the fabric had had three rounds) from a live adversarial battery
run against head 94e74dd8, and its scope and severity were then adjudicated by an
independent read-only Opus auditor that saw the code and the measured outputs but was
given no authority to edit anything. Two of the findings below (R3-7 non-finite values,
and the F2 oracle gap pinned by R3-8) are the auditor's, not the seat's.

FREEZE DISCIPLINE. This file is committed RED, before the repair, exactly as a
reviewer's probes would be. The repair may not edit this file, the two earlier probe
files, the truth table, or the fixtures.

WHAT THE DEFECT PROBES SHARE. Every one of them is the same shape: the module accepts a
packet field, never reads it, and therefore publishes a confident economic assertion the
input does not support — with ``limitations`` empty, so a consumer cannot detect it. That
is strictly worse than the fabrication that got rounds 1 and 2 rejected, which at least
left the response's own limitation vocabulary intact. The lawful response to an input
that cannot be truthfully compared is to WITHHOLD the row and mint
``omitted:expectations``; the schema pins ``comparison`` to ``minLength: 1``, so a row
without a comparison word is not representable and withholding is the only legal option.
"""
from __future__ import annotations

import dataclasses
import math

from engine.market_ontology import mining_theme_research as composition
from tests.mining_casebook import synthetic_case

NAN = float("nan")
INF = float("inf")


def _leg(value, *, unit="Mlbs", perimeter="consolidated", basis="reported", period="Q2 2026"):
    return {
        "value": value,
        "unit": unit,
        "perimeter": perimeter,
        "basis": basis,
        "period": period,
    }


def _packet(pair, epe, la, **extra):
    packet = {
        "kind": "management_estimate_vs_actual",
        "pair": pair,
        "earlier_point_estimate": epe,
        "later_actual": la,
    }
    packet.update(extra)
    return packet


def _compose(*packets):
    """Compose the usable copper case with exactly the given in-test packets."""
    case = synthetic_case("copper_complete")
    bundle = dataclasses.replace(case.bundle, financial_packets=tuple(packets))
    return composition.compose_mining_research(case.query, bundle)


def _rows(result):
    return result.get("expectations") or []


def _metric_pairs(result):
    return {
        (row["earlier_point_estimate"]["metric"], row["later_actual"]["metric"])
        for row in _rows(result)
    }


# ---------------------------------------------------------------- R3-1 duplicates


def test_probe_r3_duplicate_pair_withholds_every_contradicting_row():
    """BLOCKER R3-1: two packets naming the same ``pair`` must not both be published.

    A leg's metric/basis/source_label come from the domain yaml keyed by the pair name,
    and no packet field other than ``value`` reaches the wire, so two packets with the
    same pair name produce two rows that are IDENTICAL in identity and differ only in
    value. Nothing on the wire can disambiguate them: the response asserts that the same
    metric, for the same issuer, in the same period, was both 1700 and 9999.

    Picking one is fabrication by arbitration (nothing in the input ranks them), and
    emitting both with a limitation does not help because a limitation annotates, it
    never retracts. Both rows are therefore withheld and the pair is marked omitted.
    """
    result = _compose(
        _packet("sales", _leg(1700), _leg(1680)),
        _packet("sales", _leg(9999), _leg(1)),
    )
    assert _rows(result) == [], (
        "a duplicated pair name published contradictory rows: "
        f"{[(r['earlier_point_estimate']['value'], r['later_actual']['value']) for r in _rows(result)]}"
    )
    assert "omitted:expectations" in result["limitations"], result["limitations"]


def test_probe_r3_duplicate_pair_does_not_suppress_an_unrelated_pair():
    """BLOCKER R3-1 (scope): the withhold is per pair, never a whole-channel blackout.

    A duplicated ``sales`` says nothing about ``unit_net_cash_cost``; suppressing a
    perfectly good cost comparison would be its own truth loss.
    """
    result = _compose(
        _packet("sales", _leg(1700), _leg(1680)),
        _packet("sales", _leg(9999), _leg(1)),
        _packet("unit_net_cash_cost", _leg(1.55, unit="USD/lb"), _leg(1.62, unit="USD/lb")),
    )
    assert len(_rows(result)) == 1, _metric_pairs(result)
    assert _metric_pairs(result) == {
        ("management_issued_copper_unit_net_cash_cost_estimate", "copper_unit_net_cash_cost")
    }
    assert "omitted:expectations" in result["limitations"], result["limitations"]


# ------------------------------------------------------- R3-2 range / consensus


def test_probe_r3_a_declared_range_or_consensus_is_refused():
    """BLOCKER R3-2: ``is_range``/``is_consensus`` must be READ, not hardcoded false.

    The response schema pins both to ``const: false``, so a range or a consensus is not
    representable on this wire at all — and the domain law is that a point estimate is
    never a range and never a consensus. Flattening a source-declared range into
    ``is_range: false`` beside ``comparison_kind:
    earlier_point_estimate_vs_later_actual`` publishes a point-estimate claim about a
    value the source said was a range. The only truthful option is refusal, exactly as a
    structurally range-shaped value is already refused.
    """
    for flag in ("is_range", "is_consensus"):
        result = _compose(_packet("sales", _leg(1700), _leg(1680), **{flag: True}))
        assert _rows(result) == [], f"a packet declaring {flag}=True was published as a point estimate"
        assert "omitted:expectations" in result["limitations"], (flag, result["limitations"])


def test_probe_r3_a_declared_range_on_a_single_leg_is_refused():
    """BLOCKER R3-2: the declaration may sit on either leg, not only on the packet."""
    for leg_key in ("earlier_point_estimate", "later_actual"):
        packet = _packet("sales", _leg(1700), _leg(1680))
        packet[leg_key] = dict(packet[leg_key], is_range=True)
        result = _compose(packet)
        assert _rows(result) == [], f"a range declared on {leg_key} was published as a point estimate"
        assert "omitted:expectations" in result["limitations"], (leg_key, result["limitations"])


def test_probe_r3_absent_flags_still_compose_so_false_is_earned_not_assumed():
    """BLOCKER R3-2 (oracle, auditor finding F1): distinguish a READ false from a CONSTANT.

    Pinning ``is_range is False`` against inputs that are never ranges cannot tell a
    field that was read from a field that is hardcoded. This pair of assertions can: an
    absent declaration still composes (absence means "not a range", which is the
    default), while a present declaration refuses. Only a module that actually reads the
    field satisfies both.
    """
    composed = _compose(_packet("sales", _leg(1700), _leg(1680)))
    assert len(_rows(composed)) == 1
    assert composed["expectations"][0]["is_range"] is False
    assert composed["expectations"][0]["is_consensus"] is False


# --------------------------------------------------- R3-3..R3-6 comparability


def test_probe_r3_a_unit_mismatch_is_refused():
    """BLOCKER R3-3: polarity across incommensurate units is arithmetically false.

    1680 kt is roughly 3,700 Mlbs, so an actual of ``1680 kt`` against an estimate of
    ``1700 Mlbs`` exceeded the estimate about twofold — while ``la_value > epe_value``
    compares the numerals and publishes ``below_estimate``. The frozen domain spec
    requires "fully qualified COMPATIBLE inputs are compared normally"; compatibility is
    a clause distinct from the qualification (presence) check the module already does.
    Unit CONVERSION belongs to the producer task; unit EQUALITY belongs to this line.
    """
    result = _compose(_packet("sales", _leg(1700, unit="Mlbs"), _leg(1680, unit="kt")))
    assert _rows(result) == [], "compared 1700 Mlbs against 1680 kt"
    assert "omitted:expectations" in result["limitations"], result["limitations"]


def test_probe_r3_a_perimeter_mismatch_is_refused():
    """BLOCKER R3-4: consolidated and proportionate figures are never mixed.

    The domain law names this case by name. Two falsehoods ship without the guard: the
    polarity is computed across incommensurable perimeters, and because the actual leg's
    metric arrives from the domain yaml as ``consolidated_copper_sales``, a proportionate
    figure is LABELLED consolidated — false even to a reader who ignores the comparison.
    """
    result = _compose(
        _packet("sales", _leg(1700, perimeter="consolidated"), _leg(1680, perimeter="proportionate"))
    )
    assert _rows(result) == [], "compared a consolidated estimate against a proportionate actual"
    assert "omitted:expectations" in result["limitations"], result["limitations"]


def test_probe_r3_a_period_mismatch_is_refused():
    """MAJOR R3-5: a ``later_actual`` may not carry a period before the estimate's.

    P7 of the seat battery compared a ``Q1 2026`` estimate against a ``Q4 2025`` actual
    and published ``below_estimate`` — while the row simultaneously asserts
    ``comparison_kind: earlier_point_estimate_vs_later_actual``, a temporal relation the
    input contradicts. Both of this slice's legs are ``period_kind: quarter`` in M1, so
    string equality is the right M1 predicate; a real period comparator (FY guidance
    against a quarterly actual) is the producer task's widening, and is the reason this
    is a MAJOR rather than a BLOCKER.
    """
    result = _compose(
        _packet("sales", _leg(1700, period="Q1 2026"), _leg(1680, period="Q4 2025"))
    )
    assert _rows(result) == [], "compared a Q1 2026 estimate against a Q4 2025 actual"
    assert "omitted:expectations" in result["limitations"], result["limitations"]


def test_probe_r3_basis_may_differ_between_the_two_legs_by_design():
    """NOT-A-DEFECT, pinned so a later session does not "fix" it into a red.

    The independent auditor ruled that ``basis`` should be cross-leg compared like unit
    and perimeter. The seat departs from that one ruling on evidence: the domain yaml
    gives the two legs DIFFERENT bases on purpose (``fictional point estimate`` against
    ``fictional reported measure``), because an estimate and a reported actual are
    definitionally different bases. Cross-leg basis equality would therefore forbid the
    only comparison this slice exists to make. ``basis`` stays in
    ``definition_fields_required`` as a PRESENCE token — the domain owns the published
    label. Rejecting a producer's divergent basis at intake is the producer task's work.
    """
    result = _compose(
        _packet("sales", _leg(1700, basis="reported"), _leg(1680, basis="reported"))
    )
    assert len(_rows(result)) == 1
    row = result["expectations"][0]
    assert row["earlier_point_estimate"]["basis"] != row["later_actual"]["basis"], row


# ------------------------------------------------------- R3-7 non-finite values


def test_probe_r3_non_finite_values_are_refused():
    """MAJOR R3-7 (auditor finding): NaN and infinity are the hole in the numeric guard.

    ``isinstance(float("nan"), float)`` is True, so NaN passes the numeric gate; and
    ``nan == nan`` is False, so it also slips the equality withhold. Every NaN comparison
    is False, so execution reaches the ternary's else branch and publishes a confident
    ``below_estimate`` carrying ``nan`` as an economic value with no limitation at all —
    including for a NaN-against-NaN pair, where even the equality guard should have
    fired. Infinity publishes ``above_estimate`` the same way.
    """
    for label, epe, la in (
        ("nan actual", 1700, NAN),
        ("nan estimate", NAN, 1680),
        ("nan both", NAN, NAN),
        ("positive infinity", 1700, INF),
        ("negative infinity", 1700, -INF),
    ):
        result = _compose(_packet("sales", _leg(epe), _leg(la)))
        assert _rows(result) == [], f"{label} was published as a comparison"
        assert "omitted:expectations" in result["limitations"], (label, result["limitations"])


def test_probe_r3_the_numeric_guard_admits_only_finite_reals():
    """MAJOR R3-7: pin the predicate itself, so the guard cannot regress quietly."""
    for bad in (NAN, INF, -INF):
        assert not composition._value_is_numeric(bad), bad
    for good in (0, -1, 1700, 1.55, -2.5):
        assert composition._value_is_numeric(good), good
        assert math.isfinite(good)


# ------------------------------------------- R3-8 polarity regression (F2 killer)


def test_probe_r3_polarity_follows_the_numbers_in_both_directions():
    """REGRESSION PIN R3-8 (auditor finding F2 — a hole in the SEAT's own oracle).

    The round-1 probe as amended supplies exactly one value pair per pair name with
    exactly one expected polarity, so a module could satisfy every pin with
    ``{"sales": "below_estimate", "unit_net_cash_cost": "above_estimate"}[pair]`` and
    never execute a comparison — round-2's letter-gaming surviving the round-3 oracle.
    Reversing the values per pair makes the expected polarity flip, which no per-pair
    lookup table can reproduce. The module at 94e74dd8 already passes this; the pin
    exists so it cannot stop passing.
    """
    cases = (
        ("sales", "Mlbs", 1700, 1680, "below_estimate"),
        ("sales", "Mlbs", 1680, 1700, "above_estimate"),
        ("unit_net_cash_cost", "USD/lb", 1.55, 1.62, "above_estimate"),
        ("unit_net_cash_cost", "USD/lb", 1.62, 1.55, "below_estimate"),
    )
    for pair, unit, epe, la, expected in cases:
        result = _compose(_packet(pair, _leg(epe, unit=unit), _leg(la, unit=unit)))
        rows = _rows(result)
        assert len(rows) == 1, (pair, epe, la, result["limitations"])
        assert rows[0]["earlier_point_estimate"]["value"] == epe
        assert rows[0]["later_actual"]["value"] == la
        assert rows[0]["comparison"] == expected, (pair, epe, la, rows[0]["comparison"])


def test_probe_r3_both_pairs_still_compose_after_the_guards():
    """REGRESSION PIN: the guards must not cost the channel its real comparisons."""
    result = _compose(
        _packet("unit_net_cash_cost", _leg(1.55, unit="USD/lb"), _leg(1.62, unit="USD/lb")),
        _packet("sales", _leg(1700), _leg(1680)),
    )
    rows = _rows(result)
    assert len(rows) == 2, result["limitations"]
    assert [row["comparison"] for row in rows] == ["below_estimate", "above_estimate"]
    assert "omitted:expectations" not in result["limitations"], result["limitations"]
