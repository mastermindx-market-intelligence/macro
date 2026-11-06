# Options Flow semantics and package-reconstruction gap

**Date:** 2026-09-11  
**Parent:** `WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY`  
**Carrier:** existing Macro draft PR `#7027`  
**State:** records-only architecture/research audit. No production code, source, service, model, score, data, gate or trade changed.

## 1. Why this audit matters

The Nightglass reconstruction made one product distinction unusually clear: urgency, package structure, position persistence, price-plan quality and outcome authority are different questions. Current Mastermind source contains those ideas in architecture, but the legacy Flow Desk enrichment still collapses several of them into convenient event-level heuristics.

The result is not merely imperfect naming. The current source can call an aggressive single-contract multi-exchange sweep `MULTI_LEG` and suppress its directional lean, while failing to recognize an unswept two-leg package. It gives positive q-score points when prior-OI and moneyness evidence are unknown, while its per-event unusualness component is structurally zero on the current producer. It then exposes the result through score sorting, `ELITE` filters and a user-facing `SIGNALS` count.

This helps explain why a competitor workflow can feel more useful despite Mastermind’s broader data estate: the competitor’s user journey separates “what printed,” “is it a package,” “did it persist,” and “is there a usable plan,” while our legacy enrichment can mislabel or compress those questions before the candidate layer exists.

## 2. Pins and exact source identities

Protected Mastermind Skillpack was loaded from `e61f2951136bdc03a7ec2f5f12f960af26656a4c` (`INDEX`, `COLD_START`, `RECONCILE_STATE`, `CLOSEOUT`; schema v1, version 1.0.1, bootstrap major 1 compatible).

Current integration pins:

- Macro main: `2051ac78c0fae30d21e799996a09285453fe045f`.
- Terminal protected master: `a4be9a3f4b51246200cb1b7c4f1d44730066a9a9`.
- `engine/live_flow.py`: Git blob `323be029c88ef8ee03d97c2ae3a878fce95ba191`.
- `engine/flow_enrich.py`: Git blob `272e7f8e035e4bba085462fd4ae857e8a64ac3b3`.
- `research/FLOW_SIGNAL_FIELD_GUIDE.md`: Git blob `e992dd088dd3120d69639bfd040f9cae673ff45c`.
- Terminal `terminal/lib/flowScore.ts`: Git blob `1f29d5626ebcd4bb2a9dc00a2941b51d5b70b23d`.
- Terminal `terminal/components/flowdesk/FeedPane.tsx`: Git blob `e0b77ce30404895a1624c034c6ead1320d9aa4cc`.
- Terminal `terminal/components/flowdesk/FlowCard.tsx`: Git blob `89a8aff5364c67292df978e8f4fbfe5d9aac802d`.

The offline audit reproduces only deterministic predicates and score arithmetic from these sources. It imports no market rows and fits no model.

## 3. Current event semantics

### 3.1 The producer emits a per-contract sweep-like flag

`live_flow.process_batch` groups prints by expiration, strike and option right. A notable output event is therefore a **single contract aggregate**. Its `swept` boolean is documented as a sweep-like heuristic: at least three prints, at least two exchanges and a span no greater than two seconds.

That is an urgency/execution pattern on one contract. It does not demonstrate that another strike, expiry or option right belongs to the same parent order.

The producer now also contains the accepted OA-1T `options.trade_nbbo_microstructure/v1` block. It measures coverage, execution-location shares, spread, quote age and sizes without asserting initiator identity, direction, ranking or probability. Current canonical organizational evidence still classifies this implementation as `BUILT_NOT_PROVEN`: the scheduled source has not supplied the required natural RTH measured-event-to-consumer proof.

### 3.2 The current event-level premium z-score is deliberately absent

The notability gate explicitly rejects comparing one contract cluster with a root-day EOD-252 baseline. `_is_notable` therefore returns `premium_z=None` and `baseline_source="floor"` for every admitted event. This is honest at the producer boundary.

That means any downstream detector or score component requiring the event’s `premium_z` is structurally unavailable on this source path unless a different correctly scaled baseline is introduced through a reviewed contract.

## 4. Sweep is currently mislabeled as multi-leg

