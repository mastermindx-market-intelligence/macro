# TTI R1-B status — v3 frozen, no outcomes

**Current execution target:** v3 at `1518ef7dabc74428bd79e7724f080226381b6fe4`. V1 (`0c54e10e...`) and v2 (`1348a238...`) are immutable **DO_NOT_RUN** audit artifacts superseded before registration/outcome access by adversarial prereg review.

V3 prereg SHA256: `3b3d44979715dcf43b1e71a678c9b263485bdef124abaef959fee60273571aa7`. V3 config SHA256: `62628e9666dda22565c6f6123b80044b86a7fe5ae51f6bd3bd9b6f9915d74bed`. Grid: **60 cells**. Registration: **false**. Outcomes opened: **false**. TrialLedger modified by R1-B: **false**.

V3 preserves the same price-state thresholds while closing four pre-run design risks: future selector labels cannot define controls; selector/anchor de-dup semantics are explicit; confirmation economics and LOD diagnostics preserve both candidate and pre-confirmation episode lows; and every entry/control now waits one full five-minute processing-latency bar after its decision/confirmation clock. Price evidence also requires positive volume.

R1-B remains docs/config-only on Macro #7274. Registration and implementation are held until R1-A Macro #7270 clears the current-head shared-source/TrialLedger gate. Do not append R1-B trials, open market outcomes, alter thresholds, add post-hoc context filters, or infer short/HOD symmetry.
