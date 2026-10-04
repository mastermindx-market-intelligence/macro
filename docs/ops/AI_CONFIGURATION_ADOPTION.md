# Shared AI configuration: publication is not process adoption

Status: source implementation plus integration contract; BUILT_NOT_PROVEN.
Program: WS:EXECUTIVE-CAPACITY-FABRIC.
Source operation: vps-config-adoption-20260916-sol-001.
Source base: Macro bb02c526c4809564338f2a7208e063dbe86bc476.
Procedure: Mastermind f590c068880dbb848bda90b80b73dbcb6688d6fc, Skillpack 1.0.1.

## Outcome

A reviewed model or routing change must become an identifiable production input,
then an adopted process configuration, then a proven consumer result. Those are
three different facts. A changed file or a successful deployment is not proof
that a long-lived process abandoned its older model configuration.

Reuse existing GitHub configuration publication, deployment, runtime, Provider
Control and Capacity owners. Do not add a key-copy daemon, second router, quota
store, scheduler or source-of-truth service. Native OAuth material stays with its
approved native executor; a remote consumer receives results, not that material.

## Current source facts

- admin/github_config.py commits supported config.yml edits through the existing
  GitHub Contents path; its documented VPS pull mechanism transports those bytes.
- app/main.py already distinguishes the imported process commit from the current
  checkout commit in /api/health. That boundary must remain intact.
- lib/config.py deliberately caches config.yml for the process lifetime. Existing
  explicit cache clearing remains possible, but this feature never invokes it.
- W0 #7179 protects opted-in provider construction; W1 #7185 is a separate held
  Brief consumer. This slice neither changes their branches nor activates them.

## Implemented observation

The existing loader retains the SHA-256 of the exact bytes that produced its
cached object. There remains ONE cache. load(), object identity, cache_clear(),
cache_info(), cache_parameters() and the uncached compatibility call remain.
No model, provider, environment, service, queue or credential is changed.

The existing /api/cost response adds configuration_adoption. It observes only an
already-imported lib.config belonging to the same admin source root; otherwise
it is null. This avoids importing the dotenv bootstrap for a diagnostic.

The closed observation names config.yml, observation time, loaded/installed byte
digests and current_process_source_snapshot scope. It contains no config values,
paths, account names, environment values, prompts or model output.

States are diagnostic, NEVER lifecycle or routing authority:
- NOT_LOADED: this process has no loaded snapshot; inspection does not create one.
- MATCHING_SOURCE: installed and loaded input BYTES match, not effective settings.
- SOURCE_CHANGED: file bytes differ; the original loaded object is retained.
- SOURCE_UNAVAILABLE / SOURCE_TOO_LARGE: no trustworthy installed-byte observation.
- SOURCE_CHANGED_DURING_OBSERVATION / SOURCE_ROOT_CHANGED: mixed-source evidence.
- OBSERVATION_UNAVAILABLE: bounded unknown, never a healthy/ready fallback.

The observer refuses non-regular files and bounds reads to 2 MiB. Digests detect
same-size edits even when file timestamps are preserved. Existing response-cache
behavior is unchanged; use observed_at when judging freshness. The existing
force=1 read refreshes the response, not the configuration or process.

## Coverage ceiling

MATCHING_SOURCE does not mean that other configuration files, environment or
credentials changed. It does not inspect dictionary mutations, runtime overrides,
retained configuration references, provider descriptors, another process, a worker
or a remote host. It does not
validate YAML semantics, API entitlement, model support, quotas or a release.
Even a loaded empty YAML source can truthfully have matching input bytes.
These exclusions are machine-readable in not_covered and must not be removed by
an aggregate dashboard. Do not label this observation 'fleet synchronized'.

A response from the admin process is NOT a receipt from macro-api, a nightly
process or a native worker. Those owners must eventually expose their own
qualified observations through their existing authenticated return paths.

## One platform, distinct execution and authority

Product inference uses approved inference transports and per-consumer budgets.
Native development/research uses qualified native executors and their credential
custody. They share eligibility, model suitability and capacity governance, not
an interchangeable bearer credential or unrestricted tool set.

Current Mastermind ceo_request.py fixes ACTOR=ceo-sol and two bounded execution
profiles; executive_ceo_ingress.py v2 adds automated request identity, NOT arbitrary
website-service admission. A website request may not inherit Chairman/CEO auth
because it can construct that frame. Service-to-fabric admission must be qualified
inside the existing admission owner with its exact consumer, purpose and scope.
No new public submit endpoint or alternate lifecycle is introduced here.

## Local-to-VPS change protocol

1. Publish reviewed model/routing configuration through its existing repository
   owner. A local uncommitted edit is not a production release. Keep source-code,
   model-policy, workload-policy and account-enrollment identities distinct.
2. Transport the accepted release through the existing deployment mechanism.
   Record installed bytes independently of the process that is still serving.
3. At a safe existing lifecycle boundary, the deployment/runtime owner explicitly
   adopts the new source. Do not clear another process's cache or restart an
   active worker from this diagnostic endpoint.
4. Obtain that process's readback; compare like source identities only. Include
   observation time and unknown states. Then verify the actual consumer's result.
5. Retired account generations must be handled by the existing Provider Control
   and Capacity owners. A model/config digest cannot revoke a token or cancel an
   in-flight request. Do not add or delete guessed account slots from reported totals.

Native executor replicas sharing one provider account must share its real quota
resource; do not add their limits together. Fable reservations must be enforced
by admission/eligibility, not a preferred ordering that falls back to Claude.
The native pool wrapper observed on Mac Studio points at the incumbent Fable kit;
that local wrapper is not a qualified VPS service API and must not be copied with
private provider homes to create another balancing system.

Compatibility: lib/config.py is also in the existing H0 material source closure.
This source change does not modify the installed/frozen H0 generation. Any future
adoption of these bytes needs that release owner's ordinary exact-source review;
never update a signed/pinned receipt in place or replay the completed H0 transfer.

## Acceptance and rollout

Source proof: tests/test_config_adoption.py exercises the actual loader and
existing HTTP /api/cost handler. The observer must not initialize or reload the
cache; an unauthenticated request must still be refused before observation.
Faults include replacement during read, preserved timestamps, missing/oversized/
non-regular sources, changed roots, private exception text and retained references.

The implementation has no dependency on unmerged #7179/#7185 source. It can be
reviewed independently, but its source publication is not permission to update
installed H0 artifacts, restart a service or change routing. CI-runner recovery
is explicitly outside this operation; only this feature's test command is added
to the existing code-gated unrun-brain-desks job.

Before deployment: independent review of the loader compatibility and HTTP
privacy boundary, normal concluded source checks, and release-owner approval.
For production proof: observe the actual target process at an approved release,
make a harmless reviewed configuration update, and show installed versus loaded
state before and after that owner's normal adoption operation. No force reload,
credential change or live-provider request is authorized by this document.

Broader integration remains: #7185 SDK compatibility repair on its retained
writer when permitted; qualified service admission and real Capacity reservations;
one real VPS-originated request and returned result consumed by its feature.
The current blocked SDK edit and browser-capture action are not retried through
this independent branch or delegated to another actor as a workaround.
