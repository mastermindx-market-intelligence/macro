# gated_v3 draw census — NE-B4-GATED-V3

- BASE: `64ef5131a5f50fb65f0ad25a049a457e18258495` (verified: `git rev-parse HEAD` == BASE)
- RUN_ID: `ne-b4-gated-v3-20261022-r2`
- MODEL: glm-5.3-flash
- Host: `ubuntu3-MS-7E61` (Linux fleet host)
- Run date: 2026-10-22
- ASOF: `2026-10-22` (intended value; step 2 never ran, so no `--as-of` was consumed)
- Python: 3.12.13, run through a scratch venv at `~/lanes/tmp/ne-b4-gated-v3-20261022-r2/venv`
  (system python3.12 has no pandas; venv installed pandas 3.0.6, pyarrow 26.0.0, pyyaml 6.0.3,
  jsonschema 4.26.0, requests — see DEVIATIONS)
- VERDICT: BLOCKED

BLOCKED at the step-1 identity check: `cases.jsonl` reproduces committed gated_v2
byte-identically, but `manifest.json` does not. Root cause, established below, is code
drift in `engine/news_common.py` between the gated_v2 draw commit and BASE: exactly one
tape candidate's low-value classification flipped, which moves the manifest `counters.low_value`
counter (4 -> 5), the candidate count (2,837 -> 2,836) and the resolved count (1,822 -> 1,821).
Steps 2-4 (edgar_body fetch, routing_gates_2, the gated_v3 draw) were NOT run, per the
commission's STOP rule. No PR was opened.

## 1. Inputs

| Input | Source commit | Expected sha256 | Observed sha256 | OK |
|---|---|---|---|---|
| `data/qbus/items.parquet` | `c49e4410492e8d2a0a16d00eca5edb3b45d66bc7` | `bab574014865532c63977e44f12be0e8a3234ba9faa8253d2717e43d67580e17` | same | OK |
| `data/news/event_log.parquet` | `59ffc3ec32779bce8cad609ca59a1d5ad1508ae6` | `2345274391433d6e448a5cce9c70bea9c9a1c4efd26f6ef2f7f9106ef185ac18` | same | OK |
| `data/news/reject_sample.parquet` | `59ffc3ec32779bce8cad609ca59a1d5ad1508ae6` | `5aed74fdc6adb208064005ad2b2634a91287d4a43f8eddecae2335cb0f6beeb0` | same | OK |
| `data/edgar/ticker_cik_ledger.json` | `da2f5a45deb1d3c2970de593643c10aaa34e7634` | `6fe2459b360e16f5da1ac7f659feafb0eee3d11bb6c6477ff4fc05d4bf74621e` | same | OK |

SEC reachability: `https://data.sec.gov/submissions/CIK0000320193.json` returned `200`.

`sessions.json`: benchmark/README.md:37 (sha256 `80495fb43056ec8a8c5253b6a5bfa316f643a0e352e8ac73c4c3bc0105b46f36`)
is not in git; the one bounded home search found no match. RECONSTRUCTED at
`~/lanes/tmp/ne-b4-gated-v3-20261022-r2/in/sessions.json` (also committed as
`../body_frame_v3/sessions.json`), sha256
`c029035df267ef4f3cc12ab46723069051f29d04311e8e49c7abb5ec0ac872b4`, rule: every weekday
2026-07-01..2026-12-31 except 2026-07-03, 2026-09-07, 2026-11-26, 2026-12-25 (NYSE full
closures; early closes are sessions), ISO ascending, 128 sessions, written with
`json.dumps(obj, indent=1) + "\n"`. `exchange_calendars` cross-check: null — the module is
not importable on this host (system python3.12 and the venv both raise ModuleNotFoundError)
and installing it was not authorized.

Calendar check (step 0c, mandatory either way) — for every item_id whose committed v2
status in `../body_frame_v2/status_map.json` is `body_unavailable:window_open` or
`body_unavailable:no_qualifying_8k`, `engine.news_impact.edgar_body.session_window(seendate,
sessions, band=(1, 4))` computed from the step-1 candidates file, tested
`(window end >= 2026-10-14) == (status is window_open)`:

| v2 status | window end >= 2026-10-14 | window end < 2026-10-14 |
|---|---|---|
| `body_unavailable:window_open` | 113 | 0 |
| `body_unavailable:no_qualifying_8k` | 0 | 1,088 |

Expected rows 1,202; examined 1,201; 1 row (`92238f1f0606b57c`, v2 status
`body_unavailable:no_qualifying_8k`) has no seendate in the step-1 candidates file and could
not be tested. That row is exactly the code-drift row of section 2: BASE code drops it as
low-value before the candidates write; the v2-era code kept it as a candidate (it is the
1,089th `no_qualifying_8k` row). Among the 1,201 testable rows there are 0 contradictions
and 0 None windows.

## 2. Step-1 identity (tape_draw + fallback over the gated_v2 inputs, v2 frames)

Command per issuer_fallback/README.md "Reproduce", seed 20261014, with
`--fallback-ledger ../issuer_fallback/sec_fallback_ledger.json --candidates-out`.

| File | s1 sha256 | committed gated_v2 sha256 | identical |
|---|---|---|---|
| `cases.jsonl` | `d88f2d841800c6e7f80ff2c64f0a674768610d2275fde197b5dbcac33518ce71` | `d88f2d841800c6e7f80ff2c64f0a674768610d2275fde197b5dbcac33518ce71` | YES |
| `manifest.json` | `5a0ed82b0feed195049df7f9f4517278e223c3ef1e33a83ae23992cc2b341a37` | `8ac625b3af620a9d9def2c8c02fbf40c9fe04fcfbb7b9438546a358d4ce93935` | **NO** |

