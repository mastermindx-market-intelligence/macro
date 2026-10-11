# Communications A1 — Focused Review and Implementation Amendment

**Date:** 2026-09-24. **Operation:** `gmi-communications-research-20260923-sol-001`.
**Carrier:** Macro Draft/HOLD PR #7794, `claude/communications-sector-research-20260923`.
**Disposition:** Sol-authored review and revised implementation requirements, ready for independent/shared-owner review. This is not independent approval, shared-contract acceptance, product code, native data admission, or a Fable START.

## 1. Scope and precedence

This amendment is part of the Communications design bundle. It replaces only the first-vertical numeric-adapter and comparison-rule instructions identified below. The original research, four-company scope, compact Theme Tracker interaction, company/watchlist journey, broader sector roadmap, and all existing authority/privacy constraints remain intact.

Baseline specification: `docs/superpowers/specs/2026-09-23-communications-business-intelligence-design.md`, commit `d65263dc15a8dc3ddded35b1529c535c881175bd`, blob `2cf3918e95715cd924a5a5f402201e4053e2a036`.
Baseline plan: `docs/superpowers/plans/2026-09-23-communications-advertising-vertical-implementation.md`, commit `13b130c887353b716385552db96c8505af0efe02`, blob `c10e77b22e131ad39ab210d860f9a855a62be027`.
Baseline examples: `research/communications/COMMUNICATIONS_FIRST_VERTICAL_PROOF_CASES_2026-09-23.md`, commit `55f35e395ed4f29a77d54543b232da0bb559c69c`, blob `0356b8bf30ab7a97329da0257754f63401eb1f71`.

The controlling A1 design is the baseline plus this amendment, not either document in isolation. This is explicit versioned supersession, not another source-of-truth service. Implementers read this document before copying a baseline example. The original proposed interface block is not executable acceptance evidence and must not be implemented unchanged.

Protected procedure: Mastermind `6ffb3389635a5344df91765689acc48cf5499f60`, compatible Skillpack 1.0.1/bootstrap 1. Fresh required-file reads returned unchanged applicable procedure blobs. Native-interface investigation uses Macro `c52d80a1cc7a6d770e44c9f263c900b40895e930`; no rebase, product write or source-custody transfer occurred. Local baseline bytes were checked against the two Git blob identities above.

## 2. Review findings: enforce the promised behavior at the actual interface

### A1-R1 — Rounding and intervals disappeared before comparison

The specification requires an indeterminate outcome when rounding crosses a guidance boundary. The plan's `Measure` contains one Decimal value but no interval or rounding provenance; two sources displaying 100, one exact and one rounded, cannot carry their difference through that adapter. The plan also discusses interval actuals without giving the comparator their bounds.

**Repair:** carry source-defined uncertainty through the private, in-memory measure adapter. Reported display precision is not automatically a rounding method. Unknown rounding remains unknown. This is not a second persisted number or permission to manufacture a confidence interval.

### A1-R2 — Definition identity was confused with comparability

A current result, prior-period result and original outlook normally have different source selectors and may have different definition references. Raw equality of `definition_ref` can reject a valid comparison. Matching only labels, units or a model's assurance can accept an invalid one. The baseline prose invokes a reviewed recipe, but the public comparison signatures and result receipt do not identify the rule applied.

**Repair:** add an explicit, immutable, reviewed comparison-rule argument and return its revision with every result. The rule binds exact input roles, definitions, populations, periods and any bridge. It is local content of the existing F04 consumer recipe, not a new metric registry, runtime permission service, evaluator or store. An endpoint cannot supply or modify it.

### A1-R3 — A reference set did not establish cash-component meaning

`expected_refs` proves set membership, not whether one receipt is CFO, capital investment, finance-lease principal, an already-netted subtotal or an alternative sign convention. It also does not stop two distinct receipts for the same economic component being added twice.

**Repair:** the reviewed cash recipe binds a component key, role, input reference, source orientation and coefficient for each component. No sign is inferred from typography or current value. Reject duplicate components, duplicate references, omitted required components and a net subtotal combined with its constituents.

