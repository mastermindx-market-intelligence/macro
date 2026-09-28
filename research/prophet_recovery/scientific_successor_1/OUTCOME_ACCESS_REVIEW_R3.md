# H1 R3 — outcome-access boundary review

2026-09-28 UTC. Operation `prophet-frontier-hypotheses-20260926-sol-001`; recovery `prophet-frontier-successor-1-20260928`. Same scientific-design successor reporting to parent Sol. Sole cumulative return: #6805/5861635963. Existing empirical intake: #7288/5866202034. Parent programme: #6817.

**Disposition: accepted scientific design unchanged; direct use of the inspected unrestricted grade reader does NOT establish outcome-blind intake or training-only access. Execution binding remains HOLD.** This is a source-level capability finding and isolated proof, not evidence that a historical experiment was contaminated, a live product is unsafe, or H1 has failed. No protected market outcomes were read.

## 1. What changed and what did not

R1 plus AR1–AR4 remains accepted under #6805/5865586990 and the Agent OS decision at #7980/f478898c21962d7a4d17359051d8b1055561ab14. C2-minus-C1/K5/H10, eleven controls, three ridge fits, coordinates/weights/scales, common C0 fallback, strict selected-outcome rules, and the 50/25/25 pilot criteria are not reopened. The two parent clarifications still govern. R2's population inventory, paired raw liquidity and ordinary-industry requirements remain intact at 0e9a38c5581d8186f6c7a2c76ef2d05560abed23.

The new, bounded question was whether the native label reader can safely support R2's outcome-redacted intake and the accepted fit-before-evaluation sequence. This is different from R2's candidate coverage checks. No earlier fixtures, arithmetic, historical studies, source-release tests or fitted models were rerun to answer it.

Fresh bounded reads found no new empirical, science or parent return after the R2 checkpoint, and no later response on the existing Data OS owner request. Those are checked-carrier observations, not proof of absent workers or globally absent sources. The actual H1 input manifest and B10 callable remain undelivered at the last supplied empirical record.

## 2. Exact native source

Repository: `mastermindx-market-intelligence/macro`.

| Source | Immutable identity |
|---|---|
| Current main observation | 7878cc44564e677057c220fea7f01811ddc32c6c |
| `engine/us_prophet_grades.py` on that main | blob da7d1f625dc3d20431806502d9f36be82973ffa2 |
| Prospective #8091 candidate inspected separately | c72d5d7e5defc9582e032f72fa23a8fc90737aac |
| Same module on prospective candidate | blob 0653dd6fecbdb484557c101a634f2188dacf10a5 |
| Reviewed function | `load_grades(root=None, *, months=None, columns=None)` |

Both displayed function bodies have the same relevant read/fallback semantics. This is not a claim that their whole modules or surrounding release states are identical. Native source only was read; no grade part was opened. The copied standalone function excerpt is hash-bound in the companion exhibits and does not import the production module.

### F1 — final-column redaction is not read isolation

A successful `columns=` read requests only the declared columns. However, the inner `except Exception` retries with `pd.read_parquet(part)` without a column restriction, then reindexes the full frame to the requested columns. Thus an unavailable newly requested metadata column can cause numerical outcomes to be materialized before disappearing from the returned frame. The exception class is broad: the fallback is not restricted to proven schema evolution.

The inspected grade producer names numerical fields `entry_price`, `fwd_ret`, `bench_ret`, `excess_spy`, `fwd_mfe`, and `fwd_mdd`. The fictional tests use `excess_spy`; none is a real financial observation. A clean output schema, no printed outcome values, or null metadata after reindexing does not prove those values were never loaded into the caller process.

### F2 — run-month pruning is not training-domain selection

`months` filters the parent directory of grading-run parts. It does not filter original candidate stamp dates, the native four-field grade key, horizon, board definition, or an accepted train/calibration/test assignment. A single allowed run month can contain several original decision periods and horizons. Conversely, passing the desired stamp month can miss an allowed training row graded later.

Calling the unrestricted reader and then selecting training keys in the returned DataFrame cannot retroactively establish training-only materialization. This remains true even if the final training table is exactly right. This finding does not authorize changing the native grading-run partition scheme.

### F3 — fail-soft output is insufficient as the research refusal receipt

