"""sic_industry classification-axis reader (WS:GMI-THEME-GRAPH Taxonomy V2, lane L05).

Wraps the profile artifact written by ``collectors/equity_profile.py``
(``data/profile/profiles.parquet``, column ``sic_description``). SIC is the
SEC industry code text, not a GICS sub-industry. Display/context tier only:
one AxisCell v1 per call, every return passing ``cell.validate_cell``.
"""
from __future__ import annotations

import datetime
from pathlib import Path

import pandas as pd

from engine.classification_axes import cell, sic_industry

AS_OF = "2026-10-11"


def _profiles() -> pd.DataFrame:
    rows = [
        ("AAPL", "Apple Inc.", "Electronic Computers", pd.Timestamp("2026-09-30")),
        (
            "BRK-B",
            "Berkshire Hathaway Inc.",
            "Fire, Marine & Casualty Insurance",
            pd.Timestamp("2026-08-15"),
        ),
        # 365 days old exactly at AS_OF -> available; LATE is 366 -> stale.
        ("EDGE", "Edge Corp", "Edge Industry", pd.Timestamp("2025-10-11")),
        ("LATE", "Late Corp", "Late Industry", pd.Timestamp("2025-10-10")),
        ("MISS", "Missing Corp", None, pd.Timestamp("2026-09-01")),
        ("BLANK", "Blank Corp", "   ", pd.Timestamp("2026-09-01")),
        ("FUTURE", "Future Corp", "Time Travel Equipment", pd.Timestamp("2026-10-12")),
        ("BADASOF", "Bad Corp", "Unknown Industry", "not-a-date"),
    ]
    frame = pd.DataFrame(rows, columns=["ticker", "name", "sic_description", "as_of"])
    return frame.set_index("ticker")


def test_constants_and_single_public_reader():
    assert sic_industry.AXIS == "sic_industry"
    assert sic_industry.SOURCE_OWNER == "collectors/equity_profile.py"
    assert sic_industry.SOURCE_ARTIFACT == "data/profile/profiles.parquet"
    assert sic_industry.MAX_AGE_DAYS == 365
    assert sic_industry.SUBJECT_KINDS == ("co",)
    assert sic_industry.RIGHTS_CONTEXT == {
        "license_class": "direct_display_ok",
        "basis": (
            "SEC EDGAR submissions sicDescription (US government public-domain "
            "content) via collectors/equity_profile.py; keyless_public"
        ),
    }
    public = [
        name
        for name in dir(sic_industry)
        if callable(getattr(sic_industry, name))
        and not name.startswith("_")
        and getattr(getattr(sic_industry, name), "__module__", "") == sic_industry.__name__
    ]
    assert public == ["read_sic_industry"]


def test_available_us_row_is_exact():
    got = sic_industry.read_sic_industry("co:us:AAPL", as_of=AS_OF, profiles=_profiles())
    assert cell.validate_cell(got) == []
    assert got == {
        "schema_version": "axis_cell.v1",
        "axis": "sic_industry",
        "subject_id": "co:us:AAPL",
        "status": "available",
        "reason_code": None,
        "value": {"sic_description": "Electronic Computers"},
        "unit": None,
        "observed_at": "2026-09-30",
        "effective_at": None,
        "as_of": AS_OF,
        "freshness": {"age_days": 11, "max_age_days": 365},
        "quality": "display_only",
        "labels": ["source_local"],
        "source": {
            "owner": "collectors/equity_profile.py",
            "artifact": "data/profile/profiles.parquet",
            "field": "sic_description",
        },
        "provenance": [],
        "rights_context": sic_industry.RIGHTS_CONTEXT,
    }


def test_dot_dash_alias_resolves_with_provenance():
    got = sic_industry.read_sic_industry(
        "co:us:BRK.B", as_of="2026-08-20", profiles=_profiles()
    )
    assert cell.validate_cell(got) == []
    assert got["status"] == "available"
    assert got["value"] == {"sic_description": "Fire, Marine & Casualty Insurance"}
    assert got["observed_at"] == "2026-08-15"
    assert got["freshness"] == {"age_days": 5, "max_age_days": 365}
    assert got["provenance"] == ["symbol_alias:BRK-B"]


def test_stale_at_366_days_keeps_value_and_365_is_available():
    edge = sic_industry.read_sic_industry("co:us:EDGE", as_of=AS_OF, profiles=_profiles())
    assert cell.validate_cell(edge) == []
    assert edge["status"] == "available"
    assert edge["freshness"] == {"age_days": 365, "max_age_days": 365}

    late = sic_industry.read_sic_industry("co:us:LATE", as_of=AS_OF, profiles=_profiles())
    assert cell.validate_cell(late) == []
    age = (datetime.date(2026, 10, 11) - datetime.date(2025, 10, 10)).days
    assert age == 366
    assert late["status"] == "stale"
    assert late["reason_code"] == "owner_stale"
    assert late["value"] == {"sic_description": "Late Industry"}
    assert late["observed_at"] == "2025-10-10"
    assert late["freshness"] == {"age_days": 366, "max_age_days": 365}
    assert late["labels"] == ["source_local"]


