"""Fail when an instruction surface tells a session to wait for a named owner.

The Chairman directive of 2026-10-24, reconciled with Mastermind PR #1842, is
one clause: ownership is a role held by the session doing the work. A stall
phrase is allowed only in the same file as that leadership-takeover clause, or
when the same line negates the stall. Historical workstream and handoff records
are outside this scan.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

CLAUSE_MARKERS = (
    "Ownership is a role, not a session",
    "assumes leadership",
    "records the takeover",
    "never self-merge or approve",
)

SCAN_ROOTS = (
    "AGENTS.md",
    "CLAUDE.md",
    "agentos/README.md",
    "agentos/schema/workstream.schema.yml",
    "agentos/schema/handoff.schema.yml",
    "research/MASTERMIND_AGENT_HANDOFF_PROTOCOL.md",
    "research/MASTERMIND_AGENT_OS_STATE_SCHEMA.md",
    "scripts/agentos.py",
)

ENTRYPOINTS = SCAN_ROOTS

STALL_RE = re.compile(
    r"(?i)("
    r"held for a separate owner|"
    r"under separate owner|"
    r"awaiting owner(?: acceptance)?|"
    r"\bowner session\b|"
    r"wait for (?:an |the )?owner|"
    r"owner must act|"
    r"owner must accept|"
    r"\bowner acceptance\b|"
    r"not a takeover"
    r")"
)
NEGATION_RE = re.compile(
    r"(?i)\b(?:never|do not|does not|don't|must not|rather than|not a command)\b"
)


def has_takeover_clause(text: str) -> bool:
    return all(marker in text for marker in CLAUSE_MARKERS)


def stall_violations(text: str) -> list[str]:
    if has_takeover_clause(text):
        return []
    found: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        match = STALL_RE.search(line)
        if match is None:
            continue
        if NEGATION_RE.search(line):
            continue
        found.append(f"{number}: {line.strip()}")
    return found


def test_wait_for_owner_without_clause_fails():
    assert stall_violations("This lane is awaiting owner acceptance.")


def test_same_gate_with_clause_passes():
    text = (
        "This lane is awaiting owner acceptance.\n"
        "Ownership is a role, not a session: never wait on an absent/orphaned owner "
        "or ask the Chairman to find old chats. The current session assumes leadership, "
        "records the takeover in the source-linked handoff, and proceeds. Independent "
        "review is still required; never self-merge or approve."
    )
    assert stall_violations(text) == []


def test_instruction_surfaces_do_not_wait_for_a_named_owner():
    violations: list[str] = []
    for rel in SCAN_ROOTS:
        text = (ROOT / rel).read_text(encoding="utf-8")
        for line in stall_violations(text):
            violations.append(f"{rel}: {line}")
    assert violations == []


@pytest.mark.parametrize("rel", ENTRYPOINTS)
def test_entrypoint_carries_the_combined_leadership_clause(rel):
    text = (ROOT / rel).read_text(encoding="utf-8")
    assert has_takeover_clause(text), rel
    assert "ask the Chairman to find old chats" in text
    assert "HANDOFF_SOURCE_LINK_V1" in text


def test_claim_is_not_a_lease_and_leadership_still_proceeds():
    readme = (ROOT / "agentos/README.md").read_text(encoding="utf-8")
    assert "not a takeover" not in readme
    assert "not a lease" in readme
    assert "invariant I1" in readme
    assert "not live activity" in readme
