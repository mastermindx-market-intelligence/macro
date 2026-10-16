"""In-flight dossier GET coalescing contract for the first
``createGovernmentRevenueDossier`` factory.

This suite reads ``templates/government-revenue-dossiers.js`` from disk (not
an embedded copy) so the contract under test is whatever is actually shipped.
Each case drives Node with a stubbed ``fetch`` and a sequenced ``MDXAuth``
client, then asserts on the captured fetch calls.

Coverage:

* overlapping same-auth same-route loads dedupe to one request per route,
  newest epoch renders
* differing auth tokens and anonymous each keep their own bucket
* failures evict from the pending bucket and a retry sees a fresh request
* post-settlement reads are fresh (no completed-response cache)
* mixed-generation responses remain fail-closed
* HTTP / schema / content-id contract checks remain fail-closed
* invalidating an old selection suppresses late rendering while the new
  selection continues to share its pending reads
* ``credentials:'same-origin'`` and the auth-bearing read shape are preserved
"""
from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from pathlib import Path
from typing import Any, Iterable

import pytest


ROOT = Path(__file__).resolve().parents[1]
DOSSIER_PATH = ROOT / "templates" / "government-revenue-dossiers.js"
DOSSIER_JS = DOSSIER_PATH.read_text(encoding="utf-8")
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")


# ---------------------------------------------------------------------------
# Fixture payload builders
# ---------------------------------------------------------------------------

def _prime(content_id: str = "grd1-" + "a" * 24, *, total: int = 2) -> dict:
    return {
        "schema_version": "1.0.0",
        "content_id": content_id,
        "company": {"action_count": 1},
        "results": [],
        "next_cursor": None,
        "total": total,
    }


def _dossier(content_id: str = "grd1-" + "a" * 24) -> dict:
    return {
        "schema_version": "1.0.0",
        "content_id": content_id,
        "company": {"action_count": 1},
    }


# ---------------------------------------------------------------------------
# Node runner helpers
# ---------------------------------------------------------------------------

PRELUDE = """
    var window = globalThis, calls = [], host;
    function obj(x){return !!x&&typeof x==='object'&&!Array.isArray(x)}
    function arr(x){return Array.isArray(x)?x:[]}
    function esc(x){return String(x==null?'':x).replace(/[&<>"']/g,function(c){return({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]})}
    function text(x,fb){return x==null||x===''?(fb==null?'—':fb):String(x)}
    function n(x){var v=Number(x);return Number.isFinite(v)?v:null}
    function money(x){return x==null?'—':'$'+Number(x).toLocaleString('en-US')}
    function date(x){return String(x||'—').slice(0,10)}
    function tr(x){return x}
    function safeUrl(x){try{var u=new URL(String(x));return u.protocol==='https:'?u.href:''}catch(e){return''}}
    function factCell(a,b){return'<div>'+esc(a)+': '+esc(b)+'</div>'}
"""


def _auth_stub(token_seq: Iterable[str | None]) -> str:
    """MDXAuth returning the next entry in ``token_seq`` for each caller.

    A ``None`` entry yields an anonymous session (no ``access_token``)."""
    seq = json.dumps([t if t is None else str(t) for t in token_seq])
    return textwrap.dedent(
        f"""
            var tokenQueue = {seq};
            var tokenIdx = 0;
            window.MDXAuth = {{
              enabled: function(){{ return true; }},
              client: function(){{
                return Promise.resolve({{
                  auth: {{
                    getSession: function(){{
                      var t = tokenQueue[tokenIdx++];
                      if (!t) return Promise.resolve({{data:{{session:null}}}});
                      return Promise.resolve({{data:{{session:{{access_token:t}}}}}});
                    }}
                  }}
                }});
              }}
            }};
        """
    )


