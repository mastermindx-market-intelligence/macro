# Independent review: Options Intelligence research design

**Review date:** 2026-10-03.  
**Reviewer:** bounded independent conversation research worker.  
**Scope:** `MASTER_PLAN.md`, `CONTRACTS.md`, `RESEARCH_PROTOCOL.md`, and `ROADMAP_AND_HANDOFF.md` in `/workspace/scratch/304dc2fae6f2/options-research/`. This review examines the draft specifications, not the implementation or production state. No source files were edited, no new broad literature search was performed, and no runtime, provider login, agent dispatch, or GitHub write was attempted.

## Disposition

The documents support a coherent next research checkpoint and concrete owner-specific semantics/numerical work. They correctly preserve the existing retrospective, distinguish observation from prediction and execution, and acknowledge the incumbent strict candidate schema and false authority flags.

**Resolve R1–R4 before accepting the affected contracts as implementation-ready or running a confirmatory study.** R5–R8 are specific definition/evaluation clarifications to incorporate before the corresponding feature or pilot is frozen. These findings do not prevent continuing the evidence and owner-brief work. No new authority-activation or competing-owner blocker was found in the four reviewed prose drafts.

The principal has already acknowledged the first three findings and described intended fixes. This report records the reviewed, pre-fix text; it does not certify those fixes. The integrated checkpoint should append a disposition for each finding and identify the exact revised source hashes.

Severity below concerns acceptance of the affected specification: **High** means a plausible wrong mathematical interpretation or invalid evaluation can follow; **Medium** means a concrete ambiguity or validation gap must be closed before the relevant study/use. Neither designation alleges an already-deployed defect.

## Reviewed source identities

| File | SHA256 observed during review |
|---|---|
| `MASTER_PLAN.md` | `2d141e0717cf627b1ad5b8ff9295d7205fb531b8173b30f338c0c5eb4d1a821d` |
| `CONTRACTS.md` | `49297779117666a0a0d4d14322cedf389efe5a39783532cd32b2c443c6cb3f32` |
| `RESEARCH_PROTOCOL.md` | `fc4e5e88a22b40a33aa4d2c3eb62f92c06bf49f049c3da91743d2b54580682ac` |
| `ROADMAP_AND_HANDOFF.md` | `b8de61a7f5c4f8d00fe267265586a111bea1b8e0768005491c1e886fe53e5ff9` |

Line locations below refer to the initial reviewed draft. Later edits can shift them.

## Findings

### R1 — High: portfolio sensitivity and hedge-transaction signs need distinct labels

**Sources:** `CONTRACTS.md` §4, lines 48–59; §5, lines 70–72.

The vanna/charm rows are named hedge sensitivities but contain positive portfolio delta changes. Section 5 defines hedge shares as the negative of portfolio delta shares. These quantities therefore have opposite signs. The gamma row also needs to say precisely that it values the change in delta shares at fixed reference spot; its formula is not the full derivative of the portfolio's dollar delta.

For one underlying, let `A = Σ n m Δ` be portfolio delta shares, `B = −A` hedge shares, and `D = S A` portfolio dollar delta. At fixed IV/time:

- A small spot shock changes delta shares by `dA ≈ Σ n m Γ dS`.
- Hedge trade notional at reference spot is `S dB ≈ −S Σ n m Γ dS`.
- Full dollar-delta change is `dD = A dS + S dA`; it includes the existing-delta term.

**Checkable witness:** for one 100-multiplier long option at `S=100`, `Δ=.50`, `Γ=.02`, a one-dollar spot rise produces approximately two additional portfolio delta shares. The gamma row gives `+200` currency units of fixed-spot portfolio delta-change sensitivity; the hedge sells two shares, approximately `−200` at reference spot or `−202` at the scenario price 101. Full portfolio dollar delta rises approximately `252`, not `200`.

