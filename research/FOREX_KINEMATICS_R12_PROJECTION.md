# Forex R12 — existing kinematics to the machine snapshot

**Source candidate; not deployed and not a new user-interface release.**

Parent: Macro #8147. Operation: `bonds-forex-research-design-20260928-sol-c1-001`.
Base: `7502eac2d65e4adc6bbc134de5474d6f56ae117e`.
Branch: `claude/forex-kinematics-r12-20260930-sol-c1`.

## Capability and existing owners

`engine.forex_regime.fx_kinematics_table` already computes literal currency moves, velocity/acceleration, volatility percentiles and ex-dollar residuals. The Forex builder already passes that table to its template but previously omitted it from `data/forex/latest.json`. This slice adds one **kinematics** member to that existing snapshot using a pure, standard-library projection. It does not create a new engine, endpoint, publication, score, freshness rule or state setter.

The original template context is unchanged. The display module does not recompute the financial measures, derive a carry-unwind verdict, rank currencies, create a trade or set portfolio exposure. Its only numeric processing validates existing scalars and makes their JSON representation finite. Missing values are null, not zero. The existing alert and market-state code is untouched.

This is a machine-consumer connection, not evidence that the new data already appears on the deployed Forex page or that a downstream trading model uses it. The existing dashboard and Paper visual design are preserved.

## Additive member

`latest.kinematics` contains:

- `version: 1`, `producer`, `display_only: true` and a fixed currency-vs-USD sign convention.
- `table_as_of` and `date_basis: producer_max_index`.
- `freshness: unknown`, `metric_dates_available: false` and null per-field `observed_at` values.
- `metrics`: units, source field names and actual configured window metadata.
- `rows`: distinct valid currency identities, values and availability classifications.
- `reference_rows_excluded`: the producer's USD broad-dollar-index reference is explicitly excluded; it is not a USD-versus-USD currency return.
- `issues`: rejected optional payload/configuration or identity conditions.
- `value_status: complete | partial | unavailable`, which describes only numeric payload completeness. **Complete does not mean fresh, comparable in time, accurate as a forecast or ready for a trade.**

| Projected metric | Existing field | Unit | Meaning |
|---|---|---|---|
| `return_short` | `lit_1d_pct` | Percent | First configured literal window |
| `return_medium` | `lit_5d_pct` | Percent | Second configured literal window |
| `return_long` | `lit_20d_pct` | Percent | Third configured literal window |
| `velocity_z` | `vel_z` | Standardized z-score | Existing five-index-step velocity, with the configured normalization metadata |
| `acceleration_z` | `accel_z` | Standardized z-score | Existing change in the five-index-step velocity |
| `volatility_percentile` | `rvol_pctile` | Fraction, 0–1 | Existing realized-volatility percentile, with window/lookback metadata |
| `residual_return` | `resid_5d_pct` | Percent | Existing five-index-step ex-dollar residual return |

The legacy producer's literal column names do not change when configuration changes. Consequently, the new projected keys are not named 1d/5d/20d; consumers must read `window_observations`. These windows refer to steps in the producer's aligned, weekday-filtered index—not elapsed calendar days or a guarantee that every original source had a new observation at each step.

The actual builder supplies the same explicit configuration to the producer and projector. The projector has no second default-configuration table. Missing, non-integer, boolean, nonpositive or ambiguous ordered windows withhold this optional member. The two producer-fixed five-step computations are documented as such, not re-estimated.

## Time and provenance limits

The producer takes the last non-null reading for each metric independently and publishes the maximum table-index date. Those readings can therefore be from different dates. It supplies no field-level observation, release or ingestion timestamps. This projection preserves the table date but does not stamp it onto the metrics, refresh it with the builder's date or infer daily freshness.

A usable current-state consumer must obtain the missing source clocks through their existing producers before claiming synchronized/current evidence. No new expiry threshold or source-health service is introduced here. The projection deliberately does not forward the producer's qualitative movement label as a fresh market interpretation.

