---
workstream: WS:RATES-INFLATION-COMMAND
session: claude/event-intelligence-auction-20260917-sol
model: sol
ended_because: blocked
mission: Advance living Event Intelligence through the existing calendar, RIC/F05 and AI owners; deliver useful event context without requiring a forecast. MarketOntology parent 6819 remains nonterminal.
state_before: The first non-forecast calendar slice was published but not released; adversarial source cases could fabricate a missing deadline or split one disputed auction into apparently verified events.
changed:
- path: engine/event_calendar.py
  what: Withhold missing official deadlines, reconcile by validated CUSIP plus auction date independently of disputed family/reopening/tenor, clear conflicting terms and interpretations, and degrade malformed feed roots locally.
- path: tests/test_calendar_event_context.py
  what: Add 28 adversarial regressions to the already-enrolled suite, preserving all earlier cases.
- path: research/event_intelligence/auction_context_v1/verify_repair_consumer.py
  what: Preserve a bounded exact-source producer-to-renderer check for disputed terms, valid neighbors and absent deadlines; synthetic adversarial inputs only.
verified:
- claim: The 28 added cases distinguish the original defects from the repair.
  command: python -m pytest tests/test_auction_review_regressions.py -q
  result: In the isolated review harness, original source produced 24 failures and 4 passes; the repaired source produced 28 passes. The same 28 regressions are appended in tests/test_calendar_event_context.py on this branch.
- claim: The combined published producer tests pass in an isolated configuration harness.
  command: PYTHONPATH=. python -m pytest tests/test_calendar_event_context.py -q -k 'not captured_official_api' -p no:cacheprovider
  result: 47 passed, 1 deliberately deselected because the official capture fixture was not materialized in this sandbox. Configuration/network seams were isolated; this is not full-repository or production proof.
- claim: Reconciled producer values reach the existing renderer without stale verified claims.
  command: python research/event_intelligence/auction_context_v1/verify_repair_consumer.py
  result: The identical producer/renderer source blobs passed 36 synthetic producer-consumer executions in the sandbox proof. The portable command preserves those assertions and exact blob pins; no browser or host runtime was used.
- claim: The source repair was published on the same existing branch.
  command: Native GitHub update_file receipts and get_pr_info for macro pull request 7273.
  result: Tests commit d26fa6e2db685d78c37a58949a9808b03fa6d910, repair commit 1caee1d8edf70c210f55720568eb282277d320d3; branch readback confirmed the repair. Later evidence/continuity commits do not change product semantics.
unverified:
- claim: Current-head full CI, independent review and authenticated production acceptance.
  what_would_verify: Concluded exact-current-head checks, an eligible non-author review, governed merge and existing render/deploy followed by authenticated browser proof. Earlier 94-test and 8-browser receipts are historical after the semantic repair.
- claim: Live per-event LLM assessment, official auction results and full calendar/history are implemented.
  what_would_verify: Complete existing-owner producer-to-consumer verticals with source/correction versions, admitted AI inference and real daily workflow proof; reference guides are not those capabilities.
