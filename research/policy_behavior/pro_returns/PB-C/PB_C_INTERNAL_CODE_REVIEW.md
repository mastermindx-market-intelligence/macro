# PB-C — Bounded internal code review

## Review identity and scope

- Operation: `PB-C-STRATEGIC-ANNOUNCEMENT-ORCHESTRATION-20261007`.
- Review date: 2026-10-07.
- Reviewer role: native advisory subagent `/root/statistical_design`; parent `/root` remains integration owner and sole GitHub writer.
- Classification: **bounded internal implementation review, not a PB-F independent program review**. This record confers no production, publication, ranking, trading, sizing, or central-intent authority.
- Reviewed analysis file: `/workspace/scratch/7a0bb715b184/pbc/reproduce_pilot.py`.
- **Exact reviewed analysis SHA256: `0f6fb6bba123d08918b914807ae2fde94c04eb45cc55540cfdc90b6aaf71ce15`.** The synthetic-check output recorded this digest.
- Reviewed rate derivation: `/workspace/scratch/7a0bb715b184/pbc_methods/derive_treasury_stress.py`.
- Previously delivered Treasury script SHA256: `0b577ccd16411f02765759054bc3d9bb4b36c21212c89508aa76fd7dc4e1e53f`.
- Governing protocol: `/workspace/scratch/7a0bb715b184/pbc/PB_C_ANNOUNCEMENT_STUDY_PREREG.md`, frozen 2026-10-07 02:58:22 UTC. The protocol is retrospective, not a claim of historical preregistration or prospective validation.

The review inspected the analysis code, the critical arithmetic and temporal logic of the Treasury script, synthetic event cases, and existing local Treasury XML caches. It did not inspect the actual event panel, run the parent analysis main function, fetch data, modify parent source files, or conduct an independent program assessment. Synthetic checks used 1,000 draws where applicable and did not generate substantive event-study results.

The reviewed analysis version already contained guards for empty event samples and absent eligible pairs, primary pairing by disjoint observed issuer sets, a relaxed primary-issuer-only sensitivity, and explicit nontrading-date exclusions. Those features passed the bounded synthetic checks.

## Resolution boundary

Findings below describe the exact reviewed version. Later code has not been re-reviewed under this record. After receiving the findings, the parent reported applying constant-simulation handling and descriptive-only program coarsening, and reported adopting stable root-specific random draws and stronger input validation before the first actual panel run.

**Parent-reported fixes are distinguished from independently verified resolutions.** The parent should append the later source digest, implementation details, and any relevant verification evidence when integrating this report. No subsequent tests or source retrieval were requested for this write-up.

| ID | Finding in reviewed version | Later-version resolution status at write-up |
|---|---|---|
| F1 | A constant simulated statistic can still emit a displayed probability of 1 with Monte Carlo SE 0 | **Parent reports fixed in a later version; not re-reviewed here** |
| F2 | First-program selection occurs before simulation; its probability needs a narrower estimand or a different null operation | **Parent reports changed to descriptive-only program coarsening in a later version; not re-reviewed here** |
| F3 | C3 is unordered pair proximity; source-clock precision is distinct from earliest-public certification | Interpretation and metadata finding; parent to annotate resolution |
| F4 | Independent month-by-weekday date resampling is a restricted conditional model, not established calendar exchangeability | Interpretation and metadata finding; parent to annotate resolution |
| F5 | Sequential shared RNG makes root assignments depend on event and case order | Parent reports adopting stable root-specific RNG; implementation not re-reviewed here |
| F6 | Count-only calendar checks and assertions are weaker than fail-closed structural validation | Parent reports adopting stronger validation; implementation not re-reviewed here |
| T1 | Treasury script uses a workspace-specific default protocol path | Portability recommendation; parent to annotate resolution |
| T2 | A generic maximum-age carry rule could admit a future unexpected feed gap | Future-input hardening recommendation; current cached gap pattern checked |
| T3 | Manifest generation time changes on rerun even when derived flags do not | Provenance interpretation; preserve original receipt rather than promise every artifact is byte-identical |

## Findings

### F1 — Uninformative reference distributions need an explicit status

