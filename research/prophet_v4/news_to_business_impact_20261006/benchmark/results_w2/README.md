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
  disagree, at least one is wrong. Where they agree, both can still be wrong. The three
  audits below are the only third-family checks. Two are samples (40 slots, then 26
  absent slots in the addendum), and the malformed-slot addendum covers all 11
  `malformed_value` slots. None of them covers the population.
- **Audit coverage by class.** The absent-slot addendum audited 20 of the 129
  `agree_absent` slots and all 6 `absent_reason_differs` slots. The malformed-slot
  addendum audited all 11 `malformed_value` slots. Each of those is a fam_a prompt-v1.0
  return that wrote a quantity period as null.
- **The third family is unavailable.** GLM is exhausted until 2026-10-19 05:16Z. The
  registered case gate needs every field to agree, so with two families every case is
  deferred.
- **The labels measure extraction from the attached filing, not the headline's event.**
  The routing check addendum found that 25 of 40 sampled cases (0.625, Wilson 95%
  [0.470, 0.758]) do not pair a material event with a filing that reports it. Every
  agreement, audit and eval-receipt figure here says how faithfully the families read the
  attached 8-K. None says whether that 8-K is the event the headline reported. About 59 of
  the 157 cases (from 38 to 83 at the interval ends) are on-event.

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
`tools/build_label_lanes.py`. The next wave runs prompt-v1.2
(`tools/label_batch.template.v1.2.txt`), the packet that carries annotation guide-v1.2
(see the malformed-slot addendum).

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
| `malformed_value` | 11 | One return breaks the value shape (audited in full: malformed-slot addendum) |
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
   `DSC:NEWS-IMPACT-T1-PER-SHARE-DIVIDEND-CONTRACT-GAP`. Guide-v1.2 section 5.4 rule 5
   now gives these slots one label in the current contract: a per-share-only dividend is
   an absence with reason `stated_without_number` and a `template_defect` note, and an
   aggregate dividend amount fills the slot. The per-share value itself still has no
   home until a later contract version.
4. **Guide gap: "an increase in authorization up to $X".** Card 1 does not say whether $X
   is the increment or the new total. The families agree on the incremental reading, and
   plain English supports a new total. It is not counted as a model error. Guide-v1.2
   section 5.4 rules 3 and 4 now decide it: "increase to $X" makes $X a new total, the
   increment is `stated_without_number` unless the source states it separately, and an
   unclear "increase up to $X" is read the same way with an `ambiguity` note. Nothing is
   subtracted. See `DEC:NEWS-IMPACT-GUIDE-V12-T1-AMOUNT-RULES`.

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

### Malformed-slot audit addendum

The 11 `malformed_value` slots were audited in full, with no sampling, so this addendum
has no seed.

- **Cause.** Every malformed slot comes from one return shape. Under prompt-v1.0, fam_a
  wrote the `period` of a present quantity as null in 11 of 60 present quantities, and the
  frozen grader cannot use a null period (rule Q1). Under prompt-v1.1, fam_a wrote 0 null
  periods in 83. fam_b wrote none under either version. `tools/build_audit_malformed.py
  --census` prints the period shapes by family and prompt version. See
  `DSC:NEWS-IMPACT-MINIMAX-V10-NULL-PERIOD`.
- **Counterfactual.** Reading each null period as a `field_absence.v1` `not_stated`
  period, the 11 slots re-grade as 6 `agree_present`, 3 `present_value_differs` and 2
  `present_vs_absent` (`audit/regrade_malformed.json`, sha256 `fb37207e…`). This is a
  diagnostic only. The scorer leaves a null period malformed on purpose, and
  `summary.json` is not re-scored.
- **Verdicts.** The verdicts are `audit/audit_malformed.json` (sha256 `82819ab2…`). All 6
  counterfactual agreements were correct. Of the 5 disputes, fam_b was right in 3 and
  fam_a in 0. The other 2 are a guide gap (M1, a centre plus or minus a tolerance) and a
  routing mismatch (M9; the routing check addendum traces it to issuer resolution). All 3
  fam_a errors are non-standard T1 actions: an amendment of existing loans with no new
  money (M4), borrowing capacity written as an authorization remainder (M5), and a share
  count written where a preferred offering's liquidation amount belongs (M6).
- **Routing.** Cards M3, M7 and M9 carry a filing that does not fit their template: a
  notes offering under the strategic/product template (M3), a commercial paper program
  under the demand/guidance/contract template (M7) and an earnings release under the
  strategic/product template (M9). This bullet first read that as a template fault. The
  routing check addendum below corrects it: in none of the three was the template wrong.
