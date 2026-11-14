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
from tools.xguerrilla import tlds                         # noqa: E402
from tools.xguerrilla.persona import Persona              # noqa: E402
from tools.xguerrilla.validators import (                 # noqa: E402
    BIO_PATH_RE,
    Draft,
    canonical_bio_link,
    enforce_voice,
    links_in_text,
    validate,
    validate_bio,
)
import yaml                                               # noqa: E402

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
    ("declared link", MILA,
     dict(text="program is up, link in the usual place.", links=[MILA_SLOT]),
     [], 0, "declares link"),
    ("two declared links", MILA,
     dict(text="program is up, link in the usual place.", links=[MILA_SLOT, MILA_SLOT + "2"]),
     [], 0, "declares link"),
    ("a spent budget cannot legalise a link", MILA,
     dict(text="program is up, link in the usual place.", links=[MILA_SLOT]), [], 3,
     "declares link"),
    ("foreign link slot", MILA,
     dict(text="program is up, link in the usual place.",
          links=["https://somewhere-else.example/x"]), [], 0, "declares link"),
    ("url typed into post text", MILA,
     dict(text="full write-up at https://www.mastermind-x.com/x/ab12cd34."), [], 0,
     "URL in post text"),
    ("bare host typed into post text", MILA,
     dict(text="mastermind-x.com/x/ab12cd34 has the write-up."), [], 0,
     "URL in post text"),
    ("shortener typed into reply text", MILA,
     dict(text="cheers, details at t.co/AbCd12.", kind="reply"), [], 0,
     "URL in reply text"),
    ("url typed into quote text", MILA,
     dict(text="www.mastermind-x.com/x/ab12cd34 is the whole argument.", kind="quote"),
     [], 0, "URL in quote text"),
    ("declared link in a reply", MILA,
     dict(text="the 5am thing is real, no notes.", kind="reply",
          links=[MILA_SLOT], read_trace_id="trace-8842"),
     [], 0, "declares link"),
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


def test_own_link_slot_is_refused_and_the_budget_cannot_buy_it_back(personas):
    """The one-link-per-week allowance is gone (§26.4 as amended by BL-9).

    The persona row's ``links_per_week`` is now a historical field the gate
    never reads: a link is refused at zero spend and refused again after a week
    of imaginary link posts, because the policy has no per-account exception and
    no budget left to spend.
    """
    draft = clean_draft("program is up, link in the usual place.", links=[MILA_SLOT])
    for spent in (0, 2, 3):
        problems = validate(draft, personas[MILA], links_used_7d=spent)
        assert any("declares link" in p for p in problems), (spent, problems)


@pytest.mark.parametrize("kind", ["post", "reply", "quote"])
def test_no_draft_kind_may_carry_a_url_in_its_text(kind, personas):
    text = "the write-up is at https://www.mastermind-x.com/x/ab12cd34 and that is it."
    problems = validate(clean_draft(text, kind), personas[MILA])
    assert any(f"URL in {kind} text" in p for p in problems), problems


def test_the_clean_fixtures_carry_no_url_token(personas):
    for handle, text in CLEAN.items():
        assert links_in_text(text) == [], (handle, links_in_text(text))
        assert validate(clean_draft(text), personas[handle]) == [], handle


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


# --- the bio: the only URL surface in the network (bio policy v1) -----------

BIO_TEXT = "An editorial account of Mastermind-X. Markets, told plainly."
CHILD = "ab12cd34"


def _bio(child_id: str = CHILD) -> str:
    return f"{BIO_TEXT} {canonical_bio_link(child_id)}"


def test_the_canonical_bio_passes():
    assert validate_bio(_bio(), child_id=CHILD, known_ids={CHILD}) == []


def test_canonical_bio_link_is_the_settled_shape():
    assert canonical_bio_link(CHILD) == "https://www.mastermind-x.com/x/ab12cd34"


def test_a_bio_link_may_carry_sentence_punctuation():
    # The link ends the sentence: the period is the writer's, not the URL's.
    assert validate_bio(_bio() + ".") == []
    assert links_in_text(_bio() + ".") == [canonical_bio_link(CHILD)]


