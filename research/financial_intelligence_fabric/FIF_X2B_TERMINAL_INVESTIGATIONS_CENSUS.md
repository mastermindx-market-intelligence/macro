# FIF X2-b step 1 — Terminal manifest v2 contract census

- Lane: `fif-x2b-census-20261013` (contained READ-ONLY census; no git tree written)
- Date: 2026-10-13
- Census target commit: **c799ba7e64e2d0861228c9977cc12ed4a5d91982** (Terminal mirror `~/lanes/repos/mastermind-terminal`, partial clone; every git command prefixed `GIT_NO_LAZY_FETCH=1`; reads only via `git show`/`git grep`/`ls-tree` at the explicit commit — no ref was trusted)
- Macro consumer side: `templates/fif_saved_briefcase.js` at local detached tree `df7085bb351e4c6e49415191fb873259769c1780`
- Mirror freshness (recorded as given, not re-checked): "Mirror freshness is already established by ORCH-A: c799ba7e is the ubuntu2 mirror's origin/master; GitHub's terminal head was abea23b1 at census time with NO change under the investigations contract/route/migration paths."
- Cite convention: every cite below is `path:line@c799ba7e`; within one bullet, a bare `:N` continues the file just cited. Python = `api/investigation_contracts.py`, TS = `terminal/lib/investigationContracts.ts`, SQL = `supabase/migrations/0028_investigations.sql`.
- Offline gaps: none — no `BLOB ABSENT OFFLINE` occurred; every listed source read in full at the commit.

There are THREE validators in the shipped write path, and they are progressively stricter:
1. **Python** `validate_investigation_manifest` (api/investigation_contracts.py:84) — paired pure contract, v1+v2, admission is a caller parameter (default empty = admits nothing).
2. **TypeScript** `validateInvestigationManifest` (terminal/lib/investigationContracts.ts:274) — same grammar; the shipped service calls it with the hard-coded production admission `INVESTIGATION_ADMISSION` (terminal/lib/investigations.ts:7-13).
3. **PostgreSQL** `valid_investigation_manifest_v2` (SQL:88-155) — re-validates inside `apply_investigation_revision_v2` with the G1-only restrictions hard-coded (v2 only, no thesis refs, owner/kind and owner/object_type pairs hard-coded).

A macro→Terminal round trip must pass 2 then 3 (the Python side is the paired oracle macro cites, not the shipped gate).

---

## Q1 — Manifest v2 top level: fields, types, required/optional, defaults, enforcing validator

### Python (`validate_investigation_manifest`, api/investigation_contracts.py:84)
Enforced by `obj(raw, "$", …)` at api/investigation_contracts.py:89:

| field | type | required | notes |
|---|---|---|---|
| `schema` | string | yes | exact `investigation_manifest.v1` or `investigation_manifest.v2` (`choice` :90; invalid → `unsupported_value` at `$.schema` via :55-56) |
| `intent` | object | yes | shape at :146 |
| `layout_refs` | list | yes | ≤4 (:159) |
| `thesis_refs` | list | yes | ≤16 (:160); must be EMPTY for persisted v2 commands (not a Python rule — TS/SQL below) |
| `evidence_refs` | list | yes | ≤128 (:161); v2 total layout+thesis+evidence ≤128 (:162) |
| `continuation` | object | yes | may be `{}` (:163) |
| `review_baseline_ref` | object | optional | checked by the evidence checker with `baseline=True` (:166-167, :118) |

Pre-checks before shape: `data_only` bounds — ≤4096 nodes, depth ≤24, total string length ≤131072 UTF-16 units (:59-68). Serialized UTF-8 ≤131072 bytes (v2) / 65536 (v1) (:168-169). **No defaults exist anywhere**: nothing is injected, defaulted, or normalized ("never normalize text", :85). Returns `{ok, value}` with a detached deep copy (:170) or the FIRST error only (`require` raises on first failure, :27-29, :171-172).

### TypeScript (`Validator.manifest`, terminal/lib/investigationContracts.ts:244-270)
Same six required keys + one optional, enforced by `object()` at terminal/lib/investigationContracts.ts:245 (types InvestigationManifest :47-61). Schema check: `v2 = manifest.schema === INVESTIGATION_MANIFEST_SCHEMA_V2` (:247); `if (!v2 && schema !== "investigation_manifest.v1") add("$.schema","unsupported_schema")` (:249) — constants :10/:12. v2 question/continuation limit 4000 vs 2000 (:248); v2-only total refs ≤128 (:250-252); byte cap 131072 vs 65536 chosen by raw `.schema` (:279-281) and checked BEFORE shape validation (:278-283). `dataOnly` structural guards: ≤4096 nodes, depth ≤24, ≤131072 accumulated string units, plain prototypes only, no sparse arrays/symbols/getters/toJSON (:89-132, MAX_NODES :15). Errors ACCUMULATE up to 32 (MAX_ERRORS :14, add :85-87); `ok: false` if any (:285); success returns a detached `JSON.parse` copy (:286); hostile objects fail closed to `non_json_value` (:287-290).

