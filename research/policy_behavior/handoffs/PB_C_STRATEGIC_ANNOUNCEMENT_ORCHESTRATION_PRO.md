# PB-C — Pro Commission: Strategic Announcement Orchestration Study

**Operation key:** `PB-C-STRATEGIC-ANNOUNCEMENT-ORCHESTRATION-20261007`  
**Recommended model/mode:** **Astra Pro**  
**Research-only:** yes  
**Receiver mode:** `DIRECT_TARGETED` on Chris's live delivery into the intended session  
**Receiver binding:** `CAPACITY_SELECTABLE`

## Pro-mode receipt

```text
COGNITION_ROUTE: CHAT_INCLUDED_DEFAULT
CHAT_REASONING_MODE: PRO_MODE_EXCEPTION
WHY_PRO_MODE: This mission requires designing and executing an adversarial event-study framework over discretionary corporate announcements, market stress, government links and cross-firm sequencing while separating calendar effects, syndication and economically distinct events.
WHY_NON_PRO_INSUFFICIENT: The main failure mode is post-hoc pattern discovery from memorable winners; the session needs sustained adversarial judgment, event semantics, matched controls and multiple null models rather than a simple news search.
PRO_MODE_TASK_CLASS: ADVERSARIAL_JUDGMENT
EXPECTED_DURATION_MINUTES: 210
STOP_CONDITION: Stop when the event taxonomy and stress windows are preregistered, a sufficiently broad labeled pilot panel with negative controls exists, the main clustering/hazard hypotheses have been tested or explicitly data-blocked, and a falsifiable research packet is returned.
```

**ROUTE:** ChatGPT Astra Pro  
**WHY:** the task is hypothesis-heavy, selection-bias-sensitive and research dominated.  
**WHY NOT FABLE:** the program boundary, event owner and no-authority constraints are already frozen; no principal-level implementation or cross-repository custody is required.

## Mission

Test the hypothesis that **discretionary economically material positive announcements from strategically connected firms become unusually likely after predefined market or own-stock stress, and may arrive in cross-firm sequences that are hard to explain by ordinary corporate calendars alone**.

Do not start from the conclusion that announcements are centrally coordinated.

The study must be capable of concluding:

- strong evidence;
- partial evidence;
- ordinary calendar / issuer behavior explains the pattern;
- insufficient data.

## Frozen sources to read first

- Protected procedure: `mastermindx-market-intelligence/Mastermind@9a24ef2c4b27ac95a4d1f72f5eae1073657cd7c2`
- Policy-behavior packet: Macro PR #8560 @ `ee86db2c832c73a36837c1240df871700340d6da`
- News-to-Business-Impact PR #8533 @ `cde0219b1040c66cbc8647f86352a25794488528`
- Prophet PR #8495 @ `770918cb266b5d884978e31d61670b4efd789eaf`

PR #8533 supplies the preferred event semantics: articles are claims, event clusters deduplicate reporting, economic impact is distinct from attention and market response.

PR #8495 supplies technical-state context. Do not modify either PR.

## Core question

Is the timing of strategic-company support events abnormal **conditional on stress and known calendars**?

The research target is event arrival / sequencing, not whether all positive company news raises stock prices.

## Universe

Start with a predeclared universe that includes:

- MAG7;
- leading semiconductor / AI-compute firms;
- networking / optical / memory / power infrastructure;
- major listed counterparties to frontier-model companies;
- defense / critical-mineral strategic firms as non-tech strategic controls;
- matched non-strategic large-cap controls.

Do not select issuers because they later rallied.

Document the universe rule before reading outcome windows.

## Event species

At minimum classify:

- buyback authorization / acceleration;
- strategic partnership;
- hyperscaler / AI-model-company commercial commitment;
- capex / capacity commitment;
- financing package;
- warrant / equity-linked commercial agreement;
- government contract;
- subsidy / grant / price floor / offtake;
- White House / Treasury / Commerce / Defense agreement;
- regulatory fast path / strategic approval;
- material product or deployment announcement;
- ordinary earnings / guidance / investor-day events as calendar controls.

For each event preserve:

- first-public timestamp;
- source family;
- scheduled vs discretionary;
- announcement vs authorization vs execution;
- issuer economic materiality;
- financing link;
- government link;
- counterparties;
- event cluster / root source identity;
- whether the event changes cash-flow expectations or mainly attention/capital return.

