---
key: QUANT-ASSESSMENT-2026-10
title: "Quant assessment 2026-10 — twenty research-reference briefs (Q01–Q20)"
objective: >
  Close the twenty briefs of the 2026-10-08 macro quant assessment package. Each one gets
  a PREREG frozen before outcomes, a pure opt-in reference with synthetic red-to-green
  tests, one dependence-aware comparison on licensed retained local data, an independent
  audit, and a KEEP / REJECT / INSUFFICIENT_DATA verdict, shipped through squash-merge.
  Nothing is wired, promoted or activated.
status: done
program: research-factory
repos: [macro]
owner: chairman
class: research
blast_radius: reversible
ambiguity: specified
owns_paths:
  - research/quant_assessment_2026_10/
waves:
  - id: Q01
    title: "Bid/ask-aware, arbitrage-constrained volatility surfaces — INSUFFICIENT_DATA"
    status: done
    pr: 8730
  - id: Q02
    title: "American-exercise and discrete-dividend pricing/Greek qualification — INSUFFICIENT_DATA"
    status: done
    pr: 8732
  - id: Q03
    title: "Corporate-action-correct off-exchange participation history — KEEP"
    status: done
    pr: 8710
  - id: Q04
    title: "Trade-sign uncertainty and measurement-error calibration — INSUFFICIENT_DATA"
    status: done
    pr: 8717
  - id: Q05
    title: "Option outcome sensitivity to latency, available size and execution cost — INSUFFICIENT_DATA"
    status: done
    pr: 8720
  - id: Q06
    title: "Feasible sparse-data calibration for the existing FS-3 study — REJECT"
    status: done
    pr: 8722
  - id: Q07
    title: "Fitted, leakage-controlled HAR volatility challenger — KEEP"
    status: done
    pr: 8707
  - id: Q08
    title: "Regularized covariance and uncertainty-aware independent-bet counts — REJECT"
    status: done
    pr: 8733
  - id: Q09
    title: "Publication-vintage ATS/non-ATS concentration and venue-change analysis — INSUFFICIENT_DATA"
    status: done
    pr: 8736
  - id: Q10
    title: "Condition-adjusted abnormal off-exchange participation — KEEP"
    status: done
    pr: 8737
  - id: Q11
    title: "Persistent off-exchange activity regimes with explicit detection delay — KEEP"
    status: done
    pr: 8738
  - id: Q12
    title: "Robust option-implied forward and carry-consistency estimates — INSUFFICIENT_DATA"
    status: done
    pr: 8739
  - id: Q13
    title: "Risk-neutral tail-density estimation with quote-uncertainty bounds — INSUFFICIENT_DATA"
    status: done
    pr: 8740
  - id: Q14
    title: "Horizon-matched variance-risk-premium research — REJECT"
    status: done
    pr: 8741
  - id: Q15
    title: "Microstructure-noise-aware realized variance measurement — REJECT"
    status: done
    pr: 8742
  - id: Q16
    title: "Delayed-feedback and regime-shift calibration of existing forecast intervals — REJECT"
    status: done
    pr: 8743
  - id: Q17
    title: "Stable factor whitening under collinearity and missing observations — REJECT"
    status: done
    pr: 8744
  - id: Q18
    title: "Asynchronous-session covariance and lead/lag measurement qualification — KEEP"
    status: done
    pr: 8745
  - id: Q19
    title: "First-passage ambiguity and censoring-aware outcome diagnostics — INSUFFICIENT_DATA"
    status: done
    pr: 8746
  - id: Q20
    title: "Dependence-aware challenger comparison on the existing trial budget — KEEP"
    status: done
    pr: 8747
  - id: LEDGER
    title: "Q01–Q20 ledger + Agent OS records"
    status: done
landmines:
  - "Every module is research-tier and opt-in. Importing one into a producer, page, gate, rank or size path is a promotion and needs the owning program's gauntlet; a KEEP here is not that."
  - "New CI jobs carry if: false plus gate: code; that is the required shape (no duplicate runner), not a disabled marker."
  - "Q04/Q05/Q09/Q12/Q13 (and Q01) are INSUFFICIENT_DATA on licensed retained local data; do not buy or credential a source to re-open them."
do_not_redo:
  - "Do not re-author or re-run any Qnn brief; each verdict is accepted unless new licensed data or a changed contract materially invalidates it."
  - "Do not splice a new variance or outcome label into an incumbent benchmark history; changing a target estimator changes study identity."
  - "Do not wire a KEEP module (Q03, Q07, Q10, Q11, Q18, Q20) into production from this record; route promotion through the owning program."
artifacts:
  - research/quant_assessment_2026_10/LEDGER.md
next_action: >
  None for this workstream. Owning programs may consider the KEEP references
  (Q03, Q07, Q10, Q11, Q18, Q20) under their own promotion gates.
---

## Scope

One workstream for the twenty-brief package; the per-brief evidence lives in
`research/quant_assessment_2026_10/Qnn_*/` and the roll-up is `LEDGER.md`.