- **Guide ruling.** Annotation guide-v1.2 rules on the four gaps here and on the two the
  first audit left open. Section 5.4 adds eight T1 amount rules: what a new program, an
  increase by an amount and an increase to an amount each put in the slots, the reading
  of an unclear "increase up to", per-share-only dividends, borrowing capacity,
  amendments, and preferred offerings. Section 5.1 adds plus-or-minus notation, and
  section 4 rule 2 adds the bound words for a stated maximum or minimum. The lane packet
  that carries guide-v1.2 is prompt-v1.2. The v1 labels are not relabeled. See
  `DEC:NEWS-IMPACT-GUIDE-V12-T1-AMOUNT-RULES`.
- **Not re-scored.** `summary.json` stands under `DEC:NEWS-IMPACT-W2-BENCHMARK-SCORING`.
  The addendum lives in `audit/regrade_malformed.json` and `audit/audit_malformed.json`
  only.

### Routing check addendum

The malformed-slot audit found three cards whose filing did not fit the template. This
addendum checks, on a sample of the whole graded draw, whether each case pairs a real
event with a filing that reports it. It labels routing only. It re-grades no slot.

- **How the draw routes.** `tape_draw` picks the template from headline patterns, takes
  the issuer from the first headline token that resolves to a ticker, and attaches up to
  three qualifying 8-Ks (items 1.01, 2.02, 7.01, 8.01) that the issuer filed in the
  session window. Nothing checks that an attached filing reports the headline's event.
