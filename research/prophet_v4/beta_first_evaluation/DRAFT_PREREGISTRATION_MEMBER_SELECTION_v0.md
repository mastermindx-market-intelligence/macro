# DRAFT — forward pre-registration: three member-selection hypotheses

**Status: DRAFT, not frozen.** Prepared 2026-11-11 by Lead D on the audit branch
(`fable/prophet-beta-evaluation-audit-20261111`) at the programme CEO's request. The
programme CEO freezes this file, not the preparing session; until frozen it governs
nothing, and if frozen its freeze date and hash become binding. It changes nothing in
what Prophet publishes and nothing in the frozen beta-first-evaluation header
(`protocol_header_v1.json`, sha256 `3be32166…2ada`).

**Mandatory derivation disclosure (applies to all three hypotheses).** All three
hypotheses were derived AFTER seeing the 64-session live record, from the independent
stock-minus-sector diagnosis of 2026-11-11 (`/tmp/prophet-eval-diagnosis/REPORT.md`)
and the audit correction it prompted. Nothing in them is a tuned rule: variables,
cuts, horizons and refutation conditions are taken from the diagnosis's observed
effect sizes and standard errors, not searched for significance, and none of them is
a recommendation to change selection. Each is a falsifiable statement for a sealed
forward record only.

## Common specification (all three hypotheses)

- **Population.** Live-published incumbent-selection-era plans (the deviation-D5 rule:
  outage-reconstructed/backfilled plans excluded by origination receipt), published on
  a publication date strictly after the freeze date of this header. No plan published
  on or before the freeze date is ever eligible, whatever its horizon.
- **Ruler.** `engine.grading.forward_metrics` next-bar fill from the session before the
  publication session P; fixed horizons in sessions; matured outcomes only. Gross of
  costs in the primary test; net of the header's per-side costs (10 bp stock, 3 bp ETF)
  reported as a secondary check.
- **Yardsticks (both, always, side by side).**
  1. The plan's own cap-weighted sector SPDR (the existing event-study yardstick), and
  2. the **equal-weight mean of point-in-time eligible same-sector members** on the same
     signal date, computed exactly as `event_study.member_benchmark` in the corrected
     artifact: point-in-time S&P 1500 members at the signal session, sector label
     present, >= 126 valid closes, raw close >= $5, matured outcome at the horizon, no
     plan published on that asset that day.
  A hypothesis is read as answered only when both yardsticks agree in sign on the
  primary horizon; disagreement is reported as such, never resolved by choosing one.
- **Uncertainty.** Date-cluster bootstrap over publication dates, B = 10,000, seed
  recorded at freeze; nearby publication dates share forward paths, so these intervals
  remain optimistic and the refutation conditions below are deliberately point-estimate
  based, not interval based.
- **Multiplicity family.** Exactly three tests: the primary horizon of H-1, H-2 and
  H-3 (as defined below). Holm correction at two-sided alpha = 0.05 across the three.
  Secondary horizons, subgroup cuts and per-yardstick variants are descriptive and are
  never counted as confirmatory.
- **Planning basis.** Detectability uses the date-cluster standard errors measured on
  the 64-session record at 80% power, two-sided alpha = 0.05, and every minimum-date
  figure below is stated at the observed effect size and at half of it (the honest
  planning number: observed effects on a selected post-hoc cut are usually inflated).
  Effects share overlap in the gap; shares are not additive.

## H-1. Short-term extension at publication

- **Variable.** `close(signal) / mean(close over the 20 sessions ending at the signal
  session) − 1`, ranked within same-sector, same-date point-in-time S&P 1500 members
  (the eligible-member universe of the common specification). The plan's own entry-zone
  depth (publication close to the entry band) may be reported as a correlated secondary
  variable; it is not the registered variable.
- **Comparison.** Picks in the top half of that rank versus picks in the bottom half.
- **Yardsticks.** Both common-specification yardsticks.
- **Primary horizon.** +21 sessions from the publication close. Secondary: +42.
- **Refutation condition.** Refuted if `top-half − bottom-half >= 0` (point estimate)
  on EITHER yardstick at the primary horizon, with at least **40 new eligible
  publication dates**. If the two yardsticks disagree in sign, the hypothesis is
  unresolved, not refuted.
- **Observed on the deriving record (context only, never evidence).** −3.5 pp
  [−5.3, −1.4] at 21 sessions, SE ≈ 1.0; roughly 70–76% of picks sat in the top half.
  Detectable with ~15 new dates at the observed size, ~57 at half.

## H-2. Medium-term relative strength within sector

- **Variable.** 63-session total return through the signal session minus the own sector
  ETF's 63-session total return, ranked within same-sector, same-date eligible members.
- **Comparison.** Picks below the sector median versus picks at or above it.
- **Yardsticks.** Both common-specification yardsticks.
- **Primary horizon.** +42 sessions. Secondary: +21.
- **Refutation condition.** Refuted if `below-median − above-median >= 0` (point
  estimate) on EITHER yardstick at the primary horizon, with at least **40 new eligible
  publication dates**; yardstick sign disagreement leaves it unresolved.
- **Observed on the deriving record (context only).** −5.0 pp at 42 sessions
  (SE ≈ 2.4), −1.4 pp at 21 (not significant). Detectable with ~26 new dates at the
  observed size, ~104 at half.

## H-3. Off-index (non-S&P 1500) names

- **Variable.** Point-in-time S&P 1500 membership of the picked stock at the signal
  session (yes/no), from the same PIT membership file and with its limits restated
  every time it is used: the file records no change after 2026-06-02, so late-window
  non-membership is uncertain in both directions.
- **Comparison.** Non-member picks versus member picks.
- **Yardsticks.** Both common-specification yardsticks — noting the member benchmark is
  the honest one here, because a cap-weighted sector fund does not contain non-members.
  Also always report `stock − SPY` for the non-member group, since these names have no
  true sector yardstick.
- **Primary horizon.** +21 sessions. Secondary: +42.
- **Refutation condition.** Refuted if `non-member − member >= 0` (point estimate) on
  the member-benchmark yardstick at the primary horizon, with at least **30 new
  non-member picks** observed (not dates; these names are ~7–10% of picks, so this
  binds slower than the date minimums above — report both counts at every look).
- **Observed on the deriving record (context only).** −8.0 pp at 21 sessions
  (SE ≈ 3.4), −15.5 pp at 42; 46 of 732 published plans were off-index, carrying about
  −0.6 pp of the 21-session mean gap and −1.5 pp of the 42-session mean gap.

## Governance

- Freeze is the programme CEO's act. On freeze, record: freeze date (UTC), freezing
  authority, file sha256, and the commit that carries it; the first eligible
  publication date is then strictly after that freeze date.
- Analysis of these hypotheses belongs to a future sealed evaluation under its own
  header; nothing in the beta-first-evaluation artifact or page is modified by this
  file, and no interim look before the minimum date/pick counts are met may be
  reported as confirmatory.
- Research only, paper returns, no trade sizing, no product change.
