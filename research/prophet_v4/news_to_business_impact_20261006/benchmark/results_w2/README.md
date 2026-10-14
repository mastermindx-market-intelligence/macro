# News-impact benchmark, wave w2: two-family labeling results (commission D)

This is the commission D return (`package/MASTERPLAN.md` §11). Two inexpensive model
families labelled the graded draw in `../graded/`, and a small stronger-model audit scored
them. The scoring rules are `DEC:NEWS-IMPACT-W2-BENCHMARK-SCORING`. The body source and
rights rule are `DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE`.

Authority is `context_only`. Nothing here ranks, sizes or gates anything. No case was
auto-published.

No source text is stored here. The committed files carry case ids, issuer CIKs, cells,
folds, structured field values, outcome classes and hashes only. The 8-K bodies, the label
returns (whose spans quote the body) and the audit batches stay in the seat's scratch cache.
In `audit/audit.json`, the auditor notes for cards 1 and 27 were paraphrased at commit time
so they quote nothing.

## What the numbers cover

Read these limits before any number below.

- **157 of 600 cases.** The graded population is the body-available frame: T1 68, T2 66,
  T3 23. The shortfall is 443 cases. It comes from where these events are disclosed (most
  tape rows have no 8-K behind them; see `../README.md`). It is printed, never padded.
  Graded metrics hold only for issuers that file 8-Ks.
- **The unit is the critical slot.** There are 293 critical numeric slots: three T1 fields,
  one T2 field and one T3 field per case. Slot rates are not case rates.
- **Two families agreeing is a lower bound, not ground truth.** Where the families
  disagree, at least one is wrong. Where they agree, both can still be wrong. The two
  audits below are the only third-family checks. They are samples (40 slots, then 26
  absent slots in the addendum), not the population.
- **One class was not audited.** `malformed_value` (11 slots) has no audit, so its
  correctness is unmeasured. The addendum audited 20 of the 129 `agree_absent` slots and
  all 6 `absent_reason_differs` slots.
- **The third family is unavailable.** GLM is exhausted until 2026-10-19 05:16Z. The
  registered case gate needs every field to agree, so with two families every case is
  deferred.

## Families and what ran

| Token | Model | Host | Lanes | Cost receipts |
|---|---|---|---|---|
| `fam_a` | MiniMax-M3 | ubuntu1, mb | 10 (lane 02 scored from its re-run `02r`) | none (`USAGE_RECEIPT_MISSING`) |
| `fam_b` | qwen3.7-plus | ubuntu1 | 10 | 9 of 10 lanes observed |
| `fam_c` | cursor | ubuntu1 | 10 offered | all 10 `EXITED_EARLY` (`ECONOMIC_POLICY_REFUSED`) |

Other families were not usable this wave. GLM, Grok and Codex were exhausted, and
oc-free/mimo was blocked by its provider. Lane `fam_a_02` was superseded by its re-run
`fam_a_02r`; only the re-run is scored.

Both families got the same annotation guide and the same case batches: 10 batches of 15 or
16 cases, dealt round-robin by (template, case). The packet changed once mid-wave. Per
family, 64 cases ran on prompt-v1.0 (`tools/label_batch.template.txt`) and 93 on
prompt-v1.1 (`tools/label_batch.template.v1.1.txt`): fam_a lanes 01, 03–05 on v1.0 and
02r, 06–10 on v1.1; fam_b lanes 01–04 on v1.0 and 05–10 on v1.1. Each return records its
`prompt_version`. v1.1 adds a QUANTITY SLOTS section that restates guide sections 5–6:
value shapes, fixed basis per slot, scale words and "(in millions)" table headers folded
into the value, and which spend counts as T1 `executed_amount`. It changes no guide rule.
The tables below do not separate the versions. Batches 1, 3 and 4 (48 cases) ran v1.0 in
both families and batches 6–10 (77 cases) ran v1.1 in both. Batches 2 and 5 (32 cases) are
mixed: fam_a v1.1 against fam_b v1.0 in batch 2, and the reverse in batch 5. To rebuild a
lane on v1.1, set `LABEL_TEMPLATE=tools/label_batch.template.v1.1.txt` for
`tools/build_label_lanes.py`.

Each lane decided every case from its `source.txt` alone, with no network access and no
web search. Every returned span was replayed against the body by hash
before scoring.

