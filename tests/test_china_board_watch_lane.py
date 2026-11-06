"""China Prophet v2 artifact + overflow UX contract.

The former 110/overflow split was positional and mislabeled raw legacy early
warnings as names that had cleared the actionable screen.  V2 exposes disjoint
semantic lanes and keeps ``watch`` only as a compatibility union.
"""
from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = (ROOT / "templates" / "china.html.j2").read_text()


def test_artifact_contract_versions_semantic_lanes():
    from scripts.export_signal_contracts import ARTIFACT_MANIFEST

    entry = next(
        e for e in ARTIFACT_MANIFEST
        if e["artifact"] == "site/factordata/china_standouts.json"
    )
    # The contract under test is the SEMANTIC LANES below, not a version digit. This was
    # `== "2.1.0"`, which reds on any backwards-compatible addition — it broke on the
    # 2.1.0 -> 2.2.0 bump that merely declared `staleness`, a field the builder was
    # already shipping. Pin the MAJOR (v2 is the disjoint-lane era; a v3 would be a
    # breaking re-cut this test must not silently accept) and a floor on the minor, so an
    # additive bump passes and a REMOVAL or rename still fails here.
    major, minor, _patch = (int(p) for p in entry["schema_version"].split("."))
    assert (major, minor) >= (2, 1), entry["schema_version"]
    assert major == 2, (
        f"china_standouts reached v{major} — a major bump means fields were removed or "
        "renamed, so these lane assertions must be re-derived, not just re-floored")
    required = set(entry["schema_fields"])
    assert {
        "schema_version", "actionable", "board_definition",
        "execution_coverage", "lane_counts", "ranking",
        "more_actionable", "late_or_unfillable", "forming", "track_ledger",
    } <= required
    optional = set(entry.get("optional_fields") or [])
    assert {"reversal_ledger", "reversal_watch", "watch"} <= optional
    assert {"prophet", "lane", "lane_reasons", "microstructure", "adv_yi"} <= set(
        entry["schema_item_fields"]
    )


def test_flat_overflow_spam_is_gone_and_depth_is_collapsed():
    assert "Also cleared today's screen" not in TEMPLATE
    assert "beyond the board's" not in TEMPLATE
    assert 'class="cn-depth ' in TEMPLATE
    assert "<details" in TEMPLATE
    assert "Early warnings — not confirmed" in TEMPLATE
    assert "Wait / unfillable / do not chase" in TEMPLATE
    assert "legacy early/T4/null-tier observations" in TEMPLATE


def test_more_actionable_left_the_drawer_for_the_unified_grid():
    """CONTRACT CHANGE (prophet board priority engine G0.2, 2026-08-02).

    `more_actionable` used to be a collapsed "More live setups" depth drawer of compact
    rows. It is now part of the ONE score-ordered grid of full prophet cards, so the
    drawer — and the assertion that used to require it — are both gone. What replaced
    the old guarantee is stronger: those rows are no longer a second-class list at all.
    Pinned in full by tests/test_cn_board_unified_grid.py.
    """
    # Assert on the CALL SITE, not the bare phrase: the template keeps a comment naming
    # the drawer it replaced, and a source-grep suite cannot tell documented history
    # from live markup (memory `test-pins-a-string-inside-dead-code`).
    assert "{{ t('More live setups'" not in TEMPLATE
    assert "更多实时形态" not in TEMPLATE
    assert "cn_depth_grid(_more)" not in TEMPLATE
    assert '<details class="cn-depth" data-stf="entry">' not in TEMPLATE
    # the rows still exist — they are merged into the live grid, in score order
    assert "set _more_lane = setups.get('more_actionable') or []" in TEMPLATE
    assert "_mrg.append({'r': _e.r, 'f': false})" in TEMPLATE


def test_depth_rows_are_cards_not_one_wrapped_name_paragraph():
    assert 'class="cn-depth-card"' in TEMPLATE
    assert "cn_depth_grid(_late)" in TEMPLATE
    assert "cn_depth_grid(_forming)" in TEMPLATE
    # Backward fallback data is still collapsed and formatted, never deleted.
    assert "Legacy depth — classification pending" in TEMPLATE
    assert "cn_depth_grid(_legacy_depth)" in TEMPLATE


