# CPU leadership recovery — RS anti-chase threshold preregistration

Status: PRE-OUTCOME / ZERO PRODUCTION AUTHORITY
Carrier: macro PR #7572 / sol/us-prophet-candidate-visibility-20260921
Chairman outcome: detect concentrated CPU/compute leadership early without a CPU whitelist,
while preserving genuine extension and entry risk controls.

## Question

The live theme stack uses two distinct own-history relative-strength percentile cutoffs:
- `basket_score.clean_entry`: `rs_pctile < 0.75`;
- US dominant recommendation extension veto: `rs_pctile < 0.85`.

The September-18 audit shows AI Semiconductors, Memory/Storage and AI Infrastructure are
Enter/Accumulate themes whose clean-entry flag is blocked solely by the 0.75 RS veto despite
adequate quality. This observation motivates the study but is not calibration data.
## Frozen construction

Use the existing ~27-year US SPDR-sector proxy from `scripts.calibrate_baskets`.
Re-derive `rs_pctile`, acceleration and market breadth point-in-time from the same price panel.

A row is **otherwise-clean** when the incumbent clean-entry function would fire if only the
RS cutoff were relaxed to 1.01. All other incumbent conditions remain unchanged:
acceleration, RSI room, breadth, 200d trend, shallow pullback, and the breaking-tape veto.

Create distinct episodes from daily blocked-state onsets, one episode per contiguous blocked run.
No repeated daily rows inside an episode count as independent observations.

Frozen cohorts:
1. `incremental_075_085`: otherwise-clean and `0.75 <= rs_pctile < 0.85`.
2. `blocked_both_ge085`: otherwise-clean and `rs_pctile >= 0.85`.
3. `allowed_lt075`: otherwise-clean and `rs_pctile < 0.75` (context/control, not threshold-tuned).
## Frozen outcomes

At each episode onset report:
- distinct episode count and distinct sector count;
- forward absolute return at 5d / 10d / 21d;
- forward relative return versus SPY at 5d / 10d / 21d;
- forward 21d maximum adverse excursion / drawdown from the decision close;
- probability of 21d drawdown worse than the existing house `DD_RISK=-8%`;
- continuation-failure rate `fwd_rel_21d <= 0`.

For blocked cohorts also report threshold release within 21 sessions:
- first later session that is otherwise-clean and below that cohort's blocking threshold;
- release rate, median wait, and onset-to-release absolute/relative return.
No release is fabricated when the other clean-entry evidence has deteriorated.
## Decision rules

This study cannot directly change production thresholds.

The 0.75 cutoff is **not supported as an anti-chase improvement** if the incremental
`[0.75,0.85)` cohort has no materially worse 21d MAE / >8% drawdown risk than the
`<0.75` control while showing equal-or-better continuation outcomes or substantial missed return.

The 0.75 cutoff is **supported as protective** if the incremental cohort has clearly worse
adverse-excursion / drawdown-risk outcomes, even if some upside is forfeited.

The 0.85 cutoff is evaluated separately on the `>=0.85` cohort; no conclusion about 0.75
may be borrowed from 0.85 behavior.

No single September-2026 CPU/semiconductor episode can decide promotion. Report episode counts,
era coverage, and whether the current motivating tape is represented by the studied construction.
## Guardrails / falsifiers

- No CPU, semiconductor, ticker or current-winner whitelist in the historical study.
- No current/premarket prices enter historical features.
- No threshold search beyond the already-live 0.75 and 0.85 values.
- No optimizing a third threshold after seeing outcomes.
- No daily-row pseudo-N; episode onset is the inferential unit.
- Missing price/breadth/RS data stays unavailable.
- No production rank, entry, recommendation, sizing or trade mutation.
- The prior generic continuation-label null remains binding; this tests anti-chase selectivity,
  not a new claim that theme momentum predicts returns.

Acceptance exemplar after the frozen study: report where the September-18 AI Semiconductors,
Memory/Storage and AI Infrastructure observations fall relative to the two live cutoffs, without
using them to change the study construction.
