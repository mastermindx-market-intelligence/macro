# Page evidence — measured facts

_Heuristics identify review targets; they do not determine that a page is bad._

Generated 2026-09-13T18:16:16Z · schema `mastermind.ux_smell_report.v1`

| route | page_id | words | h1 | panels | height px | h-overflow | slug hits | TODO hits | as-of | source | shots |
| --- | --- | ---: | ---: | ---: | ---: | :---: | ---: | ---: | :---: | :---: | ---: |
| /stocks-null/AAPL.html | stocks-null_AAPL.html | — | — | — | — | no | — | — | no | yes | 1.0 |
| /stocks/AAPL.html | stocks_AAPL.html | — | — | — | — | no | — | — | no | yes | 1.0 |

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

## Re-capture notes (2026-09-13, MO-B HEAL #7117)

The committed receipts at HEAD `a335fdaee970` were re-captured against this
PR's post-heal partial. The prior receipts (`generated_at: 2026-09-07T05:30:16Z`)
were captured against m#6905's merge base and pre-date H1–H4; the heal moves
visible text in 5 of 6 (page × locale) combinations — bare `FY2025` becomes
`2025财年` in the five base rows under ZH, the ruler gap mark for a margin-gated
Cautious now reads `Too thin to run / 利润率过低` instead of `No data / 无数据`,
and the H4 lede adds one plain-word sentence below the ruler. Each cell's sha256
in `manifest.json` pins the new render; previous PNGs (same sha256 names
`211e23337bcc5fab` … `7e4dc42ca27e457a`) are no longer in this directory.
