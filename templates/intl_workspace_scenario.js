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

  var api = {
    parsePercent: parsePercent,
    calculateScenario: calculateScenario,
    sensitivityCases: sensitivityCases
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
  if (typeof window !== "undefined") {
    window.IntlWorkspaceScenario = api;
  }
})();
