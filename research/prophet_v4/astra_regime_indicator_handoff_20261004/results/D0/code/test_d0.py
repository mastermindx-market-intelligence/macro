"""D0 invariants named under NOT DONE UNLESS."""
from __future__ import annotations

import json
from pathlib import Path

import pyarrow.parquet as pq

import pandas as pd

from census import (
    CENSUS_READ_TARGETS,
    CONTEXT_HISTORY_FIRST_WRITE,
    GREP_ONLY_NAMED_PATHS,
    MIN_ROWS,
    PIT_CLASSES,
    VERDICTS,
    YEARS,
    build_payload,
    dump_payload,
    find_root,
    honest_in_force_names,
    iso_day,
    load_snapshot_names,
    load_tree_members_by_asof,
    load_universe,
    parse_company_ticker,
    results_dir,
    tree_pit_class_reason_from_commits,
)


_CACHED = None


def _payload():
    global _CACHED
    if _CACHED is None:
        _CACHED = build_payload(find_root())
    return _CACHED


def test_required_keys_present():
    payload = _payload()
    for key in (
        "lane",
        "status",
        "verdict",
        "universe_n",
        "sources",
        "leadership_artifacts",
        "repo_claims",
        "repo_head",
        "hashes_file",
    ):
        assert key in payload
    assert payload["lane"] == "D0"
    assert payload["hashes_file"] == "hashes.txt"
    assert payload["repo_head"]
    assert len(payload["repo_head"]) == 40


def test_verdict_is_one_token():
    payload = _payload()
    assert payload["verdict"] in VERDICTS


def test_coverage_by_year_has_all_13_years_for_every_source():
    payload = _payload()
    assert payload["sources"], "no sources"
    for src in payload["sources"]:
        years = list(src["coverage_by_year"].keys())
        assert years == YEARS, f"{src['name']} years={years}"
        for y, val in src["coverage_by_year"].items():
            assert isinstance(val, float)
            assert 0.0 <= val <= 1.0, f"{src['name']} {y}={val}"
        assert 0.0 <= src["universe_coverage_ever"] <= 1.0


def test_every_source_cites_path_and_date_field():
    payload = _payload()
    for src in payload["sources"]:
        assert src["path"], src["name"]
        assert src["date_field"], src["name"]
        assert src["pit_class"] in PIT_CLASSES, src["name"]
        assert src["grain"], src["name"]
        assert isinstance(src["n_tickers"], int)
        assert isinstance(src["n_themes"], int)


def test_universe_excludes_names_under_800_rows():
    root = find_root()
    payload = _payload()
    n_ok = 0
    n_short = 0
    n_files = 0
    for path in (root / "data/baskets/ohlcv").glob("*.parquet"):
        n_files += 1
        n_rows = pq.ParquetFile(path).metadata.num_rows
        if n_rows >= MIN_ROWS:
            n_ok += 1
        else:
            n_short += 1
            assert n_rows < MIN_ROWS
    assert payload["universe_n"] == n_ok
    assert payload["universe_n_files"] == n_files
    assert payload["universe_n_excluded_short"] == n_short
    assert n_ok + n_short == n_files


def test_result_json_byte_identical_across_two_builds():
    root = find_root()
    a = build_payload(root)
    b = build_payload(root)
    ta = json.dumps(a, indent=2, ensure_ascii=False)
    tb = json.dumps(b, indent=2, ensure_ascii=False)
    assert ta == tb


def test_repo_claims_have_file_line_quote_and_matches_disk():
    payload = _payload()
    assert len(payload["repo_claims"]) >= 4
    for claim in payload["repo_claims"]:
        assert claim["file"]
        assert isinstance(claim["line"], int) and claim["line"] >= 1
        assert claim["quote"]
        assert isinstance(claim["matches_disk"], bool)


def test_leadership_artifacts_schema():
    payload = _payload()
    assert payload["leadership_artifacts"]
    for art in payload["leadership_artifacts"]:
        assert art["path"]
        assert art["grain"]
        assert art["pit_class"] in PIT_CLASSES
        assert "date_min" in art
        assert "date_max" in art