Percentiles and currency moves use different scales:0.91 is a91st-percentile fraction, not a0.91% price move. Z-scores are neither probabilities nor percentages. Correlated kinematics are not independent confirmation votes. These are coincident descriptions, not a demonstrated predictive edge.

## Failure and identity behavior

A missing/nonmapping table, absent/invalid table date, malformed rows or invalid configuration yields a diagnosed unavailable/partial payload without inventing observations. Invalid optional currency rows are isolated. Ambiguous duplicate currency identities produce one quarantined row whose values are all null; neither the first nor last conflicting row wins.

Booleans, text masquerading as numbers, nonfinite readings and out-of-range percentile fractions are unavailable. A legitimate numeric zero, negative currency return, and percentile endpoints0/1 remain real values. The projector copies values without mutating the producer table or configuration.

A numpy/non-scalar currency identity is rejected before equality comparison, so it cannot crash the optional projection. Only the separate USD broad-index reference is excluded without reporting it as a broken currency observation.

## Ownership and collision boundary

The existing R4 currency/readiness PR #8096 remains its owner. This change does not copy, consume or rewrite `_r4_currency_rows` or `_r4_readiness`. The builder change is one import and one final snapshot assignment; #8096's helper insertion is a separate hunk. Its reviewed defects and merge conflict remain independent obligations.

No change to `templates/forex.html.j2`, `templates/theme.css`, `engine/forex_regime.py`, `engine/forex_signals.py` or the Bonds #8241 worktree. The context-bus tests remain in their existing suite, and its existing `unrun-macro-panels` CI job gains only the new module dependency path. No new workflow, Node version or test waiver.

## Verification on 2026-09-30

Red observations:
- Initial new projection tests could not import the absent module.
- After fixing a test-only missing archetype fixture, the actual builder tests failed because `kinematics` was absent from its written JSON (Studio PID52418).
- A real-producer regression exposed that USD's broad-index reference was incorrectly treated as an invalid currency row (PID55520); it is now explicitly excluded without marking valid currencies broken.
- A non-scalar identity regression raised before the type check (PID59276); it now yields diagnosed unavailability.

Final scoped command (PID60304, exit0):

```sh
python3 -m pytest tests/test_forex_context_bus.py tests/test_build_forex_stance.py \
  tests/test_forex.py tests/test_b3_forex_consumer.py -q --tb=short
```

**152 tests passed**, including45 R12 cases and107 pre-existing cases. Two NumPy divide warnings occurred in the existing `test_calibrate_pair_signs_inverted_and_normalizes` fixture; no failure was omitted. Compilation and `git diff --check` passed. The canonical manifest loader accepted239 jobs and confirmed the existing source/test owner.

One regression executes the real kinematics producer with synthetic price/residual series and compares every projected value with its actual returned field. Actual-builder tests invoke `build_forex.main()` and read the JSON it writes in temporary directories. Market engines, optional state writers and HTML rendering are substituted boundaries: this is not a live-data acquisition, nightly production run or browser proof.

A separate immutable-base comparison (PID58342, exit0) executed the actual base builder source against the candidate with identical test inputs. **The only added top-level member was `kinematics`; all16 previous members were unchanged**, including `stance`, `fx_state`, `regime_radar`, dollar context and pairs. The original template kinematics argument also remained unmodified. No production output or market data was written.

## Release and remaining work

Independent review and exact-head hosted checks are still required. This source-only projection does not discharge Bonds' separate browser-evidence gate or any Forex visual acceptance requirement. Do not fabricate an EVIDENCE.yml, duplicate the older readiness implementation, or relabel unknown field clocks as fresh to complete a dashboard.

After source acceptance, use the existing admitted Forex build/publication chain. A later bounded UI/API consumer may use this member while preserving its units and unknown clocks. Sourced per-metric timestamps belong to their existing data producers and need their own verified implementation. No merge, deployment, scientific forecast or trade authority is granted by this document.

## Final source/contract qualification

