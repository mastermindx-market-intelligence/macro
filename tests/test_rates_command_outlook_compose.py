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
from datetime import date, datetime, timedelta, timezone
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

# ---------------------------------------------------------------------------
# T8 outlook_paths — the nine path cards and what each is waiting on
# ---------------------------------------------------------------------------


def _pin_cards() -> list[dict]:
    rows, record = _build_at_pin()
    docs, _ = rcc.read_inputs(MAPPING, _base_bytes())
    return rcc.outlook_paths(MAPPING, docs, rows)


CARD_KEYS = {"path_id", "family", "conditions", "family_readings", "watch"}
COND_KEYS = {"condition_id", "statement_id", "evidence_ids", "reading", "reason"}
WATCH_KEYS = {"condition_id", "next_scheduled", "owner_ref"}
EVIDENCE_IDS = (
    [r["field_id"] for r in MAPPING["fields"]]
    + [r["evidence_id"] for r in MAPPING["evidence_only"]]
)


def _golden_cards() -> list[dict]:
    """The cards the pin promises, derived from GOLDEN['pin']['conditions'] and
    GOLDEN['pin']['family_readings']."""
    cards: list[dict] = []
    for path in MAPPING["paths"]:
        conds = []
        for c in path["conditions"]:
            golden = GOLDEN["pin"]["conditions"][c["condition_id"]]
            conds.append({
                "condition_id": c["condition_id"],
                "statement_id": c["statement_id"],
                "evidence_ids": ([c["field_id"]] if c["field_id"] is not None else [])
                + c["evidence_refs"],
                "reading": golden[0],
                "reason": golden[1],
            })
        cards.append({
            "path_id": path["path_id"],
            "family": path["family"],
            "conditions": conds,
            "family_readings": [
                {"evidence_family_id": fam, "reading": reading}
                for fam, reading in GOLDEN["pin"]["family_readings"][path["path_id"]].items()
            ],
            "watch": [],  # computed below
        })
    return cards


def test_outlook_paths_at_the_pin_nine_cards_in_mapping_order_with_five_keys():
    cards = _pin_cards()
    assert [c["path_id"] for c in cards] == [p["path_id"] for p in MAPPING["paths"]]
    assert len(cards) == 9
    for c in cards:
        assert set(c) == CARD_KEYS


def test_outlook_paths_at_the_pin_every_condition_matches_golden_and_key_sets():
    cards = _pin_cards()
    golden = _golden_cards()
    assert [c["path_id"] for c in cards] == [g["path_id"] for g in golden]
    for card, gold in zip(cards, golden):
        assert [c["condition_id"] for c in card["conditions"]] == [
            c["condition_id"] for c in gold["conditions"]
        ]
        for observed, expected in zip(card["conditions"], gold["conditions"]):
            assert set(observed) == COND_KEYS
            # All 21 field rows are available at the pin, so reading/reason
            # match the golden literally for every condition.
            assert (observed["reading"], observed["reason"]) == (
                expected["reading"],
                expected["reason"],
            )
        assert card["family_readings"] == gold["family_readings"]


def test_outlook_paths_stale_m_field_makes_breadth_tone_conditions_unknown_with_owner():
    base = copy.deepcopy(GOLDEN["base"])
    base["M"]["input_vintages"]["pct_above_200"]["stale"] = True
    bytes_in = {l: json.dumps(base[l]).encode() for l in sorted(MAPPING["artifacts"])}
    docs, record = rcc.read_inputs(MAPPING, bytes_in)
    rows = rcc.evidence_rows(
        MAPPING, docs, record, analysis_cutoff=CUTOFF, us_session=US_SESSION
    )
    cards = rcc.outlook_paths(MAPPING, docs, rows)
    producer = next(
        f["producer"] for f in MAPPING["fields"] if f["field_id"] == "M.components.breadth.tone"
    )
    affected = [
        cond
        for path in MAPPING["paths"]
        for cond in path["conditions"]
        if cond["field_id"] == "M.components.breadth.tone"
    ]
    assert affected, "expected at least one condition on M.components.breadth.tone"
    for cond_in in affected:
        card = next(c for c in cards if c["path_id"].startswith(cond_in["condition_id"].split("-")[0] + "-") or True)
        # locate the card whose path contains this condition_id
        target_card = next(
            c for c in cards
            if any(x["condition_id"] == cond_in["condition_id"] for x in c["conditions"])
        )
        observed = next(
            x for x in target_card["conditions"] if x["condition_id"] == cond_in["condition_id"]
        )
        assert observed["reading"] == "unknown"
        assert observed["reason"] == "stale"
        watch_entry = next(
            w for w in target_card["watch"] if w["condition_id"] == cond_in["condition_id"]
        )
        assert watch_entry["next_scheduled"] is None
        assert watch_entry["owner_ref"] == producer