def test_q2_tree_history_nonzero_only_in_2026():
    """Honest-N check: tree membership dated before 2026 must be zero."""
    payload = _payload()
    tree = next(s for s in payload["sources"] if s["name"] == "themes_heatmap_tree_history")
    for y in YEARS:
        if y == "2026":
            assert tree["coverage_by_year"][y] > 0.0
        else:
            assert tree["coverage_by_year"][y] == 0.0
    assert tree["n_univ_tickers_ever"] > 0
    assert tree["n_univ_tickers_ever"] < payload["universe_n"]


def test_dump_roundtrip_stable(tmp_path: Path):
    payload = _payload()
    p1 = tmp_path / "a.json"
    p2 = tmp_path / "b.json"
    dump_payload(payload, p1)
    dump_payload(payload, p2)
    assert p1.read_bytes() == p2.read_bytes()


def test_honest_window_computed_once_and_used_for_verdict():
    payload = _payload()
    hw = payload["honest_window"]
    vd = payload["verdict_detail"]
    assert hw["start"] == vd["honest_window_start"]
    assert hw["end"] == vd["honest_window_end"]
    assert hw["start"] and len(hw["start"]) == 10
    assert hw["rule"]
    assert "min(" in hw["rule"] or "earliest date" in hw["rule"]
    assert hw["grading_metric"] == "min_per_date_from_honest_start"
    assert "union_max_ever" in hw
    assert hw["min_per_date_from_honest_start"] <= hw["union_max_ever"]
    assert payload["verdict"] == hw.get("verdict", payload["verdict"])
    assert payload["verdict"] == "PIT_PARTIAL"
    rendered = __import__("census").render_result_md(payload)
    assert hw["start"] in rendered
    assert rendered.split("honest window is **", 1)[1].startswith(hw["start"])


def test_edges_belief_time_sub_sources_and_per_date_clocks():
    payload = _payload()
    edges = next(s for s in payload["sources"] if s["name"] == "theme_graph_edges")
    subs = edges["sub_sources"]
    assert subs
    names = {s["name"] for s in subs}
    assert "raw_snapshot" in names
    raw = next(s for s in subs if s["name"] == "raw_snapshot")
    assert raw["pit_class"] == "BACKFILLED"
    assert raw["belief_time_min"] == raw["belief_time_max"]
    assert raw["n_rows"] > 0
    assert edges["per_date_belief_time"]
    assert edges["per_date_observed_evidence_time"]
    assert edges["headline_per_date_coverage"] <= edges["union_ever_coverage"]
    assert edges["headline_per_date_n"] <= edges["union_ever_n"]


def test_leading_theme_join_snapshot_honest_vs_added_backfilled():
    payload = _payload()
    join = payload["leading_theme_join"]
    assert join["n_theme_ids_matching_basket_ids"] == 49
    assert join["snapshot_date_pit_class"] == "PIT_HONEST"
    assert join["added_pit_class"] == "BACKFILLED"
    assert "engine/basket_membership_pit.py:16-18" in join["snapshot_date_cite"]
    assert "engine/basket_membership_pit.py:99" in join["snapshot_date_cite"]
    assert join["per_date"]
    honest_rows = [r for r in join["per_date"] if r["snapshot_date_used"]]
    assert honest_rows
    assert honest_rows[0]["date"] >= "2026-08-13"
    before = [r for r in join["per_date"] if r["date"] == "2026-08-07"]
    assert before
    assert before[0]["snapshot_honest_all49_n"] == 0
    assert before[0]["added_backfilled_all49_n"] > 0


def test_q4_matches_disk_has_command_and_is_bool():
    payload = _payload()
    assert len(payload["repo_claims"]) >= 8
    for claim in payload["repo_claims"]:
        assert claim["disk_command"]
        assert "python3" in claim["disk_command"]
        assert claim["disk_result"]
        assert isinstance(claim["matches_disk"], bool)


def test_tree_change_point_is_first_observed_date():
    payload = _payload()
    tree = next(s for s in payload["sources"] if s["name"] == "themes_heatmap_tree_history")
    cp = tree["change_point_semantics"]
    assert cp["semantics"] == "first_observed_date_of_new_state"
    assert cp["not"] == "recorded_transition_date"
    assert "local_sources.py" in cp["cite"]
    assert cp["example"]["n_added"] == 1
    assert cp["example"]["n_removed"] == 18
    quoted = {q["line"]: q["text"] for q in cp["quoted_lines"]}
    assert 8 in quoted and "asof(i)" in quoted[8]
    assert 16 in quoted and "FIRST OBSERVED" in quoted[16]


