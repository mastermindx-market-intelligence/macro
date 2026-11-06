"""Source-bound F07 evidence: real archive contract, no network or live writes."""
import json

import pandas as pd
import pytest

from collectors.sec_document_spine import persist_archive_document
from collectors.guidance_source_context import enrich_guidance_hits
from engine.guidance_source_evidence import (
    CONTENT_COLUMN, RECEIPT_COLUMN, qualify_hit, source_document, with_source_context,
)

QUOTE = ('The company is raising 2026 total revenue guidance to $582 million to '
         '$592 million, or 13% to 14% growth, from prior guidance of $570 to '
         '$582 million, or 10% to 13% growth.')
CONTENT = ('<h2>2026 Financial Outlook</h2><p>' + QUOTE + '</p>').encode()
STAMP = '2026-10-20T00:49:47.595755Z'
CUTOFF = '2026-10-20T01:00:00Z'


def source_hit():
    return {'ticker': 'VCYT', 'cik': '0001384101', 'form': '8-K',
            'id': '0001384101-26-000029:vcyt-05x05x20268xkearnings.htm',
            'file_date': '2026-05-05', 'direction': 'raise', 'phrase': 'raising guidance'}


@pytest.fixture
def archived(tmp_path):
    hit = source_hit()
    receipt = persist_archive_document(tmp_path, source_document(hit), CONTENT, retrieved_at=STAMP)
    hit[RECEIPT_COLUMN] = json.dumps(receipt.to_dict())
    return hit, tmp_path


def test_exact_native_receipt_and_bytes_support_source_context(archived):
    hit, root = archived
    out = with_source_context(hit, as_of=CUTOFF, root=root)
    assert out['phrase'] == 'raising guidance'  # preserve the discovery hint
    q = out['source_context']
    assert q['quote'] == QUOTE and q['direction'] == 'raise'
    assert q['ticker'] == 'VCYT' and q['retrieved_at'] == STAMP
    assert q['source_url'].endswith('vcyt-05x05x20268xkearnings.htm')
    assert 'source_context' not in hit  # no input mutation


@pytest.mark.parametrize('cutoff', [None, '2026-10-19', '2026-10-20',
                                  '2026-10-20T00:49:47.595754Z', '2026-10-20T01:00:00'])
def test_unavailable_before_true_retrieval_or_without_aware_cutoff(archived, cutoff):
    hit, _ = archived
    assert qualify_hit(hit, CONTENT, as_of=cutoff) is None


def test_same_instant_offset_and_exact_boundary_are_allowed(archived):
    hit, _ = archived
    assert qualify_hit(hit, CONTENT, as_of=STAMP)
    assert qualify_hit(hit, CONTENT, as_of='2026-10-19T17:49:47.595755-07:00')


@pytest.mark.parametrize('field,value', [('ticker', 'AAPL'), ('cik', '0001755672'),
    ('id', '0001384101-26-000030:vcyt-05x05x20268xkearnings.htm'),
    ('id', '0001384101-26-000029:../../other.htm'), ('form', '10-K'),
    ('file_date', '2026-10-21'), ('direction', 'cut')])
def test_receipt_cannot_cross_filing_or_direction(archived, field, value):
    hit, _ = archived
    hit[field] = value
    assert qualify_hit(hit, CONTENT, as_of=CUTOFF) is None


def test_tampered_bytes_and_receipt_are_refused(archived):
    hit, _ = archived
    assert qualify_hit(hit, CONTENT + b' ', as_of=CUTOFF) is None
    r = json.loads(hit[RECEIPT_COLUMN]); r['retrieved_at'] = '2026-05-05T20:00:00Z'
    hit[RECEIPT_COLUMN] = json.dumps(r)
    assert qualify_hit(hit, CONTENT, as_of=CUTOFF) is None


def test_missing_or_corrupt_archive_does_not_trust_forwarded_context(archived):
    hit, root = archived
    hit['source_context'] = {'status': 'QUALIFIED', 'quote': QUOTE}
    r = json.loads(hit[RECEIPT_COLUMN]); (root / r['storage_key']).write_bytes(b'bad')
    assert 'source_context' not in with_source_context(hit, as_of=CUTOFF, root=root)


class Client:
    def __init__(self, root):
        self.cache_root = root
        self.calls = []
    def fetch_document(self, document):
        self.calls.append(document)
        return persist_archive_document(self.cache_root, document, CONTENT, retrieved_at=STAMP)


def test_enrichment_preserves_other_issuers_and_reuses_original_receipt(tmp_path):
    client = Client(tmp_path)
    own = source_hit(); duplicate = {**own, 'phrase': 'raises guidance'}
    other = {**own, 'ticker': 'CTVA'}
    rows = pd.DataFrame([own, duplicate, other])
    result = enrich_guidance_hits(rows, collector=client)
    assert len(client.calls) == 1 and len(result) == 3
    assert pd.isna(result.iloc[2][RECEIPT_COLUMN])
    assert result.iloc[0][RECEIPT_COLUMN] == result.iloc[1][RECEIPT_COLUMN]
    assert result.drop(columns=[RECEIPT_COLUMN, CONTENT_COLUMN]).to_dict('records') == rows.to_dict('records')
    again = enrich_guidance_hits(result, collector=client)
    assert len(client.calls) == 1 and again.equals(result)