- **Sample.** 40 of the 157 graded cases (seed 20261016, case ids sorted), plus the three
  cases behind cards M3, M7 and M9 (`audit/sample_routing.json`). The seat read each
  headline against its attached filings and classed the case (`audit/routing_verdicts.json`):
  `MATCH` (the headline reports an event of the routed template family at the resolved
  issuer, and an attached filing reports it), `NO_EVENT` (the headline reports no issuer
  event), `OTHER_EVENT` (the event is real and the issuer is right, but no attached filing
  reports it) and `WRONG_ISSUER` (the resolved issuer is not the headline's subject).
- **Result.** 15 of 40 are `MATCH` (0.375, Wilson 95% [0.242, 0.530]). The other 25
  (0.625, [0.470, 0.758]) are 15 `NO_EVENT`, 7 `WRONG_ISSUER` and 3 `OTHER_EVENT`.

  | Template | `MATCH` | `NO_EVENT` | `OTHER_EVENT` | `WRONG_ISSUER` |
  |---|---|---|---|---|
  | T1 | 7 | 8 | 3 | 0 |
  | T2 | 7 | 7 | 0 | 3 |
  | T3 | 1 | 0 | 0 | 4 |

- **Causes.** The `NO_EVENT` headlines are commentary (7), market reports (5), a list, a
  quote page and a solicitation (1 each). The `WRONG_ISSUER` cases are another company as
  the subject (2), a named partner (1), a private company (1), a private company whose
  name collides with a listed one (1), a one-letter ticker (1) and a common-word ticker
  (1). The 3 `OTHER_EVENT` cases are real events with no attached filing about them.
- **The template was not the fault.** M3 is `OTHER_EVENT`: the headline reports a product
  expansion and the attached filing reports a different event. M7 is `NO_EVENT`: the
  headline is a price-quote page. M9 is `WRONG_ISSUER`: a one-letter ticker resolved to an
  unrelated issuer. The failures sit in three draw steps: event detection, issuer
  resolution and body attachment.
- **Automated flags are not enough to gate on.** `tools/build_routing_check.py` computes
  three flags from codes alone: no template-family pattern anywhere in the attached body,
  issuer name and ticker both absent from the headline, and a T1 or T3 case whose only
  qualifying item is 2.02 (earnings). Together they flag 20 of the 40 cases with precision
  0.85 and recall 0.68 against the verdicts. They miss 8 of the 25 off-event cases, and the
  cases they let through are 12 of 20 `MATCH` (0.60). Across the 157 they flag 0.446.
- **Agreement does not imply on-event.** Of the 10 sampled slots where both families
  agreed on a present value, 4 sit on cases that are not `MATCH` (2 `NO_EVENT`, 2
  `WRONG_ISSUER`). Two families can agree exactly on a figure from a filing about
  something else.
- **Ruling.** The labels and `summary.json` stand. Their reading is narrowed to
  extraction from the attached filing (see "What the numbers cover"). The 600-case
  continuation adds three gates to the draw before any labeling: a non-event headline
  filter, an issuer-resolution guard and a body-to-event match check. See
  `DEC:NEWS-IMPACT-CONTINUATION-ROUTING-GATES` and
  `DSC:NEWS-IMPACT-W2-ROUTING-MOSTLY-OFF-EVENT`.
- **Not re-scored.** The addendum lives in `audit/sample_routing.json`,
  `audit/routing_verdicts.json` and `audit/routing_check.json` only.

### Routing gates validation addendum

The routing check led to three gates that run, in order, before any case is labeled
(`engine/news_impact/routing_gates.py`, version `ni-routing-gates-1`, frozen at commit
`a8f98d21`). This addendum runs the validation `DEC:NEWS-IMPACT-CONTINUATION-ROUTING-GATES`
registered before the gates were built. It labels routing only. It re-grades no slot.

- **The gates.** G1 drops a headline that carries no issuer event: a market report, a
  quote page, a solicitation or commentary. G2 drops a case whose resolved issuer the
  headline does not name, whose ticker is ambiguous (one letter or a common word, with no
  registrant name beside it), or whose headline is about someone else. G3 drops a case
  whose attached filings carry none of the routed template's family language, and a
  results headline with no attached item 2.02 filing. The gates never read `proxy_cell`.
- **Pool and sample.** 235 w2 candidates have an attached body. The 43 cases the routing
  check classed trained the gates and are left out. Of the other 192, the gates keep 97
  and drop 95. The seat drew 40 gated-in and 20 gated-out cases (seed 20261017) and read
  them as shuffled cards that did not show gate status (`audit/sample_gates.json`). The
  classes are the routing check's four (`audit/gate_verdicts.json`).
- **Bars, fixed before any card was read.** Gated-in: at least 34 of 40 `MATCH`.
  Gated-out: the estimated share of real events (`MATCH` cases) that the gates drop is
  0.20 or less.
- **Gated-in: MISS.** 32 of 40 are `MATCH` (0.80, Wilson 95% [0.652, 0.895]), two short of
  the bar. Without the gates the routing check found 15 of 40 (0.375). None of the 8
  misses is `WRONG_ISSUER`:
  - 2 report an event of another family: a product offering routed to capital allocation,
    and a launch of something other than a product routed to strategic/product. Neither
    headline reports an event of its routed family, so both are classed `NO_EVENT`.
  - 3 are headline shapes G1 does not catch: a market report, a quote page and a
    solicitation (`NO_EVENT`).
  - 3 are `OTHER_EVENT`: the attached filing carries the family's language, but about a
    different event.

  | Template | Gated-in | `MATCH` | `NO_EVENT` | `OTHER_EVENT` |
  |---|---|---|---|---|
  | T1 | 13 | 10 | 1 | 2 |
  | T2 | 22 | 20 | 2 | 0 |
  | T3 | 5 | 2 | 2 | 1 |

- **Gated-out: PASS.** 3 of 20 are `MATCH`. Weighted by pool size, the gates keep about
  77.6 real events and drop about 14.2, a share of 0.155. The bound interval [0.054,
  0.351] combines the two arms' Wilson bounds, so it is wide. All 3 dropped real events
  are T2 cases cut by `g3_no_family_language`: the filing reports the event in words the
  family pattern does not match. The other 17 are 6 `NO_EVENT`, 6 `OTHER_EVENT` and 5
  `WRONG_ISSUER`.
- **T3 is the weak family.** 2 of 5 gated-in T3 cases are `MATCH`. 3 of the 6 gated-out
  T3 cases are `OTHER_EVENT`: a real product or partnership event that no attached 8-K
  reports. No gate can keep those, because the body does not report them.
- **The frame binds harder than the gates.** The 97 gated-in pool cases are 36 T1, 54 T2
  and 7 T3. At each family's sampled `MATCH` rate they hold about 28 T1, 49 T2 and 3 T3
  on-event cases, and the 43 training cases add 7, 7 and 1. Reaching 200 per family on
  8-K bodies alone therefore needs a frame about 6× wider for T1, 4× for T2 and 50× for
  T3. The T3 figure rests on 5 sampled cases.
- **Limit of this audit.** The auditor is the seat, which also wrote the gates. The cards
  hid each case's gate status, not the auditor's knowledge of the rules. No second auditor
  read the same 60 cards, because the GLM, Grok and Codex lanes were exhausted.
- **Ruling.** `ni-routing-gates-1` is not accepted as an on-event guarantee. It stays in
  the draw as an efficiency filter, and every scored continuation case still carries its
  own routing verdict. A revised gate set is frozen before a fresh validation on cases no
  card has shown, under the same bars. T3 cannot reach 200 on 8-K bodies, and its
  shortfall is printed. See `DEC:NEWS-IMPACT-ROUTING-GATES-1-MISS-PATH` and
  `DSC:NEWS-IMPACT-ROUTING-GATES-1-VALIDATION`.
- **Not re-scored.** The addendum lives in `audit/sample_gates.json`,
  `audit/gate_verdicts.json` and `audit/gate_validation.json` only.

### Routing gates 2 validation addendum

The gates-1 ruling called for a revised gate set, frozen before a fresh validation on
cases no card had shown and judged against the same two bars. That set is
`engine/news_impact/routing_gates_2.py`, version `ni-routing-gates-2`, frozen at commit
`5baa4b10`. Gates-1 stays frozen and byte-reproducible beside it. This addendum labels
routing only. It re-grades no slot.

- **What changed from gates-1.** G1 adds patterns for the market report, quote page and
  solicitation shapes gates-1 missed. G3 reads the event kind the headline names and adds
  two codes. `g3_template_sense` drops a product sense of "offering" under T1, and under
  T3 a launch of something other than a product or an equity sales agreement.
  `g3_event_mismatch` drops a case whose attached filings report none of the headline's
  event kinds, and a T3 case whose filings carry only items 2.02 and 9.01. T2 guidance
  with an attached 2.02 filing, and a T2 contract with an attached 1.01 filing, pass the
  family-language check. Commentary was left as in gates-1, because widening it dropped
  real events in the cases already read.
- **Pool and sample.** 235 w2 candidates have an attached body. The 43 routing-check
  cases and the 60 gates-1 cards were read while gates-2 was built, so all 103 are left
  out. Of the other 132, gates-2 keeps 56 (19 T1, 37 T2, 0 T3) and drops 76. The seat
  drew 40 gated-in and 20 gated-out cases (seed 20261018) and read them as shuffled cards
  that did not show gate status (`audit/sample_gates2.json`, `audit/gates2_verdicts.json`).
- **Bars, fixed in the tool before any gates-2 status on the pool was computed.** The
  same as gates-1: at least 34 of 40 gated-in `MATCH`, and an estimated real-event drop
  share of 0.20 or less.
- **Gated-in: MISS.** 31 of 40 are `MATCH` (0.775, Wilson 95% [0.625, 0.877]), three
  short of the bar. No miss is `WRONG_ISSUER`. 6 are commentary on a standing fact rather
  than a new event, 2 route a product sense of "offering" to capital allocation (both
  `NO_EVENT`), and 1 names an event no attached filing reports (`OTHER_EVENT`).

  | Template | Gated-in | `MATCH` | `NO_EVENT` | `OTHER_EVENT` |
  |---|---|---|---|---|
  | T1 | 16 | 12 | 3 | 1 |
  | T2 | 24 | 19 | 5 | 0 |
  | T3 | 0 | 0 | 0 | 0 |

- **Gated-out: MISS.** 3 of 20 are `MATCH`. Weighted by pool size, gates-2 keeps about
  43.4 real events and drops about 11.4, a share of 0.208 (bound interval [0.074, 0.439]),
  just over the bar. The 3 dropped real events are cut by the issuer guard (2) and by the
  results-without-2.02 rule (1). The other 17 are 6 `NO_EVENT`, 6 `OTHER_EVENT` and 5
  `WRONG_ISSUER`.
- **T3 gets nothing through.** All 25 T3 pool cases are gated out, and none of the 6
  sampled is `MATCH` (2 `NO_EVENT`, 2 `OTHER_EVENT`, 2 `WRONG_ISSUER`).
- **Gates-1 against gates-2 on the same pool.** The two sets agree on 121 of the 132
  pool cases and disagree on 11. Agreeing cases enter both filters alike, so the 11
  decide which is the better filter. The rule, fixed in `tools/compare_gates_paired.py`
  and committed before any of its cards was read: a set is right on a case when it keeps
  a `MATCH` or drops a non-`MATCH`, and gates-2 replaces gates-1 only if it is right on
  more of the 11 (a tie keeps gates-1). 5 of the 11 already had a class from this
  validation, and the seat classed the other 6 on blind cards (seed 20261019,
  `audit/paired_verdicts.json`). Gates-2 is right on all 11 and gates-1 on none: gates-2
  keeps 5 real events gates-1 cut for missing family language, and drops 3 `NO_EVENT`
  and 3 `OTHER_EVENT` cases gates-1 kept (`audit/gates_paired.json`).
- **The frame binds.** At each family's sampled rates the pool holds about 17 T1, 38 T2
  and 0 T3 on-event cases, against 200 each. 66 pool cases have still not been carded,
  and only 15 of them are gated in under gates-2, too few for another 40-case gated-in
  sample.
- **Limit of this audit.** The seat wrote both gate sets and classed every card. The
  cards hid gate status, not the auditor's knowledge of the rules. No second auditor read
  them, because the GLM, Grok and Codex lanes were exhausted.
- **Ruling.** Neither gate set is accepted as an on-event guarantee. Gates-2 replaces
  gates-1 as the draw filter, and every scored continuation case keeps its own routing
  verdict. No further headline-gate revision is validated on this pool. The next lever is
  a filing-first widening of the frame inside the existing SEC owners. T3's shortfall is
  printed at its full 200. See `DEC:NEWS-IMPACT-ROUTING-GATES-2-MISS-PATH` and
  `DSC:NEWS-IMPACT-ROUTING-GATES-2-VALIDATION`.
- **Not re-scored.** The addendum lives in `audit/sample_gates2.json`,
  `audit/gates2_verdicts.json`, `audit/gates2_validation.json`,
  `audit/paired_verdicts.json` and `audit/gates_paired.json` only.

### v2 continuation routing census addendum

The 99-case continuation draw `../gated_v2/` (`ni-edgar-body-2`, gates-2 as the draw
filter) needs a routing verdict on every case before any of it scores, because only
`MATCH` cases score (`DEC:NEWS-IMPACT-ROUTING-GATES-2-MISS-PATH` item 3). 69 of the 99
already carry a verdict from a card the seat read earlier (17 from the routing check, 24
from the gates validation and 28 from the gates-2 validation). The other 30 are a census,
with no sampling. The rules were fixed in `tools/build_v2_routing.py` before any of its
cards was read: card order is the sorted ids shuffled with seed 20261020, the four classes
are unchanged, and the cards are built from the v2 bodies. Each filing shows its session
offset and relation, and for a graded case whether it sits in the body that was graded.
The tool's sha256 (`b6aac488…`) was recorded before the first card was opened.

A graded case keeps its grade on its graded v1 body (`DEC:NEWS-IMPACT-EDGAR-BODY-2-BAND`).
So for a graded case `MATCH` needs a filing in that graded body that reports the event. A
report found only in a filing the wider band added is `OTHER_EVENT`, kind
`graded_body_lacks_report`.

| Census (30 cases) | MATCH | NO_EVENT | OTHER_EVENT | WRONG_ISSUER |
|---|---|---|---|---|
| graded (8) | 7 | 0 | 1 | 0 |
| never graded (22) | 10 | 7 | 4 | 1 |
| total | 17 | 7 | 5 | 1 |

- **Census MATCH share 0.567**, Wilson 95% interval [0.392, 0.726]. This is information
  only. Gates-2 stays frozen at `5baa4b10` and no gate revision is validated on this
  population. The 7 `NO_EVENT` cases are 5 commentary pieces and 2 market reports. 4 of the
  5 `OTHER_EVENT` cases have no attached filing that reports the headline event; the fifth
  is the one `graded_body_lacks_report`.
- **Routing map over all 99 drawn cases:** 74 `MATCH`, 15 `NO_EVENT`, 9 `OTHER_EVENT`
  and 1 `WRONG_ISSUER`. Every drawn case has exactly one verdict, and the tool refuses a
  case carded twice.
- **Scorable.** 74 cases score. 62 of them already carry a two-family grade, and the other
  12, which are `MATCH` but never graded, form the labeling queue.

  | Template | drawn | scorable MATCH | already graded | label queue | non-MATCH | shortfall vs 200 |
  |---|---|---|---|---|---|---|
  | T1 | 49 | 34 | 28 | 6 | 6 NO_EVENT, 9 OTHER_EVENT | 166 |
  | T2 | 46 | 36 | 31 | 5 | 9 NO_EVENT, 1 WRONG_ISSUER | 164 |
  | T3 | 4 | 4 | 3 | 1 | none | 196 |
  | Total | 99 | 74 | 62 | 12 | 25 | 526 |

- **The shortfall is printed, never padded.** 74 scorable cases against 600 leaves 526.
  The band is not the binding lever; issuer resolution is (1,271 candidates name no ticker
  the ledger maps to a CIK, `DSC:NEWS-IMPACT-EDGAR-BODY-2-FRAME`).
- **Limit of this census.** The seat classed every card, and no second auditor has read
  them. A second auditor classes the same cards when a labeling lane opens.
- **Not re-scored.** The census lives in `audit/v2_routing_spec.json`,
  `audit/v2_routing_verdicts.json` and `audit/v2_routing.json` only. `summary.json` and
  the 157-case labels are unchanged. See `DSC:NEWS-IMPACT-V2-ROUTING-CENSUS`.

### v2 label queue addendum

The 12 queue cases above carry two-family labels under prompt-v1.2 (family A MiniMax-M3,
family B qwen3.7-plus) on their `ni-edgar-body-2` bodies. `tools/score_v2_queue.py` grades
them with `score_benchmark.py`'s own functions, imported rather than copied, and
`score_benchmark.py` and its outputs are unchanged. Its output is value-free: per slot it
keeps the class, both directional outcomes and the mismatch components, never a value.

- **Span replay is clean.** Family A replays 125 of 125 cited spans (Wilson 95% [0.970,
  1]) and family B 119 of 119 ([0.969, 1]). No case is flagged for injection.
- **Critical slots agree on 12 of 24 (0.50, [0.31, 0.69]).** 6 agree present, 6 agree
  absent, 3 differ in value (2 value, 3 period components) and 9 are present against
  absent. All 12 cases are `routed_pending_third`.

  | Slot | slots | agree | classes |
  |---|---|---|---|
  | T1 `executed_amount` | 6 | 0 | 6 present vs absent |
  | T1 `incremental_amount` | 6 | 4 | 4 agree present, 1 value differs, 1 present vs absent |
  | T1 `remaining_authorization` | 6 | 6 | 6 agree absent |
  | T2 `stated_amount` | 5 | 2 | 2 agree present, 2 value differs, 1 present vs absent |
  | T3 `stated_quantity` | 1 | 0 | 1 present vs absent |

- **One slot carries most of the disagreement.** On T1 `executed_amount` the families
  split present against absent on all 6 cases, family A reporting a value and family B
  none on 5 of them. Both cite only text that replays, so this looks like a definition
  gap (what counts as an executed amount on a buyback disclosure) rather than a reading
  error. A third family aimed at that slot decides which.
- **Scorable view.** Joining the 12 to the 62 graded `MATCH` cases gives 74 cases and 142
  critical slots at agreement 0.535 ([0.453, 0.615]): T1 0.598 over 102 slots, T2 0.361
  over 36, T3 0.5 over 4. By source the graded v1 bodies sit at 0.542 over 118 and the
  queue at 0.50 over 24. These are two-family agreement rates, not accuracy, and no queue
  case is adjudicated until a third family reads it. The shortfall stays 526.
- **Not re-scored.** The queue lives in `v2_queue/` only. See
  `DSC:NEWS-IMPACT-V2-QUEUE-SCORING`.

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

No kill fired. Material-event routing was not labelled by the families in this wave. The
routing check addendum gives seat routing labels for 43 cases, which measure the draw's
precision only. Routing recall needs a labelled reject set and is not reported.

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
| `audit/regrade_malformed.json` | Counterfactual class of each `malformed_value` slot (ids and classes only) |
| `audit/audit_malformed.json` | Malformed-slot verdicts and summary, with paraphrased notes |
| `audit/sample_routing.json` | The 40 routing-check cases plus the three motivating cases (ids only) |
| `audit/routing_verdicts.json` | Seat routing verdicts per case, with paraphrased notes |
| `audit/routing_check.json` | Routing codes, flags, verdicts, class rates and flag precision and recall |
| `audit/sample_gates.json` | Gates validation pool counts, the 60 sampled cases with gate status, card order (ids and codes only) |
| `audit/gate_verdicts.json` | Seat routing verdicts for the 60 gates-validation cases, with paraphrased notes |
| `audit/gate_validation.json` | Per-case gate status and class, class rates per arm, both bars with PASS or MISS |
| `audit/sample_gates2.json` | Gates-2 validation pool counts, the 60 sampled cases with gate status, card order (ids and codes only) |
| `audit/gates2_verdicts.json` | Seat routing verdicts for the 60 gates-2 validation cases, with paraphrased notes |
| `audit/gates2_validation.json` | Gates-2 per-case status and class, class rates per arm, both bars, per-family estimates |
| `audit/paired_verdicts.json` | Seat routing verdicts for the 6 disagreement cases not classed in the gates-2 validation |
| `audit/gates_paired.json` | Gates-1 against gates-2 on the 11 disagreement cases: both statuses, class, who is right, filter pick |
| `audit/v2_routing_spec.json` | v2 routing census population: counts, census ids with template and graded flag, card order (ids only) |
| `audit/v2_routing_verdicts.json` | Seat routing verdicts for the 30 census cases, with paraphrased notes |
| `audit/v2_routing.json` | Census class counts with Wilson intervals, routing map for all 99 drawn cases, scorable ids, label queue, per-template shortfall |
| `tools/build_label_lanes.py` | Builds the labeling lane trees and packets |
| `tools/label_batch.template.txt` | Lane packet prompt-v1.0 (64 cases per family) |
| `tools/label_batch.template.v1.1.txt` | Lane packet prompt-v1.1 (93 cases per family) |
| `tools/label_batch.template.v1.2.txt` | Lane packet prompt-v1.2, carrying annotation guide-v1.2 (next wave) |
| `tools/fill_spans.py`, `tools/check_label.py` | In-lane helpers: span hashing and return self-check |
| `tools/canon_returns.py` | Representation-only canonicalisation (rules C1–C4) before agreement |
| `tools/build_audit.py` | Draws the audit sample |
| `tools/build_audit_absent.py` | Draws the addendum sample and runs its positive control |
| `tools/build_audit_malformed.py` | Period-shape census and counterfactual re-grade of the `malformed_value` slots |
| `tools/build_routing_check.py` | Draws the routing sample and scores the routing verdicts (needs Python 3.11) |
| `tools/build_gate_validation.py` | Draws the gates-validation sample and scores its verdicts (needs Python 3.12) |
| `tools/build_gates2_validation.py` | Draws the gates-2 validation sample and scores its verdicts (needs Python 3.12) |
| `tools/compare_gates_paired.py` | Finds the gates-1/gates-2 disagreement cases and scores the filter comparison (needs Python 3.12) |
| `tools/build_v2_routing.py` | Finds the gated_v2 cases no card has shown, writes their census cards and scores the census verdicts (needs Python 3.12) |
| `tools/score_benchmark.py` | Produces `summary.json`, `critical_slots.jsonl` and the receipts |
| `tools/score_v2_queue.py` | Scores the two-family labels on the 12-case label queue and the 74-case scorable view, reusing `score_benchmark.py`'s grading (needs Python 3.12) |
| `v2_queue/critical_slots.jsonl` | One row per critical slot of the 12 queue cases: class, both directional outcomes and mismatch components, no values |
| `v2_queue/summary.json` | Queue span replay, critical-slot and field agreement, and the scorable view by template, prompt version and source, with the shortfall |

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
# malformed-slot addendum: period-shape census, then the counterfactual re-grade
PYTHONPATH=. python3 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/build_audit_malformed.py \
  SCRATCH_W2 research/prophet_v4/news_to_business_impact_20261006/benchmark --census
PYTHONPATH=. python3 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/build_audit_malformed.py \
  SCRATCH_W2 research/prophet_v4/news_to_business_impact_20261006/benchmark AUDIT_OUT
# routing check: draw the sample, then score the committed verdicts (imports tape_draw: Python 3.11)
PYTHONPATH=. python3.11 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/build_routing_check.py \
  SCRATCH_W2 research/prophet_v4/news_to_business_impact_20261006/benchmark AUDIT_OUT \
  research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/routing_verdicts.json
# routing gates validation: recompute gate statuses, draw the sample, score the committed verdicts (Python 3.12)
PYTHONPATH=. python3.12 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/build_gate_validation.py \
  SCRATCH_W2 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2 AUDIT_OUT \
  research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/gate_verdicts.json
# routing gates 2 validation, then the paired filter comparison (Python 3.12)
PYTHONPATH=. python3.12 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/build_gates2_validation.py \
  SCRATCH_W2 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2 AUDIT_OUT \
  research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/gates2_verdicts.json
PYTHONPATH=. python3.12 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/compare_gates_paired.py \
  SCRATCH_W2 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2 AUDIT_OUT \
  research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/paired_verdicts.json
# v2 continuation routing census: census population and cards, then score the committed verdicts (Python 3.12)
PYTHONPATH=.:research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools python3.12 \
  research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/build_v2_routing.py \
  SCRATCH_W2 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2 AUDIT_OUT \
  research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/v2_routing_verdicts.json
# v2 label queue: score the canonicalised two-family returns and join the graded MATCH cases (Python 3.12)
PYTHONPATH=.:research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools python3.12 \
  research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/score_v2_queue.py \
  --w2q SCRATCH_W2Q --results research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2 \
  --bench research/prophet_v4/news_to_business_impact_20261006/benchmark \
  --out research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/v2_queue
```

`build_audit.py` also writes `batch_*.txt` audit cards, `build_audit_absent.py` writes
`batch_absent_*.txt` cards, `build_audit_malformed.py` writes `batch_malformed_*.txt`
cards, `build_routing_check.py` writes `batch_routing_*.txt` cards,
`build_gate_validation.py` writes `batch_gates_*.txt` cards, `build_gates2_validation.py`
writes `batch_gates2_*.txt` cards, `compare_gates_paired.py` writes `batch_paired_*.txt`
cards and `build_v2_routing.py` writes `batch_v2_routing_*.txt` cards. All eight quote
headlines or filing text and must not be committed. The audit verdicts in `audit/audit.json` are the auditor's, not a
tool's output.

Checked at commit time from the committed tools and the committed `audit/audit.json`:
`score_benchmark.py` reproduces `summary.json`, `critical_slots.jsonl` and both eval
receipts byte for byte, and `build_audit.py` reproduces `audit/sample.json` byte for byte.
`build_audit_absent.py` reproduces `audit/sample_absent.json` byte for byte, and its
control reports 40 hits and 0 misses. `build_audit_malformed.py` reproduces
`audit/regrade_malformed.json` byte for byte. `build_routing_check.py` reproduces
`audit/sample_routing.json` and `audit/routing_check.json` byte for byte.
`build_gate_validation.py`, run under Python 3.12 against the frozen gates, reproduces
`audit/sample_gates.json` and `audit/gate_validation.json` byte for byte.
`build_gates2_validation.py` reproduces `audit/sample_gates2.json` and
`audit/gates2_validation.json` byte for byte, and `compare_gates_paired.py` reproduces
`audit/gates_paired.json` byte for byte. `build_v2_routing.py` reproduces
`audit/v2_routing_spec.json` and `audit/v2_routing.json` byte for byte. `score_v2_queue.py`
reproduces `v2_queue/critical_slots.jsonl` (`4efe674a…`) and `v2_queue/summary.json`
(`99fd23b2…`) byte for byte. Its scratch inputs (bundles, label returns and agreement
output) quote filing text and are not committed.

## Next

1. Done: the filing-first widening (`ni-edgar-body-2`, `../gated_v2/`, 99 cases), the
   routing census above, and two-family labels on the 12-case queue (`v2_queue/`, above).
   Any new gate rule is frozen and validated on cases no card has shown, under the same two
   bars (`DEC:NEWS-IMPACT-ROUTING-GATES-2-MISS-PATH`).
2. Run a third family (GLM after 2026-10-19 05:16Z) under prompt-v1.2 and annotation
   guide-v1.2 on the disputed slots of gated-in cases only, starting with the 12 queue cases
   and T1 `executed_amount`, where the two families split on all 6 T1 cases: set
   `LABEL_TEMPLATE=tools/label_batch.template.v1.2.txt` for `tools/build_label_lanes.py`.
3. Record three candidates for the next contract version without editing the frozen v1
   contract: a per-share basis for a T1 dividend amount, a total-authorization slot, and
   what counts as an executed amount on a buyback disclosure.
4. Decide per-slot against per-case publication.
5. Add MiniMax cost capture.
6. Grow the scorable set toward 600. It holds 74 (T1 34, T2 36, T3 4), a shortfall of
   526. The next lever is gated_v3 (`../issuer_fallback/README.md`,
   `DEC:NEWS-IMPACT-ISSUER-FALLBACK-LEDGER`): one `ni-edgar-body-2` fetch with `--as-of` on
   or after 2026-10-20 that settles the 113 open windows and reaches the 256 candidates the
   fill-only issuer fallback resolves, recorded as a new draw. The 914 candidates that name
   no ticker need a name rung. Print T3's shortfall rather than fill it with off-event
   cases.
7. A second auditor classes the 60 gates-2 validation cards, the 11 disagreement cases
   and the 30 v2 census cards when a labeling lane opens (GLM after 2026-10-19 05:16Z).
