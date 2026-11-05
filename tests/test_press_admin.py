"""tests/test_press_admin.py — D14 W1 press admin inspector (admin/press.py).

Read-only and fail-soft, mirroring admin/chronicle.py.  The panel must never
raise into the console and must never write: a panel that crashes on a
half-written staging file takes the operator's only view of the quarantine
list with it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from admin import press as A  # noqa: E402
from engine.press import desk_planner as P  # noqa: E402
from tests import press_fixtures as F  # noqa: E402


_REPORT = {
    "ok": False, "failed": ["our_value"],
    "checks": [{"name": "fact_anchor", "ok": True, "detail": "clean", "metrics": {}},
               {"name": "our_value", "ok": False,
                "detail": "our-value share 12.0% (< floor 40%)", "metrics": {}}],
    "our_value_share": 0.12, "max_block_jaccard": 0.03, "words": 420,
}


def _seed(tmp_path):
    root = F.fixture_root(tmp_path, ledger_rows=[{
        "id": "press-brief-1", "ts": "2026-07-26T13:20:00Z", "desk": "brief",
        "publication": "mastermind_news", "slug": "a-published-note",
        "sources": ["chronicle:x"], "seed_refs": [],
        "validator_report": {"ok": True, "our_value_share": 0.61},
        "urls": ["https://www.mastermind-x.com/blog/a-published-note.html"],
    }])
    stage = root / "data" / "press" / "staging"
    (stage / "passed.json").write_text(json.dumps({
        "id": "press-brief-p", "desk": "brief", "publication": "mastermind_news",
        "as_of": "2026-07-26", "staged_at": "2026-07-26T13:21:00Z",
        "status": "passed", "slug": "a-staged-note", "attempts": [{}],
        "draft": {"title": "A staged note"},
        "validator_report": {"ok": True, "checks": [], "our_value_share": 0.55,
                             "max_block_jaccard": 0.02, "words": 480},
    }), encoding="utf-8")
    (stage / "quarantined.json").write_text(json.dumps({
        "id": "press-brief-q", "desk": "brief", "publication": "mastermind_news",
        "as_of": "2026-07-26", "status": "quarantined", "attempts": [{}, {}, {}],
        "quarantine_reason": "validators: our_value", "draft": None,
        "validator_report": _REPORT,
    }), encoding="utf-8")
    (stage / "_run_summary.json").write_text(json.dumps({
        "run_at": "2026-07-26T13:21:00Z", "planned": 2, "passed": 1,
        "quarantined": 1, "items": [],
    }), encoding="utf-8")
    return root


def test_overview_separates_staged_from_quarantined(tmp_path):
    out = A.overview(root=_seed(tmp_path))
    assert out["ok"] is True
    assert [s["id"] for s in out["staged"]] == ["press-brief-p"]
    assert [q["id"] for q in out["quarantine"]] == ["press-brief-q"]
    assert out["quarantine"][0]["reason"] == "validators: our_value"


def test_overview_shows_per_validator_pass_fail(tmp_path):
    out = A.overview(root=_seed(tmp_path))
    checks = out["quarantine"][0]["checks"]
    assert {c["name"] for c in checks} == {"fact_anchor", "our_value"}
    assert [c["ok"] for c in checks] == [True, False]
    assert "12.0%" in next(c["detail"] for c in checks if c["name"] == "our_value")


def test_overview_reports_the_kill_switch_state(tmp_path, monkeypatch):
    root = _seed(tmp_path)
    monkeypatch.delenv("PRESS_PUBLISH_ENABLED", raising=False)
    dark = A.overview(root=root)["kill_switch"]
    assert dark["armed"] is False and dark["value"] is None
    assert "DARK" in dark["state"]

    monkeypatch.setenv("PRESS_PUBLISH_ENABLED", "true")
    armed = A.overview(root=root)["kill_switch"]
    assert armed["armed"] is True and "ARMED" in armed["state"]

    # The panel must read the switch the way the WORKFLOW does, or it lies.
    # GitHub's `==` ignores case but does NOT trim, so "TRUE" arms the lane and
    # "true " does not.
    monkeypatch.setenv("PRESS_PUBLISH_ENABLED", "TRUE")
    assert A.overview(root=root)["kill_switch"]["armed"] is True

    # "1" arms the marketing lane's switch. It must not arm this one by
    # accident — a muscle-memory value is exactly how a dark lane goes live.
    for value in ("1", "true ", " true", "yes", "0", ""):
        monkeypatch.setenv("PRESS_PUBLISH_ENABLED", value)
        assert A.overview(root=root)["kill_switch"]["armed"] is False, repr(value)


def test_overview_exposes_per_desk_cadence_and_thresholds(tmp_path):
    out = A.overview(root=_seed(tmp_path))
    desks = {c["desk"]: c for c in out["cadence"]}
    # `research_note` joined at W2R (XG-W8). It is a REAL desk with a real
    # cadence ceiling that the panel must show, and it plans zero slots today
    # because the cold-start volume knob composes stricter-of with it
    # (config/press.yml research_triage.volume.stage). The panel reports the
    # desk's own ceiling, not the resolved cap — see the triage ledger and
    # docs/research_triage.md for what actually runs.
    assert set(desks) == {"brief", "research_desk", "research_note"}
    assert desks["brief"]["publication"] == "mastermind_news"
    assert desks["brief"]["publication_domain"] == "mastermindx.ai"
    assert desks["research_desk"]["per_day"] == 1
    assert desks["research_note"]["publication"] == "mastermind_research"
    assert out["thresholds"]["our_value_min"] == 0.40
    assert out["thresholds"]["paraphrase_max_jaccard"] == 0.18
    # The panel must REPORT the shipped cutover state, not a literal that
    # happens to match it today. Pinning `is False` here would turn the cutover
    # PR red in the admin suite — a test failing because the switch it displays
    # got flipped is a test asserting the switch may never move.
    assert out["thresholds"]["cutover"] == P.load_config(_REPO).get("cutover")


def test_overview_returns_the_ledger_tail(tmp_path):
    out = A.overview(root=_seed(tmp_path))
    assert out["total_published"] == 1
    assert out["ledger_tail"][-1]["slug"] == "a-published-note"
    assert out["ledger_tail"][-1]["our_value_share"] == 0.61


def test_overview_is_honest_about_an_empty_ledger(tmp_path):
    out = A.overview(root=F.fixture_root(tmp_path))
    assert out["ok"] is True
    assert "published nothing yet" in out["note"]
    assert out["total_published"] == 0


def test_overview_survives_a_half_written_staging_file(tmp_path):
    root = _seed(tmp_path)
    (root / "data" / "press" / "staging" / "torn.json").write_text(
        '{"id": "press-brief-t", "status": "pas', encoding="utf-8")
    out = A.overview(root=root)
    assert out["ok"] is True
    assert len(out["staged"]) == 1     # the torn file is skipped, not fatal


def test_overview_never_writes(tmp_path):
    root = _seed(tmp_path)
    before = {p: p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}
    A.overview(root=root)
    after = {p: p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}
    assert before == after


def test_overview_on_a_bare_root_is_ok_not_an_error(tmp_path):
    out = A.overview(root=tmp_path)
    assert out["ok"] is True
    assert "not configured" in out["note"]


def test_overview_reports_an_error_shape_rather_than_raising(monkeypatch, tmp_path):
    monkeypatch.setattr(A, "_read_yaml", lambda p: (_ for _ in ()).throw(OSError("boom")))
    out = A.overview(root=tmp_path)
    assert out["ok"] is False and "boom" in out["error"]




def _claim_response(identity="press-brief-1", count=0):
    return {"publication_id": identity, "published_at": "2026-07-26T13:20:00+00:00",
            "observed_at": "2026-11-05T12:00:00Z", "active_accounts_claiming_content": count,
            "earliest_signup_at": "2026-07-26T13:20:00Z" if count else None,
            "latest_signup_at": "2026-11-04T20:00:00Z" if count else None}


def test_signup_claims_join_exact_identity_and_preserve_base_state(tmp_path):
    root = _seed(tmp_path)
    baseline = A.overview(root=root)
    calls = []
    def query(sql):
        calls.append(sql)
        return [_claim_response(count=3)]
    out = A.overview(root=root, audience_query=query)
    assert {k: v for k, v in out.items() if k != "signup_claims"} == baseline
    a = out["signup_claims"]
    assert a["status"] == "available" and a["rows"][0]["active_accounts_claiming_content"] == 3
    assert a["rows"][0]["desk"] == "brief" and a["rows"][0]["slug"] == "a-published-note"
    assert len(calls) == 1 and "LEFT JOIN auth.users" in calls[0]
    assert "u.created_at >= p.published_at" in calls[0] and "u.created_at < now()" in calls[0]
    assert "jsonb_typeof(u.raw_user_meta_data->'utm'->'utm_content')='string'" in calls[0]
    from admin.users import _ACTIVE
    assert _ACTIVE in calls[0]
    assert all(x not in a["rows"][0] for x in ("email", "user_id", "raw_user_meta_data"))




def test_signup_claims_backend_failure_preserves_native_press_state(tmp_path):
    def fail(sql):
        raise TimeoutError("PRIVATE_BACKEND_PAYLOAD")
    out=A.overview(root=_seed(tmp_path),audience_query=fail)
    assert out["ok"] is True and len(out["quarantine"]) == 1
    assert out["signup_claims"]["status"] == "unavailable"
    assert "PRIVATE_BACKEND_PAYLOAD" not in json.dumps(out)
