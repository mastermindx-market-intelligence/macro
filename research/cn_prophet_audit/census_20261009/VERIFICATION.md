# Verification, reproduction and effect boundaries

Operation `MMX-CN-PROPHET-CENSUS-20261009` · 9 October 2026 · research only.

## 1. Bound source and study inputs

| Item | Verified identity / scope |
|---|---|
| Canonical implementation | `mastermindx-market-intelligence/macro`, repository ID 1266869026, default branch `main` |
| Study source/data commit | `3d90aad6d83152dfeeaf8345bc995826ac9d3139` |
| Study base tree | `546f616981ff78bc1810d5926cbe279262e03df9` |
| Protected Mastermind procedure | `326c8469a21d7f50fc9ecb1848196bf1c6e66685`, skillpack 1.0.1 / minimum major 1 |
| Branch protection read | Mastermind protected; Macro main `protected:false`; no settings changed |
| Original research checkpoint | Commit `0dab913b711bf4a761cb728bf8602695c05ea075`, tree `516b0cc3efe46f50c87af1aec79212c41247819b` |
| Research carrier | `claude/cn-prophet-census-20261009`, [PR #8714](https://github.com/mastermindx-market-intelligence/macro/pull/8714), open Draft/HOLD, no auto-merge |
| Incumbent R0 replay | [PR #6871](https://github.com/mastermindx-market-intelligence/macro/pull/6871), observed head `51ddb898ff0c130910f9f3f4266727905826a92d`, open Draft/HOLD |
| Read-only source worktree | `/Users/chriswong/Documents/Cluade/macro-main`; experiments use immutable `git show`/tree/object reads |

The implementation source and data were frozen before the experiments. The reviewed carrier integration base is Macro main `698fd13e5f0a041ec5b9010293175232983f4f44`, tree `231d9c5c16fa84887dd509ef68d233ed297851e1`, four commits ahead of the study pin. The first three commits through `b7bea6d9af13e12cc78ac1527d9b71d408e09787` change 16 paths; the fourth adds one unrelated Terminal data-cache discovery record. None changes the studied China rank, gate, candidate/board/latch, calendar, microstructure, live-pack or reconciler source or study input blobs. One shared live-quote change raises `DISPLAY_BOARD_CAP` from 320 to 480 and adjusts its test; its purpose is additional displayed-symbol coverage. It does not repair the frozen-board schema or scheduled-reconciliation seams reported here. Other changes are White House/press-wire/Q-ledger/cost artifacts. The study remains pinned to its original epoch; no research input was silently updated.

The final research carrier incorporates that reviewed main revision as an additional parent of its completion commit, preserving the initial checkpoint as its first parent. Its tree is the reviewed integration base plus this dossier and the one new China Prophet discovery. This synchronizes only the isolated research branch. It does not write to main or change the study source/data pin; the final diff against the integration base must contain only those research and knowledge-plane paths.

Source links are collected in [SOURCE_INDEX.md](SOURCE_INDEX.md). The detailed historical source/output identities are in [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json). GitHub file-fetch responses sometimes append one newline; a local source transport copy is not declared raw-byte-identical until its Git blob hash is checked. The ordering reviewer specifically verified the relevant source copies after accounting for that transport newline.

## 2. Executed diagnostics

Run these commands from the docket directory against a read-only checkout/object store containing the pinned objects. Use a new temporary result directory. Python with pandas, NumPy and PyArrow is required for Parquet analysis. These scripts do not invoke production collection, ranking publication, deployment or trading.

### Source/data census

```bash
python3 reproduce_census.py --repo '/Users/chriswong/Documents/Cluade/macro-main' --sha 3d90aad6d83152dfeeaf8345bc995826ac9d3139 > /tmp/cn-prophet-pipeline-evidence.json
```

Executed through the authorized host connection: PID 92497, completed exit 0, 2.48 seconds. The source reader uses the actual committed board document, then disposable path/schema fixtures; it does not mutate the shared source. Results include current board counts, valuation/source ages, canonical/legacy-path frozen-reader failures, score/rank projection and scheduled pack-consumption evidence. Persisted result: [pipeline_evidence.json](pipeline_evidence.json).

### Current ordering controls and sensitivity

```bash
python3 ordering_diagnostics.py --repo '/Users/chriswong/Documents/Cluade/macro-main' --sha 3d90aad6d83152dfeeaf8345bc995826ac9d3139 > /tmp/cn-prophet-ordering-evidence.json
```

Final executed host PID 26049, completed exit 0, 0.97 seconds. Exact source AST functions establish ordering, measured-zero acceptance and malformed/unavailable coverage. The public artifact supplies the fixed qualified 125-name population. Positive control is 24/24 exact V3 membership and order; the intended intelligence permutation retains 4/24. Independent candidate-vintage replay confirms the entrant order despite 37 same-date intelligence-value differences. Components are omitted with source-faithful four-decimal points, clipping and two-decimal total rounding. [ORDERING_REVIEW.md](ORDERING_REVIEW.md) is PASS at the final hashes.

### Historical reconstruction

```bash
python3 autopsy.py --repo '/Users/chriswong/Documents/Cluade/macro-main' --out /tmp/cn-prophet-historical-results
python3 extend_audit.py --repo '/Users/chriswong/Documents/Cluade/macro-main' --out /tmp/cn-prophet-historical-results
python3 verify_diagnostic.py
```

The first two commands were executed in the worker's isolated host directory `/tmp/mmx-cn-prophet-historical-20261009/results`. All 1,875 inspected stock-price files are bound by immutable Git objects and the aggregate price-hash manifest recorded in the result. No production module is imported; reviewed pure episode and entry functions are extracted by AST. Outputs include the per-definition/horizon/cohort tables, selected-case records, current/latch reconciliation, common-feature/date ranking comparison, missing-price and unresolved-selection coverage, benchmark sensitivity and explicitly unavailable clock-only test.

`autopsy.py` and `extend_audit.py` produce raw result files and CSVs in the specified directory. `historical_evidence.json` is the delivered compact integration of their autopsy/extensions results; `v4_review_rows.json` retains column/data matrices for independent arithmetic without another remote extraction. The integrated artifact preserves the summarized raw fields and source identities. The independent review recomputed the 289-row V4 latch/current-fill results, the five-arm 11-date comparison and common matured-horizon cohort. The parent also ran `verify_diagnostic.py` locally on the delivered scripts: PASS for market-session horizon, nonpositive close MAE, missing-session refusal, maturity and selection without outcome-based replacement. [HISTORY_REVIEW.md](HISTORY_REVIEW.md) is PASS for the bounded retrospective method and final wording.

### Requested ranking-metric completion

```bash
python3 rank_metrics_addendum.py
```

The additional input is a lossless, hash-bound subset of the already generated `eligible_candidate_horizon_returns.csv`, not a new price reconstruction. The original CSV SHA-256 is `2db25adc73e9e5e5a934898edb4da6ae6852b43b096613acbe5724b8f622a1b3`, matched to its existing results manifest. The separate input retains 1,488 qualified V4 H10 rows over 29 dates, including 537 immature and two missing-session outcomes. It preserves the source strings and original manifest so the local calculation needs no further host/vendor query.

The addendum reconstructs all 55 accepted common-feature arm/date results and ten complete-pool controls before calculating precision@6, decile return lift and additional precision lift. Decile K is `ceil(0.1 × original pool size)`, with no sector cap and equal-date aggregation; all five arms share ten complete-pool dates. The return-lift intervals use 10,000 shared paired date resamples with fixed seed 20261009. The exact intended intelligence/V3/ticker tie-break leaves all 11 original six-name selections and their order unchanged. These additional descriptive results keep their own cohort and uncertainty limits and do not alter the original historical evidence or scripts. [RANK_METRICS_REVIEW.md](RANK_METRICS_REVIEW.md) is independently recomputed PASS, accepted by the parent, and binds the final addendum, report insert and handoff validation/cost subsection. Quality's decile-lift interval is wholly negative; the other four span zero. No positive advantage is demonstrated.

### Actual public HTML observation

```bash
python3 publication_probe.py --repo '/Users/chriswong/Documents/Cluade/macro-main' --sha 3d90aad6d83152dfeeaf8345bc995826ac9d3139 --html /tmp/mmx-cn-prophet-live-page-20261009.html --observed-at '2026-10-09T21:08:14.572007+00:00'
```

The public page `https://mastermind-x.com/china_stocks.html` returned HTTP200 at that timestamp. Captured HTML had 1,551,095 bytes, SHA-256 `f5a7da631d044eada6041a8e350bc503e68a16b85324df806326f9d9995670ce`. Replay PID 40433 completed exit 0 in 0.51 seconds. It identifies 24 featured plus 124 overflow cards and exact membership/order agreement with the pinned artifact. [publication_probe.json](publication_probe.json) retains the timestamp, hash, all ticker lists and the comparison scope. Omitting `--html` performs one new public HTTP read; its result would be a new observation, not a reproduction of the old page.

The raw captured HTML remains a temporary observation artifact, not an enduring historical publication archive. The durable result and hash support the recorded current receipt; a future auditor needs the original captured bytes to reproduce that exact old response. The authenticated canonical artifact and `/live/cn_prophet_live.json` routes returned HTTP401 in the separate unauthenticated check. No browser JavaScript/visual session, authenticated overlay, installed service source identity or natural live-event write was verified. The one successful HTML observation does not reconstruct any earlier recommendation's publication time.

## 3. Independently reviewed identities

| Artifact | SHA-256 |
|---|---|
| `ordering_diagnostics.py` | `e9b0a0cdb2ad8e831b5071ab831ffddeb6dc0884bf2037ff1be7a16efb731368` |
| `ordering_diagnostics.json` | `527ece9b344c34d64d184ff5fb67dbaafbe6efe557b794b03b08a908b03dde86` |
| `ORDERING_REVIEW.md` | `90d812a943601a875f2502d98a36f0d58291498d8d0cc8a2eff9339f1a649c21` |
| `autopsy.py` | `5a09a5112b3920201001d7fceefefcd336716154c696269fa6d680043a05e6a6` |
| `extend_audit.py` | `3838a50f85067e6a1a3ff990ec70c7f7a0f997699fb123a1406a3efc28f11408` |
| `historical_evidence.json` | `8b651cf4df19736f66a3cf184c5a47478ffe0bf2fc62a24bb5452c01b836e54d` |
| `v4_review_rows.json` | `626aacda09bdef9ba6cd8bb01a3688e445228b48ce63d5496defb07ce0482830` |
| `HISTORICAL_EVALUATION.md` | `49096c1197adb12bc29e526497700aa87073852ab3aee73d6e9efdc4fec668c0` |
| `HISTORY_REVIEW.md` | `156eb232e9549f59c5b397d763b95e4b5338e28c51b1b091dbd1147532780648` |
| `publication_probe.py` | `2aa725f4f464f79d57fc0c4a56d84bd6a18df7ab419009f52d6e1cfd7b5d2474` |
| `publication_probe.json` | `2161a923a6245cac0db7d13950893fdc57e4690a92a3ac7dcccc1a3591ddf963` |

The reviewed outputs were copied without modifications; the parent verified all eight historical manifest entries by byte count and SHA-256. Later editorial and supplemental metric findings are recorded separately, without silently changing those accepted artifacts. [FINAL_REVIEW.md](FINAL_REVIEW.md) covers its stated integrated scientific and handoff snapshot; [RANK_METRICS_REVIEW.md](RANK_METRICS_REVIEW.md), SHA-256 `f1a799a4ac4388fc121a40fb6ec5a9ea7c2fbaae50d4eb469b696fad8ec95809`, covers the later additions and binds the final report and handoff identities. The delivery manifest binds the complete final textual artifact set.

## 4. Findings corrected during review

- A draft current-score omission did not reproduce final score rounding exactly. The author repaired it; the reviewed same-day overlap results use the final source-faithful calculation.
- A draft historical comparison filtered to available outcomes before selecting names. The final script freezes the original pool first. One common-feature date is unresolved rather than receiving a replacement stock. Rejected-method diagnostics remain visible.
- The historical comparison now uses common feature coverage and dates, preserves whole missing-price names, clamps close MAE at zero and removes an unsourced adjusted-price legal-limit/chase classification.
- Case features are labeled candidate snapshots, not certified first-publication features. The four examples are selected extremes, not representative causal samples.
- Integrated wording distinguishes the stored-intelligence/ticker baseline from the exact intended intelligence/V3/ticker policy; spanning-zero intervals imply no demonstrated advantage, not proof of equality or inferiority.
- Precision reporting specifies frozen K, observed and unresolved counts, complete-K primary comparisons and explicit conditional precision/bounds for incomplete dates.

These changes improve the validity of the research result. They are not production code repairs and do not establish improved future returns.

## 5. Scoped repository validation

All delivered Python files were parsed with the Python AST; every JSON file decoded successfully. This is syntax/format validation, not an investment-performance test or a full production test suite.

The new discovery record was validated in isolation using the **exact pinned** `scripts/agentos.py` Git blob `1cdffbb99b8067f036e609e9016d8fafd4fb6c71` and `config/mastermind_programs.yml` blob `6e7a6ff907bb9c9c559365acee0f609604f61c3c`. Transport-only appended newlines were removed after Git blob verification; validator logic and configuration were unmodified.

```bash
python validation_source/scripts/agentos.py validate --root deliverable/agentos --quiet
```

Observed: **1 discovery, 0 errors, 0 warnings**, exit 0. This validates the authored discovery's schema and local references under the canonical validator; it is not a full-fleet AgentOS or repository CI result. Existing production suites were not run against an incomplete scratch copy. Final PR checks and carrier status are read separately during canonical persistence.

## 6. Effects and completion boundary

Shared source worktrees were read-only. Host writes were restricted to unique analytical temporary directories; local edits are the research dossier, isolated validation copy and one knowledge-plane discovery. No production dataset, entry latch, candidate decision, ranking, live configuration, deploy setting, account, order or person-directed message was changed. Native research delegation had acknowledged pickup/start receipts, independent returns and parent adjudication; it created no external worker runtime or new organizational owner.

The canonical write is confined to the existing isolated research branch and its Draft/HOLD PR. No merge into main, ready-for-review transition, auto-merge, release, source-law rewrite or implementation pickup is implied. The incumbent #6871 `.SZ`/original-basis and rejected historical assertions remain held. The precise final commit/ref and readback are discoverable through #8714; the response reports that verified head after persistence.

The valid closeout claim is **completed research commission, candidate-quality upgrade unproven**. Missing original publication clocks, benchmark opening data, full historical universe/security status, execution receipts, richer regimes and untouched future evaluation remain explicit requirements for future work.
