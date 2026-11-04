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

## 8. Company receiver: verified boundary and joint integration requirements

Receiver inspection is pinned to **mastermind-terminal #1244** at
`624dbc0ac22ecdaa6d1bd580d5221da939c5e5a9`, in repository
`mastermindx-market-intelligence/mastermind-terminal`. Earlier `/terminal`
repository links in the design packet were stale aliases, not evidence that a
receiver or permission was absent.

The current Macro `MDXTerminal` / `terminal_overlay.js` owner intercepts native
stock links and builds its existing `/terminal?sym=...&from=macro&ret=...`
handoff. In standalone Macro the overlay keeps the source document mounted;
the shared-shell path delegates to its admitted native route. Preserve this
carrier until its receiver-qualified replacement exists. Directly substituting
`/analysis` links would bypass that existing lifecycle.

At the inspected Terminal head, Company accepts exact dotted/dashed listing
syntax through `/analysis?symbol=...`. Syntax acceptance does not prove source
resolution. Preserve `CNQ.TO`, `300308.SZ` and `9988.HK` exactly; do not substitute
an ADR, invent venue/currency metadata or treat quote and statement currency as
one field. Ordinary constituent navigation must omit `company_query`; that
parameter describes an actual Company search, and an empty value still creates
search provenance in the current receiver.

The current cross-product return is incomplete:

| Existing owner | Verified limitation |
|---|---|
| `sharedShellContracts` | `VIEW_STATE` is closed to `{x, y, focusId?}`. It does not accept D05 analytical entry state. |
| `LegacyPageHost` | Native Company navigation removes the legacy iframe. Parent scroll/focus snapshots do not preserve the child `siWorkspace` / `siCyclesOrigin` state. |
| `originNav` | A safe `ret` URL is retained; assigning that URL creates navigation, not proof that an earlier analytical entry was restored. Its hook reads origin on mount. |
| `AppShell` | Existing desktop/mobile Macro return affordances are hidden under shared-shell mode. |
| Shared-shell receipts | `READY` means document/context readiness; `LOCATION_ACCEPTED` acknowledges same-document location. Neither means Company data loaded or D05 analytical state applied. |

The joint increment belongs in these existing owners. It must provide a named
return action and preserve a bounded, entry-specific snapshot through the
existing parent/child navigation ownership, without a second return store,
router or protocol. Its receive/apply distinction must bind document/context
generation, account/access scope, exact local return route and actual source
publication. Same-date source replacement must not restore old analytical
settings. Late callbacks from the departed iframe must not repopulate a new
entry or account. Invalid, expired, incompatible or missing state needs a
truthful URL-only fallback; it must not report an exact analytical restoration.

Prove constituent → exact Company → named return separately from browser
Back/Forward. Include two same-URL investigations, reload, modified/new-tab
navigation, regional listings, account/access change, publication correction,
late source arrival and keyboard focus. The existing local D05 entry tests do
not establish this cross-product outcome. F01/F02 acceptance and release holds
remain in force while incumbent source custody is reconciled.

## 9. Pure export of the currently serialized entry settings

`SectorWorkspaceExport()` returns either `null` or a detached projection:

```js
{
  siWorkspace: /* existing sector_central.entry.v1 */,
  siCyclesOrigin: /* null or { href, entry: existing entry or null } */
}
```

This is a projection of the current native history fields, not a new transport
schema. It performs no history write, route, render, focus, scroll, load, event
or persistence effect. The existing persisting `SectorWorkspaceCapture()`
remains available to its current callers. A bridge view-flush must use the pure
export rather than that persisting hook, which could recursively re-enter the
bridge through `replaceState`.

The collector requires the exact current href, active entry ID and active view.
A current Cycles projection additionally requires the last admitted host context
for that entry/href plus a live verified publication receipt matching captured
publication ID, region, family and focus. Publication status is re-read, so a
superseded core cannot reuse its former authority. Exported settings do not
certify that delayed series or a selected leg have rendered successfully.

The result contains only the fields listed in section 6: no `originNav`, unknown
history keys, DOM objects, source arrays or recursive origin chain. Strings,
collections and viewport values have explicit bounds; each comparison/mobile
list is limited to 512 IDs, and the entire projection including one origin is
limited to **32,768 UTF-8 bytes**. An origin entry must agree with its validated
local non-Cycles href/view. An invalid attached entry is withheld while a valid
URL-only origin can remain. Returned nested arrays and objects share no mutable
reference with the live entry or renderer.

