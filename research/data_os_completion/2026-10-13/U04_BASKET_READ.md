# U04 — the mode-bound basket composition read

Programme DATA-OS-COMPLETION · lane U04-1 · run `dataos-u04-1` · 2026-10-13.

## Purpose

A basket number used to be assembled from three reads that never met: a
membership answer from `engine/basket_membership_pit.members_asof` (which may
silently answer on today's membership applied backward), an identity mapping
done by ticker string, and a price read made under nobody's contract. This lane
adds `lib/dataos/basket_read.py`: one pure composition read that takes ONE
`ReadRequest` and ONE price `ReadResult` made under it, asks the membership
store for the day that mode implies, resolves every member ticker to a listing
id for that same day, and returns the same price result with a C02 coverage
account over the basket population plus a `basket` evidence block.

## Law

- **D00.D1** — CURRENT / RECONSTRUCT / REPLAY are explicit modes; one request
  decides the mode for every input, so a REPLAY output is refused here: it is
  replayed whole by `read_contract.replay`, never re-composed from parts.
- **D00.D2** — a storage key (the ticker string) is never an identity; members
  are accounted by listing id, and an unresolved ticker stays in the population
  as `unresolved:<ticker>` with `NEVER_INSPECTED` rather than being dropped.
- **D00.D4** — fallback is context only, never a substitute: a `pit=False`
  membership answer is evidence of a look-ahead basis, and a declared fallback
  price source makes a member `FALLBACK` (`displayable`, never `qualified`).
- **C02** (`read_contract.account_coverage`) — the coverage owner: one member,
  one disposition; the population is the frozen denominator; identity/basis
  drift and undeclared fallbacks are C02 demotions, not re-implemented here.
- **`engine/basket_membership_pit.py`, "THE READER'S CONTRACT"** — `pit=False`
  means the store does not cover the date and current membership was applied
  backward (look-ahead); `ths_concept_dump` and `membership` are different
  populations.

## Vocabulary

- `PopulationKind` — which population answered: `CURATED_CAPPED` (the seeded,
  capped subset the engine tracks, shape `membership`) or `VENDOR_UNIVERSE`
  (the raw vendor concept dump, shape `ths_concept_dump`).
- `EvidenceMode` — how the membership answer was sourced: `PIT_SNAPSHOT`
  (`pit=True`) or `CURRENT_MEMBERSHIP` (`pit=False`, look-ahead).
- `BasketRefusalCode` — the closed 20-code refusal vocabulary; every refusal is
  a `BasketReadRefusal` (a `ReadContractError` whose `str()` leads with the code).

## Read order (each step refuses before the next runs)

1. Mode — REPLAY is refused (`MODE_UNSUPPORTED`).
2. Price read — mode, contract, cutoff/clock (RECONSTRUCT), unaccounted, and
   `prices` bound, in that order.
3. Day — suite anchor known; RECONSTRUCT derives the venue-local day before the
   cutoff and refuses a caller `session_day`; CURRENT requires a calendar date.
4. Membership — the reader answers for that day and must echo basket, suite and
   day.
5. Validity — lawful `(pit, basis)` pair, known basket, lawful non-empty member
   list, no duplicate ticker, no look-ahead under RECONSTRUCT, snapshot not
   dated after the day, then evidence mode, population kind and its match
   against `expected_population`.
6. Identity — one listing id per ticker for that day; `None` is unresolved,
   anything else must round-trip through `listing_id(parse_listing_key(v))`,
   and a resolver that raises `IdentityError` is refused as `MALFORMED_IDENTITY`
   (repair r1: never a quiet `NEVER_INSPECTED`).
7. Dispositions — rows grouped by `listing_id`; unresolved `NEVER_INSPECTED`,
   unpriced `MISSING`/`NO_COVERAGE`, primary-only `SERVED`, declared-fallback
   `FALLBACK` (fallback segments only, so C02 never misreads the primary rows as
   an undeclared source); outside rows counted, never refused.
8. Account — `account_coverage` builds the C02 account; its `ReadRefusal` (for
   example two tickers on one listing) is deliberately not caught.
9. Result — `dataclasses.replace` of the price read with the coverage account
   and the `basket` evidence block; the input read is never mutated.

## The day rule

RECONSTRUCT uses the cutoff's venue-local calendar day minus one
(`_SUITE_TZ_MIC` anchors the suite to a venue TIMEZONE only — it is not a
listing venue and says nothing about where a member trades). This is a declared
conservative convention, not a proof: the membership store carries no knowledge
clock, so a snapshot dated on the cutoff's own local day is not provably known
BY the cutoff. CURRENT takes the caller's session day and marks the membership
`CURRENT_MEMBERSHIP` explicitly.

## Populations

The curated capped population (~3.5k member-slots the engine tracks) and the
raw vendor concept universe (~9k slots in the earliest side-car) are distinct
`PopulationKind`s. They are never accounted as one population and
`population_delta` refuses to difference them (`POPULATION_KIND_MISMATCH`):
differencing across that boundary measures the seeding cap, not churn. The
vendor dump's members are point-in-time but its concept-to-basket mapping is
today's document, so its read carries `concept_mapping: "current"`.

## Acceptance map

| Acceptance | Proven by |
| --- | --- |
| U04.01 one mode binds membership, identity and price | `test_u04_reconstruct_binds_membership_identity_and_price_to_one_request`; the step-2/3/4 refusal tests (`MODE_MISMATCH`, `CONTRACT_MISMATCH`, `CUTOFF_MISMATCH`, `DAY_CONFLICT`, `MEMBERSHIP_ECHO_MISMATCH`) |
| U04.02 `pit=False` never funds a historical claim | `test_u04_lookahead_membership_never_funds_a_reconstruction`; `test_u04_current_read_is_labelled_current_and_marks_current_membership` |
| U04.03 distinct populations | `test_u04_population_kind_follows_the_source_shape`, `test_u04_population_kind_mismatch_is_refused`, `test_u04_population_delta_refuses_across_boundaries`, `test_u04_vendor_universe_read_carries_the_current_concept_mapping_caveat` |
| U04.04 no GMI/theme/allocation/writer/schedule change | P5/P6 diff proofs against the start commit (only the three owned paths; `engine/`, `scripts/`, `config/`, `app/`, `lib/dataos/__init__.py`, `.github/` untouched) |

## What is NOT built

- No production caller: nothing invokes `read_basket` yet.
- No change to `members_asof`, GMI, theme, allocation, any writer or any
  schedule; no knowledge clock is added to the membership store.
- The new names are NOT re-exported by `lib/dataos/__init__.py` (a seat act).
- CI wiring is a seat-applied patch: the suite rides the pandas
  `dataos-identity-seams` job once the seat applies it; until then
  `check_contract_delta` reports it as the one introduced unwired suite.

## Evidence class: synthetic

All fixtures are synthetic; the suite needs no `data/` files, no network and no
wall clock, and the membership reader and resolver are injected fakes.
