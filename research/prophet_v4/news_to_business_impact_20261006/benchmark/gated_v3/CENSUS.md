# gated_v3 census — NE-B4-GATED-V3-R3 (repair round 1)

- BASE: `64ef5131a5f50fb65f0ad25a049a457e18258495`
- RUN_ID: `ne-b4-gated-v3-20261022-r3` (branch `lane/ne-b4-gated-v3-20261022-r3`)
- MODEL: glm-5.3-flash
- Host: `ubuntu3-MS-7E61` (ubuntu3 fleet)
- Run date: 2026-10-22; ASOF (edgar_body `--as-of`): `2026-10-22`
- Python: CPython 3.12.13 at `/home/ubuntu3/lanes/tmp/ne-b4-gated-v3-20261022-r2/venv/bin/python`
  (r2 venv reused read-only per packet step 0a; pandas 3.0.6, pyarrow 26.0.0; system `python3.12`
  has no pandas — every packet `python3.12` invocation used this venv interpreter)
- **VERDICT: PASS-WITH-GAPS** — `PROVISIONAL pending seat ruling on the classifier pin`
  (all checks green; gap = sessions.json is RECONSTRUCTED, not RECOVERED)

Every number below is read from a file produced in this run or a committed BASE file, cited by path.

## 1. Inputs

| Input | Source commit | Expected sha256 | Observed sha256 | OK/BAD |
|---|---|---|---|---|
| `data/qbus/items.parquet` | `c49e4410492e` | `bab574014865532c63977e44f12be0e8a3234ba9faa8253d2717e43d67580e17` | same | OK |
| `data/news/event_log.parquet` | `59ffc3ec3277` | `2345274391433d6e448a5cce9c70bea9c9a1c4efd26f6ef2f7f9106ef185ac18` | same | OK |
| `data/news/reject_sample.parquet` | `59ffc3ec3277` | `5aed74fdc6adb208064005ad2b2634a91287d4a43f8eddecae2335cb0f6beeb0` | same | OK |
| `data/edgar/ticker_cik_ledger.json` | `da2f5a45deb1` | `6fe2459b360e16f5da1ac7f659feafb0eee3d11bb6c6477ff4fc05d4bf74621e` | same | OK |
| `benchmark/issuer_fallback/sec_fallback_ledger.json` (committed, at BASE) | — | sha recorded by the run: `b046d8515b2a5ea9e26680011a3afd8d46c15689e2ea82ffb32b7be6a956494c` (== `../issuer_fallback/README.md` value) | same | OK |

SEC reachability check: `https://data.sec.gov/submissions/CIK0000320193.json` -> HTTP 200 before the run.
`git rev-parse HEAD` == BASE before any step.

**sessions.json: RECONSTRUCTED.** Host is ubuntu3; the original `benchmark/README.md:37`
calendar (sha256 `80495fb43056ec8a8c5253b6a5bfa316f643a0e352e8ac73c4c3bc0105b46f36`) is not in
git and r2 already searched ubuntu3's home with no match, so this run reuses the r2
reconstruction byte-for-byte from commit `c6c11400bf44`
(`research/prophet_v4/news_to_business_impact_20261006/benchmark/body_frame_v3/sessions.json`,
sha256 `c029035df267ef4f3cc12ab46723069051f29d04311e8e49c7abb5ec0ac872b4`, verified before use
and committed unchanged here). Reconstruction rule: every weekday 2026-07-01..2026-12-31
except 2026-07-03, 2026-09-07, 2026-11-26, 2026-12-25. exchange_calendars cross-check: **null**
(not importable in the venv: `ModuleNotFoundError: No module named 'exchange_calendars'`;
per packet it was not installed).

**Step-0c calendar check (mandatory).** For every item_id whose committed v2 status in
`../body_frame_v2/status_map.json` is `body_unavailable:window_open` or
`body_unavailable:no_qualifying_8k`, `engine.news_impact.edgar_body.session_window(seendate,
sessions, band=(1, 4))` was computed from this run's `candidates_all.jsonl`
(engine/news_impact/edgar_body.py:226) and tested `(window end >= 2026-10-14) == (status is
window_open)`:

| | window end >= 2026-10-14 | window end < 2026-10-14 |
|---|---|---|
| **v2 status = window_open** | 113 | 0 |
| **v2 status = no_qualifying_8k** | 0 | 1,089 |

Examined 1,202 (expected 1,202); 0 missing from candidates; 0 None windows; 0 untestable;
**0 contradictions -> proceed**. (r2, without the pin, could examine only 1,201 rows because
BASE code had already dropped the drift row; with the pin all 1,202 are examined.)

## 2. Step-1 identity (tape_draw + fallback over the gated_v2 inputs, v2 frames)

Command per `../issuer_fallback/README.md` "Reproduce", seed 20261014, with
`--fallback-ledger ../issuer_fallback/sec_fallback_ledger.json --candidates-out`.

