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

from dataclasses import dataclass, fields
from decimal import Decimal
from functools import lru_cache
import json
from pathlib import Path
from types import MappingProxyType

from engine.market_ontology.communications_measures import (
    AccountingBridgeResult, AccountingContribution, AccountingRule, ComparisonRule,
    Guidance, InputBinding, Interval, Measure, Result,
    accounting_bridge, compare_guidance, compare_period,
    _guidance, _measure, _same_scope, _text,  # Domain validation, NEVER native admission.
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
    explanations: tuple[ClaimText | None, ...] = ()


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


# Display vocabulary for the frozen A1 accounting examples, NOT a native
# metric registry or an admission rule. Unknown roles retain their numbers but
# receive no inferred prose. The caller still owes accepted source/rule mapping.
_ACCOUNTING_LABELS = MappingProxyType({
    'revenue': ('revenue', '营收'),
    'cost_of_revenue': ('cost of revenue', '营收成本'),
    'research_development': ('research and development', '研发'),
    'marketing_sales': ('marketing and sales', '营销与销售'),
    'general_admin': ('general and administrative costs', '一般及行政费用'),
    'operating_cash': ('operating cash', '经营现金流'),
    'property_equipment': ('property and equipment spending', '物业及设备支出'),
    'lease_principal': ('finance-lease principal', '融资租赁本金'),
    'search_other': ('Search and other', '搜索及其他'),
    'youtube_ads': ('YouTube advertising', 'YouTube广告'),
    'network': ('Network', '广告网络'),
    'platform_operations': ('platform operations', '平台运营'),
    'sales_marketing': ('sales and marketing', '销售与营销'),
    'technology_development': ('technology and development', '技术与开发'),
    'derived_tac': ('derived TAC', '推算的流量获取成本'),
    'ctv': ('CTV', '联网电视'),
    'mobile': ('mobile', '移动端'),
    'desktop': ('desktop', '桌面端'),
})
_ACCOUNTING_ROLES = MappingProxyType({
    'meta': frozenset(('revenue', 'cost_of_revenue', 'research_development',
        'marketing_sales', 'general_admin', 'operating_cash', 'property_equipment', 'lease_principal')),
    'alphabet': frozenset(('search_other', 'youtube_ads', 'network', 'operating_cash', 'property_equipment')),
    'trade_desk': frozenset(('revenue', 'platform_operations', 'sales_marketing',
        'technology_development', 'general_admin')),
    'magnite': frozenset(('revenue', 'derived_tac', 'cost_of_revenue', 'ctv', 'mobile', 'desktop')),
})


def _accounting_copy(slot, residual, relation, contributions):
    """Explain signed contributions, not their causes or investment desirability.

    Input is the existing comparator output. No new amount, ratio, interval,
    independence score or causal inference is computed. A tie is a tie.
    """
    allowed = _ACCOUNTING_ROLES.get(slot, frozenset())
    if not contributions or any(key not in allowed for key, _, _ in contributions):
        return None
    if residual != 0:
        return ('The reported total does not reconcile with these components; the difference remains unallocated.',
                '报告总额与这些分项无法核对一致；差额尚未分配。')
    if relation == 'TARGET_DEPENDENT':
        return ('This reconciliation uses the reported total in a derived component; it is not independent confirmation of that total.',
                '此项核对的推算分项使用了报告总额；这并非独立验证该总额。')
    if relation == 'DECLARED_DEPENDENCE':
        return ('Some components share derived inputs; this accounting bridge is not independent corroboration.',
                '部分分项共享推算输入；这项会计核对并非独立验证。')
    if relation != 'INDEPENDENCE_UNASSESSED':
        return None
    en, zh = [], []
    for upward in (True, False):
        selected = [(key, value, delta) for key, value, delta in contributions if (value > 0 if upward else value < 0)]
        if not selected:
            continue
        extreme = (max if upward else min)(value for _, value, _ in selected)
        keys = [key for key, value, _ in selected if value == extreme]
        direction, chinese = ('upward', '上行') if upward else ('downward', '下行')
        if len(keys) > 1:
            en.append(f'Multiple components tie for the largest {direction} contribution.')
            zh.append(f'多个分项并列贡献最大的{chinese}变化。')
        else:
            label_en, label_zh = _ACCOUNTING_LABELS[keys[0]]
            delta = next(delta for key, _, delta in selected if key == keys[0])
            change_en, change_zh = ('increase', '增加') if delta > 0 else ('decrease', '减少')
            en.append(f'Largest {direction} contribution: {label_en} ({change_en}).')
            zh.append(f'最大{chinese}贡献：{label_zh}（{change_zh}）。')
    if not en:
        en.append('No displayed component changed across the selected periods.')
        zh.append('所选期间内各展示分项均未发生变化。')
    en.append('Reported-figure bridge, not causal evidence.')
    zh.append('这是报告数值的会计核对，并非因果证据。')
    return ' '.join(en), ''.join(zh)


def _accounting_explanation(slot, view):
    copy = _accounting_copy(slot, view.residual, view.evidence_relation,
                            tuple((part.component_key, part.contribution, part.delta) for part in view.contributions))
    return None if copy is None else _claim(*copy, (view.result,))


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
    groups = []
    for key, views in sorted(grouped.items()):
        ordered_views = tuple(views[revision] for revision in sorted(views))
        groups.append(AccountingViewGroup(key, ordered_views,
                      tuple(_accounting_explanation(item.slot, view) for view in ordered_views)))
    return tuple(groups)


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


# Unregistered domain response candidate; no native generation/profile is minted.
MAX_VIEW_BYTES = 256 * 1024
_PAYLOAD_TYPES = frozenset((FourCompanyClaims, CompanyClaims, MeasureClaim, ClaimText,
    ProjectionAuthority, AccountingViewGroup, AccountingBridgeResult,
    AccountingContribution, Measure, Guidance, Interval, Result))


def _plain_projection(value, depth=0):
    """Explicit closed conversion, never deepcopy or caller-provided conversion hooks."""
    if depth > 24:
        raise ClaimInputError('INVALID_CLAIM_VIEW')
    kind = type(value)
    if kind in _PAYLOAD_TYPES:
        return {field.name: _plain_projection(getattr(value, field.name), depth + 1)
                for field in fields(kind)}
    if kind is tuple:
        if len(value) > 96:
            raise ClaimInputError('CLAIM_OUTPUT_LIMIT')
        return [_plain_projection(item, depth + 1) for item in value]
    if kind is Decimal:
        if not value.is_finite():
            raise ClaimInputError('INVALID_CLAIM_VIEW')
        parts = value.as_tuple()
        if len(parts.digits) > 384 or abs(parts.exponent) > 384:
            raise ClaimInputError('CLAIM_OUTPUT_LIMIT')
        text = format(value, 'f')
        if len(text) > 384:
            raise ClaimInputError('CLAIM_OUTPUT_LIMIT')
        return text
    if value is None or kind in (str, int, bool):
        return value
    raise ClaimInputError('INVALID_CLAIM_VIEW')


def _encoded_view(payload):
    # Bound shape BEFORE JSON/schema traversal. Only ordinary JSON values are
    # accepted: no mapping subclasses, iterators, floats, callbacks or cycles.
    nodes = 0
    text_bytes = 0
    def guard(value, depth=0):
        nonlocal nodes, text_bytes
        nodes += 1
        if depth > 32 or nodes > 16384:
            raise ClaimInputError('CLAIM_OUTPUT_LIMIT')
        kind = type(value)
        if kind is str:
            if len(value) > MAX_VIEW_BYTES:
                raise ClaimInputError('CLAIM_OUTPUT_LIMIT')
            try:
                text_bytes += len(value.encode('utf-8'))
            except UnicodeError:
                raise ClaimInputError('INVALID_CLAIM_VIEW') from None
            if text_bytes > MAX_VIEW_BYTES:
                raise ClaimInputError('CLAIM_OUTPUT_LIMIT')
        elif kind is dict:
            if len(value) > 96 or any(type(key) is not str for key in value):
                raise ClaimInputError('INVALID_CLAIM_VIEW')
            for key, item in value.items():
                guard(key, depth + 1)
                guard(item, depth + 1)
        elif kind is list:
            if len(value) > 96:
                raise ClaimInputError('CLAIM_OUTPUT_LIMIT')
            for item in value:
                guard(item, depth + 1)
        elif kind is int:
            if abs(value) > 96:
                raise ClaimInputError('INVALID_CLAIM_VIEW')
        elif value is not None and kind is not bool:
            raise ClaimInputError('INVALID_CLAIM_VIEW')
    guard(payload)
    encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False,
                         separators=(',', ':')).encode('utf-8')
    if len(encoded) > MAX_VIEW_BYTES:
        raise ClaimInputError('CLAIM_OUTPUT_LIMIT')
    return encoded


