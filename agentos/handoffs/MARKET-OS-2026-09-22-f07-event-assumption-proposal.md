---
workstream: "WS:MARKET-OS"
session: claude/f07-event-assumption-proposal
model: opus
ended_because: complete
mission: >
  F07 — let a source-grounded company event produce a typed, explainable, NON-AUTOMATIC
  proposed valuation-assumption change that the existing scenario engine can evaluate,
  without letting an event set a number it is not entitled to.
state_before: >
  B-F07-1 (engine/valuation_scenario.py, V1 AAPL), B-F07-2
  (engine/valuation_assumptions.py, three user controls) and B-F07-3
  (engine/valuation_event_bridge.py, closed event-class -> target map) were all merged.
  The bridge carried a class and a direction word only: no event identity, no source
  refs, no typed abstention, no engine consumption, no double-count law. For AAPL the
  bridge resolved to null, so the panel's only event line was the false sentence
  "No filing on file yet for this company."
changed:
  - path: engine/valuation_event_proposal.py
    what: "NEW. assumption_change_proposal.v1 + assumption_change_scenario.v1: typed proposal or typed abstention, rights gate, point-in-time law both directions, stored-proposal binding, shadow evaluation through the EXISTING per_share_at."
  - path: engine/valuation_assumptions.py
    what: "controls_blob gains event_assumption_proposal + event_assumption_scenario and an optional as_of; latest_issuer_event_record distinguishes a broken reader from an issuer with no events; guidance hits are read through their owner, not a second parquet read."
  - path: engine/guidance_gap.py
    what: "NEW public hits_for_ticker() so the F07 consumer reads the owner's validated frame instead of opening data/edgar/guidance_hits.parquet itself."
  - path: templates/_valuation_assumptions.html.j2
    what: "Proposal block (plain words, bilingual, governed CSS, both theme art directions) + the bridge line now yields to it and no longer claims 'no filing on file' above a filing it links."
  - path: scripts/build_stock_library.py
    what: "Passes rec['asof'] as the build's point-in-time ceiling."
  - path: research/F07_EVENT_ASSUMPTION_PROPOSAL_CONTRACT_V1.md
    what: "NEW. The frozen contract, its invariants, and why B-F07-3 is preserved rather than redone."
  - path: tests/test_valuation_event_proposal.py
    what: "NEW. 48 tests pinning every invariant, both abstention controls, the rights gate in BOTH directions, and the panel copy."
verified:
  - claim: "The whole valuation suite passes, including the pre-existing bridge and scenario tests."
    command: "python3.12 -m pytest tests/test_valuation_event_proposal.py tests/test_valuation_assumptions.py tests/test_valuation_event_bridge.py tests/test_valuation_scenario.py -q"
    result: "115 passed"
  - claim: "AAPL's real latest event yields a typed abstention, not a number."
    command: "python3.12 -c \"from engine import stock_fundamentals as sf, valuation_scenario as vs, valuation_assumptions as va; cb=va.controls_blob(vs.compute(sf._load_statements()['AAPL'],ticker='AAPL')); print(cb['event_assumption_proposal']['status'], cb['event_assumption_proposal']['abstain_reasons'])\""
    result: "INSUFFICIENT ['reported_result_not_an_assumption', 'payload_not_licensed', 'no_source_ref', 'event_class_unmapped']"
  - claim: "A real SEC 8-K guidance raise yields a lawful proposal and a shadow delta through the existing math."
    command: "same, ticker CTVA"
    result: "PROPOSED, sales_growth_pct 3 -> 7 (magnitude_source=model_preset), per share 30.18 -> 31.35"
  - claim: "The source link this code mints resolves and contains the quoted phrase."
    command: "curl -sI https://www.sec.gov/Archives/edgar/data/1755672/000175567226000022/a2q_2026xearningsxnewsxr.htm ; then tag-strip and grep the body"
    result: "HTTP/2 200; 'we are raising our full-year guidance' found at offset 3307"
  - claim: "The design ratchet blocks nothing on the added lines."
    command: "python3 scripts/check_design_system.py --self-check && --mode enforce-added; scripts/check_ui_visual_evidence.py --selftest; scripts/check_runtime_style_injection.py"
    result: "self-check OK; blocking=0; selftest OK; runtime style injection OK"
  - claim: "agentos records validate."
    command: "python3 scripts/agentos.py validate"
    result: "1177 records — 0 error(s)"
  - claim: "Panel renders correctly in both themes and both languages with real data."
    command: "rendered _valuation_assumptions.html.j2 for CTVA and AAPL, served via the site-static preview, screenshotted dark/light x EN/ZH"
    result: "proposal block renders with source link in both themes; AAPL shows the plain-word abstention in EN and ZH; no machine slugs in copy"
