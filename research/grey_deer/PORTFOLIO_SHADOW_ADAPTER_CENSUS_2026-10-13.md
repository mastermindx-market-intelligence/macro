# GD-9A census — where a portfolio envelope shadow adapter would plug in

Read-only census for WS card GD-9A (Portfolio envelope shadow adapter, zero book mutation).
No adapter is designed or written here. No book, envelope, or governance file was modified.

| Source | Commit read |
|---|---|
| macro worktree (`origin/main`) | `eb7c4d674235d3c4e4cda3291e8453d91fdfece8` |
| Mastermind `origin/master` (after one `git fetch -q origin`) | `98d00027cf5e228be9bd584684ad0284769cdf74` |

Mastermind was not checked out. Every Mastermind cite is `git show` / `git grep` / `git ls-tree` of that SHA. The clone's local `HEAD` was behind the fetched ref (`4c6b206d3fb7fbc6d077faf61ae361bedf259925`) and was not used. Default branch: `refs/remotes/origin/HEAD` → `origin/master`.

Card state in `agentos/workstreams/WS-GREY-DEER-RISK-INTELLIGENCE.md`: GD-3 done (`:163-233`), GD-9A todo depending on GD-3 (`:328-331`), GD-10 todo depending on GD-9A (`:332-335`). The card's own next-action line still says GD-9/10 are uncommissioned (`:398`). The binding shape of the adapter is the command packet, not new code: a shadow comparison of the local market-risk stack against the served Grey Deer bundle, with zero book behavior change (`research/grey_deer/GREY_DEER_FABLE_EXECUTION_COMMAND_PACKET_2026-08-19.md:999-1033`).

---

## The envelope a shadow import would read

Composer: `engine/risk_envelope.py`. Schema constant `SCHEMA = "mastermind.risk_envelope/v1"` (`:128`). Definition `grey-deer-v1-2026-08-19` (`:129`). `compose_envelope(...)` (`:777-872`) is pure: no clock, no disk. Birth authority is hard-false (`_authority`, `:610-618`):

- `envelope_may_rank`, `envelope_may_gate`, `envelope_may_size`, `envelope_may_execute` are all `False`
- `policy_actions_require_individual_authority` is `True`

JSON Schema required keys (`contracts/risk_envelope.schema.json:7-12`): `schema`, `definition_id`, `market`, `revision`, `bundle_id`, `source_session`, `as_of`, `observed_at`, `produced_at`, `stale_after`, `measured_state`, `hazard_summary`, `episodes`, `policies`, `policy_summary`, `data_state`, `coherence`, `coverage`, `freshness`, `correction`, `provenance`, `authority`. The schema `$id` is `https://mastermind-x.com/contracts/risk_envelope.schema.json` (`:2`). That is an identifier in the file, not a verified fetch URL.

Semantic body built at `engine/risk_envelope.py:817-850`, then clocks and `bundle_id` attached at `:865-872`. V0 ships `episodes: []`, `policies: []`, `policy_summary.posture = "NORMAL"` with `basis = "zero_active_policies"` and `display_only: True` (`:829-840`). `repair_state` is `None` (`:843`). When a rotation source is present, `rotation_context`, `confluence`, and `market_transition` are added (`:855-863`); confluence cannot change stage or policy (`:771-773`).

`revision` is only `settled`, `live_provisional`, or `corrected` (`:802-803`).

### Where the bytes are written

| Lane | Writer | Paths |
|---|---|---|
| Settled | `scripts/build_risk_envelope.py` `write()` `:806-812` | `data/risk_envelope/latest.json` (`data_path`, `:755-756`) and `site/riskdata/risk_envelope.json` (`site_path`, `:759-760`). Same canonical JSON bytes. |
| Live provisional | `scripts/build_live_risk_envelope.py` `write()` `:793-804` | `site/live/risk_envelope.json` (`out_path`, `:204-205`) only. |

The live file is the composed envelope plus a wrapper (`scripts/build_live_risk_envelope.py:741-750`): `built`, `live_active`, `stale_reason`, `stale_after_min`, `precedence`, `overlays`, `live_transition`, `clocks` (`event_time`, `upstream_built`, `observed_at`, `produced_at`). The composer is called with `revision="live_provisional"` and `stale_after=None` (`:685-694`). An accepted dwell transition can also append `data/reflexes/risk_envelope_materiality/firings.jsonl` (`:99-109`). That is telemetry, not a book.

