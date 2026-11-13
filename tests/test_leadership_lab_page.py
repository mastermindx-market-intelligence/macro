"""The preview is a read-only, exact-ref, escaped research projection."""
from __future__ import annotations

from importlib import import_module, util
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]


def builder():
    assert util.find_spec("scripts.build_leadership_lab") is not None, "preview builder not implemented"
    return import_module("scripts.build_leadership_lab")


@pytest.fixture
def owner_repo(tmp_path):
    paths = {
        "site/factordata/alpha.json": {"as_of": "2026-10-02", "per_ticker": {
            "A": {"alpha": 2, "rs": 99, "entry": "extended"},
            "B": {"alpha": 1, "rs": 80}}},
        "site/factordata/factors.json": {"as_of": "2026-10-02", "table": [
            {"ticker": "A", "name": '<script>alert("source")</script>', "sector": "Technology"}]},
        "site/basketdata/baskets.json": {"as_of": "2026-10-02", "baskets": [{
            "id": "theme-1", "name": "Theme One",
            "members": [{"symbol": "A"}, {"symbol": "B"}],
        }]},
    }
    for name, payload in paths.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "site"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "-c", "core.hooksPath=/dev/null",
                    "commit", "-qm", "Owner fixture"], check=True)
    ref = subprocess.check_output(["git", "-C", str(tmp_path), "rev-parse", "HEAD"], text=True).strip()
    return tmp_path, ref, paths


def test_reader_binds_exact_bytes_and_ignores_dirty_working_copy(owner_repo):
    repo, ref, paths = owner_repo
    module = builder()
    before = module.build_view(ref, "2026-10-02", repo_root=repo)
    (repo / "site/factordata/alpha.json").write_text('{"as_of":"2099-01-01"}')
    after = module.build_view(ref, "2026-10-02", repo_root=repo)
    assert before == after
    assert after["recovered_count"] == 2
    import hashlib
    for label, source in after["sources"].items():
        assert source["sha256"] == hashlib.sha256(json.dumps(paths[source["path"]]).encode()).hexdigest()
    json.dumps(after, allow_nan=False)


@pytest.mark.parametrize("ref", ["main", "HEAD", "-h", "abc", "a" * 40 + ":private.json"])
def test_reader_refuses_mutable_refs_or_revision_expression(owner_repo, ref):
    with pytest.raises(ValueError):
        builder().build_view(ref, "2026-10-02", repo_root=owner_repo[0])


def test_missing_required_owner_file_fails_instead_of_reading_working_copy(owner_repo):
    repo, ref, _ = owner_repo
    subprocess.run(["git", "-C", str(repo), "rm", "-q", "site/factordata/alpha.json"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "-c", "core.hooksPath=/dev/null",
                    "commit", "-qm", "Missing source"], check=True)
    new_ref = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    with pytest.raises(ValueError, match="source"):
        builder().build_view(new_ref, "2026-10-02", repo_root=repo)


def test_html_is_escaped_and_labels_recovery_not_live_or_entry(owner_repo):
    repo, ref, _ = owner_repo
    module = builder()
    view = module.build_view(ref, "2026-10-02", repo_root=repo)
    html = module.render_html(view)
    assert '<script>alert("source")</script>' not in html
    assert "&lt;script&gt;alert" in html
    assert "Leadership Lab" in html
    assert "2026-10-02" in html
    assert "Research preview" in html
    assert "Not a buy signal" in html
    assert "Entry evidence not connected" in html
    assert "data-lang" in html and "领先股研究" in html
    import re
    assert not re.search(r'@font-face\s*\{', html)
    assert not re.search(r'@import\s+url\(', html)
    assert 'src="https://' not in html
    assert 'src="http://' not in html
    assert html.count('data-leader-row=') == 2


def test_preview_subset_and_unfiltered_population_are_disclosed(owner_repo):
    repo, ref, _ = owner_repo
    module = builder()
    view = module.build_view(ref, "2026-10-02", repo_root=repo, limit=1)
    html = module.render_html(view)
    assert 'data-leader-row=' in html
    assert html.count('data-leader-row=') == 1
    assert "1 of 2" in html
    assert "Filter this preview" in html


