"""Actual usage-ledger -> Admin projection -> actual JavaScript cost view."""
from __future__ import annotations
import json
from pathlib import Path
import shutil
import subprocess

import pytest
from admin import ai_cost
from lib import ai_costs


@pytest.fixture
def costs(tmp_path, monkeypatch):
    data = tmp_path / "data"
    monkeypatch.setattr(ai_cost, "ROOT", tmp_path)
    monkeypatch.setattr(ai_cost, "DATA", data)
    monkeypatch.setenv("AI_COSTS_STATE_ROOT", str(tmp_path / "cost-state"))
    monkeypatch.setattr(ai_costs, "estimate_cost_usd", lambda *a, **k: None)

    def write(name, document):
        target = data / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(document))

    def record(*, basis="unknown", amount=None):
        assert ai_costs.record_usage(lane="brain", stage="chat", provider="go",
            model="actual-model", key_id="fabric:test", input_tokens=11, output_tokens=7,
            cost_basis=basis, est_cost_usd=amount, root=tmp_path)

    def project():
        result = ai_cost.unified()
        assert result is not None
        return result

    return record, write, project


def render(value):
    node = shutil.which("node")
    assert node, "Node is required by this registered render proof"
    result = subprocess.run([node, str(Path(__file__).with_suffix(".js"))],
        input=json.dumps({"unified": value}), text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    return result.stdout


def card(html, title):
    marker = '<section data-card="' + title + '">'
    assert marker in html
    return html.split(marker, 1)[1].split("</section>", 1)[0]


@pytest.mark.parametrize("basis", ["unknown", "metered", "subscription"])
def test_unpriced_usage_survives_every_projection_and_billing_card(costs, basis):
    record, _, project = costs
    record(basis=basis)
    value = project()
    assert value["totals"]["unpriced_calls"] == 1
    assert value["cost_basis"][basis]["unpriced_calls"] == 1
    assert value["providers"][0]["unpriced_calls"] == 1
    assert value["models"][0]["unpriced_calls"] == 1
    assert value["keys"][0]["unpriced_calls"] == 1
    assert value["lobes"][0]["unpriced_calls"] == 1
    html = render(value)
    assert "Unpriced · 1 calls" in card(html, "30-day known cost estimate")
    title = {"metered": "Metered estimate · ledger",
             "subscription": "Subscription-equivalent · ledger"}.get(basis)
    if title:
        assert "Unpriced · 1 calls" in card(html, title)
    if basis == "unknown":
        assert "Billing basis (ledger · 30d)" in html and ">unknown<" in html
    assert value["recent"][0]["est_cost_usd"] is None


def test_mixed_known_and_unpriced_cost_is_a_known_subtotal(costs):
    record, _, project = costs
    record(basis="metered", amount=2.5)
    record()
    value = project()
    assert value["totals"]["usd"] == 2.5
    assert value["totals"]["calls"] == 2 and value["totals"]["unpriced_calls"] == 1
    html = render(value)
    assert "$2.5 known · 1 unpriced calls" in card(html, "30-day known cost estimate")


def test_known_zero_cost_is_distinct_from_empty_and_unpriced(costs):
    record, _, project = costs
    empty = render(project())
    assert "No recorded calls" in card(empty, "30-day known cost estimate")
    record(basis="local", amount=0)
    value = project()
    assert value["totals"]["unpriced_calls"] == 0
    headline = card(render(value), "30-day known cost estimate")
    assert "$0" in headline and "Unpriced" not in headline and "No recorded calls" not in headline


@pytest.mark.parametrize("amount", [None, 0.0, 1.25])
def test_external_price_and_per_book_count_remain_truthful(costs, amount):
    _, write, project = costs
    write("mastermind/cost_summary.json", {"as_of": "2026-11-06T00:00:00Z",
        "totals_30d": {"usd": amount, "input_tokens": 100, "by_book": {"US": amount}}})
    value = project()
    lobe = next(row for row in value["lobes"] if row["source"] == "bot")
    source = next(row for row in value["sources"] if row["key"] == "bot")
    assert lobe["usd"] == source["usd_30d"] == amount
    assert lobe["no_usd"] is (amount is None)
    assert lobe["calls"] is None and lobe["lanes"][0]["calls"] is None
    assert lobe["lanes"][0]["usd"] == amount
    assert value["totals"]["unpriced_coverage_complete"] is False
    assert value["totals"]["calls_coverage_complete"] is False
    # No billing-basis inference from an external aggregate.
    assert value["totals"]["subscription_usd"] == 0
    html = render(value)
    bot = html.split('<b>Mastermind · bot</b>', 1)[1].split("</details>", 1)[0]
    assert "Call count unavailable" in bot
    if amount is None:
        assert "Cost unavailable" in bot and "$0" not in bot
        assert "Cost unavailable" in card(html, "30-day known cost estimate")
    else:
        assert "$" + str(amount).removesuffix(".0") in bot
        assert "No recorded calls" not in bot


def test_calls_only_external_observation_is_retained(costs):
    _, write, project = costs
    write("mastermind/cost_summary.json", {"totals_30d": {},
        "days": {"2026-11-06": {"autonomous": {"calls": 3}}}})
    value = project()
    bot = next(row for row in value["lobes"] if row["source"] == "bot")
    assert bot["calls"] == 3 and bot["usd"] is None and bot["no_usd"]
    assert value["totals"]["calls"] == 3
    assert value["totals"]["unpriced_coverage_complete"] is False
    assert "Cost unavailable" in render(value)


def test_codex_rate_limit_usage_keeps_unavailable_cost(costs):
    _, write, project = costs
    write("codex_lane/usage_state.json", {"token_usage_last": {"total_tokens": 27},
        "sessions": ["observed-session"], "plan_type": "fixture"})
    value = project()
    codex = next(row for row in value["lobes"] if row["source"] == "codex")
    assert codex["no_usd"] is True and codex["tokens"] == 27
    assert "Cost unavailable" in render(value)
