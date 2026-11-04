import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { registerHooks, stripTypeScriptTypes } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import vm from "node:vm";

const directory = dirname(fileURLToPath(import.meta.url));
const manifest = JSON.parse(readFileSync(resolve(directory, "sources.json"), "utf8"));
let integrityChecks = 0;
for (const file of manifest.files) {
  const bytes = readFileSync(resolve(directory, file.local_path));
  assert.equal(createHash("sha1").update(`blob ${bytes.length}\0`).update(bytes).digest("hex"), file.git_blob);
  assert.equal(createHash("sha256").update(bytes).digest("hex"), file.sha256);
  assert.equal(bytes.length, file.bytes);
  integrityChecks += 3;
}

const mathUrl = pathToFileURL(resolve(directory, "../statements/sources/terminal/lib/finStatementMath.ts")).href;
const marketUrl = pathToFileURL(resolve(directory, "../statements/sources/terminal/lib/markets.ts")).href;
registerHooks({
  resolve(specifier, context, nextResolve) {
    if (context.parentURL === mathUrl && specifier === "./markets") return nextResolve(marketUrl, context);
    return nextResolve(specifier, context);
  },
});
const math = await import(mathUrl);
const format = await import(pathToFileURL(resolve(directory, "sources/finFormat.ts")).href);
const source = readFileSync(resolve(directory, "sources/ForecastPage.tsx"), "utf8");

// These top-level source functions end at column zero in the pinned file.
// A source hash change fails before extraction. No React render is substituted.
function originalFunction(name) {
  const start = source.indexOf(`function ${name}(`);
  assert.ok(start >= 0, name);
  const end = source.indexOf("\n}", start);
  assert.ok(end > start, name);
  return source.slice(start, end + 2);
}

