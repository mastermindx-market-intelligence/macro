# P12.T32 — Canada basket retained-reading source parity

When optional theme scoring fails, the Canada basket producer keeps its price payload and still emits its detail pages. The shared detail builder previously labelled those regional reads with the US S&P 500 default and used the roster creation date as the observation date. Missing highs/lows and advancing/declining counts also appeared as measured 0/0.

The existing detail producer now falls back to the price payload's supplied benchmark labels and source date. If neither source supplies metadata, it keeps an unknown date and an unavailable benchmark. The reader uses its existing neutral unavailable representation for missing/nonfinite count observations; observed zero and nonzero counts remain unchanged. No price, return, scoring, benchmark calculation, roster, recommendation, rights, financial authority or data source is added or recomputed.

## Source and retained scope

- Source base: `8996951acf5a45b01dadd4d7814982fec4b063fb`.
- Selected original W9 renderer: `/basket_canada/<id>.html`, representative `ca_asset_mgrs`.
- Canonical owner path: `scripts/build_baskets_canada.py` → `scripts/build_theme_detail.py` → `templates/basket_detail.html.j2`.
- Retained published input: `site/canadabasketdata/baskets.json`; the bounded test fixture records the exact source commit/hash and preserves the eight actual member rows, prices/returns, roster/partial history and existing source metadata. No provider request.
- Original accepted disposition stays retained-static. This is a shared-renderer correctness repair, not a native conversion or a full-family runtime pass.
- Known open #8639 owns an independent SVG-geometry candidate. No registered local worktree for that branch or demonstrated active writer/lease was found in the bounded custody check. Its committed candidate remains untouched; this composition changes only metadata/count formatting and leaves graph geometry unchanged.
- Held #9536 redesign, its Paper operations and unqualified implementation return remain held and unreplayed. Its new design is not adopted here. Active Forex, Terminal Sector, SS05, T30 and Commodity paths are untouched.

## Original Paper/reference adjudication

Approved Sector R3, file `01M2WGNCX9475G79JRKJTCM08P`, page `p-24-0`, is the retained reference contract. The inspected dark desktop and light Chinese phone cycle boards make the observation close, benchmark/units and independent evidence clocks explicit. State matrix `6V9C-0` requires a dated last close and describes an abstained dossier as no data, never zero. Different-generation snapshots remain distinct.

The retained basket keeps its own authored thesis, source-linked member depth, cycle evidence, historical score/change records and membership log. This repair addresses those data-identity/degraded-reading obligations without importing the held redesign, new art direction or forecast authority. Existing dark/light materials, layout, focus and graph geometry do not change. No new screenshot is claimed; the controlled source-reading method below is not responsive/native-browser proof.

Reference exports, retained at their original identity:
- `SECTOR-R3-cycles-desktop.jpg` SHA256 `1a43ef612ea9326889248e8eb5fa55f01f6fe0148c9da8049515c56786e5ad2a`.
- `SECTOR-R3-cycles-mobile-zh.jpg` SHA256 `08bd71d508a1b45536d7d3744600a121b7497ee026564d8222cdfbff0cf465ab`.
- `SECTOR-R3-state-matrix.jpg` SHA256 `7309af04b1615d3cc3ad1489bb1f0213695fd4967a4d5b1d660e95a7693ba1df`.

## Controlled investor reading and causal proof

The actual incumbent producer and Jinja template emit the retained Canada representative. The emitted JavaScript then executes in the committed Node VM witness, with a minimal string DOM and all optional fetches returning unavailable locally. No browser, account or network is used. EN and ZH state renders are recorded separately. This is source/controlled-render proof; it does not establish CSS geometry, native focus, public iframe READY or signed-in product acceptance.

- Canonical entry/return remains Canada Theme Rotation Desk ↔ `basket_canada/ca_asset_mgrs.html`.
- All eight exact member links retain `../canada_stock.html#<source symbol>`; no US viewer substitution.
- The selected reader retains 49 score-history observations, 11 recorded changes, source roster/partial-history disclosures and the same return destination.
- Without optional theme intelligence, supplied source labels remain `S&P/TSX` / `标普/多伦多`, as-of `2026-11-02`; roster creation `2021-06-14` stays membership history only.
- Without either metadata source, benchmark is unavailable and date remains unknown; neither US defaults nor creation dates are invented.
- Missing/nonfinite/boolean count inputs render neutral unavailable values. Controlled measured 0/0 and 3/1 remain observations; no count is estimated from members.
- The full retained healthy rendered reading body is byte-identical before/after in both EN and ZH. Document JavaScript bytes intentionally change; old captures are not restamped.

