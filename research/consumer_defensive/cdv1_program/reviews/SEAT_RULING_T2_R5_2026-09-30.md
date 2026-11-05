# Seat ruling — CDV-1 Task 2, round 5 (R5): one admission order and one chain per fiscal period, 2026-09-30

Seat: CDV-1 Meta-CEO, session `251f88c8`. This record covers what the seat measured on PR #8234 at head `b973d931` (the round-4 lane's return), rulings R5.1–R5.8 and R5.10–R5.14, the amended erratum R4.2a, and the seat commit that implements them. It changes no grant, no placement and no Task 1 freeze. There is no R5.9; the number was withdrawn in drafting and is not reused.

## What the seat measured at `b973d931`

The round-4 lane returned head `b973d9316304`. The seat harness was green on it: file grants, the Task 1 freeze, 51 tests, both job lines, `tests/test_ci_pack.py`, contract-delta and `git merge-tree`. The seat then ran sweeps and probes of its own before commissioning a review. They found two classes of defect.

**Class 1 — an exception that is not the typed one leaves the function.** Ruling R4.5 says no other exception escapes `prepare_pg_workspace` on malformed input. Measured:

| Sweep | Calls | Escapes | Exceptions |
|---|---|---|---|
| every acquisition field | 372 | 32 | `FilingIdentityError`, `IdentityError`, `TypeError` |
| every position of a prior given as a workspace | 9,162 | 25 | `WorkspaceError`, `KeyError`, `AttributeError`, `ValueError` |
| every position of a prior given as a result | 9,563 | 28 | the same four |
| `observed_at` and the acceptance clock | 60 | 34 | `ValueError`, `WorkspaceError`, `ContractError` |
| every transport answer to the traced acquisition | 2,509 | 159 | `AttributeError` (110), `ValueError` (49) |

**Class 2 — the chain state is wrong after the first step.** Each single step passed its test. The defects appear when a result is fed back as `prior`:

- A changed text stayed `complete`. It was never `corrected`.
- Revision 2, prepared again with its own result as `prior`, came back as revision 1 with no predecessor and a new generation id.
- A third version got revision 2 again.
- A next-quarter source, prepared with the fourth-quarter result as `prior`, became revision 2 superseding the fourth-quarter document. Prepared again with its own result, it became revision 1 with a `fetched_at` later than its own first observation.
- A fourth-quarter source, prepared on top of the next-quarter result, became revision 2 superseding the next-quarter document.

**Lenient inputs.** These are the same two classes at the level of one field:

- Clocks: a lower-case `t` was admitted as an acceptance clock. A single-digit month, full-width digits and year 0001 were copied into the output as `source_clock`. An `observed_at` without `Z`, with an offset, with a space or with a fraction was admitted, and `generated_at` carried that string as written.
- `form`, `filing_date`, `report_date` and `exhibit_url` admitted any value, `None`, `5`, `[]` and `{}` included.
- The prior was read either as a bare workspace or as a result, and a prior holding both shapes was admitted.
- The issuer fell back to P&G's CIK (`or PG_CIK`), which R4.1 forbids.

Round 4 closed the six findings its packet named. It left both classes open for every value and every sequence the packet did not name.

## Why the seat wrote this round itself

The program's default is that lanes do the labor and the seat makes only small commits that a ruling dictates. This round is not small. The seat records the departure, as it did for Task 3 round 6, for the same reasons:

- Rounds 3 and 4 were lane rounds. Each closed the instances its packet listed.
- The operating brief says: "If the same semantic defect class survives again, propose a bounded design correction rather than another literal special case." The correction is two tables and six properties. Specifying it completely is most of writing it.
- The tests are the tables. A packet that carried them would have been the test file, and a lane would have transcribed it.

The cost is that the seat cannot accept this work. The independent check is a bounded Opus re-review of the pushed head. The suite's sweeps and the mutant specification are evidence anyone can re-run; the seat's own probes below are testimony.

## The properties R5 is held to

