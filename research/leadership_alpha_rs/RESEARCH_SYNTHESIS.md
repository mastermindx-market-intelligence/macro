# Leadership Lab — research synthesis and implementation implications

Date: 2026-10-05

Purpose: convert the external literature into falsifiable Mastermind research requirements for the recovered Alpha / RS / group-leadership program. Literature establishes hypotheses and failure modes; it does not validate the recovered formulas, current data estate, thresholds, or Prophet admission.

## 1. Price leadership and residual momentum are credible research families, not proven Mastermind alpha

Blitz, Huij & Martens, **Residual Momentum**, Journal of Empirical Finance 18 (2011), DOI 10.1016/j.jempfin.2011.01.003, report stronger risk-adjusted results for momentum formed on residual returns than for conventional total-return momentum in their tested sample.

Mastermind implication:
- preserve the recovered residual-Alpha family;
- compare it against plain market-relative, sector-relative and group-relative strength on the same eligible population and entry convention;
- do not cite the paper as validation of engine/residual_alpha.py: the recovered implementation's exact residualization, lookback and data semantics are different and must earn their own result.

## 2. Price momentum and fundamental/earnings momentum must remain separate axes

Chan, Jegadeesh & Lakonishok, **Momentum Strategies**, NBER W5375 / Journal of Finance (1996), report that past returns and past earnings surprises each predict return drift after controlling for the other in their setting.

Novy-Marx, **Fundamentally, Momentum is Fundamental Momentum**, NBER W20984 (2015), reaches a stronger conclusion in a different design: earnings momentum explains much of price-momentum strategy performance.

These results are not interchangeable; they make independence an empirical question.

Mastermind implication:
- Alpha/RS strength and earnings/revision strength are not independent confirmation by assumption;
- report the raw axes first;
- evaluate incremental information with nested/common-population tests;
- no "two bullish signals = double confidence" arithmetic;
- a continuation model must show whether price leadership contributes after earnings/revision evidence, and vice versa.

## 3. Group, industry and peer leadership is part of the mechanism

The industry-momentum literature associated with Moskowitz & Grinblatt (1999) reports that industry effects explain a substantial portion of individual-stock momentum in their sample. Subsequent work continues to treat industry momentum as an important distinct return-continuation effect.

Baker, Ni, Saadi & Zhu, **Competitive earnings news and post-earnings announcement drift**, International Review of Financial Analysis 63 (2019), DOI 10.1016/j.irfa.2017.02.002, reports intra-industry information transfer around peer earnings announcements.

Mastermind implication:
- the hierarchy market -> sector -> subsector -> theme/subtheme -> issuer-excluded peers -> security is economically meaningful;
- remove the focal economic issuer before calling peer strength independent;
- a leader moving with a healthy group is different from a single-name impulse, but neither state gets trading authority automatically;
- peer earnings/news can be a relevant catalyst for the focal name, but must retain its own event/source clock.

## 4. Earnings surprise, revisions and price reaction are causally entangled

Analyst-responsiveness research in Journal of Accounting & Economics 46 (2008), DOI 10.1016/j.jacceco.2008.04.004, finds that prompt analyst forecast revisions after earnings are associated with more price reaction in the event window and less subsequent drift.

Clement, Hales & Xue, Journal of Accounting & Economics 51 (2011), DOI 10.1016/j.jacceco.2010.11.001, find that analysts use stock returns and other analysts' revisions when updating earnings forecasts and that response varies with signal informativeness.

Mastermind implication:
- a post-earnings analyst revision may reflect the same underlying event and/or price move rather than independent new evidence;
- store source/availability clocks and contributor identity;
- distinguish issuer guidance, consensus change, within-analyst revision, panel change and price reaction;
- deduplicate/dependence-group these before any later probabilistic model;
- revision_positive is context, not a catalyst probability.

## 5. Analyst-upgrade momentum is not a timeless invariant

The Journal of Financial Economics paper **Can analysts pick stocks for the long-run?** (2016), DOI 10.1016/j.jfineco.2015.09.004, reports that post-recommendation-revision drift is not significantly different from zero in its 2003–2010 high-frequency-era sample.

Mastermind implication:
- recommendation/revision effects require era-aware prospective validation;
- do not assign a permanent positive weight because an older paper or legacy backtest found drift;
- distinguish earnings-estimate revisions from recommendation changes.

