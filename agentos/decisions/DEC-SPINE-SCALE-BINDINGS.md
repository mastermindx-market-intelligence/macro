---
key: SPINE-SCALE-BINDINGS
question: >
  What data source binds the Hong Kong and China A-shares rows on the unified
  macro dashboard's one-scale, five-markets regime spine (UNIFIED_DASHBOARD_SPEC.md
  §3:105–129), and what happens to the remaining Bonds + Commodities rows?
answer: >
  Bind the HK row to HK_PROFILE market_state.score — the same blender that
  produces the US subject row, with identical leg weights 0.24/0.18/0.16/0.16/
  0.14/0.12 and verdict cuts 60/42. Persist it to data/hk_market_state/latest.json
  (a NEW path; NEVER overwrite data/market_state/latest.json) and ingest into the
  macro vm as vm["hk_market_state"] with the contract
  {score, label_en, label_zh, asof, caveat_en, caveat_zh, display_only:true}.

  Bind the CN row to CN_PROFILE market_state.score (same blender, same weights,
  same cuts) via data/china_market_state/latest.json (the existing
  convention used by build_china.py:1888 for the CN score_log) →
  vm["cn_market_state"] with the same contract.

  Government bonds and Commodities rows STAY DESIGNED-NULL — this is the ratified
  product state, not a deferral. Their slugs (gov_bonds_regime, commodities_regime)
  stay UNCHANGED so they remain honest as not-yet-existing contracts. Renaming
  HK/CN slugs from hk_regime/china_a_regime → hk_market_state/cn_market_state
  closes the quad-wiring trap on the HK row.

  The engine caveats (lighter evidence, no VIX term, no HY, uncalibrated
  downturn gauges, no hard overrides) travel with the number on the row's
  disclosure — binding the score onto the rail WITHOUT the caveat is the named
  failure mode.
rationale: >
  The spine places five markets on one shared 0–100 scale; only US binds
  (vm["market_state"]["score"]). Commensurability requires the same question
  (confirmation risk-on of THIS market) on the same kind of evidence (multi-leg
  tape / RORO / vol / breadth / liquidity / stress) without mapper-originated
  constants. The HK_PROFILE and CN_PROFILE already publish a 0–100 with the
  identical weights and cuts, and they already disclose they are lighter — so
  binding them is composition of an existing published measurement, not a new
  signal. Refusing is also lawful; the failure mode is binding the score onto
  the rail without the engine's own caveat stamp.

  The disposition feed names `hk_regime` / `china_a_regime` are NOT engines —
  they are blocked-feed slugs. `hk_regime` and `china_regime` are QUAD engines
  (growth × inflation cycle location), not 0–100 risk-on scores. Wiring
  `hk_regime` by name would put a cycle location onto a risk-on/off rail.
  Renaming the slug to `hk_market_state` makes the wiring trap explicit.

  Bonds and commodities are honest nulls. Bond health (engine/bonds.py) is a
  stress inverse of the economy/credit/plumbing; bond_compass duration lean
  polarity is the opposite of the spine unless inverted (which originates a
  new cross-asset identity the engines do not publish). Commodities mixes
  risk-on cyclicals with risk-off precious; one marker cannot be both. The
  spec mockup already designed the Commodities row as null (UNIFIED_DASHBOARD_
  SPEC.md §3:128–129, §7:248).