**Resolution:** name the positive rows portfolio delta-share/notional sensitivities, define their fixed-price convention, and explicitly negate them for hedge transactions. Preserve section 5's exact `H = S* (B*−B0)` definition. State that a book is scoped to one hedge underlying/currency unless a vector hedge and currency conversion contract is supplied. Require a long/short call/put sign witness and a fixed-spot versus full-dollar-delta witness in W2.

### R2 — High: input availability is insufficient to prove consumer PIT eligibility

**Sources:** `CONTRACTS.md` §1, lines 15–20; proposed feature minimum, lines 84–107.

The prose correctly requires both inputs and the feature artifact to be available before the candidate decision. The conceptual minimum records `max_input_available_at` and `computed_at`, but no explicit artifact publication/availability or consumer receipt witness. An implementation can satisfy the visible fields while consuming an artifact that arrived after the purported decision.

**Checkable witness:** all inputs are available at 09:59, computation completes at 10:00, publication occurs at 10:02, and the candidate is dated 10:01. Input and computation checks pass, but the feature was unavailable to that decision.

**Resolution:** reference or record the exact artifact revision's availability/publication and actual consumer receipt, preserving the incumbent producer clocks. For a captured decision, demonstrate an ordering equivalent to input availability → computation completion → publication/availability → consumer receipt → decision, allowing only documented clock precision/uncertainty. Do not invent an original consumer receipt for historical recomputation. A computed timestamp alone is not distribution proof. The principal's proposed explicit artifact-availability addition addresses this finding if its receipt semantics are retained.

### R3 — High: distinguish the incumbent baseline from an options-free ablation

**Sources:** `RESEARCH_PROTOCOL.md` §5, lines 67–74; `MASTER_PLAN.md` §6, line 91; `ROADMAP_AND_HANDOFF.md` §3, item 3.

The roadmap correctly warns that GEX can enter a C1/Prophet path. The protocol nevertheless describes the current Prophet-containing baseline as price-first. Holding that model's version constant does not make its upstream information options-free. In addition, an incumbent candidate cohort may already have been selected using options information.

**Checkable case:** a baseline Prophet score already consumes GEX. Adding a new options family tests incremental value beyond that incumbent score; it does not estimate the value of options versus prices alone. An options-selected candidate sample further conditions the estimand even if the score is ablated.

**Resolution:** maintain (B0) an audited options-free research comparator, where feasible, (B1) the actual incumbent baseline with all upstream options lineage recorded, and (B2) B1 plus the new family. Make B2-versus-B1 the operational incremental comparison; treat B0 comparisons as separately named diagnostics/estimands. Freeze the candidate selection rule and report its options dependence. Every fitted baseline or upstream score needs a training/availability receipt for the evaluated period; a current code version applied retrospectively is insufficient. Do not alter production scoring as part of this research ablation.

### R4 — High: validation-label maturity must be enforced at the final test boundary

**Sources:** `RESEARCH_PROTOCOL.md` §4, lines 57–63; frozen packet, line 36.

The explicit purge instruction removes training observations whose labels overlap validation/test. It should also prohibit validation, tuning or calibration labels that mature during the final test from determining the test model. The general embargo language is sound but does not supply this necessary boundary condition.

**Checkable witness:** a validation candidate immediately before the test start has a 21-session label. If its completed outcome is used to choose the model for the first test day, returns from inside the test span influenced that choice despite the candidate's decision date being in validation.

**Resolution:** for every fit, tuning, calibration or model-selection stage, require the maturity/availability of every used label to precede the stage's model-freeze time; that model must then be available before its first evaluation decision. Purge validation/calibration boundary rows as well as training rows when necessary. Apply the same rule at each rolling fold. An acceptance fixture should fail the 21-session example and late-revised outcome data. Existing training-only transformations and untouched-test requirements should remain.

### R5 — Medium: variance notation and Greek scaling remain ambiguous

**Sources:** `CONTRACTS.md` §4, lines 48, 55, 60–62.

