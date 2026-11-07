"""Render the source-bound Prophet Save fixture for the save-visual receipt.

The fixture is deliberately narrow: it proves the Save dialog's presentation and
interaction states, not the whole board page.

What is REAL here (byte-for-byte, hashed in ``save-inputs.json``):

* ``templates/prophet_save.css`` and ``templates/prophet_save.js`` -- copied
  verbatim from the template sources, so the captured presentation is the
  candidate's own Save contract.
* The rendered ``<head>`` of the real dashboard, including the real built
  ``theme.css`` / ``assets/css/*`` the light/dark axis depends on.
* The real ``#us-standouts`` / ``#us-today`` / ``#us-today-grid`` wrappers and
  the real Today card markup, extracted from the real dashboard render.
* The real ``site/watchstore.js`` -- the anonymous store the page itself ships.

What is FIXTURE (stated here, in ``save-inputs.json`` and in the receipt README):

* The account store. A signed-in session cannot be produced offline without
  inventing credentials, so the session-requiring states install a local stub
  that implements the same ``WatchStore`` surface the real one exposes
  (``checkedSession`` / ``lists.refresh`` / ``symbols.saveChecked`` /
  ``symbols.inspect``). The stub answers from a constant. It contacts no
  account, writes no list, and proves nothing about a real account.
* The reduced page. Everything outside the Save surface (the 212-row stock
  table, the other panes, the footer) is dropped so the dialog is legible in a
  full-page capture.

The one state that needs no stub at all is ``signed_out``: the real
``site/watchstore.js`` reports ``signed_out`` for an anonymous page, and that is
what the candidate actually does for a visitor.

Run from the repository root::

    python3 mockups/evidence/prophet-opportunity-workspace/save-visual-20261104-fabric/render_save_fixture.py \\
        site/_tmp/prophet-save-visual-20261104-fabric > \\
        mockups/evidence/prophet-opportunity-workspace/save-visual-20261104-fabric/save-inputs.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))

import render_public_fixture as public  # noqa: E402

# The single card the capture exercises: the first Today card the real board
# renders. Its ticker, setup body and footer are the real ones.
CARD_SELECTOR = "#us-today-grid .pvcard"

# A synthetic account list. It is not a real list and holds no real account.
FIXTURE_LIST = {"id": "fixture-list-1", "name": "Fixture List"}

# The real Save dialog's own state vocabulary (templates/prophet_save.js sets
# `data-save-state`). Every state below is one the candidate's own script
# renders; the fixture only decides which account answers the read.
STATES: list[dict[str, object]] = [
    {
        "name": "signed_out",
        "real_store": True,
        "session": "signed_out",
        "lists": [],
        "save": None,
        "expect": "signed-out",
        "note": "no stub: the real site/watchstore.js answers signed_out for an anonymous page",
    },
    {
        "name": "unavailable",
        "real_store": False,
        "session": "unavailable",
        "lists": [],
        "save": None,
        "expect": "unavailable",
        "note": "fixture account store reports the account host unavailable",
    },
    {
        "name": "empty_lists",
        "real_store": False,
        "session": "ready",
        "lists": [],
        "save": None,
        "expect": "empty",
        "note": "fixture account store answers with no lists; the dialog offers the Watchlists return control",
    },
    {
        "name": "choose",
        "real_store": False,
        "session": "ready",
        "lists": [FIXTURE_LIST],
        "save": None,
        "expect": "choose",
        "note": "fixture account store answers with one list; the dialog shows the list picker",
    },
    {
        "name": "saved",
        "real_store": False,
        "session": "ready",
        "lists": [FIXTURE_LIST],
        "save": {"state": "saved", "readBackAt": "2026-11-04T07:30:00Z"},
        "expect": "saved",
        "save_state": "saved",
        "note": "fixture account store confirms the save and answers the read-back",
    },
    {
        "name": "rejected",
        "real_store": False,
        "session": "ready",
        "lists": [FIXTURE_LIST],
        "save": {"state": "rejected", "reason": "fixture rejection"},
        "expect": "rejected",
        "save_state": "rejected",
        "note": "fixture account store refuses the save",
    },
    {
        "name": "uncertain",
        "real_store": False,
        "session": "ready",
        "lists": [FIXTURE_LIST],
        "save": {"state": "uncertain", "askedAt": "2026-11-04T07:30:00Z"},
        "expect": "uncertain",
        "save_state": "uncertain",
        "note": "fixture account store neither confirms nor refuses; the dialog holds the no-retry state",
    },
    {
        "name": "observed",
        "real_store": False,
        "session": "ready",
        "lists": [FIXTURE_LIST],
        "save": {"state": "uncertain", "askedAt": "2026-11-04T07:30:00Z"},
        "inspect": {"state": "present", "membership": "member", "observedAt": "2026-11-04T07:31:00Z"},
        "expect": "observed",
        "save_state": "uncertain",
        "note": "fixture account store answers the membership read without a second save",
    },
]

# The fixture driver. Every activation is a synthetic, untrusted DOM click, so
# the page never records a real pointer or key event: the candidate's own
# `dialog.querySelector('button').focus()` then leaves the Close control
# :focus-visible, and the capture tool's focus force-state lands on a control
# that actually shows the focus ring.
DRIVER = r"""
(function () {
  'use strict';
  var CFG = window.__SAVE_FIXTURE__ || {};
  function log(m) { (window.__saveFixtureLog = window.__saveFixtureLog || []).push(String(m)); }
  function visible(el) { return !!(el && (el.offsetParent || el.getClientRects().length)); }
  function dlg() { return document.getElementById('prophet-save-dialog'); }
  function dlgState() { var d = dlg(); return d ? d.getAttribute('data-save-state') : null; }
  function waitFor(fn, ms) {
    var t0 = Date.now();
    return new Promise(function (resolve) {
      (function tick() {
        var v = null;
        try { v = fn(); } catch (e) { v = null; }
        if (v) return resolve(v);
        if (Date.now() - t0 > (ms || 8000)) return resolve(null);
        setTimeout(tick, 20);
      })();
    });
  }
  function contentButton() {
    var d = dlg();
    return d ? d.querySelector('.prophet-save-content button') : null;
  }
  function installStore(cfg) {
    var lists = (cfg.lists || []).map(function (l) { return { id: l.id, name: l.name }; });
    var outcome = cfg.save ? JSON.parse(JSON.stringify(cfg.save)) : null;
    var inspect = cfg.inspect ? JSON.parse(JSON.stringify(cfg.inspect)) : null;
    window.WatchStore = {
      checkedSession: function () {
        return { state: cfg.session, userId: cfg.session === 'ready' ? 'fixture-user' : null, generation: 1 };
      },
      status: function () { return {}; },
      pull: function () { return Promise.resolve(null); },
      user: function () { return { id: cfg.session === 'ready' ? 'fixture-user' : null }; },
      portfolioOk: function () { return false; },
      lists: {
        readOnly: false,
        refresh: function () { return Promise.resolve(lists.map(function (l) { return { id: l.id, name: l.name }; })); },
        all: function () { return lists; },
        cached: function () { return null; },
        create: function () { return Promise.resolve(null); },
        rename: function () { return Promise.resolve(null); },
        remove: function () { return Promise.resolve(null); },
        setActive: function () { return null; },
        foldTargetId: function () { return null; },
        foldTargetName: function () { return null; },
        cacheKey: function () { return 'save-visual-fixture'; },
        activeId: function () { return lists.length ? lists[0].id : null; }
      },
      symbols: {
        list: function () { return Promise.resolve([]); },
        inspect: function () { return Promise.resolve(inspect || { state: 'not-confirmed', membership: 'unknown' }); },
        add: function () { return Promise.resolve(null); },
        remove: function () { return Promise.resolve(null); },
        push: function () { return Promise.resolve(null); },
        saveChecked: function (listId, tickers, opts) {
          if (!outcome) return Promise.resolve({ state: 'uncertain', names: tickers });
          var r = JSON.parse(JSON.stringify(outcome));
          r.names = r.state === 'saved' ? [].concat(tickers) : (r.names || []);
          r.listName = (lists.filter(function (l) { return l.id === listId; })[0] || {}).name || null;
          return Promise.resolve(r);
        }
      }
    };
  }
  function run(cfg) {
    return waitFor(function () {
      var picks = Array.from(document.querySelectorAll('.pvs-save-pick'));
      return picks.filter(visible)[0] || null;
    }, 15000).then(function (pick) {
      if (!pick) { log('no visible Save control'); return null; }
      if (!cfg.real_store) installStore(cfg);
      pick.click();
      return waitFor(function () { var d = dlg(); return d && d.open ? d : null; }, 10000);
    }).then(function (d) {
      if (!d) { log('dialog did not open'); return null; }
      if (!cfg.save) return d;
      return waitFor(function () { return dlgState() === 'choose' ? true : null; }, 10000).then(function () {
        var btn = contentButton();
        if (!btn) { log('no Save control in dialog'); return d; }
        btn.click();
        return waitFor(function () { return dlgState() === cfg.save_state ? true : null; }, 10000);
      }).then(function () {
        if (!cfg.inspect) return d;
        return waitFor(function () { return dlgState() === 'uncertain' ? true : null; }, 10000).then(function () {
          var btn = contentButton();
          if (!btn) { log('no membership-read control'); return d; }
          btn.click();
          return waitFor(function () { return dlgState() === cfg.expect ? true : null; }, 10000);
        });
      });
    });
  }
  function start() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () { run(CFG); });
    } else { run(CFG); }
  }
  start();
})();
"""


def _sha256(path: Path) -> str:
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def _attrs(tag: dict[str, object]) -> str:
    out = []
    for key, value in tag.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            value = " ".join(str(v) for v in value)
        out.append(f'{key}="{str(value).replace(chr(34), "&quot;")}"')
    return " ".join(out)


def _page_css(html: str) -> str:
    """The real page's own <style> blocks, in document order.

    The board renders its card and grid CSS in body-level <style> blocks, not in
    a stylesheet: dropping them would capture an unstyled card and would prove
    nothing about the candidate's presentation. They are replayed verbatim, and
    the Save stylesheet keeps its real position relative to them so the cascade
    the candidate ships is the cascade the capture sees.
    """
    blocks = [(m.start(), m.group(0)) for m in re.finditer(r"<style[^>]*>.*?</style>", html, re.S)]
    save_at = html.find("prophet_save.css")
    before = [b for pos, b in blocks if pos < save_at]
    after = [b for pos, b in blocks if pos > save_at]
    return "\n".join(before + after)


def _visible(el) -> bool:
    return bool(el.get("data-ticker")) and el.select_one(".pv-setup-inline") is not None


def _extract(soup: BeautifulSoup) -> dict[str, object]:
    standouts = soup.select_one("#us-standouts")
    today = soup.select_one("#us-today")
    grid = soup.select_one("#us-today-grid")
    if standouts is None or today is None or grid is None:
        raise SystemExit("fixture render: the real board has no #us-standouts/#us-today/#us-today-grid")
    section = today.parent  # div.nb-grid-section in the real page
    shell = standouts.parent  # div.grid in the real page
    cards = [c for c in grid.select(".pvcard") if _visible(c)]
    if not cards:
        raise SystemExit("fixture render: no Today card carries a setup body")
    card = cards[0]
    ticker = card.get("data-ticker")
    setup = card.select_one(".pv-setup-inline")
    ticker = setup.get("data-setup-ticker") or ticker
    return {
        "standouts": dict(standouts.attrs),
        "today": dict(today.attrs),
        "grid": dict(grid.attrs),
        "section": dict(section.attrs),
        "section_name": section.name,
        "shell": dict(shell.attrs),
        "shell_name": shell.name,
        "today_head": str(today.select_one(".mx-sec-hd")) if today.select_one(".mx-sec-hd") else "",
        "card": str(card),
        "ticker": ticker,
        "card_id": card.get("id"),
    }


def _page(html_attrs: dict[str, object], head_inner: str, body_attrs: dict[str, object],
          parts: dict[str, object], cfg: dict[str, object],
          page_css: str) -> str:
    cfg_json = json.dumps(cfg, sort_keys=True)
    return f"""<!DOCTYPE html>
