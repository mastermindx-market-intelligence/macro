# Bonds CDI owner-contract proposal — 22 October 2026

**Status: UNADOPTED REQUIREMENTS / SOURCE CONSULTATION.** Prepared for the existing Macro #9590 documentation carrier. This document proposes bounded contracts; it does not install an interface, establish a live lease, admit a source, register a cohort, qualify an independent review, or authorize a release.

Intended repository path: `research/credit_dislocation/OWNER_CONTRACTS_20261022.md`.

## 1. Evidence baseline and authority

The inspected Macro source is commit `414d785d14e9af77c02a273f0f9829162b9cc55d`; the inspected Terminal #804 source is `afd01ea799bd9951953ef48ec6e682bad2b44143`. Later source changes require reconciliation through the same owners. The proposal was prepared through read-only source inspection. Its adoption as documentation does not install the proposed interfaces or qualify a release; it required no implementation, capture, provider acquisition or database action.

The current [CDI master plan][M1] assigns W4 to per-bond history/term-aware comparables, W5 to financing schedules, and W6 to retained case/evaluation memory. These names are distinct from the older CCW plan's W4 surface, W5 FINRA and W6 study waves.

All proposed consumers remain descriptive/display/context only. Preserve `rank`, `size`, `gate` and `escalate` as false, the existing explicit missingness, and the absence of predictive or CDS qualification. A priced bond, a dated issuer comparison, a saved case and an activated monitor are separate results. This proposal adds no service, store, queue, evaluator, scheduler, registry entry or publication plane.

### Recorded owner boundaries

| Boundary | Recorded source owner/carrier | What remains unresolved |
| --- | --- | --- |
| CCW/CDI source | `owner_program: ccw`; Macro #9590. Existing source integration operation `ccw-cdi-source-integration-20261022-sol-001`, publishing through `claude/ssd-ccw-dislocation-v1-cc87720e59421398`. | No current W4/W5/W6-specific execution operation or prospective-grader operation is established by the inspected records. Reconcile custody before an effect. |
| Funding calculation | `INTERFACE_OWNER = "capital-structure-intelligence"`; typed contracts and `project_funding` remain with that owner. | Current executing writer/operation and the Bonds consumer's admitted input bindings are not identified here. Historical program-owner prose is not a live lease. |
| Saved Investigation | Existing Terminal #804 and its Investigation v2 persistence, validation and resolver boundaries. | Current executing writer/operation; Bonds evidence owner/type/version namespace; immutable resolver and current-access binding. |

An `UNRESOLVED` value below is a documentation gap, not a new identifier or an accepted API value. The accountable recovery owner may prepare these proposals; only the corresponding existing source owner can adopt its contract through the ordinary gates.

## 2. W4 — per-bond history and term-aware comparables

### Existing source contract

[`engine/corp_credit.py`][M2] reads retained `data/corp_bonds/holdings/<FUND>/<date>.parquet`, the existing issuer registry, rate curves and ancillary mappings. It publishes issuer/theme/sector/market daily series, maturity rows and `series/bond_panel_latest.parquet`. The latter explicitly contains the latest `as_of` only; it is not complete per-bond historical storage.

[`engine/credit_dislocation.py`][M3] currently consumes `series/issuer_daily.parquet`, `series/bond_panel_latest.parquet`, `issuer_themes.json` and one qualified whole equity source per issuer. `compile_snapshot(...)` requires dated issuer matched-change rows and dated ISIN/issuer bond rows. The loader does not stitch equity stores. Its descriptive comparison and pricing-qualification binding remain authoritative for their existing scope.

### Unadopted requirements

| Required binding | Proposal requirement | Unresolved decision |
| --- | --- | --- |
| Instrument identity | Retain exact instrument identifier, issuer/legal-entity binding and source lineage. Preserve ambiguity and duplicate/conflicting observations explicitly. | Accepted per-instrument historical projection and canonical identity/alias policy. |
| History | Identify each actual retained source generation, observed date, available history and gaps. Separate source observation, first availability when established, capture/registration and calculation clocks. | Existing-owner history projection/version contract; verified availability/correction lineage; actual coverage. |
| Price and spread | Preserve clean/dirty convention, accrued amount, units/currency, curve date and existing pricing-validation binding. A later observation cannot inherit an earlier bound PASS. | Which existing qualified histories support the requested comparison; unknown source conventions stay unknown. |
| Comparable terms | Require evidence for maturity/coupon, currency, seniority/security/guarantee and embedded options wherever the proposed comparison relies on them. Exclude or label unknown terms. | Owner-frozen grouping, normalization, minimum support and exclusion rules. No new thresholds are specified here. |
| Population | Keep holdings coverage, issue outstanding and total issuer liabilities separate. Retain missing/delisted/defaulted or changed-identity cases when relevant to the declared population. | Exact denominator and historical cohort coverage. ETF-held par is not total debt. |
| Corrections | Retain the original observation/version and explicit replacement lineage; distinguish corrected-current analysis from what was knowable at the original cutoff. | Existing retention/correction mechanism and reproducible version reference. |