BIO_REJECTIONS = [
    ("apex host", f"{BIO_TEXT} https://mastermind-x.com/x/ab12cd34", "apex"),
    ("shortener t.co", f"{BIO_TEXT} https://t.co/ab12cd34", "shortener"),
    ("shortener bit.ly", f"{BIO_TEXT} https://bit.ly/ab12cd34", "shortener"),
    ("query string", _bio() + "?utm_source=x", "query string"),
    ("fragment", _bio() + "#top", "fragment"),
    ("trailing slash", _bio() + "/", "trailing slash"),
    ("uppercase path", f"{BIO_TEXT} https://www.mastermind-x.com/x/AB12CD34", "uppercase"),
    ("http scheme", f"{BIO_TEXT} http://www.mastermind-x.com/x/ab12cd34", "https"),
    ("no scheme", f"{BIO_TEXT} www.mastermind-x.com/x/ab12cd34", "https"),
    ("two links", _bio() + " https://www.mastermind-x.com/x/deadbeef",
     "URLs in the bio"),
    ("foreign host", f"{BIO_TEXT} https://example.com/x/ab12cd34",
     "is not 'www.mastermind-x.com'"),
    ("userinfo posing as our host",
     f"{BIO_TEXT} https://www.mastermind-x.com@evil.example/x/ab12cd34",
     "is not 'www.mastermind-x.com'"),
    ("child id too short", f"{BIO_TEXT} https://www.mastermind-x.com/x/ab1",
     "destination shape"),
    ("child id too long",
     f"{BIO_TEXT} https://www.mastermind-x.com/x/{'a' * 33}", "destination shape"),
    ("wrong path family",
     f"{BIO_TEXT} https://www.mastermind-x.com/research/demo-report.html",
     "destination shape"),
    ("no link at all", BIO_TEXT, "carries no URL"),
]


@pytest.mark.parametrize("label,text,expected", BIO_REJECTIONS,
                         ids=[c[0] for c in BIO_REJECTIONS])
def test_bio_rejections(label, text, expected):
    problems = validate_bio(text)
    assert any(expected in p for p in problems), f"{label}: {problems}"


def test_the_bio_must_name_this_childs_id():
    problems = validate_bio(_bio("deadbeef"), child_id=CHILD)
    assert any("not this child's attribution key" in p for p in problems), problems


def test_an_invalid_child_id_cannot_bind_to_a_path():
    problems = validate_bio(_bio("AB12CD34".lower()), child_id="Not-An-Id")
    assert any("is not a valid attribution key" in p for p in problems), problems


def test_an_unregistered_child_id_is_refused():
    problems = validate_bio(_bio("deadbeef"), known_ids={CHILD})
    assert any("not in the registry" in p for p in problems), problems


def test_a_registered_child_id_passes():
    assert validate_bio(_bio("deadbeef"), known_ids={CHILD, "deadbeef"}) == []


def test_a_dotted_registry_id_passes_the_full_bio_contract():
    # Real child ids are dotted: the settled shape must admit interior dots
    # or it refuses the correct bio for 4 of the 5 registered children
    # (desk.and.dusk, lowlit.austin, mila.lifts, wren.mp4).
    assert validate_bio(
        _bio("mila.lifts"),
        child_id="mila.lifts",
        known_ids={"mila.lifts", "wren.mp4", "desk.and.dusk"},
    ) == []


def test_every_registered_persona_handle_passes_the_bio_shape():
    # The validator and the registry must not disagree: each persona file's
    # handle IS a valid attribution key (BL-2), so the registry itself is the
    # witness that the shape accepts the ids the network actually provisions.
    handles = {
        row["handle"]
        for row in (
            yaml.safe_load(p.read_text())
            for p in Path(config.personas_dir()).glob("*.yml")
        )
        if isinstance(row, dict) and row.get("handle")
    }
    assert len(handles) >= 5, handles
    for handle in handles:
        assert BIO_PATH_RE.fullmatch(f"/x/{handle}"), handle
        assert validate_bio(_bio(handle), known_ids=handles) == [], handle


def test_the_dot_admitting_shape_still_refuses_degenerate_forms():
    for bad in ("a..b", ".lead", "ab1", "a" * 33,
                ".".join(["a"] * 17), ".".join(["a"] * 32)):
        problems = validate_bio(_bio(bad))
        assert any("destination shape" in p for p in problems), (bad, problems)


@pytest.mark.parametrize("child", ["a.bc", "ab.c", "a." + "b" * 29, "a." + "b" * 30])
def test_bio_id_length_counts_interior_dots(child):
    assert BIO_PATH_RE.fullmatch(f"/x/{child}")
    assert validate_bio(_bio(child), child_id=child, known_ids={child}) == []


@pytest.mark.parametrize("child", ["a..b", "trail.", "a." + "b" * 31, ".".join(["a"] * 32)])
def test_invalid_dotted_child_id_cannot_bind_even_to_a_valid_link(child):
    problems = validate_bio(_bio(), child_id=child)
    assert any("not a valid attribution key" in p for p in problems), problems


