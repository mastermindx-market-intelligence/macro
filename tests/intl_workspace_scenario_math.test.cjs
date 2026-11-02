"use strict";

const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const api = require("../templates/intl_workspace_scenario.js");
const { parsePercent, calculateScenario, sensitivityCases } = api;

function closeToDecimal(actual, decimalStr) {
  const expected = Number(decimalStr);
  assert.equal(typeof actual, "number");
  assert.ok(Number.isFinite(actual), "actual must be finite, got " + actual);
  assert.ok(Number.isFinite(expected), "decimal reference must be finite");
  const scale = Math.max(1, Math.abs(expected), Math.abs(actual));
  const tol = Number.EPSILON * 64 * scale;
  assert.ok(
    Math.abs(actual - expected) <= tol,
    actual + " not within " + tol + " of Decimal " + decimalStr
  );
}

function assertInvalidParse(result, reasonPrefix) {
  assert.equal(result.status, "invalid");
  assert.equal(result.value, null);
  assert.equal(typeof result.reason, "string");
  if (reasonPrefix) {
    assert.ok(result.reason.indexOf(reasonPrefix) === 0, result.reason);
  }
}

function assertInvalidScenario(result, reason) {
  assert.equal(result.status, "invalid");
  assert.equal(result.usdPercent, null);
  assert.equal(result.fxContributionPp, null);
  if (reason) {
    assert.equal(result.reason, reason);
  } else {
    assert.equal(typeof result.reason, "string");
  }
}

describe("module surface without DOM", () => {
  it("exports the three contract functions via CommonJS", () => {
    assert.equal(typeof parsePercent, "function");
    assert.equal(typeof calculateScenario, "function");
    assert.equal(typeof sensitivityCases, "function");
    assert.equal(api.parsePercent, parsePercent);
    assert.equal(typeof document, "undefined");
    assert.equal(typeof window, "undefined");
  });

  it("does not require a bundler path or ES import", () => {
    const resolved = require.resolve("../templates/intl_workspace_scenario.js");
    assert.equal(path.extname(resolved), ".js");
  });
});

describe("parsePercent blank and editing", () => {
  it("blank whitespace is blank, never zero", () => {
    const r = parsePercent(" ", "en");
    assert.equal(r.status, "blank");
    assert.equal(r.value, null);
    assert.equal(r.reason, null);
    assert.notEqual(r.value, 0);
  });

  it("empty string is blank", () => {
    const r = parsePercent("", "zh");
    assert.equal(r.status, "blank");
    assert.equal(r.value, null);
  });

  it("lone sign and sign+dot stay editing", () => {
    ["+", "-", ".", "+.", "-."].forEach((raw) => {
      const r = parsePercent(raw, "en");
      assert.equal(r.status, "editing", raw);
      assert.equal(r.value, null, raw);
      assert.equal(r.reason, null, raw);
    });
  });

  it("padded lone minus remains editing", () => {
    const r = parsePercent("  -  ", "en");
    assert.equal(r.status, "editing");
    assert.equal(r.value, null);
  });

  it("unicode minus alone is editing after normalization", () => {
    const r = parsePercent("\u2212", "en");
    assert.equal(r.status, "editing");
    assert.equal(r.value, null);
  });
});