def test_outlook_paths_future_dated_t_makes_t_state_conditions_unknown_keeps_yield_momentum():
    base = copy.deepcopy(GOLDEN["base"])
    base["T"]["asof"] = "2026-10-09"
    bytes_in = {l: json.dumps(base[l]).encode() for l in sorted(MAPPING["artifacts"])}
    docs, record = rcc.read_inputs(MAPPING, bytes_in)
    rows = rcc.evidence_rows(
        MAPPING, docs, record, analysis_cutoff=CUTOFF, us_session=US_SESSION
    )
    cards = rcc.outlook_paths(MAPPING, docs, rows)
    t_state_fields = [
        f["field_id"] for f in MAPPING["fields"] if f["field_id"].startswith("T.state.")
    ]
    ym_fields = [
        f["field_id"]
        for f in MAPPING["fields"]
        if f["field_id"].startswith("T.yield_momentum.series.")
    ]
    assert t_state_fields and ym_fields
    for path in MAPPING["paths"]:
        for cond_in in path["conditions"]:
            fid = cond_in["field_id"]
            if fid is None:
                continue
            target_card = next(
                c for c in cards
                if any(x["condition_id"] == cond_in["condition_id"] for x in c["conditions"])
            )
            observed = next(
                x for x in target_card["conditions"] if x["condition_id"] == cond_in["condition_id"]
            )
            if fid in t_state_fields:
                assert observed["reading"] == "unknown"
                assert observed["reason"] == "future_dated"
            elif fid in ym_fields:
                golden = GOLDEN["pin"]["conditions"][cond_in["condition_id"]]
                assert (observed["reading"], observed["reason"]) == (golden[0], golden[1])


def test_outlook_paths_dropped_artifact_l_makes_l_state_conditions_missing():
    base = copy.deepcopy(GOLDEN["base"])
    base["L"] = None
    bytes_in = {l: json.dumps(base[l]).encode() for l in sorted(MAPPING["artifacts"])}
    docs, record = rcc.read_inputs(MAPPING, bytes_in)
    rows = rcc.evidence_rows(
        MAPPING, docs, record, analysis_cutoff=CUTOFF, us_session=US_SESSION
    )
    cards = rcc.outlook_paths(MAPPING, docs, rows)
    for path in MAPPING["paths"]:
        for cond_in in path["conditions"]:
            if cond_in["field_id"] != "L.state":
                continue
            target_card = next(
                c for c in cards
                if any(x["condition_id"] == cond_in["condition_id"] for x in c["conditions"])
            )
            observed = next(
                x for x in target_card["conditions"] if x["condition_id"] == cond_in["condition_id"]
            )
            assert observed["reading"] == "unknown"
            assert observed["reason"] == "missing"


def test_outlook_paths_condition_with_no_field_reads_open_reason_with_no_owner():
    base = copy.deepcopy(GOLDEN["base"])
    bytes_in = {l: json.dumps(base[l]).encode() for l in sorted(MAPPING["artifacts"])}
    docs, record = rcc.read_inputs(MAPPING, bytes_in)
    rows = rcc.evidence_rows(
        MAPPING, docs, record, analysis_cutoff=CUTOFF, us_session=US_SESSION
    )
    cards = rcc.outlook_paths(MAPPING, docs, rows)
    no_field_conds = [
        c
        for path in MAPPING["paths"]
        for c in path["conditions"]
        if c["field_id"] is None
    ]
    assert no_field_conds
    for cond_in in no_field_conds:
        target_card = next(
            card for card in cards
            if any(x["condition_id"] == cond_in["condition_id"] for x in card["conditions"])
        )
        observed = next(
            x for x in target_card["conditions"]
            if x["condition_id"] == cond_in["condition_id"]
        )
        assert observed["reading"] == "unknown"
        assert observed["reason"] == cond_in["open_reason"]
        assert observed["evidence_ids"] == cond_in["evidence_refs"]
        watch_entry = next(
            (w for w in target_card["watch"] if w["condition_id"] == cond_in["condition_id"]),
            None,
        )
        assert watch_entry is not None
        assert watch_entry["next_scheduled"] is None
        assert watch_entry["owner_ref"] is None


