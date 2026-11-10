# Adversarial review, round 2: PR #10929 (lane 1 population route), range 5129620204c4..9c5db069856d

Reviewer: independent read-only reviewer (Claude Opus 5.5 child, ROUTE: review). Date 2026-11-10.
**Verdict: NOT READY. One BLOCKER remains: F1 is only PARTIAL.** `complete` can still be `true` while configured current members are dropped with no explanation from the owner. S1 and S2 are FIXED. S3 is FIXED for its listed items, but the gaps that hide the new F1 defect remain. Every round-1 PASS still holds.

## Provenance
- `git fetch origin pull/10929/head`; `git ls-remote origin refs/pull/10929/head` → `9c5db069856d1cd71def5e5ce575e79953a7a301`, so the PR head matches the reviewed commit.
- **Commit-id discrepancy.** `git log --oneline 5129620204c4..9c5db069856d` gives `8c3fed6ffa34`, **`01c661b0e448`** and `9c5db069856d`. The commit that the brief and the author's return call `cd5f7e1afb9e` (`returns/lane1.md:11`) is **not in the PR range**. The object exists locally, but the PR carries `01c661b0e448` ("carry GICS industry, S&P sub-industry and removal roster separately"). I reviewed the range as it is on the PR. Probably a pre-rebase SHA (NOT VERIFIED).
- The round-1 tree `/tmp/si_plan/reviews/tree` was verified at `5129620204c4`: `cmp` of `lib/sector_population.py` against `git show 5129620204c4:lib/sector_population.py` → SAME. The 8 files in `git diff --name-status` (2 added, 6 modified, no deletes) were overlaid with `git show 9c5db069856d:<path> > tree/<path>`. `pr_tree.tar` was deleted after this check.
- Wire sample: `shasum -a 256 LANE1_WIRE_V11_SAMPLE_page1.json` → `10b4b955…e10e9c`, 14,582 bytes. This **matches** the author's claim.

