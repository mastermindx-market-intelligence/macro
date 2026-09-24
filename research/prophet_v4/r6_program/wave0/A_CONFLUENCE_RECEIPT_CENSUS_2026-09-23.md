# A — Confluence receipt census for D01 (Prophet US R6, wave 0)

Lane `pu_a_receipt`. READ-ONLY: no `engine/`, `scripts/`, `tests/`, `templates/`, `.github/` or
`data/` file was modified. This record is the only write.

Question: does a CURRENT-SESSION, PRE-DECISION, qualified confluence (signal-gate) receipt exist
before a normal intraday B4 decision? This decides D01 (source-session validity).

**VERDICT: NO.** The sole writer of `site/factordata/signal_gate.json` stamps `as_of` from the last
COMPLETED daily close in the price store, so `as_of == market_session` for a session still in
progress is not merely unscheduled — it is unreachable from the writer's own inputs. In 13/13
committed samples on `origin/main`, `as_of` is strictly earlier than the emission date; in all 3
samples emitted INSIDE US RTH, `as_of` named a prior session. The emission clock is NOT the
obstruction — the session label is.

## SOURCE_SHA / HEADS READ

- SOURCE_SHA — detached HEAD, verified equal to `origin/main`: `88a3f1cfd18f391d2802e9086dc00f6fe5545607`, cited `@88a3f1cfd18f`.
- PR #7581 head — fetched as local ref `pu_a_7581`, never checked out: `39ef2cd48e091d90f12771aab142c2197022aa79`, cited `@39ef2cd48e09`. Its whole diff vs the merge-base is `engine/prophet_entry_availability_sources.py | 415 +` and `tests/test_prophet_strategy_definition.py | 373 +` (788 insertions, 0 deletions).
- Worktree is SPARSE (`data/`, `site/`, `mockups/`, `verify_shots/` omitted). Nothing was opted in; no `data/` artifact was read. Committed `site/` blobs were read from the git OBJECT STORE via `git show <rev>:<path>` — no checkout, no opt-in. The sparse policy hides nothing, it only omits bytes from the working tree, which is why the real `as_of`/`emit` pairs below are OBSERVED, not inferred.
- Finding comment `5789777976` is quoted from the lane spec and was NOT fetched (no `gh` call spent). The rule it describes was re-read independently and matches (Q3).

| # | spec item | where |
|---|---|---|
| 1 | the binding rule | `engine/prophet_entry_availability_sources.py:88-96,111-125,138-178,235-393@39ef2cd48e09` |
| 2 | the WRITER | `scripts/build_stock_library.py:275-287,3663,4873-4889,6512-6514@88a3f1cfd18f`; `as_of` origin `:2936-2947` → `scripts/build_site.py:3838-3855` → `engine/residual_alpha.py:172-179,208,277` → `engine/equity_factors.py:327-332` → `lib/closes_panel.py:6` → `collectors/breadth.py:5-8,291` |
| 2b | call chain into writer | `scripts/build_site.py:7539,7561-7563@88a3f1cfd18f`; `config.yml:2391-2392` (`stock_search.enabled: true`) |
| 3 | scheduling | `daily.yml:36-37,1895-1899,2204-2205,3061-3066,3198,4735@88a3f1cfd18f`; `scripts/ci/daily_engine_regime_dashboard.sh:104-108`; `scripts/ci/daily_engine_commit_outputs.sh:193-198`; `closing-bell.yml:40-43,60-69,123-130,264-296,558,579`; `weekly.yml:4,144`; `earlyclose.yml:46-56,240`; `render.yml:34-48,808`; `engine-render.yml:38-56,428`; `config/dag.yml:3927-3958`; session law `lib/nyse_calendar.py:36,183-197` |
| 4 | B4 / policy / definition | `engine/prophet_entry_availability.py:94-104,264-291,330-341,381-449@88a3f1cfd18f`; `engine/prophet_entry_policy.py:11-14,43-51,95-111,144-217`; `engine/prophet_strategy_definition.py:20-24,138-155` |
| 5 | intraday producers | `prophet-live.yml:65-67,184-188`; `entry-radar-live.yml:71-73,212-234`; `intraday-fastpath.yml:21,32,79-213`; `live-breadth.yml:31,72`; `intraday.yml:15,60`; `live-quotes.yml:35`; `engine/prophet_live/armed_pack.py:1-14,65-75,114,750-800@88a3f1cfd18f`; `engine/prophet_live/live_states.py:179,420-430,848-860`; `scripts/build_prophet_live_pack.py:1-18,146-177,214-222,387` |
| 6 | fixtures | `tests/test_prophet_strategy_definition.py:492-504,642-651@39ef2cd48e09`; `tests/test_stage_analysis.py:151-160@88a3f1cfd18f`; `tests/test_bottom_sensors.py:576`; `tests/test_altdata_price_truth.py:236`; `tests/test_fix43_analyst_and_whitehouse.py:117`; `tests/test_special_sits_intel.py:69`; plus the 13 real committed blobs below |

## Q1 — What does the writer set as `as_of` and the emission clock?  **OBSERVED**

