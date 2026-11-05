# Independent frozen WP02 kernel review — v1

## Verdict

**REQUEST CORRECTION for one confirmed P2: public timestamps finer than a microsecond are truncated before comparison with K.** The frozen v1 module can therefore incorporate a premise strictly after the cutoff into an otherwise complete artificial model. The failure is reproduced through `diagnose`, including an erroneous 1.9-billion-to-2.1-billion modeled capitalization revision. No real-source authority or admission was granted.

The other bounded checks support the implemented research subset: full-quota synthetic selection; a joint INT infeasibility missed by marginal counts; exact residual completion and cut certificates; ties; duplicate model issuers; forward and reverse history reconciliation; same-fact conflicts and explicit corrections; signed share deltas; unit-consistent splits; whole-class completeness; fixed raw policy binding; resource and type refusals; and unconditional real-source holds. These are statements about supplied artificial premises and actual scratch execution, not an eligible issuer population or production-ready selector.

This review does not adopt the forthcoming correction. The principal has acknowledged the P2 and is preparing a separate v2. That source must be reviewed separately. This v1 review, its failed cases and its original requests remain immutable.

## Exact reviewed source and method

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Frozen module `lanes/source_diagnostic_kernel_v1/source_diagnostic.py` | 77,308 | `80b12ec299e861d24c0c23f88805a475f44099af894fbea7d787296c72681d8f` |
| Final `INPUT_CONTRACT.md` | 19,018 | `cea9493577f98f8b57a313f20dd7f79f93095dc1ec38d32e9b0452e97f6ee63a` |
| Author suite, pinned but not executed or adopted as independent proof | 46,432 | `2c9d575614de6e41c1463ff252010e92711b21e8389034df698842c73e59bc05` |
| Author fixture helper, pinned but not imported | 7,312 | `37db957fff940f2e9557e36586c07ee4a1a3ea534d9b3e36a5c96630b1a5aa78` |
| Adopted base policy | 60,312 | `d41422d76219b1c5d3a3c9cbb19a1bc3124433031200b09499033bd4dc30d522` |
| Principal adoption sidecar | 9,593 | `645a20a39842d9c5a03b4ff39a37280d1aa02c32ef545c061d0aa959f06e0016` |

The complete 1,420-line module, including its public entry point and CLI, was read. No author application file was edited. The final contract differs from the independently pinned draft only by the final auditability/resource section: global assertion-ID nonreuse; complete supplied assertion retention and bundle binding; the allowed changed fields for four one-to-one event kinds; and the 8,192-bit derived rational bound. The exact diff and inputs are recorded separately.

The fixed policy composite remains the one previously reviewed: effective canonical SHA-256 `90bec6078348af6e41c9538e12e0443dd37d671c85a7089c64c547f5ce5e7714`; D=`2026-09-30`; K=`2026-10-09T00:00:00Z`; seed=`GMI-WP02-20261009-v1`. Its sole normative override concerns numeric domains. No quota, date, seed, source-admission interface or original policy file was changed. Exact bytes bind content; they authenticate no actor or source.

The original independent package remains 56 files/601,141 bytes, with its pre-execution manifest and all 41 gzip requests unchanged. Its historical preparation receipt still reports zero API calls. The executions below are later, separately recorded work. No 729-matrix study was rerun.

## P2 R1 — submicrosecond public bounds cross K after truncation

**Location:** `_instant`, source lines 201–214, reached by the anchor, membership-event, assertion, relation and action timestamp checks. It accepts a UTC string ending `Z` and passes it to `datetime.fromisoformat`. Fractional digits beyond microseconds are accepted by the parser but discarded. The subsequent comparison therefore changes the represented instant.

Four byte-bound public calls isolate the error:

