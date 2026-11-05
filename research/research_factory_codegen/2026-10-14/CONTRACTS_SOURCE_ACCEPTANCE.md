# Dormant codegen contract acceptance

The fresh implementation adds bounded exact-JSON manifest, per-decision input,
fixed-schedule output and prerequisite-reference validators. It rejects
malformed identities, nonfinite values, future observations, shifted or dropped
output rows, direct self-parent lineage and UTC conversion overflow. Structural
agreement grants no generation, execution, evaluation or publication authority.

The fresh Fabric return was reviewed by its actual assigning Sol coordinator
and integrated by the original root. Its original bytes were not accepted
unchanged: two validator defects and one test-isolation defect were corrected.
The root first reproduced three failures with the new regression tests. A
combined integration run then exposed the eager-import assertion's dependence
on pytest collection order and two omitted sparse fixtures. The test now checks
eager imports in an isolated interpreter; the existing fixtures were
materialized byte-for-byte from the source commit.

Final combined verification: **571 passed in 116.46s**, covering the new
contracts, existing accounting/evaluation/transport and Factory state, schema
and Market Memory suites. The existing CI job explicitly runs both new suites;
all 300 legacy job definitions validate. The authority guard returned zero;
its initial sparse-worktree warnings are not proof of physical isolation.

Fresh run: `rf-contracts-fresh-01a1333c-v1`. Original root:
`01a1333c-a475-7052-95a8-72a88eb8c17b`. Assigning parent:
`01a137c8-ddd0-7e82-8df5-6d3d2d15b0f1`. Source base:
`ee3b1907497c4d5179d76626777b007e0da93d18`. Reviewed patch SHA256:
`e74150f11d074b954f1b94eaaa87453f58a2d69f8e834e05526582041c15245a`.

The original uncertain run remains quarantined under the explicit decision
recorded in CONTRACTS_SOURCE_CUSTODY.md. Its refused read stays closed.
This accepted source is not installed/runtime, historical-data, statistical
or authenticated product acceptance. The connected existing review flow is
the next source phase on this carrier.