def test_stale_and_future_views_have_explicit_empty_or_historical_states(owner_repo):
    repo, ref, _ = owner_repo
    module = builder()
    stale = module.render_html(module.build_view(ref, "2026-10-05", repo_root=repo))
    future = module.render_html(module.build_view(ref, "2026-10-01", repo_root=repo))
    assert "Older source snapshot" in stale
    assert "No eligible source snapshot" in future
    assert 'data-leader-row=' not in future


def test_cli_has_no_file_writer_or_production_publisher():
    module = builder()
    import ast
    tree = ast.parse(Path(module.__file__).read_text())
    calls = {node.func.attr for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
    assert not calls.intersection({"write_text", "write_bytes", "mkdir", "unlink", "replace"})
    assert "write_page" not in Path(module.__file__).read_text()
    assert "--output" not in Path(module.__file__).read_text()


def test_native_select_options_do_not_embed_span_markup(owner_repo):
    repo, ref, _ = owner_repo
    module = builder()
    html = module.render_html(module.build_view(ref, "2026-10-02", repo_root=repo))
    import re
    assert not re.search(r'<option[^>]*>\s*<', html)


def test_optional_missing_enrichment_does_not_destroy_alpha_recovery(owner_repo):
    repo, ref, _ = owner_repo
    subprocess.run(["git", "-C", str(repo), "rm", "-q", "site/factordata/factors.json"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "-c", "core.hooksPath=/dev/null",
                    "commit", "-qm", "Optional source missing"], check=True)
    new_ref = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    result = builder().build_view(new_ref, "2026-10-02", repo_root=repo)
    assert result["recovered_count"] == 2
    assert result["sources"]["factors"]["read_status"] == "UNAVAILABLE"
    assert all(row["legacy_top_score"] is None for row in result["rows"])


def _commit_current_context(repo: Path) -> str:
    radar = {
        "schema": "leader_radar.v2",
        "as_of": "2026-10-02",
        "built_at": "2026-10-05T10:25:16+00:00",
        "freshness": {
            "price_through": "2026-10-02",
            "regime_as_of": "2026-10-05",
            "revisions_asof": "2026-10-05",
        },
        "history_since": "2026-07-11",
        "history_gaps": [],
        "rows": [{
            "ticker": "A", "state": "BREAKAWAY", "tracked_sessions": 3,
            "entry_read": {"key": "staged", "caveats": [], "basis": ["rs_line_nh"],
                           "extension_pct_50d": 7.0},
            "fire_onset": True,
        }],
        "rerating_watch": [{
            "ticker": "A", "state": "BREAKAWAY",
            "chips": {"revision_positive": True, "revision_breadth_60": True,
                      "multiple_compressed": None, "earnings_within_14d": False},
        }],
    }
    themes = {
        "schema": "neuralweb.theme_state.v1",
        "as_of": "2026-10-05",
        "generated_at": "2026-10-05T10:15:26Z",
        "authority": {
            "is_context_only": True, "may_rank": False, "may_gate": False,
            "may_size": False, "may_escalate": False, "display_only": True,
            "not_a_signal": True,
        },
        "themes": [{
            "theme_id": "theme_one", "name_en": "Theme One", "name_zh": "主题一",
            "foresight": {"stage": "WATCH", "score": 44, "entry_ready": False},
            "subsector_rotation": {
                "rollup_quadrant": "leading",
                "subsectors": [{"key": "Semiconductors", "quadrant": "leading",
                                "rs": {"1W": 3.0, "1M": 12.0, "3M": 7.0}}],
            },
            "basket_ids": ["theme-1"], "subsector_keys": ["Semiconductors"],
        }],
    }
    generation_id = "peg:" + "c" * 64
    episode_head = {
        "schema": "prophet.candidate_episode_head/v1",
        "generation_id": generation_id,
        "content_sha256": "d" * 64,
        "manifest_sha256": "sha256:" + "e" * 64,
    }
    entry_radar_ledger = {
        "schema": "entry_radar.w5_ledger_state/v1",
        "session": "2026-10-05",
        "state": "WAITING_FOR_LIVE_SOURCE",
        "spool_dir": None,
        "observed_spool_events": 0,
        "live_forward_rows": 0,
        "forward_rows_total": 0,
        "qledger": {"registered": 0, "rejected": 0, "failed": 0},
        "updated_at": "2026-10-05T10:08:52.994624+00:00",
    }
    episode_book = {
        "schema": "prophet.all_candidates/v1",
        "definition_era": "candidate-episode-v1-2026-08-25",
        "coverage": {"active": 1, "episodes": 1, "suppressed_inputs": 4},
        "episodes": [{
            "schema": "prophet.candidate_episode/v1",
            "ticker_at_observation": "A",
            "episode_id": "pe:SEC:US-XNAS-A:epoch_0:sa:abc:1",
            "company_id": "ISS:US-XNAS-A",
            "security_id": "SEC:US-XNAS-A",
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
    episode_book_rel = (
        f"data/us_prophet_rank/episodes/generations/{generation_id}/all_candidates.json")
    for rel, payload in (
        ("site/leaderradar/radar.json", radar),
        ("data/neuralweb/theme_state.json", themes),
        ("data/entry_radar/ledger_state.json", entry_radar_ledger),
        ("data/us_prophet_rank/episodes/HEAD.json", episode_head),
        (episode_book_rel, episode_book),
    ):
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "site/leaderradar/radar.json",
                    "data/neuralweb/theme_state.json", "data/entry_radar/ledger_state.json",
                    "data/us_prophet_rank/episodes/HEAD.json", episode_book_rel], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "-c", "core.hooksPath=/dev/null",
                    "commit", "-qm", "Current owner context"], check=True)
    return subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()


def test_context_ref_is_separate_exact_commit_and_ignores_dirty_working_copy(owner_repo):
    repo, recovery_ref, _ = owner_repo
    context_ref = _commit_current_context(repo)
    module = builder()
    before = module.build_view(
        recovery_ref, "2026-10-02", repo_root=repo, context_ref=context_ref)
    (repo / "site/leaderradar/radar.json").write_text(
        '{"schema":"leader_radar.v2","as_of":"2099-01-01"}', encoding="utf-8")
    after = module.build_view(
        recovery_ref, "2026-10-02", repo_root=repo, context_ref=context_ref)
    assert before == after
    assert after["source_ref"] == recovery_ref
    assert after["source_session"] == "2026-10-02"
    assert after["current_context"]["context_ref"] == context_ref
    assert after["current_context"]["theme_state"]["as_of"] == "2026-10-05"
    assert after["rows"][0]["current_context"]["radar"]["state"] == "BREAKAWAY"
    assert after["rows"][0]["current_context"]["episode"]["security_id"] == "SEC:US-XNAS-A"
    assert after["rows"][0]["current_context"]["episode"]["company_id"] == "ISS:US-XNAS-A"
    assert after["rows"][0]["current_context"]["identity_qualification"] == "CURRENT_EPISODE_NATIVE_IDS_NOT_HISTORICAL"
    assert after["current_context"]["sources"]["episode_head"]["read_status"] == "READ"
    assert after["current_context"]["sources"]["episode_book"]["read_status"] == "READ"
    assert after["rows"][0]["current_context"]["authority"]["entry"] is False
    json.dumps(after, allow_nan=False)


@pytest.mark.parametrize("ref", ["HEAD", "main", "b" * 39, "b" * 40 + ":x"])
def test_context_ref_must_be_exact_commit(owner_repo, ref):
    repo, recovery_ref, _ = owner_repo
    with pytest.raises(ValueError):
        builder().build_view(
            recovery_ref, "2026-10-02", repo_root=repo, context_ref=ref)


def test_missing_optional_context_owner_degrades_without_destroying_recovery(owner_repo):
    repo, recovery_ref, _ = owner_repo
    context_ref = _commit_current_context(repo)
    subprocess.run(["git", "-C", str(repo), "rm", "-q",
                    "site/leaderradar/radar.json"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "-c", "core.hooksPath=/dev/null",
                    "commit", "-qm", "Radar absent"], check=True)
    no_radar_ref = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    result = builder().build_view(
        recovery_ref, "2026-10-02", repo_root=repo, context_ref=no_radar_ref)
    assert result["recovered_count"] == 2
    assert result["rows"][0]["legacy_alpha"] == 2.0
    assert result["current_context"]["radar"]["status"] == "UNAVAILABLE"
    assert result["current_context"]["sources"]["radar"]["read_status"] == "UNAVAILABLE"
    assert result["current_context"]["sources"]["theme_state"]["read_status"] == "READ"


def test_no_context_ref_keeps_original_recovery_schema(owner_repo):
    repo, recovery_ref, _ = owner_repo
    result = builder().build_view(recovery_ref, "2026-10-02", repo_root=repo)
    assert "current_context" not in result
    assert result["schema"] == "mastermind.leadership_lab.recovery.v1"


def test_html_current_owner_context_is_plain_labeled_and_non_authoritative(owner_repo):
    repo, recovery_ref, _ = owner_repo
    context_ref = _commit_current_context(repo)
    module = builder()
    view = module.build_view(
        recovery_ref, "2026-10-02", repo_root=repo, context_ref=context_ref)
    html = module.render_html(view)
    assert "Current owner context" in html
    assert "Current context only" in html
    assert "Breaking out" in html
    assert "Theme One" in html
    assert "Semiconductors" in html
    assert "2026-10-05" in html
    assert "cannot be replayed as 2026-10-02 evidence" in html
    assert "fire_onset" not in html
    assert "fire_precipice" not in html
    assert "emerging_score" not in html
    assert "Entry permission" in html
    assert "Not connected" in html


def test_html_current_context_does_not_reorder_recovered_shortlist(owner_repo):
    repo, recovery_ref, _ = owner_repo
    context_ref = _commit_current_context(repo)
    module = builder()
    view = module.build_view(
        recovery_ref, "2026-10-02", repo_root=repo, context_ref=context_ref)
    # A has current Radar context; B does not. Recovered order must still be A then B.
    html = module.render_html(view)
    assert html.index('data-leader-row="A"') < html.index('data-leader-row="B"')
    assert [row["ticker"] for row in view["shortlist"]] == ["A", "B"]


def test_html_without_context_ref_has_no_current_owner_context(owner_repo):
    repo, recovery_ref, _ = owner_repo
    html = builder().render_html(
        builder().build_view(recovery_ref, "2026-10-02", repo_root=repo))
    assert "Current owner context" not in html


def test_html_shows_native_episode_identity_only_inside_research_detail(owner_repo):
    repo, recovery_ref, _ = owner_repo
    context_ref = _commit_current_context(repo)
    module = builder()
    html = module.render_html(module.build_view(
        recovery_ref, "2026-10-02", repo_root=repo, context_ref=context_ref))
    assert "Current Prophet episode" in html
    assert "Active since 2026-08-24" in html
    assert "SEC:US-XNAS-A" in html
    assert "ISS:US-XNAS-A" in html
    assert "Current episode identity only—not historical identity proof" in html


def _minimal_earnings_detail(view):
    episode = view["rows"][0]["current_context"]["episode"]
    generation = view["current_context"]["episode_book"]["generation_id"]
    return {
        "schema": "prophet.episode_earnings_detail/v1",
        "episode_ref": {
            "schema": "prophet.candidate_episode/v1",
            "episode_id": episode["episode_id"],
            "generation_id": generation,
            "identity_ref": episode["company_id"],
        },
        "source_projection_id": "piv:" + "1" * 64,
        "decision_cut": {
            "opened_at": episode["opened_at"],
            "opened_session": episode["opened_session"],
            "anchor_time": episode["opened_at"],
            "known_at": episode["opened_at"],
            "tradable_at": {
                "state": "NOT_ASSERTED", "value": None,
                "basis": "no_us_availability_owner_and_b4_not_built",
            },
        },
        "time_interpretation": "ORIGINAL_SOURCE_VINTAGE_RECONSTRUCTION_NOT_ORIGINAL_RECOMMENDATION",
        "method_scope": "RETROSPECTIVE_FACTUAL_RECONSTRUCTION_NO_AS_RUN_PROMOTION",
        "is_original_as_run_recommendation": False,
        "coverage": {"state": "COVERED", "basis": "owner_fixture"},
        "headline": "Revenue improved against the comparable prior-year period",
        "interpretation": "Reported operating evidence; not a forecast or permission to buy.",
        "comparison_state": "COMPARABLE_REPORTED_CHANGE_BOUND",
        "current_observations": [],
        "dossier": None,
        "evidence_brief": None,
        "missing": [
            "QUALIFIED_PRE_RELEASE_EXPECTATION",
            "MATCHED_FORECAST_REVISIONS",
            "CURRENT_ENTRY_AND_MARKET_PERMISSION",
        ],
        "authority": {
            "rank": False, "entry": False, "size": False,
            "execution": False, "trade": False,
        },
    }


def test_programmatic_builder_refuses_earnings_without_verified_native_owner(owner_repo):
    repo, recovery_ref, _ = owner_repo
    context_ref = _commit_current_context(repo)
    module = builder()
    base = module.build_view(
        recovery_ref, "2026-10-02", repo_root=repo, context_ref=context_ref)
    detail = _minimal_earnings_detail(base)
    episode_id = base["rows"][0]["current_context"]["episode"]["episode_id"]
    result = module.build_view(
        recovery_ref, "2026-10-02", repo_root=repo, context_ref=context_ref,
        earnings_details={episode_id: detail})
    earnings = result["rows"][0]["current_context"]["earnings"]
    assert earnings == {"status": "REFUSED", "reason": "EARNINGS_EPISODE_GENERATION_UNVERIFIED"}
    assert result["rows"][0]["legacy_alpha"] == 2.0
    assert result["current_context"]["earnings"]["mode"] == "EXISTING_OWNER_OUTPUT_ONLY"
    assert result["current_context"]["sources"]["issuer_master"]["read_status"] == "UNAVAILABLE"


def test_cli_has_no_earnings_network_or_source_discovery_option():
    source = Path(builder().__file__).read_text()
    assert "--earnings-url" not in source
    assert "--earnings-event" not in source
    assert "find_current_event_id_for_company" not in source
    assert "read_event_source_revisions" not in source


def test_html_refuses_unverified_earnings_instead_of_showing_unsupported_facts(owner_repo):
    repo, recovery_ref, _ = owner_repo
    context_ref = _commit_current_context(repo)
    module = builder()
    base = module.build_view(
        recovery_ref, "2026-10-02", repo_root=repo, context_ref=context_ref)
    episode_id = base["rows"][0]["current_context"]["episode"]["episode_id"]
    detail = _minimal_earnings_detail(base)
    view = module.build_view(
        recovery_ref, "2026-10-02", repo_root=repo, context_ref=context_ref,
        earnings_details={episode_id: detail})
    html = module.render_html(view)
    assert "Earnings evidence withheld" in html
    assert "EARNINGS_EPISODE_GENERATION_UNVERIFIED" in html
    assert "Revenue improved against the comparable prior-year period" not in html
    assert "continuation probability: 0%" not in html.lower()
    assert "catalyst probability: 0%" not in html.lower()


def test_context_builder_attaches_leave_issuer_out_peer_context_without_reordering(owner_repo):
    repo, recovery_ref, _ = owner_repo
    context_ref = _commit_current_context(repo)
    result = builder().build_view(
        recovery_ref, "2026-10-02", repo_root=repo, context_ref=context_ref)
    assert [row["ticker"] for row in result["shortlist"]] == ["A", "B"]
    a = result["rows"][0]["current_context"]
    assert len(a["peer_groups"]) == 1
    peer = a["peer_groups"][0]
    assert peer["group_id"] == "theme-1"
    assert peer["legacy_alpha"]["independence_status"] == "UNAVAILABLE"
    assert peer["legacy_alpha"]["unknown_peer_identity"] == ["B"]
    assert peer["authority"]["rank"] is False
    assert result["current_context"]["peer_context"]["mode"] == "EXISTING_GROUP_FLOW_OBSERVATION_ONLY"


def test_html_peer_read_discloses_identity_incompleteness_instead_of_confirmation(owner_repo):
    repo, recovery_ref, _ = owner_repo
    context_ref = _commit_current_context(repo)
    module = builder()
    html = module.render_html(module.build_view(
        recovery_ref, "2026-10-02", repo_root=repo, context_ref=context_ref))
    assert "Independent peer read" in html
    assert "Alpha peer measurement" in html
    assert "RS peer measurement" in html
    assert "unavailable" in html
    assert "Unknown issuer identities:" in html
    assert "observed independent peers" in html
    assert "Current membership; not historical PIT proof" in html
    assert "Peer-confirmed buy" not in html


def test_context_builder_adds_descriptive_group_leadership_board(owner_repo):
    repo, recovery_ref, _ = owner_repo
    context_ref = _commit_current_context(repo)
    result = builder().build_view(
        recovery_ref, "2026-10-02", repo_root=repo, context_ref=context_ref)
    groups = result["current_context"]["group_leadership"]
    assert len(groups) == 1
    group = groups[0]
    assert group["group_id"] == "theme-1"
    assert group["top_legacy_alpha"] == [
        {"ticker": "A", "value": 2.0},
        {"ticker": "B", "value": 1.0},
    ]
    assert group["top_legacy_rs"] == [
        {"ticker": "A", "value": 99.0},
        {"ticker": "B", "value": 80.0},
    ]
    assert group["authority"]["rank"] is False


def test_html_group_map_surfaces_recovered_alpha_and_rs_leaders_without_score(owner_repo):
    repo, recovery_ref, _ = owner_repo
    context_ref = _commit_current_context(repo)
    module = builder()
    html = module.render_html(module.build_view(
        recovery_ref, "2026-10-02", repo_root=repo, context_ref=context_ref))
    assert "Recovered Alpha leaders" in html
    assert "Recovered RS leaders" in html
    assert "A · +2.00" in html
    assert "B · +1.00" in html
    assert "A · 99" in html
    assert "Descriptive order only" in html
    assert "Group conviction score" not in html


def test_context_builder_surfaces_live_entry_radar_source_blocker_without_guessing_catalyst(owner_repo):
    repo, recovery_ref, _ = owner_repo
    context_ref = _commit_current_context(repo)
    result = builder().build_view(
        recovery_ref, "2026-10-02", repo_root=repo, context_ref=context_ref)
    global_state = result["current_context"]["catalyst"]
    assert global_state["status"] == "UNAVAILABLE_LIVE_ENTRY_RADAR_SOURCE"
    assert global_state["owner_state"] == "WAITING_FOR_LIVE_SOURCE"
    assert global_state["catalyst_probability"] is None
    assert global_state["prophet_episode_substitution_allowed"] is False
    row = result["rows"][0]["current_context"]["catalyst"]
    assert row["reason"] == "LIVE_ENTRY_RADAR_LIVE_EPISODE_SOURCE_NOT_AVAILABLE"
    assert row["catalyst_probability"] is None
    assert result["current_context"]["sources"]["entry_radar_ledger"]["read_status"] == "READ"


def test_html_catalyst_lane_shows_owner_blocker_and_no_absence_inference(owner_repo):
    repo, recovery_ref, _ = owner_repo
    context_ref = _commit_current_context(repo)
    module = builder()
    html = module.render_html(module.build_view(
        recovery_ref, "2026-10-02", repo_root=repo, context_ref=context_ref))
    assert "Catalyst coverage" in html
    assert "Live Entry Radar is waiting for its live source" in html
    assert "Missing coverage is not evidence that no catalyst exists" in html
    assert "Prophet episode is not substituted for a Radar LiveEpisode" in html
    assert "Catalyst probability 0%" not in html


def test_blob_receipt_matches_git_object_identity(owner_repo):
    repo, ref, _ = owner_repo
    view = builder().build_view(ref, '2026-10-02', repo_root=repo)
    for receipt in view['sources'].values():
        actual = subprocess.check_output(
            ['git', '-C', str(repo), 'rev-parse', f"{ref}:{receipt['path']}"], text=True).strip()
        assert receipt['git_blob'] == actual


def test_recovery_ignores_no_earnings_silently_without_context(owner_repo):
    repo, ref, _ = owner_repo
    with pytest.raises(ValueError, match='context'):
        builder().build_view(ref, '2026-10-02', repo_root=repo, earnings_details={})


def test_duplicate_json_keys_cannot_silently_replace_alpha_observations(owner_repo):
    repo, ref, _ = owner_repo
    path = repo / 'site/factordata/alpha.json'
    path.write_text('{"as_of":"2026-10-02","per_ticker":{"A":{"alpha":1},"A":{"alpha":99}}}')
    subprocess.run(['git', '-C', str(repo), 'add', 'site/factordata/alpha.json'], check=True)
    subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Fixture', '-c',
                    'user.email=fixture@example.invalid', '-c', 'core.hooksPath=/dev/null',
                    'commit', '-qm', 'Duplicate observation fixture'], check=True)
    ref = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    with pytest.raises(ValueError, match='source'):
        builder().build_view(ref, '2026-10-02', repo_root=repo)