def test_outlook_paths_evidence_ids_are_among_the_thirty_and_watch_lists_unknown_conditions():
    cards = _pin_cards()
    set_of_thirty = set(EVIDENCE_IDS)
    for card in cards:
        unknown_ids = []
        for cond in card["conditions"]:
            assert set(cond["evidence_ids"]).issubset(set_of_thirty), (
                cond["condition_id"], cond["evidence_ids"]
            )
            if cond["reading"] == "unknown":
                unknown_ids.append(cond["condition_id"])
        assert [w["condition_id"] for w in card["watch"]] == unknown_ids


def test_outlook_paths_keep_the_reader_s_own_reason_for_a_field_it_refuses():
    # The owner default with its input missing: the reader refuses the field
    # with its own finer reason, while the evidence row is only "partial".
    # The card must carry the reader's word, not the row's status.
    base = copy.deepcopy(GOLDEN["base"])
    base["T"]["state"]["rates"]["direction"] = "stable"
    base["T"]["state"]["rates"]["real_10y_chg_63d_bp"] = None
    bytes_in = {l: json.dumps(base[l]).encode() for l in sorted(MAPPING["artifacts"])}
    docs, record = rcc.read_inputs(MAPPING, bytes_in)
    rows = rcc.evidence_rows(
        MAPPING, docs, record, analysis_cutoff=CUTOFF, us_session=US_SESSION
    )
    row = next(r for r in rows if r["id"] == "T.state.rates.direction")
    assert row["status"] == "partial"
    assert row["issues"] == ["owner_default_on_missing"]
    cards = rcc.outlook_paths(MAPPING, docs, rows)
    seen = 0
    for path, card in zip(MAPPING["paths"], cards):
        for cond_in, observed in zip(path["conditions"], card["conditions"]):
            if cond_in["field_id"] != "T.state.rates.direction":
                continue
            seen += 1
            assert observed["reading"] == "unknown"
            assert observed["reason"] == "owner_default_on_missing"
            assert cond_in["condition_id"] in [w["condition_id"] for w in card["watch"]]
    assert seen > 0


# ---------------------------------------------------------------------------
# T9 pick_baseline — which earlier read is the new build's baseline
# ---------------------------------------------------------------------------


def _session_of(dt):
    return (dt - timedelta(hours=21)).date()


SESSION_OF = _session_of


def _prev(cutoff="2026-10-03T02:00:00+00:00", baseline=None):
    out = {
        "schema_version": "regime_outlook.v1",
        "analysis_cutoff": cutoff,
        "evidence": [
            {
                "id": "alpha",
                "values": {"v": 1},
                "owner_verdict": {"token": 1, "verdict_class": "x"},
                "status": "available",
                "source": {"as_of": "2026-10-02T15:00:00-04:00"},
            },
            {
                "id": "beta",
                "values": {"v": 2},
                "owner_verdict": None,
                "status": "stale",
                "source": {"as_of": "2026-09-30"},
            },
        ],
    }
    if baseline is not None:
        out["baseline"] = baseline
    return out


def test_pick_baseline_none_previous_is_no_earlier_projection():
    out = rcc.pick_baseline(None, us_session=date(2026, 10, 3), session_of=SESSION_OF)
    assert out == {"status": "absent", "reason": "no_earlier_projection"}


@pytest.mark.parametrize(
    "previous",
    [
        [],
        {"schema_version": "wrong", "analysis_cutoff": "2026-10-03T02:00:00+00:00", "evidence": []},
        {"schema_version": "regime_outlook.v1", "analysis_cutoff": "2026-10-03T02:00:00+00:00", "evidence": "x"},
        {"schema_version": "regime_outlook.v1", "analysis_cutoff": "2026-10-03T02:00:00+00:00", "evidence": ["x"]},
        {"schema_version": "regime_outlook.v1", "analysis_cutoff": "2026-10-03T02:00:00+00:00", "evidence": [{"source": {}}]},
        {"schema_version": "regime_outlook.v1", "analysis_cutoff": "2026-10-03T02:00:00", "evidence": []},
        {"schema_version": "regime_outlook.v1", "analysis_cutoff": 12345, "evidence": []},
    ],
)
def test_pick_baseline_unreadable_previous_is_previous_unreadable(previous):
    out = rcc.pick_baseline(previous, us_session=date(2026, 10, 3), session_of=SESSION_OF)
    assert out == {"status": "absent", "reason": "previous_unreadable"}


