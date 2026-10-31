# C3 F05 per-family consequence delivery census — News Intelligence Estate (2026-10-31)

## Scope and method

Reconciliation only, at HEAD `fff8ab44c690f1c7e68fe3e4cc49fc92663917ee` (branch
`lane/news-w3-c3-census-r1`, clean tree). Masterplan package C3
(research/news_intelligence_estate_20261021/MASTERPLAN.md:358): "Reconcile and
prove F05 per-family consequence delivery; reuse #8775 and existing Chronicle;
preserve available-record counts, six family disclosures and honest empties".

Method: targeted `grep -n` inventories plus `sed -n` region reads (≤25 lines per
region) over `engine/chronicle/impact.py`, `scripts/build_site.py`,
`templates/news.html.j2`, the three test files, and the #8775 evidence receipt;
`git show`/`git log` for merge lineage. One bounded suite run
(`tests/test_chronicle_impact.py`, 67 passed).

Sparse-worktree facts (this lane tree omits `data/`, `site/`, `mockups/` per
`config/sparse_worktree.json:9` and its `exclude_dirs`): `mockups/evidence/
news-family-inspection/` was read from the object store via
`git show HEAD:<path>` (files are tracked; the directory is omitted, not
absent); `data/chronicle/events.jsonl` and `site/news.html` are MISSING in this
worktree — the corpus is nevertheless git-tracked at HEAD (18,761 lines by
`git show HEAD:data/chronicle/events.jsonl | wc -l`; `state_log.jsonl` 60
lines), and `site/news.html` is likewise tracked at HEAD — a committed
nightly-render page carrying the rendered `#nxConsequence` section (blob, last
render commits and section counts under "Evidence receipts" below). Its
absence from this worktree is sparse-profile omission, not git absence.
`research/news_intelligence_estate_20261021/D1_NEWS_INPUT_TRACE.md` (243 lines)
contains no Chronicle/consequence/glance row — this chain is outside D1's
traced input set.

## Delivery chain at HEAD

| Stage | path:line | Input | Output | Owner per MASTERPLAN |
|---|---|---|---|---|
| Event spine (upstream) | `scripts/build_chronicle.py:1-8`; `engine/chronicle/spine.py:85` `build_events`, `:202` `load_events_jsonl` | source adapters + forward ledgers | `data/chronicle/events.jsonl` (committed; 18,761 lines at HEAD) | MarketOntology F05 "Chronicle event spine/state log/rollups" (MASTERPLAN.md:88) |
| Per-family projection producer | `engine/chronicle/impact.py:464` `project_family_impact`; `:360` `project_events_impact`; `:227` `project_event_impact` | chronicle.event.v1 records | projections grouped by `source` family; closed-key glance rows | MarketOntology F05 "per-family projection" (MASTERPLAN.md:88) |
| Glance surface (window + family views) | `engine/chronicle/impact.py:1012` `glance_consequence_surface` | full event list | dict with `rows`, `family_tally`, `family_views` (six families, `available_count`, ≤4 rows each) | MarketOntology F05 "seven-day consequence glance" (MASTERPLAN.md:88) |
| Build consumer | `scripts/build_site.py:7676-7680` (import + `load_events_jsonl(data/chronicle/events.jsonl)` + `glance_consequence_surface(_evs)`) | `data/chronicle/events.jsonl` | template context key `chronicle_impact` (`scripts/build_site.py:7715`, retry `:7729`) → `site/news.html` (`:7695`) | News page build (C3 "reuse #8775 and existing Chronicle", MASTERPLAN.md:358) |
| Template region | `templates/news.html.j2:1058` (`CI` guard) … `:1061` `<section id="nxConsequence">` … `:1092-1116` family disclosures | `chronicle_impact` context | rendered overview cards + six `<details class="nx-depth nx-family">` + typed empties | Chairman design rule region; News consumer (MASTERPLAN.md:126) |
| Tests | `tests/test_chronicle_impact.py` (67 tests), `tests/test_news_page_render.py`, `tests/test_chronicle.py:2937` | producer + template | pinned family counts, empties, closed keys | C3 acceptance (MASTERPLAN.md:358) |
| Evidence receipt | `mockups/evidence/news-family-inspection/{EVIDENCE.yml,README.md,manifest.json}` (merged in `9ebe0fe08812`) | local candidate render | capture receipt; **not** a served-page proof | retained record for "#8775 per-family source merged" (MASTERPLAN.md:88) |

