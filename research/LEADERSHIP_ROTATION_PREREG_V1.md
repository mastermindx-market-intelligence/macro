# Leadership Rotation — Pre-Registration V1 (T10)

**Programme:** LEADERSHIP-ROTATION · root seat 135304d0 · orchestrator ORCH-SCI ·
carrier lane `LR-T10-1`.
**Document id:** `leadership_rotation_prereg/v1`. **Version:** V1. **Status:** FROZEN AT
MERGE — this document is the protocol identity for every leadership-rotation study
(T11–T14). Its MERGE COMMIT SHA is the protocol identity (§6, act 1). No term of this
document may be edited after merge; any amendment is a new
`research/LEADERSHIP_ROTATION_PREREG_V2.md` whose formation dates begin after V2's own
merge (§12).

**Drafting provenance.** Drafted by lane `LR-T10-1` on fresh `origin/main` at base
`54195c10bbeb54d2218da99ea367ee1132e84127` (orchestrator-judged base `3512440213ba`
verified an ancestor by `git merge-base --is-ancestor`). During drafting the lane read
source code and research/markdown documents ONLY. No file under `data/yahoo/**`,
`data/breadth/**`, `data/rotation_events/**` was opened, loaded or decoded; no
`data/oracle/*.json` values were read beyond the pair ids already quoted by the
commission; the only data-file greps were the custody records `data/vault/seals.json`
(absent in this clone — §11) and `data/trial_ledger.jsonl`, for the strings
`rotation` / `leadership` only, family names only. No statistic was computed on market
data. Every factual claim about the codebase carries a file:line citation; every
registry/cohort fact the lane did not re-measure is cited "measured by ORCH-SCI
2026-10-14".

**Review integration.** One adversarial review (lane `LR-T10-2`, 12 findings: 2
blocker, 7 major, 3 minor) was integrated by ORCH-SCI before merge, on the drafted text
at `35ef7a207cc9`. Every integrated change is a unit definition, a denominator, an order
of operations or a test construction that the frozen decisions left unstated, so that a
harness can run this document without making a further analytical choice. No frozen
number, arm, horizon, partition date, margin, seed, block length or replicate count was
changed, and no market outcome had been read by anyone when the choices were made.

---

## §0 Status & identity

| Field | Value |
|---|---|
| Version | V1 |
| Freeze | at merge to `origin/main`; merge commit sha = protocol identity |
| Sealed-read status — P0 | `NOT_EXECUTABLE` until the T11–T14 harness exists; synthetic, no market data |
| Sealed-read status — P1 | `DEVELOPMENT` — computed freely, counted, can support no claim (§6) |
| Sealed-read status — P2 | `NOT_EXECUTABLE` until the five owner acts below are complete |
| Sealed-read status — P3 | `ACCRUING_NOT_READ` until the five owner acts below are complete |
| Consumers | the T11–T14 study lanes and the seat that accepts or refuses this protocol |
| Drafting base | `54195c10bbeb54d2218da99ea367ee1132e84127` (fresh `origin/main`; judged base `3512440213ba` an ancestor) |

**Owner acts required BEFORE any P2 or P3 read** (status until then: P2
`NOT_EXECUTABLE`, P3 `ACCRUING_NOT_READ`). This lane performs NONE of these acts and
writes no `data/`:

1. This document merged (= freeze; its merge commit sha is the protocol identity).
2. A seal for `leadership_rotation_v1/P2` registered with the existing owner
   `engine/holdout_vault.py` (`HoldoutVault.seal(window_id, content)`,
   engine/holdout_vault.py:93; seals at `data/vault/seals.json`, engine/holdout_vault.py:24)
   by the seat.
3. Family `leadership_rotation_v1` registered in the existing trial ledger
   (`engine/trial_ledger.py`: `TrialLedger` engine/trial_ledger.py:66, `log_trial` :146,
   `log_declared_budget` :204, `register_trials` :298, `effective_n` :259,
   `families` :293; `DEFAULT_PATH = data/trial_ledger.jsonl` engine/trial_ledger.py:49)
   with budget P1 = counted development looks, P2 = 1, P3 = 2.
4. The rights statement in §10 accepted by the seat.
5. A seat ruling that the §9 mapping to
   `DNR:KILL-TREND-PERSISTENCE-SECTOR-GROUP-PERSISTENCE` admits P2.

---

## §1 Selected hypotheses & exclusions (D1)

**Selected docket subset (finite; everything else is excluded with its reason).**

| Id | Question | Study |
|---|---|---|
| H1 | Q03 early detection | T12 |
| H2 | Q06 future-only continuation and false-start durability | T13 |
| H3 | Q07 paired migration vs independent legs, with the A37 common-factor / shared-constituent control | T14 |

**Mandatory controls:**

- **C1 = Q02** rolling-window carry / zero-new-return placebo (T11).
- **C2 = Q09** absolute-leg strata: every result split by absolute direction
  `both_up` / `both_down` / `mixed`.
- **C3 = Q01** breadth level vs level+change — **SOURCE_LIMITED**: development-period
  and prospective only, never confirmatory in V1 (breadth exists only from 2025-05-28,
  one regime, 344 sessions; measured by ORCH-SCI 2026-10-14).

**Excluded, with reason:**

- **Q04** — point-in-time dynamic theme membership not available; root decomposition
  belongs to another owner.
- **Q05 (standalone)** — its past-only beta residual is used inside H3 only; the
  standalone member-level form neighbours the killed trend-persistence gating baseline
  (§9).
- **Q08** — deterministic product coverage: T09 tests it, not a study.
- **Q10** — no qualified second region (A38).
- **Q11** — product/provenance UI, other owner; zero retained cross events
  (`data/rotation_events/events.jsonl`: 42 lines, all intra-sector subsector events,
  zero cross events retained; `cross_state.json` empty; measured by ORCH-SCI
  2026-10-14).
- **Q12** — economic simulation needs separate authorization.

