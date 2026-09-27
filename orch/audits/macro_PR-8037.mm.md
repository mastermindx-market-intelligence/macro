# macro PR #8037 — plain-language / theme / validated-claims audit

**Recorded:** 2026-09-26 (REMOTE USEFUL-IDLE MODE — disk-only, no PR opened)
**Auditor seat:** `claude/idle-audit-pr-7835`

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#8037](https://github.com/mastermindx-market-intelligence/macro/pull/8037) |
| title | `feat(brain): route technician doctrine from chart context` |
| mergedAt | 2026-09-26T12:52:19Z |
| files | 2 (`engine/neuralweb/doctrine.py`, `tests/test_brain_doctrine.py`) |
| additions / deletions | +128 / −23 |
| exact head | `da8ccc2cd5ec37bc8426ba967b15afe9dfad579c` |
| base | `433a65cd364761a082fd94809b9e64682589f882` (branch creation main tip) |
| PR body label | `DRAFT / HOLD-FOR-SOL / BUILT_NOT_PROVEN` (body text states "Merge can be considered after exact-head CI; gateway integration is intentionally held until #7999/#8005/#8014 collapse onto main") |

**Surface summary:** engine-only change inside `engine/neuralweb/`. The diff adds an optional `context_terms` keyword parameter to `doctrine.Library.route()` and to the module-level `doctrine.route()` shim, then sorts scored modules by a 5-tuple `(user_match_flag, user_score, context_score, priority, id)`. Six new test cases pin the new behavior (context can route on generic/empty message; explicit user intent outranks context-only matches under the existing 3-module cap; context strings are not inserted into the assembled prompt; word-boundary matching is preserved; message-only call remains backward-compatible). No templates, no HTML, no JS, no CSS, no theme tokens, no copy shipped.

## Plain-language findings

**N/A by surface.** `check_plain_language.mjs` lives in the terminal repo and is keyed to rendered chart/UI string templates; the macro repo has no equivalent because macro has no user-visible text surface inside this PR's diff. Verified by inspection:

- `engine/neuralweb/doctrine.py` — Python module + new helper `_context_match_text()` (joins bounded trimmed terms, lowercases, returns a single string used only for `_trigger_matches()` scoring).
- `tests/test_brain_doctrine.py` — six new tests assert module-id membership and the absence of the literal marker `SECRET_CONTEXT_MARKER_DO_NOT_ECHO` inside the assembled prompt block.

The only literal strings introduced are:

1. Test fixture words: `"structure"`, `"trend"`, `"intraday"`, `"support"`, `"volume"`, `"stage"`, `"email"`, `"SECRET_CONTEXT_MARKER_DO_NOT_ECHO"`.
2. One sentence of updated docstring prose describing "user-language matches rank ahead of context-only matches" and "context terms ... never inserted into the assembled prompt".

None of these strings are user-visible copy. **0 blocking plain-language findings; 0 informational plain-language findings.**

## Theme findings

**N/A by surface.** Verified by `grep -nE "color|theme|#[0-9a-fA-F]{3,6}|--color-" engine/neuralweb/doctrine.py tests/test_brain_doctrine.py` → **0 hits**. The PR touches zero files under `templates/`, `site/`, `theme/`, `nav_market.js`, `theme.js`, `landing.css`, `*.css`, or any inline-style runtime injection site. There is no `palette` change, no `data-state-marker` change, no light/dark token substitution, no z-index / geometry change. The design-system runtime-style-injection check (`scripts/check_runtime_style_injection.py`) cannot fire on Python. **0 blocking theme findings; 0 informational theme findings.**

## Validated-claims findings

`scripts/check_validated_claims.py` is the macro gate that scans user-visible copy for CI-enforced banned language patterns. PR body re-checked against the gate's vocabulary list (`guaranteed`, `win rate`, `success rate`, `probability of`, `validated`, `certified`, `proven`, `accuracy`):

- **"DRAFT / HOLD-FOR-SOL / BUILT_NOT_PROVEN"** — appears in the PR body's "Non-claims" / status banner. The word `BUILT_NOT_PROVEN` deliberately *flags* the build as not yet proven; it is a non-claim, not a positive validated claim. The PR body also explicitly enumerates what it does NOT prove: "This PR does not yet wire chart-state terms into the gateway, install new indicator-specific doctrine, ingest Terminal guide documents, change any model/provider route, or prove improved technical-analysis accuracy." This is the compliant pattern.
- **`mtime-invalidated`** — appears in three docstrings (`doctrine.py` lines 16, 178, 204). This is the codebase's standing cache-coherence idiom (see `brain_gateway._load_brain_config` referenced in the same comment block); it describes the cache invalidation mechanism, not a user-facing claim. The CI gate's regex excludes this technical use.
- **`win rate` / `guaranteed` / `probability of`** — appear only in `tests/test_brain_doctrine.py:220` inside the `_BANNED = ("success rate", "win rate", "guaranteed", "probability of")` tuple and the assertion loop at line 247. These are the *banned-phrase linter itself* — i.e., the test asserts that the assistant text DOES NOT contain these phrases. CI-correct.

**0 blocking validated-claims findings; 0 informational validated-claims findings.**

## Overall verdict

**PASS on all three dimensions by construction.** PR #8037 is an internal-engine routing change to `engine/neuralweb/doctrine.py` plus its test companion. It introduces:

- zero new user-visible strings;
- zero new template / theme / CSS / inline-style surface;
- zero new "validated" / "proven" / accuracy claims in any user-facing copy;
- one explicit Non-claims paragraph that names exactly what the PR does not prove (gateway wiring, indicator-specific doctrine, Terminal guide ingest, model/provider routes, accuracy);
- one explicit `DRAFT / HOLD-FOR-SOL / BUILT_NOT_PROVEN` banner on the PR body — the compliant pattern for a built-but-not-yet-proven capability, especially one whose gateway integration is held until #7999/#8005/#8014 collapse onto main.

Plain-language, theme, and validated-claims laws are all not-applicable to this diff because the diff has no surface they govern. The only text added to the codebase is the updated `route()` docstring and the test strings noted above — both internal documentation and assertion fixtures.

**Recorded disk-only under REMOTE USEFUL-IDLE MODE; no PR opened. The audit report itself is the durable record; transport will persist stdout to the seat's `orch/idle/` directory.**
