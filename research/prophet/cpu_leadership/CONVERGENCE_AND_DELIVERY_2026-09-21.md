# Prophet CPU / semiconductor leadership: convergence and delivery

## Mission and authority

Chris's current directive assigns this session main-CEO responsibility for the US/China Prophet improvement and explicitly removes Slack coordination as a dependency. The supplied `diagnostic.md` and `evidence.json` are a read-only first-pass return, not accepted trading-performance proof or evidence of any other writer releasing a started source operation. No new runtime program, ranker, event store, auth path or scheduler is created here.

Protected procedure: `Mastermind@3e66e43258f34db240d5bff76f54148c7af84ee4`, skillpack 1.0.1, protected master verified. Source base for this bounded implementation: `macro@4bf1b3aee532114b0c67e06c532b6e4ed7884549`. Later main observation `ae9f0459a0e815cc71075787a914ce566bf9954e` has no changes to this candidate's engine, builder, dashboard, owner-test or theme-token paths. Source carrier: `sol/us-prophet-candidate-visibility-20260921`.

Direct execution reason: PRINCIPAL_JUDGMENT — the immediate issue is separating evidence visibility from cohort/rank changes and from execution permission while preserving the existing paid-content boundary. No independent worker was admitted or started for this slice.

## What the other audit adds, and what was re-verified

The attachments analyze September 18 boards at `310a23dcd3e5fb8fdb95169a489b94487b091777`. Their four supplied source blob hashes match both that revision and the current implementation base: US board, China board, signal gate and theme-thesis registry. Exact hashes and uploaded-file digests are in `evidence/source_convergence.json`.

Accepted as diagnosis, not as a proposed trade:

- The US eligible pool has 66 names. Only 52 reach the main buy population; 14 are outside it. AMD is T1-eligible at pre-cap screen position 26, displaced by `sector_cap_overflow`, with no final Prophet score. Current code still applies the broad sector cap before calling the final ranker on `wide["buy"]`.
- A complete `candidate_pool` already exists. A source search found no template consuming it. Thus the existing producer was not sufficient for a user to recover every eligible name from the actual main-page lists.
- The full-cohort scoring proposal is consequential: changing a percentile-scoring population changes existing scores. It needs a named comparable cohort, versioned challenger and evaluation; it is not a harmless reorder of two lines.
- China still reports 1,597 measured / 1,601 ranked intelligence records, four unavailable, and one globally coherent V3 fallback. The 1,614-name historical snapshot is a different build and denominator. A real measured zero for Hygon/Loongson is not one of the unavailable rows.
- US September 17 archived reasons must not be presented as September 18 facts. The reported archival omission of AMD/INTC/ARM and others is not proof that all current market prices are stale.
- The categorical CPU crowd-out thesis warrants a dated, product-specific reassessment. Its presence has not been demonstrated to be the direct live ranking veto. This implementation does not overwrite that thesis or grant a narrative new rank/entry authority.

These findings strengthen the original China audit instead of replacing its provenance or pretending that a US CPU cycle proves China price leadership.

## Capability implemented: all eligible candidates remain discoverable

Before: a candidate such as AMD could pass the current signal screen and vanish from both top-level buy and truncated watch lists. Its only complete receipt was nested inside the generated artifact.

After, on this candidate branch: the existing Prophet stock page has a compact, initially collapsed **All eligible candidates** view. It shows all names in the existing pool order, provides company/ticker/sector search, an outside-main-list filter, readable exclusion reasons, and an expandable decision record. Screen position is explicitly not final rank. Eligibility explicitly does not confer entry permission. Off-cohort Prophet scores remain null and render as **Not scored**, never zero or a fabricated comparable score.

Producer and consumers:

1. Existing `build_stock_library` candidate_pool producer remains unchanged.
2. `engine/us_candidate_lanes.project_candidate_visibility` validates date, pool definition, row count, identities and primitive metadata, then creates an allowlisted, pure display projection.
3. `scripts/build_site.py` consumes that view, including the fresh-board re-render path. The same existing server-side panel splitter and `premiumdata/us_stocks.json` carry the paid remainder.
4. The actual `dashboard.html.j2` includes the view. Preview and protected tail use the same row partial. The browser search operates only on rows it is authorized to receive.
5. A digest of the exact projected object binds preview and remainder. Mixed-generation, partial and duplicate tails are refused before mutating the list. This is an evidence-join guard, not a new auth or lifecycle authority.

The view uses existing color tokens, bilingual text and native keyboard-accessible controls. It does not redesign the dashboard, create another data-fetch path, change a plan, or read the candidate pool on any ranking/admission authority path.