---

## §2 Cohort (D2)

**Confirmatory cohort = the 7 registered sector/broadening context pairs, by `id`
(`data/oracle/ratio_pairs.json` v1.0, dated 2026-07-11, keyed by `id`; measured by
ORCH-SCI 2026-10-14), directional roles fixed — numerator = receiver, denominator =
donor; positive ratio movement = numerator outperforming:**

| Group | Pair id | Receiver (num) | Donor (den) |
|---|---|---|---|
| defensive_sector | `xlp_vs_xlk` | XLP | XLK |
| defensive_sector | `xlu_vs_xlk` | XLU | XLK |
| defensive_sector | `xlv_vs_xlk` | XLV | XLK |
| defensive_sector | `xlp_vs_smh` | XLP | SMH |
| broadening_proxy | `dia_vs_qqq` | DIA | QQQ |
| broadening_proxy | `iwm_vs_qqq` | IWM | QQQ |
| broadening_proxy | `rsp_vs_qqq` | RSP | QQQ |

**Groups are NEVER pooled; every verdict is per group** (defensive_sector,
broadening_proxy).

**Excluded pairs and why:**

- `wmt_vs_xlk`, `cost_vs_xlk` — retailer context is not sector confirmation; the
  producer itself says so (engine/rotation_events.py:1694 — "Retailer detail does not
  count as sector confirmation").
- `mag7_basket->xlv` — basket formed with hindsight; survivorship.
- `xlp_vs_smh` — excluded from **P2 only** (SMH instrument identity changed at the
  2011-12 HOLDRS → VanEck relaunch; the splice is unverified); kept in P1/P3.

**Registered cross pairs exist** (`config/rotation_universe.json` v2.0, registered
2026-07-18 under `research/ROTATION_UNIVERSE_EXTENSION_PREREG.md`: xlk->xlv, smh->xlv,
mag7_basket->xlv primary; xlk->xlp, xlk->xlu, smh->xlf, xlk->xlf secondary —
research/ROTATION_UNIVERSE_EXTENSION_PREREG.md:60-70). Overlap with the context pairs:
XLV/XLK, XLP/XLK, XLU/XLK. Those cross pairs belong to that prereg; V1 uses them only
for the development-only descriptive arm of §4 and does not re-evaluate their gates.

**Price basis: total-return adjusted `close` for both legs and SPY.** The lane located
the basis the early-context producer and ratio lens actually use — they AGREE, so no
information-set mismatch arises (A33; had they differed, the mismatch would be recorded
here, not repaired):

- `engine/oracle/ratio_lens.py:24-26` — "ETF legs use lib.store.read('yahoo', sym)
  'close' column, which is dividend-adjusted total return. ETF ratios are therefore
  total-return ratios".
- `engine/oracle/ratio_lens.py:179-188` — `_etf_close` reads `df["close"]`.
- `engine/oracle/ratio_lens.py:369` — every short-horizon receipt carries
  `"basis": "dividend_adjusted_close"`.
- `engine/rotation_events.py:1691-1726` + `:1717` — `early_rotation_context` consumes
  `ratio_lens.short_horizons/v1` receipts, `derived_from: ["oracle.ratio_lens"]`.
- `engine/inputs.py:21` / `:115` — `yahoo_closes(basis="tr")` (default) reads the `close`
  column (total-return, split+dividend adjusted); `basis="price"` reads `close_price`
  and is NOT used by this pathway.

**Calendar:** NYSE sessions present for BOTH legs; a pair-day with a missing leg is
UNMEASURED (kept in denominators, never zero). **Warm-up:** 252 sessions of both legs
before the first formation date.

**Who is missing (printed by every study):** XLRE (2015) and XLC (2018) do not exist in
the cohort — real estate and communication services are absent; the 2018-09-24 GICS
reshuffle moved large holdings out of XLK (composition break for the main donor);
RSP < 2003-05, IWM < 2000-05, QQQ < 1999-03 are unavailable (first sessions measured by
ORCH-SCI 2026-10-14: SPY 1993-01-29, DIA 1998-01-20, XLK/XLP/XLU/XLV 1998-12-22,
QQQ 1999-03-10, IWM 2000-05-26, SMH 2000-06-05, RSP 2003-05-01; last session 2026-10-12,
DIA 2026-10-08). The ETF-level panel has no delisted members, but historical
constituent overlap is UNMEASURED.

---

## §3 Estimand, origin, horizons, maturity (D3)

**Object separation (programme constraint, binding):** `group_measurement`,
`transition_observation` and `research_estimate` are three distinct objects, never
substitutable. Measured strength, early-transition evidence, confirmed event status,
predictive support and downstream entry suitability stay separate fields and separate
claims throughout V1.

- **Ratio level:** `R_t = log(P_num,t) − log(P_den,t)` on TR closes.
- **Availability:** a signal computed at close `t` is available after close `t`; the
  first permitted observation is the close of session `t+1` = origin `o`.
- **Primary target:** `Y_h = R_{o+h} − R_o` — future-only; no term of it is known at
  `t`.
- **Evaluation horizons:** `h = 20` sessions (primary) and `63` (secondary,
  descriptive). **Display horizons (1s/2s/5s/20s in the producer) are NOT evaluation
  horizons** (the producer's descriptive receipts are 1/2/5/20-session,
  engine/oracle/ratio_lens.py:351).
- **Delayed confirmation:** `c = 5` sessions. A confirmed observation has origin
  `o_c = t+c+1` and matures at `o_c + h`; it is compared both at common origin (`o_c`)
  and on the policy path from the initial origin `o` (maturity `t+1+c+h`). No free
  earlier execution (A32).
- **Outcome states, kept distinct, never dropped from denominators:** `MATURED`,
  `IMMATURE`, `UNPRICEABLE` (missing leg at `o` or `o+h`), `SOURCE_INVALID`.
- **Unit convention (binding):** 1 log-ratio point = 0.01 in the log units of `Y_h`.
  The H2 margin (+0.50 log-ratio points) and the H3 margin (+0.25 log-ratio points) are
  therefore +0.0050 and +0.0025 in `Y_20` / `Y_20^res` — the same scale as the §8 P0
  drift grid δ ∈ {0, 0.25 %, 0.5 %, 1.0 %} per 20 sessions.
- **Per-metric denominators (binding):** coverage uses all four outcome states and
  UNMEASURED pair-days (§7 clause 3); means of `Y_h` / `Y_h^res` are over MATURED
  entries only, with the IMMATURE, UNPRICEABLE and SOURCE_INVALID counts printed beside
  every mean; the detection-rate denominator is the partition's §5 zig-zag onsets
  (MISSES included); the false-start-rate denominator is MATURED entries at `h = 20`. No
  metric reclassifies an UNMEASURED day as zero.

---

## §4 Arms (D4)

**Identical information set for every arm: the two legs' and SPY's TR closes up to
`t`, nothing else unless stated.**

| Arm | Definition (exact) |
|---|---|
| **A0** incumbent early context | `positive_2s ⇔ R_t − R_{t−2} > 0`. Raw alarm stream = every `positive_2s` day. Suppressed onset = first `positive_2s` day after ≥ 5 consecutive non-positive sessions (declared fairness transform; raw burden always also reported). Incumbent basis: engine/rotation_events.py:1691 (positive 2s = eligible `ratio_return_pct > 0`, :1778-1794). |
| **A1** challenger — ONE hysteresis setting, no grid | `z_t = (R_t − R_{t−20}) / (σ_t·√20)` where `σ_t` = stdev of daily `ΔR` over sessions `t−62..t`. Enter when `z_t ≥ +1.0` while OFF; exit when `z_t ≤ 0.0`. Entry day = alarm onset. |
| **A2** delayed confirmation | an A1 entry that stays ON (`z ≥ 0`) for 5 further sessions; confirmed at `t+5`. |
| **B1** unconditional drift | all formation days of the same pair and partition. |
| **B2** static rank / trend | trailing 63-session ratio momentum `R_t − R_{t−63}` crossing from ≤ 0 to > 0 (onset). |
| **B3** absolute + benchmark-relative leg momentum | receiver `log(P_num/P_SPY)` 20-session z ≥ 1.0 entry (same hysteresis form as A1) — the unpaired, direct-leg arm used by H3. |
| **B4** past-fitted beta/vol context | 252-session past-only betas of each leg to SPY; residual target `Y_h^res = Y_h − (β_num − β_den)·(log SPY_{o+h} − log SPY_o)`. |
| **B5** fixed multihorizon representation, no selector | signs of `R` over 1/5/20/63 sessions reported jointly. |
| **B6** known-window carry / zero-new-return placebo | recompute A1 with the day-`t` fresh return set to zero; an entry that still fires is expiry-driven ("carry entry"); its share is reported (A31). |
| **B7** abstention | no transition called. |
| **C3a/C3b** breadth arms (development/prospective only, SOURCE_LIMITED) | C3a = breadth level of the receiver sector (`pct_above_50`); C3b = level + 5-session change; same ± hysteresis form. |

**Order of operations (binding, every arm):** raw daily states → the arm's onset
definition (A0: `positive_2s` days, then the ≥ 5-session suppression transform;
A1/A2/B3/C3: hysteresis entries; B2: crossings) → the §8 within-pair 20-session merge
(the later onset is a repeated alarm) → §5 one-event/one-attempt matching. Burden =
unmatched alarm onsets per pair-year, computed after the merge. The A0 comparison uses
suppressed onsets; A0's raw burden is printed beside it and is never substituted.

**Incumbent vocabulary (context, measured by ORCH-SCI 2026-10-14):** the producer's
context states are MIXED_ROTATION / DEFENSIVE_RELATIVE_STRENGTH / BROADENING /
NO_EARLY_SHIFT, with no repeat suppression — which is why A0's raw stream is every
`positive_2s` day. The existing replay runner is `scripts/replay_rotation_events.py`,
frozen to `research/ROTATION_COMMAND_S1_S2_PREREG.md` §2.1 (:39-46; named at :135).

**Development-only descriptive arm:** the incumbent `cross_handoff` replay
(`engine/rotation_events.evaluate_cross`, engine/rotation_events.py:640; classic
`cross_handoff` = donor `blowoff` + receiver `turn_up` + `pair_confirm`, all price-only
— the classic branch at :698-715 touches closes only) on the 3 overlap pairs, **P1
only, never in a verdict**. The cross pairs belong to
`research/ROTATION_UNIVERSE_EXTENSION_PREREG.md`; this prereg does not re-evaluate its
gates. Family-B `into_strength` (donor `contagion_bleed`) REQUIRES sector breadth
(engine/rotation_events.py:543-561, breadth gate :613-625), so it cannot be replayed
before 2025-05-28 (breadth start; measured by ORCH-SCI 2026-10-14).

**Non-inputs:** `sector_cycles`, positioning, flows, options, sentiment and any LLM
output are NOT inputs to any arm.

---

## §5 Transition dating & event accounting (D5)

**Ground-truth transition dating for H1 — a retrospective EVALUATION label, never a
feature.** Zig-zag on `R_t` with fixed log amplitude **A = 0.08** and minimum up-phase
length **40 sessions**: an onset `T` is a zig-zag trough followed by a rise of ≥ A
before a fall of ≥ A from the running maximum, lasting ≥ 40 sessions. **A = 0.12 is a
descriptive sensitivity only (never in a verdict).**

**One-event / one-attempt matching:**

- An alarm at `t ∈ [T, T+40]` matches onset `T` (earliest matching alarm counts;
  delay = `t − T`).
- Further alarms inside the same up-phase are **REPEATED** alarms.
- Alarms outside every `[T, T+40]` window are **FALSE STARTS**.
- Alarms inside an up-phase after `T+40` are **LATE**.
- Onsets with no matching alarm are **MISSES**.
- An alarm state that ends with no onset within 40 sessions **EXPIRES** as a false
  start.
- Superseded episodes are retained.
- Quiet-period alarm rate (sessions in no up-phase) is reported per pair-year.

---

## §6 Partitions, custody, look budget (D6)

| Partition | Definition | Evidence class / verdict authority |
|---|---|---|
| **P0** synthetic | No market data; any number of runs (power design §8). | Synthetic; sizes the test, supports no market claim. |
| **P1** development / discovery | Formation **2015-01-02 → 2026-10-12**, outcomes truncated as IMMATURE past the last close. Contaminated (roster §11). Every P1 number is labelled **DEVELOPMENT** and can support no claim. Every arm/metric computed in P1 is counted and the count is reported. | DEVELOPMENT only. |
| **P2** era-inspected reconstructed holdout | Formation from each pair's first eligible session (the first pair-session — an NYSE session on which both legs trade — that is preceded by 252 pair-sessions on which both legs traded) to the last session with `o+c+63 ≤ 2014-12-31`; **63-session embargo before P1**. Exactly **ONE look for the whole family**. Because 1998-12 → 2014 was already inspected by `thematic_rotation_phase0` and was the in-sample of `defensive_rotation_phase0` (§11), P2 is **FALSIFICATION-ONLY**: it can issue `NOT_SUPPORTED` (binding, preserved) or `CONSISTENT` (no claim) — it can **NEVER** issue `SUPPORTED`. | RECONSTRUCTED (`naturally_observed=false`). |
| **P3** prospective confirmatory accrual | Formation dates from the **first NYSE session after the UTC date on which this document merges to main**. The ONLY partition that can issue `SUPPORTED`. | Prospective. |

**P3 look budget.** Look 1 when every (hypothesis, group) has ≥ 20 matured honest-N
clusters AND ≥ 12 months have elapsed; look 2 at ≥ 40 clusters or 36 months; one-sided
α = 0.025 per look, Holm across the family within each look. P3 additionally checks
concordance between the harness recomputation of A0 and the naturally issued nightly
`early_context` rows (nightly wiring: engine/rotation_events.py:2075-2081); every
mismatch is reported.

**Custody owner acts** — the five acts of §0, all required before any P2 or P3 read;
the existing owners are `engine/holdout_vault.py` (seal, peek, retire;
engine/holdout_vault.py:93/117/131) and `engine/trial_ledger.py`
(`register_trials`, `log_declared_budget`, `effective_n`). Expected P2 cluster counts
may be planned from P1 or P0 only, never from P2 (§8).

---

## §7 Joint rule, practical margins, verdict classes (D7)

**Verdict classes:** `SUPPORTED` (P3 only) · `CONSISTENT` (P2 pass, no claim) ·
`NOT_SUPPORTED` (binding from P2 or P3, preserved) · `UNDERPOWERED` (< 20 honest-N
clusters for that hypothesis × group; underpowered ≠ no effect) · `IMMATURE` ·
`NOT_EXECUTABLE` · `SOURCE_LIMITED`.

**A (hypothesis, group) passes only if ALL hold in the read partition:**

1. **Incremental value:** point estimate ≥ practical margin AND one-sided bootstrap
   lower bound > 0, after Holm across the 6 tests H1–H3 × 2 groups.
2. **Stability:** the read partition's calendar pair-sessions are split into three
   contiguous blocks of equal count; a cluster belongs to the third containing its
   earliest-onset date and is never split; the clause holds when the point estimate
   restricted to each third's clusters has the same sign as the full-partition point
   estimate in ≥ 2 of 3 thirds.
3. **Coverage:** all-event coverage ≥ 80 %. Denominator = every NYSE pair-session of
   the group's registered pairs (§2) from each pair's first eligible session (§6)
   through the partition's last formation session — UNMEASURED and all four outcome
   states included. Numerator = pair-days MATURED with a finite `Y_20`. The gate applies
   to all-event coverage only; supported coverage is printed beside it with the
   withheld-state counts (A35) and is never the gated quantity.
4. **False-alarm burden:** below, per hypothesis.
5. **Minimum support:** ≥ 20 honest-N clusters.

**Calibration: NOT APPLICABLE** — no arm emits a probability; heuristic states are not
probabilities and must not be presented as such.

**H1 margins (BOTH conditions):**

- Versus A2 delayed confirmation: A1 reduces median delay by ≥ 5 sessions, with burden
  (unmatched alarm onsets per pair-year) no more than +0.5 above A2's, and detection
  rate no more than 5 pp lower.
- AND versus A0 suppressed onsets: A1 cuts burden by ≥ 25 % with detection rate no more
  than 10 pp lower.

**H1 test construction (binding).** H1 is an intersection–union test of its two
conditions. Condition (a), versus A2: statistic = A1's median-delay reduction versus A2,
in sessions; margin ≥ 5; the burden (+0.5) and detection (5 pp) clauses are
non-inferiority pass clauses judged on their point estimates, with bootstrap intervals
printed. Condition (b), versus A0 suppressed onsets: statistic = A1's relative burden
reduction `1 − burden_A1 / burden_A0`; margin ≥ 0.25; the detection (10 pp) clause is a
non-inferiority pass clause judged on its point estimate, with its interval printed.
Each condition's one-sided p-value is computed from its own statistic (§8); the H1
p-value entered into the Holm family is the larger of the two, and H1 meets clause 1 only
if both conditions meet their margins.

**H2 margins:** mean `Y_20` after A1 entries minus the better of B1 and B2 at the same
pairs/partition ≥ **+0.50 log-ratio points**. Safety endpoint: A1's 20-session
false-start rate (`Y_20 ≤ 0`) no more than 5 pp worse than B2's. Cost-of-delay (A1 at
`o` vs `o_c`) and B6 carry share always printed.

