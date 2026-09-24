# Consumer Cyclical V1 — return to Sol

**Operation:** `gmi-consumer-cyclical-v1-integration-20260924-fable-001`
**Principal:** Fable integration owner
**Carrier:** PR #7942 (**MERGED** 2026-09-24T13:07:49Z, `6e3e8987c5c6`), branch
`claude/consumer-cyclical-v1-plnt`; follow-up repair PR #7945, branch `claude/consumer-cyclical-v1-lead`
**Source packet:** R15 `FABLE_INTEGRATION_READY_R15.md` @ `3d286719` (PR #7804, DRAFT/HOLD, research only)
**Admission edge:** deliberate live direct Chairman handoff, 2026-09-24 (see boundary spec §0)

## 1. Delivery state — stated at the rung the evidence reaches

**`V1-CORE` delivered; `V1 PROVEN_LIVE` NOT reached and not claimable.**

R15's V1 ruler requires an entitled user to open PLNT in a browser and see a source-bound explanation.
That cannot be reached today without violating R15's own prohibitions, so it was **not attempted**.
What is delivered is the deterministic, source-coordinate-bound economic core the blocked legs will
later publish unchanged.

Ladder position: **`MERGED` and `PRODUCTION_PROOF` reached; `ACCEPTANCE` is Sol's and is not claimed.**
PR #7942 squash-merged to `main` at 2026-09-24T13:07:49Z as `6e3e8987c5c6`, and the golden oracle was
re-run **from `main`**, not from the carrier branch — see §4. `PRODUCTION_PROOF` here means the module
computes the accepted economics correctly on the canonical tree; it does **not** mean V1's browser
ruler was met, which §1's first line already denies and §6 keeps blocked.

## 2. Why legs 6-9 were frozen rather than built

Every external owner head is **byte-identical to the R15 freeze pins and still OPEN/DRAFT**:

| Owner | head | state |
|---|---|---|
| #7870 shared foundation | `3e3a7956d014` | OPEN draft |
| #7780 build-out ruling | `b68069b2e129` | OPEN draft |
| #7669 template owner | `6942b2b62bad` | OPEN draft |
| #7462 theme graph/store | `31706d7322af` | OPEN draft |
| #7426 company history | `7bc04876747d` | OPEN draft |

`#7331` is named by R15 but is a GitHub **issue**, never pinned to a SHA, and R15 line 148 exempts PLNT
from LULU history. The R15-pinned shared transport `app/theme_research.py` **does not exist on `main`**
(`git rev-parse origin/main:app/theme_research.py` -> exit 128); it lives only on #7870's branch.

`app/earnings.py` was evaluated as an alternative and **rejected on authority, not ignorance**: R15 H1
superseded direct Earnings delivery for this dossier, pre-labels that surface "not a second publisher",
and `engine/earnings_narrative/**` belongs to sibling CDV-1 (#7792).

## 3. What was built, and the precedent it follows

`V1-CORE` extends the already-merged `contracts/sector_intelligence/` family, following the Finance
T1/T2/T3 idiom that landed on `main` the same day while #7870 stayed blocked (#7896 `b4c6e4bd`,
#7920 `e4ac3730`, #7900 `3ca9c303`). It mints no shell, evidence, rights or transport vocabulary.

Changed paths: the contract schema, its fixture, its contract tests, the projection module, its tests,
one exclusive CI job, its `CURATED_EXCLUSIVE` registration, the boundary spec, one `DEC`, one `WS` and
one handoff.

**Gates preserved, not bypassed:**
- no `profile`, no `content_discriminator`, no route, no publisher, no pointer — R15 H2 stays
  `PENDING_SHARED_OWNER_ACCEPTANCE` for the #7780 ruling;
- the contract is named `consumer_cyclical_intelligence_read_model.v1`, mirroring the merged Finance
  axis, so no shipped identifier carries the reserved `economic_change` stem;
- no source collection — the R8 denial is not re-homed.

## 4. Proof

| claim | command | result |
|---|---|---|
| Golden oracle exact, document contract-valid | `pytest tests/test_consumer_cyclical_projection.py tests/test_consumer_cyclical_intelligence_read_model_contract.py -q` | **61 passed** at merge; **65 passed** with the §5a repair |
| Shared contract family still enumerates | `pytest tests/test_sector_intelligence_contracts.py … -q` | **274 passed** |
| CI curation intact | `pytest tests/test_ci_pack.py -k "exclusive or curated" -q` | **7 passed** |
| Pack manifest valid | `run_ci_pack.py --validate-only` | **rc=0**, 229 jobs |
| Records schema-clean | `python3 scripts/agentos.py validate` | **0 errors** |

R6 §7.1 golden values, USD thousands, `Decimal` only, zero `float(` calls:
`total_revenue_change 24344`, `advertising_revenue_change 10141`, `advertising_expense_change 10145`,
`advertising_net_change -4`, `advertising_current_period_net 0`,
`advertising_share_of_revenue_change_pct 41.66`. The two advertising changes both round to `$10.1M`;
the **-4 residual is asserted to survive**.

READY document: 0 schema errors. Zero-facts document: 0 schema errors, `results: []`,
`availability: unavailable`.

## 5. Independent review

An independent Opus review returned **FAIL** on the first boundary packet. All findings accepted and
repaired in `3a0a4bb6`: the unrecorded admission edge, a false "all six owner heads" receipt, and the
contract-name collision with the reserved H2 grammar. Seat verification then found four defects in the
fabric-delivered projection that its own green suite could not detect — its fixtures encoded
`native_admitted: true`, a state that cannot occur for PLNT — repaired in `4f00e7f3`.

### 5a. A defect that only live verification could find (post-merge)

Verifying from `main` after the merge — rather than trusting the green suite — caught a real defect the
61-test suite could not see. `_build_explanation` tested the `FACT_KEY_*` constants for membership in
the set of **result** keys. Those two vocabularies are disjoint, so the test could never be true and the
economic lead was **unreachable on every input**: the document always emitted the neutral fallback
instead of the R6 advertising-flow sentence. Every asserted number stayed exact, which is why the suite
stayed green — the numbers were right and the sentence explaining them was missing.

Repaired on PR #7945 with two regression tests. A same-class audit (two defects sharing one root cause —
comparing the wrong *kind* of identifier) then found two further latent instances and hardened both:
result keys were being spelled by concatenating `"_change"` onto a `FACT_KEY_*` constant (the two
spellings coincide today, so a later rename would have retargeted silently), and `by_key` locals were
named for a grouping that had already moved to `metric`. Neither was live; both are now impossible,
pinned by two invariant tests. 61 -> 65 tests.

**This is the honest cost of the ruler:** `MERGED` was reached before the lead was correct, and only
production verification distinguished them. It is reported rather than quietly folded into §4.

## 6. What Sol is being asked to unblock

1. **#7870** — the T09 EDGAR-family/fail-closed rights correction, plus T08b / T10e / T10f / T11a.
   Until then the rights veto governs almost none of the SEC corpus and no real Consumer assertion may
   cross the shared route.
2. **#7780** — the cross-vertical profile/dispatch/mount ruling that owns the R15 H2 grammar.
3. **#7669** — template/page custody for the company-page consumer.
4. **Incumbent source owner** — native admission of PLNT accession `0001637207-26-000042` /
   `plntq22026pressreleaseex991.htm`. It is retained nowhere today, so every fact ships
   `native_admitted: false` / `native_ref: null`. This is the honest state, not a placeholder.

## 7. Not requested

No V2 LTH, V3 LULU or V4 theme journey. R15 forbids self-authorizing them on a V1 pass, and the next
modifying child takes its own continuation edge.

## 8. Operational note for the next wave

Delegation to the external fabric was only partly available from this host. `pool run qwen` refused
with `LOCAL_SEAT_REMOTE_REQUIRED host=m2 … local_only=grok,ocfree`; `grok` was then refused with
`host_load_at_or_above_limit` at load1 22.8/24; `minimax` died at launch on
`unrecognized_model MiniMax-M3`. `pool remote` exposes only `cursor|glm|glm-codex|minimax|minimax-codex`
modes — bailian has none — and a remote host would need its own checkout of the carrier branch. Two
lanes did deliver real work before that (the contract schema is theirs); the repair fell to the
principal directly under the continuation law. **Fixing this provisioning gap would materially cut
principal token burn on the next wave.**