## Evidence and acceptance limits

Real-source proof command:

```sh
python3 research/prophet/cpu_leadership/prove_visibility.py \
  --source-ref 4bf1b3aee532114b0c67e06c532b6e4ed7884549 \
  --out /Volumes/Mastermind/tmp/us-pool-browser-20260921
```

The proof uses the real September 18 board and production projection, splitter, row partial, payload writer and hydration function. It verifies 66 eligible = 52 on-list + 14 off-list; three preview rows and 63 protected rows; AMD withheld from the anonymous preview but present after the simulated authorized callback; exact original row order; no duplicated rows on repeated hydration; search, outside filter and empty search state; keyboard expansion; unchanged source-board bytes; rejection of mismatched generation and partial tail.

Eight browser views cover 1440px and 390px, light/dark and English/Chinese, without horizontal overflow. **This is real-artifact component/payload proof, with the authorization callback simulated. It is NOT authenticated deployed-browser proof, and the candidate is NOT deployed.**

The final focused regression and authority suite passed **37 tests** and is recorded in `evidence/focused-tests.txt`. It covers both positive use and negative boundaries, including actual-template XSS escaping, missing-versus-empty state, zero-versus-null scores, protected-preview leakage, immutable source objects, fresh-board refresh, and exact source identity.

The broader pre-hardening run recorded **163 passed, 10 failed, 7 skipped**. All ten failure signatures were reproduced on a separate unmodified base: eight in `test_us_board_gate.py` and two in `test_us_board_hydration_merge.py`. They expect older candidate-grid/lane/count/quiet-list markup in a dashboard whose central grid is now plan-based. They have NOT been disabled, weakened or claimed fixed. Baseline and candidate receipts are retained; seven skips are not acceptance of omitted deployed-byte tests. Review and release must adjudicate those inherited test contracts; local targeted passes are not full CI or production acceptance.

## China input finding that narrows the next repair

At the pinned current source, the four unavailable identities (`000069.SZ`, `600038.SS`, `600606.SS`, `603899.SS`) are absent from `data/china_search/closes.parquet`; corresponding per-stock files are not present in the pinned `data/china_stocks` tree. The hub trajectory reader uses these two sources, while the board's universe can additionally consume a breadth cache. That breadth cache is not committed at this pin, so a static Git audit cannot establish its runtime contents or freshness.

This supports a specific input-coverage investigation: reconcile the actual price series used by the current board with the series available to the board-independent interest reader. It does not authorize fabricated zeros, removal of atomic fallback, arbitrary price borrowing, or claims that the four securities have no prices anywhere. No China data or rank-policy changes were performed here.

## Existing work preserved

- China PR #7567 remains the same carrier, now at `d0561c3c3bbad86c3d8c2e89a77ca85135fefafb`. Fresh hosted fence-pack, self-mod-fence and ci-gate are green. It remains Draft/Open without the required independent acceptance or production proof. Its 196-test display repair is not being rebuilt.
- #7526 owns the semantic thesis repair, including the bounded CPU/HBM/DRAM/NAND correction; #7455 owns closed-session leadership observations; #7508 owns group/member entry context; #7453 owns the corresponding independent acceptance. Returned descriptive evidence does not confer trade authority.
- #7180 owns current completed-session/source-bound US repairs. Its archival/clock work must be reconciled before another writer edits the same paths.
- Open #7264 and #7237 also touch dashboard regions for earnings research and plan trust. This slice changes the candidate-pool include and existing panel hydration only; it does not take their feature custody.

No other session's stand-down, review, merge, or production acceptance is inferred from Chris's intention to contact that session.

## Next execution order and acceptance

1. Publish and independently review this lossless-visibility slice, including hosted CI and inherited test-contract adjudication. Release requires actual deployed-byte and authenticated whole-page proof through the normal product path; no Vercel detour or bypass is used.
2. Reconcile one exact US board/candidate archival build through the existing source/clock owner. Freeze complete input and refusal receipts before comparing scoring orders; do not backdate missing observations from a later snapshot.
3. Evaluate final scoring of the full eligible cohort before presentation curation as a versioned challenger. Keep all current entry, earnings, fillability, concentration and plan-origination controls separate. Report changed ranks, covered/unscored names and cohort semantics before claiming performance improvement.
4. Repair actual China interest-input gaps using the original upstream owner, then re-prove a coherent ordering basis. Never equate unknown and measured zero.
5. Consume the existing economic-exposure, early-leadership and continuation work into a registered CPU/memory-sensitive hypothesis. Test concentrated rallies and failures across themes and regimes before giving that evidence more authority.

