# Theta EOD retrospective association — research receipt

## Findings and decision

All **60/60** registered cells met the frozen support floors. **Three** rejected the null under the single 60-cell BH family at alpha 0.10; the other 57 did not. Failure to reject is inconclusive evidence, not proof of a zero effect.

- Normalized GEX versus subsequent underlying realized volatility was negative in 2017–2019 at both 5 sessions (mean IC −0.105245, BH q  0.00000389631) and 21 sessions (−0.114298, q 0.0289418). Neither horizon survived the correction in 2020–2022 or 2023–2025.
- CW IV-spread level versus subsequent SPY-excess underlying returns survived only in 2023–2025 at 21 sessions (mean IC +0.063404, 95% HAC interval [0.0202773,0.106531], BH q  0.0802663). This is an era-specific retrospective rank association, not a forecast return or executable option profit.
- No contrast/horizon survives BH in all three eras. Vanna, Charm, Vanna relief, IV-spread change, skew acceleration, term slope, OI change, and the momentum baseline supply no family-adjusted rejection in this run. The 21-session cells have only 33–34 non-overlapping label blocks, modestly above the minimum 30.

The bounded research receipt is complete. **Historical alpha remains unvalidated; PIT is unproven.** These results do not justify a fused score, model fit, runtime signal, sizing or trading change. The parent Options Alpha product issue remains open. Earlier episode-only proxy results are a separate accepted 36-cell receipt, not pooled into this family.

**Frozen protocol:** `67011db3d3aed08827f027cafc5b5a2bf890289a1017b227cad15fc240826e68`  
**Source head:** `07186d356cf2a3ef9d24a2d17fe60bd397f570cd`  
**Result SHA-256:** `7af1b1ae1c871892384388695d17977cea1a6b6aa4fd21fc1625b5dad55073f3`  
**Manifest SHA-256:** `6b678a65f531eb31735cca7641b898887739475a9c1a479c2a0ebbecd8a164dc`  
**Independent receipt SHA-256:** `c9c5c9e92f3fd22a1c17f93d580598abf04259668758816248508f39c31a118f`  
**Reproducer SHA-256:** `444f435eb8b0780ba89de12024170f3371a306d2435a75e7a0d0f1a722a5ad61`  
**Bound source-digest entries:** `1740`

## Support and registered-cell accounting

- Selected inputs: **429 present**, **6 explicit missing** of 435 expected slots.
- Registered cells: **60**; evaluable: **60**; non-evaluable: **0**; BH within-run rejections: **3**.
- Fixed design: 10 contrasts × 3 eras (Era1, Era2, Era3, 2017–2025) × two horizons (5, 21 NYSE sessions).
- Population: SPY benchmark-only; SPX/SPXW coverage-only; 20 nominal scored roots, 18 price-available roots under the frozen protocol.
- This receipt changes no runtime behavior or authority.

## All registered cells

