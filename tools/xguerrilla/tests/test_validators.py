"""Validator and explicit synthetic persona-schema regression cases.

The actual persona/link parsers consume temporary inputs. These assertions
qualify model/schema behavior, not the deployed persona roster or live pool."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.xguerrilla import config                       # noqa: E402
from tools.xguerrilla.persona import Persona              # noqa: E402
from tools.xguerrilla.validators import Draft, enforce_voice, validate  # noqa: E402

MILA = "mila.lifts"
WREN = "wren.mp4"
MILA_SLOT = "https://links.example.com/xg/mila-lifts"

BASE = "legs day again, 5x5 squats and one more set, no drama. knees felt fine."

# Clean drafts, one per persona: short, specific, no tells.
CLEAN = {
    MILA: BASE,
    WREN: "flash on, one more frame. the bar light did most of the work.",
    "harperbuilds": "dial it in on the new bag, then pull it a touch coarser. "
                    "the scale finally arrived and i am eating humble pie.",
    "lowlit.austin": "on the patio again, one drink that turned into three. "
                     "the line was gone by midnight.",
    "desk.and.dusk": "lamp on, phone face down. page one at four and the room finally quiet.",
}


@pytest.fixture(scope="module")
def personas(synthetic_xg_config):
    return config.load_personas(str(synthetic_xg_config.personas),
                                str(synthetic_xg_config.links))


def clean_draft(text: str = BASE, kind: str = "post", **kw) -> Draft:
    if kind in ("reply", "quote"):
        kw.setdefault("read_trace_id", "trace-8842")
    return Draft(text=text, kind=kind, **kw)


# (label, persona, draft kwargs, history, links_used_7d, expected substring)
CASES = [
    ("empty text", MILA, dict(text=""), [], 0, "text is empty"),
    ("whitespace only", MILA, dict(text="   "), [], 0, "text is empty"),
    ("over length", MILA, dict(text=BASE * 3), [], 0, "over length"),
    ("dangling conjunction", MILA,
     dict(text="legs day again, squats and a flat white and"), [], 0, "dangling conjunction"),
    ("double space", MILA, dict(text="legs day again,  squats and a flat white."), [], 0,
     "double space"),
    ("trailing space", MILA, dict(text=BASE + " "), [], 0, "trailing space"),
    ("too many hashtags", MILA,
     dict(text="legs day #gym #coffee, squats and a flat white.",
          hashtags=["#gym", "#coffee"]), [], 0, "too many hashtags"),
    ("declared hashtag absent", MILA,
     dict(text="legs day again, squats and a flat white.", hashtags=["#gym"]), [], 0,
     "listed but not in the text"),
    ("two links", MILA,
     dict(text="program is up, link in the usual place.", links=[MILA_SLOT, MILA_SLOT + "2"]),
     [], 0, "more than one link"),
    ("weekly link budget", MILA,
     dict(text="program is up, link in the usual place.", links=[MILA_SLOT]), [], 3,
     "link budget"),
    ("foreign link slot", MILA,
     dict(text="program is up, link in the usual place.",
          links=["https://somewhere-else.example/x"]), [], 0, "own link slot"),
    ("relative link", MILA,
     dict(text="program is up, link in the usual place.", links=["links.example.com/x"]),
     [], 0, "absolute http(s)"),
    ("reply without read trace", MILA,
     dict(text="that is the honest version of the 5x5 story.", kind="reply",
          read_trace_id=None), [], 0, "read_trace_id"),
    ("quote without read trace", MILA,
     dict(text="the part nobody posts about is the wait.", kind="quote",
          read_trace_id=None), [], 0,
     "read_trace_id"),
    ("reply opens with Agreed", MILA,
     dict(text="Agreed, the 5am thing is real.", kind="reply"), [], 0, "bare 'agreed'"),
    ("quote opens with This", MILA,
     dict(text="This is the whole argument, honestly.", kind="quote"), [], 0, "bare 'this'"),
    ("near duplicate", MILA, dict(text=BASE), [BASE], 0, "near-duplicate"),
    ("near duplicate, lightly edited", MILA, dict(text=BASE), [BASE.replace("fine", "good")],
     0, "near-duplicate"),
    ("LLM-ism delve", MILA, dict(text="let us delve into legs day for a second."), [], 0,
     "LLM-ism"),
    ("LLM-ism inflection", MILA,
     dict(text="unlocking the next level on squats this week."), [], 0, "LLM-ism"),
    ("LLM-ism hyphen drift", MILA,
     dict(text="a game-changer for my squat depth, genuinely."), [], 0, "LLM-ism"),
    ("not just but", MILA,
     dict(text="not just a leg day but a whole argument about legs."), [], 0,
     "not-just-but"),
    ("two em dashes", MILA,
     dict(text="legs day — squats — and a flat white after."), [], 0, "em dashes"),
    ("no lowercase word", WREN,
     dict(text="FLASH ON, LOW LIGHT, ONE MORE FRAME"), [], 0, "no lowercase word"),
    ("two exclamation marks", MILA,
     dict(text="legs day again!! knees felt fine."), [], 0, "exclamation marks"),
    ("four sentence post", MILA,
     dict(text="legs day. squats again. knees fine. flat white after."), [], 0,
     "sentences in a post"),
    ("unknown kind", MILA, dict(text=BASE, kind="thread"), [], 0, "unknown draft kind"),
]


@pytest.mark.parametrize(
    "label,handle,kwargs,history,spent,expected",
    CASES,
    ids=[c[0] for c in CASES],
)
def test_each_rule_fires(label, handle, kwargs, history, spent, expected, personas):
    draft = Draft(**{"kind": "post", "text": "", **kwargs})
    if draft.kind in ("reply", "quote") and "read_trace_id" not in kwargs:
        draft = clean_draft(kwargs["text"], draft.kind)
    problems = validate(draft, personas[handle], history=history, links_used_7d=spent)
    assert any(expected in p for p in problems), f"{label}: expected {expected!r} in {problems}"
    assert problems, f"{label}: no violations reported"


def test_clean_draft_passes(personas):
    assert validate(clean_draft(), personas[MILA]) == []


def test_single_em_dash_and_three_sentences_are_legal(personas):
    text = "legs day again. squats felt heavy — in a good way. flat white after."
    assert validate(clean_draft(text), personas[MILA]) == []


def test_clean_reply_and_quote_pass_with_trace(personas):
    assert validate(clean_draft("the 5am thing is real, no notes.", "reply"), personas[MILA]) == []
    assert validate(clean_draft("the part nobody posts about is the wait.", "quote"),
                    personas[MILA]) == []


def test_link_to_own_slot_passes(personas):
    draft = clean_draft("program is up, link in the usual place.", links=[MILA_SLOT])
    assert validate(draft, personas[MILA], links_used_7d=2) == []


def test_budget_exact_at_cap_is_legal(personas):
    draft = clean_draft(links=[MILA_SLOT])
    assert validate(draft, personas[MILA], links_used_7d=2)[:] == []


def test_now_must_be_a_datetime(personas):
    with pytest.raises(TypeError):
        validate(clean_draft(), personas[MILA], now="2026-11-07")


# --- voice, across drafts ---------------------------------------------------

def test_voice_clean_window(personas):
    window = [
        "grind finer than you think, then dial it back.",
        "the scale arrived before the machine.",
        "one bag, two weeks, still sour.",
        "tastes like the bag smells, which is the point.",
    ]
    assert enforce_voice(window, personas["harperbuilds"]) == []


def test_voice_flat_window(personas):
    window = [f"day {i}, the kettle took its time." for i in range(20)]
    problems = enforce_voice(window, personas["harperbuilds"])
    assert any("voice flat" in p for p in problems), problems


def test_voice_repeated_opening_word(personas):
    window = [
        "coffee at six, grind finer.",
        "coffee again at six, still sour.",
        "the grinder needs a clean.",
    ]
    problems = enforce_voice(window, personas["harperbuilds"])
    assert any("both open with 'coffee'" in p for p in problems), problems


def test_voice_accepts_one_draft(personas):
    assert enforce_voice(clean_draft(), personas[MILA]) == []


def test_voice_window_is_capped_at_twenty(personas):
    # A pet phrase from twenty-one drafts ago must not rescue the window.
    window = ["tastes like the bag smells."] + [f"day {i}, kettle again." for i in range(20)]
    problems = enforce_voice(window, personas["harperbuilds"])
    assert any("voice flat" in p for p in problems), problems


# --- the persona set --------------------------------------------------------

HANDLES = {"wren.mp4", "harperbuilds", "lowlit.austin", "mila.lifts", "desk.and.dusk"}
ROLES = {
    "wren.mp4": "lead",
    "harperbuilds": "conversation",
    "lowlit.austin": "conversation",
    "mila.lifts": "lead",
    "desk.and.dusk": "broadcast",
}


def test_five_synthetic_personas_load(personas):
    assert set(personas) == HANDLES
    assert len(personas) == 5


def test_persona_rows_are_valid(personas):
    for handle, persona in personas.items():
        assert persona.validate() == [], handle
        assert persona.role == ROLES[handle]
        assert handle == persona.handle


def test_persona_rows_are_distinct(personas):
    rows = list(personas.values())
    for field_name in ("beat", "city", "max_chars", "hours", "seed"):
        values = [getattr(p, field_name) for p in rows]
        assert len({tuple(v) if isinstance(v, list) else v for v in values}) == len(rows), field_name
    assert len({p.casing for p in rows}) >= 3
    assert len({p.speed_class for p in rows}) >= 2


def test_persona_voice_material(personas):
    for handle, persona in personas.items():
        assert len(persona.pet_phrases) == 3, handle
        assert len(persona.opinions) == 3, handle
        assert len(persona.doesnt_care_about) == 2, handle
        assert all(isinstance(x, str) and x.strip() for x in persona.pet_phrases), handle


def test_each_persona_has_a_link_slot(personas):
    for handle in HANDLES:
        assert getattr(personas[handle], "link_slot", "").endswith(handle.replace(".", "-"))


def test_every_persona_passes_a_clean_draft(personas):
    for handle, text in CLEAN.items():
        problems = validate(clean_draft(text), personas[handle])
        assert problems == [], f"{handle}: {problems}"


def test_synthetic_persona_set_seats_on_the_pool(personas, net_slots):
    assert config.check_capacity(personas, slots=net_slots) == []


def test_capacity_refuses_more_children_than_slots(net_slots):
    crowd = {f"child{i}": Persona(handle=f"child{i}", cell=f"cell{i}") for i in range(17)}
    problems = config.check_capacity(crowd, slots=net_slots)
    assert problems and "slots are exclusive" in problems[0]


def test_capacity_uses_given_slots(personas, net_slots):
    assert config.check_capacity(personas, slots=net_slots[:5]) == []


def test_paths_resolve_under_the_package():
    assert config.personas_dir() == str(Path(config.__file__).parent / "personas")
    assert config.links_path().endswith("links.yml")
    assert Path(config.personas_dir()).is_dir()
