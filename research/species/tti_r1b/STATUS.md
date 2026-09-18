# TTI R1-B status — v2 frozen, no outcomes

**Current execution target:** v2 at `1348a238c8fbcb79b617478311f2ce0e1e37d4c0`. V1 at `0c54e10e20c43827802d3d829505f74f57f8eb5f` is an immutable **DO_NOT_RUN** audit artifact, superseded before registration after adversarial prereg review.

V2 prereg SHA256: `23c6d69f40e63e6fca29b25e347a39ddf31c986e85f2e617a7682327a90590b4`. V2 config SHA256: `bb7952eef6f3714c6bae473708889a5a82ac257f2ef53f8f6d1d4a684c035382`. Grid: **60 cells**. Registration: **false**. Outcomes opened: **false**. TrialLedger modified by R1-B: **false**.

V2 preserves all v1 price thresholds while fixing three design defects before empirical use: future selector labels cannot define controls; selector-versus-anchor de-dup/retry semantics are explicit; and confirmation economics/LOD survival retain both candidate-low and pre-confirmation episode-low anchors.

R1-B remains docs/config-only on Macro #7274. Registration and implementation are held until R1-A Macro #7270 clears its current-head shared-source/TrialLedger gate. Do not append R1-B trials, open market outcomes, alter thresholds, add post-hoc context filters, or infer short/HOD symmetry.
