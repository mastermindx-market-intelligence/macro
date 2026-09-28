# H1 scientific successor — execution-binding review R2

**Date:** 2026-09-28 UTC. **Operation:** `prophet-frontier-hypotheses-20260926-sol-001`; recovery `prophet-frontier-successor-1-20260928`. Same Chairman-assigned scientific-design successor; parent Sol retains programme decisions. This is a bounded source-to-experiment review, not a new research programme, price/evaluation implementation, model fit, or execution authorization.

**Disposition: ACCEPTED_DESIGN_UNCHANGED / EXECUTION_BINDING_INCOMPLETE.** The conceptual and numerical acceptance request is closed. The immediate deliverable here is a source-bound correction to what the empirical intake must prove, with twelve isolated fictional-data witnesses. Neither missing source evidence nor these witnesses establishes a negative H1 result. No real historical coverage was measured.

## 1. Accepted baseline consumed, not reopened

Parent ruling #6805/5865586990 and Agent OS decision `DEC-PROPHET-H1-SCIENTIFIC-BASELINE-ACCEPTANCE.md` at original records commit `f478898c21962d7a4d17359051d8b1055561ab14` accept R1 specification plus AR1–AR4, originally published at `f05ea4c41c2512a739937839f76664158c75809f`. The two original files remain byte-for-byte unchanged, including their historical PROPOSED flags. The dated acceptance overlay is the present design decision, not permission to run.

Keep the three sleeves; C2−C1/K5/H10; eleven C0 controls; three fixed ridge fits and original objective, units, coordinates, scales, intercept and fallback; original one-fifth weights; complete selected-endpoint rule; accepted 50bp gain /25bp downside /25bp radius resource criteria. Preserve the parent's additional requirements that BOTH block lengths pass their own minimum-span gate and that unqualified data or inference prevents confirmatory rejection as well as acceptance. No parallel risk-policy intervention, H2/H3 fit, altered entry permission, or new threshold proposal is introduced.

Parent's 47 conformance checks, original coordinate/penalty and one-fifth arithmetic, the historical cohort study, #7288's117-case and #8091's seven-step hosted proof were NOT rerun. This review does not inspect their protected market outcomes.

## 2. The new material question and answer

**Question:** Does the supplied native price-provenance requirement, combined with conveniently available Context Vector fields, completely bind the accepted H1 input and denominator contract?

**Answer: no.** The price metadata work is necessary but does not close the candidate-request inventory, paired raw price/volume input, ordinary-industry index or exact feature construction. Existing Context Vector turnover, relay and strongest-theme fields are useful under their OWN definitions, but are not substitutes for these H1 coordinates. Reusing an existing consumer is mandatory; treating different observations as interchangeable is not reuse.

This is an interface finding. It does not authorize changes to legacy reader fail-soft behavior or legitimate production indicators. Source and implementation owners retain their current custody and all earlier refusal boundaries.

## 3. Candidate reader can conceal an incomplete requested domain

At the inspected #8091 source `c72d5d7e5defc9582e032f72fa23a8fc90737aac`, `engine/us_context_vector.py` blob `861dad4fdc7108157eda9ca7ecbbd38fc13abb75`, the supported `load_candidates` reader:

- enumerates only the parts that exist;
- logs an unreadable part and returns other readable parts;
- returns an empty DataFrame for both an absent store and an existing empty store;
- on a failed column projection, attempts a full candidate-part read and reindexes the requested columns, which can yield an explicitly null new field.

That behavior is consistent with the native fail-soft telemetry contract. It is not by itself a bug to remove. It means the returned frame, its length, and its column names do NOT establish the complete originally requested research domain.

### Executed isolated reader witnesses

| Case | Observed result on fictional inputs | Consequence for H1 binding |
|---|---|---|
| R01 | Two requested, readable parts return both fictional rows. | Positive control. |
| R02 | A requested unreadable second part is omitted; first row returns with one warning. | Nonempty return is not a complete request receipt. |
| R03 | An absent requested second part returns the SAME frame as R02, with no warning. | Warnings alone cannot prove expected coverage. |
| R04 | An intentionally one-month request returns the SAME frame. | Intended request scope must be bound independently of output. |
| R05 | Absent store returns untyped empty frame, no warning. | Empty cannot automatically mean observed zero candidates. |
| R06 | Existing empty store returns the SAME empty frame. | Capture/store state must remain separately known. |
| R07 | Old-schema projection falls back to full candidate read and returns the new identity column null. | Column presence is not identity/source qualification. No outcomes were in this fixture. |
| R08 | One returned row divided by returned-row count gives100%; the declared two-row fictional input gives50%. | The returned frame cannot supply its own original coverage denominator. Real missing-part row counts remain unknown unless their original receipt supplies them. |

