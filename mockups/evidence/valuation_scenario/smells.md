# Page evidence — measured facts

_Heuristics identify review targets; they do not determine that a page is bad._

Generated 2026-09-19T04:15:55Z · schema `mastermind.ux_smell_report.v1`

| route | page_id | words | h1 | panels | height px | h-overflow | slug hits | TODO hits | as-of | source | shots |
| --- | --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | :---: | :---: | ---: |
| /stocks-null/AAPL.html | stocks-null_AAPL.html | 180 | 0 | 4 | 900 | no | 0 | 0 | no | yes | 1.0 |
| /stocks/AAPL.html | stocks_AAPL.html | 193 | 0 | 4 | 900 | no | 0 | 0 | no | yes | 1.0 |

## Metric notes

- **asof_present** — approximate contract probe (selector OR case-insensitive text pattern); absence is a prompt to look, not a verdict
- **console_error_count** — distinct console 'error' texts across every state of the page the driver attempted, captured or not — a state that failed to load is often the one carrying the evidence
- **duplicate_heading_texts** — case-folded visible heading text seen more than once; a repeated section label across tabs is a legitimate duplicate
- **panel_count** — class-name heuristic over the configured selector list; both over- and under-counts are expected
- **payload_bytes_total** — sum of response body sizes reported by the driver for the reference state; excludes bodies the driver could not size
- **raw_slug_hits** — visible text matching 3+ segment snake_case; legitimate identifiers (file names, API keys quoted on purpose) match too
- **screenshot_completion** — captured states / attempted states for this page; states the registry excludes are not attempted and are recorded as gaps
- **section_count** — direct <section> children of <body> plus direct element children of <main>; an approximation of 'how many blocks is this page'
- **source_present** — approximate contract probe (selector OR case-insensitive text pattern); absence is a prompt to look, not a verdict
- **visible_word_count** — whitespace-split innerText of <body>; Chinese text is not word-segmented, so a zh capture undercounts relative to en

## Re-capture notes (Heal h3_7117, 2026-09-19)

CODE_HEAD: `61f3ebad371da1b8308cb46237646d47d6e9cc24`. Replay: `mockups/evidence/valuation_scenario/_recapture.py`.
The lost disposable wrapper was reconstructed using the existing AAPL test fixture,
the production translation macro and ticker styles, and the unchanged valuation
partial. Both routes are local panel fixtures; they are not full live stock pages.
Dark/light × EN/ZH × desktop 1440/mobile 390 × normal/all-null = 16/16 crops.
The historic manifest has no CSS-forced states; no --force-state flag is used.

The current thin-margin ruler label is `Margin too thin to run / 利润率过低，无法计算`.
That label and `Today's price sits near the case we could run. / 当前股价接近唯一已算出的情景。`
are **tests-only, not captured** in the normal/all-null matrix. The one/two-case
below/above copy is likewise tests-only. Null panels capture missing reported
earnings; they do not stand in for the distinct thin-margin case.

Local synthetic normal/all-null AAPL panel crops only; no live deployment, authentication or real SEC-data freshness proof. Thin-margin and one-case near/below/above branches are tests-only, not captured in this 16-cell matrix.
The 21-test suite passed; deliberately wrong near expectations produced
`2 failed, 19 passed` before restoration. No current template string needed repair.
