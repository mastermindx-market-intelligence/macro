# Market Ontology W5-A executor contracts (macro)

Verified in this worktree at `origin/main` `9a4a389c0d21d1ae4f195ec31e950eb5c07fb381` (`git rev-parse HEAD`). Operator commission W5-A: no build, no strategy, no network, no git writes. Every path:line below was opened or grepped in this session. Cheap fixture-only pytest on this head: `python3 -m pytest -q tests/test_research_priority_ordering.py tests/test_am_edition_producer.py tests/test_policy_lifecycle.py tests/test_glossary.py tests/test_chronicle_impact.py tests/test_capital_policy_projection.py` → **225 passed, 83 warnings in 41.42s**.

Excluded from re-decomposition (open PRs named in the commission): MO-PAID-020 #7122, MO-PAID-088 #7133, MO-DELTA-011 #7125, MO-DELTA-018 #7121, MO-PAID-062 #7127, MO-PAID-060 #7128, MO-PAID-064 #7126, MO-DELTA-029 #7110, F07 #7117/#7134, F11 #7100/#7106/#7124, F12 #7132, F06 #7102, F08 #7131.

## Summary

| row | disposition | tier | title |
|---|---|---|---|
| MO-DELTA-006 | RECORDS_MOVE | n/a | Theme Tracker already lists what to look at first |
| MO-PAID-017 | RECORDS_MOVE | n/a | News page already shows event consequences |
| MO-DELTA-001 | RECORDS_MOVE | n/a | No Market-Feed surface exists; alias is closed |
| MO-PAID-011 | CONTRACT | MINIMAX_ELIGIBLE | Morning edition page before the US open |
| MO-DELTA-010 | RECORDS_MOVE | n/a | Glossary already catalogs dashboard readings |
| MO-PAID-067 | RECORDS_MOVE | n/a | Capital Structure already shows dated policy steps |
| MO-DELTA-032 | RECORDS_MOVE | n/a | Policy Watch already shows proposal-to-enforcement stages |

---

### MO-DELTA-006 — [MO-B F04-1] Theme Tracker already lists what to look at first
DISPOSITION: RECORDS_MOVE

EVIDENCE NOW:
- `engine/research_priority_ordering.py:1-20` — module docstring names `MO-DELTA-006`, schema `mastermind.research_priority_ordering.v1`, rule `evidence_recency_then_daily_count_then_name`, ceiling `research_priority_only`. Command: `sed -n '1,20p' engine/research_priority_ordering.py`.
- `engine/research_priority_ordering.py:22-43` — `DOES_NOT_CLAIM` / `HELD_COLUMNS` / `FORBIDDEN_PAYLOAD_KEYS` refuse probability, confidence, impact, rank, score, gate, size, trade. Same command, lines 22-43.
- `templates/state_of_themes.html.j2:336-366` — section “What to look at first” / “先看哪些主题” is an ordered list by last recorded date then that day's statement count; copy says it is a reading order, not a score. Command: `sed -n '336,366p' templates/state_of_themes.html.j2`.
- `scripts/build_state_of_themes.py:1487-1511` — `load_research_priority()` calls `engine.research_priority_ordering` over the existing theme-graph store; failure degrades to `unavailable`. Command: `sed -n '1487,1511p' scripts/build_state_of_themes.py`.
- `templates/_navlinks.html.j2:283` — Theme Tracker is already in the mega-nav as `state_of_themes.html`. Command: `rg -n 'state_of_themes.html' templates/_navlinks.html.j2`.
- `engine/dislocation.py:1-21` — existing F04 dislocation substrate is the Fed-put washout gate (`latest.json["dislocation"]`), not a ranked opportunity map. Command: `sed -n '1,21p' engine/dislocation.py`.
- `templates/transmission.html.j2:31` — F04 explorer lineage page `transmission.html` exists (rates/inflation/dollar). Command: `sed -n '31p' templates/transmission.html.j2`.
- Ledger text `NOT_BUILT` / `real_producer=NONE` / `real_consumer=NONE` is stale against the files above. Command: `rg '^MO-DELTA-006,' research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv`.
- Fixture tests green on this head: `tests/test_research_priority_ordering.py` (included in the 225-pass run).

