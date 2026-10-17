"""Execute Desk Watch's actual startup/fetch/render path without network or signals.

Only DOM storage and fetch responses are doubled. Production functions are neither
extracted nor reimplemented, and no test-only API is added to the client.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "desk_watch.js"
SITE = ROOT / "site" / "desk_watch.js"

DRIVER = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const args = JSON.parse(fs.readFileSync(0, 'utf8'));
const requests = [];
const content = {innerHTML: ''};
const elements = {};
let observer;
const host = {};
Object.defineProperty(host, 'innerHTML', {set(value) {
  elements['desk-watch'] = {};
  elements['dw-content'] = content;
  content.innerHTML = value;
}});
elements['desk-watch-mount'] = host;
const document = {
  readyState: 'complete',
  documentElement: {getAttribute: () => args.lang},
  getElementById: id => elements[id] || null,
  createElement: () => ({}),
  head: {appendChild: element => {elements[element.id] = element;}},
};
const responses = args.feeds;
const before = JSON.stringify(responses);
const context = {
  document,
  MutationObserver: class {constructor(callback) {observer = callback;} observe() {}},
  fetch: async (url, options) => {
    requests.push({url, options});
    const response = responses[url.includes('oracle_turn_desk') ? 0 : 1];
    if (response.failure === 'network') throw new Error('offline');
    return {ok: !response.failure || response.failure === 'json',
      status: response.status || 200,
      json: async () => {
        if (response.failure === 'json') throw new SyntaxError('invalid JSON');
        return response.data;
      }};
  },
};
vm.runInNewContext(fs.readFileSync(args.path, 'utf8'), context, {filename: args.path});
setImmediate(() => {
  console.log(JSON.stringify({html: content.innerHTML, requests,
    unchanged: before === JSON.stringify(responses), observer: !!observer}));
});
"""

EMPTY_TD = {"schema": "oracle_turn_desk.v1", "asof": "2026-10-08", "armed": []}
EMPTY_TPO = {"schema": "oracle_tape_onset.v1", "asof": "2026-10-08", "nodes": {}}
FULL_TD = {
    **EMPTY_TD,
    "armed": [{"node": "XLK", "name_en": "Technology", "name_zh": "科技",
               "sessions_remaining": 3, "member_fires": [{"ticker": "MSFT", "tier": "T1"}],
               "qual_filters_true": []}],
}
FULL_TPO = {
    **EMPTY_TPO,
    "nodes": {"XLP": {"tape_onset_unconfirmed": True, "tape_onset_stats": {
        "n_flags": 928, "p_onset_5d": 0.7346, "false_positive_5d": 0.2654,
        "p_confirmed_10d": None, "window_start": "1998-12-22", "window_end": "2026-10-08"}}},
}


def response(data):
    return {"data": copy.deepcopy(data)}


def run_client(feeds, lang="en", path=TEMPLATE):
    completed = subprocess.run(
        ["node", "-e", DRIVER],
        input=json.dumps({"feeds": feeds, "lang": lang, "path": str(path)}),
        text=True, capture_output=True, check=True, timeout=10,
    )
    result = json.loads(completed.stdout)
    assert result["unchanged"], "presentation must never mutate producer payloads"
    assert result["observer"], "existing language/theme reload hook must remain wired"
    assert result["requests"] == [
        {"url": "basketdata/oracle_turn_desk.json", "options": {"cache": "no-cache"}},
        {"url": "basketdata/oracle_tape_onset.json", "options": {"cache": "no-cache"}},
    ]
    return result["html"]


