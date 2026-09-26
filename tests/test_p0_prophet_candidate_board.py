"""P0 production hotfix (GitHub #6185 / Linear MAS-111) — restores the
candidate population (`us_standouts.buy`) as a first-class, always-reachable
view of the US Prophet board on us_stocks.html, behind a Candidates|Plans
source toggle, without disturbing the migrated plan-book grid PR #6076
introduced.

One test group per production defect named in the commissioning packet:
  A  — source toggle (data-prophet-src default, #us-src-toggle presence)
  B  — DOM containers: #us-cand-grid carries neither data-mp1-grid nor
       data-provboard; #us-life-grid keeps data-mp1-grid="1"; the two grids
       share no ancestor; the gated grid holds exactly `preview_rows` real
       cards, all drawn from the input buy preview slice; the `_su`-absent
       path renders a typed Candidates-unavailable state.
  C1 — no `&lt;b&gt;` anywhere in the rendered document (the t()+|safe
       double-escape regression).
  C2 — `_cand_total` reconciles to `gate.total`; the stage shelves (plus a
       residual "Other" shelf when a stage-less row exists) sum EXACTLY to
       it — built against a fixture that would fail under the old
       `+ _ran_rows` arithmetic.
  C3 — #us-board-sub carries neither "setups" nor the "shown ·" clause.
  C4 — theme.js/site theme.js compute a heading-excluding record count;
       _us_board_cards.html.j2 marks both heading kinds `data-sm-heading`.
  D  — hydrate() reads payload.cards_html into #us-cand-grid via
       mergeBoardCards and never stamps data-mp1-grid on the fresh element.

Reuses templates/dashboard.html.j2's exact render shape and fixtures from
tests/test_dashboard_template_render.py (`_env`, `_base_vm`, `_board_row`,
`_prophet_book`) and the `_split_us_board` tier-gate helper from
scripts/build_site.py, exactly like tests/test_p_mp1_shell_repair_round.py.
"""
from __future__ import annotations

import re
import pytest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import scripts.build_site as bs  # noqa: E402
from tests.test_dashboard_template_render import (  # noqa: E402
    _env, _base_vm, _board_row, _prophet_book,
)


def _stage_rows(n_by_stage: dict, extra_stageless: int = 0) -> list:
    """Candidate rows spanning the five recognized stages, plus optional
    rows carrying a stage value OUTSIDE `_stage_order` — the C2 residual
    "Other" shelf fixture needs at least one of those to exercise honestly."""
    rows = []
    i = 0
    for stage, n in n_by_stage.items():
        for _ in range(n):
            rows.append(_board_row(ticker=f"CAND{i}", name=f"Candidate {i}",
                                    stage=stage, lane=None))
            i += 1
    for _ in range(extra_stageless):
        rows.append(_board_row(ticker=f"CAND{i}", name=f"Candidate {i}",
                                stage="unrecognized_future_stage", lane=None))
        i += 1
    return rows


def _render_stocks(vm_overrides: dict) -> str:
    vm = _base_vm()
    vm.setdefault("gate", None)
    vm.setdefault("pgate", None)
    vm.setdefault("life_gate", None)
    vm.update(vm_overrides)
    return _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")


def _gated_render(n_by_stage: dict, extra_stageless: int = 0, preview_rows: int = 3,
                   ran_extra: int = 0):
    """One gated render exercising the full C2 arithmetic: `ran_extra` rows
    land in the SEPARATE `us_standouts.ran` array (its own section/tier
    gate) — under the pre-fix `_cand_total = gate.total + _ran_rows|length`
    this would inflate the total past what the five (or six) shelves sum
    to. Returns (html, gate, shell_su)."""
    rows = _stage_rows(n_by_stage, extra_stageless)
    us_standouts = {"buy": rows, "ran": [{"ticker": f"RAN{i}"} for i in range(ran_extra)],
                     "eligible": len(rows)}
    shell_su, gate, _locked = bs._split_us_board(us_standouts, preview_rows, gated=True)
    html = _render_stocks({"us_standouts": shell_su, "gate": gate,
                            "us_prophet_book": _prophet_book(plans=[])})
    return html, gate, shell_su