| Supplied public bound | Scope | Expected temporal result | Observed v1 result |
|---|---|---|---|
| `2026-10-09T00:00:00.000001Z` | History anchor | Later than K; hold | `POST_CUTOFF_ANCHOR` |
| `2026-10-09T00:00:00.0000001Z` | History anchor | Later than K; hold or explicitly refuse unsupported precision | `ARTIFICIAL_MODEL_COMPLETE`, 120 modeled selections |
| `2026-10-09T00:00:00.000001Z` | Correcting assertion and relation | Later than K; cannot replace the prior 190m measurement | Prior modeled cap **1,900,000,000** retained |
| `2026-10-09T00:00:00.0000001Z` | Correcting assertion and relation | Later than K; cannot replace the prior 190m measurement | New 210m measurement used; modeled cap **2,100,000,000** |

The two fractions are exact positive offsets, 1/1,000,000 and 1/10,000,000 second. Numeric spans, quantities, source-content bindings and membership arrays are otherwise unchanged. The second example alters only the two public-upper timestamps in the original independently frozen post-K correction case. Thus neither an unrelated schema error nor a private parser helper supplies the proof.

**Impact:** the artificial public API violates its fixed K-vintage rule. The cutoff is central to this research kernel even while real-source admission is unavailable. A later trusted data adapter would not correct an internal ordering error. This is a release correction, not a reason to broaden the initial real-source scope.

**Minimum acceptable correction:** require a documented, exact timestamp syntax and explicitly refuse precision the implementation cannot preserve, or implement exact fractional ordering. Never truncate, round, normalize, or silently substitute K. Regression proof must retain the positive/negative controls and cover every public timestamp consumer. Changing only an internal helper test is insufficient.

**Evidence:** `CUTOFF_PRECISION_EXECUTION.json`, 27,250 bytes, SHA-256 `c6a1b192d7f5ad92349bbf522f668fa1ed617799008fdd9d9ab9fc8ce0b94ba0`; exact compressed requests and complete outputs in `cutoff_precision/`; script `RUN_CUTOFF_PRECISION.py`; process-local PID5, command exit0, four calls, no named effect-guard events. The command's success records that reproduction completed; it does not mean the two erroneous model outcomes passed the temporal oracle.

## Actual execution and independent oracles

The review made **77 direct `diagnose` calls and two separate CLI calls**, for 79 actual public invocations. A later output checker made zero API/helper calls. Every input/output is retained and hashed. Neither the author's suite nor its fixture helper was imported or run.

| Execution group | Public calls | Observed evidence |
|---|---:|---|
| Original independently frozen requests | 41 | All intended baseline, mathematical, economic-model and refusal outcomes matched their independent expectations |
| Cutoff-precision reproduction | 4 | Two valid negative controls; two confirmed temporal failures |
| Additional boundary recipes | 27 | Resource/type/identity/revision/count/ordering checks; four fixture precondition errors preserved and corrected separately |
| Corrected recipe inputs | 4 | All four intended arithmetic/event-label paths reached and matched their oracles |
| Feasible INT frame forcing residual exclusions | 1 | Initial flow24, full 120-member model, ten actual failed completion trials |
| Fresh CLI processes | 2 | Exit2 as specified; complete output bytes identical to each other and the original API result plus newline |

The output checker performed **484 explicit checks of the saved public outputs**. This number counts assertions, not independent datasets, economic observations, selector calls or statistical evidence. It independently recomputed quotas, hash ordering, capacity matrices, feasible allocation witnesses and cut capacities. It did not call private kernel helpers or implement/rerun a second selector.

### Selection, ranks and residual flow

The 168-record positive control returned all 42 pools with 2L/1M/1S under the fixed thresholds and a 120-member model satisfying all 5×24, 6×4 and 2L/1M/1S quotas, plus UK8/JP8/EU8. Every candidate retained its absolute capitalization companion tag. Relative L labels did not overwrite MICRO/S_ABS/M_ABS/L_ABS.

The 152-record Hall challenge returned actual INT maxflow18 against target24. Each country and aggregate cell marginal has sufficient capacity, but UK's eight candidates can reach only one cell of demand2. The independently frozen source-side cut has capacity18, and its supplied feasible18-unit witness establishes the matching lower bound. The public response retained a valid deficient cut and no selected cohort. No country reassignment, tie splitting, omission or quota relaxation occurred.

