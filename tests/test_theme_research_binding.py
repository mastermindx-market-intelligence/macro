"""Direct unit pins for the shared theme-research foundation.

WHY THIS SUITE EXISTS. The kernel in
``engine/market_ontology/theme_research_binding.py`` was extracted from the
semiconductor composer under Sol's decomposition ruling (#7870
issuecomment-5895067178) so every later vertical inherits the same primitives
instead of copying them. The extraction was byte-neutral and every existing
suite stayed green — which proves nothing was broken, and NOT that the moved
behaviour is pinned. A mutation pass over the kernel against 706 passing tests
in 16 consumer suites found four laws no test discriminated at all:

* ``within()`` returning ``False`` for an owner timestamp this transport cannot
  read. Letting the exception escape again — the exact defect the Energy seat
  reported as base item 5 (#7870 issuecomment-5866433049), where ONE empty
  ``reviewed_at`` answered 503 for every row the caller was entitled to —
  failed zero tests.
* ``generation_fingerprint`` sorting the owner revision tuple, so the same
  owner state fingerprints identically whatever order it arrived in.
* ``canonical_text`` keeping ``ensure_ascii=False``.
* ``validate_pagination`` rejecting ``bool`` before it passes as a limit of 1.

A shared foundation whose laws are only covered incidentally, through one
vertical's fixtures, is a foundation the next vertical cannot rely on: the
fixture that happens to exercise a branch belongs to Semiconductor, and
Semiconductor may drop it. These tests read the kernel DIRECTLY, with no
vertical imported, so the laws survive any change to any vertical's corpus.

Scope: the primitives only. No vertical vocabulary, no schema, no route, no
rights decision and no authority is asserted here.
"""
from __future__ import annotations

import pytest

from engine.market_ontology.theme_research_binding import (
    BundleUnavailable,
    ResearchRefusal,
    canonical_text,
    generation_fingerprint,
    in_anchor_scope,
    is_instant,
    le,
    parse_clock,
    parse_day,
    readable,
    validate_cutoff_format,
    validate_pagination,
    validate_replay_cutoffs,
    within,
)

# ---------------------------------------------------------------------------
# The refusal / unavailability protocol
# ---------------------------------------------------------------------------


def test_research_refusal_str_is_exactly_the_code():
    """The shell maps ``str(exc)`` onto the private error family, so the
    message must carry the code and nothing else — no prefix, no punctuation."""
    exc = ResearchRefusal("cutoff_unreadable")
    assert exc.code == "cutoff_unreadable"
    assert str(exc) == "cutoff_unreadable"


def test_research_refusal_is_a_value_error_and_unavailable_is_not():
    """A contract violation is the caller's (``ValueError``); an unavailable
    bundle is the owner's. A vertical that raised one for the other would move
    a 503 onto a 400 and back, so the two hierarchies stay disjoint."""
    assert issubclass(ResearchRefusal, ValueError)
    assert not issubclass(BundleUnavailable, ValueError)
    assert issubclass(BundleUnavailable, Exception)


# ---------------------------------------------------------------------------
# canonical_text
# ---------------------------------------------------------------------------


def test_canonical_text_sorts_keys_and_emits_no_spurious_whitespace():
    assert canonical_text({"b": 1, "a": 2}) == '{"a":2,"b":1}'
    assert canonical_text({"a": {"d": 1, "c": 2}}) == '{"a":{"c":2,"d":1}}'


def test_canonical_text_preserves_non_ascii_verbatim():
    """``ensure_ascii=False`` is a DIGEST law, not a cosmetic one: the escaped
    form hashes differently, so flipping it silently renews every generation
    whose payload crosses a bilingual label. The kernel's only production
    consumer today fingerprints ASCII-only query dimensions, which is why no
    consumer fixture discriminates this — the law is pinned here instead, where
    the next caller to serialize zh copy will inherit it."""
    text = canonical_text({"note_zh": "半导体"})
    assert text == '{"note_zh":"半导体"}'
    assert "\\u" not in text


def test_canonical_text_refuses_nan_rather_than_emitting_invalid_json():
    with pytest.raises(ValueError):
        canonical_text({"ratio": float("nan")})


