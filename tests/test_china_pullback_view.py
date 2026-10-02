"""Raw-source, canonical JSON and illustration contracts; no network or ledgers."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import json
import re

from jinja2 import Environment, FileSystemLoader, StrictUndefined
import pandas as pd
import pytest

from lib import cn_calendar
from lib.china_pullback_view import present, snapshot

NOW = datetime(2026, 9, 29, 10, tzinfo=timezone.utc)


def frame(tail=(95.0,), end=date(2026, 9, 29)):
    values = [100.0] * 64 + list(tail)
    days = []
    while len(days) < len(values):
        if cn_calendar.is_session(end):
            days.append(end)
        end -= timedelta(days=1)
    return pd.DataFrame({"close": values}, index=pd.to_datetime(list(reversed(days))))


def reader(data=None):
    data = data if data is not None else frame()
    calls = []
    def read(group, ticker):
        calls.append((group, ticker))
        return data.copy(deep=True)
    return read, calls


def test_raw_stores_are_read_once_without_any_ledger_write():
    read, calls = reader()
    observed = snapshot(now=NOW, read=read)
    assert len(calls) == 3 and len(set(calls)) == 3
    assert all(group == "china" for group, _ in calls)
    assert observed["benchmark"] == "000001.SS" and observed["phase"] == "underway"
    assert observed["clock"] == "settled_close"
    assert observed["asof"] == "2026-09-29"
    assert observed["produced_at"] == NOW.isoformat()
    assert observed["valid_until"] == "2026-09-30T09:00:00+00:00"
    assert observed["index_confirmation"] == {
        "declining": 3, "available": 3, "total": 3,
        "basis": "recent_63_close_high_and_20_close_average"}
    assert observed["indices"][1]["proxy"] is True
    assert "ETF proxy" in observed["indices"][1]["label_en"]
    json.dumps(observed, allow_nan=False)
    assert "chart_html" not in observed
    assert "policy" not in observed and "new_entry_permission" not in observed


def test_current_primary_survives_missing_secondary_with_honest_coverage():
    data = frame()
    observed = snapshot(now=NOW, read=lambda group, ticker: data if ticker == "000001.SS" else None)
    assert observed["available"] is True
    assert observed["index_confirmation"]["available"] == 1
    assert observed["index_confirmation"]["declining"] == 1
    assert observed["index_confirmation"]["total"] == 3
    assert observed["indices"][1]["declining"] is None
    assert observed["indices"][1]["drawdown_pct"] is None


def test_missing_primary_is_not_substituted_with_the_worst_secondary():
    data = frame()
    observed = snapshot(now=NOW, read=lambda group, ticker: None if ticker == "000001.SS" else data)
    view = present(observed, {"state": "calm", "top_score": 1, "dd21": 0.1})
    assert observed["available"] is False and observed["active"] is None
    assert view["show_card"] is True and view["phase"] == "unavailable"
    assert view["value"] == "—" and view["chart_html"] == ""
    assert "unavailable" in view["headline_en"].lower()


def test_reader_failure_does_not_erase_the_parent_snapshot():
    def broken(group, ticker):
        raise OSError("fixture source unavailable")
    observed = snapshot(now=NOW, read=broken)
    assert observed["quality"] == "source_unavailable"
    assert observed["index_confirmation"]["available"] == 0
    assert present(observed)["phase"] == "unavailable"
    json.dumps(observed, allow_nan=False)


def test_unsettled_day_does_not_advance_price_phase():
    data = frame((100.0, 95.0))
    observed = snapshot(now=NOW.replace(hour=8), read=lambda group, ticker: data)
    assert observed["expected_session"] == "2026-09-28"
    assert observed["asof"] == "2026-09-28"
    assert observed["phase"] == "monitoring" and observed["excluded_future_rows"] == 1
    assert observed["valid_until"] == "2026-09-29T09:00:00+00:00"


def test_intraday_store_row_is_rejected_not_normalized():
    data = frame()
    labels = list(data.index)
    labels[-1] += pd.Timedelta(hours=14)
    data.index = labels
    observed = snapshot(now=NOW, read=lambda group, ticker: data)
    assert observed["quality"] == "invalid_session_label"
    assert observed["available"] is False


def test_holiday_expiry_uses_the_existing_exchange_calendar():
    data = frame(end=date(2026, 9, 30))
    observed = snapshot(now=NOW.replace(day=30), read=lambda group, ticker: data)
    assert observed["valid_until"] == "2026-10-08T09:00:00+00:00"
    with pytest.raises(ValueError, match="aware"):
        snapshot(now=NOW.replace(tzinfo=None), read=lambda group, ticker: data)


def test_delayed_source_is_not_refreshed_by_a_new_build_clock():
    data = frame(end=date(2026, 9, 28))
    observed = snapshot(now=NOW, read=lambda group, ticker: data)
    view = present(observed)
    assert observed["asof"] == "2026-09-28" and observed["quality"] == "delayed"
    assert observed["produced_at"] == NOW.isoformat()
    assert view["value"] == "—" and view["headline_en"] == "Settled prices delayed"
    assert "underway" not in view["headline_en"].lower()


def test_quiet_forecast_cannot_hide_a_realized_decline():
    read, _ = reader()
    observed = snapshot(now=NOW, read=read)
    radar = {"top_score": 0, "dd21": 0.0, "state": "calm"}
    original = deepcopy((observed, radar))
    view = present(observed, radar)
    assert view["headline_en"] == "Pullback underway" and view["show_card"] is True
    assert view["score"] == 0 and view["probability"] == 0
    assert view["value"] == "-5.0%"
    assert (observed, radar) == original


def test_high_forecast_is_not_an_observed_event():
    read, _ = reader(frame((100.0,) * 5))
    observed = snapshot(now=NOW, read=read)
    view = present(observed, {"top_score": 98, "state": "risk-off", "dd21": 0.5})
    assert view["headline_en"] == "Pullback risk"
    assert view["phase"] == "monitoring" and view["value"] == "0.0%"
    assert view["score"] == 98 and view["probability"] == 0.5
    assert present(observed, {"state": "calm"})["show_card"] is False


def test_signal_ink_fragments_have_distinct_ids_and_no_fake_forecast():
    read, _ = reader()
    view = present(snapshot(now=NOW, read=read))
    ids = re.findall(r'\bid="([^"]+)"', view["chart_html"] + view["detail_chart_html"])
    assert ids and len(ids) == len(set(ids))
    assert "ilx-drawdown" in view["chart_html"]
    assert "<svg" in view["detail_chart_html"]
    assert "projection" not in view["chart_html"]


def test_full_component_renders_strictly_with_current_and_unavailable_data():
    env = Environment(loader=FileSystemLoader("templates"), undefined=StrictUndefined,
                      autoescape=True)
    component = env.get_template("_pullback_observation.html.j2").module
    for data in (frame(), None):
        observed = snapshot(now=NOW, read=lambda group, ticker: data)
        view = present(observed, {"top_score": 98, "dd21": 0.5, "state": "risk-off"})
        html = str(component.card(view)) + str(component.compact(view)) + str(component.detail(view))
        assert "data-pb-valid-until" in html
        assert "l-en" in html and "l-zh" in html
        assert "Price repair is not a new-entry signal" in html
        assert "Risk intensity" in html
        ids = re.findall(r'\bid="([^"]+)"', html)
        assert len(ids) == len(set(ids))
        if not observed["available"]:
            assert 'class="pbx-ruler"' not in html
            assert 'class="pbx-index-strip"' not in html


@pytest.mark.parametrize("value", [None, True, "98", float("nan"), float("inf"), -1, 101])
def test_invalid_forecast_score_is_not_fabricated(value):
    read, _ = reader()
    view = present(snapshot(now=NOW, read=read), {"top_score": value})
    assert view["score"] is None
