# PB-D — T2 × Event Quality research return

Operation: `PB-D-T2-EVENT-QUALITY-20261007`. Date: 2026-10-07.

**Research verdict: numerical discovery reproduced; independent economic-evidence value unvalidated.** The strongest surviving historical candidate is H5 T2 with at least two legacy feature categories. Those categories do not certify independent source roots. This packet completes the reproduction, dependence/clock audit and prospective design. It is **research only, zero signal authority**, and the prospective cohort is **not enrolled**.

## Result at a glance

| Finding | Reproduced result |
|---|---|
| H5 T2 + news | 10/11 SPY-positive; 8/11 absolute-positive; mean SPY excess +3.5813% |
| First qualifying news observation per issuer | 6/7 SPY-positive; 4/7 absolute-positive |
| H5 T2 + ≥2 legacy categories | 10/12 SPY-positive; mean +2.6855% |
| First T2 per issuer + ≥2 categories | 5/5 SPY and sector-positive; 4/5 absolute-positive; mean SPY +3.6627% |
| Same-date lower-category controls | Worse on all seven dates; equal-date gap +4.1879429 pp |
| Concentration | ADM and PRIM contribute 9/12 rows; five distinct issuers |
| Population correction | Original 89/17/5 table uses first-any-tier then T2; actual first-T2 bins are 118/20/5 |
| H10 multi-category result | 4/11 SPY-positive; mean −0.3871%; −2.4196% without INTC; selected control-relative gap remains positive |
| Strongest false lead | Generic first-any-tier convergence: 7/11 SPY wins but mean +0.00146%; T1 multi-category mean negative |
| NVDA news | Six retained items, zero classified positive/negative; all six underlying sentiments null |
| Event-quality edge | Unknown: historical certified materiality/root/expectation labels are absent |
| Future minimum | Fixed 252-session cohort; at least 200 complete first-T2 pairs with distinct issuers in each arm, plus calendar/coverage/support gates; not a power guarantee |

All ten numerical checks and both archive checks pass. Independent arithmetic review used direct PyArrow records and separate aggregation logic. Qualifications, uncertainty and immutable source pins are included below.

## Files

| File | Purpose |
|---|---|
| [PB_D_REPRODUCTION.md](PB_D_REPRODUCTION.md) | Tables, selectors, controls, horizons, source clocks and ten research answers |
| [PB_D_REPRODUCTION_RESULTS.json](PB_D_REPRODUCTION_RESULTS.json) | Full calculations, row records, matching, omissions, intervals and power |
| [PB_D_EVENT_QUALITY_LABEL_SPEC.md](PB_D_EVENT_QUALITY_LABEL_SPEC.md) | Orthogonal three-valued tags, roots, freshness, expectations and corrections |
| [PB_D_PROSPECTIVE_PREREG.md](PB_D_PROSPECTIVE_PREREG.md) | Primary estimand, population, clocks, outcomes, matching, enrollment and decision rules |
| [PB_D_POWER_AND_LIMITATIONS.md](PB_D_POWER_AND_LIMITATIONS.md) | Conditional uncertainty, power, clustering and limitations |
| [PB_D_SOURCE_AUDIT.json](PB_D_SOURCE_AUDIT.json) | NVDA counts/nulls, INTC/PRIM metadata probes and holdings-grade revisions |
| [PB_D_PINNED_SOURCES.json](PB_D_PINNED_SOURCES.json) | Exact input URLs, commits and Git blob identities |
| [PB_D_PB_G_HANDOFF.md](PB_D_PB_G_HANDOFF.md) | Owner-respecting next-build guidance |
| [PB_D_ACCEPTANCE.md](PB_D_ACCEPTANCE.md) | Acceptance, independent review and completion boundary |
| [reproduce_pb_d.py](reproduce_pb_d.py) | Offline hash-locked numeric reproduction |
| [audit_archived_sources.py](audit_archived_sources.py) | Offline hash-locked archive metadata reproduction |
| [fetch_inputs.py](fetch_inputs.py) | Explicit pinned public-GitHub download and byte verification |
| [requirements.txt](requirements.txt) | Exact dependency versions |
| [PB_D_FILE_MANIFEST.json](PB_D_FILE_MANIFEST.json) | SHA-256/Git blob identities for return files; excludes itself |

## Reproduce

Run from this directory with Python 3.12. The verified environment used Python 3.12.14, pandas 2.2.3, NumPy 2.3.5, SciPy 1.17.0 and PyArrow 21.0.0. The only network step is `fetch_inputs.py`; matching existing inputs are verified and reused. It never executes downloaded code.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python fetch_inputs.py --output-dir inputs
python reproduce_pb_d.py --input inputs/retro_grades.parquet --output reproduced/PB_D_REPRODUCTION_RESULTS.json
python audit_archived_sources.py --input-dir inputs --output reproduced/PB_D_SOURCE_AUDIT.json
```

Expected summaries: numeric `claims_equal=10, claims_checked=10`; archive `claims_equal=2, claims_checked=2`. Outputs refuse overwrite; choose a fresh output path each run. Input SHA-256: `61bb8cc6ff0f1cfd14f33ba50fc5ce17db4c93e800f74e307c70c5606ae4f9d7`; Git blob: `b0ee089e86269854b699f4667b47dd10a469374c`. Multiply decimal JSON returns by 100 for percentages/percentage-point gaps. Archive topic readings are explicitly human metadata interpretations, not automated economic-truth labels.

## Delivery boundary and provenance

Fresh branch: `research/pb-d-t2-event-quality-20261007`, created from observed Macro main `007e0cccbd06f089605ba122efc658f406043dd3`. The containing final commit is the exact return/freeze identity. Only `research/policy_behavior/pro_returns/PB-D/` is authored. Source PRs #8495, #8533 and #8560 remain untouched. The draft is for research review; no merge, deployment, production integration or prospective enrollment is claimed.

Protected procedure: Mastermind@`9a24ef2c4b27ac95a4d1f72f5eae1073657cd7c2`, compatible skillpack v1.0.1/bootstrap 1. Commission read head: `7abc3dc596c5a6463effb37422bf9bd34bbdf1ba`; policy packet: `ee86db2c832c73a36837c1240df871700340d6da`; Prophet research: `770918cb266b5d884978e31d61670b4efd789eaf`; event semantics: `cde0219b1040c66cbc8647f86352a25794488528`.

No remote worktree, source lease, incumbent runtime, entry policy or production output was replaced. Native helpers performed bounded read-only audits; they were not Executive dispatches, watchers or background continuation. Future implementation/enrollment requires a separate authorized owner receipt.
