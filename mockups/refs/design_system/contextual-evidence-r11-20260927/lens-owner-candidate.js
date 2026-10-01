/* ---- LENS — the site-wide explainer popover ([data-tip-en]/[data-tip-zh] + rich tier)
   The overhauled container for every explainer on the site (design mockups/lens,
   merged #3102; operator order 2026-07-19 — concise plain words, illustrated,
   beautifully formatted). One body-appended glass card, two content tiers:
     · string tier — existing data-tip-en / data-tip-zh attributes render in the new
       card unchanged. An OPTIONAL data-tip-rc-en / data-tip-rc-zh pair renders as a
       mono "receipt" line under a dashed perforation — the sanctioned Tier-2 home
       for n= / windows / sources / study IDs, which are BANNED from the body.
     · rich tier — a trigger (.lens-q "?" button or .lens-term dotted span) plus a
       hidden .lens-src block (direct child or next sibling) carrying the
       illustrated anatomy: .lens-hd (.lens-ill disc + .lens-kick kicker +
       .lens-title) → .lens-body → .lens-receipt, with a data-lens-kind accent
       (define | read | record | source | caution).
   i18n rule unchanged: translated text NEVER goes in title= attributes — dual-span
   l-en/l-zh bodies follow the [data-lang] CSS live.
   Desktop: hover-intent (90ms open / 180ms close grace), the card itself is
   hoverable, and it FOLLOWS its trigger on scroll (hiding once the trigger leaves
   the viewport). Touch: tap-to-toggle (nested controls still win the tap — the old
   singleton's contract). ≤640px the card becomes a bottom sheet — scrim, drag
   handle, swipe-down dismiss, safe-area padded, pinned left/right:0 so it CANNOT
   bleed off-screen. Esc closes; focus opens; aria-describedby wired.
   The component CSS is INJECTED here rather than living in theme.css so vector-
   family pages (own token names, no theme.css) style it correctly through the
   --lens-* fallback chains — the settings-popover pattern. */
