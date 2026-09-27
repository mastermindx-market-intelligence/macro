# China Risk Radar Revalidation — Adoption and Reporting Contract

**Operation:** `cn-risk-p1-radar-revalidation-20260923-solpro-001`
**Status:** research-only Draft/HOLD guidance; no live behavior change
**Preregistration:** `db5590accaa03f78396ca91b6874f04b9bcf4cf3`
**Binding result:** `results.json` SHA-256 `ae67d4d437784ea13a59279e020911f067eede4f272289b1edda6b2d967110c7`

This contract translates the frozen revalidation into product, evidence, and governance use.
It does not create a new evidence plane, lifecycle, authority gate, probability model, or
capital-policy owner. Existing Risk Radar, Signal Lab, forward-ledger, Market State, and
adjacent China-risk PR owners remain canonical.

## Executive adoption ruling

The exact current China external-driver construction is useful as a **directional hazard
indicator**. It is not yet evidence for precision-grade state probabilities, exact band
optimality, capital sizing, or binding Market State authority.

Use the study now to:

1. preserve the external-driver construction as a meaningful hazard context;
2. explain the 98 score as a trailing-504-session composite percentile;
3. disclose reconstructed discrimination, effective episode depth, and issued-forward maturity;
4. correct historical claims that overstate exact replication or probability authority;
5. define the evidence gates for any later recalibration or authority expansion.

Do not use it now to retune probabilities or bands, change `_GROSS`, recommend a position size,
set `can_force`, originate a trade, veto a name, or overwrite the existing forward ledger.

## What the evidence establishes

| Question | Evidence | Adoption |
|---|---|---|
| `>=5% / 21 sessions` discrimination | risk-off rate 47.3% vs 28.9% base; 1.63× lift; block CI 1.24×–2.05×; 18 effective episodes | directional hazard supported |
| `>=10% / 42 sessions` discrimination | risk-off rate 44.4% vs 16.9% base; 2.64× lift; block CI 1.82×–3.59×; 18 effective episodes | strong historical discrimination, limited independent depth |
| exact risk-off H21 probability `50%` | observed 47.3%; block CI 34.8%–58.0%; episode CI 27.4%–63.7%; 18 effective episodes | `INSUFFICIENT_EVIDENCE` for exact calibration |
| elevated vs risk-off separation | +6.2 percentage-point estimate; interval crosses zero | keep ordering only with qualification |
| context gate | elevated-plus lift improves by 0.22×; block interval 0.01×–0.46×; effective N 18 | directional value-add, not promotion-grade |
| fixed 58/72/83/91 cuts | no supported material inversion; no threshold search performed | ordering survives; cutoff optimality unknown |
| CSI300 replication | exact cash-index series unavailable; 510300.SS is only an ETF proxy | `INSUFFICIENT_EVIDENCE`; do not say CSI300-confirmed |
| issued-forward evidence | 16 matured rows, 5 loud rows, 2 loud hits, 4 risk-off rows, 1 risk-off hit, 18 pending | accruing only; `can_force=false` |

The reconstructed daily row count is not the independent sample size. The loud-state ceiling of
18 episodes is the binding constraint for the exact 50% estimate, the probability ladder, band
separation, context-gate promotion, and any downstream capital claim. The headline rows above
substantially reuse those same loud/risk-off dates; they are different measurements of one small
historical episode set, not independent corroborating studies.

The point estimate is also era-dependent: emitted `>=10% / 42 sessions` lift is 2.10× before
2016 and 4.41× from 2016 onward, with chronological-half estimates of 2.29× and 3.32×. Use the
aggregate as directional evidence, not a timeless structural coefficient. Historical transforms
are causal on the latest repository snapshots, but source-vintage identifiers are unavailable;
this is reconstructed current-snapshot evidence rather than fully vintage point-in-time proof.

## Product and machine-use policy

