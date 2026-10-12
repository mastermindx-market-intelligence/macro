"""business_model classification-axis reader (WS:GMI-THEME-GRAPH Taxonomy V2, lane L08).

Display-tier reader over the incumbent Nasdaq basket membership file's
house-curated ``archetype_groups``. Tests inject the membership document in
memory or write fixtures under ``tmp_path``; they never read ``data/**``.
"""
from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from engine.classification_axes import business_model as bm
from engine.classification_axes import cell
from engine.classification_axes.business_model import read_business_model

MODULE_PATH = Path(bm.__file__).resolve()


def _membership_doc() -> dict:
    """A well-formed membership document. Group keys are inserted out of
    sorted order on purpose: the reader must sort by group_id anyway."""
    return {
        "as_of": "2026-10-05",
        "subsectors": {
            "Software": {
                "name": "Software",
                "sector": "Technology",
                "members": [
                    {"ticker": "MSFT", "name": "Microsoft"},
                    {"ticker": "ORCL", "name": "Oracle"},
                ],
            },
            "Semiconductors": {
                "name": "Semiconductors",
                "sector": "Technology",
                "members": ["NVDA", "AMD"],
            },
        },
        "amalgamations": {
            "EV": {
                "name": "EV & Autonomy",
                "sector": "Consumer Discretionary",
                "members": [{"ticker": "TSLA", "name": "Tesla"}],
            },
        },
        "archetype_groups": {
            "notes": "house-curated archetypes; display only",
            "groups": {
                "platform_moat": {
                    "label_en": "Platform moat",
                    "label_zh": "平台护城河",
                    "rationale": "network effects and distribution scale",
                    "members": ["MSFT", "CRM"],
                },
                "asset_light": {
                    "label_en": "Asset-light platforms",
                    "label_zh": "轻资产平台",
                    "rationale": "capital-light software economics",
                    "members": ["MSFT", "ADBE"],
                },
            },
        },
    }


def _read(subject_id: str, *, as_of: str = "2026-10-05", **kwargs: object) -> dict:
    got = read_business_model(subject_id, as_of=as_of, **kwargs)
    assert cell.validate_cell(got) == [], cell.to_json(got)
    return got


def _write_membership(root: Path, text: str) -> Path:
    target = root / "data" / "baskets_nasdaq"
    target.mkdir(parents=True, exist_ok=True)
    (target / "membership.json").write_text(text, encoding="utf-8")
    return root


def test_constants_and_single_public_callable():
    assert bm.AXIS == "business_model"
    assert bm.SOURCE_OWNER == (
        "data/baskets_nasdaq/membership.json (house-curated archetype_groups)"
    )
    assert bm.SOURCE_ARTIFACT == "data/baskets_nasdaq/membership.json"
    assert bm.MAX_AGE_DAYS == 7
    assert bm.SUBJECT_KINDS == ("co",)
    assert bm.RIGHTS_CONTEXT is None
    public = sorted(
        name
        for name, obj in vars(bm).items()
        if not name.startswith("_")
        and not inspect.ismodule(obj)
        and callable(obj)
        and getattr(obj, "__module__", None) == bm.__name__
    )
    assert public == ["read_business_model"]


def test_source_dict_matches_the_frozen_shape():
    got = _read("co:us:MSFT", membership=_membership_doc())
    assert got["source"] == {
        "owner": bm.SOURCE_OWNER,
        "artifact": bm.SOURCE_ARTIFACT,
        "field": "archetype_groups",
    }


def test_ticker_in_two_groups_returns_both_sorted_by_group_id():
    got = _read("co:us:MSFT", membership=_membership_doc())
    assert got["status"] == "available"
    assert got["reason_code"] is None
    assert [group["group_id"] for group in got["value"]["groups"]] == [
        "asset_light",
        "platform_moat",
    ]
    assert got["value"]["groups"][0] == {
        "group_id": "asset_light",
        "label_en": "Asset-light platforms",
        "label_zh": "轻资产平台",
    }
    assert got["labels"] == ["house_curated"]
    assert got["unit"] is None
    assert got["observed_at"] == "2026-10-05"
    assert got["freshness"] == {"age_days": 0, "max_age_days": 7}


