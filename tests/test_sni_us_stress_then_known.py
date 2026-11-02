"""test_sni_us_stress_then_known.py — pin verified then_known entries to repo evidence.

Synthetic / in-memory copies only. Does not read live market data.
A verified entry must carry a resolvable evidence pointer; this test
does not mint identity ids and does not set any authority flag true.
"""
import copy
import subprocess
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/us_stress"),
)

from stress_set import (  # noqa: E402
    check_profiles,
    load_profiles,
)

ROOT = Path(__file__).resolve().parents[1]
PROFILES_DIR = ROOT / "research/single_name_intelligence/us_stress/profiles"
TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"]


def _evidence_git_path(evidence):
    """Return the repo path prefix of an evidence pointer, or None."""
    if not isinstance(evidence, str):
        return None
    text = evidence.strip()
    if not text:
        return None
    if "@" not in text:
        return None
    path = text.split("@", 1)[0].strip()
    if not path or path.startswith("/") or ".." in Path(path).parts:
        return None
    return path


def _git_path_exists(path):
    proc = subprocess.run(
        ["git", "cat-file", "-e", "HEAD:%s" % path],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def then_known_evidence_problems(profiles):
    """Return problem strings for verified then_known entries.

    A verified entry without a non-empty evidence pointer whose path
    resolves in git (git cat-file -e HEAD:<path>) is a problem. A
    verified entry that also carries a contradiction key is a problem.
    """
    problems = []
    if not isinstance(profiles, dict):
        return ["profiles must be a mapping"]
    for name, profile in profiles.items():
        entries = (profile or {}).get("then_known") or []
        if not isinstance(entries, list):
            problems.append("%s then_known is not a list" % name)
            continue
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            if entry.get("verified") is not True:
                continue
            loc = "%s then_known[%s] field=%s" % (name, i, entry.get("field"))
            if "contradiction" in entry:
                problems.append("%s verified true with contradiction key" % loc)
            evidence = entry.get("evidence")
            if not isinstance(evidence, str) or not evidence.strip():
                problems.append("%s verified true with empty evidence" % loc)
                continue
            path = _evidence_git_path(evidence)
            if path is None:
                problems.append(
                    "%s evidence is not path@sha:... (%r)" % (loc, evidence)
                )
                continue
            if not _git_path_exists(path):
                problems.append(
                    "%s evidence path %s does not resolve at HEAD" % (loc, path)
                )
    return problems


def test_committed_profiles_load_and_check():
    profiles = load_profiles(PROFILES_DIR)
    assert set(profiles) == set(TICKERS)
    check_profiles(profiles)


def test_every_verified_entry_has_resolvable_evidence():
    profiles = load_profiles(PROFILES_DIR)
    problems = then_known_evidence_problems(profiles)
    assert problems == []


def test_no_verified_entry_carries_contradiction():
    profiles = load_profiles(PROFILES_DIR)
    for name, profile in profiles.items():
        for i, entry in enumerate(profile.get("then_known") or []):
            if entry.get("verified") is True:
                assert "contradiction" not in entry, (
                    "%s then_known[%s] verified true with contradiction" % (name, i)
                )


def test_verified_true_without_evidence_is_reported():
    profiles = load_profiles(PROFILES_DIR)
    clone = copy.deepcopy(profiles)
    entry = clone["AAPL"]["then_known"][0]
    entry["verified"] = True
    entry.pop("evidence", None)
    problems = then_known_evidence_problems(clone)
    assert problems, "checker must report verified true with no evidence"
    assert any("empty evidence" in p for p in problems)
