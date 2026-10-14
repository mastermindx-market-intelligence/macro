# A01 — vertical acceptance journey (§14 end to end)

Programme DATA-OS-COMPLETION, lane A01-1 (`dataos-a01-1`). Evidence class:
synthetic exact-number corpus driven through the REAL entrypoints on main (C01
seam, read contract current/replay/reconstruct/account_coverage, Data Workspace
dispatch, identity tables, basket reader). This is the programme's **first
integrated milestone**, not the production completion claim.

## Scope

* Start commit `15bc4a7b392f152518c9fb8b822bd336ddc108b5`; lane branch
  `lane/dataos-a01-1`.
* Ten subject pins at the start commit (blob ids, `git rev-parse HEAD:<path>`):
  1. `engine/price_ladder.py` — `095fee9aafa128fae08bfaee07354bfee6c3f979`
  2. `tests/test_price_ladder.py` — `da1f0bc19fb1e6c9828c1c055c85ebbd5b804a3b`
  3. `lib/dataos/read_contract.py` — `460fc9403c28eefc771710cbd5b2ecd43bedfdd5`
  4. `lib/dataos/web_api.py` — `fc35cdec14c1a83752c6c8f095ed0305218ebafc`
  5. `lib/dataos/web_workspace.py` — `450c25fc363272cdff1a58889edbd14c29bffb18`
  6. `scripts/data_workspace.py` — `f3763471beb4db2174215bdfc57d17c3692d6568`
  7. `engine/basket_membership_pit.py` — `5c7ba201d505648365ba40ff88c6901b47aef713`
  8. `tests/test_basket_membership_pit.py` — `6da5b38759ad945c5781fff213b9f8a6bcfc8d55`
  9. `lib/dataos/identity.py` — `a288b38a707548f19f5701d2c35db2e1e48e5d04`
  10. `research/data_os_completion/2026-10-13/I03_CONTINUITY_REFUSAL_MATRIX.md` —
      `48b1fd6c40b8fd6c35d8f5c749dedd112bbe2b82`
* Corpus (60 business days from 2026-01-02, every price a dyadic decimal string
  exactly representable as `Fraction(str(x))`): `PLAINCO` no action;
  `SPLITCO` 2-for-1 split effective day 30 (stored tradj: pre-split tail × 1/2 →
  50.00, post 100.00, so post/pre = 2/1 exactly); `DIVCO` ONE cash distribution
  25.00 on day 20 (stored tradj: pre-ex tail × 4/5 → 80.00, post 100.00, so
  pre × 5/4 = post exactly — the store's series is the total-return adjusted
  close, `schema.close.basis: tradj` on `equity.bars.daily.stocks`, a
  multiplicative rebase of the pre-ex tail only); `GONECO` basket member with no
  stored file; basket `a01-basket` in suite `baskets_a01`.
* Generation-id mapping: `GenerationRef.generation_id` is a free-form string (no
  format imposed by the read contract), so the lane ids `a01-gen-A` /
  `a01-gen-B` are used verbatim.

## Acceptance map

| id | named assertion(s) | test node ids | verdict |
|---|---|---|---|
| A01.01 known answer, three consumers | `assert_a01_01_known_answer_three_consumers` | `test_s1_view_a_served_for_three_tickers`, `test_known_answer_three_consumers`, `test_known_answer_splitco_exact_two_for_one`, `test_known_answer_divco_exact_distribution`, `test_known_answer_plainco_control_identical` | PASS |
| A01.01 CURRENT returns B | `assert_a01_01_current_returns_b` | `test_current_returns_b`, `test_stale_generation_proof` | PASS |
| A01.01 REPLAY returns exactly A | `assert_a01_01_replay_returns_exact_a` | `test_replay_returns_exact_a` | PASS |
| A01.01 real retained corpus | — (rights pin) | `test_registry_rights_row_real_corpus_unfinished` | UNFINISHED (rights not granted; leg cannot silently flip) |
| A01.02 inspectable explanation | `assert_a01_02_inspectable_explanation` | `test_inspectable_explanation`, `test_a_passing_call_is_not_workflow_acceptance` | PASS |
| A01.03 rename owner-evidenced only | `assert_a01_03_rename_owner_evidenced_only` | `test_rename_boundary_exact`, `test_rename_row_omitted_no_continuity` | PASS |
| A01.03 rename without evidence | — (control) | `test_rename_without_evidence_is_a_finding` (strict xfail) | **FINDING A01-F1** |
| A01.03 reused ticker never joins | `assert_a01_03_reused_ticker_does_not_join` | `test_reused_ticker_two_securities`, `test_reused_ticker_boundary_ids`, `test_reused_ticker_overlap_refused` | PASS (identity split); ticker-key join UNFINISHED: `test_reused_ticker_join_unfinished_not_passed` |
| A01.03 incompatible refuses / compatible serves | `assert_a01_03_incompatible_refuses_compatible_succeeds` | `test_incompatible_refuses_compatible_serves` | PASS |
| A01.04 missing member stays in account | `assert_a01_04_missing_member_stays_in_account` | `test_missing_member_stays_in_account`, `test_coverage_denominator_before_and_after_b` | PASS |
| A01.04 revocation typed, never B under A | `assert_a01_04_revocation_typed_never_b_under_a` | `test_revocation_typed_never_b_under_a`, `test_revocation_root_binding_removed`, `test_revocation_source_file_deleted`, `test_revocation_source_unreadable`, `test_revocation_version_pin`, `test_revocation_reconstruct_required_missing`, `test_revocation_replay_payload_removed` | PASS |
| receipt pending legs | `assert_receipt_lists_pending_legs` | `test_pending_legs_receipt`, `test_receipt_json_serialisable` | PASS |

