Audit complete. Final report:

---

# K1 Evidence Foundation + K3-E Opportunity Evidence Vector — read-only source audit

**Source pin (machine-verified):** `mastermindx-market-intelligence/macro` @ `1c85878983323f9ab38fff56a15771166d0f8aeb` ("docs(grey-deer)…#10231", 2026-10-30 22:50 -0700). Commit + all blobs present locally in `~/lanes/repos/macro`; every file read via `git -c remote.origin.promisor=false show <sha>:<path>` into an isolated scratch `/tmp/k1audit/tree` (no checkout touched, no network). Protected-procedure repo not needed by any inspected path and was not opened.

**Inspected:** `lib/evidence_foundation.py` (2002 L), `lib/opportunity_evidence.py` (1678 L), `lib/opportunity_case.py` (284 L); contracts `contracts/evidence_foundation/{reference,block,recipe}.v1.schema.json, vocabulary.v1.json, README.md`, `contracts/opportunity_evidence/{vector.v1.schema.json, slot_registry.v1.json}`; freezes `research/evidence_mesh/K1_…2026-08-23.md`, `research/opportunity_evidence/K3E_…2026-08-25.md`, `DEC-K3E-…md`; consumers `scripts/security_state_producer.py`, `engine/company_intelligence/{opportunity_context,opportunity_qualification}.py`, `engine/price_pressure/research.py`, `app/ontology_explorer.py`, plus consumer enumeration by pinned-tree grep (see F1).

## Actual test results (this session, not historical)

Isolated scratch tree at the pin; host python 3.12.3 / pytest 9.1.1 / jsonschema 4.26.0 / PyYAML 6.0.1 / jinja2 3.1.2. Command: `python3 -m pytest <suites> -q --basetemp=/tmp/k1audit/tpfinal -p no:cacheprovider` from the scratch root.

```
test_evidence_foundation_contract.py        96 pass / 1 env-fail
test_evidence_foundation_product_contract.py 34 pass
test_opportunity_evidence_vector_contract.py 128 pass / 1 env-fail
test_price_pressure_research.py              79 pass
test_earnings_opportunity_qualification.py   44 pass
test_earnings_opportunity_context.py         26 pass
test_security_state_contract.py              94 pass
test_security_state_view_model.py           102 pass
TOTAL: 604 passed, 2 failed, in 36.92s
```

The 2 fails are checkout-state guards, not code: `test_k1_changed_file_inventory_creates_no_physical_mesh_store` (shells `git diff origin/main...HEAD` in CWD) and `test_no_opportunity_store_paths_are_tracked` (`git ls-files`). Their invariant was verified directly at the pin: `git ls-tree -r --name-only <sha>` contains **0** paths under `data/evidence_mesh|`, `data/evidence_foundation|`, `engine/evidence_mesh|`, `data/opportunity|`, `engine/opportunity|` (the working-tree/untracked dimension is inherently checkout-local and unproven).

## Decisive findings

**F1 — Real consumer paths are broader than the five named files.** Pinned-tree grep: (a) **live product route**: `app/ontology_explorer.py:393-430` `read_drl_research` = `capture_event` → `compose_captured_evidence` → `compose_case` behind authenticated `/api/ontology/explorer/research/v1` (fail-closed 503, no remembered answer); (b) **per-cycle producer**: `scripts/security_state_producer.py:246-288` runs `compile_recipe` at the I/O boundary via `engine/security_state.py` `_build_k1_*` (tests 94+102 green); (c) **institutional research**: `lib/institutional_13f_adapter.py:465,527` `validate_reference`, `lib/institutional_intelligence.py:949` + own `compile_recipe` :1653; (d) **research-only earnings K5**: `engine/company_intelligence/opportunity_context.py` consumed by `engine/entry_radar/earnings_context.py:11`, output explicitly `live_projection_eligible: false`; (e) quality-gate `engine/company_intelligence/pb_d_quality.py:322`; (f) convention-only users (hash + `ALL_FALSE_AUTHORITY` only): prophet_bridge, options_structure/payoff, quote_context, candidate_provenance, live_eval, research_generation, sec13d_research. `engine/chronicle/market_feed_alias.py:479` explicitly refuses to be a K1 EvidenceRef.

