---
workstream: WS:PROPHET-US-AVAILABILITY
session: claude/prophet-us-current-close-collector-20260916
model: sol
ended_because: ci_handoff
mission: >
  Recover actual completed-session US breadth prices so the existing alpha and
  Prophet producers can advance; reject successful but price-empty responses
  without weakening trade, source, calendar, retry or publication authority.
state_before: >
  The natural Sep-15 collector wrote dated but price-empty rows and reported
  success. Its engine remained on Sep-14 alpha/board; the public page remained
  on Sep-11. Existing reader, source-clock and HK publication repairs do not
  repair this newly demonstrated collector response-validation gap.
changed:
  - path: collectors/breadth.py
    what: >
      Capture one existing NYSE completed-session reference for the three US
      S&P breadth fetches; validate actual finite positive closes within the
      existing retry budget and before persistence after seam repair.
  - path: tests/test_us_breadth_completed_close.py
    what: >
      Test real fetch and health consumers for retry, exhaustion preservation,
      null/invalid/future/missing-field data, calendar isolation and partial coverage.
  - path: .github/ci/legacy-jobs.yml
    what: Register the hermetic collector suite in the existing gate-code executor.
verified:
  - claim: The repaired collector preserves partial-data and other-market contracts.
    command: python -m pytest -q tests/test_us_breadth_completed_close.py tests/test_breadth_split_seam.py tests/test_russell_breadth.py tests/test_universe_split_seam.py
    result: 56 passed; expected deprecation warnings remain outside this repair.
  - claim: The current collector can recover real missing-session data for the real alpha consumer.
    command: python -c "import json; r=json.load(open('research/us_prophet_availability/2026-09-16-completed-close/live-source-receipt.json')); print(r['source_head'], r['alpha'])"
    result: >
      Source 2ecf3db94d131cf8c59fe685ce7d1aca2e3509c2; current closes
      500/503, 599/602 and 400/400; real alpha Sep-15, 1460 names and 11 sectors.
      Isolated real-provider proof, not publication or production acceptance.
unverified:
  - claim: The integrated repair is deployed and visible on the actual US Prophet board.
    what_would_verify: >
      Concluded exact-head CI/security and independent review; accepted merge;
      real completed-session collection and source-bound board publication;
      served browser and premium-payload dates/counts/hash reconciliation.
unresolved:
  - Existing Linux CI queues and current heads/reviews must be reconciled, not bypassed.
  - The natural nightly 35041133038 must settle before any additional recovery dispatch.
  - Existing PRs 7180, 7187 and 7163 retain their independent writers and integration boundaries.
next_actions:
  - >
    Review and release this same collector carrier, integrate existing repaired
    sources, reconcile the natural nightly, then run the existing canonical
    producer/publication path and verify the live US board and next scheduled update.
do_not_redo:
  - Do not recreate the existing availability workstream or source-clock/reader/HK repairs.
  - Do not loosen mixed-vintage, chronology, ranking or publication guards to produce picks.
  - Do not mutate a running worker checkout or duplicate the active nightly.
danger_areas:
  - Date and volume presence are not completed close-price validity.
  - Regional calendars and Russell partial-cache semantics must remain separate.
  - An isolated alpha proof cannot establish full-stock-universe, plan or production freshness.
prs: [7180, 7187, 7163]
discoveries: [DSC:US-BREADTH-DATED-ROWS-CAN-HAVE-NO-COMPLETED-CLOSES]
---

Current live Chairman direction supplies the recovery scope. Protected procedure is Mastermind `0fe8074ff953b2ced9025ed40f0f66019c759967`. Executive OS owns lifecycle; Agent OS owns continuity; GitHub owns source/evidence; Slack is transport. This is direct bounded source work, not an unadmitted worker or a new runtime operation.

Before modifying this branch, re-read its remote head and current activity. PR #7187 had a separate active incumbent editing the former session checkout; that checkout was left untouched. The three approved Linux CI runners were back online during this continuation, so old offline claims are historical, not the present blocker. Capability is BUILT_NOT_PROVEN.

## 2026-09-16 cross-session coexistence boundary

Chairman explicitly requested duplicate-work assessment and complementary lanes. Protected procedure was re-pinned to `Mastermind@8ba7deedde164c90298d3e88785d98e02fa5e2d2`; all required skill bodies were fetched and confirmed unchanged from the previously read pin. Canonical Macro main at the coordination read was `e729d0fd9d48868b49a1911d4098c689b3d373bd`.

