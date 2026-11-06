# Scoped Census and Audit Ledger — Grey Deer × Leadership Rotation

**As-of:** 2026-10-31 America/Chicago. **Scope:** two owning workstreams and execution dependencies across Macro, Mastermind and Terminal; 37 named PRs queried and retained with exact heads in `CENSUS_SNAPSHOT.json`. Not a census of every PR in the entire Mastermind company. **Method:** current GitHub commit/file/PR/CI/job-log reads, protected procedure and AgentOS, relevant latest handoffs, prior source-attested Supabase schema, live-host configuration *metadata only*, Slack exact review threads, Linear projection, and primary research. No production mutation, test replay, user email, transaction, mail send, or trades.

## Evidence grading key

- **D / direct, current tracked source or hosted log:** inspected exact repository artifact, PR metadata, or existing GitHub job on Oct31. This is *not* authentication to the live website or proof of a customer delivery.
- **R / dated first-party prior read-only audit:** linked source, live schema read, proposed branch review, or operator report from prior day. Its observation time is retained; a fresh DB/host/source check is still owed before action.
- **I / inference from source mechanisms:** plausible cause requiring original workflow/release trace, not a witnessed historical cause.
- **P / design proposal:** can be adopted, rejected or revised by Fable under original ownership.
- **U / unverified:** not observed from available session/surface; cannot be promoted from absence of a record.

## A. Current exact source clocks — highest-impact contradiction

