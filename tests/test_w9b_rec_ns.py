"""Pin packet W9B_REC_NS: the Supabase migration namespace note exists and carries
nothing the records lane's own law forbids.

One suite (seat ruling R2 said one test; the file now holds two functions — the original
pin test below and the round-3 truth-pin test the seat heal added). The first asserts the four named properties of
`research/market_intelligence_productization/W9_W9B_REC_NS_2026-09-13.md`:
the note exists; it carries no Supabase personal access token, no service-role key and no
20-letter-shaped credential token; it never uses BUILT as a standalone state word (the only
allowed form that starts with BUILT is BUILT_NOT_PROVEN); and it names every anchor the ruling
requires — 0013, 0023, 0024, 0026 — so a future edit that drops the 0024 collision or the 0026
proposal fails here instead of reaching the records stack.

The suite reads this repository only: the note itself. It never reads the F00C ledger CSV,
never shells to the Terminal checkout, and never reads the seat's handoff kit. A red on this
test is a defect in this note; a green on this test is not a claim about any other repo's
state.

RED before the packet: the note did not exist, so the first assertion failed with
`missing W9 namespace note: <path>`.
"""
from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

NOTE = _ROOT / (
    "research/market_intelligence_productization/"
    "W9_W9B_REC_NS_2026-09-13.md"
)

# The four anchors ruling R1 requires the note to name. Drop any one and the note stops
# being the note the ruling asked for: 0013–0023 state (the prefix 0013 anchors the range),
# 0022/0023 unapplied (the prefix 0023 anchors the named-gap block), the 0024 double-claim
# (#577 vs #579 vs #581), and the proposed 0026 reservation for t_f12_10.
ANCHORS = ("0013", "0023", "0024", "0026")

# BUILT is not a state word in the F00C ledger. The only allowed spelling that starts with
# it is BUILT_NOT_PROVEN, and `\bbuilt\b` cannot match inside that word anyway: an underscore
# is a word character, so there is no boundary after BUILT. The check is case-insensitive on
# purpose — "the migration is built" in prose is the same unsupported claim as the state
# word, and the honest words are "merged" and "shipped".
_STANDALONE_BUILT = re.compile(r"\bbuilt\b(?!_not_proven)", re.IGNORECASE)

# A Supabase project reference, a personal access token, a service-role key, a JWT header, or
# a GitHub personal access token prefix. Every entry is a shape that appears in this estate
# only as a credential, or as the prefix that carries one. The note cites pull requests,
# merge commits, file paths and the seat's handoff-kit receipt path; the ref is never
# written. The 20-letter check is a defence against drift, not against any one specific
# value — a Supabase project reference is 20 lowercase alphanumerics by construction, and
# the regex matches a token of exactly twenty [a-z0-9] characters standing alone between
# whitespace, which covers every Supabase project reference shape this estate has ever
# carried and several base-58-shaped credentials besides.
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

# A Supabase project reference is a 20-character lowercase alphanumeric token by
# construction (see https://supabase.com/docs/guides/api/api-keys and the seat's own
# receipt JSONs, which carry it as `project_ref: "{ref}"`). The note must not contain any
# such token. The regex matches a word of exactly twenty [a-z0-9] characters surrounded by
# non-alphanumeric boundaries; underscores are excluded so identifiers like
# `0017_personal_accuracy_ledger` and `W9B_REC_NS` are not flagged.
_TWENTY_LETTER = re.compile(r"(?<![a-z0-9_])[a-z0-9]{20}(?![a-z0-9_])")