- **P1 — typed boundary.** For every value at every position of `acquisition`, `prior` and `observed_at`, `prepare_pg_workspace` returns a result or raises `PgPreparationRefused`. The refusal's `reason` is in `PG_PREPARATION_REFUSALS` and its `detail` is a non-empty `str`. No other exception leaves the function because of an argument. No method of an argument value runs before its exact type is known.
- **P2 — consistent result.** Every returned result satisfies all of these:
  - `workspace["generation_id"]` equals `preview_generation_identity({event_id: workspace}, workspace["generated_at"])`;
  - `workspace["sources"][0]["source_sha256"]` is the SHA-256 of `decoded_source.encode("utf-8")`, and `source_texts == {<release document id>: decoded_source}`;
  - `received_byte_receipt` is `{"sha256", "length", "declared_encoding": "utf-8"}` for those same bytes, and `document_metadata["content_sha256"]` and `["content_bytes"]` repeat it;
  - `document_metadata` names the release row's `document_id` and `filing_key` and the workspace's `event_id`;
  - `document_metadata["fetched_at"]` equals `workspace["lifecycle"]["observed_at"]`;
  - `published_at`, `available_at`, `lifecycle["source_available_at"]` and `currentness_context["source_available_at"]` all equal the acquisition's `acceptance_datetime`, which is not later than the first observation;
  - `revision == 1` exactly when `supersedes_document_id is None`, and a document never supersedes itself;
  - `lifecycle["state"]` is `complete` or `corrected`;
  - every clock is canonical (R5.3);
  - every value has an exact JSON type (`dict` with `str` keys, `list`, `str`, `int`, `float`, `bool`, `None`), except `currentness_context["fiscal_scope"]`, a `tuple` of four ISO dates.
- **P3 — typed acquisition.** The transport answers each URL with an `(int, bytes)` pair or raises `RefreshError`. For every such answer, `acquire_results_filing(..., trace=<callback>)` returns an acquisition or raises `RefreshError`.
- **P4 — composition.** Every acquisition P3 returns is either prepared into a P2 result or refused with `PgPreparationRefused`.
- **P5 — reuse.** Prepare an acquisition, then prepare the same acquisition again with the first result as `prior`. At any `observed_at` not earlier than the acceptance, and under any currentness, the second result has the same `workspace`, `document_metadata`, `decoded_source`, `source_texts` and `received_byte_receipt`. Only `currentness_context["currentness"]` follows the run.
- **P6 — one fiscal period per chain.** A prior of another fiscal period never enters the result. A prior of an earlier period gives exactly what `prior=None` gives. A prior of a later period is refused. A prior of another issuer is refused.

## Rulings R5.1–R5.14 (binding on PR #8234)

### R5.1 — type tests by identity, before anything is called
- A position admits one exact type, tested with `type(x) is T`: `dict` (and every key `type(k) is str`), `list`, `str`, `int`.
- Nothing is called on a value before that test passes: no `.get`, `in`, `==`, `len`, `hash`, iteration or `str()`.
- The Task 2 section contains no `isinstance` call, no `issubclass` call, no `__class__`, and no comparison of `type(x)` other than `is` / `is not`.
- Two helpers carry this: `_exact_mapping(value)` and `_exact_text(value, pattern)`.

### R5.2 — one admission order; every refusal names its position
The first failing check decides. `detail` is the literal in the last column.

