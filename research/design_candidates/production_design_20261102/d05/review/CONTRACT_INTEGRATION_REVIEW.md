# Final C3 contract integration review and adjudication

Operation d05-contract-integration-review-20261104-001. Native principal reasoning consultant d05_contract_integration_challenge. Scope: read-only cross-system challenge of UX, route and data contracts against the pinned source. No source/Paper/browser effects, external messages, worker or watcher.

Disposition on first return: corrections required before source freeze. Three material findings:

## D05-C3-01 — Coverage denominator (HIGH)

The initial contract wrongly equated confluence coverage_pct with n_priced/n_members. Current score_group increments n_priced for any nonempty member close history. basket_index.consolidated_candle defines coverage_pct as round(n_live_with_volume/n_live,3). Per-member price timestamp is not provided by the inspected detail path.

Root independently read both producers and the exact A06 source fixture. Corrected data and UX contracts; A06 now says Price histories,4/4, with latest-available member prices and explicit timestamp limitation. Native volume coverage remains separate. Added D05-DATA-08/09 falsifiers.

## D05-C3-02 — Source versus publication census (MEDIUM)

Current compute_basket_confluence emits n_listed,n_gateable,n_thin,n_below_min_members,n_unscored. n_gateable means successfully scored groups, not entry-eligible groups. The initial contract's blanket current-source absence claim was stale.

Root independently fetched the committed site/marketdata/basket_confluence.json at the audit pin. Its coverage still has only n_baskets,n_high,n_med,n_low_conf,thin_share. Corrected the package to source-present/publication-and-consumer-proof-held. Inherited SC-066 remains held, not silently accepted. Added D05-DATA-11/12.

## D05-C3-03 — Missing falsifier summary (HIGH)

Current State of Themes only maps explicit positive falsifier_n_data_missing to UNCONFIRMED. Missing thesis/summary defaults false/zero and becomes NOT_DETECTED. The initial contract incorrectly described the required missing-evidence behavior as already native.

Reviewer exercised extracted pure functions without file writes: absent fields and explicit zero yielded NOT_DETECTED; missing-count2 yielded UNCONFIRMED. Root separately read compose and consumer branches at the same pin. Corrected source description and recorded original-producer repair gate. D05-STATE-06/07/08 separate absence, explicit missing and fired evidence. No production code was changed.

## Bounded conclusion

Other inspected seams produced no additional material contradiction in this review: adapter_only research handoff, device-local investigation notes, regional save restrictions, broad-rotation formulas, current Cycles elapsed handling and regional stock adapters.

Root accepted all findings and corrections. Reviewer returned STOPPED with no watcher. Root sent ACCEPTED/STOP. This is an advisory challenge and root adjudication, not a formal RIG pass or independent production retest.