Signal-bus owner of the settled site file: `config/synapse.yml:783-811` (`risk-envelope-settled`, producer `scripts/build_risk_envelope.py`, external consumer declared as `mastermind:brain/neural_web_context.py`). `docs/SIGNAL_BUS.md:492` and `:1970-1976` repeat that contract.

### How it is served

Host boundary is `www.mastermind-x.com` (`config/site_access.yml:1-5`). Caddy is default-deny for non-HTML assets not listed under `public`.

- `/riskdata/risk_envelope.json` is not in `public`. The workstream records the anonymous 401 as the intended payload gate (`agentos/workstreams/WS-GREY-DEER-RISK-INTELLIGENCE.md:142-143`).
- `/live/risk_envelope.json` is not on the `/live/` exception list (`config/site_access.yml:325-339`). The page script's relative feed is `live/risk_envelope.json` (`templates/risk_envelope_live.js:15`), and that file says an anonymous 401 must stay quiet (`:4-6`). The allowlist comment says the payload stays registration/tier-gated (`config/site_access.yml:285-286`).
- `site/live/risk_envelope.json` is the VPS live plane. The workstream records it as gitignored on the box (`agentos/workstreams/WS-GREY-DEER-RISK-INTELLIGENCE.md:24` is an owns-path; `docs/AGENT_OS_STATE.md:271` says that owns-path is absent from the repo). A git sparse checkout of macro does not contain the live bytes.

### Second publication, the one Mastermind actually opens

`engine/neuralweb/world_state.py:4897-4935` calls `engine.neuralweb.rotation_risk_context.read_context`, which reads only `data/risk_envelope/latest.json` (`rotation_risk_context.py:126-134`). That block is stored as `world_state["risk_envelope"]`. `build_and_write` writes `data/neuralweb/world_state.json` (`world_state.py:4978-5009`).

`engine/neuralweb/mastermind_context.py:350-364` copies that `risk_envelope` key into the market lobe. `build_and_write` (`:3002-3055`) writes byte-identical copies:

- `data/neuralweb/mastermind_context.json`
- `site/neuralwebdata/mastermind_context.json`

The writer comment calls the site file a public copy (`:3011-3012`). `config/site_access.yml` has no `neuralwebdata` entry, so the same default-deny asset rule applies. This census did not HTTP-fetch either URL.

`read_preferred_context` (`rotation_risk_context.py:352-370`) can prefer `site/live/risk_envelope.json`. World state does not call it. The bridge Mastermind reads is the settled compact, not the live wrapper.

`compact_context` (`rotation_risk_context.py:31-37`, `:67-123`) keeps schema, clocks, measured state, hazard, policy summary, authority, coverage, freshness, rotation, confluence, and market transition. It does not recompute a stage.

---

## 1. Where the portfolio book lives, and who writes it

The book catalog is `portfolio/registry.py`. `PORTFOLIOS` starts at `:33`. Storage default `DEFAULT_ID = "flagship"` (`:29`) is not the product default. `DASHBOARD_DEFAULT_ID = "autonomous"` (`:30`).

Active books at this SHA: `autonomous` (US Brain), `china` (CN Brain), `hk` (HK Brain), `self_directed`. Archived: `flagship`, `heavyweight`, `etf` (`portfolio/registry.py:33-145`).

State files:

| Book | State | Canonical writer |
|---|---|---|
| Flagship (legacy storage id) | `data/portfolio/account.json` (cash, positions, NAV), `fills.jsonl`, `nav_history.jsonl` | `portfolio/paper_account.py:5-7`, `:36-37` |
| Every other registry id | `data/portfolios/<id>/account.json` and the same siblings | `portfolio/paper_account.py:_paths` `:164-172`; `registry.data_dir` `:255-274` |
| Open/close ledger | `data/portfolio/positions_ledger.json`, keyed `sleeve:ticker` | `portfolio/position_log.py:1-3`; `update` `:124`, `close_position` `:378` |
| Self-directed | `data/portfolio/self_directed/account.json`, isolated from the managed account | `portfolio/self_directed.py:17-18`; `_save_account` `:82`; `place_order` `:332` |
| Thesis spine (not positions) | `data/brain/theses.jsonl` | `brain/ledger.py:1-6`, `append` `:27` |

