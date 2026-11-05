# D05 CI recovery — 2026-11-05

## Outcome and exact source

This bounded continuation repairs two demonstrated CI failures on the existing Draft/HOLD PR [#10703](https://github.com/mastermindx-market-intelligence/macro/pull/10703). Parent source is `82c377fb79ec746a0705c3c62a0be0a760cb001a`, tree `99c8cdf59e427406fd0f800f0f77eaf0d3164e70`. The prior bilingual citation repair is retained; its exact-head hosted ci-pack-6 passed in [run 41985510510](https://github.com/mastermindx-market-intelligence/macro/actions/runs/41985510510).

Publication uses the original GitHub Git Database expected-head, non-force branch carrier. No source workspace reset, index mutation, second branch, release, or denied-effect replay is part of this repair. The protected procedure pin is `f374289eb74587eaa755f5bc8e5a3252d00850e0`. Review classification: **SELF_REVIEWED**; no formal GitHub approval is asserted.

## Restore the Dossier evidence omitted during adoption

The component integration adopted published [#10707 source 74930f69](https://github.com/mastermindx-market-intelligence/macro/commit/74930f6931773b23072f91590319dc39fe5a7d07) but omitted its canonical evidence directory. The repair adopts the **same 27 existing Git blobs**, without altering screenshots or original metadata:

- `mockups/evidence/sector-r41-dossier-component/EVIDENCE.yml`
- Original manifest and smells report.
- 24 PNGs: desktop/mobile × dark/light × EN/ZH × rest/real hover/real focus.

The following rendering assets are byte-identical between the donor and target parent:

| Path | Git blob |
| --- | --- |
| templates/sector_dossier_cycle.css | ac7bcd8b7411dabf6de6e5df6a412348300388f1 |
| templates/sector_dossier_cycle.js | 909e43196a4efab130a7eba0563543ecd19ce220 |
| templates/theme.css | 619436f58d37a222d1db7021ba9d52bb3a05a7fa |
| site/mm_charts.js | 0afa1e6ef41d06687cc3fa9a986ba1701aa54c9e |
| scripts/capture_page_evidence.py | 78ba651d2996a64231c738a133ed465d73dd8caf |

A nonpublishing exact-blob staging directory ran the target parent's actual `check_ui_visual_evidence.py` receipt-shape, image-manifest, and applied hover/focus validators: **zero errors**; all 24 capture byte hashes and dimensions passed. This validates the restored receipt, not the full repository guard over every PR path. Hosted CI owns that result.

Actual screenshot self-QA inspected desktop dark/EN, desktop light/EN, mobile dark/EN, mobile light/ZH, and desktop light/EN keyboard focus. The sampled layouts have readable chart and explanatory text, no clipped controls, stacked touch actions on mobile, and a visible focus ring. Semantic distinctions between legacy cycle history, ontology position, and noncurrent model readings remain explicit.

**Provenance limit:** the original manifest is dated 2026-11-04 and records its original source context. These are anonymous synthetic component captures, not newly rendered target-head, authenticated host, current-market, or deployed-production evidence. The original nine-step composed journey and other accepted proof remain separately scoped. The unpublished compact-layout change in #10707 remains on its original blocked carrier and is not adopted or declared final visual acceptance.

## Adopt the existing measured quote-capacity repair

The shared board input grew to 415 distinct symbols. The previous cap of 480 left only 65 slots and violated the unchanged 15% headroom invariant (415 > 408).

This repair adopts the exact published `scripts/build_live_quotes.py` blob `8fcec4d0b3c144299a6a9797af08faee53f23f19` from [5fd92012 / #10725](https://github.com/mastermindx-market-intelligence/macro/commit/5fd9201274c0e92a5250b301e5b8b629ea4afca6). The donor's only code delta is **480 → 600**, accompanied by its measurement commentary. No symbol list, 85% guard, provider request cap, tile priority, quality floor, or truncation behavior is weakened.

Fresh local qualification used the exact parent commit's ten board HTML files and the board premium payload confirmed by `git ls-tree`:

| Observation | Result |
| --- | --- |
| Input bytes | 15,078,451 |
| Uncapped board symbols | 415 |
| Symbols retained at cap 600 | 415 / 415 |
| Capacity use | 69.17% |
| Remaining slots | 185 |
| Local source parse time | 0.126 seconds |
| Committed quote snapshot | 5,263 bytes / 27 quotes |
| Median serialized entry in that snapshot | 184 bytes |

The snapshot is only a local size sample. The adopted source commentary retains the donor's separate public-snapshot measurement and historical vendor-throughput estimate; neither is relabeled as a fresh vendor latency or current-data SLA.

The exact existing test file was run against this staged source for the affected headroom, premium payload coverage, charset, duplicate handling, oversized-board and macro-tile-priority paths: **13 passed, 52 deselected** in 5.07 seconds. Twelve host pytest temporary-directory cleanup warnings were unrelated to the assertions. Full hosted tests remain required.

Reproduction scope:

```text
python3 -m pytest -q -c /dev/null --confcutdir <exact-source-stage> \
  tests/test_build_live_quotes.py \
  -k 'display_board_leg or macro_tiles_keep_priority or board_leg_has_headroom or tier_payload_pills or board_coverage_per_market or a_gated_boards or payload_leg_keeps or board_duplicate or board_rejects'
```

The explicit stage/config isolates the selected exact Git source inputs from the original verification workspace's retained dirty source. It is a focused test, not a substitute for the repository CI configuration.

## Current editable canvas and remaining programme acceptance

A fresh original-carrier Studio read succeeded for file `01M6FAXA774QT1VRDMAG7DFQ2W`, page `p-3-0`: **12 artboards, 1,448 nodes**. The page remains titled “D05 · Production journey · provisional.” No canvas mutation was attempted. Paper 0.5.18 advertises catalog `16e6b93f0c51a1574ba8acee4df732052898707a04731d3817530971a88fdefd`; the original Studio adapter reports `accepted_for_write=false` and `catalog_compatible=false` against expected `ac18857df0aa6323646333368e5798e7c28de7b4d5f5dc3cb320276e3535daa9`. Read serviceability does not waive the write gate.

The [programme checkpoint](https://github.com/mastermindx-market-intelligence/macro/blob/b68f7c000dce612d81eff74ca253e0837a1e6371/research/design_candidates/production_design_20261102/d05/IMPLEMENTATION_CHECKPOINT_20261104.md) still governs the full **13-route / 174-capability / 119-case** obligation. This CI repair does not claim all-route acceptance.

Preserve Terminal #1244 publication custody, #10707's compact-layout refusal, Paper uncertain effects, source/census and correction acceptance, regional/account/saved-view/natural-refresh proof, and F01/F02 closure as distinct remaining work. Draft/HOLD remains: no Ready, merge, queue, relabel, deploy, or purchase.
