"""Regime-outlook COMPOSER slice E1c1 — evidence rows, clocks and state families.

Three things only: ``read_inputs`` parses owner bytes, ``evidence_rows``
builds the 30 rows in mapping order, ``state_families`` and
``clock_range`` roll them up. Path conditions, baselines, and changes are
NOT in this slice and the tests do not read them.
"""

from __future__ import annotations

import copy
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from engine import rates_command_outlook as rco  # noqa: E402
from engine import rates_command_outlook_compose as rcc  # noqa: E402

GOLDEN_PATH = REPO / "tests" / "fixtures" / "regime_outlook" / "readings_golden_v1.json"
GOLDEN = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
MAPPING = rco.load_mapping()

CUTOFF = datetime(2026, 10, 3, 2, 0, tzinfo=timezone.utc)
US_SESSION = date(2026, 10, 2)

ROW_KEYS = {
    "id",
    "family_id",
    "evidence_family_id",
    "kind",
    "values",
    "unit",
    "window",
    "scope",
    "owner_verdict",
    "status",
    "issues",
    "notes",
    "currentness_certified",
    "source",
}
SOURCE_KEYS = {
    "artifact",
    "pointer",
    "sha256",
    "clock_semantics",
    "as_of",
    "precision",
    "age_calendar_days",
    "future_dated",
    "known_at",
    "available_at",
    "expected_us_session",
    "session_relation",
    "reference_period",
}


def _bytes_for(letter: str) -> bytes:
    return json.dumps(GOLDEN["base"][letter]).encode()


def _base_bytes() -> dict[str, bytes | None]:
    return {letter: _bytes_for(letter) for letter in sorted(MAPPING["artifacts"])}


def _build_at_pin() -> tuple[list[dict], dict]:
    docs, record = rcc.read_inputs(MAPPING, _base_bytes())
    rows = rcc.evidence_rows(
        MAPPING, docs, record, analysis_cutoff=CUTOFF, us_session=US_SESSION
    )
    return rows, record


# ---------------------------------------------------------------------------
# T1 inputs
# ---------------------------------------------------------------------------


def test_inputs_at_the_pin_are_all_available_with_sha256():
    docs, record = rcc.read_inputs(MAPPING, _base_bytes())
    assert set(docs) == set(MAPPING["artifacts"])
    for letter, path in MAPPING["artifacts"].items():
        rec = record[letter]
        assert rec["path"] == path
        assert rec["read_status"] == "available"
        assert isinstance(rec["sha256"], str) and len(rec["sha256"]) == 64


def test_inputs_a_none_letter_is_missing_with_none_sha():
    bytes_in = _base_bytes()
    bytes_in["T"] = None
    docs, record = rcc.read_inputs(MAPPING, bytes_in)
    assert record["T"]["read_status"] == "missing"
    assert record["T"]["sha256"] is None
    assert "T" not in docs


def test_inputs_malformed_bytes_report_malformed():
    bytes_in = _base_bytes()
    bytes_in["T"] = b"[1]"
    docs, record = rcc.read_inputs(MAPPING, bytes_in)
    assert record["T"]["read_status"] == "malformed"
    assert isinstance(record["T"]["sha256"], str) and len(record["T"]["sha256"]) == 64
    assert "T" not in docs

    bytes_in2 = _base_bytes()
    bytes_in2["T"] = b"\xff"
    docs2, record2 = rcc.read_inputs(MAPPING, bytes_in2)
    assert record2["T"]["read_status"] == "malformed"
    assert "T" not in docs2


def test_inputs_an_unknown_letter_raises_value_error():
    bytes_in = _base_bytes()
    bytes_in["Z"] = b"{}"
    with pytest.raises(ValueError):
        rcc.read_inputs(MAPPING, bytes_in)


# ---------------------------------------------------------------------------
# T2 at the pin — 30 rows, ids, statuses, pointers, sessions
# ---------------------------------------------------------------------------


def _field_id_order() -> list[str]:
    return [f["field_id"] for f in MAPPING["fields"]]


def _evidence_id_order() -> list[str]:
    return [r["evidence_id"] for r in MAPPING["evidence_only"]]


def test_at_the_pin_thirty_rows_in_mapping_order_with_exact_key_sets():
    rows, _ = _build_at_pin()
    expected_ids = _field_id_order() + _evidence_id_order()
    assert [r["id"] for r in rows] == expected_ids
    assert len(rows) == 30
    for r in rows:
        assert set(r) == ROW_KEYS
        assert set(r["source"]) == SOURCE_KEYS