The target remains timely, evidence-grounded leadership plus executable, risk-controlled entries — not a permanent semiconductor preference. **MISSION_COMPLETE: false. Capability: BUILT_NOT_PROVEN.**

Record validation: `python3 scripts/agentos.py validate --quiet` reports 1,160 records, zero errors and 286 warnings. Compile and diff-hygiene checks pass. Rendering the actual dashboard with the new view in macro mode does not include the pool, so the stocks-only server-side split is not bypassed by the shared macro VM.

## Additional archival frontier — original-run reconciliation

Using the existing `us_context_vector.load_candidates` reader on the pinned original monthly artifact resolves the unexplained 1,535-row September 18 population: **all 1,535 are scan-tier; there are zero curated rows for that date**. September 17 contains 2,932 curated rows and 1,539 scan rows. AMD/INTC/ARM/NVDA/AAPL/MSFT last appear in the curated tier on September 17. See `evidence/archive-population-read.json`.

The original daily run `35409650053`, engine job `105832792637`, reported `us_context_vector: store now 43285 rows (stamped 2026-09-18, 963.8s)` while building the board. Its build step completed, its earlier plan-output checkpoint completed, and the engine later cancelled before the final engine-output commit (step 147 remained pending). The plan checkpoint's closed output allowlist does not contain `data/us_prophet_rank/candidates`. The scan-tier job succeeded separately. The later nominally successful run `35412430497` skipped its engine, collection and scan jobs; overall workflow success does not establish archival recovery.

This is strong evidence of a durability/publication boundary rather than simply an absent input ticker. It does not prove byte-exact local archive contents: the run log is a producer claim and its reported candidate pool is 76 (60 on-list), not the 66/52 of the committed audit artifact. Recovering one would not automatically reproduce the other. The original run artifact inventory contains only an unrelated, expired capital-structure artifact, not a preserved candidate archive. No nightly retry or historical backfill was attempted.

**Next data-owner action:** trace and seal the library-produced curated candidate snapshot under the existing producer/checkpoint/publication ownership before the long engine tail; establish full board-to-archive generation identity, and preserve existing keep-first/PIT rules. Do not merely add paths to the plan-only allowlist: that manifest belongs to a different producer and its pre/post-digests and source-race checks must remain meaningful. Reconcile with #7180 rather than creating a second checkpoint/control system or copying contemporary values into September 18. Exact run/job/step and artifact receipts are in `evidence/archive-runtime-reconciliation.json`.


# Current continuation: release contracts and same-session corrections

The US candidate-visibility implementation remains on #7572. This continuation does not
change the eligible population, score formula, display caps, entry gates, portfolio size,
plan origination, or any historical archive.

A real render-path defect was reproduced: rebuilding candidate membership or an exclusion
reason on the SAME market date, with unchanged freshness metadata, did not enter the
existing refresh branch. A missing candidate_pool on an otherwise valid refreshed board
also left the earlier view in place. Three production-predicate regressions failed; the
identical-input control passed. The corrected branch compares the existing allowlisted
candidate projection and reuses the fresh object for the view model and protected payload.
This is not a new publication owner or a reconstruction of the missing September 18 archive.

Release-contract repair is separate. The ten prior baseline failures were obsolete UI
expectations: candidate and plan cards were conflated; a removed subtitle count and retired
stage buttons were expected; the relocated theme tape was still expected on this page;
the hydration check named the old target variable and the lane-heading regex disallowed
new nonsemantic attributes. Tests now read the actual Candidates census/shelves and fresh
grid, keep the real plan fixture, preserve whole-page paid-row leak controls, and retain
standalone tape parity/count checks at its actual component. No failing test was skipped.

China source repair #6992 already implements the exact four missing-input fallback. Do not
build it again. Its immutable head a51bae222eedd4c53f4101998f3a3c4bc103f554 composes cleanly
with main 2042b2f4ca5bcd84da47f0937f3b6a1e3d488b77 as tree
57b7d4f665b4c733a249898913e3039fc683c088. An isolated integration commit
7137a0cf3f0198a0974113f0f151e3aad9f01108 passed 169 existing tests with no skips.
Receipt is on #6992 comment 5755311774. No original source branch was changed or writer
released. Original raw-cache witnesses, official current continuity receipt, full current
release acceptance, and controlled serving activation remain unproven. Restoring coverage
can change the entire board order; these tests do not establish investment performance.

