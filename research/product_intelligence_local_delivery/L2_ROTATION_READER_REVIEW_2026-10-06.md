# L2 independent adversarial review — `read_ledger_history` (#8470 @ 1537636f)

**C0:** **ACCEPT_WITH_FOLLOWUPS** — replay vs retained-unmarked is honest when consumers honor per-row `mode` and both clocks, but mis-tagged `replayed` and write-clock vs observation-clock skew are not surfaced in coverage (`engine/rotation_events.py:1415-1418 @ 1537636f`).

**MAIN_PIN** (after `git fetch origin main`): `7db649d66e54835ad3dc1b324725251489128215`  
**Reviewed head:** `1537636f53cc24184a16e7a044f066d7e43f2ac4`  
**Baseline:** `read_ledger_history` absent on main (`git show d0f14c62544daca98258cbf68a5e1e3bef54ab74:engine/rotation_events.py | grep -c read_ledger_history` → 0).

**PR tests (scratch tree @ 1537636f):** `18 passed, 23 deselected in 0.49s`

## Findings

| n | severity | probe | claim | path:line | repair | re-check |
|---|----------|-------|-------|-----------|--------|----------|
| 1 | MAJOR | a/f | Mode is `RECONSTRUCTED_REPLAY` only when `replayed is True`; missing flag → `RETAINED_LEDGER_UNMARKED` | `engine/rotation_events.py:1415-1418 @ 1537636f` | Document and/or warn in coverage | Probe replay row without `replayed` |
| 2 | MAJOR | f | `ts` after `through` allowed when `asof`/`closed_asof` ≤ `through`; no skew signal | `engine/rotation_events.py:1339-1343 @ 1537636f` | Optional `clock_skew_rows` in coverage | Probe ts after through, asof within |
| 3 | MINOR | e | Duplicates inflate `event_counts`; no duplicate lifecycle metric | `engine/rotation_events.py:1442-1443 @ 1537636f` | Add duplicate count to coverage | Two identical lines → metric |
| 4 | NOTE | L-B | No membership-as-of-observation-date | L0 / `engine/rotation_events.py:1371-1389 @ 1537636f` | none in reader | #8432 / #8486 |

## Probe a — replay vs retained-unmarked

```python
# SCRATCH @ 1537636f — fixtures from tests/test_rotation_events.py
replay = _history_created(replayed=True)
unmarked = _history_closed()
_write_history(ledger, [replay, unmarked])
all_r = read_ledger_history(ledger)
rep_r = read_ledger_history(ledger, mode="replay")
unm_r = read_ledger_history(ledger, mode="ledger_unmarked")
```

**Output:**

```json
{
  "modes_all": ["RECONSTRUCTED_REPLAY", "RETAINED_LEDGER_UNMARKED"],
  "mode_counts": {"RECONSTRUCTED_REPLAY": 1, "RETAINED_LEDGER_UNMARKED": 1},
  "replay_count": 1,
  "unmarked_count": 1
}
```

**Verdict:** HANDLED — native `row` preserved; filters match modes (`engine/rotation_events.py:1419-1428 @ 1537636f`).

## Probe b — malformed before/after boundary

**Before `through`:** bad `asof` on line 2 → `status=INVALID`, `error.code=MISSING_OBSERVATION_CLOCK`, `rows=[]`.

**After `through` (honest pattern):** valid closed row at `closed_asof=through`, future created `asof>through`, malformed line 3 → `status=OK`, `stopped_by=through`, malformed not parsed (`inspected_nonblank_lines=2`, `first_uninspected_line=3`) — matches `test_read_ledger_history_through_stops_before_future_rows`.

**Edge:** junk on physical line 2 immediately after last in-window row (no future-dated row to trigger `through` stop) → `INVALID_JSON` (fail closed).

**Verdict:** HANDLED for consumer “as known at through” when future observations bound the scan; fail closed on corruption already reached.

## Probe c — no backfill

`grep backfill_leg_names` in `engine/rotation_events.py` hits definition `:1493` and `closed_recent` `:1765` only — not inside `read_ledger_history`. Stored `name_en=OLD_EN_LABEL` returned unchanged.

**Verdict:** HANDLED.

## Probe d — through semantics

- Created rows gate on `asof`; closed on `closed_asof` (`engine/rotation_events.py:1323-1326 @ 1537636f`).
- `closed_asof=2026-07-10` excluded at `through=2026-07-05` (stops before later lines).
- `asof == through` included; `closed_asof == through` included.

**Consumer rule:** Display boundary as inclusive on **observation** date, not `ts`.

## Probe e — duplicates

Two identical created lines → `selected_rows=2`, `event_counts.created=2`, same `lifecycle_id`; no duplicate field in `coverage`.

**Verdict:** HANDLED — inflation visible in counts; consumer must recompute distinct keys.

## Probe f — clock skew

| case | status | note |
|------|--------|------|
| `ts` before `asof` | OK | both `recorded_at` and `observation_date` exposed |
| `ts` after `through`, `asof` ≤ `through` | OK | row included; no warning |
| bad / missing `ts` | INVALID | `MISSING_RECORD_CLOCK` |

**Verdict:** HANDLED for dual-clock exposure and fail-closed bad `ts`; no coverage skew disclosure (follow-up finding #2).

## Probe L-A — multi-clock exposure

Envelope: `observation_date`, `recorded_at`, `mode`, native `row` with `ts`/`asof`/`started` (and `closed_asof` on closed). `coverage.first_observation` / `last_observation` are observation-clock on **selected** rows.

**Verdict:** HANDLED.

## Probe L-B — membership cutoff

Returns `from_key` / `to_key` and native leg payload only; no cohort or membership-as-of field.

**Verdict:** UNHANDLED (expected; GMI PIT held elsewhere).

## Probe P1 — provenance

`source_sha256` matches `shasum -a 256`; file `mtime`/`size` unchanged after read; one-byte append changes hash.

**Verdict:** HANDLED.

## Probe P2 — bounds

- `limit=2` with malformed line 3 → `OK`, `stopped_by=limit`.
- `limit=0`, negative, `True`, bad `through` → `ValueError` with typed messages.
- 50k rows: ~1.955s full vs ~0.028s `limit=100`.

**Verdict:** HANDLED.

## Probe P3 — missing / empty / unreadable

`MISSING`, `EMPTY`, directory path → `UNREADABLE`, permission-denied file → `UNREADABLE` (no raise).

**Verdict:** HANDLED.

## Probe P4 — consumer honesty

Truthful from dict alone: `mode_counts`, `invalid_rows`, observation window, per-row `mode` + clocks. **Cannot** support without extra logic: ts/through skew sentence, duplicate lifecycle inflation sentence, membership-as-of sentence.

## GAPS

None — all 12 probes executed; scratch worktree removed (`grep -c wt8470` → 0).
