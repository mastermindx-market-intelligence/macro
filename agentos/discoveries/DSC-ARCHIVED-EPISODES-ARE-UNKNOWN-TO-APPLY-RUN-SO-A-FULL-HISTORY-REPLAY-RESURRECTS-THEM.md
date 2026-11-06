---
key: ARCHIVED-EPISODES-ARE-UNKNOWN-TO-APPLY-RUN-SO-A-FULL-HISTORY-REPLAY-RESURRECTS-THEM
claim: >
  LiveEpisodeLedger.apply_run resolves "do I already hold this trace" from
  self._episodes alone — episodes.json — and LiveEpisodeLedger.compact pops a
  terminal row out of that dict when it moves it to episodes_archive_YYYYMM.json.
  The daily pack lane's C5 replay is STATELESS and FULL-HISTORY (every bottom
  watch a ticker's slice ever produced, 1965→today, on every build), so the
  build after a compaction finds no stored record for ~44.9k archived episodes
  and re-creates each as a brand-new CANDIDATE with the same episode_id; the
  §10 overlay resolves them again ten sessions later, compaction archives them
  again, and the ledger oscillates between ~1 MB and ~90 MB on alternate
  builds. Transitions were never compacted at all: 138,917 rows, 58.9 MB of
  the 90,115,323 B production file on 2026-10-05. The live lane's C3 replay has
  the same shape over a bounded window (60 sessions of warm-up, clamped to the
  reader's 180-session bound), so it re-mints terminal C3 history too.
falsifier: >
  On a fresh ledger: candidate → overlay at H → commit (RESOLVED) → compact at
  COMPACTION_SESSIONS+5 (archived, ledger.episodes == ()) → replay the same
  trace at that session with _SessionCut.beyond neutralised: if the row is NOT
  re-created as CANDIDATE, apply_run consults the archives and this record is
  wrong (tests/test_entry_radar_w4_ledger.py
  test_LED2_a_drained_then_archived_episode_is_not_resurrected_by_the_next_replay
  carries that positive control inline). In production: two consecutive pack
  builds after the horizon merge whose delta lines both read "0 historical
  trace(s) refused" while episodes.json stays small falsify the mechanism.
so_what: >
  A stateless full-history replay may only mint into a ledger behind an
  ADMISSION HORIZON that is no longer than the compaction window:
  HISTORICAL_TRACE_SESSIONS == COMPACTION_SESSIONS (40), so nothing a replay can
  mint is ever archived while still mintable, and nothing archived can be
  re-minted. A trace whose market_session is more than 40 sessions before the
  as_of is refused at the door with its transitions and reported on
  PendingDelta.historical (episode_id, ticker, detector_id, variant, state,
  market_session) — visible, never silent. Do not raise the horizon above the
  compaction window, do not make apply_run read the archives (a 331-file read
  on every pass on a 2-core, 3.9 GB box), and do not "fix" the symptom by
  capping the served list or by deleting state on the VPS. The C3 clamped
  window mints rows older than the horizon that are terminal by construction
  (C3_ARM_EXPIRY_SESSIONS = 15); they are refused as history and the §10 clock
  proof reads off delta.historical, not the ledger. The pack delta line now
  prints "N historical trace(s) refused"; a healthy steady state is tens of
  thousands refused per build with episodes_count in the hundreds.
kind: landmine
verified_at: 2026-10-05
verified_by: >
  engine/entry_radar/live_ledger.py apply_run (stored = self._episodes.get)
  and compact (self._episodes.pop); production copy of
  /var/lib/macro-live/state/entry_radar/episodes.json read 2026-10-05 13:5xZ
  (45,234 episodes / 36.0 MB, 138,917 transitions / 58.9 MB, 519 episodes
  within 40 sessions of 2026-10-06, 1,944 within 200); mutation control
  ll._SessionCut.beyond = lambda *a: False → 6 LED2/LED8 cases fail.
scope:
  - macro
  - engine/entry_radar/**
  - scripts/entry_radar_live_pack.py
  - scripts/entry_radar_live.py
  - WS:LIVE-ENTRY-RADAR
confidence: verified
---

## How it was found

Tracing what the first post-terminal-wins pack build would do to the
production ledger copy: the overlay resolves 44,972 candidates, compaction
archives them, and the NEXT build's C5 replay — which reads the slice store,
not the ledger — hands apply_run the same 46.8k traces with nothing stored
under their ids. Each becomes a new CANDIDATE row again. The terminal-wins
rule cannot help because there is no terminal row left in episodes.json to
win.

## Why the horizon lives in apply_run, not in the pack lane

Both lanes replay: the pack lane's C5 over full history, the live lane's C3
over a 60–180-session window. A horizon applied only in the pack script would
leave the live lane re-minting archived C3 terminal rows every pass. The door
is the one place every replay passes through.
