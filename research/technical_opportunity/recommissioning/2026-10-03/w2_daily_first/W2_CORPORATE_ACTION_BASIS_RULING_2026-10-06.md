# TOI W2 corporate-action and economic-basis ruling — 2026-10-06

Program: WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE.
Existing W2 carrier: Macro #7094 / TOI-W2-0-DATA-CLOCK-V1.
Disposition: BASIS_CONTRACT_FROZEN / CORPORATE_ACTION_SOURCE_OWNER_HOLD. MISSION_COMPLETE:false.

## Decision

The Daily-first study keeps massive_stock_day raw Daily bars as its immutable source of record, but raw printed price is not itself an admissible multi-session detector geometry across splits. The TOI report explicitly distinguishes raw geometry, split-adjusted geometry and total-return outcomes, and requires a single declared geometry basis plus a separate declared economic-outcome basis.

For the first 22-slot study, the proposed basis contract is:

1. Geometry source of record: immutable raw Daily OHLCV.
2. Analytical detector geometry: split-adjusted price-only frame derived on read from the raw source using authoritative corporate-action events effective by the decision cutoff. Dividends do not alter detector geometry.
3. Frozen occurrence audit: retain the original raw trigger/invalidation values, the derived split factor and source vintage. A later split transforms the same frozen occurrence onto the new share scale; it never creates a new breakout or resets occurrence age.
4. Participation volume: preserve raw persisted integer volume. When a feature spans a split, multiply historical raw volume by the reciprocal price factor so split-equivalent shares and close-times-volume remain invariant. The exact representation is part of the native configuration.
5. Primary economic ruler: split-adjusted price return on the same price-only basis, with transaction/confirmation costs stated separately. This is not total shareholder return.
6. Secondary total-return ruler: HOLD until authoritative dividend events, entitlement timing and an explicit dividend/reinvestment convention are frozen. The TOI research report permits a separate total-return ruler; it does not require silently converting the primary geometry into dividend-adjusted history.
7. Unmodelled reorganizations: spin-offs, mergers, stock/cash consideration and unresolved identity changes return CORPORATE_ACTION_UNRESOLVED / DATA-UNRESOLVED. Last close is not silently treated as terminal economic value.

## Why the incumbent price-jump splitter is not authority

Current scripts/replay_standout_pipeline.py::split_adjust is useful house evidence and a compatibility diagnostic. It infers clean common split ratios from large close-to-close jumps and back-adjusts prior bars. That is not an authoritative corporate-action source: a genuine large move near a clean split ratio is observationally ambiguous from price alone.

TOI therefore must not promote that heuristic into reference.corporate_actions. It may be used as an adversarial comparison against an authoritative event feed; disagreement becomes a source-quality finding.

## Existing owner and current source gate

The current Data OS contract already names reference.corporate_actions as the intended factor-table owner and explicitly says the dataset is PROPOSED / not built. TOI must not create a second corporate-action store.

The existing Massive enterprise entitlement covers corporate actions and research/derived use. Massive's current Stocks API documents:
- GET /stocks/v1/splits: execution date, split ratio, adjustment type, event ID and historical adjustment factor; trading on the execution date is already on the post-split share basis.
- GET /stocks/v1/dividends: cash/ex-date metadata and adjustment factors for total-return work.

The current m2 execution surface has no Massive/Polygon REST credential in its environment. One anonymous split request returned HTTP 401 with API-key-required semantics. No secret value was read and no credential mapping/search was attempted. This is an owner/access gate, not permission to infer actions from price jumps or to switch accounts/tools to find credentials.

The required Data OS/source-owner return is one immutable, paginated-complete corporate-action snapshot for the admitted population/window, with source endpoint/version, fetched_at, query/filter scope, raw digest, event count, IDs, execution/ex dates, ratios/amounts, identity/alias binding and correction/source vintage. The snapshot's current-vintage historical use remains RETROSPECTIVE unless stronger known-at receipts exist.

## Synthetic contract proof

The companion contract test uses no market data. Ten tests pass:
- no-action identity;
- forward split continuity;
- reverse split continuity;
- serial split composition;
- reciprocal volume transform and dollar-volume invariance;
- future split excluded from an earlier decision cutoff;
- execution date remains on post-split scale;
- a large non-action price move is not rewritten without an event;
- conflicting same-date ratios refuse;
- duplicate IDs and nonpositive ratios refuse.

An initial reproducible-test failure was test-only: the derived frame normalizes price dtype to float64 while the fixture was int64. The assertion was corrected to compare float value identity; the transform was unchanged.

## Exact transformation law

For a confirmed split event with old shares split_from and new shares split_to on execution_date E:

price_factor = split_from / split_to

For each raw bar with date D < E and E no later than the decision cutoff:
- adjusted O/H/L/C = raw O/H/L/C * price_factor;
- adjusted volume = raw volume / price_factor.

For multiple confirmed split events, multiply the event factors. Bars on E are already post-split and are not rescaled by that event. Future events beyond the decision cutoff cannot alter that decision-vintage frame.

This law is a target contract for the existing Data OS owner. It is not a new production implementation.

## Gate consequence

The mathematical basis choice is now bounded. W3 remains HOLD because the authoritative corporate-action event plane/input receipt is not yet available to this session, and historical identity/membership policy from the price-coverage census is still unresolved.

Once the source owner returns the immutable action snapshot, the first-wave data gate can test actual population coverage and transform parity without reopening broad W2 archaeology. If the source cannot bind an action or identity, that member-date remains unavailable; it is not converted into a structural TOI failure.

No outcomes, models, real trial registrations, production writes, Prophet ranking/gating/sizing or trading authority were exercised.
