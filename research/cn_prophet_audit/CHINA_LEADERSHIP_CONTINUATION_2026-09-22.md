# China leadership and continuation — delivery checkpoint, 2026-09-22

MISSION_COMPLETE: false
CAPABILITY_STATE: BUILT_NOT_PROVEN

## Commission and outcome

The Chairman's September 22 screenshot/request concerns three separate defects: China sector/Prophet intelligence coverage, meaningful US-to-China evidence, and premature removal of still-buyable leaders from Buy Now merely because their initial bottoming/clean-entry signal is no longer fresh. A sustained leadership opportunity must not require a new bottom to remain eligible. This is an end-to-end delivery assignment, not a research-only commission.

This checkpoint freezes the first implemented backend slice. It does **not** declare the Buy Now policy fixed, approve a semiconductor trade, establish profitable cross-market lead-lag, or claim production deployment.

Protected procedure pin: Mastermind `0e2575cbe2d77ea09812c8cd5d532332a3eb7edb`, Skillpack 1.0.1; INDEX, COLD_START, ACTIVE_EXECUTION, WEB_CEO_DELEGATION and CLOSEOUT consumed from that pin. Direct work rationale: PRINCIPAL_JUDGMENT for the cross-system semantic/custody decision, then a bounded direct implementation. No worker or autonomous watcher was started.

Macro source base: `088a8b5b99438bf57c182ac28106a7de8ddf8751`.
Carrier: `claude/china-crossmarket-context-20260922`.
Approved worktree: `/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/china-crossmarket-context-20260922`.

Carrier reconciliation: an earlier metadata-only worktree with the same local branch name was created in the different `/Users/chriswong/Documents/GitHub/macro` clone at `e0a501ef7d32a3399dea970414d0815de8530008`. Its native product-file write was denied; no product edit, commit, push or PR occurred there. It was left untouched. All implementation described here belongs to the approved Cluade-root worktree above. Do not resume or write through the abandoned preflight carrier.

## Verified diagnosis, not a blanket claim that China has no intelligence

1. `engine/theme_scoring.py` divides constructive Enter/Accumulate themes solely on `textures.clean_entry.flag`: true goes to `act_now.buy`; false goes to `act_now.add_on_pullback`. Absence of that one setup is therefore presented as a pullback requirement. Strategic attractiveness and an individual timing signal are conflated.
2. `engine/basket_score.py::clean_entry` hard-requires relative-strength percentile below 0.75 (or missing), in addition to quality and non-breaking breadth/momentum. A leader can fail because it has high relative strength. That is different from demonstrated absolute price extension. However, the real breadth and downside vetoes must not be removed merely to admit semiconductors.
3. `engine/narrative_crossmarket.py` already owns a curated, display-only crosswalk. Its pre-existing hotter-elsewhere chip is not a validated input to China ranking. A common theme label does not establish a company-level supply-chain exposure or tradable lead-lag.
4. `scripts/build_china_library.py` already calls the board-independent `china_intel_interest` composite. The repair must not feed the hub composite back into Prophet: hub inputs include Prophet membership, and `BOARD_DERIVED_TERMS_EXCLUDED` deliberately prevents that circularity.
5. `engine/china_continuation_watch.py` already measures a frozen, shadow-only stock cohort. It is not a Buy Now door and must not be silently promoted or redefined. Its board-definition, grading exclusions, and the China loser-intelligence masterplan remain controlling.
6. The displayed duplicate/contradictory cards already have an incumbent repair, #7567. Its audit found more than a display defect, including the published V4/V3 fallback and admission/coverage issues. Its historical and public snapshots are different bakes; this change does not relabel them as one current market observation.

## What this candidate implements

The canonical cross-market producer now has `compute_china_us_context`, schema `narrative_crossmarket.china_us_context.v1`. It reuses CANON; no second taxonomy, thesis ledger, score, or ranking owner is created.

It retains distinct local stance, foreign analog observations, and the clean-entry flag. A constructive stance does not disappear when that flag becomes false. Chinese avoid/trim and conflicting evidence remain explicit; opposing US analogs produce mixed evidence rather than cherry-picking the positive one. Scores from different markets are carried as source observations, never combined or compared as calibrated scores.

