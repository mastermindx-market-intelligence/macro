"""Current-owner context must never rewrite recovered Alpha/RS authority."""
from __future__ import annotations

from copy import deepcopy
import json

import pytest


def recovery_view():
    rows = [
        {
            "ticker": "AAA", "name": "Alpha", "sector": "Technology",
            "legacy_alpha": 2.5, "legacy_rs": 98.0,
            "legacy_rs3m": 97.0, "legacy_rs6m": 95.0, "legacy_rs12m": 93.0,
            "legacy_top_score": 1.8, "themes": [{"id": "memory_storage", "name": "Memory"}],
        },
        {
            "ticker": "BBB", "name": "Beta", "sector": "Industrials",
            "legacy_alpha": 1.5, "legacy_rs": 90.0,
            "legacy_rs3m": 88.0, "legacy_rs6m": 86.0, "legacy_rs12m": 84.0,
            "legacy_top_score": 1.1, "themes": [{"id": "data_center_power", "name": "Power"}],
        },
    ]
    return {
        "schema": "mastermind.leadership_lab.recovery.v1",
        "status": "RECOVERED_SNAPSHOT",
        "source_ref": "a" * 40,
        "source_session": "2026-10-02",
        "reference_session": "2026-10-02",
        "rows": deepcopy(rows),
        "shortlist": deepcopy(rows),
        "recovered_count": 2,
        "forecast_probability": None,
        "authority": {
            "prophet_rank": False, "entry": False, "sizing": False,
            "trade": False, "production_publish": False,
        },
        "gaps": [],
        "sources": {},
    }


def radar():
    return {
        "schema": "leader_radar.v2",
        "as_of": "2026-10-02",
        "built_at": "2026-10-05T10:25:16+00:00",
        "freshness": {
            "price_through": "2026-10-02",
            "regime_as_of": "2026-10-05",
            "revisions_asof": "2026-10-05",
            "state_history_through": "2026-10-01",
        },
        "history_since": "2026-07-11",
        "history_gaps": ["2026-09-22"],
        "rows": [
            {
                "ticker": "AAA", "state": "BREAKAWAY", "tracked_sessions": 4,
                "entry_read": {
                    "key": "staged", "caveats": ["earnings_near"],
                    "basis": ["rs_line_nh"], "extension_pct_50d": 8.0,
                },
                "breakaway_watch_state": "breakaway",
                # These are deliberately present upstream but must NOT be projected.
                "fire_precipice": True, "fire_onset": True, "k_true": 9,
            }
        ],
        "rerating_watch": [
            {"ticker": "AAA", "state": "BREAKAWAY",
             "chips": {"revision_positive": True, "revision_breadth_60": True,
                       "multiple_compressed": None, "earnings_within_14d": False}},
        ],
    }


def theme_state(*, may_rank=False):
    return {
        "schema": "neuralweb.theme_state.v1",
        "as_of": "2026-10-05",
        "generated_at": "2026-10-05T10:15:26Z",
        "authority": {
            "is_context_only": True, "may_rank": may_rank, "may_gate": False,
            "may_size": False, "may_escalate": False, "display_only": True,
            "not_a_signal": True,
        },
        "themes": [
            {
                "theme_id": "memory_storage",
                "name_en": "Memory, HBM & Storage",
                "name_zh": "存储与HBM",
                "foresight": {"stage": "WATCH", "tier": "P", "score": 45.0,
                              "entry_ready": False},
                "basket_intel": [{"basket_id": "memory_storage", "label": "neutral",
                                  "score": 54, "reco": "hold"}],
                "subsector_rotation": {
                    "rollup_quadrant": "leading",
                    "subsectors": [{
                        "key": "Semiconductors", "quadrant": "leading",
                        "rs": {"1W": 4.8, "1M": 20.9, "3M": 1.2, "6M": 53.7, "1Y": 130.3},
                        "accel_z": 2.7, "emerging_score": 3.4,
                    }],
                },
                "basket_ids": ["memory_storage"],
                "subsector_keys": ["Semiconductors"],
            },
            {
                "theme_id": "power_complex",
                "name_en": "AI Power",
                "name_zh": "AI电力",
                "foresight": {"stage": "FORMING", "tier": "P", "score": 55},
                "basket_intel": [],
                "subsector_rotation": {"rollup_quadrant": "improving", "subsectors": []},
                "basket_ids": ["data_center_power"],
                "subsector_keys": ["Electrical Equipment"],
            },
        ],
    }


