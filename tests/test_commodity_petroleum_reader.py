import pandas as pd
import pytest

from scripts.build_commodities import _petroleum_flow_read
from lib import store


NAMES = ("crude_production", "refinery_inputs", "gasoline_supplied", "distillate_supplied")


def frames():
    return {name: pd.DataFrame({name: [value]}, index=pd.to_datetime(["2026-10-02"]))
            for name, value in zip(NAMES, [13979, 16480, 8769, 3650])}


def test_reader_needs_only_existing_four_flow_series_not_inventory(monkeypatch):
    data = frames()
    calls = []

    def read(group, name):
        calls.append((group, name))
        assert group == "eia" and name in NAMES
        return data[name]

    monkeypatch.setattr(store, "read", read)
    result = _petroleum_flow_read("2026-10-20")
    assert calls == [("eia", name) for name in NAMES]
    assert result["state"] == "stale"
    assert result["common_period"] == "2026-10-02"
    assert result["values"]["refinery_inputs"] == 16480
    assert result["age_days"] == 18


@pytest.mark.parametrize("kind", ["absent", "empty", "wrong_column", "read_error"])
def test_source_failure_does_not_invent_value_or_break_the_page(monkeypatch, kind):
    data = frames()

    def read(group, name):
        if name != "refinery_inputs":
            return data[name]
        if kind == "read_error":
            raise OSError("controlled missing file")
        return {"absent": None, "empty": pd.DataFrame(),
                "wrong_column": data[name].rename(columns={name: "unrelated"})}[kind]

    monkeypatch.setattr(store, "read", read)
    result = _petroleum_flow_read("2026-10-20")
    assert result["state"] == "unavailable"
    assert result["common_period"] is None
    assert not result["values"]


def test_reader_does_not_mix_individually_latest_weeks(monkeypatch):
    data = frames()
    data["crude_production"].loc[pd.Timestamp("2026-10-09")] = [14000]
    monkeypatch.setattr(store, "read", lambda group, name: data[name])
    result = _petroleum_flow_read("2026-10-20")
    assert result["common_period"] == "2026-10-02"
    assert result["values"]["crude_production"] == 13979


def test_numeric_index_cannot_become_an_invented_epoch_week(monkeypatch):
    data = frames()
    data["crude_production"] = data["crude_production"].reset_index(drop=True)
    monkeypatch.setattr(store, "read", lambda group, name: data[name])
    result = _petroleum_flow_read("2026-10-20")
    assert result["state"] == "unavailable"
    assert result["common_period"] is None and result["values"] == {}


def test_timezone_aware_series_and_asof_use_same_utc_date(monkeypatch):
    data = frames()
    for frame in data.values():
        frame.index = frame.index.tz_localize("UTC")
    monkeypatch.setattr(store, "read", lambda group, name: data[name])
    result = _petroleum_flow_read("2026-10-20T02:00:00Z")
    assert result["state"] == "stale" and result["age_days"] == 18
    assert result["values"]["refinery_inputs"] == 16480


@pytest.mark.parametrize("value", ["now", "today", "10/20/2026"])
def test_asof_cannot_consult_an_ambient_clock_or_guess_a_date(monkeypatch, value):
    data = frames()
    monkeypatch.setattr(store, "read", lambda group, name: data[name])
    with pytest.raises(ValueError):
        _petroleum_flow_read(value)
