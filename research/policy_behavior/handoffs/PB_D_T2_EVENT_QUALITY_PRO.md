# PB-D — Pro Commission: T2 × Event-Quality Interaction Study

**Operation key:** `PB-D-T2-EVENT-QUALITY-20261007`  
**Recommended model/mode:** **Astra Pro**  
**Research-only:** yes  
**Receiver mode:** `DIRECT_TARGETED` on Chris's live delivery into the intended session  
**Receiver binding:** `CAPACITY_SELECTABLE`

## Pro-mode receipt

```text
COGNITION_ROUTE: CHAT_INCLUDED_DEFAULT
CHAT_REASONING_MODE: PRO_MODE_EXCEPTION
WHY_PRO_MODE: This mission requires reproducing a small-sample technical/news interaction, auditing post-selection and dependence, reconciling event semantics across Prophet and Company Intelligence, and designing a prospective evaluation that can distinguish attention from economic rerating.
WHY_NON_PRO_INSUFFICIENT: The key work is adversarial scientific judgment over tiny-n interaction effects, control construction, horizon dependence, duplicated issuer observations and information-quality labeling, not a routine backtest.
PRO_MODE_TASK_CLASS: ADVERSARIAL_JUDGMENT
EXPECTED_DURATION_MINUTES: 180
STOP_CONDITION: Stop when the current T2/news findings are independently reproduced or falsified, their selection/dependence risks are quantified, exact event-quality cells are frozen, and a prospective zero-authority preregistration plus reproduction packet is complete.
```

**ROUTE:** ChatGPT Astra Pro  
**WHY:** this is a concentrated research / data-science adjudication problem with high overfit risk.  
**WHY NOT FABLE:** the technical and event owners already exist and the study is bounded; no principal architecture reset is required.

## Mission

Determine what the current T2 × news / evidence discovery actually means and freeze the strongest defensible prospective test.

The working thesis is not “positive news + T2 works.”

The current evidence suggests a narrower interaction:

> a fresh technical acceptance event may become materially stronger when it coincides with genuinely independent new evidence or information arrival.

You must test whether that survives stricter event-quality and dependence controls.

## Frozen sources to read first

- Protected procedure: `mastermindx-market-intelligence/Mastermind@9a24ef2c4b27ac95a4d1f72f5eae1073657cd7c2`
- Policy-behavior packet: Macro PR #8560 @ `ee86db2c832c73a36837c1240df871700340d6da`
- Prophet PR #8495 @ `770918cb266b5d884978e31d61670b4efd789eaf`
- News-to-Business-Impact PR #8533 @ `cde0219b1040c66cbc8647f86352a25794488528`

Do not modify those PRs.

## Findings that must be independently reproduced

From PR #8495, verify or falsify:

- H5 T2 + news-burst: **10/11 positive versus SPY**;
- H5 T2 + news-burst absolute-positive: **8/11**;
- first observation per issuer: **6/7 positive versus SPY**, **4/7 absolute**;
- NVDA news-burst: six recent items, 0 positive, 0 negative;
- stronger post-hoc candidate:
  - fresh T2 × >=2 independent evidence legs;
  - repeated rows: **10/12 H5 positive vs SPY**;
  - first T2 per ticker: **5/5 positive vs SPY and sector**, **4/5 absolute**;
  - same-date controls worse on all seven observed dates;
  - average mean-excess gap ~**+4.19 percentage points**;
- H10 weakens materially and is sensitive to INTC;
- T1 + multi-leg and generic convergence do not reproduce the apparent edge.

Do not simply quote the PR. Reproduce from source artifacts / scripts where possible.

## Research questions

1. Is `news_burst` mostly an attention / information-arrival variable rather than a sentiment variable?
2. Does event **economic quality** improve the interaction beyond raw attention?
3. Does source independence matter?
4. Does the effect survive issuer deduplication?
5. Does it survive same-date, sector and technical-state controls?
6. Is H5 special while H10/H21 decay?
7. Is the effect driven by one or two names?
8. Is T2 mechanistically the right technical state, or would other fresh-acceptance definitions explain the same episodes?
9. Does the interaction predict cleaner lift-off / MFE / MAE, not merely positive close-to-close returns?
10. What sample size / prospective evidence is required before any promotion question is sensible?