def test_observed_after_as_of_is_history_not_supported():
    got = sic_industry.read_sic_industry("co:us:FUTURE", as_of=AS_OF, profiles=_profiles())
    assert cell.validate_cell(got) == []
    assert got["status"] == "unknown"
    assert got["reason_code"] == "history_not_supported"
    assert got["value"] is None
    assert got["freshness"] is None


@pytest.mark.parametrize("ticker", ["BLANK", "MISS"])
def test_blank_and_null_sic_are_value_missing(ticker):
    got = sic_industry.read_sic_industry(f"co:us:{ticker}", as_of=AS_OF, profiles=_profiles())
    assert cell.validate_cell(got) == []
    assert got["status"] == "unknown"
    assert got["reason_code"] == "value_missing"
    assert got["value"] is None


def test_ticker_absent_from_artifact_is_value_missing():
    got = sic_industry.read_sic_industry("co:us:NOPE", as_of=AS_OF, profiles=_profiles())
    assert cell.validate_cell(got) == []
    assert got["status"] == "unknown"
    assert got["reason_code"] == "value_missing"
    assert got["value"] is None


def test_non_us_market_and_non_company_kinds_are_not_applicable():
    hk = sic_industry.read_sic_industry("co:hk:0700", as_of=AS_OF, profiles=_profiles())
    assert cell.validate_cell(hk) == []
    assert hk["status"] == "not_applicable"
    assert hk["reason_code"] == "not_applicable"
    assert hk["provenance"] == ["market:hk"]
    assert hk["value"] is None

    theme = sic_industry.read_sic_industry("theme:ai_compute", as_of=AS_OF, profiles=_profiles())
    assert cell.validate_cell(theme) == []
    assert theme["status"] == "not_applicable"
    assert theme["reason_code"] == "not_applicable"
    assert theme["value"] is None


def test_identity_epoch_is_not_attributable():
    got = sic_industry.read_sic_industry("co:us:AAPL#2", as_of=AS_OF, profiles=_profiles())
    assert cell.validate_cell(got) == []
    assert got["status"] == "unknown"
    assert got["reason_code"] == "value_missing"
    assert got["provenance"] == ["identity_epoch_not_supported"]
    assert got["value"] is None


def test_default_path_missing_corrupt_and_valid(tmp_path):
    root = Path(tmp_path)
    absent = sic_industry.read_sic_industry("co:us:AAPL", as_of=AS_OF, root=root)
    assert cell.validate_cell(absent) == []
    assert absent["status"] == "unavailable"
    assert absent["reason_code"] == "owner_missing"

    profile_dir = root / "data" / "profile"
    profile_dir.mkdir(parents=True)
    parquet_path = profile_dir / "profiles.parquet"
    parquet_path.write_bytes(b"this is not a parquet file")
    corrupt = sic_industry.read_sic_industry("co:us:AAPL", as_of=AS_OF, root=root)
    assert cell.validate_cell(corrupt) == []
    assert corrupt["status"] == "unavailable"
    assert corrupt["reason_code"] == "owner_degraded"
    assert corrupt["provenance"][0].startswith("read_error:")

    _profiles().to_parquet(parquet_path)
    good = sic_industry.read_sic_industry("co:us:AAPL", as_of=AS_OF, root=root)
    assert cell.validate_cell(good) == []
    assert good["status"] == "available"
    assert good["value"] == {"sic_description": "Electronic Computers"}


def test_ticker_column_is_accepted_instead_of_the_index():
    frame = _profiles().reset_index()
    assert "ticker" in frame.columns
    got = sic_industry.read_sic_industry("co:us:AAPL", as_of=AS_OF, profiles=frame)
    assert cell.validate_cell(got) == []
    assert got["status"] == "available"
    assert got["value"] == {"sic_description": "Electronic Computers"}


def test_two_calls_are_byte_identical():
    first = sic_industry.read_sic_industry("co:us:AAPL", as_of=AS_OF, profiles=_profiles())
    second = sic_industry.read_sic_industry("co:us:AAPL", as_of=AS_OF, profiles=_profiles())
    assert cell.to_json(first) == cell.to_json(second)


def test_module_source_text_guard():
    text = Path(sic_industry.__file__).read_text(encoding="utf-8")
    for banned in (
        "engine.intelligence_workspace",
        "engine.market_ontology",
        "engine.company_intelligence",
        "scripts.",
        "datetime.now",
        "date.today",
        "requests",
    ):
        assert banned not in text, banned