### A1-R4 — Private storage capability is not the GMI publication binding

A current private Research Vault adapter and an earnings-specific entitled publication path exist at the source pin. That is a reusable storage/authentication substrate, not proof that GMI assertions are admitted there. Re-labeling earnings payloads as GMI records would violate their closed identity and schema contracts.

**Repair:** name the real existing substrate, retain the earnings domain boundary, and require the incumbent GMI/private-publication owners to establish an approved binding before real rows. Do not ask an engineer to create a parallel bucket, pointer service, raw credentials path, queue or fallback evidence file to make the demo work.

### A1-R5 — A local artifact is not an accepted live identity result

A bounded authorized metadata read found a local Macro checkout at `20c950b081773cd5ecc04815275c28b32e49b879` with security-master and GMI identity-resolution artifacts. This is neither the current interface pin nor deployment proof. A follow-on local inspection was blocked before dispatch by the platform's safety-status check. No identity rows, schema validation or production generation were thereby verified.

**Repair:** preserve the distinction between artifact existence and an accepted identity/route receipt. The blocked action was not retried, rephrased, moved to another host/tool/model or delegated around. The exact denied local inspection remains frozen pending actual platform authorization/recovery. Normal independently permitted source/design work continues; this does not establish that all remote tools or all identity services are unavailable.

## 3. Replacement numeric adapter contract

The native assertion retains its existing `observation.value`, `value_high`, unit and precision. Add optional source-rounding meaning within the proposed shared `measurement_context`: `rounding_kind` (`exact`, `nearest`, `unknown`), nullable positive `rounding_quantum`, and nullable immutable `rounding_method_ref`. These fields are subject to the shared owner's acceptance. A legacy assertion without those fields is valid; its rounding is unknown, not exact. An explicitly reported interval continues to use the native bounds and inclusivity fields.

A nearest-rounding interval may be derived only with a reviewed method/quantum. Its conservative support is `[x-q/2, x+q/2]`; retaining both endpoints avoids inventing a tie-breaking rule. An exact point supports `[x,x]`. Source-reported finite intervals preserve inclusivity. Unknown rounding produces no asserted underlying interval. The stated number can still be displayed and used in an explicitly labeled published-figure calculation, but it cannot establish an exact underlying threshold outcome.

The baseline in-memory types gain these REQUIRED fields; no production wire or native identity is introduced by the type names:

```python
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

@dataclass(frozen=True)
class Interval:
    lower: Decimal
    upper: Decimal
    lower_inclusive: bool
    upper_inclusive: bool

@dataclass(frozen=True)
class InputBinding:
    role: str
    ref: str
    definition_ref: str
    population: str
    period: tuple[str, str]
    unit: str
    currency: str | None
    scale: Decimal
    domain: str

@dataclass(frozen=True)
class CashRole:
    component_key: str
    binding_role: str
    orientation: Literal['signed_flow', 'positive_magnitude']
    coefficient: Literal[-1, 1]

@dataclass(frozen=True)
class ComparisonRule:
    revision: str
    operation: Literal['period_absolute', 'period_pct', 'guidance', 'cash']
    bindings: tuple[InputBinding, ...]
    relation_ref: str
    review_ref: str
    interpretation_basis: Literal['underlying_interval', 'published_figures']
    cash_roles: tuple[CashRole, ...]  # empty except for operation='cash'

@dataclass(frozen=True)
class CashComponent:
    component_key: str
    measure_ref: str
    orientation: Literal['signed_flow', 'positive_magnitude']
    coefficient: Literal[-1, 1]
```

`Measure` keeps all baseline fields and additionally requires `unit: str`, `support: Interval | None`, `support_basis: Literal['exact','source_interval','reviewed_nearest','unknown']`, and `support_ref: str | None`. The support is derived from that native observation and approved source method, not freely supplied by a caller. Finite source-interval actuals may have `value=None` while support is known; unknown actuals have neither. An unbounded actual is displayed but not numerically classified by A1.

