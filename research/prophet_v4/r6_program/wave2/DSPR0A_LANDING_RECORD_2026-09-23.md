## SOURCE_SHA

1fc095fe9ab6a6958f2d57d482efb6df0c5d716b

## WHAT LANDED

- `templates/theme.css`: `--sp-1` through `--sp-8`, `--gap-grid`, `--r-ctl`, `--r-btn`, `--r-card`, `--r-panel`, `--r-pill`, `--t-fast`, `--t-med`, `--t-slow`, `--ease-std`, `--ease-lift`, `--shadow-hover`, `--ser-1` through `--ser-4`, and `--ink-tier`, with light overrides for the severity and tier-ink tokens.
- `templates/theme.css`: `.mx-vh`, `.mx-vh .mx-vh-word`, `.mx-vh .mx-vh-clause`, `.mx-vh .mx-vh-meta`, `.mx-sec`, `.mx-sec h3, .mx-sec h2`, `.mx-sec .mx-asof`, `.mx-tbl`, `.mx-tbl th`, `.mx-tbl td`, `.mx-tbl tr:hover td`, `.mx-tblbox`, `.mx-tabset`, `.mx-tabset button`, `.mx-tabset button[aria-selected="true"]`, `.mx-callout`, `.mx-callout b`, `.mx-callout--warn`, `.mx-callout--act`, `.mx-callout--ok`, `.mx-disc`, `.mx-disc summary`, `.mx-disc summary small`, `.mx-disc .mx-disc-body`, `.mx-rail`, `.mx-rail li`, `.mx-rail li::before`, `.mx-rail li::after`, `.mx-rail li.done::after`, `.mx-rail li.now`, `.mx-rail li.now::before`, and `.mx-rail li.now::after`.
- `templates/theme.css`: `--ink-prov: var(--prov-ink)` in dark and light while retaining `--prov-ink`.
- `templates/theme.css`: the zh estate rule for `h1`, `h2`, `h3`, `.eyebrow`, and `.mx-vh-word`.
- `templates/dashboard.html.j2`: renamed the page-local `--sp-8:32px` declaration to `--sp-7:32px` on the same line with the same value.
- `site/theme.css`: restored as the byte-identical paired copy of `templates/theme.css`.
- `mockups/design_system/specimen.html`: removed the ported DS-PR-0a token block and primitive rules and updated the header comment.

## DEFERRED TO DS-PR-0b

- The `html body` var() rebinds of the vector-polish block and component radii.
- The `.eyebrow` snap to `--fs-label`.
- The `_icons` stroke-1.8 reconciliation.
- Deleting the specimen duplicate copies of already-shipped rules.

## GATES

- `git diff origin/main...HEAD -- templates/theme.css templates/dashboard.html.j2 > /tmp/pr7849.diff` — prepared the PR diff before the gate.
- `python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7849.diff` — exit 0.
  - `::notice title=design-system::R0 enforce-added: 0 blocking finding(s) (25304 further pre-existing, non-blocking finding(s) in the estate — run --mode report for the full census)`
  - `design-system ratchet — mode=enforce-added blocking=0 (estate pre-existing, non-blocking: 25304)`
- Review repair on the previous head: the same `--diff-file` command exited 1 with seven `literal-custom-property` findings at `templates/dashboard.html.j2:1903` and one `radius-literal` finding at `templates/theme.css:2118`. Commit `bc3944fb90dcf5c749c841a67035119424b1827a` removes the page-local spacing declarations, which now inherit the promoted values from `theme.css`, and changes only the new unused rail dot’s radius from `50%` to the numerically identical `var(--r-pill)`.
- `python3 scripts/check_runtime_style_injection.py` — exit 0.
  - `runtime style injection guard OK (197 .js files scanned, 44 injecting, 89 total hits — all within frozen allowances)`
- `python -m scripts.check_template_site_sync --fix` — exit 0.
  - `template↔site sync OK (101 pairs checked)`
- `cmp templates/theme.css site/theme.css` — exit 0.
  - `templates/theme.css` byte size: `222988`.
- `python3 -m pytest tests/test_check_design_system.py tests/test_public_chrome.py -q` — exit 0.
  - `104 passed in 1.00s`

## COLLISION SCANS

