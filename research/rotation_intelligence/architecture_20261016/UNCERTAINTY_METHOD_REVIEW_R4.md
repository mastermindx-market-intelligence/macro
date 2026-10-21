# R4 uncertainty-method review: precise target, precise guarantee

Date: 2026-10-17. Primary-source method review for the existing sector-allocation architecture; no new model admission, native statistical protocol, live confidence field, feature gate, registry or monitor. This extends L11–L13 in LITERATURE.md with version-sensitive evidence and a concrete consumer contract.

## 1. Do not confuse three questions

These are distinct:

- Is the group's **conditional expected excess return** positive?
- Will its **realized excess return over the chosen horizon** be positive?
- Will it be among the **best three groups** in that cohort?

The first concerns uncertainty about a conditional mean. The second also includes unpredictable future shocks. The third additionally depends on the joint outcomes of competitors. One number cannot silently answer all three.

An executed invented Gaussian witness has conditional mean 0.2, mean variance 0.0025, and independent future innovation variance 1. Its probability that the mean is positive is 0.9999683287581669. Its probability that the next realized outcome is positive is 0.5791621292519206. Neither is a market probability. The difference is pure target/variance accounting, not an empirical claim about sector volatility.

For a stable latent state delta and observations x, Var(Y_future | x)=Var(delta | x)+Var(future innovation), under the stated independence. If the future state is instead independent of the old one, the old posterior mean is no longer its conditional mean; use the new state's actual prior/transition law. Adding arbitrary variance terms while retaining an incompatible predictive mean does not fix a model.

## 2. Selection changes the required calibration

### CAP and its version-sensitive criticism

The official CAP paper by Bao et al., JMLR 26 (2025), proposes selected prediction intervals and conditional/FCR guarantees under specified symmetry and data assumptions. Its published Section 3.2.2 uses an adaptive historical-selection construction; Remark 10 explicitly compares it with EXPRESS. These precise conditions matter more than the word distribution-free. PDF pages 1 and 12 were visually inspected, with the surrounding text and rule read.

Sale and Ramdas, *Online Selective Conformal Prediction: Errors and Solutions* (2025), demonstrate shortcomings in earlier adaptive-selection guarantees and develop exchangeability-preserving alternatives. Their setting uses restricted decision-driven selection and particular calibration independence. The examined earlier CAP rule is not textually identical to the later official paper's rule.

**Disposition:** include the criticism and later formulation in method qualification. Do not claim that a 2024 abstract establishes our guarantee; equally, do not declare the later CAP version invalid merely because an earlier formulation was criticized. Full proof reconciliation and actual financial-data assumptions remain open. No code from either method is installed.

Sources: https://www.jmlr.org/papers/volume26/24-0452/24-0452.pdf (Section 3.2.2, Remark 10, Theorem 11); https://arxiv.org/abs/2503.16809 (Sections 2–4, calibration strategies and conditions).

### Asymmetric selection: PEMI

Zheng and Jin, *Online Selective Conformal Prediction with Asymmetric Rules: A Permutation Test Approach*, arXiv:2602.10018v1 (February 2026), constructs selection-preserving permutation reference sets for broader selection rules. The paper explicitly assumes exchangeability; its application is drug discovery, not sector allocation. It also notes computational limitations of general full-reference construction.

**Disposition:** useful candidate when a real selection rule depends asymmetrically on prior observations. Arbitrary time permutation of serial market data does not inherit the theorem. Before adoption, identify the actual selection event, exchangeable unit, retained feedback and computational bound. Treat absence of a useful finite interval as unavailable—not a precise confidence badge.

Source: https://arxiv.org/html/2602.10018v1 (Assumption 1, Sections 1.3 and 2). Full-text method sections were read; no method implementation or empirical replication occurred.

### Delayed feedback: GAIF / OCTF

Lu et al., *Feedback-Enhanced Online Multiple Testing with Applications to Conformal Selection*, JMLR 27 (2026), incorporates revealed null/non-null feedback. Its theory distinguishes FDR from marginal FDR. The conformal construction has an explicit null-exchangeability condition; Appendix C.1 handles fixed delayed feedback by changing both testing and calibration, using sub-streams and adjusted error levels. The abstract alone is not sufficient for a daily sector model.

**Disposition:** a useful research lead, not a drop-in replacement for the existing TrialLedger, native look budget or evaluator. A single observed positive return does not reveal that an unknown expected-return parameter is truly positive. A realized-event target can supply observable feedback, but that is a different question. Define the feedback event and maturity before considering the method. Time sub-streams here are mathematical index partitions, not authorization for new services or multiple runtime queues.

Source: https://jmlr.org/papers/volume27/25-2123/25-2123.pdf (Sections 2.1–2.2, Assumption 1, Appendix C.1/Corollary 17). Title and delayed-feedback pages were visually inspected; method text was read. No paper performance figures are adopted.

## 3. Concrete changes to the proposed forecast contract

A future qualified forecast needs a **target-specific** probability field, not generic confidence. Its identity must retain:

| Element | Required distinction |
|---|---|
| Target | Conditional-mean sign, realized horizon event, or joint cohort rank |
| Horizon and maturity | Decision cutoff, executable origin, exit and actual feedback-available time |
| Population | All eligible groups versus selected groups; actual cohort and membership version |
| Uncertainty | Parameter, future outcome, measurement, model/specification and out-of-support |
| Selection | Exact ranking/pick rule and what historical information it may use |
| Calibration statement | Marginal, selected, conditional, finite-sample or long-run—never substituted |
| Evidence | Exact method/source version, assumptions tested, support and permitted use |

These are additive requirements for the existing ResearchEstimate/consumer design. They do not change current display-only permissions or create an independent uncertainty service.

The new Gaussian diagnostic proves why target identity is load-bearing. Its oracle covariance model has no fitted-parameter uncertainty and cannot certify a real selected-sector probability. Its 12,000 replications per world reduce Monte Carlo numerical error; they do not supply market history.

## 4. Acceptance cases for a later uncertainty challenger

Before any live or confirmatory use, the incumbent research owner must demonstrate that the same declared claim survives: selecting only extreme forecasts; shared calibration data; a changing selection rule; missing or delayed outcomes; overlapping horizon labels; correlated groups; interval widening; structural breaks; and an empty eligible calibration set. Failed cases cannot be hidden by reporting coverage only among convenient mature winners.

A meaningful comparison reports coverage **and** interval usefulness, selected-set regret and the actual costed decision result. Coverage can be trivially achieved with an uninformative interval. Conversely, a profitable point selector may have unjustified confidence. Neither substitutes for the other.

False discovery rate, marginal false discovery rate, false coverage rate, hit rate and probability of outperforming are different quantities. A value from one cannot populate a field named for another. The native study's hypotheses and error budget remain untouched.

## 5. Architecture choice after this review

Use regularized, source-grounded opportunity estimates as candidates; test joint group relationships where they matter; and qualify the uncertainty layer against the exact selected decision. Do not ship a generic confidence percentage based on posterior mean error, data coverage, LLM opinion or an unexamined conformal claim.

This is a stronger research specification, not another runtime gate or a newly armed forecaster. The original archive-inspection refusal and final-review failure remain separate, unretried effects. No real data, new source access or portfolio action was required for this method review.
