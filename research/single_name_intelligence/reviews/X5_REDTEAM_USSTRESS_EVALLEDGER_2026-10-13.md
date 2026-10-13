# X5 red-team: US/Mag-7 stress set (A4R1) and SNI evaluation ledger (B4)

Heads under review (read-only via `git show` / path-limited `git archive`):

- Stress set `45fdf1760144e01d3dcba9ae4129c693ee646ddb`
- Ledger `646c51fee915dd084b496f8fc25292dd1667ec77`
- Owner signatures and S0 protocol text from `origin/main`

This file is the X5 review artifact. It does not edit either draft.

## Summary

**Finding counts:** BLOCKER 2, MAJOR 10, MINOR 3, NIT 1.

**(a)** No. Committed Mag-7 profiles leave `canonical_issuer_id` and `security_id` null; `stress_set.py` does not mint an issuer or security id from a ticker. `check_profile` refuses the six identity-id keys when non-null. Import of `stress_set.py` and the synthetic tests do not read `data/` or parquet. The hole is that `check_profile` still accepts CIK/FIGI/ISIN/CUSIP/PermID keys (X5-05).

**(b)** Yes, two sequences. (1) `EvalLedger.append` refuses SCORE/RESOLVE without REGISTER/BUDGET/PUBLISH, but a one-line SCORE or RESOLVE JSONL with a self-consistent `row_hash` loads with `verify_chain() == []` and `_fold` records the outcome (`registered == {}`). (2) `append` accepts REGISTER (written 2026-10-13) then PUBLISH/RESOLVE/SCORE whose payload `published_at_utc` / `observed_at_utc` sit in 2019–2020, including `horizon_end_utc` before `published_at_utc`. Payload rewrite without rehash is detected; dropping `written_at_utc` from `_row_hash` is not.

