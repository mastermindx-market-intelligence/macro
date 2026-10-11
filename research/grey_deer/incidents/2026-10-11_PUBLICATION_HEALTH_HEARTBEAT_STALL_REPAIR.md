# Publication health: QLedger GH001 headroom and the heartbeat stall-marker repair (O7/T03)

**Program:** `WS:GREY-DEER-RISK-INTELLIGENCE` / MAS-258 · **Operation:** `risk-radar-pullback-20261009`
· **Lane:** O7/T03 · **Seat:** Fable principal, session `da1ad7ad` · **Measured:** 2026-10-11 against
`origin/main` `565d883c2657`.

## 0. Relationship to the held incident note

The 2026-10-08 incident is already written up in held draft PR #8648
(`sol/grey-deer-oct8-pivot-audit-20261008`, head `8473e82a67c9`) at
`research/grey_deer/incidents/2026-10-08_QL_GH001_NIGHTLY_ISSUER_PUBLICATION.md`. That file is not on
main and belongs to the held frontier, so this seat does not write it. This note lives at a distinct
path. It records what changed since 10-08 and the heartbeat repair that the held note proposed "for
the existing heartbeat owner" (its lines 27–45). The continuation handoff's earlier pointer to the
2026-10-08 path is corrected to this file.

## 1. Three issues, three owners

| Issue | What it is | Owner | This seat's act |
|---|---|---|---|
| QLedger GH001 file size | `data/qledger/claims.jsonl` approaches GitHub's 100 MiB per-file limit; one push was rejected on 10-08 | QLedger + nightly source owners (#8042 → #8669 lineage; `research/QLEDGER_CONTINUITY_SOURCE_PLAN_2026-10-09.md`) | measured and routed; no repair |
| #8042 batching | bounds QLedger US nightly scan cost | #8042 owner | routed; not size proof |
| Heartbeat `stalled_since` erasure | a same-day rerun wiped an open stall marker | `scripts/check_ledger_advance.py` (CSP-W6) | repaired in this PR with regression tests |

The held note already says the heartbeat incident is independent of QLedger GH001. This note keeps
the three separate on purpose: a throughput patch is not file-size proof, and a green nightly is not
publication proof.

## 2. QLedger GH001: current headroom

GitHub rejects any single file above 104,857,600 B. `claims.jsonl` blob sizes on main:

| Commit | Committed (local) | Size (B) |
|---|---|---|
| `f3d3210cb5b5` | 2026-10-09 08:33 | 104,403,890 |
| `9eabe65cf44f` | 2026-10-09 23:29 | 104,411,717 |
| `9e4e3f1b4e55` | 2026-10-10 06:35 | 104,465,507 |
| `f71defd249e4` | 2026-10-10 22:46 | 104,468,672 |
| `8b58a9f9fbff` | 2026-10-11 05:59 | 104,521,374 (current at `565d883c2657`) |

Headroom now: **336,226 B**.

- Ordinary growth is about 62 KB per day (+117,484 B from `f3d3210cb5b5` to `8b58a9f9fbff`, about
  45.5 h). At that pace the limit is about five days away.
- A single burst day already exceeded the remaining headroom: +1,016,105 B from 10-08 to 10-09.
  So one heavy night can trip GH001 on any of those days.
- The 10-08 failure (run 37716729584, head `a7220102c116`) was not durable. The file landed on main
  on 10-09, 10-10 and 10-11. Recurrence is a days-scale certainty, not a resolved incident.
- `daily.yml` runs `scripts/backfill_qledger_us` with `set +e` and a non-fatal warning (line ~1797),
  then stages `data/` wholesale. A green `daily` run therefore says nothing about whether
  `claims.jsonl` published.
- Second watch item, same owner: `data/qledger/grades.jsonl` is 76,734,696 B on main.

**Routed, not repaired.** The size partition belongs to the QLedger owner. The repair must keep
native lossless continuity: no truncation, no exclusion, no force push, no alternate store and no
parallel publisher. The continuity plan on main (`research/QLEDGER_CONTINUITY_SOURCE_PLAN_2026-10-09.md`
and `.json`) is an unimplemented, untested design. Custody of that lane is recorded by #8669 as
`ADMISSION_IDENTITY_GAP / UNKNOWN_NOT_EXPIRED`, so this seat starts no second writer.

## 3. #8042 is throughput, not size

