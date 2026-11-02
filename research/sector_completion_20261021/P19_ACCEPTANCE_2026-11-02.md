# P19 — independent integrated acceptance packet (candidate stage), 2026-11-02

Programme macro #7646 · PR #9917 · candidate head `ec1f1ea694d5442e773b6158ce0cbad1385677fe` (main `f125051fdb37` merged) ·
RIG `sector-intelligence-cycles-20261021` approved at frozen `4161d404` (verdict 9 `APPROVE_WITH_CONDITIONS`, `approval.yml`).

This packet is the seat's **claim set** for the masterplan's P19 row (Wave 4: full capability disposition and candidate-stage
J01–J14 review, plus J15 release preparation). It is not acceptance. Two independent READ_ONLY verifiers attack it and their
byte-exact returns are stored under `p19/`; P20 repairs only material findings; P21 (merge) waits on P19/P20. Served-user and
natural-update proof (J15, P22) stays PENDING by design and nothing here claims it.

## A. Capability disposition (134 rows)

`P19_CAPABILITY_DISPOSITION_2026-11-02.csv` joins, per matrix row: the 2026-10-21 capability matrix row; the RIG proposal's
disposition for it (`proposal.yml` `dispositions:` — SC-nnn ↔ R3A-nn, C01–C28, U01–U14; census RETAIN 88 / IMPROVE 37 /
RELOCATE 7 / BLOCKED_DATA 2); the design state-matrix rows that cite it (`design_refs/sector-paper-20261021/state_matrix.csv`,
48 rows cited); the production evidence cells of its target family (`research/reference_integrity/sector-intelligence-cycles-20261021/evidence/cells.yml`,
46 cells captured on the render tree at `d86344b93a0b`; 90 rows have a family cell); a `candidate_stage_claim` derived only
from the proposal disposition; `served_proof` = PENDING_P22 for every row. `verifier_verdict` / `verifier_note` are empty for
the verifier. The `*_to_record` columns of the matrix itself stay blank until P23.

## B. Journeys J01–J15 — candidate-stage evidence and status

Status vocabulary: `EVIDENCED` (static or interaction evidence exists on the candidate; pointer named) · `PARTIAL` (part
evidenced, the rest named) · `PENDING_LIVE` (bound to a production condition SIC-APR-nn or to P22) · `PENDING_BY_DESIGN`.

