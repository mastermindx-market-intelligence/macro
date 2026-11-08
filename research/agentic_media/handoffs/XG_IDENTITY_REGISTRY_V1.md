# XG identity registry — schema v1 (delta on `personas/*.yml`)

Status: **specification, unbuilt**. Owning card: `t_da720ee4`. Author seat: engineering.
Inputs adopted from the 2026-11-07 room exchange: state enum and stickiness proposed by the
marketing seat; every field below exists so a claim can be *checked*, not asserted.

## What already exists

The draft harness (PR #10837) already carries registry-as-data at `tools/xguerrilla/personas/*.yml`,
five entries, each with behaviour fields: `handle, cell, role, beat, city, tz, speed_class,
typo_rate_mult, revision_prob, pause_mult, hours, idle_day_p, casing, max_chars`.

That satisfies the requirement that **voice is data the harness consumes, not code it re-derives.**
This document adds nothing to the voice half and must not restate it.

## What is missing

By inspection of `tools/xguerrilla/`: there is **no identity lifecycle**. The strings
`admitted`, `suspended`, `proposed` appear nowhere; the only `retired` occurrences are unrelated
(locator drift in `gate.py`, proxy reputation in `net.py`, a supervisor reason string). Personas
describe *how an identity behaves*; nothing describes *whether it is provisioned, on what
binding, and whose hands hold it*.

So the delta is a second plane, not a rewrite: behaviour stays where it is, lifecycle is added.

## State machine

```
proposed --admit(admission_receipt)--> admitted
admitted --drift_observed(drift_evidence_ref)--> suspended
suspended --re_admit(new receipt)--> admitted
any --> retired
```

- **Launch is a read.** A launch that fails a gate writes nothing to an existing entry; the
  identity never leaves `proposed`. Nothing is revoked because nothing was ever admitted.
- **Drift is the only writer of `suspended`.** Drift = proxy reassigned, TOTP re-seeded, handle
  renamed, custody holder changed.
- **Suspension is sticky.** Re-admission is its own event with its own receipt. Repairing the
  binding does not auto-clear `suspended`. Mirrors `X_GUERRILLA_NETWORK_MASTERPLAN.md:367`
  (§17.4): *"Suspension is not permission to replace an identity and continue the same blocked
  action."*
- `retired_from` records the predecessor when an identity replaces another, so replacement is
  visible rather than silent.

## Entry shape

```yaml
handle: desk.and.dusk            # join key to personas/<handle>.yml
state: admitted                  # proposed | admitted | suspended | retired
binding:
  email_mailbox: mail.mastermind-x.com:<alias>   # provisioned mailbox, not a plan
  proxy_slot: slot-01            # key into the credential store, never a credential
  cdp_port: 9333                 # port is part of identity (see observer contract)
  totp_custodian: <seat-id>      # who holds the seed, not the seed
admission_receipt: {path: ..., sha: ...}         # admission is an event with evidence
registry_revision: 7            # monotonic; mutations bump it
schema_version: 1
drift_observed_at: null
drift_evidence_ref: null
suspended_by: null
retired_from: null
```

Rules that come with the fields, and are the point of them:

1. **No bare booleans.** Admission is a receipt, not `true`. A reviewer must be able to open the
   evidence without asking anyone.
2. **No credentials, ever — not even "in the registry".** `proxy_slot` is a key. The credential
   store lives outside both repos at mode 0600 and is referenced by **path + custody ref**. The
   repo tree may hold an example file (`proxies.example.yml`); it may not hold a live one,
   gitignored or otherwise. One `git add -f`, one packaging step or one `rsync` of a working
   directory is the whole distance between a gitignore rule and sixteen leaked proxy credentials.
3. **`registry_revision` bumps on any mutation.** The harness refuses to launch if the revision
   it validated against differs from the revision on disk — a registry edited mid-run is drift.
4. **`binding.cdp_port` is unique across the fleet.** Two identities on one port is a collision,
   not a shared resource.
5. **`state` is the only launch gate input.** Bio-link policy, voice and cadence never gate a
   launch; they gate content.

## Validator behaviour

Pure function, no I/O, no clock of its own: `validate(registry, personas, credential_store_refs) -> Result`.

Refusals, each with its own test:

- `state` not in enum → refuse.
- `admitted` without `admission_receipt` → refuse.
- `binding.email_mailbox` whose host is not in the declared domain allowlist → refuse.
- `binding.proxy_slot` not resolvable in the credential store → refuse.
- duplicate `cdp_port` across entries → refuse.
- `registry_revision` mismatch against the value the caller validated → refuse.
- persona file present with no registry entry → refuse (behaviour without identity).
- registry entry with no persona file → refuse (identity without voice).

## Non-goals

This schema does not decide whether a domain or mailbox may be purchased, does not grant any
account, and does not touch posting. Those remain separate-grant items.
