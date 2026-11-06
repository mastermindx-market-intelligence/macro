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
| J04 | Cycles R4 specimen (`design_refs/sector-paper-20261021/cycles_repair/build_cycles.py`), `tests/test_cycle_ontology.py`, `engine/cycle_ontology.py`. **Verifier C blocker:** the in-shell Cycles workspace (rail Explore → Cycles, Dossier Cycle tab) does not exist on HEAD; the legacy `/sector_cycles.html` is unchanged; C-rows 0 CONFIRMED / 22 PARTIAL / 13 NOT_DELIVERED / 7 UNSUPPORTED. Masterplan P15/P17 (SIC-I03/I09B) unmet. | BLOCKED (downgraded by Verifier C) |
| J05 | Time Machine mount cells (`#tm-mount` ×6). Live boundary/seek/recovery behaviour is SIC-APR-03 (live Time Machine) at the production proof. | PENDING_LIVE |
| J06 | Dossier cells (`sectors/XLK.html` ×6); native company/ETF destinations are existing routes; membership/source-date independence per `B01_OWNERSHIP_MAP.md` §1. Not evidenced: open-and-return, overlapping theme and unavailable-membership cases (P22). Verifier C residual: the Dossier Cycle-tab port (U07) is NOT_DELIVERED. | PARTIAL |
| J07 | Lenses cells (`#moving` ×8) carry Participation; numerator/denominator/expected-population semantics per `B04_METRIC_DEFINITIONS.md`, parity `B12_HAZARD_PARITY.md`. Not evidenced: the four scenario cases as interactions (P22). | PARTIAL |
| J08 | Money/Explore/Confluence cells (`#money`, `#explore`, `#confluence` ×2 each) + `#moving`. Declared block: SC-066 BLOCKED_DATA (basket_confluence.json carries only n_baskets, no gate). | PARTIAL (declared block) |
| J09 | Access tiers: SIC-APR-02 (auth/premium settlement) binds the production proof; state matrix `no_access`/`locked`/`unauthorized` NOT YET PRODUCED on explore/dossier/research/cycles (declared gap, section C). | PENDING_LIVE (gap declared) |
| J10 | Research mount cells (`#tm-mount` ×6); saved investigations API `templates/watchstore.js` (`saveSectorInvestigation`/`listSectorInvestigations`, SIC-I07R). Not evidenced: editor identity hand-off, language switch, refresh persistence (P22). | PARTIAL |
| J11 | Watches cells (`#accumulation-section` ×5); account-owned watch API in `templates/watchstore.js` (F04 read-only overlay merged from main). Not evidenced: account change / reopen / remove (P22). | PARTIAL |
| J12 | State matrix: 60 of 102 board×state rows PRODUCED (`state_matrix.csv`); the 42 NOT YET PRODUCED rows are the declared gap (section C). Late-response / revision-boundary behaviour: P22. | PARTIAL (gap declared) |
| J13 | 46 cells (31 coverage + 15 compositions), theme/lang took effect on every cell, no horizontal overflow at 1440/390; three J13-width overflows recorded as production facts (`w320-rotation`, `w320-cycles`, `w430-cycles`), not repaired. Keyboard/touch/zoom/reduced-motion: not evidenced here. Verifier C residual: the Cycles cells exist dark-EN only (no light/ZH/1440/390 for the legacy page) and every cell was captured at d86344b9, pre-merge. | PARTIAL |
| J14 | Scientific disposition: `research/cycle_masterplan/W42_HAZARD_VERDICT.md` (hazard 4/6 qualified; up/3m, up/6m PRIOR), `W46_BINDING_CALIBRATION_VERDICT.md` (sizing 1.0), `W51_LEADLAG_VERDICT.md` (STOP), `B12_HAZARD_PARITY.md` (PARITY_FAILS recorded, not repaired); grader ~0.274 hit rate is not a win rate. Isolated replay countercases on the candidate: not evidenced here. | Verifier C residual: the Record/Methods surface is not a mounted view on HEAD (SC-035); the C19 MODEL badge is unqualified by the PARITY_FAILS claim. PARTIAL |
| J15 | Release preparation only: #9917 ready, main merged, RIG approved, CI pending at this head. Served identity chain and the next natural update are P21/P22. | PENDING_BY_DESIGN |

Verifier C's journey verdicts (`p19/verifier_C_C-U-journeys.md`): 14 UPHELD, J04 DOWNGRADED to BLOCKED.

## C. Declared gaps (named, not hidden)

1. 42 design state-matrix rows NOT YET PRODUCED on the candidate (brief 4, explore 3, dossier 11, research 12, watches 6,
   cycles 6 — `state_matrix.csv` `status`), concentrated in corrected/abstained/no_access/offline/unauthorized/locked/
   empty_search/uncertain_command/incompatible_generation states.
2. SC-066 and SC-092 BLOCKED_DATA (producer-field dependencies; interim rendering declared in `proposal.yml`).
3. Three J13-width overflows recorded as production facts (`evidence/README.md`).
4. Interaction-level journey proof (Back/Forward, compare, save/remove across accounts, Time Machine seeks, access tiers,
   late responses) is P22 on the served product; nothing above claims it.
