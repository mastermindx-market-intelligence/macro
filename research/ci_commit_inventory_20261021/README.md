# Complete commit inventories before declaring proof stale

## Demonstrated defect

The normal controller39568735001 (2026-10-21 08:22–08:25 UTC) treated main
`ad6e5a824334d14859495fc017605ebf76e64e93` as a globally invalidating change
because the default commit response contained300 rows and the existing generated-output
tree shortcut could not classify its changed `reports` root. Git's complete diff
contains580 paths:356data,223site and `reports/signal-sanity.md`. The report matches
no specific gate in the observed35321d4c source. Truncation prevented the existing
surface matcher from making that distinction.

The retained read of the same immutable commit using explicit `per_page=100`
returned pages100/100/100/100/100/80. All six responses bind the same SHA, tree and
ordered parent list. Their580 unique filenames exactly match the Git diff.
[GitHub's Get a commit contract](https://docs.github.com/en/rest/commits/commits#get-a-commit)
supports paginated file results up to3000; a smaller bounded reader can remain
conservative when its own budget is exhausted. No `reports/` ignore rule is justified.

## Separate bottlenecks

Known proof39564153766 at `b3276da2127749fec1b5d3782f97b6b4692d1efd` succeeded:
317passed semantic units,0infrastructure findings,3078seconds run-to-gate and
263.53summed job wall minutes. Critical pack0 spent269seconds in checkout and
2556seconds executing the pack. Its main FIF suite passed3268tests/1skip in2512.93s.
The final pack-to-gate start wait was2seconds. This sample's execution tail dominates;
job creation timestamps and fleet runner headroom are not established by these fields.

Completion-triggered controller39570514158 bound that exact head and released its
lease at08:36:40Z, approximately37seconds after gate completion. It next claimed7653,
released that on a genuine conflict and requested its ordinary serialized successor.
The9714 generation was not stranded. Later controller39572727207 observed9indexed
proofs and0extra reservations against cap8; actual definition change2d50943eb154
required fresh qualification. Complete file enumeration must preserve that invalidation.

The earlier7/8 census with a pending lease proves one unused nominal slot under
current serialization policy. It does not authorize lease deletion or a cap increase.
This repair targets unnecessary refresh demand; it makes no fleet p95,30percent gain,
cost-neutrality, runner-capacity or live-release claim.

Raw logs, API pages and Git path inventory are retained in the original evidence
directory `/Volumes/Mastermind/ci-pack-throughput-20261019/`. `evidence.json` records
immutable identities and the measured boundary. Existing proof requirements, cap,
lease generation, required checks, twelve packs and two calibrated weights remain.

## Implemented repair and local acceptance

The reader preserves the existing tree shortcut, then completes an otherwise
truncated commit using up to ten explicit100-row pages. Every response must bind
same full commit SHA, tree and ordered parents. Valid file status, both rename
endpoints, unique current filenames and agreement with original row bindings are
required. A short final page proves completion; contradictory/failed/budget-limited
reads retain the original conservative truncation result. Both outcomes are cached.

One shared100-read allowance bounds the entire sweep. The API reserve includes
that allowance:220requests cover100pagination reads plus the existing120margin.
At600remaining requests the existing budget formula admits15PR evaluations instead
of20. This is API-accounting headroom; the hosted proof cap remains eight.

The corrected new fixtures failed on the old reader (15failed/3passed); the full
owning controller suites pass474tests on the integrated source. These include
late hidden definition/source changes, rename chains, missing/unknown statuses,
changed ordered parents, duplicate or oversized pages, incomplete termination,
transport errors, shared-budget exhaustion and unchanged fast-path request counts.
Independent Sol source review approved after strict status validation and API-budget
funding corrections. This is source approval, not hosted proof.

The real580-row replay returns exactly the retained Git inventory in seven calls
(one original plus six pages). With synthetic proof metadata isolating only this
commit, Treasury9880 and Tiingo9948 footprints become current;9862,9662 and9639
remain stale because they overlap the changed site/data surfaces. See
`isolated-replay.json` for identities and limits. This does not qualify any live PR
or supersede real later definition changes.

Original Fabric operation ci-throughput-01a153e8-invalidation-audit settled rc0 at
09:20UTC and both artifacts were recovered through its original carrier. The draft
needed parent repairs for GitHub's nested commit.tree shape, repository fixture
composition, duplicate/rename validation and read accounting. It is not recorded as
an accepted unmodified worker result; acceptance applies to the reviewed and tested
integrated source. No held8920 operation was retried or adopted.
