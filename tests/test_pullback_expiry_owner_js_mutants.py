r"""Mutation-survey kills for the pullback expiry owner.

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

2026-10-12 addendum: the strict-stamp parser that replaced that parse line is
surveyed below (J084-J110, kill set: both Node expiry suites, the deadline
suite, and every fragment suite that boots the owner). Two survivors are
equivalent, not missing pins: deleting the two-digit-year guard only moves a
stamp between two expired outcomes (``Date.UTC`` maps years 0..99 onto
1900..1999, strictly behind any clock the page can run under), and deleting
the finiteness conjunct cannot change the verdict because the guarded regex
bounds leave ``instant`` finite whenever that line is reached.

J084 | KILLED | test_loose_spellings_expire | drop the `^` anchor from STAMP
J085 | KILLED | test_loose_spellings_expire | drop the `$` anchor from STAMP
J086 | KILLED | test_m_six_zero_fraction_digits_are_that_same_second | regex quantifier `\.0{1,6}` -> `\.0{1,5}`
J087 | KILLED | test_loose_spellings_expire | `(\.0{1,6})?` -> `(\.[0-9]{1,6})?` (accept a non-zero fraction)
J088 | KILLED | test_expiry_script_honours_only_zoned_deadlines_and_rechecks_on_wake | make the zone group optional `(Z|[+-](\d{2}):(\d{2}))?`
J089 | KILLED | test_m_january_is_a_month | swap `<` -> `<=` in `if (month < 1 || month > 12`
J090 | KILLED | test_loose_spellings_expire | swap `>` -> `>=` in `month > 12`
J091 | KILLED | test_m_hour_23_is_a_valid_civil_hour | swap `>` -> `>=` in `hour > 23`
J092 | KILLED | test_e3_deadlines_across_us_dst_fallback_expire_on_absolute_instants | swap `>` -> `>=` in `minute > 59`
J093 | KILLED | test_e3_deadlines_across_us_dst_fallback_expire_on_absolute_instants | swap `>` -> `>=` in `second > 59`
J094 | KILLED | test_impossible_civil_stamps_expire_immediately | swap `||` -> `&&` across the whole civil-bounds guard
J095 | EQUIVALENT | - | delete `if (year < 100) return NaN;` (both outcomes expired; see addendum)
J096 | KILLED | test_impossible_civil_stamps_expire_immediately | month-length lookup `Date.UTC(year, month, 0)` -> `Date.UTC(year, month - 1, 0)`
J097 | KILLED | test_x3_negative_offsets_honoured_across_us_dst | swap `<` -> `<=` in `if (day < 1 || day > length)`
J098 | KILLED | test_february_29_follows_the_gregorian_month_length | swap `>` -> `>=` in `day > length`
J099 | KILLED | test_expiry_script_honours_only_zoned_deadlines_and_rechecks_on_wake | flip `!==` -> `===` in `if (match[8] !== 'Z')`
J100 | KILLED | test_offset_hours_stop_at_14 | swap `>` -> `>=` in `offH > 14`
J101 | KILLED | test_m_offset_minute_59_is_a_deadline | swap `>` -> `>=` in `offM > 59`
J102 | KILLED | test_x1_plus08_expires_at_0900z | invert the offset sign `match[8].charAt(0) === '-' ? -1 : 1` -> `!== '-'`
J103 | KILLED | test_deadline_beyond_400_days_expires | swap `>` -> `>=` in `instant - Date.now() > MAX_AHEAD_MS`
J104 | KILLED | test_impossible_civil_stamps_expire_immediately | swap the max-ahead operands `instant - Date.now()` -> `Date.now() - instant`
J105 | KILLED | test_deadline_beyond_400_days_expires | constant `400` -> `401` in MAX_AHEAD_MS
J106 | KILLED | test_deadline_beyond_400_days_expires | constant `400` -> `399` in MAX_AHEAD_MS
J107 | KILLED | test_expiry_script_honours_only_zoned_deadlines_and_rechecks_on_wake | negate `if (!match) return NaN;`
J108 | KILLED | test_expiry_script_honours_only_zoned_deadlines_and_rechecks_on_wake | revert the call site `deadline(raw)` -> `Date.parse(raw)`
J109 | KILLED | test_deadline_beyond_400_days_expires | constant `60` -> `61` minutes in MAX_AHEAD_MS
J110 | EQUIVALENT | - | delete `!Number.isFinite(instant) ||` (instant is finite whenever the line is reached; see addendum)

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


def test_m_six_zero_fraction_digits_are_that_same_second():
    """Six zero fraction digits are the producer's whole second, not garbage.

    The fraction quantifier is ``{1,6}``. Shortening it to five digits (J086)
    turns ``.000000`` into an unreadable stamp, so a section whose deadline the
    producer can still emit expires early.
    """
    harness._run(
        """
const stamp = '2026-12-01T00:00:00.000000Z';
const sec = section(stamp);
now = at(stamp) - 1;
const ctx = boot([sec]);
assertCurrent(sec, 'a .000000 stamp 1ms before');
now = at(stamp);
ctx.window.mmPbExpire();
assertExpired(sec, 'a .000000 stamp on its instant');
"""
    )


def test_m_january_is_a_month():
    """A January deadline stays current until its own instant.

    The month bound is one-sided on purpose: ``month < 1``. Tightening it to
    ``<=`` (J089) expires every January stamp.
    """
    harness._run(
        """
const stamp = '2027-01-15T09:00:00Z';
const sec = section(stamp);
now = at(stamp) - 1;
const ctx = boot([sec]);
assertCurrent(sec, 'January 1ms before');
now = at(stamp);
ctx.window.mmPbExpire();
assertExpired(sec, 'January on its instant');
"""
    )


def test_m_hour_23_is_a_valid_civil_hour():
    """23:30 is a real deadline; only hour 24 and beyond is impossible.

    Hour 23 is the last civil hour, so the guard must stay strict (``> 23``).
    Widening it to ``>=`` (J091) expires a late-evening deadline while it still
    holds.
    """
    harness._run(
        """
const stamp = '2026-10-12T23:30:00Z';
const sec = section(stamp);
now = at(stamp) - 60 * 1000;
const ctx = boot([sec]);
assertCurrent(sec, '23:30 one minute before');
now = at(stamp);
ctx.window.mmPbExpire();
assertExpired(sec, '23:30 on its instant');
"""
    )


def test_m_offset_minute_59_is_a_deadline():
    """An offset minute of 59 is inside the bound the guard keeps.

    ``+08:59`` is one minute inside the ±14:59 limit the guard accepts, so a
    stamp carrying it stays current until its instant. Widening the minute test
    to ``>= 59`` (J101) expires such a stamp on sight.
    """
    harness._run(
        """
const stamp = '2026-10-15T09:59:00+08:59';
const instant = at(stamp);
assert.equal(instant, at('2026-10-15T01:00:00Z'), 'fixture instant');
const sec = section(stamp);
now = instant - 1;
const ctx = boot([sec]);
assertCurrent(sec, '+08:59 one millisecond before');
now = instant;
ctx.window.mmPbExpire();
assertExpired(sec, '+08:59 on its instant');
"""
    )