def test_honest_change_points_pinned():
    hw = _payload()["honest_window"]
    assert hw["start"] == "2026-07-05"
    by = {r["date"]: r["n_univ_tickers"] for r in hw["change_points"]}
    assert by["2026-07-05"] == 660
    assert by["2026-08-13"] == 933
    assert by["2026-08-15"] == 932
    assert by["2026-08-18"] == 931
    assert by["2026-09-04"] == 932


def test_d_star_is_exactly_2026_07_05():
    payload = _payload()
    hw = payload["honest_window"]
    assert hw["start"] == "2026-07-05"
    edges = next(s for s in payload["sources"] if s["name"] == "theme_graph_edges")
    obs = [r["date"] for r in edges.get("per_date_observed_evidence_time") or []]
    assert obs
    assert hw["start"] != min(obs)


def test_in_force_from_tree_and_snapshot_only():
    root = find_root()
    payload = _payload()
    hw = payload["honest_window"]
    assert hw["in_force_sources"] == [
        "tree_history.asof",
        "membership_history.snapshot_date",
    ]
    assert "membership_history.added" not in hw["in_force_sources"]
    assert "theme_graph_edges" not in hw["in_force_sources"]
    universe = set(load_universe(root)[0])
    tree_members = load_tree_members_by_asof(root)
    snap_names = load_snapshot_names(root)
    mh = pd.read_parquet(root / "data/baskets/membership_history.parquet")
    added_pairs = []
    for t, a in zip(mh["ticker"].tolist(), mh["added"].tolist()):
        day = iso_day(a)
        if day:
            added_pairs.append((str(t).upper(), day))
    edges = pd.read_parquet(root / "data/theme_graph/edges.parquet")
    us = edges[(edges["type"] == "MEMBER_OF") & edges["src"].astype(str).str.startswith("co:us:")].copy()
    us["ticker"] = us["src"].map(parse_company_ticker)
    for cp in hw["change_points"]:
        d = cp["date"]
        names = honest_in_force_names(d, universe, tree_members, snap_names)
        assert len(names) == cp["n_univ_tickers"]
        t_el = [a for a in sorted(tree_members) if a <= d]
        s_el = [a for a in sorted(snap_names) if a <= d]
        tree_at = (tree_members[t_el[-1]] & universe) if t_el else set()
        snap_at = (snap_names[s_el[-1]] & universe) if s_el else set()
        assert names == (tree_at | snap_at)
        added_le = {t for t, a in added_pairs if a <= d} & universe
        added_only = added_le - tree_at - snap_at
        assert names.isdisjoint(added_only)
        edges_le = set()
        for t, et in zip(us["ticker"].tolist(), us["evidence_time"].tolist()):
            day = iso_day(et)
            if t and day and day <= d and t in universe:
                edges_le.add(t)
        edges_only = edges_le - tree_at - snap_at
        assert names.isdisjoint(edges_only)


def test_iso_weeks_33_to_40_present():
    weeks = _payload()["leading_theme_join"]["iso_week_leading_restricted"]
    assert [w["iso_week"] for w in weeks] == list(range(33, 41))
    for w in weeks:
        assert "dates" in w
        assert "min_leading_n" in w
        assert "max_leading_n" in w
        assert "status" in w


def test_iso_week_33_marked_before_honest_start():
    join = _payload()["leading_theme_join"]
    weeks = join["iso_week_leading_restricted"]
    w33 = next(w for w in weeks if w["iso_week"] == 33)
    assert join["honest_start"] == "2026-08-13"
    assert "2026-08-12" in (w33.get("dates") or [])
    assert w33["status"] == "BEFORE_HONEST_START"
    assert w33["min_leading_n"] == 0
    w34 = next(w for w in weeks if w["iso_week"] == 34)
    assert w34["status"] == "HONEST"


