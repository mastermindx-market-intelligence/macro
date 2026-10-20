# Fixed runtime qualification

These helpers prepare and observe one trusted engineering canary for the Research Factory. They do not admit research candidates or activate the dormant general transport. `source_manifest.json` binds the reviewed bytes; `build_capsule.py` packages them as data and reads the existing transport from `engine/research_codegen/transport.py`. There is no second transport implementation here.

The fixed sequence checks Docker's anonymous credential-lookup behavior against an owned fake API, acquires the pinned public runtime archive, installs the six-file runtime bundle with bounded settlement, prepares the exact image if its absence is confirmed, and runs one harmless probe. One 900-second clock and 64 KiB raw-plus-return envelope cover the physical sequence. Installation keeps its rollback reserve inside its phase. Refused or uncertain operations never advance or replay.

`canary_carrier.py` has no default execution entry point. Its caller must hold an actual, separately admitted commission and the exact source hashes. It uses existing noninteractive privilege only and records uncertainty if supervision does not settle. Hashes, labels, source files and caller-supplied JSON do not authenticate an owner or grant privilege.

**The fixed probe is executable payload. Never import it on the host.** The capsule builder compiles it for syntax only. The admitted fixed container path supplies its minimal environment and resource policy. Tests substitute physical effects; a passing source test is not a runtime receipt.

`verify_canary_return.py` checks the original parent's retained bytes, source and commission identity, phase settlement and capture accounting. Passing that gate still requires parent review. It is not independent host attestation or full S01–S04/Q01–Q03 acceptance. Candidate admission and containment qualification remain false.

The original contracts operation remains quarantined as `EFFECT_UNKNOWN`; none of these helpers retries, reads or adopts it. GitHub protection settings remain a documented gap under Chris's administrator ruling. Execution uses an owned anonymous Docker config and a clean environment, separate from publishing credentials.

`host_identity.py` is a separate pure source-preparation helper for a future host observer. It joins OCI state with internal runsc metadata for one exact single-container identity, returns a closed redacted declaration, and keeps host observation, helper census and cleanup proof false. It has no file or command access and is excluded from the fixed canary capsule. See `research/research_factory_codegen/2026-10-14/HOST_IDENTITY_SOURCE_CONTRACT.md` for the immutable source contract and outstanding physical requirements.

`proc_observer.py` prepares the next bounded observation step. An explicit call observes one authorized PID through a held Linux pidfd and proc directory, brackets fixed-file reads with liveness checks, verifies stable start ticks, and returns only hashes and narrow process facts. It does not scan processes, signal them, read credentials, resolve cgroup paths or establish a runtime/container association. Host/procfs trust, namespace identity and an outer deadline remain caller obligations. It is also excluded from the fixed canary capsule. Its ordinary tests use syscall fixtures; the separate owned-process smoke is opt-in on a later qualified Linux host. See `PROC_OBSERVER_SOURCE_CONTRACT.md` in the dated research directory.

`cgroup_observer.py` prepares a future bounded host resource observation. It reads only a caller-bound cgroup hierarchy and leaf membership through held descriptors. Its consumed independent review led to explicit units, source depths and incomplete-hierarchy flags, plus suppressed incidental error context. The repaired source passes 64 fixture checks; no host observation or effective enforcement is qualified. The review task is accepted, while the successor source has root verification only. It is excluded from the fixed canary capsule. See `CGROUP_OBSERVER_SOURCE_CONTRACT.md` in the dated research directory.


## Mount-table source preparation

`mountinfo_contract.py` parses bounded caller-supplied mountinfo and returns only a matching declaration. It does not read host mounts, authenticate the host namespace or admit execution. Original Fabric source had eight reproduced contract failures; root's separate derived repair passes80inert checks. Original return remains unaccepted and unchanged. See `research/research_factory_codegen/2026-10-14/MOUNTINFO_SOURCE_CONTRACT.md`. This helper is excluded from the fixed canary capsule.

## Fixed workload source preparation

`fixed_workload_plans.py` accepts a case ID (`w01` through `w07`) and inert bytes
matching that case's literal length and SHA256. It returns the existing
`TransportPlan` with fixed identity, image, minimal environment and resource
limits. It never reads, imports or runs the workload. Its description exposes
digests and outstanding obligations, with execution authorization, candidate
admission and containment qualification all false.

`fixed_workload_engine.py` connects those plans to the existing fixed transport
lifecycle. It has no CLI or default executor. A separately commissioned caller
still owes the installed runtime, trusted host/resource mapping, helper census,
outer supervision and physical cleanup observations. When such a caller injects
an executor, the frontend reserves 30 of its 120 seconds and 4KiB of its total
64KiB capture for same-container cleanup. It exclusively creates a receipt
before Docker effects and persists the known container ID before start. An
uncertain create cannot be replaced or guessed, a prior receipt prevents reuse,
and a permission refusal freezes subsequent commands. Cleanup success preserves
any workload failure. There is no automatic seven-case campaign or retry loop.

The constructor requires an explicit `transport_path` and uses the incumbent
loader to verify and compile the exact pinned bytes. The execution plan,
orchestrator and absence parser come from that verified module; descriptions
and every receipt phase record its digest. The pure plan factory declares the
required digest without claiming it observed source files. Host binding values
are checked and copied before effects, and operation identity is read-only.
Direct create calls require the frontend's exclusive receipt and CID sink.
The longest cleanup path has four seven-second command ceilings within the
30-second reserve; an admitted caller still owes external supervision of blocked
I/O and executor settlement. This frontend does not supply cross-process custody
or authorize a replacement attempt under a new receipt path.

These two helpers are excluded from the frozen v4 canary capsule. Their tests
use inert source bytes and fake Docker responses; source success does not
qualify the host or grant physical execution.
