"""W9B_REC_F06 records guard: the F06 ledger note must stay a paste-ready proposal.

Records-only guard for ``LEDGER_MOVES`` #1-#3. It asserts the note exists at the
ruled path, names all three ledger rows, never uses a bare state word the ledger
vocabulary does not contain, proposes only vocabulary states and never
``PROVEN_LIVE``, carries every field the ruling requires per move, and records no
database project reference, personal access token or key of any kind.

It reads one markdown file and nothing else: no network, no fixtures, no ledger
CSV, no other repository's tree. It deliberately does NOT read the F00C ledger
CSV — the note quotes the stale text so a records lane can paste a move, and a
guard that failed once the records lane applied that move would punish the very
edit the note exists to enable.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
NOTE_REL = (
    "research/market_intelligence_productization/"
    "W9_LEDGER_NOTE_F06_2026-09-13.md"
)
NOTE = REPO_ROOT / NOTE_REL

ROW_IDS = ("MO-PAID-020", "MO-PAID-021", "MO-DELTA-002")

# The ledger's own vocabulary, and the subset a proposal may put in a state column.
VOCABULARY = {
    "NOT_BUILT",
    "PARTIAL",
    "BUILT_NOT_PROVEN",
    "SPEC_ONLY",
    "PROVEN_LIVE",
}
PROPOSABLE = VOCABULARY - {"PROVEN_LIVE"}

# Read-at commit of origin/main, and the four merges the note cites as ancestors of it.
BASE_SHA = "321da62b3b0163b6ab5a287fb9847a13ed7f3ed2"
MERGE_SHAS = {
    "#6920": "67ad703bd24d637ed42c5511947c82f1c1cb0c3a",
    "#7007": "961a9c3d270a4642104ec32c39c7faf1656b8f2b",
    "#6905": "3bbca5375cbe7fccd13a4f02f3d2e6d3dba3eee2",
    "#6966": "9c6e1999bb9a9a6e904a98ea617cade16594b404",
}

# Every move must carry these labels: the ruling's five items, per row.
REQUIRED_MOVE_LABELS = (
    "row_id:",
    "quoted stale text",
    "merge citation:",
    "ancestor claim:",
    "proposed capability_state_c2:",
    "proposed next_bounded_child:",
)

PROPOSED_STATE_RE = re.compile(
    r"^- proposed capability_state_c2: `([A-Z_]+)`\s*$", re.MULTILINE
)
MOVE_HEADING_RE = re.compile(
    r"^## \d+\. LEDGER_MOVE #(\d+) — `?(MO-[A-Z]+-\d+)`?\s*$", re.MULTILINE
)
BARE_BUILT_RE = re.compile(r"(?<![A-Za-z0-9_])BUILT(?![A-Za-z0-9_])")

# (pattern, what it would mean). The F06 lane has no database surface, so the
# ruling's "no Supabase project reference" is read strictly: the word itself is
# banned here, not only the host and reference shapes.
FORBIDDEN_SECRET_SHAPES = (
    (r"(?i)supabase", "a database project reference"),
    (r"[A-Za-z0-9]{10,}\.supabase\.co", "a database project host"),
    (r"(?i)\bproject_ref\b\s*[:=]", "a database project reference field"),
    (r"\bsbp_[A-Za-z0-9]", "a database access-token prefix"),
    (r"(?i)service_role", "a database service-role key name"),
    (r"\bPAT\b", "a personal access token named as an acronym"),
    (r"\bghp_[A-Za-z0-9]{10,}", "a GitHub personal access token"),
    (r"\bgithub_pat_[A-Za-z0-9]{10,}", "a GitHub fine-grained token"),
    (r"\bsk-[A-Za-z0-9]{10,}", "an OpenAI-shaped secret key"),
    (r"\bxox[baprs]-[A-Za-z0-9-]+", "a Slack token"),
    (r"\bAKIA[0-9A-Z]{16}\b", "an AWS access key id"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "a private key block"),
    (r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", "a JSON web token"),
    (r"(?i)\bbearer\s+[A-Za-z0-9._\-]{16,}", "a bearer credential"),
    (
        r"(?i)\b(api[_-]?key|access[_-]?token|password|passwd|secret[_-]?key)"
        r"\b\s*[:=]\s*\S{8,}",
        "a credential written as an assignment",
    ),
)


@pytest.fixture(scope="module")
def note() -> str:
    assert NOTE.is_file(), f"W9 F06 ledger note missing at {NOTE_REL}"
    return NOTE.read_text(encoding="utf-8")


def test_note_lives_at_the_ruled_path_in_the_productization_index() -> None:
    # R1 names the path exactly. The productization directory listing IS the
    # index for this record family, so the note must sit in it, dated.
    assert NOTE.parent == (
        REPO_ROOT / "research" / "market_intelligence_productization"
    )
    assert NOTE.name == "W9_LEDGER_NOTE_F06_2026-09-13.md"
    assert NOTE.stat().st_size > 8000, "note is too short to carry three argued moves"


def test_note_names_every_ruled_row_id(note: str) -> None:
    for row_id in ROW_IDS:
        assert row_id in note, f"ledger row {row_id} is missing from the note"


def test_note_uses_no_bare_built_state_word(note: str) -> None:
    # The vocabulary has no one-word shipped state. BUILT_NOT_PROVEN and
    # NOT_BUILT are both legal; a standalone BUILT is a state word the ledger
    # does not have, and it is how a merged capability gets read as a proven one.
    offenders = [
        note[max(0, m.start() - 60):m.end() + 60].replace("\n", " ")
        for m in BARE_BUILT_RE.finditer(note)
    ]
    assert not offenders, f"standalone BUILT is not a ledger state: {offenders}"


def test_note_records_no_project_reference_token_or_key(note: str) -> None:
    offenders = []
    for pattern, meaning in FORBIDDEN_SECRET_SHAPES:
        for match in re.finditer(pattern, note):
            offenders.append(
                f"{meaning} at offset {match.start()}: "
                f"{note[max(0, match.start() - 40):match.end() + 40]!r}"
            )
    assert not offenders, "the note must carry no secret material: " + "; ".join(offenders)


def test_note_carries_exactly_three_moves_in_ruling_order(note: str) -> None:
    moves = MOVE_HEADING_RE.findall(note)
    assert [number for number, _ in moves] == ["1", "2", "3"], moves
    assert tuple(row for _, row in moves) == ROW_IDS, moves


def test_every_move_carries_the_fields_the_ruling_requires(note: str) -> None:
    headings = list(MOVE_HEADING_RE.finditer(note))
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(note)
        block = note[heading.start():end]
        missing = [label for label in REQUIRED_MOVE_LABELS if label not in block]
        assert not missing, f"LEDGER_MOVE #{heading.group(1)} is missing {missing}"


def test_every_proposed_state_is_vocabulary_and_never_proven_live(note: str) -> None:
    proposed = PROPOSED_STATE_RE.findall(note)
    assert len(proposed) == 3, f"expected one proposed state per move, got {proposed}"
    for state in proposed:
        assert state in PROPOSABLE, f"{state} is not a proposable ledger state"
        assert state != "PROVEN_LIVE", "no production readback exists for these rows"
    # Two rows have a merged producer and a merged render path; one has neither.
    assert proposed == ["BUILT_NOT_PROVEN", "BUILT_NOT_PROVEN", "NOT_BUILT"], proposed


def test_note_says_in_words_that_it_proposes_and_does_not_apply(note: str) -> None:
    lowered = note.lower()
    assert "proposed, not applied" in lowered
    assert "#7014" in note, "the note must name the lane that owns the ledger CSV"
    assert "records_only" in lowered.replace(" ", "_") or "RECORDS_ONLY" in note


def test_every_merge_citation_names_a_full_sha_and_the_read_at_base(note: str) -> None:
    # An ancestor claim is only checkable if it names both endpoints in full.
    assert BASE_SHA in note, "the note must name the origin/main commit it was read at"
    for pull, sha in MERGE_SHAS.items():
        assert pull in note, f"merge citation {pull} is missing"
        assert sha in note, f"{pull}'s merge commit {sha} is missing"
    headings = list(MOVE_HEADING_RE.finditer(note))
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(note)
        block = note[heading.start():end]
        cited = [sha for sha in MERGE_SHAS.values() if sha in block]
        assert cited, f"LEDGER_MOVE #{heading.group(1)} cites no full merge commit sha"
        assert "git merge-base --is-ancestor" in block, (
            f"LEDGER_MOVE #{heading.group(1)} does not name how its ancestor claim was checked"
        )


def test_note_counts_no_open_pull_request_as_merged(note: str) -> None:
    # The two residuals are in flight. The note must say so and must not offer
    # either as a merge citation for a proposed state.
    for pull in ("#7102", "#7122"):
        assert pull in note, f"in-flight residual {pull} should be named"
    heading_spans = list(MOVE_HEADING_RE.finditer(note))
    for index, heading in enumerate(heading_spans):
        end = (
            heading_spans[index + 1].start()
            if index + 1 < len(heading_spans)
            else len(note)
        )
        block = note[heading.start():end]
        citation = re.search(
            r"^- merge citation:.*?(?=\n- )", block, re.MULTILINE | re.DOTALL
        )
        assert citation, f"LEDGER_MOVE #{heading.group(1)} has no merge citation block"
        text = citation.group(0)
        for pull in ("#7102", "#7122"):
            if pull in text:
                assert "unmerged" in text or "in flight" in text, (
                    f"{pull} is open and may only appear in a citation as in-flight"
                )


def test_paste_ready_block_carries_all_three_moves(note: str) -> None:
    # R1's purpose: a records lane pastes this without re-deriving anything.
    block = note.split("```text", 1)
    assert len(block) == 2, "the note must carry one fenced paste-ready block"
    paste = block[1].split("```", 1)[0]
    for number, row_id in zip(("1", "2", "3"), ROW_IDS):
        assert f"LEDGER_MOVES #{number}" in paste, f"paste block is missing move #{number}"
        move = paste.split(f"LEDGER_MOVES #{number}", 1)[1]
        move = move.split("LEDGER_MOVES #", 1)[0]
        assert f"row_id: {row_id}" in move, f"move #{number} does not name {row_id}"
        assert "ancestor_claim:" in move, f"move #{number} has no ancestor claim"
        assert "merge_citation:" in move, f"move #{number} has no merge citation"
        state = re.search(r"proposed_capability_state_c2: ([A-Z_]+)", move)
        assert state, f"move #{number} proposes no state"
        assert state.group(1) in PROPOSABLE, f"move #{number} proposes {state.group(1)}"
        assert "proposed_next_bounded_child:" in move, f"move #{number} proposes no child"


def test_note_states_the_vocabulary_it_is_allowed_to_use(note: str) -> None:
    for state in sorted(VOCABULARY):
        assert state in note, f"the note must state the vocabulary word {state}"
