# Rotation Core — code of record

The protected archive contains the engine, runner, tests, Run A fixture program and ten power-analysis helpers. This directory carries the protocols, input hashes, stdout, result data and adjudication records.

| | |
|---|---|
| Archive branch | `fable/rotation-core-20261110` |
| Archive head | `b1e4b44c529a152887a4e6080cdf8028766e60a0` |
| Engine commit (pinned by the selection rerun and the stage-1 release) | `b3f7ce4548cadabee85e5e616b88317dc63346d2` |
| Stage-1 release | `8cd6410201cd902081906deb37db81fbbf5e0685` |
| Run ledger START | `15893a170e72507666088d6d6cd3fa748c90fbd2` |
| Run ledger GATE (`gate_open: false`) | `2200b942d41a23afda7be6ca448b0aceee8ceef6` |

The branch is protected by repository ruleset 27041175 (`non_fast_forward` and `deletion` blocked, bypass list empty). It is never deleted or rewritten.

**Why the code is not on `main`.**
- Macro's import guard requires entry scripts to put the repository root first on the import path, while the v2 runner deliberately appends it so that the standard library and site-packages always win (ruling R31.6(b)). Changing the runner to pass the guard would put on `main` bytes that are not the bytes that ran.
- Macro merges by squash, so the engine, release, START and GATE commits are reachable only from the archive branch.

Every file path and line number cited in this directory (for example `engine/rotation_core_v2.py:1126` or `scripts/run_rotation_core_v2.py:774`) refers to engine commit `b3f7ce4548`.

## Verifying the archived power-analysis packet

The [power-analysis directory](https://github.com/mastermindx-market-intelligence/macro/tree/b1e4b44c529a152887a4e6080cdf8028766e60a0/research/rotation_core/v2_power) contains the ten original Python helpers alongside their recorded outputs. The [Run A fixture program](https://github.com/mastermindx-market-intelligence/macro/blob/b1e4b44c529a152887a4e6080cdf8028766e60a0/research/rotation_core/PRO_RUN_A_fixtures.py) is at the same archive commit. The `v2_power/SHA256SUMS` manifest covers the complete archived packet. To verify all entries in a checkout of the archive head, run the following from the repository root.

```sh
(cd research/rotation_core/v2_power && shasum -a 256 -c SHA256SUMS)
```

## Reproducing a published figure

1. Check out the engine commit (or the archive head, whose `engine/`, `scripts/` and `tests/` are identical to it):
   `git checkout b3f7ce4548cadabee85e5e616b88317dc63346d2`
2. Obtain the inputs. They are vendor data and are not in the repository:
   - Ken French 49 Industry Portfolios, daily, truncated at 2019-12-31;
   - Fama/French research factors, daily;
   - for the selection window, the Yahoo total-return series for SPY and RSP.

   Their sha256 values are in `research/rotation_core/v2_power/REAL_INPUT_SHA256.txt`, and the runner refuses any other bytes.
3. Run with the pinned interpreter form, from the repository root:
   `env -i HOME=$HOME PATH=/usr/bin:/bin <venv>/bin/python -E -P -B -X pycache_prefix=/dev/shm/rotation_core_v2_pycache scripts/run_rotation_core_v2.py --preflight`
   The sealed stages are run-once. They refuse here, because their ledger records already exist.
4. To recompute the stage-1 magnitudes, call `scripts.run_rotation_core_v2.pre1998_report(<industries file>, <factors file>, selection=<results_v2_selection_rerun.json>)` and compare `engine.rotation_core_v2.magnitudes_sha(result["magnitudes"])` with `0c6c207e81889fe11890420cc08d05e25c326b0087c54535473ccd4b3fafff29`, the GATE record's hash and the published file's.
   - The selection-window figures are checked against `1ca5228b3c` by `research/rotation_core/v2_power/repro_check.py`.

## A successor

A successor protocol is a new protocol carrying all 55 trials plus its own (amendment d). It brings its own runner to `main`, built to pass Macro's import guard from the start.
