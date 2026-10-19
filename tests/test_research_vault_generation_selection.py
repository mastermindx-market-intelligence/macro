"""Retain only the bytes actually qualified by the canonical consumer sweep."""
from collections import Counter
import hashlib
import pytest
from tests import test_research_vault_producer_generation as fixture

pg = fixture.pg


def select(store, **overrides):
    args = dict(expected_producer_commit=fixture.COMMIT, now=fixture.NOW,
                max_age_seconds=fixture.MAX_AGE_SECONDS, writer_protocol_qualified=True)
    args.update(overrides)
    return pg.explained_selection(store, **args)


def seeded():
    store = fixture.MemoryStore()
    fixture.build_generation(store, fixture.spec_with(19, {"none": 1}))
    return store


def test_selected_bytes_and_token_are_exact_and_immutable():
    store = seeded()
    selected, reason = select(store)
    assert reason is None
    assert selected.catalog_bytes is store.objects[pg.GENERATION_CATALOG_KEY]
    assert selected.catalog_version == store.versions[pg.GENERATION_CATALOG_KEY]
    assert selected.corpus_bytes is store.corpus
    assert selected.catalog_sha256 == hashlib.sha256(selected.catalog_bytes).hexdigest()
    assert selected.corpus_sha256 == hashlib.sha256(selected.corpus_bytes).hexdigest()
    assert selected.producer_source_commit == fixture.COMMIT
    assert selected.qualified_at == fixture.NOW
    assert selected.completed_at == fixture.COMPLETED_AT
    with pytest.raises(AttributeError):
        selected.catalog_bytes = b"changed"


def test_selection_reuses_the_single_qualification_sweep_without_extra_reads():
    store = seeded()
    selected, reason = select(store)
    assert selected is not None and reason is None
    counts = Counter(store.reads)
    assert counts[("versioned", pg.GENERATION_CATALOG_KEY)] == 2
    assert counts[("corpus", "*")] == 1
    assert all(n == 1 for (kind, key), n in counts.items() if kind == "strict")
    assert sum(n for (kind, key), n in counts.items() if kind == "strict") == 40


def test_final_fence_movement_discards_selected_body():
    store = seeded()
    store.midflight = lambda s: s.set_object(pg.GENERATION_CATALOG_KEY,
                                           s.objects[pg.GENERATION_CATALOG_KEY])
    selected, reason = select(store)
    assert selected is None
    assert reason["code"] == "catalog_moved"


@pytest.mark.parametrize("change,expected", [
    (dict(writer_protocol_qualified=False), "writer_protocol_qualified_required"),
    (dict(expected_producer_commit="invalid"), "expected_producer_commit_invalid"),
    (dict(now=True), "now_invalid"),
    (dict(max_age_seconds=-1), "max_age_seconds_invalid"),
])
def test_preflight_refuses_without_any_body_or_io(change, expected):
    store = seeded()
    selected, reason = select(store, **change)
    assert selected is None and reason["code"] == expected
    assert store.reads == []


def test_default_gate_and_boolean_compatibility():
    store = seeded()
    selected, reason = pg.explained_selection(store,
        expected_producer_commit=fixture.COMMIT, now=fixture.NOW,
        max_age_seconds=fixture.MAX_AGE_SECONDS)
    assert selected is None and store.reads == []
    assert fixture.run(store) == (True, None)
    store.corpus = b"wrong corpus"
    selected, reason = select(store)
    assert selected is None and reason["code"] == "corpus_mismatch"
    assert fixture.run(store) == (False, reason)