This interface covers the **currently serialized entry settings**. Map
scope/horizon and other unrepresented filters are outside it. A null or partial
source field must never be presented as complete workspace restoration.

No external import/apply API is delivered in this increment. The eventual
joint receiver must apply to an already-active matching entry, retain the
new destination entry ID, validate source before effects and distinguish
pending/restored/partial/rejected. Existing `SectorCyclesApply.status=applied`
is insufficient: invalid/source-changed snapshots can use defaults, series can
remain pending/unavailable and a leg can remain unrestored. The measured
receiver likewise currently returns no restoration receipt. Neither READY nor
LOCATION_ACCEPTED closes these obligations.

The native viewport replay now observes later pointer, touch, wheel and keyboard
intent through its existing generation guard. Input that caused navigation
precedes activation; later input cancels the queued correction. It neither
prevents input nor changes browser scroll-restoration policy.

## 10. Joint Company-return implementation — 2026-11-04

This increment composes on `dd903b3866e45eb25665c73629ac6dcfd409b222`.
It retains the Theme absence correction, reduced-motion changes, preview fonts/icons
and exact-source browser-runner repairs from that revision.

### Single entry and navigation owners

Terminal's existing `originNav` owns one pending transition and a bounded record
on the actual browser history entry. The original `mmxSharedShellEntry` key is
retained. `mmxOriginEntry` binds schema, verified account owner, entry key, exact
canonical URL, revision, current view and one flat return snapshot. It never
contains tokens, source rows, another return record or an index into a departed
iframe's memory. Complete owned history is limited to 40 KiB UTF-8.

The existing Next router performs navigation. A layout-effect commit runs after
Next's HistoryUpdater insertion effect, samples the actual raw browser URL, and
merges the new owned record into Next's freshly committed state. Next's router
tree is never copied from the old entry. A verified existing record is published
after commit, preserving server/hydration agreement. Unknown identity supplies
no guest or account grant; supplied guest/account identity comes from the
existing shell server props.

A Company handoff freezes the source entry/revision/settings and stages the
exact `/terminal` URL. The destination records that copied origin only after
actual URL and identity agreement. Named return stages the source canonical
URL, uses Next push with scroll disabled, and creates a new entry key. It does
not assume adjacency or call history.back. Back/Forward instead reads the
traversed entry's own record, including between identical URLs. Reload needs
neither the old iframe nor the pending in-memory transaction.

Traversal, identity change, incompatible navigation, a newer transition,
superseding source settings and document exit retire pending work. A source
render while Next is still loading does not retire it. Same-URL replace is
bookkeeping and preserves the captured view/revision; a push creates a distinct
entry. A same-URL Next refresh can recover the controller's single current-entry
record after Next replaces custom fields; traversal first clears that cache.

The existing iframe host remains the document owner. Its dependency is the
committed owner/entry/canonical tuple. Every late child message is checked
against current browser history before it can save or navigate. An old live
reference alone is insufficient.

### Closed shared-shell extension

The bridge version is **20261104.1**; the document capability remains
**20261018.1**. Actual running sibling status and child READY must agree with
the parent version gate. Deploying one half is not a compatible release.

`VIEW_STATE` retains x/y/optional focusId and adds only:

```ts
page?: {
  kind: "d05-sector-central";
  value: { siWorkspace: ExistingNativeEntry; siCyclesOrigin: ExistingLocalOrigin | null };
}
```

The existing 32 KiB UTF-8 projection is closed and detached. Native fields and
their limits are enumerated by the actual parent validator; arrays, numbers,
nested objects, relative same-page hrefs and source identifiers are checked.
Unknown fields, foreign/credential/authentication URLs, copied transport keys,
nonfinite coordinates and nested origins are refused. Account and parent-entry
identifiers are never child-supplied fields.

The child calls **SectorWorkspaceExport**, never the persisting Capture hook.
Only the existing bridge strips/rebinds `mmx_shell` and `mmx_generation`;
ordinary query order, duplicate keys, percent encoding and hash remain intact.
The native owner accepts only its exact actual local href.

