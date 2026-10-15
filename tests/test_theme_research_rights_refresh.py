"""Rights SNAPSHOT vs process cache (T03) — a revocation must reach the gate.

``engine/theme_graph/rights.py`` has always had two read disciplines to reconcile:
the legacy ``@lru_cache``d :func:`rights.load_registry` (per-process, answers "what
did this process last see") and the enforcement need for "what does the file say
RIGHT NOW" — a rights decision that moves after mint time has to be able to reach an
emission gate without a process restart. ``load_registry_snapshot`` re-reads the
registry bytes fresh and stamps a content revision;
``assert_current_emission_allowed`` gates a whole emission against that snapshot and
nothing else. These tests pin: the snapshot's freshness and revision contract, its
fail-closed error surface (missing / corrupt never reads as all-clear), that the
gating decision is exactly the legacy class → ``EMISSION_OK`` decision, and that the
legacy cached behavior is untouched by any of it.
"""
from __future__ import annotations

import re

import pytest

from engine.theme_graph.rights import (
    EMISSION_OK,
    RIGHTS_CLASSES,
    RightsRefusal,
    _load,
    assert_current_emission_allowed,
    assert_public_emission_allowed,
    load_registry,
    load_registry_snapshot,
    rights_class,
)

FIXTURE_OK = "families:\n  witness:\n    rights_class: direct_display_ok\n"
FIXTURE_REVOKED = "families:\n  witness:\n    rights_class: unresolved\n"


def test_rights_revocation_changes_snapshot_without_process_restart(tmp_path):
    from engine.theme_graph.rights import load_registry_snapshot, assert_current_emission_allowed, RightsRefusal
    import pytest
    p = tmp_path / 'sources.yml'
    p.write_text('families:\n  witness:\n    rights_class: direct_display_ok\n')
    first = load_registry_snapshot(p)
    assert_current_emission_allowed(['witness'], snapshot=first)
    p.write_text('families:\n  witness:\n    rights_class: unresolved\n')
    second = load_registry_snapshot(p)
    assert second[0] != first[0]
    with pytest.raises(RightsRefusal):
        assert_current_emission_allowed(['witness'], snapshot=second)


def test_snapshot_is_read_fresh_every_call(tmp_path):
    p = tmp_path / "sources.yml"
    p.write_text(FIXTURE_OK)
    first = load_registry_snapshot(p)
    p.write_text(FIXTURE_REVOKED)
    second = load_registry_snapshot(p)
    # No cache in the way: the second read reflects the second write, families included.
    assert second[1]["witness"]["rights_class"] == "unresolved"
    assert first[1]["witness"]["rights_class"] == "direct_display_ok"
    assert second[0] != first[0]


def test_identical_bytes_give_identical_revision(tmp_path):
    p = tmp_path / "sources.yml"
    p.write_text(FIXTURE_OK)
    a = load_registry_snapshot(p)
    b = load_registry_snapshot(p)
    assert a[0] == b[0]
    assert a[1] == b[1]
    # A rewrite of the SAME bytes is the same registry: the revision is content-stamped.
    p.write_text(FIXTURE_OK)
    assert load_registry_snapshot(p)[0] == a[0]


def test_revision_shape_is_content_addressed(tmp_path):
    p = tmp_path / "sources.yml"
    p.write_text(FIXTURE_OK)
    revision, _ = load_registry_snapshot(p)
    assert re.fullmatch(r"rights_[0-9a-f]{32}", revision), revision


def test_missing_registry_refuses(tmp_path):
    with pytest.raises(RightsRefusal) as ei:
        load_registry_snapshot(tmp_path / "nope.yml")
    assert "registry_missing" in str(ei.value)


def test_unparseable_yaml_refuses_as_corrupt(tmp_path):
    p = tmp_path / "bad.yml"
    p.write_text("families: [unclosed\n")
    with pytest.raises(RightsRefusal) as ei:
        load_registry_snapshot(p)
    assert "registry_corrupt" in str(ei.value)