The full manifest byte-diff is two values: `counters.low_value` `4` (committed) -> `5` (s1),
and the self-recorded `manifest_sha256`. Everything else in the manifest is identical.

Fallback counts, s1 `draw_report.json` vs issuer_fallback/README.md:

| Count | README (fallback on) | s1 observed | match |
|---|---|---|---|
| Resolved | 1,822 | 1,821 | no |
| Resolved by the fallback | 256 | 256 | yes |
| Unresolved | 1,015 | 1,015 | yes |
| Unknown ticker | 101 | 101 | yes |
| No ticker named | 914 | 914 | yes |
| Fallback tickers used | 7,569 of 10,459 | 7,569 of 10,459 | yes |
| Candidates (pre-frame) | 2,837 | 2,836 | no |
| Funnel `low_value` | 4 (committed `../gated_v2/manifest.json` counters) | 5 | no |

Fallback ledger sha256 recorded in the s1 report:
`b046d8515b2a5ea9e26680011a3afd8d46c15689e2ea82ffb32b7be6a956494c` (== README value).

### Root cause of the three deltas (one row, one cause)

`git log d12fb486d37..HEAD -- engine/news_common.py` shows 4 commits touched the
low-value classifier after the commit (`d12fb486d37`, #9367) that added the committed
gated_v2 manifest: `1298ed42813` (#9846), `526ce826f08` (#9942), `dcd72169ecb` (#9963),
`2c2aa51fcb0` (#9990). The diff adds an alternative to `_ROUNDUP_RE` in
`engine/news_common.py` (explicit numbered analyst roundups: `\d{1,2}\s+top|top\s+\d{1,2}`
+ `(analyst\s+)?(forecasts|upgrades|downgrades)`).

Replaying both classifiers (`low_value_reason(title, source)`) over the raw tape with the
exact funnel filters (window 2026-07-17..2026-10-14, `lang == "en"`, not reject-routed;
34,595 rows checked): old code 4 low-value rows, BASE code 5. Exactly one row differs:
`item_id=92238f1f0606b57c`, source `Benzinga`, old reason `-`, new reason
`stock_pick_roundup`. The old code run in this same environment reproduces the committed
counter (4), candidate count (2,837) and resolved count (1,822) exactly, so the drift is
code, not the venv/pandas environment. The dropped row was previously primary-resolved
(fallback-resolved stays 256, unknown ticker stays 101, no-ticker stays 914), which is why
`cases.jsonl` — the drawn set — is still byte-identical while the manifest counters move.

This is the commission's "inputs or code drift" STOP: a gated_v3 drawn at BASE would differ
from gated_v2 through the low-value reclassification in addition to the intended new-bodies
effect, and the pool denominators would shift (2,836 vs 2,837) without a seat ruling.

## 3. Body funnel v3 vs v2

null — step 2 (edgar_body ni-edgar-body-2) not run; STOP at step-1 identity.
No SEC fetch happened from this lane beyond the single reachability probe.
v2 reference (`../body_frame_v2/body_report.json`): candidates 2,837; available 364;
`no_cik` 1,271; `no_qualifying_8k` 1,089; `window_open` 113; submissions_fetched 440;
indexes_fetched 411; documents_fetched 802; texts_written 447; bytes_fetched 131,266,853.

## 4. Gates v3 vs v2

null — step 3 (routing_gates_2) not run.
v2 reference (`../body_frame_v2/gates2_report.json`): n_candidates 2,837; gated_in 135;
`gates_version` `ni-routing-gates-2`; per-code gated_out counts as committed there.

## 5. Draw v3 vs v2

null — step 4 (tape_draw with the v3 frames) not run.
v2 reference (`../gated_v2/manifest.json` + README): 99 drawn = T1 49 / T2 46 / T3 4.

## 6. Overlap gated_v3 vs gated_v2 by item_id

null — the gated_v3 draw does not exist, so the NEW/DROPPED partition cannot be computed.
Rule recorded verbatim: a case already in gated_v2 keeps its routing verdict and grade; a
NEW case needs a seat routing verdict from a census card before it scores; only MATCH scores.

## 7. Groups

null — no gated_v3 group_ids exist.

## 8. Open windows at ASOF

null — no ASOF fetch ran. Expected 0 open windows printed at draw time when the draw runs.

## 9. Denominators

gated_v2 / v2_match denominators are unchanged by this run: nothing under
`$P/benchmark/gated_v2/`, `graded/`, `results_w2/`, `section11/` was touched
(`git diff --name-only BASE -- <those paths>` prints nothing; the lane branch adds only
this file and `../body_frame_v3/sessions.json`). gated_v3, when it exists after a seat
ruling, reports as its own table.

## 10. Next

The seat must rule on the drift before any gated_v3 draw: either (a) re-freeze gated_v3
against BASE code, accepting funnel denominators 2,836 candidates / 1,821 resolved and a
v2-vs-v3 pool delta of the one reclassified row (`92238f1f0606b57c`), or (b) pin the draw
to pre-drift code, or (c) waive the manifest identity requirement explicitly. Steps 2-4
then run unchanged from the frozen README. NEW cases: null (no draw). Routing verdicts
PENDING the seat (no gated_v3 card builder exists at BASE —
`results_w2/tools/build_v2_routing.py` is gated_v2-specific). No bodies/texts were fetched
on this host, so there is no `$W/bodies_v3/` for a follow-on card lane to reuse; that lane
starts at step 2 after the ruling.
