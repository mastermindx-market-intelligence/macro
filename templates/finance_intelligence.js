/* Finance Intelligence dossier — client-side hydration.
   No payload ever crosses into localStorage / sessionStorage / IndexedDB /
   the Cache API / service worker. The document lives in one in-memory
   closure variable only; every paint is rebuilt from that single read
   against the shared foundation read-model route.

   Built verbatim from the frozen Finance T8 spec
   (research/finance/implementation/FINANCE_DOSSIER_DESIGN_SPEC_2026-09-24.md).
*/
(function () {
  'use strict';

  // ──────────────────────────────────────────────────────────────────────────
  // Read URL — placeholder is bound at integration into the shared foundation
  // route. The spec names no path.
  // ──────────────────────────────────────────────────────────────────────────
  var FI_READ_URL = ''; // resolved in boot() from <main data-fi-read-url>; empty = not connected (bound at integration)

  // ──────────────────────────────────────────────────────────────────────────
  // Planestate enum → plain-word label map (closed; one EN/ZH pair per enum).
  // Every literal enum the live contract can deliver has one row here. The
  // spec's rule: the literal token rides only on data-state-* / data-*; the
  // visible text is always this row's plain words.
  // ──────────────────────────────────────────────────────────────────────────
  var FI_LABELS = {
    // D.1 plane state chips
    plane_state: {
      OBSERVED:                          ['On file — observed',           '已观察，有据可查'],
      INFERRED:                          ['On file — inferred',           '有据，推断得出'],
      MISSING:                           ['No dated reading on file',     '暂无可追溯的读数'],
      CONFLICTING:                       ['The numbers disagree',         '读数之间存在分歧'],
      STALE:                             ['Older than freshness window',  '已超出新鲜度窗口'],
      REGIME_BREAK:                      ['Not comparable to history',    '与历史不可比'],
      VALUATION_ANCHOR_UNAVAILABLE:      ['No valuation anchor on file',  '暂无估值锚'],
      PRICE_BASIS_UNQUALIFIED:           ['No qualified price basis',     '价格口径未达合格'],
      NOT_APPLICABLE:                    ['Not applicable here',          '此处不适用']
    },
    // D.1b comparability state
    comparability_state: {
      COMPARABLE:                        ['Comparable to history',         '与历史可比'],
      REGIME_BREAK_NOT_COMPARABLE:       ['Regime break — not comparable', '制度断裂 — 不可比'],
      MIXED_BASIS:                       ['Mixed basis',                   '口径混合'],
      UNKNOWN:                           ['Comparability unknown',         '可比性未知']
    },
    // D.2 slice_state
    slice_state: {
      SEMANTIC_ONLY:                     ['Definition only',               '仅完成定义'],
      RESEARCH_EVIDENCE_AVAILABLE:       ['Research evidence on file',     '已存研究证据'],
      MEASURABLE:                        ['Measurable today',              '当前可量化'],
      PRICE_SURFACE_AVAILABLE:           ['Price surface available',       '已具备价格曲面'],
      EVALUATION_CONTEXT_AVAILABLE:      ['Evaluation context available',  '已具备评估背景'],
      RIGHTS_RESTRICTED:                 ['Source rights restricted',      '来源权利受限'],
      STALE:                             ['Stale',                         '已陈旧'],
      HELD_FOR_REVIEW:                   ['Held for review',               '待复核']
    },
    // D.3 posture
    posture: {
      SEMANTIC_ONLY:                     ['No price basket yet',                 '暂无价格组合'],
      BROAD_CONTEXT_AVAILABLE:           ['Reference basket admitted',           '已收录参考组合'],
      RESEARCH_CANDIDATE:                ['Research candidate',                  '研究候选'],
      CANDIDATE_READY_FOR_OWNER_REVIEW:  ['Under owner review',                  '待负责人复核'],
      ADMITTED:                          ['Admitted price basket',               '已收录价格组合']
    },
    // D.4 membership
    membership: {
      NONE:                              ['No membership recorded',                          '未记录成员'],
      CURRENT_MEMBERSHIP_ONLY:           ['Current membership only — not a history',         '仅为当前成员 — 非历史口径'],
      PIT_MEMBERSHIP_INCOMPLETE:         ['Point-in-time membership incomplete',             '时点成员数据不完整'],
      PIT_MEMBERSHIP_VALIDATED:          ['Point-in-time membership checked',                '时点成员数据已校验']
    },
    // D.5 materiality
    materiality: {
      MATERIAL:                          ['Material exposure',        '重要敞口'],
      PARTIAL:                           ['Partial',                  '部分'],
      IMMATERIAL:                        ['Immaterial',               '不重大'],
      UNMEASURED:                        ['Not yet measured',         '尚未量化']
    },
    // D.6 role
    role: {
      DIRECT_PURE_OR_HIGH_EXPOSURE:      ['Direct, high exposure',         '直接且高敞口'],
      DIRECT_DIVERSIFIED:                ['Direct, diversified',           '直接，多元化'],
      ENABLER_OR_TOLL_COLLECTOR:         ['Enabler or toll collector',     '基础设施或收费方'],
      SECOND_ORDER_BENEFICIARY:          ['Second-order beneficiary',      '间接受益方'],
      PROXY_OR_ADJACENCY:                ['Proxy or adjacency',            '代理或邻近'],
      AT_RISK_OR_DISRUPTED:              ['At risk or disrupted',          '承压或被颠覆'],
      HEDGE_OR_OFFSET:                   ['Hedge or offset',               '对冲或抵消']
    },
    // D.7 exposure basis
    basis: {
      SEGMENT_REVENUE:                   ['Segment revenue',                 '分部收入'],
      TRANSACTION_VOLUME:                ['Transaction volume',              '交易笔数'],
      AUC_A:                             ['Assets under custody',            '在管资产规模'],
      AUM:                               ['Assets under management',         '在管资产'],
      NOTIONAL:                          ['Notional value',                  '名义金额'],
      QUALITATIVE:                       ['Qualitative read',                '定性读数'],
      NOT_SEPARATELY_DISCLOSED:          ['Not separately disclosed',        '未单独披露']
    },
    // D.8 exposure state
    exposure_state: {
      MEASURED:                          ['Measured',                                  '已量化'],
      EXPOSURE_NOT_SEPARATELY_DISCLOSED: ['Exposure not separately disclosed',          '敞口未单独披露'],
      DIRECT_DIVERSIFIED:                ['Direct, diversified',                        '直接，多元化'],
      QUALITATIVE_ONLY:                  ['Qualitative only',                           '仅作定性']
    },
    // System-view edge evidence state
    evidence_state: {
      OBSERVED:                          ['Evidence observed',                          '证据已观察'],
      INFERRED:                          ['Evidence inferred',                          '证据推断'],
      MISSING:                           ['No edge evidence on file',                   '尚无边证据'],
      CONFLICTING:                       ['Edge evidence contradicts',                  '边证据相互矛盾']
    },
    // D.9 constraint
    constraint: {
      regulatory_permission:             ['Regulatory permission',         '监管许可'],
      capital:                           ['Capital adequacy',              '资本充足'],
      funding_liquidity:                 ['Funding and liquidity',         '融资与流动性'],
      network_access:                    ['Network access',                '网络接入'],
      settlement_finality:               ['Settlement finality',           '结算终局性'],
      data_benchmark_control:            ['Data and benchmark control',    '数据与基准控制'],
      distribution:                      ['Distribution reach',            '分销覆盖'],
      integration_switching:             ['Integration and switching cost','集成与切换成本'],
      trust_identity:                    ['Trust and identity',            '信任与身份'],
      resilience:                        ['Operational resilience',        '运营韧性']
    },
    // D.10 macro drivers
    driver: {
      policy_rates:                      ['Policy rates',            '政策利率'],
      yield_curve:                       ['Yield curve',             '收益率曲线'],
      deposit_funding:                   ['Deposit funding',         '存款融资'],
      credit_growth:                     ['Credit growth',           '信贷增长'],
      losses_defaults:                   ['Losses and defaults',     '损失与违约'],
      housing:                           ['Housing activity',        '房地产活动'],
      equity_levels:                     ['Equity market levels',    '股市水平'],
      volatility:                        ['Volatility regime',       '波动率环境'],
      issuance_ma:                       ['Issuance and M&A',        '发行与并购'],
      catastrophe_reinsurance:           ['Catastrophe and reinsurance', '巨灾与再保'],
      regulation_capital:                ['Regulation and capital',  '监管与资本'],
      fx:                                ['FX regime',               '汇率环境'],
      liquidity:                         ['Market liquidity',        '市场流动性']
    },
    // D.11 lag
    lag: {
      IMMEDIATE:                         ['Immediate',          '即时'],
      ONE_QUARTER:                       ['About a quarter',    '约一个季度'],
      TWO_TO_FOUR_QUARTERS:              ['Two to four quarters', '两到四个季度'],
      MULTI_YEAR:                        ['Multi-year',         '多年'],
      UNKNOWN:                           ['Lag not measured',   '尚未测算时滞']
    },
    // D.11b macro matrix state
    macro_state: {
      DESCRIBED:                         ['Mechanism described',            '已描述机制'],
      CAUSAL_EFFECT_UNMEASURED:          ['Causal effect not measured',     '因果影响未测量'],
      NOT_APPLICABLE:                    ['Not applicable',                 '不适用']
    },
    // D.12 + D.15 freshness state (same row in both spec tables)
    freshness: {
      FRESH:                             ['Fresh',                  '新鲜'],
      AGING:                             ['Aging',                  '趋于陈旧'],
      SOURCE_STALE:                      ['Source is stale',        '来源已陈旧'],
      NO_EVIDENCE:                       ['No evidence on file',    '暂无证据']
    },
    // D.13 first-vertical state
    first_vertical_state: {
      NOT_BUILT:                         ['Not built yet',                  '尚未构建'],
      SYNTHETIC:                         ['Synthetic construction',         '合成构建'],
      RESEARCH_RECORDS:                  ['Research records only',          '仅研究记录'],
      PRODUCTION_PROVEN:                 ['Production-proven',              '已生产验证']
    },
    // D.14 outer-dossier state
    outer_dossier_state: {
      AVAILABLE:                         ['Outer dossier accepted',         '外部报告已接入'],
      OUTER_CONTRACT_NOT_ACCEPTED:       ['Outer dossier not accepted',     '外部报告尚未接入'],
      UNAVAILABLE:                       ['Outer dossier unavailable',      '外部报告暂不可用']
    },
    // D.16 history state
    history_state: {
      DATED_CONSENSUS_AVAILABLE:         ['Dated consensus on file',                  '已存可追溯的市场预期'],
      NO_HISTORICAL_CONSENSUS:           ['No dated consensus on file',               '暂无可追溯的市场预期'],
      MANAGEMENT_GUIDANCE_ONLY:          ['Management guidance only',                 '仅管理层指引']
    },
    // D.17 valuation anchor (per-share, multiple, horizon, state)
    per_share_anchor: {
      EPS:                               ['Earnings per share',                 '每股收益'],
      CORE_EPS:                          ['Core earnings per share',            '核心每股收益'],
      TBVPS:                             ['Tangible book per share',            '每股有形账面'],
      BVPS:                              ['Book per share',                     '每股账面'],
      FCF_PER_SHARE:                     ['Free cash flow per share',           '每股自由现金流'],
      DPS:                               ['Dividend per share',                 '每股股息'],
      EMBEDDED_VALUE_PER_SHARE:          ['Embedded value per share',           '每股内含价值'],
      NAV_PER_SHARE:                     ['Net asset value per share',          '每股净资产'],
      NOT_APPLICABLE:                    ['Per-share anchor not applicable',    '每股锚点不适用']
    },
    valuation_multiple: {
      P_E:                               ['P/E multiple',                       '市盈率'],
      P_TBV:                             ['P/TBV multiple',                     '市净率（有形）'],
      P_B:                               ['P/B multiple',                       '市净率'],
      EV_EBITDA:                         ['EV/EBITDA',                          '企业价值倍数'],
      FCF_YIELD:                         ['Free cash flow yield',               '自由现金流收益率'],
      DIVIDEND_YIELD:                    ['Dividend yield',                     '股息率'],
      P_EV:                              ['P/EV multiple',                      'P/EV 倍数'],
      P_NAV:                             ['P/NAV multiple',                     'P/NAV 倍数'],
      P_AUM:                             ['P/AUM multiple',                     'P/AUM 倍数'],
      NOT_APPLICABLE:                    ['Multiple not applicable',            '倍数不适用']
    },
    horizon: {
      TRAILING_12M:                      ['Trailing 12 months',                 '过去 12 个月'],
      FORWARD_12M:                       ['Forward 12 months',                  '未来 12 个月'],
      FORWARD_24M:                       ['Forward 24 months',                  '未来 24 个月'],
      CURRENT_BOOK:                      ['Current book',                       '当前账面'],
      NOT_APPLICABLE:                    ['Horizon not applicable',             '时限不适用']
    },
    valuation_anchor_state: {
      AVAILABLE:                         ['Anchor available',                   '锚点可用'],
      VALUATION_ANCHOR_UNAVAILABLE:      ['No valuation anchor on file',        '暂无估值锚']
    },
    // D.18 falsifier state
    falsifier_state: {
      WATCHING:                          ['Watching',           '观察中'],
      NOT_YET_EVALUABLE:                 ['Not yet evaluable',  '暂无法评估']
    },
    // D.19 price basis state
    price_basis_state: {
      PRICE_BASIS_UNQUALIFIED:           ['Price basis not qualified',          '价格口径未达合格'],
      TOTAL_RETURN_QUALIFIED:            ['Total-return basis qualified',       '总回报口径合格'],
      PRICE_RETURN_QUALIFIED:            ['Price-return basis qualified',       '价格回报口径合格']
    },
    // D.20 family of basket-construction choices (plain-words label only)
    weighting_family: {
      EQUAL_WEIGHT:                      ['Equal weight',                       '等权重'],
      FLOAT_CAP_CONTEXT:                 ['Float-cap context',                  '流通上限背景'],
      EXPOSURE_WEIGHT:                   ['Exposure weight',                    '敞口权重'],
      EXPOSURE_CAPPED_WEIGHT:            ['Exposure-capped weight',             '敞口封顶权重'],
      STRATIFIED_EQUAL_WEIGHT:           ['Stratified equal weight',            '分层等权重']
    },
    // D.21 identity state
    identity_state: {
      IDENTITY_VALIDATED:                ['Identity confirmed',                 '身份已确认'],
      IDENTITY_UNRESOLVED:               ['Identity unresolved',                '身份尚未确认'],
      RESEARCH_HINT_UNVALIDATED:         ['Research hint, not validated',       '研究线索，尚未确认']
    },
    // D.22 company route state
    company_route_state: {
      AVAILABLE:                         ['Route available',                                       '路由可用'],
      IDENTITY_UNRESOLVED:               ['Route unavailable — identity unresolved',                '路由暂不可用 — 身份尚未确认']
    },
    // D.23 source rights (DRAWER SUPPRESSION)
    rights_state: {
      DIRECT_DISPLAY_OK:                 ['Direct display OK',                  '可直接展示'],
      DERIVED_DISPLAY_OK:                ['Derived display OK',                 '可展示派生内容'],
      SOURCE_RIGHTS_HELD:                ['Source rights restrict display',     '来源权利限制展示'],
      INTERNAL_ONLY:                     ['Internal only',                      '仅供内部使用']
    },
    // D.24 statement mode
    statement_mode: {
      REPORTED_FACT:                     ['Reported fact',                  '报告事实'],
      CATALOG_DESCRIPTION:               ['Catalog description',            '目录描述'],
      ANNOUNCED_ARRANGEMENT:             ['Announced arrangement',          '已公告安排'],
      FORWARD_TARGET:                    ['Forward target',                 '前瞻目标'],
      ATTRIBUTED_INTERPRETATION:         ['Attributed interpretation',      '归因解读']
    },
    // D.25 published_at grain
    published_at_grain: {
      DAY:                               ['day',           '日'],
      MONTH:                             ['month',         '月'],
      QUARTER:                           ['quarter',       '季'],
      YEAR:                              ['year',          '年'],
      UNKNOWN:                           ['grain not stated', '未说明粒度']
    },
    // D.26 measurement class
    measurement_class: {
      VOLUME_VALUE:                      ['volume',         '量值'],
      VOLUME_COUNT:                      ['count',          '计数'],
      REVENUE:                           ['revenue',        '收入'],
      EXPENSE:                           ['expense',        '支出'],
      BALANCE:                           ['balance',        '余额'],
      RATIO:                             ['ratio',          '比率'],
      RATE:                              ['rate',           '费率'],
      PER_SHARE:                         ['per share',      '每股'],
      QUALITATIVE:                       ['qualitative',    '定性']
    },
    // D.27 gross/net basis
    gross_net_basis: {
      GROSS:                             ['gross',          '总额'],
      NET:                               ['net',            '净额'],
      NOTIONAL:                          ['notional',       '名义'],
      NOT_APPLICABLE:                    ['not applicable', '不适用']
    },
    // D.28 period summary basis (internal key; visible label preserved)
    period_summary_basis: {
      AVERAGE:                           ['average',        '平均'],
      END:                               ['end',            '期末'],
      NOT_APPLICABLE:                    ['not applicable', '不适用']
    },
    // D.29 reported/derived/estimated
    reported_derived_estimated: {
      REPORTED:                          ['reported',       '原始报告'],
      DERIVED:                           ['derived',        '推算'],
      ESTIMATED:                         ['estimated',      '估计']
    },
    // D.30 indicator.direction
    indicator_direction: {
      LEADING:                           ['leading',        '领先'],
      COINCIDENT:                        ['coincident',     '同步'],
      LAGGING:                           ['lagging',        '滞后']
    },
    // D.31 indicator.state
    indicator_state: {
      OBSERVED:                          ['observed',       '已观察'],
      MISSING:                           ['missing',        '缺失'],
      STALE:                             ['stale',          '已陈旧']
    },
    // D.32 plane words (conflicts)
    plane_word: {
      operating:                         ['Operating',      '经营'],
      expectations:                      ['Expectations',   '市场预期'],
      valuation:                         ['Valuation',      '估值'],
      price:                             ['Price',          '价格'],
      regime:                            ['Regime',         '制度环境'],
      policy:                            ['Policy',         '政策']
    },
    // D.33 system-view edge relationship words (per view)
    edge_relationship: {
      PAYS:                              ['pays',           '支付'],
      SETTLES:                           ['settles',        '结算'],
      CLEARS:                            ['clears',         '清算'],
      GUARANTEES:                        ['guarantees',     '担保'],
      FUNDS:                             ['funds',          '融资'],
      INSURES:                           ['insures',        '承保'],
      LENDS:                             ['lends',          '放贷'],
      HOLDS_CUSTODY:                     ['holds custody',  '托管'],
      LICENSES:                          ['licenses',       '许可'],
      SUPERVISES:                        ['supervises',     '监管'],
      GRANTS_ACCESS:                     ['grants access',  '授予接入'],
      PUBLISHES_BENCHMARK:               ['publishes benchmark', '发布基准'],
      RATES:                             ['rates',          '评级'],
      PROVIDES_DATA:                     ['provides data',  '提供数据'],
      REQUIRES_MEMBERSHIP:               ['requires membership', '要求成员资格'],
      EARNS_FEE_FROM:                    ['earns fee from', '向…收取费用'],
      BEARS_CREDIT_RISK_OF:              ['bears credit risk of', '承担…信用风险'],
      CAPTURES_SPREAD_ON:                ['captures spread on',   '赚取…价差'],
      RECOGNISES_REVENUE_FROM:           ['recognises revenue from', '确认…收入'],
      DEPENDS_ON_VOLUME_OF:              ['depends on volume of','依赖…数量']
    },
    // D.34 input-receipt owner + state
    receipt_owner: {
      sector_intelligence:               ['Sector intelligence',          '子行业情报'],
      theme_graph:                       ['Theme graph',                  '主题图谱'],
      financial_intelligence:            ['Financial intelligence',       '金融情报'],
      expectations_revisions:            ['Expectations revisions',       '预期修订'],
      market_data:                       ['Market data',                  '市场数据'],
      baskets:                           ['Baskets',                      '组合'],
      macro_rates_credit:                ['Macro rates and credit',       '宏观利率与信贷'],
      identity:                          ['Identity',                     '身份'],
      private_publication:               ['Private publication',          '私有发布']
    },
    receipt_state: {
      READ:                              ['ready',         '就绪'],
      UNAVAILABLE:                       ['unavailable',   '暂不可用'],
      NOT_ACCEPTED:                      ['not accepted',  '未接入'],
      DEGRADED:                          ['degraded',      '已降级']
    },
    // D.35 degraded_section
    degraded_section_state: {
      AVAILABLE:                         ['available',     '可用'],
      UNAVAILABLE:                       ['unavailable',   '不可用'],
      PARTIAL:                           ['partial',       '部分可用']
    },
    // D.37 conflict labels
    conflict_label: {
      EARNINGS_UP_P_E_DOWN:                                              ['Earnings up, multiple down',                              '盈利上升，倍数下降'],
      BOOK_UP_P_B_DOWN:                                                 ['Book value up, multiple down',                            '账面价值上升，倍数下降'],
      NII_UP_CREDIT_WORSE:                                              ['Net interest income up, credit worsening',                '净利息收入上升，信贷恶化'],
      POLICY_SUPPORT_NIM_PRESSURE:                                      ['Policy supports demand, margins under pressure',           '政策支撑需求，息差承压'],
      REGULATORY_RATIO_DOWN_REGIME_BREAK:                               ['Regulatory ratio down, regime break',                      '监管比率下降，制度断裂'],
      PLAN_DISCLOSED_EXECUTION_PENDING:                                 ['Plan disclosed, execution pending',                        '计划已披露，执行待落地'],
      TAIL_RISK_DOWN_CURRENT_EARNINGS_WEAK:                             ['Tail risk down, current earnings weak',                    '尾部风险下降，当期盈利偏弱'],
      PRICE_UP_CAUSAL_EVENT_EFFECT_UNPROVEN:                           ['Price up, causal effect not proven',                        '价格上升，因果效应未证实'],
      CAPITAL_COST_UP_GROWTH_STILL_STRONG:                              ['Cost of capital up, growth still strong',                   '资本成本上升，增长仍然强劲'],
      VOLUME_UP_REVENUE_MATERIALITY_UNPROVEN:                           ['Volume up, revenue materiality not proven',                 '交易量上升，收入重要性未证实']
    }
  };

  // F1 (item 1) — every chip class that owns per-state colour rules lives in
  // this tuple. Chips NOT listed here may not paint background / color /
  // border-color in CSS. Five members: fi-step-chip, fi-membership-chip,
  // fi-posture-chip, fi-slice-chip, fi-macro-cell-state. Spec §B line 396.
  var SPEC_CHIP_SELECTORS = [
    'fi-step-chip',
    'fi-membership-chip',
    'fi-posture-chip',
    'fi-slice-chip',
    'fi-macro-cell-state',
  ];

  var LABEL_FALLBACKS = {
    plane_state:        ['State not recorded', '未记录状态'],
    comparability_state:['Comparability not recorded', '未记录可比性'],
    slice_state:        ['Definition only', '仅完成定义'],
    posture:            ['No price basket yet', '暂无价格组合'],
    membership:         ['No membership recorded', '未记录成员'],
    materiality:        ['Not yet measured', '尚未量化'],
    role:               ['—', '—'],
    basis:              ['—', '—'],
    exposure_state:     ['—', '—'],
    constraint:         ['—', '—'],
    driver:             ['—', '—'],
    lag:                ['Lag not measured', '尚未测算时滞'],
    macro_state:        ['Not applicable', '不适用'],
    freshness:          ['No evidence on file', '暂无证据'],
    first_vertical_state:['Not built yet', '尚未构建'],
    outer_dossier_state:['Outer dossier unavailable', '外部报告暂不可用'],
    history_state:      ['No dated consensus on file', '暂无可追溯的市场预期'],
    per_share_anchor:   ['Per-share anchor not applicable', '每股锚点不适用'],
    valuation_multiple: ['Multiple not applicable', '倍数不适用'],
    horizon:            ['Horizon not applicable', '时限不适用'],
    valuation_anchor_state: ['No valuation anchor on file', '暂无估值锚'],
    falsifier_state:    ['Watching', '观察中'],
    price_basis_state:  ['Price basis not qualified', '价格口径未达合格'],
    weighting_family:   ['No weighting recorded', '未记录权重'],
    identity_state:     ['Identity unresolved', '身份尚未确认'],
    company_route_state:['Route unavailable — identity unresolved', '路由暂不可用 — 身份尚未确认'],
    rights_state:       ['Source rights restrict display', '来源权利限制展示'],
    statement_mode:     ['Reported fact', '报告事实'],
    published_at_grain: ['grain not stated', '未说明粒度'],
    measurement_class:  ['qualitative', '定性'],
    gross_net_basis:    ['not applicable', '不适用'],
    period_summary_basis:['not applicable', '不适用'],
    reported_derived_estimated: ['reported', '原始报告'],
    indicator_direction: ['coincident', '同步'],
    indicator_state:    ['observed', '已观察'],
    plane_word:         ['Operating', '经营'],
    edge_relationship:  ['—', '—'],
    receipt_owner:      ['—', '—'],
    receipt_state:      ['state not recorded', '未记录状态'],
    degraded_section_state:['available', '可用'],
    conflict_label:     ['Disagreement on file', '存在分歧']
  };

  // D.38 surface chrome — fix copy
  var SURFACE = {
    conflict_foot: ['Left unresolved by design — both statements stand.', '有意不作裁决 — 两项陈述并存。'],
    falsifier_head:['What we are watching', '我们正在观察'],
    no_metric:     ['No metric on file', '暂无可用指标'],
    slice_label:   ['Slice', '切片'],
    no_role:       ['No role recorded', '未记录角色'],
    not_mapped:    ['Not mapped', '未映射'],
    private_drawer_notice: ['Value and excerpt withheld — source rights held.', '数值与摘录已隐去 — 来源权利受限。']
  };

  // ──────────────────────────────────────────────────────────────────────────
  // helpers
  // ──────────────────────────────────────────────────────────────────────────
  function isZh() { return document.documentElement.getAttribute('data-lang') === 'zh'; }
  // Accessible name in the CURRENT language plus the EN/ZH pair the inline
  // swapper re-applies on langchange. Rendered controls are created after that
  // swapper has run, so the pair alone would leave them English in 中文.
  function ariaPair(en, zh) {
    return ' aria-label="' + esc(isZh() ? (zh || en) : en) + '" data-aria-en="' + esc(en) + '" data-aria-zh="' + esc(zh) + '"';
  }
  function copyPair(pair) { return isZh() ? (pair[1] || pair[0]) : pair[0]; }
  // F7a: lang="en" marks payload prose only. A fallback placeholder is page copy
  // in the reader's language, so it never carries the attribute.
  function enLang(value) { return value ? ' lang="en"' : ''; }
  function labelRow(map, key) {
    if (!key) return FI_LABELS[map] && FI_LABELS[map][''] || LABEL_FALLBACKS[map] || ['—', '—'];
    return (FI_LABELS[map] && FI_LABELS[map][key]) || LABEL_FALLBACKS[map];
  }
  function labelFor(map, key) { return copyPair(labelRow(map, key)); }
  // Static chips are named "<what>: <current label>"; the runtime writes the
  // EN/ZH pair (the inline swapper re-applies it on langchange) plus the name
  // in the current language, since the swapper ran before hydration.
  function nameChip(el, en, zh) {
    el.setAttribute('data-aria-en', en);
    el.setAttribute('data-aria-zh', zh);
    el.setAttribute('aria-label', isZh() ? zh : en);
  }
  function esc(value) {
    return String(value === null || value === undefined ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function firstDefined() {
    for (var i = 0; i < arguments.length; i += 1) {
      if (arguments[i] !== undefined && arguments[i] !== null && arguments[i] !== '') return arguments[i];
    }
    return null;
  }
  function asArray(value) { return Array.isArray(value) ? value : []; }

  // ──────────────────────────────────────────────────────────────────────────
  // auth + fetchJson (verbatim biocatalyst.js pattern, raised to closure)
  // ──────────────────────────────────────────────────────────────────────────
  function withAuth(headers) {
    headers = headers || {};
    if (!(window.MDXAuth && window.MDXAuth.client)) return Promise.resolve(headers);
    return window.MDXAuth.client().then(function (client) {
      return client.auth.getSession();
    }).then(function (result) {
      var token = result && result.data && result.data.session && result.data.session.access_token;
      if (token) headers.Authorization = 'Bearer ' + token;
      return headers;
    }).catch(function () { return headers; });
  }
  function markHydration(error, kind, status) {
    if (!error || typeof error !== 'object') error = new Error(String(error || kind));
    error.hydration = kind;
    if (status != null) error.status = status;
    return error;
  }
  function jsonContentType(response) {
    var type = '';
    try { type = (response.headers && response.headers.get) ? String(response.headers.get('content-type') || '') : ''; } catch (_e) { type = ''; }
    if (!type) return true;
    return /json/i.test(type);
  }
  function hydrationKind(error) {
    if (!error || error.name === 'AbortError') return '';
    if (error.hydration) return error.hydration;
    if (error.status === 404) return 'not_found';
    if (typeof error.status === 'number' && error.status >= 500) return 'source_outage';
    return '';
  }
  function fetchJson(url, signal) {
    return withAuth({ Accept: 'application/json' }).then(function (headers) {
      return fetch(url, { headers: headers, credentials: 'include', cache: 'no-store', signal: signal });
    }).then(function (response) {
      var status = response.status;
      if (status === 401 || status === 402 || status === 403) throw markHydration(new Error('HTTP ' + status), 'locked', status);
      if (!response.ok) throw markHydration(new Error('HTTP ' + status), 'source_outage', status);
      if (!jsonContentType(response)) throw markHydration(new Error('HTTP 200 non-json'), 'integrity_block', 200);
      return Promise.resolve(response.text()).then(function (raw) {
        try { return JSON.parse(raw); }
        catch (parseError) { throw markHydration(parseError, 'integrity_block', 200); }
      });
    }, function (networkError) {
      if (networkError && networkError.name === 'AbortError') throw networkError;
      if (networkError && networkError.hydration) throw networkError;
      throw markHydration(networkError, 'source_outage', 0);
    });
  }

  // ──────────────────────────────────────────────────────────────────────────
  // fmtMetric, fmtClock (D.0)
  // ──────────────────────────────────────────────────────────────────────────
  function fmtMetric(metric) {
    if (!metric) return '';
    var value = metric.value;
    var unit = metric.unit;
    var mc = metric.measurement_class;
    if (value === null || value === undefined || unit === null || unit === undefined || mc === 'QUALITATIVE') {
      return copyPair(SURFACE.no_metric);
    }
    var digits;
    if (mc === 'RATIO' || mc === 'RATE') digits = 1;
    else if (mc === 'PER_SHARE') digits = 2;
    else digits = 0;
    var formatted = Number(value).toFixed(digits);
    var pieces = [formatted, unit];
    if (metric.currency) pieces.push(metric.currency);
    var body = pieces.join(' ');
    if (metric.period_start && metric.period_end) {
      body += ' (' + String(metric.period_start).slice(0, 10) + ' – ' + String(metric.period_end).slice(0, 10) + ')';
    }
    return body;
  }
  var GRAIN_LABEL = FI_LABELS.published_at_grain;
  function fmtClock(clock) {
    if (!clock) return '';
    var out = '';
    if (clock.published_at) {
      out += String(clock.published_at).slice(0, 10);
    } else if (clock.observed_at) {
      out += String(clock.observed_at).slice(0, 10);
    }
    if (clock.published_at_grain) {
      out += ' · ' + labelFor('published_at_grain', clock.published_at_grain);
    }
    return out;
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Page state — one in-memory document
  // ──────────────────────────────────────────────────────────────────────────
  var state = {
    doc: null,
    sliceId: '',
    drawer: { open: false, recordId: '', source: null },
    lastFocus: null,
    ui: {}
  };

  function $(sel) { return document.querySelector(sel); }
  function $$(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }
  function setText(el, txt) { if (el) el.textContent = txt; }
  function show(el, on) { if (!el) return; el.hidden = !on; }
  function chipClass(opts) {
    // One class attribute per chip; tokens de-duplicated, first-occurrence
    // order kept (so `fi-chip` is always present at the front). Spec §C.5(6).
    var seen = {};
    var tokens = ['fi-chip'];
    var push = function (t) {
      if (!t) return;
      var raw = String(t).trim();
      if (!raw) return;
      raw.split(/\s+/).forEach(function (w) {
        if (!seen[w]) { seen[w] = true; tokens.push(w); }
      });
    };
    push(opts && opts.classes);
    return tokens.join(' ');
  }
  function chipHtml(label, opts) {
    opts = opts || {};
    var safe = esc(label || '—');
    var attrs = [];
    attrs.push('class="' + esc(chipClass(opts)) + '"');
    if (opts.stateMarker) attrs.push('data-state-marker="' + esc(opts.stateMarker) + '"');
    if (opts.stateKey) attrs.push('data-state="' + esc(opts.stateKey) + '"');
    if (opts.stateMembership) attrs.push('data-state-membership="' + esc(opts.stateMembership) + '"');
    if (opts.statePosture) attrs.push('data-state-posture="' + esc(opts.statePosture) + '"');
    if (opts.stateSlice) attrs.push('data-state-slice="' + esc(opts.stateSlice) + '"');
    if (opts.stateBasis) attrs.push('data-state-price-basis="' + esc(opts.stateBasis) + '"');
    if (opts.stateWeighting) attrs.push('data-state-weighting="' + esc(opts.stateWeighting) + '"');
    if (opts.stateIdentity) attrs.push('data-identity="' + esc(opts.stateIdentity) + '"');
    if (opts.stateConstraint) attrs.push('data-constraint="' + esc(opts.stateConstraint) + '"');
    if (opts.statePriceState) attrs.push('data-price-state="' + esc(opts.statePriceState) + '"');
    if (opts.stateValuationState) attrs.push('data-valuation-state="' + esc(opts.stateValuationState) + '"');
    if (opts.stateAnchorState) attrs.push('data-anchor-state="' + esc(opts.stateAnchorState) + '"');
    if (opts.stateComparability) attrs.push('data-comparability="' + esc(opts.stateComparability) + '"');
    if (opts.stateHistory) attrs.push('data-history="' + esc(opts.stateHistory) + '"');
    if (opts.evidenceIds) attrs.push('data-evidence-ids="' + esc(opts.evidenceIds) + '"');
    return '<span ' + attrs.join(' ') + '>' + safe + '</span>';
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Hero + meta mount
  // ──────────────────────────────────────────────────────────────────────────
  function renderHero() {
    var d = state.doc;
    var heroAsof = state.ui.heroAsof;
    var heroCutoff = state.ui.heroCutoff;
    var heroAsofZh = state.ui.heroAsofZh;
    var heroCutoffZh = state.ui.heroCutoffZh;
    var freshnessChip = state.ui.heroFreshness;
    var outerChip = state.ui.heroOuter;
    if (d.common_as_of) {
      setText(heroAsof, 'As of ' + String(d.common_as_of).slice(0, 10));
      setText(heroAsofZh, '截至 ' + String(d.common_as_of).slice(0, 10));
      show(heroAsof, true); show(heroAsofZh, true);
    }
    if (d.knowledge_cutoff) {
      setText(heroCutoff, 'Knowledge cutoff ' + String(d.knowledge_cutoff).slice(0, 10));
      setText(heroCutoffZh, '知识截止 ' + String(d.knowledge_cutoff).slice(0, 10));
      show(heroCutoff, true); show(heroCutoffZh, true);
    }
    if (d.freshness && freshnessChip) {
      var freshRow = labelRow('freshness', d.freshness.state);
      freshnessChip.setAttribute('data-state-freshness', d.freshness.state);
      setText(freshnessChip, copyPair(freshRow));
      show(freshnessChip, true);
    }
    if (d.outer_dossier_ref && outerChip) {
      var outerRow = labelRow('outer_dossier_state', d.outer_dossier_ref.state);
      outerChip.setAttribute('data-state-outer-dossier', d.outer_dossier_ref.state);
      setText(outerChip, copyPair(outerRow));
      show(outerChip, true);
    }
  }

  // Mirror top-level freshness.state onto the what-changed section head pip
  // (E.4 freshness mirroring rule). The rerating stepper head mirrors the
  // selected slice's freshness.state.
  function mirrorFreshness() {
    var d = state.doc;
    if (!d) return;
    var whatChangedHead = $('#what-changed > .fi-section-head');
    if (whatChangedHead && d.freshness) {
      whatChangedHead.setAttribute('data-state-freshness', d.freshness.state || '');
    }
    var reratingHead = $('#rerating-map > .fi-section-head');
    if (reratingHead) {
      var slice = findSlice(state.sliceId);
      var fs = slice && slice.freshness && slice.freshness.state;
      if (!fs && d.freshness) fs = d.freshness.state;
      reratingHead.setAttribute('data-state-freshness', fs || '');
    }
  }

  // Item 10 (SEAT-PINNED source-language marking): append a small ZH-only
  // note under sections that hold English-source prose, so 中文 readers know
  // the prose is the original English. Idempotent across repaints and the
  // langchange re-render — the note's `.fi-srclang-note` class is removed
  // before any fresh append, so a second langchange doesn't stack them.
  // F7: only append when the section actually holds [lang="en"] prose; never
  // stamp the note on a section whose prose is empty.
  function renderSourceLangNote(sectionEl) {
    if (!sectionEl) return;
    var prev = sectionEl.querySelectorAll('.fi-srclang-note');
    for (var i = 0; i < prev.length; i += 1) prev[i].parentNode.removeChild(prev[i]);
    if (!isZh()) return; // EN never sees the line (per spec: ZH-only)
    var hasProse = sectionEl.querySelector('[lang="en"]') !== null;
    if (!hasProse) return;
    // Seat erratum (T11 round 2): the packet's `.fi-sowhat` exists nowhere in the frozen
    // spec or the page. Every L1 section opens with one `.fi-section-head` (title +
    // plain-word eyebrow), so the note is the first body line directly after it.
    var head = null;
    for (var k = 0; k < sectionEl.children.length; k += 1) {
      if (sectionEl.children[k].classList.contains('fi-section-head')) { head = sectionEl.children[k]; break; }
    }
    var note = document.createElement('p');
    note.className = 'fi-srclang-note l-zh';
    note.textContent = '本节部分文字为英文原文，未经翻译。';
    if (head) sectionEl.insertBefore(note, head.nextSibling);
    else sectionEl.appendChild(note);
  }

  // ──────────────────────────────────────────────────────────────────────────
  // What changed
  // ──────────────────────────────────────────────────────────────────────────
  function renderWhatChanged() {
    var d = state.doc;
    var list = state.ui.whatChangedList;
    if (!list) return;
    var changes = asArray(d.material_changes).slice().sort(function (a, b) {
      var ap = a.event_clock && (a.event_clock.published_at || a.event_clock.observed_at);
      var bp = b.event_clock && (b.event_clock.published_at || b.event_clock.observed_at);
      return (bp || '').localeCompare(ap || '');
    });
    if (!changes.length) {
      list.innerHTML = '<li class="fi-change-row fi-panel2"><span class="l-en">No material observations on file.</span><span class="l-zh">暂无重要观察。</span></li>';
      return;
    }
    // Item 4: build a unique accessible name per evidence button, keyed by
    // its row context (slice name for what-changed, plane word for step, the
    // unique side pair for conflict, §D.9 label for constraint, issuer for
    // identity). Duplicates within a section get ` (2)`, ` (3)` suffixes in
    // document order so screen readers can disambiguate every trigger.
    var nameCounts = {};
    var uniqueEn = function (kind, ctxEn, ctxZh) {
      var key = kind + '|' + ctxEn;
      var n = (nameCounts[key] = (nameCounts[key] || 0) + 1);
      var en = ctxEn + (n > 1 ? ' (' + n + ')' : '');
      var zh = ctxZh + (n > 1 ? '（' + n + '）' : '');
      return { en: en, zh: zh };
    };
    list.innerHTML = changes.map(function (row) {
      var name = sliceName(row.slice_ids && row.slice_ids[0], row.domain_ids && row.domain_ids[0]);
      var freshness = row.freshness_state || 'NO_EVIDENCE';
      var clause = row.operating_implication || (isZh() ? '尚无操作启示。' : 'No operating implication on file.');
      var evidence = asArray(row.evidence_refs).join(' ');
      var nm = uniqueEn('change', name, name);
      // Item 10: data-driven prose (operating_implication from payload) carries
      // lang="en" so screen readers know to render it with English phonology.
      // The page-local source-language note is appended below by renderSourceLangNote().
      return '<li class="fi-change-row mx-chg-row" data-change-id="' + esc(row.change_id) + '" data-state-freshness="' + esc(freshness) + '">' +
        '<span class="fi-change-name mx-chg-name">' + esc(name) + '</span>' +
        '<span class="fi-change-clause mx-chg-what"' + enLang(row.operating_implication) + '>' + esc(clause) + '</span>' +
        chipHtml(labelFor('freshness', freshness), { classes: 'fi-freshness-row', stateKey: 'FRESHNESS_PLACEHOLDER' }).replace('data-state="FRESHNESS_PLACEHOLDER"', 'data-state-freshness="' + esc(freshness) + '" data-state-marker="' + esc(freshness) + '"') +
        '<button type="button" class="fi-step-evidence fi-evidence-trigger" data-evidence-ids="' + esc(evidence) + '"' + ariaPair('Open evidence: ' + nm.en, '打开证据：' + nm.zh) + '><span aria-hidden="true">↗</span></button>' +
        '</li>';
    }).join('');
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Slice lookup
  // ──────────────────────────────────────────────────────────────────────────
  function sliceName(sliceId, domainId) {
    var slices = asArray(state.doc && state.doc.slices);
    var s = slices.filter(function (x) { return x.slice_id === sliceId; })[0];
    if (s) return isZh() ? (s.name_zh || s.name_en) : (s.name_en || s.name_zh);
    var domains = asArray(state.doc && state.doc.domains);
    var d = domains.filter(function (x) { return x.domain_id === domainId; })[0];
    if (d) return isZh() ? (d.name_zh || d.name_en) : (d.name_en || d.name_zh);
    return '—';
  }
  function findSlice(id) {
    if (!id) return null;
    return asArray(state.doc && state.doc.slices).filter(function (s) { return s.slice_id === id; })[0] || null;
  }
  function firstVerticalSliceIds() {
    var cov = state.doc && state.doc.coverage && state.doc.coverage.first_vertical;
    return asArray(cov && cov.slice_ids);
  }
  function sliceNameZH(s) { return s.name_zh || s.name_en || ''; }
  function sliceNameEN(s) { return s.name_en || s.name_zh || ''; }

  // ──────────────────────────────────────────────────────────────────────────
  // Slice selector
  // ──────────────────────────────────────────────────────────────────────────
  function renderSliceSelector() {
    var sel = state.ui.sliceSelect;
    if (!sel) return;
    var ids = firstVerticalSliceIds();
    var slices = asArray(state.doc && state.doc.slices);
    var opts = ids.map(function (id) {
      var s = slices.filter(function (x) { return x.slice_id === id; })[0];
      if (!s) return '';
      return '<option value="' + esc(id) + '">' + esc(sliceNameEN(s)) + ' / ' + esc(sliceNameZH(s)) + '</option>';
    }).join('');
    sel.innerHTML = opts;
    if (!state.sliceId && ids.length) state.sliceId = ids[0];
    sel.value = state.sliceId;
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Rerating stepper — exactly four nodes (operating, expectations, valuation, price)
  // ──────────────────────────────────────────────────────────────────────────
  var RERATING_STEPS = [
    { name: 'operating',    caption: ['What drives earnings, book, free cash flow and capital per share?', '什么驱动每股盈利、账面、自由现金流与资本？'] },
    { name: 'expectations', caption: ['What does the market already expect?',                                    '市场已经在期待什么？'] },
    { name: 'valuation',    caption: ['What anchor is the price paid against?',                                  '价格是基于什么锚定的？'] },
    { name: 'price',        caption: ['Has the price recognised it?',                                            '价格是否已经反映？'] }
  ];

  function renderRerating() {
    var ol = state.ui.reratingSteps;
    if (!ol) return;
    var slice = findSlice(state.sliceId);
    var rerating = (slice && slice.rerating) || {};
    // Item 4: each rerating step evidence button carries the plane word
    // ("operating / earnings", "expectations / consensus", "valuation /
    // anchor", "price / recognition") so screen readers can disambiguate the
    // four buttons without hearing four identical "Open evidence" calls.
    var html = RERATING_STEPS.map(function (s, idx) {
      var node = rerating[s.name] || {};
      var state$ = node.state || 'MISSING';
      var comparability = node.comparability_state;
      var evidence = asArray(node.evidence_refs).join(' ');
      var planeWordEn = labelFor('plane_word', s.name)[0] || s.name;
      var planeWordZh = labelFor('plane_word', s.name)[1] || planeWordEn;
      var rowHtml = '';
      rowHtml += '<li class="fi-rerating-step fi-node-' + s.name + '" data-active="' + (idx === activeStepIdx() ? 'true' : 'false') + '" data-state-marker="' + esc(state$) + '">';
      rowHtml += '<span class="fi-step-dot" aria-hidden="true"></span>';
      rowHtml += '<span class="fi-step-label">' + esc(isZh() ? s.caption[1] : s.caption[0]) + '</span>';
      rowHtml += '<span class="fi-step-metric">' + esc(fmtMetric(node.primary_metric || {})) + '</span>';
      rowHtml += chipHtml(labelFor('plane_state', state$), { classes: 'fi-step-chip', stateKey: state$, stateMarker: state$ });
      if (comparability && comparability !== 'COMPARABLE') {
        rowHtml += chipHtml(labelFor('comparability_state', comparability), { classes: 'fi-comparability-chip', stateComparability: comparability, stateMarker: comparability });
      }
      rowHtml += '<span class="fi-step-clock">' + esc(fmtClock(node.clock || {})) + '</span>';
      if (s.name === 'valuation') {
        var va = slice && slice.valuation_anchor;
        if (va) {
          rowHtml += chipHtml(labelFor('per_share_anchor', va.primary_per_share_anchor || 'NOT_APPLICABLE'), { classes: 'fi-anchor-chip', stateAnchorState: va.primary_per_share_anchor || '', stateMarker: va.primary_per_share_anchor || '' });
          rowHtml += chipHtml(labelFor('valuation_multiple', va.primary_valuation_anchor || 'NOT_APPLICABLE'), { classes: 'fi-anchor-chip', stateAnchorState: va.primary_valuation_anchor || '', stateMarker: va.primary_valuation_anchor || '' });
          rowHtml += chipHtml(labelFor('horizon', va.horizon || 'NOT_APPLICABLE'), { classes: 'fi-anchor-chip', stateAnchorState: va.horizon || '', stateMarker: va.horizon || '' });
          rowHtml += chipHtml(labelFor('valuation_anchor_state', va.state || 'VALUATION_ANCHOR_UNAVAILABLE'), { classes: 'fi-valuation-chip', stateValuationState: va.state || '', stateMarker: va.state || '' });
        }
      }
      if (s.name === 'expectations' && rerating.expectations && rerating.expectations.history) {
        var h = rerating.expectations.history.state;
        rowHtml += chipHtml(labelFor('history_state', h), { classes: 'fi-history-chip', stateHistory: h, stateMarker: h });
      }
      if (s.name === 'price' && state$ === 'PRICE_BASIS_UNQUALIFIED') {
        rowHtml += chipHtml(labelFor('plane_state', state$), { classes: 'fi-price-chip', statePriceState: state$, stateMarker: state$ });
      }
      rowHtml += '<button type="button" class="fi-step-evidence" data-evidence-ids="' + esc(evidence) + '"' + ariaPair('Open evidence: ' + planeWordEn, '打开证据：' + planeWordZh) + '>↗</button>';
      rowHtml += '</li>';
      return rowHtml;
    }).join('');
    ol.innerHTML = html;

    var bridge = state.ui.reratingBridge;
    if (bridge) {
      var txt = (slice && slice.rerating && slice.rerating.bridge) ||
        (isZh() ? '从盈利到分化的链路已在上方标签中写明。' : 'The chain from earnings to divergence is documented in the chips above.');
      bridge.setAttribute('lang', 'en');
      setText(bridge, txt);
    }
    renderFalsifiers();
    renderConflicts();
  }

  function activeStepIdx() {
    var slice = findSlice(state.sliceId);
    var r = (slice && slice.rerating) || {};
    for (var i = 0; i < RERATING_STEPS.length; i += 1) {
      var n = RERATING_STEPS[i].name;
      var st = (r[n] && r[n].state);
      if (st && st !== 'OBSERVED') return i;
    }
    return 3;
  }

  function renderFalsifiers() {
    var ul = state.ui.falsifiers;
    if (!ul) return;
    var slice = findSlice(state.sliceId);
    var falsifiers = asArray(slice && slice.falsifiers);
    if (!falsifiers.length) {
      ul.innerHTML = '';
      return;
    }
    ul.innerHTML = falsifiers.map(function (f) {
      return '<li class="fi-falsifier fi-panel2" data-state-falsifier="' + esc(f.state) + '" data-state-marker="' + esc(f.state) + '">' +
        chipHtml(labelFor('falsifier_state', f.state), { stateMarker: f.state }) +
        '<span class="fi-falsifier-statement"' + enLang(f.statement) + '>' + esc(f.statement || (isZh() ? '尚无可观察陈述。' : 'No statement on file.')) + '</span>' +
        '<span class="fi-falsifier-window"' + enLang(f.window) + '>' + esc(f.window || '') + '</span>' +
        '</li>';
    }).join('');
  }

  function renderConflicts() {
    var ul = state.ui.conflictList;
    if (!ul) return;
    var all = asArray(state.doc && state.doc.conflicts);
    var here = all.filter(function (c) { return asArray(c.slice_ids).indexOf(state.sliceId) >= 0; });
    var others = all.length - here.length;
    if (!here.length) {
      var note = others > 0
        ? '<p class="fi-section-foot">' + (isZh() ? '其他切片另有 ' + others + ' 项冲突。' : (others + ' more conflicts on other slices.')) + '</p>'
        : '';
      ul.innerHTML = note;
      return;
    }
    ul.innerHTML = here.map(function (c) {
      var lk = c.label || '';
      var left = c.left || {};
      var right = c.right || {};
      var leftEvidence = asArray(left.evidence_refs).join(' ');
      var rightEvidence = asArray(right.evidence_refs).join(' ');
      // Item 4: conflict evidence buttons name the side AND plane ("first
      // reading (operating)" / "second reading (valuation)") so a screen
      // reader user hears which side they're opening.
      var leftPlane = labelRow('plane_word', left.plane || 'operating');
      var leftPlaneEn = leftPlane[0] || 'first';
      var leftPlaneZh = leftPlane[1] || leftPlaneEn;
      var rightPlane = labelRow('plane_word', right.plane || 'valuation');
      var rightPlaneEn = rightPlane[0] || 'second';
      var rightPlaneZh = rightPlane[1] || rightPlaneEn;
      return '<li class="fi-conflict-card fi-panel2" data-conflict-label="' + esc(lk) + '" data-state-marker="' + esc(lk) + '">' +
        '<p class="fi-conflict-label">' + esc(labelFor('conflict_label', lk)) + '</p>' +
        '<div class="fi-conflict-pair">' +
          '<div class="fi-conflict-side" data-side="left">' +
            chipHtml(labelFor('plane_word', left.plane || 'operating'), { stateMarker: left.plane || '' }) +
            '<p class="fi-conflict-side-statement"' + enLang(left.statement) + '>' + esc(left.statement || '') + '</p>' +
            '<button type="button" class="fi-step-evidence fi-evidence-trigger" data-evidence-ids="' + esc(leftEvidence) + '"' + ariaPair('Open evidence: first reading (' + leftPlaneEn + ')', '打开证据：第一方读数（' + leftPlaneZh + '）') + '>↗</button>' +
          '</div>' +
          '<div class="fi-conflict-side" data-side="right">' +
            chipHtml(labelFor('plane_word', right.plane || 'operating'), { stateMarker: right.plane || '' }) +
            '<p class="fi-conflict-side-statement"' + enLang(right.statement) + '>' + esc(right.statement || '') + '</p>' +
            '<button type="button" class="fi-step-evidence fi-evidence-trigger" data-evidence-ids="' + esc(rightEvidence) + '"' + ariaPair('Open evidence: second reading (' + rightPlaneEn + ')', '打开证据：第二方读数（' + rightPlaneZh + '）') + '>↗</button>' +
          '</div>' +
        '</div>' +
        '<p class="fi-conflict-foot">' + copyPair(SURFACE.conflict_foot) + '</p>' +
        '</li>';
    }).join('');
  }

  // ──────────────────────────────────────────────────────────────────────────
  // System map
  // ──────────────────────────────────────────────────────────────────────────
  function renderSystem() {
    var tabsEl = state.ui.viewTabs;
    var panelsEl = state.ui.viewPanels;
    if (!tabsEl || !panelsEl) return;
    var views = asArray(state.doc && state.doc.system_views);
    if (!views.length) {
      tabsEl.innerHTML = '';
      panelsEl.innerHTML = '<p class="fi-section-foot">' + (isZh() ? '尚未建立系统视图。' : 'No system views on file.') + '</p>';
      return;
    }
    tabsEl.innerHTML = views.map(function (v, i) {
      return '<button type="button" role="tab" class="fi-view-tab" id="tab-' + esc(v.view_id) + '" aria-controls="panel-' + esc(v.view_id) + '" aria-selected="' + (i === 0 ? 'true' : 'false') + '" data-view="' + esc(v.view_id) + '" tabindex="' + (i === 0 ? '0' : '-1') + '">' +
        '<span class="l-en">' + esc(v.name_en || v.view_id) + '</span><span class="l-zh">' + esc(v.name_zh || v.name_en || v.view_id) + '</span></button>';
    }).join('');
    panelsEl.innerHTML = views.map(function (v, i) {
      var edges = asArray(v.edges);
      var hidden = i === 0 ? '' : ' hidden';
      // Resolve node ids → human labels once per view (Item 3).
      var nodeIndex = {};
      asArray(v.nodes).forEach(function (n) {
        if (n && n.node_id) nodeIndex[n.node_id] = n;
      });
      var nodeLabel = function (id) {
        var n = nodeIndex[id];
        if (!n) return isZh() ? '未标注节点' : 'Unlabelled node';
        return isZh() ? (n.label_zh || n.label_en || (isZh() ? '未标注节点' : 'Unlabelled node'))
                       : (n.label_en || n.label_zh || 'Unlabelled node');
      };
      var edgeHtml = edges.map(function (e) {
        var rel = labelFor('edge_relationship', e.relationship);
        var fromLabel = nodeLabel(e.from) + ' — ' + rel + ' → ' + nodeLabel(e.to);
        var evidence = (e.evidence_state || 'MISSING');
        return '<li class="fi-system-edge" data-state-evidence="' + esc(evidence) + '" data-state-marker="' + esc(evidence) + '">' +
          '<span class="fi-system-edge-statement">' + esc(fromLabel) + '</span>' +
          chipHtml(labelFor('evidence_state', evidence), { stateMarker: evidence }) +
          '</li>';
      }).join('');
      var nodes = asArray(v.nodes);
      // First 8 nodes live in the panel list; 9..N in a sibling .fi-disc
      // disclosure whose summary counts the remainder (Item 3 + §C.10 invariant).
      var firstNodes = nodes.slice(0, 8);
      var moreNodes = nodes.slice(8);
      var nodeHtml = firstNodes.map(function (n) {
        var label = isZh() ? (n.label_zh || n.label_en || '未标注节点')
                            : (n.label_en || n.label_zh || 'Unlabelled node');
        return '<li class="fi-slice fi-panel2" data-node-id="' + esc(n.node_id) + '">' +
          '<span class="fi-slice-name">' + esc(label) + '</span>' +
          '</li>';
      }).join('');
      var moreNodeHtml = moreNodes.map(function (n) {
        var label = isZh() ? (n.label_zh || n.label_en || '未标注节点')
                            : (n.label_en || n.label_zh || 'Unlabelled node');
        return '<li class="fi-slice fi-panel2" data-node-id="' + esc(n.node_id) + '">' +
          '<span class="fi-slice-name">' + esc(label) + '</span>' +
          '</li>';
      }).join('');
      var nodesDisclosure = '';
      if (moreNodes.length > 0) {
        var k = moreNodes.length;
        var sumEn = 'Show ' + k + ' more nodes';
        var sumZh = '再显示 ' + k + ' 个节点';
        nodesDisclosure = '<details class="fi-disc fi-system-nodes-more" data-fi-mount="system-nodes-more">' +
          '<summary>' +
            '<span class="l-en">' + esc(sumEn) + '</span>' +
            '<span class="l-zh">' + esc(sumZh) + '</span>' +
          '</summary>' +
          '<ul class="fi-slice-list">' + moreNodeHtml + '</ul>' +
          '</details>';
      }
      return '<div role="tabpanel" id="panel-' + esc(v.view_id) + '" class="fi-view-panel" data-view="' + esc(v.view_id) + '" aria-labelledby="tab-' + esc(v.view_id) + '"' + hidden + '>' +
        '<svg class="fi-system-svg" role="img"' + ariaPair(v.name_en || v.view_id, v.name_zh || '') + '><title>' + esc(v.name_en || v.view_id) + '</title></svg>' +
        '<ul class="fi-slice-list">' + nodeHtml + '</ul>' +
        nodesDisclosure +
        '<details class="fi-system-edges" open><summary><span class="l-en">Edge list</span><span class="l-zh">边的步骤视图</span></summary>' +
        '<ol class="fi-system-edge-list">' + edgeHtml + '</ol></details>' +
        '</div>';
    }).join('');

    // Bind roving tabindex
    $$('.fi-view-tab').forEach(function (tab) {
      tab.addEventListener('click', function () { activateView(tab.dataset.view); });
      tab.addEventListener('keydown', function (ev) {
        if (ev.key === 'ArrowLeft' || ev.key === 'ArrowRight' || ev.key === 'Home' || ev.key === 'End') {
          ev.preventDefault();
          var tabs = $$('.fi-view-tab');
          var idx = tabs.indexOf(tab);
          var next = idx;
          if (ev.key === 'ArrowLeft') next = (idx - 1 + tabs.length) % tabs.length;
          else if (ev.key === 'ArrowRight') next = (idx + 1) % tabs.length;
          else if (ev.key === 'Home') next = 0;
          else if (ev.key === 'End') next = tabs.length - 1;
          activateView(tabs[next].dataset.view);
          tabs[next].focus();
        }
      });
    });
    // Keep the reader's chosen view across the langchange re-render. If the
    // user never touched a tab, state.viewId is unset — promote the first
    // view so the langchange re-render lands on the same active selection
    // even when focus was elsewhere (F5).
    if (!state.viewId && views.length) state.viewId = views[0].view_id;
    if (state.viewId && views.some(function (v) { return v.view_id === state.viewId; })) activateView(state.viewId);
  }
  function activateView(viewId) {
    state.viewId = viewId;
    $$('.fi-view-tab').forEach(function (t) {
      var sel = t.dataset.view === viewId;
      t.setAttribute('aria-selected', sel ? 'true' : 'false');
      t.setAttribute('tabindex', sel ? '0' : '-1');
      var panel = document.getElementById('panel-' + t.dataset.view);
      if (panel) panel.hidden = !sel;
    });
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Atlas
  // ──────────────────────────────────────────────────────────────────────────
  function renderAtlas() {
    var grid = state.ui.domainGrid;
    var ey = state.ui.coverageEyebrow;
    var gap = state.ui.atlasGap;
    if (!grid) return;
    var d = state.doc;
    var slices = asArray(d && d.slices);
    var domains = asArray(d && d.domains);
    if (ey && d && d.coverage) {
      var c = d.coverage;
      ey.textContent = (isZh()
        ? ('已映射 ' + (c.domains_populated || 0) + ' / ' + (c.domains_total || 0) + ' 个子域 · ' + (c.slices_populated || 0) + ' / ' + (c.slices_total || 0) + ' 个切片')
        : ((c.domains_populated || 0) + ' of ' + (c.domains_total || 0) + ' domains · ' + (c.slices_populated || 0) + ' of ' + (c.slices_total || 0) + ' slices mapped'));
      show(ey, true);
    }
    if (!domains.length) {
      grid.innerHTML = '';
      return;
    }
    var rendered = 0;
    grid.innerHTML = domains.map(function (domain) {
      var inDomain = slices.filter(function (s) { return asArray(domain.slice_ids).indexOf(s.slice_id) >= 0; });
      rendered += inDomain.length;
      return '<section class="fi-domain fi-panel2" data-domain-id="' + esc(domain.domain_id) + '" aria-label="' + esc(isZh() ? (domain.name_zh || domain.name_en) : (domain.name_en || domain.name_zh)) + '">' +
        '<h3 class="fi-domain-title"><span class="l-en">' + esc(domain.name_en || '') + '</span><span class="l-zh">' + esc(domain.name_zh || domain.name_en || '') + '</span></h3>' +
        '<ul class="fi-slice-list">' + inDomain.map(function (s) {
          var ss = s.slice_state || 'SEMANTIC_ONLY';
          var bs = (s.basket_state && s.basket_state.membership_state) || 'NONE';
          var posture = (s.basket_state && s.basket_state.posture) || 'SEMANTIC_ONLY';
          var pbs = (s.basket_state && s.basket_state.price_basis_state) || 'PRICE_BASIS_UNQUALIFIED';
          var wf = s.basket_state && s.basket_state.weighting_family;
          var incumbentCount = asArray(s.basket_state && s.basket_state.incumbent_basket_ids).length;
          return '<li class="fi-slice fi-panel2" data-state-slice="' + esc(ss) + '" data-state-marker="' + esc(ss) + '" data-basket-state="' + esc(bs) + '" data-slice-id="' + esc(s.slice_id) + '">' +
            '<span class="fi-slice-name">' + esc(isZh() ? (s.name_zh || s.name_en) : (s.name_en || s.name_zh)) + '</span>' +
            '<div style="display:flex;gap:4px;flex-wrap:wrap">' +
            chipHtml(labelFor('slice_state', ss), { classes: 'fi-slice-chip', stateSlice: ss, stateMarker: ss }) +
            chipHtml(labelFor('membership', bs), { classes: 'fi-membership-chip', stateMembership: bs, stateMarker: bs }) +
            chipHtml(labelFor('posture', posture), { classes: 'fi-posture-chip', statePosture: posture, stateMarker: posture }) +
            chipHtml(labelFor('price_basis_state', pbs), { classes: 'fi-price-basis-chip', stateBasis: pbs, stateMarker: pbs }) +
            chipHtml(labelFor('weighting_family', wf || ''), { classes: 'fi-weighting-chip', stateWeighting: wf || '', stateMarker: wf || '' }) +
            '</div>' +
            '<span class="fi-slice-open">' + esc(isZh() ? (incumbentCount + ' 个参考篮子') : (incumbentCount + ' reference baskets')) + '</span>' +
            '</li>';
        }).join('') + '</ul>' +
        '</section>';
    }).join('');

    if (gap) {
      var total = (d && d.coverage && d.coverage.slices_total) || 0;
      var remaining = Math.max(0, total - rendered);
      if (remaining > 0) {
        gap.textContent = isZh() ? (remaining + ' 个切片尚未映射') : (remaining + ' slices not yet mapped');
        show(gap, true);
      } else {
        show(gap, false);
      }
    }
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Exposure table
  // ──────────────────────────────────────────────────────────────────────────
  function renderExposure() {
    var sliceIds = firstVerticalSliceIds();
    var exposures = asArray(state.doc && state.doc.company_exposures).slice().sort(function (a, b) {
      return String(a.issuer_label || '').localeCompare(String(b.issuer_label || ''));
    });
    var first = exposures.slice(0, 8);
    var more = exposures.slice(8);
    var thead = state.ui.exposureThead;
    var rows = state.ui.exposureRows;
    var moreEl = state.ui.exposureMore;
    var cards = state.ui.exposureCards;
    if (!thead || !rows) return;

    var headRow = '<tr><th class="fi-col-company" scope="col"><span class="l-en">Company</span><span class="l-zh">公司</span></th>' +
      sliceIds.map(function (sid) {
        var s = findSlice(sid);
        return '<th class="fi-col-slice" scope="col">' + esc(s ? (isZh() ? (s.name_zh || s.name_en) : (s.name_en || s.name_zh)) : sid) + '</th>';
      }).join('') + '</tr>';
    thead.innerHTML = headRow;
    if (state.ui.exposureTheadMore) state.ui.exposureTheadMore.innerHTML = headRow;

    var buildRow = function (row) {
      var identity = (row.identity && row.identity.state) || 'IDENTITY_UNRESOLVED';
      return '<tr data-row-id="' + esc(row.row_id || row.issuer_label) + '" data-state-identity="' + esc(identity) + '" data-state-marker="' + esc(identity) + '">' +
        '<td class="fi-col-company"><span>' + esc(row.issuer_label || '—') + '</span> ' +
        // Seat erratum (T11 round 2): a state chip, not an evidence trigger. The dossier's
        // company_exposures[].identity carries no evidence reference, so a trigger here
        // would open nothing, and a click-bound <span> can neither take focus nor a name.
        chipHtml(labelFor('identity_state', identity), { classes: 'fi-identity-chip', stateIdentity: identity, stateMarker: identity }) +
        '</td>' +
        sliceIds.map(function (sid) {
          var cell = asArray(row.cells).filter(function (c) { return c.slice_id === sid; })[0];
          if (!cell) {
            return '<td class="fi-cell" data-state-materiality="UNMEASURED"><span class="fi-cell-role">' + esc(copyPair(SURFACE.no_role)) + '</span></td>';
          }
          var mat = cell.materiality || 'UNMEASURED';
          var expState = (cell.exposure && cell.exposure.state) || '';
          return '<td class="fi-cell" data-state-exposure="' + esc(expState) + '" data-state-materiality="' + esc(mat) + '" data-state-marker="' + esc(expState) + '">' +
            '<span class="fi-cell-role">' + esc(cell.role ? labelFor('role', cell.role) : copyPair(['No role recorded', '未记录角色'])) + '</span>' +
            '<span class="fi-cell-basis">' + esc(labelFor('basis', (cell.exposure && cell.exposure.basis) || '')) + '</span>' +
            '<span class="fi-cell-materiality">' + esc(labelFor('materiality', mat)) + '</span>' +
            (cell.retained_risk ? '<span class="fi-cell-risk" lang="en">' + esc(cell.retained_risk) + '</span>' : '') +
            (cell.evidence_date ? '<span class="fi-cell-evidence-date">' + esc(cell.evidence_date) + '</span>' : '') +
            '</td>';
        }).join('') +
        '</tr>';
    };
    rows.innerHTML = first.map(buildRow).join('');
    if (state.ui.exposureRowsMore) state.ui.exposureRowsMore.innerHTML = more.map(buildRow).join('');

    if (moreEl) {
      if (more.length > 0) {
        moreEl.hidden = false;
        var sum = moreEl.querySelector('summary');
        if (sum) {
          sum.innerHTML = '<span class="l-en">See all ' + (exposures.length) + ' companies</span>' +
                           '<span class="l-zh">查看全部 ' + exposures.length + ' 家</span>';
        }
      } else {
        moreEl.hidden = true;
      }
    }

    if (cards) {
      if (first.length === 0) {
        cards.innerHTML = '';
      } else {
        cards.innerHTML = first.map(function (row) {
          return '<li class="fi-exposure-card fi-panel2" data-row-id="' + esc(row.row_id || row.issuer_label) + '">' +
            '<p class="fi-cell-role">' + esc(row.issuer_label || '—') + '</p>' + asArray(row.cells).slice(0, 6).map(function (cell) {
              return '<p><strong>' + esc(sliceName(cell.slice_id, null) || cell.slice_id) + ':</strong> ' +
                esc(labelFor('role', cell.role)) + ' · ' +
                esc(labelFor('materiality', cell.materiality || 'UNMEASURED')) + '</p>';
            }).join('') + '</li>';
        }).join('');
      }
    }
    if (state.ui.exposureCardsMore) {
      if (more.length === 0) {
        state.ui.exposureCardsMore.hidden = true;
      } else {
        state.ui.exposureCardsMore.hidden = false;
        var list = state.ui.exposureCardsList;
        var sumExp = state.ui.exposureCardsMore.querySelector('summary');
        if (sumExp) sumExp.innerHTML = '<span class="l-en">See all ' + exposures.length + ' companies</span>' +
                                       '<span class="l-zh">查看全部 ' + exposures.length + ' 家</span>';
        if (list) list.innerHTML = more.map(function (row) {
          return '<li class="fi-exposure-card fi-panel2" data-row-id="' + esc(row.row_id || row.issuer_label) + '">' +
            '<p class="fi-cell-role">' + esc(row.issuer_label || '—') + '</p>' + asArray(row.cells).slice(0, 6).map(function (cell) {
              return '<p><strong>' + esc(sliceName(cell.slice_id, null) || cell.slice_id) + ':</strong> ' +
                esc(labelFor('role', cell.role)) + ' · ' +
                esc(labelFor('materiality', cell.materiality || 'UNMEASURED')) + '</p>';
            }).join('') + '</li>';
        }).join('');
      }
    }
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Macro matrix
  // ──────────────────────────────────────────────────────────────────────────
  var MACRO_DRIVERS = ['policy_rates','yield_curve','deposit_funding','credit_growth','losses_defaults',
                       'housing','equity_levels','volatility','issuance_ma','catastrophe_reinsurance',
                       'regulation_capital','fx','liquidity'];
  function renderMacro() {
    var rowsEl = state.ui.macroRows;
    var theadEl = state.ui.macroThead;
    if (!rowsEl || !theadEl) return;
    var sliceIds = firstVerticalSliceIds();
    var rows = sliceIds.slice(0, 8);
    var matrix = asArray(state.doc && state.doc.macro_matrix);

    theadEl.innerHTML = '<tr><th scope="col"><span class="l-en">Slice</span><span class="l-zh">切片</span></th>' +
      MACRO_DRIVERS.map(function (d) { return '<th scope="col">' + esc(labelFor('driver', d)) + '</th>'; }).join('') + '</tr>';
    if (state.ui.macroTheadMore) state.ui.macroTheadMore.innerHTML = theadEl.innerHTML;

    function buildRow(sliceId) {
      return '<tr data-slice-id="' + esc(sliceId) + '">' +
        '<th scope="row" class="fi-col-company">' + esc(sliceName(sliceId, null)) + '</th>' +
        MACRO_DRIVERS.map(function (driver) {
          var match = matrix.filter(function (m) { return m.slice_id === sliceId && m.driver === driver; })[0];
          if (!match) {
            return '<td class="fi-cell"><span>' + esc(copyPair(SURFACE.not_mapped)) + '</span></td>';
          }
          var mState = match.state || '';
          return '<td class="fi-cell" data-state="' + esc(mState) + '" data-state-marker="' + esc(mState) + '">' +
            '<span' + enLang(match.mechanism) + '>' + esc(match.mechanism || (isZh() ? '尚未描述。' : 'No mechanism on file.')) + '</span>' +
            '<div style="display:flex;gap:4px;flex-wrap:wrap;margin-top:4px">' +
            chipHtml(labelFor('lag', match.lag || 'UNKNOWN'), { stateMarker: match.lag || '' }) +
            chipHtml(labelFor('macro_state', mState), { classes: 'fi-macro-cell-state', stateKey: mState, stateMarker: mState }) +
            '</div></td>';
        }).join('') +
        '</tr>';
    }
    rowsEl.innerHTML = rows.map(buildRow).join('');
    if (state.ui.macroRowsMore) state.ui.macroRowsMore.innerHTML = sliceIds.slice(8).map(buildRow).join('');

    if (state.ui.macroMore) {
      if (sliceIds.length > 8) {
        state.ui.macroMore.hidden = false;
        var sum = state.ui.macroMore.querySelector('summary');
        if (sum) sum.innerHTML = '<span class="l-en">See all ' + sliceIds.length + ' slices</span><span class="l-zh">查看全部 ' + sliceIds.length + ' 个切片</span>';
      } else {
        state.ui.macroMore.hidden = true;
      }
    }
    if (state.ui.macroCards) {
      state.ui.macroCards.innerHTML = rows.map(function (sid) {
        return '<li class="fi-macro-card fi-panel2"><p class="fi-cell-role">' + esc(sliceName(sid, null)) + '</p>' +
          matrix.filter(function (m) { return m.slice_id === sid; }).slice(0, 6).map(function (m) {
            return '<p>' + esc(labelFor('driver', m.driver)) + ': <span' + enLang(m.mechanism) + '>' + esc(m.mechanism || '—') + '</span></p>';
          }).join('') + '</li>';
      }).join('');
    }
    if (state.ui.macroCardsMore) {
      var moreSlices = sliceIds.slice(8);
      if (moreSlices.length === 0) {
        state.ui.macroCardsMore.hidden = true;
      } else {
        state.ui.macroCardsMore.hidden = false;
        var sumMacro = state.ui.macroCardsMore.querySelector('summary');
        if (sumMacro) sumMacro.innerHTML = '<span class="l-en">See all ' + sliceIds.length + ' slices</span><span class="l-zh">查看全部 ' + sliceIds.length + ' 个切片</span>';
        var cardsList = state.ui.macroCardsList;
        if (cardsList) cardsList.innerHTML = moreSlices.map(function (sid) {
          return '<li class="fi-macro-card fi-panel2"><p class="fi-cell-role">' + esc(sliceName(sid, null)) + '</p>' +
            matrix.filter(function (m) { return m.slice_id === sid; }).slice(0, 6).map(function (m) {
              return '<p>' + esc(labelFor('driver', m.driver)) + ': <span' + enLang(m.mechanism) + '>' + esc(m.mechanism || '—') + '</span></p>';
            }).join('') + '</li>';
        }).join('');
      }
    }
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Constraints
  // ──────────────────────────────────────────────────────────────────────────
  function renderConstraints() {
    var ul = state.ui.constraintList;
    if (!ul) return;
    var cons = asArray(state.doc && state.doc.constraints);
    ul.innerHTML = cons.map(function (c) {
      // Item 4: the constraint evidence button names its §D.9 plain-word
      // label ("capital" / "regulatory permission" / ...) so screen readers
      // can pick the right row out of a list.
      var cPair = labelRow('constraint', c.constraint);
      var cEn = cPair[0] || c.constraint || 'constraint';
      var cZh = cPair[1] || cEn;
      return '<li class="fi-constraint-row fi-panel2" data-constraint="' + esc(c.constraint) + '" data-slice-id="' + esc(c.slice_id || '') + '" data-state-marker="' + esc(c.constraint) + '">' +
        chipHtml(labelFor('constraint', c.constraint), { classes: 'fi-constraint-chip', stateConstraint: c.constraint, stateMarker: c.constraint }) +
        '<span class="fi-constraint-effect"' + enLang(c.economic_effect) + '>' + esc(c.economic_effect || (isZh() ? '尚无经济效应记录。' : 'No economic effect on file.')) + '</span>' +
        '<button type="button" class="fi-constraint-evidence fi-step-evidence" data-evidence-ids="' + esc(asArray(c.evidence_refs).join(' ')) + '"' + ariaPair('Open evidence: ' + cEn, '打开证据：' + cZh) + '>↗</button>' +
        '</li>';
    }).join('');
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Provenance + degraded sections
  // ──────────────────────────────────────────────────────────────────────────
  function renderProvenance() {
    var footer = state.ui.provenance;
    if (!footer) return;
    var receipts = asArray(state.doc && state.doc.input_receipts);
    var lines = receipts.filter(function (r) { return r.state !== 'READ'; }).map(function (r) {
      return '<p class="fi-receipt-line">' + esc(labelFor('receipt_owner', r.owner)) + ' · ' + esc(labelFor('receipt_state', r.state)) + (r.note ? ' · ' + esc(r.note) : '') + '</p>';
    }).join('');
    var dec = asArray(state.doc && state.doc.degraded_sections);
    dec.forEach(function (s) {
      var idMap = {
        what_changed: 'what-changed',
        rerating_map: 'rerating-map',
        system_map: 'system-map',
        subtheme_atlas: 'subtheme-atlas',
        company_exposure: 'company-exposure',
        macro_matrix: 'macro-matrix',
        constraint_map: 'constraint-map'
      };
      var section = document.getElementById(idMap[s.section]);
      if (section && s.state !== 'AVAILABLE') {
        section.setAttribute('data-state-partial', 'true');
      }
    });
    footer.innerHTML = lines;
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Evidence drawer — setInert + focus trap + Escape + focus restore
  // ──────────────────────────────────────────────────────────────────────────
  function setInert(el, on) {
    if (!el) return;
    if (on) { el.setAttribute('inert', ''); el.setAttribute('aria-hidden', 'true'); }
    else { el.removeAttribute('inert'); el.removeAttribute('aria-hidden'); }
  }
  function focusableInDrawer() {
    return Array.prototype.slice.call(state.ui.drawer.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )).filter(function (node) { return node.offsetParent !== null; });
  }
  function handleDrawerKeydown(ev) {
    if (!state.ui.drawer.classList.contains('is-open')) return;
    if (ev.key === 'Escape') { ev.preventDefault(); setDrawer(false); return; }
    if (ev.key !== 'Tab') return;
    var focusable = focusableInDrawer();
    if (!focusable.length) { ev.preventDefault(); state.ui.drawer.focus(); return; }
    var first = focusable[0], last = focusable[focusable.length - 1];
    if (ev.shiftKey && document.activeElement === first) { ev.preventDefault(); last.focus(); }
    else if (!ev.shiftKey && document.activeElement === last) { ev.preventDefault(); first.focus(); }
  }
  function setDrawer(open) {
    var wasOpen = state.ui.drawer.classList.contains('is-open');
    if (open) {
      state.lastFocus = document.activeElement;
      state.ui.drawer.hidden = false;
      setInert(state.ui.drawer, false);
      state.ui.drawer.setAttribute('aria-hidden', 'false');
      state.ui.scrim.hidden = false;
      document.body.classList.add('fi-modal-open');
      setInert(state.ui.shell, true);
      setInert(state.ui.siteNav, true);
      window.requestAnimationFrame(function () {
        state.ui.drawer.classList.add('is-open');
        var first = focusableInDrawer()[0];
        if (first) first.focus();
      });
      return;
    }
    state.ui.drawer.classList.remove('is-open');
    setInert(state.ui.drawer, true);
    state.ui.drawer.hidden = true;
    state.ui.scrim.hidden = true;
    document.body.classList.remove('fi-modal-open');
    setInert(state.ui.shell, false);
    setInert(state.ui.siteNav, false);
    if (wasOpen && state.lastFocus && typeof state.lastFocus.focus === 'function') {
      state.lastFocus.focus({ preventScroll: true });
    }
  }

  function renderDrawer(recordId) {
    var fields = state.ui.evidenceFields;
    if (!fields) return;
    var records = asArray(state.doc && state.doc.source_records);
    var rec = records.filter(function (r) { return r.record_id === recordId; })[0];
    state.drawer.source = rec;
    if (!rec) {
      fields.innerHTML = '';
      // A named record that is not in source_records says so; only the bare
      // drawer asks the reader to choose an evidence action.
      show(state.ui.evidenceEmpty, !recordId);
      show(state.ui.evidenceMissing, !!recordId);
      show(state.ui.evidencePrivate, false);
      return;
    }
    // D.23 fails CLOSED: a missing or unrecognised rights_state never displays
    // value/excerpt (its label falls back to "Source rights restrict display").
    var rights = rec.rights_state || '';
    var suppress = !(rights === 'DIRECT_DISPLAY_OK' || rights === 'DERIVED_DISPLAY_OK');
    show(state.ui.evidenceEmpty, false);
    show(state.ui.evidenceMissing, false);
    show(state.ui.evidencePrivate, suppress);

    var rows = [];
    function row(label, value, opts) {
      opts = opts || {};
      if (suppress && opts.sensitive) return;
      rows.push('<dt>' + esc(label) + '</dt><dd' + (opts.identity ? ' class="fi-evidence-identity" data-identity="' + esc(opts.identity) + '"' : '') +
        (opts.rights ? ' class="fi-evidence-rights fi-chip" data-rights="' + esc(rights) + '" data-state-marker="' + esc(rights) + '"' : '') +
        // F7a: only business_scope, the excerpt and limitations are payload prose.
        (opts.prose && value ? ' lang="en"' : '') + '>' + esc(value) + '</dd>');
    }

    row(isZh() ? '记录 ID' : 'Record ID', rec.record_id || '—');
    row(isZh() ? '来源' : 'Source', rec.source && rec.source.publisher ? (rec.source.publisher + ' / ' + (rec.source.source_family || '')) : '');
    row(isZh() ? '业务范围' : 'Business scope', rec.business_scope || '', { prose: true });
    if (!suppress) row(isZh() ? '数值' : 'Value', rec.excerpt || (rec.metric && rec.metric.value) || '', { prose: !!rec.excerpt });
    row(isZh() ? '方法' : 'Methodology', rec.statement_mode ? labelFor('statement_mode', rec.statement_mode) : '');
    row(isZh() ? '观察时点' : 'Observed at', rec.source && rec.source.observed_at ? String(rec.source.observed_at).slice(0, 10) : '');
    row(isZh() ? '披露时点' : 'Published at', rec.source && rec.source.published_at ? String(rec.source.published_at).slice(0, 10) : '', { sensitive: false });
    row(isZh() ? '披露粒度' : 'Published grain', rec.source && rec.source.published_at_grain ? labelFor('published_at_grain', rec.source.published_at_grain) : '');
    row(isZh() ? '陈述方式' : 'Statement mode', rec.statement_mode ? labelFor('statement_mode', rec.statement_mode) : '');
    row(isZh() ? '身份状态' : 'Identity state', labelFor('identity_state', rec.identity_state || ''), { identity: rec.identity_state });
    row(isZh() ? '来源权利' : 'Rights', labelFor('rights_state', rights), { rights: true });
    row(isZh() ? '限制' : 'Limitations', asArray(rec.limitations).join(' · '), { prose: true });
    row(isZh() ? '修正' : 'Correction', rec.correction || '—');
    row(isZh() ? '证据引用' : 'Evidence ref', rec.evidence_ref || '');

    fields.innerHTML = rows.map(function (r) { return '<div>' + r + '</div>'; }).join('');
    // Item 10 (drawer body variant): add the source-language note at the TOP
    // of the drawer body when the drawer holds English-source prose
    // (business_scope, limitations.*, etc.). F7: copy "此记录部分文字为英文原文，
    // 未经翻译。" Idempotent — strip any prior note first.
    var drawer = state.ui.drawer;
    if (drawer) {
      var priorDrawer = drawer.querySelectorAll('.fi-srclang-note');
      for (var pdi = 0; pdi < priorDrawer.length; pdi += 1) priorDrawer[pdi].parentNode.removeChild(priorDrawer[pdi]);
      if (isZh() && fields.querySelector('[lang="en"]')) {
        var drawerNote = document.createElement('p');
        drawerNote.className = 'fi-srclang-note l-zh';
        drawerNote.textContent = '此记录部分文字为英文原文，未经翻译。';
        if (fields.parentNode) {
          // Insert as the FIRST child of the drawer body so the reader sees
          // the note above the bilingual field list (F7).
          fields.parentNode.insertBefore(drawerNote, fields.parentNode.firstChild);
        }
      }
    }
  }

  function openEvidence(recordIds) {
    if (!recordIds) return;
    var first = String(recordIds).split(' ').filter(Boolean)[0];
    if (!first) return;
    var target = '#evidence=' + encodeURIComponent(first);
    if (location.hash === target) { handleHash(); return; }
    location.hash = target;
  }

  function hashPart(raw) {
    try { return decodeURIComponent(raw); } catch (e) { return null; }
  }

  function handleHash() {
    var h = location.hash.slice(1);
    if (!h) return;
    var m1 = h.match(/^slice=([^&]+)/);
    var m2 = h.match(/^evidence=([^&]+)/);
    if (m1 && hashPart(m1[1]) !== null) {
      state.sliceId = hashPart(m1[1]);
      if (state.ui.sliceSelect) state.ui.sliceSelect.value = state.sliceId;
      mirrorFreshness();
      renderRerating();
    }
    if (m2 && hashPart(m2[1]) !== null) {
      var id = hashPart(m2[1]);
      renderDrawer(id);
      setDrawer(true);
    }
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Notice (E.3 status mapping)
  // ──────────────────────────────────────────────────────────────────────────
  function renderNotice(kind, payload) {
    var notice = document.querySelector('[data-fi-mount="notice"]');
    var en = document.querySelector('[data-fi-mount="notice-en"]');
    var zh = document.querySelector('[data-fi-mount="notice-zh"]');
    if (!notice) return;
    var map = {
      not_connected: ['Not yet connected to the evidence service.', '尚未接入证据服务。'],
      locked: ['Sign in to read current research', '请登录以查阅当前研究'],
      not_entitled: ['This dossier is part of the research tier', '此报告为研究层内容'],
      private_store_unavailable: ['Private evidence store unavailable', '私有证据库暂不可用'],
      no_generation: ['No evidence generation published yet — re-drawn after the next nightly', '尚未发布证据版本，夜间更新后重绘'],
      generation_torn: ['Generation interrupted — partial context only', '生成中断 — 仅展示部分背景'],
      contract_invalid: ['Contract mismatch — showing public shell only', '契约不一致 — 仅展示公开外壳'],
      network: ["Couldn't load — try again", '未能加载 — 请重试'],
      source_outage: ['Evidence source temporarily unavailable — try again later', '证据来源暂不可用 — 请稍后重试'],
      unknown: ['Read failed', '读取失败']
    };
    var pair = map[kind] || map.unknown;
    if (en) en.textContent = pair[0];
    if (zh) zh.textContent = pair[1];
    show(notice, true);
    $$('.fi-section, .fi-toc').forEach(function (s) { s.style.display = 'none'; });
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Hydration orchestrator
  // ──────────────────────────────────────────────────────────────────────────
  function hydrate(doc) {
    state.doc = doc;
    state.ui.shell = document.getElementById('fi-main');
    state.ui.siteNav = document.querySelector('nav.site-nav');
    state.ui.drawer = document.getElementById('evidence-drawer');
    state.ui.scrim = document.getElementById('fi-scrim');
    state.ui.closeBtn = document.getElementById('fi-close-evidence');
    state.ui.heroAsof = document.querySelector('[data-fi-mount="hero-asof"]');
    state.ui.heroAsofZh = document.querySelector('[data-fi-mount="hero-asof-zh"]');
    state.ui.heroCutoff = document.querySelector('[data-fi-mount="hero-cutoff"]');
    state.ui.heroCutoffZh = document.querySelector('[data-fi-mount="hero-cutoff-zh"]');
    state.ui.heroFreshness = document.querySelector('[data-fi-mount="hero-freshness"]');
    state.ui.heroOuter = document.querySelector('[data-fi-mount="hero-outer"]');
    state.ui.provenance = document.querySelector('[data-fi-mount="provenance"]');
    state.ui.whatChangedList = document.querySelector('[data-fi-mount="what-changed-list"]');
    state.ui.sliceSelect = document.getElementById('fi-slice-select');
    state.ui.reratingSteps = document.querySelector('[data-fi-mount="rerating-steps"]');
    state.ui.reratingBridge = document.querySelector('[data-fi-mount="rerating-bridge"]');
    state.ui.falsifiers = document.querySelector('[data-fi-mount="falsifiers"]');
    state.ui.conflictList = document.querySelector('[data-fi-mount="conflict-list"]');
    state.ui.viewTabs = document.querySelector('[data-fi-mount="view-tabs"]');
    state.ui.viewPanels = document.querySelector('[data-fi-mount="view-panels"]');
    state.ui.domainGrid = document.querySelector('[data-fi-mount="domain-grid"]');
    state.ui.coverageEyebrow = document.querySelector('[data-fi-mount="coverage-eyebrow"]');
    state.ui.atlasGap = document.querySelector('[data-fi-mount="atlas-gap"]');
    state.ui.exposureThead = document.querySelector('[data-fi-mount="exposure-thead"]');
    state.ui.exposureTheadMore = document.querySelector('[data-fi-mount="exposure-thead-more"]');
    state.ui.exposureRows = document.querySelector('[data-fi-mount="exposure-rows"]');
    state.ui.exposureRowsMore = document.querySelector('[data-fi-mount="exposure-rows-more"]');
    state.ui.exposureMore = document.querySelector('[data-fi-mount="exposure-more"]');
    state.ui.exposureCards = document.querySelector('[data-fi-mount="exposure-cards"]');
    state.ui.exposureCardsMore = document.querySelector('[data-fi-mount="exposure-cards-more"]');
    state.ui.exposureCardsList = document.querySelector('[data-fi-mount="exposure-cards-list"]');
    state.ui.macroThead = document.querySelector('[data-fi-mount="macro-thead"]');
    state.ui.macroTheadMore = document.querySelector('[data-fi-mount="macro-thead-more"]');
    state.ui.macroRows = document.querySelector('[data-fi-mount="macro-rows"]');
    state.ui.macroRowsMore = document.querySelector('[data-fi-mount="macro-rows-more"]');
    state.ui.macroMore = document.querySelector('[data-fi-mount="macro-more"]');
    state.ui.macroCards = document.querySelector('[data-fi-mount="macro-cards"]');
    state.ui.macroCardsMore = document.querySelector('[data-fi-mount="macro-cards-more"]');
    state.ui.macroCardsList = document.querySelector('[data-fi-mount="macro-cards-list"]');
    state.ui.constraintList = document.querySelector('[data-fi-mount="constraint-list"]');
    state.ui.evidenceFields = document.querySelector('[data-fi-mount="evidence-fields"]');
    state.ui.evidenceEmpty = document.querySelector('[data-fi-mount="evidence-empty"]');
    state.ui.evidenceMissing = document.querySelector('[data-fi-mount="evidence-missing"]');
    state.ui.evidencePrivate = document.querySelector('[data-fi-mount="evidence-private-notice"]');
    state.ui.notice = document.querySelector('[data-fi-mount="notice"]');
    state.ui.noticeEn = document.querySelector('[data-fi-mount="notice-en"]');
    state.ui.noticeZh = document.querySelector('[data-fi-mount="notice-zh"]');

    renderHero();
    renderWhatChanged();
    renderSliceSelector();
    mirrorFreshness();
    renderRerating();
    renderSystem();
    renderAtlas();
    renderExposure();
    renderMacro();
    renderConstraints();
    renderProvenance();
    renderSourceLangNote(document.getElementById('what-changed'));
    renderSourceLangNote(document.getElementById('rerating-map'));
    renderSourceLangNote(document.getElementById('system-map'));
    renderSourceLangNote(document.getElementById('subtheme-atlas'));
    renderSourceLangNote(document.getElementById('company-exposure'));
    renderSourceLangNote(document.getElementById('macro-matrix'));
    renderSourceLangNote(document.getElementById('constraint-map'));

    if (state.ui.sliceSelect) {
      state.ui.sliceSelect.addEventListener('change', function () {
        state.sliceId = state.ui.sliceSelect.value;
        if (history && history.replaceState) history.replaceState(null, '', '#slice=' + encodeURIComponent(state.sliceId));
        mirrorFreshness();
        renderRerating();
      });
    }

    document.addEventListener('click', function (ev) {
      var t = ev.target;
      if (!t) return;
      var btn = t.closest && t.closest('.fi-evidence-trigger, .fi-step-evidence, .fi-constraint-evidence, .fi-slice-open, .fi-toc-evidence');
      if (btn) {
        if (btn.classList.contains('fi-slice-open')) return;
        ev.preventDefault();
        var ids = btn.getAttribute('data-evidence-ids') || '';
        if (ids) openEvidence(ids);
        else {
          renderDrawer('');
          setDrawer(true);
        }
      }
    });

    if (state.ui.closeBtn) state.ui.closeBtn.addEventListener('click', function () { setDrawer(false); });
    if (state.ui.scrim) state.ui.scrim.addEventListener('click', function () { setDrawer(false); });
    document.addEventListener('keydown', handleDrawerKeydown);
    window.addEventListener('hashchange', handleHash);
    document.addEventListener('langchange', function () {
      // Item 8: capture which system tab held focus before the re-render.
      // renderSystem() below rebuilds the tab DOM from scratch, so the
      // original element is gone — we restore to the new tab that shares the
      // same data-view. If focus was elsewhere, leave it alone (the global
      // ARIA swapper has already swapped aria-label on the focused element).
      var preViewFocus = null;
      try {
        var ae = document.activeElement;
        if (ae && ae.classList && ae.classList.contains('fi-view-tab') && ae.dataset && ae.dataset.view) {
          preViewFocus = ae.dataset.view;
        }
      } catch (e) { /* focus probe is best-effort */ }
      renderHero();
      renderWhatChanged();
      renderSliceSelector();
      renderRerating();
      renderSystem();
      renderAtlas();
      renderExposure();
      renderMacro();
      renderConstraints();
      renderProvenance();
      renderSourceLangNote(document.getElementById('what-changed'));
      renderSourceLangNote(document.getElementById('rerating-map'));
      renderSourceLangNote(document.getElementById('system-map'));
      renderSourceLangNote(document.getElementById('subtheme-atlas'));
      renderSourceLangNote(document.getElementById('company-exposure'));
      renderSourceLangNote(document.getElementById('macro-matrix'));
      renderSourceLangNote(document.getElementById('constraint-map'));
      if (state.drawer.source) renderDrawer(state.drawer.source.record_id);
      if (preViewFocus) {
        var newTab = document.querySelector('.fi-view-tab[data-view="' + preViewFocus + '"]');
        if (newTab && typeof newTab.focus === 'function') newTab.focus({ preventScroll: true });
      }
    });

    handleHash();
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Boot — single read
  // ──────────────────────────────────────────────────────────────────────────
  function boot() {
    var mainEl = document.getElementById('fi-main');
    FI_READ_URL = mainEl ? (mainEl.getAttribute('data-fi-read-url') || '').trim() : '';
    if (!FI_READ_URL) {
      if (mainEl) mainEl.setAttribute('data-state', 'not-connected');
      renderNotice('not_connected');
      return; // no endpoint bound yet — the shell stays data-free and says so
    }
    fetchJson(FI_READ_URL).then(function (doc) {
      if (!doc || doc.contract_id !== 'finance_intelligence_read_model.v1') {
        renderNotice('contract_invalid');
        return;
      }
      hydrate(doc);
    }).catch(function (err) {
      var kind = hydrationKind(err);
      if (typeof console !== 'undefined' && console.error) console.error('[fi-hydration-err]', kind, err && err.message, err && err.stack);
      if (kind === 'locked') renderNotice('locked');
      else if (kind === 'integrity_block') renderNotice('contract_invalid');
      else if (kind === 'source_outage') renderNotice('source_outage');
      else renderNotice('unknown');
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
