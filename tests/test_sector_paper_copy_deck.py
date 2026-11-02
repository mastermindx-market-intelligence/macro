# Sector Paper completion boards — bilingual copy deck contract.
#
# The deck (design_refs/sector-paper-20261021/copy_deck.json) is what the Paper
# writer places on the boards. It must reuse the product's shipped EN/ZH strings:
# every non-NEW entry cites a file:line that really carries a fragment of the
# string, so the boards cannot drift from the shipped templates. SIC-V6-C04 (PRC-049): the ZH of a
# cited row must itself have a fragment in the cited window (JS unicode escapes decoded), unless the
# source declares the ZH NEW or gives the ZH its own `ZH path:line` that carries it — an EN hit alone
# never vouches for a misattributed ZH string. SIC-V7-C03 (i) (PRC-050/051): the EN half matches whole
# alphanumeric runs of the normalized window (`_present`; `norm` splits on every non-alphanumeric character, `_` and `.` included) — a Latin fragment must equal a whole run: a substring of a run (`win` in `window`,
# `stance` in `stanceHTML` / `stances`) is not a hit, a component of a snake_case or dotted identifier (`hit` in `dir_hit_rate`, `stance` in `nw.stance` / `stance_zh`) is; a CJK fragment matches as a substring.
"""Tests for the Sector Paper bilingual copy deck."""

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DECK = REPO / "design_refs" / "sector-paper-20261021" / "copy_deck.json"

BOARDS = [
    "brief",
    "explore_rotation",
    "explore_lenses",
    "dossier",
    "research",
    "watches",
    "cycles",
    "components",
    "states",
    "authority",
]

ROLES = {  # closed vocabulary; extended per RIG wave (wave 2/3 rows added the descriptive roles)
    "alt",
    "aria",
    "asof",
    "board disclaimer",
    "board footnote",
    "body",
    "caption",
    "cell sub-label",
    "chip",
    "count line",
    "cta",
    "disclosure",
    "drawer",
    "eyebrow",
    "facts",
    "footnote",
    "h1",
    "h2",
    "heading",
    "label",
    "lane title",
    "lane_sub",
    "legend",
    "link",
    "list body",
    "list title",
    "method",
    "nav",
    "note",
    "pattern",
    "placeholder",
    "qualifier",
    "row chip",
    "screen-reader text",
    "stance qualifier",
    "stat basis",
    "state",
    "state_action",
    "state_body",
    "state_title",
    "status body",
    "status title",
    "subtitle",
    "tagline",
    "text link",
    "tier gate",
}

STATE_KEYS = [
    "fresh",
    "stale",
    "incompatible_generation",
    "partial",
    "corrected",
    "abstained",
    "error",
    "empty",
    "no_access",
    "loading",
    "offline",
    "unauthorized",
    "locked",
    "invalid_payload",
    "zero",
    "empty_search",
    "uncertain_command",
]

# First word of every cta/link must be one of these shipped verbs (word budget
# law: cta/link <= 5 EN words and starts with a verb).
LINK_VERBS = {
    "see",
    "compare",
    "find",
    "check",
    "inspect",
    "review",
    "select",
    "return",
    "clear",
    "view",
    "open",
    "switch",
}

# Assembled here so this file never spells the banned word out in prose.
FORBIDDEN_WORD = "valid" + "ated"


def load_deck():
    with DECK.open(encoding="utf-8") as fh:
        return json.load(fh)


def entries(deck):
    for board, rows in deck.items():
        for key, entry in rows.items():
            yield board, key, entry


def norm(text):
    """Lowercase; join contractions; keep letters, digits and CJK; rest -> space."""
    joined = text.lower().replace("'", "").replace("’", "")
    return re.sub(r"[^0-9a-z一-鿿]+", " ", joined).strip()


def en_words(text):
    return [t for t in norm(text).split() if any(c.isalnum() for c in t)]


def zh_chars(text):
    return len([c for c in text if not c.isspace()])


_CJK = re.compile(r"[一-鿿]")