(function () {
  var OPEN_MS = 90, CLOSE_MS = 180;
  // NOTE: bare `data-lens` is NOT a trigger — the AI-Brief tab system already uses
  // data-lens="macro|china|btc" for its tabs + body wrapper, and a capture-phase
  // match here would swallow those taps on touch. Rich-tier triggers opt in via the
  // .lens-q / .lens-term classes only.
  var SEL = '[data-tip-en], .lens-q, .lens-term';
  // A focusable control NESTED INSIDE a tip container owns its own taps. The click
  // handler has always honoured that; `nestedCtrl` is that same test, hoisted so the
  // focusin handler below cannot drift from it.
  var CTRL_SEL = 'button, a, input, select, textarea, label, [role="button"]';
  function nestedCtrl(target, t) {
    var ctrl = target && target.closest && target.closest(CTRL_SEL);
    return !!(ctrl && ctrl !== t && t.contains(ctrl));
  }
  var pop = null, scrim = null, cur = null, openTimer = 0, closeTimer = 0, scrollRaf = 0;
  // A tap on a focusable trigger FOCUSES it first: focusin -> show(t) mounts the
  // sheet + scrim mid-gesture, the browser retargets the tap's own trailing click
  // to <body> (down-target and up-target no longer share a hit path), and a naive
  // "click outside closes" read hides the tip inside the very tap that opened it —
  // open-then-vanish on every bare [data-tip-en] chip in sheet mode, toggle-close
  // on non-sheet touch. On touch the focusin lands AFTER pointerup (compat mouse
  // events follow the pointer sequence), so "is a pointer down" cannot gate this;
  // instead gestureSeq counts pointerdown gestures, focusin stamps the gesture it
  // opened under, and a click still carrying that same gesture is the tap's own
  // artifact, never a dismissal. A real dismissal tap always brings a NEW
  // pointerdown (seq mismatch), and keyboard activation clicks carry detail === 0
  // (no pointer gesture), so Enter on a <button> trigger still toggles as before.
  var gestureSeq = 0, focusShowSeq = -1, focusShowEl = null;
  function gestureOpenedTip(e) {
    return e.detail !== 0 && focusShowSeq === gestureSeq &&
           cur && cur === focusShowEl && isOpen();
  }

  var CSS =
    '.lens-src{display:none}' +
    '.lens-q{display:inline-flex;align-items:center;justify-content:center;width:17px;height:17px;border-radius:50%;' +
      'margin:0 2px;padding:0;vertical-align:middle;flex:none;font:600 10.5px/1 var(--font-ui,Inter,sans-serif);' +
      'color:var(--muted,var(--mut,#8b93a1));background:color-mix(in srgb,var(--muted,var(--mut,#8b93a1)) 9%,transparent);' +
      'border:1px solid color-mix(in srgb,var(--muted,var(--mut,#8b93a1)) 42%,transparent);cursor:help;user-select:none;' +
      '-webkit-tap-highlight-color:transparent;transition:color .18s,border-color .18s,background .18s,box-shadow .22s,transform .22s cubic-bezier(.34,1.26,.4,1)}' +
    '.lens-q:hover,.lens-q.lens-on,.lens-q:focus-visible{color:var(--ink-info, var(--info,var(--blue,#5b9bf0)));' +
      'border-color:color-mix(in srgb,var(--info,var(--blue,#5b9bf0)) 55%,transparent);' +
      'background:color-mix(in srgb,var(--info,var(--blue,#5b9bf0)) 13%,transparent);' +
      'box-shadow:0 0 0 3px color-mix(in srgb,var(--info,var(--blue,#5b9bf0)) 12%,transparent);transform:scale(1.12);outline:none}' +
    '.lens-term{border-bottom:1px dotted color-mix(in srgb,var(--muted,var(--mut,#8b93a1)) 65%,transparent);cursor:help;' +
      'border-radius:3px 3px 0 0;transition:color .18s,border-color .18s,background .18s}' +
    '.lens-term:hover,.lens-term.lens-on,.lens-term:focus-visible{color:var(--ink-info, var(--info,var(--blue,#5b9bf0)));' +
      'border-bottom:1px solid var(--info,var(--blue,#5b9bf0));background:color-mix(in srgb,var(--info,var(--blue,#5b9bf0)) 9%,transparent);outline:none}' +
    /* upgraded legacy "?" icons pick up the same live hover accent as .lens-q */
    'span.help.help-upgraded{position:relative;cursor:help;touch-action:manipulation;' +
      'transition:color .18s,border-color .18s,background .18s,box-shadow .22s}' +
    'span.help.help-upgraded:hover,span.help.help-upgraded.lens-on{color:var(--ink-info, var(--info,var(--blue,#5b9bf0)));' +
      'border-color:color-mix(in srgb,var(--info,var(--blue,#5b9bf0)) 55%,transparent);' +
      'background:color-mix(in srgb,var(--info,var(--blue,#5b9bf0)) 13%,transparent);' +
      'box-shadow:0 0 0 3px color-mix(in srgb,var(--info,var(--blue,#5b9bf0)) 12%,transparent)}' +
    'span.help.help-upgraded:focus-visible{color:var(--info,var(--blue));border-color:currentColor;' +
      'outline:2px solid currentColor;outline-offset:3px}' +
    '@media (hover:none),(pointer:coarse){span.help.help-upgraded::before{content:"";position:absolute;' +
      'left:50%;top:50%;width:40px;height:40px;transform:translate(-50%,-50%);border-radius:var(--r-pill,999px)}}' +
    /* One glass shell, shared with the rotation hover card and the heatmap card so
       every popup on a page reads as one component. --glass-* are theme-aware
       (theme.css rebinds them for light); the dark values stay inlined as fallbacks
       for vector-family pages that carry their own token set. */
    '.lens-pop{--lens-panel:var(--panel,var(--card,#181b21));--lens-text:var(--text,var(--ink,#d7dce3));' +
      '--lens-mut:var(--muted,var(--mut,#8b93a1));--lens-accent:var(--info,var(--blue,#5b9bf0));' +
      'position:fixed;left:0;top:0;z-index:12600;width:min(300px,calc(100vw - 24px));border-radius:15px;' +
      'background:var(--glass-bg,color-mix(in srgb,var(--lens-panel) 88%,transparent));' +
      '-webkit-backdrop-filter:var(--glass-blur,saturate(180%) blur(22px));backdrop-filter:var(--glass-blur,saturate(180%) blur(22px));' +
      'box-shadow:var(--glass-shadow,0 24px 64px -18px rgba(3,7,18,.72),0 8px 22px -10px rgba(3,7,18,.5));' +
      'opacity:0;pointer-events:none;transform:translateY(6px) scale(.97);transition:opacity .12s ease,transform .12s ease;' +
      'font-family:var(--font-ui,Inter,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif);' +
      'text-align:left;text-transform:none;letter-spacing:normal;white-space:normal}' +
    '@supports not (backdrop-filter:blur(1px)){.lens-pop{background:color-mix(in srgb,var(--panel,var(--card,#181b21)) 98%,#fff)}}' +
    '.lens-pop.open{opacity:1;pointer-events:auto;transform:none;transition:opacity .18s ease,transform .26s cubic-bezier(.34,1.26,.4,1)}' +
    '.lens-pop::before{content:"";position:absolute;inset:0;border-radius:inherit;padding:1px;' +
      'background:radial-gradient(150px 74px at 20% -6%,color-mix(in srgb,var(--lens-accent) 72%,transparent),transparent 70%),' +
      'var(--glass-brd,color-mix(in srgb,var(--lens-text) 14%,transparent));' +
      '-webkit-mask:linear-gradient(#fff 0 0) content-box,linear-gradient(#fff 0 0);-webkit-mask-composite:xor;' +
      'mask:linear-gradient(#fff 0 0) content-box,linear-gradient(#fff 0 0);mask-composite:exclude;pointer-events:none}' +
    '.lens-pop[data-kind=define]{--lens-accent:var(--info,var(--blue,#5b9bf0))}' +
    '.lens-pop[data-kind=read]{--lens-accent:var(--q2,#d4a017)}' +
    '.lens-pop[data-kind=record]{--lens-accent:var(--ok,var(--up,#3da564))}' +
    '.lens-pop[data-kind=source]{--lens-accent:color-mix(in srgb,var(--lens-mut) 85%,var(--lens-text))}' +
    '.lens-pop[data-kind=caution]{--lens-accent:var(--warn,#e0a030)}' +
    '.lens-hd{display:flex;align-items:center;gap:11px;padding:15px 16px 0}' +
    '.lens-ill{flex:none;width:34px;height:34px;border-radius:11px;display:grid;place-items:center;color:var(--lens-accent);' +
      'background:radial-gradient(120% 120% at 30% 18%,color-mix(in srgb,var(--lens-accent) 24%,transparent),color-mix(in srgb,var(--lens-accent) 6%,transparent) 62%,transparent);' +
      'box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--lens-accent) 30%,transparent)}' +
    '.lens-ill svg{width:20px;height:20px;display:block}' +
    '.lens-hgroup{min-width:0}' +
    '.lens-kick{display:block;font:700 9.5px/1 var(--font-ui,Inter,sans-serif);letter-spacing:.15em;text-transform:uppercase;' +
      'color:color-mix(in srgb,var(--lens-accent) 80%,var(--lens-text))}' +
    '.lens-title{display:block;margin-top:4px;font:700 14px/1.3 var(--font-ui,Inter,sans-serif);letter-spacing:-.01em;color:var(--lens-text)}' +
    '.lens-body{padding:10px 16px 14px;font:450 12.5px/1.62 var(--font-ui,Inter,sans-serif);color:color-mix(in srgb,var(--lens-text) 88%,var(--lens-mut))}' +
    '.lens-body b,.lens-body strong{font-weight:650;color:var(--lens-text)}' +
    '.lens-receipt{display:flex;flex-wrap:wrap;gap:5px 14px;align-items:baseline;margin:0 16px;padding:10px 0 13px;' +
      'border-top:1px dashed color-mix(in srgb,var(--lens-text) 17%,transparent);' +
      'font:600 10px/1.5 var(--font-ui,Inter,sans-serif);letter-spacing:.02em;color:var(--lens-mut)}' +
    '.lens-receipt .r-i{display:inline-flex;align-items:baseline;gap:5px;white-space:nowrap}' +
    '.lens-receipt .r-k{font:700 8.5px/1 var(--font-ui,Inter,sans-serif);letter-spacing:.12em;text-transform:uppercase;' +
      'color:color-mix(in srgb,var(--lens-mut) 75%,transparent)}' +
    /* String tier. Most of the site's ~780 tips land here, so this is the container
       that has to carry itself with no illustrated anatomy to lean on: a headline
       when the author supplies one (data-tip-t-en/zh), a comfortable measure, and
       nothing else. A tip that needs more structure than this belongs in the rich
       tier — that is what it is for. */
    '.lens-pop.lens-plain{width:auto;max-width:min(300px,calc(100vw - 24px))}' +
    '.lens-ttl{display:block;padding:13px 15px 0;font:700 12.5px/1.38 var(--font-ui,Inter,sans-serif);' +
      'letter-spacing:-.012em;color:var(--lens-text)}' +
    '.lens-pop.lens-plain .lens-body{padding:12px 15px 13px;font-size:12.5px;line-height:1.6}' +
    '.lens-ttl+.lens-body{padding-top:5px}' +
    '.lens-pop.lens-plain .lens-receipt{margin:0 15px}' +
    '.lens-pop.open .lens-hd,.lens-pop.open .lens-ttl,.lens-pop.open .lens-body,.lens-pop.open .lens-receipt{animation:lensRise .34s cubic-bezier(.34,1.26,.4,1) both}' +
    '.lens-pop.open .lens-body{animation-delay:.045s}' +
    '.lens-pop.open .lens-receipt{animation-delay:.09s}' +
    '@keyframes lensRise{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}' +
    '.lens-grab,.lens-x{display:none}' +
    '.lens-scrim{position:fixed;inset:0;z-index:12595;background:rgba(4,7,13,.48);' +
      '-webkit-backdrop-filter:blur(5px);backdrop-filter:blur(5px);opacity:0;pointer-events:none;transition:opacity .24s ease}' +
    '.lens-scrim.open{opacity:1;pointer-events:auto}' +
    'html.lens-lock,html.lens-lock body{overflow:hidden}' +
    /* the Mastermind launcher stacks above the sheet — hide it while one is open */
    'html.lens-lock #mmb-root{visibility:hidden !important}' +
    '@media (max-width:640px){' +
      '.lens-pop{left:0 !important;right:0;top:auto !important;bottom:0 !important;width:100%;max-width:100%;' +
        'border-radius:20px 20px 0 0;padding-bottom:max(10px,env(safe-area-inset-bottom));' +
        'max-height:min(72vh,480px);overflow:auto;overscroll-behavior:contain;' +
        'transform:translateY(26px);transform-origin:50% 100% !important}' +
      '.lens-pop.lens-plain{max-width:100%}' +
      '.lens-pop.open{transform:none}' +
      '.lens-grab{display:block;width:38px;height:4px;border-radius:2px;margin:10px auto 2px;' +
        'background:color-mix(in srgb,var(--lens-text) 22%,transparent)}' +
      '.lens-x{display:grid;place-items:center;position:absolute;top:8px;right:8px;z-index:2;width:40px;height:40px;' +
        'border-radius:50%;border:0;padding:0;font:600 11px/1 var(--font-ui,Inter,sans-serif);' +
        'color:var(--lens-mut);background:color-mix(in srgb,var(--lens-mut) 14%,transparent);cursor:pointer}' +
      '.lens-x{touch-action:manipulation}' +
      '.lens-x:focus-visible{outline:2px solid var(--lens-accent);outline-offset:-3px;color:var(--lens-text)}' +
      '.lens-hd{padding-top:8px}' +
      '.lens-ill{width:38px;height:38px}' +
      '.lens-ttl{padding:8px 18px 0;font-size:14px}' +
      '.lens-pop.lens-plain .lens-body{font-size:13px;padding:12px 18px 6px}' +
      '.lens-ttl+.lens-body{padding-top:6px}' +
      '.lens-pop.lens-plain .lens-receipt{margin:0 18px}' +
    '}' +
    '@media (prefers-reduced-motion:reduce){' +
      '.lens-pop,.lens-pop.open{transition:opacity .12s ease;transform:none}' +
      '.lens-pop.open .lens-hd,.lens-pop.open .lens-ttl,.lens-pop.open .lens-body,.lens-pop.open .lens-receipt{animation:none}' +
    '}';

  function injectCss() {
    if (document.getElementById('lens-style')) return;
    var st = document.createElement('style');
    st.id = 'lens-style';
    st.textContent = CSS;
    (document.head || document.documentElement).appendChild(st);
  }
  injectCss();   // eager: trigger styles (.lens-q/.lens-term, upgraded ?) must apply at paint

  function isSheet() { return window.matchMedia && window.matchMedia('(max-width:640px)').matches; }
  function isOpen() { return !!(pop && pop.classList.contains('open')); }
  function touchMode() { return window.matchMedia && window.matchMedia('(hover: none)').matches; }

  function ensure() {
    if (pop) return;
    injectCss();
    scrim = document.createElement('div');
    scrim.className = 'lens-scrim';
    scrim.addEventListener('click', hide);
    document.body.appendChild(scrim);

    pop = document.createElement('div');
    pop.className = 'lens-pop';
    pop.id = 'lensPop';
    pop.setAttribute('role', 'tooltip');
    document.body.appendChild(pop);

    pop.addEventListener('pointerenter', function () { clearTimeout(closeTimer); });
    pop.addEventListener('pointerleave', function () { if (!touchMode()) scheduleClose(); });
    pop.addEventListener('click', function (e) {
      var x = e.target && e.target.closest && e.target.closest('.lens-x');
      if (x) { e.preventDefault(); e.stopPropagation(); hide(); }
    });
    /* swipe-down dismiss on the sheet */
    var y0 = null, dy = 0;
    pop.addEventListener('touchstart', function (e) {
      if (!isSheet() || pop.scrollTop > 0) return;
      y0 = e.touches[0].clientY; dy = 0; pop.style.transition = 'none';
    }, { passive: true });
    pop.addEventListener('touchmove', function (e) {
      if (y0 == null) return;
      dy = Math.max(0, e.touches[0].clientY - y0);
      pop.style.transform = 'translateY(' + dy + 'px)';
    }, { passive: true });
    pop.addEventListener('touchend', function () {
      if (y0 == null) return;
      pop.style.transition = ''; pop.style.transform = '';
      if (dy > 64) hide();
      y0 = null;
    });
  }

  function contentFor(t) {
    var src = null, i, kids = t.children;
    for (i = 0; i < kids.length; i++) {
      if (kids[i].classList && kids[i].classList.contains('lens-src')) { src = kids[i]; break; }
    }
    if (!src && t.nextElementSibling && t.nextElementSibling.classList &&
        t.nextElementSibling.classList.contains('lens-src')) src = t.nextElementSibling;
    if (src) {
      return { kind: t.getAttribute('data-lens-kind') || src.getAttribute('data-lens-kind') || 'define',
               rich: src.innerHTML };
    }
    var en = t.getAttribute('data-tip-en');
    if (!en) return null;
    var rcEn = t.getAttribute('data-tip-rc-en') || '';
    /* Optional headline for the string tier. Without one the card opens on a
       paragraph and the reader has to parse before they know what they are
       reading; with one they can stop after four words. */
    var tEn = t.getAttribute('data-tip-t-en') || '';
    return { kind: t.getAttribute('data-lens-kind') || '',
             tEn: tEn, tZh: t.getAttribute('data-tip-t-zh') || tEn,
             en: en, zh: t.getAttribute('data-tip-zh') || en,
             rcEn: rcEn, rcZh: t.getAttribute('data-tip-rc-zh') || rcEn };
  }

  function mkSpan(cls, txt) {
    var s = document.createElement('span'); s.className = cls; s.textContent = txt; return s;
  }

  function place(t) {
    var r = t.getBoundingClientRect();
    var pw = pop.offsetWidth, ph = pop.offsetHeight;
    var above = r.top - ph - 9 >= 8;
    var y = above ? r.top - ph - 9 : r.bottom + 9;
    if (!above && y + ph > window.innerHeight - 8) y = Math.max(8, window.innerHeight - ph - 8);
    var x = Math.round(Math.max(12, Math.min(r.left + r.width / 2 - pw / 2, window.innerWidth - pw - 12)));
    pop.style.left = x + 'px';
    pop.style.top = Math.round(y) + 'px';
    pop.style.transformOrigin = Math.round(r.left + r.width / 2 - x) + 'px ' + (above ? '100%' : '0%');
  }

  function show(t) {
    var c = contentFor(t);
    if (!c) return;
    ensure();
    clearTimeout(closeTimer);
    if (cur === t && isOpen()) return;
    if (cur) { cur.classList.remove('lens-on'); cur.removeAttribute('aria-describedby'); }
    cur = t;
    t.classList.add('lens-on');
    t.setAttribute('aria-describedby', 'lensPop');

    pop.textContent = '';
    var grab = document.createElement('div'); grab.className = 'lens-grab'; pop.appendChild(grab);
    var x = document.createElement('button'); x.type = 'button'; x.className = 'lens-x';
    x.setAttribute(
      'aria-label',
      document.documentElement.getAttribute('data-lang') === 'zh' ? '关闭' : 'Close'
    );
    x.textContent = '✕'; pop.appendChild(x);
    if (c.rich) {
      pop.classList.remove('lens-plain');
      var wrap = document.createElement('div'); wrap.innerHTML = c.rich;
      while (wrap.firstChild) pop.appendChild(wrap.firstChild);
    } else {
      pop.classList.add('lens-plain');
      if (c.tEn) {
        var ttl = document.createElement('div'); ttl.className = 'lens-ttl';
        ttl.appendChild(mkSpan('l-en', c.tEn)); ttl.appendChild(mkSpan('l-zh', c.tZh));
        pop.appendChild(ttl);
      }
      var body = document.createElement('div'); body.className = 'lens-body';
      body.appendChild(mkSpan('l-en', c.en)); body.appendChild(mkSpan('l-zh', c.zh));
      pop.appendChild(body);
      if (c.rcEn) {
        var rc = document.createElement('div'); rc.className = 'lens-receipt';
        rc.appendChild(mkSpan('l-en', c.rcEn)); rc.appendChild(mkSpan('l-zh', c.rcZh));
        pop.appendChild(rc);
      }
    }
    if (c.kind) pop.setAttribute('data-kind', c.kind); else pop.removeAttribute('data-kind');

    pop.classList.remove('open');
    void pop.offsetWidth;                       /* restart the entrance + sheen */
    pop.classList.add('open');

    if (isSheet()) {
      scrim.classList.add('open');
      document.documentElement.classList.add('lens-lock');
      return;
    }
    scrim.classList.remove('open');
    document.documentElement.classList.remove('lens-lock');
    place(t);
  }

  function hide() {
    clearTimeout(openTimer); clearTimeout(closeTimer);
    if (!pop) return;
    pop.classList.remove('open');
    if (scrim) scrim.classList.remove('open');
    document.documentElement.classList.remove('lens-lock');
    if (cur) { cur.classList.remove('lens-on'); cur.removeAttribute('aria-describedby'); cur = null; }
  }
  function scheduleClose() { clearTimeout(closeTimer); closeTimer = setTimeout(hide, CLOSE_MS); }

  document.addEventListener('pointerover', function (e) {
    // Touch devices: a tap fires pointerover BEFORE click, so pre-showing here would
    // let the click handler immediately toggle it back off (flash-and-vanish) and the
    // tip would never persist. On touch, let the click handler own show/hide entirely.
    if (touchMode()) return;
    if (e.pointerType && e.pointerType !== 'mouse' && e.pointerType !== 'pen') return;
    if (!e.target || !e.target.closest) return;
    var _h = e.target.closest('span.help:not([data-tip-en])'); if (_h) upgradeOne(_h);  // JIT-upgrade client-rendered icons
    var t = e.target.closest(SEL);
    if (t) {
      clearTimeout(closeTimer);
      if (cur === t && isOpen()) return;
      clearTimeout(openTimer);
      openTimer = setTimeout(function () { show(t); }, OPEN_MS);
      return;
    }
    if (pop && pop.contains(e.target)) { clearTimeout(closeTimer); return; }  // keep while over the pop
    clearTimeout(openTimer);
    if (isOpen()) scheduleClose();
  }, true);
  document.addEventListener('pointerout', function (e) {
    if (touchMode()) return;
    if (!e.relatedTarget) {                              // cursor left the window
      clearTimeout(openTimer);                           // don't flash a pending open
      if (isOpen()) scheduleClose();
    }
  }, true);
  document.addEventListener('pointerdown', function () { gestureSeq++; }, true);
  document.addEventListener('focusin', function (e) {
    var t = e.target && e.target.closest && e.target.closest(SEL);
    if (!t) return;
    // Tapping a nested control FOCUSES it, and focusin bubbles up to the wrapper. In
    // SHEET mode show() mounts a full-viewport .lens-scrim — mid-tap. mousedown has
    // already landed on the control but mouseup then lands on the scrim, so the
    // browser retargets the click to <body> and the control's own handler NEVER runs.
    // The click carve-out below cannot save it, because no click survives to reach it.
    // Gated on isSheet() because that is exactly when show() mounts the scrim: the
    // floating card steals nothing, so keyboard focus still discloses the tip on every
    // viewport that can safely show one. Keep this gate in step with show().
    if (isSheet() && nestedCtrl(e.target, t)) return;
    focusShowSeq = gestureSeq;   // this gesture's own trailing click is NOT a dismissal
    focusShowEl = t;
    show(t);
  }, true);
  document.addEventListener('focusout', function (e) {
    var t = e.target && e.target.closest && e.target.closest(SEL);
    if (t) scheduleClose();
  }, true);
  document.addEventListener('click', function (e) {
    if (!e.target || !e.target.closest) return;
    var _h = e.target.closest('span.help:not([data-tip-en])'); if (_h) upgradeOne(_h);  // JIT-upgrade client-rendered icons
    var t = e.target.closest(SEL);
    if (!t) {
      if (isOpen() && !(pop && pop.contains(e.target))) {
        if (gestureOpenedTip(e)) return;   // the opening tap's own retargeted click
        hide();
      }
      return;
    }
    // If the tap landed on an interactive control NESTED INSIDE the tip container
    // (a button/link/field that is a descendant of t — e.g. the Grid/Table view
    // toggle, whose wrapper carries the data-tip), let the control activate instead
    // of hijacking the tap (the old singleton's load-bearing contract). A nested
    // .lens-q can never reach here as ctrl !== t: closest(SEL) resolves the .lens-q
    // itself as the trigger from inside it.
    if (nestedCtrl(e.target, t)) {
      if (isOpen()) hide();
      return;
    }
    var dedicated = t.classList.contains('lens-q') || t.classList.contains('lens-term');
    if (touchMode()) {
      if (!contentFor(t)) return;               // no resolvable tip — never swallow the tap
      e.preventDefault(); e.stopPropagation();
      if (cur === t && isOpen()) { if (!gestureOpenedTip(e)) hide(); } else show(t);
      return;
    }
    if (dedicated) {                            // desktop pin-toggle on purpose-built triggers only
      if (cur === t && isOpen()) { if (!gestureOpenedTip(e)) hide(); } else show(t);
      return;
    }
    // bare data-tip chips: desktop clicks pass through (hover already shows the tip)
  }, true);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && isOpen()) { hide(); return; }
    if ((e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') &&
        e.target && e.target.closest) {
      var help = e.target.closest('span.help.help-upgraded');
      if (help && contentFor(help)) {
        e.preventDefault();
        e.stopPropagation();
        show(help);
      }
    }
  });
  document.addEventListener('langchange', function () {
    if (!pop) return;
    var x = pop.querySelector('.lens-x');
    if (x) x.setAttribute(
      'aria-label',
      document.documentElement.getAttribute('data-lang') === 'zh' ? '关闭' : 'Close'
    );
  });
  window.addEventListener('scroll', function () {
    // The floating card FOLLOWS its trigger; it hides only when the trigger leaves
    // the viewport. Sheet mode is scroll-locked (and the card's own inner scroll
    // must never dismiss it), so skip entirely there.
    if (!isOpen() || !cur || isSheet()) return;
    if (scrollRaf) return;
    scrollRaf = requestAnimationFrame(function () {
      scrollRaf = 0;
      if (!isOpen() || !cur) return;
      var r = cur.getBoundingClientRect();
      if (r.bottom < 0 || r.top > window.innerHeight) { hide(); return; }
      place(cur);
    });
  }, true);
  window.addEventListener('resize', function () { if (isOpen()) hide(); });

  /* Upgrade the legacy help() icons site-wide to this same popover system.
     The old help() macro renders EXACTLY
       <span class="help">?<span class="tip"><span class="l-en">…</span><span class="l-zh">…</span></span></span>
     with a CSS :hover tooltip that (a) doesn't persist on tap, (b) bleeds off-screen
     on mobile, and (c) looks different from the Mag7 / Leadership icons. Rather than
     rewrite ~34 per-page macros + re-render every page, lift each icon's nested .tip
     text into data-tip-en / data-tip-zh so the delegated handler above drives it
     (viewport-clamped popover + tap-to-toggle), and mark it .help-upgraded so CSS can
     suppress the old nested tooltip and apply the new pill look.

     IMPORTANT: the bare `help` class is ALSO reused on non-icon CONTENT elements whose
     tooltips are RICH — market-state factor labels (`f-name help`), the seasonality
     cell (`help` with an SVG chart + table in its .tip), the anticipation index badge
     (`idxbadge … help`). Upgrading those would flatten/delete their content and paint a
     stray pill. So upgradeOne only touches a CANONICAL help() icon: class is EXACTLY
     "help" (single class) AND its direct .tip contains nothing but .l-en / .l-zh.
     Everything else is left completely untouched (keeps its own tooltip + styling). */
  function upgradeOne(el) {
    if (el.hasAttribute('data-tip-en')) return false;
    if (!(el.classList.length === 1 && el.classList.contains('help'))) return false;
    // A canonical help() icon is EXACTLY a "?" text node + a single .tip element child.
    // Content reuses (e.g. the seasonality value cell) carry an extra element child — a
    // value span — alongside their tip, so requiring exactly one element child filters
    // them out even when their tip is a plain l-en/l-zh pair (the low-history fallback).
    var tip = null, tkids, i, c, en = null, zh = null;
    if (el.children.length !== 1) return false;
    tip = el.children[0];
    if (!tip.classList.contains('tip')) return false;
    tkids = tip.children;
    if (tkids.length < 1 || tkids.length > 2) return false;   // canonical tip = l-en (+ l-zh), nothing else
    for (i = 0; i < tkids.length; i++) {
      c = tkids[i];
      // l-en / l-zh must be PLAIN TEXT. A few help() icons pack rich markup (tables, <b>
      // separators) inside their bilingual spans — the popover renders via textContent,
      // which would flatten that to an unreadable run-on, so leave those on their original
      // formatted :hover tooltip rather than upgrading.
      if (c.children.length) return false;
      if (c.classList.contains('l-en')) en = (c.textContent || '').trim();
      else if (c.classList.contains('l-zh')) zh = (c.textContent || '').trim();
      else return false;                                      // any other child → not an icon; leave it
    }
    if (!en) return false;
    el.setAttribute('data-tip-en', en);
    el.setAttribute('data-tip-zh', zh || en);
    el.setAttribute('tabindex', '0');
    el.setAttribute('role', 'button');
    el.classList.add('help-upgraded');
    syncUpgradedHelpLabel(el);
    return true;
  }
  function syncUpgradedHelpLabel(el) {
    if (!el) return;
    var zh = document.documentElement.getAttribute('data-lang') === 'zh';
    el.setAttribute('aria-label', zh ? '更多信息' : 'More information');
  }
  function upgradeHelpIcons(root) {
    var icons = (root || document).querySelectorAll('span.help:not([data-tip-en])');
    for (var i = 0; i < icons.length; i++) upgradeOne(icons[i]);
  }
  document.addEventListener('langchange', function () {
    document.querySelectorAll('span.help.help-upgraded').forEach(syncUpgradedHelpLabel);
  });
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { upgradeHelpIcons(); });
  } else {
    upgradeHelpIcons();
  }
  window.upgradeHelpIcons = upgradeHelpIcons;   // exposed for client-rendered content
  window._upgradeHelpIcon = upgradeOne;         // JIT hook used by the pointerover/click handlers
})();
