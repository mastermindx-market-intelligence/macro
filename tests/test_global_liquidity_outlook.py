"""Tests for engine/global_liquidity_outlook.py (GLT T08, measurement-only).

The fixture is a synthetic H.4.1 Table 5 row in $ millions (never market
data); every expected number below is exact synthetic arithmetic pinned by
the frozen T08 spec. C16 covers the reserve-identity reconciliation, C15 the
point-in-time announcement admissibility law.
"""

from __future__ import annotations

import copy
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

import engine.global_liquidity_outlook as outlook_module
from engine.global_liquidity_outlook import (
    AUTHORITY,
    BASELINE_SCHEMA,
    CLAIM_LEVEL,
    COMPONENT_LINES,
    COMPONENT_SIGN,
    DEFAULT_DECISION_TZ,
    DEFAULT_HORIZONS_WEEKS,
    DEFAULT_PUBLICATION_TZ,
    ESTIMATE_TYPES,
    H41_ASSETS_LINE,
    H41_BASIS,
    H41_CAPITAL_LINE,
    H41_NONRESERVE_LIABILITY_LINES,
    H41_RESERVES_LINE,
    H41_RRP_FOREIGN_LINE,
    H41_RRP_OTHERS_LINE,
    H41_TGA_LINE,
    SCHEMA,
    SNAPSHOT_OWNER_INPUTS,
    VALIDATED,
    admissible_announcements,
    baseline_comparison,
    compose_component_paths,
    reconcile_reserve_identity,
    snapshot,
)

NY = ZoneInfo("America/New_York")

FR_NOTES = "Federal Reserve notes, net of F.R. Bank holdings"
RRP_FOREIGN = "Reverse repurchase agreements: Foreign official and international accounts"
RRP_OTHERS = "Reverse repurchase agreements: Others"
TERM_DEPOSITS = "Deposits: Term deposits held by depository institutions"
TGA_LINE = "Deposits: U.S. Treasury, General Account"
DEPOSITS_FOREIGN = "Deposits: Foreign official"
DEPOSITS_OTHER = "Deposits: Other"
DEFERRED_CASH = "Deferred availability cash items"
TREASURY_CONTRIBS = "Treasury contributions to credit facilities"
EARNINGS_REMITTANCES = "Earnings remittances due to the U.S. Treasury"
OTHER_LIABILITIES = "Other liabilities and accrued dividends"

FIXTURE_ROW = {
    FR_NOTES: 2_300_000,
    RRP_FOREIGN: 380_000,
    RRP_OTHERS: 150_000,
    TERM_DEPOSITS: 0,
    TGA_LINE: 800_000,
    DEPOSITS_FOREIGN: 10_000,
    DEPOSITS_OTHER: 120_000,
    DEFERRED_CASH: 1_000,
    TREASURY_CONTRIBS: 5_000,
    EARNINGS_REMITTANCES: -230_000,
    OTHER_LIABILITIES: 40_000,
    H41_CAPITAL_LINE: 50_000,
    H41_RESERVES_LINE: 3_000_000,
    H41_ASSETS_LINE: 6_626_000,
}

AS_OF = date(2026, 9, 4)
CUTOFF_UTC = "2026-09-04T04:00:00+00:00"


def make_anchor(row=None):
    return {
        "observed_on": date(2026, 9, 2),
        "published_at": datetime(2026, 9, 3, 16, 30, tzinfo=NY),
        "publication_tz": "America/New_York",
        "row": dict(FIXTURE_ROW if row is None else row),
    }


def make_announcements():
    return [
        {
            "id": "tga-qra-2026q3",
            "component": "treasury_general_account",
            "kind": "schedule",
            "published_at": datetime(2026, 8, 4, 8, 30, tzinfo=NY),
            "changes": [{"effective": date(2026, 9, 30), "level": 850_000}],
        },
        {
            "id": "tga-qra-2026q3-rev",
            "component": "treasury_general_account",
            "kind": "schedule",
            "published_at": date(2026, 9, 10),
            "supersedes": "tga-qra-2026q3",
            "changes": [{"effective": date(2026, 9, 30), "level": 900_000}],
        },
        {
            "id": "financing-shift-2026-09-15",
            "component": "treasury_general_account",
            "kind": "financing_source",
            "published_at": date(2026, 9, 15),
            "changes": [{"effective": date(2026, 9, 16), "delta": -200_000}],
        },
        {
            "id": "same-day-after-cutoff",
            "component": "treasury_general_account",
            "kind": "schedule",
            "published_at": datetime(2026, 9, 4, 8, 30, tzinfo=NY),
            "changes": [{"effective": date(2026, 9, 30), "level": 700_000}],
        },
    ]