def _fetch_stub(responses: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
            var responses = {json.dumps(responses)};
            window.fetch = function(url, opts){{
              calls.push({{
                url: url,
                authorization: (opts && opts.headers && opts.headers.Authorization) || '',
                credentials: opts ? opts.credentials : ''
              }});
              var value = responses[url];
              return Promise.resolve({{
                ok: !!value,
                status: value ? 200 : 404,
                json: function(){{ return Promise.resolve(value); }}
              }});
            }};
        """
    )


def _host_and_factory(selected: str = "company:LMT") -> str:
    return textwrap.dedent(
        f"""
            host = {{
              innerHTML: '',
              insertAdjacentHTML: function(_, x){{ this.innerHTML += x; }},
              querySelectorAll: function(){{ return []; }},
              querySelector: function(){{ return null; }}
            }};
            var selected = {json.dumps(selected)};
            var ui = window.createGovernmentRevenueDossier({{
              obj:obj, arr:arr, esc:esc, text:text, n:n, money:money,
              date:date, tr:tr, safeUrl:safeUrl, factCell:factCell,
              host:function(){{ return host; }},
              selected:function(){{ return selected; }},
              shellMode:function(){{}},
              openEvidenceDrawer:function(){{}}
            }});
        """
    )


def _settle_ms(token_seq_len: int) -> int:
    # Every withAuth call costs one microtask; fetches resolve synchronously
    # in the stub. The action body itself may carry its own `setTimeout`
    # (used by post-settlement, retry, contract tests); keep enough head
    # room for those inner timers (40ms each) to fire before we serialize.
    return max(80, token_seq_len * 2 + 60)


def run(action_js: str, *, responses: dict[str, Any], token_seq: Iterable[str | None],
        selected: str = "company:LMT") -> dict:
    """Compose and execute a Node script that captures fetch calls + html."""
    seq = list(token_seq)
    script = (
        PRELUDE
        + _auth_stub(seq)
        + _fetch_stub(responses)
        + "\n"
        + DOSSIER_JS
        + _host_and_factory(selected)
        + action_js
        + textwrap.dedent(
            f"""
                setTimeout(function(){{
                  process.stdout.write(JSON.stringify({{
                    calls: calls,
                    html: host.innerHTML
                  }}));
                }}, {_settle_ms(len(seq))});
            """
        )
    )
    result = subprocess.run(
        ["node", "-"], input=script,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, (
        f"node exited {result.returncode}\nstderr:\n{result.stderr}\nstdout:\n{result.stdout}"
    )
    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# Acceptance contract tests
# ---------------------------------------------------------------------------

@needs_node
def test_overlapping_same_auth_dedupes_to_one_request_per_route() -> None:
    """3 same-auth overlapping loadCompany calls dedupe to one fetch per route."""
    responses = {
        "/api/government-revenue/dossier/company/LMT": _dossier(),
        "/api/government-revenue/company/LMT/awards?limit=8": _prime(),
    }
    # 3 callers × 2 fetchPages each = 6 withAuth calls — all same bearer.
    out = run(
        action_js="ui.loadCompany('LMT'); ui.loadCompany('LMT'); ui.loadCompany('LMT');",
        responses=responses,
        token_seq=["t-A"] * 6,
    )
    urls = [c["url"] for c in out["calls"]]
    assert urls.count("/api/government-revenue/dossier/company/LMT") == 1, urls
    assert urls.count("/api/government-revenue/company/LMT/awards?limit=8") == 1, urls
    assert len(out["calls"]) == 2, urls
    # Credentials and Authorization shape are preserved.
    for c in out["calls"]:
        assert c["credentials"] == "same-origin"
        assert c["authorization"].startswith("Bearer ")


@needs_node
def test_overlapping_same_auth_renders_newest_epoch() -> None:
    """Newest ticket wins; older tickets are dropped without overwriting host."""
    responses = {
        "/api/government-revenue/dossier/company/LMT": _dossier(),
        "/api/government-revenue/company/LMT/awards?limit=8": _prime(),
    }
    out = run(
        action_js="ui.loadCompany('LMT'); ui.loadCompany('LMT'); ui.loadCompany('LMT');",
        responses=responses,
        token_seq=["t-A"] * 6,
    )
    assert "Official award book" in out["html"], out["html"]


@needs_node
def test_differing_auth_tokens_remain_separate() -> None:
    """Same route with two tokens must issue two fetches, never share."""
    responses = {
        "/api/government-revenue/dossier/company/LMT": _dossier(),
        "/api/government-revenue/company/LMT/awards?limit=8": _prime(),
    }
    # Caller A: 2 routes × same token A; Caller B: 2 routes × same token B.
    out = run(
        action_js="ui.loadCompany('LMT'); ui.loadCompany('LMT');",
        responses=responses,
        token_seq=["t-A", "t-A", "t-B", "t-B"],
    )
    urls = [c["url"] for c in out["calls"]]
    assert urls.count("/api/government-revenue/dossier/company/LMT") == 2, urls
    assert urls.count("/api/government-revenue/company/LMT/awards?limit=8") == 2, urls
    assert len(out["calls"]) == 4
    # Exactly two distinct Authorization values are observed across all calls.
    auths = sorted({c["authorization"] for c in out["calls"]})
    assert len(auths) == 2, auths


@needs_node
def test_anonymous_and_auth_remain_separate() -> None:
    """Anonymous and bearer-authed callers must not coalesce."""
    responses = {
        "/api/government-revenue/dossier/company/LMT": _dossier(),
        "/api/government-revenue/company/LMT/awards?limit=8": _prime(),
    }
    # Caller 1 anonymous, Caller 2 with token. withAuth order: anon, anon, t-A, t-A.
    out = run(
        action_js="ui.loadCompany('LMT'); ui.loadCompany('LMT');",
        responses=responses,
        token_seq=[None, None, "t-A", "t-A"],
    )
    urls = [c["url"] for c in out["calls"]]
    assert urls.count("/api/government-revenue/dossier/company/LMT") == 2, urls
    assert urls.count("/api/government-revenue/company/LMT/awards?limit=8") == 2, urls
    auths = [c["authorization"] for c in out["calls"]]
    assert auths.count("") == 2, auths
    assert sum(1 for a in auths if a.startswith("Bearer ")) == 2, auths


@needs_node
def test_failure_evicts_and_allows_retry() -> None:
    """A 404 rejection must not poison later requests on the same key."""
    responses: dict[str, Any] = {
        # First call gets a 404 (mapped to falsy value) on both routes;
        # retry hits the same URLs on the same auth and must see fresh requests.
        "/api/government-revenue/dossier/company/LMT": None,
        "/api/government-revenue/company/LMT/awards?limit=8": None,
    }
    action_js = textwrap.dedent(
        """
            ui.loadCompany('LMT');
            setTimeout(function(){
              var html_after_first = host.innerHTML;
              responses['/api/government-revenue/dossier/company/LMT'] = __SUCCESS__;
              responses['/api/government-revenue/company/LMT/awards?limit=8'] = __PRIME__;
              ui.loadCompany('LMT');
              setTimeout(function(){
                process.stdout.write(JSON.stringify({
                  calls: calls,
                  html_first: html_after_first,
                  html_last: host.innerHTML
                }));
              }, __SETTLE_MS__);
            }, __SETTLE_MS__);
        """
    ).replace(
        "__SUCCESS__", json.dumps(_dossier())
    ).replace(
        "__PRIME__", json.dumps(_prime())
    ).replace("__SETTLE_MS__", "40")
    # 4 withAuth calls per loadCompany × 2 = 8 total.
    seq = ["t-A"] * 8
    script = (
        PRELUDE
        + _auth_stub(seq)
        + _fetch_stub_with_responses_var(responses)
        + "\n"
        + DOSSIER_JS
        + _host_and_factory("company:LMT")
        + action_js
    )
    result = subprocess.run(
        ["node", "-"], input=script, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, (
        f"node exited {result.returncode}\nstderr:\n{result.stderr}\nstdout:\n{result.stdout}"
    )
    out = json.loads(result.stdout)
    urls = [c["url"] for c in out["calls"]]
    assert urls.count("/api/government-revenue/dossier/company/LMT") == 2, urls
    assert "Award book unavailable" in out["html_first"]
    assert "Official award book" in out["html_last"]


def _fetch_stub_with_responses_var(responses: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
            var responses = {json.dumps(responses)};
            window.fetch = function(url, opts){{
              calls.push({{
                url: url,
                authorization: (opts && opts.headers && opts.headers.Authorization) || '',
                credentials: opts ? opts.credentials : ''
              }});
              var value = responses[url];
              return Promise.resolve({{
                ok: !!value,
                status: value ? 200 : 404,
                json: function(){{ return Promise.resolve(value); }}
              }});
            }};
        """
    )


