# D05 China Central — canonical visual evidence

**16 of 16 states captured; the unchanged visual-evidence validator returns zero findings for the incremental material UI repair.** Capture began at **2026-11-05T08:53:05Z**. The selected detail panel is visible on desktop; the opaque detail sheet and sticky navigation are visible on mobile. Review classification: **SELF_REVIEWED**.

This receipt registers the existing repair to `templates/macro-desk.css` and `templates/sector_central_china.html.j2`. It uses the existing three-key `mastermind.page_evidence_receipt.v1` receipt and the unmodified canonical `mastermind.p0_evidence.v2` emitter. No runtime source, test, gate, evidence schema or release hold changes in this evidence commit.

## Source binding and method

The runtime repairs were published at [1f050a23](https://github.com/mastermindx-market-intelligence/macro/commit/1f050a234311a8c2a90d325b048159ebf2fe2386) and [fb4ee257](https://github.com/mastermindx-market-intelligence/macro/commit/fb4ee25752ae2900038ec6cf8e2b17c2e90148d9). Current parent [ceff73c1](https://github.com/mastermindx-market-intelligence/macro/commit/ceff73c10fa34563e64a54aa3bd38fc4d3823869) adds only copy-deck citation corrections; comparison confirmed unchanged runtime bytes. The published citation deck passed all **13 unchanged tests**, recorded in [copy_deck_tests.txt](copy_deck_tests.txt). The separately prepared citation candidate was not published over that concurrent repair.

Capture uses the original running Next host at `http://localhost:3100/sector_central_china.html#801010` and its existing shared-shell iframe on port 8765. No additional server or gateway was started. A bounded Chromium driver intercepts the already qualified 46-file archived China fixture, then closes each context and the browser. Only localhost origins are allowed; other network requests are aborted.

The staged HTML is rendered from the qualified templates with an explicit archived-fixture marker. It is not represented as byte-identical deployed HTML. Source inputs, emitted fixture hashes, current renderer hash and archived data identity are preserved in the existing [history fixture provenance](../../../docs/verification/d05_native_cycles_20261104/china_history_20261105/fixture_provenance.json), [history source manifest](../../../docs/verification/d05_native_cycles_20261104/china_history_20261105/source_manifest.json) and [regional source manifest](../../../docs/verification/d05_native_cycles_20261104/china_archive_20261105/source_manifest.json).

The selected source is Shenwan sector **801010**, native **China**, benchmark **SHCOMP**, as of **2026-11-03**: 31 sectors and 22 baskets. The underlying archive is [2e6c4589](https://github.com/mastermindx-market-intelligence/macro/commit/2e6c45899a9aeb7f90f03f85272aaff3ca42f4eb), with cycle payload SHA-256 `e5fd4fa4fbe8329e4707e6d6e75168976dfc8b325c84c6b1f2499f61d1329da7`. Core and series evidence are verified; narrative/DNA remain unavailable. Capture time is distinct from source date.

The capture tool is the exact existing `scripts/capture_page_evidence.py`, version **1.4.0**, Git blob `78ba651d2996a64231c738a133ed465d73dd8caf`, SHA-256 `9b6e643c1c784eb81b584be4cb063092ae71c4a16fe01498130891e84cd0de42`. Its documented `main(argv, driver_factory=...)` seam receives the real Playwright adapter. The canonical utility writes every manifest row, image hash, dimension and smell report; none were constructed manually.

The exact executed adapter is archived as [capture_driver.py](capture_driver.py), SHA-256 `e36e19ef8fec6cf880176c21ae81b6debd54b04ff9cbca57fef10f83c0d4e634`. For replay it belongs at `scripts/d05_china_capture_driver.py` under the qualified verification stage with the pinned capture module and original fixture paths; it is not a standalone live-site runner. It reuses the canonical DOM observer and timing collector inside the child frame. Those measurements describe the child document; screenshots include the actual host and iframe. Parent and child observations are not merged into synthetic metrics.

## Captured matrix

| State | Requested viewport | Selected detail | Actual rail hover |
| --- | --- | --- | --- |
| desktop · EN · dark | 1440 × 900 | [Rest](346043e0c8c568bd.png) | [Hover](2fbd46f2da4e6359--rail_hover.png) |
| desktop · EN · light | 1440 × 900 | [Rest](bd5e7bb112679e18.png) | [Hover](61eff2c4aa6ae32c--rail_hover.png) |
| desktop · ZH · dark | 1440 × 900 | [Rest](d28ed7ef691a52b5.png) | [Hover](f00232a806262c80--rail_hover.png) |
| desktop · ZH · light | 1440 × 900 | [Rest](e72cc8a3309e0c12.png) | [Hover](8a17a43cd62a3aa1--rail_hover.png) |
| mobile · EN · dark | 390 × 844 | [Rest](b9df0815b9dce0b2.png) | [Hover](974fb1d0fcd0957d--rail_hover.png) |
| mobile · EN · light | 390 × 844 | [Rest](a3e4658c1f801be3.png) | [Hover](60d3a994340c98bb--rail_hover.png) |
| mobile · ZH · dark | 390 × 844 | [Rest](c440646bbec8cb31.png) | [Hover](cb2b4dd4b16b2ca8--rail_hover.png) |
| mobile · ZH · light | 390 × 844 | [Rest](ed5d4b4c0f429f9c.png) | [Hover](da815d9d8652b6f1--rail_hover.png) |

Each cell checks the actual host and child theme/locale, exact selected identity, visible Map and verified core publication. The real pointer hovers the inactive Overview rail button while preserving Map and selection; the canonical helper confirms `:hover`. All eight required rest cells and all eight declared hover cells are captured. Hover is required by the exact patch's selector-dependency analysis; focus is not required by that predicate.

## Verification and self-QA

- [manifest.json](manifest.json): canonical state identity, tool provenance, image byte lengths and SHA-256 values.
- [driver_observations.json](driver_observations.json): real rendered state, source receipt, network failures and frame/host observations.
- [validation.json](validation.json): zero findings, 16/16 captures, zero uncaught JavaScript page errors and zero outer document overflow.
- [repair_ui.diff](repair_ui.diff): exact incremental material declarations inspected by the unchanged guard.
- [smells.json](smells.json) and [smells.md](smells.md): canonical heuristic report, retained without editing.

The author inspected every final rest/hover PNG. Desktop detail text, source-unavailable disclosure and rail hover remain readable in EN/ZH and dark/light. Mobile navigation and sheets retain opaque surfaces, selected identity and an exposed localized close control. The earlier actual keyboard-close, route-return and Price/Linear Back/reload proofs remain in their separate browser receipts. This visual matrix does not replace those interaction proofs.

The first capture pass framed the chart on desktop. Self-QA identified that the detail panel was below the frame, so the final pass scrolls the real desktop detail into view. The first pass remains an unregistered local intermediate; only this final 16-cell matrix is committed.

## Explicit limits

This is archived fixture evidence with a disclosed synthetic identity and local E2E cookie, not a live authenticated account/tier test. The canonical manifest retains the free/essential/pro and loading/empty/stale/error gaps. No durable save, live refresh, producer correction, full regional Dossier/Members journey or production deployment is claimed.

Four optional fixture resources return 404: `chinastatedata/participation.json`, `chinabasketdata/narrative_emergence.json`, `chinasectordata/desk.json` and `basketdata/pulse.json`. Their resource console errors are retained; zero uncaught page errors does not mean an error-free network. No absent narrative, DNA or overview data was invented.

The stock heuristic reports as-of/source probes false and counts wide descendants. These are review prompts: actual source identity is recorded in the observed publication receipt and archive marker, while wide chart/table descendants coexist with **no document overflow**. The report is not rewritten to appear clean. Timing is synthetic local lab timing, not real-user performance.

The local guard result is scoped to the incremental 82c377 → fb4ee material repair, unchanged at ceff73. The full PR's hosted CI and other historical receipts remain separate gates. Original **Draft/HOLD** restrictions persist. This evidence does not establish full D05, F01/F02, editable Paper or release acceptance.
