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


## Reviewed event clock versus publication clock — 2026-10-12

A fresh primary-source read found a concrete reason to keep these clocks separate:
[White House prepared remarks](https://www.whitehouse.gov/remarks/2026/10/remarks-by-director-michael-kratsios-at-the-science-a-new-golden-age-summit/)
have an October9 page-publication date but explicitly date the speech October8.
The later web date is not a new NVDA event and supplies no new ticker association.
No source body was copied into a new candidate or admitted to staging.

The opt-in planner now reads the qualification's separately reviewed ISO event
date, requires it no later than publication, preserves publication/observation
chronology, and applies the unchanged Brief window to that event date. Its result
exposes event, publication, observation and as-of clocks. Facts retain their
reviewed event date and all stage/emit/publication flags remain false. This is
explicit reviewed metadata, not automatic event-date extraction from arbitrary prose.

The earlier implementation already failed closed when dates differed, but could
not represent a legitimate later publication of a still-current event. Seven new
regressions cover that positive case, expired events, invalid date types/forms and
a postpublication event date. Actual red:2failed/33passed in36.33seconds. Corrected
external candidate, existing planner and validator suites:161passed in30.41seconds.
Commands: `python3 -m pytest tests/test_press_external_candidate.py -q --tb=short`
and `python3 -m pytest tests/test_press_external_candidate.py tests/test_press_planner.py tests/test_press_validators.py -q --tb=short`.
Logs remain `/tmp/mmx-event-clock-red.log` and `/tmp/mmx-event-clock-green.log`.
Source SHA256:f109055b0638d34193a50fe296bb2e545ee073184329e793dc1a5d98b1266675.
The existing Fabric adapter admitted a bounded independent review under
`mmx-press-event-clock-review-20261012-001`; the same retained result accepted
the exact source hash with no blocking finding. Root adjudicated the source and
161 passing tests before recording reviewer acceptance. The result is read-only
source review, not a new live-source or publication qualification.
Root made the small direct edit because dispatch/reintegration cost exceeded
the bounded repair; independent review uses admitted Fabric.


## Current report screen — October 12

The [CEA manufacturing report page](https://www.whitehouse.gov/research/2026/10/the-state-of-american-manufacturing/)
is dated October 10. Its [14-page PDF](https://www.whitehouse.gov/wp-content/uploads/2026/10/The-State-of-American-Manufacturing_Oct2026.pdf)
provides a current report-release premise, but does not make the cited company
commitments new issuer events. This is a parent source screen only: no retained
PDF ingestion, rights receipt, planner admission or Press draft was created.

Bounded findings from the primary sources:

- The report's printed page 1 cites 72,000 manufacturing jobs and 101,000 durable-goods jobs added in 2026. These are attributed CEA observations with their own periods, not new Mastermind calculations or company sales.
- Printed page 3 lists Apple's $600 billion commitment. [Apple's original release](https://www.apple.com/newsroom/2025/08/apple-increases-us-commitment-to-600-billion-usd-announces-ambitious-program/) dates the $100 billion increase to August 6, 2025, bringing a four-year commitment to $600 billion. Do not call that an October 2026 announcement or realized capital expenditure.
- The same report page describes Micron's $250 billion in terms of memory plants. [Micron's September 15 release](https://investors.micron.com/news/press-release/2026/Micron-Appoints-Deirdre-Hanford-to-Lead-Micron-Research-Labs/default.aspx) describes its previously announced plan as more than $250 billion across manufacturing **and R&D**. The category, horizon and vintage require reconciliation before a factory-capex claim.
- Printed pages 1 and 4 refer to nine versus fourteen consecutive months of manufacturing expansion. The latter names S&P PMI; the former does not identify the same series clearly. This is an unresolved series-definition ambiguity, not proof that either count is false.
- The PDF includes company quotations and vendor-derived S&P material. Government hosting alone is not blanket permission to reproduce those texts, charts or series. A short original factual report would need its own source-specific rights and editorial qualification.

The bounded candidate question is: which parts of the newly released government
investment tally represent older pledges, and what existing company evidence
shows subsequent delivery? AAPL is explicitly associated with the report; its
canonical stock page, and MU's, exist in cc5d3116 (`git cat-file -e
cc5d31160dd3584b067453bc3b11d78440133000:site/stocks/AAPL.html`, likewise MU).
This does not establish current hosted page behavior or new investment effects.

Five external observations are not five first-party analytical receipts. The
next qualification remains consumption of existing company/economic evidence,
with exact revisions and permitted access, followed by a relevant analytical
result. The RSS planning reader intentionally does not ingest PDF claims; this
screen does not bypass that interface or invent a replacement pipeline.

The attempted bounded Grok review
`mmx-press-current-report-review-20261012-001` was refused before launch on
Ubuntu0 with `SUPPORT_POLICY_STALE_ACTIVE_REFUSED` / `SUPPORT_PUBLICATION_REFUSED`.
Same-ID status reports `TERMINAL_FAILURE`, rc75, signal `prelaunch_failure`,
`result_available=false`. No review result was accepted, no worker is running,
and no alternate host/carrier retry occurred. This root screen used the already
permitted public web read path; it did not retry the refused support-publication
effect. Original Press delivery continues independently.


## Existing dossier capital evidence — offline replay, October12

To test a more relevant input for the October10 manufacturing-report premise,
root consumed the existing debt-maturity cache and pure cash-runway/capital-need
engines at protected main611f88003639aea7272ec30b1b4e7120020e23ea. The ticker/CIK
ledger, both source objects and all three engine modules are hash-bound in
retained_aapl_mu_capital_screen.json. No collector, credentials, staging provider
or publication was invoked, and no raw companyfacts cache was copied into this
record. Existing source ownership and interfaces are unchanged.

Reproduction: read the named revision's data/edgar/ticker_cik_ledger.json with
`git show`, select AAPL and MU, then read each exact source_path recorded in the
JSON. Verify all source_sha256 and engine_sha256 values before invoking
`engine.debt_maturity.extract_maturity_ladder(facts, cik=cik, as_of=date(2026,10,12))`,
`engine.cash_runway.extract_cash_runway(facts, cik=cik, as_of=date(2026,10,12), ladder=ladder)`
and `engine.capital_need.assemble_capital_need(ladder, cash, as_of=date(2026,10,12))`.
Propagate the retained facts.fetched_at to both engine blocks, as the existing
stock-library producer does. The engine bytes used matched protected source.

Actual results: both capital-need states complete; AAPL FY2025 accession
0000320193-25-000079 has OCF111.482B minus equipment spending12.715B = FCF98.767B.
MU FY2025 accession0000723125-25-000028 has OCF17.525B minus equipment spending
15.857B = FCF1.668B. Values are USD and retain their separate fiscal periods and
cache acquisition dates. The canonical stock-page disclosure agrees.

These retained annual, consolidated issuer figures are useful historical context,
not proof of current U.S. project execution, fulfillment of multiyear pledges,
or the latest available filing. The engine's stale=false uses its 550-day rule;
it does not establish those stronger claims. Two FCF calculations do not supply
five independent relevant Press receipts. No public-article rights receipt,
fact-pool admission, new candidate draft or freshness upgrade is inferred.
