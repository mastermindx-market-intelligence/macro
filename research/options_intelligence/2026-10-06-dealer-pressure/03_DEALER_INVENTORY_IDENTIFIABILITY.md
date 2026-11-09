# Dealer inventory identifiability

**Research verdict, 2026-10-06.** This is an original identification analysis, extending the October 3 contracts. It does not estimate today's positions or authorize trading. Equations below are accounting identities or explicitly proposed models. External evidence is indexed in `SOURCE_REGISTER.json`; incumbent evidence is in `02_CURRENT_STATE_NO_REDO.md`.

## 1. The answer in one sentence

Ordinary options trades, quotes, volume and unsigned open interest do not uniquely identify dealer inventory; exchange participant-side buy/sell records can identify a much narrower listed-market inventory change, provided coverage, starting positions, corrections and non-trade adjustments are reconciled. Neither route observes the dealer's complete risk book or actual underlying hedge execution.

## 2. Seven different questions

| Object | What is directly observed? | What remains uncertain? |
|---|---|---|
| Trade price and size | Eligible published print, with its revisions | Economic sequence, late reports, package allocation, coverage |
| Aggressive side | Usually inferred from eligible prior quotes | Midpoint, auction, crossed/locked markets, sequencing ambiguity |
| Participant capacity | Available only in a source that explicitly reports it | Beneficial owner, dealer affiliation across accounts, off-venue books |
| Opening/closing | Sometimes participant-side exchange labels | Other participant, position transfers, adjustments, correct scope |
| Long/short inventory | A stock of contracts, requiring a starting state plus changes | Initial positions and incomplete history |
| Dealer net inventory change | Dealer buys minus dealer sells for the stated scope | Unobserved venues, corrections, transfers and nontrade events |
| Underlying hedge and price effect | A modeled target and a separate execution/impact model | Actual hedge holdings, instrument choice, delay, internalization, impact |

An aggressor-classifier accuracy is not a dealer-inventory accuracy. A good fit to next-day OI is not evidence of correct participant assignments. A signed underlying markout can evaluate usefulness, but cannot label who traded.

## 3. Exact transaction accounting

For trade `n`, contract quantity `q_n`, let `d_B,n` and `d_S,n` indicate whether the buyer and seller belong to the chosen dealer population. Aggregate signed dealer inventory, positive for long options, changes by

\[
\delta h_n=q_n(d_{B,n}-d_{S,n}).
\]

This identity does **not** require opening/closing classification. A dealer buying to close a short position increases signed net inventory just as a dealer buying to open a long position does. Dealer-to-dealer and nondealer-to-nondealer trades contribute zero to aggregate dealer net inventory. An estimator that multiplies dealer-side volume by an opening probability wrongly discards closing trades that change net risk.

Opening/closing is a separate clearing identity. Let `o_B,o_S` equal one when that side opens, zero when it closes:

\[
\delta OI_n=q_n(o_{B,n}+o_{S,n}-1).
\]

| Buyer | Seller | Change in total OI |
|---|---|---:|
| Opens long | Opens short | `+q` |
| Opens long | Closes long | `0` |
| Closes short | Opens short | `0` |
| Closes short | Closes long | `−q` |

Both sides matter. OCC educational material describes this clearing distinction [R18]. The public Cboe files' market-maker buy/sell columns should therefore be used as signed changes without demanding nonexistent market-maker open/close columns; actual schema details belong to `14_DATA_SOURCE_COST_RIGHTS.md`.

## 4. Constructive non-identification proof

Suppose a newly listed contract has zero OI, and an ask-side execution opens ten contracts on both sides. OI becomes ten. Three observationally compatible cases are: a nondealer buys from a dealer (`h=−10`); a dealer buys from a nondealer (`h=+10`); or two nondealers trade (`h=0`). The public trade price, size, aggressor classification, opening status and OI are identical. Further price paths cannot logically convert these observations into participant identities.

The executable witness in `witnesses/mechanics_witness.py` enumerates these cases. Its purpose is to disprove unique identification, not assign equal real-world probabilities. Adding many transactions makes the assignment set larger; a Bayesian prior ranks possibilities but does not remove observational equivalence.

## 5. What next-session OI can and cannot do

For contract `i`, after aligning the same economic session and correct vintage,

\[
OI_{i,D+1}^{published}-OI_{i,D}^{published}
=\sum_{n\in D,i}q_n(o_{B,n}+o_{S,n}-1)+A_{i,D}.
\]

`A` includes exercises, expiry extinguishment, transfers/position adjustments where relevant, corrections and any unresolved coverage residual. It is not a free parameter allowed to absorb every model error. Publish components known from source, bounds for plausible unknown components, and a reconciliation failure when constraints cannot be met.

For a nonexpiring contract without adjustments, many opening/closing allocations satisfy the same scalar OI change. If ten contracts open and ten later close, turnover is substantial while final OI is unchanged. Good OI reconciliation rules out impossible allocations; it does not pick the real dealer book.

