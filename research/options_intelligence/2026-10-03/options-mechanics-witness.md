# Options mechanics: bounded quantitative witness

Research date: 2026-10-03. Prepared for Astra's Options Intelligence research package. This is a pinned-source and synthetic-math review, with no production changes, runtime claim, inferred dealer inventory, or alpha claim.

## Verdict

**Terminal's `hedgeProfile` can produce a cumulative sensitivity display grouped by contract strike, but its Gamma branch does not calculate the hedge trades required as spot travels from the current price to a target.** Sorting strike rows and summing the existing Gamma sensitivities on either side of spot cannot recover that quantity. This conclusion follows from zero-move, trade-direction, omitted-position, and equal-input/different-output witnesses below. It does not invalidate the underlying per-strike Gamma sensitivities as local sensitivities. [T1]

**Macro's `_gamma_flip` has a separate crossing-orientation assumption.** Its underlying `gamma_profile` does reprice Gamma across hypothetical spot levels. However, when a crossing exists, the wrapper chooses the nearest crossing and assigns long above/short below without consulting crossing direction or the sign of the same curve at spot. The supplied descending-crossing chain makes the returned regime disagree with the function's own repriced Gamma. Ascending-crossing and no-crossing controls agree. [M1]

Both findings are bounded to the exact source pins below. They establish mathematical counterexamples and executable source behavior, not frequency, materiality in live data, or an operational deployment defect.

## 1. Exact sources and execution boundary

| Source | Immutable revision | Inspected code |
|---|---|---|
| Terminal `terminal/lib/marketStructure.ts` | `a049d46fa2415d3949aae5efc0ee515b6667c7a0` | Unit contract 10–16; profile types and units 597–635; `hedgeProfile` 646–697. [T1] |
| Terminal `terminal/components/msc/HedgingCards.tsx` | Same Terminal revision | Function invocation, bars/profile mapping, and per-unit caption 69–151. [T2] |
| Macro `engine/gex_engine.py` | `6f5e78e94e8808582a650cdfa0fc3357040a179c` | `gamma_profile` and `_gamma_flip`, 43–90. [M1] |

The companion Python script embeds the exact selected source snippets. It executes the original Terminal function in Node after explicit, checked removal of TypeScript type annotations only. It executes the original two Macro function ASTs with NumPy, pandas and the mathematical constant `sqrt(2π)` supplied. It does not import a production engine, load a production checkout, query a live options feed, call an application API, or run a production test suite.

The fetched source bytes were verified against their Git blob IDs before creating the embedded capsules. Local staging copies had one appended final newline; removing only that byte produced the exact recorded blob IDs. The `.json` contains file hashes, snippet hashes, execution methods, every synthetic input, original function outputs, and computed hedge quantities. The `.py` is self-contained apart from the stated runtimes.

## 2. Chosen economic convention and units

Each synthetic book contains European options on one share-priced underlying. All contracts use a 100-share multiplier. Let `n_i` denote a signed scenario position in contracts: positive is long options and negative is short options. These are deliberately specified hypothetical books, without a dealer-ownership inference. Rates and dividend yield are zero. Time to maturity is in years and implied volatility is an annual decimal.

For the spot-only witnesses, positions, remaining maturities and implied volatilities stay fixed during the comparison. Under Black–Scholes, with `v_i=σ_i√T_i`,

\[
d_{1,i}(S)=\frac{\log(S/K_i)+\tfrac12\sigma_i^2T_i}{\sigma_i\sqrt{T_i}},\qquad
\Delta_i^{call}(S)=\Phi(d_{1,i}),\qquad
\Delta_i^{put}(S)=\Phi(d_{1,i})-1,
\]

\[
\Gamma_i(S)=\frac{\phi(d_{1,i})}{S\sigma_i\sqrt{T_i}}.
\]

These independently evaluated scalar formulas provide a transparent synthetic benchmark; the Gamma expression agrees with the zero-rate, zero-yield case of the inspected Macro repricer. [M1]

The delta-neutral underlying position is

