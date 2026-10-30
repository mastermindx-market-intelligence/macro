# Shared Shell bridge principal review — 2026-10-18

## Decision and scope

The supplied bridge snapshot is not ready for release until the navigation, URL filtering, and readiness defects below are corrected. The ACK notification implementation is sound within the stated protocol. A separate lifecycle defect requires a persisted-pagehide fix and browser confirmation of restoration behavior.

This is independent reasoning over source snapshots supplied and SHA-verified by the root; it is not independent source retrieval. I read the bridge, the parent host's admission/message/lifecycle code, the boundary contract, and relevant test harness/regressions. I made no application-source changes and performed no network, browser, Git, CI, or deployment actions. I ran bounded in-memory probes using the supplied test harness and actual source. The harness's only adaptation was its source-file lookup, pointing to the supplied local snapshot. The parent URL predicate was executed with its TypeScript signature removed, preserving its implementation and constants. These are VM/source proofs, not browser acceptance.

### Snapshot identities

- shared_shell_bridge.js: 5e67e459bfbdb195c6de97e4d481521cca7515b2e205ef886aa31b1050a12f3d
- LegacyPageHost.tsx: 06795fb571d2ac126b472da796e0d2429049f32ff77b62a6195615f0b6d3059b
- sharedShellContracts.ts: e416e24178741803b49c7fed66ae6651e726ef6e0b5d0565909636c6f2cbff61
- shared_shell_bridge.test.cjs: debe73a962505b9b36a6fc5f5e5ceaf0aa553ddad46f404719d8655cbfe2f1c6

## R1 — Cross-pathname history changes mutate the wrong document and are rejected by the parent

**Source:** shared_shell_bridge.js 351–386; LegacyPageHost.tsx 187–211.

The active history wrapper resolves a same-origin URL, admits its pathname, replaces the child's history/location, then always sends NAVIGATE with sameDocument:true (384–386). The parent correctly refuses same-document requests whose pathname differs from the rendered legacy route (193–195). Thus a page at /tools calling pushState or replaceState for /dashboard leaves the child showing the /tools document under a /dashboard URL and places the host in its failed boundary.

Before INIT the wrapper is worse: it replaces the child location before catalog admission (374–376), and the queued handler later always labels the request same-document (351–356). My probes for both pushState and replaceState reproduced a child URL change to /dashboard before any message was sent; after INIT the bridge sent sameDocument:true and READY for /dashboard even though the loaded document was /tools. Active probes likewise produced the wrong same-document flag after replacement.

**Smallest safe fix:** classify pathname against the actual current document before changing child history. For a different pathname, queue or emit ordinary parent navigation with sameDocument:false, preserving the requested push/replace mode and leaving child URL/history/state unchanged. Preserve same-path query/fragment replacement and its existing transport-byte behavior. Pre-INIT queue admission must succeed before any mutation; queue-full refusal must not change the child. Validate unknown destinations when the catalog becomes available.

**Bounded regression set:** parameterize push/replace × pre-INIT/active for a different legacy pathname and one native destination; assert zero child replacement, correct requested mode, and sameDocument:false. Retain same-path query/fragment and byte-preservation coverage on /tools. Add one full pre-INIT queue case asserting no mutation.

## R2 — Authentication material can cross the bridge in URLs

### Direct fragment parsing

**Source:** shared_shell_bridge.js 69–113, 340–348.

paramPairs.add removes a leading question mark but not a leading hash. The direct fragment #access_token=value is parsed with the key '#access_token', so the first sensitive parameter is missed. The same defect admits a first refresh_token and type=recovery. My probes showed navigate('/tools#access_token=SYNTHETIC_REVIEW_VALUE') returning true and emitting NAVIGATE containing the complete synthetic value. The native reader rejects the direct-fragment form later, but that does not undo the cross-window disclosure.

### Initial URLs and contract disagreement

**Source:** shared_shell_bridge.js 186–191, 736–746, 876–931; sharedShellContracts.ts 141–154; LegacyPageHost.tsx 100–105, 171–183.

currentCanonical and sendReady do not apply the URL sensitivity filter. The native predicate does not recognize parameterized route fragments such as #tab?access_token=value, and it classifies query and hash separately, missing a code in the query combined with onboard in the hash. Executing the actual native predicate and child harness showed both /tools#tab?access_token=SYNTHETIC_REVIEW_VALUE and /tools?code=SYNTHETIC_REVIEW_VALUE#onboard=resume being admitted and then copied into READY.

### Credentials in history URLs

**Source:** shared_shell_bridge.js 360–386, contrasted with API 1067 and anchor 539; sharedShellContracts.ts 141–154.

The history wrapper checks origin but does not reject username/password components. A credential-bearing URL has the same origin. Both pre-INIT and active replaceState probes emitted a NAVIGATE containing synthetic username/password values; the pre-INIT probe also emitted READY with them. Even if a real browser refuses the history rewrite, origReplaceSafe swallows the exception, and the wrapper still emits the supplied canonical URL. API and anchor paths already reject these credentials.

