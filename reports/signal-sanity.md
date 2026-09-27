# Signal sanity — 2026-09-27

**🚨 FAIL** · 1 failure(s), 0 warning(s)

| board | as_of | records | coverage | status |
|---|---|---:|---:|---|
| standouts (engine buy-board) | 2026-09-25 | 69 | 69 | ok |
| briefing (Phase-5 priority queue) | 2026-09-27 | 25 | 25 | ok |
| radar (divergence radar) | 2026-09-27 | 333 | 333 | ok |
| altdata (alt-data desk) | 2026-09-27 | 30 | 30 | ok |
| news (news flow) | 2026-09-27 | 816 | 693 | 🚨 fail |
| intel_hub (5-desk command) | 2026-09-27 | 30 | 30 | ok |

## Failures (these block publish)

- news: CONTENT FROZEN — as_of advanced 2026-09-26→2026-09-27 but signal values are byte-identical to the prior vintage (builder did not recompute)

_Invariants: coverage floor · score-column degeneracy · content-freeze (as_of advanced but values identical) · staleness · distribution drift. Ground-truth-free — see engine/signal_sanity.py._