def make_assumptions():
    return [
        {
            "id": "qt-runoff-assumption",
            "component": "total_assets",
            "kind": "weekly_delta",
            "value": -5_000,
        },
        {"id": "hold-tga", "component": "treasury_general_account", "kind": "hold_level"},
        {
            "id": "hold-reverse-repo-others",
            "component": "reverse_repo_others",
            "kind": "hold_level",
        },
        {
            "id": "hold-reverse-repo-foreign-official",
            "component": "reverse_repo_foreign_official",
            "kind": "hold_level",
        },
        {
            "id": "hold-federal-reserve-notes",
            "component": "federal_reserve_notes",
            "kind": "hold_level",
        },
        {
            "id": "hold-other-nonreserve-and-capital",
            "component": "other_nonreserve_and_capital",
            "kind": "hold_level",
        },
    ]


def make_outlook(**kwargs):
    return compose_component_paths(
        make_anchor(), make_announcements(), make_assumptions(), as_of=AS_OF, **kwargs
    )


FORBIDDEN_KEY_FRAGMENTS = ("probability", "forecast", "calibrat", "score", "confidence")
MODULE_FORBIDDEN_FRAGMENTS = (
    "probability",
    "forecast_prob",
    "calibrat",
    "score",
    "confidence",
    "statistical_forecast",
)


def _walk_keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _walk_keys(value)
    elif isinstance(node, (list, tuple)):
        for item in node:
            yield from _walk_keys(item)


def _walk_numbers(node):
    if isinstance(node, dict):
        for value in node.values():
            yield from _walk_numbers(value)
    elif isinstance(node, (list, tuple)):
        for item in node:
            yield from _walk_numbers(item)
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        yield node


# ---------------------------------------------------------------------------
# C16 -- H.4.1 Table 5 reserve identity reconciliation
# ---------------------------------------------------------------------------


def test_c16_identity_reconciles_on_fixture_row():
    recon = reconcile_reserve_identity(FIXTURE_ROW)
    assert recon["basis"] == H41_BASIS
    assert recon["assets"] == 6_626_000
    assert recon["reserves_reported"] == 3_000_000
    assert recon["capital"] == 50_000
    assert recon["nonreserve_total"] == 3_626_000
    assert recon["reserves_implied"] == 3_000_000
    assert recon["residual"] == 0
    assert recon["reconciles"] is True
    assert recon["duplicate_lines"] == []
    assert recon["undeclared_lines"] == []
    assert recon["missing"] == []
    assert recon["lines_used"] == list(H41_NONRESERVE_LIABILITY_LINES) + [H41_CAPITAL_LINE]
    assert set(recon["nonreserve_liabilities"]) == set(H41_NONRESERVE_LIABILITY_LINES)
    assert recon["nonreserve_liabilities"][EARNINGS_REMITTANCES] == -230_000


def test_c16_dropped_liability_prints_nonzero_residual():
    dropped = [n for n in H41_NONRESERVE_LIABILITY_LINES if n != DEPOSITS_OTHER]
    recon = reconcile_reserve_identity(FIXTURE_ROW, nonreserve_lines=dropped)
    assert recon["nonreserve_total"] == 3_506_000
    assert recon["reserves_implied"] == 3_120_000
    assert recon["residual"] == -120_000
    assert recon["reconciles"] is False
    assert recon["missing"] == []
    assert recon["duplicate_lines"] == []
    assert recon["undeclared_lines"] == []


def test_c16_double_counted_liability_prints_nonzero_residual():
    doubled = list(H41_NONRESERVE_LIABILITY_LINES) + [H41_TGA_LINE]
    recon = reconcile_reserve_identity(FIXTURE_ROW, nonreserve_lines=doubled)
    assert recon["residual"] == 800_000
    assert recon["reconciles"] is False
    assert recon["duplicate_lines"] == [H41_TGA_LINE]
    assert recon["reserves_implied"] == 2_200_000
    # a duplicated name is summed twice, never silently de-duplicated
    assert recon["lines_used"].count(H41_TGA_LINE) == 2


