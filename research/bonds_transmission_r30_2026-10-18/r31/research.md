# R31 analytical research and design decisions

This pass deepens the accepted R30 research journey. It does not treat the motivating AI-credit/Treasury explanation as an established current causal fact. The additional tools ask what evidence would distinguish competing explanations, how a mechanism can fail and which observation should be checked next.

## A useful continuation view preserves disagreement

An apparent reversal should be compared across horizons and along the curve. A positive five-day Treasury return with a negative twenty-day return is a rebound within a weaker longer window. A large front-end rally with little long-end participation may reflect a different mechanism from a uniform duration bid.

R31 therefore presents price structure, relative return and participation as related descriptions. It does not count them as independent confirmations. The 5.08% close test and 5.22% invalidation are authored illustrative conditions. Their volatility distances describe scale; they do not estimate success odds.

A break-and-retest rule becomes reviewable only when its series, close clock, band, allowed sessions and next-close condition are explicit. Retaining those parameters is necessary before evaluating outcomes. Changing a rule after seeing an outcome would invalidate the comparison.

The existing historical replay route remains useful because it includes contrary episodes and separates what was known from what happened later. R31 adds more precise inputs to that path rather than manufacturing a new predictive score.

## A curve can move in several directions

A single duration number is convenient for a small parallel shift. It can hide a position's exposure to a twist. The CME key-rate-duration note explains maturity-specific sensitivity and portfolio rebalancing by curve segment [R31-S03]. R31 uses that principle to add a four-node sensitivity fixture.

The example short-end yield declines are offset by long-end increases. The result is a modest estimated price loss even though some yields fall. This is a deterministic calculation under declared assumptions. It is not a forecast of the future curve or a replacement for instrument repricing.

The implementation must preserve the curve, bump method, valuation cutoff and vector coverage. Combining incompatible key-rate sensitivities and shocks would create a precise-looking but meaningless output. The control therefore withholds shape mode when those inputs do not match.

## Reported debt is not a daily cash calendar

CoreWeave's June 30, 2026 Form 10-Q provides annual principal buckets in Note 10, alongside facility conditions and entity-specific restrictions [R31-S01]. Those disclosures support the reported obligation view; they do not establish a current exact-date funding gap.

R31 keeps that reported view distinct from the synthetic Parent A cash example. A valid payment analysis needs dated obligations, accessible cash for the selected legal obligor, transfer permissions and financing that actually settles before the relevant cutoff.

The operating buffer is a user-selected analytical assumption. Crossing it is different from lacking cash to meet the scheduled obligations. The two financing amounts are therefore shown separately.

The late-draw state tests a failure that a daily closing balance can hide. Later proceeds can restore the projected balance while the earlier payment cutoff still had a financing deficit. The design does not equate that deficit with an observed overdraft or a legal default determination.

Facility capacity also needs semantic care. Gross commitment, already drawn funds, letters of credit and borrowing-base constraints are different fields. A disclosed amount already net of a constraint must not have the same constraint deducted again. A past draw deadline requires a rollforward; it cannot be treated as currently eligible financing.

## Falling holdings do not prove capital rotation

The Federal Reserve Financial Accounts distinguishes transactions, revaluation and other changes in the reconciliation of balance-sheet positions. The current explanatory material also makes release frequency and timing relevant to interpretation [R31-S02].

R31's matched-holder fixture makes the distinction concrete: AI-credit holdings fall in market value while the holder is still a net buyer. Treasury holdings and Treasury net purchases rise at the same time. These observations do not establish that AI-credit sales funded Treasury purchases.

Even positive net purchases do not mean that no gross sales occurred. A causal funding route requires additional matched transaction, cash, redemption or allocation evidence at a compatible frequency. A residual estimate can be useful, but its label must remain different from a sourced transaction observation.

The default UI therefore offers three useful tests: could this buyer switch, can the switch be observed, and could funding pressure force a different decision? Mandate, currency, duration, hedge cost and liquidity eligibility remain part of the buyer comparison.

## The funding channel can challenge a safety bid

The Federal Reserve's August 26, 2026 repo note discusses channels through which Treasury supply composition, dealer financing demand and money-fund allocation alternatives affect repo conditions [R31-S04]. R31 uses the qualitative mechanism to expose a counterpath to a simple Treasury-safety narrative.

More coupon supply can raise dealer financing demand. Bills can offer money funds an alternative to repo lending. Those two channels do not have a universal fixed coefficient or an automatic Treasury-price consequence. The interface therefore points to funding rates, collateral/margin conditions and market depth, with dealer/holder data shown at their slower native frequency.

A narrative about aggregate liquidity is incomplete if it does not examine cash actually deployed to the relevant funding market. This is why the diagram is a mechanism map with equal-weight lines, not a Sankey chart with invented flow volumes.

## Research continuity is part of analytical quality

The source inspection located Terminal Investigation v2 and the current Alerts owner. This avoids inventing another case store or monitoring service. It also revealed that their existing admission paths do not yet accept the complete proposed bond scenario.

That boundary affects the design itself. A save review must show exactly what survives. A successful question save cannot imply that the scenario will reopen unchanged. Saved versus current evidence must remain visibly separate, and uncertainty about an exact revision read must not silently fall through to a different revision.

The complete retained-case comparison is a future-capability design state. The current question-only state is the bounded alternative when the supported fields pass the owner. Combined monitoring remains unavailable until its full condition semantics are implemented in the existing service.

## Evidence register

| ID | Primary source | Reviewed portion and use |
| --- | --- | --- |
| R31-S01 | [CoreWeave June 30, 2026 Form 10-Q](https://www.sec.gov/Archives/edgar/data/1769628/000176962826000366/crwv-20260630.htm) | Note 10 annual principal, borrowing conditions and entity restrictions; dated reported obligations and rollforward requirements |
| R31-S02 | [Federal Reserve Financial Accounts: explanatory text](https://www.federalreserve.gov/releases/z1/current/introductory_text.htm) | Current release concepts for transactions, revaluation, other changes and publication frequency; read October 18, 2026 |
| R31-S03 | [CME Key Rate Duration Adjustment](https://www.cmegroup.com/education/files/key-rate-duration-adjustment.pdf) | Revised January 2017 note; introductory/maturity-specific sensitivity sections reviewed, not a claim of complete paper reproduction |
| R31-S04 | [Federal Reserve: Repo Markets and the Fed's Balance Sheet](https://www.federalreserve.gov/econres/notes/feds-notes/repo-markets-and-the-feds-balance-sheet-implications-for-monetary-policy-implementation-20260826.html) | August 26, 2026 supply, dealer financing and cash-allocation mechanisms; no fitted coefficient imported |

The current Financial Accounts explanatory source notes a June 2026 table reorganization. An implementation should resolve current table/series metadata rather than assume that an older F/L table number remains the canonical identifier.

Repository evidence is separately pinned in source_bindings.json and data_contract.md. The numeric technical, buyer-flow, key-rate and Parent A examples are synthetic fixtures. They are not current market quotes, forecasts or issuer solvency findings.

## Remaining empirical work

The design supports an eventual qualified continuation estimate, but no likelihood has been produced in this pass. The next empirical work must retain a specific target and horizon, point-in-time source availability, matched instruments and regimes, contrary cases, out-of-sample calibration, dependence-aware evaluation and an abstention policy.

Faster understanding comes from reducing the number of things the user must interpret at once. More analytical depth comes from a reproducible next test and inspectable evidence. R31 supplies that architecture while leaving the actual production/data/model acceptance work explicit.
