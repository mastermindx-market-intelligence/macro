"""Native synthetic owner integration; no actual label or production grants."""
import json
from pathlib import Path
import subprocess

import pytest

from engine.neuralweb import market_memory_outcome_inspection as inspection
from engine.neuralweb import market_memory_episode_outcomes as outcomes
from engine.neuralweb import market_memory_episode_features as features
from engine.neuralweb import market_memory_episode_retrieval as retrieval
from tests.test_market_memory_episode_features import Policy
from tests.test_market_memory_episode_outcomes import (
    CUTOFF, attach, corpus, prepare, published,  # noqa: F401 - real pytest fixtures
)


def test_observed_projection_preserves_original_selection_and_source_clocks(corpus, published):
    selection = corpus[2]
    original = retrieval.disclose_episode_retrieval(selection, policy=Policy())
    value = inspection.project_outcome_inspection(selection, attach(corpus, published), policy=Policy())
    assert value["schema"] == "market_memory.outcome_inspection.v1"
    assert value["selection_sha256"] == original["selection_sha256"]
    row, selected = value["rows"][0], original["selected"][0]
    assert row["context_id"] == selected["candidate"]["context_id"]
    assert row["comparison_id"] == selected["comparison_id"]
    assert row["distance_q18"] == selected["distance_q18"]
    assert row["status"] == "observed" and row["value_q18"] is not None
    assert row["observation"]["clocks"]["published_at"] == "2026-08-21T00:00:00Z"
    assert value["metric"] == "archived_close_ratio"
    assert value["effective_n"] == "not_estimated"
    assert all(value[key] is False for key in
               ("economic_return", "corporate_action_adjusted", "RTH_close_authenticated"))
    assert "observation_generation_ref" not in value
    assert "technical_generation" not in value and "source_marks" not in row
    row["observation"]["clocks"].clear()
    assert inspection.project_outcome_inspection(selection, attach(corpus, published),
                                                 policy=Policy())["rows"][0]["observation"]["clocks"]
    assert retrieval.disclose_episode_retrieval(selection, policy=Policy()) == original


def test_then_known_future_and_absent_observation_are_indistinguishable(corpus, published):
    present = attach(corpus, published, lens="then_known", cutoff=CUTOFF)
    absent = attach(corpus, published, lens="then_known", cutoff=CUTOFF, ids=(None,))
    left = inspection.project_outcome_inspection(corpus[2], present, policy=Policy())
    right = inspection.project_outcome_inspection(corpus[2], absent, policy=Policy())
    assert left == right
    assert left["rows"][0]["value_q18"] is None
    assert left["rows"][0]["observation"] is None
    assert left["rows"][0]["reason"] == "not_visible_at_query"


@pytest.mark.parametrize("action", ["read_registered_contextual_outcome_labels",
    "read_retained_source_bar_marks", "disclose_retained_source_bar_marks",
    "disclose_retained_contextual_observation", "compare_retained_macro_feature"])
def test_current_original_purposes_are_required_after_capability_creation(corpus, published, action):
    attachment = attach(corpus, published)
    expected = features.EpisodeFeatureAccessError if action == "compare_retained_macro_feature" else PermissionError
    with pytest.raises(expected):
        inspection.project_outcome_inspection(corpus[2], attachment, policy=Policy({action}))


def test_json_and_preparation_cannot_become_public_observation(corpus, published):
    attachment = attach(corpus, published)
    for invalid in (json.loads(attachment._body), prepare(corpus)):
        with pytest.raises(outcomes.EpisodeOutcomeError):
            inspection.project_outcome_inspection(corpus[2], invalid, policy=Policy())


def test_changed_selection_is_rejected_before_projection(corpus, published, monkeypatch):
    attachment = attach(corpus, published)
    original = retrieval.disclose_episode_retrieval
    calls = 0
    def changed(cap, *, policy):
        nonlocal calls
        value = original(cap, policy=policy)
        calls += 1
        if calls == 1:
            value["selection_sha256"] = "f" * 64
        return value
    monkeypatch.setattr(retrieval, "disclose_episode_retrieval", changed)
    with pytest.raises(outcomes.EpisodeOutcomeError, match="exact_inspection_selection"):
        inspection.project_outcome_inspection(corpus[2], attachment, policy=Policy())


def test_native_projection_browser_contract_and_paper_view(corpus, published):
    """Exercise real sealed owners through the production JS, not a wire mock."""
    observed = inspection.project_outcome_inspection(corpus[2], attach(corpus, published), policy=Policy())
    then = inspection.project_outcome_inspection(corpus[2],
        attach(corpus, published, lens="then_known", cutoff=CUTOFF), policy=Policy())
    absent = inspection.project_outcome_inspection(corpus[2],
        attach(corpus, published, lens="then_known", cutoff=CUTOFF, ids=(None,)), policy=Policy())
    script = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const contract = require('./templates/market_memory_outcome_contract.js');
const view = require('./templates/market_memory_outcome_view.js');
const [observed, then, absent] = JSON.parse(fs.readFileSync(0, 'utf8'));
function expected(value) {
  return { retrievalId: value.retrieval_id, selectionSha256: value.selection_sha256,
    queryCutoff: value.query_cutoff, outcomeCutoff: value.outcome_cutoff, lens: value.lens,
    definitionSha256: value.definition_sha256, neighbors: value.rows.map(row => ({
      contextId: row.context_id, captureId: row.capture_id, packetSha256: row.packet_sha256,
      comparisonId: row.comparison_id, distanceQ18: row.distance_q18 })) };
}
const labels = observed.rows.map(row => ({ contextId: row.context_id, label: '<img src=x onerror=alert(1)>' }));
for (const locale of ['en', 'zh']) {
  const html = view.render(observed, expected(observed), labels, locale);
  assert(html.includes(contract.formatRatio(observed.rows[0].value_q18)));
  assert(html.includes(observed.rows[0].observation.clocks.published_at));
  assert(html.includes(observed.rows[0].observation.id));
  assert(html.includes('&lt;img src=x onerror=alert(1)&gt;'));
  assert(!html.includes('<img'));
  assert(!html.includes('undefined'));
  assert(!html.includes('onclick='));
  assert.equal(view.render(then, expected(then), labels, locale),
               view.render(absent, expected(absent), labels, locale));
  const pending = view.render(then, expected(then), labels, locale);
  assert(!pending.includes(observed.rows[0].observation.id));
  assert(!pending.includes('mmr-outcome-ratio'));
}
assert.throws(() => view.render(observed, expected(observed), [], 'en'), /case_binding/);
const tampered = structuredClone(observed);
tampered.rows[0].observation.clocks.recorded_at = '2027-01-01T00:00:00Z';
assert.throws(() => view.render(tampered, expected(observed), labels, 'en'), /outcome_contract:/);
console.log('native projection, EN/ZH view, escaping, future redaction and exact binding PASS');
"""
    result = subprocess.run(["node", "-e", script], input=json.dumps([observed, then, absent]),
        text=True, capture_output=True, cwd=Path(__file__).resolve().parents[1], timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
