"""AI Desk Phase B — the adversarial analyst PANEL + desk-head adjudicator.

Verifies the four independent analysts run over the same bundle, the adjudicator
collapses them into the SAME falsifiable thesis schema (so the engine falsifier /
ledger / scorer downstream are untouched), the adjudicator's dissent is preserved,
the panel is surfaced for the page, and the whole thing degrades to the single
analyst when the panel is off or unavailable. Keyless — the fake model is routed by
the ROLE marker in each system prompt."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import ai_desk as d  # noqa: E402

CFG = d._cfg()

_FLOW = {
    "as_of": "2026-03-02", "verdict": "display_only",
    "regime": {"vix": 17.0, "elevated": False},
    "cluster": {"absorption": 0.55, "regime": "mixed", "dominant_cluster": ["Energy"]},
    "sectors": [{"name": "Energy", "type": "sector", "read_quality": 0.7, "stage": "emerging"}],
    "baskets": [], "emerging": {"sectors": ["Energy"], "baskets": []},
    "ai_handoff": {"overall_verdict": "display_only",
                   "do_not_conclude": ["no forward returns from flow_score"]},
}

_FINAL = {
    "regime_context": "Cyclical cluster concentrating; the panel is split.",
    "theses": [{"subject": "Energy", "lean": "overweight", "conviction": "low",
                "horizon_d": 20, "thesis": "Energy leads the cluster.",
                "evidence": ["opportunity: cluster leader", "structural: co-moving"],
                "dissent": "Skeptic: narrow and mean-reverting — likely a coincident trap.",
                "falsifier_text": "Energy lags SPY by >5% over 20 trading days."}],
    "confidence": "low",
}


def _state():
    return {"as_of": "2026-03-02", "flow": d._flow_view(_FLOW), "regime_snap": None,
            "track_record": None, "sources_present": {"flow": True, "regime_snap": False}}


def _role(system: str) -> str:
    """Mirror how a real routed responder must disambiguate — adjudicator FIRST,
    because its prompt legitimately names the analysts (incl. 'SKEPTIC')."""
    if "DESK HEAD" in system:
        return "adjudicator"
    for tag in ("OPPORTUNITY", "SKEPTIC", "BASE-RATE", "STRUCTURAL"):
        if f"ROLE: {tag}" in system:
            return tag.lower()
    return "single"


def _make_call(record=None, fail_roles=()):
    def call(system, user, cfg):
        role = _role(system)
        if record is not None:
            record.append(role)
        if role in fail_roles:
            return None, "llm_error"
        if role in ("adjudicator", "single"):
            return json.dumps(_FINAL), None
        return json.dumps({"stance": f"{role} read", "key_risk": "x",
                           "candidates": [{"subject": "Energy", "lean": "overweight",
                                           "rationale": "r", "strength": "moderate"}]}), None
    return call


# --- the panel runs, the adjudicator synthesizes ------------------------- #
def test_panel_runs_all_four_analysts_then_adjudicates():
    seen = []
    brief = d.synthesize(_state(), CFG, call=_make_call(record=seen))
    assert {"opportunity", "skeptic", "base-rate", "structural"} <= set(seen)
    assert "adjudicator" in seen and "single" not in seen      # adjudicated, not single-shot
    assert set(brief["panel"]) == {"opportunity", "skeptic", "base_rate", "structural"}


def test_adjudicated_thesis_keeps_schema_and_engine_falsifier():
    brief = d.synthesize(_state(), CFG, call=_make_call())
    assert brief["schema"] == "ai_desk.v1" and brief["is_context_only"] is True
    assert len(brief["theses"]) == 1
    t = brief["theses"][0]
    assert t["subject"] == "Energy" and t["lean"] == "overweight"
    chk = t["falsifier"]["check"]                              # engine-derived, unchanged by Phase B
    assert chk["kind"] == "rel_return" and chk["subject_ticker"] == "XLE" and t["check_by"]


def test_adjudicator_dissent_is_preserved():
    t = d.synthesize(_state(), CFG, call=_make_call())["theses"][0]
    assert "skeptic" in (t["dissent"] or "").lower()           # the bear case survives onto the card


# --- graceful degradation ------------------------------------------------ #
def test_panel_disabled_falls_back_to_single_analyst():
    seen = []
    cfg = {**CFG, "panel": {"enabled": False}}
    brief = d.synthesize(_state(), cfg, call=_make_call(record=seen))
    assert seen == ["single"]                                  # exactly one call, no panel
    assert not brief.get("panel") and len(brief["theses"]) == 1


def test_whole_panel_unavailable_falls_back_to_single():
    seen = []
    call = _make_call(record=seen,
                      fail_roles=("opportunity", "skeptic", "base-rate", "structural"))
    brief = d.synthesize(_state(), CFG, call=call)
    assert "single" in seen and "adjudicator" not in seen      # no panel survivors -> single analyst
    assert brief["panel"] == {} and len(brief["theses"]) == 1


def test_partial_panel_still_adjudicates():
    seen = []
    call = _make_call(record=seen, fail_roles=("opportunity", "base-rate"))  # 2 of 4 fail
    brief = d.synthesize(_state(), CFG, call=call)
    assert "adjudicator" in seen and "single" not in seen      # survivors are enough to adjudicate
    assert set(brief["panel"]) == {"skeptic", "structural"}
    assert len(brief["theses"]) == 1


# ---------------------------------------------------------------------------
# Thematic desk: point-in-time factual event context and owner rights.
# Consolidated here so the incumbent unrun-brain-desks PR gate collects it.
# ---------------------------------------------------------------------------

from datetime import datetime, timezone
from hashlib import sha256
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


def test_rights_revocation_and_corruption_override_a_warm_process_cache(tmp_path):
    _write_rights(tmp_path)
    registry = tmp_path / tec._theme_rights.REGISTRY_FILE
    assert tec._theme_rights.rights_class(
        tec.RIGHTS_FAMILY, path=registry) == "direct_display_ok"
    initial = tec._sec_rights_posture(tmp_path)
    assert initial["status"] == "admitted"

    registry.write_text(
        "families:\n"
        "  sec_edgar:\n"
        "    rights_class: internal_only\n"
        "    auth_class: keyless_public\n"
    )
    revoked = tec._sec_rights_posture(tmp_path)
    assert revoked["status"] == "not_admitted"
    assert revoked["display_ok"] is False
    assert revoked["model_use_ok"] is True
    assert revoked["registry_revision"] != initial["registry_revision"]
    assert initial["registry_revision"].startswith("rights_")
    assert revoked["redistribution_ok"] is False

    registry.write_text("families: [")
    corrupt = tec._sec_rights_posture(tmp_path)
    assert corrupt["status"] == "not_admitted"
    assert corrupt["display_ok"] is False
    assert corrupt["registry_revision"] is None

    registry.unlink()
    missing = tec._sec_rights_posture(tmp_path)
    assert missing["status"] == "not_admitted"
    assert missing["display_ok"] is False

    _write_rights(tmp_path)
    assert tec._sec_rights_posture(tmp_path)["status"] == "admitted"
    (tmp_path / tec.MODEL_USE_RIGHTS_PATH).write_text(
        "## SEC EDGAR\n\n"
        "| Model use | Posture: **internal-only**. |\n"
    )
    model_revoked = tec._sec_rights_posture(tmp_path)
    assert model_revoked["status"] == "not_admitted"
    assert model_revoked["display_ok"] is True
    assert model_revoked["model_use_ok"] is False


def test_loader_fingerprints_the_same_bytes_it_parses_during_source_replacement(
    monkeypatch, tmp_path,
):
    data = tmp_path / "data"
    (data / "edgar").mkdir(parents=True)
    (data / "baskets").mkdir(parents=True)
    (data / "baskets" / "membership.json").write_text(json.dumps(_membership()))
    source = data / "edgar" / "material_8k_events.parquet"
    _events().to_parquet(source)
    original = source.read_bytes()
    replacement = _events().iloc[[2]].to_parquet(index=False)
    assert replacement != original
    _write_rights(tmp_path)
    real_read_parquet = tec.pd.read_parquet

    def replace_then_parse(value, *args, **kwargs):
        source.write_bytes(replacement)
        return real_read_parquet(value, *args, **kwargs)

    monkeypatch.setattr(tec.pd, "read_parquet", replace_then_parse)
    got = tec.build_sec_event_context(
        root=tmp_path, theme_ids=["cpu_compute", "memory_storage"],
        knowledge_cutoff=CUTOFF, max_events=10,
    )

    assert source.read_bytes() == replacement
    assert got["status"] == "ready"
    assert got["source_snapshot_ref"] == (
        tec.SOURCE_PATH + "#sha256:" + sha256(original).hexdigest()
    )
    assert [event["reports"][0]["accession"] for event in got["events"]] == [
        "0000000111-26-000001",
        "0000000111-26-000002",
        "0000000222-26-000001",
    ]


# ---------------------------------------------------------------------------
# Thematic desk: source-bound thesis/watch records and evaluation separation.
# Consolidated here so the incumbent unrun-brain-desks PR gate collects it.
# ---------------------------------------------------------------------------

import json

from engine import desk_placebo as dp
from engine import thematic_desk as td


def _thematic_event_state(*, event_context=True):
    state = {
        "as_of": "2026-09-21",
        "region": "us",
        "market": "US",
        "narrative_rotation": {
            "region": "us",
            "ranks": [{
                "name": "AI Infrastructure",
                "name_zh": "AI",
                "id": "ai_infra",
                "rank": 1,
                "score": 2.4,
                "eligible": True,
                "durability_bar": 0.7,
                "crowding_z": 0.2,
                "crowded": False,
                "etf_proxy": "SMH",
                "scorable": True,
            }],
            "guardrails": {"do_not_conclude": ["no sizing"]},
        },
        "track_record": None,
    }
    if event_context:
        state["event_context"] = {
            "knowledge_cutoff": "2026-09-23T14:30:00+00:00",
            "source_snapshot_ref": "qbus@fixture",
            "coverage": {
                "status": "complete",
                "eligible_events": 2,
                "examined_events": 2,
                "failed_events": 0,
            },
            "events": [{
                "event_key": "ev-launch",
                "reports": [{
                    "item_id": "item-launch",
                    "source": "Primary",
                    "title": "Launch",
                    "body_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "source_date_value": "2026-09-08T20:53:00+00:00",
                    "publisher_stated_at": "2026-09-08T20:53:00+00:00",
                    "context_available_at": "2026-09-23T14:20:00+00:00",
                    "timestamp_quality": "PUBLISHER_STATED",
                }],
            }],
        }
    return state


def _call(payload):
    def call(system, user, cfg):
        return json.dumps(payload), None
    return call


def _thesis_payload():
    return {
        "regime_context": "ctx",
        "confidence": "low",
        "emerging_watch": "Watch agent infrastructure demand confirmation.",
        "emerging_watch_evidence_refs": [{
            "item_id": "item-launch",
            "event_key": "ev-launch",
            "role": "support",
        }],
        "theses": [{
            "subject": "AI Infrastructure",
            "lean": "overweight",
            "conviction": "low",
            "horizon_d": 20,
            "thesis": "A source-backed event may change the demand mechanism.",
            "evidence": [f"support-{i}" for i in range(1, 8)],
            "counterevidence": ["capacity may absorb demand", "valuation may already reflect it"],
            "evidence_refs": [{
                "item_id": "item-launch",
                "event_key": "ev-launch",
                "role": "support",
            }],
            "dissent": "The incremental hardware requirement is not yet quantified.",
            "falsifier_text": "The demand mechanism fails to appear in subsequent primary evidence.",
        }],
    }


def test_event_thesis_preserves_full_evidence_and_source_binding():
    brief = td.synthesize(_thematic_event_state(), {"panel": {"enabled": False}}, _call(_thesis_payload()))
    thesis = brief["theses"][0]

    assert thesis["record_type"] == "thesis"
    assert thesis["state_asof"] == "2026-09-21"
    assert thesis["decision_at"] == brief["generated_at"]
    assert thesis["knowledge_cutoff"] == "2026-09-23T14:30:00+00:00"
    assert thesis["source_snapshot_ref"] == "qbus@fixture"

    assert thesis["evidence"] == [f"support-{i}" for i in range(1, 6)]
    assert thesis["evidence_all"] == [f"support-{i}" for i in range(1, 8)]
    assert thesis["display_evidence_omitted_n"] == 2
    assert thesis["counterevidence"] == [
        "capacity may absorb demand",
        "valuation may already reflect it",
    ]
    assert thesis["evidence_refs"] == [{
        "item_id": "item-launch",
        "event_key": "ev-launch",
        "role": "support",
        "source_snapshot_ref": "qbus@fixture",
        "source": "Primary",
        "body_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "source_date_value": "2026-09-08T20:53:00+00:00",
        "publisher_stated_at": "2026-09-08T20:53:00+00:00",
        "context_available_at": "2026-09-23T14:20:00+00:00",
        "timestamp_quality": "PUBLISHER_STATED",
    }]
    assert thesis["event_coverage"]["eligible_events"] == 2
    assert thesis["event_coverage"]["examined_events"] == 2
    assert thesis["event_coverage"]["failed_events"] == 0
    assert thesis["evidence_refs_rejected_n"] == 0


def test_foreign_event_reference_is_rejected_not_silently_bound():
    payload = _thesis_payload()
    payload["theses"][0]["evidence_refs"].append({
        "item_id": "invented-item",
        "event_key": "invented-event",
        "role": "support",
    })
    brief = td.synthesize(_thematic_event_state(), {"panel": {"enabled": False}}, _call(payload))
    thesis = brief["theses"][0]

    assert [r["item_id"] for r in thesis["evidence_refs"]] == ["item-launch"]
    assert thesis["evidence_refs_rejected_n"] == 1


def test_event_aware_thesis_cannot_backdate_a_machine_grade():
    brief = td.synthesize(_thematic_event_state(), {"panel": {"enabled": False}}, _call(_thesis_payload()))
    thesis = brief["theses"][0]

    check = thesis["falsifier"]["check"]
    assert check["kind"] == "soft"
    assert "prospective decision anchor" in check["reason"]
    assert thesis["evaluation_status"] == "prospective_anchor_required"


def test_event_context_without_returned_refs_still_cannot_backdate_a_machine_grade():
    payload = _thesis_payload()
    payload["theses"][0].pop("evidence_refs")
    brief = td.synthesize(_thematic_event_state(), {"panel": {"enabled": False}}, _call(payload))
    thesis = brief["theses"][0]

    check = thesis["falsifier"]["check"]
    assert check["kind"] == "soft"
    assert thesis["evaluation_status"] == "prospective_anchor_required"
    assert thesis["event_evidence_bound"] is True
    assert thesis["evidence_refs"] == []


def test_legacy_thesis_without_event_context_keeps_existing_machine_check():
    brief = td.synthesize(_thematic_event_state(event_context=False), {"panel": {"enabled": False}},
                          _call(_thesis_payload()))
    thesis = brief["theses"][0]

    check = thesis["falsifier"]["check"]
    assert check["kind"] == "theme_rel_return"
    assert check["subject_ticker"] == "SMH"
    assert thesis["evaluation_status"] == "legacy_machine_check"
    assert thesis["knowledge_cutoff"] is None


def test_watch_persists_in_existing_ledger_but_never_returns_for_qledger(tmp_path):
    payload = _thesis_payload()
    payload["theses"] = []
    brief = td.synthesize(_thematic_event_state(), {"panel": {"enabled": False}}, _call(payload))

    written = td._append_ledger(brief, tmp_path)
    assert written == []

    rows = [json.loads(line) for line in
            (tmp_path / "data" / "thematic_desk" / "theses.jsonl").read_text().splitlines()]
    assert len(rows) == 1
    watch = rows[0]
    assert watch["record_type"] == "emerging_watch"
    assert watch["watch"] == "Watch agent infrastructure demand confirmation."
    assert watch["knowledge_cutoff"] == "2026-09-23T14:30:00+00:00"
    assert watch["source_snapshot_ref"] == "qbus@fixture"
    assert watch["evidence_refs"][0]["item_id"] == "item-launch"
    assert "lean" not in watch
    assert "falsifier" not in watch


def test_watch_rows_do_not_enter_thematic_track_record(tmp_path):
    d = tmp_path / "data" / "thematic_desk"
    d.mkdir(parents=True)
    (d / "theses.jsonl").write_text(json.dumps({
        "id": "watch-1",
        "record_type": "emerging_watch",
        "market": "us",
        "state_asof": "2026-01-01",
        "watch": "context only",
        "knowledge_cutoff": "2026-01-02T12:00:00+00:00",
    }) + "\n")

    track = td.score_ledger(root=tmp_path, today="2026-03-01")
    assert track is not None
    assert track["scored_total"] == 0
    assert track["open"] == 0
    assert track["unscored_soft"] == 0


def test_placebo_reconstruction_ignores_watch_rows(tmp_path):
    d = tmp_path / "data" / "thematic_desk"
    d.mkdir(parents=True)
    thesis = {
        "id": "thesis-1",
        "record_type": "thesis",
        "market": "us",
        "state_asof": "2026-01-05",
        "check_by": "2026-02-05",
        "falsifier": {"check": {"kind": "theme_rel_return"}},
    }
    watch = {
        "id": "watch-1",
        "record_type": "emerging_watch",
        "market": "us",
        "state_asof": "2026-01-05",
        "watch": "context only",
    }
    (d / "theses.jsonl").write_text(json.dumps(thesis) + "\n" + json.dumps(watch) + "\n")

    pairs, source, orphans, reason = dp._decided_mix(tmp_path, "thematic_desk", "2026-03-01")
    assert source == "ledger_elapsed"
    assert orphans == 0
    assert reason == ""
    assert [row["id"] for row, _ in pairs] == ["thesis-1"]


def test_event_scout_treats_attention_as_context_not_top_or_buy():
    prompt = td._PANEL_SYSTEMS["narrative_scout"]
    assert "attention/inflow spikes mark TOPS" not in prompt
    assert "NEVER by itself a buy or a top call" in prompt
    assert "event-first watch may precede a price cluster" in prompt
    assert "graded hypothesis" not in td._ADJ_SYSTEM
    assert "never a scored thesis" in td._ADJ_SYSTEM


def test_known_item_cannot_be_rebound_to_a_different_known_event():
    state = _thematic_event_state()
    state["event_context"]["events"].append({
        "event_key": "ev-other",
        "reports": [{
            "item_id": "item-other",
            "source": "Other source",
            "context_available_at": "2026-09-23T14:25:00+00:00",
        }],
    })
    refs = [
        {"item_id": "item-launch", "event_key": "ev-other", "role": "support"},
        {"item_id": "item-launch", "role": "support"},
        {"event_key": "ev-other", "role": "context"},
    ]
    payload = _thesis_payload()
    payload["theses"][0]["evidence_refs"] = refs
    payload["emerging_watch_evidence_refs"] = refs
    brief = td.synthesize(state, {"panel": {"enabled": False}}, _call(payload))

    thesis = brief["theses"][0]
    for normalized, rejected in (
        (thesis["evidence_refs"], thesis["evidence_refs_rejected_n"]),
        (brief["emerging_watch_evidence_refs"], brief["emerging_watch_evidence_refs_rejected_n"]),
    ):
        assert rejected == 1
        assert len(normalized) == 2
        assert normalized[0]["item_id"] == "item-launch"
        assert normalized[0]["event_key"] == "ev-launch"
        assert normalized[0]["source"] == "Primary"
        assert normalized[0]["context_available_at"] == "2026-09-23T14:20:00+00:00"
        assert normalized[1] == {
            "event_key": "ev-other",
            "role": "context",
            "source_snapshot_ref": "qbus@fixture",
        }
    assert thesis["evaluation_status"] == "prospective_anchor_required"


# ---------------------------------------------------------------------------
# Thematic desk: zero-thesis watch rendering and served/template parity.
# Consolidated here so the incumbent unrun-brain-desks PR gate collects it.
# ---------------------------------------------------------------------------

from pathlib import Path


def _source(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def test_event_watch_renders_before_zero_thesis_return_and_site_matches_template():
    root = Path(__file__).resolve().parents[1]
    template = _source(root, "templates/ai_desk_thematic.js")
    site = _source(root, "site/ai_desk_thematic.js")

    assert site == template
    watch = "if (brief && brief.emerging_watch && watchEl)"
    empty = "if (!brief || !theses.length)"
    assert template.count(watch) == 1
    assert template.index(watch) < template.index(empty)
    assert "source-bound · context only · unscored" in template
    assert "来源已绑定 · 仅供背景 · 不计分" in template
