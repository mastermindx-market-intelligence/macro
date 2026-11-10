# Lane 5 — `theme_research.request/v2` wire contract (2026-11-09)

Owner: lane 5 suborchestrator (theme research v2 + real industry evidence).
Branch `claude/si-research-v2-20261109`. This note is the Terminal-repo
wire contract for the v2 union shipped through the EXISTING router —
`POST /api/themes/v1/research/query` and `POST /api/themes/v1/research/evidence`
carry BOTH generations; no new path exists.

## 1. Version selection (the discriminator law)

A request body carrying `"request_schema": "theme_research.request/v2"`
selects the v2 union. A body WITHOUT the key keeps v1 parsing and the v1
response envelope byte-for-byte (the v1 fixture suite is the proof; it is
unchanged and green). Any OTHER `request_schema` value is a private 400
`invalid_request` / `fix_request`.

Auth is unchanged and precedes parsing/source access on both generations:
401/403 with the four private headers before any body is read.

## 2. The closed entry-kind union

| entry_kind | key fields | pagination | subject | notes |
|---|---|---|---|---|
| `theme` | `anchor_theme_id`, `slice_key` | `offset` 0..10000, `limit` 1..100 | `slice_key` | the v1 shape + discriminator + context expectation |
| `company_profile` | `profile_id` (`technology_economic_change.v1`), `company_ref` | single-document: NO `limit` field (supplying one is a 400); `offset` must be 0 or omitted | `company_ref` | `anchor`/`slice` forbidden |
| `sector_profile` | `profile_id` (`finance_intelligence_research.v1`), `sector_ref` (`sector:financials`) | single-document, same law | `sector_ref` | view `dossier` only |

All kinds require `view` and `time_mode`. Registered view sets are the
registry's `view_keys` (theme: the semiconductor set; technology:
`business`/`comparison`/`counter_observations`/`identity`/`coverage`;
finance: `dossier`). Registered time modes: theme all three;
both profiles `latest` only today. A `cursor` field exists on no kind —
supplying one is a private 400, never a silent ignore.

Foreign/mixed fields (a theme field on a profile kind, an unknown
`entry_kind`, an unknown `request_schema`) are private 400s at parse.

## 3. Expectation pairing (continuation law)

- First query: omit `expected_generation` AND
  `expected_context_generation`.
- A continuation — `offset > 0` on the `theme` kind, or any pinned read on a
  profile kind — carries BOTH. Exactly-one-supplied is a private 400.
- EVERY evidence request carries BOTH, always (a missing one is a parse 400).

`expected_generation` is the NATIVE generation of the entry — the grammar is
the entry's own (`gen_<32hex>` for the theme/finance entries, `tecd_<32hex>`
for the technology profile; enforced after the entry resolves, so a `tecd_`
token on the theme entry is a 400 naming the grammar rule).
`expected_context_generation` is ALWAYS the shell's `gen_<32hex>` surface.

## 4. Query response — `theme_research.response/v2`

```json
{
  "schema": "theme_research.response/v2",
  "entry_kind": "company_profile",
  "request": {
    "entry_kind": "company_profile",
    "profile_id": "technology_economic_change.v1",
    "company_ref": "co:us:synthetic-alpha",
    "view": "business",
    "time_mode": "latest",
    "source_cutoff": null,
    "recorded_cutoff": null
  },
  "generation": "tecd_0f33abef6a4b…",
  "context_generation": "gen_9c1d0e2f7b8a…",
  "data": { "…the exact registered native payload, unmodified…" },
  "evidence_refs": []
}
```

- `generation` — the vertical's OWN native generation, read from the field
  the registration declares (`dossier_id` for technology, `generation` for
  the gen_-fingerprinted verticals). Never renamed.
- `context_generation` — the shell's fingerprint over: the registration's
  definition version, the FRESH enforced rights revision, the bundle's
  native revision tuple, entry kind + key, subject/view/time_mode/cutoffs,
  and the native generation. Deliberately EXCLUDES `offset`/`limit` and the
  `expected_*` fields, so one collection context survives pagination.
- `data` — the exact registered payload (contract-checked against the
  registration's `schema_id` + `definition_version`; a mismatch is a fixed
  private 503).