\[
q(S)=-\sum_i n_i m_i\Delta_i(S).
\]

The chosen endpoint hedge trade is executed at the target spot, after starting with the hedge appropriate to `S0`:

\[
\Delta q=q(S_*)-q(S_0)
=-\sum_i n_i m_i[\Delta_i(S_*,T_i,\sigma_i^*)-\Delta_i(S_0,T_i,\sigma_i^0)],
\]

\[
\boxed{H(S_*)=S_*\Delta q.}
\]

`Δq` is in underlying shares; `H` is in dollars. **Positive `H` means buy underlying; negative `H` means sell underlying. The cash balance change from that trade is `−H`.** The numerical spot-only cases set `σ_i*=σ_i0`. Existing cash, option P&L, financing, turnover, transaction costs, and continuous rebalancing are outside this convention. In particular, endpoint notional `S*Δq` is not the accumulated cash traded by continuously rehedging along an arbitrary path.

At the initial spot, each Terminal Gamma row is constructed to match the source's unit contract:

\[
G_K=\frac{1}{10^6}\sum_{i:K_i=K}n_i m_i\Gamma_i(S_0)S_0^2(0.01).
\]

Its unit is **$mn of underlying delta-notional sensitivity per +1% spot move at the base snapshot**. Gamma itself is delta change per dollar of underlying price. Summing the `G_K` values across strikes retains that local sensitivity unit; it does not supply a target-specific total hedge trade. [T1]

## 3. What `hedgeProfile` actually calculates

For Gamma, the function maps a valid row to `hedgeMn = -gamma_net`, sorts by strike, then splits the rows into `K<S0` and `K>=S0`. It accumulates the first group from the closest lower strike outward and the second group from the closest upper strike outward. Consequently, at a displayed strike `K`, the returned cumulative value is:

\[
C(K)=
\begin{cases}
-\sum_{K\le j<S_0}G_j,&K<S_0,\\
-\sum_{S_0\le j\le K}G_j,&K\ge S_0.
\end{cases}
\]

Here `j` denotes a contract strike, not a hypothetical spot. There is no multiplication by the actual price shock, no integration over spot, no Gamma repricing, and no use of the omitted side's positions. A row exactly at spot enters the upper branch; the function inserts no separate zero anchor. [T1]

The UI's profile view maps these values directly to the line series and retains the per-unit caption. It also requires more than one plotted point; every Terminal synthetic book below has two distinct strike rows. The per-unit caption is appropriate for sensitivities and is an important qualification: **the numerical mismatch is with the source's price-travel/hedge-requirement interpretation, not with an invented assertion that every displayed value is labeled as total dollars.** [T1][T2]

## 4. Minimal Terminal witnesses

All rows use `S0=100`, zero rates and dividend yield, and multiplier 100. `H` below is the endpoint trade defined above. The source profile column is a local sensitivity and is deliberately shown with its different unit.

| Witness | Specified synthetic book and target | Source cumulative output, $mn per +1% | Endpoint `H`, $mn | Discriminating result |
|---|---|---:|---:|---|
| Unchanged spot | 1,000 long calls each at K100/K110; 30 days; IV20%; target100 | −0.695484 at K100 | 0 | A nonzero profile point at spot cannot be the no-move hedge trade or a zero anchor. |
| Lower target | 1,000 long calls each at K95/K105; 30 days; IV20%; target95 | −0.454333 at K95 | +4.494315 | The underlying hedge must buy 47,308.58 shares. The negative sensitivity on the lower branch is still the sensitivity to an upward shock, so reading it as the downward-travel action reverses the direction. |
| Upper target, baseline | Same K95/K105 book; target105 | −0.496197 at K105 | −4.681849 | Reference for the omitted-position comparison. |
| Upper target, more lower-strike inventory | Increase K95 calls to 3,000, keep K105 at 1,000; target105 | −0.496197 at K105 | −7.620211 | The displayed upper cumulative value is exactly unchanged even though the required sale grows by $2.938363mn. Positions below spot also change delta when spot rises. |