def test_pick_baseline_session_of_raising_is_previous_unreadable():
    def boom(dt):
        raise RuntimeError("nope")

    out = rcc.pick_baseline(_prev(), us_session=date(2026, 10, 3), session_of=boom)
    assert out == {"status": "absent", "reason": "previous_unreadable"}


def test_pick_baseline_us_session_none_with_valid_stored_baseline_returns_deep_copy():
    stored = {
        "analysis_cutoff": "2026-10-02T02:00:00+00:00",
        "us_session": "2026-10-01",
        "evidence": {
            "alpha": {
                "values": {"v": 1},
                "owner_verdict": None,
                "status": "available",
                "as_of": "2026-10-01",
            }
        },
    }
    out = rcc.pick_baseline(_prev(baseline=stored), us_session=None, session_of=SESSION_OF)
    assert out == stored
    assert out is not stored
    assert out["evidence"] is not stored["evidence"]


def test_pick_baseline_us_session_none_without_stored_baseline_is_us_session_unavailable():
    out = rcc.pick_baseline(_prev(), us_session=None, session_of=SESSION_OF)
    assert out == {"status": "absent", "reason": "us_session_unavailable"}


def test_pick_baseline_us_session_none_with_list_evidence_is_us_session_unavailable():
    bad = {
        "analysis_cutoff": "2026-10-02T02:00:00+00:00",
        "us_session": "2026-10-01",
        "evidence": [],
    }
    out = rcc.pick_baseline(_prev(baseline=bad), us_session=None, session_of=SESSION_OF)
    assert out == {"status": "absent", "reason": "us_session_unavailable"}


def test_pick_baseline_us_session_none_with_non_string_us_session_is_us_session_unavailable():
    bad = {
        "analysis_cutoff": "2026-10-02T02:00:00+00:00",
        "us_session": 7,
        "evidence": {"a": {}},
    }
    out = rcc.pick_baseline(_prev(baseline=bad), us_session=None, session_of=SESSION_OF)
    assert out == {"status": "absent", "reason": "us_session_unavailable"}


def test_pick_baseline_next_session_builds_new_baseline_from_previous():
    prev = _prev()
    out = rcc.pick_baseline(prev, us_session=date(2026, 10, 3), session_of=SESSION_OF)
    assert out["analysis_cutoff"] == "2026-10-03T02:00:00+00:00"
    assert out["us_session"] == "2026-10-02"
    assert set(out["evidence"]) == {"alpha", "beta"}
    for entry in out["evidence"].values():
        assert set(entry) == {"values", "owner_verdict", "status", "as_of"}
    assert out["evidence"]["alpha"]["values"] == {"v": 1}
    assert out["evidence"]["alpha"]["owner_verdict"] == {"token": 1, "verdict_class": "x"}
    assert out["evidence"]["alpha"]["status"] == "available"
    assert out["evidence"]["alpha"]["as_of"] == "2026-10-02T15:00:00-04:00"
    assert out["evidence"]["beta"]["values"] == {"v": 2}
    assert out["evidence"]["beta"]["owner_verdict"] is None
    assert out["evidence"]["beta"]["status"] == "stale"
    assert out["evidence"]["beta"]["as_of"] == "2026-09-30"


def test_pick_baseline_next_session_ignores_stored_older_baseline():
    stored = {
        "analysis_cutoff": "2026-09-30T02:00:00+00:00",
        "us_session": "2026-09-29",
        "evidence": {
            "marker": {
                "values": {},
                "owner_verdict": None,
                "status": "stale",
                "as_of": "2026-09-29",
            }
        },
    }
    out = rcc.pick_baseline(
        _prev(baseline=stored), us_session=date(2026, 10, 3), session_of=SESSION_OF
    )
    assert out["analysis_cutoff"] == "2026-10-03T02:00:00+00:00"
    assert "marker" not in out["evidence"]
    assert set(out["evidence"]) == {"alpha", "beta"}


def test_pick_baseline_cutoff_with_trailing_z_parses_to_same_baseline():
    out = rcc.pick_baseline(
        _prev(cutoff="2026-10-03T02:00:00Z"),
        us_session=date(2026, 10, 3),
        session_of=SESSION_OF,
    )
    assert out["analysis_cutoff"] == "2026-10-03T02:00:00Z"
    assert out["us_session"] == "2026-10-02"
    assert set(out["evidence"]) == {"alpha", "beta"}


