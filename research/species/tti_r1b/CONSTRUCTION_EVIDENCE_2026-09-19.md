# R1-B v4 construction evidence — 2026-09-19

## Capability delta
The frozen v4 rules now have an executable pure candidate/confirmation constructor and a real synthetic JSON/Markdown replay consumer, on the existing #7274 carrier. Previously the branch contained a preregistration and a small specification transcription, not the authoritative constructor. This is BUILT_NOT_PROVEN research construction, not a validated trading strategy or deployed Terminal feature.

`engine/entry_radar/tactical_exhaustion.py` accepts standard five-minute indexed OHLCV and caller-qualified prior close/ATR. It emits forming candidates, actual-time reclaim/continuation confirmations, expiry/unavailable reasons, separate candidate/episode low anchors and first-per-time-bin control anchors. Five-minute processing latency is a scheduled entry CLOCK only; the constructor does not read or claim an entry price/fill.

`python3 scripts/research/terminal_tactical_r1b_preview.py --format markdown` exercises the constructor. Its only inputs are literal synthetic examples and frozen config bytes. The generated SYNTHETIC_CONSTRUCTION_REPORT.md/.json contains no observed market history. There is no market-input command-line option.

## Discriminating tests
40 new TTIB tests cover strict versus equal low, prior displacement/impulse, completed-bar cutoffs, independent selectors, overlapping anchors ordered by actual confirmation time, reclaim-before-continuation/continuation-before-reclaim, exact expiry, full processing latency, control-census independence from future labels, separate low anchors, volume/price/basis/prior-session qualification, timezone conversion, holiday/early-close refusal, zero-range geometry, future corrupt/duplicate mutation and partial-data preservation. Real subprocess tests exercise JSON/Markdown output and reject an attempted market-input flag. An import/I/O guard excludes network, historical-file, registry and event-writer calls from the constructor.

An empty input originally produced an AVAILABLE/no-events report, later gaps also remained AVAILABLE, and a pre-completion request appeared measured. Three adversarial tests failed on those exact behaviors before repair. The engine now reports UNAVAILABLE for no usable data, PARTIAL for late gaps without erasing valid earlier events, and PENDING before the first completed bar. A control-bin test fixture initially failed its own frozen impulse threshold; the fixture was corrected to satisfy the unchanged rule, not by changing the rule.

## Verified results
- Existing full detector suite including the 40 new cases: 192 passed.
- Full existing Live Entry Radar CI-owned test step: 1520 passed, 3 skipped.
- Existing script-import-pinning suite: 11 passed.
- Compilation and git diff check: PASS.
- Owned implementation/test/config hashes were captured before the final full Radar run and matched after it.
- An initial broad-suite attempt was blocked at collection by an omitted tracked app/deploy/update.sh. Materializing app/deploy in this sparse worktree resolved that environment limitation; the complete rerun above passed. No deploy script was executed and no assertion was waived.

The three broader-suite skips are not counted as passes. All 40 new cases executed. Tests are author-run engineering evidence, not independent scientific review, browser proof, production execution or empirical accuracy.

## Frozen scientific boundary
Config SHA256: 24b5a89f8df9c441160f1162c0f08d62796e842e29fff3c55766160fe388bc19.
Prereg SHA256: a8afab8d87cfe912aeaed02c105112869943433cf6b7bb7c765bd2768d0dfcd3.
Both remain byte-identical. TrialLedger unchanged by this slice. Planned grid 60; registered R1-B cells 0; market data reads 0; empirical outcomes 0. No ATR/beta ingestion, matched-control estimates, return/LOD outcomes or probability calibration was implemented here.

## Sequencing and release
Same-carrier Sol ruling #7274 comment 5745472291 narrows the older blanket code wait to the actual empirical/shared-source and release boundary. It allows path-disjoint synthetic construction without altering frozen scientific rules. The code does not import R1-A, alter its shared TrialLedger, change existing production detector identities or create a scanner/store.

R1-A #7270 review/CI, independent review of this construction, lawful full-grid registration before outcomes, qualified empirical adapters and the eventual Radar/Terminal production proof remain outstanding. No live alert, rank, sizing, order or options authority is created. Next work is the gated empirical consumer, not another rewrite of this constructor or the completed arrival-receipt layer.
