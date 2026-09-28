from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from scripts.build_commodities import (
    _build_sector_vm_inner,
    _wti_physical_evidence_vm as _build_physical_vm,
)

_REPO = Path(__file__).resolve().parents[1]


def _wti_physical_evidence_vm(supply, analysis_asof, **kwargs):
    kwargs.setdefault("now", "2026-09-27T20:00:00Z")
    return _build_physical_vm(supply, analysis_asof, **kwargs)


def _supply(**overrides):
    row = {
        "crude_stocks_mb": 420.5,
        "crude_chg_4w_mb": -5.2,
        "crude_z": -0.74,
        "balance_z": -0.61,
        "balance_word": "tight",
        "cushing_mb": 23.4,
        "cushing_z": -0.42,
        "observed_at": "2026-09-25",
        "published_at": None,
        "received_at": None,
        "source_id": "eia_wpsr",
        "source_name": "U.S. Energy Information Administration",
        "source_url": "https://www.eia.gov/petroleum/supply/weekly/",
        "method_version": "eia_wpsr_seasonal_anomaly_v1",
        "caveat_en": "Physical balance ≠ price direction.",
        "caveat_zh": "实物供需≠价格方向。",
    }
    row.update(overrides)
    return row


def test_wti_physical_contract_separates_three_clocks_and_stays_partial_without_receipt_clocks():
    vm = _wti_physical_evidence_vm(_supply(), analysis_asof="2026-09-25")

    assert vm["state"] == "PARTIAL_EVIDENCE"
    assert vm["available"] is True
    assert vm["quote_clock"]["kind"] == "RUNTIME_INDEPENDENT"
    assert vm["analysis_clock"]["asof"] == "2026-09-25"
    assert vm["physical_clock"]["observed_at"] == "2026-09-25"
    assert vm["physical_clock"]["published_at"] is None
    assert vm["physical_clock"]["received_at"] is None
    assert vm["method_version"] == "eia_wpsr_seasonal_anomaly_v1"
    assert vm["source_id"] == "eia_wpsr"
    assert vm["rights_decision"] == "DEC:EIA-SPR-RIGHTS"
    assert vm["directional_authority"] is False


def test_wti_physical_contract_marks_stale_last_known_without_zero_substitution():
    vm = _wti_physical_evidence_vm(
        _supply(observed_at="2026-09-01"),
        analysis_asof="2026-09-25",
    )

    assert vm["state"] == "STALE_LAST_KNOWN"
    assert vm["values"]["crude_stocks_mb"] == 420.5
    assert vm["values"]["crude_chg_4w_mb"] == -5.2
    assert vm["physical_clock"]["observed_at"] == "2026-09-01"


def test_wti_physical_contract_missing_is_typed_absence_not_zero():
    vm = _wti_physical_evidence_vm(None, analysis_asof="2026-09-25")

    assert vm["state"] == "NOT_CONNECTED"
    assert vm["available"] is False
    assert vm["values"] == {}
    assert vm["physical_clock"]["observed_at"] is None
    assert "crude_stocks_mb" not in vm["values"]


def test_wti_physical_contract_can_become_qualified_only_with_all_receipt_clocks():
    vm = _wti_physical_evidence_vm(
        _supply(
            published_at="2026-09-25T14:30:00Z",
            received_at="2026-09-25T14:31:12Z",
        ),
        analysis_asof="2026-09-25",
    )

    assert vm["state"] == "QUALIFIED"
    assert vm["physical_clock"]["published_at"] == "2026-09-25T14:30:00Z"
    assert vm["physical_clock"]["received_at"] == "2026-09-25T14:31:12Z"


def test_sector_detail_carries_core_oil_physical_evidence_from_incumbent_asset_vm():
    idx = {
        "breadth": {
            "n_members": 1,
            "n_up_trend": 1,
            "n_bull_momentum": 0,
            "n_low_risk": 1,
            "trend_diversity": 0.0,
        },
        "index": {"benchmarks": {}, "mtf": {}, "velocity": {}},
    }
    conf = {
        "members": [{
            "name": "oil",
            "state": "Neutral",
            "bottom_score": 0,
            "top_score": 0,
            "bottom_fired": [],
            "top_fired": [],
        }]
    }
    dates = pd.date_range("2026-07-01", periods=70, freq="D")
    oil_df = pd.DataFrame(
        {
            "close": range(70, 140),
            "momentum_state": ["neutral"] * 70,
            "shock_state": ["normal"] * 70,
            "ts_trend": ["up"] * 70,
        },
        index=dates,
    )
    physical = _wti_physical_evidence_vm(_supply(), analysis_asof=dates[-1])
    assets = [{
        "key": "oil",
        "mtf_rows": [],
        "verdict": {},
        "conviction": None,
        "dollar_usd_dir": None,
        "dollar_effect": None,
        "physical_evidence": physical,
    }]

    vm = _build_sector_vm_inner(
        idx,
        conf,
        {},
        {"oil": oil_df},
        assets,
        {},
    )
    oil = next(row for row in vm["detail"] if row["name"] == "oil")

    assert oil["physical_evidence"] == physical