### SQL (`valid_investigation_manifest_v2`, SQL:88-155)
`investigation_keys_v2(m, [schema,intent,layout_refs,thesis_refs,evidence_refs,continuation], [review_baseline_ref])` (SQL:92; key function :74-78 — required keys present, values not JSON `null`, NO key outside required∪optional). Schema must be exactly `investigation_manifest.v2` (SQL:93) — **v1 is not accepted by the persistence layer**. Rendered-size bound `octet_length(investigation_json_v2(m)) ≤ 131072` (SQL:93, serializer :79-87). Returns a single boolean; any failure → `invalid_payload` from the RPC (SQL:177).

### Where the sides disagree (same verdicts, different mechanics)
- **Error code for a bad schema string**: Python `unsupported_value` (api/investigation_contracts.py:90 via :55-56) vs TS `unsupported_schema` (terminal/lib/investigationContracts.ts:249, pinned by test terminal/lib/__tests__/investigationContracts.test.ts:83); SQL: just `false`.
- **Error cardinality**: Python returns the first error only (:27-29); TS accumulates ≤32 (terminal/lib/investigationContracts.ts:14, :85-87).
- **Unknown-key error path**: Python reports the PARENT path (`$` for top level — `obj` :32-34 passes the container path); TS reports the child path `$.<key>` (:139).
- **Size-check order**: TS checks serialized bytes before shape (:278-283); Python after shape (:168-169). Same caps.
- **Calendar date**: Python uses `date.fromisoformat` (:155-158); TS hand-rolls leap-year tables (:173-181); SQL uses a `::date` cast + `to_char` round-trip (:100-101). Same outcomes (frozen corpus pins this: 47 vectors, terminal/lib/__tests__/investigationManifestParity.test.ts:5-16, fixture terminal/lib/__tests__/fixtures/investigation_manifest_vectors.json).
- **v1**: accepted by Python and TS validators, refused by the route/DB (terminal/lib/investigations.ts:52 requires v2; SQL:93).

---

## Q2 — Unknown/extra key policy (decides whether A survives a Terminal round trip)

**Every level on every side REJECTS unknown keys (`unknown_field`); nothing is dropped, nothing kept verbatim.** Macro's top-level carrier `fif_saved_research` makes Terminal refuse the whole manifest.

Deciding code:
- Python `obj()` — `require(set(value) <= set(required) | set(optional), path, "unknown_field")` (api/investigation_contracts.py:32-36), applied at top level via :89. A `fif_saved_research` key → `{"path": "$", "code": "unknown_field"}` (first-error form).
- TS `object()` — `for (const key of Object.keys(result)) if (!allowed.has(key)) this.add(`${path}.${key}`, "unknown_field")` (terminal/lib/investigationContracts.ts:139), applied at top level via :245. → `{"path": "$.fif_saved_research", "code": "unknown_field"}`.
- SQL — `investigation_keys_v2` fails any key outside required∪optional (SQL:76-77), applied at SQL:92 (top), :94 (intent), :108 (subjects[i]), :140 (evidence_refs[i]/review_baseline_ref), :123 (layout_refs[i]) → RPC returns `invalid_payload` (SQL:177).

Per container (required | optional key sets):
- top level: 6 required + `review_baseline_ref` — Python :89; TS :245; SQL :92
- `intent`: `title|question|subjects` + `horizon|research_as_of` — Python :146; TS :253; SQL :94
- `subjects[i]`: `kind|owner|object_id` + `version_ref` — Python :95; TS :196; SQL :108
- `evidence_refs[i]`: `owner|object_type|object_id|mode` + `version_ref|fingerprint|selection` — Python :119; TS :222; SQL :140
- `layout_refs[i]`: exactly `layout_id|layout_revision_id|digest|role` (no optional) — Python :104; TS :208; SQL :123
- `thesis_refs[i]`: exactly `thesis_id|version_id|role` — Python :112; TS :215; SQL :123
- `continuation`: no required + `next_question|next_observation` — Python :163; TS :263; SQL :97
- `selection`: exactly `field` — Python :133; TS :238; SQL :146

Behaviorally pinned by tests: unknown top-level keys rejected (`investigationContracts.test.ts:79-81`), forged evidence keys rejected (:99-102), thesis `statement` rejected (:144), continuation `last_reviewed_at` rejected (:162-163), layout `name` rejected (:118-121), intent `owner_principal`/`rights` rejected (:242-245), fixture vector "unknown body" (one of the 47, fixture file).

---

## Q3 — subjects[]

- **kind**: closed set of 12 — `security, issuer, industry, subtheme, theme, regime, economy, event, portfolio, option_underlying, option_contract, policy_question` (Python KINDS :19; TS SUBJECT_KINDS :16-19). `"issuer"` IS a member. SQL does not check the set directly; it enumerates the two admitted pairs (SQL:110).
- **owner**: syntax `NAMESPACE` = `^[a-z][a-z0-9_.-]{0,63}$` (Python :17 enforced :96; TS :75 enforced :198). `"fif"` is syntactically valid. **But the owner set is closed by ADMISSION**: a subject is accepted only if `admission.subjects` contains `{owner, kinds}` matching (Python :100; TS :201-204, admission type :62-66). Production admission admits exactly:
  - `terminal.analysis_symbol` + kind `security`
  - `data_os.security_master` + kinds `security|issuer`
  (terminal/lib/investigations.ts:7-13; SQL hard-codes the same two pairs, SQL:110; test admission uses fixture owners only, investigationContracts.test.ts:5-8.) Default admission is empty → "admits no external references by default" (test :94-98; Python default `{}` :86). **"fif" is NOT admitted on any shipped surface.**
