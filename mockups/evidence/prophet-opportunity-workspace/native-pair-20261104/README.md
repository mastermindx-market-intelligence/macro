# Native Prophet publication pair — coherent 2026-11-03 board + gate, regenerated consumers

Source head of this record: `e5c288011f026cb74b2a2e265d6dfc767359565d` — the exact
remote head of PR #9495 branch `claude/ssd-prophet-opportunity-system-20261015-5ba805642dd9aece`
at the start of this work. The worktree used was an isolated `git worktree` of the
local macro clone; no occupied checkout, no other session's Git state, and no
Paper/Fabric carrier was touched.

## What was wrong, and what this record fixes

At that head the committed pair was incoherent. `site/factordata/us_standouts.json`
carried `as_of 2026-11-02` with `emit.pair_id 87b4097a82f849b9807c0e099ab10cc7`
(written `2026-11-04T07:36:26+00:00`), while `site/factordata/signal_gate.json`
carried `as_of 2026-11-03` with `emit.pair_id 64e1656a94da49a19f5bee73ca39745c`
(written `2026-11-04T07:03:05+00:00`). Two different writer runs, so
`scripts/check_signal_gate_coherence.py` reported **103 mismatching tickers**.
The branch's own ancestry contains the coherent Nov 3 pair from run `64e1656a`
(commit `1e35243749b4`, `engine-render: … 2026-11-04 (scope=all)`); a later branch
commit replaced the board half with the Nov 2 one and the pair split.

This record adopts a **coherent pair produced by one build snapshot** and
regenerates the actual native publication consumers from it. Nothing was
hand-stamped, no stale output was copied, and no test or assertion was disabled.

## The pair — one writer run, one date

| artifact | sha256 | bytes | as_of | emit.pair_id |
|---|---|---|---|---|
| `site/factordata/us_standouts.json` | `e655802dbb50851d726120ac7db48886a6d36d3a0f6d59ff68a99ddb40d6f792` | 2025921 | 2026-11-03 | `a941b520be05487291def2f9b4acb488` |
| `site/factordata/signal_gate.json` | `8acc0a3d273aa6e2cd22964943c7e7b8cbe28f58eccee3d7defddc4c4cbcd9f1` | 455044 | 2026-11-03 | `a941b520be05487291def2f9b4acb488` |

Both files carry the **same `emit.pair_id` and the same `at_utc`** — the lineage
stamp `scripts/build_stock_library.py::_PAIR_EMIT_STAMP` writes once per writer
PROCESS — so the pair is one run's output, not two files copied together.
`scripts/check_signal_gate_coherence.py` exits 0 with **zero** mismatching
tickers, and `scripts/check_board_contradictions.py` passes all five board
invariants.

The pair was produced by the repository's own builder inside the accepted
four-module native build (below). It is Nov 3, so the gate freshness was not
rolled back, and its `eligible` count is 159 — the same generation the accepted
`main` board (`a3b04cc31fd1d29cca84c68b49712bd6192dd153ddbe7ce37ff8ff3194105322`,
also `as_of 2026-11-03`, `eligible 159`) carries. The host's committed stores
reach the 2026-11-03 session (`data/breadth/_closes_cache.parquet` max date
2026-11-03), so this host can build the current generation natively; it does not
have to import one.

## The build that produced it

`mockups/evidence/prophet-opportunity-workspace/full-page-20261103/tools/build_native_prophet.py`
— the repo's own accepted driver, run with `RENDER_NO_DRIP=1`, `MACRO_DUMP_VM=1`
and `DEEPSEEK_API_KEY` removed. `build.json` is its receipt.

| module | exit | seconds |
|---|---|---|
| `scripts.build_site` | 0 | 876.57 |
| `scripts.inject_data_base` | 0 | 6.09 |
| `scripts.externalize_css` | 0 | 7.40 |
| `scripts.optimize_assets` | 0 | 26.47 |

