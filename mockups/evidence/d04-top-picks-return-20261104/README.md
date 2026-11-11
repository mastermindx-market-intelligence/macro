# D04 Top Picks controls and return proof

## Scope and result

This continuation repairs the existing `/discovery.html` page in the original managed operation `d04-top-picks-return-20261104`, branch `sol/web-d04-top-picks-return-20261104`, acquired at `d18d83019f3972c9bd915c736210176c7bd0b6b5`.

The tested candidate preserves the selected view, conviction side, stable sector identity, stretch filter, logical company origin, focus and horizontal table position across the qualified standalone document-return path. It preserves the incumbent Terminal overlay and leaves same-document scroll restoration to native history. This is bounded source proof, not whole-programme D04 acceptance.

The work remains held: no merge, Ready/un-draft, queue admission, auto-merge, held relabel, deployment or purchase is authorized by this receipt.

## Changes and ownership

- Scope Hide stretched / parabolic to the global Top Picks lists. The sector overview, sector leaders/avoids and Buy zone remain available and retain their analytical values.
- Use source sector names as option identities instead of rank-dependent indices. Retain existing section IDs and company URLs.
- Add tab/tabpanel semantics, selected and pressed states, a visible sector label, bilingual filter/return messages and keyboard selection. Modified arrow/Home/End chords are not consumed by page tabs.
- Use one authored `.discovery-scroll.tbl-scroll` wrapper per table. The shared theme recognises its existing `.tbl-scroll` contract and does not add a second scroll owner.
- Keep controls and phone company links at the measured 44px interaction floor. Constrain wide tables inside their scroll region, provide a mobile scroll hint and visible focus, and respect the local reduced-motion rule.
- Opt in through `body[data-discovery-history="v1"]`. Store bounded page state under `history.state["mmx.topPicks.v1"]` with `replaceState`; retain foreign keys and the exact URL/search/hash. No extra history entries, account persistence, auth layer, router or data producer is introduced.
- Yield while embedded, while the shared shell owns the page, or while the incumbent Terminal overlay owns navigation. Ordinary keyboard activation and phone taps use that overlay at every tested matrix width.
- On document return, restore the logical origin only if no later user action or other owner supersedes it. Explain changed source dates, missing sectors/companies, invalid records and unavailable history writes.
- On changed-URL `popstate`, apply controls synchronously and let the browser restore viewport/table scroll. A saved company position can predate later in-document scrolling and must not be replayed over native fragment traversal.

