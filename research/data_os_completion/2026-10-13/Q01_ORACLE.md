# Q01 — independent exact-rational oracle + mutation kill matrix (lane Q01-1)

Programme DATA-OS-COMPLETION. Run id `dataos-q01-1`. Branch
`lane/dataos-q01-1`. The oracle tests live in
`tests/verification/test_oracle_q01.py`; this file is the record required by
the lane (scope, independence, vector table, results, kill matrix, findings).

## Scope

SUT blob pins (verified at step 0.4 against the start commit):

| path (at start commit) | blob |
| --- | --- |
| `lib/dataos/price_views.py` | `9ceb782f6426bc8d701341f433d0d0eb7e8dedb8` |
| `lib/dataos/read_contract.py` | `0aa82b26bbee70b2860ca3d8da89cf33a3f7aac4` |
| `lib/dataos/identity.py` | `a288b38a707548f19f5701d2c35db2e1e48e5d04` |
| `lib/dataos/registry.py` | `65b0d69036da97760f20241468f2549b21d9c686` |
| `lib/dataos/temporal.py` | `094b149a8b9158f19cb99c4005568c12db96ed41` |

Start commit `a0fa900488db2f9270a2ce5cda6f7418a87eb86f` (= origin/main
2026-10-14 02:19Z). Freeze commit `8fb925ed1c8406383b6739d5e958d0a3aa5d0943`.
Interpreter `~/lanes/venv/bin/python` (pytest 9.1.1).

## Independence

Every file opened (read/cat/grep/less/diff/inspect) BEFORE the freeze commit:
NONE. The forbidden set (`lib/dataos/price_views.py`, `read_contract.py`,
`identity.py`, `temporal.py`, `registry.py`, existing `tests/test_*`) was never
opened before the freeze. What DID happen before the freeze, disclosed in
full:

- Step 0.5 sanity: `ls` of directory NAMES only (`tests/`, `research/…/`) — no
  file contents.
- Three SUT shape probes (`~/lanes/tmp/dataos-q01-1/probe{,2,3}.py`), permitted
  by the lane ("You MAY import the SUT and call it to learn ARGUMENT SHAPES"):
  imports + constructor/request calls, printing exception types, enum values,
  refusal `.reason` strings, row key names, and shape errors (e.g. `code_version`
  must be 40-hex; `ViewContract.identity` needs `mic`+`security_id`+
  `listing_id`). No SUT output value was copied into any expectation: every
  expected value in the frozen file comes from the Section A oracle functions
  (derived from the D00.D3 text) or the vector JSON.
- pytest/traceback output from running the suite pre-freeze printed a handful
  of SUT source lines verbatim in exception backtraces (regions near
  `lib/dataos/price_views.py:541/625/1291` and `lib/dataos/read_contract.py:156`).
  This is stdout of calling the SUT, not an intentional read; disclosed here
  rather than hidden.
- The pre-freeze suite run surfaced the not-confirmed disagreement (F1 below)
  and two fixture-construction bugs of mine (a computed `family=` never passed
  to the event builder; the supersede event missing its inherited `sequence`),
  both fixed BEFORE the freeze as fixture bugs — no expectation was changed to
  match the SUT.

First open of each SUT body AFTER the freeze commit (2026-10-14T03:06:03Z):
`lib/dataos/price_views.py` and (for M7) `lib/dataos/identity.py`, read only to
target the mutation matrix. `read_contract.py` was never opened as a body.

## Vector table

`oracle` = Section A function output; `SUT` = view/answer read through the
public interface; `JSON` = section 5.3 vector. All values exact `Fraction`.
Split vectors read through `sadj_view` (row dated 2026-06-09, before every
ex-date) cross-checked with `split_factor` + `adjust_quantity`; return vectors
through `return_vector`; cash vectors through `total_return_view` (two closes
2026-06-09/2026-06-11 straddling ex-date 2026-06-10; V07 declares the split
FIRST via `sequence=0`, cash `sequence=1` — the cash event is deliberately
inserted first in the revision tuple so ordering can only come from
`sequence`); V12 through `VendorAliasTable.vendor_symbol_for` /
`.resolve`.

