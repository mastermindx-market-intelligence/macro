# Macro Dashboard VNext — Design Record

**Date:** 2026-09-14  
**Status:** `BUILT_NOT_PROVEN` — design complete enough for Chairman review; no production implementation or acceptance claimed  
**Figma:** https://www.figma.com/design/zU2Zv96P8qzEAlHEk1asbZ  
**Macro baseline:** `e0e3fda2fa2a44d8d64c3f0a52b9d56c1de3653b`  
**Sol Skillpack:** `f4730cc65436d86500ef827c24493f83a7e41def` (`bootstrap_major = 1`)  
**Authority:** Chairman Chris is final business authority. Sol owns product thesis, experience architecture, design ruling, decomposition, adversarial review, and final acceptance.

## 1. Executive ruling

The Macro dashboard should become a **decision command center**, not a longer collection of independent dashboard cards.

The first screen must answer four questions without requiring the primary user to scroll:

1. **What regime are we in?**
2. **What changed?**
3. **What is fragile or disagreeing?**
4. **What should I do or watch next?**

This is an experience and hierarchy redesign, not a new forecasting system. VNext must consume the existing regime, damage, policy, tape, event, source, provenance, correction, and publication systems. It must not introduce a parallel score, data plane, event system, authority plane, or model-originated trade policy.

The Macro dashboard remains a supporting intelligence surface for Mastermind’s spoon-fed signal and intelligence proposition. It should help users understand the environment around Prophet and other actionable intelligence; it should not reposition Mastermind as a generic research-terminal product.

## 2. User job and machine job

### Primary user job

A retail-professional or sophisticated market participant needs to understand the current macro environment quickly enough to decide whether to follow strength, reduce aggression, wait for a catalyst, or investigate a specific risk. The user should not have to mentally reconcile a long sequence of cards before reaching a usable posture.

### Machine and intelligence job

The system must:

- project the canonical regime state without changing its authority;
- keep the trend, damage/stress, and capital-policy reads independently inspectable;
- show where those reads agree and disagree;
- expose what changed and which inputs drove the change;
- connect summary state to purpose-built detailed workspaces;
- retain point-in-time identity, source, freshness, null, stale, correction, and fallback behavior;
- allow explanatory model synthesis only after deterministic state and evidence are established.

## 3. Verified current state

The editable production baseline preserves the live page’s important capabilities:

- regime label, score, support state, and 46-session path;
- separate trend, damage/stress, and capital-policy reads;
- cross-asset tape;
- “What To Do Now” guidance;
- live event status and scheduled catalysts;
- Fed path, sentiment, sector temperature, policy monitor, AI brief, and alerts;
- destination cards and data-health disclosure.

The current page is information-rich, but its hierarchy requires substantial vertical scanning. The user encounters the regime, disagreement, tape, actions, events, sector context, policy context, AI synthesis, alerts, and destinations as a sequence rather than as one resolved decision surface. Existing pop-up dashboards also use mixed structures, making the transition from summary to deep work less coherent than it should be.

VNext preserves the content law while changing the experience architecture.

## 4. Figma evidence

The Figma file contains separate truth layers so the redesign cannot erase or silently reinterpret production behavior.

| Page | Purpose | Root node |
|---|---|---:|
| `00 — Source References` | Locked production capture and preserved design laws | page `0:1` |
| `01 — Current Baseline` | Editable reconstruction of the current production page | `4:2` |
| `02 — VNext Decision Cockpit` | Primary redesigned Macro Command Center | `6:34` |
| `03 — Detailed Dashboards` | Shared drill-down system for Market Map, Fed & Policy, Alert Center, and AI Brief | `9:2` |
| `04 — Components & Tokens` | Reusable visual tokens, components, and failure states | `10:2` |
| `05 — Decisions & Handoff` | Product ruling, capability delta, implementation waves, and acceptance boundary | `10:148` |

All principal screens are editable Figma layers, not flattened screenshots. The production reference remains separately locked.

## 5. VNext experience architecture

### 5.1 First-screen command band

The command band combines three independent zones:

1. **Regime and independent reads**
   - canonical regime label and score;
   - trend read;
   - damage/stress read;
   - capital-policy read;
   - explicit disagreement rather than an opaque blended conclusion.

2. **Regime path and drivers**
   - 46-session path;
   - recent change in points;
   - input drivers such as breadth, credit, rates, or leadership;
   - static fallback remains available before or without chart JavaScript.

3. **Decision brief**
   - what changed;
   - what is fragile;
   - the next resolution point;
   - concise action language tied to the existing authority chain.

This command band is the primary independently useful capability. It must work with the current data and publication path before any broader redesign wave is treated as complete.

### 5.2 Cross-asset confirmation

