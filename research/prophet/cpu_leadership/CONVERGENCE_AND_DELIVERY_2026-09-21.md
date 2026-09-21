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