| V | key | oracle | SUT | JSON | agree? |
| --- | --- | --- | --- | --- | --- |
| V01 | adjusted_price / adjusted_quantity / wealth | 50 / 6 / 300 | 50 / 6 / 300 | "50"/"6"/"300" | yes |
| V02 | adjusted_price / adjusted_quantity / wealth | 50 / 1 / 50 | 50 / 1 / 50 | "50"/"1"/"50" | yes |
| V03 | adjusted_price / adjusted_quantity / wealth | 30 / 3600 / 108000 | 30 / 3600 / 108000 | "30"/"3600"/"108000" | yes |
| V04 | original / rebased / equal | 1/10 / 1/10 / True | 1/10 / 1/10 / True | "1/10"/"1/10"/true | yes |
| V05 | original / rebased / equal | 1/10 / −9/20 / False | 1/10 / −9/20 / False | "1/10"/"−9/20"/false | yes |
| V06 | cash / holding_return / q1 / raw_price_return / wealth | 2 / 0 / 1 / −1/50 / 100 | 2 / 0 / 1 / −1/50 / 100 | same | yes |
| V07 | cash / holding_return / q1 / raw_price_return / wealth | 2 / 0 / 2 / −51/100 / 100 | 2 / 0 / 2 / −51/100 / 100 | same | yes |
| V12 | symbols at 2026-01-06 | ["NEW"] | "NEW" (vs "OLD" on 01-05; `resolve(OLD)`→None) | ["NEW"] | yes |

Plus a derived boundary check (frozen, D00.D3 "ex_date > t" strict): a row
dated ON the ex-date is not adjusted; split_factor = 1 there — agrees.

## Q01.02 uniform scaling

Grid: 4 scalars {1, 2, 1/3, 100/7} × 3 price pairs {100→110, 7→13, 9/4→27/8} =
12 parametrized cases: oracle and SUT `return_vector(p0,p1,s,s)` both give
original == the unscaled original and `equal=True`; non-vacuity asserted
(scaled endpoints differ for s≠1). Whole-series scaling: a 2:1 split over rows
(120, 50) — SADJ simple returns are (−1/6,) for the original series and stay
(−1/6,) when every raw close is multiplied by each scalar, while the SADJ
closes themselves scale by c (non-vacuous). Different endpoint factors
((1,1/2) and (2,1)) DO change the rebased return, and `qualified_return`
refuses both with `RETURN_ACROSS_UNADJUSTED_SPLIT` while answering exactly
when no split crosses. Cash-only event set: `close_sadj == close_raw` and
`volume_sadj == volume_raw` (cash never transforms volume, P03.03). All agree.

## Q01.03 future-mutation immunity

Base revision set (all known before T1=2026-06-20T00:00Z): split 2:1 ex
06-10 (seq 0), split 3:1 ex 06-12, cash 1/share ex 06-10 (seq 1); rows
06-09 (100, vol 10) and 06-11 (50, vol 20). Additions, all `known_at`
2026-06-25 (> T1, < T2=2026-07-01): (a) NEW split 5:1 ex 06-16; (b) SUPERSEDE
of the 2:1 by a 5:2 ex 06-10 (seq 0 inherited); (c) CANCELLATION of the 3:1
(`cancelled=True`, `supersedes`). Result: the T1 view over base+additions is
identical to the T1 view over base — row tuples equal, `split_factor`
equal (6 at 06-09), and every `TotalReturnView` economic field equal
(wealth0/q1/cash/wealth1/holding_return/raw_price_return/events_applied/
executable/policy). Non-vacuity: each addition alone, and all three together,
change the T2 view (rows and factor: 30, 15/2, 2, 25/2 vs 6; the TR view also
moves under "all"). Retain/reopen: `retain_view` froze the T1 view with
payload bytes; after computing the T2 view over base+additions,
`reopen_view` returned byte-identical rows and label (`== view_label`), and
the reopened rows differ from the later view's rows (non-vacuous freeze).

## Q01.04 exactness

Every numeric SUT output read by the suite — `close_sadj`, `volume_sadj`,
`split_factor`, `adjust_quantity`, `return_vector` values, `simple_returns`
items, all seven `TotalReturnView` numeric fields and the `events_applied`
rationals — is a `Fraction` (or `int`), never `float`/`Decimal`. A float in
`close_raw` (`sadj_view`), in `volume_raw` (`sadj_view`), or in `close_raw`
(`total_return_view`) refuses `NON_EXACT_INPUT` in all three cases. Agree.