## Stress windows — freeze before outcome testing

Construct several prespecified stress definitions, such as:

- Nasdaq drawdown from 20d / 60d high;
- semis relative-strength drawdown;
- issuer drawdown from 20d / 60d high;
- breadth deterioration;
- VIX shock;
- 2y / real-yield shock;
- growth / AI factor selloff;
- proximity to prior support only if defined mechanically and without future extrema.

Use more than one threshold but do not data-mine dozens after seeing results.

## Main hypotheses

**C1 — STRESS_HAZARD**  
The hazard of discretionary positive strategic events rises after predefined stress.

**C2 — CONNECTED_HAZARD**  
The effect is stronger among firms with documented government / strategic-program / public-private links.

**C3 — CROSS_FIRM_SEQUENCE**  
Related issuers' events arrive in statistically unusual sequence / spacing relative to calendar nulls.

**C4 — ECONOMIC_QUALITY_MATTERS**  
Economically material / expectation-changing events have stronger post-event persistence than attention-only events.

**C5 — ORDINARY_CALENDAR_NULL**  
The apparent pattern disappears after earnings, conference, product-cycle, previously announced close-date and known policy-calendar controls.

Treat C5 as a first-class hypothesis, not a nuisance.

## Required nulls / controls

At minimum:

- matched stress windows with **no** supportive announcement;
- matched issuers with similar size/sector but weak strategic linkage;
- known corporate calendar events;
- same event species in non-stress periods;
- source-family deduplication;
- random / permuted event-date null;
- leave-one-famous-issuer-out results;
- leave-one-event-species-out results.

If feasible, include a pre-period to test whether the pattern is new or longstanding.

## Market-effect layer

For each event, separate event arrival from effect.

Measure as available:

- issuer absolute / SPY-relative / sector-relative return;
- index contribution;
- breadth;
- revisions;
- options repricing;
- volume / gap;
- H1 / H5 / H21 persistence;
- reversal / fade.

Do not infer coordination because the market response was positive.

## Data integrity

- Article count is not event count.
- Multiple outlets repeating one root release are one source family.
- A White House dinner / meeting is a coordination **channel**, not proof of scheduled market support.
- Government connection must be source-backed.
- Outcome-selected support / resistance dates are forbidden.
- Negative announcement outcomes stay in the sample.
- Events that look “supportive” but were pre-scheduled must remain clearly typed.

## Deliverables

If GitHub write is verified, use a fresh branch from current `main` and write only under:

`research/policy_behavior/pro_returns/PB-C/`

Preferred files:

- `PB_C_ANNOUNCEMENT_STUDY_PREREG.md`
- `PB_C_EVENT_PANEL.json` or parquet/CSV if more suitable
- `PB_C_STRESS_WINDOWS.json`
- `PB_C_RESULTS.md`
- `PB_C_NULL_TESTS.md`
- reproducible research script(s)

A smaller but rigorously labeled pilot is better than a large contaminated panel.

## Acceptance

A valid return must include:

- frozen universe;
- frozen stress definitions;
- event taxonomy;
- scheduled/discretionary distinction;
- at least 30 unique root events if lawful data allow, including negative/null examples;
- stress windows with no announcements;
- at least one calendar-control test;
- at least one permutation or comparable null;
- leave-NVDA-out / leave-famous-winners-out sensitivity;
- confidence in C1–C5 separately;
- no central-orchestration claim unless the evidence survives ordinary-calendar and selection-bias controls.

If data are insufficient for a statistical conclusion, return a build-ready prospective design plus the strongest honest pilot evidence.

## Non-goals

Do not:

- create a new canonical event store;
- rewrite News-to-Business-Impact;
- change Prophet;
- build a production “support operation” score;
- infer private government intent solely from corporate event timing;
- hand-select winners and call the pattern validated;
- deploy or merge.

## Stop condition and return

Stop when the preregistration, pilot panel, null tests and conclusion are complete.

Return:
- branch / PR if any;
- exact head SHA;
- sample counts by event species;
- event/source dedup method;
- strongest positive result;
- strongest null or falsification;
- whether PB-G should treat announcement orchestration as SURVIVES / WEAK / REJECT / PROSPECTIVE_ONLY.
