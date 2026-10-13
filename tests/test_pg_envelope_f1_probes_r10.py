"""CDV-1 T1 F1-Q envelope — frozen R10 witness (seat-frozen after the independent Opus audit R10 of 6caa2ffc1a95).

Every case tampers a workspace built from a frozen gzipped FY26 Q1-Q3 original, or an argument handed to the validator
with it, and asserts the outcome that the seat rulings R116-R194 and R195-R197 require.  Group A accepted.  Group B
found R193's walk admitting a Fraction by its exact type and never checking the two parts the type only promises: a
part that is not a number raised TypeError in the walk itself, a zero denominator raised ZeroDivisionError where the
value is read as a real number, and an int subclass with a hostile __str__ raised where the fiscal period is printed
(B-R10-B1).  It found an exact list or dict, read as a document id on the non-envelope route, raising TypeError
(unhashable) before the test of its type (B-R10-B2).  Both are R193's class: a value raises where the validator reads
it instead of being refused.

R195 admits an int or a Fraction only in the form Python builds one, and has the walk and the entry decide by identity
alone, so no argument runs code of its own, not even through its class's metaclass.  R196 has the public entry turn
the exceptions a built-in operation raises about a value's type or range into the refusal they stand for, and nothing
else.  R197 freezes this file.

The findings' constructions and controls are group B's; the seat sharpened the controls to the refusal each one
meets.  The seat added R195's other parts and forms, the values whose class or metaclass
carries code, the arguments' cases and the fiscal_scope forms, and R196's contract cases, which raise inside the body
from the pg_profile helper it calls once the entry's checks pass.  Every other case drives the public path.

Rulings: research/consumer_defensive/cdv1_program/reviews/SEAT_RULING_T1_ENVELOPE_R10_2026-09-29.md.
Audit record: research/consumer_defensive/cdv1_program/reviews/OPUS_T1_ENVELOPE_AUDIT_R10_2026-09-29.md.
"""
from __future__ import annotations

import collections
import copy
import enum
import json
import sys
import types
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_pg_envelope_f1_probes_r4 as r4  # noqa: E402
import test_pg_envelope_f1_probes_r7 as r7  # noqa: E402
import test_pg_envelope_f1_probes_r9 as r9  # noqa: E402
from engine.company_intelligence import economic_observations as eo  # noqa: E402
from engine.company_intelligence.economic_observations import EconomicObservationError  # noqa: E402

REL = r4.REL
QUARTERS = sorted(REL)
refused, present_row = r7.refused, r7.present_row
fresh, UNPRINTABLE, NOT_TEXT = r9.fresh, r9.UNPRINTABLE, r9.NOT_TEXT
NOT_MAPPING = "workspace must be a mapping"
NOT_DATES = "fiscal_scope must contain four ISO dates"
UNREADABLE = "a value has the wrong type or range where the validator reads it"

def validate(ws, texts, scope):
    return eo.validate_selected_facts(ws, source_texts=texts, fiscal_scope=scope)


class Boom(Exception):
    """What code a tampered value carries raises; the validator must refuse the value before that code runs."""


def _boom(*_args):
    raise Boom("a value's own code ran inside the validator")


# ============================ R195 (B-R10-B1): a number holds the parts its type promises
def _fraction(numerator, denominator):
    """Group B's construction: an object of exact type Fraction whose two slots hold what they were assigned."""
    value = Fraction(1, 3)
    value._numerator, value._denominator = numerator, denominator
    assert type(value) is Fraction
    return value


class _HostileStrInt(int):
    """Group B's int subclass: printing it raises."""

    def __str__(self):
        raise RuntimeError("hostile __str__")

    __repr__ = __str__


NOT_INT_PARTS = {
    "numerator_none": lambda: _fraction(None, 1),
    "numerator_str": lambda: _fraction("1", 1),
    "denominator_none": lambda: _fraction(1, None),
    "numerator_list": lambda: _fraction([], 1),
    # seat
    "numerator_bool": lambda: _fraction(True, 1),
    "numerator_float": lambda: _fraction(1.0, 1),
    "denominator_nan": lambda: _fraction(1, float("nan")),
    "numerator_int_subclass": lambda: _fraction(_HostileStrInt(3), 1),
}