def test_c16_component_partition_names_each_line_once():
    partition_lines = [line for lines in COMPONENT_LINES.values() for line in lines]
    expected = set(H41_NONRESERVE_LIABILITY_LINES) | {H41_ASSETS_LINE, H41_CAPITAL_LINE}
    assert set(partition_lines) == expected
    assert len(partition_lines) == len(set(partition_lines))  # no line twice
    for lines in COMPONENT_LINES.values():
        assert H41_RESERVES_LINE not in lines  # reserves line in no component
    assert set(COMPONENT_SIGN) == set(COMPONENT_LINES)
    assert COMPONENT_SIGN["total_assets"] == 1
    assert all(sign == -1 for key, sign in COMPONENT_SIGN.items() if key != "total_assets")


def test_c16_missing_line_is_unavailable_never_zero():
    row = dict(FIXTURE_ROW)
    row[DEFERRED_CASH] = None
    recon = reconcile_reserve_identity(row)
    assert recon["missing"] == [DEFERRED_CASH]
    assert recon["reserves_implied"] is None
    assert recon["residual"] is None
    assert recon["reconciles"] is False
    assert recon["nonreserve_total"] is None
    outlook = compose_component_paths(
        make_anchor(row), make_announcements(), make_assumptions(), as_of=AS_OF
    )
    assert outlook["reserves"]["estimate_type"] == "unavailable"
    assert outlook["reserves"]["unavailable_reason"] == "anchor_incomplete"
    assert outlook["reserves"]["points"] == []
    other = outlook["paths"]["other_nonreserve_and_capital"]
    assert other["estimate_type"] == "unavailable"
    assert other["unavailable_reason"] == "anchor_incomplete"
    assert other["anchor_level"] is None
    assert other["points"] == []
    assert 0 not in [p["level"] for p in outlook["paths"]["treasury_general_account"]["points"]]


# ---------------------------------------------------------------------------
# C15 -- point-in-time announcement admissibility
# ---------------------------------------------------------------------------


def test_c15_future_published_announcement_excluded_and_recorded():
    announcements = make_announcements()
    before = copy.deepcopy(announcements)
    adm = admissible_announcements(announcements, as_of=AS_OF)
    assert announcements == before  # inputs are never mutated
    assert [a["id"] for a in adm["admitted"]] == ["tga-qra-2026q3"]
    excluded = {entry["id"]: entry for entry in adm["excluded"]}
    assert set(excluded) == {
        "tga-qra-2026q3-rev",
        "financing-shift-2026-09-15",
        "same-day-after-cutoff",
    }
    for entry in excluded.values():
        assert entry["reason"] == "published_after_as_of"
        assert entry["cutoff_utc"] == CUTOFF_UTC
    # a date bound becomes available only after that local day elapses (T05)
    assert excluded["tga-qra-2026q3-rev"]["published_at_utc"] == "2026-09-11T04:00:00+00:00"
    assert excluded["financing-shift-2026-09-15"]["published_at_utc"] == "2026-09-16T04:00:00+00:00"


def test_c15_announcement_published_on_as_of_date_after_cutoff_excluded():
    a4 = make_announcements()[3]
    adm = admissible_announcements([a4], as_of=AS_OF)
    assert adm["admitted"] == []
    assert len(adm["excluded"]) == 1
    entry = adm["excluded"][0]
    assert entry["id"] == "same-day-after-cutoff"
    assert entry["reason"] == "published_after_as_of"
    assert entry["published_at_utc"] == "2026-09-04T12:30:00+00:00"
    assert entry["cutoff_utc"] == CUTOFF_UTC  # a date as_of means local day START


