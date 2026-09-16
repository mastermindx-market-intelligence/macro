# Deep-stock completed-price recovery

## Proven gap and consumer
The real stock library prefers `data/stocks` deep histories before the index-constituent breadth tapes. In the immutable combined US-recovery source copy, 243/245 deep histories ended September 14 while the repaired breadth panels reached September 15. The existing StockPriceAdapter accepted historical-only successful downloads and counted those frames toward its 70% return floor. Fresh breadth alone therefore could not make the full source universe coherent.

This repair retains the same stock-price producer, universe/retention/dead exclusions, adjustment-basis repair and retry budgets. It captures one existing NYSE completed session per fetch, retries price-incomplete responses inside the existing downloader, filters stale/invalid frames before the store consumer, and applies the existing whole-universe 70% floor to actual current prices. A failed source cannot publish aggregates through run_adapter. No second calendar, provider, retry plane, source selector or trade rule exists.

## Verification
The current-price/retention/basis/delisting suites passed 102 tests with one existing sparse-data test skipped. Three negative variants were detected: removed semantic retries, invalid prices accepted as current, and removed final post-pull filtering. The old basis fixtures now date their max-history response consistently with their seed and explicitly bind the fixture observation clock; their basis and retention assertions are unchanged. The new hermetic suite is registered under gate:code.

The real existing `run_adapter(StockPriceAdapter())` was run against an isolated copy of committed stock/holdings/dead-name inputs with the final source SHA-256 bound in `live-source-receipt.json`. It refreshed **243 deep-stock files to September 15**, returning **ok / last_date=2026-09-15**. AVB was excluded by the existing confirmed-exit ledger; EA's unavailable current tape was disclosed and not fabricated. These exceptions remain explicit. This is actual provider-to-store-consumer proof, not production publication.

## Integration boundary
The earlier full composed board probe used #7180/#7200/#7187 source and actual full data, including the running engine's read-only Russell cache snapshot. It analysed 3,042 names but timed out in later enrichment after 1,200 seconds; it did not emit a completed new board receipt. Its extension guard correctly fell back one session because current-row coverage was only 42.1%. Further inspection showed Russell only 21/1,943 current constituent closes, with 1,922 still on September 14. That distinct producer dependency remains unresolved; this deep-stock repair does not claim to fix it.

Production is not restored by this PR. Required before acceptance: independent exact-head review, hosted/security checks, current-base composition with the existing source repairs, full current source universe, canonical publication and a real served browser/premium-payload receipt. Never retry over natural run 35041133038 or rewrite any incumbent worktree.
