# PB-B — Pro Commission: U.S.–Japan Constraint and Policy-Leverage Study

**Operation key:** `PB-B-US-JAPAN-CONSTRAINT-20261007`  
**Recommended model/mode:** **Astra Pro**  
**Research-only:** yes  
**Receiver mode:** `DIRECT_TARGETED` on Chris's live delivery into the intended session  
**Receiver binding:** `CAPACITY_SELECTABLE`

## Pro-mode receipt

```text
COGNITION_ROUTE: CHAT_INCLUDED_DEFAULT
CHAT_REASONING_MODE: PRO_MODE_EXCEPTION
WHY_PRO_MODE: This mission requires reconstructing a cross-country policy chronology from primary and wire sources, distinguishing public pressure from operational cooperation, measuring contemporaneous market expectations, and adjudicating multiple plausible causal explanations.
WHY_NON_PRO_INSUFFICIENT: The central difficulty is causal identification under incomplete public evidence, not document collection; the session must sustain adversarial reasoning across monetary policy, FX intervention, liquidity backstops and domestic Japanese macro conditions.
PRO_MODE_TASK_CLASS: LONG_HORIZON_FRONTIER_REASONING
EXPECTED_DURATION_MINUTES: 180
STOP_CONDITION: Stop when the U.S.–Japan chronology is PIT-certified, 10–15 casebook rows are complete, the domestic-only counterfactual is tested, and the strongest supported constraint inference plus its falsifiers are documented.
```

**ROUTE:** ChatGPT Astra Pro  
**WHY:** the task is a concentrated political-economy / markets identification problem.  
**WHY NOT FABLE:** the research boundary is frozen and no architecture or source-custody decision requires a principal operator.

## Mission

Determine how much U.S. Treasury / Fed / White House pressure and operational cooperation changed the **feasible Japanese monetary and FX policy set**, without requiring documentary proof of command-and-control and without overclaiming causality.

The target is a disciplined answer to:

> Did unexpected U.S. involvement materially change the probability, timing or instrument mix of Japanese policy beyond what Japanese domestic inflation, wages, growth and market conditions already implied?

## Frozen sources to read first

- Protected procedure: `mastermindx-market-intelligence/Mastermind@9a24ef2c4b27ac95a4d1f72f5eae1073657cd7c2`
- Macro PR #8560 source head: `ee86db2c832c73a36837c1240df871700340d6da`
- Read the policy-behavior masterplan, casebook preregistration and seed.
- The seed includes candidate sources only. Re-fetch / verify every material fact from primary or high-quality independent sources.

## Required chronology

Reconstruct the relevant sequence beginning before the public 2025 U.S. pressure cycle and extending through the 2026 tightening / intervention period.

At minimum investigate:

- Japanese inflation, wages, activity and BOJ communications before U.S. involvement;
- Treasury / Bessent statements and direct meetings;
- Ueda / BOJ responses;
- New York Fed yen rate checks and what they operationally mean;
- any confirmed U.S.–Japan FX intervention;
- instrument-choice pressure;
- FIMA repo / dollar-liquidity / Treasury-market considerations;
- subsequent BOJ decisions;
- contemporaneous OIS / JGB / USDJPY expectations around each event.

Do not assume the seed chronology is complete or perfectly dated.

## Core hypotheses

Evaluate at least these competing explanations:

**H1 — MATERIAL_EXTERNAL_CONSTRAINT**  
U.S. actions narrowed Japan's feasible policy choices or changed timing/instrument selection.

**H2 — DOMESTIC_FUNDAMENTALS_DOMINATED**  
Japanese inflation/wages/growth already implied the observed BOJ path; U.S. pressure mainly narrated or reinforced it.

**H3 — JOINT_MARKET_STABILIZATION**  
Operational cooperation was primarily about disorderly FX / market functioning rather than changing BOJ's underlying monetary reaction function.

**H4 — JAPAN_SOLICITED_COOPERATION**  
Japan itself sought U.S. operational support, so evidence of cooperation is weaker evidence of U.S. coercion.

**H5 — EXPECTATIONS_ALREADY_PRICED**  
The observed policy decisions were substantially priced before U.S. involvement, reducing evidence that U.S. pressure changed the path.

Add stronger alternatives if the evidence requires them.

## Required evidence structure

For every episode:

- decision / observation cut;
- source and first-public time;
- domestic macro backdrop;
- BOJ / Japan MOF stated preference;
- pre-event BOJ OIS / JGB / USDJPY expectation;
- U.S. action or statement;
- operational versus rhetorical nature;
- immediate market repricing;
- subsequent Japanese action;
- plausible alternatives;
- what was not publicly knowable;
- competing-hypothesis update;
- falsifier.

Produce **10–15 casebook rows** compatible with the PR #8560 schema.

## Causal / identification method

Do not use a single before/after story.

Use the strongest feasible combination of:

- event windows around genuinely unexpected U.S. interventions;
- domestic-data controls;
- previously scheduled BOJ decisions as controls;
- pre-event market pricing;
- comparable Japan episodes without material U.S. involvement;
- instrument-specific reactions;
- source-clock discipline;
- negative cases where U.S. pressure did not lead to the implied Japanese action.

If a clean causal estimate is impossible, say so and provide bounded inference instead of inventing precision.

## Required market outputs

Where lawful data are available, examine:

- USDJPY;
- JPY trade-weighted measures if useful;
- 2y / 10y JGB;
- BOJ OIS / policy-expectation proxies;
- UST spillovers;
- Japanese bank / exporter / importer reactions only as secondary context.

Separate immediate expectation repricing from the eventual policy decision.

## Critical interpretation rules

- “The U.S. influenced Japan” is not equivalent to “the U.S. controls the BOJ.”
- A rate check is not intervention.
- FIMA availability is not proof of facility use.
- A joint intervention is not by itself evidence that BOJ tightening was externally commanded.
- Domestic Japanese inflation / wages are a required counterfactual, not an afterthought.
- Later reporting of private pressure cannot be injected into earlier decision-time features unless it establishes the fact was already known then.

## Deliverables

If GitHub write is verified, use a fresh branch from current `main` and write only under:

`research/policy_behavior/pro_returns/PB-B/`

Preferred files:

- `PB_B_US_JAPAN_TIMELINE.md`
- `PB_B_CASEBOOK.json`
- `PB_B_CONSTRAINT_ASSESSMENT.md`
- `PB_B_EVENT_WINDOWS.json`
- `PB_B_SOURCE_LEDGER.md`
- optional research scripts / notebooks if they are reproducible

## Acceptance

A valid return includes:

- 10–15 PIT-certified episodes;
- primary-source chronology for BOJ / Fed / Treasury / MOF actions where possible;
- domestic-data counterfactual;
- market-expectation evidence;
- at least one meaningful negative / null case;
- explicit separation of pressure, cooperation and command;
- confidence by claim;
- a ranked assessment of H1–H5;
- the single observation that would most strongly change the current conclusion.

## Non-goals

Do not:

- build a Japan policy engine;
- modify international dashboards;
- change RIC;
- assign policy authority to an LLM;
- call private motive proven without evidence;
- merge results into production;
- duplicate existing country / qbus / rates stores.

## Stop condition and return

Stop when the bounded Japan study and compatible casebook rows are complete.

Return:
- branch / PR if any;
- exact head SHA;
- source ledger;
- case count;
- strongest evidence for external constraint;
- strongest evidence against it;
- what PB-G should preserve, weaken or reject.
