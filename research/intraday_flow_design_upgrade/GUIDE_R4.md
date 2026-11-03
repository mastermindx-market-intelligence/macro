# R4 · Field guide aligned with recorded evidence

Status: implemented and locally verified candidate; PR10498 remains **Draft/HOLD**.
This is the next bounded continuation after the actual R3 canonical visual proof,
published at `703f3c9c230730cf9f0f5dbb99c7bd416b85859b`.

## Problem and resulting behavior

The scan calls its classifications recorded, and R3 explains that received data is
not current confirmation. The old field guide still described a setup as live,
called unknown quality a clean leader, implied that Stand aside meant a quiet market,
and described options flow as call-heavy or put-heavy. Its dealer explanation gave
present-tense stop-placement instructions despite an unavailable chain source time.

The existing guide now explains the same recorded assessment as the scan. Its six
labels remain byte-identical, including markers; descriptions explain their rules
without promising a live setup or a reversal. Call-only estimates are distinguished
from combined calls+puts premium. Unknown observations remain unknown. Daily/nightly
dealer context, the unavailable chain clock and reference-level limits are explicit.

The guide still uses the original native details and four subsection controls.
The closed state has the same height. All seven checks, options activity, dealer map,
nightly stop/buy zone, VWAP, session low, source details and advanced evidence remain.
No product CSS or JavaScript was changed.

## Frozen design and source scope

The R4 contract is appended to [DESIGN_SPEC.md](DESIGN_SPEC.md).
Paper file `01M2WGNCX9475G79JRKJTCM08P`, page `p-26-1` now includes two additional
guide-only specimens:

| Variant | Node | Canvas sizing | Extract |
|---|---|---|---|
| Desktop / light / EN | `71UJ-0` | 1440 px, height fits content | [JSX](paper_r4_guide_light_en.jsx) |
| Mobile / dark / ZH | `720J-0` | 390 px, height fits content | [JSX](paper_r4_guide_dark_zh.jsx) |

Both were visually inspected in full and their working indicators released on those
exact IDs. The specimen titles are design annotations, not new product UI.
They are principal design inspection, not qualified independent acceptance.
The denied dark-ZH ticker-row effect at 6ZIW-1/6ZHV-1 was not repeated or reconstructed.

Only the `ift-guide` region changes in the template and generated page. The page
was rendered from the existing committed board through `lib.pages.write_page`
and `scripts.optimize_assets.make_optimizer`; optimizer idempotence passed.

| File | R4 SHA-256 |
|---|---|
| `templates/intraday_flow.html.j2` | `9dd9a11896db3c75b8ca48c782dc5976d85170ff1a2809f64b323923e5003f69` |
| `site/intraday_flow.html` | `aa82b215294514edd929bce48512d56fc44b6aaa1604e8079032c2314de70fc9` |

Against 703f3c9c, all template/page text outside the guide is identical. All4template
script elements and all 10 generated script elements are identical, covering the
protected model functions, existing pollers and R3 source disclosure. Both CSS
files retain SHA-256 `fec0337920fe79b84a316cf08584321289813cd79f1a7e7f2f21b4ac8e4d0039`.
The main-integrated board retains SHA-256
`76f8f28816e347866a59b90e3d8c2ee1654786e9dbec13eddcdc750e0bf3fe18`.

## Actual browser evidence

[verify_guide.py](verify_guide.py) completed **105/105 checks** and **8/8 screenshots**:
9 source-identity checks plus 12 behavior/layout checks in each of 1440/390 × light/dark
× EN/ZH. It exercises the real local page with the existing local feed files; no
synthetic market data or feed writes are used.

- Enter and Space open/close the native guide and each of its four subsections.
- Every language shows its own six labels and hides the other language.
- The expanded guide has no page or guide horizontal overflow.
- Closing restores the original guide height and retains focus.
- Combined theme/query filters, selected name and expanded full evidence survive.
- No page exceptions or failed responses were observed.
- All 8 screenshots were inspected in full; the focus outline is visible and the
  complete English/Chinese text wraps at 390 px. Desktop text remains at its existing
  readable line length; the floating assistant does not cover the guide text in
  these captured states.

The [verification receipt](../../mockups/refs/intraday-flow-upgrade/guide-r4/verification.json)
contains every check, screenshot SHA-256 and exact candidate source hashes.
The targeted capture was made before the R4 material commit on worktree head 703f3c9c;
this is explicit in the receipt. Final canonical page proof is recorded separately
against the committed material source.

| Width | Light EN | Dark EN | Light ZH | Dark ZH |
|---|---|---|---|---|
| 1440 | [PNG](../../mockups/refs/intraday-flow-upgrade/guide-r4/guide-1440-light-en.png) | [PNG](../../mockups/refs/intraday-flow-upgrade/guide-r4/guide-1440-dark-en.png) | [PNG](../../mockups/refs/intraday-flow-upgrade/guide-r4/guide-1440-light-zh.png) | [PNG](../../mockups/refs/intraday-flow-upgrade/guide-r4/guide-1440-dark-zh.png) |
| 390 | [PNG](../../mockups/refs/intraday-flow-upgrade/guide-r4/guide-390-light-en.png) | [PNG](../../mockups/refs/intraday-flow-upgrade/guide-r4/guide-390-dark-en.png) | [PNG](../../mockups/refs/intraday-flow-upgrade/guide-r4/guide-390-light-zh.png) | [PNG](../../mockups/refs/intraday-flow-upgrade/guide-r4/guide-390-dark-zh.png) |

## Preserved evidence and limits

The R3 record retains 329 scoped pytest, 515 baseline browser, 244 recovery and 201 source-detail
checks. Those suites were not rerun for this editorial slice; exact script/CSS/data
identity and targeted actual interaction proof establish the scope of retained evidence.
The R3 canonical matrix remains immutable in `source-r3-canonical/`.

This does not grant independent source/visual approval, current live-session proof,
field-performance acceptance or a release decision. No denied reviewer, startup
diagnosis, GLM helper or Paper row operation was retried or moved to another carrier.
No new runtime, watcher, queue, authentication or shared-navigation work was created.
The original branch, workspace and root operation retain custody. No Ready, un-draft,
label, enqueue, merge or deployment action is authorized or performed.

## Final canonical binding

R4 material commit: `d3665db28f34737ddbe7b712a3e48a0e41f1f93b`. The incumbent canonical driver then captured
**24/24 states** at 2026-11-03T08:19:07Z on the clean material source. All image
digests and source bytes match. Console errors, failed responses and page-wide
horizontal overflow are zero. All eight resting page layouts were inspected;
their widths and document heights match their R3 counterparts exactly.

Current matrix: [guide-r4-canonical/manifest.json](../../mockups/refs/intraday-flow-upgrade/guide-r4-canonical/manifest.json).
Verification: [guide-r4-canonical/verification.json](../../mockups/refs/intraday-flow-upgrade/guide-r4-canonical/verification.json).
Resting lab CLS: desktop 0.67893–0.69153, phone 0.00994–0.02440; existing shared-navigation
startup stability remains unresolved. No refused startup diagnosis was repeated.
The generic source/as-of detector mismatch is retained and explained in the receipt.
The containing evidence commit changes no product blobs from the material commit.
