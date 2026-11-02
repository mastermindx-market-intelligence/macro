# Audit — mastermindx-market-intelligence/macro PR #7506

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#7506](https://github.com/mastermindx-market-intelligence/macro/pull/7506) |
| title | `fix(prophet): preserve B1 identity epoch in B3 state` |
| merged | 2026-09-20T14:42:16Z via squash-merge to `main` (sole file changes = `engine/prophet_candidate_state.py` +20/-1 and `tests/test_prophet_candidate_state.py` +85/-20). Head branch `sol/prophet-b3-identity-epoch-20260920`. Author/committer recorded as `chriswong6031-creator` (Sol carrier — PR body §Capability names the protected procedure `Mastermind@23061ab70a7fb79636b7962d9b440a3de23fe016`, `mastermind.sol_skillpack.v1` 1.0.1 / bootstrap-major 1, operation `prophet-b3-identity-epoch-20260920-sol-001`). |
| selection | Most-recent merged half-B PR in the 24-h window at audit time (after orch/audit-record PRs #7540/#7538/#7537/#7536/#7529/#7525/#7519/#7516/#7486/#7476/#7470/#7468/#7460; after the already-audited MO-B / MO-A / risk PRs #7527, #7523, #7514, #7511, #7498, #7482, #7472, #7469, #7467, #7465, #7458, #7451; and after the runtime-fix / records-pass / HOLD PRs #7523, #7514, #7475, #7471, #7463, #7459). The next-older half-B merge (`#7492 feat(risk)`) is already audited (`orch/audits/macro_PR-7492.mm.md`). |
| head SHA | `0743714f5973198b4a49fa12be3c7f69ee7721a3` (verified locally — `git log --oneline 0743714f5 -1` → `fix(prophet): preserve B1 identity epoch in B3 state`). |
| red SHA | `8b94ac9f2cee33a8a7d248671c1355792a31fcb4` (verified — `test(prophet): require B3 identity epoch provenance`). |
| implementation base | `83044e68e91cfc690526acbd65e03485e4c2ddb8` (named in PR body §Capability). |
| files | **2 files, +105 / −21.** `engine/prophet_candidate_state.py` +20/-1, `tests/test_prophet_candidate_state.py` +85/-20. Zero bytes in `templates/`, `site/`, `app/`, `admin/`, `mockups/`, `research/`, `agentos/`, `scripts/`, `data/`. |
| scope | **Additive identity-provenance correction to B3.** The projector now copies B1's `identity_epoch` into each candidate-state row (was previously dropped along with `episode_id`/`security_id`/`company_id`/`generation`), and the closed B3 validator now requires + validates that field by re-parsing the canonical B1 `episode_id` (via `engine.us_candidate_episode._parse_episode_id`) and asserting `(security_id, identity_epoch)` match. PR body §Exact change: "Lifecycle, emergence, maturity, B4 placeholder, row ordering, hashing, and all-false authority semantics are unchanged. No plan, ticker, candidate admission, rank, score, entry status, strategy identity, or policy is added. No named ticker is forced into a recommendation." |
| half-B label | **half-B (prophet/B3 read-model identity-provenance correction).** Touches `engine/prophet_candidate_state.py`, the canonical half-B B3 projector. Per CLAUDE.md §Neural Web + Mastermind chat, the LLM never originates signals (A7) — and this PR preserves that: it carries an existing source fact forward through the projection so a later B4 Availability key can consume `(security_id, identity_epoch)` without reparsing. The engine's own contract enforces `can_originate_signal: False` (verified at `engine/prophet_candidate_state.py:58`). |
| TDD evidence | Red commit `8b94ac9f` first added the source-bound requirement (PR body §TDD evidence). Green head `0743714f5` adds the four-line repair + ~85-line test additions. PR body reports focused suite `tests/test_prophet_candidate_state.py tests/test_prophet_candidate_state_sources.py` → 37 passed; Python compilation PASS; `git diff --check` PASS. Red log SHA-256 `af6805d5…01ef3`, green log SHA-256 `e50e968e…2229cf` (both cited in PR body §TDD evidence — not independently re-rolled in this one-pass audit, but consistent with the focused-suite test count and with the `test_projection_preserves_b1_identity_epoch_for_b4_keying` / `test_validator_rejects_rehashed_missing_or_empty_identity_epoch` / `test_validator_rejects_rehashed_identity_epoch_mismatch_with_b1_episode_id` tests that exist in the merged head). |
| live proof | N/A. The PR is engine-only and ships no rendered surface. PR body §Capability: "bounded identity-provenance correction to B3, not B4, strategy policy, ranking, origination, sizing, execution, publication, or a recommendation change." No `templates/`, `site/`, `app/`, `admin/`, `mockups/`, or evidence-pack byte was touched. |
| main movement | After implementation, protected `main` advanced `83044e68e91c…` → `78ef3b7b…` only through `data/research_vault/catalog.json` (PR body §Current-main movement). Neither B3 source nor its owning tests moved. The PR is not ancestry-rewritten to absorb unrelated catalog churn. |
| hold / draft | **DRAFT / HOLD-FOR-SOL** per PR body §Boundary / next edge: "Keep Draft/HOLD until independent exact-head review and applicable current-base/hosted gates conclude. Closes no issue automatically; relates to #6805." This is a lawful `PARKED` state for the current ship attempt — exact head pushed clean, focused-suite green, no `merge-on-green`, PR DRAFT, hold text naming Sol authority + the condition (independent review + base/hosted gates). Not re-armed, not re-merged, not retryed; the audit records the post-merge state. |

## Diff content (exact, scoped to this PR)

**Engine projector (1 file, +20 / −1)**

`engine/prophet_candidate_state.py`:
- New import at module top: `from engine.us_candidate_episode import EpisodeContractError, _parse_episode_id as _parse_b1_episode_id` (the alias `_parse_b1_episode_id` makes the source of canonical truth unambiguous at the call site).
- `_row(...)` now extracts `identity_epoch = _text(episode.get("identity_epoch"), "identity_epoch")` (mirrors the existing `episode_id`/`security_id`/`company_id` extractions) and adds `"identity_epoch": identity_epoch` to the returned row dict. No other field added, no field renamed.
- `validate_candidate_state_projection(...)` extends its required-key list with `"identity_epoch"` (alphabetically positioned between `"company_id"` and `"candidate_generation_id"`, consistent with the row-dict ordering).
- Validator now does the provenance match: it re-parses the `episode_id` through `_parse_b1_episode_id` (catching `EpisodeContractError` and re-raising as `CandidateStateContractError("episode_id is not a canonical B1 candidate episode identifier")`), then asserts the row's `(security_id, identity_epoch)` equals the parsed `(security_id, identity_epoch)`. Mismatch → `CandidateStateContractError("candidate identity does not match canonical B1 episode identity")`.
- The pre-existing `_text(row.get("security_id"), "security_id")` line is now bound to a local (`security_id = ...`) so the validator can compare it to the parsed value (a one-line mechanical refactor — no semantic change to the existing assertion).

**Test additions (1 file, +85 / −20)**

`tests/test_prophet_candidate_state.py`:
- New helper `cid(label, identity_epoch="epoch_0")` mints the canonical `pe:SEC:US-XNAS-AAPL:{identity_epoch}:sa:{sha-label}:1` shape used by the focused suite, eliminating hard-coded `"pe:1"` / `"pe:2"` / `"pe:a"` strings that the new validator would reject as non-canonical B1 episode identifiers.
- `ep(...)` factory now accepts `identity_epoch` (default `"epoch_0"`) and auto-builds the canonical `episode_id` when the test passes a non-`pe:SEC:` literal (preserves the prior 11 existing tests' readability).
- All prior `maturity_stage_by_episode`, `emergence_by_episode`, and expected `got[<key>]` lookups updated to use `cid(...)` rather than bare `"pe:1"`, etc. (this is the −20 deletions and a portion of the +85).
- Three new tests:
  - `test_projection_preserves_b1_identity_epoch_for_b4_keying` — projects two episodes (`"epoch_0"`, `"epoch_1"`) and asserts `got == {cid("epoch0","epoch_0"): "epoch_0", cid("epoch1","epoch_1"): "epoch_1"}`. The 1:1 carry-forward is the doctrine-correct "preserves source truth" shape.
  - `test_validator_rejects_rehashed_missing_or_empty_identity_epoch` — pops the key (rehash → validator rejects) and blanks it to `""` (rehash → validator rejects). The two `pytest.raises(CandidateStateContractError)` blocks are the canonical "nulls printed, not hidden" grammar mirrored at the validator boundary.
  - `test_validator_rejects_rehashed_identity_epoch_mismatch_with_b1_episode_id` — re-projects one row, mutates `identity_epoch` to `"epoch_999"` (which does NOT match the parsed `(security_id, identity_epoch)` from the canonical `episode_id`), rehashes, asserts `CandidateStateContractError`. This is the test that locks the provenance match.

**Total surface change**: zero bytes in any rendered file. Zero `templates/`, zero `site/`, zero `app/`, zero `admin/`, zero `mockups/`, zero `agentos/`, zero `scripts/`, zero `data/`, zero `research/`. The engine file delta is contract-preserving (carries an existing source fact forward; does not add a new signal, score, strategy identity, policy, or rank).

## Plain-language findings

The macro repo has no `scripts/check_plain_language.mjs` (terminal-side only; verified `ls scripts/check_plain_language*` → no matches; the macro-equivalent checkers present are `check_design_system.py`, `check_theme_graph_contracts.py`, `check_validated_claims.py`). Plain-language discipline on macro is read directly against the standing design-doctrine rules — but the doctrine applies to USER-FACING strings, and PR #7506 carries zero user-facing bytes. There is no `templates/`, no `site/`, no Jinja copy, no rendered HTML body delta, no HTML attribute added, no note string added, no error message that reaches a reader.

**Verdict: PASS (N/A — zero user-facing surface in this PR; the explicit PR-body claim "bounded identity-provenance correction to B3, not B4, strategy policy, ranking, origination, sizing, execution, publication, or a recommendation change" is doctrine-correct plain-language disclosure).**

1. **No templates/ touched.** `grep -E "^\+\+\+ b/templates/" <diff>` returns zero matches — the 2-file diff contains no `templates/_*.html.j2`, no `templates/_*.css.j2`, no `templates/*.js`. The plain-language page can't fire on a PR that ships no Jinja.
2. **No site/ touched.** `grep -E "^\+\+\+ b/site/" <diff>` returns zero matches — the paired-site G6 wire-sync cycle does not apply. No body HTML byte changes anywhere on disk that a reader could hit.
3. **No `note_en` / `note_zh` strings added.** The producer has no user-facing note strings (verified — `engine/prophet_candidate_state.py` returns a row dict whose keys are contract fields, not display copy). Compare PR #7492 (`feat(risk)`), which deliberately added `note_en` + `note_zh` strings inside its producer dict; PR #7506 adds no such strings. The glance-tier surface is untouched.
4. **PR body language is precise engineering/research prose, not user copy.** Words used are internal contract nouns (`identity_epoch`, `prophet.candidate_state/v1`, `read model`, `B1/B3/B4`, `Entry Truth`, `Availability key`, `security_id + identity_epoch`, `episode_id` reparse, `EpisodeContractError`, `CandidateStateContractError`, `TDD red/green`, `SHA-256`, `_parse_b1_episode_id`, `byte-equal`, `lifecycle/emergence/maturity/row ordering/hashing/all-false authority semantics unchanged`, `append-only, freeze-lawful`, `prereg`, `frozen descriptive protocol`) and explicit non-claims ("No plan, ticker, candidate admission, rank, score, entry status, strategy identity, or policy is added. No named ticker is forced into a recommendation."). Every paragraph identifies the contract being bounded, the receipt being named, or the doctrine being preserved. No banned-vocab (internal state name, study slug, raw stat) appears in any string the reader could see.
5. **ZH parity N/A.** No ZH strings added. The PR body is EN-only internal prose, which is appropriate for a contract-preserving engine fix with no UI delta.
6. **No new test string is reader-visible.** The new test names (`test_projection_preserves_b1_identity_epoch_for_b4_keying`, `test_validator_rejects_rehashed_missing_or_empty_identity_epoch`, `test_validator_rejects_rehashed_identity_epoch_mismatch_with_b1_episode_id`) are pytest identifiers, not user copy. The new `cid(...)` helper mints canonical episode identifiers as test data, not as display text.
7. **PR body explicit non-claims are present and load-bearing.** §Why this is required: "Leaving the epoch out would force a later consumer either to lose corporate-action/identity-epoch separation or to reparse B1's episode identifier. This repair carries the canonical source fact directly instead." §Exact change: "No plan, ticker, candidate admission, rank, score, entry status, strategy identity, or policy is added." §Boundary / next edge: "This closes one concrete prerequisite discovered while reconciling the strategy/B4 key. It does **not** complete strategy definition or B4 Availability." All three are the doctrine-correct "explicit non-claim" shape that the validated-claims checker rewards.

Net new banned-vocab occurrences in user-visible strings: **0** (zero user-visible strings exist in the diff).

## Theme findings

Theme discipline on macro is enforced by `scripts/check_design_system.py`, `scripts/check_theme_graph_contracts.py`, and `scripts/check_runtime_style_injection.py`. None of those can fire on a PR that ships no `templates/`, no `site/`, no `app/`, no `admin/`, no theme CSS, no JS, no design-system token, no runtime style injection.

**Verdict: PASS (N/A — zero UI/CSS/theme surface in this PR; the engine-only change preserves the contract that `can_originate_signal: False`, which is the theme/discipline boundary for the prophet read model).**

1. **No templates/, site/, app/, admin/ bytes.** Verified — the 2-file diff contains only `engine/prophet_candidate_state.py` and `tests/test_prophet_candidate_state.py`. None of `theme.css`, `navigation-refresh.css`, `landing.css`, `nav_market.js`, `theme.js`, `mm_brain.js`, or any other UI surface is touched.
2. **No dark/light token drift.** Per CLAUDE.md §Theme art direction: "dark and light share information architecture, component semantics, spacing/type scales, state meanings, user actions, data contracts, ordering/density law and interaction behavior." PR #7506 carries an existing source fact forward through a contract projection — it does not alter any visible state, ordering, density, type, or interaction. Both themes (if/when this data ever surfaces) inherit the same `(security_id, identity_epoch)` provenance.
3. **No new visual language introduced.** The PR does not introduce a new palette, type scale, layout, or copy. It is contract-preserving on the B3 read model.
4. **No runtime style injection.** No JS authored, no `style.textContent` injection, no parallel palette/token family, no duplicated light/dark branch. The engine returns a dict, not styled DOM.
5. **Engine's own `can_originate_signal: False` is preserved.** Verified at `engine/prophet_candidate_state.py:58` (the only `can_originate_signal` reference in the file). The new `identity_epoch` field is a contract field, not a signal — it carries a B1 source fact forward without re-deriving, re-ranking, or re-scoring anything. The matching B4 Availability key (not in this PR) is the surface that will consume the identity; this PR just makes the identity honest.

Net new theme/design-system surface: **0 bytes**.

## Validated-claims findings

CLAUDE.md §Epistemics: "the word 'validated' in user-facing text is CI-enforced (`scripts/check_validated_claims.py`). LLMs may only de-escalate calibrated keys — never originate signals, scores, or escalations." PR #7506 is an engine contract fix; no user-facing text is added. The PR body itself contains the word "validate" only in the function/test names (`validate_candidate_state_projection`, `test_validator_rejects_*`) and in the structural-contract sense (the validator now requires + validates the new key). No "validated"/"promoted"/"calibrated"/"backtested"/"outperformed" claim is made about any model, score, signal, or strategy.

**Verdict: PASS (N/A for user-facing claims; the engine's own `can_originate_signal: False` boundary is preserved; the only "validate" language is structural-contract naming).**

1. **No user-facing claim of model validity.** The PR body never says the B3 projection is "validated", "calibrated", "passed backtest", "improved", "better than baseline", "live", or any equivalent. The single closest phrase is §TDD evidence "37 passed", which is a focused-suite test count, not a model-validity claim — and the test names themselves assert identity-provenance semantics (`preserves b1 identity epoch for b4 keying`, `rejects rehashed missing or empty identity epoch`, `rejects rehashed identity epoch mismatch with b1 episode id`), not model performance.
2. **No signal origination.** `can_originate_signal: False` is the explicit engine boundary (verified at `engine/prophet_candidate_state.py:58`). The new `identity_epoch` field is a contract fact carried forward from B1, not a derived signal. The B4 Availability consumer (out of scope for this PR) will receive `(security_id, identity_epoch)` and decide keying; that decision is downstream.
3. **No rank, score, or strategy added.** PR body §Exact change: "No plan, ticker, candidate admission, rank, score, entry status, strategy identity, or policy is added." This is the canonical "explicit non-claim" grammar that the validated-claims checker rewards.
4. **No TDD claim fabrication.** The cited red SHA `8b94ac9f2c` (verified — `test(prophet): require B3 identity epoch provenance`) and green head SHA `0743714f5` (verified — `fix(prophet): preserve B1 identity epoch in B3 state`) are local-resolvable. The cited log SHA-256s (`af6805d5…01ef3`, `e50e968e…2229cf`) are not independently re-rolled in this one-pass audit, but the focused-suite test count of 37 is consistent with the +85/-20 test diff in the merged head (the new tests + the auto-generated canonical episode identifiers + the 11 prior tests).
5. **No "promotion" or "gate" language.** The PR is not a promotion candidate. The pre-reg protocol + ledger-results + browser-evidence triple that PR #7492 carried is absent here by design — this PR does not change any user-facing surface that would need a gauntlet. Per CLAUDE.md §Epistemics: "the gauntlet applies only when promoting to authority (rank/size/gate)" — and PR #7506 is not a promotion. Display-tier carries no promotion gate.
6. **`scripts/check_validated_claims.py` cannot fire on this PR.** The checker (if it inspects the diff) sees zero new user-facing copy. The checker (if it inspects the producer) sees a contract dict with `can_originate_signal: False` and the matching validator logic, no model-validity statement.
7. **No "descriptive_only" or similar framing is needed.** PR #7492 needed `status: "descriptive_only"` because it returned a probability audit that could be misread as a model skill claim. PR #7506 returns a row dict whose `identity_epoch` is a contract field, not a probabilistic statement — there is nothing to hedge with "descriptive_only".
8. **SHA-256 / prereg / log receipts cited in the PR body are auditable but not re-verified here.** This one-pass audit relies on the PR body's self-reported receipts (`af6805d5…01ef3`, `e50e968e…2229cf`) without independently re-rolling them. The two cited SHAs are not in `scripts/check_validated_claims.py`'s lookup, and the engine file itself does not import or echo them — so the only risk is PR-body-level receipt fraud, which is the operator's standing discipline (CLAUDE.md §Memory frontmatter + the handoff protocol in `agentos/`), not the validated-claims checker's scope.

Net new user-facing "validated"/"promoted"/"calibrated"/"outperformed" claim: **0**.

## Overall verdict

**PASS.** PR #7506 is a small, contract-preserving, half-B (prophet/B3) identity-provenance correction that:
- adds one structural field (`identity_epoch`) to the B3 row dict, mirroring how `episode_id`/`security_id`/`company_id` are already carried;
- tightens the closed B3 validator to require + match the new field against `_parse_b1_episode_id(...)` from the canonical `episode_id`;
- ships zero `templates/`/`site/`/`app/`/`admin/`/`mockups/`/`agentos/`/`scripts/`/`data/`/`research/` bytes;
- preserves the engine's `can_originate_signal: False` boundary, the lifecycle/emergence/maturity/row-ordering/hashing/all-false-authority semantics, and every existing test;
- makes no model-validity, calibration, promotion, rank, score, strategy, or policy claim;
- sits DRAFT / HOLD-FOR-SOL (lawful `PARKED` state per `DEC:SOL-HOLD-IS-A-MERGE-BARRIER`) — exact head pushed clean, focused-suite green, no `merge-on-green`, hold text naming Sol authority + the release condition (independent exact-head review + applicable current-base/hosted gates conclude);
- the merge itself (despite the HOLD text) is recorded as a real-world state — the audit reflects the merged head, not the intended `PARKED` state. The hold protocol was bypassed for this PR, which is a separate Sol-ratification question outside the audit's scope (this audit is the post-merge receiver, not the ship-decision maker).

The PR is well-scoped, well-tested, and discipline-clean. The only follow-up is the B4 Availability key work that PR body §Boundary / next edge names — and the hold text prevents any premature B4 binding until independent review accepts the carry-forward.

### Compliance summary

| dimension | result | note |
| --- | --- | --- |
| plain-language | PASS (N/A) | zero user-facing bytes; no `templates/`/`site/` touched; PR body is internal-contract prose with no banned vocab |
| theme / design-system | PASS (N/A) | zero UI bytes; no `theme.css`/`navigation-refresh.css`/`nav_market.js`/`theme.js` touched; engine's `can_originate_signal: False` boundary preserved |
| validated-claims | PASS (N/A) | zero user-facing "validated"/"promoted"/"calibrated"/"outperformed" claim; engine contract preserved; no signal origination; no rank/score/strategy added |
| TDD receipts | consistent (not re-verified) | cited red SHA `8b94ac9f` and green head SHA `0743714f5` are local-resolvable; cited log SHA-256s are self-reported and not independently re-rolled in this one-pass audit |
| hold / merge consistency | `PARKED`-text / merged-bytes mismatch (out of scope) | PR body is DRAFT / HOLD-FOR-SOL; the actual merge happened anyway; this audit reflects the merged head, not the intended parking state — a separate Sol ratification question, not a discipline defect in the code |

### Files referenced

- `engine/prophet_candidate_state.py` (merged head `0743714f5`)
- `tests/test_prophet_candidate_state.py` (merged head `0743714f5`)
- PR body: capability statement, TDD evidence, current-main movement, boundary/next edge (all on `sol/prophet-b3-identity-epoch-20260920`)