"""The existing Macro/US page builder consumes one source-qualified pullback view."""
from datetime import datetime, timezone
from inspect import getsource

from lib import us_pullback_observation
from scripts import build_site


NOW = datetime(2026, 10, 9, 22, tzinfo=timezone.utc)


def test_page_builder_uses_the_same_native_snapshot_and_presenter(monkeypatch):
    seen = []
    observation = {"schema": "pullback_observation.v1", "market": "us",
                   "available": False, "quality": "delayed", "phase": "unavailable"}
    view = {"phase": "unavailable", "observation": observation}
    def capture_snapshot(*, now):
        seen.append(("snapshot", now))
        return observation
    def capture_present(obs):
        seen.append(("present", obs))
        return view
    monkeypatch.setattr(us_pullback_observation, "snapshot", capture_snapshot)
    monkeypatch.setattr(us_pullback_observation, "present", capture_present)
    assert build_site._us_pullback_risk_popup(now=NOW) is view
    assert seen == [("snapshot", NOW), ("present", observation)]


def test_page_builder_binds_the_one_view_to_both_existing_page_render_calls():
    source = getsource(build_site.main)
    assert 'vm["us_pullback_view"] = _us_pullback_risk_popup(' in source
    assert source.count('vm["us_pullback_view"] = _us_pullback_risk_popup(') == 1
    assert source.index('vm["us_pullback_view"] = _us_pullback_risk_popup(') < source.index('env.get_template("dashboard.html.j2").render(**vm, mode="macro")')