| # | Check | `reason` | `detail` |
|---|---|---|---|
| 1 | `acquisition` is an exact mapping | `malformed_acquisition` | `acquisition` |
| 2 | `acceptance_datetime` is a canonical clock | `malformed_source_clock` | `acquisition.acceptance_datetime` |
| 3 | `exhibit_body` is an exact `str`, not blank | `malformed_acquisition` | `acquisition.exhibit_body` |
| 4 | `exhibit_body` encodes as UTF-8 | `non_utf8_source` | `acquisition.exhibit_body` |
| 5 | `cik` is ten ASCII digits | `unadmitted_issuer` | `acquisition.cik` |
| 6 | `accession` is `NNNNNNNNNN-NN-NNNNNN` | `malformed_acquisition` | `acquisition.accession` |
| 7 | `form` is exactly `8-K` or `8-K/A` | `malformed_acquisition` | `acquisition.form` |
| 8 | `filing_date` is `""` or a real `YYYY-MM-DD` date | `malformed_acquisition` | `acquisition.filing_date` |
| 9 | `report_date`, the same rule | `malformed_acquisition` | `acquisition.report_date` |
| 10 | `exhibit_url` is 1–2048 printable ASCII characters, no whitespace | `malformed_acquisition` | `acquisition.exhibit_url` |
| 11 | `currentness`, when the key is present, is an exact mapping with exactly `state` and `checked_at` | `malformed_currentness` | `acquisition.currentness` |
| 12 | `currentness.state` is one of the three tokens | `malformed_currentness` | `acquisition.currentness.state` |
| 13 | `currentness.checked_at` is `None` for `currentness_unverified`, else a canonical clock | `malformed_currentness` | `acquisition.currentness.checked_at` |
| 14 | `received_bytes` is an exact mapping | `missing_received_byte_receipt` | `acquisition.received_bytes` |
| 15 | `received_bytes.sha256` is 64 lowercase hex characters | `missing_received_byte_receipt` | `acquisition.received_bytes.sha256` |
| 16 | `received_bytes.length` is an exact `int`, not negative | `missing_received_byte_receipt` | `acquisition.received_bytes.length` |
| 17 | `declared_encoding` is exactly `"utf-8"` | `non_utf8_source` | `acquisition.declared_encoding` |
| 18 | `observed_at` is a canonical clock | `malformed_observation_clock` | `observed_at` |
| 19 | the prior's shape (R5.4) | see R5.4 | see R5.4 |
| 20 | `observed_at` is not earlier than the acceptance | `malformed_observation_clock` | `observed_at` |
| 21 | the receipt describes `exhibit_body.encode("utf-8")` | `received_bytes_mismatch` | `acquisition.received_bytes` |
| 22 | the admitted registry resolves the CIK | `unadmitted_issuer` | `acquisition.cik` |
| 23 | the fiscal scope can be computed from the acceptance date | `malformed_source_clock` | `acquisition.acceptance_datetime` |
| 24 | the document period verdict is `None` or `scope` | `document_period_not_admitted` | `acquisition.exhibit_body` |
| 25 | the prior is the same issuer (R5.14) | `malformed_prior` | `prior.workspace.sources.filing_key.cik` |
| 26 | the prior is not of a later fiscal period (R5.14) | `source_precedes_prior_event` | `prior.workspace.fiscal_period` |
| 27 | a carried first observation is not earlier than the acceptance (R5.5) | `malformed_prior` | `prior.workspace.lifecycle.observed_at` |
| 28 | a recorded run clock is not earlier than the predecessor's first observation (R5.5) | `malformed_observation_clock` | `observed_at` |
| 29 | the native build succeeds (R5.6) | `workspace_build_refused` | the exception class name |
| 30 | the prior's `event_id` agrees with its period (R5.14) | `malformed_prior` | `prior.workspace.event_id` |
| 31 | the same native document id appears only when the source is carried (R5.13) | `malformed_prior` | `prior.workspace.sources.document_id` |

Keys the table does not name (`items`, for one) are not read.

### R5.3 — one canonical clock, one date
- **Clock.** A canonical clock is an exact `str` that fully matches `[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z` and that `datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)` constructs. Year `0000`, month `13`, second `60`, a lower-case `t` or `z`, a fraction, an offset, a space and a non-ASCII digit are all refused.
- **One parser.** `_canonical_clock` reads `acceptance_datetime`, `observed_at`, `currentness.checked_at` and the prior's `lifecycle.observed_at`. Clocks are compared as the instants it returns.
- **Never** `strptime`, `fromisoformat` or a `strftime` round trip: each accepts forms the canonical form excludes, or differs by platform.
- **Date.** `filing_date` and `report_date` are `""` (a typed absence) or an exact `str` matching `[0-9]{4}-[0-9]{2}-[0-9]{2}` that `date(year, month, day)` constructs.

### R5.4 — the prior is the previous result
`prior` is `None` or the previous result of `prepare_pg_workspace`. Only `workspace` and `document_metadata` are read from it, and only these positions, in this order:

| # | Check | `reason` | `detail` |
|---|---|---|---|
| 1 | `prior` is an exact mapping | `malformed_prior` | `prior` |
| 2 | `prior["workspace"]` is an exact mapping | `malformed_prior` | `prior.workspace` |
| 3 | `prior["document_metadata"]` is an exact mapping | `malformed_prior` | `prior.document_metadata` |
| 4 | `workspace["event_id"]` is a token | `malformed_prior` | `prior.workspace.event_id` |
| 5 | `workspace["fiscal_period"]` is an exact mapping whose `year` and `quarter` are exact `int`, quarter 1–4 | `malformed_prior` | `prior.workspace.fiscal_period` |
| 6 | `workspace["lifecycle"]` is an exact mapping | `malformed_prior` | `prior.workspace.lifecycle` |
| 7 | `lifecycle["observed_at"]` is a canonical clock | `malformed_prior` | `prior.workspace.lifecycle.observed_at` |
| 8 | `lifecycle["state"]` is exactly `complete` or `corrected` | `malformed_prior` | `prior.workspace.lifecycle.state` |
| 9 | `workspace["sources"]` is an exact `list` | `malformed_prior` | `prior.workspace.sources` |
| 10 | the list holds an exact mapping whose `kind` is exactly `issuer_release` (the first one is the release row) | `prior_source_identity_missing` | `prior.workspace.sources` |
| 11 | the release row's `filing_key` is an exact mapping | `prior_source_identity_missing` | `prior.workspace.sources.filing_key` |
| 12 | `filing_key["cik"]` is ten ASCII digits | `prior_source_identity_missing` | `prior.workspace.sources.filing_key.cik` |
| 13 | `filing_key["accession"]` is `NNNNNNNNNN-NN-NNNNNN` | `prior_source_identity_missing` | `prior.workspace.sources.filing_key.accession` |
| 14 | the release row's `source_sha256` is 64 lowercase hex characters | `prior_source_identity_missing` | `prior.workspace.sources.source_sha256` |
| 15 | the release row's `document_id` is a token | `prior_source_identity_missing` | `prior.workspace.sources.document_id` |
| 16 | `document_metadata["document_id"]` equals the release row's | `malformed_prior` | `prior.document_metadata.document_id` |
| 17 | `document_metadata["event_id"]` equals the workspace's | `malformed_prior` | `prior.document_metadata.event_id` |
| 18 | `document_metadata["revision"]` is an exact `int`, at least 1 | `malformed_prior` | `prior.document_metadata.revision` |
| 19 | `document_metadata["supersedes_document_id"]` is `None` for revision 1, else a token other than the document's own id | `malformed_prior` | `prior.document_metadata.supersedes_document_id` |

- A **token** is an exact `str` of 1–128 printable ASCII characters with no whitespace.
- No other position of the prior is read, so no other position can change the result.
- The preparation does not verify the stored prior's content address. That integrity check belongs to Task 4's verified reader.

### R5.5 — the run clock and the first observation
- The source is **carried** when the predecessor (R5.14) has the same accession and the same decoded-text digest.
- **Carried.** The predecessor's first observation is kept. It must not be earlier than the acceptance (row 27). The run clock is not recorded anywhere, so it only has to be canonical and not earlier than the acceptance.
- **Not carried, with a predecessor.** The run clock becomes the first observation. It must not be earlier than the predecessor's first observation (row 28).
- **No predecessor.** The run clock becomes the first observation.

### R5.6 — one backstop
```python
_PREPARATION_BACKSTOP = (TypeError, ValueError, ArithmeticError, LookupError, AttributeError, RecursionError)
```
`prepare_pg_workspace` calls the private `_prepare_pg_workspace` inside one `try`:
- `PgPreparationRefused` passes through unchanged;
- an exception of those six classes becomes `PgPreparationRefused("workspace_build_refused", type(exc).__name__)`, chained with `from exc`;
- every other exception propagates (`MemoryError`, `KeyboardInterrupt`, `AssertionError`, a `RuntimeError` that is not a `RecursionError`).

The native builders raise `ContractError`, `FilingIdentityError` and `BindingError`, all `ValueError` subclasses. The backstop is what makes their refusals typed. It only raises; it never returns a result.

### R5.7 — no default issuer; the profile lookup is typed
- Delete `or PG_CIK`. The filing key is built from the admitted `cik` only.
- `source_family_for_profile(profile)` tests `type(profile) is str` before the lookup. Any other value, and any unmapped string, is `PgPreparationRefused("unsupported_source_profile", "profile")`.