Before agreement, `tools/canon_returns.py` rewrote representation-only shapes in the 314
returns (157 per family): C1 period-absence unwrap 57, C2 period `form` key drop 170, C3
per-share unit 0, C4 ISO unit case 22. It never changes a number, unit dimension,
currency, period component, absence reason or span.

## 1. Error taxonomy

**All critical slots (n = 293).** Agreement is 0.577 (Wilson 95% [0.520, 0.632]). The
disputed rate is 0.423. The worse family is wrong on at least 0.212 of slots.

| Class | Slots | Meaning |
|---|---|---|
| `agree_absent` | 129 | Both families say the value is not stated (addendum audit: 20 sampled) |
| `agree_present` | 40 | Both give the same value |
| `present_value_differs` | 57 | Both give a value; the values differ |
| `present_vs_absent` | 50 | One gives a value; the other says not stated |
| `malformed_value` | 11 | One return breaks the value shape (unaudited) |
| `absent_reason_differs` | 6 | Both absent, for different reasons (addendum audit: all 6) |

The 57 + 50 disputed value slots break down by which part of the value differs. One slot
can differ in several parts.

| Component | Count |
|---|---|
| period | 43 |
| value | 18 |
| basis | 13 |
| unit | 13 |
| absence reason | 6 |
| currency | 4 |
| form (point or range) | 2 |

**The period is the main failure, not the number.** Most disputes are about which fiscal
period a correct number belongs to, or whether the filing states one at all.

**By template and field:**

| Template | Field | Slots | Agreement | Wilson 95% | Worse-family error ≥ |
|---|---|---|---|---|---|
| T1 | executed_amount | 68 | 0.618 | [0.499, 0.724] | 0.191 |
| T1 | incremental_amount | 68 | 0.412 | [0.303, 0.530] | 0.294 |
| T1 | remaining_authorization | 68 | 0.941 | [0.858, 0.977] | 0.029 |
| T2 | stated_amount | 66 | 0.364 | [0.258, 0.484] | 0.318 |
| T3 | stated_quantity | 23 | 0.478 | [0.292, 0.670] | 0.261 |

T2 guidance amounts are the hardest slot. Their disputes are mostly period (21), value
(11) and basis (9). T1 `remaining_authorization` agrees well, but 63 of its 68 slots agree
on absence, which the audit did not check.

**Disagreement direction.** Here each family is scored by the frozen endpoint grader with
the other family as reference. These counts are directions of disagreement, not error
rates.

| Family | Template | Agree | Says absent, other has value | Value differs | Reference unusable |
|---|---|---|---|---|---|
| fam_a | T1 | 134 | 27 | 43 | — |
| fam_a | T2 | 24 | 11 | 31 | — |
| fam_a | T3 | 11 | 5 | 7 | — |
| fam_b | T1 | 134 | 18 | 45 | 7 |
| fam_b | T2 | 24 | 2 | 38 | 2 |
| fam_b | T3 | 11 | 1 | 9 | 2 |

fam_a says "not stated" more often than fam_b, and fam_b gives a differing value more
often.

### Third-family audit

The auditor was the seat model, Opus 5.5, a third model family. It drew 40 slots with seed
20261014 from rows sorted by (case, field): 20 `agree_present`, 10 `present_value_differs`
and 10 `present_vs_absent`. The sample is `audit/sample.json` (sha256 `868ce66e…`, pinned
in `summary.json`). The verdicts are `audit/audit.json`.

| Stratum | Family | Correct | Wrong | Ambiguous | Error rate | Wilson 95% |
|---|---|---|---|---|---|---|
| agreed (n = 20) | both | 19 | 0 | 1 | 0.000 | [0.000, 0.168] |
| disputed (n = 20) | fam_a | 3 | 11 | 6 | 0.786 | [0.524, 0.924] |
| disputed (n = 20) | fam_b | 5 | 8 | 7 | 0.615 | [0.355, 0.823] |

Error rates exclude ambiguous verdicts. Among the 20 disputed slots, 4 are ambiguous for
both families and 3 hit the contract gap below.

**Findings from the audit:**

1. **Two-family agreement on a stated value predicts correctness in this sample.** The
   auditor found no error among the 19 decidable agreed slots. The upper bound of 0.168 is
   wide. Agreed absences are covered by the addendum below. See
   `DSC:NEWS-IMPACT-TWO-FAMILY-AGREEMENT-PREDICTS-CORRECTNESS`.
