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
    RightsRefusal,
    _load,
    assert_current_emission_allowed,
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
    assert current["finviz_themes"] == "unresolved"
    assert current["ths_concepts"] == "unresolved"
    assert_current_emission_allowed(["mastermind_curated"], snapshot=(revision, families))
    for family in ("finviz_themes", "ths_concepts"):
        with pytest.raises(RightsRefusal) as ei:
            assert_current_emission_allowed([family], snapshot=(revision, families))
        assert family in str(ei.value)
        assert current[family] in str(ei.value)