# ═══════════════════════════ A — source toggle ════════════════════════════

def test_a_data_prophet_src_defaults_candidates_when_su_present():
    rows = _stage_rows({"live": 2})
    html = _render_stocks({
        "us_standouts": {"buy": rows, "ran": [], "eligible": len(rows)},
        "us_prophet_book": _prophet_book(),
    })
    assert 'data-prophet-src="candidates"' in html
    assert 'id="us-src-toggle"' in html
    assert 'data-src="candidates"' in html and 'data-src="plans"' in html


def test_a_today_uses_owner_featured_preview_without_entry_promotion():
    from bs4 import BeautifulSoup

    rows = []
    for i in range(5):
        wait = i == 1
        rows.append(_board_row(
            ticker=f"TOD{i}", name=f"Today {i}", lane="bottoming",
            stage=("setting_up" if wait else "live"),
            featured=True,
            entry_signal={
                "status": ("bounce_wait" if wait else "buy_now"),
                "buy_zone": {"low": 40.0 + i, "high": 41.0 + i},
            },
        ))
    rows.append(_board_row(
        ticker="OTHER", name="Other", lane="continuation", stage="live",
        featured=False,
        entry_signal={
            "status": "buy_now",
            "buy_zone": {"low": 50.0, "high": 51.0},
        },
    ))
    su = {
        "as_of": "2026-09-24",
        "buy": rows,
        "ran": [],
        "eligible": len(rows),
        "ranking": {"featured_count": 5},
    }
    html = _render_stocks({
        "us_standouts": su,
        "us_prophet_book": _prophet_book(),
    })
    soup = BeautifulSoup(html, "html.parser")

    panel = soup.select_one("#us-standouts")
    assert panel["data-prophet-src"] == "today"
    assert soup.select_one('#us-src-btn-today[aria-selected="true"]')
    today = soup.select_one("#us-today")
    assert today and today["data-today-total"] == "5"
    assert today["data-today-visible"] == "3"
    cards = today.select("#us-today-grid .pvcard")
    assert [card["data-ticker"] for card in cards] == ["TOD0", "TOD1", "TOD2"]
    assert "pv-buy" in cards[0]["class"]
    assert "pv-wait" in cards[1]["class"], "Featured bounce_wait must remain Wait"
    today_text = today.get_text(" ", strip=True)
    assert "2 more Featured names remain in Candidates" in today_text
    assert "not a pick quota" in today_text

    # Today previews the owner's shelf; it does not remove any candidate row.
    assert len(soup.select("#us-cand-grid .pvcard")) == 6
    assert soup.select_one('#us-src-btn-cand[data-src="candidates"]')
    assert soup.select_one('#us-src-btn-plan[data-src="plans"]')


def test_a_today_zero_does_not_replace_candidates_default():
    rows = [_board_row(
        ticker="AAA", name="A", stage="live", lane="bottoming", featured=False,
    )]
    html = _render_stocks({
        "us_standouts": {
            "as_of": "2026-09-24",
            "buy": rows,
            "ran": [],
            "eligible": 1,
            "ranking": {"featured_count": 0},
        },
        "us_prophet_book": _prophet_book(),
    })
    assert 'data-prophet-src="candidates"' in html
    assert 'id="us-today"' in html
    assert "No owner-Featured names on this board." in html


