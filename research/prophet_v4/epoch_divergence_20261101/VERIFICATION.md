# Candidate verification

This file reports observed candidate checks. It is not a production/deployment
attestation and does not authorize merge or auto-merge.

## Local regressions

The final selected runs passed **545 tests**, with **2 skips** and **5 explicitly
deselected shipped-artifact tests**. The checkout is an owned sparse Macro
workspace; the normal workspace helper materialized `site/` for existing tests
that read its committed JavaScript. `data/`, `mockups/` and `verify_shots/`
remain omitted. This is not a claim that the full repository suite ran.

| Command (from repository root) | Result |
| --- | --- |
| `python3 -m pytest tests/test_prophet_source_epochs.py tests/test_prophet_source_epochs_reader.py tests/test_p_mp1_shell_ladder_error_state.py tests/test_prophet_plan_relation.py -q --tb=short -p no:cacheprovider` | 196 passed, 2 skipped |
| `python3 -m pytest tests/test_us_board_gate.py -q --tb=short -p no:cacheprovider -k "not test_shipped"` | 94 passed, 5 deselected |
| `python3 -m pytest tests/test_us_today_source_binding.py -q -x --tb=short -p no:cacheprovider` | 131 passed |
| `python3 -m pytest tests/test_us_board_hydration_merge.py tests/test_dashboard_template_render.py -q --tb=short -p no:cacheprovider -k "not test_shipped"` | 124 passed |

The new source-epoch suites cover 84 synthetic cases with no skip: the helper's
raw-byte/metadata/snapshot failures, the actual express refresh body, single index
read/path advancement, immutable index/snapshot bytes, and the production
hydration entry point refusing mismatched/missing/forged-status evidence before
paid-row or panel mutation.

The initial broad run exposed a missing sparse site asset and outdated unit
fixture inputs, and exceeded its 240-second wrapper limit before reporting a
complete result. It is not counted as passing. The final split runs above resolved
those specific failures without weakening the production admission fence:
the shared predicate fixture holds the new independent variable fixed, and three
existing loader scenes generate genuine source-epoch projections from their
synthetic source bytes and displayed plan books.

## Immutable committed source

`committed_tree_reader.json` records the new projector's result over exact Git
objects at main `9fe98ab14db8ccc1bb35d9dd8b1d11617527dfdf`:
`SEPARATE_EPOCHS`, `PENDING`, verified frozen snapshot. Its index, board and
snapshot hashes/byte lengths are retained; no raw source rows are published.

## Browser proof

A preliminary browser run passed 8 responsive/theme/language cells and 5 refusal
cases against the real rendered dashboard and existing paid payload route.
Chromium version: `151.0.7922.34`. No page JavaScript errors were observed.
Unrelated live-data/config requests were unavailable in the isolated synthetic
fixture; their paths are retained in the browser receipt rather than presented
as production health.

The first browser attempt tried to focus the disclosure while the Plans panel
was hidden. The harness was corrected to enter through the actual Plans selector.
The observed final journey must include source selection, keyboard/pointer
disclosure, paid-row loading/refusal, and return to Screener. The retained final
receipt will bind the source commit and exact file hashes.

Final command:

```sh
python tests/tools/prove_prophet_source_epochs_browser.py \
  --output research/prophet_v4/epoch_divergence_20261101/browser
```

Expected matrix: 1440px and 390px × dark/light × EN/ZH. Failure cases:
different board hash, different index hash, missing source metadata, forged
SETTLED, and 403 access denial. The proof preserves the existing floating assistant
and centers the disclosure by scrolling; it does not hide product controls.
The metadata rows must be unoccluded, the disclosure must not overflow, and the
native summary target must be at least 40px tall.

## No-false-SETTLED attestation

The projection emits `settlement_status: PENDING` on every outcome. Equal hashes
establish only the defined source relation, not A2 four-family publication/read
agreement. Mismatched or unavailable page/payload identities are refused before
paid row/panel mutation. The browser also refuses an injected SETTLED field.
No accepted bundle ID, producer timestamp, second publisher or deployment is
created by this change.

## Completion gates

Independent final non-author Fabric review and GitHub PR CI are still pending at
the implementation checkpoint. The pre-implementation audit and helper acceptance
are recorded separately in `FABRIC_ADJUDICATION.md`; neither substitutes for the
final review. The PR remains Draft/unarmed under the Chairman's no-merge boundary.