`INIT.restore` adds `restoreId` and `snapshotId`. One qualified
`RESTORE_RESULT` contains those identifiers, canonicalPath, outcome
(applied/partial/rejected), bounded reason, actual publicationId, focus status
and viewport status. Envelope origin/source/new-frame-generation still apply.
READY proves document readiness; it never proves analytical restoration.

While restoration is pending, initial default VIEW_STATE messages cannot
overwrite the requested snapshot. The terminal result precedes the next actual
view flush. Repeated INIT is idempotent. An existing-host 15-second completion
deadline sends exact-request `RESTORE_CANCEL` and ends pending as rejected;
the child itself has a 12-second deadline and cancels the native transaction.
Neither deadline retries a request or records success. A later valid user view
can then be saved.

### Native application and qualified outcomes

`SectorWorkspaceApplyCurrent(projection, options)` is the sole application
owner. It binds the incoming request to the current child entry ID, href,
view and intent generation; preserves the destination ID/foreign history;
never routes; and writes its own final bookkeeping with an omitted history URL.
It holds one requested projection outside live history until source preflight
succeeds. A repeated restore ID with different input is rejected.

The existing `SectorCyclesApply` gains opt-in `strictRestore` and
`validateOnly`. Strict input is checked before default fallback or chart
setting changes. Exact current publication/region/family/focus, range,
unique selections/phases, mobile semantics and stable leg identity must agree.
Price and nonsector history require the verified series part. Native callers
without the strict option keep their existing fallback behavior.

Measured restoration requires the original group and a non-null matching
generation. Apply is followed by capture equality, so observed history silently
falling back to reconstruction cannot be called restored. Cycles readback checks
all supported settings, set membership and the chart's numerical range
tolerance. Publication is re-read before final success. Source-ready events
resume pending work without repeatedly forcing old controls after application.

The typed viewport has one writer: the native owner for D05. Completion is
reported after the guarded animation frames, actual scroll and actual focus
readback. Clamping, missing focus, source changes, unavailable series/legs,
supersession or later pointer/touch/wheel/keyboard input yield partial/rejected
outcomes. Later input cancels outstanding work before it can overwrite the
user's changes. Bilingual native feedback distinguishes restored settings,
interrupted restoration, source changes and incomplete restoration.

**Fidelity boundary:** this restores the currently serialized chart settings,
measured evidence lens and typed position/focus. Unrepresented map horizon/scope
and other controls remain outside the projection. It is not complete arbitrary
workspace replay, observed PIT evidence, saved Research state or trade authority.

### Verification and outstanding gates

At this increment, exact candidate source executed:

- 79 bridge tests, including pure export, raw-query transport, ordered result/view,
  idempotence, input/cancel/navigation interruption and hostile requests.
- Seven native-entry executable cases, including four input kinds, pure bounded
  export and the new qualified current-entry restore case.
- Five actual Python-producer/real-WebCrypto receiver scenarios with strict
  no-fallback, unchanged-settings and source mismatch assertions.
- Terminal's original operation: all 97 tests in eight suites passed, including
  48 contract/controller/SSR hydration/mounted-host cases and existing route,
  status, primary-navigation and public-presentation cases. The Node 26 test
  worker receives the supported webstorage-disable option through NODE_OPTIONS;
  the presentation fixture now mounts the real entry provider, with its existing
  assertions unchanged. Fresh full TypeScript passed (exit 0, 72.49 seconds)
  before that presentation-fixture-only test repair.

These are source/lifecycle proofs, not actual browser or production acceptance.
Original browser/theme Fabric operations now report TERMINAL/rc0/root_verified,
but this parent's result-consumption projection remains false and acceptance
NOT_ACCEPTED. Their retained source repairs are separately present in dd903.
No uncertain effect was retried.

Terminal changes are prepared in the original #1244 operation at 624dbc,
with all 486 inherited untracked files verified unchanged. Publication is held:
the installed exact-HEAD publisher sweeps all unignored changes and its push
gate rejects inherited dirt. The existing publisher owner must supply a
supported exact-change/preserved-baseline path; no alternate publisher, ignore
change, artifact removal, branch replacement or release action is used.

The qualified Dossier component is available at 2c4edf26. It is not mounted by
this increment. Its source access receipt and native disclosure lifecycle are
a separate attachment to the same seven-view host. Original Fable dirty work
is preserved. Shared F01/F02 acceptance and all original release holds remain.
