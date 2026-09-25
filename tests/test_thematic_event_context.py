from __future__ import annotations

from datetime import datetime, timezone
import json

import pandas as pd

from engine import thematic_event_context as tec


CUTOFF = "2026-09-24T01:00:00Z"


def _membership():
    return {
        "baskets": {
            "cpu_compute": {
                "members": [
                    {"ticker": "AAA"},
                    {"ticker": "CCC", "removed": True},
                ],
            },
            "memory_storage": {
                "members": [{"ticker": "BBB"}],
            },
            "unrelated": {
                "members": [{"ticker": "ZZZ"}],
            },
        }
    }




def _rights():
    return {
        "family": "sec_edgar",
        "status": "admitted",
        "rights_class": "direct_display_ok",
        "internal_ok": True,
        "display_ok": True,
        "model_use_ok": True,
        "redistribution_ok": False,
        "rights_ref": tec.RIGHTS_REF,
        "model_use_rights_ref": tec.MODEL_USE_RIGHTS_REF,
        "representation_scope": "fixture factual metadata only",
    }


def _write_rights(root):
    cfg = root / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "theme_sources.yml").write_text(
        "families:\n"
        "  sec_edgar:\n"
        "    rights_class: direct_display_ok\n"
        "    auth_class: keyless_public\n"
    )
    reg = root / "research" / "licenses"
    reg.mkdir(parents=True, exist_ok=True)
    (reg / "PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md").write_text(
        "## SEC EDGAR\n\n"
        "| Dimension | Determination and posture |\n"
        "|---|---|\n"
        "| Model use | **RECORDED** — fixture. Posture: **user-facing**. |\n"
        "\n## Next family\n"
    )

def _events():
    return pd.DataFrame([
        {
            "ticker": "AAA", "cik": 111, "form": "8-K", "filing_date": "2026-09-23",
            "items": "1.01,2.03", "accession": "0000000111-26-000001",
            "_first_seen": "2026-09-23T16:00:00Z", "amount_usd": 5_000_000_000.0,
            "counterparty": "Bank A", "extraction_ok": True,
            "amount_src": "contract", "counterparty_src": "contract",
        },
        {
            "ticker": "AAA", "cik": 111, "form": "8-K", "filing_date": "2026-09-22",
            "items": "8.01", "accession": "0000000111-26-000002",
            "_first_seen": "2026-09-23T15:00:00Z", "amount_usd": 123.0,
            "counterparty": "Must Not Survive", "extraction_ok": False,
        },
        {
            "ticker": "BBB", "cik": 222, "form": "8-K", "filing_date": "2026-09-23",
            "items": "7.01", "accession": "0000000222-26-000001",
            "_first_seen": "2026-09-23T14:00:00Z", "extraction_ok": None,
        },
        {  # available only after the decision cutoff
            "ticker": "BBB", "cik": 222, "form": "8-K", "filing_date": "2026-09-23",
            "items": "8.01", "accession": "0000000222-26-000002",
            "_first_seen": "2026-09-24T02:00:00Z",
        },
        {  # outside the context window by first-seen time
            "ticker": "AAA", "cik": 111, "form": "8-K", "filing_date": "2026-08-01",
            "items": "8.01", "accession": "0000000111-26-000003",
            "_first_seen": "2026-08-02T12:00:00Z",
        },
        {  # removed member
            "ticker": "CCC", "cik": 333, "form": "8-K", "filing_date": "2026-09-23",
            "items": "8.01", "accession": "0000000333-26-000001",
            "_first_seen": "2026-09-23T12:00:00Z",
        },
        {  # current member of a theme outside the requested rank universe
            "ticker": "ZZZ", "cik": 999, "form": "8-K", "filing_date": "2026-09-23",
            "items": "8.01", "accession": "0000000999-26-000001",
            "_first_seen": "2026-09-23T11:00:00Z",
        },
        {  # malformed knowledge clock
            "ticker": "AAA", "cik": 111, "form": "8-K", "filing_date": "2026-09-23",
            "items": "8.01", "accession": "0000000111-26-000004",
            "_first_seen": "not-a-time",
        },
    ])