def test_live_rank_copy_names_only_earned_components():
    assert "signal 35%" in TEMPLATE
    assert "entry 25%" in TEMPLATE
    assert "runway 20%" in TEMPLATE
    assert "bottom quality 10%" in TEMPLATE
    assert "reversal-sleeve membership 10%" in TEMPLATE
    assert "not a win probability or return forecast" in TEMPLATE


def test_zero_universe_publishes_outage_instead_of_reusing_stale_board():
    source = (ROOT / "scripts" / "build_china_library.py").read_text()
    assert "published explicit empty outage artifact" in source
    assert "Scored universe collapsed to zero" in source
    assert "allow_nan=False" in source


def test_renderer_rejects_a_superseded_fallback_under_the_current_heading():
    """Was `..._under_prophet_v2_heading`, and spelled "cn_prophet_v2" three times.

    That made it a MIRROR of the renderer's own hardcoded pin: it re-asserted the
    copy instead of the producer, so when #4509 moved the engine to cn_prophet_v3
    the test stayed green while the renderer rejected every real board and
    china_stocks.html served a "data coverage degraded" shell over a complete
    24-name board.  Reading BOARD_DEFINITION from the engine is what gives this
    test the power to fail on the next cutover.
    """
    from engine.china_board_rank import BOARD_DEFINITION
    from scripts.build_china import (
        _is_current_prophet_artifact,
        _prophet_outage_shell,
    )

    assert not _is_current_prophet_artifact({"buy": [{"ticker": "OLD"}]})
    assert _is_current_prophet_artifact({
        "schema_version": "2.0.0",
        "board_definition": BOARD_DEFINITION,
        "buy": [],
    })
    # a board from the PREVIOUS era must still be refused, not quietly relabelled
    assert not _is_current_prophet_artifact({
        "schema_version": "2.0.0",
        "board_definition": "cn_prophet_v2" if BOARD_DEFINITION != "cn_prophet_v2"
                            else "cn_prophet_v1",
        "buy": [],
    })
    shell = _prophet_outage_shell("test failure")
    assert shell["board_definition"] == BOARD_DEFINITION
    assert shell["buy"] == []
    assert shell["data_outage"]["flag"] is True


# ---------------------------------------------------------------------------
# Act Now must consume the current settled China theme-intel generation.
# ---------------------------------------------------------------------------