**Reviewed behavior.** `probability_record()` returns `(hits + 1) / (B + 1)` for every nonempty simulation vector. The empty-event and no-pair guards correctly avoid that call in those cases. It is still called when events exist but the chosen statistic has no variation.

Two synthetic examples reproduced the remaining issue:

1. One January event for a rate specification with no exposure opportunity on any eligible January date: observed count 0, every simulated count 0, displayed probability 1, Monte Carlo SE 0.
2. Two scheduled roots held fixed: observed pair count 0, every simulated count 0, displayed probability 1, Monte Carlo SE 0.

The tail count is mathematically correct for that mechanical reference distribution. Its presentation can be mistaken for informative evidence against excess alignment or clustering when the design had no opportunity to distinguish alternatives.

**Recommended handling.** Where the statistic is demonstrably constant over its eligible assignment support, report an explicit status such as `UNINFORMATIVE_DEGENERATE_NULL`, retain the observed count and constant reference value, and suppress an inferential probability and Monte Carlo SE. At minimum, flag absent variation among simulations and avoid treating a displayed 1 as substantive evidence of absence.

Do not infer structural degeneracy merely from a finite set of identical simulated values. A finite simulation can miss rare alternatives. If all sampled values coincide but differ from the observation, distinguish `NO_SIMULATED_STATISTIC_VARIATION` from a proven constant null.

Useful diagnostics include movable-root count, the number of distinct simulated statistic values, and, for stress alignment, the number of roots whose eligible date sets contain both exposed and unexposed dates. Keep the existing empty-event and no-pair guards.

**Later-version status:** Parent reports the constant-simulation fix is applied. This reviewer has not inspected that later implementation.

### F2 — Program coarsening changes the analysis unit and the null

**Reviewed behavior.** The program-family sensitivity sorts observed broad events by date and root ID, keeps the earliest captured root for each program family, and then randomizes only those representatives. Constituent roots are not randomized and re-coarsened within each simulation.

This can be described as a conditional first-captured-representative sensitivity. It is not the same statistic/reference procedure as randomizing all constituent roots and selecting the earliest member per program in every simulated panel.

For example, with two program roots sharing four eligible dates, independent uniform draws make the earliest eligible date the program minimum with probability `7/16`. Randomizing one representative uniformly gives `1/4`. The procedures therefore answer different questions.

**Recommended choices before inspecting results:**

1. Retain the representative algorithm, explicitly label its restricted estimand, preserve the representative-to-member mapping, and avoid describing it as preserving whole-program timing dynamics.
2. If the target is a minimum-date program statistic under the constituent-root null, apply the same program-minimum operation in every simulated panel.
3. Report the observed coarsened counts descriptively and withhold a probability until the program-level null is specified.

The reviewed code also coarsens before excluding nontrading originals. A program with a Saturday first capture and a Tuesday subsequent capture disappears from the sensitivity because its selected representative is excluded. That follows a first-captured-program-date definition; it differs from first eligible trading-date observation. Record the chosen rule and resulting program exclusions.

Keep source-manifestation deduplication separate from program coarsening. Multiple manifestations of one economic root must be deduplicated. Distinct economic developments within one program remain separate roots in the base panel; coarsening them is a sensitivity that changes the analysis unit.

**Later-version status:** Parent reports switching this sensitivity to descriptive-only output. This reviewer has not inspected that later implementation.

### F3 — Pair proximity, same-day ambiguity, and clock certification

The C3 statistic counts eligible pairs whose absolute trading-session distance is zero through the chosen horizon. It measures unordered proximity. The added `same_session_pairs` output is useful, but neither date equality nor an exact timestamp attached to one source establishes a cross-firm announcement order or a globally first public disclosure.

Recommended metadata:

```text
statistic: UNORDERED_DISTINCT_ROOT_PAIR_PROXIMITY
same_session_order: NOT_INFERRED
```

The `broad_exact_source_clock` sensitivity should separately report the number of retained roots with exact source clocks and the number with certified earliest-public timestamps. The reviewed script preserves both concepts in overall counts; carrying them into the sensitivity metadata would make its limits clearer. An exact-source-clock flag is not evidence that the source was globally earliest.