The managed-book mutation is `portfolio.paper_account.rebalance` (`:1780-1796`): it validates targets, simulates fills, and updates `account.json` atomically through `_commit_account_and_fills` (`:1270`). Sibling mutators on the same module: `execute_fill` (`:1995`), `queue_orders` (`:2107`), `save_pending_target` (`:2873`), `mark` (`:3120`).

Who calls it:

- Active Brain books go through `bot.settle.execute_or_queue` (`bot/settle.py:1-10`, `:169`). Open market rebalances; closed market queues and books nothing. Callers: `bot/autonomous.py:337`, `bot/china.py:290`, `bot/hk.py:285`. `bot/etf.py:288` uses the same choke point but that book is archived.
- Archived flagship still has a direct `paper_account.rebalance` in `bot/phase2.py:2704`.
- Archived heavyweight calls `paper_account.rebalance` directly (`bot/heavyweight.py:525`).

Sizing is not the book. `portfolio/risk_sizing.py:1-11` reweights inside an already chosen book and "can never RAISE gross". `portfolio/firm_exposure.clamp_book` is the binding cross-book cap, subtract-only, called before commit (`portfolio/firm_exposure.py:1-16`; `bot/autonomous.py:327`). `brain/book_lifecycle.py:1-4` recommends probation or retirement and writes `data/lifecycle/<date>.json`. Its header says kill is never automated.

There is no single object named "envelope" inside the book. Gross caps and allow-adds live on the local macro-risk state (`brain/macro_risk.py:333-347`), not on a stored portfolio envelope.

## 2. What already consumes market-risk or regime state from macro

Production Python at this SHA does not open `site/riskdata/risk_envelope.json`.

```
git grep -n -e 'riskdata/risk_envelope' 98d00027 -- ':!review_evidence' ':!docs' ':!tests'
```

returned no hits. `grey_deer` / `Grey Deer` in `*.py` excluding tests also returned no hits. The string `risk_envelope` in production Python is only:

- `brain/neural_web_context.py`
- `brain/market_view.py` (passes the neural-web fields through)

### The one envelope consumer

`brain/neural_web_context.py:1-5` reads only `vendor/macro/site/neuralwebdata/mastermind_context.json` (`:42-43`). It never imports macro engine modules.

`_qualify_risk_envelope_context` (`:381-539`) requires `schema == "mastermind.risk_envelope/v1"` (`:333`, `:401-402`), a fresh `source_session` matching the market lobe as-of, a known revision, usable data state, all four authority flags `False`, and `display_only is True` on hazard and policy (`:401-424`). It whitelists fields (`:335-340`, `:464`) and returns `(None, status)` on any failure. The docstring says no scores, votes, posture, caps, or confidence are derived (`:388-389`).

`market_plane()` (`:683-770`) puts that pair on the plane as `risk_envelope` and `risk_envelope_status`. `seat_prompt_block` (`:779-811`) turns the same qualified object into prompt lines that say the context is descriptive and has no sizing authority (`:549-558`).

`brain/market_view.py:_adapt_neural_web` is defined at `:1009`. Its docstring at `:1012` says it always passes `validated=False`; the return sets `validated=False` at `:1053`; the envelope passthrough is `:1061`. The module header says the view sizes nothing (`brain/market_view.py:14-20`). Flagship's phase2 starts that publish at the E0.5 comment `bot/phase2.py:1028`, imports the module at `:1034`, and logs it as perception at `:1065`, before the book is touched.

So the envelope already arrives, already qualified, already marked advisory. Nothing in that path calls `rebalance`, `execute_or_queue`, or `apply_risk_state`.

### How the file gets into the vendor tree

`vendor/macro` at this SHA is a symlink blob whose target is `macro_src` (`git ls-tree` mode `120000`; `bot/__init__.py:3-7`). It is not a gitlink. `data_layer/macro_refresh.py:117` points `_SRC` at `vendor/macro_src`, a gitignored sparse checkout. The sparse set (`:130-132`) includes `site` (so `site/riskdata/` and `site/neuralwebdata/` come along if they are on `origin/main`) plus `data/regime` and `data/risk_radar`. It does not include `data/risk_envelope/` or `site/live/`. CI checks out a pinned macro revision `256c757b3c4f0ec759571c29a30a71387d0a18f8` with sparse paths `engine` and `lib` only (`.github/workflows/ci.yml:29-52`), so CI does not materialize the envelope at all.