**(c)** No. README and the seven profiles never say the Mag-7 set is a hindsight/survivorship selection (today's seven largest). Nothing describes a residual as transferable evidence. A36/A37 are stated as no-ticker-branch and config onboarding only.

Residuals and Brier means in these drafts are descriptive statistics. This review does not treat them as causal effects, forecasts, news impact, or signals.

## Findings

### X5-01 — BLOCKER — Attack 10 / 8

- **CLAIM:** `verify_chain` plus `state()` accept a SCORE or RESOLVE row for a family that was never REGISTERED or BUDGETED, because `_rebuild` folds JSONL without re-running validators.
- **EVIDENCE:** `sni_eval_ledger.py:288-317` (`_fold` applies SCORE/RESOLVE with no registration check); `:596-602` (`_rebuild` only folds); `:611-636` (`verify_chain` checks seq/prev/row_hash only). Probe `/tmp/x5probe/run_attacks.py` wrote a one-line SCORE file and a one-line RESOLVE file:

```
SCORE-only file verify_chain []
SCORE-only file state scores 1 registered {} counts {..., 'registered': 0, 'scores': 1}
RESOLVE-only file verify_chain [] resolved {'f1': 'MATURED'}
```

- **FALSIFIER:** Opening that SCORE-only file raises `FAMILY_NOT_REGISTERED` (or `verify_chain` returns a semantic violation).
- **REPAIR:** Re-run the same `_validate_*` gates inside `_rebuild`/`verify_chain` so a hash-valid file that skips REGISTER/BUDGET is refused, and treat semantic order as part of the chain.

### X5-02 — BLOCKER — Attack 9

- **CLAIM:** `append` accepts a MATURED outcome (and a SCORE over it) whose `observed_at_utc` is years earlier than the family's REGISTER `written_at_utc`, and accepts `horizon_end_utc` before the published decision time.
- **EVIDENCE:** `_validate_resolve` (`sni_eval_ledger.py:494-501`) compares `observed_at_utc` to `horizon_end_utc` only. `_validate_publish` (`:440-441`) parses the two timestamps and never requires `published_at_utc >= REGISTER.written_at_utc` or `horizon_end_utc >= published_at_utc`. Probe:

```
REGISTER written_at 2026-10-13T03:01:52Z
PUBLISH accepted with payload published_at 2020-01-01T00:00:00Z
MATURED observed_at 2020 vs REGISTER 2026-10-13T03:01:52Z -> ACCEPTED
horizon_end BEFORE published_at accepted; observed after horizon before published: ACCEPTED
SCORE of pre-registration 2019 outcome: ACCEPTED
```

- **FALSIFIER:** The 2019-observed SCORE sequence raises a named `REFUSAL_CODES` member (`OUTCOME_BEFORE_REGISTER` or `HORIZON_BEFORE_PUBLISH`).
- **REPAIR:** Refuse PUBLISH when `published_at_utc` is before that family's REGISTER time; refuse MATURED when `observed_at_utc < published_at_utc` or `horizon_end_utc < published_at_utc`.

### X5-03 — MAJOR — Attack 2

- **CLAIM:** The Mag-7 cohort is today's seven largest names chosen with hindsight, and neither the README nor any profile discloses that as a survivorship/hindsight selection.
- **EVIDENCE:** README title and A36 line (`README.md:1-4`) call it a "US/Mag-7 science stress set" for acceptance A36/A37. Grep of README + seven YAML + `stress_set.py` for `hindsight`, `survivorship`, `survivor`, `largest`, `market cap`, `representative`, `US large cap`, `transfer`, `generaliz` returned 0 hits. Profiles have no episode-selection rule and no stress windows. S0 protocol register on `origin/main` has 0 Mag-7 hits; contamination law §2–§3 (time axis / name axis) never names this cohort.
- **FALSIFIER:** A reader-facing sentence in README and each profile stating that membership is the 2026-10-12 largest-seven list, is hindsight/survivorship-selected, and is not a US-large-cap sample.
- **REPAIR:** Disclose the as-of market-cap rule and survivorship in README plus a `cohort_selection` block on every profile; keep A36/A37 as no-ticker-branch claims only.

### X5-04 — MAJOR — Attack 3

- **CLAIM:** Profile labels and sector ETFs are 2026-10-12 facts applied as if they held over any historical window the stress table would cover, with no then-known flag.
- **EVIDENCE:** Every profile has `as_of: "2026-10-12"` (e.g. `META.yml:11`, `GOOGL.yml:11`). `META.yml:14,34-36` writes `display_name: Meta Platforms, Inc.` and `label: NASDAQ META` with no FB→META (2021-10-28) history. `GOOGL.yml:13-14,34-36` writes `issuer_key: alphabet` / `NASDAQ GOOGL` with no Class-A/GOOG 2014 share-class split. `GOOGL.yml` and `META.yml` set `sector_etf: XLC` (XLC launched 2018-06-18; Communication Services GICS cut is 2018). Tests synthesize closes from `2015-01-02` (`test_sni_us_stress.py:64`). No profile contains `ticker_history`, `then-known`, `then_known`, or an inception bound.
- **FALSIFIER:** Each profile carries a dated ticker/name/share-class/ETF validity interval, and `stress_table` abstains outside it.
- **REPAIR:** Add then-known validity ranges (META ticker, GOOGL class, XLC/XLY/XLK inception) and refuse or abstain when caller closes fall outside.

### X5-05 — MAJOR — Attack 1

- **CLAIM:** `check_profile` refuses the six listed identity-id keys but accepts CIK, FIGI, ISIN, CUSIP, and PermID, so a profile can carry a real issuer identifier under another name.
- **EVIDENCE:** `_IDENTITY_ID_KEYS` is `canonical_issuer_id`, `issuer_id`, `security_id`, `canonical_security_id`, `instrument_id`, `listing_id` (`stress_set.py:45-52`). `_walk_refuse` (`:125-128`) only those keys plus `issuer_link`. Probe `check_profile({"authority": {}, "cik": "0000320193"})` (and figi/isin/cusip/permid, nested cik) all returned without raising; the six listed keys did raise `stress profiles never carry identity ids`. Committed profiles have those six as null and do not contain CIK/FIGI/CUSIP/PermID tokens.
- **FALSIFIER:** `check_profile` raises on `cik`/`figi`/`isin`/`cusip`/`permid` at any depth.
- **REPAIR:** Extend the identity refuse-set to those aliases (and any `*_id` that is not a ticker display field) and add a test profile that carries a CIK.

### X5-06 — MAJOR — Attack 5

- **CLAIM:** `_inner_join_returns` drops mismatched calendar days without a named abstention and `stress_table` still emits a numeric summary on the intersection.
- **EVIDENCE:** `stress_set.py:529-538` builds `shared = sorted(set(stock_map) & set(bench_map))` with no dropped-date field. Probe with 26 stock closes vs 18 bench closes:

```
inner join dates ['2020-01-03', '2020-01-06'] dropped stock ['2020-01-02', '2020-01-07'] dropped bench ['2020-01-08']
mismatched calendars summary {n: 6, mean: 5.629..., stdev: 1.285..., n_shared_dates: 17}
stock n closes 26 bench n 18 n_shared 17 emitted mean 5.629...
```

README (`:39-42`) documents the inner join; the summary still emits `mean`/`stdev` with no named reason for the dropped days.

- **FALSIFIER:** Mismatched calendars raise, or the per-benchmark dict sets `mean` to None with `reason: DATE_JOIN_MISMATCH` (and lists dropped dates).
- **REPAIR:** Record dropped dates; abstain the numeric summary unless the caller passed a pre-declared join policy.

### X5-07 — MAJOR — Attack 11

- **CLAIM:** `SCORE` accepts a non-finite `brier` and a non-finite `baseline_brier` (`NaN`), so a SCORE row can store a non-number without `BRIER_MISMATCH`.
- **EVIDENCE:** `_validate_score` (`sni_eval_ledger.py:553-561`) type-checks `int`/`float` and compares `abs(float(reported) - recomputed) > 1e-12`. `NaN > 1e-12` is False. Probe:

```
SCORE with NaN brier: ACCEPTED
SCORE with inf brier: BRIER_MISMATCH
SCORE with NaN baseline_brier: ACCEPTED
```

- **FALSIFIER:** `brier=float("nan")` raises `INVALID_PAYLOAD` (or `BRIER_MISMATCH`).
- **REPAIR:** Refuse unless `math.isfinite(brier)` and `math.isfinite(baseline_brier)`.

### X5-08 — MAJOR — Attack 11

- **CLAIM:** UNPRICEABLE and CENSORED forecasts are excluded from Brier (correct) but the SCORE row never counts them, so they are silently omitted from `n`.
- **EVIDENCE:** `_brier_pairs` (`sni_eval_ledger.py:338-360`) keeps `state == MATURED` only. `_validate_score` (`:542-552`) requires `scored_forecast_ids == _matured_ids`. Probe with one MATURED, one CENSORED, one UNPRICEABLE, one PENDING: `brier(...) == 0.0625` and `SCORE` with `n=1` / `["f1"]` was `ACCEPTED`; including the censored id raised `NOT_MATURED`. SCORE payload keys (`:508-519`) have no `n_censored` / `n_unpriceable` / `n_pending`. Draft (`REGISTRATION_LEDGER_DRAFT.md:125-136`) says matured-only.
- **FALSIFIER:** A SCORE payload is refused unless it reports the censored, unpriceable, and pending counts alongside `n`.
- **REPAIR:** Require those counts on SCORE (and check them against `state()`), still excluding those ids from the Brier mean.

### X5-09 — MAJOR — Attack 13

- **CLAIM:** `_check_authority` refuses a top-level authority key and ignores the same flag when nested or case-varied, so a PUBLISH can carry `rank_authority: true` under another key.
- **EVIDENCE:** `sni_eval_ledger.py:197-204` loops `AUTHORITY_KEYS` on the payload dict only. Probe on a registered+budgeted ledger:

```
nested authority.rank_authority True -> ACCEPTED
nested trade_authority True -> ACCEPTED
case-variant Rank_Authority True -> ACCEPTED
SIGNAL_AUTHORITY=1 -> ACCEPTED
_check_authority {'nested': {'rank_authority': True}} -> ACCEPTED
_check_authority {'Rank_Authority': True} -> ACCEPTED
```

Top-level `rank_authority=True/"true"/1/False` all returned `AUTHORITY_FLAG_REFUSED`.

- **FALSIFIER:** The nested and `Rank_Authority` payloads raise `AUTHORITY_FLAG_REFUSED`.
- **REPAIR:** Walk payloads the way `stress_set._walk_refuse` does, matching keys case-insensitively.

### X5-10 — MAJOR — Attack 14

- **CLAIM:** `sni_eval_ledger.py` re-implements append-only JSONL, trial budget, hash digest, and Brier scoring that `engine/trial_ledger.py`, `engine/qledger.py`, and `engine/grading_stats.py` already own, and the docstring does not say why a separate ledger is unavoidable.
- **EVIDENCE:** Module docstring (`sni_eval_ledger.py:1-28`) calls itself an SNI-local DRAFT that CONSUMES qledger vocabulary and "does not replace qledger". It never states why a second ledger is required. Duplicates vs `origin/main` owner surface (grep `^def |^class ` plus first 40 lines): `EvalLedger._write_line` (`:684-690`, JSONL + fsync) vs `TrialLedger._append_rows` (`engine/trial_ledger.py:134-144`); `BUDGET`/`declared_trials` vs `TrialLedger.log_declared_budget` (`:204`); `REGISTER`/`SCORE` vs `qledger.register` (`engine/qledger.py:2026`) and `qledger.grade_claim` (`:2698`); `brier()` (`sni_eval_ledger.py:363-372`) vs `grading_stats.brier_decomposition` (`engine/grading_stats.py:914`). Protocol register §4 (L140) already says return/hit grading is never probabilistic; this draft still mints its own Brier path.
- **FALSIFIER:** The module docstring names the owner functions it will adapter onto and the single invariant qledger/TrialLedger cannot hold.
- **REPAIR:** Keep this file as a facade: persist via `TrialLedger` + `qledger.register`, compute Brier via `grading_stats`, and drop the parallel hash chain once the adapter exists.

### X5-11 — MAJOR — Attack 15(a)

- **CLAIM:** Removing the REGISTER-before-BUDGET check leaves the module's own tests green.
- **EVIDENCE:** Mutation copy `/tmp/x5mut/a` deleted the `_family_registered` refuse inside `_validate_budget` (`sni_eval_ledger.py:398-399`). `python3 -m pytest tests/test_sni_eval_ledger.py -q -p no:cacheprovider` → `25 passed in 1.63s`. Existing `test_budget_required` covers PUBLISH-before-BUDGET, not BUDGET-before-REGISTER.
- **FALSIFIER:** After that deletion, a test fails with `FAMILY_NOT_REGISTERED`.
- **REPAIR:** Add `test_budget_before_register_refused` that `append(BUDGET)` on a fresh ledger raises `FAMILY_NOT_REGISTERED` and writes zero rows.

### X5-12 — MAJOR — Attack 15(b)

- **CLAIM:** Dropping `written_at_utc` from `_row_hash` leaves the module's own tests green, so a timestamp rewrite would not break the chain.
- **EVIDENCE:** Mutation copy `/tmp/x5mut/b` changed `_row_hash` (`sni_eval_ledger.py:150-152`) to exclude `written_at_utc`. Same pytest command → `25 passed in 1.56s`. `test_a27_tamper_middle_line_violation` rewrites `payload.family_id`, not `written_at_utc`.
- **FALSIFIER:** After that deletion, a test that rewrites `written_at_utc` on an earlier line sees a `ROW_HASH_MISMATCH`.
- **REPAIR:** Hash every field except `row_hash`, and add a tamper test that changes only `written_at_utc`.

### X5-13 — MINOR — Attack 5

- **CLAIM:** When the window is longer than the series, or benchmark variance is zero, the module abstains with `None` / `n=0` and never names a reason.
- **EVIDENCE:** `rolling_beta_residual` (`stress_set.py:406-437`) writes `None`; `_beta` (`:396-397`) returns `None` on `var_b == 0.0`; `_summary` (`:465-511`) has no `reason` key. Probe: length-10 series with `window=63` → all `None`, summary `{n: 0, mean: None, ...}` and `"named_reason" in stats` is False. Constant benchmark returns → defined count 0.
- **FALSIFIER:** The empty summary includes `reason: WINDOW_TOO_SHORT` or `ZERO_BENCHMARK_VARIANCE`.
- **REPAIR:** Put a named abstention reason on the per-benchmark dict whenever `n == 0` or any residual was skipped for zero variance.

### X5-14 — MINOR — Attack 6

- **CLAIM:** `check_profile` accepts a case-variant authority key (`Rank_Authority: True`) while refusing the canonical names.
- **EVIDENCE:** Probe: `check_profile({"authority": {"Rank_Authority": True, "rank_authority": False}})` printed `[HIT] case-variant Rank_Authority True accepted`. Canonical `rank_authority=True/"true"/1/0/None` all raised. Nested `extra.rank_authority=True` did raise via `_walk_refuse` (`stress_set.py:119-128`).
- **FALSIFIER:** The case-variant profile raises `ValueError`.
- **REPAIR:** Compare authority keys case-insensitively in `_walk_refuse`.

### X5-15 — MINOR — Attack 12

- **CLAIM:** Draft status is explicit in prose, but there is no `registered=false` flag, and `_parse_utc` accepts timestamps without a `Z`/offset by assuming UTC.
- **EVIDENCE:** `REGISTRATION_LEDGER_DRAFT.md:1-6,195-203` and module docstring (`sni_eval_ledger.py:1-8`) say R1-gated DRAFT / not Evaluation OS. Grep for `registered=false` in that doc is False. `_parse_utc` (`:186-188`): naive datetime gets `tzinfo=UTC`. Probe: PUBLISH with `published_at_utc="2020-01-01T00:00:00"` (no Z) → `ACCEPTED`. `_now_utc` (`:167-173`) does emit `Z` and is not an append argument, so it cannot backdate `written_at_utc`.
- **FALSIFIER:** The draft header contains `registered: false`, and a naive timestamp raises `INVALID_PAYLOAD`.
- **REPAIR:** Add `registered: false` to the draft header and require an explicit `Z` or numeric offset.

### X5-16 — NIT — Attack 6 / 13

- **CLAIM:** Stress-set authority refusals reuse the identity-id message `stress profiles never carry identity ids`, which hides the actual gate that fired.
- **EVIDENCE:** `_REFUSE_MSG` (`stress_set.py:54`) is used for both identity and authority (`:65-66`, `:123-124`, `:143`). Probe of `authority_flags(rank_authority=True)` printed `authority_flags True refused stress profiles never carry identity ids`.
- **FALSIFIER:** Authority refusal text names the flag.
- **REPAIR:** Split the message (or raise a dedicated exception) so the failing gate is in the string.

## Checked-clean

Each entry is an attack that did not produce a finding, with search/run bounds.

### Attack 1 remainder — identity minting and committed profiles

- **Bounds:** Seven YAML stems AAPL/AMZN/GOOGL/META/MSFT/NVDA/TSLA; `stress_set.py` `_IDENTITY_ID_KEYS` and `_walk_refuse`; probe `check_profile` for the six keys plus `issuer_link`.
- **Evidence:** `load_profiles` returned all seven with `canonical_issuer_id is None`, `security_id is None`, `issuer_link == "UNRESOLVED"`. Non-null values of those six keys raised. No CIK/FIGI/CUSIP/PermID tokens in committed profiles (`isin` hits were the substring inside `isinstance`). Module does not construct an id from a ticker string.

### Attack 2 remainder — transfer / representativeness claims; episode picking

- **Bounds:** README (96 lines), seven profiles, `stress_set.py`; tokens `transfer`, `representative`, `US large cap`, `generaliz`, `outperform`.
- **Evidence:** 0 hits. A36/A37 text is no-ticker-branch and "held-out company onboards via config". Profiles contain no stress-episode dates. The hindsight *disclosure* gap is X5-03; this item is the absence of a transfer claim.

### Attack 4 — data reads at import / test time

- **Bounds:** `/tmp/x5us` path-limited archive (no `data/`); fresh interpreter import of `stress_set`; CLI `--data-dir /tmp/x5probe/no-such-data`; pytest `tests/test_sni_us_stress.py`.
- **Evidence:** `(US_ROOT / "data").exists() == False`. Import with `open` wrapped: `pandas in sys.modules` False, 0 opens, 0 parquet paths. `load_closes_from_parquet` missing file → `None`. CLI rc 0, report `data absent in this checkout; no statistics computed`. Tests 14 passed using `random.Random(7)` synthetic closes (`test_sni_us_stress.py:57-71,210-214`). Pandas is imported only inside `load_closes_from_parquet` (`stress_set.py:677-680`). Socket guard during `load_profiles`: no socket.

### Attack 5 remainder — NaN/inf, unsorted/duplicate, zero-variance abstain (value)

- **Bounds:** `simple_returns`, `rolling_beta_residual`, `_beta`, `hist_vol_normalize`, `_summary`.
- **Evidence:** Unsorted and duplicate dated closes raised `ValueError`. NaN/inf/<=0 closes became `None` in returns (no bridged gap). `_beta` on constant bench returned `None`; residuals were all `None` (no number). Named-reason gap is X5-13; inner-join numeric emit is X5-06.

### Attack 6 remainder — literal-false authority on canonical keys

- **Bounds:** All six `AUTHORITY_FLAG_NAMES`; values True, `"true"`, `"True"`, 1, `"1"`, 0, `"false"`, None, `{nested: True}`; `AuthorityMap.__setitem__` / `update` / `|=`; nested `extra.rank_authority`.
- **Evidence:** All canonical-key cases raised. `authority_flags(rank_authority=True)` raised. Nested canonical key raised. Case-variant hole is X5-14.

### Attack 7 — language

- **Bounds:** README, `stress_set.py`, seven YAML; tokens `validated`, `outperform`, `predict`, `alpha` (as claim), `edge` (as claim), `50/50`, `news impact`, `causal`, `forecast`, `signal`.
- **Evidence:** `validated` / `outperform` / `predict` absent. `alpha` hits are `Alphabet Inc.` / `issuer_key: alphabet`. `edge` hits are the substring in `qledger`. `50/50`, `news impact`, `causal`, `forecast`, `signal` appear only as required negations (`README.md:6-20`, `stress_set.py:12-15,813`). No residual is described as transferable evidence.

### Attack 8 remainder — append() kind order

- **Bounds:** Fresh `EvalLedger` in `/tmp`; sequences SCORE, RESOLVE, PUBLISH, BUDGET, second REGISTER, second BUDGET after PUBLISH, extra PUBLISH after cap, SCORE before RESOLVE.
- **Evidence:**

```
SCORE before anything: FAMILY_NOT_REGISTERED
RESOLVE before PUBLISH: UNKNOWN_FORECAST
BUDGET before REGISTER: FAMILY_NOT_REGISTERED
PUBLISH after REGISTER before BUDGET: BUDGET_REQUIRED
second REGISTER same key: ALREADY_REGISTERED
BUDGET increase after first PUBLISH: DUPLICATE_BUDGET
PUBLISH after budget exhausted: BUDGET_EXCEEDED
SCORE before any RESOLVE: NO_MATURED_FORECASTS
```

File-load bypass is X5-01, not this append path.

### Attack 10 remainder — naive tampers and canonical hashing

- **Bounds:** Four-row ledger; mutate payload; reorder two rows; delete middle; duplicate last; rehash only first; key-order swap; `0.1` vs `0.10`.
- **Evidence:**

```
tamper mutate_payload violations=['ROW_HASH_MISMATCH:2']
tamper reorder violations=['SEQ_MISMATCH:2', 'PREV_HASH_MISMATCH:2', ...]
tamper delete_middle violations=['SEQ_MISMATCH:2', 'PREV_HASH_MISMATCH:2', ...]
tamper duplicate violations=['SEQ_MISMATCH:5', 'PREV_HASH_MISMATCH:5']
hash key-order stable True
float 0.1 vs 0.10 0.1 0.1 True
```

`_canonical` uses `sort_keys=True`. SCORE-only semantic hole is X5-01. `written_at_utc` hash gap is X5-12.

### Attack 11 remainder — Brier not labeled as hit/return forecast support; exclusion of non-matured from the mean

- **Bounds:** `REGISTRATION_LEDGER_DRAFT.md` L141 and L204; `brier` docstring L363-364; `_brier_pairs` MATURED filter.
- **Evidence:** Exact sentence present: "Hit/return grading is not probabilistic forecast support until an accepted bridge exists." Brier is called a descriptive residual mean. CENSORED id in `scored_forecast_ids` raised `NOT_MATURED` (not scored as 0/1). Count omission is X5-08; NaN accept is X5-07.

### Attack 12 remainder — no real family; `_now_utc` not an append backdate knob

- **Bounds:** Ledger module + draft doc; tokens AAPL/BABA/NVDA/META/MSFT; `append` signature.
- **Evidence:** Those tickers absent from the ledger module. Tests use synthetic `fam-a` / `fam-b`. `written_at_utc` is assigned inside `append` from `_now_utc()` (`:671-674`); callers cannot pass it. `Z` suffix on `_now_utc` confirmed. `registered=false` / naive-timestamp issues are X5-15.

### Attack 13 remainder — top-level authority keys

- **Bounds:** All six `AUTHORITY_KEYS` at top level with True / `"true"` / 1 / False / `"TRUE"` on PUBLISH.
- **Evidence:** All six × those values → `AUTHORITY_FLAG_REFUSED`. Nested/case-variant hole is X5-09.

### Attack 15(c)(d) — mutations the tests caught

- **Bounds:** `/tmp/x5mut/c` identity refuse disabled; `/tmp/x5mut/d` `_beta` zero-variance guard removed; same pytest files as the drafts.
- **Evidence:** (c) `test_r1_05_identity_ids_at_any_depth` FAILED `DID NOT RAISE ValueError` (1 failed, 13 passed). (d) `test_r1_03_nonfinite_nonpositive_closes` FAILED `ZeroDivisionError: float division by zero` at `_beta` `cov / var_b` (1 failed, 13 passed).

## Test runs

Path-limited archives (full `git archive` of those commits filled `/tmp`; `data/` was omitted on purpose and is the sparse-checkout case the CLI already handles):

```
mkdir -p /tmp/x5us && git archive 45fdf1760144e01d3dcba9ae4129c693ee646ddb \
  research/single_name_intelligence/us_stress tests/test_sni_us_stress.py | tar -x -C /tmp/x5us
cd /tmp/x5us && PYTHONPATH=/tmp/x5us python3 -m pytest tests/test_sni_us_stress.py -q -p no:cacheprovider
```

Result: **14 passed, 0 skipped, 0 failed** in 0.80s.

```
mkdir -p /tmp/x5led && git archive 646c51fee915dd084b496f8fc25292dd1667ec77 \
  research/single_name_intelligence/evaluation tests/test_sni_eval_ledger.py | tar -x -C /tmp/x5led
cd /tmp/x5led && PYTHONPATH=/tmp/x5led python3 -m pytest tests/test_sni_eval_ledger.py -q -p no:cacheprovider
```

Result: **25 passed, 0 skipped, 0 failed** in 1.09s.

Probes: `/tmp/x5probe/run_attacks.py` (read-only against those copies). Mutations: `/tmp/x5mut/{a,b,c,d}` only.

## Mutation results

| mutation | tests caught | result |
|---|---|---|
| (a) remove REGISTER-before-BUDGET check in `_validate_budget` | no | 25 passed (`test_sni_eval_ledger.py`) |
| (b) drop `written_at_utc` from `_row_hash` | no | 25 passed (`test_sni_eval_ledger.py`) |
| (c) disable identity refusal in `_walk_refuse` | yes | 1 failed (`test_r1_05_identity_ids_at_any_depth`), 13 passed |
| (d) let `_beta` divide by zero variance | yes | 1 failed (`test_r1_03_nonfinite_nonpositive_closes`, `ZeroDivisionError`), 13 passed |

## Attack index

| Attack | Where |
|---|---|
| 1 Identity | X5-05; remainder in Checked-clean |
| 2 Hindsight cohort | X5-03; transfer-claim remainder in Checked-clean |
| 3 Then-known | X5-04 |
| 4 Data reads | Checked-clean |
| 5 Statistics | X5-06, X5-13; NaN/sort remainder in Checked-clean |
| 6 Authority (stress) | X5-14, X5-16; canonical keys in Checked-clean |
| 7 Language | Checked-clean |
| 8 Ordering | X5-01 (file load); append path in Checked-clean |
| 9 Registration-before-outcome | X5-02 |
| 10 Immutability / hash | X5-01, X5-12; naive tampers in Checked-clean |
| 11 Grading honesty | X5-07, X5-08; bridge sentence in Checked-clean |
| 12 Draft status | X5-15; remainder in Checked-clean |
| 13 Authority (ledger) | X5-09; top-level in Checked-clean |
| 14 Owner fork | X5-10 |
| 15 Mutations | X5-11, X5-12; (c)(d) in Checked-clean |