## Journey

| step | exact call | generation | label seen | value relation / code |
|---|---|---|---|---|
| S1 | `resolve_close_canonical(<t>, view=ReadRequest(CURRENT, basis='tradj'), data_dir=store)` × PLAINCO/SPLITCO/DIVCO | GEN_A | served (`CanonicalClose.ok`) | SPLITCO post/pre = 2/1; DIVCO pre × 5/4 = post; registry row `equity.bars.daily.stocks`, clock `ingested_at`, `dependency_generation_ids = ("sha256:"+content_sha,)` |
| S1 | `dispatch(ws, {'action':'read','ref':'store:stocks/<t>.parquet','columns':[__index_level_0__, close],'limit':200})` | GEN_A | `action=read` | rows identical to seam values; `production_qualification=NOT_ESTABLISHED_BY_THIS_ADAPTER`; A's `file_version` captured |
| S1 | `members_asof('a01-basket','2026-03-27',suite='baskets_a01')`, `coverage(suite)`, `account_coverage(...)` | GEN_A | `current` (retained A) | members = all four incl. GONECO, `pit=True`, basis `pit_snapshot`; account requested 4, GONECO `MISSING/NO_COVERAGE` |
| S1 | `current(ReadRequest(CURRENT), {'prices': dep@GEN_A}, evidence=…GEN_A)` | GEN_A | `current` | 60 rows; day-10 = 109 (A) |
| S2 | rewrite `stocks/PLAINCO.parquet` day-10 close 109 → 999; declare GEN_B `supersedes=GEN_A` | **GEN_B** | SYNTHETIC correction | labelled `SYNTHETIC` in the receipt; no natural production event claimed |
| S3 | seam re-read + `current(..., evidence=…GEN_B)` | GEN_B | `current` | day-10 = 999; all other days equal A; `current(..., evidence=…GEN_A)` raises `STALE_GENERATION` |
| S4 | `replay(ReadRequest(REPLAY, output_id='a01-view-A'), RetainedOutput(...))` | GEN_A (inside payload) | `replay` | payload byte-identical to retained A (sha equal); decoded label `current`, GEN_A, day-10 = 109 |
| S5 | six revocation cases (table below) | — | refused | typed codes, `values_present=False` |
| S6 | `VendorAliasTable` I03 rows 1 & 4 + join probe | — | — | rename boundary exact; reuse splits ids; ticker-key join recorded UNFINISHED |
| S7 | seam with basis `sadj` / currency `EUR` / compatible | GEN_B | refused / served | `price_views.AMBIGUOUS_BASIS` + `values is None`; `price_views.CURRENCY_MISMATCH` + `values is None`; compatible serves |
| S8 | `account_coverage(...)` again after B | GEN_B | — | requested still 4; GONECO still MISSING/NO_COVERAGE |

## CURRENT vs REPLAY

* Day-10 close of PLAINCO: A = `109`, B = `999` (SYNTHETIC correction).
* Retained A: `sha256` of the canonical bytes
  `json.dumps(<served A>, sort_keys=True, separators=(",", ":")).encode()`
  recorded in the receipt (`s1_view_a.retained_a.sha256`), with a publishing
  receipt JSON naming GEN_A whose own sha256 is the
  `publishing_receipt_sha256`.