**Smallest next deliverable:** a source-owner compatibility table identifying the existing retained input generations, actual per-instrument history coverage, proposed comparable fields and each unsupported dimension. Bind one finite, descriptive example only after its actual data/identity support is established. Do not create a collector, re-solve all history, or invent an immutable history endpoint to fill a contract gap.

### Acceptance checklist — requirements, not completed results

- [ ] The adopted input/version contract identifies a real existing owner and its exact source; the current writer/custody has been reconciled.
- [ ] A latest-only panel cannot pass a requirement for historical per-bond coverage.
- [ ] Missing terms, ambiguous identity, unsupported currency/options and insufficient peers remain explicit; they cannot become confident relative-value rankings.
- [ ] Date, price-convention and qualification bindings survive missing, duplicate, conflicting, corrected and future-observation cases.
- [ ] The output exposes its actual denominator and source clocks; no CDS, point-in-time knowability, total-debt or predictive claim is inferred.
- [ ] Any adopted runtime delta receives its existing affected source/consumer qualification and review. This checklist is not a request to run it now.

## 3. W5 — exact Capital Structure funding binding

### Existing callable and records

The incumbent pure call is [engine/capital_structure/funding.py][M4]:

```python
project_funding(
    financials: FinancialInputs,
    commitments: CommitmentInputs,
    scenario: FinancingScenario,
) -> FundingSchedule
```

The records belong to [issuer_state_contracts.py][M5], not a Bonds-specific calculation fork:

- `FinancialInputs(binding, facts, cash_basis)` requires a `GenerationBinding` for the `financials` family.
- `CommitmentInputs(binding, commitments)` binds one `document_terms` or `covenant_terms` family. Do not conceal a multi-family merge inside this argument or silently change its signature.
- `GenerationBinding` fields are `input_family`, `schema`, `support`, `generation_id`, `artifact_sha256` and `as_of`. Supported/partial inputs require a generation ID or digest. `schema=None` is permitted for `unavailable`/`not_built`. Constructor validation checks structure and compatibility; it does not verify artifact bytes or independently admit a producer.
- `FinancingScenario` binds aware `as_of`, horizon start/end, a typed price assumption, selected actions, fee/discount assumptions and explicit unknown resolutions. Its scenario identity digests assumptions; changing an assumption must not mutate source facts.
- `FundingSchedule` preserves `state_id`, `scenario_id`, `cash_basis`, `CalculationReceipt`, dated periods, assumptions and unknowns. Its serialized schema is `capital_structure.funding_schedule.v2`. The raw `project_funding` result's `state_id` identifies funding inputs plus scenario and is explicitly not an issuer-state join key. Its receipt sets `computed_at` to `scenario.as_of`; that value is not an observed execution timestamp. Preserve the existing assembler's explicit issuer-state binding rather than inventing a join.

`project_funding` performs no file, network, clock, collector or model access. Its source law excludes facts first available after scenario `as_of`; non-USD inputs remain excluded/unknown instead of being silently converted.

### Unadopted Bonds consumer mapping

| Required mapping | Binding to preserve | Unresolved field/decision |
| --- | --- | --- |
| Subject | Exact issuer/legal entity and any guarantor relationship backed by the Capital Structure owner. | The Bonds-to-Capital-Structure subject mapping and actual covered entities. |
| Input generation | Existing `GenerationBinding` plus source-supported facts/commitments. | Actual admitted producer generation, schema, digest and supported/partial/unavailable/not_built state. |
| Scenario | Existing `FinancingScenario` and its immutable scenario identity. | Requested scenario/horizon and explicit assumptions; none is preselected by this document. |
| Consumer result | Return the owner's `FundingSchedule` and receipt without a second arithmetic path. | Existing consumer attachment/view contract and admitted owner operation. |
| Unknowns | Preserve owner-supplied unknowns and source coverage. | Which missing obligation families can actually be supplied by existing owners; no promised completeness. |

