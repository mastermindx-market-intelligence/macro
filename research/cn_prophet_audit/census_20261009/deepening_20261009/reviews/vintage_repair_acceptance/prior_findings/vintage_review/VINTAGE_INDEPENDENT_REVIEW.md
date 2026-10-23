# Independent vintage laboratory review

## Decision

**The empirical evidence is accepted. The fill and retention prototypes require four contract corrections before their guards can be handed off as complete.** The review reproduced all **18 contract checks and 9 benchmark checks exactly**, then exercised **13 additional synthetic counterexamples**. Eleven expose the four contract gaps below; two expose a minor positive-scale guard omission that does not change any retained empirical count.

The reviewed package is frozen by `VINTAGE_MANIFEST.json` SHA-256 **`7ffe548de43b85e2d1f4fc3ab8b06710ffd09c902bbe251ac6a5f517869ba9b3`**. All 18 package files matched the captured identities before and after review. Source/data remain at Macro **`3d90aad6d83152dfeeaf8345bc995826ac9d3139`**. No original source, original latch, production data or completed laboratory file was edited.

The executable challenge is [review_vintage.py](review_vintage.py); exact inputs, outcomes and minimum corrections are in [vintage_review_results.json](vintage_review_results.json). The result deliberately reports `REVIEW_COMPLETE_WITH_CONTRACT_BLOCKERS`; successful execution of the challenge is not acceptance of the challenged guards.

## Accepted evidence and denominators

The 1,948 retained unique latch rows contain exactly 656 changed `(date, ticker)` entries. Their differences were recomputed from prices, and their current-field classifications were rebuilt from the retained adjusted/raw bars. The separately retained prior V4 table at SHA-256 `626aacda09bdef9ba6cd8bb01a3688e445228b48ce63d5496defb07ce0482830` supplies exactly 289 matured episodes across 21 admission dates. Its keys match the vintage package's V4 designation exactly.

| Recomputed class | Changed unique entries | Matured V4 episodes |
|---|---:|---:|
| Stored basis equals current field, while preferred basis changes | 274 | 61 |
| Current raw-plane numerical match on stored basis | 206 | 35 |
| Other same-session revision remains unresolved | 176 | 40 |
| Unchanged entry within tolerance | — | 153 |
| Total | **656** | **289** |

Exactly **136** entries belong to both cohorts. Their union contains **809** keys and exactly **1,618** witness rows, two bounded sides per key. Every stored T+1 session equals its current derivation across all 1,948 rows. The matured V4 cohort has **216 original opens and 73 original HL2 proxies**; all 73 proxies retain the original corrupt-bar flag. One proxy equals the current open within tolerance, explaining why only 72 proxies occur among the 136 changed matured entries.

| Recomputed witness qualification | Changed 656 | Matured V4 289 |
|---|---:|---:|
| Earlier matching source witness | 385 | 239 |
| Only later witness matches | 186 | 33 |
| Neither bounded witness matches | 85 | 17 |
| Total | **656** | **289** |

The preferred matching-witness shapes also reconcile exactly: changed entries have **317 open-only, 179 uniform positive scale, 26 mixed, 49 identical**; V4 has **75 open-only, 28 uniform positive scale, 8 mixed, 161 identical**. Earlier V4 matches alone give **75/19/8/137**, respectively. The review independently checked each witness's exact side of the latch clock and its nearest time among the retained 82 commit clocks; it checked every output-to-input source identity link. The producer's ancestry assertions are retained as producer evidence; this local review did not reread all 3,360 historical Git blobs or rerun their ancestry checks.

The fixed-current-exit accounting decomposes to **+0.009029304238045575 percentage points** in the 289-row mean, with **16 sign changes: 10 winners become losses and 6 losses become winners**. All class contributions were recomputed from the earlier retained V4 rows. The 2,632 total latch-bearing episode rows and 933 changed episode rows remain tied to their hash-bound prior CSV inputs; they are not the unique-entry denominator and were not independently reconstructed from those CSVs in this local review.

All 38 retained benchmark versions are close/volume only. The 58 retained action-title leads cover 42 changed-entry issuers, including 13 with changed matured V4 entries. Their fields contain no verified adjustment factor. The package correctly keeps every representative case's causal attribution `UNVERIFIED`.

These findings support a mechanism-level explanation. **A matching repository bar remains a historical source witness, not a serving or fill receipt. A title containing a distribution or capitalization phrase remains a lead, not a transformation factor.** The package does not upgrade those observations into original economic P&L or executable fills, and this review accepts those qualifications.

## Required contract corrections

### V1 — Bind clocks to the actual mark sessions and anchors

`fill_vintage_contract.py` checks publication against the separately supplied `entry_anchor_at` and checks source availability against grading, but it does not bind those clocks to either endpoint's session. The following all return `ALIGNED_MARK_DIAGNOSTIC`:

- Exit sessions of **October 12**, graded on **October 9**, with an earlier source-availability string.
- Entry marks dated **September 16**, publication on **October 1**, and an unrelated `entry_anchor_at` of **October 2**.
- A nonexistent entry session **September 31** that passes lexical comparison with October 1.

The docstring delegates the entry clock to the calendar owner. That is a legitimate dependency, but the current interface does not validate the dependency and carries no exit anchor clock. The handoff must make the responsibility executable. Use a calendar-owned receipt or resolver for exact market/session/anchor, reject invalid/non-session dates, check the supplied entry anchor against the mark, require grading at or after the exit anchor, and keep publication at or before the actual assumed entry anchor. The smallest compatible addition is an exit-anchor input together with validation of both anchors; an immutable calendar receipt can cover both. Preserve the distinction between source availability at grading and evidence that was available to the original decision.

