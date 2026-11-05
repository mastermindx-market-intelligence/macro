# B1/B2 executable research reference

**Result: PASS, 83 adversarial assertions; independently reproduced by the bounded native math reviewer.** These are new, isolated reference artifacts for incumbent-owner adaptation. They do not modify a production engine, Terminal component, existing research file, schema, active PR, store, loop, runtime or authority flag.

| Artifact | Role | SHA256 |
|---|---|---|
| [options-reference-kernels.py](options-reference-kernels.py) | Standard-library numerical references and executable fixtures | `188fcb0f80cdb27bdde06601cfa4f4da50799bb8d53372f80b8aaec5f155da8f` |
| [options-reference-kernels-results.json](options-reference-kernels-results.json) | All assertion names, synthetic inputs, output states, root features and numerical results | `c869486ea537219c90259c299aadaf548647e148bc39d9cd5c6861bdd90909cc` |

The requested behavior comes from [OWNER_REPAIR_BRIEFS.md B1/B2](OWNER_REPAIR_BRIEFS.md), [CONTRACTS.md](CONTRACTS.md), and the accepted [mechanics witness](options-mechanics-witness.md). The original counterexamples remain tied to Terminal `a049d46fa2415d3949aae5efc0ee515b6667c7a0` and Macro `6f5e78e94e8808582a650cdfa0fc3357040a179c`. Those pins establish the earlier defect, not the current state of any incumbent worktree. The principal supplied governance pin `20adcaf65c2dd1bb734ab06e215feb1a0eb65659`; no provider or M2 work was performed.

## Run and inspect

The recorded final command was:

```bash
python /workspace/scratch/304dc2fae6f2/options-research/options-reference-kernels.py --output /workspace/scratch/304dc2fae6f2/options-research/options-reference-kernels-results.json --replace-results
```

It returned `PASS`, 83 assertions, and the JSON hash above. Python 3.12.14 was used; there are no nonstandard dependencies, network requests, production imports or background workers. `--replace-results` was used only to update this task's newly created results artifact after edge-case corrections. A fresh reproduction can instead select a new output path:

```bash
python options-reference-kernels.py --output /tmp/options-reference-kernels-reproduced.json
```

The CLI refuses an existing output unless replacement is explicit. Omitting `--output` emits JSON to stdout. The JSON records the script's own SHA256. Its numeric values use finite JSON serialization; malformed arguments or numeric range overflow produce a named `ContractError`, rather than a qualified infinity. Missing row information produces the nullable result states described below.

## B1: direct current regime, separate sampled root features

`analyze_gamma_curve(evaluate, sample_spots, current_spot, ...)` calls the supplied evaluator at actual current spot. It does not infer the current sign from the nearest crossing or interpolate the current value from a grid. `book_gamma_evaluator` supplies the same hypothetical-book economics at each requested spot; synthetic functions supply adversarial topology fixtures.

The declared quantity is **Gamma-driven delta-change notional per +1% spot perturbation**:

\[
G(S)=\sum_i n_i m_i\Gamma_i(S)S^2(0.01).
\]

It excludes the `Delta*dS` term in the change of `S*Delta`; it is not the full market-value change of hedge holdings. `GammaUnit` records currency and output scale, so dollars and millions cannot be silently interchanged. Net and gross-absolute Gamma use the same unit.

The current sign is positive, negative or near-zero according to

\[
\epsilon(S)=\epsilon_{abs}+\epsilon_{rel}\sum_i|G_i(S)|.
\]

The research defaults are `1e-8` in output monetary units and `1e-10` relative to gross exposure at the same spot. These are numerical tolerances, not market-materiality thresholds or calibrated risk bands. The scale is local, so adding distant grid points cannot change the current regime. A dollars-to-millions conversion also converts the absolute tolerance.

Grid points are sorted and deduplicated; generator inputs are materialized once. The output distinguishes:

- Opposite-sign brackets with explicitly approximate linear-interpolation locations and ascending/descending orientation.
- One sampled exact-zero crossing, without double counting both adjacent intervals.
- Sampled zero bands, with no fabricated unique root; same-sign and opposite-sign flanks remain distinct.
- A sampled touch candidate compatible with a tangent, without asserting a derivative-based proof.
- Tolerance bands, which may have no actual zero. `observed_exact_zero_spots` preserves any true zero-valued samples inside a mixed band independently of `all_samples_exact_zero`.
- Boundary or gap-adjacent zeros with undetermined two-sided orientation.

Missing evaluations are never bridged into crossings. Multiple features and equally nearest features are retained. A finite grid cannot certify all continuous roots, exclude unsampled tangencies or hidden multiple crossings, or establish that a run of zero samples is a continuously zero interval. Accordingly the output calls them **root features**, and explicitly denies continuous-root completeness.

Grid and model domains are different. Outside the sample grid, a permitted direct model evaluation can still give a qualified current regime. Outside an explicit model domain, evaluation is withheld and the regime is unknown. Domain labels and evaluation-method fields report those cases separately. An empty or one-point grid cannot establish a complete root search, even if the direct current evaluation is valid.

The accepted 20-contract descending-crossing witness now yields:

| Current spot | Direct Gamma, USD per +1% | Reference regime | Sampled crossing orientation |
|---|---:|---|---|
| 98 | +242,969.325354 | positive | positive to negative |
| 101 | −178,019.058317 | negative | positive to negative |

The mirrored ascending chain, no-crossing curve, multiple roots, exact zeros, plateaus, tangencies, near-zero values, missing intervals, unit mismatch, model failure, permutations, duplicated grid points and domain boundaries have separate fixtures.

## B2: sensitivity distribution and endpoint trade are different outputs

`strike_sensitivity_distribution(book, spot, amount_scale=...)` groups the signed portfolio Gamma contribution by **contract strike**. Positive portfolio Gamma sensitivity and the opposite negative hedge sensitivity have distinct fields. Short inventory can reverse those signs; “portfolio” does not mean unconditionally positive.

The cumulative fields run from the lowest represented contract strike and explicitly retain sensitivity units. They are a distribution summary, not an anchored target-spot scenario, path integral or total trade. No division by net signed Gamma creates unstable pseudo-weights around cancellation.

`endpoint_rehedge(book, initial_spot, target_spot, ...)` instead reprices every eligible specified position under fixed IV/time or explicit per-position IV overrides and elapsed time:

\[
B_0=-\sum_i n_i m_i\Delta_i(S_0),\qquad
B_*=-\sum_i n_i m_i\Delta_i(S_*,\sigma_*,T_*),\qquad
H=S_*(B_*-B_0).
\]

Positive `H` means buying underlying; the endpoint trade's cash-balance change is `−H`. The calculation is not `S*B*−S0B0`. Per-position delta differences are summed directly to avoid needless cancellation of large hedge levels. Tiny floating-point differences can therefore exist between the separately displayed summed levels and the directly summed change.

The matched long-call/short-put fixture demonstrates why this matters: the hedge remains approximately −100 underlying units when spot moves from 100 to 110, and hedge trading is exactly zero in the recorded run. A change in the marked value of those already-held units is not hedge trading.

| Discriminating fixture | Reference result |
|---|---|
| Qualified unchanged spot/IV/time | Zero hedge trade |
| Long calls, spot100→105 | `H=−$4,681,848.775567`, underlying sale |
| Same book, spot100→95 | `H=+$4,494,315.053360`, underlying purchase |
| Increase lower-strike inventory, target105 | Sale grows to `$7,620,211.296964`; both strike sides matter |
| Same Gamma rows, different maturity books, target110 | Sales `$10,499,083.265595` versus `$18,763,049.691345` |
| Same Gamma rows, different IV books, target110 | Sales `$10,495,349.479204` versus `$18,336,240.089975` |
| Small shocks 0.1→0.0001 spot units | Whole-book local-approximation relative error falls from `6.17e-4` to `6.06e-7` |

Further fixtures cover long puts, signed-inventory reversal, position permutation and splitting, heterogeneous multipliers, monetary scaling, a locally Gamma-neutral book with nonzero finite rehedging, IV-only/time-only changes, and an analytic `d1=0` delta/Gamma anchor.

## Unknown is not zero

Every `Book` declares its underlying, currency and whether the supplied hypothetical population is complete. That declaration is not proof of actual market or dealer coverage. Scope validation precedes pricing: mixed/unknown currencies, mixed/unknown underlyings and missing/duplicate position identities reject aggregation even if an offending row also lacks IV.

Missing quantity, multiplier, strike, maturity, IV or option kind remains explicit. Unsupported exercise style, expired/zero-time scenarios, invalid volatility and nonfinite inputs also withhold the affected calculation. Complete totals remain null while eligible partial totals retain their narrower label and counts. Incomplete buckets and cumulative prefixes remain null. An unknown-strike row prevents claiming any complete cumulative prefix. An incomplete population prevents claiming complete totals even when all supplied rows price successfully.

A supplied, explicitly complete empty hypothetical book has zero exposure. Absent data or an empty incomplete population remains unknown. The no-move fixture with a missing IV correctly keeps the complete hedge total null while the eligible subset's known zero remains labeled partial.

## Review and adaptation limits

The native reviewer independently reproduced the final 83 assertions and found no remaining blocking issue in this bounded reference. Review exposed and resolved missing-target routing, generator consumption, scaled/aggregate overflow, mixed-band zero evidence and an ambiguous out-of-grid label. No review check wrote source, JSON or bytecode.

The pricing model is strictly European Black–Scholes with zero rates/dividends, positive remaining time and IV, and a scalar deliverable multiplier on one hedge underlying. American exercise, discrete dividends, adjusted/nonlinear deliverables, expiry limits, production surface dynamics, actual inventory reconstruction and operational data quality are not implemented. Numerical tail saturation is flagged in evaluated rows; a floating-point zero is not a claim of structurally zero economic exposure.

These reference outputs are **not drop-in extensions to strict production schemas**. Current pricing/FS-5 and conditional-producer owners must adapt the economic behavior to accepted models, data contracts, revisions and failure vocabulary; Terminal owners must retain truthful units and distinguish display modes. Existing B1/B2 carrier custody and consumer compatibility remain prerequisites. No endpoint result establishes path cash, turnover, execution, price impact, dealer positions or predictive alpha, and no test grants activation authority.