def test_a_url_in_the_display_name_is_refused():
    problems = validate_bio(_bio(), display_name=f"mila {canonical_bio_link(CHILD)}")
    assert any("display name carries a URL" in p for p in problems), problems


def test_links_in_text_sees_every_spelling_that_resolves():
    assert links_in_text("see https://t.co/abc now") == ["https://t.co/abc"]
    assert links_in_text("see www.mastermind-x.com/x/ab12cd34 now") == [
        "www.mastermind-x.com/x/ab12cd34"]
    # A bare host is a link on X even with no scheme in front of it.
    assert links_in_text("see mastermind-x.com/x/ab12cd34") == [
        "mastermind-x.com/x/ab12cd34"]
    # A number is not a host: version strings must survive the matcher.
    assert links_in_text("shipped 2.0.1 today") == []


# --- the general scheme-less host: TLD membership, not label shape ----------
#
# The last _LINK_TOKEN alternative used to fire on any dotted word with an
# alphabetic 2+ label tail, so filename-shaped prose was refused by the
# absolute zero-URL gate (BL-9) as though it carried a link. The trailing
# label must now be a member of the versioned TLD set (tlds.py/tlds.txt)
# for the match to count. One fire row and one non-fire row per class.

#: Not links: the post gate must let every one of these through.
LINK_PROSE = [
    "Node.js 22 ships today",
    "the checklist lives in notes.txt now",
    "setup.exe is what the vendor shipped",
    "cf. e.g. the earlier run",
    "we shipped 2.0.1 and v1.2 both",
    "ping me at a.b@corp.com any time",
]

#: Links: the post gate must refuse every one of these (fire direction
#: unchanged — scheme-less outside-domain hosts stay refused).
LINK_HOSTS = [
    "the write-up is at x.com/handle now",
    "she is twitter.com/somebody these days",
    "the mirror is evil.example/path today",
    # Collision decision (tlds.txt): zip/mov/app are REGISTERED TLDs, so a
    # dotted word ending on one fires, fail-closed, exactly like any host.
    "grab it from archive.zip today",
    "the clip is at movie.mov now",
]


@pytest.mark.parametrize("text", LINK_PROSE)
def test_filename_shaped_prose_is_not_a_link(text, personas):
    assert links_in_text(text) == [], text
    assert validate(clean_draft(text), personas[MILA]) == [], text


@pytest.mark.parametrize("text", LINK_HOSTS)
def test_a_scheme_less_host_with_a_real_tld_still_refuses(text, personas):
    tokens = links_in_text(text)
    assert tokens, text
    problems = validate(clean_draft(text), personas[MILA])
    assert any("URL in post text" in p for p in problems), (text, problems)


def test_the_canonical_bio_link_is_still_the_one_token_a_bio_may_carry():
    # Non-fire row for the bio surface: the canonical destination is still
    # tokenized (validate_bio depends on links_in_text seeing exactly it).
    assert links_in_text(_bio()) == [canonical_bio_link(CHILD)]
    assert validate_bio(_bio(), child_id=CHILD, known_ids={CHILD}) == []


# Rejecting a filename-shaped candidate must leave later explicit URLs visible
# to every consumer of the shared scanner, including the profile-only gates.
@pytest.mark.parametrize("prefix", [
    "Node.js", "notes.txt", "setup.exe", "page.html", "payload.json",
])
@pytest.mark.parametrize("url", [
    "https://evil.example/path", "http://evil.example/path", "www.evil.example/path",
])
@pytest.mark.parametrize("wrapper", [
    "{prefix}/{url}", "{prefix}/({url})", "{prefix}/[{url}]", "{prefix}/nested/{url}",
])
@pytest.mark.parametrize("surface", ["post", "reply", "quote", "bio", "display_name"])
def test_rejected_filename_cannot_hide_an_explicit_url(prefix, url, wrapper, surface, personas):
    text = wrapper.format(prefix=prefix, url=url) + " today"
    assert links_in_text(text) == [url]
    if surface in ("post", "reply", "quote"):
        problems = validate(clean_draft(text, surface), personas[MILA])
        assert any(f"URL in {surface} text" in p for p in problems), problems
    elif surface == "bio":
        problems = validate_bio(f"{_bio()} {text}", child_id=CHILD, known_ids={CHILD})
        assert any("2 URLs in the bio" in p for p in problems), problems
    else:
        problems = validate_bio(_bio(), child_id=CHILD, display_name=text)
        assert any("display name carries a URL" in p for p in problems), problems


