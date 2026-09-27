# T02 `min_t02_witness_profiles` — seat-authored freeze packet (pre-dispatch)

Authored 2026-09-27. **Uncommitted** — lands with the T02 wave. T02 is the true next task in
sequence: Audit A line 73 gives it `mining_issuer_profiles.py` **(new)**, and T03 only extends
that file, so **T02 precedes T03** and T03 cannot be dispatched on #7950's merge alone.

**GATE: T02 branches only after CDV-1 #7905 has merged** (Audit A F3 — the
`profile_for_ticker` private-branch hunk is that PR's own hunk). #7905 is another seat's DRAFT
under its own audit: **do not poll it and do not arm a watcher on it.** Dispatch when its
content reaches `main`.

Audit A already froze the spec, imports, signatures, selector law, absence mapping, fixture
law, RED/GREEN commands and three mutants (lines 71–122). This packet does not restate that —
it adds the three things Audit A does not carry: the **exact truth table** R-MIN-31 requires,
an **expanded mutant set**, and the **removal of an act the plan wrongly orders**.

Per **R-MIN-33e** the eventual commission carries the binding excerpt INLINE. Naming this file
by path turns the worker into a discovery task; measured twice at 166k and 150k tokens for zero
verdicts.

## 1. REMOVE FROM THE PACKET — the plan orders an unauthorized act (Audit A F1, BLOCKER)

Plan §4 bullet 1 reads *"Acquire the selected C1/C2/C3 and R1/R2 source bodies through approved
existing intake … retain their actual receipt and availability clocks."* That is a worker
checkbox for an act this program is not cleared to perform. The frozen corpus itself records
that **no original bytes were obtained** and that the container could not resolve
`www.sec.gov`; G2 (source admission) and IR-05 (source-use / republication rights) are open.

**The T02 fabric packet is SYNTHETIC-ONLY.** Real-byte acquisition is an owner/intake step held
behind G2 + IR-05 and must be *deleted from the build packet* and recorded as a held gate
(R-IND-12 precedent). A lane handed the plan verbatim would attempt a live SEC fetch — and a
lane that cannot fetch tends to invent the bytes instead, which is the fabrication failure this
program has already paid for once at T04a round 2.

