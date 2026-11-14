# Beta shell P4 — complete Prophet candidate read

## Purpose and scope

The Shared Shell migration needs the complete eligible US candidate population,
including names excluded from the main list. The existing Today selection,
historical model plans, observations, and Sector research are different
populations. This change transports the existing complete-pool display
projection; it does not join or replace those owners.

Parent construction plan: [Terminal PR1495](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1495),
`terminal/docs/beta-shell-consolidation-20261113/PLAN.md` at
`e8cfa85476c75afc445a4395a98982667787a095`. The parent P0–P17 acceptance remains
open. A merged endpoint is not a completed migration or production acceptance.

## Source and ownership

- Protected Macro input: `d8a12a7e4ca01628a5c45835458d13da2181fb34`.
- Existing mounted router: `app/prophet_daily_brief.py`, source blob
  `a9d223dff1e88a8ac573d3765f8c1642b7d8090e`.
- Projection owner: `engine.us_candidate_lanes.project_candidate_visibility`,
  source blob `01d5c8becd86ca8a126edf27ff7eade723b04ae2`. The engine is unchanged.
- Fixed input: `site/factordata/us_standouts.json`. Directory metadata at the
  protected input reports blob `b00a657c3c837b37d3d20eb60a0824114cd2ed13` and
  2,110,340 bytes. No captured market payload is added as a test fixture.
- Same site-full authentication dependency, private headers, configured repo
  root and nonqueuing `_READ_ADMISSION` as the existing Daily Brief route.
- The existing `POOL_ALLOWLIST` gains this exact transport module only. The
  authority import-closure, token fence and behavioral invariance tests remain.

The original Daily Brief query grammar, required source/pair/selection pins,
optional candidate-generation pin, conflict framing and pass-through behavior
are unchanged. `app/main.py`, build writers, scoring, selection, archive readers,
plan books and publication workflows are untouched.

## Read contract

`GET /api/prophet/candidates/v1` accepts no query parameters. Authentication and
site-full entitlement run before query validation or any owner/source work.
An entitled request with any query receives private HTTP 400 before read admission.

The fixed source is read at most 8 MiB plus one byte. Oversize, unreadable, invalid
UTF-8, duplicate-key, nonfinite-number and malformed JSON inputs fail privately.
The pure owner projection receives the parsed source without archive enrichment.
It retains source order and every eligible row, validates population/session
coherence, and suppresses off-cohort final scores. Zero is a legitimate score.

The response is serialized before a second bounded source read. Different raw
bytes or a failed final read refuse the response, even if an unrelated source
field changed and the normalized display digest stayed identical. The shared
permit remains held through projection, serialization and the final check, and
is released on every outcome. There is no retry, repair, fallback, queue or
cached publication in this transport.

Successful envelope:

```json
{
  "schema": "mastermind.prophet_candidate_pool_read.v1",
  "market": "US",
  "source": {
    "path": "site/factordata/us_standouts.json",
    "sha256": "sha256:<digest of exact accepted source bytes>",
    "bytes": 1234
  },
  "projection": "the existing owner's complete JSON projection"
}
```

The illustrative byte count is not a live reading. `projection` is an object
at runtime. `ready` and verified `empty` return HTTP 200. Owner `unavailable` returns
503 with its empty rows and unknown counts preserved. Unexpected read, import,
parse, projection, serialization or source-race failures return only
`{"error":"CANDIDATES_UNAVAILABLE"}` with HTTP 503. Authentication/entitlement keep
their incumbent 401/403 responses. All paths retain private/no-store, Vary
Authorization, nosniff and noindex/noarchive.

The raw source hash and the owner's normalized `source_digest` identify different
objects. Neither is a Today selection receipt, immutable candidate-generation
receipt, archive verification, research case, plan relationship or entry
assessment. The source may change after the final accepted read; this route
binds the returned snapshot, not future source state. It creates no timestamp.

## Native consumer and Paper binding

The planned native consumer is the existing `/prophet` owner with
`tab=candidates`, existing `symbol` for detail and existing `prophetQ` for
committed search. It retains the parent account lifetime and existing URL owner.
The canonical Today default, model plans/options and Sector journey remain.
It must display every accepted candidate, distinguish main-list membership,
screen position and final score, and show the source session explicitly.

Paper: [Prophet P4 page p-L-0](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-L-0).
Boards: desktop Light EN `29W6-0`; 390px Dark ZH `2A11-0`; candidate detail
`2A19-0`; availability/return states `2A50-0`. All candidate names/numbers in
these design boards are explicitly synthetic. Parent token catalog remains
`640746f9`; no new token authority is created. The phone contrast and desktop
CTA-fit repairs were visually read back.

The state design distinguishes verified empty, no search matches, source
unavailable, restricted access, unsupported market and requested symbol absent
from an otherwise valid publication. Generic model-plan navigation must not
claim a candidate-to-plan match. US→other-market→US retains the task without
fetching or relabeling US candidates as another country's data.

## Verification and remaining acceptance

The isolated route-boundary suite passed 78 tests with 11 deliberately excluded
assembled-runtime cases. The scratch test runner used an explicitly marked
authentication import stand-in because the sparse local harness lacks Prophet
Lab's application dependencies. The candidate projector and source reader were
the actual source. This is not real authentication or production proof.

Coverage includes a 97-row population, source-order retention, valid zero score,
off-list null scores, unknown versus empty, private field exclusion, invalid
queries before admission, exact-size bounds, malformed/nonfinite input, raw
source replacement with unchanged display digest, final-read/serialization/
projection failures, recovery and contention with Daily Brief in both directions.
The published real-auth-chain test covers both routes and 401/403 while busy.
The new assembled-app test checks the existing mounted router and entitlement
call with synthetic substitutions. These and the unchanged authority-fence
suite remain binding CI obligations; live entitlement and consumer acceptance
remain separate production obligations.

Release sequence: qualify this backend at its exact head, use the incumbent
protected Macro merge/deploy path, verify the served endpoint with entitled
source evidence, then qualify and release the native Terminal consumer. Keep
`/us_stocks.html` available until its full feature and access parity is proven.
No legacy source/presentation retirement is authorized by this API result alone.

## Preserved active effects

Macro #10674's unresolved operation 26751 and held 449-file branch are neither
adopted nor replayed. This slice is independently authored from protected source.
The inspected #10674/#10780/#11217/#11227 changed-file sets do not own this route
or its two test files; their other effects remain untouched. #10780's app/main
and build ownership, #7255's registry/order ownership, and Terminal #574/#668's
`ProphetView.tsx` work remain outside this slice. P3 Liquidity #11246 is a
separate in-flight API change with no shared implementation files.
