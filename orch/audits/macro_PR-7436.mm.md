# Audit — mastermindx-market-intelligence/macro PR #7436

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#7436](https://github.com/mastermindx-market-intelligence/macro/pull/7436) |
| title | fix(flow-leaders): heal tracked strict-JSON artifact |
| branch head | `2e4067728e9b5e131fbcb1aa653ba97852db45f6` on `sol/heal-flow-leaders-artifact-json-20260919` |
| mergedAt | 2026-09-19T20:20:35Z |
| files | 1 changed (1 +, 1 −): `site/flowleaders/leaders.json` (single-line JSON, one-token edit) |
| merged-into tip | `d11573a3bc` (orch(audit) for PR #7411 — this PR landed earlier in the same window) |
| producer PR | #7391 ("fix(flow-leaders): publish browser-parseable strict JSON") merged 2026-09-19T10:20:59Z — already normalized `gamma_regime` and set `allow_nan=False` at the producer |
| follow-up context | the auto-render triggered by #7391 regenerated a strict artifact but failed post-bake on unrelated site-wide guards (dead HK link, pre-existing Market State coherence failure) before `site/` could be committed; this PR repairs the tracked artifact by hand so the Terminal board can recover without depending on that render |
| half-B label | "half-B" = MO-B / data-side half. The fix is a one-token JSON repair inside an already-tracked historical snapshot (`stale=true`, `session_date=2026-08-12`). It is not a UI/UX change, not a capture-evidence rotation, and not a re-shoot — strictly a parse-correctness repair |
| user-surface scope | NONE. `site/flowleaders/leaders.json` is consumed by the Terminal via `fetch(...).json()`; the PR is required precisely because browser `JSON.parse` rejects `NaN` tokens. No HTML, CSS, JS, template, i18n, or theme token touched |

The PR body is precise: "Make the tracked Flow Leaders artifact browser-parseable now" + "One bounded artifact repair only" + `stale=true` + `2026-08-12` snapshot. The diff is exactly the change the body claims (1 file, 2 tokens).

## Diff content (exact)

```
- "gamma_regime":NaN                          (board_a[43], 1 occurrence)
+ "gamma_regime":null                         (board_a[43], 1 occurrence)
```

Other field frequencies in the artifact (post-change):
- `"gamma_regime":"long"` — 238
- `"gamma_regime":"short"` — 64
- `"gamma_regime":null` — 1 (the repaired row)
- `NaN` tokens total — 0
- `Infinity` tokens total — 0
- `"NaN"`/`"Infinity"` string leakage — 0

JSON parses with `python -c "import json; json.load(open('site/flowleaders/leaders.json'))"` → exits 0. `node -e "JSON.parse(require('fs').readFileSync('site/flowleaders/leaders.json','utf8'))"` → exits 0. Schema still `flow_leaders.v1`; `as_of`, `session_date`, `stale`, `cold_start`, `direction_note`, `coverage`, every board row's score/rank/timestamp untouched.

## Plain-language findings

Macro has no `check_plain_language.mjs` equivalent — that gate is terminal-side. The macro-side nearest equivalent is the design-checker family and `check_validated_claims.py` (front-facing vocabulary). The plain-language lens reduces here to: did this PR introduce or expose any new user-visible raw slugs / untranslated strings / English-only leaks?

**Verdict: PASS (N/A — no user-visible strings touched).**

PR footprint = 1 file, all under `site/flowleaders/leaders.json`:

- The file is a single-line JSON data artifact (366 kB on disk). It is fetched by the Terminal board client; the JS runtime never renders its text on a Macro Dashboard surface.
- The only text-bearing field in the artifact that humans might see in a DevTools/network tab is `direction_note`: *"Net premium direction is ~-soft (approximate) for all sources until multi-session tape calibration extension passes (FL-R3). Magnitude leads direction."* This string is **unchanged** in this PR — the diff is one byte of a value (`NaN` → `null`) in `board_a[43].gamma_regime`, well away from `direction_note`.
- `stale=true` and `session_date=2026-08-12` correctly label this snapshot as historical — no plain-language debt from a stale label.
- No new English strings, no ZH strings, no i18n keys, no raw slug leaks.

Conclusion: this PR adds zero plain-language debt. The only user-observable change is that the Terminal board now successfully fetches and renders the same content it was already trying to render — the underlying JSON parse error is what prevented the board from appearing at all.

## Theme findings

TP-0 art-direction law in force: dark and light are two art directions, not one skin. The 8-cell evidence matrix is required for any user-facing material change.

**Verdict: N/A — no user-facing material change.**

PR footprint = 1 file, all under `site/flowleaders/leaders.json`:

- `site/flowleaders/leaders.json` is a JSON data artifact consumed by the Terminal, not a Macro Dashboard page. It contains no CSS, no theme tokens, no color values, no layout primitives, no DOM.
- No HTML, CSS, JSX, Jinja, palette, or token file touched. No evidence-matrix obligation arises (the 8-cell matrix applies to user-facing page captures, not to JSON data).
- Theme compliance is unchanged from the prior merged head.

Conclusion: theme law does not apply. There is no evidence matrix to ship and no cell to capture — the artifact is data, not art direction.

## Validated-claims findings

The standing law: the word "validated" and friends are CI-enforced via `scripts/check_validated_claims.py`; user-facing copy may not promote a context/data/detection/tagging artifact to authority unless it has cleared the gauntlet. The PR body and the artifact itself must not introduce a new "validated"/"certified"/"approved" framing.

**Verdict: PASS.**

- PR body wording: *"Make the tracked Flow Leaders artifact browser-parseable now"*, *"JavaScript strict JSON parse: PASS"*, *"the existing Terminal board can recover"*, *"historical snapshot"*. None of "validated", "certified", "approved", "promoted", "gauntleted" appears in the body. The PR is explicit about its non-claim: *"This does **not** repoint legacy Flow Leaders to ThetaData, alter its gates, or claim freshness."*
- Artifact wording: `direction_note` is unchanged and already disclaims ("~soft (approximate)", "until multi-session tape calibration extension passes (FL-R3)"). `stale=true` and `session_date=2026-08-12` are unchanged — the snapshot remains honestly labeled.
- Schema field `flow_leaders.v1` is unchanged.
- `gamma_regime` for the repaired row is `null` (not a numeric value or string label), which is the documented "missing" encoding per the producer fix in #7391. No new claim is encoded by the new value.

Conclusion: no validated-claim debt. The repair is an honest encoding of "missing" for one row, and the artifact's `stale=true` + `session_date` disclaim freshness explicitly.

## Overall verdict

**PASS.** PR #7436 is a minimal, well-scoped data integrity repair:

- One file, one token (`NaN` → `null`) in `board_a[43].gamma_regime`.
- Required by the Terminal's strict JSON parser (`JSON.parse` rejects `NaN`); the producer in #7391 already set `allow_nan=False` for future emissions.
- No UI surface, no CSS, no theme tokens, no i18n, no validated-claim language — plain-language, theme, and validated-claims laws do not apply to a JSON data artifact whose only user-visible effect is "the Terminal board now loads".
- PR body accurately describes the diff (1 file / 2 tokens), the boundary ("does **not** repoint legacy Flow Leaders to ThetaData, alter its gates, or claim freshness"), and the verification (strict parse PASS, zero `NaN`/`Infinity` tokens, schema unchanged, snapshot honestly labeled `stale=true` / `session_date=2026-08-12`).

No findings to flag. The PR is exactly what it says it is.