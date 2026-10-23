# A2 / Freshness Consistency Execution Packet — Alerts, Entry Availability, and Plan Publication

**Date:** 2026-10-06  
**Parent evidence carrier:** PR #8495  
**Owner:** existing Prophet V4 A2 settlement/freshness lane + existing watchlist/availability owners  
**Authority:** execution specification only; zero deployment or live behavior authority  
**Critical rule:** do not weaken the Prophet plan clock-provenance validator.

## 0. Defect exposed by NVDA

On Sep-25, three surfaces disagreed operationally:

1. the watchlist sentinel emitted a real premarket `buy_zone_enter` for NVDA;
2. that alert was sourced from an older board carrying `buy_now` / T1;
3. formal plan origination refused the same general opportunity because its source plane was stale / mixed-vintage.

The formal plan gate was correct.

The inconsistency was that an alert could still appear actionable while the stronger provenance-aware plan path refused current-action publication.

This is a **freshness consistency defect**, not an argument to relax plan validation.

---

# 1. Existing owners to reuse

## Reader-visible session truth

`scripts/freshness_sentinel.py`

Existing capability:

- `client_visible_session()` reads the production reader / served bytes;
- append-only `sentinel.first_fresh/v1` receipts already measure first reader-visible settlement.

## Settlement manifest

Frozen contract:

`prophet.settlement_manifest/v1`

Owner:

R6 A2.

Settlement chain:

`owed_session -> source_asof -> computed_asof -> artifact_asof -> published_asof -> reader_visible_asof`

A session is settled only when:

- production reader shows the owed source session; and
- served artifact hash matches the accepted bundle.

## Plan provenance

Existing `prophet_bridge` / `build_prophet` clock-provenance validation.

Preserve fail-closed behavior.

## Watchlist sentinel

Existing producer:

`scripts/run_watchlist_sentinel.py`

It reads:

- `site/factordata/us_standouts.json`;
- `site/factordata/signal_gate.json`;

and can emit `buy_zone_enter`.

It currently stamps a real UTC wall clock, but action semantics need to be bound to the source decision cut, not merely to the alert generation time.

---

# 2. Product law

Every action-like surface must answer two independent questions:

1. **What did the signal say?**
2. **Is that signal current enough to act on now?**

A stale signal may remain useful research context.

It must not retain a current-action appearance.

Required state split:

- `SIGNAL_ACTIONABLE_AND_CURRENT`
- `SIGNAL_HISTORICAL_OR_STALE`
- `SIGNAL_UNAVAILABLE`

Do not convert stale into bearish/negative.

Stale means **unknown for current action**, not “bad setup.”

---

# 3. Required decision-cut contract

For every alert / Entry Availability / plan-publication row, preserve:

- `decision_session`;
- `source_asof`;
- `source_board_asof`;
- `source_price_basis_session`;
- `source_mixed_vintage`;
- `source_delayed`;
- `computed_at`;
- `published_at` where applicable;
- `reader_visible_at` where applicable;
- source/bundle digest;
- freshness state;
- freshness reason.

The alert's wall-clock `ts` is transport/generation time.

It must never substitute for the market-data decision session.

---

# 4. Watchlist sentinel repair shape

Do not add a second freshness algorithm.

Before an alert can be emitted as `buy_zone_enter`, the sentinel must consume the existing source freshness truth.

Recommended pure predicate:

`action_surface_freshness(...)`

It should resolve from the same settlement/source clocks the plan path uses, not from `date.today()`.

Minimum requirements for current-action alert:

- board/source session is the latest legally completed decision session for the alert's strategy;
- `mixed_vintage == false`;
- required source-delay state is explicitly acceptable;
- embedded row and gate verdict are coherent;
- quote/price basis is within the current Entry Availability freshness contract.

If any required leg fails:

- do not emit `buy_zone_enter` as a current-action alert;
- optionally emit/display a distinct **research-context** state through the existing product owner;
- include explicit reason (`stale_board`, `mixed_vintage`, `source_session_missing`, etc.).

Do not silently drop the candidate from research visibility.

---

# 5. Relation to B03 emergence

A stale but important candidate may still appear in B03 as:

> Emerging candidate · current entry status unavailable

