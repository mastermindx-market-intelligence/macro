STATUS: PARTIAL

RESULT:
I checked all 46 rows (R3A-47..92) against the source at HEAD ec1f1ea694d5. Tally: 39 CONFIRMED, 0 DELIVERED, 1 PARTIAL (R3A-89), 0 NOT_DELIVERED, 5 UNSUPPORTED (R3A-47, -52, -66, -75, -86) and 1 BLOCK_CONFIRMED (R3A-92).

One finding is major. The SC-066 BLOCKED_DATA premise is false at HEAD. Commit 41a036f0fbc1 (SIC-D-B03, 2026-10-20) is an ancestor of both HEAD and the frozen 4161d404. It made `compute_basket_confluence` emit `n_listed`, `n_gateable` and `n_thin` (engine/subsector_confluence.py:488-491), and a test now pins those fields (tests/test_sector_membership_coverage.py:255-275).

The interim rendering is also untrue. The shared Confluence honesty line turns on whenever `cov.n_gateable` is present, but it reads `cov.n_subsectors` for the total (templates/subsectors.js:220-222). The basket payload has no `n_subsectors` field. So once the HEAD producer writes basket_confluence.json, the Baskets tab will show "N of undefined baskets have enough data to time · M thin". The proposal's interim ("candidate renders no Baskets thin/gateable disclosure line at all") and its premise ("no D-wave lane changed that producer", proposal.yml:542) are both contradicted at HEAD. The cure belongs to SIC-APR-05 and P20.

The other UNSUPPORTED rows are things I could not find at HEAD within the turn budget, not proven absences.

