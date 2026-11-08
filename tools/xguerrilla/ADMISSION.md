# Admission chain — six refusals, in cost order

`admission.py` decides whether a cohort may be seated on one box. It is the gate
that runs **before** a browser exists, so that a cohort which could never be
seated is refused in text rather than discovered as a wedged box.

This document exists because the module is deliberately half a feature: the gate
logic lives here, and the one call site lives in the runtime. Two copies of a
check like this drift within a week, so there is exactly one implementation and
the call-site contract is written down instead of reimplemented.

## The chain

Each stage emits an artifact; the next stage refuses if the previous artifact is
absent. The artifacts are digest-linked (`parent`), so a chain with a stage
removed cannot be reassembled later and presented as complete —
`verify_chain()` re-checks a stored chain and refuses on a hole, a reorder, a
link naming a stage that does not exist, or a hand-edited receipt.

| # | stage | refuses when | cost of finding out later |
|---|---|---|---|
| 1 | `domain` | no record, unverified, unstated expiry, expired, duplicate or empty cohort | a dead mailbox |
| 2 | `identity` | cohort larger than the admitted identity pool, no recovery owner, identity off its own domain, persona in another cell | an account nobody can recover |
| 3 | `custody` | no TOTP, no held recovery codes, no named custodian | a 2FA wall mid-run |
| 4 | `proxy` | cohort larger than the exclusive proxy pool (`net.bind`) | a shared endpoint, i.e. a burnt slot |
| 5 | `account` | account not explicitly admitted, or no account id | a profile on an unowned account |
| 6 | `slot` | cohort larger than the **measured** ceiling of the box | a wedged browser and a degraded box |

**The ordering rule.** A cohort larger than the number of admitted identities
refuses at stage 2, not stage 6. Slot-7-on-a-6-slot-box is the last link and the
expensive one; an identity shortfall is a line of text. `AdmissionRefused`
carries `stage_index`, so a caller reporting a refusal also reports how early it
fired.

## The ceiling is measured, never declared

`§26.3` says six light-profile browsers per box. That is an intention, not a
measurement. `Box.effective_ceiling(now)` returns

```
min(declared, memory_capacity, process_capacity)
```

and records which term bound it. `Headroom` is a reading taken at a stated moment
and it expires (`DEFAULT_MAX_AGE`, 900s): a box that lost 3 GB to another
application an hour ago does not inherit the ceiling it had then. A stamp that
is not a finite moment (`measurement_unstated`) or one more than
`FUTURE_TOLERANCE` (60s) ahead of the gate's clock (`measurement_from_future`)
refuses before the staleness comparison — which is itself fail-open on a bad
stamp (`nan > limit` is False) — because a measurement dated after it is used
measured nothing, and one the gate cannot date is not a measurement.

**Both heads are checked, and neither is taken on trust.**

*Memory must name its counter.* `Headroom.memory_basis` must be one of
`MEMORY_BASES` (`free_inactive_speculative`, `free_pages`, `vm_stat_reclaimable`)
or the chain refuses `measurement_basis_unstated`. This is not pedantry: a
memory-pressure gauge can print "58% free" on a box whose unused pages are 1.8%
and whose compressor holds 4.2 GiB, and a gate fed that percentage admits a
browser into swap while reporting healthy headroom. The receipt carries
`compressor_bytes` and `pageouts` alongside the verdict so a reader can tell a
healthy reading from a gauge wearing its clothes.

*Per-instance cost must be measured, not remembered.* `browser_resident_bytes`
and `browser_processes` are per profile class on this box. A constant carried
over from another machine calibrates the guard against a machine nobody measured
— and it errs in both directions, refusing admissions the box can seat while
passing the ones it cannot. Observed on mini1: instance helper counts ranged 8-16
across four profiles, well under the 28 that had been assumed.

*The reading must also cohere.* Available pages cannot exceed the total they are
part of, a process count cannot be negative or run past its own limit, and a
total of zero measured nothing. Any of those refuses `measurement_incoherent`
instead of computing a ceiling from a contradiction.

**Do not hard-code a box's number in this repository.** The descriptor value is
the output of a readback, recorded with its timestamp. For reference, assurance
measured mini1 at **1 live browser instance** on 2026-11-08T05:32Z (299 MiB
unused of 16 GiB, 4.23 GiB compressor, ~1.6 GiB per instance, and three
non-harness `xg` profiles resident); evidence in
`t_b6f30cc1/mini1_recon_20261108T053208Z.txt`. That is a data point with a date
and a capture, not a constant this module knows. When the off-harness workload
moves, the number changes and nothing here needs editing.

The stage-6 artifact records `declared`, `memory_capacity`, `process_capacity`,
`effective`, `binding`, `over_claim`, `memory_basis` and the page evidence, so an
over-claimed descriptor is visible in the receipt rather than inferred from a
degraded box.

## The box is enumerated, never assumed

A measured ceiling describes how much room a box has. It says nothing about what
else is on it. Before the ceiling is computed, stage 6 consumes an observer
snapshot — injected by the caller, never fetched by the gate — and refuses on
four codes, in this order:

| code | fires when | remedy |
|---|---|---|
| `enumeration_not_collected` | the `Box` carries no enumeration at all | run the observer sweep and inject the snapshot; an unobserved box is not admissible |
| `enumeration_wrong_box` | the snapshot's `host` is not `box.box` | re-run the observer against this box; another box's census says nothing about this one |
| `enumeration_stale` | `now - taken_at` reaches the box's `max_age_seconds` (the same 900s default as headroom); a non-finite or future stamp refuses earlier as `measurement_unstated` / `measurement_from_future` | re-run the sweep; a stale census describes a box that may no longer exist |
| `undeclared_port` | an observed port is in neither `declared_ports` nor `baseline_ports` | declare it in the registry or the resource plane, add it to the baseline allowlist, or stop it; an undeclared port is an undeclared identity |