def test_real_episode_review_html_is_excluded_from_public_source_commits():
    # Macro may be public. A local review artifact with native episode context
    # must not ride along with a future all-current-changes source commit.
    for name in ('leadership_lab.html', 'leadership_lab_20261006.html'):
        path = f'research/leadership_alpha_rs/evidence/{name}'
        check = subprocess.run(['git', '-C', str(ROOT), 'check-ignore', '--no-index', '-q', path])
        assert check.returncode == 0, f'review-only HTML is committable: {path}'


def test_sanitized_reproduction_receipts_remain_committable():
    path = 'research/leadership_alpha_rs/evidence/browser_receipt_20261006.json'
    check = subprocess.run(['git', '-C', str(ROOT), 'check-ignore', '--no-index', '-q', path])
    assert check.returncode == 1


def test_html_peer_deltas_render_missing_measurements_as_unavailable(owner_repo):
    repo, recovery_ref, _ = owner_repo
    context_ref = _commit_current_context(repo)
    module = builder()
    view = module.build_view(
        recovery_ref, "2026-10-02", repo_root=repo, context_ref=context_ref)
    peer = {
        "group_id": "theme-1",
        "name": "Theme One",
        "category": "Theme",
        "membership_basis": "RECOVERED_SOURCE_MEMBERSHIP_NOT_PIT_QUALIFIED",
        "historical_membership_qualified": False,
        "identity_basis": "CURRENT_PROPHET_EPISODE_COMPANY_ID_NOT_HISTORICAL",
        "legacy_alpha": {
            "state": "AVAILABLE", "independence_status": "AVAILABLE",
            "peer_denominator": 1, "observed_independent_peers": 1,
            "missing_market_observation": [], "unknown_peer_identity": [],
            "excluded_same_issuer": ["A"], "peer_median": 1.0,
            "focal_value": 2.0, "focal_minus_peer_median": 1.0,
        },
        "legacy_rs": {
            "state": "UNAVAILABLE", "independence_status": "AVAILABLE",
            "peer_denominator": 1, "observed_independent_peers": 0,
            "missing_market_observation": ["B"], "unknown_peer_identity": [],
            "excluded_same_issuer": ["A"], "peer_median": None,
            "focal_value": 99.0, "focal_minus_peer_median": None,
        },
        "authority": {
            "rank": False, "entry": False, "size": False,
            "execution": False, "trade": False,
        },
    }
    view["shortlist"][0]["current_context"]["peer_groups"] = [peer]
    html = module.render_html(view)
    assert "Alpha vs peer median" in html
    assert "+1.00" in html
    assert "RS vs peer median" in html
    assert "—" in html
    assert "missing peer observations" in html