| Contrast | Era | H | IC dates | Blocks | Mean IC | 95% CI | Raw p | BH q | Paired momentum difference | State / reason |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---|
| GEX_NORM_TO_FWD_RV | Era1 | 5 | 748 | 125 | -0.105245 | [-0.143088, -0.0674027] | 6.49385e-08 | 3.89631e-06 | -0.0538425 | EVALUABLE |
| VEX_NORM_TO_SPY_EXCESS | Era1 | 5 | 748 | 125 | -0.00859294 | [-0.0415346, 0.0243487] | 0.608737 | 0.951753 | 0.0350581 | EVALUABLE |
| CEX_NORM_TO_SPY_EXCESS | Era1 | 5 | 748 | 125 | 0.0179337 | [-0.0118443, 0.0477118] | 0.237464 | 0.951753 | 0.0614592 | EVALUABLE |
| VANNA_RELIEF_TO_SPY_EXCESS | Era1 | 5 | 743 | 124 | 0.00636227 | [-0.0265411, 0.0392656] | 0.704349 | 0.951753 | 0.0484268 | EVALUABLE |
| CW_IVSPREAD_LEVEL_TO_SPY_EXCESS | Era1 | 5 | 748 | 125 | 0.0164131 | [-0.0157836, 0.0486098] | 0.317265 | 0.951753 | 0.0558972 | EVALUABLE |
| D5_CW_IVSPREAD_TO_SPY_EXCESS | Era1 | 5 | 743 | 124 | 0.0129722 | [-0.0145947, 0.0405391] | 0.355885 | 0.951753 | 0.0500556 | EVALUABLE |
| SKEW_ACCEL_TO_SPY_EXCESS | Era1 | 5 | 738 | 123 | -0.00914391 | [-0.0334619, 0.0151741] | 0.460636 | 0.951753 | 0.0327342 | EVALUABLE |
| TERM_SLOPE_TO_SPY_EXCESS | Era1 | 5 | 748 | 125 | 0.0287205 | [-0.0145967, 0.0720377] | 0.193447 | 0.941712 | 0.076006 | EVALUABLE |
| DOI5_TO_SPY_EXCESS | Era1 | 5 | 743 | 124 | -0.00622267 | [-0.0396686, 0.0272232] | 0.715028 | 0.951753 | 0.0361551 | EVALUABLE |
| MOM5_BASELINE_TO_SPY_EXCESS | Era1 | 5 | 748 | 125 | -0.0435662 | [-0.085639, -0.00149343] | 0.042423 | 0.318172 | — | EVALUABLE |
| GEX_NORM_TO_FWD_RV | Era1 | 21 | 732 | 34 | -0.114298 | [-0.182006, -0.0465897] | 0.000964727 | 0.0289418 | -0.111007 | EVALUABLE |
| VEX_NORM_TO_SPY_EXCESS | Era1 | 21 | 732 | 34 | -0.00838388 | [-0.0665462, 0.0497785] | 0.777265 | 0.951753 | 0.0498666 | EVALUABLE |
| CEX_NORM_TO_SPY_EXCESS | Era1 | 21 | 732 | 34 | 0.0431995 | [-0.00146335, 0.0878624] | 0.0579723 | 0.386482 | 0.10123 | EVALUABLE |
| VANNA_RELIEF_TO_SPY_EXCESS | Era1 | 21 | 727 | 34 | 0.00905902 | [-0.0242367, 0.0423548] | 0.593399 | 0.951753 | 0.0630883 | EVALUABLE |
| CW_IVSPREAD_LEVEL_TO_SPY_EXCESS | Era1 | 21 | 732 | 34 | 0.00762346 | [-0.034537, 0.0497839] | 0.7227 | 0.951753 | 0.0593633 | EVALUABLE |
| D5_CW_IVSPREAD_TO_SPY_EXCESS | Era1 | 21 | 727 | 34 | 0.00657521 | [-0.0148566, 0.028007] | 0.547152 | 0.951753 | 0.0551722 | EVALUABLE |
| SKEW_ACCEL_TO_SPY_EXCESS | Era1 | 21 | 722 | 33 | -0.00108821 | [-0.0191078, 0.0169314] | 0.905655 | 0.963617 | 0.057219 | EVALUABLE |
| TERM_SLOPE_TO_SPY_EXCESS | Era1 | 21 | 732 | 34 | 0.073614 | [0.00487697, 0.142351] | 0.0358503 | 0.307288 | 0.13229 | EVALUABLE |
| DOI5_TO_SPY_EXCESS | Era1 | 21 | 727 | 34 | -0.0180299 | [-0.051776, 0.0157162] | 0.294563 | 0.951753 | 0.0378628 | EVALUABLE |
| MOM5_BASELINE_TO_SPY_EXCESS | Era1 | 21 | 732 | 34 | -0.0580648 | [-0.104186, -0.0119435] | 0.0136775 | 0.16413 | — | EVALUABLE |
| GEX_NORM_TO_FWD_RV | Era2 | 5 | 750 | 125 | -0.0276849 | [-0.0704378, 0.015068] | 0.204038 | 0.941712 | 0.00410151 | EVALUABLE |
| VEX_NORM_TO_SPY_EXCESS | Era2 | 5 | 750 | 125 | -0.00434361 | [-0.0459612, 0.037274] | 0.837712 | 0.959928 | -0.0160605 | EVALUABLE |
| CEX_NORM_TO_SPY_EXCESS | Era2 | 5 | 750 | 125 | -0.00996784 | [-0.0419425, 0.0220068] | 0.540729 | 0.951753 | -0.0216848 | EVALUABLE |
| VANNA_RELIEF_TO_SPY_EXCESS | Era2 | 5 | 750 | 125 | -0.00453339 | [-0.0356735, 0.0266067] | 0.775115 | 0.951753 | -0.0138696 | EVALUABLE |
| CW_IVSPREAD_LEVEL_TO_SPY_EXCESS | Era2 | 5 | 749 | 125 | -0.0048996 | [-0.0360289, 0.0262297] | 0.757416 | 0.951753 | -0.0182629 | EVALUABLE |
| D5_CW_IVSPREAD_TO_SPY_EXCESS | Era2 | 5 | 748 | 125 | -0.00497357 | [-0.0289064, 0.0189593] | 0.683414 | 0.951753 | -0.0215456 | EVALUABLE |
| SKEW_ACCEL_TO_SPY_EXCESS | Era2 | 5 | 750 | 125 | 0.00672464 | [-0.0130792, 0.0265285] | 0.505229 | 0.951753 | -0.00403726 | EVALUABLE |
| TERM_SLOPE_TO_SPY_EXCESS | Era2 | 5 | 750 | 125 | -0.00347386 | [-0.0390265, 0.0320788] | 0.847936 | 0.959928 | -0.0227881 | EVALUABLE |
| DOI5_TO_SPY_EXCESS | Era2 | 5 | 750 | 125 | 0.00157407 | [-0.0258958, 0.029044] | 0.910464 | 0.963617 | -0.0101429 | EVALUABLE |
| MOM5_BASELINE_TO_SPY_EXCESS | Era2 | 5 | 750 | 125 | 0.0117169 | [-0.0369908, 0.0604247] | 0.63689 | 0.951753 | — | EVALUABLE |
| GEX_NORM_TO_FWD_RV | Era2 | 21 | 734 | 34 | -0.0201899 | [-0.0974239, 0.057044] | 0.607961 | 0.951753 | 0.0165159 | EVALUABLE |
| VEX_NORM_TO_SPY_EXCESS | Era2 | 21 | 734 | 34 | 0.00305942 | [-0.0534859, 0.0596047] | 0.915436 | 0.963617 | -0.0173879 | EVALUABLE |
| CEX_NORM_TO_SPY_EXCESS | Era2 | 21 | 734 | 34 | -0.0423257 | [-0.0886595, 0.00400805] | 0.0733242 | 0.439945 | -0.062773 | EVALUABLE |
| VANNA_RELIEF_TO_SPY_EXCESS | Era2 | 21 | 734 | 34 | 0.00558898 | [-0.0227593, 0.0339373] | 0.698829 | 0.951753 | -0.0139536 | EVALUABLE |
| CW_IVSPREAD_LEVEL_TO_SPY_EXCESS | Era2 | 21 | 733 | 34 | -0.0058867 | [-0.0542996, 0.0425262] | 0.811394 | 0.959928 | -0.0267566 | EVALUABLE |
| D5_CW_IVSPREAD_TO_SPY_EXCESS | Era2 | 21 | 732 | 34 | 0.00836832 | [-0.0163387, 0.0330753] | 0.506295 | 0.951753 | -0.0111875 | EVALUABLE |
| SKEW_ACCEL_TO_SPY_EXCESS | Era2 | 21 | 734 | 34 | 0.0125756 | [-0.00260228, 0.0277535] | 0.10425 | 0.568634 | -0.00564617 | EVALUABLE |
| TERM_SLOPE_TO_SPY_EXCESS | Era2 | 21 | 734 | 34 | 0.00826556 | [-0.0396431, 0.0561742] | 0.734928 | 0.951753 | -0.0138464 | EVALUABLE |
| DOI5_TO_SPY_EXCESS | Era2 | 21 | 734 | 34 | -0.00658844 | [-0.041566, 0.0283891] | 0.711644 | 0.951753 | -0.0270358 | EVALUABLE |
| MOM5_BASELINE_TO_SPY_EXCESS | Era2 | 21 | 734 | 34 | 0.0204473 | [-0.0368001, 0.0776948] | 0.483397 | 0.951753 | — | EVALUABLE |
| GEX_NORM_TO_FWD_RV | Era3 | 5 | 746 | 125 | -0.0110607 | [-0.0581633, 0.0360418] | 0.644939 | 0.951753 | -0.036371 | EVALUABLE |
| VEX_NORM_TO_SPY_EXCESS | Era3 | 5 | 746 | 125 | -0.00401055 | [-0.0378734, 0.0298523] | 0.816208 | 0.959928 | 0.00745254 | EVALUABLE |
| CEX_NORM_TO_SPY_EXCESS | Era3 | 5 | 746 | 125 | 0.0312529 | [0.00410941, 0.0583963] | 0.0240863 | 0.240863 | 0.042716 | EVALUABLE |
| VANNA_RELIEF_TO_SPY_EXCESS | Era3 | 5 | 746 | 125 | 0.0125178 | [-0.0126857, 0.0377214] | 0.329858 | 0.951753 | 0.0215432 | EVALUABLE |
| CW_IVSPREAD_LEVEL_TO_SPY_EXCESS | Era3 | 5 | 746 | 125 | 0.0154348 | [-0.0183716, 0.0492412] | 0.37038 | 0.951753 | 0.0309658 | EVALUABLE |
| D5_CW_IVSPREAD_TO_SPY_EXCESS | Era3 | 5 | 746 | 125 | -0.00848847 | [-0.0332028, 0.0162258] | 0.500347 | 0.951753 | 0.00242322 | EVALUABLE |
| SKEW_ACCEL_TO_SPY_EXCESS | Era3 | 5 | 746 | 125 | 0.00392823 | [-0.0146922, 0.0225486] | 0.67888 | 0.951753 | 0.0144945 | EVALUABLE |
| TERM_SLOPE_TO_SPY_EXCESS | Era3 | 5 | 746 | 125 | -0.00107418 | [-0.0358635, 0.0337151] | 0.951682 | 0.972241 | 0.00506353 | EVALUABLE |
| DOI5_TO_SPY_EXCESS | Era3 | 5 | 746 | 125 | -0.015455 | [-0.0455206, 0.0146106] | 0.313233 | 0.951753 | -0.00402283 | EVALUABLE |
| MOM5_BASELINE_TO_SPY_EXCESS | Era3 | 5 | 746 | 125 | -0.0114321 | [-0.0609858, 0.0381215] | 0.65075 | 0.951753 | — | EVALUABLE |
| GEX_NORM_TO_FWD_RV | Era3 | 21 | 730 | 34 | -0.00756641 | [-0.0962441, 0.0811113] | 0.867014 | 0.963349 | -0.0621199 | EVALUABLE |
| VEX_NORM_TO_SPY_EXCESS | Era3 | 21 | 730 | 34 | -0.013849 | [-0.0659851, 0.038287] | 0.60218 | 0.951753 | -0.0122576 | EVALUABLE |
| CEX_NORM_TO_SPY_EXCESS | Era3 | 21 | 730 | 34 | 0.0473956 | [0.0130119, 0.0817794] | 0.0069656 | 0.104484 | 0.0489871 | EVALUABLE |
| VANNA_RELIEF_TO_SPY_EXCESS | Era3 | 21 | 730 | 34 | -0.00529649 | [-0.0403053, 0.0297124] | 0.766539 | 0.951753 | -0.00511773 | EVALUABLE |
| CW_IVSPREAD_LEVEL_TO_SPY_EXCESS | Era3 | 21 | 730 | 34 | 0.063404 | [0.0202773, 0.106531] | 0.00401331 | 0.0802663 | 0.0619816 | EVALUABLE |
| D5_CW_IVSPREAD_TO_SPY_EXCESS | Era3 | 21 | 730 | 34 | 0.0111274 | [-0.016661, 0.0389159] | 0.432041 | 0.951753 | 0.0100116 | EVALUABLE |
| SKEW_ACCEL_TO_SPY_EXCESS | Era3 | 21 | 730 | 34 | 0.00507183 | [-0.0104369, 0.0205806] | 0.521053 | 0.951753 | 0.00489042 | EVALUABLE |
| TERM_SLOPE_TO_SPY_EXCESS | Era3 | 21 | 730 | 34 | -0.0205169 | [-0.078209, 0.0371751] | 0.485289 | 0.951753 | -0.027156 | EVALUABLE |
| DOI5_TO_SPY_EXCESS | Era3 | 21 | 730 | 34 | -0.000599403 | [-0.0383408, 0.037142] | 0.975135 | 0.975135 | 0.00102351 | EVALUABLE |
| MOM5_BASELINE_TO_SPY_EXCESS | Era3 | 21 | 730 | 34 | -0.00162291 | [-0.0593989, 0.0561531] | 0.956037 | 0.972241 | — | EVALUABLE |