Known joint-program and conference clustering should have separate descriptive counts or an explicit missing status. Disjoint issuer sets do not eliminate shared conference calendars, and first-program coarsening does not enumerate conference dependence.

### F4 — The null is conditional independent date resampling

The reviewed algorithm independently samples each movable root's date, with replacement, from eligible trading dates in its original month and weekday. Root identities and their attributes remain fixed. Scheduled dates remain fixed except in the explicitly moved calendar diagnostic.

It does not preserve every earnings, conference, policy, financing, issuer-burst, or program-gap pattern. Independent assignments can also produce same-issuer same-day collisions. These are features of the stipulated reference model, not necessarily coding errors. They limit the interpretation of its probabilities.

Suggested metadata:

```text
null_model: INDEPENDENT_UNIFORM_MONTH_WEEKDAY_DATE_RESAMPLING
exchangeability: ASSUMED_WITHIN_SELECTED_PANEL_NOT_ESTABLISHED
population_arrival_inference: NOT_SUPPORTED
```

The reviewed file already acknowledges incomplete calendar adjustment and search-driven capture. Preserve those qualifications when interpreting results. Monte Carlo uncertainty measures simulation precision conditional on the model; it does not measure uncertainty from incomplete source capture or a misspecified opportunity calendar. Do not turn the selected panel into a complete issuer-day risk set or interpret uncaptured events as certified absences.

### F5 — Stable reproduction should not depend on unrelated case ordering

The reviewed script is deterministic given identical code, input bytes, NumPy version, and case order. It uses one sequential RNG across cases and roots. A synthetic reversal of root rows changed the random vector assigned to a given root. Adding or reordering cases likewise changes subsequent random assignments.

This is an order-stability limitation, not nondeterminism under unchanged inputs.

Options include canonical root sorting plus stable case-specific seeds, or root-specific random draws derived from the master seed and stable root ID. Reusing each root's assignments across leave-issuer/species subsets supplies common random draws and avoids sensitivity differences driven only by changing Monte Carlo assignments. Use a stable digest such as SHA256, not Python's process-dependent built-in `hash()`.

Record the bit-generator identity and include analysis-code and frozen-protocol digests in output provenance.

**Later-version status:** Parent reports adopting stable root-specific RNG before the actual panel run. This reviewer has not inspected that later implementation.

### F6 — Structural validation should fail closed

The reviewed checks cover unique root IDs, the 250-session count, the exceptional January 9 closure, 365 stress rows, selected enumerations, and lag invariants. They do not fully establish that calendars are sorted, unique, complete, and correctly typed.

Recommended additions:

- Require sorted, unique trading dates within 2025.
- Require stress dates to equal the complete 365-date sequence for 2025, with no duplicates or omissions.
- Require exposure flags to be binary.
- Require each observed issuer set to be nonempty, duplicate-free, and to contain the primary issuer.
- Validate tickers under the declared schema and counterpart-role policy; do not silently assume every counterparty must be a frozen-universe issuer.
- Parse ISO dates before relying on string comparisons.
- Use explicit exceptions for essential gates because Python optimization with `-O` disables assertions.

The explicit output `semantic_source_truth_proved_by_these_checks: False` is appropriate and should remain. Structural validation does not certify source interpretation, global first publication, or semantic root identity.

**Later-version status:** Parent reports adopting stronger validation before the actual panel run. This reviewer has not inspected that later implementation.

## Synthetic checks of already-correct behavior

| Synthetic case | Result in the reviewed version | Assessment |
|---|---|---|
| No eligible events | Rates return `NOT_ESTIMABLE_NO_ELIGIBLE_EVENTS` and null probability | Pass |
| One root, hence no eligible pair | C3 returns `NOT_ESTIMABLE_NO_ELIGIBLE_ROOT_PAIRS` and null probability | Pass |
| Joint NVDA–MSFT root paired with a separate MSFT root | Excluded by the primary disjoint-set rule; included only by the relaxed primary-issuer rule | Pass |
| A Saturday original and a January 9 original | Both excluded from trading-date randomization and named in exclusions | Pass |
| Two fixed scheduled roots | No movable roots; constant statistic still receives displayed probability 1 | F1 |
| One January root with no eligible rate-exposure contrast | Constant zero alignment still receives displayed probability 1 | F1 |
| Reversed ordering of otherwise identical synthetic roots | Root-specific random vectors change under the same master seed | F5 |

