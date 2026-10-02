"""Single canonical producer / three display entries; no forecast authority delta."""
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
import pandas as pd

from lib import cn_calendar, config
from lib.china_pullback_view import present, snapshot

ROOT = Path(__file__).resolve().parents[1]


def observation():
    day = date(2026, 9, 29)
    days = []
    while len(days) < 66:
        if cn_calendar.is_session(day):
            days.append(day)
        day -= timedelta(days=1)
    data = pd.DataFrame({"close": [100.0] * 64 + [97.0, 96.0]},
                        index=pd.to_datetime(list(reversed(days))))
    return snapshot(now=datetime(2026, 9, 29, 10, tzinfo=timezone.utc),
                    read=lambda group, ticker: data)


def test_observation_precedes_existing_canonical_persist_without_second_feed():
    source = (ROOT / "scripts/build_china.py").read_text()
    assert source.count("_cpv.snapshot()") == 1
    assert source.index('["pullback_observation"] = _pb_observation') < source.index('_ms.persist(vm.get("market_state"), market_key="cn")')
    assert source.count('_ms.persist(vm.get("market_state"), market_key="cn")') == 1
    assert 'ctx["pullback_view"] = vm["pullback_view"]' in source
    adapter = (ROOT / "lib/china_pullback_view.py").read_text()
    for mutation in (".to_parquet(", ".write_text(", "stamp_forward(", "append_event("):
        assert mutation not in adapter


def test_existing_market_state_serializes_the_exact_observation(monkeypatch, tmp_path):
    from engine.market_state import persist
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    observed = observation()
    payload = {"asof": "2026-09-29", "score": 37, "color": "red",
               "radar": {"top_score": 98, "dd21": 0.5, "state": "risk-off"},
               "pullback_observation": observed}
    before = json.loads(json.dumps(payload))
    persist(payload, market_key="cn")
    stored = json.loads((tmp_path / "china_market_state" / "latest.json").read_text())
    assert stored == before and payload == before
    assert not (tmp_path / "market_state" / "latest.json").exists()


def test_same_view_is_wired_to_all_three_china_entries():
    page = (ROOT / "templates/china.html.j2").read_text()
    dialog = (ROOT / "templates/_risk_radar_dlg.html.j2").read_text()
    for marker in ("{{ pbo.card(_pbv) }}", "{{ pbo.compact(_pbv) }}",
                   "{{ t(_pbv.headline_en, _pbv.headline_zh) }}", "_pbv.show_card if _pbv else"):
        assert marker in page
    assert "{{ pbo.detail(c.pullback_view) }}" in dialog
    assert "mkt == 'cn' and c.get('pullback_view')" in dialog
    assert 'data-pb-trigger-value' in page
    assert 'include "_pullback_observation.js.j2"' in page
    assert 'include "_pullback_observation.css.j2"' in page


def test_shared_dialog_is_unchanged_for_other_countries():
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
    module = env.get_template("_risk_radar_dlg.html.j2").module
    view = present(observation(), {"state": "calm", "top_score": 0, "dd21": 0.1})
    context = {"pullback_view": view}
    for country in ("hk", "ca"):
        html = str(module.risk_radar_dlg(country, {}, [], context))
        assert 'class="pbx pbx-detail' not in html
        assert "Pullback underway" not in html
    cn = str(module.risk_radar_dlg("cn", {}, [], context))
    assert 'class="pbx pbx-detail' in cn
    assert "Pullback underway" in cn
    assert "The forecast below concerns a future fall" in cn


def test_frontend_reuses_the_existing_clock_and_language_owner():
    js = (ROOT / "templates/_pullback_observation.js.j2").read_text()
    assert "getAttribute('data-pb-valid-until')" in js
    assert "addEventListener('langchange', language)" in js
    assert "addEventListener('visibilitychange'" in js
    for new_plane in ("fetch(", "setInterval(", "new MutationObserver", "localStorage", "indexedDB", "WebSocket"):
        assert new_plane not in js
    assert "root.setAttribute('data-pb-phase', 'unavailable')" in js
    assert "Price update needed" in js and "价格数据待更新" in js


def test_price_history_is_not_claimed_as_issued_warning_history():
    observed = observation()
    assert observed["history_basis"] == "reconstructed_current_source_vintage"
    for key in ("issued_at", "first_known_at", "warning_sent", "recovery_permission"):
        assert key not in observed
    partial = (ROOT / "templates/_pullback_observation.html.j2").read_text()
    assert "Reconstructed from closes" in partial
    assert "not first-known alert history" in partial
    assert "not stock breadth" in partial
