# Sector Central R4.1 — Dossier Cycle implementation and integration proof

**Parent mission incomplete. Component built; production mounting and release not accepted.**

Programme: macro#7646 / `sector-central-redesign-20260921-sol-001` / `WS:SECTOR-INTELLIGENCE-COMPLETION`.
Protected procedure: Mastermind `93c8c3c01f9226d1ea267e21c548f047458654dc` (compatible Skillpack1.0.1).
Owned workspace operation: `sector-r41-dossier-cycle-impl-20261104-sol-001`, base `4a2291747fd2d8d364a3838e1ed2263636bc64a6`.

## What changed

Before: the R4 design lacked a dedicated Dossier Cycle journey and 768px transition; this session's missing component had no executable source/data-bound proof.

After: four editable R4.1 boards exist in the original Paper file. An opt-in Dossier Cycle view reads the existing producer stamps, separates legacy history from ontology facts, refuses unsupported/denied/mismatched evidence, and delegates actions to the original host. It is implemented and exercised in real Chromium, but is **not yet mounted into a production route**. Existing cycle engines, research/watch stores, auth, Company routing and the native Cycles implementation are not replaced.

### Source

- `templates/sector_dossier_cycle.js`: dependency-free `buildView` and explicit `mount` with update/destroy. No automatic boot, fetch, storage, history, authorization decision, signal computation or new router.
- `templates/sector_dossier_cycle.css`: confined presentation using existing theme and frozen design-system tokens. Dark instrument surfaces and light research surfaces; complete focus outline, 44/48px controls, responsive layout and reduced motion.
- `tests/test_sector_dossier_cycle_js.py`: real Node behavior tests. Access-pending/denied never evaluate the sensitive payload. Exact subject/family, dates, null/zero, provenance, lower-bound age and model qualification are tested.
- Existing `sector-cycles-page` CI job gains this suite and its three source dependencies; no independent CI plane or new release job.

### Important source correction

The first adapter version trusted `phase_v2` even when the producer said `phase_v2_source=legacy_fallback`. A real RED test reproduced that mislabelling. The fix keeps the original provenance visible and withholds the ontology phase/age unless the ontology classifier actually produced it. A separately valid ontology position remains distinct. The component never promotes historical MODEL/PRIOR evidence into a current probability.

### Responsive chart-label repair

Actual phone visual QA found the inherited MMChart date ticks overlapping. A new real-browser assertion reproduced the collision at 390px before the fix. The component now measures rendered date labels and suppresses only colliding labels within its own chart surface, with observer cleanup on update/destroy. Native observations, zoom, crosshair, and source dates are unchanged. Browser checks verify spacing after both initial rendering and native zoom redraw. No shared MMChart or active D05 source path was edited.

## Native Paper receipt

Exact file: `01M6FAXA774QT1VRDMAG7DFQ2W`; page `p-2-0` (R4 · M1).

| Board | Exact node | Purpose |
|---|---|---|
| Desktop dark English | BP8-0 | Energy Cycle/Dossier, source-qualified evidence and constituent continuation |
| Tablet light English | BUY-0 | 768px Members transition, exact listing and Company-return contract |
| Phone dark English | BXQ-0 | 390px Cycle reading and reachable deeper evidence |
| Phone light Chinese | C0K-0 | 390px translated composition with the existing locale semantics |

The R4 page was read back with 28 boards, retaining the 24 predecessors. The separate D05 page `p-3-0` and its 12 candidates were not overwritten. Actual native screenshots of all four R4.1 boards were inspected after the semantic-family copy correction: no visible clipping, clear subject/answer/evidence hierarchy, neutral borders without accent rails, and readable phone/tablet composition. This is representative visual QA, not a full Cartesian state/access acceptance.

`paper/evidence-inspector.jsx` is the native `get_jsx` return for BSM-0 (inside BP8-0), inline-styles, no node IDs. It is a static reference, not executable production data. New copy remains proposed NEW_COPY; no frozen copy deck is silently changed.

The same native carrier returned `APPLIED_RESPONSE_OBSERVED` for `finish_working_on_nodes` on precisely BP8-0/BUY-0/BXQ-0/C0K-0, operation `sector-r41-four-boards-release-indicators-20261104-sol-001`. The original unrelated Refined-vase operation `paper-v21-current-app-board-20261103-sector-001` remains EFFECT_UNKNOWN/no-replay.

## Executed verification

Read the retained logs/result files at this commit, not an earlier chat count.

