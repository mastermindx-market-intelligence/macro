# AI Daily Brief freeze + Capacity Fabric completion — continuation handoff (2026-11-09)

Session: GLM 5.3 principal (T3), worktree `claude/ssd-t3-4f13be30-c4747f2c70fdfd15` at Macro
baseline `9a13c64bf69f782332afa29efb09fe48ee30b857`. Parent: Mastermind#983.
Source handoff: GLM53_VPS_Capacity_Fabric_Execution_Handoff_20261109 (Chairman attachment).

## Proven causal chain — Daily Brief freeze (read-only evidence, no reruns)

1. **Producer stopped being reached, not (only) broken.** `master brain` step
   (`.github/workflows/daily.yml` ~line 3934, step 75 of ~127 in the `engine` job) has NO
   `if:`, so it inherits `success()` and is skipped whenever the engine job fails/cancels
   upstream. Nov 9 real slot (run 42553252794, engine job 129006912060 on runner
   `mac-builder-light`): job CANCELLED externally at 09:57:22Z inside step 47 (215.5 min in;
   job timeout 300 — not the timeout). After the cancel only `if: always()` steps ran
   (proof: OIP-PIT steps executed at 10:12–10:25), steps 51–127 incl. master brain (75) and
   build_aibrief (106) skipped. Concurrency design (`pipeline-daily-3-cron-{schedule}`,
   `cancel-in-progress: false`, per-cron groups) rules out same-slot supersede. Every real
   slot Oct 13 → Nov 9 concluded failure/cancelled; "success" runs are DST-gate no-ops.
2. **Failure masking.** Step wraps `python -m engine.master_brain` in `set +e … exit 0`
   (lines ~3964-3968): producer failure is invisible. `engine/master_brain.py` "NEVER
   raises" (`except Exception` throughout; `run()` returns None on error). Last brief
   commit `6ef6fe67976b` 2026-10-18T07:09:10Z; Oct 19 06:09–06:12Z the step ran "success"
   but wrote nothing new (log evidence: oauth rungs dead, `deepseek served after fallback`
   at 05:25Z; a `degraded_reason: "llm_error"` row present). Renderer
   `scripts/build_aibrief.py::_load_briefs` prefers committed `site/*.json` over
   `data/regime/*` and `main()` returns 0 on any exception (lines 571-573) — the rebuilt
   2026-11-09 page embeds October text with "Updated daily" UI.
