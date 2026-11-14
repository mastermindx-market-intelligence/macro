# Adversarial review — PR #10929 (lane 1 population route), range eabee55527a3..5129620204c4

Reviewer: independent read-only reviewer (Claude Opus 5.5 child, ROUTE: review). Date 2026-11-10.
Verdict: **1 BLOCKER, 3 SHOULD-FIX, 5 NOTE.** Access control, path selection and cursor signing hold. The defects are in what the route *claims to know* (completeness and the "missing" semantics) and in cursor durability.

## Provenance of what was reviewed
- The named worktree `/Users/chriswong/.t3/worktrees/Macro Dashboard/t3-00553a7d` is **not** at the PR head. Its `.git` HEAD is `ref: refs/heads/t3/si-macro-generation`, and that ref resolves to `cae8e01be6ad…` (main), with no `lib/sector_population.py` present. As the brief instructed, I reviewed the commit object instead: `git rev-parse --verify 5129620204c4^{commit}` → `5129620204c45f7c26ab95888ee734295b4c918e`.
- Tree: `git archive -o /tmp/si_plan/reviews/pr_tree.tar 5129620204c4`, extracted to `/tmp/si_plan/reviews/tree`. All `tree/…` line numbers below are at that commit.
- Diff: `git diff eabee55527a3..5129620204c4` (13 files, +1307/−17).
- The author has since pushed `8c3fed6ffa34`, which adds `industry` and `carried` (per `/tmp/si_plan/returns/lane1.md:5`). This review does **not** cover that commit. The sample's sha256 is now `5bf9a3bc…f8e2`, not the `99c0058e…ef27` named in the brief (`LANE1_WIRE_V11.md:81` says it was re-pinned).

## Verdict table
| # | Standard | Verdict | Evidence |
|---|---|---|---|
| 1 | Denied before read | **PASS** | `app/sector_generation.py:535` parse → `:540` `_authorize` (regwall+paywall) → `:543ff` reader/actor/token. The incumbent route has the same order: `:498` parse → `:502` authorize → `:509` resolve. Before auth only `len(token) <= 1024` is checked (`:458-459`); the token is not decoded or verified. Probe: no cookie → 401; bad cursor with no cookie → 401, not 400. The test at `tests/test_sector_population.py:285-286` checks that no reader call happens. |
| 2 | No arbitrary reads | **PASS** | Closed grammar `_POPULATION_PARAMS` with a duplicate/unknown check (`app/sector_generation.py:449-453`). `audience` must be `entitled`. `limit` is `[0-9]{1,4}` and 1..200. `group`/`q` go through regexes (`lib/sector_population.py` `_GROUP_ID`, `_QUERY`). The generation id and content id come only from an HMAC-verified token. `read_retained_generation` re-validates the segment and sha256 grammar, refuses symlinks and checks the resolved path is under the root (`scripts/vps_live_orchestrator.py:2327-2354`). Probes: duplicate audience/limit, a blank name and empty `q` all → 400. |
| 3 | Cursor integrity | **FAIL (SHOULD-FIX)** | The signing itself is sound (layout below). Durability fails: the per-process fallback key, which is what production uses today, makes every outstanding cursor and `retained_resolver_ref` return **400 REQUEST_INVALID** after a restart (finding S1). Tokens never expire (N1). |
| 4 | One capture per read (SP01) | **PASS** (with N3) | The continuation passes `(g,c)` from the signed token to `read_retained_generation`, which never reads `current.json` (`app/sector_generation_reader.py:95`, `vps_live_orchestrator.py:2317-2368`). The route re-checks the result identity (`app/sector_generation.py:573-574`). There is no TOCTOU: the snapshot's `members` are the bytes the verifier hashed (`vps_live_orchestrator.py:2173-2176`, `2364-2368`). A partly gone capture → 409 `capture_not_retained` / 404 `ORIGINAL_UNAVAILABLE` (tested at `tests/test_sector_population.py:245-258`). |
| 5 | Complete & correctly joined (SP02) | **FAIL (BLOCKER, F1)** | Paging is correct: the filter runs on the full population before paging, the offset is signed, filter and limit are bound to the `c` token, order follows the captured row order, and a symbol in several groups gives one row per group (`lib/sector_population.py:205-222`, tests `:120-191`). **But** expected/admitted/complete is a tautology, and `missing` is misdescribed (F1). |
| 6 | Bounds | **PASS** | The 4 MiB check runs on the exact bytes returned (`lib/sector_generation_wire.py:581-586`, returned at `app/sector_generation.py:612`). `limit` ≤ 200. There is one `read_population` call per request (`:566-567`; test `:293-294`). `_HEADERS` (`private, no-store`) is on success, `_error` and `_reset` (`:138-143`, `:242-252`). Probe: every refusal carries `private, no-store`. |
| 7 | Honest unknowns | **FAIL (BLOCKER, F1; plus S2)** | `taxonomy_revision`, `membership_first_known`, `original_affiliation_set`, `currency`, `decision_cutoff` and `prophet_eligibility` are all `{"status":"unavailable","reason":"not_produced"}` (`lib/sector_population.py:159,301-307,…`). No current roster is labelled "original" (`original_affiliation_set` is unavailable). **However**, `population.complete:true` and `missing_reason:"owner_reported_missing_members"` misreport what the route knows (F1). `retained_resolver_ref` is advertised as a durable original ref but is not durable (S2). |
| 8 | Finite JSON | **PASS** | `lib/numeric.py:88-123`, `scripts/build_sector_action_board.py:32-33`, `scripts/build_site.py:2705-2716`. The probe covered float/np.float32/np.float64 NaN/±Inf, pd.NA, pd.NaT, ndarray and nested containers: all → null. Finite values, 0.0 and −0.0 are unchanged; keys are kept. Anything missed raises under `allow_nan=False`, e.g. a NaN dict key (fails closed). Side effect (N5): np.float32 1.1 is now written as the number `1.100000023841858`. Before, it raised TypeError, or under `default=str` in factors it was written as the string "1.1". |
| 9 | Tests | **PARTIAL FAIL (SHOULD-FIX, S3)** | The tests run real bytes through the real publisher, reader, route and gate code. Only the Supabase identity seam and the clock are faked. They are not mocks of the thing under test. Gaps: listed in S3. One test **asserts the F1 defect as correct** (`tests/test_sector_population.py:139-144`). |