#8042 ("[NORTH STAR][W2] Bound qledger US nightly ledger scans", draft, `merge-blocked`) bounds how
long the nightly scan takes. #8669 already records that "#8042 owns batching, not a size migration."
Merging #8042 would not move `claims.jsonl` one byte further from the limit. No acceptance gate in
this program may cite #8042 as GH001 proof.

## 4. Heartbeat stall-marker erasure: reproduced and repaired

`scripts/check_ledger_advance.py` keeps `data/ci/ledger_heartbeat_state.json`. `daily.yml` line 6535
runs it with `--render-happened`, fail-open.

**Production replay.** Both `risk_radar` and `leadership_crack` show the same sequence:

| State commit | `updated_utc` | asof | `stalled_since` |
|---|---|---|---|
| `5df46b62e1ec` | 2026-10-06 14:58Z | 2026-10-05 | none |
| `f2e831e534c3` | 2026-10-07 10:30Z | 2026-10-06 | none |
| `49418b034729` | 2026-10-08 15:05Z | 2026-10-06 | 2026-10-07 |
| `e65335239332` | 2026-10-08 16:17Z | 2026-10-06 | **none** (erased) |
| `f22524b73ab9` | 2026-10-09 12:35Z | 2026-10-08 | none |
| `1a2212fbb53c` | 2026-10-09 16:20Z | 2026-10-08 | none |

The 16:17Z rerun on 10-08 saw the same asof as the 15:05Z run. The same-day guard correctly made it
"not a stall", but the old code treated every non-stall as an advance and cleared the marker. The
asof had not moved. The stall was erased, not resolved.

**Mechanism.** The state update had two branches: stall, or "cleared on advance". A same-day rerun, a
night without a republish, and an unreadable ledger all fell into the second branch. An unreadable
ledger also overwrote the last good asof with `None`.

**Repair.** An advance is now a strictly newer asof only. The marker clears on an advance and nowhere
else; otherwise it carries forward. An unreadable ledger keeps the last good asof. A regressed asof
stays a stall under the existing `<=` comparison. A high-water-mark asof was considered and rejected:
after a deliberate ledger reset it would hold the alarm open indefinitely.

**Regression tests** in `tests/test_check_ledger_advance.py`:

- `test_same_day_rerun_preserves_open_stall`: no second alert today, marker kept, next session
  reports the stall from its original start.
- `test_same_day_rerun_with_changed_ledger_clears_stall`: changed issuer data clears it.
- `test_no_render_night_preserves_open_stall`.
- `test_unreadable_ledger_keeps_snapshot_and_open_stall`.
- `test_regressed_asof_is_a_stall_and_rerun_keeps_marker`: out-of-order asof alerts once, never twice.

Red-first evidence: against the unfixed script the file gives 4 failed / 17 passed. With the repair
it gives 21 passed. The alert path (`push_ops_alert`, type `ledger_stall`) is unchanged.

## 5. Wider proof gap, left with its owner

The held note names three further weaknesses. This PR does not change them:

- `--render-happened` is passed unconditionally, so "the site republished" is asserted, not observed.
- The step is fail-open, so a crash in the detector is a warning.
- Staleness is measured against the previous asof, not against the expected NYSE session.

## 6. Not the refused effect

The held note records a refused publication: operation `gd-issued-warning-artifact-audit-20261008`,
files `scripts/research/risk_warning_issue_artifact_audit.py` and
`tests/test_risk_warning_issue_artifact_audit.py`, result `TYPED_GIT_PRECHECK_REFUSED`. This PR does
not create, move or republish either file. It touches only the heartbeat script, its existing test
file, its house-law registry entry and Grey Deer records. No denied log was retrieved, and no ledger
or control infrastructure changed carrier.

## 7. T03 acceptance

| Gate | Evidence |
|---|---|
| Same-day reruns cannot falsely clear an unchanged issuer stall | `test_same_day_rerun_preserves_open_stall`, `test_regressed_asof_is_a_stall_and_rerun_keeps_marker` |
| Changed issuer data can clear it | `test_same_day_rerun_with_changed_ledger_clears_stall` |
| No truncated ledger, alternate publisher or duplicate job | none created; QLedger routed to its owner (§2) |
| A throughput patch is not file-size proof | §3 |
| Production effect | first trading-day `daily` run after merge writes the state file under the repaired rule; read it with `git show origin/main:data/ci/ledger_heartbeat_state.json` |

## 8. Reproduce

```bash
git ls-tree -l origin/main data/qledger/claims.jsonl
git show e65335239332:data/ci/ledger_heartbeat_state.json
python3 -m pytest -q tests/test_check_ledger_advance.py
```