2. **When the families disagree, usually both are wrong in some part.** The commonest
   pattern is periods. fam_a drops a stated period end or invents a period. fam_b invents a
   period end or a multi-year period, or drops a stated one.
3. **Contract gap: a per-share dividend has no T1 home.** Cards 24, 25, 34, 36 and 39 are
   dividend declarations. T1 `incremental_amount` fixes its basis to `incremental`, and
   guide §5.1 forbids a per-share unit, so a per-share amount cannot be written correctly.
   Both families improvise, differently. See
   `DSC:NEWS-IMPACT-T1-PER-SHARE-DIVIDEND-CONTRACT-GAP`.
4. **Guide gap: "an increase in authorization up to $X".** Card 1 does not say whether $X
   is the increment or the new total. The families agree on the incremental reading, and
   plain English supports a new total. The guide has to rule on this. It is not counted as
   a model error.

### Absent-slot audit addendum

A second audit covered the absent slots the first one left out. It adds strata on top of
the first audit (seed 20261014) and never redraws it.

- **Draw.** Seed 20261015, rows sorted by (case, field) before sampling: 20 of the 129
  `agree_absent` slots and all 6 `absent_reason_differs` slots. The sample is
  `audit/sample_absent.json` (sha256 `819911e4…`). The verdicts are
  `audit/audit_absent.json` (sha256 `14e63889…`).
- **Method.** Each card showed both families' absences and every keyword window in the
  body that holds a number, so a value both families missed would be on the card. As a
  positive control, the same windows covered the agreed span in 40 of 40 `agree_present`
  slots.
- **Agreed absences.** All 20 absences were correct, with 0 shared misses: no body stated
  a value that both families failed to find. Wilson 95% is 0 to 0.161. The reason was
  another matter. On cards 8 and 17 both families wrote `not_stated` where the source
  states a scheduled execution, which guide-v1.1 labels `stated_without_number`. See
  `DSC:NEWS-IMPACT-TWO-FAMILY-AGREED-ABSENCE-HOLDS`.
- **Reason splits.** Of the 6 slots where the families gave different reasons, 2 are
  clear, one won by each family. In both, the losing family cited boilerplate as a claim.
  The other 4 turned on a gap in guide-v1. Cards 23 to 25 turn on whether a scheduled or
  planned execution with no amount is a claim without a number. Card 26 turns on whether a
  qualitative statement of expected effect is a claim about the amount.
- **Guide ruling.** Annotation guide-v1.1 section 6 rules on all three. Scheduled, planned
  or pending execution with no amount is `stated_without_number`. A qualitative statement
  about the slot's own quantity is `stated_without_number`, while a topic mention is
  `not_stated`. Boilerplate never supports `stated_without_number`. Under these rules the
  4 ambiguous cards resolve to `stated_without_number`. The v1 labels are not relabeled;
  the next labeling wave uses guide-v1.1. See
  `DEC:NEWS-IMPACT-ABSENCE-REASON-SCHEDULED-EXECUTION`.
- **Not re-scored.** `summary.json` is unchanged, because the scorer reproduces it byte
  for byte from the first audit. The addendum lives in `audit/audit_absent.json` only.

### Eval receipts

There is one `eval_receipt.v1` per family (`eval_receipt_fam_a.json`,
`eval_receipt_fam_b.json`). Their critical-numeric correctness values come from the audit
sample alone, with cluster bootstrap (9,999 reps, seed 20261012).

| Metric | fam_a | fam_b |
|---|---|---|
| critical_numeric_correctness_all_dispositions | 0.667 (n = 33, [0.50, 0.818]) | 0.750 (n = 32, [0.594, 0.895]) |
| critical_numeric_correctness_auto_published | not evaluable (n = 0; proposed bar 0.98) | not evaluable |
| span_replay_pass_rate | 1.0 (n = 157) | 1.0 (n = 157) |
| disposition_accounting_complete | 1.0 | 1.0 |
| unsupported_ticker_to_supplier_count | 0 | 0 |

No kill fired. Material-event routing was not labelled in this wave, so routing recall is
not reported.

**Span replay.** fam_a returned 1,515 spans and fam_b 1,451. Every span replayed (157 of
157 cases each; Wilson lower bound 0.997). Neither family flagged an injection, and neither
abstained on any case.

