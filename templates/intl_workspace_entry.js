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
    var handle;
    try {
      handle = window.IntlWorkspace.mountIntlWorkspace(root, JSON.parse(config.textContent));
      relabel();
      document.addEventListener('langchange', relabel);
      controls.disabled = false;
      if (legacy) {
        legacy.open = location.hash === '#intl-legacy-research';
        root.querySelector('a[href="#intl-legacy-research"]').addEventListener('click', function () { legacy.open = true; });
      }
    } catch (_) {
      if (handle) handle.destroy();
      document.removeEventListener('langchange', relabel);
      controls.disabled = true;
      if (legacy) legacy.open = true;
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once:true});
  else start();
}());