def test_synthetic_qualified_owner_fixture_can_render_earnings_evidence_without_authority(owner_repo):
    # This is a template/unit fixture, NOT historical identity or source proof.
    from lib.dataos.identity import IssuerMaster
    from engine.leadership_lab.earnings import attach_earnings_evidence
    repo, recovery_ref, _ = owner_repo
    context_ref = _commit_current_context(repo)
    module = builder()
    view = module.build_view(
        recovery_ref, "2026-10-02", repo_root=repo, context_ref=context_ref)
    episode = view["rows"][0]["current_context"]["episode"]
    episode_id = episode["episode_id"]
    view["current_context"]["episode_book"]["source_validation"] = {
        "status": "VALIDATED_CANONICAL_OWNER",
    }
    native = IssuerMaster.from_records([{
        "security_id": episode["security_id"],
        "issuer_id": episode["company_id"],
        "issuer_cik": "0000001234",
        "issuer_state": "RESOLVED",
        "security_state": None,
        "listing_key": "US-XNAS-A",
    }])
    output = attach_earnings_evidence(
        view, {episode_id: _minimal_earnings_detail(view)}, issuer_master=native)
    assert output["rows"][0]["current_context"]["earnings"]["status"] == "AVAILABLE"
    html = module.render_html(output)
    assert "Business evidence" in html
    assert "Revenue improved against the comparable prior-year period" in html
    assert "Pre-release expectation baseline" in html
    assert "No continuation, catalyst, or re-rating probability is established" in html
    assert "Current entry / market permission" in html
