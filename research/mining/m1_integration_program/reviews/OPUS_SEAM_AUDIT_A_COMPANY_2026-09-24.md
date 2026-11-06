# Opus READ_ONLY seam audit — Mining M1 Company-Intelligence / earnings-receipt seams (T02, T03, T07)

Date 2026-09-24. MODE: READ_ONLY. Refs: `origin/main` b38ba86e; `refs/remotes/pr/7870` (Semiconductor B); `refs/remotes/pr/7905` (CDV-1 T1, accepted sibling idiom); `origin/sol/mining-principal-research-20260923` (frozen Mining corpus). No file in the worktree was written; the only artifact is this report.

## 1. Findings

**F1 — BLOCKER (T02 packet as written orders an unauthorized acquisition act).** Plan §4 bullet 1 ("Acquire the selected C1/C2/C3 and R1/R2 source bodies through approved existing intake … retain their actual receipt and availability clocks") is a worker checkbox. The frozen corpus itself records that no original bytes were obtained and that the container could not resolve `www.sec.gov` (`research/mining/MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md` §1, "native retained-body hash, byte offsets, span-receipt ID … remain unestablished"), and the addendum leaves G2 and IR-05 (source-use / republication rights) open (addendum §3 rows G2/G5, §4 IR-05). Correction: the T02 fabric packet is **synthetic-only**; real-byte acquisition is an owner/intake step held behind G2+IR-05 and must be removed from the build packet and recorded as a held gate (R-IND-12 precedent, `research/industrials/first_vertical_program/rulings/R-IND-2026-09-24-wave1.md:24`).