`Guidance` keeps baseline bounds and additionally requires `unit: str` and `bounds_basis: Literal['stated_threshold','approximate','unknown']`. An approximate outlook is not silently converted into an exact floor or range. Explicit issuer target bounds are documentary thresholds; a model-created range is not company guidance.

`Result` keeps its baseline fields and additionally requires `rule_revision: str`, `formula: str`, and `interpretation_basis: str`. A qualified or unavailable result preserves the rule/input references and reason. These derived receipts live only in the existing F04 output, not a second ledger.

Replacement function signatures:

```python
# Private, pure functions over accepted owner-reader inputs; not HTTP parameters.
# compare_period(current, prior, *, rule: ComparisonRule, mode='pct') -> Result
# compare_guidance(actual, guide, *, rule: ComparisonRule) -> Result
# cash_bridge(*, measures: tuple, components: tuple[CashComponent, ...],
#             rule: ComparisonRule) -> Result
```

The unit/scale check uses the rule's explicit normalization. A USD-million guide may match a USD-thousand result after conversion. Percent, fraction, percentage-point change, users, accounts and currency are not interchangeable. No FX conversion is introduced in A1. Decimal values reject booleans, nonfinite values, malformed strings and pathological exponents/lengths before arithmetic; use the existing bounded contract utilities where available.

The approved numeric domain must agree at the native definition, input binding and consumer recipe. A caller cannot make a negative camera count valid by changing its predicate/domain label. Losses and signed cash remain representable. A source-defined exceptional negative revenue case requires its own reviewed domain and cannot weaken every revenue metric.

## 4. Comparability and threshold semantics

A comparison rule carries exact current/prior or actual/guide roles. A same-quarter prior-year relationship is explicit in the two bound intervals; it is not inferred merely because two periods last approximately three months. Guidance requires a matching target period. Definition references can differ only where the rule's `relation_ref` records a reviewed same-definition or accepted restatement/bridge relation. A dictionary of synonyms is not such evidence. Missing relation/review or a mismatched input produces INCOMPATIBLE/UNAVAILABLE, leaving reported levels visible.

Every comparison uses the current admitted input generation. Replacing an input with a corrected reference requires a newly bound rule/output revision or the accepted recipe owner's equivalent invalidation process. Do not allow stale rules to silently accept a changed source. Unaffected rules remain reusable. A branch of unresolved source corrections is a visible conflict, not an instruction to choose the largest value or latest URL timestamp.

For underlying-interval guidance comparisons, classify only when every feasible actual value implies the same result. A support crossing a boundary is `QUALIFIED / ROUNDING_INDETERMINATE`, never a forced beat/miss. Equality at an inclusive floor satisfies the stated threshold; equality at an exclusive floor is an excluded boundary, not a value below that floor. Similar rules apply at ceilings. An interval with zero width and an excluded endpoint is invalid, not a usable exact point.

Published-figure comparison is a separate documentary statement. It can report the displayed values and their difference with `interpretation_basis=published_figures`; unknown rounding adds a qualification and prevents an exact underlying-economic claim. The UI may say “reported figure equals the original floor; exact comparison is indeterminate.” It must not convert that result into a consensus surprise or an investment verdict.

An approximate guide supports a labeled difference from the published reference, not a new exact threshold or fictitious confidence interval. A dated original guide remains original even if later revised. Repeating it in a newer release does not refresh its original publication time. None of these source clocks establishes an intraday historical knowable cutoff without the owner evidence.

## 5. Cash reconciliation with role-bound inputs

For each cash formula the existing reviewed consumer recipe names exact component keys, references, periods, entity scope, accounting basis and orientation. `signed_flow` means the source already expresses the effect on cash; `positive_magnitude` means the rule supplies whether to add or deduct it. Coefficients belong to the approved rule's `cash_roles`, never request input or a heuristic based on the observed sign. Every supplied CashComponent must match its CashRole and the referenced InputBinding exactly; non-cash rules require an empty cash_roles tuple.

