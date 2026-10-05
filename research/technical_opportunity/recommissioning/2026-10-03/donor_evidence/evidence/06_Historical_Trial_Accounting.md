# TOI W3 ledger and hypothesis-accounting follow-up

**Scope:** bounded source-only advice for the new W3 tournament; no reconstruction of historical S16 search, no outcome run, and no remote/ledger write. Source pin: Macro `5fc7af4a1aa2510966a7b566f97e5b894f2632f8`.

## 1. Exact current source facts

- [TrialLedger][ledger] counts distinct **(family, canonical-config hash)** rows. `_canon()` sorts JSON keys; it does not recognize scientific aliases or correlated formulas. `info_cutoff`, `source`, `note` and observation timestamp are metadata outside the hashed config.
- `log_grid()` logs every candidate at generation. Identical config reruns are idempotent; new config values add rows. A code rerun's zero new rows is therefore not a scientific ruling that reusing an inspected tape incurs no selection or repeated-look risk.
- `log_declared_budget(n)` stores a **maximum floor**, not an additive increment. The default effective trial count is `max(distinct_itemized_configs, maximum_declared_budget, 1)`. Optional correlation credit is off by default; do not enable it for W3 without an explicit frozen justification.
- `with_declared_budget()` creates a temporary ledger. It is an accepted DSR-call adapter, not a substitute for the canonical before-run registration required for W3.
- [Setup Species §1.2][species] requires the full grid before outcomes, an episode/time-dependent p-value for each primary proportion contrast, and one correction over the full registered family. DSR applies only when there is an actual return series, never as a correction for success/failure proportions.
- [S16's report appendix][s16report] expressly says its historical 12 declared trials stand; the mandatory DT-R14 same-cell time-control repair is robustness, not a new trial family.

### Historical accounting, directly verified

A read-only JSON parse of the entire pinned `data/trial_ledger.jsonl` returned:

| Family | Canonical ledger at this pin | Defensible claim |
|---|---|---|
| `esx_sq_phase0` | One `declared_budget` row, `n=12`, timestamp `2026-07-05T07:36:12.540811+00:00`, config hash `55556a38be80b4cf`; reason “frozen state grid x 2 panels x 3 forms + 3 named sensitivities” | Historical declared budget 12, with a historical report/run. Do not fabricate twelve itemized rows from today's interpretation of the expression. |
| `esx_sq_def4_phase0` | **Zero rows** | Draft pre-registration exists, with planned trial count 10 and planned BH pool 46. No canonical ledger/run proof at this pin. |

The [Def4 draft][def4] says DRAFT/pending approval, then registration → ledger row → study. It does not authorize execution. Do not add ten to historical twelve and call the result “22 consumed.”

## 2. The strongest local precedent: trial rows and hypothesis cells are different

Def4 §5 explicitly declares **10 trial rows and 46 BH hypothesis cells**:

- T01–T04 and T09–T10: six within-S16 contrasts, seven BH-eligible outcomes each = 42 cells.
- T05–T08: four subset/control or interaction rows, only their verdict-bearing stop5 outcome = four cells.
- Non-stop5 V/I outcomes are context, not additional confirmatory claims.
- Floors and any family-size reduction are frozen and evaluated before any p-value; the future W3 does not automatically inherit this particular permission to shrink its pool.
- The document names the same-tape sequential-family limitation: its within-family q-values would not provide tape-level protection against the earlier S16 search. [def4]

This supports the new tournament's explicit two-count design. It does **not** establish that “number of candidates” may be silently substituted for “number of statistical claims.”

## 3. Recommended new W3 accounting — proposed architecture

Use one existing TrialLedger family for the coherent W3 scientific selection exercise, with lineage references to S16, Def4 and all inspected prior research. Do not put W3 trials into the old S16 family merely because they use the same detector, and do not split families by model/clock/head to reduce the correction on one shared headline. If distinct families are justified, freeze their scope and the rule combining their selection claims before outcomes.

Create a frozen, itemized manifest in the research packet; register its semantic candidate rows through the existing ledger once the study is admitted. It is an experiment artifact, not a second registry.

### Candidate identity

A proposed semantic candidate key contains:

`detector/version × direction × clock-construction/version × information/confirmation-policy × prediction-head × model/hyperparameters × declared-selection-protocol`.

Include the actual mechanism-defining parameters, canonical indicator/source identities, label/censoring/fill definition and data-contract version. The immutable manifest separately binds train/validation/confirmation populations and availability cutoffs. Do not hash a per-run wall clock into scientific identity.

A “head” belongs in candidate identity when it changes the fitted target/model or selection policy. Additional metrics used to judge the same fitted head are **hypotheses/endpoints**, not necessarily new fitted candidates.

### Hypothesis manifest

For each confirmatory claim, separately freeze:

`candidate/contrast IDs × estimand/head × primary horizon × comparator × population × inferential direction × decision rule`.

This determines the primary hypothesis pool. A candidate can support several claims; a comparison can involve two candidates; Brier, log loss, tail MAE and calibration failure are not interchangeable copies of one endpoint. Make the rule linking all primary claims to promotion explicit—co-primary intersection, family-wise adjustment, hierarchical testing or the approved full-family correction. It must not become “passes whichever endpoint looks best.”

Use manifest-derived counts and preserve every excluded/insufficient cell with reason. Do not manually write an attractive small denominator after seeing which cells have power or significance.

### What consumes budget

| Work performed | Treatment |
|---|---|
| Identical aliases/formula implementations | Normalize before the manifest; one semantic construction if equivalence is proven before outcomes. TrialLedger cannot do this itself. |
| Different parameterization, clock, direction, confirmation policy, target head or model that can be selected | A new candidate choice; log at generation. Correlation is not automatic budget credit. |
| Frozen CV folds, fixed training windows, refitting the same model in each fold | Evaluation machinery, not automatically one independent hypothesis or new scientific candidate per fit. Bind the protocol. |
| Inner hyperparameter/feature search | Every distinct selectable setting belongs in the declared/itemized candidate search; logging only the eventual winner hides the search. Repeated settings across folds may dedup; the full search procedure and selection budget must still be disclosed. |
| Bootstrap/permutation replicates used by one frozen estimator | Monte Carlo draws, not separate alpha hypotheses. Changing seeds/replicate counts/estimator after seeing favorable results becomes adaptive analysis, which must be recorded. |
| A frozen seed ensemble whose outputs are averaged by rule | One fixed construction with disclosed computation, not an opportunity to select the best seed. Selecting a seed/model fit turns the tried alternatives into candidate search. |
| Same config recomputed to verify a deterministic fix or registered robustness control | Keep original family and result lineage. S16 DT-R14 is a direct precedent for a mandatory same-cell repair without a new family. It is not permission for unregistered redesign. |
| Same config rerun on new outcome data | Literal ledger count may remain unchanged; preregistered evidence clocks and repeated-look rules still govern inference. An unplanned data-window/analysis-epoch choice must not disappear behind idempotence. |
| Diagnostic endpoint never used in selection or promotion | Print as descriptive with no success claim and retain its status. |
| Diagnostic endpoint used to choose the winner, change a gate, select a grain or justify advancement | It has become a selection channel. Preserve the exploratory status and new look; it cannot be retroactively declared an untouched primary. New frozen confirmation is required. |
| Mechanically changing display precision, report formatting or rereading immutable results | No new candidate, hypothesis or outcome look created by formatting itself. |

These are proposed W3 operationalizations of the existing generation-counting, full-family, frozen-ruler and no-audition laws; TrialLedger alone does not infer or enforce all of them.

## 4. Max-floor trap to avoid

Suppose a family has only a historical declared floor 12 and a genuinely new ten-config extension is added. Logging ten itemized rows alone yields `max(10,12)=12`, **not 22**. Appending `log_declared_budget(10)` also leaves the maximum at 12.

If an approved same-family extension truly requires a cumulative floor, declare that justified cumulative floor explicitly and explain the non-overlapping increments. Never reconstruct phantom old config rows. For this new W3, do not choose “12+10” as its budget: S16 is prior consumed evidence; Def4 is a separate unrun draft at the pin; W3's actual new manifest determines its own finite candidate and claim counts, while same-tape design contact remains a disclosed limitation.

## 5. Legacy family×regime restriction remains binding

[DNR:KILL-PER-SIGNAL-FAMILY-RELIABILITY][dnr] killed the old per-family regime-reliability grid because the required interaction was weak/unstable and richer regime axes unestimable. Reopening requires the existing [estimability meter][coverage] to return estimable for the target axis plus a fresh preregistration whose **interaction is primary**. The [Setup Species learned-cell law][species] additionally freezes ≤2 axes/≤6 cells and requires genuinely independent regime episodes before learned authority.

A new model, hierarchical shrinkage or hazard head does not by itself make the killed lookup construction new. W3 may study a sparse mechanism-specific interaction using a valid target and data contract, but cannot manufacture “breakout reliability this regime = 0.73” from unsupported cells or call a common date-level regime label independent evidence for every stock.

[ledger]: https://github.com/mastermindx-market-intelligence/macro/blob/5fc7af4a1aa2510966a7b566f97e5b894f2632f8/engine/trial_ledger.py
[species]: https://github.com/mastermindx-market-intelligence/macro/blob/5fc7af4a1aa2510966a7b566f97e5b894f2632f8/research/SETUP_SPECIES_MASTERPLAN_BY_FABLE.md
[s16report]: https://github.com/mastermindx-market-intelligence/macro/blob/5fc7af4a1aa2510966a7b566f97e5b894f2632f8/research/entry_stack/W2_SSQ_REPORT.md
[def4]: https://github.com/mastermindx-market-intelligence/macro/blob/5fc7af4a1aa2510966a7b566f97e5b894f2632f8/research/entry_stack/SSQ_DEF4_VARIANT_PREREG.md
[dnr]: https://github.com/mastermindx-market-intelligence/macro/blob/5fc7af4a1aa2510966a7b566f97e5b894f2632f8/research/DO_NOT_REBUILD.md
[coverage]: https://github.com/mastermindx-market-intelligence/macro/blob/5fc7af4a1aa2510966a7b566f97e5b894f2632f8/engine/regime_conditioning_coverage.py