- Focused source suite: `tests/test_sector_dossier_cycle_js.py`, `tests/test_sector_cycles.py`, `tests/test_cycle_rhythm_disclosure.py`. The baseline before implementation was 97 passed / 3 skipped. Current result is retained in `validation.json`.
- `verify_component.py`: 16 actual Chromium combinations (1440/768/390/320 × dark/light × English/Chinese). It uses the real existing MMChart renderer. Tests exercise keyboard actions, duplicate-listener avoidance, chart cleanup, literal hostile source text, denial cleanup, loading/unavailable/stale states, snapshot mismatch, overflow and measured contrast. Synthetic fixtures are labelled and never used as a production fallback.
- `capture_governed.py`: calls the existing `scripts/capture_page_evidence.py` owner with its supported driver seam and Chromium sandbox enabled. The isolated test page gets 24 real captures: 8 rest cells plus hover/focus across both themes/languages and desktop/mobile. Canonical `mastermind.p0_evidence.v2` manifest and three-key EVIDENCE receipt live under `mockups/evidence/sector-r41-dossier-component/`.
- The canonical evidence checker initially refused the sparse checkout because it could not see predecessor mockups. The existing `worktree_sparse.py add mockups` owner materializes only that evidence subtree; no full data/site checkout or guard bypass.
- The first design ratchet rejected literal radii and a locally constructed shadow. They were replaced with the existing frozen radius scale and `--card-shadow`; no shared-token edits.

This remains component proof. It does not prove a signed-in production account, all thirteen D05 routes, Company exact return in production, saves, natural refresh, revision identity, a release, or user acceptance.

## Historical integration finding — repaired upstream, original ownership retained

Draft #10703 owns native Cycles in Central. The initial audit below inspected `9906c882d56e5bed829b2d11aa7b837c5b7abc7f`. Its current inspected successor `a97b8f50cdf3a16ad8cba3a52edf76fc9ef30f14` has repaired the duplicate controls and owns publication/part verification and entry restoration. The component is now exercised against that exact producer/verifier. Do not repeat the historical repair, overwrite the incumbent, create another router or replay #9917.

A finite original local browser run reached the real Cycles chart through the mismatch/latest-snapshot gate and exercised price/linear/zoom controls. It then failed because the rendered page contains duplicate `sc-tabs`, `sc-tab-n-sec`, `sc-tab-n-bsk` IDs. These occur in the Market map controls (template around2165) and native Cycle controls (around2249). Inline `__siWireScope` (~3067) and `sector_cycles.js::wireFamily` (~862) both bind `#sc-tabs .sc-tab`; the collision can cross-change two different universe selections. See `evidence/native-qualification/` for the failed result and capture. **No end-to-end native pass is claimed.**

The original supplied verifier also clicks the mobile-only advanced disclosure on desktop. `verify_native_cycles.py` corrects that testing assumption by checking visibility and then asserting the real controls are reachable; it does not force hidden controls or replace production code. That source repair is now present in upstream a97; the failed capture remains historical evidence only. Current full-route browser acceptance belongs to the original upstream owner.

### Newly recovered effect fence

The incumbent's original Slack thread `C0CBC6AEAQZ/1793768002.626429` reports unresolved Fabric browser request `d05-native-browser-proof-20261104-01` (`INVALID_ARGUMENT root_id`, execution absence not proven, retry disallowed). This was discovered **after** the finite local validation above. That browser and local server exited. No further overlapping native browser job, alternative worker or write to the incumbent branch is dispatched while that uncertainty persists. This does not block the disjoint component/fixtures/self-QA in this workspace.

A new advisory finding was delivered to the same thread at `1793769498.948619`, mentioning Grok Secretary. Delivery is not pickup or completion. The prior separate safety-denied Fabric audit and denied#7646 note from this session are not retried or rerouted.

Also preserve the original Fable worktree/branch `claude/sic-cycles-wave-20261102` at90fe7973 with dirty `scripts/build_site.py`, `templates/sector.html.j2` and untracked `templates/sector_dossier.js`. Historical ownership alone is not a live writer, but this known dirty work is not overwritten or silently superseded.

## Integration contract and next action

The host supplies already-settled access/data state, exact subject/family, locale and source date. `mount` returns update/destroy so the owning Dossier lifecycle can replace or remove it. The host remains responsible for request-generation fencing, entitled source loading, Company identity, navigation/return and chart lifecycle. Date equality alone does not establish revision identity or PIT truth.

