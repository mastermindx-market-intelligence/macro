# Prophet Management Replay Execution Packet — Historical First-Cross Truth

**Date:** 2026-10-06  
**Parent evidence:** PR #8495 NVDA Pro re-audit  
**Owner:** existing Prophet management / plan-state owner  
**Current main inspected:** `macro@1bd2813bfffc228b4dd9d70e1bb43d4e66cb0a6e`  
**Authority:** implementation specification only; no live write/deploy authority

## 0. Defect

`engine/prophet_management.py::compute_management_state(...)` currently treats the latest close as the current call's observation and persists:

- `_first_trigger_ts`;
- `_first_t1_ts`;
- `_first_t2_ts`;
- `_mfe`;
- `_mae`;
- `_max_p1`

through `prev_state`.

When several market sessions are absent from successive calls and later appear in the price frame, the function does **not** replay the missing sessions.

It evaluates only the last available close, and if a threshold is now satisfied it stamps:

> `first_*_ts = asof`

That makes the catch-up run date look like the first historical crossing.

NVDA demonstrated this:

- formal trigger: $226.90;
- market had crossed by Sep-28;
- management state remained pre-trigger through Sep-30 because its tape was stale;
- when fresh data arrived Oct-01, `_first_trigger_ts` became Oct-01;
- the historical first crossing was earlier.

This is a management-record truth defect, not a selection defect.

---

# 1. Preserve current public API semantics

Existing API:

`compute_management_state(plan, price_history, asof, macro_stance=None, futures_chg=None, prev_state=None)`

Required preservation:

- deterministic;
- PIT-safe;
- no wall clock;
- same schema;
- same phase/confidence rules when no bars were missed;
- same existing freshness authority;
- same plan clock;
- same management-only authority tier.

Do not make browser/runtime state the source of truth.

---

# 2. Add a replay boundary, not another state machine

Recommended shape:

A pure helper inside the existing management owner, e.g.

`replay_management_path(plan, price_history, *, through_asof, prev_state, ...)`

or equivalent internal decomposition.

The helper should determine the first not-yet-accounted-for market session and evaluate missing bars **in chronological order** through the final as-of session.

It must reuse the existing threshold/geometry semantics.

Do not create a second phase detector.

---

# 3. Required replay cursor

The persisted state needs an explicit monotone market-data cursor.

Recommended additive internal field:

`_last_evaluated_price_session`

Semantics:

- exact latest price session whose close has been folded into MFE/MAE/first-cross/path state;
- never inferred from management `asof`;
- updated only after the corresponding bar is evaluated.

If adding this field is schema-incompatible, use an existing internal/private provenance field or versioned compatible extension after exact contract review.

Do not infer the cursor from `_first_trigger_ts`.

---

# 4. Replay algorithm

For each plan-state update:

1. PIT-validate the frame: no row after requested `asof`.
2. Resolve the plan clock using the existing `plan_clock_date`.
3. Resolve previous replay cursor.
4. Select rows:
   - after the previous evaluated price session;
   - on/before `asof`;
   - no row before plan's lawful management/entry clock.
5. Sort ascending by market session.
6. For each missing bar:
   - compute signed move and threshold geometry;
   - update MFE;
   - update MAE;
   - update max p1;
   - if trigger is first crossed, stamp **that bar's session**;
   - if T1 first crossed, stamp that bar's session;
   - if T2 first crossed, stamp that bar's session.
7. After path accumulators are correct, compute the final displayed management state at requested `asof`.
8. Apply current frame freshness to **current action presentation**.
9. Persist replay cursor.

This separates:

- historical path truth;
- current-action freshness.

A stale current action can be withheld while historical crossings remain accurately reconstructed from newly arrived PIT-safe bars.

---

# 5. Crossing semantics

Use the same BULL/BEAR direction semantics as current code.

For BULL:

- trigger crossed when close satisfies incumbent trigger condition;
- T1/T2 crossed according to incumbent p1/p2/target semantics.

For BEAR:

- crossing direction reverses consistently.

Do not introduce high/low-based fills unless the management contract explicitly changes; current management is close-based.

If later intraday crossing semantics are desired, that is a separate versioned study.

---

# 6. MFE / MAE semantics

Current implementation updates excursion from one last-close observation per call.

Replay should instead fold every newly available missing close in chronological order.

This fixes catch-up paths such as:

- plan at 100;
- missed bars 105 → 120 → 108;
- catch-up final close 108.

Correct reconstructed close-based path:

