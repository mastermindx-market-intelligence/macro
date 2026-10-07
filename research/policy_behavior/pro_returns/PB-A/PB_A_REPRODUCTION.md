# PB-A — Reproduction and evidence guide

## Scope

This is the reproducible research return for `PB-A-POLICY-BEHAVIOR-BASELINE-20261007`. It contains 24 primary U.S. Fed/Treasury episodes and one separately selected June 2023 challenge. It has no network, broker, production-store or live inference dependency. The full richer M2 and several target families remain explicitly untested because required pricing, cost-history or transmission data are absent.

Read [PB_A_METHOD_AND_FINDINGS.md](PB_A_METHOD_AND_FINDINGS.md) first. The method names `M2` in the JSON **M2-min** in prose to distinguish minimal rate-decision persistence plus a conventional-floor assumption from the full commissioned actions/constraints/revealed-preference model.

## 1. Quick reproduction

Use Python 3.9 or later with the IANA `America/New_York` timezone database available. This package was verified with Python 3.12. It uses only the standard library. No package install or internet connection is needed for the included data.

From the extracted PB-A directory:

```bash
python3 pb_a_verify.py --reproduce
```

This command validates the received hash manifest, immutable design/code/forecast identities, episode structure, source-time bounds, joint-agency lineage and the allocation/settlement distinction. It then creates a temporary directory, copies **only** the three design/input files and scorer, and regenerates the forecast before an outcome directory exists. After verifying the forecast bytes, it adds the included outcome data and reproduces both targets, all matched score groups, the exploratory calendar diagnostic and the assembled casebook. It leaves the received files unchanged and prints a JSON result with `status: PASS`.

The transcript of the pre-publication reproduction is [PB_A_VALIDATION.json](PB_A_VALIDATION.json). Its manifest count is zero because the receipt was created before the final manifest. The delivered verifier reads the final manifest and verifies every listed file. This difference does not affect the analysis. A missing, modified or malformed input is an error, not a zero-valued observation.

To run only package integrity and structure checks:

```bash
python3 pb_a_verify.py
```

To run the scorer's fifteen synthetic edge checks:

```bash
python3 pb_a_analyze.py self-test
```

An independent reviewer also ran nine separate synthetic examples and found no material scorer blocker; see `audit/scorer_review.md`. These checks validate implementation details, not generalizable policy-forecast skill.

## 2. Manual stages

The following commands write outputs, so run them in a disposable copy of the PB-A folder if you want to preserve the delivered manifest unchanged:

```bash
python3 pb_a_build_casebook.py build
python3 pb_a_analyze.py forecast
python3 pb_a_analyze.py score
python3 pb_a_build_casebook.py assemble
python3 pb_a_endpoint_sensitivity.py
```

`build` reads the three reviewed source-annotation packets, normalizes clocks, source roles, action stages and qualitative fields, then writes the decision-only casebook and strict prediction inputs. It reads no outcome file. If an input file is already present, it preserves the original coding timestamp so deterministic reconstruction of the delivered package is possible.

`forecast` reads only `PB_A_DECISION_INPUTS.json`, `PB_A_PROTOCOL_FREEZE.json`, `PB_A_IMPLEMENTATION_CLARIFICATIONS.json`, and its own code bytes for hashing. Its pure predictor receives four scalar features. It does not read the source-packet prose, the whole casebook, a market series or an outcome file.

`score` first verifies the forecast content digest, the four input/code identities and regenerated predictions. **Only afterward** does it open the outcome files. It reconciles the daily target series against the official decision/effective-date ledger, reconstructs the most recently publicly decided anchor, computes each target/horizon and builds own, pairwise and three-way coverage results. An already-announced next-day rate implementation is absorbed into the anchor.

`assemble` places the frozen forecast row inside `decision_time`, then attaches the corresponding outcome row afterward. It does not run a model. The source register includes archaeology and excluded material for audit, while the case-specific certificate identifies what is admitted. The normalized canonical fields override weaker provisional wording in raw source annotations.

`pb_a_endpoint_sensitivity.py` is a separate **post-score exploratory** diagnostic. It keeps the primary predictions, probabilities, sample, cuts and anchors fixed and changes only net-target horizon endpoints by −7/0/+7 days. It excludes the challenge and writes a separate JSON file. It must not replace the primary results or be described as preregistered validation.

### JSON formatting and reproducibility

The large published `PB_A_BASELINE_PILOT.json` is whitespace-compacted to reduce transfer size. The scorer emits the same JSON object with indentation. The verifier compares canonical JSON content for this file, so either representation reproduces identically. No numerical value, ID, comparison intersection or result was changed by compaction.

- Original indented pilot file SHA-256: `02dea7aef2b4bee65a55552e8195ae73ceef5c674c8041e91400e1f4169bd656`.
- Published compact pilot SHA-256: `13a608725989e95bd5775dfc21b1f67c4319a82a60bdf99255cfefdf839bc62f`.

