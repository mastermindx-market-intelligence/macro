VERDICT: READY

# Lane 1 population route — third review (range `9c5db069856d..595fe6b75af2`)

Reviewer: independent read-only review subagent (Opus), ROUTE review. Self-check by the author is not counted. No repo writes, pushes, PR comments, labels, or production calls were made.

## Head and scope
- `git ls-remote origin refs/pull/10929/head` → `595fe6b75af2cd36ab447d4987e3c410abe4cca0`. The head has not moved.
- `git diff --name-status 9c5db069856d..595fe6b75af2` → M `app/sector_generation.py`, `config/dag.yml`, `lib/sector_central_carry.py`, `lib/sector_population.py`, `scripts/build_sector_central.py`, `tests/test_sector_central_carry.py`, `tests/test_sector_population.py`. The 7 files went into `/tmp/si_plan/reviews/tree` via `git show 595fe6b75af2:<path>`.
- Item 8: the range does **not** touch `.github/ci/legacy-jobs.yml` or `tests/test_ci_pack.py`. `_parse_population_query` / `_parse_audience` are unchanged in the range. The only new response field is `unserved_matching`, and it is not a parameter. No new parameter can name a generation, path or domain.

## Open findings (none BLOCKER)
| id | severity | one line |
|---|---|---|
| R3-S1 | SHOULD-FIX | The completeness denominator is only "live `baskets[]` + `observation_refusals`". A basket the producer drops by any other path disappears from the denominator, and the route answers `complete: true`. The producer has such a path (`engine/baskets.py:233` `if lvl.dropna().empty: continue`). This is the same class as R2-B2, through a second exit. |
| R3-N1 | NOTE | `owner_observation_refusal` string values are not length-bounded (`lib/sector_population.py:325-327`; live groups use `_text`). A 200,000-character `status` is carried verbatim. The 4 MiB encoder bound still refuses cleanly. |
| R3-N2 | NOTE | `etf_flows` `full_window` uses the **maximum** depth over funds (`collectors/sponsors.py:127`), not each fund's depth. The block `as_of` is the index max across funds, and `tail(n)` runs over a `dropna` series. So a single short or stale fund can be labelled "full" under a date it does not have. |
| R3-N3 | NOTE | `ETF_FLOW_WINDOWS` (`lib/sector_central_carry.py:113`) restates `FLOW_PERIODS` instead of importing it. A producer change of day count under the same labels would be mislabelled silently. |
| R3-N4 | NOTE | In `etf_flows`, `row.get("ticker")` runs before the Mapping check (`lib/sector_central_carry.py:137`). A non-Mapping row raises `AttributeError`, the builder's broad `except` catches it (`scripts/build_sector_central.py:670-673`), and **every** carried block is dropped, not only `etf_flows`. |
| R3-N5 | NOTE | R2-N4 is only partly closed. `member_industry` / `member_sub_industry` are single-source but are not in `_DATED_BLOCKS` (`lib/sector_central_carry.py:309`), so an undated source would still be carried with `as_of: null`. Both are dated on real bytes (2026-11-09 / 2026-11-06). For `confluence`, `as_of` is `generated_utc` for nasdaq and russell (a build timestamp, not a market session). `as_of_field` discloses this. |
| R3-N6 | NOTE | The author's claim that a refusal is "visible … in `group_index`" is overstated. `group_index` (`app/sector_generation.py:627-632`) has no `refused_by_owner`. A refused group shows there only as `name: null`, `n_members_listed: 0`, `n_unserved == n_configured_current`. |
| R3-N7 | NOTE | In two contradictory owner states the route answers `complete: true`. (a) A member is in both `missing_columns` and `observed_members`. (b) A refused basket's member is also served in a live group. Neither is producible by `lib/closes_panel.py:475-483` (disjoint by construction), so this is owner-trust, not a route defect. |
| R3-N8 | NOTE | Availability cliff. More than 500 unserved (for example, many baskets refused in a data outage; real total 1,020) makes every population read 503 `SECTOR_GENERATION_UNAVAILABLE`. This fails closed and is correct, but it is a total outage of the route, not a degraded page. |

---

## 1. R2-B1 — **FIXED**
Evidence: `lib/sector_population.py:267-279`. The `empty_price_tape` branch is gone. Any configured member that is not served, not in `missing_columns`, and not in `missing_at_asof` is `REASON_UNACCOUNTED` and increments `unaccounted`. `accounted_unserved` (`:104-107`) excludes it. `complete` (`:110-115`) requires `unaccounted == 0`.

