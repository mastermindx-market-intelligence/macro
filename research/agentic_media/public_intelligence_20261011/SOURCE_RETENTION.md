# Existing White House sentinel: source retention

Operation `mmx-public-intelligence-delivery-20261011-local-ceo-001`.

The existing feed parser supplied source text only in memory; the alert ledger's
`raw_text` is a model response. The next Press acquisition slice keeps immutable
normalized feed documents before the existing brain and seen-item filter, through
the same sentinel. It adds no poll, provider call, schedule, competing writer,
Chronicle event, earnings packet, public article or rights approval.

## Public-repository boundary

A fresh `gh repo view mastermindx-market-intelligence/macro --json visibility,isPrivate`
reported `PUBLIC`, `isPrivate:false` on 2026-10-11. A bounded review rejected the
initial implementation because `data/whitehouse` is staged and pushed by the
existing sentinel. That uncommitted implementation was repaired before push.

Captures now reside under the runner user's
`~/.local/share/mastermind/whitehouse/source_documents`, outside every Git checkout.
Resolved repository descendants, another checkout's `.git` ancestor and symlink
aliases into those paths are refused before storage. The directory must be mode
0700 and documents mode 0600. Complete fsynced bytes are linked exclusively into
the content address, then the directory is synced. Existing corruption or unsafe
permissions are refused, never overwritten or silently repaired. The existing
workflow and its public Git staging scope are unchanged; no Actions artifact or
public object upload is added. Rights remain unqualified, stage/emit denied.

This is host-local, same-user retention. It is not cloud backup, cross-host
availability, source authenticity, full page retention, acquisition completeness,
a defense against privileged/same-user hostile processes, or a public rights grant.
Capture failure preserves the ordinary desk evaluation path and logs the missing
evidence. Page-only never captures, and synthetic Treasury items enter afterward.

## Verification

- Before implementation, eight new retention tests failed and one passed; retained
  output: `/tmp/mmx-source-retention-red.log`.
- After the containment repair, the five affected suites passed: **70 passed in
  4.03 seconds**. Command: `python3 -m pytest tests/test_whitehouse_feed.py
  tests/test_whitehouse_build.py tests/test_whitehouse_brain.py
  tests/test_whitehouse_w5.py tests/test_fix43_analyst_and_whitehouse.py -q
  --tb=short --basetemp=../mmx-source-retention-private`.
- Regressions include actual `git add data/whitehouse`, permission and symlink
  refusals, corruption, concurrent exclusive writes, no partial result after a
  failed link, changed-source revisions, seen-item capture without brain replay,
  one ordinary brain evaluation after capture failure, and page-only exclusion.
- The bounded independent repair review accepted this host-local boundary.
- `whitehouse_host_retention_replay.json` binds a real retained official feed:
  30 parsed items, one exact candidate URL, matching original body, verified file
  and directory modes and content address. No network/model/stage/publication call.
  This exercised working local code, not an installed production sentinel.

The parser now labels description fallback and 12,000-character truncation.
Description-only bodies are also bounded at 12,000 characters (previously unbounded);
ordinary encoded-content bodies keep their previous bound. Retained text is
normalized RSS content, not raw HTTP or proof of the complete publisher page.

## Delivery frontier

PR8786's a85aeb97144e469719b1c4ef4a77da55fa27c103 passed all 21 binding checks in
CI38169345491. The protected controller refreshed it onto main770a48ff5ade at
90b5fe5d6297a3000d7af84c7a859c3766574a9e; that head needs its own terminal CI.
All 13 prepared installation-source hashes and all three prepared page hashes
are unchanged by that refresh. The retention change is saved on the recovery
branch separately; it has not been added to the armed release or installed.

After PR8786 lands, verify installed source/served bytes and browser paths, then
integrate this accepted producer change from fresh main. The White House/NVIDIA
editorial candidate remains unadmitted: its real 17-check replay has 12 passes
and five failures, including zero first-party receipts and zero first-party
numeric value share. Never relabel government facts to force a D14 pass.

## Candidate document preparation

`replay_event_candidate.py --formatted --peer-root <existing stage root>` now
adds the existing byline/footer and required document metadata without changing
reviewed prose or fact tiers. Actual replay: **15 of17 checks pass**, with only
`our_value` (0% versus40%) and `receipts` (0 versus5) failing. All334 prose words
remain; both existing stage files retain their hashes.
`whitehouse_formatted_candidate_validation.json` binds the exact preparation
script, source, configuration, validator, original candidate and prepared JSON.
This is a prepared research artifact, not an admitted/staged/public Press article
or a generated D14 acceptance sample. The original12/17 replay remains retained.

## Opt-in external candidate planning — 2026-10-11 23:06 UTC

Source commit `7f0759ee547c` adds `desk_planner.plan_external_candidate` over the
existing sentinel's exact retained document. Its closed input binds the document,
body, qualification and copyright-policy hashes, reviewed literal quantities,
ticker association and arithmetic. It rejects incomplete/truncated text, altered
identity, future/stale/naive clocks and missing rendered dossiers. The reviewed
White House material was already qualified for this public research record; the
byte-identical sentinel object is retained with it. General host captures remain
private and unqualified. No poll or source-ownership transfer was introduced.

This returns a planning-only envelope with a validation context, not an ordinary
writer slot. Default `plan()` and the runner are unchanged. Coverage dedupe is
reported and the existing cadence ceiling is exposed; no reservation or cadence
consumption occurs. Future writer admission must recheck both. The denial fields
are descriptive here, not a claim of a new generic staging enforcement gate.

Verification: `python3 -m pytest tests/test_press_external_candidate.py
 tests/test_press_planner.py tests/test_press_validators.py -q` returned **154
passed in 5.29s**. The first run found a test incorrectly assuming the existing
fixture's staging directory did not exist; it was repaired to compare all input
file hashes before and after. Quantity-substring rejection was added and passed.
Independent source review accepted reader SHA256
`b73fd096e72592684ae89262342606a5f14b2f05e349c4e914a6e996d13a273a`.

Verified command: `python3
research/agentic_media/public_intelligence_20261011/replay_event_candidate.py
--peer-root /Volumes/Mastermind/agent-workspaces/codex/69a1/macro-main --formatted
--external-plan`. The saved `whitehouse_external_plan_validation.json` binds
source commit and module hashes. The real candidate remains **15/17**, failing
only our-value and receipts, with both staged peer hashes unchanged. All external
figures and external-only arithmetic remain third-party. Hashes bind the reviewed
rights input; they do not independently grant rights or publication approval.

CI integration retains the existing `press-lane` owner and adds the new suite to
its manifest command. This is the existing data-health lane, not a new claim of
pre-merge proof. Runtime scope inference confirms all six new code/test/evidence
paths select that lane (source fixtures through the conservative read fallback).
The workflow start catch-all already covers them; no redundant global workflow
change is retained. `check_ci_trigger_closure.py` reports zero gaps; manifest
`--validate-only --workflow .github/ci/legacy-jobs.yml` passes;28 Press workflow
contract tests pass in3.90s. The curated import-closure test passed in131.78s.
No application or test behavior changed after the154-test run.