The existing funding implementation makes a missing member of a named opening cash basis unknown, makes the opening balance unknown when required cash-basis members have different measurement dates, recording `unknown:opening:date_mismatch`, keeps conditional financing out of balance identities, requires dated obligations, and separates gross/net/fees. Net loss is not burn; undated debt is not a maturity schedule; registered capacity is not available cash. It names missing owners for restricted cash, revolver availability, accrued interest, debt maturities and committed expenditure rather than treating these as zero. These are current source constraints, not new policy.

**Smallest next deliverable:** a typed, read-only consumer-binding specification for one actually supported issuer generation and explicit scenario, including the complete unknown/coverage projection. The existing Capital Structure owner must resolve any missing input-admission contract. This is not an instruction to activate its runtime or complete an unrelated program.

### Acceptance checklist — requirements, not completed results

- [ ] Subject identity, input generation/digest, scenario cutoff and scenario identity are exact and source-supported.
- [ ] The consumer calls the incumbent function and preserves the result/receipt; it does not recompute financing or combine incompatible families.
- [ ] Missing cash components, obligations, legal terms and data owners remain named unknowns; partial coverage is visible.
- [ ] Future-available facts, mismatched cash dates, unsupported units and duplicate available items retain incumbent refusal/withholding behavior.
- [ ] Conditional financing, restricted cash, revolving facilities and capacity cannot silently become available cash or eliminate a funding gap.
- [ ] The output remains a dated scenario, with no probability, score, rank, sizing or infinite-runway inference.

## 4. W6 — typed immutable Bonds evidence in Investigation v2

### Existing boundaries

[`terminal/lib/investigations.ts`][T1] owns `INVESTIGATION_ADMISSION`, command parsing, revision application, operation read/reconciliation and exact investigation reads. Its current evidence types are earnings workspace and smart-screen evidence; Bonds evidence is not admitted.

