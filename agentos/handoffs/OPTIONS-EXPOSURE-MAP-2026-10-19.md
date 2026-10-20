---
workstream: WS:ADVANCED-DATA-OPTIONS
session: 01a156f1-f450-7793-8951-bddadd4784c2
model: codex
ended_because: ci_handoff
mission: Deliver the Options Exposure Map through Release A, then admitted B/C mechanics and research gates.
prs: [9815, 9868, 9874]
state_before: The initial Options build was rejected for inadequate product quality and competitor parity; the full handoff remained assigned.
changed:
  - path: collectors/thetadata.py
    what: Add an explicit one-GET full-observed-root capture profile while preserving selected-capture limits and defaults.
  - path: engine/options_exposure_projection.py
    what: Add source-bound joint projection and explicitly dated Gamma qualification.
  - path: scripts/build_options_hub_nightly.py
    what: Compose bounded captured inputs through the existing builder while preserving legacy inputs and publication guards.
  - path: .github/ci/legacy-jobs.yml
    what: Keep affected Options tests owned by the existing flow-surface CI lane.
verified:
  - command: Affected exposure, receipt, dated identity, reference-page, Hub, Theta and daily-owner tests
    result: 560 passed; 253 targeted checks passed after malformed-link/metadata repairs; 9 focused daily opt-in cases passed after call-path additions.
  - command: python3 -m pytest tests/test_options_dated_projection.py tests/test_options_source_receipts.py tests/test_thetadata.py -q
    result: 155 passed, including a 14000-row multi-expiry capture and refusal/byte/row controls.
  - command: python3 -m pytest tests/test_options_source_receipts.py tests/test_options_contract_identity.py tests/test_options_dated_projection.py -q
    result: 83 passed after indexing full-book term composition, including 3000 exact term merges and duplicate refusal.
  - command: python3 -m pytest tests/test_options_observed_qqq.py tests/test_repair_gex_history.py -q
    result: 17 QQQ adversarial cases and11 archive cases passed; actual full SPY archive repair also verified offline.
  - command: python3 scripts/audit_unrun_tests.py
    result: Exit 0 after the current-main integration; no newly unwired suite.
  - command: curated_exclusive_closure_findings(Path('.github/ci/legacy-jobs.yml'))
    result: No uncovered flow-surface dependency after the merge.
  - command: TERMINAL_E2E_PORT=3193 npm run test:e2e:responsive -- e2e/options-exposure-workspace.spec.ts --workers=1
    result: All six EN/ZH desktop, tablet and mobile workspace journeys passed after the copy-layer repair.
unresolved:
  - Full actual QQQ source qualification and rights-held native publication; canonical QQQ intake merged, Hub install remains on its original fetch.
  - Protected Terminal release, production deployment and authenticated product acceptance.
unverified:
  - Full QQQ qualification and authenticated production rendering; actual full SPY dated source and local browser proof now pass.
  - Release B nonlinear and Release C empirical/PIT acceptance.
danger_areas:
  - Do not replace a last-good full book with the 20-contract canary or weaken its empty-book guard.
  - Preserve exact source/Fabric operation identities, rights, held carriers and the Chrome extension UI consent boundary.
next_actions:
  - Integrate the matched captured source pair through the incumbent nightly publisher, then verify qualified native API output.
  - Complete exact-head protected CI, merge, git-gated deployment and authenticated product verification.
do_not_redo:
  - Preserve Macro 8555 and 7328 HOLD, IW2 T03k refusal, Save admission and recovered negative QQQ/calibration evidence.
  - Keep original Fabric identities, failed operations and the stopped M2 acquisition distinct; no replay or new truth store.
---


# Current Options source checkpoint — October20,2026

Original root `01a156f1-f450-7793-8951-bddadd4784c2`; source coordinator
`01a15700-1ae2-7a73-9756-f1546da7ace8`. Root owns Terminal/release acceptance.
Evidence directory: `/Volumes/Mastermind/evidence/options-exposure-01a156f1`.