def test_at_the_pin_usd_dir_is_unknown_date_with_empty_values():
    rows, _ = _build_at_pin()
    row = next(r for r in rows if r["id"] == "T.dollar_channel.usd_dir")
    assert row["status"] == "unknown_date"
    assert row["values"] == {}
    assert row["source"]["as_of"] is None


def test_at_the_pin_no_field_row_is_missing():
    rows, _ = _build_at_pin()
    field_ids = set(_field_id_order())
    for r in rows:
        if r["id"] in field_ids:
            assert r["status"] in {"available", "partial", "stale"}, r["id"]


def test_at_the_pin_oil_trend_is_partial_with_bare_sign_issue():
    rows, _ = _build_at_pin()
    row = next(r for r in rows if r["id"] == "C.assets.oil.trend")
    assert row["status"] == "partial"
    assert row["issues"] == ["sign_only_verdict"]
    assert row["values"] == {"trend": "up"}
    assert row["owner_verdict"] is None


def test_at_the_pin_breadth_tone_pointer_is_component_selector():
    rows, _ = _build_at_pin()
    row = next(r for r in rows if r["id"] == "M.components.breadth.tone")
    assert row["source"]["pointer"] == "/components/[key=breadth]/tone"


def test_at_the_pin_session_relation_matches_clock_dates():
    rows, _ = _build_at_pin()
    same_count = 0
    older_count = 0
    for r in rows:
        rel = r["source"]["session_relation"]
        if rel == "same_completed_session":
            same_count += 1
        elif rel == "older_than_completed_session":
            older_count += 1
    assert same_count > 0, "expected at least one same_completed_session row"
    assert older_count > 0, "expected at least one older_than_completed_session row"


def test_at_the_pin_date_october_2_row_is_same_session_and_september_25_is_older():
    docs, record = rcc.read_inputs(MAPPING, _base_bytes())
    rows = rcc.evidence_rows(
        MAPPING, docs, record, analysis_cutoff=CUTOFF, us_session=US_SESSION
    )
    found_oct2 = False
    found_sep25 = False
    for r in rows:
        if r["source"]["as_of"] == "2026-10-02" and not r["source"]["future_dated"]:
            assert r["source"]["session_relation"] == "same_completed_session", r["id"]
            found_oct2 = True
        if r["source"]["as_of"] == "2026-09-25" and not r["source"]["future_dated"]:
            assert r["source"]["session_relation"] == "older_than_completed_session", r["id"]
            found_sep25 = True
    assert found_oct2
    assert found_sep25


# ---------------------------------------------------------------------------
# T3 status ladder — each by editing a deep copy of the base
# ---------------------------------------------------------------------------


def _patch(letter: str, path: list, value):
    base = copy.deepcopy(GOLDEN["base"])
    node = base[letter]
    *parents, last = path
    for seg in parents:
        node = node[seg]
    node[last] = value
    return {l: json.dumps(base[l]).encode() for l in sorted(MAPPING["artifacts"])}


def test_status_dropping_artifact_l_makes_l_state_missing():
    base = copy.deepcopy(GOLDEN["base"])
    base["L"] = None
    bytes_in = {l: json.dumps(base[l]).encode() for l in sorted(MAPPING["artifacts"])}
    docs, record = rcc.read_inputs(MAPPING, bytes_in)
    rows = rcc.evidence_rows(
        MAPPING, docs, record, analysis_cutoff=CUTOFF, us_session=US_SESSION
    )
    row = next(r for r in rows if r["id"] == "L.state")
    assert row["status"] == "missing"
    assert row["values"] == {}
    assert row["owner_verdict"] is None


def test_status_setting_t_asof_to_future_date_makes_t_state_rows_future_dated():
    bytes_in = _patch("T", ["asof"], "2026-10-09")
    docs, record = rcc.read_inputs(MAPPING, bytes_in)
    rows = rcc.evidence_rows(
        MAPPING, docs, record, analysis_cutoff=CUTOFF, us_session=US_SESSION
    )
    state_rows = [r for r in rows if r["id"].startswith("T.state.")]
    assert state_rows
    assert all(r["status"] == "future_dated" for r in state_rows)
    assert all(r["values"] == {} for r in state_rows)


