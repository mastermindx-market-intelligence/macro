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
schema_version: 1            # exact int 1; booleans, floats and unknown versions refuse before other fields
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
    drift_observed_at: null          # valid ISO-8601 timestamp string iff suspended; null otherwise
    drift_evidence_ref: null         # non-empty string; same rule
    suspended_by: null               # non-empty seat id string; same rule
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
3. **`registry_revision` bumps on any mutation.** `check_revision(doc, expected)` refuses when the
   revision on disk differs from the one a caller validated against — a registry edited mid-run
   is drift. Today its only caller is `registry-check --expect-revision`; no runtime launch path
   calls it yet (see "Wiring status" below). The sentence "the harness refuses to launch" is
   owed by the runtime wiring, not delivered by this module.
4. **`binding.cdp_port` is unique across the fleet.** Two identities on one port is a collision,
   not a shared resource. Retired entries are exempt: the port leaves uniqueness at retirement
   while its history stays auditable.
5. **`state` is the only launch gate input.** Bio-link policy, voice and cadence never gate a
   launch; they gate content.
6. **Strict keys, fail-closed.** Unknown top-level key, unknown entry key, unknown binding key →
   refuse. An unknown `schema_version` is exactly ONE refusal ("unknown schema_version …
   refusing to parse") and no field validation runs.

## Lock file (`registry.lock.yml`) — exact snapshots and explicit updates

```yaml
schema_version: 1
registry_revision: 7
document_sha256: <64 lowercase hex>
entries:
  desk.and.dusk: {revision: 1, state: proposed, child_id: dsk7q2, sha256: <hex>, receipt_sha256: null}
domains:
  www.mastermind-x.com: {state: admitted, sha256: <hex>}
```

`document_sha256` pins the whole canonical document, including its global revision, mail
allowlist, domains and entries. Each entry `sha256` pins the entry minus `revision`; each
domain digest pins the whole domain record. `registry.canonical_sha(mapping, drop=())` hashes
the sorted-key, compact JSON representation with SHA-256. Receipt paths must be non-empty
strings and receipt digests must be exactly 64 lowercase hexadecimal characters. These are
shape checks: the validator does not open the cited evidence or grant account authority.

`registry.write_lock(doc) -> dict` is the pure formatter. The existing `registry-lock` CLI is
the writer. It validates the document, then validates any existing prior lock **before**
replacing it. A genuinely absent target permits bootstrap. A malformed, incomplete or
unreadable existing target refuses with exit 2 and leaves its bytes unchanged; it is never
silently treated as bootstrap. The examples in this PR carry the complete v1 lock shape.

`registry.check_lock(doc, lock) -> list[str]` is the read-only exact-snapshot check. Global
revision and complete-document digest must match, entry/domain memberships must agree, and
all row pins (including entry revision, child ID, state and receipt digest) must match. A
valid prospective edit remains a refusal until its explicit re-lock has completed.

`registry.check_relock(doc, previous_lock) -> list[str]` validates a prospective update:

- Global revision cannot decrease. Every document mutation advances it. An identical no-op
  re-lock and a global-only checkpoint are allowed. When the prior payload can be reconstructed
  by restoring its global revision, all prior row pins must also agree with that payload.
- Explicit valid entry/domain additions and removals are allowed after a global revision
  advance. For retained handles, `child_id` is immutable, entry revisions cannot decrease,
  mutations require an entry revision advance, and a revision-only entry bump refuses.
- Legal retained-entry transitions are proposed→admitted (with a receipt), admitted→suspended
  (with valid drift evidence), suspended→admitted (with a **new receipt digest** and cleared
  suspension fields), any→retired, and unchanged state. Binding repair alone cannot clear
  suspension. Retired entries cannot transition back to a live state.
- The lock records the last snapshot, not permanent identity history. It does not invent
  tombstones for explicitly removed records or verify an external admission grant. The prior
  lock produced by the existing writer remains the transition baseline.

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
def check_relock(doc: dict, previous_lock: dict) -> list[str]
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
<path> [--lock <path>] [--personas <dir>] [--proxies <path>] [--expect-revision N]
[--skip-bindings]` loads registry, lock (default: `<stem>.lock.<rest>` beside the registry, e.g.
`registry.lock.yml`; a missing lock file is a refusal, exit 2), personas and credential slots,
runs `validate_all`, prints one refusal per line, and exits 0 on pass / 2 on any refusal
(including a missing registry file). `--personas` defaults to the repo personas directory
(`DEFAULT_PERSONAS`) so the persona↔entry binding check runs on the default invocation; a
missing or empty personas directory is itself a refusal (exit 2, "binding check could not run"),
never a silent pass. `--skip-bindings` exists only for the lock-only structural check and prints
a loud `bindings NOT checked` line. The write side is
`registry-lock --registry <path> --lock <path>`: `validate_document` must return `[]` first;
if a prior target exists, loading it and `check_relock` must also succeed. Only then is the
new exact snapshot written. Refusals exit 2 without replacing the previous lock.

## Wiring status (what actually calls this module)

Measured at commit `bdc3debedf` (`xg/pilot-sim-runtime-wiring`, PR #10908), so a reader can
re-run the grep rather than trust the prose:
`git grep -n 'registry\.' -- tools/xguerrilla ':!tools/xguerrilla/tests' ':!tools/xguerrilla/registry.py'`
and `git grep -n '_identity_gates' -- tools/xguerrilla`.

- **Called today:** the two operator subcommands above (`cli.py` `cmd_registry_check` /
  `cmd_registry_lock`) — `validate_all`, `validate_document`, `check_relock`, `write_lock`,
  `load_registry`, `load_lock` on every hand-run gate — **and the runtime path**
  `pilot_sim.run_pilot()` (`pilot_sim.py:639`). `run_pilot` loads personas at
  `pilot_sim.py:666` (`config.load_personas(...)`), then makes **one** call to
  `_identity_gates(...)` at `pilot_sim.py:680` before any clock, report, supervisor, lease
  store or driver exists. Gates that execute on every `run_pilot`:

  | gate | called at | shape |
  |---|---|---|
  | `registry.check_revision` | `pilot_sim.py:586` | `list[str]` |
  | `registry.check_lock` (live mutation on top of the revision) | `pilot_sim.py:590` | `list[str]` |
  | `registry.launchable` (per cohort handle) | `pilot_sim.py:594` | `list[str]` |
  | `registry.validate_bio_against_registry` | `pilot_sim.py:606` | `list[str]` |
  | `registry.links_outside_domain` | `pilot_sim.py:607` | `list[str]` |
  | `admission.preflight` (the whole admission chain) | `pilot_sim.py:620` | raises `AdmissionRefused` |

  (`_identity_gates` is defined at `pilot_sim.py:563`; the seam tests are
  `tests/test_pilot_sim.py:378` non-admitted refusal, `:405` revision/lock mutation,
  `:465` each gate reached from the one call site, `:515` admitted cohort clears it.)
- **Single-call-site invariant:** `_identity_gates` is the *only* runtime consumer of these
  gates, and `run_pilot` is its only caller (`pilot_sim.py:680` — grep finds exactly those two
  occurrences outside tests). Registry refusals and the admission chain meet at that one seam
  on purpose; adding another copy of any check anywhere else on the launch path (a second
  `launchable` loop, a per-post bio re-check, a `preflight` call beside rather than inside)
  breaks the invariant. Extend `_identity_gates`; do not add a sibling.
- **The two plumbing shapes reconciled at that seam:** the registry gates return
  `list[str]`, so each call `refusals.extend(...)` into one local list
  (`pilot_sim.py:575`, extended at `:578`, `:580`, `:586`, `:590`, `:594`, `:606`, `:607`).
  `admission.preflight` instead raises `AdmissionRefused`; its handler
  (`pilot_sim.py:622-629`) takes `exc.public()` (`:625`) — the JSON-safe
  `stage`/`code`/`detail`/`remedy` dict, no endpoint or credential — formats it into **one**
  line, and raises `PilotRefused(refusals + [that line])` so the admission verdict joins the
  same refusal list rather than becoming a second error path. Otherwise `if refusals: raise
  PilotRefused(refusals)` (`:631`); success returns `chain.grant`, the `SlotGrant`, which the
  run only uses for the telemetry admission receipt (`:701-706`). One refusal type, one
  list-shaped payload, on every path.
- **What the live post path enforces meanwhile:** `pilot_sim` already runs
  `validators.validate(...)` on every finalised post, whose absolute zero-URL rule
  (`validators.links_in_text`) refuses *any* link; `links_outside_domain` is the registry-side
  defence that matters only once a post is allowed to carry a canonical link at all. There is
  no bio-writing path in the harness today, so `validate_bio_against_registry` still has no
  post-time sink — it runs at the run seam (`pilot_sim.py:606`) as a cohort-time gate, not per
  post.
- **CI:** the suite runs under the `xguerrilla-identity-registry` job in
  `.github/ci/legacy-jobs.yml`, which is enrolled in `CURATED_EXCLUSIVE` but carries
  `if: ${{ false }}` — enrolment, not execution. Enabling it is a separate CI-weight change.

The registry is no longer operator-gate-only: `run_pilot` reads registry state and refuses the
whole cohort before anything launches. The harness still consumes `personas/*.yml` for voice;
what changed is that registry admission state is now a precondition of the run, not data sitting
behind a hand-run CLI.

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
- **The lock file pins the complete document and per-record identity.** `check_lock` requires
  the completed exact snapshot; `check_relock` enforces revision and transition rules before
  the existing CLI writer replaces the prior snapshot. A per-entry revision-only bump refuses;
  an explicit global-only checkpoint remains valid.
- **Unknown `schema_version` refuses to parse (fail-closed)**: exactly one refusal, no partial
  field validation.
- **The observer contract's `baseline_allowlist` provenance fields** (`added_by`, `added_at`,
  `reason`, `host_seed_sha`) are OUT of this card and owed by the observer card: they span
  surfaces and baselines, not identities.

## Non-goals

This schema does not decide whether a domain or mailbox may be purchased, does not grant any
account, and does not touch posting. Those remain separate-grant items.