| File | s1 sha256 | committed `../gated_v2/` sha256 | identical |
|---|---|---|---|
| `cases.jsonl` | `d88f2d841800c6e7f80ff2c64f0a674768610d2275fde197b5dbcac33518ce71` | `d88f2d841800c6e7f80ff2c64f0a674768610d2275fde197b5dbcac33518ce71` | **YES** |
| `manifest.json` | `8ac625b3af620a9d9def2c8c02fbf40c9fe04fcfbb7b9438546a358d4ce93935` | `8ac625b3af620a9d9def2c8c02fbf40c9fe04fcfbb7b9438546a358d4ce93935` | **YES** |

Both byte-identical — the r2 identity failure is resolved. (r2's s1 `manifest.json` differed
exactly in `counters.low_value` 4 -> 5; with the pin it is 4 and the file is byte-identical.)

Fallback counts, s1 `draw_report.json` (this run) vs `../issuer_fallback/README.md`:

| Count | README (fallback on) | s1 observed | match |
|---|---|---|---|
| Resolved | 1,822 | 1,822 | yes |
| Resolved by the fallback | 256 | 256 | yes |
| Unresolved | 1,015 | 1,015 | yes |
| Unknown ticker | 101 | 101 | yes |
| No ticker named | 914 | 914 | yes |
| Fallback tickers used | 7,569 of 10,459 | 7,569 of 10,459 | yes |
| Candidates (pre-frame) | 2,837 | 2,837 | yes |
| Funnel `low_value` | 4 (committed `../gated_v2/manifest.json` counters) | 4 | yes |

### DEVIATIONS

- **Classifier pin (recorded verbatim):** `engine/news_common.py` was pinned to blob
  `ea8ada59ea34cbba3b55c2bdaa1f72a5c0a58156` from commit `6fc028727a5a`
  (`../issuer_fallback/README.md` freeze) for steps 1-4; the BASE blob
  `71e153136d66dad02239325a6927510a965d7026` was restored (`git checkout --`) before step 6 and
  it is not in the diff; never committed. Evidence: `git hash-object engine/news_common.py`
  printed `ea8ada59ea34cbba...` with the pin in place and `71e153136d66dad0...` after restore;
  `git status --porcelain` showed exactly ` M engine/news_common.py` during steps 1-4 and
  nothing under `engine/` after restore. Reason: BASE classifier drops item
  `92238f1f0606b57c` as low-value (r2 commit `c6c11400bf44` CENSUS.md section 2), while the
  frozen code keeps it — "exactly as registered" requires the frozen funnel.
- `python3.12` = the r2 venv interpreter (packet step 0a allowed substitution; system python3.12
  lacks pandas). Steps 0b/0c/6 non-data steps used system python3 for JSON/ sha tooling.
- Step 4: `tape_draw` wrote a 4th file, `candidates_meta.jsonl`, into `benchmark/gated_v3/`;
  it was moved out to lane scratch (`~/lanes/tmp/ne-b4-gated-v3-20261022-r3/extra/`) per packet
  and is not committed. The committed directory holds exactly `manifest.json`, `cases.jsonl`,
  `draw_report.json`.
- exchange_calendars cross-check printed null (module not importable; not installed).

## 3. Body funnel v3 vs v2

Source: `../body_frame_v3/body_report.json` and `../body_frame_v2/body_report.json`;
crosschecks against the two status maps.

| | v2 | v3 | delta |
|---|---|---|---|
| candidates | 2,837 | 2,837 | — |
| available | 364 | 420 | +56 |
| body_unavailable: no_cik | 1,271 | 1,015 | −256 |
| body_unavailable: no_qualifying_8k | 1,089 | 1,402 | +313 |
| body_unavailable: window_open | 113 | 0 | −113 |
| body_unavailable: any other code | 0 (calendar_gap / document_missing / empty_text / fetch_failed / index_failed / no_body_document / span_failed / submissions_failed / too_large all 0) | 0 (same codes all 0) | — |
| submissions fetched | 440 | 659 | +219 |
| indexes fetched | 411 | 484 | +73 |
| documents fetched | 802 | 940 | +138 |
| bytes fetched | 131,266,853 | 150,613,957 | +19,347,104 |
| texts written | 447 | 575 | +128 |

v3 status-map tally (this run, `../body_frame_v3/status_map.json`): available 420,
`body_unavailable:no_cik` 1,015, `body_unavailable:no_qualifying_8k` 1,402 — no other code.

- Of the 256 fallback-resolved rows (v2 `body_unavailable:no_cik` -> v3 CIK known): **256**
  kept a CIK, of which **42** are `available` and **214** are `body_unavailable:no_qualifying_8k`.
  (v2 no_cik 1,271 = 1,015 still no_cik + 42 available + 214 no_qualifying_8k.)
