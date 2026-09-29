from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]


def _detail():
    from tests.test_dashboard_template_render import _env

    return _env().get_template("_prophet_setup_detail.html.j2").module


def _relation(book, error=False):
    from scripts.build_site import _plan_relations_for

    default, by_ticker = _plan_relations_for(book, error)
    return {
        "state": ("related_security" if by_ticker.get("LFUS") else default),
        "plans": by_ticker.get("LFUS", []),
    }


def _lfus_book():
    return {
        "plans": [
            {
                "id": "LFUS-CLOSED-20260801",
                "asset": " lfus ",
                "lifecycle_state": "resolved",
                "formation_date": "2026-08-05",
                "signal_date": "2026-08-10",
                "plan_asof": "2026-08-11",
                "closed": True,
            },
            {
                "id": "LFUS-BULL-20260810",
                "asset": "LFUS",
                "lifecycle_state": "entered",
                "formation_date": "2026-08-10",
                "signal_date": "2026-08-15",
                "plan_asof": "2026-08-16",
                "closed": False,
            },
        ]
    }


def test_plan_relation_pure_function_is_open_same_security_and_sorted():
    from scripts.build_site import _plan_relations_for

    default, by_ticker = _plan_relations_for(_lfus_book(), False)
    assert default == "none"
    assert list(by_ticker) == ["LFUS"]
    assert [plan["id"] for plan in by_ticker["LFUS"]] == ["LFUS-BULL-20260810"]
    assert by_ticker["LFUS"][0] == {
        "id": "LFUS-BULL-20260810",
        "lifecycle_state": "entered",
        "formation_date": "2026-08-10",
        "signal_date": "2026-08-15",
        "plan_asof": "2026-08-16",
    }
    assert _plan_relations_for(None, True)[0] == "unknown"
    assert _plan_relations_for({}, False) == ("none", {})


def test_plan_relation_sorts_multiple_open_plans_and_matches_normalized_tickers():
    from scripts.build_site import _plan_relations_for

    book = {"plans": [
        {"id": "AAA-EARLY", "asset": " aa ", "closed": False, "formation_date": "2026-08-01"},
        {"id": "AAA-LATE-B", "asset": "AA", "closed": False, "formation_date": "2026-08-10"},
        {"id": "AAA-LATE-A", "asset": "aA", "closed": False, "formation_date": "2026-08-10"},
    ]}
    default, by_ticker = _plan_relations_for(book)
    assert default == "none"
    assert list(by_ticker) == ["AA"]
    assert [plan["id"] for plan in by_ticker["AA"]] == [
        "AAA-LATE-B", "AAA-LATE-A", "AAA-EARLY"]


def test_missing_plan_book_is_unknown_and_presenters_render_none_without_a_match():
    from scripts.build_site import _plan_relations_for
    from tests.test_dashboard_template_render import _env

    assert _plan_relations_for(None, False)[0] == "unknown"

    env = _env()
    row = {"ticker": "AAA", "name": "AAA", "sector": "Industrials"}
    relation = {"state": "none", "plans": []}
    by_ticker = {"BBB": relation["plans"]}
    pool = env.get_template("_us_candidate_pool_rows.html.j2").render(
        rows=[row], plan_rel=relation, plan_rel_by_ticker=by_ticker)
    board = env.get_template("_us_board_cards.html.j2").render(
        items=[row], sg_any=False, bs_adj=False, xu_allfeat=False, trg_map={},
        rw_en="", rw_zh="", plan_rel=relation, plan_rel_by_ticker=by_ticker)
    assert 'data-plan-relation="none"' in pool
    assert 'data-plan-relation="none"' in board


def test_setup_detail_reuses_the_existing_plan_lifecycle_vocabulary():
    setup = (ROOT / "templates" / "_prophet_setup_detail.html.j2").read_text(encoding="utf-8")
    plan_cards = (ROOT / "templates" / "_us_prophet_plan_cards.html.j2").read_text(encoding="utf-8")
    assert "{% from '_us_prophet_plan_cards.html.j2' import life_label_en, life_label_zh %}" in setup
    assert "_LIFE_LABEL_EN" not in setup
    assert "_LIFE_LABEL_ZH" not in setup
    assert "{% macro life_label_en(code) -%}" in plan_cards
    assert "{% macro life_label_zh(code) -%}" in plan_cards


def test_setup_detail_renders_related_security_record():
    html = str(_detail().body({"ticker": "LFUS"}, "board", "2026-09-24", _relation(_lfus_book())))
    soup = BeautifulSoup(html, "html.parser")
    section = soup.select_one(".pvs-plan-relation")
    assert section["data-plan-relation"] == "related_security"
    assert section["data-plan-exact"] == "unavailable"
    assert section.select_one("h3").get_text(" ", strip=True) == "Related model record 相关模型记录"
    records = section.select(".pvs-plan-rec")
    assert len(records) == 1
    assert records[0]["data-plan-id"] == "LFUS-BULL-20260810"
    assert records[0]["data-plan-lifecycle"] == "entered"
    assert "Entered" in records[0].get_text(" ", strip=True)
    assert "入场" in records[0].get_text(" ", strip=True)
    assert "Formed 形成于 2026-08-10" in records[0].get_text(" ", strip=True)
    assert "Signal date 信号日期 2026-08-15" in records[0].get_text(" ", strip=True)
    assert "Plan as of 计划截至 2026-08-16" in records[0].get_text(" ", strip=True)
    button = records[0].select_one(".pvs-plan-link")
    assert button["data-pvs-plan-target"] == "pv-LFUS-BULL-20260810"
    text = section.get_text(" ", strip=True)
    assert "It is not this candidate's plan and not a position you hold." in text
    assert "这是同一证券的模型记录，不是此候选的计划，也不是您持有的仓位。" in text
    assert "Exact plan relation: not available from the source." in text
    assert "精确计划关联：来源未提供。" in text