@pytest.mark.parametrize("text, expected", [
    ("notes.txt.http://evil.example/path", "http://evil.example/path"),
    ("notes.txt.https://evil.example/path", "https://evil.example/path"),
    ("notes.txt.www.evil.notarealtld/path", "www.evil.notarealtld/path"),
    ("notes.txt/(evil.example/a/b?x=1)", "evil.example/a/b?x=1"),
    ("notes.txt/[x.com/handle]", "x.com/handle"),
    ("notes.txt/(twitter.com/somebody)", "twitter.com/somebody"),
    ("notes.txt/(t.co/AbCd12)", "t.co/AbCd12"),
    ("notes.txt/(mastermind-x.com/x/ab12cd34)", "mastermind-x.com/x/ab12cd34"),
])
def test_rejected_filename_resumes_with_original_token_context(text, expected):
    assert links_in_text(text) == [expected]


def test_rejected_filename_preserves_link_paths_order_and_deduplication():
    assert links_in_text(
        "notes.txt/https://evil.example/a/b?x=1 then x.com/handle "
        "and https://evil.example/a/b?x=1"
    ) == ["https://evil.example/a/b?x=1", "x.com/handle"]


def test_nested_filename_path_does_not_consume_the_final_explicit_url():
    text = "/".join(["notes.txt"] * 2000 + ["https://evil.example/path"])
    assert links_in_text(text) == ["https://evil.example/path"]


@pytest.mark.parametrize("text", [
    "notes.txt/subdir/file.json", "notes.txt/evil.example/path", "notes.txt/a.b@corp.com",
])
def test_rejected_filename_preserves_existing_bare_host_boundaries(text):
    assert links_in_text(text) == []


# --- the TLD data file: versioned, sha256-pinned, consumed ------------------


def test_the_tld_set_carries_the_pinned_sentinels():
    # Real TLDs are members, file extensions are not: this is the row that
    # separates "Node.js" (pass) from "x.com" (refuse).
    assert tlds.is_tld("com") and tlds.is_tld("io") and tlds.is_tld("xn--p1ai")
    assert not tlds.is_tld("js") and not tlds.is_tld("txt")
    assert not tlds.is_tld("exe") and not tlds.is_tld("html")
    # Documented collision decision: these labels are BOTH registered TLDs
    # and file extensions; they count as TLDs so the gate stays fail-closed.
    for label in ("zip", "mov", "app", "dev", "py", "md"):
        assert tlds.is_tld(label), label
    # Reserved names IANA's registry omits (RFC 2606/6761/7686) still
    # refuse: "evil.example/path" must fire.
    for label in ("example", "invalid", "localhost", "test", "onion"):
        assert tlds.is_tld(label), label
    # Case is not semantic.
    assert tlds.is_tld("COM") and tlds.is_tld("Com") and tlds.is_tld("Example")


def test_the_tld_file_declares_its_version_and_source():
    raw = tlds._DATA_PATH.read_text(encoding="utf-8")
    assert "# source: https://data.iana.org/TLD/tlds-alpha-by-domain.txt" in raw
    assert "# iana-version: Version 2026111200" in raw
    assert tlds._PIN_RE.search(raw) is not None


def test_a_drifted_tld_file_refuses_to_load(tmp_path):
    raw = tlds._DATA_PATH.read_text(encoding="utf-8")
    # Drop one label from the IANA block: the recomputed sha256 no longer
    # matches the pin, so the loader must refuse loudly, not load quietly.
    assert raw.count("\nZIP\n") == 1
    tampered = tmp_path / "tlds-dropped-label.txt"
    tampered.write_text(raw.replace("\nZIP\n", "\n", 1), encoding="utf-8")
    with pytest.raises(RuntimeError, match="does not match"):
        tlds._load(tampered)
    # A stale pin (label added, pin left behind) must refuse the same way.
    stale = tmp_path / "tlds-stale-pin.txt"
    stale.write_text(raw.replace("\nZIP\n", "\nZIP\nZZZ\n", 1), encoding="utf-8")
    with pytest.raises(RuntimeError, match="does not match"):
        tlds._load(stale)
    # A file with no pin at all is not loadable data.
    stripped = tmp_path / "tlds-no-pin.txt"
    stripped.write_text(tlds._PIN_RE.sub("", raw), encoding="utf-8")
    with pytest.raises(RuntimeError, match="sha256"):
        tlds._load(stripped)