**"The better of B1 and B2" (binding):** the baseline with the higher mean `Y_20` over
its own entry/formation set in the read partition — a within-read conservative maximum
that can only shrink A1's margin. The same maximum is re-taken inside every bootstrap
replicate; no P1 outcome selects the baseline. For H2 and H3 the statistic entering
Holm is the margin quantity itself (A1 minus the better of B1/B2 on `Y_20`; A1 minus B3
on `Y_20^res`).

**H3 margins:** on residual targets `Y_20^res`, mean after pair entries (A1) minus mean
after receiver-only leg entries (B3) ≥ **+0.25 log-ratio points**. Overlap rule: pairs
sharing a leg are one cluster; constituent overlap is UNMEASURED historically and is
disclosed, not assumed zero.

---

## §8 Dependence, honest-N, uncertainty, synthetic power (D8)

**Honest-N = number of common-shock clusters.** Events of the same group whose onsets
fall within ±10 sessions form one cluster; within one pair, entries closer than 20
sessions are merged (the later is a repeated alarm). Overlapping pairs and days are not
N. Cluster formation is single-linkage (the transitive closure of the ±10-session rule).
A cluster's calendar coordinate — for the block bootstrap and for the §7 stability
thirds — is its earliest onset date.

**Uncertainty:** stationary block bootstrap over calendar time, mean block 21 sessions,
2000 replicates, clusters resampled whole, seed 20261014; report the two-sided 90 %
interval and the one-sided lower bound.