- Studio PID62736, exit0: full `python3 scripts/check_contract_delta.py --base 7502eac2d65e4adc6bbc134de5474d6f56ae117e` returned **0 introduced / 0 inherited findings**. All three existing workload probes were unchanged and inside their ceilings. The source/test/manifest set was held stable during the check.
- PID65089 detected **five deliberately introduced in-memory defects**: false freshness, boolean-as-price, first-duplicate-wins, erased horizon definitions and percentile-as-percent. Original source files were not modified. This is not independent human/worker review.
- PID66543 exercised **238 mixed-type boundary cases** with0 uncaught exceptions,0 non-JSON outputs and0 currentness/score outputs. These are type/contract checks, not market backtests.
- PID63518: current main still7502eac2d65e4adc6bbc134de5474d6f56ae117e, material dependency paths and owning CI job unchanged. A temporary three-way merge of the builder with exact sibling #8096 head e0cf9c7d7d6ab16695df705b20128c17727b626e had no hunk conflict. The sibling helpers were not adopted or waived; their review and source custody remain separate.

Tested source SHA-256s:

| Path | SHA-256 |
|---|---|
| `lib/forex_kinematics_view.py` | `f86d9d616bfd9afcb3b6cb2a43f438763e50f6b5856bbd4474376c04d3e1b948` |
| `scripts/build_forex.py` | `3f026c00151a51d0428a9bdcf567ab9ba9cd1cbc6b2c8ae9aadd962fe2bfa44d` |
| `tests/test_forex_context_bus.py` | `b2ac7c33857265416e6045fd761a8b812c7f978d9a6df58352d89c0a9f8121a9` |
| `.github/ci/legacy-jobs.yml` | `f5f42a678f67e4b18984d90234e693566a89ba4325ad9eeecae30e344b5eddf7` |

No full-repository local test pass, production consumer activation, source-age validation, browser proof or independent review is claimed. Exact-head hosted CI and review are still owed before release.


## R13 continuation — calculation-index dates, not vendor clocks

This section supersedes only the statement that no per-metric **calculation** dates exist. Source observation and release/ingestion clocks remain unavailable. The R12 numeric field definitions, missing-value policy and display-only fence remain unchanged.

The existing `engine.forex_regime.fx_kinematics_table` now attaches a versioned `calculation_clock` to each output row. Its `selected_index_dates` map names the exact derived-series index selected for each legacy numeric field. The unchanged literal-return formulas, velocity/acceleration, volatility percentile and residual calculations still use their original last-non-null selection and rounding. `normalized_input_dates` separately records the last finite close/residual-return input index when available.

These are not real-time source observations. In the existing normalization chain, broad-dollar drivers can be forward-filled and residual returns can be zero-filled or equal raw returns before the rolling beta is estimable. A recent derived-series date therefore does not prove a recent vendor observation, available-at timestamp, fitted residual, or tradable synchronized state. This change does not modify that chain or its numerical behavior.

The existing projector forwards validated dates as `rows[].calculated_through`, with `index_relation` equal to `at_table_date`, `before_table_date`, or `unknown`. Top-level `calculation_date_status` describes only date coverage; complete coverage can still contain multiple different dates. Source `observed_at` entries remain null, `metric_dates_available` remains false, and `freshness` remains unknown. Unrecognized/malformed date receipts never supply an observation date or overwrite valid numeric values. Dates after the table date are rejected; unknown vendor timestamps are not copied through. Duplicate/missing-value rows cannot acquire a valid clock simply because a timestamp was supplied. Legacy clockless tables retain numeric compatibility with unknown calculation dates.

### R13 proof before publication