def test_c15_future_revision_cannot_replace_admitted_schedule():
    outlook = make_outlook()
    assert outlook["admitted_announcement_ids"] == ["tga-qra-2026q3"]
    tga = outlook["paths"]["treasury_general_account"]
    assert tga["estimate_type"] == "announced_scenario"
    assert [p["level"] for p in tga["points"]] == [850_000, 850_000, 850_000]
    assert tga["support"]["announcement_ids"] == ["tga-qra-2026q3"]
    assert tga["support"]["ignored_assumption_ids"] == ["hold-tga"]
    excluded = {e["id"]: e["reason"] for e in outlook["excluded_announcements"]}
    assert excluded["tga-qra-2026q3-rev"] == "published_after_as_of"

    # positive control: as_of one week later the revision is admissible and,
    # having the later availability start, applies after (so on top of) A4.
    later = compose_component_paths(
        make_anchor(), make_announcements(), make_assumptions(), as_of=date(2026, 9, 11)
    )
    excluded_later = {e["id"]: e["reason"] for e in later["excluded_announcements"]}
    assert excluded_later["tga-qra-2026q3"] == "superseded_by:tga-qra-2026q3-rev"
    assert "tga-qra-2026q3-rev" in later["admitted_announcement_ids"]
    tga_later = later["paths"]["treasury_general_account"]
    assert tga_later["estimate_type"] == "announced_scenario"
    assert tga_later["points"][0]["target_date"] == "2026-09-30"
    assert tga_later["points"][0]["level"] == 900_000


def test_c15_post_as_of_financing_source_change_cannot_alter_any_path():
    with_a3 = make_outlook()
    without_a3 = compose_component_paths(
        make_anchor(),
        [a for a in make_announcements() if a["id"] != "financing-shift-2026-09-15"],
        make_assumptions(),
        as_of=AS_OF,
    )
    assert with_a3["paths"] == without_a3["paths"]
    assert with_a3["reserves"] == without_a3["reserves"]
    # the post-as-of delta (-200_000) never reaches any reserves number
    assert -200_000 not in set(_walk_numbers(with_a3["reserves"]))


def test_c15_anchor_published_after_as_of_makes_paths_unavailable():
    outlook = compose_component_paths(
        make_anchor(), make_announcements(), make_assumptions(), as_of=date(2026, 9, 3)
    )
    assert outlook["anchor"] is None
    assert outlook["anchor_lineage"] == {
        "observed_on": "2026-09-02",
        "published_at_utc": "2026-09-03T20:30:00+00:00",
        "admissible": False,
    }
    for path in outlook["paths"].values():
        assert path["estimate_type"] == "unavailable"
        assert path["unavailable_reason"] == "anchor_published_after_as_of"
        assert path["points"] == []
        assert path["anchor_level"] is None
    assert outlook["reserves"]["unavailable_reason"] == "anchor_published_after_as_of"
    assert outlook["reserves"]["points"] == []
    assert outlook["reserves"]["anchor_residual"] is None
    numbers = set(_walk_numbers(outlook))
    assert 3_000_000 not in numbers  # no anchor number anywhere in the output
    assert 6_626_000 not in numbers


# ---------------------------------------------------------------------------
# estimate types, output-key law, module text law
# ---------------------------------------------------------------------------


def test_estimate_types_are_three_allowed_values_never_statistical_forecast():
    outlook = make_outlook()
    assert ESTIMATE_TYPES == ("announced_scenario", "conditional_accounting", "unavailable")
    seen = {p["estimate_type"] for p in outlook["paths"].values()}
    seen |= {outlook["reserves"]["estimate_type"]}
    seen |= {outlook["statistical_residual"]["estimate_type"]}
    assert seen == {"announced_scenario", "conditional_accounting", "unavailable"}
    assert "statistical_forecast" not in seen
    assert outlook["statistical_residual"]["unavailable_reason"] == "no_statistical_model_until_T09"
    assert outlook["paths"]["treasury_general_account"]["estimate_type"] == "announced_scenario"
    assert outlook["paths"]["total_assets"]["estimate_type"] == "conditional_accounting"
    assert outlook["reserves"]["estimate_type"] == "conditional_accounting"


def test_no_forbidden_output_keys():
    outlook = make_outlook()
    baseline = baseline_comparison(
        outlook, realized_reserves={date(2026, 9, 30): 2_960_000}
    )
    snap = snapshot(Path("/nonexistent-glt-t08-root"), as_of=AS_OF)
    for document in (outlook, baseline, snap):
        for key in _walk_keys(document):
            lowered = str(key).lower()
            for fragment in FORBIDDEN_KEY_FRAGMENTS:
                assert fragment not in lowered, (fragment, key)


def test_module_text_has_no_forbidden_fragments():
    source = Path(outlook_module.__file__).read_text(encoding="utf-8").lower()
    for fragment in MODULE_FORBIDDEN_FRAGMENTS:
        assert fragment not in source, fragment