@needs_node
def test_post_settlement_reads_are_fresh() -> None:
    """Settled entries are evicted; subsequent calls do NOT see a stale promise."""
    responses = {
        "/api/government-revenue/dossier/company/LMT": _dossier(),
        "/api/government-revenue/company/LMT/awards?limit=8": _prime(),
    }
    out = run(
        action_js=textwrap.dedent(
            """
                ui.loadCompany('LMT');
                setTimeout(function(){
                  ui.loadCompany('LMT');
                }, 40);
            """
        ),
        responses=responses,
        token_seq=["t-A", "t-A", "t-A", "t-A"],
    )
    urls = [c["url"] for c in out["calls"]]
    assert urls.count("/api/government-revenue/dossier/company/LMT") == 2, urls
    assert urls.count("/api/government-revenue/company/LMT/awards?limit=8") == 2, urls


@needs_node
def test_mixed_generation_fail_closed() -> None:
    """Two fetches returning divergent content_ids must still raise
    ``generation_mismatch`` and leave the host on the error surface."""
    responses = {
        "/api/government-revenue/dossier/company/LMT":
            _dossier("grd1-" + "a" * 24),
        "/api/government-revenue/company/LMT/awards?limit=8":
            _prime("grd1-" + "b" * 24),
    }
    out = run(
        action_js="ui.loadCompany('LMT');",
        responses=responses,
        token_seq=["t-A", "t-A"],
    )
    assert "Award book unavailable" in out["html"], out["html"]


