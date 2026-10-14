"""The existing China page builder consumes one source-qualified pullback view."""
from datetime import datetime, timezone
from inspect import getsource

import pytest

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


@pytest.mark.parametrize("error", [RuntimeError, ImportError, AttributeError, AssertionError])
def test_any_adapter_error_leaves_the_existing_popup_not_a_broken_build(monkeypatch, caplog, error):
    """An additive section must never take the page down: not only source errors,
    but an adapter bug or a missing symbol too. Only the error's type is logged."""
    def boom(**_):
        raise error("adapter-detail-not-logged")

    monkeypatch.setattr(cn_pullback_observation, "snapshot", boom)
    with caplog.at_level("WARNING"):
        assert build_china._cn_pullback_risk_popup(now=NOW) is None
    assert "CN pullback presentation unavailable: " + error.__name__ in caplog.text
    assert "adapter-detail-not-logged" not in caplog.text


def test_an_unimportable_episode_owner_leaves_the_existing_popup(monkeypatch):
    monkeypatch.delattr(pullback_observation, "observe")
    assert build_china._cn_pullback_risk_popup(now=NOW) is None