describe("parsePercent valid forms", () => {
  it("ascii percent +5.00%", () => {
    const r = parsePercent("+5.00%", "en");
    assert.equal(r.status, "valid");
    closeToDecimal(r.value, "5.00");
    assert.equal(r.reason, null);
  });

  it("unicode minus percent", () => {
    const r = parsePercent("\u22123.00%", "en");
    assert.equal(r.status, "valid");
    closeToDecimal(r.value, "-3.00");
  });

  it("fullwidth ZH digits, signs, and percent", () => {
    const r = parsePercent("＋５．００％", "zh");
    assert.equal(r.status, "valid");
    closeToDecimal(r.value, "5");
  });

  it("fullwidth grouped thousands", () => {
    const r = parsePercent("１，２３４．５％", "zh");
    assert.equal(r.status, "valid");
    closeToDecimal(r.value, "1234.5");
  });

  it("optional percent sign and leading-dot fraction", () => {
    const a = parsePercent("-.5", "en");
    const b = parsePercent("-.5%", "en");
    assert.equal(a.status, "valid");
    assert.equal(b.status, "valid");
    closeToDecimal(a.value, "-0.5");
    closeToDecimal(b.value, "-0.5");
  });

  it("true zero is valid zero, distinct from blank", () => {
    const zero = parsePercent("0", "en");
    const blank = parsePercent("", "en");
    assert.equal(zero.status, "valid");
    closeToDecimal(zero.value, "0");
    assert.equal(blank.status, "blank");
    assert.equal(blank.value, null);
    const plusZero = parsePercent("+0%", "en");
    assert.equal(plusZero.status, "valid");
    closeToDecimal(plusZero.value, "0");
  });

  it("trailing percent with space and trailing dot", () => {
    assert.equal(parsePercent("5 %", "en").status, "valid");
    closeToDecimal(parsePercent("5 %", "en").value, "5");
    assert.equal(parsePercent("5.", "en").status, "valid");
    closeToDecimal(parsePercent("5.", "en").value, "5");
  });

  it("correct comma thousands grouping", () => {
    const r = parsePercent("1,234.5%", "en");
    assert.equal(r.status, "valid");
    closeToDecimal(r.value, "1234.5");
    const grouped = parsePercent("+1,234,567.89", "zh");
    assert.equal(grouped.status, "valid");
    closeToDecimal(grouped.value, "1234567.89");
  });

  it("preserves the original raw string (controller-owned)", () => {
    const raw = "+5.00%";
    parsePercent(raw, "en");
    assert.equal(raw, "+5.00%");
    const fullwidth = "＋５．００％";
    parsePercent(fullwidth, "zh");
    assert.equal(fullwidth, "＋５．００％");
  });
});

describe("parsePercent rejections", () => {
  it("decimal comma 1,5 is invalid, not 15 or 1.5", () => {
    const r = parsePercent("1,5", "en");
    assertInvalidParse(r, "invalid_format");
  });

  it("malformed grouping 12,34.0 is invalid", () => {
    assertInvalidParse(parsePercent("12,34.0", "zh"), "invalid_format");
    assertInvalidParse(parsePercent("1234,567", "en"), "invalid_format");
    assertInvalidParse(parsePercent("1,2345", "en"), "invalid_format");
  });

  it("trailing text, double percent, and internal words", () => {
    assertInvalidParse(parsePercent("5 percent", "en"), "invalid_format");
    assertInvalidParse(parsePercent("5%%", "en"), "invalid_format");
    assertInvalidParse(parsePercent("5.0foo", "en"), "invalid_format");
  });

  it("exponent notation is rejected", () => {
    assertInvalidParse(parsePercent("1e3", "en"), "invalid_format");
    assertInvalidParse(parsePercent("1E3", "en"), "invalid_format");
    assertInvalidParse(parsePercent("1e-2", "en"), "invalid_format");
  });

  it("accounting parentheses and double signs", () => {
    assertInvalidParse(parsePercent("(5)", "en"), "invalid_format");
    assertInvalidParse(parsePercent("++5", "en"), "invalid_format");
    assertInvalidParse(parsePercent("+-5", "en"), "invalid_format");
  });

  it("unsupported locale gets a decimal-format hint, not a guessed parse", () => {
    const r = parsePercent("1.5", "fr");
    assertInvalidParse(r, "unsupported_locale");
    assert.ok(/dot decimal/i.test(r.reason));
    assert.ok(/1,234\.56/.test(r.reason));
    assert.equal(r.value, null);
    assertInvalidParse(parsePercent("1,5", "fr"), "unsupported_locale");
    assertInvalidParse(parsePercent("1.5", "EN"), "unsupported_locale");
    assertInvalidParse(parsePercent("1.5", null), "unsupported_locale");
  });

  it("max raw length 128 allowed, 129 invalid", () => {
    const ok = parsePercent("1".repeat(128), "en");
    assert.equal(ok.status, "valid");
    assert.equal(typeof ok.value, "number");
    const tooLong = parsePercent("1".repeat(129), "en");
    assertInvalidParse(tooLong, "max_length");
    const longBlankish = parsePercent(" ".repeat(129), "en");
    assertInvalidParse(longBlankish, "max_length");
  });

  it("booleans, null, numbers, and NaN are not strings", () => {
    [true, false, null, undefined, 0, 5, NaN, Infinity, { raw: "5" }].forEach((raw) => {
      const r = parsePercent(raw, "en");
      assertInvalidParse(r, "not_string");
    });
  });

  it("percent-only and sign-plus-percent are invalid, not blank/editing/zero", () => {
    assertInvalidParse(parsePercent("%", "en"), "invalid_format");
    assertInvalidParse(parsePercent("+.%", "en"), "invalid_format");
    assert.notEqual(parsePercent("%", "en").status, "blank");
  });
});