def test_non_mapping_document_refuses_as_corrupt(tmp_path):
    p = tmp_path / "list.yml"
    p.write_text("- just\n- a\n- list\n")
    with pytest.raises(RightsRefusal) as ei:
        load_registry_snapshot(p)
    assert "registry_corrupt" in str(ei.value)


def test_missing_families_mapping_refuses_as_corrupt(tmp_path):
    p = tmp_path / "nofam.yml"
    p.write_text('version: 1\nupdated: "2026-09-23"\n')
    with pytest.raises(RightsRefusal) as ei:
        load_registry_snapshot(p)
    assert "registry_corrupt" in str(ei.value)


def test_null_families_mapping_refuses_as_corrupt(tmp_path):
    p = tmp_path / "nullfam.yml"
    p.write_text("families:\n")
    with pytest.raises(RightsRefusal) as ei:
        load_registry_snapshot(p)
    assert "registry_corrupt" in str(ei.value)


def test_undecodable_bytes_refuse_as_corrupt(tmp_path):
    p = tmp_path / "bin.yml"
    p.write_bytes(b"\xff\xfe\x00not yaml at all")
    with pytest.raises(RightsRefusal) as ei:
        load_registry_snapshot(p)
    assert "registry_corrupt" in str(ei.value)


def test_unknown_family_refuses_and_names_it(tmp_path):
    p = tmp_path / "sources.yml"
    p.write_text(FIXTURE_OK)
    snapshot = load_registry_snapshot(p)
    with pytest.raises(RightsRefusal) as ei:
        assert_current_emission_allowed(["ghost"], snapshot=snapshot)
    assert "unknown_family:ghost" in str(ei.value)


def test_refusal_names_the_family_and_its_rights_class(tmp_path):
    p = tmp_path / "sources.yml"
    p.write_text(FIXTURE_REVOKED)
    with pytest.raises(RightsRefusal) as ei:
        assert_current_emission_allowed(["witness"], snapshot=load_registry_snapshot(p))
    message = str(ei.value)
    assert "witness" in message
    assert "unresolved" in message


def test_empty_family_list_is_a_no_op(tmp_path):
    p = tmp_path / "sources.yml"
    p.write_text(FIXTURE_OK)
    assert_current_emission_allowed([], snapshot=load_registry_snapshot(p))


def test_unknown_rights_class_in_a_snapshot_refuses_closed(tmp_path):
    p = tmp_path / "typo.yml"
    p.write_text("families:\n  witness:\n    rights_class: display_ok_probably\n")
    with pytest.raises(RightsRefusal) as ei:
        assert_current_emission_allowed(["witness"], snapshot=load_registry_snapshot(p))
    assert "witness" in str(ei.value) and "display_ok_probably" in str(ei.value)


def test_legacy_cached_loader_is_unaffected_by_a_later_disk_write(tmp_path):
    """The snapshot and the legacy cache are independent read disciplines.

    ``_load``/``rights_class`` stay per-process cached — a rights decision that moves
    on disk must NOT change what the legacy accessors answer for that path, exactly as
    before T03. Only the fresh snapshot sees the new bytes.
    """
    p = tmp_path / "sources.yml"
    p.write_text(FIXTURE_OK)
    assert rights_class("witness", path=p) == "direct_display_ok"
    assert _load(str(p))["witness"]["rights_class"] == "direct_display_ok"
    p.write_text(FIXTURE_REVOKED)
    # Legacy cached reads keep answering from the cache — unchanged behavior.
    assert rights_class("witness", path=p) == "direct_display_ok"
    assert _load(str(p))["witness"]["rights_class"] == "direct_display_ok"
    assert load_registry(p)["witness"]["rights_class"] == "direct_display_ok"
    # ... while the snapshot carries the revocation.
    revision, families = load_registry_snapshot(p)
    assert families["witness"]["rights_class"] == "unresolved"
    with pytest.raises(RightsRefusal):
        assert_current_emission_allowed(["witness"], snapshot=(revision, families))


def test_default_path_reads_the_real_registry_and_matches_load_registry():
    revision, families = load_registry_snapshot(None)
    assert families == load_registry()
    assert re.fullmatch(r"rights_[0-9a-f]{32}", revision)


