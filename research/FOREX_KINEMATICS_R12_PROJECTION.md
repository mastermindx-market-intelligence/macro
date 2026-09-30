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
