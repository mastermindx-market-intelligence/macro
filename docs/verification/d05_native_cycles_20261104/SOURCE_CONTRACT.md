# D05 additive source and entry contract

This contract describes this implementation candidate. It supplements the
programme's complete 13-route `DATA_BACKEND_CONTRACT.md`; it neither changes the
canonical route registry nor supplies missing source-owner acceptance.

## 1. Existing producers and transport

| Producer | Existing output prefix | Region / namespace |
|---|---|---|
| `scripts/build_sector_cycles.py` | `sector_cycles_` | `us` / `sector_cycles:us` |
| `scripts/build_china_sector_cycles.py` | `sector_cycles_china_` | `china` / `sector_cycles:china` |
| `scripts/build_country_cycles.py` | `country_cycles_` | `intl` / `sector_cycles:intl` |

Each prefix retains four files: `data.js`, `series_data.js`, `narr_data.js`,
`dna_data.js`. Their native globals remain `SECTOR_CYCLES`,
`SECTOR_CYCLES_SERIES`, `SECTOR_NARR`, `SECTOR_DNA`. The existing split helper
remains pure/lossless and keeps entity objects compatible with existing readers.
The new serializer is `scripts._cycles_payload.publication_scripts`. It emits
one exact JSON payload string per part and parses it into the native global.
No new fetch endpoint, release pointer, publisher, cache service or data store
is introduced. Existing build/publication owners still publish the files.

All entity IDs across the four family lists must be nonempty, unique strings.
`asOf` must be an exact valid `YYYY-MM-DD` session date. Invalid/non-finite JSON
cannot be published. These checks intentionally fail the producer instead of
shipping a coherent-looking identity collision or non-session timestamp.

## 2. Sector-input identity

`engine.sector_generation_guard.cycle_spine_identity(payload)` returns either
`null` or this receipt:

| Field | Type / meaning |
|---|---|
| `schema` | Literal `sector_cycles.sector_spine.v1` |
| `scope` | `us_sectors_11` for US; `<region>:sectors` for other native sector lists |
| `sha256` | Lowercase 64-character SHA-256 of the canonical Python serialization |

The hashed input contains schema/scope, full native metadata except
`n_baskets`, `families`, `publication`, all phases, and complete sector records
sorted by native ID. It includes price/history arrays, benchmark, methodology,
parity and semantic fields actually present. Duplicate sector IDs/tickers or an
invalid source session produce `null`. Missing sectors do not become zeros.

Central calls the helper on the actual input already passed into
`measured_group_read`; the receipt is additive under
`measured_read.generation.cycle_spine`. It is not copied from a later file on
disk. The prior `generation.id`, measured values, cohort coverage, research
status and event semantics remain unchanged. The golden fixture includes only
this deterministic addition. Other consumers must qualify their own use;
Terminal adoption is not asserted by a Macro fixture update.

The Cycles manifest contains the same receipt under `sector_spine`. A Central
sector handoff compares session, receipt schema/scope and digest. A basket,
Nasdaq or Russell record cannot be admitted by a sector fingerprint. It can be
opened explicitly as its own dated Cycles source; no Canadian ticker is
remapped to a US listing and no Canadian sector-cycle cohort is invented.

## 3. Publication manifest

The core script adds companion `SECTOR_CYCLES_PUBLICATION`:

| Field | Required value / meaning |
|---|---|
| `schema` | `sector_cycles.publication.v1` |
| `id` | `cycp1-` plus SHA-256 of the exact `manifest_json` UTF-8 bytes |
| `region`, `namespace` | Native region and namespace from section 1 |
| `as_of` | Exact source session, equal to core `meta.asOf` |
| `benchmark` | Native benchmark or null; never a substituted display benchmark |
| `basis` | `current_reconstruction`; not point-in-time availability |
| `sector_spine` | Receipt from section 2, or null when not available |
| `sources` | Independent `narr` and `dna` source dispositions |
| `payload_sha256` | Exact SHA-256 strings for `core`, `series`, `narr`, `dna` |
| `manifest_json` | Canonical JSON of the nine identity fields above, excluding `id` and both raw strings |
| `payload_json` | Exact serialized core bytes as a JavaScript string |

Payload JSON uses Python `sort_keys=True`, compact separators,
`ensure_ascii=False`, `allow_nan=False`, then UTF-8 hashing. The JavaScript
literal safely escapes that exact string. The browser never attempts to
reproduce Python float formatting or canonicalize the parsed object. Manifest
and payload bytes are checked before display cleanup affects parsed strings.

The core hash excludes its companion manifest, avoiding a self-referential
hash. The publication ID includes all four part hashes and source dispositions.
Identical content yields identical identity; a narrative-only change changes
the bundle ID without falsely changing sector-input identity.

Each other companion global (`SECTOR_CYCLES_SERIES_PUBLICATION`,
`SECTOR_NARR_PUBLICATION`, `SECTOR_DNA_PUBLICATION`) contains:

| Field | Required value |
|---|---|
| `schema` | `sector_cycles.part.v1` |
| `publication_id` | Exact active core publication ID |
| `namespace` | Exact core namespace |
| `kind` | `series`, `narr`, or `dna`, matching the requested receiver |
| `sha256` | Exact manifest part digest |
| `payload_json` | Exact serialized part string |

The source receipt projects the existing narrative resolver: `status` is
`available`, `quarantined`, or `unavailable`; `reason` is null,
`epoch_mismatch`, or `missing_or_unreadable`; `epoch`, source basename and record
count remain explicit. An available empty map is distinct from a missing file.
If a builder does not supply source receipts, annotations remain unverified.
Narrative `as_of`, TTL and revisions are not reset to publication time.