def test_real_registry_posture_under_the_current_snapshot():
    """What the shipped registry actually says, asserted through the new gate.

    Pinned against the file's own rows: if the registry's classes move, this test
    fails loudly rather than silently passing an outdated posture.
    """
    revision, families = load_registry_snapshot(None)
    current = {k: str(v.get("rights_class", "")).strip() for k, v in families.items()}
    assert current["mastermind_curated"] == "direct_display_ok"
    # internal_only, not unresolved: Chairman gate #2 (2026-10-06, PR #8324
    # comment 6009724772, op gmi-vendor-rights-gate2-20261006-web-001) retained
    # BOTH vendor families as internal-only and closed the 2026-08-14 gmi-w3a
    # escalation as a no-display disposition. This test did its job — it failed
    # loudly when the ruling moved the registry under it. The refusal half below
    # needs no change: it reads `current[family]`, and rights.py:241 refuses
    # `internal_only` and `unresolved` alike.
    assert current["finviz_themes"] == "internal_only"
    assert current["ths_concepts"] == "internal_only"
    assert_current_emission_allowed(["mastermind_curated"], snapshot=(revision, families))
    for family in ("finviz_themes", "ths_concepts"):
        with pytest.raises(RightsRefusal) as ei:
            assert_current_emission_allowed([family], snapshot=(revision, families))
        assert family in str(ei.value)
        assert current[family] in str(ei.value)


# ---------------------------------------------------------------------------
# A2-F2 — the two gates, compared against EACH OTHER.
#
# The module docstring above claims these tests pin "that the gating decision is
# exactly the legacy class -> EMISSION_OK decision", and
# assert_current_emission_allowed's own docstring makes the stronger safety claim
# that "a snapshot gate can never be more permissive than the legacy one". Before
# this block neither was asserted anywhere: every test exercised ONE gate, and
# test_real_registry_posture_under_the_current_snapshot reaches only the two
# classes the shipped registry happens to use (direct_display_ok, internal_only)
# through only the snapshot gate. derived_display_ok and unresolved were never
# compared across both.
#
# The two gates agree today because both spell the permit decision
# `cls not in EMISSION_OK`. They are not the SAME code, though: the legacy gate
# delegates its unknown-family and out-of-enum checks to rights_class(), while
# the snapshot gate reimplements both inline against the snapshot mapping. That
# duplication is the divergence vector -- normalising or aliasing a class inside
# rights_class() would move one verdict and not the other -- and it is what
# these tests watch.
# ---------------------------------------------------------------------------

#: (class, whether a public emission is permitted). Deliberately a LOCAL table and
#: not a comprehension over EMISSION_OK: a test that derives its expectation from
#: the constant under test asserts only that the constant equals itself. The
#: coverage guard below is what keeps this table honest against the real enum.
_CLASS_VERDICTS: tuple[tuple[str, bool], ...] = (
    ("direct_display_ok", True),
    ("derived_display_ok", True),
    ("internal_only", False),
    ("unresolved", False),
)


def _both_gate_verdicts(path, family: str) -> tuple[bool, bool]:
    """``(legacy_permits, snapshot_permits)`` for one family, read through both gates.

    Each caller passes a DISTINCT file: ``assert_public_emission_allowed`` reads
    through the ``@lru_cache``d ``load_registry``, which is keyed on the path, so
    reusing one path with rewritten contents would compare a fresh snapshot against
    a stale cache and measure the caching, not the verdicts.
    """
    try:
        assert_public_emission_allowed(family, path=path)
        legacy = True
    except RightsRefusal:
        legacy = False
    try:
        assert_current_emission_allowed([family], snapshot=load_registry_snapshot(path))
        snapshot = True
    except RightsRefusal:
        snapshot = False
    return legacy, snapshot


