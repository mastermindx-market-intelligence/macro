# Captured Sector document-completion calculations

Date: 2026-11-06. Base: `1f3f605367f48021455e1dbec462bdbbf879c58a`.
Carrier: Macro #10780; mission #10779. These are shared calculation seams; runtime activation remains open.

## Rotation context

`engine.sector_generation_guard.rotation_context_from_inputs` owns the original
rotation-context projection over a consumer session, captured events/fragmentation and
explicit evaluation day. The legacy cycles builder keeps file and clock acquisition
and delegates the resulting values. Missing, invalid, incompatible and projection-error
statuses and `rotation_alignment_version` are preserved. Aligned nested values are
detached; no file or wall-clock lookup occurs in the explicit projection.

## Self-grader

`engine.sector_central_grader.grade_from_inputs` receives captured calls, Yahoo prices,
frozen basket levels/membership and first-freeze metadata. It reuses the unchanged
next-bar grading and score-version segmentation. `frozen_basket_levels_from_inputs`
projects the existing chain-qualified return series from a captured frozen DataFrame.
Missing anchors, a later unanchored tail and membership changes retain their existing
exclusions; current recomputed basket prices are never a grading substitute.

The legacy `grade()` adapter retains its three independent frozen reads and original
exception boundaries. Runtime composition must derive levels, membership checks and
first-freeze metadata from one accepted frozen snapshot. `append_central_log`, keep-FIRST
semantics and nightly advancement stay outside this calculation. A pre-append captured
log correctly grades recorded calls but does not reproduce newly accruing counts from
an append-then-grade nightly run; that writer transition is separately required.

## Central publication facts

`engine.sector_central.complete_document_from_inputs` shares original crowding disclosure,
publication metadata and legacy research-row attachment. It takes an aware build clock,
actual secondary-source facts and actual legacy premium-write outcome. The builder
calls it after its existing write attempt; default output remains identical. The row
digest remains a row digest and is never reused as the generation content identity.

Native private composition supplies `research_mode="unbound_native"`, the explicit
sector-generation transport, `flows_html.status="not_applicable"` and a false legacy
premium-write fact. Conflicting claims are refused. Old research bindings are removed
and the unbound receiver is disclosed; no private native member is mislabeled as an
updated static artifact. The existing authorized projector owns native audiences and
does not currently forward raw handoffs. Native research journey integration remains
open and cannot be inferred from this metadata seam.

## Qualification and next step

Rotation plus existing guard tests: **64 passed**. Grader/publication and their direct
neighbors: **253 passed**, with 232 expected warnings from flat synthetic correlations.
Literal baseline fixtures, all-v2 grading, missing/unreadable/empty logs, independent
frozen-read failures, input detachment, fixed clocks and same-session row corrections
are covered. Exact source and log hashes are in
[the source proof](SECTOR_DOCUMENT_COMPLETION_SOURCE_REVIEW_2026-11-06.json).

Next: invoke these seams from the existing data-only Sector document composer, using
the actual basket/theme/allocation/cycle/timing owners. Serialize final baskets once,
bind the action board to those exact bytes, and submit precisely the existing five
members to the current generation factory. Capture, staging, selection, authorization,
ledger advancement and scheduling retain their existing owners.