LEDGER MOVE ON MERGE+LIVE: capability_state_c2 `NOT_BUILT` → `BUILT_NOT_PROVEN` in the records PR (code is on `origin/main` `9a4a389c`; this session did not curl the live site). After live proof: `BUILT_NOT_PROVEN` → `DONE`. Live readback: `GET https://www.mastermind-x.com/state_of_themes.html` contains “What to look at first” / “先看哪些主题” and does not contain a confidence/impact/score chip in that section.

AUTHORITY: `research_priority_only`. Do not add calibrated ranking, impact, confidence, gate, size, or trade semantics (K5 + Eval-OS remain held). Sol split in ledger `adjudication_notes` stands.

---

### MO-PAID-017 — [MO-B F05-1] News page already shows event consequences
DISPOSITION: RECORDS_MOVE

EVIDENCE NOW:
- `engine/chronicle/spine.py:1-19,49` — canonical event spine; `EVENTS_REL = data/chronicle/events.jsonl`. Command: `sed -n '1,19p;49p' engine/chronicle/spine.py`.
- `engine/chronicle/state_log.py:1-15` and `engine/chronicle/rollups.py:1-8` — the other two producers the ledger names; both exist. Command: `ls engine/chronicle/spine.py engine/chronicle/state_log.py engine/chronicle/rollups.py`.
- `engine/chronicle/impact.py:1-20,72,80,918-931` — uncalibrated per-family consequence projector; `CAUSAL_LABEL = "uncalibrated_association"`; calibrated magnitude gated `not_yet_knowable_k5_gated`; `glance_consequence_surface` is the News Feed consumer over families earnings / earnings_call / macro_release / regime-risk / research_vault. Command: `sed -n '1,20p;72p;80p;918,931p' engine/chronicle/impact.py`.
- `scripts/build_site.py:6980-7024` — render-time call `spine.load_events_jsonl` → `impact.glance_consequence_surface` → template kwarg `chronicle_impact`. Command: `sed -n '6980,7024p' scripts/build_site.py`.
- `templates/news.html.j2:823-847` — “Event consequences” / “事件影响” section; comment states “News Feed entry point, not Market-Feed.” Command: `sed -n '823,847p' templates/news.html.j2`.
- Ledger `real_consumer=NONE stable consequence-oriented distribution` is stale. Command: `rg '^MO-PAID-017,' research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv`.
- Fixture tests green: `tests/test_chronicle_impact.py:1-11` restates the row's acceptance test and is in the 225-pass run.

LEDGER MOVE ON MERGE+LIVE: capability_state_c2 `PARTIAL` → `BUILT_NOT_PROVEN` (consumer is now `templates/news.html.j2` + `scripts/build_site.py`). After live proof: `DONE`. Live readback: `GET https://www.mastermind-x.com/news.html` contains “Event consequences” / “事件影响” and the stance “Named exposures only — no sizing, not a forecast.”

AUTHORITY: `context_only`; K3/K5 cap causal/second-order claims. Executor (none for this row) must not add calibrated impact, direction, or a second event store.

---

### MO-DELTA-001 — [MO-B F05-2] No Market-Feed surface exists; alias is closed
DISPOSITION: RECORDS_MOVE