The exploratory diagnostic records hashes of the files it reads. The verifier therefore uses the delivered compact pilot bytes before reproducing that diagnostic. If you rerun the manual stages, its input byte hash may reflect your indented pilot even though every mathematical result agrees. Use the read-only verifier for exact reproduction of the delivered artifacts.

## 3. Immutable evidence chain

| Item | Identity |
|---|---|
| Protected Mastermind procedure | `9a24ef2c4b27ac95a4d1f72f5eae1073657cd7c2` |
| Commission carrier | Macro PR #8560, handoff at `7abc3dc596c5a6463effb37422bf9bd34bbdf1ba` |
| Parent research packet | `ee86db2c832c73a36837c1240df871700340d6da` |
| Fresh-branch main base | `309f88c6c209bdc9fb611de0018fb619d9351b37` |
| Initial protocol commit | `99253212652ba7d1248a587c249da44ec6e3b9b6` |
| Decision/code/forecast commit, before scoring | `8799d065178b7637bc91a0e69696df8b9ef763f6` |
| Forecast file SHA-256 | `2204fc89a45fa6cb3234762316ae63ffdd9f60daae631c799e2d0d5ac55e246a` |
| Frozen decision input SHA-256 | `8235b465e9c0b05f23d499b849d74789d0ef40cb99885306295b92bdf5485ff5` |
| Frozen scorer SHA-256 | `590155910f811f29fd7230055387fb93f37cd83930d1ee01ef5db8f764774f27` |
| Frozen protocol SHA-256 | `5f5c4f2b2100defeaf31fa8aa3eaa4975fe46bf4db1723d433f1be9b5dfe009b` |
| Frozen clarification SHA-256 | `74192c2966f07aad502437120359a8aeba5c834f2e6928902c0423517d4d142c` |
| Outcome artifact SHA-256 | `257be1726d941ff0ae562eb1354ac9820c6abf02a26224b70cb62d544eb4fdfd` |

The forecast commit was fetched back through immutable file references and compared exactly before scoring. Its protocol, clarifications, decision inputs, scorer and forecast bytes are unchanged in the final return. The casebook was subsequently enriched with source-preserving schema aliases, explicit absent-control fields, multi-origin joint-statement lineage, corrected BTFP quarantine wording and the outcome join. These annotation changes are recorded in `PB_A_COMPLETION.json`; they do not change model inputs or results.

The final branch, draft PR and verified package-content revision are recorded in `PB_A_RETURN_RECEIPT.json`. The PR's final head and readback are also returned in the commissioning chat. A mutable branch name alone is not the evidence receipt. No merge or production acceptance is claimed.

## 4. Source and data layout

| File or directory | Purpose |
|---|---|
| `PB_A_METHOD_AND_FINDINGS.md` | Standalone method, results, interpretations, limits and PB-G recommendation |
| `PB_A_CASEBOOK.json` | 25 complete normalized rows; primary/challenge distinction; sources; decisions before outcomes |
| `PB_A_BASELINE_PILOT.json` | All policy scores, exact coverage intersections, regimes, slices, sensitivity and uncertainty |
| `PB_A_OUTCOMES.json` | Per-episode policy and daily market observations, actual dates and gaps |
| `PB_A_PROTOCOL_FREEZE.json` | Original fixed sample and model/target definitions |
| `PB_A_IMPLEMENTATION_CLARIFICATIONS.json` | Pre-score endpoint, clock, coding and comparison clarifications |
| `PB_A_DECISION_INPUTS.json` | Strict four-feature prediction input, known focal anchors and source-time bounds |
| `PB_A_FORECAST_FREEZE.json` | Frozen predictions, probabilities, abstentions and input/code digests |
| `PB_A_ANALYSIS_CONTRACT.json` | Build-time input schema example; its original workspace locator is explanatory only |
| `source_packets/` | Three complete reviewed source-annotation packets, not archived webpage bytes |
| `outcome_inputs/` | Six public CSV extracts, verified decision-change ledger and retrieval metadata |
| `audit/` | Independent protocol, source, scorer and recent-case integration reviews |
| `PB_A_ENDPOINT_SENSITIVITY.json` | Separate endpoint-only exploratory diagnostic and independent anchor/label audit |
| `PB_A_VALIDATION.json` | Package verification and reproduction receipt |
| `PB_A_COMPLETION.json` | Bounded capability, limitations, accepted repairs, unresolveds and next owner/gate |
| `SHA256SUMS.txt` | Received-file integrity manifest; excludes itself and generated bytecode |

The original sources are official Fed, Treasury and TreasuryDirect documents. The joint March 2023 statement also originates from the FDIC. URL-specific identities, source families, publisher/originator, clock evidence, correction/supersession notes and admission are in the casebook. Registered archaeological sources remain distinguishable from predictive sources. Exact URL duplicates are identified by canonical URL-derived document IDs; the current catalog contains 84 distinct URL records. These are not 84 independent observations.

