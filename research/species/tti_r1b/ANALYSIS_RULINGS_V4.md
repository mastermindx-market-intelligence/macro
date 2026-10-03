# TTI R1-B v4 — FROZEN ANALYSIS RULINGS (pre-outcome)

Status: adopted by the programme architect (Fable CEO seat, handoff mastermind-terminal#784) on 2026-10-03,
BEFORE any outcome of the study was computed, read or inferred. Source: independent outcome-blind Opus review
of the architect's tentative rulings at carrier head 9015dfefa535 (PR macro#7274); all six of the reviewer's
overturns (O1-O6) are accepted and folded into the numbered rulings below. Where the frozen text admits more
than one honest reading, every admissible reading is published and the prospective gate passes only if it
passes under ALL of them. No reading may be chosen by what it does to the result.

Frozen inputs these rulings interpret (never edited): research/species/TTI_R1B_V4_PREREG.md
(sha256 a8afab8d87cfe912aeaed02c105112869943433cf6b7bb7c765bd2768d0dfcd3), research/species/tti_r1b/config_v4.json
(sha256 24b5a89f8df9c441160f1162c0f08d62796e842e29fff3c55766160fe388bc19), the 60 registered ledger rows
(sha256 8fc5a844886cfa2d69ec25f38fd6948b4a4556e01829bea76338e94570def281, registered at 350c57e1c6aa).

## Rulings

Terms used below: TD = TEXT-DETERMINED, one reading. CD = PRE-OUTCOME-CODE-DETERMINED, fixed by code committed before outcomes. UD = UNDER-DETERMINED, two or more honest readings. "d" = the selected event's confirmation delay in bars.

1. **Control clock (a).** §10: "shifted by the same `d` completed confirmation-delay bars **plus the same one full five-minute processing-latency bar**". CD at tactical_exhaustion.py:455-456 (`control_at + timedelta(minutes=delay * 5 + processing_minutes)`). Uphold: control entry = control candidate decision + 5d + 5 minutes.
   - The measurement function needs a decision time and checks `entry_at == decision_at + 5` (te.py ~597). So set the control's `decision_at` = control candidate + 5d.

2. **Control measurement inputs.** The frozen text is silent; §10 says only "lawful matched-control returns". Treated as TD. Ruling:
   - Join each control by `anchor_id` to its own session's `construct_one_day` anchors and normalization: own `prior_atr`, `previous_regular_close`, `candidate_low`, own beta.
   - Use the same `measure_event_outcome` path and the same horizon and cost as the selected cell.
   - `selector` = `"BASE_FRESH_LOW"`. This is only a validation tag, because census rows are base anchors.
   - `episode_low` := `candidate_low`. Report the control's episode-delay and episode-LOD fields as `not_applicable`; §9 defines them "for confirmed families" only.
   - Copying the selected event's fields onto a control is forbidden.

3. **Delay d per selector.** CD at te.py:272/313-316. BASE_FRESH_LOW and EXHAUSTION_FORMING have d = 0. RECLAIM_ONLY, EXHAUSTION_RECLAIM and CONTINUATION_RISK have d = i − anchor index, which is 1, 2 or 3.

4. **Matching time (c).** §10: "same 30-minute decision-time bin … same sign of QQQ open-to-decision return", and "its membership uses candidate-time facts only". CD at te.py:397-406 and the runner's `construct_one_day`, which takes the sign at `candidate_at`. Uphold.
   - Bin = ET minutes-since-midnight ÷ 30, rounded down. These are wall-clock half-hours, so 09:45–09:55 is one bin and 14:30 is a bin of its own.
   - Sign = close of the last QQQ bar before candidate time minus the 09:30 open. It is null if the QQQ prefix has any gap or invalid bar (runner:158-200).
   - Sign 0 matches only 0.

5. **Control floor (b).** Prereg §10: "If fewer than 10 matched controls exist, the selected event is marked `no_control`. There is no fallback". Plan:25: "unavailable when the frozen pool or usable residual evidence is below its floor". UD. Admissible readings:
   - **L:** at least 10 matched controls by candidate-time facts, and at least 1 control return available.
   - **S:** at least 10 control returns available.
   - In both, delta = selected return − mean of the available control returns.

6. **Control shift-bar validity (new).** §10 "completed confirmation-delay bars" against §8, where outcome evidence starts at the entry bar. UD. Admissible readings:
   - **A:** only the entry-onward path is validated, exactly as the selected event's own measurement does.
   - **B:** each of the control's d shift bars must exist once with valid OHLC and positive volume, else that control is censored. This is the standard the selected event's confirmation bars met.
   - Publish all four readings L-A, L-B, S-A, S-B. Report L-A first, because the prereg outranks the plan and A is the frozen measurement function's own evidence rule.
   - The gate passes only if it passes under all four.

7. **Primary return.** §10: "selected 60-minute net beta-residual return at 25 bp minus the mean of its lawful matched-control returns". TD: the control return is the control's `net_beta_residual` in the same cell.
   - Algebraic fact: the cost cancels, so the 10, 25 and 50 bp matched deltas are identical. Cost cells differ only in absolute returns. Publish this as a fact.

8. **Censoring.** §8: "censored for that horizon, not dropped from the fire count". TD.
   - A selected event whose primary residual is unavailable stays in the fire count and is counted as `selected_censored`. No delta.
   - A selected event with a null QQQ sign is marked `no_control` with reason `qqq_sign_unavailable`. Today `match_controls` raises on it (te.py:384).
   - Census rows with a null sign are rejected and counted separately.
   - Neither `no_control` nor censored events enter the date mean. No-control fraction = `no_control` events ÷ fires.

9. **Date mean.** §10/§12: "average within calendar date first". TD.
   - Date = session date. Date mean = mean of that date's deltas for the selector.
   - Primary statistic = unweighted mean of date means.
   - A date with no deltas does not exist in the series.

10. **Calendar-week block.** The frozen text is silent. Ruling:
    - Block = ISO week (`date.isocalendar()[:2]`) of each date in the series.
    - Blocks sorted ascending; dates inside a block ascending. K = number of such blocks.
    - Weeks with no dates are not blocks. The alternative that includes empty weeks is inadmissible: it makes the resample size random, can produce an undefined replicate, and is not "resample calendar-week blocks" of the observed series.
    - Each replicate always holds at least one date. If K = 0, the interval is unavailable and the gate fails.

11. **Bootstrap mechanics.** §12: "4,000 bootstrap replicates, seed 20260917 … 95% percentile interval". Ruling:
    - For each (selector, reading), create a fresh `numpy.random.default_rng(20260917)`.
    - Draw `idx = rng.integers(0, K, size=(4000, K))`; row r is replicate r.
    - Replicate statistic = mean of all date means in the concatenated drawn blocks, counting duplicates.
    - Interval = `numpy.quantile(reps, [0.025, 0.975])` with the default `method='linear'`.
    - Gate test: lower bound strictly > 0.

12. **Which cells get intervals.** §12: "For the primary matched deltas". TD: an interval only for the 60m/25bp cell of each selector. Other cells get the point statistic only and play no gate role.

13. **Eligible fires.** §13: "at least 300 eligible fires, 100 distinct dates and 6 tickers". UD between raw fires and fires that contribute a delta.
    - For the count thresholds the delta-contributing count is the binding test, because those events are a subset of raw fires.
    - Ticker share (§13: "no single ticker contributes more than 35% of fires") does not move monotonically between the two denominators. Gate it on the raw denominator and on the delta-contributing set of each reading.
    - A ticker counts toward "6 tickers" if it has at least 1 eligible fire.

14. **Partition sign.** §13: "early and late retrospective partition primary deltas have the same sign". TD: the primary statistic computed within each partition, no interval. "Same sign" requires both strictly positive or both strictly negative; 0 fails.

15. **Control partition.** CD at te.py:443: a control's partition is set by the control's own date. The same-date exclusion is CD at te.py:440.

16. **Selected events inside the control pool.** Config `matched_control_exclude_selected_family: false`. TD: a control stays in the pool even if it is a selected event on its own date.
    - Publish overlap (§10 "Report … overlap explicitly"): the number of selected anchors that appear in other events' pools, and the distribution of how many pools each control sits in.

17. **Census ties and duplicates.** CD at te.py:316-327:
    - The first base anchor per symbol, session and bin that passes the displacement and impulse tests, taken in chronological order.
    - A zero-range candidate does not use up its bin.
    - A duplicate `anchor_id` is rejected (te.py:420).
    - One missing, duplicate or invalid bar disables every later candidate in that session (`prefix_complete`). Disclose the number of such sessions per symbol.

18. **Bucket edges.** §10 uses half-open buckets `[0.50,0.75)` etc. CD as `bisect_right(edges, x) − 1` on raw floats with no rounding. Synthetic check: `(0.75,1),(1.0,2),(1.5,3)`.

19. **Descriptive metrics** (§12; no gate role except where §13 names them):
    - Ticker coverage = tickers with at least 1 fire, plus per-ticker counts.
    - Per-ticker sign = sign of the mean of that ticker's deltas.
    - Single-ticker concentration = largest ticker share of fires.
    - Time-bin concentration = largest share by candidate bin. Also show it by decision bin.

20. **Coverage (g).** Uphold, and add: per-symbol and QQQ session coverage, the sessions in capped files, and beta- or ATR-unavailable sessions are written and hashed before the first outcome call. Missing sessions are never filled.

21. **Gate bullet 5.** "no systematic admission artifact that explains the result". UD and not mechanical. Ruling: this bullet is marked `REQUIRES_ADJUDICATION`. The run can at most publish "candidate pending artifact adjudication by an independent reviewer", working from the disclosures in rulings 17 and 20.

22. **Refusals and leak audit.**
    - Refuse when: the output directory already exists (even empty); any results artifact for this study_id already exists; any hash mismatch on prereg, config, ledger rows or input manifest; any network or provider path.
    - Order: build all control pools, write them to disk and hash them before any `measure_event_outcome` call.
    - The leak audit must contain: those hashes; the code sha; the test result for every §14 test at that sha; every census row showing `future_family_labels_used=false`; `market_outcomes_computed=false` on every pool; rejection counts by reason; overlap counts.
    - (e) Uphold. The row-bytes admission is implemented (runner:63-87).

## Architect's additions (same date, same pre-outcome status)

23. **Admission hardening (from the exact-head admission review, verdict APPROVE_WITH_NITS).**
    - A test must kill the mutant that removes the `te.CONFIG_SHA256` comparison: editing a non-grid config value
      together with the receipt's `config_sha256` is refused with `config_sha256_mismatch`.
    - A ledger line that is not valid UTF-8 and a registered row with a duplicated JSON key are refused with
      named reasons (`registered_row_unparseable`, `registered_row_duplicate_key`).
    - The registration receipt's ledger-prefix hash is DISCLOSED in the run's leak audit
      (`ledger_prefix_matches_receipt: true|false`, computed over the first `ledger_lines_after - 60` non-empty
      lines) and is not a refusal: no threshold of this study depends on the pre-registration prefix, and a hard
      pin would couple every other programme's ledger row to this study's tests.
24. **Single run.** The registered study is executed exactly once, from a `git archive` export of the reviewed
    carrier head, against the already-captured D0 5-minute inputs (manifest sha256
    59c50ed405bd76c083a1d2beb20cf25edd6f4bd892c3e55fd38d21a66bef642b). Event-, outcome- and match-level files
    and every licensed bar stay outside Git; Git receives aggregate tables, hashes, counts and the disposition.
25. **Disposition vocabulary.** If any mechanical gate bullet (1-4) fails under any reading: `NO_PROMOTION`.
    If bullets 1-4 pass under every reading: `PROSPECTIVE_CANDIDATE_PENDING_ARTIFACT_ADJUDICATION` (ruling 21).
    Neither disposition grants rank, alert, sizing or trade authority; V1-V3 remain DO_NOT_RUN.
26. **Cost cells.** Because selected and control returns carry the same round-trip cost, the matched delta is
    identical at 10, 25 and 50 bp (ruling 7); the 60 cells are still all reported, with absolute net returns
    differing by cost and the matched delta stated once per (selector, horizon) with that fact printed.
27. **Arithmetic form of the bootstrap replicate (same quantity as ruling 11, fixed so two implementations agree
    to the last bit).** Block sums use `math.fsum`; `sums` is float64 and `counts` int64, one entry per ISO-week
    block in ascending order; `reps = sums[idx].sum(axis=1) / counts[idx].sum(axis=1)`. Event delta =
    selected return − `math.fsum(controls)/len(controls)`; date mean and primary statistic likewise use
    `math.fsum(values)/len(values)`. The run records the numpy version in its leak audit.
28. **Event accounting identity.** For every cell and reading:
    `fires_raw = fires_delta + control_evidence_unavailable + |no_control ∪ selected_censored|`. An event that is
    both `no_control` and `selected_censored` is counted in both tallies and once in the union; the no-control
    fraction is `no_control ÷ fires_raw` regardless of censoring.
29. **Selected-event identity is the frozen constructor's.** Each selector emits at most its first qualifying
    event per symbol/session (`emitted` set in `construct_session`); the consumer never adds, drops or reorders
    fires. A control's measurement inputs therefore come from the control session's `anchors` row and that
    session's normalization (ruling 2), not from any selector event.
30. **Pool construction detail.** Census rows with a null QQQ sign are removed first and counted (ruling 8);
    each selected event is then matched against the ENTIRE remaining census, all symbols, so `excluded_counts`
    is the frozen matching function's own count (the same-ticker rule rejects other symbols by reason). A
    control's outcome for a given (anchor, d, horizon, cost) is computed once and reused by every pool that
    contains it — a cache of an identical deterministic computation, never a selection. The run asserts
    `bootstrap_repetitions == 4000` and `seed == 20260917` from the frozen config before any outcome call.
