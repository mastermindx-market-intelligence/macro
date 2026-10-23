# Evidence register and reproducibility — K3E standard-Pro audit

**Audit date:** 2026-10-03. **Evidence classes:** `SOURCE_READ`, `INCUMBENT_REPORTED`, `INDEPENDENT_EXECUTION`, `PRIMARY_PUBLICATION`, `VENDOR_PUBLIC_CLAIM`, `PROPOSAL`, and `NOT_VERIFIED`. A current source read does not establish deployed behavior. An independently executed incumbent algorithm is not a separately implemented independent algorithm. The attached report's exported citation tokens are not treated as newly verified references.

This register resolves the IDs in [AUDIT.md](AUDIT.md), [MASTERPLAN.md](MASTERPLAN.md), and [CONTRACTS_AND_EVALUATION.md](CONTRACTS_AND_EVALUATION.md). The mathematical counterexamples and proposed acceptance tests are this audit's reasoning, not published empirical results.

## Original input custody

| User-supplied input | Bytes | SHA-256 |
|---|---:|---|
| `deep-research-report (3).md` | 63,585 | `7367c76f0a58e76765f996cff879dca447af72878f0d2f8a3e8d7ac88996136f` |
| `Pasted text(4).txt` | 29,168 | `9bb97d4e8c583d1a6c9e0454d1100ec5a1c1dc25d6e2f154648df34f581e0e5e` |

Both were read in full and their mounted bytes hashed. They are not republished in this folder: this packet is the independent audit and handoff, not a new copy of the original research. The historical brief's request for Deep Research is part of the input, not the mode used for this review.

## Internal source register

### I01 — accepted-main source and capability ledger