## Treasury derivation review

### Arithmetic and temporal assessment

No material arithmetic or lag defect was found in the consumed derivation.

- Decimal arithmetic converts percentage-point changes to basis points and implements the inclusive 25 bp threshold without binary floating-point threshold drift.
- Aligned value at index `t` minus aligned value at `t-5` measures five NYSE-session intervals.
- `bisect_left(sessions, event_date) - 1` selects a session strictly before the event date.
- The prior-five and prior-ten slices contain exactly five and ten preceding session entries.
- Episode onset requires ten immediately preceding nonstress sessions.
- The 2024 Q4 warmup is sufficient to avoid treating initial unknown rate changes as known nonstress observations during the 2025 study.
- The 2025 equity calendar includes the exceptional January 9 closure.

An offline inspection of existing caches found exactly these NYSE sessions without same-date Treasury observations, for both nominal 2-year and real 10-year series:

```text
2024-10-14
2024-11-11
2025-10-13
2025-11-11
```

This matches the disclosed bank-holiday carry pattern. Neither cached instrument contained nonfinite values. The inspection did not fetch or modify any source data.

### Hardening recommendations

**T1 — Protocol path portability.** Replace the workspace-specific default `--protocol` path with a required argument or documented relative path when preparing a portable reproduction package.

**T2 — Missing-date policy.** The current seven-calendar-day maximum source-age gate limits staleness but could permit an unexpected future feed gap. For later acquisitions, distinguish declared calendar absences from unexpected missing observations. The current cached gap pattern was checked and does not require a rerun solely for this recommendation.

**T3 — Manifest identity.** The derived flags are deterministic for fixed inputs, while `computed_at_utc` changes on rerun. Preserve the original source and derivation receipts; do not claim every artifact will be byte-identical after regeneration.

The rate outputs remain current-vintage, prior-date Treasury sensitivity proxies. This review does not certify original intraday publication availability or historical vintages. The rate specifications do not substitute for blocked Nasdaq or VIX data.

## Parent integration record

Parent to append, without altering the distinction between reviewed evidence and later resolution:

- Later analysis source SHA256 and integration commit, if any.
- Resolution details for F1 and F2, already reported applied.
- Resolution details for F5 and F6, reported being adopted.
- Disposition of interpretation/provenance findings F3, F4, and T1–T3.
- Any subsequent verification evidence and its scope.

This report records a bounded implementation review before the first actual event-panel analysis. It neither validates substantive effects nor establishes a complete source risk set, direct coordination, or causal intent.

## Integration-owner resolution after the reviewed version

The original findings above retain their original review scope. The accepted analysis code was subsequently frozen at Git commit `f856691e4578db7029646bba1c5e90949e009de5` before event tests. The delivered numerical review independently reconciles every observed case and saved tail-count calculation; it is still an internal review, not PB-F.

- Empty samples and absent pairs return explicit NOT_ESTIMABLE states.
- Constant sampled statistics equal to the observation suppress probabilities; rate cases with no structural exposure contrast have a separate status.
- Root-specific SHA256 seeds and canonical ID order stabilize assignments across case/row order; a synthetic reversal check passed.
- Dates, complete calendars, binary flags and issuer sets use explicit exceptions.
- Program-representative probabilities are suppressed; direct multi-program memberships are preserved without transitive collapse.
- Same-day proximity is unordered; exact source clocks are distinguished from earliest-public certification.
- The Treasury script default protocol path is now relative to the delivered script. The original derivation receipts remain unchanged; fresh computation timestamps may differ.
- An independent-directory offline rerun reproduced both analysis and descriptive JSON outputs byte for byte. See `PB_C_REPRODUCTION_RECEIPT.json`.

No implementation check certifies source-frame completeness, causal identification, a complete calendar null, or an economic effect.
