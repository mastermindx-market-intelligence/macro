"""P-MP1-SHELL §8a — the stance-projection function + `pv_card` no-read parameter.

MP-1-prophet-board.md §8a (Amendment 1, b1 ruling, `verdict.yml
rulings.b1_actionability_axis`): display-tier stance sources `entry_status` when
present on a plan row, else `board_read.fields.status`, projected through the SAME
Q7 bucket table `engine/us_board_rank.py` already ships
(`_LIVE_/_SETTING_UP_/_RAN_/_BLOCKED_STATUSES`) — never a second mapping. "No read
yet" (BLOCKED_DATA, DESIGN_NOTES.md Q7b) renders only when BOTH sources are absent.

This is the DATA-LAYER half of §8a, independently testable against the real
published payload (`site/prophet/index.json`) without the packet's central act
(re-sourcing the Setups card grid to the plan book / building the lifecycle
ladder), which the worker report attached to this commission documents as BLOCKED
by an unowned collision with the W-L1 provisional-board live-refresh system. The
projection function and the `pv_card(cx, allow_no_read=...)` parameter are real,
wired-correctness-verified building blocks for that still-blocked display wiring;
this file proves the function is CORRECT against real data and that the macro
parameter is BYTE-IDENTICAL for every caller that does not opt in.

Run: .venv/bin/python -m pytest tests/test_p_mp1_shell_stance_projection.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from html.parser import HTMLParser
import copy

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import jinja2  # noqa: E402

import scripts.build_site as bs  # noqa: E402

PAYLOAD = ROOT / "site" / "prophet" / "index.json"
PARTIAL = ROOT / "templates" / "_prophet_card.html.j2"


def _avail(value):
    return {"fields": {"status": {"value": value, "state": "available"}}}


def _not_applicable():
    return {"fields": {"status": {"value": None, "state": "not_applicable"}}}


# ── pure function: source precedence + bucket mapping ──────────────────────────
def test_entry_status_wins_over_board_read_when_both_present():
    out = bs.us_stance_projection("buy_now", _avail("blocked"))
    assert out == {"verb": "buy", "stance_basis": "entry_status"}


def test_board_read_fallback_when_entry_status_absent():
    out = bs.us_stance_projection(None, _avail("blocked"))
    assert out == {"verb": "avoid", "stance_basis": "board_read"}


def test_board_read_fallback_ignores_non_available_state():
    """`not_applicable` (e.g. a resolved plan) is not a usable board_read status —
    it must NOT be read as a value, only 'available' status states count."""
    out = bs.us_stance_projection(None, _not_applicable())
    assert out == {"verb": None, "stance_basis": "no_read"}


def test_no_read_only_when_both_absent():
    assert bs.us_stance_projection(None, None) == {"verb": None, "stance_basis": "no_read"}
    assert bs.us_stance_projection("", {}) == {"verb": None, "stance_basis": "no_read"}


def test_every_q7_status_maps_to_the_ruled_verb():
    """DESIGN_NOTES.md Q7 table, transcribed verbatim as the test oracle."""
    expect = {
        "buy_now": "buy", "partial": "buy", "buy_soon": "near",
        "await_confluence": "wait", "bounce_wait": "wait", "watch": "wait",
        "extended": "hold", "topping": "hold", "hold": "hold",
        "blocked": "avoid", "exit": "avoid", "avoid": "avoid",
        "wait_pullback": "wait", "later": "wait", "await": "wait",
    }
    for status, verb in expect.items():
        assert bs.us_stance_projection(status, None) == {
            "verb": verb, "stance_basis": "entry_status"}, status


def test_unrecognized_truthy_status_fails_soft_to_wait_not_an_exception():
    out = bs.us_stance_projection("some_future_status_v2", None)
    assert out == {"verb": "wait", "stance_basis": "entry_status"}


# ── real-payload proof: the projection is correct against the current bake ──────
def test_projection_reproduces_the_published_boundary_on_real_data():
    """Every one of the 262 published plans classifies into exactly one basis, and
    the no-read count matches the payload's own board_read_coverage arithmetic
    (25 not_applicable/plan_closed rows minus any of those 25 that also carry a
    live entry_status) — proving the function's BOTH-absent rule against real
    data, not just the hand-built fixtures above."""
    if not PAYLOAD.exists():
        import pytest
        pytest.skip("site/prophet/index.json not present in this checkout")
    data = json.loads(PAYLOAD.read_text())
    plans = data["plans"]
    bases = {"entry_status": 0, "board_read": 0, "no_read": 0}
    verbs_seen = set()
    for p in plans:
        out = bs.us_stance_projection(p.get("entry_status"), p.get("board_read"))
        bases[out["stance_basis"]] += 1
        if out["verb"] is not None:
            verbs_seen.add(out["verb"])
            assert out["verb"] in ("buy", "near", "wait", "hold", "avoid")
        else:
            assert out["stance_basis"] == "no_read"
    assert sum(bases.values()) == len(plans)
    # every row got a verdict from SOME source — the fallback closes the gap
    # entry_status alone left (only 143/262 rows carry entry_status directly).
    assert bases["board_read"] > 0, "the fallback path must fire on real data, not just fixtures"
    assert bases["no_read"] < len(plans), "not every row can be unreadable on a live payload"


# ── macro parameter: additive, byte-identical when unused ──────────────────────
def _env():
    return jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))


def _render(macro_call: str, **ctx) -> str:
    tmpl = _env().from_string(
        '{% import "_prophet_card.html.j2" as pv %}' + macro_call
    )
    return tmpl.render(**ctx)


_BASE_CX = {
    "href": "stock.html#AAPL", "tk": "AAPL", "mkt": "us", "name": "Apple",
    "sec": "Technology", "verb": "buy", "edge": 88, "stage": 2,
}


def test_pv_card_output_identical_with_and_without_the_new_parameter():
    """Every existing caller (hk/china/canada/intl, every current US call site)
    passes no `allow_no_read` argument — acceptance item 3 / §8a's parity
    requirement. Must be byte-for-byte identical to calling the macro with the
    parameter explicitly at its default."""
    out_omitted = _render("{{ pv.pv_card(cx) }}", cx=_BASE_CX)
    out_explicit_default = _render("{{ pv.pv_card(cx, allow_no_read=false) }}", cx=_BASE_CX)
    assert out_omitted == out_explicit_default


def test_pv_card_allow_no_read_off_still_defaults_missing_verb_to_wait():
    """Without the flag, a row with no verb (e.g. a caller that has not yet been
    updated) keeps the PRE-EXISTING legacy behavior — silently 'wait' — because
    this parameter is additive-only (§8a: 'every other caller's byte output is
    unchanged')."""
    tmpl = _env().from_string(
        '{% import "_prophet_card.html.j2" as pv %}'
        "{{ pv.pv_card({'href':'x','tk':'AAPL','mkt':'us'}) }}"
    )
    html = tmpl.render()
    assert 'class="pvcard pv-wait' in html
    assert "pv-noread" not in html


def test_pv_card_allow_no_read_on_renders_the_disclosed_no_read_state():
    """Opted in AND no usable verb -> the dashed, hue-free no-read chip (Q7b),
    never a guessed Wait."""
    tmpl = _env().from_string(
        '{% import "_prophet_card.html.j2" as pv %}'
        "{{ pv.pv_card({'href':'x','tk':'AAPL','mkt':'us'}, allow_no_read=true) }}"
    )
    html = tmpl.render()
    assert "pv-noread" in html
    assert "No read yet" in html
    assert 'class="pvcard pv-wait' not in html


def test_pv_card_allow_no_read_on_but_verb_present_renders_normally():
    """Opting in must not change a card that DOES have a usable verb — the flag
    only ever changes behavior on the no-verb path."""
    tmpl = _env().from_string(
        '{% import "_prophet_card.html.j2" as pv %}'
        "{{ pv.pv_card({'href':'x','tk':'AAPL','mkt':'us','verb':'buy'}, allow_no_read=true) }}"
    )
    html = tmpl.render()
    assert 'class="pvcard pv-buy' in html
    assert "pv-noread" not in html


def test_stance_basis_tip_renders_when_caller_passes_it():
    """§8a: 'per-row stance_basis disclosed at minimum in the LENS tip'."""
    tmpl = _env().from_string(
        '{% import "_prophet_card.html.j2" as pv %}'
        "{{ pv.pv_card({'href':'x','tk':'AAPL','mkt':'us','verb':'buy',"
        "'stance_basis':'board_read'}, allow_no_read=true) }}"
    )
    html = tmpl.render()
    assert "data-tip-en=" in html and "board_read" in html


# Chairman-approved plan-record boundary, 2026-09-16.
# Keep the legacy projection tests above: the history/data function is not a
# current-entry authority. These tests bind the actual presentation consumer.


def _record_plan(**overrides):
    plan = {
        "id": "CVCO-BULL-20260810", "asset": "CVCO",
        "entry_status": "buy_now", "_priority_score": 84.5,
        "plan_asof": "2026-08-12", "recorded_at": "2026-08-12",
        "lifecycle_state": "entered", "closed": False,
        "entry_zone": {"low": 580.40, "high": 598.40},
        "board_read": {"as_of": "2026-09-15", "fields": {
            "status": {"state": "available", "value": "blocked"},
            "name": {"state": "available", "value": "Cavco Industries"},
            "sector": {"state": "available", "value": "Consumer Discretionary"},
        }},
    }
    plan.update(overrides)
    return plan


def _render_plan_record(plan, *, candidates=None, triggers=None, episodes=None):
    env = _env()
    env.globals.update(us_stance_projection=bs.us_stance_projection, tr=lambda x: x)
    return env.get_template("_us_prophet_plan_cards.html.j2").render(
        items=[plan], cand_map=candidates or {}, trg_map=triggers or {},
        episode_map=episodes or {},
    )


@pytest.mark.parametrize("lifecycle", ["ready", "entered", "delivering", "overtime", "invalidated", "resolved"])
@pytest.mark.parametrize("old_status", ["buy_now", "partial", "bounce_wait", None])
def test_record_plan_never_projects_an_original_status_as_current_action(lifecycle, old_status):
    plan = _record_plan(lifecycle_state=lifecycle, closed=lifecycle == "resolved", entry_status=old_status)
    before = copy.deepcopy(plan)
    rendered = _render_plan_record(plan)
    assert 'data-record-only="1"' in rendered
    assert "Tracking only" in rendered and "仅作跟踪" in rendered
    for action in ("buy", "near", "wait", "hold", "avoid"):
        assert f"pv-{action}" not in rendered
    assert 'data-noread="1"' not in rendered  # purpose is not missing-data status
    assert "fresh read" not in rendered
    assert plan == before  # immutable episode/geometry/status remain intact


def test_record_plan_restores_its_own_name_and_sector_outside_candidate_list():
    rendered = _render_plan_record(_record_plan())
    assert "Cavco Industries" in rendered
    assert "Consumer Discretionary" in rendered
    assert 'href="stock.html#CVCO"' in rendered
    assert 'id="pv-CVCO-BULL-20260810"' in rendered


def test_record_plan_uses_attached_identity_before_shortlist_enrichment():
    rendered = _render_plan_record(_record_plan(), candidates={"CVCO": {
        "name": "Wrong identity", "sector": "Wrong sector", "price": 999.0,
        "featured": True, "new": True, "spark_svg": "", "lane": "continuation",
    }})
    assert "Cavco Industries" in rendered and "Consumer Discretionary" in rendered
    assert "Wrong identity" not in rendered and "Wrong sector" not in rendered
    assert "pv-featured" not in rendered and "pv-triage" not in rendered
    assert "★ Featured" not in rendered


def test_record_plan_labels_original_geometry_and_creation_not_current_buy_zone():
    rendered = _render_plan_record(_record_plan())
    assert "Original zone" in rendered and "原始区间" in rendered
    assert "$580.40" in rendered and "$598.40" in rendered
    assert "Created Aug 12" in rendered and "建立 08-12" in rendered
    assert "Last screen" in rendered and "2026-09-15" in rendered
    assert "Original priority: 84" in rendered
    assert "how ready this setup is today" not in rendered
    assert 'class="pv-edge"' not in rendered
    assert "Re-add" not in rendered and "Zone sets on confirmation" not in rendered


@pytest.mark.parametrize("zone", [None, {}, {"low": None, "high": None}])
def test_record_plan_missing_geography_is_not_a_pending_entry_promise(zone):
    rendered = _render_plan_record(_record_plan(entry_zone=zone))
    assert "Original zone unavailable" in rendered
    assert "Zone sets on confirmation" not in rendered
    assert "No zone — stand aside" not in rendered


@pytest.mark.parametrize("board", [None, {}, {"fields": {}}, {"as_of": None, "fields": {}}])
def test_record_plan_missing_observation_is_explicit_without_invented_wait(board):
    rendered = _render_plan_record(_record_plan(board_read=board, entry_status=None))
    assert "Tracking only" in rendered
    assert "Screen date unavailable" in rendered
    assert 'class="pvcard pv-wait' not in rendered


def test_record_plan_escapes_attached_identity_in_real_unescaped_environment():
    plan = _record_plan()
    plan["board_read"]["fields"]["name"]["value"] = '<img src=x onerror="bad()">'
    plan["board_read"]["fields"]["sector"]["value"] = '<script>bad()</script>'
    rendered = _render_plan_record(plan)
    assert "&lt;img" in rendered and "&lt;script&gt;" in rendered
    assert "<img" not in rendered and "<script>" not in rendered


def test_record_macro_defends_against_accidentally_supplied_current_action_hints():
    cx = dict(_BASE_CX, record_only=True, featured=True, triage=True,
              trigger={"kind": "fired"}, show_change=True, price_txt="$123.45",
              zone_kind="readd", zone_lo="$100", zone_hi="$110")
    rendered = _render("{{ pv.pv_card(cx) }}", cx=cx)
    assert 'data-record-only="1"' in rendered
    assert "pv-featured" not in rendered and "pv-triage" not in rendered
    assert 'class="pv-trg' not in rendered and 'class="pv-live"' not in rendered
    assert "Re-add" not in rendered
    assert 'class="nb-px' not in rendered  # no unsupported current-price stamp


def test_record_plan_preserves_missing_identity_without_template_failure():
    plan = _record_plan(board_read={"fields": {
        "name": {"state": "blocked_data", "value": "Unusable name"},
        "sector": {"state": "available", "value": None},
    }})
    rendered = _render_plan_record(plan)
    assert "CVCO" in rendered and "Unusable name" not in rendered
    assert "Company name unavailable" in rendered


def test_record_plan_malformed_optional_observation_does_not_abort_the_board():
    for board in (True, [], {"fields": True}, {"fields": {"name": True, "sector": []}}):
        rendered = _render_plan_record(_record_plan(board_read=board))
        assert "Tracking only" in rendered and "CVCO" in rendered


def test_record_only_does_not_change_ordinary_candidate_macro_bytes():
    omitted = _render("{{ pv.pv_card(cx) }}", cx=_BASE_CX)
    explicit = _render("{{ pv.pv_card(cx) }}", cx=dict(_BASE_CX, record_only=False))
    assert omitted == explicit
    assert 'class="pvcard pv-buy' in omitted


def test_record_ladder_describes_inventory_not_today_recommendations():
    book = {"plans": [{"id": "P"}], "intake": {"early_turn_watch": []},
            "lifecycle_counts": {"watch": 0, "ready": 1, "entered": 2,
                "delivering": 0, "overtime": 1, "invalidated": 1, "resolved": 3},
            "lifecycle_live_total": 5, "lifecycle_grand_total": 8}
    rendered = _render("{{ pv.mx_ladder(book) }}", book=book)
    assert "unresolved setups" in rendered
    assert "Ordered by original priority" in rendered
    assert "live setups today" not in rendered
    assert "how ready a setup is today" not in rendered
    assert 'class="ladder-n fig">5<' in rendered
    assert 'data-life="resolved"' in rendered


def test_record_ladder_read_failure_does_not_assert_other_sources_are_current():
    rendered = _render("{{ pv.mx_ladder(none, error=true) }}")
    assert "Tracking unavailable" in rendered
    assert "are current" not in rendered
    assert "仍是最新" not in rendered


def test_record_macro_omits_price_stage_when_model_lifecycle_is_unavailable():
    rendered = _render("{{ pv.pv_card(cx) }}", cx=dict(_BASE_CX, record_only=True))
    assert 'class="pv-stp"' not in rendered
    assert "State unavailable" in rendered


@pytest.mark.parametrize("low,high", [(float("nan"), 11), (1, float("inf")),
    (True, 2), (2, 1), (0, 1), ("1", "2"), (None, 2)])
def test_record_plan_invalid_original_geometry_stays_unavailable(low, high):
    rendered = _render_plan_record(_record_plan(entry_zone={"low": low, "high": high}))
    assert "Original zone unavailable" in rendered
    assert "$nan" not in rendered and "$inf" not in rendered


class _RecordAnchorAudit(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchor_depth = 0
        self.nested = []
        self.card_tags = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "pvcard" in attrs.get("class", "").split():
            self.card_tags.append(tag)
        if tag == "a":
            if self.anchor_depth:
                self.nested.append(attrs)
            self.anchor_depth += 1
            self.links.append(attrs)

    def handle_endtag(self, tag):
        if tag == "a":
            self.anchor_depth = max(0, self.anchor_depth - 1)


def test_record_navigation_has_no_nested_anchors_and_preserves_both_destinations():
    plan = _record_plan(lifecycle_state="resolved", closed=True)
    html = _render_plan_record(plan, episodes={plan["id"]: {
        "ep": 1, "eps": 2, "dopen_en": "Aug 12", "dopen_zh": "8月12日",
        "newer": "CVCO-BULL-20260915",
    }})
    parsed = _RecordAnchorAudit()
    parsed.feed(html)
    assert not parsed.nested, "nested links make Chromium clone cards and their ids"
    assert parsed.card_tags == ["article"]
    assert any(a.get("href") == "stock.html#CVCO" for a in parsed.links)
    assert any("CVCO-BULL-20260915" in a.get("href", "") for a in parsed.links)
    stock = next(a for a in parsed.links if a.get("href") == "stock.html#CVCO")
    assert stock.get("aria-label") == "CVCO"


def test_record_stock_overlay_uses_house_radius_token_without_losing_full_card_navigation():
    plan = _record_plan(lifecycle_state="resolved", closed=True)
    html = _render_plan_record(plan)
    parsed = _RecordAnchorAudit()
    parsed.feed(html)
    stock = next(a for a in parsed.links if a.get("href") == "stock.html#CVCO")
    style = stock.get("style", "").replace(" ", "")
    assert "position:absolute" in style
    assert "inset:0" in style
    assert "z-index:4" in style
    assert "border-radius:var(--r-card,12px)" in style
    assert "border-radius:inherit" not in style
