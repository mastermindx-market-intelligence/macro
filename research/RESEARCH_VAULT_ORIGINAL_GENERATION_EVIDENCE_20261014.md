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
| Before checkpoint/final corpus publication | Exact intended catalog bytes, corpus digest/length and original pending receipt bodies | A plan does not prove publication |
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
effect. Each publication plan also reserves the known remainder of its serial
corpus/catalog/receipt batch before the first corpus effect. This includes the
following catalog intent, bounded versions and receipt envelopes. An actual
disk/I/O failure after an effect still leaves an uncertain operation.
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

The batch freezes its normalized catalog and original publication timestamp
before the corpus write. The same exact bytes are retained in publication_plan
and supplied to catalog.publish; that call refuses a changed body and does not
restamp it. This closes a measured gap in the earlier journal: a process lost
after an acknowledged corpus PUT but before catalog.publish previously lost the
intended catalog that existed only in memory. Corpus, catalog and receipts still
publish in that order. A catalog conflict does not release pending receipts.

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

The publication-gap failure injection uses actual ingestion control flow with a
synthetic parser and store. The intended new catalog is absent from the earlier
journal despite a confirmed corpus write. Three discriminators fail on that
source and pass with the frozen batch: original catalog retention, exact later
publication bytes, and refusal of a body changed after capture. Additional tests
cover later publication clocks and conflict-withheld receipts. The final affected
suite contains671passing tests with no skips.

A separate local sizing probe retained three4,623,772-byte synthetic catalog
intents plus thirty2KiB receipt plans. It used the current2889-item public
fixture and the earlier2888-member observation only as sizing inputs, not as a
coherent live generation. The resulting journal was18,579,918bytes, append plus
inspection took0.563seconds, and process peak RSS was88,883,200bytes on macOS.
These figures neither qualify the production runner nor establish source custody.
They describe the earlier capture layout, before exact intended catalog bytes
were also included in each publication plan, and are not the new run budget.

The focused publication review of82e131770576a421fe68e955db34e8b78807abb4
found that an individually affordable corpus intent could leave insufficient
capacity for the next catalog intent. A causal test on that exact writer records
the corpus PUT before the catalog is refused. Reserving the rest of the known
serial batch at publication_plan now refuses before that PUT. The first version
of this test was too tight and refused both versions early; it is retained as
nondiscriminating evidence, not counted as a causal failure.

That review also identified an avoidable serialization and a misleading failure
payload. Prepared-catalog refusals now retain the original planned bytes, use
separate errors for missing session, invalid bytes and a changed body, and share
the existing normal serializer. The peer report is accepted as an adjudicated
review of82e131; root verified the repair postimage. This does not claim that the
peer reviewed the later commit. Existing Linux filesystem evidence remains
applicable because generation_evidence.py is unchanged.


## Bounded original-parent continuation candidate

The companion source now provides a read-only closed-journal analyzer and a
private `_continue_after_original_exit` entry point. These functions do not
establish caller authority or process settlement. The protected producer launcher
must actually wait for its own original child, retain the closed journal's
capture digest, and invoke one fresh isolated continuation child. A saved receipt,
manual CLI call, newly assigned run identity or matching remote postimage cannot
substitute for that original control flow. Mastermind PR1546 supplies that
composition; its source-pair release requires adjudicated recovery-review
findings and the normal protected release checks.

The analyzer accepts only acknowledged, observed BUILDING publication with an
exact live catalog version and bytes, valid corpus/receipt/PDF bindings, and no
unsettled write intents. The continuation creates an exclusive tail journal and
records its original capture and catalog predecessor before issuing only missing,
previously unissued create-only receipts and the final COMPLETE transition. It
retains the same source/run identity and epoch, leaves the original journal
immutable, and never starts another BEGIN. Failed or ambiguous tails stay on the
same reserved operation; there is no recursive or manual retry entry point.

The continuation uses the analyzer's existing 1 GiB aggregate live-read ceiling.
The ordinary 256 MiB budget could be exhausted by an admitted 256 MiB corpus
before receipt, PDF and catalog-fence checks finished. A scaled regression runs
the actual analyzer and same-epoch completion at that boundary; the former
budget fails before continuation writes. Larger aggregate cuts still refuse
before writes and require original-operation reconciliation. This is a bounded
continuation, not a general recovery mechanism for every possible batch size.

The CLI opens its read-only SQLite projection by a percent-encoded absolute
file URI. A corpus path containing percent, question-mark or hash characters
must identify the named database rather than a decoded or truncated decoy.

Generation invocations use a separate write client with a resolved standard SDK
policy of one total attempt and a per-invocation guard on actual outbound sends.
The guard also refuses S3 regional redirects and their HeadBucket probes before
any second request. A lost response remains an uncertain effect even when a
matching object or COMPLETE postimage can be read later. Ordinary legacy writes
and read retry behavior remain unchanged. This reduces generation availability:
a transient write failure can leave BUILDING frozen until its original operation
is lawfully reconciled. It does not authorize a successor to replay the write.

The changed source is tested with the prepared boto3/botocore1.43.108 pair and
loopback HTTP, including redirect request counts, concurrent writes, missing
credentials, lost responses and legacy injected-client replacement. The source
pair's isolated actual launcher/engine proofs distinguish an acknowledged
publication followed by an unissued tail from original and tail lost-ack cases.
These are synthetic service proofs, not real R2 consistency, all-writer admission,
source installation or consumer acceptance. A COMPLETE generation still requires
its own truthful coverage census; it does not imply the95percent target.