**F2 — Multi-owner case composition is dead in v1 by design, and the blocker is upstream of the case code.** `vocabulary.v1.json` registers 15 owner stores; **none admits `security_id`/`listing_key`/`issuer_id` subjects** (subjects are cik, theme_node, fif_*, drl_event_key, etc.), and `test_dataos_security_master_is_deferred_without_a_native_row_reader` freezes that deferral. `compile_recipe` (`lib/evidence_foundation.py:1786-1804`) requires every reference subject to equal the canonical subject; identity-join declarations are non-proofs (`:1645-1666`). So `compose_case`'s `exact_subject` branch (`lib/opportunity_case.py:188-196`) can never join: the AAPL golden is REFUSED `identity_unresolved`, 0/4 included (fixture `aapl_security_state_recipe_valid.json`). Only two single-owner native bindings work: DRL captured event (`_captured_drl_identity`) and earnings workspace context (`_earnings_context_identity`).

**F3 — Unexpected defect (reproducible falsifier): `validate_vector` breaches its documented never-raises contract.** Module contract (`lib/opportunity_evidence.py:60-63`): "Never raised by validate_vector — that function always returns findings instead of raising." Falsifier: compose a vector with an included slot, set `slot["known_at"]["value"]="2026-01-01T08:00:00"` (no offset) while `asof["value"]="2026-01-02T09:00:00Z"`, re-hash `content_sha256`, call `validate_vector` → `TypeError: can't compare offset-naive and offset-aware datetimes`. Root: `_compare_known_at_to_asof` :778-780 compares parsed instants unguarded; call sites `_check_lookahead` :955 and `_check_clocks` :756-757 (`(value or "")[:10]` on non-string → `'int' object is not subscriptable`, second falsifier) have no guard, while `_check_captured_drl` :707-712 **does** guard its identical call — inconsistent application of the repo's own discipline (cf. red-team MAJOR 6 language at :846-847). Impact bounded: production producers emit Z-suffixed aware clocks, and `opportunity_case.compose_case:163` catches TypeError → `case_input_shape_invalid`; the crash surfaces only for direct `validate_vector` callers and as an opaque 503 via `app/ontology_explorer.py:427-429`. Related minor: `compose_vector` raises raw `TypeError` (not `OpportunityEvidenceError`) on non-string clock values via `_derive_inclusion` :1374 — contract drift only.

**F4 — PIT clock behavior is real and layered.** K1: per-owner clock bindings, replay cutoffs parsed even when unused, cross-grain same-day ordering returns ambiguous→refusal (`_beyond_cutoff`, :678-697); DRL capture hard-pins retrospective replay + digest binding (:866-891). K3-E: asof/known_at per-registry pins, lookahead and same-day mixed-grain exclusion (`R007`), I7 always `ex_post_excluded`, live-t0 lag budgets (`R021`), generation clock can't precede evidence (MAJOR-4 default, :1645-1658). Case: cutoff sweep over all known reference clocks (`lib/opportunity_case.py:168-175`). All covered by passing suites.

**F5 — Correction/withdrawal is contract-complete but consumer-inert.** Five kinds, append-only, relation targets must exactly equal predecessors (:963-995), block-level corrected refs force a new block id + `recompiled` lineage receipt (:1470-1483). No store exists, so no consumer walks a correction chain; `compose_case` admits a corrected receipt via `{"complete","partial","corrected"}` and reflects it only as receipts/dominant_degradation. Withdrawal excludes; it never deletes.