### R5.8 — the traced acquisition is typed
In `scripts/refresh_event_workspaces.py`, `acquire_results_filing` with a `trace` callback calls `_acquire_results_filing_traced` inside one `try`:
```python
_TRACED_ACQUISITION_BACKSTOP = (TypeError, ValueError, ArithmeticError, LookupError, AttributeError, RecursionError)
```
- `RefreshError` passes through unchanged;
- an exception of those six classes becomes `RefreshError(f"results filing acquisition met a malformed response ({type(exc).__name__})")`, chained with `from exc`;
- every other exception propagates;
- the `trace` callback is called after the `try`, so an exception the callback raises is never converted;
- a call that raises may have emitted no trace event;
- the callback-less branch (`trace is None`) is unchanged, byte for byte.

An exception of the six classes raised by the transport itself is converted too. The real transport, `_http_get`, raises only `RefreshError`.

### R5.10 — amends r4 R4.5, third bullet
A prior is a value, not a reader. The read happens in the caller, and the caller's own exception is raised there. `test_prior_read_failure_raises` keeps its name and its `dict` subclass whose `get` raises. It now asserts the refusal `malformed_prior` with detail `prior`, and that `get` was never called. The plan's demand still holds: a failed prior read is an error, never an empty history.

### R5.11 — lifecycle follows the native law
- A changed decoded text for the same fiscal period is a correction: `lifecycle.state == "corrected"`.
- Once corrected, every later preparation of that period stays `corrected`.
- An unchanged text under another accession (a refiling, or an 8-K/A that repeats the text) is not a correction. The state stays what the predecessor's was. It is a new observation: the run clock is recorded.
- The first observation is carried only when accession and text are both unchanged.

The preparation passes the native builder:
- `prior_source_sha256`: the predecessor's digest, or `None` when there is no predecessor or when the text is unchanged under another accession;
- `prior_lifecycle_state`: the predecessor's state, or `None` without a predecessor;
- `prior_observed_at`: the predecessor's first observation when carried, else `None`.

### R5.12 — the generation id is a content address
`workspace["generation_id"] = preview_generation_identity({event_id: workspace}, workspace["generated_at"], previous_generation_id=None)`.
- The previous generation id is never folded in. The run clock is never folded in.
- So an unchanged source reproduces its generation id (P5), and any reader can verify a stored workspace by recomputing it.
- The link to the predecessor lives in `document_metadata` (`revision`, `supersedes_document_id`), not in the generation id.

**Plan basis, and where this departs from the native writer.** The plan says to use `preview_generation_identity(workspaces, generated_at, previous_generation_id=...)` "for native identity without invoking the public writer", to "reuse identical prior content" when nothing changed, and not to "hash a new wall clock into an unchanged economic result simply to create activity". Its file table also notes that the native writer's hashing "includes build clock and predecessor". The native writer folds the predecessor in for one stated reason (its note A4): a content cycle A → B → A must mint a third id distinct from the first. The seat rules the fold out here for three reasons:

- The preparation result is "an in-memory input to Tasks 3-5, not another persisted ledger" (plan, Task 2 interfaces). It does not carry its predecessor's generation id. To reproduce a folded id for an unchanged source, the preparation would have to copy the prior's stored `generation_id`. A value copied from the prior is a value a tampered prior controls, and P2 would no longer hold.
- The cycle A → B → A cannot collide here. The third workspace is `corrected` with a later first observation, so its content differs from the first. The suite asserts eight distinct generation ids over eight chain states, the repeated document id included.
- The observation handle is `(workspace_generation_id, event_id, fact_id)`. A content address makes that handle name one workspace and no other, which is what a pinned source drawer needs.

The chain position that the native fold records is recorded by Task 4's manifest (`previous_manifest`) and by `document_metadata`.

