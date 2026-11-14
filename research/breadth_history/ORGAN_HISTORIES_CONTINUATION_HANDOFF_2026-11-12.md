# Continuation handoff — organ alert histories (COO ruling 38, Part A)

Date: 2026-11-12 · Author: bounded Claude implementation seat · Status: **DRAFT delivered, awaiting commissioning-authority review/merge**

This record exists so the work survives a context clear, crash or operator handoff
(standing context-economy WRITE rule). It is a description of work, not an outcome:
the draft is **not** merged, approved, labelled, armed, deployed or production-proven.

## Mission and authority

- Brief: `/tmp/qb/r38_partA_brief.md`; census `/tmp/si_plan/quant/ORGAN_CENSUS.md`;
  ruling §2/§2d of `/tmp/si_plan/deputy/RULING_38_organ_histories_and_group_indexes.md`.
- Scope: engine alert histories for **three HOUSE organs only** —
  `us_basket` washout (`WASHED_OUT → CONFIRMED`, two labelled membership versions
  `dated` + `current` in one file), rolling-over override (11 SPDR sectors),
  `phase_v2` (11 SPDR sectors). **`turn_down` is out of scope** (vendor-keyed; no
  file/name/test of it here).
- Terminal deliverable per brief: **"Open a draft only. Never merge, approve, label
  or arm."** Merge/CI/render/deploy/live-verification belong to the commissioning
  deputy/COO, not this bounded seat.

## Deliverable (verified)

- Draft PR: https://github.com/mastermindx-market-intelligence/macro/pull/11174
  (`isDraft: true`).
- Branch: `claude/ssd-quant-organ-histories` · head `1ab1a0bf2ae2ab7b7d8f07f823dd8e7afe027993`.
- **Stacked base:** `claude/ssd-quant-regime-inputs` (NOT `main`). Path to `main`
  runs through the regime-inputs PR first; this draft cannot merge to `main`
  directly until that base lands and the draft is retargeted/advanced by its owner.
- BASE_HEAD: `1c22905b3e7e7b9ac6f28ec15dcd5b157e5440a1`.
- Exactly five files in the head commit:
  1. `scripts/build_organ_histories.py` (667 lines) — thin replay wrappers; imports
     and calls the engine's own code, no copied threshold/rule, `engine/` untouched.
  2. `data/breadth/history/organ_histories_house.parquet` — 2,254,378 bytes,
     sha256 `dbf36d7b82725fd68a63fc62d8452db7f103c903226fa6f86db694e8b26f216a`.
  3. `data/breadth/history/organ_histories_house.meta.json` (11,421 lines) — full
     fidelity + every mismatch + first-knowable by organ/key.
  4. `research/breadth_history/ORGAN_HISTORIES_REPORT.md` (1,617 lines) — one-page
     table + every mismatch by key/date.
  5. `tests/test_build_tree_breadth_and_index.py` (+186 lines, the only test file
     changed) — five organ tests, `skipif`-on-missing-data per file convention.

## Engine pin and provenance

- `engine_code_sha = 72082493cb5e29cf5fe4a093fadf6f435b6fe2c3` on every row; the six
  engine modules are sha256-verified at build start.
- Prices: **restated** as of capture (latest committed tape), `price_basis: "restated"`.
  2000-bar trailing cap = `scripts/backfill_forward_logs.py:85` (PIT-equivalent for
  signal fields). `state` holds only the engine's own output; nothing relates to
  outcomes; no new state/label/threshold of ours.
- Group-level rows only: no member ticker, price or per-security date. Sector keys
  are the 11 SPDR ids (`n_members=1`); basket keys are basket ids.
- `data/breadth/history/internal_only` empty in git (public repo; no vendor data).

## Fidelity baseline (replay vs live stores; every mismatch enumerated)