unresolved:
- Host execution was refused by the platform in this continuation; it was not retried or routed through another host. Native GitHub and isolated sandbox review remained available.
- No eligible independent reviewer admission or START was established. Executive connector discovery found no current tool. A bounded Slack placement search found another current review lane still waiting on placement; it is not an assignment for this operation.
- The last detailed former-head CI read had all twelve executor packs queued, not running. Read current-head results; do not infer execution from a running workflow wrapper or from old receipts.
- The legacy local worktree is behind native GitHub commits. Reconcile and fast-forward the same branch before any later host push; never reset, force or overwrite the newer remote repair.
- Upcoming Treasury API changes are officially documented but their exact rollout date is not established. Current compatibility is legacy-schema only; do not claim new-schema support or assume a cutover date.
next_actions:
- Read current PR 7273 head and checks, then the source/review addendum below. Keep Draft and HOLD-FOR-SOL; no automatic merge.
- Obtain eligible exact-head independent review and full verification through the existing owners. Refresh browser/source evidence for changed conflict and missing-deadline states; do not count earlier screenshots as current semantic proof.
- After release gates clear, complete the existing production render and authenticated live readback. No scope reauthorization is needed from Chairman.
- Extend the calendar-owned read projection into existing AI grounding, then implement official result/correction intelligence under the method and source-version constraints below. Preserve the full calendar/history, regime, monitoring and learning mission.
do_not_redo:
- Preserve the implemented calendar context, Chronicle/F05, MarketOntology parent, provider routing and private-state owners. Do not create duplicates.
- Preserve this branch and PR; historical RIC-F1 and incumbent 7241/7036/7230 are not replacement targets.
- Do not restore the 13:00 fallback for absent official auction deadlines, or use disputed classifications in canonical auction identity.
- Do not repeat unchanged host/refused-path probes, blindly retry effects, rerun shared CI, or repair shared runner infrastructure in this program.
- Do not publish September production from the rejected June cached view-model.
danger_areas:
- Announcement reference context is not a live outcome assessment. No calibrated forecast, when-issued quote, rank, size or trade authority is added.
- CUSIP alone is not an auction identity; auction date remains necessary. Announced-as identifiers on unscheduled reopenings need an official relationship, not a guessed join.
- Indirect bidder classification does not establish foreign domicile. Published auction subtotals and competitive award denominators must not be replaced by grand totals.
- Old hosted/browser results remain evidence of the old revision, not permission to release a changed source.
prs:
- 7273
---

# Event Intelligence continuation — source integrity and analytical method

## Mission and carrier

Chairman authorizes continued end-to-end leadership without repeated confirmations.
The full target remains a living calendar, deterministic event-family intelligence,
grounded LLM assessment, shared AI context, exposures, monitoring and learning.
This is a bounded source-integrity advance, not acceptance of that parent mission.

Protected procedure: Mastermind `320f586126b7c82c843ef17612f12d40d20a42e0`, Skillpack 1.0.1.
Original implementation: `46c51b36607c331b0f49794c1e7caa4724fbbc6c`.
Current product semantic revision: `1caee1d8edf70c210f55720568eb282277d320d3`.
Original source base: `60db17a8e6e59381f0648f110035b1cc513da638`.
One carrier: `claude/event-intelligence-auction-20260917-sol`, Macro PR #7273.
Review operation: `event-intelligence-auction-context-review-20260918-sol-001`.
Author/owner review receipt: PR comment `5723479197`; not independent review.
Parent: #6819, architecture comment `5722262696`, prior implementation comment `5722914083`.

## Exact source and proof boundary

Original event-calendar blob: `a66baf1f89d40b8606452a08768a2f333b18bbc6`.
Repaired event-calendar blob: `ff60c892a41138e07a8e77b318ae50137993c1ef`.
Unchanged context projection blob: `db1d08adb36e81418b8f9137114e89af488eafa1`.
Unchanged renderer blob: `9e144245006f24679f50b37fb2ea98c6540f97a8`.
Published producer-test blob: `be4ad83df058d2e98127297a7d92adb2e8c65795`.
Sandbox copies matched these Git blob hashes, not merely pasted approximations.

The earlier 94-test, 8-interaction and 8-theme-capture results remain retained in
`research/event_intelligence/auction_context_v1/` and
`mockups/evidence/event-intelligence-auction-20260917/`. They predate the semantic
repair and are not described as refreshed. New proof comprises the RED/GREEN
adversarial cases, 47 passing isolated producer cases and 36 producer/renderer
executions. No provider, host execution, live collection or production deployment
occurred in this continuation. No synthetic record was written to product data.

The new conflict handling latches disagreement across duplicate ordering, clears
the disputed headline and family-specific summary with the facts, and preserves
valid neighboring events. Missing official time is blank in the calendar as well
as unavailable in the dossier. Non-list feed responses return no auction rows and
log a local diagnostic instead of taking out adjacent calendar functionality.