# ---------------------------------------------------------------------------
# Time comparison — the measured contract in le()'s docstring
# ---------------------------------------------------------------------------


def test_is_instant_splits_on_the_time_designator_only():
    assert is_instant("2026-12-31T23:00:00Z") is True
    assert is_instant("2026-12-31") is False


def test_parse_clock_assumes_utc_for_a_naive_value_and_reads_the_z_suffix():
    assert parse_clock("2026-12-31T23:00:00Z") == parse_clock("2026-12-31T23:00:00+00:00")
    assert parse_clock("2026-12-31T23:00:00").tzinfo is not None
    assert parse_clock("2026-12-31T23:00:00") == parse_clock("2026-12-31T23:00:00Z")


@pytest.mark.parametrize(
    ("value", "cutoff", "expected"),
    [
        # The three examples le()'s docstring publishes as "measured on this
        # build" for consumers reading a date-only cutoff (asked by the Energy
        # seat on #7870). They were prose; now they are pins.
        ("2026-12-31T23:00:00-05:00", "2026-12-31", True),
        ("2027-01-01T01:00:00+08:00", "2026-12-31", False),
        ("2026-12-31T23:00:00-05:00", "2026-12-31T23:59:59+00:00", False),
    ],
)
def test_le_matches_its_published_day_semantics(value, cutoff, expected):
    assert le(value, cutoff) is expected


def test_le_compares_two_dates_on_calendar_days_inclusively():
    assert le("2026-12-31", "2026-12-31") is True
    assert le("2027-01-01", "2026-12-31") is False


def test_le_never_synthesizes_a_time_for_a_date_only_side():
    """A date-only side is compared as a DAY, so an instant late in the cutoff
    day is still inside it. Synthesizing midnight would exclude it — the
    behaviour the no-synthesis rule exists to prevent."""
    assert le("2026-12-31T23:59:59+00:00", "2026-12-31") is True
    assert le("2026-12-31", "2026-12-31T00:00:00+00:00") is True


# ---------------------------------------------------------------------------
# Unreadable owner timestamps — WITHHOLD, never fatal
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    ["", "unknown", "not-a-date", "2026-13-45", None, 0, 20261231, [], {}],
)
def test_within_withholds_an_unreadable_owner_timestamp_instead_of_raising(value):
    """``le`` raises ``ValueError`` on a string it cannot parse and
    ``TypeError`` on a non-string. Reached from a time gate that bare exception
    left the route's catch-all to answer 503, so ONE unreadable owner timestamp
    denied the caller every row it was entitled to (Energy seat base item 5,
    #7870 issuecomment-5866433049, probed with an empty ``reviewed_at``).

    This is reachable in the shipping vertical today: the semiconductor
    composer's identity gate calls ``within`` on ``mapping_learned_at`` behind
    an ``isinstance(..., str)`` check with no readability guard, so an empty
    string from the owner lands here.
    """
    assert within(value, "2026-12-31") is False


def test_within_withholds_on_an_unreadable_cutoff_too():
    assert within("2026-12-01", "not-a-date") is False
    assert within("2026-12-01", None) is False


def test_within_is_unchanged_for_every_value_le_could_already_read():
    assert within("2026-12-01", "2026-12-31") is True
    assert within("2027-01-01", "2026-12-31") is False
    assert within("2026-12-31T23:00:00-05:00", "2026-12-31") is True


def test_withholding_is_false_in_both_polarities():
    """Every caller reads ``within`` as "in range", so ``False`` withholds
    whichever way the gate is written: an inclusion test does not include and
    an exclusion test excludes. A helper that raised instead would make the
    polarity decide between a dropped row and a dead request."""
    unreadable = ""
    assert within(unreadable, "2026-12-31") is False
    assert (not within(unreadable, "2026-12-31")) is True


@pytest.mark.parametrize("value", ["", "unknown", "not-a-date", None, 17, []])
def test_readable_is_false_for_what_le_cannot_compare(value):
    assert readable(value) is False


@pytest.mark.parametrize("value", ["2026-12-31", "2026-12-31T23:00:00Z"])
def test_readable_is_true_for_what_le_can_compare(value):
    assert readable(value) is True