@pytest.mark.parametrize("rights_cls,permitted", _CLASS_VERDICTS)
def test_both_emission_gates_agree_for_every_rights_class(tmp_path, rights_cls, permitted):
    """Same verdict from both gates, for every member of ``RIGHTS_CLASSES``."""
    path = tmp_path / f"{rights_cls}.yml"
    path.write_text(f"families:\n  witness:\n    rights_class: {rights_cls}\n")

    legacy, snapshot = _both_gate_verdicts(path, "witness")

    assert legacy == permitted, f"legacy gate disagrees with the table for {rights_cls}"
    assert snapshot == legacy, (
        f"the snapshot gate and the legacy gate DISAGREE for rights_class="
        f"{rights_cls!r}: legacy permits={legacy}, snapshot permits={snapshot}. "
        f"assert_current_emission_allowed's docstring claims it can never be more "
        f"permissive than the legacy gate; one of them has moved")


@pytest.mark.parametrize("family,contents", (
    # Unknown family: no row at all.
    ("ghost", "families:\n  witness:\n    rights_class: direct_display_ok\n"),
    # A class outside the enum -- a typo must not read as a permission.
    ("witness", "families:\n  witness:\n    rights_class: display_ok_probably\n"),
))
def test_both_emission_gates_agree_on_the_two_refusal_axes(tmp_path, family, contents):
    """The axes where the gates do NOT share code: each implements these itself.

    Bounded honestly: this pins the VERDICT, and for the out-of-enum axis the
    verdict cannot distinguish the two guards. ``EMISSION_OK`` is a subset of
    ``RIGHTS_CLASSES``, so a class outside the enum is necessarily outside
    ``EMISSION_OK`` too, and the later check refuses it anyway. Measured: replacing
    the snapshot gate's ``if cls not in RIGHTS_CLASSES`` with ``if False`` left this
    file at 72 passed and the three rights suites the boundary job runs at 132
    passed -- nothing noticed. The out-of-enum guard is therefore
    defence-in-depth whose only observable effect is WHICH refusal message you
    get; the test below is what makes that branch discriminable.
    """
    path = tmp_path / "axis.yml"
    path.write_text(contents)

    legacy, snapshot = _both_gate_verdicts(path, family)

    assert legacy is False and snapshot is False, (
        f"a fail-closed axis read as a permission: legacy={legacy}, "
        f"snapshot={snapshot} for family={family!r}")


def test_an_out_of_enum_class_gets_the_unreadable_class_diagnosis(tmp_path):
    """The out-of-enum guard, pinned by its MESSAGE because its verdict is redundant.

    Both of the snapshot gate's refusal branches name the family and the offending
    class, so the existing
    ``test_unknown_rights_class_in_a_snapshot_refuses_closed`` passes whichever one
    fires -- which is why deleting the enum check was invisible. This asserts the
    distinguishing half: a typo'd class must be diagnosed as UNREADABLE ("outside
    the enum"), not merely reported as unpermitted, because the two call for
    different repairs -- fix the row's spelling versus seek a rights decision.
    """
    path = tmp_path / "typo.yml"
    path.write_text("families:\n  witness:\n    rights_class: display_ok_probably\n")

    with pytest.raises(RightsRefusal) as excinfo:
        assert_current_emission_allowed(["witness"], snapshot=load_registry_snapshot(path))

    message = str(excinfo.value)
    assert "outside" in message and "unreadable class" in message, message
    assert "permitted:" not in message, (
        "the out-of-enum class fell through to the EMISSION_OK branch, so the "
        "specific 'unreadable class' diagnosis was lost: " + message)


def test_the_verdict_table_covers_every_member_of_the_enum():
    """Guard on the table above: a fifth rights class must not slip in uncovered.

    Without this, adding a class to ``RIGHTS_CLASSES`` would leave the differential
    test silently covering a subset -- the test would stay green and stop
    discriminating, which is the failure mode the table's locality invites.
    """
    assert {cls for cls, _ in _CLASS_VERDICTS} == set(RIGHTS_CLASSES), (
        "RIGHTS_CLASSES and _CLASS_VERDICTS have diverged; add the new class to the "
        "table with its intended verdict rather than deleting this guard")


