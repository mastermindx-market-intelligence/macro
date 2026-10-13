"""Mutation-survey kills for the pullback expiry owner.

The sweep that produced the table below ran outside pytest, against
``tests/test_pullback_expiry_owner_js.py`` and
``tests/test_pullback_expiry_owner_js_edge.py``. Each test here pins a
behaviour a surviving single-edit mutant broke. Stamps are synthetic.
The owner source is not modified.

Mutant table (id, verdict, killer, change):

J001 | KILLED | test_m_focus_without_contains_still_expires | swap `||` -> `&&` in `lement; if (!active || typeof root.contains !=`
J002 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | flip `!==` -> `===` in `|| typeof root.contains !== 'function' || !root.con`
J003 | KILLED | test_m_focus_without_contains_still_expires | swap `||` -> `&&` in `contains !== 'function' || !root.contains(active))`
J004 | KILLED | test_x11_expiry_leaves_focus_that_stays_visible_alone | flip `<` -> `<=` in `; for (var i = 0; i < hidden.length; i += 1)`
J005 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | flip `<` -> `>` in `; for (var i = 0; i < hidden.length; i += 1)`
J006 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | flip `<` -> `>=` in `; for (var i = 0; i < hidden.length; i += 1)`
J007 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | flip `===` -> `!==` in `g = typeof root.closest === 'function' ? root.close`
J008 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | swap `&&` -> `||` in `var target = dlg && (dlg.querySelector('but`
J009 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | swap `||` -> `&&` in `n[aria-label="Close"]') || dlg); if (target`
J010 | KILLED | test_m_focus_inside_without_a_dialog_does_not_throw | swap `&&` -> `||` in `dlg); if (target && typeof target.focus ===`
J011 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | flip `===` -> `!==` in `&& typeof target.focus === 'function') target.focu`
J012 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | swap `||` -> `&&` in `piry'); if (!region || region.getAttribute('da`
J013 | KILLED | test_x13_expiry_fills_the_live_region_once_and_a_future_stamp_stays_empty | flip `===` -> `!==` in `te('data-pb-announced') === '1') return; var ca`
J014 | KILLED | test_x13_expiry_fills_the_live_region_once_and_a_future_stamp_stays_empty | swap `||` -> `&&` in `kup = carrier.innerHTML || ''; if (!markup) re`
J015 | KILLED | test_m_announcement_stays_once_when_the_carrier_cannot_be_removed | swap `&&` -> `||` in `if (carrier.parentNode && typeof carrier.parentNo`
J016 | KILLED | test_m_expiry_hides_the_current_claim_and_announces_once | flip `===` -> `!==` in `.parentNode.removeChild === 'function') { car`
J017 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | swap `||` -> `&&` in `('data-pb-valid-until') || ''; var end = ZON`
J018 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | swap `||` -> `&&` in `(!Number.isFinite(end) || now >= end) { k`
J019 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | flip `>=` -> `>` in `er.isFinite(end) || now >= end) { keepFocu`
J020 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | flip `>=` -> `<` in `er.isFinite(end) || now >= end) { keepFocu`
J021 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | flip `>=` -> `<=` in `er.isFinite(end) || now >= end) { keepFocu`
J022 | KILLED | test_x13_expiry_fills_the_live_region_once_and_a_future_stamp_stays_empty | flip `===` -> `!==` in `if (document.readyState === 'loading') document.add`
J023 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | negate if (!active || typeof root.contains !== 'function' || !root.contains(active))
J024 | KILLED | test_x11_expiry_leaves_focus_that_stays_visible_alone | negate if (!hidden[i].contains(active))
J025 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | negate if (target && typeof target.focus === 'function')
J026 | KILLED | test_x13_expiry_fills_the_live_region_once_and_a_future_stamp_stays_empty | negate if (!region || region.getAttribute('data-pb-announced') === '1')
J027 | KILLED | test_x13_expiry_fills_the_live_region_once_and_a_future_stamp_stays_empty | negate if (!carrier)
J028 | KILLED | test_x13_expiry_fills_the_live_region_once_and_a_future_stamp_stays_empty | negate if (!markup)
J029 | KILLED | test_m_announcement_stays_once_when_the_carrier_cannot_be_removed | negate if (carrier.parentNode && typeof carrier.parentNode.removeChild === 'functi…)
J030 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | negate if (!Number.isFinite(end) || now >= end)
J031 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | negate if (heading)
J032 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | negate if (en)
J033 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | negate if (zh)
J034 | KILLED | test_x6_timer_rearmed_within_60s_when_deadline_is_days_away | negate if (Number.isFinite(next))
J035 | KILLED | test_e6_hidden_tab_does_not_recheck_until_visible | negate if (!document.hidden)
J036 | KILLED | test_x13_expiry_fills_the_live_region_once_and_a_future_stamp_stays_empty | negate if (document.readyState === 'loading')
J037 | KILLED | test_x4_naive_stamp_is_expired | ZONED regex -> /.*/
J038 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | ZONED regex -> /Z$/
J039 | KILLED | test_x4_naive_stamp_is_expired | Number.isFinite(end) -> true
J040 | KILLED | test_e4_two_sections_expire_independently | Number.isFinite(next) -> true
J041 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | drop classList.add('pb-expired')
J067 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | delete expire statement `root.classList.add('pb-expired');`
J042 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | drop setAttribute data-pb-phase
J068 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | delete expire statement `root.setAttribute('data-pb-phase', 'unavailable');`
J043 | KILLED | test_m_announcement_stays_once_when_the_carrier_cannot_be_removed | drop setAttribute data-pb-announced
J059 | KILLED | test_m_announcement_stays_once_when_the_carrier_cannot_be_removed | delete announceExpiry statement `region.setAttribute('data-pb-announced', '1');`
J044 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | en textContent -> ''
J045 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | zh textContent -> ''
J046 | KILLED | test_m_announcement_stays_once_when_the_carrier_cannot_be_removed | remove data-pb-announced idempotence guard
J047 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | delete announceExpiry statement `var region = root.querySelector('.pbx-expiry');`
J048 | KILLED | test_m_announcement_stays_once_when_the_carrier_cannot_be_removed | delete announceExpiry statement `if (!region || region.getAttribute('data-pb-announced') === ...
J049 | KILLED | test_x13_expiry_fills_the_live_region_once_and_a_future_stamp_stays_empty | delete announceExpiry statement `var carrier = root.querySelector('template.pbx-expiry-msg');`
J050 | KILLED | test_m_region_without_a_carrier_expires_quietly | delete announceExpiry statement `if (!carrier) return;`
J051 | KILLED | test_x13_expiry_fills_the_live_region_once_and_a_future_stamp_stays_empty | delete announceExpiry statement `var markup = carrier.innerHTML || '';`
J052 | KILLED | test_m_empty_carrier_does_not_announce | delete announceExpiry statement `if (!markup) return;`
J053 | KILLED | test_x13_expiry_fills_the_live_region_once_and_a_future_stamp_stays_empty | delete announceExpiry statement `var live = document.createElement('span');`
J054 | KILLED | test_x13_expiry_fills_the_live_region_once_and_a_future_stamp_stays_empty | delete announceExpiry statement `live.className = 'pbx-expiry-live';`
J055 | KILLED | test_x13_expiry_fills_the_live_region_once_and_a_future_stamp_stays_empty | delete announceExpiry statement `live.innerHTML = markup;`
J056 | KILLED | test_x13_expiry_fills_the_live_region_once_and_a_future_stamp_stays_empty | delete announceExpiry statement `region.appendChild(live);`
J057 | KILLED | test_m_expiry_hides_the_current_claim_and_announces_once | delete announceExpiry statement `if (carrier.parentNode && typeof carrier.parentNode.removeCh...
J058 | KILLED | test_m_expiry_hides_the_current_claim_and_announces_once | delete announceExpiry statement `carrier.parentNode.removeChild(carrier);`
J060 | KILLED | test_x6_timer_rearmed_within_60s_when_deadline_is_days_away | delete expire statement `window.clearTimeout(timer);`
J061 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | delete expire statement `var now = Date.now(), next = Infinity;`
J062 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | delete expire statement `document.querySelectorAll('.rrp.pbx[data-pb-valid-until]').forEach(f...
J063 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | delete expire statement `var raw = root.getAttribute('data-pb-valid-until') || '';`
J064 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | delete expire statement `var end = ZONED.test(raw) ? Date.parse(raw) : NaN;`
J065 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | delete expire statement `if (!Number.isFinite(end) || now >= end) { keepFocus(root); root.cla...
J066 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | delete expire statement `keepFocus(root);`
J069 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | delete expire statement `var heading = root.querySelector('.pbx-heading h2');`
J070 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | delete expire statement `if (heading) { var en = heading.querySelector('.l-en'), zh = heading...
J071 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | delete expire statement `var en = heading.querySelector('.l-en'), zh = heading.querySelector(...
J072 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | delete expire statement `if (en) en.textContent = 'Price update needed';`
J073 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | delete expire statement `if (zh) zh.textContent = '价格数据待更新';`
J074 | KILLED | test_x13_expiry_fills_the_live_region_once_and_a_future_stamp_stays_empty | delete expire statement `announceExpiry(root);`
J075 | KILLED | test_x6_timer_rearmed_within_60s_when_deadline_is_days_away | delete expire statement `next = Math.min(next, end);`
J076 | KILLED | test_x6_timer_rearmed_within_60s_when_deadline_is_days_away | delete expire statement `if (Number.isFinite(next)) timer = window.setTimeout(expire, Math.mi...
J077 | KILLED | test_x13_expiry_fills_the_live_region_once_and_a_future_stamp_stays_empty | delete boot statement `expire();`
J078 | KILLED | test_x7_mm_pb_expire_twice_does_not_double_install | delete boot statement `document.addEventListener('visibilitychange', function () { if (!docume…`
J079 | KILLED | test_e6_hidden_tab_does_not_recheck_until_visible | delete boot statement `if (!document.hidden) expire();`
J080 | KILLED | test_x7_mm_pb_expire_twice_does_not_double_install | delete boot statement `window.addEventListener('pageshow', expire);`
J081 | KILLED | test_x7_mm_pb_expire_twice_does_not_double_install | delete boot statement `window.addEventListener('focus', expire);`
J082 | KILLED | test_x10_expiry_hands_focus_from_the_hidden_history_to_the_close_button | delete boot-install statement `window.mmPbExpire = expire;`
J083 | KILLED | test_x13_expiry_fills_the_live_region_once_and_a_future_stamp_stays_empty | delete boot-install statement `if (document.readyState === 'loading') document.addEventListen...

The parse line `var end = ZONED.test(raw) ? Date.parse(raw) : NaN;` was replaced by `deadline(raw)`.
"""
from tests import test_pullback_expiry_owner_js as harness