## Qualified next-result analysis, not yet an implemented producer

The research lane tested several attractive-looking but incorrect interpretations
against primary Treasury documents. These constraints belong in the next result
vertical and its evaluations before an LLM is allowed to narrate the numbers.

**Bid-to-cover.** Treasury's historical May 21, 2025 20-year result uses
39,388,371,800 / 16,000,014,900 = 2.4617709449758, displayed as 2.46. Using the
SOMA-inclusive grand totals instead gives 2.2857499904991, or 2.29: an incorrect
substitution. Reproduce the source's named subtotal and compare to its reported
ratio. Do not generalize a subtraction rule across unqualified schema generations.

**Participation.** In that example competitive awards of 15,784,555,100 partition
into dealer 2,669,255,000, direct 2,221,300,000 and indirect 10,894,000,100.
Their competitive-award shares are approximately 16.9105%, 14.0726%, and 69.0168%.
This is arithmetic, not a demand grade. Treasury explicitly states that both direct
and indirect categories contain domestic and foreign bidders. Actual foreign
participation requires the separately released investor-class allotment source.
Its availability clock must not be backfilled into an auction-time assessment.

**Tail and instrument semantics.** Stop minus the reported median in that example
is 7.3 basis points; it is NOT a when-issued tail. Without the matched security,
auction deadline, quote timestamp and appropriate instrument measure, tail remains
unavailable. FRNs bid on discount margin; nominal notes/bonds and TIPS bid on yield.
Do not compare an FRN measure to a nominal yield or call a TIPS real yield nominal.
One historical arithmetic reproduction validates none of the proposed market-effect
models, regime thresholds or trade decisions.

**Source-version risk.** Treasury's amended August 21, 2026 specification announces
renamed API fields and changed XML; it gives no finalized implementation date.
The table maps `auctionDate` to `CompetitiveAuctionCloseDate`,
`closingTimeCompetitive` to `CompetitiveAuctionCloseTime`, `cusip` to `CUSIP`, and
`tips` to `InflationProtected`. It splits totals by inside/outside offering amount
and describes announced-as fields for unscheduled reopenings. Required response:
version-aware qualification, retained raw evidence, explicit mismatch reporting
and contract tests from real new-schema responses when available. Do not silently
use the old schema, case-insensitive guesses or old subtotal assumptions.

Primary references (PDF tables were visually inspected):
- Auction result, page 1 and footnote 4: https://www.treasurydirect.gov/instit/annceresult/press/preanre/2025/R_20250521_2.pdf
- Auction definitions and bidder domicile: https://www.treasurydirect.gov/help-center/faqs/auction-faqs/
- Investor-class source and separate release schedule: https://home.treasury.gov/data/investor-class-auction-allotments
- Amended specification, API crosswalk pages 7-8: https://www.treasurydirect.gov/files/auction/auction-file-%26-api-specification-changes.pdf

## Existing-owner integration order

`engine/neuralweb/market_packet.py` currently consumes published market/rates
artifacts but not these dossiers. `scripts/build_site.py` around 6021-6042 builds
the calendar for the template and imminent brief line only. The next join is a
bounded versioned READ PROJECTION from this calendar owner into the existing
publication/AI context path, not a second event database or collector in chat.
The AI reader must not collect data or invoke providers while building its packet.

Before result implementation, reconcile existing RIC-F1/source-publication custody;
#7241 release recovery, #7036 diagnostic semantics and #7230 research persistence
remain separate. A source correction must invalidate dependent interpretations;
retain announcement/result/observed/assessment clocks and the actual snapshot
identity. Facts, deterministic calculations, forecasts and model interpretations
remain distinguishable. Missing prices are not unpriced alpha. Historical analogs
need independent episodes, point-in-time inputs and outcomes, not article counts.

Release remains held on actual verification and reviewer/production capabilities,
not on a request for Chairman to restate intent. Shared CI capacity stays with its
current owner; queued packs are never described as executing work.