The native history ownership decision is consistent with the [HTML history traversal algorithm](https://html.spec.whatwg.org/multipage/browsing-the-web.html#updating-the-document): `popstate` precedes restoration of persisted user state. The tested result is Chromium-specific; this reference is not a claim of universal browser parity.

## Recovery findings

The timed-out predecessor left an uncommitted candidate and a failing browser run. This session continued that exact workspace and operation.

1. **Nested scroll owner:** the page created `.discovery-scroll`, then shared `theme.js` wrapped its table in `.tbl-scroll`. The outer element did not scroll (316/316px client/scroll width); the inner element did (316/886px). Adding the established `.tbl-scroll` class to the authored wrapper repaired capture and restoration at the real scroll owner.
2. **Modified tab chords:** a focused tab consumed Alt/Ctrl/Meta/Shift navigation keys. A failing regression was recorded before the modifier guard was added. The passing regression establishes DOM event ownership, not execution of an OS/browser-chrome shortcut.
3. **Stale fragment position:** a saved company position could override later scrolling during same-document Back. Application scroll replay was removed from that path. The regression records a 0px visible-anchor difference after native Back.

Earlier failed and superseded reports and captures remain in this operation's evidence directories. They are diagnostic history and must not be presented as final passing proof.

## Ranking snapshot qualification

The workspace is sparse and lacks the complete enrichment inputs required for a qualified ranking rebuild. A normal builder invocation during recovery exposed this by producing zero sectors; that incomplete output was discarded.

The served candidate was then reproduced from the exact committed ranking page at the acquired base:

- Base HTML SHA-256: `2555f1bbccb192b90502a28381446a80ec0db89dafaebd8e2cf16122416263f6`.
- Snapshot date: 2026-11-03; retained generated timestamp: 2026-11-05 01:09 UTC.
- 11 source sectors and 25 tables.
- Every ranked `<tr>` and the complete Buy zone block remain byte-for-byte identical to that committed snapshot.
- Current source assets are copied and fingerprinted using the repository's existing asset helpers.

`render_committed_snapshot.py` is an evidence helper for reproducing these control-markup changes against that pinned data snapshot. It does not calculate scores, refresh data or replace `scripts/build_discovery.py`. The ordinary builder's change is limited to copying and fingerprinting the two new assets. A successful production rebuild with complete inputs is not claimed.

## Verification

| Check | Observed result | Receipt |
| --- | --- | --- |
| Focused browser journey suite | 51 passed, 0 failures, 0 page errors; 22 screenshots | `ux-evidence/d04-top-picks-return-20261104/final/browser-report.json` |
| Existing scoring/signal-gate source tests | 92 passed, 12 warnings, 16.42s test time; process exited 0 | Same-session process 8091, recorded in `final-validation.json` |
| Canonical visual capture | 16/16: desktop/mobile × EN/ZH × dark/light × rest/focused tabs | `manifest.json`, `ux_smells.json`, `EVIDENCE.yml` |
| JavaScript syntax | Passed | `source-checks.json` |
| Design-system enforce-added gate | 0 blocking findings; pre-existing estate findings remain non-blocking | `source-checks.json` |
| Runtime style injection guard | Passed within existing frozen allowances | `source-checks.json` |
| UI visual evidence gate | Passed using tracked diff plus all new template/site source files | `source-checks.json` |
| Diff whitespace and served/source asset equality | Passed | `source-checks.json` |

The source test command was:

```sh
python3 -m pytest -q tests/test_top_picks.py tests/test_signal_gate.py tests/test_signal_gate_coherence.py tests/test_signal_gate_validity_contract.py
```

Pytest reported cleanup warnings about an unrelated older temporary directory. There were no test failures; this operation did not delete that unrelated directory.

Browser coverage includes desktop 1440px and phone 390px in both languages/themes, a 320px Chinese/light return, scoped filtering, stable sectors, native document return, incumbent overlay return, reordered data, missing row/sector, changed source date, invalid state, foreign history state, unavailable `replaceState`, iframe/shared-shell opt-out, later focus and pre-pageshow deliberate scroll, native fragment history, modifier-event ownership, focused horizontal tables, filtered-empty/unsupplied states and fingerprinted asset delivery. Actual returned horizontal offsets include 94px for the sector table and 570px for the global table.

The canonical captures report no page console errors, failed responses or document horizontal overflow at either viewport. Wide table descendants remain deliberately contained in horizontal scroll regions. Heuristic layout-shift/timing metrics are recorded measurements, not a performance acceptance verdict.

## Visual self-QA

The source author inspected these final viewport images directly:

- `top-picks-1440-en-dark.png`
- `top-picks-1440-zh-light.png`
- `top-picks-390-zh-light.png`
- `top-picks-390-zh-dark.png`
- `global-table-return-390-en-light.png`
- `missing-sector.png`

The changed controls are readable, tab focus is visible, bilingual labels fit, wide analytical tables remain reachable within their panels, and the missing-sector message exposes the required next action. Existing dense analytical content is retained. The visual capture gate verifies all 16 canonical files and their declared state identity; it does not substitute for visual judgement or establish every accessibility requirement.

Disposition: **SELF_REVIEWED**. An optional read-only reasoning child identified the modifier and fragment issues above. Those findings were repaired and covered by the final browser pass. That advice is not a GitHub approval, and no independent-review requirement was invented.

## Reproduction

From the repository root, with the recorded base object and normal repository dependencies available:

```sh
python3 mockups/evidence/d04-top-picks-return-20261104/render_committed_snapshot.py
# Add --write only to recreate the qualified committed-snapshot fixture and assets.

python3 scripts/capture_page_evidence.py \
  --site-dir site --routes /discovery.html \
  --viewports desktop,mobile --locales en,zh --themes dark,light \
  --output-dir mockups/evidence/d04-top-picks-return-20261104 \
  --manifest mockups/evidence/d04-top-picks-return-20261104/manifest.json \
  --smells mockups/evidence/d04-top-picks-return-20261104/ux_smells.json \
  --force-state 'controls-focus:focus(body[data-discovery-history] .tabbtn)' \
  --settle-ms 1300
```

Run `python3 scripts/verify_top_picks_return_browser.py --out ux-evidence/d04-top-picks-return-20261104/new-diagnostic` to direct a new browser run to its own directory and retain the final receipt above. Do not overwrite the final run and then relabel a failed or materially different source candidate as passed.

The canonical capture's nearest-HEAD field records the pre-commit base accurately. Exact working source hashes are in the browser report, source checks and final validation receipt; those hashes qualify the bytes tested.

## Limits and programme continuity

The company and Terminal response fixtures are controlled same-origin test content. Fresh-document traversal deliberately disables Chromium BFCache; retained-document coverage here is for the incumbent overlay. This is not proof of live D07 company content/authentication, BFCache/Safari parity, cross-origin shared-shell full-state transport, account save/persistence, live data or production deployment.

No Paper canvas was edited in this source continuation. Final editable Paper composition, qualified F01/F02 contracts, D23 persistence, remaining route-family integration and full programme acceptance retain their existing status. The 75 whole-programme acceptance cases remain unpromoted; the 25 inherited conditions are not silently discharged.

Confluence #10705 and US Heatmap #10719 remain accepted source work to preserve. The separate old heatmap Fabric commission remains unreconciled with no proven START/return; this continuation did not replay or replace it. The existing D04 #7727 continuation is the durable programme handoff and receives the source PR/head and exact next action after publication.
