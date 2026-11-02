"""CDV-1 T1 F1-Q envelope — frozen R9 witness (seat-frozen after the independent Opus audit R9 of 11bd3dea8879).

Every case edits a frozen gzipped FY26 Q1-Q3 original in memory, or tampers a workspace built from one, and asserts the
outcome that the bytes and the seat rulings R116-R191 and R192-R194 require.  Group A found the validator's span check
counting a named character reference's 32-character bound in bytes, so a run of 31 letters and a multi-byte character
was cut inside the character, and decoding the cut raised UnicodeDecodeError (A-R9-B1, R187's class).  Group B found
R189's entry walk passing every type it did not list, so a range, a deque, a path or a Decimal reached the validator's
print, encode and compare sites and raised (B-R9-B1, R189's class), and a signalling Decimal NaN raising in a comparison
of the non-envelope branch (B-R9-B2).

R192 reads the span check's units as characters, as a reader does, and reports each at its bytes, so no unit can end
inside a character.  R193 admits at the validator's entry a closed set of types, each by its exact type, and refuses
every other value, so no type is left for a later site to meet: the types a JSON document parses to (dict, list, str,
int, float, bool and None), a tuple (R136) and a Fraction (R134).  source_texts must be a dict of str to str.  R194
freezes this file.

The constructions are the auditors' (A and B).  The seat added R192's sweep over every run length and a fragment that
is not whole characters, and R193's subclasses of the admitted types, its source_texts cases and its JSON round trip.
Every case drives the public path (build_event_workspace, validate_selected_facts) except R192's reader cases, which
read the one function the rule changed, and the relocations, which patch the shared receipts API that R143 names as the
only place a wrapped receipt is minted.

Rulings: research/consumer_defensive/cdv1_program/reviews/SEAT_RULING_T1_ENVELOPE_R9_2026-09-29.md.
Audit record: research/consumer_defensive/cdv1_program/reviews/OPUS_T1_ENVELOPE_AUDIT_R9_2026-09-29.md.
"""
from __future__ import annotations

import collections
import copy
import enum
import html
import json
import pathlib
import sys
import types
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_pg_envelope_f1_probes_r4 as r4  # noqa: E402
import test_pg_envelope_f1_probes_r6 as r6  # noqa: E402
import test_pg_envelope_f1_probes_r7 as r7  # noqa: E402
from engine.company_intelligence import economic_observations as eo  # noqa: E402
from engine.company_intelligence.economic_observations import EconomicObservationError  # noqa: E402
from engine.earnings_release import receipts  # noqa: E402

REL = r4.REL
QUARTERS = sorted(REL)
refused, present_row = r7.refused, r7.present_row
UNPRINTABLE = "workspace holds a value it cannot print"
NOT_WHOLE = "present envelope observation span is not a whole literal"
NOT_TEXT = "source_texts must map document ids to text"

_BUILT: dict = {}


def fresh(q):
    """A deep copy of the unedited build of quarter q, built once per quarter."""
    if q not in _BUILT:
        _BUILT[q] = r7.built(q)
    ws, texts = _BUILT[q]
    return copy.deepcopy(ws), dict(texts)


# ============================ R192 (A-R9-B1): the span check reads characters, as a reader does
# A run of letters as long as a named reference may be, ending in a multi-byte character: 32 characters, more bytes.
CUT = {
    "e_acute": "&" + "a" * 31 + "é",
    "rsquo": "&" + "a" * 30 + "’",
    "math_bold": "&" + "a" * 29 + "\U0001d400",
    "amp_prefix": "&amp" + "b" * 28 + "é",  # a reader reads the legacy "&amp" and prints "&"
}


@pytest.mark.parametrize("form", sorted(CUT))
def test_r192_a_named_run_ending_in_a_multibyte_character_is_read_as_a_reader_reads_it(form):
    """A-R9-B1: the byte pattern counted the run's 32 characters in bytes and cut the last one, and decoding the cut
    raised.  The run drops no reference: a reader prints it, or prints "&" for the legacy "&amp"."""
    text = CUT[form]
    assert receipts.unescape(text) == html.unescape(text)
    assert eo._drops_a_reference(text.encode("utf-8")) is False


@pytest.mark.parametrize("form", sorted(CUT))
def test_r192_a_relocation_beside_a_named_run_ending_in_a_multibyte_character_is_refused(monkeypatch, form):
    """A-R9-B1 on the public path: Q3's diluted EPS receipt relocated through R143's seam onto the '1.63' printed after
    the run.  Refused as the ASCII control below is, not raised."""
    ws, texts, _ = r4.build(r6.relocated(monkeypatch, "<p>" + CUT[form] + " 1.63</p>"), "Q3")
    refused(ws, texts, "Q3", NOT_WHOLE)


