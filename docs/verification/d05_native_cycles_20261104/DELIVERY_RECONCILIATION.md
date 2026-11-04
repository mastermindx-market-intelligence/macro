# D05 delivery reconciliation — 4 November 2026

This increment is source-tested and preserves the existing Draft/HOLD boundary.
It does not establish complete D05, Company-return, production or final design
acceptance. The original 13-route programme and 119 planned cases remain in the
D05 design package; those cases are not all executed by this increment.

## Source and custody

The code is composed on Macro #10703 at
`77b6e5d4771242320198b002878d8c842f9833b9`. Its pure entry export and
input-cancelled viewport restoration are preserved. The six changed paths are
disjoint from that commit and from the current bridge/Company work. Publication
uses the existing branch and a checked expected head; no parallel implementation
PR or release action is created.

Protected law was read at
`690e5316629815ae3e78f65ebdec2eb87f0cad16`, compatible INDEX 1.0.1.

The existing Studio verification operation
`d05-native-source-verification-20261104` was advanced from its observed clean
9906 head to a97b, then to 77b6e5d4. The six owned file blobs survived the latter
fast-forward unchanged. This supersedes historical observations describing that
verification workspace as clean at 9906. The GitHub publication was reconstructed
from the exact base and strict diff, and every resulting blob matched the actual
tested Studio file.

## What changed

- **Theme evidence:** absent or unusable native falsifier summaries no longer
  become an evaluated clean negative. The native engine remains the sole
  evaluator. Missing count fields, booleans/strings/nulls and negative counts
  are rejected as malformed without crashing the page. An invalid summary
  cannot mark a row fired. Typed known negatives and valid fired/input-missing
  states retain their meanings. The returned worker patch needed these
  additional checks before integration.
- **Reduced motion:** the owned Cycles range presets, Home and historical-leg
  zoom respect the existing reduced-motion preference. Shared MMChart behavior
  outside these owned calls is unchanged and is not certified by this patch.
- **Browser proof:** reduced-motion runs assert immediate range application.
  Both motion modes wait for the requested observable range before capturing
  history state. The normal-motion mode is selectable with
  `D05_REDUCED_MOTION=no-preference`. This replaces the diagnostic arbitrary
  delay; exact state equality on Back/reload remains.
- **Preview fidelity:** runtime assets come from the candidate, archived market
  fixture inputs remain dated, and CSS font/icon dependencies are copied
  recursively. Provenance records the source and digest of each copied asset.

## Executed validation

**253 passed, 5 skipped, 0 failed** in 74.14s across the five affected suites
listed in [the exact validation record](delivery_reconciliation.json). These
include the newer pure-export/viewport tests. Counts overlap prior results and
must not be added to the earlier 485 or 105.

The five skips are the missing generated State-of-Themes page, absent basket
membership, two missing local sector-data tests, and an absent historical
scorecard. Explicitly materialized exact committed inputs repaired sparse
checkout failures; no assertion was relaxed. Paired Cycles assets, Node syntax
and diff whitespace checks pass. The coherent preview builds with six Inter
font weights and navigation icons.

## Retained browser evidence and its limits

The original browser return remains bound to source 2e6c4589. Actual result files
show 7/7 passes for each of archive, same-date mismatch, mixed series and missing
extras. Coherent failed twice on a captured range just before a 360ms tween
finished; a diagnostic settled copy passed 7/7. That diagnostic is not counted
as an unchanged-runner pass.

The canonical capture contains 48 images across Central/Cycles and
desktop/mobile, EN/ZH, light/dark and interaction states. All eight standalone
focus variants record a failed focus application. The preview omitted fonts
and navigation icons. A successful capture/guard is therefore not complete
visual acceptance. Direct inspection covered the retained Central desktop and
mobile captures, plus the actual Paper A02 and A09 boards; fresh captures on
the complete current source remain owed.

The prior visual helper refusal remains in force. No denied helper was retried.
No new browser worker or Fabric acceptance is implied by this source record.
Original terminal return identities and their limitations are preserved in
the JSON record.

## Next exact proof

On a lawfully admitted browser host, build all five scenarios from the exact
published combined source. Run the unchanged committed runner for all five in
reduced-motion mode and coherent once in normal-motion mode. Re-capture the
canonical Central/Cycles matrix with real copied fonts/icons and per-page
focus selectors that actually apply. Inspect the resulting images, preserve
the existing evidence schema and bind every receipt to its source/artifacts.

The current Company/bridge writer retains its exact files and original
Terminal #1244 operation. Companion #10707 retains Dossier qualification and
its unresolved host boundary. Neither integration is claimed here. Existing
merge, Ready, queue, relabel, deployment and shared-acceptance holds remain.