Retain this session on #7200 (breadth input validity). The other published recovery is #7206 / `sol/prophet-deep-stock-current-close-20260916`, head `6159410678619d148531ba3e2ecbb1ad7a537d04`; it owns preferred deep-stock histories and names Russell as its next dependency. Do not duplicate its Russell repair or edit `collectors/sector_holdings.py`. Only the CI manifest directly overlaps these two published repairs. #7060 additionally overlaps this collector file, so no cross-branch wholesale replacement is safe.

New self-review repair: Boolean True was counted as a valid price. Five new checks failed before the local correction; 65 total tests now pass. The exact old provider-input file hashes remain intact and revalidation accepts the same observed valid-price counts. No provider request or production mutation was made for this correction. The peer has an independently reproduced NumPy-bool gap; give its owner the specific repair, not a replacement implementation. The evidence README and `boolean-validation-compatibility.json` contain the exact boundary.

The existing #7187 maintainer has local head `0a076cedd8094e5425e782aca976820e93ed6e8e` while the observed remote still has `c21c9be04bbf983bc22f8e3fe6075339bbc9ebef`; leave that worktree untouched. #7163 is subject to the existing #7018-first ruling and a one-line HK byte-pin repair. These remain distinct owners, not additional assignments to this session.

One acknowledged session must own the eventual combined production build/publish; Until that responsibility is confirmed, this session performs source verification only and issues no duplicate nightly/rescue/deploy. Sending a coordination packet is not acknowledgment or writer release. The unnamed peer chat's provider-session identity remains unverified; use exact PR/branch identity in the forwarded handoff.

## Partial-coverage publication follow-through

The next actual fetch/store check found the invalid minority could survive an otherwise valid 80% batch and reach the stored Close matrix. The source now shares exact-session validity between count and mask, masking invalid current cells before seam analysis and after seam repair before persistence. Existing history, valid numeric one, 80% breadth availability, regional/Russell interfaces and peer source custody remain unchanged. Seven regressions were red before repair; 74 tests are now green; removal of either masking boundary is detected separately.

New evidence file: `research/us_prophet_availability/2026-09-16-completed-close/partial-price-publication-replay.json`. The recorded-matrix reconstruction is non-production and made no provider calls. Actual fetch/store health and current price values were recovered under the repaired source. Per-name and sector alpha values match, but a strict ordered-alpha assertion failed for two reordered top-list members; do not call it byte-identical, raw-provider-response, or full-board proof. No alpha-ranking rule was changed.

Continue exact-head independent review and current-base compatibility on #7200, consume the peer's response on #7206, and preserve one-owner publication. There is still no peer ACK proving ownership agreement. Do not duplicate its Russell/full-library work or retry the unresolved natural nightly without canonical reconciliation.


## Same-session cache finality follow-through

At exact preimage `e3c87afae3e42e79f615d3219092c8869305d4e6`, a new RED planted a finite value in the existing cache on the expected completed session, then returned four fresh valid closes and one missing fresh close. The 80% response passed and `fresh.combine_first(cached)` repopulated the omitted name with cached `102.0`, proving that same-date cache bytes could impersonate settlement.

The same carrier now masks the expected-session cache cells for requested US names before the historical merge. Only fresh response bytes may populate that row; prior rows and regional/Russell interfaces are untouched. The focused RED failed for the intended reason; the repaired four-suite run is `75 passed, 31 warnings in 19.12s`. Evidence is `research/us_prophet_availability/2026-09-16-completed-close/same-session-cache-quarantine-receipt.json`. No provider, production store, workflow, ranking, runner or publication effect occurred.

The release boundary is unchanged: exact-head CI/security, independent review, current-base composition, accepted merge and real source-to-browser proof remain required. Do not duplicate #7206 or the separately owned CI-host work.


## CI-manifest composition follow-through

A current-head pairwise composition of #7200 and the separately owned #7206 returned a single conflict in `.github/ci/legacy-jobs.yml`. The implementations and tests are disjoint; both carriers had independently appended their job at EOF. The unchanged `us-breadth-completed-close` job is now positioned beside the existing breadth collector owner, with the file restored to one terminal newline. A fresh three-way merge returns zero, retains both `us-breadth-completed-close` and `us-deep-stock-completed-close`, parses as 216 jobs, and passes `run_ci_pack.py --validate-only` over the 142 legacy jobs. Receipt: `research/us_prophet_availability/2026-09-16-completed-close/ci-manifest-composition-receipt.json`.

