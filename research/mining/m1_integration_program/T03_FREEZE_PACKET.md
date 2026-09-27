# T03 `min_t03_economic_inputs` — seat-authored freeze packet (pre-dispatch)

Authored 2026-09-27 while #7950/#8060 CI runs. **Not yet committed** — it lands with the
T03 wave so it does not disturb #8060's in-flight proof. Mandated by R-MIN-31: *every*
Mining task carries a seat-authored exact truth table, frozen BEFORE the lane runs.

T04a cost three rounds because its oracle was written after the lane delivered. Rounds 1–2
were passed by *satisfying the letter* of count/flag probes (`_leg()` filled both comparison
legs from `period_kind`, so every leg published the string `"quarter"` while row-count and
`is_range` probes went green). This packet exists to make that impossible for T03.

## 1. Scope (binding, R-MIN-20)

T03 owns exactly `engine/company_intelligence/mining_issuer_profiles.py` and
`tests/test_mining_economic_inputs.py` (+ its fixtures). Its suite asserts on **Company-owner
fact rows** from `fcx_profile()` / `mp_profile()`. It **may not import
`engine/market_ontology/*`** — every `compose_mining_research` assertion belongs to T04.

Imports are closed to the pg idiom (R-MIN-11): `TypedAbsence, text_span`; `IssuerRegistry`;
`IssuerIdentity, ListingAlias, company_id_for_cik`; `IssuerProfile, _no_guidance`;
`BoundRelease, bind_release_document`; `ReceiptError, SpanReceipt, receipt_for_literal`.
Never `issuer_profiles`' module-private helpers. Signatures are fixed: `FCX_CIK`, `MP_CIK`,
`MINING_TICKERS`, `fcx_issuer()`, `mp_issuer()`, `mining_private_registry()`,
`fcx_profile(*, fiscal_scope)`, `mp_profile(*, fiscal_scope)`.

## 2. SEQUENCING — RESOLVED from Audit A (answer: T02 mints, T03 extends)

R-MIN-11 tags `mining_issuer_profiles.py` as **T02/T03**, which reads as shared and is what
made the earlier record wrong. Audit A's frozen specs settle it:

- line 73, **FROZEN SPEC — T02**: `OWNED FILES: engine/company_intelligence/mining_issuer_profiles.py (new)`
- line 125, **FROZEN SPEC — T03**: `OWNED FILES: engine/company_intelligence/mining_issuer_profiles.py (extend)`
- line 183, **FROZEN SPEC — CI**: the job is *"created by T02's PR, appended by T03/T07"*

So **T02 mints the module and T03 only extends it** — option (b). Per Audit A F3, T02 itself
branches only after CDV-1 **#7905** merges (the `profile_for_ticker` private-branch hunk is
that PR's own hunk, and FCX/MP must resolve only under `publication="private"`).

**Therefore T03 needs BOTH #7950 (T04a) merged AND T02 delivered.** Dispatching T03 on
#7950's merge alone points a lane at a module that does not exist yet and guarantees a
collision with T02 over one file. #7950 merging unblocks **T04b**, not T03. The committed
handoff has been corrected accordingly.

**Landmine this surfaced (Audit A F12):** a Mining private span needs BOTH a Mining rights
constant in `mining_issuer_profiles.py` AND its registration in
`engine/company_intelligence/qa_exchange.py` — a second shared-owner edit the plan's file map
never mentions, which must also be in the CI job's `paths:`. The frozen pg probe asserts
`qa_exchange.py` is the **only** declaring file, so registering the token anywhere else reds
it. Per R-IND-13, 10-Q/filing-edition spans use `rp_unknown_v1`-class handling until the
rights owner qualifies the use.

## 3. Exact truth table — the oracle, frozen before the lane

Per R-MIN-31, counts and flags are NOT an oracle. Each case names, exactly:
`fact row count`, the EXACT set of typed-absence reasons (`== sorted(expected)`, never `⊆`),
and per row `(metric, value, unit, period, basis)` with the **literal numeric value**.

| case | rows | exact absence set | pinned row values |
|---|---|---|---|
| `fcx_profile(fiscal_scope=<quarter>)` normal | exact N | `[]` | each `(metric, value, unit, period, basis)` literal, value a real `float`, never `bool` |
| parenthesized negative literal | exact N | `[]` | `parse_mining_literal("(20,296)", unit=…) == -20296.0` — a **negative float**, sign on the fact row, not a display string (R-MIN-14) |
| no period column | N−1 | `["missing_period"]` | the surviving rows unchanged |
| basis absent | N−1 | `["missing_basis"]` | — |
| unit/definition mismatch | N−1 | `["missing_units"]` | — |
| ambiguous / duplicate / unaddressable cell | N−1 | `["no_span_addressable_evidence"]` | — |
| document body not held | 0 | `["document_bytes_not_held"]` | — |
| accession unjoinable | 0 | `["unjoinable_filing_identity"]` | — |
| W-C: prior point estimate + actual, **no** `next_outlook` | both reported values present | typed `projector_unbound` refusal | `assess_management_sequence` is **never called**; no invented range, midpoint or badge (R-MIN-16) |
| two events, same metric | distinct `fact_id`s | `[]` | `fact_id` derives from `(event_id, metric, period, basis)` — a borrowed id is REFUSED (R-MIN-17) |

