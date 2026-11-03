# Verification and independent review

## Accepted scope

Bounded independent methodological review found no remaining material execution or methodological error in corrected `analyze.py` and `supplement.py`. It checked source definitions, completed bars, next-open chronology, entry-day and gap stops, capital reservation, open cutoff positions, paired comparisons, uncertainty support and archived cohort reconciliation. This is a research-mechanics acceptance, not a strategy validation or production approval.

## Mechanical checks

`verify.py` passed 13 focused checks: entry-session stop; adverse gap fill; strict versus quarter-ATR breach; adjustment-factor versus price-only arithmetic; reserved capital/exit-close entry clock; cash after early stop; cutoff open-position marking; equal-value basket arithmetic; nine future-prefix native-indicator invariance comparisons; flat-RSI handling; fees/exposure/account arithmetic; declared cash-yield elapsed compounding; and sparse-bootstrap suppression with joint contrast arithmetic.

Original V11 reconstruction matched 1,872/1,872 dates, with zero context mismatches and maximum return difference 1.13528735240509e-06. The absent original temporary raw files were not recreated or claimed present. Thirteen public histories were newly acquired; other histories reused retained verified inputs.

## Review-driven corrections

1. The first implementation used the old 0.25-ATR tolerance for the primary reference-break field. The protocol froze the actual reference low. Primary breach is now strictly below that low; the tolerant result is separately named. Touching and untouched-through-stop fields are explicit.
2. Bootstrap intervals now require at least four populated half-years and 95% usable draws. Contrasts retain joint valid-draw fractions and both arms' support.
3. The eventual-winner AND stopped-loss AND untouched-reference intersection is calculated directly, including the ordinary-date comparator.
4. Archived 74-event versus 50-entry membership is explicitly reconciled. Of 41 common signals, 39 have different endpoints and two the same endpoint.
5. Capital hit-rate comparisons use common scheduled maturity. Early stops can close otherwise immature horizon slots, so the operational closed-trade denominator is not a valid paired denominator at cutoff.
6. Complete-comparator support is shown within each cohort. It does not equalize the core and peer calendar/regime distribution.

The initial run was preserved privately. `audit_corrections.json` proves the portfolio summary, daily paths and capital rosters remained byte-identical after the definition/inference repair. Defensive entry identities, context, returns, stops and frozen-reference geometry also remained unchanged. The supplemental reporting does not select a new policy.

## Independently reconciled headline arithmetic

- Core matched support: 66/73 positive versus ordinary positive fraction 82.2594%; mean paired increment 1.09925 pp.
- Peer matched support: 146/213 positive versus ordinary 62.1629%; mean paired increment 1.91312 pp.
- Core common scheduled-mature capital slots: 29/32 positive unstopped versus 14/32 stopped.
- Sector common scheduled-mature capital slots: 75/93 positive unstopped versus 54/93 stopped.
- Strict reference survival: 39/74 core joint events and 71/218 peer joint events.
- Eventual winners converted into stopped losses with reference untouched: 4/23 core conversions and 2/51 peer conversions.
- Worst-drawdown sleeve contributions sum to aggregate drawdown within 1e-8 for core JOINT and sector selected accounts.

## Interpretive acceptance boundaries

The positive descriptive timing increment should be retained; the ordinary-date comparison does not erase it. The high absolute core hit rate remains conditional on the selected ownership cohort. Pointwise intervals do not correct exposed-history selection. Same-day low/stop order is unknown. Same-date sector comparisons show uncertainty about selection benefit, not statistical equivalence. Worst-episode attribution explains observed paths and does not validate a new risk rule. Adjusted OHLC supplies a dividend-return proxy, not an exact historical dividend cash ledger.

No production code, live signal, rank, size, broker action, deployment, source-feed configuration or automated information feature changed. The authored strategy families and information schema remain research hypotheses.