EVIDENCE NOW:
- `engine/chronicle/market_feed_alias.py:1-41,58-61,507-513,571` — dedicated alias resolver for this row; introducing answer `NOT_SERVED`; public states `SERVED | PARTIALLY_SERVED | NOT_SERVED | UNKNOWN`. Command: `sed -n '1,41p;58,61p;507,513p;571p' engine/chronicle/market_feed_alias.py`.
- `engine/chronicle/impact.py:959,1046,1062` — glance payload always sets `served_as_market_feed: False`. Command: `rg -n 'served_as_market_feed' engine/chronicle/impact.py`.
- `scripts/build_site.py:6982,6993-6994` — render path stamps `market_feed_disposition: explicitly_does_not_serve_market_feed`. Command: `sed -n '6980,6994p' scripts/build_site.py`.
- `templates/news.html.j2:823` — the only `Market-Feed` string under `templates/` is a negation. Command: `rg -n -i 'market[- ]feed' templates engine --glob '!engine/neuralweb/**'`.
- Positive control: `rg -l chronicle templates` → `templates/news.html.j2` only. No Market-Feed-branded page.
- Ledger `real_consumer=UNCONFIRMED Market-Feed-branded surface` is stale: the alias is confirmed **not served**. Command: `rg '^MO-DELTA-001,' research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv`.

LEDGER MOVE ON MERGE+LIVE: capability_state_c2 `PARTIAL` → `BUILT_NOT_PROVEN` with `missing_contract_or_proof` rewritten to “alias closed: MO-PAID-017 consequence glance is News Feed, not Market-Feed (`served_as_market_feed=false`)”. After live proof of the news page: `DONE` for the alias question. Live readback: the news page must not brand itself “Market Feed”; the glance must keep `served_as_market_feed` false.

AUTHORITY: `context_only`. Do not promote `weight_hint` / `horizon_hint` into impact direction or magnitude (see `REJECTED_PROXIES` at `engine/chronicle/market_feed_alias.py:82-95`).

---

### MO-PAID-011 — [MO-B F01-1] Morning edition page before the US open
DISPOSITION: CONTRACT

EVIDENCE NOW:
- Ledger: `PROJECTION_ONLY` / `NOT_BUILT` / acceptance “a distinct AM-Edition page + producer script live on a render lane”. Command: `rg '^MO-PAID-011,' research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv`.
- `scripts/build_am_edition.py:1-18,36,814-830` — producer exists (`am_edition.v1`, `display_only`); `main()` writes **only** `site/am_edition.json` and fail-softs to exit 0. Command: `sed -n '1,18p;36p;814,830p' scripts/build_am_edition.py`.
- `ls templates/am_edition.html.j2 templates/am-edition.html.j2` → both missing. `rg -l 'am_edition' templates` → no hits. There is no page.
- Render-lane hook already present (do not add a second one): `config/dag.yml:1271-1272` and `:2837-2838` (`build_am_edition` / `scripts.build_am_edition`); `.github/workflows/render.yml:91,830` “AM edition producer (build_am_edition)”; `.github/workflows/daily.yml:3983-3986` same. Command: `rg -n 'build_am_edition' config/dag.yml .github/workflows/render.yml .github/workflows/daily.yml`.
- Existing brief pipeline to reuse, not rebuild: `scripts/build_aibrief.py:1-13,467-485` writes `site/aibrief.html` from `master_brief.json` / `china_brief.json` / `btc_brief.json` via `templates/aibrief.html.j2` and `lib.pages.write_page`. Command: `sed -n '1,13p;467,485p' scripts/build_aibrief.py`.
- `scripts/build_am_edition.py:680-694` already carries a `prior_close_brief_ref` block with `"link": "/aibrief.html"` — the page must render that link, not re-summarize the brief. Command: `sed -n '680,694p' scripts/build_am_edition.py`.
- `tests/test_am_edition_producer.py:1-7,17-31` — producer tests are fixture-only (no `data/`); `FORBIDDEN_KEYS` is the copy ceiling. Included in the 225-pass run.
- Sibling chrome: `templates/aibrief.html.j2:95` `{% include "_site_nav.html.j2" %}`; `lib/pages.py:740-746` is the required HTML writer.