### Local market-risk origination, still separate from the envelope

`brain/macro_risk.py:1-29` fuses volatility, credit/USD, liquidity, crowding, and dealer-gamma from the vendored dashboard into `risk_on | caution | risk_off`, with `gross_cap` / `allow_adds` / `apply_risk_state`. It does not read `risk_envelope`. `risk_state()` (`:633-655`) is documented as pure, and its default dwell path still calls `_save_state_machine` (`:690-691`), writing `data/macro_risk/state_machine.json` (`:40`, `:50`). `run()` (`:921-928`) also writes `data/macro_risk/<asof>/`.

Those teeth change a book only when `MASTERMIND_MACRO_RISK` is on. The flagship path is `bot/phase2.py:783-790` and `:2340-2347` (`apply_risk_state`, then `position_log.close_position`). Default is off, so the live flagship build stays byte-identical. Flagship is archived. This census did not find `apply_risk_state` on `bot/autonomous.py`, `bot/china.py`, or `bot/hk.py`.

`bot/derisk.py:213-227` calls `macro_risk.risk_state` inside the fast tripwire. Arming is `MASTERMIND_FAST_DERISK` (`config/authority_map.yml:238-245`). That path can cut gross. It is local fusion, not the Grey Deer envelope.

### Regime and risk-radar reads (not the envelope)

These read macro regime / radar artifacts, not `mastermind.risk_envelope/v1`:

- `brain/market_view.py:46-47`, `:293-322`, `:1528` — `risk_radar` plane from the regime file, validated because a forward log exists.
- `brain/regime_frame.py:102-106`, `:573-604` — `vendor/macro/data/risk_radar/forward_log.jsonl`.
- `brain/anticipation.py:549-568` — drawdown-scare leg off `risk_radar`.
- `portfolio/context_gate.py:108-117` and `portfolio/held_risk.py:1338-1373` — `risk_radar.state` on the regime file.
- `brain/decision_context.py:30`, `:54` — names `risk_radar` as a probability plane.

`portfolio/held_risk.py:56` also points at `vendor/macro_src`. Held-risk is a reader of regime state for held-name alerts. This census did not trace every held-risk caller into `rebalance`.

Design-only mentions of Grey Deer and `site/riskdata/risk_envelope.json` sit in `docs/superpowers/specs/2026-09-15-mastermind-portfolio-v3-risk-first-autonomous-manager-design.md` and `docs/superpowers/plans/2026-09-15-mastermind-portfolio-v3-s0-decision-snapshot.md`. They are not an implementation.

## 3. Existing shadow / sidecar / dry-run patterns

The closest "compute a diff, write a receipt, do not change the book" pattern is the DecisionPacket gate.

`control_plane/packet_gate.py:1-19`. Mode comes from `MASTERMIND_PACKET_GATE`, default `shadow` (`:68-81`). In shadow, `process()` builds, validates, and appends a run event, and returns `ok=True` even when the packet is invalid (`:229-238`: "the book ALWAYS proceeds unchanged"). Enforce is the only mode that returns `ok=False` (`:240-247`). Active books call it before pricing, for example `bot/autonomous.py:217-253`. A rejection there sets `decided = False`, which skips the trade. Shadow never takes that branch.

A second, narrower pattern is desk quorum. `brain/committee.py:46-54`: mode `shadow` runs the technician seat and logs the verdict, and does not change the book. `desk_quorum_effect` returns the input action unchanged in shadow (`:207-221`). The log line is `data/pipeline/ledger.jsonl` via `bot/phase2.py:746-750`. Default mode is `off` (`brain/committee.py:59-60`). This lives on the archived flagship loop.

`brain/posture_decider.py:6-11` publishes `data/posture/latest.json` on every build, and the header says that with the flag off no sizing path reads it. `build()` (`:715-736`) writes that artifact and a dated copy. Phase2 only consults it when `posture_flag()` is true (`bot/phase2.py:1201-1207`). The command packet forbids arming this module as the GD-9A shortcut (`GREY_DEER_FABLE_EXECUTION_COMMAND_PACKET_2026-08-19.md:1024-1028`).

`portfolio/shadow_books.py:1-21` is not a zero-mutation receipt. It runs counterfactual paper books that write their own `data/shadow/books/<id>/` accounts. They do not write the production singletons. They do mutate a book.