def test_persistence_and_announced_only_differ_only_where_admissible_announcement_exists():
    outlook = make_outlook(horizons_weeks=(1, 4))
    rows = {r["horizon_weeks"]: r for r in baseline_comparison(outlook)["rows"]}
    assert rows[1]["target_date"] == "2026-09-09"  # before the 2026-09-30 schedule
    assert rows[1]["persistence_level"] == rows[1]["announced_only_level"] == 3_000_000
    assert rows[1]["difference"] == 0
    assert rows[4]["difference"] == -50_000
    assert rows[4]["announced_only_level"] == 2_950_000
    tga_points = {
        p["horizon_weeks"]: p
        for p in outlook["paths"]["treasury_general_account"]["points"]
    }
    assert tga_points[1]["level"] == 800_000  # announced but not yet effective
    assert tga_points[4]["level"] == 850_000


def test_baseline_comparison_plain_numbers_on_fixture():
    outlook = make_outlook()
    before = copy.deepcopy(outlook)
    realized = {date(2026, 9, 30): 2_960_000}
    result = baseline_comparison(outlook, realized_reserves=realized)
    assert outlook == before  # realized history never changes any path
    rows = result["rows"]
    assert [r["horizon_weeks"] for r in rows] == [4, 8, 13]
    assert [r["target_date"] for r in rows] == ["2026-09-30", "2026-10-28", "2026-12-02"]
    for row in rows:
        assert row["persistence_level"] == 3_000_000
        assert row["announced_only_level"] == 2_950_000
        assert row["difference"] == -50_000
    assert rows[0]["realized_level"] == 2_960_000
    assert rows[0]["persistence_miss"] == -40_000
    assert rows[0]["announced_only_miss"] == 10_000
    for row in rows[1:]:
        assert row["realized_level"] is None
        assert row["persistence_miss"] is None
        assert row["announced_only_miss"] is None
    assert result["unavailable_reason"] is None
    assert result["schema"] == BASELINE_SCHEMA
    assert result["validated"] is False

    reserves = outlook["reserves"]
    assert [p["level"] for p in reserves["points"]] == [2_930_000, 2_910_000, 2_885_000]
    assert [p["announced_change"] for p in reserves["points"]] == [-50_000] * 3
    assert [p["assumed_change"] for p in reserves["points"]] == [-20_000, -40_000, -65_000]
    assert all(p["statistical_residual"] is None for p in reserves["points"])
    assert reserves["anchor_residual"] == 0
    tga = outlook["paths"]["treasury_general_account"]
    assert [p["level"] for p in tga["points"]] == [850_000, 850_000, 850_000]
    total_assets = outlook["paths"]["total_assets"]
    assert [p["level"] for p in total_assets["points"]] == [6_606_000, 6_586_000, 6_561_000]
    assert total_assets["support"]["assumption_id"] == "qt-runoff-assumption"
    assert outlook["paths"]["other_nonreserve_and_capital"]["anchor_level"] == -4_000


def test_snapshot_empty_root_names_missing_inputs(tmp_path):
    snap = snapshot(tmp_path, as_of=AS_OF)
    assert snap["degraded"] is True
    assert snap["validated"] is False
    assert snap["authority"] == "measurement_only"
    assert snap["headline"]["state"] == "data_degraded"
    assert "no paths computed" in snap["headline"]["summary"]
    assert snap["paths"] == {}
    assert snap["as_of"] == "2026-09-04"
    assert snap["as_of_cutoff_utc"] == CUTOFF_UTC
    for relative in SNAPSHOT_OWNER_INPUTS:
        assert f"{relative} not found" in snap["gaps"]
    loader_gaps = [g for g in snap["gaps"] if g.startswith("no owner loader")]
    assert len(loader_gaps) == 11  # ten nonreserve lines + capital, TGA exempt
    assert f"no owner loader for H.4.1 line: {H41_TGA_LINE}" not in snap["gaps"]
    assert f"no owner loader for H.4.1 line: {H41_CAPITAL_LINE}" in snap["gaps"]
    assert len(snap["gaps"]) == 15


