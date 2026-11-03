# GMI theme graph — Chairman assessment and upgrade plan (2026-10-17)

Workstream WS:GMI-THEME-GRAPH · seat 6f14c2da · plain-English assessment for the Chairman.
Short names used below: SPEC = research/theme_graph/taxonomy_upgrade_v2/SPEC.md · D2E =
research/theme_graph/D2E_ACCEPTANCE_2026-10-06.md · census =
research/theme_graph/census/GMI_CLASSIFICATION_CENSUS_2026-10-07.md · HIER =
research/theme_graph/THEME_HIERARCHY_SPEC_V1_2026-10-07.md · MEMRES =
research/theme_graph/MICROTHEME_MEMBERSHIP_RESEARCH_2026-10-08.md · RULER =
research/theme_graph/GMI_COMPLETION_RULER_AUDIT_2026-10-05.md.
Production state read at origin/main 8ce9f3e9 (seat facts, verified 2026-10-17).

## 1. Bottom line

The theme map is live, rebuilt every night, and clean in its current scope. Taxonomy V2 gave
it a finer vocabulary (an optional sub-theme layer) and six on-demand ways to describe a
company — plus two new read-only viewers landed this week — but none of it is visible to you
on the site yet. One cleanup needs your signature (27 micro-themes with two parent chains);
one rights decision is waiting on you (W3C capture); two lanes sit with other owners (F04
consumption; registry roots). Recommended order: cheap display wins first (U1–U4), then the
curation workbench (U5), then the two gated graph changes (U6–U7).

## 2. What GMI does today (plain words)

**The product in one sentence.** GMI is a map that connects companies to the big ideas we
track — AI compute, grid power, GLP-1 drugs, rare earths, satellites, defense — and it is
rebuilt automatically every night.

**How the map is built.** We hand-pick 18 themes and express each through curated baskets of
companies (49 US baskets, 708 companies touched all-time). Each night the pipeline reads
those lists and writes one graph: at the last audited count, 3,882 nodes — 2,807 companies,
358 baskets, 55 ETFs, 18 themes, plus 644 vendor-label nodes kept strictly internal — and
25,101 links, most of them "is a member of" (census:16, census:20, D2E:169).

**How a company gets a theme.** Never by a stored tag on the company. When a company or a
theme is viewed, the system works out the connection at that moment from current basket
membership, so history stays honest and one company can sit in several ideas at once
(HIER:100-101; census:63).