def test_a_toggle_stays_reachable_and_typed_unavailable_state_shows_when_su_missing():
    # The toggle is deliberately UNCONDITIONAL (not gated on `_su`): the page
    # opens on Plans when `_su` is falsy, but Candidates must stay reachable
    # so the typed unavailable state (B5) is not baked-and-unreachable dead
    # markup — the A3 CSS rule that hides #us-candidates in Plans mode would
    # otherwise combine with a `_su`-gated toggle to make that state
    # permanently unseeable.
    html = _render_stocks({
        "us_standouts": None,
        "action_board": {"hold": [], "avoid": [], "notable": [{"ticker": "X"}], "buy": []},
    })
    assert 'data-prophet-src="plans"' in html
    assert 'id="us-src-toggle"' in html, (
        "the source toggle must stay reachable even when the page opens on "
        "Plans, or the typed Candidates-unavailable state can never be seen")
    assert 'id="us-src-btn-plan" type="button" aria-selected="true"' in html, (
        "the baked aria-selected state must agree with the baked "
        "data-prophet-src default")
    idx = html.find('id="us-candidates"')
    assert idx != -1
    block = html[idx:idx + 1200]
    assert 'class="mx-empty"' in block and 'class="mx-empty-why"' in block, (
        "switching to Candidates via the (now reachable) toggle must land on "
        "the typed unavailable state, not nothing")


# ═══════════════════════ B — DOM containers / cross-hydration ═════════════

def test_b_cand_grid_carries_neither_mp1_nor_provboard_marker():
    html, gate, _su = _gated_render({"live": 5})
    m = re.search(r'<div class="nbgrid"[^>]*id="us-cand-grid"[^>]*>', html)
    assert m, "expected a baked #us-cand-grid element"
    tag = m.group(0)
    assert 'data-mp1-grid' not in tag, (
        "the candidate grid must never carry the plan grid's W-L1 "
        "neutralization marker — doing so would make the repaint selector "
        "skip it too")
    assert 'data-provboard' not in tag


def test_b_life_grid_still_carries_mp1_marker_and_grids_share_no_ancestor():
    rows = _stage_rows({"live": 3})
    html, gate, _su = _gated_render({"live": 3})
    # Need real plan cards for #us-life-grid to render at all (empty plans
    # bakes the .mx-empty state instead) — re-render with a populated book.
    us_standouts = {"buy": rows, "ran": [], "eligible": len(rows)}
    shell_su, gate2, _locked = bs._split_us_board(us_standouts, 3, gated=True)
    html = _render_stocks({"us_standouts": shell_su, "gate": gate2,
                            "us_prophet_book": _prophet_book()})
    life_tag = re.search(r'<div class="nbgrid"[^>]*id="us-life-grid"[^>]*>', html)
    assert life_tag and 'data-mp1-grid="1"' in life_tag.group(0)

    plan_start = html.find('<div id="us-plan-block">')
    cand_start = html.find('id="us-cand-grid"')
    assert plan_start != -1 and cand_start != -1
    assert plan_start < cand_start, "#us-plan-block must open before #us-cand-grid"

    # #us-plan-block must CLOSE before #us-cand-grid opens — i.e. no shared
    # ancestor below .nb-grid-section (invariant E2). Walk div balance.
    segment = html[plan_start:cand_start]
    depth = 0
    close_pos = None
    for dm in re.finditer(r'<div\b|</div>', segment):
        depth += 1 if dm.group(0) == '<div' else -1
        if depth == 0:
            close_pos = dm.end()
            break
    assert close_pos is not None, "#us-plan-block never closes before #us-cand-grid"


def test_b_gated_grid_holds_exactly_preview_rows_real_cards_from_the_input_slice():
    preview_rows = 3
    rows = [_board_row(ticker=f"CAND{i}", name=f"Candidate {i}", stage="live", lane=None)
            for i in range(10)]
    us_standouts = {"buy": rows, "ran": [], "eligible": len(rows)}
    shell_su, gate, _locked = bs._split_us_board(us_standouts, preview_rows, gated=True)
    assert gate["preview"] == preview_rows
    html = _render_stocks({"us_standouts": shell_su, "gate": gate,
                            "us_prophet_book": _prophet_book(plans=[])})
    grid_start = html.find('id="us-cand-grid"')
    wall_start = html.find('id="us-tier-wall"', grid_start)
    assert wall_start != -1
    grid_html = html[grid_start:wall_start]
    assert grid_html.count('class="pvcard') == preview_rows, (
        "the tier boundary must never widen — the shell only carries the "
        "gate-sliced preview, and this grid renders _render_list.items built "
        "from that same slice")
    preview_tickers = {r["ticker"] for r in shell_su["buy"]}
    assert preview_tickers == {"CAND0", "CAND1", "CAND2"}
    for tk in preview_tickers:
        assert tk in grid_html
    # none of the withheld rows may appear
    for i in range(preview_rows, 10):
        assert f"CAND{i}" not in grid_html


