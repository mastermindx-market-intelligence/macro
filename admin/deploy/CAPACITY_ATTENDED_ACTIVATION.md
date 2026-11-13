# Attended Capacity Router activation

This is the bounded deployment procedure for Macro PR #11194. It uses the
incumbent `ai.mastermind.fabric-router` job and `state/reload.lock`. It installs
no service, scheduler, alternate router, or retry owner. The assigned operation
retains custody until the source, runtime and dashboard receipts agree.

## Preconditions

Use the original managed workspace and mutation carrier. Release the qualified
source through the repository's controller, then deploy the admin through the
existing VPS deployment owner. Preserve the VPS's generated working files.

Stage from the exact live release with `stage_capacity_observer.py`, including
`--prepare-controls --prepare-maintenance`. Recheck the installed plist,
gateway, all preserved native files, configuration digest, candidate overlays,
and the staged writer/maintenance preimages immediately before activation.
A changed preimage requires reconciliation; never overwrite a live writer.

Record the job label, loaded PID and start identity, working directory, loaded
exit timeout, runtime generation, effective configuration digest, active work,
and current observer epoch. The qualified installation had a loaded 60-second
launchd exit timeout while its disk plist specified 1860 seconds. Writing the
plist does not change the running supervisor definition. The native application
has a 960-second graceful timeout and a 900-second upstream admission budget.

Verify no existing reload transaction or unresolved configuration receipt. Take
the incumbent model guard's lock to settle earlier guard invocations and inspect
any already-running peak/reload/watchdog children. Protect unrelated canary jobs.
Do not disable a loaded job as a substitute for a restart fence: the real launchd
fixture proved KeepAlive can still respawn it.

## Exact transaction

1. Acquire the existing shared configuration lock and incumbent model-guard
   lock. Create the private evidence directory and record each intended file
   effect with its rollback preimage before applying it. Install the prepared
   reload/watchdog and configuration-writer adapters only against their recorded
   preimages, and verify installed hashes. Enroll all four existing owners before
   opening the maintenance journal so interruption cannot leave an older writer
   that ignores the durable marker. No router signal occurs during enrollment.
2. Settle any invocation that began before installation; disk hashes alone do
   not prove old processes have finished. Recheck the original PID and config,
   atomically acquire the existing reload directory, and write a private, fsynced
   `maintenance.json` with schema `mastermind.capacity_router.maintenance.v1`,
   operation ID, target job, source refs, old PID/start identity, base/candidate
   paths, configuration and file digests, candidate service SHA-256, phase and
   recovery action. The reload/watchdog fences override their ordinary 180/120-
   second stale thresholds. Shared configuration writers refuse while this marker
   exists, including after the activating process loses its flock. The model
   guard's write and subsequent kickstart are inside the same writer scope.
3. Install the qualified startup guard into the retiring service source by exact
   preimage comparison. The running process keeps its already loaded code; the
   receipt must distinguish that from the guarded disk postimage. The guard
   targets only the exact launchd job and permits a starting candidate only in
   `STARTING_CANDIDATE` or `VERIFYING_CANDIDATE`, at the recorded canonical path
   and exact service hash. Unknown/corrupt markers hold the targeted startup.
4. Record `DRAINING_OLD`, recheck the old process identity, and send one ordinary
   SIGTERM directly. Do not use `kickstart -k`, bootout, a second signal, or a
   time-triggered kill on a still-draining process. Observe completion and exit.
   The fixture proved this signal path preserves an active stream even when the
   loaded supervisor timeout is shorter. An exceeded bound remains held for
   diagnosis; it does not authorize destructive escalation.
5. Observe any automatic KeepAlive child exit before opening a listener. Require
   the original PID gone, no router listener, and the old job stopped. Preserve
   the retiring epoch's final real VPS snapshot through the existing
   `capacity_history.record` owner before the new epoch replaces it. Record the
   snapshot digest, sequence, ledger counts and an actual completed-request key;
   do not invent observations or replay equal-sequence ingress. Then unload that
   stopped job once. Install the candidate working directory in the
   same plist against its preimage; retain all other settings. Set
   `STARTING_CANDIDATE` and bootstrap the same label once.
6. Record `VERIFYING_CANDIDATE`. Verify the actual PID/start identity, canonical
   release and module source, loaded exit timeout, single loopback listener,
   native runtime manifest, preserved gateway, effective config digest, new
   observer epoch, and fresh VPS projection. A health response alone is not
   sufficient. Once the listener may have opened, treat traffic as admitted.
7. After native identity and telemetry are verified, restore the retired source
   only against its recorded guard postimage and only while its old job remains
   unloaded. Mark native activation complete, then atomically rename this
   operation's entire reload directory into its evidence archive and fsync the
   state directory. This removes the marker and its lock directory together;
   there is no aged-lock cleanup window. Read back the receipt and release locks. Observe the next normal guard/watchdog cycle
   and confirm no surprise restart or stale configuration write.

The shared writer does not interpret a terminal maintenance phase as permission
to write; only the owning transaction's removal of the marker resumes writers.
The startup guard allows terminal phases so recovery can bring up the verified
job while the owner finishes its records. These are separate boundaries.

## Failure and rollback

An interrupted signal, unload, bootstrap, apply or journal transition must be
reconciled at its original target before another effect. Leave the maintenance
fences and exact return action in place. Never blindly rerun the procedure.

There is no automatic 60-second rollback. If the candidate may have admitted
work, first move the journal to a phase that fences candidate restarts, verify
its PID, and perform the same single-signal drain. Only after its exit and
listener absence may the stopped job be unloaded and the qualified base
restored. Prove base compatibility with the current configuration; do not reset
`routes.json` from an old backup and erase legitimate changes. A needed rollback
must be qualified for the observed state before it is executed.

## Production acceptance

Use the authenticated dashboard through its real edge proxy. Verify the full
exported topology, live request updates, history, intelligence, settings and
mobile layout. Check SSE reconnect, history retained across the actual admin
restart, and native/VPS epoch agreement. Validate and apply one explicitly
reversible observation-cadence change through the UI, confirm the native
receipt and effective revision, then restore the original cadence through a new
explicit transaction. This does not authorize route, account, quota or spending
changes. Genuine existing consumer traffic must be visible; fixture traffic
alone is not production proof.

Persist the release, deployment, native transition, browser and control receipts
in the existing observatory/evidence records and link them from the existing
Executive Capacity Fabric workstream. Keep its broader program waves unchanged.
