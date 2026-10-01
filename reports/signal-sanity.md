# Signal sanity — 2026-10-01

**✅ OK** · 0 failure(s), 1 warning(s)

| board | as_of | records | coverage | status |
|---|---|---:|---:|---|
| standouts (engine buy-board) | 2026-09-25 | 66 | 66 | ⚠️ warn |
| briefing (Phase-5 priority queue) | 2026-09-30 | 25 | 25 | ok |
| radar (divergence radar) | 2026-09-30 | 328 | 328 | ok |
| altdata (alt-data desk) | 2026-10-01 | 30 | 30 | ok |
| news (news flow) | 2026-10-01 | 1253 | 1179 | ok |
| intel_hub (5-desk command) | 2026-09-30 | 30 | 30 | ok |

## Warnings

- standouts: as_of 2026-09-25 is 6d old (> 5d)

_Invariants: coverage floor · score-column degeneracy · content-freeze (as_of advanced but values identical) · staleness · distribution drift. Ground-truth-free — see engine/signal_sanity.py._