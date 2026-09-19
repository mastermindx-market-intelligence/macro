# TTI R1-B status — v4 frozen, no outcomes

**Current execution target:** v4 at `4db8d0edc63997f7f7944c3b35ac04709461b810`. V1 (`0c54e10e...`), v2 (`1348a238...`) and v3 (`1518ef7d...`) are immutable **DO_NOT_RUN** audit artifacts superseded before registration/outcome access.

V4 prereg SHA256: `a8afab8d87cfe912aeaed02c105112869943433cf6b7bb7c765bd2768d0dfcd3`. V4 config SHA256: `24b5a89f8df9c441160f1162c0f08d62796e842e29fff3c55766160fe388bc19`. Grid: **60 cells**. Registration: **false**. Outcomes opened: **false**. TrialLedger modified by R1-B: **false**.

V4 preserves all v3 market thresholds, latency, controls, population and promotion gates while removing two machine ambiguities: there is no global first-event-per-symbol/day gate, and candidate/episode LOD anchors cannot collapse into one singular anchor. Thirteen synthetic/static cases passed without market data.

R1-B remains prereg-only on Macro #7274. Registration/implementation stay held until R1-A #7270 clears current-head hosted checks and independent review. Do not append R1-B trials, open outcomes, alter thresholds, add post-hoc filters, or infer short/HOD symmetry.