@lru_cache(maxsize=1)
def _view_validator():
    # This is a shipped code contract, not a data reader. The path is fixed;
    # no request chooses a file or reference resolver, and all $refs are local.
    from jsonschema import Draft202012Validator, FormatChecker
    path = Path(__file__).resolve().parents[2] / 'contracts/market_ontology/communications_business_research.v1.schema.json'
    try:
        schema = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise ClaimInputError('CLAIM_CONTRACT_UNAVAILABLE') from None
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _wire_decimal(text):
    # Fixed-point output may expand a valid source coefficient by up to 32 zeroes.
    # Recover a bounded equivalent WITHOUT context-sensitive normalize/rounding.
    value = Decimal(text)
    sign, digits, exponent = value.as_tuple()
    digits = list(digits)
    while len(digits) > 48 and digits[-1] == 0 and exponent < 32:
        digits.pop()
        exponent += 1
    return Decimal((sign, tuple(digits), exponent))


def _payload_measure(record):
    data = dict(record)
    data['period'] = tuple(data['period'])
    for key in ('value', 'scale'):
        if data[key] is not None:
            data[key] = _wire_decimal(data[key])
    if data['support'] is not None:
        support = data['support']
        data['support'] = Interval(_wire_decimal(support['lower']), _wire_decimal(support['upper']),
                                   support['lower_inclusive'], support['upper_inclusive'])
    candidate = Measure(**data)
    return candidate if _measure(candidate) else None