## Cursor token layout (as read from `lib/sector_population.py:241-275`)
`base64url_nopad(raw) + "." + hex(HMAC-SHA256(key, raw))`. `raw = json.dumps({"v":1,"k":"c"|"x","o":offset,"g":generation_id,"c":content_id,"a":audience,"f":filter_sha256,"l":limit,"u":actor_sha256,"b":BASIS_VERSION}, sort_keys=True, separators=(",",":")).encode("ascii")`.
- **Canonical encoding:** JSON with sorted keys and ASCII-escaped strings is injective, so two different bindings cannot sign to the same bytes. Verification runs over the *received* raw bytes, not a re-serialization, and an attacker cannot produce a valid MAC over other bytes.
- **Verification:** `hmac.compare_digest` over hex strings (`:266`). The exact key set and types are checked *after* the MAC (`:268-275`). Malformed token → PopulationError → 400.
- **Key:** `SECTOR_GENERATION_CURSOR_SECRET` (≥32 bytes) → `HMAC(secret, "macro.sector_population.cursor.v1")`. If unset → `_PROCESS_KEY = os.urandom(32)` at import (`:227-238`). If short or empty → `PopulationError`: on mint the route returns 503 `SECTOR_GENERATION_UNAVAILABLE`, and on open it returns 400. **This fails closed**, confirmed by probe. The fallback key comes from a CSPRNG and can never be empty or predictable.
- **Bound:** capture (g,c), basis, audience, actor, plus filter, limit and offset for `k=c`. A `k=x` token binds only capture, actor, audience and basis (by design, offset 0, any filter).
- **Audience downgrade:** impossible. The route only accepts `audience=entitled` and checks `claims["a"]` (`app/sector_generation.py:558`).
- **Replay by another actor:** → 409 reset, confirmed for both a `c` token (test `:234-242`) and an `x` token (my probe). See N2 for the shared "anonymous" digest.
- **No expiry and no entitlement revision.** Readability: the claims are only base64-encoded, not encrypted (N4).

## Findings (most severe first)

### F1 — BLOCKER — `population.complete:true` is a tautology, and `missing` means the opposite of what the code and wire doc say
- **Code:** `lib/sector_population.py:165-170`. `expected` is the sum of `group["n_members"]`. `missing` is `len(group["missing"])`. `:320` sets `complete = expected == admitted`. `:321-322` sets `missing_reason = "owner_reported_missing_members"`. The comment at `:316-319` and `LANE1_WIRE_V11.md:60` say: "`missing` = listed members … (they remain listed)".
- **Producer facts:**
  - `engine/baskets.py:296` writes `"n_members": len(active), "members": active`. So `n_members == len(members)` by construction, and `complete` can never be false.
  - `active` excludes every configured member that is not observed at the last date, has an empty tape, or is removed (`engine/baskets.py:243-250`).
  - `missing` (`:231`) is the set of configured tickers absent from the price panel. These are **never** in `members`.