def test_pick_baseline_same_session_with_older_stored_baseline_returns_deep_copy():
    stored = {
        "analysis_cutoff": "2026-09-30T02:00:00+00:00",
        "us_session": "2026-10-01",
        "evidence": {
            "alpha": {
                "values": {"v": 99},
                "owner_verdict": None,
                "status": "stale",
                "as_of": "2026-10-01",
            }
        },
    }
    prev = _prev(baseline=stored)
    out = rcc.pick_baseline(prev, us_session=date(2026, 10, 2), session_of=SESSION_OF)
    assert out == stored
    assert out is not stored
    assert out["evidence"] is not stored["evidence"]


def test_pick_baseline_same_session_with_no_stored_baseline_is_no_earlier_projection():
    out = rcc.pick_baseline(_prev(), us_session=date(2026, 10, 2), session_of=SESSION_OF)
    assert out == {"status": "absent", "reason": "no_earlier_projection"}


def test_pick_baseline_same_session_with_baseline_same_day_is_no_earlier_projection():
    stored = {
        "analysis_cutoff": "2026-09-30T02:00:00+00:00",
        "us_session": "2026-10-02",
        "evidence": {
            "alpha": {
                "values": {},
                "owner_verdict": None,
                "status": "available",
                "as_of": "2026-10-02",
            }
        },
    }
    out = rcc.pick_baseline(
        _prev(baseline=stored), us_session=date(2026, 10, 2), session_of=SESSION_OF
    )
    assert out == {"status": "absent", "reason": "no_earlier_projection"}


def test_pick_baseline_previous_later_than_us_session_is_no_earlier_projection():
    out = rcc.pick_baseline(_prev(), us_session=date(2026, 10, 1), session_of=SESSION_OF)
    assert out == {"status": "absent", "reason": "no_earlier_projection"}


def test_pick_baseline_never_mutates_previous():
    stored = {
        "analysis_cutoff": "2026-09-30T02:00:00+00:00",
        "us_session": "2026-10-01",
        "evidence": {"alpha": {"values": {}, "owner_verdict": None, "status": "stale", "as_of": "2026-10-01"}},
    }
    cases = [
        (None, date(2026, 10, 3)),
        (_prev(), date(2026, 10, 3)),
        (_prev(), None),
        (_prev(baseline=stored), date(2026, 10, 2)),
        (_prev(), date(2026, 10, 2)),
        (_prev(), date(2026, 10, 1)),
    ]
    for previous, us_session in cases:
        before = copy.deepcopy(previous)
        rcc.pick_baseline(previous, us_session=us_session, session_of=SESSION_OF)
        assert previous == before


def test_pick_baseline_returned_baseline_mutation_does_not_change_previous():
    stored = {
        "analysis_cutoff": "2026-09-30T02:00:00+00:00",
        "us_session": "2026-10-01",
        "evidence": {
            "alpha": {
                "values": {"v": 1},
                "owner_verdict": None,
                "status": "available",
                "as_of": "2026-10-01",
            }
        },
    }
    prev = _prev(baseline=stored)
    snapshot = copy.deepcopy(prev)
    out = rcc.pick_baseline(prev, us_session=None, session_of=SESSION_OF)
    out["evidence"]["alpha"]["values"] = "MUTATED"
    out["us_session"] = "MUTATED"
    assert prev == snapshot


def test_pick_baseline_returned_new_baseline_mutation_does_not_change_previous():
    prev = _prev()
    snapshot = copy.deepcopy(prev)
    out = rcc.pick_baseline(prev, us_session=date(2026, 10, 3), session_of=SESSION_OF)
    out["evidence"]["alpha"]["values"] = "MUTATED"
    out["analysis_cutoff"] = "MUTATED"
    out["us_session"] = "MUTATED"
    assert prev == snapshot


def test_pick_baseline_new_baseline_shares_no_nested_object_with_previous():
    prev = _prev()
    snapshot = copy.deepcopy(prev)
    out = rcc.pick_baseline(prev, us_session=date(2026, 10, 3), session_of=SESSION_OF)
    out["evidence"]["alpha"]["values"]["v"] = "MUTATED"
    out["evidence"]["alpha"]["owner_verdict"]["token"] = "MUTATED"
    assert prev == snapshot


def _prev_with_ids(*ids):
    prev = _prev()
    row = prev["evidence"][0]
    prev["evidence"] = [dict(row, id=i) for i in ids]
    return prev


