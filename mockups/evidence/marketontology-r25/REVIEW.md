# R25 selected-reading response and recovery — implementation checkpoint

Status: PARTIAL / BUILT_NOT_PROVEN. This source is not release-ready or deployed.
Scope: existing ontology host, shared Brain, and the existing synchronous/SSE response owner.
Base: Macro 910e6f1ea41940fd21a0cabbe6626c7c2156b304; prior route merge fc4a9d277d269096f7e637b796fd5583be2c42f0 is not replayed.
Current branch: sol/web-marketontology-r25-recovery-20261003 in the existing isolated source workspace.

## Implemented behavior

The source emits a positive, closed `ontology_selection_receipt.v1` only from the same permission-checked owner snapshot used for selected grounding. It binds the exact five-field request reference and localized source labels. Both public preflight and the in-loop race refusal emit a minimal unverified receipt with no source labels or values. Provider unavailability and ambient client claims do not produce a matched receipt. Existing tuple contracts, quota, permission, chat history and thread ownership are unchanged.

The real shared widget compares a returned positive reference with the reference sent by that turn. It does not infer success from absent errors or parse refusal prose. A selection-only preview stays distinct from a server-confirmed reading. Unverified results suppress new numerical citation/suggestion chips, provide a 44px return control, and invoke the existing exact-focus close callback without an automatic resend. A recovery control from an earlier selection cannot close a different selection. The prior answer and existing thread survive a subsequent refusal. Display labels use literal DOM text and remain outside the five-field request reference.

## Verification to this checkpoint

- The new gateway regressions failed for missing positive receipts and missing race-refusal metadata before implementation; the targeted 14-case suite then passed.
- Real-widget tests failed for the absent response card and preview before implementation.
- Current gateway/browser/shared-asset suite: **527 passed, 9 warnings**, PID 95313, exit 0. This is not hosted CI or production proof.
- Additional prior-thread and literal-label browser probes passed; the remaining ontology contract/identity/shell/transport group passed **192 tests, 5 warnings**, PID 8678, exit 0.
- Existing driver source `scripts/capture_page_evidence.py` captured **48/48** declared states: matched/unverified, English/Chinese, dark/light, desktop/mobile, rest/real hover/real focus. A one-cell smoke capture used a separate output directory. Capture PID 99149 is no longer running; its exact manifest was read back after its output stream detached. No duplicate capture was launched to reconcile it.
- First visual inspection identified unresolved rounded-corner token aliases: Paper radius names do not currently exist in production theme.css. Fix the scoped fallback and verify the final visuals before accepting the design extraction.

## Release holds and effects

The shared Brain change requires the normal `site/theme.js` producer to emit its new lazy-loader hash. That producer was executed; the corresponding asset test now passes. The real P0b closure guard still reports that both existing HK/Canada browser receipts pin the changed theme and have not been reminted. It remains an effective release gate.

A compound scoped HTML-restamp / P0b fixture-remint operation was explicitly blocked before dispatch. It has not been rephrased, replayed, delegated, or moved to another tool. That affected production-build/proof operation remains held; no hash-only receipt edit, test exemption or second deployment path is permitted. The independent R25 browser capture does not replace P0b proof. A separate smoke-manifest filtering diagnostic was also refused and not replayed.

Earlier, invoking `scripts.optimize_assets --help` unexpectedly executed the optimizer because that script has no argument parser. The four known local effects were inspected: only eight-character asset query hashes changed in ontology.html and three existing product pages that directly load the shared Brain. No data, model, service or publication operation was involved. The resulting concurrent-write test guard correctly failed; it was not disabled. Later verification ran after all product writes ceased. A subsequent attempted import of a nonexistent optimizer helper failed before its intended restamp; no effect is attributed to that failed import.

## Next bounded work

Finish the radius/status-color review and regression, capture final source-aligned R25 states, and publish the same source branch without claiming release. Consume the exact held build/proof gate only after an actual lawful recovery condition; do not probe or route around the refusal. Required P0b remint, full hosted checks, normal release decision, backend runtime and new served R25 acceptance remain open. Real browser 200% zoom and complete screen-reader acceptance are not established by these captures.

Authoritative design: Paper file 01M3P1X4FR6BRTB13KA736Y1HT, R25 board 4SA-0; R22 controls the existing four F04 objects and owners. No new graph, chat, persistence, permission, retry or lifecycle is introduced. Procedure: protected Mastermind bdf2a972e68a70270c24d4b5d61a4d60edc4f288, INDEX 1.0.1/bootstrap 1. Current Chairman continuation authorizes this bounded follow-through; it does not waive release or platform controls.