- **Reproduction (committed bytes at 5129620204c4):**
  - `site/basketdata/baskets.json`: silver_miners has `n_members 8`, `len(members) 8`, `missing ['GATO','MAG']`. Membership test: `[False, False]`, so they are **not listed**.
  - `data/baskets/membership.json`: 1046 configured rows, of which 26 are flagged removed, leaving 1020 current members. GATO (removed 2025-01-16) and MAG (removed 2025-09-04) are *removed* members, not current members lacking a measurement.
  - Five **current** (not removed) configured members are silently not served: regional_banks/WBS, defensives/KVUE, us_sector_comm/PSKY, us_sector_comm/WBD, us_sector_staples/KVUE.
  - The route (probe `test_probe_x_ref_cross_actor`) still emits `population = {"expected":1015,"admitted":1015,"missing":2,"complete":true,"missing_reason":"owner_reported_missing_members",…}`.
- **Wrong result:** a downstream engine is told the entitled population is **complete**. In fact 5 current constituents are dropped with no count. The "2 missing" are departed members, wrongly described as "listed members without a usable measurement".
- **The test enshrines it:** `tests/test_sector_population.py:139-144` asserts `complete is True` and `missing == 2`, with the false comment "they stay listed and are counted".
- **Fix direction:** the bundle does not carry the configured roster, so `complete` cannot be known from the generation. Either emit `complete`/`expected` as `{"status":"unavailable","reason":"not_produced"}`, or label the basis honestly ("listing of the owner's *observed active* members; configured roster not in capture"). Redescribe `missing` as "configured tickers absent from the price panel (not listed)", or drop it.

### S1 — SHOULD-FIX — cursors and `retained_resolver_ref` die on every restart, and the client sees "invalid request" instead of a reset
- **Code:** `lib/sector_population.py:227-238` (per-process key when the env var is unset). Route: `app/sector_generation.py:551-556` maps a MAC mismatch to `_error(400, REQUEST_INVALID)`.
- **Deployment:** no deploy/config file in the tree sets `SECTOR_GENERATION_CURSOR_SECRET`. `grep -rln` finds it only in `lib/sector_population.py`. The app runs as a single `uvicorn.run("app.main:app", …)` (`app/runtime_attestation.py:200`), and `update.sh` restarts it on every deploy.
- **Reproduction:** probe `test_probe_restart_key_rotation_gives_400_not_reset` mints page 1, then swaps `_PROCESS_KEY` (equivalent to a restart or a second worker). `next_cursor` → `400 {"code":"REQUEST_INVALID"}`. `context_ref` → `400 REQUEST_INVALID`. The expected answers are `409 CURSOR_RESET` and `404 ORIGINAL_UNAVAILABLE` respectively.
- **Impact:** a lane-6 consumer told to "persist `context_ref`" (`returns/lane1.md:47`) holds a reference that the next deploy silently invalidates. The failure is indistinguishable from a forged token. Nothing fails open.
- **Fix direction:** map `open_token → None` to `_reset("signature_unrecognised")`, and require the secret at startup (refuse to serve) instead of falling back silently.

### S2 — SHOULD-FIX — the "original ref" is misreported as a durable owner reference
- `compatibility_tuple` publishes `owner_ref.retained_resolver_ref` (`lib/sector_population.py:~297`) and `currentness:"retained_original"` as if they were stable. Given S1, the ref lives only for one process lifetime. The wire doc's "cursors reset on restart" (`LANE1_WIRE_V11.md:54`) is also wrong about the *answer*: the route returns 400, not a reset.

### S3 — SHOULD-FIX — test gaps (standard 9)
No test for:
- (a) restart or key mismatch → status code (S1);
- (b) short or empty secret → 503 on mint;
- (c) duplicate parameters (unknown names are tested; duplicates are not);
- (d) `Cache-Control` on refusals (only success is checked, at `:138`);
- (e) cross-actor use of an `x` token (only `c` is tested at `:234-242`);
- (f) a cursor chain that crosses a qualification change (N3);
- (g) any independent check of the completeness semantics. Instead, `:139-144` asserts the defect.

My probes covered (a) through (e).

### N1 — NOTE — tokens carry no expiry and no entitlement revision
A token stays usable for as long as the generation is retained (until key loss). Authorization is re-run on every request (`app/sector_generation.py:540`), so this does not bypass a revoked entitlement.

### N2 — NOTE — the actor digest falls back to a shared "anonymous" value
`_actor_digest` (`app/sector_generation.py:473-484`) gives `actor_digest(None)` whenever the uid lookup returns None. That happens when the regwall is disabled (`app/regwall.py:224-228`) or on a transient Supabase failure after the gate passed. All such callers share one digest, so their tokens are mutually replayable. Every one of them has already passed both gates, so no data crosses an access boundary. It weakens the "actor bound" claim only.