alternatives:
  - option: "Bind HK/CN to a different 0-100 (affine of global_score, RORO state map, intl turn-state)"
    why_not: >
      Different question / narrower question / double-counting. HK's hk_global
      reads concurrent global factor complex; RORO is one of six legs of HK_PROFILE;
      intl_market_state.market_states() does NOT cover CN (build_site.py:6431–6433)
      and turn-state is not a risk-on score (parabolic would print HIGH while the
      stance is "Protect gains — don't chase").
  - option: "Map the HK/CN quad (Q1–Q4) to a 0–100 table"
    why_not: >
      Quad is a growth × inflation cycle location, NOT a risk-on position.
      Mapping originaties a new signal in the dashboard — out of scope.
  - option: "Bind bonds via health_score or bond_compass.lean with polarity inverted"
    why_not: >
      Both originate a new signal — health high ≈ equity-friendly (a US stress
      guard proxy, not a bonds-row position); duration lean long ≈ equity
      risk-off unless inverted. Spec law: "not price performance" does not
      license "not even the same construct."
  - option: "Bind commodities via complex ts_trend or an inverted risk_index"
    why_not: >
      engine.commodity_index.py is explicit that it is display-tier only and never
      a scored authority. Complex mixes risk-on cyclicals with risk-off precious;
      one marker cannot be both "precious bid = risk-off" and "complex uptrend = risk-on."
  - option: "Leave HK/CN designed-null until a richer engine contract exists"
    why_not: >
      Legitimate — HK/CN row already publishes a 0-100 with the same blender and
      weights. Dashed rail loses real evidence without a concrete reason to defer;
      publishing the score with the engine's caveat stamp is composition, not
      origin. The spec's "62 capped / 71 uncapped" caveat is the SAME pattern.
evidence:
  - "engine/market_state_hk.py:152-164 — HK_PROFILE definition + caveat_en / caveat_zh"
  - "engine/market_state_cn.py:148-160 — CN_PROFILE definition + caveat_en / caveat_zh"
  - "engine/market_state.py:41-48 — leg weights 0.24/0.18/0.16/0.16/0.14/0.12"
  - "engine/market_state.py:448-453 — verdict cuts 60/42 (RISK_ON / MIXED / RISK_OFF)"
  - "engine/market_state.py:1263-1267 — _store_path (US path); 1283-1327 — persist() no-regress guard"
  - "engine/market_state.py:1339-1352 — load_persisted() (US default; per-market_key added 2026-09-20)"
  - "scripts/build_hk.py:1398-1413 — vm[market_state] = market_state_snapshot(..., HK_PROFILE); HK persist call added"
  - "scripts/build_hk.py:1440-1475 — HK score_log.parquet (read + append, ≥22 rows → real travel)"
  - "scripts/build_china.py:1557-1575 — vm[market_state] = market_state_snapshot(..., CN_PROFILE); CN persist call added"
  - "scripts/build_china.py:1880-1921 — CN score_log.parquet (read + append)"
  - "scripts/build_site.py:6661-6701 — _persisted_ms_view('hk') / _persisted_ms_view('cn') ingestion; vm[hk_market_state] / vm[cn_market_state] injection"
  - "templates/_unified_dashboard_hero.html.j2:415-505 — HK row bound to vm[hk_market_state]; CN row bound to vm[cn_market_state]"
  - "research/UNIFIED_DASHBOARD_DISPOSITION.md:58-61 — rows 19b/19c updated to BOUND with ratified source named; 19d/19e stay BLOCKED_DATA"
  - "research/UNIFIED_DASHBOARD_SPEC.md:3:105-129 — one-scale five-markets spine contract"
  - "research/spine_scale_analysis/analysis.out.md — the seat's adjudication; rank-1 recommendations ratified (host-path canonical: ~/lanes/ext/lanes/spine_scale_analysis/analysis.out.md, since the analysis lives outside the repo)"
  - "research/spine_scale_analysis/analysis.out.md §HK Candidate 1 — same blender, lighter evidence (no VIX term, no HY, uncalibrated stress, no overrides)"
  - "research/spine_scale_analysis/analysis.out.md §CN Candidate 1 — same blender, lighter evidence (QVIX, no HY, PBoC overlay, uncalibrated downturn)"
  - "research/spine_scale_analysis/analysis.out.md §GOV BONDS / §COMMODITIES — rejected (no commensurable scalar; spec designed Commodities as null)"
affects:
  - macro
confidence: high
reversibility: easy
decided_by: "META-CEO A packet UD-B2-W2 (seat, 2026-09-20); analyst packet ratified the rank-1 recommendations on this host"
decided_at: 2026-09-20
---