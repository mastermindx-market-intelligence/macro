# Prophet: main integration and native publication proof

## Outcome

The redesign and pinned-source render guard are integrated locally with main `b48b5dc562cf1e2600699fc24a445709e18ef8fe`. All 25 reported conflicts are resolved through the existing publication owners. The native four-step pipeline completed successfully, and all 1,915 frozen publication inputs remained byte-identical.

The source input commit is `ee5d7f68229ad14e9d384af61bafc3701df70f65`, with parents `676b5ecc915295165553b931c9b753598b33c756` and pinned main. The frozen-render implementation is commit `676b5ecc`; its focused test batch passed 265 tests. The generated public page and protected payload are adopted together in the commit containing this packet. The earlier published touch-target/shell evidence remains at `538d47bfcb1e658cdd3f138566701a07b505ec1e`.

This packet proves source integration, generated publication integrity, and anonymous offline browser behavior. It does not record a merge into main, deployment, authenticated product acceptance, or acceptance of the held Fabric/Paper operations.

## Conflict decisions and preserved history

The raw Prophet Plan publications are immutable. Main first published the disputed November 4 cohort at `c3a578d866f962bc595a0c23fea6950f9fe66fa0` (14:45:16 UTC). The branch subsequently originated the same 12 IDs from a different capture at `f10a9e0fc7a515f658fadec6203eccacb0ccaffc` (19:45:51 UTC). These are conflicting publication lineages, not ordinary updates to a shared Plan.

All 12 records were compared. Trade geometry matches, but priorities, source receipts and other source-dependent facts differ. MPWR additionally differs in original horizon (main 56 days, branch 45), leash and related management state. Existing corrections do not authorize replacing these terms. The integration therefore preserves main's complete earlier publication, including its index, raw Plans, management states, source archives, receipt, sparks, ledger and AIR Plan. No Plan terms were blended, no ID was fabricated, and same-date origination was not rerun.

The two ledgers contain the same 502 unique records and identical records by ID, with a shared byte-identical 499-record prefix. Their final three records differ only in append order. Main's complete ledger bytes are preserved.

Main's entire Arena publication bundle is preserved, including the six automatically mergeable cohort ledgers, so that a text merge cannot mix those ledgers with another scoreboard. The branch's distinct content-addressed `e655802d…` source archive remains retained as historical evidence. The publication directories differ from pinned main only by that retained archive.

The shared EW-P4 receipt is main's complete receipt paired with main's case 66 PNG. Its image digest is `5eb57c75755390a0daf35a94f3886ac7b4ebe688067ef667dd42a8d41f84f777`. Accepted branch evidence remains available at immutable `e5c288011f026cb74b2a2e265d6dfc767359565d`, where the corresponding PNG digest is `cf76b5116a47408bf08a80fc9fa96aca4cc7d7b0e2f0ed0df1e28c5904ba2e24`. Neither historical capture is relabeled as integrated-source evidence.

See [source-integration.json](source-integration.json) and [source-comparison.json](source-comparison.json).

## Native renderer and source guard

The existing `scripts.build_site` owner now supports an explicit frozen mode. Normal scheduled rendering retains its existing default behavior.

```bash
python -m scripts.build_site --no-refresh-stock-library \
  --frozen-us-board-sha256 1e821810c93753f5bcce47c083cc515486aaf38c9bd9b28af1b5639270f67471 \
  --frozen-us-gate-sha256 288fe5457782f460c3e705c2643ccb1a6b444a450f5e337c2f48b19aba3129a5
python -m scripts.inject_data_base
python -m scripts.externalize_css
python -m scripts.optimize_assets
```

Before any output write, frozen mode requires both exact SHA-256 pins, real source files, matching pair identity/writer/emission/session, the existing signal-gate coherence predicate and the native Today source binding. It skips the stock-library recomputation and profile translation. It preserves the existing public/protected split and paired output writers. A final check rejects source drift.

The bound board/gate pair is `e44f5a15c1414a63a65c05508fefb82f`, emitted `2026-11-05T02:30:51+00:00`, with data session `2026-11-03`. This later display pair is distinct from the immutable origination archive bound to the published Planbook. That distinction is retained.

The operation ran from a clean integrated source checkout. The wrapper recorded all 1,915 files under the frozen publication directories and both source files before the first module and after the last. All four module exits are zero, and all frozen input hashes match.

| Adopted artifact | SHA-256 | Bytes |
|---|---|---:|
| `site/us_stocks.html` | `5f09f469275023fa6cbee3db2e161796ae6c6f4febc6f924eeffceba756a8646` | 795,376 |
| `site/premiumdata/us_stocks.json` | `4931a5c91d9de49b6b3d109c4985310a0f43ebc2acaa5caf362bf442633699b3` | 9,735,092 |

The site-wide owner also touched 14,031 incidental paths. Those were restored to the integrated input commit before final browser capture. This included both `templates/movers.html` and `site/movers.html`, plus old hashed assets still required by retained pages. Every referenced Prophet stylesheet/script and all 567 recorded render inputs were checked after restoration. The two adopted artifacts retained their exact native-build hashes. No unrelated market refresh or mass restamping is included.

Receipts and inventories are in [build](build); the reproducible wrapper is [tools/build_frozen_native.py](tools/build_frozen_native.py).

## Publication integrity

The existing native verifier passes all 12 checks. The additional integration verifier passes 22 checks covering complete Plan membership, source order, public Today identity/served rows and published lifecycle values.