def _render_partial(physical: dict) -> str:
    env = Environment(loader=FileSystemLoader(str(_REPO / "templates")), autoescape=True)
    env.globals["t"] = lambda en, zh="": en
    return env.get_template("_commodity_oil_physical.html.j2").render(
        d={"name": "oil", "physical_evidence": physical},
    )


def test_oil_physical_partial_renders_source_receipt_and_non_directional_boundary():
    html = _render_partial(_wti_physical_evidence_vm(_supply(), analysis_asof="2026-09-25"))

    assert "Physical confirmation" in html
    assert "U.S. Energy Information Administration" in html
    assert "PARTIAL_EVIDENCE" in html
    assert "2026-09-25" in html
    assert "Publication time not captured" in html
    assert "Received time not captured" in html
    assert "Physical balance" in html
    assert "price direction" in html
    assert "DEC:EIA-SPR-RIGHTS" in html
    assert "420.5" in html
    assert "-5.2" in html
    assert "not a buy signal" in html.lower()


def test_oil_physical_partial_missing_state_never_renders_fake_zero():
    html = _render_partial(_wti_physical_evidence_vm(None, analysis_asof="2026-09-25"))

    assert "NOT_CONNECTED" in html
    assert "Physical evidence is not connected for this build" in html
    assert "0.0" not in html
    assert "420.5" not in html


def test_main_template_includes_oil_physical_partial_only_for_oil_detail():
    src = (_REPO / "templates" / "commodities.html.j2").read_text()
    needle = '{% include "_commodity_oil_physical.html.j2" %}'

    assert needle in src
    include_at = src.index(needle)
    guard_at = src.rfind("{% if d.name == 'oil' %}", 0, include_at)
    endif_at = src.find("{% endif %}", include_at)
    assert guard_at != -1
    assert endif_at != -1


# Review regressions: each fails if invalid/missing evidence can be promoted,
# or if the user-facing timestamp does not belong to the displayed value.
import pytest


@pytest.mark.parametrize('field,value', [
    ('observed_at', 'not-a-date'), ('published_at', 'not-a-date'),
    ('received_at', 'not-a-date'), ('published_at', '2026-09-25'),
    ('received_at', 123),
])
def test_invalid_clocks_do_not_qualify_or_crash(field, value):
    supply = _supply(published_at='2026-09-25T14:30:00Z',
                     received_at='2026-09-25T14:31:12Z')
    supply[field] = value
    result = _wti_physical_evidence_vm(supply, '2026-09-25')
    assert result['state'] == 'PARTIAL_EVIDENCE'
    assert result['physical_clock'][field] is None


def test_future_observation_is_not_current_qualified_evidence():
    result = _wti_physical_evidence_vm(
        _supply(observed_at='2099-01-01', published_at='2099-01-03T14:30:00Z',
                received_at='2099-01-03T14:31:12Z'), '2026-09-25')
    assert result['state'] == 'PARTIAL_EVIDENCE'
    assert 'future_observation' in result['limitations']


def test_received_before_publication_is_not_a_valid_receipt():
    result = _wti_physical_evidence_vm(
        _supply(published_at='2026-09-25T14:30:00Z',
                received_at='2026-09-25T13:30:00Z'), '2026-09-25')
    assert result['state'] == 'PARTIAL_EVIDENCE'
    assert 'receipt_before_publication' in result['limitations']


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf'), True, 'nan'])
def test_nonfinite_or_non_numeric_measurements_are_not_renderable(value):
    result = _wti_physical_evidence_vm(_supply(crude_stocks_mb=value), '2026-09-25')
    assert 'crude_stocks_mb' not in result['values']
    assert result['available'] is False
    assert result['state'] != 'QUALIFIED'
    assert 'nan million' not in _render_partial(result)
    assert 'inf million' not in _render_partial(result)


def test_zero_is_preserved_when_it_is_an_actual_measurement():
    result = _wti_physical_evidence_vm(_supply(crude_chg_4w_mb=0.0), '2026-09-25')
    assert result['values']['crude_chg_4w_mb'] == 0.0


