"""Discriminating controls for the deliberately narrow source grammar."""
import pytest

from engine.guidance_source_context import extract_total_revenue_guidance as extract

QUOTE = ('The company is raising 2026 total revenue guidance to $582 million to '
         '$592 million, or 13% to 14% growth, from prior guidance of $570 to '
         '$582 million, or 10% to 13% growth.')


def body(quote=QUOTE):
    return f'<h2>2026 Financial Outlook</h2><div><font>{quote}</font></div>'.encode()


def test_exact_declarative_sentence_is_documentary_not_model_math():
    result = extract(body(), 'raise')
    assert result == {'schema': 'guidance_source_context.v1', 'status': 'QUALIFIED',
        'metric': 'total_revenue', 'direction': 'raise', 'fiscal_year': 2026,
        'quote': QUOTE, 'reason': 'explicit_total_revenue_revision'}


def test_inline_tags_whitespace_and_decimal_intervals():
    quote = QUOTE.replace('total revenue', 'total <b>revenue</b>').replace('$582', '$582.5').replace(' to ', '\n to  ')
    assert extract(body(quote), 'raise')['status'] == 'QUALIFIED'


def test_explicit_lowering_and_optional_prior_unit():
    quote = QUOTE.replace('raising', 'lowering').replace('$582 million to $592', '$550 million to $560')
    quote = quote.replace('$570 to', '$570 million to')
    assert extract(body(quote), 'cut')['direction'] == 'cut'
    assert extract(body(quote), 'raise')['status'] == 'UNQUALIFIED'


@pytest.mark.parametrize('word', ['testing revenue', 'organic revenue', 'net income', 'adjusted EBITDA', 'EPS', 'revenue'])
def test_other_metrics_and_generic_revenue_are_not_total_revenue(word):
    assert extract(body(QUOTE.replace('total revenue', word)), 'raise')['status'] == 'UNQUALIFIED'


@pytest.mark.parametrize('prefix', ['If demand improves, ', 'Example: ', 'It is not true that ', 'Analysts expect that ', 'Suppose ', '"'])
def test_prefix_cannot_be_dropped_to_invent_a_declaration(prefix):
    assert extract(body(prefix + QUOTE), 'raise')['status'] == 'UNQUALIFIED'


@pytest.mark.parametrize('tag', ['script', 'style', 'noscript', 'blockquote', 'q', 'pre', 'code'])
def test_non_assertion_context_is_not_a_filing_assertion(tag):
    assert extract(f'<{tag}>{QUOTE}</{tag}>'.encode(), 'raise')['status'] == 'UNQUALIFIED'


def test_hypothetical_heading_applies_to_following_paragraph():
    assert extract(f'<h2>Illustrative scenario</h2><p>{QUOTE}</p>'.encode(), 'raise')['status'] == 'UNQUALIFIED'


@pytest.mark.parametrize('changed', [QUOTE.replace('$592', '$580'), QUOTE.replace('$582 million', '$569 million'),
    QUOTE.replace('$582 million', '$570 million'), QUOTE.replace('13% to 14%', '14% to 13%'),
    QUOTE.replace('2026', '26'), QUOTE.replace('$582', '$NaN'), QUOTE.replace('$582', '$-582')])
def test_invalid_reversed_or_non_directional_intervals_fail_closed(changed):
    assert extract(body(changed), 'raise')['status'] == 'UNQUALIFIED'


def test_exact_duplicates_deduplicate_but_unequal_claims_refuse():
    assert extract(body() + body(), 'raise')['status'] == 'QUALIFIED'
    assert extract(body() + body(QUOTE.replace('$592', '$595')), 'raise')['reason'] == 'conflicting_revisions'
    assert extract(body() + body(QUOTE.replace('2026', '2027')), 'raise')['status'] == 'UNQUALIFIED'


def test_other_following_metrics_do_not_override_the_revenue_sentence():
    doc = body(QUOTE + ' The company is also raising testing revenue guidance to $570 million to $580 million.')
    assert extract(doc, 'raise')['quote'] == QUOTE


@pytest.mark.parametrize('content,direction', [(None, 'raise'), ('text', 'raise'), (b'', 'raise'),
    (b'\xff', 'raise'), (b'x' * (2 * 1024 * 1024 + 1), 'raise'), (body(), None), (body(), 'maintain')])
def test_invalid_inputs_return_a_bounded_refusal(content, direction):
    assert extract(content, direction)['status'] == 'UNQUALIFIED'