_EN = "Awaiting a newer close. This assessment is no longer current."
_ZH = "等待更新的收盘价。此评估已过时。"

# A section with a status region and an inert carrier. opts selects the DOM
# shapes the owner's guards exist for: no carrier, an empty carrier, a carrier
# whose parent cannot remove it, or the ordinary carrier that removeChild detaches.
_REGION = r"""
const EN = %r;
const ZH = %r;
function expirySection(stamp, opts) {
  opts = opts || {};
  const sec = section(stamp);
  const carrier = {
    className: 'pbx-expiry-msg',
    innerHTML: Object.prototype.hasOwnProperty.call(opts, 'markup')
      ? opts.markup
      : '<span class="l-en">' + EN + '</span><span class="l-zh">' + ZH + '</span>',
    parentNode: null,
  };
  const region = {
    attrs: {},
    children: [],
    getAttribute(name) {
      return Object.prototype.hasOwnProperty.call(this.attrs, name) ? this.attrs[name] : null;
    },
    setAttribute(name, value) { this.attrs[name] = String(value); },
    appendChild(child) {
      this.children.push(child);
      child.parentNode = this;
      return child;
    },
    removeChild(child) {
      const at = this.children.indexOf(child);
      if (at >= 0) this.children.splice(at, 1);
      child.parentNode = null;
      return child;
    },
  };
  if (opts.carrier !== false) {
    if (opts.linkParent !== false) carrier.parentNode = region;
    region.children.push(carrier);
  }
  const baseQuery = sec.querySelector.bind(sec);
  sec.querySelector = (sel) => {
    if (sel === '.pbx-expiry') return region;
    if (sel === 'template.pbx-expiry-msg') {
      if (opts.carrier === false) return null;
      if (opts.sticky) return carrier;
      return region.children.includes(carrier) ? carrier : null;
    }
    return baseQuery(sel);
  };
  sec.region = region;
  sec.carrier = carrier;
  return sec;
}
function liveCount(sec) {
  return sec.region.children.filter((child) => child.className === 'pbx-expiry-live').length;
}
function announced(sec) {
  return sec.region.children
    .filter((child) => child.className === 'pbx-expiry-live')
    .map((child) => child.innerHTML)
    .join('');
}
""" % (_EN, _ZH)