| Evidence | Source / identity | Verified value | Consequence |
|---|---|---|---|
| D | [Macro public Risk Envelope](https://github.com/mastermindx-market-intelligence/macro/blob/d533508a4e66e4abece8cac91466660b679bff9e/site/riskdata/risk_envelope.json), blob `ceb29e57f0b02f412e21d3021f23aa4176122127` | session `2026-10-30`, produced `2026-10-31T00:06:45Z`, `PARTIAL`, measured `MIXED` 47, hazard `FRAGILE`, `revision=settled`, `bundle_id=e1c5acd101f263a0` | Latest tracked public condition is **not** Oct29 DEGRADED, but still not fully fresh or settlement-attested |
| D | Same payload `freshness.per_source` | leadership Oct30 `FRESH/BROKEN`; Radar Oct30 `FRESH/caution`; market state Oct30 `FRESH/MIXED`; **rotation Oct20 `STALE`** | A current headline can contain a ten-day-old subcomponent. A fresh composite cannot make every input fresh |
| D | Same payload `repair_state` and `policy_summary` | Repair `null`; 0 active policies, `NORMAL`; no permission to rank/size/execute | Repair not established; zero active protective policy is not an all-clear |
| D | [Macro durable Risk Envelope](https://github.com/mastermindx-market-intelligence/macro/blob/d533508a4e66e4abece8cac91466660b679bff9e/data/risk_envelope/latest.json), blob `2e5a643cca555db7b76c976cde8cf067fa4493d7` | session `2026-10-20`, `FRESH/FRAGILE`, bundle `9e78b77361860f3f` | The two copies are not a single currently qualified settlement |
| D | [#10221 source](https://github.com/mastermindx-market-intelligence/macro/pull/10221) | Nonblocking pair check compares worktree, staged index, committed Git and source sessions but `settlement_proven=false` | A passing comparison could prove bytes matching, not actual capture entitlement |
| I, code-supported | [Express](https://github.com/mastermindx-market-intelligence/macro/blob/d533508a4e66e4abece8cac91466660b679bff9e/.github/workflows/engine-render.yml) and [closing-bell](https://github.com/mastermindx-market-intelligence/macro/blob/d533508a4e66e4abece8cac91466660b679bff9e/.github/workflows/closing-bell.yml) source | Site-only staging vs data/ discard around a composer that writes both; public may advance alone | Structural split-publish possibility **proven from source**, exclusive historical cause **unproven** |
| I, code-supported | [Settled composer](https://github.com/mastermindx-market-intelligence/macro/blob/d533508a4e66e4abece8cac91466660b679bff9e/scripts/build_risk_envelope.py#L728-L820), [live overlay](https://github.com/mastermindx-market-intelligence/macro/blob/d533508a4e66e4abece8cac91466660b679bff9e/scripts/build_live_risk_envelope.py#L632-L706) | Marker `revision=settled` not independently qualified; same-session provisional later may be suppressed | Require falsifier for fake same-day settled capture; do not blindly copy public to durable |

**Important correction to old plan:** on Oct29 the public envelope was DEGRADED with null hazard and sources Oct23/Oct20. The Oct31 main changed it to PARTIAL Oct30, with leadership now current, rotation still stale. Both statements can be true *at their respective source snapshots*.

## B. Natural production-automation evidence; what did and did not happen

Direct original [GitHub daily run 40803269874](https://github.com/mastermindx-market-intelligence/macro/actions/runs/40803269874) decoded at job level without rerunning anything:

| Job/time (UTC) | Observed receipt | Boundary |
|---|---|---|
| `collect_tail` job 123688869633, Oct29 20:20:23 | `GH001`: `data/qledger/claims.jsonl` **146.50 MB**, over GitHub 100MB single-file limit; automatic retry stopped | Real publication push failure, not an algorithm judgment |
| `engine` job 123688873047, Oct29 23:58 and Oct30 00:17 | Repeated `GH001` rejection on the same oversized claims file; `engine outputs: GH001 large-file rejection; automatic retry stopped` | Root stream's accepted push failed even though some components computed |
| Same engine, Oct29 20:34/22:40 | `engine.leadership_crack` wrote `data/leadership_crack/latest.json` and forward log | Refutes simplistic “leadership builder never ran”; does not prove that computed result was safely published |
| Same engine, Oct30 00:18 | R2 `massive_stock_day` last published **65.3 h** before (26 h limit), content Oct23 (7 days vs 6-day limit); additional episode/campaign/candidate failure logged | Separate R2 data-plane problems. These are **Oct29/30 run-local metrics**, not current R2 status on Oct31 |
| Earlier original job receipts in [P1 evidence](https://github.com/mastermindx-market-intelligence/macro/blob/ff4b0aab3f9c2e0130f4a98d20502dde257ee575/research/grey_deer/evidence/EW_P1_SOURCE_CLOCK_DIVERGENCE_2026-10-30.md) | GH001 tail recurrences Oct21/23/24/26/27/30, direct engine Oct23/24, some green et_gate-only slots skip engine and collect | Pipeline's “green daily” alone does not establish a natural qualified source advance |

**Do not redo** merged [#9556](https://github.com/mastermindx-market-intelligence/macro/pull/9556) collection-only snap/park/restore. That protects one staging lane, not broad engine/tail. **Do not** stage all `data/`, truncate ledger, reset uncommitted original claims, or call a manual replay natural. Original [#10079](https://github.com/mastermindx-market-intelligence/macro/pull/10079) source-only accepted-prefix guards passed an independent nonauthor review; the missing complete original source-generation proof remains an actual blocker. Its prior service-filter-denied native flags/swap experiment is not a permitted retry target. No material live effect was launched by this audit.

## C. Code and release custody: exact important PRs

All statuses represent Oct31 reads; absence of a review does not mean a live writer is absent.

| Owner / PR | Head and exact gate | Current capability and disposition |
|---|---|---|
| [Macro #10219](https://github.com/mastermindx-market-intelligence/macro/pull/10219) | Draft `ff4b0aab3f9c2e0130f4a98d20502dde257ee575`; [CI 41145833169](https://github.com/mastermindx-market-intelligence/macro/actions/runs/41145833169) PASS and [fences 41145833074](https://github.com/mastermindx-market-intelligence/macro/actions/runs/41145833074) PASS; no formal PR reviews observed | Governing **candidate** task-tree and research packet; independent Oct30 architecture review REQUEST AMENDMENTS, later plan corrected; new nonauthor assessment still needed |
| [Macro #10221](https://github.com/mastermindx-market-intelligence/macro/pull/10221) | Draft `3599ba678f434a4e26b512cb8fc71bd78635bb2f`; [CI 41145378963](https://github.com/mastermindx-market-intelligence/macro/actions/runs/41145378963) FAIL, fences PASS | Nonblocking diagnostic only. Hosted contract-delta says new `tests/test_risk_envelope_pair.py` suite belongs to no run step/curated registry; ci-pack-1 `house-law-registry-code` fails; gate fails; Terra independent review FIX_REQUIRED: use pushed immutable 40-hex SHA, not symbolic HEAD, plus test coverage |
| [Macro #10104](https://github.com/mastermindx-market-intelligence/macro/pull/10104) | Draft `a324b7fc1f15e18393482ab18c4d97e12ebcbabe`; dirty/mergeable false, existing CI-authority/main pass but other target authority intentionally fails, **no** ordinary exact-head PR `ci`/`fences` observed | Canonical observation continuity candidate; original branch must preserve curated `.github/ci/legacy-jobs.yml` and `app/deploy/update.sh` changes; do not force automatic conflict resolution |
| [Macro #10079](https://github.com/mastermindx-market-intelligence/macro/pull/10079) | Draft `291d3ded65cbee29e116774dc3db2e4becf96ea9`; fences [41147368589](https://github.com/mastermindx-market-intelligence/macro/actions/runs/41147368589) PASS, CI [41147368679](https://github.com/mastermindx-market-intelligence/macro/actions/runs/41147368679) PASS; independent nonauthor Terra PASS/STOP source-only | Accepted-prefix-only fail-closed guard, complete original generation **NOT_PROVEN**, not a full QLedger migration/publication recovery |
| [Macro #8132](https://github.com/mastermindx-market-intelligence/macro/pull/8132) | Draft `639aaed06ce7754110d3bd6e94a0b704bb6c7760`; [CI](https://github.com/mastermindx-market-intelligence/macro/actions/runs/36377868822) FAIL, formal CHANGES_REQUESTED | Severe banner/projection may falsely clear warning on degraded calm, infer confirmed repair, emit unqualified probabilities. Do not release as-is |
| [Macro #9957](https://github.com/mastermindx-market-intelligence/macro/pull/9957) | Draft `26f60b69a5c929f2a5a4316add623d01ccbc7eac`; CI/fences PASS, formal review missing | Grey Deer reason publication and original refusal hold, not a deliverability shortcut |
| [Macro #10103](https://github.com/mastermindx-market-intelligence/macro/pull/10103) | Merged Oct23, head `933498fc5fbbf523674c9c1fcb18649228ad4a57` | Existing **descriptive** early-context renderer; usable source fallback if #10104 blocked, not historical Oct6 delivery |
| [Macro #9932](https://github.com/mastermindx-market-intelligence/macro/pull/9932) | Merged Oct21, head `5cdc2960bc32dc43a1ca390f9a3a32c19170c981` | MAS-258 accepted evidence landing; do not reimplement |
| [Macro #10218](https://github.com/mastermindx-market-intelligence/macro/pull/10218) | Draft `d8332c7928a257ca527439ec62beae99ea37f661` | Retained Sep/Oct pre-event forensics, no production-user or notification receipt |
| [Macro #10212/#10213/#10227](https://github.com/mastermindx-market-intelligence/macro/pull/10212) | Separate current Draft breadth and factor carriers | Adjacent source/provenance; owner paths overlap conceptually, not permission to absorb or duplicate their engine/UX |
| [Mastermind #1660/#1667](https://github.com/mastermindx-market-intelligence/Mastermind/pull/1667) | Both merged Oct21; captured risk publication/decision custody in source | Historical live stale Market View Aug7 falsely fresh Oct21; production HOLD and current common risk/observation capture absent, so merged ≠ served |
| [Mastermind #1567](https://github.com/mastermindx-market-intelligence/Mastermind/pull/1567) | Merged Oct17 | Reject future-date source; reuse existing source law |
| [Mastermind #1194](https://github.com/mastermindx-market-intelligence/Mastermind/pull/1194) | Draft `3f471167f31950f652d308a3342419024f0d113d` | Tie-aware AUC science continuation, no retune/promotion |
| [Terminal #1103/#1132](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1132) | Both merged Oct21/23 respectively | Real Sector/Options evidence and Catalyst comparison route; Oct23 authenticated proof was EOD fallback/absence, **not** natural high-frequency publication |
| [Terminal #1000/#1003](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1000) | Both merged Oct14 | Measured history route/invalid closed_recent handling, preserve |
| [Terminal #1019](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1019) | Open non-Draft, `7de7725f8421d7c0a4dbd323aa7e9734278325db` | Owns foreign-market envelope qualification (US only); do not duplicate or infer current release |
| [Terminal #881](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/881) | Closed unmerged; replaced by #1000 | Historical only; do not revive |

Other relevant PRs in `CENSUS_SNAPSHOT.json`: Macro #6989 all-region Radar, #9513 global warning client, #9440 suppressed ledger, #9428 deterioration preservation, #9035 forensic, #9917 Sector Central, #8721 pullback depth, #9548 VIX, #9980 six-document reasons hold, #7480 moved risk band into Radar, #7595 sector shell, #7022 Market Changes Desk, #7870 semiconductor theme owner, Mastermind #1887 Fabric launcher transport; their source writers remain with original programmes. The 37-item list is a **bounded dependency map**. Do not treat uninspected CI on each peripheral PR as passed or failed.

## D. Source/consumer gap map

| Stage | Current tracked implementation/provenance | Ownership / fault line |
|---|---|---|
| Market/regime/leadership | `data/regime/latest.json`, `data/leadership_crack/latest.json`, `data/risk_radar/us/latest.json`; builders in `engine/` | Native risk and leadership producers; actual original source clock/rights required |
| Sector events and observations | [`scripts/build_rotation_events.py`](https://github.com/mastermindx-market-intelligence/macro/blob/a324b7fc1f15e18393482ab18c4d97e12ebcbabe/scripts/build_rotation_events.py#L210-L212), `engine/rotation_events.py` | Public rotation JSON written before `rotobs_` recording; the ID/history projected to users is **not proven** |
| Grey Deer derived readout | `engine/risk_envelope.py`, `scripts/build_risk_envelope.py`, `scripts/build_live_risk_envelope.py` | Sole composer; not a new model or authority; split capture/settlement |
| Publishing | `scripts/ci/daily_engine_commit_outputs.sh`, `.github/workflows/daily.yml`, `engine-render.yml`, `closing-bell.yml` | Original GitHub owner, QLedger oversized stage, exact staged/push SHA; never stage all data |
| Macro experience | `templates/_risk_envelope_band.html.j2`, `_risk_envelope_band.css.j2`, `rotation_events.js`, `theme.css` | Risk Radar inset, Sector Central existing movement and evidence, no new global dashboard |
| Notifications | `lib/user_prefs.py`, `app/account_prefs.py`, `scripts/deploy/0007_support_email.sql`, `engine/alert_delivery_drain.py`, `scripts/drain_alert_outbox.py`, `app/mailer.py` | Auth vs authoritative consent, global unique `fire_event_id`, actual drain enablement and SMTP uncertainty |
| Terminal | `terminal/app/api/sector-intelligence/route.ts`, `marketRisk.ts`, Sector product | Current BFF handles both endpoints and hashes individually; common source/capture not proven |
| Mastermind | `brain/perception_publication.py`, `brain/market_view.py`, `brain/decision_context.py` | Four captured inputs only, excludes risk envelope/rotobs, original #1667 production gate |
| Science | `research/DEFENSIVE_ROTATION.md`, `research/LEADERSHIP_ROTATION_* `, `research/grey_deer/`, #1194 | Frozen failures, issued-vs-graded maturity, forward study target/membership/clock |

### Current Supabase and notification seam — R, not independently re-read today

The [Oct30 live schema census](https://github.com/mastermindx-market-intelligence/macro/blob/ff4b0aab3f9c2e0130f4a98d20502dde257ee575/research/grey_deer/evidence/EW_P2_LIVE_SUPABASE_SCHEMA_2026-10-30.md) reports **MarketIntelligence PostgreSQL17**, `public.email_prefs` columns `user_id, lang, marketing_opt_out, updated_at`, no trusted rotation family enable/revision and no `pg_policies` registered; `alert_outbox` one unique index on **single** `fire_event_id` (not user+fire), with service-role write and authenticated owner SELECT. Zero rows observed in prefs and outbox; two other `alert_runs` lanes 4032 successes over14days each, none fired, **no** `macro_delivery_drain` run observed in all-time grouping. Source `scripts/drain_alert_outbox.py` forces dry-run unless `ALERT_DRAIN_ENABLE=1`. A configured systemd timer file is not installed/enabled/observed host state. The old host SSH safety failure is not authorization to switch carriers and test mail. Recheck grants/service role and the existing schema migration owner's authority before DDL.

The GET→full Admin PUT code in `lib/user_prefs.py` can resurrect stale `alert_email_optin` after a simultaneous opt-out. A mere second pre-send GET fails linearizable revocation semantics. Strong privacy/source review required; no production send or user-record reading by this audit.

## E. Scientific evidence and counterevidence

- [Frozen `research/DEFENSIVE_ROTATION.md`](https://github.com/mastermindx-market-intelligence/macro/blob/d8332c7928a257ca527439ec62beae99ea37f661/research/DEFENSIVE_ROTATION.md), blob `e0668e5a6c24c91f1d10d4762f7a9687532668f9`: 39 OOS triggers, 80% false alarms for primary event, lift +0.062 with 95% block bootstrap interval [-0.0482,0.1994]; **six-part combined gate fails**, 2 components passed and 4 failed; six variants also failed combined gate. Historical OOS result is *not* universal impossibility, inverse edge, or permission to retune.
- [#10218 as-issued retrospective](https://github.com/mastermindx-market-intelligence/macro/pull/10218): Sep30 `risk_state.v1 ELEVATED` and leadership `BROKEN` pre-Oct6 peak, Radar Caution due to broad gate and index context. Hardware reversed BROKEN→INTACT Oct2; retrospectively visible is not an issued notification. Oct8 generated Oct9 XLP/SMH +6.22% two-session relative wealth, XLP/XLK +4.16%; no confirmed event, availability UNKNOWN, 2S/20S conflicts. **Cannot call this a delivered early crash prediction.**
- Existing `risk_state.v1` modern-era 0.68x lift is a negative authority argument, not a sign that inverse is predictively valid. Preserve frozen compatibility only.
- Retained mature Radar **4 same-model issued, 0 graded**. Do not combine prior epochs, and do not call this “zero issued.”
- Existing Radar promotion-review eligibility in #10219: at least252 issued spanning>=300 days; each H5/H10/H21 >=200 graded,20 events,50 non-events,5 overlap-aware clusters; paired Brier improvement upper90% moving-block CI below zero, calibration-in-the-large interval includes zero. These are existing procedural bars, not proof of enough power or automatic promotion; science owner may require more.
- A categorical sector watch has no issued probability; use coverage, false alarms, time-in-watch, episode recall, real delivery lead and calibration of comprehension. A separately issued forecast must predict the **registered matching sector event**, compare with same-row conditional/unconditional sector baselines and account for selection, overlapping outcomes, embargo, source availability and cluster count.

Primary research and methodological critique are detailed in `RESEARCH_AND_VALIDATION.md`.

## F. Ownership, runtime and process limitations

- Existing workstreams show Grey Deer owner role `coo-fable`, Rotation `meta-ceo-fable`. These are role fields, **not** proof of a currently running Fable attempt or automatic commission/START.
- Oct31 read-only Executive projection (generated 05:12:24Z): Jobs 25 total (21 complete,1 failed,3 queued,0 running); Attempts 33 (21 complete,1 failed,11 lost); one worker available; session_targets empty; **active_builds/deployment windows ~817h old** and incomplete. Therefore use it for bounded capacity clues, not fresh company truth.
- Oct31 Studio fleet returned eight ready account tunnels but `DEGRADED`, physical fleet unknown and `FLEET_STATUS_FABRIC_LAUNCHER_DRIFT`. M2 Studio Direct `get_config` identified a darwin m2studio container, but physical worker admission, installed host service and target process were not proven by this metadata. This census did not launch a Fabric task.
- Local M2 runtime handoffs directory, Oct31 shallow listing: `LEADERSHIP_CONTINUITY_20261024.md`, `WS-ORCHESTRATOR-PROJECT-CONTINUITY-2026-10-25.md` and unrelated Tiingo/intelligence notes; **no current Grey Deer local record found in that exact directory listing**. This does not establish absence across machines/registries.
- `LEADERSHIP_CONTINUITY_20261024.md` specifies owner role continuity: don't wait for absent historical chats; record takeover after current writer/effect check. No unsafe replay of a refused operation. Use source-linked handoffs and preserve independent nonauthor review/approval boundaries.
- Public GitHub workflow-name route to fetch latest `daily.yml` runs returned connector `INVALID_ARGUMENT`; this audit instead relied on **identified original immutable run/jobs**. It does not claim exhaustive Oct31 natural-run status. Before actual publication repair, obtain exact current source/runner receipts on eligible original carrier.
- Linear `MAS-258` was read as In Progress, high, last updated Oct22; a supplemental `linear_get_agent_context` call failed as tool not found, so no new field notes were created or accepted. No projection write.
- No production browser session, receiver mailbox, live preference/host service state, real model-prompt receipt, Paper editing/screenshot or deliberate end-to-end alert was exercised by this census.

## G. Adversarial counter-narrative

A correctly printed sector relative-strength ratio might mislead users into believing it forecasts a broad crash; overloaded designs can cause needless risk reduction. Current observations can lag actual knowable time, interdependent ETF prices can overstate corroboration, a stale public source may read as fresh because the container build timestamp is current, and a green PR can still be a held branch. The product may be more useful as a truthful *monitor and explanation* than a “warning,” and Fable should be allowed to choose that if comprehension and user decisions support it.

## H. Specific next evidence; no unproductive second census

1. Latest exact open PR heads, ownership/lease/unknown effects, live source session and daily original failure: **only material invalidators**.
2. Original publisher qualified settled-vs-provisional rule; reconcile safe QLedger source-generation limitations.
3. Original #10104 merge conflict actual hunks, CI registry, append/correction identity projection.
4. Reviewed authoritative consent grant/migration, global/category/family revocation race and actual drain unit status; **never use live send as a speculative probe**.
5. Terminal/Mastermind cross-generation consumer/admission and served authenticated receipts.
6. Science prereg and true forward outcomes, rights, availability, target and statistical power.

On completion, amend existing #10219 and WS dated handoff; do not create a second authoritative plan. Preserve this census as a proposal and source-pointer aid.