This is an integration-layout repair only. #7206 source, branch, review and Russell/deep-stock ownership were not modified. Exact committed-head merge-tree, CI/security and independent review remain open.


## Same-session OHLCV-extra finality follow-through

The same finality defect applied to the accepted response's companion fields. At exact preimage `7355c03b6ba8919ed52f0147861777051cc64c29`, fresh valid closes with one missing fresh High, Low, or Volume value still allowed the later extras-cache merge to restore a finite same-date intraday cache value. Three RED cases reproduced the leak. Cached extras now pass through the same expected-session quarantine before merge for the three US groups. Fresh history still wins normally; only same-session cache substitution is refused. Focused GREEN is 3 passed and the owner battery is `78 passed, 34 warnings in 18.68s`. Receipt: `research/us_prophet_availability/2026-09-16-completed-close/same-session-extra-cache-quarantine-receipt.json`.

No ranking, provider, retry, market-calendar, regional, Russell, workflow-dispatch, runner, or production behavior changed. Exact-head CI/security, independent review, merge/current-base integration, and full source-to-browser production proof remain required.


## Same-response OHLCV coherence follow-through

A partial batch may lawfully pass the existing 80% close floor while one name has no completed close. At exact preimage `1a64c60bd64c41568cb51bb69fe5093630094fe2`, that same accepted response still persisted the missing-close name's current-session High, Low, and Volume. The repaired source masks expected-session companion fields for exactly the names whose Close is absent or invalid before the attempt becomes accepted. Focused GREEN is 1 passed and the owner battery is `79 passed, 35 warnings in 34.48s`. Receipt: `research/us_prophet_availability/2026-09-16-completed-close/same-response-ohlcv-coherence-receipt.json`.

This preserves valid partial coverage, prior history, other names, regional calendars, Russell, retries and ranking. Exact-head CI/security, independent review, merge/current-base integration and real source-to-browser production proof remain open.


## Independent review repair — whole-field omission

Independent verification comment `5696266993` correctly distinguished a missing cell from an omitted field. On preimage `664add61942e8cf7c678705ee5d6c60ee90e1ce6`, a whole omitted High/Low/Volume field never entered `_last_extras`, so its existing cache file retained the old current-session row. The same carrier now includes each existing US extras cache in persistence even when its fresh field is absent, then applies the requested-universe expected-session quarantine. Three REDs failed; the missing-field plus missing-cell controls are `6 passed`, and the owner battery is `82 passed, 38 warnings in 4.21s`. Receipt: `research/us_prophet_availability/2026-09-16-completed-close/whole-field-extra-omission-receipt.json`.

The verifier retains re-review authority. Exact-head CI/security, accepted independent review, current-base integration, merge and full source-to-browser production proof remain required.

## 2026-09-17 split-repair coherence correction

Current Chairman continuation resumed this original direct operation after the source remained local/remote `f6d1b8632aa353c213b1f39cda63a38d30949e79`, clean and without active source/Git operations. No child assignment or separate writer transfer was invented. Procedure: Mastermind `aacf3df5a47ca37ce71cd47a3bd7caea81ad4cd2`. Same-carrier continuation marker: #7200 comment 5720226883.

The native returned seam failures are now corrected in semantic commit `196e0731b30d6b8c303302eff98954e32079856c`: retain the one captured session for the existing repair download; refuse incoherent replacement companions before all cache writes; reseal final completed Close/High/Low/Volume; retain optional returned companion fields. Normal 80% coverage and all legacy/non-US/Russell interfaces remain. Incomplete split correction is explicitly failed with previous cache bytes preserved, not published as partially corrected success.

Proof packet: `research/us_prophet_availability/2026-09-16-completed-close/seam-repair/`. Initial new tests 16 failed/3 passed; final native 105 passed; three forbidden mutations caught; integrated geometry/clock tree 467 passed across ten suites, no source changes. Recorded real-matrix replay preserves 500/599/400 current prices and exact current companion values without provider calls or changes to the 18 original proof files. This is not a new live-provider or full-board run.

The old source green CI and author-side COMMENTED review do not accept this new head. Keep release held for fresh semantic review, current checks and real publication proof. Reuse the current independent-review placement and MastermindX1 request rather than self-approve or duplicate it. Do not edit #7206, recalculate archived full-library proofs, or dispatch a duplicate rescue. Next action: consume this new exact-head review/CI, integrate with the other accepted source repairs under one publication owner, then verify the actual new-session candidate/plan/history and authorized browser/payload journey.
