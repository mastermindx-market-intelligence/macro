"""Item 2 — the publication primitives B uses, proven from B's side.

Sol #7780 asked B to return an exact map of the accepted data and control
primitives, their representation and budgets, and native **absent / create /
read / identical-replay / stale-predecessor / supersession** tests. This is
the test half; the map is in the return comment and in the module docstring
table below.

**No new store.** B publishes nothing and owns no bucket. Everything here
exercises the Company Intelligence owner's existing primitives — the writer
``engine.company_intelligence.event_workspace.write_workspace_generation``,
its validator, and the reader's model-facing surfaces — and asserts what the
semiconductor binder does on top of each case. Where the owner's own suite
already proves a leg, this suite proves the leg B depends on rather than
restating it (``tests/test_company_intelligence_event_workspace.py``,
``tests/test_company_intelligence_neural_reader.py``,
``tests/test_publish_company_intelligence_r2.py``).

The accepted primitives, measured on a two-issuer / two-period nest:

===============================  ==========================================  ========
primitive                        representation                              bytes
===============================  ==========================================  ========
``event_workspaces/manifest``    the ONE mutable control object: the marker.  1 820
   .json                         Closed key set ``event_workspace_manifest
                                 .v2`` — schema, status, generated_at,
                                 generation_id, event_count, files{path ->
                                 {bytes, sha256}}, aliases{alias -> canonical
                                 event id}, warnings, authority
                                 ("context_only"), previous_generation_id,
                                 previous_manifest_sha256.
``generations/<24hex>/           the same bytes, immutable at a
   manifest.json``               content-addressed key.                       1 820
``generations/<24hex>/           one immutable data object per event,         7 710
   workspaces/<event_id>.json``  receipted by bytes+sha256 in the manifest.   - 8 489
===============================  ==========================================  ========

Budget: ~1.8 KB of control plane per generation plus ~8 KB per event; a
two-issuer, two-period generation is **36 038 bytes across 6 objects**. The
binder reads at most FOUR objects per witness request (marker, immutable
manifest, current object, preceding object) and never walks the predecessor
chain — that walk is O(hops) and is what the 153 s incident was.

Control semantics B relies on and does not re-implement: immutable objects
are published BEFORE the marker; an existing immutable key must prove
byte-identity or the publish is a hard collision; the marker moves under a
compare-and-swap on its etag, so a concurrent publisher loses with
``PUBLISH_CONFLICT`` rather than interleaving; and the generation id folds
``previous_generation_id``, so an identical payload set published as a
successor is a DIFFERENT generation while a true replay is the same one.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.company_intelligence.event_workspace import (
    WorkspaceError,
    validate_workspace_manifest,
    write_workspace_generation,
)
from engine.market_ontology.semiconductor_owner_bundle import (
    WORKSPACE_UNAVAILABLE,
    load_semiconductor_owner_bundle,
)
from engine.market_ontology.semiconductor_theme_research import ResearchQuery
from engine.market_ontology.semiconductor_witness_scope import (
    SLICE_SCOPE_UNOWNED,
    WitnessIdentity,
    WitnessScope,
)
from engine.neuralweb import company_intelligence_reader as reader
from tests.semiconductor_research_helpers import (
    nest_files,
    wire_witness_nest,
    witness_workspace_payloads,
)
from engine.market_ontology import semiconductor_owner_bundle as loader_module

_TSM = WitnessIdentity(ticker="TSM", company_node_id="co:us:TSM",
                       issuer_id="ISS:US-XNYS-TSM", cik="0001046179")
_SNAPSHOT = ("rights_synthetic_snapshot", {})
_MARKER = "company_intelligence/event_workspaces/manifest.json"


def _query(**overrides) -> ResearchQuery:
    fields = dict(anchor_theme_id="ai_semiconductors", slice_key="hbm_packaging",
                  view="economics", time_mode="latest", source_cutoff=None,
                  recorded_cutoff=None, offset=0, limit=50, expected_generation=None)
    fields.update(overrides)
    return ResearchQuery(**fields)


def _pin(monkeypatch, *identities):
    scope = WitnessScope(slice_key="hbm_packaging", identities=tuple(identities),
                         omissions=(SLICE_SCOPE_UNOWNED,))
    monkeypatch.setattr(loader_module, "resolve_witness_scope", lambda key: scope)


def _write(out: Path, payloads: dict, **kwargs) -> dict:
    write_workspace_generation(out, payloads, generated_at="2026-09-24T15:00:00Z",
                               status="ready", **kwargs)
    return json.loads((out / "event_workspaces" / "manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def payloads() -> dict:
    return witness_workspace_payloads()


# ---------------------------------------------------------------------------
# 1. ABSENT — the control object exists, the witness does not
# ---------------------------------------------------------------------------

def test_native_absent_is_a_typed_omission_not_a_failure(tmp_path, monkeypatch, payloads):
    """A published nest that simply does not carry this witness is the normal
    steady state for a newly enrolled issuer. It must degrade the panel with a
    named omission, never fail the request and never invent coverage."""
    only_on = {k: v for k, v in payloads.items() if "0001097864" in k}
    assert only_on, "the ON workspaces are the non-witness half of this case"
    out = tmp_path / "company_intelligence"
    _write(out, only_on)
    wire_witness_nest(monkeypatch, nest_files(out))
    _pin(monkeypatch, _TSM)
    bundle = load_semiconductor_owner_bundle(_query(), rights_snapshot=_SNAPSHOT)
    assert bundle.event_workspaces == ()
    assert f"{WORKSPACE_UNAVAILABLE}.TSM" in bundle.omissions
    assert not any(o.startswith("workspace_unverified") for o in bundle.omissions)


# ---------------------------------------------------------------------------
# 2. CREATE — the first generation
# ---------------------------------------------------------------------------

def test_native_create_writes_a_marker_immutable_manifest_and_receipted_objects(tmp_path, payloads):
    """The producer creates the whole nest: one mutable marker, the same bytes
    immutable under a content-addressed generation key, and one receipted
    object per event. B adds no object of its own."""
    out = tmp_path / "company_intelligence"
    marker = _write(out, payloads)
    validate_workspace_manifest(marker)
    assert marker["schema"] == "event_workspace_manifest.v2"
    assert marker["authority"] == "context_only"
    assert marker["previous_generation_id"] is None
    assert marker["previous_manifest_sha256"] is None
    gen_dir = out / "event_workspaces" / "generations" / marker["generation_id"]
    assert (gen_dir / "manifest.json").read_bytes() == (
        out / "event_workspaces" / "manifest.json").read_bytes()
    for relative, receipt in marker["files"].items():
        body = (gen_dir / relative).read_bytes()
        assert len(body) == receipt["bytes"]
        import hashlib
        assert hashlib.sha256(body).hexdigest() == receipt["sha256"]
    # Every alias the binder can ask for resolves to a canonical id it can read.
    for alias, canonical in marker["aliases"].items():
        assert f"workspaces/{canonical}.json" in marker["files"], alias


# ---------------------------------------------------------------------------
# 3. READ — every byte the binder consumes is receipted
# ---------------------------------------------------------------------------

def test_native_read_consumes_only_receipted_objects_and_at_most_four_per_witness(
    tmp_path, monkeypatch, payloads,
):
    """The binder's read is marker → immutable manifest → current object →
    preceding object. Four objects per witness, all receipted, and never the
    predecessor chain (that walk is O(hops))."""
    out = tmp_path / "company_intelligence"
    marker = _write(out, payloads)
    calls = wire_witness_nest(monkeypatch, nest_files(out))
    _pin(monkeypatch, _TSM)
    bundle = load_semiconductor_owner_bundle(_query(), rights_snapshot=_SNAPSHOT)
    assert len(bundle.event_workspaces) == 2
    assert len(calls) == 4, calls
    receipted = {f"workspaces/{Path(u).name}" for u in calls if "/workspaces/" in u}
    assert receipted <= set(marker["files"]), receipted - set(marker["files"])
    assert not any("source_revisions" in url or "raw" in url for url in calls), calls


# ---------------------------------------------------------------------------
# 4. IDENTICAL REPLAY — the same inputs are the same generation
# ---------------------------------------------------------------------------

def test_identical_replay_is_the_same_generation_and_the_same_answer(
    tmp_path, monkeypatch, payloads,
):
    """Re-publishing the same payloads yields the same generation id and
    byte-identical objects, so a replay is an idempotent no-op at the store
    and cannot change what the binder serves. This is what lets a nightly run
    that found nothing new be safe to repeat."""
    first = tmp_path / "a" / "company_intelligence"
    second = tmp_path / "b" / "company_intelligence"
    marker_a = _write(first, payloads)
    marker_b = _write(second, payloads)
    assert marker_a["generation_id"] == marker_b["generation_id"]
    assert (first / "event_workspaces" / "manifest.json").read_bytes() == (
        second / "event_workspaces" / "manifest.json").read_bytes()
    assert marker_a["files"] == marker_b["files"]

    answers = []
    for root in (first, second):
        wire_witness_nest(monkeypatch, nest_files(root))
        _pin(monkeypatch, _TSM)
        bundle = load_semiconductor_owner_bundle(_query(), rights_snapshot=_SNAPSHOT)
        answers.append((tuple(w["event_id"] for w in bundle.event_workspaces),
                        bundle.omissions, bundle.revision_tuple))
    assert answers[0] == answers[1]


# ---------------------------------------------------------------------------
# 5. STALE PREDECESSOR — a chain link that no longer describes the parent
# ---------------------------------------------------------------------------

def test_stale_predecessor_link_is_refused_by_the_owner_and_never_walked_by_the_binder(
    tmp_path, monkeypatch, payloads,
):
    """A successor names its parent by id AND by that parent's manifest
    sha256. Two facts B returns rather than assumes:

    * the STANDALONE validator enforces only the link's SHAPE — both fields
      null together or both well-formed, never self-referential. It sees one
      manifest and cannot fetch a parent, so a link whose sha does not match
      the parent it names passes validation. Verified below.
    * the link is checked against the predecessor's RAW FETCHED BYTES in
      exactly one place: the reader's predecessor WALK
      (``company_intelligence_reader`` raises ``WorkspaceChainIntegrityError``
      on a mismatch or a missing parent). That walk is O(hops) — the 153 s
      incident — and is the surface B deliberately does not use.

    So on B's read path the chain link is provenance, not an integrity
    control, and B does not need it to be one: the binder reads the CURRENT
    generation, whose every object is receipt-verified against the manifest
    it came with, and steps ONE fiscal label back through an alias in that
    same manifest. A chain that is long, forked, or stale costs it nothing
    and can mislead it about nothing.
    """
    parent = tmp_path / "p" / "company_intelligence"
    parent_marker = _write(parent, payloads)
    parent_sha = __import__("hashlib").sha256(
        (parent / "event_workspaces" / "manifest.json").read_bytes()).hexdigest()

    child = tmp_path / "c" / "company_intelligence"
    child_marker = _write(child, payloads,
                          previous_generation_id=parent_marker["generation_id"],
                          previous_manifest_sha256=parent_sha)
    validate_workspace_manifest(child_marker)
    # Folding the parent into the identity is what makes a successor distinct
    # from a replay even when the payloads are identical.
    assert child_marker["generation_id"] != parent_marker["generation_id"]

    # A stale link — well-formed, but not the parent's actual sha — PASSES
    # standalone validation. This is the fact, not a wish.
    stale = dict(child_marker)
    stale["previous_manifest_sha256"] = "0" * 64
    validate_workspace_manifest(stale)
    # The only byte-level verification of the link lives on the walk B avoids:
    # the reader hashes the predecessor's RAW FETCHED BYTES and raises. If
    # this ever moves onto a surface B uses, that is a design change B should
    # see, so the pin names both the check and the error class.
    walk_source = Path(reader.__file__).read_text(encoding="utf-8")
    assert "sha256(predecessor_bytes).hexdigest()" in walk_source
    assert "WorkspaceChainIntegrityError" in walk_source
    assert "previous_manifest_sha256" not in Path(
        loader_module.__file__).read_text(encoding="utf-8"), (
        "the binder must not read the chain link"
    )

    # The SHAPE laws the validator does enforce.
    for broken in ({"previous_generation_id": None},
                   {"previous_manifest_sha256": None},
                   {"previous_generation_id": child_marker["generation_id"]}):
        candidate = dict(child_marker)
        candidate.update(broken)
        with pytest.raises(WorkspaceError):
            validate_workspace_manifest(candidate)

    # And the binder: it serves from the child without touching the parent.
    calls = wire_witness_nest(monkeypatch, nest_files(child))
    _pin(monkeypatch, _TSM)
    bundle = load_semiconductor_owner_bundle(_query(), rights_snapshot=_SNAPSHOT)
    assert len(bundle.event_workspaces) == 2
    assert len(calls) == 4
    assert not any(parent_marker["generation_id"] in url for url in calls), calls


# ---------------------------------------------------------------------------
# 6. SUPERSESSION — the marker moves; the binder follows it
# ---------------------------------------------------------------------------

def test_supersession_moves_the_marker_and_the_binder_follows_it(
    tmp_path, monkeypatch, payloads,
):
    """A later generation supersedes the marker while every earlier immutable
    object stays addressable. The binder must serve the NEW generation — the
    reader's 300-second snapshot cache is the one thing that could serve a
    superseded answer, so the proof clears it exactly as the reader's own
    contract requires and checks the generation the binder reports."""
    root = tmp_path / "company_intelligence"
    first_marker = _write(root, payloads)
    first_gen = first_marker["generation_id"]

    corrected = {k: dict(v) for k, v in payloads.items()}
    victim = sorted(k for k in corrected if "0001046179" in k)[-1]
    corrected[victim] = {**corrected[victim], "_supersession_probe": "second generation"}
    first_sha = __import__("hashlib").sha256(
        (root / "event_workspaces" / "manifest.json").read_bytes()).hexdigest()
    second_marker = _write(root, corrected, previous_generation_id=first_gen,
                           previous_manifest_sha256=first_sha)
    assert second_marker["generation_id"] != first_gen
    assert second_marker["previous_generation_id"] == first_gen
    # The superseded generation is still addressable — supersession is not
    # deletion, which is what makes an in-flight read safe.
    assert (root / "event_workspaces" / "generations" / first_gen / "manifest.json").is_file()

    wire_witness_nest(monkeypatch, nest_files(root))
    _pin(monkeypatch, _TSM)
    bundle = load_semiconductor_owner_bundle(_query(), rights_snapshot=_SNAPSHOT)
    generations = {value for kind, value in bundle.revision_tuple if kind == "generation"}
    assert generations == {second_marker["generation_id"]}, generations
    assert first_gen not in generations
