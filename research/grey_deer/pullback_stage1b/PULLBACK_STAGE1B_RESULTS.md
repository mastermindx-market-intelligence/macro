# Pullback stage-1b panel results

- schema: `grey_deer_pullback_stage1b/v1`
- status: OK
- trial family `grey_deer_pullback_v11`, budget `66`
- dividend basis: unadjusted
- bootstrap: n_draws=10000 seed_root=221012 axis=date block_length_rule=stage-1 block_length(h, variant)

## Provenance

- manifest: `research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_V1_1_2026-10-12.md` version `1.1.0` blob `c52d93e98f4e4a776a7cf38fce46bcf4a84c52d7`
- prereg: `research/grey_deer/PULLBACK_PREREGISTRATION_V1_1_2026-10-12.md` blob `53837859164ab1d33785101dc0b464272acd5704`
- commit: `df7085bb351e4c6e49415191fb873259769c1780`
- script blob: `f615c089ba5c396c0578d94d5f4707de1717116b`
- test blob: `3bed87e6da07675dcc0ec9492996a9bdfd2cd0fc`
- adjust module blob: `60833bfae7fce1e9b2efaeea17c271fc9f91d119`
- subframe_sha256:
  - QQQ: `d6bd7575c5db3f0fb5d63e6baa2892a5a9d3610a8885562f8ead677a4444373f`
  - IWM: `ca2df002ee03ed68c19cd77e73b702c057be11f92435936b1f7d4fd57e218b8b`
  - DIA: `f11d142d015fca21c404e4a96524791d17ecaee4eb08f489f620ac47a753d618`
  - XLB: `0863d459e79a40b0943b2ced0aeea42801e81d9a989b8df07823ee6445055628`
  - XLC: `121c9b52c6ef4231540b73ad15362cf5927e7e5ae3c8df073ae231cbd158374d`
  - XLE: `ebf4be8c9f7f53b2472b1a032d5f105f7ed5ce7f439411f468b6435939176ba3`
  - XLF: `da3a5aa47a06f469dd6a99288e7be423ff63e9a8b9dc10d6832dc7a4af5b1491`
  - XLI: `d153ab22f333d536bdf7c8ef84c981b9c5614e8f62969687d765f043e35e596c`
  - XLK: `7dc854d1e340f1619340c1c26c9be4cc17fd0c925a0bbe036c74c058d53d0e63`
  - XLP: `a480545513732922a2be49c2cf807f7500baf923beb909cdf8d59eae70ef885b`
  - XLRE: `c578f88c142f67a237f45a324097fc912c6994abd2aaa355080b5e94ca41fcae`
  - XLU: `238dbbd6d68fa71ae074020ad83a2bbc4ffcd0a45cc087ca1982d56fb4a5b2f1`
  - XLV: `64f9d9b448b7e93b9e11137db11d9860c1c61d4682b0c685f43a6ff73db5d251`
  - XLY: `870fa4c0b19e31d5ef33b2d0702b9e9815b89285f3e3eb925434afb36b758ed5`

## Claims (12) and INC

| claim | statistic | point | lower bound | verdict | flags |
|---|---|---|---|---|---|
| h5/P-all/binary | delta_v@alpha=b_h | 0.12423543875826044 | -0.486393193049741 | rejected candidate | FRAGILE |
| h5/P-all/quantile | pinball_skill | 0.000347905278569427 | -0.013134759851198908 | rejected candidate | FRAGILE |
| h10/P-all/binary | delta_v@alpha=b_h | 0.11432186254161558 | -0.3615229585304165 | underpowered/blocked claim | UNDERPOWERED_DISCLOSED |
| h10/P-all/quantile | pinball_skill | -0.011483001403053139 | -0.030434265836015977 | underpowered/blocked claim | FRAGILE, UNDERPOWERED_DISCLOSED |
| h21/P-all/binary | delta_v@alpha=b_h | 0.05057178116001645 | -0.3789082075071964 | underpowered/blocked claim | FRAGILE, UNDERPOWERED_DISCLOSED |
| h21/P-all/quantile | pinball_skill | -0.028383042919036816 | -0.06568245703241668 | underpowered/blocked claim | FRAGILE, UNDERPOWERED_DISCLOSED |
| h5/P-active/binary | None | None | None | underpowered/blocked claim | OBSERVER_NOT_ON_MAIN |
| h5/P-active/quantile | None | None | None | underpowered/blocked claim | OBSERVER_NOT_ON_MAIN |
| h10/P-active/binary | None | None | None | underpowered/blocked claim | OBSERVER_NOT_ON_MAIN |
| h10/P-active/quantile | None | None | None | underpowered/blocked claim | OBSERVER_NOT_ON_MAIN |
| h21/P-active/binary | None | None | None | underpowered/blocked claim | OBSERVER_NOT_ON_MAIN |
| h21/P-active/quantile | None | None | None | underpowered/blocked claim | OBSERVER_NOT_ON_MAIN |
| INC | — | — | — | NOT_APPLICABLE | the incumbent is SPY-only and SPY is excluded from the panel |

## Honest-N (event dates on the common calendar)

| cell | origins | event dates | episodes | event months | power floor |
|---|---|---|---|---|---|
| h5 binary | 14000 | 175 | 11 | 35 | met |
| h5 quantile | 14000 | 175 | 11 | 35 | met |
| h10 binary | 13930 | 395 | 4 | 44 | not met |
| h10 quantile | 13929 | 395 | 4 | 44 | not met |
| h21 binary | 13776 | 625 | 1 | 46 | not met |
| h21 quantile | 13776 | 625 | 1 | 46 | not met |

Pinned splits are adjusted per D14 (table in grey_deer_panel_adjust.PINNED_SPLITS). Dividends are unadjusted. The common axis is the intersection per D15 with pinned exclusion 2026-08-18.