def test_edges_clock_excluded_from_honest_series():
    edges = next(s for s in _payload()["sources"] if s["name"] == "theme_graph_edges")
    assert "BACKFILLED source" in edges["honest_clock"]
    assert "excluded from the honest series" in edges["honest_clock"]
    assert "cumulative-ever" in edges["per_date_in_force_semantics"]


def test_census_read_targets_cover_known_inputs():
    for rel in (
        "data/theme_graph/edges.parquet",
        "data/themes_heatmap/tree_history.jsonl",
        "data/baskets/membership_history.parquet",
        "engine/theme_graph/local_sources.py",
        "engine/basket_membership_pit.py",
        "contracts/biocatalyst/biocatalyst_theme_rollup_pit.v1.schema.json",
        "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/D0/gh_evidence.json",
    ):
        assert rel in CENSUS_READ_TARGETS


def test_tree_pit_class_reason_names_commit_evidence():
    tree = next(s for s in _payload()["sources"] if s["name"] == "themes_heatmap_tree_history")
    reason = tree["pit_class_reason"]
    assert "b35bac058e" in reason
    assert "00c7154781" in reason
    assert "2026-07-05T06:50:58Z" in reason
    assert "evidence unavailable" not in reason


def test_tree_pit_class_reason_unavailable_without_evidence():
    reason = tree_pit_class_reason_from_commits({"tree_history": {"ok": False, "commits": []}})
    assert "evidence unavailable" in reason
    assert "b35bac058e" not in reason
    empty = tree_pit_class_reason_from_commits(None)
    assert "evidence unavailable" in empty


def test_context_history_honest_start_is_first_write():
    payload = _payload()
    ctx = next(s for s in payload["sources"] if s["name"] == "themes_context_history")
    assert CONTEXT_HISTORY_FIRST_WRITE == "2026-07-19"
    assert ctx["honest_start"] == "2026-07-19"
    assert ctx["date_min"] == "2026-06-18"
    assert ctx["asof_classes"]["before_first_write"]["pit_class"] == "BACKFILLED"
    assert ctx["asof_classes"]["from_first_write"]["pit_class"] == "PIT_HONEST"
    assert ctx["honest_start_before_i1"] == "2026-06-18"
    i1 = payload["i1_context_history_honest_start"]
    assert i1["before"] == "2026-06-18"
    assert i1["after"] == "2026-07-19"


def test_matches_disk_derived_from_disk_result():
    payload = _payload()
    assert len(payload["repo_claims"]) >= 8
    for claim in payload["repo_claims"]:
        needles = claim["disk_match_needles"]
        derived = all(n in claim["disk_result"] for n in needles)
        assert claim["matches_disk"] is derived, claim["file"]
        assert claim["matches_disk"] is claim["matches_disk_inprocess"], (
            claim["file"],
            claim["disk_result"][:200],
        )


def test_repair_item_cites_contain_symbol():
    payload = _payload()
    import census as census_mod
    census_src = Path(census_mod.__file__).read_text(encoding="utf-8").splitlines()
    test_src = Path(__file__).read_text(encoding="utf-8").splitlines()
    n = 0
    for group in ("repair_items", "repair_items_round2", "repair_items_round3"):
        for item in payload[group]:
            found = list(__import__("re").finditer(r"(census\.py|test_d0\.py):(\d+)\s+(\S+)", item["where"]))
            assert found, item
            for m in found:
                file, line, symbol = m.group(1), int(m.group(2)), m.group(3).rstrip(";,")
                src = census_src if file == "census.py" else test_src
                assert 1 <= line <= len(src), (item["id"], file, line)
                assert symbol in src[line - 1], (item["id"], file, line, symbol, src[line - 1])
                n += 1
    assert n >= 20


def test_grep_only_paths_not_in_read_targets():
    for rel in GREP_ONLY_NAMED_PATHS:
        assert rel not in CENSUS_READ_TARGETS
    assert "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/D0/gh_evidence.json" in CENSUS_READ_TARGETS


def test_data_law_heading_in_render():
    rendered = __import__("census").render_result_md(_payload())
    assert "## Data law" in rendered
    assert rendered.split("\n")[8] == "## Data law" or "\n## Data law\n" in rendered
    assert "## Provenance" in rendered
    assert "## Repair items (round 3)" in rendered