`scripts.build_prophet --date 2026-11-04` then regenerated the index/Plan consumer
(`site/prophet/index.json`, `site/prophet/plans/*.json`, `site/prophet/states/*.json`,
`site/prophet/board_read_sparks.json`) and the source-bound snapshot. It advanced
the append-only forward ledger by three closed-plan rows and wrote the arena
scoreboard. It reported **no ThetaData store on this host**, so option
recommendations were skipped for new plans — an optional enrichment, recorded
here rather than hidden.

## The regenerated consumers

| consumer | sha256 | bytes |
|---|---|---|
| `site/us_stocks.html` (public) | `222bd3a37a3c4b98d3a5076155e77f643b3e8bc924df80740f93418c3dcf6070` | 793059 |
| `site/premiumdata/us_stocks.json` (protected Essential) | `b98f14fd1a1ccd68341b24e5d67c33d17cf800f64b9f774bc07f6cc588dd4d8d` | 9485252 |
| `site/prophet/index.json` (index/Plan consumer) | see `pair-provenance.json` | — |

The index is **source-bound to this exact board**: `source_board_sha256` is
`e655802d…`, and the content-addressed snapshot
`data/prophet/origination_sources/e655802d….json.gz` decompresses to bytes whose
sha256 is `e655802d…` — the board file itself. `index.asof` is the run date
(2026-11-04) and `index.source_board_asof` is the board date (2026-11-03),
matching the shape of the accepted `main` index.

## The twelve publication-pair checks

`publication-pair.json` is the receipt produced by
`full-page-20261103/tools/verify_native_pair.py`, which ends with
`PUBLICATION_PAIR_VERIFIED`. All twelve checks are `true`:
`pool_membership`, `pool_no_duplicates`, `pool_disjoint`,
`pool_public_subsequence`, `pool_protected_subsequence`, `pool_source_identity`,
`screener_preview_order`, `screener_protected_order`, `today_entitled_order`,
`plan_targets_resolve`, `public_has_no_protected_plan_controls`,
`today_raw_source_binding`.

The entitlement counts are **derived from this source, not carried over**:

- eligible pool: **159 total = 3 public + 156 protected** (public source positions
  0, 7, 9). The previously published 212/209 split belonged to the superseded
  Nov 2 board and is not reused.
- protected Plan targets: **43**, missing **0**.
- screener: 3 preview / 48 protected / 51 total. Today: 0 public articles,
  6 entitled preview, 12 featured total.

## Protected / public separation, measured on the bytes

- public pool rows `PWR, HUBG, MC`; protected pool rows 156; **disjoint**.
- public screener cards `PWR, CMG, CVNA`; protected screener cards 48;
  **disjoint**.
- **no** protected card block appears verbatim anywhere in the public root HTML.
- **zero** `[data-pvs-plan-target]` controls in the public HTML.

## Anonymous, offline rendering — 16 cells

`render/observations.json` plus 16 full-page PNGs. The generated public HTML is
served unchanged; the protected payload is **not** served (no `premiumdata/`, no
`us_stocks.json` in the served root) and every `/premiumdata/` request is aborted,
as is every non-loopback request. Theme and locale are real browser context
settings.

Widths 1440 / 768 / 390 / 320 × light / dark × en / zh. In **every** cell:
`overflow = 0`, `page_errors = 0`, `protectedControls = 0`. The blocked-request
set is exactly the protected payload plus one R2 asset URL, and the offline 404
set is the same live-only endpoint set the prior accepted capture recorded at
`full-page-20261103/verification/native-381bb7-pre-assistant-20261103`.

### One visible consequence of this board generation, stated plainly

The anonymous public **Featured shelf is empty on this board**: the page shows
`TODAY 0 of 12 Featured` and the honest empty state *"Featured setups are outside
your current access."* / *"精选形态尚未包含在当前访问权限内。"*.