**Family p-values (binding):** each of the 6 family p-values is the one-sided bootstrap
p-value `p = (1 + #{replicates with statistic ≤ 0}) / (1 + 2000)`. "One-sided bootstrap
lower bound > 0 after Holm" (§7 clause 1) means the Holm-adjusted p-value is below the
look's one-sided α = 0.025 — P2 and P3 alike; raw and Holm-adjusted p-values are both
printed. P1 computes the same quantities, labelled DEVELOPMENT.

**P0 synthetic power design** (run by the T11–T14 harness before any P2/P3 read; no
market data): simulated `R` paths with daily vol σ ∈ {0.7 %, 1.0 %, 1.4 %}, planted
up-regimes with drift δ per 20 sessions ∈ {0, 0.25 %, 0.5 %, 1.0 %}, onsets at a
Poisson rate of 2/year, regime length 40–120 sessions, within-group common factor
ρ ∈ {0.5, 0.8}; every arm, metric, clustering and bootstrap run as registered; report
power to reach the pass rule at N_clusters ∈ {20, 40, 80} and the false-pass rate at
δ = 0 (must be ≤ the nominal α, else the test is mis-sized and the verdict machinery is
repaired before any read). The expected P2 cluster count may be planned from P1 or P0
only, never from P2.

**The ten `SYNTHETIC_FALSIFIERS` controls are part of P0:** both-down pair; missing
breadth; empty population; composition-only breadth; shared holdings; rolling carry;
beta-only excess; relative units; delayed confirmation; valid zero score. Passing them
proves only the stated mathematical distinctions (relative resilience ≠ absolute
recovery; logical bounds ≠ confidence intervals; trailing-score improvement can be
known expiry arithmetic; etc.) — never a live market claim.

