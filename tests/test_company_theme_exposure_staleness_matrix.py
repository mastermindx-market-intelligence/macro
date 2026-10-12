"""Staleness and coverage edges for company theme exposure.

Pins ``views.py`` and ``health.py`` at the boundaries the Terminal theme card
and the integrated-answer company_theme_exposure leg rely on. Fixtures are
in-test JSON and tmp directories only.

Observed age rule (``THEME_STATE_MAX_AGE_DAYS`` is 5): a stamp is fresh when
``(as_of - stamp).days > 5`` is false, so age 5 is fresh and age 6 is stale.
Membership is the half-open interval ``[added, removed)``.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta

import pytest

from engine.company_theme_exposure.contracts import ContractError, canonical_json_sha256
from engine.company_theme_exposure.health import validate_generation
from engine.company_theme_exposure.views import (
    THEME_STATE_MAX_AGE_DAYS,
    _active_membership,
    _as_date,
    _canonical_theme_ids,
    _coverage,
    _crosswalk_index,
    _theme_state_receipt,
    build_bundle,
    derive_generation_id,
    write_generation,
)
from tests.test_company_theme_exposure import _company_tree


RUN_AS_OF = date(2026, 2, 7)
CANONICAL = {"canonical_theme"}
THEME_BY_BASKET = {
    "mapped": {"theme_id": "canonical_theme"},
    "other": {"theme_id": "other_theme"},
}


def _theme_state(as_of: object, **extra: object) -> dict:
    payload = {
        "schema": "neuralweb.theme_state.v1",
        "as_of": as_of,
        "stale_legs": [],
        "n_themes": 1,
        "themes": [{"theme_id": "canonical_theme"}],
        "authority": {"is_context_only": True},
    }
    payload.update(extra)
    return payload


def _receipt(payload, *, as_of: date = RUN_AS_OF):
    return _theme_state_receipt(payload, as_of=as_of, canonical_theme_ids=set(CANONICAL))


@pytest.mark.parametrize(
    "age_days,status,warnings",
    [
        pytest.param(0, "fresh", [], id="age-0-fresh"),
        pytest.param(4, "fresh", [], id="age-4-fresh"),
        pytest.param(5, "fresh", [], id="age-5-fresh-max-age-inclusive"),
        pytest.param(6, "stale", ["theme_state_stale"], id="age-6-stale"),
    ],
)
def test_theme_state_receipt_age_against_max_age(age_days, status, warnings) -> None:
    """Age 5 stays fresh because the gate is ``days > THEME_STATE_MAX_AGE_DAYS``."""
    assert THEME_STATE_MAX_AGE_DAYS == 5
    stamp = RUN_AS_OF - timedelta(days=age_days)
    assert (RUN_AS_OF - stamp).days == age_days
    payload = _theme_state(stamp.isoformat())
    receipt, got = _receipt(payload)
    assert got == warnings
    assert receipt == {
        "status": status,
        "as_of": stamp.isoformat(),
        "sha256": canonical_json_sha256(payload),
    }


def test_theme_state_receipt_stale_legs_marks_age_zero_stale() -> None:
    payload = _theme_state(RUN_AS_OF.isoformat(), stale_legs=["prices"])
    receipt, warnings = _receipt(payload)
    assert warnings == ["theme_state_stale"]
    assert receipt == {
        "status": "stale",
        "as_of": "2026-02-07",
        "sha256": canonical_json_sha256(payload),
    }


def test_theme_state_receipt_missing_date_is_invalid() -> None:
    payload = _theme_state(RUN_AS_OF.isoformat())
    del payload["as_of"]
    receipt, warnings = _receipt(payload)
    assert warnings == ["theme_state_invalid"]
    assert receipt == {
        "status": "invalid",
        "as_of": None,
        "sha256": canonical_json_sha256(payload),
    }


def test_theme_state_receipt_missing_payload_is_missing() -> None:
    receipt, warnings = _receipt(None)
    assert warnings == ["theme_state_missing"]
    assert receipt == {"status": "missing", "as_of": None, "sha256": None}


def test_theme_state_receipt_unparseable_date_is_invalid() -> None:
    payload = _theme_state("not-a-date")
    receipt, warnings = _receipt(payload)
    assert warnings == ["theme_state_invalid"]
    assert receipt == {
        "status": "invalid",
        "as_of": None,
        "sha256": canonical_json_sha256(payload),
    }


def test_theme_state_receipt_future_date_is_invalid() -> None:
    future = (RUN_AS_OF + timedelta(days=1)).isoformat()
    payload = _theme_state(future)
    receipt, warnings = _receipt(payload)
    assert warnings == ["theme_state_invalid"]
    assert receipt == {
        "status": "invalid",
        "as_of": future,
        "sha256": canonical_json_sha256(payload),
    }


def test_boolean_n_themes_is_not_fresh() -> None:
    payload = _theme_state(RUN_AS_OF.isoformat(), n_themes=True)
    receipt, warnings = _receipt(payload)
    assert receipt["status"] != "fresh"
    assert warnings


def test_junk_suffix_date_is_not_fresh() -> None:
    payload = _theme_state("2026-02-07garbage")
    receipt, warnings = _receipt(payload)
    assert receipt["status"] != "fresh"
    assert warnings


@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param(None, None, id="none"),
        pytest.param("2026-02-07", date(2026, 2, 7), id="plain-date"),
        pytest.param("2026-02-07T14:30:00Z", date(2026, 2, 7), id="utc-datetime"),
        pytest.param("2026-02-07T14:30:00+08:00", date(2026, 2, 7), id="offset-datetime"),
        pytest.param(date(2026, 2, 7), date(2026, 2, 7), id="date-object"),
        pytest.param(datetime(2026, 2, 7, 14, 30), date(2026, 2, 7), id="datetime-object"),
        pytest.param("2026-02-07garbage", None, id="junk-suffix"),
        pytest.param("2026-02-07 extra", None, id="space-suffix"),
        pytest.param("20260207", None, id="basic-format-date"),
        pytest.param(True, None, id="bool"),
        pytest.param("", None, id="empty-string"),
    ],
)
def test_as_date_accepts_exact_iso_only(value, expected) -> None:
    """``_as_date`` accepts exact days and real ISO datetimes, refuses the rest.

    Pins the local parser that replaced the shared ``parse_date`` delegation:
    a truncated ``text[:10]`` prefix (junk suffix) and the basic/week forms
    ``fromisoformat`` also accepts on 3.11+ must stay ``None`` — a stamp that
    only looks like a date must never reach the freshness gate.
    """
    got = _as_date(value)
    assert got == expected
    assert (got is None) == (expected is None)


def _closed_membership() -> dict:
    return {
        "baskets": {
            "mapped": {
                "members": [{"ticker": "AAPL", "added": "2026-01-10", "removed": "2026-01-20"}],
            },
        },
    }


@pytest.mark.parametrize(
    "as_of,expected",
    [
        pytest.param(date(2026, 1, 9), {}, id="before-added"),
        pytest.param(date(2026, 1, 10), {"AAPL": {"mapped"}}, id="at-added"),
        pytest.param(date(2026, 1, 15), {"AAPL": {"mapped"}}, id="inside-half-open"),
        pytest.param(date(2026, 1, 20), {}, id="at-removed"),
        pytest.param(date(2026, 1, 21), {}, id="after-removed"),
    ],
)
def test_active_membership_half_open_interval(as_of, expected) -> None:
    """Active on ``[added, removed)``: the removal day itself is already out."""
    assert _active_membership(_closed_membership(), as_of=as_of) == expected


@pytest.mark.parametrize(
    "as_of,expected",
    [
        pytest.param(date(2026, 1, 9), {}, id="open-before-added"),
        pytest.param(date(2026, 1, 10), {"AAPL": {"mapped"}}, id="open-at-added"),
        pytest.param(date(2026, 6, 1), {"AAPL": {"mapped"}}, id="open-after-added"),
    ],
)
def test_active_membership_open_ended_interval(as_of, expected) -> None:
    membership = {
        "baskets": {
            "mapped": {"members": [{"ticker": "AAPL", "added": "2026-01-10", "removed": None}]},
        },
    }
    assert _active_membership(membership, as_of=as_of) == expected


def test_active_membership_zero_length_interval_is_never_active() -> None:
    membership = {
        "baskets": {
            "mapped": {"members": [{"ticker": "AAPL", "added": "2026-01-10", "removed": "2026-01-10"}]},
        },
    }
    for as_of in (date(2026, 1, 9), date(2026, 1, 10), date(2026, 1, 11)):
        assert _active_membership(membership, as_of=as_of) == {}


def _theme_row(theme_id, baskets, *, foresight_id=None) -> dict:
    return {
        "id": theme_id,
        "foresight_id": theme_id if foresight_id is None else foresight_id,
        "name_en": "Canonical Theme",
        "name_zh": "规范主题",
        "basket_ids": list(baskets),
    }


def _baskets(*basket_ids: str) -> dict:
    return {"baskets": {basket_id: {"members": []} for basket_id in basket_ids}}


def test_crosswalk_accounted_baskets_match_canonical_theme_ids() -> None:
    crosswalk = {
        "version": 1,
        "themes": [_theme_row("canonical_theme", ["mapped"])],
        "unmapped_baskets": [{"id": "aside", "reason": "outside the canonical registry"}],
    }
    index = _crosswalk_index(crosswalk, _baskets("mapped", "aside"))
    assert set(index) == {"mapped"}
    assert index["mapped"]["theme_id"] == "canonical_theme"
    assert _canonical_theme_ids(crosswalk) == {"canonical_theme"}


def test_crosswalk_basket_with_no_row_is_unaccounted() -> None:
    crosswalk = {
        "version": 1,
        "themes": [_theme_row("canonical_theme", ["mapped"])],
        "unmapped_baskets": [],
    }
    with pytest.raises(ContractError, match=r"does not account for baskets: \['orphan'\]"):
        _crosswalk_index(crosswalk, _baskets("mapped", "orphan"))
    assert _canonical_theme_ids(crosswalk) == {"canonical_theme"}


@pytest.mark.parametrize(
    "theme_id,foresight_id,canonical",
    [
        pytest.param("canonical_theme", "other_theme", {"canonical_theme"}, id="foresight-id-disagrees"),
        pytest.param(123, 123, {"123"}, id="non-string-theme-id"),
        pytest.param("", "", {""}, id="empty-theme-id"),
    ],
)
def test_crosswalk_row_with_unknown_theme_id_is_rejected(theme_id, foresight_id, canonical) -> None:
    crosswalk = {
        "version": 1,
        "themes": [_theme_row(theme_id, ["mapped"], foresight_id=foresight_id)],
        "unmapped_baskets": [],
    }
    with pytest.raises(ContractError, match="ID invalid or duplicate"):
        _crosswalk_index(crosswalk, _baskets("mapped"))
    assert _canonical_theme_ids(crosswalk) == canonical


def test_crosswalk_duplicate_basket_mapping_is_rejected() -> None:
    crosswalk = {
        "version": 1,
        "themes": [
            _theme_row("theme_a", ["mapped"]),
            _theme_row("theme_b", ["mapped"]),
        ],
        "unmapped_baskets": [],
    }
    with pytest.raises(ContractError, match="mapped twice: mapped"):
        _crosswalk_index(crosswalk, _baskets("mapped"))
    assert _canonical_theme_ids(crosswalk) == {"theme_a", "theme_b"}


def test_coverage_zero_active_returns_no_active_membership() -> None:
    assert _coverage(set(), THEME_BY_BASKET) == {
        "status": "no_active_membership",
        "active_basket_count": 0,
        "mapped_basket_count": 0,
        "unmapped_basket_count": 0,
    }


def test_coverage_all_mapped_returns_mapped() -> None:
    assert _coverage({"mapped", "other"}, THEME_BY_BASKET) == {
        "status": "mapped",
        "active_basket_count": 2,
        "mapped_basket_count": 2,
        "unmapped_basket_count": 0,
    }


def test_coverage_partial_returns_mixed() -> None:
    assert _coverage({"mapped", "orphan"}, THEME_BY_BASKET) == {
        "status": "mixed",
        "active_basket_count": 2,
        "mapped_basket_count": 1,
        "unmapped_basket_count": 1,
    }


def test_coverage_unmapped_only_returns_unmapped_only() -> None:
    assert _coverage({"orphan"}, THEME_BY_BASKET) == {
        "status": "unmapped_only",
        "active_basket_count": 1,
        "mapped_basket_count": 0,
        "unmapped_basket_count": 1,
    }


def _materialize(tmp_path, *, state_as_of: str = "2026-02-02", expect_status: str = "ready"):
    contexts, company_manifest = _company_tree(tmp_path / "company")
    membership = {
        "baskets": {
            "mapped": {"members": [
                {"ticker": "AAPL", "added": "2025-01-01", "removed": None},
                {"ticker": "NVDA", "added": "2025-01-01", "removed": "2026-01-01"},
            ]},
        },
    }
    crosswalk = {
        "version": 1,
        "themes": [_theme_row("canonical_theme", ["mapped"])],
        "unmapped_baskets": [],
    }
    theme_state = _theme_state(state_as_of)
    exposures, manifest = build_bundle(
        contexts,
        company_manifest=company_manifest,
        membership=membership,
        crosswalk=crosswalk,
        theme_state=theme_state,
        as_of="2026-02-02",
    )
    assert manifest["status"] == expect_status
    assert manifest["company_count"] == 2
    assert manifest["exposure_count"] == 1
    out = tmp_path / "out"
    write_generation(out, exposures, manifest)
    marker = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    return out, marker


def _health_body(marker, *, status: str, warnings: list) -> dict:
    return {
        "status": status,
        "warnings": warnings,
        "company_count": 2,
        "exposure_count": 1,
        "generation_id": marker["generation_id"],
    }


def test_validate_generation_missing_manifest(tmp_path) -> None:
    assert validate_generation(tmp_path) == {
        "status": "empty",
        "warnings": ["manifest_missing"],
        "company_count": 0,
        "exposure_count": 0,
    }


def test_validate_generation_manifest_generation_id_mismatch(tmp_path) -> None:
    out, marker = _materialize(tmp_path)
    generation_id = marker["generation_id"]
    immutable = out / "generations" / generation_id / "manifest.json"
    payload = json.loads(immutable.read_text(encoding="utf-8"))
    payload["generation_id"] = "f" * 24
    immutable.write_text(json.dumps(payload), encoding="utf-8")
    assert validate_generation(out) == _health_body(
        marker, status="degraded", warnings=["generation_manifest_mismatch"],
    )


def test_validate_generation_missing_exposure_file(tmp_path) -> None:
    out, marker = _materialize(tmp_path)
    target = out / "generations" / marker["generation_id"] / "companies" / "AAPL.json"
    target.unlink()
    assert validate_generation(out) == _health_body(
        marker,
        status="degraded",
        warnings=["file_mismatch:companies/AAPL.json", "exposure_count_mismatch"],
    )


def test_validate_generation_valid_generation_is_ready(tmp_path) -> None:
    out, marker = _materialize(tmp_path)
    assert marker["status"] == "ready"
    assert marker["warnings"] == []
    assert validate_generation(out) == _health_body(marker, status="ready", warnings=[])


def test_validate_generation_stale_theme_state_stays_partial(tmp_path) -> None:
    """An intact tree echoes the marker. Age is not recomputed into degraded."""
    out, marker = _materialize(tmp_path, state_as_of="2026-01-27", expect_status="partial")
    assert marker["warnings"] == ["theme_state_stale"]
    assert validate_generation(out) == _health_body(
        marker, status="partial", warnings=["theme_state_stale"],
    )


def _generation_inputs():
    exposures = {
        "AAPL": {"generation_id": "a" * 24, "company": {"ticker": "AAPL"}, "marker": 1},
        "NVDA": {"generation_id": "a" * 24, "company": {"ticker": "NVDA"}, "marker": 2},
    }
    manifest = {
        "generation_id": "b" * 24,
        "status": "ready",
        "company_count": 2,
        "files": {"companies/AAPL.json": {"sha256": "ab", "bytes": 3}},
    }
    return exposures, manifest


def _reverse_dict(value):
    if not isinstance(value, dict):
        return value
    return {key: _reverse_dict(item) for key, item in reversed(list(value.items()))}


def test_derive_generation_id_is_stable_for_reordered_dicts() -> None:
    exposures, manifest = _generation_inputs()
    original = derive_generation_id(exposures, manifest)
    reordered = {
        ticker: _reverse_dict(body)
        for ticker, body in reversed(list(exposures.items()))
    }
    assert derive_generation_id(reordered, _reverse_dict(manifest)) == original
    assert len(original) == 24
    assert original == original.lower()


def test_derive_generation_id_changes_when_any_exposure_changes() -> None:
    exposures, manifest = _generation_inputs()
    original = derive_generation_id(exposures, manifest)
    mutated = json.loads(json.dumps(exposures))
    mutated["AAPL"]["company"]["ticker"] = "MSFT"
    assert derive_generation_id(mutated, manifest) != original


def test_derive_generation_id_ignores_stored_ids_and_file_receipts() -> None:
    exposures, manifest = _generation_inputs()
    original = derive_generation_id(exposures, manifest)
    moved = json.loads(json.dumps({"exposures": exposures, "manifest": manifest}))
    for item in moved["exposures"].values():
        item["generation_id"] = "c" * 24
    moved["manifest"]["generation_id"] = "d" * 24
    moved["manifest"]["files"] = {"companies/ZZ.json": {"sha256": "ff" * 32, "bytes": 9}}
    assert derive_generation_id(moved["exposures"], moved["manifest"]) == original