def _payload_guidance(record):
    data = dict(record)
    data['period'] = tuple(data['period'])
    for key in ('lower', 'upper', 'scale'):
        if data[key] is not None:
            data[key] = _wire_decimal(data[key])
    candidate = Guidance(**data)
    return candidate if _guidance(candidate) else None


def _view_links_valid(projection):
    """Internal consistency only: it does not authenticate sources or approve copy."""
    if projection['headline_issuer_count'] != sum(p['headline'] is not None for p in projection['panels']):
        return False
    source_refs, derived_count = set(), 0
    observations = {}

    def consistent_record(record, slot):
        # One ephemeral response check, not an identity/revision/source store.
        # Match the input composer's rule: a reference cannot acquire another
        # issuer, record kind, value or context between visible output copies.
        known = observations.get(record['ref'])
        if known is not None:
            return known[0] == slot and known[1] == record
        observations[record['ref']] = (slot, record)
        return True

    def matches(claim, results):
        refs = list(dict.fromkeys(ref for result in results for ref in result['refs']))
        revisions = list(dict.fromkeys(result['rule_revision'] for result in results))
        return claim['refs'] == refs and claim['rule_revisions'] == revisions
    for panel in projection['panels']:
        rows = panel['measures']
        for row in rows:
            actual, prior, result, trend = (row[key] for key in ('current','prior','comparison','trend'))
            source_refs.update(m['ref'] for m in (actual, prior) if m is not None)
            for measurement in (actual, prior):
                if measurement is not None and (_payload_measure(measurement) is None
                        or measurement['metric'] != row['metric']
                        or not consistent_record(measurement, panel['slot'])):
                    return False
            if result is not None:
                derived_count += 1
                if actual is None or prior is None or result['refs'] != [actual['ref'], prior['ref']]:
                    return False
            if trend is not None and (result is None or result['value'] is None
                    or result['status'] not in ('COMPARABLE','QUALIFIED') or not matches(trend, (result,))):
                return False
        if panel['headline'] is not None:
            if (any(row['trend'] is None for row in rows)
                    or rows[0]['current']['period'] != rows[1]['current']['period']
                    or rows[0]['prior']['period'] != rows[1]['prior']['period']
                    or not matches(panel['headline'], tuple(row['comparison'] for row in rows))):
                return False
        guide, result = panel['original_guidance'], panel['guidance']
        if (guide is None) != (result is None):
            return False
        if guide is not None:
            derived_count += 1
            source_refs.add(guide['ref'])
            if (panel['slot'] == 'alphabet' or rows[0]['current'] is None
                    or result['refs'] != [rows[0]['current']['ref'], guide['ref']]):
                return False
            native_free_guide = _payload_guidance(guide)
            if (native_free_guide is None or not consistent_record(guide, panel['slot'])
                    or not _same_scope(_payload_measure(rows[0]['current']),
                                       native_free_guide, same_period=True)):
                return False
        outcomes = set()
        for group in panel['accounting']:
            key = tuple(group['outcome_refs'])
            if key in outcomes:
                return False
            outcomes.add(key)
            revisions = set()
            if len(group['explanations']) != len(group['views']):
                return False
            for view, explanation in zip(group['views'], group['explanations']):
                derived_count += 1
                source_refs.update(view['result']['refs'])
                if (group['outcome_refs'] != [view['current_output']['ref'], view['prior_output']['ref']]
                        or view['result']['rule_revision'] in revisions):
                    return False
                if any(_payload_measure(view[key]) is None
                       or not consistent_record(view[key], panel['slot'])
                       for key in ('current_output','prior_output')):
                    return False
                expected_refs = [view['current_output']['ref'], view['prior_output']['ref']]
                for contribution in view['contributions']:
                    expected_refs.extend((contribution['current_ref'], contribution['prior_ref']))
                actual_refs = view['result']['refs']
                # The accounting core admits unique component receipts. An
                # omitted, extra or repeated pointer cannot become support;
                # its list order is not a statement about evidence independence.
                if (len(set(expected_refs)) != len(expected_refs)
                        or len(set(actual_refs)) != len(actual_refs)
                        or set(actual_refs) != set(expected_refs)):
                    return False
                copy = _accounting_copy(panel['slot'], Decimal(view['residual']), view['evidence_relation'],
                        tuple((part['component_key'], Decimal(part['contribution']), Decimal(part['delta'])) for part in view['contributions']))
                if copy is None:
                    if explanation is not None:
                        return False
                elif (explanation is None or (explanation['en'], explanation['zh']) != copy
                        or len(explanation['refs']) != len(set(explanation['refs']))
                        or set(explanation['refs']) != set(actual_refs)
                        or explanation['rule_revisions'] != [view['result']['rule_revision']]
                        or explanation['interpretation_basis'] != (
                            'exact_reported_values' if view['result']['status'] == 'COMPARABLE' else 'published_figures')):
                    return False
                revisions.add(view['result']['rule_revision'])
    return len(source_refs) <= 96 and derived_count <= 32


def validate_view(payload) -> None:
    """Validate closed domain structure/lineage, NOT source, rights or identity.

    An internally consistent false statement is still false. Native admission,
    source verification, copy review and shared release acceptance remain required.
    """
    _encoded_view(payload)
    if not _view_validator().is_valid(payload) or not _view_links_valid(payload['projection']):
        raise ClaimInputError('INVALID_CLAIM_VIEW')


def compose_communications_payload(inputs: tuple[CompanyClaimInput, ...]) -> dict:
    """Unregistered domain portion only; not the shared query/bundle callback.

    'unbound' is an invariant of this constructor, not an inferred rights verdict.
    The incumbent owner must accept the full request/generation/evidence/identity
    mapping before any shared registration. No current paid snapshot is written.
    """
    projection = _plain_projection(compose_four_company_claims(inputs))
    payload = {'schema': 'communications_business_research.v1',
               'binding_state': 'unbound', 'projection': projection}
    validate_view(payload)
    return payload


def encode_communications_payload(inputs: tuple[CompanyClaimInput, ...]) -> bytes:
    """Return bounded UTF-8 JSON; no storage, network or public publication."""
    return _encoded_view(compose_communications_payload(inputs))