**Class:** SOURCE_READ. Primary source/data pin: Macro `9d3fb88f59af7896d1d6060854a9c8c51af89414`. The [capability ledger](https://github.com/mastermindx-market-intelligence/macro/blob/9d3fb88f59af7896d1d6060854a9c8c51af89414/research/alpha_intelligence/expectation_market_dynamics/CURRENT_CAPABILITY_LEDGER.md) retains the August source-proof status and downstream gates.

The documentation publication parent is separately `7ce8e6dfaaa8b8effed2430e069e1efe73e47fa6` (commit timestamp 2026-10-03T09:42:11Z), tree `1cb3a32dfa0a2c4ca0969f63d59f041e218c9dd0`. The data audit remains bound to the earlier explicit source pin. Do not silently call the measurement a read of any later main. The top-level recursive tree response was truncated; a separately retrieved research subtree was not. No exhaustive repository-wide negative proof is inferred from the truncated tree.

### I02 — active Information→Price continuation

**Class:** SOURCE_READ of current organizational claims. [Macro issue #8309](https://github.com/mastermindx-market-intelligence/macro/issues/8309), created 2026-10-03T06:19:24Z, inspected body updated 2026-10-03T09:39:15Z. Existing operation: `information-to-price-20261003-sol-001`; existing owner: `WS:ALPHA-INTELLIGENCE-INTEGRATION`.

The newer issue body reports active execution and a separately implemented conditional EXP-1 consumer under independent review/repair. This audit did not obtain that child's exact implementation revision, path manifest or live writer receipt. Therefore: active work is reported, not independently accepted as built; a successor must recover that child before another implementation starts. The [08:37 continuation comment](https://github.com/mastermindx-market-intelligence/macro/issues/8309#issuecomment-5967248422) is useful history but is older than the updated body.

### I03 — existing source-acceptance carrier and natural proof

**Class:** SOURCE_READ plus INCUMBENT_REPORTED review/production receipts. [PR #8312](https://github.com/mastermindx-market-intelligence/macro/pull/8312), inspected exact head `63fe5e92d305e34ba8bdd6578ccb56e97076d740`, open/draft/unmerged and HOLD-FOR-SOL. Its [native acceptance record](https://github.com/mastermindx-market-intelligence/macro/blob/63fe5e92d305e34ba8bdd6578ccb56e97076d740/research/alpha_intelligence/expectation_market_dynamics/SRC_A1_POST_REPAIR_ACCEPTANCE_2026-10-03.md) proposes physical-source PASS/PROVEN_LIVE while explicitly limiting economic, rights, identity and public-clock claims.

The record traces scheduled September 25 JBGS partial-after-good and KBH fiscal rollover, and scheduled October 2 UVV unchanged/V superseding observations. It reports full 31-field observation and 13-field attempt preservation, plus a complete 6,776-observation/125-attempt selected session. Those historical parent/introduction comparisons were read, not rerun independently in this review.

The reported successful integration run [37109663073](https://github.com/mastermindx-market-intelligence/macro/actions/runs/37109663073) binds subject `63fe5e92d305e34ba8bdd6578ccb56e97076d740`, tested base `e72c6b85d82e8c0c4578e13c0860d1f68e55869a`, merge `214b0f382946e756ab17c78e8932784d89ed365d` and tree `ee3d044ab7bf17ee73ccb4ae6ea117523fe89e00`. This audit read that receipt; it does not assert independently re-inspected hosted job logs or latest-base release eligibility. Later main movement and the hold remain action-time release questions.

### I04 — incumbent auditor, frozen report and source program

**Class:** SOURCE_READ; selected code subsequently independently executed as V01/V02. All following files are in [the exact #8312 K3E directory](https://github.com/mastermindx-market-intelligence/macro/tree/63fe5e92d305e34ba8bdd6578ccb56e97076d740/research/alpha_intelligence/expectation_market_dynamics):

- `INFORMATION_TO_PRICE_PROGRAM_2026-10-03.md`
- `information_to_price_audit.py` — SHA-256 `ec89a53116081627881dcfc082d4bd9e06de0c2264c315d013ee1136c480bc8e`
- `test_information_to_price_audit.py` — SHA-256 `f46f3a77f92f0f20be38a8520e16de47fad9cf9637e7efd2ef92ef9c678d5d52`
- `INFORMATION_TO_PRICE_AUDIT_2026-10-03.json` — SHA-256 `9191e344d4d10b211a66ccb22f5b5a0a07aa2180aaa2b0ddb08503239a704e36`, 41,276 bytes
- `SRC_A1_OPERATING_RECEIPT_2026-10-03.json` — SHA-256 `2a171848d034a10ae8221f1336b01de3062e611bc133c83868c1d967716d32f0`, 99,529 bytes
- `VERIFICATION_AND_NEXT_GATE_2026-10-03.md`

The earlier report uses input `ff420e6841a2468e4b718340cff240abbef114f1` and cutoff `2026-10-03T06:31:51Z`: 473,200 observations and 8,583 attempts. The [source-census comment](https://github.com/mastermindx-market-intelligence/macro/issues/8309#issuecomment-5966333743) discloses the missing canonical identity/economic/public-clock fields and UNKNOWN rights. Those missing fields cannot be repaired by adding a statistical model.

### I05 — collector performance collision

**Class:** SOURCE_READ. [PR #8064](https://github.com/mastermindx-market-intelligence/macro/pull/8064), inspected head `2fcedafa46b30e5b0fb74b779f72f6116ad9a0ee`, open/unmerged and observed non-mergeable. Its two changed paths are `collectors/equity_revisions.py` and `tests/test_equity_revisions_w2a.py`. Preserve that source custody. Proposed performance improvement and production timing targets in the PR are not independently measured by this audit.

### I06 — original owner and derived-model laws

**Class:** SOURCE_READ. At [Macro audit-pin K3E directory](https://github.com/mastermindx-market-intelligence/macro/tree/9d3fb88f59af7896d1d6060854a9c8c51af89414/research/alpha_intelligence/expectation_market_dynamics), read `MASTERPLAN.md`, `BUILD_SEQUENCE.md`, `EXPECTATION_MODEL_SPEC.md`, `MARKET_MODEL_SPEC.md`, `COUPLING_AND_PHASE_SPEC.md`, `OWNER_AND_REUSE_MATRIX.md`, and source/clock handoffs. The naming boundary and freeze are also in [DEC-K3E-EXPECTATION-MARKET-DYNAMICS-FREEZE.md](https://github.com/mastermindx-market-intelligence/macro/blob/9d3fb88f59af7896d1d6060854a9c8c51af89414/agentos/decisions/DEC-K3E-EXPECTATION-MARKET-DYNAMICS-FREEZE.md).

These define the no-rebuild, source-grain, ownership, abstention and no-financial-authority rules; their existence is not implementation or runtime proof.

### I07 — frozen EVAL-0

**Class:** SOURCE_READ. [EVALUATION_PREREG.md](https://github.com/mastermindx-market-intelligence/macro/blob/9d3fb88f59af7896d1d6060854a9c8c51af89414/research/alpha_intelligence/expectation_market_dynamics/EVALUATION_PREREG.md), [machine preregistration](https://github.com/mastermindx-market-intelligence/macro/blob/9d3fb88f59af7896d1d6060854a9c8c51af89414/research/alpha_intelligence/expectation_market_dynamics/eval0_preregistration.v1.json), adjacent activation receipt, and [schema](https://github.com/mastermindx-market-intelligence/macro/blob/9d3fb88f59af7896d1d6060854a9c8c51af89414/contracts/research/k3e_expectation_market_dynamics_evaluation_prereg.v1.schema.json).

Canonical registration digest stated by source: `986ec117e8517b77e8dece565fd9d9dc169e758beb9d1619acc443e061ef87fd`. The companion contract reproduces the exact v1 thresholds, eras and budget rather than silently replacing them with the report's recommended q=0.05. No outcomes were examined or models trained under this review.

### I08 — Finance Intelligence is a sector product

**Class:** SOURCE_READ. [WS-GMI-FINANCE-INTELLIGENCE.md](https://github.com/mastermindx-market-intelligence/macro/blob/9d3fb88f59af7896d1d6060854a9c8c51af89414/agentos/workstreams/WS-GMI-FINANCE-INTELLIGENCE.md), especially the objective, owned paths and current next-action section. It describes Financial Rails/Market Infrastructure and says `FI_READ_URL = ""`, NOT CONNECTED by design, with shared-foundation dependencies. Those dependency PRs were not individually requalified here. This is a source-routing correction, not a claim that all Finance UI code is absent.

### I09 — existing security-level Terminal consumer

**Class:** SOURCE_READ, not live transport verification. Terminal pin `41b8af2da46614cedd2a485214e53003d4f030fc`; [COMPANY_INTELLIGENCE_WORKSPACE.md](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/41b8af2da46614cedd2a485214e53003d4f030fc/docs/COMPANY_INTELLIGENCE_WORKSPACE.md). It documents `/analysis?symbol=<ticker>&page=intelligence`, same-origin `/api/company-intelligence/<ticker>`, generation-pinned `company_intelligence_context.v1`, context-only authority, field-lineage receipts and existing responsive tests. Extending this seam is a proposal requiring its owner, not a new contract claimed to be already accepted.

### I10 — current forward valuation family

**Class:** SOURCE_READ of the header and implementation entry. [engine/valuation_scenario.py](https://github.com/mastermindx-market-intelligence/macro/blob/9d3fb88f59af7896d1d6060854a9c8c51af89414/engine/valuation_scenario.py), blob `e632f019bb42d1dc200650535f5d1ba217f43d43`. It documents a fixed earnings-multiple scenario family, exact real loader fields, no debt bridge on a P/E valuation, and outstanding—not diluted—share inputs. No DCF, physical distribution or universal inverse engine is inferred from this module. Further sibling/path census is assigned before extension.

### I11 — existing VEND-0 sample, not a new procurement decision

**Class:** SOURCE_READ. [VEND_0_INSTITUTIONAL_ESTIMATES_BAKEOFF_2026-08-23.md](https://github.com/mastermindx-market-intelligence/macro/blob/9d3fb88f59af7896d1d6060854a9c8c51af89414/research/alpha_intelligence/expectation_market_dynamics/VEND_0_INSTITUTIONAL_ESTIMATES_BAKEOFF_2026-08-23.md), companion `VEND_0_EVIDENCE_LEDGER_2026-08-23.json`, `VENDOR_BAKEOFF_PROTOCOL.md` and `handoffs/VEND_0.md`.

The frozen sample has 30 issuers (12 US, 8 Europe, 6 APAC, 4 Canada/other), non-calendar fiscal, inactive, corporate-action and share-class cases; 10 fixed historical as-of dates; EPS/revenue and a KPI where offered; correction, clock, contributor, null and rights probes. Four credible candidates remain unsampled and rights-unverified in that record. The packet expressly does not authorize contact, trial activation, purchase or confidential-data commitment. Public capability checks below do not change that status.

### I12 — current Linear projections

**Class:** SOURCE_READ of projections, not canonical implementation proof. Live reads of [MAS-118](https://linear.app/mastermindx/issue/MAS-118) and [MAS-119](https://linear.app/mastermindx/issue/MAS-119) returned In Review and Backlog respectively. MAS-118 describes a completed scientific return, missing canonical GitHub closeout and an unstarted successor source census. No projection was modified.

### I13 — governing-source recovery

**Class:** SOURCE_READ. Mastermind governing pin observed `20adcaf65c2dd1bb734ab06e215feb1a0eb65659`; [Skillpack INDEX](https://github.com/mastermindx-market-intelligence/Mastermind/blob/20adcaf65c2dd1bb734ab06e215feb1a0eb65659/docs/sol_skills/INDEX.md), [COLD_START](https://github.com/mastermindx-market-intelligence/Mastermind/blob/20adcaf65c2dd1bb734ab06e215feb1a0eb65659/docs/sol_skills/COLD_START.md), and [ACTIVE_EXECUTION](https://github.com/mastermindx-market-intelligence/Mastermind/blob/20adcaf65c2dd1bb734ab06e215feb1a0eb65659/docs/sol_skills/ACTIVE_EXECUTION.md). These reinforce recovery, source custody and effect-scoped gates. Astra must read current applicable release/admission procedures before modifying existing carriers; a dated handoff does not waive them.

## Independent execution receipts

### V01 — current pinned raw-pair audit

**Class:** INDEPENDENT_EXECUTION of I04's unchanged incumbent auditor, not a second algorithm. Source pair downloaded from the same explicit I01 commit through GitHub blob identities and decoded as actual parquet bytes in a task-local scratch directory.

| Input | Git blob | Bytes | SHA-256 |
|---|---|---:|---|
| `data/revisions/expectation_observations.parquet` | `164919cf4c33e53ca7fcb8dad6e83bd4771b2ad1` | 37,020,102 | `3db55f485c01bd307f1419ff04f392ae5f1994d2e7d8071b977abe9bbb562b93` |
| `data/revisions/expectation_attempts.parquet` | `461f5b6312a64a236fb29a504091583f8ee3b23f` | 1,170,213 | `0e0bacc450ca21e93316f80a157095994eec08fc224775614afc5e90c760d89f` |

Executed with `python3 -B`, I04's `information_to_price_audit.py`, `--as-of 2026-10-03T06:31:51Z`, and explicit `--observations-path` / `--attempts-path` to that scratch pair. **Exit 0.** Output reports 473,200 observations; 8,587 attempts; 400,509 finite values; 72,691 true NULLs; 400,482 structurally eligible declared-capture rows; 66,860 central average/median rows; 24,612 absent period anchors. The authoritative measured summary is also in [AUDIT_RECEIPT.json](AUDIT_RECEIPT.json).

The local-file auditor reports stable-read byte hashes, not Git-history attestation: its own provenance has `mode=local_parquet`, `source_revision=null`, and explicitly says shared historical origin is unverified by that local reader. The same-commit Git assembly evidence above is separate. Observation bytes match I04's prior frozen snapshot; attempts differ. We did not complete an independent row-diff of the four additional attempts and do not certify append-only history from the count difference.

All reported financial-authority flags are false; historical availability is not verified; readiness is `DIAGNOSTIC_ONLY`. Long-form row counts are not analyst counts, distinct economic episodes, licensed use or economic eligibility. Nonexclusive dimension flags cannot be summed.

### V02 — unchanged audit and companion tests

**Class:** INDEPENDENT_EXECUTION. Exact I04 audit/tests and acceptance companion, with the current source collector and its actual `lib/config.py`, `lib/nyse_calendar.py`, `lib/__init__.py` dependencies copied to isolated scratch.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=<isolated-source-root> python3 -B -m pytest -q \
  -p no:cacheprovider --noconftest \
  research/alpha_intelligence/expectation_market_dynamics/test_information_to_price_audit.py \
  tests/test_equity_revisions_src_a1_acceptance.py
```

Result: **34 passed, 4 warnings, 1.02 seconds; exit 0**. These are 23 auditor cases plus 11 acceptance-companion cases. Companion SHA-256: `1e1f9b0128713d99e1b96904d41df88114f04533220385a7ee4113d3b6522a2b`.

An initial scratch test collection failed because `lib` had not yet been copied. Fetching those exact source dependencies resolved the environment issue without modifying application code. Four warnings concern pytest cleanup of unrelated prior Chromium temporary directories with permission errors; no permission workaround or cleanup retry was performed. No provider request or dependency installation was used. The separate incumbent 34-case legacy subset/6 deselections in I03 was not independently executed here.

### V03 — verification boundaries and negative results

A redundant hand-written pandas count probe failed on its own assumed `ticker` column name; that is not a source-data defect or a second count validation. A later auxiliary inspection request was blocked before execution and was not retried. The successful incumbent auditor and test results above remain the executed evidence.

Not independently performed here: full historical parent/introduction row comparisons; adjudication/release of #8312; full latest-base hosted CI log inspection; exact EXP-1 child implementation review; complete all-owner deployment census; live Terminal transport; vendor sample or contractual rights review; academic replication; held-out financial-outcome testing; model training; procurement; source/data modification; production deployment; Executive/worker dispatch. The full transient raw auditor stdout is not claimed as an attached file; this folder preserves its bounded measured receipt and immutable rerun inputs/code references.

## Primary external evidence register

Accessed during the 2026-10-03 standard-mode audit. Most empirical checks are primary publisher/NBER/author abstracts or official documentation, not full independent replications. Dates below distinguish paper vintage from this access date. Vendor pages describe products, never Mastermind entitlements.

| ID | Primary source | Supports; limit |
|---|---|---|
| E01 | Breeden & Litzenberger (1978), [Prices of State-Contingent Claims Implicit in Option Prices](https://www.gsb.stanford.edu/faculty-research/working-papers/prices-state-contingent-claims-implicit-option-prices) | State-contingent pricing relation; not an automatically physical forecast or arbitrary raw-chain density. |
| E02 | de Vincent-Humphreys & Noss (2012), [Bank of England WP455](https://www.bankofengland.co.uk/working-paper/2012/estimating-probability-distributions-of-future-asset-prices) | Risk-neutral/real-world distinction and model-based transformation; no automatic local calibration. |
| E03 | Damodaran, [Growth in valuation](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/valquestions/growth.htm) and [terminal value and excess returns](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/valquestions/termvalueexreturns.htm) | Reinvestment/return-on-capital and terminal assumptions; not a recommended security valuation. |
| E04 | Pan & Poteshman (2006), [RFS DOI](https://doi.org/10.1093/rfs/hhj024); [NBER WP10925, 2004](https://www.nber.org/papers/w10925) | The cited flow construct depends on buyer-initiated opening volume; a generic quote-side estimate is not a reproduction. |
| E05 | Benjamini & Yekutieli (2001), [author-hosted paper](https://www.math.tau.ac.il/~ybenja/depApr27.pdf) | Dependence matters for FDR procedures. PDF first page inspected visually; no claim it repairs biased sampling or invalid p-values. |
| E06 | Hou, Xue & Zhang, [NBER WP23394, Replicating Anomalies](https://www.nber.org/papers/w23394) | Substantial non-replication under their standardized implementation choices; not a universal failure probability for K3E. |
| E07 | Chen & Zimmermann, [Open Source Asset Pricing, published DOI](https://doi.org/10.1561/104.00000112); [Federal Reserve FEDS 2021-037](https://www.federalreserve.gov/econres/feds/files/2021-037pap.pdf) | Extensive faithful replication of original predictors; complements rather than simply refutes E06. PDF cover inspected visually; abstract/method framing, not independent empirical reproduction. |
| E08 | McLean & Pontiff (2016), [Does Academic Research Destroy Stock Return Predictability?](https://onlinelibrary.wiley.com/doi/full/10.1111/jofi.12365) | Out-of-sample and post-publication decay; no local return claim. |
| E09 | [FactSet PIT Consensus overview](https://insight.factset.com/resources/at-a-glance-factset-estimates-point-in-time-consensus?hs_amp=true); [LSEG I/B/E/S official learning material](https://www.lseg.com/en/training/learning-centre/learning-paths/learning-path-for-data-solutions/learn-about-quantitative-data-solutions/learn-about-data-and-content/learn-about-ibes) | Official estimates-history/consensus product claims; record-level sampling and use rights remain required. |
| E10 | [OptionMetrics IvyDB US](https://optionmetrics.com/united-states/) | Official EOD options/model/surface capabilities; not evidence that every current K3E input is certified or licensed for display. |
| E11 | [ThetaData option historical trade/quote endpoint](https://docs.thetadata.us/operations/option_history_trade_quote.html) | Documented trade and quote observations do not by themselves establish opening-position or observed dealer-inventory fields. |
| E12 | Chan, Jegadeesh & Lakonishok, [Momentum Strategies, NBER WP5375](https://www.nber.org/papers/w5375) (1995 WP; 1996 publication) | Historical return/earnings information and sluggish updating; no untested modern incremental-alpha inference. |
| E13 | Livnat & Mendenhall (2006), [Comparing PEAD for analyst and time-series forecasts](https://doi.org/10.1111/j.1475-679X.2006.00196.x) | Choice of expectation baseline changes measured drift; distinguish absolute from relative drift. |
| E14 | Diether, Malloy & Scherbina (2002), [Differences of Opinion and the Cross Section of Stock Returns](https://doi.org/10.1111/0022-1082.00490) | Analyst dispersion/disagreement interpretation; not a generic physical uncertainty distribution. |
| E15 | DellaVigna & Pollet, [Investor Inattention and Friday Earnings Announcements, NBER WP11683](https://www.nber.org/papers/w11683) (2005 WP; 2009 publication) | Historical attention/earnings-response evidence; no universal underreaction probability. |
| E16 | Clement, Lee & Ow Yong (2019), [A new perspective on PEAD: Using a relative drift measure](https://doi.org/10.1111/jbfa.12401) | Smaller analyst-based drift ratio can coexist with larger absolute drift; prevents an overbroad inference from E13. |

No exact vendor cost, delivered analyst-detail capability, storage/display/training entitlement or current local alpha is inferred from these sources. The original report's broader named professional products are not all newly reviewed here. That scope remains explicit rather than being filled with unsupported claims.

## Evidence-to-decision trace

A01 depends on I01–I05; A02 on V01/I03–I04; A03 on I08–I09; A04–A05 on I06–I07/V01; A06–A08 are mathematical corrections to the supplied report's PAE proposals; A09 depends on I10/E03 and explicit accounting reasoning; A10–A12 use E01–E04/E10–E11; A13 is fixed by I07/E05; A14 compares E06–E08/E12–E16; A15 is the proposed product/scientific completion distinction. Every implementation phase in MASTERPLAN.md has its own acceptance evidence instead of inheriting authority from this register.