def test_status_setting_t_asof_to_a_non_date_string_is_unknown_date():
    bytes_in = _patch("T", ["asof"], "not a date")
    docs, record = rcc.read_inputs(MAPPING, bytes_in)
    rows = rcc.evidence_rows(
        MAPPING, docs, record, analysis_cutoff=CUTOFF, us_session=US_SESSION
    )
    state_rows = [r for r in rows if r["id"].startswith("T.state.")]
    assert state_rows
    assert all(r["status"] == "unknown_date" for r in state_rows)


def test_status_setting_t_asof_to_naive_datetime_is_unknown_date():
    bytes_in = _patch("T", ["asof"], "2026-10-02T10:00:00")
    docs, record = rcc.read_inputs(MAPPING, bytes_in)
    rows = rcc.evidence_rows(
        MAPPING, docs, record, analysis_cutoff=CUTOFF, us_session=US_SESSION
    )
    state_rows = [r for r in rows if r["id"].startswith("T.state.")]
    assert state_rows
    assert all(r["status"] == "unknown_date" for r in state_rows)


def test_status_setting_m_stale_flag_to_true_makes_breadth_tone_stale_and_keeps_values():
    bytes_in = _patch(
        "M", ["input_vintages", "pct_above_200", "stale"], True
    )
    docs, record = rcc.read_inputs(MAPPING, bytes_in)
    rows = rcc.evidence_rows(
        MAPPING, docs, record, analysis_cutoff=CUTOFF, us_session=US_SESSION
    )
    row = next(r for r in rows if r["id"] == "M.components.breadth.tone")
    assert row["status"] == "stale"
    assert row["values"] == {"tone": "bad"}


def test_status_setting_m_stale_flag_to_a_string_makes_breadth_tone_partial_with_malformed():
    bytes_in = _patch(
        "M", ["input_vintages", "pct_above_200", "stale"], "no"
    )
    docs, record = rcc.read_inputs(MAPPING, bytes_in)
    rows = rcc.evidence_rows(
        MAPPING, docs, record, analysis_cutoff=CUTOFF, us_session=US_SESSION
    )
    row = next(r for r in rows if r["id"] == "M.components.breadth.tone")
    assert row["status"] == "partial"
    assert "malformed" in row["issues"]


def test_status_deleting_m_stale_flag_makes_breadth_tone_partial_with_malformed():
    base = copy.deepcopy(GOLDEN["base"])
    del base["M"]["input_vintages"]["pct_above_200"]["stale"]
    bytes_in = {l: json.dumps(base[l]).encode() for l in sorted(MAPPING["artifacts"])}
    docs, record = rcc.read_inputs(MAPPING, bytes_in)
    rows = rcc.evidence_rows(
        MAPPING, docs, record, analysis_cutoff=CUTOFF, us_session=US_SESSION
    )
    row = next(r for r in rows if r["id"] == "M.components.breadth.tone")
    assert row["status"] == "partial"
    assert "malformed" in row["issues"]


def test_status_setting_eci_comp_yoy_to_zero_records_possible_missing_as_zero():
    for value in (0, 0.0):
        bytes_in = _patch(
            "T", ["state", "inflation", "eci_comp_yoy"], value
        )
        docs, record = rcc.read_inputs(MAPPING, bytes_in)
        rows = rcc.evidence_rows(
            MAPPING, docs, record, analysis_cutoff=CUTOFF, us_session=US_SESSION
        )
        row = next(r for r in rows if r["id"] == "T.state.inflation.eci_comp_yoy")
        assert "possible_missing_as_zero" in row["issues"]


def test_status_setting_eci_comp_yoy_to_nan_via_dict_is_missing():
    base = copy.deepcopy(GOLDEN["base"])
    base["T"]["state"]["inflation"]["eci_comp_yoy"] = float("nan")
    bytes_in = {l: json.dumps(base[l]).encode() for l in sorted(MAPPING["artifacts"])}
    docs, record = rcc.read_inputs(MAPPING, bytes_in)
    rows = rcc.evidence_rows(
        MAPPING, docs, record, analysis_cutoff=CUTOFF, us_session=US_SESSION
    )
    row = next(r for r in rows if r["id"] == "T.state.inflation.eci_comp_yoy")
    assert row["status"] == "missing"


# ---------------------------------------------------------------------------
# T4 date_info
# ---------------------------------------------------------------------------