@pytest.mark.parametrize("q", QUARTERS)
@pytest.mark.parametrize("where", ["fiscal_period.quarter", "event_id", "claims"])
@pytest.mark.parametrize("kind", sorted(NOT_INT_PARTS))
def test_r195_a_fraction_whose_parts_are_not_exact_ints_is_refused_at_the_entry(q, where, kind):
    """B-R10-B1 (i): R193's walk admitted the Fraction by its exact type and read abs(numerator), so a part that is not a
    number raised TypeError in the walk itself, and a number of another type went on to the value checks."""
    ws, texts = fresh(q)
    value = NOT_INT_PARTS[kind]()
    if where == "fiscal_period.quarter":
        ws["fiscal_period"]["quarter"] = value
    elif where == "event_id":
        ws["event_id"] = value
    else:
        ws["claims"] = [value]
    refused(ws, texts, q, UNPRINTABLE)


NOT_CANONICAL = {
    "zero_denominator": lambda: _fraction(1, 0),
    # seat
    "negative_denominator": lambda: _fraction(1, -3),
    "not_in_lowest_terms": lambda: _fraction(2, 4),
}


@pytest.mark.parametrize("q", QUARTERS)
@pytest.mark.parametrize("kind", sorted(NOT_CANONICAL))
def test_r195_a_fraction_python_would_not_build_is_refused_at_the_entry(q, kind):
    """B-R10-B1 (ii): a zero denominator passed the walk and raised ZeroDivisionError where the value is read as a real
    number.  The seat's two other forms Python never builds compare and hash unlike the number they denote."""
    ws, texts = fresh(q)
    present_row(ws)["value"] = NOT_CANONICAL[kind]()
    refused(ws, texts, q, UNPRINTABLE)


@pytest.mark.parametrize("q", QUARTERS)
@pytest.mark.parametrize("field", ["quarter", "year"])
def test_r195_an_int_subclass_part_is_refused_before_anything_prints_it(q, field):
    """B-R10-B1 (iii): an int subclass with a hostile __str__, as a Fraction's numerator, passed the walk and raised where
    the fiscal period is printed."""
    ws, texts = fresh(q)
    ws["fiscal_period"][field] = _fraction(_HostileStrInt(3), 1)
    refused(ws, texts, q, UNPRINTABLE)


# Seat: a value whose class, or whose class's metaclass, defines what a test of its type would ask it.
def _metaclass_instance(name, **methods):
    return type(name, (type,), methods)(name + "Instance", (), {})()


CARRIES_CODE = {
    "metaclass_hash": lambda: _metaclass_instance("HashMeta", __hash__=_boom),
    "metaclass_eq": lambda: _metaclass_instance("EqMeta", __eq__=_boom, __hash__=lambda cls: hash(float)),
    "metaclass_class": lambda: _metaclass_instance("ClassMeta", __class__=property(_boom)),
    "instance_class": lambda: type("InstanceClass", (), {"__class__": property(_boom)})(),
}


@pytest.mark.parametrize("q", QUARTERS)
@pytest.mark.parametrize("kind", sorted(CARRIES_CODE))
def test_r195_a_value_whose_class_carries_code_is_refused_without_running_it(q, kind):
    """Seat: R193's walk tested its leaves by membership in a set of types, which hashes the value's class and may
    compare it, and a metaclass defines both.  The walk now decides by identity, so the value is refused unrun."""
    ws, texts = fresh(q)
    ws["fiscal_period"]["quarter"] = CARRIES_CODE[kind]()
    refused(ws, texts, q, UNPRINTABLE)


@pytest.mark.parametrize("q", QUARTERS)
@pytest.mark.parametrize("kind", sorted(CARRIES_CODE))
@pytest.mark.parametrize("argument", ["workspace", "source_texts", "fiscal_scope"])
def test_r195_an_argument_whose_class_carries_code_is_refused_without_running_it(q, kind, argument):
    """Seat: the entry tested the workspace and source_texts with isinstance against typing.Mapping, which asks the
    argument's class for its __class__ and hashes it, and fiscal_scope with isinstance against tuple, which asks the
    argument for its __class__.  It now reads each argument by its exact type before any other test."""
    ws, texts = fresh(q)
    value = CARRIES_CODE[kind]()
    expected = {"workspace": UNPRINTABLE, "source_texts": NOT_TEXT, "fiscal_scope": NOT_DATES}[argument]
    with pytest.raises(EconomicObservationError, match=expected):
        validate(
            value if argument == "workspace" else ws,
            value if argument == "source_texts" else texts,
            value if argument == "fiscal_scope" else REL[q].scope,
        )


def _scope_form(kind, scope):
    return {
        "named_tuple": lambda: collections.namedtuple("Scope", "start end prior_start prior_end")(*scope),
        "list": lambda: list(scope),
        "str_subclass_date": lambda: (enum.StrEnum("Start", {"S": scope[0]}).S, *scope[1:]),
        "three_dates": lambda: tuple(scope[:3]),
    }[kind]()


