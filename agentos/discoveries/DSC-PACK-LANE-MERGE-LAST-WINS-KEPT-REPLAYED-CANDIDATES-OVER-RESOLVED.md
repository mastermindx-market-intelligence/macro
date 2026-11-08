---
key: PACK-LANE-MERGE-LAST-WINS-KEPT-REPLAYED-CANDIDATES-OVER-RESOLVED
claim: >
  Until 2026-10-05 `engine/entry_radar/live_ledger.py::merge_deltas` merged two
  episode rows for one `episode_id` LAST-WINS, and the daily pack lane
  (`scripts/entry_radar_live_pack.py` step 4) merges the §10 clock overlay —
  the ONLY producer of RESOLVED/EXPIRED rows — in ONE delta with the stateless
  C5/G0 replays, which re-emit every historical candidate as CANDIDATE because
  the pack re-stamps `freshness.pack_as_of` and that changes the canonical. The
  replay's CANDIDATE therefore overwrote the overlay's RESOLVED row on every
  pack, the RESOLVED transition was admitted (then address-deduped) while the
  stored state never became terminal, and nothing was ever compacted. Measured
  on the production ledger 2026-10-05: 44,972 CANDIDATE episodes back to
  1965-01-07, 45,223 →RESOLVED transitions, episodes.json 90,115,323 B, served
  entry_radar.json 33.6 MB, 4.8-minute live passes on a 5-minute timer.
falsifier: >
  On a fresh ledger run `python3 -m pytest tests/test_entry_radar_w4_ledger.py
  -k "outranks or end_to_end"`: if the overlay-first case passes with
  `_row_terminal` neutralised (`ll._row_terminal = lambda r: False`), the
  defect never existed in merge order. In production: after the first pack
  build following the merge of the terminal-wins fix, `jq
  '.episodes_count' /var/lib/macro-live/public/live/entry_radar.json` still
  reading tens of thousands, or `episodes.json` still ~90 MB with CANDIDATE
  rows dated before the pack's as_of minus 10 sessions, falsifies the
  diagnosis (another writer keeps them non-terminal).
so_what: >
  Never "fix" the payload by hand-editing or truncating state on the VPS, by
  restarting units, or by bounding the served episodes list in the Terminal —
  the backlog is a ledger defect and drains through the normal pack build.
  Terminal-wins in merge_deltas is NECESSARY but NOT SUFFICIENT (corrected
  2026-10-05 the same day, before merge): apply_run looks stored records up in
  episodes.json only, so once compact() archives the resolved rows the next
  full-history replay re-creates every one of them as a fresh CANDIDATE and the
  ledger oscillates between ~1 MB and ~90 MB on alternate builds — see
  DSC:ARCHIVED-EPISODES-ARE-UNKNOWN-TO-APPLY-RUN-SO-A-FULL-HISTORY-REPLAY-RESURRECTS-THEM
  for the admission horizon that closes the loop. With both rules in place the
  overlay resolves the stale candidates, `commit` opens inert C5-keyed re-arm
  blocks (`arm_allowed` is consulted only on the C1/C2/C3 paths), `compact`
  archives the ~44.9k terminal rows AND their transitions, the next replay
  refuses them at the door, and the served file shrinks to non-terminal +
  current/previous session terminals per
  DEC:ENTRY-RADAR-EPISODES-ARE-ADDITIVE-IN-THE-LIVE-PAYLOAD. Any future merge
  of an overlay with a replay must preserve terminal precedence; `commit`
  already refuses to update a stored terminal record and the merge must hold
  the same rule.
kind: landmine
verified_at: 2026-10-05
verified_by: >
  engine/entry_radar/live_ledger.py::merge_deltas (pre-fix loop
  `episodes[episode_id] = episode`); scripts/entry_radar_live_pack.py:569-590;
  read-only VPS readback 2026-10-05 13:5xZ of
  /var/lib/macro-live/state/entry_radar/episodes.json and
  /var/lib/macro-live/public/live/entry_radar.json; mutation control
  `ll._row_terminal = lambda r: False` → 2 precedence tests fail.
scope:
  - macro
  - engine/entry_radar/**
  - scripts/entry_radar_live_pack.py
  - WS:LIVE-ENTRY-RADAR
confidence: verified
---

## How it was found

The Terminal `/dislocations` route read a live payload whose `episodes_count`
was 44,972 while `health.state` was `out_of_window`. Every episode was
`C5_BOTTOM_WATCH@1` in CANDIDATE with `freshness.pack_as_of = 2026-10-02` and
`last_observed_at == candidate_at`; candidate dates ran from 1965 to
2026-10-02. The ledger held 45,223 `→RESOLVED` transitions against 262
RESOLVED episodes (all from the 2026-08 RTH lane). Today's pack delta line read
"48431 transition(s), 0 event(s), 46827 episode(s), 0 superseded terminal
trace(s)": the overlay resolved everything, the replay re-produced everything,
and the merge kept the replay.

## Why the obvious remedies are wrong

- Capping the served list hides the symptom and leaves a 90 MB ledger growing
  by ~47k rows per pack.
- Deleting or rewriting `episodes.json` on the VPS destroys the audit trail
  the §13 lifecycle promises and is forbidden state surgery.
- Making the replay skip known episodes would lose the genuine re-observation
  path (`superseded` accounting) that `apply_run` already models correctly.

The precedence rule belongs in the merge, where the two producers meet.