| Surface | Public | Protected / entitled | Published total |
|---|---:|---:|---:|
| Eligible Candidate Pool | 3 | 156 | 159 |
| Screener | 3 | 48 | 51 |
| Planbook | 3 | 851 | 854 |
| Today | 0 public articles | 6 in the entitled preview | 12 Featured |

Zero public Today rows is the actual access result; the browser checks the explicit access-empty state. It is not presented as zero setups or replaced with synthetic cards.

All 854 source Planbook IDs survive exactly once across the two partitions, in published order within each partition. AIR is included. All 56 protected Plan targets resolve. The public HTML exposes no protected Plan-target controls. The public Today source digest, pair ID, selection receipt, roster size and served-row receipts agree with the native owner and protected payload.

Displayed lifecycle values match the published count block: Watch 0, Ready 70, Entered 281, Delivering 0, Overtime 0, Invalidated 12, Resolved 491. The renderer does not derive replacement lifecycle totals from the gated row count.

See [validation/native-pair.json](validation/native-pair.json) and [validation/complete-pair.json](validation/complete-pair.json).

## Browser and visual verification

The exact generated public bytes were served through temporary anonymous public-only stages.

- Native page: 16 cells, widths 1440/768/390/320, English/Chinese, light/dark. Zero uncaught page exceptions and zero document overflow.
- Cautions: 16 matching cells with reduced motion. All three visible disclosure controls in each cell have at least 44 × 44 CSS-pixel targets. Native disclosure markers, Enter-to-open, Space-to-close, visible keyboard focus, card widths and public entitlement boundaries pass.
- Canonical theme evidence: 24 original PNGs through the unchanged `mastermind.p0_evidence.v2` producer—8 rest, 8 actual hover and 8 actual focus captures. All 16 requested forced states were applied to the real `a.terminal-link`.
- All canonical PNG hashes, byte counts and dimensions were verified against their manifest.
- Parent visual inspection covered desktop light/dark, mobile Chinese dark, the expanded 320px English and 390px Chinese Cautions cards, and the 768px Chinese card. The inspected cards have readable hierarchy, visible focus, complete action rows and no clipped disclosure content.

Native page capture records 128 HTTP 404 responses: the same eight omitted feed endpoints in each of 16 cells. These are explicitly offline feed gaps, not missing CSS/JS assets. Two feed paths are not files in the source checkout; no claim is made about their production service availability. The Cautions and canonical stages explicitly block JSON feeds and retain those blocked requests. Their network console messages remain in the raw records; no console-clean claim is made. These captures do not qualify live feed availability, authenticated hydration, account writes or production latency.

The canonical manifest retains its uncaptured access and synthetic-state gaps. User-authorized omissions are recorded honestly. See [validation/offline-feed-gaps.json](validation/offline-feed-gaps.json), [browser/observations.json](browser/observations.json), [cautions/observations.json](cautions/observations.json), and [theme/manifest.json](theme/manifest.json).

## Additional verification and source preservation

The material-UI evidence gate passed (exit0, 2.88seconds) against the full staged PR diff from pinned main, including the strengthened real-PNG integrity checker. See [validation/ui-evidence-gate.json](validation/ui-evidence-gate.json). The subsequently added gate receipt/documentation do not change rendered inputs or captured files. The staged source/documentation whitespace check passed; 486 native-generator trailing-whitespace warnings in the generated HTML were retained to preserve the exact producer output bytes.

The focused frozen-render/Today/Plan-relation batch passed 265 tests in 58.66 seconds; the exact log and source-file digest binding are retained. Earlier published 119 card/layout checks and five generated-shell checks remain in the preceding evidence packet; they are not relabeled as newly run tests.

Main's dossier observation-clock changes, Release Radar refresh behavior, and strengthened screenshot-byte checker are preserved by the merge. The final adopted output scope leaves unrelated main pages unchanged. Main subsequently advanced to `2fbee06234fec4e792918c1cb0d9f8ea2ed833c4` in three disjoint Agent OS/BEA/CI-document commits; the bounded comparison found no Prophet or shared UI source delta.

The original long-running local Git merge was interrupted only after checking its exact process identity, parent and checkout. Its absence, exit, removed lock/merge metadata and three incidental CSS deletions were reconciled. The three files were restored. The subsequent documented Git merge-tree operation completed in 0.92 seconds; the 25 conflicts were resolved in a temporary index and the prepared two-parent commit was checked out normally. No hook was disabled; there were no active local hooks. No held Fabric process was signaled or replayed.

## Remaining scope and continuity

PR #9495 remains Draft/HOLD. Source integration and local proof do not release a deployment hold.

The existing Fabric run `d03-pr9495-native-pair-publication-20261104-c2-v1` retains its canonical EFFECT_UNKNOWN projection. Existing terminal/process/GitHub receipts do not authorize a retry or manual lifecycle edit. Its incumbent owner still needs a supported exact-run reconciliation.

The original Chrome record distinguishes a working signed-in production tab from a refused local preview tab. It does not establish that Save itself was denied. No supported same-binding repair was established, and no human-only credential/physical gate was proven. Final candidate Save/readback/reopen and Sources → Plan → same-candidate return remain unaccepted until the authorized original production path is covered by lawful publication.

Paper bindings and held operations are unchanged. No optional independent review was awaited, and no formal nonauthor approval was claimed. See [CONTINUATION.md](CONTINUATION.md) for the exact frontier.