- **object_id**: string, non-blank after trim, 1..256 Unicode scalars, single-line (no tab/LF/CR), no C0 controls/NUL/DEL, no unpaired surrogates (Python text() :39-48 called :97 single=True; TS :143-157 called :199; SQL investigation_text_v2 :67-73 called :109). No charset/pattern beyond that.
- optional `version_ref`: same text rules, ≤256 (Python :98-99; TS :200; SQL :111).
- **max items**: 16 (Python :149; TS :256; SQL :106).
- **uniqueness**: exact tuple `(owner, kind, object_id, version_ref)` — duplicate → `duplicate_reference` (Python :101, :140-144; TS :205, :182-194; SQL :112-113). `null` vs absent version_ref both land in the identity tuple.
- Unknown key → reject (Q2 cites).

---

## Q4 — evidence_refs[]

- **owner / object_type**: both must match `NAMESPACE` `^[a-z][a-z0-9_.-]{0,63}$` (Python :120-121; TS :224; SQL checks no pattern but hard-codes exact values, SQL:141). `"fif"` and `"occurrence"` are each syntactically valid namespace strings.
- **Admission (the real gate)**: accepted only if `admission.evidence` contains `{owner, object_types}` matching (Python :123; TS :226-228). Production admits exactly ONE pair: `earnings.workspace_generation` + `event_workspace` (terminal/lib/investigations.ts:12; SQL:141 `r->>'owner'<>'earnings.workspace_generation' or r->>'object_type'<>'event_workspace'` → false). **"fif" as evidence owner: NOT admitted. "occurrence" as object_type: NOT admitted.** (`admits_owner_fif=false`, `admits_object_type_occurrence=false`.)
- **object_id**: same rules as subjects' object_id, ≤256, single-line, non-blank (Python :122; TS :225; SQL :142).
- **mode**: `pinned | follow_head` (Python :124; TS :229; SQL :142). In `review_baseline_ref` position the checker is called with `baseline=True` → `pinned` only (Python :118/:124; TS :221/:229; SQL :134).
- **pinned requires**: `version_ref` present (Python :125 `pinned_version_required`; TS :230; SQL :143) and it must be valid text ≤256 single-line (Python :126-127; TS :231; SQL :143). No format/pattern beyond the text rules; no fingerprint requirement (fingerprint is optional everywhere).
- **follow_head forbids**: BOTH `version_ref` and `fingerprint` — Python :130 `incompatible_reference_mode`; TS :233-235; SQL :144.
- **fingerprint** (optional): exactly 64 lowercase hex — `^[0-9a-f]{64}$` (Python :16 enforced :128-129; TS :74 enforced :232; SQL :145).
- **selection** (optional): object with exactly `field`, `FIELD` pattern `^[A-Za-z0-9_][A-Za-z0-9_.:-]{0,127}$`, never executable text (Python :131-134; TS :236-241; SQL :146; tests investigationContracts.test.ts:230-237).
- **max items**: 128 individually (Python :161; TS :262) — and in v2 the layout+thesis+evidence TOTAL is ≤128 (Python :162; TS :250-252; SQL:118-120 total + layout ≤4 + thesis ≤16).
- **ordering/uniqueness**: order is preserved and is mutation identity (docs/INVESTIGATION_V2_CONTRACT.md:20 "JSON object order is not mutation identity. Arrays and exact string values are"). Duplicate identity tuple `(owner, object_type, object_id, mode, version_ref, selection.field)` → `duplicate_reference` (Python :135, :140-144; TS :242, :182-194; SQL :148-150 — SQL also folds `review_baseline_ref` into the same dedupe pass, SQL :133-135, :149-151).

---

## Q5 — intent

- `title`: REQUIRED, string, 1..160 Unicode scalars, non-blank, single-line (no tab/LF/CR), no other controls (Python :147 `text(...,160,True)`; TS :255 `text(...,160,true)`; SQL :95 `investigation_text_v2(...,160,true)`). Trimming: never performed by Terminal (text is preserved exactly; blankness tested with the TRIM set Python :14 / ECMAScript trim TS :145 — P1 doc :43-44); an all-whitespace title is rejected `empty_text`.
- `question`: REQUIRED, string, 1..2000 (v1) / 1..4000 (v2) scalars, non-blank, multi-line allowed (CRLF/whitespace preserved) (Python :148 with limit :92; TS :255 with :248; SQL :96).
- `subjects`: REQUIRED array ≤16 (Q3).
- `horizon`: OPTIONAL, ≤64 scalars, single-line, non-blank if present (Python :150-151; TS :257; SQL :98).
- `research_as_of`: OPTIONAL, EXACT format `YYYY-MM-DD` — regex `[0-9]{4}-[0-9]{2}-[0-9]{2}` AND a real calendar date: Python `date.fromisoformat` (:152-158), TS manual leap-year validation (:173-181 enforced :258), SQL `::date` cast with `to_char` round-trip (:99-102). Not a timestamp; no time zone; invalid calendar dates (2026-02-30, 2025-02-29, 2026-13-01, 0000-01-01, 2026-1-1, 2026-01-01T00:00:00Z) all reject `invalid_date` (test :155-157; valid leap 2024-02-29 accepted :158-161).
- No other intent field exists; unknown → reject (Python :146; TS :253; SQL :94).

