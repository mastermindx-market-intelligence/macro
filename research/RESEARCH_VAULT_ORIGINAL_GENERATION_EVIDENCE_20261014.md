# Original producer evidence before generation adoption

The producer fence currently retains confirmed writes and pending receipts only
in memory. At a checkpoint the order is corpus, catalog, then receipts. A process
lost after catalog visibility can therefore lose the receipt bytes that its own
publication intended. A new census does not reconstruct those original effects.

This source increment provides an explicitly supplied private evidence sink. It
does not enable the workflow, expose a CLI mode, resume an operation, or change
the BUILDING/COMPLETE contract. All-writer qualification remains a separate gate.

## Captured cuts

| Cut | Evidence retained before/after the effect | What remains unproven |
| --- | --- | --- |
| Before BEGIN CAS | Exact catalog intent bytes, predecessor version, source/run identity | Caller identity is provenance, not authentication |
| Before each covered PUT | Key, exact byte digest and length, content type, epoch | An intent does not show that the request was sent |
| After synchronous return | True, conditional conflict, or explicitly uncertain result | Legacy unconditional false may hide a transport error |
| After catalog readback | Actual observed version and exact byte digest | A version is not an anti-ABA history |
| Before checkpoint/final corpus publication | Corpus digest/length and the original pending receipt bodies | A plan does not prove publication |
| After successful COMPLETE readback | Exact catalog digest/version and original epoch | Source admission, all writers and consumer acceptance remain separate |

Every append is fsynced before returning. Creation uses exclusive, no-follow file
creation in an existing private same-owner directory; the new file is mode0600.
The directory entry is also fsynced. An exclusive file lock remains held until
the caller closes the original sink. The writer refuses the next effect if
evidence persistence fails. A failure after a remote effect leaves the original
intent available and closes the session; it is never rewritten as success.

The default hard limit is128MiB, with a32MiB per-record limit. A caller may narrow
the total. Before every covered write, its intent must also leave64KiB for the
synchronous result, catalog readback and possible COMPLETE terminal record.
Opaque catalog versions are bounded to4096UTF-8bytes, so even their worst JSON
escaping fits that reserve. Budget exhaustion therefore refuses before the
effect; an actual disk/I/O failure after it still leaves an uncertain operation.
Corpus and PDF bodies are not copied into this file. Actual catalog
intents and pending receipt bodies are private and must stay on the original
private run/artifact carrier. Nothing writes them to the repository mirror,
GitHub source, a new object-store namespace or another scheduler.

The hash-linked sequence detects broken interior links and malformed/truncated
records. It is not a signature: a complete-line prefix, a rewritten final line,
or a wholly rewritten chain cannot be authenticated without an independently
retained original capture digest and custody. The read-only inspector validates
the local file format and exact expected identity. Its nonblocking lock only
checks this file on this host. It does not prove process ancestry, global writer
absence, or settlement of requests already sent to the object store.

## Recovery ruling and remaining implementation

No automatic takeover is introduced. An interrupted BUILDING stays bound to its
original operation. Removing its marker, restoring an old COMPLETE, inventing
confirmed writes from current objects, or treating a terminal CI flag as global
settlement is not an admissible recovery.

A later continuation can be considered only by the original assigning owner,
with the original captured source/run identity and retained evidence bytes. It
must establish that the actual old executor cannot issue further effects, that
each started request is settled on its original carrier, that the canonical
catalog still has the original epoch and exact expected predecessor, and that
the retained publication state supports the intended next step. An unmatched
intent, lost artifact, unknown delayed request, moved predecessor, or missing
capture anchor remains unavailable. A current matching object is an observation,
not permission to retry an uncertain write.

This increment deliberately contains no recovery executor. Before production
adoption the owner still owes that supported continuation path, actual executed
source/run binding for every recurring invocation, all-writer settlement,
measured run/evidence budgets, and a successful producer-published generation.
Missing evidence must remain a safe refusal even if the original host disappears.

COMPLETE must use the non-generation catalog payload already published by the
same BUILDING session. It cannot introduce a changed body during completion.
Ordinary BUILDING checkpoints may still publish changed payloads. Refusals keep
their specific cause on later use. Run identities reject surrounding whitespace,
and a failed close invalidates the local descriptor before reporting uncertainty
so a subsequent close cannot target an unrelated descriptor reused by the OS.

## Independent review disposition

The retained Qwen review of source0fdf71e277ab90a5ba48d39f8b3f1ab14f61e35a
identified six items. The post-effect budget gap, unpublished COMPLETE payload,
identity whitespace, close handling and overwritten refusal reason are repaired
with causal failing tests. Exact catalog checkpoint bytes remain retained; a
hash-only replacement would lose the original visibility intent. The128MiB run
limit still requires workload qualification before adoption.

The suggested generic mutator-name deny-list is not applied: an actual census
of both current R2Store and LocalStore public APIs found exactly two mutators,
`put_bytes` and `put_bytes_strict_conditional`, both intercepted by the fence.
This cooperative wrapper is not a sandbox for arbitrary future/custom APIs.
The review also suggested rejecting changed checkpoint bodies; that part is not
applied because publishing changes is the purpose of a BUILDING checkpoint.
The new payload-equality check applies at completion only.

## Verification

Writer tests use the actual ingestion path and a synthetic store. They verify
intent persistence before a PUT, failure before versus after a remote effect,
lost BEGIN responses, identity mismatch before mutation, pending receipt bytes
before checkpoint and final visibility, and uncertain immutable-write refusal.
Omitting the publication-plan hook is a causal red against the real integration
test. The separate Fabric-authored journal tests are reviewed against actual file
bytes, permissions, locks and injected I/O failures. These are source proofs;
they do not qualify any live writer or installed runtime.

A separate local sizing probe retained three4,623,772-byte synthetic catalog
intents plus thirty2KiB receipt plans. It used the current2889-item public
fixture and the earlier2888-member observation only as sizing inputs, not as a
coherent live generation. The resulting journal was18,579,918bytes, append plus
inspection took0.563seconds, and process peak RSS was88,883,200bytes on macOS.
These figures neither qualify the production runner nor establish source custody.
