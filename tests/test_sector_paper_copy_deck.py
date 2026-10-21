# Sector Paper completion boards — bilingual copy deck contract.
#
# The deck (design_refs/sector-paper-20261021/copy_deck.json) is what the Paper
# writer places on the boards. It must reuse the product's shipped EN/ZH strings:
# every non-NEW entry cites a file:line that really carries a fragment of the
# string, so the boards cannot drift from the shipped templates.
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

ROLES = {
    "h1",
    "subtitle",
    "h2",
    "label",
    "body",
    "cta",
    "link",
    "footnote",
    "asof",
    "chip",
    "state_title",
    "state_body",
    "state_action",
    "aria",
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


def fragments(entry):
    """Pieces of the EN or ZH string that should appear near the cited line."""
    cands = [t for t in en_words(entry["en"]) if len(t) >= 3]
    cands += re.findall(r"[一-鿿]{2,}", entry["zh"])
    en_n = norm(entry["en"])
    if len(en_n) <= 6 and en_n:
        cands.append(en_n)
    return cands


def source_window(source):
    m = re.match(r"^(.+):(\d+)$", source)
    if not m:
        return None
    path = REPO / m.group(1)
    if not path.is_file():
        return None
    line_no = int(m.group(2))
    lines = path.read_text(encoding="utf-8").splitlines()
    lo = max(0, line_no - 4)
    hi = min(len(lines), line_no + 3)
    return norm(" ".join(lines[lo:hi]))


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
    deck = load_deck()
    missing = []
    for board, key, entry in entries(deck):
        src = entry["source"]
        if src == "NEW":
            continue
        window = source_window(src)
        if window is None:
            missing.append((board, key, src, "unresolvable source"))
            continue
        cands = fragments(entry)
        if not cands:
            missing.append((board, key, src, "no fragments"))
            continue
        if not any(c in window for c in cands):
            missing.append((board, key, src, "fragment not found"))
    assert not missing, missing


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
