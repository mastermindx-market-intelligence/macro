# US Risk Radar Current-Reading Integrity Extract — 2026-09-25

## Why this exists

Legacy Macro PR #7236 was closed unmerged after its surrounding presentation and
integration architecture was superseded. Its closeout identified two safety
semantics still absent from current main: missing eligible evidence is not calm,
and missing current evidence is not recovery. This slice owns only those semantics.

## Eligible-reading honesty

Risk Radar legacy scare arithmetic is unchanged. subscore_series continues to
include display-only legs exactly as before; no weight is removed or renormalized.

Each scare now adds reading_state = AVAILABLE | PARTIAL | UNAVAILABLE plus
display_score and display_band. A scare is UNAVAILABLE for presentation when none
of its structurally eligible, non-display-only registered weight resolves on the
current observation. Its legacy numeric score and band remain in the machine payload,
but the current US Risk Detail scare row shows an em dash, Unavailable / 不可用,
and no score bar. A genuine observed zero with eligible evidence remains 0.0 / calm.

Old payloads already disclosing n_legs_resolved=0 also fail closed in the template.

## Missing-current evidence cannot become recovery

The existing trajectory and de-escalation display context previously called
dropna().tail(...) before verifying a scare resolved today. A current missing
observation could therefore reuse yesterday as warm, faded, or receding narration.

The repair skips a scare from those display narratives when its presentation read
is UNAVAILABLE or its current sub-score is NaN. Past history remains available for
valid current observations.

## Preserved semantics

Unchanged: scare arithmetic and weights; legacy score/band; state resolution and
bands; context gate and conjunction; H5/H10/H21 probabilities; Market-State force
authority; gross factor / leadership cap; calibration, review, and capital policy.
The old risk_presentation.py layer from #7236 was not ported.

## Red-first and owning-suite proof

Five discriminating tests failed on untouched current main. After the bounded
repair all 5 pass. They are enrolled inside the existing hosted Risk Radar review
and Risk Detail suites rather than a new CI plane. A broader owning run across
test_risk_radar, test_risk_radar_review, test_risk_radar_scorecard, Risk Detail,
and the extracted falsifiers passed 187 tests on the exact committed input set.

Python compile and git diff --check pass.

## Numerical equivalence proof

Base and candidate were executed on the same synthetic missing-evidence frame. A
canonical projection compared state/state_ungated/alert, Market-State authority,
dominant scare/top score, conjunction, the full drawdown-probability payload,
context gate, gross factor/cap_leadership, and every legacy scare arithmetic field.

Base SHA-256:
0baf91860d26dbd4cb508d5c6acc5795a8ef46fe57b7806e704c62e23d8e5c6c

Candidate SHA-256:
0baf91860d26dbd4cb508d5c6acc5795a8ef46fe57b7806e704c62e23d8e5c6c

Byte-identical.

The only intentional delta is truthful current-reading presentation and exclusion
of missing-current observations from warm/faded/receding narration.