- Initial R13 tests: **27 failed** before implementation (Studio PID75466), specifically because selected dates were absent.
- A further malformed array-valued basis regression failed at PID85188; a string-type check now rejects it before comparison.
- Final scoped run PID87189 exited0: **184 tests passed** across the existing context-bus/stance/Forex/B3 suites (32 added R13 cases). Two existing NumPy divide warnings remained in the calibration-sign fixture; a separate pytest cleanup warning referred to an unrelated protected old temporary Chromium fixture. That folder was not modified or used for browser execution.
- The exact old producer from commit `043d4fc527a69b5ddd6a4d5829f5a93b2efabd3e` and the candidate were executed with15 deterministic synthetic missing-tail combinations. Across30 output rows, **every pre-existing numeric/label/key value was unchanged** when the additive clock was removed.
- AST/function-body comparison confirmed only the existing `fx_kinematics_table` body changed, plus one `_selected_index_date` helper. Shared scenario, intensity, state-label and feature functions remained unchanged.
- Tests cover holes affecting different return horizons, currencies lagging a newer broad-dollar table, separately older residual values, absent residuals, invalid/future dates, fake source clocks, legacy payloads and actual builder JSON write-through. The actual writer fixture still substitutes external input/state/render boundaries; no live nightly build or browser proof is implied.

The same PR and worktree retain source custody. No parallel clock service, scoring rule, readiness owner, source collection, template, trading or deployment change is introduced by this date-only phase. A UI may expose calculation-date disagreement but must not convert it into a freshness verdict.

R13 final contract check: Studio PID380 exit0, full `scripts/check_contract_delta.py --base 7502eac2d65e4adc6bbc134de5474d6f56ae117e` returned **0 introduced / 0 inherited**; all existing workload probes stayed within their ceilings. Current-main comparison at0c7ec71ba502aca98bfd03c851ea22fa75f4e5e2 found no affected source/producer/test changes; the existing `unrun-macro-panels` job was byte-equivalent as a parsed object. No ancestry-only merge/rebase was performed. PID9910 detected5/5 in-memory mutations (future date accepted, table date replacing the selected date, invented source observation, boolean clock version, date rescuing a missing value); no source files were changed by those probes and no independent review is implied.


## R13 consumer phase — actual Forex route, read-only movement evidence

The same validated `kinematics_view` now feeds **both** the existing Forex template and `latest.json`. It is computed once in `scripts/build_forex.py`; the source producer is not called again and no UI-side formula or inferred freshness rule is introduced.

A native HTML disclosure, **Movement evidence**, is included between the existing Stress watch and The pairs sections. It lets a reader expand each currency, inspect all seven measures with their correct units and configured windows, compare selected calculation dates, and see unavailable values or ambiguous identities without zero substitution. A recent table date never upgrades an earlier metric to current. Source freshness and vendor observation/release times remain explicitly unknown. Broad-dollar-adjusted returns are labelled as adjustments rather than causal attribution; correlated measurements are not independent confirmations. The inspector cannot activate a carry scenario or declare funding normal.

This advances the actual user-facing route rather than another standalone prototype. `templates/_forex_movement_evidence.html.j2` uses the existing typography/spacing/colour roles, open fact rows, progressive disclosure and the accepted native Paper R11 dated-evidence hierarchy. The original Paper evidence-row JSX at file01M2WGNCX9475G79JRKJTCM08P/node5LN6-0 was inspected for structural/token alignment. No native design mutation occurred: current Mastermind_Paper advertises0.5.14 with write admission still pinned to0.5.12, reported to the existing integration owner at Mastermind#1011/comment5922168754. That gate is not a data-loss warning and was not bypassed.

No JavaScript, input, market-state setter, storage or network request is added by the disclosure. Native HTML `details/summary` supplies the interaction; actual keyboard/screen-reader/visual behavior remains to be proven in an admitted browser. Source styling declares desktop three-column facts, two-column tablet facts and stacked/mobile label-value rows, with44px summary targets, focus-visible and reduced-motion rules. This is source coverage, not pixel acceptance.

### Source overlap and tests