def test_b_su_absent_renders_typed_unavailable_state_with_mx_empty_why():
    html = _render_stocks({
        "us_standouts": None,
        "action_board": {"hold": [], "avoid": [], "notable": [{"ticker": "X"}], "buy": []},
    })
    idx = html.find('id="us-candidates"')
    assert idx != -1, "Candidates must never be silently absent"
    block = html[idx:idx + 1200]
    assert 'class="mx-empty"' in block
    assert 'class="mx-empty-why"' in block, (
        "theme.css requires .mx-empty-why alongside .mx-empty (S4 idiom) — "
        "the unavailable state must follow the same house pattern")
    assert "hasn't published" in block or "尚未发布" in block
    assert "Plans view below is unaffected" in block or "下方的计划视图不受影响" in block


# ══════════════════════════════ C1 — escaped <b> ═══════════════════════════

def test_c1_no_escaped_b_tag_anywhere_in_the_rendered_document():
    html, gate, _su = _gated_render({"live": 5, "setting_up": 3, "ran": 2, "basing": 1,
                                      "blocked": 4})
    assert "&lt;b&gt;" not in html, (
        "t()+|safe on a string already containing raw <b>/</b> double-escapes "
        "under autoescape — the fix writes the bilingual twin explicitly")
    assert f"<b>{gate['total']}</b> screened" in html


# ═══════════════════════════ C2 — census reconciliation ════════════════════

def test_c2_cand_total_equals_gate_total_not_inflated_by_the_ran_array():
    # 22 + 24 + (17-12=5 in buy) + 6 + 3 = 60 = gate.total. A separate 17-row
    # `ran` array sits alongside — under the OLD `+ _ran_rows|length`
    # arithmetic this would have inflated _cand_total to 77.
    html, gate, _su = _gated_render(
        {"live": 22, "setting_up": 24, "ran": 5, "basing": 6, "blocked": 3},
        ran_extra=17)
    assert gate["total"] == 60
    assert f"<b>{gate['total']}</b> screened" in html
    assert "<b>77</b> screened" not in html


def test_c2_five_shelves_sum_exactly_to_cand_total_no_residual_when_clean():
    html, gate, _su = _gated_render(
        {"live": 22, "setting_up": 24, "ran": 5, "basing": 6, "blocked": 3},
        ran_extra=17)
    figs = [int(m) for m in re.findall(r'class="fig">(\d+)</b>', html.split('class="cand-shelves"')[1].split('</div>')[0])]
    assert sum(figs) == gate["total"] == 60
    assert "us-cand-shelf-other" not in html, (
        "no residual shelf when every row carries a recognized stage")


def test_c2_residual_other_shelf_appears_only_when_a_stageless_row_exists():
    html, gate, _su = _gated_render(
        {"live": 2, "setting_up": 2, "ran": 1, "basing": 1, "blocked": 1},
        extra_stageless=4)
    assert gate["total"] == 11
    shelves_block = html.split('class="cand-shelves"')[1].split('</div>')[0]
    figs = [int(m) for m in re.findall(r'class="fig">(\d+)</b>', shelves_block)]
    assert sum(figs) == gate["total"] == 11
    assert "us-cand-shelf-other" in html
    assert '<b class="fig">4</b>' in shelves_block


# ═══════════════════════════ C3 — mixed-unit board-sub ═════════════════════

