# Independent acceptance: coupled vintage contract

**ACCEPTED_BOUNDED_RESEARCH_CONTRACT. No remaining blocker was found within the sealed candidate's stated research scope.** The independent suite passes **86 of 86 checks** and closes **all 13 original V1–V5 variants plus both retained pre-seal interface findings**. The producer's **104-check** suite reproduces with **byte-identical results and fixtures**. No production owner or original evidence file was edited.

Acceptance applies to candidate manifest SHA256 `2ec4ad61150efa1ad01b10137ed3d1a0070ba6412770edc2f4e79a098945eec5` and `contract.py` SHA256 `ea8c3d3da6b3d064563f64e3f78b6e4590530fc51bbe92535cf2cce7e1c2bdef`. Study source remains `3d90aad6d83152dfeeaf8345bc995826ac9d3139`. The exact candidate is retained in `reviewed_candidate/`; prior findings remain intact and their relevant evidence is copied into `prior_findings/`. The independent executable, inputs and terminal results are retained here.

## Findings closed

| Finding | Independent challenge | Repaired disposition |
|---|---|---|
| V1 — endpoint clocks, 3 original variants | Future finalized exit with an earlier source clock; unrelated later caller entry clock; nonexistent September 31 | Named refusals bind the exact calendar session/anchor to source resolution and comparison. An honestly late source still cannot grade a future exit. |
| V2 — stored-original integrity, 3 variants | Tamper an existing original before exact replay or correction lookup; change session to create a second original | Stored hashes are recomputed before fast paths. Stable `(decision_id, ticker)` uniqueness protects the original's entry session. |
| V3 — retained quality and mark identity, 2 variants | Open 9 outside low/high 4.7/4.9; deserialize a mark and change price 100 to 80 with its old row/source identity | The invalid observation cannot become an opening mark. Complete canonical mark comparison repeats source-row/field resolution and rejects the changed price. |
| V4 — malformed optional fields, 3 variants | Numeric-string open, vendor-token open and vendor-token high | Required native Close/Volume remains exactly equal, raw optional values remain unparsed and visible, and the shared validator provides typed opening refusals. |
| V5 — nonpositive uniform scale, 2 variants | Zero and negative OHLC scale | Both return `invalid_ohlc`; a positive-scale control remains recognized. |
| V-R1 — full-blob availability | Exact retained source with an earlier selected row and an unselected finalized future row, including reversed row order | `SOURCE_PRECEDES_FINALIZED_BAR` applies to the whole blob. Its declared availability cannot precede any finalized row's calendar close. |
| V-R2 — strict later-than-original correction | Exact retained equal-time original/correction pair and an equivalent timezone spelling | `CORRECTION_NOT_AFTER_ORIGINAL`; one microsecond later is admitted. |

The stricter repaired interfaces require canonical ticker identities and actual source bytes. Original semantic counterexamples were adapted to those interfaces so that incidental old placeholder tickers or unrelated malformed fields would not mask the behavior being challenged. The two early interface fixtures are reused directly from their retained evidence; the V-R1 payload hash matches exactly. [Evidence: `ACCEPTANCE_RESULTS.json`, `finding_closure` and named checks; `independent_fixtures.json`; `prior_findings/`.]

## The connecting interfaces were challenged independently

The new source fixtures deliberately assign different prices to different sessions and fields. The positive comparison therefore has a checkable independent answer, rather than equal values that could conceal wrong-row or wrong-field selection. Serialized valid marks revalidate. Changing the price, field anchor, session, row hash, basis, adjustment metadata or calendar identity fails. A syntactically valid source digest without bytes, replaced bytes beneath an unchanged digest, a supplied mismatching bar, duplicate source sessions and duplicate JSON fields all refuse.

Boundary clocks are explicit. Publication at the resolved entry anchor is admitted; one microsecond later is refused. Source availability at the final bar's close is admitted; one microsecond earlier is refused. Grading immediately before source availability is refused. A changed calendar receipt invalidates the prior serialized mark, and an anchor from an unrelated date cannot construct the fixture calendar. This proves the candidate's structural relationships using synthetic inputs; it does not prove a real provider clock or exchange calendar.

Ledger tests put damaged content **after** the authentic original that would otherwise match the replay fast path. A later unrelated damaged row, nonobject row, unsupported event kind, shifted duplicate original, duplicate event ID and changed existing correction all refuse. This tests validation of the entire stored list, including unrelated later objects. Authentic correction append preserves the original and caller input list; input objects remain unchanged after both accepted and refused operations. A custody event cannot be used directly as a market mark: the separate source/calendar contract still applies.