That is better than either:

- falsely saying Buy Now; or
- making the name disappear.

B03 and action-alert freshness therefore complement each other:

- B03 preserves importance/research continuity;
- A2/B4 determines whether current action state is knowable.

---

# 6. Plan origination remains fail-closed

The Sep-25 NVDA plan failure is a golden negative test.

When:

- source price basis is stale;
- board is mixed-vintage;
- source delayed status fails the plan contract;

then:

- plan must not originate;
- validation failure must remain explicit;
- no fallback may substitute a newer wall clock for an older data clock.

The fix is upstream settlement speed and downstream consistency, not validator relaxation.

---

# 7. Required latency telemetry

Measure the following per candidate/opportunity:

- `first_detection_at`;
- `first_entry_signal_observed_at`;
- `first_current_actionable_at`;
- `first_clean_source_at`;
- `first_plan_published_at`;
- `first_reader_visible_plan_at`;
- `first_realistically_executable_price_after_publication`.

Derived metrics:

- detection → actionable latency;
- actionable → clean-source latency;
- clean-source → plan-publication latency;
- plan-publication → reader-visible latency;
- total intelligence lead time consumed by infrastructure;
- whether the entry zone remained executable at each cut.

This is operational telemetry, not a new trading score.

---

# 8. Required regression tests

## F1 — NVDA Sep-25 stale alert case

Fixture board:

- NVDA `buy_now`;
- T1;
- valid buy zone;
- stale/mixed-vintage source.

Expected:

- research/context visibility may remain;
- current `buy_zone_enter` alert is refused or explicitly stale;
- no current-action copy.

## F2 — Same signal on clean current source

Expected:

- alert permitted according to existing Entry Availability rules;
- decision/session clocks preserved.

## F3 — Wall clock cannot launder stale source

Set alert generation time to “now” with old source session.

Expected:

- still stale.

## F4 — Mixed vintage always disclosed

Even when `source_asof` date looks recent.

Expected:

- action unavailable;
- reason names mixed vintage.

## F5 — Coherent board/gate required

If embedded board signal and `signal_gate.json` disagree and coherence owner cannot resolve safely:

- fail action closed;
- do not pick a convenient side.

## F6 — Plan validator unchanged

Mutation proof:

- A2/watchlist changes do not weaken `prophet_bridge` plan validation.

## F7 — Research visibility survives

A stale-action refusal does not remove the ticker from B03 lossless candidate visibility.

## F8 — Settlement truth is one truth

Liveness, rescue, watchlist/current-action surface and plan publication all resolve the same owed/source/reader-visible chain.

No local “fresh enough” constants may fork settlement truth.

## F9 — No future-session inference

Friday after-close / weekend / holiday fixtures use NYSE-completed session law.

No calendar-day shortcut.

## F10 — Publication hash mismatch

Current date/session but served bytes do not match accepted bundle.

Expected:

- not settled;
- current-action publication not advertised as settled.

---

# 9. Acceptance case

The product should be able to narrate the Sep-25 NVDA situation truthfully:

> **NVDA is an important emerging candidate. The latest available signal says the entry window was open on its source decision cut, but the source bundle is not current/coherent enough to issue a current-action alert or formal plan yet.**

Then, after clean settlement:

> **Current source confirmed. Entry Availability re-evaluated.**

This preserves the predictive insight without lying about freshness.

---

# 10. Owner routing

This packet belongs to the existing A2 settlement/freshness lane.

It may require coordination with:

- watchlist sentinel owner;
- B4 Entry Availability owner;
- Prophet plan/publication owner.

It must not:

- create a second liveness service;
- create a second settlement manifest;
- change rescue ownership;
- change ranking;
- change plan admission policy;
- create a new alert transport plane.

---

# 11. Done-when

The defect is closed only when:

1. stale/mixed source cannot appear as a current-action buy alert;
2. stale research candidates remain visible as research, not silently dropped;
3. clean current source can still produce the normal action alert;
4. plan provenance remains strict;
5. all surfaces cite the same decision/settlement clocks;
6. latency from detection to reader-visible plan is measurable;
7. NVDA Sep-25 regression passes;
8. real ordinary refresh demonstrates the fix on the production path.
