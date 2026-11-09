# Crypto R4: safe saved cases and clear asset comparisons

## Current phase — honest comparison basis and usable asset workflows

The interface now names the reported measures accurately: **Asset/BTC ratio change** and **Price change**. One native **Comparison basis** disclosure separates the calculation rule from missing paired-window metadata. Markets starts in the supplied asset order, comparison explicitly includes all snapshot assets, and null relative history keeps other usable asset readings visible.

Missing asset data, an empty projection, an absent requested asset and a search with no matches have distinct recovery. Reset keeps keyboard focus. Locale refresh preserves the basis disclosure and reading position. Narrow fine-pointer Close no longer exposes the Settings hover target beneath the mouse; touch drawers remain full-height.

**161 cases passed**: 39 contract + 122 browser cases (all previous 86 plus 36). The native run used 123 contexts / 129 pages with zero page errors or external/WebSocket traffic. Eight final focused/capture cases passed with unchanged runtime; six overlap the suite and two are visual readbacks. **Thirteen final native crops inspected.**

Published values, dates, view JSON, producer and model remain unchanged. The existing renderer reproduces the parent exactly before applying the presentation patch. The proposed per-result comparison receipt remains unimplemented.

- [Comparison architecture, state logic and remaining build plan](COMPARISON_BASIS.md)
- [Exact source and validation](COMPARISON_VALIDATION.json)
- [Complete native JUnit](comparison/CANDIDATE_RESULTS.xml) and [final focused JUnit](comparison/FINAL_FOCUSED_RESULTS.xml)
- [Parent baseline](comparison/BASELINE.txt), [corrected Reset proof](comparison/RESET_BASELINE.txt) and [corrected pointer proof](comparison/POINTER_BASELINE.txt)
- [Inspected native captures](comparison/captures)

Next: evaluate a compact two-asset matrix at 320/390px while preserving native scrolling for larger cohorts. Public-route, H5/model, alert, hosted/independent visual and release holds remain unchanged.

## Prior phase — original-condition-first saved cases

The complete saved condition is now visible immediately. Two native disclosures hold the original case details and captured evidence; Historical review is the clear primary action. Review qualifications are available on demand. Expiry remains distinct from original progress, and malformed optional evidence never creates invented readings or dates.

**86 browser cases passed**, retaining all previous 61 and adding 25 focused cases. Two current-scenario views retain exact parent DOM and geometry. Twelve native captures were inspected, including two additional light-theme captures. The 39 unchanged Python contract cases retain their prior passing evidence.

Paper now includes **state 17 / 3LJ-0** for unreadable saved evidence and **state 18 / 3MC-0** for unavailable original progress, alongside the accepted states 09–16. These extend the existing workflow without a new router, storage key, reading-state owner or data/model refresh.

- [Frozen-case builder contract](FROZEN_LAYOUT.md)
- [Exact source, native proof and limitations](FROZEN_LAYOUT_VALIDATION.json)
- [Parent baseline](layout/BASELINE.txt) and [candidate JUnit](layout/CANDIDATE_RESULTS.xml)
- [Current-scenario DOM/geometry comparison](layout/CURRENT_SCENARIO_PROJECTION.json)
- [Source transformations](layout/SOURCE_TRANSFORMS.json)
- [Inspected native captures](layout/captures)

The current comparison phase above completes that presentation audit. The proposed paired-window receipt remains separate from implemented UI.

## Prior phase — saved-case navigation verified

The original 30-day case now remains the same case through review, parent return, native Back/Forward and locale changes. Close restores the original outer horizon. The existing drawer/history owner retains per-entry disclosures, semantic focus and reading position; missing or unreadable saved context receives explicit recovery.

**39 contract + 61 browser cases have passing coverage across the initial 93-pass/7-failure run and the corrected 10-pass affected run.** Seven initial failures were classified and retained as test-harness mistakes; runtime assets did not change between the runs. Three new native navigation crops were inspected. The frozen-case hierarchy is implemented in the current phase above.

