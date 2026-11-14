# Native Rates scenario service qualification — 2026-11-14

## Assignment and outcome

WS:MARKET-OS / F01, Macro #6819; recovery parent Terminal #1524.
This phase joins the existing two-yield Rates owner and closed v2 wire contract
to the existing private scenario HTTP service. It is prepared source, with
local consumer proof. It is not deployed acceptance or client admission.

The existing POST `/api/ontology/explorer/scenario/v1` accepts
`ontology_scenario_request.v2` / `rates_curves.two_yield_shift.v1` after its
incumbent Bearer identity and `site_full` entitlement check. The server derives
the baseline from the qualified published Rates snapshot. Clients submit only
two bounded yield shifts and expected publication digests. The result is an
ephemeral mechanical calculation; no persistence or external execution occurs.

All producer `execution_available` values remain false, including Rates. The
snapshot/client contract remains 1.0.0. This source phase adds no discovery
capability, UI enablement, release opt-in, catalogue publication or deployment.

## Exact source composition and custody

Single real parent: Analyst Macro #11278 at
`25d1a5e1fb193f86809b5cf427ecb6292f258fb6`, tree
`945aa763ef14a1963108ae5175391da26e3b131e`.

The three core leaves from #11269 at
`66a8e4cf15ebcb9c3a470d182fce5c0e15cacf3e` and five contract leaves from #11274 at
`360bf8c8bca191fe0622b1e220747e6476df4a44` are imported by exact blob identity.
No additional ancestry or CI evidence is transferred from those branches.

| Imported path | Exact blob |
| --- | --- |
| `engine/market_os/macro_workspaces/rates_curves.py` | `0fbeaaef256fb48c8949cf5237c21fbf34992f33` |
| `tests/test_macro_workspace_rates_curves.py` | `10822544fc4571cbdc886687fcc1b9a4b1adfb80` |
| `research/market_intelligence_productization/NATIVE_RATES_SCENARIO_CORE_2026-11-14.md` | `e2c93c47c4ca46d59939c8557c8867da23552d0c` |
| `contracts/market_os/macro_workspace_scenario_request.v2.schema.json` | `f4d8c0b26bd6c96f335056e92d5736174316b3df` |
| `contracts/market_os/macro_workspace_scenario_result.v1.schema.json` | `295d9aef9ffa1a0773c3a58173c206635e396abf` |
| `lib/macro_rates_scenario_contract.py` | `6862b7f773c5a5292626679659c5f87b100212b2` |
| `tests/test_macro_rates_scenario_contract.py` | `dd355815d668659a39b79ff6906948eff3b89a86` |
| `research/market_intelligence_productization/NATIVE_RATES_SCENARIO_CONTRACT_2026-11-14.md` | `7394936677d8d28bde19d86c2b103acdd0aa745d` |

Both modified core preimages match this parent and the core commit's real parent
`8dd7689db40d27594161eb1a124553bfc285280f` (tree
`72d3c5784bd873d3b33b81a32e32641ffd806fae`): Rates owner
`09eb20d1c2855086fa2d9ee7bb3c78ef09362adc`, Rates tests
`50f16badd8e48708eb3e4c9202901e493266a162`. All six imported additions were proved
absent from the Analyst parent by nontruncated tree traversal.

The owned integration paths and their parent preimages are:

| Path | Parent blob |
| --- | --- |
| `app/macro_command.py` | `00db04c9dba70903d555ce94085062664edf946b` |
| `app/ontology_explorer.py` | `51039f1389a56dc6129b5b0dce2b43ba5e36f3b8` |
| `tests/test_macro_command_api.py` | `a5f870fe40d1b6be17f48a9c206d794570eca3d2` |
| `.github/ci/legacy-jobs.yml` | `25ff68e2a07a48113ef1f23d227ba89e9367ddd7` |
| `tests/test_macro_rates_scenario_api.py` | Absent |
| This qualification record | Absent |

The held #10614 WTI runtime, Parquet store, transport tests and uncertain
commands are not changed or replayed. The existing v1 handler retains its
implementation. The broad #10674 Business integration is not imported; any
future join with its artifact-retention/aggregate-clock work remains explicit.
Source law is pinned to Mastermind
`eeaf5eeec3f29b565bcc816db003706f429074fc`.

## Shared reader and successful-result fence

`read_macro_publication` factors the incumbent fixed-root loader into a
server-only context. It preserves the qualified served root, suite admission,
manifest/schema/digest validation, bounded file reads and response projection.
There is no alternate root, loader, cache or snapshot store.

Selected reads retain the raw body bytes already read. After a successful
consumer finishes, the context rereads that exact body and then the original
manifest. Rates constructs and bounds the actual HTTP response inside this
scope. A changed selected file is detected even while the producer has not yet
written its manifest. Aggregate reads retain their existing manifest fence.
The existing Macro GET projection still constructs its JSONResponse outside
the read scope; this phase does not claim a new GET serialization guarantee.

The internal raw-byte comparison does not redefine public identities:
`manifest_sha256` hashes raw manifest bytes, while `artifact.sha256` and
`snapshot_content_sha256` remain canonical content digests. Repeated reads are
charged to the existing 16 MiB total budget; per-body and manifest limits remain
2 MiB and 256 KiB.

