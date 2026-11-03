# Global Liquidity Transmission — producer liveness (GLT T06, 2026-10-13)

Workstream: `WS:GLOBAL-LIQUIDITY-TRANSMISSION` · task T06 of the 2026-10-13 28-task DAG ·
acceptance rows C11 (ageing survives the normal producer→reader path) and C12 (a wrapper
or a checked-in sample cannot certify freshness). Producer `#6296` and reader Mastermind
`#914` are frozen; nothing here changes their semantics, thresholds, hashes or contract.

## 1. Finding — the producer had no production caller

`site/liquiditydata/global_liquidity_transmission.json` has been checked in twice and
never refreshed by machinery since:

| commit | date | what |
|---|---|---|
| `ae039fb06768` | 2026-08-22 | first producer artifacts (W-LIQ.1 merge) |
| `7fb785ee07b8` | 2026-09-04 | manual regeneration "at the post-merge head" |

Served state as of this note: `freshness.clocks.evidence_available_at = 2026-08-28T00:00:00Z`,
`meta.generated_at = 2026-09-04T11:03:41Z`, `freshness.status = "fresh"`. The status is
the producer's judgment *at generation time*; it is frozen into the file and says
nothing about today.

Root cause, verified on `origin/main` `84e177a2b9b2`:

```
git grep -n build_global_liquidity_transmission origin/main -- .github config
.github/ci/legacy-jobs.yml:13804:      - "scripts/build_global_liquidity_transmission.py"
```

That one hit is a `paths:` filter of the pack-executed CI **test** lane
`global-liquidity-transmission` (its `if: ${{ false }}` only keeps the legacy status
definition runner-free; `run_ci_pack.py` executes it inside a ci-pack). The lane runs
pytest against synthetic inputs and never publishes. No workflow (`daily.yml`,
`render.yml`, `engine-render.yml`, `asia-close.yml`, …) invokes the builder and
`config/dag.yml` does not declare it. A frozen producer with zero callers is a
display surface that can only age.

## 2. Four staleness layers (distinct — fixing one does not fix the next)

| layer | where | what makes it stale | owner after this note |
|---|---|---|---|
| **producer** | Macro `daily.yml` engine job | builder never ran (§1) | **fixed here** |
| **source inputs** | collect job (fred, yahoo stores), asia lane (`china_credit/tsf.parquet`), engine job (`regime/latest.json`) | collection not landing on main | nightly/collect owners — not GLT |
| **publish** | VPS `/opt/macro` → `site.served/` → Caddy | none observed; access is gated | unchanged |
| **vendor copy / consumer** | Mastermind `vendor/macro/site/liquiditydata/…` read by `brain/liquidity_transmission.py` | the consuming host's macro checkout not moving | consumer task (T23), see §5 |

**Producer.** Fixed by the step in §3.

**Source inputs.** The builder reads only local stores: `data/fred/{BUSLOANS,WALCL,
ECBASSETSW,JPNASSETS,DTWEXBGS,DFII10,BAMLH0A0HYM2}`, yahoo `EURUSD=X`/`USDJPY=X`,
`data/china_credit/tsf.parquet`, `data/regime/latest.json`. On `84e177a2` the newest
`data: daily collection` commit on main is `cdab77c46a9e` (2026-10-09); the newest
`data: asia collection` is `07d0bcf3a8ca` (2026-10-12). A local rebuild on that tree
moved `evidence_available_at` from 2026-08-28 to **2026-10-02** — eleven days before
today, so even a live producer serves a state the consumer will call stale until
collection is current again. Producer liveness is not source freshness, and this note
claims only the first.

**Publish.** `app/deploy/update.sh` (installed as `/usr/local/bin/macro-update`, cron every
3 min) does `git fetch --depth 1 origin main`, `git reset --hard FETCH_HEAD`, then
`rsync -a --delete --min-size=1 site/ site.served/`. Anything the nightly commits under
`site/` is served within minutes; no second refresher is needed or added.
`https://www.mastermind-x.com/liquiditydata/global_liquidity_transmission.json` returns
**401** (`application/json`, measured 2026-10-13): `/liquiditydata/*` is outside the
Caddyfile `PUBLIC-BOUNDARY` allowlist (`app/deploy/Caddyfile`, the `@reg_asset` block and
its not-path list). That is an access gate, not staleness, and stays as is.

**Vendor copy / consumer.** The Mastermind reader resolves
`_ROOT/vendor/macro/site/liquiditydata/global_liquidity_transmission.json`.
On Mastermind master, `vendor/macro` is a tracked **symlink** to `macro_src`
(tree blob `67c7d1aa`); `.gitmodules` still documents the older pinned-submodule wiring.
Mastermind CI checks out macro at a pinned sha, sparse `engine` + `lib` only, so CI never
sees `site/` at all. On the serving host the reader sees whatever checkout
`vendor/macro_src` resolves to; a macro merge plus a nightly does not move that copy unless
that checkout is pulled. This layer was not inspected on the host (no VPS shell in this
commission) and is named as a gap, not assumed healthy.