**Required intake closure:** through the existing candidate/source owner, bind the requested calendar interval and native read request to the expected input inventory, the actual same-generation inputs read, per-input read dispositions, original capture status/counts where actually attested, and typed unknown totals. Obtain inventory through the existing native/source-manifest owner; a science consumer must not create a parallel part globber, data store or source-of-truth ledger. A zero-row capture needs an actual successful-capture receipt, not absence of a file. A missing part must not disappear from expected-session coverage. An unavailable original key count cannot be invented from surviving files or latest rows.

This extends the empirical return's same-read provenance requirement from selected prices to the candidate population; it does not repeat its eight price-expression probes. The existing reader can preserve every value and its fail-soft behavior while the admitted research path refuses an incomplete or unbound request.

## 4. Source fields that must not be silently substituted

The same pinned native file implements `turnover_percentiles`, `theme_pulse_by_ticker` and `relay_features` with materially different definitions from H1. Four new isolated source-function specimens demonstrate the non-equivalence:

| Case | Source-function witness | Binding requirement |
|---|---|---|
| B01 | Two fictional securities have identical own-history share-volume percentiles, but raw price levels2 versus200 give different accepted log median-dollar-liquidity values. | `turnover_pctile_20d` cannot stand in for `log_dollar_liquidity_20` or establish its raw price/volume basis. |
| B02 | The native turnover function drops missing observations and still returns a20-observation rank when only17 of the last20 fictional expected sessions are populated. | A non-null trailing-observation feature cannot certify the accepted complete-session support. Do not change this legitimate legacy field; build H1's exact input from its admitted primitives. |
| B03 | With unchanged overlapping memberships, swapping two theme ranks changes the native selected theme. | Strongest-theme output is not the owner-declared H1 primary group. Without a source-eligible owner primary rule, H1 overlap remains q=0. |
| B04 | The native relay counts an alternate listing of the focal issuer as another ticker; the fictional ex-issuer peers are flat against a flat benchmark. | Ticker exclusion is not economic-issuer exclusion. A relay count is not weighted peer relative-return breadth or acceleration. |

Do not remove or redefine these existing fields. They were not commissioned as H1 features. The counterexamples reject aliases, not their native uses, and do not demonstrate that H1 predicts returns.

## 5. Exact eleven-coordinate dependency closure

The formula is the accepted R1 formula. The entries below are required input roles, not a proposed new canonical schema or claims that the names already exist in a production API. `d` is the declared completed feature session; all numerical intervals are on the bound expected native calendar.

| Accepted coordinate | Primitive support / missing binding that must be supplied |
|---|---|
| `own_rel_5` | Focal and SPY exact endpoint prices d−5,d; compatible basis and source clocks, with required native session coverage. |
| `own_rel_20` | Focal and SPY endpoints d−20,d; same exactness. |
| `own_extension_20` | Focal20 closes d−19…d; ratio to their arithmetic mean. A different extension/Z-score is not an alias. |
| `own_logvol_20` | Focal21 closes d−20…d for20 log returns; population standard deviation, no annualization or gap compression. |
| `log_dollar_liquidity_20` | Twenty same-security, same-session pairs of RAW close and compatible RAW share volume, d−19…d, USD basis. Compute median of daily products, then log1p; not product of medians, share-volume percentile, or adjusted-close times unadjusted shares. |
| `industry_rel_20` | Decision-eligible ordinary-industry assignment and exact owner index I, version/methodology and prices d−20,d plus SPY. A sector label, strongest theme, or convenient ETF is not sufficient evidence of that binding. |
| `industry_rel_change_5` | The SAME I and compatible price construction at d−10,d−5,d plus SPY; no independent selection of a better-performing industry window. |
| `log_peer_count` | Decision-known ex-focal-economic-issuer roster, representative listings and original denominator; accepted encoded absence only with its flag. |
| `peer_price_coverage` | Original fixed owner-weight mass whose peer identity/prices qualify in BOTH windows. Keep unavailable member mass in the denominator. |
| `roster_unavailable` | Derived from the actual original roster/identity/weight receipt; not from whether a convenient current theme is present. |
| `peer_unavailable` | Complement of the full accepted q predicate; preserve reasons, including overlap, insufficient OTHER issuers, and unresolved issuer weights. |