describe("calculateScenario arithmetic", () => {
  it("golden +5 / -3 -> USD 1.85 and FX contribution -3.15", () => {
    const local = parsePercent("5", "en");
    const fx = parsePercent("-3", "en");
    assert.equal(local.status, "valid");
    assert.equal(fx.status, "valid");
    const r = calculateScenario(local.value, fx.value);
    assert.equal(r.status, "valid");
    closeToDecimal(r.usdPercent, "1.85");
    closeToDecimal(r.fxContributionPp, "-3.15");
    assert.equal(r.reason, null);
  });

  it("numeric +5 / -3 matches the parsed golden path", () => {
    const r = calculateScenario(5, -3);
    assert.equal(r.status, "valid");
    closeToDecimal(r.usdPercent, "1.8500");
    closeToDecimal(r.fxContributionPp, "-3.1500");
  });

  it("-1.8 / -0.8 -> -2.5856 USD and -0.7856pp, unrounded", () => {
    const r = calculateScenario(-1.8, -0.8);
    assert.equal(r.status, "valid");
    closeToDecimal(r.usdPercent, "-2.585600");
    closeToDecimal(r.fxContributionPp, "-0.785600");
    assert.ok(Math.abs(r.usdPercent - (-2.59)) > Math.abs(r.usdPercent - (-2.5856)));
  });

  it("local total loss -100 with valid FX is -100 USD and 0 contribution", () => {
    const r = calculateScenario(-100, 3);
    assert.equal(r.status, "valid");
    closeToDecimal(r.usdPercent, "-100");
    closeToDecimal(r.fxContributionPp, "0");
  });

  it("local below total loss is invalid, not a computed number", () => {
    const r = calculateScenario(-100.01, 3);
    assertInvalidScenario(r, "local_below_total_loss");
  });

  it("FX -100 is invalid while local -100 is valid", () => {
    const fxLoss = calculateScenario(5, -100);
    assertInvalidScenario(fxLoss, "fx_nonpositive_endpoint");
    const fxBelow = calculateScenario(5, -100.01);
    assertInvalidScenario(fxBelow, "fx_nonpositive_endpoint");
    const localLoss = calculateScenario(-100, 3);
    assert.equal(localLoss.status, "valid");
  });

  it("true zero local and FX is valid zeros", () => {
    const r = calculateScenario(0, 0);
    assert.equal(r.status, "valid");
    closeToDecimal(r.usdPercent, "0");
    closeToDecimal(r.fxContributionPp, "0");
  });

  it("does not round inside the core formulas", () => {
    // 5 / -3 is exactly 1.85: binary noise is not evidence of retained
    // precision. Use an answer with actual digits beyond display precision.
    const r = calculateScenario(-1.8, -0.8);
    assert.notEqual(r.usdPercent, Number(r.usdPercent.toFixed(2)));
    closeToDecimal(r.usdPercent, "-2.5856");
  });
});