def test_corrupt_receipt_is_not_refetched_or_backdated(archived):
    hit, root = archived
    hit[RECEIPT_COLUMN] = '{}'
    client = Client(root)
    result = enrich_guidance_hits(pd.DataFrame([hit]), collector=client)
    assert client.calls == [] and result.iloc[0][RECEIPT_COLUMN] == '{}'


def test_collector_request_budget(tmp_path):
    client = Client(tmp_path)
    hits = [{**source_hit(), 'id': f'0001384101-26-{n:06d}:source.htm'} for n in range(8)]
    result = enrich_guidance_hits(pd.DataFrame(hits), collector=client)
    assert len(client.calls) == 4
    assert result[RECEIPT_COLUMN].notna().sum() == 4


def test_qualified_source_drives_existing_shadow_only(archived, monkeypatch):
    from engine import valuation_assumptions as assumptions
    from engine.valuation_scenario import compute
    from engine import valuation_event_proposal as proposals
    hit, root = archived
    qualified = with_source_context(hit, as_of=CUTOFF, root=root)
    # Existing native SEC FY2025 reported fields; no forecast numbers enter it.
    rows = [{'fy': 2025, 'period_end': '2025-12-31', 'ni': 66353000,
             'revenue': 517145000, 'shares': 79359005}]
    monkeypatch.setattr(assumptions, 'latest_issuer_event_record', lambda ticker: (None, True))
    monkeypatch.setattr(assumptions, 'issuer_guidance_hits', lambda ticker, **kwargs: [qualified])
    controls = assumptions.controls_blob(compute(rows, ticker='VCYT'), as_of=CUTOFF)
    proposal = controls['event_assumption_proposal']
    shadow = controls['event_assumption_scenario']
    assert proposal['status'] == 'PROPOSED'
    assert proposal['magnitude_source'] == 'model_preset'
    assert proposal['proposed_value'] == 7  # published model preset, not 13/14% forecast
    assert controls['server_default']['per_share'] == 15.5
    assert shadow['baseline']['per_share'] == 15.5 and shadow['proposed']['per_share'] == 16.1
    assert shadow['changed_assumptions'] == ['sales_growth_pct'] and shadow['applied'] is False
    assert proposal['event']['source_refs'][0]['retrieved_at'] == STAMP
    assert proposal['event']['source_refs'][0]['quote'] == QUOTE


def test_real_source_excerpt_and_its_clock_render_as_dated_evidence(archived, monkeypatch):
    from jinja2 import Environment, FileSystemLoader
    from engine import valuation_assumptions as assumptions
    from engine.valuation_scenario import compute
    from pathlib import Path
    hit, root = archived
    qualified = with_source_context(hit, as_of=CUTOFF, root=root)
    monkeypatch.setattr(assumptions, 'latest_issuer_event_record', lambda ticker: (None, True))
    monkeypatch.setattr(assumptions, 'issuer_guidance_hits', lambda ticker, **kwargs: [qualified])
    controls = assumptions.controls_blob(compute([{'fy': 2025, 'period_end': '2025-12-31',
        'ni': 66353000, 'revenue': 517145000, 'shares': 79359005}], ticker='VCYT'), as_of=CUTOFF)
    env = Environment(loader=FileSystemLoader(str(Path(__file__).resolve().parents[1] / 'templates')), autoescape=True)
    text = env.from_string("{% macro t(en, zh='') %}{{ en }} {{ zh }}{% endmacro %}{% include '_valuation_assumptions.html.j2' %}").render(valuation_assumptions=controls)
    assert QUOTE in text and '2026-05-05' in text and '2026-10-20' in text
    assert 'not a new announcement' in text and '并非新的公告' in text
    assert 'A recent filing' not in text
    assert '$15.5' in text and '$16.1' in text


def test_published_parquet_keeps_exact_bytes_across_separate_hosts(tmp_path):
    client = Client(tmp_path / 'producer-archive')
    out = enrich_guidance_hits(pd.DataFrame([source_hit()]), collector=client)
    path = tmp_path / 'guidance_hits.parquet'
    out.to_parquet(path, index=False)
    consumer_hit = pd.read_parquet(path).iloc[0].to_dict()
    assert consumer_hit[CONTENT_COLUMN] == CONTENT
    hydrated = with_source_context(consumer_hit, as_of=CUTOFF, root=tmp_path / 'absent-consumer-archive')
    assert hydrated['source_context']['quote'] == QUOTE
    assert CONTENT_COLUMN not in hydrated
    # A corrupt embedded body cannot borrow a valid producer archive instead.
    consumer_hit[CONTENT_COLUMN] += b'changed'
    assert 'source_context' not in with_source_context(consumer_hit, as_of=CUTOFF, root=client.cache_root)