- `evidence_refs` — the payload's registered refs field (`evidence_refs` for
  the theme entry; none for technology today; `assertion_refs` for finance),
  `[]` when absent.

Evidence responses are NOT wrapped: `/evidence` returns the vertical's OWN
evidence envelope (technology: `technology_economic_change.evidence.v2`;
finance: `finance_intelligence_research.evidence.v1`) with the same pairing
checks applied.

## 5. Error table (private envelopes; identical for both generations unless noted)

| condition | status | body |
|---|---|---|
| anonymous / unentitled | 401/403 | existing earnings-gate envelope + private headers |
| malformed JSON / unknown `request_schema` / foreign or mixed fields / unknown `entry_kind` | 400 | `{"error":{"code":"invalid_request","action":"fix_request","detail":…}}` |
| unregistered anchor / unknown `profile_id` / subject outside the entry's closed set | 404 | `{"error":{"code":"not_available","action":"none"}}` — no echo, no list |
| unregistered `view`/`time_mode`/`slice_key` | 400 | `invalid_request` / `fix_request`, detail names the rule |
| nonzero `offset` (or any pagination) on a single-document kind | 400 | `invalid_request` / `fix_request`, detail names the pagination law |
| expectation pair half-missing (query) / missing (evidence) / offset>0 without pair | 400 | `invalid_request` / `fix_request` |
| `expected_generation` off the entry's grammar | 400 | `invalid_request` / `fix_request`, detail names the grammar rule |
| stale `expected_generation` OR stale `expected_context_generation` | 409 | `{"error":{"code":"refresh_required","action":"reset_to_first_page"}}` — SAME bytes either way, no leak of which |
| unknown / not-cited / ambiguous / duplicate-span `assertion_ref`; unresolvable subject; sealed input absent | 404 | `not_available` / `none` — byte-identical for all |
| loader cannot serve; composer/registration contract mismatch; rights registry fault; any internal fault | 503 | `{"error":{"code":"service_unavailable","action":"retry_later"}}` |

409 semantics worth naming: the native generation and the context
fingerprint move for DIFFERENT reasons (native: the vertical's sealed
inputs; context: additionally the enforced rights revision and the bundle's
revision tuple). The falsifier pinned in-suite: the same technology inputs
under a changed rights revision keep the native `tecd_` id FIXED while the
context moves — and the continuation carrying the old pair still gets the
one 409 envelope.

## 6. Evidence selection (assertion-grained, v2)

`assertion_ref` is the owner-minted `gmi-curation://` ref
(`^gmi-curation://(?:theme:)?[a-z0-9_.\-]+/gmirca_[0-9a-f]{32}$` — the
canonical `theme:` prefix and hyphen/dot ids are legal). Selection requires
ALL of: the ref matches EXACTLY ONE bundle assertion's minted curation ref;
that assertion's recomputed six-field native source tuple (owner, object_id,
schema, generation, sha256, SELECTOR) is cited by a rendered item of the
composed dossier; and a rendered item citing that tuple carries THAT
assertion's curation revision. Two assertions from one document are
independently selectable when their selectors/revisions differ and each
actually rendered; the duplicate-span sibling (same document AND selector)
cannot borrow the rendered row and shares the private `not_available` with
unknown refs. Never selected by document id; never the first matching row.

## 7. Per-vertical availability (packet §7, ten verticals)

Filled from the lane-5 census + witness tests. AVAILABLE means a real
registered surface serves through this transport today; UNAVAILABLE names
the exact missing real input and its producer — never a synthetic
substitute.

Provenance: derived by the lane-5 suborchestrator from first-hand repo
evidence (registry reads, module reads, the witness suites named per row) on
2026-11-09; the parallel census delegates had not returned before delivery and
nothing below waits on them. The closed transport registers exactly three
entries — `ai_semiconductors` (theme kind), `technology_economic_change.v1`
(company_profile), `finance_intelligence_research.v1` (sector_profile); an
unregistered vertical is unreachable through `/research` by registry law
(private 404), and its row names where its real surface lives.