For C1/C2, form B and P from the SAME qualified ex-issuer weights at d−10,d−5,d and the required source support; form raw A=B−P before standardization. This table changes neither the model nor the price reader's precedence. Raw liquidity evidence and return-basis evidence are different input roles and need independently correct bindings, even when they originate in one underlying source object.

The input manifest must identify the ordinary-industry index and paired raw price/volume consumer, not merely a general price namespace. Their absence from the supplied intake is **UNBOUND**, not proof that no suitable source exists anywhere. Parent's existing #7936 Data OS edge and the empirical/B09 owners resolve them. This seat does not select a different source to make the study run.

## 6. Literal chronology: what can be fixed now and what cannot

Fixed now: original key/grain, expected-session accounting, historical60/20/20 allocation or accepted prospective126/42/252 allocation, source-only allocation, strict support purging, AR2 fit cutoff, one formal look and all selection/coverage rules. No parameter or period choice is reopened.

Not supplied: an admissible outcome-redacted source manifest with literal session IDs/timestamps, original decision instants, feature-support witnesses, label support and known-at metadata, original captures, prior-access inventory, accepted source/code/environment/trial/budget and actual B10/B06 callables. Consequently this review does NOT publish invented literal calendar dates, estimate current historical coverage, declare current source infeasibility from the old2/249 census, or claim registration is complete.

### Role-aware binding order

1. Bind the owner calendar and requested source interval INCLUDING failed/empty captures, and the original observation/class/identity receipts. The calendar is not the set of returned rows.
2. Bind primitive numerical supports and their source availability/observation/usable cutoffs. Reference metadata and actual numeric lookback are distinguished; any upstream numerical construction that expands support must be disclosed rather than hidden in a precomputed feature.
3. Derive literal raw partitions mechanically from that manifest, before protected labels. Keep purged records and reasons; never reassign them to another block.
4. Bind training support/known-at to AR2's fixed pre-calibration cutoff. Evaluation labels may legitimately become known later, by the fixed formal look. A universal feature-time cutoff on outcomes is wrong; a later outcome clock does not authorize a later feature vintage.
5. Bind the original decision timestamp tau to the native stamp/fill/mark relationship. A date-only stamp does not establish that the prediction existed before its purported fill. A missing original stamp or session is not resnapped to a convenient bar.
6. Keep planned label support and actual observed support separate. Missing/late observations never shorten the expected calendar or silently move the formal-look schedule. An unresolved planned endpoint is a manifest/registration gate, not permission to use the next available price or delay until the result is favorable.
7. Before the numerical batch, bind the predeclared result domain, actual implementation, environment and existing trial registration; pass execution-bound source-blind review and the native owner smoke. Within the single admitted batch, expose only the declared training labels to the fitting stage, fit once, and seal coefficients/scalers and calibration/test predictions/selections BEFORE exposing calibration/test outcomes to evaluation. No later evaluation information may reach fitting or selection. Failure to establish this stage boundary stops evaluation; it does not authorize a refit, rerun or another trial. Prediction sealing is not a claim that a fitted prediction can exist before its permitted training-label access.

This is an implementation-binding order for the accepted design, not another scheduler or approval engine. Current conceptual approval is not asked for again. Runtime admission is still separate.

## 7. Ready-to-consume owner request

**To the existing empirical successor on #7288, via the same H1 intake:** return one outcome-redacted, source-bound execution package. Use the accepted R1 and parent overlay; do not invent a competing threshold set or incorporate the parallel risk-policy experiment.

The package must contain (a) original requested/captured/read inventory and known/unknown denominators; (b) the eleven-coordinate primitive binding above, including paired raw close-volume and ordinary industry; (c) exact native candidate and grade read interfaces plus B10 fit/prediction callable and source revision; (d) calendar/support/decision/label-known-at and prior-access records sufficient for literal partition binding; and (e) actual rights, release/normal-capture, environment, trial, review and admission/budget receipts. These are attachments to existing registration/evidence ownership, not new stores.