## 2. Recall versus cost

| Construction | Slots accepted | Cases accepted | Tokens per case |
|---|---|---|---|
| fam_b alone (qwen3.7-plus) | none | none | 300,318 |
| fam_a alone (MiniMax-M3) | none | none | not measured |
| fam_a + fam_b, agreement gate | 0.577 | 0 of 157 | ≥ 300,318 |
| fam_a + fam_b + third family on disputed slots | — | — | unavailable until GLM resets |

The registered rule accepts no value on one family's word, so a single family accepts
nothing. With two families, 57.7% of slots agree. That would be the accepted fraction if
publication were per slot. The case gate as built needs every field of a case to agree.
No case had every field agree, so it accepts 0 of 157.

The cost-efficient next construction is per-slot acceptance on two-family agreement, with
a third family only on disputed slots (about 42% of slots). That waits on GLM. A switch to
per-slot publication is a contract change for the owner, not a scoring choice.

## 3. Actual token and search costs

**Search cost is zero by construction.** The packet forbids network access and web search.
Every case was decided from its pre-fetched body.

**fam_b (qwen3.7-plus).** Receipts come from the Codex-native session counters, one
session per lane run. Nine lanes covering 141 cases were observed. Lane
`W2_L_fam_b_01_ubuntu1_a3` was excluded because its receipt mixed several session ids.

| Per case | Tokens |
|---|---|
| total | 300,318 (min 186,350, median 314,411, max 408,359) |
| input | 297,755 |
| of which cached | 279,232 |
| uncached input | 18,523 |
| output | 2,564 |

Pooled over the nine lanes: 42,344,869 total tokens and 361,480 output tokens. These counts
include each lane's tool-loop context, not just one prompt and answer. About 93% of input
is cache reads, so the billed cost is dominated by uncached input and output.

**fam_a (MiniMax-M3).** The MiniMax lane mode writes no usage file, so cost is unmeasured
(`DSC:NEWS-IMPACT-MINIMAX-NO-USAGE-RECEIPTS`). The table does not estimate it.

**Audit.** The 40-slot audit ran in the seat's own session. It has no separate receipt.

## 4. Calibration

There is no model confidence to calibrate. `DNR:KILL-LLM-CONFIDENCE` forbids using it, and
the labelers were not asked for one. Instead, `summary.json` → `calibration_by_proxy_cell`
reports agreement by the draw's market-reaction proxy cell. The aim is to see whether the
labels behave differently on events the market moved on.

| Template | Proxy cell | Slots with a value | Agreed | Disputed |
|---|---|---|---|---|
| T1 | positive | 51 | 99 | 48 |
| T1 | negative | 12 | 15 | 12 |
| T1 | ambiguous | 6 | 15 | 6 |
| T1 | no_change | 5 | 5 | 4 |
| T2 | positive | 42 | 18 | 29 |
| T2 | negative | 7 | 2 | 5 |
| T2 | ambiguous | 9 | 4 | 7 |
| T2 | no_change | 1 | 0 | 1 |
| T3 | positive | 10 | 9 | 9 |
| T3 | negative | 2 | 0 | 2 |
| T3 | ambiguous | 1 | 0 | 1 |
| T3 | no_change | 2 | 2 | 0 |

The agreed counts include agreed absences. Outside T1 positive and T2 positive the cells
are too small for any reading. No pattern by proxy cell is claimed.

## 5. Burst and defer behavior

**Event bursts.** The graded draw spans 61 event days with at most 9 cases on one day
(2026-08-05). The routing draw spans 82 days with at most 18 on one day (2026-09-15 and
2026-09-30). One labeling wave absorbs either burst. Labeling ran as a batch, not against
arrival time, so these are load figures, not latency figures.

**Defer.** All 157 cases are `routed_pending_third`. None was auto-published. A case
defers when any field is disputed, and the third family is unavailable.

**Lane admission** (events in the admit-drain log):

| Family | Host | Offered | Admitted | Refused | Exited early |
|---|---|---|---|---|---|
| fam_a | ubuntu1 | 9 | 8 | 1 | — |
| fam_a | mb | 1 | 1 | — | — |
| fam_b | ubuntu1 | 12 | 10 | 2 | — |
| fam_c | ubuntu1 | 10 | — | — | 10 |

