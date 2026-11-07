# Captured Sector Pulse and basket/Brief documents

Base carrier: `b168ff4a498999251e70dc6a0076e422d2689738`.
This is an explicit-input calculation/assembly boundary. Production ownership,
current provider observations, source release and authenticated beta remain open.

## One existing Pulse calculation

`engine.sector_pulse.build_pulse_from_inputs` requires decoded archive observations
and the existing heat-calibration document's verdict mapping. Empty values remain
explicit absence; neither starts a loader. `enrich_theme_intel_from_inputs` returns
a detached theme document and its one calculated Pulse.

The existing theme-row, heat-grade and observation-alignment algorithms remain the
single implementations. Current theme `as_of` controls the calculation. Same-day and
future archive observations are excluded; the first duplicate date wins. US deltas
use exact existing NYSE session slots, so missing endpoints stay unknown. Other
regions retain their own dated-observation convention. A real historical zero score
is not missing data. Calibration remains descriptive/risk context under its existing
grades and does not acquire trade or sizing authority.

All six existing enrichment keys retain `setdefault` precedence, including existing
None, zero and false. Rank, score, recommendation, rank_5d and delta_5d are unchanged.
Legacy reader/writer/merge entry points remain adapters; the merge still mutates its
owned input and returns None. Invalid or empty observations return before acquisition.
The explicit path does not log, load archives/calibration, write Pulse files, seed
history or append score/forward ledgers.

Independent literal fixture: `tests/fixtures/base_sector_pulse_7885.py`.
Original source at `7885f75fc27877b5757fdafc860da6552a2f52bf` has SHA256
`969a94a79d1f2713e8104fa532b73557e0ab0e2c7492b8773f916f374f94cc9e`.
The fixture has SHA256
`6eb878fa6352e9e5d4c2d3c09f93f58858576bfee9ef60fac365af206e4a5375`.
It contains literal original functions with only import/acquisition scaffolding,
not delegation to the extracted calculator.

Pulse-focused verification: **139 passed**, six pytest temporary-directory cleanup
warnings, exit0. Log `/tmp/mmx-sector-pulse-explicit-20261106.log`, SHA256
`711f1bc6811c62208339f3209cd3ef7d5d9893b1013bd1210d6d7963609d8050`.
This includes complete-output/enrichment parity, archive clock counterexamples,
field precedence, detachment, no-effect calls and original reader/writer wiring.

## One data-only basket/Brief assembly

`engine.sector_basket_documents.assemble_sector_basket_documents` accepts computed
basket, theme and allocation values plus explicit context history, alignment events,
bottoming-log rows and date, Chinese names, factor-season document, flow document,
Pulse observations/verdict and aware build time. It returns detached baskets,
si_handoff, the same Pulse and private assembly evidence.

Basket, theme, allocation and derived context sessions must equal the declared
baseline. An unavailable coherent context is refused. The full original chart is
retained; JSON-invalid/nonfinite values are refused. Build time is formatted in UTC
as the incumbent `generated_utc` display field and remains separate from source and
publication timestamps. The generation owner still serializes and hashes final
basket bytes once; this assembler creates no additional publication identity.

Bottoming uses `engine.us_act_now.assemble_bottoming_watch` and the actual captured
latest-date forward-log rows. Nonempty rows must carry the declared log date, and
future rows are refused. Older rows retain their older date in assembly evidence.
None and [] remain distinct. The bilingual name overlay order, dual-read/recovering
sets, authority disclosure and original buy/pullback/reduce lanes remain unchanged.
Fresh cycle output is not substituted for the retained forward ledger.

Factor-season chips retain the existing v2 schema, neutral omission, momentum
priority, list ordering and bilingual tooltip mapping. Flow exports only the
existing compact cluster regime. Member symbols come from computed basket rows.
`si_handoff` retains its five existing fields. Optional inputs keep their own source
vintages in private evidence; assembly does not relabel them with the new baseline.

The legacy `scripts.build_baskets` acquires its existing values and delegates the
moved display transformations to the same helpers. It keeps its existing page,
archive and publication responsibilities; those are never invoked by the runtime
entry. The existing recovering-field guard follows the shared helper and still
requires the legacy caller to invoke it.

Pre-extraction builder SHA256:
`3472f3947bbe138896fefc4df31c48c34ca928ed5ebf5b4ac1e5e939b391a577`.
A local Git object read stalled before edits; its original process was terminated
(exit143, no residual processes), and all three intended targets were verified
unchanged before the same extraction proceeded with that exact source hash fence.
No competing mutation or uncertain effect was replayed.

## Composition and affected verification

The final document suite passed **24 tests**, including actual computed basket/context
outputs reaching the existing native Brief projection: correct leader, 21 chart points,
20-session comparison and the unchanged source endpoint. The pure assembly has no
builder/archive/config/store/ledger effects, and returned values are detached.
Log `/tmp/mmx-sector-basket-documents-final-20261106.log`, exit0, SHA256
`19e5fec26ce797d742178bfc38f083244cd7482e56f8744272507059f5dbdd24`.
There were six pytest old temporary-directory cleanup warnings.

The broader affected run recorded **463 passed, 4 skipped and 5 failed**. One new
integration fixture used `fresh` instead of the existing `accepted` receipt enum;
that fixture alone was corrected, and the final 24-test gate above closes it without
changing production code. Four original generated-site assertions require files or
directories omitted from this sparse checkout. Their unchanged exact pinned source
was independently retrieved and each missing-artifact assertion reproduced before
any changed builder ran. Assertions and hosted gates were not removed or relaxed.
The affected log is `/tmp/mmx-sector-basket-pulse-affected-20261106.log`, exit1,
SHA256 `2d23a25988ce2dae772bd2fd04b562adb6ca414dc62906ae31d2b85300b9721d`.
Counts overlap and must not be added. This is not an all-green full-site gate.

[Source review proof](SECTOR_BASKET_DOCUMENTS_SOURCE_REVIEW_2026-11-06.json)
binds the three modified existing files to exact pinned GitHub source. Ten Pulse
calculation/reader/writer functions are byte-unchanged; the member-symbol, factor
output and five-field handoff expressions match the original AST. All seven changed
Python files parse and have no trailing whitespace. Both unscoped and scoped local
`git diff --check` attempts timed out at 45 seconds; no successful Git diff-check is
claimed. Source comparison and focused tests completed independently of that index
read limitation. Required hosted CI and release conditions remain binding.

## Remaining completion path

The canonical board still needs a shared pure preparation/reducer/envelope path.
The same private input cohort must capture Nasdaq/Russell membership and actual
holdings/auxiliary values before full Sector composition. Then one final producer
must publish all five Sector members under its original CAS and source admission.

The existing Terminal PRs remain separate release carriers. A single read at
2026-11-06T09:36:35Z confirmed #1311 actually QUEUED at position 22 with head 847af34
and 22 successful candidate contexts; #1285 actually QUEUED at position 19 with
head aba8b24 and 21 successful candidate contexts. Neither had a merge-group head or
merge commit. This is queue proof, not merge/deployment/acceptance.

Updater first-install/recovery, legacy-writer drain/anti-downgrade, CI capability
resolution, protected releases, API/Terminal installation and authenticated
source-to-screen/fault proof remain binding. Regional/product-family waves and
whole-estate acceptance remain open.
