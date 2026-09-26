---
key: TWO-CONSUMERS-OF-ONE-DATASET-DISAGREED-ABOUT-ITS-ADDRESS
claim: >
  The EquityDesk earnings-call archive had a WORKING R2 transport the whole time the
  Prophet hold-leash was reported as starved for lack of one. `engine/earnings_qual.py`
  reads it from `data/earnings_calls/history.parquet` at tier `r2_history`
  (earnings_qual.py:1627), published by `scripts/publish_earnings_r2.py` and restored by
  `scripts/fetch_earnings_scores.py`. `engine/prophet_stage_inputs.py` resolved a
  DIFFERENT address for the identical evidence —
  `data/stage_analysis/backfill/earnings_calls.parquet` — which is gitignored, has zero
  commits, and has no publisher. Same dataset, same native `document_ticker` /
  `call_date` / `earnings_call_sent` columns, same ~-10..30 desk scale, two addresses,
  one of them unreachable in production. `DNR:HOLD-PSQ-TILT-CLOCK` (2026-08-06) froze a
  promotion clock over this and diagnosed it as a missing fetch/publish pair; the pair
  existed, one consumer just did not know the address. A SECOND, independent cause
  compounded it: `daily.yml`'s only hydration call (`scripts.fetch_earnings_scores`,
  inside `scripts/ci/daily_engine_regional_desk_builders.sh:141`) sits ~840 lines BELOW
  the Prophet step in the SAME `engine` job, so even a published store arrived after the
  night's plans were written. Both were invisible because every directory involved is
  gitignored: nothing shows in `git status`, and an empty join is indistinguishable from
  an honest negative unless a consumer discloses which it is.
falsifier: >
  `python3 -m pytest tests/test_prophet_earnings_source_restore.py::test_prophet_tiers_are_the_native_prefix_of_the_earnings_qual_ladder`
  failing, or `engine/earnings_qual.py::_backfill_earnings_candidates` no longer listing
  `data/earnings_calls/history.parquet` first. Reproduce the original starvation by
  placing that file plus its `manifest.json` on a host with no
  `data/stage_analysis/backfill/earnings_calls.parquet` and asking
  `psi.resolve_ec_source()`: pre-repair it answered `unavailable` with the table sitting
  right there.
so_what: >
  Before concluding that an artifact "has no transport", grep for the FILENAME and for
  every sibling address the same dataset might live at — not just the path the consumer
  in front of you names. Here the answer was one `grep -rn "history.parquet"` away and a
  binding registry row had already been written on the opposite premise. Two rules
  follow. (1) When two production modules consume one dataset, they must resolve it
  through ONE ordered ladder with shared tier names, or they will silently diverge; the
  Prophet ladder is now pinned as the NATIVE prefix of the earnings_qual ladder so a
  reorder on either side goes red. (2) Hydration ORDER inside a single CI job is as
  load-bearing as the transport itself — a fetch step 800 lines below its consumer is the
  same as no fetch at all, and nothing in the repo tests step order unless you write that
  test. Also: do NOT "fix" an address mismatch by repointing at whatever nearby file has
  a plausible name. `data/earnings_calls/scores.parquet` sits in the very directory the
  correct store lives in and carries a -1..1 `sentiment`; adopting it would have
  re-scaled a promoted construction against `EC_SENT_GATE = 24`. Two of
  earnings_qual's four tiers are likewise PROJECTIONS (`sent * 18 + 12`) and must not be
  admitted to a promoted gate.
kind: landmine
verified_at: 2026-09-18
verified_by: >
  RED/GREEN reproduction on a host holding only the transported store (pre-repair
  `resolve_ec_source().state == "unavailable"`, `ec_sent_at_entry` None; post-repair
  `available` / 30.0); `tests/test_prophet_earnings_source_restore.py` (31 cases,
  including a deploy-host proof driving the real `scripts.fetch_earnings_scores.fetch`
  against a local-directory S3 stand-in); daily.yml step indices 30 vs 32 after the
  repair, ~2315 vs ~3156 before it; PR #7294
scope:
  - mastermindx-market-intelligence/macro
  - engine/prophet_stage_inputs.py
  - engine/earnings_qual.py
  - scripts/fetch_earnings_scores.py
  - scripts/publish_earnings_r2.py
  - .github/workflows/daily.yml
confidence: verified
---