Each source has its own observation-session identity, exact-byte SHA-256, actual current-read clock, expected settled session, and health state. Existing NYSE/CN calendar owners determine session finalization. Stale, unsettled, non-session, missing, malformed and duplicate-identity inputs fail closed. The historical-availability flag remains false: current reads cannot be backdated into historical information sets. Same-session corrections change the content receipt without inventing a new theme identity.

The new context is actually consumed by two existing publication paths:

- `compute_crossmarket` -> `scripts/build_crossmarket` -> `site/crossmarketdata/links.json`, field `china_us_context`.
- `engine/china_intel_hub` -> `scripts/build_china_intel_hub` -> `site/china_intel/command.json`, field `us_theme_context`.

The hub attaches this context **after** its existing ranking and snapshot inputs are constructed. A historical dated hub rebuild returns an explicit unavailable state instead of importing current theme inputs. Optional producer failure leaves the China command intact. The empty/failure result cannot report healthy foreign context.

All root and theme-row `may_rank`, `may_gate`, `may_size`, `may_escalate`, and `may_trade` flags are false. The relationship is explicitly `theme_analog` with `exact_member_link=false`. This candidate does not alter stock admission, Buy Now routing, position size, ledger grading, entry expiry, thesis invalidation, or order authority. The compact `china_intel_bus` command summary and the dashboard do not yet consume the new field; those downstream integrations remain explicit next work, not inferred from a published JSON field.

## Actual validation

Initial red-first run: 22 new context cases failed because the consumer API did not exist; the five incumbent cross-market tests passed. After implementation the helper suite passed 27 tests. Additional publication/consumer cases were then added.

Final focused regression at this checkpoint: **165 passed** across the existing narrative-crossmarket, China hub command, China board-independent interest, hub visits, hub briefing, CN calendar and NYSE calendar suites. `git diff --check` passed. No new test file or shared CI manifest was introduced.

The tests include both actual builder functions writing synthetic temporary artifacts. They verify that changing US evidence changes the context while preserving a non-empty China command, its order/values, counts, discovery output and snapshot-ledger inputs. These are behavioral and serialization proofs, not live-data, browser, production, or investment-performance proofs.

Intermediate suite failures were missing sparse-checkout inputs, not waived assertions: two template fixtures and the THS membership fixture required the tracked templates and basket membership directories; five visits cases required the tracked collectors directory. Restoring those declared inputs produced the 165-pass run. The first Python environment lacked pytest; the successful runs used the existing system Python/pytest installation. No dependencies, runners or global permissions were changed.

Raw development logs stay local; the compact evidence report and final green output are the review artifacts. The production/exemplar snapshot read and one CI-manifest inspection encountered explicit platform safety-status blocks and were not retried through alternate carriers. Live-input and hosted integration proof therefore remain owed.

## Incumbent source custody and dependency boundaries

- #7567, `sol/cn-act-now-coherence-20260921`, observed head `d0561c3c3bbad86c3d8c2e89a77ca85135fefafb`: exact-identity card coherence, `engine/china_act_now.py`, template and tests. Open/Draft/HOLD, independent acceptance and full-page deployed proof still owed.
- #7669, `claude/theme-recommendation-reasons-20260921-sol`, observed head `b2e61137bcb52157be5bb9c1df5c1dd92cfc1294`: owns `engine/theme_scoring.py` and `engine/basket_score.py`. This candidate does not race those files. Explaining the present gate is not itself a continuation-admission fix.
- #6992, `claude/prophet-cn-interest-input-parity-20260908-sol-001`, observed head `a51bae222eedd4c53f4101998f3a3c4bc103f554`: raw-price/board-independent China interest repair, still held. Existing compatibility results do not establish deployed coverage.
- #7664 is the active Theme Intelligence integration consumer of released Lane C/D semantic changes; #7526's semantic repair is already merged. Do not merge #7508 independently or duplicate their theme-state, membership, entry-context, CI-owner or falsifier work.
- Existing #7064/#7095/#7210 persistence/control/multi-speed research and #7572/#7604 candidate/funnel work retain their scopes. Do not recreate those programs to avoid their evaluation gates.

