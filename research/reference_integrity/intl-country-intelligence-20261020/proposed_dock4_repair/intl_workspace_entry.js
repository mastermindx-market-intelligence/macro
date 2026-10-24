(function () {
  'use strict';

  function start() {
    var root = document.querySelector('[data-im-workspace][data-im-mode="macro"]');
    if (!root || root.hasAttribute('data-im-enhanced')) return;
    var config = root.querySelector('[data-im-config]');
    var controls = root.querySelector('[data-im-controls]');
    var legacy = document.getElementById('intl-legacy-research');
    if (!config || !controls || !window.IntlWorkspace) return;

    function relabel() {
      var zh = document.documentElement.lang.toLowerCase().indexOf('zh') === 0;
      root.querySelectorAll('option[data-im-label-en]').forEach(function (option) {
        option.textContent = option.getAttribute(zh ? 'data-im-label-zh' : 'data-im-label-en');
      });
    }

    function decodeHashValue(rawValue) {
      try {
        return decodeURIComponent(rawValue);
      } catch (_) {
        return '';
      }
    }

    function findLegacyTarget(rawValue) {
      var targetId = decodeHashValue(rawValue);
      var target = targetId && document.getElementById(targetId);
      return legacy && target && legacy.contains(target) ? target : null;
    }

    function revealTarget(target) {
      if (!target) return;
      for (var element = target; element && element !== root; element = element.parentElement) {
        if (element.tagName === 'DETAILS') element.open = true;
      }
    }

    function handleHashChange() {
      revealTarget(findLegacyTarget(location.hash.slice(1)));
    }

    function handleAnchorActivation(event) {
      if (!event.target.closest) return;
      var anchor = event.target.closest('a');
      if (!anchor || anchor.getAttribute('href') === null) return;

      var url;
      try {
        url = new URL(anchor.getAttribute('href'), location.href);
      } catch (_) {
        return;
      }
      if (url.origin !== location.origin || url.pathname !== location.pathname || url.search !== location.search) return;
      revealTarget(findLegacyTarget(url.hash.slice(1)));
    }

    var handle;
    var languageListenerAdded = false;
    var navigationListenersAdded = false;

    try {
      handle = window.IntlWorkspace.mountIntlWorkspace(root, JSON.parse(config.textContent));
      relabel();
      document.addEventListener('langchange', relabel);
      languageListenerAdded = true;
      controls.disabled = false;
      if (legacy) {
        var target = findLegacyTarget(location.hash.slice(1));
        if (target) revealTarget(target);
        else legacy.open = false;
      }
      window.addEventListener('hashchange', handleHashChange);
      document.addEventListener('click', handleAnchorActivation);
      navigationListenersAdded = true;
    } catch (_) {
      if (handle) handle.destroy();
      if (languageListenerAdded) document.removeEventListener('langchange', relabel);
      if (navigationListenersAdded) {
        window.removeEventListener('hashchange', handleHashChange);
        document.removeEventListener('click', handleAnchorActivation);
      }
      controls.disabled = true;
      if (legacy) legacy.open = true;
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
}());
