# FIF D2 — Attestation admission gate (2026-10-12)

Workstream `WS:FINANCIAL-INTELLIGENCE-FABRIC`, program `fundamental-forensics`, lane D2.
Module: `engine/fundamental_forensics/attestation_admission.py`.
Contract: `contracts/fundamental_forensics_attestation_admission.schema.json`.

## Status

**No lawful attestation exists.** Every capture this house can describe today is
`reconstruction`: bytes fetched today, fixture bytes, comparative reprints. No
`historic_capture` and no `admitted` state is reachable — `admitted` is reserved
because no verifiable signed trust anchor exists, and a self-asserted "admitted"
mapping is exactly the forged attestation the module exists to refuse. Until the
human gate below clears, the machine-checkable answer to "is there an attested
history?" is the explicit state `unresolved_human_gate`, never an absence and
never a silent default to yes.

## Observed metadata

Gathered by the orchestrator on 2026-10-12 from GitHub **metadata APIs only; no
secret value was read** (and none ever will be by this lane):

- Repository: `mastermindx-market-intelligence/macro`.
- Environment `attested-history-seed`, required reviewer login `chriswong6031-creator`.
- Repository secret NAMES (values never read): `R2_ATTESTED_HISTORY_ENDPOINT`,
  `R2_ATTESTED_HISTORY_BUCKET`, `R2_ATTESTED_HISTORY_SEED_ACCESS_KEY_ID`,
  `R2_ATTESTED_HISTORY_SEED_SECRET_ACCESS_KEY`,
  `R2_ATTESTED_HISTORY_READONLY_ACCESS_KEY_ID`,
  `R2_ATTESTED_HISTORY_READONLY_SECRET_ACCESS_KEY`.
- Writer key metadata: `R2_ATTESTED_HISTORY_SEED_ACCESS_KEY_ID` updated
  2026-09-29T06:06:34Z; `R2_ATTESTED_HISTORY_SEED_SECRET_ACCESS_KEY` updated
  2026-09-29T06:06:40Z → **writer-key rotation stamp 2026-09-29T06:06:40Z**.
- Latest seed run `36397411740`, workflow `attested-history-aapl-seed`, event
  `workflow_dispatch`, branch `main`, created 2026-09-28T08:26:53Z,
  `run_attempt` 2, attempt started 2026-09-29T07:34:44Z (**after** the
  rotation), completed 2026-09-29T08:17:43Z, conclusion `failure`, failed step
  `acquire bounded AAPL seed and run zero-write preflight`, actor
  `chriswong6031-creator`. No seed run since.

## EXACT HUMAN GATE (case `post_rotation_attempt_failed`)

**WHAT**: Operator (human) diagnosis of the protected writer path at the failed
step `acquire bounded AAPL seed and run zero-write preflight` — out of band, in
the human-owned lane — followed by an operator-approved `workflow_dispatch` of
`attested-history-aapl-seed` on `refs/heads/main` with `enable_aapl_seed=true`
in the `attested-history-seed` environment.

**WHO**: `chriswong6031-creator` (required reviewer of `attested-history-seed`)
and the Chairman. No agent session holds any part of this gate.

**WHY**: Seed run `36397411740` attempt 2 started 2026-09-29T07:34:44Z at/after
the writer-key rotation 2026-09-29T06:06:40Z and still concluded `failure` — so
the post-rotation writer path itself is failing, and re-dispatching without
human diagnosis would only repeat it (attempt 1 predates the rotation and
carries no evidence about the current keys).

**NEXT LAWFUL ACTION**: The Chairman or the required reviewer inspects the
failed step's logs out of band, fixes or rules on the writer path in the
human-owned lane, and only then approves a fresh dispatch. After a successful
seed, the gate becomes case `seed_succeeded`: a separately commissioned
verification of that bundle with
`scripts/verify_fundamental_forensics_attested_history_seed_bundle.py` before
any admission can exist.

## What agents may never do (D2 HARD LAW)

- Never debug, repair, replace, wrap, re-implement or exercise the
  attested-history writer/credential path.
- Never read, print, rotate, store or transmit any secret VALUE; secret NAMES
  are the only credential fact any artifact may carry.
- Never dispatch, rerun or re-run any workflow — never seed run `31534160304`
  nor FF-1R runs `32626273461` / `32708350406`.
- Never point anything at production, R2, Cloudflare, GitHub or SEC; no network.
- Never label any fixture or fetched-today capture `attested`; no `ffatt_` id
  may be minted from reconstruction bytes. A partial package is never complete;
  a comparative reprint is not a restatement; the four clocks never collapse.

## What this module guarantees until the gate clears

- `resolve_capture_basis` returns `reconstruction` for every lawful input;
  `historic_capture` is unreachable in v1; recording-before-acceptance is
  refused as `clock_order_violation`; any admission claiming `state='admitted'`
  or truthy `attested` is refused as `attestation_claim_refused`.
- `build_admission_status` emits a non-secret receipt (`ffadm_…`, deliberately
  distinct from `ffatt_`) whose state is always `unresolved_human_gate`,
  `attested=false`, `capture_basis='reconstruction'`, with the deterministic
  gate (case, what, who, why, next lawful action, forbidden agent actions) and
  nonclaims. It refuses value-shaped keys before anything else, unknown secret
  names, fixture candidate sources, unexpected keys, malformed timestamps, and
  missing environment/writer-secret evidence. Pure: no I/O, no clock reads,
  every time an explicit argument.
- Vocabulary: `ADMISSION_STATES = (admitted, unresolved_human_gate, refused)`,
  `CAPTURE_BASES = (historic_capture, reconstruction)`; environment/workflow
  literals are AST-pinned to the seed script's expected constants.

## Follow-on

After D2 merges, D3's `delivery()` (open PR #8951,
`engine/fundamental_forensics/production_datasets.py`) may accept a D2
admission-status reference instead of refusing the vocabulary outright. That
wiring is a separately commissioned task; this lane does not create or edit
`production_datasets.py`. Nothing here authorises a second SEC request budget,
a second scheduler, or any model-originated canonical number.
