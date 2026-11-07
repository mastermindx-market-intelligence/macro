# Verified Sector generation read and admission contract

Date: 2026-11-06. Mission: [#10779](https://github.com/mastermindx-market-intelligence/macro/issues/10779). Convergence: [#10780](https://github.com/mastermindx-market-intelligence/macro/pull/10780). Built on published base `b5437f84eacb8681056f9b1c9a924a22cad3bf6c`.

## Scope and ownership

This slice connects the existing verified snapshot facade to the native Brief/action-board projection and authenticated HTTP envelope. It prepares the incumbent publisher's fixed five-member request with semantic and complete-response admission. It adds no scheduler, lock, state store, authorization decision, publication pointer, calendar or proxy owner.

`app/sector_generation_reader.py::SectorGenerationReader` receives one deployment-owned absolute private generations root. The domain is fixed to `sector`; an HTTP request supplies only the already-authorized preview/entitled audience. The reader invokes `scripts.vps_live_orchestrator.read_selected_generation` once and consumes only the verified returned bytes and manifest. It never reopens member files or the current pointer, creates directories, writes a lock, uses the static tree as fallback, or selects another generation.

The five captured members are fixed:

| Member | Domain role |
|---|---|
| `sectordata/sector_central.json` | Core source-session agreement |
| `sectordata/sector_cycles.json` | Cycle source-session agreement |
| `basketdata/baskets.json` | Brief baseline, basket observations and chart input |
| `basketdata/si_handoff.json` | Accepted leadership/context input |
| `basketdata/action_board.json` | Canonical board and exact baskets-byte dependency |

This is the native five-member contract. The legacy freshness validator has a different five-artifact surface, including premium JSON and HTML. The native adapter does not fabricate those artifacts or assert that their relationships were inspected.

## Explicit domain identity

The generic `vps_live_generation.v1` manifest must contain this mapping inside its existing `input_identity`. Every named field is required:

```json
{
  "sector_view": {
    "schema": "sector.view_inputs.v1",
    "source_session": "2026-11-05",
    "input_version": "sector-inputs-v1",
    "baseline_session": null,
    "source_qualification": "accepted"
  }
}
```

These values illustrate shape, not production facts. A null baseline means the source session; an older Brief baseline must be an explicit valid date. It cannot be future-dated or inferred from whichever file is oldest. The input version is an approved opaque public token, not a private path or raw manifest. Qualification is accepted, stale or degraded.

The public generation ID is the actual verified manifest ID. Both it and the input version use the projector's narrower token grammar. A generic publisher ID containing colon or at-sign is refused, never sanitized into another identity. Publication time is the original manifest value, not pointer `selected_at`, mtime, computation time, HTTP Date or the read clock. It is bounded to 32 characters. The reader samples one aware clock after snapshot capture and refuses a publication timestamp later than that clock.

## Semantic and freshness checks

`lib/sector_generation_contract.py` strictly decodes the captured UTF-8 JSON objects. Duplicate keys, nonfinite numbers, malformed objects and missing members are errors, including nonfinite values in undisplayed fields.

The existing freshness owner exposes shared board-shape and baskets-dependency checks. The board must name the SHA-256 of the exact captured baskets bytes. Matching dates cannot qualify a same-session correction built from a different baskets revision.

The canonical projector checks core session, explicit common secondary baseline, schema, row allowlists and audience partition. Its 21-observation comparison formula is unchanged. Only the authorized representation contributes to the public content hash; private manifests and dependency hashes stay private.

The shared `evaluate_session_age` helper uses the existing published US calendar through `lib.market_session`. Its owner already settles published half-days at 14:00 ET and other sessions at 17:00 ET. The helper verifies every year needed for its exact lag calculation, including current, expected, source and baseline years; unavailable annual coverage is not replaced with a claimed verified fallback. This aligns legacy Sector freshness and the native reader with that owner. Direct consumers of the historical `lib.nyse_calendar` implementation are unchanged. The existing one-completed-session allowance is unchanged.

The reader qualifies both core and Brief baseline against the read clock and their original publication clock:

- Source-declared stale status or an age breach on either clock yields stale.
- Otherwise source-declared degraded status or developing data on either clock yields degraded.
- Otherwise the source is accepted under this policy.
- Non-session/future source dates, source after original publication, unavailable calendar evaluation, contradictory dates, corrupt bytes or dependency mismatches are unavailable errors.

Time passing cannot turn developing-at-publication observations into final-close observations. A recent date cannot improve a producer-declared stale/degraded state. An accepted retained generation can age to stale without republishing or changing its original publication time. None of this manufactures provider observations; exact-target acquisition and adequate history remain producer obligations.

## Final admission inside the existing publisher

`lib/sector_generation_wire.py::encode_sector_generation` is the finite-JSON encoder shared by actual HTTP responses and preflight. The 4 MiB ceiling applies to the complete `sector_generation.read/v1` body. Preflight checks preview and entitled views from the same bytes and reserves the existing maximum public receipt widths. Size probes are never returned as source facts.

`prepare_sector_generation_request` assembles the fixed five artifacts with strict per-member decoding and the incumbent `GenerationRequest`'s optional final bundle validator. The publisher captures and verifies all staged members, samples one admission clock, and resolves the actual new or retained target manifest. It then invokes this callback once with detached target identity, immutable captured member bytes, the exact target's original `published_at`, and the current admission clock.

For a new generation, publication and admission clocks coincide. Reuse preserves the original publication string and evaluates it separately from the new admission clock. The callback precedes both an unchanged return and a selection change. Thus an earlier generic publication cannot gain accepted Sector qualification through reuse with a more favorable clock.

After the callback, the publisher re-verifies staged bytes. A retained target is reverified too, including equality of its complete manifest because publication time is deliberately outside content identity. New selection through this factory requires accepted qualification. Existing requests without a bundle validator retain their behavior; semantic rollback through any direct generic selection operation remains a caller obligation before runtime activation.

Requests are detached from the caller's initial identity mapping; mutation of the request's captured identity is refused. The caller owns acquisition/calculation and supplies the actual expected-current selection fence. Preparing a request does not publish, retry, select, grade or fetch data.

## HTTP authorization and construction

The router runs the incumbent registration and entitlement gates over all five fixed preview resources and the additional paid resource for entitled output. It invokes the reader once after authorization. Errors omit private roots, manifests, hashes and exception details. Responses are private/no-store and vary on Cookie.

The application owner can construct `SectorGenerationReader(generations_root=absolute_private_root)` and inject it into the existing router, or set the existing `app.state.sector_generation_reader` capability. The root is deployment-owned, never selected by query parameters. This slice does not mount that route or provision a production root.

## Verification and remaining activation

The clock-correction reader/API/projection and selected legacy freshness run passed 145 tests, with 57 unrelated page tests deselected. A separate focused incumbent publisher run passed 68 generation tests, with 88 unrelated cases deselected. Final combined verification after the retained-receipt correction passed **222 tests**, with 143 unrelated cases deselected. Its exact command and log identity are recorded in `ALWAYS_ON_ACTIVE_COMMISSIONS_2026-11-06.json`; overlapping runs must not be added as unique test counts. Existing dependency-deprecation and pytest temporary-directory cleanup warnings remain.

Tests use temporary generations through the actual publisher, verified snapshot facade, canonical projector and actual HTTP gates with controlled identity/entitlement fixtures. They cover pointer movement, same-session correction, immutable capture, no read-side writes, independent baseline aging, exact dependency mismatch, malformed identity/JSON, calendar outage/coverage/half-day boundaries, both audience limits, actual-clock admission, retained receipt reuse, and rejection preserving selection. These are local integration proofs, not live-provider or authenticated-beta receipts.

No production root, timer, ownership profile, selection, BFF binding or deployed release changes here. The projection still carries Brief and action board; complete coherent Sector core/history adoption is outstanding. Strict 14-symbol and broad/member acquisition, board calculation, updater recovery/first-install admission, protected CI/release controls and actual source-to-screen beta proof remain open.