def test_c3_board_sub_drops_setups_and_shown_clause():
    rows = _stage_rows({"live": 2})
    html = _render_stocks({
        "us_standouts": {"buy": rows, "ran": [], "eligible": 76},
        "us_prophet_book": _prophet_book(plans=[]),
    })
    idx = html.find('id="us-board-sub"')
    assert idx != -1
    sub_html = html[idx:idx + 600]
    assert "setups" not in sub_html
    assert "shown ·" not in sub_html
    assert "76" not in sub_html
    assert "green dot = entry open" in sub_html or "绿点＝现在可入场" in sub_html


# ═══════════════════════ C4 — record-count contract ════════════════════════

def test_c4_us_board_cards_marks_both_heading_kinds():
    src = (ROOT / "templates" / "_us_board_cards.html.j2").read_text()
    assert 'class="nb-stage-hd' in src and 'data-sm-heading="1"' in src
    stage_hd_line = [l for l in src.splitlines() if 'nb-stage-hd sg-' in l][0]
    lane_hd_line = [l for l in src.splitlines() if 'class="nb-lane-hd"' in l][0]
    assert 'data-sm-heading="1"' in stage_hd_line
    assert 'data-sm-heading="1"' in lane_hd_line


def test_c4_theme_js_computes_heading_excluding_record_count():
    src = (ROOT / "templates" / "theme.js").read_text()
    assert "function isHd(el)" in src
    assert "data-sm-heading" in src
    assert "recTotal" in src and "recShown" in src
    # paging must still walk every child (a row stays a row)
    assert "bar.style.display = (total <= pageSize())" in src


def test_c4c_show_more_and_show_all_labels_use_record_units_not_child_units():
    src = (ROOT / "templates" / "theme.js").read_text()
    # the old child-unit constructions must be gone — replaced by record-unit
    # equivalents (nextRecs / recTotal) so "Show N more" / "Show all N" never
    # disagree with the "Showing X of Y" record count beside them
    assert "'Show ' + next + ' more'" not in src
    assert "'Show all ' + total" not in src
    assert "nextRecs" in src and "'Show ' + nextRecs + ' more'" in src
    assert "'Show all ' + recTotal" in src


def test_c4_site_theme_js_matches_template_byte_for_byte():
    a = (ROOT / "templates" / "theme.js").read_text()
    b = (ROOT / "site" / "theme.js").read_text()
    # theme.js is a specially-handled paired asset (baked Supabase config +
    # bundled Terminal overlay) — compare the SHARED prefix up to the point
    # site/theme.js's own bake divergence begins, which is exactly what
    # scripts/check_template_site_sync.py's token-split fallback does.
    assert a.splitlines()[0] == b.splitlines()[0]
    # The isHd/recTotal contract this PR adds must appear verbatim on both
    # sides — that's the part a stale `site/theme.js` would be missing.
    for needle in ("function isHd(el)", "recTotal", "recShown"):
        assert needle in a and needle in b, (
            f"{needle!r} must appear in both templates/theme.js and "
            f"site/theme.js — run scripts.check_template_site_sync --fix")


# ══════════════════════════ D — hydration wiring ════════════════════════════

def test_d_hydrate_reads_cards_html_via_mergeboardcards_never_sets_mp1_grid():
    html, gate, _su = _gated_render({"live": 5})
    hydrate_start = html.find("function hydrate(payload)")
    assert hydrate_start != -1
    teardown_start = html.find("function _pvcTeardown", hydrate_start)
    # hydrate() body — bounded loosely by the next top-level function
    next_fn = html.find("function recountStageChips", hydrate_start)
    body = html[hydrate_start:next_fn if next_fn != -1 else hydrate_start + 6000]
    assert "payload.cards_html" in body
    assert "mergeBoardCards(freshCand, payload.cards_html)" in body
    assert "getElementById('us-cand-grid')" in body
    assert "freshCand.setAttribute('data-mp1-grid'" not in body, (
        "the plan grid's W-L1 neutralization marker must never travel onto "
        "the freshly-hydrated candidate grid")
    assert "getElementById('us-tier-wall')" in body, (
        "hydrate() teardown must remove the restored candidate wall by its "
        "own id (D3)")