### V2 — Authenticate existing originals before replay or amendment

`append_event` validates the incoming event digest but trusts every existing ledger object. Changing a stored original from **100 to 80** while retaining the original `event_id`, then replaying the true original, returns the changed 80 record as a successful duplicate. A later correction also accepts that changed object as its target.

A separate counterexample changes only `entry_session` from September 16 to September 17 and appends a **second `original_entry` for the same decision/ticker**. The current uniqueness key includes the mutable entry-session field. Although neither operation edits a production file in this laboratory, these are gaps in the claimed immutable-original admission rule.

Before replay or correction lookup, authenticate prior event bodies, validate prior original uniqueness, and bind the original to the incumbent decision/latch identity. For this one-entry-per-decision contract, the original session is protected content; changing it requires a correction. Keep the existing store owner responsible for durable immutable custody. Revalidating an in-memory list complements that storage proof; it does not replace it.

### V3 — Carry observation quality and exact row/field identity into mark admission

The retention shim correctly refuses **open 9 outside low 4.7 / high 4.9**, while preserving the source observation. Passing that exact retained bar to `mark_from_bar` and then `aligned_excess` produces a qualified diagnostic anyway. The two laboratory components therefore disagree at their connecting interface.

Separately, changing a constructed mark from **100 to 80** without changing its `bar_row_sha256` or source identity is accepted. The comparator neither validates the retained row hash nor resolves the row/field against immutable source bytes.

Keep invalid observations visible, require the opening-quality result at mark construction, and bind the exact source blob, session, field and anchor to the admitted price. A trusted source-row resolver or retained authenticated row can enforce that binding; a free hash string cannot. Validate a mark on deserialization before performing return arithmetic. This correction should remain with the existing price/entry owner and should not create a new price store.

### V4 — Malformed optional OHLC must preserve usable required Close/Volume

The independently fetched pinned native `_extract` accepts all three following frames and retains their exact Close/Volume projection. The candidate raises `TypeError` for each:

- An optional numeric-string open `"4.8"`.
- An optional open token `"vendor-missing"`.
- An optional high token `"vendor-missing"`.

The failures occur in scalar finite checks or range comparisons. They are not a new upstream-data coverage assertion; they demonstrate that optional columns can currently break a formerly usable required observation.

Type-check optional scalars before applying NumPy finite checks or numeric comparisons. Retain the original optional value and emit a named refusal while returning the incumbent Close/Volume projection. The owner should explicitly decide whether numeric strings are refused or parsed. Missing Volume, all missing closes, empty frames and all missing optional fields already behave compatibly in the independent controls. No source call, historical-open fabrication or new collector is needed for this correction.

## Minor guard omission

`collect_vintage_evidence.py::classify_bar` labels both a zero-scale and a negative-scale OHLC transformation `uniform_ohlc_scale`, despite the prose's positive-factor requirement. Require finite positive values/ratios before applying that name. **Every retained actual uniform-scale witness passed an independent positive-factor check**, so the empirical classifications and counts above stand.

## Exact reviewed file identities

All identities are SHA-256. [reviewed_input_identities.json](reviewed_input_identities.json) contains the complete 18-file list with byte lengths and Git blob IDs.

| Reviewed file | SHA-256 |
|---|---|
| VINTAGE_FINDINGS.md | `5b0fd84b01371502ddfdd758a93083d6ce95d8e37e7d76d4281cc68477766f15` |
| fill_vintage_contract.py | `522d81a9d9d647d9a5b1658c5864dc00aea315e871eb91a51060a77869986fbc` |
| verify_vintage_contract.py | `2b07fa2faf58531b653f56a0a086bc35258eff0f90456239a946e136b2cb4450` |
| benchmark_retention_probe.py | `0aefc7ab01204b08af88d6807993647f80dcf2d906e5e8e34d7904be1c9e845c` |
| collect_vintage_evidence.py | `6e1a1d138f2a8101b5500ac815046b254c593954bf82344b6698b60c84bd237d` |
| entry_comparison_rows.json | `25160d291bec91cb7ba6fe77ac1e69ed5043f89f507dd369d4b32d0314c2e30c` |
| historical_witness_rows.json | `aaf1d164616d2cd459774360cc8893d9ae181a56caeaa77b2f2aa05a827805fd` |
| vintage_inputs.json | `e064dcbc17e0081aab26cb079e41f940c2f387fca8c47bf6ff9302043954eac5` |
| vintage_results.json | `0c702ad83845c50c2418ee8c22a522a3701147e1c4d1d62c52cda6b5747c79d3` |

The native benchmark extractor was independently acquired from immutable GitHub source, verified against Git blob **`4324c7299af32abd22380488e86d97abdc552f72`** and SHA-256 **`fddb468e6cb2c6a1bf86235c337d6ad3b52cb34b0702510f3352c91b3e9a3b5a`**, then AST-extracted without importing or running the collector. The producer's benchmark suite was replayed with only its source-read operation redirected to these verified bytes. Both replay JSON files are byte-identical to the producer's retained results.

## Reproduction and disposition

```bash
python -B deliverable/research/cn_prophet_audit/census_20261009/deepening_20261009/reviews/vintage_review/review_vintage.py
```

The executable refuses source-package identity drift and writes only beside itself. It performs the 27 producer checks, nine independent reconciliation/compatibility checks and the 13 additional synthetic counterexamples in under a second on the local runtime. Preserve this review against the exact reviewed hashes. A corrected package needs a fresh independent replay of these counterexamples and updated expected refusals; that replay should determine contract acceptance. Original publication custody, certified basis bridges, real benchmark opening coverage and natural-process production proof remain distinct implementation gates.
