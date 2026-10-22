VERDICT: FAIL

# B21 U2 re-review — PR #9999 landing head 1c5c74b4 (fix chain 0024c326 → 7ddeaf5f, plus main a92ee6e9)

- **Mode:** ROUTE review, READ_ONLY.
- **Export:** `git archive 1c5c74b4… | tar -x` into scratchpad/rr_u2 (my own export). In the seat worktree I ran git read commands only.
- **Standard:** contract (as amended), F26, F28 R1–R10, and the post-F28 seat rulings (weekend fallback struck; U4 key renamed `original_quarantined`).

**Blocking: 1.** The repair logic is otherwise sound. Every prior finding is fixed, and one fix-and-pin is all that stands between this and PASS_WITH_NOTES.

## BLOCKING

**X1 [blocker] The suite is red on the landing commit, so prophet-lab will fail CI.**
- Command, in the export: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=rr_u2 python3 -W ignore -m pytest tests/test_prophet_journey_notifications.py -q -p no:cacheprovider`
- Result: **`1 failed, 29 passed`**
- Failing test: `test_r2_not_after_anchors_on_the_transition_session_and_stale_never_mints`, at tests/test_prophet_journey_notifications.py:1357 (`assert len(plan.rows) == 1` → `0 == 1`).
- Cause:
  - The seat commit 7ddeaf5f changed **only** the engine and the contract (`git show --stat 7ddeaf5f`: 2 files). It struck the weekend neighbouring-session fallback in `_session_end` (engine :1067-1093, now `return None` at :1093).
  - The test block at :1349-1358 still asserts the struck behaviour: "a transition known on a Saturday takes Friday's next-session end", expecting one row with `not_after == "2026-08-31T20:00:00Z"`.
  - So the engine and test disagree, and the ruling that the seat itself made has no test pinning it.
- Repair, test only: replace :1349-1358 with the F28-post ruling. A Saturday-known transition with only Friday's row gives `rows == []` and `suppressed["not_after_unresolvable"] == 1`. Then re-run the suite and expect 30 passed.
- The CI measurement/ceiling work does not need to change. The step and paths are unchanged.

## Prior findings — disposition

| ID | Prior finding | Disposition | Evidence (export file:line / probe) |
|---|---|---|---|
| B1 | dedupe key drift for retracted/superseded | **FIXED** | engine :874-897 `before` comes from the B1 replay state in canonical order (`_replay_order` :666); retracted at :957, superseded at :978. Probe P1: run 1 mints `ACTIVE->CLOSED`, `CLOSED->SUPERSEDED`; run 2 with the evolving prev projection gives **0 rows**, `already_fired: 2` |
| E1 | stale replay / run-anchored not_after | **FIXED** | not_after comes from the transition's session (`_session_of` :758-766 → `_session_end` :1203). Recency gate at :1207-1211 (`not_after <= now` or no clock ⇒ `stale_transition_at_mint`). Probe P4: a 2026-08 transition replayed in 2027 gives 0 rows, `stale_transition_at_mint: 1` |
| E2 | `pe:` substring false positive on *PE tickers | **FIXED** | `_MACHINE_ID_RE = r"\b(?:pee?:[0-9a-f]|peg:[0-9a-f]|pe:SEC:)"` at :212, used at :540. Probe P3: HPE mints 1 row |
| E3 | non-terminal STATE_TRANSITIONED untested | **FIXED + pinned** | gate at :901-905, plus the reasonless/second-terminal gate at :907-913. Mutation M3 is now caught |
| C1 | producer patch re-read as user opt-out | **FIXED** | distinct branch at :1240-1244 (`original_producer_suppressed`). Unsent ⇒ PATCH + row in the same run (:1262-1272), with the non-presuming copy. In-run original handled at :1226-1233. Probe P6: run 1 gives 1 patch + 1 row "XYZ: this name is no longer tracked." (no "withdrawn" wording); run 2 gives 0 rows |
| C2 | emergence originals never correctable | **FIXED** | readback notice index at :1136-1148 (parses own fids, ranked by B1 replay); original = max prior at :1216-1225. Probe P5: run 2 supersede mints with `corrects_fire_event_id = prophet|emergence_triggered|…` |
| C3 | relation-level retraction copy | **FIXED** | `relation_level` at :966. Probe P7: "an earlier observation was withdrawn; the name remains tracked." |
| N1 | prev UNESTIMABLE → TRIGGERED | **RATIFIED (R8)** | engine :1006-1014. One-sentence contract amendment in §eligibility (diff hunk `+  Exception (ratified deviation, seat ruling F28 R8)…`) |
| N2 | prev READ_UNAVAILABLE treated as empty | **FIXED** | :803-805 `prev_projection_unavailable`. Probe R9: 0 events |
| N3 | emergence not gated on curr ACTIVE | **FIXED** | :1022-1035. Probe R4: TRIGGERED on a CLOSED lifecycle mints no emergence |
| N4 | ticker correction ignored | **FIXED** | `_episode_identity(applied)` at :723. Probe R10: corrected ticker ABC used for routing and glance |
| order nit | recorded_at vs B1 replay order | **FIXED** | `_replay_order` :666; events sorted by replay rank at :1050-1058 |
| tests | six missing tests | **FIXED** | the suite grew 18 → 30, including a replay-order permutation test (:1290-1302), an R3 HPE test (:1368+) and per-ruling tests |

PASS items carried over, rechecked:
- `REQUIRES_TIER = "essential"`.
- episode_opened is never minted (:884-888).
- The module stays pure (no new imports beyond re/uuid/dataclasses/typing; 7ddeaf5f removed `from datetime import date`).
- No trade language.

## NOTES (non-blocking; for the seat to own)

**N-A [major consequence, by ruling] Off-calendar UTC dates permanently drop transitions.**
- `_session_of` (:758-766) takes the session as the **UTC** date of `known_at`. With the fallback struck, any transition whose `known_at` falls on a non-row UTC date is never notifiable. It does not lag; it is never sent.
- Affected UTC dates:
  - weekends;
  - US holidays;
  - Friday ET evenings after 00:00Z, which land on Saturday UTC.
- Probe NEW: EXPIRED known `2026-08-29T01:30:00Z` (Friday 21:30 ET), with Friday's row present and the run at 02:00Z, gives `rows 0, not_after_unresolvable: 1`, event session `2026-08-29`.
- Whether this bites depends on the B1 transition producer's clock (us_candidate_episode.py:1055 takes `known_at` from the command). I did not verify that clock.
- Suggested follow-up that is not a guess: resolve the session as the first calendar session whose close is ≥ known_at, in exchange time. Alternatively, assert the producer clock never lands off-calendar.

**N-B [nit] Equality boundary differs between producer and drain.**
- The producer treats `now == not_after` as stale (:1207, `<=`). Contract §5 (:323) has the drain suppress only on `now_utc > not_after`. The producer is stricter, so it is safe, but the two sides are not identical.

**N-C [minor drift] Producer-side typed keys are missing from the contract.**
- `stale_transition_at_mint`, `not_after_unresolvable`, `original_producer_suppressed`, `original_superseded_in_run` and `prev_projection_unavailable` exist in the engine but are not named in the contract (grep finds no hits in the contract). Only `original_quarantined` was aligned (U4 row).
- The contract §5.1 mint-time gate text should name them.

## CI registration

- `.github/ci/legacy-jobs.yml`: the module and suite are in prophet-lab paths (:8981-8982), and the step is at :9053.
- Main's W33-LA `macro-signals-conditions` registration survives (:26600).
- `tests/test_ci_pack.py:5179-5180` = `("templates/index.html", 136, 5_844)` and `("scripts/build_free_content.py", 135, 5_817)`. Main a92ee6e9 has 5_841 / 5_814, so each is exactly +3.
- I did not re-run test_ci_pack itself (see Not reached).

## Mutation reruns

All in my export, with the engine restored after each (diff verified). The baseline is 1 failed (X1), so "caught" means more than one failure.

| # | Ruling | Mutation | Result |
|---|---|---|---|
| M2' | R1 | `before = "ACTIVE"` always (:893) | 3 failed, 27 passed — caught |
| M3 | R4 | terminal gate admits `ACTIVE` (:901) | 2 failed — caught (previously SURVIVED) |
| M7 | R5 | producer-suppressed branch disabled (:1240) | 3 failed — caught |
| M8 | R6 | readback notice index dropped (:1146) | 6 failed — caught |
| M9 | R4 | emergence ACTIVE gate disabled (:1031) | 2 failed — caught |
| M10 | R9 | prev-unavailable gate disabled (:803) | 2 failed — caught |

Probes: `cd rr_u2 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=rr_u2 python3 -W ignore scratchpad/rr_probe.py`. Outputs are quoted in the table above.

## Diff hunks relied on

- `git show 7ddeaf5f -- engine/prophet_journey_notifications.py`: `_session_end` fallback removed (`-    try: weekend = date.fromisoformat(session).weekday() >= 5 … +    return None`).
- `git show --stat 7ddeaf5f`: engine + contract only, no test change. This is the root cause of X1.
- The contract diff 6e6798aa..7ddeaf5f: the R8 exception sentence, and the U4 key renamed to `original_quarantined`.

## Not reached

- Running `tests/test_ci_pack.py` / the manifest checker in the export. I verified the ceilings by diff against main only.
- Verifying the production `known_at` clock of B1 STATE_TRANSITIONED commands, which decides N-A's real-world frequency.
- A full re-audit of the compose_payload field semantics (the 17-key shape was unchanged from the prior PASS).
- Randomized test order (pytest-randomly is not installed).

## Addendum — 7fad42de (2026-10-22)

**Verdict for 7fad42de: PASS_WITH_NOTES. Blocking: 0.**

- **Commit shape:** 7fad42de has a single parent, 1c5c74b4.
- **Scope:** `git diff --stat 1c5c74b4 7fad42de` gives `tests/test_prophet_journey_notifications.py | 10 ++++++----, 1 file changed`. The engine, contract, CI yml and test_ci_pack are therefore byte-identical to 1c5c74b4.
- **X1 is FIXED.** The Saturday block now asserts `plan.rows == []` and `plan.suppressed["not_after_unresolvable"] == 1`. The old row, not_after and market_session assertions were removed.
- **Suite:** run in a fresh export (scratchpad/rr_u2b) with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=rr_u2b python3 -W ignore -m pytest tests/test_prophet_journey_notifications.py -q -p no:cacheprovider`. Result: **30 passed in 1.23s**.
- **Notes:** N-A, N-B and N-C stand as non-blocking notes, consumed by the seat for the U4 ruling. They are not re-litigated here.
- **Still not run:** test_ci_pack / the manifest checker (unchanged since 1c5c74b4, where they were verified by diff only).
