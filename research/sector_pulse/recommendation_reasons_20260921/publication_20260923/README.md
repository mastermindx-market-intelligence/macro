# #7669: close the compiled-page integration gap

## Actual result

The latest exact-head run 35807840374 on b2e61137bcb52157be5bb9c1df5c1dd92cfc1294
failed the existing `test_basket_score_native_state_survives_render_and_reinjection`:
new template helpers were absent from committed detail HTML. This was a real
source-to-artifact defect, not an inherited CI false red. The unchanged test was
reproduced locally before repair.

Main d34993def9fa00e88c930f39a498b6ecad97455b was integrated once on the same branch
at 9c81d664d1337b5214e249151ab0c343b4047dab. The composition was conflict-free.
The native theme/stock recommendation implementations and the detail template are
unchanged from the previous feature head; no policy or threshold was revised.

121 actual generated pages were refreshed through the existing Jinja template,
stock-entry owner, native CSS/JS externalization, asset optimizer and page writer.
No new asset was necessary. The compiled output now contains the real stock-check
workflow, not merely a scratch-template demonstration.

The 121 pages comprise US49 / China22 / HK17 / Canada16 / international17, covering
1,917 member rows (not unique stocks). Every original non-explanation payload
field, status, buy record, coverage result, observation date and displayed original
generation time is preserved. US/Canada observations remain Sep21; China/HK/
international remain Sep22. The earlier Sep18 proof did not overwrite these inputs.

## Evidence

- Both Python3.14 and Python3.12 affected suites: 302 passed each (overlapping).
- The originally failing generated-page helper assertion passes unchanged.
- Native capture owner `scripts/capture_page_evidence.py`: 40/40 cells captured
  over five real compiled regional pages, desktop/mobile x EN/ZH x dark/light.
- Ten supplemental compiled-file interaction states verify keyboard opening,
  full member reasons, native stock-link destinations, 40px controls and preserved
  open/focus state after `render()`. No JavaScript page exception or page-wide
  horizontal overflow in those interactions.
- The canonical capture retains expected 404 console entries for deliberately
  unavailable live endpoints, authenticated-state gaps and its heuristic layout
  findings. This is NOT a clean-console claim or a complete page-design approval.
- All capture PNG hashes match the canonical manifest. `native-refresh-receipt.json`
  binds the original and emitted bytes for every page.

All browsers operated on local generated artifacts with optional live/API data
unavailable. None of this is a deployed, authenticated or current-market receipt.

## Material input defect discovered, not concealed

The Sep21 semiconductor detail had 11/12 non-null stock assessments at accepted
full-engine commit e77ddcedfe9f49aea0ad3ac1ef10e3ac337dd911. At focused publication
f8bc00fe15323ced6ff56ef5768124c94cd7f384, it had 0/12. A later public render retained
that loss. The current page truthfully shows twelve unavailable assessments.

The focused Sector Intelligence path calls `build_baskets.main(sector_intelligence_only=True)`;
that function still builds stock-detail pages even though this lane does not build
or hydrate their gitignored stock dossiers. This is a separate publisher-ownership
defect. Do not paper it over by grafting old individual scores into a newer frame,
accessing an unauthenticated alternate private-data alias, or calling the coverage
gap a bearish verdict. Preserve the complete dated inputs until the proper producer
can publish a complete successor. This new invalidator has its own bounded source
repair, not a replay of already-merged #7211.

#7749's mixed technical-date return is another separate defect. Its unpublished,
platform-held candidate was not imported or republished. No unchanged-policy proof
is mislabeled as corrected-date score proof.

## Source-operation boundary

A proposed new helper/CLI modification to scripts/build_theme_detail.py was refused
by the platform before a process receipt. Same-carrier readback proved that file
still matched HEAD (blob2592a094577cd9014a3006ffe89f9d84b294160c). That source
modification was not retried. The untracked prototype tests for that unimplemented
API were preserved in session scratch; no committed test was removed or weakened.
The independently allowed generated-page refresh used the already-existing
renderer/writer/finalizer interfaces and created no new publication plane.

## Release

#7650, #7520 and #7693 are now MERGED; do not repeat their release repairs.
#7669 stays DRAFT/HOLD-FOR-SOL, without automatic merge. Concluded new-head CI,
independent semantic review and real production acceptance remain necessary.
Protected procedure pin: Mastermind@c18ea2ca779f042702a63a78bf1f10f5a1e0c0f6.
MISSION_COMPLETE: false.