_DEFAULT = object()


def compose(view=None, radar_payload=_DEFAULT, theme_payload=_DEFAULT):
    from engine.leadership_lab.context import compose_current_context
    return compose_current_context(
        recovery_view() if view is None else view,
        radar() if radar_payload is _DEFAULT else radar_payload,
        theme_state() if theme_payload is _DEFAULT else theme_payload,
        context_ref="b" * 40,
    )


def test_context_preserves_recovered_population_order_and_authority():
    view = recovery_view()
    before = deepcopy(view)
    result = compose(view)
    assert view == before
    assert [r["ticker"] for r in result["rows"]] == ["AAA", "BBB"]
    assert [r["ticker"] for r in result["shortlist"]] == ["AAA", "BBB"]
    for got, original in zip(result["rows"], before["rows"]):
        for field in ("legacy_alpha", "legacy_rs", "legacy_top_score"):
            assert got[field] == original[field]
    assert result["authority"] == before["authority"]
    assert result["forecast_probability"] is None
    assert result["current_context"]["authority"] == {
        "rank": False, "entry": False, "size": False,
        "execution": False, "trade": False,
    }


def test_radar_context_keeps_post_date_clocks_separate_and_blocks_historical_replay():
    result = compose()
    context = result["current_context"]
    assert context["historical_replay_qualified"] is False
    assert context["radar"]["as_of"] == "2026-10-02"
    assert context["radar"]["built_at"] == "2026-10-05T10:25:16+00:00"
    assert context["radar"]["freshness"]["revisions_asof"] == "2026-10-05"
    assert context["radar"]["history_gaps"] == ["2026-09-22"]
    assert "CONTEXT_KNOWN_AFTER_RECOVERY_SESSION" in context["limitations"]


def test_radar_row_is_whitelisted_and_fire_flags_never_become_entry_authority():
    row = compose()["rows"][0]
    current = row["current_context"]["radar"]
    assert current["status"] == "AVAILABLE"
    assert current["state"] == "BREAKAWAY"
    assert current["tracked_sessions"] == 4
    assert current["entry_read"]["key"] == "staged"
    assert "fire_precipice" not in current
    assert "fire_onset" not in current
    assert "k_true" not in current
    assert row["current_context"]["authority"]["entry"] is False
    assert row.get("entry_status", "NOT_CONNECTED") == "NOT_CONNECTED"


def test_missing_radar_row_is_unavailable_not_neutral():
    row = compose()["rows"][1]
    assert row["current_context"]["radar"] == {
        "status": "UNAVAILABLE", "reason": "NO_RADAR_ROW",
    }


def test_rerating_watch_is_context_only_and_not_a_probability():
    row = compose()["rows"][0]
    rerating = row["current_context"]["rerating"]
    assert rerating["status"] == "AVAILABLE"
    assert rerating["chips"]["revision_positive"] is True
    assert rerating["chips"]["multiple_compressed"] is None
    assert "probability" not in rerating
    assert row["current_context"]["forecast_probability"] is None


def test_theme_authority_drift_refuses_theme_enrichment_without_destroying_alpha():
    result = compose(theme_payload=theme_state(may_rank=True))
    assert result["rows"][0]["current_context"]["themes"] == []
    assert result["rows"][0]["legacy_alpha"] == 2.5
    assert result["current_context"]["theme_state"]["status"] == "REFUSED_AUTHORITY_DRIFT"
    assert "THEME_STATE_AUTHORITY_DRIFT" in result["current_context"]["limitations"]


