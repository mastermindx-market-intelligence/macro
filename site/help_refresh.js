/* MO-PAID-057: Help-page build age only. No data freshness or nightly claim. */
(function () {
  'use strict';
  var el = document.getElementById('help-refresh');
  if (!el) return;
  function paint() {
    var raw = el.getAttribute('data-build-stamp') || '';
    var legacy = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(raw);
    var iso = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(raw);
    var parsed = legacy ? raw.replace(' ', 'T') + ':00Z' : raw;
    var stamp = legacy || iso ? Date.parse(parsed) : NaN;
    var now = Date.now();
    var age = Number.isFinite(stamp) && Number.isFinite(now) && stamp <= now ? Math.floor((now - stamp) / 3600000) : null;
    var state = age === null ? 'unknown' : age >= 36 ? 'stale' : 'fresh';
    var en, zh;
    if (age === null) {
      en = 'The build time for this Help page is unavailable. Data pages show their own update times.';
      zh = '本帮助页的构建时间不可用。数据页面会分别显示各自的更新时间。';
    } else if (state === 'stale') {
      en = 'This Help page was built ' + age + ' hours ago. Its content may be behind recent product changes.';
      zh = '本帮助页于 ' + age + ' 小时前构建，内容可能尚未反映最近的产品变化。';
    } else if (age === 0) {
      en = 'This Help page was built less than an hour ago. Data pages show their own update times.';
      zh = '本帮助页于不到一小时前构建。数据页面会分别显示各自的更新时间。';
    } else {
      en = 'This Help page was built ' + age + (age === 1 ? ' hour' : ' hours') + ' ago. Data pages show their own update times.';
      zh = '本帮助页于 ' + age + ' 小时前构建。数据页面会分别显示各自的更新时间。';
    }
    if (state === 'stale') {
      en += ' Check the product page for its latest status.';
      zh += ' 请查看产品页面了解最新状态。';
    }
    el.querySelector('.l-en').textContent = en;
    el.querySelector('.l-zh').textContent = zh;
    el.setAttribute('data-refresh-state', state);
  }
  paint();
  document.addEventListener('visibilitychange', function () { if (!document.hidden) paint(); });
  window.addEventListener('pageshow', paint);
  window.setInterval(paint, 60000);
}());