- Existing #7409 owns a three-line dark tooltip CSS correction nearline108. The new include is nearline652 and all new styles are scoped to the new partial. PID38680 executed a temporary three-way merge with exact siblinga6ba169c4fafd7aaf1d09e30aea49747b65e3c92; both changes compose cleanly. No sibling code was adopted and its writer/review gates remain intact.
- Existing #8096's readiness/currency-row helper insertion remains untouched, with its earlier independent source findings still outstanding.
- The existing `unrun-macro-panels` CI owner now explicitly includes the parent Forex template and the new partial in its path closure. No new job or waiver.
- Initial consumer tests PID15852:7failed because the include, markup and shared projection were absent. After implementation, the same7 passed. The full-page test initially exposed a missing `factor.value` in the older JSON-only synthetic fixture; only that test fixture was completed, not the product model.
- PID38680 exit0: **195 tests passed**, including11 new consumer cases in addition to the32 clock cases and the existing152 checks. Same2 NumPy divide warnings and unrelated old pytest cleanup warning; no hidden failure.
- The complete real Forex template renders with the captured actual-builder context, the actual dollar view-model and bounded synthetic inputs. It contains one evidence disclosure alongside the existing pair/scenario content. Another test runs real `lib.pages.write_page` and the existing CSS externalizer against temporary component output, confirming the dated rows and both languages survive, with one content-hashed stylesheet and its exact bytes. No production render, data collection or browser run was performed.
- Tests cover mixed dates, correct percent/z-score/percentile units, genuine zero, missing values, legacy clockless data, custom windows, duplicate/hostile currency identity, explicit unknown source clocks, real builder/page snapshot equivalence and source-only interaction boundaries.
- Actual design-ratchet `enforce-added` at PID28554 returned0 introduced violations. Its estate-wide historical findings are not introduced by this component.

**Release remains HOLD:** the new material UI requires its own truthful browser evidence/independent review, not a borrowed Bonds receipt or Paper screenshot. No `EVIDENCE.yml` with invented passing outcomes is included. All previously published non-deployment and live-source limits remain in force.

Final consumer-phase gates: full contract-delta at Studio PID46533 exited0 with **0 introduced / 0 inherited findings** and unchanged workload ceilings. Full Forex template → real page writer → real asset extractor also ran as one path at PID52403: one evidence inspector, existing pair content retained, selected earlier metric date preserved, zero component scripts, exactly one component stylesheet SHA256 `b9b73065256ea260677d35b1212d6a37f8453cee4923e4aefeeb5adb93dffd90`. A second extraction produced byte-identical output. This uses synthetic inputs and temporary output, not the deployed site. Independent review, native visual parity, real browser interaction, measured contrast/overflow and a truthful owning visual-evidence receipt remain outstanding.


## R14 — adjustment method must be evidenced, not inferred from the field name

A real-source synthetic reproduction at R13 head `fc34971a432d36ac4bee1b9a998f32500d6ebc18` found that `orthogonalize(price, None, cfg)` returns the raw currency index with no fitted beta, but the projection/UI still described its −1.00% five-observation return as ex-dollar/dollar-adjusted. The numerical fallback is intentional existing behavior; the unconditional display interpretation was wrong. This is a source-candidate finding, not a claimed live market incident.

The existing adjustment calculation now has one internal implementation which returns its unchanged residual/beta plus per-return method annotations. The public `orthogonalize` interface remains exactly two Series. `compute_asset` appends `residual_method` and `residual_dollar_carried` only after its existing factor/score assembly. No alternative estimator, factor weight or scenario rule was added. A valid zero coefficient remains a fitted adjustment. Raw fallback, producer zero-fill and unknown evidence are distinguished.

`fx_kinematics_table` attaches a five-selected-return receipt from those exact origin annotations, bound to the currency/pair and selected index window. It cannot borrow the newest row's method, infer a fit from the residual field name, or accept missing pair identities merely because nullable comparisons skip missing values. The projector validates receipt version, owner, pair/currency, window, nonboolean counts and correspondence to the already-qualified calculation end date. Missing/invalid method evidence does not erase an independently valid number; it withholds the adjustment claim.

