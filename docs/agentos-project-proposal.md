# AgentOS project-proposal compiler — `scripts/agentos_project_proposal.py`

Status: **DRAFT_ONLY compiler** — a pure authoring-edge tool over the existing
Agent OS knowledge plane. It extends the knowledge *authoring* boundary (how a
well-formed `WS-*` record comes into existence) and touches nothing downstream
of authoring: no store write, no API, no credentials, no lifecycle.

Everything in this document is enforced by
`tests/test_agentos_project_proposal.py`, which runs the compiler against the
real `scripts/agentos.py` checker — not a mirror of it.

## 1. Purpose and boundary

The Agent OS record store (`agentos/workstreams/WS-<KEY>.md`) already has a
canonical validator (`scripts/agentos.py validate`). What it does not have is
a way to turn a fully-authored project proposal into a record draft without
hand-writing YAML. This module is that frontend: one authored request in, one
detached record draft out.

What the compiler is NOT, and says so in its own output body:

* **Not a store writer.** `agentos/workstreams/` is never read or written.
  The draft exists only in the returned `content_utf8`. Carrying it into the
  store is a separate publication step this module can neither perform nor
  prove.
* **Not a Git client and not an authority.** `expected_commit` is an
  *obligation the author pins* for that later publisher. The compiler cannot
  verify, mint, advance, or CAS a commit, and its output deliberately says
  nothing about source publication, branches, pull requests, or a default
  branch. Compiling a proposal grants no authority and performs no Git effect.
* **Not a session or lifecycle participant.** A compiled draft carries no
  `created`/`updated` (those are derived from git by the store tooling, never
  authored), no `claim`, no `runtime_ref`, no `wait`, no session/dispatch
  identity, and never records that a conversation happened. `status` is always
  `proposed` and every wave is always `todo`: a proposal has not started, and
  no output of this compiler may claim otherwise.

## 2. API

```python
from scripts import agentos_project_proposal

draft = agentos_project_proposal.compile_proposal(
    request, programs=frozenset(actual_program_keys))
```

* `compile_proposal(request: object, *, programs: set[str]) -> dict` — returns
  a **detached** dict (shares no mutable structure with the request; the
  request is treated as frozen and is never mutated).
* `ProposalError(ValueError)` — raised for every refused input. The message
  names the offending request/record path and the rule that fired.
* `programs` is keyword-only and **fail-closed**: omitting it is a `TypeError`
  at the call site; `None`, an empty set, a non-set (list/tuple), or a set
  with non-string, empty, whitespace-padded, or control-bearing members is a
  `ProposalError`. There is no default program and no default owner — program
  membership must be actual.

## 3. Request schema — `agentos.project_proposal_request.v1`

The request is a mapping with **exactly** these keys; anything missing or
extra (a runtime field, a store handle, a session id) is refused:

| key | law |
|---|---|
| `schema` | exactly `"agentos.project_proposal_request.v1"` |
| `request_id` | strict ASCII `[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}` |
| `expected_commit` | exactly 40 lowercase hex characters |
| `record` | the workstream record, exact keys below |

The `record` is a mapping with **exactly** the twelve authored workstream
fields — every one explicitly authored, no defaults, no inference:

| field | law |
|---|---|
| `key` | UPPER-KEBAB per the canonical `KEY_RE` (checked with `fullmatch` — Python's `$` would admit a trailing newline), ≤ 64 chars; builds `agentos/workstreams/WS-<KEY>.md` |
| `title` | non-blank string, ≤ 200 chars, no control characters |
| `objective` | non-blank string, ≤ 4000 chars; LF and TAB allowed, no other control characters (NUL/CR/ESC/DEL/C1 refused) |
| `status` | exactly `proposed` |
| `program` | non-empty, no surrounding whitespace, ≤ 128 chars, must be in the supplied `programs` catalog |
| `repos` | list of 1..3 canonical repo keys, unique |
| `owner` | non-empty, no surrounding whitespace, ≤ 200 chars, no control characters |
| `class` | canonical enum (research/build/design/adjudication/mechanical) |
| `blast_radius` | canonical enum (reversible/user_facing/irreversible) |
| `ambiguity` | canonical enum (specified/scoped/open) |
| `waves` | 1..16 waves, each with exact keys `id`,`title`,`status` plus optional `depends_on` |
| `next_action` | non-blank string, ≤ 1000 chars; LF/TAB allowed, no other control characters |

Wave fields: `id` non-empty, whitespace-clean, ≤ 64 chars; `title` non-blank,
≤ 200 chars; `status` exactly `todo`; `depends_on` (when present) a list of
existing wave ids. **No other wave keys** — no `pr`, no `adoption`, no
`next_action`, no `wait`: a proposal carries no adoption or runtime claims.

Exact-key closure is the point: `created`, `updated`, `claim`, `owns_paths`,
`runtime_ref`, `wait`, `p0`, `blocked_by` and every other field defined
elsewhere in the workstream schema are **refused** at compile time. An author
cannot smuggle runtime, derived, or ownership state into a draft.

## 4. Canonical join — the checker owns the semantics

After the compiler-local law above, the compiled record is handed to the real
canonical checker:

```python
agentos.check_workstream(record, Path("agentos/workstreams/WS-<KEY>.md"), programs)
```

Any **hard** problem rejects the draft with a `ProposalError` quoting the
checker's own rule and message. The checker therefore owns: enum membership
(from its own `CLASSES`/`BLAST`/`AMBIGUITY`/`REPOS`/`WORKSTREAM_STATUS`/
`WAVE_STATUS` sets — imported, never re-declared here), actual program
membership, wave dependency dangling/cycle analysis, duplicate wave ids, and
key/filename agreement. Warnings do not reject; no warning is reachable for a
`proposed` draft with no `claim`, no `blocked_by`, and no `artifacts`.

One deliberate divergence, inherited knowingly: `depends_on` entries are
type-checked by the compiler, because the canonical checker silently drops
non-string entries — and silently losing a dependency edge is exactly the
failure a proposal compiler must not inherit.

A traversal backstop sits in front of the join: the built path must be exactly
`agentos/workstreams/WS-<KEY>.md` (relative, correct stem), so a key that
would escape the directory is refused even if some future regex change
loosened `KEY_RE`.

## 5. Output schema — `agentos.project_proposal.v1`

The returned dict has exactly these keys:

| key | value |
|---|---|
| `schema` | `"agentos.project_proposal.v1"` |
| `state` | `"DRAFT_ONLY"` |
| `request_id` | the validated request id |
| `request_sha256` | SHA-256 over the **sorted compact JSON of the validated request** (`ensure_ascii=False`, `allow_nan=False`, UTF-8 bytes) — over the input, never over the output |
| `expected_commit` | the pinned obligation, echoed verbatim |
| `work_ref` | `"WS:<KEY>"` |
| `path` | `"agentos/workstreams/WS-<KEY>.md"` (relative construction only) |
| `content_utf8` | the complete record file text |
| `content_sha256` | SHA-256 over `content_utf8` encoded as UTF-8 |

Budgets: the request's canonical JSON must be ≤ 16384 UTF-8 bytes, and the
compiled content ≤ 32768 UTF-8 bytes. Both are checked, and the over-budget
case is reachable while every individual field is inside its own limit — that
is what the budget rule is for.

## 6. Deterministic rendering

* Frontmatter is emitted by `agentos.yaml.safe_dump(record, sort_keys=False,
  allow_unicode=True)` (plus fixed flow style and width) over the compiler's
  **fixed authored key order** — never the caller's dict order. Caller text
  survives byte-exact: CJK, YAML-looking text, LF and TAB are safe-quoted by
  the serialiser and round-trip through `FRONTMATTER_RE` →
  `yaml.safe_load` unchanged. The frontmatter carries **no `schema` key**,
  matching real records.
* The body contains only a static, module-owned explanation plus exactly one
  HTML provenance comment carrying the strict triple
  (`request_id`, `request_sha256`, `expected_commit`). The id is
  charset-bounded strict ASCII and the digests are lowercase hex, so the
  comment can carry no markup and no caller text. The caller's goal, title, or
  objective is never placed in the body.
* Same validated input ⇒ same bytes, verified across `PYTHONHASHSEED`
  values and locales; every ordering the compiler emits comes from a tuple,
  a `sorted(...)`, or `sort_keys=True`, never from set iteration.

## 7. Purity

The compiler performs no filesystem access, no subprocess, no network, and
reads no clock. `Path` is used only for pure relative construction. The test
suite proves this by compiling a full draft with `Path.open`,
`Path.write_text`, `subprocess.*`, and `socket.*` patched to raise — which is
the machine-checked form of the sentence: **this compiler never proves a Git
write, a store write, or a conversation.** A returned draft and its digests
advertise nothing except the validated input and the rendered text.

## 8. Tests (`tests/test_agentos_project_proposal.py`)

* **Canonical join:** every accepted draft round-trips through the real
  `FRONTMATTER_RE` → `yaml.safe_load` → `check_workstream` with zero hard
  problems and parses back to exactly the authored record; the checker's own
  enum sets are the only membership law, and the test asserts the compiler
  carries no parallel copy of them.
* **Determinism and hashes:** repeated compiles are byte-identical; digests
  are recomputed independently in the tests; the request digest is over the
  input, the content digest over the output, and they are distinct quantities.
* **Detachment:** the request is unchanged by a compile; an earlier result is
  unchanged by later mutation of the caller's request object.
* **Refusals:** 119 focused negatives — traversal and newline keys (the
  `$`-vs-`fullmatch` trap), uppercase/short/non-hex commits, missing/padded
  owner, unknown program, `active` status, runtime/extra fields at envelope,
  record and wave scope (`created` timestamps, `claim`, `runtime_ref`,
  `owns_paths`, `pr`, `wait`, `adoption`), duplicate/unknown/too-many repos,
  invalid enums, cyclic/dangling/non-string wave dependencies, wrong types,
  field-limit and canonical-JSON-budget oversize, deep structural junk, and
  every invalid `programs` catalog shape (including omission, which fails
  closed as a `TypeError`).
* **Purity:** the I/O-ban compile described above.

## 9. Integration

The parent integrates this file as `scripts/agentos_project_proposal.py`, the
test file as `tests/test_agentos_project_proposal.py`, and this document into
`docs/`. The test bootstrap works in both layouts: in the integrated tree it
resolves the sibling `scripts/` package from the repo root; in flat staging it
takes the canonical checkout from the ambient `PYTHONPATH` — the same join the
parent integration runs. Run with:

```
python3 -m pytest tests/test_agentos_project_proposal.py
```

## 10. Non-goals

No persistence, no API, no credentials, no lifecycle, no store or Git writes,
no authority decisions, no scheduling or dispatch, no derived fields, and no
second store. Where a rule already exists in `scripts/agentos.py`, this module
imports it instead of restating it.