<html {_attrs(html_attrs)}>
<head>
{head_inner}
{page_css}
<link rel="stylesheet" href="prophet_save.css">
</head>
<body {_attrs(body_attrs)}>
<div data-watchstore-checked-save hidden></div>
<main class="wrap">
<{parts['shell_name']} {_attrs(parts['shell'])}>
<div {_attrs(parts['standouts'])}>
<{parts['section_name']} {_attrs(parts['section'])}>
<section {_attrs(parts['today'])}>
{parts['today_head']}
<div {_attrs(parts['grid'])}>
{parts['card']}
</div>
</section>
</{parts['section_name']}>
</div>
</{parts['shell_name']}>
</main>
<script src="theme.js"></script>
<script src="watchstore.js"></script>
<script src="prophet_save.js"></script>
<script>window.__SAVE_FIXTURE__ = {cfg_json};</script>
<script>{DRIVER}</script>
</body>
</html>
"""


def render(out: Path) -> dict[str, object]:
    """Render the real dashboard once, then emit one focused page per Save state."""
    out.mkdir(parents=True, exist_ok=True)
    # The public renderer leaves the real built assets, the real theme.js and the
    # real watchstore.js in the fixture root, next to the page they belong to.
    public.render(out / "public")
    for name in os.listdir(out / "public"):
        shutil.move(str(out / "public" / name), str(out / name))
    (out / "public").rmdir()

    html_path = out / "us_stocks.html"
    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    parts = _extract(soup)

    head_inner = "".join(str(c) for c in soup.head.contents)
    page_css = _page_css(html)
    html_attrs = dict(soup.html.attrs)
    body_attrs = dict(soup.body.attrs)

    # The Save stylesheet and script are copied from the TEMPLATE sources, not
    # from the built site, so the capture is bound to the changed template path
    # this receipt owns. The built site copies are byte-identical; the hashes
    # of both are recorded below.
    for name in ("prophet_save.css", "prophet_save.js"):
        shutil.copyfile(ROOT / "templates" / name, out / name)

    pages = []
    for spec in STATES:
        cfg = {
            "session": spec["session"],
            "lists": spec["lists"],
            "real_store": spec["real_store"],
            "expect": spec["expect"],
            "ticker": parts["ticker"],
        }
        if spec["save"] is not None:
            cfg["save"] = spec["save"]
        if spec.get("save_state"):
            cfg["save_state"] = spec["save_state"]
        if spec.get("inspect") is not None:
            cfg["inspect"] = spec["inspect"]
        name = f"save_{spec['name']}.html"
        page = _page(html_attrs, head_inner, body_attrs, parts, cfg, page_css)
        (out / name).write_text(page, encoding="utf-8")
        pages.append({
            "file": name,
            "route": f"/{name}",
            "state": spec["expect"],
            "account_store": "real site/watchstore.js (anonymous)" if spec["real_store"] else "fixture stub",
            "note": spec["note"],
        })

    # The public render is the source of every extracted byte; it is not itself
    # part of this capture, so the page does not stay in the fixture root.
    (out / "us_stocks.html").unlink()

    return {
        "fixture": "Prophet Save surface, reduced from the real dashboard render",
        "board_as_of": parts["standouts"].get("data-board-asof"),
        "ticker": parts["ticker"],
        "card_id": parts["card_id"],
        "pages": pages,
        "source_sha256": {
            "templates/prophet_save.css": _sha256(ROOT / "templates" / "prophet_save.css"),
            "templates/prophet_save.js": _sha256(ROOT / "templates" / "prophet_save.js"),
            "site/prophet_save.css": _sha256(ROOT / "site" / "prophet_save.css"),
            "site/prophet_save.js": _sha256(ROOT / "site" / "prophet_save.js"),
            "site/watchstore.js": _sha256(ROOT / "site" / "watchstore.js"),
            "site/theme.js": _sha256(ROOT / "site" / "theme.js"),
            "site/factordata/us_standouts.json": _sha256(ROOT / "site" / "factordata" / "us_standouts.json"),
            "site/basketdata/action_board.json": _sha256(ROOT / "site" / "basketdata" / "action_board.json"),
            "site/prophet/index.json": _sha256(ROOT / "site" / "prophet" / "index.json"),
        },
        "driver_sha256": hashlib.sha256(DRIVER.encode("utf-8")).hexdigest(),
        "page_sha256": {
            p["file"]: hashlib.sha256((out / p["file"]).read_bytes()).hexdigest() for p in pages
        },
        "not_proven": [
            "no signed-in account was contacted, no list was written and no membership was read "
            "from a real account: every session-requiring state answers from the fixture store",
            "no served production or signed-in acceptance is claimed from this fixture",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(render(args.output), indent=2))
