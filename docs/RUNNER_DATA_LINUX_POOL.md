# The `data-linux` pool — offloading Macro's Mac Studio data lanes

Status: **planned, no carrier yet** (2026-11-11). This runbook is the operator
guide for building the pool and moving the scheduled data jobs onto it, so the
M2 Mac Studio hosts (`macstudio` = mac-builder-5/mac-builder-light,
`macstudio-light` = mac-builder-3) can be freed. The analysis behind it lives
in `/tmp/cil_diag/m2_runner_offload.md` (M2-side) and
`.github/runner-policy.yml` (the declared pool model).

## The one-line switch

Every movable data job's `runs-on` now reads:

```yaml
runs-on: [self-hosted, "${{ vars.MACRO_DATA_LANE || 'macstudio' }}"]        # heavy lanes
runs-on: [self-hosted, "${{ vars.MACRO_DATA_LANE || 'macstudio-light' }}"]  # light lanes
```

* **Variable unset (today, the default):** the quoted fallback is the label the
  job already used. Routing is byte-for-byte today's routing; R11 sees the
  registered `macstudio`/`macstudio-light` literals and stays green.
* **`MACRO_DATA_LANE=data-linux`:** every switched job moves to the data pool
  in one act — heavy and light together. There is no per-job staging; size the
  pool for the combined load or don't flip.
* **Rollback:** unset the repository variable (Settings → Secrets and
  variables → Actions → Variables → delete `MACRO_DATA_LANE`). Jobs route back
  to the Mac labels on their next scheduling. Nothing else to undo.

This mirrors the existing in-repo pattern of a repository variable selecting a
lane (`vars.CI_EXECUTION_ROUTE` for the PC executor route, `vars.AD1_M1_LANE`
activating the M1 producer lane); the `|| 'label'` runs-on shape mirrors
sector-intelligence's `github.event.inputs.runner || 'macstudio'`.

## Activation order (memorize this, the order is the safety)

1. **Register carrier(s) first.** Register the runner(s) with the
   `data-linux` label through the runners API
   (`POST /orgs/{org}/actions/runners/{id}/labels` or repo-level equivalent) —
   labelling is an operator act via the API, never a file edit (same law as
   the pc-render `render-linux` restore).
2. **Update the registry in the same act.** Flip
   `label_registry.data-linux` in `.github/runner-policy.yml` to
   `status: live` with the real `carried_by` roster, and set
   `pool_topology.data-linux.slots` to the live count.
3. **Flip the variable last.** Only when
   `gh api repos/{owner}/{repo}/actions/runners` shows the carrier online set
   `MACRO_DATA_LANE=data-linux`.

Out of order, a cron fires onto a carrier-less label, its run sits `queued`
until GitHub's 24h kill while holding the concurrency group — the exact
2026-08-17 Prophet freeze (see the label_registry header notes). While the
label is registered-but-unused the declaration gates can't see this risk;
`scripts/check_runner_queue_hostage.py` (nightly-liveness) is the live
detector and will report the queued-with-no-runner symptom either way.

**Runner group:** do NOT put these runners in the `macro-home-canary` group
(`runtime_runner_group` in runner-policy.yml is restricted to six named
workflows — none of these lanes). Use the existing org fleet group
(`self-hosted, Linux, X64` + `self-ubuntu`-style fleet membership), the same
public-repo trust model already accepted for the canary group.

## Host prerequisites (the pool image)

Everything bootstraps itself except the base packages. Ubuntu 24.04 LTS x64:

```bash
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv git poppler-utils
```

* **python3.12** — on PATH. `.github/actions/python-venv` resolves
  `command -v python3.12` and falls back to `/opt/homebrew/bin/python3.12`
  (the Mac path); on this pool the PATH hit must exist. Ubuntu 24.04's system
  python3 is 3.12, so `python3.12` + `python3.12-venv` cover it. On 22.04 use
  the deadsnakes PPA. `python3.12-venv` matters: without it `python -m venv`
  fails with ensurepip errors.
* **poppler-utils** — `pdftotext` for asia-close's CBBC SLD extraction
  (`command -v pdftotext` preflight warns, then `hk_cbbc_sld` fails all
  extractions and the call_levels store freezes until a poppler-capable run).
  The only OS package any movable job needs beyond python/git.