@needs_node
def test_invalid_schema_does_not_share_pending() -> None:
    """A 200 response with a wrong ``schema_version`` raises ``contract`` and
    does not poison a follow-up request against the same route."""
    bad = {
        "schema_version": "2.0.0",  # wrong version
        "content_id": "grd1-" + "a" * 24,
        "company": {"action_count": 1},
    }
    good = _dossier()
    responses = {
        "/api/government-revenue/dossier/company/LMT": bad,
        # The awards URL is missing entirely → 404 (None), which fails the
        # first loadCompany too. We map it to a valid response on retry.
        "/api/government-revenue/company/LMT/awards?limit=8": None,
    }
    action_js = textwrap.dedent(
        """
            ui.loadCompany('LMT');
            setTimeout(function(){
              responses['/api/government-revenue/dossier/company/LMT'] = __GOOD__;
              responses['/api/government-revenue/company/LMT/awards?limit=8'] = __PRIME__;
              ui.loadCompany('LMT');
            }, 30);
        """
    ).replace("__GOOD__", json.dumps(good)).replace("__PRIME__", json.dumps(_prime()))
    seq = ["t-A", "t-A", "t-A", "t-A", "t-A", "t-A", "t-A", "t-A"]
    script = (
        PRELUDE
        + _auth_stub(seq)
        + _fetch_stub_with_responses_var(responses)
        + "\n"
        + DOSSIER_JS
        + _host_and_factory("company:LMT")
        + action_js
        + textwrap.dedent(
            """
                setTimeout(function(){
                  process.stdout.write(JSON.stringify({
                    calls: calls,
                    html: host.innerHTML
                  }));
                }, 60);
            """
        )
    )
    result = subprocess.run(
        ["node", "-"], input=script, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    urls = [c["url"] for c in out["calls"]]
    assert urls.count("/api/government-revenue/dossier/company/LMT") == 2, urls
    assert "Official award book" in out["html"]


@needs_node
def test_invalid_content_id_does_not_share_pending() -> None:
    """A 200 response whose ``content_id`` does not match the prefix regex
    raises ``contract`` and a retry sees a fresh request."""
    bad = {
        "schema_version": "1.0.0",
        "content_id": "BOGUS-" + "a" * 24,  # wrong prefix
        "company": {"action_count": 1},
    }
    good = _dossier()
    responses = {
        "/api/government-revenue/dossier/company/LMT": bad,
        "/api/government-revenue/company/LMT/awards?limit=8": None,
    }
    action_js = textwrap.dedent(
        """
            ui.loadCompany('LMT');
            setTimeout(function(){
              responses['/api/government-revenue/dossier/company/LMT'] = __GOOD__;
              responses['/api/government-revenue/company/LMT/awards?limit=8'] = __PRIME__;
              ui.loadCompany('LMT');
            }, 30);
        """
    ).replace("__GOOD__", json.dumps(good)).replace("__PRIME__", json.dumps(_prime()))
    seq = ["t-A", "t-A", "t-A", "t-A", "t-A", "t-A", "t-A", "t-A"]
    script = (
        PRELUDE
        + _auth_stub(seq)
        + _fetch_stub_with_responses_var(responses)
        + "\n"
        + DOSSIER_JS
        + _host_and_factory("company:LMT")
        + action_js
        + textwrap.dedent(
            """
                setTimeout(function(){
                  process.stdout.write(JSON.stringify({
                    calls: calls,
                    html: host.innerHTML
                  }));
                }, 60);
            """
        )
    )
    result = subprocess.run(
        ["node", "-"], input=script, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    urls = [c["url"] for c in out["calls"]]
    assert urls.count("/api/government-revenue/dossier/company/LMT") == 2, urls
    assert "Official award book" in out["html"]


@needs_node
def test_invalidate_suppresses_old_selection_while_new_reads_coalesce() -> None:
    """Late LMT reads cannot render after invalidation; pending GD reads still coalesce."""
    responses = {
        "/api/government-revenue/dossier/company/LMT": _dossier(),
        "/api/government-revenue/company/LMT/awards?limit=8": _prime(),
        "/api/government-revenue/dossier/company/GD": _dossier(),
        "/api/government-revenue/company/GD/awards?limit=8": _prime(),
    }
    actions = textwrap.dedent(
        """
            var resolvers = {};
            window.fetch = function(url, opts){
              calls.push({url:url, authorization:opts.headers.Authorization||'', credentials:opts.credentials});
              return new Promise(function(resolve){resolvers[url]=resolve;});
            };
            function turn(){return new Promise(setImmediate);}
            function release(ticker){
              Object.keys(resolvers).filter(function(url){return url.indexOf('/'+ticker)!==-1;}).forEach(function(url){
                resolvers[url]({ok:true,json:function(){return Promise.resolve(responses[url]);}});
              });
            }
            (async function(){
              ui.loadCompany('LMT'); await turn();
              ui.invalidate(); selected='company:GD'; ui.loadCompany('GD'); await turn();
              release('LMT'); await turn();
              if(host.innerHTML.indexOf('Official award book')!==-1)throw new Error('old selection rendered');
              ui.loadCompany('GD'); await turn();
              release('GD'); await turn();
            })().catch(function(e){console.error(e);process.exitCode=1;});
        """
    )
    out = run(action_js=actions, responses=responses, token_seq=["t-A"] * 6)
    urls = [c["url"] for c in out["calls"]]
    for ticker in ["LMT", "GD"]:
        assert urls.count(f"/api/government-revenue/dossier/company/{ticker}") == 1
        assert urls.count(f"/api/government-revenue/company/{ticker}/awards?limit=8") == 1
    assert "Official award book" in out["html"]


@needs_node
def test_credentials_remain_same_origin() -> None:
    """No auth bypass: every fetch retains ``credentials:'same-origin'``."""
    responses = {
        "/api/government-revenue/dossier/company/LMT": _dossier(),
        "/api/government-revenue/company/LMT/awards?limit=8": _prime(),
    }
    out = run(
        action_js="ui.loadCompany('LMT'); ui.loadCompany('LMT');",
        responses=responses,
        token_seq=["t-A"] * 4,
    )
    for c in out["calls"]:
        assert c["credentials"] == "same-origin"


@needs_node
def test_anonymous_uses_no_authorization_header() -> None:
    """When withAuth returns no token, no Authorization header must be sent."""
    responses = {
        "/api/government-revenue/dossier/company/LMT": _dossier(),
        "/api/government-revenue/company/LMT/awards?limit=8": _prime(),
    }
    out = run(
        action_js="ui.loadCompany('LMT');",
        responses=responses,
        token_seq=[None, None],
    )
    for c in out["calls"]:
        assert c["authorization"] == ""