---

## Q6 — layout_refs, thesis_refs, continuation

- **layout_refs** items: exactly `{layout_id, layout_revision_id, digest, role}`; layout_id and layout_revision_id lowercase UUID `^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`; digest 64 lowercase hex; role `primary|supporting` (Python :103-109; TS :207-213; SQL :122-126). ≤4 items (Python :159; TS :260; SQL :120). Dedupe on `(layout_id, layout_revision_id)` even when roles differ (Python :109/:143; TS :212/:190; SQL :127-128; test :122-124). **Empty `[]` is lawful** (no minimum). Persisted refs must ALSO resolve to the user's retained `chart_layout_revisions` rows or the RPC returns `reference_unavailable` (SQL :204-206) — shape acceptance never proves referent existence (TS header :2-4).
- **thesis_refs** items: exactly `{thesis_id, version_id, role}`; both UUIDs; role `primary|alternative|context` (Python :111-116; TS :214-220; SQL :122-126). ≤16 (Python :160; TS :261; SQL :120). Dedupe on `(thesis_id, version_id)` (distinguishes distinct versions of one thesis; test :225-229). **Empty `[]` is lawful and, for persisted v2 commands, MANDATORY**: TS command gate `!checked.value.thesis_refs.length` (terminal/lib/investigations.ts:52) and SQL `if jsonb_array_length(m->'thesis_refs')>0 then return false` (SQL:131, comment :130 "G1 admits no unverified Thesis rows").
- **continuation**: object whose ONLY legal keys are OPTIONAL `next_question` and `next_observation`, each a non-blank string ≤2000 (v1) / 4000 (v2), multi-line allowed (Python :163-165; TS :263-268; SQL :97, :103-105). **`{}` is lawful** (required-present but empty; test "keeps no baseline absent…" neighborhood, investigationContracts.test.ts:14 `continuation: {}` in every valid draft). Any other key (e.g. `last_reviewed_at`) → `unknown_field` (test :162-163).

---

## Q7 — Schema identifier

- Field name: **`schema`** (top-level required string).
- Values: `investigation_manifest.v1` (Python :90; TS :10) and `investigation_manifest.v2` (Python :90; TS :12; SQL :93).
- v1 vs v2 distinguished by exact string equality only (Python :91; TS :247). Version differences: question/continuation scalar limit 2000→4000 (Python :92; TS :248), byte cap 65536→131072 (Python :169; TS :279-281), total-refs-≤128 cap exists only in v2 (Python :162; TS :250-252; SQL:120).
- The shipped route/DB accept **v2 only**: `checked.value.schema !== INVESTIGATION_MANIFEST_SCHEMA_V2 → null` (terminal/lib/investigations.ts:52); SQL:93 `m->>'schema'<>'investigation_manifest.v2'` → invalid. A `v3` string is rejected `unsupported_schema` (TS :249; fixture vector; test :82-84).

---

## Q8 — Persistence and route

### Route `terminal/app/api/investigations/route.ts`
- **Methods**: `GET` (:16-40) and `POST` (:41-60); `runtime="nodejs"`, `dynamic="force-dynamic"` (:5-6); responses `private, no-store` + `Vary: Cookie` (:7).
- **Auth**: Supabase session cookie — `createClient()` from `@/lib/supabase/server` then `db.auth.getUser()`; no user → `401 unauthenticated` (:10-15 GET, :45-46 POST). The DB actor comes only from `auth.uid()` inside the RPC (SQL:162, :167) — never from request data. RLS owner-only SELECT policies on all four tables (SQL:51-64).
- **GET shapes**: no params → list (rpc `list_investigations_v2`, investigations.ts:33-40); `operation_id` alone → operation receipt (`read_investigation_operation_v2` :91-99); `id` + optional `revision` (1..2147483647) → `read_investigation_v2` (:101-115). Duplicate/unknown params → 400 (:26-27, :29, :34, :36). Readback re-validates the manifest with production admission before trusting it (investigations.ts:112).
- **POST**: in-memory per-IP fixed-window rate limit, name `investigations-save`, max 30 per 60 s window (route.ts:42; terminal/lib/rateLimit.ts:53, :85-120; real client IP from CDN headers :30-38). Body: stated `content-length` and re-encoded body both capped at 132×1024 bytes → else 413 (:48-52); `JSON.parse` → 400 on bad JSON (:54). Then `parseInvestigationCommand` (:55) and `applyInvestigationRevision` (:57).
- **Validators the route runs** (the chain): (1) `parseInvestigationCommand` — exact key set `{id, operation_id, expected_revision, action, manifest, layout_capture?}`, both UUIDs, expected_revision 0..2147483646, action ∈ create|revise|remove|restore (investigations.ts:46-50); (2) `validateInvestigationManifest(manifest, INVESTIGATION_ADMISSION)` + schema must be v2 + `thesis_refs` empty (+ `layout_refs` empty iff `layout_capture` present) (:51-59); (3) RPC `apply_investigation_revision_v2` → SQL `valid_investigation_manifest_v2` (SQL:177) with advisory-lock ordering: per-principal operation lock → exact-retry receipt replay → validity → capacity lock → global target lock → CAS on `expected_revision` (SQL:171-195); `remove`/`restore` must resend the CURRENT revision's manifest byte-identically (SQL:196-198).
- **Status map** (route.ts:9): found/committed 200, invalid_payload 400 (413 for oversize), unauthenticated 401, not_found 404, version_conflict/idempotency_conflict/layout_conflict 409, invalid_transition/reference_unavailable 422, limit_reached 429, unavailable 503.

