# Observed quote-source coverage, 2026-10-14 ET

Bounded reads only. No private Terminal SSH retry, new credential, source collector, retrospective financial test or production detector invocation. Observations after 23:00 ET describe after-hours/closed-session source state, not regular-session freshness.

## Independent source paths

The allowed public /live/quotes.json endpoint returned HTTP 200/no-store with 365 quote objects. SPY was present; the 11 sector ETFs were not. Current source shows this is the display projection, not the Basket Pulse full input. Do not diagnose the full producer universe from this subset. Exact payload digest and schema/clock metadata are in public_display_source_census.json; no prices are retained in that report.

The existing GitHub live-data branch, read through authorized GitHub access, has one orphan commit 99f656615250e527aec8bcc2389a08b2e658ea90 committed 2026-10-15T00:37:52Z. Its quotes.json has 2,166 quote objects, all 11 sector ETF anchors and SPY, and objects for 700 of 702 active basket member tickers at the bound membership revision. The payload digest is ef51fdd92bccd72e721af7452f2379e107cb1131e677b9626319d6d3550b772b. Quote-object presence is not matched-clock eligibility, present subscription rights, freshness in regular hours, or representative group coverage.

.github/workflows/live-quotes.yml explicitly creates a single-commit orphan branch; the observed commit has no parent. It cannot provide a two-snapshot historical trajectory. Do not scrape unknown overwritten refs or backdate a contemporary download as first historical availability.

The current VPS orchestrator's snapshot() runs the full producer with --private-provenance and stores quotes_full.json in its existing private state directory before passing that source to Basket Pulse. The repository live-data writer is another existing full-producer consumer, not proof that its current bytes equal the private VPS input. Its broad universe nevertheless resolves the narrower claim that the public display subset is not the only existing quote source.

## Consequence

The pilot should use the incumbent full snapshot path and existing retained-history owner, not buy a new feed or build a new snapshot service merely because sector ETFs are absent from public display quotes. Real regular-session source-to-consumer proof still needs two eligible observations and authorized production access. Overnight/opening anchors, availability/correction lineage, delayed sampling and rights remain separately qualified.
