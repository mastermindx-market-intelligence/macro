import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { registerHooks } from "node:module";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

if (!process.argv[2]) throw Error("Pass the path to the pinned mastermind-terminal checkout");
const sourceUrl = (file) => pathToFileURL(resolve(process.argv[2], file)).href;

const read = (file) => readFileSync(new URL(file, import.meta.url));
const metadata = JSON.parse(read("./sources.json"));
for (const source of metadata.files) {
  const bytes = readFileSync(new URL(sourceUrl(source.path)));
  const id = createHash("sha1").update("blob " + bytes.length + "\0").update(bytes).digest("hex");
  assert.equal(id, source.blob, source.path);
}
const runtimeFiles = {
  "@/lib/theses": "./terminal/lib/theses.ts",
  "@/lib/analysisSymbol": "./terminal/lib/analysisSymbol.ts",
};
// Resolve the unmodified production module aliases. Node strips the files' TypeScript types.
registerHooks({
  resolve(specifier, context, nextResolve) {
    return nextResolve(runtimeFiles[specifier] ? sourceUrl(runtimeFiles[specifier]) : specifier, context);
  },
});
const {
  parseAnalysisRoute, parseAnalysisSearchParams, ambientForAnalysisRoute,
} = await import(sourceUrl("terminal/lib/analysisRoute.ts"));
const cases = JSON.parse(read("./matrix.json"));
let index = 0;
console.log("commit " + metadata.commit + "; " + process.version + "; 4 immutable file blob IDs verified");
for (const [label, encoded, expected] of cases) {
  const params = new URLSearchParams(encoded);
  // Model Next's searchParams object, preserving arrays for repeated fields.
  const serverInput = {};
  for (const key of new Set(params.keys())) {
    const occurrences = params.getAll(key);
    serverInput[key] = occurrences.length > 1 ? occurrences : occurrences[0];
  }
  const server = parseAnalysisRoute(serverInput);
  const browser = parseAnalysisSearchParams(params);
  assert.deepStrictEqual(server, expected, label + " server contract");
  assert.deepStrictEqual(browser, expected, label + " browser-query contract");
  assert.deepStrictEqual(browser, server, label + " entry-point parity");
  const expectedPanel = ["company", "theses"].includes(expected.kind) ? expected.kind : null;
  assert.equal(ambientForAnalysisRoute(browser), expectedPanel, label + " ambient panel");
  console.log("PASS " + String(++index).padStart(2, "0") + " | " + label);
}
console.log("PASS " + cases.length + "/" + cases.length + " query cases; " + (cases.length * 4) + " query assertions; 4 source integrity checks.");