def test_basket_to_theme_mapping_is_deterministic_and_strips_score_fields():
    result = compose()
    aaa = result["rows"][0]["current_context"]["themes"]
    bbb = result["rows"][1]["current_context"]["themes"]
    assert [x["theme_id"] for x in aaa] == ["memory_storage"]
    assert [x["theme_id"] for x in bbb] == ["power_complex"]
    theme = aaa[0]
    assert theme["name_en"] == "Memory, HBM & Storage"
    assert theme["foresight_stage"] == "WATCH"
    assert theme["rotation_quadrant"] == "leading"
    assert theme["subsectors"][0]["rs"]["1M"] == 20.9
    rendered = json.dumps(theme, sort_keys=True)
    assert "emerging_score" not in rendered
    assert "accel_z" not in rendered
    assert '"score"' not in rendered
    assert '"reco"' not in rendered
    assert '"entry_ready"' not in rendered


def test_multiple_theme_memberships_are_context_not_independent_votes():
    view = recovery_view()
    view["rows"][0]["themes"].append({"id": "data_center_power", "name": "Power"})
    view["shortlist"][0]["themes"].append({"id": "data_center_power", "name": "Power"})
    result = compose(view=view)
    current = result["rows"][0]["current_context"]
    assert [x["theme_id"] for x in current["themes"]] == ["memory_storage", "power_complex"]
    assert current["theme_membership_count"] == 2
    assert current["independent_confirmation_count"] is None


@pytest.mark.parametrize("bad", [
    None,
    {},
    {"schema": "leader_radar.v1", "rows": []},
    {"schema": "leader_radar.v2", "as_of": "bad", "rows": []},
])
def test_bad_radar_degrades_only_radar_context(bad):
    result = compose(radar_payload=bad)
    assert result["rows"][0]["legacy_alpha"] == 2.5
    assert result["rows"][0]["current_context"]["radar"]["status"] == "UNAVAILABLE"
    assert result["current_context"]["radar"]["status"] == "UNAVAILABLE"


def test_context_source_dates_are_not_collapsed_into_recovered_asof():
    result = compose()
    assert result["source_session"] == "2026-10-02"
    assert result["current_context"]["theme_state"]["as_of"] == "2026-10-05"
    assert result["current_context"]["radar"]["as_of"] == "2026-10-02"
    assert result["current_context"]["context_ref"] == "b" * 40


def test_context_output_is_strict_json_and_inputs_are_immutable():
    v, r, t = recovery_view(), radar(), theme_state()
    before = deepcopy((v, r, t))
    result = compose(v, r, t)
    assert (v, r, t) == before
    json.dumps(result, allow_nan=False)


def episode_book():
    return {
        "schema": "prophet.all_candidates/v1",
        "definition_era": "candidate-episode-v1-2026-08-25",
        "coverage": {"active": 1, "episodes": 1, "suppressed_inputs": 10},
        "episodes": [{
            "schema": "prophet.candidate_episode/v1",
            "ticker_at_observation": "AAA",
            "episode_id": "pe:SEC:US-XNAS-AAA:epoch_0:sa:abc:1",
            "company_id": "ISS:US-XNAS-AAA",
            "security_id": "SEC:US-XNAS-AAA",
            "identity_epoch": "epoch_0",
            "identity_epoch_state": "provisional",
            "episode_state": "ACTIVE",
            "opened_session": "2026-08-24",
            "opened_at": "2026-08-24T20:00:00Z",
            "last_observed_at": "2026-10-02T20:00:00Z",
            "observation_count": 11,
            "intake_classes": ["technical_emergence"],
        }],
    }


def compose_with_episode(book=None):
    from engine.leadership_lab.context import compose_current_context
    return compose_current_context(
        recovery_view(), radar(), theme_state(),
        context_ref="b" * 40,
        episode_book=episode_book() if book is None else book,
        episode_generation_id="peg:" + "c" * 64,
    )