## Refusal oracle

| expectation (D00.D3 sentence) | source sentence | observed | agree? |
| --- | --- | --- | --- |
| SPIN_OFF never coerced → `UNSUPPORTED_ACTION` (sadj_view) | "Unsupported (typed refusal UNSUPPORTED_ACTION, never coerced): … spin-offs" | `UNSUPPORTED_ACTION` | yes |
| any unsupported event in the TR window → `UNSUPPORTED_ACTION` (total_return_view) | "refuses [when] any event in the window is unsupported" | `UNSUPPORTED_ACTION` | yes |
| ratio 0 → `INVALID_RATIO` (split_factor and sadj_view) | "a ratio is zero/negative/unknown" | `INVALID_RATIO` both | yes |
| ratio −2 → `INVALID_RATIO` (split_factor) | same | `INVALID_RATIO` | yes |
| split ratio None → `UNKNOWN_RATIO` (split_factor and sadj_view) | same | `UNKNOWN_RATIO` both | yes |
| INFERRED split not applied as confirmed | "an action inferred … is never admitted as a confirmed event (P01.02)" | SUT raises `NOT_CONFIRMED`; oracle pre-registered factor stays 1 | **FINDING F1** (strict-xfail) |
| non-raw price column refused (reason recorded) | "an input already adjusted … would be adjusted twice" | `MIXED_OHLC_BASIS` (bases {raw,sadj} in one row); a uniform `*_sadj`-only input maps to `DOUBLE_ADJUST_RISK` per the SUT's column-law order | yes (reason recorded) |
| OHLC rows mixing bases → `MIXED_OHLC_BASIS` | "OHLC rows mix bases" | `MIXED_OHLC_BASIS` | yes |
| k0≠k1 executable return refused → `RETURN_ACROSS_UNADJUSTED_SPLIT` | "a return only when no split crosses the interval" | same | yes |

## Mutation kill matrix

Each mutation applied only in the detached worktree
`~/lanes/wt/dataos-q01-1-mut` (removed afterwards); diffs saved under
`~/lanes/tmp/dataos-q01-1/`. No post-freeze tests were needed (no survivors).

