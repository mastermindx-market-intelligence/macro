"""asia-close.yml — Asia ownership fence (Options PIT/campaign narrow roots).

The Options PIT episode root and the campaign-v2 root are OWNED by their
narrow publishers. Asia's broad ``git add data/ site/qledger/`` (collect
stage) and ``git add data/ site/`` (engine stage) are bracketed by
``bash scripts/ci/options_signal_nightly.sh exclude-broad`` so neither the
collect nor the engine commit can smuggle an Options artifact onto the Asia
lane.

Ported from the 7193 integration proof (commit
a465e45e9082096432b31ca9989799b4207d486b).  Only the fixture step names that
delimit the collect and engine sections are adapted to current main; the
semantic assertion (two ``exclude-broad`` calls bracket each broad ``git
add``) is unchanged. Filename kept for the PR-8320 contract-delta wiring
audit; the test asserts the Asia ownership fence, not China heatmap
freshness.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "asia-close.yml"


def test_asia_broad_publishers_exclude_options_narrow_roots_around_staging() -> None:
    """Asia must never acquire the Options PIT/campaign roots owned by narrow publishers."""
    workflow = WORKFLOW.read_text(encoding="utf-8")
    exclusion = "bash scripts/ci/options_signal_nightly.sh exclude-broad"

    # Collect stage: bracketed by the "commit collected asia data" step and the
    # first later step name (timings band — build-china on current main; this is
    # the adapted fixture locator vs 7193's "build + verify China A-share heatmap").
    collected_start = workflow.index("name: commit collected asia data")
    collected_end = workflow.index("name: timings band — build-china (W2)", collected_start)
    collected = workflow[collected_start:collected_end]
    collected_stage = collected.index("git add data/ site/qledger/")
    collected_exclusions = [
        match.start() for match in re.finditer(exclusion, collected)
    ]
    assert len(collected_exclusions) == 2
    assert collected_exclusions[0] < collected_stage < collected_exclusions[1]

    # Engine stage: bracketed by the "commit engine outputs" step and the
    # "publish CN/HK stores to R2" step (unchanged vs 7193 — both step names
    # still exist on current main).
    output_start = workflow.index("name: commit engine outputs")
    output_end = workflow.index(
        "name: publish CN/HK stores to R2 (additive; no-op without creds)",
        output_start,
    )
    output = workflow[output_start:output_end]
    output_stage = output.index("git add data/ site/")
    output_exclusions = [
        match.start() for match in re.finditer(exclusion, output)
    ]
    assert len(output_exclusions) == 2
    assert output_exclusions[0] < output_stage < output_exclusions[1]