"""Fixture-render adapter, NOT an entitlement service or production page renderer.

The same view belongs behind the existing paid-fragment delivery path. This
reference supplies no styles, script, subscription check, route or publication.
"""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from review_projection import _source_url

COPY = {
 'en': dict(title='Needs relationship review',
   intro='A take-private is mentioned. This does not establish that this company is the target.',
   status='Target role not established',
   explanation="Do not apply the target’s deal price or delisting outcome to this company.",
   source_summary='Read the source statement', source_link='Open original disclosure',
   sign_in='Sign in to view the source review.', name_missing='Name unavailable',
   summary_missing='Source summary unavailable', date_missing='Source date unavailable',
   link_missing='Source link unavailable',
   empty='No filings need relationship review in this selection.',
   more='More source records are present in this selection; this view is bounded.'),
 'zh': dict(title='需核实与交易的关系',
   intro='披露提及一项私有化交易，但尚不能据此认定这家公司就是交易标的。',
   status='标的身份尚未确认',
   explanation='请勿将交易标的的收购价格或退市结果套用到这家公司。',
   source_summary='阅读披露原文', source_link='查看原始披露',
   sign_in='登录后查看来源核实内容。',name_missing='公司名称不可用',
   summary_missing='来源摘要不可用',date_missing='披露日期不可用',
   link_missing='来源链接不可用',empty='当前筛选中没有需要核实交易关系的披露。',
   more='当前筛选还有其他来源记录；此视图仅展示部分记录。')
}


def render_fixture_fragment(view, *, entitled_fixture, locale='en'):
    if locale not in COPY:
        raise ValueError('unsupported_locale')
    env=Environment(loader=FileSystemLoader(Path(__file__).parent), autoescape=True)
    return env.get_template('review_fragment.html.j2').render(
        review=view, copy=COPY[locale], entitled=entitled_fixture is True, source_link=_source_url)
