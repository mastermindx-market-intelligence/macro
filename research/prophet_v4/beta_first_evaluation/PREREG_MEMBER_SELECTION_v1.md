# Forward pre-registration: member selection — v1

**Status: Frozen when the sidecar exists on the remote branch; governs nothing before that.**
Freeze record: sidecar `PREREG_MEMBER_SELECTION_v1.FREEZE.json` beside this file (freeze date UTC, freezing
authority, sha256 of this file, commit, seed), written by the programme CEO. Seed: 20261111.

This file changes nothing in what Prophet publishes, and nothing in the frozen beta-first-evaluation header
(`protocol_header_v1.json`, sha256 `3be32166c7be5170c5153f7c6e66af02e988e88dda52167140e7ac12f30b2ada`).

**Research only. Paper returns. No trade sizing. No product change.** No hypothesis here is a recommendation
to change Prophet's selection. Acting on any of them before the read **ends the test**, and the read is then
UNRESOLVED. Acting on a hypothesis means changing selection, filtering, ranking or the published copy in its
direction.

## Derivation disclosure (binding on every reader)

All three hypotheses below were **derived after seeing the 64-session live record**, from the independent
stock-minus-sector diagnosis of 2026-11-11, committed beside this file as
`research/prophet_v4/beta_first_evaluation/DIAGNOSIS_STOCK_MINUS_SECTOR_20261111.md`. H-3's variable was found
later still, *after* that diagnosis's own pre-declared analyses ("added after seeing results"). The deriving
record (publication dates 2026-08-10 … 2026-11-06) supplied effect sizes and the dependence structure for
planning only. It is never evidence for or against any hypothesis here. No plan published on or before the
freeze date is ever eligible.

## Registered family

**One confirmatory hypothesis: H-1**, read at two-sided α = 0.05 (Bonferroni over a family of one). H-2 and H-3
are **declared descriptive, not registered**. They are specified in full below and computed once, at H-1's read,
on the same population and under the same embargo. They never receive a SUPPORTED/REFUTED/UNRESOLVED label.
On the governing method, neither can reach useful power in the available span even at its *observed* effect
(appendix).

## Common specification

**Span and read (calendar-fixed).** The eligible publication dates are the publication dates P that fall within
the **first N = 189 NYSE sessions strictly after the freeze date**. N was chosen before any forward data by the
rule stated in the appendix. With freeze date 2026-11-11, the first eligible publication session is 2026-11-12
and the **last eligible publication session is 2027-08-16**. The **single read** is taken once the last eligible
date has matured at 21 sessions: those outcomes complete at the close of **2027-09-15**, and the read is taken
on or after that date. The span is the last date. No plan published after 2027-08-16 enters the read, and there
is no other read.

**Minimum to label.** At least **40 contributing dates** inside the span and **df ≥ 4** on the governing method.
If either fails, the result is UNRESOLVED and is reported with what was observed.

**Population (eligible plans).** Plans in the incumbent selection era whose P lies inside the span. They must be
live-published only: under the deviation-D5 rule, outage-backfilled or reconstructed plans (identified by
`origination_mode` / `backfill_disclosures.json`) are excluded. They must also not be quarantined, must have a
mapped sector SPDR, and must have a defined registered variable. Entered, filled, converted, live and expired
plans are all eligible, because the ruler is policy-free.