def test_universe_ticker_without_a_group_is_available_no_mapping():
    got = _read("co:us:ORCL", membership=_membership_doc())
    assert got["status"] == "available"
    assert got["reason_code"] is None
    assert got["value"] == {"groups": []}
    assert got["labels"] == ["NO_MAPPING", "house_curated"]
    assert got["observed_at"] == "2026-10-05"
    assert got["freshness"] == {"age_days": 0, "max_age_days": 7}


def test_group_member_outside_subsectors_is_still_in_the_universe():
    for subject_id in ("co:us:CRM", "co:us:ADBE", "co:us:TSLA", "co:us:NVDA", "co:us:AMD"):
        got = _read(subject_id, membership=_membership_doc())
        assert got["status"] == "available", subject_id
    crm = _read("co:us:CRM", membership=_membership_doc())
    assert [group["group_id"] for group in crm["value"]["groups"]] == ["platform_moat"]


def test_ticker_outside_the_universe_is_value_missing():
    got = _read("co:us:ZZZZ", membership=_membership_doc())
    assert got["status"] == "unknown"
    assert got["reason_code"] == "value_missing"
    assert got["value"] is None
    assert got["freshness"] is None
    assert got["labels"] == []


def test_stale_after_max_age_keeps_the_last_known_value():
    doc = _membership_doc()
    fresh = _read("co:us:MSFT", as_of="2026-10-12", membership=doc)  # 7 days old
    assert fresh["status"] == "available"
    assert fresh["freshness"] == {"age_days": 7, "max_age_days": 7}
    stale = _read("co:us:MSFT", as_of="2026-10-13", membership=doc)  # 8 days old
    assert stale["status"] == "stale"
    assert stale["reason_code"] == "owner_stale"
    assert stale["value"] == fresh["value"]
    assert stale["labels"] == ["house_curated"]
    assert stale["freshness"] == {"age_days": 8, "max_age_days": 7}
    assert stale["observed_at"] == "2026-10-05"


def test_document_as_of_after_the_caller_as_of_is_history_not_supported():
    got = _read("co:us:MSFT", as_of="2026-10-04", membership=_membership_doc())
    assert got["status"] == "unknown"
    assert got["reason_code"] == "history_not_supported"
    assert got["value"] is None
    assert got["freshness"] is None
    assert got["labels"] == []


def test_default_file_resolution_under_root(tmp_path):
    absent = _read("co:us:MSFT", root=tmp_path)
    assert absent["status"] == "unavailable"
    assert absent["reason_code"] == "owner_missing"

    _write_membership(tmp_path, "{not json")
    degraded = _read("co:us:MSFT", root=tmp_path)
    assert degraded["status"] == "unavailable"
    assert degraded["reason_code"] == "owner_degraded"
    assert degraded["provenance"] == ["read_error:JSONDecodeError"]

    _write_membership(tmp_path, json.dumps(_membership_doc()))
    healthy = _read("co:us:MSFT", root=tmp_path)
    assert healthy["status"] == "available"
    assert [group["group_id"] for group in healthy["value"]["groups"]] == [
        "asset_light",
        "platform_moat",
    ]


def test_empty_root_falls_back_to_repo_root(monkeypatch, tmp_path):
    """A falsy non-None ``root`` (``""``) must fall back to the repo root
    (R-root ruling), never to the process cwd."""
    repo = _write_membership(tmp_path / "repo", json.dumps(_membership_doc()))
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.setattr(bm, "_REPO_ROOT", repo)
    monkeypatch.chdir(elsewhere)
    expected = cell.to_json(_read("co:us:MSFT", root=repo))
    got = _read("co:us:MSFT", root="")
    assert got["status"] != "unavailable"
    assert cell.to_json(got) == expected


