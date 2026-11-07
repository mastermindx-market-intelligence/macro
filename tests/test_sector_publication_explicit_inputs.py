"""Original publication metadata parity and truthful native non-execution facts."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from pathlib import Path

import pytest
from engine import sector_central as central
from tests.fixtures.base_sector_publication_1f3f605 import complete_original

BUILT = datetime(2026, 11, 6, 12, 20, tzinfo=timezone.utc)


def record(status="ok", path=None):
    return {"status": status, "path": path, "sha256": None, "as_of": None, "error": None}


def specimen(n, unresolved, grade):
    return {"as_of": "2026-11-03", "meta": {"n_baskets": n, "conviction_score_version": 2,
        "membership_coverage": {"n_crowding_unresolved": unresolved}}, "grader": deepcopy(grade),
        "sectors": [{"id": "s-xlk", "kind": "sector", "ticker": "XLK", "name": "Technology", "name_zh": "科技", "score": 60}],
        "baskets": [{"id": "b-ai", "kind": "basket", "basket_id": "ai", "name": "AI", "score": 55}]}


GRADERS = [None, {"available": False, "note": "no calls logged yet"}, {"available": True},
    {"available": True, "score_version_segments": {"2": {"first_date": "2026-10-15"}}}]


@pytest.mark.parametrize("n,unresolved", [(0, 0), (5, 0), (5, 2), (5, 5)])
@pytest.mark.parametrize("grade", GRADERS)
def test_publication_crowding_and_research_binding_match_literal_original(n, unresolved, grade):
    data = specimen(n, unresolved, grade); before = deepcopy(data)
    statuses = {name: record("ok", name) for name in ("flows_html", "si_handoff", "action_board", "baskets", "grader")}
    statuses["si_handoff"] = record("malformed", "basketdata/si_handoff.json")
    premium = {"path": "premiumdata/sector_central.json", "written": True, "withheld_rows": 2}
    expected = complete_original(data, _flows_status=statuses["flows_html"], _si_status=statuses["si_handoff"],
        _ab_status=statuses["action_board"], _bk_status=statuses["baskets"], _grader_status=statuses["grader"],
        _payload_written=True, _sc_locked=[{"rows": [{}, {}]}], built_at=BUILT)
    result = central.complete_document_from_inputs(data, built_at=BUILT,
        secondary_sources=statuses, premium_publication=premium)
    assert result == expected
    assert data == before
    assert result["publication"]["premium_payload"] == premium
    assert result["sectors"][0]["research_handoff"]["snapshot"]["artifact"] == "sectordata/sector_central.json"
    result["publication"]["secondary_sources"]["si_handoff"]["status"] = "changed"
    assert statuses["si_handoff"]["status"] == "malformed"


def test_fixed_build_clock_and_same_session_row_correction_keep_distinct_digests():
    data = specimen(1, 0, {"available": True})
    kwargs = dict(built_at=BUILT, secondary_sources={}, premium_publication={"written": False})
    first = central.complete_document_from_inputs(data, **kwargs)
    assert central.complete_document_from_inputs(data, **kwargs) == first
    changed = deepcopy(data); changed["sectors"][0]["score"] += 1
    corrected = central.complete_document_from_inputs(changed, **kwargs)
    a = first["sectors"][0]["research_handoff"]["snapshot"]
    b = corrected["sectors"][0]["research_handoff"]["snapshot"]
    assert a["session"] == b["session"] and a["generation"] == b["generation"]
    assert a["content_sha256"] != b["content_sha256"]


def test_native_metadata_cannot_claim_html_or_legacy_premium_publication(monkeypatch):
    from lib import config
    from engine import sector_research_handoff
    data = specimen(1, 0, {"available": False, "note": "empty"})
    data["sectors"][0]["research_handoff"] = {"stale": "must not retain old binding"}
    def forbidden(*a, **k): raise AssertionError("acquisition or unbound handoff reached")
    monkeypatch.setattr(config, "load", forbidden); monkeypatch.setattr(config, "data_dir", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden); monkeypatch.setattr(sector_research_handoff, "attach_handoffs", forbidden)
    kwargs = dict(built_at=BUILT, secondary_sources={"flows_html": record("not_applicable")},
        premium_publication={"path": "premiumdata/sector_central.json", "written": False, "withheld_rows": 0},
        transport={"kind": "sector_generation", "legacy_html_published": False}, research_mode="unbound_native")
    result = central.complete_document_from_inputs(data, **kwargs)
    assert result["publication"]["premium_payload"]["written"] is False
    assert result["publication"]["research_handoff"] == {"status": "unbound", "reason": "native_receiver_not_bound"}
    assert "research_handoff" not in result["sectors"][0]
    assert result["publication"]["crowding_input"]["first_active_note"] == "empty"
    assert data["sectors"][0]["research_handoff"]["stale"]
    for override in ({"premium_publication": {"written": True}}, {"secondary_sources": {"flows_html": record("ok")}}, {"transport": None}):
        with pytest.raises(ValueError): central.complete_document_from_inputs(data, **{**kwargs, **override})


def test_naive_or_unknown_completion_context_is_refused():
    with pytest.raises(ValueError):
        central.complete_document_from_inputs({}, built_at=datetime(2026, 11, 6), secondary_sources={}, premium_publication={})
    with pytest.raises(ValueError):
        central.complete_document_from_inputs({}, built_at=BUILT, secondary_sources={}, premium_publication={}, research_mode="unknown")


def test_literal_publication_block_is_frozen():
    p = Path(__file__).parent / "fixtures/base_sector_publication_1f3f605.py"
    assert hashlib.sha256(p.read_bytes()).hexdigest() == "a790cbab0d7923cd1038078309779bbf78c1a099a08953e447706c0c34224fb1"
