"""Pin packet W9B_REC_F08: the F08 slice of LEDGER_MOVES exists as a note, and
proposes nothing the ledger's own law forbids.

One suite, one test, per seat ruling R2. It asserts the four named properties of
`research/market_intelligence_productization/W9_LEDGER_NOTE_F08_2026-09-13.md`:
the note exists; it names every row the ruling named; it never uses BUILT as a
standalone state word (BUILT_NOT_PROVEN is the only allowed form); and it carries
no Supabase project reference, personal access token or key. It also pins the
per-row shape ruling R1 requires — a quoted stale text, a merge citation, an
ancestor claim, a proposed state inside the five-word vocabulary and never
PROVEN_LIVE, and a proposed next bounded child — because a move the records stack
cannot paste is not a move.

The suite reads this repository only: the note itself. It never reads the F00C
ledger CSV and never shells to the Terminal checkout, so it cannot pass or fail on
the state of a tree this repository does not own.

RED before the packet: the note did not exist, so the first assertion failed with
`missing W9 F08 ledger note: <path>`.
"""
from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

NOTE = _ROOT / (
    "research/market_intelligence_productization/"
    "W9_LEDGER_NOTE_F08_2026-09-13.md"
)

# The four rows ruling R1 names, in the order the ruling gives them, which is the
# order LEDGER_MOVES #7-#10 carry.
ROWS = ("MO-DELTA-003", "MO-DELTA-042", "MO-PAID-027", "MO-PAID-085")

# The column's whole vocabulary. A note may propose a move inside this set; it may
# never widen the set, and this packet never proposes PROVEN_LIVE.
VOCABULARY = ("NOT_BUILT", "SPEC_ONLY", "PARTIAL", "BUILT_NOT_PROVEN", "PROVEN_LIVE")

# BUILT is not a state word in this ledger. The only allowed spelling that starts
# with it is BUILT_NOT_PROVEN, and `\bbuilt\b` cannot match inside that word
# anyway: an underscore is a word character, so there is no boundary after BUILT.
# The check is case-insensitive on purpose -- "the delivery leg is built" in prose
# is the same unsupported claim as the state word, and the honest words are
# "merged" and "shipped".
_STANDALONE_BUILT = re.compile(r"\bbuilt\b(?!_not_proven)", re.IGNORECASE)

# A Supabase project reference, a personal access token or a key. Every entry is a
# shape that appears in this estate only as a credential, or as the ref that carries
# one. A ledger note cites pull requests, merge commits and file paths instead; where
# a DDL application matters it cites the merged ledger-flip pull request and the seat
# receipt that pull request names, and the ref is never written.
_FORBIDDEN_TOKENS = (
    "sbp_",
    "service_role",
    "eyJ",
    "supabase.co",
    "postgres://",
    "postgresql://",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "ghp_",
    "github_pat_",
)

# The five labelled lines ruling R1 requires for every named row. Each one is a
# line-start label so the records stack can find it mechanically, and so a row that
# quietly drops its ancestor claim or its proposed child fails here instead of
# reaching the CSV.
_REQUIRED_LABELS = (
    r"^Stale text as it reads on macro `origin/main` \(quoted\):",
    r"^Merge citation:",
    r"^Ancestor claim:",
    r"^Proposed capability_state_c2: (\S+)\s*$",
    r"^Proposed next_bounded_child: (.+?)\s*$",
)


def _row_section(text: str, row_id: str) -> str:
    """The note's block for one row: from its LEDGER_MOVES heading to the next one."""
    pattern = re.compile(
        rf"^### LEDGER_MOVES #\d+ — {re.escape(row_id)}\b(?P<body>.*?)(?=^### |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    assert match, (
        f"the note has no `### LEDGER_MOVES #<n> — {row_id}` heading: a move the "
        "records stack cannot find by row id is not a pasteable move"
    )
    return match.group("body")


def test_the_w9_f08_ledger_note_carries_every_row_and_says_nothing_forbidden() -> None:
    assert NOTE.exists(), f"missing W9 F08 ledger note: {NOTE}"
    text = NOTE.read_text(encoding="utf-8")

    # (R2) every named row is in the note.
    for row_id in ROWS:
        assert row_id in text, f"the note does not name {row_id}"

    # (R2) no standalone BUILT; BUILT_NOT_PROVEN is allowed and is the only form.
    standalone = sorted(set(_STANDALONE_BUILT.findall(text)))
    assert not standalone, (
        "BUILT is not a state word in this ledger -- the vocabulary is "
        f"{', '.join(VOCABULARY)}, and BUILT_NOT_PROVEN is the only allowed word "
        f"that starts with it; standalone uses found: {standalone}"
    )

    # (R2) no Supabase project reference, personal access token or key.
    for token in _FORBIDDEN_TOKENS:
        assert token not in text, (
            f"the note carries {token!r}, which is a Supabase project reference, a "
            "personal access token or a key; cite the merged ledger-flip pull "
            "request and the seat receipt it names instead, and never write the ref"
        )

    # (R1) every row carries the five labelled elements, inside the vocabulary.
    for row_id in ROWS:
        section = _row_section(text, row_id)
        for label in _REQUIRED_LABELS:
            assert re.search(label, section, re.MULTILINE), (
                f"{row_id}: the move is missing the line {label!r} that ruling R1 "
                "requires"
            )
        proposed = re.search(
            r"^Proposed capability_state_c2: (\S+)\s*$", section, re.MULTILINE
        )
        assert proposed, f"{row_id}: no proposed capability_state_c2 line"
        state = proposed.group(1)
        assert state in VOCABULARY, (
            f"{row_id}: proposed state {state!r} is outside the column's vocabulary "
            f"{VOCABULARY}"
        )
        assert state != "PROVEN_LIVE", (
            f"{row_id}: PROVEN_LIVE needs a production readback of two people doing "
            "the thing the row describes; this packet holds merged code and applied "
            "DDL receipts, so it never proposes that word"
        )
        child = re.search(
            r"^Proposed next_bounded_child: (.+?)\s*$", section, re.MULTILINE
        )
        assert child and child.group(1).strip(), (
            f"{row_id}: an open row owes a next bounded child; a proposed move that "
            "leaves the column empty hands the next lane nothing to pick up"
        )