The residual metric's general basis is now **upstream_residual_index**, superseding R12's unconditional **ex_dollar_residual** interpretation. Each row's `residual_adjustment` has one of: adjusted, raw_fallback, mixed, input_gaps, unverified or unavailable. Numeric values/units are unchanged. Unknown vendor observation and availability clocks remain unknown regardless of method completeness.

The existing HTML inspector chooses **Broad-dollar-adjusted move**, **Unadjusted fallback move**, **Partly adjusted move**, or a neutral **Residual-index move** according to that validated evidence. Zero-filled returns and carried dollar inputs are explicit qualifications. There is no new interaction, JavaScript, score, direction setter or probability.

Verification during this phase:
- Initial31 R14 tests failed before implementation; then31 passed. Two inherited assertions were corrected because they enforced the old unconditional method label while their fixtures had no method evidence.
- Exact immutable R13 `orthogonalize`, `compute_asset`, and kinematics producer were executed against the candidate for15 synthetic configurations (64/260/760 observations × raw/adjusted/zero-beta/gap/carried inputs). Every legacy Series, asset column, metric value, label and calculation date was exactly equal after excluding the additive annotations/receipt.
- Full scoped run PID26101 passed226 checks. A subsequent nullable-identity probe found that an all-missing StringDtype pair column could pass `.eq(pair).all()`; the new three-case regression failed2/3 before adding the explicit `.notna().all()` guard.
- Full canonical contract-delta PID32674:0 introduced/0 inherited, all existing workload ceilings unchanged. It preceded only that final identity guard and its same-owner tests; current-head hosted checks and the complete final local suite remain separately recorded.
-144 mixed-type receipt probes produced no exception/non-JSON output or false source-freshness claim. Probe execution changed no source files.

All previously recorded browser, native-Paper-adapter, independent-review and release gates remain. This source candidate is not deployed and does not prove predictive advantage.

Final R14 method-phase verification, PID46299 exit0: **229 tests passed** (the195 prior checks plus34 new method/identity cases). The existing two NumPy warnings and unrelated protected pytest-temp cleanup warning remain disclosed. Four temporary in-memory mutations were detected: raw promoted to adjusted, zero beta discarded, nullable pair identity accepted, and mismatched window accepted. Those probes changed no source files and are not independent review. Full contract coverage/probe ceilings remained as recorded above; real browser evidence is still absent.


## R14 continuation — price direction, relative momentum and a usable comparison

The interrupted continuation was recovered without resetting its three owned dirty files. Its earlier method repair is already published at `cb644708a85f10d2b14ea23987bf69fe149c60da`; that source remains the immutable comparison baseline for this change. No separate branch, prototype or market engine was created.

### The interpretation defect

The actual producer can emit a falling five-observation currency return together with a positive velocity z-score. A deterministic synthetic reproduction gave a −0.19% return alongside +1.51 z relative momentum. This is not contradictory: `_velocity` is mean log return over five observations divided by EWMA volatility, and `_z_causal` compares that measure with its own strictly earlier rolling mean/standard deviation. A positive standardized deviation can accompany a still-negative return. `_accel` is the one-observation change in that underlying momentum measure; its z-score likewise is not a price-direction sign.

The former blanket caption, “positive means currency appreciation,” is now restricted to literal returns. Metric definitions publish their distinct `positive_means` values; acceleration names its one-observation change horizon; z-scores name the earlier-observation comparison and existing ±8 bound. The existing UI labels become **Relative momentum** and **Relative change in momentum**, with bilingual explanations. Volatility rank is not a direction signal, and the residual-index sign must be read with its adjustment-method evidence. The legacy top-level direction field remains for compatibility, but `positive_direction_scope=literal_returns_only` makes its scope explicit. Financial calculations and source scenario/weight rules do not change.

Malformed z-score payloads outside the actual producer's ±8 bound now remain unavailable. They are not clamped into apparent valid readings. Real endpoint values −8 and +8 are preserved.

### From definitions to useful reading

