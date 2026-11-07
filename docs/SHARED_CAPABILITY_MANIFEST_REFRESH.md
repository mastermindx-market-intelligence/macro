# Shared capability-reference manifest refresh

Part of [Mastermind #983](https://github.com/mastermindx-market-intelligence/Mastermind/issues/983), shared-model-pool-control-20261105-c4. Mastermind source companion: [PR #2109](https://github.com/mastermindx-market-intelligence/Mastermind/pull/2109).

## Existing consumer, repaired behavior

`engine.neuralweb.capability_broker` already owns `config/capability_manifest.yml`: capability identifiers, reference names and lane permissions. `engine.neuralweb.key_pool` consumes the same source. Neither this repair nor its manifest reader creates a pool registry, provider client, credential store or lifecycle.

The capability broker previously retained its default-root manifest for the process lifetime. Editing/removing a reference or lane grant could therefore remain invisible to subsequent calls until process restart. The key pool separately loaded the same file with different read behavior.

Both callers now use `capability_broker.load_manifest_source` while retaining their own exact `_manifest_path(root)` selection. Each call opens and reads the current source with bounded bytes and regular-file checks, then rechecks descriptor/path identity after parsing. There is no retained grant cache or last-good fallback. Missing, invalid or moving source returns the existing safe `{}` shape. Existing public NEVER-RAISE behavior and successful reference/lane resolution remain intact; this repair does not authorize a previously denied caller.

Fresh data is allocated for each call, so mutation of a returned dictionary cannot change the next read. Inode, size, modification time and change time are checked before/after reading and after parsing. No clock-only cache test is used. Atomic replacement during an observation refuses that observation; a later independent observation can consume the new source.

## Source grammar and bounds

The current manifest is explicit `capability_manifest.v1` YAML with a list of capability rows. The reader keeps existing additional source metadata. A file must be regular and at most 1 MiB. It refuses duplicate mapping keys and capability IDs, non-string mapping keys, nonfinite numbers, malformed UTF-8, excessive depth/node counts, unsupported YAML constructors and alias/merge indirection. Current published source has no alias/merge constructs.

Capability IDs are bounded nonempty strings. A present `secret_ref` must be a reference NAME, never an inline credential. The reader does not dereference the environment, access provider auth files, hash a private credential, issue API calls or change a secret. Failure logs use fixed text rather than YAML excerpts, file paths or exception contents.

## What this does not prove

This is configuration-read correctness for new observations, not transactional key rotation, global capacity accounting, a physical subscription identity proof or admission of every model pool. Already admitted work remains with its original operation/lease/account owner. The original configuration/credential publisher still owns approved reference updates, private provisioning, drain, generation retention and rollback. A reference changing does not authorize replay or failover of an uncertain provider request.

The historical key pool's seven Claude capability slots and current provider slots are unchanged. This repair does not expand the legacy selector into a second generic model pool; the existing Fabric/application integration retains that migration.

## Verification recorded

The actual checked-in manifest was read through both repaired callers: schema `capability_manifest.v1`, 14 capability rows, equal documents. No credential value was resolved and no provider or ledger effect occurred. Source diff was self-reviewed. No discretionary test suite was run under the current Chairman instruction; normal hosted checks remain unchanged. Installation and real rotated-credential behavior are unproved until the original release/credential owners produce those receipts.