def test_sec_context_uses_first_seen_cutoff_and_declares_current_membership():
    got = tec.project_sec_event_context(
        _events(), _membership(),
        theme_ids=["cpu_compute", "memory_storage"],
        knowledge_cutoff=CUTOFF, window_days=14, max_events=10,
        source_snapshot_ref="sec#fixture", membership_snapshot_ref="membership#fixture",
        rights_posture=_rights(),
    )

    assert got["status"] == "ready"
    assert got["authority"] == "descriptive_research_only"
    assert got["is_context_only"] is True
    assert got["may_rank"] is got["may_gate"] is got["may_size"] is got["may_trade"] is False
    assert got["knowledge_cutoff"] == "2026-09-24T01:00:00Z"
    assert got["membership_basis"] == "current_only"
    assert got["historical_vintage_proven"] is False
    assert got["source_snapshot_ref"] == "sec#fixture"
    assert got["membership_snapshot_ref"] == "membership#fixture"
    assert got["blocked_sources"]["press_narrative_search"]["status"] == "blocked_rights"

    accessions = [e["reports"][0]["accession"] for e in got["events"]]
    assert accessions == [
        "0000000111-26-000001",
        "0000000111-26-000002",
        "0000000222-26-000001",
    ]
    assert "0000000222-26-000002" not in accessions
    assert "0000000333-26-000001" not in accessions
    assert "0000000999-26-000001" not in accessions

    excluded = got["coverage"]["excluded"]
    assert excluded["not_yet_seen"] == 1
    assert excluded["outside_context_window"] == 1
    assert excluded["outside_theme_membership"] == 2
    assert excluded["invalid_first_seen"] == 1


def test_extracted_amount_and_counterparty_survive_only_on_success():
    got = tec.project_sec_event_context(
        _events(), _membership(),
        theme_ids=["cpu_compute", "memory_storage"],
        knowledge_cutoff=CUTOFF, max_events=10,
        source_snapshot_ref="sec#fixture", membership_snapshot_ref="membership#fixture",
        rights_posture=_rights(),
    )
    by_acc = {e["reports"][0]["accession"]: e["reports"][0] for e in got["events"]}

    good = by_acc["0000000111-26-000001"]
    assert good["extraction_ok"] is True
    assert good["amount_usd"] == 5_000_000_000.0
    assert good["counterparty"] == "Bank A"

    failed = by_acc["0000000111-26-000002"]
    assert failed["extraction_ok"] is False
    assert "amount_usd" not in failed
    assert "counterparty" not in failed


def test_selection_is_theme_coverage_first_not_global_newest_only():
    frame = pd.DataFrame([
        {
            "ticker": "AAA", "cik": 111, "form": "8-K", "filing_date": "2026-09-23",
            "items": "8.01", "accession": f"0000000111-26-00000{i}",
            "_first_seen": f"2026-09-23T{20-i:02d}:00:00Z",
        }
        for i in range(1, 5)
    ] + [{
        "ticker": "BBB", "cik": 222, "form": "8-K", "filing_date": "2026-09-23",
        "items": "8.01", "accession": "0000000222-26-000009",
        "_first_seen": "2026-09-23T10:00:00Z",
    }])
    got = tec.project_sec_event_context(
        frame, _membership(),
        theme_ids=["cpu_compute", "memory_storage"],
        knowledge_cutoff=CUTOFF, max_events=2,
        source_snapshot_ref="sec#fixture", membership_snapshot_ref="membership#fixture",
        rights_posture=_rights(),
    )

    assert got["coverage"]["eligible_events"] == 5
    assert got["coverage"]["shown_events"] == 2
    assert got["coverage"]["omitted_events"] == 3
    shown_themes = {t for e in got["events"] for t in e["theme_ids"]}
    assert shown_themes == {"cpu_compute", "memory_storage"}
    assert got["coverage"]["themes_with_events"] == 2
    assert got["coverage"]["themes_represented"] == 2


def test_same_event_maps_to_overlapping_themes_once():
    membership = _membership()
    membership["baskets"]["memory_storage"]["members"].append({"ticker": "AAA"})
    one = _events().iloc[[0]]
    got = tec.project_sec_event_context(
        one, membership,
        theme_ids=["cpu_compute", "memory_storage"],
        knowledge_cutoff=CUTOFF, max_events=10,
        source_snapshot_ref="sec#fixture", membership_snapshot_ref="membership#fixture",
        rights_posture=_rights(),
    )

    assert len(got["events"]) == 1
    assert got["events"][0]["theme_ids"] == ["cpu_compute", "memory_storage"]


def test_loader_binds_real_file_bytes_and_never_hides_source_absence(tmp_path):
    data = tmp_path / "data"
    (data / "edgar").mkdir(parents=True)
    (data / "baskets").mkdir(parents=True)
    (data / "baskets" / "membership.json").write_text(json.dumps(_membership()))
    _events().to_parquet(data / "edgar" / "material_8k_events.parquet")
    _write_rights(tmp_path)

    got = tec.build_sec_event_context(
        root=tmp_path,
        theme_ids=["cpu_compute", "memory_storage"],
        knowledge_cutoff=CUTOFF,
        max_events=10,
    )
    assert got["status"] == "ready"
    assert got["source_snapshot_ref"].startswith("data/edgar/material_8k_events.parquet#sha256:")
    assert got["membership_snapshot_ref"].startswith("data/baskets/membership.json#sha256:")
    assert got["rights_posture"]["status"] == "admitted"
    assert got["rights_posture"]["rights_class"] == "direct_display_ok"
    assert got["rights_posture"]["model_use_ok"] is True
    assert got["rights_posture"]["redistribution_ok"] is False

    missing = tec.build_sec_event_context(
        root=tmp_path / "missing",
        theme_ids=["cpu_compute"],
        knowledge_cutoff=CUTOFF,
    )
    assert missing["status"] == "unavailable"
    assert missing["reason"] == "source_files_unavailable"
    assert missing["events"] == []