Synthetic examples: CFO 100 and signed investment outflow -60 with coefficients +1/+1 produce 40. CFO 100 and a positive investment magnitude 60 with coefficients +1/-1 also produce 40. Feeding -60 into the positive-magnitude contract refuses; it must not produce 160. Two different receipts both assigned `capital_investment` refuse even if their reference IDs differ. Missing lease principal cannot be treated as zero where the selected company's formula requires it.

A signed consolidated source FCF can be displayed directly when the source reports it. Reconstructing the formula is a separate derived result. Do not count both that result and its component cash flows as additional independent evidence or sum them together. A real company-specific formula stays company-specific; it does not create a uniform peer ranking.

## 6. Existing private substrate and qualification boundary

Fresh canonical source reads at `c52d80a1cc7a6d770e44c9f263c900b40895e930` establish:

| Source | Blob | Bounded finding |
|---|---|---|
| `app/earnings.py` | `3b8251388c8e9ae59b933212a7384faaea61eb27` | Entitlement precedes use of the existing Research Vault adapter; private error handling and receipt-backed reads are present in source |
| `engine/research_vault/r2_store.py` | `139fcbe8cf08945a2be1feaa0dca5428c818837b` | Existing private object-store interface, strict bounded reads and conditional-write capability declarations; not proof of current deployed configuration |
| `engine/earnings_narrative/private_publication.py` | `0ee93909693893f419f0109f9eba1994d94e2b46` | Earnings-specific immutable artifacts, manifest/pointer and closed record identity; not a generic GMI assertion publisher |
| `contracts/theme_graph/evidence.v1.schema.json` | `83dece15e98b9c8775a584afcd6ee09811dad220` | The inspected closed evidence schema still has no `curation_assertion` property |

The existing store exposes more than one bounded-read protocol shape. Select the exact implemented capability required by the admitted consumer; similar method names do not prove signature compatibility. Never fall back from strict reads to a fail-open method to convert unavailability into an empty dataset. Verify object size before unrestricted buffering, exact digest after read, and authoritative not-found separately from denial/timeouts.

The shared GMI/private-publication owner must supply the actual binding, admission writer, private retention pointer, generation, current-rights disposition, strict-reader contract and public-emitter exclusions. This is a prerequisite receipt under the existing owners, not a new binding registry. Do not alter an earnings prefix, write GMI data into earnings payloads, allocate a parallel bucket or set an alternate production data root as a shortcut. If an existing approved GMI binding is found, consume it after compatibility checks; if none exists, the shared owner must resolve the architecture before live admission.

A successful remote metadata read established local artifact presence only. The denied follow-on local inspection is action-scoped and is not retried through another worker or account. No production private credentials, bucket values or individual identity rows were read in this phase. Actual source/identity and alternate-mirror proof remain open.

## 7. Exact changes to the eight-task plan

- **Task 1:** add rounding meaning to the same proposed shared measurement context; enforce definition-bound signs and preserve physical guards. No new schema family or general metric registry.
- **Task 2:** round-trip new context through the actual native codec/column/reader; keep unknown rounding and all source clocks. Legacy absent/null rows remain valid. K1 stays pointer-only and retains unsupported-join refusals.
- **Task 3:** replace the old adapter/function block with sections 3–5 above. Update every fixture/helper call to supply units, support/basis and an explicit reviewed rule. A test-only factory must label its synthetic review, never be callable as production admission.
- **Task 4:** include the rule revision, basis and full input references in each derived result; invalidate affected outputs on correction. Fixed four-company coverage and independent evidence blocks remain unchanged.
- **Task 5:** require the actual private binding before data reads, retain auth-before-read and private headers, and keep sources/rules/paths/formulas off HTTP input.
- **Task 6:** render indeterminate, approximate and published-figure states as useful explanations, not missing-value zeros or beat/miss icons. Preserve session/logout and compact-layout behavior.
- **Task 7:** qualify the real shared binding and current identity/route receipts. Local file existence or old schema examples do not close either gate. Do not repeat the denied local inspection as a delegated workaround.
- **Task 8:** independent review must exercise the new cases below as well as CRV-01 through CRV-40. Author self-review and reference arithmetic are not that independent gate.

