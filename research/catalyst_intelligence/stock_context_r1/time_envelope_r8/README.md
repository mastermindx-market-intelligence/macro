# R8: separate information and artifact clocks

## User benefit and source scope

The company research consumer can now reconstruct an earlier information cut from owner
artifacts materialized and received later. It records those later clocks honestly instead
of requiring them to be backdated to the decision cutoff. Current news remains useful
when historical evidence or peer inputs are unavailable.

This additive v3 source increment continues PR #9616 and operation
`catalyst-stock-context-r1-20261019` from
`6995b4d25b083b2c4907c2306ab77a93d6279ed6`. The v1 and v2 implementations and their
existing tests are unchanged. The original Draft / HOLD and
`NONACTIVATED_RESEARCH_CONSUMER` scope remain.

This is supplied research composition. A caller-supplied source reference, revision and
matching digest establish internal consistency, not independent source qualification,
historical owner availability, source rights, authentication, or actual decision delivery.
A caller could change a payload and recompute its digest. The consumer does not treat that
as native owner admission.

## Why the previous contract needed a separate version

The v1/v2 research snapshot inequalities require `as_of <= known_at`, while qualification
at an exact requested cutoff requires `as_of == decision_at` and
`known_at <= decision_at`. Those conditions collapse the three clocks to equality.
They remain supported for compatibility; they are not used as a native acquisition model.

V3 distinguishes:

| Clock | Meaning |
| --- | --- |
| information_cutoff_at | Cut at which the owner is asked to project information |
| materialized_at | Time the supplied artifact was assembled |
| received_at | Time the composer received that artifact |
| composed_at | Time of the resulting research composition |

The envelope requires
`information_cutoff_at <= materialized_at <= received_at <= composed_at`.
The request's information cutoff must match each current envelope. A comparison has its
own strictly earlier cutoff and independent prior envelope. Example fixture clocks are
20:00:08Z, 20:00:13Z, 20:00:15Z and 20:00:16Z on 2026-09-28.

These clock labels do not prove that supplied owner maps were knowable historically.
That requires evidence and admission by the existing owner. In particular, the current
NewsImpact projector filters fact observations at the requested cut but consumes supplied
identity, leaf and relationship maps. Relabeling those maps with an old cutoff cannot
establish their historical availability.

## Closed request and unchanged owner boundaries

Input schema: `catalyst.stock_research_inputs.v3`.
Output schema: `catalyst.stock_research_assessment.v3`.
All fields are required; intentional missing facets use null.

| Request field | Content |
| --- | --- |
| focal | Existing security_id, company_id, identity_epoch and identity_source_ref |
| information_cutoff_at | Complete supported UTC information cutoff |
| composed_at | Actual composition clock |
| peer_inputs | Existing supplied-cohort input, or null |
| entry | Prophet B4 envelope, or null |
| news | fact_log, current_owners and comparison, or null |

A supplied envelope has exactly `schema`, `owner`, `information_cutoff_at`,
`materialized_at`, `received_at`, `source_ref`, `source_revision`,
`payload_digest` and `payload`. The schema is
`catalyst.supplied_owner_time_envelope.v1`; owner is `news_impact` or `prophet_b4`.
A news comparison contains `information_cutoff_at` and `prior_owners`.

NewsImpact is always called at the information cutoff, never at materialization, receipt
or composition time. An owner's literal `decision_cut` and payload digest are preserved.
Current and prior states are projected independently. Missing prior evidence disables
comparison without erasing available current news. Malformed supplied evidence still
refuses when another optional facet is missing.

The existing peer builder retains its formation, observation and knowability constraints
at the information cutoff. Delayed composition does not admit later peer knowledge.

Prophet B4 retains its original identity, quote clock, evaluated clock, gates and payload.
A different evaluation cutoff is explicitly unavailable for the requested cut. An attached
projection is research context only; delayed receipt is not current entry availability.
Existing strategy scientific status and authority tier are unchanged.

The CLI dispatches v3 only for its exact schema:

```sh
python -m engine.catalyst_intelligence < request.json
```

Every v3 result explicitly sets `source_admission_established=false` and
`decision_availability_established=false`. All authority flags remain false. Advanced
entry, valuation, causal, predictive and clinical estimates remain unqualified or
unavailable. There is no acquisition, identity allocator, source store, publisher,
authenticated endpoint, fusion score, gate override or trade authority in this increment.

