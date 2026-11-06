---
key: ENTRY-RADAR-CATALYST-LIVE-READ-IS-OPT-IN
question: >
  How does the live Radar payload get decision-time EDGAR Item 2.02 coverage for an
  episode's ticker when the nightly backfill receipt is hours old, and what clock does
  the catalyst assessment run on when the owner answers after the pass started?
answer: >
  A second read of the SAME owner at decision time: ``catalyst_edgar_live.read_edgar_item_202_live``
  fetches each episode ticker's recent submissions block through the collector's own
  ``_sec_get_json`` / ``_extract_8k_rows`` (same source id as the store read, CIK from the
  tracked store parquet), bounded to 48 tickers / 20 s per pass at the owner's 0.12 s pace,
  fail-open to the nightly store read. It runs ONLY when ``ENTRY_RADAR_CATALYST_LIVE=1`` is
  set at call time, which exactly two producers set: the VPS unit
  ``app/deploy/macro-live-entry-radar.service`` and the Actions backstop's evaluate step.
  The catalyst decision clock is ``decision_at = generated_at = max(now, live.last_observed_at)``;
  per ticker the attach prefers a live ``ok`` read, else the store read, else records
  ``source_modes.none``. The receipt gains ``live_enabled``, ``live{...}``, ``source_modes``
  and ``decision_at``; no existing key changes meaning.
rationale: >
  Every episode without a blocking filing read ``coverage_unknown`` at 13:04Z because the only
  owner receipt was the 19:48Z nightly backfill (mapping doc §3): the store read is honest but
  blind for the whole session. Asking the owner itself at decision time closes that gap without
  a second event store, a second HTTP owner or a second freshness receipt. ``usable_at`` needs
  ``observed_at <= decision_at``, and a live answer is observed after the pass clock ``now``, so
  the decision clock must advance to the last live observation or the read it just paid for is
  unusable by construction. Opt-in via the environment (not a default) keeps every test, CI run
  and research lane network-free; the reader never reads the environment itself, so the gate
  lives in exactly one place (``_catalyst_live_enabled``).
alternatives:
  - option: Default-on live read gated only by a kill switch
    why_not: >
      Every pytest run of the attach path and every CI job would hit data.sec.gov unless
      each injected a fake; one forgotten injection is a network call from CI.
  - option: Warm the store more often (hourly backfill) instead of a live read
    why_not: >
      Still stale by up to an hour at decision time and runs the full collector on the
      2-core box during RTH; the live read costs <=48 requests per 5-min pass.
  - option: Pass ``decision_at = now`` and accept the live read as "observed before now"
    why_not: >
      Backdates an observation receipt; ``CatalystSourceRead.usable_at`` and the context
      hardening (#8305) exist precisely to refuse that.
  - option: A cross-pass cache of live answers under ENTRY_RADAR_STATE_DIR
    why_not: >
      Deferred (wave 2b-3) until a week of ``health.catalyst.live.elapsed_s`` receipts
      shows the budget actually binds; an unmeasured cache is a second freshness semantic.
evidence:
  - "engine/entry_radar/catalyst_edgar_live.py (wave 2b-1, lane IDR_CAT_W2B1, tests test_W2B1_* T14-T19)"
  - "engine/entry_radar/live_eval.py ``_attach_catalyst`` / ``_catalyst_live_enabled`` (wave 2b-2, lane IDR_CAT_W2B2, tests test_W2B2_* T20-T25 + test_EP_catalyst_live_read_is_opt_in_on_real_producer_paths)"
  - "VPS 2026-10-04: last live pass 26 s wall / 15.7 s CPU under TimeoutStartSec 570 (drop-in); data.sec.gov HEAD 200 in 0.19 s from the host; data/edgar/company_tickers.json absent on the host (gitignored) -> CIK from the tracked store parquet"
  - "research/live_entry_radar/INTRADAY_DISLOCATION_CATALYST_EDGAR_EARNINGS_R0_MAPPING.md §3 (clock law), §7 (no-coverage rule)"
affects:
  - WS:LIVE-ENTRY-RADAR
  - engine/entry_radar/live_eval.py
  - engine/entry_radar/catalyst_edgar_live.py
  - app/deploy/macro-live-entry-radar.service
  - .github/workflows/entry-radar-live.yml
confidence: high
reversibility: easy
decided_by: "coo-fable (IDR CEO seat a0115103)"
decided_at: 2026-10-04
---

The nightly store read stays the floor; the live read is the same owner asked again,
closer to the decision. Removing one line from the unit and one from the workflow
turns it off with no code change, and the receipt says which mode served every row.