- Of the 113 v2 `body_unavailable:window_open` rows at as-of 2026-10-22: **14** now
  `available`, **99** `body_unavailable:no_qualifying_8k`, **0** still open.
- Reconciliation: 420 = 364 (v2 available, none lost) + 42 (fallback) + 14 (windows settled).
- Net no_qualifying_8k +313 = 99 (windows settled, no 8-K) + 214 (fallback-resolved, no 8-K).

## 4. Gates v3 vs v2

Source: `../body_frame_v3/gates2_map.json`, `../body_frame_v3/gates2_report.json`
(gates_version `ni-routing-gates-2`), vs `../body_frame_v2/gates2_report.json`.

| | v2 | v3 |
|---|---|---|
| n_candidates | 2,837 | 2,837 |
| **gated_in** | **135** | **173** |
| gated_out:no_body | 2,473 | 2,417 |
| gated_out:g1_commentary | 21 | 24 |
| gated_out:g1_market_report | 19 | 20 |
| gated_out:g1_quote_page | 3 | 5 |
| gated_out:g1_solicitation | 5 | 6 |
| gated_out:g2_ambiguous_ticker | 30 | 30 |
| gated_out:g2_issuer_absent | 67 | 70 |
| gated_out:g2_issuer_not_subject | 36 | 40 |
| gated_out:g3_event_mismatch | 17 | 19 |
| gated_out:g3_no_family_language | 25 | 26 |
| gated_out:g3_results_without_202 | 3 | 3 |
| gated_out:g3_template_sense | 3 | 4 |

Gated cells by template (v3 `draw_report.json` `gate_frame.gated_cells`):
T1 79 (ambiguous 6 / negative 6 / no_change 3 / positive 64), T2 81 (6/11/2/62),
T3 13 (1/1/0/11); v2: T1 54, T2 74, T3 7.

## 5. Draw v3 vs v2

Source: `manifest.json` and `draw_report.json` (this directory), vs `../gated_v2/manifest.json`
and `../gated_v2/draw_report.json`. Seed 20261014, sampler `ni-sampler-1`, window
2026-07-17..2026-10-14 in both; tape sha256 `bab57401...` in both.

Drawn per template x proxy cell (drawn / target, short = target − drawn):

| Cell | T1 v2 | T1 v3 | T2 v2 | T2 v3 | T3 v2 | T3 v3 |
|---|---|---|---|---|---|---|
| ambiguous | 3/30 (short 27) | 4/30 (26) | 6/30 (24) | 6/30 (24) | 0/30 (30) | 0/30 (30) |
| negative | 5/50 (45) | 6/50 (44) | 5/50 (45) | 7/50 (43) | 0/50 (50) | 1/50 (49) |
| no_change | 3/30 (27) | 3/30 (27) | 2/30 (28) | 1/30 (29) | 0/30 (30) | 0/30 (30) |
| positive | 38/90 (52) | 58/90 (32) | 33/90 (57) | 39/90 (51) | 4/90 (86) | 10/90 (80) |
| **total** | **49** | **71** | **46** | **53** | **4** | **11** |

- Total drawn: v2 99 -> **v3 135** (+36).
- Folds (v3): f1 28, f2 27, f3 27, f4 28, f5 25, prospective 0 (v2: 21/19/20/21/18/0).
- Megacap share (v3): T1 0.014084507042253521, T2 0.07547169811320754, T3 0.09090909090909091
  (cap 0.1; v2: 0.02040816326530612 / 0.08695652173913043 / 0.0).
- Max issuer groups (v3): T1 3, T2 2, T3 2 (cap 6; v2: 3 / 2 / 1).
- Counters (v3 manifest): low_value 4, outside_window 7,856, rights_refused 0,
  unresolved_issuer 0 (v2: 4 / 7,856 / 0 / 0 — the pin keeps low_value at the registered 4).
- Tag quotas (v3): indirect_transfer drawn 7/17/1 (T1/T2/T3, target 10), near_duplicate 0
  everywhere (target 20); tags on tape: indirect_transfer 463, near_duplicate 2.
- Frame (v3 `draw_report.json`): n_candidates_in_frame 420, frame_cells T1 155 / T2 181 /
  T3 84; holdout groups 2,316, largest `hg:5c803892ceb42ed3` size 47.

## 6. Overlap by item_id: gated_v3 vs gated_v2 `cases.jsonl`

- In both: **95**. NEW (v3 only): **40**. DROPPED (v2 only): **4**. 95 + 40 = 135 ✓.
- NEW per template: T1 23, T2 10, T3 7. Per template x cell: T1/ambiguous 1, T1/negative 1,
  T1/positive 21, T2/negative 2, T2/positive 8, T3/negative 1, T3/positive 6.