The variance-gap row defines `RV_H` as realized variance, while the next paragraph uses `IV−RV` and `IV²−RV²`, implicitly making RV a volatility. Applying the latter notation to the former variable squares an already-squared quantity. Vega also appears without an explicit derivative/price-unit definition; this matters because the `.01` conversion assumes vega per decimal-volatility unit, not an already per-vol-point vendor field.

**Resolution:** use separate names such as `RVar_H`, `RVol_H`, and `σ_Q,H`. Define the variance gap as `σ_Q,H² − E_t[RVar_H]`. If displaying a volatility gap, specify whether the physical quantity is `sqrt(E_t[RVar_H])` or `E_t[RVol_H]`; these need not coincide. Define `V` in the Greek notation as model value per quoted unit and `Vega = ∂V/∂σ` with σ decimal annualized volatility. Normalize vendor Greeks to this convention before multiplication by the contract multiplier or `.01`. Record already-scaled inputs to prevent double conversion.

### R6 — Medium: P6 must not calibrate a cost model against its own simulated costs

**Sources:** `RESEARCH_PROTOCOL.md` §3 pilot table, line 49; `CONTRACTS.md` §8, lines 152–154; `MASTER_PLAN.md` pilot P6.

The P6 primary question asks whether the cost model explains observed or conservatively simulated expression costs. If those simulated costs are generated using that same cost model, agreement is numerical consistency, not execution calibration. The exact-option contract already correctly distinguishes bounded simulation from observed fill evidence; the pilot row should preserve this distinction.

**Resolution:** define separate acceptance tracks: numerical correctness and scenario sensitivity for bounded simulation; independent held-out execution/quote-to-fill evidence for actual cost calibration. A conservative assumption is not automatically an empirically validated bound. The simulator can support explicitly conditional economics, with entry/exit and missingness rules, but its self-generated outcomes cannot establish model accuracy or live fill feasibility.

### R7 — Medium: P1 needs a label-observation plan, not only a frozen precision target

**Sources:** `RESEARCH_PROTOCOL.md` §3 pilot P1, line 44; population construction, lines 55–57.

The P1 outcome is deliberately still to be selected with its owner. Its preregistration must address which candidates receive labels. If only historically reviewed/admitted candidates have an outcome, a new top-K review ranking cannot be evaluated fairly by treating unreviewed items as failures or silently dropping them. Historical acceptance itself can also be circular ground truth for a model designed to mimic that review.

**Resolution:** preregister the review budget K, independent definition of useful discovery, and label collection for the union of compared top-K sets or an appropriate blinded/sample-based adjudication design. Alternatively, use an objectively observable future outcome for all eligible candidates and name that estimand. Record label propensity/coverage and unresolved outcomes. Existing population waterfalls help but do not alone solve selective labels. This is a concrete W3 dependency, not evidence that P1 currently fails.

### R8 — Medium: conditional hedge direction is not an identified price-impact effect

**Source:** `MASTER_PLAN.md` executive description, line 12; compared with `CONTRACTS.md` §5, lines 70–74.

The executive description says a stated inventory scenario would amplify a move. Whole-book delta repricing can establish procyclical or countercyclical hedge transactions under the assumed hedge rule. It does not by itself identify how those transactions move prices; liquidity, execution behavior, offsetting flows and other inventory remain outside that calculation.

**Resolution:** say the inventory scenario implies procyclical hedge demand, or amplification pressure conditional on the stated execution/impact assumptions. Reserve a numerical or causal amplification claim for a separately specified impact model and evidence. This keeps the executive wording aligned with the appropriately cautious mathematical contract and the conflicting 0DTE evidence.

## Checks that passed within scope

