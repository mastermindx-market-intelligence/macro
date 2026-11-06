#!/usr/bin/env python3
"""Generate a research candidate from hash-bound native source, no repo edits."""
import difflib
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
original = (HERE / "pinned_cn_prophet_live.js").read_text()
assert hashlib.sha256(original.encode()).hexdigest() == "e4bfdad0781eda00f8c940047e637a6f4ac691b057b703f9eba25d9930665147"
candidate = original


def replace(old, new):
    global candidate
    assert candidate.count(old) == 1, old[:100]
    candidate = candidate.replace(old, new)


replace("artifact older than 45 minutes", "artifact at least 15 minutes old")
replace("  var _fetching = false;", """  var _fetching = false;
  var _request = 0;
  var _expiryTimer = 0;
  var _expiresAt = 0;
  var FUTURE = 60000; /* research choice: allowed device/source clock skew */""")
replace("    if (ageMs(d) > MAXAGE) return true;", """    var age = ageMs(d);
    if (!isFinite(age) || age < -FUTURE || age >= MAXAGE) return true;""")
replace("  function tearDown() {\n    if (!_painted) return;", """  function tearDown() {
    if (_expiryTimer) clearTimeout(_expiryTimer);
    _expiryTimer = 0;
    _expiresAt = 0;
    if (!_painted) return;""")
replace("  function apply(d) {\n    paintCards(d.names || {});\n  }", """  function expire() {
    if (_expiresAt && Date.now() >= _expiresAt) tearDown();
  }

  function apply(d) {
    paintCards(d.names || {});
    if (_expiryTimer) clearTimeout(_expiryTimer);
    _expiresAt = Date.now() - ageMs(d) + MAXAGE;
    _expiryTimer = setTimeout(expire, Math.max(0, _expiresAt - Date.now()));
  }""")
start = candidate.index("  function tick(force) {")
end = candidate.index("\n  function arm() {", start)
candidate = candidate[:start] + """  function tick(force) {
    expire();
    if (document.visibilityState === "hidden" && !force) return;
    var now = Date.now();
    if (!force && _fetching) return;
    if (!force && _lastFetch && (now - _lastFetch) < FLOOR) return;
    _fetching = true;
    _lastFetch = now;
    var request = ++_request;
    var controller = typeof AbortController !== "undefined" ? new AbortController() : null;
    var deadline = setTimeout(function () {
      if (controller) controller.abort(); /* also bound obsolete requests */
      if (request !== _request) return;
      ++_request; /* any late response is obsolete */
      _fetching = false;
      tearDown();
    }, FLOOR); /* bounded request lifetime; poll cadence remains unchanged */
    var options = { cache: "no-store" };
    if (controller) options.signal = controller.signal;
    fetch(URL + "?t=" + now, options)
      .then(function (r) {
        if (request !== _request) return null;
        if (!r.ok) { tearDown(); return null; }
        return r.json().then(function (d) { return { d: d, status: r.status }; });
      })
      .then(function (pack) {
        if (request !== _request) return;
        if (!pack) { tearDown(); return; }
        if (refuse(pack.d, pack.status)) { tearDown(); return; }
        try { apply(pack.d); } catch (e) { tearDown(); }
      })
      .catch(function () { if (request === _request) tearDown(); })
      .then(function () {
        clearTimeout(deadline);
        if (request === _request) _fetching = false;
      });
  }
""" + candidate[end:]
(HERE / "candidate_cn_prophet_live.js").write_text(candidate)
(HERE / "candidate.diff").write_text("".join(difflib.unified_diff(original.splitlines(True), candidate.splitlines(True), fromfile="pinned/templates/cn_prophet_live.js", tofile="research/candidate_cn_prophet_live.js")))
print(hashlib.sha256(candidate.encode()).hexdigest())
