---
workstream: WS:LIVE-ENTRY-RADAR
session: claude/idr-catalyst-live-ship-20261004
model: fable
ended_because: ci_handoff
mission: 'Intraday Dislocation + Reclaim wave 2b (receiver assignment mastermind-terminal#784): let the
  Entry Radar catalyst attach ask the incumbent EDGAR collector at decision time, bounded and opt-in,
  so an episode''s catalyst coverage reflects the owner''s current answer rather than only the nightly
  store — without a second event store, without touching the frozen R1-B cells, and without changing
  any existing live-payload key.'
state_before: 'Wave 2a (#8448, merged) attaches episode.catalyst from the nightly EDGAR store only: a
  filing published after the nightly backfill is invisible until the next night, so the live payload
  can say "no earnings filing in window" for an episode whose filing is already on EDGAR. Neither the
  VPS unit macro-live-entry-radar.service nor the entry-radar-live.yml backstop carried a catalyst
  opt-in. Catalyst clock contract: CatalystSourceRead.usable_at(decision) needs source_asof <=
  observed_at <= decision <= fresh_until and age <= 900 s.'
changed:
- path: engine/entry_radar/catalyst_edgar_live.py
  what: NEW bounded live reader read_edgar_item_202_live(tickers, now, ...) built ONLY from the
    collector''s own _sec_get_json / _extract_8k_rows / SUBMISSIONS_URL. Limits per pass <=48 tickers,
    20 s budget, the collector''s 0.12 s pace; CIK resolved from the tracked store parquet (ticker, cik),
    so a ticker absent from the store is "cik unknown in store" and falls to the store read. Returns
    EdgarLiveRead with per-ticker CatalystSourceRead rows stamped observed_at / fresh_until. Never reads
    os.environ; the default fetch is the module''s ONLY network path and no test exercises it.
- path: engine/entry_radar/live_eval.py
  what: _attach_catalyst gains environ / clock / live_reader / store_reader injection (call sites
    unchanged). ENTRY_RADAR_CATALYST_LIVE=1 enables the live read; decision_at = max(now, last live
    observed_at) so the store read is judged on the same clock; per-row source mode live / store / none;
    health.catalyst gains live_enabled, live receipt (attempted, fetched_ok, budget_exhausted, elapsed_s,
    error, refusals, last_observed_at), source_modes and decision_at. No existing key or value changed.
- path: tests/test_entry_radar_catalyst_attach.py
  what: +12 tests — test_W2B1_* (reader bounds, pace, CIK fallback, refusals) and test_W2B2_*
    (disabled by default, live ok no filing, live blocking filing, mixed live/store, live exception falls
    back to store, decision-clock invariant). Every test injects fetch= / live_reader= / store_reader=.
- path: tests/test_entry_radar_w4_liveness.py
  what: test_EP_catalyst_live_read_is_opt_in_on_real_producer_paths — the two real producers carry the
    opt-in and no other unit, workflow or test path sets it.
- path: app/deploy/macro-live-entry-radar.service
  what: Environment=ENTRY_RADAR_CATALYST_LIVE=1 on the VPS evaluator unit (comment names the DEC).
- path: .github/workflows/entry-radar-live.yml
  what: evaluate step env ENTRY_RADAR_CATALYST_LIVE=1 so the Actions backstop publishes the same
    coverage the VPS does.
- path: agentos/decisions/DEC-ENTRY-RADAR-CATALYST-LIVE-READ-IS-OPT-IN.md
  what: the ruling, its evidence and the rejected alternatives (always-on, a second event store, a
    per-ticker cache deferred as 2b-3 until a measured VPS pass receipt exists).
verified:
- claim: Catalyst attach, catalyst context, Radar lane and liveness suites pass on the ship head
  command: python -m pytest tests/test_entry_radar_catalyst_attach.py tests/test_entry_radar_catalyst_context.py
    tests/test_entry_radar_w4_lane.py tests/test_entry_radar_w4_liveness.py -q
  result: '345 passed in 3.89s at cherry-pick head 62f264626c (ubuntu1 venv macro-idr, python3 -m pytest … -q)'
- claim: Agent OS records validate
  command: python scripts/agentos.py validate
  result: '1520 records — 0 error(s), 101 warning(s) (all review-overdue warnings on older records)'