## Root coverage and reason counts

| Root | Price reason | Feature support | H=5 reasons | H=21 reasons |
|---|---|---|---|---|
| ARKK | PRICE_FILE_MISSING | cw_ivspread=1655, d5_cw_ivspread=1571, doi5=1959, mom5=0, net_charm_norm=1959, net_gamma_norm=1959, net_vanna_norm=1959, skew_accel=1867, term_slope=1536, vanna_relief=1827 | ERA_BOUNDARY_PURGE=18, ROOT_PRICE_UNAVAILABLE=2244 | ERA_BOUNDARY_PURGE=66, ROOT_PRICE_UNAVAILABLE=2196 |
| DIA | PRICE_FILE_MISSING | cw_ivspread=2261, d5_cw_ivspread=2255, doi5=2257, mom5=0, net_charm_norm=2262, net_gamma_norm=2262, net_vanna_norm=2262, skew_accel=2252, term_slope=2234, vanna_relief=2257 | ERA_BOUNDARY_PURGE=18, ROOT_PRICE_UNAVAILABLE=2244 | ERA_BOUNDARY_PURGE=66, ROOT_PRICE_UNAVAILABLE=2196 |
| IWM | OK | cw_ivspread=2260, d5_cw_ivspread=2253, doi5=2255, mom5=2262, net_charm_norm=2261, net_gamma_norm=2261, net_vanna_norm=2261, skew_accel=2249, term_slope=2261, vanna_relief=2255 | ERA_BOUNDARY_PURGE=18, EVALUABLE=2244 | ERA_BOUNDARY_PURGE=66, EVALUABLE=2196 |
| KRE | OK | cw_ivspread=2065, d5_cw_ivspread=1903, doi5=2255, mom5=2262, net_charm_norm=2261, net_gamma_norm=2261, net_vanna_norm=2261, skew_accel=2212, term_slope=2013, vanna_relief=2228 | ERA_BOUNDARY_PURGE=18, EVALUABLE=2244 | ERA_BOUNDARY_PURGE=66, EVALUABLE=2196 |
| NVDA | OK | cw_ivspread=2258, d5_cw_ivspread=2249, doi5=2257, mom5=2262, net_charm_norm=2262, net_gamma_norm=2262, net_vanna_norm=2262, skew_accel=2249, term_slope=2228, vanna_relief=2255 | ERA_BOUNDARY_PURGE=18, EVALUABLE=2244 | ERA_BOUNDARY_PURGE=66, EVALUABLE=2196 |
| QQQ | OK | cw_ivspread=2261, d5_cw_ivspread=2255, doi5=2257, mom5=2262, net_charm_norm=2261, net_gamma_norm=2261, net_vanna_norm=2261, skew_accel=2249, term_slope=2261, vanna_relief=2255 | ERA_BOUNDARY_PURGE=18, EVALUABLE=2244 | ERA_BOUNDARY_PURGE=66, EVALUABLE=2196 |
| SMH | OK | cw_ivspread=2255, d5_cw_ivspread=2243, doi5=2257, mom5=2262, net_charm_norm=2262, net_gamma_norm=2262, net_vanna_norm=2262, skew_accel=2252, term_slope=2053, vanna_relief=2241 | ERA_BOUNDARY_PURGE=18, EVALUABLE=2244 | ERA_BOUNDARY_PURGE=66, EVALUABLE=2196 |
| SOXX | OK | cw_ivspread=2148, d5_cw_ivspread=2069, doi5=2257, mom5=2262, net_charm_norm=2262, net_gamma_norm=2262, net_vanna_norm=2262, skew_accel=2249, term_slope=1680, vanna_relief=2061 | ERA_BOUNDARY_PURGE=18, EVALUABLE=2244 | ERA_BOUNDARY_PURGE=66, EVALUABLE=2196 |
| XBI | OK | cw_ivspread=2172, d5_cw_ivspread=2087, doi5=2257, mom5=2262, net_charm_norm=2262, net_gamma_norm=2262, net_vanna_norm=2262, skew_accel=2252, term_slope=2054, vanna_relief=2257 | ERA_BOUNDARY_PURGE=18, EVALUABLE=2244 | ERA_BOUNDARY_PURGE=66, EVALUABLE=2196 |
| XLB | OK | cw_ivspread=1573, d5_cw_ivspread=1150, doi5=2257, mom5=2262, net_charm_norm=2262, net_gamma_norm=2262, net_vanna_norm=2262, skew_accel=2131, term_slope=1689, vanna_relief=2148 | ERA_BOUNDARY_PURGE=18, EVALUABLE=2244 | ERA_BOUNDARY_PURGE=66, EVALUABLE=2196 |
| XLC | OK | cw_ivspread=1096, d5_cw_ivspread=739, doi5=1886, mom5=1890, net_charm_norm=1891, net_gamma_norm=1891, net_vanna_norm=1891, skew_accel=1606, term_slope=1347, vanna_relief=1646 | ERA_BOUNDARY_PURGE=18, EVALUABLE=1877, ROOT_FILL_UNAVAILABLE=367 | ERA_BOUNDARY_PURGE=66, EVALUABLE=1829, ROOT_FILL_UNAVAILABLE=367 |
| XLE | OK | cw_ivspread=2240, d5_cw_ivspread=2213, doi5=2257, mom5=2262, net_charm_norm=2261, net_gamma_norm=2261, net_vanna_norm=2261, skew_accel=2246, term_slope=2215, vanna_relief=2253 | ERA_BOUNDARY_PURGE=18, EVALUABLE=2244 | ERA_BOUNDARY_PURGE=66, EVALUABLE=2196 |
| XLF | OK | cw_ivspread=2241, d5_cw_ivspread=2215, doi5=2257, mom5=2262, net_charm_norm=2262, net_gamma_norm=2262, net_vanna_norm=2262, skew_accel=2252, term_slope=2204, vanna_relief=2257 | ERA_BOUNDARY_PURGE=18, EVALUABLE=2244 | ERA_BOUNDARY_PURGE=66, EVALUABLE=2196 |
| XLI | OK | cw_ivspread=2000, d5_cw_ivspread=1781, doi5=2257, mom5=2262, net_charm_norm=2262, net_gamma_norm=2262, net_vanna_norm=2262, skew_accel=2243, term_slope=1839, vanna_relief=2251 | ERA_BOUNDARY_PURGE=18, EVALUABLE=2244 | ERA_BOUNDARY_PURGE=66, EVALUABLE=2196 |
| XLK | OK | cw_ivspread=2221, d5_cw_ivspread=2177, doi5=2257, mom5=2262, net_charm_norm=2262, net_gamma_norm=2262, net_vanna_norm=2262, skew_accel=2249, term_slope=1923, vanna_relief=2255 | ERA_BOUNDARY_PURGE=18, EVALUABLE=2244 | ERA_BOUNDARY_PURGE=66, EVALUABLE=2196 |
| XLP | OK | cw_ivspread=1921, d5_cw_ivspread=1685, doi5=2257, mom5=2262, net_charm_norm=2262, net_gamma_norm=2262, net_vanna_norm=2262, skew_accel=2214, term_slope=1748, vanna_relief=2231 | ERA_BOUNDARY_PURGE=18, EVALUABLE=2244 | ERA_BOUNDARY_PURGE=66, EVALUABLE=2196 |
| XLRE | OK | cw_ivspread=1373, d5_cw_ivspread=1037, doi5=2257, mom5=2262, net_charm_norm=2262, net_gamma_norm=2262, net_vanna_norm=2262, skew_accel=2207, term_slope=1509, vanna_relief=2026 | ERA_BOUNDARY_PURGE=18, EVALUABLE=2244 | ERA_BOUNDARY_PURGE=66, EVALUABLE=2196 |
| XLU | OK | cw_ivspread=2139, d5_cw_ivspread=2028, doi5=2257, mom5=2262, net_charm_norm=2262, net_gamma_norm=2262, net_vanna_norm=2262, skew_accel=2243, term_slope=1825, vanna_relief=2251 | ERA_BOUNDARY_PURGE=18, EVALUABLE=2244 | ERA_BOUNDARY_PURGE=66, EVALUABLE=2196 |
| XLV | OK | cw_ivspread=2168, d5_cw_ivspread=2076, doi5=2257, mom5=2262, net_charm_norm=2261, net_gamma_norm=2261, net_vanna_norm=2261, skew_accel=2246, term_slope=1935, vanna_relief=2253 | ERA_BOUNDARY_PURGE=18, EVALUABLE=2244 | ERA_BOUNDARY_PURGE=66, EVALUABLE=2196 |
| XLY | OK | cw_ivspread=1957, d5_cw_ivspread=1712, doi5=2257, mom5=2262, net_charm_norm=2262, net_gamma_norm=2262, net_vanna_norm=2262, skew_accel=2228, term_slope=1760, vanna_relief=2241 | ERA_BOUNDARY_PURGE=18, EVALUABLE=2244 | ERA_BOUNDARY_PURGE=66, EVALUABLE=2196 |