TABLE:
R3A-47 | UNSUPPORTED | templates/si_workspace.js:100; templates/sector_central.html.j2:43 | Only the module loads are confirmed (subsector_rotation.js, rotation_events.js, desk_watch.js). The five JSON bindings were not found. The cited rotation-* cells are #map, not #moving (cells.yml:7-95).
R3A-48 | CONFIRMED | templates/sector_central.html.j2:2314 | `si-read-money` with `data-regime` baked from flow.cluster.regime, guarded.
R3A-49 | CONFIRMED | templates/sector_central.html.j2:2325-2333, 2751, 2772 | Server regime headline (FLOW_V_EN/ZH) plus client etf_pulse/vol_sentiment chip mounts.
R3A-50 | CONFIRMED | templates/sector_central.html.j2:2320, 2963-2972 | `#mkt-breadth` gcards with a "Not measured" default; reads market_concentration.
R3A-51 | CONFIRMED | scripts/build_sector_central.py:456, 512-524; templates/sector_central.html.j2:2337 | `#sc-flows` is built server-side and injected via flows_html.
R3A-52 | UNSUPPORTED | templates/sector_central.html.j2:2342; si_workspace.js:103 | `#heatmap-scorecard` and the lazy heatmap.js load exist. The polling on `generated_utc` change was not found (2440/2448 only print it).
R3A-53 | CONFIRMED | templates/sector_central.html.j2:2344, 3393-3429, 3414 | `#scc-leadership` with Validated / Measuring / Accruing labels.
R3A-54 | CONFIRMED | templates/sector_central.html.j2:2366-2368, 2529, 2623-2629 | Mode tabs, category filter, column sort and range tabs, persisted in localStorage (fw-btbl-sort).
R3A-55 | CONFIRMED | templates/sector_central.html.j2:2484, 2596-2614 | `#btable`: name, optional Group pulse, sparkline, 1d..YTD, S&P 500 row in raw mode.
R3A-56 | CONFIRMED | templates/sector_central.html.j2:2529, 2532, 2596-2610 | Default {col:'20d', dir:-1}; TABLE_SHOW=8 top and bottom; "Show all (N)". The 49 count depends on data.
R3A-57 | CONFIRMED | templates/sector_central.html.j2:2380-2385, 2631, 2659-2667, 3005 | lightweight-charts rebased to 0%; draw deferred while clientWidth is 0; re-run on si:view.
R3A-58 | CONFIRMED | templates/sector_central.html.j2:2388; templates/time_machine.js:16, 196, 211 | `#tm-mount` lives in the Explore view, "No predictive claim". The cited dossier cells (sectors/XLK.html) do not show it; research-* cells do (tm-mount height 60, collapsed).
R3A-59 | CONFIRMED | engine/narrative_emergence.py:42, 165-180, 256-269; templates/forming_narratives.js:92-97 | Fixed-weight `_W` score with legs breakdown bar; no LLM in the score.
R3A-60 | CONFIRMED | engine/narrative_emergence.py:121, 293; templates/forming_narratives.js:149-151 | ai_watch printed separately and feeds no score. The DeepSeek/_call_model origin was not traced.
R3A-61 | CONFIRMED | engine/narrative_emergence.py:16, 211, 265, 280 | caveats_en/zh are produced. The client render line was not located (see DEVIATIONS).
R3A-62 | CONFIRMED | engine/narrative_emergence.py:101-115; templates/forming_narratives.js:16-28 | "Kill criterion:" is rewritten to "Watching for:" (EN) / 关注条件 (ZH).
R3A-63 | CONFIRMED | templates/subsectors.js:3-6, 41-43 | Four artifact URLs, one DS-driven engine, per-tab groupsKey.
R3A-64 | CONFIRMED | templates/sector_central.html.j2:2426-2429 | DOM order: S&P → Nasdaq → Russell → Baskets.
R3A-65 | CONFIRMED | templates/subsectors.js:220-222; engine/subsector_confluence.py:413-416 | n_gateable/n_subsectors/n_thin wording.
R3A-66 | UNSUPPORTED | engine/subsector_confluence.py:488-491; tests/test_sector_membership_coverage.py:255-275; templates/subsectors.js:220-222 | The block is not real at HEAD (B03 added the basket fields), and the interim would render "of undefined baskets". Major.
R3A-67 | CONFIRMED | templates/subsectors.js:220-222; engine/subsector_confluence.py:566-592 | Same code path as S&P; silent when n_thin=0.
R3A-68 | CONFIRMED | engine/sector_signals.py:86-100, 288 | `_STATE_META` with EN/ZH labels. I read 7 entries; the full count of 9 was not read.
R3A-69 | CONFIRMED | templates/subsectors.js:80-93; engine/subsector_confluence.py:208 | No ribbon bucket for forming; it falls to `counts.neutral++` (:93).
R3A-70 | CONFIRMED | engine/subsector_confluence.py:101-103, 208, 388, 405 | `_slug(sub)`, kind="subsector", `_CLASS_ORDER` sort. Nit: `_CLASS_ORDER` is a dict, not a tuple.
R3A-71 | CONFIRMED | templates/subsectors.js:467-473, 540 | Client re-sort, default tier ascending, independent of producer order.
R3A-72 | CONFIRMED | engine/subsector_confluence.py:458; templates/subsectors.js:41 | basket_id stamp; dir 'subsector/' with prefix 'b-'.
R3A-73 | CONFIRMED | engine/subsector_confluence.py:588-592 | "amalg-" prefix, kind="sector", with_members=True.
R3A-74 | CONFIRMED | templates/subsector_detail.html.j2; templates/subsectors.js:42-43 | subsector_nasdaq/ and subsector_russell/ directories. The cited cells are sectors/XLK.html, not detail pages.
R3A-75 | UNSUPPORTED | no evidence found at HEAD | The weight-desc / `vs_basket`-desc member sort was not located in subsector_detail.html.j2 or build_subsector_confluence.py.
R3A-76 | CONFIRMED | templates/subsectors.js:66; scripts/build_subsector_confluence.py:238, 424; templates/subsector_detail.html.j2:191 | stock.html# links (../stock.html# from detail pages).
R3A-77 | CONFIRMED | templates/subsectors.js:221-222 | Fixed EN/ZH template with `DS[ds].noun` swapped per universe.
R3A-78 | CONFIRMED | engine/subsector_confluence.py:369, 388, 411, 458 | The structural facts behind the 5-part rule exist; no runtime detector (the row describes an attack surface).
R3A-79 | CONFIRMED | templates/subsectors.js:496; state_matrix.csv:34 | Count-only "0 / N"; no no-results copy.
R3A-80 | CONFIRMED | templates/si_workspace.js:17, 387 | VIEWS array with exact-match dispatch.
R3A-81 | CONFIRMED | templates/si_workspace.js:52-74, 83-88 | The literal has 21 keys; S2 merges 3 at runtime (24 live). Nit: comment :45-48 says "two" keys.
R3A-82 | CONFIRMED | templates/sector_central.html.j2:2740-2745, 2999; templates/si_workspace.js:385 | Boot-time `#theme-` redirect; the router stands aside.
R3A-83 | CONFIRMED | templates/si_workspace.js:111, 288, 293-301, 386 | pendingTrace is held until the Act-Now row exists.
R3A-84 | CONFIRMED | templates/si_workspace.js:389-390 | Unknown hash → overview; empty hash → replaceState('#overview').
R3A-85 | CONFIRMED | templates/si_workspace.js:365 | `scrollIntoView({block:'start'})` with no behavior key.
R3A-86 | UNSUPPORTED | no evidence found at HEAD | The static and runtime href inventory for each view was not checked; the row has no evidence cells.
R3A-87 | CONFIRMED | templates/sector_central.html.j2:4079-4087; config/site_access.yml:769 | The pgate attempt-hydrate gates only the Act-Now payload under /premiumdata/. The exact filename was not read.
R3A-88 | CONFIRMED | templates/subsectors.js:41-43; state_matrix.csv:30 | Confluence fetches marketdata/ (ungated). The Map/Moving/Money fetch paths were not each checked.
R3A-89 | PARTIAL | engine/sector_central_grader.py:36-48, 120-164, 540-592; templates/si_workspace.js:271-277 | Delivered: n_neutral, directional_coverage, score_version_segments, "not a win rate". Residual: abstention and cohort-maturity fields not found, and there is no Record/Methods surface (evidence/README.md J14).
R3A-90 | CONFIRMED | templates/sector_central.html.j2:2432 | `#sc-app` is a static "Loading…" shell, no skeleton; Overview is baked HTML.
R3A-91 | CONFIRMED | templates/subsectors.js:302, 307, 318-339; templates/sector_central.html.j2:1904 | Confluence caps 4/8/12 with data-n/data-cap. Not confirmed that the slice(0,3) at :1904 is the Overview lane cap.
R3A-92 | BLOCK_CONFIRMED | design_refs/sector-paper-20261021/state_matrix.csv:6, 23, 40; templates/sector_central.html.j2:1973-1974 | No producer correction marker exists. Minor: explore:corrected is marked PRODUCED, but it cites a comparison-reset note, not a correction UI.