**F2 — MAJOR (T03's own test contract imports a module that cannot exist yet).** Plan §5's frozen expectation imports `compose_mining_research` from `engine/market_ontology/mining_theme_research.py`, which consumes the T01 shared generalization; the shared route/kernel the plan calls "existing" (plan §2 row `app/theme_research.py`, `site/assets/js/theme-research.js`) exists on neither ref — main's own ruling record states #7870 "has no `app/theme_research.py`, no aggregator, no `theme-research.js`" (`…/R-IND-2026-09-24-wave1.md:7`, ruling R-IND-00; R-IND-20 at `:32`). Correction: T03's owned suite `tests/test_mining_economic_inputs.py` asserts on the **Company-owner fact rows** returned by `mp_profile()`/`fcx_profile()` extraction (the `event_fact.v1` row shape at `engine/company_intelligence/pg_profile.py:198-209@pr/7905`); every `compose_mining_research(...)` assertion moves to T04/Auditor-B scope. `missing_derivation` / `interpretation_stale` are composition **limitation** strings, never Company-owner outputs.

**F3 — MAJOR (`profile_for_ticker` signature moves under #7905; Mining must serialize and must use the private branch).** On main: `def profile_for_ticker(ticker: str) -> IssuerProfile | None` (`engine/company_intelligence/issuer_profiles.py:1293@origin/main`). On pr/7905: `def profile_for_ticker(ticker: str, *, publication: str = "public", fiscal_scope: tuple[str,str,str,str] | None = None)` with a hard-coded private branch `if publication == "private" and normalized == "PG"` and `raise ValueError("private PG profile requires fiscal_scope")` (`issuer_profiles.py:1293-1312@pr/7905`). Plan T02 forbids public enrollment ("Do not add FCX/MP to `DISCOVERY_TICKERS` or public `production_registry()`"), so FCX/MP **must resolve only under `publication="private"`**, mirroring PG. T02 therefore branches only after #7905 merges (same hunk), and the edit is ONE contiguous `_MINING_PROFILE_FACTORIES` block + one branch appended after the PG branch, homebuilder dicts untouched.

**F4 — MAJOR (the plan's duplicate-literal obligation is a *window* obligation, not a receipt feature).** Verified by execution (§3): `receipt_for_literal` refuses any literal occurring twice in its window (`engine/earnings_release/receipts.py:253-259@origin/main`). So IR-02's "a valid literal appearing in both Q2 and H1 columns" can only be **selected**, never disambiguated, by the receipt layer. The accepted idiom narrows the window to the parsed cell: `_receipt(bound, cell.source_span.char_start, cell.source_span.char_end, literal)` (`pg_profile.py:171-183@pr/7905`, called at `:245`/`:256`). Correction: T02's "approved parsed row/column scope" is frozen as *heading → row label → column header* selection (`_column(table, row_label, header)`, `pg_profile.py:150`), receipt window = that cell's span; the duplicate-literal test proves the document-wide window **refuses**, and a second test proves the cell-scoped window **mints**.

**F5 — MAJOR (signs/units are the Company owner's, not the receipt's).** The corpus claims the receipt helpers "preserve original UTF-8 bytes, source and span digests and **normalized value**" (witness doc §4 N4). Executed probe: a receipt over `(20,296)` replays the raw literal `'(20,296)'`; `SpanReceipt` exposes no `normalized_value` attribute. Sign, unit, scale and basis must ride the fact row (`value`,`unit`,`period`,`basis` in `_present`, `pg_profile.py:200-209@pr/7905`) and a definition-driven parser (`parse_pg_literal(value, *, unit)`, `:116`). W-R's GAAP net loss and the elimination row therefore carry their negative sign through the Company/financial route, exactly as Global Constraints demand, and never through the nonnegative physical-observation slot.

**F6 — MAJOR (typed absences are a closed 14-word vocabulary; the plan's words are not in it).** `ABSENCE_REASONS` (`engine/company_intelligence/documents.py:72-87@origin/main`, unchanged on pr/7905) = `no_source_document, no_transcript, no_primary_release, no_span_addressable_evidence, document_bytes_not_held, scanned_image_no_text_layer, unjoinable_filing_identity, speaker_unresolvable, slide_family_discontinued, superseded_by_duplicate, missing_basis, missing_units, missing_period, missing_source`; `TypedAbsence.__post_init__` raises on anything else (`documents.py:508-512`). `missing_derivation`, `interpretation_stale`, `missing_stream_threshold`, `definition_unqualified:*` are NOT absence reasons. Frozen mapping is in §4 T02/T03 specs.

**F7 — MAJOR (IR-01 cannot bind to `assess_management_sequence` for W-C, for a second reason the plan does not state).** `guidance_history.py` exists only on pr/7870 (absent from `git ls-tree origin/main engine/company_intelligence/`). Its signature is `assess_management_sequence(prior, actual, next_outlook, *, native_derivations=None)` (`engine/company_intelligence/guidance_history.py:226@pr/7870`) — `next_outlook` is **positional and required**. W-C is a prior-estimate-vs-actual pair with no next-period outlook, and Global Constraints forbid promoting a same-year revision to one. `definition_unqualified:<field>` is emitted only for `_OPTIONAL_DEFINITION_FIELDS = ("basis","currency","perimeter","definition")` and only when the field is None on **both** prior and actual (`:294-296`), schema `management_sequence_assessment.v1` (`:25`). Correction (mirrors R-IND-18): Mining binds the literal `definition_unqualified:` prefix through ONE module constant in `mining_issuer_profiles.py`, delegates to the helper only when importable, and otherwise returns a typed `projector_unbound` refusal — it never calls the helper for W-C and never invents a range/midpoint.

**F8 — MAJOR (the CI seam named in the commission does not exist on main).** `earnings-economic-dossier` is absent from `origin/main:.github/ci/legacy-jobs.yml` (grep empty) and present only at `pr/7905:.github/ci/legacy-jobs.yml:13436-13484` with `if: ${{ false }}` / `gate: code` / `scope: exclusive` and `run: python -m pytest tests/test_pg_economic_observations.py tests/test_pg_economic_observations_probes.py -q`, plus `CURATED_EXCLUSIVE` entry `tests/test_ci_pack.py:3535@pr/7905` (set at `:3508`, asserted at `:3764`). Mining must mint its **own** `mining-economic-dossier` block appended at the END of the freshly fetched `origin/main` job map, with its `CURATED_EXCLUSIVE` entry in the same PR (R-IND-19). Wiring a Mining suite into the PG job's `run:` line would both edit a contested sibling PR's block and — per the standing law — red `contract-delta` fleet-wide if any test in the run line is missing from `paths:`.

**F9 — MINOR (two names the plan forbids editing do not live where it implies).** `issuer_profiles.py` defines no `DISCOVERY_TICKERS` and no `def production_registry` on either ref; the only trace is the comment at `issuer_profiles.py:136@origin/main`. Verified owners: `def production_registry() -> IssuerRegistry` is at `engine/company_intelligence/event_workspace.py:180@origin/main`; `DISCOVERY_TICKERS` does not exist anywhere under `engine/`, `scripts/` or `app/` on main (`git grep` empty) — the corpus locates the discovery tuple at `scripts/refresh_event_workspaces.py:100-122` on the shared candidate (witness doc N2). The prohibition is correct but must name those real owners to be checkable.

**F10 — MAJOR (the sibling's `fact_id` convention is a KNOWN OPEN DEFECT; copying it imports the defect).** `"fact_id": f"fact_{definition.metric}"` (`pg_profile.py:201` and `:217@pr/7905`) is metric-scoped only. The frozen reviewer probe says so in its own docstring: *"fact_id must derive from (event, metric, period, basis) … At bc33493b both events mint ``fact_pg_diluted_eps`` (pg_profile.py:201/217)"* (`tests/test_pg_economic_observations_probes.py:498-505@pr/7905`, assertions `q4_id != q1_id` at `:511`, borrowed-id refusal at `:514-515`). This is the seat's freeze-the-probe-RED idiom, not settled behaviour. Correction: Mining derives `fact_id` from `(event_id, metric, period, basis)` from the first line — never `f"fact_{metric}"` — and its own suite carries the two-event distinctness and borrowed-id refusal tests.

**F11 — MINOR (T02/T03/T07 consume a fixture loader owned by an unlanded task).** `tests/mining_casebook.py::synthetic_case` is created by T01 (plan §2, §4). If T01 slips, three suites are unimportable. Correction (R-IND-21 precedent, `…wave1.md:33`): the packet freezes a ≤10-line local loader with a citation rather than importing an unmerged helper.

**F12 — MAJOR (a private span payload needs a rights token that only `qa_exchange.py` may declare).** The pg idiom stamps every span with a module constant `PG_PRIVATE_RIGHTS_PROFILE = "rp_internal_private_v1"` (`pg_profile.py:26`), passed as `rights_profile=` into `text_span(...)` (`:184-196`), and the frozen probe `test_private_rights_token_is_the_single_registry_entry` asserts the token is in `qa_exchange.RIGHTS_PROFILES` and that the **only** declaring file is `qa_exchange.py` (`tests/test_pg_economic_observations_probes.py:547-565@pr/7905`). Mining therefore cannot mint a private span without (a) one Mining rights constant in `mining_issuer_profiles.py` and (b) its registration in `engine/company_intelligence/qa_exchange.py` — a second edit to a shared owner file that the plan's §2 file map does not mention at all, and which must be in the CI job's `paths:`. Per R-IND-13, 10-Q/filing-edition spans use `rp_unknown_v1`-class handling until the rights owner qualifies the use.

## 2. Seam table

| Plan name | main | pr/7905 | pr/7870 | Binding candidate |
|---|---|---|---|---|
| `IssuerProfile` | `issuer_profiles.py:156-178` (4 fields, `extract_guidance` default `_no_guidance:151`) | unchanged | unchanged | import `IssuerProfile`, `_no_guidance` only; add NO field |
| `profile_for_ticker` | `:1293` `(ticker)` | `:1293` `(ticker, *, publication="public", fiscal_scope=None)` | unchanged | private branch after PG; serialize behind #7905 |
| `issuer_for_ticker` | `:1280` | `:1280` (+`_HOMEBUILDER_ISSUER_FACTORIES:128`) | unchanged | one merge line, appended |
| `_<SECTOR>_PROFILE_FACTORIES` | `_HOMEBUILDER_PROFILE_FACTORIES:1272` | same | same | `_MINING_ISSUER_FACTORIES` + `_MINING_PROFILE_FACTORIES` contiguous before `issuer_for_ticker` |
| `production_registry()` / `DISCOVERY_TICKERS` | not defined in `issuer_profiles.py` (comment `:136`) | same | discovery tuple in `scripts/refresh_event_workspaces.py:100-122` (corpus N2) | do not touch; record as held gate |
| `IssuerIdentity` | `identity.py:146-155` (`company_id`, `display_name`, `fiscal_year_end_month`, `reporting_currency`, `listings`, `issuer_kind`, `external_ids`) | unchanged | unchanged | CIK via `external_ids` + `company_id_for_cik:50` |
| `production_registry()` | `event_workspace.py:180` | unchanged | unchanged | never enrolled by Mining in M1 |
| private rights token | `qa_exchange.py` `RIGHTS_PROFILES` (sole declaring file) | `PG_PRIVATE_RIGHTS_PROFILE="rp_internal_private_v1"` `pg_profile.py:26`, used `:184-196` | — | one Mining constant + one `qa_exchange.py` registration (F12) |
| `IssuerRegistry` | `identity.py:229` | re-exported, pg imports `from .event_workspace import IssuerRegistry` (`pg_profile.py:18`) | — | follow pg import path |
| `build_event_workspace` | `event_workspace_build.py:108`, `profile:` kwarg `:125`, `prior_lifecycle_state` `:123` | unchanged | unchanged | pass `profile=` explicitly |
| `bind_release_document` | `binding.py:244`, `form: str = "8-K"` (unvalidated) | unchanged | unchanged | `form="10-Q"` for C3/R2 editions |
| `ABSENCE_REASONS` | `documents.py:72-87` (14, closed) | unchanged | — | closed list only |
| `DocumentRevisionChain` | `documents.py:236-303`, `mints_event:283` | unchanged | — | T07 A→B→A owner |
| `receipt_for_literal` / `_char_span` / `replay_receipt` / `ReceiptError` | `receipts.py:233 / :191 / :138 / :51` | unchanged | unchanged | cell-scoped windows |
| `assess_management_sequence` | ABSENT | ABSENT | `guidance_history.py:226`, schema `:25`, `definition_unqualified:` `:296` | import-guarded, one module constant |
| `mining-economic-dossier` CI job | absent | sibling `earnings-economic-dossier` `legacy-jobs.yml:13436` | — | new block at END of main's map |
| sibling idiom | — | `pg_profile.py` (431 lines): `_table:139`, `_column:150`, `_receipt:171`, `_span:184`, `_present:198`, `_absent:212`, `_row_fact:230`, `parse_pg_literal:116`, `_scope:83`, `pg_profile(*, fiscal_scope):99` | — | copy the SHAPE, not the constants |

## 3. Executed evidence (the plan's own receipt test)

Run from the worktree root, `python3 -` heredoc, rc line quoted verbatim:

```
MASK: '                       710     '
REPLAY: '710'
char_start: 23 rindex: 23 EQ: True
ASSERT1 True
DUP ReceiptError: literal '710' occurs more than once in the window — ambiguous location, refusing to mint a receipt
NEG replay: '(20,296)' span_text: '(20,296)' normalized: None
RC=0
```

Reading: the plan's `test_receipt_ignores_style_attribute` **passes today, unchanged** — it is existing-behavior evidence, not a new fix (plan §4 already concedes this). Its `rindex` assertion is weak on its own (it would also pass for a last-occurrence heuristic); the masking property is proven by `MASK:` showing the `style="width:710%"` bytes blanked at equal length, which is why offsets stay source-absolute. The DUP line is the T02/IR-02 obligation's real shape (F4). The NEG line is F5.

## 4. FROZEN SPEC blocks

### FROZEN SPEC — T02 (witness source bytes + native Company profiles)
```
OWNED FILES: engine/company_intelligence/mining_issuer_profiles.py (new)
             tests/test_mining_witness_profiles.py (new)
             tests/mining_fixtures.py (new; synthetic filings + ≤10-line local case loader)
             engine/company_intelligence/issuer_profiles.py (ONE contiguous block + 2 merge lines)
IMPORTS (exactly, pg idiom pr/7905 pg_profile.py:15-22):
  from .documents import TypedAbsence, text_span
  from .event_workspace import IssuerRegistry
  from .identity import IssuerIdentity, ListingAlias, company_id_for_cik
  from .issuer_profiles import IssuerProfile, _no_guidance
  from ..earnings_release.binding import BoundRelease, bind_release_document
  from ..earnings_release.receipts import ReceiptError, SpanReceipt, receipt_for_literal
  NEVER import issuer_profiles' module-private helpers at :304-419 (_fact_present/_literal_receipt/...)
SIGNATURES:
  FCX_CIK = "0000831259"; MP_CIK = "0001801368"; MINING_TICKERS = ("FCX","MP")
  def fcx_issuer() -> IssuerIdentity; def mp_issuer() -> IssuerIdentity
  def mining_private_registry() -> IssuerRegistry
  def fcx_profile(*, fiscal_scope: tuple[str,str,str,str]) -> IssuerProfile
  def mp_profile(*, fiscal_scope: tuple[str,str,str,str]) -> IssuerProfile
  issuer_profiles.py edit: _MINING_ISSUER_FACTORIES/_MINING_PROFILE_FACTORIES + in profile_for_ticker
    a branch AFTER the PG branch: publication=="private" and normalized in _MINING_PROFILE_FACTORIES
    -> requires fiscal_scope (ValueError otherwise, pg wording). No public/default resolution.
SELECTOR LAW: heading -> row label -> column header (_table/_column shape), then, with the EXACT
  attribute names the sibling uses (pg_profile.py:171-182 — bound.body/bound.body_sha256 do NOT exist):
    receipt_for_literal(source=bound.source, source_sha256=bound.revision.source_sha256,
      search_start=cell.source_span.char_start, search_end=cell.source_span.char_end,
      literal=cell.text.strip())            # ReceiptError -> typed absence, never a fallback match
  span payload: text_span(document_id=..., document_version=1,
      body_sha256=bound.revision.source_sha256, segment_index=0, segment_text=bound.source,
      start_byte=receipt.byte_start, end_byte=receipt.byte_end, text=receipt.span_text,
      rights_profile=MINING_PRIVATE_RIGHTS_PROFILE).to_payload()   # pg_profile.py:184-196
  MINING_PRIVATE_RIGHTS_PROFILE must be registered in engine/company_intelligence/qa_exchange.py,
  the only file allowed to declare a rights token (F12).
  Document-wide windows are forbidden. fact_id derives from (event_id, metric, period, basis) — the
  sibling's f"fact_{metric}" is an open probe defect (F10) and must not be copied.
ABSENCE REASONS (closed, documents.py:72-87): ambiguous/duplicate cell or unaddressable ->
  no_span_addressable_evidence; unit/definition mismatch -> missing_units; no period column ->
  missing_period; basis absent -> missing_basis; body not held -> document_bytes_not_held;
  accession unjoinable -> unjoinable_filing_identity. NO new word.
FIXTURE LAW: synthetic HTML only; invented issuers; sources under example.invalid; invented
  CIK-shaped ids in fixtures (real FCX_CIK/MP_CIK only as module identity constants);
  synthetic: true on every case; NEVER a live FCX/MP figure in tests or CI evidence.
RED:   python -m pytest tests/test_mining_witness_profiles.py -q   (expect collection/assert failures)
GREEN: same command; plus python -m pytest tests/test_issuer_profiles.py tests/test_event_workspace_build.py -q
MUTANT: (a) widen the receipt window to the whole body -> DUP ReceiptError expected;
        (b) swap Q2/H1 column header -> value must change or absence; (c) add "FCX" to the public
        branch of profile_for_ticker -> a test must fail.
HELD (not in this packet): real SEC byte acquisition (G2), rights disposition (IR-05),
  DISCOVERY_TICKERS/refresh_event_workspaces enrollment (#7870), Data OS issuer bridge.
```

### FROZEN SPEC — T03 (definition-safe economic inputs)
```
OWNED FILES: engine/company_intelligence/mining_issuer_profiles.py (extend), tests/test_mining_economic_inputs.py
NO import of engine/market_ontology/* in this packet (F2). Assertions are on fact rows, not on a response.
ROW SHAPE (frozen, pg_profile.py:198-209): {"schema":"event_fact.v1","fact_id":...,"event_id":...,
  "metric":...,"value":...,"unit":...,"period":...,"basis":...,"source_span":...}
  absent row: same keys minus value/unit/period/basis, plus "typed_absence": TypedAbsence(...).to_payload()
DEFINITION CARRIER: a frozen MiningDefinition dataclass (metric, value_kind, unit, scale, basis, scope,
  period_duration_days, comparison_family, segment_scope) — quarter-vs-half-year, elimination sign,
  GAAP-vs-adjusted and cost exclusions travel ON the definition and in `basis`/`period`, never inside a
  display string, never recomputed from text.
SIGNED VALUES: parse_mining_literal(value, *, unit) -> float | None; parenthesized negatives return a
  negative float; the receipt keeps the raw literal (verified: replay returns '(20,296)').
  Signed facts use the Company/financial route; the nonnegative physical-observation slot is untouched.
IR-01 BINDING (guidance_history is absent on main): one module constant
  DEFINITION_UNQUALIFIED_PREFIX = "definition_unqualified:"  (mirrors guidance_history.py:296@pr/7870)
  and MANAGEMENT_SEQUENCE_SCHEMA = "management_sequence_assessment.v1" (:25@pr/7870).
  assess_management_sequence is called ONLY through a guarded import and ONLY when a real
  next_outlook exists; W-C (prior estimate + actual, no outlook) NEVER calls it -> typed
  `projector_unbound` refusal. No invented low/high range, no midpoint, no beat/miss/badge wording.
OPTIONAL ARITHMETIC: any percentage, difference, midpoint, metal-equivalent or total requires the
  financial owner's derivation receipt (formula identity, sign, unit, input refs, cutoff). Absent that,
  the module returns the reported values plus a `missing_derivation` LIMITATION string (never a
  TypedAbsence reason) and the reported result stays visible.
TESTS (minimum): positive reported value; signed loss stays negative; the same literal in Q2 and H1
  columns binds the Q2 cell; two missing bases -> missing_basis rows; PPA/price-protection income is
  never mapped to a revenue metric; production vs sales quantities are distinct metrics; a derivation
  whose consumed revision changed is refused (binds ALL consumed revisions, not just event_id).
RED:   python -m pytest tests/test_mining_economic_inputs.py -q
GREEN: same + python -m pytest tests/test_mining_witness_profiles.py -q
MUTANT: rename the PPA metric to revenue -> test fails; drop `basis` from a definition -> test fails;
  supply a qualified definition pair -> the consumer must NOT suppress the genuine comparison.
```

### FROZEN SPEC — T07 (corrections, replay, version identity)
```
OWNED FILES: tests/test_mining_updates.py (+ fixtures only). Owner code is edited ONLY under an
  owner grant with a reproduced RED (plan §9).
CONSUMES: documents.DocumentRevisionChain (documents.py:236-303, mints_event :283),
  build_event_workspace(prior_source_sha256=, prior_lifecycle_state=, prior_observed_at=)
  (event_workspace_build.py:118-125), bind_release_document(form=) (binding.py:244).
PROOFS (each its own test):
  1 A->B->A keeps THREE semantic revisions (chain length), and the third is not deduped to the first.
  2 Repeated unchanged A mints no new generation AND a prior `corrected` state is re-applied via
    prior_lifecycle_state (the exact regression documented at event_workspace_build.py:129-145).
  3 Unknown version refuses (no silent v1.1 -> v1 renaming); unchanged v1 replay is byte-equal.
  4 A changed source with a stale interpretation refuses or is tagged; it never splices new financial
    objects into old explanatory text.
  5 A later mapping does not appear before its system-recorded cutoff: source cutoff and recorded
    cutoff stay separate fields; a date-only label never gains midnight/UTC/`Z`.
  6 Unchanged-incumbent proof: freeze homebuilder/Apple profile outputs and the public discovery
    comparison BEFORE Mining registration, re-run after, assert byte-equal. Never update the expected
    incumbent outputs to make this pass.
FORBIDDEN: a Mining-local revision index, invalidation engine or second event store; regenerating
  expected hashes from the candidate alone (that is not legacy-parity evidence, IR-04).
RED:   python -m pytest tests/test_mining_updates.py -q
GREEN: same + python -m pytest tests/test_issuer_profiles.py tests/test_event_workspace_build.py \
       tests/test_company_documents.py -q
```

### FROZEN SPEC — CI (all three tasks; created by T02's PR, appended by T03/T07)
```
FILE: .github/ci/legacy-jobs.yml — ONE new contiguous block appended at the END of the job map of a
FRESHLY FETCHED origin/main copy (contested by #7870/#7905/#7881/#7891/#7896/#7900 — never reorder
or edit a sibling block; never add Mining tests to the PG job's run line, F8).
  mining-economic-dossier:
    if: ${{ false }}
    gate: code
    scope: exclusive
    paths:
      - "engine/company_intelligence/mining_issuer_profiles.py"
      - "engine/company_intelligence/issuer_profiles.py"
      - "engine/company_intelligence/documents.py"
      - "engine/company_intelligence/identity.py"
      - "engine/company_intelligence/event_workspace.py"
      - "engine/company_intelligence/event_workspace_build.py"
      - "engine/company_intelligence/events.py"
      - "engine/company_intelligence/contracts.py"
      - "engine/company_intelligence/qa_exchange.py"
      - "engine/earnings_release/binding.py"
      - "engine/earnings_release/receipts.py"
      - "engine/earnings_release/filing_key.py"
      - "engine/fundamental_forensics/disclosure_diff.py"
      - "tests/mining_fixtures.py"
      - "tests/test_mining_witness_profiles.py"
      - "tests/test_mining_economic_inputs.py"
      - "tests/test_mining_updates.py"
    timeout-minutes: 6
    runs-on: ubuntu-latest
    steps: (checkout@v4, setup-python@v5 "3.12", `pip install pytest pyyaml` measured per suite)
    run: python -m pytest tests/test_mining_witness_profiles.py tests/test_mining_economic_inputs.py tests/test_mining_updates.py -q
ALSO IN THE SAME PR: add "mining-economic-dossier" to CURATED_EXCLUSIVE (tests/test_ci_pack.py:~3508,
asserted :~3764) — the set and the manifest must match or test_the_curated_exclusive_set_is_actually_declared
fails. Every test named in the run line MUST have a paths: entry (a missing entry reds contract-delta
on every later PR head fleet-wide).
```

## 5. R-IND-10..16 transfer table (main: `research/industrials/first_vertical_program/rulings/R-IND-2026-09-24-wave1.md:22-28`)

| Ruling | Mining disposition | Why |
|---|---|---|
| R-IND-10 (`<sector>_profiles.py` on the pg idiom; public primitives only; ONE contiguous block + merge lines) | **TRANSFERS** verbatim with names swapped to `mining_issuer_profiles.py` / `_MINING_*` | Same file, same collision set; pg idiom verified at `pg_profile.py:15-22,139-262@pr/7905` |
| R-IND-11 (no field added to `IssuerProfile`/`IssuerIdentity`; CIK in `external_ids`) | **TRANSFERS** | `issuer_profiles.py:156-178`, `identity.py:146-155` identical on all three refs; Mining's quarter/H1 need is met by `fiscal_scope` + column headers, not a new field |
| R-IND-12 (serialize behind #7905; discovery-population is a HELD sub-step) | **TRANSFERS-WITH-EDIT** | Same signature collision (F3). Edit: Mining's held sub-step is `scripts/refresh_event_workspaces.py` discovery + any `production_registry()` enrollment, and it is held behind BOTH #7870 and a publication disposition (plan §4) |
| R-IND-13 (release-edition = public-primary; filing-edition carries `rp_unknown_v1`/`unknown` until rights qualify) | **TRANSFERS-WITH-EDIT** | Mining's C3/R2 are 10-Q editions and IR-05 leaves EDGAR republication unqualified, so filing-edition spans carry `rights_profile="rp_unknown_v1"`. Edit: Mining is **synthetic-only** in M1, so the rights keyword is exercised on synthetic bodies; no verbatim filing body is ever a fixture |
| R-IND-14 (closed 14-reason `ABSENCE_REASONS` only) | **TRANSFERS** verbatim | `documents.py:72-87` unchanged on pr/7905; F6 |
| R-IND-15 (`bind_release_document(form="10-Q")` + distinct `document_kind` + `DocumentRevisionChain`; no second binder) | **TRANSFERS** | `binding.py:244` `form` is unvalidated on main; W-C C3 and W-R R2 are exactly this enrichment case; T07 proof 1 consumes the chain |
| R-IND-16 (`industrials_result_cash.py`, `FORMULA_VERSION`, `build_comparison_receipt`) | **DOES-NOT-APPLY** to T02/T03/T07 | Mining M1 mints **no** derivation module: every optional number is deferred to the existing financial/metric owner's receipt, else `missing_derivation` (plan §5). If a Mining derivation is ever admitted, R-IND-16's closed receipt shape is the precedent to copy, not to re-invent |

## 6. W-C / W-R metric-selection table (labels, bases, periods, source families — NO values)

| Witness | Metric label | Basis / definition scope | Period | Source family |
|---|---|---|---|---|
| W-C | Copper sales | Million recoverable pounds; consolidated reporting; **excludes purchases** | Earlier issued Q2 estimate vs Q2 actual (two separate facts) | C1 8-K exhibit (estimate) / C2 8-K exhibit (actual) |
| W-C | Copper unit net cash cost | USD per pound; **includes by-product credits**, **excludes specified idle/restoration costs** | Same Q2 pair | C1 / C2 8-K exhibits |
| W-C | Copper production | Million pounds; production ≠ sales (separate scope) | Q2 | C2 8-K exhibit |
| W-C | Excluded idle/restoration charge | USD; excluded from the unit-cost measure | Q2 **and** first-half stated separately — never summed | C2 8-K exhibit |
| W-C | Morenci consolidation basis | Proportionate consolidation of a stated interest — already proportionate, never re-multiplied | Q2 | C2 8-K exhibit |
| W-C | Corroboration | Quarterly operating/ownership context; a later filing is NOT knowledge captured earlier | Quarter ended June 30 | C3 10-Q |
| W-R | Materials revenue **including intersegment** | USD thousands; segment revenue row | Q2 column only (H1 columns exist in R2) | R1 8-K Ex-99.1 segment table |
| W-R | Magnetics revenue | USD thousands; segment revenue row | Q2 column | R1 same table |
| W-R | Revenue elimination | USD thousands; **negative sign is part of the fact** | Q2 column, elimination row | R1 same table |
| W-R | Consolidated revenue | USD thousands; issuer-reported total row (reconciles the three above) | Q2 column, total row | R1 same table |
| W-R | Price-protection income | USD thousands; **separate from revenue**, never renamed revenue | Q2 | R1 Materials results / R2 discussion |
| W-R | GAAP net loss | USD thousands; **GAAP**, signed negative | Q2 three-month statement | R1 consolidated results / R2 |
| W-R | Adjusted EBITDA | USD thousands; **non-GAAP**, reconciliation-bound; never conflated with the GAAP line | Q2 | R1 consolidated results + reconciliation |
| W-R | NdPr production | Metric tonnes; physical quantity | Q2 | R1 operating indicators |
| W-R | NdPr sales | Metric tonnes; definition **includes intercompany quantities** — difference vs production is NOT inventory depletion | Q2 | R1 operating indicators + definition footnotes |

Clock law for both: release date, acceptance timestamp, index filing date and reporting-period end are four distinct fields; none is the operating quarter, and an unlabeled display time never gains `Z` (corpus §2, §3).

## 7. Not verified / out of scope

- The probe suite's helpers (`_literal_workspace`, `_pg_rows`, `_validate`, `_refused`) and `engine/company_intelligence/economic_observations.py`'s `validate_selected_facts` (`:67@pr/7905`) were read by symbol grep only; whether Mining should also consume `validate_selected_facts` is an open owner question, not a resolved seam.
- Whether the frozen PG probes currently pass on pr/7905 was NOT determined (no suite was run against that ref); F10 rests on the probe's own docstring, which names the defect at blob `bc33493b`.
- No `gh` call was made: PR states, check results, review threads, merge status and the collision census are the seat's (commission states the census is done).
- Market-ontology composition, schema, route and mount (T01/T04/T05/T06) are Auditor B's; F2 touches them only to keep T03's own suite importable.
- G2/G5 real-byte and rights evidence cannot be produced by any fabric lane from this repo; both stay held.
