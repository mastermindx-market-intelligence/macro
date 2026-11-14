import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { registerHooks } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

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
const moduleUrl = pathToFileURL(resolve(directory, "sources/companySearchContext.ts")).href;
const symbolUrl = pathToFileURL(resolve(directory, "sources/analysisSymbol.ts")).href;
registerHooks({
  resolve(specifier, context, nextResolve) {
    if (context.parentURL === moduleUrl && specifier === "./analysisSymbol") return nextResolve(symbolUrl, context);
    return nextResolve(specifier, context);
  },
});
const api = await import(moduleUrl);
const results = [];
let assertions = 0;
function equal(actual, expected) {
  assertions += 1;
  assert.deepEqual(actual, expected);
}
function run(id, label, body, evidenceClass = "SOURCE_BEHAVIOR") {
  const before = assertions;
  const observed = body();
  results.push({ id, label, evidence_class: evidenceClass, status: "BASELINE_REPRODUCED", assertions: assertions - before, observed });
}
const queryCases = [
  ["Alibaba", "Alibaba"], [" 阿里巴巴 & # ", "阿里巴巴 & #"], ["", ""],
  [" \tAlibaba\n", "Alibaba"], ["Ali\nBaba", null], ["Ali\u0000Baba", null],
  ["x".repeat(160), "x".repeat(160)], ["x".repeat(161), null],
  ["😀".repeat(80), "😀".repeat(80)], ["😀".repeat(81), null],
  [null, null], [123, null],
];
queryCases.forEach(([input, expected], index) => {
  run(`SQ${String(index + 1).padStart(2, "0")}`, "Query normalization and UTF-16 limit", () => {
    const value = api.normalizeCompanySearchQuery(input);
    equal(value, expected);
    return { input_type: typeof input, input_length: typeof input === "string" ? input.length : null, output: value };
  });
});
for (const [id, input, expected] of [
  ["SS01", { symbol: "BABA", query: " Alibaba " }, { symbol: "BABA", query: "Alibaba" }],
  ["SS02", { symbol: "9988.HK", query: "阿里" }, { symbol: "9988.HK", query: "阿里" }],
  ["SS03", { symbol: "baba", query: "Alibaba" }, null],
  ["SS04", { symbol: " BABA", query: "Alibaba" }, null],
  ["SS05", { symbol: "BABA", query: "Alibaba", owner: "unexpected" }, null],
  ["SS06", ["BABA", "Alibaba"], null],
  ["SS07", { symbol: "BABA" }, null],
]) {
  run(id, "Canonical listing and narrow selection shape", () => {
    const value = api.readCompanySearchSelection(input);
    equal(value, expected);
    return value;
  });
}
run("SU01", "Encoded listing and CJK query round trip", () => {
  const href = api.companySearchAnalysisHref({ symbol: "9988.HK", query: "阿里 & #" });
  const url = new URL(href, "https://example.invalid");
  equal(url.pathname, "/analysis");
  equal(url.searchParams.get("symbol"), "9988.HK");
  equal(api.readCompanySearchQuery(url.searchParams), "阿里 & #");
  return { href, query: api.readCompanySearchQuery(url.searchParams) };
});
run("SU02", "Empty search differs from missing context", () => {
  const href = api.companySearchAnalysisHref({ symbol: "BABA", query: "" });
  equal(href, "/analysis?symbol=BABA&company_query=");
  equal(api.readCompanySearchQuery(new URLSearchParams("company_query=")), "");
  equal(api.readCompanySearchQuery(new URLSearchParams("symbol=BABA")), null);
  return { href };
});
run("SU03", "Duplicate or malformed query loses only search context", () => {
  equal(api.readCompanySearchQuery(new URLSearchParams("company_query=a&company_query=b")), null);
  equal(api.readCompanySearchQuery(new URLSearchParams("company_query=bad%00query")), null);
  equal(api.companySearchAnalysisHref({ symbol: "bad/path", query: "a" }), null);
  return { duplicate: null, malformed: null, invalid_selection_href: null };
});
for (const [id, row, symbol, expected] of [
  ["SC01", { ticker: "BABA", quote_currency: "USD", stmt_currency: "CNY" }, "BABA", "USD"],
  ["SC02", { ticker: "9988.HK", quote_currency: "HKD" }, "BABA", null],
  ["SC03", { ticker: "BABA", stmt_currency: "CNY" }, "BABA", null],
  ["SC04", { ticker: "BABA", quote_currency: "usd" }, "BABA", null],
  ["SC05", { ticker: "9988.HK", quote_currency: "HKD" }, "9988.HK", "HKD"],
]) {
  run(id, "Trading currency requires exact listing and quote field", () => {
    const value = api.tradingCurrencyFor(row, symbol);
    equal(value, expected);
    return { requested: symbol, observed: value };
  });
}
for (const [id, row, expected, evidenceClass] of [
  ["SV01", { sec: "Equities", mkt: "NYSE" }, "NYSE"],
  ["SV02", { mkt: "NYSE" }, null],
  ["SV03", { sec: "Options", mkt: "NYSE" }, null],
  ["SV04", { sec: "Equities", mkt: "" }, null],
  ["SV05", { sec: "Equities", mkt: "N\nYSE" }, null],
  ["SV06", { sec: "Equities", mkt: "x".repeat(81) }, null],
  ["SV07", { sec: "Equities", mkt: "   " }, "   ", "EXPECTED_UNDESIRABLE_BASELINE"],
]) {
  run(id, "Explicit venue field boundary", () => {
    const value = api.venueFor({ symbols: { BABA: row } }, "BABA");
    equal(value, expected);
    return { observed: value };
  }, evidenceClass);
}
run("SV08", "A different listing never supplies the venue", () => {
  const value = api.venueFor({ symbols: { "9988.HK": { sec: "Equities", mkt: "HKEX" } } }, "BABA");
  equal(value, null);
  return { observed: value };
});

console.log(JSON.stringify({
  status: "SOURCE_BEHAVIOR_REPRODUCED", source_commit: manifest.commit,
  method: "Unchanged module imports with Node native type stripping",
  cases: results.length, assertions, integrity_checks: integrityChecks,
  browser_assertions: 0, history_restore_assertions: 0,
  limitations: ["ShellSearch React lifecycle is source-inspected separately", "New source epoch is a narrow dependency read", "Whitespace-only venue requires owner qualification"],
  results,
}, null, 2));