def _present(window, frag):
    """SIC-V7-C03 outcome (i): a Latin fragment counts only as a whole alphanumeric run of the normalized window.
    ``norm`` splits on every non-alphanumeric character, ``_`` and ``.`` included, so a substring of a run (``win`` in
    ``window``, ``stance`` in ``stanceHTML`` / ``stances``) is not a hit, while a component of a snake_case or dotted
    identifier (``hit`` in ``dir_hit_rate``, ``stance`` in ``nw.stance`` / ``stance_zh``) is. A CJK fragment matches as a substring, since ZH has no word boundary."""
    if _CJK.search(frag):
        return frag in window
    return re.search(r"(?<![0-9a-z])" + re.escape(frag) + r"(?![0-9a-z])", window) is not None


def fragments(entry):
    """Pieces of the EN or ZH string that should appear near the cited line."""
    cands = [t for t in en_words(entry["en"]) if len(t) >= 3]
    cands += re.findall(r"[一-鿿]{2,}", entry["zh"])
    en_n = norm(entry["en"])
    if len(en_n) <= 6 and en_n:
        cands.append(en_n)
    return cands


_CITE = re.compile(r"^(\S+?\.(?:j2|js|py|md|html|json|css|yml|yaml)):(\d+)(?:-(\d+))?(?=\s|$|[),;])")


def is_note(source):
    """A provenance note carries no string to find: NEW rows (with or without a rationale after
    the word), derived rows, and fact citations that name a data/engine state or a DOM
    observation rather than a file:line. They only have to be non-empty (well-formed test)."""
    return source.startswith(("NEW", "derived:")) or _CITE.match(source) is None


# SIC-V6-C04 (PRC-049): a source may give the ZH its own line (`; ZH path:line`) when the EN and the ZH
# sit on different lines, or declare the ZH NEW (`; ZH NEW (...)`) when the ZH was written for the deck.
_ZH_CITE = re.compile(r"(?:^|[\s;(])ZH (\S+?\.(?:j2|js|py|md|html|json|css|yml|yaml)):(\d+)(?:-(\d+))?(?=\s|$|[),;])")
_ZH_NEW = re.compile(r"(?:^|[\s;(])ZH NEW(?=\s|$|[(),;])")
_JS_ESCAPE = re.compile(r"\\u([0-9a-fA-F]{4})")


def _window(path_str, lo_no, hi_no):
    path = REPO / path_str
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    lo = max(0, lo_no - 4)
    hi = min(len(lines), hi_no + 3)
    text = " ".join(lines[lo:hi])
    # a ZH string a template writes as JS unicode escapes (sector_central.html.j2 state copy) still counts
    text = _JS_ESCAPE.sub(lambda m: chr(int(m.group(1), 16)), text)
    return norm(text)


def source_window(source):
    """Lines around a ``path:line`` or ``path:lo-hi`` citation; annotations after the citation
    (a finding id, a note in parentheses) are allowed and ignored."""
    m = _CITE.match(source)
    if not m:
        return None
    return _window(m.group(1), int(m.group(2)), int(m.group(3) or m.group(2)))


def zh_window(source):
    """The window of a ``ZH path:line`` sub-citation, or None when the source has none."""
    m = _ZH_CITE.search(source)
    if not m:
        return None
    return _window(m.group(1), int(m.group(2)), int(m.group(3) or m.group(2)))


def zh_fragments(entry):
    return re.findall(r"[一-鿿]{2,}", entry["zh"])


def row_gaps(entry):
    """Gaps of one cited (non-note) row: the any-fragment check (EN fragments as whole words of the window,
    SIC-V7-C03 (i); CJK fragments as substrings), then the SIC-V6-C04 ZH rule — the ZH
    needs a fragment in the cited window, or a ``ZH NEW`` declaration, or a ``ZH path:line`` whose own
    window carries a ZH fragment."""
    src = entry["source"]
    window = source_window(src)
    if window is None:
        return ["unresolvable source"]
    cands = fragments(entry)
    if not cands:
        return ["no fragments"]
    gaps = []
    if not any(_present(window, c) for c in cands):
        gaps.append("fragment not found")
    zh = zh_fragments(entry)
    if zh and not any(_present(window, c) for c in zh) and not _ZH_NEW.search(src):
        sub = zh_window(src)
        if sub is None:
            gaps.append("zh fragment not in the cited window; no ZH NEW declaration and no ZH path:line")
        elif not any(_present(sub, c) for c in zh):
            gaps.append("zh fragment not found at the ZH path:line")
    return gaps