If a required source or callable is genuinely absent or custody-gated, return that exact field/owner/blocker and the already-authorized next repair—not another same-scope price metadata audit. Source implementation can proceed in the correct existing owner while this scientific seat retains interpretation. Do not rerun the refused custody census, proxy it through another worker, or seize another branch to produce this hand-in.

**To parent Sol:** consume this as a new source-binding result beneath the already-accepted specification. Add the candidate-request inventory, raw liquidity pairing and ordinary-industry binding to the current native-input implementation edge; no repeat ruling on50/25/25 is needed. Leave all current production indicator definitions untouched. Full execution-bound independent review is still owed because no actual B10 implementation or dataset binding has been supplied. No reviewer has been dispatched by this seat, and no anonymous/author self-review is claimed independent.

## 8. Evidence class, scope and continuity

Executed commands in the conversation evidence directory:

```text
python reader_visibility_probe.py          8 passed /0 failed
python input_binding_counterexamples.py    4 passed /0 failed
```

Python3.13.5 / pandas2.2.3. The scripts use executable function bodies copied from the permitted native GitHub source, with docstrings omitted, mocked I/O or isolated helpers, and FICTIONAL data. They do not import the entire native module or run a hosted suite. The two full-module download attempts returned no file; no further download was attempted and no unverified module bytes were used. No native-source change, real parquet read, protected grade, fit, bootstrap, H1 known-answer smoke, market result or independent review occurred. These are twelve scoped review witnesses, not twelve new bugs, implementation acceptance, performance or real coverage.

| Artifact | SHA256 |
|---|---|
| `reader_visibility_probe.py` | `9f63921d3576847e1ee52ba53f8dc8ad74b6c1fd7d7930d68bd8756a5edc245f` |
| `reader_visibility_receipt.json` | `682705f67a555438be328c87f1386b3717cd42035bfb42b5cc37170d793196c8` |
| `input_binding_counterexamples.py` | `246a9182746c7e9d9274c9222b557ca1640da532dbab40b0fd30706db10e560d` |
| `input_binding_counterexamples_receipt.json` | `ed77b38a9e59f2a0e0c5e5707be663a04bc5078e2d6b47a5f2399d29db6b5e6e` |

Protected procedure: Mastermind `5c6b010a6157895d4f697548c75263cdff641ea6`, INDEX `94d1af402598894372858793a5b1931019c5fa77`, compatible1.0.1/bootstrap1; continuing execution/review/reconciliation/delegation/closeout read from this pin. Current Macro observation `1690e69040d2c6bea46c2ed1c3c06c51b311732c`; its `lib/dataos/price.py` blob `be127fa853a6aafbf0bcb33b58783316ac972faa` remains vocabulary, not an actual H1 consumer binding. The Context Vector specimens bind the exact existing #8091 candidate source named above, not a claimed production release.

Source custody: same disjoint review branch `review/prophet-frontier-successor1-20260928`, original head f05ea4c41c2512a739937839f76664158c75809f; additive R2 evidence only. Original R1 files, parent #7980, application, empirical, economic and Paper sources remain untouched. No new PR, worker, watcher, source takeover, deployment or financial effect. Original empirical workspace/effect state remains UNKNOWN/PRESERVED; own known writes require same-carrier readback.

Canonical continuing return: #6805/5861635963; parent #6817. **MISSION_COMPLETE:false.** Next phase is actual owner-delivered source/implementation binding and execution review, followed by the admitted empirical/build disposition. These results are recoverable without relaunching the old research or repeating the accepted tests.

### Source references

- Assignment `Prophet_Astra_Scientific_Successor.md`, especially continuing responsibility and source/consumer boundaries.
- Parent acceptance #6805/5865586990; Agent OS decision at f478898c21962d7a4d17359051d8b1055561ab14; parent cumulative #6817/5825588412.
- Accepted specification and review binding at f05ea4c41c2512a739937839f76664158c75809f, blobs076b1513… and58ac4052….
- Empirical source-return #6805/5861747284 and continuing record #7288/5861614361; original-owner request #7936/5865611017.
- Context Vector source c72d5d7e5defc9582e032f72fa23a8fc90737aac, blob861dad4fdc7108157eda9ca7ecbbd38fc13abb75, functions `load_candidates`, `turnover_percentiles`, `theme_pulse_by_ticker`, `relay_features`.
- Data OS vocabulary source1690e69040d2c6bea46c2ed1c3c06c51b311732c, blobbe127fa853a6aafbf0bcb33b58783316ac972faa.