### Storage `supabase/migrations/0028_investigations.sql` (applied 2026-10-04, SQL:2)
- `public.investigations` — head index: id, user_id, current_revision>0, lifecycle active|removed, created_at, updated_at (SQL:7-15). Manifest NOT stored here.
- `public.investigation_revisions` — immutable ledger: (investigation_id, user_id, revision>0) PK, action, lifecycle, **`manifest jsonb not null`** (SQL:22), committed_at (SQL:16-26). The manifest is stored as **jsonb**; no column-level size limit — the bound is the validator's 131072-byte envelope (SQL:93) plus the route's 132-KiB body cap.
- `public.investigation_mutation_receipts` — idempotency: (user_id, operation_id) PK, request jsonb, result jsonb (SQL:27-33); exact retry replays the stored result (SQL:172-176).
- `public.chart_layout_revisions` — belongs to the layout owner, not Investigation (SQL:34-46).
- **Plan/quota limits**: create refused at ≥500 lifetime investigation records; any mutation refused at ≥2000 lifetime revision rows → `limit_reached` (SQL:199-201; docs/INVESTIGATION_V2_CONTRACT.md:70-74 — counts include removed records; exact committed replay stays available). Rate limit above (30/min/IP) is transport-level only.
- Grants: tables SELECT-only to authenticated (SQL:63-64); RPC execute grants (SQL:241, :256, :268); `apply` is SECURITY DEFINER owned by postgres (SQL:160, :239-240).

### Baseline route `terminal/app/api/investigations/baseline/route.ts`
GET only, same Supabase cookie auth (:10-13); resolves a retained Earnings workspace from R2 by `symbol` or by `event_id+generation_id+company_id+fingerprint` (:18-33) and projects a **pinned evidence reference** `{owner:"earnings.workspace_generation", object_type:"event_workspace", object_id:event_id, mode:"pinned", version_ref:generation_id, fingerprint}` (:34-37) — the only evidence shape the G1 UI creates.

---

## Q9 — Owner registry / extension mechanism

**None exists.** There is no registry, enum of products, allow-list file, or plug-in point through which an external product becomes an admitted owner/object_type, and no extension/extras/payload field through which a manifest carries a product's own payload. What exists is only:
- a caller-supplied **admission parameter** on the two pure validators (Python `admission` arg :84-86; TS `InvestigationAdmission` type :62-66 with the comment "Supplied by existing admitted adapters. This module owns no adapter registry." :62; Python docstring "It owns no persistence, adapter registry…" :3-5) — a function argument, not a registry; and
- the **hard-coded production admission** `INVESTIGATION_ADMISSION` (terminal/lib/investigations.ts:7-13) duplicated as hard-coded equality in SQL (:110 subjects, :141 evidence).

Negative findings, exact commands (all run with `GIT_NO_LAZY_FETCH=1`, at commit c799ba7e64e2d0861228c9977cc12ed4a5d91982):
- `git -C ~/lanes/repos/mastermind-terminal grep -n -i 'fif' <commit> -- api terminal/lib terminal/app/api/investigations terminal/components supabase/migrations docs/INVESTIGATION_V2_CONTRACT.md docs/INVESTIGATION_P1_CONTRACT_CANDIDATE.md` → 10 hits, ALL unrelated English words ("fifteen", "fifth", "fifty") in finPages.ts, gexStrings.ts, four test files, feedFreshness.ts, watchlists.ts. **Zero occurrences of "fif" as an owner or identifier in the investigations surface.**
- `git -C ~/lanes/repos/mastermind-terminal grep -n 'occurrence' <commit> -- api terminal/lib terminal/app/api/investigations terminal/components supabase/migrations docs` → hits only in unrelated design/audit docs and unrelated tests. **Zero in the contract, admission, migration, or vectors.**
- `git -C ~/lanes/repos/mastermind-terminal grep -niE 'extension|extras|payload|plug-?in|registry' <commit> -- api/investigation_contracts.py terminal/lib/investigationContracts.ts terminal/lib/investigations.ts docs/INVESTIGATION_V2_CONTRACT.md docs/INVESTIGATION_P1_CONTRACT_CANDIDATE.md` → only NEGATIONS: "owns no … adapter registry" (Python :4, TS :62), "no adapter discovery, registry, identity mapping" (P1 doc :36), "identity registry" absent by design (P1 doc :12), "future P4/P5 payloads are rejected, not discarded" (TS :7), "Future relation/notes/scenario fields require an explicit contract extension; this G1 slice does not advertise them as implemented" (V2 doc :17-18), "not a license registry" (V2 doc :88).
- Fixture corpus corroborates: 47 vectors; every admission entry is the G1 pair set (`terminal.analysis_symbol`/security, `data_os.security_master`/security+issuer, `earnings.workspace_generation`/event_workspace ×46, one empty-admission vector); only object_type seen is `event_workspace` (568 refs); the only extra-top-level-key vector is the rejection case "unknown body" (terminal/lib/__tests__/fixtures/investigation_manifest_vectors.json).