**Reader ageing law (consumer).** `brain/liquidity_transmission.py::_freshness_verdict`
(Mastermind `08597860f`) ages from `freshness.clocks.evidence_available_at` alone:
stale when the clock is unparseable, future-dated, later than `first_known_at`, older than
10 calendar days, or when the producer status is not `fresh`. `generated_at`,
`monetary_release_at`, `latest_component_observed_at` and `state_asof` are declared
non-evidence clocks. Freshness is re-judged on every call; the process cache holds only
the read. The Macro workspace reader (`liquidity_central_banks._glt_freshness`) ages
`state.asof` on the W-FRI grid (7 days CURRENT, +4 days LATE_WITHIN_TOLERANCE, then
STALE_SOURCE; a future clock is SOURCE_FAILED), and the producer's own status can only
downgrade it.

## 3. Fix

* `.github/workflows/daily.yml`, engine job — new step **after** `build_liquidity_plumbing`
  (which already consumes `data/regime/latest.json`; collect is a job dependency of
  engine), using the sibling non-fatal idiom:
  `python -m scripts.build_global_liquidity_transmission || echo "::warning::… (non-fatal — last committed artifact stands)"`.
  No Python annotation was added; the builder is unchanged.
* Outputs are staged by the existing `git add data/ site/ reports/`
  (`scripts/ci/daily_engine_commit_outputs.sh` L64) in "commit engine outputs"; neither
  path is in that script's reset lists and neither is git-ignored.
* `config/dag.yml` — the matching `build_global_liquidity_transmission` lane entry
  (`scripts/check_dag_conformance.py` → OK, 27 lanes).
* `tests/test_global_liquidity_transmission_liveness_v2.py` — versioned namespace, reads the
  tracked artifact, asserts its bytes are unchanged afterwards, writes nothing:
  - C11: the tracked artifact past the window is stale under the mirrored consumer law and
    under the real Macro reader (`compose`); a future-dated clock is rejected by both; the
    August artifact evaluated on 2026-10-13 is stale on both, although its frozen status
    reads `fresh`.
  - C12: re-stamping `meta.generated_at`, `first_known_at` and every non-evidence clock
    leaves the verdict stale; a wrapper carrying a new `generated_at` and `status: fresh`
    is stale or SOURCE_FAILED.
  - Wiring: exactly one engine-job invocation, ungated, non-fatal, after the plumbing
    step; the commit step stages `data/` and `site/`. Against `origin/main` bytes this
    test fails ("exactly one nightly invocation of the GLT producer").
  - All ages are relative to the artifact's own clocks, so the nightly advancing the
    artifact cannot break the suite.
* The test is registered in the existing `global-liquidity-transmission` CI lane (paths +
  pytest command). It is pure stdlib + pyyaml beyond the lane's existing install.

## 4. Measured cost (render budget ≈ 67 min)

`/usr/bin/time -l python3 scripts/build_global_liquidity_transmission.py` on the M2,
2026-10-13, tree `84e177a2`: rc 0, **2.54 s real** (1.92 user, 0.17 sys), max RSS
142,491,648 B (**≈136 MiB**), peak footprint 93,127,400 B. That is under 0.07 % of
the budget, and no network calls are made. The regenerated bytes were **not**
committed: production data is the nightly's job (it is the only thing that advances
ledgers and artifacts), and committing a local rebuild would pre-empt the proof below.

## 5. Production-proof condition

`MERGED` is not `PRODUCTION_PROOF`. The proof needs all of the following:

1. **Run.** The first `daily.yml` run after the merge whose engine job reaches the
   new step. Its log shows the builder's JSON summary or the non-fatal warning.
2. **Commit.** Its "commit engine outputs" lands a main commit that changes
   `site/liquiditydata/global_liquidity_transmission.json`, with
   `freshness.clocks.evidence_available_at` later than `2026-08-28T00:00:00Z` and
   `meta.generated_at` inside that run's window.
3. **Served.** The VPS bytes at `/opt/macro/site.served/liquiditydata/global_liquidity_transmission.json`
   show the same `evidence_available_at`. An authenticated GET of the gated URL is an
   equivalent check.
   - Never prove this by ancestry. `/opt/macro` is a `--depth 1` clone, so
     `merge-base --is-ancestor` is false there even for a deployed commit.
4. **Consumer (separate claim, T23).** The Mastermind host's
   `vendor/macro/site/liquiditydata/…` shows the same clock.
   - Until it does, a fresh producer can still be read as stale by the consumer.

"Advances" proves liveness. Being inside the consumer's 10-day window also needs current
collection (§2), and the nightly lane owns that, not this task.

The nightly is currently held by the fleet's runner/outage owners. This task schedules
nothing, dispatches nothing and adds no cron. Proof arrives with the first nightly that
those owners run.

## 6. Reversibility

Delete the step and the dag entry. The artifact keeps its last committed bytes and
ages stale in every reader by its own evidence clock — the same fail-closed state as
before this change.