Consume the qualified successor component through its exact source revision and reconcile the existing standalone Dossier lifecycle before mounting. The upstream duplicate-ID repair is already present. Integrate Cycle/Dossier/constituent/Company/back through the existing router and D07/F01 return contract; consume the original native browser result rather than duplicating its run. Component proof is not whole-route or production acceptance.

All merge, Ready, un-draft, enqueue, held-label and deployment holds remain. Final F01/F02 shared design acceptance, real auth/save journeys, source correction/publication semantics and natural data refresh remain separate release gates. No worker/watch/service is left running by these scripts.

## Qualified successor — publication-bound integration (2026-11-04)

The interrupted local qualification was recovered in the original workspace, not rebuilt. Governing93c8c3 procedure blobs were compared with current Mastermind690e531 and are unchanged. The published baseline672bae had concluded CI and fences SUCCESS; those receipts do not cover the successor until its own checks run.

`mountFromNative(root, owner, options)` now consumes the existing `SectorCyclesEvidence()` receipt from an **already-loaded** source owner. It never loads the singleton renderer, calls SectorCyclesApply, hashes, fetches, authorizes or routes. Receipt schema `sector_cycles.evidence.v1`, status `verified`, verified core part, US region, expected `cycp1-` publication identity and any supplied exact sector spine must agree before the payload is read. Same-date publication changes are not treated as the same snapshot.

- Sector oscillator history is core-owned; it survives an optional heavy-series failure. Basket/Nasdaq/Russell oscillator history requires the verified series part. This component does not expose price-mode history; a later price mode must require the series receipt. Missing NARR/DNA never deletes valid facts/history.
- Exact values are original valid observations in bounded50-row pages. Null, nonnumeric, out-of-range, repeated or reversed coordinates withhold the whole history rather than silently filtering it; valid core facts remain. Invalid, unverified and missing history have different explanations in EN/ZH.
- Evidence details expose source date, publication identity, classifier, basis, membership meaning, reconstructed-history meaning and source-part verification. They do not claim historical constituents or observed point-in-time evidence.
- Same-subject/publication refresh retains Exact values/Sources expansion, value page, keyboard focus and the native chart viewport. A changed/denied/superseded subject focuses its new heading only when focus was inside the component; an unrelated task keeps focus. Host page scroll/history remains host-owned.
- Callbacks carry stable `actionKey` (`members`, `cycles`, `sources`), exact subject/family/as-of/locale, actual DOM `invoker`, and verified `publicationId`. Click-time revalidation rejects a superseded or malformed core receipt. Updates/destroy remove old chart resources/listeners and stale actions cannot fire.

`verify_native_receiver.py` uses original producer `_cycles_payload.py` and original receiver `sector_cycles.js` at a97, not copied digest logic or a mock source acceptance. Four end-to-end component scenarios cover verified source, mixed sector-series, mixed basket-series, and corrupted core; the verified case also covers supersession, denial, callback identity, focus/viewport/disclosure retention and malformed receipt transport. This is **component receiver proof**, not a replacement native route/browser worker.

Three further RED-before-GREEN regressions were observed during recovery: missing verified-core part permitted payload access; source supersession lost focus to body; an action could dispatch after the core receipt became invalid. The final source closes these, plus a real-browser regression distinguishing invalid attached history from missing history. See retained resume logs and current validation.

### Original browser worker: material status change

Same native Fabric status on `d05-native-browser-proof-20261104-01`, conserved root/parent `6aea7863-bef8-83e9-bb5b-47850ca7132b`, now reports TERMINAL, rc0, result available9101bytes, root_verified=true and controller return RECORDED. Acceptance remains NOT_ACCEPTED/NO_OUTCOME; this surface reports result_consumption_authorized=false. The original parent was notified on its existing Secretary thread at1793777492.419259 to consume its retained result through the admitted path. No outcome is invented, no worker is retried, and the older second-run/Paper effects are not cleared by this observation.

### Existing Dossier host seam

Read-only inspection of the preserved dirty Fable host found `SC_DOSSIER.bind`, standalone `#scd`, Cycle mount `#scd-cycle`, original `SC_STATES.fetchTyped('../sectordata/sector_cycles.json')` and local language repaint. That host has no accepted publication-aware lifecycle hook yet. Its dirty template/builder/module are not overwritten. The original D05 root and Secretary have the exact hook and companion contract; the remaining work is source-owner composition, not another frontend router.