[`investigationContracts.ts`][T2] and the corresponding pure Python [validator][T3] enforce closed manifest fields, declared subject/evidence owner/type, pinned versus follow-head semantics, exact baseline membership and argument endpoints. The current persistence-side `valid_investigation_manifest_v2` also restricts the evidence types [at the inspected #804 source][T4]. A TypeScript allowlist change alone cannot establish a usable or accepted Bonds contract.

The existing earnings retained resolver [in eventWorkspace.ts][T5] is a concrete design precedent: validate exact immutable generation/object bytes and digest/length, subject identity and receipt fingerprint, then require current authorization; do not fall back to the current head or cache. It is earnings-specific, not an existing Bonds resolver. The [selected issuer-release adapter][T6] keeps container and selection fingerprints separate. Current [review][T7] and [replay][T8] routes are also earnings-specific. These are source precedents, not an available end-to-end retained-resolution path: at this pin the whole-workspace authorization helper deliberately throws `current_rights_owner_unavailable`; the selected issuer-release resolver requires an authorization callback that the inspected review/replay calls do not supply. This is a missing technical current-access connection, not a reopening of the user's Tiingo licensing approval.

### Unadopted reference and resolver requirements

| Contract element | Required meaning | Current value/status |
| --- | --- | --- |
| Evidence `owner` and `object_type` | Existing producer owner's accepted Bonds artifact family. | UNRESOLVED; no owner string or type is minted here. |
| `object_id` and subject binding | Stable producer identity bound to exact issuer/instrument/basket scope, with ambiguity refused. | UNRESOLVED namespace and mapping. |
| `mode`, `version_ref`, `fingerprint` | Explicit pin/follow-head semantics; pinned evidence recovers the same retained generation and verified receipt. | Generic pinned references require `version_ref`; fingerprint is optional in generic shape validation, while review/replay impose stronger requirements. Existing grammar applies; Bonds version/digest contract UNRESOLVED. |
| Producer receipt | Exact object/manifest byte counts and hashes, source/availability/capture clocks where established, calculation/version provenance and limitations. | Existing retained Bonds receipt/resolver contract UNRESOLVED. Do not add undeclared fields to the closed Investigation reference. |
| `selection.field` and scenario | A typed, owner-supported selection/reference to retained scenario/evidence; exact assumptions/revisions are recoverable. | Bonds selector/scenario representation UNRESOLVED. `selection` currently accepts a field selector, not an arbitrary payload. |
| Current access | Existing owner evaluates the current principal/policy and the exact retained subject/object. An old receipt is not a present permission grant. | Bonds current-access owner/callback and policy binding UNRESOLVED. |
| Baseline and argument relations | The baseline is an exact pinned evidence-reference member, including its fingerprint when present. Evidence argument endpoints match owner/type/object/mode/version/selection identity; endpoint grammar excludes fingerprint. | Existing strict rules retained. |
| Persistence and recovery | Existing `id`, `operation_id`, `expected_revision`, apply/read/reconcile semantics and immutable revision response matching. | Existing #804 ownership retained; Bonds parity and resolver integration UNADOPTED. |

Any immutable source receipt and typed scenario must live behind the accepted producer contract and be referenced through the declared manifest shape. Serializing scenario JSON into `intent.question`, adding arbitrary reference keys, or pointing a pin at a mutable latest object does not meet this requirement.

**Smallest next deliverable:** an owner-reviewed compatibility matrix specifying the real producer reference/receipt, subject mapping, typed selector, current-access decision and resolution failure states, alongside the exact TS/Python/persistence and review/replay paths affected. Preserve proposal status until the incumbent #804 writer accepts the interface after custody reconciliation. This document contains no registry edit or migration/cutover instruction.

### Acceptance checklist — requirements, not completed results

- [ ] A real existing producer owner, retained object namespace and admissible subject mapping are recorded; no proposed identifier is treated as installed.
- [ ] The same reference is accepted/rejected consistently at TS, Python and persistence boundaries; unsupported owner/type remains refused.
- [ ] Exact generation, object bytes/length/hash, subject and receipt fingerprint are verified before a successful retained resolution.
- [ ] Missing/corrupt/wrong-subject/revoked/unknown-access history remains unavailable or denied; there is no current-head fallback.
- [ ] Changing selection or scenario assumptions produces the owner's corresponding new identity; container and selection fingerprints remain distinct.
- [ ] Current review and replay paths explicitly handle the adopted Bonds contract; generic manifest admission does not imply this integration.
- [ ] Genuine save/readback/reopen, exact-revision conflict, response-loss reconciliation, correction/supersession and access-change behavior are qualified through the existing owner when its gates permit.
- [ ] No automatic monitor, delivery proof, predictive authority or source-admission claim follows from a successful case save.

## 5. Prospective protocol anchor and absent grader

[`engine/credit_momentum.py`][M6] has the existing CCW forward emitter and keep-FIRST log. It writes velocity-threshold and tag-fire events only, under `COLLECT_LANE == 'nightly'`, using the triggering source bar for `as_of` and registration time separately. It preserves fixed h21/h63 rulers and initializes grading fields to null.

The declared [`ccw-forward-log` Synapse contract][M7] names `owner_program: ccw`, `schema: ccw.forward_log.v1`, no scoring, no extra writers and **no consumers**. Its notes explicitly assign grading fields to a future grader. The bounded inspection does not establish a ready issuer-CDI prospective grading service.

[`scripts/ccw_study_s1.py`][M8] is the existing one-shot historical study over broad spread series and SPX, with 21/63/126 horizons and a [frozen preregistration][M9]. Preserve its accepted result and constructions. It is not the current issuer-CDI cohort, a prospectively registered episode store, or permission to retune its thresholds.

### Required anchor — all currently unresolved unless the existing owner supplies evidence

| Field | Required record |
| --- | --- |
| Protocol identity | Exact accepted protocol/version and review reference; eligibility, peer normalization, outcomes, baselines and censoring frozen before evaluation. |
| Existing evaluation owner | Actual existing owner/operation and compatible source contract; absent grader implementation/admission is stated explicitly. |
| Cohort/episode identity | Actual first eligible issuer-CDI episode, its source versions, subject and observable; no synthetic start. |
| Observation clock | Source observation and genuinely established availability/registration clocks; no artifact/build-date substitution. |
| Calendar and horizons | Accepted eligible-session calendar and 21/63/126 outcome definitions; no silent change to the incumbent ledger's h21/h63 ruler. |
| Missingness and corrections | Delayed/missing observations, delisting/default, revisions, censoring, overlapping episodes and negative controls handled under the frozen protocol. |
| Promotion | Existing independent evaluation/review gates; descriptive use and engineering progress remain separate from predictive promotion. |

No accepted prospective cohort start is recorded by this proposal. The retained CDI population's zero eligible five-session pairs cannot be replaced by an artifact-age count. No completion date can be computed until the actual eligible anchor/calendar and required observations are established. Historical backfill cannot be relabeled prospective.

**Smallest next deliverable:** a CCW-owner compatibility/protocol docket under this same research plan, identifying the existing evaluation entry point or explicitly recording its missing adopted contract. It must preserve S1, the forward logger and current authority. The dossier is not a new evaluator or a request to run a scheduled service.

## 6. Ordered bounded continuation

1. Reconcile the existing CDI documentation/source carrier and the incumbent owners' custody. Adopt or amend this proposal as documentation only; mark each actual decision with source/owner evidence.
2. W4: freeze the real history/term-comparability input coverage and missing dimensions. W5 may independently freeze the typed funding consumer mapping to actual supported inputs.
3. W6: use those exact source identities to prepare the #804 reference/resolver/access/parity contract. Keep unresolved types and selectors unadmitted.
4. Prospective research: freeze the protocol and identify the actual existing evaluation owner/compatible contract before claiming a cohort start. Observe real eligible evidence through incumbent ownership; no replay, new watch or synthetic time passage.
5. Qualify each subsequently adopted source delta through its existing tests/review/product gates. Source contracts, native output, browser/visual proof and production acceptance stay separately scoped.

Existing R33/Terminal review holds, the R11 administrator browser denial, the original Terminal deployment refusal, migration0038's applied-once state and all preserved workspaces remain binding. This proposal grants no exception. Tiingo intended-use licensing remains complete; technical source/current-access contracts do not reopen that decision.

## Source references

[M1]: https://github.com/mastermindx-market-intelligence/macro/blob/414d785d14e9af77c02a273f0f9829162b9cc55d/research/credit_dislocation/MASTERPLAN.md
[M2]: https://github.com/mastermindx-market-intelligence/macro/blob/414d785d14e9af77c02a273f0f9829162b9cc55d/engine/corp_credit.py
[M3]: https://github.com/mastermindx-market-intelligence/macro/blob/414d785d14e9af77c02a273f0f9829162b9cc55d/engine/credit_dislocation.py
[M4]: https://github.com/mastermindx-market-intelligence/macro/blob/414d785d14e9af77c02a273f0f9829162b9cc55d/engine/capital_structure/funding.py
[M5]: https://github.com/mastermindx-market-intelligence/macro/blob/414d785d14e9af77c02a273f0f9829162b9cc55d/engine/capital_structure/issuer_state_contracts.py
[M6]: https://github.com/mastermindx-market-intelligence/macro/blob/414d785d14e9af77c02a273f0f9829162b9cc55d/engine/credit_momentum.py
[M7]: https://github.com/mastermindx-market-intelligence/macro/blob/414d785d14e9af77c02a273f0f9829162b9cc55d/config/synapse.yml
[M8]: https://github.com/mastermindx-market-intelligence/macro/blob/414d785d14e9af77c02a273f0f9829162b9cc55d/scripts/ccw_study_s1.py
[M9]: https://github.com/mastermindx-market-intelligence/macro/blob/414d785d14e9af77c02a273f0f9829162b9cc55d/research/CCW_STUDY_S1_PREREG.md
[T1]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/afd01ea799bd9951953ef48ec6e682bad2b44143/terminal/lib/investigations.ts
[T2]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/afd01ea799bd9951953ef48ec6e682bad2b44143/terminal/lib/investigationContracts.ts
[T3]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/afd01ea799bd9951953ef48ec6e682bad2b44143/api/investigation_contracts.py
[T4]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/afd01ea799bd9951953ef48ec6e682bad2b44143/supabase/migrations/0030_investigation_kernel.sql
[T5]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/afd01ea799bd9951953ef48ec6e682bad2b44143/terminal/lib/eventWorkspace.ts
[T6]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/afd01ea799bd9951953ef48ec6e682bad2b44143/terminal/lib/investigationIssuerRelease.ts
[T7]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/afd01ea799bd9951953ef48ec6e682bad2b44143/terminal/app/api/investigations/review/route.ts
[T8]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/afd01ea799bd9951953ef48ec6e682bad2b44143/terminal/app/api/investigations/replay/route.ts