---

## §9 DNR-to-hypothesis mapping (D9, A28)

Rows transcribed from the commission (verified present in
`research/DO_NOT_REBUILD.md` at base `54195c10bbeb`; cited by key only — `DNR:<KEY>`,
never by row/line number, per that registry's own rule):

| Row | Does / does not touch V1 |
|---|---|
| `DNR:KILL-ROTATION-CYCLE-CONFLUENCE` | DOES NOT TOUCH — no cycle conditioner, no rotation×cycle arm; `sector_cycles` is not read. |
| `DNR:KILL-TREND-PERSISTENCE-SECTOR-GROUP-PERSISTENCE` | DOES NOT TOUCH as the killed construction — killed: 11-GICS-sector, member-level, rank-linear group features against relative-to-SPY forward 20/60 returns, formation 2022-07-06..2026-06-02. H2 differs in unit (registered ETF pair ratio, not members), form (state-entry event, not rank-linear), and target (pair ratio, not member vs SPY). The killed formation window lies inside P1 (development only) and is never confirmatory; P3 is gated on post-merge formation dates as that row demands; P2 admission is reserved to a seat ruling (§6 act 5). |
| `DNR:KILL-ROTATION-SCHEDULE` | DOES NOT TOUCH — no new display artifact or parallel surface; this is a study protocol only. |
| `DNR:KILL-ROTATION-TM-KEEPS` | DOES NOT TOUCH — no same-complex Time-Machine keeps; intra-sector subsector pairs are excluded. |
| `DNR:KILL-POSITIONING-FUSION` | DOES NOT TOUCH — no positioning/flow/options input, no fused score. |
| `DNR:KILL-SPONSORSHIP-SCORE` | DOES NOT TOUCH — no fused score of any kind. |
| `DNR:KILL-DEFENSIVE-FLOOR-BUNDLE` | DOES NOT TOUCH — no count-conjunction bundle; group states are reported, never fused into a floor. |
| `DNR:KILL-OUTCOME-AUDITION` | DOES NOT TOUCH — one arm setting for every pair; no per-pair best-of-grid selection. |
| `DNR:KILL-PSS-SR2-PEER-DIFFUSION` | DOES NOT TOUCH — no name-level peer diffusion. |
| `DNR:KILL-PSS-SR3-PARTICIPATION` | DOES NOT TOUCH — no name-level participation construction. |
| `DNR:HOLD-FACTOR-UNIVERSE-WIDENING` | DOES NOT TOUCH — no factor-universe change. |
| `DNR:KILL-COMMODITY-XSEC-MOM` | DOES NOT TOUCH — no cross-sectional momentum long/short portfolio. |
| LLM in detection | NONE — constitution A7; backed by `DNR:KILL-LLM-ORIGINATION` and the non-inputs list of §4. |

**Additional rows found by this lane's grep** of `research/DO_NOT_REBUILD.md` for
rotation / sector / breadth / leadership / handoff / momentum / relative strength, each
with its does/does-not-touch line:

| Row | Match | Does / does not touch V1 |
|---|---|---|
| `DNR:KILL-REGIME-SCORECARD` | breadth fusion into a regime verdict | DOES NOT TOUCH — no composite regime score; C3 breadth arms are standalone level-vs-level+change comparisons, never fused. |
| `DNR:KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR` | breadth + leadership in a 16-input fusion list | DOES NOT TOUCH — no composite monitor; per-arm measurement only. |
| `DNR:KILL-FORCED-CALLS` | Mag-7 "leadership board" | DOES NOT TOUCH as a construction — the row closes operator-forced un-gauntleted directional calls on signal surfaces and says a leadership read may return "only via prereg + gauntlet"; V1 IS that prereg path, and pins nothing to any signal surface. |
| `DNR:KILL-DOW-TRANSPORTS` | "rotation physics" in the ruling text | DOES NOT TOUCH — no Dow-theory transports leg; the defensive radar legs that row cites are unrelated display organs. |
| `DNR:KILL-PER-SIGNAL-FAMILY-RELIABILITY` | "momentum reliability" grid | DOES NOT TOUCH — no family×regime reliability table; registered arms on registered partitions only. |
| `DNR:KILL-LIQUIDITY-SHOCK-REVERSAL-CLASSIFIER` | "momentum base state" in the ruling text | DOES NOT TOUCH — no shock classifier; no mean-reversion arm. |
| `DNR:KILL-CN-SUPPLY-ABSORPTION` | "price-only absorption ≡ momentum" | DOES NOT TOUCH — CN share-supply family; different market, unit, construction. |
| `DNR:KILL-ASHARE-SUBSECTOR-GATE` | "subsector" | DOES NOT TOUCH — A-share subsector state gating; V1's cohort is US sector ETF pairs and gates nothing. |
| `DNR:KILL-MCO-THRUST` | "advanced_breadth" display homes | DOES NOT TOUCH — no McClellan thrust; C3 uses `pct_above_50` level/level+change only. |
| `DNR:KILL-PSS-F3-RESIDUAL` | "beta-stripped vs sector ETF" | DOES NOT TOUCH as a construction — name-level residual-reset timers are closed; H3's residual target is pair-level with past-only betas and B4 is a control arm, not a standalone promotion. |
| `DNR:KILL-PSS-SR1-ELASTICITY` | "same-sector-pulse clusters" | DOES NOT TOUCH — name-level stress-elasticity construction. |
| `DNR:KILL-PRIMED-DIRECTIONAL-GATE` | "breadth/smallcap universe" revival clause | DOES NOT TOUCH — bottom-radar PRIMED gating; unrelated. |
| `DNR:KILL-200DMA-RECLAIM-VETO-FLAT` | "CN handoff §6 machinery" doc pointer | DOES NOT TOUCH — US 200dma reclaim veto; "handoff" appears only as a document pointer. |
| `DNR:KILL-TREND-PERSISTENCE-PATH-FEATURE-PROFILE` | "sector/group persistence" revival clause | DOES NOT TOUCH as a construction — trailing path-shape features against forward drawdown are closed; its revival clause anticipates exactly a fresh prereg, and V1 is pair-level with different unit, form and target. |
| `DNR:HOLD-PSS-CR1-CHALLENGE` | "sector-pullback" | DOES NOT TOUCH — name-level prospective charters. |
| `DNR:HOLD-IGNITION-SURFACES` | "single-sector bids" | DOES NOT TOUCH — V1 opens no user-facing surface; T10 writes one research document. |
| `DNR:KILL-OPTIONS-CONTEXT-AUDIT-OWNER-EVICTION` | "Ledger rotation/sharding" | DOES NOT TOUCH — "rotation" there is ledger sharding; V1 touches no options-context audit ledger. |
| `DNR:KILL-PARALLEL-KNOWLEDGE-BASE` | path fragment `agentos/handoffs` | DOES NOT TOUCH — string-level match only (and the row is OVERRULED 2026-08-12 regardless); V1 creates no knowledge store. |
| `LAW-REVIEWED-MANIFEST-CENSUS` | "handoff §2.4/2.5" doc pointer | DOES NOT TOUCH — estimator law about manifest censuses; string-level match only. |
| `DNR:KILL-RS-DISPERSION-GATES` | found by inspection (abbreviation "rs" is not matched by the grep pattern) | DOES NOT TOUCH — member-level relative-strength dispersion gates; V1's arms are pair-ratio level with no member dispersion gating. |

---

## §10 Rights and source status (D10)

- `data/yahoo/*.parquet` are existing committed product inputs used here for INTERNAL
  RESEARCH ONLY; results are aggregate statistics; no raw price redistribution; the
  source is not independently qualified for external claims — any external or
  user-facing use of a result requires source-owner qualification first.
- **Status line:** `RIGHTS: INTERNAL_RESEARCH_ONLY — external claims NOT_EXECUTABLE
  pending source-owner qualification`.
- **Vintage/correction:** TR closes are vendor-adjusted and retroactively revised
  (dividends, splits); first-known dates of historical closes are unknown → P1/P2
  evidence class RECONSTRUCTED; every study records the git blob sha of each parquet it
  reads plus the code revision (immutable input identity).

---

## §11 Contamination roster (D11)

Prior studies that already INSPECTED these instruments/eras — this is why no historical
partition is untouched:

| # | Study | Era | Instruments | What it saw |
|---|---|---|---|---|
| 1 | `scripts/thematic_rotation_phase0.py` (docstring :7-26) | daily 1998-12 → today (~27y, multi-cycle) | the 9 original SPDR sector ETFs (XLK XLE XLF XLV XLY XLP XLU XLI XLB; +XLRE 2015, +XLC 2018 when present) + 15 theme baskets (~3y, hindsight-curated) | monthly top-N 12-1 rotation algorithm backtests, rank-IC, TSMOM above/below 10-mo MA, crowding/extension z |
| 2 | `scripts/defensive_rotation_phase0.py` (docstring :1-29; `OOS_START = "2015-01-01"` :52) | full history; TRAIN ≤ 2014 (in-sample) → OOS 2015+ | XLU × {XLK, SMH, QQQ}; VIX; SPY | XLU technical bottom × tech-top trigger → equity vol-shock outcomes, lift vs base rate |
| 3 | `scripts/research/sp500_nasdaq_regime_rotation_study.py` (docstring :1-22, :39-41) | 2013-2026 | SPY QQQ RSP IWM SMH HYG TLT _VIX + 11 sector ETFs | ex-post regime spans, sector scoreboards, month-of-year/election-cycle diagnostics, weekly MACD event study (regime boundaries selected ex post) |
| 4 | `research/ROTATION_COMMAND_S1_S2_PREREG.md` (§2.1 :39-46, §2.5 :73-78, RESULTS :133-176) | events 2015-01-01 → 2026-04-30 (replay 2014-11 → 2026-07) | intra-sector subsector pairs + sector ETF legs | episode census + forward-20s outcomes read 2026-07-12 (S1/S2 ACCRUE, n = 13 < 20) |
| 5 | S_MLC_1 (ORCH-SCI fact) | reconstruction 2015-01-02 → 2026-05-31, accrual ≥ 2026-07-16 | — | reconstruction/accrual programme |
| 6 | `research/ROTATION_UNIVERSE_EXTENSION_PREREG.md` (registered :33-34; cross pairs :60-70; survivorship watermark :328-330) | replay 2015-01 → ; reconstructed era 2015-01 → 2023-04 watermarked | 12 series incl. the 7 cross-sector pairs, 3 contagion pairs, 1 complex | expanded-universe event census gates; no historical hit-rate before floor |
| 7 | `DNR:KILL-TREND-PERSISTENCE-SECTOR-GROUP-PERSISTENCE` (registry L134) | formation 2022-07-06..2026-06-02, scored three times (V2, B2, C1) | 11 GICS sectors | member-level rank-linear group features vs relative-to-SPY forward 20/60 returns — C1-NULL |
| 8 | macro #9035 (ORCH-SCI fact) | October 2026 incident | — | read-only discovery material |
| 9 | July 2026 motivating episode (ORCH-SCI fact) | July 2026 | the ratio-pair registry itself is dated 2026-07-11, inside it | the episode that motivated the pair registry |

**Excluded from every confirmatory set:** the October 2026 incident window
(**2026-10-01 → freeze**) and the July 2026 window (**2026-07-01 → 2026-07-31**). The
pair registry authored 2026-07-11 may reflect awareness of the July winners — the
mitigation is that pairs are fixed by registry id (no performance-based selection,
every registered pair reported) and SUPPORTED can only come from P3 (formation from
this document's merge).

**Custody-record names found by this lane (names only):** trial-ledger families whose
rows match `rotation|leadership` in `data/trial_ledger.jsonl`:
`thematic_rotation_phase0` (the row-1 prior study's own family), `cortex`,
`pss_af1_finra_absorption_witness_prospective` (the latter two matched on config
strings, not as rotation-study families). `data/vault/seals.json` is ABSENT in this
clone (`git ls-files data/vault/` empty) — no existing seals to list; the §6 act-2 seal
for `leadership_rotation_v1/P2` will be its first rotation-family entry.

---

## §12 Invalidators (D12)

Any ONE of these voids the read; the void is reported, never repaired by editing V1:

1. A blank or ambiguous cohort field.
2. Any October 2026 outcome (or any P1/P2 outcome) reused in a confirmatory set.
3. Selecting pairs, eras, horizons or arms by past performance (past-winner selection).
4. Any rotation×cycle joint read.
5. Any read of a pair, region or universe outside §2 that is not disclosed (concealed
   expanded-universe read).
6. Any outcome-bearing commit whose parent chain does not contain this document's merge
   commit.
7. Any edit of V1 after merge (amendments are a new `..._PREREG_V2.md` with formation
   dates after its own merge).

A field that cannot be truthfully filled is reported `NOT_EXECUTABLE` with its reason —
never a filled fake value (A29; §14).

---

## §13 Per-study reporting obligations (D13)

Every T11–T14 study writes
`research/LEADERSHIP_ROTATION_STUDY_<task>_2026-10-xx.md` and reports, in this order:

1. The motivating exemplars first (October 2026 window, July 2026 window) and the
   current regime (last 63 sessions) — descriptive, labelled DEVELOPMENT.
2. Episode-level honest-N (clusters, not fires/days).
3. Whether today is in-sample (P1: yes; P2: no; P3: from merge).
4. Who is missing from the panel (the §2 list).
5. Dependence-aware uncertainty (§8).
6. Every baseline B1–B7 and A0/A2 printed beside A1 even when uninteresting.
7. Nulls and failures printed, never hidden.
8. Immutable input identities (§10).
9. The look count spent.

---

## §14 SCIENCE_PROTOCOL §3 study-record checklist (D14)

Every field named in SCIENCE_PROTOCOL §3, mapped to the section of THIS document that
binds it, or to an explicit `NOT_EXECUTABLE`/`NOT_APPLICABLE` status with reason. No
field is blank.

Source of the field list: `SCIENCE_PROTOCOL.md` §3 of the Chairman's leadership-rotation
masterplan (2026-10-13), which has no copy in this repository. The list is reproduced
verbatim so the checklist can be audited here: *hypothesis ID; old trial/kill
relationship; consumer task; group identities and effective membership; universe
inclusion/exclusion and contamination; source/use rights; first-known/vintage/correction
contract; dates and split roles; target/benchmark/currency; weighting/rebalance; allowed
features and their supports; issue/price-entry rule; outcome maturity and missingness;
model family and capacity; finite tuning grid; comparable baselines; primary and safety
endpoints; practical margins; power and independent-block assumptions;
dependence/multiplicity/look budget; confirmation custodian; and exact scripts/source
revisions.* (22 fields; 22 rows below.)

| SCIENCE_PROTOCOL §3 field | Bound by |
|---|---|
| hypothesis ID | §1 (H1/H2/H3; controls C1/C2/C3) |
| old trial/kill relationship | §9 (DNR mapping, incl. additions) + §11 (roster) |
| consumer task | §0 (consumers: T11–T14 lanes + accepting seat); early recognition of a group-level change worth investigating is the principal consumer task — no stock selection, no automatic entry |
| group identities and effective membership | §2 (7 pairs by id, roles fixed; ETF panel; constituent overlap UNMEASURED) |
| universe inclusion/exclusion and contamination | §2 (excluded pairs + reasons) + §11 (roster + excluded windows) |
| source/use rights | §10 |
| first-known/vintage/correction contract | §10 (RECONSTRUCTED class; vendor-adjusted retroactive revisions; git blob shas + code revision per study) |
| dates and split roles | §6 (P0/P1/P2/P3, embargo, formation windows) |
| target/benchmark/currency | §3 (Y_h on R_t; SPY = benchmark for B3/B4; all instruments USD-denominated NYSE-session ETF series — one currency, no mixing) |
| weighting/rebalance | `NOT_APPLICABLE` — no portfolio is formed by V1; arms are state rules on pair ratios; economic simulation (Q12) would need separate authorization |
| allowed features and their supports | §4 (information set; C3 breadth exception SOURCE_LIMITED; non-inputs list) + §3 (availability clock) |
| issue/price-entry rule | §3 (signal at close t available after close t; first permitted observation = close of t+1 = origin o) |
| outcome maturity and missingness | §3 (MATURED/IMMATURE/UNPRICEABLE/SOURCE_INVALID; never dropped from denominators) |
| model family and capacity | §4 (deterministic measurement + one interpretable hysteresis family; no neural/statistical change-point model is admitted in V1) |
| finite tuning grid | §4 (A1: exactly ONE hysteresis setting, no grid — the grid is the singleton; the §8 P0 grid is power design, not tuning) |
| comparable baselines | §4 (A0 incumbent, A2, B1–B7, C3a/C3b — matched information set) |
| primary and safety endpoints | §7 (margins; H2 safety endpoint = 20-session false-start rate vs B2) |
| practical margins | §7 (H1 ≥ 5 sessions / +0.5 / 5 pp / 25 % / 10 pp; H2 +0.50 / 5 pp; H3 +0.25) |
| power and independent-block assumptions | §8 (P0 design; honest-N common-shock clusters) |
| dependence/multiplicity/look budget | §8 (block bootstrap, seed 20261014) + §6/§7 (Holm across 6 tests; P2 = 1 look, P3 = 2 looks, α = 0.025 one-sided) |
| confirmation custodian | §0/§6 (the seat; `engine/holdout_vault.py` seal + `engine/trial_ledger.py` family budget) |
| exact scripts/source revisions | §10 (per-study git blob shas + code revision); protocol identity = this document's merge commit sha (§0) |

---

## §15 Acceptance-matrix mapping

| Case | Bound by |
|---|---|
| **A28** — the new study resembles a killed rotation×cycle/positioning/LLM construction | §9 — explicit DNR-to-hypothesis mapping BEFORE outcomes, including every row the lane's grep added; no killed construction is reopened by V1. |
| **A29** — the protocol lacks cohort dates, targets, practical margins, rights or holdout custody | §0/§2/§3/§6/§7/§10 — every field filled or explicitly `NOT_EXECUTABLE`/`NOT_APPLICABLE` (§14); no empirical outcome access before the §0 owner acts. |
| **A30** — October/July motivating winners enter an allegedly untouched confirmation set | §6 (P3 formation from merge) + §11 (roster; 2026-10-01→freeze and 2026-07-01→2026-07-31 excluded from every confirmatory set; pairs fixed by registry id) + §6 custody seal under `engine/holdout_vault.py`. |
| **A31** — an old negative return exits a trailing window while new returns are zero | §4 B6 (zero-new-return placebo; carry-entry share reported) + §7 (H2 carry share always printed) + §8 (ten synthetic falsifiers incl. rolling carry, part of P0). |
| **A32** — confirmation arrives c sessions after the original trigger | §3 (o_c = t+c+1, maturity t+1+c+h; common-origin AND policy-path comparisons, separately reported) + §7 (H2 cost-of-delay A1 at o vs o_c). |
| **A33** — candidate and baseline have different accepted dates/groups | §2 (price-basis citation proving one information set; any future mismatch is recorded, never silently tolerated) + §4 (identical information set; C3 breadth exception labelled SOURCE_LIMITED) + §6 (P3 A0-concordance check against naturally issued nightly rows, every mismatch reported). |
| **A34** — one market transition triggers many repeated notices | §5 (one-event/one-attempt matching; REPEATED/LATE/MISSES/EXPIRES accounting; quiet-period alarm rate per pair-year) + §8 (within-pair 20-session merge). |
| **A35** — a favorable supported subset excludes most unseen or ineligible events | §7 clause 3 (evaluable pair-days ≥ 80 %; all-event AND supported coverage both printed with withheld states). |
| **A36** — a method wins one era but fails the frozen recent/holdout/practical criterion | §6 (frozen partitions; P2 falsification-only; P3 prospective-only) + §7 (joint rule — all clauses must hold) + §12 (era selection is an invalidator). |
| **A37** — two legs share constituents and respond to a common factor | §4 (B4 past-only beta residual target; B3 direct-leg arm) + §7 H3 (residual-target margin; pairs sharing a leg = one cluster; overlap UNMEASURED is disclosed, never assumed zero). |
