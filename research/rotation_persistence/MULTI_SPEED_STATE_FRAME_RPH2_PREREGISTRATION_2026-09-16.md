# Multi-Speed State Frame RPH-2 — Preregistration

**Frozen:** 2026-09-16, before any outcome comparison or policy study
**Operation:** `multi-speed-state-rph2-20260916-sol-001`
**Parent workstream:** `WS:LEADERSHIP-PERSISTENCE-INTELLIGENCE`
**Parent source carrier:** RPH-1 exact head `27a966041272a9de6823a590e90a0c6fd7b5141d`
**Architecture authority:** Sol (GPT-5.6), carrier `a78b8fe23d8e1ed129880ac47e97ebe96afa8aea`
**Capability at freeze:** `SPEC_ONLY`
**Authority at birth:** research/display context only; rank, gate, size, entry, exit, trade, Prophet, Oracle and portfolio authority are all false. This is an OUTCOME-BLIND descriptive module.

---

## 1. Why RPH-2 is a successor to RPH-1

RPH-1 established that slow (21-session) and fast (5-session) sector leadership, cross-sectional dispersion, and MACD phase-cross hierarchy are all measurable on the daily repository panel. It did not emit a **causal state frame** — a set of orthogonal, date-keyed, prefix-invariant structural and tactical signals suitable as inputs to a later policy study.

RPH-2 adds:

- Explicit slow structural state (leadership percentile, rank/level velocity, top-tier residency age) and fast tactical state (same, 5-session).
- MACD histogram level / sign / slope / acceleration on daily closes.
- Completed half-cycle duration and a causal trailing summary of completed half-cycles.
- Temporal-basis equivalence: standard daily EMA versus a daily filter whose per-session decay equals the 3D 12/26/9 MACD's per-session decay.
- Reuse of RPH-1 dependence definitions (dispersion, correlation) as state inputs.
- ETF-panel participation: fraction of the 10-symbol declared panel with positive causal returns.

**This wave is purely descriptive and outcome-blind.** No forward return, rank, trade candidate, Prophet recommendation, capital size, or entry rule is emitted or implied. The later P0–P3 policy study that consumes these state inputs is NOT run here.

---

## 2. Seven required state families

All state is keyed by sector symbol and date. Every value uses only rows at or before that date (no future peeking). Insufficient history returns `null` with an explicit `INSUFFICIENT_HISTORY` state label.

### 1. Structural (slow, 21-session)

- **Leadership percentile:** Spearman of 21-session sector return vs SPY return, anchored at each completed session. Summary windows: `all`, `recent_20`, `recent_60`, `prior_252`.
- **Prior-day rank velocity:** change in sector rank (1 = best) from prior session to current session. Positive = improving leadership rank.
- **Prior-day level velocity:** simple return of the sector from prior session to current session.
- **Top-tier residency age:** for each sector at each anchor session, how many consecutive prior 21-session lookback windows placed the sector in the top 3 by rank. Null when the sector is not in the top 3 on the anchor session; 0 when the sector enters the top 3 on the anchor session itself.

### 2. Tactical (fast, 5-session)

Same four metrics as Structural, computed over a 5-session lookback window. Plus:
- **Daily MACD histogram level:** value of the 12/26/9 histogram at each completed bar.
- **Bars since latest completed zero-cross:** at each date, the count of completed bars since the most recent confirmed histogram sign flip (positive→negative or negative→positive). A confirmed flip closes the prior half-cycle. The latest cross age is a lower bound until the next confirmed flip.
- **Slope:** 3-session difference in histogram value.
- **Acceleration:** change in slope over 3 sessions.

### 3. Cycle duration

- **Latest completed half-cycle:** sign (+1 / -1) and length in sessions of the most recent confirmed half-cycle. A half-cycle closes when the histogram sign flips — the confirmed flip bar is the last bar of the prior half-cycle. The incomplete current half-cycle is never emitted.
- **Trailing positive half-cycles:** summary (mean, median, count, state) of completed positive half-cycle lengths.
- **Trailing negative half-cycles:** same for completed negative half-cycles.
- Null when fewer than `MIN_OBSERVATIONS` (8) completed cycles of that sign have been observed.

### 4. Temporal basis

- **Standard daily EMA:** fast (span 12), slow (span 26), and histogram — the full 12/26/9 MACD applied to daily closes.
- **Daily 3D memory-equivalent filter:** the same spans applied to daily closes but with a per-session decay alpha equivalent to the 3D 12/26/9 MACD. The equivalent daily span is 26 (because the 3D per-session alpha = 1 − 2/27, and a 26-span EMA has per-session alpha = 1 − 1/26). The signal span equivalent is 19.5. **Label: `memory_equivalent`.** The 3D filter is NOT information-equivalent to the 3D MACD and must not be substituted for it.

### 5. Dependence (reusing RPH-1 definitions exactly)

- **Dispersion:** sample std across the 11 sector daily simple returns per session. Summary windows as above.
- **Correlation:** 20-session trailing mean of the 55 unique upper-triangle Pearson correlation pairs. Summary windows as above.

### 6. Participation

- **With positive 5-session return:** fraction of the 10-symbol declared panel (XLB…XLY) whose causal 5-session return is positive. Denominator = 10 always; absent symbols are excluded from both numerator and denominator and flagged.
- **With positive 21-session return:** same at the 21-session horizon.
- This is NOT constituent breadth — it is an ETF-panel participation signal.

### 7. Evidence and metadata

- `schema_version`, `operation_key`, `produced_at` (output generation timestamp, not source PIT proof), source universe identity, `common_rows`, `first_session`, `last_session`.
- `INSUFFICIENT_HISTORY` state with explicit null values when minimum observations are not met.
- Authority declaration identical to RPH-1: `is_context_only = true`, all action authorities false.
- Limitations list including the outcome-blind restriction and the note that historical price corrections are not reconstructable from this corpus.

---

## 3. What is NOT in scope

- Forward return, outcome, or performance columns.
- Ranker, grader, trial ledger, Prophet recommendations, Oracle signals.
- Capital sizing, entry rules, exit rules, portfolio construction.
- The later P0–P3 policy study (that is a separate operation).
- Substituting the daily 3D memory-equivalent filter for the actual 3D MACD.
- Locating a future-confirmed histogram pivot (cycle state uses completed bars only).

---

## 4. Implementation constraints

- Single focused producer module under `scripts/research/rotation_persistence/`.
- Reuses RPH-1 panel-loading and aggregation helpers; does not copy price/calendar logic.
- No new queue, store, identity, grader, trial ledger, or model authority.
- Outputs canonical strict JSON via the existing `contracts.atomic_write_json`.
- Outputs under `research/rotation_persistence/`.
- Tests use only synthetic data (no network, no vendor calls, no production writes).
- All seven state families must be present in output.
- Prefix invariance: appending future rows to the panel must not change prior state values.
- Byte-stable canonical payload apart from explicitly separated generation metadata.
