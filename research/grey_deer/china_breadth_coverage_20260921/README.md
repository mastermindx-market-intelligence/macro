# China breadth publication integrity — bounded producer repair

## Outcome and limits
The China collector may no longer qualify a latest observation using historical
availability, unrequested symbols, invalid prices or an undersized moving-average
sample. It must also prove that the inherited calculation retained that latest
observation before writing either its cache or constituents artifact.

The existing runner receives a failed-source result on rejection and preserves
the previous aggregate. A valid result passes through the same store and regional
breadth summary reader. No new data store, calendar, control plane, model weight,
probability table, risk threshold, score, ranking or trade authority is added.
This does not certify whole-frame freshness, change 94 to a chosen number, finish
PR 6989, or establish a production deployment. Parent China dashboard work remains
incomplete.

## Evidence
Base: macro `cf2aae0beefb3e7dbb15e4ec672d8c288492dd13`.
Skillpack: protected Mastermind `3e66e43258f34db240d5bff76f54148c7af84ee4`.
Initial behavioral RED: **9 failed, 2 passed**. Intended failures were missing
coverage rejections and an unrequested symbol counted as the 41st member.
Expanded edge RED: **2 failed, 13 passed**: empty live download TypeError and
40 current quotes hiding only 10 usable moving averages.
Final focused regression: **84 passed**, one inherited Timestamp.utcnow warning.
The 17 new cases include actual `run_adapter`, parquet publication/preservation,
and `breadth_summary`, not just helper-only assertions.

Full regression command:
```sh
python -m pytest tests/test_china_breadth_coverage.py tests/test_china_board_breadth.py tests/test_market_heatmap.py tests/test_breadth_constituents_repair.py tests/test_breadth_split_seam.py -q
```

## Stored-input canary
`real_input_probe.py --source <existing china_search/closes.parquet>` reads one
byte snapshot, selects configured curated names, replaces only network I/O, then
compares the real producer with the unchanged inherited calculation. It writes
only its own receipt and temporary canary directory, not the shared store.
The committed receipt records 1,270 rows, 76 available columns from 82 configured
names, 75 latest quotes and 75 eligible members for both moving averages, with
exact output equality. Its source ends **2026-09-04**. This is genuine stored
input, NOT a fresh September 21 production run and NOT the original collector's
missing `_closes_cache.parquet`. Do not use it to assert today's market breadth.

## Release and integration
The new suite is wired into the existing `china-board-breadth` CI job with its
import dependency. No test or required check is removed. Agent OS validation:
1,163 records, zero errors, 99 existing-store warnings.
Independent admitted review, exact-head hosted checks, merge and real production
collector/status/artifact proof remain separate gates. Do not arm an immediate
native auto-merge while checks are pending. Do not certify the whole dashboard
from this safeguard alone.

Existing shared radar work stays on Draft/HOLD PR **6989**, published head
`d775a6c40c9f12c8411cd87100ac7dbfcd664870`. Its accepted candidate seams are not
rebuilt here. Existing China template writers **7481 / 7485 / 7383** and
act-now writer **7567** are not modified. Keep merged **7156** freshness and
**7463** offline-render repairs. This branch changes no page template or live data.

Continuation: `agentos/handoffs/GREY-DEER-CHINA-MACRO-INTEGRITY-2026-09-21.md`.