The lower-branch example is not a demand that a +1% sensitivity should itself reverse sign: it correctly remains negative for a long-option book's response to a positive perturbation. It shows why the sensitivity cannot simultaneously be interpreted as the actual transaction required for the negative price move.

### Same snapshot Gamma, different maturity or IV

Each pair below contains a common position of 1,000 long K110 calls, 30 days, IV20%. The other position has K100. Position B is analytically scaled to match position A's current Gamma contribution exactly:

\[
n_B=n_A\frac{\Gamma_A(S_0)}{\Gamma_B(S_0)}.
\]

The fractional weights are intentional scenario portfolio scalings. They are not purported observed or executable fractional exchange-contract holdings. Matching could also be approximated with sufficiently large integer portfolios, but that is unnecessary to disprove the mathematical identification claim.

| Pair | K100 position A | K100 position B | Identical source profile at K110, $mn per +1% | `H_A(110)`, $mn | `H_B(110)`, $mn |
|---|---|---|---:|---:|---:|
| Different maturity | n=1,000; T=7/365; IV20% | n=5,082.957178276; T=180/365; IV20% | −1.623472 | −10.499083 | −18.763050 |
| Different IV | n=1,000; T=30/365; IV10% | n=5,012.343979474; T=30/365; IV50% | −1.574626 | −10.495349 | −18.336240 |

Both pairs produce **identical input Gamma rows and identical profile outputs in the recorded floating-point run**: maximum row and cumulative differences are zero. Their finite-spot hedge requirements differ by $8.263966mn and $7.840891mn respectively. Thus no deterministic transformation using only these Gamma rows, their strike ordering, and the base spot can recover both books' correct finite-move hedge trades.

The conclusion is about information loss in the snapshot summary. Under zero rates and frozen inputs, equal `σ√T` produces the same spot-only delta/Gamma functions even when T and IV individually differ; the script checks that equality as a control. Different T or IV alone is not a sufficient argument without controlling the combined volatility-time dependence and portfolio weights.

## 5. What a consistent Gamma calculation can establish

With time and IV frozen, the endpoint hedge share change can also be written as

\[
\Delta q=-\int_{S_0}^{S_*}\sum_i n_i m_i\Gamma_i(s,T_i,\sigma_i)\,ds.
\]

The integral is over **hypothetical underlying spot**, includes **the entire chosen position book at each spot**, and then multiplies the resulting share change by `S*` for the selected endpoint convention. It is not a sum over contract strikes. If expressed using a repriced dollar-Gamma curve `G(s)=Σ n m Γ(s)s²·0.01`, its share-change integrand is `G(s)/(s²·0.01)`, not `G(s)` without scaling.

The supplied controls distinguish the conceptual finding from an objection to Gamma mechanics:

- A tiny move from 100 to 100.0001 gives exact `H=−$95.05300150`; the whole-book local Gamma approximation is `−$95.05305902`, a relative error of `6.0513×10⁻⁷`.
- Integrating the whole-book repriced Gamma from 100 to 105 yields `H=−$4,681,848.77556698`; direct endpoint deltas yield `−$4,681,848.775566985`.
- Reversing every signed position reverses `H` exactly to recorded precision.
- Reversing the input row order leaves Terminal's profile identical, as expected from its sort. Ordering the same insufficient statistics differently does not add the missing information.

These are synthetic witness/control assertions, not production tests or a validation of any pricing model against observed markets.

## 6. Macro gamma-flip crossing orientation

`gamma_profile` reevaluates Gamma at 101 trial spot points spanning 75%–125% of its input spot. It keeps each contract's IV and time fixed and uses the explicit proxy sign `+1` for calls and `−1` for puts, multiplied by OI and the configured multiplier. It locates sign crossings by linear interpolation. `_gamma_flip` selects the crossing closest to current spot; if one exists, its final regime depends only on whether current spot is above or below that crossing. The no-crossing branch instead uses the midpoint curve sign. [M1]

### Discriminating chain

