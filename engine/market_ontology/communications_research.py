"""Communications Task4A: pure claim projection, NOT the shared wire adapter.

The caller supplies an already-authorized, owner-selected in-memory observation
set. These types do not admit sources, establish issuer identity, decide rights,
read stores, select a generation, register a native schema or expose a route.
Native translation into these inputs remains UNBOUND. Nonempty fixture/reference
strings are not admission receipts. No research or test file is loaded here.

The public roster is presentation scope, not canonical membership/security data.
Future native callers must qualify each issuer/metric-role/population mapping
before constructing these objects. Missing records cannot establish absence.
Only resolved observations may support output; stale rule pointers never recover
withheld bodies. This is not a new evidence/rights/correction store or cache.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from engine.market_ontology.communications_measures import (
    AccountingBridgeResult, AccountingRule, ComparisonRule, Guidance, InputBinding,
    Measure, Result, accounting_bridge, compare_guidance, compare_period,
    _measure, _text,  # Same domain's structural validation, NEVER native admission.
)


class ClaimInputError(ValueError):
    """Fixed domain refusal code; never echo a source or caller value."""


@dataclass(frozen=True)
class PairSelection:
    current_ref: str | None
    prior_ref: str | None
    rule: ComparisonRule | None


@dataclass(frozen=True)
class CompanyClaimInput:
    slot: str
    measures: tuple[Measure, ...]
    pairs: tuple[PairSelection, PairSelection]
    guide: Guidance | None = None
    guide_rule: ComparisonRule | None = None
    accounting_rules: tuple[AccountingRule, ...] = ()


@dataclass(frozen=True)
class ClaimText:
    en: str
    zh: str
    refs: tuple[str, ...]
    rule_revisions: tuple[str, ...]
    interpretation_basis: str


@dataclass(frozen=True)
class MeasureClaim:
    metric: str
    current: Measure | None
    prior: Measure | None
    comparison: Result | None
    trend: ClaimText | None


@dataclass(frozen=True)
class AccountingViewGroup:
    outcome_refs: tuple[str, ...]
    views: tuple[AccountingBridgeResult, ...]


@dataclass(frozen=True)
class CompanyClaims:
    slot: str
    name: str
    measures: tuple[MeasureClaim, MeasureClaim]
    headline: ClaimText | None
    guidance: Result | None
    accounting: tuple[AccountingViewGroup, ...]
    next_observation_en: str
    next_observation_zh: str
    original_guidance: Guidance | None = None
    limitation_en: str = ''
    limitation_zh: str = ''


@dataclass(frozen=True)
class ProjectionAuthority:
    can_rank: bool = False
    can_gate: bool = False
    can_size: bool = False
    can_originate: bool = False
    can_open_entry: bool = False


@dataclass(frozen=True)
class FourCompanyClaims:
    panels: tuple[CompanyClaims, ...]
    headline_issuer_count: int
    expected_issuer_count: int = 4
    limitations: tuple[str, ...] = (
        'native_source_mapping_unbound', 'shared_delivery_unbound',
        'source_completeness_unqualified',
    )
    authority: ProjectionAuthority = ProjectionAuthority()


# Local role keys are NOT native metric IDs. The future owner adapter must prove
# their semantic mapping; this dictionary cannot mint an issuer/security binding.
_PROFILES = MappingProxyType({
    'meta': ('Meta', (('revenue', 'revenue', '营收'),
                     ('operating_income', 'operating income', '营业利润')),
             'Inspect comparable monetization-to-profit and cash conversion.',
             '观察可比口径下的变现、利润与现金转化。'),
    'alphabet': ('Alphabet', (('search_other_revenue', 'Search & other revenue', '搜索及其他营收'),
                             ('network_revenue', 'Network revenue', '广告网络营收')),
                 'Inspect category monetization and separately disclosed investment conversion.',
                 '观察各业务的变现及单独披露的投资转化。'),
    'trade_desk': ('The Trade Desk', (('revenue', 'revenue', '营收'),
                                    ('operating_income', 'operating income', '营业利润')),
                   'Inspect comparable customer spending, costs and retained economics.',
                   '观察可比客户支出、成本与留存经济收益。'),
    'magnite': ('Magnite', (('contribution_ex_tac', 'contribution ex-TAC', '扣除流量获取成本后的贡献额'),
                          ('gross_profit', 'gross profit', '毛利')),
                'Inspect channel contribution and conversion into comparably defined profit and cash.',
                '观察渠道贡献及向可比口径利润和现金的转化。'),
})
# Fixed caveats qualify the role interpretation; none reveals missing private rows.
_CAVEATS = MappingProxyType({
    'meta': ('Reported issuer figures do not establish advertising-only costs or returns on AI.',
             '发行主体层面的报告数据不能确定广告专属成本或人工智能投资回报。'),
    'alphabet': ('Business revenues do not allocate consolidated cash or capital expenditure to Search.',
                 '业务营收并不把合并现金或资本支出分配给搜索业务。'),
    'trade_desk': ('Reported figures do not establish organic growth, market-share transfer or consensus surprise.',
                   '报告数据不能证明有机增长、市场份额转移或相对分析师共识的超预期。'),
    'magnite': ('Contribution ex-TAC is issuer-defined; alternative accounting views are not independent confirmations.',
                '扣除流量获取成本后的贡献额由发行主体定义；不同核对视角并非独立证实。'),
})
_ROSTER = tuple(_PROFILES)
_MAX_OBSERVATIONS = 96
_MAX_ACCOUNTING_VIEWS = 8


def _validate_inputs(inputs):
    if type(inputs) is not tuple:
        raise ClaimInputError('INVALID_CLAIM_INPUT')
    if len(inputs) > 4:
        raise ClaimInputError('CLAIM_INPUT_LIMIT')
    slots, observations, revisions = {}, {}, {}
    observed_count = accounting_count = 0

    def record_rule(candidate):
        comparison = candidate.comparison if type(candidate) is AccountingRule else candidate
        if type(comparison) is not ComparisonRule or not _text(comparison.revision):
            return
        if type(comparison.bindings) is not tuple:
            return
        if len(comparison.bindings) > 16:
            raise ClaimInputError('CLAIM_INPUT_LIMIT')
        if type(candidate) is AccountingRule:
            if ((type(candidate.terms) is tuple and len(candidate.terms) > 7)
                    or (type(candidate.dependencies) is tuple and len(candidate.dependencies) > 16)):
                raise ClaimInputError('CLAIM_INPUT_LIMIT')
        key = comparison.revision
        if key in revisions and revisions[key] != candidate:
            raise ClaimInputError('RULE_REVISION_CONFLICT')
        revisions[key] = candidate

    for item in inputs:
        if (type(item) is not CompanyClaimInput or type(item.slot) is not str
                or item.slot not in _PROFILES or type(item.measures) is not tuple
                or type(item.pairs) is not tuple or len(item.pairs) != 2
                or type(item.accounting_rules) is not tuple
                or (item.guide is not None and type(item.guide) is not Guidance)):
            raise ClaimInputError('INVALID_CLAIM_INPUT')
        if item.slot in slots:
            raise ClaimInputError('DUPLICATE_ISSUER')
        observed_count += len(item.measures) + int(item.guide is not None)
        accounting_count += len(item.accounting_rules)
        if observed_count > _MAX_OBSERVATIONS or accounting_count > _MAX_ACCOUNTING_VIEWS:
            raise ClaimInputError('CLAIM_INPUT_LIMIT')
        for pair in item.pairs:
            if (type(pair) is not PairSelection
                    or any(ref is not None and not _text(ref) for ref in (pair.current_ref, pair.prior_ref))):
                raise ClaimInputError('INVALID_CLAIM_INPUT')
            record_rule(pair.rule)
        for recipe in item.accounting_rules:
            if type(recipe) is not AccountingRule:
                raise ClaimInputError('INVALID_CLAIM_INPUT')
            record_rule(recipe)
        record_rule(item.guide_rule)
        for observation in item.measures + (() if item.guide is None else (item.guide,)):
            if type(observation) not in (Measure, Guidance) or not _text(observation.ref):
                raise ClaimInputError('INVALID_CLAIM_INPUT')
            if observation.ref in observations:
                previous_slot, previous = observations[observation.ref]
                if previous_slot != item.slot:
                    raise ClaimInputError('CROSS_ISSUER_INPUT_REUSE')
                if previous != observation:
                    raise ClaimInputError('INPUT_REVISION_CONFLICT')
            observations[observation.ref] = (item.slot, observation)
        slots[item.slot] = item
    return slots


def _claim(en, zh, results) -> ClaimText:
    # Copy is generated here from reviewed fixed role labels and tested results,
    # not supplied by the input or retained across composition calls.
    if not 0 < len(en) <= 240 or not 0 < len(zh) <= 240:
        raise ClaimInputError('CLAIM_TEXT_LIMIT')
    return ClaimText(en, zh,
        tuple(dict.fromkeys(ref for result in results for ref in result.refs)),
        tuple(dict.fromkeys(result.rule_revision for result in results)),
        'exact_reported_values' if all(result.status == 'COMPARABLE' for result in results) else 'published_figures')


def _row(profile, selection, observed) -> MeasureClaim:
    metric, en, zh = profile
    def resolve(ref):
        value = observed.get(ref)
        return value if (value is not None and value.metric == metric
                         and value.unit == 'currency' and value.currency == 'USD'
                         and (value.value is not None or value.support is not None)) else None
    current, prior = resolve(selection.current_ref), resolve(selection.prior_ref)
    comparison = trend = None
    if current is not None and prior is not None:
        mode = 'absolute' if (type(selection.rule) is ComparisonRule
                              and selection.rule.operation == 'period_absolute') else 'pct'
        comparison = compare_period(current, prior, rule=selection.rule, mode=mode)
        if comparison.status in ('COMPARABLE', 'QUALIFIED') and comparison.value is not None:
            direction = 1 if comparison.value > 0 else -1 if comparison.value < 0 else 0
            word_en, word_zh = {1: ('increased', '增加'), -1: ('decreased', '减少'),
                               0: ('was unchanged', '保持不变')}[direction]
            trend = _claim(f'Reported {en} {word_en}.', f'报告{zh}{word_zh}。', (comparison,))
    return MeasureClaim(metric, current, prior, comparison, trend)


def _accounting_views(item, rows, observed):
    grouped = {}
    for recipe in item.accounting_rules:
        comparison = recipe.comparison
        if (type(comparison) is not ComparisonRule or type(comparison.bindings) is not tuple
                or not 1 <= len(comparison.bindings) <= 16
                or any(type(b) is not InputBinding or not _text(b.ref) for b in comparison.bindings)):
            continue
        refs = tuple(dict.fromkeys(b.ref for b in comparison.bindings))
        if any(ref not in observed for ref in refs):
            continue
        view = accounting_bridge(measures=tuple(observed[ref] for ref in refs), rule=recipe)
        if view.reconstructed_current is None or view.current_output is None or view.prior_output is None:
            continue
        # A retained historical record cannot replace the selected corrected total.
        # Other accounting populations keep their explicit source scope and period.
        matching = next((row for row in rows if row.metric == view.current_output.metric), None)
        if matching is not None and (matching.current is None or matching.prior is None
                or matching.current.ref != view.current_output.ref
                or matching.prior.ref != view.prior_output.ref):
            continue
        key = view.outcome_refs
        grouped.setdefault(key, {})[view.result.rule_revision] = view
    return tuple(AccountingViewGroup(key, tuple(views[revision] for revision in sorted(views)))
                 for key, views in sorted(grouped.items()))


def compose_four_company_claims(inputs: tuple[CompanyClaimInput, ...]) -> FourCompanyClaims:
    """Project already-selected facts; never load, refresh, authorize or cache them.

    Fixed coverage is four public issuer slots even when no observations arrive.
    Headline count measures only composed headlines, NOT source completeness,
    readiness, identity qualification, securities coverage or release acceptance.
    A later shared adapter must bind its actual query, authorized owner bundle,
    generation and closed schema. This function deliberately implements none of
    those contracts and must not be registered directly as the shared composer.
    """
    selected = _validate_inputs(inputs)
    panels = []
    for slot in _ROSTER:
        name, profiles, next_en, next_zh = _PROFILES[slot]
        caveat_en, caveat_zh = _CAVEATS[slot]
        item = selected.get(slot)
        if item is None:
            rows = tuple(MeasureClaim(profile[0], None, None, None, None) for profile in profiles)
            panels.append(CompanyClaims(slot, name, rows, None, None, (), next_en, next_zh,
                                        limitation_en=caveat_en, limitation_zh=caveat_zh))
            continue
        # This ephemeral index covers ONLY records supplied by the authorized
        # owner. There is no alternate read, rights inference or retained state.
        observed = {m.ref: m for m in item.measures if _measure(m)}
        rows = tuple(_row(profile, pair, observed) for profile, pair in zip(profiles, item.pairs))
        headline = None
        if (all(row.trend is not None for row in rows)
                and rows[0].current.period == rows[1].current.period
                and rows[0].prior.period == rows[1].prior.period):
            first, second = (row.trend for row in rows)
            headline = _claim(first.en[:-1] + '; ' + second.en[0].lower() + second.en[1:],
                              first.zh[:-1] + '；' + second.zh,
                              tuple(row.comparison for row in rows))
        guide_result = None
        if (slot != 'alphabet' and rows[0].current is not None and item.guide is not None
                and item.guide.vintage == 'original_company_guidance'):
            candidate = compare_guidance(rows[0].current, item.guide, rule=item.guide_rule)
            if candidate.status in ('COMPARABLE', 'QUALIFIED'):
                guide_result = candidate
        panels.append(CompanyClaims(slot, name, rows, headline, guide_result,
                                    _accounting_views(item, rows, observed), next_en, next_zh,
                                    original_guidance=item.guide if guide_result is not None else None,
                                    limitation_en=caveat_en, limitation_zh=caveat_zh))
    return FourCompanyClaims(tuple(panels), sum(panel.headline is not None for panel in panels))
