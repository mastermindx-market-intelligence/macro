# The §26.9 pilot gate

**What this proves, plainly: harness behaviour. Not X.** No browser starts, no
cookies exist, no network call is made. A `FakeDriver` implements the whole
`drivers.base.Driver` protocol in memory, so the gate exercises the real
scheduler, the real leases, the real supervisor state machine, the real
validators, the real keystroke planner and the real telemetry writer — and then
fakes only the part that would have been Chrome. A green gate means the harness
would not have fallen over on its own during the pilot. It does **not** mean X
accepted the posts, that the selectors still match a live DOM, or that the
accounts avoid walls in practice. Those still need §26.9's real fourteen days.

The clock is simulated, so fourteen days finish in a few seconds and nothing
ever sleeps. Runs are seeded and deterministic.

## Running it

From the repository root (`/Users/chriswong/Mastermind/macro`). The pytest run
must start here too — `tools/xguerrilla/typing.py` shadows the stdlib `typing`
module and importing from inside the package dies with `partially initialized
module 'typing' has no attribute 'ClassVar'`.

```bash
# the gate itself
python3 -m tools.xguerrilla.gate sim          # the 14-day dry run, JSON on stdout
python3 -m tools.xguerrilla.gate criteria     # the checklist and its pass state
python3 -m tools.xguerrilla.gate drill        # the deliberate-failure drills

# the tests
python3 -m pytest tools/xguerrilla/tests/test_pilot_sim.py -q
```

Same commands on `mini1`, which is the point of the fake driver — the gate needs
no display, no Chrome, no logged-in profile. `--store-dir DIR` (on `sim` and
`criteria`) keeps the sqlite database and the JSONL telemetry instead of a
temporary directory, so evidence survives for a post-mortem. `--seed N` changes
the draft pool.

## Exit codes

| code | meaning |
| ---- | ------- |
| 0 | every §26.9 criterion holds |
| 1 | the simulation ran and at least one criterion failed; `failures` names it |
| 2 | the harness itself threw; `error` carries the exception |

2 exists so a crashed gate is never mistaken for a passing one.

## The criteria

Each row is one sentence of §26.9 turned into a check. `sim` and `criteria` emit
all five with a `pass` state; `failures` carries one plain sentence per failing
criterion, naming it.

| id | criterion | what it actually checks |
| -- | --------- | ----------------------- |
| `children_days_challenges` | three children run fourteen days with zero challenges | all `DEFAULT_CHILDREN` post on all fourteen days, no challenge recorded |
| `iki_in_band` | IKI histograms stay inside each speed class band | each child's median inter-keystroke interval, measured from the real keystroke plans, sits within `median_ms × pause_mult` of its speed class |
| `label_spread` | at least two labels in each child's thirty posts | distinct labels per child across the run |
| `restart_without_relogin` | one restart is survived without a re-login | the driver is stopped and rebuilt mid-run; posts continue and `relogins == 0` |
| `outage_degraded_recovered` | one deliberate worker outage falls through to degraded mode and recovers | `Supervisor.degrade` puts the broadcast child out of the runnable set for the window, `recover` restores it, and it posts again afterwards |

## The drills

`drill` is the negative control — it deliberately breaks something and asserts
the *response* the masterplan asks for, not just that nothing crashed.

- `challenge` — a wall on the third write: counted, child cooled, run continues.
- `retire-on-second-wall` — two walls: the second retires the child instead of
  cooling it forever.
- `session-expiry` — cold cookie jar: exactly one re-login and no post inside the
  `LOGIN_COOLDOWN_S` window.
- `worker-outage` — broadcast child drops out, degradation is recorded, recovery
  happens and work resumes.
- `selector-drift` — the composer locator drifts: the step is quarantined and the
  child stays runnable.

## Injections

`run_pilot(..., inject={...})` accepts:

| key | effect |
| --- | ------ |
| `challenge_after_n` | int or list of submit counts; raises a verification wall there |
| `expire_session_at` | datetime; drops the session once, forcing a re-login |
| `outage_window` | `(start_day, end_day)` floats; the worker outage window, default `(9.0, 10.0)` |
| `selector_drift_step` | number of N-th writes where the locator has drifted |
| `drift_target` | which selector drifts, default the composer |
| `break_drafts` | number of drafts to compose invalid (over-length) on purpose |
| `restart_day` | day the worker restarts, default `7` |
| `start` | simulated start timestamp, default `START` |

## Reading the output

`posts`, `typed_posts`, `pasted_posts`, `challenges`, `relogins`, `restarts`,
`lease_conflicts`, `violations_blocked`, `degraded_windows`,
`quarantined_steps`, per-child `labels`/`iki`/`per_child_posts`, `holds` (one row
per lease span), `skipped` (why a slot did nothing) and `telemetry` (JSONL path).
`posts` counts only writes that reached the composer and submitted;
`violations_blocked` counts drafts the validators refused and rewrote.

## Known seams

- **Two driver protocols.** `drivers/base.py` defines the real one — `start`,
  `goto`, `snapshot`, `find`, `click`, `type_plan`, `paste`, `key`, `screenshot`,
  `stop`. The docstring at the top of `supervisor.py` still describes a different
  login/session/locate/act surface that nothing implements. `FakeDriver` follows
  `base.py`. Until the docstring is corrected, treat `base.py` as the contract.
- **No `Supervisor.heartbeat()`.** Only `degrade()`/`recover()` write the health
  row, so a child that is merely alive looks stale after `STALE_HEALTH_S`. The
  simulator re-stamps `health.updated_at` itself on every slot; a live worker
  must do the same or degraded mode will fire for the wrong reason.
- **`typing.py` is in flux.** Another change is editing the keystroke planner, so
  the tests assert on the folded text and on the IKI band, never on a keystroke
  count.
- **Absolute paths leak into the JSON.** `store_dir` and `telemetry` differ
  between two runs; everything else is byte-identical for a fixed seed.