| J | Candidate-stage evidence (pointers) | Status |
|---|---|---|
| J01 | Brief R4 specimen boards (`coverage_matrix` Brief cells, `design_refs/sector-paper-20261021/brief_repair/`), `copy_deck.json` EN/ZH strings pinned by `tests/test_sector_paper_copy_deck.py` (SIC-V8-C02 stopword form), width cells `w320/w430/w768-brief-dark-en`; partial snapshot: state matrix `brief:partial` PRODUCED. Not evidenced: a cold reader's task completion (P22). | PARTIAL |
| J02 | Router inventory `templates/si_workspace.js` (`VIEWS`, `LEGACY_ANCHORS`); 31 coverage cells mount by hash with `hash`, `h1`/`title` and `asof` read back in `cells.yml`. Not evidenced: refresh/Back/Forward/return-from-stock preservation (P22). | PARTIAL |
| J03 | Rotation cells (`#map` ×9, 1440/390 × theme × lang) + selection capture `evidence/journeys/j03-map-select-zh-light-0.4x.jpg`; producer basis in `engine/sector_central.py` / `B04_METRIC_DEFINITIONS.md`. Not evidenced: compare-two-groups and list-search equivalence as an interaction (P22). | PARTIAL |
| J04 | Cycles R4 specimen (`design_refs/sector-paper-20261021/cycles_repair/build_cycles.py`, every visible string bound to deck/example/enum), width cells `w320/w430/w768-cycles-dark-en` (tab-row overflow at 320/430 recorded as a production fact), `tests/test_cycle_ontology.py`, `engine/cycle_ontology.py`. Thematic basket investigation: not evidenced as an interaction (P22). | PARTIAL |
| J05 | Time Machine mount cells (`#tm-mount` ×6). Live boundary/seek/recovery behaviour is SIC-APR-03 (live Time Machine) at the production proof. | PENDING_LIVE |
| J06 | Dossier cells (`sectors/XLK.html` ×6); native company/ETF destinations are existing routes; membership/source-date independence per `B01_OWNERSHIP_MAP.md` §1. Not evidenced: open-and-return, overlapping theme and unavailable-membership cases (P22). | PARTIAL |
| J07 | Lenses cells (`#moving` ×8) carry Participation; numerator/denominator/expected-population semantics per `B04_METRIC_DEFINITIONS.md`, parity `B12_HAZARD_PARITY.md`. Not evidenced: the four scenario cases as interactions (P22). | PARTIAL |
| J08 | Money/Explore/Confluence cells (`#money`, `#explore`, `#confluence` ×2 each) + `#moving`. Declared block: SC-066 BLOCKED_DATA (basket_confluence.json carries only n_baskets, no gate). | PARTIAL (declared block) |
| J09 | Access tiers: SIC-APR-02 (auth/premium settlement) binds the production proof; state matrix `no_access`/`locked`/`unauthorized` NOT YET PRODUCED on explore/dossier/research/cycles (declared gap, section C). | PENDING_LIVE (gap declared) |
| J10 | Research mount cells (`#tm-mount` ×6); saved investigations API `templates/watchstore.js` (`saveSectorInvestigation`/`listSectorInvestigations`, SIC-I07R). Not evidenced: editor identity hand-off, language switch, refresh persistence (P22). | PARTIAL |
| J11 | Watches cells (`#accumulation-section` ×5); account-owned watch API in `templates/watchstore.js` (F04 read-only overlay merged from main). Not evidenced: account change / reopen / remove (P22). | PARTIAL |
| J12 | State matrix: 60 of 102 board×state rows PRODUCED (`state_matrix.csv`); the 42 NOT YET PRODUCED rows are the declared gap (section C). Late-response / revision-boundary behaviour: P22. | PARTIAL (gap declared) |
| J13 | 46 cells (31 coverage + 15 compositions), theme/lang took effect on every cell, no horizontal overflow at 1440/390; three J13-width overflows recorded as production facts (`w320-rotation`, `w320-cycles`, `w430-cycles`), not repaired. Keyboard/touch/zoom/reduced-motion: not evidenced here. | PARTIAL |
| J14 | Scientific disposition: `research/cycle_masterplan/W42_HAZARD_VERDICT.md` (hazard 4/6 qualified; up/3m, up/6m PRIOR), `W46_BINDING_CALIBRATION_VERDICT.md` (sizing 1.0), `W51_LEADLAG_VERDICT.md` (STOP), `B12_HAZARD_PARITY.md` (PARITY_FAILS recorded, not repaired); grader ~0.274 hit rate is not a win rate. Isolated replay countercases on the candidate: not evidenced here. | PARTIAL |
| J15 | Release preparation only: #9917 ready, main merged, RIG approved, CI pending at this head. Served identity chain and the next natural update are P21/P22. | PENDING_BY_DESIGN |

## C. Declared gaps (named, not hidden)

1. 42 design state-matrix rows NOT YET PRODUCED on the candidate (brief 4, explore 3, dossier 11, research 12, watches 6,
   cycles 6 — `state_matrix.csv` `status`), concentrated in corrected/abstained/no_access/offline/unauthorized/locked/
   empty_search/uncertain_command/incompatible_generation states.
2. SC-066 and SC-092 BLOCKED_DATA (producer-field dependencies; interim rendering declared in `proposal.yml`).
3. Three J13-width overflows recorded as production facts (`evidence/README.md`).
4. Interaction-level journey proof (Back/Forward, compare, save/remove across accounts, Time Machine seeks, access tiers,
   late responses) is P22 on the served product; nothing above claims it.

## D. What the verifiers are asked

Attack sections A and B against the candidate head: every pointer must resolve on HEAD; every `candidate_stage_claim` must
be supportable from the named source/evidence or be marked UNSUPPORTED with the reason; every IMPROVE row must receive a
verdict of DELIVERED / PARTIAL (residual named) / NOT_DELIVERED on the merged head; any journey status overstated must be
downgraded with the reason. Returns are stored byte-exact under `p19/`.