Reconcile material changes to the exact affected owner/head before the next edit. A new Chairman request does not silently transfer an incumbent writer or a started effect.

## Required Buy Now / leadership policy change — not yet activated

The accepted product distinction should be strategic priority versus executable entry, not bottoming versus already-risen.

| Strategic evidence | Entry evidence | Required treatment |
| --- | --- | --- |
| Constructive, continuing leadership | A validated continuation entry remains executable | Eligible for Buy Now without a new bottoming signal; identify the route as continuation |
| Constructive, continuing leadership | Explicit overextension, failed trigger, unavailable execution or other genuine entry constraint | Keep visible as a strategic priority; disclose the exact execution constraint, not thesis deterioration |
| Constructive thesis | Timing data absent | Show entry unavailable, not an invented pullback instruction |
| Fresh hard falsifier or meaningful local deterioration | Any foreign strength | Withdraw/de-escalate according to the existing owner; US strength cannot override invalidation |
| US strength, local evidence not confirming | No local executable entry | Surface a source-bound watch hypothesis, not an automatic Chinese buy |
| Missing/stale thesis or market evidence | Any remembered label | Disclose degradation; no indefinite stale Buy Now carry-forward |

No fixed 90-day buy lock is proposed. The Chairman's three-month example establishes the need for a continuing thesis, not permission to buy any price for 90 days. Absence of a new bottom, a high relative-strength percentile, or elapsed time since the first signal must not by themselves remove a still-valid continuation opportunity. Exit/demotion hysteresis must consume distinct dated evidence; same-date corrections are not additional confirmations. Hard falsifiers must not be delayed by a cosmetic minimum-hold rule.

Use the existing Theme Thesis Ledger/ThemeState and stable identities for thesis age, horizon, evidence, review and invalidation. Do not add a parallel authoritative thesis state machine. Use the existing entry/stock eligibility owners for tradability and risk. A theme-level thesis never automatically admits every constituent.

## Remaining intelligence and validation work

The next scoring/admission proposal must connect the current owners' actual evidence rather than sum correlated labels. Evaluate equal-weight and weighted multi-horizon momentum, relative and absolute performance, breadth/confluence participation and broadening, concentration/coverage, thesis/economic evidence and available flow observations separately. Show missing dimensions as missing, not zero or silently renormalized certainty. CPU, memory and broad semis require correct membership/exposure identities; the current broad analog map is not a granular CPU or memory transmission model.

For US-to-China prediction, freeze the typed relationship and decision cutoff before testing. Distinguish common-demand beneficiaries, suppliers, substitutes and competitors; test the local confirmation required for each. Use the existing point-in-time archive and prospective record, genuine source availability, local calendars, execution constraints, costs and independent episodes. Compare local-only, US-context-only and combined candidates against the existing baseline. Do not tune on the Chairman's named winners or count repeated dates as independent successful forecasts.

Acceptance must include the motivating semiconductor/CPU/memory cases AND non-winning/control themes, sustained leaders after their first signal, truly stretched leaders, weak-breadth rallies, invalidated theses, missing data, and multi-session corrections. Measure missed-leader capture together with drawdown, turnover and false promotion. Passing implementation tests is not financial validation.

## Release and continuation

This first slice still requires immutable PR publication, exact-head hosted checks, independent review, and the normal production release/real-path proof. The present checkpoint does not satisfy those gates. No bypass, force push, signal activation or deployment occurred.

Primary next action after the backend slice is safely checkpointed: reconcile #7669 and #7567 with their existing writers, then implement the distinct continuation-entry path and truthful primary-card semantics through those existing owners. In parallel, consume this candidate's exact-head CI/review and qualify both publication paths. Resolve #6992's raw coverage proof through its owner rather than feeding board-derived hub scores back into Prophet.

DO_NOT_REDO: original card-coherence repair; frozen continuation-watch cohort; already-merged Lane A semantic fix; released Lane D integration; initial 22-case red proof; successful 165-test run on these exact code bytes. Re-run only after a material candidate/dependency change or for required independent/hosted evidence.