describe("exact-input numerical stability", () => {
  // References are Decimal.from_float on BOTH inputs, precision 1000;
  // they are not decimal-string reinterpretations of binary64 inputs.
  it("preserves the positive FX endpoint immediately above total loss", () => {
    const r = calculateScenario(1e20, -99.99999999999999);
    assert.equal(r.status, "valid");
    closeToDecimal(r.usdPercent, "14110.8547152020037316333400667645037174224853515625");
    closeToDecimal(r.fxContributionPp, "-99999999999999985789.1452847979962825775146484375");
  });

  it("preserves the local endpoint immediately above total loss", () => {
    const r = calculateScenario(-99.99999999999999, 1e20);
    assert.equal(r.status, "valid");
    closeToDecimal(r.usdPercent, "14110.8547152020037316333400667645037174224853515625");
    closeToDecimal(r.fxContributionPp, "14210.8547152020037174224853515625");
  });

  it("retains a small residual after large cancelling assumptions", () => {
    const r = calculateScenario(1e10, -99.99999900000002);
    assert.equal(r.status, "valid");
    closeToDecimal(r.usdPercent, "-0.0000006735612174679773");
    closeToDecimal(r.fxContributionPp, "-10000000000");
  });

  it("keeps tiny assumptions and subnormal results instead of cancelling them to zero", () => {
    const tiny = calculateScenario(1e-20, 1e-20);
    assert.equal(tiny.status, "valid");
    assert.equal(tiny.usdPercent, 2e-20);
    assert.equal(tiny.fxContributionPp, 1e-20);
    const subnormal = calculateScenario(Number.MIN_VALUE, Number.MIN_VALUE);
    assert.equal(subnormal.status, "valid");
    assert.equal(subnormal.usdPercent, 2 * Number.MIN_VALUE);
    assert.equal(subnormal.fxContributionPp, Number.MIN_VALUE);
  });

  it("rounds exact halfway results to the even binary significand", () => {
    // At local=1, contribution=(101/100)*FX. These exact dyadic FX
    // inputs put USD halfway between 50/51 and 151/152 ulps above 1.
    assert.equal(calculateScenario(1, 25 * Math.pow(2, -51)).usdPercent,
      1 + 50 * Number.EPSILON);
    assert.equal(calculateScenario(1, 75 * Math.pow(2, -51)).usdPercent,
      1 + 152 * Number.EPSILON);
  });

  it("evaluates finite results even when unscaled endpoint products overflow", () => {
    assert.equal(Number.isFinite((100 + 1e308) * (100 - 50)), false);
    const r = calculateScenario(1e308, -50);
    assert.equal(r.status, "valid");
    closeToDecimal(r.usdPercent, "5e307");
    closeToDecimal(r.fxContributionPp, "-5e307");
    const loss = calculateScenario(-100, Number.MAX_VALUE);
    assert.equal(loss.status, "valid");
    assert.equal(loss.usdPercent, -100);
    assert.equal(loss.fxContributionPp, 0);
  });

  it("keeps rounded finite endpoints while withholding genuine overflow and all sensitivity rows", () => {
    const finite = calculateScenario(Number.MAX_VALUE, Number.MIN_VALUE);
    assert.equal(finite.status, "valid");
    assert.equal(finite.usdPercent, Number.MAX_VALUE);
    assertInvalidScenario(calculateScenario(Number.MAX_VALUE, 3), "overflow");
    assert.deepEqual(sensitivityCases(Number.MAX_VALUE, Number.MIN_VALUE), []);
    assert.deepEqual(sensitivityCases(1e200, 1e200), []);
  });

  it("uses the accurate boundary result in sensitivity without approximate deduplication", () => {
    const rows = sensitivityCases(1e20, -99.99999999999999);
    assert.equal(rows.length, 3);
    assert.equal(rows[0].kind, "current");
    closeToDecimal(rows[0].usdPercent, "14110.854715202004");
    assert.equal(sensitivityCases(5, -0).length, 2);
    assert.equal(sensitivityCases(5, 3.0000000000000004).length, 3);
  });
});

describe("calculateScenario invalid inputs never become zero", () => {
  it("booleans are not 0/1", () => {
    assertInvalidScenario(calculateScenario(true, -3), "non_finite_input");
    assertInvalidScenario(calculateScenario(5, false), "non_finite_input");
    assert.notEqual(calculateScenario(true, false).usdPercent, 0);
  });

  it("null, undefined, and strings are not coerced", () => {
    assertInvalidScenario(calculateScenario(null, -3), "non_finite_input");
    assertInvalidScenario(calculateScenario(5, undefined), "non_finite_input");
    assertInvalidScenario(calculateScenario("5", "-3"), "non_finite_input");
    assert.equal(calculateScenario("5", "-3").usdPercent, null);
    assert.equal(calculateScenario("", 0).usdPercent, null);
  });

  it("NaN and Infinity are invalid", () => {
    assertInvalidScenario(calculateScenario(NaN, -3), "non_finite_input");
    assertInvalidScenario(calculateScenario(5, Infinity), "non_finite_input");
    assertInvalidScenario(calculateScenario(-Infinity, 0), "non_finite_input");
  });

  it("invalid after valid withholds result fields as null", () => {
    const ok = calculateScenario(5, -3);
    assert.equal(ok.status, "valid");
    const editingFx = parsePercent("-", "en");
    assert.equal(editingFx.status, "editing");
    const withheld = calculateScenario(5, editingFx.value);
    assertInvalidScenario(withheld, "non_finite_input");
  });

  it("overflow withholds all numeric outputs", () => {
    const r = calculateScenario(1e200, 1e200);
    assertInvalidScenario(r, "overflow");
  });
});

