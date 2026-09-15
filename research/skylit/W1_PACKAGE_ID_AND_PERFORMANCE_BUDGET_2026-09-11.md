# W1 package identity and performance budget amendment

Recorded: 2026-09-11 UTC. Accountable seat: ceo-sol.
Operation: `us-sector-participation-w1-20260910-sol-001`.
Applies to `research/skylit/W1_DERIVED_PACKAGE_AND_UI_CONTRACT_2026-09-11.md` and Macro PR7060.
Procedure pin: protected Mastermind `068dcc1533776672844b36ffcde30fad68a4317f`, Skillpack 1.0.1 / bootstrap 1.

## 1. Why this amendment exists

The one-package ruling correctly prevents calendar summary and member detail from drifting, but its first wording left `generation_id` and the payload/render budget underspecified. That ambiguity could create either unstable IDs that change solely because a build clock moved, or cache-stale packages whose provenance changed without a new fetch identity.

This amendment makes three content identities explicit and freezes a bounded full-year package envelope. It creates no registry, history database or new publication owner; the hashes are deterministic receipts carried inside the existing derived package.

## 2. Canonical identities

Canonical hashing uses UTF-8 JSON with sorted object keys, compact separators, arrays in their declared semantic order, finite numbers only and no implementation-specific whitespace. Before hashing, every object is validated against the W1 schema; invalid or non-finite values are refused rather than normalized into a different meaning.

### `roster_id`

`roster_id = sha256(canonical roster rows)` where each row is exactly:

```json
{"symbol":"...","name":"...","sector":"..."}
```

Rows are sorted by the existing canonical membership symbol. Duplicate symbols, conflicting sector assignments or invalid names are rejected before hashing. The roster observation clock is not part of this content hash; it remains a separate field and stays null when no authoritative observation time exists.

### `response_set_id`

`response_set_id = sha256(canonical per-member accepted-source receipts)`.

Each receipt binds the requested canonical symbol, accepted provider symbol, adjusted basis, requested start/end, returned accepted session/value pairs in ascending session order, explicit holes/exclusion class, body/request identity when safe, and qualification outcome. It excludes secrets, raw bodies, wall-clock logging text and retry noise.

A re-fetch returning identical accepted values and holes may retain the same `response_set_id`; a correction, basis/identity change, changed hole or changed requested range changes it.

### `observation_id`

Add `observation_id` to the package. It is the SHA-256 of the canonical economic/analytical content:

- schema and method/version;
- roster identity and universe semantics;
- source contract/basis/requested range/latest expected session;
- `response_set_id`;
- ordered session list;
- all sector summary arrays and exclusion arrays;
- all member identities, states, links and derived distances;
- state vocabulary.

It excludes `generation_id`, acquisition/computation/publication clocks and transport-only diagnostics. The same dated evidence and method therefore retain one observation identity across a no-change rebuild.

### `generation_id`

`generation_id = sha256(canonical package generation receipt)` where the receipt contains:

```json
{
  "schema": "sector_participation_20.generation.v1",
  "observation_id": "...",
  "roster_id": "...",
  "response_set_id": "...",
  "source_acquired_at": "UTC timestamp",
  "computed_at": "UTC timestamp"
}
```

This ID binds the exact package generation used by the page and allows cache busting even when the economic observation is unchanged but a new qualification/computation occurred. It does not make the source newer: the UI continues to judge currentness from `source_session` versus `latest_expected_session`, never from `generation_id`, `acquired_at`, `computed_at` or `published_at`.

The builder pointer carries both `generation_id` and `observation_id`. The client refuses a package whose IDs do not match the pointer or whose recomputed canonical IDs fail validation. Site `published_at` is outside both hashes and records only the projection event.

## 3. Measured package feasibility

A research-only sandbox benchmark generated a worst-normal full-year package with:

- 503 members using the actual current sector-count shape;
- 252 sessions;
- all six member states represented;
- one state character and one nullable `distance_bps` value per member/session;
- sector summary and four exclusion arrays per sector/session;
- method, source, roster and clock metadata.

Measured result using compact sorted finite JSON:

| Measure | Result |
|---|---:|
| Raw JSON | 892,747 bytes |
| gzip level 6 | 265,468 bytes |
| Python serialization median, 20 runs | 13.7 ms |
| Python parse median, 20 runs | 16.5 ms |

This is synthetic feasibility evidence, not browser, network, mobile-device or production proof. Values are shape-sensitive and do not grant permission to drop names, sessions, state distinctions or clocks to meet a budget.

## 4. W1 engineering budgets

For a 503-member, 252-session package, the initial acceptance ceilings are:

- raw canonical JSON: **1,500,000 bytes maximum**;
- gzip/transfer representation when compression is used: **600,000 bytes maximum**;
- one package fetch on first activation of Money & Breadth, zero duplicate fetches on return/resize;
- calendar DOM: only 11 sector rows × the selected 3M/6M/1Y session window, never 503 × sessions;
- detail DOM: only the selected sector's reference members, not all 503 names;
- no pre-render of every member/session distance or hidden duplicate table.

The worker must report actual browser fetch, parse, first-render and interaction timings at 1440, 768 and 390 widths on the accepted evidence machine. The product fails the budget if it meets latency only by truncating sectors, members, sessions, states, exclusions or clocks.

Recommended initial browser acceptance targets, subject to measured host evidence rather than a claim of universal device performance:

- fetched-package JSON parse + validation: <=100 ms at p95 over 20 warm local runs;
- first 3M calendar render after data availability: <=150 ms at p95 over 20 warm local runs;
- selected-sector detail update: <=100 ms at p95 over 20 interactions;
- no long task over 200 ms attributable to the W1 asset in those runs.

A slower result is not automatically waived: return the measured profile and smallest bounded optimization. Do not create pagination/network APIs, Web Workers, IndexedDB, another cache or a second package before proving the static one-package approach insufficient.

## 5. Cache and correction behavior

The site URL may use `?v=<generation_id>` under the existing asset/version convention. A changed generation forces a new fetch. A byte-identical semantic observation rebuilt at a later time may have a new generation but the same `observation_id`; the UI may say “revalidated” only when the source/acquisition contract proves that fact, while keeping the original `source_session` currentness.

A provider correction changes `response_set_id`, `observation_id` and `generation_id`. Atomic replacement ensures the old complete generation remains available until the new complete generation validates. The pointer is published only after the package projection succeeds; a page cannot point at a generation that is not present.

The browser treats an ID mismatch, malformed hash input, unknown state code, inconsistent array length, sector/member count mismatch or impossible clock ordering as `invalid`, not a partial ready state. It retains the existing page organs and exposes the W1 error without attempting a client-side repair.

## 6. Additional discriminating tests

1. Changing only `published_at` changes neither `observation_id` nor `generation_id`.
2. Changing only `computed_at` retains `observation_id` and changes `generation_id`.
3. Reordering JSON object keys changes no identity; reordering sessions or member rows without matching semantic reordering is rejected.
4. One corrected close or changed missing-session state changes all three downstream response/observation/generation identities as appropriate.
5. Pointer/package generation mismatch and recomputed-hash mismatch are refused.
6. A 503 × 252 fixture is below the raw budget and renders without dropping any member or session.
7. Initial non-Money page load makes zero W1 requests; first activation makes exactly one; return/resize makes zero additional requests.
8. Browser measurement records p50/p95 and long-task count rather than a single fastest run.

## 7. Authority boundary

This amendment is a specification/proof refinement only. It does not prove PR7060 repaired, authorize native delivery to Claude, grant source START, run provider data, change CI, mark Ready, merge, deploy or accept W1. The current Sol `CHANGES_REQUESTED` review, active PR7056 shared-path custody and direct action-specific native-transmission consent gate remain controlling.