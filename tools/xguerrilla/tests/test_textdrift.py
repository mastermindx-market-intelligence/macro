"""Laws for ``xguerrilla.textdrift`` — the §26.8 persona-drift check.

The check is what tells a cell that its children are converging. These tests
hold the arithmetic (cosine, centroids), the scoping rule that only siblings
in one cell are compared, and the refusal to score a child that has barely
posted. Everything is synthetic and offline: no rail, no browser, no clock.

Note the harness quirk — pytest runs from the repo root, and the ``conftest``
already put ``tools/`` on ``sys.path`` so the package imports as ``xguerrilla``.
"""

from __future__ import annotations

import math

import pytest

from xguerrilla import config, textdrift

THRESHOLD = 0.55


def corpus(*sentences: str, repeats: int = 3) -> list[str]:
    """A child's history: each sentence repeated, always 3+ posts."""
    return [sentence for _ in range(repeats) for sentence in sentences]


# ---------------------------------------------------------------------------
# 1. vectorize — lowercase, punctuation, token floor, stopwords, weighting
# ---------------------------------------------------------------------------


def test_vectorize_lowercases_and_strips_punctuation():
    vec = textdrift.vectorize(["Espresso, Grinder! Roasters?"])
    assert set(vec) == {"espresso", "grinder", "roasters"}
    assert all(token == token.lower() for token in vec)


def test_vectorize_drops_short_tokens_and_stopwords():
    vec = textdrift.vectorize(["up at 6am on 35mm", "the bar and the queue with them"])
    assert "6am" in vec and "35mm" in vec
    assert "bar" in vec and "queue" in vec
    for word in ("up", "at", "on", "the", "and", "with", "them"):
        assert word not in vec


def test_vectorize_is_deterministic():
    text = "flash portraits in bar light, 35mm, 1am sidewalks"
    assert textdrift.vectorize([text]) == textdrift.vectorize([text])


def test_vectorize_weights_repeats_sublinearly():
    vec = textdrift.vectorize(["market " * 10 + "market"])
    # 11 occurrences, and 11 is not the weight.
    assert vec["market"] == 1.0 + math.log(11)
    assert vec["market"] < 11


# ---------------------------------------------------------------------------
# 2. cosine — the exact edges, and the case that used to divide by zero
# ---------------------------------------------------------------------------


def test_cosine_identical_corpora_is_exactly_one():
    vec = textdrift.vectorize(["grind finer, dial it in"])
    assert textdrift.cosine(vec, vec) == 1.0


def test_cosine_disjoint_corpora_is_zero():
    a = textdrift.vectorize(["espresso grinder roaster"])
    b = textdrift.vectorize(["barbell squat progression"])
    assert textdrift.cosine(a, b) == 0.0


def test_cosine_empty_and_zero_vectors_are_zero():
    vec = textdrift.vectorize(["patio queue downtown"])
    assert textdrift.cosine({}, vec) == 0.0
    assert textdrift.cosine(vec, {}) == 0.0
    assert textdrift.cosine({}, {}) == 0.0
    # zero-magnitude vectors divide by zero unless the guard is there
    assert textdrift.cosine({"alpha": 0.0, "beta": 0.0}, {"gamma": 0.0}) == 0.0


def test_cosine_is_symmetric_and_bounded():
    a = textdrift.vectorize(["lamp on, phone face down"])
    b = textdrift.vectorize(["lamp on, desk is the plan"])
    forward, backward = textdrift.cosine(a, b), textdrift.cosine(b, a)
    assert forward == backward
    assert 0.0 <= forward <= 1.0


# ---------------------------------------------------------------------------
# 3. profile — a centroid that is actually normalised
# ---------------------------------------------------------------------------


def test_profile_is_unit_norm():
    prof = textdrift.profile(corpus("bar path and the 6am gym", "one more set"))
    assert abs(math.sqrt(sum(w * w for w in prof.values())) - 1.0) < 1e-9


def test_profile_of_nothing_is_empty():
    assert textdrift.profile([]) == {}
    assert textdrift.profile(["at the", "on it"]) == {}


# ---------------------------------------------------------------------------
# 4. pairs — ordering and the threshold
# ---------------------------------------------------------------------------


def _three_profiles() -> dict[str, dict[str, float]]:
    return {
        "close.a": textdrift.vectorize(["one drink three hours on the patio"]),
        "close.b": textdrift.vectorize(["one drink, three hours, on the patio"]),
        "far.c": textdrift.vectorize(["squat rack barbell progress"]),
    }


def test_pairs_are_sorted_descending_and_respect_the_threshold():
    profiles = _three_profiles()
    loose = textdrift.pairs(profiles, threshold=0.0)
    sims = [sim for _, _, sim in loose]
    assert sims == sorted(sims, reverse=True)
    assert len(loose) == 3  # including the disjoint pair, at 0.0

    tight = textdrift.pairs(profiles, threshold=0.9)
    assert len(tight) < len(loose)
    assert all(sim >= 0.9 for _, _, sim in tight)
    assert {pair for pair in (tuple(r[:2]) for r in tight)} <= {("close.a", "close.b")}


# ---------------------------------------------------------------------------
# 5. audit — scoping, the skip, and the shape of the report
# ---------------------------------------------------------------------------


