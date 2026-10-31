"""F11 selected-thesis read grounding — read-half tests (macro brain_gateway).

Loads ``engine/neuralweb/brain_gateway.py`` directly by path (no package
layout, no service-role key, no network): every read goes through a stubbed
``_user_plane_get``. Run with pytest; all caller-plane reads are synthetic stubs.

Tests use the real raw ai_context_client.v1 request and the server's compiled
F11 gate. Every caller-plane request is stubbed; no provider or database I/O.
"""

import importlib.util
import os
import sys
from pathlib import Path

import pytest


def _load_gateway():
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "..", "..", "engine", "neuralweb", "brain_gateway.py"),
        os.path.join(here, "..", "engine", "neuralweb", "brain_gateway.py"),
        os.path.join(here, "engine", "neuralweb", "brain_gateway.py"),
    ]
    for path in candidates:
        if os.path.exists(path):
            spec = importlib.util.spec_from_file_location("brain_gateway_under_test", path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            return module
    raise RuntimeError("brain_gateway.py not found relative to " + here)


gw = _load_gateway()

THESIS_ID = "11111111-1111-4111-8111-111111111111"
VERSION_ID = "22222222-2222-4222-8222-222222222222"
OTHER_VERSION_ID = "33333333-3333-4333-8333-333333333333"
JWT = "caller-jwt"

def grounded_context(focus):
    ambient = {"page": "analysis", "panel": "theses"}
    if focus is not None:
        ambient["thesis_read"] = focus
    return {"ai_context": {"schema": "ai_context_client.v1", "origin_id": "test-origin",
            "context_revision": 0, "captured_at": "2026-10-20T12:00:00Z",
            "pinned": [], "active": None, "ambient": ambient}}


def version_row(content=None, thesis_id=THESIS_ID, version_id=VERSION_ID, version=3,
                clock="2026-10-19T08:00:00+00:00"):
    return {
        "id": version_id,
        "thesis_id": thesis_id,
        "version": version,
        "content": {
            "title": "Rates stay higher longer",
            "statement": "Core inflation sticks above target through H1.",
            "falsifiers": ["Two consecutive soft CPI prints", "Guidance cut at the next meeting"],
            "evidence": {"payload": "SHOULD-NOT-APPEAR"},
            "revisionNote": "SHOULD-NOT-APPEAR",
            "notes": "SHOULD-NOT-APPEAR",
            "score": 99,
        } if content is None else content,
        "system_recorded_at": clock,
    }


class _Missing:
    pass


MISSING = _Missing()


class StubReads:
    """Route stubbed reads by table prefix; records every path + JWT used.

    ``MISSING`` simulates a read error (``_user_plane_get`` returning ``None``);
    the ``id=eq.<uuid>`` PostgREST filter in each path is applied like the real
    service would, so id-scoped reads answer exactly the matching row.
    """

    def __init__(self, theses=MISSING, versions=MISSING):
        self.theses = [{"id": THESIS_ID}] if theses is MISSING else theses
        self.versions = [version_row()] if versions is MISSING else versions
        self.paths = []
        self.tokens = []

    @staticmethod
    def _requested_id(path):
        for part in path.split("&"):
            if part.startswith("id=eq."):
                return part[len("id=eq."):]
        return None

    def __call__(self, path, user_jwt, timeout=5):
        self.paths.append(path)
        self.tokens.append(user_jwt)
        if path.startswith("theses?"):
            rows = self.theses
            if rows is None:
                return None
            wanted = self._requested_id(path)
            return [row for row in rows if wanted is None or str(row.get("id")) == wanted]
        if path.startswith("thesis_versions?"):
            rows = self.versions
            if rows is None:
                return None
            wanted = self._requested_id(path)
            return [row for row in rows if wanted is None or str(row.get("id")) == wanted]
        return []


@pytest.fixture(autouse=True)
def restore_reads():
    original = gw._user_plane_get
    yield
    gw._user_plane_get = original


def stub(stub_reads):
    gw._user_plane_get = stub_reads


# --- focus extraction -------------------------------------------------------

def test_no_context_means_no_focus():
    assert gw._research_thesis_focus(None) is None
    assert gw._research_thesis_focus({}) is None


def test_ungrounded_turn_never_considers_a_focus():
    context = grounded_context({"thesis_id": THESIS_ID, "version_id": VERSION_ID})
    assert gw._research_thesis_focus(context) is None


def test_absent_focus_on_grounded_turn_is_none():
    assert gw._research_thesis_focus(grounded_context(None), grounded=True) is None


def test_grounded_focus_extracted_strict():
    focus = gw._research_thesis_focus(
        grounded_context({"thesis_id": THESIS_ID, "version_id": VERSION_ID}), grounded=True)
    assert focus == {"thesis_id": THESIS_ID, "version_id": VERSION_ID}


def test_malformed_focus_fails_closed_never_best_effort():
    bad = [
        {"thesis_id": THESIS_ID},                       # missing key
        {"thesis_id": THESIS_ID, "version_id": VERSION_ID, "extra": 1},  # extra key
        {"thesis_id": THESIS_ID, "version_id": "not-a-uuid"},
        {"thesis_id": THESIS_ID, "version_id": "ABCDEFAB-CDEF-ACDF-ADEF-ABCDEFABCDEF"},  # not lowercase
        {"thesis_id": "chart", "version_id": VERSION_ID},                # arbitrary string
        "chart",                                        # not a dict
    ]
    for focus in bad:
        result = gw._research_thesis_focus(grounded_context(focus), grounded=True)
        assert isinstance(result, dict) and "rejected" in result, focus


# --- selected read ----------------------------------------------------------

def test_selected_read_happy_path_allowlist_only():
    reads = StubReads()
    stub(reads)
    outcome = {}
    artifact = gw._research_selected_thesis_artifact(JWT, THESIS_ID, VERSION_ID, outcome=outcome)
    assert outcome["state"] == "ok"
    assert artifact is not None
    body = artifact["body"]
    assert "Rates stay higher longer" in body
    assert "Core inflation sticks above target through H1." in body
    assert "Two consecutive soft CPI prints" in body
    for forbidden in ("SHOULD-NOT-APPEAR", "payload"):
        assert forbidden not in body
    # Immutable provenance stays structured, with the real server clock.
    prov = artifact["thesis_read"]
    assert prov["kind"] == "selected_immutable_version"
    assert prov["thesis_id"] == THESIS_ID and prov["version_id"] == VERSION_ID
    assert prov["version"] == 3 and prov["system_recorded_at"] == "2026-10-19T08:00:00+00:00"
    # Reads are exact-id, caller-plane, limit-2 — never a broad list.
    assert reads.tokens == [JWT, JWT]
    assert all("id=eq." in path and "limit=2" in path for path in reads.paths)


def test_changed_statement_or_falsifiers_change_the_selected_corpus():
    stub(StubReads())
    before = gw._research_selected_thesis_artifact(JWT, THESIS_ID, VERSION_ID)["body"]
    stub(StubReads(versions=[version_row(
        content={
            "title": "Rates stay higher longer",
            "statement": "Inflation re-accelerates instead.",
            "falsifiers": ["One hot CPI print"],
        })]))
    after = gw._research_selected_thesis_artifact(JWT, THESIS_ID, VERSION_ID)["body"]
    assert before != after
    assert "Inflation re-accelerates instead." in after
    assert "One hot CPI print" in after
    assert "Core inflation sticks above target" not in after


def test_selected_immutable_version_is_stable_when_head_advances():
    stub(StubReads())
    selected = gw._research_selected_thesis_artifact(JWT, THESIS_ID, VERSION_ID)
    # The head moves on (a version 4 exists); the id-scoped read still answers
    # EXACTLY the selected row — same bytes, never the new head.
    stub(StubReads(
        theses=[{"id": THESIS_ID}],
        versions=[version_row(version_id=OTHER_VERSION_ID, version=4,
                              content={"title": "NEW HEAD", "statement": "New head text.",
                                       "falsifiers": []})]
        + [version_row()],
    ))
    again = gw._research_selected_thesis_artifact(JWT, THESIS_ID, VERSION_ID)
    assert selected["body"] == again["body"]
    assert selected["thesis_read"]["version"] == 3


def test_fail_closed_matrix():
    cases = [
        ("unavailable", StubReads(theses=None, versions=[version_row()])),   # read error
        ("unavailable", StubReads(theses=[{"id": THESIS_ID}], versions=None)),
        ("rejected", StubReads(theses=[], versions=[version_row()])),        # missing thesis
        ("rejected", StubReads(theses=[{"id": THESIS_ID}, {"id": THESIS_ID}],
                               versions=[version_row()])),                   # duplicate
        ("rejected", StubReads(theses=[{"id": "44444444-4444-4444-8444-444444444444"}],
                               versions=[version_row()])),                   # id mismatch
        ("rejected", StubReads(theses=[{"id": THESIS_ID}], versions=[])),    # missing version
        ("rejected", StubReads(theses=[{"id": THESIS_ID}],
                               versions=[version_row(), version_row()])),    # duplicate
        ("rejected", StubReads(theses=[{"id": THESIS_ID}],
                               versions=[version_row(thesis_id="44444444-4444-4444-8444-444444444444")])),
        ("rejected", StubReads(theses=[{"id": THESIS_ID}],
                               versions=[version_row(version=0)])),          # version shape
        ("rejected", StubReads(theses=[{"id": THESIS_ID}],
                               versions=[version_row(clock="")])),           # clock shape
        ("rejected", StubReads(theses=[{"id": THESIS_ID}],
                               versions=[version_row(clock=None)])),
        ("rejected", StubReads(theses=[{"id": THESIS_ID}],
                               versions=[version_row(content="prose")])),    # content shape
        ("rejected", StubReads(theses=[{"id": THESIS_ID}],
                               versions=[version_row(content={"title": "t"})])),  # no statement
    ]
    for expected, reads in cases:
        stub(reads)
        outcome = {}
        artifact = gw._research_selected_thesis_artifact(JWT, THESIS_ID, VERSION_ID, outcome=outcome)
        assert artifact is None, expected
        assert outcome["state"] == expected, expected


def test_authenticated_denial_is_unavailable_never_empty():
    # A 401/403 from the caller-plane read maps to [] inside _user_plane_get —
    # but an env/network failure maps to None, and None must stay "unavailable"
    # (never an empty-ok that would read as "nothing selected").
    stub(StubReads(theses=None, versions=None))
    outcome = {}
    assert gw._research_selected_thesis_artifact(JWT, THESIS_ID, VERSION_ID, outcome=outcome) is None
    assert outcome["state"] == "unavailable"


def test_no_clock_is_ever_manufactured():
    stub(StubReads(versions=[version_row(clock="2026-10-19T08:00:00+00:00")]))
    artifact = gw._research_selected_thesis_artifact(JWT, THESIS_ID, VERSION_ID)
    assert artifact["asof"].startswith("2026-10-19")
    assert artifact["thesis_read"]["system_recorded_at"] == "2026-10-19T08:00:00+00:00"


def test_budget_truncation_and_conditions_cap():
    # A short statement: the conditions CAP (20) is what truncates, visibly.
    many = [f"condition {i}" for i in range(40)]
    stub(StubReads(versions=[version_row(content={
        "title": "T", "statement": "Short statement.", "falsifiers": many})]))
    artifact = gw._research_selected_thesis_artifact(JWT, THESIS_ID, VERSION_ID)
    assert len(artifact["body"]) <= 1200  # existing user-corpus budget
    assert "condition 19" in artifact["body"] and "condition 20" not in artifact["body"]
    assert "truncated" in artifact["coverage"].lower()


def test_budget_clamps_extremely_long_content():
    # A huge statement: the existing 1200-char user-corpus budget is the clamp;
    # the coverage note still names the truncation.
    huge = {"title": "T", "statement": "S" * 5000,
            "falsifiers": [f"condition {i}" for i in range(40)]}
    stub(StubReads(versions=[version_row(content=huge)]))
    artifact = gw._research_selected_thesis_artifact(JWT, THESIS_ID, VERSION_ID)
    assert len(artifact["body"]) <= 1200
    assert artifact["body"].count("S") <= 900
    assert "truncated" in artifact["coverage"].lower()


# --- corpus wiring ----------------------------------------------------------

def test_broad_corpus_unchanged_without_focus():
    reads = StubReads(theses=[
        {"id": THESIS_ID, "current_version": 3, "lifecycle_state": "active",
         "updated_at": "2026-10-19T08:00:00+00:00"}],
        versions=[version_row()])
    stub(reads)
    corpus = gw._build_research_corpus(Path("/nonexistent-f11-synthetic-root"), user_jwt=JWT)
    assert "thesis_read" not in corpus
    assert corpus["user_read"] == "ok"
    assert [a["plain_en"] for a in corpus["artifacts"]].count("Your theses") == 1
    corpus_no_jwt = gw._build_research_corpus(Path("/nonexistent-f11-synthetic-root"), user_jwt="")
    assert corpus_no_jwt["user_read"] == "absent" and not corpus_no_jwt["jwt_present"]


def test_selected_read_replaces_generic_user_artifacts():
    stub(StubReads(theses=[
        {"id": THESIS_ID, "current_version": 3, "lifecycle_state": "active",
         "updated_at": "2026-10-19T08:00:00+00:00"}],
        versions=[version_row()]))
    corpus = gw._build_research_corpus(
        Path("/nonexistent-f11-synthetic-root"), user_jwt=JWT,
        context=grounded_context({"thesis_id": THESIS_ID, "version_id": VERSION_ID}), grounded=True)
    plain = [a["plain_en"] for a in corpus["artifacts"]]
    assert "Your theses" not in plain and "Your thesis versions" not in plain
    assert "Your selected thesis" in plain
    assert corpus["thesis_read"]["state"] == "ok"


def test_failed_focus_never_degrades_to_generic_artifacts():
    stub(StubReads(theses=[], versions=[]))  # foreign/missing selection
    corpus = gw._build_research_corpus(
        Path("/nonexistent-f11-synthetic-root"), user_jwt=JWT,
        context=grounded_context({"thesis_id": THESIS_ID, "version_id": VERSION_ID}), grounded=True)
    plain = [a["plain_en"] for a in corpus["artifacts"]]
    assert "Your theses" not in plain and "Your selected thesis" not in plain
    assert corpus["thesis_read"]["state"] == "rejected"


def test_used_list_distinguishes_selected_immutable_version():
    stub(StubReads())
    corpus = gw._build_research_corpus(
        Path("/nonexistent-f11-synthetic-root"), user_jwt=JWT,
        context=grounded_context({"thesis_id": THESIS_ID, "version_id": VERSION_ID}), grounded=True)
    used = gw._format_used_list(corpus)
    assert "Selected thesis version 3" in used
    broad_used = gw._format_used_list(gw._build_research_corpus(Path("/nonexistent-f11-synthetic-root"), user_jwt=JWT))
    assert "Selected thesis version" not in broad_used  # broad output untouched


def test_used_list_names_failed_selected_read_explicitly():
    stub(StubReads(theses=[], versions=[]))
    corpus = gw._build_research_corpus(
        Path("/nonexistent-f11-synthetic-root"), user_jwt=JWT,
        context=grounded_context({"thesis_id": THESIS_ID, "version_id": VERSION_ID}), grounded=True)
    used = gw._format_used_list(corpus)
    assert "not available for this account" in used
    stub(StubReads(theses=None, versions=None))
    corpus = gw._build_research_corpus(
        Path("/nonexistent-f11-synthetic-root"), user_jwt=JWT,
        context=grounded_context({"thesis_id": THESIS_ID, "version_id": VERSION_ID}), grounded=True)
    assert "could not be read this turn" in gw._format_used_list(corpus)


def test_wrong_selection_forces_canonical_research_null():
    stub(StubReads(theses=[], versions=[]))
    corpus = gw._build_research_corpus(
        Path("/nonexistent-f11-synthetic-root"), user_jwt=JWT,
        context=grounded_context({"thesis_id": THESIS_ID, "version_id": VERSION_ID}), grounded=True)
    body, withheld = gw._research_postprocess(
        "Here is a confident answer from general knowledge.", corpus)
    assert body.startswith(gw._RESEARCH_NULL_EN)
    assert not withheld
    # Without a focus, a citing answer still passes through unchanged in shape.
    stub(StubReads())
    broad = gw._build_research_corpus(Path("/nonexistent-f11-synthetic-root"), user_jwt=JWT)
    body_broad, _ = gw._research_postprocess(
        f"Grounded sentence citing {_RESEARCH_CITE_TOKEN(broad)}.", broad)
    assert not body_broad.startswith(gw._RESEARCH_NULL_EN)


def _RESEARCH_CITE_TOKEN(corpus):
    """A token _research_cites_artifact accepts for the first broad artifact."""
    first = corpus["artifacts"][0]
    return first["plain_en"]


def test_ok_selection_still_answers_from_the_selected_artifact():
    stub(StubReads())
    corpus = gw._build_research_corpus(
        Path("/nonexistent-f11-synthetic-root"), user_jwt=JWT,
        context=grounded_context({"thesis_id": THESIS_ID, "version_id": VERSION_ID}), grounded=True)
    body, withheld = gw._research_postprocess(
        f"The selected thesis says: {_RESEARCH_CITE_TOKEN(corpus)}.", corpus)
    assert not body.startswith(gw._RESEARCH_NULL_EN)
    assert not withheld


@pytest.mark.parametrize("index", [0, 1], ids=["sync", "stream"])
def test_actual_handler_calls_reach_selected_version_reader(index):
    import ast
    from engine.intelligence_workspace import context_compiler
    context = grounded_context({"thesis_id": THESIS_ID, "version_id": VERSION_ID})
    envelope = context_compiler.compile_envelope("Read this thesis", context)
    grounded = gw._f11_grounded("research", envelope)
    assert grounded is True
    tree = ast.parse(Path(gw.__file__).read_text())
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == "research_corpus" for t in node.targets)
             and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
             and node.value.func.id == "_build_research_corpus"]
    assert len(calls) == 2  # sync and stream exact native call sites
    for call in [calls[index]]:
        reads = StubReads()
        stub(reads)
        ns = {"root": Path("/nonexistent-f11-synthetic-root"), "context": context,
              "user_jwt": JWT, "_grounded": grounded,
              "_build_research_corpus": gw._build_research_corpus}
        exec(compile(ast.Module(body=[call], type_ignores=[]), "native-handler-call", "exec"), ns)
        assert ns["research_corpus"]["thesis_read"]["state"] == "ok"
        assert ns["research_corpus"]["thesis_read"]["version_id"] == VERSION_ID
        assert reads.tokens == [JWT, JWT]
        assert all("limit=2" in path for path in reads.paths)