In a fictional test, an outer read guard refused the fallback before any outcome was materialized. The reader's outer `except Exception` caught that refusal, logged a warning, and returned an empty frame. The guard prevented access, but the returned frame alone could not distinguish refusal from healthy emptiness. The registered research path therefore needs the existing owner to preserve a machine-consumed failure/disposition alongside the data; a missing warning inspection must not certify a successful empty study.

F1–F3 are one execution-access problem with a bounded repair surface, not three new programmes or a reason to disable the legacy reader globally.

## 3. Executed evidence and limits

Final command: `python label_access_probe.py`. Python 3.13.5, pandas 2.2.3. Eight isolated native-function cases passed. All file access, store enumeration and logging were controlled test doubles; DataFrame operations used installed pandas. No production module, real Parquet file, market price, actual return or fitted model was loaded.

| Case | Observed fictional witness |
|---|---|
| P01 | Successful metadata-only projection materialized no outcome values. Positive control. |
| P02 | Missing requested metadata triggered full read of five outcome keys; the returned frame still hid the outcome column. |
| P03 | A non-schema projected-read exception also triggered the same full read. |
| P04 | One run-month read returned multiple stamps, H10/H42 and two board definitions. |
| P05 | Post-read exact-key filtering returned one training row after five outcome keys had already been materialized. |
| P06 | Using the stamp month as the run-month selector returned no row and performed no read. |
| P07 | A fictional full-read refusal prevented outcome access but became a warning plus empty frame. |
| P08 | A fixture whose domain was already restricted by its owner materialized only the allowed training key. This is not proof that such a real view exists. |

A separate executed `python key_scope_counterexample.py` produced one passing repair-design witness: filtering each key column independently with an IN list admitted two cross-combinations outside the two allowed four-field tuples. Exact tuple membership admitted only the allowed tuples. This is a warning for the proposed repair, not an allegation that the current native reader implements that flawed filter.

The mocked cases were first exercised with a generic fictional outcome-column label; fixture names were then aligned to the actual `excess_spy` field and internally ordered fictional timestamps. The final eight-case run is the source-bound result above. No calendar validity, market observation or performance is inferred from the decorative fixture dates.

### Real-Parquet confirmation was NOT executed

An additional three-case real-Parquet script was prepared. Its only execution stopped at `import pyarrow` with `ModuleNotFoundError`, before creating a fixture or invoking the reader. One sandbox-local dependency-install attempt for `pyarrow==19.0.1` failed on DNS/name resolution; no successful installation was observed. That optional lane was not retried on another carrier. The dependency failure is not an application defect, native host outage, or evidence that this package version does not exist.

Accordingly: eight mocked function witnesses plus one exact-key counterexample are executed; zero real-Parquet confirmation cases passed or ran. The unexecuted script and failure receipt are labelled separately in the portable package. There is no native integration, independent review, registered H1 smoke, numerical batch or empirical result claim.

## 4. Minimum native-owner closure

The repair belongs to existing US B06/Evaluation and the empirical successor's B10 integration, coordinated by parent Sol. This science seat neither takes that source lease nor introduces a wrapper as a second access authority. Default legacy behavior, frozen grades, the existing writer, run-month storage and numerical definitions should remain unchanged unless the owner separately accepts a change.

**Metadata intake:** use the existing owner to provide a restricted read with an explicit metadata allowlist and immutable source identity. A missing optional field may be represented as a typed null without loading forbidden columns; a missing mandatory field is an explicit unavailable result. An unexpected projection/I/O/schema failure must never widen a restricted read to unrestricted decoding. `columns=None` or a caller-supplied broader list cannot silently inherit metadata-only permission.

**Training:** bind the exact allowed set of native `(stamp_date,ticker,board_definition,horizon)` keys and the accepted support/known-at cutoff before exposing target values to fitting. Do not use run month or a Cartesian product of individually allowed key values as that set. The owner must establish the actual boundary between authorized source preparation and the fit process; filtering after unrestricted values reach the fit process is insufficient. Preserve original excluded/unresolved counts and disclosure without exposing their forbidden numerical labels.

**Evaluation:** release calibration/test values only after the existing registration and admission gates, one permitted training fit, and verification of the sealed coefficient/scaler and prediction/selection artifacts. The seal must bind the accepted model and input generation as well as both prediction sets; a file named sealed is not a receipt. No missing proof may cause a refit, re-selection, broader read or unrecorded retry.