The additional feasible 152-record frame puts UK's eight candidates into four L cells with two each. Its independently checked24-member witness makes joint feasibility explicit. The API rejected ten early JP/EU choices that would consume slots required by UK. For every such actual trial, the independent output checker reconstructed the remaining candidate capacities **after removing the current candidate**, checked the decremented country/cell demands, verified its returned allocation, and recomputed the cut bound below the decreasing target. Successful-prefix completion was verified with the actual final selected suffix as a witness. The last accepted inclusion reached residual target0. This exercises the exclusion branch the balanced example did not reach.

Full record/source/member/partition order reversal preserved the selected ID order, pool values and complete selection result. Original request bindings changed, as they should. Two further fresh CLI children, PIDs6 and7 within their scratch harness, both exited2 and emitted the same 655,244 bytes, SHA-256 `e4b479786716e120d22d1356f9b8d2db3ef120b196eda288414d0d69b10337d4`. The corresponding original canonical API result is 655,243 bytes, SHA-256 `d70f07a0be3cea9425404516fd72998b29bd56b1452862346b260e35d18b24a9`.

### Identity, history, corrections and numeric mechanisms

Duplicate nonnull model issuer IDs in different record/pool positions produced `DUPLICATE_ECONOMIC_ISSUER`; global assertion-ID reuse in distinct components produced `ASSERTION_ID_REUSED_ACROSS_COMPONENTS`. No row was overwritten into apparent uniqueness.

Forward and reverse histories with offsetting admission/removal counts of168 still produced `TARGET_MEMBER_SET_MISMATCH`; the complete differing member sets were exposed. An invalid reverse after-state produced `EVENT_BEFORE_AFTER_STATE_MISMATCH`. A supported conversion with exact separate source arrays completed. Relabeling its instrument change as a transfer produced `EVENT_KIND_CHANGED_FIELDS_MISMATCH`.

Competing190m/210m assertions for the same measurement stayed conflicted, including two assertions by the same publisher without an explicit correcting link. The latest actual measurement date won over a later publication of an older measurement. An explicit same-publisher pre-K correction produced the210m model, while the original whole-second post-K correction retained190m. Retracting the latest required assertion produced unavailable; it did not resurrect an older clean measurement. Complete supplied assertion fields and canonical bundle bindings were retained in the resolution receipts, including explicitly excluded post-K content. They remain unauthenticated claims, not admitted K-time evidence.

The additive −10m/0/+10m examples produced exact modeled caps1.8b/2.0b/2.2b. Removing explicit no-change evidence from zero held the whole cap. A stale pre-split quote was divided by the exact factor, yielding 200m shares×5=1b; omitting the price bridge caused a typed hold. An unpriced second class held the whole issuer rather than yielding a partial-class cap. Persistent shares, ADR/proxy/zero-or-ceased class semantics remain typed unsupported paths, not completed implementations.

The derived-rational test used a price divided by32 factors of `(10**47+1)`, with an independently measured D share count. One class's exact denominator needs4,997 bits and succeeds. Adding a second class with the coprime factor `(10**47+3)` requires a9,993-bit denominator in the sum. The API emitted `EXACT_ARITHMETIC_BUDGET`, preserved a null whole cap and withheld model selection. No rounding, partial sum or ambient integer-string failure substituted for that boundary.

### Bounds and count distinctions

The actual byte API accepted the valid positive control at exactly2,097,152 input bytes and exactly262,144 bytes for one supplied source, and refused the corresponding +1 cases for the intended limits. A513-record request was1,130,740 bytes/136,918 lexical tokens, below the other principal gates; it reached the512-record refusal. Seventeen assertions reached the16-per-bundle refusal. JSON duplicates at top and nested levels, invalid UTF-8, nonfinite numbers, bool/float numeric roles,13-digit JSON integers and nonpositive price inputs were refused or held through their intended codes.

