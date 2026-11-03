# Signal sanity — 2026-11-02

**✅ OK** · 0 failure(s), 1 warning(s)

| board | as_of | records | coverage | status |
|---|---|---:|---:|---|
| standouts (engine buy-board) | 2026-10-30 | 95 | 95 | ⚠️ warn |
| briefing (Phase-5 priority queue) | 2026-11-01 | 25 | 25 | ok |
| radar (divergence radar) | 2026-11-01 | 301 | 301 | ok |
| altdata (alt-data desk) | 2026-11-02 | 30 | 30 | ok |
| news (news flow) | 2026-11-02 | 170 | 170 | ok |
| intel_hub (5-desk command) | 2026-11-01 | 30 | 30 | ok |

## Warnings

- standouts.conviction.composite_z: mean drifted 50% (0.0284→-0.165) vs 2026-10-19

_Invariants: coverage floor · score-column degeneracy · content-freeze (as_of advanced but values identical) · staleness · distribution drift. Ground-truth-free — see engine/signal_sanity.py._