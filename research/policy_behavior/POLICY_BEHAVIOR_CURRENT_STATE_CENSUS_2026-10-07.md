# Policy Behavior Program — Current-State Census and Reconciliation

**Date:** 2026-10-07 UTC  
**Branch:** `research/policy-behavior-revealed-preference-20261007`  
**Status:** READ-ONLY CENSUS FINDINGS + RESEARCH PROGRAM DELTA  
**Protected law pin:** `Mastermind@6a85e0d60ebb5e1003ab2ab86aa8658ccefb6ccf`

## 1. Why this census was necessary

The first forward plan correctly identified Policy Watch as the natural owner, but the current repository has advanced beyond several older qualitative-intelligence audits.

The implementation census changes the plan in important ways:

- do **not** rebuild the policy lifecycle;
- do **not** rebuild Federal Register ingestion;
- do **not** treat the old Intel Hub policy authority leak as current;
- do **not** describe the Policy Intent track record as empty;
- concentrate on the remaining gap: a fresh, point-in-time **behavioral evidence / revealed-preference casebook** that can be evaluated against simpler baselines and then projected into the already-live context surfaces.

---

## 2. Capability ledger

| Capability | Current state | Evidence / consequence |
|---|---|---|
| Policy Watch page + realpolitik framing | **PROVEN_LIVE / existing owner** | Existing Policy Watch renders current policy context. Reuse it. |
| Deterministic policy lifecycle | **PROVEN_LIVE** | Market Ontology closure records `policy_intent_desk.lifecycle_view` + `config/policy_lifecycle_seed.json` + `build_policy_watch`, with live proof from 2026-09-19. No second lifecycle tracker/store. |
| White House sentinel / official-action lane | **PROVEN_LIVE** | The hourly `.github/workflows/whitehouse-sentinel.yml` lane is an incumbent producer; later Market Ontology receipts re-proved production behavior after fixes. Reuse, do not create another White House watcher. |
| Federal Register ingestion | **PROVEN_LIVE / reusable source rail** | `collectors/federal_register.py` writes PIT documents + regulatory velocity; `engine/policy_calendar.py` consumes it; collector is registered in `scripts/collect.py`. No second Federal Register collector. |
| Policy lifecycle / regulation date grading | **BUILT / existing evaluation rail** | `scripts/grade_policy_calendar.py` already checks matured regulatory-calendar predictions against the Federal Register store. Reuse for timing truth where semantics fit. |
| Policy Intent track record | **PARTIAL / ACCRUING** | Current `data/policy_intent/track_record.json` is as-of 2026-10-06 with 14 scored, 30 open; hit-rate 0.571, directional accuracy 0.357. Too small / weak to grant authority, but the accountability loop is no longer empty. |
| Policy Intent site artifact | **PARTIAL / STALE RELATIVE TO CURRENT LEDGER** | `site/policy_intent.json` was generated 2026-09-30 and embeds only 9 scored rows / 32 open. Current ledger has advanced to 14 scored / 30 open. |
| Editorial `data/policy/intel.json` | **PARTIAL / STALE** | Current substrate remains `as_of=2026-07-13`. The model layer can be freshly generated over a stale policy thesis substrate, so source freshness remains a first-order defect. |
| Intel Hub policy scoring firewall | **BUILT / CURRENT SOURCE IS A7-COMPLIANT** | Current `engine/intel_hub.py` explicitly excludes policy from `_VOTING_DESKS`; policy is display-only and does not enter `net_confirm`, `conf_bonus`, leading-gap, or opportunity score. The older audit's scoring leak has been repaired in current source. |
| Policy display contradiction flags | **BUILT / DISPLAY ONLY** | `policy_aligned` and `policy_conflict` compare policy with an independently derived desk lean. They remain context, not ranking votes. |
| Broad Congress.gov legislative source rail | **PARTIAL / NOT A GENERAL POLICY OWNER YET** | Congress-related sources exist in specialist programs, but the broad Policy Desk v2 congress.gov action/vote lane described in older design text is not the current central behavioral substrate. Do not invent a second generic collector without an owner census. |
| Non-China / non-U.S. policy event buses | **PARTIAL BUT MATERIAL** | Market Ontology records a live EU/UK PIT event bus through `europe_news_intel -> qbus`; international policy coverage exists but is not a complete global behavioral casebook. |

---

## 3. Current-source correction to the older audit

The older qualitative audit was useful because it found a real authority defect, but two of its headline conditions are now stale.

### 3.1 Policy Intent is no longer unscored

Current canonical track-record artifact:

- `as_of: 2026-10-06`
- `scored_total: 14`
- `open: 30`
- hit rate: **57.1%**
- directional accuracy: **35.7%**

Interpretation:

- the system now has real matured accountability rows;
- the sample is still tiny;
- hit-rate and directional accuracy are not the same thing;
- 35.7% directional accuracy is not evidence that the desk should influence money-path authority;
- this is exactly why behavioral inference should remain context / research while we build a stronger experiment.

### 3.2 The Intel Hub leak is repaired in current source

Current `engine/intel_hub.py` states that policy is absent from the scored voting set because its direction is LLM-originated.

The current voting desks are:

- news;
- alt;
- radar;
- standout.

Policy remains available for:
- dossier display;
- policy direction display;
- alignment / conflict context;
- macro context.

This is the correct boundary for the new program.

---

## 4. The real current bottleneck

The bottleneck is **not** another page, another LLM or another event store.

It is the absence of a fresh, decision-time-certified object that answers:

> What did the actor say, what did it actually do, what constraints and alternatives were visible at that time, which outcomes did the action mechanically favor, and which competing motives remain plausible?

Current components each own only part of this:

- Policy Watch owns synthesis;
- Policy lifecycle owns implementation stage;
- White House sentinel owns a live official-action lane;
- Federal Register owns regulatory documents;
- RIC owns rates / path repricing;
- news/event machinery owns company events;
- policy-intent track record scores directional proxy theses;
- none of them currently provides the **cross-source rhetoric-action-constraint research casebook** needed to adjudicate this thesis.

Therefore W1 remains the correct next research dependency.

---

## 5. Revised no-duplication architecture

### Reuse directly

- White House: incumbent sentinel / official feed;
- Federal Register: incumbent collector and PIT store;
- regulatory lifecycle: incumbent lifecycle owner;
- Fed / rates: RIC and existing Fed/rate sources;
- company events: News-to-Business-Impact / qbus / company intelligence;
- issuer technical state: Prophet;
- strategic financial support: GovRev / Defense / company contracts;
- circular credit: CCW;
- international context: existing country / EU / UK / Japan owners where they have the relevant source.

### Build only as research glue

The casebook should initially exist under `research/policy_behavior/`.

It may reference canonical observations by identity and copy only the minimum research fields needed for frozen episodes.

It must **not** become:
- a second policy lifecycle;
- a second qbus;
- a second news store;
- a second rates ledger;
- a second government-contract database;
- a production intent score.

If the casebook later proves useful, its live representation should be absorbed into the appropriate existing owner, not promoted as a permanent parallel store by default.

---

## 6. Revised execution priority

### P0 — W1 casebook + baseline race

Highest value because it tests the central thesis and is independent of live-product mutations.

Deliver:
- 40–60 PIT-certified episodes;
- M0 literal rhetoric;
- M1 mechanical inversion;
- M2 actions + constraints;
- defined outcomes / horizons;
- leakage guard;
- source-family deduplication;
- competing hypotheses.

### P1 — Freshness bridge into the existing policy context

Only after W1 semantics are stable.

The current `data/policy/intel.json` substrate is materially stale. The eventual production fix should reuse incumbent source rails and produce a fresh evidence bundle for Policy Watch rather than continuing to depend on a hand-curated July snapshot.

Important: this is an **upgrade to the existing owner**, not a new policy database.

### P2 — U.S.–Japan case study

Run as the first deep case family because it has:
- explicit cross-state interaction;
- observable market expectations;
- multiple instruments;
- a strong rhetoric/action/constraint question;
- real counterfactuals.

### P3 — announcement orchestration + Prophet interaction

Reuse #8533 event clusters and #8495 T2 evidence convergence.

Do not ask whether “good headlines work.” Ask:
- is event arrival abnormal after stress?
- is it discretionary?
- does government / financing linkage add predictive information?
- does the interaction only work after technical acceptance?

### P4 — circular-financing / selective-protection graph

Reuse CCW / GovRev / company event owners. Add external-cash conversion and failure-mode analysis.

### P5 — product projection

Policy Watch first; Rates & Inflation cross-check; Terminal / dossier read-through; Prophet only after separate prospective promotion.

---

## 7. Immediate implementation caution

The current Policy Intent desk is already producing current theses on top of a stale editorial substrate.

That means there are **two clocks**:
1. model run / market-state clock;
2. policy-intel evidence clock.

A freshly generated thesis is not necessarily a fresh policy evidence base.

Any future UI / API must expose both clocks. The new casebook should use source-native decision clocks rather than inherit the editorial `intel_asof` silently.

---

## 8. Exact frontier

The branch now contains:

1. the full revealed-preference / strategic-support masterplan;
2. a structured evidence seed;
3. the W1 casebook preregistration;
4. an uncertified initial casebook seed;
5. this current-state reconciliation.

The next research action is to expand the seed into the first **PIT-certified** batch, beginning with U.S.–Japan and Fed/Treasury episodes, and then run the first M0/M1/M2 pilot on a held-out subset.

No live scoring or production consumer needs to change before that result exists.
