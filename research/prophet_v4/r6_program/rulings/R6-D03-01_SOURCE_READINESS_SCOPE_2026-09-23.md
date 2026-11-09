# R6-D03-01 — Seat ruling on D03 (real source histories and rights): usable scope

- Seat: Fable Meta-CEO 48cdfd56 (claude8) · operation `prophet-us-fable-meta-ceo-20260923-001` · parent #6805 · WS:PROPHET-US-V4-RECOVERY
- Date: 2026-09-23 · Status: RULED (evidence-conditional; §5) · Revision: v2 after an independent Opus read-only red-team of the draft (COMMIT WITH REPAIRS; one blocker, seven majors, ten minors — every one folded in below)
- Authority: D03 playbook — "Fable decides usable scope" (`research/prophet_v4/r6_fable_meta_ceo_handoff/DECISION_RESOLUTION_PLAYBOOK.md` §D03, steps 1–4, closure artifact, "no backdated current membership/events" at :40); B16 "Fable Duty: prioritize, settle blocked decisions, adjudicate exact evidence" and release limit "no alpha claim or outcome-selected sector choice; pilot qualification alone cannot admit a trade" (`effective/BUILD_PROGRAM.md` §B16).
- Evidence consumed (both independent-review PASS at their heads):
  - Cycle: `research/prophet_v4/r6_program/wave2/D03_CYCLE_SOURCE_READINESS_CENSUS_2026-09-23.md` (PR #7836 @ 68ece597)
  - Issuer/event: `research/prophet_v4/r6_program/wave2/D03_ISSUER_EVENT_SOURCE_READINESS_CENSUS_2026-09-23.md` (PR #7837 @ 6c0539e2)
  - Red-team measurement (read-only `git show origin/main:<path>` of tracked blobs, not a lane receipt; B16-a re-receipts it): `data/fred_vintage/vintages.parquet` holds all 17 census series (54 total); `data/baskets/membership_history.parquet` first snapshot 2026-08-13 (3,114 rows to 2026-09-04); `data/themes_heatmap/tree_history.jsonl` two lines, first asof 2026-07-05.
- Not consumed, by design: any strategy return, trade outcome or protected outcome artifact. Both censuses were run before return inspection and this ruling preserves that order.

## 1. The admission rule is ratified verbatim (binding for every Cycle proving-domain decision)

The Cycle census §Q5 readiness rule is the D03 admission rule, quoted in full. "A proving domain may enter pilot only if all five pass:"

1. **Vintage depth/clock:** at least two independent economic mechanisms have source legs with measured source-vintage history of at least 120 post-first-release months over the preregistered window. Admission uses source observation/publication clocks; a modeled lag may stress but never create an available date. Missing or late vintage rows block, not silently fall back.
2. **Mapping at cut:** issuer or segment membership at each decision cut is genuinely observed from a dated source, or the domain is declared macro-only. Current membership/sector/concept maps may never be backdated.
3. **Failure coverage:** the decision universe includes failed/delisted issuers at that cut, or the study is explicitly macro-only and reports survivorship as a limit.
4. **Definition tolerance:** every NAICS/benchmark/reclassification/seasonal-method/discontinuity is dated and handled by era split, declared diagnostic-only splice, or exclusion. Broad series may never be relabeled as granular subthemes.
5. **Rights:** acquisition, processing, storage, model use and user redistribution are each resolved; internal-only or unresolved sources support private diagnostics, never public pilots.

Seat additions, binding: (i) "independent economic mechanisms" is adjudicated by the seat in the B16-b admission ruling against rule 4's no-relabel clause — the configured legs are capital-goods and total-manufacturing grain, and none may be counted as a machinery mechanism by relabeling; (ii) the **preregistered window** is proposed by B16-a from source clocks alone and ratified by the seat in the B16-b ruling before any return is inspected — an outcome-selected window is a B16 release-limit violation; (iii) readiness is decided on source clocks, vintage depth, definition continuity, mapping/coverage and rights — never on returns. A domain that fails is "not pilot-ready", never "no alpha".

## 2. Cycle proving domain: NONE admitted on current evidence

| Candidate | Rule 1 vintage depth | Rules 2–3 mapping / failures | Rule 4 definitions | Rule 5 rights | Verdict |
|---|---|---|---|---|---|
| (a) Industrial capital goods / machinery (the census's R4-recommended primary candidate) | Census: UNKNOWN in its sparse tree. Red-team measurement on the tracked store: NEWORDER first vintage 1997-03-26 (354 periods), ISRATIO 1997-04-15 (354), AWHMAN 1997-01-10 (357), PERMIT 1999-09-17 (325), AMTMUO 2011-07-05 (183), CAPUTLG3344S 2022-09-15 (49); largest gap one month; release lags 31–74 days. Depth ≥120 months is therefore plausible for several legs, pending B16-a's receipt and the independent-mechanism adjudication under §1(i). Granular M3 machinery series exist publicly but are not repo-configured. | FAIL on measured first dates: membership history begins 2026-08-13, theme tree history 2026-07-05; no historical issuer mapping or failed-issuer coverage at any earlier cut | conditional PASS after era treatment (Census SIC→NAICS and benchmark breaks dated) | NOT resolved: FRED public-domain tags are favorable per series but exact redistribution terms beyond the tag are UNKNOWN, CMRMTSPL carries a copyrighted tag, and Census redistribution and historical segment rights are unresolved — no leg may be assumed public-domain | NOT PILOT-READY; prospective collection + retrospective diagnostic |
| (b) Semiconductor equipment | FAIL/unverified; M3 semiconductor subtheme discontinued Apr-2010; no equipment-specific orders/shipments legs | FAIL — theme snapshots only (same measured first dates) | conditional PASS by refusing the post-2010 M3 subtheme and broad-series relabeling | not pilot-sufficient | NOT PILOT-READY; macro-only prospective diagnostic |
| (c) Building products / residential construction (mechanism breadth exists structurally at macro level) | FAIL — PERMIT is measured above, but starts/HPI/mortgage are not in the vintage set | FAIL — XHB is a current monitor, not membership history | FAIL — no rebaseline treatment assembled | not pilot-sufficient | NOT PILOT-READY; macro-only prospective diagnostic |

Ruling: **no Cycle pilot domain is selected.** (a) stays the primary candidate on the census's R4 recommendation; (b) and (c) stay documented alternatives under the same rule. Nothing in this table may be revisited by inspecting returns.

## 3. B16 is redirected: qualification means producing the closure matrix, read-only, from named tracked paths

B16's outcome ("a proving domain is selected") cannot be reached today because rules 2–3 fail on measured first dates. B16 is split:

- **B16-a (commission now):** produce the D03 closure artifact — the source-readiness MATRIX with measured admissible coverage and rights per branch, per first consumer (B04, B08, B09, B16, B18), with fallback and proof. Method, binding:
  - **Read-only access by allowlist, never a data checkout.** Inputs are read with `git show origin/main:<path>` into the lane's scratch directory: `data/fred_vintage/vintages.parquet`, `data/fred_vintage/alfred_depth_audit.json`, `data/baskets/membership_history.parquet`, `data/themes_heatmap/tree_history.jsonl`, `data/reference/security_master.parquet`, `data/reference/vendor_aliases.parquet`, `data/reference/*_receipt.json`, `config/delisted_symbols.yml`, plus the THS history path once located. `python3 scripts/worktree_sparse.py add data` is FORBIDDEN (it checks out outcome ledgers); `data/prophet/**`, `data/prophet_arena/**`, `data/prophet_stage_shadow/**`, `data/trial_ledger*`, any ledger, scoreboard or outcome artifact are never opened. Nothing under `data/` is written; outputs go to `research/prophet_v4/r6_program/wave2/`.
  - **Vintage depth:** `python3 -m scripts.audit_alfred_depth --series <Q6-1 list>` is run only as a cross-check — it emits earliest/latest vintage, vintage and period counts and a verdict whose 2010/2015 thresholds are unrelated to rule 1, so an "OK" is never a rule-1 pass; `--probe-missing` is FORBIDDEN (needs a key); post-first-release months and gaps are computed separately per series from the parquet and reported per period with `realtime_start`.
  - **Keyed-vs-keyless equivalence** receipt for the machinery candidates (census Q6-2) and the authoritative Census-to-FRED crosswalk status for the remaining M3 measures (Q6-3).
  - **Membership and identity:** first date, rows, dead names and identity coverage per suite (Q6-5); security master / aliases / delisted cross-check per historical cut (issuer Q6-1); each branch classified observed-as-run / admissible point-in-time replay / prospective-only / retrospective diagnostic (playbook step 2).
  - **Units and mapping cases (B16 discriminating cases):** record the semantic unit of every leg (levels, SA/NSA, nominal/real, cash-flow vs orders) and refuse any segment mapping whose source date is after the decision cut ("future segment mapping").
  - **Rights per branch:** the five answers for every branch in the matrix — FRED/ALFRED per series tag, Census M3, and the issuer families of §4 — plus census Q6 items 6–8 (Census terms record, provider entitlement record, Massive dead-name coverage against the licensed universe).
  - **Provider evaluation:** if rules 1, 4 and 5 are otherwise satisfiable for a domain and only rules 2–3 fail, list the licensed historical issuer-mapping providers that would close them, with scope and the five rights per provider, so the Chairman question in §4 can be asked precisely.
  - What cannot be reconstructed is recorded as absent; no lag, date, membership or license is manufactured.
- **B16-b (gated on B16-a):** if and only if a domain passes all five rules on the matrix, the seat rules admission (adjudicating §1(i) and ratifying the window under §1(ii)) and B16-b versions the pilot population and source map before any return inspection. Otherwise B16 closes as "NOT PILOT-READY — prospective collection started", and the prospective collection legs for (a) are the only Cycle work admitted.
- **B18 (failure-inclusive Cycle policy research) is BLOCKED** until B16-b admits a domain. No Cycle strategy return may be computed or cited under this program before that admission.

## 4. Issuer and event sources: rights and history scope (binds B04, B08, B09 as an ADDITIONAL gate)

Rights are five separate answers per family; a price, account, rights-profile string, product guard or public accessibility is never a grant. Classification on the issuer census §Q5 and the cycle census §Q4:

| Family | Acquisition | Processing / storage | Model use | User redistribution | Admitted scope now |
|---|---|---|---|---|---|
| Massive — `massive_stock_day` (enterprise license + redistribution addendum, `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md`) | recorded | recorded | recorded | recorded; vendor debranding remains required | user-facing for that feed, subject to the per-feed entitlement check the record itself requires; coverage of any historical segment product is UNKNOWN |
| First-party curated baskets / theme graph (`config/theme_sources.yml` house rows) | house | house | house | house (`direct_display_ok`) | user-facing |
| FRED / ALFRED economic legs | public endpoints, recorded | recorded mechanics | per-series tag only | UNKNOWN beyond the tag; CMRMTSPL tagged copyrighted | internal-only until the per-series rights row exists; no leg assumed public-domain |
| Census M3 | public file, recorded | recorded mechanics | UNKNOWN | UNKNOWN | internal-only |
| SEC EDGAR filings / 13F | public endpoints, recorded | processing INFERRED from the contracts; storage receipts are a mechanism, not a grant | UNKNOWN (public-domain status plausible but not recorded; D03 forbids assuming it) | UNKNOWN | internal-only until a rights-register row records the determination, quoting the source's own published terms |
| Nasdaq earnings calendar / surprise | public endpoint, recorded | UNKNOWN | UNKNOWN | UNKNOWN | internal-only (private diagnostics) |
| Yahoo / yfinance expectations | recorded | recorded (SRC-A1, `rights_class: UNKNOWN`) | UNKNOWN | UNKNOWN (the price row `vendor_terms_personal_use` does not transfer) | internal-only |
| Basket / SPY closes | recorded (yfinance, `vendor_terms_personal_use`, adverse-terms finding) | recorded; history rewrites nightly (`DSC:BASKET-OHLCV-REWRITES-HISTORY-NIGHTLY`) | UNKNOWN | UNKNOWN | internal-only for model use and redistribution; this ruling neither adjudicates nor ratifies existing display — that question goes to the rights register |
| EquityDesk, Finnhub, earnings-call scores | NOT REGISTERED | NOT REGISTERED | NOT REGISTERED | NOT REGISTERED | internal-only until registered |
| Finviz / THS themes | recorded as `unresolved` | internal-only posture | ungranted | refused (no public emission) | internal-only |
| S&P Kensho / Theia | reserved, unresolved rows only — no acquisition | — | — | — | not a source |
| Consensus estimates | none licensed | — | — | — | PERMANENTLY ABSENT (`R6-C-01`); beat/miss forbidden |
| Transcripts (`rp_public_primary_v1`) | UNKNOWN (the profile string is not a grant) | UNKNOWN | UNKNOWN | UNKNOWN | internal-only, `authority=context_only` |
| Press / narrative / search | documented endpoints only | UNKNOWN | UNKNOWN | UNKNOWN | internal-only; the Trends "display-only" note is a product guard, not a grant |

Rulings:
- **The R6-C-01 planes stand:** the EquityDesk plane and the company-intelligence/D5 plane remain separate as that ruling defines them; EDGAR-anchored releases are the issuer-fact plane; expectations are display-tier context; no beat/miss. Episode anchors remain D02's closed vocabulary (`turn_watch_reset_low`), which this ruling does not touch.
- **History is admissible only where a source-dated point-in-time row exists**, classified per playbook step 2. Admissible point-in-time replay today, per the issuer census: EDGAR 8-K event/date history and release bodies; S&P 1500 membership as bounded replay from log start; dated vendor aliases; the CPI vintage path. UNKNOWN today — not absent — pending B16-a's full-store audit: historical CIK lineage and identifier changes, a corporate-action / merger / spin-off / bankruptcy registry, and delisted-universe coverage (the security master is a tracked store whose coverage has not been measured). Until measured, those branches are prospective-only from first observed date. Current membership, event sets, GICS assignments and issuer identity are never backdated (playbook :40).
- **Rights register owed (an additional gate on B08/B09; B08 also waits on the natural nightly B1 clock per `R6-C-01`, B04 on D02 and its own D03/D07 preregistration):** one row per family above with the five answers, each quoting the source terms it rests on, under `research/licenses/`. A family without its row stays internal-only. The register grants nothing the terms do not; it records determinations, it does not assume them.
- **No new paid commitment outside the approved envelope.** None is proposed. If B16-a's matrix shows that rules 1, 4 and 5 are otherwise satisfiable for a domain and only a licensed historical issuer-mapping provider would close rules 2–3, that single question — provider, scope, the five rights, cost, and whether it sits inside the approved envelope — goes to the Chairman as an exact human gate with the measured evidence and the provider list attached. It does not go before the evidence exists.

## 5. Evidence condition and what would change this ruling

Measurement can ADMIT a domain; it cannot loosen a rule. Admission requires ALL FIVE rules on B16-a's receipted matrix: measured ≥120-month vintage receipts for two mechanisms the seat adjudicates as independent under §1(i); a dated membership history with failure coverage at every cut; every break handled under rule 4 (today only conditional for (a) and (b)); and every leg's five rights resolved (today unresolved for every candidate). The same rule reopens (b), (c), a provider-closed path, or any new candidate — a kill closes the construction tested, not the search space. A recorded rights determination moves a §4 family up its scope column.

## 6. Disposition

- Records: this ruling → `research/prophet_v4/r6_program/rulings/`; both censuses stay the evidence of record at their cited heads; the red-team's measurement is cited above and superseded by B16-a's receipts once they exist.
- Next commission: B16-a (read-only, allowlisted, on the external fabric); the rights register as a separate records lane under `research/licenses/`. B18 blocked. D03 status: RULED / CLOSURE PENDING the B16-a matrix (including the Q6 items and the per-branch rights) plus the rights register.
