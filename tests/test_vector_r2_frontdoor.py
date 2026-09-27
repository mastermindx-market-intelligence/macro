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
    }
    for step in job["steps"]:
        command = shlex.split(step.get("run", ""))
        if command[:3] == ["python", "-m", "pytest"] and required.issubset(command):
            assert "if" not in step, "Vector regression invocation must not be conditional"
            assert not step.get("continue-on-error", False), "Regressions must fail the step"
            break
    else:
        raise AssertionError("R2 regressions are not invoked by the existing Vector CI owner")