* CURRENT after B: seam returns 999 on day 10 and A on every other day;
  read-contract `current` binds GEN_B and returns 999.
* REPLAY: label `replay`; payload bytes == retained bytes; decoded payload
  carries A's original label `current` and GEN_A and day-10 = 109 — never B's.
* STALE_GENERATION proof: `current` with evidence
  `identity_generation_id=GEN_A` against the GEN_B ledger raises
  `ReadRefusal STALE_GENERATION` ("a superseded generation is readable by id
  only for RECONSTRUCT/REPLAY").

## Revocation mapping

| S5 case | typed code | values_present |
|---|---|---|
| root binding removed from the host config | `ROOT_NOT_BOUND` | False |
| source file deleted | `SOURCE_NOT_FOUND` | False |
| source unreadable (chmod 000, restored) | `SOURCE_INACCESSIBLE` (would record `SKIPPED_ROOT_HOST` on a root host; this host is not root) | False |
| inspector `read` with `expected_version` pinned to A's version after B | `SOURCE_VERSION_MISMATCH` | False |
| `reconstruct` with a required dependency missing | `UNBOUND_DEPENDENCY` | False |
| `replay` with the retained payload removed | `NO_RETAINED_OUTPUT` | False |

There is no literal UNAVAILABLE/DENIED code; the closed typed sets above are the
explicit refusal. Principal revocation: K01 GAP 1 (owner transport).

## Identity controls

* Rename (I03 row 1, vendor `yahoo`, half-open `[valid_from, valid_to)`,
  evidence digests on both rows): `resolve('yahoo','MRSH', 2026-01-13)` →
  `None`; `resolve('yahoo','MRSH', 2026-01-14)` → `SEC:US-XNYS-MMC`;
  `resolve('yahoo','MMC', 2026-01-13)` → the same id — continuity WITH owner
  evidence. With the MRSH row omitted: `None` — no invented continuity.
  Without any `evidence_sha256` (the type allows it for non-polygon vendors):
  the table STILL binds continuity → **FINDING A01-F1**.
* Reused ticker (I03 row 4): `resolve('yahoo','ABC', 2026-03-01)` →
  `SEC:US-XNYS-ABC`; on/after 2026-03-02 → `SEC:US-XNYS-ABC.2`; the two ids
  never compare equal; an overlapping-interval table refuses at construction
  (`IdentityError "ambiguous alias table"`).
* Ticker-key join: the C01 seam and the basket store are ticker-keyed — recorded
  `UNFINISHED: awaiting U03/U04 LANDED` with the exact call
  `resolve_close_canonical('ABC', view=_view_request(), data_dir=store_join)`
  which served n=60 rows spanning the 2026-03-02 reuse boundary under the single
  key 'ABC'; basket membership rows key on `(snapshot_date, basket_id, ticker)`
  with no security column. NOT marked passed.

## Coverage account

`GONECO` disposition before B and after B: `MISSING` with
`missing_reason=NO_COVERAGE`, no segments, never in `qualified`;
`requested = 4` (the basket size) both times; `qualified_fraction = 3/4`
exactly; the eight-way disposition summary is identical before and after B.
GONECO is never filled from another member or from current data (the C01 seam
refuses it `read_contract.UNBOUND_DEPENDENCY`, `values is None`).

## Rights

Registry row `equity.bars.daily.stocks` (`config/dataset_registry.yml`, read
only, quoted verbatim):

```yaml
rights:
  purchase_access: unverified
  internal_computation: unverified
  redistribution: not_granted
```

Because `internal_computation: unverified` and `redistribution: not_granted`, a
rights-allowed retained corpus cannot be established on this repo's evidence, so
the real-corpus leg of A01.01 is UNFINISHED; the test pins the three values
exactly (via both the `Registry` object and the raw YAML) so the leg cannot
silently flip to "passed" when rights change.

## Pending legs

Verbatim `PENDING_LEGS`:

* `terminal_json_evidence`: `UNFINISHED: awaiting C04 LANDED` — closed by the
  C04 sidecar emitter carrying evidence into the Terminal JSON (browser/production
  workflow acceptance is owned by R02/R03; Terminal PR #996 deploy `fdc7c7f9` is
  the accepted production proof, cited, not re-run).
* `canonical_reads_in_workspace`: `UNFINISHED: awaiting U03 LANDED` — closed by
  canonical reads exposed through the DataWorkspace.
* `basket_prices_one_basis`: `UNFINISHED: awaiting U04 LANDED` — closed by basket
  membership + prices composed on one evidence basis.
* `real_retained_corpus`: `UNFINISHED: rights-allowed retained corpus not
  established (registry rights quoted)` — closed by a rights grant recorded in
  the registry row.
* `principal_revocation`: `GAP: K01 GAP 1, owner transport` — closed by the
  transport owner (see `K01_RIGHTS_LEAKAGE_MATRIX.md` §GAPS, GAP 1).

## Mutation sensitivity

Procedure: `git worktree add --detach <mut> HEAD`, smallest edit (≤ 6 changed
lines) in that tree only, run the suite there, restore with
`git checkout -- lib/ engine/`, remove the worktree.

| mutation | edit | failing test(s) | killed |
|---|---|---|---|
| AM1 replay regenerates | `replay` returns freshly built bytes (`payload=json.dumps({"regenerated": True}).encode()`) | `test_replay_returns_exact_a` | yes |
| AM2 current serves superseded | `_current_generation` takes all ledger rows and `min` instead of live `max` | `test_current_returns_b`, `test_stale_generation_proof` | yes |
| AM3 coverage drop | `account_coverage` drops MISSING members and their population slots | `test_missing_member_stays_in_account`, `test_coverage_denominator_before_and_after_b` | yes |
| AM4 alias interval ignored | `AliasRow.covers` skips the `valid_from` check | `test_rename_boundary_exact` | yes |
| AM5 version pin ignored | `DataWorkspace._file` skips the `expected_version` comparison | `test_revocation_typed_never_b_under_a`, `test_revocation_version_pin` | yes |

**Killed 5/5. No survivor.**

## Findings

**FINDING A01-F1** — `VendorAliasTable` grants rename continuity from an alias
row that carries NO evidence digest: `evidence_sha256` is optional for
non-polygon vendors, so owner evidence is not enforced at bind time. Pinned by
`pytest.mark.xfail(strict=True)` asserting the correct behaviour (no continuity
without evidence). 5-line reproducer:

```python
from datetime import date
from lib.dataos.identity import AliasRow, VendorAliasTable
t = VendorAliasTable([
    AliasRow(vendor="yahoo", vendor_symbol="MMC", security_id="SEC:US-XNYS-MMC",
             valid_from=None, valid_to=date(2026, 1, 14)),          # no evidence
    AliasRow(vendor="yahoo", vendor_symbol="MRSH", security_id="SEC:US-XNYS-MMC",
             valid_from=date(2026, 1, 14), valid_to=None)])         # no evidence
assert t.resolve("yahoo", "MRSH", date(2026, 1, 14)) is None        # FAILS: returns the id
```

No other findings: every other leg passes or is recorded UNFINISHED/GAP above.

## Commands

Run from the lane worktree; `PY` = `~/lanes/venv/bin/python`.

* `PYTHONDONTWRITEBYTECODE=1 PY -m pytest tests/verification/test_journey_a01.py -q -p no:cacheprovider -rs`
  → last line (both runs identical): `29 passed, 1 xfailed in 1.4xs` (30 items,
  0 skipped; the xfail is the strict FINDING A01-F1).
* `git diff --name-only 15bc4a7b… HEAD` → exactly the four owned paths;
  `git diff --diff-filter=M --name-only 15bc4a7b… HEAD` → empty.
* `PY -m py_compile tests/verification/journey_a01.py tests/verification/test_journey_a01.py` → `compile-ok`.
* Hermeticity grep (see P4): one hit, the word "subprocess" inside the module
  docstring's promise "no subprocess"; all writes go to the tmp corpus only.
* `PY scripts/check_contract_delta.py --base 15bc4a7b… 2>&1 | tail -8` →
  `::error title=contract-delta::tests/verification/test_journey_a01.py is a new
  pytest suite named by no run: step in any workflow — wire it into the job that
  owns its subject in .github/ci/legacy-jobs.yml, or add a reasoned row to
  config/unrun_test_waivers.yml` / `contract-delta: 1 introduced, 0 inherited
  (base 15bc4a7b)`. This "introduced" finding naming the unwired test file is
  EXPECTED: the suite is not yet wired into CI (the orchestrator applies the
  `.github/ci/legacy-jobs.yml` patch).