def test_unrecognized_method_does_not_gain_qualification_from_present_clocks():
    result = _wti_physical_evidence_vm(
        _supply(method_version='unknown_formula', published_at='2026-09-25T14:30:00Z',
                received_at='2026-09-25T14:31:12Z'), '2026-09-25')
    assert result['state'] == 'METHOD_NOT_VERIFIED'


def test_old_analysis_cannot_make_an_old_physical_source_fresh():
    result = _wti_physical_evidence_vm(
        _supply(published_at='2026-09-25T14:30:00Z', received_at='2026-09-25T14:31:12Z'),
        '2026-09-25', now='2026-10-20T12:00:00Z')
    assert result['state'] == 'STALE_LAST_KNOWN'
    assert result['analysis_clock']['asof'] == '2026-09-25'


def test_eia_observation_date_belongs_to_last_finite_crude_value(monkeypatch):
    from scripts.build_commodities import _oil_supply_read
    from lib import store
    data = pd.DataFrame({'crude_stocks': [420500.0, float('nan')]},
                        index=pd.to_datetime(['2026-09-18', '2026-09-25']))
    monkeypatch.setattr(store, 'read', lambda group, name: data if name == 'crude_stocks' else None)
    result = _oil_supply_read()
    assert result['crude_stocks_mb'] == 420.5
    assert result['observed_at'] == '2026-09-18'


def test_partial_does_not_inject_language_spans_into_attributes():
    from bs4 import BeautifulSoup
    env = Environment(loader=FileSystemLoader(str(_REPO / 'templates')), autoescape=True)
    template = env.from_string('''{% macro t(en, zh) -%}<span class="l-en">{{ en }}</span><span class="l-zh">{{ zh }}</span>{%- endmacro %}{% include "_commodity_oil_physical.html.j2" %}''')
    html = template.render(d={'name': 'oil', 'physical_evidence': _wti_physical_evidence_vm(_supply(), '2026-09-25')})
    doc = BeautifulSoup(html, 'html.parser')
    for element in doc.find_all(True):
        assert all('<span' not in str(value) for value in element.attrs.values())
    assert '实物供需≠价格方向' in doc.get_text()
    assert doc.select_one('.oil-phys-receipt a[href="https://www.eia.gov/petroleum/supply/weekly/"]')


def test_balance_word_is_translated_in_chinese_partial():
    env = Environment(loader=FileSystemLoader(str(_REPO / 'templates')), autoescape=True)
    env.globals['t'] = lambda en, zh='': zh
    html = env.get_template('_commodity_oil_physical.html.j2').render(
        d={'name': 'oil', 'physical_evidence': _wti_physical_evidence_vm(_supply(), '2026-09-25')})
    assert '偏紧' in html
    assert '>tight<' not in html


def test_future_evidence_is_withheld_not_shown_as_limited_context():
    result = _wti_physical_evidence_vm(_supply(observed_at='2099-01-01'), '2026-09-25')
    assert result['available'] is False
    assert result['values'] == {}


def test_another_source_cannot_inherit_eia_attribution_or_rights():
    result = _wti_physical_evidence_vm(_supply(source_id='different_vendor'), '2026-09-25')
    assert result['available'] is False
    assert result['values'] == {}
    assert 'source_identity_mismatch' in result['limitations']


def test_corrupt_crude_store_does_not_break_other_commodity_views(monkeypatch):
    from scripts.build_commodities import _oil_supply_read
    from lib import store
    def broken(group, name):
        raise OSError('fixture unreadable store')
    monkeypatch.setattr(store, 'read', broken)
    result = _wti_physical_evidence_vm(_oil_supply_read(), '2026-09-25')
    assert result['state'] == 'FETCH_ERROR'
    assert result['available'] is False
    assert 'source could not be read' in _render_partial(result)


def test_inventory_composite_is_withheld_for_different_observation_weeks(monkeypatch):
    from scripts.build_commodities import _oil_supply_read
    from lib import store
    frames = {
        'crude_stocks': pd.DataFrame({'x': [420500.0]}, index=pd.to_datetime(['2026-09-25'])),
        'cushing_stocks': pd.DataFrame({'x': [23400.0]}, index=pd.to_datetime(['2026-09-18'])),
    }
    monkeypatch.setattr(store, 'read', lambda group, name: frames.get(name))
    raw = _oil_supply_read()
    result = _wti_physical_evidence_vm(raw, '2026-09-25')
    assert raw['unaligned_inventory_periods'] is True
    assert 'balance_z' not in result['values']
    assert result['values']['balance_word'] == 'n/a'
    assert 'unaligned_inventory_periods' in result['limitations']


def test_vm_does_not_mutate_source_dictionary():
    import copy
    source = _supply()
    before = copy.deepcopy(source)
    _wti_physical_evidence_vm(source, '2026-09-25')
    assert source == before
