"""The existing China page builder consumes one source-qualified pullback view."""
from datetime import datetime, timezone
from inspect import getsource

from lib import cn_pullback_observation, pullback_observation
from scripts import build_china


NOW = datetime(2026, 10, 9, 9, 30, tzinfo=timezone.utc)


def test_page_builder_uses_the_same_native_snapshot_and_presenter(monkeypatch):
    seen = []
    observation = {"schema": "pullback_observation.v1", "market": "cn",
                   "available": False, "quality": "delayed", "phase": "unavailable"}
    view = {"phase": "unavailable", "observation": observation}

    def capture_snapshot(*, now, read, observer):
        seen.append(("snapshot", now, read, observer))
        return observation

    def capture_present(obs):
        seen.append(("present", obs))
        return view

    monkeypatch.setattr(cn_pullback_observation, "snapshot", capture_snapshot)
    monkeypatch.setattr(cn_pullback_observation, "present", capture_present)
    assert build_china._cn_pullback_risk_popup(now=NOW) is view
    assert seen == [("snapshot", NOW, cn_pullback_observation.licensed_index_closes,
                     pullback_observation.observe),
                    ("present", observation)]


def test_a_failing_source_leaves_the_dialog_unchanged_not_the_build_broken(monkeypatch):
    def boom(**_):
        raise OSError("store unreadable")

    monkeypatch.setattr(cn_pullback_observation, "snapshot", boom)
    assert build_china._cn_pullback_risk_popup(now=NOW) is None


def test_page_builder_binds_the_licensed_reader_and_the_one_episode_owner():
    source = getsource(build_china._cn_pullback_risk_popup)
    body = source.split('"""')[-1]
    assert "read=pb.licensed_index_closes" in body
    assert "from lib.pullback_observation import observe" in body
    assert "observer=observe" in body
    assert "yahoo" not in source.lower()


def test_view_rides_the_dialog_ctx_once_before_the_page_renders():
    source = getsource(build_china.main)
    bind = 'vm["radar_dlg"]["pullback_view"] = _cn_pullback_risk_popup('
    assert source.count(bind) == 1
    assert source.index('vm["radar_dlg"] = _radar_dlg_vm(vm, latest)') < source.index(bind)
    assert source.index(bind) < source.index('env.get_template("china.html.j2")')
