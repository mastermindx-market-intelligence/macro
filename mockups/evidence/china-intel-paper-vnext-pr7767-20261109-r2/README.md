# China Intelligence Paper workspace: current source and browser proof

Operation: `pr7767-proof-01a1a7fb-m149`. Original PR: [#7767](https://github.com/mastermindx-market-intelligence/macro/pull/7767). [Canonical source/effect ledger](https://github.com/mastermindx-market-intelligence/macro/pull/7767#issuecomment-6732134769).

## Captured source

This is actual local rendering of the revised Paper workspace, not production deployment evidence. The operation-owned workspace is based on accepted receiver `071ed19f5ce87927f078f94f3e126c24d8a0307e`. The producer records the nearest checkout HEAD. The table below binds the modified source bytes actually rendered and tested; the manifest's own nearest-checkout caveat remains in force. The later selected integration receiver `448f681b2dcacd2639674b91afc6a812437e402f` differs only in the marketing-press-wire workflow timeout (10 to 30), outside these page, data, renderer and capture inputs.

| Source | Git blob | SHA256 |
|---|---|---|
| templates/china_intel.html.j2 | 7359b4f95df7497f75062529a9ef2ae6ce0208e9 | d80e4d26c7dbc8fa6307c24e753d8a49462cd759e25f4559ef126428e0c923d8 |
| .github/ci/legacy-jobs.yml | 206b9a19bd506ecd435e3fd3b0da061acd225ca9 | 4a83900fd4ae161a126bed78404d347db8072c4ff68d067c185f3758ffbe4582 |
| tests/test_china_intel_paper_vnext.py | ecef8929f2b79d2683f8a09cdf196351ef9c05d4 | eb58fcb933d0cc12492d1392f078d2c7ebcc399306cf7dc3cbbedc24b11c2e8d |

The original Paper information architecture is retained. Repairs supply bilingual headings/map labels, truthful dated context and missing-versus-zero coverage/evidence, and labeled signal semantics without colored left-edge rules. A real browser inspection found the translation helper leaking HTML from the map aria-label; the current source uses a plain bilingual accessible label and a rendering regression. Original R1 images are not accepted evidence and are not part of this bundle.

## Actual execution

- Initial integrated source: 77 focused cases passed, zero failures/errors/skips, November 9 04:36:33–04:37:00 UTC. Log261B, SHA256 `27f21f06e2b0ec498e7685f11a207cc4f880db9402d9d8540acb6a95fc2d8983`.
- After the accessible-label correction: all16 Paper module cases passed, zero failures/errors/skips, 05:02:19.638–05:02:24.446 UTC. Log180B, SHA256 `0ca35f406d327563aaef2677e1197246f341a9116136babd0c5e9ddbda6236c2`. These were separate runs, not a newly executed combined78-case suite.
- Unchanged canonical `scripts/build_china_intel.py`, blob `9dead274465ca99070235ec4c80d30662bca8a02`. The builder ran successfully at05:02:24.447–05:02:26.821 UTC using operation-owned local inputs. Its log816B/SHA256 `f6dcc600154f557dcd9c27a19ee0474932699efa1eaa6f979ca9ca317eb4b5f0`.

Actual rendered HTML212523B/SHA256 `d7e199fc7bfc17471bc7cc3246e3d13b6a261cd0cf5a3d35c094fb3836fcb13d`; briefing108046B/`5a34b819babfe5c88f4233d9819bc4a6cb796103052bef97be9a8b776968c8b7`; digest1568B/`5d849525e009ba34ee6eacda48d9c6683fadf6f042fb4bceeb83c476fa05738f`. The briefing has actual as-of2026-11-08 and9 source surfaces. Oldest-data age remains visible; this is dated context, not a live-market assertion. Generated site outputs are proof inputs and are not shipped in this template-focused change.

## Canonical rest-state evidence

The unchanged `scripts/capture_page_evidence.py` v1.4.0,114040B/SHA256 `9b6e643c1c784eb81b584be4cb063092ae71c4a16fe01498130891e84cd0de42`, used its actual registry, anonymous state, Python Playwright1.64.1 and owned Chrome156.0.8078.4. No private Paper bundle, fixture substitution, authentication, provider, collector, publisher or deployment was used.

The unmodified [manifest](manifest.json) is schema `mastermind.p0_evidence.v2`,14855B/SHA256 `b8fae29deb11763cb4d6c8828aa8548b8e28207f6e6bb35ff5342f58723edcfe`. Its twelve raw PNGs are included unchanged. It records all12 desktop1440×900/tablet820×1180/mobile390×844 × English/Chinese × light/dark cells, with actual applied theme and locale. Capture72797 exited0 at05:03:33.728 UTC; log215B/SHA256 `92f8169463a1a88159276314c9f9fca87737dddb06639d7246c9eb9500206783`.

There were zero console errors, zero failed responses, and no document horizontal overflow. The mobile measurement reports48 elements wider than its viewport, including retained legacy wide content; zero overwide elements is not claimed.

Root inspected all twelve genuine images, including every new workspace and the transition into retained deep evidence. Bilingual headings, dated context, coverage/evidence values, map labels, signal states and all three layouts are readable in both themes. The visible aria-label defect is gone. Temporary pixel crops aided inspection without changing the original PNGs; they are not substitute evidence files or page geometry.

[EVIDENCE.yml](EVIDENCE.yml) uses the existing exact three-key `mastermind.page_evidence_receipt.v1` schema to bind the changed template to this canonical manifest.

## Narrow actual mobile interaction check

The existing producer additionally captured [three mobile English/light cells](../china-intel-paper-vnext-pr7767-20261109-interaction/manifest.json): its normal baseline and two real browser interactions:

```text
--force-state 'catalysts_focus:focus(.ci-vnext-tab[href="#ci-upcoming-catalysts"])'
--force-state 'last_signal_hover:hover(.ci-vnext-signal:last-child)'
```

This is the existing producer's real locator focus/hover implementation, with actual activeElement/:hover readback; no CSS class or attribute was forced. The focused Catalysts link is fully reachable in the horizontally scrolling navigation. The final Sector Desk card is reachable in the signal rail. Both actual images were visually inspected. This focused check is scoped to mobile390×844/English/light and is additional to the complete twelve rest cells.

Interaction producer91886 exited0,05:22:32.631–05:22:52.310 UTC,19.679s. Manifest8239B/SHA256 `2fd3d66d23cadf3ae4f0dbed68ee66810a6b0bf4adfa31c0e42f82193810f806`; log231B/`38c6dab8bf7cee2254461064da07406beacb6adc5083ece00b4dbddc97f9e082`. All3 cells captured, both interactions applied, no console errors or failed responses. Current source and all three generated outputs remained byte-identical through both capture runs.

## Boundaries

This bundle supports the current source/UI change. It does not establish hosted CI, a merge, deployed assets, public-origin behavior, current market availability or investment/trading acceptance. The separate #7753 engine/command carrier remains untouched. Existing retained deep analytical data and source contracts are not replaced by the presentation.
