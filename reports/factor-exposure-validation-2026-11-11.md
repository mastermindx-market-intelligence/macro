# Factor Exposure observation-alignment validation — 2026-11-11

## Outcome and scope

This report qualifies the source repair for [issue #11016](https://github.com/mastermindx-market-intelligence/macro/issues/11016). Returns are formed on their original source calendars before factor-availability filtering or estimation-window slicing. Each ticker uses a joint centered regression on its own finite observations within one shared factor basis. Models that lose identification on a ticker's support are omitted, so the existing RiskCore consumer counts those holdings as unmodeled.

The correction restores exact self-exposure for the stored SPY and Bitcoin series while retaining the same 1,538 modeled names. The paired historical Phase0 study renews the active confidence measurements below. It does not establish current market readings, predictive returns, trade sizing, statistical significance, or deployed behavior.

The factor history in these fixed inputs ends **2026-09-25**, although the stock cache extends through 2026-11-10. That cutoff is distinct from this execution date and from the evaluated rebalance span.

## Source and input identity

Baseline source and all 45 cached data files came from Macro commit [`82930233f83a2e62734e605becb1076508eefc31`](https://github.com/mastermindx-market-intelligence/macro/tree/82930233f83a2e62734e605becb1076508eefc31). The four baseline source blobs remained identical on receiving main `20197727622e5bf4da2e7306bf612fb533466250`. The candidate used the four replacements below; all remaining input bytes were held fixed. Git blob identities were verified before execution and reverified after the final tests.

| Candidate path | Baseline Git blob | Validated candidate Git blob |
|---|---|---|
| `engine/factor_exposure.py` | `52cc784da54d9a3c4659091f275a5c81851625ff` | `00a69b707e4d7ac4bbd79ed198ebf42f2573d76a` |
| `scripts/factor_exposure_phase0.py` | `3a8c28fb5fa0008c241e5483e115c372ecf1b336` | `91aefc16c60456018873fc25cfe66220b68de9dc` |
| `tests/test_factor_exposure.py` | `4948843f657bd4ee82010edd8a6325267320125e` | `38cb7bb9a3a63cb30e58df4a580b1ea745639cb3` |
| `tests/test_factor_exposure_stress.py` | `24eadd8f234d3f606fcf6d3f4cae1fd9df8ae850` | `d70d8e9df16764e264dbfc05ccb427df89b6dc6b` |

The original published report, `reports/factor-exposure-phase0.md` (blob `e5939a9988d426506ebf07db4183d64a72545749`), remains historical and unchanged. The paired baseline below is a new execution of the original estimator on the same frozen inputs as this candidate; it is distinct from that older published calibration.

Runtime: Python 3.14.7, NumPy 2.5.2, pandas 3.0.5, PyArrow 25.0.1. Inputs contain nine factors and 3,020 common factor rows, 2014-09-18 through 2026-09-25; the native stock panel contains 1,552 names and 776 rows, 2023-10-09 through 2026-11-10. Existing cache-merger behavior, factor ordering, coefficient caps, observation floors, and annualization conventions were retained. No market-data download was used.

## Paired native exporter

Both executions use the complete native `factor_frame → compute_exposure` path and strict JSON serialization.

| Quantity | Original source | Corrected source |
|---|---:|---:|
| Modeled names | 1,538 | 1,538 |
| Names added / removed | — | 0 / 0 |
| Export as-of | 2026-09-25 | 2026-09-25 |
| SPY market beta / raw market beta | 1.002 / 1.002 | 1.000 / 1.000 |
| SPY R² / annualized residual volatility | 1.000 / 0.001 | 1.000 / 0.000 |
| SPY observations | 251 | 252 |
| BTC crypto beta / raw crypto beta | 0.939 / 0.972 | 1.000 / 1.000 |
| BTC R² / annualized residual volatility | 0.870 / 0.161 | 1.000 / 0.000 |
| BTC observations | 251 | 252 |

BTC is itself a factor. Zero residual volatility for its exact self-fit is expected, while independent crypto variation can still produce positive residual risk. The retained noisy-crypto fixture checks that latter case.

Serialized export SHA-256 values:

- Original source: `67054ee3178a7edb3cc88c33db2f78299463f38b88c199b6aebd5f87ddc6bfce`.
- Corrected estimator before confidence-text refresh: `43951e0267703d76eba27496ec6e2dcf66dd240d70a76b67a378496429bf6194`.
- Final export with renewed confidence metadata: `dea48c614f1fa9b6ee082940078302090e47dfad8a680272c1b7298f2c6e3a6e`.

The final metadata edit left all numerical function ASTs unchanged. A fresh native export also verified equality of every payload field other than the intended `factors` metadata and explanatory `note`.

## Paired stability and confidence decision

Both runs use 252 finite factor observations for estimation, the next 63 for forward evaluation, minimum estimation support 126, coefficient cap ±5, seed 7, and 200 random equal-weight baskets per size/date. Basket sizes are 1, 5, 10, 20 and 40. The corrected forward sample excludes the rebalance anchor's return.

Both this baseline and the corrected run evaluated **20 monthly dates, 2024-10-31 through 2026-05-29**. Each factor has 20 valid persistence observations. Forward windows overlap; these are not 20 independent trials.

| Factor | Paired original persistence | Corrected persistence | Corrected K=1 → K=40 | Retained UI tier / scope |
|---|---:|---:|---:|---|
| Market | 0.670 | 0.676 | 0.703 → 0.671 | high / single |
| Growth | 0.446 | 0.448 | 0.446 → 0.519 | high / single |
| Size | 0.524 | 0.527 | 0.543 → 0.466 | high / single |
| Rates | 0.323 | 0.324 | 0.323 → 0.277 | medium / single |
| USD | 0.090 | 0.093 | 0.099 → 0.092 | low / low |
| Oil | 0.220 | 0.219 | 0.231 → 0.456 | medium / book |
| China | 0.140 | 0.132 | 0.120 → 0.129 | low / low |
| Bitcoin | 0.035 | 0.039 | 0.044 → 0.119 | low / low |
| Gold | 0.104 | 0.103 | 0.080 → 0.125 | low / low |

The existing qualitative ordering remains supported by these relative historical measurements: market, size and growth have the strongest individual persistence; rates has moderate individual persistence; oil has weaker individual persistence and the strongest measured endpoint improvement for larger baskets. The remaining factors stay low-confidence context. Gold is now measured rather than untested.

These are descriptive presentation tiers, without new automatic numerical cutoffs. Aggregation is not uniformly beneficial: size, rates and USD do not improve between these endpoints. Growth and Bitcoin also improve, but Bitcoin remains weak. No significance or universal monotonicity claim is made; gold's K=20 value, 0.168, exceeds its K=40 value.

Across the same 1,503 stocks, median nested R² changes from market/style/full **0.068 / 0.178 / 0.220** to **0.068 / 0.178 / 0.221**. Corrected median within-stock style and remaining-factor additions are **0.089** and **0.033**; these are not differences between the separately reported model medians. The median naive/model factor-variance ratio changes from approximately **1.67×** to **1.68×**.

## Executed regression and consumer proof

The final source passes **57 tests**:

```bash
python -m pytest tests/test_factor_exposure.py tests/test_factor_exposure_stress.py tests/test_risk_core_js.py -q
```

The final run uses the normal repository `conftest.py`, actual cached data, real engine imports and real JavaScript consumers. The store-dependent tests execute against the populated inputs. A separate Python 3.12 fixture run also passed all 57 tests before the metadata-only refresh.

Coverage includes original daily-return intervals across factor-date holes; the first retained return's predecessor; one finite support for coefficients, R² and residual risk; joint coefficient recovery when missingness destroys full-window orthogonality; constant and collinear support-loss omission; coefficient-cap residual accounting; common calm/stress factor basis; native equity/crypto source calendars; strict JSON; exact self-factor identities; and the Phase0 forward boundary and actual fitted-date count.

The complete unchanged `site/factor_exposure.js` runs through its public `FX.setAutoWeights` entry with controlled external JSON and a minimal DOM shell. Both English and Chinese versions display **−5.0%** for the exact two-name market-tracking book under the market −5% scenario. The actual `RiskCore.book` consumes market beta 1. The actual `RiskCore.coverage` counts an unidentified holding as unmodeled and abstains when its dollar share exceeds the existing threshold. Mode, provenance and universe fields retain their existing contracts.

This is native consumer-output proof, not browser pixels, layout, authentication, a live account, or deployment proof. The existing `wri-risk-core` CODE owner already executes the affected test files and broader consumer contracts; its required hosted results remain part of PR release qualification. No test owner or CI policy is added or relaxed.

## Reproduction

Use separate isolated source directories for the original and candidate versions. Materialize the exact baseline input blobs in the manifest below, then replace only the four candidate source files. Run the focused pytest command above, `compute_exposure()` with strict JSON serialization, and:

```bash
python -m scripts.factor_exposure_phase0 --win 252 --horizon 63 --min-obs 126 --max-abs 5 --n-baskets 200
```

Run Phase0 in a fresh Python process so its existing seeded generator starts at seed 7. Preserve each run's generated report separately. The script writes its normal report path inside that isolated directory; this evidence does not replace the historical report in the repository.

## Baseline input manifest

Every row is a Git blob from the fixed input commit above. The four candidate replacements are identified separately. This list is sufficient to reconstruct the cached inputs without substituting newer data.

| Path | Git blob | Bytes |
|---|---|---:|
| `config.yml` | `5be75249c98033d7ee0fbe55928713b1f50af627` | 496073 |
| `engine/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 |
| `engine/factor_exposure.py` | `52cc784da54d9a3c4659091f275a5c81851625ff` | 30403 |
| `engine/equity_factors.py` | `74a5dbb280b7060d86c9e8ed6cd58e0df950e4a2` | 39495 |
| `engine/validation.py` | `c9a09740cd630f920e52fd21b88ff36ff31366b6` | 71729 |
| `lib/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | 0 |
| `lib/config.py` | `b6fc888269876242597da354aaa726c20ed95802` | 1131 |
| `lib/store.py` | `3a0985944f534be7d771c926d73eb49f53aba140` | 33048 |
| `lib/closes_panel.py` | `f36b47e9d10590c3d750cbce7f5646f504794b64` | 25166 |
| `lib/nyse_calendar.py` | `0ece6439ffe4b081ee7a268fe99b69e1de1216a3` | 29814 |
| `scripts/__init__.py` | `dafbbd0c3a49c56a2635c0d3d8918302d10689a6` | 2217 |
| `scripts/factor_exposure_phase0.py` | `3a8c28fb5fa0008c241e5483e115c372ecf1b336` | 14435 |
| `tests/conftest.py` | `b2d40ef0eebddcfa3b4292a0d1cd296563222cdc` | 34456 |
| `tests/test_factor_exposure.py` | `4948843f657bd4ee82010edd8a6325267320125e` | 12335 |
| `tests/test_factor_exposure_stress.py` | `24eadd8f234d3f606fcf6d3f4cae1fd9df8ae850` | 14288 |
| `tests/test_risk_core_js.py` | `b6ca3a310ae21ef265f7dffb4d8d22f67fdfbd1e` | 21435 |
| `templates/risk_core.js` | `2ab3f1836688df62f97f25af34b80b3c56614d7c` | 22892 |
| `site/risk_core.js` | `2ab3f1836688df62f97f25af34b80b3c56614d7c` | 22892 |
| `site/factor_exposure.js` | `4cb22439f45f4057d34e46041df9f55f85acde55` | 21589 |
| `data/yahoo/BTC-USD.parquet` | `4d1b6fbc3228ec54c4dc1a9f5712963fab6d8e99` | 140346 |
| `data/yahoo/COIN.parquet` | `0336e13d3bcf4fcaf3e97b9fb7916008a99d2b5c` | 43082 |
| `data/yahoo/DX-Y.NYB.parquet` | `f080fa8a3694e3a36d8d25d3910a72341dcd1588` | 214689 |
| `data/yahoo/EMB.parquet` | `d7dac478455c6cfd044f1a37d0f0dc649a2fa401` | 124671 |
| `data/yahoo/ETH-USD.parquet` | `6c5ec0ba4ffea8007649ce5528d433ee73d6f869` | 104311 |
| `data/yahoo/ETHA.parquet` | `e9fb5adc18b04a186f2dcbe3d98b0759474ff8e9` | 18889 |
| `data/yahoo/FXI.parquet` | `1bb6a11d45840c1591522fe5ec6dbee0b5b24fec` | 149904 |
| `data/yahoo/GC_F.parquet` | `a49ae302cc42914c624a011fe047c6e965350fdd` | 157104 |
| `data/yahoo/HYG.parquet` | `4a09c5a9e2884fdb3375333b4b8c41956808ecd2` | 129115 |
| `data/yahoo/IBIT.parquet` | `9060f249936938a23508be4ab1a5149bcdf535da` | 22899 |
| `data/yahoo/IEF.parquet` | `bcb98a8d7d053f7a9767e1e736e9e3566f6815f1` | 156559 |
| `data/yahoo/IJH.parquet` | `078da8e278dd24a9bd7f8dc60822e1207c26f6f6` | 185575 |
| `data/yahoo/IWD.parquet` | `9fd8d9d6460dec1dbf6081e7ec2f5fb6197d74eb` | 182830 |
| `data/yahoo/IWF.parquet` | `45309f345188b3ce0d53beaa7a482856e2bd4fe8` | 183731 |
| `data/yahoo/IWM.parquet` | `4930b10b16344ce39df788d2cae65c0149c5b0e3` | 192826 |
| `data/yahoo/LQD.parquet` | `fd06266ef3029e2e0706bb192373831ebef378cb` | 156203 |
| `data/yahoo/MTUM.parquet` | `7d7155c402c88d61dfcf0142603e41e46f5d78f8` | 95690 |
| `data/yahoo/QQQ.parquet` | `16f4c8f193d8910e66476814373f5bc1edaac18b` | 201942 |
| `data/yahoo/QUAL.parquet` | `0959c48ac976f0ec5cb327ff2ecc52c0865818a5` | 93638 |
| `data/yahoo/RSP.parquet` | `c3a37f29645ca947c8161a129632e4971511bad1` | 164079 |
| `data/yahoo/SMH.parquet` | `392f0c0b4570979748a1bc3d88f3fa1345f1e9c1` | 179850 |
| `data/yahoo/SPHB.parquet` | `8d5ce720c473a52c9ffc07f517c1ab96d7b6994a` | 102393 |
| `data/yahoo/SPLV.parquet` | `63d1ea75abae3cb84c6e422ba49ce8e8f241ae9b` | 104888 |
| `data/yahoo/SPY.parquet` | `d73be3d49b2a43359a226f872e5f8274a830735c` | 245142 |
| `data/yahoo/TIP.parquet` | `d4cb8098a557df19c1d7fd356ca533211cc9709a` | 143711 |
| `data/yahoo/TLT.parquet` | `e25585dfa4b698f358c8b37c7f7f7c854decc660` | 166359 |
| `data/yahoo/USMV.parquet` | `4379f77c0cf1ca93537b8e84b14deb056ad8eefe` | 102546 |
| `data/yahoo/XLB.parquet` | `3039f8f7787bc77b9263288652a6cc2a6e63995a` | 188631 |
| `data/yahoo/XLC.parquet` | `31cccc2cc40d48ace791a9d2d0a14cedc4bb6a75` | 60916 |
| `data/yahoo/XLE.parquet` | `98051f60dc2038084ffbbdac215ce38fa7957ed8` | 194181 |
| `data/yahoo/XLF.parquet` | `73fa89292c47a4a64cc4843cf4ba67135de4da21` | 189590 |
| `data/yahoo/XLI.parquet` | `8f9692e5b211696b43d2c158f0d49e62b33a4d1f` | 189760 |
| `data/yahoo/XLK.parquet` | `36963d9254918bb59c18fdde9f57d66bc0cd5a13` | 190546 |
| `data/yahoo/XLP.parquet` | `dcada432770b5a5c51e5c393551e30cf2d83a151` | 182065 |
| `data/yahoo/XLRE.parquet` | `bdb072edee4130d4b7fb5cc92a10239a9c8c8736` | 73054 |
| `data/yahoo/XLU.parquet` | `02348245da57f7d4054dbd7be273dd6f4e1440f2` | 186913 |
| `data/yahoo/XLV.parquet` | `098fc81d2a7a7f9b469bb188466d9c1b28fa4e0a` | 184820 |
| `data/yahoo/XLY.parquet` | `2a11c7cde52fec52a821b16de5919e7b1f267445` | 190206 |
| `data/commodity/signals_oil.parquet` | `1ae47157839dac157367940068d71df3951d6a0a` | 876065 |
| `data/breadth/_closes_cache.parquet` | `e0729db2deeef391a2d09c541f9ed602b845a12a` | 1701154 |
| `data/breadth/constituents.parquet` | `c903da727a238071bcc15351a970bfe7524bff74` | 12696 |
| `data/smallcap_breadth/_closes_cache.parquet` | `7c5c7713c5c28bd256d1b433a696417d27272f8f` | 3350709 |
| `data/smallcap_breadth/constituents.parquet` | `31bc18351829ef61085d158ac2fec55e5b69485b` | 16293 |
| `data/midcap_breadth/_closes_cache.parquet` | `dc5277ab06217baf6c84b2143d6a16f72749eeca` | 2320467 |
| `data/midcap_breadth/constituents.parquet` | `af08b5c476345ec16a42a2976024213bf2b80343` | 10949 |

## Corrected generated Phase0 report

The following is the final renderer's output, SHA-256 `98118fff7cc10af6ae8e07330b247d37129e3233e1f23c46be0fdf4248d7d956`.

# Factor-exposure engine — Phase 0 validation

*Generated by `scripts/factor_exposure_phase0.py`. This is a MEASUREMENT tool, not a predictive signal — the gate is collinearity control + out-of-sample beta STABILITY, not IC/FDR/DSR. Working assumption under test: trust the portfolio aggregate, not a single stock's secondary beta.*

Factor observations: 3020 rows, 2014-09-18..2026-09-25. Fit 252 returns; forward 63 returns; minimum fit support 126; coefficient cap ±5. Random baskets: 200 per size/date, seed 7. The forward sample excludes the rebalance anchor's return.

## 1. Collinearity — why a univariate beta table double-counts

VIF per factor (>5 redundant, >10 severe) on the RAW factors vs after orthogonalization:

| factor | raw VIF | orthogonalized VIF |
|---|--:|--:|
| Market | 13.53 | 1.0 |
| Growth / Tech | 8.42 | 1.0 |
| Small-cap | 4.26 | 1.0 |
| Rates (duration) | 1.13 | 1.0 |
| US Dollar | 1.23 | 1.0 |
| Oil / energy | 1.03 | 1.0 |
| China | 1.45 | 1.0 |
| Bitcoin / crypto | 1.08 | 1.0 |
| Gold | 1.21 | 1.0 |

Most-correlated raw factor pairs: mkt–growth 0.93, mkt–size 0.86, growth–size 0.77, mkt–china 0.53, growth–china 0.52, size–china 0.49, usd–gold 0.39.

**Variance ratio:** treating univariate exposures as independent gives a median naive/model factor-variance ratio of **1.68×** (p90 2.79×) across 1503 stocks. A ratio above one indicates overstatement; below one indicates understatement.

## 2. Out-of-sample beta stability (single-stock)

Span 2024-10-31..2026-05-29 · 20 monthly rebalances · estimate on 252 finite factor observations, realize on the next 63. Forward windows overlap; these are not independent trials. Cross-sectional rank correlation between in-sample and next-period beta (1 = perfectly persistent, 0 = no rank association):

| factor | persistence | n |
|---|--:|--:|
| Market | 0.676 | 20 |
| Growth / Tech | 0.448 | 20 |
| Small-cap | 0.527 | 20 |
| Rates (duration) | 0.324 | 20 |
| US Dollar | 0.093 | 20 |
| Oil / energy | 0.219 | 20 |
| China | 0.132 | 20 |
| Bitcoin / crypto | 0.039 | 20 |
| Gold | 0.103 | 20 |

## 3. Aggregation denoising — does the portfolio aggregate firm up?

Same persistence, but for random equal-weight books of K names (mean beta). Compare each size with K=1; improvement must be measured, not assumed:

| factor | K=1 | K=5 | K=10 | K=20 | K=40 |
|---|--:|--:|--:|--:|--:|
| Market | 0.703 | 0.683 | 0.633 | 0.657 | 0.671 |
| Growth / Tech | 0.446 | 0.523 | 0.518 | 0.523 | 0.519 |
| Small-cap | 0.543 | 0.474 | 0.471 | 0.473 | 0.466 |
| Rates (duration) | 0.323 | 0.343 | 0.298 | 0.314 | 0.277 |
| US Dollar | 0.099 | 0.105 | 0.078 | 0.107 | 0.092 |
| Oil / energy | 0.231 | 0.382 | 0.423 | 0.441 | 0.456 |
| China | 0.12 | 0.119 | 0.118 | 0.092 | 0.129 |
| Bitcoin / crypto | 0.044 | 0.083 | 0.097 | 0.105 | 0.119 |
| Gold | 0.08 | 0.113 | 0.124 | 0.168 | 0.125 |

## 4. Explanatory power (nested R²)

Median single-stock R² over 1503 names: market-only **0.068** → +style (growth, size) **0.178** → +remaining factors **0.221**. Style adds a median **0.089**; the remaining factors add a median **0.033** (p90 0.082). These are in-sample explanatory changes, not evidence of forward beta stability.

---

**How to read.** §1 measures collinearity and the variance difference between the two models. §2 reports single-stock beta persistence on the evaluated dates. §3 tests whether aggregation improves that persistence; a flat or weaker result does not support a denoising claim. Interpret each factor against its measured values and sample size. This historical measurement does not establish predictive performance or future stability.