| vertical | transport state | availability | exact missing real input / producer |
|---|---|---|---|
| semiconductors | registered — `theme`, anchor `ai_semiconductors` | **AVAILABLE** | none missing: real Company Intelligence reader + witness corpus serve today (`tests/test_theme_research_api.py` §13 production-mount, `tests/semiconductor_research_helpers.py`); the private half stays unbound and is served as typed omissions, not synthesized |
| technology | registered — `company_profile`, `technology_economic_change.v1` | **UNAVAILABLE** end-to-end | real loader serves the honest-empty bundle; compose refuses `company_ref_unresolved` → private 404. Missing: private technology curation assertions + identity receipts for the cohort (producer: Theme Graph curation lane + identity owner). The v2 assertion-grained evidence selector itself is implemented and falsifier-covered; it serves nothing real until those inputs land |
| finance | registered — `sector_profile`, `finance_intelligence_research.v1` | **UNAVAILABLE** end-to-end | honest-empty bundle; compose refuses `sealed_input_unavailable:run_context` → private 404. Missing: an admitted `finance_run_context` native-ref producer + the private assertion half (producer: finance intelligence run-context writer + Theme Graph curation lane) |
| robotics | not registered (any `/research` request is the private 404 by law) | **UNAVAILABLE** | module is real and implements the honest-empty doctrine (`engine/market_ontology/robotics_owner_bundle.py`, `tests/test_market_ontology_robotics_theme_research.py`). Missing: private curation assertions + owned cohort (producer: Theme Graph curation lane) and transport registration once they exist |
| mining | not registered | **UNAVAILABLE** | real composer over the casebook with omissions machinery (`engine/market_ontology/mining_theme_research.py`, `tests/test_mining_composition*.py`, `tests/mining_casebook.py`). Missing for the transport: registration + the casebook's promoted real data (producer: mining casebook lane) |
| nuclear | no entry, deliberately | **UNAVAILABLE** | #9124 content is HOLD-FOR-SUCCESSOR-PROOF; the entry stays explicitly unavailable per charter (no synthetic substitute, no revival) |
| P&G | not registered | **UNAVAILABLE** | real surface is the Company Intelligence P&G profile (`engine/company_intelligence/pg_profile.py`, `pg_envelope.py`). Missing for the transport: registration + binding that profile's real inputs to a research composer (producer: Company Intelligence lane) |
| PLNT | not registered | **UNAVAILABLE** — public hold | the synthetic fixture card is held from the public carrier (`tests/test_consumer_cyclical_plnt_public_hold.py`); native staging is out of scope per charter and is not retried here (producer: the hold's owner) |
| healthcare | not registered | **UNAVAILABLE** | real surface is W0b dispersion infrastructure — sector-holdings archiver + EW sector ETF tickers (`tests/test_healthcare_dispersion_w0b.py`) plus FDA-details/molecule-gap suites. Missing: a research composer binding those real inputs + registration (producer: W0b dispersion lane) |
| industrials | not registered | **UNAVAILABLE** | real surfaces: `engine/fundamental_forensics/industrials_result_cash.py` and the shared financial dossier (`tests/test_industrials_financial_dossier.py`). Missing: registration + a composer binding (producer: fundamental-forensics / Company Intelligence lanes) |

No row above substitutes generic or synthetic narrative for a missing input;
the three registered entries are the only ones addressable on this transport,
and two of them honestly refuse rather than serve composed placeholders.

## 8. Where the law lives

- Discriminators, entry-kind union, context fingerprint:
  `engine/market_ontology/theme_research_binding.py`
- Closed registries (theme anchors + profile ids) and the v2 registration
  columns (`subject_field`, `time_modes`, `single_document`,
  `native_generation_prefix`/`width`/`field`, `evidence_refs_field`):
  `engine/market_ontology/theme_research_registry.py`
- The transport union (parse, resolve, pairing, grammars, 409 law, refusal
  mapping): `app/theme_research.py` (no vertical named, no regex, no second
  rights opinion)
- Technology adapter (native `tecd_`, v2 evidence selection):
  `engine/market_ontology/technology_research_registration.py` +
  `contracts/market_ontology/technology_economic_change.evidence.v2.schema.json`
- Finance adapter (sector_profile, gen_ native, v1 evidence):
  `engine/sector_intelligence/finance_research_registration.py`
- Falsifiers: `tests/test_theme_research_api.py` §14 (wire),
  `tests/test_market_ontology_technology_research_registration.py`
  (selection law), `tests/test_theme_research_registry.py` (registry),
  `tests/test_finance_research_registration.py` (finance loader/facts).