### R5.13 — the document chain follows the native document id
- **No predecessor:** revision 1, `supersedes_document_id` `None`.
- **The native `document_id` equals the predecessor's:** the source must be carried (else row 31). The revision and `supersedes_document_id` are the predecessor's own.
- **Otherwise:** revision is the predecessor's plus 1, and `supersedes_document_id` is the predecessor's `document_id`.
- `fetched_at` is the workspace's first observation (`lifecycle.observed_at`), never the run clock.
- `document_kind` is `release_amendment` for form `8-K/A`, else `release`.
- The native id covers the text, accession, form, filing date, report date and URL. A text that returns to an earlier version (A → B → A) therefore repeats the first id at revision 3. The native `DocumentRevisionChain` admits that.
- **Guard.** `fetched_at` is read back from the workspace the native builder returned. If that clock is not canonical, the preparation refuses with `workspace_build_refused` and detail `workspace.lifecycle.observed_at`. No admitted input reaches this refusal; it exists so that a change in the native builder cannot put a malformed clock into `document_metadata`.

### R5.14 — one fiscal period per chain
The acquisition's fiscal period is the `(year, quarter)` that r4 R4.1 derives. The prior's is `workspace["fiscal_period"]`.
- The prior's issuer must be the acquisition's (row 25).
- **Later period:** refused, `source_precedes_prior_event` (row 26).
- **Same period:** the prior is the predecessor.
- **Earlier period:** there is no predecessor. The result equals the `prior=None` result in every part.
- The native `event_id` must agree: the prior's `event_id` equals the new workspace's exactly when the periods are equal (row 30).

### Amended erratum R4.2a — an unverified currentness carries no clock
This replaces the erratum the seat drafted before the round-4 lane returned. That draft kept the acquisition stamp's `checked_at` for every state and dropped it only in the output.
- For `currentness_unverified`, the acquisition's `checked_at` must be `None` (row 13), and the output `source_clock` is `None`.
- For `up_to_date` and `newer_source_pending`, `checked_at` must be a canonical clock, and the output `source_clock` is that clock.
- An acquisition without a `currentness` key still prepares `currentness: None` (r4 R4.2).
- The traced acquisition stamps a selected acquisition only `up_to_date` or `newer_source_pending`, so this rule refuses no acquisition it returns.

## What R5 amends

