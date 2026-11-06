"""Literal legacy rotation-stamp parity over captured optional inputs."""
from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path

import pytest

from engine.sector_generation_guard import rotation_context_from_inputs
from scripts.build_sector_cycles import _stamp_rotation_context
from tests.fixtures.base_sector_rotation_1f3f605 import _stamp_rotation_context as original


def event(day="2026-11-03", **fields):
    return {"schema": "rotation_events.v1", "ok": True, "as_of": day,
            "active": [{"id": "one", "nested": {"value": 2}}], **fields}


def fragment(day="2026-11-03", **fields):
    return {"as_of": day, "sectors": [{"ticker": "XLK", "state": "aligned"}], **fields}


CASES = [
    (None, None), (event(), fragment()), (event("2026-11-02"), fragment()),
    (event("2026-11-04"), fragment("2026-11-02")),
    (event("2026-11-10"), fragment("2026-11-10")),
    (event(schema="bad"), fragment()), (event(ok=False), fragment()),
    (event(active="invalid"), fragment(sectors="invalid")),
    (event(active=({"id": "tuple"},)), fragment(sectors=())),
    (event(None), fragment(None)), (event("invalid"), fragment("invalid")),
    ([], fragment()), (event(), 3), (event(), {"sectors": []}),
]


@pytest.mark.parametrize("events,fragmentation", CASES)
@pytest.mark.parametrize("consumer", ["2026-11-03", None, "invalid"])
def test_literal_old_adapter_new_adapter_and_value_projection_match(tmp_path, events, fragmentation, consumer):
    (tmp_path / "marketdata").mkdir()
    for name, value in (("rotation_events.json", events), ("sector_fragmentation.json", fragmentation)):
        if value is not None:
            (tmp_path / "marketdata" / name).write_text(json.dumps(value))
    initial = {"meta": {"asOf": consumer}, "sectors": [{"ticker": "XLK"}], "unchanged": {"value": 7}}
    before, after = deepcopy(initial), deepcopy(initial)
    today = date(2026, 11, 6)
    original(before, site_root=tmp_path, today=today)
    _stamp_rotation_context(after, site_root=tmp_path, today=today)
    fields = rotation_context_from_inputs(consumer_session=consumer, rotation_events=events,
        fragmentation=fragmentation, today=today)
    explicit = {**deepcopy(initial), **fields}
    assert explicit == before == after
    assert set(fields) == {"rotation_context", "rotation_alignment_version"}
    assert initial["unchanged"] == {"value": 7}


def test_unreadable_legacy_input_remains_explicit_absence(tmp_path):
    (tmp_path / "marketdata").mkdir()
    (tmp_path / "marketdata/rotation_events.json").write_text("{invalid")
    before = {"meta": {"asOf": "2026-11-03"}}; after = deepcopy(before)
    original(before, site_root=tmp_path, today=date(2026, 11, 6))
    _stamp_rotation_context(after, site_root=tmp_path, today=date(2026, 11, 6))
    fields = rotation_context_from_inputs(consumer_session="2026-11-03", rotation_events=None,
        fragmentation=None, today=date(2026, 11, 6))
    assert before == after == {"meta": {"asOf": "2026-11-03"}, **fields}


def test_projection_does_not_read_files_config_or_mutate_auxiliaries(monkeypatch):
    from lib import config
    events, fragmentation = event(), fragment()
    before = deepcopy((events, fragmentation))
    def forbidden(*a, **k): raise AssertionError("ambient acquisition reached")
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(config, "load", forbidden)
    result = rotation_context_from_inputs(consumer_session="2026-11-03", rotation_events=events,
        fragmentation=fragmentation, today=datetime(2026, 11, 6, tzinfo=timezone.utc))
    assert result["rotation_context"]["events"]["status"] == "aligned"
    result["rotation_context"]["events"]["active"][0]["nested"]["value"] = 99
    result["rotation_context"]["fragmentation"]["sectors"][0]["ticker"] = "changed"
    assert (events, fragmentation) == before


def test_literal_rotation_baseline_is_frozen():
    p = Path(__file__).parent / "fixtures/base_sector_rotation_1f3f605.py"
    assert hashlib.sha256(p.read_bytes()).hexdigest() == "47089af89bf933239a64909be3090e8af1b93604e1d41c77862bdd43a7709794"
