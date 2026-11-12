"""Dated HK IPO evidence through the real store, engine, VM and bilingual section."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from jinja2 import Environment

from engine import ipo_hk
from lib import config
from scripts import build_ipo

ROOT = Path(__file__).resolve().parents[1]
KEYS = ("southbound", "hibor", "peg", "risk")
DATES = pd.bdate_range(end="2026-11-11", periods=30)
PATHS = {
    "southbound": ("china_connect", "southbound", "net"),
    "hibor": ("hkma", "interbank_liquidity", "hibor_1m"),
}


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    for key, value in (("southbound", 1.0), ("hibor", 2.0)):
        _write_series(tmp_path, key, pd.Series(value, index=DATES))
    _write_regime(tmp_path, {"date": "2026-11-10", "peg_state": "strong", "risk_state": "risk-off"})
    return tmp_path


def _write_series(root, key, values):
    group, name, column = PATHS[key]
    path = root / group / (name + ".parquet")
    path.parent.mkdir(parents=True, exist_ok=True)
    values.to_frame(column).to_parquet(path)


def _write_regime(root, value):
    path = root / "hk_regime/latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def _hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def _render(view):
    source = (ROOT / "templates/ipo.html.j2").read_text()
    start = source.index("    <!-- hong kong -->")
    end = source.index("    <!-- methodology", start)
    macro = source[source.index("{% macro t("):]
    macro = macro[:macro.index("{%- endmacro %}") + len("{%- endmacro %}")]
    return Environment(autoescape=True).from_string(macro + source[start:end]).render(
        hk=view, STATEW={})


def _observe(root):
    before = _hashes(root)
    raw = ipo_hk.hk_backdrop()
    view = build_ipo._hk_vm()
    html = _render(view)
    assert _hashes(root) == before
    json.dumps(raw, allow_nan=False)
    json.dumps(view, allow_nan=False)
    return raw, view, html


def _legacy(raw):
    return {key: value for key, value in raw.items() if key not in ("coverage", "as_of")}


def _legs(raw):
    return {leg["key"]: leg for leg in raw["legs"]}


def test_real_parquet_dates_and_coverage_reach_both_languages(inputs):
    raw, view, html = _observe(inputs)
    assert list(_legs(raw)) == list(KEYS)
    assert _legs(raw)["southbound"]["value"] == 20
    assert _legs(raw)["hibor"]["value"] == 2.0
    assert raw["as_of"] == "2026-11-10"
    assert raw["verdict"] == "receptive"
    assert raw["coverage"]["southbound"]["observation_dates"] == [
        day.date().isoformat() for day in DATES[-20:]]
    assert raw["coverage"]["hibor"]["observation_dates"] == ["2026-11-11"]
    assert "Input coverage: 4 of 4." in html and "数据覆盖：4项中有4项。" in html
    assert "20 observations" in html and "20个观测值" in html
    assert "Observation: 2026-11-11" in html and "观测日期：2026-11-11" in html
    assert "Regime snapshot date: 2026-11-10" in html and "市场状态快照日期：2026-11-10" in html
    assert ipo_hk.SCORED is False


@pytest.mark.parametrize("days", [-365, 365])
@pytest.mark.parametrize("target", ["series", "regime"])
def test_date_only_shift_changes_evidence_not_values_or_votes(inputs, days, target):
    before, before_vm, before_html = _observe(inputs)
    if target == "series":
        for key, value in (("southbound", 1.0), ("hibor", 2.0)):
            _write_series(inputs, key, pd.Series(value, index=DATES + pd.Timedelta(days=days)))
        stamp = (DATES[-1] + pd.Timedelta(days=days)).date().isoformat()
    else:
        stamp = (pd.Timestamp("2026-11-10") + pd.Timedelta(days=days)).date().isoformat()
        _write_regime(inputs, {"date": stamp, "peg_state": "strong", "risk_state": "risk-off"})
    after, after_vm, after_html = _observe(inputs)
    assert _legacy(after) == _legacy(before)
    assert after["coverage"] != before["coverage"]
    assert after_vm != before_vm and after_html != before_html
    assert stamp in after_html
    # These shifted dates are evidence controls, not an exchange-holiday calendar.
    assert after["n_legs"] == 4 and after["low_confidence"] is False


def test_trailing_missing_hibor_discloses_selected_and_source_dates(inputs):
    before, _, before_html = _observe(inputs)
    values = pd.Series(2.0, index=DATES)
    values.iloc[-5:] = np.nan
    _write_series(inputs, "hibor", values)
    raw, _, html = _observe(inputs)
    assert _legacy(raw) == _legacy(before)
    evidence = raw["coverage"]["hibor"]
    assert evidence["observation_dates"] == [DATES[-6].date().isoformat()]
    assert evidence["source_date"] == "2026-11-11" and evidence["trailing_missing"] == 5
    assert html != before_html
    assert "5 trailing rows have no reading" in html and "末尾5行没有读数" in html
    assert "source rows through 2026-11-11" in html and "源数据行截至2026-11-11" in html


@pytest.mark.parametrize("key", ["southbound", "hibor"])
@pytest.mark.parametrize("bad", [float("inf"), float("-inf"), "not-a-number", "nan"])
def test_active_bad_parquet_operand_excludes_only_its_leg(inputs, key, bad):
    values = pd.Series("1.0" if key == "southbound" else "2.0", index=DATES, dtype="str") \
        if isinstance(bad, str) else pd.Series(1.0 if key == "southbound" else 2.0, index=DATES)
    values.iat[-1] = bad
    _write_series(inputs, key, values)
    raw, view, html = _observe(inputs)
    assert raw["missing_legs"] == [key] and raw["n_legs"] == 3
    assert set(_legs(raw)) == set(KEYS) - {key}
    assert view["available"] is True
    assert raw["coverage"][key]["status"] == "invalid_value"
    assert "invalid or non-finite reading; input excluded" in html
    assert "读数无效或不是有限数值；本读数未纳入" in html
    assert "not-a-number" not in html


@pytest.mark.parametrize("key", ["southbound", "hibor"])
def test_old_bad_value_outside_selected_window_does_not_erase_current_leg(inputs, key):
    values = pd.Series("1.0" if key == "southbound" else "2.0", index=DATES, dtype="str")
    values.iloc[0] = "old-malformed-reading"
    _write_series(inputs, key, values)
    raw, _, _ = _observe(inputs)
    assert raw["n_legs"] == 4 and raw["missing_legs"] == []
    assert _legs(raw)[key]["value"] == (20 if key == "southbound" else 2.0)


@pytest.mark.parametrize("key", ["southbound", "hibor"])
@pytest.mark.parametrize("bad", [True, np.bool_(True), 1 + 2j, [], {}, " ", np.array([1.0]), np.array(1.0)])
def test_non_reading_scalar_types_are_contained_without_backfill(inputs, monkeypatch, key, bad):
    real_read = ipo_hk.store.read
    group, name, column = PATHS[key]
    values = pd.Series([1.0 if key == "southbound" else 2.0] * len(DATES),
                       index=DATES, dtype=object)
    values.iat[-1] = bad
    frame = values.to_frame(column)
    monkeypatch.setattr(ipo_hk.store, "read", lambda g, n:
                        frame.copy(deep=True) if (g, n) == (group, name) else real_read(g, n))
    raw, _, _ = _observe(inputs)
    assert raw["missing_legs"] == [key] and raw["n_legs"] == 3


def test_finite_operands_with_overflowing_sum_do_not_erase_other_legs(inputs):
    _write_series(inputs, "southbound", pd.Series(1e308, index=DATES))
    raw, view, _ = _observe(inputs)
    assert raw["missing_legs"] == ["southbound"]
    assert raw["coverage"]["southbound"]["status"] == "invalid_value"
    assert set(_legs(raw)) == {"hibor", "peg", "risk"} and view["available"] is True


def test_real_zero_stays_available_and_keeps_existing_states(inputs):
    for key in PATHS:
        _write_series(inputs, key, pd.Series(0.0, index=DATES))
    raw, _, html = _observe(inputs)
    assert raw["missing_legs"] == []
    assert _legs(raw)["southbound"]["value"] == 0
    assert _legs(raw)["southbound"]["state"] == "neutral"
    assert _legs(raw)["hibor"]["value"] == 0.0
    assert _legs(raw)["hibor"]["state"] == "constructive"
    assert "+0 HK$mn" in html and "0.00%" in html


@pytest.mark.parametrize("value,state", [(2.49, "constructive"), (2.5, "neutral"),
                                         (3.99, "neutral"), (4.0, "cautious"),
                                         (-1.0, "constructive")])
def test_hibor_thresholds_and_negative_value_policy_are_unchanged(inputs, value, state):
    _write_series(inputs, "hibor", pd.Series(value, index=DATES))
    raw, _, _ = _observe(inputs)
    assert _legs(raw)["hibor"]["value"] == value
    assert _legs(raw)["hibor"]["state"] == state


@pytest.mark.parametrize("count", [19, 20])
def test_original_twenty_observation_floor_is_preserved(inputs, count):
    _write_series(inputs, "southbound", pd.Series(1.0, index=DATES[-count:]))
    raw, _, html = _observe(inputs)
    assert ("southbound" in _legs(raw)) == (count == 20)
    assert raw["coverage"]["southbound"]["observations"] == count
    if count == 19:
        assert "requires 20 observations; input excluded" in html
        assert "需要20个观测值；本读数未纳入" in html


def test_internal_missing_row_retains_original_nonmissing_window(inputs):
    values = pd.Series(1.0, index=DATES[-21:])
    values.iloc[-10] = np.nan
    _write_series(inputs, "southbound", values)
    raw, _, html = _observe(inputs)
    assert _legs(raw)["southbound"]["value"] == 20
    assert raw["coverage"]["southbound"]["observation_dates"][0] == DATES[-21].date().isoformat()
    assert "20 observations" in html


@pytest.mark.parametrize("field,key", [("peg_state", "peg"), ("risk_state", "risk")])
@pytest.mark.parametrize("bad", [999, [], {}, True, None, "", " "])
def test_invalid_regime_field_is_independent(inputs, field, key, bad):
    regime = {"date": "2026-11-10", "peg_state": "strong", "risk_state": "risk-off"}
    regime[field] = bad
    _write_regime(inputs, regime)
    raw, view, _ = _observe(inputs)
    assert raw["missing_legs"] == [key] and raw["n_legs"] == 3
    assert view["available"] is True


@pytest.mark.parametrize("value", [[], 42, "bad-shape", True, None])
def test_non_dictionary_regime_preserves_both_numeric_legs(inputs, value):
    _write_regime(inputs, value)
    raw, _, html = _observe(inputs)
    assert raw["missing_legs"] == ["peg", "risk"] and raw["n_legs"] == 2
    assert raw["low_confidence"] is True
    assert "Input coverage: 2 of 4. Limited coverage." in html
    assert "数据覆盖：4项中有2项。 数据覆盖有限。" in html


def test_unparseable_regime_json_preserves_both_numeric_legs(inputs):
    (inputs / "hk_regime/latest.json").write_text("{")
    raw, _, _ = _observe(inputs)
    assert set(_legs(raw)) == {"southbound", "hibor"}


@pytest.mark.parametrize("value", [None, [], {}, True, 999, "not-a-date", "now", "today", "2026", "2026-11", "2026-W46-3"])
def test_missing_regime_date_is_disclosed_without_changing_votes(inputs, value):
    _write_regime(inputs, {"date": value, "peg_state": "strong", "risk_state": "risk-off"})
    raw, _, html = _observe(inputs)
    assert raw["n_legs"] == 4 and raw["verdict"] == "receptive"
    assert raw["as_of"] is None
    assert "Regime snapshot date unavailable" in html and "市场状态快照日期缺失" in html
    assert "not-a-date" not in html


@pytest.mark.parametrize("key", ["southbound", "hibor"])
def test_actual_store_malformed_date_failure_is_scoped_to_its_leg(inputs, key):
    _write_series(inputs, key, pd.Series(["1.0"] * 30, index=["not-a-date"] * 30))
    raw, _, _ = _observe(inputs)
    assert raw["missing_legs"] == [key] and raw["n_legs"] == 3


def test_duplicate_observation_dates_are_disclosed_not_deduplicated(inputs):
    dates = DATES[-20:].tolist()
    dates[-2] = dates[-1]
    _write_series(inputs, "southbound", pd.Series(1.0, index=dates))
    raw, _, html = _observe(inputs)
    assert _legs(raw)["southbound"]["value"] == 20
    assert raw["coverage"]["southbound"]["observations"] == 20
    assert raw["coverage"]["southbound"]["dates_in_order"] is False
    assert "stored dates are duplicated or out of order" in html
    assert "所存日期有重复或未按时间排序" in html


@pytest.mark.parametrize("kind", ["nat", "text", "numeric", "reverse"])
def test_direct_reader_date_evidence_is_not_replaced_or_reordered(inputs, monkeypatch, kind):
    # The actual store normalises/sorts its index before returning it. This seam
    # qualifies the engine's own disclosure, not recovery of lost original provenance.
    dates = DATES[-20:].tolist()
    if kind == "nat":
        dates[0] = pd.NaT
    elif kind == "text":
        dates[0] = "bad-date"
    elif kind == "numeric":
        dates = list(range(20))
    else:
        dates.reverse()
    frame = pd.DataFrame({"net": [1.0] * 20}, index=pd.Index(dates))
    real_read = ipo_hk.store.read
    monkeypatch.setattr(ipo_hk.store, "read", lambda g, n:
                        frame.copy(deep=True) if g == "china_connect" else real_read(g, n))
    raw, _, html = _observe(inputs)
    assert _legs(raw)["southbound"]["value"] == 20
    coverage = raw["coverage"]["southbound"]
    assert coverage["observations"] == 20 and coverage["dates_in_order"] is False
    if kind == "reverse":
        assert coverage["observation_dates"][0] == DATES[-1].date().isoformat()
        assert "stored dates are duplicated or out of order" in html
    else:
        assert coverage["dated_observations"] == (0 if kind == "numeric" else 19)
        assert "dates available for" in html and "个有日期" in html


def test_regime_display_keeps_template_escaping(inputs):
    _write_regime(inputs, {"date": "2026-11-10", "peg_state": "<script>bad</script>",
                           "risk_state": "risk-off"})
    raw, _, html = _observe(inputs)
    assert raw["n_legs"] == 4  # no new enum whitelist or changed text classification
    assert "<script>bad</script>" not in html
    assert "&lt;script&gt;bad&lt;/script&gt;" in html


@pytest.mark.parametrize("key", ["southbound", "hibor"])
def test_actual_parquet_list_cells_are_not_numeric_readings(inputs, key):
    _write_series(inputs, key, pd.Series([[1.0]] * len(DATES), index=DATES))
    raw, view, _ = _observe(inputs)
    assert raw["missing_legs"] == [key] and raw["n_legs"] == 3
    assert view["available"] is True


@pytest.mark.parametrize("stamp", ["2026-11-10", "2026-11-10T08:15:00+08:00"])
def test_explicit_regime_calendar_date_is_retained(inputs, stamp):
    _write_regime(inputs, {"date": stamp, "peg_state": "strong", "risk_state": "risk-off"})
    raw, _, html = _observe(inputs)
    assert raw["n_legs"] == 4 and raw["as_of"] == "2026-11-10"
    assert raw["coverage"]["peg"]["snapshot_date"] == "2026-11-10"
    assert "Regime snapshot date: 2026-11-10" in html
    assert "市场状态快照日期：2026-11-10" in html