OBJECTIVE: A user can open a distinct Morning Edition page before the US open and see since-prior-close facts (tape, session clock, regime, calendar, yesterday's brief link) in plain English and Chinese, with no scores.

CONSTRAINTS:
1. Extend existing `scripts/build_am_edition.py` so `main()` also writes `site/am_edition.html` through `lib.pages.write_page`. Do not add a new dag node, workflow step, or producer; the hook is already `scripts.build_am_edition` on daily + render.
2. Render the existing `am_edition.v1` payload only. The prior-close brief is a link to `/aibrief.html` (already in `_prior_brief_ref_block`). Do not re-summarize `master_brief`, do not call an LLM, do not read a new store.
3. Bilingual labels via the existing `t()` / `<span class="l-en">`·`<span class="l-zh">` convention copied from `templates/aibrief.html.j2`; include `_site_nav.html.j2` the same way aibrief does at line 95.
4. Forbidden in payload and visible copy (mirror `tests/test_am_edition_producer.py:26-31`): score, rank, signal, gate, size, ENTRY_OPEN, Prophet, conviction, buy, sell, target, confidence.
5. Add one public-nav card in `templates/_public_nav.html.j2` beside the glossary card at line 36, and a `macro:am_edition` editorial archetype next to `macro:aibrief` in `config/product_experience/page_registry_overrides.yml:835-837`.

OWNED FILES:
- Existing (edit): `scripts/build_am_edition.py`, `templates/_public_nav.html.j2`, `config/product_experience/page_registry_overrides.yml`.
- Existing (read / include / call only — do not change behavior): `templates/aibrief.html.j2`, `templates/_site_nav.html.j2`, `templates/_seo_head.html.j2`, `lib/pages.py`, `engine/i18n.py`, `tests/test_am_edition_producer.py` (must stay green).
- Existing (do not edit — already the render-lane hook): `config/dag.yml`, `.github/workflows/render.yml`, `.github/workflows/daily.yml`.
- New: `templates/am_edition.html.j2`, `tests/test_am_edition_page.py`.
- Nothing else.

ACCEPTANCE GATE:
RED on this head (`9a4a389c`) because there is no template and the producer writes JSON only:

```sh
python3 - <<'PY'
from pathlib import Path
assert not Path("templates/am_edition.html.j2").exists(), "template unexpectedly present"
src = Path("scripts/build_am_edition.py").read_text(encoding="utf-8")
assert "am_edition.html" not in src
assert "write_page" not in src
print("RED confirmed: no AM-Edition page on 9a4a389c")
PY
# expected: RED confirmed
# python3 -m pytest -q tests/test_am_edition_page.py
# expected: collection error (file missing) — that is the RED-first starting state
```

Executor adds `tests/test_am_edition_page.py` **first**. That file must, using tmp_path fixtures only (copy the tree helper from `tests/test_am_edition_producer.py:39`, freeze `now`, no `data/`):
1. assert `templates/am_edition.html.j2` exists;
2. render it with a `build_payload()` fixture and assert the HTML contains the Morning Edition heading (EN+ZH), `l-en` and `l-zh`, a session-state string, and an `aibrief.html` href;
3. assert none of `FORBIDDEN_KEYS` from `tests/test_am_edition_producer.py` appear as authority copy;
4. call `scripts.build_am_edition.main()` against the fixture root and assert it writes both `am_edition.json` and `am_edition.html`, and that the HTML was written via `lib.pages.write_page` (contains the data-base shim `write_page` injects).

On this head that new test file is RED (template missing; `main()` does not write HTML). After the change it must be GREEN:

```sh
python3 -m pytest -q tests/test_am_edition_page.py tests/test_am_edition_producer.py
# expected GREEN; no data/ tree required
```

RETURN FORMAT (PR body):
- WHAT CHANGED: the Morning Edition HTML page, the producer now writing it on the existing render step, the public-nav card, the registry archetype.
- HOW VERIFIED: paste the RED python snippet run on the parent, then the GREEN pytest command + output.
- LEDGER ROW + proposed move: `MO-PAID-011` capability_state_c2 `NOT_BUILT` → `BUILT_NOT_PROVEN`.
- LIVE-PROOF plan: after merge + one daily/render run, `GET https://www.mastermind-x.com/am_edition.html` → HTTP 200; body contains the Morning Edition heading and an `aibrief.html` link; `GET https://www.mastermind-x.com/am_edition.json` still serves `schema: am_edition.v1`. Paste status + a 20-line body excerpt.

TIER: MINIMAX_ELIGIBLE (one objective, five constraints, owned files listed, gate executable without `data/`).

LEDGER MOVE ON MERGE+LIVE: capability_state_c2 `NOT_BUILT` → `BUILT_NOT_PROVEN` on merge of this PR; `BUILT_NOT_PROVEN` → `DONE` when the live GET above succeeds.

AUTHORITY: ledger `authority_ceiling=display_only`. The one thing the executor must NOT add: any score, rank, confidence, gate, size, or trade language — including re-using Prophet, ENTRY_OPEN, or a new briefing model.

---

### MO-DELTA-010 — [MO-B F01-2] Glossary already catalogs dashboard readings
DISPOSITION: RECORDS_MOVE (absorbed by the glossary child MO-DELTA-011 / #6909 on this head; do not re-decompose open #7125)

EVIDENCE NOW:
- Ledger wants “catalog page over `docs/site_semantics` + dashboard cross-links” / acceptance “a rendered indicators-catalog page live on the render path”. Command: `rg '^MO-DELTA-010,' research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv`.
- Substrate exists: `ls docs/site_semantics/` → `china.md china_stocks.md etfs.md macro.md stretch_oracles.md us_stocks.md` (six files, matching the ledger).
- `lib/glossary.py:1-7,51-57,80-85,100-105` — every term binds to a heading in those six files and carries `page_href` to the matching dashboard (`macro.html`, `us_stocks.html`, `china.html`, `china_stocks.html`, `etfs.html`, `measurement.html`). Command: `sed -n '1,7p;51,57p;80,85p;100,105p' lib/glossary.py`.
- `python3 -c "from lib.glossary import GLOSSARY_TERMS, GLOSSARY_MIN_TERMS; print(len(GLOSSARY_TERMS), GLOSSARY_MIN_TERMS)"` → `54 50`.
- `templates/glossary.html.j2:10-13,153-157` — public page; each term renders a dashboard cross-link `<a class="gl-src" href="{{ term.page_href }}">`. Command: `sed -n '10,13p;153,157p' templates/glossary.html.j2`.
- Render lane: `scripts/build_public_pages.py:141-147` writes `site/glossary.html` from `glossary_view_model`. Command: `sed -n '138,147p' scripts/build_public_pages.py`.
- Nav: `templates/_public_nav.html.j2:36` “Glossary / 词汇表 — Every reading on the dashboards, in plain words.” Command: `sed -n '36p' templates/_public_nav.html.j2`.
- `git log -p` on `templates/glossary.html.j2` / `lib/glossary.py` (this session): the template is a bilingual catalog with `page_href` dashboard chips; `lib/glossary.py` fail-closes unless `source_file` starts with `docs/site_semantics/` and `page_href` is a relative `.html`. (Follow-log first-parent attributes a later nightly touch at `6367d46a`; the files are present on this `origin/main` head. Program map records the glossary child as #6909 / B-F13-1. Open #7125 is MO-DELTA-011 and is out of this commission.)
- Adjacent but **not** this substrate: `scripts/build_market_reference.py:1-10,130` builds `reference.html` from `config/market_reference.yml` (`ALLOWED_KINDS = {indicator, glossary}`), not from `docs/site_semantics/*.md`. Do not treat that page as this row's remaining work.
- Fixture tests green: `tests/test_glossary.py:24-37` (term count + source-heading bind) in the 225-pass run.

LEDGER MOVE ON MERGE+LIVE: granular_disposition `PROJECTION_ONLY` / capability_state_c2 `NOT_BUILT` → `EXACT_EQUIVALENT` of the glossary child (MO-DELTA-011), capability_state_c2 `BUILT_NOT_PROVEN`. After live proof of `/glossary.html`: `DONE` for this row (absorbed). Live readback: `GET https://www.mastermind-x.com/glossary.html` lists ≥50 terms, each with a dashboard `*.html` chip.

AUTHORITY: `reference_only`. Do not add a second vocabulary store or a parallel indicators catalog.

---

### MO-PAID-067 — [MO-B F09-1] Capital Structure already shows dated policy steps
DISPOSITION: RECORDS_MOVE

EVIDENCE NOW:
- Ledger: `PROJECTION_ONLY` / `PARTIAL` / `real_consumer=untraced` / next child “wire policy engines into one capital-markets page”. Command: `rg '^MO-PAID-067,' research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv`.
- Producers exist: `engine/policy_calendar.py:1-30,70-73` (Federal Register theme calendar, display-only); `engine/foresight_cascade.py:1-18` (thematic stage machine, display-only). Command: `sed -n '1,30p;70,73p' engine/policy_calendar.py; sed -n '1,18p' engine/foresight_cascade.py`.
- Capital-markets page family on disk: `templates/capital_structure.html.j2`, `templates/macro_capital_structure.html.j2`, `templates/bonds.html.j2`, `templates/_debt_maturity.html.j2`. Command: `ls templates/capital_structure.html.j2 templates/macro_capital_structure.html.j2 templates/bonds.html.j2 templates/_debt_maturity.html.j2`.
- `templates/capital_structure.html.j2:111-165` — B-F09-6 Policy watch chip **and** B-F09-6b “Dated steps on the public record” / six windows; comments name `MO-PAID-067`. Command: `sed -n '111,165p' templates/capital_structure.html.j2`.
- `engine/capital_policy_projection.py:1-8,25-65` — projection over `engine.policy_calendar` + cached event calendar into six frozen windows; no new signal. Command: `sed -n '1,8p;25,65p' engine/capital_policy_projection.py`.
- `scripts/build_capital_structure_page.py:14-15,53,77-80,178-197` — builder cites `compute_policy_calendar` for the chip and `capital_policy_projection.project` for the section. Command: `sed -n '14,15p;53p;77,80p;178,197p' scripts/build_capital_structure_page.py`.
- `foresight_cascade` current consumers: `scripts/build_foresight.py:117-133,324,349` writes `site/foresight.html` + `site/basketdata/foresight_cascade.json`; `rg -l foresight_cascade templates` → **none**. Thematic cascade stays on the foresight desk, not a second capital-markets signal. Acceptance test “a capital-markets page cites a policy_calendar/foresight_cascade projection” is met by the policy_calendar projection on `capital_structure.html`.
- `templates/foresight.html.j2:747-769` — the general (non-capital) policy_calendar consumer. Command: `sed -n '747,769p' templates/foresight.html.j2`.
- Fixture tests green: `tests/test_capital_policy_projection.py` in the 225-pass run.

LEDGER MOVE ON MERGE+LIVE: capability_state_c2 `PARTIAL` → `BUILT_NOT_PROVEN`; rewrite `real_consumer` from `untraced` to `templates/capital_structure.html.j2` (`#cs-policy` + `#cs-policy-projection`). After live proof: `DONE`. Live readback: `GET https://www.mastermind-x.com/capital_structure.html` contains `id="cs-policy"` and `id="cs-policy-projection"` / “Dated steps on the public record”.

AUTHORITY: `context_only`. F09 row-accounting repair still binds: do not sum par vs outstanding; do not join issuers by name/theme. Do not import foresight_cascade stages (PRECIPICE/BROADENING/…) onto this page — that would be a new signal.

---

### MO-DELTA-032 — [MO-B F02-1] Policy Watch already shows proposal-to-enforcement stages
DISPOSITION: RECORDS_MOVE

EVIDENCE NOW:
- Ledger: `NEW_BOUNDED_BUILD` / `SPEC_ONLY` / “no state-machine code found”. Command: `rg '^MO-DELTA-032,' research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv`. That sentence is stale.
- `engine/policy_intent_desk.py:508-528,598-623,745,908-917` — deterministic (no LLM) lifecycle block: stages `proposed → passed → in_force → enforced`, terminals `withdrawn/struck_down/superseded`, append-only store `data/policy_lifecycle/events.jsonl`, `ingest_lifecycle()`, `fold_lifecycle()`, `lifecycle_view()`. Command: `sed -n '508,528p;598,623p;745p;908,917p' engine/policy_intent_desk.py`.
- `config/policy_lifecycle_seed.json:1-8` — operator-signed seed substrate (not a second event DB). Command: `sed -n '1,8p' config/policy_lifecycle_seed.json`.
- `scripts/build_policy_watch.py:456-477` — nightly ingest + `lifecycle_view` passed into the template. Command: `sed -n '456,477p' scripts/build_policy_watch.py`.
- `templates/policy_watch.html.j2:660-694` — “Policy stages” / “政策进程” column with counts and per-item `data-state`. Command: `sed -n '660,694p' templates/policy_watch.html.j2`.
- MiniMax-eligible first slice named in the commission (pure state-machine module + RED-first tests + one rendered column) **already exists** on this head: `tests/test_policy_lifecycle.py:1-51` is fixture-only, asserts `proposed→passed→in_force→enforced`, and is in the 225-pass run. Command: `sed -n '1,51p' tests/test_policy_lifecycle.py`.
- F02 owner-ambiguity on MO-PAID-006 does **not** block this row. Ledger `MO-PAID-006` missing contract is “political/institutional dossier layer” on country pages (`engine/intl_risk.py` + `templates/intl.html.j2`), not lifecycle. Command: `rg '^MO-PAID-006,' research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv`. The owner map `research/market_intelligence_productization/MARKET_ONTOLOGY_F02_OWNER_SOURCE_RIGHTS_MAP_2026-09-05.md:12-16,45-48` already names `engine/policy_intent_desk.py` as Owner A of policy lifecycle and `engine/international_macro_dashboard.py` as owner of the 006 dossier. Different jobs.

LEDGER MOVE ON MERGE+LIVE: capability_state_c2 `SPEC_ONLY` → `BUILT_NOT_PROVEN`; rewrite `state_delta` (the “no state-machine code found” clause is false on `9a4a389c`). After live proof: `DONE`. Live readback: `GET https://www.mastermind-x.com/policy_watch.html` contains “Policy stages” / “政策进程” and at least one `data-state` in `{proposed,passed,in_force,enforced,withdrawn,struck_down,superseded,unknown}`.

AUTHORITY: `context_only`; deterministic owner-governed joins; LLM summarizes non-authoritatively over cited inputs. The lifecycle fold itself must stay LLM-free (already true at `policy_intent_desk.py:508-511`). Do not add confidence numbers as authority, and do not create a second event database.

---

## Operator notes (not contracts)

- DONE remains merged **and** live-verified. This session could not curl the live site (network forbidden), so no row is moved to `DONE` here — only `BUILT_NOT_PROVEN` via a records PR, except MO-PAID-011 which still needs the page.
- `engine/foresight_cascade.py` is a thematic stage producer consumed by `scripts/build_foresight.py`, not by Capital Structure. Wiring it onto the capital-markets page would be a new signal and is out of MO-PAID-067's remaining work.
- Frequencies-never-confidence and Charter P7 (no second stores / control planes) are already obeyed by the landed code cited above; the one remaining MiniMax PR must keep them.