def test_degraded_documents(tmp_path):
    cases = [
        ("[]", "archetype_groups_missing"),
        ("\"a string\"", "archetype_groups_missing"),
        (
            json.dumps({"as_of": "2026-10-05", "subsectors": {}}),
            "archetype_groups_missing",
        ),
        (
            json.dumps({"as_of": "2026-10-05", "archetype_groups": {"groups": []}}),
            "archetype_groups_missing",
        ),
        (
            json.dumps({"archetype_groups": {"groups": {}}}),
            "asof_unparseable",
        ),
        (
            json.dumps({"as_of": "not-a-date", "archetype_groups": {"groups": {}}}),
            "asof_unparseable",
        ),
        (
            json.dumps({"as_of": 20261005, "archetype_groups": {"groups": {}}}),
            "asof_unparseable",
        ),
    ]
    for index, (text, note) in enumerate(cases):
        root = _write_membership(tmp_path / f"case{index}", text)
        got = _read("co:us:MSFT", root=root)
        assert got["status"] == "unavailable", text
        assert got["reason_code"] == "owner_degraded", text
        assert got["provenance"] == [note], text


def test_injected_membership_that_is_not_a_dict_is_degraded():
    got = _read("co:us:MSFT", membership=["not", "a", "dict"])
    assert got["status"] == "unavailable"
    assert got["reason_code"] == "owner_degraded"
    assert got["provenance"] == ["archetype_groups_missing"]


def test_injected_membership_never_touches_the_filesystem(tmp_path):
    got = _read(
        "co:us:MSFT",
        root=tmp_path / "does_not_exist",
        membership=_membership_doc(),
    )
    assert got["status"] == "available"
    assert [group["group_id"] for group in got["value"]["groups"]] == [
        "asset_light",
        "platform_moat",
    ]


def test_subject_kind_and_market_gates():
    doc = _membership_doc()
    for subject_id in (
        "co:hk:0700",
        "etf:QQQ",
        "theme:ai_compute",
        "basket:baskets:semis",
    ):
        got = _read(subject_id, membership=doc)
        assert got["status"] == "not_applicable", subject_id
        assert got["reason_code"] == "not_applicable", subject_id
        assert got["value"] is None
        assert got["labels"] == []
        assert got["freshness"] is None
    epoch = _read("co:us:FB#2", membership=doc)
    assert epoch["status"] == "unknown"
    assert epoch["reason_code"] == "value_missing"
    assert epoch["provenance"] == ["identity_epoch_not_supported"]


def test_unparseable_subjects_propagate_the_identity_error():
    for subject_id in ("ltheme:finviz:x", "co:eu:AAPL", "co:us:", "not-a-subject"):
        with pytest.raises(cell.AxisCellError):
            read_business_model(subject_id, as_of="2026-10-05", membership=_membership_doc())


def test_value_never_carries_rationale_or_members():
    got = _read("co:us:MSFT", membership=_membership_doc())
    text = cell.to_json(got["value"])
    assert "rationale" not in text
    assert "members" not in text
    assert "network effects" not in text
    for row in got["value"]["groups"]:
        assert set(row) == {"group_id", "label_en", "label_zh"}


def test_determinism_across_calls():
    doc = _membership_doc()
    first = cell.to_json(_read("co:us:MSFT", membership=doc))
    second = cell.to_json(_read("co:us:MSFT", membership=json.loads(json.dumps(doc))))
    assert first == second


def test_module_source_has_no_banned_dependencies_or_clocks():
    src = MODULE_PATH.read_text(encoding="utf-8")
    for banned in (
        "engine.intelligence_workspace",
        "engine.market_ontology",
        "engine.company_intelligence",
        "from scripts",
        "import scripts",
        "requests",
        "urllib",
        "socket",
        "datetime.now",
        "datetime.utcnow",
        "date.today",
        "time.time",
        "finviz_themes",
        "ths_concepts",
    ):
        assert banned not in src, banned
