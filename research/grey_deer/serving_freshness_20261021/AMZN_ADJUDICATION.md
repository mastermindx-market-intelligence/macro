# AMZN historical rejection and present-day correction boundary

Programme: MAS-258. Evidence recovered 21 October 2026. **No data correction applied; no historical admission or production action authorized.**

## Finding

The August 11 engine-render execution rejected AMZN's contradictory exhaustive explanation and nevertheless committed it to `main`. This is now supported by the actual workflow/job log, exact checkout and published artifact. A successful outer job cannot be treated as signal-contract admission.

[Execution and source evidence](amzn_historical_execution_20261021.json) retains bounded log excerpts, source/blob hashes and full before/after marker values. [The run](https://github.com/mastermindx-market-intelligence/macro/actions/runs/31452043288) is attempt 1, head `d90753171038dc318e55f71cf441a33db0757b02`; [job 93658213173](https://github.com/mastermindx-market-intelligence/macro/actions/runs/31452043288/job/93658213173) concluded success.

## Execution chronology

All times below are August 11, 2026 UTC.

| Time | Direct evidence |
|---|---|
| 02:20:08 | Checkout cleans and resets the prior shared runner workspace. Initial dirty-file output precedes this reset; it is not evidence that those bytes survived checkout. |
| 02:21:29 | Full checkout SHA is d90753171038dc318e55f71cf441a33db0757b02. |
| 02:21:31 | Pull of main reports already up to date. |
| 02:23:17 | Builder reports 240 ticker outputs, asof August 10, in site/signals and the MTF brain snapshot. |
| 02:23:23 | Validator reports two contract errors: AMZN marker175 and AMZN.last have divergence-led reasons but failed-next-bar-hold primary. The regime engine starts immediately afterward. |
| 03:36:29 | Render commit created locally as 2663c4ab7b. |
| 03:36:32–42 | Fetch advances origin/main to13a234e; the generated commit is successfully rebased. |
| 03:38:08 | Push explicitly records13a234e7f8..210d11aae6 main→main and success on attempt1. |

The actual source checkout and final Git parent are different. Their AMZN files are nevertheless byte-identical: blob `accd347ccf188bba0931bc3ebf40c386ce9b9770`, SHA256 `58ef7011d6cba31a0f35a056b219f260e2c9dc2badf6d4cc1588b64836d4a634`. The published child is blob `28ad955e765618ee7c27bba0f303ffff7b86062e`, SHA256 `723bec24d163f0ef002e8f97cfe185601e5c241342a6642c0f02e5133ccad247`.

[Actual input](https://github.com/mastermindx-market-intelligence/macro/blob/d90753171038dc318e55f71cf441a33db0757b02/site/signals/AMZN.json) · [Final parent](https://github.com/mastermindx-market-intelligence/macro/blob/13a234e7f88e5b2e50dcf324acbb254ea20b5438/site/signals/AMZN.json) · [Published child](https://github.com/mastermindx-market-intelligence/macro/blob/210d11aae688bd2ce4f40937cc8636562d0135f4/site/signals/AMZN.json).

## Exact transition and cause

Both parent and child contain176 markers. Only marker175 changes.

| Field | Actual checkout / final parent | Published child |
|---|---|---|
| date / type | 2026-07-31 / buy | unchanged |
| anchor era | sq-abs-session-2026-08-06 | unchanged |
| quality | block | unchanged |
| primary reason | veto: bearish divergence | failed next-bar hold |
| reasons | divergence veto; failed next-bar hold | unchanged inherited array |
| signal_date | 2026-08-04 | unchanged |
| confirmed_date | null | 2026-08-10 |
| recorded_at | null | unchanged |

Document asof advances August5→August10; refinement and date-backfill counters each increase by one. The marker is within the existing refinement window. The historical merge updates the primary but retains its old companion. The contemporaneous non-divergence producer uses the schema's omitted-array singleton representation. The contemporaneous validator rejects the contradictory output.

The merge, producer and validator files are byte-identical between actual checkout d9075317 and final parent13a234e. The builder explicitly reads the existing ticker file and then calls merge_payload. Restored cache paths do not include site/signals. Together with checkout/reset, this supports the predecessor attribution; no independent runtime digest of that read was emitted.

The workflow's recompute step uses `set +e`, annotates a nonzero module return, and ends `exit 0`. Its later publication stages `site/`. The same nonblocking wrapper remains in the inspected October21 Macro pin9664943. This is a distinct publication defect from the merge defect repaired prospectively by [#9957](https://github.com/mastermindx-market-intelligence/macro/pull/9957).

The logs do not include full byte hashes of every transient validator input. The supported conclusion is that this run rejected the stated AMZN contradiction and subsequently pushed the identified commit containing that contradiction. Do not claim that every transient file exactly equals its final published counterpart, or that the generated data/ brain snapshot was committed by this site-only lane.

## Narrow present-day correction proposal — unapplied

At inspected current base `96649436590c5d25f503eac90a74c2379e4f8a8e`, AMZN has blob `f65420895d69de6d0dc63f740b429afa6abb8f9c`, SHA256 `53448cd7760dd270e3a01ccb2d1801382989af0c6d644c817ca2afd0e8095f40`. Its July31 marker exactly equals the rejected published marker. The local available history preserves that same marker across203 file-changing versions after the shallow boundary.

The reviewable proposal removes only its inherited `reasons` field, preserves `block / failed next-bar hold`, and uses the producer-era singleton representation. The complete proposed before/after is in the JSON evidence. It preserves the market date, signal_date, confirmed_date, recorded_at:null, anchor era and PIT counters.

This is a substantive explanation correction. It would make a currently invalid marker pass that portion of the schema; unchanged quality alone does not prove unchanged downstream eligibility.

Before application:

1. Reconcile current source/writer state and fence the exact current base, blob and complete target row. Refuse an unexpected predecessor.
2. Record a present correction clock, the complete original value and this historical rejection. Never imply the corrected account was known or admitted in August.
3. Identify consumers that would become able to read the corrected file. Prove historical grading/backtests cannot use latest corrected bytes as an August observation. Git vintages and a PIT note alone do not protect a latest-file consumer.
4. Obtain separate exact correction review and acceptance. The C3 historical consultation and forward source fix are not this acceptance.
5. Retain original artifacts and rejection intervals. Do not relabel recorded_at or confirmation dates to manufacture causal availability.

Historical run recovery is not an absolute prerequisite to reviewing this narrower correction; uncertainty must travel with it. Here, AMZN's actual rejection/publication is now recovered. The remaining consumer boundary still prevents application.

## Other five records and history scope

[The six-row history](mtf_history_candidates_20261021.json) covers a bounded first-parent scan since July20, maximum400 file-changing commits per ticker, at Macro9664943. All requested local scans completed; none hit the cap. **The repository is shallow at69268b06502cdbfb9cdf9ae24e6e64663b17c8ed, August23.** Its real GitHub parent is fab0a94929174b899387df83aafcde5d05325ff4. An earliest local malformed row is not a first introduction.

| Ticker | Market date | First malformed candidate within available scope | Prior file-changing candidate | Interpretation |
|---|---|---|---|---|
| AMZN | July31 | Local boundary69268b; actual earlier transition210d11a recovered above | Actual execution checkoutd9075317; final parent13a234e | Actual validator rejection and publication bound. |
| EQIX | August13 | Local boundary69268b | Not available locally | Pre-boundary transition and execution remain open. |
| GOOGL | August26 | 0da39b480dc2ff8799c3a5a489e883de3d35b1c4 | 78198eeb7a583b3fb02eb6a49d1b64f294a81ce6 | Candidate transition, not run admission. |
| HST | October8 | 2f7f702ed60b32cf7971c0b00609eeb715e62f14 | f6e47389af8ce3d1e6e0eadb6c289d550e3b82b5 | Candidate transition, not run admission. |
| KMI | August31 | 5d675b38c3cf0418065c300b76d0377615a06fce | 3119171478a7cd9cd851687cf24e8bf0c271cdc4 | Candidate transition, not run admission. |
| MU | September17 | c4b705de8f29da0faf6676999effde31d9a81931 | 7f95fd99223eaa0007aa0e737cf0a86bb2b4cd17 | closingbell candidate; do not assume engine-render execution. |

A preceding file-changing commit is neither necessarily the final Git parent nor the actual runtime input. AMZN's finding must not be generalized as historical admission for these other rows.

## Immediate publication-gate acceptance target

The Macro workflow owner must qualify a narrow repair that prevents contract-rejected signals from reaching publication. The scope must cover actual generated signal bytes and every subsequent mutation before the publication boundary, including rebase/restoration. A failure must be observable and must not acquire a green acceptance label through an outer `exit 0`.

Preserve the nightly's ownership of canonical data/ artifacts. Do not solve a site-only publication error by granting this render lane a new data-writer role, relaxing the validator, discarding frozen contradictions, manually dispatching a producer, or modifying protected research eligibility.

No workflow implementation was changed by this evidence update. The source-owner reconciliation and exact follow-up implementation review remain open.