- **Candidate schema and authority:** the draft explicitly recognizes `additionalProperties: false`, no existing extension slot, the need for a compatible schema/version/consumer change, and all 15 false candidate authority flags. It also warns against assuming episode/expression authority dictionaries are interchangeable. No silent payload insertion is authorized by the text. Actual schema contents remain a source-verification dependency.
- **Existing nulls:** the drafts retain #8286, its family-limited BH result, prior eras, non-rejections and the prohibition on recreating the same study. They do not claim that failure to reject proves no possible options information. The exact result hashes/statistics were not recomputed in this review.
- **Multiplicity:** the template requires preregistered primary families, limits interactions and rejects post-hoc promotion from diagnostics. It distinguishes within-family BH from global/adaptive discovery and policy approval. A concrete test family, dependence assumptions and repeated-look rule still need freezing in W3, as the draft acknowledges.
- **Literature interpretation:** the opening-flow observability gap, borrow-fee challenge, risk-neutral versus physical risk distinction, source versioning and 0DTE manuscript overlap are represented with appropriate limits. R8 is the notable residual wording overreach.
- **Mathematical architecture:** repricing the whole assumed book, retaining multiple gamma crossings, evaluating gamma sign at actual spot, and treating time/IV/mark/model jointly are sound specification choices. Their implementation and numerical witnesses were not reviewed here.
- **Research versus implementation:** numerical and observation-only corrections can proceed through incumbent owners without waiting for alpha; predictive policy remains separately gated. No instruction in the four drafts authorizes bypassing runtime, publication or placement holds.

## Is the next work concrete?

**Yes, for W1/W2 and preparation of W0/W3.** The roadmap identifies the relevant incumbent carriers, finite semantics/math defects, deliverables, current-owner reconciliation and acceptance witnesses. A next-turn worker can produce an owner-specific correction brief without choosing a new architecture or repeating literature collection.

**No, for a confirmatory empirical run or broad predictive implementation yet—and the documents correctly say so.** The pilot universe, one primary target/horizon per empirical family, target loss/minimum useful effect, source availability, borrow-data estimand, untouched evaluation span and feasible effective sample size still need explicit accepted values. P1 additionally needs R7's label plan; P6 needs R6's evidence track. W3 should instantiate these values in a finite study packet, rather than merely copying the template.

The next checkpoint can therefore accept corrected research contracts, record these pending empirical gates, and issue bounded owner briefs. It should not describe the six-family pilot as already preregistered, implementation-accepted, calibrated or profitable.

## Inherently unverified in this review

This review did not inspect the final catalogue, the incoming Macro census/mechanics witness, current PR diffs, deployed code, runtime data, provider entitlements, raw trades, current strict JSON schemas, real-time clock quality, execution fills or underlying #8286 data. Consequently it cannot certify actual Greek correctness, dealer positions, source freshness, production influence, schema compatibility, evidence hashes from other carriers, causality, statistical power, alpha or option economics. Those are evidence dependencies, not implied failures.

The report is a document-level independent review. Closing its findings improves the plan; it does not substitute for exact-source review, numerical verification, frozen empirical evaluation or the incumbent authority/release process.


## Post-fix bounded recheck — 2026-10-03

**Scope:** recheck of R1–R8 only in the four revised prose drafts. This is not a new broad review. The original findings above remain the record of the pre-fix text.

### Revised source identities

| File | SHA256 at recheck |
|---|---|
| `MASTER_PLAN.md` | `26826d35db7e41bc8a692680b308142188c4de2856e11023194a19556f92fd38` |
| `CONTRACTS.md` | `e2a8ced5a769996a8b46a737db07d33ce6a9571b8838d763447d5c2e19514db5` |
| `RESEARCH_PROTOCOL.md` | `53d7f5264d6145f798cfe89115a5fe9b574e0c4c6894394c3494f3dd30d135d1` |
| `ROADMAP_AND_HANDOFF.md` | `a56b1c0d6b017c2afea064b24247e691d9fd2846a51e8014ad3225ec61a5ed43` |

### Resolution status

