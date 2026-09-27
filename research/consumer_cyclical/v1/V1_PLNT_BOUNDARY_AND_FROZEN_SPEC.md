# Consumer Cyclical V1 PLNT — principal boundary adjudication + frozen build spec

**Operation:** `gmi-consumer-cyclical-v1-integration-20260924-fable-001`
**Principal:** Fable integration owner (this carrier)
**Carrier:** `claude/consumer-cyclical-v1-plnt`
**Source packet:** R15 `FABLE_INTEGRATION_READY_R15.md` @ `3d286719686d285a64e31e3059f366885c5ab172` (PR #7804, DRAFT/HOLD)

This file is the frozen boundary for V1. Workers implement against THIS file.
It creates no authority; it records what was re-pinned and what was adjudicated.

## 0. Admission edge (R15 §Routing / placement receipt)

R15 froze this operation at `PLACEMENT_STATE: WAITING_CAPACITY`, `RECEIVER_ASSIGNMENT: NONE`,
`EXECUTION_STATE: PRE_START`, `FABLE_DISPATCH: NOT_SENT`, and forbids self-selection: "Do not convert
this into `OPEN_PICKUP`, select a numbered account by convenience, arm a receiver watcher, or claim
ACK/START."

That state was lifted by the mechanism R15 itself names in the same paragraph: "When a lawful
Capacity/placement owner **or deliberate live direct handoff** assigns an eligible Fable session,
that delivery becomes the receiver assignment under current law; the worker then performs
pickup/read/watch/START as a separate sequence."

**The admission edge is a deliberate live direct handoff from the Chairman on 2026-09-24**, whose
delivery stated verbatim: "THIS LIVE DELIVERY IS YOUR RECEIVER ASSIGNMENT for operation
`gmi-consumer-cyclical-v1-integration-20260924-fable-001`", instructed this seat to "Read and follow
the R15 packet completely", to "Re-pin current protected Mastermind procedure, Macro main, #7804, and
every affected shared-owner/custody head before any native effect", and named V1 PLNT as the first
executable outcome. No numbered account was self-selected and no receiver watcher was armed.

This receipt is what R15 line 73 requires when it says a future source-modifying wave "must enter
through current lawful custody/workspace/admission". Custody is evidenced in §1; **admission is this
section**. An independent review correctly refused the packet while this receipt was absent — it was
performed but not recorded.

## 1. Re-pin receipt (R15 step 1 — executed 2026-09-24)

Macro `main` at first re-pin: `b076a4004599` (R15 froze at `c99fdde7302d`). **Main moves fast on this
repo** — it was already at `cdcfbb27681e`, then `69c52bbe8df5`, within the same session. Per R15
"Re-pin every affected native group immediately before write", the four blob claims below are
re-verified immediately before each commit, not merely at this timestamp.

Owner heads re-pinned — **five external owner PRs, all byte-identical to the R15 freeze pins, all
OPEN/DRAFT, none merged.** R15 also names **#7331**, but #7331 is a GitHub **issue**
("[K4-G][HOLD-FOR-SOL] Repair event-workspace clocks…", OPEN), not a pull request, and R15 never
pinned a SHA for it — so "byte-identical to the R15 freeze pin" is unsatisfiable for #7331 and it is
listed below as such. #7804 is this program's own research carrier, **not** an external gate, and is
listed separately for that reason.

| Owner | R15 pin | Re-pinned now | State |
|---|---|---|---|
| #7870 shared foundation | `3e3a7956d014...` | `3e3a7956d014` | OPEN draft |
| #7780 build-out ruling | `b68069b2e129...` | `b68069b2e129` | OPEN draft |
| #7669 template owner | `6942b2b62bad...` | `6942b2b62bad` | OPEN draft |
| #7462 theme graph/store | `31706d7322af...` | `31706d7322af` | OPEN draft |
| #7426 company history | `7bc04876747d...` | `7bc04876747d` | OPEN draft |
| #7331 history semantics | *(named by R15; never pinned — it is an issue, not a PR)* | n/a | OPEN issue |

This program's own research carrier, listed separately because it is not an external gate:

| #7804 consumer evidence | `3d286719686d` | `3d286719686d` | OPEN draft |

Affected blob re-pins against current `origin/main`:
- `app/paywall.py` = `7e1c6861ebb7d27924865b2b8d157e6a9356405d` — **unchanged** from R15.
- `tests/test_paywall.py` = `1d958154eed91ee08f9f7ab65b719e1910e2ccd1` — **unchanged** from R15.
- `config/theme_sources.yml` = `e59ce0a9f98e34e45165545f21a84596c23a6de4` — **MOVED** from R15 pin `1073ca1e9841...`.
- `app/theme_research.py` — **ABSENT FROM `main`**. The R15-pinned shared transport blob `f3c70ffd67cc...`
  exists only on the #7870 branch.

## 2. Principal adjudication — what V1 can lawfully reach today

V1 PLNT decomposes into R15's nine implementation steps. Status against current custody:

| # | V1 leg | Status | Evidence |
|---|---|---|---|
| 1 | Pickup / current-source gate | **DONE** | §1 above |
| 2 | Resolve external gates | **BLOCKED** | all six owner heads unmoved; #7780 ruling still open |
| 3 | One lawful V1 product carrier | **OPEN** | collision census §3 |
| 4 | Native PLNT source/measurement qualification | **OPEN** | incumbent SEC owners on `main`, §4 |
| 5 | Consumer deterministic composition | **OPEN** for computation; **BLOCKED** for mount/registration | R15 H2 |
| 6 | Shared private/read transport integration | **BLOCKED** | `app/theme_research.py` absent from `main`; T09 rights veto BUILT_NOT_PROVEN |
| 7 | Company-page consumer | **BLOCKED** | #7669 DRAFT, no custody |
| 8 | Independent review + real proof | **PARTIAL** — provable for 4/5, not for 6/7 | — |
| 9 | V1 `PROVEN_LIVE` | **BLOCKED** — depends on 6/7 | — |

**Ruling.** The entitled, browser-visible closure of V1 is gated by external owners whose heads have not
moved since the R15 freeze. R15 forbids the only constructions that would route around them — no Consumer-only
private publisher or pointer, no forked discriminator grammar, no writes to #7426/#7462/#7669-owned paths, no
second plane of any kind. Therefore legs 6–9 are frozen, **not** rebuilt.

Legs 3–5 are gated by nothing. They are executed now as **V1-CORE**: the deterministic, source-bound Consumer
economic-change composition that legs 6–7 will later publish unchanged. Building V1-CORE does not consume,
weaken, pre-empt or duplicate any blocked owner seam.

**The lawful precedent is already merged.** Finance shipped a vertical to `main` today through the incumbent
`contracts/sector_intelligence/` family while #7870 stayed blocked:
- T1 `#7896` `b4c6e4bdb347` — contract schema + valid fixture + contract test + CI gate job
- T2 `#7920` `e4ac37302968` — `engine/sector_intelligence/finance_projection.py` + tests
- T3 `#7900` `3ca9c3038061` — `engine/sector_intelligence/finance_overlap.py` + tests

None of those touched `app/theme_research.py`, `app/paywall.py`, any template, or any blocked owner PR.
Consumer Cyclical V1-CORE follows that idiom exactly. This **extends an incumbent owner**; it mints no
shell, evidence, rights or transport vocabulary.

**Explicitly preserved gate.** V1-CORE carries NO transport mount identity: no `profile`/
`content_discriminator` registration, no route, no publisher, no pointer. The R15 H2 identity
(`profile=consumer_cyclical`, `content_discriminator=consumer_economic_change.v1`,
`registration_status=PENDING_SHARED_OWNER_ACCEPTANCE`) stays exactly where R15 left it — awaiting the #7780
ruling. V1-CORE is a data shape plus a pure projection, not a mount.

## 2a. Refutation of the leg-6 block (principal ran this against his own ruling)

The leg-6 block was first argued only from `app/theme_research.py` being absent from `main`. That is a weak
reason on its own: a *different* merged private transport could have made leg 6 reachable. Tested directly.

**A merged, entitled, private publication route does exist on `main`:** `app/earnings.py` —
`require_site_full_user` -> `app.paywall.enforce_site_full`, `Cache-Control: private, no-store`, serving
`/api/earnings/v1/records/{slug}` out of private R2 through `engine.earnings_narrative.private_publication`.

It still does not open leg 6, for three independent reasons:

1. **R15 H1 already chose a different family and superseded this one.** "For the new Consumer
   economic-change dossier, R12 supersedes R6's direct Earnings delivery and R7 Task4's proposed changes to
   the Earnings private-publication files. The selected integration family is the same shared POST:
   `/api/themes/v1/research/query` / `/api/themes/v1/research/evidence`." Using `app/earnings.py` would
   overturn an accepted decision locally, which R15 forbids ("do not locally rewrite authority").
2. **R15 H1 pre-labels that exact move as forbidden.** "R7 Task4 becomes compatibility, catalog-preservation
   and next-run non-loss proof against the actual shared owner; **it is not a second publisher**."
3. **Custody.** R6 §3 records that the Earnings member record "is a closed HTML-oriented payload; it does
   not already accept an arbitrary economic JSON view. A versioned owner extension is required." And
   `engine/earnings_narrative/**` is owned by sibling program CDV-1 (#7792) — no custody here.

Leg 6 is therefore blocked on the **accepted-family** ground, which is stronger than the missing-file ground
and does not depend on #7870 file layout. Recorded so a later session does not "discover" `app/earnings.py`
and mistake it for an opening.

## 2b. Contract NAMING also preserves the #7780 gate (independent review finding)

An independent review found that "carries no transport mount identity" covered *registration* but not
*naming*. The first draft named the contract `consumer_cyclical_intelligence_read_model.v1`, which fuses both
values R15 H2 reserves to the open #7780 ruling — `profile = consumer_cyclical` and
`content_discriminator = consumer_economic_change.v1` — into a durable, versioned, CI-gated,
merge-bound filename. Registering nothing while shipping a `.v1` filename that implies the grammar is
a distinction the successor session would not have honoured, and if #7780 ruled differently the repair
would be a contract migration on `main`.

**Resolved by renaming, not by disclosure:** the contract is
`consumer_cyclical_intelligence_read_model.v1`, mirroring the merged sibling
`finance_intelligence_read_model.v1` exactly. That axis — `<sector>_intelligence_read_model` — belongs
to the `contracts/sector_intelligence/` family, is already established on `main`, and is one #7780
cannot contradict, because it is not a transport grammar at all. The reserved discriminator stem
`economic_change` does not appear in any shipped identifier.

## 2c. Why incumbent-extension licenses V1-CORE but not `app/earnings.py`

The same review noted §2a never distinguishes its own licensing argument from the one it refuses.
The distinction is that R15 H1 made an **affirmative family selection** for this dossier's transport —
it chose `/api/themes/v1/research/query` and explicitly superseded direct Earnings delivery. Extending
`app/earnings.py` would therefore contradict a positive, accepted authority choice about *this*
artifact. `contracts/sector_intelligence/` is not a transport at all, so no accepted choice speaks
against it; it carries no route, no entitlement, no publication, and no pointer. Incumbent extension
is lawful exactly where no accepted decision already assigned the seam elsewhere.

## 3. Collision census (R15 step 3)

- **CDV-1 Consumer *Defensive* (#7792, `WS-CONSUMER-DEFENSIVE-CDV1`)** owns `engine/company_intelligence/*`,
  `engine/earnings_narrative/*`, `templates/earnings_wire/*`. V1-CORE writes **none** of those.
- **Finance** owns `engine/sector_intelligence/finance_*`. V1-CORE uses `consumer_cyclical_*`. No overlap.
- No open PR claims `engine/sector_intelligence/consumer*` or
  `contracts/sector_intelligence/consumer_cyclical_*`. Verified against all open PRs 2026-09-24.

## 4. Native PLNT source (R15 step 4)

PLNT is already retained by incumbent source owners on `main` — V1-CORE consumes, never re-collects:
- `data/edgar/ticker_cik_ledger.json` → `tickers.PLNT = 1637207` (CIK `0001637207`).
- `engine/fundamental_forensics/sec_companyfacts.py` — pure SEC Company Facts/Submissions ingestion already
  emitting exact-decimal `FactOccurrence` bound to `SourceFiling` (`decimal_text`, `canonical_json`,
  `stable_id`). This is the M1–M5 exact-decimal + lineage seam; do not re-implement it.

R6 §4 source coordinates for the V1 case (S1):

```text
issuer_cik   = 0001637207
accession    = 0001637207-26-000042
exhibit      = plntq22026pressreleaseex991.htm
event        = PLNT Q2 2026, quarter ended 2026-06-30
sec_acceptance_raw = "2026-08-06 06:30:44"   # UNLABELED — never attach Z,
                                             # never treat as first public availability
```

## 4a. Native admission is NOT achievable today — and must not be faked

Tested: `grep -rl "0001637207-26-000042" data/ config/ engine/` returns nothing. PLNT's **identity** is
native on `main` (`data/edgar/ticker_cik_ledger.json` -> `1637207`), but the **Q2 2026 8-K exhibit
`plntq22026pressreleaseex991.htm` is not retained anywhere**.

Consequences, all binding on the build:

- Every fact in V1-CORE carries `native_admitted = false` and `native_ref = null`. This is not a placeholder
  to be "improved" later by flipping a flag — it is the honest state, and R15 requires it: "Research values
  are expected oracles, never substitute receipts."
- V1-CORE is therefore **source-coordinate-bound, not natively admitted**. It carries and validates the real
  CIK, accession, exhibit, locator and the raw unlabeled acceptance string, and it refuses to present any of
  that as a retained native receipt.
- **Do not collect the filing to close this gap.** Fetching it here would create the source plane R15
  prohibits and would re-home the sticky R8 native-staging denial. Retention belongs to the incumbent source
  owner under R15 step 4. This gap returns to Sol; it is not worked around.
- `engine/fundamental_forensics/sec_companyfacts.py` ingests XBRL Company Facts, not 8-K press-release
  exhibits, so it is not a shortcut to admission for the advertising lines either.

**Stated plainly, because it is load-bearing:** R15 step 3 allows a carrier "only after current source
custody and collision census". What §1 and §3 establish is a custody **census** — who owns what, and
what is retained — not **possession** of the PLNT exhibit, which nobody here has. V1-CORE is lawful
under that reading only because it never presents a non-possessed value as a receipt: `native_admitted`
is false, `native_ref` is null, and the projection refuses to describe either as a retained source. A
wave that needed possession would be blocked here; V1-CORE does not.

## 5. FROZEN GOLDEN ORACLE — R6 §7.1 (acceptance, not a formula service)

All values USD **thousands** (`unit="USD"`, `scale_power10=3`), exact decimal text, signed.
Comparison basis: `explicit_same_quarter_prior_year`.

| key | metric | new | old | change |
|---|---|---|---|---|
| `total_revenue` | total revenue | `365223` | `340879` | `24344` |
| `advertising_revenue` | advertising revenue | `32922` | `22781` | `10141` |
| `advertising_expense` | advertising expense | `32922` | `22777` | `10145` |

Derived, exact:
- `advertising_net_change` = `10141 - 10145` = **`-4`**
- `advertising_current_period_net` = `32922 - 32922` = **`0`**
- `advertising_share_of_revenue_change` = `10141 / 24344` = `0.4165707...` → **`41.66%`** at 2dp

**Precision law (R6 §7.1 refinement of R5):** the two advertising changes are NOT equal at displayed table
precision. Never round both to `$10.1 million`. The `-4` residual must survive. Float arithmetic is banned —
use `decimal.Decimal` throughout. Do not retro-edit R5 evidence.

Explanation envelope (generated from selected results only):
- **Lead:** a substantial part of the revenue increase is associated with advertising flows with nearly
  matching expense, so it does not translate one-for-one into incremental profit.
- **Counterevidence/context:** franchise, corporate-club and equipment economics require their own analysis.
- **Next observation:** comparable dues and retained operating contribution, plus franchisee economics where
  actually disclosed.
- **Does not prove:** organic growth, a complete profit bridge, or a conclusion about franchise health.
- **Forbidden conclusions (must be refused, not merely unsaid):** calling dues "observed visits"; subtracting
  advertising alone and labelling the remainder organic growth.

## 6. FROZEN result semantics (R15 H3 / M1–M5)

1. Exact decimal reported values; preserve unit, scale and sign. `value_text` is canonical decimal **text**.
2. Every ready derived result binds exact input refs plus period/event/clock/precision metadata.
3. **Dependency-local** omission/degradation. Zero ready results ⇒ `unavailable`, **never** empty-ready.
4. Period grain explicit (`quarter`/`half_year`/`year`). Real issuer fiscal calendars stay with their owner.
5. Outlooks require timezone-aware publication clocks and strict prior-before-new order.
6. Ratio **withheld** when the denominator is nonpositive **or** when the declared rounding envelope
   includes zero. Percentages >100 are NOT automatically invalid.
7. Numerical explanation is generated from selected result envelopes, carries counterevidence and next
   observation, and never promotes a forbidden conclusion.
8. Malformed **case shape** may refuse the whole case. Malformed/missing **values** suppress only the
   affected dependency closures.
9. A missing or invalid result is never bearish and never zero.
10. No ranking, entry, gating, sizing or origination authority. Identical inputs must produce an identical
    selection/ranking/entry/sizing outcome — the panel is explanatory only.

## 7. Fact envelope (frozen, from R12 `profile_contract` worked-case shape)

Required per fact: `basis, definition, display_quantum, event, evidence{document,locator,revision}, key,
kind, metric, native_admitted, native_ref, perimeter, period_end, period_kind, period_start, published_at,
role, scale_power10, sign_convention, target, unit, value_text`.

`native_admitted`/`native_ref` carry native admission. Research values are **expected oracles, never
substitute receipts** — a fact whose `native_admitted` is false may not be presented as a retained receipt.

## 8. Build packets

### T1 — contract (owned paths, exclusive)
- `contracts/sector_intelligence/consumer_cyclical_intelligence_read_model.v1.schema.json`
- `data/sector_intelligence/fixtures/consumer_cyclical_intelligence_read_model.v1.valid.json`
- `tests/test_consumer_cyclical_intelligence_read_model_contract.py`
- `.github/ci/legacy-jobs.yml` — new `consumer-cyclical-economic-change` job, mirroring `finance-intelligence`

### T2 — projection (owned paths, exclusive)
- `engine/sector_intelligence/consumer_cyclical_projection.py`
- `tests/test_consumer_cyclical_projection.py`

### Forbidden for both packets
No writes to: `app/theme_research.py`, `app/paywall.py`, `app/earnings.py`, `templates/**`, `site/**`,
`config/theme_sources.yml`, `engine/company_intelligence/**`, `engine/earnings_narrative/**`,
`engine/sector_intelligence/finance_*`, or anything on PR #7804. No new route, publisher, pointer, queue,
identity, rights, retry or evaluation plane. No profile/discriminator registration. No float arithmetic.
No network calls.

## 9. Return / stop condition

V1-CORE merged + green is **not** `V1 PROVEN_LIVE`. It is the maximal lawful V1 subset under current
custody. Legs 6–9 return to Sol as the exact external blocker with the receipts in §1.

## 8a. Integration rulings (principal; made during delivery, bind both packets)

Two conflicts surfaced between the T1 contract and the T2 projection while the packets were being
built in parallel. Neither worker owns both sides, so the principal rules:

**Ruling A — a result envelope is emitted only when its inputs exist.**
`results[].input_refs` is `minItems: 1`, so a "result" with no inputs cannot satisfy the contract and
must not be invented. The two states are distinct and must stay distinct:
- inputs **absent** (a fact or its prior-period pair is missing) -> emit **no** result for that key and
  record the key in `degraded_dependencies`. This is R15's dependency-local omission.
- inputs **present** but the computation is refused (nonpositive denominator, or a declared rounding
  envelope that includes zero) -> emit the result with `value_text: null`, a populated
  `withheld_reason`, and real `input_refs`. This is R15's withholding.
With zero facts, `results` is therefore `[]`, `degraded_dependencies` names every unmet key, and
`availability` is `unavailable` — never `ready`, and never a phantom result whose value is null
because nothing was ever read. A withheld result is an answer about inputs that exist; an omitted
result is the absence of inputs.

**Ruling B — `value_decimal` never reaches the emitted document.**
`Decimal` is the required internal arithmetic carrier and must stay internal: it is not
JSON-serializable, and the contract sets `additionalProperties: false`, so any `value_decimal` key in
an emitted result fails validation. Carry it in intermediate structures if useful, but strip it when
building the document. `value_text` is the only emitted value, and it stays exact decimal text.

**Also adopted from the merged Finance idiom:** the document carries an `authority_caps` object whose
booleans are all `const: false` — `rank`, `gate`, `size`, `trade`, `create_theme`,
`change_membership`, `write_graph`, `admit_source`. This turns R15's "no ranking, entry, gating,
sizing or origination authority" from an absence into a machine-checked assertion, and it is how the
sibling vertical already on `main` expresses the same constraint.