- **r4 R4.2**, "`source_clock` … may be `None` only for `currentness_unverified`": replaced by the amended erratum R4.2a.
- **r4 R4.4**, revision "1 unchanged, 2 changed" and the carried-forward `generation_id`: replaced by R5.13 (the predecessor's revision plus 1) and R5.12 (a content address, which an unchanged source reproduces without copying it).
- **r4 R4.4**, the prior read as "the prior workspace's release entry": replaced by R5.4. The prior is the previous result, and its `document_metadata` carries the revision the chain continues from.
- **r4 R4.5**, third bullet ("read failures still propagate"): replaced by R5.10.
- **r4 R4.5**, the closed tuple: it goes from 11 reasons to 14, gaining `malformed_observation_clock`, `source_precedes_prior_event` and `workspace_build_refused`. Every refusal now carries a `detail`.

Everything else in the r3 and r4 packets still binds, including the file grants, pure addition in `pg_profile.py`, and r4's rule on date literals in the Task 2 section.

## Known limits

None of these produces a wrong result for a well-formed acquisition. The seat lists them so the next reader does not have to find them.

- A quarter that ends on 29 February is outside what the scope derivation was tested for. P&G's quarters end in March, June, September and December.
- A body with no period signal is admitted by scope (r4 R4.1, Task 1 R35).
- The native period refuses fiscal years outside its own range. That refusal is typed only by the backstop: `workspace_build_refused` with detail `ContractError`.
- Parsing deeply nested HTML takes quadratic time in Task 1's frozen parser. The suite's deepest answer is 1,000 nested elements. Task 5's collector should cap the size and the run time of what it fetches.
- The preparation cannot tell that a prior of an earlier fiscal period is stale. It returns a root for the new period, as ruled. Rejecting a root for a period that already has a stored chain is the publication seam's job (Task 4).
- Row 27 names the prior, although the acquisition may be the side at fault.
- The URL's host is not checked.
- An exception of the six classes raised by the transport itself is converted (R5.8).
- The acquisition script's own `str(...)` coercions of submission-index fields predate this round and are outside it.

## The commit

| Commit | Files | Size | Content |
|---|---|---|---|
| `09621cc5e527` | `engine/company_intelligence/pg_profile.py` | +353 −187 | The Task 2 section, rewritten to R5.1–R5.7, R5.10–R5.14 and R4.2a. It goes from 278 lines to 444. Nothing above the section marker changes. |
| | `scripts/refresh_event_workspaces.py` | +13 −3 | R5.8: `_TRACED_ACQUISITION_BACKSTOP` and the conversion around the traced branch of `acquire_results_filing`. |
| | `tests/test_pg_economic_source_selection.py` | +1,562 −14 | The suite goes from 33 test functions (51 cases) to 70 (341 cases). The 14 removed lines are one import, two refusal messages, the read-failure expectation (R5.10) and the lines that pass the prior (R5.4). |
| `113323df10cb` | merge of `main` at `c7e1f8edd8e5` | — | `main` now carries Task 3 (#8232). Both sides changed `.github/ci/legacy-jobs.yml`, in different jobs, and the merge needed no resolution. Of the six owned files, the merge changes only that one. |

`113323df10cb9e315c02106bf5ffdf42e1fbfbfa` is the pushed head. The seat committed both as "Sol CEO". No lane ran in this round.

## Verification on the pushed head

This section was never finalized. The round-5 review rejected head `113323df` on finding B1 (`OPUS_T2_PR_REVIEW_R2_2026-09-30.md`), and round 6 superseded it. The verification of the merged head is in `SEAT_RULING_T2_R6_2026-09-30.md`.

The seat's runs on the pushed head were still in progress when the review was commissioned. This section lists what had been measured by then.

**On the merged tree, before the push:**

- The suite: 341 passed.
- `tests/test_ci_pack.py -k "exclusive or curated or contract or legacy_jobs"`: 16 passed, 129 deselected.
- Six files differ from `origin/main`, all owned. `pg_profile.py` and the fixtures file remove no line of `main`'s. The Task 1 freeze diff is empty. The `earnings-economic-dossier` job is byte-identical to `main`'s.
- pyflakes reports only the two lines it reported before this PR.

**On a scratch tree built from `b973d931` plus the three round-5 files, byte-identical to commit `09621cc5e527`:**

- Mutants: 94, each run against the whole suite. All 94 are killed.
- Sweeps, with no escape and no violation of P2 or P5 in any:
  - acquisition: 6,777 calls (567 returned, 6,210 refused with a typed reason);
  - `observed_at` and the acceptance clock: 896 calls (230 returned, 666 refused);
  - prior: 96,983 calls over 40,258 edits (90,993 returned, 5,990 refused);
  - transport: 5,744 answers (2,279 acquisitions returned, 3,465 `RefreshError`), and 4,558 preparations of what was returned (3,950 returned, 608 refused).
- The seat's P2 checker flags all 43 tampers of a valid result in its positive control.
- The chain probe's 80 checks pass, and so do the 22 checks of the probe that feeds Task 2's output to Task 3.

**Still running:** the seat harness, hosted CI, and a re-run of the mutants, sweeps and probes on an export of the pushed head.

## What follows

A bounded Opus re-review of the pushed head, held to P1–P6, the rulings above and the r3 and r4 rulings that still bind. On ACCEPT and concluded CI the seat merges PR #8234 by exact head. There is no Sol hold on Task 2 (Sol `5902318060`).

Task 4's packet then takes these from the merged Task 2:

- `prior` is the latest stored P&G record, passed as `{"workspace": …, "document_metadata": …}`. Task 4 owns the read, a read failure, and the stored prior's integrity.
- A prior of an earlier quarter yields a root for the new period. A root for a period that already has a stored chain must be rejected at publication.
- On `source_precedes_prior_event`, keep the last good record and mark currentness pending.
- The workspace `generation_id` is a content address a reader can recompute. An unchanged source reproduces the prior result exactly.
- Document ids can repeat along a chain (A → B → A). Key stored documents by more than the id, do not treat a repeated id as a cycle, and validate each period's chain with the native `DocumentRevisionChain`.
- The refusal tuple has 14 reasons. Pass a canonical `observed_at` and the ten-digit CIK.
- A traced acquisition call that raises may have emitted no trace event.
- An unverified currentness carries `checked_at: None`. A returned acquisition is only ever `up_to_date` or `newer_source_pending`.
- An exact-accession acquisition can carry any `form`, and is then refused with `malformed_acquisition` and detail `acquisition.form`.
- `currentness_context.fiscal_scope` is a tuple of four ISO dates.
