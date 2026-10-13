---
workstream: WS:LIVE-ENTRY-RADAR
session: claude/idr-ledger-terminal-wins-20261005
model: fable
ended_because: ci_handoff
discoveries:
  - "DSC:PACK-LANE-MERGE-LAST-WINS-KEPT-REPLAYED-CANDIDATES-OVER-RESOLVED"
  - "DSC:ARCHIVED-EPISODES-ARE-UNKNOWN-TO-APPLY-RUN-SO-A-FULL-HISTORY-REPLAY-RESURRECTS-THEM"
decisions: ["DEC:ENTRY-RADAR-EPISODES-ARE-ADDITIVE-IN-THE-LIVE-PAYLOAD"]
mission: >
  Fable CEO seat for Intraday Dislocation + Reclaim (Chairman handoff on mastermind-terminal issue
  784). This record covers the live-ledger repair found while proving the Terminal screen's real data
  path: the daily pack lane kept every historical C5 candidate non-terminal forever, so the served
  payload carried 44,972 episodes and the live passes ran 4.8 minutes on a 5-minute cadence.
state_before: >
  Production ledger /var/lib/macro-live/state/entry_radar/episodes.json at 90,115,323 B with 45,234
  episodes (44,972 CANDIDATE back to 1965-01-07, 262 RESOLVED from the 2026-08 RTH lane), 138,917
  transitions (45,223 of them →RESOLVED), last_session 2026-10-02; served entry_radar.json 33.6 MB
  with episodes_count 44,972 while health.state was out_of_window. merge_deltas merged episode rows
  last-wins. The Terminal route's top-20 rows were legitimately recent 2026-10-01/02 candidates, so
  the harm was payload size, parse cost and the nonsense count, not wrong rows.
changed:
- path: engine/entry_radar/live_ledger.py
  what: >
    merge_deltas is TERMINAL-WINS for one episode_id — a stored terminal row (RESOLVED/EXPIRED/
    INVALIDATED) never loses a merge to a replayed non-terminal trace; two non-terminal rows still
    merge last-wins. New helper _row_terminal reads a raw row's state against dt.TERMINAL_STATES.
    Docstring records the measured production failure. SAME DAY, SAME PR (folded before merge):
    an ADMISSION HORIZON — apply_run refuses a trace whose market_session is more than
    HISTORICAL_TRACE_SESSIONS (= COMPACTION_SESSIONS = 40) before the as_of, with its transitions,
    and reports it on the new PendingDelta.historical (episode_id, ticker, detector_id, variant,
    state, market_session); merge_deltas unions those rows by id; compact() now also archives
    transitions older than the window into the month file under "transitions" (idempotent, nothing
    lost) and returns archived_transitions. New _SessionCut helper (one searchsorted per cut).
- path: scripts/entry_radar_live_pack.py
  what: the pack delta line prints "N historical trace(s) refused" beside the superseded count.
- path: tests/test_entry_radar_w4_pit.py
  what: >
    W4R-M8 clamped-window case reads the §10 expiry proof off result.delta.historical when the
    replayed C3 episode is older than the horizon (it was minted at 2026-05-29, 54 sessions before
    the pass) — the clock still runs; the row is refused as history, state and all.
- path: tests/test_entry_radar_w4_ledger.py
  what: >
    LED8 C5 cases now aim as_of at the session after the fixture's newest candidate (c5_window_as_of)
    so the youngest candidates sit inside the horizon and the 2000–2022 ones are reported refused;
    new LED2 horizon cases (refused beyond, admitted at the edge, merge carries refusals, drained→
    archived→replayed is NOT resurrected with an inline positive control) and a LED7 transitions
    compaction case. Five LED2 cases — positive control that a re-stamped replay IS a differing canonical (emits the
    CANDIDATE row), terminal-row precedence in both merge orders followed by commit → RESOLVED,
    last-wins mutation control between two non-terminal rows, and the pack-lane order end to end
    (overlay first, replay second, one merge, one commit → RESOLVED; next replay superseded).
verified:
- claim: the new cases pin the defect, not the wording
  command: "python3 one-off: import engine.entry_radar.live_ledger as ll; ll._row_terminal = lambda row: False; then pytest.main on tests/test_entry_radar_w4_ledger.py -k 'outranks or end_to_end or last_wins_between'"
  result: 2 failed (overlay-first precedence, pack-lane end-to-end), 2 passed (replay-first passes by accident under last-wins; mutation control unchanged)
- claim: ledger, pack and PIT suites green with both fixes
  command: python3 -m pytest tests/test_entry_radar_w4_ledger.py tests/test_entry_radar_w4_pack.py tests/test_entry_radar_w4_pit.py -q
  result: 210 passed (sparse tree; these suites use tmp_path only)
- claim: the whole Radar CI step is green on the folded tree
  command: the 42-suite pytest line at .github/ci/legacy-jobs.yml:1204 run with python3
  result: 2029 passed in 135.92s
- claim: the horizon cases pin the resurrection, not the wording
  command: "python3 one-off: ll._SessionCut.beyond = lambda self, earlier, n: False; pytest.main on tests/test_entry_radar_w4_ledger.py -k 'horizon or refused or resurrected or carries_historical or c5_candidates or knowability_clock or lane_is_idempotent'"
  result: 6 failed, 6 passed (the refused/resurrected/LED8 cases fail; the edge-admitted and last-wins cases are independent of the cut)
- claim: the horizon keeps the production ledger small without losing live rows
  command: "python3 one-off over the production episodes.json copy: count rows whose market_session is within N sessions of 2026-10-06 via ll._SessionCut"
  result: 519 of 45,234 within 40 sessions, 1,013 within 100, 1,944 within 200; detector mix C5 44,979 / C2 188 / C1 66 / C3 1
