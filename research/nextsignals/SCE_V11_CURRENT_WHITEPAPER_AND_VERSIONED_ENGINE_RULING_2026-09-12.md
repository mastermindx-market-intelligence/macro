# SCE V11 — current whitepaper, versioned engines and identification ruling

Status: `LIMITED_IDENTIFICATION_CURRENT_VERSION`. The tested August auction-profile family remains `NO_EXIT_RULE_VALIDATED`. Records only; no trading, portfolio, source-runtime, model-ranking or deployment authority.

Procedure pin: protected Mastermind `57a2672af5b9dcea282e4bae01d1a0b9d10bb1cd`,
Sol Skillpack 1.0.1, bootstrap major 1. Same records carrier and PR #7009.
Earlier V4–V8 observations remain historical evidence unless this ruling narrows their use.

## 1. Why V11 changes the research target

The bounded V10/V11 auction-profile reconstruction did not validate a deterministic exit
rule from the tested August profile family. Preserve that negative result as
`NO_EXIT_RULE_VALIDATED` **for that family and versioned evidence only**. It must not be
promoted into a claim that the current September SCE method lacks an exit rule.

A new current primary-source packet materially changes the identification problem. On
September 10 the publisher described a new 25-page Systematic Core Portfolio whitepaper
and posted page 3. On September 11–12 the publisher posted current Systematic Core
product views. These sources expose a more recent strategy architecture than the June,
July and August disclosures used during earlier reconstruction.

Current source locators:
- https://x.com/TailThatWagsDog/status/2098105790175363512
- https://x.com/TailThatWagsDog/status/2098398253284753541
- https://x.com/TailThatWagsDog/status/2098901921817895284
- https://x.com/TailThatWagsDog/status/2097428696067965372

## 2. Current September architecture — observed, not inferred

The September 10 whitepaper page identifies the current SCE as a long-only systematic
strategy aimed at compounding retirement capital while limiting sequence-of-returns harm.
It says the investable set is SPY, XLE and GLD plus short-duration Treasury ETF SHY, and
that allocation is controlled by **two independent engines** described later in the
whitepaper. The same page reports full-window 2004–2026 performance, but those numbers
are publisher claims until independently reconstructed with the declared clocks, costs,
benchmark and rule version.

The September 11 product index names the architecture more concretely as **Trend Base
with Dislocation Overlay: SPY, XLE, GLD**. It says the performance and position pages are
generated from one engine run and one data pull, and explicitly labels the figures as
model output rather than a brokerage record.

The September 12 position page shows a current long SPY allocation with XLE and GLD flat,
plus cash. Separate options labels sit beside the three ETF states. The September 8
publisher text states that Signal Sigma options positioning is scored beside the base
model and interpreted each day. This is evidence that options information is an input or
context layer; it is **not** evidence that current SCE portfolio holdings are option
contracts.

That distinction closes a material stale assumption in V8/V9 planning: derivative account
lifecycle support is conditional on a future admitted implementation actually using
options. It is not a current prerequisite for researching or representing the September
ETF/Treasury method.

## 3. Version boundary — do not splice old systems into the current one

Public SCE disclosures describe several materially different generations:

- June 25 described a four-sleeve SPX/IEMG/GLD/BTC-or-IBIT construction that was flat
  outside structural dislocations and identified a Donald Jones auction-market exit as
  the winner among ten tested exits.
- July 6 described a white-box system using dual-KAMA regime detection, hysteresis,
  an ATR-normalized dislocation trigger, HYG/IEI veto, GEX tilt and weighting across
  SPY/QQQ/GLD/BIL.
- July 10 showed a live state of 25% SPY / 75% BIL with QQQ and GLD flat.
- August 12 described a long index base plus defined-risk QQQ/GLD dislocation trades.
- September changes the disclosed investable set to SPY/XLE/GLD plus SHY and exposes a
  named Trend Base + Dislocation Overlay architecture.

Historical source locators:
- https://x.com/TailThatWagsDog/status/2070128419036156055
- https://x.com/TailThatWagsDog/status/2074093446659236138
- https://x.com/TailThatWagsDog/status/2075568429264785462
- https://x.com/TailThatWagsDog/status/2087483692516085964

These are useful lineage evidence, not interchangeable rule disclosures. A Jones exit,
dual-KAMA coefficient, QQQ sleeve or BIL cash proxy observed in an older generation must
not be inserted into the September method without a version-matched source. Likewise,
the V11 August-profile null rejects only the tested reconstruction family; it does not
refute a later private Section 3 rule.

## 4. Claim ledger for the current whitepaper

Treat current publisher statements as attributed claims until independently reproduced:

| Claim class | Current public claim | Mastermind state |
|---|---|---|
| Objective | retirement compounding with drawdown control | publisher claim |
| Universe | SPY, XLE, GLD, SHY | current disclosed method fact |
| Architecture | two independent engines; Trend Base + Dislocation Overlay | current disclosed method fact |
| Account | long-only, no leverage/shorting; puts permitted | publisher method claim |
| Full window | 2004–2026 | publisher evaluation-window claim |
| Terminal value | $200k to about $10.08m | unverified numeric claim |
| Annualized return | 19.7% | unverified numeric claim |
| Max drawdown | -7.9% | unverified numeric claim |
| Calmar/MAR | 2.51 versus 0.20 for S&P 500 | unverified numeric claim |
| Live model | same engine run feeds performance and position views | current product disclosure |
| Brokerage status | figures are model output, not brokerage record | current product disclosure |

The September 12 live page separately reports a roughly +23% model-book result since its
2026 inception and a materially smaller maximum drawdown than SPY over that window. Those
live-page numbers are useful version/shape constraints, not substitutes for the whitepaper's
full-history rule-to-account reconstruction.

## 5. What remains unidentified

The current primary sources do not disclose Section 3. Therefore these items remain open:

1. exact Trend Base state variable, warm-up, cash-rotation threshold, hysteresis and sizing;
2. exact Dislocation Overlay entry predicate, eligible asset selection, overlap policy and sizing;
3. exact overlay exit/invalidation rule and whether Jones auction-value logic survived into September;
4. exact role of daily options positioning — descriptive context, eligibility modifier or deterministic gate;
5. exact SHY versus cash treatment, distributions, costs, execution clock and rebalance convention;
6. exact version used for the 2004–2026 statistics and whether all disclosed current components existed for the full window.

## 6. Research ruling

Current SCE reconstruction is `PARTIAL`, not strategy-accepted and not rejected.

The September packet is strong enough to close three obsolete branches of inquiry:

- Do not keep searching the V8 integer option-inventory family as if it were the current
  portfolio ledger. Current disclosed holdings are ETFs/Treasury/cash and the product itself
  distinguishes ETF position state from options context.
- Do not promote the June Donald Jones exit into the September overlay. It is lineage evidence
  only until a current source or exact behavioral reproduction reconnects it.
- Do not tune August profile geometry to recover the current core. The current architecture
  exposes a separate Trend Base whose exact Section 3 rule has not yet been recovered.

The useful retained V6–V8 work is evidence discipline: source clocks, missingness, funded
accounting, initialization sensitivity, profile-construction ambiguity and the favorable
whole-book drawdown feasibility result. Those findings constrain any later replay; they no
longer define the current strategy's instrument ontology.

## 7. Product and intelligence implication

The existing Quant Lab `METHODS` placement remains correct. The dossier should make the
version timeline first-class and separate publisher claims, disclosed rules, inferred rules,
failed reconstructions and Mastermind-original candidates. A negative reconstruction result is
still a useful artifact.

No Prophet, Market State, Risk Radar or portfolio authority is added. If a future frozen
September-equivalent rule earns a paper mandate, admit one distinct ETF/Treasury book through
the existing portfolio lifecycle. Add option lifecycle support only if the accepted mandate
actually trades options; descriptive Signal Sigma context does not create that requirement.

The primary machine value is now a version-safe external-method dossier, not an approximate
replica assembled from incompatible generations.

## 8. Bounded current-source closure and exact continuation

The current-version source effort reviewed the September 10 whitepaper excerpt, September 11
product index, September 12 live position book, September 8 options-context disclosure and the
versioned June–August lineage sources. Direct public-site/search checks found no disclosed
Section 3 or equivalent current rule packet. The public whitepaper material available in this
wave therefore does not identify the exact Trend Base transition, Dislocation Overlay entry/exit,
or options-context authority boundary.

That is enough to stop reverse-engineering by proxy. The external replica is closed at
`LIMITED_IDENTIFICATION_CURRENT_VERSION`; the August auction-profile family separately remains
`NO_EXIT_RULE_VALIDATED`. A later genuinely new current-version methodology disclosure may reopen
identification, but old-version rules are not gap-fillers.

Highest-leverage next action is now productization of the honest research result: one Quant Lab
`METHODS` vertical slice that presents the version timeline, publisher claims, disclosed facts,
independently reproduced mechanics, failed reconstruction families and unresolved current rules.
The artifact must render limited identification as a useful result, not as pending/broken state.

Only after a future current rule becomes sufficiently frozen should the program resume a funded
ETF/Treasury rule-to-account replay with original availability, total-return data, costs,
cash/SHY treatment, corrections and an unchanged benchmark. Any Mastermind-original candidate is
a separate hypothesis and inherits none of the publisher's return, drawdown or validation claims.

## 9. Acceptance boundary

This V11 research ruling is complete when the records carrier preserves the current-version
architecture, version conflicts, the bounded `LIMITED_IDENTIFICATION_CURRENT_VERSION` conclusion
and the separately scoped `NO_EXIT_RULE_VALIDATED` August-family null, and repository validation
is green. It does not establish alpha, a recovered Section 3, a paper mandate, source recovery,
product deployment or production proof. Those remain separate gates.