A compact tape shows the same cross-asset evidence already available in production, but adds an explicit confirmation summary. Supportive and warning counts describe agreement; they do not replace or originate the canonical state.

### 5.3 Market Map

The Market Map brings sector leadership, laggards, breadth, credit, rates, and leadership participation into one visual working surface. It provides both a high-level heatmap and a confirmation ledger. The heatmap is descriptive; it does not independently rank or authorize trades.

### 5.4 Catalyst Clock

The Catalyst Clock exposes the events most likely to resolve or break the current read. Each event carries time, impact, channel, and destination. It must distinguish:

- scheduled but not yet released;
- publication time passed while an official source is still pending;
- released and provisional;
- corrected after publication;
- fully resolved.

### 5.5 Pressure and leadership

The pressure radar and leadership ledger explain why the trend and damage reads can disagree. They show the user where stress is concentrated and which cohorts are leading, recovering, damaged, or losing support.

These views must use existing deterministic and point-in-time inputs. They must not derive new trade rankings from model summaries.

### 5.6 Recommended posture

The recommended-posture card translates existing state into concise, conditional guidance. It names:

- the current posture;
- the reasons supporting it;
- the risk controls or conditions that would change it;
- the next event or input that should be watched.

This is a presentation and policy-projection layer over existing authority. It is not a new policy engine.

### 5.7 Purpose-built destinations

Every summary must resolve into a real workspace:

- **Market Map:** cross-asset, breadth, sector, and transmission analysis;
- **Event & Policy Desk:** scheduled catalysts, expectations, official releases, and post-event reaction;
- **Risk Radar:** fragile cohorts, invalidation conditions, and damage progression;
- **Evidence Trace / Lineage:** source, timestamp, correction, and deterministic inputs.

Dead decorative cards are rejected by design.

## 6. Detailed-workspace grammar

The four designed drill-downs establish one shared grammar:

1. title and as-of time;
2. state or impact badge;
3. reversible filters or tabs;
4. working content;
5. source and provenance;
6. explicit destination or next action;
7. shareable URL/state where the current application supports it;
8. escape and close behavior that returns the user to the same dashboard state.

The initial detailed workspaces are:

- **Market Map** — index health, sector leadership/laggards, and breadth;
- **Fed & Policy** — pressure balance, stance, implied path, and forces;
- **Alert Center** — fired, watching, new, and resolved stateful alerts rather than a generic news feed;
- **AI Brief** — evidence-first explanatory synthesis with an explicit non-authoritative boundary.

## 7. Visual system

VNext uses one restrained institutional dark system rather than a set of unrelated card styles.

### Core rules

- minimum functional type size: **11 px**;
- semantic colors always pair with text labels;
- no emoji or icon-font dependency for critical meaning;
- one elevation family;
- containers exist only where they clarify a task boundary;
- tabular numerals for market values;
- actions name their destination;
- no unlabeled icon-only controls;
- motion should explain state change or navigation, not decorate the page.

### Semantic accents

- green: supportive / healthy / confirmed;
- amber: warning / fragile / unresolved;
- red: damage / high-impact failure / invalidation;
- violet: model explanation, catalyst, or event context;
- cyan: information, lineage, and destination links;
- blue: primary user action.

Color must never be the sole state carrier.

## 8. Data, time, null, and correction behavior

The Figma values are copied from the September 11 production capture and are labeled as illustrative. They are not current-market claims or recommendations.

Production implementation must enforce the following behavior:

### Live and point-in-time values

- every live or recently settled value exposes an as-of time;
- values link to a source or lineage view where supported;
- point-in-time identity is preserved through corrections and replays;
- a provisional value is visibly distinct from a settled value.

### Null

A missing value must display a reason such as “source has not published.” The UI must not substitute zero, an empty chart, or a fabricated carry-forward value.

### Stale

A stale value must show the last valid time and the source. Last-valid state and current-null state remain distinct.

### Loading or source verification

A pending official publication displays “verifying source” or equivalent. The UI must never invent a number while waiting.

### Correction

A corrected source value must preserve both the initial and corrected versions in the underlying record. The user-facing state must make the correction visible and update dependent projections through the canonical correction path.

### Failure

If interactive chart code fails, the static first-frame fallback remains visible. A failed detailed workspace must show an actionable error or retry state rather than an empty panel.

## 9. Deterministic versus model method

### Deterministic and authoritative

The following remain upstream and authoritative:

- canonical regime state;
- trend read;
- damage/stress read;
- capital-policy state;
- source timestamps and freshness;
- event status;
- alert lifecycle;
- invalidation thresholds;
- trade or policy restrictions.

### Model-assisted and explanatory

Model synthesis may:

- summarize established evidence;
- explain disagreement among deterministic inputs;
- group the most relevant existing signals;
- provide natural-language context with citations to the underlying evidence.

Model synthesis may not independently:

- originate a regime or damage state;
- rank or size trades;
- gate entry or exit;
- create a new policy restriction;
- overwrite deterministic or point-in-time evidence;
- present unsupported confidence as fact.

## 10. Capability delta

| Current experience | VNext capability |
|---|---|
| Long sequence of strong but separate cards | One decision command band above the fold |
| State and action separated by substantial scrolling | Regime, change, fragility, and next action visible together |
| Read disagreement explained later | Trend, damage, and capital policy visibly independent at the decision point |
| Mixed pop-up structures | Shared detailed-workspace grammar |
| Data health primarily treated as a footer utility | Freshness, source, provenance, null, and correction become first-class interaction states |
| AI appears as another summary card | AI is explicitly evidence-first and explanatory, never authoritative |
| Several summary cards feel terminal | Every summary names and opens a purpose-built destination |

## 11. Bounded implementation sequence

Implementation must preserve the full VNext thesis while shipping one independently useful capability per pull request.

### W1 — Command band

**Mission:** Recompose the existing regime, read, tape, and driver data into the VNext first screen.

**Scope:**

- VNext page shell and navigation state;
- regime and three independent reads;
- 46-session path with static fallback;
- decision brief;
- cross-asset confirmation;
- explicit time, source, null, stale, and correction projection.

**Non-goals:** no new regime computation, data plane, event system, or policy engine.

**Acceptance proof:** a real production input travels through the current path and produces the correct visible command-band state, including at least one fallback or null case.

### W2 — Market Map and Catalyst Desk

**Mission:** Make the two highest-value summary-to-detail journeys coherent and shareable.

**Scope:**

- Market Map summary and detailed workspace;
- Catalyst Clock summary and Event & Policy detailed workspace;
- existing source, event, and alert lifecycle integration;
- correction-safe release states.

**Acceptance proof:** a user opens a real summary, reaches the correct detailed state, and can inspect its source or event lineage.

### W3 — Risk and posture

**Mission:** Connect damage cohorts and invalidation conditions to the recommended-posture surface.

**Scope:**

- pressure and leadership explanation;
- Risk Radar destination;
- posture conditions and change rules;
- explicit separation from trade-ranking authority.

**Acceptance proof:** a real correction-safe state transition changes the visible damage explanation and posture condition without altering the canonical regime improperly.

### W4 — AI and health

**Mission:** Attach evidence-first synthesis and explicit data-health behavior.

**Scope:**

- AI Brief detailed workspace;
- evidence and lineage links;
- null, stale, loading, and corrected components;
- health projection and instrumentation.

**Acceptance proof:** model prose is traceable to existing evidence, no model-originated rank or action appears, and health/correction state is visible through the real path.

## 12. Acceptance standard

The redesign is not accepted until all applicable conditions are proven:

- the primary persona can resolve the market state without scrolling;
- trend, damage, and capital policy remain separately inspectable;
- no infrastructure or schema is treated as the completed user capability;
- every live value exposes time, source, and correction-safe behavior;
- real summaries open the correct detailed workspace;
- static fallbacks prevent blank critical charts;
- dark and light themes retain functional parity;
- English and Chinese surfaces retain functional parity;
- keyboard, focus, escape, and reduced-motion behavior are usable;
- real production input reaches visible output through the real path;
- observability can distinguish loaded, stale, null, corrected, failed, and fallback-rendered states;
- Chairman acceptance occurs after production proof, not after CI or merge alone.

## 13. Non-goals

This design does not authorize:

- a new regime, stress, ranking, or policy score;
- a parallel data, event, identity, correction, transcript, queue, or publication system;
- a generic research-terminal repositioning of Mastermind;
- model-originated trade actions;
- a claim that Figma, CI, merge, or delivery equals production acceptance;
- an unbounded whole-page rewrite in one pull request.

## 14. Current state and exact next action

### Current state

- Source references: recorded in Figma.
- Editable production baseline: complete.
- VNext command-center design: complete enough for review.
- Four detailed-workspace designs: complete enough for review.
- Component, token, and failure-state library: complete enough for review.
- Implementation: not started by this design branch.
- Production proof: not started.
- Final acceptance: not granted.

### Exact next action

Chairman reviews:

1. `02 — VNext Decision Cockpit` for the primary experience;
2. `05 — Decisions & Handoff` for the product ruling, boundaries, and implementation waves;
3. `01 — Current Baseline` only as the comparison source when a VNext decision is questioned.

After Chairman approval or requested revisions, Sol should freeze the design boundaries, invoke the implementation-planning procedure, and produce the bounded W1 plan before any production code change.