- claim: No new test file is outside a CI run step
  command: python -c "from scripts.audit_unrun_tests import gated_unrun_suites; print(gated_unrun_suites())"
  result: '[] — no gated unrun suites; the attach suite is already named in .github/ci/legacy-jobs.yml by #8448'
- claim: The live reader resolves CIK from the store, not from the gitignored company_tickers.json that the
    VPS does not have
  command: grep -n "read_parquet(store_p, columns=\[\"ticker\", \"cik\"\])" engine/entry_radar/catalyst_edgar_live.py
  result: 'one hit (line 109 at the lane head 663b0472ce86); data/edgar/company_tickers.json is absent on
    146.190.142.17 (ls, 2026-10-04) and nothing in the reader reads it.'
unverified:
- claim: The VPS evaluator pass stays inside its budget with the live read enabled
  what_would_verify: 'First Monday 2026-10-05 pass after /opt/macro pulls the merge: health.catalyst.live
    elapsed_s <= 20 and the unit''s journal shows no timeout (effective TimeoutStartSec is 570 s via
    drop-ins; the repo file says 120).'
- claim: The live read changes a served coverage verdict on a real episode
  what_would_verify: 'A live payload where health.catalyst.source_modes.live > 0 and at least one
    episode.catalyst.context_state differs from what the store-only read would have produced; compare
    against the parquet spool row for the same pass.'
unresolved:
- 'PRODUCTION_PROOF is Monday 2026-10-05 >= 13:04Z: health.catalyst.live_enabled true, source_modes.live > 0,
  decision_at present in /var/lib/macro-live/public/live/entry_radar.json; systemctl show
  macro-live-entry-radar.service -p Environment carries ENTRY_RADAR_CATALYST_LIVE=1 after /opt/macro pulls.'
- '2b-3 (per-ticker live cache across passes) is DEFERRED until one measured VPS pass receipt shows the
  48-ticker read''s real elapsed_s; see the DEC''s alternatives.'
- 'Terminal wave 2c (mastermind-terminal, /dislocations): the chip must read context_state — "Checked: no
  earnings filing" is not "Catalyst on file"; lands after mastermind-terminal#808 merges.'
next_actions:
- 'Monday 2026-10-05 after 13:04Z: read the live payload once and record health.catalyst (live_enabled,
  source_modes, decision_at, live.elapsed_s) in the WS record as PRODUCTION_PROOF or as the exact defect.'
- 'If live.budget_exhausted is true on a normal pass, raise DEFAULT_MAX_LIVE_TICKERS / the 20 s budget ONLY
  with the measured elapsed_s in the commit message, or ship 2b-3 (cache) instead.'
- 'Terminal wave 2c: implement the frozen catalystLabels spec on master after #808 merges; crops in the PR.'
do_not_redo:
- 'Do not rebuild the EDGAR collector, the catalyst adapters, catalyst_context, the store reader or the native
  episode seam — the live reader is the collector''s own functions behind a bounded pass.'
- 'Do not add a second catalyst / event store or an always-on live read; DEC:ENTRY-RADAR-CATALYST-LIVE-READ-IS-OPT-IN.'
- 'Do not re-register R1-B (60-cell v4 grid) or touch research/species/** or data/trial_ledger.jsonl.'
- 'Do not re-add the tests to .github/ci/legacy-jobs.yml — #8448 already names tests/test_entry_radar_catalyst_attach.py.'
danger_areas:
- 'Coverage is bounded by the store: a ticker with no row in the tracked EDGAR parquet gets "cik unknown in
  store" and never a live read — the backfill (#8392, 2,765 tickers) is the ceiling until the collector widens it.'
- 'Clock: decision_at moves FORWARD to the newest live observed_at; the store read is judged on that clock, so
  a store snapshot older than 900 s on that clock is unusable even when it was usable on wall-clock now.'
- 'The VPS unit''s effective limits come from drop-ins (TimeoutStartSec 570, MemoryMax 1G), not the repo
  file; a live read failing open still costs up to 20 s per pass.'
- 'Pushing .github/workflows/* from ubuntu1 is refused (token lacks workflow scope) — push from the Mac.'
prs:
- 8448
decisions:
- DEC:ENTRY-RADAR-CATALYST-LIVE-READ-IS-OPT-IN
---

Wave 2b of Intraday Dislocation + Reclaim. Rung reached at the time of writing: CI (ship PR open).
PRODUCTION_PROOF and ACCEPTANCE are listed under unresolved with the exact readback that closes each.