`scripts/export_macro_snapshot.py` in Mastermind has a `--no-push` dry run (`:14-16` from the earlier grep). That is a macro-snapshot export switch, not a portfolio diff.

Not found: a function whose name or docstring is a Grey Deer envelope-versus-local-risk diff receipt. Patterns searched in production Python: `risk_envelope` (only the two files above), `grey_deer`, `site/riskdata/risk_envelope`, `diff_receipt`, `shadow_receipt`.

## 4. Where a diff receipt would naturally be stored, and who owns it

| Path | Writer | What it already stores | Owner in this tree |
|---|---|---|---|
| `data/governance/run_events.jsonl` | `control_plane/run_events.py:3`, `append` `:80-85`, path `:56-61` | Packet accepted/rejected, startup, lifecycle | `control_plane` (module docstring `:1-5`). Executive worker policy lives in the same authority file. |
| `data/governance/packet_rejections.jsonl` | `control_plane/decision_packet.py:469-475` | Invalid DecisionPackets, including shadow-mode invalids | `control_plane` |
| `data/pipeline/ledger.jsonl` | `bot/phase2.py:746-750` | Desk-quorum observability rows | Flagship phase2 |
| `data/posture/latest.json` | `brain/posture_decider.py:106-107`, `:735` | Shadow posture object | Posture decider. Arming it is an authority-map flag. |
| `data/shadow/books/<id>/` | `portfolio/shadow_books.py:17-21` | Isolated counterfactual paper accounts | Shadow-book runner. These are books, not receipts. |
| `data/macro_risk/<asof>/` | `brain/macro_risk.py:_write_artifacts` `:891` | Local fused state the shadow comparison would quote | Macro-risk seat |

`config/authority_map.yml:1-11` is the conformance table for flags and for a fixed set of governance `event_type`s. `tests/test_governance_ledger.py:774-792` checks that fixed set (`flag_changed`, `doctrine_changed`, `experiment_matured`, `book_lifecycle_recommendation`, `posture_governor_armed`, `posture_governor_disarmed`, `operator_action`). It does not scan every `kind` passed to `run_events.append`. A new observational `kind` can be appended without editing the map. Promoting that kind into the governance `events:` table would mean editing `config/authority_map.yml`.

The command packet says Grey Deer portfolio waves must not edit Executive OS authority maps (`GREY_DEER_FABLE_EXECUTION_COMMAND_PACKET_2026-08-19.md:116`). No `CODEOWNERS` file is in the Mastermind tree at this SHA (`git ls-tree --name-only` of the root, and a `*CODEOWNERS*` grep, both empty).

A receipt that only records bundle id, local state, differences, and hypothetical gross/no-add effects fits `run_events.append` or a new file under `data/shadow/` that is not an account. It does not fit `packet_rejections.jsonl` (that file is for invalid decision packets) and it does not fit `data/posture/` (that artifact is the forbidden shortcut).

## 5. Authority and approval gates on book mutation

One line each, from this SHA.

1. Executive workers cannot mutate paper state. `config/authority_map.yml:135-140` denies `CAPITAL_EXECUTION` and `PAPER_STATE_MUTATION`. `control_plane/executive_authority.py:29-34` repeats those denies as required and fail-closed (`:1-8`).
2. Serve-only mode refuses operator runs. `app/auth.py:208-210`: "True when MASTERMIND_SERVE_ONLY=1 — read-only mirror mode." `app/main.py:297` says operator paths return 403.
3. Packet gate, default shadow. `config/authority_map.yml:513-524`: flipping shadow to enforce "MUST be recorded in the governance ledger BEFORE the flag is changed."
4. Local macro-risk teeth, default off. `bot/phase2.py:785-790`: "Default OFF — so the live build is BYTE-IDENTICAL until the user opts in."
5. Fast de-risk, default off. `config/authority_map.yml:242-245`: "When armed, a confirmed macro RISK-OFF/gamma-flip tripwire auto-cuts flagship gross."
6. Posture decider, default off. `brain/posture_decider.py:10-11`: "Flag OFF (default / shadow): the artifact publishes, NO sizing path reads it."
7. Desk quorum, default off. `brain/committee.py:52-53`: shadow logs the verdict and does "NOT change the book."
8. Envelope authority cannot size or execute. `engine/risk_envelope.py:611-616`: every boolean is hard-false "by construction."
9. Rebalance itself refuses a bad target before it writes. `portfolio/paper_account.py:1793-1794`: "malformed or over-gross targets fail closed before account mutation."
10. Firm clamp is subtract-only. `portfolio/firm_exposure.py:15`: "clamps a book's target DOWN toward cash; it never raises it."
11. GD-10 is not this card. Cutover needs Sol acceptance and Chairman approval (`GREY_DEER_FABLE_EXECUTION_COMMAND_PACKET_2026-08-19.md:1043-1050`). Absent or stale envelope must not loosen risk (`:1054`).