def test_deck_exists_and_boards_exact():
    deck = load_deck()
    assert sorted(deck.keys()) == sorted(BOARDS)


def test_every_entry_well_formed():
    deck = load_deck()
    count = 0
    for board, key, entry in entries(deck):
        count += 1
        assert isinstance(entry, dict), (board, key)
        assert entry.get("en", "").strip(), (board, key)
        assert entry.get("zh", "").strip(), (board, key)
        assert entry.get("role") in ROLES, (board, key, entry.get("role"))
        assert entry.get("source", "").strip(), (board, key)
    assert count >= 150


def test_budgets():
    deck = load_deck()
    for board, key, entry in entries(deck):
        role = entry["role"]
        en, zh = entry["en"], entry["zh"]
        if role == "h1":
            assert len(en_words(en)) <= 4, (board, key, en)
            assert zh_chars(zh) <= 12, (board, key, zh)
        elif role == "subtitle":
            assert len(en_words(en)) <= 14, (board, key, en)
            assert zh_chars(zh) <= 28, (board, key, zh)
        elif role == "h2":
            assert len(en_words(en)) <= 7, (board, key, en)
        elif role in ("cta", "link"):
            words = en_words(en)
            assert len(words) <= 5, (board, key, en)
            assert words[0] in LINK_VERBS, (board, key, en)
        elif role == "chip":
            assert len(en_words(en)) <= 3, (board, key, en)


def test_exactly_one_h1_per_board():
    deck = load_deck()
    for board, rows in deck.items():
        h1s = [k for k, v in rows.items() if v["role"] == "h1"]
        assert len(h1s) == 1, (board, h1s)


def test_cited_sources_carry_a_fragment():
    """Every cited (non-note) deck row carries a fragment of its EN string as a whole alphanumeric run of the
    normalized cited window (SIC-V7-C03 outcome (i); ``norm`` splits on every non-alphanumeric character, ``_`` and ``.`` included, so
    a substring of a run is not a hit while a snake_case or dotted identifier component is) and clears the ZH rule of row_gaps (SIC-V6-C04)."""
    deck = load_deck()
    missing = []
    for board, key, entry in entries(deck):
        src = entry["source"]
        if is_note(src):
            continue
        for gap in row_gaps(entry):
            missing.append((board, key, src, gap))
    assert not missing, missing


def test_zh_rule_catches_a_misattributed_zh():
    """PRC-049 falsifier, restated in wave 7 (PRC-050 / SIC-V7-C01): stanceHTML opens at
    templates/sector_cycles.js:205 (:202 is the TONE_CLS anticipatory/neutral row); its
    L("Resolved stance · engine", "综合策略 · 引擎") sits at :209, outside the :202 window (:199-205). The
    :202-misattributed row clears the EN half anyway — under the wave-6 substring rule on the identifier
    substring ``stance`` (stances :199, stanceLabel / stanceHTML :204-205), and under the wave-7 whole-word
    rule (SIC-V7-C03 (i)) on the whole token ``stance`` in ``nw.stance`` at :204 — so this falsifier
    discriminates on the ZH half only: the ZH fragment is outside the window and the source carries no ZH NEW
    declaration and no ZH path:line. It passes once the ZH is sub-cited to the line that carries it or
    declared NEW; a ZH string the sub-cited line does not carry still fails. The EN-half falsifier is
    test_en_rule_rejects_identifier_substrings."""
    row = {"en": "Resolved stance · engine", "zh": "综合策略 · 引擎", "role": "label", "source": "templates/sector_cycles.js:202"}
    assert row_gaps(row) == ["zh fragment not in the cited window; no ZH NEW declaration and no ZH path:line"]
    assert row_gaps(dict(row, source="templates/sector_cycles.js:202; ZH templates/sector_cycles.js:209")) == []
    assert row_gaps(dict(row, source="templates/sector_cycles.js:202 (EN); ZH NEW (test fixture)")) == []
    assert row_gaps(dict(row, zh="不存在的字串", source="templates/sector_cycles.js:202; ZH templates/sector_cycles.js:209")) == ["zh fragment not found at the ZH path:line"]
    assert row_gaps(dict(row, source="templates/sector_cycles.js:209")) == []