The existing projector now derives one bounded, descriptive `movement_comparison` per currency. It matches the configured literal-return window to the momentum measure's five-observation window instead of assuming the fixed producer field name determines the horizon. It requires two valid values and matching, qualified selected calculation dates. It then describes the literal return direction and relative-momentum baseline separately.

The existing inspector uses that same projection for **How to read this combination**, for example:

> The currency fell versus USD over 5 observations. Relative momentum is above its prior baseline.

The selected calculation date, unknown source freshness and “not a reversal signal or independent confirmation” boundary remain alongside the explanation. Displayed zero is qualified as flat/at-baseline **at displayed precision**, not an exact assertion about unrounded market measurements. The combined text is not a predictive model, trade recommendation, independent confluence vote, current-market status or synchronized-source guarantee.

If the windows differ, calculation dates differ or are unknown, or a value/identity is invalid, the UI instead says **Read these values separately** and names the local reason. The independently valid metrics are preserved. Injected upstream comparison narratives are ignored; only this projector's validated values and definitions supply the descriptive state. No new JavaScript, CSS, interaction, storage, collector or API is added. The single existing builder projection still supplies both HTML and `latest.json`.

### Verification on the repaired candidate

- Recovery PID58960 exited0 with238 scoped passes (229 previously published cases plus9 recovered sign-meaning cases).
- New comparison tests were written before implementation: PID66066 failed21/21 on the absent comparison/consumer. After implementation, PID67466 passed259 scoped checks.
- Six bounded-z cases then exposed four actual failures at PID69257 (out-of-bound values wrongly available), with two positive endpoint controls passing. `_value` now rejects that invalid payload without clamping.
- **Final PID70801 exited0:265 scoped tests passed**, Python compilation and diff check clean, followed by the complete canonical contract-delta check: **0 introduced /0 inherited findings**, all existing workload probes within their ceilings. The same2 inherited NumPy divide warnings and1 unrelated protected pytest temporary-directory cleanup warning remain disclosed; that directory was not modified or used for browser execution.
- PID75005 exited0:60 combinations of windows/signs/calculation-date mismatch compared against the exact cb644 projector. Every pre-existing value, date, adjustment receipt and key remained equal for valid producer-range inputs; input objects were unchanged. The new intentional rejection of malformed out-of-bound z payloads is not represented as legacy parity.
- Four in-memory mutations (ignore date disagreement, reverse price direction, treat momentum as price, accept invalid z bound) were distinguished by the targeted semantic checks. These are local adversarial checks, not independent review or a whole-program mutation score.
- PID80658 exited0: complete actual Forex template → real page writer → existing asset extractor passed for BOTH the matching-date interpretation and the withheld mismatched-date interpretation. Existing pair content, both languages, selected dates, unknown source freshness and one inspector survived; zero component scripts. Second extraction was byte-identical. Component CSS remains `b9b73065256ea260677d35b1212d6a37f8453cee4923e4aefeeb5adb93dffd90`, unchanged by this sign/summary work. Actual design enforce-added returned0 introduced violations.

All render examples use bounded synthetic fixtures and temporary output, not a live nightly build. No browser pixel, focus, keyboard, screen-reader, full contrast or production acceptance is inferred. The original cb644 CI36805101838 passed its contract and11packs, but pack7/design-governance failed for the missing owning browser EVIDENCE.yml. Fences36805101494 passed. Those are prior-head results, not proof for the next published head.

Current source remains Draft/HOLD, with both registered source-review requests still awaiting a submitted review. The Paper connector's last exact write-admission mismatch and the historical browser administrator refusal remain unresolved; no alternate browser, host, profile or Paper carrier was used to get around them. Existing accepted designs, source/collector owners, other PRs, trading state and production outputs are untouched.


## R15 — source-review correction: the actual pull-request gate must execute the tests

