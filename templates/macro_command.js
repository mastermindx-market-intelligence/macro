/* macro_command.js — Macro Command shell behaviour (F01 / Macro Command P1).
   No framework. No style injection: zero colour literals, zero
   `style.textContent` writes, zero created style elements (G9). The only
   style-adjacent DOM this file touches is class names and the `hidden`
   property. No section-swap animation of any kind (§6.2 item 5) — sections
   swap instantly in both themes, and there is no animation clock anywhere on
   this page.

   Hash grammar: `#<section>` or `#<section>/<subtab>` (§6.2 item 1). An
   unknown or empty section resolves to `overview`; an unknown sub-tab
   resolves to that section's first tab. */
(function () {
  'use strict';

  var shell = document.getElementById('mc-shell');
  if (!shell) return;

  var rail = document.getElementById('mc-rail');
  var content = document.getElementById('mc-content');
  var panels = Array.prototype.slice.call(content.querySelectorAll('[data-mc-panel]'));
  var railLinks = Array.prototype.slice.call(rail.querySelectorAll('[data-mc-section]'));
  var PENDING_TIMEOUT_MS = 8000;
  var fetchedSections = {};

  function panelById(id) {
    for (var i = 0; i < panels.length; i++) {
      if (panels[i].getAttribute('data-mc-panel') === id) return panels[i];
    }
    return null;
  }

  function railLinkById(id) {
    for (var i = 0; i < railLinks.length; i++) {
      if (railLinks[i].getAttribute('data-mc-section') === id) return railLinks[i];
    }
    return null;
  }

  function tabbodyOwner(id) {
    var node = document.getElementById(id);
    if (!node || !node.hasAttribute('data-mc-tabbody')) return null;
    var owner = node.closest('[data-mc-panel]');
    if (!owner) return null;
    return {
      section: owner.getAttribute('data-mc-panel'),
      subtab: node.getAttribute('data-mc-tabbody')
    };
  }

  /* ── hash grammar (two segments) — §6.2 item 1 ─────────────────────────── */
  function parseHash() {
    var raw = (location.hash || '').replace(/^#/, '');
    var parts = raw.split('/');
    var sectionId = parts[0] || '';
    var subtabId = parts[1] || '';
    if (!panelById(sectionId)) {
      var owned = tabbodyOwner(sectionId);
      if (owned) return owned;
      sectionId = 'overview';
    }
    return { section: sectionId, subtab: subtabId };
  }

  /* ── section activation — §6.2 item 2 ──────────────────────────────────── */
  function activateSection(id, subtabId, focus) {
    var target = panelById(id) || panelById('overview');
    if (!target) return;
    var resolvedId = target.getAttribute('data-mc-panel');

    panels.forEach(function (panel) {
      var isTarget = panel === target;
      panel.hidden = !isTarget;
    });
    railLinks.forEach(function (link) {
      var isCurrent = link.getAttribute('data-mc-section') === resolvedId;
      if (isCurrent) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
      link.classList.toggle('is-current', isCurrent);
    });

    activateSubtab(target, subtabId);
    maybeFetchFragment(target, resolvedId);

    var hash = '#' + resolvedId + (subtabId ? '/' + subtabId : '');
    if (location.hash !== hash) history.replaceState(null, '', hash);
    if (focus !== false) (target.querySelector('.mc-panel-title') || target).focus();
  }

  /* ── sub-tabs: real role="tablist", roving tabindex — §6.2 item 4 ─────── */
  function activateSubtab(panel, requestedId) {
    var tabs = Array.prototype.slice.call(panel.querySelectorAll('[data-mc-subtab]'));
    if (!tabs.length) return;
    var match = null;
    for (var i = 0; i < tabs.length; i++) {
      if (tabs[i].getAttribute('data-mc-subtab') === requestedId) { match = tabs[i]; break; }
    }
    if (!match) match = tabs[0];
    tabs.forEach(function (tab) {
      var selected = tab === match;
      tab.setAttribute('aria-selected', selected ? 'true' : 'false');
      tab.setAttribute('tabindex', selected ? '0' : '-1');
    });
    var selectedId = match.getAttribute('data-mc-subtab');
    var bodies = Array.prototype.slice.call(panel.querySelectorAll('[data-mc-tabbody]'));
    bodies.forEach(function (body) {
      body.hidden = body.getAttribute('data-mc-tabbody') !== selectedId;
    });
  }

  function wireSubtabKeyboard(panel) {
    var tabs = Array.prototype.slice.call(panel.querySelectorAll('[data-mc-subtab]'));
    if (!tabs.length) return;
    tabs.forEach(function (tab, index) {
      tab.addEventListener('click', function () {
        activateSubtab(panel, tab.getAttribute('data-mc-subtab'));
        var sectionId = panel.getAttribute('data-mc-panel');
        history.replaceState(null, '', '#' + sectionId + '/' + tab.getAttribute('data-mc-subtab'));
      });
      tab.addEventListener('keydown', function (ev) {
        var delta = 0;
        if (ev.key === 'ArrowRight') delta = 1;
        else if (ev.key === 'ArrowLeft') delta = -1;
        else if (ev.key === 'Home') delta = -index;
        else if (ev.key === 'End') delta = tabs.length - 1 - index;
        else return;
        ev.preventDefault();
        var next = tabs[(index + delta + tabs.length) % tabs.length];
        next.focus();
        next.click();
      });
    });
  }

  /* ── fragment fetch on first activation — §6.2 item 3 ──────────────────── */
  function maybeFetchFragment(panel, sectionId) {
    /* P1 ships no fragments. The builder only sets data-mc-fragments when
       fragment files exist; without that flag this function is a no-op so
       P1 never issues a guaranteed-404 and never unhides the pending line
       (Opus review, pull request 6930, M3). */
    if (!shell.hasAttribute('data-mc-fragments')) return;
    if (sectionId === 'overview' || fetchedSections[sectionId]) return;
    fetchedSections[sectionId] = true;
    var figure = panel.querySelector('[data-mc-figure]');
    if (!figure) return;
    var pending = figure.querySelector('[data-mc-pending]');
    var offers = Array.prototype.slice.call(figure.querySelectorAll('[data-mc-offer]'));
    if (pending) pending.hidden = false;
    offers.forEach(function (offer) { offer.hidden = true; });

    var settled = false;
    var timer = setTimeout(function () { fail(); }, PENDING_TIMEOUT_MS);

    function restoreOffer() {
      if (pending) pending.hidden = true;
      offers.forEach(function (offer) { offer.hidden = false; });
    }

    function fail() {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      var tpl = panel.querySelector('template[data-mc-empty-e5]');
      if (tpl) {
        figure.innerHTML = '';
        figure.appendChild(tpl.content.cloneNode(true));
        return;
      }
      restoreOffer();
    }

    if (typeof fetch !== 'function') { fail(); return; }
    fetch('macro/fragments/' + sectionId + '.html')
      .then(function (resp) {
        if (settled) return;
        if (!resp.ok) { fail(); return; }
        var ctype = (resp.headers.get('content-type') || '').toLowerCase();
        if (ctype.indexOf('text/html') === -1) { fail(); return; }
        return resp.text().then(function (text) {
          if (settled) return;
          if (text.indexOf('data-mc-fragment') === -1) { fail(); return; }
          settled = true;
          clearTimeout(timer);
          figure.innerHTML = text;
          /* The assignment above destroys the [data-mc-tabbody] wrappers this
             panel's roving tab state lives on, so re-apply the selection that
             was resolved from the hash before the fetch started (P3, A13). */
          var selected = panel.querySelector('[data-mc-subtab][aria-selected="true"]');
          if (selected) activateSubtab(panel, selected.getAttribute('data-mc-subtab'));
        });
      })
      .catch(function () { fail(); });
  }

  /* ── rail click/keyboard ────────────────────────────────────────────────── */
  railLinks.forEach(function (link) {
    link.addEventListener('click', function (ev) {
      ev.preventDefault();
      var id = link.getAttribute('data-mc-section');
      activateSection(id, '');
    });
  });

  window.addEventListener('hashchange', function () {
    /* A hash that names a real non-panel id (e.g. the skip link's
       `#mc-content`) is a native anchor jump, not section routing --
       let the browser's own scroll-and-focus stand instead of
       coercing it to `overview` and stealing focus back (Meta-CEO
       review, PR 6930 MAJOR skip-link hijack). */
    var raw = (location.hash || '').replace(/^#/, '');
    var sectionId = raw.split('/')[0];
    if (raw && !panelById(sectionId)) {
      var owned = tabbodyOwner(sectionId);
      if (owned) {
        activateSection(owned.section, owned.subtab);
        return;
      }
      if (document.getElementById(raw)) return;
    }
    var parsed = parseHash();
    activateSection(parsed.section, parsed.subtab);
  });

  panels.forEach(wireSubtabKeyboard);

  /* ── analyst control — §8: existing sitewide open entry point only ───────
     templates/mm_brain.js:3815 explain(key, title) is the callable that
     accepts opening context. open() (line 3102) takes no context. No
     query-topic, ampersand-section, or slash-api literal is introduced. */
  var analystBtn = document.querySelector('[data-mc-analyst]');
  if (analystBtn) {
    analystBtn.addEventListener('click', function () {
      var lang = (document.documentElement.getAttribute('data-lang') || 'en') === 'zh' ? 'zh' : 'en';
      var sectionId = 'overview';
      var current = content.querySelector('[data-mc-panel]:not([hidden])');
      if (current) sectionId = current.getAttribute('data-mc-panel') || 'overview';
      var label;
      if (sectionId === 'overview') {
        label = lang === 'zh'
          ? (analystBtn.getAttribute('data-mc-analyst-label-zh') || '宏观指挥台')
          : (analystBtn.getAttribute('data-mc-analyst-label-en') || 'Macro Command');
      } else {
        var railLink = railLinkById(sectionId);
        var span = railLink && railLink.querySelector(lang === 'zh' ? '.l-zh' : '.l-en');
        label = (span && span.textContent.trim())
          || (railLink && railLink.textContent.trim())
          || (lang === 'zh' ? '宏观指挥台' : 'Macro Command');
      }
      if (window.MMBrain && typeof window.MMBrain.explain === 'function') {
        window.MMBrain.explain(sectionId, label);
        return;
      }
      if (window.MMBrain && typeof window.MMBrain.open === 'function') {
        window.MMBrain.open();
        return;
      }
      /* Degraded: the builder already emitted <a href="chat.html"> when the
         widget is not mountable. If this button is present but the widget
         has not booted, click the sitewide launcher stub. */
      var boot = document.getElementById('mmb-boot');
      if (boot) boot.click();
    });
  }

  /* ── boot ───────────────────────────────────────────────────────────────── */
  var initial = parseHash();
  /* focus:false -- boot must not draw a focus ring around the initial
     panel with no user interaction (Meta-CEO review, PR 6930 BLOCKER
     boot-focus ring). Rail clicks and hashchange still focus (default). */
  activateSection(initial.section, initial.subtab, false);
  /* Deep-link arrival line (P3, D12). Server-rendered per panel and `hidden`
     in the document, so bilingual copy is never generated here (G6) and a
     no-JS reader never sees it. Shown once, on a hash arrival only. */
  if ((location.hash || '').length > 1) {
    var arrivalPanel = document.querySelector(
      '[data-mc-panel="' + (location.hash.slice(1).split('/')[0]) + '"]');
    var arrival = arrivalPanel && arrivalPanel.querySelector('[data-mc-arrival]');
    if (arrival) arrival.hidden = false;
  }
  document.querySelectorAll('[data-mc-section]').forEach(function (link) {
    link.addEventListener('click', function () {
      var open = document.querySelector('[data-mc-arrival]:not([hidden])');
      if (open) open.hidden = true;
    });
  });
})();
