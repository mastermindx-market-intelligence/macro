# Standalone Cycles: truthful chart accessibility — 2026-11-05

**SELF_REVIEWED.** This integrates the exact prepared one-file local commit `eb807572d1c1d0645801e3bc060e1507dd374111` into the original Macro #10703 source carrier. Integration parent: `d1ebd39fb1287f69592d8a621c5db0318e7fff05`. The template blob is `e37c035f2f6fd8f7711b45f5221277723c428739`; no engine, renderer, data, access or navigation code is changed by this slice.

The chart's accessible name now follows its existing bilingual heading. Its description distinguishes rebased prices from the 0–100 oscillator and explicitly states that scorecards are summaries, not a point-by-point data table.

## Executed evidence

- Prior exact local source qualification: `tests/test_sector_cycles.py tests/test_cycles_entry_state.py tests/test_sector_paper_copy_deck.py`: **103 passed / 3 existing skips**, as recorded in [the original verified source receipt](https://github.com/mastermindx-market-intelligence/macro/issues/7646#issuecomment-6655690702). Those unchanged tests were not repeated merely to claim new work.
- New actual-renderer Chromium proof: **8/8 cases**, desktop 1440×1000 and phone 390×844, each dark/light × EN/ZH.
- Every case used real keyboard activation for Cycle → Price/Linear → Cycle; actual accessibility-tree role, localized name and localized description were asserted at all three stages.
- Price changed the actual SVG path geometry. Returning to Cycle restored its exact previous geometry.
- **0 uncaught page errors, 0 missing fixture assets, 0 document overflow**; 16 captured PNGs. Themes and languages were asserted from the actual DOM.
- Screenshot self-QA inspected the complete contact sheet and full-size phone Price view. This hidden semantic change retains existing chart composition.

[Raw browser result](result.json) · [executed driver](verify_accessibility.py) · [fixture provenance](fixture_provenance.json) · [contact sheet](contact-sheet.jpg).

## Source and proof limits

The existing `prepare_preview.py --scenario coherent` rendered the actual template and runtime sources from the retained local commit. It reconstructed a clearly labelled synthetic coherent publication from the retained dated archive using the existing producer/verifier. This is local fixture browser proof; it is not current market data, an authenticated account/tier test, production deployment or full D05 acceptance. The prior accepted integrated US journey is preserved and was not re-run.

The original source-verification workspace remains dirty and preserved. The separate prepared branch was not pushed. #10707's refused compact layout, Terminal #1244's refused publisher, original Paper uncertainties and every release hold remain unchanged.

## Newly observed next repair

The screenshots expose an independent visible defect: the temporary first-use hint still says “High = stretched · low = washed-out” in Price mode. The existing mode caption and legend already switch correctly; the one-shot hint does not. This receipt does **not** accept that hint as correct. The next bounded source repair must qualify the first-use hint against the current Price/Cycle mode, preserve its existing dismissal/timer owner, and verify initial Price URLs plus keyboard mode transitions in both languages. A point-by-point chart table is also not claimed by this accessibility description.

MISSION_COMPLETE=false. Draft/HOLD; no merge, Ready/un-draft, enqueue, hold weakening or deployment.
