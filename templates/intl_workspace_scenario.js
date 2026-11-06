/**
 * Pure manual scenario arithmetic and EN/ZH percent parsing.
 * No I/O, DOM, rounding, or quote-mode conversion. Raw strings stay with the controller.
 */
(function () {
  "use strict";

  var MAX_RAW_LENGTH = 128;
  var SUPPORTED_LOCALES = { en: true, zh: true };
  var EDITING_FORMS = { "+": true, "-": true, ".": true, "+.": true, "-.": true };
  var UNICODE_MINUS = /\u2212/g;
  var PERCENT_GRAMMAR = /^[+-]?(?:(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]*)?|\.[0-9]+)$/;
  var LOCALE_HINT =
    "unsupported_locale: use dot decimal with optional comma thousands (1,234.56 or 1234.56); locales en, zh";

  function isFiniteNumber(value) {
    return typeof value === "number" && Number.isFinite(value);
  }

  function invalidParse(reason) {
    return { status: "invalid", value: null, reason: reason };
  }

  function parsePercent(raw, locale) {
    if (typeof raw !== "string") {
      return invalidParse("not_string");
    }
    if (raw.length > MAX_RAW_LENGTH) {
      return invalidParse("max_length");
    }
    if (typeof locale !== "string" || !Object.hasOwn(SUPPORTED_LOCALES, locale)) {
      return invalidParse(LOCALE_HINT);
    }

    var s = raw.normalize("NFKC").replace(UNICODE_MINUS, "-").trim();
    if (!s) {
      return { status: "blank", value: null, reason: null };
    }
    if (Object.hasOwn(EDITING_FORMS, s)) {
      return { status: "editing", value: null, reason: null };
    }
    if (s.charAt(s.length - 1) === "%") {
      s = s.slice(0, -1).trim();
    }
    if (!PERCENT_GRAMMAR.test(s)) {
      return invalidParse("invalid_format");
    }

    var value = Number(s.replace(/,/g, ""));
    if (!isFiniteNumber(value)) {
      return invalidParse("non_finite");
    }
    return { status: "valid", value: value, reason: null };
  }

  function invalidScenario(reason) {
    return {
      status: "invalid",
      usdPercent: null,
      fxContributionPp: null,
      reason: reason
    };
  }

  // Every finite binary64 number is an integer multiple of 2^-1074.
  // Exact integer evaluation avoids cancellation at either loss boundary and
  // overflow of intermediates whose final percentage is still representable.
  var BINARY_SCALE = 1n << 1074n;
  var HUNDRED_SCALED = 100n * BINARY_SCALE;
  var RESULT_DENOMINATOR = 100n * BINARY_SCALE * BINARY_SCALE;

  function binaryUnits(value) {
    var bits = new DataView(new ArrayBuffer(8));
    bits.setFloat64(0, value);
    var hi = bits.getUint32(0);
    var lo = bits.getUint32(4);
    var exponent = (hi >>> 20) & 2047;
    var mantissa = (BigInt(hi & 1048575) << 32n) | BigInt(lo);
    if (exponent !== 0) {
      mantissa = ((1n << 52n) | mantissa) << BigInt(exponent - 1);
    }
    return hi >>> 31 ? -mantissa : mantissa;
  }

  // Round the exact rational once to nearest binary64, ties to even. This is
  // representation rounding, not decimal/display rounding. Integers are bounded
  // by the binary64 input format (under 4,210 bits), independent of input text.
  function percentageNumber(numerator) {
    if (numerator === 0n) return 0;
    var negative = numerator < 0n;
    var n = negative ? -numerator : numerator;
    var d = RESULT_DENOMINATOR;
    var exponent = n.toString(2).length - d.toString(2).length;
    if (exponent >= 0 ? n < (d << BigInt(exponent)) :
        (n << BigInt(-exponent)) < d) {
      exponent -= 1;
    }
    if (exponent > 1023) return negative ? -Infinity : Infinity;
    var shift = exponent < -1022 ? 1074 : 52 - exponent;
    if (shift >= 0) n <<= BigInt(shift);
    else d <<= BigInt(-shift);
    var significand = n / d;
    var remainder = n % d;
    var twiceRemainder = remainder * 2n;
    if (twiceRemainder > d ||
        (twiceRemainder === d && (significand & 1n) !== 0n)) {
      significand += 1n;
    }
    var value = Number(significand) *
      (exponent < -1022 ? Number.MIN_VALUE : Math.pow(2, exponent - 52));
    return negative ? -value : value;
  }

  function calculateScenario(localPercent, fxPercent) {
    if (!isFiniteNumber(localPercent) || !isFiniteNumber(fxPercent)) {
      return invalidScenario("non_finite_input");
    }
    if (localPercent < -100) {
      return invalidScenario("local_below_total_loss");
    }
    if (fxPercent <= -100) {
      return invalidScenario("fx_nonpositive_endpoint");
    }

    var local = binaryUnits(localPercent);
    var fx = binaryUnits(fxPercent);
    var localEndpoint = HUNDRED_SCALED + local;
    var usdPercent = percentageNumber(localEndpoint * (HUNDRED_SCALED + fx) -
      HUNDRED_SCALED * HUNDRED_SCALED);
    var fxContributionPp = percentageNumber(localEndpoint * fx);
    if (!isFiniteNumber(usdPercent) || !isFiniteNumber(fxContributionPp)) {
      return invalidScenario("overflow");
    }
    return {
      status: "valid",
      usdPercent: usdPercent,
      fxContributionPp: fxContributionPp,
      reason: null
    };
  }

  function sameFx(a, b) {
    return a === b;
  }

  function sensitivityCases(localPercent, currentFxPercent) {
    if (calculateScenario(localPercent, currentFxPercent).status !== "valid") {
      return [];
    }

    var candidates = [
      ["current", currentFxPercent],
      ["unchanged", 0],
      ["illustrative_plus3", 3]
    ];
    var rows = [];
    var seen = [];
    var i;
    var kind;
    var fx;
    var generated;
    var j;
    var already;

    for (i = 0; i < candidates.length; i += 1) {
      kind = candidates[i][0];
      fx = candidates[i][1];
      already = false;
      for (j = 0; j < seen.length; j += 1) {
        if (sameFx(seen[j], fx)) {
          already = true;
          break;
        }
      }
      if (already) {
        continue;
      }
      generated = calculateScenario(localPercent, fx);
      if (generated.status !== "valid") {
        return [];
      }
      seen.push(fx);
      rows.push({
        kind: kind,
        fxPercent: fx,
        usdPercent: generated.usdPercent
      });
    }
    return rows;
  }

  // A pure draft reducer used by the one workspace controller. Context proposals
  // are tentative until that controller commits its existing research reducer.
  function draftCopy(value, depth) {
    if (depth > 12) throw new TypeError('invalid_scenario_draft');
    if (value === null || typeof value === 'string' || typeof value === 'boolean') return value;
    if (typeof value === 'number' && Number.isFinite(value)) return value;
    if (!value || typeof value !== 'object' ||
        (!Array.isArray(value) && Object.getPrototypeOf(value) !== Object.prototype)) throw new TypeError('invalid_scenario_draft');
    var result = Array.isArray(value) ? [] : {};
    var keys = Reflect.ownKeys(value);
    if (keys.length > 40) throw new TypeError('invalid_scenario_draft');
    keys.forEach(function (key) {
      if (Array.isArray(value) && key === 'length') return;
      var descriptor = Object.getOwnPropertyDescriptor(value, key);
      if (typeof key !== 'string' || !descriptor.enumerable || !Object.hasOwn(descriptor, 'value') ||
          ['__proto__','constructor','prototype'].includes(key)) throw new TypeError('invalid_scenario_draft');
      result[key] = draftCopy(descriptor.value, depth + 1);
    });
    return result;
  }

  function draftShape(value, names) {
    if (!value || Array.isArray(value) || typeof value !== 'object' ||
        Object.keys(value).length !== names.length || !names.every(function (key) { return Object.hasOwn(value,key); })) {
      throw new TypeError('invalid_scenario_draft');
    }
  }

  function draftContext(value) {
    var context = draftCopy(value,0);
    draftShape(context,['selected_market','horizon','currency_basis']);
    if ((context.selected_market !== null && (typeof context.selected_market !== 'string' || !context.selected_market)) ||
        typeof context.horizon !== 'string' || !context.horizon ||
        !['local','usd_unhedged'].includes(context.currency_basis)) throw new TypeError('invalid_scenario_draft');
    // The existing research reducer remains responsible for roster/horizon admission.
    return context;
  }

  function sameContext(a,b) {
    return a.selected_market === b.selected_market && a.horizon === b.horizon && a.currency_basis === b.currency_basis;
  }

  function emptyErrors() { return {local:null,fx:null}; }

  function createDraft(context) {
    return {context:draftContext(context),raw:{local:'',fx:''},result:null,rows:[],pending:null,
      reset_pending:false,errors:emptyErrors(),tab:'history'};
  }

  function evaluateRaw(raw, locale) {
    var local = parsePercent(raw.local,locale), fx = parsePercent(raw.fx,locale), errors = emptyErrors();
    if (local.status !== 'valid') errors.local = local.reason || 'input_required';
    else if (local.value < -100) errors.local = 'local_below_total_loss';
    if (fx.status !== 'valid') errors.fx = fx.reason || 'input_required';
    else if (fx.value <= -100) errors.fx = 'fx_nonpositive_endpoint';
    var result = null, rows = [];
    if (!errors.local && !errors.fx) {
      var computed = calculateScenario(local.value,fx.value);
      rows = sensitivityCases(local.value,fx.value);
      if (computed.status !== 'valid' || !rows.length) { errors.local = 'overflow'; rows = []; }
      else result = computed;
    }
    return {errors:errors,result:result,rows:rows};
  }

  function checkDraft(value) {
    var d = draftCopy(value,0);
    draftShape(d,['context','raw','result','rows','pending','reset_pending','errors','tab']);
    draftContext(d.context);
    function rawShape(raw) {
      draftShape(raw,['local','fx']);
      if (typeof raw.local !== 'string' || typeof raw.fx !== 'string') throw new TypeError('invalid_scenario_draft');
    }
    rawShape(d.raw);
    draftShape(d.errors,['local','fx']);
    if (![d.errors.local,d.errors.fx].every(function (v) { return v === null || typeof v === 'string'; }) ||
        typeof d.reset_pending !== 'boolean' || !['history','scenario'].includes(d.tab) || !Array.isArray(d.rows)) {
      throw new TypeError('invalid_scenario_draft');
    }
    if (d.pending !== null) {
      draftShape(d.pending,['context','raw','original_errors']); draftContext(d.pending.context); rawShape(d.pending.raw);
      draftShape(d.pending.original_errors,['local','fx']);
      if (![d.pending.original_errors.local,d.pending.original_errors.fx].every(function (v) { return v === null || typeof v === 'string'; })) throw new TypeError('invalid_scenario_draft');
      if (d.reset_pending || sameContext(d.context,d.pending.context)) throw new TypeError('invalid_scenario_draft');
    }
    if (d.result !== null) {
      var expected = evaluateRaw(d.raw,'en');
      if (expected.result === null || JSON.stringify(d.result) !== JSON.stringify(expected.result) ||
          JSON.stringify(d.rows) !== JSON.stringify(expected.rows)) throw new TypeError('invalid_scenario_draft');
    } else if (d.rows.length) throw new TypeError('invalid_scenario_draft');
    return d;
  }

  function reduceDraft(value, command, locale) {
    var d = checkDraft(value), prior = checkDraft(value), commit = null, focus = null, announce = false;
    function response(ok, reason) {
      return {ok:ok,draft:d,context_commit:commit,focus:focus,announce:announce,reason:reason || null,
        visible_result:d.pending ? null : d.result,visible_rows:d.pending ? [] : d.rows};
    }
    function refuse(reason) { d = prior; return response(false,reason); }
    var c;
    try {
      c = draftCopy(command,0);
      var shapes = {edit:['type','field','raw'],calculate:['type'],set_tab:['type','tab'],
        propose_context:['type','context'],confirm_context:['type'],cancel_context:['type'],
        request_reset:['type'],confirm_reset:['type'],cancel_reset:['type']};
      if (!c || !Object.hasOwn(shapes,c.type)) return refuse('invalid_action');
      draftShape(c,shapes[c.type]);
      if (c.type === 'edit') {
        if (d.reset_pending || !['local','fx'].includes(c.field) || typeof c.raw !== 'string') return refuse('invalid_action');
        (d.pending ? d.pending.raw : d.raw)[c.field] = c.raw;
        d.errors = emptyErrors();
        if (!d.pending) { d.result = null; d.rows = []; }
      } else if (c.type === 'set_tab') {
        if (!['history','scenario'].includes(c.tab)) return refuse('invalid_action');
        d.tab = c.tab;
      } else if (c.type === 'propose_context') {
        var proposed = draftContext(c.context);
        if (d.pending || d.reset_pending) return refuse('confirmation_pending');
        if (!sameContext(d.context,proposed)) {
          if (d.raw.local !== '' || d.raw.fx !== '') {
            d.pending = {context:proposed,raw:draftCopy(d.raw,0),original_errors:draftCopy(d.errors,0)}; d.errors = emptyErrors();
          } else { d.context = proposed; commit = draftCopy(proposed,0); }
        }
      } else if (c.type === 'calculate' || c.type === 'confirm_context') {
        if (d.reset_pending || (c.type === 'calculate' ? d.pending !== null : d.pending === null)) return refuse('confirmation_required');
        var calculation = evaluateRaw(d.pending ? d.pending.raw : d.raw,locale);
        d.errors = calculation.errors;
        if (calculation.result === null) {
          if (!d.pending) { d.result = null; d.rows = []; }
          focus = d.errors.local ? 'local' : 'fx';
          return response(false,'invalid_inputs');
        }
        announce = d.pending !== null || JSON.stringify(d.result) !== JSON.stringify(calculation.result);
        if (d.pending) {
          d.context = d.pending.context; d.raw = d.pending.raw; d.pending = null; commit = draftCopy(d.context,0);
        }
        d.result = calculation.result; d.rows = calculation.rows;
      } else if (c.type === 'cancel_context') {
        if (!d.pending) return refuse('confirmation_required');
        d.errors = d.pending.original_errors; d.pending = null;
      } else if (c.type === 'request_reset') {
        if (d.pending) return refuse('confirmation_pending');
        d.reset_pending = true;
      } else if (c.type === 'confirm_reset') {
        if (!d.reset_pending) return refuse('confirmation_required');
        d.raw = {local:'',fx:''}; d.result = null; d.rows = []; d.errors = emptyErrors(); d.reset_pending = false;
      } else if (c.type === 'cancel_reset') {
        if (!d.reset_pending) return refuse('confirmation_required');
        d.reset_pending = false;
      }
    } catch (_) { return refuse('invalid_action'); }
    return response(true);
  }

  var api = {
    parsePercent: parsePercent,
    calculateScenario: calculateScenario,
    sensitivityCases: sensitivityCases,
    createDraft: createDraft,
    reduceDraft: reduceDraft
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
  if (typeof window !== "undefined") {
    window.IntlWorkspaceScenario = api;
  }
})();
