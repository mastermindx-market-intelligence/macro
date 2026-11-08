# Research Factory — isolated code-candidate research masterplan

**Prepared 12 October 2026. Records-only assessment and Fable handoff. Not dispatched; RF-16 is not released.**

## 1. Mission and actual missing capability

Complete the existing deferred [Research Factory codegen seed](https://github.com/mastermindx-market-intelligence/macro/blob/fd330fd7132347c0382e6c5945bdb58fa635067d/research/RF_CODEGEN_LANE_FOR_FABLE.md): permit original model-authored research primitives to be admitted, executed in an isolated environment, judged by fixed existing evaluators and tracked through an honest research decision. Generated code must never control its evaluator, inspect future inputs or labels, understate its search history, publish itself or acquire capital authority.

This is **not a restart of the completed Factory**. The [original charter](https://github.com/mastermindx-market-intelligence/macro/blob/fd330fd7132347c0382e6c5945bdb58fa635067d/research/RESEARCH_FACTORY_MASTERPLAN_BY_FABLE.md) records W0–W7 completion. [Signal Foundry](https://github.com/mastermindx-market-intelligence/macro/blob/fd330fd7132347c0382e6c5945bdb58fa635067d/research/SIGNAL_FOUNDRY_MASTERPLAN_BY_FABLE.md) already has a declarative-spec research loop. The new capability is the explicitly deferred, separately governed code-candidate extension—not another generator, evaluator, research ledger, queue or control plane.

The Chairman requested the next hardest eligible existing project and a masterplan. This is a bounded engineering judgment among recovered candidates, not an exhaustive numerical company ranking. The extension combines security, causal data access, numerical evaluation, adaptive-selection control and actual operator delivery. Intelligence Workspace and Native Apps are substantial alternatives, but their historical documents do not establish current whole-program state and they do not address this missing execution boundary.

## 2. Source and artifact identities

Primary source cut: **macro@fd330fd7132347c0382e6c5945bdb58fa635067d**. Compatible protected procedure: **Mastermind@25c4b7923734392b1013afae179966985819d847**, Skillpack1.0.1/bootstrap1. Terminal shortlist-only reference: **c799ba7e64e2d0861228c9977cc12ed4a5d91982**.

The expanded conversation package, `Mastermind_Research_Factory_Codegen_Fable_Masterplan_2026-10-12.zip`, contains a 4,456-word main plan, **28 capability assessments, 31 detailed work packages, 131 planned acceptance assertions and 29 sources**, plus delegation templates, risks, passive DAG and document validator. Those annexes are conversation artifacts, not claimed to be installed repository source.

Exact expanded artifact hashes:
- `01_MASTERPLAN.md`: SHA256 `cdf1ca04f5dbd55b498edb85e851d7c50dbbf918f57443e573dd24d9c73bc15b`.
- `work_packages.json`: SHA256 `32d42bea4638051f6efdc027cedd731a1c2dabb4fec8ead05c783eb130d48014`.
- `sources.json`: SHA256 `532ca254ac382ff2847cfff70232dfa9b03ca9471518556d5e74ef9ee0e1ea20`.
- `03_WORK_PACKAGES.md`: SHA256 `d7a30d79149db34db26c3a5b011183755216460c1bd6e733e83e350975d4f7d2`.
- `04_ACCEPTANCE_MATRIX.md`: SHA256 `e32dd84e025eda3531477239c3425216008440a6e345d175b5675247cf39c826`.

Local document-integrity checks passed task/source/reference closure, acyclic dependencies, all-required-tasks-to-closeout, generation prerequisites, assertion crosswalk and passive scope. Eight deep-copy mutations were rejected: cycle, unknown source, duplicate assertion, removed RF-16 gate, false execution authority, removed exclusion, mutable pin and missing isolation dependency. **No Mastermind product test, candidate generation, sandbox test, market-data/holdout read or scientific evaluation was run by this assessment.**

This document is a standalone durable execution entrypoint. It does not amend old charter/source files, assign a worker, claim an active Fable session, or grant protected-source/administrative permissions.

## 3. Scope and exclusions

Initial research scope: bounded feature primitives unavailable in the current declarative vocabulary, using existing lawful price-based data and a fixed existing drawdown/MAE entry-ordering or reversion research objective. A primitive that the existing DSL already expresses should use that path instead. No automatic return-alpha search, brokerage execution, allocation, liquidation, board rank, alert priority or scored-path promotion.

Exclude development of **Adaptive Signal Clock, Catalyst Intelligence, Research Vault, Financial Intelligence Fabric/Fundamental Forensics (FIF), Single-Name Intelligence, Grey Deer Risk, Market OS, Options Intelligence, Prophet, Market Ontology, Native Chart Engine, Mastermind OS, Executive OS, Subagent Fabric and GMI**. Existing narrow read-only interfaces do not transfer their ownership. Infrastructure work is limited to this named research consumer and must reuse approved existing runtime/record/authentication/release owners.

## 4. What the census actually found

| Capability | Source evidence at the pinned cut | Required disposition |
|---|---|---|
| Base Factory | Charter records W0–W7 complete; Factory routes/evidences existing evaluators | Reuse; historical completion is not a new live certification |
| Code candidate | [schema.py](https://github.com/mastermindx-market-intelligence/macro/blob/fd330fd7132347c0382e6c5945bdb58fa635067d/engine/research_factory/schema.py), blob `eaaee50b65cb163b809c569dfc0425642043e67e`, excludes code_candidate | Reviewed versioned extension; do not hide code as external_idea |
| Actor/lifecycle | [state.py](https://github.com/mastermindx-market-intelligence/macro/blob/fd330fd7132347c0382e6c5945bdb58fa635067d/engine/research_factory/state.py), blob `3c45e61538d044de46b9279a7ee6d09b7b3063ee`, has fifteen states and qualified Opus adjudication | Preserve current packet/actor requirements, not just old prose or a model-name string |
| Trial Ledger | [trial_ledger.py](https://github.com/mastermindx-market-intelligence/macro/blob/fd330fd7132347c0382e6c5945bdb58fa635067d/engine/trial_ledger.py), blob `994c616afd46157e9c887542405f541a37e4e9fa`, records configs with flush/fsync; loader records error/corruption and may load empty/partial | New lane refuses unqualified accounting; do not create another ledger or rewrite all legacy callers |
| Holdout Vault | [holdout_vault.py](https://github.com/mastermindx-market-intelligence/macro/blob/fd330fd7132347c0382e6c5945bdb58fa635067d/engine/holdout_vault.py), blob `20bf2eb98d58f50d65e3963687a1e91305a7fadb`, logs peek with a supplied result | Existing owner must mediate actual dataset access; post-result metadata is insufficient |
| Scientific helper | [promotion_gate.py](https://github.com/mastermindx-market-intelligence/macro/blob/fd330fd7132347c0382e6c5945bdb58fa635067d/engine/promotion_gate.py), blob `8a9bd19549985ebfbbb4e42b8590a2794dd9175e`, evaluates supplied inputs | Require the complete frozen proof set before a whole-lane verdict |
| DSR interface | [validation.py](https://github.com/mastermindx-market-intelligence/macro/blob/fd330fd7132347c0382e6c5945bdb58fa635067d/engine/validation.py), blob `c5eba06e3c2bbe3e63ed602f562e0b60b97ff35b`, retains legacy n_trials and ducktyped ledger | Use actual authoritative persistent ledger; no temporary or candidate-authored effective_n |
| Existing count ratchet | [test_no_literal_ntrials.py](https://github.com/mastermindx-market-intelligence/macro/blob/fd330fd7132347c0382e6c5945bdb58fa635067d/tests/test_no_literal_ntrials.py) | Preserve; no new literal-count caller |
| Domain adapter | [adapter_oracle.py](https://github.com/mastermindx-market-intelligence/macro/blob/fd330fd7132347c0382e6c5945bdb58fa635067d/engine/research_factory/adapter_oracle.py), blob `9ed2c241392d16e491b3611bd82c13f9157fdae2`, distinguishes counted63d and read-only reversion tracks | Do not collapse their rulers or duplicate registry status |
| Mechanical probes | [probes.py](https://github.com/mastermindx-market-intelligence/macro/blob/fd330fd7132347c0382e6c5945bdb58fa635067d/engine/research_factory/probes.py), blob `be9df4225ae2b395b4ac6cc4f5e3edec1d4e0d3a`, is deterministic/flag-only | Reuse with appropriate independent control cases |
| Effective protections | Ruleset read returned rule21813020 in evaluate mode; traditional branch-protection read returned403 Resource not accessible by integration | **UNKNOWN**, not absent; no alternate-carrier retry. Obtain legitimate owner evidence before the gated effect |
| Actual isolated runtime | Not inspected/executed by this assessment | No installation, containment or current capacity claim |

Selected source ranges and a bounded keyword PR search were inspected, not all unpublished work or live leases. Some old source comments are historical. The shared helpers' tolerant/modular behaviour is not itself proof of a production exploit or universal defect; this extension needs a stricter composition. A failed container-side public-raw DNS fetch supplied no local clone or test evidence.

## 5. RF-16 and the trust boundary

**RF-16 continues to prohibit arbitrary generated code in the base Factory.** A00 defines the proposed separately governed extension and binds the exact permitted morphology, source cohort, evaluator, primary objective, feedback, budget and required evidence. Candidate generation and execution remain disabled until actual OS/identity separation and reserved protections are independently accepted. An in-process allowlist, worktree, prompt instruction or policy file alone is not that boundary.

Normal source engineering to establish prerequisites can proceed under an actual assignment and its existing controls. Administrative/credential changes, reserved evaluator edits, human-only acts and spend expansion retain their genuine gates. Missing optional metadata is not a veto on unrelated lawful work; a required unverified protection blocks its dependent effect.

Separate four responsibilities without creating four new services:

| Responsibility | Allowed | Denied |
|---|---|---|
| Generation | Approved development specification/input schema; inert original feature source | Sealed labels, privileged credentials, canonical writes, evaluator manipulation |
| Candidate execution | Exact source/runtime, per-decision available input, bounded state/scratch, data-only output | Network, host files/processes, adjacent job data, runtime socket, future inputs/labels, ledger writes |
| Trusted evaluation | Validated features, fixed evaluator and authorized labels | Import candidate code or trust candidate-authored statistics/gates |
| Records/adjudication/publication | Existing verified records, genuine actor/packet authority and current release controls | Auto-promote, erase failures, reset trials/peeks, publish untrusted code |

A truly read-only execution identity does not also gain publication power. Trusted source acquisition and PR/record publication use their existing separate owners; those credentials never enter candidate execution.

Prefer an already-qualified isolation service. Otherwise propose a disposable Linux gVisor environment under the current owner; use a microVM only when actual compatibility/threat evidence warrants it. Do not build a universal sandbox platform. [GitHub secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use) and [gVisor's security model](https://gvisor.dev/docs/architecture_guide/security/) inform, but do not prove, the actual deployment. Effective egress, CPU/memory/process/disk/wall limits and teardown must be tested independently. Residual kernel/hardware/side-channel risks stay disclosed.

Use harmless sentinels in approved isolated tests. A denied-operation test must be paired with successful permitted computation. Obtain **S02 independent exact-boundary acceptance before C02**. Q01 later tests the full composition and is not a substitute for initial boundary acceptance.

## 6. Interface and source map

Proposed locations, not implemented files:
- `engine/research_codegen/{contracts,admission,input_contract,prefix_driver,static_checks,output_contract,transport}.py`: closed, bounded adapters, not new lifecycle or evaluation owners.
- `engine/research_factory/adapter_codegen.py`: versioned bridge into the original Factory and fixed domain evaluator.
- `scripts/research_codegen_sandbox.py`: finite adapter to the existing admitted runtime, never a daemon/scheduler.
- `data/research_factory/code_candidates/`: inert source/manifests through the incumbent record owner, never imported by ordinary application/nightly code.
- `tests/test_research_codegen_*.py`: actual collected contract, temporal, containment, integration and acceptance suites.

Conceptual candidate interface: `on_observation(available_input, bounded_state) -> feature_value + availability + bounded_state`. The trusted driver assigns decisions and validates output. The candidate cannot supply paths, credentials, tool selectors, timestamps, p-values, metrics or authority. Pin code/configuration, lineage, runtime/dependencies, input policy, evaluator, family and protocol. Hashes prove identity, not trusted origin by themselves.

All trusted/untrusted transfers use closed bounded data. No executable deserialization, output-driven shell commands, arbitrary object hooks or generated config imports. Unsupported/nonfinite/oversized/incoherent output is an explicit refusal, not a dropped inconvenient observation.

## 7. Causal data access

A dataset clipped at final cutoff T still exposes t+1 through T at an earlier historical decision t. The runtime must supply only information whose qualified availability is no later than each decision, not an accessible full panel. Labels remain outside the candidate process. Earlier permitted state is allowed; later folds, sibling candidates and previous runs cannot contaminate it.

Prove future-suffix invariance: alter every future observation/revision while holding the information at t constant, then require the same feature at t through the real integrated boundary. Check metadata/schedule-length leaks too. A static `.shift(-1)` linter is a preliminary filter, not the security or causal proof.

Keep event time, availability, receipt, revision, decision cutoff and label maturity separate. Existing source owners retain symbol/calendar/corporate-action semantics. Do not restamp unknown vintages or recompute old issued features with future revisions. Warmup, refusal and missingness stay in the denominator.

A model can know historical outcomes from prior training. Isolation cannot erase that knowledge. Historical reconstructed studies and genuine prospective evidence are separate claims, even with anonymized prompts. Prospective data starts after actual frozen registration and labels mature before scoring.

## 8. Accounting, holdout and scientific protocol

Use the **existing** Trial Ledger and Vault. Count every explicit generated variant and tested refinement before it can affect a conclusion, including rejected/failed/abandoned work. Preserve exact replay versus new scientific choice. Do not store hidden reasoning. Child names, prompt changes, fresh chats or family renames do not reset the search budget. Preserve RF-15's two-refinement-cycle limit and original re-arm gates.

L01 requires complete authoritative history, qualified diagnostics, family identity, declared allowance and durable readback. A temporary declared count or candidate-supplied effective_n object is not enough. Local thread locks do not establish cross-process serialization; retain one admitted writer through its existing owner.

L02 mediates actual label access. The trusted owner durably records consumed authorization before releasing permitted labels to the evaluator. Generator and candidate never read those labels directly. Verify complete original history against trusted origin/anchor; a recomputed hash chain alone cannot authenticate replacement history. Crashes/lost responses preserve consumed peeks and original identities before any replay.

E01 binds one existing numerical ruler. Its required input/evidence set is frozen before outcomes; omitted mandatory checks refuse full eligibility. Candidate outputs are features, not candidate-authored performance. Shared scientific code is never edited inside the candidate loop. Any necessary trusted input adapter receives normal independent source review.

Primary pilot objective is an appropriate loss on drawdown/MAE entry ordering, not a promised return-alpha result. Compare the same eligible cohort, label cutoffs and selection/opportunity/exposure budget. An all-cash or zero-coverage candidate cannot win merely by avoiding all adverse observations. Retain foregone opportunities, costs/turnover assumptions and failures.

Freeze effect size, independent sample/power, paired date/episode-aware uncertainty, multiplicity, feedback and stopping rules. Purge actual information/label overlap rather than trusting the name of a generic function. Use DSR only for an appropriate selected return-series diagnostic; it is not the primary test for every non-return loss. PBO/CV do not cure source leakage, wrong labels or unlimited adaptive feedback. Relevant primary research: [adaptive holdout reuse](https://arxiv.org/abs/1506.02629), [Deflated Sharpe Ratio](https://doi.org/10.2139/ssrn.2460551), [Probability of Backtest Overfitting](https://escholarship.org/uc/item/4w1110bb).

Initial planning bound: at most four explicit variants across at most two mechanisms, subordinate to tighter existing limits and an actual approved budget. Choose mechanisms because the current DSL cannot express the useful primitive, not because a large fleet needs work. An honest null batch is complete research, not permission to try more variants until something wins. No profitable-strategy quota.

## 9. Work breakdown and dependencies

These IDs are passive planning labels, not runtime identities. Exact current source allowlists, accepted inputs, evidence classes and original carriers are required before effects. The expanded annex gives every package's steps and assertions.

| Task | Lead | Dependencies | Required result |
|---|---|---|---|
| G00 | Fable | — | Recover source/writer/effects and legitimate protection evidence; no ghost-owner dependency |
| G01 | Fable | G00 | Useful native Opus→Fabric operator→same Opus retained-result consumption proof |
| A00 | Fable | G00 | RF-16 extension/pilot contract and actual reserved gates; no implicit release |
| S01 | O1 | A00 | Separate acquisition/execution/evaluation/publication identities and effective permissions |
| S02 | O1 | S01 | Independently accepted actual isolation with successful allowed and denied canaries |
| S03 | O1 | S02 | External resource limits, bounded outputs and whole-process-subtree cleanup |
| S04 | O1 | S03 | Trusted source/input/runtime/output binding and no forged result authority |
| T01 | O2 | A00 | Qualified source/time/cohort contract from existing lawful inputs |
| T02 | O2 | T01,S04 | Actual per-decision prefix-only stream and suffix-invariance proof |
| T03 | O2 | T02 | Correct missingness, warmup, corrections and generation fencing |
| L01 | O5 | A00,S01 | Strict use of existing Trial Ledger, full generation accounting and durable original writer |
| L02 | O5 | L01,S04,T01 | Existing Vault's real trusted label mediation and non-resettable access history |
| C01 | O3 | A00,L01 | Reviewed versioned candidate schema/adapter; no disguised type or duplicate lifecycle |
| C02 | O3 | C01,T01,S04,L01,G01 | Original bounded primitives only after accepted boundary; complete generation provenance |
| C03 | O3 | C02,S03 | Bounded compilation/lint within qualified environment; no allowlist-as-sandbox claim |
| C04 | O3 | C03,T03,S04 | Closed validated feature data before the trusted evaluator |
| E01 | O4 | C04,L02 | One fixed existing evaluator with mandatory complete proof set |
| E02 | O4 | E01 | Matched opportunity/risk/loss comparison and visible refusal/cost denominators |
| E03 | O5 | E02,L01,L02 | Frozen statistical design, feedback, multiplicity and prospective interpretation |
| E04 | O6 | E01,E03 | Independent numerical and temporal oracles, not only implementation self-tests |
| Q01 | O6 | S04,T03,L02,C04 | Full composed actual containment/tamper suite; pre-generation S02 remains separately required |
| Q02 | O6 | E03,E04 | Measured leakage/bias-detection cases; no numeric reviewer confidence |
| Q03 | O6 | S03,E04 | Actual total compute/budget/overload proof without hidden dropped work |
| U01 | O7 | E03,Q02 | Existing challenge/adjudication packets, genuine actor/packet checks |
| U02 | O7 | U01 | Actual authenticated admin/Experiments investigation including losing candidates |
| P01 | O4/O6 | G01,E04,Q01,Q02,Q03,U02 | Real synthetic end-to-end positive primitive and deliberate failure control |
| P02 | O4 | P01,E03 | Frozen bounded historical research batch; all results retained |
| P03 | O4 | P02,U01 | Actual prospective shadow evidence through original forward owner; real data horizon gate |
| R01 | O7 | P01,Q01,Q03 | Canonical source release, installed/selected/actually executing path separately proven |
| R02 | O7 | R01,P01 | Recovery/rollback retaining history and spent budgets; independent of future accrual |
| CLOSE | Fable | P02,P03,R02 | Honest engineering and scientific acceptance plus unfinished obligations |

Start only ready contract/security, data/method and independent baseline responsibilities. Shared files get one integrating writer. No all-workers-finished barrier. R02 does not wait for statistical accrual; a blocked future-evidence lane cannot prevent safe rollback qualification.

## 10. First vertical and acceptance

First demonstrate: **permitted synthetic primitive → durable generation record → exact isolated prefix execution → trusted numerical output → advisory challenge → proper adjudication → visible operator evidence**. A deliberately leaky control must be rejected or exposed by its declared temporal test, and both attempts must remain accounted. This is real machinery proof, not alpha.

Then run the frozen historical batch. Prospective shadow follows only through existing adjudication and the original nightly/experiment owner. A second unchanged cycle tests idempotence. Longer evidence horizons remain actual obligations; no backfilled prospective dates, clock reset or invented background owner.

Five proof layers remain separate: contracts; actual containment; independent numerical/causal semantics; research-selection integrity; authenticated product journey. A model-authored review does not replace an independent numerical oracle. Source tests do not prove physical controls. All skipped, missing and failed cases remain visible.

Expected isolated controls include missing ledger history, untrusted ledger object, missing mandatory gate input, future suffix/full-window normalizer, output forgery/nonfinite payload, unauthorized host/network/label access, lost-response/replay accounting and omitted cleanup. No real secret or production attack is used. Do not weaken assertions or widen permissions to force a pass.

## 11. Fable/native Opus/Fabric organisation

**Fable → native Opus suborchestrators → existing Subagent Fabric task operators → optional bounded Fabric workers.** Operators may self-execute when framing/review costs exceed the benefit of delegation. Native Opus agents own domain judgment, not routine bulk coding by default. Fable owns cross-domain choices, reserved decision routing, root spend and final acceptance.

O1 identity/isolation/resources; O2 data/time/corrections; O3 candidates/contracts/outputs; O4 evaluator/historical/forward research; O5 accounting/Vault/statistics; O6 independent security/numerics/bias/cost proof; O7 review/admin/release/recovery. Seven responsibilities are not seven compulsory concurrent launches.

G01's read-only route proof asks an actual native Opus to have a Fabric operator inspect the supplied-input behaviour of the existing promotion helper and return a discriminating fixture proposal. Observe actual tools/model, START, retained return and same-parent consumption. [Native-subagent documentation](https://code.claude.com/docs/en/sub-agents) does not prove current harness/MCP configuration or nesting. Do not multiply limits through coordinators or claim unavailable/unknown pools are all down.

Each return contains original root/task/carrier; exact source/data/runtime/evaluator identities; changed paths; actual checks and failure controls; independent review; limitations; confirmed/unknown effects; active children; observed usage; and the exact next useful action. Opus adjudicates consolidated evidence; Fable consumes domain deltas. Raw logs stay with existing owners. No full-transcript fan-out, duplicate queue, daemon or memory store.

## 12. Release, recovery and completion

Current assignment permits ordinary in-scope engineering without repeated permission. Genuine administrative/human-only/rights/validator gates remain. Preserve active source writers, held branches, prior denials and unknown effects. A historical author or archived chat is not a live exclusive owner; observation failure is not proof a lease expired. Recover through existing fencing/owner procedures.

Follow actual source CI, independent review and canonical release. Installation, selected configuration, accepted activation and executing path are different receipts. This plan enables no workflow, changes no settings and starts no background work. Keep automatic candidate generation dark until its exact owner admits it. Do not arm Signal Foundry or add a parallel forward scheduler.

Rollback disables new code-candidate admissions and removes only owned integration. Keep Factory/Foundry state, failed trials, peeks, prospective history and original workspaces. Interrupted effects are reconciled on their original targets before replay; a denied action is never rerouted through another tool/account/model.

Engineering acceptance proves the declared safe research capability end to end. Scientific acceptance states each predeclared candidate's result and uncertainty. A valid null can finish an experiment; a positive historical result cannot impersonate prospective confirmation. No scored-path, trading or sizing permission follows from either.

Execute → verify → persist compact delta in existing owners → start the next safe ready dependency. Checkpoints, passing tests and open PRs are saves, not automatic stops. End for the proven requested outcome or a real gate after useful independent work is exhausted; preserve actual future observations and original returns. Do not hide required unrun work as optional future improvements.

**Fable: finish the missing isolated research capability, not the completed base Factory. Expand what can be evaluated without allowing generated code to control the judgment machinery.**
