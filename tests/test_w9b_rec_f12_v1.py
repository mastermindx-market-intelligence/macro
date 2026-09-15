"""Pin the W9 / W9B-REC F12 v1 DEC draft note.

This packet is records-only. It drafts a companion DEC note against the
closed PR #6925, names G2 tenancy `0014_tenancy_foundation` as applied as
already true, and does NOT apply, reopen, or rebuild anything. The pin
test guards that posture: file exists, no secrets / no real Supabase
project_ref, no standalone "BUILT" assertion about the F12 v1 Public-API
surface. Mirrors `tests/test_b_rec3_wave_boundary_records.py` for
house style: repo-root `_ROOT`, no network, no subprocess, no read of any
other checkout.

RED if the note is missing, if it carries a 20-letter lowercase Supabase
project_ref literal, a PAT-shaped token, a service-account/private-key
literal, or asserts that the F12 v1 Public-API surface is BUILT (this
packet is explicitly `NOT APPLIED` — see note §6 authority ceiling).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]

NOTE = _ROOT / (
    "research/market_intelligence_productization/"
    "W9_W9B_REC_F12_V1_2026-09-13.md"
)

# A Supabase project reference is a 20-character run of lowercase letters.
# The 0014 tenancy receipt uses the literal placeholder `{ref}`; this
# guard keeps a real one from ever being committed by a later edit.
_PROJECT_REF_SHAPE = re.compile(r"[a-z]{20}")

# GitHub PAT / fine-grained token shapes, and common service-account key
# envelopes. Conservative: matches `ghp_`, `gho_`, `ghu_`, `ghs_`, `ghr_`,
# `github_pat_`, `xox[abprs]-`, and PEM-style `-----BEGIN ... PRIVATE KEY-----`
# blocks. A note that ships with a real token fails RED here.
_TOKEN_SHAPES = (
    re.compile(r"\bghp_[A-Za-z0-9]{20,}"),
    re.compile(r"\bgho_[A-Za-z0-9]{20,}"),
    re.compile(r"\bghu_[A-Za-z0-9]{20,}"),
    re.compile(r"\bghs_[A-Za-z0-9]{20,}"),
    re.compile(r"\bghr_[A-Za-z0-9]{20,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)

# Standalone "BUILT" assertions about the F12 v1 Public-API surface. The
# note's plain posture is `NOT APPLIED` + `NOT_BUILT` — anything that
# asserts the surface itself is BUILT (without a negation between
# `F12 v1` and `BUILT`) is a posture violation. The regex allows
# qualified/negated phrasings (e.g. "is NOT BUILT", "stays NOT_BUILT",
# "was NOT merged"); it only RED-flags a standalone positive claim
# scoped to F12 v1 Public-API.
_STANDALONE_BUILT = re.compile(
    r"(?im)^[^\n]{0,80}\bF12[ _-]?v1(?:(?![\w-]*\b(?:NOT|not|never|n'?t|"
    r"unbuilt|UNBUILT|no|No|NO)\b)[^\n]){0,40}\bBUILT\b"
)


# ---------------------------------------------------------------- existence


def test_note_exists() -> None:
    assert NOTE.exists(), f"missing W9B-REC F12 v1 draft note: {NOTE}"


def test_note_is_markdown() -> None:
    text = NOTE.read_text(encoding="utf-8")
    assert text.startswith("# "), f"{NOTE.name}: missing H1 header"
    # Plain-language posture check (note §6 explicitly says records-only,
    # NOT APPLIED, NOT_BUILT).
    assert "NOT APPLIED" in text, (
        f"{NOTE.name}: missing 'NOT APPLIED' posture marker (note §6)"
    )


# ---------------------------------------------------------------- secrets / refs


def test_note_has_no_real_supabase_project_ref() -> None:
    """A real 20-letter lowercase Supabase project_ref must not appear.

    The 0014 tenancy receipt uses the literal placeholder `{ref}`; this
    guard rejects a real reference that a later copy/paste might commit.
    """
    text = NOTE.read_text(encoding="utf-8")
    matches = _PROJECT_REF_SHAPE.findall(text)
    assert not matches, (
        f"{NOTE.name}: real Supabase project_ref-shaped token(s) present: "
        f"{matches!r}"
    )


def test_note_has_no_pat_or_service_key() -> None:
    """No GitHub PAT / fine-grained token / service-account key literal."""
    text = NOTE.read_text(encoding="utf-8")
    offenders: list[str] = []
    for shape in _TOKEN_SHAPES:
        for hit in shape.findall(text):
            offenders.append(hit)
    assert not offenders, (
        f"{NOTE.name}: secret-shaped token literal(s) present: {offenders!r}"
    )


# ---------------------------------------------------------------- posture


def test_note_does_not_assert_f12_v1_public_api_built() -> None:
    """The note must not claim the F12 v1 Public-API surface is BUILT.

    This packet's authority ceiling is `NOT APPLIED` + `NOT_BUILT`. A
    standalone "F12 v1 ... BUILT" assertion is the violation this guard
    exists to prevent. Negated/qualified phrasings ("is NOT BUILT",
    "stays CLOSED") pass; only a positive claim red-flags.
    """
    text = NOTE.read_text(encoding="utf-8")
    bad = _STANDALONE_BUILT.findall(text)
    assert not bad, (
        f"{NOTE.name}: standalone 'F12 v1 ... BUILT' assertion(s) present "
        f"(posture is NOT APPLIED / NOT_BUILT): {bad!r}"
    )


def test_note_names_0014_tenancy_as_applied() -> None:
    """The note must name `0014_tenancy_foundation` as applied already.

    This is the G2 tenancy receipt; the W9 ruling requires the note name
    it as applied-as-already-true so the drafted DEC's posture stays
    anchored to a real receipt, not a planned one.
    """
    text = NOTE.read_text(encoding="utf-8")
    assert "0014_tenancy_foundation" in text, (
        f"{NOTE.name}: does not name the 0014 tenancy foundation receipt "
        "(W9 ruling requires the note name G2 tenancy 0014 applied as "
        "already true)"
    )
    assert "applied" in text.lower(), (
        f"{NOTE.name}: does not state that 0014 is applied (posture is "
        "'applied as already true', not 'pending' or 'planned')"
    )


def test_note_does_not_reopen_pr_6925() -> None:
    """The note must NOT reopen PR #6925.

    #6925 stays closed; the note records that posture. A plain "NOT
    reopen" / "stays CLOSED" / "does NOT reopen" phrasing is the compliant
    shape.
    """
    text = NOTE.read_text(encoding="utf-8")
    assert "6925" in text, (
        f"{NOTE.name}: does not name PR #6925 at all (the note must record "
        "the closed PR as the subject of the drafted DEC)"
    )
    # The note's posture marker (R1) is explicit: "do not reopen #6925".
    lowered = text.lower()
    assert (
        "does not reopen" in lowered
        or "does not re-open" in lowered
        or "stays closed" in lowered
        or "kept closed" in lowered
        or "not reopen" in lowered
    ), (
        f"{NOTE.name}: missing 'does not reopen / stays closed' posture on "
        "#6925 (R1 of the W9 ruling)"
    )


# ---------------------------------------------------------------- blocklists


def test_note_does_not_regenerate_blocklists() -> None:
    """The note must not edit the F00C ledger or rebuild compiled blocklists.

    R0 forbids F00C CSV edits; R1 forbids blocklist regen. The note
    records state without mutating either artefact.
    """
    text = NOTE.read_text(encoding="utf-8")
    assert "F00C" in text, (
        f"{NOTE.name}: does not name F00C ledger at all (the note must "
        "record that F00C CSV is read-only input, not mutated)"
    )
    # The compliant posture marker.
    assert (
        "not regenerate" in text.lower()
        or "not edit" in text.lower()
        or "read-only input" in text.lower()
        or "does not edit" in text.lower()
        or "does not mutate" in text.lower()
    ), (
        f"{NOTE.name}: missing 'do not regenerate / not mutate / read-only "
        "input' posture on F00C / blocklists (R0/R1 of the W9 ruling)"
    )


# ---------------------------------------------------------------- parametrized witnesses


@pytest.mark.parametrize(
    "needle, why",
    [
        ("NOT_BUILT", "F12 v1 Public-API surface is NOT_BUILT, not BUILT"),
        ("CLOSED", "#6925 stays CLOSED, not MERGED/OPEN"),
        ("DRAFT", "companion DEC is a draft, not applied"),
        ("0014_tenancy_foundation.sql", "tenancy SQL file name pinned"),
        (
            "supabase_receipt_0014_tenancy_foundation_2026-09-08.json",
            "tenancy receipt path pinned",
        ),
        (
            "MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv",
            "F00C ledger cited by path (read-only input)",
        ),
    ],
)
def test_note_carries_required_witness_phrases(needle: str, why: str) -> None:
    """Compliance witnesses the note must carry to satisfy W9 ruling R0/R1.

    Each witness is a literal that proves a posture claim the W9 ruling
    requires. The list is closed; adding a witness is a code change, not a
    note change.
    """
    text = NOTE.read_text(encoding="utf-8")
    assert needle in text, (
        f"{NOTE.name}: missing witness literal {needle!r} ({why})"
    )