## Event-quality taxonomy

Use PR #8533 semantics. At minimum distinguish:

- `ATTENTION_ONLY` — reporting breadth / burst without a verified economic delta;
- `VERIFIED_MATERIAL_EVENT` — source-backed material company event;
- `EXPECTATION_CHANGE` — valid expectation/guidance/revision delta;
- `STRATEGIC_OPTION` — credible new funded option but near-term earnings still unquantified;
- `GOVERNMENT_LINKED`;
- `FINANCING_LINKED`;
- `INDEPENDENT_EVIDENCE_2PLUS`;
- `SYNDICATED_SINGLE_ROOT`;
- `NO_MATERIAL_EVENT`.

One event can carry multiple orthogonal tags, but do not double-count correlated reports as independent evidence.

## Prospective cells

Freeze at least:

1. T2 alone;
2. T2 + raw attention burst;
3. T2 + verified material event;
4. T2 + >=2 independent evidence legs;
5. T2 + expectation / earnings revision;
6. T2 + strategic-option event;
7. T2 + government-linked event;
8. T2 + financing-linked event;
9. T2 + syndicated-single-root burst.

Do not create twenty micro-cells if the sample cannot support them. Predefine aggregation rules.

## Outcomes

At minimum:

- H1 / H5 / H10 / H21 absolute return;
- SPY-relative return;
- sector-relative return;
- MFE;
- MAE;
- clean-liftoff / failed-breakout definition;
- persistence conditional on H5 response;
- reversal / drawdown.

Use the same execution-delay convention across compared cells.

## Controls / sensitivity

Required:

- first-T2-per-ticker;
- same-date T2 controls;
- sector controls;
- leave-one-issuer-out;
- leave-INTC-out;
- repeated-row dependence treatment;
- event-root deduplication;
- calendar-time / era controls;
- July / regime-comparability audit rather than blind pooling;
- T1 comparison;
- no-news T2 comparison.

Where possible, use confidence intervals / exact binomial or bootstrap methods appropriate to tiny n. Avoid false precision.

## Prospective preregistration

Produce a frozen zero-authority prospective test that states:

- eligible population;
- exact T2 definition;
- event-quality labels;
- observation clock;
- source-independence rules;
- entry delay;
- outcomes / horizons;
- n-floor;
- decision rule;
- missing / stale behavior;
- correction behavior;
- no-go conditions for promotion.

The prereg must not be rewritten after future outcomes mature except through a logged amendment before the affected observations.

## Deliverables

If GitHub write is verified, use a fresh branch from current `main` and write only under:

`research/policy_behavior/pro_returns/PB-D/`

Preferred files:

- `PB_D_REPRODUCTION.md`
- `PB_D_REPRODUCTION_RESULTS.json`
- `PB_D_EVENT_QUALITY_LABEL_SPEC.md`
- `PB_D_PROSPECTIVE_PREREG.md`
- `PB_D_POWER_AND_LIMITATIONS.md`
- reproducible scripts

## Acceptance

A valid return must:

- reproduce or explicitly falsify each numeric claim above;
- disclose any population mismatch;
- separate article burst from independent evidence;
- quantify dependence / tiny-n uncertainty;
- identify the strongest surviving cell;
- identify the strongest apparent false lead;
- freeze a prospective test;
- grant zero live signal authority.

## Non-goals

Do not:

- modify Prophet;
- alter T2 logic;
- change the board population;
- promote a news score;
- change entry authority;
- create a second event store;
- tune thresholds against the same observed returns and call it validation.

## Stop condition and return

Stop after reproduction, bias audit and prospective preregistration.

Return:
- branch / PR if any;
- exact head SHA;
- reproduced table;
- sample construction;
- strongest surviving interaction;
- strongest null;
- prospective n requirement;
- what PB-G should or should not build.
