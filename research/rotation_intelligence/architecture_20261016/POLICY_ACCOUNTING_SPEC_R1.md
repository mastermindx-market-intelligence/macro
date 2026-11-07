# Self-financing policy accounting — research specification R1

This appendix closes an arithmetic ambiguity in [TARGET_SCOPE_AND_BASELINES_R1.md](TARGET_SCOPE_AND_BASELINES_R1.md) before any market-outcome study. It is not a portfolio optimizer, empirical result, trading engine or native evaluator implementation. The executable witness reads no market data and imports no product module.

## 1. Fix the budget equation

Let h_i be the pre-trade marked dollar holdings, including uninvested settlement cash; W = sum(h_i). Let w_i be nonnegative target fractions summing to one. Let c_i be proportional transaction cost per dollar of an actual security purchase or sale, with 0 <= c_i < 1. Settlement cash has c_0 = 0. BIL is a **security** in this accounting, not that free settlement-cash coordinate.

The investable post-trade wealth V must satisfy:

    V + sum_i c_i * abs(w_i * V - h_i) = W.

The new holdings are w_i * V. Costs depend on those actual post-cost purchases/sales. Computing costs on one notional and then normalizing a different portfolio can otherwise introduce an inconsistent budget.

For F(V) equal to the left side minus W, F(0) <= 0 and F(W) >= 0. Between sign changes its slope is 1 + sum_i c_i*s_i*w_i, bounded below by 1 - max_i(c_i) > 0. Hence the root exists and is unique on [0,W]. Bisection is sufficient for this research witness; no price forecast or general optimization service is required.

For an independent check, enumerate each possible buy/sell sign region s_i in {-1,+1} and solve:

    V = (W + sum_i c_i*s_i*h_i) / (1 + sum_i c_i*s_i*w_i).

Retain only roots consistent with their assumed signs. For the small invented vectors, this analytic calculation provides a different method from bisection. It is independent arithmetic, **not an independent reviewer or approval receipt**.

## 2. Simple discriminating examples

With unit initial wealth and a synthetic one-way cost c:

| Case | Correct post-trade wealth |
|---|---|
| Settlement cash into one fund | 1 / (1+c) |
| Entire fund A holding switched to fund B | (1-c) / (1+c) |
| Fund liquidated to settlement cash | 1-c |
| Target equals actual drifted weights | 1; zero trades and zero costs |
| Weights drifted to 60/40, rebalance to 50/50 with equal cost c | 1-0.2*c |
| Flat-price settlement-cash → fund → settlement-cash round trip | (1-c) / (1+c); never a profit from accounting |

These formulas use **cost per traded security dollar**. An illustrative model that charges a fraction of pre-trade wealth uses a different cost convention; do not silently combine the two. The earlier package's simple multiplicative synthetic examples remain illustrative evidence under their original assumptions, not the implementation of this exact cash-flow rule.

## 3. Cash bookkeeping is not security turnover

An initial cash-to-fund purchase changes both the cash coordinate and the security coordinate. Summing both absolute changes nearly doubles the number called turnover, even though only one security transaction occurred. The first version of this research witness used the overly broad name `gross_traded_notional` for that sum. A regression assertion failed as expected: approximately 1.999 units were reported while the actual security purchase was approximately 0.999 units.

The corrected witness reports two different quantities:

- `gross_position_changes_including_settlement_cash`: all bookkeeping movements;
- `securities_traded_notional`: actual security purchase/sale notional, excluding settlement cash.

It explicitly reserves coordinate zero for settlement cash and rejects a security-trading charge on that coordinate. BIL and other funds occupy security coordinates even when their financial role is a cash alternative. A zero-fee fund trade still counts as security turnover; the code does not infer security identity merely from a positive fee.

This correction was made to the standalone research witness only. It is not a claim that an existing production portfolio engine had or now has this bug.

## 4. Executed checks

[policy_accounting_witness.py](policy_accounting_witness.py) produced [policy_accounting_results.json](policy_accounting_results.json):

- Seven closed-form deterministic cases passed.
- 512 invented three-coordinate portfolios matched bisection against the separate sign-region solution. Maximum relative discrepancy was 4.536289913420521e-16.
- 128 invented portfolios retained non-increasing post-trade wealth as the declared proportional costs increased through 5, 10, 25 and 50 basis points.
- Eight invalid cases were rejected, including negative holdings, incomplete weights, negative/100% costs, booleans, NaN, zero wealth and a charge on settlement cash.
- A red/green turnover discriminator demonstrated that the original naming/counting behavior failed and that security-only turnover now matches the actual purchase, liquidation and zero-fee security-switch cases.

Script SHA-256: `9a071d1b156ab9684e72f2032d06a51c8096089aef784c0c87ebfb5aa3a7281e`.
Result SHA-256: `a9c590f56f43900975a8160f39efa103408ccda7777f804fcb7922791b47cf7e`.

The exact scientific values must be reproduced from published bytes at final readback. A source edit invalidates that script's prior hash but does not invalidate unrelated source observations or the original archived assessment.

## 5. What the witness does not model

No market impact, minimum commissions, discrete share sizes, taxes, financing, borrow, options, intraday fills or forecast calibration is modelled. Costs are assumptions rather than estimates. Prices are fixed within each rebalance calculation. Cash accrual and fund returns between decisions belong to the separately qualified path; the witness cannot create them.

The future baseline evaluator must mark holdings using the actual interval return, compute drifted weights, aggregate duplicate instrument targets before netting trades, apply a common terminal-date convention and handle missing prices without invented liquidation or capital resets. Source/return/currency basis, spread and capacity proof remain required. These are acceptance conditions for the **existing evaluation owner**, not a new parallel service.

## 6. Research phase result

The accounting question now has an explicit equation, uniqueness argument, independent arithmetic comparison, bad-input behavior and reproducible adverse cases. This closes the standalone design uncertainty. It does not open market data, replace native statistical size/power tests, qualify an investment policy or authorize trading weights.