def test_m_deadline_is_closed_at_one_millisecond():
    """A stamp equal to now expires; a stamp one millisecond ahead stays current.

    The owner compares with ``now >= end``. One second of slack would hide a
    flip of that boundary.
    """
    harness._run(
        """
const stamp = '2026-10-12T09:00:00.000Z';
const sec = section(stamp);
now = at(stamp) - 1;
const ctx = boot([sec]);
assertCurrent(sec, '1ms before the deadline');
now = at(stamp);
ctx.window.mmPbExpire();
assertExpired(sec, 'the exact millisecond expires');
const ahead = section(stamp);
now = at(stamp) - 1;
boot([ahead]);
assertCurrent(ahead, 'a stamp 1ms in the future does not expire');
"""
    )


def test_m_missing_live_region_still_expires():
    """A page with no status region still withdraws the current claim, and does not throw."""
    harness._run(
        """
now = at('2026-10-12T09:00:00Z');
const sec = section('2026-10-12T08:00:00Z');
assert.equal(sec.querySelector('.pbx-expiry'), null);
const ctx = boot([sec]);
assertExpired(sec, 'no live region');
ctx.window.mmPbExpire();
assertExpired(sec, 'no live region on the second pass');
"""
    )


def test_m_expiry_hides_the_current_claim_and_announces_once():
    """One expire() both withdraws the current heading and copies the message in once.

    The inert carrier is detached, so a later pass cannot find a second copy.
    Repeating mmPbExpire() leaves a single live span.
    """
    harness._run(
        _REGION
        + """
now = at('2026-10-12T09:00:00Z');
const sec = expirySection('2026-10-12T08:00:00Z');
const ctx = boot([sec]);
assertExpired(sec, 'past stamp');
assert.equal(sec.en.textContent, 'Price update needed');
assert.ok(announced(sec).includes(EN) && announced(sec).includes(ZH), announced(sec));
assert.equal(liveCount(sec), 1);
assert.equal(sec.region.children.includes(sec.carrier), false, 'carrier was not detached');
ctx.window.mmPbExpire();
ctx.window.mmPbExpire();
assert.equal(liveCount(sec), 1, 'repeated mmPbExpire duplicated the announcement');
assert.equal(sec.classes.has('pb-expired'), true);
"""
    )