const context = vm.createContext({
  pick: format.pick,
  fmtNum: format.fmtNum,
  incomeView: math.incomeView,
  incomeViewTopLineLabel: math.incomeViewTopLineLabel,
  isIndustrialIncomeView: math.isIndustrialIncomeView,
});
const functions = ["buildEstimateRows", "mapRawPeriodLabel", "buildActualsTable"];
vm.runInContext(stripTypeScriptTypes(functions.map(originalFunction).join("\n")), context);
const plain = value => JSON.parse(JSON.stringify(value));
const results = [];
let assertions = 0;
function equal(actual, expected, label) {
  assertions += 1;
  assert.deepEqual(plain(actual), expected, label);
}
function run(id, label, operation, evidenceClass = "SOURCE_BEHAVIOR") {
  const before = assertions;
  const observed = operation();
  results.push({ id, label, evidence_class: evidenceClass, status: "BASELINE_REPRODUCED", assertions: assertions - before, observed });
}
function estimates(periods = ["2026", "2027", "2028"], values = [6, 7, 8]) {
  const series = {
    periods, avg: values,
    high: periods.map(() => null), low: periods.map(() => null), n: periods.map(() => null),
  };
  return { eps_fy: series, rev_fy: structuredClone(series), eps_q: null, growth: { eps_yoy: null, rev_yoy: null } };
}
const emptyFund = { ticker: "600519.SS", earnings: { fy: [], q: [] } };
for (const [id, periods, values] of [
  ["FC01", ["2026", "2027", "2028"], [6, 7, 8]],
  ["FC02", ["2026", "2027"], [6, 7]],
  ["FC03", ["2026", "2028"], [6, 8]],
  ["FC04", ["2028"], [8]],
]) {
  run(id, "Every supplied annual target is retained", () => {
    const output = context.buildEstimateRows("eps", emptyFund, estimates(periods, values), "A");
    equal(output.labels, periods, "supplied identities");
    equal(output.estimate, values, "supplied estimates");
    equal(output.reported, periods.map(() => null), "unknown actuals");
    return plain(output);
  });
}
run("FC05", "Null quarterly estimates retain actual history", () => {
  const fund = { ticker: "600519.SS", earnings: { fy: [], q: [{ period: "Q1 2026", eps_a: 2, eps_e: null }] } };
  const output = context.buildEstimateRows("eps", fund, estimates(), "Q");
  equal(output.labels, ["Q1 2026"], "quarter label");
  equal(output.reported, [2], "quarter actual");
  equal(output.estimate, [null], "missing quarter estimate");
  return plain(output);
});
run("FC06", "Absent estimate block retains annual helper actuals", () => {
  const fund = { ticker: "600519.SS", earnings: { fy: [{ period: "FY2025", eps_a: 5, eps_e: null }], q: [] } };
  const output = context.buildEstimateRows("eps", fund, null, "A");
  equal(output.labels, ["FY2025"], "actual period");
  equal(output.reported, [5], "actual retained");
  equal(output.estimate, [null], "absent estimate");
  return plain(output);
});
run("FC07", "All-null annual values retain known target identities", () => {
  const output = context.buildEstimateRows("eps", emptyFund, estimates(undefined, [null, null, null]), "A");
  equal(output.labels, ["2026", "2027", "2028"], "known fiscal targets");
  equal(output.estimate, [null, null, null], "unknown values");
  return plain(output);
});
run("FC08", "Zero denominators and signed EPS retain arithmetic semantics", () => {
  const fund = { earnings: { fy: [{ period: "2024", eps_a: 0, eps_e: 0 }, { period: "2025", eps_a: -1, eps_e: -2 }], q: [] } };
  const output = context.buildEstimateRows("eps", fund, null, "A");
  equal(output.reported, [0, -1], "zero and loss");
  equal(output.surprise, [null, 50], "zero denominator and signed baseline");
  return plain(output);
});
run("FC09", "Unclocked forward average fills an actual-period comparator", () => {
  const fund = { earnings: { fy: [{ period: "2026", eps_a: 10, eps_e: null }], q: [] } };
  const output = context.buildEstimateRows("eps", fund, estimates(["2026"], [8]), "A");
  equal(output.estimate, [8], "forward value patched");
  equal(output.surprise, [25], "unqualified surprise baseline");
  return plain(output);
}, "EXPECTED_UNDESIRABLE_BASELINE");
run("FC10", "Different raw period labels remain distinct", () => {
  const fund = { earnings: { fy: [{ period: "FY2026", eps_a: 10, eps_e: null }], q: [] } };
  const output = context.buildEstimateRows("eps", fund, estimates(["2026"], [8]), "A");
  equal(output.labels, ["FY2026", "2026"], "exact-label matching");
  equal(output.surprise, [null, null], "no implicit identity qualification");
  return plain(output);
});
run("FC11", "Distinct consensus and report populations pass through", () => {
  const est = estimates(["2026"], [6]);
  Object.assign(est.eps_fy, { high: [9], low: [8], n: [2] });
  const output = context.buildActualsTable(emptyFund, est, "income", false);
  const detail = output.rows[0].children;
  equal(output.periods, ["2026 E"], "fiscal target");
  equal(detail.map(row => row.values), [[null], [6], [9], [8], [2]], "uncoerced populations");
  return { periods: plain(output.periods), detail: detail.map(row => ({ label: row.label, values: plain(row.values) })) };
});
run("FC12", "Chinese report-count label currently says institution count", () => {
  const output = context.buildActualsTable(emptyFund, estimates(["2028"], [8]), "income", true);
  const row = output.rows[0].children[4];
  equal(row.label, "预测机构数", "current label");
  equal(row.values, [null], "missing count");
  return { label: row.label, values: plain(row.values) };
}, "EXPECTED_UNDESIRABLE_BASELINE");
run("FC13", "Actual table helper computes retained actuals without estimates", () => {
  const fund = { ticker: "600519.SS", earnings: { fy: [{ period: "FY2025", eps_a: 5 }], q: [] } };
  const output = context.buildActualsTable(fund, null, "income", false);
  equal(output.periods, ["FY2025"], "actual period");
  equal(output.rows[0].values, [5], "helper retains actual");
  return { periods: plain(output.periods), eps: plain(output.rows[0].values), component_early_return: "SOURCE_INSPECTED_SEPARATELY" };
});

console.log(JSON.stringify({
  status: "SOURCE_BEHAVIOR_REPRODUCED", source_commit: manifest.commit,
  method: "Three unchanged function bodies, Node native type stripping, unchanged formatting/math imports",
  cases: results.length, assertions, integrity_checks: integrityChecks,
  component_render_assertions: 0, browser_assertions: 0,
  limitations: ["React component mount blocked by npm E403 during dependency setup", "Controlled fixtures establish source behavior only", "Estimate timing and rights require the existing data owner"],
  results,
}, null, 2));