`MASTERMIND_VPS_AUTHORITATIVE` (`config/authority_map.yml:222-235`) is the writer-instance gate, separate from serve-only. The authoritative box runs with serve-only off (`app/auth.py:213-220`).

## 6. Candidate seams

Three attach points. None of them is implemented. Each stays off `rebalance` / `execute_or_queue` / `apply_risk_state` / `derisk`.

### Seam A — read the settled site file beside the daily perception step

File: `bot/daily.py:62-70`. The preceding step calls `macro_refresh.refresh_and_check()` (`:57-58`). The perception block then materializes read-only artifacts "BEFORE the book build" and "they change ZERO trading behavior" (`:65`).

Read-only calls:

- Parse `vendor/macro/site/riskdata/risk_envelope.json` (the settled contract the sparse `site` cone already pulls). Do not import `engine.risk_envelope`.
- Read the last written local state under `data/macro_risk/` (or call `macro_risk.risk_state` with an injected no-op `state_saver` and `dwell=False`). The default `risk_state()` persists dwell (`brain/macro_risk.py:690-691`).
- Do not call `macro_risk.run`, `apply_risk_state`, or `bot.derisk`.

Receipt: one append-only object via `control_plane.run_events.append` (`control_plane/run_events.py:80`), `kind` naming the shadow comparison, payload carrying bundle id, local `state` / `gross_cap` / `allow_adds`, field differences, and hypothetical gross/no-add effects. Or a sibling file under `data/shadow/` that is not an account.

Why it cannot mutate the book: this step returns a status dict into `out` and does not call `paper_account`. The book writers are later, in `execute_or_queue` and `rebalance`. A function that only parses JSON and appends a ledger line has no handle on `account.json`.

This is the seam that matches "exact served/vendored bundle" (`command packet:1011`). The neural-web lobe is a compact of the settled file, not the file itself.

### Seam B — diff against the envelope Mastermind already qualifies

File: `brain/neural_web_context.py:market_plane` (`:683-714`).

Read-only call: `market_plane()` (or `_risk_envelope_context` on the market lobe). It returns a dict. Pair it with a read of the already-written `data/macro_risk` artifact. Write the same receipt as seam A.

Why it cannot mutate the book: the qualifier drops any envelope whose authority flags are not all false (`:416-420`), derives no cap (`:388-389`), and `market_view._adapt_neural_web` forces `validated=False` (`brain/market_view.py:1053`). Prompt text from `seat_prompt_block` is descriptive (`:557`). None of these functions take a portfolio id or call `paper_account`.

Limitation: the object inside `mastermind_context.json` is `rotation_risk_context.compact_context` of the settled artifact, copied by `mastermind_context._summarize_market` (`engine/neuralweb/mastermind_context.py:359-364`). It is not the live wrapper, and it is not a byte-identical copy of `site/riskdata/risk_envelope.json`. GD-9A's "exact served bundle" is seam A. Seam B is the existing qualified projection, useful as the parity baseline of what the bot already sees.

### Seam C — do not attach inside the packet gate; copy its shadow shape

`control_plane.packet_gate.process` (`:115-138`) already sits on the active-book submission boundary (`bot/autonomous.py:225-247`, and the china/hk/etf/heavyweight twins). In shadow it cannot reject. In enforce, `ok=False` makes the caller skip the trade (`bot/autonomous.py:247-253`).

A GD-9A diff does not belong inside `process()`. That function's enforce mode is a book gate, and its receipt is a decision-packet acceptance, not a market-truth comparison. The adapter should copy the shadow contract (always proceed, ledger the difference) from `packet_gate.py:15-16` and `:229-238`, and stay a sibling of perception, not a new clause in the packet.

