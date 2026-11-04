# D05 — native Cycles implementation candidate

**Status: source candidate; browser/visual acceptance held.** This package does not
claim merge, production deployment, production proof, or final shared-design
acceptance. The Chairman's “Resume design and implementation” instruction
commissioned this bounded continuation; the original release holds persist.

## Scope and source binding

- Protected Mastermind law: `33aec27fff672a4f334cb79b3b2604156401597d`;
  INDEX 1.0.1 compatible. Unchanged Paper/continuity law blobs were reconciled.
- Macro base: `c53915f6d67078d5c0aeaf73bf85ddea1a23de03`.
- Work branch: `claude/d05-native-cycles-20261104`; root is the source writer.
- Active continuation plan: programme Draft #10617, commit
  `1467b6997d420ca5c95ac44235dac866ef949dd1`, D05 `BUILDER_INSTRUCTIONS.md`.
- Original D05 package: commit `22f6a887a621e82497ea256611835cee2ba6f079`;
  13 canonical routes, retained-feature ledger, source contracts and test matrix
  remain the programme baseline. This candidate implements one missing journey
  within existing Sector Central; it does not create a fourteenth canonical page.
- Paper: exact file `01M6FAXA774QT1VRDMAG7DFQ2W`, D05 page `p-3-0`,
  12 boards / 1,448 nodes, token hash `811c9dc5` read back unchanged. No Paper
  mutation or uncertain-effect retry occurred in this continuation.
- F01 #10645 and F02 #10630 are provisional inputs. Final shared acceptance held.

## What this candidate changes

`sector_central.html#cycles` becomes a native view in the existing Macro router.
The single existing chart/detail subtree moves from Market map into that view;
its family controls and native scorecards are exposed alongside the retained
price/cycle-position, log/linear, phase filter, zoom/Home, leg, narrative, DNA,
FX and pathway capabilities. The standalone page keeps the same renderer.
There is no iframe, new chart engine, independent navigation store, replacement
shell, duplicated model, authorization bypass or new market-data endpoint.

The measured-sector detail and existing sector-card cycle links enter this
native view. The host owns the URL; the renderer owns its chart interactions.
`g` and unrelated query/history fields survive. `cycle` and `cycleFamily`
separately preserve entity and family identity, including a family with no
focused entity. The 21 literal and 24 total compatibility anchors remain;
`sc-cyclemap` now routes to the native Cycles view.

The old renderer disabled embedded history listeners but still wrote an entity
hash inside `setFocus`. The new execution test reproduced that defect through
its public hook in shell, lazy and explicit-host modes. The repair guards the
writer, preserves foreign history state on standalone pages, and prevents a
language rerender from rewriting navigation.

Market map still loads cycle data for its own mini charts. The main chart and
scorecards wait for a visible box, then mount through the existing `si:view`
lifecycle. No second live chart subtree is created. Hydration preserves entity
object identity so existing Central references see the arrays arrive.

## Data and historical meaning

The archived input pair at the pinned Macro base contains an actual mismatch:

| Source | Observed value | Committed blob |
|---|---|---|
| Central `measured_read.generation.session_end` | `2026-10-30` | `65d7e6d6394963db9ea54fa5bde403cc3ad57d8a` |
| Cycles `meta.asOf` | `2026-11-02` | `c8574250f9b55ee8291e7d2af6b52024fc2dc370` |
| Cycles heavy series | Existing per-entity split chunk, no publication envelope | `9029d49fbce8134ffb644fe0f028b568dfdbbab7` |

A selected Central handoff with mismatched or missing dates is withheld.
**Open the current Cycles snapshot** is an explicit user action that retains the
older origin, displays the Cycles date, and labels the view **current
reconstruction**. It does not simulate an October 30 view by truncating a
November 2 chart. A general, unselected Cycles visit may show its own dated
snapshot without claiming alignment with Central.

`SectorCyclesApply` returns a typed receipt: `pending`, `unsupported`,
`source_unavailable`, `source_mismatch`, or `applied`, plus source date, family
and detailed-series availability. Hidden layout cannot yield `applied`.
**Equal dates prove only session alignment.** The producer does not yet bind
core, series and narrative chunks with the complete D05 publication/digest
contract. Same-date corrections, point-in-time vintage and cross-chunk
publication equivalence remain unproven and held for implementation/acceptance.