No autonomous wake or reciprocal worker dialogue was established. Resume in this same ChatGPT engineering session from the exact branch/PR checkpoint, not from chat-only recollection. The user explicitly permits chunked continuation; this is an implementation/consumer-test boundary, not completion of the parent mission.

## Publication gate observed after the test boundary

The command that would stage the eight explicit files and create the first commit was blocked by the platform with: `This tool call was blocked by OpenAI because we couldn't determine the safety status of the request.` A separate read-only reconciliation confirmed HEAD is still `088a8b5b99438bf57c182ac28106a7de8ddf8751`, the index is empty, and the four product/test changes plus research evidence remain saved but uncommitted. No push, new PR, hosted CI, merge or deployment was performed. The blocked source-publication operation was not retried via another tool or route.

A state-only continuation notice may be placed on incumbent #7669, whose head was re-read as `b2e61137bcb52157be5bb9c1df5c1dd92cfc1294`, OPEN/Draft. Such a notice preserves coordination and exact local digests; it does not publish source code, transfer that writer, count as independent acceptance, or bypass the blocked commit. The actual comment receipt/readback, not this proposed transport, establishes remote checkpoint persistence.

Resume first by verifying this worktree's four source/test hashes against `china_us_context_20260922/evidence.json`. Preserve the local code. Resolve the normal source-publication gate without bypassing it; then publish/review the bounded context slice and continue the continuation-admission work through the incumbent #7669/#7567 owners. No other session or automation is assumed to be working on this checkpoint.

## Current cumulative checkpoint — briefing/narrator integration, September 22 continuation

MISSION_COMPLETE: false. Capability remains BUILT_NOT_PROVEN. This section supersedes the older uncommitted/publication-block state above; older receipts remain historical evidence.

The original approved worktree and all four saved hashes were reconciled in the current Studio connection. Normal original-carrier commit and push succeeded: first published source `a449d9f1a9d152499401590db12f2922f9e6a385`, PR #7753. No rehome, force push or raw-API source replacement occurred. Current procedure pin is Mastermind `b4493b52810a43a413e381a07e1194ca905b4851` (compatible Skillpack 1.0.1).

The new code completes the previously missing machine-consumer path: published China command -> `china_intel_bus._command_block` -> structured briefing + digest -> the explicit `master_brain.gather_china_state` allowlist. A current U.S./China theme observation now survives even when there are no local stock picks. Cached observations are rechecked against both production and consumption session clocks; changed crosswalk/source identity, future clocks and authority-bearing payloads cannot become current intelligence. Source-relative performance is retained, not silently lost in projection. Qualitative state and narrator prose are reconstructed by the existing cross-market owner, not trusted from input text.

The digest distinguishes U.S. strength, Chinese confirmation/defensiveness/conflict and fresh-entry texture. Absence of the texture is not automatically a pullback requirement or thesis deterioration. The complete context remains non-ranking/non-gating/non-sizing/non-trading. No Buy Now admission policy or stock recommendation was activated.

New red-first consumer proof: eight failing cases on the absent adapter. Final focused regression: **229 passed**, including the actual command builder, briefing, narrator and their negative controls. Final output and seven exact source/test hashes are in `china_us_context_20260922/evidence.json` and `narrator-final-tests.txt`. These supersede the initial 165-test report for current source validation; they are not production or financial-performance proof.

Live verification attempt at 2026-09-23T01:18:23Z: both official basket JSON routes returned HTTP 401 Authorization Required. No credentials/cookies were extracted or invented, and no live data were substituted with fixtures. Authenticated production-path proof remains owed; the existing live access path must be used by its owner.

The attempted explicit registration of the two existing context/command suites under the existing `unrun-brain-desks` CI owner was blocked by the tool platform before effect. Readback confirmed no `.github/ci/legacy-jobs.yml` diff and unchanged HEAD. No manifest bypass or replacement job was created. Separate permitted test execution then produced the 229-pass result. Exact CI-owner registration/contract-delta qualification remains a release obligation; local tests alone cannot waive it.

Scope review found incumbent #7075 also touches the hub/bus family. Its observed bus delta concerns display helpers, policy/analysis copy and staleness; it does not change the command-context projection or digest insertion used here. Preserve that owner and obtain normal current-base integration evidence; do not replay or overwrite its template/design work.