- MFE = +20, not +8;
- first T1 could be on 120 session even if current price is below T1;
- retention/giveback can then use real accumulated path.

Do not retroactively read any bar that was not in the supplied PIT-safe frame.

---

# 7. Freshness interaction

Replaying historical bars does **not** make the current action fresh.

Example:

- frame catches up only through Sep-30;
- requested asof Oct-02;
- replay can truthfully establish trigger crossed Sep-28;
- current recommended action may still be withheld because latest price session is stale.

Required separation:

- `historical_path_state` can advance from newly known historical bars;
- `recommended_action` remains subject to existing price-frame freshness.

Do not erase historical path facts merely because current quote is stale.

---

# 8. Idempotence

Re-running the same exact:

- plan;
- price frame;
- `asof`;
- prior state

must produce byte-equivalent path facts.

Once `_first_trigger_ts` is set to a historical first-cross session, later calls cannot move it forward or backward unless a separately authorized correction/reconstruction mechanism applies.

Appending bars after the cursor must not re-fold older bars into MFE/MAE in a way that changes results.

---

# 9. Required tests

## M1 — no-gap behavior unchanged

Sequential daily calls with no missing sessions.

Expected:

- outputs match incumbent behavior for phase/cross clocks/MFE/MAE within exact existing semantics.

## M2 — missing trigger bar replay

Plan:

- entry 100;
- trigger 105;
- previous cursor at 103;
- missing closes: 104, 106, 108;
- catch-up asof on final row.

Expected:

- first trigger = session of 106;
- not catch-up run timestamp.

## M3 — T1 crossed then gave back before catch-up

Closes:

- 110;
- 116 (T1=115);
- 108.

Expected:

- `_first_t1_ts` = 116 session;
- `_mfe` retains +16;
- current detection can reflect giveback using existing phase law.

## M4 — T2 crossed historically

Equivalent first-cross test for T2.

## M5 — BEAR replay

Thresholds crossed downward.

Expected exact first-cross sessions.

## M6 — MAE through skipped bars

A severe adverse close exists between prior cursor and catch-up final close.

Expected MAE records the skipped adverse close.

## M7 — PIT rejection

Frame contains any row after requested asof.

Expected existing assertion/refusal.

## M8 — replay cannot make current action fresh

Latest price session still stale relative to requested asof.

Expected:

- historical first-cross fields correct;
- current `recommended_action` follows stale-frame safety.

## M9 — idempotent rerun

Same frame/cursor.

Expected no path double count or timestamp drift.

## M10 — partial append

First run replays first two missing bars; second run receives one more.

Expected exact same final path as a single run over all three bars.

## M11 — plan-clock floor

No bar before lawful entry/management clock may create trigger/T1/T2 or MFE/MAE for the plan.

## M12 — NVDA golden regression

Use a frozen close sequence spanning:

- Sep-25 plan basis;
- Sep-28 trigger crossing;
- Sep-29;
- Sep-30;
- Oct-01 catch-up/current state.

Expected:

- first trigger historical session = Sep-28, subject to the exact frozen close fixture and incumbent close-based threshold;
- never Oct-01 solely because that is the catch-up run date;
- MFE/MAE equal chronological replay;
- no future leakage.

---

# 10. Build-site / state persistence boundary

`scripts/build_prophet.py` already loads prior state and calls `compute_management_state`.

Preferred integration:

- keep one management owner;
- let the engine derive/replay from price history;
- builder remains a caller/persister.

Do not make `build_prophet.py` independently scan thresholds.

One threshold implementation only.

---

# 11. Reconstruction provenance

If replay is used to correct previously emitted incorrect first-cross dates in durable/public historical artifacts, that is a **correction/reconstruction effect**, not an ordinary forward update.

Use the existing Prophet integrity/correction owner.

Do not silently rewrite append-only historical truth.

The first implementation may safely:

- fix forward behavior;
- add regression tests;
- produce a separate correction packet for already-published affected states.

Historical correction requires its normal custody/review path.

---

# 12. Done-when

Forward defect is closed when:

1. missing bars are replayed chronologically;
2. first trigger/T1/T2 are stamped on actual first-cross price sessions;
3. skipped bars contribute to MFE/MAE;
4. current action remains freshness-gated;
5. no future bars can enter;
6. idempotence holds;
7. no-gap behavior stays unchanged;
8. NVDA regression reproduces Sep-28 rather than Oct-01;
9. ordinary nightly/catch-up path is verified;
10. any historical state correction is separately provenance-stamped.