3. **Provider ladder state (Oct 19 log, job 117872871101).** Rungs `codex → oauth pool →
   ANTHROPIC_API_KEY → deepseek` (master_brain.py:1636; daily.yml env block exposes
   CLAUDE_CODE_OAUTH_TOKEN_1..7, ANTHROPIC_API_KEY, DEEPSEEK_API_KEY; codex reads the
   runner's ~/.codex login). Oct 19: oauth TOKEN_2/4/7 → 401/403 (expired), TOKEN_3/5/6 →
   429; deepseek served after fallback. Separate real bug: `llm_auth[catalyst_tone]`
   `TypeError: Messages.create() got an unexpected keyword argument 'temperature'` on the
   deepseek lane (llm_auth is Macro#10740 territory — coordinate, don't dual-write).
4. **DST gate false-green.** et_gate keeps only the cron matching the current NY offset;
   off-slot firings skip all 17 downstream jobs yet the run concludes SUCCESS (Nov 9
   42547790647). Run-level monitoring therefore lies. (Designed behavior, daily.yml:91-106.)
5. **Interval gate is NOT the cause**: macro/china interval=1 (gate only applies when
   interval>1; BTC=3). run() persists BOTH data/regime/<out> and site/<out>; the engine
   job's later commit step never ran (cancelled) so nothing landed after Oct 18.
6. Secondary defect (not the brief cause): Nov 9 `government_revenue_projection/refresh`
   failed: `publication frozen: baseline_source_or_owner_not_qualified` (exit 75), job
   129006177716.

## Fix packet P1 (this branch, pending collision check vs #10727/#10740/#7179)

- daily.yml: steps ~3923 (scorer), ~3934 (master brain), ~4444 (build_aibrief):
  `if: always()` + `timeout-minutes` + `continue-on-error: true` — matching the file's own
  hardening precedent (`commit engine outputs` at line ~5154 is already `if: always()` with
  the rationale "a skipped commit = stale live site", and OIP-PIT steps executed after the
  Nov 9 mid-job cancel, proving always() steps run post-cancel on this runner). NOTE:
  `!cancelled()` would NOT run on a cancelled job — rejected. Master brain step exits
  `$rc` (visible red) while continue-on-error keeps the pipeline safe; writes a per-run
  receipt, mirroring the existing OHLC producer-receipt doctrine already in this file.
  File-size law: 484,513 B now, cliff ~512,000 B (tests/test_workflow_file_size.py) —
  keep additions ≲2 KB.
- engine/master_brain.py: run_all writes `data/master_brain/receipt.json`
  {run_id?, attempted_at, per-lens outcome: written|interval_skip|disabled|no_provider|error,
  served_by, state_asof, generated_at}; CLI exits non-zero when a due lens produced no
  fresh brief. (#10727 overlap — coordinate before edit.)
- scripts/build_aibrief.py: choose fresher of site/*.json vs data/regime/*.json by
  generated_at; stale chip ("Stale — last generated <date>") instead of "Updated daily";
  stamp published_at/brief_generated_at; machine-readable site/aibrief_freshness.json;
  ::warning on exception (renderer stays fail-open, truth in receipt+chip).
- scripts/check_nightly_liveness.py: count a night only when the engine JOB concluded
  success (ignore run=false no-ops); trip when brief generated_at older than 2×interval
  while regime state_asof is newer.
- Verification (three clocks): market_state_asof (brief state_asof == latest regime state
  date), brief.generated_at within the real engine job window, page.published_at ≥
  brief.generated_at; receipt per due lens = written; negative test: provider failure ⇒
  receipt degraded/error + stale chip renders + pipeline still commits.

## Live estate truth (worker B, read-only ssh `vps-mmx` = 146.190.142.17)

- VPS `/opt/macro` HEAD = `9a13c64bf69f` (== baseline). macro-api restarted Nov 9 11:29Z.
  VPS AI config today: `DEEPSEEK_API_KEY` (/etc/macro-api.env) + Ollama
  `http://100.80.236.59:11434` model `qwen3.5:9b` (EARNINGS_LLM_*) — NO VPS consumer wired
  to Capacity Fabric yet.
- M2: native fabric router RUNNING — `ops.native_fabric.unified_router.service` at
  127.0.0.1:8313 (upstream 8312), launchd `ai.mastermind.fabric-router` pid 52778.
  Chisel reverse RUNNING: launchd `com.mastermind.executive.fabric-application-tunnel`
  client `R:127.0.0.1:50142:127.0.0.1:4142`; VPS 127.0.0.1:50142 up (chisel pid 278367),
  TCP connects, HTTP 000. **Application gateway listener on M2 4142: ABSENT** — the
  missing link for VPS↔Fabric. Chisel auth ≠ application admission; admission needs
  provider_workloads.v1.json entries + service credential per
  integrations/hermes_application_fabric/ENROLLMENT_CONTRACT.md.
- Runners: mac-builder-3/-4/-5/-light all online now; engine ran on mac-builder-light.
- #2182: OPEN draft b5d7ece3, source push APPLIED, native publication
  UNKNOWN/NO_RETAINED_PUBLICATION_RECEIPT/retry_allowed=false, last touched Nov 9 12:41Z
  (mastermidx4). #2367: OPEN head e466a13c, auto-merge ARMED, Nov 9 12:48Z release-lead
  transfer posted to "a GLM 5.3 session" — prepared, not picked up. DO NOT replay #2182's
  carrier or steal #2367's writer; coordinate via #983.

## Fleet state at save

- A (debugger, opus): DONE (partial, gaps closed inline above).
- B (scout, sonnet): DONE (VPS/M2 truth above).
- C (GLM 5.3 delegate): RUNNING — PR/issue custody matrix (#983/#2060/#2175/#2182/#2367;
  Macro #10740/#10727/#7179) + per-file collision answers for daily.yml, master_brain.py,
  build_aibrief.py, brain_gateway, brain.yml, llm_auth, fabric_inference_client,
  provider_workloads.v1.json.
- E (DeepSeek V4.1 Flash delegate): RUNNING — census delta 9e6659c4→HEAD + remaining
  direct-bypass call sites.
- Next: C lands → decide write path (own PR vs coordinate) → builder packet P1 → tests →
  PR (link + merge-on-green controller) → real-slot verification. D (Brain Fast/Pro:
  deepseek-v4.1-flash / full glm-5.3 via qualified Fabric) and F (E2E canaries) queue
  behind P2 custody. T3 capacity_fabric provider EXPOSES both deepseek-v4.1-flash and
  glm-5.3 (+glm-5.3-flash which Pro must NOT get) as child models.

## Open gates

- Cancellers of engine jobs (chronic Oct 20–Nov 9): source unidentified (external cancel
  API or runner drops); fix is resilient `!cancelled()` steps + truthful receipts, robust
  to either.
- OAuth pool secrets (CLAUDE_CODE_OAUTH_TOKEN_1..7) expired/limited — credential refresh
  belongs to its existing owner; not fabricatable here.
- llm_auth deepseek `temperature` TypeError — #10740's file; coordinate.