def test_projector_fails_closed_without_owner_rights():
    got = tec.project_sec_event_context(
        _events(), _membership(),
        theme_ids=["cpu_compute", "memory_storage"],
        knowledge_cutoff=CUTOFF, max_events=10,
        source_snapshot_ref="sec#fixture", membership_snapshot_ref="membership#fixture",
    )
    assert got["status"] == "unavailable"
    assert got["reason"] == "source_rights_not_admitted"
    assert got["events"] == []


def test_loader_refuses_existing_sources_until_both_rights_owners_admit(tmp_path):
    data = tmp_path / "data"
    (data / "edgar").mkdir(parents=True)
    (data / "baskets").mkdir(parents=True)
    (data / "baskets" / "membership.json").write_text(json.dumps(_membership()))
    _events().to_parquet(data / "edgar" / "material_8k_events.parquet")

    got = tec.build_sec_event_context(
        root=tmp_path,
        theme_ids=["cpu_compute", "memory_storage"],
        knowledge_cutoff=CUTOFF,
        max_events=10,
    )
    assert got["status"] == "unavailable"
    assert got["reason"] == "source_rights_not_admitted"
    assert got["rights_posture"]["display_ok"] is False
    assert got["rights_posture"]["model_use_ok"] is False
    assert got["events"] == []


def test_loader_refuses_model_use_when_theme_source_only_is_admitted(tmp_path):
    data = tmp_path / "data"
    (data / "edgar").mkdir(parents=True)
    (data / "baskets").mkdir(parents=True)
    (data / "baskets" / "membership.json").write_text(json.dumps(_membership()))
    _events().to_parquet(data / "edgar" / "material_8k_events.parquet")
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True)
    (cfg / "theme_sources.yml").write_text(
        "families:\n"
        "  sec_edgar:\n"
        "    rights_class: direct_display_ok\n"
        "    auth_class: keyless_public\n"
    )

    got = tec.build_sec_event_context(
        root=tmp_path,
        theme_ids=["cpu_compute"],
        knowledge_cutoff=CUTOFF,
    )
    assert got["status"] == "unavailable"
    assert got["reason"] == "source_rights_not_admitted"
    assert got["rights_posture"]["display_ok"] is True
    assert got["rights_posture"]["model_use_ok"] is False
    assert got["events"] == []

def test_us_gather_wires_existing_event_adapter_without_changing_rank_state(monkeypatch, tmp_path):
    from engine import thematic_desk as td

    site = tmp_path / "site" / "allocationdata"
    site.mkdir(parents=True)
    (site / "allocation.json").write_text(json.dumps({
        "as_of": "2026-09-23",
        "market_en": "US",
        "ranks": [
            {"name": "CPU Compute", "id": "cpu_compute", "rank": 1,
             "durability": {}, "crowding": {}, "etf_proxy": None},
            {"name": "Memory", "id": "memory_storage", "rank": 2,
             "durability": {}, "crowding": {}, "etf_proxy": "SMH"},
        ],
        "ai_handoff": {},
    }))
    seen = {}
    expected = {
        "schema": tec.SCHEMA,
        "status": "ready",
        "knowledge_cutoff": "2026-09-24T01:00:00Z",
        "events": [],
        "coverage": {"eligible_events": 0},
    }

    def fake(**kwargs):
        seen.update(kwargs)
        return expected

    monkeypatch.setattr(td._event_context, "build_sec_event_context", fake)
    state = td.gather_thematic_state("us", root=tmp_path)

    assert state["event_context"] is expected
    assert seen["root"] == tmp_path
    assert seen["theme_ids"] == ["cpu_compute", "memory_storage"]
    assert [r["id"] for r in state["narrative_rotation"]["ranks"]] == [
        "cpu_compute", "memory_storage",
    ]


def test_non_us_gather_does_not_invent_us_sec_context(monkeypatch, tmp_path):
    from engine import thematic_desk as td

    site = tmp_path / "site" / "allocationdata"
    site.mkdir(parents=True)
    (site / "allocation_china.json").write_text(json.dumps({
        "as_of": "2026-09-23",
        "market_en": "China",
        "ranks": [{"name": "Semiconductors", "id": "cn_semis", "rank": 1,
                   "durability": {}, "crowding": {}, "etf_proxy": None}],
        "ai_handoff": {},
    }))

    def forbidden(**kwargs):
        raise AssertionError("US SEC adapter must not run for non-US desks")

    monkeypatch.setattr(td._event_context, "build_sec_event_context", forbidden)
    state = td.gather_thematic_state("china", root=tmp_path)
    assert state["event_context"] is None