Incumbent archive/source-clock #7180 is untouched. Its GitHub current head remains
f83c3603f74591db8920b25c7a5b4b9d9b80b7bf and its complete 20-file API patch was inspected;
its build_site changes concern source time and caller arguments, not this rerender predicate.
The local shared repository is shallow, so no unsupported local #7180 ancestry/merge proof
is claimed. Never widen the plan-only checkpoint or backdate today's values to replace the
missing curated archive.

Next phase: independent exact-head acceptance and production-page proof for the two display
carriers; producer-owned curated snapshot durability with #7180; original source/effect and
controlled-activation reconciliation for #6992. The broader leadership/entry-strategy
mission remains incomplete. No worker/watcher or autonomous wake was started.

## Verified results

Final four-suite run: **183 passed, 0 failed, 7 skipped**. All seven skips are the existing shipped-page/premium-payload probes: those baked artifacts are not present in this isolated checkout. No production pass is inferred. The same-session predicate RED result is three intended failures plus one unchanged-input pass; the repaired focused branch checks pass five cases. A further actual-assignment -> preview/protected-payload test proves a same-session corrected company row reaches only the protected remainder, with both halves bound to its new digest and the original input unchanged.

The current protected Source Continuity GET-only writer-gate adapter was actually executed for #6992. Receipt e8b34a893489bb442cdee12897776dad73f7a8a9f89da50d63ce5cc7892e3204 reports TECHNICAL_WRITER_GATE_UNAVAILABLE / RULES_ABSENT, exact branch head a51bae222eedd4c53f4101998f3a3c4bc103f554, and authority_effect NONE. Under the existing review law, absent technical fencing is not a new permission refusal or an automatic release blocker: custody remains procedural. This receipt does NOT authorize a writer release, receiver transfer, merge, or production activation. Official full source/effect continuity remains distinct and unverified.

Evidence files: release-continuation.json, release-contract-tests.txt, release-shipped-skip-reasons.txt, same-session-refresh-{red,green}.txt, cn-6992-current-{integration.json,tests.txt}, cn-6992-writer-gate.json, source-continuity-adapter-manifest.json in the existing evidence directory. No source adapter was modified or reimplemented.


## Archive-integrity consumer — current same-carrier unit

The September 18 scan-only archive failure is now a discriminated condition in the existing candidate view, not just an audit note. `load_candidate_archive_status` consumes `us_context_vector.load_candidates` for one validated month and compares the already-persisted pool fields using `store_columns`. Only the exact date, board definition and curated tier can match. Missing/changed/duplicate candidate records are disclosed, with opaque unavailable status on reader failure. Matching fields does not prove exact board-generation identity; that remains explicitly false. This is not a full raw-universe audit or a new replay/admission/grade authority.

The compact Saved history disclosure is inside the existing candidate expansion. Its public part carries aggregate counts only. Per-name missing/mismatch details ride the original gated row partial, and an archive-only correction updates the existing same-session source digest and refresh path. Current candidate order, null scores, entry and portfolio rules are untouched. No canonical archive file, source producer or workflow was modified; #7180 still owns the outstanding durable-write repair.

Verification: RED-first 18 absent-API failures; 18 archive cases green; 39 focused source/view/payload/refresh cases green; final existing owner suites **205 passed, 7 skipped, 0 failed**. The seven are existing shipped-page checks without baked artifacts in the isolated checkout, not production passes. Hosted design violations were repaired using the existing radius tokens; current forward ratchet reports zero blockers. Evidence lives in `research/prophet/cpu_leadership/evidence/archive-integrity/`.

The platform blocked the combined new browser-proof update/run request. The proof-script diff is empty on same-carrier readback, the request was not retried through another tool, and no new real-archive/browser result is claimed. Prior screenshots are not exact-new-head proof. New browser/deployed validation and independent acceptance remain release requirements. The original China display repair #7567 has an independent review request to verified repository reviewer MastermindX1 at comment 5756273366; request is not pickup, execution or approval.

The original #7180 hosted blockers were also separated into their actual jobs: an unwired `test_unified_dashboard_b1.py` contract-delta finding, stock-dashboard-first-frame and research-screener failures. This identifies the failed gates but does not show they remain reproducible on today's base, does not classify them as introduced by #7180, and does not authorize a retry or unrelated manifest edit.

Status: BUILT_NOT_PROVEN. Parent mission remains incomplete. Next release action stays on #7572's exact committed head; the next producer change stays with #7180 rather than silently widening the plan-only checkpoint or rewriting historical snapshots.