**For an option expiring that day, next-day zero OI generally provides almost no reconstruction of its intraday path.** Expiration extinguishes surviving positions irrespective of earlier transactions. This is especially damaging to a 0DTE thesis built around next-day OI labels. The useful starting state must come from earlier life-cycle history, explicit assumptions, or participant-classified data.

The previously published prior-session OI can legitimately enter a session-D model once actually received. Do not blindly add a second lag because a file is dated D. Conversely, a file's date is not proof of original availability. Store economic session, publication/receipt time and revision separately. These distinctions refine the incumbent collector's overly broad same-day-leak warning without changing production code.

## 6. Identification tiers

| Tier | Admissible evidence | Claim permitted | Claim forbidden |
|---|---|---|---|
| U0 | Unsigned OI and price/Greek snapshots | Concentration, hypothetical signed-book sensitivities | Observed dealer direction |
| U1 | Public trades plus eligible preceding quotes | Aggressor estimates, classified flow, scenario inventory | Confirmed customer opening/dealer opposite side |
| U2 | Preserved venue quote-condition/customer-interest evidence | Bounded participant-likelihood features where validated | Every resting order is dealer liquidity |
| U3 | Exchange participant-side buy/sell aggregates | Scoped net participant changes after publication | Complete real-time dealer portfolio |
| U4 | U3 plus series-inception history and reconciled adjustments | Scoped cumulative listed inventory estimate | Individual dealer hedge policy or OTC exposure |
| U5 | Proprietary full position/hedge data with rights | Whatever exact covered positions/hedges actually show | Universal extrapolation beyond scope |

The SEC staff paper on customer limit orders demonstrates why passive-side-equals-dealer is unsafe and why economic sequence needs care. It uses raw quote conditions and proprietary validation; its matching rate is not a universal classifier success rate [R04]. Strong modern 0DTE studies use participant-classified position histories [R02] [R03], a different data problem from public OI signing.

## 7. Posterior versus identified set

Maintain two distinct uncertainty objects:

1. **Feasible/scenario set** `H_t`: positions consistent with admitted constraints and explicit assumptions. Its min/max hedge demands are stress bounds, not probability intervals.
2. **Model posterior** `P_M(h_t,z_t | O_≤t)`: a distribution conditional on a named model, prior and calibration sample. Its credible intervals need independent coverage checks and prior sensitivity. Without labeled data, call them model-implied credible intervals, not calibrated inventory confidence.

Report the dispersion within a model and disagreement between models separately. Inventory errors are correlated across strikes, legs and time. An independent contract-error assumption can create absurdly narrow aggregate uncertainty. Preserve shared participant-regime and package-level latent states.

## 8. Scope that remains irreducible

Even perfect listed-market net positions leave OTC options, exotics, variance swaps, cross-asset hedges, internal client netting, dealer risk limits, hedge timing and the distribution across individual dealers unobserved. Aggregation can hide two desks trading in opposite directions at different times. Identical aggregate gamma can coexist with different execution pressure.

The correct product promise is conditional: **given this covered inventory estimate, volatility path, hedge convention and liquidity state, here is the modeled range of incremental hedge demand and the historically calibrated range of outcomes.** Mechanistic plausibility and predictive value must be tested independently.

## 9. Decisive research questions and falsifiers

| Question | Test | Falsifier / disposition |
|---|---|---|
| Does public tape improve inventory estimation? | Compare signed changes and exposure against a rights-cleared participant benchmark by contract, expiry, time and package | No exposure-error improvement over simple priors: do not expand latent model |
| Does OI smoothing help future filtering? | Train on prior-session reconciliations only; evaluate later live-filter errors | Benefit exists only after using the evaluated day's later OI: leakage, reject |
| Does true scoped inventory improve predictions? | Exchange-labeled benchmark plus identical price/liquidity model | No economically meaningful out-of-sample gain: stop expensive reconstruction programme |
| Does inventory ambiguity reverse the inferred sign? | Prior/venue/package/surface sensitivity ensemble | Unstable sign: publish scenario dispersion and withhold behavioral label |
| Are modeled hedges actually material? | Matched horizon/venue liquidity and downstream outcome tests | Exposure magnitude alone succeeds only in-sample: do not claim control |

The smallest useful experiment compares public-flow, participant-informed and incumbent models on the same frozen sessions. It is specified in `16_EMPIRICAL_VALIDATION_MASTERPLAN.md` and `20_CEO_FABLE_HANDOFF.md`.

<!-- Report-local source links. Scope and access limits are in SOURCE_REGISTER.md. -->

[R02]: https://www.jean-sebastienfontaine.com/papers/0dte-options-volatility.pdf
[R03]: https://cdn.cboe.com/resources/education/research_publications/gammasqueezes.pdf
[R04]: https://www.sec.gov/files/dera-hope-reasonable-prc-2503.pdf
[R18]: https://www.optionseducation.org/referencelibrary/faq/general-information