def test_the_w9_namespace_note_carries_every_anchor_and_says_nothing_forbidden() -> None:
    assert NOTE.exists(), f"missing W9 namespace note: {NOTE}"
    text = NOTE.read_text(encoding="utf-8")

    # (R2) every anchor the ruling names appears in the note.
    for anchor in ANCHORS:
        assert anchor in text, (
            f"the note does not name anchor {anchor!r}: a namespace note without all four "
            "anchors (0013, 0023, 0024, 0026) is not the note the ruling asked for"
        )

    # (R2) no standalone BUILT; BUILT_NOT_PROVEN is allowed and is the only form.
    standalone = sorted(set(_STANDALONE_BUILT.findall(text)))
    assert not standalone, (
        "BUILT is not a state word in the F00C ledger; the only allowed word that starts "
        "with it is BUILT_NOT_PROVEN. standalone uses found: "
        f"{standalone}; rewrite as 'merged' or 'shipped' or 'applied'"
    )

    # (R2) no Supabase project reference, personal access token or key.
    for token in _FORBIDDEN_TOKENS:
        assert token not in text, (
            f"the note carries {token!r}, which is a Supabase project reference, a "
            "personal access token or a key. Cite the merged pull request and the seat's "
            "handoff-kit receipt path instead, and never write the ref"
        )

    # (R2) no 20-letter-shaped credential token (catches Supabase project references and
    # base-58-shaped credentials that the prefix list above cannot enumerate).
    matches = sorted(set(_TWENTY_LETTER.findall(text)))
    assert not matches, (
        "the note carries a 20-letter-shaped token that looks like a Supabase project "
        "reference or a base-58 credential: "
        f"{matches}; cite the merged pull request and the seat's handoff-kit receipt "
        "path instead, and never write the ref"
    )


# --- Round-3 truth pins (seat, 2026-09-19): one test function that FAILS as a whole at bf526615 and
# 426cccc3 (some individual pins already held there; the false-ruling / REST-read / all-three /
# placeholder-clock / OPEN-row pins did not). Round-3b (rv3b m1) adds the present-tense pins. ---
_RULING_EXACT = '"#579 owns 0024, #577 owns 0025, #582 owns 0026 (reserved), #581 owns 0027."'
_FALSE_RULING = "#581 owns 0024"
_READ_DATE_EXACT = "(committed 2026-09-14T07:06:47Z; local 2026-09-14 00:06:47 -0700)"
_REST_READ = "contents/supabase/migrations/RESERVATIONS.json?ref=master"
_ROW_0027 = "0027: state=taken, packet=B-F12-10, pr=581, pr_state=merged, merged_sha=c9381593, applied_in_production=True, applied_date=2026-09-19"


def test_round3_truth_pins_ruling_date_read_and_no_placeholder_clock() -> None:
    text = NOTE.read_text(encoding="utf-8")
    assert _RULING_EXACT in text, "the seat ruling must be quoted exactly (0024->#579, 0025->#577, 0026 reserved, 0027->#581)"
    assert _FALSE_RULING not in text, "the false ruling sentence (#581 owning 0024) must not appear anywhere"
    assert _READ_DATE_EXACT in text, "origin/main read date must carry the UTC instant and the -0700 local time"
    assert "T00:06Z" not in text, "the -0700 wall time must never be written with a Z suffix"
    assert _REST_READ in text, "the re-verify block must quote the REST contents read, not GraphQL"
    assert _ROW_0027 in text, "the live 0027 row must be quoted verbatim"
    assert "all three 0024-claimers" in text and "all four 0024-claimers" not in text
    assert "07:5xZ" not in text and ":xxZ" not in text, "read timestamps are clocks, never placeholders"
    assert "| OPEN |" not in text, "the 2026-09-13 table must not present the three PRs as OPEN in the present tense"


def test_round3b_no_present_tense_open_claims():
    """rv3b MINOR 1: the 2026-09-13 narrative may describe the collision only as a dated read;
    the three Terminal PRs are MERGED (2026-09-19T03:15:10Z / 04:58:44Z / 06:36:06Z)."""
    text = NOTE.read_text(encoding="utf-8")
    for phrase in (
        "Three open Terminal pull requests each claim",
        "One open Terminal pull request",
        "Three open\nTerminal pull requests all claim",
        "because none of the three is merged",
        "The records stack has the leverage right now",
    ):
        assert phrase.replace("\\n", "\n") not in text, f"present-tense open-PR prose must not remain: {phrase!r}"
    assert "At the 2026-09-13 read, three Terminal pull requests each claimed" in text
    assert "which is what seat ruling h_t581 did" in text

