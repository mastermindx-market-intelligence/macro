# R5 prospective consumer — frozen specification

Pinned tree: `origin/main` `6f220a16e9e0a16c9042976f3a38c2615ed3d164` (2026-10-06).
Program row, quoted verbatim from `INFORMATION_TO_PRICE_PROGRAM_2026-10-03.md` §8 (held PR #8312, read by `git show` only, not checked out):

> R5 — prospective consumer | Existing scheduled owner accrues shadow output; existing read model exposes accepted context | Actual natural-time production and consumer proof, degradation, correction and replay checks | Security State/F04/Prophet context as separately accepted

This document is a proposal. It takes no owner decision, builds nothing, and grants no financial, rank, gate, size, trade, or publication authority.

## §0 Status line

FROZEN SPEC — proposal for owner ratification; builds nothing; HOLD-FOR-SOL

HOLD-FOR-SOL — holding authority: Sol (AI CEO). Release condition: a Sol comment beginning `HOLD-RELEASED`. Proposal for owner ratification — builds nothing.

Parent issue: [#8309](https://github.com/mastermindx-market-intelligence/macro/issues/8309).

## §1 Scheduled owner

The scheduled owner is the existing nightly workflow `.github/workflows/daily.yml`, job id `engine`. There is no step `id:` on the step this spec extends. The step name is the identifier.

Job id, quoted from `.github/workflows/daily.yml`:

```
1895:  engine:
1896:    needs: [et_gate, collect, government_revenue_projection]
1897:    if: always() && needs.et_gate.outputs.run != 'false'
1900:    env:
1901:      COLLECT_LANE: nightly   # job-level sentinel: inherited by every step; ensures all
1902:                              # forward-ledger writers in this job (build_track_record,
1903:                              # build_flip_confirmation, oracle_nightly, demand_ledger,
1904:                              # build_confluence_strength, archive_signals,
1905:                              # archive_context_snapshots, build_thematic_state,
1906:                              # grade_thematic) can advance their ledgers.
```

The header of the same file states the lane law this spec does not replace (`.github/workflows/daily.yml:8`):

```
8:    # Build B — the sole authoritative / ledger-advancing build (two-build design 2026-07).
```

The step a future build lane would extend, and the script that step already runs:

```
2250:      - name: run regime engine + build dashboard + daily brief (resilient)
2251:        if: steps.leader_accepted_source.outputs.ready == 'true'
2284:        # Body extracted verbatim to scripts/ci/daily_engine_regime_dashboard.sh (512KB processing-cap diet 2026-08-12 — tests/test_workflow_file_size.py).
2285:        run: bash scripts/ci/daily_engine_regime_dashboard.sh
```

Inside that script, the existing call that reaches this family's only source accrual is `scripts/ci/daily_engine_regime_dashboard.sh:104`:

```
104:run_py "macro dashboard + US stocks (build_site)" scripts.build_site
```

`scripts.build_site` calls `scripts/build_stock_library.py`, which calls the existing revisions drip:

```
3358:        from collectors.equity_revisions import fetch_revisions
3359:        if _no_drip():
3360:            log.info("revision drip skipped (render lane — data/ write discarded)")
3361:        else:
3362:            fetch_revisions(max_new=int(config.load().get("equity_profile", {}).get("per_build", 200)))
```

`fetch_revisions` calls `collectors/equity_revisions.py:accrue_expectation_observations` (`collectors/equity_revisions.py:425`). That function is the source owner. R5 reads its parquet outputs. R5 does not change it, its cadence, `_FRESH_DAYS`, or its universe.

The forward-ledger gate the consumer must call, and must not reimplement, is `engine/ledger_lane.py:nightly_advance_enabled`:

```
24:def nightly_advance_enabled() -> bool:
27:    Gate: COLLECT_LANE=nightly — the same sentinel set by daily.yml's
28:    engine-job env.  US_LANE is accepted as a legacy alias so existing
35:    val = os.environ.get("COLLECT_LANE", "") or os.environ.get("US_LANE", "")
36:    return val.lower() == "nightly"
```

Render and intraday lanes do not advance this ledger. `scripts/build_stock_library.py:1305` documents the discard:

```
1305:def _no_drip() -> bool:
1306:    """True when RENDER_NO_DRIP=1 — set by the render-only lanes (render.yml /
1307:    engine-render.yml). Those lanes commit site/ ONLY and DISCARD every data/ write,
```

`.github/workflows/earlyclose.yml` commits site output and discards ledger appends (`earlyclose.yml:336`, step name `commit rendered site + provisional snapshot pointers (ledgers discarded)`). `DNR:KILL-INTRADAY-CHRONICLE` says the nightly is the sole advancer and intraday lanes discard writes.

A future build lane extends `scripts/ci/daily_engine_regime_dashboard.sh` with one non-fatal call placed after line 104, still inside the existing `engine` step. The call returns immediately unless `nightly_advance_enabled()` is true. It does not add a job, a step id, a workflow, a cron line, a daemon, or a queue. The step's existing `if: steps.leader_accepted_source.outputs.ready == 'true'` remains the gate: a night that skips this step accrues nothing and does not count toward §4 G-PROD.

`DNR:KILL-NIGHTLY-HARD-GATE` stays in force. An unavailable upstream records a degraded row or, when no append target exists yet, writes nothing. It must not fail the `engine` job and must not skip later steps.

No new queue, daemon, cron, workflow, or scheduler. Intraday lanes never advance the ledger.

## §2 Read model

On `origin/main` `6f220a16e9e0a16c9042976f3a38c2615ed3d164` the read model that would expose accepted expectation, market-response, and coupling context is **UNOWNED**.

Search bounds, all run on this tree:

- `engine/k3e_expectation_surface.py` — absent
- `scripts/query_k3e_expectation_surface.py` — absent
- `engine/k3e_coupling.py` — absent
- `engine/price_pressure/response_export.py` — absent
- `engine/k3e*` — no matches
- `contracts/` and `research/` filenames containing `k3e` or `descriptive_coupling` — the only hit is the evaluation registration `contracts/research/k3e_expectation_market_dynamics_evaluation_prereg.v1.schema.json`. That file is an evaluation contract, not a consumer read model.
- `engine/price_pressure/` on this tree contains `__init__.py`, `artifact.py`, `backfill.py`, `base_rates.py`, `completion.py`, `context.py`, `detect.py`, `ledger.py`, `panel.py`, and `pipeline.py`. It does not contain the market-response export.
- These commits are not ancestors of this HEAD: `13910854fbd652dcdf975301bdc8c6728c2e4767`, `314ddae3f926c4ab1e424c646b1f21e90b2c6a68`, `3bf903fae36b94cff461eca81a9538862ec0cc38`.

`contracts/market_os/security_state.v1.schema.json` exists and is a real read model. `OWNER_AND_REUSE_MATRIX.md` says `security_state.v1` and K3E outputs are not substitutes for one another. This spec does not bind R5's expectation surface to Security State.

`data/revisions/expectation_observations.parquet` and `data/revisions/expectation_attempts.parquet` are SRC-A1 source-owner records. The same matrix forbids turning them into a K3E store. `data/prophet/ledger.jsonl` (`engine/prophet_arena.py` schema `prophet_arena.ledger/v2`) is Prophet's ledger. `scripts/archive_signals.py` appends regime and model snapshots under `data/signal_archive/`. None of those files carries schema `k3e.declared_capture_inspection.v1`, `price_pressure.market_response_export.v1`, or `k3e.descriptive_coupling.v1` on this tree.

This spec does not invent a store, a schema, or a path to fill that hole. The physical append target is the subject of §8 question 1. Until that question has an owner answer naming a file that already exists, a build lane must not create one.

Lands-after readers, not merged, not assumed merged. A build lane may call them only after the commits in §7 are ancestors of `origin/main`. It may not vendor copies of them.

| Role | Path on the held head | Schema constant | Held head | PR |
|---|---|---|---|---|
| Expectation reader | `engine/k3e_expectation_surface.py` function `inspect_expectation_surface`; CLI `scripts/query_k3e_expectation_surface.py` | `k3e.declared_capture_inspection.v1` (`engine/k3e_expectation_surface.py:9` at that head) | `13910854fbd652dcdf975301bdc8c6728c2e4767` | #8337 |
| Market-response reader | `engine/price_pressure/response_export.py` function `export_market_response` | `price_pressure.market_response_export.v1` (`response_export.py:27` at that head). `financial_influence` is false (`:61`). `k3e_admissible` is false (`:89`). | `314ddae3f926c4ab1e424c646b1f21e90b2c6a68` | #8422 |
| Coupling reader | `engine/k3e_coupling.py` function `compose_descriptive_coupling` | `k3e.descriptive_coupling.v1` (`k3e_coupling.py:17` at that head). `financial_influence` is false (`:24`). `k3e_admissible` is false (`:25`). | `3bf903fae36b94cff461eca81a9538862ec0cc38` | #8461 |

The named reader, once those heads have landed, is the existing CLI:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/query_k3e_expectation_surface.py \
  --repository <absolute path of this checkout> \
  --source-revision <40-hex commit> \
  --ticker <ticker> --metric EPS|revenue --horizon <horizon> \
  --as-of <UTC timestamp>
```

That command is the one recorded in the EXP-1 handoff at head `13910854fbd652dcdf975301bdc8c6728c2e4767` (`research/alpha_intelligence/expectation_market_dynamics/handoffs/EXP_1.md`). It prints one JSON object and does not write a file. Coupling is `compose_descriptive_coupling(expectation_result, market_response)`. R5 does not add a second reader.

## §3 Natural-time accrual contract

One scheduled `engine` success may append at most one receipt per `(market_date, ticker, metric, horizon)`. `market_date` is the America/New_York calendar date of the cron that `et_gate` allowed (`30 22 * * *` in EDT, `30 23 * * *` in EST; `.github/workflows/daily.yml:36-37`). A `workflow_dispatch` run may append a diagnostic receipt, and that receipt does not count toward G-PROD.

The receipt wraps the composer payload. It does not add an economic field, a score, a rank, a phase probability, or a value the composer left null.

Receipt fields:

- `payload`: the exact dict returned by `compose_descriptive_coupling`, serialized with `json.dumps(..., sort_keys=True, allow_nan=False)` and UTF-8. Schema inside the payload remains `k3e.descriptive_coupling.v1`.
- `source_revision`: the 40-hex commit whose `data/revisions/expectation_observations.parquet` and `data/revisions/expectation_attempts.parquet` blobs were read. The CLI already refuses any other revision form.
- `observation_blob_sha256` and `attempts_blob_sha256`: SHA-256 of those two blobs.
- `market_date`, `ticker`, `metric`, `horizon`.
- `github_event`: `schedule` or `workflow_dispatch`.
- `github_run_id`: the run id of this `engine` job, or null in a hermetic test.
- `appended_at`: wall-clock time the writer recorded the line. This field is named nondeterminism. It is not part of identity and not part of the replay compare.
- `correction_state`: `original` or `supersedes`.
- `supersedes_append_id`: null, or the prior receipt's `append_id`.
- `context`: the three optional refs in §4 G-CONTEXT. Absent means null. Context is not passed into `compose_descriptive_coupling` and must not change `payload` bytes.
- `append_id`: SHA-256 of the canonical UTF-8 string formed from `payload` bytes, `source_revision`, `market_date`, `ticker`, `metric`, `horizon`, and the canonical JSON of `context`. Not a wall-clock UUID.

Append rules:

- Append-only. The writer opens the owner-named file, parses existing lines, and adds one line. It never rewrites a previous line's bytes.
- As-of clocks. The expectation query `--as-of` is the engine run's recorded UTC time truncated to seconds. It is not a later re-interpretation of the same night. The consumer does not call `accrue_expectation_observations`. That function refuses a historical `system_observed_at` more than 60 seconds from the wall clock (`collectors/equity_revisions.py:441-444`) and is the wrong replay path.
- No hindsight backfill. A receipt for `market_date` D may not be inserted under an earlier `market_date`. A missed night stays missing.
- Idempotent re-run on the same date. If a line with the same `append_id` is already present, the writer adds zero bytes and exits 0. The `et_gate` fail-open double-run described at `.github/workflows/daily.yml:27-29` is this case when the input blobs match.
- Upstream `REFUSED` or unavailable. If `compose_descriptive_coupling` returns `state` `REFUSED`, or `coupling.status` `EXPECTATION_COMPONENT_UNAVAILABLE`, `MARKET_COMPONENT_UNAVAILABLE`, or `UNAVAILABLE`, the writer still appends that payload when an append target exists. Numeric fields that the composer set to null stay null. The writer must not substitute `0`. The shell call is non-fatal: a refusal does not set a non-zero exit on the `engine` step. Reason codes are copied from the composer (`REFUSED`, `SUBJECT_IDENTITY_MISSING`, `SUBJECT_MISMATCH`, `EXPECTATION_COMPONENT_UNAVAILABLE`, `MARKET_COMPONENT_UNAVAILABLE`, `UNAVAILABLE_NORMALIZED_EXPECTATION`, `PERIOD_CHANGED_NOT_REVISION`). The writer invents no additional economic code.
- Read model absent. On this tree the three reader files are absent. The shell call must detect that absence, print nothing that looks like a value, append nothing, and exit 0. Absence is not a fabricated `k3e.descriptive_coupling.v1` object.
- No append target. Until §8 question 1 is answered, the shell call is not added. Writing zero rows is the only lawful behavior. A comment in a status file is not an append.

The consumer does not call a provider, does not recompute a residual, and does not read held outcomes.

## §4 Acceptance gates as observables

No gate is met by a status note, a PR comment, or a green CI check alone. Each gate fails closed while its file or module is absent.

### G-PROD

N = 7.

`collectors/equity_revisions.py:82` sets `_FRESH_DAYS = 6`. Seven consecutive scheduled `engine` successes are the next integer after that freshness window. N is not a promotion threshold. EVAL-0 does not name a night count. Its prospective era is `PROSPECTIVE_SHADOW` with `promotion_eligible` const false (`contracts/research/k3e_expectation_market_dynamics_evaluation_prereg.v1.schema.json`, the `PROSPECTIVE_SHADOW` prefix item) and `prospective_authority_requirement` const `new_explicit_promotion_decision_after_prospective_shadow_never_from_EVAL_0` (`research/alpha_intelligence/expectation_market_dynamics/eval0_preregistration.v1.json`).

Check, after §8 question 1 has named an existing file `P`:

1. List receipts in `P` whose `github_event` is `schedule` and whose `github_run_id` belongs to a GitHub Actions job with `workflow` file `.github/workflows/daily.yml`, job name `engine`, event `schedule`, and job conclusion `success`. Use the jobs API for that run. The run-level conclusion is not evidence (`CURRENT_CAPABILITY_LEDGER.md` records runs whose run-level state was `cancelled` while `engine` succeeded).
2. Take the distinct `market_date` values. Sort them. A pair is consecutive when the later date is the next America/New_York date on which `daily.yml`'s `et_gate` allowed a scheduled `engine` job, not merely the next civil day filled by hand.
3. The longest trailing run of such dates that are ancestors of `origin/main` (the appending commit is on `main`) has length at least 7.

`workflow_dispatch` receipts do not count. A successful `engine` job that appended no receipt does not count. Two successes on the same `market_date` count as one date.

### G-CONSUMER

Named reader: `scripts/query_k3e_expectation_surface.py`, then `engine.k3e_coupling.compose_descriptive_coupling`.

Check:

```sh
test -f scripts/query_k3e_expectation_surface.py \
  && test -f engine/k3e_expectation_surface.py \
  && test -f engine/k3e_coupling.py \
  && test -f engine/price_pressure/response_export.py
```

On this HEAD that command fails. The gate is not met.

After §7 has landed, for a receipt R on `main`:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/query_k3e_expectation_surface.py \
  --repository "$PWD" \
  --source-revision "<R.source_revision>" \
  --ticker "<R.ticker>" --metric "<R.metric>" --horizon "<R.horizon>" \
  --as-of "<payload.expectation.as_of>"
```

The printed object's `schema` equals `k3e.declared_capture_inspection.v1`, and its `query_identity` equals `R.payload.expectation.query_identity`. A second call, `compose_descriptive_coupling` on that object plus `export_market_response` for the same ticker and the same source revision, serializes to bytes equal to `R.payload`. The stock-page revision chip (`data/revisions/latest.parquet` inside `build_stock_library`) is not this reader.

### G-DEGRADE

Check, as a hermetic test, not as a live night:

- Feed `compose_descriptive_coupling` an expectation object whose schema is not `k3e.declared_capture_inspection.v1`, or a market object whose schema is not `price_pressure.market_response_export.v1`. The returned `state` is `REFUSED` and `coupling.status` is `REFUSED` (`engine/k3e_coupling.py` at head `3bf903fae36b94cff461eca81a9538862ec0cc38`, `compose_descriptive_coupling`).
- Feed a supported expectation object and no market object. `coupling.status` is `MARKET_COMPONENT_UNAVAILABLE` and `state` is `EXPECTATION_ONLY`.
- Feed no expectation object and a supported market object. `coupling.status` is `EXPECTATION_COMPONENT_UNAVAILABLE` and `state` is `PRICE_ONLY`.
- In every case above, `normalized_value` is null, `financial_influence` is false, `k3e_admissible` is false, and no numeric field equals `0` unless the owner export itself contained that zero.
- Invoke the shell call the way the engine step invokes other non-fatal builders (failure does not abort the script). Exit status of the engine step's script remains 0.

A green nightly with no such row, and with no recorded refusal payload, does not pass.

### G-CORRECT

Check: take a frozen fixture pair. Run the writer once. Record the first line's bytes and `append_id` A. Change one input blob (a new `observation_id` that supersedes the prior observation, matching the SRC-A1 rule that corrections append and do not mutate as-known bytes). Run the writer again.

- The file now has two lines.
- Line 1's bytes equal the bytes recorded after the first run.
- Line 2's `correction_state` is `supersedes` and `supersedes_append_id` is A.
- Line 2's `append_id` is not A.
- No line was rewritten in place. `git diff` on a committed file shows an insertion, not a changed earlier line.

### G-REPLAY

Check: from the frozen `source_revision` and the two blob hashes stored on the receipt, recompute `payload` by the G-CONSUMER calls. Canonical JSON of that payload equals the stored `payload` bytes.

Named nondeterminism, excluded from the byte compare:

- `appended_at`
- `github_run_id`
- the wall clock inside `accrue_expectation_observations` when `system_observed_at` is omitted, and that function's refusal of a historical clock (`collectors/equity_revisions.py:441-444`). Replay must not call it.
- JSON serializers other than `sort_keys=True`, `allow_nan=False`, and stable UTF-8. Using a different serializer fails the gate rather than being waved through.

If the recomputed payload differs, the gate fails. A prose claim that the night was deterministic does not pass.

### G-CONTEXT

Security State, F04, and Prophet are optional refs on the receipt. They are not arguments to the composer. Each ref is either null or an object that passes its own predicate. A ref with an empty acceptance field fails.

Security State. Compiler `engine/security_state.py` (`SCHEMA = "security_state.v1"`). Contract `contracts/market_os/security_state.v1.schema.json` (`schema` const `security_state.v1`). Acceptance reference: PR #6371 squash `10b54a12828b14af0e99541a83c8d0638e64145e`, recorded in `agentos/handoffs/MARKET-OS-2026-08-26-b1a-proven-live.md`. Predicate: `schema == "security_state.v1"` and `authority.class == "context_only"` and `authority.can_rank`, `can_gate`, `can_size`, `can_originate_signal`, and `can_execute` are all false. The ref stores `content_sha256` and that acceptance sha. It does not copy leg values into `payload`.

Prophet. Schema `prophet_arena.ledger/v2` in `engine/prophet_arena.py` (`LEDGER_SCHEMA`). Registration `research/PROPHET_ARENA_REGISTRATION.md`. Predicate: the ref stores a ledger row identity and `schema == "prophet_arena.ledger/v2"`. It must not contain a score, a rank, a size, or schema `prophet.trade_plan/v1`. Prophet remains a separately accepted input.

F04. Until §8 question 2 is answered, `context.f04` is null. A non-null F04 ref fails G-CONTEXT. This spec does not choose `market_ontology.exposure_map/v1` (`engine/market_ontology/exposure_map.py`, `SCHEMA_ID`) as the F04 input. That file is one research-display projection under a merged ontology program. It is not, by itself, the acceptance reference for every F04 object.

A receipt that fails G-CONTEXT is not a successful consumer proof.

## §5 Owned-file list for a future build lane

This PR's only file is the document you are reading. The lists below bind a later lane. That lane must not start until every §7 item is merged and §8 question 1 has an answer naming a path that already exists on `origin/main`.

Lane R5-BUILD. At most five files.

May modify:

1. `scripts/ci/daily_engine_regime_dashboard.sh` — one non-fatal call after the existing `scripts.build_site` line, guarded by `nightly_advance_enabled()`.
2. The single existing append-only file named by the answer to §8 question 1 — append a line, or leave the bytes unchanged on an idempotent re-run. The lane may not create this file.
3. `tests/test_r5_prospective_consumer.py` — the §4 checks that can run hermetically (G-DEGRADE, G-CORRECT, G-REPLAY, G-CONTEXT, and the absence path). G-PROD stays an observation of `origin/main` and is not a unit-test substitute.

May not modify, create, or delete:

- `.github/workflows/daily.yml` and every other workflow file, including `earlyclose.yml`, `render.yml`, and `engine-render.yml`
- `collectors/equity_revisions.py` and `tests/test_equity_revisions_w2a.py`
- `data/revisions/expectation_observations.parquet` and `data/revisions/expectation_attempts.parquet` (read-only inputs)
- `scripts/build_stock_library.py` and `scripts/build_site.py`
- `engine/security_state.py`, `engine/prophet_arena.py`, `engine/prophet_bridge.py`, `engine/market_ontology/**`
- `engine/valuation_event_bridge.py`, `engine/valuation_event_proposal.py`, `engine/valuation_assumptions.py`
- `research/F07_EVENT_ASSUMPTION_PROPOSAL_CONTRACT_V1.md`
- `engine/ledger_lane.py` (call it; do not fork a second gate)
- EVAL-0 files: `research/alpha_intelligence/expectation_market_dynamics/eval0_preregistration.v1.json`, `eval0_activation_receipt.v1.json`, and `contracts/research/k3e_expectation_market_dynamics_evaluation_prereg.v1.schema.json`
- PR #8312 paths: `research/alpha_intelligence/expectation_market_dynamics/INFORMATION_TO_PRICE_PROGRAM_2026-10-03.md`, `CURRENT_CAPABILITY_LEDGER.md`, `SRC_A1_*_2026-10-03.*`, `information_to_price_audit.py`, `agentos/*` records, `.github/ci/legacy-jobs.yml`, `tests/test_equity_revisions_src_a1_acceptance.py`
- `config/compiled_kill_registry.yml` and `config/signal_foundry_blocklist.yml`
- anything under `data/` other than the one named append target, and anything under `site/`
- a new queue, daemon, scheduler, store, schema file, score, or scenario module

If the answer to §8 question 1 never names an existing path, lane R5-BUILD has no second file and must not open.

## §6 Standing kills and rulings honoured

Each key below was found in `research/DO_NOT_REBUILD.md` on this tree. Cite them as `DNR:<KEY>`.

- `DNR:KILL-PSS-F3-RESIDUAL`. The consumer does not build an idiosyncratic-residual entry timer. Market numbers, if present, come only from the landed MKT-1 export. If that export is absent, the receipt says the market component is unavailable. It does not residualize prices itself.
- `DNR:KILL-LIQUIDITY-SHOCK-REVERSAL-CLASSIFIER`. The consumer does not classify shocks, does not label forced liquidation, and does not veto Prophet entries.
- `DNR:KILL-OUTCOME-AUDITION`. The consumer does not pick a per-name tool by later outcomes, does not search a grid, and does not grade shadow rows against returns. G-PROD counts appends, not profits.
- `DNR:KILL-CAUSAL-DAG-ALPHA`. The consumer does not discover a graph, emit an alpha score, or size a portfolio. The landed composer leaves `phase_probability`, velocity, acceleration, disagreement magnitude, and incorporation fraction null. This spec does not fill them.
- `DNR:KILL-LLM-ORIGINATION`. The accrual call does not invoke a model. It does not attach the engine step's existing LLM desks (master brain, narrative brain, risk brain, alt-data brain). Those desks stay where they are.
- `DNR:KILL-OWNERSHIP-BREAKAWAY`. The consumer does not read 13F holdings as a breakaway signal. Ownership is not an input. Crowding context, if an owner later wants it, needs its own acceptance and is not granted here.

Sol comment `5991076454` on issue #8309, binding sentences, quoted verbatim:

> ## Commission-1 / R3 scenario ownership ruling — reuse F07/MAS-148; do not build a third scenario engine

> The deterministic scenario capability is **not greenfield**.

> Canonical valuation / assumption / scenario owner:
> - **WS:MARKET-OS**
> - **F07**
> - Linear projection **MAS-148**

> Commission-1 must **not** create:
> - a K3E-owned scenario calculator;
> - an Earnings-owned parallel valuation/scenario engine;
> - another Brain financial calculator;
> - a third financial scenario schema.

> preserving K3E as expectation→market owner rather than scenario owner.

> DO_NOT_REDO: new scenario kernel, duplicate calculator, new financial-truth store, new event owner, new K3E valuation plane.

This spec stays outside that ruling. It does not call `engine/valuation_event_bridge.py`, `engine/valuation_event_proposal.py`, or `engine/valuation_assumptions.py`. It does not define a scenario schema. It does not mint a magnitude. F07 remains the scenario owner. K3E, here, only reads expectation and market-response outputs and records what those readers returned.

Two further standing rows bind the nightly shape and are not part of the six keys above. `DNR:KILL-INTRADAY-CHRONICLE`: intraday and render lanes discard `data/` writes; only the nightly advances a ledger. `DNR:KILL-NIGHTLY-HARD-GATE`: a refused upstream must not hard-fail the rest of the night.

No user-facing product string is introduced. The Terminal shell is dark-only under `DEC:TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06`. This spec builds no Terminal surface and no macro site surface. A later surface that showed a receipt would owe plain sentences in English and Chinese, and both a dark and a light treatment. That surface is out of scope.

## §7 Prerequisites and order

A build lane must not start until each of these commits is an ancestor of `origin/main`. None of them is an ancestor of `6f220a16e9e0a16c9042976f3a38c2615ed3d164`.

| PR | Head sha | What it supplies | State on this pin |
|---|---|---|---|
| #8337 | `13910854fbd652dcdf975301bdc8c6728c2e4767` | EXP-1 reader `k3e.declared_capture_inspection.v1` | not merged into this HEAD |
| #8422 | `314ddae3f926c4ab1e424c646b1f21e90b2c6a68` | MKT-1 export `price_pressure.market_response_export.v1` | not merged into this HEAD |
| #8461 | `3bf903fae36b94cff461eca81a9538862ec0cc38` | CPL-1 composer `k3e.descriptive_coupling.v1` | not merged into this HEAD |

Order: #8337 and #8422 before #8461's composer can see both inputs, and all three before R5-BUILD edits the shell. The lane also waits on an answer to §8 question 1. Merging those three pulls does not by itself name an append file.

Descriptive only, until a separate EVAL admission that this spec does not grant:

- `financial_influence` is false on the market export and on the coupling payload.
- `k3e_admissible` is false on both, until EVAL admission.
- `PROSPECTIVE_SHADOW.promotion_eligible` is false.
- Prospective authority requires `new_explicit_promotion_decision_after_prospective_shadow_never_from_EVAL_0`. Passing G-PROD does not promote.

SRC-A1 on this tree remains the source of the two revision parquets. This spec does not restate its proof state and does not promote it.

## §8 Open questions for owners

None of these is answered by this document.

1. Addressed to Sol (AI CEO), holding authority for this proposal, on issue #8309, workstream `WS:ALPHA-INTELLIGENCE-INTEGRATION`. Which existing append-only file on `origin/main` may receive the receipt line in §3? The search in §2 found no file whose schema is the coupling payload. Please name a path that already exists, or rule that no durable append is authorized. A new path is not an acceptable answer under the program's exclusion of new stores.

2. Addressed to the MarketOntology F04 operation `marketontology-f04-ontology-transmission-20260826-fable-001`, decision `agentos/decisions/DEC-GMI-THEME-GRAPH-END-TO-END-COMPLETION-OWNERSHIP-SEQUENCING.md` (merged PR #6504 is the program's canonical assignment, not a choice of object). Which single accepted F04 object, if any, may appear in `context.f04`? Until you name the schema const and the acceptance sha, the field stays null.