- Existing-declaration guard: the specified command printed only `2057:   --r-ctl:8px, --r-card:12px), not an invented one. Both fallbacks go`, the comment the frozen spec explicitly identifies and says to leave. No declaration was duplicated or overwritten.
- Dashboard consumer count before the rename: `grep -c -E 'var\(--sp-8\)' templates/dashboard.html.j2` observed `0`.
- Class-collision scan: `git grep -n -E '\.mx-(vh|sec|tbl|tblbox|tabset|callout|disc|rail)\b' -- templates app site scripts | grep -v -E '^(templates|site)/theme\.css'` observed `0 lines`.
- Same-name page-local token scan observed these report-only hits:
  - `templates/dashboard.html.j2:1903:    --sp-1:4px; --sp-2:8px; --sp-3:12px; --sp-4:16px; --sp-5:20px; --sp-6:24px; --sp-7:32px;`
  - `templates/options.html.j2:91:  --r-pill:999px; --r-ctl:8px; --r-panel:14px; --r-shell:14px;`
  - `templates/seo_base.html.j2:121:  --sp-1:4px; --sp-2:8px; --sp-3:12px; --sp-4:16px; --sp-5:20px; --sp-6:24px; --sp-8:32px;`
  - `templates/tier_preview.css:11:  --ink-tier:var(--ink-link, var(--link));`
  - `templates/tier_preview.css:26:.mx-tier-gate--prophet{--mx-tier-accent:#7c5cff;--mx-tier-fill:#6340d8;--ink-tier:#9b86ff;`
  - `templates/tier_preview.css:28:html[data-theme="light"] .mx-tier-gate--prophet{--ink-tier:#5b3fc4}`

## ACCEPTANCE GREPS

| Grep | Expected | Observed |
|---|---:|---:|
| `grep -c -E '^\s*--sp-7:32px' templates/theme.css` | 1 | 1 |
| `grep -c -E '^\s*--r-ctl:8px;' templates/theme.css` | 1 | 1 |
| `grep -c -E '^\.mx-tbl\{' templates/theme.css` | 1 | 1 |
| `grep -c -E '^\s*--ink-prov:' templates/theme.css` | 2 | 2 |
| `grep -c -F 'PROPOSED — DS-PR-0' mockups/design_system/specimen.html` | 0 | 0 |
| `grep -c -E -- '--sp-8:32px' templates/dashboard.html.j2` | 0 | 0 |
| `grep -c -E -- '--sp-7:32px' templates/dashboard.html.j2` | 1 | 1 |
| `grep -c -E '^\.mx-(vh|sec|tbl|tblbox|tabset|callout|disc|rail)' mockups/design_system/specimen.html` | 0 | 0 |

## PIXEL-NEUTRALITY ARGUMENT

- No markup or script consumer of a newly ported `.mx-vh`, `.mx-sec`, `.mx-tbl`, `.mx-tblbox`, `.mx-tabset`, `.mx-callout`, `.mx-disc`, or `.mx-rail` selector exists outside `theme.css`; the class-collision scan returned 0 lines.
- The ported token declarations are additive at `:root`. A scan of added lines under `templates`, `app`, and `site` finds token consumers only inside the ported, zero-consumer `.mx-*` primitive rules; this PR adds no markup, script, or existing-rule consumer.
- The report-only token-declaration scan finds same-name declarations in local scopes, but this PR neither edits those scopes nor adds a consumer to them. Their declarations are out-shipped by specificity in their existing scopes and were not affected by this PR.
- The dashboard change removes its local `--sp-1` through `--sp-7` declarations and inherits the identically valued global scale (`4`, `8`, `12`, `16`, `20`, `24`, and `32` pixels). Its three existing consumers use `--sp-3`, `--sp-4`, and `--sp-5`, and `var(--sp-8)` had zero occurrences before the change; no consumer changed.
- The review repair changes only the new, zero-consumer `.mx-rail` dot radius from `50%` to `var(--r-pill)`, whose promoted value is exactly `999px`; for its fixed 8px square dot this remains a fully rounded circle.
- The provenance alias resolves to the existing `--prov-ink` value in each theme and does not rename or re-express the source token.

## EVIDENCE

- Skeleton record opened and pushed by `9a1d0542357aa392d475b0737648ee952c930757`.
- DS-PR-0a implementation landed by `48ae8c7b8c2642a39e3fcf6164452f7196351b10`.
- Reviewer gate fixes landed by `bc3944fb90dcf5c749c841a67035119424b1827a`.
- Evidence record updated by this record commit.

## DEVIATIONS

- No implementation deviation from the frozen packet.
- The combined spacing row is wrapped before `--sp-7:32px`, and the provenance-root line is wrapped before `--ink-prov`, so both frozen acceptance regexes anchor at line starts. This is line-formatting only; no value, selector, declaration order, or consumer changed.