Two different clocks, from two different sources, in one 3-key document (`{"as_of","verdicts","emit"}`
— confirmed against the committed blob's top-level keys), written at
`scripts/build_stock_library.py:4882-4885@88a3f1cfd18f`.

- **`as_of` is a SESSION DATE string, never a wall clock.** It is `alpha_asof`, read from `site/factordata/alpha.json`'s own `as_of` (`scripts/build_stock_library.py:2939-2945`), which `build_alpha_data` writes from `engine.residual_alpha.compute_residual_alpha` (`scripts/build_site.py:3850-3852`). That value is `str(R.index.max().date())` (`engine/residual_alpha.py:277@88a3f1cfd18f`), where `R` is the return matrix of the DAILY CLOSE panel (`:208`, from `_closes()` at `:173-174`; `engine/equity_factors.py:327-332`) — the `data/{breadth,smallcap_breadth,midcap_breadth,russell_breadth}/_closes_cache.parquet` union-forever close archives (`lib/closes_panel.py:6`, written by `collectors/breadth.py:291@88a3f1cfd18f`). **Timezone: none — a bare `YYYY-MM-DD` exchange session date, being the last COMPLETED daily bar in the store.**
- **The emission clock is the render host's UTC wall clock, taken at MODULE IMPORT:** `_PAIR_EMIT_STAMP = {"pair_id": uuid.uuid4().hex, "at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "writer": "build_stock_library"}` — `scripts/build_stock_library.py:283-287@88a3f1cfd18f`. Writer identity string: `"build_stock_library"` (`:286`). The same stamp object rides the board twin `us_standouts.json` (`:6512-6514`), which is what `scripts/check_signal_gate_coherence.py:29-31@88a3f1cfd18f` reads to detect a one-sided re-emit. That module's own comment states the law this census rests on: "`as_of` cannot reveal it — both stamp the DATA date, not the write time" (`scripts/build_stock_library.py:282`).
- Format note: `at_utc` is written `+00:00`, not `Z` (observed `2026-09-23T06:26:10+00:00`); `_utc()` accepts both (`engine/prophet_entry_availability_sources.py:88-96@39ef2cd48e09`).

### Real `as_of` / `emit.at_utc` pairs committed on `origin/main`  **OBSERVED**

Lane from the commit subject; commit times converted from `-07:00` to UTC; "session in progress"
uses US RTH 13:30–20:00Z; staleness vs `expected_last_session()` per
`lib/nyse_calendar.py:183-197@88a3f1cfd18f`.

| commit | lane | `as_of` | `emit.at_utc` (Z) | ET at emit | session in progress | `as_of` == it? | vs expected |
|---|---|---|---|---|---|---|---|
| `6fd01a29f0` | daily nightly | 2026-09-17 | 2026-09-18T15:40:33 | Thu 11:40 | Thu 09-18 RTH | **NO** | on time |
| `f43207a34d` | weekly deep-dive | 2026-09-18 | 2026-09-19T19:51:14 | Sat 15:51 | none (Sat) | n/a | on time |
| `aad54dc04d` | render markets | 2026-09-18 | 2026-09-19T19:51:14 | — | none (Sat) | n/a | same blob |
| `790af46a32` | render all | 2026-09-18 | 2026-09-21T14:57:05 | Mon 10:57 | Mon 09-21 RTH | **NO** | on time |
| `9cb8f3e21e` | render macro | 2026-09-18 | 2026-09-21T22:12:04 | Mon 18:12 | Mon post-close | **NO** | 1 stale |
| `6778c552b5` | closingbell | 2026-09-18 | 2026-09-21T23:20:32 | Mon 19:20 | Mon post-close | **NO** | 1 stale |
| `0dfd4d1aa3` | render-sync | 2026-09-18 | 2026-09-21T23:20:32 | — | — | **NO** | same blob |
| `7f95fd9922` | engine-render all | 2026-09-18 | 2026-09-22T03:02:02 | Mon 23:02 | none | **NO** | 1 stale |
| `9eacc0ecf2` | render all | 2026-09-18 | 2026-09-22T05:14:54 | Tue 01:14 | none | **NO** | 1 stale |
| `e77ddcedfe` | daily nightly | 2026-09-21 | 2026-09-22T16:44:41 | Tue 12:44 | Tue 09-22 RTH | **NO** | on time |
| `f426902719` | daily nightly | 2026-09-21 | 2026-09-23T06:26:10 | Wed 02:26 | none | **NO** | 1 stale |
| `10b8c5b3dc` | daily nightly | 2026-09-21 | 2026-09-23T06:26:10 | — | — | **NO** | same blob |
| `88a3f1cfd18f` | **SOURCE_SHA tip** | 2026-09-21 | 2026-09-23T06:26:10 | Wed 02:26 | none | **NO** | 1 stale |

Tip blob: `as_of="2026-09-21"`, `emit={"pair_id":"b96f79ec15d3485bac200aad29ee8be8","at_utc":"2026-09-23T06:26:10+00:00","writer":"build_stock_library"}`, 2,930 verdicts, 158 `eligible:true`. Two facts fall out: (i) `as_of < date(at_utc)` in 13/13, never equal; (ii) three emissions landed INSIDE RTH (`6fd01a29f0`, `790af46a32`, `e77ddcedfe`) and all three carried a prior session — so `emit.at_utc <= decision_clock` is satisfiable intraday while `as_of == market_session` is not.

## Q2 — At what UTC time does the scheduled path emit, and for which session?

Cron lines and the call chain are **OBSERVED**; the exact minute of the stamp is **INFERRED**
(labelled) because `at_utc` is a host wall clock taken mid-job.

Lanes that run `scripts.build_site` — and therefore `build_stock_library.main()` via
`scripts/build_site.py:7561-7562@88a3f1cfd18f`, gated only by `stock_search.enabled: true`
(`config.yml:2391-2392`) — are the ONLY lanes that can emit the receipt:

| workflow | trigger (UTC) | session the emit can carry |
|---|---|---|
| `daily.yml` (Build B, authoritative) | `cron: "30 22 * * *"` EDT / `"30 23 * * *"` EST — `daily.yml:36-37@88a3f1cfd18f`; both **18:30 ET**, ~2.5 h after the 20:00Z close | the just-closed session, only if collect landed its bar. `engine` job `needs: [et_gate, collect, government_revenue_projection]` (`:1896`); writer runs inside `bash scripts/ci/daily_engine_regime_dashboard.sh` (`:2204-2205`), whose `run_py … scripts.build_site` is line `104`; commit msg `engine: regime update $(date -u +%F)` from `scripts/ci/daily_engine_commit_outputs.sh:198`, called at `daily.yml:3198,4735` |
| `closing-bell.yml` (Build A, provisional) | `cron: '5 20 * * 1-5'` EDT / `'5 21 * * 1-5'` EST — `closing-bell.yml:68-69@88a3f1cfd18f`; **16:05 ET**, 5 min after the close | **the PRIOR session** — its own header: "The price store may not yet hold today's bar (it won't at 16:05 ET)" (`:40-41`). Runs `scripts.build_site` at `:294`; `--heal` is best-effort (`:123-130`); commits `git add site/` (`:558`), msg at `:579`; measured 109 min → site lands ~17:55 ET (`:65-67`) |
| `weekly.yml` | `cron: "0 14 * * 6"` — Sat 14:00Z (`weekly.yml:4`) | Friday at best; non-session day; `build_site` at `:144` |
| `earlyclose.yml` | **schedule RETIRED** — `on:` is `workflow_dispatch` only, both crons commented out (`earlyclose.yml:46-56`) | n/a (`build_site` at `:240`) |
| `render.yml` / `engine-render.yml` | `workflow_dispatch` + `push: branches:[main]` path filters (`render.yml:34-48`, `engine-render.yml:38-56`) — **event-driven, no cron** | whatever the store holds. These produced the three IN-RTH emissions in the Q1 table (`build_site` at `render.yml:808`, `engine-render.yml:428`) |

**Which session: the COMPLETED session (T-1 close), never the current one.** That is the repository's
own definition of what the store may hold, not a scheduling accident:
`lib.nyse_calendar.expected_last_session()` returns today's session ONLY once
`_CLOSE_PLUS_SETTLE = time(17, 0)` ET has passed (`lib/nyse_calendar.py:36,195-197@88a3f1cfd18f`) —
**21:00Z (EDT) / 22:00Z (EST)**, after the 20:00Z RTH close and 7 h after a 14:00Z decision. Its
docstring: "a same-day afternoon run conservatively expects only the PRIOR session" (`:186-188`).

**Emission wall-clock vs US RTH 13:30–20:00Z** (INFERRED from crons + observed samples): the two
SCHEDULED lanes emit at/after 20:05Z and 22:30Z — both after the close — and in practice hours later
(closingbell sample 23:20Z; nightly samples 15:40Z, 16:44Z, 06:26Z, the last from a run whose
build_site band fell next-day). No scheduled emission is anchored inside RTH.

## Q3 — Can a receipt with `as_of == TODAY's market_session` exist before a decision at 14:00Z today?

# **NO**

- **Cron citation:** `.github/workflows/daily.yml:36@88a3f1cfd18f` — `- cron: "30 22 * * *"  # 18:30 ET while America/New_York is on EDT (UTC-4, Mar→Nov)`; the only other scheduled writer is `.github/workflows/closing-bell.yml:68@88a3f1cfd18f` — `- cron: '5 20 * * 1-5'   # 20:05 UTC = 16:05 ET (EDT, Mar→Nov); 15:05 ET in winter → guard skips`. Both fire at/after the 20:00Z RTH close; neither can have run at 14:00Z for today's session.
- **Writer citation:** `scripts/build_stock_library.py:4883@88a3f1cfd18f` — `json.dumps({"as_of": alpha_asof, "verdicts": sig_out,`, with `alpha_asof` bound at `:2945` (`alpha_asof = _aj.get("as_of")`) from `engine/residual_alpha.py:277@88a3f1cfd18f` — `return {"as_of": str(R.index.max().date()), …`. `as_of` is the max date of the DAILY CLOSE matrix, so it cannot name session D before D's close bar exists.

Three independent legs, each sufficient:

1. **Structural (OBSERVED).** `as_of` comes from a completed-daily-bar panel; session D's bar is not expected before 17:00 ET = 21:00Z/22:00Z (`lib/nyse_calendar.py:36,195-197@88a3f1cfd18f`). A 14:00Z decision is 7 h earlier.
2. **Empirical (OBSERVED).** 13/13 committed samples have `as_of < date(at_utc)`; the three emitted inside RTH all carried a prior session (Q1 table).
3. **Contractual (OBSERVED).** For a PASS the session policy forces `decision_et.date() == market_session` (`engine/prophet_entry_policy.py:178-180@88a3f1cfd18f`) and refuses premarket/after-hours (`:181-186`), so a 14:00Z decision's `market_session` MUST be today — exactly the value the writer cannot produce. `market_session` is caller-supplied (`engine/prophet_entry_availability_sources.py:240@39ef2cd48e09`) and cross-checked against B3 (`engine/prophet_entry_availability.py:273-275@88a3f1cfd18f`), so it cannot be back-dated to the receipt either.

**The failure mode is a hard refusal, not a graceful UNKNOWN** (OBSERVED — the sharpest edge here).
`engine/prophet_entry_availability_sources.py:161-162@39ef2cd48e09` raises
`RuntimeOwnerFactError("signal-gate artifact session does not match B4 market_session")`; only
`signal_gate_artifact is None` degrades to `UNKNOWN` (`:157-158`). Wiring the REAL artifact into a
same-day B4 call therefore does not fail closed to `UNAVAILABLE_DATA` — it raises out of
`compose_runtime_owner_facts` and takes the whole evaluation with it. The second guard,
`emitted_at > decision_clock` (`:170-171`), is the satisfiable half (Q1 rows 1/4/10) — which is why
session equality, not the clock, is the binding constraint.

**ONLY-IF considered and rejected:** a push-triggered `render.yml`/`engine-render.yml` run can and
does emit inside RTH (`790af46a32` Mon 14:57Z; `e77ddcedfe` Tue 16:44Z), so the clock half is
reachable — but those emissions carried a PRIOR `as_of` because the close panel had not advanced. No
workflow's cron + writer composition yields `as_of == today` before today's close.

## Q4 — Honest compositions, ranked

### (a) RECOMMENDED — explicit versioned validity contract on the last-completed-session receipt

Make the receipt state, in its own bytes, which decision sessions it may serve. The producer already
emits a lineage stamp; this extends it rather than minting a second one.

- Fields (spec-named): `source_session` (today's `as_of`, renamed for meaning, NOT relabelled); `emitted_at` (today's `emit.at_utc`); `valid_for_decision_sessions` (explicit list, or a rule derived from `lib.nyse_calendar`); `expiry` (absolute UTC instant AND the last session served); `revocation` (monotone supersede token — the existing `emit.pair_id` is the natural carrier).
- Files / owners touched:
  - `scripts/build_stock_library.py:275-287` + `:4873-4889@88a3f1cfd18f` — the confluence PRODUCER (owner: the US stock-library builder, which also owns `us_standouts.json` and is therefore already bound by `scripts/check_signal_gate_coherence.py:29-31`). Additive keys only; `as_of` stays byte-identical so existing readers are untouched (`engine/stage_analysis.py:413-425`, `engine/neuralweb/bottom_sensors.py:159-170`, `engine/altdata_emit.py:34-36`).
  - `engine/signal_gate.py` — the GATE owner (T1→T4 cascade, `is_buyable`, `buy_signal`); must state that its verdict is CLOSE-ONLY (`:35-39@88a3f1cfd18f`) and hence what a next-session validity window claims.
  - `engine/prophet_entry_availability_sources.py:138-178@39ef2cd48e09` — the CONSUMER: replace the bare `as_of != market_session` raise with a contract read — decision session inside `valid_for_decision_sessions`, `emitted_at <= decision_clock`, not revoked → PASS with a receipt naming the SOURCE session; otherwise `UNKNOWN` (never a raise) so B4 fails closed to `UNAVAILABLE_DATA` (`engine/prophet_entry_availability.py:385-393,403-405@88a3f1cfd18f`).
  - `engine/prophet_strategy_definition.py:138-155@88a3f1cfd18f` — the POLICY owner: `owner_confluence_gate_may_be_waived: False` and `missing_or_stale_required_fact: "UNAVAILABLE_DATA"` already exist; the accepted source-session rule becomes a versioned field here so it sits inside the hashed definition identity, not an adapter convention.
  - `config/dag.yml:3927-3958@88a3f1cfd18f` — declare the widened write surface; `scripts/check_signal_gate_coherence.py` + `.github/ci/legacy-jobs.yml:218-257` — the pair-skew guard must learn the new keys.
- Must NOT do: **no date relabeling** — `as_of`/`source_session` must keep naming the session the closes actually belong to; writing today's date onto Friday's closes is the exact fraud the `_PAIR_EMIT_STAMP` comment (`scripts/build_stock_library.py:275-282@88a3f1cfd18f`) exists to expose. **No deletion of the equality check** as a silent widening — the session bind stays provable, only its SOURCE becomes explicit. **No second validity oracle** — reuse `lib.nyse_calendar`, the incumbent session-existence owner (`engine/prophet_entry_policy.py:98-101,123@88a3f1cfd18f`).
- Strongest counterargument: **it legalises a stale fact.** The Q1 table shows `as_of` one completed session behind `expected_last_session()` in 5 of 13 samples and up to 4 calendar days behind (Fri 09-18 still stamped on Tue 09-22). A window wide enough to survive that lag is wide enough to serve a verdict computed on a 2-4-session-old tape — and `owner_confluence` gates ENTRY_OPEN (`engine/prophet_entry_availability.py:421-423,439-449@88a3f1cfd18f`). The contract therefore needs a hard freshness ceiling (≤1 completed session) that fails to `UNKNOWN` rather than stretching, or it converts a data-freshness bug into a legitimate entry signal.

### (b) Intraday re-emission by the existing producer

- Files / owners: a bounded re-emit entrypoint in `scripts/build_stock_library.py` (same producer); a new intraday lane or an added step in `prophet-live.yml:65-67,184-188` or `entry-radar-live.yml:71-73,212-234` (both already fire every 5 min across 13:25–21:15Z); `config/dag.yml` (a second writer of `site/factordata/signal_gate.json` must be declared); `scripts/check_signal_gate_coherence.py` (pair-skew semantics when the gate emits N×/day but the board does not).
- Must NOT do: no relabelling a partial bar as a close; no overwriting the nightly's authoritative receipt without a supersede token; no second `pair_id` family that breaks the gate↔board skew detector.
- Strongest counterargument, close to fatal: **`signal_gate` is CLOSE-ONLY by construction** (`engine/signal_gate.py:35-39@88a3f1cfd18f` — it stochs the RSI of close), and its verdict is the validated §7 marker stream (reclaim-and-hold + bearish-div veto + 200MA bar-raiser; cut avg max drawdown −23.7% → −15.5% on 110 held-out US names). Run on an unfinished intraday bar it is a DIFFERENT statistic than the one validated, so (b) either silently changes the gate's meaning or owes its own validation study before it may gate an entry. Cost is law too: ~250 ms per gate call on ~2,900 names (`engine/prophet_live/armed_pack.py:65-67@88a3f1cfd18f`) ≈ 15-20 min per full pass — precisely why the armed pack precomputes instead.

### (c) Other — bind confluence from the intraday owner that ALREADY exists

- The repo already runs the same `signal_gate.gate` against candidate PROVISIONAL closes APPENDED AS THE NEXT SESSION'S BAR, nightly, and publishes the price interval over which `is_buyable` holds: `engine/prophet_live/armed_pack.py:1-14,114,750-800@88a3f1cfd18f` (`schema prophet_live.armed/v1`; `as_of` = store tip, `built_at` = UTC now), built by `scripts/build_prophet_live_pack.py:1-18,387@88a3f1cfd18f` at `daily.yml:3061-3066@88a3f1cfd18f`, with a US-only completed-session admission law at `:146-177,214-222`. The */5 lane compares a delayed live print to those edges and publishes `prophet_live.states/v1` with `meta.pass_ts` = the pass clock and `meta.session_et` = TODAY (`engine/prophet_live/live_states.py:179,420-430,848-860@88a3f1cfd18f`). That IS a same-session, pre-decision, natively-clocked confluence-derived fact — and the adapter already consumes it and already requires `pass_ts == decision_clock` (`engine/prophet_entry_availability_sources.py:276-281@39ef2cd48e09`). What it lacks is a per-name POSITIVE confluence verdict with lineage: the live state carries `state`, `price`, `quote_age_min`, `basis_status`, `basis_receipt` — not a signal-gate pair receipt.
- Files / owners: `engine/prophet_live/live_states.py` + `armed_pack.py` (owner: Prophet Live intraday); `scripts/build_prophet_live_pack.py` (owner: the nightly arming pass); `engine/prophet_entry_availability_sources.py` (consumer); `config/dag.yml:826-827`.
- Must NOT do: no promoting the pack's OPTIMIZATION into the truth — `armed_pack.py:8` is explicit ("The pack is an OPTIMIZATION; the gate is the truth"); an interval-membership test is not a gate call, so the receipt must name the construction (appended-bar provisional close) it was measured on; no reusing `center_buyable` (the as-of-close verdict) as today's — `armed_pack.py:27-45` documents that conflation: 45 of 180 probed names answered differently once the construction was fixed.
- Strongest counterargument: it binds `owner_confluence` to a PROVISIONAL-close verdict never validated as an entry gate in its own right, and makes a B4 fact depend on an R2-published artifact with a budget-cut coverage hole (`meta.skipped`, `armed_pack.py:71-75`) — a name whose band was not swept would be indistinguishable from one genuinely not forming unless the receipt carries coverage explicitly.

### (d) Do nothing — leave `owner_confluence` UNKNOWN

The current de-facto state: pass `signal_gate_artifact=None` → `UNKNOWN`
(`engine/prophet_entry_availability_sources.py:157-158@39ef2cd48e09`) → `OWNER_CONFLUENCE_UNKNOWN` →
`UNAVAILABLE_DATA` (`engine/prophet_entry_availability.py:385-393,403-405@88a3f1cfd18f`). Zero new
surface, zero staleness risk, ENTRY_OPEN unreachable until (a)-(c) lands. Files: none.
Counterargument: it makes the whole B4 vertical inert, and `owner_confluence_gate_may_be_waived: False`
(`engine/prophet_strategy_definition.py:152@88a3f1cfd18f`) means it cannot be routed around.

### Recommendation (the seat decides)

**(a), with (c) as the follow-on wave and (b) rejected.** (a) is the only composition that keeps the
incumbent owner, the validated close-only statistic and the existing lineage stamp intact while making
the source session a stated, versioned, revocable fact instead of an equality the producer can never
satisfy — provided its freshness ceiling is ≤1 completed session and fails to `UNKNOWN` rather than
stretching (Q1 shows the producer already runs 1 session behind `expected_last_session()` in 5 of 13
samples). (c) is the honest route to a genuinely same-session pre-decision positive and needs its own
validation, because it changes WHICH statistic gates the entry. (b) is rejected on
`engine/signal_gate.py:35-39@88a3f1cfd18f`.

## Q5 — Discriminating cases the eventual test must cover

All citations at `@39ef2cd48e09`; `T` = `tests/test_prophet_strategy_definition.py`. Fixture under
test: `_b4_signal_gate()` at `T:642-651` (`as_of="2026-09-18"`, `emit.at_utc="2026-09-18T19:30:07Z"`,
`pair_id="unit-pair-001"`, `writer="build_stock_library"`) against `_b4_runtime_kwargs()` at
`T:492-504` (`decision_at="2026-09-18T19:30:08Z"`, `market_session="2026-09-18"`).

| # | case | existing coverage | verdict |
|---|---|---|---|
| 1 | same-session pre-decision positive | `T:654-661` — `owner_confluence == "PASS"`, `"signal-gate-pair:unit-pair-001" in source_receipts` | COVERED but **synthetic**: a 19:30:07Z same-session emit (15:30 ET, inside RTH) is a pair NO real producer emits (Q1–Q3). Proves the adapter, not the pipeline |
| 2 | valid prior-session under explicit policy | **NONE.** Only the refusal side exists: `T:679-684` (`as_of="2026-09-17"` → "session does not match"). No `source_session`/`valid_for_decision_sessions` field exists to accept one | NONE |
| 3 | expired | **NONE.** The committed artifact has exactly three top-level keys (`as_of`, `verdicts`, `emit`) — no `expiry`. Nearest: `T:686-692` (post-decision emission) | NONE |
| 4 | late emission | `T:686-692` — `at_utc="…19:30:09Z"` > decision clock `19:30:08Z` → "emitted after B4 decision clock" | COVERED |
| 5 | retraction / revocation | **NONE for confluence** — `_bind_owner_confluence` (`:138-178`) takes no revocation input. Adjacent but a DIFFERENT owner: `T:339-348` (`event_status RETRACTED` → `INVALIDATED`), `T:756-798` (B1 relation receipt / `RETRACTED.correction_of`) | NONE |
| 6 | missing / non-eligible → UNKNOWN | PARTIAL. Non-buyable → `T:663-668`; malformed (`eligible="true"`) → `T:670-676`. Artifact absent (`None`) → `UNKNOWN` by `:157-158` + `_GATE_DEFAULTS:29-39`: exercised at `T:507-529`, `T:532-558` but `owner_confluence == "UNKNOWN"` is never asserted for it, and `OWNER_CONFLUENCE_UNKNOWN` appears in no blocker assertion. Verdict row absent for the symbol (`:172-175`) → none | PARTIAL |
| 7 | holiday / shortened close | Session policy COVERED: `T:834-846` (2026-11-27 and 2026-12-24 close 13:00 ET, not a hardcoded 16:00), `T:849-859` (2026-11-26 Thanksgiving, 2026-07-03 observed → `NON_SESSION`). Confluence-RECEIPT side (what `as_of` a shortened-close/holiday-adjacent run stamps; whether a validity window may span a closure) → none | PARTIAL |
| 8 | identity / basis unresolved | `T:561-570` (no ticker-equality fallback; alias round-trip refusal), `T:573-612` (synthetic `quote_ts`; `state == "dark"`; missing `basis_receipt`; quote↔live-state price disagreement) | COVERED |
| 9 | source-health failure | **NONE.** `source_health` is hardcoded `"PASS"` in `_GATE_DEFAULTS:34`, asserted PASS once at `T:516`; the adapter RAISES on bad quote/live-state inputs (`:265-290`) rather than setting FAIL, so `SOURCE_HEALTH_FAILED` (`engine/prophet_entry_availability.py:381-384@88a3f1cfd18f`) is unreachable from the adapter and untested here | NONE |
| 10 | risk / liquidity / gap not yet positive | `T:518-519`, `T:542-544` (all three `UNKNOWN` through the adapter), `T:556-558` (the three `*_UNKNOWN` blockers), `T:325-336` (each `FAIL` → `NOT_READY` with its own blocker) | COVERED |
| 11 | exact adapter-to-B4 response | `T:521-529`, `T:547-558` — `evaluate_runtime_entry_availability` → `state == "UNAVAILABLE_DATA"`, `entry_open is False`, named blockers; injection refusal end-to-end `T:615-637`. NOTE: no test reaches `ENTRY_OPEN` via the adapter, because `risk_ceiling`/`liquidity_fillability`/`gap_velocity` stay `UNKNOWN` by design (`:29-39`) — a same-session confluence PASS alone cannot open an entry | COVERED (negative path only) |

Extra case this census adds, not in the spec list: **`as_of` lagging `expected_last_session()`** (5 of
13 observed samples). Any (a) validity contract needs a test for "well-formed, unexpired, unrevoked,
and STILL one completed session staler than the store should be" → must be `UNKNOWN`, not PASS.
Existing coverage: **NONE**.

## EVIDENCE

Run in the worktree root. `rc` = shell exit status; tails verbatim, `…` marks elision.

```
$ git rev-parse HEAD; git rev-parse origin/main
88a3f1cfd18f391d2802e9086dc00f6fe5545607
88a3f1cfd18f391d2802e9086dc00f6fe5545607                       rc=0  # HEAD == origin/main
$ python3 scripts/worktree_sparse.py status
worktree-sparse: SPARSE checkout — omitting data, mockups, site, verify_shots    rc=0
$ git fetch origin pull/7581/head:pu_a_7581 && git rev-parse pu_a_7581
 * [new ref]               refs/pull/7581/head -> pu_a_7581
39ef2cd48e091d90f12771aab142c2197022aa79                       rc=0  # == the spec's head
$ git diff --stat $(git merge-base pu_a_7581 origin/main) pu_a_7581
 engine/prophet_entry_availability_sources.py | 415 +++++++++++…
 tests/test_prophet_strategy_definition.py    | 373 +++++++++…
 2 files changed, 788 insertions(+)                            rc=0

$ git show pu_a_7581:engine/prophet_entry_availability_sources.py | nl -ba -v1 | sed -n '157,178p'
   157      if signal_gate_artifact is None:
   158          return "UNKNOWN", None
   161      if signal_gate_artifact.get("as_of") != market_session:
   162          raise RuntimeOwnerFactError("signal-gate artifact session does not match B4 market_session")
   166      if emit.get("writer") != "build_stock_library":
   169      emitted_at = _utc(emit.get("at_utc"), "signal_gate.emit.at_utc")
   170      if emitted_at > decision_clock:
   171          raise RuntimeOwnerFactError("signal-gate owner verdict was emitted after B4 decision clock")
   176      if verdict.get("eligible") is not True or not signal_gate_is_buyable(dict(verdict)):
   178      return "PASS", f"signal-gate-pair:{pair_id}"        rc=0

$ rg -n "signal_gate.json" -g '*.py' . | rg "write_text"
./scripts/build_stock_library.py:4882   # the ONLY production writer; every other hit is tests/   rc=0
$ sed -n '283,287p;4882,4885p' scripts/build_stock_library.py
_PAIR_EMIT_STAMP = {
    "pair_id": uuid.uuid4().hex,
    "at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    "writer": "build_stock_library",
}
            (site / "factordata" / "signal_gate.json").write_text(
                json.dumps({"as_of": alpha_asof, "verdicts": sig_out,
                            "emit": _PAIR_EMIT_STAMP},
                           separators=(",", ":"), default=str, allow_nan=False))  rc=0
$ sed -n '277p' engine/residual_alpha.py
    return {"as_of": str(R.index.max().date()), "n": int(len(d)), "note": NOTE,   rc=0
$ rg -n "scripts.build_site|build_site\b" .github/workflows/*.yml scripts/ci/*.sh
closing-bell.yml:294  earlyclose.yml:240  engine-render.yml:428  render.yml:808
weekly.yml:144  scripts/ci/daily_engine_regime_dashboard.sh:104                   rc=0
$ sed -n '7561,7562p' scripts/build_site.py
        from scripts.build_stock_library import main as build_library
        build_library()                                                           rc=0

$ rg -n "cron:" .github/workflows/{daily,closing-bell,weekly,earlyclose}.yml
daily.yml:36:    - cron: "30 22 * * *"  # 18:30 ET while America/New_York is on EDT (UTC-4, Mar→Nov)
daily.yml:37:    - cron: "30 23 * * *"  # 18:30 ET while America/New_York is on EST (UTC-5, Nov→Mar)
closing-bell.yml:68:    - cron: '5 20 * * 1-5'   # 20:05 UTC = 16:05 ET (EDT, Mar→Nov); 15:05 ET in winter → guard skips
closing-bell.yml:69:    - cron: '5 21 * * 1-5'   # 21:05 UTC = 16:05 ET (EST, Nov→Mar); 17:05 ET in summer → stamp-dedup skips
weekly.yml:4:    - cron: "0 14 * * 6"    # Saturday 14:00 UTC — deep-dive report
earlyclose.yml:55:  #     - cron: "20 21 * * 1-5"   ← COMMENTED OUT (schedule retired :48-53)
earlyclose.yml:56:  #     - cron: "20 22 * * 1-5"                                  rc=0
$ rg -n "cron:" .github/workflows/{prophet-live,entry-radar-live,intraday-fastpath,live-breadth,intraday,live-quotes}.yml
prophet-live.yml:65-67       25,30,35,40,45,50,55 13 * * 1-5 | */5 14-20 * * 1-5 | 0,5,10,15 21 * * 1-5
entry-radar-live.yml:71-73   (identical window)   intraday-fastpath.yml:21,32  */30 11-21 | */30 1-8
live-breadth.yml:31  5,35 13-20 * * 1-5   intraday.yml:15  35 13-21 * * 1-5   live-quotes.yml:35  */5 * * * 1-5
# NONE of those six runs scripts.build_site, so NONE can emit signal_gate.json (spec item 5 → NONE):
# prophet-live.yml:186-188 → prophet_live_evaluator; entry-radar-live.yml:214-234 → entry_radar_live_pack /
# entry_radar_live; intraday-fastpath.yml:79-213 → build_live_overlay, build_risk_state, build_sp500_heatmap,
# build_intraday_flow, build_basket_pulse, build_live_quotes, notify_turn_events; live-breadth.yml:72 →
# live_breadth_poller (reads _closes_cache at :226, writes only site/live at :514); intraday.yml:60 →
# build_polygon_intraday.

$ git ls-tree origin/main site/factordata/signal_gate.json
100644 blob 2acc74029cdc30f6bea115f56d2c0c38c25dbb59	site/factordata/signal_gate.json
$ git cat-file blob 2acc74029cdc30f6bea115f56d2c0c38c25dbb59 | python3 -c "…"   # 724832 bytes
top-level keys: ['as_of', 'emit', 'verdicts']
as_of: '2026-09-21'
emit: {"pair_id": "b96f79ec15d3485bac200aad29ee8be8", "at_utc": "2026-09-23T06:26:10+00:00", "writer": "build_stock_library"}
n verdicts: 2930     eligible counts: Counter({'False': 2772, 'True': 158})       rc=0

$ git log --format='%h | commit=%cI | %s' -n 11 origin/main -- site/factordata/signal_gate.json
f426902719 | 2026-09-23T01:43:17-07:00 | engine: regime update 2026-09-23
e77ddcedfe | 2026-09-22T13:51:37-07:00 | engine: regime update 2026-09-22
6778c552b5 | 2026-09-21T17:35:50-07:00 | closingbell: full close render 2026-09-21 (scope=close)
790af46a32 | 2026-09-21T09:59:07-07:00 | render: site re-render 2026-09-21 (scope=all, from=bede0712670b)
… 7 more (9eacc0ecf2, 7f95fd9922, 0dfd4d1aa3, 9cb8f3e21e, aad54dc04d, f43207a34d, 6fd01a29f0)  rc=0
$ rg -n "engine: regime update" .github/workflows/*.yml scripts/ci/*.sh; rg -n "daily_engine_commit_outputs" .github/workflows/*.yml
scripts/ci/daily_engine_commit_outputs.sh:198:  "engine: regime update $(date -u +%F)"
.github/workflows/daily.yml:3198   .github/workflows/daily.yml:4735               rc=0
# → "engine: regime update" commits are daily.yml's nightly engine-job commit step.

$ for s in 88a3f1cfd18f f426902719 e77ddcedfe 9eacc0ecf2 7f95fd9922 6778c552b5 9cb8f3e21e \
         790af46a32 f43207a34d 10b8c5b3dc 6fd01a29f0 aad54dc04d 0dfd4d1aa3; do
    git show "${s}:site/factordata/signal_gate.json" | python3 -c '…as_of/emit…'; done
88a3f1cfd18f as_of=2026-09-21 at_utc=2026-09-23T06:26:10+00:00 writer=build_stock_library n=2930 elig=158
790af46a32   as_of=2026-09-18 at_utc=2026-09-21T14:57:05+00:00 writer=build_stock_library n=2930 elig=120
6fd01a29f0   as_of=2026-09-17 at_utc=2026-09-18T15:40:33+00:00 writer=build_stock_library n=2932 elig=135
… 10 further rows, all writer=build_stock_library — the complete 13-row table is in Q1.
                                                    rc=0   # 13/13: as_of < date(at_utc)
# TRAP for the next session: the first attempt printed 13 × "UNREADABLE / Expecting value: line 1
# column 1" with rc=0, because zsh applies the `:s` history modifier to "$s:site/…" and git received
# a bad revision. Quoting as "${s}:site/…" fixes it. A silent empty-output failure, not a data problem.

$ sed -n '36p;183,197p' lib/nyse_calendar.py
_CLOSE_PLUS_SETTLE = time(17, 0)
def expected_last_session(now: datetime | None = None) -> date:
    """The most recent COMPLETED session whose daily bar the price store should hold.
    'Completed' = the regular 16:00 ET close plus a settle buffer has passed (17:00 ET),
    so a same-day afternoon run conservatively expects only the PRIOR session. …"""
    if is_session(today) and now_et.time() >= _CLOSE_PLUS_SETTLE:
        return today
    return last_session_on_or_before(today - timedelta(days=1))                   rc=0

$ rg -n "at_utc" tests/ | rg "signal_gate"
(no hits)  # no committed tests/ fixture carries a signal-gate emit stamp except the synthetic
           # one at tests/test_prophet_strategy_definition.py:642-651@39ef2cd48e09
$ sed -n '151,160p' tests/test_stage_analysis.py
    (fd / "signal_gate.json").write_text(json.dumps({
        "as_of": "2026-07-17",
        "verdicts": { … },
    }))                 # pre-stamp shape: as_of + verdicts, NO emit block          rc=0
```

No test, lint or CI command was run for this record: the deliverable is a research Markdown file and
the lane spec names no validator for it. `python3 -m pytest` was not invoked at all (the suite must
not run in a sparse worktree). No `gh` call was made during the investigation. Nothing here asserts a
CI status.

## BLOCKED

Nothing blocked. Every READ item in the spec was completed, including the one the sparse checkout
could have prevented: the committed `site/factordata/signal_gate.json` blobs were reachable from the
git object store without opting into `site/`, so the real `as_of`/`emit` pairs — the strongest
evidence here — were observed, not inferred.

## NOT_ESTABLISHED

Each UNKNOWN names the artifact that would close it.

1. **UNKNOWN — which Actions RUN produced each observed `emit.at_utc`.** Commit subjects name the LANE (`engine: regime update` → `daily.yml`; `closingbell:` → `closing-bell.yml`; `render:`/`engine-render:` → the push/dispatch lanes) but not the run id, the fired cron, or the job timeline. Missing artifact: the Actions runs/jobs API timeline for `daily.yml` and `closing-bell.yml` over 2026-09-18 → 2026-09-23 (no CI polling, per lane law). Does not weaken Q3 — the cron lines and the writer's inputs are both directly cited.
2. **UNKNOWN — why `as_of` sat at 2026-09-21 (Monday) when the nightly emitted 2026-09-23T06:26Z (Wednesday), one completed session (Tue 09-22) behind `expected_last_session()`.** Candidate causes not separable from the tree: Tuesday's close never landing in `data/breadth/_closes_cache.parquet`; an `actions/cache` restore miss; `build_alpha_data` reading a stale panel. Missing artifacts: `data/breadth/_closes_cache.parquet` (gitignored AND sparse-omitted — deliberately not opted into) and that night's `collect` job log. The same UNKNOWN explains Fri-09-18 still stamped on Tue-09-22.
3. **UNKNOWN — real intraday coverage of `prophet_live.armed/v1`** (`meta.probed_n`, `armed_n`, `skipped`). The pack publishes to R2 at `live_flow/prophet_live_armed.json`, not to the repo (`scripts/build_prophet_live_pack.py:5-6@88a3f1cfd18f`; `scripts/freshness_sentinel.py:593-601@88a3f1cfd18f`). Missing artifact: the R2 object. Bounds Q4(c); does not affect Q1–Q3.
4. **UNKNOWN — whether `--heal` ever lands today's bar before the closing-bell render.** `closing-bell.yml:40-43,123-130@88a3f1cfd18f` calls it best-effort and predicts it will not; the single observed closingbell sample (`6778c552b5`, Mon 16:05-ET lane) carried Friday's `as_of` — consistent, but n=1. Missing artifact: `scripts.check_price_store_freshness --heal` output from several closing-bell runs. Even a YES cannot satisfy Q3: that lane fires at 20:05Z, after the 20:00Z close and 6 h after a 14:00Z decision.
5. **NOT VERIFIED — finding comment `5789777976`** on #7581. Quoted from the lane spec only; no `gh` call was spent on it and no PR/issue was commented on. The rule it describes was re-read independently at `engine/prophet_entry_availability_sources.py:161-171@39ef2cd48e09` and matches.