def test_the_table_and_EMISSION_OK_describe_the_same_permission_set():
    """The table's TRUE rows must be exactly ``EMISSION_OK``.

    Separate from the test above on purpose: that one catches a missing class, this
    one catches a class present but carrying the wrong intended verdict.
    """
    assert {cls for cls, ok in _CLASS_VERDICTS if ok} == set(EMISSION_OK)


# ---------------------------------------------------------------------------
# T04b — the transport withholds what it cannot attribute, and the
# interpretations derived from it. Sol #7780 issuecomment-5813801605:
# unmapped rights fail CLOSED. Robotics #7908 issuecomment-5815643294 (a)/(b).
# ---------------------------------------------------------------------------

def _bundle(assertions=(), blocks=()):
    from engine.market_ontology.semiconductor_theme_research import OwnerBundle

    return OwnerBundle(
        revision_tuple=(), rights_revision="r", assertions=tuple(assertions),
        identity_results=(), event_workspaces=(), financial_packets=(),
        interpretation_blocks=tuple(blocks), native_refs=(), omissions=(),
    )


def _assertion(revision, source_uri=None, locator=None):
    source = {}
    if source_uri is not None:
        source["source_uri"] = source_uri
    if locator is not None:
        source["locator"] = locator
    return {"curation_revision": revision, "source": source}


def _filter(bundle):
    from app.theme_research import _filter_bundle_for_rights
    from engine.theme_graph.rights import load_registry_snapshot

    return _filter_bundle_for_rights(bundle, snapshot=load_registry_snapshot())


def test_an_unmapped_source_ref_is_withheld_not_emitted():
    """The owner's ``None`` means "no opinion" for its own disagreement guard.
    This is an EMISSION path: material no rights row covers is exactly what
    the registry exists to decide about, so it is not published."""
    bundle = _bundle([
        _assertion("gmirca_" + "a" * 32, source_uri="https://unmapped.example/x.htm"),
        _assertion("gmirca_" + "b" * 32, source_uri="s3://somewhere/private.json"),
        _assertion("gmirca_" + "c" * 32),  # no source ref at all
    ])
    filtered, dropped = _filter(bundle)
    assert dropped is True
    assert filtered.assertions == ()


def test_a_mapped_and_permitted_family_still_passes():
    """The fail-closed rule must not swallow the families the registry does
    cover — otherwise the route would serve nothing whatever the rights say."""
    bundle = _bundle([_assertion("gmirca_" + "d" * 32, source_uri="data/baskets/x.json")])
    filtered, dropped = _filter(bundle)
    assert dropped is False
    assert filtered is bundle
    assert len(filtered.assertions) == 1


def test_an_interpretation_block_is_withheld_with_the_assertion_it_reads():
    """Prose derived from a withheld assertion is that assertion reaching the
    wire in another form. The composer would otherwise still emit it, marked
    stale but emitted."""
    kept_rev, refused_rev = "gmirca_" + "e" * 32, "gmirca_" + "f" * 32
    bundle = _bundle(
        [_assertion(kept_rev, source_uri="data/baskets/x.json"),
         _assertion(refused_rev, source_uri="https://unmapped.example/y.htm")],
        [{"interpretation_id": "i1", "mechanism": "reads the served one",
          "input_revisions": [kept_rev], "freshness": "current"},
         {"interpretation_id": "i2", "mechanism": "reads the withheld one",
          "input_revisions": [refused_rev], "freshness": "current"},
         {"interpretation_id": "i3", "mechanism": "reads both",
          "input_revisions": [kept_rev, refused_rev], "freshness": "current"},
         {"interpretation_id": "i4", "mechanism": "names no input at all",
          "input_revisions": [], "freshness": "current"}],
    )
    filtered, dropped = _filter(bundle)
    assert dropped is True
    assert [a["curation_revision"] for a in filtered.assertions] == [kept_rev]
    assert [b["interpretation_id"] for b in filtered.interpretation_blocks] == ["i1"]


def test_a_block_whose_inputs_are_all_served_survives_an_untouched_bundle():
    rev = "gmirca_" + "9" * 32
    bundle = _bundle(
        [_assertion(rev, source_uri="data/baskets/x.json")],
        [{"interpretation_id": "i1", "mechanism": "m", "input_revisions": [rev],
          "freshness": "current"}],
    )
    filtered, dropped = _filter(bundle)
    assert dropped is False and filtered is bundle