def test_setup_detail_renders_none_wrong_ticker_and_unknown_states():
    module = _detail()
    other_only = {"plans": [{"id": "BBB-BULL-20260801", "asset": "BBB", "closed": False,
                             "lifecycle_state": "watch", "formation_date": "2026-08-01"}]}
    none = BeautifulSoup(str(module.body({"ticker": "AAA"}, "board", None, _relation(other_only))),
                         "html.parser").select_one(".pvs-plan-relation")
    assert none["data-plan-relation"] == "none"
    assert "No model plan is linked to this candidate." in none.get_text(" ", strip=True)
    assert "此候选暂无关联的模型计划，不在此创建计划或持仓。" in none.get_text(" ", strip=True)
    assert not none.select(".pvs-plan-rec")

    unknown = BeautifulSoup(str(module.body({"ticker": "AAA"}, "board", None, _relation(None, True))),
                            "html.parser").select_one(".pvs-plan-relation")
    assert unknown["data-plan-relation"] == "unknown"
    assert "Plan records could not be read for this candidate." in unknown.get_text(" ", strip=True)
    assert "无法读取此候选的计划记录。" in unknown.get_text(" ", strip=True)


def test_three_presenters_render_the_same_plan_relation_body():
    from tests.test_dashboard_template_render import _env

    env = _env()
    relation = _relation(_lfus_book())
    row = {"ticker": " lfus ", "name": "LFUS", "sector": "Industrials"}
    module = env.get_template("_prophet_setup_detail.html.j2").module
    expected = str(module.body(row, "pool", None, relation))
    pool = env.get_template("_us_candidate_pool_rows.html.j2").render(
        rows=[dict(row, lane_reasons=["cleared_admission"])], plan_rel=relation,
        plan_rel_by_ticker={"LFUS": relation["plans"]})
    board = env.get_template("_us_board_cards.html.j2").render(
        items=[row], sg_any=False, bs_adj=False, xu_allfeat=False, trg_map={}, rw_en="", rw_zh="",
        plan_rel=relation, plan_rel_by_ticker={"LFUS": relation["plans"]})
    table = str(module.table_action(row, None, plan_rel=relation))
    rendered = [BeautifulSoup(fragment, "html.parser").select_one(".pvs-plan-relation") for fragment in
                (expected, pool, board, table)]
    normalized = [" ".join(str(node).split()) for node in rendered]
    assert normalized[0] == normalized[1] == normalized[2] == normalized[3]


def test_dashboard_has_delegated_plan_link_handler_without_pool_state_writes():
    source = (ROOT / "templates" / "dashboard.html.j2").read_text(encoding="utf-8")
    match = re.search(r"document\.addEventListener\('click', function\(event\)\{.*?pvsPlanLinkResult='ok'.*?\}\);", source, re.S)
    assert match, "delegated plan-link handler is missing"
    handler = match.group(0)
    for expected in (
        "pv-setup-dialog", ".pvs-close", "USProphetSource.set('plans')",
        "document.getElementById(target)", "pvsPlanLinkResult='missing'",
        "sm-hidden", "sm-reveal", "scrollIntoView", "focus({preventScroll:true})",
        "setAttribute('tabindex','-1')", "pvsPlanLinkResult='ok'"):
        assert expected in handler
    assert "createElement" not in handler
    assert "us-candidate-pool" not in handler
    assert "ucp-" not in handler


def test_evidence_manifest_is_bound_to_the_checked_out_head():
    import json
    import subprocess

    manifest = json.loads(
        (ROOT / "mockups/evidence/pri_ui_c1/manifest.json").read_text(encoding="utf-8"))
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, cwd=ROOT).strip()
    target = manifest["target"]
    assert target["resolved_sha_or_none"] == head
    assert target["resolved_sha_source"] == f"git directory at {target['resolved_gitdir_or_none']}"


def test_plan_relation_preserves_existing_machine_attribute_sets():
    module = _detail()
    row = {"ticker": "LFUS", "entry_signal": {"status": "wait", "headline": "Wait"},
           "signal": {}, "hold": {}}
    attrs = ("data-reason", "data-entry-status", "data-native-id", "data-setup-kind", "data-source-field")
    before = str(module.body(row, "board", None))
    after = str(module.body(row, "board", None, _relation(_lfus_book())))
    extracted = []
    for html in (before, after):
        values = {name: sorted(re.findall(rf'{name}="([^"]*)"', html)) for name in attrs}
        extracted.append(values)
    assert extracted[0] == extracted[1]
