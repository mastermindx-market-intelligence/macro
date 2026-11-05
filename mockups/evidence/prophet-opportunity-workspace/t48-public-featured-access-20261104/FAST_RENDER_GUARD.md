# D03 T48 — fail-closed dev fast-render publication check

Observed on 2026-11-04 after T48's source-only implementation commit
`f5c6ead13c31c582568285f44f3551566d7aa8bd`.

## Mismatch

The tracked public `site/us_stocks.html` carrier on #9495 declares
`data-today-visible=0`, `data-today-total=12`, and an empty
`data-today-served` member list. Its exact source SHA256, pair ID and
selection receipt were all present.

The isolated development `_dev_macro_vm.pkl`, generated during an
interrupted broad build, rendered **3** of the same 12 Featured rows and
three served row receipts, **despite the same source SHA/pair/selection
pins**. The cached VM is therefore NOT equivalent to the committed
public-source entitlement partition. Its generated `site/us_stocks.html`
had 72,457 additions / 3,845 deletions versus Git HEAD, showing broad
unaccepted data changes as well as the UI change.

## Guard and exact behavior

`scripts/render_macro_fast.py` now reuses canonical production-Jinja
globals/functions, renders in memory, and compares six binding attributes
against **Git HEAD's committed** `site/us_stocks.html` before writing
*any* page:

1. total, visible;
2. source_sha256, pair_id, selection_receipt;
3. served row receipts / membership.

Missing, malformed, unavailable or different values refuse with
`REFUSED_STALE_PROPHET_VM` (return code 2); the response names changed
fields and count only, without printing protected row receipts.
`tests/test_render_macro_fast_source_guard.py` tests all six individual
drifts plus missing fields and committed-source readback.

Before this guard the dev-only renderer could overwrite four pages from
an old or different-access cache; after it, the observed candidate
`3` vs committed `0` exited 2 **without writing**. The earlier
unqualified generated output still exists only as dirty files inside
the isolated Ubuntu0 worktree. **Never stage or publish those files.**

## Remaining native gate

This guard is a developer fail-safe; it does not regenerate trusted
public data or constitute source/publisher acceptance. A qualified
native production publisher must reproduce the exact public access
binding and regenerate the coherent site + gate pair. The broad
`build_site` attempt was stopped after upstream GDELT 429/freshness
errors and unrelated data/profile fetching. No merge, enqueue,
Ready/un-draft, label, deploy or purchase.