**Smallest safe fix:** normalize the fragment prefix before child parameter parsing; reject sensitive or credential-bearing current URLs before any READY; reject credentials before history mutation/queueing. Align the native predicate with direct fragments, route fragments, case normalization, and combined query/hash classification so it rejects these URLs before iframe admission. Keep transport removal byte preserving; do not solve this by broadly reserializing ordinary presentation parameters.

**Bounded regression set:** direct secret fragment as the first parameter through API, anchor, pre-INIT history, and active history; initial route-fragment secret and split query/hash recovery context; one credential-bearing history URL in pre-INIT and active states. Assert the synthetic marker never appears anywhere in outbound messages and no prohibited child mutation occurs. Mirror representative URL classifications in the native predicate tests. Ordinary symbol/query/hash examples must remain admitted.

## R3 — Context acknowledgments can falsely report applied presentation

**Source:** shared_shell_bridge.js 620–655, 666–685, 736–780, 887–894, 934–948; LegacyPageHost.tsx 180–183.

Initial READY proves theme, data-lang, and normalized html.lang. Later CONTEXT and repeated INIT acknowledgments call sendReady without that proof. An incumbent setter can return normally while leaving the opposite presentation; applyContext then advances appliedRevision and the bridge emits READY for that revision. The parent treats the matching revision as ready.

My probe activated the page successfully, then installed setTheme that writes dark and supplied CONTEXT requesting light at revision 4. The document remained dark while the bridge emitted READY with contextRevision:4 and no error.

**Smallest safe fix:** require the presentation proof before every READY, including subsequent CONTEXT and repeated INIT. Emit the appropriate existing failure code when proof fails. Keep successful recovery possible after the actual setter/presentation becomes compliant; do not mark a still-contradictory setter as successful in tests.

**Bounded regression set:** post-readiness CONTEXT with a contradictory theme setter and a contradictory locale attribute pair; repeated INIT with the same behavior; successful later recovery after restoring the compliant setter. Ensure no repeated initial scroll/focus restoration occurs for context acknowledgments.

## R4 — Persisted pagehide irreversibly disables a restored bridge

**Source:** shared_shell_bridge.js 1025–1047, 1088–1094, with installation guard 46 and marker 142.

Every pagehide invokes full cleanup. The handler ignores event.persisted, removes the message listener, restores native history, deletes the public API, and leaves the installed marker true. There is no pageshow restoration handler. My lifecycle probe dispatched pagehide({persisted:true}), pageshow({persisted:true}), then valid INIT: the API remained undefined, there were zero message listeners, native history remained restored, and INIT produced no messages.

This source behavior will break a document that the browser restores from its back/forward cache. Browser cache eligibility and an actual cached restoration were not tested in this lane, so the user-visible reproduction remains conditional on retention.

**Smallest safe fix:** distinguish persisted pagehide from actual document destruction. Preserve the live bridge for a retained document, or implement an explicit owner for reactivation; retaining it is the smaller change. Full cleanup should still occur for non-persisted destruction.

**Bounded regression set:** persisted pagehide/pageshow preserves API, history interception, origin/generation validation, and functional navigation; non-persisted pagehide still cleans up. Confirm one real browser Back restoration during release verification where cache retention actually occurs.

## ACK implementation: no blocker found

**Source:** shared_shell_bridge.js 950–972; LegacyPageHost.tsx 193–207; bridge tests 1384–1433.

The parent commits accepted canonical history before posting LOCATION_ACCEPTED. The child checks the exact envelope, latest outstanding request ID, same child origin, credentials, sensitive URL classification, and equality with its actual current canonical location. It clears the outstanding request and updates lastLocationNotified before synchronously dispatching on the child window. That ordering prevents a same-value history call in a subscriber from creating an event loop. Duplicate and superseded ACKs are inert; native hashchange is not fabricated. The existing three window-subscriber tests exercise relevant behavior rather than a document-only event sink.

## Other reviewed boundaries

The child receives messages only from the exact referrer-approved parent origin and parent WindowProxy with the current protocol/generation (987–1000). The native reader checks exact child origin, iframe WindowProxy, protocol/generation, bounded data, and closed message fields (sharedShellContracts.ts 169–225). AUTH_REQUEST carries only one of four intent values and is handled by the existing native onboarding/settings owners. API navigation refuses unsupported modes and arbitrary external origins; the bridge itself does not perform a fallback navigation after refusal. Anchor projection and unmodified-click interception deliberately preserve modified-click, download, and external-link handling.

The DOMContentLoaded repair now remembers the event before late INIT, does not treat interactive alone as ready, arms only the shared listener, sets pendingInitialReady before draining queued callbacks, and proves initial presentation. I found no additional initial-readiness blocker in that mechanism beyond the initial-URL and subsequent-acknowledgment defects above.

## Release judgment after corrections