def test_m_announcement_stays_once_when_the_carrier_cannot_be_removed():
    """The announced flag is the idempotence guard when removeChild cannot run.

    A null parent must not throw, and a second mmPbExpire() must not append
    another live span just because the carrier is still in the tree.
    """
    harness._run(
        _REGION
        + """
now = at('2026-10-12T09:00:00Z');
const sec = expirySection('2026-10-12T08:00:00Z', {linkParent: false, sticky: true});
assert.equal(sec.carrier.parentNode, null);
const ctx = boot([sec]);
assertExpired(sec, 'expired without a removable carrier');
assert.equal(liveCount(sec), 1, 'first announcement');
assert.equal(sec.region.getAttribute('data-pb-announced'), '1');
ctx.window.mmPbExpire();
ctx.window.mmPbExpire();
assert.equal(liveCount(sec), 1, 'second pass repeated the announcement');
assert.ok(announced(sec).indexOf(EN) === announced(sec).lastIndexOf(EN));
"""
    )


def test_m_region_without_a_carrier_expires_quietly():
    """A status region with no inert message expires the panel and inserts nothing."""
    harness._run(
        _REGION
        + """
now = at('2026-10-12T09:00:00Z');
const sec = expirySection('2026-10-12T08:00:00Z', {carrier: false});
const ctx = boot([sec]);
assertExpired(sec, 'region without a carrier');
assert.equal(liveCount(sec), 0);
assert.equal(sec.region.getAttribute('data-pb-announced'), null);
ctx.window.mmPbExpire();
assert.equal(liveCount(sec), 0);
"""
    )


def test_m_empty_carrier_does_not_announce():
    """An empty carrier is not copied into the live region and does not count as announced."""
    harness._run(
        _REGION
        + """
now = at('2026-10-12T09:00:00Z');
const sec = expirySection('2026-10-12T08:00:00Z', {markup: ''});
const ctx = boot([sec]);
assertExpired(sec, 'empty carrier still expires the panel');
assert.equal(liveCount(sec), 0, 'an empty message was announced');
assert.equal(announced(sec), '');
assert.equal(sec.region.getAttribute('data-pb-announced'), null);
ctx.window.mmPbExpire();
assert.equal(liveCount(sec), 0);
"""
    )


def test_m_focus_without_contains_still_expires():
    """A focused section whose root has no contains() still expires, and does not throw.

    The contains test is a guard, not something the owner may call blindly.
    """
    harness._run(
        """
now = at('2026-10-12T09:00:00Z');
const sec = section('2026-10-12T08:00:00Z');
const ctx = boot([sec]);
assertExpired(sec, 'boot');
ctx.document.activeElement = {tag: 'button'};
ctx.window.mmPbExpire();
assertExpired(sec, 'focused section without contains');
assert.equal(sec.en.textContent, 'Price update needed');
"""
    )


def test_m_focus_inside_without_a_dialog_does_not_throw():
    """Focus sitting in the hidden subtree of a section that has no dialog is left alone.

    Expiry still withdraws the current claim. There is no close button to move to,
    and the owner must not touch focus on a null dialog.
    """
    harness._run(
        harness._FOCUS_FIXTURE
        + """
now = at('2026-10-12T09:00:00Z');
const f = dialogWith('2026-10-12T08:00:00Z');
f.sec.closest = () => null;
const ctx = boot([]);
ctx.document.querySelectorAll = () => [f.sec];
ctx.document.activeElement = f.summary;
ctx.window.mmPbExpire();
assertExpired(f.sec, 'no dialog');
assert.equal(f.focused(), null, 'focus was moved without a dialog');
"""
    )