Depth24/25 and lexical-token160000/160001 controls specifically checked parser progression. At the allowed boundary, processing reached a later typed invalid-count hold; at +1 it stopped at `JSON_DEPTH_LIMIT` or `JSON_NODE_LIMIT`. These are parser-boundary controls using deliberately invalid count values, not claims of complete valid inputs at those structural depths.

Missing, null, explicitly not-published and supplied-zero source totals stayed distinct. Not-published continued only with the separately supplied exhaustive counts; supplied zero against168 records was an explicit mismatch. All remain supplied counts, with source truth unverified.

Two expected code labels initially guessed by the reviewer for altered raw policy/adoption bytes did not match the implementation's shared `FROZEN_POLICY_BINDING_MISMATCH` code. The actual scope distinguishes policy/adoption correctly and fulfills the required fixed-byte refusal. This is an expectation-label correction, not a kernel defect or a hidden rerun.

## Preserved failed fixture preparation and proof limits

The first arithmetic recipe accidentally kept the baseline Sep15 share date while declaring an empty share bridge. The first membership-event recipe changed the anchor while reusing its target source ID. The resulting `EXPLICIT_BRIDGE_EVENT_SET_MISMATCH` and `RAW_TO_PARSED_RECONCILIATION_MISMATCH` are correct early refusals, but they **do not test the intended downstream arithmetic/event-label conditions**. All four original requests, outputs and initial expectation metadata remain in `boundary_recipes/`. Separate corrected requests change the share coordinate to D or give the anchor its own exact source binding. Those four later public calls reached the intended branches. The null expected-code marker in the initial positive recipes is not counted as a passed semantic oracle.

The 8 MiB whole-output refusal was read in `_finish`, but no supported public request was demonstrated to reach that branch. This is explicitly **NOT EXERCISED**, not a passed output-budget test. The review does not claim exhaustive hostile-input fuzzing, every unsupported class/persistent transition, complete real calendar/source semantics, or a full real source frame.

The first vector stdout log contains39 case summaries although its completed execution receipt and all41 complete hashed outputs are present and subsequently verified. The later receipt/output closure is the execution evidence for all41; the short log is retained unchanged and is not represented as complete.

## Authority, operational boundary and remaining external prerequisite

Every observed response retains `STRUCTURAL_ONLY`, `NOT_READY`, `NOT_ADMITTED`, false authority flags and null real population, pool, capitalization, quantile, cohort, F and INT-flow fields. Both all-true self-attesting claims and a synthetic mode label fail to change these states. Real/default mode does not expose a synthetic cap/selection object. Genuine case counts, independent review, pre-vendor order and rights remain unverified; empty or artificial stress labels do not fulfill the actual30/6-per-stratum requirement.

The first kernel intentionally has no real-source adapter. A supplied coherent receipt cannot authenticate itself. **Real-source readiness still requires a principal-bound existing trusted owner-review/admission interface**, with verified identity/perimeter/activity/history/source/entitlement dependencies. Neither this review nor content hashes can mint that interface. The available kernel can validate internal artificial coherence before that prerequisite; it cannot lawfully or empirically establish a complete historical cap frame or actual cohort. The work needed to establish the all-eligible historical rank denominator remains larger than the120 final selections and has no established complete lawful source frame here.

All writes are confined to this review directory. Standard-library scratch execution was used; no native worktree/app/store, Git, provider, source acquisition, stock census or authority registry was touched. Named Python filesystem-mutation/process/socket audit events were denied during module import and all77 direct calls, with zero such events observed. The two explicit CLI children were launched by the review harness; their launches are disclosed rather than included in that guard claim. This is a bounded effect accounting statement, not a universal operating-system sandbox proof.

Every review process reported local PID5 in its separately invoked scratch execution namespace; these reused process-local numbers are not global host identities or native liveness observations. Both yielding execution sessions were reconciled to exit0. The two CLI child exits2 are the documented NOT_READY outcome, not test errors. Exact commands, tool session/exit observations, input/output digests and final source preservation are recorded in the receipt set and manifest.

**v1 finding remains open in this frozen review. STOP for v1.** A separate principal-authorized v2 corrective review follows, without rewriting this evidence.