The next Buy Now candidate is now scoped on the existing #7567 owner, comment `5787344850`: evaluate the existing final non-US `dominant + accumulate` recommendation as the narrow continuation path, not a new-bottom requirement. Preserve later risk/extension/macro/deterioration safeguards, stock-entry gates, exact identity and freshness. #7567 and #7669 source bytes were not changed by that ruling, and no worker pickup/START is inferred. Broader `enter` cases still require their separate assessment.

Correction to the earlier explanation: `group_flow.prep_group` computes `pct_rank_window(lvl / bench, lookback)`. The .75 texture cutoff is an own-history relative-price percentile, **not cross-sector rank**. This precision matters to the subsequent evaluation; no cutoff was retuned here.

Continuation boundary: the source-bound artifact-to-narrator integration is implemented and locally tested. Next, qualify #7753 through exact-head hosted/CI-owner and independent review gates, use the authenticated production path, and execute the continuation-entry/card change with #7567/#7669 under their original source custody. Do not repeat the initial reproduction or recreate any branch. No worker, autonomous watcher or continuing Web session has been started. A new chat is not a source-writer transfer.

## Current continuation: same-session correction repair and Buy Now write boundary

MISSION_COMPLETE: false. This section supersedes the previous 229-test checkpoint for current validation; the parent product is still not deployed or accepted.

On #7567's original clean carrier at `d0561c3c3bbad86c3d8c2e89a77ca85135fefafb`, a direct run of the existing assembler reproduced final dominant/accumulate remaining in wait_pullback solely without the fresh-entry texture. Eight prospective contracts (116 appended test lines) were saved, including >=60 sessions of continuing eligibility, immediate final demotion/correction, preserved raw provenance, freshness, missing evidence and conflicts. Their first run failed at the absent `observed_at` API; this is not eight independent semantic mutation kills. The first engine append was blocked by the platform. Same-carrier readback proves no engine change, unchanged HEAD and only the test diff. No blocked write was retried or moved to another carrier. Exact record: #7567 comment `5787532065`. The local test candidate remains uncommitted and must not be mistaken for an implemented Buy Now repair.

The independent #7753 review found a second genuine persistence defect: session checks and digest syntax alone did not detect corrected source bytes within the same session. It also accepted cached row values or omitted analogs under an unchanged source digest.

The repaired briefing consumer now invokes the same canonical context producer against the configured source directory, compares current exact-byte hashes, verifies complete mapped theme/analog coverage, and compares normalized row values to the actual sources. It never treats a digest's format as proof of its contents. A changed/missing source or mismatched/omitted row withholds the foreign-theme context; the existing local stock command remains intact. After the existing producer refreshes the command context, the real briefing consumes the corrected Chinese defensive stance immediately. No new score, stock gate, state store or publisher is introduced. Content hashes are identity receipts, not digital signatures.

Eight new source-content/real-briefing cases were added. The intended red-first execution was blocked before a test result; no red result is claimed. The first allowed post-change run was 235 passed/1 failed: an older performance fixture edited cached values after creating the source receipt. Updating the actual source before minting the receipt repaired that fixture without waiving its assertions. The final nine-suite result is **237 passed**, `content-final-tests.txt`; exact source/test and log hashes are in the cumulative evidence manifest. `git diff --check` passed.

The proof includes the actual briefing sequence: current context -> same-session China correction -> stale foreign context withheld with local picks unchanged -> producer refresh -> current defensive China context, still with the same local picks. This is deterministic implementation proof, not live-market, browser or investment-performance proof.

Remaining gates: normal #7567 engine-write access for the actual continuation/card implementation; #7753 existing-owner CI registration/qualification and independent review; authenticated production input-to-result proof (the earlier official routes returned 401). No credentials, access controls, CI requirements or blocked tool requests were bypassed. No autonomous worker or watcher was started.

Resume the same branches, not replacements. Preserve the #7567 prospective tests and original coherence implementation; continue #7753 from the newly published semantic head and its cumulative evidence. Do not reinterpret the current source-content repair as completing Buy Now eligibility. No live recommendation, stock admission, score, sector quota or sizing changed.