TRANSPORT_FAILURES = [
    pytest.param({"failure": "network"}, id="network"),
    pytest.param({"failure": "json"}, id="invalid-json"),
    *[pytest.param({"failure": "http", "status": status}, id=f"http-{status}")
      for status in (401, 403, 404, 500)],
]
MALFORMED_TD = [
    None, [], False, "payload", {}, {"armed": None}, {"armed": {}},
    {"armed": ""}, {"armed": [None]}, {"armed": [[]]},
    # Step 19 may augment a missing Turn Desk artifact. This additive field is
    # not the Step 15 armed-window collection and cannot establish zero windows.
    {"tape_onset_nodes": FULL_TPO["nodes"]},
    {"armed": [{"node": "XLK", "member_fires": "bad"}]},
    {"armed": [{"node": "XLK", "member_fires": [None]}]},
    {"armed": [{"node": "XLK", "qual_filters_true": "bad"}]},
    {"armed": [], "base_rates": {"holdout_delta_pp": "bad"}},
    {"armed": [], "base_rates": {"in_window_wr21": "bad"}},
    {"armed": [], "base_rates": []},
    {"armed": [{"node": "XLK", "member_fires": {"ticker": "MSFT"}}]},
    {"armed": [{"node": "XLK", "member_fires": False}]},
    {"armed": [{"node": "XLK", "qual_filters_true": {"F-Q2-RISKOFF": True}}]},
    {"armed": [{"node": "XLK", "qual_filters_true": [None]}]},
    {"armed": [], "asof": {"toString": None}},
    {"armed": [{"node": "XLK", "name_en": {"toString": None}, "name_zh": {"toString": None}}]},
]
MALFORMED_TPO = [
    None, [], False, "payload", {}, {"nodes": None}, {"nodes": []},
    {"nodes": ""}, {"nodes": {"XLP": None}}, {"nodes": {"XLP": []}},
    {"nodes": {"XLP": {}}}, {"nodes": {"XLP": {"tape_onset_unconfirmed": "false"}}},
    *[{"nodes": {"XLP": {"tape_onset_unconfirmed": True, "tape_onset_stats": stats}}}
      for stats in ([], "bad", {"p_onset_5d": "bad"}, {"p_confirmed_10d": True},
                    {"false_positive_5d": {}}, {"n_flags": "bad"})],
    {"nodes": FULL_TPO["nodes"], "asof": {"toString": None}},
    {"nodes": {"XLP": {"tape_onset_unconfirmed": True,
                         "tape_onset_stats": {"window_start": {"toString": None}}}}},
]


def assert_unavailable(html, feed):
    if feed == 0:
        assert "Armed-window data unavailable." in html
        assert "入场窗口数据暂不可用。" in html
        assert "No sectors armed right now" not in html
    else:
        assert "Early-flow data unavailable." in html
        assert "早期资金信号数据暂不可用。" in html
        assert "No early flow signs right now" not in html
    assert "No armed windows and no early flow signs" not in html


def assert_sibling(html, failed_feed, populated, lang):
    if failed_feed == 0:
        if populated:
            assert 'class="tpo-node-card"' in html
            assert ("Cons Staples" if lang == "en" else "必需消费") in html
            assert "73.5%" in html and "26.5%" in html
        else:
            assert "No early flow signs right now" in html
        assert 'class="td-sector-card"' not in html
        assert "65.2%" not in html, "rejected Turn Desk must not lend base-rate fallback claims"
    else:
        if populated:
            assert 'class="td-sector-card"' in html
            assert ("Technology" if lang == "en" else "科技") in html
            assert "MSFT" in html and "T1" in html
        else:
            assert "No sectors armed right now" in html
        assert 'class="tpo-node-card"' not in html


@pytest.mark.parametrize("lang", ["en", "zh"])
@pytest.mark.parametrize("failed_feed", [0, 1])
@pytest.mark.parametrize("populated", [False, True])
@pytest.mark.parametrize("failure", TRANSPORT_FAILURES)
def test_partial_fetch_failure_does_not_claim_quiet_or_hide_sibling(lang, failed_feed, populated, failure):
    feeds = [response(FULL_TD if populated else EMPTY_TD), response(FULL_TPO if populated else EMPTY_TPO)]
    feeds[failed_feed] = failure
    html = run_client(feeds, lang)
    assert_unavailable(html, failed_feed)
    assert_sibling(html, failed_feed, populated, lang)