| Consumer | Allowed now | Not allowed now |
|---|---|---|
| Risk Radar card/dialog | semantic relabeling, evidence-depth disclosure, historical-vs-forward distinction | silent probability/band changes or precision language |
| Signal Lab registry | record directional hazard and qualified provenance | “2.07× validated, CSI300-confirmed” as an unqualified current claim |
| Market State | advisory context only; preserve `can_force=false` | verdict override, veto, or binding authority |
| Portfolio / Prophet / ranking | contextual explanation only | trade origination, sizing, exit, selection, or rank changes |
| Forward-evidence system | accrue new issued rows and independent episodes | pool reconstructed history with issued forecasts |
| Research/calibration | preregister a later challenger after evidence gates mature | threshold shopping or post-hoc surface replacement |

## Where this should be reported

### 1. Canonical research record — this PR

`PREREGISTRATION.md`, `results.json`, `REPORT.md`, `data_manifest.json`, and this contract are the
canonical P1 research record. The Draft PR body should carry only the executive verdicts, key
metrics, evidence ceiling, and links to these artifacts. It must remain HOLD and must not imply a
production retune.

### 2. Existing probability-evidence plane — not a new file family

The repository already owns reconstructed probability disclosure through
`scripts/build_risk_radar_probability_evidence.py` and
`data/risk_radar/probability_evidence.json`. That implementation is currently US-specific. A future
CN projection should extend the same governed plane under a separate evidence-authority change,
with a CN-qualified schema/source contract and tests. Do not create a parallel CN evidence store.

The minimum useful CN projection is:

```text
evidence_class = reconstructed_historical
hazard_discrimination = supported_directional
probability_precision = insufficient_evidence
intensity_semantics = trailing_504_session_percentile
risk_off_h21_observed = 0.4727
risk_off_h21_effective_episodes = 18
forward_authority = false
cash_index_replication = insufficient_evidence
```

This projection is descriptive only. It must never be read by calibration, sizing, ranking,
trade-authority, or `can_force` code.

### 3. Signal Lab claim registry

The current Signal Lab prose still describes the China radar as “2.07×, p=0.01,
CSI300-confirmed.” The evidence-authority owner should replace that with qualified wording:

> External-driver hazard discrimination survives on the exact emitted production state. The
> current reconstruction estimates 1.63× lift for >=5%/21 sessions and 2.64× for >=10%/42
> sessions, with 18 effective loud-state episodes. The historical 2.07× record is not
> byte-for-byte reproducible, and exact CSI300 cash-index replication is unavailable.

### 4. Risk Radar product surface

The existing Risk Radar evidence area is the correct visible destination. Do not add another card,
alert tier, or competing confidence score. The CN surface may report:

- `98th percentile` only with “trailing 504-session composite intensity” semantics;
- the displayed H21 estimate alongside “historical model estimate; not precision-grade”;
- reconstructed risk-off observations and the 18-episode ceiling;
- issued-forward maturity separately: 16 matured / 5 loud / 2 loud hits / 18 awaiting maturity;
- `ADVISORY / DISPLAY CONTEXT ONLY` while `can_force=false`.

The UI must not imply that 98th percentile means 98% odds, that 50% is validated to actuarial
precision, or that a current risk-off state automatically binds capital.

### 5. Forward ledger and prospective evidence

Continue natural issuance. Do not backfill or mutate the 34 frozen historical rows. New international
rows need exact model-cohort identity and independent-episode accounting before they can support a
same-model recalibration claim. The episode-aware authority work remains the owner of independent-N
and authority semantics; model-identity receipts should reuse the accepted prospective pattern rather
than introduce another ledger.

### 6. Capital-policy reporting

This P1 study validates hazard discrimination, not the mapping from state to gross exposure. The
capital-policy study in Draft PR #7884 is the dedicated evidence lane for `_GROSS`. Its current HOLD ruling is
`DISPLAY_CONTEXT_ONLY` and blocks stronger sizing language pending acceptance: do not call `×0.62` a suggested size or a risk-budget reference, and do not
promote it into Portfolio, Prophet, or execution authority.

