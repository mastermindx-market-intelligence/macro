# D03 T49 — CI import-integrity repair and real-template browser recapture

Source branch: macro Draft PR #10617, original head `2dfda0a3b2e23e74bb551baf302001a9fb22f909`. The exact-head hosted `ci` run `41912325742` failed **only** pack 3 / `nyse-calendar-freshness` → `tests/test_first_party_import_names.py::test_every_first_party_import_resolves` (1 failed, 202 passed). Both offending evidence scripts imported `tests.test_prophet_setup_sections._body_html`; that test module lives on Prophet implementation PR #9495, **not** in the design documentation PR. The other 11 CI packs, `fences` and `ci-authority` were green.

## Exact change

- `d03_t49_plan_recovery_20261104/check_t49_plan_recovery_tablet.py` and `d03_t49_two_candidate_compare_20261104/check_t49_two_candidate_compare.py` now use only the already-present `tests.test_dashboard_template_render` and `tests.test_prophet_plan_relation` helpers. Each locally generates the same explicitly synthetic LFUS detail through the **real** `_prophet_setup_detail.html.j2` Jinja macro.
- No dynamic import masquerading as acceptance, no assertion deletion, no copied competitor/source asset, no change to the gated design or authenticated production route. The scripts still bind exact SHA256 of five original UI-owner files in `--workspace`, and refuse a source-tree mismatch.
- Both scripts compiled cleanly. On the #10617 checkout, the exact CI blocker `pytest -q tests/test_first_party_import_names.py::test_every_first_party_import_resolves` completed **1 passed** in 46.25s.

## Real browser verification

The repaired scripts were executed against an **independent clean** Prophet implementation checkout at `43ac1d47cdc73b716301da3edbe9dc69da8bd120`, with all external requests blocked.

- `plan-recovery-6cell/qa.json`: 1440 light EN / 1440 dark ZH / 1024 light EN / 768 dark ZH / 390 light EN / 320 dark ZH — **6/6 passed**. Missing linked Plan stays in-place, retry is keyboard accessible, then a valid Plan hop and return preserve original Sources section, focus and scroll with no false zero state.
- `two-candidate-2cell/qa.json`: 1024 light EN and 768 dark ZH — **2/2 passed**. LFUS and ZEUS selected from separate source rows, comparison retains both objects, clear/back restore state, and Plan return still works.
- All eight browser cases have saved PNGs and SHA256 digests in their respective QA JSON. They remain synthetic anonymous owner-path proofs; no signed-in account Save/list or deployment acceptance is claimed.
- Previously committed T49 evidence is preserved. These outputs document the narrow import repair and real-template recapture, not a reclassification of earlier Paper EFFECT_UNKNOWN or new Paper artboard acceptance.

## Next fence

Publish this documentation/evidence-only patch on the **same** Draft #10617 branch, recheck its exact-head hosted CI and verify no new import-name failures. Keep Draft/HOLD; no Ready, un-draft, enqueue, label, merge, deploy or purchase.