## Verification on the original M2 workspace

Protected procedure was loaded at
`Mastermind@a7553e0a18339c910eef9687c730b06605dd710e`,
Skillpack 1.0.1 / bootstrap major 1. Root performed the bounded critical-path source work.
The Executive read at 2026-10-20T06:52:12.460427Z returned
`backend_unavailable` / request not sent; no worker submission or execution readiness
was established. The native child supplied C3 architectural review only.

- Final declared consumer suite: **128 passed**, zero failures, 8.41 seconds
  (Studio process 33841, exit 0). This includes 40 new v3 cases and the unchanged 88.
- The first combined run had 127 passes and one over-broad late-fact test assertion
  (process 4288). The test had compared full owner views even though adding an excluded
  fact changes the whole-log provenance hash. Diagnostic process 7285 found exactly the
  current/prior `log_sha256` differences. The repaired assertion requires those hashes
  to change while all semantic fields remain identical; targeted process 9318 passed.
  It retains a positive wrong-clock witness that includes the later-observed fact.
- Existing CI import-closure and exclusive packing contracts: **2 passed**, zero failures,
  214.73 seconds (process 12568, exit 0). The existing job now includes the new test and
  its actual R5 fixture dependency; packing limits and exclusive ownership are unchanged.
- Source claim guard `python scripts/check_validated_claims.py --scope source` passed
  (process 40427, exit 0). Its first attempt reported the sparse checkout's missing
  allowlist. The 94,204-byte allowlist was restored unchanged from the baseline commit
  (SHA-256 f252221c9b6ef40f7ac49fd0503c4c10e68b7b01557d2c324ddfea1d9188c0fc);
  no claim allowlist or source copy was edited to obtain the result.
- Final tests emitted two inherited pytest temporary Chromium cleanup warnings. No test
  failed and no unrelated temporary artifacts were removed.
- Two actual v3 CLI captures passed scenario assertions, including missing history.
  Capture process 31915 exited 0. Inputs are synthetic R5 owner fixtures with the new
  envelope clocks, not acquired current market cases.
- Five legacy requests produced **byte-identical stdout** between the original baseline
  CLI and the updated CLI using this same source composition. Legacy implementation
  bytes are unchanged. Source hashes and exact outputs are in
  [capture-receipt.json](capture-receipt.json).
- Three stored historical captures also match this branch. R5's `source_revision` and
  `peers_missing` captures were made in the separately documented R3/R4 owner composition;
  their trigger lists already differ on the unmodified baseline. The first capture attempt
  (process 17042) stopped on that distinction; diagnostic process 26849 resolved it.
  The historical examples remain unchanged. This is not an introduced v3 regression.
- Independent C3 review accepted the exact module, CLI, test repair and CI declaration for
  nonactivated research-consumer source scope. It did not execute tests or accept native
  acquisition, qualified ledger state, serving, publication fencing or decision availability.

Review binding (SHA-256):

| Source | SHA-256 |
| --- | --- |
| assessment_v3.py | f7a95ab98a9c9e499bf42ff51840ea656ff3bfbe4e9fe3d9e7cb1982c2b2866a |
| __main__.py | 67b6c9944b378387117fc0106258559962389ea3deeec54a35c007c73c0a2aa9 |
| test_catalyst_time_envelope.py | d06d1ab445aa95d0d272500a161837f711b603c572a8375d78cae9e33511f3f8 |
| .github/ci/legacy-jobs.yml | b401196b905dd2f3b9e82ada34c7160230ef4673f3164571c12dd99553c1f80d |

## Continuation gates

This source change repairs artifact-clock representation. Native integration still needs
independently qualified current/prior owner state, real source and identity bindings,
purpose- and rights-qualified peer/market inputs, and an actual entry-owner record.
Reconstruction never establishes that an assessment was delivered before a past decision.

The next serving work retains #6712 custody and original unpublished tests, repairs the
existing identity/provenance admission path, and binds the entitlement-aware consumer.
The existing server publisher must reject an older composition finishing after an admitted
correction; a client generation counter does not prove that race is safe. Current-head
hosted CI, source-hold release, native admission and authenticated serving remain separate
gates. No merge, activation, deployment, background watch, scientific qualification or
full-program completion is claimed.
