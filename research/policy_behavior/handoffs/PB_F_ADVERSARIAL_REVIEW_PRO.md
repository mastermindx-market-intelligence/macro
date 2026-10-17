# PB-F — Pro Commission: Independent Adversarial Review of Policy-Behavior Research

**Operation key:** `PB-F-POLICY-BEHAVIOR-REDTEAM-20261007`  
**Recommended model/mode:** **Astra Pro**  
**Research-only:** yes  
**Launch gate:** PB-A, PB-B, PB-C, PB-D and PB-E have returned complete artifacts  
**Receiver mode:** `DIRECT_TARGETED` on Chris's live delivery into the intended session  
**Receiver binding:** `CAPACITY_SELECTABLE`

## Pro-mode receipt

```text
COGNITION_ROUTE: CHAT_INCLUDED_DEFAULT
CHAT_REASONING_MODE: PRO_MODE_EXCEPTION
WHY_PRO_MODE: The mission is to adversarially audit five substantial research programs for hidden selection bias, outcome leakage, causal overreach, weak source independence, political-intent overclaim and invalid statistical inference before architecture is derived from them.
WHY_NON_PRO_INSUFFICIENT: The reviewer must cross-compare independent source packets, reconstruct the strongest alternative explanations, detect subtle dependency among observations and decide which conclusions survive without becoming a second research author.
PRO_MODE_TASK_CLASS: ADVERSARIAL_JUDGMENT
EXPECTED_DURATION_MINUTES: 150
STOP_CONDITION: Stop when every material conclusion from PB-A through PB-E has a SURVIVES/WEAKEN/REJECT/NEEDS_MORE_DATA disposition, the strongest confounders and leakage risks are documented, and a bounded recommendation to PB-G is complete.
```

**ROUTE:** ChatGPT Astra Pro  
**WHY:** independent adversarial judgment is the entire mission.  
**WHY NOT FABLE:** this is a bounded review over frozen returned artifacts; the reviewer does not own program integration or implementation.

## Mission

Attack the combined PB-A..PB-E research before Mastermind turns any of it into architecture.

The reviewer is not asked to produce a more exciting theory. The reviewer is asked to identify where the apparent evidence is actually:

- selection bias;
- hindsight;
- source dependence;
- small-n noise;
- multiple testing;
- ordinary corporate calendars;
- domestic policy fundamentals;
- common-cause macro effects;
- survivorship;
- regime dependence;
- publication-clock leakage;
- market-outcome labeling disguised as event semantics;
- vague political-intent inference.

## Inputs

Do not begin until Chris provides the exact PB-A..PB-E return artifacts or their draft PRs / SHAs.

Also read:

- protected procedure at `Mastermind@9a24ef2c4b27ac95a4d1f72f5eae1073657cd7c2`;
- Macro PR #8560 source packet;
- the handoff and preregistration that governed each lane.

A research return is evidence, not accepted truth.

## Required review frame

For every material claim, classify:

- `SURVIVES` — evidence supports the claim at the stated strength;
- `WEAKEN` — direction may survive but scope/confidence must be reduced;
- `REJECT` — evidence does not support the claim;
- `NEEDS_MORE_DATA` — current evidence cannot decide.

For each disposition state:

- what the claim actually says;
- strongest supporting evidence;
- strongest counterargument;
- source / sample weakness;
- whether the conclusion was preregistered or post-hoc;
- whether the proposed causal mechanism is identified;
- what new evidence could change the disposition.

## PB-A review

Attack:

- M0/M1/M2 comparability;
- whether M1 is a fair automatic-inversion baseline;
- outcome leakage through “directional implication” coding;
- episode selection;
- correlated Fed/Treasury episodes;
- target multiplicity;
- whether M2 wins because it sees more information rather than better behavioral inference;
- whether institutional mandate explanations dominate strategic interpretations.

## PB-B review

Attack:

- conflation of U.S. pressure, operational cooperation and control;
- missing Japanese domestic-data counterfactuals;
- later reporting inserted into earlier decision cuts;
- rate-check versus intervention confusion;
- FIMA availability versus actual use;
- BOJ OIS / JGB moves that were already priced;
- cherry-picking U.S.-pressure episodes.

Explicitly test whether the strongest conclusion should be:
- coercive constraint;
- reinforcing pressure;
- joint stabilization;
- mostly domestic policy with U.S. commentary.

## PB-C review

Attack:

- winner selection;
- famous-company bias;
- event taxonomy drift;
- known earnings / conference / product calendars;
- event duplication;
- stress-window data mining;
- definition of “discretionary”;
- multiple-comparison inflation;
- cross-firm clustering driven by one common industry cycle;
- White House contact treated as coordination proof;
- absence of negative stress windows.

Require leave-famous-winners-out evidence.

## PB-D review

Attack:

- tiny n;
- repeated rows from the same issuer / date;
- INTC or another single-name dependence;
- same-date control construction;
- regime / era pooling;
- H5 chosen after seeing the data;
- event-quality labels influenced by returns;
- T2 definition selected because it worked;
- multiple interaction cells;
- whether the apparent signal is simply attention × existing momentum.

Require an explicit distinction between discovery and prospective evidence.

## PB-E review

Attack:

- double-counting deal headline values;
- confusing investment, commitments and revenue;
- false circularity from normal strategic partnerships;
- government strategic support interpreted as market support;
- missing external-cash data;
- incomplete entity / SPV graphs;
- fragile conclusions drawn from one disclosed contract;
- claims that financing dependence implies poor economics.

## Cross-program attacks

Look for:

1. the same famous events appearing in multiple lanes and being treated as independent evidence;
2. the same market outcome validating policy, announcement and technical hypotheses simultaneously;
3. same-date macro shocks causing apparent multi-engine convergence;
4. causal stories that cannot be distinguished but are written as if identified;
5. open/draft source PRs treated as canonical law;
6. point-in-time violations;
7. any result that quietly grants production authority.

## Deliverables

If GitHub write is verified, use a fresh branch from current `main` and write only under:

`research/policy_behavior/pro_returns/PB-F/`

Preferred files:

- `PB_F_CLAIM_DISPOSITIONS.md`
- `PB_F_CLAIM_MATRIX.json`
- `PB_F_CONFOUNDERS.md`
- `PB_F_REPLICATION_GAPS.md`
- `PB_F_INTEGRATOR_INSTRUCTIONS.md`

## Acceptance

A valid review:

- covers every material claim from all five returns;
- rejects at least one plausible claim if evidence warrants it;
- preserves strong evidence even when motive remains unidentified;
- distinguishes “not proven” from “false”;
- explicitly calls out any information leakage;
- identifies which result is most decision-relevant for Mastermind;
- identifies which attractive result should **not** influence product design yet;
- gives PB-G a compact disposition matrix.

## Non-goals

Do not:

- rebuild the studies;
- alter production;
- create a new theory to replace weak evidence;
- merge or accept PRs;
- interpret review severity as program authority;
- spend the session on stylistic feedback.

## Stop condition and return

Stop when the disposition matrix and integration instructions are complete.

Return:
- branch / PR if any;
- exact head SHA;
- number of claims reviewed;
- SURVIVES / WEAKEN / REJECT / NEEDS_MORE_DATA counts;
- five most important architecture consequences;
- exact items PB-G must not silently resurrect.