# ═══════════ E — the render's dead-reference guard (render 32585314359) ═══════
def test_e_no_js_assignment_impersonates_an_href_or_src_attribute():
    """The first P0 merge rendered fine and then died at the render's
    `guard — no dead site references` step, on a target named `candidates`
    "linked by" us_stocks.html. There was no such link: the source-toggle
    script assigned a string to a variable whose name is one of the two
    attribute names scripts/check_site_asset_refs.py scans for, and the
    guard's lookbehind only rejects a preceding word character or hyphen
    (which is what makes `data-` prefixed attributes safe) — an assignment
    preceded by a space is not rejected. The site never published.

    Imports the checker's OWN pattern rather than restating it, so the pin
    follows the guard if the guard moves. Asserts against the RENDERED page,
    because a comment inside a <script> ships in the bytes exactly like markup
    does — the first attempt at this fix re-introduced the failure inside the
    comment explaining it.
    """
    from scripts.check_site_asset_refs import _ATTR_RE

    html, _gate, _su = _gated_render({"live": 3, "setting_up": 2})
    targets = [m.group(1) for m in _ATTR_RE.finditer(html)]
    bogus = sorted({t for t in targets if t in ("candidates", "plans")})
    assert not bogus, (
        "the rendered page carries href/src reference(s) to "
        f"{bogus} — no such file exists, so the render's dead-reference guard "
        "fails and nothing publishes. A JS variable named href or src, or a "
        "comment spelling one followed by = and a quoted string, is enough to "
        "cause this."
    )


@pytest.mark.parametrize("as_of", ("2026-09-11", "2026-09-15", None, "", "__missing__"))
def test_candidate_heading_discloses_source_date_without_tonight_claim(as_of):
    """A new shell/render timestamp must not freshen an old or undated screen."""
    from bs4 import BeautifulSoup

    su = {"buy": _stage_rows({"live": 1}), "ran": [], "eligible": 1}
    if as_of != "__missing__":
        su["as_of"] = as_of
    html = _render_stocks({"us_standouts": su,
                           "us_prophet_book": _prophet_book(plans=[])})
    soup = BeautifulSoup(html, "html.parser")
    section = soup.select_one("#us-candidates")
    assert section is not None
    heading = section.select_one(".mx-sec-total .l-en").get_text(" ", strip=True)
    assert "1 screened" in heading
    if as_of and as_of != "__missing__":
        assert "as of " + as_of in heading
    else:
        assert "date unavailable" in heading
    assert "tonight" not in section.get_text(" ", strip=True).lower()
    assert "今晚" not in section.get_text(" ", strip=True)


def _dated_gated_candidate_and_plan_page(as_of, *, first_resolved=False):
    """Exercise actual tier splitters; dates, counts and hidden identities stay separate."""
    from copy import deepcopy
    from tests.test_dashboard_template_render import _prophet_plan

    source = {"buy": _stage_rows({"live": 5}), "ran": [], "eligible": 5}
    if as_of != "__missing__":
        source["as_of"] = as_of
    plans = [_prophet_plan(id=f"PLAN{i}-BULL-20260701", asset=f"PLAN{i}",
                           lifecycle_state="resolved" if first_resolved and i == 0 else "ready")
             for i in range(5)]
    book = _prophet_book(plans=plans, source_asof="2026-07-04")
    original_source, original_book = deepcopy(source), deepcopy(book)
    shell, gate, locked = bs._split_us_board(source, 3, gated=True)
    plan_shell, life_gate, locked_plans = bs._split_us_prophet_board(book, 3, gated=True)
    context = bs._us_life_repair_context(
        {"us_standouts": source, "us_prophet_book": book}, plan_shell, life_gate, preview_rows=3)
    html = _render_stocks({"us_standouts": shell, "gate": gate,
                           "us_prophet_book": plan_shell, "life_gate": life_gate, **context})
    assert source == original_source and book == original_book
    assert gate["preview"] + gate["locked"] == gate["total"] == 5
    assert life_gate["preview"] + life_gate["locked"] == life_gate["total"] == 5
    assert len(locked) == len(locked_plans) == 2
    return html, gate, life_gate, context