@pytest.mark.parametrize(
    "previous",
    [
        _prev_with_ids(7),
        _prev_with_ids(None),
        _prev_with_ids(["alpha"]),
        _prev_with_ids("alpha", "alpha"),
    ],
    ids=["int_id", "none_id", "list_id", "duplicate_id"],
)
def test_pick_baseline_row_ids_must_be_distinct_strings(previous):
    out = rcc.pick_baseline(previous, us_session=date(2026, 10, 3), session_of=SESSION_OF)
    assert out == {"status": "absent", "reason": "previous_unreadable"}


@pytest.mark.parametrize(
    "returned",
    [None, "2026-10-02", datetime(2026, 10, 2, tzinfo=timezone.utc)],
    ids=["none", "string", "datetime"],
)
def test_pick_baseline_session_of_must_return_a_plain_date(returned):
    out = rcc.pick_baseline(_prev(), us_session=date(2026, 10, 3), session_of=lambda dt: returned)
    assert out == {"status": "absent", "reason": "previous_unreadable"}


def test_session_helper_matches_the_documented_cutoffs():
    cut = datetime(2026, 10, 3, 2, 0, tzinfo=timezone.utc)
    assert SESSION_OF(cut) == date(2026, 10, 2)
    assert SESSION_OF(cut + timedelta(hours=24)) == date(2026, 10, 3)
    assert SESSION_OF(datetime(2026, 10, 1, 2, 0, tzinfo=timezone.utc)) == date(2026, 9, 30)


# ---------------------------------------------------------------------------
# T10 list_changes — what changed since the baseline (appended; no existing
# symbol is touched)
# ---------------------------------------------------------------------------


def _erow(eid, values, verdict, status, as_of, semantics="owner_snapshot_date"):
    return {
        "id": eid,
        "values": values,
        "owner_verdict": verdict,
        "status": status,
        "source": {"clock_semantics": semantics, "as_of": as_of},
    }


def _baseline(rows):
    return {
        "analysis_cutoff": "2026-10-03T02:00:00+00:00",
        "us_session": "2026-10-02",
        "evidence": {
            r["id"]: {
                "values": r["values"],
                "owner_verdict": r["owner_verdict"],
                "status": r["status"],
                "as_of": r["source"]["as_of"],
            }
            for r in rows
        },
    }


# L1 ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "baseline",
    [
        None,
        {"status": "absent", "reason": "no_earlier_projection"},
        {"analysis_cutoff": "2026-10-03T02:00:00+00:00", "us_session": "2026-10-02", "evidence": []},
        {"analysis_cutoff": "2026-10-03T02:00:00+00:00", "us_session": "2026-10-02", "evidence": "x"},
    ],
    ids=["none", "absent", "list_evidence", "non_dict_evidence"],
)
def test_list_changes_bad_baselines_return_empty(baseline):
    rows = [_erow("a", {"v": 1}, None, "available", "2026-10-02")]
    assert rcc.list_changes(baseline, rows) == []


# L2 ---------------------------------------------------------------------


def test_list_changes_baseline_built_from_same_rows_returns_empty():
    rows = [
        _erow("a", {"v": 1}, None, "available", "2026-10-02"),
        _erow("b", {"v": 2}, {"token": 1, "verdict_class": "x"}, "stale", "2026-09-30"),
    ]
    assert rcc.list_changes(_baseline(rows), rows) == []


# L3 ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "baseline_status,current_status,kind",
    [
        ("available", "stale", "became_stale"),
        ("partial", "stale", "became_stale"),
        ("stale", "available", "became_available"),
        ("missing", "available", "became_available"),
        ("available", "missing", "became_unavailable"),
        ("stale", "unknown_date", "became_unavailable"),
        ("partial", "future_dated", "became_unavailable"),
        ("available", "partial", "became_unavailable"),
        ("stale", "partial", "became_unavailable"),
        ("missing", "partial", "unattributed"),
        ("missing", "unknown_date", "unattributed"),
        ("unknown_date", "future_dated", "unattributed"),
    ],
)
def test_list_changes_status_transitions(baseline_status, current_status, kind):
    baseline_rows = [_erow("a", {"v": 1}, None, baseline_status, "2026-10-02")]
    current_rows = [_erow("a", {"v": 1}, None, current_status, "2026-10-02")]
    out = rcc.list_changes(_baseline(baseline_rows), current_rows)
    assert out == [{
        "evidence_id": "a",
        "change_kind": kind,
        "from": {
            "values": {"v": 1},
            "owner_verdict": None,
            "status": baseline_status,
            "as_of": "2026-10-02",
        },
        "to": {
            "values": {"v": 1},
            "owner_verdict": None,
            "status": current_status,
            "as_of": "2026-10-02",
        },
    }]