The retention seam uses the exact independently verified pinned native `_extract` as its required-field oracle; no collector is imported or invoked. Additional Boolean, huge-integer, missing, NaN, reversed-range and dictionary-range inputs retain the native Close/Volume projection and agree with opening admission. Close-only observations survive with zero fabricated opening marks. Missing required Volume remains unavailable under the same incumbent extractor. [Evidence: `accept_vintage.py`; interface, retention and custody checks in `ACCEPTANCE_RESULTS.json`.]

## Empirical evidence remains unchanged

All **1,332 present** source-witness bars reproduce their prior shape classification. The complete retained witness table still has **1,618 rows**, including unavailable witnesses. These are the full two-sided witness comparisons, not the preferred-match or unique-entry denominators used elsewhere.

| Present witness classification | Count |
|---|---:|
| Identical OHLC | 418 |
| Open-only rewrite | 636 |
| Uniform positive OHLC scale | 226 |
| Mixed-field revision | 52 |
| Total | **1,332** |

The 226 actual uniform-scale witnesses independently satisfy finite positive values and a consistent positive factor. Causal attribution remains `UNVERIFIED`; scale resemblance is not a certified corporate-action transformation. All **1,948** retained entry rows have equal stored and current T+1 session fields. This review rechecks those retained equalities; it does not claim a new calendar derivation. The earlier accepted 289-row price-accounting analysis, original latch values and outcome classifications were not recalculated or altered. [Evidence: empirical checks in `ACCEPTANCE_RESULTS.json`; unchanged hashed `entry_comparison_rows.json` and `historical_witness_rows.json`.]

## Required wording and implementation qualifications

**Entry-session correction is deliberately narrow.** The append fixture demonstrates separate declared price/basis corrections while retaining the original identity, including `entry_session`. It refuses a different entry session both as a second original and as a correction. It does **not** implement general replacement-session migration. If a legitimate future date correction is required, an explicitly named replacement-session field and its semantics must be designed through the incumbent owner. No candidate edit is needed to establish the current narrower acceptance; the handoff should carry this qualification. All 1,948 retained current rows have unchanged T+1 dates, so no migration is needed to preserve this evidence.

**Strict correction chronology means strictly later than the referenced original.** The fixture permits independent corrections to be appended in an order different from their recording times, as long as each is later than the original. It does not define a total correction-time ordering, a latest-correction view or a fold that replaces the original. Those behaviors must not be inferred from the append checks. This is an executable scope observation, not a failure of the stated later-than-original rule.

**Hash validation is content integrity, not external authenticity.** The candidate detects damage relative to retained event IDs. A wholly replaced history whose content and hashes are rewritten consistently cannot be detected by this in-memory list alone; the independent control demonstrates that boundary. Trusted original identity, durable append-only custody and atomic write/read behavior remain the existing store owner's responsibility. Likewise, hashing the source blob proves which bytes were used, not who produced them or when they first became available.

**The JSON codec and finite calendar remain synthetic.** The finite calendar validates date/anchor structure; a supplied Sunday session can be represented, which makes clear that actual exchange-session truth must come from the incumbent calendar owner. The JSON codec is not a proposed production source or second store. Implementation must bind actual immutable Parquet bytes and genuine basis, availability and calendar receipts at the existing owners. This research cannot manufacture missing historical opening data, historical publication custody or a verified `.SZ` basis bridge.

**The output remains a mark diagnostic.** Every comparison is `ALIGNED_MARK_DIAGNOSTIC` with `MARK_ONLY` status. Source availability is checked at grading and need not establish what was knowable at the original decision. Actual fills, original economic P&L, total return, transaction costs and serving/publication authenticity remain separate evidence requirements. A legacy HL2 proxy receives no invented execution timestamp.

These qualifications are consistent with the sealed design and do not require another broad research sweep. The implementation session needs concrete adapters and natural lifecycle verification at the existing owners, followed by these same discriminating checks. This acceptance does not authorize a new price store, ledger owner, ranking policy or production deployment.

## Reproduction and terminal evidence

Run `python -B accept_vintage.py`. The script verifies exact candidate and external-input hashes, loads the unchanged candidate functions, redirects only the producer suite's input/output roots, compares the producer output byte for byte, executes the independent challenges and writes its results in this directory. Its terminal run exited **0** with **86 passed, 0 failed, 104 producer tests and 15 closed findings**. `verify_manifest.py` checks the sealed artifact identities without rerunning the experiment.