@pytest.mark.parametrize("q", QUARTERS)
@pytest.mark.parametrize("kind", ["named_tuple", "list", "str_subclass_date", "three_dates"])
def test_r195_fiscal_scope_is_an_exact_tuple_of_four_str(q, kind):
    """Seat: fiscal_scope is read as R193 reads source_texts, by exact type: a tuple of four str.  A tuple subclass and a
    str subclass, which isinstance admitted, are refused like a list and a short tuple."""
    ws, texts = fresh(q)
    with pytest.raises(EconomicObservationError, match=NOT_DATES):
        validate(ws, texts, _scope_form(kind, REL[q].scope))


NOT_A_DICT = {
    "list": lambda texts: list(texts.items()),
    "none": lambda texts: None,
    "text": lambda texts: next(iter(texts.values())),
    "mapping_proxy": lambda texts: types.MappingProxyType(dict(texts)),
}


@pytest.mark.parametrize("q", QUARTERS)
@pytest.mark.parametrize("kind", sorted(NOT_A_DICT))
def test_r195_source_texts_that_are_not_a_dict_are_refused_as_not_text(q, kind):
    """Seat: source_texts are read only by their exact type, so every value that is not a dict of str to str takes R193's
    refusal; the separate isinstance test, and its message that source_texts must be a mapping, are gone."""
    ws, texts = fresh(q)
    with pytest.raises(EconomicObservationError, match=NOT_TEXT):
        validate(ws, NOT_A_DICT[kind](texts), REL[q].scope)


# ============================ R196 (B-R10-B2): a value of the wrong shape where it is read is refused, not raised
@pytest.mark.parametrize("q", QUARTERS)
@pytest.mark.parametrize("value", [[], {}, [1], {"a": 1}], ids=["list", "dict", "list1", "dict1"])
def test_r196_a_list_or_dict_read_as_a_document_id_on_the_non_envelope_route_is_refused(q, value):
    """B-R10-B2: the non-envelope route used a present row's source_span.document_id as a dict key before testing its
    type, so an exact list or dict, which the entry admits, raised TypeError (unhashable)."""
    ws, texts = fresh(q)
    r9._non_envelope(ws)
    rows = [row for row in ws["facts"] if str(row.get("metric", "")).startswith("pg_") and "source_span" in row]
    assert rows
    for row in rows:
        row["source_span"]["document_id"] = copy.deepcopy(value)
    refused(ws, texts, q, UNREADABLE)


def _raise_inside(monkeypatch, exc):
    """Raise exc from the first helper the validator's body calls on the unedited workspace."""

    def raiser(*_args, **_kwargs):
        raise exc

    monkeypatch.setattr(eo, "_fiscal_identity", raiser)


CONVERTED = {
    "type_error": lambda: TypeError("unhashable type: 'list'"),
    "value_error": lambda: ValueError("invalid literal"),
    "unicode_decode_error": lambda: UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte"),
    "zero_division_error": lambda: ZeroDivisionError("division by zero"),
    "overflow_error": lambda: OverflowError("int too large to convert to float"),
    "key_error": lambda: KeyError("document_id"),
    "index_error": lambda: IndexError("list index out of range"),
    "attribute_error": lambda: AttributeError("'list' object has no attribute 'get'"),
}


@pytest.mark.parametrize("kind", sorted(CONVERTED))
def test_r196_the_public_entry_turns_a_built_in_error_about_a_value_into_a_refusal(monkeypatch, kind):
    """Seat: R196's contract.  An exception a built-in operation raises about a value's type or range, raised anywhere
    in the body, leaves the public path as a refusal that names it and keeps it as its cause."""
    ws, texts = fresh("Q3")
    exc = CONVERTED[kind]()
    _raise_inside(monkeypatch, exc)
    with pytest.raises(EconomicObservationError, match=UNREADABLE) as caught:
        validate(ws, texts, REL["Q3"].scope)
    assert caught.value.__cause__ is exc
    assert str(caught.value).endswith(f"({type(exc).__name__})")


PROPAGATED = {
    "boom": lambda: Boom("not about a value's type or range"),
    "runtime_error": lambda: RuntimeError("dictionary changed size during iteration"),
    "recursion_error": lambda: RecursionError("maximum recursion depth exceeded"),
    "name_error": lambda: NameError("name 'undefined' is not defined"),
}


@pytest.mark.parametrize("kind", sorted(PROPAGATED))
def test_r196_every_other_exception_still_propagates_as_itself(monkeypatch, kind):
    """Seat: R196 converts exactly the exceptions about a value's type or range; any other leaves the entry unchanged."""
    ws, texts = fresh("Q3")
    exc = PROPAGATED[kind]()
    _raise_inside(monkeypatch, exc)
    with pytest.raises(type(exc)) as caught:
        validate(ws, texts, REL["Q3"].scope)
    assert caught.value is exc