This is the designed entitlement path, not a build defect and not a leak. On the
Nov 3 board the first Featured row sits at `buy[]` index **3**, and the public
shell publishes the first **3** rows — so no Featured name falls inside the public
preview, and `templates/dashboard.html.j2` takes its own `{%- elif _today_total > 0 %}`
branch. The board still declares 12 Featured names, the protected payload carries
the 6 entitled Today cards, and the guard `today_entitled_order` proves the
protected order matches the entitled preview. On the previous Nov 2 board the
first Featured row was at index 0, so one Featured card was publicly visible;
the public article count is a property of the board, not a constant. The prior
accepted builds recorded 2 and 1 public articles for the same reason.

## The Save fixture — what is superseded and what is not

The existing `save-visual-20261104-fabric` receipt is **preserved byte-for-byte**.
Seven of the nine sources it records are still byte-identical to the committed
files:

`templates/prophet_save.css`, `templates/prophet_save.js`,
`site/prophet_save.css`, `site/prophet_save.js`, `site/watchstore.js`,
`site/theme.js`, `site/basketdata/action_board.json` — all unchanged. The Save
presentation and interaction contract the fixture proves is therefore untouched
by this publication.

Two of its recorded **data-context** bindings are superseded, because this
publication replaces the board and the index it was captured against:

| path | recorded sha256 | now |
|---|---|---|
| `site/factordata/us_standouts.json` | `bc0c02f8…` | `e655802d…` |
| `site/prophet/index.json` | `22272683…` | `7d305181…` |

**No new version of the Save fixture is produced here, and none is claimed.** The
fixture's own anchor is the public Featured card (`#us-today-grid .pvcard`); its
renderer refuses to proceed without `#us-standouts`, `#us-today` **and**
`#us-today-grid`, and this board generation publishes no Featured card. The three
public screener cards do carry a setup body, but they carry **no Save control**,
so re-anchoring on one would capture a different surface and prove nothing about
Save. The honest statement is the one above: the contract sources are unchanged,
the two data-context bindings moved, and a fresh Save capture needs a board
generation that publishes a Featured card.

## Test status — the pre-existing red is not this change's

A focused run (11 suites, 642 passed, 22 skipped) showed **9 failures**. The
identical 9 failures reproduce on a **pristine worktree at the same head
`e5c288011f02`** with none of this change applied — they are pre-existing at the
PR head and are not in this delta's scope:

- `tests/test_prophet_w1_intake_repair.py::TestIndexHygieneEndToEnd` — 4 cases
  (`test_every_shipped_plan_carries_an_age_and_a_pulse`,
  `test_a_ledger_closed_plan_is_flagged_and_pulses_as_closed`,
  `test_open_count_and_the_age_buckets_stay_coherent`,
  `test_open_count_equals_active_count_when_the_ledger_is_empty`)
- `tests/test_us_board_priority_ui.py` — 5 cases, all asserting the older
  "Higher Priority means the setup is more ready today" footnote copy

A second pre-existing failure, outside the focused set, is
`tests/test_site_shim.py::test_every_committed_site_page_has_shim` (it names
`site/market_memory.html`). It fails identically on the pristine baseline
worktree, and `site/market_memory.html` is **not** touched by this change.

No test was disabled, weakened or skipped to obtain a green result.

## Local verification actually run