## Tests run (head tree)
- `pytest tests/test_sector_population.py tests/test_sector_central_carry.py tests/test_sector_native_view_typed_blocks.py tests/test_sector_generation_reader.py tests/test_sector_native_view.py tests/test_sector_generation_api.py tests/test_sector_generation_guard.py tests/test_factors_finite_json.py tests/test_deploy_git_history.py` → **541 passed, 3 skipped** (the same skips as round 1). This matches the author's count.
- Neighbour suites that touch the central builder: `test_sector_central_publication`, `test_sector_central_gate`, `test_sector_central_data_is_sync`, `test_sector_central_contract`, `test_sector_research_handoff`, `test_sector_central_paper`, `test_sector_intelligence_page`, `test_fif_x2_ownership_guards`, `test_dag_conformance` → **283 passed**.
- Reviewer probes: `r2probes/test_zz_r2_probe.py` (run as `tree/tests/test_zz_r2_probe.py` against the suite's real-byte fixture) → 4 passed. Outputs are quoted below. Real-byte scripts: `r2probes/carry_real.py` and `r2probes/f1_real.py`.

## Verdict table
| Item | Verdict |
|---|---|
| F1 completeness | **PARTIAL. BLOCKER remains** (R2-B1, R2-B2) |
| S1 token answers | **FIXED** |
| S2 durability | **FIXED** (one NOTE) |
| S3 tests | **FIXED for (a)–(e). The tests do not catch R2-B1/B2** |
| Q5 typed-block carry | PASS with NOTES. No new tier exposure, and nothing is readable anonymously |
| Q6 industry | PASS. 617/698 and 424/698 reproduced, kept separate, current-basis |
| Q7 regressions | No regression. All round-1 PASSes still PASS |
| Q8 notes | None raised to SHOULD-FIX. N2 is FIXED; N1/N3/N4/N5 stay NOTE |

---

## Q1 / F1: completeness. **PARTIAL**

**What is now right**
- **Who writes the denominator.** The denominator comes from `observation.configured_members`, written by the owner's `lib/closes_panel.py:443-505` (`population_observation`), which `engine/baskets.py:216` calls. It is put into `baskets.json` at `engine/baskets.py:297` (`"observation": basket_observation`). The owner computes it as members with `added <= as_of < removed` (`closes_panel.py:458-467`). So "configured minus removed" is the owner's own statement, not re-derived. Strictly, it also excludes members whose `added` date is in the future; there are 0 such members today. `build_population` does no request-time roster read: `lib/sector_population.py` has no `open`/`Path`/`read_text`, and the only `os.environ` use is the cursor key (`:350`, `:355`).
- **Real bytes reproduced** (`r2probes/f1_real.py`): `REAL {'configured_current': 1020, 'served': 1015, 'unserved': 5, 'unaccounted': 0, 'complete': True}`. The unserved members are defensives/KVUE, us_sector_staples/KVUE, regional_banks/WBS, us_sector_comm/PSKY and us_sector_comm/WBD, all `not_observed_at_effective_as_of`. Each one was confirmed to be in that group's `observation.missing_at_asof` (`in missing_at_asof: True`), so these five reasons come from owner evidence. Roster: 1046 rows, 26 removed. `carried.removed_members` has n=26. The sum of `observation.configured_members` is 1020.
- **Identity is per (group, member).** `unserved` entries carry `group_id` (`:263`), so KVUE counts twice, which is correct.
- **Page and filter consistency.** `capture.population` is built from the unfiltered `result.population` on every page (`app/sector_generation.py:595-602`), so it is identical across pages and filters. `group=` keeps its descriptor with `unserved` even when no row is served (`lib/sector_population.py:330-337`; probe: `('defensives', 18, 17, [KVUE…])`).
- **`complete` can be false or null.** `null` when any group lacks a roster (probe CASE C → `configured_current None, complete None`). `false` when a configured member is absent from `observed_members` and from both missing lists, or when a served row is not configured (fixtures `tests/test_sector_population.py:445-452`).
- **The independent check in the test is independent.** `tests/test_sector_population.py:157-166` rebuilds configured-minus-removed from `data/baskets/membership.json` and compares it with served ∪ unserved per group. It does not use the code under test. But it only proves that today's bytes have no anomaly. It cannot detect a wrong reason label (see R2-B1).

### R2-B1 — BLOCKER — `empty_price_tape` is a default label, not owner evidence. A silently dropped member is "accounted" and `complete` stays true
- **Code:** `lib/sector_population.py:259-260`: `elif symbol in observed: reason = "empty_price_tape"`. This label goes to any configured member that the owner observed **with a close at the as-of date** but that has no served row. It is not counted as unaccounted (`:265-266`), so `complete` stays true.
- **Why it is not owner evidence:** the producer cannot emit this state. `engine/baskets.py:241-250` keeps a member only if it is in `observed_now`, and then `tc = closes[t].dropna()`. "Observed" means `notna` at `idx.max()` in the same `closes` panel (`closes_panel.py:472-476`, called with `closes` at `engine/baskets.py:216`), so `tc` can never be empty for an observed member. Every real occurrence of "observed but not served" is therefore a member lost after the owner's observation: a serialization or truncation defect, a hand edit, or a partial rewrite. The code calls that loss a known, explained state.
- **Reproduction through the real route, using the suite's own fixture** (probe `test_probe_g2_silent_drop_is_called_complete`). `_advance` (`tests/test_sector_population.py:99-111`) publishes g2 with one served member removed and `observation` left untouched. Output:
  `PROBE g2 dropped housing CARR -> {'configured_current': 1020, 'served': 1014, 'accounted_unserved': 6, 'unaccounted': 0, 'complete': True} [{'group_id': 'housing', 'symbol': 'CARR', 'reason': 'empty_price_tape'}]`
  Per the owner, CARR had a close on 2026-11-06. The route tells an entitled consumer that the population is complete and that CARR has an empty tape. Both statements are false.
- **The author's "silent drop" fixture misses it.** `tests/test_sector_population.py:445-447` simulates the drop by also removing the symbol from `observed_members`. That is not a silent drop, because it changes the owner's own receipt.
- **Smallest fix:** delete the `empty_price_tape` branch, so that observed but not served → `unaccounted_by_owner`. Or use that reason only if the owner emits an explicit empty-tape list. Add a test that drops a served member while leaving `observation` intact and expects `complete:false`.

### R2-B2 — BLOCKER — a basket the owner refused is dropped from the denominator, and `complete` stays true
- **Code:** `build_population` iterates only `baskets["baskets"]`. It never reads the top-level `observation_refusals` that the same owner writes into the same captured `baskets.json` (`engine/baskets.py:217-228` appends `{"basket_id", "observation"}` and then `continue`s, so the basket and its configured roster are absent from `baskets[]`; the key is emitted at `engine/baskets.py:323`). The configured roster of a refused basket is the owner's own statement, and it is in the capture. The route ignores it.
- **Reproduction** (`r2probes/f1_real.py` CASE A, real bytes with `housing` moved into `observation_refusals` exactly as the producer would do it when coverage is below 60% or fewer than 3 members are observed):
  `CASE A whole basket refused (housing, 18 configured) {'configured_current': 1002, 'served': 997, 'unserved': 5, 'unaccounted': 0, 'complete': True}`
  18 configured current members vanish from both the numerator and the denominator, and `complete:true` is emitted. This happens on any data-outage night that knocks a basket below the owner's coverage floor. Today `observation_refusals == []` (real bytes).
- The suite's independent check would catch this on the day it happens, because it compares with all 49 roster baskets. The route has no such check.
- **Smallest fix:** for each `observation_refusals[i]`, add its `observation.configured_members` to `configured_current`, with every member in `unserved` under a new closed reason such as `group_refused_by_owner_observation`. Add the group to `groups` with `n_members_listed: 0`. If the key is missing or malformed, set `configured_current`/`complete` to `null`. Add the CASE A fixture.

### R2-N1 — NOTE — `accounted_unserved` also counts unaccounted members
`"accounted_unserved": len(population.unserved)` (`lib/sector_population.py:468`) includes `unaccounted_by_owner` entries. In the author's own silent fixture the wire would say `accounted_unserved:1, unaccounted:1`, which double-reports one member. `complete` is still correct because `unaccounted==0` is required. Fix: `accounted_unserved = len(unserved) - (count of unaccounted_by_owner)`, and `complete_rule` adjusted to match.

### R2-N2 — NOTE — `q` cannot find an unserved member
`q=KVUE` → `total 0, groups []` (probe). The member is listed only in `capture.population.unserved_members`. This is disclosed in that capture, so it is not dishonest, but a search UI shows "no result". Lane 3 should check the capture list.

## Q2 / S1: token answers. **FIXED**
- `app/sector_generation.py:556-566`. `CursorSecretInvalid` → 503 (`:558-559`). Other `PopulationError` → 400, for grammar only (`:560-561`). `claims is None` (MAC mismatch, `lib/sector_population.py:389-390`) → `unverified_kind == "x"` → 404 `ORIGINAL_UNAVAILABLE`, else 409 `CURSOR_RESET signature_unrecognised` (`:562-566`).
- Probe output (raw bytes):
  - forged `c` → `409 {"schema":"sector_generation.error/v1","code":"CURSOR_RESET","reason":"signature_unrecognised"}`
  - forged `x` → `404 {…"ORIGINAL_UNAVAILABLE"}`
  - forged unknown kind → 409 (same body)
  - `raw-bytes equal c: True  x: True` (stale after a key swap vs forged)
  - all carry `private, no-store`.
- **No oracle:** `unverified_kind` (`:401-413`) reads only the `k` the forger wrote. It reveals nothing about the key, the generation or the store, and the answer comes before any storage read. JSON decoding happens before the MAC check (`:385-388`), so "not JSON" → 400 and "JSON with a bad MAC" → 409/404. That depends only on the attacker's own bytes. `compare_digest` is unchanged.
- **Short secret fails closed:** `_key` raises `CursorSecretInvalid` for any set secret under 32 bytes (`:355-360`). Mint → outer `except Exception` → 503; open → 503. Tested for `""`, `"short"`, 31×x (`tests/test_sector_population.py:370-381`; passes). Malformed `"not a token"` → 400 (`:307`).

## Q3 / S2: durability. **FIXED**
- `key_is_durable()` (`lib/sector_population.py:348-351`) is true iff the env secret is ≥32 UTF-8 bytes. This is exactly the condition under which `_key()` derives from the secret and not from `_PROCESS_KEY` (`:353-361`). When the secret is short, mint fails with 503 before any body is emitted, so "durable" can never be published alongside a process key. `ref_durable` is computed in the same request as the mint (`app/sector_generation.py:590-602`).
- The test covers both states, and that a configured secret survives a `_PROCESS_KEY` swap (`tests/test_sector_population.py:348-367`).
- **R2-N3 — NOTE.** "durable" means only that the *signature* survives a restart. The ref still answers 404 once the generation leaves retention, and every outstanding token dies if the secret is rotated or differs per worker. The wire doc (`LANE1_WIRE_V11.md:58`) states the restart case. It should add "valid while the capture is retained and the secret is unchanged".

## Q4 / S3: tests. **FIXED for the listed items**
All of these run through the real route, the real reader, the real publisher and the real gate code, with only the Supabase identity function seamed:
- (a) restart: `:324-345`
- (b) secret: `:370-381`
- (c) duplicates: `:384-400`
- (d) refusal headers for 400/401, plus 404/409/503 in other tests
- (e) cross-actor `x` and `c` tokens: `:309-321`

The N2 401 test seams `api._actor_digest` (`:403-413`). My probe adds proof that **no `read_population` call happens** before that 401 (`read_population calls 0`).

**Still untested:**
1. A served member dropped with `observation` intact (R2-B1).
2. Refused baskets (R2-B2).
3. A cursor chain that crosses a qualification change (N3).
4. 403 `ENTITLEMENT_REQUIRED` headers on *this* route. They are covered generically by `_error`/`_gate_denial` (`app/sector_generation.py:283-299`) and by the API suite, not in `test_sector_population`.
5. A forged `x` token (only the stale `x` is tested; my probe covers forged).
6. `MAX_UNSERVED` refusal.
7. `carried` with a missing or malformed `member_industry`/`member_sub_industry` at the population level.
8. The real `build_sector_central.main()` writing `carried`. Only `build_carry` is exercised.

## Q5: typed-block carry
- **Size bound is enforced, not just asserted.** `_bounded` encodes and compares, ≤60 KiB (`lib/sector_central_carry.py:45-48`). The industry blocks are capped at 256 KiB (`:203-204`, `:251-252`). The native view re-checks ≤64 KiB per typed block (`engine/sector_native_view.py:1880`). Real sizes (`carry_real.py`):

  | block | bytes |
  |---|---|
  | removed_members | 1,909 |
  | r1 | 1,846 |
  | display_order | 1,111 |
  | etf_flows | 1,444 |
  | confluence | 2,686 |
  | bottoming_watch | 2,756 |
  | theme_table | 9,831 |
  | member_industry | 18,603 |
  | member_sub_industry | 20,236 |
  | **total `carried`** | **60,583** |

  All nine blocks are produced from real bytes.
- **Absent when the source is missing or malformed:** yes. Every reader returns `None` → the key is dropped (`:273`). `_read` refuses non-finite values (`:51-60`). A contradictory duplicate → `None` (`:195-196`, `:244-245`). The whole step is wrapped and falls back to `{}` (`scripts/build_sector_central.py:666-672`).
- **R2-N4 — NOTE — `source`/`as_of` are present as keys but not required.** `confluence` has no top-level `source`/`as_of` (real: `source None as_of None`). They are per universe (`:134-136`). Any block whose source lacks a date is still carried with `as_of: null` (e.g. `etf_flows` from `tile.get("asof")`, `bottoming_watch`). Smallest fix: drop a block whose `as_of` is not a string, and document that `confluence` is dated per universe.
- **R2-N5 — NOTE.** `removed_members` filters on the central `as_of` (`:223`, 2026-11-06), while `configured_members` uses the baskets `effective_as_of`. If those two dates differ and a removal falls between them, one member can appear both in `unserved`/served and in `removed`. Use the same date (the baskets `observation.effective_as_of`).
- **Who can read `sector_central.json`.** Carried blocks are written into `site/sectordata/sector_central.json` **and** `site/sector_central_data.js` (`scripts/build_sector_central.py:718-723`). Neither path is in `public`/`free_registered` (`config/site_access.yml`, grep), nor in any Caddy public exemption list (`app/deploy/Caddyfile:382,529,573` contain no `sectordata`, `sector_central_data.js`, `basketdata`, `stagedata`, `flow_desk` or `subsector_confluence`). So both are default-deny `premium.default_tier: essential`: **anonymous readers cannot fetch them.** They are not under `enforced_early` (`site_access.yml:757-777`), so while `PAYWALL_ENABLED=0` a registered Free account can fetch them directly. **Is this a new exposure?** No. Every carried source (`flow_desk.json`, `marketdata/subsector_confluence*.json`, `basketdata/baskets.json#theme_intel`, `basketdata/si_handoff.json`, `stagedata/screener.json`) is in the same default class, and the same Free account can already fetch it at its own URL. The rendered HTML does not receive `carried` (`build_sector_central.py:726-742`). The native projection copies only closed keys, not `carried` wholesale (`engine/sector_native_view.py:1777-1813`, `1916-1930`). The only newly published fact is the removal roster with dates from `data/baskets/membership.json`, which is not under `site/` and goes into the same tier. Caveat (**R2-N6, NOTE**): the API's "entitled-only" label for the four lane-7 blocks (`sector_native_view.py:1890-1893`) is not mirrored by the static estate. A preview-tier reader is refused them by the API but can direct-fetch them in `sector_central.json`. This was already true of their sources before the PR. If they must be site_full-only, they belong in the `/premiumdata/` payload. NOT VERIFIED: the live Caddy config matches the repo Caddyfile.
- **Compute:** `build_carry` + `_membership()` takes **0.70 s** on real bytes (`carry_real.py`; the `engine.baskets` import is excluded and is already in the builder's import chain, NOT VERIFIED). JSON reads only, so the effect on the ~67 min budget is negligible. Side effect: the synchronous `sector_central_data.js` (267 KB today) grows by ~61 KB.
- **R2-N7 — NOTE — undeclared DAG reads.** `config/dag.yml:4824-4830` declares only 5 reads for `scripts.build_sector_central`. The new reads are `stagedata/screener.json`, `marketdata/subsector_confluence*.json` (4), `data/baskets/membership.json`, plus the already undeclared `flow_desk.json` and `si_handoff.json`. `test_dag_conformance` passes, so it does not check reads. The ordering is asserted only by comments (`daily.yml:3625-3628`). Each block carries its own `as_of`, so the worst case is a stale but labelled block. Fix: declare the reads.
- **"No golden hash moves":** TRUE for the pinned tests. The committed `sector_central.json` has no `carried`, the native-view suites pass unchanged (541) and so do the central suites (283). Once a nightly writes `carried`, the live `sector_central.json` member sha and the entitled projection hash **will** change (the typed blocks become available). That is intended, not a golden-test break.

## Q6: industry. **PASS**
Real bytes (`carry_real.py`): `distinct served basket symbols 698`; `industry cover 617` (block holds 617 symbols, `stagedata/screener.json`, as_of 2026-11-09); `sub cover 424` (block holds 430, `marketdata/subsector_confluence.json`, as_of 2026-11-06).

Two separate row fields, `industry` and `sub_industry` (`lib/sector_population.py:209-226`), each with its own capture descriptor: `identity.industry_classification` / `sub_industry_classification` (`:449-450`). Each requires `point_in_time is False` to be `available` (`:160`), with basis `current_gics_industry_not_point_in_time` / `current_sp500_membership_not_point_in_time` (`sector_central_carry.py:31,33`). They are never merged. `membership_first_known` and `original_affiliation_set` stay `unavailable/not_produced` (`:451-453`).

## Q7: regressions at 9c5db069856d. **No regression**
| Round-1 PASS | Now | Evidence |
|---|---|---|
| Denied before read | PASS | parse `app/sector_generation.py:536` → `_authorize` `:541` → reader resolution → actor `:549` → 401 `:552` → token `:556` → read `:578`. Probe: 401 with `read_population calls 0`. |
| No arbitrary reads | PASS | Grammar unchanged (`:440-470`). The capture comes only from a verified token (`:576`). `unverified_kind` claims are never used to read. `build_population` has no I/O. |
| One capture | PASS | `:576-583` unchanged. Identity re-checked. |
| Bounds | PASS | `encode_sector_population(..., max_encoded_bytes=MAX_ENCODED_BYTES)` `:617-620`. `MAX_UNSERVED` 500 refuses rather than truncates (`lib/sector_population.py:282-283`). Sample page is 14,582 B. |
| Finite JSON | PASS | Canonical hash `allow_nan=False` (`:284-286`). Carry `_encoded allow_nan=False` and `parse_constant` refusal. Probe pages contain no NaN/Infinity (suite assertion `tests/test_sector_population.py:187`). |
| `private, no-store` on every answer | PASS | `_error`/`_reset`/success all use `_HEADERS` (`:138-143`, `:242-252`, `:432-437`). Probe confirms it on 401/404/409. |

## Q8: notes
- **N1** (no expiry): stays NOTE. Now that tokens can be durable, they live for as long as the secret and the retention do. Authorization still re-runs on every request (`:541`), so revoked entitlement is still enforced.
- **N2:** FIXED (`app/sector_generation.py:473-485`, `:549-552`; `lib/sector_population.py:307-312`). New side effect, **R2-N8 (NOTE):** a transient Supabase verification failure after the gates passed now answers `401 AUTHENTICATION_REQUIRED` rather than 503. That can push a logged-in paying reader to a log-in prompt. Consider 503 when a token cookie is present but verification returned None.
- **N3, N4, N5:** stay NOTE. Nothing in the new code makes them worse.

## Not verified
- Live host, nightly, real Caddy runtime config, the real `build_sector_central.main()` run with `carried`, nightly DAG ordering of screener/confluence vs central, and the `engine.baskets` import cost inside the builder.
- `cd5f7e1afb9e` was not reviewed. It is not on the PR; `01c661b0e448` was reviewed instead.

## Deviations
- The session guard quarantined Bash at the launch root, so I minted the prescribed SSD worktree `/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/t3-7e7aa529-6ce02674fa8dbc5e` (branch `claude/ssd-t3-7e7aa529-6ce02674fa8dbc5e`) and entered it. I ran only read-only git there.
- I overlaid the head files onto the round-1 extracted tree in place, added the probe `tree/tests/test_zz_r2_probe.py` (a copy is in `r2probes/`), and deleted `pr_tree.tar` as permitted.
- No repository edits, commits, pushes, PR comments, labels or network calls to production.