def test_readable_separates_not_datable_from_datable_but_outside():
    """The two cases need different limitations, so a caller must be able to
    tell them apart: ``readable`` is the only thing that does."""
    assert readable("2027-06-01") is True and within("2027-06-01", "2026-12-31") is False
    assert readable("unknown") is False and within("unknown", "2026-12-31") is False


# ---------------------------------------------------------------------------
# Shared query-format validation
# ---------------------------------------------------------------------------


def _pagination(**overrides):
    kwargs = {"limit": 50, "offset": 0, "expected_generation": None,
              "min_limit": 1, "max_limit": 100}
    kwargs.update(overrides)
    return validate_pagination(**kwargs)


def test_validate_pagination_accepts_a_limit_inside_the_callers_own_bounds():
    assert _pagination(limit=1) is None
    assert _pagination(limit=100) is None


@pytest.mark.parametrize("limit", [0, 101, -1])
def test_validate_pagination_refuses_a_limit_outside_the_callers_bounds(limit):
    with pytest.raises(ResearchRefusal) as exc:
        _pagination(limit=limit)
    assert exc.value.code == "limit_out_of_range"


def test_the_bounds_are_the_callers_not_this_helpers():
    """``min_limit``/``max_limit`` are arguments because the page policy is the
    VERTICAL's. A helper with defaults of its own would quietly impose
    semiconductor's bounds on every later vertical."""
    assert _pagination(limit=7, min_limit=5, max_limit=7) is None
    with pytest.raises(ResearchRefusal):
        _pagination(limit=7, min_limit=1, max_limit=6)


@pytest.mark.parametrize("value", [True, False])
def test_validate_pagination_refuses_a_bool_limit(value):
    """``bool`` is an ``int`` subclass, so ``True`` would otherwise pass the
    range check as a limit of 1 and ``False`` as 0: a caller that posted a
    truthy flag where a page size belongs would be served one row instead of
    being told its request was malformed."""
    with pytest.raises(ResearchRefusal) as exc:
        _pagination(limit=value)
    assert exc.value.code == "limit_out_of_range"


@pytest.mark.parametrize("value", [True, False])
def test_validate_pagination_refuses_a_bool_offset(value):
    with pytest.raises(ResearchRefusal) as exc:
        _pagination(offset=value)
    assert exc.value.code == "offset_negative"


@pytest.mark.parametrize("limit", ["50", 50.0, None])
def test_validate_pagination_refuses_a_non_int_limit(limit):
    with pytest.raises(ResearchRefusal) as exc:
        _pagination(limit=limit)
    assert exc.value.code == "limit_out_of_range"


def test_validate_pagination_refuses_a_negative_offset():
    with pytest.raises(ResearchRefusal) as exc:
        _pagination(offset=-1)
    assert exc.value.code == "offset_negative"


def test_a_deep_page_requires_the_generation_pin():
    """Paging past the first page without pinning the generation would let the
    corpus move under the caller between pages."""
    with pytest.raises(ResearchRefusal) as exc:
        _pagination(offset=50, expected_generation=None)
    assert exc.value.code == "expected_generation_required"
    assert _pagination(offset=50, expected_generation="gen_" + "a" * 32) is None
    assert _pagination(offset=0, expected_generation=None) is None


def test_replay_requires_both_cutoffs_and_the_mode_token_is_the_callers():
    with pytest.raises(ResearchRefusal) as exc:
        validate_replay_cutoffs(time_mode="system_replay", source_cutoff="2026-12-31",
                                recorded_cutoff=None)
    assert exc.value.code == "replay_cutoffs_required"
    with pytest.raises(ResearchRefusal):
        validate_replay_cutoffs(time_mode="system_replay", source_cutoff=None,
                                recorded_cutoff="2026-12-31")
    assert validate_replay_cutoffs(
        time_mode="system_replay", source_cutoff="2026-12-31",
        recorded_cutoff="2026-12-31") is None
    # ``latest`` needs neither, and the mode VOCABULARY belongs to the vertical:
    # a vertical whose replay token is spelled differently says so.
    assert validate_replay_cutoffs(time_mode="latest", source_cutoff=None,
                                   recorded_cutoff=None) is None
    with pytest.raises(ResearchRefusal):
        validate_replay_cutoffs(time_mode="as_of", source_cutoff=None,
                                recorded_cutoff=None, replay_mode="as_of")


