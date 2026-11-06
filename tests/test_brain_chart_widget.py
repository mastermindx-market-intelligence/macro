"""Real shared-widget lifecycle tests with an explicitly synthetic transport.

These exercise the actual widget and host callback boundary. They do not establish
production authentication, model selection, market data or chart pixel execution.
"""
import json
from pathlib import Path
from urllib.parse import urlparse

import pytest
from playwright.sync_api import expect, sync_playwright
from tests.test_brain_visuals_browser import sample

ROOT = Path(__file__).resolve().parents[1]
RUN = "a" * 32
QUESTION = "Add the requested study to this chart."

SETUP = r"""
window.chartCalls = [];
window.chartStops = [];
window.cancelRequests = [];
window.streamController = null;
window.emitBrain = function (event) {
  window.streamController.enqueue(new TextEncoder().encode('data: ' + JSON.stringify(event) + '\n\n'));
};
window.MM_BRAIN_CFG = {
  anchor: 'top', api: '', principal: null, symbol: function () { return 'NVDA'; },
  onCommand: function (event) { window.chartCalls.push(event); },
  onAnnotate: function (event) { window.chartCalls.push(event); },
  onChartStop: function (request) {
    window.chartStops.push(request);
    return {scope: 'received_batches', cancelled: 1};
  }
};
window.fetch = function (input, options) {
  var url = new URL(String(input), location.href), path = url.pathname;
  var json = function (value) { return Promise.resolve(new Response(JSON.stringify(value), {
    status: 200, headers: {'Content-Type': 'application/json'}
  })); };
  if (path.endsWith('/me')) return json({tier: 'guest', quotas: {
    fast: {remaining: 30, limit: 30, period: 'day'}, pro: {remaining: 0, limit: 0, period: 'day'}
  }});
  if (path.endsWith('/cancel')) { window.cancelRequests.push(path); return json({cancelled: true}); }
  if (path.endsWith('/threads')) return json({threads: []});
  var isNew = path === '/api/brain/stream';
  if (isNew || /\/runs\/[^/]+\/stream$/.test(path)) {
    var stream = new ReadableStream({start: function (controller) {
      window.streamController = controller;
      if (isNew) window.emitBrain({type: 'run', run_id: 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'});
      else {
        window.emitBrain({type: 'command', v: 2, op: 'chart.set_tf', args: {tf: 'W'}, batch_id: 'old_batch', seq: 0});
        window.emitBrain({type: 'annotate', symbol: 'NVDA', annotations: []});
        window.emitBrain({type: 'delta', text: 'Recovered answer with its original evidence.'});
        if (window.recoveryVisual) window.emitBrain(window.recoveryVisual);
        window.emitBrain({type: 'done', citations: [], charts: window.recoveryVisual ? [window.recoveryVisual] : []});
        controller.close();
      }
    }});
    return Promise.resolve(new Response(stream, {status: 200, headers: {'Content-Type': 'text/event-stream'}}));
  }
  if (/\/runs\/[^/]+$/.test(path)) return json({
    run_id: 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', thread_id: null, done: false, cancelled: false, lane: 'fast'
  });
  return json({});
};
"""


def open_widget(page):
    page.wait_for_function("Boolean(window.MMBrain)")
    page.evaluate("MMBrain.open()")
    page.locator("#mmb-ta").wait_for(state="visible")


@pytest.fixture
def page():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
        context.add_init_script(SETUP)
        page = context.new_page()

        def route(request):
            asset = urlparse(request.request.url).path.lstrip("/")
            if asset in ("mm_brain.js", "mm_brain_visuals.js", "mm_brain_visuals.css"):
                request.fulfill(path=str(ROOT / "templates" / asset),
                                content_type="text/css" if asset.endswith(".css") else "application/javascript")
            else:
                request.fulfill(body='<html data-theme="dark" data-lang="en"><head></head><body><script src="/mm_brain.js"></script></body></html>', content_type="text/html")

        page.route("http://brain.test/**", route)
        page.goto("http://brain.test/")
        open_widget(page)
        yield page
        context.close()
        browser.close()


def send(page):
    page.evaluate("window.streamController = null")
    page.locator("#mmb-ta").fill(QUESTION)
    page.locator("#mmb-send").click()
    page.wait_for_function("Boolean(window.streamController)")


def emit(page, event):
    page.evaluate("event => window.emitBrain(event)", event)


def command(batch="this_turn"):
    return {"type": "command", "v": 2, "op": "chart.set_tf", "args": {"tf": "W"}, "batch_id": batch, "seq": 0}


def test_stop_after_chart_handoff_keeps_question_and_cancels_only_received_batches(page):
    send(page)
    emit(page, command())
    page.wait_for_function("window.chartCalls.length === 1")
    page.locator("#mmb-send").click()
    assert page.locator(".mmb-msg.user").count() == 1
    assert QUESTION in page.locator("#mmb-scroll").inner_text()
    assert page.locator("#mmb-ta").input_value() == ""
    assert page.evaluate("window.chartStops") == [{"scope": "received_batches", "batch_ids": ["this_turn"]}]
    assert "already applied" in page.locator("#mmb-scroll").inner_text()