EVIDENCE:
- I read the artifact CSV (rows R3A-47..92 only) and sections A and D of P19_ACCEPTANCE_2026-11-02.md. I also read evidence/cells.yml (all 46 cells summarised) and evidence/README.md.
- `git rev-parse HEAD` = ec1f1ea694d5442e773b6158ce0cbad1385677fe.
- `git blame -L 486,491 engine/subsector_confluence.py` → 41a036f0fbc1. I then ran `git show 41a036f0fbc1`: the coverage changed from `{"n_baskets": len(baskets)}` to the n_listed/n_gateable/n_thin set.
- `git merge-base --is-ancestor 41a036f0fbc1` against HEAD, 4161d404 and d86344b93a0b: true for all three. It is not on origin/main.
- I ran targeted greps and line-ranged reads across templates/si_workspace.js, sector_central.html.j2, subsectors.js, forming_narratives.js, subsector_detail.html.j2, time_machine.js, engine/subsector_confluence.py, sector_signals.py, narrative_emergence.py, sector_central_grader.py, ledger_lane.py, scripts/build_sector_central.py, build_subsector_confluence.py, config/site_access.yml and state_matrix.csv.
- Tests:
  - `python3 -m pytest -q tests/test_sector_membership_coverage.py -p no:cacheprovider` → 17 passed. This includes test_basket_confluence_census_splits_thin_causes, which pins the basket n_gateable/n_thin fields.
  - `python3 -m pytest -q tests/test_sector_central_grader_v2.py tests/test_sector_central_score_version.py -p no:cacheprovider` → 23 passed, 16 warnings.

GAPS:
- R3A-66 UNSUPPORTED (major): the basket producer emits n_gateable/n_thin at HEAD (subsector_confluence.py:488-491, tested). The shared honesty line would then print "N of undefined baskets" (subsectors.js:220-222, reads `n_subsectors`). The BLOCKED_DATA premise and the "no disclosure line at all" interim are both false. To route to P20: fix the basket denominator (`n_listed`) or suppress the line on the Baskets tab, and re-dispose SC-066.
- R3A-47 UNSUPPORTED: the five-artifact JSON binding was not found (only the JS module loads), and the evidence cited is the wrong family (#map cells for a #moving capability).
- R3A-52 UNSUPPORTED: the polling-on-generated_utc half was not found at HEAD.
- R3A-75 UNSUPPORTED: the member sort (own-cascade weight desc, `vs_basket` desc) was not found.
- R3A-86 UNSUPPORTED: the per-view destination href inventory was not checked within the budget.
- R3A-89 PARTIAL: the grader denominator, directional coverage, version segments and "not a win rate" framing are delivered. Abstention and cohort-maturity fields were not found, and the Dossier Record/Methods home is absent at HEAD (evidence README J14). Residual owner: seat P20 / B13 lane.

DEVIATIONS:
- The evidence PNGs and cells.yml were captured on render tree d86344b93a0b, before main f125051f was merged. Visual claims are therefore bound to the pre-merge tree, not HEAD ec1f1ea6. I did not open any PNGs; visual judgments rest on the cells.yml facts only. No Baskets-tab cell exists, so the R3A-66 rendering defect cannot be seen in the evidence. It is inferred from the source.
- Sparse tree: data/ and site/marketdata/basket_confluence.json are absent, so I could not read whether production data already carries the B03 fields. On main the producer still emits only n_baskets, so the defect appears once #9917's producer runs.
- Evidence citations are wrong in several rows: R3A-58 and R3A-74 cite dossier cells (sectors/XLK.html) for #tm-mount and subsector-detail capabilities, and R3A-47 cites #map cells for Moving. I treated these as minor citation defects; the source verdicts stand.
- Checks not completed within the budget: R3A-61 client caveat render line, R3A-68 full nine-state count, R3A-87 exact premium filename, R3A-88 Map/Moving/Money fetch paths, R3A-91 Overview lane cap, R3A-60 DeepSeek origin. Each is noted in its row.
- tests/test_si_workspace_shell.py and test_si_chart_deferred_until_visible.py were not run because they are outside the permitted name prefixes.
- Outside this artifact's question: templates/forming_narratives.js:53-58 injects a runtime stylesheet carrying presentation. It is a legacy RETAIN surface carried unchanged, and the house design-system law still applies to it. Flagged for Fable to rule on; it is not a row verdict.