def test_audit_flags_near_copy_siblings():
    # Near-copy, not identical: the second child adds one word, so the pair
    # goes through the real cosine instead of the equality shortcut.
    history = {
        "wren.mp4": corpus("flash on, one more frame at 1am"),
        "harperbuilds": corpus("flash on, one more frame at 1am tonight"),
    }
    cells = {"wren.mp4": "LAA-01", "harperbuilds": "LAA-01"}
    report = textdrift.audit(history, cells=cells)
    assert report["ok"] is False
    assert report["worst"], "a near-copy pair must be reported"
    top = report["worst"][0]
    assert {top["a"], top["b"]} == {"wren.mp4", "harperbuilds"}
    assert THRESHOLD < top["similarity"] < 1.0
    assert "diverge" in report["note"]


def test_audit_passes_siblings_with_distinct_beats():
    history = {
        "harperbuilds": corpus(
            "specialty coffee grinders roasters espresso", "dial the grinder finer"
        ),
        "mila.lifts": corpus(
            "lifting progression barbell path", "gyms eating enough actually grow"
        ),
    }
    cells = {"harperbuilds": "ATX-01", "mila.lifts": "ATX-01"}
    report = textdrift.audit(history, cells=cells)
    assert report["ok"] is True
    assert report["worst"] == []
    assert "diverge" not in report["note"]
    # and the margin is not a hair under the knob
    closeness = float(report["note"].rsplit(" at ", 1)[1].split(".")[0])
    assert closeness < THRESHOLD / 2


def test_audit_never_reports_cross_cell_similarity():
    history = {
        "desk.and.dusk": corpus("lamp on, page one at four"),
        "lowlit.austin": corpus("lamp on, page one at four"),
    }
    cells = {"desk.and.dusk": "SEA-01", "lowlit.austin": "ATX-01"}
    report = textdrift.audit(history, cells=cells)
    assert report["ok"] is True
    assert report["worst"] == []
    assert report["n"] == 0


def test_audit_skips_child_under_three_posts_and_says_so():
    history = {
        "harperbuilds": corpus("grinders roasters espresso dial finer"),
        "mila.lifts": corpus("barbell progression squat rack eating"),
        "wren.mp4": ["one frame", "closing time"],  # two posts only
    }
    cells = {h: "ATX-01" for h in history}
    report = textdrift.audit(history, cells=cells)
    assert "wren.mp4" in report["note"]
    assert "Skipped" in report["note"]
    assert report["n"] == 2


def test_audit_reports_shape_and_honours_the_window():
    history = {h: corpus(f"{h} distinctive vocab word") for h in ("a.one", "b.two")}
    cells = {"a.one": "ATX-01", "b.two": "ATX-01"}
    report = textdrift.audit(history, cells=cells, window=5)
    assert set(report) == {"ok", "worst", "n", "window", "note"}
    assert report["window"] == 5
    assert isinstance(report["note"], str) and report["note"]


def test_audit_takes_the_cell_off_the_persona_row():
    """No ``cells`` argument: the cell comes from the Persona object."""
    history = {
        "wren.mp4": corpus("flash on, one more frame at 1am"),
        "harperbuilds": corpus("flash on, one more frame at 1am"),
    }
    personas = {
        "wren.mp4": type("P", (), {"cell": "LAA-01"})(),
        "harperbuilds": type("P", (), {"cell": "LAA-01"})(),
    }
    report = textdrift.audit(history, personas=personas)
    assert report["ok"] is False
    assert report["n"] == 2


# ---------------------------------------------------------------------------
# 6. the real rows, and the brief that gets written into the next prompt
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def personas() -> dict:
    return config.load_personas()


def _history_for(persona, n: int = 20) -> list[str]:
    """Synthetic posts from a real row's own beat, phrases, opinions."""
    seeds = [persona.beat] + list(persona.pet_phrases) + list(persona.opinions)
    return [seeds[i % len(seeds)] for i in range(n)]


def test_audit_runs_over_the_five_real_personas(personas):
    """Real rows, synthetic histories. In production every child has its own
    cell, so nothing is comparable; forced into one cell, the report is real."""
    assert len(personas) == 5
    assert len({p.cell for p in personas.values()}) == 5
    history = {handle: _history_for(p) for handle, p in personas.items()}

    alone = textdrift.audit(history, personas=personas)
    assert alone["n"] == 0  # one child per cell: no siblings to compare
    assert alone["ok"] is True
    assert alone["worst"] == []

    shared = textdrift.audit(history, cells={handle: "ATX-01" for handle in personas})
    assert set(shared) == {"ok", "worst", "n", "window", "note"}
    assert shared["n"] == 5
    assert shared["window"] == 20
    assert shared["ok"] is (not shared["worst"])
    assert isinstance(shared["note"], str) and shared["note"]
    sims = [row["similarity"] for row in shared["worst"]]
    assert sims == sorted(sims, reverse=True)
    for row in shared["worst"]:
        assert set(row) >= {"a", "b", "similarity"}
        assert row["a"] in personas and row["b"] in personas
        assert row["a"] < row["b"]


def test_diverge_brief_names_both_handles_and_their_levers(personas):
    a, b = "harperbuilds", "wren.mp4"
    brief = textdrift.diverge_brief(a, b, personas[a], personas[b])
    assert a in brief and b in brief
    assert personas[a].pet_phrases[0] in brief
    assert personas[b].pet_phrases[0] in brief
    assert personas[a].casing in brief


def test_diverge_brief_is_plain_text_without_optional_personas():
    brief = textdrift.diverge_brief("a.one", "b.two")
    assert "a.one" in brief and "b.two" in brief
    for marker in ("|", "**", "#", "- "):
        assert marker not in brief