Use 20 distinct contracts, each OI100, T30/365, IV20%, multiplier100. The lower ten strikes are `95.00 + 0.01j`; the upper ten are `105.00 + 0.01j`, for `j=0..9`. Assign lower strikes to calls and upper strikes to puts. Under the source's assumed signs this creates a descending crossing: positive Gamma on the lower side and negative Gamma on the upper side. The chain passes the function's 20-row minimum without duplicating identical rows.

| Scenario | Input spot | Nearest crossing | Own curve Gamma at current spot, $ per +1% | Wrapper regime | Regime from own curve |
|---|---:|---:|---:|---|---|
| Descending crossing | 98 | 99.75550735 | +242,969.33 | short | long |
| Descending crossing | 101 | 99.75550989 | −178,019.06 | long | short |
| Ascending control: swap calls and puts | 98 | 99.75550735 | −242,969.33 | short | short |
| Ascending control: swap calls and puts | 101 | 99.75550989 | +178,019.06 | long | long |
| No crossing control: all calls | 101 | null | +955,204.61 | long | long |

The tiny difference in interpolated flip values between the two input spots comes from their different spot-centered grids. It has no bearing on the orientation result. Each descending case has exactly one crossing and disagrees with the function's own midpoint value; no multi-crossing interpretation or external pricing model is needed.

The verdict is therefore specific: **nearest-crossing location alone does not determine the local Gamma sign; long-above/short-below assumes an ascending crossing.** This witness does not allege that `gamma_profile` is a strike cumsum: its hypothetical-spot repricing is categorically different from Terminal's `hedgeProfile`. Neither its assumed position sign nor a computed Gamma regime identifies actual dealer inventory or proves a predictive market effect. [M1]

## 7. Reproduction and evidence handoff

Run:

```bash
python options-mechanics-witness.py --output options-mechanics-witness.json
```

The recorded run used Python 3.12.14, NumPy 2.3.5, pandas 2.2.3, and Node v24.19.0. It completed with `PASS: all intended counterexample and control assertions`. The final source-capsule formatting and provenance-assertion reruns produced byte-identical JSON. No dependency installation or network request is performed by the script.

JSON SHA256: `ed13e0ac68b84d8556acea030a91e4851f57bc098a80dedf35d7106d5dec2c0b`.

| Source | Git blob SHA | Original full-file SHA256 |
|---|---|---|
| Terminal math | `b57bb1b794522c80af5a8288a82bcb06d64ed939` | `9dbb320e5f89dee717e8f6d7fa044ec36036a46c514dc685efd5dcd8cb1c852a` |
| Macro Gamma engine | `15cff47b86b6a452daa6268a7f8be5455f914b13` | `781298048633b08050ae00fe6bb5fd89fdc20d0d040630e7b0a4b3d7d5e97e2c` |
| Terminal UI consumer | `b3562a6b227673a94e8f2cc55bb55b64fe87dce3` | `55b9d401674b8f4b283a0c0b02f9d5f032912f60e067af97f71624c54aaac67e` |

This bounded witness is complete. For a later implementation assignment, the consequential design decisions are whether to retain the Terminal view as an explicitly labeled cumulative sensitivity by strike or supply sufficient position/scenario state for a hedge-change view, and how to express a flip's location, orientation, local Gamma sign and boundary status consistently. Those are research handoff criteria; this package makes no production repair, branch, PR, merge, deployment or owner reassignment.

## Primary source references

[T1]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/a049d46fa2415d3949aae5efc0ee515b6667c7a0/terminal/lib/marketStructure.ts
[T2]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/a049d46fa2415d3949aae5efc0ee515b6667c7a0/terminal/components/msc/HedgingCards.tsx
[M1]: https://github.com/mastermindx-market-intelligence/macro/blob/6f5e78e94e8808582a650cdfa0fc3357040a179c/engine/gex_engine.py

- [T1 — Terminal units and hedgeProfile][T1]
- [T2 — Terminal chart consumer][T2]
- [M1 — Macro Gamma profile and flip wrapper][M1]
