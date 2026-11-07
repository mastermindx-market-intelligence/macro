# Kernel factorial findings -- exploratory, not a promoted strategy

The follow-on specification at `3ebbf18df3e1f359e08df1f6690409aa7247fa3c` was frozen before calculating the two crossed variants. The ETF panel had already been inspected in the first pilot; this is NOT independent validation or untouched out-of-sample evidence.

## What ran

Executed source `bd7a4c63a6ef74008b0796efe8ece553f2c7351c` added `factorial_kernel_pilot.py` and seventeen synthetic tests. The connected host verified all ten program source files, then passed **94 tests**: the prior 77 plus 17 new. The actual study reused all **2,730 parent events** unchanged and calculated **2,681 added variant events**. The ten saved input hashes matched the parent exactly; no new data source, outcome period, universe, macro threshold, cost, live policy or calendar was introduced.

The two-by-two comparison is:

| Input | Kernel A (12/26/9) | Kernel B (14/60/5) |
|---|---|---|
| Price close | Original raw price-MACD events, reused | Added research-only variant |
| Native RSI14 of close | Added research-only variant | Original raw Prophet RSI-MACD events, reused |

Each policy uses the existing 1D/2D/3D/completed-weekly definitions. The existing prior-session real-rate/participation states, next-session-close entry, H10 and assumed 20bp round-trip cost are unchanged. The 2007-start calendar amendment remains in force; this study does not repair that calendar or certify source availability.

5,411 is the total number of policy events now represented, NOT independent trades, independent market regimes or a portfolio sample size. Overlaps across policies, instruments and holding windows are intentional and retained in the joint entry-quarter inference.

## The primary regime x grain interaction

Define D = (3D hidden-fragility minus relief/broadening mean net SPY-excess return) minus (the same difference for 1D). Negative D points toward a worse relative 3D outcome in the hidden state. It is a comparison of policy-specific event populations, not paired identical admission dates or a causal experiment.

| Input / kernel | 2007-2014 D | 2015-2025 D | Combined D | Combined 95% interval |
|---|---:|---:|---:|---|
| Price / A | +0.3521 pp | -0.1912 pp | +0.0359 pp | [-1.2848, +1.1990] |
| Price / B | -0.1775 pp | -0.4501 pp | -0.3351 pp | [-1.6690, +0.9884] |
| RSI14 / A | -0.6191 pp | +0.0404 pp | -0.2257 pp | [-1.2359, +0.9916] |
| RSI14 / B | -0.4718 pp | -1.0992 pp | -0.8660 pp | [-1.8181, +0.0929] |

All four combined intervals include zero. Every era-specific D interval also includes zero. The original two policies' estimates and intervals reproduce exactly from their reused parent events; their outcomes were not recomputed or selected again.

## Holding the input or kernel fixed

The additional contrasts use the SAME sampled entry-quarter weights across all their component cells. The code differences sample statistics before computing intervals; it does not subtract marginal confidence-interval endpoints.

| Change, holding the other dimension fixed | Combined change in D | 95% interval |
|---|---:|---|
| Kernel B minus A, price input | -0.3710 pp | [-1.3248, +0.6541] |
| Kernel B minus A, RSI14 input | -0.6404 pp | [-1.5531, +0.2378] |
| RSI14 minus price input, kernel A | -0.2616 pp | [-1.5333, +1.0347] |
| RSI14 minus price input, kernel B | -0.5309 pp | [-1.9144, +0.7721] |

All four combined contrasts include zero. The twelve pre-specified era/combined contrast intervals also all include zero. The RSI-input kernel contrast is explicitly NOT era-stable: B-minus-A D is **+0.1473 pp in 2007-2014**, but **-1.1397 pp in 2015-2025**. This prevents a claim that a longer-memory kernel universally caused the weakness.

All component sample-support checks passed the declared twelve-entry-month/four-entry-quarter floor for these contrasts, and all 1,000 joint bootstrap draws were finite. Passing a support floor is not statistical significance, a rich-regime coverage certificate or a promotion gate.

## Interpretation that survives the test

The results do not identify a universally correct timeframe. They show why the initial comparison cannot be explained by timeframe alone: the signal input, smoothing parameters and event selection matter, and changing them changes the observed regime interaction.

The native RSI14/14-60-5 policy remains the strongest negative point estimate among this fixed four-policy comparison. That is a development clue, not permission to select the best-looking challenger, optimize more settings on these same events or infer that RSI itself is defective. The intervals remain wide and the crossed variants weaken a simple single-cause story.

Do not revise production from these tables. Do not replace 3D with 1D, install 12/26/9 everywhere, remove RSI, or promote the conspicuously positive weekly cell from the first pilot. The existing validated-take, candidate-universe, theme, catalyst, availability and portfolio layers were not replayed here.

## Consequence for the integrated program

Treat `input transform x kernel memory x sampling grain x observation basis x decision policy` as separate experiment dimensions. A live router keyed only by chart labels would conflate them. Future family/clock comparisons must hold the economic outcome horizon and population policy fixed, distinguish observation-at-the-time from finalized history, and quantify incremental information rather than count correlated bullish indicators.

The next research priority is not a larger blind grid search. It is the existing R1/R2 qualification and a new, predeclared matched-population candidate study through TOI/Evaluation, Rates/Regime and GMI. That study should test the specific sequence hypothesis -- fresh 2D reacceleration inside older constructive 3D -- separately from a new 3D crossover; measure theme leadership persistence and rotation speed rather than equating low breadth with churn; and retain both long-cycle and tactical strategy roles. None of those mechanisms was established by this ETF pilot.

The original program's ablation ladder and existing-owner boundaries remain in MASTER_PLAN. These new results narrow the scientific claim, not the product ambition. Model-generated prose, a larger test count and retrospective consistency do not substitute for qualified historical evidence, independent review or prospective candidate performance.

## Reproducibility and retained effects

Full result:
`/Volumes/Mastermind/research/prophet-regime-indicator-program-20261002/factorial-bd7a4c63a6ef/kernel-factorial-v1.json`
Bytes **1,713,102**; SHA-256 **`9d76c1b5301e73c9a0c446e35c12862a7952dfc28c01f4d0f2e53facf96fb11b`**.
Includes both complete kernel summaries, all added events, the joint factorial contrasts and component-support counts, source receipts, dependency/code identity and runtime versions.

Parent artifact remains unchanged at SHA-256 `ce0abe8268301b7f3ac9dee5dc6807e79d1644dd689007b29b2195197a402b9e`. The program compares the parent bytes before/after and verifies a semantic digest of the reused baseline rows. The result folder retains source-manifest, unit-test log, execution log and result receipt.

Factorial code SHA-256 `20763cb43957e6865e00a9f1a14a7e69160c1539184de2ae3c75fa54deeee104`; tests SHA-256 `2cb7c842eadea55b9db5e9b824e5d60f84c61a09a97458a35ffc1624b76aa940`. Exact executed commit `bd7a4c63a6ef74008b0796efe8ece553f2c7351c`.

No hosted-CI acceptance is implied by 94 connected-host tests. The independent discovery finding on #8303 still requires explicit enrollment in the existing code job and exact-head selection/execution proof. No worker, watcher, production mutation or autonomous continuation was created. No modifying effect is unresolved.
