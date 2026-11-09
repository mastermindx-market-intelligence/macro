# XG identity registry — schema v1 (delta on `personas/*.yml`)

Status: **implemented: tools/xguerrilla/registry.py (this PR)**. Owning card: `t_da720ee4`. Author seat: engineering.
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

## Document shape (`registry.yml`)

```yaml
schema_version: 1            # int; validator knows exactly {1}; anything else → refuse (fail-closed)
registry_revision: 7         # int ≥ 1, monotonic for the whole document
mail_domains:                # allowlist for binding.email_mailbox host
  - mail.mastermind-x.com
domains:                     # domain records; a bio link may only exist against an ADMITTED record
  - domain: www.mastermind-x.com     # exact host, lowercase
    state: admitted                  # same enum as entries
    recovery_owner: seat:marketing   # who recovers the domain/DNS; never a credential
    bio_link_policy: single_canonical   # none | single_canonical
    admission_receipt: {path: research/..., sha256: <64 hex>}   # required iff state == admitted
entries:
  - handle: desk.and.dusk            # join key to personas/<handle>.yml, unique
    child_id: dsk7q2                 # immutable attribution key, ^[a-z0-9]{4,32}$, unique; feeds validate_bio(known_ids)
    state: proposed                  # proposed | admitted | suspended | retired
    revision: 1                      # int ≥ 1, per-entry; any mutation of the entry bumps it
    domain: www.mastermind-x.com     # must name a record in `domains`
    recovery_owner: seat:marketing   # free string, required, non-empty
    bio_link_policy: single_canonical   # none | single_canonical; `none` ⇒ bio may carry NO link
    binding:
      email_mailbox: null            # "<host>:<alias>"; host ∈ mail_domains. Required non-null iff state in {admitted, suspended}
      proxy_slot: null               # key into credential store (slot name, e.g. us-01); required iff admitted/suspended
      cdp_port: null                 # int 1024..65535; unique across non-retired entries; required iff admitted/suspended
      totp_custodian: null           # seat id string; required iff admitted/suspended
    admission_receipt: null          # {path, sha256} required iff state in {admitted, suspended}; must be null when proposed
    drift_observed_at: null          # ISO-8601 string; required non-null iff suspended, must be null otherwise
    drift_evidence_ref: null         # string; same rule
    suspended_by: null               # seat id; same rule
    retired_from: null               # handle of the predecessor identity this one replaces; if set, predecessor must exist in entries with state retired
```

Rules that come with the fields, and are the point of them:

1. **No bare booleans.** Admission is a receipt, not `true`. A reviewer must be able to open the
   evidence without asking anyone.
2. **No credentials, ever — not even "in the registry".** `proxy_slot` is a key. The credential
   store lives outside both repos at mode 0600 and is referenced by **path + custody ref**. The
   repo tree may hold an example file (`proxies.example.yml`); it may not hold a live one,
   gitignored or otherwise. One `git add -f`, one packaging step or one `rsync` of a working
   directory is the whole distance between a gitignore rule and sixteen leaked proxy credentials.
   The validator refuses any credential-like value: a URL carrying userinfo, a 32+ character
   base64-looking string, or any key named `password`/`secret`/`token`/`seed`. A receipt's
   `sha256` digest is itself the evidence and is exempt.
3. **`registry_revision` bumps on any mutation.** The harness refuses to launch if the revision it
   validated against differs from the revision on disk — a registry edited mid-run is drift.
4. **`binding.cdp_port` is unique across the fleet.** Two identities on one port is a collision,
   not a shared resource. Retired entries are exempt: the port leaves uniqueness at retirement
   while its history stays auditable.
5. **`state` is the only launch gate input.** Bio-link policy, voice and cadence never gate a
   launch; they gate content.
6. **Strict keys, fail-closed.** Unknown top-level key, unknown entry key, unknown binding key →
   refuse. An unknown `schema_version` is exactly ONE refusal ("unknown schema_version …
   refusing to parse") and no field validation runs.

## Lock file (`registry.lock.yml`) — the mutation-without-bump check

```yaml
schema_version: 1
registry_revision: 7
entries:
  desk.and.dusk: {revision: 1, state: proposed, sha256: <hex>, receipt_sha256: null}
domains:
  www.mastermind-x.com: {state: admitted, sha256: <hex>}
```

`sha256` = `hashlib.sha256(json.dumps(entry_minus_revision, sort_keys=True,
separators=(",",":")).encode()).hexdigest()` where `entry_minus_revision` is the entry mapping
without the `revision` key (domains: the whole record). `registry.canonical_sha(mapping,
drop=("revision",))` is the one public helper and the lock writer uses it.

`registry.write_lock(doc) -> dict` produces the lock mapping (pure; caller writes it). The CLI
gets `registry-lock` that writes the lock — the explicit bump ceremony. This is the ONLY writer.

`registry.check_lock(doc, lock) -> list[str]` refuses when:

- lock `schema_version`/`registry_revision` ≠ doc's → "registry_revision drift" (document edited
  without bump, or lock stale).
- entry in doc not in lock, or in lock not in doc → refuse (new/removed identity without re-lock).
- entry sha ≠ lock sha AND revision == lock revision → "entry mutated without revision bump".
- entry revision < lock revision → refuse (revision went backwards).
- entry sha == lock sha AND revision ≠ lock revision → refuse (bump without mutation is a forged
  ceremony).