## Root-year quality counters

| Counter | Value |
|---|---:|
| atm_iv_reason:ATM_NEAR_STRICT_REFUSAL | 532 |
| atm_iv_reason:NO_ONE_TO_ONE_JOINED_CONTRACTS | 5 |
| atm_iv_reason:NO_VALID_UNCROSSED_QUOTE | 7 |
| atm_iv_reason:OK | 44029 |
| cw_ivspread_reason:CW_INSUFFICIENT_STRICT_PAIRS | 4297 |
| cw_ivspread_reason:NO_ONE_TO_ONE_JOINED_CONTRACTS | 5 |
| cw_ivspread_reason:NO_VALID_UNCROSSED_QUOTE | 7 |
| cw_ivspread_reason:OK | 40264 |
| greeks_duplicate_rows_removed | 0 |
| greeks_empty_input | 2 |
| greeks_invalid_date_rows | 0 |
| greeks_invalid_identity_rows | 1428090 |
| greeks_non_session_rows | 24392 |
| greeks_raw_input_rows | 80635816 |
| greeks_root_mismatch_rows | 0 |
| greeks_unmatched_rows | 4687322 |
| greeks_valid_rows | 79207726 |
| joined_quote_excluded_rows | 31321453 |
| joined_rows | 74520404 |
| net_charm_norm_reason:NO_ONE_TO_ONE_JOINED_CONTRACTS | 5 |
| net_charm_norm_reason:NO_VALID_UNCROSSED_QUOTE | 7 |
| net_charm_norm_reason:OK | 44561 |
| net_gamma_norm_reason:NO_ONE_TO_ONE_JOINED_CONTRACTS | 5 |
| net_gamma_norm_reason:NO_VALID_UNCROSSED_QUOTE | 7 |
| net_gamma_norm_reason:OK | 44561 |
| net_vanna_norm_reason:NO_ONE_TO_ONE_JOINED_CONTRACTS | 5 |
| net_vanna_norm_reason:NO_VALID_UNCROSSED_QUOTE | 7 |
| net_vanna_norm_reason:OK | 44561 |
| oi_duplicate_rows_removed | 0 |
| oi_empty_input | 2 |
| oi_invalid_date_rows | 0 |
| oi_invalid_identity_rows | 2501484 |
| oi_non_session_rows | 25868 |
| oi_raw_input_rows | 77047303 |
| oi_root_mismatch_rows | 0 |
| oi_total_dates | 44569 |
| oi_unmatched_rows | 25415 |
| oi_valid_rows | 74545819 |
| skew_reason:NO_ONE_TO_ONE_JOINED_CONTRACTS | 5 |
| skew_reason:NO_VALID_UNCROSSED_QUOTE | 7 |
| skew_reason:OK | 44306 |
| skew_reason:SKEW_STRICT_DELTA_LEG_MISSING | 255 |
| term_slope_reason:NO_ONE_TO_ONE_JOINED_CONTRACTS | 5 |
| term_slope_reason:NO_VALID_UNCROSSED_QUOTE | 7 |
| term_slope_reason:OK | 38314 |
| term_slope_reason:TERM_STRICT_REFUSAL | 6247 |

