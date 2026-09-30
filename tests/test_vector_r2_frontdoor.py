from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "vector.html.j2"


def test_r2_frontdoor_uses_research_tabs_and_plain_editorial_read() -> None:
    source = TEMPLATE.read_text(encoding="utf-8")

    assert 'class="vector-tabs"' in source
    assert 'href="#overview"' in source
    assert 'href="#cycle-lab"' in source
    assert 'href="#strategy-track-record"' in source
    assert 'href="#onchain-lab"' in source
    assert 'href="#derivatives-desk"' in source
    assert "Constructive backdrop." in source
    assert "Defensive backdrop." in source
    assert "Mixed backdrop." in source


def test_r2_frontdoor_surfaces_final_allocation_without_new_authority() -> None:
    source = TEMPLATE.read_text(encoding="utf-8")

    assert "decision.final.exposure_pct" in source
    assert "decision.final.action_en" in source
    assert "Model allocation" in source
    assert "模型仓位" in source


def test_r2_frontdoor_puts_synchronized_instrument_before_decision_shelf() -> None:
    source = TEMPLATE.read_text(encoding="utf-8")

    assert source.count('id="vec-risk-chart"') == 1
    assert source.index('id="vec-risk-chart"') < source.index('data-shelf="S2"')
    assert 'class="overview-instrument"' in source
    assert "Price · risk · model allocation" in source
    assert "价格 · 风险 · 模型仓位" in source


def test_r2_frontdoor_removes_decorative_shelf_rail() -> None:
    source = TEMPLATE.read_text(encoding="utf-8")

    assert ".shelf::before{display:none}" in source
    assert ".shelf-kicker{display:none}" in source


def test_r2_suites_are_invoked_by_the_existing_vector_ci_owner() -> None:
    """Files on disk are not a gate: require the packed Vector pytest command."""
    import shlex
    import yaml

    manifest = yaml.safe_load((ROOT / ".github/ci/legacy-jobs.yml").read_text(encoding="utf-8"))
    job = manifest["jobs"]["unrun-vector-dsr"]
    required = {
        "tests/test_vector_wave1.py",
        "tests/test_vector_r2_data_boundary.py",
        "tests/test_vector_r2_frontdoor.py",
        "tests/test_btc_signals.py",
        "tests/test_btc_impulse_falsifier.py",
        "tests/test_btc_impulse_radar.py",
        "tests/test_btc_impulse_alerts.py",
    }
    for step in job["steps"]:
        command = shlex.split(step.get("run", ""))
        if command[:3] == ["python", "-m", "pytest"] and required.issubset(command):
            assert "if" not in step, "Vector regression invocation must not be conditional"
            assert not step.get("continue-on-error", False), "Regressions must fail the step"
            break
    else:
        raise AssertionError("R2 regressions are not invoked by the existing Vector CI owner")


def test_vector_uses_in_page_brain_entry_and_suppresses_floating_launcher() -> None:
    source = TEMPLATE.read_text(encoding="utf-8")

    assert 'data-vector-brain' in source
    assert "{{ t('Ask Mastermind','询问操盘大脑') }}" in source
    assert "body.page-vector #mmb-boot" in source
    assert "body.page-vector #mmb-launch" in source
    assert "document.getElementById('mmb-boot')" in source
    assert "window.MMBrain.open()" in source


def test_vector_brain_entry_is_not_a_second_chat_owner() -> None:
    source = TEMPLATE.read_text(encoding="utf-8")

    assert "MM_BRAIN_CFG" not in source
    assert "mm_brain.js" not in source
    assert "fetch('/api/brain" not in source


# R13: display contract consumes the existing CVD owner; it cannot grant authority.
def _r13_context(**changes):
    d=dict(ok=True,display_only=True,causally_qualified=False,scope='OKX/BTC/CONTRACTS',
           asof='2026-01-09 08:00:00',evaluated_at='2026-01-09 09:00:00',
           n_hours=200,window_24h_complete=True,window_72h_complete=True,
           stale=False,gap_detected=False,flow_state='buy_dominant',buy_share_24h=.625,
           net_flow_24h_native=24.)
    d.update(changes)
    return {'context_legs':{'intraday_cvd':d}}


def test_r13_consumes_current_scoped_flow_without_creating_signal():
    from scripts.build_vector import _derivatives_flow_view
    d=_derivatives_flow_view(_r13_context())
    assert d['state']=='available' and d['buy_share_pct']==62.5
    assert d['window_24h_complete'] and d['window_72h_complete']
    assert d['observed_at']=='2026-01-09 08:00 UTC'
    assert d['evaluated_at']=='2026-01-09 09:00 UTC'
    assert d['causally_qualified'] is False
    assert not {'action','allocation','confidence','funding_annual','net_flow_usd'}.intersection(d)


