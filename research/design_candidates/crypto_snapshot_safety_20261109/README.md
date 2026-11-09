# Crypto R4 saved-snapshot safety

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

Paper file `01M6Y3F0NXNDPAKJMJGCAD759Z`, Build `3IP-0`, remains the full saved-case design contract. Storage safety is implemented here; parent return, route-horizon continuity, disclosure/locale/scroll restoration and the original-condition-first layout continue as distinct work.

This stays a dependent Draft candidate. H5/model authority, alert integration, hosted and independent visual acceptance, public-route cutover and release gates remain with their existing owners. No production replacement or current-market freshness is claimed.