| Finding | Status | Checked source | Resolution / remaining condition |
|---|---|---|---|
| R1 | **resolved-at-specification** | CONTRACTS §4–§5 | Positive portfolio sensitivities are named separately from opposite-signed hedge changes; gamma is explicitly only the delta-change component. The book has one hedge underlying/currency; cross-book aggregation requires a vector/FX contract. |
| R2 | **resolved-at-specification** | CONTRACTS §1 and feature minimum | The artifact revision, publication/materialization time and consumer receipt are explicit. Input/computation/artifact/receipt/decision ordering includes clock-uncertainty treatment and preserves producer clocks. |
| R3 | **remaining: one pilot-row wording inconsistency** | RESEARCH_PROTOCOL §5; MASTER_PLAN §6/§9; RESEARCH_PROTOCOL P2 | B0/B1/B2, incumbent-primary incrementality, options-dependent cohort selection and fitted upstream historical availability are now explicit. The P2 row still says "over the same price-first model". Replace that phrase with the incumbent B1 comparison to make it match the now-explicit primary estimand. The substantive baseline design is corrected. |
| R4 | **resolved-at-specification** | RESEARCH_PROTOCOL §4; MASTER_PLAN §9 | All fitting, tuning, selection and calibration labels must mature and become available before model freeze/first test decision. The H21 validation-boundary example is explicitly excluded. |
| R5 | **resolved-at-specification** | CONTRACTS §4 | RVar and RVol are separate; variance-gap notation is consistent. Vega is defined as dV/dsigma for decimal annualized volatility, with model value per quoted unit. Concrete vendor conversions remain implementation qualification. |
| R6 | **resolved-at-specification** | RESEARCH_PROTOCOL P6; CONTRACTS §8 | Deterministic quote/cost arithmetic and simulation sensitivity are separated from forecast-cost evaluation against observed fills with separate calibration/evaluation samples. |
| R7 | **resolved-at-specification** | RESEARCH_PROTOCOL §4 | Objective outcomes use the full frozen eligible population. Review-dependent outcomes require a prespecified blinded/random audit with known sampling probabilities, or an explicitly labelled-population claim. Unreviewed is not negative. |
| R8 | **resolved-at-specification** | MASTER_PLAN §1; CONTRACTS §5 | The executive text now describes procyclical hedge demand. Price amplification/dampening requires an additional impact/liquidity model or empirical identification. |

**Result:** seven findings are resolved at specification level. R3’s substantive design is corrected, with one residual P2-table phrase still to align. No other unresolved condition within R1–R8 was found.

**Remaining gates:** selecting actual W3 values, proving source/clock/field availability, implementing and testing the contracts, collecting independent labels/fills, performing untouched empirical evaluation, and obtaining incumbent authority/release acceptance remain owed as already stated in the drafts. A specification resolution does not certify any of those outcomes. ROADMAP_AND_HANDOFF retains the separate structural, predictive and economic gates.

The principal reports separate byte-equal mechanics reproduction and a five-case IV/TTE check. This reviewer did not run or independently verify those numerical checks and does not certify them. No implementation acceptance, empirical acceptance, production readiness, runtime clearance or predictive/economic claim is conferred by this recheck.


## Principal integration disposition — 2026-10-03

The independent recheck resolved R1, R2 and R4–R8 at specification level. Its remaining R3 wording inconsistency was corrected by the principal: the P2 row now names the actual incumbent B1 and the B2-versus-B1 comparison. The principal also aligned proposed primary horizons with the catalogue and retained the explicit final preregistration dependencies. No implementation or empirical acceptance is claimed.

All eight findings are resolved in the integrated specification. The original review and its source hashes remain above as provenance. Current integrated file hashes are:

| File | SHA256 |
|---|---|
| MASTER_PLAN.md | `029ae123259f5d27ae7a82ba96b913f7ec2344d06a411229779136a78b1692c1` |
| CONTRACTS.md | `e2a8ced5a769996a8b46a737db07d33ce6a9571b8838d763447d5c2e19514db5` |
| RESEARCH_PROTOCOL.md | `af5509c15a54b936a6995905723c44a7ae0cfeaba2e0072fbc001cdcc511cd05` |
| ROADMAP_AND_HANDOFF.md | `83ed4347dbeb182d49f3a8fa010066cc904c24c992c0dfe33f53d60af5982d3c` |