Empty/malformed heavy-series chunks produce unavailable state; unexpected
fields cannot overwrite core facts. Known records are hydrated in place. A
selected record with no price history does not receive a ready-history claim.

Rotation/fragmentation consume only the producer's `rotation_context` with
matching artifact and consumer sessions. The previous late raw-file fetch is
removed. Missing/mismatched inputs remain unavailable, distinct from an aligned
empty set of events. The producer already owns that alignment stamp; this
candidate changes the receiver, not the model.

Phase age keeps trading-session units and measured/lower-bound/unknown states.
A lower bound remains “At least … trading sessions.” The visible research stance
uses producer doctrine fields; the old engine stance remains inspectable as
provenance. Historical calibration is labelled historical. Live feature parity
is disclosed independently and is not promoted into current predictive validity.

## Navigation and accessibility limits

A same-selection return leaves the existing measured detail mounted, retaining
its recorded-versus-reconstructed history lens and focus origin. Router-owned
entry tokens, local-origin validation and a conservative history-length check
limit use of Back; otherwise the validated local return link is used. Foreign
history state is preserved. New entry focus takes precedence over old Cycles
focus memory. Scorecards receive keyboard activation; new controls use shared
tokens and touch/focus requirements.

Exact preservation of every advanced chart setting across several distinct
history entries, reload, or an external shared-shell receiver is **not claimed**.
The current native renderer retains one current chart state. Terminal #1244's
origin/receiver contract is separate and unchanged. Browser acceptance must
exercise return, rapid transitions, focus after final layout, and family-only
Back/Forward before this candidate advances.

US is the new host view. The shared renderer's URL-writer fix also protects the
existing China embedding, and standalone US/China/international renderers keep
their own datasets and benchmark identity. No Canadian listing is remapped to a
US ticker; supported Canadian and Company continuation contracts stay in the
original 13-route package. This is not a new browser-proof claim for those routes.

## Ownership and overlap

| Existing owner | Candidate treatment |
|---|---|
| Macro #10689, Agent OS continuity | No workstream/handoff duplication; no changes to its branch or two owned paths. |
| Macro #7595, shell asset/access guards | Its `inject`/`loadCycles`/error-handling hunks are not copied or changed. Read-only `git apply --check --recount` of its observed router patch succeeds against this candidate. File-level overlap remains and must be composed before integration. |
| Macro #10695, regional flow/return and theme builder | No owned-file changes. |
| Macro #8639, theme expired-projection geometry | No owned-file changes. |
| Macro #10625, temperature | No owned-file changes; prior publisher refusal untouched. |
| Terminal #1244 | No branch/workspace/generated registry changes or duplicate publication effects. |
| F01/F02 | No final shared acceptance, relabel or uncertain Paper retry. |

## Executed verification

See `source_validation.json` for the final exact file digests and command result.
The seven focused Python suites execute existing engine, source, fixture and
navigation contracts, including Node execution of the real public receiver and
host URL/history code. The frozen R3 fixture directory was materialized before
running its tests; missing sparse files were not treated as product failures.
Paired authored JS/CSS assets are byte-identical to their `site/` copies.

`prepare_preview.py` successfully renders the actual templates using archived
committed data and shared assets. It marks the local page as a non-live fixture;
it does not run an engine, append a forward log, or deploy. The browser runner
passes syntax checking, but **its UI scenarios have not run successfully**.

Browser attempts reached these explicit boundaries:

1. Playwright's normal Chromium installation returned a truncated download. No
   unchanged installation loop was requested after that tool attempt settled.
2. The existing Chromium binary could not create its required local socket
   (`Operation not permitted`). No browser flags were used to defeat the restriction.
3. The standard request for broader local execution permission was rejected by
   this environment's granular approval policy (`sandbox_approval: false`).
4. The approved Browser connection could not reach the fixture server
   (`ERR_SOCKET_NOT_CONNECTED`). The task-created tab and local server were closed.