* **git** — comes with the runner; jobs push data commits through
  `GITHUB_TOKEN` + `scripts/ci/push_retry.sh` (host-agnostic).
* **No Playwright/Chrome, no Keychain, no launchd, no local services.** All
  credentials are Actions secrets; the VPS services are reached over SSH with
  repo secrets. Warm GHA caches (`breadth/*_closes_cache.parquet`) are
  performance-only; parquet stores restore from R2 or the git checkout.
* **Python provisioning is NOT `actions/setup-python`.** Two documented
  self-hosted Mac failures rule it out (no hostedtoolcache dir →
  "mkdir: /Users/runner: Permission denied"; a setup-python 3.12 exec died
  with SIGKILL on the Studio). The pool provides python3.12; workflows never
  assume the tool cache exists.

## Disk

Sized for the nightly's restore-in / build-out pattern (R2 restores +
freshly-built parquet layers, plus the per-runner venv at
`$HOME/.cache/mm-venv-<runner>` and GHA cache staging):

* working tree + parquet store restores: **≥ 60 GB free** steady-state
  (thetadata lanes self-skip store-less — the 60 GB `thetadata_eod` store
  stays on the M1 and is NOT this pool's problem);
* headroom for the nightly `engine` band (the heaviest single CPU job,
  ~126 m measured green under a 300 m cap) and R2 restore staging:
  **120 GB free** is the comfortable floor;
- jobs are timeout-capped exactly as on the Mac (`timeout-minutes` unchanged),
  so worst-case disk burn per lane is the same class as today.

## Which jobs move (and which do not)

**Move with the switch (66 jobs / 47 workflows):** daily.yml's 16 nightly
jobs, weekly, asia-close (gate/asia/ths_rescrape — needs poppler),
closing-bell, close-pass backstop, earlyclose, cortex-retry, heartbeat,
backfill, brain-eval, debt-maturity-drip, edgar-flow-ops, factor-ops,
intl-etf, seo-director, signal-foundry, smart-money-13f-bulk-reconcile,
smart-money-filings, special-sits-backfill, tushare-spine-backfill,
validate-leading-legs, the 11 metabolism-* lanes; light lanes: sentinels
(flash-crash/commodity/whitehouse), intraday + intraday-fastpath,
live-breadth, marketing-publish, filing-forensics (sec + broad-sec),
fms-acquire, dod-budget-acquire, government-revenue-live, regime-self-heal,
research-vault-census, deploy-api-secrets.

**Stay on the Mac (unchanged by this PR):**

* `research-ingest.yml` — pinned producer release + prebuilt arm64 venv on
  `/Volumes/Mastermind` (external SSD). Moving it is a producer
  re-platforming project, not a runner change.
* The arm64-locked isolated-runtime lanes — `smart-money-13f-census`,
  `smart-money-13f-k2c-pilot`, `smart-money-13f-r2-conformance`,
  `capital-share-count-r2-concurrency/-conformance`,
  `attested-history-operator`, `attested-history-aapl-seed` — install from
  `requirements/*-macos-arm64-py312.lock` files. They need Linux lock files
  before they can follow; until then they keep their literal Mac labels.
  (`smart-money-13f-bulk-reconcile` *does* move: its lock is also named
  `macos-arm64` but contains only plain `==` pins with no platform markers
  or hashes, so the same file installs on Linux x64; its venv step resolves
  `python3.12` from PATH with the Homebrew path as fallback.)
* `key-pool-probe.yml` (own macOS/Linux conditional bootstrap) and
  `sector-intelligence.yml` (own `inputs.runner` options) — unchanged
  mechanisms.
* `options-intel.yml` stays `[self-hosted, m1-theta]` (R15 exact-route
  contract); render.yml/engine-render.yml keep their Linux-default routes.

The Python bootstrap itself is now host-neutral in **every** workflow that
used the old `/opt/homebrew/bin/python3.12 -m venv` step (the composite action
`.github/actions/python-venv`), so the staying-Mac jobs benefit too and the
remaining `opt/homebrew` references are the deliberate ones above.
