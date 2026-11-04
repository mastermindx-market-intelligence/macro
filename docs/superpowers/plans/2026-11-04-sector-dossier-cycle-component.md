# Sector Dossier Cycle component — implementation plan

**Goal:** Start the missing Dossier Cycle implementation with a tested, source-bound presentation component that cannot fetch paid data, calculate signals, or invent a second router/state store.

**Architecture:** A dependency-free view adapter reads the existing `SECTOR_CYCLES` record and meta contracts. The host supplies its already-settled access/data state and selected subject; the component fails closed before reading payloads when access is not allowed. Existing chart, navigation, company identity, source loader and persistence owners remain responsible for their effects. This first component is not auto-mounted in a production route.

**Tech stack:** Existing vanilla JavaScript, semantic DOM, existing theme CSS variables, Node assertions invoked by pytest, browser qualification with Playwright.

**Spec:** Existing `design_refs/sector-paper-20261021/cycles_ia.md`, D05 source contracts at 22f6a887, and native Paper R4.1 Dossier boards BP8-0 / BUY-0 / BXQ-0 / C0K-0 in file 01M6FAXA774QT1VRDMAG7DFQ2W. R4.1 new text remains proposed NEW_COPY; no frozen copy deck is overwritten.

## Global constraints

- No merge, Ready, un-draft, enqueue, held-label change or forced publication.
- No modified engine scores, phase classification, model probabilities, sizing, auth, source fetch, saved state or Company identity owner.
- No new route/store. An explicit mount accepts an existing host-provided record; loading this asset alone does nothing.
- Null is not zero; malformed date/number/identity cannot become a success state. Same family and same snapshot are required.
- Only existing producer fields: meta.asOf, meta.region, record.id/kind/ticker/name/name_zh, now phase_v2/pos_v2/phase_v2_age_bars/above200d/rs_63d, series_provenance, estimate_kinds. Never combine legacy position with a v2 label.
- No current model probability under parity failure; up/3m and up/6m are not promoted beyond PRIOR. The summary does not print hazard probabilities.
- Existing CSS variables only; neutral borders, full focus outline, 44px controls, light/dark EN/ZH and reduced motion.

## Review focus

1. Denied access cannot evaluate or retain the sensitive payload, even via a property getter.
2. Zero, null, numeric strings, Infinity and invalid dates have distinct handling.
3. Duplicate IDs, wrong-family IDs and mismatched dates must not select an arbitrary record.
4. Source text and identifiers never execute markup or produce an unsafe URL.
5. Rendering a new subject or denied state must remove old values and chart callbacks; no duplicate listeners.

## Task 1 — pure view and source contract

Create `templates/sector_dossier_cycle.js` and `tests/test_sector_dossier_cycle_js.py`.
API: `SectorDossierCycle.buildView(payload, options)` returns a plain view with typed state, selected identity, independent dates, strictly finite facts and producer-qualified provenance. Options: accessState, dataState, family, id, locale, expectedAsOf. Unknown options fail closed. Neither function owns access authorization.

Write and run RED tests for absent implementation and each boundary above. Implement only enough for GREEN. Assert that input objects are not mutated. Render through textContent/createElement rather than untrusted HTML.

## Task 2 — deliberate presentation

Add `templates/sector_dossier_cycle.css` using existing tokens and R4.1 hierarchy. API `mount(root, payload, options)` replaces only the supplied root, returns {update, destroy}, and delegates existing chart/depth/member effects through host callbacks. No automatic network, storage, history, routes or global event effects.

Use real browser tests on supplied canonical/negative fixtures at 1440/768/390/320 and EN/ZH, both themes, keyboard focus, denied/loading/unavailable/correction states. This is candidate component proof, not an entitled production journey.

## Task 3 — integration boundary

Enroll the Node-backed pytest in the existing sector-cycles-page CI owner with exact paths. Keep #9917, shared renderer, shell router, regional and adjacent writer paths untouched in this initial component slice. Run focused source tests, JS syntax, scoped design-system checks and diff checks. Commit through the original managed workspace publisher if allowed; do not merge or deploy.

Production mounting, canonical Company originNav handoff and full P22/P23 acceptance are later explicit integration work, not claimed by this component.

## Recovery and integration ruling — 2026-11-04

Current Chairman instruction resumes implementation in this same owned workspace; all four prior files are intact at base 4a2291747fd2d8d364a3838e1ed2263636bc64a6. Prior unit result: 29 passed after a real missing-module RED. Previous engine baseline: 97 passed / 3 skipped. Original native Paper effects were individually observed and four new boards read back (R4 page now 28 boards); no replay is needed.

New material source: D05 Draft #10703 at 9906c882d56e5bed829b2d11aa7b837c5b7abc7f already implements the native Cycles route. Its writer owns `templates/si_workspace.js`, `templates/sector_central.html.j2` and the shared cycle renderer. Do not implement another router or overwrite that candidate. An older original Fable local candidate 90fe7973 also exists with unfinished `sector_dossier.js` and sector detail edits; those remain untouched.

Current phase: finish this disjoint presentation component, run real browser checks on the exact D05 candidate using the independently authorized Studio host, repair only owned-source findings, and retain an explicit integration result. Browser permission is determined by the actual Studio launch; no sandbox override, account/host switch after denial or escalation. A historical other-host refusal does not prove this host's capabilities. The previous Fabric audit request and GitHub note were explicitly refused and are not retried or substituted.

Direct-work rationale: CRITICAL_PATH_SHORTCUT and UNIQUE_APPROVED_ACCESS for same-workspace recovery, native design-to-code integration and actual browser proof. No worker is claimed running. The original root remains sector-central-redesign-20260921-sol-001. Execution and evidence continue in this owned source tree; no protected/held PR release action.

Open falsifiers before acceptance: ontology source marked legacy_fallback must not be relabelled as ontology; 0/null and per-family dates remain distinct; negative access must purge old rendering; JS must have no HTML injection; 320–1440 layouts must remain readable; chart interactions and exact return must work against original D05 renderer, not a mock.
