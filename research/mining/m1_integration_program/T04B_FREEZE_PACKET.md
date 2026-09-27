# T04b FREEZE PACKET — integrated positive witnesses on T03 inputs

Operation `gmi-mining-fable-ceo-m1-integration-20260924-chairman-001` · seat `664a0650` · 2026-09-27
Status: SEAT-AUTHORED. Neither audit wrote a T04b spec — this fills that gap.

---

## §1 Why this packet exists at all

**T04b had no frozen spec.** Audit A §4 covers T02 / T03 / T07 / CI. Audit B §4 is a single
`FROZEN SPEC — T04` covering all of T04, whose GREEN gate is literally *"8 MGD tests, §6"*.
The a/b split is **R-MIN-05's** (`T01' → (T02 ∥ T04a) → T03 → T04b → T07`), where
T04b = "the integrated positive witnesses on T03 inputs". So no auditor ever froze T04b's
seams, and dispatching it from R-MIN-05's one-line definition would leave every decision in
§4 below to the lane.

**Hard gate — T04b shares OWNED FILES with T04a.** It extends
`engine/market_ontology/mining_theme_research.py` and `tests/test_mining_composition.py`,
which #7950 delivers. T04b therefore starts only when **#7950 is merged AND T03 is delivered**.
It is not unblocked by #7950 alone.

## §2 Scope

IN: wire the two positive witnesses (W-C copper, W-R rare-earth) to **T03's real emitted fact
rows** instead of hand-written casebook packets; carry the consequences of that wiring through
the closed schema; close MGD-08 clause 2.

OUT: any new definition (T04a owns the closed two), any route/client/mount (T05/T06, held
behind #7870), any correction/replay semantics (T07), any live figure (G2 — no Freeport or MP
Materials real value may become a fixture before G2).

## §3 What T03 hands over (Audit A §4 ROW SHAPE, frozen)

```
{"schema":"event_fact.v1","fact_id":…,"event_id":…,"metric":…,"value":…,"unit":…,
 "period":…,"basis":…,"source_span":…}
absent row: same keys minus value/unit/period/basis, plus "typed_absence": TypedAbsence(...).to_payload()
```
Emitted by `engine/company_intelligence/mining_issuer_profiles.py`. **Every row carries `period`.**

## §4 The four seams the lane must NOT decide for itself

### 4.1 Direction of the dependency — the TEST wires, the module does not import

Audit A F2 forbids T03 importing `engine/market_ontology/*`. Nothing forbids the reverse, and
that is the trap: importing `mining_issuer_profiles` into `mining_theme_research` would give
the composer a transitive I/O path and break the already-shipped
`test_compose_does_not_perform_io`.

**FROZEN: the composer gains no new import.** The *test* calls T03's profile function, maps its
`event_fact.v1` rows into `MiningOwnerBundle.financial_packets`, and composes. The mapping
function lives in the test layer (`tests/mining_casebook.py`), not in the engine module.

### 4.2 `period` — carry it, and the schema changes

T03's rows carry `period`; T04a's native block does **not** (measured at #7950 head:
`['basis','measure','sign','source_label','stable_subject_id','value']`). There is no third
option — the lane either drops `period` on the way in or carries it:

- dropping it makes a *reported* period measure period-less in the payload — information
  destroyed at the seam, and a consumer cannot tell which period a value belongs to;
- carrying it pairs a `period` with an issuer-derived `stable_subject_id`, which is exactly the
  MGD-10 exposure (§4.3).

**FROZEN: carry `period`.** Add it to the native-block object in
`contracts/market_ontology/mining_theme_research.v1.schema.json`. The schema is closed
(`additionalProperties: false`), so **this is a deliberate contract change** — it will show in
`contract-delta` and must be declared in the PR body, not explained away as incidental.

### 4.3 MGD-10 becomes live here too, not only in T03

Once §4.2 lands, the composition layer pairs a period with a current-CIK-derived subject id.
T03 carries its own MGD-10 pin (`T03_FREEZE_PACKET.md` §6); **T04b must not re-introduce the
confusion at the composition layer.** Required, both arms:
1. a witness whose fact-row `period` precedes the issuer mapping's validity → the
   asset→issuer attribution is refused, or degraded to a named limitation, asserted by exact
   code, never by truthiness and never by a subset check;
2. the REVERSED case: identical literals plus an accepted time-valid bridge → attribution
   minted. A one-armed pin is satisfiable by refusing everything.

### 4.4 MGD-08 clause 2 — the pin R-MIN-34 authorises

Measured at #7950 head: an empty economic path returns `status == "degraded"`,
`native_blocks == []`, `limitations == ['omitted:expectations']` — identically so with
`omissions == ()`. **R-MIN-34: `degraded` + named absence SATISFIES "a wholly empty economic
path fails".** Do NOT force a refusal: that contradicts R-MIN-15 and would break the
source-only usefulness MGD-11 requires.

**Pin:** `status == "degraded"` AND `native_blocks == []` AND the absence limitation present by
exact code, compared `==` against the exact status, never `!=`. Reverse arm already shipped
(both complete cases return `ready` with a populated block).

**Construction note — the casebook cannot express this today.** `synthetic_case(name, **overrides)`
can only SET fixture keys (`_merge` has no delete) and `financial_packets` is derived from the
presence of the top-level `economics` key. Build the bundle directly —
`dataclasses.replace(case.bundle, financial_packets=())` — or add a fixture whose `economics`
key is absent. A `bundle={…}` override is silently ignored: it sets a top-level key `_bundle()`
never reads, and the probe then reports a populated path while claiming an empty one.

## §5 Anti-letter-gaming rules (carried from T04a's three rounds + T07)

1. **Integrated fixtures are committed FIRST, in their own commit, before the suite.** Any
   regeneration of expected values from the composer in the lane's diff is automatic rejection
   even with a green suite — the T07 proof-7 trap, and the cheapest way to fake this task.
2. Literal pins are never derived from a neighbouring field.
3. Every polarity/sign/ordering pin carries a REVERSED case; every boolean pin asserts BOTH states.
4. Absence sets compared `== sorted(...)`, never a subset check.
5. Non-finite reals rejected explicitly (`nan == nan` is False, so NaN slips equality guards too).
6. A field accepted but never read is a live defect, not a future task.
7. Unknown data is never zero; `authorized_coverage.industry_total` stays null.

## §6 Delivery gates — "not done unless"

1. #7950 merged AND T03 delivered before the branch is cut (shared OWNED FILES).
2. The two witnesses compose from T03's **real emitted rows**, proven by the test calling T03's
   function — not by a copy of its output pasted into a fixture.
3. `period` present on native blocks, the schema change declared in the PR body, `contract-delta`
   green.
4. MGD-08 clause 2 and MGD-10 both pinned two-armed per §4.3/§4.4.
5. All authority flags literal false and echoed on every response and every evidence object;
   every return path validated by `validate_mining_research`.
6. RED committed before GREEN; a mutation run whose survivors are each argued EQUIVALENT on the
   code path (unreachable past a preceding guard, that guard itself pinned by another killed
   mutant) — the M11 standard.
7. Review commissioned per **R-MIN-33e**: evidence INLINE (code excerpt + measured outputs +
   numbered candidates). Naming an artifact by path turns the reviewer into a discovery task and
   it spends its whole budget before reaching judgment — measured twice, 166k and 150k tokens
   for zero verdicts.
8. The obligation count is verified by **obligation id, never by test name** — the failure that
   let MGD-08 and MGD-10 through T04a's green CI and two Opus rounds (see `T08_FREEZE_PACKET.md` §4).