`flow_enrich.detect_multi_leg` ignores the other session events and returns only:

```python
return bool(event.get("swept"))
```

The badge rationale then says the direction is ambiguous and the event should be treated as a spread or accumulated order. `build_enrich_envelope` sets `direction_discounted=True`; Terminal’s `FlowCard` replaces the soft side with a muted “spread/unreliable” label.

This yields two deterministic errors in capability semantics:

1. A single-contract multi-exchange sweep is classified as `MULTI_LEG`, even though the event contains only one contract.
2. A plausible two-leg package whose component contracts were not individually sweep-like is not classified as `MULTI_LEG`, because the detector does not inspect cross-contract association.

The internal field guide already distinguishes these concepts: a sweep is a multi-venue urgency pattern, while a simultaneous call/put or adjacent-strike combination is merely a package candidate requiring association evidence. It also reports that 98.3% of its SPY 2022–2023 tape-reconstruction cohort met the same sweep-like definition. **Conditionally applying the current enrichment mapping to that cohort would mark 98.3% as multi-leg/direction-discounted.** That is a cross-source diagnostic, not a measurement of current production prevalence.

This inversion suppresses precisely the kind of single-contract urgency that the Nightglass workflow exposes as a first-class fact, while still failing to reconstruct true packages.

## 5. Other association badges overstate evidence

### LADDER

The current detector fires when the same root, option right and expiry occur at three or more distinct strikes. It does not require temporal proximity, comparable size, coherent side, package ID, net price or compatible ratios. The label may be a useful attention heuristic, but it is not a demonstrated ladder order.

### REPEAT_HITTER

The current detector fires when a root appears in at least three session events. The events may differ in right, expiry, side, size and horizon. Calling this a “conviction reload pattern” overstates the association. It is root activity concentration until additional coherence is shown.

### FRESH

The current predicate requires only:

- `vol_gt_oi is True`;
- ATM or near-OTM moneyness;
- 1–45 DTE.

It does not check execution side, measured NBBO coverage, aggression, package ambiguity or next-day OI. A `mixed` event qualifies. Its rationale says “likely fresh directional positioning,” which is stronger than the evidence.

### SIZE_VS_OI

The badge fires for `vol_gt_oi=True` and premium of at least $500,000. Its text claims “new positioning.” Volume exceeding prior OI means enough gross turnover occurred that some opening activity was necessary at some point; it does not prove a position remained open overnight or identify the alert’s opening side.

A simple accounting counterexample starts with OI 100, closes those 100 contracts, opens 101 new contracts, then closes those 101 in the same session. Volume is 302—greater than prior OI—while ending OI is zero and OI change is -100. The example is stylized accounting, not market data, but it disproves overnight-retention language.

## 6. Parts of the q-score are dead or reward missingness

The current q-score weights are:

| Component | Weight | Current issue |
|---|---:|---|
| Premium magnitude | 30% | Salience, not expected return |
| Event unusualness | 20% | Always zero on the current per-event producer because `premium_z=None` |
| DTE relevance | 15% | Heuristic horizon preference |
| “Fresh positioning” | 12% | Unknown prior-OI evidence receives 60% of the component; false receives 40% |
| Moneyness proximity | 10% | Unknown moneyness receives 60% of the component |
| Repeat/cluster | 8% | Root/print concentration without parent-order proof |
| Direction penalty | -5% | Soft tape side still only a small penalty |

### Positive credit for unknown evidence

- `vol_gt_oi=None` contributes **7.2 score points**.
- `vol_gt_oi=False` still contributes **4.8 points**.
- unknown moneyness contributes **6.0 points**.

A $250,000, 30-DTE event with no z-score, unknown OI and unknown moneyness, one print and mixed soft side scores **37**. A $1 million reference event with no z-score and unknown OI scores **52**; that value is used as the minimum reference floor in the percentile `ELITE` threshold logic. The mathematical maximum is 94 because even a directional tape read receives a one-point penalty.

Missingness credit can be defensible in a ranking designed to avoid punishing unavailable data, but it must be named as such. It cannot be read as conviction, evidence quality, probability or expected return.

### Dead detectors on this source path

Because the current per-event `premium_z` is always null:

- the 20-point unusualness component always contributes zero;
- `Z_OUTLIER` cannot fire;
- the $1M-plus-soft-side `WHALE` branch cannot fire;
- only the $3M hard whale branch survives.

Current source-host research also found the scheduled OI family disconnected, which can make `vol_gt_oi` null. Under that condition `FRESH` and `SIZE_VS_OI` do not fire, but the q-score still grants the unknown-OI 7.2 points.

## 7. The UI projects more authority than the architecture permits

Terminal correctly keeps the actual score weights server-only, but the result is operationally important:

- users can sort by score;
- users can filter by minimum score;
- the feed has an `ELITE — top 2% of tape` preset;
- the toolbar calls the rows `SIGNALS`;
- source comments and types call the value a conviction score.

The accepted OA architecture says the fixed score’s lawful role is **attention/salience only**. Research candidate, calibrated probability, promoted signal, operator issue and trade are distinct states. The current UI’s score/signal/elite vocabulary therefore risks false authority even when the underlying card keeps direction visually soft.

This is not a claim that the UI currently originates trades. It is a trust/coherence defect: the words imply more than the evidence and architecture allow.

## 8. Why Nightglass feels more effective

The competitive difference is not that Nightglass publicly reveals a superior deep-learning model. Its product makes the sequence legible:

1. identify an unusual print or repeated activity;
2. expose ask/bid and classification quality;
3. determine whether the activity is single-leg or structured;
4. later distinguish what remained open;
5. place the candidate against stable price structure;
6. withhold or stall a candidate when plan geometry is poor;
7. separately show human/editorial selection and management.

Mastermind already owns much of the raw evidence and the correct future architecture. The current weakness is that the legacy Flow Desk mixes urgency, package ambiguity, missingness and salience before the governed candidate composition exists. More data or another score will not fix that product problem.

## 9. Current capability ledger

| Capability | Current state | Evidence |
|---|---|---|
| Per-contract premium-floor event | `PROVEN_LIVE` historically, current deployment health separately qualified | Existing live feed and stage estate |
| Measured trade/NBBO block | `BUILT_NOT_PROVEN` | #6585 merged; natural RTH proof owed |
| Sweep-like single-contract urgency | `PARTIAL` | Deterministic heuristic, no parent-order identity |
| Exact package/parent-order reconstruction | `NOT_BUILT` | Event schema is per contract; current `MULTI_LEG` is a sweep proxy |
| Settled OI confirmation | `DARK_OR_DISCONNECTED` on observed scheduled source | Host/store discovery; current owner must qualify |
| Q-score as attention ranking | `PARTIAL` | Built, but dead fields/missingness credit and authority language |
| Q-score as probability/alpha | `REJECTED_BY_DESIGN` | OA architecture and current DNR law |
| Governed Options Alpha candidate projection | `SPEC_ONLY` / `NOT_BUILT` in current Terminal | `options.alpha_candidate_feed/v1` specified; no current consumer implementation found |
| Conditional structure-aware plan | `PARTIAL` estate, not yet integrated in OA candidate | Existing Smart S/R and chart-digest purposes need source/clock reconciliation |
| Exact-option executable outcome | `PARTIAL` / later OA-3 | Current daily references are not exact-option fills |
| Existing Issue Desk handoff | `PROVEN_LIVE` as an owner, not connected to OA | OA-5 remains held |

## 10. Bounded repair architecture after the current production gate

This report does not open a modifying wave. The first source-to-screen production dependency remains controlled adoption of the already-accepted OA-1T source on the scheduled host and one natural event-to-consumer proof.

After that evidence exists and the owning waves are admitted, the minimal semantics repair should extend existing contracts rather than create a new system:

### Producer facts

- retain `sweep_like` as a single-contract urgency fact with its exact evidence;
- retain measured NBBO coverage/location/spread/age as observations, not buyer identity;
- label `volume_exceeds_prior_oi` as an opening-pressure proxy;
- add later settled-OI confirmation as a campaign revision, never backfill it into the earlier decision.

### Derived package association

Compose package candidates across existing event/campaign identities using temporal, size/ratio, right/strike/expiry and source linkage evidence. Return:

- `single_leg_supported`;
- `package_candidate` with candidate legs/evidence;
- `structure_resolved` with an explicit recognized payoff;
- `unresolved`/`conflicting`.

A package projection may reinterpret direction, but it must not overwrite the immutable component events.

### Attention versus candidacy

- keep any fixed heuristic as `attention_score` or percentile, not conviction/probability;
- zero or explicitly separate missing-evidence contributions rather than silently treating unknown as positive evidence;
- display component availability and why an event is unrankable or only partially ranked;
- only the governed candidate composer may state candidate readiness;
- probability remains absent until a separately promoted statistical family exists.

### Terminal language

Until statistical authority exists, prefer `events`, `attention`, `research candidates`, `unresolved structure`, `measurement unavailable` and `top attention percentile` over `SIGNALS`, `ELITE` and conviction language. Preserve bilingual parity.

## 11. Acceptance and production proof for the eventual repair

The semantics repair is complete only when real production inputs demonstrate:

1. a genuine single-contract sweep remains a sweep/urgency event and does not become multi-leg solely because it crossed venues;
2. an unswept but coherent multi-leg package is represented as a linked package candidate;
3. conflicting/unmatched legs remain unresolved rather than forced into a payoff;
4. missing OI, baseline, moneyness or NBBO evidence remains null/degraded and does not masquerade as positive evidence;
5. score/percentile language never implies calibrated return probability;
6. later OI confirmation appends a correction-safe campaign revision without rewriting the original decision;
7. the existing Terminal candidate view shows these states on mobile and desktop with browser proof;
8. exact source IDs, event/decision/availability/client clocks and package linkage are machine-readable;
9. no second collector, event identity, campaign/outcome store, queue, Issue Desk or control plane is created.

## 12. Verification artifacts

The companion offline audit generated:

- `mastermind_flow_semantics_audit.py` — SHA-256 `5a48ef94bec3125ab7b75afc57066bf2fa1f3d9a86ea35bc6871f0a79d27ad77`;
- `MASTERMIND_FLOW_SEMANTICS_AUDIT.json` — SHA-256 `f847cf6355b7a21ee37c6a5da9b49de22b2d9de73e4dae75791f82eceed09e99`;
- `test_mastermind_flow_semantics_audit.py` — SHA-256 `fa071405b186fa84920697c2d3200236616f9f980c2b6334c16b7f93072f82fe`;
- test output — SHA-256 `35a706fbd30eef7a256abacc32e4ff406c6db320964ec5040d7071b6fe5b38b9`;
- mutation probe — SHA-256 `5ebd3c4272ca9b22517ec9b022a53abc1eccaabdda0404c7a7a3573ad99b6436`;
- mutation output — SHA-256 `4acf9a9d1f67e40cfc9f8e96b9d47ca96623cccfc28b6ab52b68650fb28f5672`.

Twenty-two unit tests passed. The mutation probe detected ten of ten deliberately wrong variants. This verifies the report’s deterministic source-semantics arithmetic and counterexamples, not current R2 prevalence, predictive performance, browser behavior or a production repair.

A bounded attempt to inspect the current public R2 enrich/feed artifacts could not be completed: the Studio connector stopped responding after a read-only search timeout; the Mini/MacBook accepted pings but file/process actions reported not connected; Firecrawl had insufficient credits; Opera Browser Connector was not connected. No modifying effect was requested. The 98.3% figure is therefore retained only as the pinned historical tape-reconstruction cohort, not promoted to a current production measurement.

## 13. Exact continuation

**Primary production action:** the existing deployment/source owner qualifies controlled adoption of the accepted OA-1T measured source on the actual scheduled host, preserving sole-writer and rollback law, then proves one natural RTH event through the existing stage, campaign evidence and intended consumer.

**Independent research action:** add the sweep/package/missingness predicates in this report to the existing measurement/candidate preregistration and specify the cross-contract package-association evaluation. No acquisition, fitting or implementation begins merely because this source audit is complete.

**Held:** AD-1T2, OA-1C implementation, OA-3 exact-option outcomes, OA-4 statistical promotion and OA-5 Issue Desk integration retain their current gates. The legacy q-score is not promoted, and no new worker commission or Chairman allocation request is created by this records-only continuation.
