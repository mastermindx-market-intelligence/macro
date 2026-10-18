"""Real shared-widget lifecycle tests with an explicitly synthetic transport.

These exercise the actual widget and host callback boundary. They do not establish
production authentication, model selection, market data or chart pixel execution.
"""
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

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
  anchor: 'top', api: '', symbol: function () { return 'NVDA'; },
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
        window.emitBrain({type: 'done', citations: []});
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
    # The synthetic host declares its known guest principal through the public API.
    page.evaluate("MMBrain.setPrincipal(null); MMBrain.open()")
    page.locator("#mmb-ta").wait_for(state="visible")


@pytest.fixture
def page():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
        context.add_init_script(SETUP)
        page = context.new_page()

        def route(request):
            if request.request.url.endswith("/mm_brain.js"):
                request.fulfill(path=str(ROOT / "templates/mm_brain.js"), content_type="application/javascript")
            else:
                request.fulfill(body='<html data-theme="dark" data-lang="en"><head></head><body><script src="/mm_brain.js"></script></body></html>', content_type="text/html")

        page.route("http://brain.test/**", route)
        page.goto("http://brain.test/")
        open_widget(page)
        yield page
        context.close()
        browser.close()


def send(page):
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


def test_buffered_chart_events_after_done_cannot_repeat_completed_effects(page):
    send(page)
    applied = command("handed_before_done")
    emit(page, applied)
    page.wait_for_function("window.chartCalls.length === 1")
    page.evaluate("""events => window.streamController.enqueue(new TextEncoder().encode(
      events.map(event => 'data: ' + JSON.stringify(event) + '\\n\\n').join('')
    ))""", [
        {"type": "delta", "text": "The completed chart analysis."},
        {"type": "done", "citations": []},
        command("buffered_after_done"),
        {"type": "annotate", "symbol": "NVDA", "annotations": []},
    ])
    page.get_by_text("The completed chart analysis.", exact=True).wait_for()
    page.wait_for_timeout(80)
    assert page.evaluate("window.chartCalls") == [applied]
    assert page.evaluate("window.chartStops") == []
    assert page.evaluate("window.cancelRequests") == []
    assert page.locator(".mmb-msg.user").count() == 1


def test_previous_principals_buffered_chart_events_cannot_reach_the_host(page):
    send(page)
    page.evaluate("MMBrain.setPrincipal('user-B')")
    page.evaluate("""events => window.streamController.enqueue(new TextEncoder().encode(
      events.map(event => 'data: ' + JSON.stringify(event) + '\\n\\n').join('')
    ))""", [
        {"type": "run", "run_id": RUN},
        command("previous_principal"),
        {"type": "annotate", "symbol": "NVDA", "annotations": []},
        {"type": "delta", "text": "Previous principal's private answer."},
        {"type": "done", "citations": []},
    ])
    page.wait_for_timeout(80)
    assert page.evaluate("window.chartCalls") == []
    assert "Previous principal's private answer." not in page.locator("#mmb-scroll").inner_text()
    assert QUESTION not in page.locator("#mmb-scroll").inner_text()
    assert page.evaluate("sessionStorage.getItem('mm.brain.run.v2:user:user-B')") is None