5. **Undeclared by the seat, found at P19 (Verifier C):** the Sector Cycles in-shell workspace is NOT DELIVERED on HEAD
   (P15/P17, SIC-I03/I09B); the BOARD CLAIM OPEN rows C02, C03, C05, C17, C21 stay open; C19's MODEL badge is unqualified by
   the recorded PARITY_FAILS claim (`engine/cycle_rhythm.py` publishes it, `templates/sector_cycles.js` ignores it).
6. **Undeclared by the seat, found at P19:** the SIC-APR-04 path was live — `engine/index_leadership_track.py:257` can emit
   `validated` and `trackBox` printed it; repaired at P20 (`Measured` / `已实测`, test-pinned); discharge is the P22 readback.
7. **Evidence identity:** every cell was captured at d86344b93a0b, before the main merge; P22 re-captures on the served build.
8. **P20 source repairs (behaviour changed, fresh review required before P21):** `templates/subsectors.js` basket denominator
   (SC-066), `templates/sector_central.html.j2` trackBox wording (SIC-APR-04), `.github/ci/legacy-jobs.yml` wiring of four
   dark sector-paper suites, `tests/test_ci_pack.py` ceilings funded +9 to the measured values.

## D. What the verifiers are asked

Attack sections A and B against the candidate head: every pointer must resolve on HEAD; every `candidate_stage_claim` must
be supportable from the named source/evidence or be marked UNSUPPORTED with the reason; every IMPROVE row must receive a
verdict of DELIVERED / PARTIAL (residual named) / NOT_DELIVERED on the merged head; any journey status overstated must be
downgraded with the reason. Returns are stored byte-exact under `p19/`.

## E. Outcome (P19 disposed, P20 repaired — 2026-11-02)

Verifier returns (byte-exact, `p19/`): A `1cac9dd8…f23292` (R3A-01..46: 42 CONFIRMED / 3 UNSUPPORTED / 1 PARTIAL), B
`bb12e30e…53ee90a` (R3A-47..92: 39 CONFIRMED / 5 UNSUPPORTED / 1 PARTIAL / 1 BLOCK_CONFIRMED), C `50b0025c…645288` (C/U rows
+ J01–J15: 0 CONFIRMED / 22 PARTIAL / 13 NOT_DELIVERED / 7 UNSUPPORTED; J04 BLOCKED). The 134-row CSV now carries every
verdict verbatim (80 CONFIRMED, 24 PARTIAL, 15 UNSUPPORTED, 13 NOT_DELIVERED, 1 CONFIRMED-with-contract-gap, 1
BLOCK_CONFIRMED). Row-level dispositions and the P20 repairs are the ledger block `p19_p20_dispositions_20261102` in
`research/reference_integrity/sector-intelligence-cycles-20261021/proposal.yml`.

**Split disposition.** The Sector Central half (shell, router, Brief/Rotation/Lenses/Money/Explore/Confluence/Dossier/
Research/Watches, the engines B01–B13 and the approved design reference) is candidate-accepted with the residuals above.
The Sector Cycles replacement is **NOT DELIVERED**: no in-shell Cycles workspace exists on HEAD, so J04 is BLOCKED and
P10/P15/P17 remain owed. #9917 may therefore land only as a **PARTIAL release** of the Sector Central half plus CI wiring,
after the fresh P20 source review and binding CI; that merge is never described as the programme's completion. The Cycles
build wave (SIC-I03/I09B against the approved `cycles_ia.md`, with C19 badge qualification, U07 Dossier port, typed states
and light/ZH/1440/390 cells) is commissioned next, followed by P22 production/natural-update proof on both served surfaces
and P23's separate acceptances. This note is seat-authored; the independent part is the verifier receipts.

**P20 source review (Reviewer D, 2026-11-02).** The fresh READ_ONLY review of the P20 diff (`p19/verifier_D_P20_source_review.md`,
`980f84be…326e04`) returned ACCEPT-WITH-NOTES: every repair clears the CI failure it names, no guard is weakened, nothing touches
GMI (0 paths differ from main 838a69c08deb). Its one MAJOR finding — the `templates/subsectors.js` repair added three lines and
shifted four frozen state-matrix citations (csv rows 19/26/33/34, md 62/69/74/75) — is repaired line-count-neutral in the same
commit as this paragraph (582 lines; `:309/:496/:506/:508` carry the cited content again; the design reference is untouched).
The reviewer located R3A-75 (`engine/subsector_confluence.py:270-271` sort; `templates/subsector_detail.html.j2:191,194`
producer order), confirmed R3A-47 (adding `templates/desk_watch.js:20-21`) and R3A-52, and left R3A-86 CONFIRMED-PARTIAL
(Overview at `:1496`; runtime destination order is P22's). Residuals it names for P22 rather than repair: the merged P0B
receipts were never re-measured on the merged tree; the research-vault textarea restyle and the Measured/已实测 badge have no
dual-theme/ZH visual evidence; `templates/sector_central.html.j2:2280` still carries the word 'validated' inside the
board-ordering receipt tooltip (inherited from main, not forward-track-record wording — for the P22 observer, see ledger
`P20-SIC-APR-04`). The reviewer re-confirmed the release scope: #9917 lands only as the PARTIAL Sector Central release.