def _write_theme_intel(path: Path, as_of: str, *, stale: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(__import__("json").dumps({
        "theme_intel": {
            "as_of": as_of,
            "stale": stale,
            "themes": [{"id": "cn_semis", "reco": "enter"}],
        }
    }))


def _cn_after_settle():
    from datetime import datetime, timezone
    return datetime(2026, 9, 23, 10, 0, tzinfo=timezone.utc)


def test_act_now_theme_intel_reuses_current_persisted_generation(tmp_path, monkeypatch):
    from scripts import build_china
    p = tmp_path / "chinabasketdata" / "baskets.json"
    _write_theme_intel(p, "2026-09-23")

    def should_not_recompute(_region):
        raise AssertionError("current settled theme intel must be reused")

    monkeypatch.setattr("engine.theme_scoring.compute_theme_intel", should_not_recompute)
    got = build_china._theme_intel_for_act_now(
        p, observed_at=_cn_after_settle(), refresh=False
    )
    assert got["as_of"] == "2026-09-23"


def test_act_now_theme_intel_recomputes_stale_or_missing_generation(tmp_path, monkeypatch):
    from scripts import build_china
    p = tmp_path / "chinabasketdata" / "baskets.json"
    _write_theme_intel(p, "2026-09-22")
    calls = []

    def current(region):
        calls.append(region)
        return {"as_of": "2026-09-23", "themes": [{"id": "cn_semis", "reco": "enter"}]}

    monkeypatch.setattr("engine.theme_scoring.compute_theme_intel", current)
    got = build_china._theme_intel_for_act_now(p, observed_at=_cn_after_settle())
    assert calls == ["china"]
    assert got["as_of"] == "2026-09-23"

    p.unlink()
    got = build_china._theme_intel_for_act_now(p, observed_at=_cn_after_settle())
    assert calls == ["china", "china"]
    assert got["as_of"] == "2026-09-23"


def test_act_now_theme_intel_never_restamps_a_stale_recompute(tmp_path, monkeypatch):
    from scripts import build_china
    p = tmp_path / "chinabasketdata" / "baskets.json"
    _write_theme_intel(p, "2026-09-22")
    monkeypatch.setattr(
        "engine.theme_scoring.compute_theme_intel",
        lambda _region: {"as_of": "2026-09-22", "themes": []},
    )
    got = build_china._theme_intel_for_act_now(p, observed_at=_cn_after_settle())
    assert got["as_of"] == "2026-09-22"


def test_act_now_theme_intel_compute_failure_preserves_source_evidence(tmp_path, monkeypatch):
    from scripts import build_china
    p = tmp_path / "chinabasketdata" / "baskets.json"
    _write_theme_intel(p, "2026-09-22")

    def fail(_region):
        raise RuntimeError("synthetic theme owner failure")

    monkeypatch.setattr("engine.theme_scoring.compute_theme_intel", fail)
    got = build_china._theme_intel_for_act_now(p, observed_at=_cn_after_settle())
    assert got["as_of"] == "2026-09-22"


def test_act_now_data_lane_refreshes_even_same_session_artifact(tmp_path, monkeypatch):
    from scripts import build_china
    p = tmp_path / "chinabasketdata" / "baskets.json"
    _write_theme_intel(p, "2026-09-23")
    calls = []

    def corrected(region):
        calls.append(region)
        return {
            "as_of": "2026-09-23",
            "revision": "same-session-correction",
            "themes": [{"id": "cn_semis", "reco": "accumulate"}],
        }

    monkeypatch.setattr("engine.theme_scoring.compute_theme_intel", corrected)
    got = build_china._theme_intel_for_act_now(
        p, observed_at=_cn_after_settle(), refresh=True
    )
    assert calls == ["china"]
    assert got["revision"] == "same-session-correction"


@pytest.mark.parametrize("envelope", [["wrong-root"], "wrong-root", True, 7, [], None])
def test_act_now_bad_envelope_does_not_prevent_owner_refresh(tmp_path, monkeypatch, envelope):
    import json
    from scripts import build_china
    p = tmp_path / "baskets.json"
    p.write_text(json.dumps(envelope))
    original = p.read_bytes()
    current = {"as_of": "2026-09-23", "themes": []}
    calls = []

    def compute(region):
        calls.append(region)
        return current

    monkeypatch.setattr("engine.theme_scoring.compute_theme_intel", compute)
    assert build_china._theme_intel_for_act_now(p) is current
    assert calls == ["china"]
    assert p.read_bytes() == original


@pytest.mark.parametrize("envelope", [["wrong-root"], "wrong-root", True, 7, [], None])
def test_act_now_bad_envelope_rerender_keeps_sector_cards(tmp_path, monkeypatch, envelope):
    import json
    from scripts import build_china
    from engine.china_act_now import assemble_act_now
    p = tmp_path / "baskets.json"
    p.write_text(json.dumps(envelope))
    original = p.read_bytes()

    def forbidden(_region):
        raise AssertionError("a site-only render must not refresh theme intelligence")

    monkeypatch.setattr("engine.theme_scoring.compute_theme_intel", forbidden)
    intel = build_china._theme_intel_for_act_now(p, refresh=False)
    assert intel is None
    sector = {"ticker": "512480.SS", "name": "Sector control",
              "entry": {"urgency": "now", "tag": "BUY NOW"}}
    board = assemble_act_now([sector], intel, None)
    assert len(board["lanes"]["buy_now"]) == 1
    assert board["lanes"]["buy_now"][0]["kind"] == "SECTOR"
    assert p.read_bytes() == original