unverified:
  - claim: "Behaviour on a live rendered ticker page in production."
    what_would_verify: "After merge, the render lane bakes site/stocks/AAPL.html; open it and confirm the abstention line replaced 'No filing on file yet for this company.' AAPL is the only V1-pinned issuer (_VS_TICKERS), so AAPL is the only page that changes."
unresolved:
  - "engine/capital_structure imports fail closed under Python 3.14 (bytecode-digest pin computed for CI's 3.12.13). Local work on this seam needs python3.12. Not caused here and not in scope; it is a W2C/#6415 lane matter."
  - "`earnings` — 82% of chronicle rows — remains absent from engine/valuation_event_bridge.py's class map. It is now TYPED as a reported result rather than falling through silently, but no corporate-action class map entry was added."
next_actions:
  - "After merge, verify the baked site/stocks/AAPL.html carries the abstention sentence (see unverified above)."
  - "If a consensus source is ever licensed, DEC:F07-VALUATION-SOURCE-IS-SEC-COMPANYFACTS-V1 is the record to supersede; the rights gate here reads payload text, so widening it is a one-place change (_CONSENSUS_MARKERS)."
  - "To extend beyond AAPL, widen _VS_TICKERS in scripts/build_stock_library.py — the proposal path is already issuer-generic and was exercised on CTVA."
do_not_redo:
  - "Do NOT rebuild engine/valuation_event_bridge.py's class->target map. It is merged, correct for what it governs, and is reused here as the DIRECTION_ONLY path."
  - "Do NOT let an event supply a magnitude. See DEC:F07-EVENT-PROPOSES-DIRECTION-MODEL-OWNS-MAGNITUDE; an assertion in _build enforces it and a test pins it against a phrase that contains numbers."
  - "Do NOT try to make AAPL produce a numeric proposal. See DSC:AAPL-HAS-NO-LAWFUL-EVENT-FOR-A-VALUATION-ASSUMPTION — abstention IS the correct AAPL result."
  - "Do NOT add a consensus/estimates source, an earnings store, or a financial-statement store to reach a number; all four are NO-GO for this lane."
  - "Do NOT reintroduce 'No filing on file yet for this company.' as the AAPL line — it is false, and that was the defect this PR fixed."
danger_areas:
  - "valuation_assumptions.py is guarded by tests/test_valuation_assumptions.py::test_module_is_pure, which bans 'open(', 'requests', 'read_parquet', 'datetime.now' and 'Path(' from the SOURCE TEXT. Read new data through an owning module's reader."
  - "The controls blob is serialized into the page, so every field name and string in it is front-facing. Refutation vocabulary is banned there too — that is why the field is what_would_change_this, not falsifier."
  - "Tests that assert on rendered HTML must scope to the element, not the whole document: the embedded controls JSON legitimately contains field values and control keys that read like leaks."
prs: []
decisions:
  - "DEC:F07-EVENT-PROPOSES-DIRECTION-MODEL-OWNS-MAGNITUDE"
discoveries:
  - "DSC:AAPL-HAS-NO-LAWFUL-EVENT-FOR-A-VALUATION-ASSUMPTION"
---

## Why AAPL abstains, in one paragraph

AAPL is the only issuer V1 valuation is pinned to, and it has no event this product may
lawfully turn into a number. Its five chronicle events are all quarterly earnings; the
only figures attached to them are EPS measured against a consensus estimate, which
DEC:F07-VALUATION-SOURCE-IS-SEC-COMPANYFACTS-V1 forbids as a valuation input, and their
`links.source` is null so there is nothing a user could open. Its capital-structure
classified spine is empty and it has no 8-K guidance hits. The honest output is therefore
a typed abstention naming every reason — which is what ships. The positive path is proven
on CTVA, whose 8-K of 2026-07-30 says, in the filed document, "we are raising our
full-year guidance".
