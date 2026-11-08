# xguerrilla operator runbook

Everything here is a command an operator runs from the repository root. Exit
codes, output shapes and timings are measured, not intended; the last measured
run is dated beside each table.

## 1. What is shipped, and what is not

| Shipped | Where |
| --- | --- |
| three-child, fourteen-day pilot model (posts, typing, labels, IKI, restarts, outage, walls) | `pilot_sim.py` |
| six gate criteria and five deliberate-failure drills | `gate.py`, `GATE.md` |
| proxy pool loader with 1:1 sticky slots and a masked loggable form | `net.py` |
| two drivers (Playwright and HTTP), paste contract, keystroke accounting | `drivers.py` |
| supervisor heartbeat, profile snapshot/restore/verify | `ops.py`, `profile.py` |
| text-drift audit | `textdrift.py` |

The **live binding is not shipped.** Every runtime entry point calls
`refuse_runtime` and exits **3** with `runtime_binding_unavailable` before it
touches a profile, a browser, a process or a ledger. This is a code property, not
a configuration: no environment variable, approval token or force flag changes
it, and `stop` is not a safe way to clean up a profile whose owner is unbound.
Section 6 lists the adapter work that removes the refusal. Until then the only
executable surfaces are inspection and simulation.

Sections 26.2–26.3 of the
[masterplan](../../research/agentic_media/X_GUERRILLA_NETWORK_MASTERPLAN.md) keep
lifecycle, exclusive ownership, approval and health with their existing owners;
a local row, lease token, persona handle, proxy slot or backend choice does not
substitute for any of them.

## 2. Interpreter and invocation

The harness is a module tree, not an installed console script: run it with `-m`
and put the repository root on the path.

```
# laptop
cd ~/Mastermind/macro && PYTHONPATH=. /opt/homebrew/bin/python3.12 -m tools.xguerrilla.cli status

# worker box
cd ~/macro && ~/.venvs/xg/bin/python -m tools.xguerrilla.cli status
```

`PYTHONPATH=.` is not optional on the laptop: the default `python3` there is
3.14 without PyYAML, and `cli.py` dies at import with
`ModuleNotFoundError: No module named 'yaml'` rather than reporting a missing
dependency. `/opt/homebrew/bin/python3.12` has PyYAML and pytest. On the worker
box `~/.venvs/xg/bin/python` does.

## 3. Command reference

Measured 2026-11-08 on `c17a0c40b` + the masking commit.

| Command | Result |
| --- | --- |
| `cli status` | exit 3, `runtime_binding_unavailable`; no state database, no health row |
| `cli personas` | lists persona rows; no account or runtime admission |
| `cli net-check` | exit 0, `count` and `slots`, **masked** (see section 4) |
| `cli net-check --reveal` | exit 0, full host/user per slot; use only where a child is about to bind |
| `cli shadow --dry-run` | describes the resolved steps; `checked: 0`; starts no driver |
| `cli shadow` (no `--dry-run`) | exit 3 before reading steps or importing a driver factory |
| `cli snapshot` / `restore` / `verify` | exit 3 before profile access |
| `cli degrade` / `recover` | exit 3; both need an incumbent health/recovery binding |
| `gate criteria` | exit 0, six criteria with `pass` per criterion |
| `gate sim` | exit 0, fourteen-day model report (section 5) |
| `gate drill` | exit 0, five drills with `pass` and the counts each one produced |

`gate sim` on seed 7 returns `children` (three handles), `days: 14`,
`posts: 659`, per-child day and post counts, `keystrokes` / `typed_chars` /
`paste_chars`, `challenges`, `relogins`, `restarts`, `degraded_windows`,
`lease_conflicts`, `quarantined_steps`, and `criteria` as six booleans, all true.
It also returns `evidence_scope: synthetic_model`, `runtime_binding_available:
false` and `live_gate_satisfied: false`. Read those three fields before quoting
any number from the report: they are the difference between "the model behaves"
and "the platform allowed it".