Post-merge drift: `git log -- engine/chronicle/impact.py templates/news.html.j2`
shows exactly one later commit, `ccc3242ef529` (Shared Shell #7949, 2026-10-21),
whose `impact.py` diff is empty and whose `news.html.j2` diff is one changed
line (signin redirect via `window.MMXSharedShell.openAuth`) outside the
consequence region — the F05 producer and template region are byte-stable since
`9ebe0fe08812`.

## Producer: families, windows and honest empties

`engine/chronicle/impact.py` imports only `engine.chronicle.schema`
(impact.py:69) plus stdlib; `spine.py`/`state_log.py`/`rollups.py`/`manifest.py`
are upstream via the events file, not Python imports. `governor.py:179-181`
records the design: consumers call `glance_consequence_surface` /
`project_family_impact` over a bounded window at read time; no nightly impact
dump is written.

- **Family key**: the event `source` field — `project_family_impact` buckets by
  `proj["source"] or "unknown"` (impact.py:478); the surface reads
  `(proj.get("source") or "").strip()` (impact.py:1100, :1108). `schema.SOURCES`
  (engine/chronicle/schema.py:28-31) enumerates seven: `research_vault,
  prophet_ledger, macro_release, earnings, earnings_call, regime_flip,
  risk_band`.
- **Excluded**: `GLANCE_EXCLUDED_FAMILIES = frozenset({"prophet_ledger"})`
  (impact.py:135) — the product's own trade ledger; typed exclusion, never
  tallied (test `tests/test_chronicle_impact.py:737`, `:1099`).
- **Eligible six**: `GLANCE_ELIGIBLE_FAMILIES = frozenset({"earnings",
  "earnings_call", "macro_release", "regime_flip", "risk_band",
  "research_vault"})` (impact.py:136-143). Disclosure order is
  `eligible_order = [fam for fam in _schema.SOURCES if fam in
  GLANCE_ELIGIBLE_FAMILIES]` (impact.py:1091) → `research_vault,
  macro_release, earnings, earnings_call, regime_flip, risk_band`.
- **Flip families**: `GLANCE_FLIP_FAMILIES = frozenset({"regime_flip",
  "risk_band"})` (impact.py:157); ≥2 in-window flips of one series collapse to
  the latest state plus the unstable note (`_collapse_flip_series` impact.py:656;
  note strings impact.py:153-154).
- **Window**: `_select_glance_pool` (impact.py:573-591) — events dated within 7
  days (`GLANCE_WINDOW_DAYS = 7`, impact.py:127) **as-of the newest parseable
  event date** (`_as_of_event_date` impact.py:564-571: "Render path has no
  wall-clock; the ledger's own newest date is the as-of"); if that window is
  empty, newest-200 fallback (`GLANCE_FALLBACK_LIMIT = 200`, impact.py:128).
  Header labels from `_glance_window_labels` (impact.py:615-629) via
  `_plain_window_span` (impact.py:592-613), e.g. "Events from 31 Aug to 7 Sep
  2026" / fallback "Latest 200 recorded events" (impact.py:146-147).
- **Date fields and their meaning** (`_time_fields` impact.py:201-225 with
  `_midnight_of` :197): `event_time` is the spine calendar `date` (when the
  development occurred); `known_at` is the source `ts` printed **only when
  genuinely distinct from midnight of that date**, else `None` with a typed
  reason (`NO_SOURCE_CLOCK` :85 / `NO_DISTINCT_SOURCE_CLOCK` :89) — never
  fabricated.
- **Input keys read** by `project_event_impact` (impact.py:253-297): `tickers`,
  `date`, `ts`, `id`, `source`, `source_ref`, `kind`, `title`, `facts`, `links`,
  `themes` (the `schema.EVENT_FIELDS` allowlist, schema.py:21-24); second-order
  tickers arrive only as caller arguments, never invented (impact.py:227-247).
- **Honest empties, producer side**:
  - Empty event list → early return (impact.py:1056-1078): `reason_en "No
    chronicle events in this window yet."`, `empty_kind: None`,
    `family_views: []`, `rows: []`.
  - Zero qualifying rows → `empty_kind: "no_named_exposure"` with
    `EMPTY_NO_EXPOSURE_EN/ZH` (impact.py:1270-1291; strings :144-145) —
    `family_tally`/`family_views` are still emitted in that typed-empty return
    (`"family_tally": family_tally,` / `"family_views": family_views`,
    impact.py:1283-1284) so each family renders its own typed state.
  - Per-family state (impact.py:1189-1193): `no_events` (0 in-window),
    `named` (≥1 direct-ticker event), `none_named` (events present, none with
    a direct ticker); `in_window` counts the **pre-exposure-filter** window
    pool (impact.py:1098-1105, :1179-1181) so a ticker-less macro event still
    counts honestly.

## Consumer: counts, six-family disclosure, empty state

**Build step** — `scripts/build_site.py:7671-7689`, comment "F05/MO-PAID-017:
bounded chronicle consequence surface for News Feed. Read-time projection over
a recent window — never a nightly-committed impact.jsonl dump." It loads the
full unfiltered spine (`_evs = _spine_mod.load_events_jsonl(_ev_path)` with
`_ev_path = data_dir()/chronicle/events.jsonl`, build_site.py:7678-7679) and
calls `glance_consequence_surface(_evs)` (:7680); the result is passed as
`chronicle_impact=` into `news.html.j2` (:7715; artifact-free retry :7729) and
rendered to `site/news.html` (:7695). On projection failure a degrade dict is
substituted (:7683-7694) that deliberately carries **no** `family_tally` /
`family_views` keys — the template type-guard then hides the family section
(pinned by `tests/test_news_page_render.py:1007`). `scripts/build_news.py` and
`scripts/build_chronicle.py` have no `chronicle_impact`/`family_views`/
`nxConsequence` reference (grep clean); the sole production caller of the
producer family is `build_site.py`.

**Available-record count** — `available_count` is written once, in the
`family_views` comprehension (impact.py:1206-1214): `"available_count":
len(buckets[ft["family"]])` (:1213) — collapsed **display records** after
flip-collapse and title filtering, before the overview cap; `in_window`
(source-event count) is carried separately from `family_tally` (:1194-1201) so
"an empty family is explained honestly" (comment :1203-1205). Rows are capped
at four: `"rows": buckets[ft["family"]][:4]` (:1214).

**Six-family disclosure** — `templates/news.html.j2:1092-1116`: heading
`t('Browse by event type','按事件类型查看')` (:1092), one
`<details class="nx-depth nx-family">` per `CI.family_views` entry (:1094);
summary shows the bilingual family label (`_FAMILY_LABELS`, impact.py:162-169 —
e.g. earnings "Earnings reports"/"业绩公告") and `{{ family.available_count }}
{{ t('records','条记录') }}` (:1097). The code names exactly six families
(`schema.SOURCES` ∩ `GLANCE_ELIGIBLE_FAMILIES`, impact.py:1091) — the same
six, in the same order, as the receipt's `source.actual_families`
(manifest.json). An opened body shows "Showing N of M records /
显示M条中的N条" (:1101) and the same `consequence_card` macro as the overview
(macro at :1031; grid :1102-1104; overview use :1075-1077 `CI.rows[:8]`).

**Empty states, template side** — CSS `#nxConsequence` block at
templates/news.html.j2:284-296 (`.nx-empty` base :251; `.nx-depth` family
materials :718-728):
- Overview typed empty (`CI.empty_kind == 'no_named_exposure'`, :1081-1084):
  lead sentence from `CI.reason_en/reason_zh` plus fixed next line "Cards appear
  when an event maps to a named exposure./当事件对应到明确标的时，卡片会在此显示。".
- No-payload empty (:1085-1090): "Not available yet/暂不可用" with reason or the
  default "No chronicle events in this window yet./此窗口尚无大事记事件。".
- Per-family empty (:1105-1115), three typed branches: `family.in_window == 0`
  → "No recorded events of this type in this window./该时段没有此类已记录事件。"
  (:1109); `family.state == 'none_named'` → "Recorded events do not name a
  market exposure./已记录事件未点名市场敞口。" (:1111); else neutral → "No
  displayable records are available for this event type./此类事件暂无可展示记录。"
  (:1113). All copy is bilingual via `t(EN, ZH)`.

## Tests that pin it

`python3 -m pytest tests/test_chronicle_impact.py -q -p no:cacheprovider` →
**67 passed in 0.77s** (no sparse-data dependency; suite is self-fixturing).

tests/test_chronicle_impact.py:
- `:286 test_family_grouping_reads_spine_source_field_per_event_family` —
  `project_family_impact` buckets strictly by the spine `source` field.
- `:515 test_project_family_impact_threads_corpus_eligible_themes` — windowed
  callers must thread corpus-level theme eligibility (broad theme refused only
  when threaded).
- `:566 test_glance_24_tickerless_research_notes_yield_typed_empty_and_zero_cards`
  — ticker-less-only input yields the typed empty, zero cards.
- `:601 test_glance_7day_window_and_200_event_fallback_boundary` — window and
  newest-200 fallback boundaries.
- `:737 test_prophet_ledger_is_typed_exclusion_from_glance` (and
  `:1099 …never_tallied`) — prophet_ledger excluded from rows and tally.
- `:767 test_glance_zero_qualifying_rows_typed_empty` — `no_named_exposure`
  typed empty with honest reason strings.
- `:783`/`:801` — fallback carries the "Latest 200" label and emits no tip.
- `:878`/`:907`/`:1145`/`:1239` — fair-share water-fill selection, tie-breaks,
  single-family equivalence.
- `:955 test_glance_family_tally_named_none_named_states`,
  `:1017 …five_tickerless_macro_events_state_none_named`,
  `:1041 …no_events_when_window_empty_for_family`,
  `:1063 test_glance_second_order_only_event_no_row_and_none_named` — the three
  tally states and their exact in_window/named/shown counts.
- `:1121 test_glance_rows_are_closed_key_no_calibrated_no_causal_no_second_order`
  — closed-key row contract.
- `:1391 test_family_views_are_bounded_and_independent_of_overview_cap` —
  family_views list equals `schema.SOURCES ∩ GLANCE_ELIGIBLE_FAMILIES` in
  order, `available_count == 7` with `rows` capped at 4, order-independent,
  independent of the overview cap.
- `:1413 test_family_views_distinguish_no_events_from_no_named_exposure` —
  macro ticker-less event → `in_window 1 / available_count 0 / none_named`;
  other families `no_events`; empty input → `family_views == []`;
  prophet_ledger absent.
- `:1428 test_family_views_use_window_and_collapsed_latest_series` — views use
  the 7-day window and the collapsed latest flip (union tickers, unstable note).

tests/test_news_page_render.py:
- `:334` single-column section; `:350` typed empty sentence only; `:383` plain
  dates never raw ISO; `:440` one row renders a card; `:473` fallback label
  renders; `:503` ZH card no ASCII spaces; `:535` stance once per locale;
  `:576` flip note without size slot.
- `:694 test_build_site_passes_unfiltered_event_spine_to_glance` — build_site
  hands the full loaded spine to the glance, no pre-filter between load and
  call.
- `:985 test_family_inspection_exposes_capped_records_and_typed_empty_sections`
  — exactly 6 `nx-depth nx-family` disclosures, "Showing 4 of 6 records /
  显示6条中的4条", both per-family empty strings in EN and ZH, `stock.html#TICKER`
  links, raw spine title and `prophet_ledger` absent from the section.
- `:1007 …absent_for_unavailable_legacy_payload` — no `family_views` key ⇒ no
  family section (degrade path).
- `:1076`/`:1111`/`:1125`/`:1154`/`:1188` — lens tip button with both locale
  attrs, no raw family slug, omitted when tally missing, ZH punctuation,
  omitted on newest-200 fallback.
- `:1209` no calibrated/causal/market-feed strings in the section.
- `:1247 test_consequence_honest_empty_all_families_fixture_in_en_and_zh` —
  all-six-families ticker-less fixture renders the typed empty plus a tip
  naming each family's state, both locales.

tests/test_chronicle.py (boundary-adjacent, not F05-row pinning): `:2937
test_market_feed_alias_empty_projection_never_upgrades_from_not_served` — the
consequence surface never upgrades a Market-Feed alias state (ledger row
MO-DELTA-001 "PROJECTION_ONLY … does not masquerade as a Market-Feed product",
research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv:49).

## Evidence receipts and the owed covering-render proof

`mockups/evidence/news-family-inspection/EVIDENCE.yml` (4 lines, read in full):
schema `mastermind.page_evidence_receipt.v1`; `changed_paths:
[templates/news.html.j2]`; manifest pointer to `manifest.json`. (The receipt's
own `changed_paths` names only the template; the merge `9ebe0fe08812` also
carried `engine/chronicle/impact.py` +18, `tests/test_chronicle_impact.py` +56,
`tests/test_news_page_render.py` +50, `capture.cjs` +62 and 17 PNGs —
`git show 9ebe0fe --stat`.)

`README.md` (read in full) is the F05 MO-PAID-017 bounded design freeze (CEO A,
2026-10-11, base `478103d5e8…`): six native disclosures reusing `nx-depth`
materials; `available_count` counts collapsed display records, not raw event
fires; empty wording distinguishes no-recorded-events from events-without-named-
exposure plus a neutral unavailable-display reason; acceptance ends "CI
concluded before exact-head merge, **then covering render/served check**" and
"Local fixtures and committed-corpus evidence are labelled separately from
served acceptance… production proof remains separate."

`manifest.json` (read in full; schema `mastermind.p0_evidence.v2`,
generated_at `2026-10-11T07:27:14.860Z` — 42 minutes before the merge at
08:09:22Z): `head` names the **base** `478103d5e8…`, not the merge; target
`news.html#nxConsequence`; axes desktop 1440×900 / mobile 390×844 × locales
en/zh × themes dark/light × access anonymous, subject `consequences`; 17 states
(8 resting + 8 real keyboard-open + 1 saved-corpus mobile); fixture "six
earnings with named exposures; one tickerless macro event; overview cap1";
saved corpus 16,771 events, window "Events from 1 Oct to 8 Oct 2026";
`source.actual_families` = exactly the six families with `in_window`/
`available_count` (research_vault 0/0; macro_release 3/0; earnings 0/0;
earnings_call 6/6; regime_flip 0/0; risk_band 0/0) — a live demonstration that
in_window and available_count diverge honestly (macro_release: 3 source events,
0 display records). Honesty block: "Local render of the candidate template and
producer… **No served, authenticated or fresh-market-data claim**"; source was
uncommitted at capture, pinned by template/producer SHA256.

**What the receipt proves**: the candidate producer+template rendered the six
disclosures, capped-record counts, keyboard interaction and typed empties
across the full theme×locale×viewport matrix from a local fixture and the
committed corpus, before merge. **What it does not prove**: any served page —
it is a pre-merge local-render capture of uncommitted sources against a base
commit.

**The committed served page at HEAD** — `site/news.html` is a tracked blob at
HEAD (`git ls-files site/news.html` lists it; `git ls-tree HEAD` → `100644
blob 152aedcd…`), last committed by the nightly renders `b4a4333cdd87` and
`c600dd5631f1` ("render: site re-render 2026-10-31" / "engine-render: regime
recompute + re-render 2026-10-31"). It is a rendered artifact, not a proof
document: measured with bounded greps (at `7ee58f07a86e`, one census-file
commit past `fff8ab44c690`; the page blob is byte-identical at both), the
committed page contains the `#nxConsequence` section (`<section …
id="nxConsequence" …>`, 1 matching line), exactly 6 `nx-depth nx-family`
family disclosures, the window label "Events from 23 Oct to 30 Oct 2026", and
11 lines carrying `nx-empty` typed-empty markup. The two mockup receipts above
remain pre-merge local renders; this page is the committed nightly render of
the merged code.

**"Covering-render proof still owed" in committed terms** (MASTERPLAN.md:88),
restated against that page — two separate facts. What EXISTS is a committed
nightly-rendered page carrying the section: artifact evidence that the render
path produces the six disclosures, the window label and the typed empties.
What does NOT exist is any committed receipt or proof document that checks
that served page's counts, six disclosures and empties against the corpus.
The retained checkpoint record itself — D100 in
research/MARKET_ONTOLOGY_CEO_A_CONTINUATION_HANDOFF_2026-10-02.md:617 — ends
"MERGED2026-10-11T08:09:22Z as `9ebe0fe088126267c6a4fb64ff2dab54a268da56`
after 26checks concluded… **Covering render/served pending**". The frozen grep
(`git grep -E 'nxConsequence|news-family-inspection'` over `mockups/evidence`,
`research`, `docs`, run as `git grep` for the sparse-omitted `mockups/`) finds
only: the pre-#8775 receipt `mockups/evidence/a-f05-1-consequence/` (landed
with `d2d7a6af805a` / #6896, the earlier "Also watching" era), the #8775
receipt itself, and the two research citations above; `git grep … HEAD --
verify_shots` returns nothing. **Is there a committed served-page or
nightly-render receipt for `#nxConsequence` after `9ebe0fe`? NO.** The debt is
an evidence-receipt gap — accurately recorded and still open — not an absence
of the rendered artifact.

## Reconciliation

| Masterplan claim (line) | Observed at HEAD | Status |
|---|---|---|
| :88 "Chronicle event spine/state log/rollups, seven-day consequence glance, per-family projection" | spine `build_events`/`load_events_jsonl` (spine.py:85,:202) → committed `data/chronicle/events.jsonl`; 7-day pool impact.py:573-591; per-family views impact.py:1206-1214 | RECONCILED |
| :88 "#8775 per-family source merged in retained record" | merge `9ebe0fe08812` in history with impact.py/templates/tests/receipt; impact.py has no later commit; the one later template commit (`ccc3242ef529`) touches one line outside the F05 region | RECONCILED |
| :88 "covering-render proof still owed there" | D100 (handoff:617) "Covering render/served pending"; committed receipts are pre-merge local renders only (manifest honesty block); post-merge served receipt grep → NO | RECONCILED (the debt is real and recorded) |
| :88 "Reconcile actual served state" (artifact) | `site/news.html` is a tracked blob at HEAD (`git ls-files`/`git ls-tree`; last commits `b4a4333cdd87`/`c600dd5631f1`, site re-render 2026-10-31) whose committed page carries the rendered `#nxConsequence` section: 6 `nx-depth nx-family` disclosures, window "Events from 23 Oct to 30 Oct 2026", typed `nx-empty` markup | RECONCILED-ARTIFACT |
| :88 "Reconcile actual served state" (receipt) | No committed receipt or proof document checks that served section's counts, six disclosures and empties against the corpus (D100 handoff:617 "Covering render/served pending"; frozen grep → only pre-merge receipts) | GAP-RECEIPT (extends consumer → served stage) |
| :88 "causal/ranked implications remain gated" | `CAUSAL_LABEL = "uncalibrated_association"` (impact.py:74); `calibrated_impact: None` + `CALIBRATED_IMPACT_GATE_REASON` (:82, :293-294); closed-key rows (test :1121); template "no sizing, not a forecast" (news.html.j2:1071) | RECONCILED |
| :126 "the six-family consequence interface" | exactly six disclosures (impact.py:1091 order; template loop :1093-1116; test_news_page_render.py:985 asserts count == 6) | RECONCILED |
| :126 "The per-family source is already built" | `family_views` producer + consumer + tests all present at HEAD (impact.py:1206-1214; build_site.py:7680; tests :1391/:1413/:1428/:985) | RECONCILED |
| :126 "unresolved retained checkpoint concerns covering generation and served proof" | nightly generation of the section is in the render path (build_site.py:7671-7689, read-time projection); no covering-generation or served receipt has landed since 2026-10-11 | RECONCILED |
| :358 "preserve available-record counts" | `available_count` = collapsed display records (impact.py:1213), distinct from `in_window` source events (:1194-1201); template prints it (:1097, :1101); manifest demonstrates 3/0 divergence; tests :1391/:985 pin it | RECONCILED |
| :358 "six family disclosures and honest empties" | six `nx-depth nx-family` details (:1093-1116); typed empties at three levels — surface (:1081-1090), family (:1105-1115), producer states (:1189-1193); tests :1413/:1247/:350 | RECONCILED |

Counts: 10 RECONCILED (one as RECONCILED-ARTIFACT), 1 GAP (GAP-RECEIPT),
0 CONTRADICTED.

## Gaps for C3

Evidence gaps only; each names the chain stage it extends. No implementation
proposal.

1. **Served-stage receipt gap** (extends template → served page): no committed
   served-page or nightly-render receipt for `#nxConsequence` exists after
   `9ebe0fe` (frozen grep → NO) — the nightly-rendered page itself is
   committed (see "Evidence receipts"), so the missing artifact is the
   receipt, not the render. The committed record stops at D100's
   "Covering render/served pending" (handoff:617). Closing it needs a receipt
   that checks the rendered/served section, not new code.
2. **Corpus-growth re-proof gap** (extends producer → receipt): the #8775
   receipt pinned corpus 16,771 events (window 1–8 Oct 2026); HEAD carries
   18,761 committed events, and the committed served page renders a newer
   window ("Events from 23 Oct to 30 Oct 2026"). No committed receipt checks
   the served section against the current corpus — the #8775 receipt's own
   honesty block scopes it to the capture-time corpus.
3. **Served-empty coverage gap** (extends consumer → receipt): the receipt's
   17 states cover the fixture's no-events / no-named-exposure variants in a
   local render; no committed receipt shows the served page in its
   projection-failed degrade state (build_site.py:7683-7694, section hidden per
   test :1007) or with a live empty corpus.
4. **D1 trace coverage gap** (extends estate documentation): D1_NEWS_INPUT_
   TRACE.md (243 lines) has no row for the Chronicle consequence input — the
   F05 chain is unreconciled in the estate's own input-trace artifact (this
   census is the first committed reconciliation of it).

## What this census is not

Not a design, build, or behaviour change: no code, template, data, or site
file was modified; no site was rendered; no PNG was opened (receipt PNGs are
cited only through manifest/EVIDENCE.yml fields); no CI, PR, label or merge
action was taken. Reconciliation counts describe committed evidence at HEAD,
not served truth: nothing here upgrades the delivery ladder past MERGED for
#8775 — the served/production-proof rung remains unclaimed, exactly as D100
records. The pytest run is a targeted suite result, not a CI conclusion.

## Evidence

Every command run for this census (worktree `/home/ubuntu3/lanes/wt/news-w3-c3-census-r1`, branch `lane/news-w3-c3-census-r1`):

1. `git rev-parse HEAD` → `fff8ab44c690f1c7e68fe3e4cc49fc92663917ee`
2. `git status --porcelain` → empty
3. `git branch --show-current` → `lane/news-w3-c3-census-r1`; `printenv REMOTE_SUB_RUN_ID` → `news-w3-c3-census-r1`
4. `mkdir -p ~/lanes/tmp/news-w3-c3-census-r1`
5. `git show 9ebe0fe --stat | head -40` (file list quoted above)
6. `git log --oneline -8 -- engine/chronicle/impact.py templates/news.html.j2 | cat`
7. `grep -n "F05" research/news_intelligence_estate_20261021/MASTERPLAN.md`
8. `sed -n '88p;126p;136p;218p;234p;358p' research/news_intelligence_estate_20261021/MASTERPLAN.md`
9. `grep -n -i -E "chronicle|consequence|family|news page|8775" research/news_intelligence_estate_20261021/D1_NEWS_INPUT_TRACE.md`; follow-up `grep -n -i "chronicle"` / `grep -n -i -E "impact.py|glance"` → no hits (243 lines)
10. `git show HEAD:mockups/evidence/news-family-inspection/EVIDENCE.yml` (full)
11. `git show HEAD:mockups/evidence/news-family-inspection/README.md` (full)
12. `git show HEAD:mockups/evidence/news-family-inspection/manifest.json` (full via python structure walk; six `actual_families` + 17 states printed)
13. `wc -l engine/chronicle/impact.py` (1309); `grep -n -E "^def |^GLANCE|^[A-Z_]* =|^class " engine/chronicle/impact.py`
14. `sed -n '127,158p' / '197,226p' / '227,260p' / '260,300p' / '360,400p' / '400,437p' / '438,463p' / '464,510p' / '544,592p' / '592,630p' / '1012,1075p' / '1076,1140p' / '1140,1200p' / '1200,1309p' engine/chronicle/impact.py`
15. `grep -rn -E "project_family_impact|project_events_impact|glance_consequence_surface" scripts engine templates tests` (callers)
16. `grep -rln -E "nxConsequence|consequence" scripts engine templates`
17. `sed -n '7655,7735p' scripts/build_site.py`
18. `ls scripts/build_news.py scripts/build_chronicle.py`; `sed -n '1,12p'` of each
19. `grep -n -E "nxConsequence|nx-empty|nx-depth" templates/news.html.j2`; `wc -l templates/news.html.j2` (2204)
20. `sed -n '1055,1105p' / '1105,1165p' / '1041,1057p' templates/news.html.j2`; `grep -n "macro consequence_card"` (:1031)
21. `sed -n '14,60p' engine/chronicle/schema.py`; `grep -n "SOURCES" engine/chronicle/schema.py`
22. `grep -n -E "def |^class " engine/chronicle/spine.py`; `grep -n -E "state_log|rollups|manifest|governor" engine/chronicle/impact.py` (no hits)
23. `grep -n -E "^def test_|^class " tests/test_chronicle_impact.py` (all 67)
24. `grep -n -E "def test_.*family|.*consequence|.*empty|.*available|.*glance" tests/test_chronicle.py tests/test_news_page_render.py`
25. `python3 -m pytest tests/test_chronicle_impact.py -q -p no:cacheprovider 2>&1 | tail -3` → `67 passed in 0.77s`
26. `sed -n '286,296p' / '515,533p' / '1391,1428p' / '1428,1443p' / '955,985p' / '1017,1040p' tests/test_chronicle_impact.py`
27. `sed -n '985,1030p' / '1247,1290p' / '694,740p' / '2937,2960p' tests/test_news_page_render.py` (+ test_chronicle.py:2937 read)
28. `git grep -n -E "nxConsequence|news-family-inspection" HEAD -- mockups/evidence | cut -c1-160`; `grep -rn … research docs | cut -c1-160`
29. `sed -n '615,625p' research/MARKET_ONTOLOGY_CEO_A_CONTINUATION_HANDOFF_2026-10-02.md`; `sed -n '49p' …/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv`
30. `git log --oneline -1 -- mockups/evidence/a-f05-1-consequence` → `d2d7a6af805a`; `git grep -l "nxConsequence" HEAD -- verify_shots` → empty
31. `git show ccc3242ef529 --stat | head -15`; `git show ccc3242ef529 -- engine/chronicle/impact.py` (empty); `git show ccc3242ef529 -- templates/news.html.j2` (one line, outside F05 region)
32. `ls data/chronicle/events.jsonl site/news.html` → both MISSING in sparse worktree; `git ls-files data/chronicle/` → events.jsonl, earnings_call_events.jsonl, manifest.json tracked
33. `git show HEAD:data/chronicle/events.jsonl | wc -l` → 18761; `git show HEAD:data/chronicle/state_log.jsonl | wc -l` → 60
34. `grep -n -E "_FAMILY_LABELS|family_views = |available_count|in_window_pool|family_tally" engine/chronicle/impact.py`; `sed -n '162,171p'`; `sed -n '178,184p' engine/chronicle/governor.py`
35. `grep -n -E "if not events:|if not rows:|no_named_exposure" engine/chronicle/impact.py`; `grep -n -E "Browse by event type|No recorded events|Showing ' ~" templates/news.html.j2`
36. `grep -n -E "mockups|evidence" config/sparse_worktree.json` (mockups in exclude_dirs)

r2 repair commands (worktree `/home/ubuntu3/lanes/wt/news-w3-c3-census-r2`,
branch `lane/news-w3-c3-census-r2`, at `7ee58f07a86e…`, clean tree):

37. `git ls-files site/news.html` → tracked; `git ls-tree HEAD site/news.html`
    → `100644 blob 152aedcd…`; `git log -2 --format="%h %s" -- site/news.html`
    → `b4a4333cdd87` ("render: site re-render 2026-10-31") / `c600dd5631f1`
    ("engine-render: regime recompute + re-render 2026-10-31").
38. `git show HEAD:site/news.html | grep -c 'nxConsequence'` → 1; `| grep -c
    'nx-depth nx-family'` → 6; `| grep -o -m1 'Events from [^<]*'` → "Events
    from 23 Oct to 30 Oct 2026"; `| grep -c 'nx-empty'` → 11; `git diff --stat
    HEAD~1 HEAD` → this census file only (page blob identical at `fff8ab44`
    and `7ee58f07`).
39. Every `path:line` citation re-derived by `sed -n` at HEAD and corrected
    where drifted (NEWS-W3-C3-REVIEW R1): impact.py 478, 1100, 1108, 1091,
    253-297, 1189-1193, 1203-1205, 1283-1284, 293-294; build_site.py 7695;
    news.html.j2 1071, 1075-1077; schema.py 21-24; governor.py 179-181; plus
    the exact test name at test_chronicle_impact.py:737.