def test_native_candidate_episode_ids_bind_current_context_without_rank_authority():
    result = compose_with_episode()
    row = result["rows"][0]["current_context"]
    assert row["episode"] == {
        "status": "AVAILABLE",
        "episode_id": "pe:SEC:US-XNAS-AAA:epoch_0:sa:abc:1",
        "company_id": "ISS:US-XNAS-AAA",
        "security_id": "SEC:US-XNAS-AAA",
        "identity_epoch": "epoch_0",
        "identity_epoch_state": "provisional",
        "episode_state": "ACTIVE",
        "opened_session": "2026-08-24",
        "opened_at": "2026-08-24T20:00:00Z",
        "last_observed_at": "2026-10-02T20:00:00Z",
        "observation_count": 11,
        "intake_classes": ["technical_emergence"],
    }
    assert row["identity_qualification"] == "CURRENT_EPISODE_NATIVE_IDS_NOT_HISTORICAL"
    assert row["authority"]["rank"] is False
    assert result["current_context"]["episode_book"]["generation_id"] == "peg:" + "c" * 64


def test_unmatched_candidate_episode_is_explicitly_unavailable():
    row = compose_with_episode()["rows"][1]["current_context"]
    assert row["episode"] == {"status": "UNAVAILABLE", "reason": "NO_CURRENT_EPISODE"}
    assert row["identity_qualification"] == "NOT_CONNECTED_CURRENT_ONLY_OWNER_NOT_YET_BOUND"


def test_duplicate_episode_ticker_refuses_identity_instead_of_picking_one():
    book = episode_book()
    other = deepcopy(book["episodes"][0])
    other["episode_id"] = "pe:SEC:US-XNAS-AAA:epoch_0:sa:def:2"
    other["security_id"] = "SEC:US-XNAS-AAA-OTHER"
    book["episodes"].append(other)
    result = compose_with_episode(book)
    row = result["rows"][0]["current_context"]
    assert row["episode"] == {
        "status": "UNAVAILABLE", "reason": "AMBIGUOUS_MULTIPLE_CURRENT_EPISODES",
    }
    assert row["identity_qualification"] == "NOT_CONNECTED_CURRENT_ONLY_OWNER_NOT_YET_BOUND"


@pytest.mark.parametrize("book,generation", [
    ({}, "peg:" + "c" * 64),
    ({"schema": "wrong", "episodes": []}, "peg:" + "c" * 64),
    (episode_book(), "bad"),
])
def test_invalid_episode_owner_degrades_only_episode_lane(book, generation):
    from engine.leadership_lab.context import compose_current_context
    result = compose_current_context(
        recovery_view(), radar(), theme_state(), context_ref="b" * 40,
        episode_book=book, episode_generation_id=generation)
    assert result["rows"][0]["legacy_alpha"] == 2.5
    assert result["rows"][0]["current_context"]["episode"]["status"] == "UNAVAILABLE"
    assert result["current_context"]["episode_book"]["status"] == "UNAVAILABLE"


def test_episode_projection_is_strict_whitelist():
    book = episode_book()
    book["episodes"][0].update(
        rank=1, score=99, buy=True, plan={"size": 100}, probability=0.99,
        source_event_ids=["private:event"],
    )
    row = compose_with_episode(book)["rows"][0]["current_context"]["episode"]
    rendered = json.dumps(row, sort_keys=True)
    for banned in ("rank", "score", "buy", "plan", "probability", "source_event_ids"):
        assert f'"{banned}"' not in rendered


def test_theme_extra_trading_permission_refuses_owner_drift():
    themes = theme_state()
    themes['authority']['may_trade'] = True
    result = compose(theme_payload=themes)
    assert result['current_context']['theme_state']['status'] == 'REFUSED_AUTHORITY_DRIFT'


def test_duplicate_radar_rows_do_not_first_win():
    owner = radar()
    other = deepcopy(owner['rows'][0])
    other['state'] = 'FAILED'
    owner['rows'].append(other)
    result = compose(radar_payload=owner)
    assert result['rows'][0]['current_context']['radar'] == {
        'status': 'UNAVAILABLE', 'reason': 'AMBIGUOUS_RADAR_ROWS'}


def test_duplicate_theme_identity_does_not_first_win():
    owner = theme_state()
    other = deepcopy(owner['themes'][0])
    other['foresight']['stage'] = 'FAILED'
    owner['themes'].append(other)
    result = compose(theme_payload=owner)
    assert result['rows'][0]['current_context']['themes'] == []
    assert 'AMBIGUOUS_THEME_IDS' in result['current_context']['limitations']