def test_an_absent_cutoff_is_not_a_format_error():
    assert validate_cutoff_format(None, None) is None
    assert validate_cutoff_format() is None


@pytest.mark.parametrize("raw", ["2026-12-31", "2026-12-31T23:00:00Z",
                                 "2026-12-31T23:00:00-05:00"])
def test_validate_cutoff_format_admits_what_le_can_compare(raw):
    assert validate_cutoff_format(raw) is None


@pytest.mark.parametrize("raw", ["", "unknown", "31/12/2026", "2026-13-01", 20261231, []])
def test_validate_cutoff_format_refuses_an_unreadable_supplied_cutoff(raw):
    """Until this validator ran, the first parse happened inside a time gate:
    ``le`` raised a bare ValueError and the route answered 503 ``retry_later``
    — a TRANSIENT code for a permanently malformed request — and where no gate
    read the cutoff the request answered a silent 200 that echoed the
    unreadable value back with no limitation marking it (#7870
    issuecomment-5868018569, corrected in 5869344590 and 5870740225)."""
    with pytest.raises(ResearchRefusal) as exc:
        validate_cutoff_format(raw)
    assert exc.value.code == "cutoff_unreadable"


@pytest.mark.parametrize("raw", ["20261231", "2026-W53-4"])
def test_the_validator_parses_with_parse_day_not_parse_clock(raw):
    """``parse_day`` is the parser deliberately: it accepts EXACTLY what ``le``
    can go on to compare. ``fromisoformat`` admits these two forms, which
    ``le`` then raises on — a validator built on it would hand them straight
    back to the 503 it exists to remove. Measured both halves here so the
    choice cannot be "simplified" back."""
    assert parse_clock(raw) is not None          # fromisoformat accepts it
    with pytest.raises(ValueError):
        parse_day(raw)                           # le cannot compare it
    with pytest.raises(ResearchRefusal) as exc:
        validate_cutoff_format(raw)              # so the validator refuses it
    assert exc.value.code == "cutoff_unreadable"


def test_a_well_formed_cutoff_is_never_refused_for_the_mode_it_arrives_in():
    """FORMAT only. A registered vertical may read a cutoff in a mode another
    vertical ignores — nuclear judges target windows from ``source_cutoff`` in
    ``latest`` — so refusing it here would fail that vertical's existing pins."""
    assert validate_cutoff_format("2026-12-31", None) is None
    assert validate_cutoff_format(None, "2026-12-31") is None


# ---------------------------------------------------------------------------
# Canonical anchor scope matching — two vocabularies meet here
# ---------------------------------------------------------------------------


def _assertion(scope_id):
    return {"scope": {"canonical_theme_id": scope_id}}


def test_the_crosswalk_slug_form_matches():
    assert in_anchor_scope(_assertion("ai_semiconductors"), "ai_semiconductors") is True


def test_the_identity_owners_canonical_node_id_form_matches_too():
    """``theme:<slug>`` is the canonical-id law this carrier published (#7870
    issuecomment-5812295091) and every later vertical was told to mint through
    ``theme_node_id``. Comparing raw strings admitted only the slug: the
    semiconductor corpus happens to carry the slug so the defect stayed
    invisible, while a vertical that followed the published law matched nothing
    and — because an out-of-scope row is deliberately silent — got zero rows
    and NO limitation naming why."""
    assert in_anchor_scope(_assertion("theme:ai_semiconductors"), "ai_semiconductors") is True


def test_a_foreign_theme_does_not_match_in_either_form():
    assert in_anchor_scope(_assertion("ai_robotics"), "ai_semiconductors") is False
    assert in_anchor_scope(_assertion("theme:ai_robotics"), "ai_semiconductors") is False