- state transition from lock.state → doc.state not in the legal set:
  - proposed→admitted (needs receipt), admitted→suspended (needs drift fields), suspended→admitted
    (needs receipt whose sha256 ≠ lock.receipt_sha256 — re-admission is a NEW event), any→retired,
    X→X (no change).
  - everything else (admitted→proposed, suspended→proposed, retired→anything, proposed→suspended)
    → refuse with "suspension is sticky" / "retired is terminal" / etc.

## Validator behaviour

Pure function, no I/O, no clock of its own. House style (matching `validators.py`): every
refusal is a human-readable string in a `list[str]`; empty list means pass; the only exception
is a `TypeError` guard for wrong argument types.

```python
def load_registry(path: str) -> tuple[dict | None, list[str]]
def load_lock(path: str) -> tuple[dict | None, list[str]]
def validate_document(doc: dict) -> list[str]
def validate_bindings(doc: dict, personas: Mapping[str, Any], credential_slots: Iterable[str]) -> list[str]
def check_lock(doc: dict, lock: dict) -> list[str]
def check_revision(doc: dict, expected_revision: int) -> list[str]
def launchable(doc: dict, handle: str) -> list[str]
def links_outside_domain(text: str, entry: dict) -> list[str]
def validate_bio_against_registry(text: str, doc: dict, handle: str, *, display_name: str = "") -> list[str]
def validate_all(doc, lock, personas, credential_slots, expected_revision=None) -> list[str]
def write_lock(doc: dict) -> dict
def canonical_sha(mapping: Mapping, drop: tuple[str, ...] = ()) -> str
```

- `validate_document` covers the schema and the intra-document rules: key sets, state and policy
  enums, per-state receipts/binding/drift fields, mail-host allowlist, cdp uniqueness (excluding
  retired), child_id shape and uniqueness, retired_from, and the no-credentials scan.
- `validate_bindings` is the persona↔entry symmetry check in BOTH directions (persona without a
  registry entry and registry entry without a persona are both refusals), plus `proxy_slot ∈
  credential_slots` for admitted/suspended entries. Retired entries are exempt from the
  persona-present requirement, but a persona file for a retired handle IS a refusal.
- `launchable` is the launch gate input: `[]` iff the entry exists and `state == admitted`. It
  never mutates the document.
- `links_outside_domain` reports, per URL, whether its host ≠ the entry's declared domain ("a
  post may not carry a link outside the declared domain").
- `validate_bio_against_registry` returns the refusals on ONE bio: entry must exist; policy
  `none` ⇒ any link is a refusal; otherwise the domain record must exist AND be admitted, then
  `validators.validate_bio(text, child_id=entry.child_id, known_ids=all child_ids,
  display_name=display_name)` runs, plus a refusal for any link whose host ≠ `entry.domain`.
- `validate_all` concatenates in that order and stops after `validate_document` if it returned a
  schema_version refusal. `lock=None` is itself a refusal ("fail-closed"): a check that could not
  run is never a pass.

Operator CLI (read-only side): `python -m tools.xguerrilla.cli registry-check --registry
<path> [--lock <path>] [--personas <dir>] [--proxies <path>] [--expect-revision N]` loads
registry, lock (default: `<stem>.lock.<rest>` beside the registry, e.g. `registry.lock.yml`; a
missing lock file is a refusal, exit 2), personas and credential slots, runs `validate_all`, prints one refusal per line,
and exits 0 on pass / 2 on any refusal (including a missing registry file). The write side is
`registry-lock --registry <path> --lock <path>`: `validate_document` must return `[]` first, then
the lock is written, else it exits 2 and writes nothing.

## Schema amendments vs the 2026-11-07 draft

The draft (`spec` on branch `xg/observer-and-registry-v1`) skipped several decisions; this
document is the binding version on main. Deltas:

- **`schema_version` and `registry_revision` live at document level, and each entry carries its
  own per-entry `revision`** — the draft had `registry_revision` and `schema_version` as
  per-entry keys, which could drift between rows of the same document.
- **`child_id` added** (`^[a-z0-9]{4,32}$`, unique): the immutable attribution key feeding
  `validators.validate_bio(known_ids=...)` — the bio path segment, never the handle.
- **`recovery_owner` and `bio_link_policy` added** on both domain records and entries: who holds
  recovery (never a credential, same rule as `totp_custodian`), and whether the bio may carry a
  link (`none` refuses every link; `single_canonical` gates on an ADMITTED domain record).
- **`domains` and `mail_domains` records added**: a binding may only point at a declared record;
  the admissibility of a bio link is now a registry fact, not an opinion.
- **The lock file is the mutation-without-bump mechanism.** The draft said "revision bumps on any
  mutation" but had nothing that could detect a bump skipped; the lock carries each entry's
  canonical sha and receipts by handle/domain, and `check_lock` refuses edited-but-not-bumped and
  bumped-but-not-edited alike.
- **Unknown `schema_version` refuses to parse (fail-closed)**: exactly one refusal, no partial
  field validation.
- **The observer contract's `baseline_allowlist` provenance fields** (`added_by`, `added_at`,
  `reason`, `host_seed_sha`) are OUT of this card and owed by the observer card: they span
  surfaces and baselines, not identities.

## Non-goals

This schema does not decide whether a domain or mailbox may be purchased, does not grant any
account, and does not touch posting. Those remain separate-grant items.