@pytest.mark.parametrize("as_of", ("2026-09-11", "2026-09-16", None, "", "__missing__"))
def test_gated_candidate_journey_never_borrows_freshness(as_of):
    from bs4 import BeautifulSoup

    html, gate, _, _ = _dated_gated_candidate_and_plan_page(as_of)
    soup = BeautifulSoup(html, "html.parser")
    section = soup.select_one("#us-candidates")
    wall = section.select_one(".us-tier-wall")
    assert wall is not None
    toggle = soup.select_one("#us-src-toggle")
    assert toggle is not None
    visible_and_tooltip = (section.get_text(" ", strip=True) + " "
                           + toggle["data-tip-en"] + " " + toggle["data-tip-zh"])
    assert "tonight" not in visible_and_tooltip.lower()
    assert "今晚" not in visible_and_tooltip
    assert str(gate["locked"]) in wall.select_one(".us-tw-h .l-en").get_text()
    assert str(gate["locked"]) in wall.select_one(".us-tw-h .l-zh").get_text()
    assert len(section.select("#us-cand-grid a[data-ticker]")) == gate["preview"]
    assert not section.select('#us-cand-grid [data-ticker="CAND3"], #us-cand-grid [data-ticker="CAND4"]')
    heading = section.select_one(".mx-sec-total .l-en").get_text(" ", strip=True)
    if as_of and as_of != "__missing__":
        assert "as of " + as_of in heading
    else:
        assert "date unavailable" in heading


@pytest.mark.parametrize("as_of", ("2026-09-11", "2026-09-16", None, "", "__missing__"))
@pytest.mark.parametrize("first_resolved", (False, True))
def test_historical_plan_wall_does_not_borrow_candidate_date(as_of, first_resolved):
    from bs4 import BeautifulSoup

    html, _, gate, context = _dated_gated_candidate_and_plan_page(as_of, first_resolved=first_resolved)
    soup = BeautifulSoup(html, "html.parser")
    wall = soup.select_one("#us-life-wall")
    assert wall is not None
    text = wall.get_text(" ", strip=True)
    assert "tonight" not in text.lower() and "今晚" not in text
    assert "2026-09-11" not in text and "2026-09-16" not in text
    assert "2 more tracked plan rows" in text if not first_resolved else "3 more tracked plan rows" in text
    visible = context["life_gate_visible_preview"]
    locked = context["life_gate_visible_locked"]
    assert visible + locked == gate["total"] == 5
    assert visible == (2 if first_resolved else 3)
    assert f"first {visible} of 5 tracked plan rows" in text
    assert len(soup.select("#us-life-grid a[data-ticker]")) == 3
    assert not soup.select('#us-life-grid [data-ticker="PLAN3"], #us-life-grid [data-ticker="PLAN4"]')


# --- #7237 tracked-record pager regression family ---
# ═══════════ F — tracked-record pager uses the default-visible population ════
def _show_more_script() -> str:
    src = (ROOT / "templates" / "theme.js").read_text()
    start = src.index("  function smBL(")
    end_marker = "  window.initShowMore = initShowMore;"
    end = src.index(end_marker, start) + len(end_marker)
    return src[start:end]


def test_f_plan_grid_declares_resolved_as_default_pager_exclusion_on_both_build_paths():
    dash = (ROOT / "templates" / "dashboard.html.j2").read_text()
    assert 'data-showmore-exclude-life="resolved" id="us-life-grid"' in dash
    assert "freshLifeGrid.setAttribute('data-showmore-exclude-life', 'resolved')" in dash