Causal sequence: five metadata regression failures/two passes on unchanged producer → producer repair; one emitted-reader missing-count failure/nine passes on unchanged count formatter → renderer repair. The combined affected regional/cycle run passed **38 checks**. The regressions now live in `tests/test_theme_detail_cycles.py` and are explicitly invoked by the existing `basket-staleness-warn` **code** gate, with a fail-closed Node availability check. The initial regional-library placement was nightly/data-only and was corrected before publication. No new job or CI pack is introduced; the original regional suite is unchanged. The final code-gate focused run passed **19 checks** (`merge-gate-focused.log`).

`check_ui_visual_evidence.py` passes for the actual diff: no new CSS, inline style or runtime stylesheet system. Design enforce-added reports zero blocking additions. This is not a visual-taste or full-Paper acceptance claim.

## Guard applicability and remaining release gates

The initial expanded mount run yielded 97 PASS and three local failures. Two were caused by this sparse checkout omitting the tracked theme-research client (blob `6965055b2006058f402ad9dd8ae071e7eaf06d38`), not by source absence; that earlier diagnosis was corrected. Materializing only the exact tracked blob produced 106 PASS and one FAIL.

The remaining guard demanded this branch introduce an already-landed aggregator with exactly +1/-0. Under the bounded parent ruling, first introduction still requires exactly +1/-0. An inherited aggregator instead must remain unique, in the same relative position, with the entire back-link/include/app seam byte-identical to the actual integration base. No inherited case is skipped; the prior missing-history-only skip is unchanged. All tree, absent/malformed render, asset order and harmlessness guards remain enforced. Actual binding is code job `semiconductor-b-boundary`, plus data-only `unrun-subsector-themes`.

The unchanged guard first rejected a safe inherited edit (one causal RED/eight counterexample passes). The repaired guard accepts a clean inherited base and the authorised count repair, while rejecting removed, duplicated, moved or modified mounts, altered back link, added seam content and loss of `ignore missing`. Original introduction still rejects +2/-0 and +1/-1. Final affected qualification is **118 PASS, zero FAIL/skip** across the basket-detail, staleness and two mount suites (`guard-affected-final.log`). Existing source and historical proof identities are not restamped.

PR #10665 was created on `fd6ab1bf2f68dd9d51eb2eee6a562642864854e0` / refreshed base `cb0b039a41af0e3a18ae50f2c5040f531d136a9d`; it is now Draft and unarmed. Actual original CI run `41659037911` started from the direct `pull_request` workflow. The protected cb0 workflow has no shared-cap admission dependency/receipt, so authored-cap admission is unqualified. That already-started operation remains on its original carrier; no cancellation, retry, duplicate watcher or source push is used to clear capacity. The local source correction awaits the actual cutover predicate and bounded parent adjudication.

Required next delivery: independent bounded source adjudication, exact-head protected CI/landing, normal covering renderer and static served-source binding. Actual browser/Shell READY and broader family acceptance remain their original separate programme boundaries. No Person1 operation, refused Chromium launch, alternate browser/carrier, provider probe, account mutation, manual publisher or direct generated-site patch is authorised by this record.

Local exact evidence: `/Volumes/Mastermind/evidence/shared-shell-regional-basket-20261103/` (`causal-red.log`, `counts-red.log`, `affected-final.log`, `source-reading-proof.json`, baseline applicability and guard logs). The earlier proof-harness import diagnostic is retained; the corrected source qualification ran successfully. No Fabric recovery or unsupported-model refusal is inferred from the earlier terminal worker prose; MMOS #2009/comment6605720152 leaves those effects narrowly unqualified and authorises no retry.


## P12.T32.S1 current-base source preparation

The root-commissioned current receiver reuses the original externally admitted,
clean regional worktree on a distinct preparation branch. The original d194
branch/ref and remote PR10665/fd6 remain preserved. Base for this composition is
`b4df44260aefb42afbabd5f85e3b0630c8fec506`, available locally without fetching.

This is source preparation only. The reviewed producer, template, regional tests
and retained fixtures are composed through d194. The incoming #10656 inherited
include recognition and fail-closed Git-read diagnosis remain: an already-landed
mount is checked by the reviewed full back-link/include/app seam assertion rather
than skipped. Original first-introduction +1/-0 controls remain. Only the four
original coverage-step lines enter the existing basket-staleness-warn job; current
unrelated manifest content is preserved.

Current `tests/test_ci_pack.py` is unchanged from this base, including its existing
ceilings and newer curation comment. Historical d194 +3 ceilings are deliberately
not transplanted: current composed probe/job/weight/pack measurements are still
owed before any bounded baseline proposal. This stage ran no tests, CI, rendering,
browser/provider operation, fetch or publication. Earlier source checks are
retained historical evidence, not current-candidate acceptance.

The failed distinct storage-helper operation8840/partial checkout is preserved
without adoption or retry. The separate old hosted base-replay UNKNOWN is also
unchanged: this source composition neither settles nor replays it.