---

## Q10 — Line-cite drift (macro briefcase comment block vs c799ba7e)

Macro side: `grep -n 'investigation_contracts' templates/fif_saved_briefcase.js` → exactly ONE hit, `588: // (api/investigation_contracts.py): subjects kind/owner/object_id :94-100`. The comment block is templates/fif_saved_briefcase.js:585-592; its colon-cites are exactly `:19`, `:94-100`, `:118-123`, `:124`, `:125`, `:130`, `:146-158` (lines 588-592). **The census brief's claimed `:86-200` cite does NOT exist in the file at df7085bb** — `grep -nE ':[0-9]{2,3}' templates/fif_saved_briefcase.js` returns only the seven above. (For the record, `validate_investigation_manifest` spans api/investigation_contracts.py:84-174, so a `:86-200` cite would also over-run the file's 174 lines.)

| macro cite (comment at briefcase :585-592) | macro claim | actual at c799ba7e | verdict / current line |
|---|---|---|---|
| `:19` | "'issuer' in KINDS" | api/investigation_contracts.py:19 = `KINDS = frozenset(("security","issuer",…))` | **CORRECT** |
| `:94-100` | "subjects kind/owner/object_id" | :94 `def subject`, :95 key set, :96 owner NAMESPACE, :97 object_id ≤256 single-line, :98-99 optional version_ref, :100 admission gate | **CORRECT** (return tuple is :101) |
| `:118-123` | "evidence owner/object_type/object_id/mode" | :118 `def evidence`, :119 key set (incl. mode), :120-121 owner/object_type NAMESPACE, :122 object_id, :123 ADMISSION gate | **PARTIAL** — :123 is the admission gate, not a field rule; the mode VALUE check is :124 (next cite). Correct narrow cite for the four field names: :119-122 |
| `:124` | "mode pinned\|follow_head" | :124 `choice(r["mode"], …, ("pinned","follow_head"))` (pinned-only when baseline) | **CORRECT** |
| `:125` | "pinned requires version_ref" | :125 `require(r["mode"] != "pinned" or "version_ref" in r, …, "pinned_version_required")` | **CORRECT** |
| `:130` | "follow_head carries neither version_ref nor fingerprint" | :130 `require(r["mode"] != "follow_head" or not ({"version_ref","fingerprint"} & r.keys()), …)` | **CORRECT** |
| `:146-158` | "intent.research_as_of is a plain YYYY-MM-DD date" | :146-151 = intent key set + title/question/subjects/horizon; research_as_of is **:152-158** (regex :154, calendar :155-158) | **OVER-BROAD** — correct narrow cite :152-158; also the macro comment omits that the date must be a REAL calendar date, not just regex-shaped |
| (not in file) `:86-200` | (census brief asserted this cite) | no such cite exists in templates/fif_saved_briefcase.js at df7085bb | N/A — grep commands above |

**Material omissions in the macro comment (the drift that matters for X2-b, none of it line-number drift):** the block records field shapes only and does NOT record (a) the `unknown_field` policy that rejects the top-level carrier key `fif_saved_research` (api/investigation_contracts.py:34 via :89; terminal/lib/investigationContracts.ts:139 via :245; SQL:92), (b) the admission gate that refuses owner `fif` in production (terminal/lib/investigations.ts:7-13; SQL:110/:141), (c) the v2-only + empty-thesis_refs command constraints (terminal/lib/investigations.ts:52; SQL:93/:131), (d) calendar-valid `research_as_of` (:155-158).

---

## Q11 — Field-by-field verdict on macro's `toInvestigationManifestV2` (templates/fif_saved_briefcase.js:606-639, constants :28/:31/:32)

Macro emits (per :616-638): `schema`, `intent{title, question, subjects[1]}`, `layout_refs: []`, `thesis_refs: []`, `evidence_refs[…]`, `continuation: {}`, optional `intent.research_as_of`, and the top-level carrier `manifest[CARRIER_KEY] = copy(saved)` (:637, CARRIER_KEY='fif_saved_research' :31).

