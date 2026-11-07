"""The existing publisher mounts History without implying source disclosure."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

from lib.intl_library_mount import render_international_pages
from scripts import build_intl


def _fixture(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_shell = _fixture("history_publication_shell", "test_intl_inspector_mount.py")
_history = _fixture("history_publication_data", "test_intl_history_mount.py")


def publish(root, **kwargs):
    return build_intl._publication_workspace(
        None, data_root=root, evaluated_at="2026-10-09T01:30:00Z", **kwargs)


def test_normal_publication_has_one_history_catalogue_and_no_invented_grants(tmp_path):
    workspace = publish(tmp_path)
    assert len(workspace["histories"]) == 1
    panel = workspace["histories"][0]
    assert panel["generation"] == workspace["config"]["source_reference"]
    assert [s["selected_market"] for s in panel["sections"]] == workspace["config"]["markets"]
    assert len(panel["sections"]) == 7
    assert all(s["source_read_status"] == "unknown" and s["points"] == [] for s in panel["sections"])
    assert len(workspace["panels"]) == len(workspace["macros"]) == len(workspace["risks"]) == 10


def test_explicit_supplied_projection_remains_detached_and_market_bound(tmp_path):
    _, args = _history.fixture()
    sources = args["sources"]
    before = deepcopy(sources)
    workspace = publish(tmp_path, history_sources=sources)
    jp = next(s for s in workspace["histories"][0]["sections"] if s["selected_market"] == "JP")
    assert jp["source_read_status"] == "ready" and jp["points"]
    assert all(s["points"] == [] for s in workspace["histories"][0]["sections"] if s["selected_market"] != "JP")
    jp["points"][0]["growth_score"] = 999
    assert sources == before


def test_history_failure_preserves_other_complete_panels(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("private History error")
    monkeypatch.setattr(build_intl, "attach_history", fail)
    workspace = publish(tmp_path)
    assert "histories" not in workspace
    assert len(workspace["panels"]) == len(workspace["macros"]) == len(workspace["risks"]) == 10


def test_malformed_history_input_does_not_remove_the_workspace(tmp_path):
    workspace = publish(tmp_path, history_sources=[])
    assert "histories" not in workspace
    assert len(workspace["panels"]) == len(workspace["macros"]) == len(workspace["risks"]) == 10


def test_real_shell_keeps_all_owners_and_exposes_blank_disabled_scenario(tmp_path):
    workspace = publish(tmp_path)
    before = deepcopy(workspace)
    catalogue = json.loads((Path(__file__).parents[1] / "config/intl_library_catalogue.json").read_text())
    html, stocks = render_international_pages(
        _shell.ActualShell(), {"intl_workspace": workspace}, catalogue=catalogue)
    nodes = _shell.Document(html).nodes
    assert stocks == "Incumbent stocks" and workspace == before
    assert len([a for _, a in nodes if "data-im-history-panel" in a]) == 1
    assert len([a for _, a in nodes if "data-im-inspector-shell" in a]) == 1
    assert "data-im-library-static" in html and "data-im-compare-panel" in html
    assert html.count('data-view="macro"') == html.count('data-view="risk"') == 10
    history_button = next(a for tag, a in nodes if tag == "button" and a.get("data-im-view") == "history")
    assert "disabled" not in history_button
    inputs = [a for tag, a in nodes if tag == "input" and a.get("name") in {"local", "fx"}]
    assert len(inputs) == 2 and all(a.get("value", "") == "" for a in inputs)
    assert "disabled" in next(a for _, a in nodes if "data-im-scenario-fields" in a)
    ids = [a["id"] for _, a in nodes if "id" in a]
    assert len(ids) == len(set(ids))


def test_receipt_bridge_reuses_exact_receipts_without_new_disclosure(tmp_path, monkeypatch):
    from engine import international_macro_dashboard as owner
    _, args = _history.fixture()
    projected = deepcopy(args['sources']['JP']['history_read'])
    supplied = {'status': 'ready', 'frame': object()}
    seen = []
    def project(value):
        seen.append(value)
        return projected
    monkeypatch.setattr(owner, 'project_history_read', project, raising=False)
    sources = build_intl._history_publication_sources({'JP': supplied})
    assert len(seen) == 1 and seen[0] is supplied
    assert sources['JP']['history_read'] == projected
    for key in ('history_source', 'events', 'track_record'):
        assert sources['JP']['capabilities'][key] == dict(metadata='unknown', value='unknown')
    assert sources['JP']['turn_events'] == [] and sources['JP']['track_record'] is None
    assert sources['JP']['destinations'] == {}
    workspace = publish(tmp_path, history_sources=sources)
    for section in workspace['histories'][0]['sections']:
        assert section['points'] == [] and section['source_read_status'] == 'unknown'


def test_receipt_bridge_contains_one_bad_market_and_rejects_wrong_binding(monkeypatch, caplog):
    from engine import international_macro_dashboard as owner
    _, args = _history.fixture()
    projected = deepcopy(args['sources']['JP']['history_read'])
    bad, good = object(), object()
    def project(value):
        if value is bad:
            raise ValueError('private secret cannot appear in log')
        return deepcopy(projected)
    monkeypatch.setattr(owner, 'project_history_read', project, raising=False)
    sources = build_intl._history_publication_sources({'GB': bad, 'JP': good, 'KR': good})
    assert set(sources) == {'JP'}
    assert 'private secret' not in caplog.text


def test_receipt_bridge_does_not_invoke_projector_for_unknown_market(monkeypatch):
    from engine import international_macro_dashboard as owner
    def forbidden(*args, **kwargs):
        raise AssertionError('unknown market must not reach reader projector')
    monkeypatch.setattr(owner, 'project_history_read', forbidden, raising=False)
    assert build_intl._history_publication_sources({'UNKNOWN': object()}) == {}


def test_receipt_bridge_empty_and_invalid_sink():
    import pytest
    assert build_intl._history_publication_sources({}) == {}
    for invalid in ([], None, {'JP': object(), 7: object()}):
        with pytest.raises(ValueError, match='^invalid_history_receipts$'):
            build_intl._history_publication_sources(invalid)


def _native_history_receipt(tmp_path, monkeypatch):
    import pandas as pd
    from lib import config
    from lib.intl_history_materialization import capture_history_context, describe_history_write
    from engine import international_macro_dashboard as reader
    settings = deepcopy(config.load())
    monkeypatch.setattr(config, 'data_dir', lambda: tmp_path)
    frame = pd.DataFrame({'growth_score': [0.25, -0.125], 'inflation_score': [0.5, 0.75]},
                         index=pd.date_range('2026-01-01', periods=2))
    context = capture_history_context('JP', settings['intl']['countries']['JP'],
        settings['intl']['engine'], frame, source_root=config.ROOT)
    path = tmp_path/'intl_regime/JP_history.parquet'; path.parent.mkdir(); frame.to_parquet(path)
    materialization = describe_history_write('JP', frame, context, path.read_bytes(), '2026-11-05T00:00:00+00:00')
    receipt = reader.load_history_result('JP', materialization=materialization)
    assert receipt['status'] == 'ready'
    return receipt, settings


def test_derived_history_requires_explicit_exact_policy_and_verified_native_binding(tmp_path, monkeypatch):
    from lib import config
    receipt, settings = _native_history_receipt(tmp_path, monkeypatch)
    settings['intl']['history_publication'].update(status='proposed', decision_ref=None)
    monkeypatch.setattr(config, 'load', lambda: settings)
    source = build_intl._history_publication_sources({'JP': receipt})['JP']
    assert source['capabilities']['history_source'] == dict(metadata='unknown', value='unknown')
    policy = settings['intl']['history_publication']
    policy.update(status='confirmed', decision_ref='TEST-ONLY-explicit-derived-output-decision')
    source = build_intl._history_publication_sources({'JP': receipt})['JP']
    assert source['capabilities']['history_source'] == dict(metadata='allowed', value='allowed')
    assert source['capabilities']['events'] == source['capabilities']['track_record'] == dict(metadata='unknown', value='unknown')
    assert source['capabilities']['snapshot_compare'] == dict(left_observation_at=None, right_observation_at=None)
    assert receipt['materialization']['provider_coverage']['status'] == 'unknown'
    assert receipt['materialization']['disclosure_authority'] == 'none'
    result = publish(tmp_path, history_sources={'JP': source})
    jp = next(s for s in result['histories'][0]['sections'] if s['selected_market']=='JP')
    assert jp['snapshot_compare']['selection']['eligible'] is True
    assert jp['snapshot_compare']['reason'] == 'not_requested'


def test_derived_policy_cannot_admit_legacy_or_changed_scope(tmp_path, monkeypatch):
    from lib import config
    receipt, settings = _native_history_receipt(tmp_path, monkeypatch)
    policy = settings['intl']['history_publication']
    policy.update(status='confirmed', decision_ref='TEST-ONLY-explicit-derived-output-decision')
    monkeypatch.setattr(config, 'load', lambda: settings)
    for change in [lambda p:p.update(status='denied'), lambda p:p.update(decision_ref=None),
                   lambda p:p.update(audience='entitled-only'), lambda p:p['fields'].append('raw_series'),
                   lambda p:p.update(extra='not-scoped')]:
        candidate = deepcopy(policy); change(candidate)
        assert build_intl._history_disclosure_allowed(receipt,'JP',candidate) is False
    legacy = {k:v for k,v in receipt.items() if k!='materialization'}
    assert build_intl._history_disclosure_allowed(legacy,'JP',policy) is False
    original_timeout = settings['intl']['macro']['official_series']['ez_depo_rate']['timeout_s']
    settings['intl']['macro']['official_series']['ez_depo_rate']['timeout_s'] = original_timeout + 1
    assert build_intl._history_disclosure_allowed(receipt,'JP',policy) is False
    settings['intl']['macro']['official_series']['ez_depo_rate']['timeout_s'] = original_timeout
    assert build_intl._history_disclosure_allowed(receipt,'JP',policy) is True
    settings['intl']['countries']['JP']['index'] = 'different-universe'
    assert build_intl._history_disclosure_allowed(receipt,'JP',policy) is False


def test_native_seven_market_receipts_reuse_five_reads_without_new_pages(tmp_path, monkeypatch):
    """The five country routes are not the seven-market History universe."""
    import pandas as pd
    from collections import Counter
    from types import SimpleNamespace
    from lib import config
    from lib.intl_history_materialization import capture_history_context, describe_history_write
    from engine import international_macro_dashboard as reader
    from scripts import build_international_macro as builder
    settings = deepcopy(config.load())
    settings['storage']['site_dir'] = str(tmp_path/'site')
    monkeypatch.setattr(config, 'load', lambda: settings)
    monkeypatch.setattr(config, 'data_dir', lambda: tmp_path)
    frame = pd.DataFrame({'growth_score':[0.25,-0.125], 'inflation_score':[0.5,0.75]},
                         index=pd.date_range('2026-01-01',periods=2))
    records=[]
    for cc, country in settings['intl']['countries'].items():
        context = capture_history_context(cc,country,settings['intl']['engine'],frame,source_root=config.ROOT)
        path=tmp_path/f'intl_regime/{cc}_history.parquet';path.parent.mkdir(exist_ok=True);frame.to_parquet(path)
        descriptor=describe_history_write(cc,frame,context,path.read_bytes(),'2026-11-05T00:00:00+00:00')
        records.append(dict(cc=cc,history_materialization=descriptor))
    calls=[]
    def read(cc, **kwargs):
        calls.append(cc);return reader.load_history_result(cc,**kwargs)
    monkeypatch.setattr(builder,'load_history_result',read)
    monkeypatch.setattr(builder,'load_history',lambda *a:pytest.fail('duplicate compatibility read'))
    monkeypatch.setattr(builder,'build_country_view',lambda record,history:dict(decision=dict(score=1)))
    monkeypatch.setattr(builder,'validate_view',lambda *a:None)
    monkeypatch.setattr(builder,'Environment',lambda **k:SimpleNamespace(get_template=lambda n:SimpleNamespace(render=lambda **k:'fixture')))
    monkeypatch.setattr(builder,'write_page',lambda *a:None)
    monkeypatch.setattr(builder,'ASSETS',())
    monkeypatch.setattr('engine.europe_news_intel.panel',lambda *a:None)
    sink={};outputs=builder.build_all(dict(records=records),history_receipts=sink)
    assert len(outputs)==5 and {p.name for p in outputs}=={s.route for s in reader.REGIONS.values()}
    assert Counter(calls)==Counter({cc:1 for cc in settings['intl']['countries']})
    sources=build_intl._history_publication_sources(sink)
    assert set(sources)==set(settings['intl']['countries'])
    assert all(s['capabilities']['history_source']==dict(metadata='allowed',value='allowed') for s in sources.values())
    workspace=publish(tmp_path,history_sources=sources)
    assert len(workspace['histories'][0]['sections'])==7
    assert all(s['snapshot_compare']['selection']['eligible'] for s in workspace['histories'][0]['sections'])
    # Data loss is represented by the actual read, rather than an absent adapter row.
    (tmp_path/'intl_regime/TW_history.parquet').unlink()
    altered=frame.copy();altered.loc[altered.index[0],'growth_score']=999.0
    altered.to_parquet(tmp_path/'intl_regime/AU_history.parquet')
    calls.clear();sink={};builder.build_all(dict(records=records),history_receipts=sink)
    assert Counter(calls)==Counter({cc:1 for cc in settings['intl']['countries']})
    assert sink['TW']['status']=='missing' and sink['AU']['status']=='invalid'
    sources=build_intl._history_publication_sources(sink)
    assert sources['TW']['history_read']['status']=='missing'
    assert sources['AU']['history_read']['status']=='invalid'
    assert sources['TW']['capabilities']['history_source']==dict(metadata='unknown',value='unknown')
    assert sources['AU']['capabilities']['history_source']==dict(metadata='unknown',value='unknown')