def test_early_stop_without_chart_handoff_still_restores_the_prompt(page):
    send(page)
    page.locator("#mmb-send").click()
    assert page.locator(".mmb-msg.user").count() == 0
    assert page.locator("#mmb-ta").input_value() == QUESTION
    assert page.evaluate("window.chartStops") == []


def test_late_buffered_chart_event_cannot_mutate_after_stop(page):
    send(page)
    page.locator("#mmb-send").click()
    emit(page, command("arrived_after_stop"))
    page.wait_for_timeout(80)
    assert page.evaluate("window.chartCalls") == []


def test_cold_recovery_restores_answer_without_replaying_chart_actions(page):
    page.evaluate("([id, q]) => sessionStorage.setItem('mm.brain.run.v2:guest', JSON.stringify({id, q, cursor: 0, ts: Date.now()}))", [RUN, QUESTION])
    page.reload()
    open_widget(page)
    page.get_by_text("Recovered answer with its original evidence.", exact=True).wait_for()
    assert page.evaluate("window.chartCalls") == []
    assert "not replayed" in page.locator("#mmb-scroll").inner_text()


def test_completion_wins_a_stop_race_without_cancelling_or_marking_the_answer(page):
    send(page)
    emit(page, {"type": "delta", "text": "The completed answer."})
    emit(page, {"type": "done", "citations": []})
    page.get_by_text("The completed answer.", exact=True).wait_for()
    page.locator("#mmb-send").click()
    assert page.evaluate("window.cancelRequests") == []
    assert page.locator(".mmb-stopped").count() == 0


def test_mixed_completed_answer_keeps_visual_and_allows_a_fresh_chart_turn(page):
    wire = sample(identity="mixed-completed")
    send(page)
    emit(page, command())
    emit(page, {"type": "delta", "text": "The chart change has a separate receipt. This is an illustrative comparison."})
    emit(page, wire)
    emit(page, {"type": "done", "citations": [], "charts": [wire]})
    expect(page.locator(".mmb-v")).to_have_count(1)
    expect(page.locator(".mmb-v-plot svg")).to_be_visible()
    emit(page, command("late_after_done"))
    page.wait_for_timeout(80)
    assert [c["batch_id"] for c in page.evaluate("window.chartCalls")] == ["this_turn"]
    page.evaluate("window.streamController.close()")
    page.wait_for_function("!document.querySelector('#mmb-send').classList.contains('mmb-stop')")
    send(page)
    emit(page, command("fresh_turn"))
    page.wait_for_function("window.chartCalls.length === 2")
    emit(page, {"type": "delta", "text": "A fresh chart request."})
    emit(page, {"type": "done", "citations": []})
    expect(page.locator(".mmb-v")).to_have_count(1)
    assert [c["batch_id"] for c in page.evaluate("window.chartCalls")] == ["this_turn", "fresh_turn"]
    assert page.evaluate("window.chartStops") == []


def test_mixed_stop_preserves_chart_effect_note_and_next_turn_still_works(page):
    wire = sample(identity="mixed-interrupted")
    send(page)
    emit(page, command())
    emit(page, {"type": "delta", "text": "The analysis is still in progress."})
    emit(page, wire)
    expect(page.locator(".mmb-v")).to_have_count(1)
    page.locator("#mmb-send").click()
    expect(page.locator(".mmb-v")).to_have_count(0)
    assert "already applied" in page.locator("#mmb-scroll").inner_text()
    page.evaluate("events => events.forEach(window.emitBrain)", [
        command("late_after_stop"), {"type": "done", "charts": [wire]},
    ])
    page.wait_for_timeout(80)
    expect(page.locator(".mmb-v")).to_have_count(0)
    assert [c["batch_id"] for c in page.evaluate("window.chartCalls")] == ["this_turn"]
    send(page)
    emit(page, command("fresh_after_stop"))
    page.wait_for_function("window.chartCalls.length === 2")
    emit(page, {"type": "delta", "text": "The next request is independent."})
    emit(page, {"type": "done", "citations": []})
    assert [c["batch_id"] for c in page.evaluate("window.chartCalls")] == ["this_turn", "fresh_after_stop"]
    assert page.evaluate("window.chartStops") == [{"scope": "received_batches", "batch_ids": ["this_turn"]}]


def test_cold_recovery_keeps_visual_without_actions_then_accepts_fresh_turn(page):
    wire = sample(identity="mixed-cold-recovery")
    page.context.add_init_script("window.recoveryVisual = " + json.dumps(wire) + ";")
    page.evaluate("([id, q]) => sessionStorage.setItem('mm.brain.run.v2:guest', JSON.stringify({id, q, cursor: 0, ts: Date.now()}))", [RUN, QUESTION])
    page.reload()
    open_widget(page)
    page.get_by_text("Recovered answer with its original evidence.", exact=True).wait_for()
    expect(page.locator(".mmb-v")).to_have_count(1)
    assert page.evaluate("window.chartCalls") == []
    assert "not replayed" in page.locator("#mmb-scroll").inner_text()
    send(page)
    emit(page, command("fresh_after_recovery"))
    page.wait_for_function("window.chartCalls.length === 1")
    emit(page, {"type": "delta", "text": "Only this fresh request reaches the chart."})
    emit(page, {"type": "done", "citations": []})
    expect(page.locator(".mmb-v")).to_have_count(1)
    assert [c["batch_id"] for c in page.evaluate("window.chartCalls")] == ["fresh_after_recovery"]
