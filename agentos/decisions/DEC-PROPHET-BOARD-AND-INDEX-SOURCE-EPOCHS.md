---
key: PROPHET-BOARD-AND-INDEX-SOURCE-EPOCHS
question: >
  May a lawful site re-render replace the current US board independently of the
  frozen source bound to the existing Prophet index?
answer: >
  Yes. Preserve the two source epochs and make the existing reader distinguish
  their exact byte identities. Bind the displayed plan book to one captured index
  read, verify its canonical frozen gzip source, and compare the current board
  separately. The existing paid payload may hydrate only when its board, index
  and frozen-source identities match those captured by the page. Missing or
  mismatched evidence remains PENDING; this reader never issues SETTLED.
rationale: >
  The normal Prophet producer already defines us_standouts.json as a live artifact
  with several lawful render publishers and binds each index to a content-addressed
  immutable source snapshot. Express render regenerates and stages the board
  without running Prophet origination. The nightly index checkpoint is separate.
  A date-only reader therefore hides a real same-session source change. Moving
  origination into express rendering would transfer lifecycle and ledger authority
  to a presentation lane. A source identity disclosure and the existing hydration
  entry fence correct the consumer without creating another publisher or bundle
  issuer. Exact agreement among these source pins is not A2's four-family
  source-published/read verification, so no settlement inference is permitted.
alternatives:
  - option: Reissue an accepted index and bundle atomically on every site re-render.
    why_not: >
      Express rendering does not own plan origination or lifecycle accounting.
      Running that producer on each presentation refresh would change its authority
      and cadence. The current producer explicitly preserves immutable origination
      sources while allowing board refreshes. This bounded repair preserves that
      contract and does not mint an accepted bundle identity.
  - option: Treat equal market dates as one source epoch.
    why_not: >
      The committed source has equal market dates and a different buy membership:
      95 rows in each source, 94 shared. Exact raw hashes differ. A formatting-only
      difference also remains a byte difference; normalization cannot establish
      the producer's exact source identity.
  - option: Add a disclosure without checking the existing paid payload.
    why_not: >
      The page and premiumdata/us_stocks.json are read separately. An old page
      could otherwise append plan or candidate rows from a different source pair
      while retaining its original identity label.
evidence:
  - research/prophet_v4/epoch_divergence_20261101/PLAN.md
  - research/prophet_v4/epoch_divergence_20261101/census.json
  - https://github.com/mastermindx-market-intelligence/macro/pull/10174#issuecomment-6567098234
  - scripts/build_prophet.py::_freeze_origination_source_board
  - scripts/build_site.py::_read_us_prophet_book and post-build_library refresh
  - scripts/build_stock_library.py::main us_standouts serialization
  - .github/workflows/render.yml and .github/workflows/engine-render.yml
  - .github/workflows/daily.yml nightly Prophet checkpoint and R2 mirror
affects:
  - WS:PROPHET-US-V4-RECOVERY
  - WS:PROPHET-US-AVAILABILITY
  - engine/prophet_source_epochs.py
  - scripts/build_site.py
  - templates/dashboard.html.j2
confidence: high
reversibility: easy
decided_by: Chairman-assigned Pro fix owner, ChatGPT4
decided_at: 2026-11-02
---

## Scope and authority

This decision resolves operation
`prophet-a2-board-index-epoch-divergence-20261101-sol01` within the existing reader.
It grants no deployment, merge, auto-merge, credential, security or trade authority.
It does not modify the accepted bundle producer, lifecycle ledger, board producer
or render/nightly workflows.

`settlement_status: PENDING` is the explicit limit of this source-only projection.
`SAME_SOURCE` describes byte identity; `SEPARATE_EPOCHS` describes different
verified source snapshots; `UNAVAILABLE` describes missing or invalid evidence.
None is a settlement receipt. Four-family verification remains with its existing
owner. PRs #10202, #10209 and #10289 retain their separate holds and owners.

## Proof boundary

The pickup tree is macro/main
`9fe98ab14db8ccc1bb35d9dd8b1d11617527dfdf`.
The full census and initial plan were published at
`6343a18748e4ce2bed5a34b2e015acdb39a5d7a7` before implementation.
Committed-tree measurements are not served-production observations.
Candidate tests and browser evidence are tracked in the scoped research directory;
no production acceptance is asserted by this decision alone.