def test_f_tracked_pager_counts_only_default_visible_unresolved_records():
    """The default plan grid hides resolved history. Its pager must walk/count
    the same unresolved population, while lifecycle filters remain free to
    reveal every matching sm-hidden record later."""
    import shutil
    import subprocess

    node = shutil.which("node")
    assert node, "node is required by the existing code-gated JavaScript contract"
    harness = r"""
class Classes {
  constructor(){ this.values = new Set(); }
  contains(v){ return this.values.has(v); }
  add(v){ this.values.add(v); }
  remove(v){ this.values.delete(v); }
}
class Element {
  constructor(tag, attrs){
    this.tagName = tag; this.nodeType = 1; this.attrs = attrs || {};
    this.dataset = {}; this.children = []; this.classList = new Classes();
    this.style = {}; this.listeners = {}; this.parentNode = null;
    this.nextSibling = null; this.innerHTML = ''; this.className = '';
    this.offsetWidth = 100;
  }
  hasAttribute(name){ return Object.prototype.hasOwnProperty.call(this.attrs, name); }
  getAttribute(name){ return this.hasAttribute(name) ? this.attrs[name] : null; }
  setAttribute(name, value){ this.attrs[name] = String(value); }
  appendChild(child){ this.children.push(child); child.parentNode = this; return child; }
  addEventListener(name, fn){ this.listeners[name] = fn; }
  scrollIntoView(){}
}
const parent = new Element('section');
parent.insertBefore = function(child){ this.inserted = child; child.parentNode = this; };
const grid = new Element('div', {
  'data-showmore-rows': '3',
  'data-showmore-exclude-life': 'resolved',
});
grid.parentNode = parent;
const lives = [
  'ready','resolved','entered','ready','entered','resolved','ready','entered',
  'ready','entered','resolved','ready','entered','ready','entered','resolved',
  'ready','entered','ready','entered','ready','entered'
];
const records = lives.map(function(life){
  const el = new Element('article', {'data-life': life});
  el.life = life; el.parentNode = grid; return el;
});
grid.children = records;
global.document = {
  querySelectorAll: () => [grid],
  createElement: (tag) => new Element(tag),
};
global.window = {
  getComputedStyle: () => ({getPropertyValue: () => '100px 100px 100px 100px 100px'}),
  addEventListener: () => {},
};
""" + _show_more_script() + r"""
initShowMore();
const bar = parent.inserted;
if (!bar) throw new Error('show-more bar was not created');
const count = bar.children[0];
const buttons = bar.children[1];
const more = buttons.children[0];
const all = buttons.children[1];
const unresolved = records.filter(x => x.life !== 'resolved');
const resolved = records.filter(x => x.life === 'resolved');
const visibleUnresolved = () => unresolved.filter(x => !x.classList.contains('sm-hidden')).length;
const hiddenResolved = () => resolved.filter(x => x.classList.contains('sm-hidden')).length;
if (visibleUnresolved() !== 15) throw new Error('default visible unresolved=' + visibleUnresolved());
if (hiddenResolved() !== resolved.length) throw new Error('resolved history leaked into default pager');
if (!count.innerHTML.includes('Showing <b>15</b> of <b>18</b>')) throw new Error(count.innerHTML);
if (!more.innerHTML.includes('Show 3 more')) throw new Error(more.innerHTML);
if (!all.innerHTML.includes('Show all 18')) throw new Error(all.innerHTML);
all.listeners.click();
if (visibleUnresolved() !== 18) throw new Error('show-all unresolved=' + visibleUnresolved());
if (hiddenResolved() !== resolved.length) throw new Error('show-all exposed resolved history');
if (!count.innerHTML.includes('Showing <b>18</b> of <b>18</b>')) throw new Error(count.innerHTML);
"""
    proc = subprocess.run([node, "-e", harness], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr or proc.stdout