Two lanes were refused at least once, with at most two refusals for one lane. The refusal
reasons were not recorded (3 refusals). The run log also shows 1 SIGSTOP, 3 FINDING
entries and 1 CORRECTION.

## Files

| File | What it is |
|---|---|
| `summary.json` | Everything above, machine-readable (`news_impact_w2_benchmark_summary.v0`) |
| `critical_slots.jsonl` | One row per critical slot: class, mismatch components, both directions' graded values |
| `eval_receipt_fam_a.json`, `eval_receipt_fam_b.json` | `eval_receipt.v1` per family |
| `audit/sample.json` | The 40 audit slots (ids and strata only) |
| `audit/audit.json` | Auditor verdicts per slot, with paraphrased notes |
| `audit/sample_absent.json` | The 26 addendum slots (ids and strata only) |
| `audit/audit_absent.json` | Addendum verdicts and summary, with paraphrased notes |
| `tools/build_label_lanes.py` | Builds the labeling lane trees and packets |
| `tools/label_batch.template.txt` | Lane packet prompt-v1.0 (64 cases per family) |
| `tools/label_batch.template.v1.1.txt` | Lane packet prompt-v1.1 (93 cases per family) |
| `tools/fill_spans.py`, `tools/check_label.py` | In-lane helpers: span hashing and return self-check |
| `tools/canon_returns.py` | Representation-only canonicalisation (rules C1–C4) before agreement |
| `tools/build_audit.py` | Draws the audit sample |
| `tools/build_audit_absent.py` | Draws the addendum sample and runs its positive control |
| `tools/score_benchmark.py` | Produces `summary.json`, `critical_slots.jsonl` and the receipts |

Registration: sampler `ni-sampler-1`, sampling seed 20261014. Bootstrap 9,999 reps, seed
20261012, coverage 0.95. Contract prefix `3edc7139`. Endpoints sha256 `061d1c21…`. Tape
sha256 `bab57401…`. `t_prospective` 2026-10-14T00:00:00Z. Owner status
`PROPOSED-OWNER-FREEZES`.

## Reproduce

The scorer reads only files already on disk. The inputs it needs that are not committed
here (bodies, label returns, agreement output and usage receipts) live in the seat's
scratch cache, because they quote filing text.

```
# one --labels per returned lane directory (20 dirs; fam_a lane 02 is W2_L_fam_a_02r)
PYTHONPATH=. python3 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/canon_returns.py \
  --labels SCRATCH_W2/labels_returned/W2_L_fam_a_01 [--labels ...] --out SCRATCH_W2/labels_canon_full
PYTHONPATH=. python3 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/build_audit.py \
  SCRATCH_W2 AUDIT_OUT
PYTHONPATH=. python3 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/score_benchmark.py \
  --w2 SCRATCH_W2 --bench research/prophet_v4/news_to_business_impact_20261006/benchmark \
  --out OUT --audit research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/audit.json
# addendum: draw the 26 absent slots, then run the window positive control
PYTHONPATH=. python3 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/build_audit_absent.py \
  SCRATCH_W2 AUDIT_OUT
PYTHONPATH=. python3 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/build_audit_absent.py \
  SCRATCH_W2 --control
```

`build_audit.py` also writes `batch_*.txt` audit cards, and `build_audit_absent.py`
writes `batch_absent_*.txt` cards. Both quote filing text and must not be committed. The audit verdicts in `audit/audit.json` are the auditor's, not a
tool's output.

Checked at commit time from the committed tools and the committed `audit/audit.json`:
`score_benchmark.py` reproduces `summary.json`, `critical_slots.jsonl` and both eval
receipts byte for byte, and `build_audit.py` reproduces `audit/sample.json` byte for byte.
`build_audit_absent.py` reproduces `audit/sample_absent.json` byte for byte, and its
control reports 40 hits and 0 misses.

## Next

1. Run a third family (GLM after 2026-10-19 05:16Z) on the disputed slots, under
   annotation guide-v1.1. The `agree_absent` audit is done (addendum above).
2. Get owner rulings on the two remaining gaps: a per-share dividend home in T1, and the
   "increase up to $X" reading. The absence-reason gap is ruled in guide-v1.1.
3. Decide per-slot against per-case publication.
4. Add MiniMax cost capture.
5. Widen the graded frame toward 600 cases where a body source exists.