| macro emission | Terminal verdict at c799ba7e | detail |
|---|---|---|
| `schema: 'investigation_manifest.v2'` (:617, const :28) | **ACCEPTED** | exact v2 string (Python :90; TS :247; SQL :93) |
| `intent.title = text(saved.name,160)` (:619) | **ACCEPTED-ONLY-IF** non-empty and single-line and surrogate-safe | macro `text()` (briefcase :77-80) returns `''` for a missing/blank name → Terminal `empty_text` (Python :41; TS :145; SQL :70); macro trims ends but an INTERNAL newline/tab survives → `invalid_control` (single-line rule, Python :47-48; TS :153-154; SQL :72); macro slices by UTF-16 units (:79) so a 160-unit cut can split an astral pair → `invalid_unicode` (Python :44; TS :149). Slice-by-units also means emitted length in Terminal scalars is always ≤ the limit otherwise. |
| `intent.question: 'Filing forensics saved view'` (:620) | **ACCEPTED** | literal, non-blank, 25 chars ≤ 4000 (Python :148; TS :255; SQL :96) |
| `intent.subjects = [{kind:'issuer', owner:'fif', object_id}]` (:621-623) | **REJECTED** (whole manifest) | `issuer` ∈ KINDS (Python :19) and `fif` matches NAMESPACE (:96), but NO production admission admits owner `fif` → `unsupported_owner_kind` (TS :201-204 via terminal/lib/investigations.ts:51, :8-11; Python :100 under default admission; SQL :110 → `invalid_payload`). |
| ↳ `object_id = text(saved.issuer.entity_id,256)` | (moot while owner rejected) ACCEPTED-ONLY-IF non-empty (guarded at macro :608 — null return, never emitted blank), single-line, surrogate-safe | same text rules (Q3) |
| `layout_refs: []` (:625) | **ACCEPTED** | empty is lawful (no minimum; Python :159; TS :260; SQL :117-120) |
| `thesis_refs: []` (:626) | **ACCEPTED and REQUIRED** | commands with any thesis ref are refused (terminal/lib/investigations.ts:52; SQL :131) |
| `evidence_refs[i].owner: 'fif'` (:597) | **REJECTED** (whole manifest) | not in production evidence admission `earnings.workspace_generation` (terminal/lib/investigations.ts:12; TS :226-228; SQL :141) |
| `evidence_refs[i].object_type: 'occurrence'` (:598) | **REJECTED** (whole manifest) | only `event_workspace` admitted (same cites) |
| ↳ `object_id = text(ref.occurrence_id,256) \|\| text(ref.accession,256)` (:594) | ACCEPTED-ONLY-IF non-empty (blank refs are silently SKIPPED by macro :595 — that is a macro-side loss channel for A→B if neither id exists, not a Terminal refusal), single-line, surrogate-safe | Q4 text rules |
| `mode: pinned ? 'pinned' : 'follow_head'` (:600) | **ACCEPTED** | both legal values (Python :124; TS :229; SQL :142) |
| `version_ref` only when pinned (:602) | **ACCEPTED-ONLY-IF** non-empty (macro falls back to objectId, so never blank), ≤256, single-line | pinned requires it (Python :125; TS :230; SQL :143); macro emits no `fingerprint` ever — fine (optional) |
| follow_head entries carry no version_ref/fingerprint | **ACCEPTED** | exactly the rule (Python :130; TS :233-235; SQL :144) |
| duplicate evidence tuples | ACCEPTED-ONLY-IF all `(owner,object_type,object_id,mode,version_ref)` tuples distinct | two saved refs sharing occurrence_id+mode → `duplicate_reference` (Python :143; TS :190; SQL :150) |
| `continuation: {}` (:628) | **ACCEPTED** | lawful (Q6) |
| `intent.research_as_of` only when pinned + regex-shaped (:630-632) | **ACCEPTED-ONLY-IF a real calendar date** | macro only regex-tests `^\d{4}-\d{2}-\d{2}$` (:632); Terminal also requires calendar validity → `invalid_date` (Python :155-158; TS :173-181; SQL :101). Absent otherwise — fine (optional). |
| `manifest['fif_saved_research'] = copy(saved)` (:637) | **REJECTED — this single emission makes Terminal refuse the ENTIRE manifest** | top-level `unknown_field`: Python :34 via :89; TS :139 via :245; SQL :76-77 via :92 → `invalid_payload`. It is not dropped, not kept. |

**Bottom line for R1/R2:** the mapped (native) projection — minus the carrier, and with owners admitted — is fully within the v2 grammar; the two hard refusals are the owner admissions (`fif`+`issuer` subjects; `fif`/`occurrence` evidence) and the carrier key itself. The carrier is the lossless half of the round trip (macro comment :634-636), so under the current Terminal contract a LOSSLESS round trip through Terminal is impossible: keeping the carrier ⇒ refused manifest; dropping it ⇒ lossy. There is also no place else in the grammar to hide the payload (Q9). Also note `fromInvestigationManifestV2` (macro :641-647) keys off `manifest[CARRIER_KEY]` — a Terminal-stored-and-returned manifest (jsonb round trip preserves unknown keys only if admitted; today they never are) is the other half macro's test must pin.

Macro-side conditions that need NO Terminal change (recorded for the mapping test): title/object_id/version_ref blankness, internal tab/newline, split surrogates; calendar-valid `research_as_of`; distinct evidence tuples; ≤128 KiB v2 envelope (route caps the whole POST body at 132 KiB, route.ts:48).

---

## GATE TEXT

Terminal-side changes a LOSSLESS round trip through Terminal would require. Per seat ruling R2 these are delivered as text only — no Terminal patch is attached or implied; macro sessions may not edit Terminal.