### N3 — NOTE — qualification is re-evaluated on each page of one capture
`now = self._clock()` runs on every read (`app/sector_generation_reader.py:102`), and `_capture_view` derives qualification from `now` (`lib/sector_generation_contract.py:121-139`). Within one cursor chain, page 1 can say `accepted` and page 2 `stale`. If the clock check raises, the page returns `503 SECTOR_GENERATION_UNAVAILABLE`, not a reset. The rows never mix, but the envelope's `qualification` and `read_captured_at` are not part of the capture.

### N4 — NOTE — cursor contents are readable
The claims are only base64-encoded, so any holder can read the generation id, content id and an unsalted `sha256("sector-actor:"+uid)`. That allows linking but not forgery.

### N5 — NOTE — `finite_json_value` changes the representation of some scalars
`np.float32`/`np.float16` values are now written as widened floats, e.g. `1.100000023841858`. Before, they raised, or were written as strings under `default=str`. No NaN/Inf leak was found.

Also outside the nine standards and not deeply reviewed: in `app/deploy/update.sh` the git path now resets to the literal `FETCH_HEAD` and the journal path to `$NEW`. I saw no intervening fetch in the diff context but did not trace the whole script. NOT-VERIFIED.

## Industry / sub-industry question
**Yes.** Existing producer artifacts carry a per-member **current** industry classification. None of them is point-in-time.
1. **`site/stagedata/screener.json`**, field `rows[].industry` (GICS industry; e.g. FOXA → `Media`). It covers **617 of the 698** distinct basket symbols. `sub_industry` is null for every row. Producer: `engine/stage_analysis.py:524-526` (`industry`, `sub_industry` from `stage_industry` frames), seeded from the GICS industry at `:1265-1266`/`:1516`. Same rows in `site/stagedata/stage_board_daily.json`. `asof 2026-11-09`.
2. `site/marketdata/sp500_heatmap.json` has `industry` on S&P 500 rows, covering 500 of the 698.
3. `data/profile/profiles.parquet`, column `sic_description` (SEC SIC industry text, current). Owner: `collectors/equity_profile.py`. Reader with `as_of`: `engine/classification_axes/sic_industry.py:22-26`. Also `data/edgar/cik_sic.json` (575 CIKs, `sic`, `sic_desc`). I could not compute coverage because pyarrow is not installed.

So the author's statement that "No other per-member industry field was found" besides `marketdata/subsector_confluence.json` at 424/698 (`returns/lane1.md:14`) is **incorrect**. `screener.json` already gives 617/698. Neither source is point-in-time, so the PIT identity gap (SI02) stands.

Searches run:
- `grep -rlniE "gics|sub_?industry|\"industry\"|'industry'|sic_code|naics" scripts engine lib` (~150 files);
- `grep -rl '"industry"' site data --include='*.json'` (11 artifacts);
- a coverage script joining each artifact's ticker→industry rows against the `baskets.json` symbols.

## Commands and tests
- `git rev-parse --verify 5129620204c4^{commit}`; `git diff --stat|… eabee55527a3..5129620204c4`; `git archive -o … 5129620204c4`; then tar extraction.
- `python3 -m pytest -q tests/test_sector_population.py tests/test_factors_finite_json.py tests/test_sector_native_view_typed_blocks.py tests/test_sector_generation_reader.py tests/test_sector_native_view.py tests/test_sector_generation_api.py tests/test_sector_generation_guard.py tests/test_deploy_git_history.py`
  → **521 passed, 3 skipped**. Skips: 2 at `test_sector_generation_reader.py:579` (owner-composition stack not on this lane); 1 at `test_sector_native_view.py:1328` (in-tree producer not at the pinned revision).
- Probes (in `/tmp/si_plan/reviews/probes/`):
  - `probe_cursor_numeric.py`: key, secret and `finite_json_value` matrix;
  - `test_review_probe.py`: 4 passed. Outputs are quoted above.

## Gaps
- `8c3fed6ffa34` (industry and carried blocks) is not reviewed.
- `profiles.parquet` coverage was not computed (no parquet engine).
- `update.sh` was only partly traced.
- No live-host check.
- `typed_blocks` was reviewed only for shape and fallbacks (the preview audience gets the full central blocks, by design at `engine/sector_native_view.py:~1880`). It was not checked against lane 7/8 needs.

## Deviations
- The session guard quarantined Bash in the launch root. I minted the guard's prescribed SSD worktree (`/Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/t3-7e7aa529-8bc2eb5c52857ee0`, branch `claude/ssd-t3-7e7aa529-8bc2eb5c52857ee0`) and entered it, only to run read-only git there. No source files were edited.
- I extracted the PR tree and wrote probe files under `/tmp/si_plan/reviews/`. Pytest runs wrote `__pycache__` only inside that extracted copy.
