# CDV-1 T4 — ROUND A of two (new branch `claude/cdv1-t4-private-publication-v2`)

LANE `cdv1_t4_private_publication_r2a` — BUILD CDV-1 Task 4, round A. New-packet mode: you start on a detached HEAD equal to `origin/main` and create the branch by pushing to it. The seat owns readiness, labels, review and merge.

This packet is complete on its own. Where it differs from the plan, the packet rules. Each difference is a seat ruling.

## C0 GATE (first actions; quote the outputs under EVIDENCE)
1. `git fetch origin main`, then quote `git rev-parse HEAD origin/main`. The two must be equal. Never `git checkout -B`; every push is `git push origin HEAD:refs/heads/claude/cdv1-t4-private-publication-v2`.
2. Tasks 1–3 are merged (#7905, #8234 `b1b2ea3b3c65`, #8232 `ddf03116a2f6`). `ls engine/company_intelligence/pg_profile.py engine/earnings_narrative/economic_interpretation.py scripts/refresh_event_workspaces.py tests/earnings_economic_fixtures.py` must list four files. If one is missing, STOP with STATUS BLOCKED.
3. `sed -n '33p' engine/earnings_narrative/private_publication.py` must print `PRIVATE_PREFIX = "earnings_wire_private/v1"`.
4. Reading aid, never a gate: the plan is `docs/superpowers/plans/2026-09-23-consumer-defensive-cdv1-implementation.md` on branch `sol/consumer-defensive-research-20260923` (its own `git fetch`), Task 4. Every plan sentence that binds this round is quoted below.

## MISSION
Teach the one existing private owner, `engine/earnings_narrative/private_publication.py`, to stage and validate a **v2 private generation**. A v2 generation carries native economic evidence beside the existing wire records: Task 2's workspaces, document metadata and source text, and Task 3's interpretation, each bound to the others by digest, identity and clock. This round prepares and validates. It does not publish v2 and adds no reader.

Plan 4.3 binds: "Dispatch on schema and exact key set. Existing v1 code paths must return the same canonical bytes and error behavior." The seat will prepare one v1 stage with main's module and with yours and compare the manifest bytes.

## ROUND B OWNS (do not build it now)
- The v2 publish transaction, the downgrade check on v1 publication, the five readers and their typed errors.
- All CI and deploy wiring: `.github/ci/legacy-jobs.yml`, `tests/test_ci_pack.py`, `app/deploy/update.sh`, `tests/test_deploy_update_self_heal.py`. Never edit them.

Hosted CI on this round's head will be red in the CI-manifest checks and in the deploy restart guard: the new test file is in no job yet, and the owner now imports modules those lists do not name. That is expected. Do not fix it, do not run those two test files, and do not count it against your STATUS.

## HARD LAWS (violations are seat-reportable)
- Never `git add -A`; add named files only. Never force-push, rebase, amend, or use bare `git stash`/`pop`.
- Never `gh pr ready|merge|edit|review|comment`, and never add labels. At most 3 `gh` calls in total and no CI polling.
- Never print, copy or open credentials (`~/.glm`, `~/.minimax`, `~/.codex/auth*`, `ext/glm_shim/.token`, any `.env`).
- Never write outside OWNED FILES. Never write under `data/` or `site/`: this is a SPARSE tree, and a write there truncates committed artifacts.
- Never edit STSI PR #7777's paths. Never touch the research carrier PR #7792 or its branch.
- Do not stop to ask questions and never end on a status note. Record blocks under GAPS and finish the packet. A lane that ends with "I'm finishing…" commits nothing and is a wasted slot.
- All numbers in fixtures are SYNTHETIC test values, never copied live P&G facts. No research value may be converted into a native receipt. No test uses the network.
- Reported and core EPS are separate definitions; organic sales are not household consumption; combined volume/mix is not pure volume; all rank/gate/size/originate/entry/Prophet effects stay literal false; the LLM never originates a signal.
- Trailer on EVERY commit: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Push with `git push origin HEAD:refs/heads/claude/cdv1-t4-private-publication-v2` (no force). Treat "Everything up-to-date" as FAILURE when a commit was expected.

## FILES
OWNED (the only files you may change or create):
- `engine/earnings_narrative/private_publication.py`
- `tests/test_earnings_economic_private_store.py` (new)
- `tests/earnings_economic_private_fixtures.py` (new)

FROZEN (never edit; a failing frozen test is a finding for GAPS):
- Task 1: `engine/company_intelligence/{pg_envelope,economic_observations,issuer_profiles,pg_profile}.py`, every `tests/test_pg_envelope_f1*.py` and `tests/test_pg_economic_observations*.py`, `tests/fixtures/pg_envelope/**`.
- Task 2: `scripts/refresh_event_workspaces.py`, `tests/test_pg_economic_source_selection.py`, `tests/earnings_economic_fixtures.py`.
- Task 3: `engine/earnings_narrative/economic_interpretation.py`, `tests/test_earnings_economic_interpretation.py`, `tests/earnings_economic_interpretation_fixtures.py`.
- `tests/test_earnings_private_store.py`, the legacy suite. Import its helpers; never edit it. It must stay `18 passed`.
- `research/**` and every other file in the repository.

## MEASURED INTERFACES (seat probes on main; build on these, do not re-derive them)
```python
import engine.company_intelligence.pg_profile as PG
import engine.company_intelligence.event_workspace as EW
import engine.company_intelligence.documents as DOC
import engine.earnings_narrative.economic_interpretation as EI
import scripts.refresh_event_workspaces as R
import tests.earnings_economic_fixtures as FX

R._PACE_S = 0                                  # restore the old value in a `finally`
def acquire(case):
    acq = R.acquire_results_filing(cik="0000080424", http_get=FX.fixture_http_get(case), trace=[].append)
    acq["currentness"] = {"state": "up_to_date", "checked_at": "2026-07-30T20:00:00Z"}   # pins the run clock
    return acq
v1 = PG.prepare_pg_workspace(acquire("same_source_rebuild"), prior=None, observed_at="2026-07-29T17:10:00Z")
v2 = PG.prepare_pg_workspace(acquire("changed_bytes"), prior=v1, observed_at="2026-07-30T17:20:00Z")       # corrected, revision 2
v3 = PG.prepare_pg_workspace(acquire("amendment_sequence"), prior=v1, observed_at="2026-07-30T18:01:00Z")  # amended, revision 2

v = v1; W = v["workspace"]; D = v["document_metadata"]; ctx = v["currentness_context"]
texts = {D["document_id"]: v["decoded_source"]}
sel = {"facts": None, "currentness": ctx["currentness"]}
p = EI.build_economic_interpretation(W, source_texts=texts, fiscal_scope=tuple(ctx["fiscal_scope"]), selection=sel,
                                     semantic_revision=EI.SEMANTIC_REVISION, code_revision=EI.CODE_REVISION)
EI.validate_economic_interpretation(p, workspaces=W, source_texts=texts, fiscal_scope=tuple(ctx["fiscal_scope"]))
EW.validate_event_workspace(W)
EW.preview_generation_identity({W["event_id"]: W}, W["generated_at"], previous_generation_id=None) == W["generation_id"]
fields = {k: x for k, x in D.items() if k not in ("schema", "authority", "filing_key")}
DOC.SourceDocument(**fields, filing_key=DOC.FilingKey(**D["filing_key"])).to_payload() == D
```
- With the run clock pinned as above, two builds give byte-identical results.
- A prepared result has exactly the keys `workspace`, `document_metadata`, `decoded_source`, `source_texts`, `received_byte_receipt`, `currentness_context`. It carries no raw bytes.
- W is about 27 KB of canonical JSON. `W["generation_id"]` is 24 lowercase hex. `W["issuer"]["company_id"]` is `"cik:0000080424"`. `W["lifecycle"]` has `source_available_at`, `observed_at`, `state`. `W["sources"]` is a list with exactly one row of `kind == "issuer_release"`; that row has `document_id`, `filing_key`, `source_sha256` and four more keys.
- D is under 1 KB. It has `document_id`, `event_id`, `revision`, `supersedes_document_id`, `content_sha256`, `content_bytes`, `available_at`, `fetched_at`, `rights_profile`, `rights_state`, `holds_bytes`, `filing_key` and seven more keys. `D["schema"] == DOC.DOCUMENT_SCHEMA`, `D["authority"] == DOC.AUTHORITY`.
- With `body = v["decoded_source"].encode("utf-8")`: `v["received_byte_receipt"] == {"sha256": sha256(body), "length": len(body), "declared_encoding": "utf-8"}`, `D["content_sha256"] == sha256(body)`, `D["content_bytes"] == len(body)`, and the release row's `source_sha256 == sha256(body)`. Task 2 admits a source only when its received bytes are exactly the UTF-8 bytes of its decoded text.
- `ctx` is `{"profile_version": "pg_profile.v1", "fiscal_scope": (four ISO date strings), "currentness": {"state", "source_clock"}, "source_available_at"}`.
- `p` has exactly the 14 keys of `EI.TOP_LEVEL_KEYS`, `p["schema"] == EI.SCHEMA`, `p["interpretation_id"]` is `econ_` plus 64 hex, `p["issuer"]["company_id"]` and `p["event_id"]` match W. The fixture gives 20 observations (2 are typed absences, which carry a `typed_absence` key) and 2 comparisons. `p["observations"][i]["handle"]` is exactly `{"workspace_generation_id", "event_id", "fact_id"}`. `selection["facts"]` may be `None` (every row) or a list of such handles.
- **Task 3's validator refuses a payload whose top-level keys are not in `EI.TOP_LEVEL_KEYS` order.** Canonical JSON sorts keys, so reorder a stored payload before validating it (R-A7 stage 4).
- A rebuild from a JSON round trip of the same inputs gives byte-identical canonical JSON.
- The chain is v1 then v2, or v1 then v3. The later document has `revision == 2` and `supersedes_document_id == v1's document_id`. v3's text is the same text as v1's.
- **The native validators are permissive.** `validate_event_workspace` accepts a month-13 or offset-form `observed_at`, an `observed_at` earlier than the source clock, and a changed issuer or event id. `preview_generation_identity` ignores the stored id, so a workspace with a wrong id still validates. `SourceDocument` accepts `holds_bytes True`, the public rights profile, and a root that supersedes itself. R-A7 checks all of these itself.
- `PG.pg_private_registry().get(company_id)` returns the issuer or `None`; it admits only `cik:0000080424`. `PG.RIGHTS_PROFILE` is the public rights profile and `PG.PG_PRIVATE_RIGHTS_PROFILE` the private one; `PG.source_family_for_profile(PG.RIGHTS_PROFILE)` returns `"sec_edgar"`. Never type either rights-profile string: import the constants.
- `canonical_json_bytes` (already imported by the owner) is sorted-key compact UTF-8 JSON plus one `\n`.

## SEAT RULINGS R-A1–R-A12 (binding)

### R-A1 — the module header; line 33 is pinned
Another program's receipts cite line 33 of the owner. Lines 13–33 become exactly this, and nothing else may be added above line 33:
```python
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import threading
from types import MappingProxyType
from typing import Any, Mapping

from engine.company_intelligence import documents, event_workspace, pg_profile
from engine.earnings_narrative import economic_interpretation
from engine.earnings_narrative.context_packets import (canonical_json_bytes, validate_context_manifest,
                                                      validate_context_packet_at_cutoff)
from engine.research_vault.r2_store import StrictBoundedReadStore, Store
from engine.theme_graph import rights

PRIVATE_PREFIX = "earnings_wire_private/v1"
```
Lines 1–12 (the docstring) stay as they are. Any note about the pin goes in a comment below the constants. Reach every Task 1–3 name through these module imports (`pg_profile.pg_private_registry()`, never a `from … import` of the function), so a test can patch the module attribute.

### R-A2 — constants (added below the existing constants; every v1 constant stays)
`RECORD_SCHEMA_V2 = "earnings.tier_payload/v2"`, `MANIFEST_SCHEMA_V2 = "earnings.private_manifest/v2"`, `DOSSIER_PAGE = "earnings_economic_dossier"`, `NATIVE_STAGE_DIR = "native"`, `NATIVE_STAGE_MANIFEST_NAME = "latest.json"`, `NATIVE_STAGE_SCHEMA = "earnings.private_native_stage/v1"`, `MAX_NATIVE_CHAIN = 4`, `MAX_ECONOMIC_FACTS = 24`, `MAX_ECONOMIC_COMPARISONS = 24`, `MAX_SOURCE_BODY_BYTES = 8 * 1024 * 1024`, `MAX_NATIVE_WORKSPACE_BYTES = 2 * 1024 * 1024`, `MAX_NATIVE_DOCUMENT_BYTES = 64 * 1024`, `MAX_NATIVE_STAGE_MANIFEST_BYTES = 1024 * 1024`, `RECORD_UNAVAILABLE_REASONS = ("no_native_selection",)`, `NATIVE_RIGHTS_REGISTRY_PATH = None`, and `CLOSURE_REASONS`, a tuple of the 17 reasons of R-A3 in that order.

### R-A3 — one typed error with a closed reason set
`class EarningsPrivateClosureError(EarningsPrivatePublicationError)` with `__init__(self, reason, message=None)` and a `.reason` attribute. A reason outside `CLOSURE_REASONS` is a programming error (`ValueError`). `str(exc)` is `message` when given, otherwise one fixed sentence per reason. A message may name a field path. It never contains a body excerpt, an object key or a digest. Every v2 refusal in this round raises this class. Every v1 refusal keeps its current class and message.

| reason | meaning |
|---|---|
| `unsupported_schema` | a record, manifest or native stage manifest names an unknown schema |
| `malformed_native_section` | a v2 field has the wrong shape, type or pairing; a native object is not canonical JSON, fails its native validator or round trip, or carries a rights field R-A7 does not allow |
| `unsafe_path` | a symlink, a path escape, or an id or object key that is not in the exact form used to build a path |
| `missing_artifact` | something the generation names is not there |
| `unexpected_artifact` | an object, stage file or catalog entry that nothing names |
| `wrong_role` | an object key with another role's suffix, or one object key under two roles |
| `digest_mismatch` | bytes that do not hash to their receipt, file name or identity |
| `size_mismatch` | bytes whose length differs from their receipt |
| `over_limit` | more than 4 chain entries, 24 facts or 24 comparisons, or a body over its role maximum |
| `mismatched_source` | a document, release row, transport receipt and stored body that do not name the same source |
| `cross_issuer` | an issuer the private registry does not admit, or a selection, workspace and record that name different issuers |
| `broken_chain` | revisions not 1..n, a supersession link that does not name the entry before, or a source clock that steps back |
| `predecessor_cycle` | an entry that supersedes itself or a later entry |
| `future_source_clock` | a clock later than `native_source_cutoff`, or a source clock later than its own first observation |
| `interpretation_mismatch` | a stored interpretation that is not what Task 3 rebuilds from the stored evidence |
| `interpretation_unsupported` | an interpretation schema, revision or profile version this code does not support |
| `rights_refused` | the rights seam refused |

Over-limit content is refused whole. Nothing is ever truncated to fit.

### R-A4 — roles fix suffix, media type and maximum
Plan 4.3: "Extend `_artifact`/receipt validation with role-fixed media type and suffix for source bodies; callers cannot choose an arbitrary content type/path."

| role | suffix | media type | maximum |
|---|---|---|---|
| `record`, `context_manifest`, `context_packet` | `.json` | `application/json` | unchanged |
| `native_workspace` | `.json` | `application/json` | `MAX_NATIVE_WORKSPACE_BYTES` |
| `native_document` | `.json` | `application/json` | `MAX_NATIVE_DOCUMENT_BYTES` |
| `source_body_text` | `.txt` | `text/plain; charset=utf-8` | `MAX_SOURCE_BODY_BYTES` |

- One table in the module holds these. `PrivateArtifact` gains `content_type: str = "application/json"` as its last field. An object key is `f"{PRIVATE_PREFIX}/objects/sha256/{digest[:2]}/{digest}{suffix}"`. v1 keys and v1 receipts do not change, and `_OBJECT_KEY_RE` is not widened.
- A **native receipt** is exactly `{"object_key", "sha256", "bytes"}`. `sha256` is a `str` of 64 lowercase hex and `bytes` is an `int` (not `bool`) of at least 1, else `malformed_native_section`. `bytes` over the role maximum is `over_limit`. `object_key` must be a `str` equal to the one key its role and digest give. If it is that key with another role's suffix, the reason is `wrong_role`. Any other value is `unsafe_path`.
- **One stored body per source (seat ruling).** Plan §2.4 stores the received and the decoded body "only … when they differ". Task 2 never admits a differing source and hands over no raw bytes, so v2 stores the decoded text's UTF-8 bytes once and binds the transport receipt to them. There is no raw-byte role in this schema.

### R-A5 — records
Plan 4.3 gives the dispatch; keep its three branches and its last message:
```python
if value.get('schema') == 'earnings.tier_payload/v1':
    return validate_v1_record(value, expected_slug=expected_slug)
if value.get('schema') == 'earnings.tier_payload/v2':
    return validate_v2_record(value, expected_slug=expected_slug)
raise EarningsPrivatePublicationError('unsupported private record schema')
```
- `validate_private_record` becomes this dispatch. A value whose type is not exactly `dict` goes to `validate_v1_record`, which keeps refusing a non-mapping with its current message. The last branch raises `EarningsPrivateClosureError("unsupported_schema", "unsupported private record schema")`.
- `validate_v1_record` is today's validator, moved without a change in behavior or messages. Add every new public name to the module's `__all__`.
- A **v2 record** has exactly the eight v1 keys plus `economic_interpretation`. Faults in the eight shared fields keep the v1 messages (share the v1 checks; do not copy them). Faults in the addition raise `malformed_native_section` unless stated.
- `economic_interpretation` is one of two things. (i) **An interpretation object**: a `dict` whose `schema` is `economic_interpretation.SCHEMA` (else `interpretation_unsupported`), whose key set is exactly `TOP_LEVEL_KEYS`, whose `interpretation_id` and `event_id` are `str`, whose `issuer` is a `dict` with a `str` `company_id`, and whose `observations` and `comparisons` are lists of at most 24 (else `over_limit`). (ii) **The unavailable result**: exactly `{"state": "unavailable", "reason": "no_native_selection"}`. A dict whose key set is `{"state", "reason"}` must equal it.
- `page == "earnings_wire_article"` (a wire record): every v1 rule applies, and (i) or (ii) is allowed.
- `page == DOSSIER_PAGE` (a native-only record; plan: "A native-only record may coexist with the real existing wire/context generation; it does not require a PG story packet."): `required_tier == "essential"`, `public_facts == 0`, `facts_html == ""`, `receipt_rows_html == ""`, (i) is required, and `locked_facts == len(observations)` with `1 <= locked_facts <= 24`. Typed absences count.
- Any other `page` in a v2 record is `malformed_native_section`. This validator checks shape only; R-A7 replays the interpretation.

### R-A6 — manifest v2
- `validate_private_manifest` becomes a dispatch on `schema`: v1 goes to `validate_v1_manifest` (today's validator, unchanged), `MANIFEST_SCHEMA_V2` goes to `validate_v2_manifest`, a non-mapping keeps the v1 message, and anything else raises `unsupported_schema` with the message "unsupported private manifest schema".
- A **v2 manifest** has exactly the eight v1 keys plus `native`, `native_source_cutoff` and `previous_manifest`. The eight shared fields keep their v1 rules and messages; `published_at` stays the context `knowledge_cutoff`. `generation_id` comes from the same `_generation_id`, so it covers the native section and the predecessor (plan: "Generation hashing includes native catalogs and prior-manifest binding").
- `native_source_cutoff` is a canonical clock (R-A7). Plan: "The v2 native-source cutoff is separately represented".
- `previous_manifest` is `None` or exactly the five pointer fields `generation_id`, `manifest_key`, `manifest_sha256`, `manifest_bytes`, `published_at`, valid under `validate_private_pointer({"schema": POINTER_SCHEMA, **previous_manifest})`. This round only checks its shape.
- `native` has exactly `workspaces`, `documents`, `source_bodies`, `selections`, `economic_slots`:
  - `workspaces`: workspace generation id (`\A[a-f0-9]{24}\Z`) → native receipt.
  - `documents`: sha256 of the document's canonical JSON bytes → native receipt; the receipt's `sha256` equals the key (`digest_mismatch`).
  - `source_bodies`: sha256 of the text bytes → exactly `{"text": native receipt, "received": {"sha256", "length", "declared_encoding"}}`. The text receipt's `sha256` equals the key (`digest_mismatch`). `received` must be `{"sha256": <the key>, "length": <the text receipt's bytes>, "declared_encoding": "utf-8"}`; a well-shaped `received` with other values is `mismatched_source`.
  - `selections`: record slug → exactly `company_id`, `event_id`, `profile_version` (three `str`), `fiscal_scope` (a list of four ISO dates), `chain`, `selection`, `interpretation_id` (`\Aecon_[a-f0-9]{64}\Z`).
    - `chain` is a list of 1 to 4 entries, oldest first, each exactly `{"workspace": <generation id>, "document": <document key>}`. An empty chain is `malformed_native_section`; more than 4 is `over_limit`.
    - `selection` is exactly `{"facts", "currentness"}`, the value passed to Task 3's build. `facts` is `None` or a list of 1 to 24 handles, each exactly three `str` fields (25 or more is `over_limit`). `currentness` is `None` or exactly `{"state": str, "source_clock": canonical clock or None}`.
  - `economic_slots`: `company_id` → exactly `{"slug", "event_id"}`. A slot names the issuer's current record.
- Catalog keys and chain ids that do not match their pattern are `unsafe_path`. They are checked before any path or object key is built from them.
- An object key that appears in more than one of the five catalogs (records, context, workspaces, documents, source bodies) is `wrong_role`. This is the plan's "duplicate key with different bound".

### R-A7 — one closure validator
`validate_native_closure(manifest, objects, *, slugs=None, interpretations=True)`. `objects` maps object key → `bytes`. It is the only place that holds the rules below. `prepare_private_publication` calls it now; Round B's publish and readers will call the same function.

**Scope.** `slugs=None` is the full scope: every record, context and native object the manifest names must be in `objects`, and `objects` holds nothing else. `slugs=(…)` checks only those records and their chains; a named slug that is not in `records` is `missing_artifact`. `interpretations=False` skips stage 4.

**Return.** A dict: slug → `{"record": dict, "selection": dict | None, "interpretation": dict | None, "chain": [{"workspace": dict, "document": dict, "text": str}, …]}` for every slug in scope. A slug with no selection has `None`, `None` and `[]`. The interpretation is returned in `TOP_LEVEL_KEYS` order.

**Canonical clock.** `type(value) is str`, the pattern `\A[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z` (write `[0-9]`, never `\d`), and `datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")` succeeds. Clocks are then compared as strings. An ISO date is the same idea with `%Y-%m-%d`. A clock that fails this is `malformed_native_section`.

**Order.** The first failing check in the order below decides the reason. Tests use one fault at a time.

**Stage 0 — manifest shape.** `validate_private_manifest(manifest)` (R-A6, which also applies R-A4 to every native receipt).

**Stage 1 — objects.** For each object in scope: absent is `missing_artifact`; longer than its role maximum is `over_limit`; a length other than the receipt's `bytes` is `size_mismatch`; another sha256 is `digest_mismatch`. In the full scope, an object the manifest does not name is `unexpected_artifact`, and so is a workspace, document or source body that no chain names.

**Stage 2 — chains.** First every `economic_slots` key and every selection's `company_id` must be admitted by `pg_profile.pg_private_registry().get(...)` (`cross_issuer`). Then, for each selection and each chain entry `i` (1-based), in this order:
1. The entry's workspace and document must be in their catalogs (`missing_artifact`).
2. Workspace W: canonical JSON and `event_workspace.validate_event_workspace(W)` (`malformed_native_section`). The id recomputed with `preview_generation_identity`, W's own `generation_id` and the catalog key must all be equal (`digest_mismatch`).
3. Document D: canonical JSON; `schema` and `authority` equal the `documents` constants; the native round trip shown under MEASURED INTERFACES returns D; then `rights_profile == pg_profile.PG_PRIVATE_RIGHTS_PROFILE`, `rights_state == "internal_only"` and `holds_bytes is False` (all `malformed_native_section`).
4. `D["revision"] == i` (`broken_chain`).
5. Supersession. Entry 1: `supersedes_document_id` must be `None`; if it names its own or a later entry's `document_id` the reason is `predecessor_cycle`, otherwise `broken_chain`. Entry `i > 1`, tested in this order: it names its own `document_id` → `predecessor_cycle`; it names entry `i-1`'s → fine; it names a later entry's → `predecessor_cycle`; anything else → `broken_chain`.
6. The body named by `D["content_sha256"]` must be in `source_bodies` (`missing_artifact`). Source binding (`mismatched_source`): the body decodes as strict UTF-8; `D["content_bytes"] == len(body)`; W has exactly one `issuer_release` row, and its `source_sha256` equals the body's sha256 (recompute it from the stored bytes), its `document_id == D["document_id"]` and its `filing_key == D["filing_key"]`; `D["event_id"] == W["event_id"] == selection["event_id"]`; `D["available_at"] == W["lifecycle"]["source_available_at"]`.
7. Issuer: `W["issuer"]["company_id"] == selection["company_id"]` (`cross_issuer`).
8. Clocks: W's `lifecycle.source_available_at`, `lifecycle.observed_at` and `generated_at`, and D's `available_at` and `fetched_at`, are canonical clocks (`malformed_native_section`). `source_available_at <= observed_at`, and all five `<= native_source_cutoff` (`future_source_clock`). The selection's `currentness.source_clock`, when not `None`, is `<= native_source_cutoff` (`future_source_clock`).
9. `source_available_at` never decreases along the chain (`broken_chain`).

One workspace, document or text may be named by more than one chain entry. Never key a chain position on an id.

**Stage 3 — pairing** (`malformed_native_section`). A v1 record has no selection. A v2 record with an interpretation object has a selection, and a selection's record has an interpretation object. A v2 record with the unavailable result has no selection. Every selection key is a slug in `records`. No two selections share `(company_id, event_id)`. Every slot names a selection with the same `company_id` and `event_id`. A selection without a slot is allowed. Empty `selections` and `economic_slots` are allowed. A v2 manifest may hold v1 and v2 records together.

**Stage 4 — interpretation** (per selection; `stored` is the record's interpretation object, `newest` the last chain entry):
1. `selection["profile_version"] == pg_profile.PG_PROFILE_VERSION`, else `interpretation_unsupported`.
2. `stored["interpretation_id"] == selection["interpretation_id"]` and `stored["event_id"] == selection["event_id"]` (`interpretation_mismatch`); `stored["issuer"]["company_id"] == selection["company_id"]` (`cross_issuer`).
3. `ordered = {key: stored[key] for key in economic_interpretation.TOP_LEVEL_KEYS}`; `texts = {newest document_id: newest text}`; `scope = tuple(selection["fiscal_scope"])`. Call `economic_interpretation.validate_economic_interpretation(ordered, workspaces=newest workspace, source_texts=texts, fiscal_scope=scope)`. Catch `UnsupportedInterpretationVersion` first → `interpretation_unsupported`. Any other error → `interpretation_mismatch`.
4. Rebuild with `build_economic_interpretation(newest workspace, source_texts=texts, fiscal_scope=scope, selection=selection["selection"], semantic_revision=economic_interpretation.SEMANTIC_REVISION, code_revision=economic_interpretation.CODE_REVISION)` and require `canonical_json_bytes(rebuilt) == canonical_json_bytes(stored)` (`interpretation_mismatch`).

### R-A8 — the exception boundary
- `_json_object` stays unchanged. Native roles load through one helper that checks the role maximum first (`over_limit`), then calls `_json_object` and turns its errors, and `RecursionError`, into `malformed_native_section`.
- Every call into a native class or validator, the registry, the rights gate or a Task 3 function sits behind one seam: `except Exception as exc:  # noqa: BLE001 - normalize contract boundary`, re-raised as the ruled reason `from exc`. No Task 1–3 exception type leaves the owner.
- A `KeyError`, `TypeError` or `ValueError` from reading a field of a native object in stages 2 to 4 is `malformed_native_section`. An `EarningsPrivateClosureError` always passes through unchanged.
- Type tests on untrusted v2 values use `type(x) is T`, never `isinstance` and never membership of an unchecked value in a set. The v1 code keeps its own tests unchanged.

### R-A9 — the v2 stage and `prepare_private_publication`
- `<stage>/native` selects the path. A symlink named `native` is `unsafe_path` (test `is_symlink()` first: `is_dir()` follows links). A real directory selects v2. Anything else is the v1 path, which must stay byte-identical; a v1 stage that holds a v2 record is `malformed_native_section`.
- A v2 stage still needs `records/` and `context/`, read exactly as today. It adds:
  - `native/latest.json`: canonical JSON, at most `MAX_NATIVE_STAGE_MANIFEST_BYTES`, exactly `schema` (`NATIVE_STAGE_SCHEMA`, else `unsupported_schema`), `native_source_cutoff`, `previous_manifest`, `selections`, `economic_slots` (the shapes of R-A6) and `received` (text sha256 → `{"sha256", "length", "declared_encoding"}`);
  - `native/workspaces/<generation id>.json`, `native/documents/<sha256 of the file>.json`, `native/source_bodies/<sha256 of the file>.txt`.
- The preparer reads only the files the chains name: ids are pattern-checked first, each document gives its `content_sha256`, and that names the body. It computes every receipt from the bytes it read and uses the file names as catalog keys, so a wrongly named file surfaces in the closure as `digest_mismatch`. A text that two entries name is stored once. Every body read needs its `received` entry (`malformed_native_section`), and a `received` entry for a body no chain names is `unexpected_artifact`.
- v2 stage-file faults: a symlink or a path escape is `unsafe_path`; a missing file is `missing_artifact`; a file over its role maximum is `over_limit`; an empty file or one that changed during the read is `malformed_native_section`. Any file or directory under `native/` that the chains do not name is `unexpected_artifact`. Unexpected files outside `native/` keep the v1 message. `_stage_file`'s v1 messages must not change.
- The preparer then builds the v2 manifest and calls `validate_native_closure(manifest, payloads)` in the full scope. Put no semantic rule in the preparer itself. The returned `PreparedPrivatePublication` carries the native artifacts, with their roles and media types, and their payloads.
- The preparer never reads the wall clock. `native_source_cutoff` and `previous_manifest` come from the stage.

### R-A10 — the rights seam (declared and tested now, called in Round B)
```python
def assert_native_rights() -> None:
    family = pg_profile.source_family_for_profile(pg_profile.RIGHTS_PROFILE)
    rights.assert_public_emission_allowed(family, path=NATIVE_RIGHTS_REGISTRY_PATH)
```
Both calls sit behind the R-A8 seam and any failure is `rights_refused`. It takes no parameter and is the only place in the owner that touches the rights module. `prepare_private_publication` does not call it. The production registry has no `sec_edgar` row yet (another program lands it), so never assert what the production registry says.

### R-A11 — the publish guard
`publish_private_publication` refuses a preparation whose manifest schema is not the v1 id, right after its two type checks and before any store call: `EarningsPrivatePublicationError("v2 private publication is not enabled")`. Round B replaces this guard.

### R-A12 — `retire_slots`
`prepare_private_publication(stage_dir, *, retire_slots=())`. `PreparedPrivatePublication` gains `retired_slots: tuple[str, ...] = ()` as its last field. The value must be a tuple or list of `str`; it is stored sorted and unique; a wrong shape raises `EarningsPrivateClosureError("malformed_native_section")`. It is allowed on a v1 stage and is not written into the manifest. Round B gives it its meaning.

## FIXTURES (`tests/earnings_economic_private_fixtures.py`)
- Import `_staged_publication` and `CountingLocalStore` from `tests.test_earnings_private_store`, and Task 2's helpers from `tests.earnings_economic_fixtures`, read-only. `_staged_publication(dir)` returns `(public_dir, private_dir, slug)`; `private_dir` is a v1 stage with one AAPL wire record.
- Build the Task 2 results once per process as shown under MEASURED INTERFACES, cache them, and hand out deep copies. Use the fixed cutoff `"2026-07-31T00:00:00Z"`.
- Two layers. `economic_stage_parts(case)` returns plain in-memory parts: chains of `{workspace, document, text_bytes}`, the selection receipts, slots, `received`, cutoff, `previous_manifest` (`None`) and the v2 records. `write_economic_stage(stage_dir, parts)` computes every digest and file name from the parts and writes the native files and records as canonical JSON. `stage_economic_case(tmp_path, case)` creates `tmp_path / "economic"`, calls `_staged_publication` on it, writes the parts into its private stage and returns that stage. Round B relies on this name and on that sub-directory.
- Cases: `'valid'` (one P&G root dossier record beside the AAPL wire record), a corrected chain (v1, v2), an amended chain (v1, v3), a stage whose wire record is v2 with the unavailable result, a stage whose wire record is v2 with an interpretation, an explicit three-handle selection, and `currentness None`.
- Reseal helpers: one that recomputes a workspace's `generation_id` after an edit (`preview_generation_identity` ignores the stored id), and one that recomputes a manifest's `generation_id` with the module's `_generation_id`. A tamper test edits the parts or a prepared manifest, reseals everything downstream of its one fault, and asserts the reason.

## TESTS (`tests/test_earnings_economic_private_store.py`; every refusal asserts `exc.reason`)
File-system faults go through `prepare_private_publication`. Object and manifest faults go through `validate_native_closure` on a prepared generation's manifest and a copy of its payloads. Plan 4.1: "Test v1-only, v1/v2 mixed records, standalone native economic record, absent native source, wrong role/hash/size/issuer, malicious path, symlink, duplicate key with different bound, oversized source, future source clock, predecessor cycle and unsupported schema."
1. **v1 unchanged.** A v1 stage gives a v1 manifest with exactly the eight v1 keys, only `.json` keys, `retired_slots == ()`. A v1 stage holding a v2 record is refused.
2. **Accepted v2 cases.** Each fixture case prepares. For `'valid'`: the 11 manifest keys, catalog sizes 1/1/1, the slot, the text artifact's `.txt` key and media type, `locked_facts == 20`, and the closure's return shape. For the two-entry chains: catalog sizes (v1 and v3 share one text). Preparing the same stage twice gives identical manifest bytes.
3. **Objects:** absent body, workspace and document (`missing_artifact`); an extra object, an unnamed catalog entry, and an unnamed file or directory under `native/` (`unexpected_artifact`); same-length other bytes and a wrongly named stage file (`digest_mismatch`); a receipt `bytes` off by one (`size_mismatch`); a body of 8 MiB + 1 (`over_limit`).
4. **Roles and paths:** a source-body receipt whose key ends `.json`, and a document's receipt placed under `workspaces` (`wrong_role`); an object key containing `../`, a chain id containing `../`, a symlinked stage file and a symlinked `native` (`unsafe_path`).
5. **Limits:** a chain of 5 and a selection of 25 handles (`over_limit`); an empty chain (`malformed_native_section`).
6. **Chains:** a root that names entry 2 and an entry 2 that names itself (`predecessor_cycle`); an entry 2 that names an outside document, a reversed chain, and a source clock that steps back (`broken_chain`).
7. **Source binding (`mismatched_source`):** a changed body with its document resealed (the release row no longer matches); a non-UTF-8 body with document and workspace resealed; `received` with another sha256, another length, another encoding; a document whose `event_id` differs.
8. **Native objects (`malformed_native_section` unless noted):** `holds_bytes True`; the public rights profile; a month-13 `observed_at`; an offset-form clock; a workspace whose stored id was changed (`digest_mismatch`).
9. **Clocks (`future_source_clock`):** a cutoff earlier than `observed_at`; a `source_clock` later than the cutoff; `source_available_at` later than `observed_at`.
10. **Issuer (`cross_issuer`):** a selection and slot naming an unadmitted company; and, with `pg_profile.pg_private_registry` patched to a double that admits a second company id, that company named over P&G's chain.
11. **Interpretation:** a changed stored number, stored `selection.currentness`, stored `selection.currentness_observed_at`, the receipt's `currentness.state`, the receipt's `fiscal_scope`, and another `interpretation_id` (`interpretation_mismatch`); a changed `build.code_revision`, another `profile_version`, and another interpretation `schema` (`interpretation_unsupported`). With `interpretations=False` the changed number passes and the chain is still returned.
12. **Pairing and records (`malformed_native_section`):** a dossier with `public_facts != 0`, with a wrong `locked_facts`, with non-empty html, with the unavailable result; an unknown unavailable reason; an extra record key; an unknown `page`; an interpretation without a selection and a selection without one; two selections for one event; a slot naming another event. 25 observations is `over_limit`.
13. **Schemas (`unsupported_schema`):** record (message exactly `unsupported private record schema`), manifest, native stage manifest.
14. **Scope:** a scoped closure for the dossier slug passes with only its own objects and fails `missing_artifact` without one of them or for an unknown slug.
15. **Rights seam:** permitted with `derived_display_ok` and with `direct_display_ok`; `rights_refused` for an absent family, for `internal_only`, for `unresolved`, for a malformed registry and for a missing file. Patch `NATIVE_RIGHTS_REGISTRY_PATH` to a **distinct** registry file per case (the loader caches per path). The registry format is `families:\n  sec_edgar:\n    rights_class: derived_display_ok\n    auth_class: keyless_public\n`.
16. **Guard and retirement:** publishing a v2 preparation raises the R-A11 message and the store recorded no write; `retire_slots` shape, order and default.
17. **Surface:** the 17 reasons; every `EarningsPrivateClosureError` is an `EarningsPrivatePublicationError`; no refusal message contains a digest or an object key.

## MUTANTS (each: edit, run, quote the failing test NAME, `git checkout -- <file>`, prove `git diff --quiet`)
(a1) skip the release-row digest check; (a2) trust the workspace's stored `generation_id`; (a3) accept a root that names a predecessor; (a4) keep Task 3's validator but skip the rebuild comparison; (a5) send an unknown record schema to the v1 validator; (a6) ignore unnamed files under `native/`; (a7) drop `source_available_at <= observed_at`; (a8) make `assert_native_rights` swallow the refusal.

## WORK ORDER (short steps; commit and push after each)
1. R-A1 to R-A4: header, constants, the error class, the role table. First write the surface tests and quote them failing (RED).
2. R-A5 records and the fixture module's parts layer.
3. The stage writer, R-A6, R-A9 and R-A7 stages 0 to 3.
4. R-A7 stage 4 and R-A8.
5. R-A10, R-A11, R-A12.
6. Mutants, the runs below, the merge check.

## RUNS (quote each rc line under EVIDENCE)
- A clean venv **outside the repository tree**, on CPython 3.12 like CI (3.12.13): `uv venv --python 3.12 <dir>` (uv is `/opt/homebrew/bin/uv`; a 3.12 is already installed), then `uv pip install --python <dir>/bin/python pytest pyyaml requests jinja2` and nothing else. Quote `<dir>/bin/python --version`. If no 3.12 can be had, use `python3 -m venv` and say so under GAPS. Run each pytest command with `<dir>/bin/python -m pytest …` under `bash -c 'ulimit -s hard; …'`.
- `python -m pytest tests/test_earnings_economic_private_store.py -q -p no:cacheprovider` (GREEN).
- `python -m pytest tests/test_earnings_private_store.py -q -p no:cacheprovider` → `18 passed`, with the file unedited.
- `python -m pytest tests/test_earnings_economic_interpretation.py tests/test_pg_economic_source_selection.py -q -p no:cacheprovider` still passes.
- `python -m pyflakes` on the three owned files is clean (pyflakes goes in a second venv, made the same way).
- `sed -n '33p' engine/earnings_narrative/private_publication.py`.
- `python scripts/check_contract_delta.py --base origin/main`: quote its summary. A delta that comes only from the missing CI wiring goes under GAPS.
- `git diff --name-only origin/main...HEAD` lists only the three owned files.

## COMMON RULING (binding)
- **Short steps, pushed as they land.** After each step: `git add <named paths>`, commit with a message that names only that step's hunks, then push. Push an unfinished step as `wip(...)` rather than holding it. A long single exec degenerates and commits nothing.
- **Real probes.** A test must be able to fail against a plausible wrong implementation. Never restate the code in a test.
- **One rule, one place.** If a rule seems to need a special case, report it under GAPS instead.
- **The PR.** Open it yourself, once, after the final push: `gh pr create --draft --base main --head claude/cdv1-t4-private-publication-v2 --title 'feat(earnings): bind economic evidence into existing private generations (CDV-1 Task 4)' --body-file <file>`. First run `gh pr list --head claude/cdv1-t4-private-publication-v2 --state open`; if a PR is already open, do not open another. The body states the head sha, the files changed, the test commands with their summary lines, and that hosted CI is expected red in the CI-manifest checks and the deploy restart guard until round B. It never claims a check is green.

Before the final push: `git fetch origin main`. If `origin/main` moved, `git merge --no-ff origin/main` (never rebase). On a conflict keep both sides and never discard main's side. A conflict outside OWNED FILES means STOP with STATUS BLOCKED naming it. After any merge, re-run the RUNS and re-check line 33.

## GAPS RULE
If an R-A item contradicts the plan text quoted here, Task 1–3's measured behavior, or another R-A item, or cannot be met, implement everything else and report that item under GAPS with its reason. The seat rules on it. Never silently drop or reinterpret an item.

## NOT DONE UNLESS
- Every RUNS line is quoted with its rc, and the new suite and the legacy suite pass in the clean venv.
- The 17 test groups exist, and each refusal test asserts a reason.
- The eight mutants each fail a named test and are restored.
- Line 33 is unchanged and lines 13–33 match R-A1 exactly.
- `git grep -n "isinstance" -- engine/earnings_narrative/private_publication.py` shows no new line that tests an untrusted v2 value (RESULT lists the new lines, if any).
- Every commit carries the trailer and is pushed, with no force and no amend.

## RETURN (final message, exactly these sections)
- **STATUS:** COMPLETE | PARTIAL | BLOCKED.
- **RESULT:** head sha; files; each R-A item with its line refs; the public names you added.
- **EVIDENCE:** the C0 outputs; quoted rc lines for RED, GREEN, the legacy suite, the Task 2 and Task 3 suites, each mutant with its failing test name, pyflakes and the line-33 check.
- **GAPS.**
- **DEVIATIONS:** each with its R-A id, or "none".

Then EXACTLY ONE final stdout sentinel line `<LABEL>: <STATUS> <sha>`.