@pytest.mark.parametrize("inputs", [None, "not-a-list", 7, {}])
def test_a_block_with_a_malformed_input_list_is_withheld(inputs):
    """An input list this transport cannot read is not an attribution."""
    rev = "gmirca_" + "8" * 32
    bundle = _bundle(
        [_assertion(rev, source_uri="data/baskets/x.json")],
        [{"interpretation_id": "i1", "mechanism": "m", "input_revisions": inputs}],
    )
    filtered, dropped = _filter(bundle)
    assert dropped is True and filtered.interpretation_blocks == ()


# ---------------------------------------------------------------------------
# T04b review fold — the four holes an independent READ_ONLY review found in
# the attribution the fail-closed rule depends on.
# ---------------------------------------------------------------------------

def test_a_traversing_source_ref_is_not_attributed_by_its_prefix():
    """THE LEAK. ``family_for_source_ref`` matches a literal prefix, so
    ``data/baskets/../finviz_themes/private.json`` resolved to
    ``mastermind_curated`` — a permitted family — and was SERVED while naming
    a file in another family's directory. The first two asserts prove the leak
    was real rather than theoretical: the owner's table does map it, and the
    owner does permit that family."""
    from engine.theme_graph.rights import (
        assert_current_emission_allowed, family_for_source_ref, load_registry_snapshot,
    )

    ref = "data/baskets/../finviz_themes/private.json"
    assert family_for_source_ref(ref) == "mastermind_curated"
    assert_current_emission_allowed(["mastermind_curated"], snapshot=load_registry_snapshot())

    bundle = _bundle([_assertion("gmirca_" + "1" * 32, source_uri=ref)])
    filtered, dropped = _filter(bundle)
    assert dropped is True
    assert filtered.assertions == ()


@pytest.mark.parametrize("ref", [
    pytest.param("data/baskets/../finviz_themes/x.json", id="parent-segment"),
    pytest.param("data/baskets/./x.json", id="current-segment"),
    pytest.param("data/baskets/sub/../../baskets_hk/x.json", id="two-parents"),
    # LOAD-BEARING backslash case: the prefix matches, so only the backslash
    # branch can decline it. The earlier bare-backslash param passed because
    # no prefix matched it at all, which proved nothing.
    pytest.param("data/baskets/x\\..\\finviz_themes\\y.json", id="backslash-after-prefix"),
    pytest.param("data/baskets\\..\\finviz_themes\\x.json", id="backslash"),
    pytest.param("..", id="bare-parent"),
    # Percent-escaped traversal. RFC 3986 decodes %2E to "." before dot-segment
    # removal, so these are traversal to anything that dereferences the URI —
    # and with https prefixes in the table this is the NORMAL spelling.
    pytest.param("data/baskets/%2e%2e/finviz_themes/x.json", id="encoded-parent"),
    pytest.param("data/baskets/%2E%2E/finviz_themes/x.json", id="encoded-parent-upper"),
    pytest.param("data/baskets/..%2ffinviz_themes/x.json", id="encoded-slash"),
    pytest.param("data/baskets/.%2e/finviz_themes/x.json", id="half-encoded"),
    pytest.param("https://www.sec.gov/Archives/%2e%2e/%2e%2e/vendor/x.json",
                 id="encoded-parent-under-a-permitted-https-prefix"),
    pytest.param("https://www.sec.gov/Archives/..%2f..%2fvendor/x.json",
                 id="encoded-slash-under-a-permitted-https-prefix"),
])
def test_a_non_canonical_ref_is_never_attributed(ref):
    """The transport declines to attribute; it does NOT normalize. Resolving
    what a path really means would be this route forming a second opinion
    about someone else's namespace."""
    from app.theme_research import _attributable_family

    assert _attributable_family({"source_uri": ref}) is None