**Protected source:** Macro9815 merged at `5c2d0a04afd19642d2dab483885d46c73b7baed4`
after exact CI39408959806 succeeded. Canonical QQQ intake9868 merged at
`e474e63180871fcb55ccc2660f509f336689b9b3` after parent accepted exact
`f8d4c37a3294a3f4a242abe649b7072db56145af` and CI39415142541 passed all12packs/gate.
The inactive pilot authority context is irrelevant to the active main gate.
QQQ tuple is `SEC:US-XNAS-QQQ` / `US-XNAS-QQQ`, normalized NASDAQ ETF listing,
effective October20, ingested11:13:21UTC, source known10:26:04.581160UTC. No issuer
grouping, historical extension, root alias or lost-row fence was invented. CENT/CENTA
changes apply their existing ratification; CECO/IBOC retain six lost immutable members.
Parent review: `QQQ-parent-identity-review.md`.

**Current producer increment:** fresh helper-created branch/worktree
`options-qqq-observed-producer-20261020-3ae19975dd79ea4c` extends observed identity v2
to that exact QQQ target, preserving v1 and compact tuple fields. QQQ sessions before
October20 refuse, actual master/listing/read clocks remain required. Explicit
`occ_standard_qqq_etf/v1` interprets only verified ordinary100-share American reference
terms and retains raw omission/citations. Synthetic actual-producer pair
`synthetic-producer-QQQ-observed-identity-v2-120contracts.json` and
`synthetic-native-QQQ-observed-identity-v2-envelope.json` has119qualified/1missing,
120observed/60cells/3expiries, rights null; this is not actual QQQ market capture.
Fabric test leaf `oem-01a156f1-qqq-observed-test-leaf-v1`, original controller74629,
settled on its original carrier; exact stdout/artifact were consumed, reviewed, repaired
and accepted as test assistance.17 cases pass;328 affected source/native/archive cases pass in total. Original fixture date/raw venue and an
API-missing skip were corrected; this is not independent production review. See
`qqq-observed-test-leaf-adjudication.md`.

**Release A accepted evidence:** actual October16 SPY full source acquired October20
through the incumbent version1 Greek/OI wrapper:13104observed,12212Gamma-qualified,
892missing (654degenerateIV/238missingOI),33expiries/6552cells/491strikes,
251fully-qualified strike aggregates. Whole net/gross remain null; covered
net−20.42010111776526B/gross47.779712252337456B, provisional leader765, dated
underlying763.25USD. Parent independently verified arithmetic and six EN/ZH responsive
browser views; fixtures supplied price bars/auth, so this is not authenticated production.
Native full import/builder witness has3994690JSONbytes; ordinary writer/store/Hub
composition preserves all rows. See `actual-full-source-native-import-verification.json`
and `actual-full-source-consumer-pairing.json`.

**Archive engineering:** existing `repair_gex_history` now accepts an explicit full
native context/date, preserves projection and covered amounts, rejects selected-window
substitution/digest mismatch, and applies the whole8MiB event budget. It updates only
dated archive keys and a LIST-derived index with zero unrelated heal budget. Actual
SPY dry-run plus isolated evidence-copy application retained12212/892 and6552cells;
`archive-only-projection-repair-verification.json`. A real repair bug was fixed:
stringifying expirations before digest validation invalidated the native input identity.
No production store/archive/current book has been written or published.

**Runtime custody:** original protected Hub install remains Python79654→git79656→SSH79657
on M1. Its original native handle20079 was pruned by tool refresh; no replacement install
was launched. As of12:52UTC the same operation has a41.5GB received pack; child80584 is processing it at86%CPU, HEAD remains
201064395fff8e16e958619bf1343eea6d7aca9c and no runtime backup/install receipt exists
because no checkout write has begun. Retained receipt path is
`~/optionshub-ops-wt/.git/options-source-install-5c2d0a04-v1/receipt.json`.
Theta scoped dirty-source composition script is prepared but unexecuted; default-off
version selection is not enabled. Preserve incumbent dirty baseline-refresh edits,
wrappers/data/symlinks/writer locks. No service restart or provider GET for installation.

**Actual source/rights gates:** original October19 full Greek request is EFFECT_UNKNOWN,
no raw return/settled effect, no replay. October16 reference first-page cap was a known
local failure; reconciliation reused the same original budget and charged a repeated
settled first page:15aggregateGET/14104rows/3226397B, not an unknown-effect retry.
Both old retained-only SPY/QQQ negative books remain unqualified for missing acquisition
version evidence. QQQ's new October20 canonical identity cannot qualify those October16
or October19 archives. Next actual QQQ EOD source must be October20 or later and truly
available; no current-market capture is claimed by the synthetic fixture.