## Unsupported matrix

- Cost status: not_estimable_and_not_applicable_to_the_primary_underlying_association. Daily EOD bid/ask is not an executable entry/exit NBBO path and the archive has no option fills, marks, fees, slippage or assignment lifecycle.

| Family | Recorded status |
|---|---|
| dark_pool_context | unsupported: absent from selected archive |
| executable_option_pnl_and_costs | unsupported: no entry/exit option marks/fills/cost model |
| fresh_final_oos | unsupported: selected history was already outcome-exposed |
| historical_known_at_or_vintage | unsupported: no availability or revision fields |
| intraday_5m_30m_2h | unsupported: daily archive only |
| measured_trade_flow_and_trade_sign | unsupported: no attributable trade tape/NBBO-at-trade path |
| model_training_calibration_or_serving | out of scope and prohibited by this protocol |

## Boundaries and reproduction

- PIT remains unproven. Fresh final OOS is unsupported because selected history was previously outcome-exposed.
- Exposure signs use the protocol’s long-call/short-put dealer-position assumption; this is a model assumption, not measured inventory.
- The root set is fixed. Survivorship, delisting and broader program-wide selection limits remain outside a within-run BH adjustment.
- Persistent root/sector identity and risk exposures are not neutralized. The paired momentum comparison is descriptive, not a formal conditional incremental-alpha test.
- Intraday paths, measured trade flow, executable option marks/costs, and dark-pool context remain as listed unsupported. The prior 36-cell episode proxy receipt is separate and is not pooled here.
- The independent artifact checker recomputes IC-series summaries, HAC, and BH from emitted IC series; it does not recompute every root/date Spearman IC from raw archive inputs. The producer replay below is the full-archive computation reproduction. Any separately recorded fixed-date feature/label/rank witness has only its declared spot-check scope.

