# TOI W2 Daily-first price/denominator coverage return — 2026-10-06

Program: WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE.
Existing W2 carrier: Macro #7094 / TOI-W2-0-DATA-CLOCK-V1.
Evidence class: source/coverage qualification only; no outcomes.
Disposition: PRICE_DATE_COVERAGE_MEASURED / POPULATION_IDENTITY_STILL_HOLD. MISSION_COMPLETE:false.

This return advances the Daily-first source gate created by the preceding source ruling. It does not alter #7094's broad Daily/Weekly/4H HOLD or open W3.

## Live R2 census

The canonical massive_stock_day R2 snapshot was read directly. The public manifest was byte-identical before and after the scan: SHA-256 ee3f0ad6db975e4d29a44924611ad51f6be55e45c0ab18745d681629ebcf4ce2, ETag 9966c7a141809b7fb5e5d9a5a466d967, Last-Modified 2026-10-06 05:00:15 GMT. Its embedded store contract covers 2021-07-06 through 2026-10-02.

The census used committed PIT S&P1500 membership blob ec7085bc7460aca4a07661fa5983c424e1559be8, inclusive house interval semantics, and the current NYSE session calendar. It read only each R2 parquet date index. No OHLCV/transaction values, signals, labels, forward returns, model outputs or market outcomes were read.

After canonical Massive ticker-path reconciliation:
- population: 1,924 unique membership ticker keys / 2,205 overlapping intervals;
- R2 objects resolve uniquely for 1,922 keys; zero proposed-population join keys have multiple R2 candidates;
- literal expected member-session cells: 1,990,911;
- Daily date cells present: 1,957,003;
- missing or identity/source-unresolved cells: 33,908;
- literal date availability: 98.2969%;
- 583 ticker keys have complete literal coverage; 1,341 have at least one missing/unresolved cell;
- no unresolved HTTP transport failure remained; five bounded transport retries succeeded.

The full per-ticker receipt is PRICE_COVERAGE_CENSUS_2026-10-06.json.

## Availability is not identity admission

The first bulk reader initially used the normalized membership join key as the R2 artifact filename. That incorrectly marked four share-class names absent. Canonical Massive mapping preserves vendor dot spelling: BF-B -> BF.B, BRK-B -> BRK.B, CWEN-A -> CWEN.A, MOG-A -> MOG.A. The corrected totals above include those files. Two keys remain object/identity unresolved: BPFH (2 expected sessions at the Daily-store boundary) and UAA/UA (1,123 literal expected sessions). Existing dead-name evidence also marks both unresolved; UAA/UA is not silently split into securities.

## Missingness is dominated by membership-floor uncertainty

Of 33,908 missing/unresolved literal cells:
- floor-seeded interval before first R2 row: 28,765 (84.83%);
- other pre-first gap: 180 (0.53%);
- after last R2 row while literal interval remains active: 1,673 (4.93%);
- interior date gaps over resolved objects: 2,165 (6.38%);
- object/identity unresolved: 1,125 (3.32%).

The reconstruction source floors names whose membership predates its available change log: S&P400 at 2012-01-13 and S&P600 at 2019-12-17 (S&P500 source floor 1996-01-02). Fifty-two ticker keys carry floor-seeded pre-price missingness. Those cells explain most missing dates.

This does not establish that R2 randomly lost 28,765 observations. It exposes identity/membership-time uncertainty: a current/new ticker string can be projected backward across a floor-seeded interval even when that vendor symbol has price history only much later. Current security-master law independently forbids manufacturing U.S. listing dates from earliest bars. First R2 price date therefore cannot repair membership start.

## Gate consequence

The price-file/date availability question is now measured, but the proposed population is not scientifically admitted. Retain unavailable/ambiguous cells explicitly. Before outcomes, the scientific/source owner must freeze how historical alias/security identity and floor-seeded membership uncertainty are treated. Do not backdate current aliases, substitute first price as inception, silently drop problem names, or narrow to a cleaner cohort after seeing TOI results. Any narrower population is an explicit preregistration amendment with its own generalization claim.

Remaining first-wave data gates are historical identity treatment, immutable source/archive identity, volume representation, raw geometry versus economic-return basis, Weekly contract implementation, RETROSPECTIVE ceiling plus prospective follow-up, and per-use ADMIT/HOLD/REJECT. The independent #7094 current-base records recompose also remains owed.

No trial registration, outcome access, model fit, production mutation, Prophet rank/gate/size or trading authority follows.