def test_r192_control_the_same_relocation_beside_an_ascii_run_is_refused(monkeypatch):
    ws, texts, _ = r4.build(r6.relocated(monkeypatch, "<p>&" + "a" * 32 + " 1.63</p>"), "Q3")
    refused(ws, texts, "Q3", NOT_WHOLE)


def test_r192_no_run_length_cuts_a_character():
    """Seat: every run of 1 to 40 letters followed by a 2-, 3- and 4-byte character, with and without a ';' after it.
    The one reader agrees with html.unescape on each, and the span check reads each without raising."""
    for length in range(1, 41):
        for character in ("é", "’", "\U0001d400"):
            for tail in ("", ";", " 1.63"):
                text = "&" + "a" * length + character + tail
                assert receipts.unescape(text) == html.unescape(text), text
                assert eo._drops_a_reference(text.encode("utf-8")) in (True, False), text


def test_r192_a_fragment_that_is_not_whole_characters_is_refused_not_raised():
    """Seat: the span check decodes a fragment once; bytes that end inside a character are refused."""
    with pytest.raises(EconomicObservationError, match="not UTF-8 aligned"):
        eo._drops_a_reference("&aé".encode("utf-8")[:-1])


# ============================ R193 (B-R9-B1, B-R9-B2): the entry admits a closed set of types, and nothing else
def _huge():
    old = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(0)
    try:
        return 10**5000
    finally:
        sys.set_int_max_str_digits(old)


def _deep(depth=100_000, container=collections.deque):
    value = container([0])
    for _ in range(depth):
        value = container([value])
    return value


# B-R9-B1: types R189's walk did not list, carrying its three forms (a digit run past the limit, a deep nest, a lone
# surrogate) to str() of the fiscal period (the quarter and year checks) and to the fact identity's bytes.
UNLISTED = {
    "range_huge": lambda: range(_huge()),
    "slice_huge": lambda: slice(_huge()),
    "deque_huge_int": lambda: collections.deque([_huge()]),
    "namespace_huge": lambda: types.SimpleNamespace(x=_huge()),
    "deque_deep": lambda: _deep(),
    "userlist_deep": lambda: _deep(container=collections.UserList),
}
UNLISTED_TEXT = {
    "purepath": lambda: pathlib.PurePosixPath("\udc80"),
    "userstring": lambda: collections.UserString("\ud800"),
    "exception": lambda: ValueError("\ud800"),
    "range_huge": UNLISTED["range_huge"],
    "namespace_huge": UNLISTED["namespace_huge"],
}


@pytest.mark.parametrize("q", QUARTERS)
@pytest.mark.parametrize("field", ["quarter", "year"])
@pytest.mark.parametrize("kind", sorted(UNLISTED))
def test_r193_a_fiscal_period_field_of_an_unlisted_type_is_refused_at_the_entry(q, field, kind):
    ws, texts = fresh(q)
    ws["fiscal_period"][field] = UNLISTED[kind]()
    refused(ws, texts, q, UNPRINTABLE)


@pytest.mark.parametrize("q", QUARTERS)
@pytest.mark.parametrize("kind", sorted(UNLISTED_TEXT))
def test_r193_a_present_rows_period_of_an_unlisted_type_is_refused_at_the_entry(q, kind):
    ws, texts = fresh(q)
    present_row(ws)["period"] = UNLISTED_TEXT[kind]()
    refused(ws, texts, q, UNPRINTABLE)


def _non_envelope(ws):
    """B-R9-B2's route: rename the release document so its text is not the caller-held envelope."""
    for source in ws["sources"]:
        if source.get("kind") == "issuer_release":
            source["document_id"] = "nope"


@pytest.mark.parametrize("q", QUARTERS)
@pytest.mark.parametrize("where", ["segment_bytes", "event_id"])
def test_r193_a_signalling_decimal_nan_is_refused_at_the_entry(q, where):
    """B-R9-B2: Decimal('sNaN') raised InvalidOperation in the non-envelope branch's comparisons."""
    ws, texts = fresh(q)
    _non_envelope(ws)
    if where == "segment_bytes":
        present_row(ws)["source_span"]["receipt"]["segment_bytes"] = Decimal("sNaN")
    else:
        ws["event_id"] = Decimal("sNaN")
        for row in ws["facts"]:
            row["event_id"] = Decimal("sNaN")
    refused(ws, texts, q, UNPRINTABLE)