Full immutable-archive replay (expensive):

```bash
cd /path/to/immutable-source-07186d356cf2a3ef9d24a2d17fe60bd397f570cd
PYTHONPATH="$PWD" python -m scripts.research.options_history_retrospective analyze --store /path/to/bound-theta-store --price-store /path/to/bound-price-store --protocol research/options_estate/theta_eod_retrospective_association_v1_1_protocol.json --manifest /path/to/archive-artifacts/options_theta_retrospective_20261002_manifest.json --manifest-sha 6b678a65f531eb31735cca7641b898887739475a9c1a479c2a0ebbecd8a164dc --out /outside/source/new-rerun.json
```

Standalone independent IC-summary/HAC/BH reproduction (artifact-only; uses the same frozen calendar/source):

```bash
cd /path/to/immutable-source-07186d356cf2a3ef9d24a2d17fe60bd397f570cd
PYTHONPATH="$PWD" python /path/to/archive-artifacts/options_theta_retrospective_20261002_reproduce.py /path/to/archive-artifacts/options_theta_retrospective_20261002_result.json research/options_estate/theta_eod_retrospective_association_v1_1_protocol.json --receipt /outside/source/independent-receipt.json
```

## Population, units and unattempted extensions

The manifest covers 429 present files and six explicit missing slots (10,195,107,902 bytes). Its 139,484,279 Greek rows, 133,703,957 OI rows and 118,954 adjusted-price rows count all selected source files, including SPX/SPXW coverage-only and SPY benchmark inputs. They are not the inferential sample size. The scored 20-root processing read 80,635,816 Greek rows and 77,047,303 OI rows, joined 74,520,404 contracts, and excluded 31,321,453 joined rows under quote/OI quality screens. These contract-row counts are also not independent observations. Per-cell IC dates, root-date pairs and non-overlapping blocks carry the analytic support.

