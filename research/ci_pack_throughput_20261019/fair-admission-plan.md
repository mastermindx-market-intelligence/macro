# Shared authored and refresh proof admission — P9.T9

Goal: actual capacity for both newly authored PR proofs and eligible stale refreshes, within unchanged cap8, followed by natural refreshed proof and downstream publication (#10640 first when equally ready).

Commission and explicit policy: https://github.com/mastermindx-market-intelligence/Mastermind/pull/1842#issuecomment-6595832764 and https://github.com/mastermindx-market-intelligence/Mastermind/pull/1842#issuecomment-6595947761. WS:CI-MERGE-CONTROL-PLANE / W-THROUGHPUT-20261019. Protected procedure pin b4a5a8925c6c1412dac67ba296cf65ee81c4d4c8, skillpack1.0.1/minimum1. Initial source5ec3e920b33b63c1e0cdb2c27fb7e5694517256d. Original harness is ~/gwcap/project-charters/ci-packs; material frontier is /private/tmp/ci-throughput-original-storage-frontier.json.

## Architecture and alternatives

Extend the existing serialized merge-on-green controller and PR records. All automatic new PR proofs must request admission before workflow creation; pending source/PR publication stays allowed and deferred checks remain incomplete. Trusted lifecycle events wake the same controller. Existing open PR records are the discovery source, not another queue. One durable launch generation covers a dispatch indexing gap; per-PR admitted identity remains conservative capacity evidence until exact terminal reconciliation. All current active legacy proofs drain normally.

Use protected-main ci.yml dispatch with explicit PR role, exact subject/base/tested-merge/workflow identity, an admitted generation and exact returned run ID. Proof execution has no controller write credentials. Trusted completion publishes real validated checks onto the subject head. Existing main-baseline dispatch and PC/fork boundaries remain separately bound. Semantic evidence readers must accept this carrier only with verified admission, never relabel the event or treat main's dispatch SHA as PR source.

Rejected: refresh ordering alone (no free slot at8); job-level admission (run already exists/counts); global concurrency group (replaces pending work and cannot provide8 slots); counting only convenient statuses or omitting authored work (false capacity); manual refresh/cancel/cap increase.

## Task tree

- [ ] P9.T9.S1: pure shared admission identity/capacity/fairness contracts plus interleaved-arrival regression. Module is a helper of the incumbent controller, no API/queue/runtime authority.
- [ ] P9.T9.S2: extend incumbent durable PR records/singleton generation, discovery and one-shot dispatch/reconciliation. Keep legacy m1 live ownership; exact requests with ambiguous results remain reserved without retry/expiry clearance.
- [ ] P9.T9.S3: wire BOTH actual workflow entry points, trusted exact checkout, real contract/pack proof and subject-head check publication. Adapt semantic-proof/controller/local reader identity and PC/fork route coherently. Deferred checks stay incomplete.
- [ ] P9.T9.S4: affected tests plus independent changed-risk review covering permissions, malformed/forged identity, phase races, stale/superseded heads, current-base proofs and unresolved effects. No self approval/merge.
- [ ] P9.T9.S5: normal protected publication and prospective deployment; consume existing natural controller return, actual admitted refresh, own proof and named downstream publication. No completion at source/test/PR/merge alone.

## Invariants and review focus

True cap8 counts distinct active legacy and managed PR-proof identities plus genuinely unindexed admission generations, never twice for a bound run. All5 active statuses count. Known active admission identity is a conservative floor across non-atomic status reads. Main baseline is excluded only with affirmative role binding; ambiguous dispatched role closes admission. Closed/superseded PR cannot erase active workload.

Fairness uses stable first-unserved controller request age across head replacement, with deterministic ties; admitted future heads become new demand. An eligible refresh cannot be indefinitely overtaken by later authored demand. Fairness does not promise service without actual completion.

No active cancellation, replay, fictional reservation, new queue/controller, cap/budget increase or stale-green transfer. Preserve720/setup600, Brain900, BEA600, legacy96/64MiB/allbytes/tails and UNKNOWN.

Trust: protected controller author/records, immutable workflow definition, exact ordered merge parents, originalrun/attempt, source-only job tokens and a separate trusted check writer. A user-modified PR workflow or privileged manual dispatch is not cryptographically prevented by this patch alone: actual execution controls must be verified, bypasses remain accounted and close admission. Do not claim an unenforceable universal ceiling.

Validation must exercise workflow entrypoint mappings, not only a helper model. Positive7+0 admission and negative8/7+1, unknown state, status transitions, indexed dedupe, PR close, late head, lost response, forged binding, wrong workflow, rerun attempt and incomplete evidence are required.

## Bounded discovery and original demand age — P9.T9.S6

The original 875-PR discriminator executes the real preparation and budget code
with synthetic provider responses. The pre-repair prospective bridge stopped after 185 PRs,
759 core requests used and 241 remaining, before publishing a census or selecting
work. The inactive foundation makes no admission effects. That original failure established the need for bounded bulk discovery and
conserved batch ages; the refusal remains valid evidence of the old path.
The complete live population read on November 3 at 13:57 UTC contained 871 open
main-targeting PRs, 600 Drafts and 110 armed non-Draft PRs. These are discovery
counts, not a claim that those PRs are eligible or need refresh.

Prepare bounded bulk reads through the same job token and GitHub origin. Require
complete connections, explicit errors and authoritative identities. Current PR
base fields must never stand in for the base actually tested by an original run.
Existing proof validation and exact freshness remain required for refreshes.
GraphQL point batching does not waive REST or GraphQL secondary content limits.
See the official [REST limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
and [GraphQL limits](https://docs.github.com/en/graphql/overview/rate-limits-and-query-limits-for-the-graphql-api).

Use one authenticated reference to the existing immutable demand batch on an
existing PR, with a retained existing-label association, to preserve historical
request ages. The batch is not an eligibility census, capacity lease, executable
queue or dispatch authority. Complete fresh PR discovery remains authoritative;
per-PR admission and settlement records remain unchanged. An age-only anchor
counts zero proof slots and survives PR closure while it protects unserved ages.
Before retiring or replacing an anchor, authenticate its successor and prove
conservation of every still-open unserved generation, purpose and original age,
including qualified head transitions. Missing or expired records are unresolved,
not permission to invent a younger request.

Legacy v1 demand artifacts contain changed rows, not complete snapshots. A
prospective v2 age snapshot must explicitly bind its covered predecessors and
prove conservation before publication. Readers may omit only that authenticated
coverage; newest-wins replacement is forbidden. Coverage itself must remain
bounded through the existing checkpoint model. Self/future references,
conflicting successors and uncovered later demands cannot be silently discarded.

The existing singleton register may distinguish the one original anchor-comment
publication intent from a launch reservation. Record intent before the POST and
reconcile its exact positive readback. A lost response plus an absent comment is
UNKNOWN, not permission to POST again; clientMutationId supplies correlation,
not assumed idempotency. Completion and cleanup must preserve this custody.
No separate cursor, queue, registry, token source, quota increase or capacity
exemption is introduced.

Qualification must exercise real stage wiring: complete authored discovery,
the observed mixed population shape, closed anchors, changed heads, forged or
incomplete responses, interrupted publication, original response loss, budget
exhaustion, conservation on replacement and capacity accounting. A successful
875-authored fixture does not qualify 875 armed refreshes needing distinct
original proof reads. That mixed-case read bound stays explicit until separately
demonstrated. Preparation and synthetic tests do not activate the bridge or
satisfy the natural refresh and downstream publication acceptance above.

The prospective implementation now uses the bounded reader and authenticated v2
age frontier described above. Real stage-wiring fixtures cover 900 authored PRs
and the observed 871/110 population shape with native proof records. The final
composed stage module has 104 passing cases, including failures after original
reservation that retain custody and hold the next sweep. The five other affected
controller/helper modules retain their passing composed results. These are local
source checks, not production token or installed admission qualification. A
hypothetical 875 armed existing-proof population still exhausts the incumbent
REST budget and refuses. Uncovered expired age artifacts also still refuse;
periodic renewal of unchanged artifacts is not implemented.