Absence reasons are closed to the 14-word `ABSENCE_REASONS` vocabulary (R-MIN-15).
`missing_derivation`, `interpretation_stale`, `stream_threshold_unknown` and
`definition_unqualified:*` are T04 **limitation** strings — if any appears as an absence
reason, that is a defect, and the suite pins their absence explicitly.

## 4. Anti-letter-gaming rules (earned the hard way on T04a)

These are oracle *construction* rules, not style. Each maps to a measured T04a failure:

1. **Every value pin is a literal, never derived from another field of the same fixture.**
   The round-2 defect was legs filled from `period_kind`. A test that would still pass if the
   module echoed a neighbouring field is not a test.
2. **Every polarity / sign / ordering pin carries a REVERSED case.** R-MIN-33d: my own R-MIN-32
   amendment pinned one value pair per name with one expected direction, satisfiable by a
   lookup table without comparing numbers. Reversed inputs must flip the output.
3. **Every boolean pin asserts BOTH states.** A `False`-only pin is satisfied by a hardcoded
   `False`.
4. **Absence sets use `==` against a sorted list, never `in` or a subset check.** Subset
   assertions cannot see a spurious extra reason.
5. **Numeric guards must reject non-finite reals explicitly.** `nan` passed T04a's numeric gate
   and, because `nan == nan` is False, also slipped the equality withhold (R-MIN-33c).
6. **A field the module accepts but never reads is a live defect, not a future task.** T04a
   carried `unit`/`perimeter`/`period` unread, which published an *inverted* polarity across
   Mlbs/kt and relabelled a proportionate figure as consolidated.

## 5. Delivery gates — "not done unless"

- Probes committed **RED first**, in a separate commit, before any repair. The receipt is the
  commit order, not an assertion.
- Clean-venv run from the CI job's own install line; the full Mining suite set green with
  **every previously passing test still passing** (no frozen oracle moved).
- `test_ci_pack.py -k 'curated or exclusive or mining'` green; every test in `run:` also in
  `paths:`; `paths:` covers the import closure.
- A mutation run over the new decision path, with each survivor either killed or argued
  **equivalent on the code path** (as M11 was: unreachable past a preceding guard, that guard
  itself pinned by another killed mutant).
- Review commissioned per **R-MIN-33e**: evidence INLINE (code excerpt + measured outputs +
  numbered candidates). Naming an artifact by path turns the reviewer into a discovery task
  and it spends its whole budget before reaching judgment — measured twice, 166k and 150k
  tokens for zero verdicts.

## 6. ADDED 2026-09-27 — MGD-10 becomes T03's obligation (from the forty-obligation audit)

MGD-10 is mapped to T04 in Audit B §6, but it is **unfalsifiable until T03 exists** and T03 is
the lane that makes it live. Measured at #7950 head (`scratchpad/probe_mgd_08_10_v2.py`):

- `identity_results` fields are exactly `['cik', 'fictional', 'name']` — no validity window.
- a native economics block carries `['basis','measure','sign','source_label','stable_subject_id','value']`
  — **no `period`** — and `stable_subject_id` is the issuer CIK (`'0000000421'`).

So today the module makes no historical-ownership claim because it cannot express a period on
a measurement. **T03 changes that**: its job is definition-safe economic inputs and
`COMPARABILITY_FIELDS` already names `period`. The first row that carries a period while being
attributed to a current-CIK-derived `stable_subject_id` creates exactly the confusion MGD-10
forbids — "Current issuer mapping is not used as historical asset ownership without an
accepted time-valid bridge."

**Required pin, both arms (a one-armed version is satisfiable by refusing everything):**
1. A case whose economics period precedes the issuer mapping's validity → the asset→issuer
   attribution is refused, or degrades to a named limitation, asserted **by exact code**,
   never by truthiness and never by a subset check.
2. The REVERSED case: identical literals plus an accepted time-valid bridge → attribution
   **minted**.

**W-C is the live trap this protects:** Freeport's current CIK says nothing about which entity
held a given mine during a prior reporting period, and W-C's economics are period measures.

**Adjacent, do NOT fold into MGD-10:** `reported operating income` currently ships with no
period at all. A reported measure without a period is under-specified for a consumer even
when it makes no ownership claim. T03 should decide whether to add one; it is a separate
question from the time-validity bridge, and merging the two would let a lane satisfy neither
properly.