## Current CI-owner repair — 2026-09-23

Current protected procedure pin: Mastermind `c18ea2ca779f042702a63a78bf1f10f5a1e0c0f6`. All five required skill contents were read from that exact revision and matched the previously fully read 1.0.1 blobs. MISSION_COMPLETE remains false.

Hosted run `35808216618`, job `107015602342`, failed on five introduced exclusive-scope omissions for `engine/narrative_crossmarket.py`: biocatalyst-history, biocatalyst-serving, flow-surface, unrun-government-revenue-candidate-projection and unrun-government-revenue-grader. The failing gate was not an unexplained global outage. Its separate unwired render-dead-ref notice was inherited, not this PR's change.

The normal manifest edit succeeded on the original #7753 carrier in this continuation. Each of those five existing owners now includes the exact imported path. The two existing narrative/command suites were also added to the existing unrun-brain-desks command. No new job, runner, waiver, check bypass, threshold or gate removal was introduced.

The existing scope-inference owner was executed against the five affected jobs: all five now have zero uncovered closure paths. This is bounded local closure proof, not a replacement for the complete hosted contract-delta gate. The explicit three-suite context/command/briefing test set passed 89 tests. Runtime source bytes and their prior 237-test proof are unchanged.

Current evidence: `china_us_context_20260922/ci-closure-proof.json` and `ci-owner-tests.txt`. Exact-head hosted rerun, independent review, current-base qualification and authenticated production proof remain owed. This CI repair is independent of #7567's current final member-observation gate, whose write was blocked before effect; it does not bypass that block.

## Configured-source repair recovered and qualified — 2026-09-23

MISSION_COMPLETE: false. Original #7753 carrier only. Current compatible protected procedure pin: Mastermind `89582a372aa2a57ec500868ce6d79cd156219445` (INDEX/COLD_START/ACTIVE_EXECUTION/WEB_CEO_DELEGATION/RECONCILE_STATE/CLOSEOUT consumed from this pin). Direct execution reason: CRITICAL_PATH_SHORTCUT for publishing the already-built bounded correction, not a new source owner or worker.

The earlier local source-directory fix is now recovered through actual source reads and a complete five-file diff on the original Cluade-root worktree. HEAD was still `77df9ed9160494ceec0d735dc61005b66aa7dc96`; no branch recreation, source replacement, or new engine implementation occurred. The current nine-suite regression ran again on those saved bytes: **242 passed / 0 failed**, recorded in `china_us_context_20260922/recovery-current-tests.txt`. The exact eight source/test hashes and recovery log hash now replace the stale current evidence fields in evidence.json; prior 237-pass evidence is retained as historical.

The canonical configured site directory is used by the China hub context producer, default cross-market computation and existing cross-market publisher. The consumer already uses that configured directory. Relative and absolute non-default directory tests exercise the real producer and existing publisher/consumer without silently falling back to ROOT/site. Empty mapped context has summary=None; unavailable variants do not manufacture source receipts for reads that never happened. Ranking, sizing, entry permission and local stock-command isolation are unchanged.

The completed prior independent review and its explicit same-session STOP are now recovered with matching hashes. Its material path-asymmetry finding has been repaired, but its PARTIAL result does not independently approve the changed candidate. Fresh exact-candidate review, current-base hosted checks and authenticated production proof remain owed. The previous real-repository input proof established a stale U.S. feed and truthful withholding, not a current live positive narrative. No relaxed freshness or replacement publisher is introduced.

The #7567 action-template mutation was independently refused before effect in this turn and direct readback confirms the original template remains. This correction is path-disjoint from that refusal. #7567 still owes neutral data-state/type rendering and distinct unsettled-session explanation. Its two failures must not be waived. The wider emerging/enter and CPU/memory goal stays open under the incumbent recommendation/member-intelligence owners.

Publish only these verified saved #7753 source changes and their supported review/evidence on the same branch. Preserve the existing CI registration, source-content correction and constituent-observation guard as DO_NOT_REDO. No active child, autonomous wake, deployment or trade activation is claimed at this checkpoint.