- DROPPED rows (item_id list) with their v3 body/gate status — all four are still
  `body_available` and `gated_in` in v3; they lost their slot at sampling, they were not
  excluded:
  - `2a25707f5e214065` — available / gated_in (its v2 group `grp:a727d3d65a820f1b` is the one
    v2 group absent from the v3 drawn set)
  - `ac46e1ff6b122b6c` — available / gated_in (v3 group `grp:a044e9e5fd944477` drew NEW case
    `4ebd7e5286323806` instead)
  - `bea9e4ca79450a7a` — available / gated_in (v3 group `grp:c070745e126e88bc` drew NEW case
    `b9119cfb98ad0aa6`)
  - `eff279aeb30a6267` — available / gated_in (v3 group `grp:73fe9ebe6fe62bc3` drew NEW case
    `c6690b067520bdfc`)
- Rule recorded verbatim (`../issuer_fallback/README.md`, "Next draw: gated_v3"): "A case
  already in gated_v2 keeps its routing verdict and grade. A case new to gated_v3 needs a
  routing verdict from a census card before it scores, and only MATCH scores."

## 7. Groups

- Number of gated_v3 group_ids: **135** (one per drawn case).
- Groups holding >1 drawn case: **0**.
- Groups that contain a gated_v2 case: **98** (95 of them drew the shared gated_v2 case itself;
  in 3 — `grp:73fe9ebe6fe62bc3`, `grp:a044e9e5fd944477`, `grp:c070745e126e88bc` — the drawn
  case is NEW and the group's gated_v2-labeled member went undrawn). 37 gated_v3 groups hold
  no gated_v2 case. Counts printed, not selected: at scoring time a labeled case is kept over
  an unlabeled one inside a group.

## 8. Open windows and exclusion codes at ASOF 2026-10-22

- Open windows at ASOF (`body_unavailable:window_open` in `../body_frame_v3/status_map.json`):
  **0** (expected 0 — printed, never padded).
- Frame exclusion codes (`draw_report.json` `frame.excluded_reasons`): no_cik 1,015,
  no_qualifying_8k 1,402; window_open 0.
- Gate exclusion codes (`draw_report.json` `gate_frame.excluded_codes`): g1_commentary 24,
  g1_market_report 20, g1_quote_page 5, g1_solicitation 6, g2_ambiguous_ticker 30,
  g2_issuer_absent 70, g2_issuer_not_subject 40, g3_event_mismatch 19,
  g3_no_family_language 26, g3_results_without_202 3, g3_template_sense 4; no_body 2,417.
- Funnel (55,110 tape rows -> 2,837 candidates): low_value 4, outside_window 7,856,
  non_english 11,348, no_family 31,754, seendate_dropped 1,311 (all `seendate_blank`).
- Body fetch failure codes (`../body_frame_v3/body_report.json` `reasons`): every code other
  than no_cik / no_qualifying_8k is 0 (fetch_failed, index_failed, submissions_failed,
  document_missing, no_body_document, empty_text, span_failed, too_large, calendar_gap all 0).

## 9. Denominators unchanged

`git diff --name-only 64ef5131a5f50fb65f0ad25a049a457e18258495 --
research/prophet_v4/news_to_business_impact_20261006/benchmark/{gated_v2,graded,results_w2,section11}`
prints nothing: no file under `gated_v2/`, `graded/`, `results_w2/` or `section11/` was
modified. gated_v2 / v2_match denominators are unchanged, and gated_v3 reports as its own
table.

## 10. Next

NEW cases: **40**; routing verdicts PENDING the seat (no gated_v3 card builder exists at
BASE — `results_w2/tools/build_v2_routing.py` is gated_v2-specific). Bodies/texts stay on this
host for the follow-on card lane:

- host: `ubuntu3-MS-7E61`
- path: `/home/ubuntu3/lanes/tmp/ne-b4-gated-v3-20261022-r3/bodies_v3/`
  (`bodies.jsonl`, `status_map.json`, `body_report.json`, `texts/`)
- `sha256sum bodies.jsonl` = `59bbeb2251d4e1577003d2eb118672592651b6428904256b098039a04b98c86c`
- also reusable: `~/lanes/tmp/ne-b4-gated-v3-20261022-r3/edgar_cache/` (warm SEC cache) and
  `~/lanes/tmp/ne-b4-gated-v3-20261022-r3/candidates_all.jsonl` (scratch, never committed)

## Step 6 evidence (BASE code, pin restored)

- `section11_registration --check`: `registration ok:
  research/prophet_v4/news_to_business_impact_20261006/benchmark/section11/registration.json`
  (exit 0; never regenerated).
- `pytest -q tests/test_news_impact_contracts.py tests/test_news_impact_section11.py
  tests/test_news_impact_tape_draw.py tests/test_news_impact_edgar_body.py` ->
  `243 passed in 5.33s`.