Review comment5926367177 on exact `1a3635f0a2060d38e0b3c7e2ba30e95cb6e864ad` correctly found that the only run owner of `tests/test_forex_context_bus.py` was `unrun-macro-panels`, classified `gate: data`. The PR planner loads `gate: code` and filters that job before selection. The R12–R14 local results remain real, but earlier all-gates ownership/dependency checks did **not** prove these regressions ran on a pull request. This section supersedes that inference, not their source/test results or browser HOLD.

The suite now runs in the **existing `data-base-shim` code-gated job**, next to its real-builder/temporary-root tests. All context-bus cases are synthetic, temporary-output or source-contract checks; no live-data case is being moved to the code plane. The old data job retains its other panel/calibration tests and remains `gate: data`. Exactly two existing job definitions change. There is no new job, planner, authority, skip, waiver or runtime version. The code owner declares the full existing Forex-test dependency set rather than relying on host-installed packages. Scope inference remains with the canonical planner; no broad global path glob or `scope: exclusive` is added.

Two new regressions require exactly one code-gated run owner for the entire context-bus suite, no test-name filter, retention of the existing builder suite, preservation of the data-health job, and declared test dependencies. Initial Studio PID69753:2 expected assertion failures; both pass after the manifest repair.

### Local execution and sparse-input boundary

- Initial combined owner run PID70446:195 passed/2 failed. Both failures were existing free-content builder tests requiring committed `site/` URLs omitted by the sparse checkout, not Forex assertions. The shell's trailing diff check returned0 despite pytest's failures; the pytest result is recorded here as **failed**, not green.
- First exact-site restoration PID72576 fixed `related.live` paths but exposed a separate omitted `/chat.html` CTA target:195 passed/2 failed. No test/source was weakened to ignore the paths.
- Final PID74241 rebuilt the missing *frontmatter HTML references*, including CTA targets, from exact reviewed-head Git blobs in a temporary directory and redirected only `build_free_content._LIVE_SITE_DIR` during the test process. No production checkout/site/source data was changed. **276 passed** across the existing builder-shim/context-bus/stance/Forex/B3 suites:267 scoped Forex-related cases (265 prior+2 R15) and9 builder-owner cases. All cases ran; none was deselected. Two inherited NumPy warnings and the unrelated protected pytest-temp cleanup warning remain disclosed.
- Restored exact HEAD paths: site/chat.html, congress_trades.html, crypto.html, markets.html, options.html, research/index.html, stocks/index.html, us_stocks.html and vector.html. These supply the existing link-existence validator, not browser acceptance or new live market inputs.

### Real planner and contract proof

Studio PID70975 executed the canonical `load_legacy_jobs(gate='code')` → `infer_job_scopes` → `select_jobs` path. **`data-base-shim` is selected** separately for changes to each of7 paths: context-bus tests, kinematics projector, forex_regime producer, forex_signals adjustment owner, build_forex, the movement inspector, and the parent Forex template. No tested path is reported unowned; the data-only macro-panel job is absent from code selection. A test-only change selects2/167 jobs, not a fabricated full-run workaround.

The same process ran the complete `scripts/check_contract_delta.py --base 7502eac2d65e4adc6bbc134de5474d6f56ae117e`: **0 introduced/0 inherited findings**, all existing workload ceilings preserved. The displayed build_free_content and prophet probes retain job/pack counts and each increase the estimate by1second. Process exit0, contract wall202.4seconds. No scope/budget/authority rule changed.

Current-main comparison at `b1a85f89b2f7d2f678f828087adcf59616f836a3` found no change to the relevant source/law/planner/test paths or either owning job since this candidate's base. No ancestry-only merge/rebase was made. Financial source, templates, the source-data contract and the Bonds carrier are unchanged by R15.

**Acceptance still owed:** a new exact pushed head; real hosted planner selection and execution of the moved suite; follow-up review of the bounded CI repair; and the independent existing browser/visual-evidence requirement. The current Paper app still advertises0.5.14 but refuses writes under an expected0.5.12 receipt; source procedure has corrected the version-only rule, but source publication is not this connection's runtime installation. No Paper write, browser-policy retry, screenshot substitution or EVIDENCE waiver occurred.
