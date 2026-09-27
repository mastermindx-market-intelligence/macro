import pytest
from render_reference import render_fixture_fragment
from review_projection import project_relationship_review
from test_review_projection import row


def render(locale='en',auth=True,**change):
    v=project_relationship_review([row(**change)],as_of='2026-09-27')
    return render_fixture_fragment(v,entitled_fixture=auth,locale=locale)


@pytest.mark.parametrize('locale',['en','zh'])
def test_entitled_fixture_retains_identity_and_source(locale):
    h=render(locale)
    assert 'FIX-B' in h and 'Example related registrant' in h
    assert 'https://example.invalid/filing' in h


def test_plain_meaning_not_a_trade():
    h=render()
    assert 'Target role not established' in h
    assert 'Do not apply the target' in h
    assert '99' not in h and 'arb' not in h


def test_no_unqualified_affected_claim():
    h=render()
    assert 'economic relationship is confirmed' not in h
    assert 'Needs relationship review' in h


@pytest.mark.parametrize('auth',[False,None,1,'yes'])
def test_nonpositive_entitlement_fixture_withholds_content(auth):
    h=render(auth=auth)
    assert 'FIX-B' not in h and 'Example related' not in h and 'example.invalid' not in h
    assert 'Sign in' in h


def test_source_html_autoescaped():
    h=render(summary='<img src=x onerror=alert(1)>')
    assert '<img' not in h and '&lt;img' in h


def test_unsafe_url_not_rendered_but_identity_retained():
    h=render(source_url='javascript:alert(1)')
    assert 'javascript:' not in h and 'FIX-B' in h and 'Source link unavailable' in h


def test_chinese_copy_is_not_untranslated_state_label():
    h=render(locale='zh')
    assert '标的身份尚未确认' in h and '查看原始披露' in h
    assert 'Needs relationship review' not in h


def test_missing_data_stays_readable():
    h=render(ticker=None, company=None, summary=None)
    assert 'Name unavailable' in h and 'Source summary unavailable' in h


def test_empty_selection_is_explicit():
    v=project_relationship_review([],as_of='2026-09-27')
    assert 'No filings need relationship review in this selection' in render_fixture_fragment(v,entitled_fixture=True)


def test_wrong_locale_refused():
    with pytest.raises(ValueError,match='unsupported_locale'):render(locale='de')


def test_render_sink_rechecks_source_link_with_shared_validator():
    v=project_relationship_review([row()],as_of='2026-09-27')
    v['records'][0]['source_url']='javascript:alert(1)'
    h=render_fixture_fragment(v,entitled_fixture=True)
    assert 'javascript:' not in h and 'Source link unavailable' in h