Seam explicitly rejected by the card: `brain/posture_decider.build` (`command packet:1026`). It already writes a shadow artifact, and arming `MASTERMIND_POSTURE_DECIDER` is what makes phase2 read it (`bot/phase2.py:1207`).

## 7. Risks and unknowns

- The live file and the settled file are different shapes. Mastermind's qualifier rejects `revision == "live_provisional"` when `stale_after` is missing (`brain/neural_web_context.py:438-439`). The live builder publishes `stale_after=None` and puts expiry in `stale_after_min` plus `clocks` (`scripts/build_live_risk_envelope.py:692`, `:746-750`). Feeding the live wrapper through `_qualify_risk_envelope_context` will currently drop it as `missing_live_expiry`. World state never sends that wrapper. A shadow adapter that wants the live plane has to qualify `clocks` / `precedence` / `live_active` itself, or call macro's `qualify_live_context` (`rotation_risk_context.py:236`), which means importing macro engine code. `neural_web_context.py:5` says the bridge never does that. GD-9A says no reaching into macro internals (`command packet:1011`).
- `risk_state()` writes dwell state unless the saver is injected (`brain/macro_risk.py:690-691`). A "read" of the local stack can move later caps. The shadow comparison should read the last artifact or pass a no-op saver.
- `MASTERMIND_NW_DECISION` is documented as default `off` in `config/authority_map.yml:305-310` and in the `nw_decision_mode` docstring (`brain/neural_web_context.py:122`). The code default when the variable is absent is `_DECISION_MODE_DEFAULT = "shrink"` (`:87`, returned at `:137-139`). That ladder can shrink entries. It is a separate chokepoint from the envelope qualifier, and the authority-map note differs from the runtime default. Prompt injection of the qualified envelope is on unless `MASTERMIND_NW_CONTEXT` is set false: `nw_prompts_enabled` (`:103`) has a docstring that still says default OFF (`:104`), while the return at `:114` is `os.environ.get("MASTERMIND_NW_CONTEXT", "1")` and the comment at `:110-113` records that the default was flipped on. That injection is prompt text. An LLM that sees the lines can still propose a different book.
- Active books (`autonomous`, `china`, `hk`) do not call `apply_risk_state`. The local teeth this card would shadow are on archived flagship (`bot/phase2.py`) and on the optional fast derisk tripwire (`bot/derisk.py`). A shadow diff against flagship's fused state may not be the state the live US book trades on. What the live brains do consume is the neural-web plane and, for autonomous, a prompt slice of `macro_risk` (`bot/autonomous.py:1082`). This census did not follow that prompt into the model call.
- `portfolio/held_risk.py` and `portfolio/context_gate.py` still read `risk_radar` from regime JSON. If any of those results reach a target weight, a shadow adapter that only diffs `macro_risk.risk_state` will miss them. Caller trace into `rebalance` was not finished.
- Vendored bytes depend on `macro_refresh`, which pulls `origin/main` and can sync an R2 stock plane (`data_layer/macro_refresh.py:1-10`, `:140-145`). The shadow adapter must not invoke that refresh. CI's macro pin (`256c757b…`) is not current macro `eb7c4d67…`, and CI does not check out `site/`.
- `bot/__init__.py:19-22` reads a gitignored `.env` on import. This census did not import `bot` and did not open any env or credential file. An adapter test that imports `bot` would.
- No `CODEOWNERS`. Ownership of `data/governance/` is by module (`control_plane`), not by a named person in this tree.
- GD-9A and GD-10 are still `todo` and the workstream next-action says they are uncommissioned (`WS-GREY-DEER-RISK-INTELLIGENCE.md:328-335`, `:398`). This census is not a commission.
- Portfolio v3 design docs describe a future Grey Deer ceiling and `UNKNOWN_PROTECTIVE`. Those behaviors are not in `brain/` or `portfolio/` Python at this SHA.

## Searches that came back empty

At Mastermind `98d00027cf5e228be9bd584684ad0284769cdf74`:

- `git grep grey_deer|Grey Deer` in `*.py` excluding tests: no hits.
- `git grep riskdata/risk_envelope` outside `docs/`, `tests/`, `review_evidence`: no hits.
- `git grep risk_envelope` in production `*.py`: only `brain/neural_web_context.py` and `brain/market_view.py`.
- `packet_gate` in `bot/phase2.py`: no hits. Flagship does not use the packet gate.
- Root `CODEOWNERS`: not in the tree.