def test_a_locator_never_attributes_a_row():
    """``locator`` is a pointer INSIDE the cited document — the corpus fills it
    with ``para-3`` and ``table-1`` — not a path, and the v1.1 proposal names
    the rights dependency as ``family_for_source_ref(source_uri)`` with
    ``locator`` carrying no rights role. Two earlier readings were wrong in the
    same place: falling back to it let a paragraph pointer that happens to look
    like a repo path attribute a row the rights owner never attributed."""
    from app.theme_research import _attributable_family

    assert _attributable_family({"locator": "data/baskets/x.json"}) is None
    assert _attributable_family({"locator": "para-3"}) is None

    bundle = _bundle([_assertion("gmirca_" + "2" * 32, locator="data/baskets/x.json")])
    filtered, dropped = _filter(bundle)
    assert dropped is True and filtered.assertions == ()


def test_an_internal_pointer_never_contradicts_the_source_uri():
    """The mirror error, which the first repair introduced: treating the two
    fields as co-equal vetoes manufactures a contradiction out of an external
    URL and an internal pointer, and withholds a legitimate row."""
    from app.theme_research import _attributable_family

    assert _attributable_family({
        "source_uri": "data/baskets/x.json", "locator": "para-3",
    }) == "mastermind_curated"
    assert _attributable_family({
        "source_uri": "https://www.sec.gov/Archives/edgar/data/1/x.htm",
        "locator": "data/baskets/membership.json",
    }) == "sec_edgar"


def test_a_hostile_str_subclass_cannot_launder_a_source_uri():
    """``family_for_source_ref`` re-coerces with ``str()``, so a subclass whose
    ``__str__`` lies would be attributed by one string and serialised by
    another. Exact type only."""
    from app.theme_research import _attributable_family

    class Liar(str):
        def __str__(self) -> str:  # noqa: D105
            return "data/baskets/ok.json"

    assert _attributable_family(
        {"source_uri": Liar("finviz_themes/private.json")}) is None


@pytest.mark.parametrize("collection", [None, 7, "a string", object()])
def test_an_unreadable_collection_withholds_everything_instead_of_503ing(collection):
    """A collection this transport cannot iterate follows the same rule as a
    row it cannot read: withheld, never raised into the route's catch-all."""
    from app.theme_research import _rows_of

    assert _rows_of(collection) == ((), False)


def test_a_one_shot_iterable_is_not_consumed_into_a_silent_empty_response():
    """If ``assertions`` were iterated where it is, a generator would be spent
    and the composer would see nothing — while ``dropped`` stayed False, so the
    response would drop every row and report nothing withheld."""
    from app.theme_research import _rows_of

    rows, readable = _rows_of(iter([{"a": 1}, {"b": 2}]))
    assert readable is True and len(rows) == 2


@pytest.mark.parametrize("row", ["a string", 7, None, ["list"], ("tuple",)])
def test_a_non_mapping_assertion_is_withheld_and_never_raises(row):
    """It used to raise ``AttributeError`` into the route's catch-all, so ONE
    malformed row from the owner returned a 503 for the WHOLE request and
    denied the caller every row it was entitled to. The row withholds itself;
    its neighbours are still served."""
    good = "gmirca_" + "3" * 32
    bundle = _bundle([_assertion(good, source_uri="data/baskets/x.json"), row])
    filtered, dropped = _filter(bundle)
    assert dropped is True
    assert [a["curation_revision"] for a in filtered.assertions] == [good]


@pytest.mark.parametrize("source", ["a string", 7, ["list"]])
def test_a_non_mapping_source_is_withheld_and_never_raises(source):
    bundle = _bundle([{"curation_revision": "gmirca_" + "4" * 32, "source": source}])
    filtered, dropped = _filter(bundle)
    assert dropped is True and filtered.assertions == ()


def test_a_revision_is_compared_as_a_string_and_never_coerced():
    """``str()`` on both sides made the integer 12 and the string "12" the
    same revision, so a block naming a revision that was never served could
    survive. A curation revision is a string by its own contract."""
    bundle = _bundle(
        [{"curation_revision": 12, "source": {"source_uri": "data/baskets/x.json"}}],
        [{"interpretation_id": "i1", "mechanism": "m", "input_revisions": ["12"],
          "freshness": "current"}],
    )
    filtered, dropped = _filter(bundle)
    assert dropped is True
    assert filtered.interpretation_blocks == ()


