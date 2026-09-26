"""Pure-text shape checks for the catalyst-links nightly step and CI job.

Does not import the engine. Reads the workflow files as text.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAILY = ROOT / ".github" / "workflows" / "daily.yml"
LEGACY = ROOT / ".github" / "ci" / "legacy-jobs.yml"
PYTEST_LINE = (
    "run: python -m pytest tests/test_build_options_catalyst_links.py "
    "tests/test_options_catalyst_link.py "
    "tests/test_options_catalyst_links_nightly_shape.py -q"
)


def test_daily_step_follows_episode_publish():
    text = DAILY.read_text()
    assert text.count("id: options_catalyst_links") == 1
    publish_at = text.index("id: options_signal_episode_publish")
    after = text[publish_at + len("id: options_signal_episode_publish"):]
    nxt = re.search(r"(?m)^[ ]+id: \S+", after)
    assert nxt is not None
    assert nxt.group(0).strip() == "id: options_catalyst_links"
    marker = text.index("id: options_catalyst_links")
    step_start = text.rfind("\n      - name:", 0, marker)
    next_step = text.find("\n      - name:", marker)
    block = text[step_start:next_step]
    assert "if: always()" in block
    assert "continue-on-error: true" in block
    assert "timeout-minutes: 5" in block
    for name in ("R2_ENDPOINT", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"):
        assert f"{name}: ${{{{ secrets.{name} }}}}" in block
    assert (
        'run: python -m scripts.build_options_catalyst_links || '
        'echo "::warning::build_options_catalyst_links non-fatal failure"'
    ) in block
    assert "consumes only the date-keyed events stage already read by the episode step" in block
    assert "writes site/options_catalyst_links/ only" in block
    assert "all authority false" in block
    assert "first production caller of engine/options_catalyst_link.py" in block


def test_legacy_job_is_gate_code_with_the_three_suites():
    lines = LEGACY.read_text().splitlines()
    hits = [index for index, line in enumerate(lines) if line == "  options-catalyst-links:"]
    assert hits == [hits[0]]
    job_line = hits[0]
    nearby = lines[job_line:job_line + 4]
    assert any(line.strip() == "gate: code" for line in nearby)
    end = next(
        index for index, line in enumerate(lines) if index > job_line and line.startswith("  ") and line.endswith(":") and not line.startswith("    ")
    )
    block = "\n".join(lines[job_line:end])
    assert "if: ${{ false }}" in block
    assert "runs-on: ubuntu-latest" in block
    assert 'python-version: "3.12"' in block
    assert "pip install pytest pandas numpy pyarrow pyyaml jinja2" in block
    assert "gate: data" not in block
    pytest_runs = [line.strip() for line in block.splitlines() if "python -m pytest" in line]
    assert pytest_runs == [PYTEST_LINE]