# L4 ---------------------------------------------------------------------


def test_list_changes_same_missing_status_and_different_as_of_is_clock_only():
    baseline_rows = [_erow("a", {}, None, "missing", "2026-09-30")]
    current_rows = [_erow("a", {}, None, "missing", "2026-10-02")]
    out = rcc.list_changes(_baseline(baseline_rows), current_rows)
    assert out == [{
        "evidence_id": "a",
        "change_kind": "clock_only",
        "from": {"values": {}, "owner_verdict": None, "status": "missing", "as_of": "2026-09-30"},
        "to": {"values": {}, "owner_verdict": None, "status": "missing", "as_of": "2026-10-02"},
    }]


def test_list_changes_same_missing_status_and_equal_as_of_returns_empty():
    rows = [_erow("a", {}, None, "missing", "2026-10-02")]
    assert rcc.list_changes(_baseline(rows), rows) == []


# L5 ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "b_as_of,c_as_of,b_values,c_values,b_verdict,c_verdict,kind",
    [
        ("2026-10-02", "2026-10-02", {"v": 1}, {"v": 2}, None, None, "value_revised"),
        ("2026-10-02", "2026-10-03", {"v": 1}, {"v": 1}, None, {"token": "yes"}, "owner_verdict_changed"),
        ("2026-10-02", "2026-10-03", {"v": 1}, {"v": 2}, None, None, "observation_advanced"),
        ("2026-10-02", "2026-10-03", {"v": 1}, {"v": 1}, None, None, "clock_only"),
        ("2026-10-03", "2026-10-02", {"v": 1}, {"v": 2}, None, None, "unattributed"),
        ("2026-10-03", "2026-10-02", {"v": 1}, {"v": 1}, None, None, "clock_only"),
        (None, "2026-10-02", {"v": 1}, {"v": 2}, None, None, "unattributed"),
        (None, "2026-10-02", {"v": 1}, {"v": 1}, None, None, "clock_only"),
    ],
    ids=[
        "same_asof_new_values",
        "later_asof_new_verdict",
        "later_asof_new_values",
        "later_asof_only",
        "earlier_asof_new_values",
        "earlier_asof_only",
        "baseline_none_asof_new_values",
        "baseline_none_asof_only",
    ],
)
def test_list_changes_observation_clock_semantics(
    b_as_of, c_as_of, b_values, c_values, b_verdict, c_verdict, kind
):
    baseline_rows = [_erow("a", b_values, b_verdict, "available", b_as_of, semantics="source_observation_date")]
    current_rows = [_erow("a", c_values, c_verdict, "available", c_as_of, semantics="source_observation_date")]
    out = rcc.list_changes(_baseline(baseline_rows), current_rows)
    assert len(out) == 1
    assert out[0]["evidence_id"] == "a"
    assert out[0]["change_kind"] == kind


# L6 ---------------------------------------------------------------------


def test_list_changes_owner_snapshot_clock_new_values_same_as_of_is_unattributed():
    baseline_rows = [_erow("a", {"v": 1}, None, "available", "2026-10-02")]
    current_rows = [_erow("a", {"v": 2}, None, "available", "2026-10-02")]
    out = rcc.list_changes(_baseline(baseline_rows), current_rows)
    assert out == [{
        "evidence_id": "a",
        "change_kind": "unattributed",
        "from": {"values": {"v": 1}, "owner_verdict": None, "status": "available", "as_of": "2026-10-02"},
        "to": {"values": {"v": 2}, "owner_verdict": None, "status": "available", "as_of": "2026-10-02"},
    }]


def test_list_changes_owner_snapshot_clock_new_verdict_later_as_of_is_unattributed():
    baseline_rows = [_erow("a", {"v": 1}, None, "available", "2026-10-02")]
    current_rows = [_erow("a", {"v": 1}, {"token": "yes"}, "available", "2026-10-03")]
    out = rcc.list_changes(_baseline(baseline_rows), current_rows)
    assert out == [{
        "evidence_id": "a",
        "change_kind": "unattributed",
        "from": {"values": {"v": 1}, "owner_verdict": None, "status": "available", "as_of": "2026-10-02"},
        "to": {"values": {"v": 1}, "owner_verdict": {"token": "yes"}, "status": "available", "as_of": "2026-10-03"},
    }]