| check | result |
|---|---|
| `scripts/check_signal_gate_coherence.py` (both artifacts) | exit 0, 0 mismatching tickers |
| `scripts/check_board_contradictions.py site/factordata/us_standouts.json` | exit 0, 5 invariants pass |
| `scripts/check_validated_claims.py` | exit 0 |
| `verify_native_pair.py` (the twelve publication-pair checks) | `PUBLICATION_PAIR_VERIFIED` |
| `pytest tests/test_signal_gate_coherence.py tests/test_signal_gate_validity_contract.py` (the `signal-gate-pair-coherence` pack step) | 59 passed |
| `scripts/check_template_site_sync.py` | OK, 161 pairs checked |
| `scripts/check_design_system.py --mode enforce-added --diff-file <templates diff>` | 0 blocking findings |
| `scripts/check_ui_visual_evidence.py --diff-file <templates+site diff>` | exit 0, no finding |
| `scripts/check_runtime_style_injection.py` | OK (277 .js scanned) |
| `scripts/check_design_system.py --self-check` | OK |
| `scripts/check_p0b_receipt_closure.py --diff-file <changed paths>` | exit 0 |
| `scripts/run_ci_pack.py --plan-only` / `--validate-only` (packs 0 and 1) | 384 legacy jobs validated |
| `pytest` design-governance suites | 220 passed |
| `pytest` template-site-sync / asset-stamp / externalize-css / site-shim suites | 234 passed, 1 pre-existing failure |
| `pytest` the 11 focused suites | 642 passed, 22 skipped, 9 pre-existing failures |

The two diff-gated CI packs this change triggers are `board-contradictions`
(pack 0) and `signal-gate-pair-coherence` (pack 1); both were executed here as
the workflow defines them.

## Hosted CI on this exact head

`ci-authority` run **41900174608** on head `f10a9e0fc7a515f658fadec6203eccacb0ccaffc`
concluded **success**: `ci-authority` success, `ci-authority/main` success,
`ci-authority/codex/merge-queue-pilot` failure. That pilot job is the known
pre-existing failure on every macro pull request — it also failed on this
branch's own earlier heads (runs 41887383343 at `e5c28801` and 41865069481 at
`22abd622`), so it is not caused by this change.

**This is not full hosted PR/fences proof.** The pack-level `ci` and `fences`
workflows produced **no run** for this head. On this branch they last ran at
head `464152a0` (run `ci` 41804161703, `fences` 41804161294), before the pull
request was converted to draft at 15:23:28Z; every push since then, including
this one, has produced only `ci-authority`. The trigger condition for the
pack-level lanes on a draft pull request is not established from here, and the
only ways to exercise it — un-drafting the pull request, or an owner CI
dispatch — are outside this assignment's authority.

## What this is not

It is not an authenticated, entitled, signed-in, Paper, production or live
acceptance; it is not a merge, release, deploy, Ready/un-draft, label, enqueue or
purchase; and it does not infer or activate trade entry availability, signal
activation, sizing, or any account/portfolio write. No deploy, publisher or R2
publication was invoked — `scripts.build_prophet --publish` is disabled by the
builder itself and was not used.

## Files in this record

- `build.json` — the four-module native build receipt (head, modules, artifacts).
- `publication-pair.json` — the twelve publication-pair checks.
- `pair-provenance.json` — every number above, re-derived from the workspace by
  `tools/build_pair_provenance.py` (re-runnable; nothing typed by hand).
- `render/observations.json` + 16 PNGs — the anonymous offline rendering record.
- `tools/capture_native_pair_page.py` — the capture runner.
- `tools/build_pair_provenance.py` — the provenance deriver.

## Reproduce

```bash
python3 mockups/evidence/prophet-opportunity-workspace/full-page-20261103/tools/build_native_prophet.py \
  --workspace <isolated-worktree> --source-head <head> --log <log> --receipt <receipt>
python3 -m scripts.build_prophet --date 2026-11-04
python3 scripts/check_signal_gate_coherence.py
python3 scripts/check_board_contradictions.py site/factordata/us_standouts.json
python3 mockups/evidence/prophet-opportunity-workspace/full-page-20261103/tools/verify_native_pair.py \
  --workspace <isolated-worktree> --source-head <head> --output publication-pair.json
python3 mockups/evidence/prophet-opportunity-workspace/native-pair-20261104/tools/build_pair_provenance.py \
  --workspace <isolated-worktree> --source-head <head> --build-receipt build.json \
  --publication-pair publication-pair.json --render render/observations.json --output pair-provenance.json
```