There are 2262 canonical study dates. Each root's feature-support count above uses that denominator; its label counts separately include era-boundary and missing-price exclusions. DIA and ARKK never contribute a labeled pair. XLC has 367 unavailable fill dates. No missing native-price window was filled from a substitute source.

IC is a date-level cross-root Spearman correlation. GEX targets forward annualized underlying realized volatility; all other registered contrasts target underlying return minus SPY over the same complete native window. Their units and formulas are frozen in the protocol. The GEX paired momentum comparison uses the same realized-volatility target, not the return target. Neither paired baseline differences nor the Vanna ablation below have additional inferential tests.

Walls were not separately registered or tested. MOM5 is a price-only baseline, not an Options-derived feature. The three calendar eras are reporting partitions, not contemporaneously known regime labels. Broader technical indicators, formal sector-neutral effects, regime conditioning and other horizons were not evaluated by this 60-cell specification. Missing intraday/executable-option data and these unattempted extensions are different limitations.

## Paired Vanna ablation (descriptive only)

| Era | Horizon | Paired dates | Mean IC difference: relief minus VEX |
|---|---:|---:|---:|
| Era1 | 5 | 743 | 0.0172915608 |
| Era1 | 21 | 727 | 0.0178464177 |
| Era2 | 5 | 750 | -0.00199023439 |
| Era2 | 21 | 734 | 0.00555014728 |
| Era3 | 5 | 746 | 0.0201545809 |
| Era3 | 21 | 730 | 0.00987024486 |

## Execution, independent checks and source identity