def test_list_changes_owner_snapshot_clock_later_as_of_only_is_clock_only():
    baseline_rows = [_erow("a", {"v": 1}, None, "available", "2026-10-02")]
    current_rows = [_erow("a", {"v": 1}, None, "available", "2026-10-03")]
    out = rcc.list_changes(_baseline(baseline_rows), current_rows)
    assert out == [{
        "evidence_id": "a",
        "change_kind": "clock_only",
        "from": {"values": {"v": 1}, "owner_verdict": None, "status": "available", "as_of": "2026-10-02"},
        "to": {"values": {"v": 1}, "owner_verdict": None, "status": "available", "as_of": "2026-10-03"},
    }]


# L7 ---------------------------------------------------------------------


def test_list_changes_ids_only_on_one_side_are_mapping_version_changed_in_authored_then_sorted_order():
    current_rows = [
        _erow("a", {"v": 1}, None, "available", "2026-10-02"),
        _erow("b", {"v": 2}, None, "available", "2026-10-02"),
        _erow("c", {"v": 3}, None, "available", "2026-10-02"),
    ]
    baseline_rows = [
        _erow("b", {"v": 2}, None, "available", "2026-10-02"),
        _erow("z", {"v": 9}, None, "available", "2026-10-02"),
        _erow("y", {"v": 8}, None, "available", "2026-10-02"),
    ]
    out = rcc.list_changes(_baseline(baseline_rows), current_rows)
    assert [e["evidence_id"] for e in out] == ["a", "c", "y", "z"]
    assert all(e["change_kind"] == "mapping_version_changed" for e in out)
    assert [e["from"] for e in out[:2]] == [None, None]
    assert [e["to"] for e in out[2:]] == [None, None]


# L8 ---------------------------------------------------------------------


def test_list_changes_each_entry_has_exactly_the_four_keys():
    current_rows = [_erow("a", {"v": 1}, None, "available", "2026-10-02")]
    baseline_rows = [_erow("b", {"v": 2}, None, "available", "2026-10-02")]
    out = rcc.list_changes(_baseline(baseline_rows), current_rows)
    for entry in out:
        assert set(entry) == {"evidence_id", "change_kind", "from", "to"}


def test_list_changes_emits_only_kinds_in_change_kinds():
    baseline_rows = [
        _erow("a", {"v": 1}, None, "available", "2026-10-02"),
        _erow("b", {"v": 1}, None, "available", "2026-10-02"),
        _erow("c", {"v": 1}, None, "available", "2026-10-02"),
        _erow("d", {"v": 1}, None, "available", "2026-10-02"),
    ]
    current_rows = [
        _erow("a", {"v": 1}, None, "stale", "2026-10-02"),  # became_stale
        _erow("b", {"v": 1}, None, "missing", "2026-10-02"),  # became_unavailable
        _erow("c", {"v": 2}, None, "available", "2026-10-03", semantics="source_observation_date"),  # observation_advanced
        _erow("d", {"v": 1}, None, "available", "2026-10-03"),  # clock_only
    ]
    out = rcc.list_changes(_baseline(baseline_rows), current_rows)
    assert {e["change_kind"] for e in out}.issubset(set(rcc.CHANGE_KINDS))


def test_change_kinds_is_the_nine_word_tuple_literally():
    assert rcc.CHANGE_KINDS == (
        "observation_advanced",
        "value_revised",
        "owner_verdict_changed",
        "became_stale",
        "became_available",
        "became_unavailable",
        "clock_only",
        "mapping_version_changed",
        "unattributed",
    )


def test_list_changes_does_not_mutate_baseline_or_evidence():
    baseline_rows = [
        _erow("a", {"v": 1}, None, "available", "2026-10-02"),
        _erow("b", {"v": 2}, None, "available", "2026-10-03"),
    ]
    current_rows = [
        _erow("a", {"v": 9}, None, "stale", "2026-10-04"),
        _erow("b", {"v": 2}, None, "available", "2026-10-03"),
    ]
    baseline = _baseline(baseline_rows)
    baseline_snapshot = copy.deepcopy(baseline)
    current_snapshot = copy.deepcopy(current_rows)
    out = rcc.list_changes(baseline, current_rows)
    assert baseline == baseline_snapshot
    assert current_rows == current_snapshot
    assert out[0]["from"] is not baseline["evidence"]["a"]
    assert out[0]["to"] is not current_rows[0]
    out[0]["from"]["values"]["v"] = "MUTATED"
    out[0]["to"]["values"]["v"] = "MUTATED"
    assert baseline["evidence"]["a"]["values"] == {"v": 1}
    assert current_rows[0]["values"] == {"v": 9}
