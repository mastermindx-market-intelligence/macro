# Options native publication custody and first adoption

Scope: Macro10285 follow-on under META6568210481 and Options6568183827.
This source is not an installation receipt. PID85040 and any pre-fence legacy
holder must settle naturally. No stop/restart, new scheduler, account change or
provider request is part of adoption.

## Shared boundary

`lib.options_publication_custody` uses the assigned Mac user's canonical
`~/optionshub-ops-wt/.git/options-hub-publication.lock`, independent of cwd,
input/output overrides and worktree. Native inspection established that `.git`
is a directory on the actual M1. The parent must already exist. The inode is
persistent, owner-checked and rechecked under a nonblocking exclusive flock.
Contention fails before client/effect work. Nested calls in the same thread join
one descriptor; a fork cannot inherit admission. There is no environment-token
admission, alternate lock path, timeout takeover or lock-file deletion.

Nightly publication holds custody around the entire run. Legacy repair holds it
around its publication entry, and direct upload also checks custody and the
pending target. Correction requires an already-held outer publication interval:
the operator must acquire it BEFORE the separately admitted exact preimage read,
call the existing correction entry under that same interval, and keep it through
the one admitted readback. Standalone correction CLI without that interval fails
closed. Read-only correction preparation remains claim/client free. The context
is not authority for a provider/read/write call; the exact existing ruling and
operation budget still apply.

The original bounded correction identity is
`oem-01a156f1-spy-20261016-correction-v1`. Its native receipt is beneath the same
canonical `.git` directory. Exclusive claim creation precedes the client/PUT.
STARTED survives process death. Acknowledgment stays held pending exact admitted
readback; only byte-length and SHA equality can mark READBACK_VERIFIED. An
ambiguous/denied/conflicting result remains held for qualified reconciliation,
never automatic retry or cleanup. Ordinary uploads to the disputed bucket/key
refuse while unrelated keys remain eligible. Even a verified receipt cannot be
reused for another correction. This is one existing operation receipt, not a
registry or scheduling service.

`installation_custody()` uses the SAME inode with a distinct non-publishing role.
It cannot invoke nested publication, and unresolved correction claims also hold
installation. Its acquisition does not retroactively exclude a legacy process.

## Concrete first-adoption sequence to qualify before execution

1. Retain exact protected source/patch/preimage hashes and original native
   entry inventory. At present the verified launcher execs the nightly module;
   direct/manual nightly and repair module paths also count. Any other capable
   checkout, wrapper, interpreter or ingress discovered must be included or hold
   adoption. Do not treat an inventory omission as permission.
2. Prepare the shared guard source and minimal admission-prelude patches for
   BOTH incumbent modules. They call `assert_admission_open()` after the existing
   repo-path bootstrap and before engine imports or main. An exclusive durable
   `options-hub-adoption.pending` barrier in the canonical `.git` directory must
   precede interposition. Deploy only reviewed exact guarded hunks with durable
   originals/preimages. The prelude affects NEW module entries; it does not stop
   or reclassify the old interpreter's already-loaded code. Do not apply this
   preparation until the actual native mutation mechanism and ingress coverage
   are independently qualified.
3. Establish the end of legacy admission only after every actual new-entry path
   is interposed and negatively checked. Record pre-fence wrappers/interpreters,
   descendants and outstanding effects. Consume their natural settlement. A
   preloaded manual holder that can still invoke old code is not excluded by the
   source patch. Unknown holder/remote-effect settlement holds adoption. Neither
   the calendar gap nor an idle PID census is a substitute.
4. With that barrier continuously present, acquire installation custody, recheck
   ingress/preimages/holders, apply the exact protected guard-bearing versions,
   preserve unrelated bytes and retain originals. Read back all entry/module
   hashes, lock identity and guard behavior. Existing run/claim histories remain.
5. Remove only the exact bootstrap barrier after those proofs qualify, under
   installation custody and the original bootstrap identity. Preserve the lock
   inode and all operation receipts. No forced producer run. New entries then
   reach the shared publication interlock; correction still needs the separate
   exact body/version/IfMatch/one-send/readback gates and installed truthful UI.

The source supplies the barrier checks and installer/publication role separation;
this document does NOT assert that native interposition, preloaded-holder
coverage or first-adoption execution has been proven. If interposing the actual
legacy ingress needs a denied or additional configuration/security effect, hold
that exact mutation and return its concrete action rather than invent a fence.

## Acceptance

Use separate processes to test contention in both directions, nested lifetime,
different cwd, inode replacement, process death with persistent STARTED,
installer/publisher role separation and pending-target publication. Reuse the
accepted conditional body/IfMatch/one-send and clock-label checks. Independent
review covers the new concurrency and first-adoption risk. Hosted source checks,
protected merge, native adoption, object correction and A/B/C remain distinct.
