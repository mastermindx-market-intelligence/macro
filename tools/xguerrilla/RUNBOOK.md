# xguerrilla source and simulation runbook

**Runtime binding is unavailable.** This harness does not yet bind a canonical
account, approved action, original holder, settled receipt or incumbent profile
owner. Its public runtime interfaces refuse before their first operation.
A successful source test or simulation does not activate the harness.

The accepted [masterplan](../../research/agentic_media/X_GUERRILLA_NETWORK_MASTERPLAN.md)
sections 26.2–26.3 keep lifecycle, exclusive ownership, approval and health with
the existing owners. No local SQLite row, generated lease token, persona handle,
proxy slot or backend choice grants those authorities.

## Supported behavior

| Surface | Current result |
| --- | --- |
| CLI status, degrade, recover | Exit 3; runtime_binding_unavailable; no state database or health row |
| CLI snapshot, restore, verify | Exit 3 before profile access |
| CLI shadow without --dry-run | Exit 3 before reading steps or importing a driver factory |
| CLI shadow --dry-run | Describes explicit step input; checked remains 0; no driver or readiness proof |
| CLI help, personas, net-check | Descriptive inspection only; no account or runtime admission |
| Public LeaseStore, Supervisor, Store/ProfileStore and profile wrappers | Refuse before constructing a local authority or accessing a profile |
| Direct selector check/quarantine interfaces | Refuse before driver observation, capture or ledger I/O |
| choose and both real drivers' start/stop | Refuse before backend probing, browser import, directory creation, process launch or cleanup |
| Explicit Simulation classes/functions, FakeDriver and pure helpers | Synthetic model tools only; no incumbent authority or live gate proof |

There is no environment variable, approval token or force flag that enables the
unbound runtime. Do not treat an unavailable start as a reason to switch drivers,
restore a profile, kill a process or create a replacement holder. In particular,
stop is not a safe way to clean up a profile whose original owner is unbound.

## Existing integration owners

The relevant existing source interfaces are:

- engine/marketing/reply_export.py: export_approved, claim_for_desktop and
  ingest_receipts preserve the approved item, original holder and observed result.
- engine/marketing/reply_queue.py: the incumbent critic, conversation-owner,
  expiry, mode and pacing contracts.
- engine/marketing/outbox.py: the incumbent parent-post construction and queue.
- engine/marketing/health_monitor.py: halt_record and is_halted supply a veto.
  Absence of a halt is not positive permission.

A future adapter must actually compose those contracts with the canonical
account and profile identity. Importing these modules, assigning a persona name
or finding a browser executable is insufficient. No general profile allocator
is supplied by the reply interface. Preserve original uncertain effects and
live writers; do not replace them with a new local queue, lease or health row.

## Synthetic regression work

SimulationLeaseStore, SimulationSupervisor, SimulationProfileStore and the
simulation_* selector functions preserve model algorithms for explicit
temporary fixtures. They are not alternate runtime interfaces. Supply synthetic
persona mappings to SimulationSupervisor; it never discovers a persona folder.

The fake pilot imports the simulation state classes and constructs FakeDriver
directly. It cannot use choose to activate either real backend. Its report and
every gate JSON document identify evidence_scope=synthetic_model,
runtime_binding_available=false and live_gate_satisfied=false. Model ok=true
is not a real fourteen-day result, readiness, platform permission or acceptance.

Run only the selected synthetic cases appropriate to the change from the
repository root. The shared fixtures generate temporary synthetic proxy/persona/link inputs
and use the actual parsers. The public proxy example and Git ignore/index policy
are checked separately, without reading or creating the private pool. The
text-drift proof remains separate and should not be rerun without a meaningful
change. GATE.md explains the model's limits.

## Incidents and prospective acceptance

Record incidents and source evidence with the existing GitHub/Agent OS owners
and reconcile the original action there. The superseded local escalation-folder
design is not an active question or retry queue; see ESCALATIONS.md.

The real pilot still needs the accepted masterplan's fixed cohort, permissions,
account/profile ownership, actual observations, heartbeat/health evidence,
restart and outage settlement, and full acceptance period. Its original product
journey is retained as prospective work. PILOT_PLAYBOOK.md contains historical
planning material; no commands there override this unavailable-runtime boundary.
