---
workstream: WS:LIVE-ENTRY-RADAR
session: claude/idr-ledger-terminal-wins-20261005
model: fable
ended_because: ci_handoff
discoveries: ["DSC:PACK-LANE-MERGE-LAST-WINS-KEPT-REPLAYED-CANDIDATES-OVER-RESOLVED"]
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
    Docstring records the measured production failure.
- path: tests/test_entry_radar_w4_ledger.py
  what: >
    Five LED2 cases — positive control that a re-stamped replay IS a differing canonical (emits the
    CANDIDATE row), terminal-row precedence in both merge orders followed by commit → RESOLVED,
    last-wins mutation control between two non-terminal rows, and the pack-lane order end to end
    (overlay first, replay second, one merge, one commit → RESOLVED; next replay superseded).
verified:
- claim: the new cases pin the defect, not the wording
  command: "python3 one-off: import engine.entry_radar.live_ledger as ll; ll._row_terminal = lambda row: False; then pytest.main on tests/test_entry_radar_w4_ledger.py -k 'outranks or end_to_end or last_wins_between'"
  result: 2 failed (overlay-first precedence, pack-lane end-to-end), 2 passed (replay-first passes by accident under last-wins; mutation control unchanged)
- claim: ledger, pack and PIT suites green with the fix
  command: python3 -m pytest tests/test_entry_radar_w4_ledger.py tests/test_entry_radar_w4_pack.py tests/test_entry_radar_w4_pit.py -q
  result: 80 passed + 125 passed (sparse tree; these suites use tmp_path only)
- claim: apply_session_clocks is called only by the daily pack lane, never by the RTH live lane
  command: grep -rn 'apply_session_clocks' engine/ scripts/
  result: one caller, scripts/entry_radar_live_pack.py:569
- claim: the re-arm blocks commit opens for the 2,420 C5 units when the backlog resolves are inert
  command: grep -n 'arm_allowed' engine/entry_radar/*.py scripts/entry_radar_live_pack.py
  result: consulted only at engine/entry_radar/live_eval.py:2061 (C1/C3 path) and :2099 (C2); never in the pack lane or c5_adapter.py
unverified:
- claim: the production backlog self-heals on the first pack build after the merge
  what_would_verify: >
    read-only VPS readback after the 2026-10-06 ~10:20Z pack build — episodes_count in
    /var/lib/macro-live/public/live/entry_radar.json small (non-terminal + current/previous session
    terminals), episodes.json far below 90 MB with ~44.9k rows moved into episodes_archive_*.json,
    and the macro-live-entry-radar pass duration well under 5 minutes in the journal.
- claim: no other writer re-creates the stale CANDIDATE rows
  what_would_verify: the same readback showing no CANDIDATE row with candidate_at older than as_of minus 10 sessions
unresolved:
- The first post-fix pack build will emit ~44.9k RESOLVED rows and open ~2,420 C5-keyed re-arm
  blocks in one commit; the journal entry for that build will be large once. It is a one-time cost.
- The Terminal route still sorts the full served list before slicing to 20; that is fine once the
  payload is small again and is not changed here (DEC:ENTRY-RADAR-EPISODES-ARE-ADDITIVE-IN-THE-LIVE-PAYLOAD).
next_actions:
- Merge this PR on concluded-green via the merge-on-green sweeper; verify landed with `git fetch
  origin` then a per-path blob comparison against origin/main.
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
  tested (LED2 end-to-end).
- Do not re-register R1-B, re-open #812, or re-arm #8448/#8457; #7274 stays PARKED/HOLD-FOR-SOL.
danger_areas:
- merge_deltas is the ONLY place the overlay and the replays meet; any new producer of terminal rows
  must keep the terminal-wins rule, and any new consumer of merged deltas must not assume last-wins.
- A sparse worktree omits data/ and site/; the Radar suites use tmp_path only, but never run the full
  suite in a sparse tree.
- arm_allowed is unconsulted on the C5 path by construction; if C5 ever gains re-arm gating, the
  ~2,420 blocks the backlog drain opens become live and must be reviewed first.
---

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION
MISSION_COMPLETE: false

This is a durable save for one repair inside the larger Intraday Dislocation + Reclaim program;
the program continues on the Terminal queue and W3 acceptance.