def test_en_rule_rejects_identifier_substrings():
    """SIC-V7-C03 (i) falsifiers for the EN half (whole-word matching). (1) The PRC-051 shape:
    components.grader_caption cited at engine/sector_central_grader.py:332 (the frozen_df window predicate)
    has no whole-word EN hit — the wave-6 substring rule passed it on ``win`` inside ``window`` — so it fails
    the EN half; the real row, cited at :498-506 where dir_hit_rate is produced and defined, passes.
    (2) The stance shape: the stance_label row cited at templates/sector_cycles.js:200 (window :197-203)
    has ``stance`` only inside ``stances`` (:199), so the substring rule passed it and the whole-word rule
    fails it; its ZH is outside that window too, so both halves report. Each case first shows that the
    substring rule would have passed."""
    deck = load_deck()
    real = deck["components"]["grader_caption"]
    assert row_gaps(real) == []
    stale = dict(real, source="engine/sector_central_grader.py:332 dir_hit_rate (PRC-051 fixture); ZH NEW (test fixture)")
    assert any(c in source_window(stale["source"]) for c in fragments(stale))  # win inside window
    assert row_gaps(stale) == ["fragment not found"]
    row = {"en": "Resolved stance · engine", "zh": "综合策略 · 引擎", "role": "label", "source": "templates/sector_cycles.js:200"}
    assert any(c in source_window(row["source"]) for c in fragments(row))  # stance inside stances (:199)
    assert row_gaps(row) == ["fragment not found", "zh fragment not in the cited window; no ZH NEW declaration and no ZH path:line"]
    assert row_gaps(dict(row, source="templates/sector_cycles.js:200 (EN); ZH NEW (test fixture)")) == ["fragment not found"]


def test_all_seventeen_states_present():
    deck = load_deck()
    states = deck["states"]
    for state in STATE_KEYS:
        title = states.get(state + "_title")
        body = states.get(state + "_body")
        assert title and title["role"] == "state_title", state
        assert title["en"].strip() and title["zh"].strip(), state
        assert body and body["role"] == "state_body", state
        assert body["en"].strip() and body["zh"].strip(), state
        action = states.get(state + "_action")
        if action is not None:
            assert action["role"] == "state_action", state


def test_no_forbidden_word():
    deck = load_deck()
    blob = json.dumps(deck, ensure_ascii=False).lower()
    assert FORBIDDEN_WORD not in blob


def test_win_rate_only_negated():
    deck = load_deck()
    for board, key, entry in entries(deck):
        for field in ("en", "zh"):
            low = entry[field].lower()
            idx = low.find("win rate")
            while idx != -1:
                assert "not a win rate" in low, (board, key, field)
                idx = low.find("win rate", idx + 1)


def test_placeholder_braces_balanced():
    deck = load_deck()
    for board, key, entry in entries(deck):
        for field in ("en", "zh"):
            assert entry[field].count("{") == entry[field].count("}"), (board, key)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


def test_stance_rows_equal_the_engine_doctrine_vocabulary():
    """SIC-V4-C01: the deck's stance chips are the engine's DOCTRINE_STANCES, string for string,
    so the specimen and the producer can never fork the vocabulary again (SIC-ADJ-02)."""
    import sys
    sys.path.insert(0, str(REPO))
    from engine.cycle_ontology import DOCTRINE_STANCES
    comp = load_deck()["components"]
    for key, rec in DOCTRINE_STANCES.items():
        row = comp[f"stance_{key}"]
        assert (row["en"], row["zh"]) == (rec["en"], rec["zh"]), key


def test_present_pins_the_normalizer_split():
    """SIC-V8-C01 pin (PRC-053): ``norm`` splits on ``_`` and ``.``, so a snake_case component is a whole-run hit and a
    substring of a run is not — both halves pinned with literals."""
    assert _present(norm("dir_hit_rate"), "hit") is True and _present(norm("window"), "win") is False