def test_r13_stale_or_future_observations_cannot_look_current():
    from scripts.build_vector import _derivatives_flow_view
    assert _derivatives_flow_view(_r13_context(stale=True))['state']=='stale'
    old=_derivatives_flow_view(_r13_context(evaluated_at='2026-01-12 09:00:00'))
    assert old['state']=='stale' and old['buy_share_pct'] is None
    future=_derivatives_flow_view(_r13_context(asof='2026-01-10 08:00:00'))
    assert future['state']=='unavailable' and future['buy_share_pct'] is None


def test_r13_zero_activity_and_valid_extreme_shares_are_distinct():
    from scripts.build_vector import _derivatives_flow_view
    z=_derivatives_flow_view(_r13_context(flow_state='no_activity',buy_share_24h=None,net_flow_24h_native=0))
    assert z['state']=='no_activity' and z['buy_share_pct'] is None
    for share in [0.,1.]:
        d=_derivatives_flow_view(_r13_context(buy_share_24h=share))
        assert d['state']=='available' and d['buy_share_pct']==share*100
    bad=_derivatives_flow_view(_r13_context(flow_state='no_activity',buy_share_24h=.5))
    assert bad['state']=='unavailable'


def test_r13_window_coverage_is_local_not_whole_history_label():
    from scripts.build_vector import _derivatives_flow_view
    for d in [_r13_context(n_hours=23),_r13_context(window_24h_complete=False)]:
        p=_derivatives_flow_view(d);assert p['state']=='coverage_gap' and p['buy_share_pct'] is None
    d=_derivatives_flow_view(_r13_context(n_hours=48,window_72h_complete=False,gap_detected=True))
    assert d['state']=='available' and d['window_24h_complete'] and not d['window_72h_complete']
    assert d['historical_gap'] is True


def test_r13_unavailable_malformed_scope_and_numeric_inputs_fail_closed():
    from scripts.build_vector import _derivatives_flow_view
    for raw in [None,{},[],{'context_legs':'bad'},{'context_legs':{'intraday_cvd':[]}}]:
        p=_derivatives_flow_view(raw);assert p['state']=='unavailable' and p['buy_share_pct'] is None
    for changes in [dict(scope='COINBASE/SPOT'),dict(display_only=False),dict(causally_qualified=True),
                    dict(buy_share_24h=True),dict(buy_share_24h=float('nan')),dict(buy_share_24h=1.5),
                    dict(buy_share_24h='0.5'),dict(n_hours=True),dict(n_hours=200.5),dict(stale=None),
                    dict(evaluated_at=None),dict(asof=True)]:
        p=_derivatives_flow_view(_r13_context(**changes))
        assert p['state']=='unavailable' and p['buy_share_pct'] is None,changes


def test_r13_projection_is_pure_and_timezone_equivalent():
    import copy
    from scripts.build_vector import _derivatives_flow_view
    original=_r13_context();before=copy.deepcopy(original)
    a=_derivatives_flow_view(original)
    b=_derivatives_flow_view(_r13_context(asof='2026-01-09T03:00:00-05:00',evaluated_at='2026-01-09T04:00:00-05:00'))
    assert a==b and original==before


def test_r13_template_withholds_unqualified_funding_and_old_daily_flow():
    s=TEMPLATE.read_text();desk=s.split('id="derivatives-desk"',1)[1].split('id="onchain-lab"',1)[0]
    assert 'data-flow-context' in desk and 'data-flow-evidence' in desk
    assert 'derivatives_flow' in desk
    assert 'leverage.funding_annual' not in desk and 'leverage.okx_taker_buy' not in desk
    assert 'Settlement interval not established' in desk
    assert 'Not spot flow or a trading signal' in desk
    assert 'No activity observed' in desk and 'Stale observations' in desk
    assert 'net_flow_24h_mn' not in desk and 'confidence' not in desk
    builder=(ROOT/'scripts/build_vector.py').read_text()
    assert '"derivatives_flow": _derivatives_flow_view(regime)' in builder


def test_r13_mobile_hero_override_follows_shared_desktop_rule():
    """Regression for a visually observed shared-style specificity collision."""
    source=TEMPLATE.read_text(encoding='utf-8')
    tail=source.split('{% include "_crypto_house_style.html.j2" %}',1)[1].split('</style>',1)[0]
    assert '@media(max-width:780px)' in tail
    assert 'body.page-vector .hero-read{grid-template-columns:minmax(0,1fr)' in tail
    assert 'body.page-vector .hero-read>div{min-width:0}' in tail
