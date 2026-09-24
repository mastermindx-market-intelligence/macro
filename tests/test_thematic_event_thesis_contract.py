from __future__ import annotations

import json

from engine import desk_placebo as dp
from engine import thematic_desk as td


def _state(*, event_context=True):
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
    brief = td.synthesize(_state(), {"panel": {"enabled": False}}, _call(_thesis_payload()))
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
    brief = td.synthesize(_state(), {"panel": {"enabled": False}}, _call(payload))
    thesis = brief["theses"][0]

    assert [r["item_id"] for r in thesis["evidence_refs"]] == ["item-launch"]
    assert thesis["evidence_refs_rejected_n"] == 1


def test_event_aware_thesis_cannot_backdate_a_machine_grade():
    brief = td.synthesize(_state(), {"panel": {"enabled": False}}, _call(_thesis_payload()))
    thesis = brief["theses"][0]

    check = thesis["falsifier"]["check"]
    assert check["kind"] == "soft"
    assert "prospective decision anchor" in check["reason"]
    assert thesis["evaluation_status"] == "prospective_anchor_required"


def test_event_context_without_returned_refs_still_cannot_backdate_a_machine_grade():
    payload = _thesis_payload()
    payload["theses"][0].pop("evidence_refs")
    brief = td.synthesize(_state(), {"panel": {"enabled": False}}, _call(payload))
    thesis = brief["theses"][0]

    check = thesis["falsifier"]["check"]
    assert check["kind"] == "soft"
    assert thesis["evaluation_status"] == "prospective_anchor_required"
    assert thesis["event_evidence_bound"] is True
    assert thesis["evidence_refs"] == []


def test_legacy_thesis_without_event_context_keeps_existing_machine_check():
    brief = td.synthesize(_state(event_context=False), {"panel": {"enabled": False}},
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
    brief = td.synthesize(_state(), {"panel": {"enabled": False}}, _call(payload))

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