**Failure and observability:** distinguish no rows, incomplete input, refused access and malformed/moved source through the existing result/receipt owner. Record the permitted key/column scope, actual read mode and source generation, stage and parent artifact references; avoid numerical values in metadata-stage logs. An access failure must remain visible to the adjudicator even when the normal data reader is fail-soft.

**Tests before closure:** the native owner must test successful metadata projection, absent metadata, non-schema I/O failure, scope widening, mixed run-month/stamp/horizon/definition, exact tuple membership, refusal-versus-empty, and evaluation-seal enforcement. Verify legacy output/grade immutability and real engine behavior in its admitted environment. These are required acceptance cases, not tests this seat claims have passed.

## 5. Do not overclaim the isolation boundary

There are distinct facts: raw object access; decoding inside an authorized source custodian; values reaching the fitting/evaluation process; values reaching a person or model prompt. The isolated traces establish the function's materialization behavior under the stated fixtures. They do NOT establish a historical human/LLM exposure or a contaminated fit.

If the existing authority permits a trusted custodian to process wider data and emit a restricted view, its scope and non-disclosure proof must be explicit. It must not be presented as a whole-process outcome-blind read. Use existing admission and data owners, not another security service or parallel grade store. An ephemeral source-owned view is only a possible implementation, not a new accepted source or permission grant.

Versioned primary documentation was checked solely for API semantics: pandas 2.2.3 documents column restriction through `columns` and engine-dependent filtering; Arrow 19.0.1 documents column projection and scan filtering, including nested-field prefixes and optional pandas index metadata. Those APIs are not authorization systems. In particular, a filter that removes returned rows does not by itself attest which values were decoded or visible across the declared trust boundary. Documentation is not a substitute for the missing real-engine test.

## 6. Exact next action and stopping rule

Existing empirical successor: consume this R3 addition to the R2 intake and return the exact native restricted-read/fit/evaluation boundary, implementation revision, source manifest and trace evidence, or the named original owner and concrete gate. Do not substitute another metadata report, launch another grader, retry the refused custody census, or run protected labels to test whether the boundary works.

Parent Sol: bind this narrow outcome-access repair to the existing B06/B10/empirical implementation responsibility while maintaining the existing Data OS provenance/volume/industry/population work. The scientific design and numerical tolerance decision remain closed. No additional live entry/rank/holding policy is requested.

Scientific successor: next substantive work is the actual returned manifest/callable/stage-trace adjudication and then interpretation of the one admitted result or measured infeasibility. A new static finding may be reviewed if material, but another unchanged readiness or fixture cycle is not useful progress. Until native delivery, all protected-outcome/model-fitting/source-release lanes remain held. This completed boundary review does not declare the underlying market hypothesis accepted or rejected.

Current protected pin: Mastermind5c6b010a6157895d4f697548c75263cdff641ea6; freshly read INDEX blob94d1af402598894372858793a5b1931019c5fa77, compatible1.0.1/bootstrap1. Same-pin execution/delegation/review/reconcile/closeout procedures previously loaded in this continuing session remain unchanged. Own review-branch preimage0e9a38c5581d8186f6c7a2c76ef2d05560abed23; R1/R2 and all incumbent sources preserved. No worker, watcher, new PR, source release, live policy or financial effect. Original empirical workspace/effects remain UNKNOWN/PRESERVED. MISSION_COMPLETE:false.

## Source references

- Native source identities: section 2; `load_grades` and the same module's `grade_row` numerical-field construction.
- Accepted parent baseline: #6805/5865586990; `agentos/decisions/DEC-PROPHET-H1-SCIENTIFIC-BASELINE-ACCEPTANCE.md` at f478898c21962d7a4d17359051d8b1055561ab14.
- R2 source/return: 0e9a38c5581d8186f6c7a2c76ef2d05560abed23; #7288/5866202034; #6817/5866217617.
- Actual last supplied data return: #7288/5861614361 and #6805/5861747284; parent source-owner request #7936/5865611017.
- Primary API documentation checked 2026-09-28:

```text
https://pandas.pydata.org/pandas-docs/version/2.2/reference/api/pandas.read_parquet.html
https://arrow.apache.org/docs/19.0/python/generated/pyarrow.parquet.read_table.html
```

Complete executed source specimens and hash-bound result summaries are in `EXECUTED_ACCESS_SPECIMENS_R3.md`. Portable scripts and raw fictional traces supplement rather than replace this canonical review.
