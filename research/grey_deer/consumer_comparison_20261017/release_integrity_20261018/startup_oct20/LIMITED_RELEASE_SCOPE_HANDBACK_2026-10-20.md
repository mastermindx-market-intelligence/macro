# Limited release-scope handback — 2026-10-20

Reviewer: `/root/release_scope_judgment_oct20`. Assignment: independent architectural/adversarial review for the existing Risk Radar release; no implementation, provider use or production effects.

## Ruling

**No additional startup or production qualification was obtained in this child.** The completed observations support the existing bounded static characterization, and a finite next release-proof sequence. They do not certify a harmless application restart, the final release archive, or backend-to-user acceptance.

Root reports that the four reviewed test files are now on Mastermind #1610 at `7b5ccfffef4e90b89496751dd7bc0f55b711ed25`, and that its required CI passed. Those are parent-supplied current observations, not independently retrieved by this child. The production helper is reported unchanged from `797c760f3e18eb6993579f56986103de9d9fdcb4`. Source integration can proceed when root's actual source gates allow it; production acceptance remains separate.

## Completed evidence

The full `FULL_RELEASE_FIXED_SOURCE_REVIEW_2026-10-18.md` was read. Its 17,614-byte identity, SHA256 `fc2cd6f40727d0535d812eee2d9469e13cd96bc658e528a919a363eec3109924`, is inherited from the parent checkpoint; this child did not recompute that digest. A completed local standard-library read of `full_release_fixed_source_focus_20261018.json` confirmed its 76,602-byte size and structure: four dependency records, fourteen dynamic contexts and two root-import inventories. The inherited extract SHA256 is `ede83fc78f739731d6b42466457274e3c9b030860a1175ffe484c329e07af902`; it was not recomputed here.

The prior review binds candidate `797c760f3e18eb6993579f56986103de9d9fdcb4` against the dated installed comparison `732cf7be88e7159b4995a8885fbd381cd1484e3e`. It records 180 reached changed source paths, 29 module-lexical import statements and 160 function-body import statements in `app/main.py` and `app/web.py`. All fourteen dynamic sites are function-local. These are static catalogue facts from that review, not a fresh production observation or a realized call graph.

The strongest counterexample remains decisive: **a function-local import may execute during an application startup handler.** The prior inventory names `_startup_flags`, `_start_scheduler`, `app.scheduler` and governance imports, but lacks their complete startup registration, effective guards and invoked call chain. Similarly, a file-loader call executes its target's top-level code; a loader being inside a function does not establish that it is unreachable during startup. A comment or function name does not prove absence of effects.

The supplied dependency diff has no changed package/version/hash lines in the two gate locks; the new research producer lock explicitly does not establish installation. This narrows one source concern. It proves neither installed-package realization nor successful use of that environment by the production service.

## Interrupted request and effect accounting

One `functions.exec` batch requested two independent operations:

1. A cloud `exec_command` read of the Craft common and reviewer reference files.
2. A Studio Direct `start_process` call containing a standard-library Python script. It requested only `git show` at the fixed `797c760f...` commit, `ast.parse`, and extraction from these six files: `app/main.py`, `app/scheduler.py`, `control_plane/executive_incident_composition.py`, `ops/executive_os/provider_readiness.py`, `bot/overnight.py`, and `control_plane/worker_adapter.py`.

The batch returned **“aborted by user after 3774.3s”** without either operation's output, a process PID, an execution status, or a receipt. The call did not supply usable new evidence. Because output publication was after `Promise.allSettled`, the child cannot infer which nested operation completed.

The Studio script, if dispatched, could have written only `/tmp/rr-oct20-release-startup-source-extract.json` after its fixed-source reads. That extract's existence, completeness and process completion are **unknown**. No first-party imports, application startup, scheduler, service operation, provider/model call, live-data write, Git mutation, or deployment was requested. This is a transport/request uncertainty for a source-read and possible temporary extract, not evidence of an uncertain production mutation. The request was not replayed. Root instructed the child to stop and use completed observations only.

## Smallest remaining qualification sequence

These are proposed checks for root's existing release owner, not new authority or approval requirements.

### 1. Freeze one real release candidate

After normal source integration, bind the exact operation's merged commit and eligible deployment archive. Reconcile any functional source delta between reviewed `797c760f...` and that release. The four test-only changes reported at `7b5ccfff...` leave the production helper bytes intact, but a later queue merge can incorporate other functional changes. Do not relabel the earlier static catalogue as proof of a different full archive.

The smallest lawful release option is the existing exact-commit deployment path after its actual gates clear. An arbitrary newest default-branch snapshot or manual replacement of only the consumer files is not a justified way to evade the complete-archive question.

### 2. Resolve the bounded startup-effect slice

Obtain fixed-source evidence for actual lifecycle registration, `_startup_flags`, `_start_scheduler`, scheduler construction/job registration and effective governance/serve-only guards. Follow only positively invoked startup callees and module-level initialization needed for that path. Resolve the finite descriptor and `_RUNNERS` bindings and file-loader target bodies when a real startup or acceptance caller reaches them. Broader deferred endpoints need not become a full-fleet investigation.

Accept this step only when the actual configured restart path can be described as an ordered set of effects and refusals. Preserve unproven paths explicitly. “All imports are local,” a green health endpoint, and a test fuse that bypasses the affected path are insufficient substitutes.

### 3. Rehearse the full archive in an isolated matching runtime

Use the actual deployment helper and release archive against temporary receiver/runtime roots, with live network, credentials, books and provider actions unavailable. Bind the interpreter, platform and transport implementation. Confirm the relevant startup and failure paths under declared settings, complete eligible source replacement/restoration, retained runtime/cohort state and truthful stopped-service refusal when restoration cannot be completed. Root's existing meaningful helper tests remain reusable evidence; rerun or extend only for a concrete runtime or final-archive difference.

A passing isolated rehearsal closes only what its effect boundaries observe. It does not prove current installed versions or that production startup effects have been reversed by code rollback.

### 4. Make the reserved production decision concrete

Before presenting the existing reserved release decision, bind the exact commit/archive, current installed comparison, effective service command/mounts/settings, expected startup effects, rollback behavior, availability risk and the already-verified rehearsal. Reuse dated observations where still valid, refreshing only material facts that can have changed since the 18 October VPS read. No new approval is needed for the independently permitted source investigation or rehearsal; the actual production effect retains its current owner and constraint.

### 5. Close the real consumer path after an authorized installation

Verify installed source identity and service health, then the dated future-source/null behavior at the backend and the actual authenticated consumer. A warning must retain its source date, uncertainty and advisory boundary through the UI. Record actual delivery and user-visible interpretation; source merge, test count and service health alone cannot close this gate. Numerical allocation and execution remain with Portfolio/Prophet policy owners.

## Handoff and stop

Root's next action is normal source integration using its completed CI evidence, followed by the smallest source read that establishes startup registration and guards for the final candidate. The unreturned optional extract must not be treated as evidence or blindly rerun. No full-fleet certification, new infrastructure system, policy change, source-custody transfer or production permission is implied.

This child is terminal under the parent's explicit finish/STOP instruction. No watcher or background continuation was created. Parent remains accountable for integration, release qualification and final programme acceptance.