No screenshot of the new implementation is claimed. Prior Paper images remain
design references, not evidence of this code rendering correctly.

## Browser matrix still owed

| Case | Required observation | Status |
|---|---|---|
| 1440 dark EN / light ZH | Chart, details, source dates, visual hierarchy and all controls | NOT RUN — browser boundary |
| 1024 / 768 | Responsive chart/detail reflow, no clipped controls | NOT RUN |
| 390 dark EN / light ZH | Touch, readable labels, detail sheet, return focus | NOT RUN |
| 320 ZH stress | No page overflow, no unreachable controls | NOT RUN |
| Keyboard / reduced motion | Visible focus, scorecards, Escape, return after layout | PARTIAL source checks; browser owed |
| Mismatched source dates | Withheld selection → explicit newer snapshot → intact origin | PASS executable host contract; browser owed |
| Unknown id / missing date / hidden chart / malformed series | Distinct unavailable/pending behavior | PASS executable receiver contract; browser owed |
| Slow/failed assets, permission, offline | Honest visible failure without bypass/retry | Browser owed; compose #7595 owner handling |
| Multiple entries / reload / source correction | No false promise of full historical/advanced-state restoration | OPEN contract work |
| China / supported Canada / Company round trip | No identity, currency, benchmark or return regression | Original package matrix remains owed |

## Reproduce on an admitted local browser host

From the repository root, with the repository Python dependencies and Playwright
available:

```bash
PYTHONPATH=. python docs/verification/d05_native_cycles_20261104/prepare_preview.py --out /tmp/d05-native-preview
python -m http.server 8765 --bind 127.0.0.1 --directory /tmp/d05-native-preview
```

In another terminal on that same admitted host:

```bash
D05_BASE_URL=http://127.0.0.1:8765 node docs/verification/d05_native_cycles_20261104/verify_browser.cjs
```

`D05_CHROMIUM_EXECUTABLE` may name an already admitted browser binary;
`D05_EVIDENCE_DIR` may name the output directory. The runner accepts only a local
fixture origin, blocks off-origin/non-GET requests, and writes dated screenshots
and a result JSON. A result file is not design acceptance: inspect the actual
screenshots for clipping, hierarchy, density, light/dark contrast and EN/ZH fit.
It must not be used to bypass any host's denied browser capability.

## Exact continuation / release hold

Keep the PR Draft, no Ready/un-draft, no merge queue/auto-merge, no hold-label
changes, no production deploy. The next useful action is to run and visually
inspect this exact candidate on an admitted browser host, repair real findings
on this branch, then complete publication identity and multi-entry return work
against the existing D05 contracts. Reconcile #7595 and Terminal receiver owners
before integration. Final shared design acceptance remains Chairman/Sol-held.
There is no running background worker or armed watcher from this session.

## Receiver fields for the next builder

| Field | Input / output | Meaning |
|---|---|---|
| `context.id` | Optional native entity id or null | Exact producer identity; unknown id → unsupported. No cross-market ticker inference. |
| `context.family` | Optional sectors / baskets / nasdaq / russell | Used when no entity is focused. A focused entity resolves its own family. |
| `context.asOf` | Optional valid ISO calendar date | Requested source session; invalid dates are unavailable, unequal dates are a mismatch. This is not a historical replay parameter. |
| `context.requireSourceDate` | Boolean | A selected Central handoff requires the originating date. The deliberate newer-snapshot action removes this alignment requirement. |
| `receipt.status` | Finite status string | Applied requires a known source date and visible mounted chart; it is not visual acceptance. |
| `receipt.asOf` | Valid Cycles date or null | Displayed source cutoff; never the browser's wall-clock date. |
| `receipt.family` | Applied native family | Renderer-owned resolution of the selected identity. |
| `receipt.series` | pending / ready / unavailable | Chunk/selected price availability; not proof of publication-digest equality. |
| `SectorCyclesHost.onFocus(id, family)` | Renderer → host callback | Host writes only its existing entry's cycle query fields. The renderer does not write the shell hash. |

The existing public `SectorCyclesFocus(id)` boolean remains compatibility-only:
true means a known native id was selected, not that source alignment, layout,
history restoration or user acceptance has been proven.
