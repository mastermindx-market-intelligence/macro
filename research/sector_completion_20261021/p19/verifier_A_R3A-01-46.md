STATUS: PARTIAL

RESULT:
I reviewed all 46 rows (R3A-01..46) against HEAD ec1f1ea6. Coverage is complete. The status is PARTIAL because the artifact does not hold up as written. Of the 45 RETAIN rows, 42 are CONFIRMED and 3 are UNSUPPORTED (R3A-20, R3A-25, R3A-31). R3A-27 is confirmed for its named capability, but it fails the contract clause the matrix gives that row; it is listed under GAPS. The one IMPROVE row, R3A-35, is PARTIAL. No rows in this range are DELIVERED (in full), NOT_DELIVERED or BLOCK_CONFIRMED (counts: CONFIRMED 42, DELIVERED 0, PARTIAL 1, NOT_DELIVERED 0, UNSUPPORTED 3, BLOCK_CONFIRMED 0). The seat did not check any row itself: the RETAIN claims and the IMPROVE claim are fixed sentences that ask the verifier to do the check ("verify presence on HEAD").

Findings on the artifact:
- **major:** `P19_CAPABILITY_DISPOSITION_2026-11-02.csv` drops the `contract` column of `CAPABILITY_MATRIX_2026-10-21.csv`. That column holds the per-row acceptance text, for example R3A-03 "preview rows never become the denominator" and R3A-27 "an invalid timestamp is unavailable, never fresh". `row_specific_acceptance` is empty for all 46 R3A rows (only 28 of 134 rows have it), so nothing in the packet judges a row against its own contract.
- **major:** the `candidate_stage_claim` text is the same on all 45 RETAIN rows and asserts no evidence. Section D's statement that every claim must be "supportable from the named source" is therefore met by no row as authored.
- **minor:** the proposal target sentence "carried unchanged inside the shell's Explore workflow" is wrong for R3A-01..08, 12, 20, 24 and 25. On HEAD these sit in the Brief view (`data-view="overview"`, templates/sector_central.html.j2:1510, :2092), not in Explore. The phrase "sic-p-rev finding 4 OPEN for the reviewers" also remains in every one of these targets, and no closure is recorded in proposal.yml or verdict.yml.
- **minor:** the Explore view switchers are hidden in the new shell (`<nav class="si-side" ... hidden>`, :1502). Rotation, money, explore and confluence are reachable only through hash links (`_sector_central_brief.html.j2` links to #moving, #money and #confluence). Reachability for R3A-36..46 depends on those links and on the router; the interaction is not proven here (P22).

TABLE:
R3A-01 | CONFIRMED | templates/_us_act_now_board.html.j2:528-532,555-650; sector_central.html.j2:2092-2093 | Six keys fold into 5 columns; hold+avoid share one Stand-aside body (:532,:641-648). Sits in Brief, not Explore.
R3A-02 | CONFIRMED | _us_act_now_board.html.j2:559-562,578-581,597-600,616-619,636-639 | EN/ZH labels and subcopy present verbatim.
R3A-03 | CONFIRMED | _us_act_now_board.html.j2:528-538,560 | Counts taken from the full board before the gated slice; comment states that counts are free.
R3A-04 | CONFIRMED | scripts/build_site.py:2216-2227 | Basket rows come first, then sectors (`bi.get("buy_soon") + buy_soon`).
R3A-05 | CONFIRMED | scripts/build_site.py:2151 | Sort key is `days` ascending, None→99. Note that basket buy_soon is sorted by score (:1872).
R3A-06 | CONFIRMED | _us_act_now_board.html.j2:493-494,507-508 | Theme score and perf_20d_rel rendered with is-not-none guards.
R3A-07 | CONFIRMED | _us_act_now_board.html.j2:478 | stat_en/stat_zh chip on sector rows.
R3A-08 | CONFIRMED | engine/sector_central.py (conviction chain); sector_central.html.j2:2278 `#board` | Separate artifact kept. Distinctness from the action board shown by source layout only.
R3A-09 | CONFIRMED | scripts/build_site.py:1887-1900 (US_SECTOR_PAGE→basket/us_sector_*); templates/sector_cycles.js:1246,1275; _us_act_now_board.html.j2:463 | Override table maps tickers to basket pages; sectors/<TICKER> is the legacy fallback.
R3A-10 | CONFIRMED | scripts/build_site.py:1781; _us_act_now_board.html.j2:486 | basket/<id>.html href, consumed verbatim.
R3A-11 | CONFIRMED | templates/_us_bottoming_watch.html.j2:95 | `href="{{ x.href }}"` taken verbatim from the producer.
R3A-12 | CONFIRMED | _us_act_now_board.html.j2:569,588,607,626,650 | All five lanes link to sector_central.html#actnow-section. Not checked: how the hash router handles that anchor.
R3A-13 | CONFIRMED | sector_central.html.j2:2094-2096 | "Drill to stocks →" links to #confluence; it is a section foot, not a per-lane foot.
R3A-14 | CONFIRMED | config.yml:7487-7489; _us_act_now_board.html.j2:64,539-545 | gated:true, preview_rows:3; preview/locked split.
R3A-15 | CONFIRMED | scripts/build_sector_central.py:224-246,296 | split_actnow is pure and gets the same dict as the page render.
R3A-16 | CONFIRMED | scripts/build_sector_central.py:273,286-297 | tier_payload.v1 written to premiumdata/sector_central.json; build continues if the write fails.
R3A-17 | CONFIRMED | scripts/build_sector_central.py:56-66 | Separate file, with the rationale against sharing us_stocks.json.
R3A-18 | CONFIRMED | config/site_access.yml:20,145; build_sector_central.py:61 | /premiumdata/ prefix enforced early. Served enforcement is P22.
R3A-19 | CONFIRMED | sector_central.html.j2:4085-4168 | whenAuthSettled → hydrate → data-ab-lane insert → restoreFold.
R3A-20 | UNSUPPORTED | templates/_sector_central_paper.css.j2:26; si_workspace.js:164-182,281 | readOverview still paints, but `.si-view[data-view="overview"] .si-view-read{display:none}` hides the strip in the Brief. Not "carried unchanged".
R3A-21 | CONFIRMED | _us_bottoming_watch.html.j2:24-27,100-107 | signal/timing_state never rendered; watch-only chips.
R3A-22 | CONFIRMED | _us_bottoming_watch.html.j2:83,86,107 | EN/ZH title, subcopy and chips present. Empty/null wording not individually checked.
R3A-23 | CONFIRMED | _us_bottoming_watch.html.j2:2,21,63; _us_act_now_board.html.j2:660 | `grid-column:1/-1` strip under the five lanes, not a sixth column.
R3A-24 | CONFIRMED | sector_central.html.j2:1512-1562,1564,2101-2147,2314 | Hero, handoff and What-changed read theme_context, factor_season and flow.
R3A-25 | UNSUPPORTED | sector_central.html.j2:1516,1529 vs main f125051f :2354 | The generic "US Sector Intelligence" hero eyebrow is gone. Fallback is now "Leadership not measured."; same intent, different form, needs re-disposition.
R3A-26 | CONFIRMED | scripts/build_site.py:1991 (action_board signature has no theme_context); build_sector_central.py:224-296 | No hero→lane path found. build_bottoming_context mutates the board from act_now (:326), not from hero text.
R3A-27 | CONFIRMED (contract gap) | sector_central.html.j2:1638-1646 | 12h guard present. But `stale=isFinite(builtMs)&&…`, so an invalid as_of_utc gives stale=false and the contract "invalid → unavailable, never fresh" is not met.
R3A-28 | CONFIRMED | _us_act_now_board.html.j2:417,443,493,507 | `is not none and is defined` idioms.
R3A-29 | CONFIRMED | _us_act_now_board.html.j2:565-567,584-586,603-605,622-624 | Jinja for/else empty-state copy.
R3A-30 | CONFIRMED | scripts/build_sector_central.py:483-524 | Each source has its own try/except and falls back (flows_html→None at :524).
R3A-31 | UNSUPPORTED | sector_central.html.j2:3024; `id="actnow"` exists only in templates/_baskets_desk.html.j2:366 | The fixed string is present, but its target #actnow is not on this page (the board is server-rendered, :2088-2091), so the failure message can never show.
R3A-32 | CONFIRMED | sector_central.html.j2:2031,4085 | 401/403 → 'denied'; the shell and preview are kept.
R3A-33 | CONFIRMED | _us_act_now_board.html.j2:33,466,489 | dispshort table; full name in ZH branch. CSS ellipsis not checked visually.
R3A-34 | CONFIRMED | _us_act_now_board.html.j2:219-226,571; sector_central.html.j2:4126 | 3-row fold, control hidden below the threshold, restoreFold on the hydrate path.
R3A-35 | PARTIAL | engine/sector_central_grader.py:34-48,106-153; sector_central.html.j2:2097,3327-3366; si_workspace.js graderVersionFrame | Engine v2 fields delivered (coverage, n_neutral, cohort, score_version, "not a win rate"). Residual: the grader card still lives in Brief #actnow-section, not the Dossier Record/Methods home; renderGrader shows no n_neutral/abstention; dossier:corrected/abstained NOT YET PRODUCED.
R3A-36 | CONFIRMED | sector_central.html.j2:2150,2171 | #rvx-rmap SVG in the map view.
R3A-37 | CONFIRMED | sector_central.html.j2:2191 | #rvx-board ranked list.
R3A-38 | CONFIRMED | sector_central.html.j2:2870-2871,2937 | RVX_RECO enter/accumulate/hold/trim/avoid → Buy/Add/Hold/Trim/Avoid.
R3A-39 | CONFIRMED | sector_central.html.j2:2257; si_workspace.js:90,101 | #sc-chart lazy-mounted through `map:['@cycles']`. It sits in the Market-map view, not a Cycles view.
R3A-40 | CONFIRMED | sector_central.html.j2:2278,2280 | #board with an ordering receipt.
R3A-41 | CONFIRMED | sector_central.html.j2:2151; si_workspace.js:184-199,282 | readMap paints #si-read-map (no CSS suppression outside overview).
R3A-42 | CONFIRMED | sector_central.html.j2:2158 (map-view si-vocab tip); :2094 | Disclaimer carried in the same form as main :2452 and :2388. The literal "Only the lanes above" string is not present.
R3A-43 | CONFIRMED | sector_central.html.j2:2295; si_workspace.js:200-213 | Counts by the sign of pulse_rank_delta_5d only.
R3A-44 | CONFIRMED | sector_central.html.j2:2304 | #rc-events-mount in the moving view.
R3A-45 | CONFIRMED | sector_central.html.j2:2305; templates/subsector_rotation.js:299,319,432 | #rotation-app with drawStrip and drawTrackRecord. The 269-subsector count was not checked (data absent).
R3A-46 | CONFIRMED | sector_central.html.j2:2306; templates/desk_watch.js:12-15,319 | DISPLAY-ONLY, fail-soft, "Watch material, not calls".

EVIDENCE:
- `git rev-parse HEAD` → ec1f1ea694d5442e773b6158ce0cbad1385677fe.
- Parsed the P19 CSV for rows R3A-01..46. Compared it with CAPABILITY_MATRIX_2026-10-21.csv: the `contract` column is missing from the P19 CSV. Read crosswalk rows 1-46.
- Several batches of `git -C <tree> grep -n -E` over templates, scripts, engine, config.yml and config/site_access.yml.
- `sed` line reads of sector_central.html.j2 (1486-1570, 1638-1652, 2076-2150, 3020-3026, 3327-3366), _us_act_now_board.html.j2 (526-563), si_workspace.js (160-290), build_site.py (1885-1900) and config.yml (7487-7491).
- `git log -S` on the paper CSS rule: added in 4fd82658 (2026-10-20, branch-only).
- `git show f125051fdb37:templates/sector_central.html.j2 | grep`: main hero eyebrow "US Sector Intelligence 🇺🇸" at :2354; lane-foot disclaimer at :2388; map-view tip at :2452.
- Read the brief width entries in cells.yml (821, 887, 953): horizontal_overflow false.
- `python3 -m pytest -q tests/test_sector_central_gate.py tests/test_sector_central_grader_v2.py tests/test_sector_central_paper.py tests/test_sector_central_contract.py -p no:cacheprovider` → 139 passed, 16 warnings (numpy divide RuntimeWarning in test_rank_ic_distribution_negative_mean_preserved), 0 failed.

GAPS:
- R3A-20 UNSUPPORTED: the si-read-overview strip is hidden by _sector_central_paper.css.j2:26 in the Brief. Either show it or re-disposition the row as RELOCATE/IMPROVE.
- R3A-25 UNSUPPORTED: the generic "US Sector Intelligence" hero fallback was replaced by "Leadership not measured." (:1529). The row needs re-disposition; RETAIN is false as written.
- R3A-31 UNSUPPORTED: the fetch-fail string targets #actnow, which is absent from sector_central (only in _baskets_desk.html.j2:366), so the fallback is dead code. This is probably an inherited defect.
- R3A-35 PARTIAL: engine v2 grader fields are delivered, but the card stays in the Brief action section, its renderer omits Neutral/abstention, and the dossier corrected/abstained states are NOT YET PRODUCED.
- R3A-27 (contract caveat on a CONFIRMED row): an invalid as_of_utc gives stale=false (:1646), which breaks "never fresh".
- Artifact-level (major): the `contract` column was dropped and `row_specific_acceptance` is empty, so the candidate claims are untested placeholders.

DEVIATIONS:
- The tree is sparse, so data/ and site/ are absent. I judged runtime counts (269 subsectors, 11 SPDRs, 49 baskets) from source only.
- I did not open any evidence PNGs. The visual checks rely on cells.yml metadata only, so no visual dark/light design review was done for these rows. Production Brief cells exist only as dark EN widths (w320/w430/w768); light and ZH Brief coverage rests on R4 specimen boards 37/38, which I did not view.
- Not verified, because the budget ended at the coordinator's limit:
  - the hash-router mapping of #actnow-section;
  - the exact empty-state and null-disclosure strings in the bottoming watch (R3A-22);
  - the CSS ellipsis fallback (R3A-33);
  - "written unconditionally every build" beyond the guarded write at build_sector_central.py:273-297.
- Pre-existing versus branch-introduced: confirmed only for R3A-25 (main differs) and R3A-20 (the CSS is branch-only). R3A-31 and R3A-27 were not compared with main.
- STATUS uses PARTIAL to report findings. Row coverage itself is complete (46 of 46).