## 4. Proxy pool handling

`tools/xguerrilla/proxies.yml` is the live pool: sixteen endpoints, one sticky
slot each, read from the environment or the file **where the harvest runs**. It
is gitignored, it is never committed, and it is never rsynced — a copy on a
second host is a second credential to rotate.

`net-check` prints the masked form by default:

```
{ "count": 16, "ok": true, "revealed": false,
  "slots": [ { "port": 8309, "slot": "<pool>-00", "user": "T3***" }, ... ] }
```

`slot` and `port` are enough to bisect a slot in a ticket, a log or a pasted
session. The address block and the provider username are not, and two octets of
an address still identify the pool — an earlier revision printed
`170.124.x.x` and was still inventory. `--reveal` is for the command that is
about to bind a child to a slot. Slot names carry the pool tag, so scrub them
before a log leaves the box.

The committed `proxies.example.yml` is a template in the strict sense: sixteen
inventory lines carrying `${BART_USER}` / `${BART_PASS}` and RFC 5737
documentation addresses, no purchased endpoint and no vendor name.
`test_template_exists_and_is_not_the_live_pool` fails if any host falls outside
the documentation ranges or the vendor name appears. Its ports therefore say
nothing about the live allocation — read `proxies.yml` for the real order.

## 5. Running the suite

Laptop:

```
cd ~/Mastermind/macro && PYTHONPATH=. /opt/homebrew/bin/python3.12 -m pytest tools/xguerrilla/tests -q
```

Worker box, after the sync in section 7:

```
cd ~/macro && ~/.venvs/xg/bin/python -m pytest tools/xguerrilla/tests -q
```

Both boxes: **294 passed, 0 failed, 0 errors, 0 skipped** (34.8 s laptop, 16.4 s
worker box). The skip that used to appear was `test_live_pool_is_gitignored`
running on a machine that was not a repository; making `~/macro` a real `git
init` repository turned it into the assertion it was written to be.

`tests/test_ci_pack.py` at the repository root is a separate, much slower
surface: 240 tests, 0 failures, 639 s, unchanged by harness work.

## 6. What the live pilot still needs

The refusal in section 1 lifts when an adapter composes the harness with the
existing owners rather than replacing them:

- `engine/marketing/reply_export.py` — `export_approved`, `claim_for_desktop`,
  `ingest_receipts`: the approved item, its original holder and the observed
  result.
- `engine/marketing/reply_queue.py` — the incumbent critic, conversation-owner,
  expiry, mode and pacing contracts.
- `engine/marketing/outbox.py` — parent-post construction and queueing.
- `engine/marketing/health_monitor.py` — `halt_record` and `is_halted`. A halt is
  a veto; the absence of one is not permission, so the adapter has to bind the
  canonical account and profile identity as well.

Two source gaps stay open and are named in `FINDINGS.md`: `textdrift.audit` is
untested below a window of three posts, and the GUI backend in `drivers.py` has
never been exercised against a real browser.

Once the adapter lands, the pilot runs exactly as the model describes it: three
children, fourteen days, per-day evidence in the shape `PILOT_PLAYBOOK.md`
specifies, judged against the six criteria in `GATE.md`. Nothing about the model
timings transfers without that run — the sim proves the accounting, not the
platform.

## 7. Syncing the worker box

The worker box has no GitHub credentials and no remote; `rsync` is the only
transport.

```
rsync -az --exclude __pycache__ --exclude '*.pyc' --exclude 'proxies.yml' \
  tools mini1:/Users/mini1/macro/
```

The sync must carry the repository's root `.gitignore` and must exclude
`proxies.yml`. Syncing `tools/` alone drops the root ignore file, and a
`git add -A` in that state commits the live credential pool into the worker's
local history.

## 8. Incidents

Record incidents and source evidence with the existing GitHub / Agent OS owners
and reconcile the original action there. `ESCALATIONS.md` explains why the
superseded local escalation-folder design is not an active retry queue.