def test_r196_a_refusal_raised_inside_leaves_the_entry_as_itself(monkeypatch):
    """Seat: a refusal the body raises is not rewrapped, so its message is the one the rulings pin."""
    ws, texts = fresh("Q3")
    exc = EconomicObservationError("replay_mismatch: a refusal raised inside the body")
    _raise_inside(monkeypatch, exc)
    with pytest.raises(EconomicObservationError) as caught:
        validate(ws, texts, REL["Q3"].scope)
    assert caught.value is exc
    assert caught.value.__cause__ is None


def test_r196_a_call_that_does_not_match_the_signature_is_not_a_refusal():
    """Seat: the conversion covers the body, not the call; a malformed call still raises TypeError."""
    ws, texts = fresh("Q3")
    with pytest.raises(TypeError) as caught:
        eo.validate_selected_facts(ws, source_texts=texts)
    assert not isinstance(caught.value, EconomicObservationError)


# ---- controls
@pytest.mark.parametrize("q", QUARTERS)
def test_r195_control_the_unedited_workspace_and_its_json_round_trip_validate(q):
    """Neither ruling moves an acceptance: the unedited build validates, and so does its JSON round trip."""
    ws, texts = fresh(q)
    assert validate(ws, texts, REL[q].scope)
    round_trip = json.loads(json.dumps(ws))
    assert round_trip == ws
    assert validate(round_trip, texts, REL[q].scope)


CANONICAL = {
    "third": lambda: Fraction(1, 3),
    "whole": lambda: Fraction(3),
    "negative": lambda: Fraction(-7, 12),
    "near_the_bound": lambda: Fraction(10**639, 10**639 - 1),
}


@pytest.mark.parametrize("q", QUARTERS)
@pytest.mark.parametrize("kind", sorted(CANONICAL))
def test_r195_control_a_fraction_python_builds_passes_the_entry_and_the_row_checks_refuse_it(q, kind):
    """A Fraction in the form Python builds passes the walk, as R193 admits it, and a present row's value that is one is
    refused by the row's own check, as before."""
    ws, texts = fresh(q)
    present_row(ws)["value"] = CANONICAL[kind]()
    refused(ws, texts, q, "selected observation is not JSON data")


@pytest.mark.parametrize("q", QUARTERS)
@pytest.mark.parametrize("where", ["quarter", "value", "claims"])
def test_r195_control_a_genuine_fraction_is_refused_or_unread_without_raising(q, where):
    """Group B's control: Fraction(1, 3) as the quarter or a present value is refused by the check that reads it, and in
    a field the validator does not read it is accepted, as at 6caa2ffc1a95."""
    ws, texts = fresh(q)
    if where == "quarter":
        ws["fiscal_period"]["quarter"] = Fraction(1, 3)
        refused(ws, texts, q, "workspace quarter does not match fiscal_scope")
    elif where == "value":
        present_row(ws)["value"] = Fraction(1, 3)
        refused(ws, texts, q, "selected observation is not JSON data")
    else:
        ws["claims"] = [Fraction(1, 3)]
        assert validate(ws, texts, REL[q].scope)


@pytest.mark.parametrize("q", QUARTERS)
def test_r196_control_the_non_envelope_route_with_a_text_document_id_keeps_its_refusal(q):
    """Group B's control: on B-R10-B2's route, a present row whose document id is text is refused by the route's own
    check, not converted."""
    ws, texts = fresh(q)
    r9._non_envelope(ws)
    refused(ws, texts, q, "present observation belongs to another document")


@pytest.mark.parametrize("q", QUARTERS)
@pytest.mark.parametrize("kind", ["list", "none", "text", "ordered_dict"])
def test_r195_control_a_workspace_that_is_not_a_dict_keeps_its_refusal(q, kind):
    """A workspace of an admitted type other than dict is refused as before, as not a mapping; one of a type the walk
    does not admit keeps the walk's refusal, which R193 pins for a dict subclass."""
    ws, texts = fresh(q)
    tampered, expected = {
        "list": lambda: ([ws], NOT_MAPPING),
        "none": lambda: (None, NOT_MAPPING),
        "text": lambda: ("workspace", NOT_MAPPING),
        "ordered_dict": lambda: (collections.OrderedDict(ws), UNPRINTABLE),
    }[kind]()
    with pytest.raises(EconomicObservationError, match=expected):
        validate(tampered, texts, REL[q].scope)