### Public outcome series

| Series | Measurement | Source |
|---|---|---|
| DFEDTARL | Effective daily lower target bound, percent | [FRED](https://fred.stlouisfed.org/series/DFEDTARL) |
| DFEDTARU | Effective daily upper target bound, percent | [FRED](https://fred.stlouisfed.org/series/DFEDTARU) |
| DGS2 | Daily two-year Treasury constant-maturity yield | [FRED](https://fred.stlouisfed.org/series/DGS2) |
| DGS10 | Daily ten-year Treasury constant-maturity yield | [FRED](https://fred.stlouisfed.org/series/DGS10) |
| DFII10 | Daily ten-year inflation-indexed Treasury yield | [FRED](https://fred.stlouisfed.org/series/DFII10) |
| T10YIE | Daily ten-year breakeven inflation compensation | [FRED](https://fred.stlouisfed.org/series/T10YIE) |

The extracts cover 2018-01-01 through 2025-01-10 and were retrieved on October 7, 2026. The exact CSV download URLs and SHA-256 values are in `outcome_inputs/retrieval.json`. The ledger `policy_decision_changes.json` documents each of 23 nonzero policy changes with an official release URL, decision clock, effective date, prior/new range and verification evidence. It reconciles every effective-series change in its window. It is an outcome-source ledger, not a predictor-accessible time series.

The official [Fed target-change history](https://www.federalreserve.gov/monetarypolicy/openmarket.htm) is a current historical reference. It must not be treated as if its current content, corrections and future rows had been available at earlier episode cuts. A future re-download may reflect revisions; do not silently replace the included data and retain the old receipt. Create a new research revision and compare changes explicitly.

## 5. Reading the scored JSON

The primary aggregate is:

```text
cohorts.PRIMARY.targets.fed_target_midpoint_net_direction.<1|3|6>.ALL
```

Each group contains `own_coverage`, `pairwise_common_coverage` and `all_three_common_coverage`. For example, `pairwise_common_coverage.M0__M2` has the exact intersection IDs, class counts, regime counts, scores for both models and paired contrasts. Use that intersection when making a comparative claim. `own_coverage` is useful for describing reach and abstention, not for a cross-model ranking on different populations.

The separate secondary target is `first_subsequent_rate_change_within_horizon`. `DEVELOPMENT`, `CHRONOLOGICAL_REPORT` and `REGIME:...` groups are separate slices. `cohorts.ADVERSARIAL_CHALLENGE` is never pooled with the primary sample. `market_targets` reports observed drift availability and zero forecast coverage for the four yield series and all missing market targets.

Brier uses the unnormalized multiclass squared-error sum. Natural-log loss is smaller when the true class receives more probability. At fixed 0.6/0.2/0.2 confidence, these scores are linear transforms of accuracy, so they must not be sold as independent validations. Cluster intervals enumerate whole-regime draws and remain descriptive with at most four clusters. Horizon overlap and purposive selection remain outside what a numerical interval can repair.

## 6. Preserved negative results and exclusions

- All three competing baselines fail on the four-case common intersection at one month because the outcomes are HOLD.
- M0 and M2-min have no incremental difference on their eight shared primary cases.
- C0 beats M2-min at one month on eleven matched cases.
- The June 2023 challenge favors M0 over M2-min at three and six months.
- The conventional-floor gain is entirely one March 2020 episode and disappears when the pandemic regime is omitted.
- M1's five inputs all originate from upward guidance; a representative dovish-inversion comparison is absent.
- The later chronological slice is not an unseen holdout; some model counts are one or two.
- Policy-surprise, DXY, expectation-vintage and sector-relative forecast targets are not scored. Missing inputs do not become neutral or correct forecasts.
- Minute/date documentary certificates do not prove historical served bytes; five parent-linked attachments are quarantined.
- Accepted Treasury buyback allocations do not prove completed settlement. Facility ceilings and backstops do not prove disbursed loans or expenditure.

## 7. Return boundary

`FINALIZATION_CLASSIFICATION: PROVEN_OUTCOME` applies only to the bounded PB-A research return, including its explicitly named data deficiencies. `PB_A_RESEARCH_RETURN_COMPLETE: true`; `PARENT_W1_COMPLETE: false`; `PB_G_INTEGRATION_COMPLETE: false`; `FULL_M2_FORECAST_VALIDATED: false`.

Before this return, the commissioned 24-case reconstruction, frozen comparison and reproducible outcome join were not available through this branch. After it, they are available as a draft research package with immutable freeze evidence and visible limits. The allowed final action is PB-G's review under the existing parent mission. No new Agent OS parent, Policy Watch store, live score, RIC consumer or production lifecycle is created by this research artifact.
