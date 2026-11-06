"""Actual retained annual source through the normal collector/store/mount seam."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from pathlib import Path
import json

import pandas as pd
import pytest

from lib import config
from lib import intl_eurostat_publication as pub
from collectors.intl_macro import IntlMacroAdapter
from collectors.base import run_adapter

FIELD = pub.ANNUAL_FIELD
COLUMN = pub.ANNUAL_FIELDS[FIELD]['column']
RAW = Path(__file__).parent / 'fixtures/intl_workspace/eurostat_tipsbp20_ea21.json'
URL = 'https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/tipsbp20?lang=en&geo=EA21&unit=PC_GDP&freq=A&sinceTimePeriod=2023'
REQUESTED = '2026-11-04T08:13:06.578582+00:00'
RECEIVED = '2026-11-04T08:13:07.981575+00:00'
NOW = '2026-11-04T09:00:00+00:00'


def capture(root):
    raw = RAW.read_bytes()
    assert pub._sha(raw) == '2ac70f929ac25e2bff803a139fb5a477bb585b36508404dafc255a6a7a2afe4e'
    parsed, frame = pub.parse_native_field(FIELD, raw)
    dest = root / 'intl_macro' / (COLUMN + '.parquet')
    dest.parent.mkdir(parents=True, exist_ok=True); frame.to_parquet(dest)
    pub.capture_eurostat_commit(field=FIELD, data_root=root, returned=frame, response_bytes=raw,
        source_url=URL, requested_at=REQUESTED, response_received_at=RECEIVED,
        input_verified_at='2026-11-04T08:18:00+00:00', committed_at='2026-11-04T08:20:00+00:00')
    return pub.read_eurostat_materialization(field=FIELD, data_root=root)


def decision(materialized, **changes):
    result = {'owner_ref': 'scripts/build_intl.py', 'policy_ref': pub.ANNUAL_POLICY,
        'decision_ref': 'im-workspace-generation:df4a2d6b-aed5-4d0c-a211-68f3a4627eb4:' + FIELD,
        'metadata': 'allowed', 'value_permission': 'allowed',
        'binding': {'field': FIELD, 'receipt_sha256': materialized['receipt_sha256']}}
    result.update(changes); return result


def admit(materialized, **changes):
    return pub.admit_eurostat_annual_field(materialized, evaluated_at=NOW,
                                          publication_decision=decision(materialized, **changes))


def test_actual_native_annual_value_and_distinct_clocks_survive_capture_and_projection(tmp_path):
    m = capture(tmp_path); assert m['status'] == 'ready'
    r = admit(m); metric = r['measure']; support = r['support']
    assert metric['value'] == 1.7 and metric['unit'] == 'percent_gdp'
    assert metric['instrument']['kind'] == 'current_account'
    assert metric['instrument']['id'] == 'TIPSBP20/A/PC_GDP/CA/S1/S1/BAL/EXT_EA21/NSA/EA21'
    assert metric['observation_at'] == '2025-12-31' and metric['calculation_at'] is None
    assert metric['period'] == {'start': '2025-01-01', 'end': '2026-01-01', 'count': 1, 'count_basis': 'release_periods'}
    assert support == {'method_ref': pub.ANNUAL_POLICY, 'market_id': 'EZ', 'field_year': 2025,
        'vintage': None, 'observation_type': 'statistical', 'observation_clock_basis': 'period_end',
        'dataset_updated_at': '2026-10-28T23:00:00+0100'}
    assert r['evidence']['response_received_at'] == RECEIVED
    assert pub.project_field_evidence({FIELD: r['evidence']}, {FIELD: metric}) == {FIELD: r['evidence']}
    assert m['receipt']['provider_published_at'] is m['receipt']['revision_vintage'] is None
    assert m['receipt']['schema'] == 'intl.eurostat_annual_materialization.v1'


@pytest.mark.parametrize('metadata', ['denied', 'unknown'])
def test_metadata_withheld_scrubs_source_clocks_and_support(tmp_path, metadata):
    m = capture(tmp_path); result = admit(m, metadata=metadata)
    assert result['support'] is result['evidence'] is None
    assert result['measure']['value'] is result['measure']['source_reference'] is None
    assert '2026-10-28' not in json.dumps(result) and 'https://' not in json.dumps(result)


@pytest.mark.parametrize('permission', ['unknown', 'denied'])
def test_value_permission_never_grants_statistical_interpretation(tmp_path, permission):
    m = capture(tmp_path); r = admit(m, value_permission=permission)
    assert r['measure']['value'] is None and r['support'] is None
    assert r['measure']['quality'] in {'unknown', 'denied'}


def test_missing_policy_does_not_infer_a_grant_from_real_source(tmp_path):
    m = capture(tmp_path)
    r = pub.admit_eurostat_annual_field(m, evaluated_at=NOW, publication_decision=None)
    assert r['measure']['value'] is None and r['support'] is r['evidence'] is None


@pytest.mark.parametrize(('days', 'quality'), [(400, 'qualified'), (401, 'stale')])
def test_year_end_400_day_display_limit_is_not_renewed_by_dataset_update(tmp_path, days, quality):
    m = capture(tmp_path)
    evaluated = datetime(2025, 12, 31, tzinfo=timezone.utc) + timedelta(days=days)
    r = pub.admit_eurostat_annual_field(m, evaluated_at=evaluated.isoformat(), publication_decision=decision(m))
    assert r['measure']['quality'] == quality
    assert r['support']['vintage'] is None


def test_missing_dependent_store_retains_validated_permission_but_no_dynamic_evidence(tmp_path):
    m = capture(tmp_path); (tmp_path / 'intl_macro' / (COLUMN + '.parquet')).unlink()
    failed = pub.read_eurostat_materialization(field=FIELD, data_root=tmp_path)
    assert failed['status'] == 'failed' and failed['receipt_sha256'] == m['receipt_sha256']
    r = admit(failed)
    assert r['measure']['quality'] == 'failed' and r['measure']['reason'] == 'source_failed'
    assert r['measure']['metadata'] == 'allowed' and r['measure']['unit'] == 'percent_gdp'
    assert r['measure']['value'] is r['measure']['observation_at'] is None
    assert r['support'] is r['evidence'] is None


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = datetime.fromisoformat(NOW)
        return value if tz else value.replace(tzinfo=None)


def collector(root, monkeypatch):
    cfg = deepcopy(config.load()); cfg['storage']['data_dir'] = str(root)
    cfg['storage']['run_status_file'] = str(root / 'run_status.json')
    cfg['intl']['countries'] = {}; cfg['intl']['macro']['extra_series'] = {}
    cfg['intl']['macro']['official_series'] = {COLUMN: cfg['intl']['macro']['official_series'][COLUMN]}
    monkeypatch.setattr(config, 'load', lambda: cfg)
    monkeypatch.setattr('collectors.intl_macro.datetime', FixedDateTime)
    monkeypatch.setattr('collectors.base.datetime', FixedDateTime)
    return IntlMacroAdapter(), cfg


def test_actual_retained_input_reaches_normal_collector_successful_store_and_reader(tmp_path, monkeypatch):
    adapter, cfg = collector(tmp_path, monkeypatch)
    (tmp_path / 'source.json').write_bytes(RAW.read_bytes())
    (tmp_path / 'receipt.json').write_text(json.dumps({'status': 200, 'sha256': pub._sha(RAW.read_bytes()),
        'url': URL, 'requested_at': REQUESTED, 'received_at': RECEIVED}))
    cfg['intl']['macro']['official_series'][COLUMN]['native_input'] = {'response': 'source.json', 'receipt': 'receipt.json'}
    monkeypatch.setattr(adapter, 'http_get', lambda *a, **k: pytest.fail('retained source cannot acquire again'))
    result = run_adapter(adapter)
    assert result.status == 'ok' and result.rows == 3
    m = pub.read_eurostat_materialization(field=FIELD, data_root=tmp_path)
    assert m['status'] == 'ready' and m['receipt']['response_received_at'] == RECEIVED
    assert pd.read_parquet(tmp_path / 'intl_macro' / (COLUMN + '.parquet')).iloc[-1, 0] == 1.7
    assert adapter._eurostat_responses == {}


def test_ordinary_http_collector_uses_exact_native_selector_and_not_legacy_collapse(tmp_path, monkeypatch):
    adapter, cfg = collector(tmp_path, monkeypatch); calls = []
    def http(url, **kwargs):
        calls.append((url, kwargs['params']))
        return type('Response', (), {'content': RAW.read_bytes(), 'url': URL, 'status_code': 200})()
    monkeypatch.setattr(adapter, 'http_get', http)
    assert run_adapter(adapter).status == 'ok' and len(calls) == 1
    assert calls[0][1]['partner'] == 'EXT_EA21'
    assert pub.read_eurostat_materialization(field=FIELD, data_root=tmp_path)['status'] == 'ready'


def test_post_store_capture_failure_never_replays_acquisition(tmp_path, monkeypatch):
    adapter, _ = collector(tmp_path, monkeypatch); calls = []
    def http(*args, **kwargs):
        calls.append(1)
        return type('Response', (), {'content': RAW.read_bytes(), 'url': URL, 'status_code': 200})()
    monkeypatch.setattr(adapter, 'http_get', http)
    monkeypatch.setattr(pub, 'capture_eurostat_commit', lambda **k: (_ for _ in ()).throw(ValueError('capture failed')))
    result = run_adapter(adapter)
    assert result.status == 'ok' and len(calls) == 1 and len(result.notes) == 1
    assert pd.read_parquet(tmp_path / 'intl_macro' / (COLUMN + '.parquet')).iloc[-1, 0] == 1.7
    assert adapter._eurostat_responses == {}


@pytest.mark.parametrize(('days', 'status'), [(400, 'ok'), (401, 'stale')])
def test_normal_annual_collector_uses_period_age_without_relabeling_collection_as_observation(tmp_path, monkeypatch, days, status):
    adapter, cfg = collector(tmp_path, monkeypatch)
    instant = datetime(2025, 12, 31, tzinfo=timezone.utc) + timedelta(days=days)
    class AtBoundary(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant if tz else instant.replace(tzinfo=None)
    monkeypatch.setattr('collectors.intl_macro.datetime', AtBoundary)
    monkeypatch.setattr('collectors.base.datetime', AtBoundary)
    (tmp_path / 'source.json').write_bytes(RAW.read_bytes())
    (tmp_path / 'receipt.json').write_text(json.dumps({'status': 200, 'sha256': pub._sha(RAW.read_bytes()),
        'url': URL, 'requested_at': REQUESTED, 'received_at': RECEIVED}))
    cfg['intl']['macro']['official_series'][COLUMN]['native_input'] = {'response': 'source.json', 'receipt': 'receipt.json'}
    monkeypatch.setattr(adapter, 'http_get', lambda *a, **k: pytest.fail('no acquisition for retained cadence check'))
    result = run_adapter(adapter)
    assert result.status == status and not result.notes
    m = pub.read_eurostat_materialization(field=FIELD, data_root=tmp_path)
    assert m['status'] == 'ready'
    assert m['receipt']['observations'][-1]['observation_at'] == '2025-12-31'
    assert m['receipt']['observations'][-1]['value'] == 1.7
    assert m['receipt']['source_updated'] == '2026-10-28T23:00:00+0100'
    assert m['receipt']['response_received_at'] == RECEIVED


def test_annual_health_cadence_does_not_change_monthly_or_quarterly_rules(tmp_path, monkeypatch):
    from collectors.base import detect_stale_series
    adapter, _ = collector(tmp_path, monkeypatch)
    _, annual = pub.parse_native_field(FIELD, RAW.read_bytes())
    assert adapter.fetch_result_status({COLUMN: annual, 'existing_monthly': annual.copy()}) is None
    frozen = detect_stale_series('intl_macro', {COLUMN: annual, 'existing_monthly': annual.copy()},
        cadence_days=45, now=datetime.fromisoformat(NOW), cadence_days_by_series=adapter.cadence_days_by_series)
    assert [x['series'] for x in frozen] == ['existing_monthly']
    assert frozen[0]['cadence_days'] == 45
    with pytest.raises(ValueError, match='per-series cadence'):
        detect_stale_series('intl_macro', {COLUMN: annual}, cadence_days=45, cadence_days_by_series=[])


def _mounted(root, result, *, supply_evidence=True):
    from engine.intl_workspace_overview import build_workspace_overviews
    from engine.intl_inputs import countries
    from lib.intl_risk_mount import attach_risks
    from tests.test_intl_eod_publication import _setup, GENERATION
    frame, _ = _setup(root)
    workspace = build_workspace_overviews(frame, workspace_generation=GENERATION)
    registry = {'markets': [{'market_id': cc, 'name_en': c['name'], 'name_zh': c['name_zh']}
                            for cc, c in countries().items()],
                'horizons': workspace['config']['horizons'], 'bases': workspace['config']['bases']}
    return attach_risks(workspace, registry=registry, risk_desk=None, cgl=None,
        measures={FIELD: result['measure']},
        field_support={FIELD: result['support']} if result['support'] is not None else {},
        summary_eligibility={}, destinations={},
        field_evidence={FIELD: result['evidence']} if supply_evidence and result['evidence'] is not None else None)


def test_statistical_value_requires_separate_bound_clock_evidence_at_mount(tmp_path):
    result = admit(capture(tmp_path))
    mounted = _mounted(tmp_path, result)
    row = next(x for x in mounted['risks'][0]['risk_section']['pressure_rows'] if x['market_id'] == 'EZ')
    assert row['annual_current_account']['value'] == 1.7
    assert mounted['risks'][0]['field_evidence'][FIELD]['requested_at'] == REQUESTED
    withheld = _mounted(tmp_path, result, supply_evidence=False)
    row = next(x for x in withheld['risks'][0]['risk_section']['pressure_rows'] if x['market_id'] == 'EZ')
    assert row['annual_current_account'].get('value') is None


@pytest.mark.parametrize('metadata', ['allowed', 'denied', 'unknown'])
def test_statistical_render_labels_and_source_link_follow_real_typed_metadata(tmp_path, metadata):
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
    from tests.test_intl_workspace_risk_render import collect
    mounted = _mounted(tmp_path, admit(capture(tmp_path), metadata=metadata))
    panel = mounted['risks'][0]
    env = Environment(loader=FileSystemLoader(Path(__file__).resolve().parents[1]),
                      autoescape=False, undefined=StrictUndefined)
    html = env.get_template('templates/intl_workspace/risk.html.j2').render(
        risk_section=panel['risk_section'], registry=mounted['risk_registry'], context_id=panel['context_id'],
        panel_context=panel['context'], generation=panel['generation'],
        field_evidence=panel.get('field_evidence', {}))
    if metadata == 'allowed':
        assert 'data-im-risk-value>+1.7</span>' in html and 'Annual statistic' in html and '年度统计' in html
        assert 'Period ended' in html and '2025-12-31' in html
        assert 'Vintage not supplied' in html and '未提供版本日期' in html
        assert URL in collect(html).hrefs
        assert '2026-10-28T23:00:00+0100' in html and RECEIVED in html
        assert '400 days after year end' in html and 'not a release or freshness promise' in html
        assert '>Actual<' not in html
    else:
        assert URL not in collect(html).hrefs
        assert 'Source: Eurostat' not in html and '来源：欧盟统计局' not in html
        assert '2026-10-28T23:00:00+0100' not in html
        assert 'data-im-risk-value>+1.7</span>' not in html