- [Navigation architecture, behavior and next work](NAVIGATION.md)
- [Exact source, test results and qualifications](NAVIGATION_VALIDATION.json)
- [Parent baseline output](navigation/BASELINE.txt)
- [Initial candidate output](navigation/INITIAL_CANDIDATE.txt) and [JUnit](navigation/INITIAL_CANDIDATE_RESULTS.xml)
- [Harness diagnostic](navigation/DISAPPEARANCE_DIAGNOSTIC.txt) and [corrected affected JUnit](navigation/HARNESS_CORRECTION_RESULTS.xml)
- [Exact navigation transformations](navigation/SOURCE_TRANSFORMS.json)

## Prior completed phase — storage safety

This dependent candidate repairs the local saved-snapshot workflow in the existing R4 drawer and storage owner. It is based on [Macro PR #9580](https://github.com/mastermindx-market-intelligence/Macro/pull/9580), exact parent `5e496c24c962e85a4f7f514dd43dc61443b95cab`.

A stale Remove button previously could save a record again. Removal also used a filtered, capped collection, losing unrelated entries; failed reads appeared empty, and unconfirmed writes could announce success. This change gives the displayed action a stable intent, preserves the full readable collection, validates requested saved versions and confirms the write before reporting its outcome.

## Implemented

- Explicit Save and Remove in the existing `save` function; already-present Save and already-absent Remove make no write.
- Exact-revision removal across the complete array, including duplicates outside the display window.
- Separate readable collection, usable display records, missing requested version and unreadable collection states.
- Original saved horizon/cutoff/fields required for a requested version; a missing legacy evidence digest remains supported.
- One attempted write, followed by exact serialized readback. Unconfirmed completion retains the action and does not retry or navigate.
- Confirmation respects a newer route, language, focused control or focus-triggered navigation.
- English and Chinese recovery copy, with a neutral collection-read message that remains true after a confirmed removal.

## Verification

**40 real-browser cases and all 39 existing Python contract cases are covered by passing results.** The initial candidate run returned **76 passed / 3 failed**: the three failures were missing imports in the isolated source subset. After restoring 20 exact-parent dependency files, only those three unchanged tests were rerun: **3 passed / 36 deselected**. This is not a claim of a single 79-pass run.

The browser run used Chrome `157.0.8103.39`, **41 fresh contexts / 47 pages**, with **zero page errors**. Its first case also retains the existing 32 view/theme/locale/width permutations. New cases cover actual second-tab changes, malformed/inaccessible storage, duplicate preservation, write/readback uncertainty, newer focus and reentrant focus callbacks. Eight final native dialog crops were inspected.

The saved candidate pages change only the two asset-version references each: `be2ec2a278c4` → `3786626cb4d5`. Template and served JS are byte-identical. Reversing the ten explicit JS transformations recovers the exact parent. The data, CSS, HTML template, builder, model projection and shared assets remain byte-identical.

## Build contract and evidence

- [Implementation and remaining work](SNAPSHOT_SAFETY.md)
- [Exact verification and limitations](SNAPSHOT_VALIDATION.json)
- [Original baseline output](BASELINE.txt)
- [Harness correction receipts](BASELINE_HARNESS_CORRECTIONS.txt)
- [Initial candidate results](CANDIDATE_RESULTS.xml) and [completed dependency checks](DEPENDENCY_RECOVERY_RESULTS.xml)
- [Source transformations](SOURCE_TRANSFORMS.json)

Paper file `01M6Y3F0NXNDPAKJMJGCAD759Z`, Build `3IP-0`, remains the full saved-case design contract. Storage, navigation and frozen-case hierarchy are implemented and locally verified; see the current build contract above.

This stays a dependent Draft candidate. H5/model authority, alert integration, hosted and independent visual acceptance, public-route cutover and release gates remain with their existing owners. No production replacement or current-market freshness is claimed.