**Clock.** P = the first NYSE session strictly after `price_basis_date` and at or after `recorded_at` (the
frozen protocol's publication clock). Signal session t = the session before P. Characteristics use adjusted
closes through t only.

**Ruler (outcome).** `engine.grading.forward_metrics` semantics: fill at the next own-calendar bar after t
(the close of P); gross forward return to fill + H bars; matured outcomes only. Gross is primary. Net is
secondary: 10 bp per side for the stock and for each equal-weight member leg, 3 bp per side for the ETF.

**Yardsticks (both, always, side by side).**
1. **Governing: equal-weight same-sector members.** The equal-weight mean forward return, on the same ruler and
   horizon, of the point-in-time eligible members of the plan's sector on the same signal session. It is computed
   exactly as `event_study.member_benchmark` in
   `engine/prophet_beta_evaluation.py::member_benchmark_event_study` / `member_universe` at Macro commit
   `eebd40b295`. Eligible members are active S&P 1500 members at t with a sector label, at least 126 valid
   closes, a raw close of at least $5 at t, and a matured outcome. Names published on P are excluded.
2. **Secondary: the plan's own cap-weighted sector SPDR** (the existing event-study yardstick).
Outcome y = stock − yardstick.

**Estimator (all three).** Date-fixed-effects slope:
β = Σ_P Σ_i (x_iP − x̄_P) · y_iP / Σ_P Σ_i (x_iP − x̄_P)²,
over eligible plans i on publication date P, where x̄_P is the date mean of x. Dates on which x does not vary
contribute nothing. β is expressed in percentage points of outcome per unit of x.

**Contributing date.** An eligible publication date with at least 2 eligible matured plans and non-zero
variation in x.

**Governing uncertainty.** The score of date P is z_P = Σ_i (x_iP − x̄_P)(y_iP − β(x_iP − x̄_P)).
Var(β) = [Σ_P Σ_P' z_P z_P' · 1{|P − P'| < H sessions}] / (Σ Sxx)², floored at the independent-dates value
Σ z_P² / (Σ Sxx)². This is Hansen–Hodrick with a rectangular kernel to lag H − 1, on the session calendar.
Reference distribution: Student t with df = ⌊S / H⌋ − 1, where S = (sessions from the first to the last
contributing date) + H. The two-sided p-value and the 95% interval come from it. The date-cluster bootstrap
(B = 10,000 over publication dates, seed 20261111) is **always reported beside it, labelled "optimistic: ignores
shared forward paths"**, and is never used for a label.

**Outcome labels (exactly three; H-1 only).**
- **SUPPORTED**: at the primary horizon, the point estimate is in the stated direction on **both** yardsticks,
  **and** the governing (equal-weight member) two-sided p-value is below 0.05, **and** the minimum to label is met.
- **REFUTED**: the governing point estimate at the primary horizon is zero or of the wrong sign, and the minimum
  to label is met.
- **UNRESOLVED**: everything else. This includes:
  - a governing estimate in the stated direction that misses α;
  - yardstick sign disagreement;
  - failing the minimum to label;
  - a material selection change without enough pre-change data (see below);
  - a breach of the embargo;
  - a test ended by action taken on the hypothesis.

A REFUTED label means the effect did not appear even in sign. It does not mean the effect is proven to be zero.

**One confirmatory read; embargo.** H-1 is read once, at the read date above. **Before that read, no one
computes, for any purpose, the split of eligible plans' outcomes by any of the three registered variables.**
That covers any slope, half or tercile split, group mean, chart, dashboard or "quick look", on any yardstick or
horizon. The embargo applies equally to H-2 and H-3. Concretely, any re-run of the beta-first evaluation, or of
any page, that includes post-freeze plans must suppress its off-index split (deviation D8) and must not compute
any split by ext20 or by 63-session strength.

The beta-first evaluation's published window is fixed (last close 2026-11-06, the deriving record), so its
existing off-index block is not a breach. Any future extension of that window past the freeze date is covered by
this embargo.

The pooled stock − yardstick mean of all eligible plans is **not** embargoed. Computing the variables
themselves, without outcomes, is permitted for counting and data checks. A breach makes the read UNRESOLVED and
is reported as such.

**Selection drift.** Each eligible plan records the selection identity it was published under:
- `selection_era`, `entry_basis.era`, `entry_zone.era`, `entry_zone.leader_pullback.construction_era` and
  `early_turn.admission_era`;
- the per-plan `source_origin.source_binding.selection_receipt`, which hashes the selection *output*, not the
  code.

No plan field identifies the selection *code*. A change is **material** if either:
(i) the recorded era tuple changes; or
(ii) a merged change to the selection modules (`engine/prophet_bridge.py`, `engine/us_board_rank.py`,
`engine/us_early_turn.py`, `engine/us_leader_pullback.py`, `engine/us_turn_watch.py`, and their configuration)
changes the selected set when the new selection is replayed on the last archived pre-change board snapshot
(`data/prophet/origination_sources/<sha256>.json.gz`).

If a material change occurs inside the span, the read is taken on the pre-change plans only, and only if they
meet the minimum to label. Otherwise the result is UNRESOLVED. The selection change log is reported at the read.
A `selection_code_sha` field on each plan is requested from the publishing owner; until it exists, the replay
rule governs.

---

## H-1 (REGISTERED). Short-term extension at publication

**Sentence.** *Among eligible plans published on the same date, plans on stocks more extended above their own
20-session average, relative to their sector's members, trail their equal-weight sector members by more over
the next 21 sessions.*

- **Variable x.** The percentile rank of e = close_t / mean(close over the 20 sessions ending at t) − 1.
  - The rank is taken among the eligible members of the plan's sector at t, as defined by the governing
    yardstick, with the plan's own stock removed if it is a member.
  - x = (number of members with lower e + ½ × number tied) / number of members, so x runs from 0 to 1.
  - Off-index stocks are ranked against the members in the same way.
- **Direction.** β < 0.
- **Primary horizon.** 21 sessions. Secondary horizons (descriptive): 42 and 10.
- **Read.** Single read on the span above (N = 189 sessions, last eligible publication 2027-08-16, outcomes
  complete at the close of 2027-09-15).
- **Reported beside the label.**
  - both yardsticks, gross and net;
  - the governing interval and the date-cluster interval;
  - the top-half minus bottom-half difference of means (descriptive; about 24% of plans fall in the bottom half);
  - the counts of eligible plans and contributing dates, and df;
  - the selection change log.
- **Context from the deriving record (never evidence).** β = −7.10 pp on the governing yardstick (−6.57 pp
  against the sector ETF): a plan at the top of its sector's extension ranking trailed its sector members by about
  7 pp more than one at the bottom. The date-cluster SE was 2.12 pp (optimistic). On the governing method, over
  the deriving record's own span, df = 1 and the two-sided p = 0.18. **The deriving record does not itself
  establish H-1.**

## H-2 (DECLARED DESCRIPTIVE — not registered). Medium-term relative strength within sector

**Sentence.** *Among eligible plans published on the same date, plans on stocks that were stronger over the
prior 63 sessions relative to their sector's members do better against their equal-weight sector members over
the next 42 sessions.*

- **Variable x.** The percentile rank, among the same eligible same-sector members at t, of the 63-session total
  return through t. This is identical to the rank of the 63-session return minus the sector ETF's.
- **Direction.** β > 0.
- **Horizon.** 42 sessions; secondary 21.
- **When and how computed.** Once, at H-1's read, on plans in the span whose 42-session outcome has matured by
  the read date. It is reported with both yardsticks and both intervals, and receives **no label**.
- **Why not registered.** Governing-method power is too low even at the observed effect (+9.18 pp). A record a
  few hundred sessions long holds only a handful of independent 42-session paths.

## H-3 (DECLARED DESCRIPTIVE — not registered). Off-index names

**Sentence.** *Among eligible plans published on the same date, plans on stocks that are not S&P 1500 members at
the signal session trail their equal-weight sector members by more over the next 21 sessions than plans on
member stocks.*

- **Variable x.** x = 1 if the stock is not an active S&P 500/400/600 member at t, else 0.
- **Direction.** β < 0.
- **Horizon.** 21 sessions; secondary 42.
- **Extra report.** Also report stock − SPY for the off-index group, since these names have no true sector
  yardstick.
- **Membership source.** Start from `data/breadth/sp1500_pit_membership.parquet`, which records no change after
  2026-06-02. Roll it forward with `data/sp_index_changes/changes.parquet`, the S&P Dow Jones press-release feed
  collected by `collectors/sp_index_changes.py`: apply each addition or deletion on its `effective_date` if its
  `_seen` timestamp is at or before the close of t.
- **Known gap.** The feed's first announcement is 2026-06-08, so the June-2026 quarterly rebalance (announced
  around 2026-06-05, effective around 2026-06-22) is missing. The evaluation owner reconciles that gap against an
  authoritative constituent list before the first eligible plan matures. If it is not reconciled, H-3 is reported
  as "membership unverified".
- **Feed completeness.** The feed is an accumulated rolling RSS, so each quarterly rebalance announcement must be
  present. A missing one is a data gap and is reported at the read.
- **When computed.** Once, at H-1's read, under the same embargo. **No label.**
- **Why not registered.** Governing-method power is about a coin flip even at the observed effect (−7.91 pp).
  Only about half of all dates carry an off-index plan, and the variable rests on the repaired source above.

---

## Appendix A — choice of span N (pre-declared rule, applied before any forward data)

**Rule (programme CEO).** N is the smallest span in {126, 189, 252} sessions whose H-1 power at the observed
effect is at least 0.80 at **both** cadences: one publication date per session, and the deriving record's 0.47
dates per session. If no span qualifies, N = 252.

**Procedure.** Monte Carlo of the **registered** procedure: H-1, α = 0.05, the Hansen–Hodrick variance with
lag H − 1 and the t reference on ⌊S/H⌋ − 1 df, 20,000 draws, seed 20261111. The dependence model comes from
Appendix B.

| Span N (sessions) | Cadence | Contributing dates | df | Power @ observed (−7.10 pp) | Power @ half (−3.55 pp) | Size (nominal .05) |
|---|---|---|---|---|---|---|
| 126 | 1 / session | 126 | 5 | 0.82 | 0.36 | 0.037 |
| 126 | 0.47 / session | 59 | 5 | **0.70** | 0.25 | 0.024 |
| **189** | 1 / session | 189 | 8 | **0.95** | 0.49 | 0.039 |
| **189** | 0.47 / session | 89 | 8 | **0.88** | 0.38 | 0.032 |
| 252 | 1 / session | 252 | 11 | 0.99 | 0.59 | 0.039 |
| 252 | 0.47 / session | 118 | 11 | 0.96 | 0.48 | 0.032 |

126 fails the rule at the 0.47 cadence (0.70). **189 qualifies at both cadences, so N = 189.** Both cadences
also clear the minimum to label (89 or more contributing dates; df 8). Calendar, with NYSE holidays from the
published 2026–2027 schedule:

| | Date |
|---|---|
| First eligible publication session | 2026-11-12 |
| Last eligible publication session (189th) | 2027-08-16 |
| Last outcomes complete (21 sessions later) / read | close of 2027-09-15 |

Even at N = 189, H-1 has 0.38–0.49 power at half the observed effect. **It can detect an effect near the size
seen in the deriving record, not one half that size.** Under the true half effect, the most likely outcome is a
non-significant estimate in the right direction (UNRESOLVED).

## Appendix B — dependence model and choice of governing method

**Measuring the dependence.** Each date's slope is decomposed into daily pieces g(P, s) over its H forward
sessions.
- γ0 = Var g, the variance per day.
- γc = Cov(g(P, s), g(P', s)) for different dates sharing day s, the shared forward path.
- The common share γc/γ0 was 0.12 for H-1, 0.11 for H-2 and 0.20 for H-3, measured on the deriving record from
  1,872 / 3,242 / 426 overlapping (date, date, day) triples.
- Planning assumes future dates carry the deriving record's plans per date (H-1: 18.8).

**Choosing the method.** Size of candidate methods at nominal α .025, with 126 dates and the common share at 1–3×
the measured value:

| Method | Size |
|---|---|
| Date-cluster bootstrap | 0.12–0.57 |
| Block bootstrap, block length H | 0.06–0.27 |
| Block bootstrap, block length 2H | 0.09–0.37 |
| Hansen–Hodrick, normal reference | 0.06–0.28 |
| **Hansen–Hodrick, t on ⌊S/H⌋ − 1 df** | **0.01–0.06** |

The registered method is the only candidate that holds size near nominal. The draft's default, a block bootstrap
with block length H, was optimistic by construction at this sample size. With few independent H-windows, any
estimate of the variance is itself noisy, and only the t reference on the number of windows accounts for that.

**H-2 and H-3 at the original 126-date planning point.**
- H-2: power 0.10 at the observed effect at one date per session (α .0167); 0.65 at the 0.47 cadence.
- H-3: 0.44–0.53 at the observed effect at one date per session; 0.74–0.79 at the 0.47 cadence. About half of all
  dates contribute.

At the observed effect neither reaches 0.80 power at both cadences, which the rule above requires of H-1. They are
descriptive for that reason.