Successful result encoding precedes the exit checks. A failed consumer does
not release a result and retains its original failure. A failed reread is
unavailability, not evidence that different bytes were observed.

## Request and response behavior

The existing transport retains its 4 KiB request limit, three-second receive
deadline, duplicate-key parser, JSON-only policy, query/encoding restrictions,
and 256 KiB encoded response limit. Authentication and entitlement run before
body parsing and source I/O. `always=True` preserves the paid entitlement gate
even with the global staging paywall disabled. The route's current dependency
uses Bearer identity; this phase does not introduce cookie authentication.

| Condition | HTTP result |
| --- | --- |
| Invalid v2 fields, method, digest syntax or shifts | 400 `invalid_rates_request`, before source I/O |
| Qualified current publication differs from valid expected identity | 409 `source_changed` |
| Body or manifest bytes demonstrably change before result release | 409 `source_changed` |
| Initial reader/baseline refusal or unreadable exit fence | 503 `source_unavailable` |
| Malformed internal publication/calculation receipt | 500 `internal_error` |
| Existing response encoder exceeds its limit | 503 `response_too_large` |

The wire serializer qualifies the baseline/calculation/publication before
comparing expectations. A stale client digest therefore cannot disguise an
invalid server receipt as an ordinary refresh request. The small pure
calculation may execute before a valid stale expectation is refused. It has no
external effect. The serializer also recomputes the calculation for consistency;
this is not a second runtime or provider execution.

The private route wrapper retains `private, no-store`, authorization/cookie
Vary, `nosniff` and `noindex, noarchive` on successes and refusals. Error responses
and log messages do not include private assumptions or filesystem paths.

## Qualification evidence

473 distinct relevant tests passed across final local qualification runs:

| Existing/new suite | Passed |
| --- | ---: |
| New real Rates HTTP integration | 52 |
| Macro aggregate/selected serving API | 58 |
| Analyst exact-source context and HTTP gateway | 40 |
| Closed Rates wire contract | 98 |
| Rates workspace and pure calculation owner | 225 |

The initial joined run had 459 passes and 14 reader assertions expecting the
old one-body-read schedule. Those assertions now require the exact sequence
manifest → selected body → same selected body → same manifest, and still forbid
sibling reads or writes. The final serving API + Rates HTTP run passed 110/110.
No production behavior was weakened to satisfy an obsolete read-count assertion.

The positive HTTP path uses the assembled application with the real router,
real identity/entitlement functions, real composer/finalizer, real selected
reader and real Rates serializer. Only external identity/entitlement backing
services and the served-root fixture are controlled. No successful response is
stubbed. Observed 2Y 3.8% and 10Y 4.1%, shifted +100/+25 bp, produce 4.8%/4.35%,
30 bp observed spread, −45 bp assumed spread and −75 bp change. All authority
flags remain false except `display_only`; all four effect counts are zero.
The fixture's source bytes remain unchanged after the request.

Discriminating refusals include authentication before body parsing, entitlement
with staging disabled, identity outage, every disallowed method, duplicate JSON
keys, both declared and streamed body limits, client baseline/path injection,
booleans/nonfinite/off-step shifts, zero, opposing ±300 bp shifts, stale
expectations, same-content republication, missing/corrupt/no-common-date data,
and body/manifest changes during calculation, serialization and response
encoding. A same-length, semantically identical body rewrite with an unchanged
manifest is still refused during an in-flight calculation. EIO rereads remain
503; malformed internal receipts remain500 even if publication also changes.

The new HTTP suite and imported wire suite are registered on the existing
Macro Command serving-API step in the incumbent CI pack. The Rates owner suite
already has its existing CI registration. No workflow, queue, runner or job is
introduced. Test-environment deprecation warnings are unrelated to assertions.

Local logs: joined suite SHA256
`7a340fbee8904e0ac79e5cfebc57b7aaeae8e4d0b69a5ec57da80a9a95641eb6`;
final 110-test reader/API run SHA256
`730b930fbee53fa786d80cbf39600e7b67ae76dcda2fb2f4d2ad67cfcc62bb7a`.
These identify local evidence, not hosted or deployed receipts.

## Release and next proof

Keep this companion Ready and unarmed on its exact Analyst parent. Parent
#11278's contracts gate passed, but its feature-branch authority gate reports
`unsupported_base_ref`; that release boundary is retained. Only an allowed
protected integration can establish a releasable ancestry and binding exact-head
CI. Local tests do not transfer that status.

The native consumer still owes explicit scenario admission/version handling,
the preserved server baseline and publication identity, stale-baseline review,
desktop/mobile EN/ZH and dark/light browser proof, and authenticated deployed
round-trip evidence. No producer availability flag or catalogue row should be
enabled by interpreting this source qualification as that later acceptance.

Reassess the parent mission after publication/readback. Rates service source is
a phase, not completion of Native Macro/Economy. Analyst bridge compatibility
with retained Options evidence and protected backend/browser/deployment proofs
remain separate live boundaries; the existing immutable captures are preserved.