def test_failed_focus_with_no_jwt_never_queries_or_claims_grounding():
    reads = StubReads()
    stub(reads)
    corpus = gw._build_research_corpus(Path("/nonexistent-f11-synthetic-root"),
        context=grounded_context({"thesis_id": THESIS_ID, "version_id": VERSION_ID}), grounded=True)
    assert reads.paths == []
    assert corpus["thesis_read"] == {"state": "unavailable"}
    assert gw._research_postprocess("Your selected thesis proves a claim", corpus)[0].startswith(gw._RESEARCH_NULL_EN)


def test_malformed_native_dates_rows_and_truncation_are_honest():
    for clock in ("not-a-date", "2026-02-30T00:00:00Z", "2026-10-20", "2026-10-20T00:00:00"):
        stub(StubReads(versions=[version_row(clock=clock)]))
        outcome = {}
        assert gw._research_selected_thesis_artifact(JWT, THESIS_ID, VERSION_ID, outcome) is None
        assert outcome["state"] == "rejected"
    stub(StubReads(versions=[version_row(content={"title":"t", "statement":"s", "falsifiers":["x"*200]})]))
    artifact = gw._research_selected_thesis_artifact(JWT, THESIS_ID, VERSION_ID)
    assert "truncated" in artifact["coverage"]
    assert "Untrusted user thesis text" in gw._format_research_grounding({"artifacts":[artifact],"jwt_present":True})