## 6. Earnings quality matters for rerating durability

Chan, Chan, Jegadeesh & Lakonishok, **Earnings Quality and Stock Returns**, NBER W8308 / Journal of Business (2006), find that earnings increases accompanied by high accruals are associated with weaker subsequent returns in their sample.

Mastermind implication:
- "earnings up" is not enough for a durable rerating dossier;
- pair reported earnings/revenue/margin improvement with cash conversion, accrual quality and balance-sheet evidence when owner coverage permits;
- the Earnings adapter should surface explicit missing cash/profitability evidence instead of neutral-filling it.

## 7. Momentum risk is state-dependent

Daniel & Moskowitz, **Momentum Crashes**, NBER W20439 / Journal of Financial Economics 122 (2016), document severe momentum losses concentrated in panic/high-volatility states and market rebounds.

This is primarily evidence about momentum portfolios including a loser short leg; it is not a direct estimate of the loss distribution for Mastermind's long-only leader sleeve.

Mastermind implication:
- stress-test long-only leaders separately through panic/rebound regimes;
- never copy long-short crash magnitudes into long-only risk labels;
- current macro/regime and extension state remain separate risk/context inputs rather than retroactively redefining Alpha.

## 8. Design hypotheses to preregister

The program should eventually preregister these separately:

1. **Residual Alpha incrementalism** — does residual Alpha add forward information after plain RS, group RS and earnings momentum?
2. **Group confirmation** — within fixed PIT membership, does leave-issuer-out group leadership improve continuation versus same-strength names in weak groups?
3. **Fundamental confirmation** — do source-qualified earnings/guidance/revision trajectories improve continuation among high Alpha/RS names?
4. **Single-name leadership** — when group breadth is weak, which issuer-specific mechanisms distinguish real idiosyncratic leaders from temporary impulses?
5. **Emergence** — do accepted owner-defined sequential leadership transitions identify future leaders earlier than level-only screens?
6. **Rerating durability** — separately test EPS/revenue/margin growth, estimate revision, multiple expansion/compression, cash quality, and price recognition.
7. **Catalyst propagation** — test issuer and peer/subtheme event information only from exact source/event clocks; absence is not inferred from missing coverage.
8. **Regime interaction** — test leadership continuation through ordinary, panic, rebound and high-volatility regimes without post-hoc threshold changes.

Each test keeps selection quality, entry timing and outcome labeling separate.

## 9. Current Mastermind owner reality changes what can ship now

At the current program checkpoint:

- recovered Alpha/RS, current Radar/ThemeState context, current Prophet native episode IDs, leave-issuer-out peer observations and descriptive group leadership are implemented in the bounded Lab;
- the accepted Earnings dossier contract can be consumed when the exact same Prophet episode has an owner-produced detail; cross-episode ticker joins are refused;
- Live Entry Radar's canonical ledger is WAITING_FOR_LIVE_SOURCE, so no per-name catalyst likelihood or negative "no catalyst" inference is lawful;
- SRC-A1 remains BUILT_NOT_PROVEN, with EXP-1 NOT_BUILT; therefore the Lab must not manufacture consensus trajectories or expectation-based rerating probabilities from the raw parquet store;
- Research Vault F6 subject identity is merged, but F5 exact full-text/segment work and F3 corpus repair remain unfinished, and F6 still lacks its first production consumer proof. Broad institutional-paper synthesis is therefore not yet an accepted Lab input.

The correct current product is an evidence-separating research surface with typed missingness—not a false-confidence scoring dashboard.

## 10. Promotion ruler

No predictive field should be named "probability", "confidence", "continuation likelihood", "catalyst likelihood", or "rerating likelihood" until:

- target population and target outcome are frozen;
- all owner identities and knowledge clocks are qualified;
- dependence/dedup rules are frozen;
- train/calibration/forward boundaries are frozen;
- calibration is measured out of sample;
- coverage/missingness and failed leaders remain in the denominator;
- existing Eval/Conditional Fusion owner accepts the result;
- product authority stays separate from the research model's statistical output.

Until then, the Lab uses direct measurements, owner states, evidence, counterevidence, and explicit UNAVAILABLE / NOT_CONNECTED states.