Theta signed distribution terms remain unfiled. Exact connected-mail search found only
unsent DRAFT1a13ddd5759e45e7, no provider agreement/response. Root has asked the one precise
signed-terms location question; no provider message was sent. Massive provisioned
reference read succeeds, but its retained stock-scope agreement is not proof of option
redistribution permission. Rights remain null. Publication-only hold remains; code,
negative tests and protected installation continue independently. Fresh-read served
session before any later publication; never replace newer latest boards with Oct16 or
the20-contract canary. API target after lawful publication is native `/api/hub/gex/SPY`
and entitled Terminal current/archive flow routes.

**Release B/C remain open:** dated Gamma never gains instantaneous/next-live/joint/
repricing/PIT capabilities. Retain explicit requested_version1: methodology and current EOD
endpoint docs conflict for omitted-version whole-day versus latest/min1h semantics;
Vanna/Charm output units and elapsed-time sign remain unproved. Existing owners are
`engine/options_american_exercise.py` (research-only converged/interval American finite
 differences), `engine/intraday_greeks.py`, and `engine/options_scenario_surface.py`;
no parallel Greek engine. Model-aware bid/ask/IV, complete declared dividends and explicit
calendar/economic-expiry policy must compose before nonlinear exposure. Current Cboe
pages distinguish expiring ETF16:15trading from16:00underlying reference close; do not
invent16:00 economic expiry or backdate current rules. See
`expiry-clock-source-boundary.md`. Retrospective September21 price-analogue calibration
is not prespecified exposure-node/PIT validation; its negative proper-interval-score
result stays scoped to that study.

**Terminal root custody:** #1083 refreshed protected base to
`9068d579c7a3925c65dd1b2632f990ac55c0b907` (Exposure blobs unchanged), exact CI39423133774
on verified observer7825/log `terminal-ci-9068d579-observer.log`. Prior ffa78f9
CI39415488127 ALLPASSED and recovered71462 was consumed exit0, not live.
#1091 is `84b00c720e802ec47600b1a17e519166be33d965`, exact CI39423505973 on verified11971/log
`terminal-1091-ci-84b00c72-observer.log`. Root owns both consumption and deployment.
QQQ consumer Fabric result was accepted after70 focused tests/TypeScript and six EN/ZH
responsive map→sameQQQbook chart journeys;96 affected captures,11locks and build pass.
Actual native SPY archive also passed six EN/ZH chart-link journeys with fixture auth/prices.
Preserve authenticated Chrome extension consent and publication rights holds; no live proof.

**Snapshot engineering frontier:** local follow-up on protected-base plus9874 retains exact
regular first/second/OI acquisition endpoint, actual parameters, response hash and capture
clock. Explicit1/latest requested calculation policy is separate from actual serving build,
which stays null; omitted version/tenor stays unknown. Exact contract+snapshot_ts joins retain
separately named secondary source metadata; no-match stays null. EOD dated guards are unchanged.
Original test leaf50372 returned on its same carrier; accepted after principal fixture repairs,
337 affected collector/receipt/poller/dated cases pass after owner reconciliation;25 snapshot cases include byte-cap and malformed-proof negatives. `snapshot-receipt-tests-adjudication.md` records limits.
Original8684 owner released87cc03d54b9cab4d76d4f932fc33114311d87ed7 (parent59e5508f),
494 affected cases pass. Fresh-inspected exact source and reused its snapshot raw-clock
retention; our distinct addition retains acquisition receipts and exact secondary joins.
No duplicate history append repair or broader8684/CI shard change was copied; original
held merge/install custody remains. Frozen original patch is retained. No live GET, host installation, new service/poller or numerical qualification.

**Review/source release:** #9874 exact00668db passed all12packs/ci-gate/contract-delta/active
main authority and fences; original observer77735 consumed exit0, PR ready/mergeable. Inactive
pilot authority is separate. Full-observed binding assessment is original Fabric
`oem-01a156f1-full-observed-producer-review-v1`, MiniMax/ubuntu0, verified native22838; pending
adjudication, not independent acceptance. Older selected producer/identity returns remain
unaccepted and do not cover full-observed v2. Root owns accepted QQQ canonical intake review.

Preserve original HOLDs #7327/#8555/#7328, #8684 custody, IW2T03k refusal, Save admission,
Oct15SPY seal, original source/Fabric effects and their exact retained carriers. No new
store, collector, engine, watcher or truth registry is authorized by this checkpoint.