The order matters: a box whose occupants are unknown has no meaningful ceiling,
so the census runs first and `effective_ceiling` only ever sees a box that has
been counted. An unenumerated box refuses even when its headroom measurement is
also missing — `enumeration_not_collected` fires before `ceiling_unmeasured`,
and that is the point. The refusal for `undeclared_port` names the undeclared
ports, sorted: ports are not secrets.

**Declaration is injected, not parsed.** The gate never reads the registry
document, the resource-plane declarations or the baseline file. The caller
builds two sets and hands them to the `Box`. `declared_ports` is the union of
the registry persona bindings (`binding.cdp_port`) and the resource-plane tool
declarations (`{id, host, port}`) — tooling such as the chrome-automation
bridge on 9223 is declared in the resource plane, not minted as a persona.
`baseline_ports` is the versioned stock-macOS allowlist, ARDAgent's 3283 among
them. A port in both sets is labelled `declared`: a persona binding is the
stronger claim.

**The snapshot parses strictly.** `Enumeration.from_snapshot` requires a
mapping, pins `schema_version` to `SUPPORTED_SNAPSHOT_SCHEMA` (currently 1, as
an exact integer — `1.0` is not `1`), requires `taken_at` to be a tz-aware
ISO-8601 stamp or a finite epoch number (a naive stamp dates the sweep to no
moment in particular), requires every `listeners`/`chrome` row to be a mapping,
requires every port to be an integer in 1..65535 — a string port is a shape the
contract forbids — and requires `collection_status == "complete"`. Shape
failures refuse `schema_unsupported`; an incomplete collection refuses
`enumeration_incomplete`. An empty observed set is legitimate: a box with
nothing listening has been counted.

**The receipt records the verdict words.** The stage-6 artifact gains an
`enumeration` fact: schema version, host, `taken_at`, `collection_status`,
`tool_sha256`, the observed ports sorted, and a `verdicts` map giving every
observed port exactly one of two words — `declared` or `baseline`.
`undeclared` never appears in a receipt, because it refused. `SlotGrant` gains
`enumeration_digest`, the hash of that fact, so a grant is pinned to what was
observed: a different census is a different grant, and a hand-edited receipt no
longer hashes. `verify_chain()` catches a partial edit, a hole or a reorder; a
wholesale re-forge with recomputed digests is not detectable without a
signature, which this module deliberately does not have.

## Ownership is asserted, never inferred

On the observed box every `xg` Chrome instance carries `ppid=1` — they are
launched detached (`open -na`) and reparented to init. Process parentage therefore
carries no slot information, so stage 4 binds `handle -> slot` from the pool
record and the receipt says so (`facts["ownership"] == "pool_record"`). A gate
that tried to discover ownership by walking a process tree would find nothing and
call it agreement.

## What success is

`preflight()` returns an `Admission`, and the only thing in it a caller may use to
start anything is `Admission.grant` — a `SlotGrant` carrying box, handles and slot
**names** (never endpoints or credentials). A refused preflight raises
`AdmissionRefused` and yields no grant, so there is nothing to pass to a driver.
That is what makes "fails before a browser is allocated" a property of the return
type rather than a rule someone has to remember.

## The one call site (runtime owner)

The gate is pure: records in, artifacts and a grant out. It reads no credential,
no endpoint and no browser, which is why the suite can run it on a laptop that has
never run a child. Wiring it is the runtime owner's side of the split — do not add
a second copy of the checks on the way past.

- **Pilot path.** `pilot_sim.run_pilot()` — after `config.load_personas()` has
  produced handles and before the `Report`/`SimulationSupervisor`/lease objects
  and the `driver_for` closure exist. That is the last point where refusing costs
  nothing.
- **Real runtime.** `drivers.choose.choose()` (which already refuses before
  probing) and immediately before `Driver.start(profile_dir, proxy_url, headless)`
  in `drivers/base.py`. `profiles.init(handle, slot=...)` mints the browser-profile
  slot and must not be reached by an ungranted cohort.
- **Surfacing.** `AdmissionRefused.public()` is a JSON-safe dict with `stage`,
  `stage_index`, `code`, `detail`, `remedy`. It carries no mailbox address,
  endpoint or credential (handles, domains and account ids are identifiers, not
  secrets). Map it onto the existing CLI exit-code vocabulary rather than
  inventing a new one.

Cohort pinning (`net.bind()` binding a cohort to exclusive slots) stays in `net.py`
and is called by stage 4 — the gate does not grow a second binder.

## Horizontal distribution is deferred

A gate takes one `Box` descriptor. Going wide across four boxes is a change of
descriptor and a loop over cohorts, not a redesign: `preflight()` is per-box and
has no global state. Nothing here assumes a single box stays the only box.

## Running the laws

```sh
cd ~/Mastermind/macro && PYTHONPATH=. /opt/homebrew/bin/python3.12 -m pytest \
  tools/xguerrilla/tests/test_admission.py -q
```

The suite is registered in `.github/ci/legacy-jobs.yml` (the manifest is explicit;
an unlisted suite never runs and `scripts/audit_unrun_tests.py` reds the pack).