## 4. Receiver and failure contract

`SectorCyclesEvidence()` returns `sector_cycles.evidence.v1` with effective
status, publication ID, source session/region, usable spine only when verified,
per-part states and source dispositions. If the captured core or manifest object
is replaced, the effective status is `superseded` and no usable spine is returned.

| State | Meaning / product treatment |
|---|---|
| `pending` | Verification/loading still underway; no success claim |
| `verified` | Exact bytes, identity and shape accepted for that core or part |
| `legacy_unverified` | Unstamped archive; readable only as explicitly unverified own evidence |
| `invalid_payload` | Missing/malformed envelope, unsupported shape or manifest fields |
| `incompatible_publication` | Wrong bundle, namespace, role or expected part identity |
| `integrity_failed` | Exact bytes or manifest contents fail the declared digest |
| `verification_unavailable` | Required verification mechanism cannot complete |
| `source_unavailable`, `quarantined` | Optional source could not legitimately supply annotations |
| `unavailable` | Transport failed |
| `superseded` | Captured core is no longer the active source; receipt cannot authorize a read |

The renderer accepts only known series IDs and the existing heavy-field
allowlist. It mutates accepted records in place, preserving references held by
Central. Async completion is fenced by captured core/manifest identity and a
per-part operation epoch. A stale callback cannot mutate or announce success
for a replacement core. Verified empty series are different from malformed
series. The selected instrument's lack of price history remains unavailable,
even if an empty part itself was valid.

Optional narratives and DNA are checked independently. Their accepted maps,
not raw window globals, supply the detail panel. Preloaded annotations pass the
same checks. Failure of one annotation cannot invalidate valid core/series.
There is no silent stamped-to-legacy fallback.

Central reconstructed history requires the active core, matching source spine,
and verified detailed series before drawing any points. Central mini charts
also gate before cache lookup; sector charts require the matching spine, and
theme charts carry a separate dated-snapshot label. Publication replacement
invalidates their cache authority. Loader success/global existence is never
accepted as source proof.

## 5. Host apply contract and source policy

`SectorCyclesApply(context)` accepts native `id`, optional `family`, source
`asOf`, `requireSourceDate`, expected `spine`, `requirePublication`, `entryKey`
and an optional analytical `snapshot`. It returns a typed receipt:
`pending`, `unsupported`, `source_unavailable`, `source_mismatch`, or `applied`.
The receipt also identifies source date/publication, family, detailed-series
availability, restoration outcome and leg restoration/pending/unavailable state.
A hidden chart container cannot yield `applied`.

`SectorCentralOpenCycle` creates the stricter Central handoff and clears
`cycleSource`. An explicit readable own-snapshot choice uses
`cycleSource=latest`; the term means the loaded Cycles snapshot, not a promise
of present-day freshness. That choice retains the Central origin. Direct user
interaction on an already admitted Cycles canvas persists the same source mode
before subsequent data/language events. A failed core integrity check never
exposes a usable latest-snapshot button.

## 6. One bounded browser-entry snapshot

`history.state.siWorkspace` uses `sector_central.entry.v1`:

| Field | Owner / validation |
|---|---|
| `entryId` | Opaque per-entry identity; never a history-stack index |
| `href`, `view` | Exact local pathname/query/hash and an existing Central view |
| `measured` | `sector_central.measured_view.v1`; URL-owned group, obs/recon lens and exact producer generation |
| `cycles` | `sector_cycles.view.v1`; fields below |
| `viewport` | Bounded finite scrollY plus a typed whitelisted focus locator |

The Cycles snapshot contains exact publication ID, region, family, nullable
focus, mode (`osc`/`price`), scale (`log`/`linear`), finite bounded range, known
phase keys, known active-family comparison IDs, mobile leader/all/explicit
selection, and a nullable leg identified by stable start/end dates. Empty
comparison selection is meaningful. Unknown IDs, another family, invalid range,
unsupported schema or old publication cannot partially restore a misleading
state. A fresh entry uses defaults. Saved transient modal chrome is excluded.

Capture replaces the current entry; it does not spam history. Delayed viewport
capture is bound to the entry ID and href. Restoration suppresses renderer
callbacks, cancels the previous chart tween, applies validated analytical state,
then restores host focus/scroll after layout. Hydration and language rerenders
preserve stable leg/control identity without replaying leg zoom or scrolling.

`siCyclesOrigin` is the single bounded local origin envelope. Return validates
same origin/path, no credentials and an existing non-Cycles view; it performs
ordinary local navigation with the bounded origin entry. It never infers Back
adjacency from history length. Foreign history fields, F01 `originNav`, native
Back/Forward, browser scroll-restoration policy and shared-shell ownership are
preserved. No localStorage, sessionStorage, new router or server save is added.

## 7. Evidence and builder obligations

Run the exact focused command in `source_validation.json`; review actual
changes and paired authored/generated assets. Use labelled local scenarios from
`prepare_preview.py`, then `verify_browser.cjs` on an admitted host. Capture
actual screenshots at the seven declared responsive/language/theme cases.
Core/part coherence tests do not prove point-in-time data, correction lineage,
predictive validity, production auth or visual acceptance.

Existing build owners must regenerate all four files together and build Central
from matching sector input before an aligned production journey is possible.
Partial publication remains fail-closed. The original route, Company, regional,
scientific, auth, foundation, CI and release owners retain their acceptance
conditions. No release action is authorized by this file.
