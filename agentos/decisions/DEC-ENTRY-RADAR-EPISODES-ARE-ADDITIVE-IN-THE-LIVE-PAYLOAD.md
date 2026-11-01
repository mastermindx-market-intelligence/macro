---
key: ENTRY-RADAR-EPISODES-ARE-ADDITIVE-IN-THE-LIVE-PAYLOAD
question: >
  Where does the Terminal /dislocations screen read live Radar episodes from: an
  additive ``episodes`` array inside the existing ``live/entry_radar.json``, or a
  second served file?
answer: >
  Additive. ``live/entry_radar.json`` (schema string unchanged, ``entry_radar.live/v1``)
  gains a top-level ``episodes`` array of untouched ``LiveEpisode.to_dict()`` rows —
  every non-terminal episode plus terminal episodes from the current and previous
  reference session — and ``health`` gains ``episodes_count`` and ``episodes_schema``.
  The key is ABSENT (never ``[]``) on the evaluator-failure path, which the Terminal
  route reports as ``episodes_not_published``. No second served file.
rationale: >
  The payload is already the one auth-gated, health-receipted artifact the Terminal
  server reads from disk on the same host (``MACRO_LIVE_DIR``), and the Terminal screen
  derives its stale/unavailable states from that file's ``health`` and ``asof``. A second
  file would be a second freshness receipt, a second auth-gating decision and a second
  consumer contract for the same ledger. PIT-W4-13 holds by construction: the payload is
  built after ``spool_then_commit`` and the ledger mutates only inside ``commit()``, so a
  withheld transition never appears in ``episodes``. The session bound on terminal
  episodes keeps the served file small on the 2-core / 3.9 GB box.
alternatives:
  - option: A separate served file ``live/entry_radar_episodes.json``
    why_not: >
      Duplicates the health/freshness receipt and the Caddy default-deny decision;
      the Terminal contract (``lib/dislocations/types.ts``) and its fixtures already
      read ``episodes`` from ``entry_radar.json``. Left "open" in the product spec;
      closed here.
  - option: Publish the whole ledger (all terminal episodes until compaction)
    why_not: >
      Unbounded growth of the served file between compactions on a memory-starved
      host; the product spec bounds terminal rows to the current and previous session.
  - option: Compose display fields (stance, watching lines) producer-side
    why_not: >
      The live lane is mechanical copy only (A7); display composition is the
      Terminal's ``displayFor`` and stays there.
evidence:
  - "research/INTRADAY_DISLOCATION_TERMINAL_PRODUCT_SPEC_V1.md:134-137 — additive ``episodes`` array; ``health.episodes_count`` / ``episodes_schema``"
  - "engine/entry_radar/live_eval.py ``_payload`` (no ``episodes`` key before this change); ``run_pass`` calls ``_payload`` after ``ll.spool_then_commit``"
  - "engine/entry_radar/live_ledger.py:620 — ``self._episodes[...] = record`` only inside ``commit()``"
  - "mastermind-terminal ``lib/dislocations/types.ts`` ``EntryRadarFile.episodes?``; ``fixtures/dislocations/fresh.json`` carries 9 owner-schema rows; PR #808 renders them"
  - "Producer branch ``claude/idr-live-episodes-payload-20261004`` (lane IDR_P_EPISODES_W1, frozen spec F1–F5, tests T1–T6)"
affects:
  - WS:LIVE-ENTRY-RADAR
  - engine/entry_radar/live_eval.py
  - mastermind-terminal lib/dislocations/**
confidence: high
reversibility: easy
decided_by: "coo-fable (IDR CEO seat a0115103)"
decided_at: 2026-10-04
---

The Terminal reads ``${MACRO_LIVE_DIR}/entry_radar.json`` on the same host; the
Macro live lane publishes it once per pass and withholds nothing the ledger did not
commit. Publishing the committed episodes inside that file keeps one artifact, one
health receipt and one gate. A failed pass omits the key so the screen says "source
unavailable" rather than "nothing on the board".