Concrete test intentions for Task 3: source-defined nearest-rounded actual 100 at quantum 1 versus an inclusive floor 100 must be indeterminate; actual 101 under that same method satisfies the floor. An exact actual of 100 satisfies an inclusive floor, but not an exclusive one. Actual 1500 in USD thousands and guide 1.5 in USD millions are equal after an approved scale conversion. An actual/prior definition pair with different IDs passes only with its exact accepted relation. A changed input ref under the old rule refuses. Cash examples in section 5 must produce 40, 40 and refusal respectively. These are future application tests; the local review experiment only checks the arithmetic and specification consistency.

## 8. Additional acceptance requirements

CRV-01 through CRV-40 remain required. These twenty cases extend their coverage; they are not executed product-test passes.

| ID | Required behavior | Task |
|---|---|---|
| CRV-41 | Exact and rounded display-equal values remain distinguishable through the adapter | 1–3 |
| CRV-42 | Unknown rounding never defaults to an exact underlying interval | 1–3 |
| CRV-43 | Boundary-straddling support renders an indeterminate comparison | 3,6 |
| CRV-44 | Exclusive equality differs from inclusive equality | 3,6 |
| CRV-45 | Uncertainty bounds receive the same scale conversion as values | 3 |
| CRV-46 | Approximate outlook cannot become an exact floor | 3,6 |
| CRV-47 | Different definition IDs can compare only via the exact reviewed relation | 3 |
| CRV-48 | Same metric label with a different population still refuses | 3 |
| CRV-49 | Same duration is insufficient for a prior-period match | 3 |
| CRV-50 | Missing rule/review receipt cannot fall back to label matching | 3–5 |
| CRV-51 | Corrected input reference invalidates the old bound result | 3,4 |
| CRV-52 | Native definition, numeric domain and recipe agreement are all required | 1,3 |
| CRV-53 | Percent, fractional rate and percentage-point change do not silently interchange | 1,3 |
| CRV-54 | Cash role and source-sign orientation prevent subtracting an outflow twice | 3 |
| CRV-55 | Two receipts for the same cash component cannot be added twice | 3 |
| CRV-56 | An already-netted subtotal cannot be combined with its own constituents | 3 |
| CRV-57 | A strict-read outage/denial is not authoritative absence or an empty ready panel | 5,7 |
| CRV-58 | Existing private earnings infrastructure does not confer a GMI publication identity | 2,7 |
| CRV-59 | Source-only identity/artifact presence cannot enable a verified stock route | 4,7 |
| CRV-60 | Private rights/identity changes invalidate affected cached view material before serving | 4–8 |

CRV-60 uses existing session, rights and source-generation owners. A view fingerprint includes their applicable generation/decision receipts as well as input and recipe revisions. It excludes a volatile build timestamp but does not exclude material authorization state. No new polling or permission service is introduced.

## 9. Review result and delivery boundary

The focused review found and specified repairs for three numeric-interface defects and qualified two deployment assumptions. The changes are intellectual/design deltas, not a shipped capability. The baseline company facts were not re-audited and no new market or forecasting claim is made. Reference examples are synthetic unless explicitly drawn from the unchanged baseline source pack.

Independent/shared-owner acceptance, exact production private binding, current four-company identity routes, native source admission, application tests, CI, deployment and browser/watchlist proof remain required. The Fable packet may carry these explicit gates; it must not label them complete. Fable should retain shared architecture, privacy/custody reconciliation and final integration; bounded coding/testing belongs to the least-scarce capable admitted workers.

The unassigned packet is a preparation artifact. No eligible concrete Fable receiver or Executive START was established in this phase. No worker-specific watcher or broadcast commission is justified by packet existence. Keep PR #7794 DRAFT/HOLD until a scoped release ruling; do not manufacture an automatic background continuation.