| id | file:line | diff (≤10 lines) | frozen-suite failures | killed? | post-freeze |
| --- | --- | --- | --- | --- | --- |
| M1 | `lib/dataos/price_views.py:627` | `factor *= contribution` → `factor *= Fraction(1) / contribution` | `V01`,`V02`,`V03`,`ex_date_boundary`,`sadj_scaling`,`Q01_03_immunity` (6) | yes | n/a |
| M2 | `lib/dataos/price_views.py:458-463` | sort key third element → `-(e.sequence …)` (reverse same-day sequence) | `V07` (1) | yes | n/a |
| M3a | `lib/dataos/price_views.py:623` | `t < event.ex_date` → `t <= event.ex_date` (row ON ex-date adjusted) | `ex_date_boundary` (1) | yes | n/a |
| M3b | `lib/dataos/price_views.py:416` | `event.known_at <= as_at` → `event.ex_date <= as_at.date()` | `Q01_03_immunity` (1) | yes | n/a |
| M4a | `lib/dataos/price_views.py:511` | `if event.qualification != CONFIRMED:` → `if False and …` | `not_confirmed_never_applied_as_confirmed` (1) | yes | n/a |
| M4b | `lib/dataos/price_views.py:850,857,864` | basis law disabled: `len(bases) > 1`, `basis is SADJ`, `basis is TRADJ` each guarded with `False and` | `non_raw_refused`, `mixed_ohlc_refused` (2) | yes | n/a |
| M5 | `lib/dataos/price_views.py:625` | `contribution = _check_window_event(event)` wrapped in `try/except ViewRefusal: contribution = Fraction(1)` | 6× `typed_refusals[…]` + strict-XPASS of the F1 xfail (7) | yes | n/a |
| M6 | `lib/dataos/price_views.py:1308-1315,1359` | cash `amount = q * …` → `amount = day_start_q * …` (count before that ex-date's events) | `V07` (1) | yes | n/a |
| M7 | `lib/dataos/identity.py:811` | `on >= self.valid_to` → `on > self.valid_to` (closed interval) | `V12` (1) | yes | n/a |

Killed: **9/9**.

## Findings

**F1 (GAP, recorded as a strict xfail — not fixed, lib/ untouched).**
Oracle says: an INFERRED-qualification split is not a *qualified* event, so
per "S(t; v) = ∏ r_e over qualified split events" it simply does not enter the
product (`split_factor` stays 1), and the D00.D3 "refuses when" column for
SADJ does not list qualification. SUT says: a typed `NOT_CONFIRMED` refusal.
Both outcomes honour "never admitted as a confirmed event"; the D00.D3 text
does not by itself select between them. Reproducer (5 lines):

```python
from datetime import date, datetime, timezone
from fractions import Fraction
from lib.dataos.price_views import ActionEvent, ActionFamily, ActionRevisionSet, split_factor, ViewRefusal
e = ActionEvent(event_id="f1", family=ActionFamily.FORWARD_SPLIT, ex_date=date(2026, 6, 10),
                known_at=datetime(2026, 1, 1, tzinfo=timezone.utc), source_receipt="rcpt:f1",
                qualification="INFERRED", ratio=Fraction(2))
try: split_factor(date(2026, 6, 9), ActionRevisionSet("f1", (e,)), datetime(2026, 6, 20, tzinfo=timezone.utc), mic="XNYS")
except ViewRefusal as vr: print("SUT:", vr.reason)   # -> SUT: not_confirmed  (oracle expected: Fraction(1), no refusal)
```

Kept as `@pytest.mark.xfail(strict=True, reason="Q01 FINDING F1: …")` in the
frozen suite; a companion passing test pins the shared invariant (the factor
may never become the ratio) and is what kills M4a/M5. The suite is not yet
wired into CI (the orchestrator applies the `.github/ci/legacy-jobs.yml`
patch).

## No alpha conclusion

These tests prove arithmetic and refusal semantics only: that exact-rational
split adjustment, volume conventions, rebased-return algebra, holding-plus-cash
total-return arithmetic, half-open alias validity, point-in-time immunity and
typed refusals behave as the D00.D3 decision text specifies, on fully
synthetic inputs, and that deliberately breaking each rule is caught. Nothing
here is a claim about any return, signal, performance or market, and no real
data row was read or printed. No market conclusion of any kind follows.

## Commands

- `PY -m pytest tests/verification/test_oracle_q01.py -rs` (run twice) →
  `46 passed, 1 xfailed` both runs (see P1 in the return packet).
- `PY -m pytest tests/verification/test_oracle_q01.py -q -p no:cacheprovider`
  in `~/lanes/wt/dataos-q01-1-mut` per mutation M1–M7 → failure counts in the
  kill matrix above; baseline unmutated run `46 passed, 1 xfailed`.
- `git diff --name-only a0fa900488db2f9270a2ce5cda6f7418a87eb86f HEAD` → the
  three owned paths only.
- `PY -m py_compile tests/verification/test_oracle_q01.py` → `compile-ok`.
- hermeticity grep (P6) → no hits.
- `PY scripts/check_contract_delta.py --base a0fa900488db2f9270a2ce5cda6f7418a87eb86f`
  → quoted in the return packet (P7).

## Seat ruling 2026-10-17 — FINDING F1 closed by D00.D3 clarification

D00.D3 is clarified (seat 972d2923, Fable Meta-CEO, 2026-10-17): the product `S(t; v)` runs over
QUALIFIED events, and an event whose qualification is `INFERRED` is **UNRESOLVED**, not absent.
A revision set with no observation at all is the ABSENT case and the factor is 1 (the oracle's
pre-registered reading). A revision set that CONTAINS an inferred event cannot assert its share
basis, so `split_factor`, `sadj_view` and `total_return_view` refuse with the typed
`NOT_CONFIRMED` (D00.D4: context may be shown, computation refuses); RAW is untouched. Silently
computing factor 1 would state "no split happened" without a qualified receipt — the false
consensus C03 exists to prevent. The SUT behaviour observed at first run is therefore the lawful
one. `test_Q01_06_not_confirmed_pre_registered_oracle_factor` (strict xfail) is replaced by
`test_Q01_06_not_confirmed_is_a_typed_refusal_by_ruling`, which pins the refusal; the
either-reading guard `test_Q01_06_not_confirmed_event_is_never_applied_as_confirmed` stays.