- claim: the ci-pack-2 red on this PR's first run was main's, not this head's
  command: gh api repos/mastermindx-market-intelligence/macro/actions/jobs/111798112209/logs, then git log b32bb2f6f1c..origin/main -- tests/test_agentos_status.py
  result: the only failure was tests/test_agentos_status.py::test_readiness_states_explain_graph_and_authored_progress; PR #8493 "heal main's ci-pack-2 readiness exemplar" landed on main at 601f87f3992; after merging origin/main into the branch the case passes locally
- claim: apply_session_clocks is called only by the daily pack lane, never by the RTH live lane
  command: grep -rn 'apply_session_clocks' engine/ scripts/
  result: one caller, scripts/entry_radar_live_pack.py:569
- claim: the re-arm blocks commit opens for the 2,420 C5 units when the backlog resolves are inert
  command: grep -n 'arm_allowed' engine/entry_radar/*.py scripts/entry_radar_live_pack.py
  result: consulted only at engine/entry_radar/live_eval.py:2061 (C1/C3 path) and :2099 (C2); never in the pack lane or c5_adapter.py
unverified:
- claim: the production backlog drains on the first pack build after the merge and STAYS drained
  what_would_verify: >
    read-only VPS readback after the 2026-10-06 ~10:20Z pack build — the pack journal's delta line
    reading tens of thousands of "historical trace(s) refused", episodes_count in
    /var/lib/macro-live/public/live/entry_radar.json in the hundreds, episodes.json far below 90 MB
    with the resolved rows and their transitions in episodes_archive_*.json, the
    macro-live-entry-radar pass back to ~30 s in the journal and RTH passes publishing; then the
    2026-10-07 build showing no rebound (the oscillation falsifier).
- claim: no other writer re-creates the stale CANDIDATE rows
  what_would_verify: the same readback showing no CANDIDATE row with candidate_at older than as_of minus 10 sessions
- claim: the 2026-10-05 RTH outage ends with the first drained build
  what_would_verify: >
    journalctl -u macro-live-entry-radar showing no "Start operation timed out" after the build; the
    unit's 9.5-minute start timeout killed the 13:34:07Z, 13:43:38Z and later RTH passes because the
    45k-row ledger load/save plus per-episode payload work no longer fit on the 2-core VPS.
unresolved:
- The first post-fix pack build will emit ~44.9k RESOLVED rows and open ~2,420 C5-keyed re-arm
  blocks in one commit; the journal entry for that build will be large once. It is a one-time cost.
- The Terminal route still sorts the full served list before slicing to 20; that is fine once the
  payload is small again and is not changed here (DEC:ENTRY-RADAR-EPISODES-ARE-ADDITIVE-IN-THE-LIVE-PAYLOAD).
next_actions:
- Merge this PR on concluded-green via the merge-on-green sweeper; verify landed with `git fetch
  origin` then a per-path blob comparison against origin/main. No manual VPS intervention before the
  scheduled build — a forced rebuild during RTH races the live lane's unconditional ledger.save()
  (the pack takes no lock) and risks OOM beside the 680 MB live pass on a 3.9 GB box.
- Only if the 2026-10-06 build reports "already current" (no fresh slice) or fails to drain, consider
  ONE pre-open forced rebuild (scripts.entry_radar_live_pack --force) with the save race in mind.
- After the 2026-10-06 pack build (timer next fire ~10:20Z), do the read-only VPS readback above and
  record PRODUCTION_PROOF on the terminal#784 checkpoint; never systemctl start the pack or live
  units by hand and never edit state files on the VPS.
- Resume the Terminal queue (#827 T-CHART-2c, #829 T-CHART-2b) and the W3 G8 real-path acceptance.
do_not_redo:
- Do not cap or filter the served episodes list in the Terminal or the publisher as a "fix" — the
  precedence bug is the cause and it is now closed in merge_deltas.
- Do not hand-edit, truncate or delete episodes.json / episodes_archive_*.json on the VPS, and do not
  restart or re-dispatch production units; the normal pack build drains the backlog.
- Do not make apply_run skip episodes the ledger already holds — the superseded path is correct and
  tested (LED2 end-to-end). The horizon refuses by AGE, never by presence.
- Do not raise HISTORICAL_TRACE_SESSIONS above COMPACTION_SESSIONS, and do not make apply_run read the
  archives to "remember" history — the invariant is horizon == compaction window.
- Do not re-register R1-B, re-open #812, or re-arm #8448/#8457; #7274 stays PARKED/HOLD-FOR-SOL.
danger_areas:
- merge_deltas is the ONLY place the overlay and the replays meet; any new producer of terminal rows
  must keep the terminal-wins rule, and any new consumer of merged deltas must not assume last-wins.
- A sparse worktree omits data/ and site/; the Radar suites use tmp_path only, but never run the full
  suite in a sparse tree.
- arm_allowed is unconsulted on the C5 path by construction; if C5 ever gains re-arm gating, the
  ~2,420 blocks the backlog drain opens become live and must be reviewed first.
- The live lane's C3 replay window (60 sessions of warm-up, clamped to the 180-session reader bound)
  mints rows older than the horizon; they are terminal by construction and are refused as history.
  A test that wants to observe a replayed terminal row older than 40 sessions must read
  PassResult.delta.historical, not the ledger.
- PendingDelta.historical can hold ~47k rows per pack build in memory; it is never persisted (the
  delta dict is not spooled) — keep it that way.
---

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION
MISSION_COMPLETE: false

This is a durable save for one repair inside the larger Intraday Dislocation + Reclaim program;
the program continues on the Terminal queue and W3 acceptance.
