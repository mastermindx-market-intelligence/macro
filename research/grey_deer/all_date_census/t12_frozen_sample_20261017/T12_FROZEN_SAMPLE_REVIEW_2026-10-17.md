# Independent review of the frozen T12 sample — 2026-10-17

**Disposition: accept the sample identity and retain the construction result unchanged. Confirmatory support is not established; T13 fitting remains unadmitted.** The observed shortfalls are a substantive limitation of this frozen design, not a reason to select a new seed, shorten windows, relax exclusions or discard inconvenient episodes.

## Evidence and review scope

Reviewed the existing T12 specification and original builder/Stage1 sources, then independently recomputed serialization, counts and interval properties from `sample.json`. No prices, labels or hypotheses were recomputed. No sampler, source import, collector, feature join, fit or trial was executed.

- Sample: `../research_notes/all_date_census/t12_frozen_sample_20261017/sample.json`.
- Exact canonical bytes: 6,359; no trailing newline; equal to `json.dumps(sample, sort_keys=True).encode('utf-8')`.
- Independently verified sample SHA256: `944e0054b724aef775a5073ee8a1537779b464454a304acf4a4b396cd818a583`.
- Receipt SHA256: `ad8a1f5fe92fb12690a25794f917619a2e113baaf9a07fc3f446207020340d4f`.
- Sample: SPY, 1,321 sessions, 2021-07-06–2026-10-07, seed `20261013`, horizons 5/10/21.
- Close-series identity: `60f0d81c686fce6e03ace59c9549d9cd28713b10973b2d2711fc465740fd0bc8`; separate from the admitted RAW OHLCV hash `c686f0bc683f3109c1be5431cab99661734f2481fc98e8479320e285507be6fb`.

The receipt records one original builder call, zero fits/trial writes, original pure AST isolation, and pinned `lib.observed_moves` source. The parent separately established that observed-moves source matched original T12 merge #9208. This closes the earlier transitive-source qualification for that isolated execution path. It does not assert that importing every unrelated Stage1 module is side-effect-free.

## Support actually obtained

| Horizon | Event origins | Episodes | Controls requested | Controls placed | Shortfall | Episodes with any control | Episodes with all 3 controls | Month-matched controls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 sessions | 32 | 6 | 18 | 10 | 8 | 4 | 3 | 4 |
| 10 sessions | 99 | 7 | 21 | 3 | 18 | 2 | 0 | 1 |
| 21 sessions | 238 | 8 | 24 | 1 | 23 | 1 | 0 | 1 |

All recorded shortfalls and per-episode counts reconcile. Every emitted control has its associated episode's clipped length, stays in bounds, respects the 63-session episode buffer and avoids other controls within that horizon. Episode windows do not overlap within a horizon. Month-match flags agree with the emitted starting months. These checks establish structural consistency; they do not independently replay random draws or labels.

Only four 5-session episodes and two 10-session episodes have even one control; all of those event episodes are in 2022. Later episodes are not represented by matched controls. At 21 sessions, the sole matched episode is September 2021. This is not broad temporal support for the intended three-controls-per-episode comparison.

The 6/7/8 episode counts are also below Stage1's existing ten-episode support floor. T12 itself defines no inferential gate, so that comparison does not silently impose Stage1's whole validation policy on T13. A T13 support rule and inference design still need an explicit freeze. No independent-episode count or numerical power calculation is established here.

## Immature and pre-warmup origins

| Control | Window indices | Length | Immature origins at its horizon | Origins before index 63 |
|---|---|---:|---:|---:|
| `h5-e002-c000` | 1265–1319 | 55 | 4 | 0 |
| `h5-e003-c000` | 5–31 | 27 | 0 | 27 |
| `h10-e002-c001` | 0–39 | 40 | 0 | 40 |
| `h21-e000-c000` | 1274–1319 | 46 | 20 | 0 |

These independently computed intersections agree with the receipt. At 21 sessions, 20 of the sole control's 46 origins lack mature labels at the frozen cutoff. They cannot be counted as confirmed negatives. The table identifies dates within windows, not an already frozen study-origin projection.

The only matched 21-session event episode, `h21-e000`, spans indices 20–65. Its first and last event origins are indices 41 and 44 under the original 21-session padding, and it contains four event origins: all four precede index 63. If a downstream study adopts the Stage1 63-session warm-up cut, that sole matched episode has no eligible event origin. Two controls in the table would likewise lose their entire origin content under that cut. Preserve the sample; report this projected attrition separately instead of changing its contents.

## Overlap and independence

All six 5-session episode windows are contained within 10- and 21-session episode windows; all seven 10-session episode windows are contained within the eight 21-session windows. The 21 horizon-specific episode records therefore do not represent 21 independent episodes. The union yields eight windows as bookkeeping, not a verified independent sample size.

Controls also overlap across horizons: four 5/10 control pairs, one 5/21 pair and one 10/21 pair. The entire 46-session 21-day control sits inside the long 5-day control. Shorter-horizon control windows overlap longer-horizon event windows in four 5/10 pairs, eight 5/21 pairs and two 10/21 pairs. This is compatible with horizon-specific labels; it prevents treating these controls as generic benign periods or pooling horizons as independent replications.

Retrospective event/control proportions are not population event rates. Month-of-year and window-length matching do not establish comparable macro regimes, funding conditions or point-in-time information sets. A leave-one-episode-out analysis can still train on later history unless chronological restrictions are specified separately.

## Next legitimate research step

1. Keep the exact sample and this failure-of-support finding in the existing programme evidence. Record sample identity as accepted and the original intended matched confirmatory design as unsupported by the obtained allocation. Do not repair or resample it after observing these results.
2. Freeze a **sample-use and feasibility contract** before feature joins or fitting: scored origin within each window, feature warm-up and release availability, label maturity, treatment of partial/missing controls, horizon dependence, chronological folds and embargo, support minimums, and exact counted fits. Retain the original sample and report the projected inclusion/exclusion map separately.
3. Assess whether that contract has enough common support using metadata and frozen window identities. If it does not, close the existing confirmatory lane as unsupported. A revised design or expanded history must be declared as a new development preregistration that discloses this observed failure; it is not an untouched confirmatory holdout or a rerun under the old freeze.
4. Retain the current source-purpose and policy boundaries. Genuine prospective issuance or a separately declared future evaluation can build new evidence; this sample identity alone cannot validate warnings, probabilities, lead time, re-entry or allocation policy.

No additional trial has been consumed by this review. No files beyond this review were changed.