# Seat: a subclass of an admitted type is not the type.  Each is a stdlib type.
SUBCLASSED = {
    "int_enum": lambda: enum.IntEnum("Quarter", {"Q": 3}).Q,
    "str_enum": lambda: enum.StrEnum("Quarter", {"Q": "3"}).Q,
    "ordered_dict": lambda: collections.OrderedDict(q=3),
    "default_dict": lambda: collections.defaultdict(int, q=3),
    "counter": lambda: collections.Counter(q=3),
    "named_tuple": lambda: collections.namedtuple("Quarter", "q")(3),
}


@pytest.mark.parametrize("q", QUARTERS)
@pytest.mark.parametrize("kind", sorted(SUBCLASSED))
def test_r193_a_subclass_of_an_admitted_type_is_refused_at_the_entry(q, kind):
    ws, texts = fresh(q)
    ws["fiscal_period"]["quarter"] = SUBCLASSED[kind]()
    refused(ws, texts, q, UNPRINTABLE)


@pytest.mark.parametrize("q", QUARTERS)
def test_r193_a_workspace_that_is_a_dict_subclass_is_refused_at_the_entry(q):
    ws, texts = fresh(q)
    refused(collections.OrderedDict(ws), texts, q, UNPRINTABLE)


@pytest.mark.parametrize("q", QUARTERS)
@pytest.mark.parametrize(
    "kind", ["mapping_proxy", "str_subclass_text", "str_subclass_id", "user_string_text"]
)
def test_r193_source_texts_must_be_a_dict_of_str_to_str(q, kind):
    ws, texts = fresh(q)
    ((document_id, text),) = texts.items()
    tampered = {
        "mapping_proxy": lambda: types.MappingProxyType(dict(texts)),
        "str_subclass_text": lambda: {document_id: enum.StrEnum("Text", {"T": text}).T},
        "str_subclass_id": lambda: {enum.StrEnum("Id", {"D": document_id}).D: text},
        "user_string_text": lambda: {document_id: collections.UserString(text)},
    }[kind]()
    refused(ws, tampered, q, NOT_TEXT)


# ---- controls
@pytest.mark.parametrize("q", QUARTERS)
def test_r193_control_the_unedited_workspace_and_its_json_round_trip_validate(q):
    """The walk admits every type a JSON document parses to: the unedited build validates, and so does the same
    workspace after json.dumps and json.loads."""
    ws, texts = fresh(q)
    assert eo.validate_selected_facts(ws, source_texts=texts, fiscal_scope=REL[q].scope)
    round_trip = json.loads(json.dumps(ws))
    assert round_trip == ws
    assert eo.validate_selected_facts(round_trip, source_texts=texts, fiscal_scope=REL[q].scope)


REFUSED_AT_THE_ENTRY = {
    "int_huge": _huge,
    "list_deep": lambda: _deep(container=list),
    "str_surrogate": lambda: "\ud800",
    "decimal_nan": lambda: Decimal("NaN"),
    "complex": lambda: 1j,
    "bytes": lambda: b"\xff",
}
ADMITTED = {
    "float_inf": lambda: float("inf"),
    "fraction": lambda: Fraction(1, 3),
    "tuple_key": lambda: {(1, 2): 1},
}


@pytest.mark.parametrize("q", QUARTERS)
@pytest.mark.parametrize("kind", sorted(REFUSED_AT_THE_ENTRY))
def test_r193_control_r189s_witnesses_and_types_outside_the_set_are_refused_at_the_entry(q, kind):
    """B's controls: R189's own witnesses, and a Decimal, complex and bytes, are refused by the walk."""
    ws, texts = fresh(q)
    present_row(ws)["period"] = REFUSED_AT_THE_ENTRY[kind]()
    refused(ws, texts, q, UNPRINTABLE)


@pytest.mark.parametrize("q", QUARTERS)
@pytest.mark.parametrize("kind", sorted(ADMITTED))
def test_r193_control_an_admitted_type_passes_the_entry_and_the_row_checks_refuse_it(q, kind):
    """B's controls: a float, a Fraction and a tuple are in the set, so the walk admits them; the row checks refuse a
    period that is not the stored one."""
    ws, texts = fresh(q)
    present_row(ws)["period"] = ADMITTED[kind]()
    with pytest.raises(EconomicObservationError) as caught:
        eo.validate_selected_facts(ws, source_texts=texts, fiscal_scope=REL[q].scope)
    assert UNPRINTABLE not in str(caught.value)