Re-run the affected owned regression groups, inspect the final source delta, and perform the required actual browser acceptance. The original supplied snapshot is blocked by R1–R3. R4 is a concrete source lifecycle defect with conditional browser manifestation and should be repaired before claiming robust Back/restore behavior. This report does not approve a later revision, deployment, or browser experience that this lane has not inspected.


---

## Bounded correction review — current source delta

### Scope and identities

I inspected bridge-current.diff, parent-current.diff, and their corresponding current source files. I independently recomputed the local snapshot hashes:

- shared_shell_bridge.current.js: 9e98cc403b65a433d2699885c793dcd8c95a656296d400074c977f5d7e5cb554
- sharedShellContracts.current.ts: dc7c893852c287b2a18c6b71cbced07bfa0996c1168490c5a8c24e4d3de01266

The root reports that the bridge hash matches the actual M2 working tree and that its comparison of the parent contract hash with M2 is next. I verified the local bytes only. This pass was limited to R1–R4 and their credential/split-query subcases; it was not a new broad audit. I did not edit application code or use remote tools, network access, or a browser.

### Closure judgment

**R1 is closed in the inspected delta.** Current bridge 351–356 retains queued sameDocument classification. Lines 368–379 reject credentialed input, classify the target pathname before mutation, and mutate a same-document URL only after enqueue succeeds. Lines 384–390 admit the target and route a different pathname to the parent with sameDocument:false before any child replacement. Requested push/replace mode remains intact. The existing same-path path retains its view flush, transport-preserving local replacement, and same-document parent notification.

**R2 is closed for the reported cases.** Current bridge 87 removes the leading fragment marker before parsing. currentCanonical at 187–191 rejects both credentials and sensitive URLs, preventing initial READY from carrying them. The history entry point at 368 rejects credentials before queueing or mutation. The native predicate at sharedShellContracts.current.ts 142–164 rejects credentials, recognizes direct and route-fragment parameters, normalizes key/value case, and aggregates code/onboard classification across query and fragment. resolveShellTarget now invokes that predicate at line 80 for exact first-party destinations after external-origin classification. Consequently its routing path also enforces the corrected boundary; external-link behavior remains outside this first-party auth filter.

**R3 is closed in the inspected delta.** All READY messages now pass through proofAppliedContext in sendReady at current bridge 741–748. Initial failure uses initialization_failed, while a failed later acknowledgment uses unsupported_context. The proof covers theme, semantic data-lang, and normalized html.lang. The existing initial boot restoration still runs before initial READY; later acknowledgments do not acquire a second initial restoration.

**R4 is closed at the source lifecycle boundary.** The pagehide wrapper at current bridge 1098–1101 preserves the existing owners for event.persisted === true and retains full cleanup otherwise. This addresses the irreversible teardown demonstrated in the original snapshot. An actual browser cached Back restoration remains part of browser acceptance; this local pass makes no claim about observed cache retention.

The ACK dispatch code is unchanged by these corrections, so the earlier favorable judgment on latest-request/canonical checks, pre-dispatch deduplication, and actual child-window delivery remains applicable.

### Bounded executable verification

I replayed the previously demonstrated failures using the original supplied harness with its in-memory source lookup redirected to shared_shell_bridge.current.js. I also executed the current native URL predicate after removing only its TypeScript signature. All 16 bounded checks passed:

- Cross-path queued and active push/replace: four cases; no child mutation and sameDocument:false.
- Full pre-INIT queue: no same-path child mutation on refusal.
- Credential-bearing history before and after INIT: two cases; no NAVIGATE or credential value in outbound messages.
- Direct access_token, refresh_token, and recovery type fragments: three cases; refusal and no NAVIGATE.
- Initial route-fragment token and split query/hash code/onboard: two cases; native rejection, no READY, and no synthetic marker in outbound messages.
- Contradictory setter on CONTEXT and repeated INIT, followed by compliant-setter recovery: two cases; no false READY and successful later revision 5 acknowledgment.
- Persisted and non-persisted pagehide: two cases; the retained document remains navigable, while destruction removes the API/listeners and restores native history.

These checks independently validate the reported mechanisms. The root's broader 179/179 working-tree result was reported to this lane, not rerun or independently observed here.

### Result

**No unresolved blocker from R1–R4 remains in these exact local source deltas.** This correction note supersedes the initial blocked judgment only for the identities listed above. Final parent-source custody comparison and the programme's actual browser/deployment acceptance remain with the root; they are outside this bounded source-delta judgment.


## Root custody completion

The actual M2 parent contract was subsequently hashed as dc7c893852c287b2a18c6b71cbced07bfa0996c1168490c5a8c24e4d3de01266, matching the reviewed source. Root-owned working-tree verification passed 179 bridge/navigation/owner/handoff tests and 91 native contract/header/auth/status tests plus TypeScript checking. This records source custody and owned regression results; actual beta browser/deployment acceptance remains pending.