def test_a_non_string_input_revision_never_matches_a_served_one():
    """The mirror image: a served revision "12" must not satisfy a block that
    names the integer 12."""
    bundle = _bundle(
        [_assertion("12", source_uri="data/baskets/x.json")],
        [{"interpretation_id": "i1", "mechanism": "m", "input_revisions": [12],
          "freshness": "current"}],
    )
    filtered, dropped = _filter(bundle)
    assert dropped is True and filtered.interpretation_blocks == ()


def test_a_tuple_input_list_is_read_exactly_like_a_list():
    """The ``tuple`` half of the accepted-shapes check had no coverage: an
    owner handing back an immutable input list must be read, not withheld."""
    rev = "gmirca_" + "5" * 32
    bundle = _bundle(
        [_assertion(rev, source_uri="data/baskets/x.json")],
        [{"interpretation_id": "i1", "mechanism": "m", "input_revisions": (rev,),
          "freshness": "current"}],
    )
    filtered, dropped = _filter(bundle)
    assert dropped is False and filtered is bundle


@pytest.mark.parametrize("block", ["a string", 7, None, ["list"]])
def test_a_non_mapping_interpretation_block_is_withheld_and_never_raises(block):
    rev = "gmirca_" + "6" * 32
    bundle = _bundle([_assertion(rev, source_uri="data/baskets/x.json")], [block])
    filtered, dropped = _filter(bundle)
    assert dropped is True and filtered.interpretation_blocks == ()


def test_an_edgar_filing_url_now_attributes_to_the_admitted_sec_edgar_family():
    """The gap this test used to PIN is closed, by ruling, not by inference.

    ``sec_edgar`` was admitted (b256aa6a756, qualified by 7d456cd37d8) and is
    ``direct_display_ok``, but no ``https://`` prefix existed, so a filing URL
    attributed to nothing and the fail-closed rule withheld the witnesses' own
    evidence — refused for want of a mapping rather than for want of a right.
    Sol #7780 issuecomment-5825621672 item 5 bound the exact recognition prefix
    ``https://www.sec.gov/Archives/`` to that family. This transport asks the
    owner and does not restate the decision.
    """
    from engine.theme_graph.rights import family_for_source_ref, load_registry_snapshot

    _revision, families = load_registry_snapshot()
    assert families["sec_edgar"]["rights_class"] == "direct_display_ok"

    rev = "gmirca_" + "7" * 32
    bundle = _bundle([_assertion(
        rev, source_uri="https://www.sec.gov/Archives/edgar/data/1046179/tsmc-6k.htm",
    )])
    assert family_for_source_ref(
        "https://www.sec.gov/Archives/edgar/data/1046179/tsmc-6k.htm"
    ) == "sec_edgar"
    filtered, dropped = _filter(bundle)
    assert dropped is False, "an EDGAR-sourced assertion is no longer withheld"
    assert [a["curation_revision"] for a in filtered.assertions] == [rev]


def test_a_recognition_only_publisher_is_named_and_still_withheld():
    """Sol item 6: recognition changes the refusal reason, not the result. The
    transport must withhold an ``unresolved`` family exactly as it withholds an
    unmapped one — the caller sees the same response either way."""
    bundle = _bundle([_assertion(
        "gmirca_" + "0" * 32,
        source_uri="https://www2.jpx.co.jp/disc/some-issuer/disclosure.html",
    )])
    filtered, dropped = _filter(bundle)
    assert dropped is True
    assert filtered.assertions == ()


def test_the_private_half_is_unbound_so_both_rules_are_inert_today():
    """Stated plainly: with R4 open the served bundle carries no assertion and
    no interpretation block, so neither rule changes a served response. They
    are the fail-closed default for the moment R4 binds them."""
    filtered, dropped = _filter(_bundle())
    assert dropped is False and filtered.assertions == ()
    assert filtered.interpretation_blocks == ()