Probes (`r3probes/test_zz_r3_probe.py`, output in `r3probes/probe_run.txt`), through the real publisher, reader, route and gates:
- **B1a** (real bytes; CARR dropped from housing's served members **and** from `observed_members`, still configured):
  `PROBE B1a 200 {'configured_current': 1020, 'served': 1014, 'accounted_unserved': 5, 'unaccounted': 1, 'complete': False} [{'group_id': 'housing', 'symbol': 'CARR', 'reason': 'unaccounted_by_owner'}]`
- **Synthetic edges** (`build_population`, the real function):
  - `dup_configured (None, 1, 0, 0, None)`: duplicate roster gives null, never true.
  - `member_in_two_groups_unserved_in_second (3, 2, 0, 1, False) [('g2','AAA','unaccounted_by_owner')]`: being served in g1 does not explain g2.
  - `case_mismatch_served_upper_configured_lower (1, 1, 0, 2, False)`: both the served "AAA" (unconfigured) and the configured "aaa" (unserved) count.
  - `served_unconfigured (1, 2, 0, 1, False)`
  - `empty_price_tape_label_gone (2, 1, 0, 1, False) [('g1','BBB','unaccounted_by_owner')]`
- **B1b** (whole basket removed from `baskets[]`, not added to refusals; this simulates `engine/baskets.py:233`):
  `PROBE B1b 200 {'configured_current': 1002, 'served': 997, 'accounted_unserved': 5, 'unaccounted': 0, 'complete': True} housing members anywhere: []`
  This is **R3-S1**. All 18 configured current housing members are neither served nor explained, and the route says `complete: true`.

  Reachability: `population_observation` admits a basket only with ≥3 observed closes at the as-of date and ≥60% coverage. `_ew_level` (`engine/baskets.py` `_ew_level`) then returns all-NaN only if no active member ever had a valid one-day return inside its `[added, removed)` window. For a basket with any history that cannot happen. It needs, for example, a basket whose members were all added at the as-of date with no prior-session close. On the real capture all 49 roster baskets are present (`r3probes/carry_real.txt`: `roster baskets 49 baskets.json live+refused 49 missing from capture []`). I therefore grade it SHOULD-FIX, not BLOCKER: it is not reachable on current data and needs a pathological upstream state. It is still the R2-B2 class, so the lead may raise it.

  Cheap fixes, either one:
  - The producer records that exit in `observation_refusals`.
  - The route cross-checks the capture's basket ids against the owner roster ids. The builder already reads `_membership()` for `removed_members`, so it can carry `roster_basket_ids`; any id missing from live + refused gives `configured_current: null`.

## 2. R2-B2 — **FIXED** (residual R3-S1 is a different exit)
Evidence: `lib/sector_population.py:296-331`. A non-list gives `roster_unknown`. Each entry is validated: `basket_id` must match the grammar, must not repeat a live or refused id, and `configured_members` must be a list of unique `_SYMBOL` strings. Anything else gives `roster_unknown`, so `configured_current` and `complete` are `None` (`:343-346`). Valid refusals add every member under `group_refused_by_owner_observation` and add to `configured_total`.

Synthetic probe (`PROBE B2syn`; tuple = configured, served, accounted, unaccounted, complete):
- Null in every malformed case: `absent_key`, `none`, `dict`, `string`, `int`, `entry_not_mapping`, `no_basket_id`, `basket_id_int`, `basket_id_bad_grammar`, `no_observation`, `no_configured`, `configured_not_list`, `configured_int_member`, `configured_dup`, `repeats_live_id` all give `(None, 1, 0, 0, None)`. `repeats_refused_id` gives `(None, 1, 2, 0, None)`.
- `empty_list (1, 1, 0, 0, True)`: an empty list is distinguished from an absent key.
- `valid (3, 1, 2, 0, True)`, `empty_configured (1, 1, 0, 0, True)`.
- `bool_and_huge_string_obs (2, 1, 1, 0, True) {'status': 200000}`: the bool `coverage` is dropped and the 200 k string is carried (R3-N1).

Real-route probe (`PROBE B2real`):
- `dict 200 {'configured_current': None, … 'complete': None} … private, no-store`
- `absent 200 {'configured_current': None, … 'complete': None}`
- `dup_live 200 {'configured_current': None, … 'complete': None}`
- `near495 200 {'configured_current': 1515, 'served': 1015, 'accounted_unserved': 500, 'unaccounted': 0, 'complete': True} page bytes 97907 q=Q bytes 112085 unserved_matching 495`
- `big496 503 {'schema': 'sector_generation.error/v1', 'code': 'SECTOR_GENERATION_UNAVAILABLE'} private, no-store`. That is 501 unserved, refused cleanly, with no truncation.
- A very large roster in `build_population` gives `PROBE B2big 501 PopulationError population_unserved_too_large` and `100000 PopulationError population_unserved_too_large`.

Refused basket with removed members: the producer's `configured_members` already excludes removed members (`lib/closes_panel.py:458-470`). If a removed pair were ever also listed, `:333-338` counts it as unaccounted (fixture test `test_removed_member_that_is_also_configured_is_a_contradiction`).

## 3. Preserved limits against the new surface — **HOLD**
- **Denied before read / no reader call**: `PROBE N8 read_population calls 0` across regwall-on bad uid, regwall-off bad token, and no token. `PROBE N8race2 … reads 0`.
- **`private, no-store`**: present on 401, 403, 503 (`SERVICE_UNAVAILABLE`, `SECTOR_GENERATION_UNAVAILABLE`) and 200 in every probe above.
- **One reader per request**: `_resolve_reader` once, then `read_population` once (`app/sector_generation.py:557-595`); unchanged by the range.
- **4 MiB bound / MAX_UNSERVED**: `unserved_matching` is drawn from `population.unserved`, which is already capped at 500 before any page exists (`lib/sector_population.py:339-340`). The worst real page measured is 112,352 B (`q=A`), and the synthetic 500-unserved page is 112,085 B. The final `encode_sector_population(max_encoded_bytes=MAX_ENCODED_BYTES)` still answers 503 TOO_LARGE (regression test `test_oversized_page_is_refused_not_truncated` passes). A large refused roster or a `q` match cannot pass the bound without a clean refusal.
- **Does `q` over unserved reveal anything new?** No. `PROBE q KVUE matching 2 subset_of_capture True`, `q A … True`, `q . … True`: `unserved_matching` is always a subset of `capture.population.unserved_members`, which every page already carries in full to the same entitled actor.

## 4. `etf_flows` carry — **ACCEPTABLE (NOTES R3-N2..N4)**
- **Tier**: `engine/sector_native_view.py:1890` `("etf_flows", "carried", "etf_flows", True)` is entitled-only and not in the range, so preview and anonymous users get `audience_not_entitled`. The same numbers are already server-rendered into `sector_central.html` by `_flows_section_html()` (`scripts/build_sector_central.py:398-410`). Static-estate exposure is unchanged in class (see R2-N6, which the author left as is).
- **Verbatim / no invented window**: labels must equal the producer's labels exactly, or the block is None. Values are copied, with `as_of=asof`, `depth`, and the producer's `rows[].vals` and `net`. Real values: as_of 2026-11-05, depth 79, 11 funds, all windows `full_window: True` (`r3probes/carry_real.txt`). Caveats are R3-N2 and R3-N3.
- **Build dependency**: `sector_flow_periods()` → `flows_table()` → `lib/store.read` → local `pd.read_parquet` of about 11 sector funds (`lib/store.py:476-482`). There is no network and no heavy compute. It is the second call per build (the first is in `_flows_section_html`), which is negligible.

## 5. Round-2 notes
- **R2-N1 — FIXED.** `accounted_unserved` counts only owner-explained entries (`lib/sector_population.py:104-107`). B1a shows `accounted_unserved 5, unaccounted 1`.
- **R2-N2 — FIXED.** `select_page` returns `unserved_matching` (`:396-403`). `q=KVUE` returns 2 entries, a subset of the capture.
- **R2-N4 — PARTIAL (NOTE R3-N5).** `_DATED_BLOCKS` drops undated blocks. Confluence is dated per universe: sp500 `as_of` 2026-11-06, nasdaq `generated_utc` "2026-11-09 09:38 UTC", russell `generated_utc`, china `as_of` 2026-11-09. The two industry blocks are not covered by the drop rule.
- **R2-N5 — FIXED.** `removed_members(membership, owner_effective_as_of(site))` (`lib/sector_central_carry.py:292-305, 323`). Real: effective 2026-11-06, 26 removed, all group ids are in the capture. The cut (`removed <= as_of`) matches the producer's `when >= removed` exclusion. A removed pair that is also configured, served or unserved adds to `unaccounted` (`lib/sector_population.py:333-338`). Small caveat: `owner_effective_as_of` returns None (so no `removed_members` is carried) when live baskets disagree on `effective_as_of`, and it ignores refusals' dates. That is fail-soft.
- **R2-N7 — FIXED.** `config/dag.yml` lists the 8 new reads. `tests/test_dag_conformance.py` is in the suite run below (passed).
- **R2-N8 — FIXED**, with no new oracle. `app/sector_generation.py:492-496, 560-567`:
  - regwall on, uid fails → **401** at the regwall gate (`PROBE N8 regwall-on bad uid 401 … AUTHENTICATION_REQUIRED`).
  - regwall off, token present but unverifiable → **503** `SERVICE_UNAVAILABLE`.
  - regwall off, no token → **403** `ENTITLEMENT_REQUIRED` (paywall).
  - gates verify and then the actor lookup fails → **503** (`PROBE N8race2 503 … verify callers ['regwall_check' ×6, '_actor_digest'] reads 0 private, no-store`).

  Token validity was already observable (200 vs 401/403). The 503 arises only after both gates admitted the token, so it gives an attacker nothing the gates did not. Semantic caveat: with regwall off, an expired token gets 503 rather than a login prompt. That is acceptable given the paywall's own verification.

## 6. Regressions — **NONE FOUND**
The full affected suites pass at head (below), including the S1 token answers, S2 durability, the S3 tests (forged `x`, `MAX_UNSERVED`, malformed taxonomy), the industry fields, the carried blocks and the size cap. My probes for 401/503/403 show `private, no-store` and zero reader calls.

## 7. Tests
- Author's affected suites. Command: `python3 -m pytest -q tests/test_sector_population.py tests/test_sector_central_carry.py tests/test_sector_native_view_typed_blocks.py tests/test_sector_generation_reader.py tests/test_sector_native_view.py tests/test_sector_generation_api.py tests/test_sector_generation_guard.py tests/test_factors_finite_json.py tests/test_deploy_git_history.py tests/test_dag_conformance.py`. Result: **602 passed, 3 skipped** (author: 601 / 3). The author did not give an exact command. My set is the round-2 list plus `test_dag_conformance`, which explains a difference of ±1.
- Central builder neighbours (my selection; the author's 111-test set is unnamed): `test_sector_central.py`, `_contract`, `_data_is_sync`, `_gate`, `_publication`, `_history`, `_measured_panel` → **279 passed**. Not the same set as the author's 111, so NOT VERIFIED as the identical selection.
- **Mutation check** (the review copy of `lib/sector_population.py` was mutated, then restored and verified byte-equal to `595fe6b75af2`):
  - Re-adding an "observed ⇒ explained" branch (R2-B1 return) fails `test_f1_completeness_is_computed_from_the_configured_roster` and `test_r2_b1_real_route_a_lost_served_row_is_not_complete`.
  - Ignoring `observation_refusals` (R2-B2 return) fails `test_r2_b2_real_route_a_refused_basket_stays_in_the_denominator` and `test_r2_b2_owner_refused_baskets_stay_in_the_denominator`.

  The new tests **do** catch a return of either blocker. No test covers R3-S1 (a basket absent from both lists).

## Sample
`shasum -a 256 /tmp/si_plan/v11/LANE1_WIRE_V11_SAMPLE_page1.json` → `dbb09959b4feaaf849ea369f667c34b2e390f3b12e5c509b1e86daedf8a49d80`. `wc -c` → 15284. Both match the author. The sample has `unserved_matching` and the closed reason list `['absent_from_price_panel','not_observed_at_effective_as_of','group_refused_by_owner_observation','unaccounted_by_owner']`, and reads `configured_current 1020, served 1015, accounted_unserved 5, unaccounted 0, complete True`.

## NOT VERIFIED
- Live host, nightly builder run, CI.
- `build_sector_central.main()` end to end (the author also lists this as untested).
- The author's exact 601 and 111 test selections.
- Wire doc (`LANE1_WIRE_V11.md`) prose beyond the `group_index` line.
- Whether lane 7 accepts the `etf_flows` shape.
- Behaviour of the real Supabase `paywall._fetch_supabase_user` versus `_mm_verify_uid_cached` divergence (both are seams in the fixture).

## Commands / artifacts
- Probes: `/tmp/si_plan/reviews/r3probes/test_zz_r3_probe.py` (also at `tree/tests/test_zz_r3_probe.py`), output in `r3probes/probe_run.txt`, real carry output in `r3probes/carry_real.txt`, suite tails in `r3probes/suites.txt`, mutants in `r3probes/mut_b1.py` and `mut_b2.py`.
- The review shell first hit the session-root quarantine. I followed the guard's mint recipe and entered the minted SSD worktree; only read-only git (`ls-remote`, `fetch`, `show`, `diff`) was run there.