Also held, and not in this packet: rights disposition (IR-05), `DISCOVERY_TICKERS` /
`refresh_event_workspaces` enrollment (#7870 only), the Data OS issuer bridge.

## 2. Exact truth table — the oracle, frozen before the lane (R-MIN-31)

Audit A gives RED/GREEN commands but no per-case expected values, and counts-and-flags are not
an oracle. Each case pins the **exact** absence set (`== sorted(...)`, never subset) and, per
fact row, literal `(metric, value, unit, period, basis)` with `value` a real `float`, never
`bool`, never a string echoed from a neighbouring field.

| case | rows | exact absence set | pinned |
|---|---|---|---|
| `fcx_profile(fiscal_scope=…)` nominal | exact N | `[]` | every row's five fields as literals; `fact_id` distinct per row |
| `mp_profile(fiscal_scope=…)` nominal | exact M | `[]` | same |
| parenthesized negative | N | `[]` | `-20296.0` — a **negative float** on the fact row; sign never in a display string (R-MIN-14) |
| literal appears in Q2 **and** H1 columns, document-wide window | 0 | `["no_span_addressable_evidence"]` | `receipt_for_literal` **refuses** — proves the window obligation (F4) |
| same literal, **cell-scoped** window | 1 | `[]` | the receipt **mints**; `byte_start`/`byte_end` inside the cell span |
| no period column | N−1 | `["missing_period"]` | survivors unchanged |
| basis absent | N−1 | `["missing_basis"]` | — |
| unit/definition mismatch | N−1 | `["missing_units"]` | — |
| ambiguous / duplicate / unaddressable cell | N−1 | `["no_span_addressable_evidence"]` | — |
| body not held | 0 | `["document_bytes_not_held"]` | — |
| accession unjoinable | 0 | `["unjoinable_filing_identity"]` | — |
| two events, same metric | 2 | `[]` | `fact_id` derives from `(event_id, metric, period, basis)`; a **borrowed** id is REFUSED (R-MIN-17) |
| `profile_for_ticker("FCX")` with no `publication` | — | — | resolves to **nothing**; the private branch requires `fiscal_scope` and raises `ValueError` in the pg wording otherwise |

The absence vocabulary is closed to the 14 words in `documents.py:72-87`;
`TypedAbsence.__post_init__` raises on anything else. `missing_derivation`,
`interpretation_stale`, `stream_threshold_unknown` and `definition_unqualified:*` are **T04
limitation strings, never absence reasons** — pin their absence explicitly.

Fixture law is binding: synthetic HTML, invented issuers, sources under `example.invalid`,
invented CIK-shaped ids in fixtures (the real `FCX_CIK`/`MP_CIK` appear only as module identity
constants), `synthetic: true` on every case. **Never a live FCX or MP figure in a test or in CI
evidence** — that is a G2 gate, not a style preference.

## 3. Mutant set — Audit A's three, plus five the seat adds

Audit A: **(a)** widen the receipt window to the whole body → expect `DUP` `ReceiptError`;
**(b)** swap the Q2/H1 column header → the value must change or become an absence; **(c)** add
`"FCX"` to the public branch of `profile_for_ticker` → a test must fail.

Seat additions, each aimed at a defect this program has actually shipped:

- **(d)** `fact_id` → `f"fact_{metric}"` (the sibling's open probe defect, F10). Must be killed
  by the two-event distinctness test. If it survives, the distinctness test is decorative.
- **(e)** drop the sign in `parse_mining_literal` (return `+20296.0`). Must be killed — a
  sign-only mutant is the cheapest possible real defect.
**STRUCTURAL PRECONDITION (added 2026-09-27, measured on `origin/main`) — this packet's
oracle describes the POST-#7905 shape, which does not exist yet.** §3's
`profile_for_ticker("FCX")` row and mutant (d) both speak of a *private branch* that requires
`fiscal_scope` and raises `ValueError`, and of a *public branch* to mutate. On main there is
neither:

- `def profile_for_ticker(ticker: str) -> IssuerProfile | None:` at
  `engine/company_intelligence/issuer_profiles.py:1293` — the **only** definition of the name.
- `fiscal_scope` occurs **zero** times in that file; the body contains **zero** `raise`
  statements. An unknown ticker returns `None`, it does not raise.
- There is no private/public split: an `AAPL` special case, then
  `_HOMEBUILDER_PROFILE_FACTORIES.get(normalized)` (dict literal at `:1272`; the identity twin
  `_HOMEBUILDER_ISSUER_FACTORIES` at `:128`).
- **There is no registration seam** — no `register_profile()`, no plugin hook. Both dicts are
  module-level literals, and `__all__` at `:1307` enumerates every exported symbol by hand.

So this is a precondition, not a defect in the packet: **#7905 introduces the branch split and
T02 appends into it.** Two consequences bind a lane.

1. **If `fiscal_scope` is still absent from `issuer_profiles.py`, #7905 has not landed and T02 is
   NOT dispatchable.** That is the cheapest lawful check of the gate, and it reads `main` — never
   #7905, which must not be polled. Do not build the private/public split yourself: that is
   #7905's hunk in a shared file its incumbent owns, and doing it here violates this program's
   own landmine about shared files being touched only at named seams.
2. **Do not put `"FCX"`/`"MP"` into a dict named `_HOMEBUILDER_*`.** That is the wrong-but-easy
   move the current shape invites. Mining's tickers belong in Mining's own factory mapping, with
   `profile_for_ticker` consulting it — the same pattern #7905 establishes for consumer
   defensive. Expect a conflict at all four sites (`:128`, `:1272`, the two `*_for_ticker`
   bodies, `__all__`) whenever a sibling sector program lands first: this shared dispatcher is
   the `legacy-jobs.yml` append-LAST problem expressed in Python, so re-fetch `origin/main` and
   re-diff before pushing, and a conflict there usually means a sibling already landed.

**Symbol note (added 2026-09-27, measured against `origin/main`):** neither
`MINING_PRIVATE_RIGHTS_PROFILE` nor `DISCOVERY_TICKERS` resolves anywhere in `engine/`, `tests/`
or `contracts/`, and both misses are CORRECT — T02 mints the first, and the second is held for
#7870 (§1). Stated explicitly because a lane that greps a name and finds nothing cannot tell
*not yet minted* from *wrong name*, and one such phantom in the T03 packet had produced a
requirement that passed for free. Every other identifier this packet names resolves, including
the casebook seam R-MIN-34 depends on: `tests/mining_casebook.py:43` `_merge` (merge-only, no
delete), `:67` `_bundle`, `:76` `financial_packets=(dict(fixture["economics"]),) if "economics"
in fixture else ()` — which is exactly why a `bundle={...}` override is silently ignored — and
`:83` `synthetic_case`.

- **(f)** change `MINING_PRIVATE_RIGHTS_PROFILE` to any other token, or declare it outside
  `qa_exchange.py`. Must be killed by the single-declarer probe (F12).
- **(g)** substitute a non-vocabulary absence word. Must raise in
  `TypedAbsence.__post_init__` — if it does not, the closed vocabulary is not actually closed
  on this path.
- **(h)** `ReceiptError` → fall back to a first-occurrence match instead of a typed absence.
  Must be killed. "Never a fallback match" is the whole point of the selector law.

Every survivor is either killed or argued **equivalent on the code path** — unreachable past a
named preceding guard, with that guard itself pinned by a different killed mutant. That is the
standard M11 met on T04a; nothing weaker counts.

## 4. Anti-letter-gaming rules (paid for on T04a)

1. Literal pins only — never a value derivable from another field of the same fixture. T04a
   round 2 passed count-and-flag probes with both legs filled from `period_kind`.
2. Every ordering/sign/polarity pin carries a **reversed** case (R-MIN-33d).
3. Every boolean pin asserts **both** states.
4. Absence sets compared `== sorted(...)`, never `in`/subset — a subset check cannot see a
   spurious extra reason.
5. Non-finite reals rejected explicitly; `nan == nan` is False, so `nan` slips equality guards
   as well as numeric ones (R-MIN-33c).
6. A field accepted but never read is a live defect, not a later task.

## 5. Delivery gates — "not done unless"

- Probes committed **RED first**, in their own commit; the receipt is commit order.
- `tests/test_mining_witness_profiles.py` green, **plus** `tests/test_issuer_profiles.py` and
  `tests/test_event_workspace_build.py` green — the shared-owner edit must not move a sibling.
- The `issuer_profiles.py` edit is ONE contiguous block + 2 merge lines, the branch appended
  **after** the PG branch, homebuilder dicts untouched (R-IND-10 transfers verbatim).
- T02 **mints** the Mining CI job (Audit A line 183) — `scope: exclusive`, appended at the END
  of a freshly fetched main, `paths:` ⊇ every test in `run:` **and** the import closure,
  including `qa_exchange.py`. Note `.github/ci/legacy-jobs.yml` is the fleet's
  highest-conflict file; expect to merge main and keep BOTH blocks (R-MIN-33f).
- Mutation run per §3. Review per R-MIN-33e with evidence inline.
- Before waiting on any check: assert `mergeable != false`, and watch with the canonical
  `scratchpad/watch_pr.sh` (R-MIN-33f).
