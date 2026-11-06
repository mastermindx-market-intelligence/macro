---
key: DARKFLOW-DIX-20261017
claim: Mastermind can construct a reproducible DIX-style observation from its existing FINRA and raw-price stores, but stale prices, survivor membership, mixed publication generations and unregistered presentation assets can silently invalidate the product.
falsifier: Run the arithmetic, source-vintage, source-clock, render-only and canonical-public-asset tests in tests/test_darkflow_index.py and tests/test_darkflow_publish.py, then the real shared-component browser checks in tests/darkflow_browser.py.
so_what: Reuse the existing data, ledger, access and publication owners. Keep the expected source session separate from the last fully covered display date; expose ratio, weight and coverage contributions rather than institutional-intent claims.
kind: landmine
verified_at: '2026-11-06'
verified_by: 'python -m pytest tests/test_darkflow_index.py tests/test_darkflow_publish.py -q; #9574; research/evidence/darkflow_20261106/source-qualification.json'
scope:
- mastermindx-market-intelligence/macro
- engine/darkflow_index.py
- engine/darkflow_publish.py
- engine/darkflow_observations.py
- templates/_darkflow_panel.html.j2
confidence: verified
---

Implementation and delivery evidence: https://github.com/mastermindx-market-intelligence/macro/pull/9574.
Method, source constraints, Paper identity and dated data-acquisition hashes are in
`research/DARKFLOW_INDEX.md`. The final merge/release/browser receipts belong to
that PR; a successful local calculation or this discovery is not production proof.

The compact consumer belongs after Macro's Market State overview and expands into
the existing Dark Pool Desk, not a second risk or transmission classifier. The
existing participation gauge measures a different quantity and remains unchanged.
Sector history uses current classifications and is explicitly not a point-in-time
investment backtest. No predictive, alert, sizing or trade authority is granted.

The existing public-shell boundary is default-deny for unknown static assets.
Pure component CSS and JavaScript must use the existing inline-asset externalizer
and approved `/assets/css/` and `/assets/js/` prefixes. The new analytical JSON
stays protected. Do not solve a presentation 401 by making market payloads public
or editing the Caddy/auth allowlist. A source 401/403 is an access state, not an
unchanged retry loop; use the existing local sign-in/plans destinations.

Historical backfill owns only `panel_deep.parquet`. The collector panel and
PSS-AF1 prefix are not rewritten. Render-only delivery calls the existing context
producer with `write=False`; only the existing nightly gate can append a first
observed input record. Historical reconstruction never becomes a backdated live
observation. Exact source-byte hashes and summary/history generation identity are
part of the read contract, not merely decorative provenance.

Historical capability on 2026-10-17: the attempted typed publication resolved the
default Mastermind repository and was reconciled NOT_APPLIED. The original Macro
branch was then published on its authorized Studio carrier without changing the
publisher allowlist or repository identity. That dated failure is not a present
capability restriction.

On 2026-11-06 the existing Macro operation was recovered, qualified and published
through the installed typed commit and push owners. Native readback confirmed
head daec89b8a41adc8dc05263784d14eb10bce5c55e and its exact qualified merge tree.
The current source and browser receipts are under
research/evidence/darkflow_20261106/ and the source-linked return on #9574.
