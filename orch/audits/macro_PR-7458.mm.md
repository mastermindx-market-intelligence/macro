# Audit — mastermindx-market-intelligence/macro PR #7458

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#7458](https://github.com/mastermindx-market-intelligence/macro/pull/7458) |
| title | `fix(theme-graph): preserve parquet evidence refs on PIT cutover` |
| merged | 2026-09-20T00:34:00Z (24-h window: 2026-09-19 00:34 UTC → now) |
| head | `6ccde65a637cd7550b580881187fdab403d935cf` on `origin/main`; base `ef5fb6bd57` |
| files | 2 changed (+11 / −2): `engine/theme_graph/materialize.py` (+9/−2), `tests/test_theme_graph_materialize.py` (+2/−0) |
| half-B label | **half-B (MO-B / theme-graph data integrity).** Title carries the canonical `[theme-graph]` scope tag and the body cites the parent operation `gmi-theme-pit-d2c-20260827-sol-001` (merged #6809). This is a child of the Mastermind-Option-B GMI D2C PIT-cutover program and the third follow-up repair to the THS PIT replay (after #7459 and #7456). |
| owner | Meta-CEO B seat (`gmi-d2c-postmerge-evidence-ref-repair-20260919-sol-001` operation; protected procedure anchored at `Mastermind@9e796168b467c17d9853f139c4e4a6ccdf3a3a87`). |
| user-surface scope | NONE. The change is internal to `engine/theme_graph/materialize.py::_normalize_evidence_refs` — a pure normalization helper that converts parquet-backed evidence IDs back to flat string lists. No HTML, CSS, JSX, Jinja, i18n, palette, token, or template file touched. |
| body claims | "Repair the post-merge GMI D2C cutover so parquet-backed `evidence_refs` remain flat evidence IDs instead of becoming one stringified NumPy array. This preserves the existing append-only Theme Graph and makes the real PIT cutover pass the strict evidence-integrity contract." Names parent op, names root cause (`store.read_edges()` returns parquet list columns as NumPy arrays; `_normalize_evidence_refs()` handled strings/lists/tuples but not array-like values), names the exact bug shape (`["['ev:a8cd…' 'ev:71d2…']"]` instead of `["ev:a8cd…", "ev:71d2…"]`), and pins the blast radius ("exactly two paths change"). |
| proof block | RED exact regression **1 failed as intended** (SHA-256 `439668b0…`); GREEN focused **1 passed** (SHA-256 `a9d8d2a0…`); owning battery **247 passed** + contract self-test OK (SHA-256 `f8eef89d…`); committed inputs 57,010 PIT rows / 237 baskets / 4,715 tickers; natural run 1 → 9,814 edges / 2 evidence rows appended, exit 0; natural run 2 → 0 / 0, exit 0; `check_theme_graph_contracts.py --strict` exit 0 after both runs. The body also discloses the sidecar caveat: "Capability and identity-resolution sidecars intentionally append fresh derivations each run; the no-op claim is limited to graph edges and evidence." |

The diff is exactly what the body claims: 2 files, 9 + 2 = 11 added lines, 2 deleted lines. No drive-by edits. No silent scope expansion.

## Diff content (exact)

**`engine/theme_graph/materialize.py` (+9 / −2)**

```diff
 def _normalize_evidence_refs(value: object) -> list[str]:
     if _null(value):
         return []
     if isinstance(value, str):
         try:
             parsed = json.loads(value)
         except (TypeError, ValueError):
             return [value] if value.strip() else []
         value = parsed
+    to_list = getattr(value, "tolist", None)
+    if callable(to_list):
+        value = to_list()
     if isinstance(value, (list, tuple)):
-        return [str(x) for x in value]
-    return [str(value)]
+        out: list[str] = []
+        for item in value:
+            out.extend(_normalize_evidence_refs(item))
+        return out
+    text = str(value).strip()
+    return [text] if text else []
```

Three behaviours in one minimal patch, each load-bearing for the regression:

1. **Array-like passthrough.** When `value` carries a `.tolist` callable (NumPy array, pandas Series of object dtype), invoke it before the list/tuple branch. This is the root-cause fix — `store.read_edges()` returns parquet list columns as NumPy arrays, and the previous function stringified them via `str(value)`, producing the `["['ev:a8cd…' 'ev:71d2…']"]` regression the body documents.
2. **Recursive flatten for nested containers.** The new branch iterates and re-enters `_normalize_evidence_refs(item)` per element. This catches edge cases where a parquet row holds `[["ev:a", "ev:b"], "ev:c"]` (list-of-lists) and prevents the same string-of-array failure at any depth.
3. **Scalar fallback hardened.** The scalar branch now strips whitespace and returns `[]` for an empty string instead of `[""]` (the prior code's `return [str(value)]`). Empty-string scalars used to leak into `evidence_refs` as one-element lists containing the empty string, which downstream integrity checks treated as a fabricated ID.

**`tests/test_theme_graph_materialize.py` (+2 / −0)**

```diff
     assert {c["edge_id"] for c in closings} == {e["edge_id"] for e in prior}
     assert all(c["valid_to"] == pit_birth for c in closings)
+    assert all(c["evidence_refs"] == ["ev:deadbeefdeadbeef"] for c in closings), (
+        "parquet-backed evidence refs must stay flat identifiers, never one stringified array")
```

This is the exact regression the body claims: a closed-cutover assertion on every closing row's `evidence_refs`, using the literal string `"ev:deadbeefdeadbeef"` (the same fixture token the test already used elsewhere in the function — no new fixture introduced). The assertion message is human-readable and points to the failure mode (`"never one stringified array"`) so a future regression prints the exact intent of the test.

## Plain-language findings

The macro repo has no `scripts/check_plain_language.mjs` (terminal-side only). The plain-language lens here is read against the standing design-doctrine rules (no internal-state names; no raw slugs; no untranslated strings; per-signal "so what do I do"; honest-null grammar; glance-tier word budgets).

**Verdict: PASS (N/A — no user-facing strings touched).**

The PR is purely a backend normalization fix in `engine/theme_graph/materialize.py` plus a test addition. Footprint = 2 files, all under `engine/` and `tests/`:

- The diff introduces no Jinja templates, no HTML, no CSS, no JSX, no i18n keys, no English strings, no ZH strings.
- The only user-observable consequence is that the Theme Graph's `evidence_refs` column on cutover closing rows now contains real evidence IDs (`["ev:a8cd…", "ev:71d2…"]`) instead of one stringified NumPy array (`["['ev:a8cd…' 'ev:71d2…']"]`). The stringified-array form was a corruption — never rendered to users, but it caused 3,532 dangling evidence references under `check_theme_graph_contracts.py --strict` against the 57,010-row THS PIT replay. The user-visible effect of the fix is the integrity contract now passes; no new copy is exposed.
- The added test assertion message ("parquet-backed evidence refs must stay flat identifiers, never one stringified array") is an internal developer comment, not a user-facing string — it lives in test code and only surfaces in pytest output if the regression returns.
- No `t('...', '...')` blocks added. No new title-attribute text. No ZH/EN parity obligation triggered (no translated strings introduced).
- No raw slugs / untranslated strings. The literal `"ev:deadbeefdeadbeef"` in the test is a fixture-only token matching an existing fixture row, not user copy.

The PR adds zero plain-language debt. The fix is invisible to the user unless they previously saw a strict-contract failure — and the body documents that failure as a developer-facing diagnostic, never as a user-facing message.

## Theme findings

TP-0 art-direction law in force (operator 2026-08-27): dark and light are TWO art directions, not one skin; the 8-cell evidence matrix (dark × light × EN × ZH × desktop 1440 × mobile 390) is required for any user-facing material change.

**Verdict: N/A — no user-facing material change.**

- PR footprint = 2 files, both under `engine/theme_graph/` and `tests/`. The only file in the path that touches the word "theme" is `engine/theme_graph/materialize.py` — and "theme_graph" here is the name of the Neural Web lobe (the data-side theme taxonomy), not the visual theme system (`templates/theme.css`, `templates/theme.js`, `templates/navigation-refresh.css`).
- The fix is internal to a pure normalization helper. It returns a Python `list[str]` of evidence IDs; the IDs are opaque machine tokens (e.g. `ev:a8cd…`), not visual artefacts.
- No HTML, CSS, JSX, Jinja, palette, token, or template file touched. No DOM, no layout primitive, no color value, no typography, no motion introduced.
- No evidence-matrix obligation arises (the 8-cell matrix applies to user-facing page captures, not to backend normalization code).

Conclusion: theme law does not apply. The PR's "theme-graph" tag names the data structure being preserved, not a visual surface. The visual/theme compliance surface is unchanged from the prior merged head.

## Validated-claims findings

The standing law: `scripts/check_validated_claims.py` is CI-enforced; user-facing copy may not promote a context/data/detection/tagging artefact to authority unless it has cleared the gauntlet. The PR body and the modified code must not introduce a new "validated"/"certified"/"approved"/"gauntleted"/"promoted"/"proven" framing.

**Verdict: PASS.**

- **PR body wording scan.** Grep on the body for `validated | certified | approved | gauntleted | promoted | proven`: zero matches. The body uses "strict evidence-integrity contract" — this is an internal contract name (`check_theme_graph_contracts.py --strict`, the same gate the proof block runs), not a promotion claim. The body also writes "natural run 1", "natural run 2", "no-op claim is limited to graph edges and evidence" — these are operational labels for the proof, not authority claims.
- **Diff wording scan.** Grep on the diff for `validated | certified | approved | gauntleted | promoted | proven`: zero matches. The added test assertion message ("parquet-backed evidence refs must stay flat identifiers, never one stringified array") is a regression-prevention comment, not a promotion claim.
- **No gauntlet promotion attempted.** The PR explicitly limits its claim to a parser-shape repair (NumPy array → flat list of IDs). It does not promote any theme-graph edge, basket, ticker, or signal to authority. The fix restores the integrity contract that already exists; it does not create a new "validated edge" or "validated evidence ref" type. The 9,814 edges and 2 evidence rows appended in natural run 1 are recorded as **appended**, not **validated** — the body uses the operator-correct verb (a ledger append is a ledger append, not a gauntlet pass).
- **Strict-contract self-test.** The proof block runs `check_theme_graph_contracts.py --strict` after each natural run and reports exit 0. This is the existing integrity contract — the same gate that the previous merged head ran and the same gate whose failure (3,532 dangling refs) this PR fixes. The PR does not introduce a new contract; it makes an existing one pass on the real PIT replay.
- **No `check_validated_claims.py` impact.** The script scans `templates/`, `app/`, and a handful of other surfaces for the "validated" family. Neither file changed by this PR is in that scan path (`engine/theme_graph/materialize.py` is engine code; `tests/test_theme_graph_materialize.py` is test code). Running `python3 scripts/check_validated_claims.py --list` against the merged head would not surface this PR — its scope is not a validated-claim surface.

Conclusion: no validated-claim debt. The repair is a parser-shape fix; the proof is honest about its limits ("no-op claim is limited to graph edges and evidence"); the body and diff introduce zero new promotion language.

## Overall verdict

**PASS.** PR #7458 is a minimal, well-scoped engine data-integrity repair:

- 2 files, 11 lines added, 2 deleted. Exactly two paths change: `engine/theme_graph/materialize.py::_normalize_evidence_refs` (the fix) and `tests/test_theme_graph_materialize.py` (the regression). No drive-by edits, no silent scope expansion.
- Root cause is documented with a literal example (`["['ev:a8cd…' 'ev:71d2…']"]` vs `["ev:a8cd…", "ev:71d2…"]`) and the proof block shows the regression was RED-then-GREEN on the exact test that pins it.
- The fix is invisible to users unless they previously saw the strict-contract failure (3,532 dangling evidence references). No new user-facing text, no new theme surface, no new validated claim.
- The proof is honest about its limits: capability and identity-resolution sidecars intentionally append fresh derivations each run; the "no-op on run 2" claim is scoped to graph edges and evidence, not to those sidecars. The body and the SHA-256 receipts together make the boundary legible.
- Plain-language, theme, and validated-claims laws do not apply to a backend normalization helper whose only output is machine-readable evidence ID strings. The PR adds zero debt on any of the three dimensions audited.

No findings to flag. The PR is exactly what it says it is, and its scope is the smallest shape that closes the regression.