## Existing adjacent owners

| Lane | Current owner | P1 evidence supplied |
|---|---|---|
| Presentation semantics | Draft PR #7875 / P0 | percentile meaning, exact-probability caveat, reconstructed-vs-forward disclosure |
| Evidence and authority | Draft PR #7872 / P2 | effective-N ceiling, forward counts, no pooling, current `can_force=false` |
| Capital policy | Draft PR #7884 / P4 | hazard discrimination only; no sizing authorization |
| Prospective model identity | merged PR #7808 pattern | reuse exact issue/model cohort receipt design for international rows |

P1 must not duplicate or absorb those source changes. It supplies their common scientific record and
flags contradictions between them.

## Cross-lane reconciliation required before merge

P0 currently proposes showing `advisory risk-budget reference ×0.62`. P4 subsequently finds that the
issued-forward evidence is too thin to call `×0.62` a suggested size or risk-budget reference. P4 is
the specific capital-policy evidence lane; its negative result blocks P0 from shipping stronger wording
unless the Chairman accepts materially different evidence. P0 should retain the exact
factor only as clearly non-advisory research/debug disclosure, or omit it from the user-facing surface.

P2 proposes an episode-aware separation of independent episodes from raw rows. P1 additionally shows that exact state
probabilities and cutoffs remain underpowered. P2 authority maturity must not be interpreted as
probability-calibration maturity; they are separate gates.

Merged PR #7808 establishes exact model-cohort receipts for the US prospective ledger. It does not
retroactively identify the frozen international rows. A future international identity extension must
be prospective and first-writer-bound, with no backfill.

## Evidence gates for future use

| Expansion | Minimum gate |
|---|---|
| report exact 50% as calibrated | at least 20 effective risk-off episodes, >=5 hit and >=5 non-hit episodes, absolute calibration error <=10 percentage points, forecast inside block and episode intervals, nonnegative Brier skill, no supported inversion |
| promote the full H5/H10/H21 ladder | all loud-state cells meet independent-episode floors; no supported inversion; held-out/prospective comparison passes |
| claim exact band optimality | separately preregistered fixed neighborhood/sensitivity test; no post-hoc threshold selection |
| open a recalibration candidate | at least 25 matured same-model issued rows plus identifiable model cohort and independent episodes |
| grant binding `can_force` | existing production authority contract only, including episode-aware floors and conservative Wilson evidence |
| claim CSI300 replication | lawful exact cash-index history with disclosed provenance and sufficient depth |
| promote a sizing ladder | separate capital-policy acceptance with issued-forward independent episodes and explicit opportunity-cost validation |

No threshold is automatically self-executing. Meeting a research floor permits a preregistered
candidate or authority evaluation; it does not itself change production.

## Recommended execution order

1. Land this P1 package as Draft/HOLD evidence with CI ownership and exact-head review.
2. Feed the result hash and claim table into P0, P2, and P4 through PR comments; do not copy source.
3. Reconcile P0’s `×0.62` wording to P4’s `DISPLAY_CONTEXT_ONLY` ruling before either PR can leave HOLD.
4. Let P2 remain the sole international episode/authority implementation owner.
5. Extend the existing probability-evidence plane and prospective identity pattern only in a dedicated,
   no-behavior-change evidence projection.
6. Wait for natural issued-forward maturity before any separately preregistered calibration or sizing candidate.

## What must not be redone

- Do not rerun the P1 study on a changed construction and call it the same preregistered result.
- Do not use the ungated counterfactual to reproduce the historical 2.07× record.
- Do not quantify 510300.SS as confirmatory CSI300 evidence in this operation.
- Do not merge reconstructed and issued-forward evidence.
- Do not create another probability-evidence JSON, ledger, authority gate, or UI panel.
- Do not let semantic disclosure become probability, sizing, ranking, or trade authority.