**GATE 1 — Admit a carrier/extension field for an external product's payload.**
- WHAT: add one optional, namespaced extension key (exact name is the Terminal owner's choice; macro's candidate is `fif_saved_research`) to the manifest grammar in ALL THREE validators plus the TS type: `InvestigationManifest` (terminal/lib/investigationContracts.ts:47-61) and `Validator.manifest` optional set (:245); `obj` call in `validate_investigation_manifest` (api/investigation_contracts.py:89) — its optional tuple `("review_baseline_ref",)`; and `valid_investigation_manifest_v2`'s key admission (supabase/migrations/0028_investigations.sql:92, key function :74-78) — plus a bounded size/content rule for it (the v2 envelope already caps at 131072 bytes, SQL:93; the Terminal owner must decide the sub-budget). The readback paths re-validate, so the key must be admitted consistently everywhere manifests are re-checked: terminal/lib/investigations.ts:52, :69, :112.
- WHO: the Terminal repository owner — the investigations / Saved Research owner lane (PR #777 / migration 0028 owner; docs/INVESTIGATION_V2_CONTRACT.md:1-6 names it the "#777 integrated owner"). Macro sessions may not edit Terminal (R2).
- WHY: macro's `fif_saved_research` carrier (templates/fif_saved_briefcase.js:637) is the only lossless half of the A→B mapping; today it is refused `unknown_field` on every surface (api/investigation_contracts.py:34; terminal/lib/investigationContracts.ts:139; SQL:92), so a Terminal round trip either refuses the manifest or, if macro dropped the carrier, loses the saved view (violating R1).

**GATE 2 — Admit owner `fif` (kind `issuer`) for subjects.**
- WHAT: add `{ owner: "fif", kinds: ["issuer"] }` to `INVESTIGATION_ADMISSION.subjects` (terminal/lib/investigations.ts:8-11) AND widen the hard-coded SQL pair list in `valid_investigation_manifest_v2` (supabase/migrations/0028_investigations.sql:110 — currently only `terminal.analysis_symbol`+security and `data_os.security_master`+security/issuer) via a new migration; the pure validators need no change (admission is already a parameter, api/investigation_contracts.py:100; terminal/lib/investigationContracts.ts:201-204).
- WHO: Terminal repository owner (same lane as GATE 1; the SQL change is a new migration, 0028 is applied and immutable-by-practice, SQL:2).
- WHY: macro emits subject `{kind:'issuer', owner:'fif', object_id}` (templates/fif_saved_briefcase.js:622); without admission the whole manifest is refused `unsupported_owner_kind` (TS) / `invalid_payload` (SQL).

**GATE 3 — Admit evidence owner `fif` with object_type `occurrence`.**
- WHAT: add `{ owner: "fif", object_types: ["occurrence"] }` to `INVESTIGATION_ADMISSION.evidence` (terminal/lib/investigations.ts:12) AND replace the hard-coded equality at supabase/migrations/0028_investigations.sql:141 (`r->>'owner'<>'earnings.workspace_generation' or r->>'object_type'<>'event_workspace'`) with an admitted-pairs test that includes `fif`/`occurrence`, in the same new migration. If `occurrence` objects are to be resolvable/readable in Terminal (not just referenceable), that is additional owner work outside this census's scope — the contract only checks shape (TS header :2-4).
- WHO: Terminal repository owner (same lane).
- WHY: macro emits evidence refs `{owner:'fif', object_type:'occurrence', …}` (templates/fif_saved_briefcase.js:597-598); today every such ref refuses the manifest (TS :226-228; SQL :141).

**No Terminal change required for:** empty `layout_refs`/`thesis_refs`/`continuation{}` (all lawful; thesis empty is mandatory anyway), the v2 schema string, the literal question, `follow_head`/`pinned` mode usage, or the optional `research_as_of` — those are macro-side obligations only (calendar-valid date, single-line/non-blank strings, distinct evidence tuples, envelope size).

---

## Census hygiene record

- Working-tree status, BEFORE: `git -C ~/lanes/wt/fif-x2b-census-20261013 status --porcelain | wc -l` → **0**; `git -C ~/lanes/repos/mastermind-terminal status --porcelain | wc -l` → **0**.
- Working-tree status, AFTER (measured at lane end): `git -C ~/lanes/wt/fif-x2b-census-20261013 status --porcelain | wc -l` → **0**; `git -C ~/lanes/repos/mastermind-terminal status --porcelain | wc -l` → **0** — both unchanged from BEFORE.
- Files written: ONLY `~/lanes/out/fif/fif-x2b-census-20261013/X2B_TERMINAL_CENSUS.md` (this file) and `~/lanes/out/fif/fif-x2b-census-20261013/terminal_manifest_v2_contract.json` (D2).
- D2 parse check: `python3 -c "import json,sys; json.load(open(sys.argv[1]))" ~/lanes/out/fif/fif-x2b-census-20261013/terminal_manifest_v2_contract.json` → **rc=0**.
- No network, no gh, no workflow dispatch, no secrets/env reads, no `.claude/` access, no writes into either git tree. The banned status-word and hold marker strings do not appear in either output file (grep-checked after writing; 0 hits each).
