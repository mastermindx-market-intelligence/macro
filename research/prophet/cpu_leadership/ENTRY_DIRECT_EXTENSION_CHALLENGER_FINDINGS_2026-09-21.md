# CPU leadership recovery — direct extension challenger findings

Status: RESEARCH NO-GO AS GATE / DISPLAY TEXTURE PRESERVED / ZERO PRODUCTION AUTHORITY
Carrier: macro PR #7572
Preregistered source: ENTRY_DIRECT_EXTENSION_CHALLENGER_PREREG_2026-09-21.md

## Result

Frozen artifact: `evidence/direct-extension-challenger.json`
SHA-256: `b8448a6a7c3f6bac2771d7beaebd71f48ea9cebf13b2282bc0e749a9f12654f3`
Episode-set SHA-256: `055cdab72c28994111b5a307f5bc13adaeb8302d8960e837d183f8e1be0b9883`

The study reuses the incumbent `theme_extension` close-based ATR formula and its existing
`BAND_EXTENDED=1.5` boundary. All source dependencies used by the study were byte-current with
protected Macro main at the decision boundary.
Across the RS<.85 otherwise-clean population:

| Cohort | Episodes | 21d rel median | 21d DD median | P(DD < -8%) | continuation failure |
|---|---:|---:|---:|---:|---:|
| ATR extension <1.5 | 2,712 | +0.041% | -2.166% | 10.95% | 49.48% |
| ATR extension >=1.5 | 3,254 | +0.067% | -1.802% | 6.85% | 48.71% |

The descriptive table does **not** show the direct-extension boundary acting as the expected
protective veto. The ATR-extended cohort is not obviously more dangerous.
## Preregistered dependence-aware inference

Primary comparison: ATR-extended minus ATR-normal, one cohort mean per calendar month,
paired on 288 overlapping months.

- 21d relative return: +0.008%, NW p=0.951, bootstrap CI [-0.229%, +0.270%].
- 21d maximum adverse excursion: -0.195%, NW p=0.093,
  bootstrap CI [-0.411%, +0.054%].
- >8% drawdown risk: +0.11pp, NW p=0.912, CI [-1.76pp, +1.93pp].
- continuation failure: -0.07pp, NW p=0.966, CI [-3.18pp, +3.03pp].

**Ruling: NO-GO for promoting the existing 1.5-ATR extension texture to entry-gate authority.**
The only near-separation is slightly worse mean MAE for the extended cohort, but the preregistered
bootstrap interval crosses zero and neither drawdown risk nor continuation failure separates.
## Recovered .75-.85 middle band

The middle-band descriptive split is also mixed rather than a clean gate-validation result:

- ATR-normal: 337 episodes, 21d relative median +0.692%, DD-risk 11.57%, failure 39.47%.
- ATR-extended: 958 episodes, 21d relative median +0.307%, DD-risk 6.16%, failure 45.09%.

This is useful context but not a separately preregistered primary inference and must not be used to
rescue the ATR gate after its primary test failed.
## What changes in the model plan

1. Keep `engine/theme_extension` **display-only**. Do not make 1.5 ATR a gate.
2. Do not combine two unvalidated vetoes merely because they tell a plausible story.
3. The evidence-backed clean-entry challenger remains **RS<.85**, with the live RS<.75 policy
   untouched until prospective shadow accrual clears the existing promotion process.
4. Use the incumbent daily basket archive rather than a new ledger:
   `build_baskets -> data/baskets/latest.json -> archive_signals` already records clean-entry
   state and is the lawful prospective history owner.
5. Add the .85 challenger only as an all-false-authority sibling field on the existing clean-entry
   texture / slim basket snapshot when Source Continuity admits the production-source edit.
6. Keep CPU/compute leadership discovery separate from entry timing. A leader may deserve top
   research/Prophet visibility while still saying “wait for entry.”

This is a falsification result: it prevents the project from replacing one bad proxy
(RS<.75 as extension) with another unvalidated veto (ATR>=1.5) merely to fit the September winners.