| organ | comparison | match/total | mismatch | mismatch-detail sha256 |
|---|---|---|---|---|
| `us_basket` (dated) | vs `ledger.jsonl` | 1803/1911 | 108 | `f294e536e376992592d40e26853b94b473897d6ffecf6dfcfe192c584d485507` |
| `phase_v2` | vs `backfill.parquet` (month-end) | 652/1881 | 1229 | `7bd59797d33dee41e66916c27338212525d7764e03e5635dff5f68233f77ace8` |
| `phase_v2` | vs `forward_log.parquet` (daily) | 601/858 | 257 | `61a9f9e6818960af3031a1dbdc332b45c0f8a0d9b132b2a407ddb18599812a3a` |
| `rolling_over` | vs live engine (latest 10 sessions) | 110/110 | 0 | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |

**The replay is faithful to the live engine:** on the latest 10 sessions both
`phase_v2` and `rolling_over` match `sector_cycles.compute(asof)` **110/110**
(basis `price` throughout). The store mismatches are therefore *not* a wrapper
defect — they are restated-price **vintage** effects (stores built at earlier
captures; replay uses the latest tape) plus a **calendar-vs-trading date convention**
(stores stamp month-end/nightly run dates incl. weekends, e.g. Sun 2026-07-05, which
a daily trading-session replay does not emit → `missing_in_replay`). Reported, never
tuned (brief; ruling 38 §2d). Tests pin counts **and** the full mismatch-detail sha256
as a "no new mismatch" regression baseline.

## Boundaries honored

- Frozen files keep their bytes: `regime_inputs_daily_current.parquet`
  (`c15d5c2d533ae7d66dd84a67c8c1abfa19457aa44fcd1e8504d00bc0c9348177`) and
  `regime_inputs_current.meta.json`
  (`552260044b01a67b6a5aed0a30dee52db634c77dd100fb7726d5f282cf0f634d`), and every
  other existing file under `data/breadth/history/`, verified unchanged at HEAD
  (23 files = 21 original + 2 new). New files only.
- `engine/`, `.github/`, `lib/` untouched. No production builder run, no nightly;
  reads engine stores, never writes them.
- Materialised pin-price build inputs (`data/baskets/ohlcv`, `data/stocks`,
  `data/yahoo`) were restored to HEAD bytes after build+tests so the working tree is
  clean and no member price enters git (brief bars member prices). The rolling-over
  test carries a pin-price sentinel (`_PIN_SPY_SHA256
  37bad67655facda3cb3b171f34dde36471b975bcfdf16f438f33a66bf5368eb5`) and skips when the
  panel is absent/restored (sparse CI / post-build cleanup).

## Tests

Five organ tests in `tests/test_build_tree_breadth_and_index.py`:
schema/provenance, `us_basket` vs ledger, `phase_v2` vs stores, rolling-over vs live
engine, sidecar consistency. On the pin basis: 4 pass + 1 sentinel-skip after input
restore. The regime `_FORBIDDEN` regex (bans the word "state") is regime-only and does
NOT apply to organ files, which legitimately carry the engine's `state` output.

## Next actions for the commissioning owner (NOT this seat)

1. Adversarial review of the draft (session-owned review law; independent native
   reviewer if distinct scrutiny is owed).
2. Advance the regime-inputs base PR through its own gates to `main`.
3. Retarget/advance this draft, convert to Ready when qualified, meet real
   review/hold gates, use the existing protected publisher when eligible.
4. Verify exact merge + consumer proof; CI → render/deploy → live verification on
   www.mastermind-x.com (committed main; github.io mirror is stale).

## Open friction (administrative, not a deliverable defect)

The generic ship-loop Stop hook demands a merged `main` PR keyed on the local branch.
That is structurally unsatisfiable within this commission: the brief bars merge and
the draft is stacked on the regime-inputs base. The merge wait is owned by the
commissioning deputy/COO and has been handed back via the seat return. This seat does
not merge, approve, label, arm, convert-to-Ready or poll the CI queue.