**F6 — Rights ceiling is "unknown" everywhere; that is honest, and it caps usefulness.** K1 `rights:{state:unknown}` is the only value any of these producers can assert (both producers hard-code it); `rights_blocked` refuses required blocks and excludes otherwise; the DRL capture must carry unqualified rights/freshness (:874-877). The earnings path states it outright: `whole_workspace_rights: "unknown"`, `publication_permission: "not_asserted"` (`opportunity_qualification.py:264-266`). Nothing in the stack resolves a rights owner or grant — so no case can ever claim a rights-clean fact in v1.

**F7 — Missingness and authority fences hold.** `zero_substituted` must be false; absent-without-reason and present-with-reason both flagged (:997-1006); adverse-state slots can't carry values (`K3E_R005`); `complete` is illegal while any adverse count is non-zero; dominant degradation order frozen (composer+validator share it, `R015` recomputes every denominator including the fixed 7-leg I1..I7 set, BLOCKER-2 fence :1227-1237). All-false authority is literal-equality enforced at every layer (K1 `authority_leak` :1087, K3E envelope, case `authority`). The red-team repairs cited in comments (MINOR 10 newline `$`, R-2 intraday lookahead, R-3 relative tolerance, R-5 entry-leg states, R-7 modeled legs, BLOCKER-1 owner-pin equality) are all present and tested.

**F8 — Verdict: "K1 and K3-E contract-complete, broad product integration partial" is correct, with one refinement.** K1 is not merely contract-complete: it has two real per-cycle product integrations (security_state producer bundle; 13F institutional research context) plus a quality gate. K3-E has one live read-only product route (DRL research) and one research-only producer (earnings context, `live_projection_eligible:false`). What is genuinely partial is *cross-owner opportunity integration*: v1 structurally refuses it (F2), and the K5 stack currently proves only single-native-event context. Drift note: the K3-E freeze header still says "NO CONSUMER ARMED" (2026-08-25) — stale relative to the pinned code, where `/research/v1` is armed.

## Material gaps (not defects)

- **Validation cost**: every `validate_reference`/`validate_block` re-reads schema+vocabulary from disk (`_contract_schema_violations` caches only meta-schema success, :1093-1101); README documents p50 ≈164 ms per fixture composition. Fine for current call sites; would not scale to per-row validation.
- **Engine-internal coupling in K1**: `lib/evidence_foundation.py:634-645` imports private `engine.company_intelligence.event_workspace._EVENT_ID_RE` and slices `event_id[7:17]` for CIK parity — works at the pin (`^evt_cik\d{10}_\d{4}(?:q[1-4]|fy)_[a-z0-9]+$`), but is a silent-failure drift hazard (import failure degrades to `subject_native_identity_mismatch`, not a typed error).
- The in-module K3-E schema checker implements no `propertyNames`/`format`; mitigated at t0 only (`_check_t0_authentication`) — currently not exploitable at the pin.

## Suggested first vertical

Smallest useful vertical: **harden the two unguarded PIT call sites** (`_check_lookahead` :955, `_check_clocks` :756-757) to return typed findings instead of raising — restores the documented never-raises contract that MAJOR 6 promised, and converts the ontology route's opaque 503 into a typed refusal. The next real integration vertical (multi-owner case) requires v2 work per the frozen law: either a registered DataOS security-master owner store admitting `security_id` subjects with a native row reader, or a validated bridge-object slot in `compile_recipe` — neither exists at the pin.

## Explicitly not proven

- No runtime/production behavior: no logs, no live route execution, no site/data builds, no live capture; static code + fixture tests only.
- CI greenness at the pin; the two checkout-state tests' working-tree/untracked dimensions; performance beyond the README's fixture measurement.
- Whether the two production producers' *upstream* native reads are authentic (validators prove contract consistency, not authenticity — the code says so itself).
- The Mastermind protected-procedure side: not read; no assertion made.
- Disclosure: an initial `cat-file -t` probe against the *other* checkout `~/Documents/GitHub/macro` triggered its background `git gc --auto` (PID 2465342, local packing only, no `git-remote-http`, i.e. no network dial). I left it to finish rather than kill mid-repack; no other write touched any checkout. No child dispatch; this read-only task ends with this report.