def test_module_constants_measurement_only():
    assert VALIDATED is False
    assert AUTHORITY == "measurement_only"
    assert CLAIM_LEVEL == "conditional_accounting_display_tier"
    assert SCHEMA == "glt_component_outlook_v1"
    assert BASELINE_SCHEMA == "glt_component_outlook_baselines_v1"
    assert DEFAULT_HORIZONS_WEEKS == (4, 8, 13)
    assert DEFAULT_DECISION_TZ == DEFAULT_PUBLICATION_TZ == "America/New_York"
    assert H41_BASIS == (
        "H.4.1 Table 5 Consolidated Statement of Condition of All Federal Reserve Banks"
    )
    assert H41_ASSETS_LINE == "Total assets"
    assert H41_RESERVES_LINE == "Reserve balances with Federal Reserve Banks"
    assert H41_CAPITAL_LINE == "Total capital"
    assert H41_TGA_LINE == TGA_LINE
    assert H41_RRP_FOREIGN_LINE == RRP_FOREIGN
    assert H41_RRP_OTHERS_LINE == RRP_OTHERS
    assert H41_NONRESERVE_LIABILITY_LINES[0] == FR_NOTES
    assert SNAPSHOT_OWNER_INPUTS == (
        "data/fred/WALCL.parquet",
        "data/fred/RRPONTSYD.parquet",
        "data/treasury/tga.parquet",
        "data/fred/WRESBAL.parquet",
    )
    expected_all = {
        "VALIDATED", "AUTHORITY", "CLAIM_LEVEL", "SCHEMA", "BASELINE_SCHEMA",
        "ESTIMATE_TYPES", "DEFAULT_HORIZONS_WEEKS", "DEFAULT_DECISION_TZ",
        "DEFAULT_PUBLICATION_TZ", "H41_BASIS", "H41_ASSETS_LINE",
        "H41_RESERVES_LINE", "H41_CAPITAL_LINE", "H41_TGA_LINE",
        "H41_RRP_FOREIGN_LINE", "H41_RRP_OTHERS_LINE", "H41_FR_NOTES_LINE",
        "H41_NONRESERVE_LIABILITY_LINES", "COMPONENT_LINES", "COMPONENT_SIGN",
        "SNAPSHOT_OWNER_INPUTS", "reconcile_reserve_identity",
        "admissible_announcements", "compose_component_paths",
        "baseline_comparison", "snapshot",
    }
    assert set(outlook_module.__all__) == expected_all
    assert len(outlook_module.__all__) == 26


def test_bool_rejected():
    for line in (H41_ASSETS_LINE, H41_RESERVES_LINE, H41_CAPITAL_LINE, DEPOSITS_OTHER):
        row = dict(FIXTURE_ROW)
        row[line] = True
        with pytest.raises(TypeError):
            reconcile_reserve_identity(row)

    def assumptions_with(replacement):
        return [
            a for a in make_assumptions() if a["component"] != replacement["component"]
        ] + [replacement]

    bool_notes = {
        "id": "bool-notes",
        "component": "federal_reserve_notes",
        "kind": "weekly_delta",
        "value": True,
    }
    with pytest.raises(TypeError):
        compose_component_paths(
            make_anchor(), make_announcements(), assumptions_with(bool_notes), as_of=AS_OF
        )
    null_notes = {
        "id": "null-notes",
        "component": "federal_reserve_notes",
        "kind": "weekly_delta",
        "value": None,
    }
    with pytest.raises(ValueError):
        compose_component_paths(
            make_anchor(), make_announcements(), assumptions_with(null_notes), as_of=AS_OF
        )
    with pytest.raises(ValueError):
        compose_component_paths(
            make_anchor(), make_announcements(), make_assumptions(),
            as_of=AS_OF, horizons_weeks=(4, True),
        )
    with pytest.raises(ValueError):
        compose_component_paths(
            make_anchor(), make_announcements(), make_assumptions(),
            as_of=AS_OF, horizons_weeks=(),
        )
    with pytest.raises(ValueError):
        compose_component_paths(
            make_anchor(), make_announcements(), make_assumptions(),
            as_of=AS_OF, horizons_weeks=(8, 4),
        )
    duplicate_tga = [
        {
            "id": "second-tga-assumption",
            "component": "treasury_general_account",
            "kind": "hold_level",
        }
    ]
    with pytest.raises(ValueError):
        compose_component_paths(
            make_anchor(), make_announcements(), make_assumptions() + duplicate_tga,
            as_of=AS_OF,
        )