Attempt 1 used computation source `a7ee15312486cac5992e2fb658135adff465939e` and manifest `fa1453f1de296150055eea27fce440722ff491f9083145ebd5e4d66c5cb8e3d3`. It computed cells internally but failed final JSON serialization because a pandas null diagnostic reason became a NaN mapping key. No valid result artifact was emitted, no numerical cell result was inspected, and final manifest reverification was not reached.

Attempt 2 used source `07186d356cf2a3ef9d24a2d17fe60bd397f570cd`. The only computational-source change was a null guard/string key for that diagnostic counter; the 50-session regression reproduced the original failure. All 435 input-manifest entry, protocol, calendar and runtime version was unchanged. The whole manifest hash changed solely because the helper source digest changed. Root matched all 1740 source entries to the committed retry head before execution. The retry completed with exit 0 in 1543.49 seconds and passed full input/source/runtime verification before and after computation. Its result was created atomically outside source and input paths.

The independent artifact checker verified all 60 IC summaries, support counts, full-calendar HAC uncertainty and BH results to absolute tolerance 1e-12. It consumes emitted IC series; it does not independently reconstruct every raw feature or rank. Separately, the original three fixed root/date witnesses matched normalized Greek and native-price label arithmetic at both horizons. A second raw-data audit used those same dates (2019-06-03,2021-04-06,2024-08-06) across all 20 roots and independently formed normalized GEX/VEX/CEX and average-rank Pearson ICs. All 18 selected cell-date ICs and root counts matched; touched input files remained manifest-identical before and after. These are spot audits, not full independent raw-archive replication.

Later delivery source `464d5d55197e3d2e2b58917658312bda67354750` adds only seven import-startup lines required by the repository's CI. It is not the computation source. Full archive replay must use the exact computation head and manifest above; using a later checkout with an old manifest correctly refuses a changed source digest. The runtime recorded in the manifest is Python 3.12.13, NumPy 2.5.1, pandas 3.0.5, SciPy 1.18.0 and PyArrow 25.0.0.

The scientific acceptance concerns this fixed retrospective package. Source publication and checks are tracked on [Macro PR #8286](https://github.com/mastermindx-market-intelligence/macro/pull/8286); this report grants no production authority. Studio access was recovered through the existing admitted route without changing security configuration. Execution deviations and both attempt identities are retained in the execution receipt.

## Evidence files

- [All 60 results and daily IC/paired series](options_theta_retrospective_20261002_result.json)
- [Exact frozen v1.1 protocol](options_theta_retrospective_20261002_protocol.json)
- [Retry input/source/runtime manifest](options_theta_retrospective_20261002_manifest.json)
- [Independent all-cell verification receipt](options_theta_retrospective_20261002_independent_receipt.json)
- [Standalone independent summary/HAC/BH verifier](options_theta_retrospective_20261002_reproduce.py)
- [Fixed-date raw feature/label arithmetic receipt](options_theta_retrospective_20261002_arithmetic_witness.json)
- [Executed arithmetic witness](options_theta_retrospective_20261002_arithmetic_witness.py)
- [Independent raw IC witness expectations](options_theta_retrospective_20261002_raw_ic_witness.json)
- [Executed raw IC witness](options_theta_retrospective_20261002_raw_ic_witness.py)
- [Hash-bound 18-cell-date comparison receipt](options_theta_retrospective_20261002_raw_ic_comparison.json)
- [Attempt manifest comparison](options_theta_retrospective_20261002_manifest_comparison.json)
- [Committed computation-source binding](options_theta_retrospective_20261002_source_binding.json)
- [Execution attempt and deviation record](options_theta_retrospective_20261002_execution.json)
- [Preserved first-attempt manifest](options_theta_retrospective_20261002_run1_manifest.json)
- [Preserved first-attempt arithmetic receipt](options_theta_retrospective_20261002_run1_arithmetic_witness.json)
- [Preserved first-attempt executed witness](options_theta_retrospective_20261002_run1_arithmetic_witness.py)

The delivered source also passed all 90 scoped research, Flow and import-hygiene tests (`90 passed in 37.27s`). Repository CI/review remain the separate publication gate tracked by PR #8286.

Raw-IC spot-audit receipt verification (artifact-only; the supplied raw witness itself was independently computed from the archive):

```bash
cd /path/to/archive-artifacts
python options_theta_retrospective_20261002_compare_raw_ic.py \
  --result options_theta_retrospective_20261002_result.json \
  --witness options_theta_retrospective_20261002_raw_ic_witness.json \
  --raw-script options_theta_retrospective_20261002_raw_ic_witness.py \
  --arithmetic-script options_theta_retrospective_20261002_arithmetic_witness.py \
  --out /outside/source/new-raw-ic-comparison.json
```

- [Raw-IC comparator](options_theta_retrospective_20261002_compare_raw_ic.py)
- [Executed comparator receipt](options_theta_retrospective_20261002_raw_ic_reproduction_receipt.json)
