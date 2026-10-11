"""Contract tests for the SNI coverage_profile.v1 qualification files (E0/M0, 2026-10-11).

The profiles record qualification facts about existing owners. These tests pin the
shape and the non-negotiables: every family is filled for every counter, every
authority flag is false, no identity id is minted from a ticker, local code or CIK,
and every unresolved or blocked cell names the owner that would close it.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "contracts" / "single_name_intelligence" / "coverage_profile.v1.schema.json"
PROFILE_DIR = ROOT / "config" / "single_name_intelligence" / "coverage_profiles"
PROFILES = ("alibaba", "tencent")

AUTHORITY_FLAGS = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)
ISSUER_ID_RE = re.compile(r"^ISS:[A-Z]{2}-[A-Z]{4}-[A-Z0-9.]+$")
SECURITY_ID_RE = re.compile(r"^SEC:[A-Z]{2}-[A-Z]{4}-[A-Z0-9.]+$")
# Shapes a minted-from-market-data id would take: bare ticker, HK local code, CIK.
TICKERISH_RE = re.compile(r"^(?:[A-Z]{1,5}|\d{3,5}(?:\.HK)?|0*\d{6,10})$")


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _validator() -> Draft202012Validator:
    schema = _schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _profile(name: str) -> dict:
    return yaml.safe_load((PROFILE_DIR / f"{name}.yml").read_text(encoding="utf-8"))


def _cells(profile: dict):
    for family, cells in profile["families"].items():
        for counter, cell in cells.items():
            yield family, counter, cell


@pytest.mark.parametrize("name", PROFILES)
def test_profile_matches_schema(name: str) -> None:
    errors = sorted(_validator().iter_errors(_profile(name)), key=lambda e: list(e.path))
    assert not errors, "\n".join(f"{list(e.path)}: {e.message}" for e in errors)


@pytest.mark.parametrize("name", PROFILES)
def test_header_declares_schema_asof_and_non_signal_status(name: str) -> None:
    head = (PROFILE_DIR / f"{name}.yml").read_text(encoding="utf-8").splitlines()[:8]
    text = "\n".join(head)
    assert head[0].startswith("# coverage_profile.v1")
    assert "as_of 2026-10-11" in head[0]
    assert "QUALIFICATION FACTS" in text and "not signals" in text


@pytest.mark.parametrize("name", PROFILES)
def test_every_family_is_filled_for_every_counter(name: str) -> None:
    profile = _profile(name)
    counters = set(profile["counters"])
    required = set(_schema()["properties"]["families"]["required"])
    assert set(profile["families"]) == required
    for family, cells in profile["families"].items():
        assert set(cells) == counters, f"{family}: {sorted(set(cells) ^ counters)}"


@pytest.mark.parametrize("name", PROFILES)
def test_all_six_authority_flags_are_false(name: str) -> None:
    authority = _profile(name)["authority"]
    assert set(authority) == set(AUTHORITY_FLAGS)
    assert all(authority[flag] is False for flag in AUTHORITY_FLAGS)


@pytest.mark.parametrize("name", PROFILES)
def test_identity_ids_are_existing_owner_shapes_never_minted(name: str) -> None:
    profile = _profile(name)
    issuer_ids = [profile["canonical_issuer_id"]] + [c["issuer_link"] for c in profile["counters"].values()]
    for value in issuer_ids:
        assert value == "UNRESOLVED" or ISSUER_ID_RE.match(value), value
        assert not TICKERISH_RE.match(value), value
    for counter in profile["counters"].values():
        sid = counter["security_id"]
        assert sid == "UNRESOLVED" or SECURITY_ID_RE.match(sid), sid
        assert not TICKERISH_RE.match(sid), sid
    # Profile-local keys must not masquerade as identity ids.
    assert not profile["issuer_key"].startswith(("ISS:", "SEC:"))


@pytest.mark.parametrize("name", PROFILES)
def test_unresolved_and_blocked_cells_name_the_owner_that_would_close_them(name: str) -> None:
    for family, counter, cell in _cells(_profile(name)):
        if cell["status"] in {"UNRESOLVED", "BLOCKED"}:
            assert cell.get("would_be_owner"), (family, counter)
        if cell["rights"].startswith("BLOCKED-"):
            assert cell["status"] == "BLOCKED", (family, counter)


@pytest.mark.parametrize("name", PROFILES)
def test_behavioral_pilot_is_historical(name: str) -> None:
    for counter, cell in _profile(name)["families"]["behavioral_pilot"].items():
        assert cell["temporal"]["state"] == "HISTORICAL", counter
        assert "HISTORICAL" in cell["notes"], counter


@pytest.mark.parametrize("name", PROFILES)
def test_cited_owner_code_paths_exist(name: str) -> None:
    for family, counter, cell in _cells(_profile(name)):
        for rel in cell["owner"]:
            assert (ROOT / rel).is_file(), (family, counter, rel)
        for rel in cell["evidence"]:
            # Evidence lives under data/, which sparse session trees omit; shape only here.
            assert rel.startswith("data/"), (family, counter, rel)


@pytest.mark.parametrize("name", PROFILES)
def test_profile_carries_no_promotion_vocabulary(name: str) -> None:
    text = (PROFILE_DIR / f"{name}.yml").read_text(encoding="utf-8").lower()
    assert "validated" not in text


def test_schema_rejects_a_true_authority_flag() -> None:
    bad = copy.deepcopy(_profile("alibaba"))
    bad["authority"]["signal_authority"] = True
    assert list(_validator().iter_errors(bad))


@pytest.mark.parametrize("minted", ["BABA", "9988.HK", "0001577552", "ISS:BABA"])
def test_schema_rejects_minted_issuer_ids(minted: str) -> None:
    bad = copy.deepcopy(_profile("tencent"))
    bad["canonical_issuer_id"] = minted
    assert list(_validator().iter_errors(bad))


def test_schema_rejects_ready_cell_with_unverified_rights() -> None:
    bad = copy.deepcopy(_profile("tencent"))
    cell = bad["families"]["market_data_daily"]["hkd_0700"]
    cell["status"] = "ready"
    cell["blocks"] = []
    assert list(_validator().iter_errors(bad))