**Cleanliness.** Each company resolves to one canonical identity; a renamed duplicate found
in October was merged away, leaving 2,806 canonical companies (D2E:186, #8544). Every data
source carries a rights label; the two vendor theme lists (finviz, THS) are internal-only and
are never inputs to anything shown (census:21-23; SPEC:10).

**What it deliberately does not do.** The taxonomy carries no scores, weights or rankings and
makes no claim about what any theme's stocks will do (SPEC:8). Those stay with their own
owners.

## 3. What Taxonomy V2 added

**A middle layer in the theme tree.** An optional "sub_theme" now sits between a theme and
its finest entries (micro-themes) — e.g. "copper supply chain" between the Copper theme and
copper mining / refined copper / copper wire (SPEC:14; MEMRES:315). It landed in the nightly
producer (#8948) and in the path reader (#8941); in production today: 12 sub_theme nodes and
132 parent edges at 8ce9f3e9 (seat facts; MEMRES:29).

**Six ways to describe a company, on demand.** SEC industry, geography, macro sensitivity,
business model, lifecycle stage, and value-chain position can be read for any subject as a
uniform typed record ("AxisCell") (SPEC:25-28). Six reader modules live in
engine/classification_axes/ (SPEC:62).

**A strict record contract.** A missing answer is a typed "we don't know, here's why" — never
a zero, never a guess; records are point-in-time checked and may not carry score, weight or
rank keys (SPEC:8, SPEC:31-38).

**The finest tier got researched, not padded.** All 68 micro-themes now have a proposed
definition, inclusion/exclusion rules, and named source-linked company candidates — 103
activity records over 100 public sources — all unadmitted research with company identities
deliberately left unresolved (MEMRES:322-333; #9200, #9491, #9504).

**Two read-only viewers (landed 10-17).** One answers "how wide is this theme?" — parents,
children by tier, distinct micro-theme descendants (#9537,
engine/theme_graph/hierarchy_breadth_display.py:1-20). The other shows, for a sub-theme or
micro-theme, which ancestor theme's baskets/ETFs could stand in for it — a clearly labeled
proxy that computes no strength number itself (#9534,
engine/theme_graph/micro_rs_proxy_display.py:6-10). Both are display-tier and exclude vendor
data (seat facts).

**Hardening landed 10-17.** A test that would catch future-dated records sneaking into
views (#9525), an identity-resolution test (#9535), the frozen V2 spec with the F04 sub-tier
note (#9526), and wave bookkeeping (#9072) (seat facts).

## 4. What is left

| # | Item | Why it matters | Owner | Blocker | Size |
|---|------|----------------|-------|---------|------|
| 1 | No site page renders the theme tree yet (seat fact) | The finer vocabulary exists but no human can see it | This seat | None identified — display work | M |
| 2 | 27 micro-themes carry two parent chains — the old direct edge plus the new sub_theme path (MEMRES:303; seat fact, ruling L17 = KEEP+ADD) | The graph is correct but reads as duplication until the old direct edges are withdrawn by event | Chairman — a HUMAN ratifier must sign 27 RELATION_WITHDRAW events (seat fact; HIER:19-20) | Human signature | S |
| 3 | W3C capture-rights decision still pending (seat fact) | Gates a capture/use question on the rights path | Chairman (operator decision) | Decision pending | S |
| 4 | Registry roots in config/mastermind_programs.yml deferred (seat fact) | Program registration stays incomplete | Other owner — lane mo-b-f09-10-usgs-mcs | That lane's gap | S |
| 5 | MarketOntology F04 consuming the new readers (SPEC:7) | F04 is the canonical downstream consumer of these readers | Other owner — parent session 01a12842; owned elsewhere (seat fact) | Not this program's work | M |
| 6 | Basket-to-micro membership admission (the E1b arm, HIER:113-117) | Micro-themes have no real members yet; every view proxies through ancestor baskets (micro_rs_proxy_display.py:3-10) | This seat, gated | GMI admission amendment + vertical countersign + honest accrual window (MEMRES:202) | L |
| 7 | Tier-aware display consumers beyond the two readers (category roll-ups, stock context cards) (census:66, census:75-77) | Turns the new vocabulary into more views for you | This seat | None identified — display work | M |
| 8 | General-CPU vocabulary hole (MEMRES:110-115) | Fresh Intel/AMD/Arm evidence makes the standing deferral worth a focused decision | Chairman (owner decision) | Decision | S |

Sizes are engineering estimates, not measurements of effort spent to date (not measured).

## 5. Upgrade plan (ranked)

**U1. Put the theme tree on the site (display-tier).** You open one page and browse
category → theme → sub-theme → micro-theme with live breadth counts. Extends
engine/theme_graph/hierarchy_breadth_display.py and the existing path reader in
engine/theme_graph/structural_navigation.py (HIER:99-100). Acceptance: a site-build test
asserting the page's counts equal the reader's output, plus the strict theme-graph contract
guard green (D2E:158 shows the guard command). No site page exists today (seat fact).

**U2. Micro-theme detail card (display-tier).** Click any micro-theme: its parent chain,
breadth counts, and the labeled proxy instruments from the #9534 reader. Extends
engine/theme_graph/micro_rs_proxy_display.py + hierarchy_breadth_display.py. Acceptance:
typed-null tests (an orphan micro-theme returns "unknown/value_missing", never a zero) and
the forbidden-key walk over every output (micro_rs_proxy_display.py:20-29).

**U3. "Why is this company here?" card (display-tier).** Given a ticker, show its read-time
path basket → theme → sub-theme → micro-theme, with a typed abstention for any missing leg.
Extends engine/theme_graph/structural_navigation.py (landed as W-C6, #8612; HIER:99-101).
Acceptance: as-of-date tests, plus the standing contract test that no per-ticker tag is ever
stored (HIER:159). The stock context card is the flagged display owner for this view
(census:77).

**U4. Six-axis labels beside company context (display-tier).** Surface the AxisCell readers
(engine/classification_axes/, SPEC:62) next to a company's theme path — industry, geography,
macro sensitivity, business model, lifecycle, value-chain position. Acceptance: the AxisCell
contract — one status per record, typed reasons, point-in-time check, no score/weight/rank
keys (SPEC:31-38).

**U5. Curation workbench for the membership research (display-tier; admits nothing).** Let
the curator page through the 103 candidate records with sources, stage labels and unresolved
identities, and record review outcomes — read-only against the graph. Extends
engine/theme_graph/membership_evidence.py and the existing read-only mode of
scripts/explain_theme_overlap.py (#9200; MEMRES:196, MEMRES:556). Acceptance: the existing
--review output stays byte-identical; refusal tests for malformed input and any attempted
authority escalation (MEMRES:222).

**U6. Prepare the 27 parent-collapse packets (promotion-bearing).** Build the 27
RELATION_WITHDRAW packets — each showing the retained chain side by side with the edge being
withdrawn — ready for your signature. Extends the curated-parent withdrawal path in
engine/theme_graph/probation.py (#8627) and the read-only relation-action resolver (#8507).
Acceptance: each packet cites its own prior-chain evidence; an LLM-originated action can
propose but never ratify (HIER:19-20). Gate: a reviewed crosswalk PR is the only act that
materializes an edge (HIER:80), and the withdrawal signature is human-only (seat fact).

**U7. First admitted group-to-micro membership pilot (promotion-bearing).** One small,
owner-admitted basket/slice binding so a micro-theme shows real members instead of a proxy
view. Extends the incumbent membership admission path (MEMRES:156-160) behind the existing
consumer tier-guards (HIER:138). Acceptance: Data OS identity qualification happens first;
the E1b preregistered arm runs only inside its honest accrual window (HIER:113-117); LLM
proposes, a human ratifies (HIER:19-20). Gauntlet gates: new-tier MEMBER_OF/EXPRESSES stays
blocked without the GMI admission amendment (MEMRES:160); Gate #8 — no new store, producer or
control plane (SPEC:9); Gate #2 — vendor theme lists are never inputs (SPEC:10).

Ranking rationale: U1–U4 are cheap, visible, and carry no graph risk; U5 makes every later
curation decision cheaper; U6–U7 change the graph itself and stay behind their gates.

## 6. Decisions needed from the Chairman

- Sign the batch of 27 parent-collapse withdrawal events (or any subset)? — yes/no.
- Give the W3C capture-rights decision now? — yes/no.
- Authorize opening the group-to-micro membership pilot path (the admission amendment)? — yes/no.
- Open the general-CPU scope review? — yes/no.

## 7. Sources

Read in full for this assessment:

- research/theme_graph/taxonomy_upgrade_v2/SPEC.md (frozen V2 program spec)
- research/theme_graph/GMI_COMPLETION_RULER_AUDIT_2026-10-05.md (Wave G audit; second
  publication surface flagged at RULER:396)
- research/theme_graph/D2E_ACCEPTANCE_2026-10-06.md (D2 acceptance; node/edge/company counts)
- research/theme_graph/census/GMI_CLASSIFICATION_CENSUS_2026-10-07.md (whole-GMI inventory;
  C0 erratum at census:111-125 supersedes the historical 11/7 split with 13 primary / 5 null)
- research/theme_graph/THEME_HIERARCHY_SPEC_V1_2026-10-07.md (frozen hierarchy spec V1)
- research/theme_graph/MICROTHEME_MEMBERSHIP_RESEARCH_2026-10-08.md (68-micro research)
- `git log origin/main --oneline -- engine/theme_graph research/theme_graph | head -40`
- Module docstrings: engine/theme_graph/hierarchy_breadth_display.py,
  engine/theme_graph/micro_rs_proxy_display.py, engine/theme_graph/structural_navigation.py

PRs cited: #9525, #9526, #9072, #9535, #9534, #9537 (landed 2026-10-17, seat facts); #8948,
#8941, #8942, #8629, #8612, #8595, #8609, #8544, #8540, #8507, #8627, #9200, #9491, #9504.

Seat facts (verified by the seat at origin/main 8ce9f3e9, 2026-10-17): Taxonomy V2 in
production with 12 sub_theme nodes and 132 PARENT_OF edges; L17 = KEEP+ADD with 27
double-parented micro-themes needing 27 human-signed RELATION_WITHDRAW events; no site page
renders the hierarchy; both new readers display-tier only with Gate #2 vendor exclusion;
registry roots deferred on the mo-b-f09-10-usgs-mcs gap; W3C capture-rights operator decision
pending; F04 consumption owned by parent session 01a12842 (owned elsewhere, not this
program's work).