@pytest.mark.parametrize("lang", ["en", "zh"])
@pytest.mark.parametrize("populated", [False, True])
@pytest.mark.parametrize("bad", MALFORMED_TD)
def test_malformed_turn_desk_is_unavailable_without_hiding_onset(lang, populated, bad):
    html = run_client([response(bad), response(FULL_TPO if populated else EMPTY_TPO)], lang)
    assert_unavailable(html, 0)
    assert_sibling(html, 0, populated, lang)


@pytest.mark.parametrize("lang", ["en", "zh"])
@pytest.mark.parametrize("populated", [False, True])
@pytest.mark.parametrize("bad", MALFORMED_TPO)
def test_malformed_onset_is_unavailable_without_hiding_turn_desk(lang, populated, bad):
    html = run_client([response(FULL_TD if populated else EMPTY_TD), response(bad)], lang)
    assert_unavailable(html, 1)
    assert_sibling(html, 1, populated, lang)


@pytest.mark.parametrize("failure", TRANSPORT_FAILURES)
def test_both_fetches_failed_uses_existing_unavailable_copy(failure):
    html = run_client([failure, failure])
    assert "Desk-watch data unavailable." in html
    assert "值守台数据暂不可用。" in html
    assert "quiet" not in html.replace('class="dw-quiet"', '')
    assert "as of" not in html


@pytest.mark.parametrize("lang", ["en", "zh"])
@pytest.mark.parametrize("td_populated,tpo_populated", [(False, False), (True, False), (False, True), (True, True)])
def test_successful_empty_and_populated_feeds_retain_existing_output(lang, td_populated, tpo_populated):
    td = copy.deepcopy(FULL_TD if td_populated else EMPTY_TD)
    # These are lawful additive fields from producer Step 19 / artifact stamps.
    td.update(tape_onset_nodes=FULL_TPO["nodes"], produced_by="oracle-nightly", schema_version="1")
    html = run_client([response(td), response(FULL_TPO if tpo_populated else EMPTY_TPO)], lang)
    assert "unavailable" not in html
    assert ('class="td-sector-card"' in html) == td_populated
    assert ('class="tpo-node-card"' in html) == tpo_populated
    if not td_populated and not tpo_populated:
        assert "No armed windows and no early flow signs right now" in html
        assert "当前无已武装窗口，也无最早期资金迹象" in html
    assert "2026-10-08" in html


def test_false_flags_in_successful_onset_are_a_real_empty_result():
    onset = copy.deepcopy(FULL_TPO)
    onset["nodes"]["XLP"]["tape_onset_unconfirmed"] = False
    html = run_client([response(EMPTY_TD), response(onset)])
    assert "No armed windows and no early flow signs right now" in html
    assert "unavailable" not in html


@pytest.mark.parametrize("stats", [None, {}, {"p_onset_5d": None, "false_positive_5d": None,
                                          "p_confirmed_10d": None, "n_flags": None}])
def test_missing_or_null_onset_rates_remain_valid_unavailable_metrics(stats):
    onset = {"nodes": {"XLK": {"tape_onset_unconfirmed": True, "tape_onset_stats": stats}}}
    html = run_client([response(EMPTY_TD), response(onset)])
    assert 'class="tpo-node-card"' in html
    assert "5d onset rate: </b>—" in html
    assert "NaN" not in html and "unavailable" not in html


@pytest.mark.parametrize("fields", [{}, {"member_fires": None, "qual_filters_true": None},
                                   {"member_fires": [], "qual_filters_true": []}])
def test_optional_member_collections_remain_compatible(fields):
    td = {"armed": [{"node": "XLK", "sessions_remaining": 3, **fields}]}
    html = run_client([response(td), response(EMPTY_TPO)])
    assert 'class="td-sector-card"' in html and "unavailable" not in html


@pytest.mark.parametrize("asof", [None, "", "2026-10-08"])
def test_optional_string_clocks_remain_compatible(asof):
    td = {**FULL_TD, "asof": asof}
    tpo = {**FULL_TPO, "asof": asof}
    html = run_client([response(td), response(tpo)])
    assert 'class="td-sector-card"' in html and 'class="tpo-node-card"' in html
    assert "unavailable" not in html


def test_source_and_published_client_are_byte_identical():
    assert TEMPLATE.read_bytes() == SITE.read_bytes()