def test_the_deliberately_non_canonical_ltheme_prefix_is_refused_structurally():
    """No blocklist: the identity owner declares ``ltheme:`` non-canonical and
    ``theme_node_id`` can never produce it, so the refusal follows from going
    through the owner instead of concatenating a literal prefix."""
    assert in_anchor_scope(_assertion("ltheme:ai_semiconductors"), "ai_semiconductors") is False


@pytest.mark.parametrize("scope_id", [None, "", 17, [], {"x": 1}])
def test_a_missing_or_unusable_scope_id_is_out_of_scope_not_an_exception(scope_id):
    assert in_anchor_scope(_assertion(scope_id), "ai_semiconductors") is False


def test_an_assertion_with_no_scope_block_is_out_of_scope():
    assert in_anchor_scope({}, "ai_semiconductors") is False


def test_an_anchor_the_identity_owner_cannot_form_a_node_id_for_is_out_of_scope():
    """``theme_node_id`` raises on an empty id; that is an out-of-scope answer,
    not a 500 for the caller."""
    assert in_anchor_scope(_assertion("theme:"), "") is False
    assert in_anchor_scope(_assertion("theme:x"), "   ") is False


# ---------------------------------------------------------------------------
# Generation / fingerprint mechanics
# ---------------------------------------------------------------------------


def _fingerprint(**overrides):
    kwargs = {
        "definition_version": "2026-09-24.1",
        "rights_revision": "rev-7",
        "revision_tuple": (("owner_a", "r1"), ("owner_b", "r2")),
        "fields": {"anchor_theme_id": "ai_semiconductors", "slice_key": "hbm_packaging"},
    }
    kwargs.update(overrides)
    return generation_fingerprint(**kwargs)


def test_the_fingerprint_is_the_prefix_plus_a_fixed_width_hex_digest():
    value = _fingerprint()
    assert value.startswith("gen_")
    body = value[len("gen_"):]
    assert len(body) == 32 and all(c in "0123456789abcdef" for c in body)


def test_the_fingerprint_is_stable_for_the_same_inputs():
    assert _fingerprint() == _fingerprint()


def test_the_owner_revision_tuple_fingerprints_independently_of_arrival_order():
    """An owner revision SET is not an ordered list: the same owner state
    reached by a different read order must pin the same generation, or a caller
    holding a valid pin is told to refresh for no reason."""
    assert _fingerprint(revision_tuple=(("owner_b", "r2"), ("owner_a", "r1"))) == _fingerprint()


def test_a_changed_owner_revision_mints_a_new_generation():
    assert _fingerprint(revision_tuple=(("owner_a", "r1"), ("owner_b", "r3"))) != _fingerprint()


def test_the_rights_revision_is_bound_into_the_generation():
    """A rights change must renew the pin: without it a caller's stale
    ``expected_generation`` would still validate after entitlement moved, and
    the row set served under the new rights would differ from the one the pin
    was issued for."""
    assert _fingerprint(rights_revision="rev-8") != _fingerprint()


def test_the_definition_version_is_bound_into_the_generation():
    assert _fingerprint(definition_version="2026-09-24.2") != _fingerprint()


def test_every_vertical_query_dimension_is_bound_into_the_generation():
    base = _fingerprint()
    assert _fingerprint(fields={"anchor_theme_id": "ai_semiconductors",
                                "slice_key": "sic_gan_specialty"}) != base
    assert _fingerprint(fields={"anchor_theme_id": "ai_robotics",
                                "slice_key": "hbm_packaging"}) != base


def test_the_helper_adds_no_dimension_of_its_own_and_defaults_none():
    """``fields`` carries the vertical's OWN dimensions. A helper that injected
    one would force Mining's different generation semantics and Technology's
    temporal-key defect into a shape neither asked for — which Sol's ruling
    explicitly forbids."""
    assert _fingerprint(fields={}) != _fingerprint()
    assert _fingerprint(fields={"slice_key": "hbm_packaging",
                                "anchor_theme_id": "ai_semiconductors"}) == _fingerprint()


def test_the_prefix_and_width_are_the_callers():
    value = generation_fingerprint(
        definition_version="v", rights_revision="r", revision_tuple=(),
        fields={}, prefix="rev_", width=8)
    assert value.startswith("rev_") and len(value) == len("rev_") + 8
