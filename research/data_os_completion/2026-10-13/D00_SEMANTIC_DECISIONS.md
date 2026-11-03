# D00 — Data OS completion: the six principal semantic decisions

**Status:** FROZEN v1 (2026-10-13), Fable Meta-CEO seat `972d2923`, Chairman masterplan
`Mastermind_Data_OS_Integrity_Fable_Masterplan_2026-10-13` (plan text: PR #9121).
**Design home:** this file is the completion-programme delta to
`research/MASTERMIND_DATA_OS_ARCHITECTURE.md` (§D1–§D11 there keep their numbering; the
decisions below are the masterplan's D1–D6 and are cited as `D00.D1` … `D00.D6`).
**Scope of authority:** ordinary reversible design inside the assigned programme. Writing a
decision here changes no global contract, no rights, no production selection and no source
ownership. Reserved gates (rights, access, production release, source-owner custody) stay real.
**Revision rule (D00.04):** the supported population, action families and financial
conventions below change only by a new dated revision of this file written *before* the
result it would excuse; a later failed case never edits v1.

## D00.D1 — Query meaning: three modes, three evidence obligations

A canonical read carries an explicit `mode`. One `as_of` switch never promises all three.

| mode | question answered | evidence the result must bind | what it may never claim |
|---|---|---|---|
| `CURRENT` | what the house holds now | source receipt(s) of the rows served, identity generation id, action revision set id, producing code version | any historical "as it was" statement |
| `RECONSTRUCT(cutoff, clock)` | what qualified information was available by `cutoff` | the clock used per dataset (`published_at` = publisher availability, `ingested_at` = first system observation; `lib/dataos/temporal.py::KNOWN_AT_CLOCKS` declares which exist), the `known_at <= cutoff` filter applied to **every** dependency (price rows, action revisions, alias/master generation, membership snapshot), code version | that it is a replay. It is a current-code recomputation (ARCHITECTURE §3.2 "recomputable"); the label is `reconstruction`. A `DERIVED` profile has no clock and the read RAISES (`PointInTimeError`), it never returns latest. |
| `REPLAY(output_id)` | what the system actually emitted | the retained artifact's original identity, its exact-byte sha256, the receipt that published it | anything when no retained output exists → typed refusal `NO_RETAINED_OUTPUT`; a generated label is never substituted for retained bytes |

Publication is not observation (design vector V08): a row `published_at < cutoff` but
`ingested_at > cutoff` is **eligible** under `clock=published_at` and **ineligible** under
`clock=ingested_at`; the receipt names the clock so the two can never be confused. A later
correction of an earlier event date is excluded from the earlier observed view (V09).
`as_of_filter` filters *rows*; eligibility of *revisions* and of the dependency *generation* is
the higher-level contract (`read_contract.py`, T01/T02) layered on top, not a change to the
helper's existing callers.

## D00.D2 — Identity continuity: five names, one owner each

| name | meaning | owner | continuity rule |
|---|---|---|---|
| `security_id` | the stable house security (`lib/dataos/identity.py::security_id`) | identity module + curated seams (`config/identity_seams.yml`, `IssuerMaster` era-gated correction) | preserved across a **curated, provenance-backed** rename or listing transfer only |
| `listing_id` | security @ MIC (`listing_id`) | identity module | a listing transfer ends one listing interval and starts another; the security may continue |
| `issuer_id` | the issuing entity (CIK-anchored) | `IssuerMaster` | same issuer never implies same security; share classes are distinct securities |
| vendor symbol | a vendor's spelling, namespaced per vendor, half-open validity `[valid_from, valid_to)` per namespace (V12) | `VendorAliasTable` | a reused ticker is a **new** security even when names or price levels look alike; each namespace observes its own interval |
| storage key | the file key of the physical store (`data/stocks/{ticker}.parquet`, Terminal `{symbol}.json`) | the producer of that store | a storage key is a vendor spelling frozen at write time, never an identity; the read contract resolves it through the alias table and reports the binding |

Insufficient on their own, always: same CIK, unchanged company name, FIGI at a different
assignment level (S33), same price path, same storage key. Mergers and spin-offs are an
**economic successor relation**, not an identity overwrite; this programme declares successor
economics `UNSUPPORTED` and refuses rather than coercing (see D3). No new identifier system, no
rename map derived from Terminal heuristics, no second allocator. The #8637 identity candidate
is adopted through its original carrier (I01); #7299's security-master builder is reconciled,
never re-implemented.

## D00.D3 — Economic units: what RAW, SADJ and TRADJ mean here

Per `lib/dataos/price.py::AdjustmentBasis` (naming law unchanged). Currency is the listing
currency; no FX is applied in any view.

| basis | definition in this programme | share basis | lawful for | refuses when |
|---|---|---|---|---|
| `RAW` | the printed exchange price of the listing on that session | shares as traded that day | limit/tick/exchange rules, execution, tax (`DNR:KILL-CN-ADJUSTED-TAPE-LEGAL-LIMIT` stays binding) | never adjusted; a vendor-adjusted series can never be labelled RAW |
| `SADJ` | `P_sadj(t) = P_raw(t) / S(t; v)` with `S(t; v) = ∏ r_e` over qualified split events `e` with `ex_date > t` in action revision set `v`; `r_e` is an exact rational (2:1 → `Fraction(2,1)`, 1:10 reverse → `Fraction(1,10)`) | the share basis at `as_at` (default: request time; under `RECONSTRUCT`, the cutoff) | structure math, levels, chart continuity | an input already adjusted (`is_ambiguous` or basis ≠ RAW) would be adjusted twice; a ratio is zero/negative/unknown; OHLC rows mix bases |
| `TRADJ` | the vendor-normalized adjusted close (yahoo `auto_adjust`, measured as total_return in the registry) — a **vendor total-return proxy** | vendor's current share basis | performance and attribution *as a proxy*, explicitly labelled | used against a printed price, as an executable price, or as a brokerage cash-flow ledger (P04.04) |
| house `TOTAL_RETURN` view | a separately computed holding-plus-cash oracle under a **declared** policy: `reinvest=NONE` (cash held) or `reinvest=EX_DATE_CLOSE`; withholding = none unless declared | post-event share count | economic total-return questions where every event in the window is qualified | any event in the window is unsupported, or withholding/FX/reinvestment/ordering the request needs is unknown (P04.03) |

Volume transforms only under a split, by the declared convention `vol_adj = vol_raw × r_e`
(V03); cash dividends never apply an inverse split-volume transform (P03.03). A split changes
the price/share unit, not holding wealth (V01/V02); a common scalar on both endpoints cancels
(V04); split-first cash on new shares differs from cash on the old count (V07) and the view
states which it used. Original cash, current-share adjusted cash and a price factor are three
distinct facts and never substitute for one another (P04.02).

**Supported action families (v1):** forward split, reverse split, ordinary cash dividend.
**Unsupported (typed refusal `UNSUPPORTED_ACTION`, never coerced):** rights issues, spin-offs,
mergers, return-of-capital specials, stock dividends, scrip options. An action inferred solely
from a price discontinuity is never admitted as a confirmed event (P01.02); the only admitted
source of events is a qualified original observation with its own receipt (P02).

### D00.D3 clarification (seat ruling 2026-10-17) — ABSENT vs UNRESOLVED

The product `S(t; v) = ∏ r_e` runs over QUALIFIED split events. Two situations were conflated by
the Q01 oracle's pre-registration and are now distinguished:

- **ABSENT** — the revision set contains no split observation at all for the window. The product is
  empty and the factor is 1. This is the oracle's pre-registered reading and it stands.
- **UNRESOLVED** — the revision set CONTAINS an observation whose qualification is `INFERRED`
  (P01.02: a discontinuity-inferred action is never admitted as a confirmed event). The share basis of
  the window cannot be asserted either way: applying the ratio would admit an unqualified event,
  and computing factor 1 would state "no split happened" without a qualified receipt — the false
  consensus C03 exists to prevent. `split_factor`, `sadj_view` and `total_return_view` therefore
  refuse with the typed `NOT_CONFIRMED` (D4: context may be shown, computation refuses). RAW is
  untouched.

Consequence recorded in `Q01_ORACLE.md` (FINDING F1 CLOSED-BY-RULING): the strict-xfail pin
`test_Q01_06_not_confirmed_pre_registered_oracle_factor` was replaced by
`test_Q01_06_not_confirmed_is_a_typed_refusal_by_ruling` in PR #9273 (commit b1ca917a0b7d).
No library change was needed — the SUT already behaved this way at first run.

## D00.D4 — Compatibility and absence: context is shown, computation refuses

Fallback is **context, never a substitute**. It may be shown when (a) the fallback row has the
same basis and session convention as the requested view, (b) `view_contract.fallback` names the
dataset, clock and reason, and (c) the request mode allows a non-primary source. A requested
computation **refuses** (typed, per member) when a member has no eligible row, members mix
bases, sources would have to be averaged without a `CROSS_VALIDATE` policy, or a current
snapshot would stand in for a historical one.

Never: drop a member silently, synthesize a traded open (Terminal's `synthetic_open_deepstore`
bar-quality marker (`ingest/sample_from_macro.py`) is displayed, never passed as a traded open), average incompatible sources, or relabel a
current snapshot to achieve a clean aggregate. Coverage is reported over the **frozen request
population** as `{requested, delivered, fallback[reason], refused[reason]}`; a refusal affects
one member without changing the denominator (V11). Source disagreement is explained (per
ARCHITECTURE §7 discrepancy states), never forced into consensus (C03).

## D00.D5 — Publication and correction: generations, one pointer, receipts

Reuse the existing owner's transition: the security-master producer's generation + `_receipt`
seam (`scripts/build_security_master.py`) and the registry's receipt vocabulary. Rules:

1. A generation is immutable and complete (alias table + master + receipt captured together,
   I02.01); the current pointer moves atomically to a complete generation only.
2. A correction publishes a **new** generation carrying `supersedes=<old generation id>`; the
   superseded generation stays readable by id for `RECONSTRUCT`/`REPLAY` and is no longer
   selected by `CURRENT`.
3. A receipt-only change (identical Parquet bytes, different receipt) is a new generation and
   a prior refusal cannot disappear because the bytes did not move (I02.02).
4. An interrupted publish is `EFFECT_UNKNOWN` until the pointer target is validated against
   its own receipt; reconciliation reads, it never re-runs the write.
5. Exact replay is promised only when the original output and its material are retained
   (T02.01); otherwise the read is a reconstruction and says so.

## D00.D6 — Scope and acceptance: the frozen matrix

| consumer | surface | dataset(s) | market population (v1 positive witness) | acceptance owner |
|---|---|---|---|---|
| A | Terminal daily OHLC + data-origin readout in the existing `ChartFrameBar.tsx` controls | Terminal `ingest/build_universe.py::build_ohlc_json` output (polygon/massive bars), via the canonical view contract | US (XNAS, XNYS, ARCX) | U01/U02 |
| B | existing `DataWorkspace` canonical read (`lib/dataos/web_workspace.py`, `web_api.py`) | `equity.bars.daily.stocks` (yahoo, `data/stocks/{ticker}.parquet`) + security master/alias generation | US | U03 |
| C | existing basket membership/price composition (`engine/basket_membership_pit.py` suites) | basket membership histories + the same price view | US suites | U04 |

- **HK and CN** are enrolled for identity normalization only (`normalize_hk_symbol`,
  `normalize_cn_symbol`); no HK/CN price-view positive witness is claimed in v1 and the gap is
  reported as coverage, not hidden. CN limit arithmetic stays on RAW per the standing kill.
- **Baseline (Q00):** `tests/test_dataos_*.py`, `tests/test_price_ladder.py`, Terminal ingest
  tests and `terminal/lib/__tests__` at the pinned heads (Macro `5569baad`, Terminal
  `4005275c`); accepted unchanged results are reused, never re-proven by habit.
- **Ordinary source cycle:** one nightly collector run producing one coherent generation.
  Second-cycle acceptance (R03) = two consecutive nightly cycles produce coherent generations
  with the pointer transition above and no refusal regression.
- **Release/rollback (A03):** rollback = pointer revert to the previous complete generation
  plus Terminal JSON regeneration from it; the superseded generation remains readable.
- **Rights:** purchase/access, internal computation and redistribution are distinct (K01.02);
  the twenty PROPOSED Tiingo contracts stay PROPOSED unless their original owner produces them
  (R00.04); no raw licensed rows leave the existing read roots.

## The view contract every request must carry (D00.01)

`purpose` · `identity` (`security_id`, `listing_id`, resolved vendor binding + namespace
interval) · `field_units` (currency, share basis, volume convention) · `adjustment_reference`
(basis, action revision set id, `as_at`) · `evidence_mode` (mode, clock used, dependency
generation ids, code version) · `coverage` · `refusal_reasons[]`. All of it is declared before
implementation results are seen; the specification signature in the masterplan
(`canonical_price_view(request, *, server_context, supplied_original_receipts)`) is a
composition of existing readers, not a new store, registry, allocator or evaluator (D11).

## Amendments

- **D00.A1 (2026-10-13)** — venue-local `as_at` day for action admission (D00.D3), declared currency units on
  price rows (D00.D3 / D00.01), consumer-A venues `[XNYS, XNAS, XASE, ARCX]` and the `TRADJ`-labelled v1
  witness with its readout obligation (D00.D6). Full text: `D00_A1_AMENDMENT.md`;
  decision `DEC:DATAOS-D00-A1-VENUE-CLOCK-UNITS-SCOPE`.
- **D00.A2 (2026-10-17)** — D00.D3 clarification ABSENT vs UNRESOLVED: an empty split product is
  factor 1 (ABSENT); a window that CONTAINS an `INFERRED` observation is UNRESOLVED and `split_factor` /
  `sadj_view` / `total_return_view` refuse with the typed `NOT_CONFIRMED` (D00.D4); RAW untouched.
  Pinned by `tests/verification/test_oracle_q01.py` (PR #9273, commit b1ca917a0b7d);
  decision `DEC:DATAOS-D00-D3-ABSENT-VS-UNRESOLVED`.