describe("inverse quote boundary", () => {
  it("reciprocal transform is not a sign flip; module does not convert quote mode", () => {
    const reverseQuotePct = 5;
    const reciprocalPct = 100 * (1 / (1 + reverseQuotePct / 100) - 1);
    assert.ok(Math.abs(reciprocalPct - -5) > 0.01);
    const signFlip = calculateScenario(5, -5);
    const reciprocal = calculateScenario(5, reciprocalPct);
    assert.equal(signFlip.status, "valid");
    assert.equal(reciprocal.status, "valid");
    assert.ok(Math.abs(signFlip.usdPercent - reciprocal.usdPercent) > 0.01);
    closeToDecimal(reciprocalPct, "-4.761904761904761904761904760");
  });
});

describe("sensitivityCases", () => {
  it("golden current / 0 / +3 for +5 local and -3 FX", () => {
    const rows = sensitivityCases(5, -3);
    assert.equal(rows.length, 3);
    assert.equal(rows[0].kind, "current");
    assert.equal(rows[0].fxPercent, -3);
    closeToDecimal(rows[0].usdPercent, "1.85");
    assert.equal(rows[1].kind, "unchanged");
    assert.equal(rows[1].fxPercent, 0);
    closeToDecimal(rows[1].usdPercent, "5");
    assert.equal(rows[2].kind, "illustrative_plus3");
    assert.equal(rows[2].fxPercent, 3);
    closeToDecimal(rows[2].usdPercent, "8.15");
  });

  it("deduplicates current when it equals 0, keeping the current label", () => {
    const rows = sensitivityCases(5, 0);
    assert.equal(rows.length, 2);
    assert.equal(rows[0].kind, "current");
    assert.equal(rows[0].fxPercent, 0);
    closeToDecimal(rows[0].usdPercent, "5");
    assert.equal(rows[1].kind, "illustrative_plus3");
    assert.equal(rows[1].fxPercent, 3);
  });

  it("deduplicates current when it equals +3, keeping the current label", () => {
    const rows = sensitivityCases(5, 3);
    assert.equal(rows.length, 2);
    assert.equal(rows[0].kind, "current");
    assert.equal(rows[0].fxPercent, 3);
    closeToDecimal(rows[0].usdPercent, "8.15");
    assert.equal(rows[1].kind, "unchanged");
    assert.equal(rows[1].fxPercent, 0);
  });

  it("withholds every row when original arithmetic is invalid", () => {
    assert.deepEqual(sensitivityCases(5, -100), []);
    assert.deepEqual(sensitivityCases(-100.01, 3), []);
    assert.deepEqual(sensitivityCases(5, NaN), []);
    assert.deepEqual(sensitivityCases(null, -3), []);
    const editing = parsePercent("-", "en");
    assert.deepEqual(sensitivityCases(5, editing.value), []);
  });

  it("all-or-none: original finite but generated +3 overflow withholds all rows", () => {
    const original = calculateScenario(1.75e308, 0);
    assert.equal(original.status, "valid");
    const plus3 = calculateScenario(1.75e308, 3);
    assert.equal(plus3.status, "invalid");
    assert.equal(plus3.reason, "overflow");
    assert.deepEqual(sensitivityCases(1.75e308, 0), []);
  });

  it("uses the entered local return on every surviving row", () => {
    const rows = sensitivityCases(-1.8, -0.8);
    assert.equal(rows.length, 3);
    closeToDecimal(rows[0].usdPercent, "-2.585600");
    const unchanged = calculateScenario(-1.8, 0);
    closeToDecimal(rows[1].usdPercent, String(unchanged.usdPercent));
    closeToDecimal(rows[1].usdPercent, "-1.8");
  });
});

// Parent adversarial regression: prototype properties are not supported values.
describe("closed parser sets", () => {
  it("rejects inherited object properties as locales", () => {
    for (const locale of ["toString", "constructor", "__proto__", "hasOwnProperty"]) {
      assertInvalidParse(parsePercent("5", locale), "unsupported_locale");
    }
  });
  it("rejects inherited object properties as editing text", () => {
    for (const raw of ["toString", "constructor", "__proto__", "hasOwnProperty"]) {
      assertInvalidParse(parsePercent(raw, "en"), "invalid_format");
    }
  });
});
