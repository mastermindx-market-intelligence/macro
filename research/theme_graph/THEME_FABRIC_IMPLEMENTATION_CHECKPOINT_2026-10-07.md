# Theme Fabric implementation checkpoint — 2026-10-07

**Workstream:** `WS:GMI-THEME-GRAPH` · Frozen authority: `DEC:GMI-THEME-HIERARCHY-ON-CROSSWALK`, `research/theme_graph/THEME_HIERARCHY_SPEC_V1_2026-10-07.md` §7–9. This is an implementation evidence checkpoint, **not** a new lifecycle, owner, taxonomy registry or program ledger.

## Source identity and custody

- Protected Mastermind procedure: `mastermindx-market-intelligence/Mastermind@c7e47c859eb2925c5626931fd511800773ba09ac` (`mastermind.sol_skillpack.v1` 1.0.1, bootstrap 1; `COLD_START`, `ACTIVE_EXECUTION`, `SESSION_RELIABILITY` loaded).
- Macro `main` at latest decision-boundary observation: `1385697ab8353e849f376ad5b2d29994076652ee`; start observation `6848743faa613f2aad55d4b4d831b88f8482f89e`. That main movement was one unrelated file (no W-C7/collision surface).
- W-C7 branch: `sol/gmi-wc7-context-vector-20261007`. Draft [PR #8643](https://github.com/mastermindx-market-intelligence/macro/pull/8643), **stacked against** W-C4 `claude/gmi-hier-wc4-populate-20261007@f64ee5f26ba32e4e6a5af69d16869e224d681fcc`; W-C6 #8612 merged as `e23843869cfc77704dd3ac6738670c1fd6a60a43`. **Do not merge #8643 independently of W-C4.**
- Last semantic implementation/test/doc head before this checkpoint: `840b10e2f816ddaf09946984aef1cf55ae49e031`. Checkpoint commit comes after it; fetch PR head for actual latest SHA.

## Path-level collision census

| Existing carrier | Owner/changes | W-C7 overlap | Decision |
|---|---|---|---|
| #8629 / W-C4 (DRAFT) | `config/theme_crosswalk.yml`, `tests/test_theme_graph_crosswalk.py`, `tests/test_theme_graph_hierarchy_population.py`, `scripts/check_theme_graph_contracts.py`, `.github/ci/legacy-jobs.yml` | none | exact-head dependent stack, no W-C4 edits |
| #8631 / W-C8 (DRAFT) | `engine/market_ontology/exposure_map.py`, its schema/test and owner note | none | untouched |
| #8633 / micro census (DRAFT) | `research/theme_graph/census/MICRO_MEMBERSHIP_CENSUS_2026-10-07.md` | none | consume research return later |
| #8635 / GMI census (DRAFT) | `research/theme_graph/census/GMI_CLASSIFICATION_CENSUS_2026-10-07.md` | none | consume research return later |
| #7870 / semiconductor vertical (DRAFT/HOLD) | shared theme/rights and vertical carrier | none in W-C7 changed files | W-C5 blocked on merge + owner countersign |
| #8643 / W-C7 (this implementation) | `engine/us_context_vector.py`, `tests/test_us_context_vector.py`, `data/us_prophet_rank/README.md`, this checkpoint | self | only source writer for this W-C7 carrier |

## Completed capability delta

- W-C7 adds **nullable display-only** `theme_category_ids` to the nightly US context-vector store. The value is a stable, sorted, pipe-delimited set of `theme:<macro_category_slug>` house category ids, read through the **existing** `structural_navigation.hierarchy_paths` and gated by its rights receipts. Multiple parents survive; no vendor node is a house ancestor.
- Point-in-time inputs: `asof = knowledge_cutoff = stamp_date`; source is a single owner graph snapshot with raw `read_edges(latest_belief=False)` and raw `read_node_lifecycle(latest=False)`, so a later withdrawal or correction never leaks into an earlier belief. It does **not** join today's taxonomy onto historical rows. No second hierarchy resolver, store, edge kind, producer, score, rank, gate or trade authority.
- Integration is in the **existing** `append_candidates` nightly path. The monthly-part parquet writer and `load_candidates` already perform keep-first and forward-only column union; pre-W-C7 historical parts are never rewritten and read as null for the new field. Production input refusal leaves only this shadow null and prints a warning; the other nightly rows still accrue.
- **Curated + scan tier integration:** the curated nightly calls the store with no explicit root; `scripts/run_us_scan_tier.py` passes `root=ROOT`. The initial draft withheld scan-tier context; corrected in `e24572e4f418d6caaf8aa33868477f9428e5cd88` to read incumbent graph inputs when (and only when) `graph_store.store_dir().resolve() == (root / "data" / "theme_graph").resolve()`. All mismatched scratch roots remain null, without touching production data. A new test pins both matched-root scan accrual and scratch isolation (head `840b10e2f816ddaf09946984aef1cf55ae49e031`).
- Product/authority status: **BUILT_NOT_PROVEN** as a draft, zero decision authority. Crosswalk hierarchy population is not on main; no natural nightly W-C7 row or deployed consumer acceptance is claimed.

## Verification and real consumer proof

- Isolated **sparse** test worktree, exact implementation head `840b10e2f816ddaf09946984aef1cf55ae49e031`, `TZ=UTC COLLECT_LANE=nightly`, Python 3.12, `pytest -q`.
- Focused test files: `tests/test_us_context_vector.py`, `tests/test_us_context_vector_payload_containment.py`, `tests/test_theme_graph_hierarchy_paths.py`, `tests/test_theme_graph_hierarchy.py`, `tests/test_theme_graph_hierarchy_population.py`, `tests/test_theme_graph_tier_guard.py`. **131 passed, 11 skipped**, exit 0. Skips include fixture tests requiring a full production data checkout; do not extrapolate those checks.
- W-C7 specific proofs: pre-admission null/default invariance; effective-date and later belief cutoff; withdrawal/correction; polyhierarchy and deterministic serialization; missing graph, invalid and refused reader; vendor-parent exclusion; rank/gate/score unchanged; keep-first; old-part byte preservation; schema union of an old part that lacks the new column; uncapped belief-history owner read. Matched-root scan-tier owner read and mismatched-root scratch refusal are also pinned.
- **Actual codepath fixture proof**, distinct from a helper-only test: incumbent `materialize.build` emits curated PARENT_OF → existing `hierarchy_paths` reads it with cutoff → `append_candidates` writes `theme_category_ids` into `YYYY-MM.parquet` → direct `pd.read_parquet` and `load_candidates` retrieve the same value. The EXPRESSES basket link and membership are synthetic for this fixture; this is **local producer/consumer proof**, not real market/nightly publication.
- Broader optional `tests/test_us_candidate_lanes.py` encountered one remaining **baseline-equivalent** guard red: `scripts/prophet_journey_reconcile.py` tokens `candidate_pool` / `us_candidate_lanes` are not in its existing allowlist. The two files have identical GitHub blobs on current main and #8643: `c2f0c746a9435f3d3d0064798b7624bac1ffca69` and `69fb701d3452dc5b0ba8431afc83c711c4116bec`. This unrelated guard is **not** W-C7 acceptance; do not quietly change another owner to green it. Earlier sparse failures were omitted-dependency artifacts (`collectors`, `research`, `admin`, `app`) and were repaired only in the isolated test checkout.

## DO_NOT_REDO, holds and unresolved gates

- **DO_NOT_REDO:** W-C6 #8612 merged reader; W-C4 #8629 population and its `config/theme_crosswalk.yml`; W-C8 #8631 exposure-map ancestry; #8633/#8635 censuses; #7870 incumbent vertical; previously accepted ThemeState/tier-guard work. Do not rebake production theme graph locally, touch active sibling paths, create a second hierarchy or read-most-recent taxonomy for a past decision.
- **Research-dependent HOLD:** new themes/microthemes and membership, V1.1/V2 taxonomy, finance/semiconductor slice changes, economic/trading/attention exposure weights, causal relationship types, microtheme ThemeState legs, Prophet scoring/ranking/sizing/gating/trading integration. W-C5 requires #7870 **merged plus owner countersign**. W-C9 evaluation preregistration/run waits on real W-C7 accrual.
- **Remaining W-C7 admission:** W-C4 adjudicated and merged; revalidate W-C7 against updated main; incumbent owner CI and independent review; merge/deployment only through their gates; capture first real nightly `source graph → PIT reader → monthly parquet → read-back` receipt with a naturally populated hierarchy. Synthetic-only status is not release acceptance.

## Exact convergence frontier for Pro Theme Fabric return

Reconcile the new research masterplan with this checkpoint; latest #8629 and #8631 reviews, #8633/#8635 census dispositions, W3B ThemeState owner status, and #7870 dependency. Preserve PR #8643 as the W-C7 carrier; retarget/reconcile its stack only after W-C4 merge and collision review. Next owned action is **W-C4 decision and merge by its incumbent seat**, then W-C7 review/CI/current-main verification, followed by the natural-night proof. No separate in-scope research-dependent build is authorized merely to fill the wait.

## 2026-10-08 continuation — W-C7 lifecycle/PIT hardening

**Current source identity.** Mastermind protected master c7e47c859eb2925c5626931fd511800773ba09ac, compatible Skillpack 1.0.1 / bootstrap major 1. Macro main 8aa1aca8c593982e722bbc666a221fdd82466f15. W-C8 #8631 is MERGED at that main head (accepted candidate 54419a42871837682ddd217bfaad30cff4bfa209). W-C4 #8629 remains DRAFT, current owner head a4deb82387895dae58bb77404faeeb851450c174, having reconciled the CI-file collision. W-C4 workflow runs 37848256909 and 37848257463 were IN_PROGRESS when observed, not accepted here. W-C7 #8643 remains a separate DRAFT dependent on that W-C4 branch; source/release custody is unchanged.

**Verified new defect (pre-fix RED).** The incumbent graph store read_node_lifecycle(latest=False) defaults to a lenient read. A PRESENT corrupt parquet returned [] with only a log warning, which permitted a house category to reappear as if no lifecycle correction or withdrawal existed. The new test_wc7_corrupt_owner_lifecycle_fail_soft initially failed: 1 failed, 1 passed, 72 deselected; actual category {x: (theme:cat_a,)} instead of the required null. This reproduces the same fundamental point-in-time failure class reviewed in W-C8 B2.

**Bounded repair.** W-C7 now distinguishes genuinely ABSENT optional lifecycle data (compatible empty history) from a PRESENT lifecycle sidecar (strict owner read, raw history, no latest-belief collapse). If the present sidecar fails to read, the hierarchy shadow is withheld and warns; normal nightly records still write. Another W-C7 fix distinguishes a refused hierarchy path for an individual basket from a legitimately uncategorized basket. A ticker belonging to both readable and refused baskets now gets null rather than an incomplete category set presented as complete. Other tickers retain their independently resolved categories. Explicit root mismatches warn and continue to prevent cross-root graph reads. No new resolver, graph, edge, producer, authority, per-ticker exposure, ranking or trading path.

**Paths and heads.** Only engine/us_context_vector.py, tests/test_us_context_vector.py and data/us_prophet_rank/README.md changed, plus this existing checkpoint. W-C7 semantic implementation/test head: 7574d409ac6bb2a5792a0c9364075019b372a2da. README-only head before checkpoint: d6d3e9c6ce6c1b02e447f2bfd121a6f879313097. Read #8643 again for the final checkpoint head; never reuse these as later current-head evidence.

**Verification.** Isolated detached W-C7 checkout, TZ=UTC and COLLECT_LANE=nightly, Python 3.12: focused six-file pytest pack (context vector, payload containment, hierarchy paths, hierarchy materializer, population, tier guard) -> 135 passed, 11 skipped, exit 0. W-C7-only selection -> 18 passed, 58 deselected, exit 0. New witnesses: corrupt lifecycle refusal, optional absent/empty lifecycle compatibility, refused lifecycle preserving the nightly write, mixed-basket partial refusal and unaffected tickers. Full-data population tests remain skipped by the sparse checkout; no production or main-branch acceptance claimed. Existing isolated materialize.build -> PIT hierarchy_paths -> append_candidates -> monthly parquet -> load_candidates fixture proof remains valid.

**DO_NOT_REDO / research holds.** #8629 remains the incumbent population and CI owner; do not edit or merge its carrier from W-C7. #8631 W-C8 is merged and must not be rebuilt. #8633/#8635 V1.1 censuses and #7870 vertical are externally owned; W-C5 requires #7870 merge and countersign. W-C9 evaluation depends on actual accrual. New taxonomy, exposure weights, causal edges, ThemeState legs and Prophet/trading authority remain held for Pro research.

**Next convergence action.** After W-C4 has merged through its own owner, reconcile #8643 onto the exact new main (including merged W-C8), verify current-main code and CI, obtain independent review and then the first real nightly PIT consumer receipt. This continuation is BUILT_NOT_PROVEN, not production-accepted.

## 2026-10-08 isolated current-upstream integration proof

**Purpose:** verify W-C7 compatibility with the active, newer W-C4 owner head and already-merged W-C8 without editing any incumbent PR or declaring CI green.

**Exact source:** W-C7 semantic head 7574d409ac6bb2a5792a0c9364075019b372a2da in the detached, isolated test worktree. Current W-C4 owner head at probe a4deb82387895dae58bb77404faeeb851450c174 (descends from original W-C4 f64ee5f). The latter includes accepted W-C8 merge 8aa1aca8c593982e722bbc666a221fdd82466f15. W-C4 movement from f64ee5 to a4deb did not change any of W-C7's four owned files (GitHub compare: zero path overlap).

**Method:** same-carrier local git fetch of W-C4 owner branch; git merge-tree --write-tree of the W-C7 test head plus FETCH_HEAD returned tree SHA 3918a260a503ad4bf96bcf1a57eb601324119985, no conflict. An isolated git merge --no-ff --no-commit of FETCH_HEAD into the DETACHED W-C7 TEST WORKTREE then succeeded without conflict; this was a test-only merge, not a branch push/commit, and not an attempt to move W-C4 source custody.

**Verification on the merged test tree:** W-C7-only targeted cases -> 18 passed, 58 deselected, exit 0. Seven-suite pack (US context vector, payload containment, hierarchy paths, hierarchy materializer, hierarchy population, tier guard, AND F04 exposure-map) -> 206 passed, 10 skipped, exit 0, TZ=UTC, COLLECT_LANE=nightly, Python 3.12. This directly tests W-C7 plus W-C4 candidate and merged W-C8 together at the testable level; skipped cases are still full-data tests. No full-graph local rebake, GitHub CI conclusion or production receipt is implied.

**Cleanup/readback:** Local merge explicitly aborted on the same isolated worktree; HEAD verified back at 7574d409ac6bb2a5792a0c9364075019b372a2da and tracked dirty count 0. Remote W-C7 branch and upstream W-C4 branch were never modified by this compatibility test.

**Frontier remains held:** W-C4 #8629 is still OPEN / DRAFT at a4deb82387895dae58bb77404faeeb851450c174. The latest unrelated Macro main observation after this test is 11b48b2304ecda38bc4f78594af58cc8bfafd871; this moving main was not the target of the isolated merge proof, and owner CI/merge admission remain separate. After W-C4 merges through its incumbent owner, reconcile/retest W-C7 against that final exact main, obtain owner CI + review, and pursue natural nightly production artifact proof.