def test_date_info_handles_date_strings_and_offset_instants():
    assert rcc.date_info("2026-09-25", CUTOFF) == {
        "as_of": "2026-09-25",
        "precision": "date",
        "age_calendar_days": 8,
        "future_dated": False,
    }
    assert rcc.date_info("2026-10-02T15:00:00-04:00", CUTOFF) == {
        "as_of": "2026-10-02T19:00:00+00:00",
        "precision": "datetime",
        "age_calendar_days": 1,
        "future_dated": False,
    }


def test_date_info_an_offset_instant_equal_to_cutoff_is_not_future_dated():
    iso = CUTOFF.isoformat()
    info = rcc.date_info(iso, CUTOFF)
    assert info["precision"] == "datetime"
    assert info["future_dated"] is False
    later = CUTOFF.replace(second=CUTOFF.second + 1).isoformat()
    later_info = rcc.date_info(later, CUTOFF)
    assert later_info["future_dated"] is True


def test_date_info_a_naive_cutoff_raises_value_error():
    naive = datetime(2026, 10, 3, 0, 0)
    with pytest.raises(ValueError):
        rcc.date_info("2026-10-02", naive)


# ---------------------------------------------------------------------------
# T5 state families
# ---------------------------------------------------------------------------


def test_state_families_ten_rows_in_canonical_order():
    rows, record = _build_at_pin()
    families = rcc.state_families(MAPPING, rows)
    assert [f["family_id"] for f in families] == [fid for fid, _ in rcc.STATE_FAMILIES]
    assert len(families) == 10


def test_state_families_every_evidence_family_is_mapped_and_targets_a_known_state():
    known_states = {fid for fid, _ in rcc.STATE_FAMILIES}
    for family in MAPPING["families"]:
        fid = family["evidence_family_id"]
        assert fid in rcc.EVIDENCE_FAMILY_TO_STATE_FAMILY
        assert rcc.EVIDENCE_FAMILY_TO_STATE_FAMILY[fid] in known_states


def test_state_families_volatility_correlation_positioning_is_not_covered_at_the_pin():
    rows, record = _build_at_pin()
    families = rcc.state_families(MAPPING, rows)
    vfam = next(f for f in families if f["family_id"] == "volatility_correlation_positioning")
    assert vfam["coverage"] == "not_covered"
    assert "D.avg_corr" in vfam["evidence_ids"]


def test_state_families_change_and_outlook_is_covered_with_no_evidence_ids():
    rows, record = _build_at_pin()
    families = rcc.state_families(MAPPING, rows)
    change = next(f for f in families if f["family_id"] == "change_and_outlook")
    assert change["coverage"] == "covered"
    assert change["reason"] is None
    assert change["evidence_ids"] == []


def test_state_families_union_of_evidence_ids_is_the_thirty_ids_with_no_duplicates():
    rows, record = _build_at_pin()
    families = rcc.state_families(MAPPING, rows)
    all_ids = [eid for f in families for eid in f["evidence_ids"]]
    expected = [r["id"] for r in rows]
    assert sorted(all_ids) == sorted(expected)
    assert len(all_ids) == len(set(all_ids)) == 30


# ---------------------------------------------------------------------------
# T6 clock_range
# ---------------------------------------------------------------------------


def test_clock_range_at_the_pin_oldest_september_25_newest_october_1():
    rows, record = _build_at_pin()
    rng = rcc.clock_range(rows)
    assert rng["oldest"] == "2026-09-25"
    assert rng["newest"] == "2026-10-01"
    assert sum(rng["by_clock_semantics"].values()) == 30


def test_clock_range_with_every_observation_row_future_dated_both_are_none():
    rows, _ = _build_at_pin()
    mutated = []
    for r in rows:
        copy_r = {k: dict(r) if isinstance(r, dict) else r for k, r in r.items()}
        copy_r["source"] = dict(r["source"])
        copy_r["source"]["future_dated"] = True
        mutated.append(copy_r)
    rng = rcc.clock_range(mutated)
    assert rng["oldest"] is None
    assert rng["newest"] is None


# ---------------------------------------------------------------------------
# T7 purity
# ---------------------------------------------------------------------------


def test_module_source_uses_no_clock_or_io_primitives():
    src = Path(rcc.__file__).read_text(encoding="utf-8")
    banned = ("datetime.now", "time.time", "open(", "read_text", "read_bytes", "requests", "urllib")
    for needle in banned:
        assert needle not in src, f"found banned primitive {needle!r} in module source"