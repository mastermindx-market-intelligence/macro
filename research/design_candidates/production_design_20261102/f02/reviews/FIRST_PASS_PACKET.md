# F02 first-pass critique packet

## User / business job

The shared product kit must let an investor read dense comparisons, understand direction and units, distinguish unknown from zero and partial/stale data, inspect the underlying evidence, and return to the same context. It must support Macro, Company, Options and a public editorial page in light/dark, EN/ZH and narrow/wide presentations. It must preserve current domain capabilities and meaningful chart/table density. Keyboard, touch and 400% zoom are part of the intended journey.

This assignment concerns common component patterns and their consumer integration. The four proposed consumer slices must not imply deletion of the remaining existing product functions. Assess whether the supplied artifacts actually support the claimed shared tasks, what became harder or missing, and whether a reasonable user would prefer the current product for an important task. Do not assume behavior from a static image.

## Production-before and existing-system artifacts

All paths below are relative to the `f02/` directory.

- `evidence/macro-before.png` — served Macro inside the current investor shell.
- `evidence/company-before.png` — served Company Financials/Statements.
- `evidence/options-before.png` — served Options tape.
- `evidence/editorial-before.png` — served compound-growth article.
- `evidence/paper-metric-before.jpg` — existing canonical metric specimen.
- `evidence/paper-state-before.jpg` — existing canonical state specimen.
- `evidence/paper-pattern-before.jpg` — existing canonical chart/table/access pattern.

## Proposed-after artifacts

- `pattern-lab.html` — complete standalone source specimen.
- `sheets/macro-dark-1440.png`, `sheets/macro-light-1440.png` and matching SVGs.
- `sheets/company-dark-1440.png`, `sheets/company-light-1440.png` and matching SVGs.
- `sheets/options-dark-1440.png`, `sheets/options-light-1440.png` and matching SVGs.
- `sheets/editorial-dark-1440.png`, `sheets/editorial-light-1440.png` and matching SVGs.
- `sheets/mobile-comparison.png`, `sheets/macro-dark-390.svg`, `sheets/company-evidence-light-320.svg`.
- `sheets/states-and-semantics.png` and matching SVG.
- `sheets/macro-light-zh-390.svg`.

These exact files are the proposed artifact set to judge. Their immutable digests are in `reviews/first-pass-artifacts.json`. Do not read author explanations in other files for the first pass.

## Capability / task manifest

| Task | Critical | Required retained capability |
| --- | --- | --- |
| T01 Compare dense numeric rows | yes | Aligned raw-value comparison; meaningful units, coverage and source access; no hidden feature deletion |
| T02 Interpret a metric and its change | yes | Observation and comparator periods; percent versus pp/bps/currency; missing versus reported zero |
| T03 Inspect exact evidence and return | yes | Correct field/row/entity/source identity and clocks; reversible inspector; focus/scroll return |
| T04 Understand stale/partial/connected states | yes | Separate source freshness, coverage, transport and market session; retained useful data |
| T05 Use keyboard/touch/400% zoom | yes | Tabs, table scrolling, controls, overlays and virtualized-list semantics; no hover-only essential path |
| T06 Preserve Company depth | yes | Annual/quarterly statements, earlier periods, definitions, citations, route/entity identity and unknown fields |
| T07 Preserve Options depth and meaning | yes | Existing workflow tabs/filters/saved screens/share/export, side classification, exposure, coverage and exact contract identity |
| T08 Preserve Macro capabilities | yes | Regime/risk/calendar/linked desks and existing domain logic; useful chart compression remains |
| T09 Read and navigate public editorial | yes | Readable body, TOC/anchors, calculation, assumptions, publication dates and continuation destinations |
| T10 Handle exceptional read/write/access states | yes | Loading distinct from empty; clear recovery; guest/denied/expired; pending/failed/uncertain/saved with correct authority |
| T11 Switch theme/locale/density | yes | Retained meaning, legibility and hierarchy; long labels; no conflation of language, market region or trading semantics |
| T12 Use domain-owned verdict/count/lifecycle and focused charts | yes | Preserve existing meanings, partitions, transitions and chart/replay capabilities; common style must not redefine them |

## Critique output

Return `PASS`, `PASS_WITH_CONDITIONS` or `BLOCK` for this proposed reference set; findings with stable `PRC-nnn` or `VTC-nnn` IDs and blocker/major/minor severity; concrete before/after evidence; affected tasks; and `BETTER / EQUIVALENT / WORSE / UNKNOWN` task judgments. Separate observable defects from unverified behavior. Record first-pass UTC freeze time and the artifact digest set examined. Do not self-certify formal RIG approval.
