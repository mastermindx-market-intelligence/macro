"""Synthetic F11 input boundaries; no committed corpus or remote IO."""
import json

import pytest

from engine import thesis_condition_monitor as monitor


@pytest.fixture
def isolated_inputs(monkeypatch, tmp_path):
    monkeypatch.setattr(monitor.config, "ROOT", tmp_path)
    monkeypatch.setattr(monitor.ft, "_FALSIFIERS_JSON", "falsifiers.json")
    monkeypatch.setattr(monitor.ft, "_STATE_JSON", "state.json")

    def forbidden(*args, **kwargs):
        pytest.fail("Malformed local inputs must stop before remote thesis/outbox IO")

    for name in ("read_active_theses", "read_current_versions", "read_existing_fire_ids", "enqueue"):
        monkeypatch.setattr(monitor, name, forbidden)
    return tmp_path


@pytest.mark.parametrize("value", [
    None, True, 17, "bad", {"falsifiers": None}, {"falsifiers": {}},
    {"falsifiers": "bad"}, [None], [17], ["bad"], [{"id": "valid"}, None],
    {"falsifiers": [{"id": "valid"}, []]},
])
def test_invalid_registry_shape_stops_before_remote_io(isolated_inputs, value):
    (isolated_inputs / "falsifiers.json").write_text(json.dumps(value))
    result = monitor.run(dry_run=False, now_utc="2026-01-01T00:00:00Z")
    assert result.outcome == "unavailable"
    assert result.read_state == monitor.READ_UNAVAILABLE
    assert result.error_class == "corrupt_falsifiers_json"
    assert result.enqueued_n == result.evaluated_n == 0


@pytest.mark.parametrize("value", [None, True, 17, "bad", [], [{"state": "FIRED"}]])
def test_invalid_latch_shape_stops_before_remote_io(isolated_inputs, value):
    (isolated_inputs / "falsifiers.json").write_text('[{"id":"synthetic"}]')
    (isolated_inputs / "state.json").write_text(json.dumps(value))
    result = monitor.run(dry_run=False, now_utc="2026-01-01T00:00:00Z")
    assert result.outcome == "unavailable"
    assert result.read_state == monitor.READ_UNAVAILABLE
    assert result.error_class == "corrupt_tripwire_state_json"
    assert result.enqueued_n == result.evaluated_n == 0


@pytest.mark.parametrize("wrapped", [False, True])
def test_valid_shapes_preserve_exact_fired_window(isolated_inputs, wrapped):
    entries = [{"id": "synthetic", "version": 2, "cycle": "test-cycle", "claim": "test"}]
    state = {"synthetic": {"state": "FIRED", "latched": True, "version": 2, "fired_on": "2026-01-01"}}
    (isolated_inputs / "falsifiers.json").write_text(json.dumps({"falsifiers": entries} if wrapped else entries))
    (isolated_inputs / "state.json").write_text(json.dumps(state))
    actual_entries, actual_state, error = monitor.load_tripwire_view()
    assert (actual_entries, actual_state, error) == (entries, state, None)
    windows = monitor.fired_windows(actual_entries, actual_state)
    assert len(windows) == 1
    assert windows[0]["id"] == "synthetic"
    assert windows[0]["fired_on"] == "2026-01-01"


@pytest.mark.parametrize("value", [[], {}, {"falsifiers": []}])
def test_valid_empty_registry_is_preserved(isolated_inputs, value):
    (isolated_inputs / "falsifiers.json").write_text(json.dumps(value))
    (isolated_inputs / "state.json").write_text('{}')
    assert monitor.load_tripwire_view() == ([], {}, None)


def test_missing_files_remain_empty(isolated_inputs):
    assert monitor.load_tripwire_view() == ([], {}, None)
